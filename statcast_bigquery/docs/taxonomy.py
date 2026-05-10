"""Semantic groupings of Statcast columns. Used by renderers to organize output."""

from __future__ import annotations

from statcast_bigquery.schema import PITCHES_SCHEMA, ColumnSpec

SEMANTIC_GROUPS: dict[str, str] = {
    "identifier": "Stable IDs and join keys (game_pk, batter, pitcher, ...)",
    "pitch_context": "Game state at pitch time (balls, strikes, inning, runners, outs)",
    "pitch_physics": "Pitch trajectory and spin (release_speed, spin_rate, pfx, vx0/vy0/vz0)",
    "pitch_location": "Plate-crossing point + strike zone (plate_x, plate_z, sz_top, sz_bot, zone)",
    "outcome_pitch": "Per-pitch outcome (description, type)",
    "outcome_at_bat": "Per-AB outcome (events, hit_distance_sc)",
    "batted_ball": "Batted-ball metrics (launch_speed, launch_angle, hit_location)",
    "expected_stats": "Statcast expected stats (xBA, xwOBA, xSLG)",
    "runner": "Baserunners + sprint speed (on_1b/2b/3b, sprint_speed)",
    "score_state": "Score before/after pitch (home_score, post_*_score, bat_score, fld_score)",
    "temporal": "Calendar fields (game_date, game_year)",
    "team": "Team identifiers (home_team, away_team)",
    "handedness": "Batter / pitcher handedness (stand, p_throws)",
    "physics": "Catch-all for low-level physics (compatible with pitch_physics)",
    "post_hit": "Post-contact metrics (synonym used on batted-ball columns)",
    "join_key": "Subset of identifier — explicit join columns",
    "mlb_canonical": "Subset — values that match MLB's canonical scheme",
}


def columns_in_group(group: str) -> list[ColumnSpec]:
    """Return all PITCHES_SCHEMA entries tagged with `group`."""
    return [c for c in PITCHES_SCHEMA if group in c.semantic_tags]
