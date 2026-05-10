"""Pitfall catalog — known cross-cutting gotchas for Statcast data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pitfall:
    summary: str
    explanation: str
    columns: list[str]   # columns referenced; CI verifies they exist


PITFALLS: list[Pitfall] = [
    Pitfall(
        summary="launch_speed and launch_angle are NULL for non-batted balls.",
        explanation=(
            "These metrics are only populated when the pitch was put into play. "
            "For other pitches (called strike, ball, foul tip, swinging strike, hit-by-pitch, "
            "intentional ball), they are NULL. Always filter by `description = 'hit_into_play'` "
            "or `launch_speed IS NOT NULL` before averaging."
        ),
        columns=["launch_speed", "launch_angle", "description"],
    ),
    Pitfall(
        summary="game_type='R' is required for regular-season analyses.",
        explanation=(
            "Statcast also covers spring training ('S'), exhibition ('E'), wild card ('F'), "
            "division series ('D'), league championship ('L'), and World Series ('W'). "
            "Without the filter, your aggregate mixes regimes."
        ),
        columns=["game_type"],
    ),
    Pitfall(
        summary="Statcast team abbreviations differ from MLB-StatsAPI's.",
        explanation=(
            "Statcast uses 'AZ' (not 'ARI'), 'WSH' (not 'WSN'), 'CWS' (White Sox; some sources "
            "use 'CHW'), and historical 'OAK' rather than 'ATH' for the Athletics. Use a "
            "canonical mapping if joining across data sources."
        ),
        columns=["home_team", "away_team"],
    ),
    Pitfall(
        summary="bat_speed is 2024+ only.",
        explanation=(
            "MLB began publishing bat speed in 2024. Earlier games have NULL. Filter by "
            "`game_year >= 2024` before computing bat-speed aggregates."
        ),
        columns=["bat_speed", "game_year"],
    ),
    Pitfall(
        summary="sprint_speed is sparse — populated only on baserunning events.",
        explanation=(
            "Sprint speed is measured when a runner triggers enough trackable events. "
            "Many pitches have NULL sprint_speed for the runner on first. Don't blindly filter "
            "for non-NULL — instead aggregate by runner across many games to derive a "
            "season-level sprint_speed."
        ),
        columns=["on_1b"],
    ),
    Pitfall(
        summary="`events` is NULL on non-terminal pitches.",
        explanation=(
            "The `events` column carries the at-bat outcome (single, strikeout, etc.) only on "
            "the *last* pitch of the at-bat. To get a per-AB outcome, group by "
            "(game_pk, at_bat_number) and take `events` from the row with `MAX(pitch_number)`."
        ),
        columns=["events", "pitch_number", "at_bat_number"],
    ),
    Pitfall(
        summary="`description` (per-pitch) and `events` (per-AB) live in different vocabularies.",
        explanation=(
            "`description` carries values like 'called_strike', 'hit_into_play', 'ball'. "
            "`events` carries values like 'single', 'strikeout', 'walk'. They overlap "
            "conceptually but should not be mixed in the same aggregation."
        ),
        columns=["description", "events"],
    ),
    Pitfall(
        summary="plate_x is from the catcher's perspective, not the batter's.",
        explanation=(
            "Negative `plate_x` is on the third-base side of home plate. To get a batter-eye "
            "view, multiply by -1 for right-handed batters (or use a derived column)."
        ),
        columns=["plate_x", "stand"],
    ),
    Pitfall(
        summary="release_speed and effective_speed measure different things.",
        explanation=(
            "`release_speed` is the velocity at the moment of release. `effective_speed` "
            "factors in extension and release point — it's the perceived velocity at the plate. "
            "Use `release_speed` for raw stuff metrics; `effective_speed` for hitter-perspective "
            "comparisons."
        ),
        columns=["release_speed", "effective_speed"],
    ),
    Pitfall(
        summary="Pre-2017 spin-rate data has known calibration issues.",
        explanation=(
            "Statcast's spin-rate measurement methodology changed in 2017. Comparisons across "
            "this boundary can be misleading. When trending across years, either start at 2017+ "
            "or note the caveat in your analysis."
        ),
        columns=["release_spin_rate", "game_year"],
    ),
    Pitfall(
        summary="`zone` is a coarse 1-13 region, not a continuous probability.",
        explanation=(
            "The `zone` column carries Baseball Savant's discrete strike-zone region (1-9 inside "
            "the strike zone, 11-14 outside). It is NOT a 'probability of strike' — for that, use "
            "`plate_x`/`plate_z` against `sz_top`/`sz_bot` directly."
        ),
        columns=["zone", "plate_x", "plate_z", "sz_top", "sz_bot"],
    ),
]
