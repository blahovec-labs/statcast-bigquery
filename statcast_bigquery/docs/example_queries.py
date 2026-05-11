"""Curated example queries — unit-tested for BigQuery-dialect parseability via sqlglot.

Each query uses the placeholder `{table}` for the fully qualified pitches table.
Substitute and wrap in backticks: `your-project.your_dataset.statcast_pitches`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExampleQuery:
    title: str
    question: str
    sql: str
    columns_used: list[str]
    result_shape: str
    notes: str | None


EXAMPLE_QUERIES: list[ExampleQuery] = [
    ExampleQuery(
        title="League barrel rate by season",
        question="What's the league-wide barrel rate per season?",
        sql=(
            "SELECT game_year,\n"
            "       AVG(IF(launch_speed >= 98 AND launch_angle BETWEEN 8 AND 50, 1.0, 0.0))\n"
            "         AS barrel_rate,\n"
            "       COUNT(*) AS batted_balls\n"
            "FROM {table}\n"
            "WHERE game_type = 'R' AND launch_speed IS NOT NULL\n"
            "GROUP BY game_year\n"
            "ORDER BY game_year;"
        ),
        columns_used=["game_year", "game_type", "launch_speed", "launch_angle"],
        result_shape="one row per season",
        notes="Filter to regular season + batted balls before averaging.",
    ),
    ExampleQuery(
        title="Top hard-hit% hitters this season",
        question="Top 10 hitters by hard-hit% (>=100 BBE) this season",
        sql=(
            "SELECT batter,\n"
            "       AVG(IF(launch_speed >= 95, 1.0, 0.0)) AS hard_hit_pct,\n"
            "       COUNT(*) AS bbe\n"
            "FROM {table}\n"
            "WHERE game_type='R' AND launch_speed IS NOT NULL\n"
            "  AND game_year = EXTRACT(YEAR FROM CURRENT_DATE())\n"
            "GROUP BY batter\n"
            "HAVING bbe >= 100\n"
            "ORDER BY hard_hit_pct DESC\n"
            "LIMIT 10;"
        ),
        columns_used=["batter", "launch_speed", "game_type", "game_year"],
        result_shape="10 rows, batter sorted by hard_hit_pct",
        notes=None,
    ),
    ExampleQuery(
        title="Umpire called-strike rate (last 30 days)",
        question="Called-strike rate by umpire over the last 30 days",
        sql=(
            "SELECT umpire,\n"
            "       AVG(IF(description = 'called_strike', 1.0, 0.0)) AS called_k_rate,\n"
            "       COUNTIF(description IN ('called_strike','ball')) AS sample\n"
            "FROM {table}\n"
            "WHERE description IN ('called_strike','ball')\n"
            "  AND game_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)\n"
            "                    AND CURRENT_DATE()\n"
            "GROUP BY umpire\n"
            "HAVING sample >= 100\n"
            "ORDER BY called_k_rate DESC;"
        ),
        columns_used=["umpire", "description", "game_date"],
        result_shape="one row per umpire",
        notes="Restricts to called pitches (called_strike + ball). Excludes swings, fouls, HBP.",
    ),
    ExampleQuery(
        title="Edge-zone called-strike rate by umpire",
        question="Which umpires call edge-zone pitches strikes most often?",
        sql=(
            "SELECT umpire,\n"
            "       AVG(IF(description = 'called_strike', 1.0, 0.0)) AS edge_k_rate,\n"
            "       COUNT(*) AS sample\n"
            "FROM {table}\n"
            "WHERE description IN ('called_strike','ball')\n"
            "  AND ABS(ABS(plate_x) - 0.83) < 0.0833\n"
            "GROUP BY umpire\n"
            "HAVING sample >= 50\n"
            "ORDER BY edge_k_rate DESC;"
        ),
        columns_used=["umpire", "description", "plate_x"],
        result_shape="one row per umpire",
        notes="Edge zone defined as within 1 inch of plate edge.",
    ),
    ExampleQuery(
        title="Pitcher whiff rate vs L/R batters",
        question="Compare whiff rate against left-handed vs right-handed batters by pitcher",
        sql=(
            "WITH swings AS (\n"
            "  SELECT pitcher, stand,\n"
            "         description IN ('swinging_strike','swinging_strike_blocked',\n"
            "                         'foul_tip','missed_bunt') AS is_whiff,\n"
            "         description IN ('swinging_strike','swinging_strike_blocked','foul_tip',\n"
            "                         'foul','hit_into_play','missed_bunt') AS is_swing\n"
            "  FROM {table}\n"
            "  WHERE game_type = 'R'\n"
            ")\n"
            "SELECT pitcher,\n"
            "       AVG(IF(stand='L' AND is_swing, IF(is_whiff,1.0,0.0), NULL)) AS whiff_vs_L,\n"
            "       AVG(IF(stand='R' AND is_swing, IF(is_whiff,1.0,0.0), NULL)) AS whiff_vs_R\n"
            "FROM swings\n"
            "GROUP BY pitcher\n"
            "ORDER BY pitcher;"
        ),
        columns_used=["pitcher", "stand", "description", "game_type"],
        result_shape="one row per pitcher",
        notes=None,
    ),
    ExampleQuery(
        title="Average exit velocity allowed by starter",
        question="Average EV allowed per starter (where pitcher pitched 1st inning of game)",
        sql=(
            "WITH starters AS (\n"
            "  SELECT DISTINCT game_pk, pitcher\n"
            "  FROM {table}\n"
            "  WHERE inning = 1\n"
            ")\n"
            "SELECT s.pitcher,\n"
            "       AVG(p.launch_speed) AS avg_ev_allowed,\n"
            "       COUNT(*) AS bbe\n"
            "FROM {table} p\n"
            "JOIN starters s USING (game_pk, pitcher)\n"
            "WHERE p.launch_speed IS NOT NULL AND p.game_type='R'\n"
            "GROUP BY s.pitcher\n"
            "HAVING bbe >= 50\n"
            "ORDER BY avg_ev_allowed DESC;"
        ),
        columns_used=["pitcher", "inning", "launch_speed", "game_pk", "game_type"],
        result_shape="one row per starter",
        notes="Approximation; true 'starter' role is from statsapi.",
    ),
    ExampleQuery(
        title="xwOBA on contact, by batter (current season)",
        question="Best xwOBA on contact this season (>=150 BBE)",
        sql=(
            "SELECT batter,\n"
            "       AVG(estimated_woba_using_speedangle) AS xwoba_contact,\n"
            "       COUNT(*) AS bbe\n"
            "FROM {table}\n"
            "WHERE game_type='R'\n"
            "  AND launch_speed IS NOT NULL\n"
            "  AND game_year = EXTRACT(YEAR FROM CURRENT_DATE())\n"
            "GROUP BY batter\n"
            "HAVING bbe >= 150\n"
            "ORDER BY xwoba_contact DESC\n"
            "LIMIT 25;"
        ),
        columns_used=[
            "batter", "estimated_woba_using_speedangle", "launch_speed",
            "game_type", "game_year",
        ],
        result_shape="25 rows",
        notes=None,
    ),
    ExampleQuery(
        title="Pitches per plate appearance by team",
        question="P/PA — how many pitches does each team see per PA?",
        sql=(
            "WITH ab AS (\n"
            "  SELECT game_pk, at_bat_number,\n"
            "         IF(inning_topbot='Top', away_team, home_team) AS batting_team,\n"
            "         COUNT(*) AS pitches\n"
            "  FROM {table} WHERE game_type='R'\n"
            "  GROUP BY 1,2,3\n"
            ")\n"
            "SELECT batting_team, AVG(pitches) AS p_per_pa, COUNT(*) AS pa_count\n"
            "FROM ab GROUP BY batting_team ORDER BY p_per_pa DESC;"
        ),
        columns_used=[
            "game_pk", "at_bat_number", "inning_topbot", "away_team",
            "home_team", "game_type",
        ],
        result_shape="30 rows",
        notes=None,
    ),
    ExampleQuery(
        title="Sweet-spot rate leaders",
        question="Hitters with highest sweet-spot rate (8-32 degree launch angle, >=100 BBE)",
        sql=(
            "SELECT batter,\n"
            "       AVG(IF(launch_angle BETWEEN 8 AND 32, 1.0, 0.0)) AS sweet_spot_pct,\n"
            "       COUNT(*) AS bbe\n"
            "FROM {table}\n"
            "WHERE game_type='R' AND launch_speed IS NOT NULL\n"
            "GROUP BY batter HAVING bbe >= 100\n"
            "ORDER BY sweet_spot_pct DESC LIMIT 25;"
        ),
        columns_used=["batter", "launch_angle", "launch_speed", "game_type"],
        result_shape="25 rows",
        notes=None,
    ),
    ExampleQuery(
        title="Bat speed leaders 2024+",
        question="BBE-weighted top 25 bat speeds (2024 onward, where bat_speed populated)",
        sql=(
            "SELECT batter, AVG(bat_speed) AS avg_bat_speed, COUNT(*) AS bbe\n"
            "FROM {table}\n"
            "WHERE bat_speed IS NOT NULL AND game_year >= 2024 AND game_type='R'\n"
            "GROUP BY batter HAVING bbe >= 50\n"
            "ORDER BY avg_bat_speed DESC LIMIT 25;"
        ),
        columns_used=["batter", "bat_speed", "game_year", "game_type"],
        result_shape="25 rows",
        notes=None,
    ),
    ExampleQuery(
        title="Strikeout rate on 0-2 counts by pitcher",
        question="Best K rate when ahead 0-2",
        sql=(
            "SELECT pitcher,\n"
            "       AVG(IF(events='strikeout', 1.0, 0.0)) AS k_rate_02,\n"
            "       COUNT(*) AS pa_02\n"
            "FROM {table}\n"
            "WHERE balls=0 AND strikes=2 AND events IS NOT NULL AND game_type='R'\n"
            "GROUP BY pitcher HAVING pa_02 >= 50\n"
            "ORDER BY k_rate_02 DESC LIMIT 25;"
        ),
        columns_used=["pitcher", "balls", "strikes", "events", "game_type"],
        result_shape="25 rows",
        notes="Only counts terminal 0-2 PAs (events not null).",
    ),
    ExampleQuery(
        title="Average release speed by pitch type, by pitcher",
        question="Pitch-type velocity profile per pitcher",
        sql=(
            "SELECT pitcher, pitch_type,\n"
            "       AVG(release_speed) AS avg_velo,\n"
            "       COUNT(*) AS pitches\n"
            "FROM {table}\n"
            "WHERE pitch_type IS NOT NULL AND game_type='R'\n"
            "GROUP BY pitcher, pitch_type HAVING pitches >= 50\n"
            "ORDER BY pitcher, avg_velo DESC;"
        ),
        columns_used=["pitcher", "pitch_type", "release_speed", "game_type"],
        result_shape="multiple rows per pitcher",
        notes=None,
    ),
    ExampleQuery(
        title="Spin rate distribution by pitch type",
        question="Mean / stddev / quartile spin rate per pitch type, league-wide",
        sql=(
            "SELECT pitch_type,\n"
            "       AVG(release_spin_rate) AS avg_spin,\n"
            "       APPROX_QUANTILES(release_spin_rate, 100)[OFFSET(50)] AS p50,\n"
            "       APPROX_QUANTILES(release_spin_rate, 100)[OFFSET(90)] AS p90,\n"
            "       COUNT(*) AS pitches\n"
            "FROM {table}\n"
            "WHERE release_spin_rate IS NOT NULL AND game_type='R'\n"
            "GROUP BY pitch_type ORDER BY avg_spin DESC;"
        ),
        columns_used=["pitch_type", "release_spin_rate", "game_type"],
        result_shape="one row per pitch type",
        notes=(
            "Uses APPROX_QUANTILES (BigQuery's approximate-quantile aggregate). "
            "Exact PERCENTILE_CONT in BQ is window-only."
        ),
    ),
    ExampleQuery(
        title="Pitch usage % by count state",
        question="What pitch types are thrown in 0-0, 1-1, 3-2 count states (league-wide)?",
        sql=(
            "SELECT balls, strikes, pitch_type,\n"
            "       COUNT(*) AS n,\n"
            "       100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY balls, strikes) AS pct\n"
            "FROM {table}\n"
            "WHERE pitch_type IS NOT NULL AND game_type='R'\n"
            "GROUP BY balls, strikes, pitch_type\n"
            "ORDER BY balls, strikes, pct DESC;"
        ),
        columns_used=["balls", "strikes", "pitch_type", "game_type"],
        result_shape="rows by count + pitch type",
        notes=None,
    ),
    ExampleQuery(
        title="Plate-appearance result distribution by inning",
        question="How does PA outcome distribution change by inning?",
        sql=(
            "WITH terminal AS (\n"
            "  SELECT inning, events FROM {table}\n"
            "  WHERE events IS NOT NULL AND game_type='R'\n"
            ")\n"
            "SELECT inning, events, COUNT(*) AS n\n"
            "FROM terminal GROUP BY inning, events ORDER BY inning, n DESC;"
        ),
        columns_used=["inning", "events", "game_type"],
        result_shape="rows per inning + outcome",
        notes=None,
    ),
    ExampleQuery(
        title="Hard-hit balls allowed by reliever in high-leverage innings",
        question="Bullpen hard-hit% allowed in innings 7+",
        sql=(
            "SELECT pitcher,\n"
            "       AVG(IF(launch_speed >= 95, 1.0, 0.0)) AS hard_hit_allowed,\n"
            "       COUNT(*) AS bbe\n"
            "FROM {table}\n"
            "WHERE inning >= 7 AND launch_speed IS NOT NULL AND game_type='R'\n"
            "GROUP BY pitcher HAVING bbe >= 25\n"
            "ORDER BY hard_hit_allowed DESC;"
        ),
        columns_used=["pitcher", "inning", "launch_speed", "game_type"],
        result_shape="one row per reliever",
        notes=None,
    ),
    ExampleQuery(
        title="Run expectancy by base-out state (24-state RE)",
        question="League-average run expectancy across all 24 base-out states",
        sql=(
            "WITH starts AS (\n"
            "  SELECT game_pk, inning, inning_topbot, at_bat_number,\n"
            "         IF(on_1b IS NOT NULL,1,0) AS r1,\n"
            "         IF(on_2b IS NOT NULL,1,0) AS r2,\n"
            "         IF(on_3b IS NOT NULL,1,0) AS r3,\n"
            "         outs_when_up AS outs,\n"
            "         post_bat_score - bat_score AS runs_added\n"
            "  FROM {table}\n"
            "  WHERE pitch_number = 1 AND game_type='R'\n"
            ")\n"
            "SELECT r1, r2, r3, outs, AVG(runs_added) AS RE, COUNT(*) AS n\n"
            "FROM starts GROUP BY r1, r2, r3, outs ORDER BY r1, r2, r3, outs;"
        ),
        columns_used=[
            "game_pk", "inning", "inning_topbot", "at_bat_number",
            "on_1b", "on_2b", "on_3b", "outs_when_up",
            "post_bat_score", "bat_score", "pitch_number", "game_type",
        ],
        result_shape="24 rows",
        notes="Approximation — assumes per-PA marginal run change.",
    ),
    ExampleQuery(
        title="Baserunner on first — pitch distribution",
        question="What pitches are thrown when a runner is on first base?",
        sql=(
            "SELECT pitch_type,\n"
            "       COUNT(*) AS pitches,\n"
            "       AVG(IF(description='ball',1.0,0.0)) AS ball_rate\n"
            "FROM {table}\n"
            "WHERE on_1b IS NOT NULL AND pitch_type IS NOT NULL\n"
            "  AND game_type='R'\n"
            "GROUP BY pitch_type ORDER BY pitches DESC;"
        ),
        columns_used=["on_1b", "pitch_type", "description", "game_type"],
        result_shape="one row per pitch type",
        notes=(
            "Sprint speed on baserunning events is a real Statcast field but is not in "
            "PITCHES_SCHEMA; use statsapi game data for runner sprint speed."
        ),
    ),
    ExampleQuery(
        title="Late-and-close performance by team",
        question="Team batting wOBA in close games, innings 7+",
        sql=(
            "SELECT IF(inning_topbot='Top', away_team, home_team) AS batting_team,\n"
            "       AVG(woba_value) AS late_close_woba,\n"
            "       COUNT(*) AS n\n"
            "FROM {table}\n"
            "WHERE inning >= 7\n"
            "  AND ABS(post_bat_score - post_fld_score) <= 2\n"
            "  AND game_type='R' AND woba_value IS NOT NULL\n"
            "GROUP BY batting_team ORDER BY late_close_woba DESC;"
        ),
        columns_used=[
            "inning_topbot", "away_team", "home_team",
            "woba_value", "inning", "post_bat_score", "post_fld_score", "game_type",
        ],
        result_shape="30 rows",
        notes=None,
    ),
    ExampleQuery(
        title="Year-over-year league exit-velocity trend",
        question="Mean exit velocity per season",
        sql=(
            "SELECT game_year, AVG(launch_speed) AS avg_ev, COUNT(*) AS bbe\n"
            "FROM {table} WHERE launch_speed IS NOT NULL AND game_type='R'\n"
            "GROUP BY game_year ORDER BY game_year;"
        ),
        columns_used=["game_year", "launch_speed", "game_type"],
        result_shape="one row per year",
        notes=None,
    ),
    ExampleQuery(
        title="Pitch tempo by pitcher",
        question="Estimate pitches per minute (game-time) per pitcher",
        sql=(
            "SELECT pitcher, COUNT(*) AS pitches, COUNT(DISTINCT game_pk) AS games,\n"
            "       COUNT(*) / NULLIF(COUNT(DISTINCT game_pk), 0) AS pitches_per_game\n"
            "FROM {table} WHERE game_type='R'\n"
            "GROUP BY pitcher ORDER BY pitches_per_game DESC;"
        ),
        columns_used=["pitcher", "game_pk", "game_type"],
        result_shape="one row per pitcher",
        notes="Tempo-style proxy; for actual pitch-clock data use statsapi.",
    ),
    ExampleQuery(
        title="Two-strike approach: K rate vs contact rate",
        question="When ahead 0-2 / 1-2 / 2-2, who strikes out vs makes contact?",
        sql=(
            "SELECT pitcher, balls, strikes,\n"
            "       AVG(IF(events='strikeout',1.0,0.0)) AS k_rate,\n"
            "       AVG(IF(events IN ('single','double','triple','home_run'),1.0,0.0))\n"
            "         AS contact_rate,\n"
            "       COUNT(*) AS terminal_pas\n"
            "FROM {table}\n"
            "WHERE strikes = 2 AND events IS NOT NULL AND game_type='R'\n"
            "GROUP BY pitcher, balls, strikes\n"
            "HAVING terminal_pas >= 25\n"
            "ORDER BY pitcher, balls, strikes;"
        ),
        columns_used=["pitcher", "balls", "strikes", "events", "game_type"],
        result_shape="rows by pitcher x count",
        notes=None,
    ),
    ExampleQuery(
        title="Catcher framing approximation",
        question="Catcher's called-strike rate on edge-zone pitches",
        sql=(
            "SELECT fielder_2 AS catcher,\n"
            "       AVG(IF(description='called_strike',1.0,0.0)) AS edge_called_k_rate,\n"
            "       COUNT(*) AS edge_pitches\n"
            "FROM {table}\n"
            "WHERE description IN ('called_strike','ball')\n"
            "  AND ABS(ABS(plate_x) - 0.83) < 0.0833\n"
            "  AND game_type='R'\n"
            "GROUP BY catcher HAVING edge_pitches >= 100\n"
            "ORDER BY edge_called_k_rate DESC;"
        ),
        columns_used=["fielder_2", "description", "plate_x", "game_type"],
        result_shape="one row per catcher",
        notes="Approximation; for true framing models use Baseball Savant's framing leaderboard.",
    ),
    ExampleQuery(
        title="Park effects on exit velocity",
        question="Mean EV by stadium (home_team as proxy)",
        sql=(
            "SELECT home_team AS park, AVG(launch_speed) AS avg_ev, COUNT(*) AS bbe\n"
            "FROM {table} WHERE launch_speed IS NOT NULL AND game_type='R'\n"
            "GROUP BY park HAVING bbe >= 1000 ORDER BY avg_ev DESC;"
        ),
        columns_used=["home_team", "launch_speed", "game_type"],
        result_shape="30 rows",
        notes="Approximation — assumes park = home_team. Some teams shared/moved stadiums.",
    ),
    ExampleQuery(
        title="Game-by-game team Statcast batting line",
        question="V1's per-game-team batting metrics — barrel rate, hard-hit%, EV, xwOBA",
        sql=(
            "WITH bb AS (\n"
            "  SELECT game_pk, game_date,\n"
            "         IF(inning_topbot='Top', away_team, home_team) AS batting_team,\n"
            "         launch_speed, launch_angle, estimated_woba_using_speedangle AS xwoba\n"
            "  FROM {table} WHERE game_type='R' AND launch_speed IS NOT NULL\n"
            ")\n"
            "SELECT game_pk, game_date, batting_team,\n"
            "       AVG(IF(launch_speed>=98 AND launch_angle BETWEEN 8 AND 50,1.0,0.0))\n"
            "         AS barrel_rate,\n"
            "       AVG(IF(launch_speed>=95,1.0,0.0)) AS hard_hit_pct,\n"
            "       AVG(launch_speed) AS avg_ev,\n"
            "       AVG(launch_angle) AS avg_la,\n"
            "       AVG(xwoba) AS xwoba_contact,\n"
            "       COUNT(*) AS bbe\n"
            "FROM bb GROUP BY 1,2,3 ORDER BY 1,2,3;"
        ),
        columns_used=[
            "game_pk", "game_date", "inning_topbot", "away_team", "home_team",
            "launch_speed", "launch_angle", "estimated_woba_using_speedangle",
            "game_type",
        ],
        result_shape="one row per (game, batting team)",
        notes="V1's `statcast_games` view replicates this output.",
    ),
]
