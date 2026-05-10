"""Statcast → statsapi (MLB-StatsAPI) field-name cross-reference.

A None value means there is no statsapi equivalent. Useful for hobbyists
straddling both ecosystems.
"""

from __future__ import annotations

STATCAST_TO_STATSAPI_MAP: dict[str, str | None] = {
    # Identifiers
    "game_pk": "gamePk",
    "game_date": "gameDate",
    "game_year": "season",
    "game_type": "gameType",
    "at_bat_number": "atBatIndex",
    "pitch_number": "pitchNumber",
    "sv_id": None,
    "batter": "matchup.batter.id",
    "pitcher": "matchup.pitcher.id",
    "player_name": "fullName",
    "fielder_2": None,
    "fielder_3": None,
    "fielder_4": None,
    "fielder_5": None,
    "fielder_6": None,
    "fielder_7": None,
    "fielder_8": None,
    "fielder_9": None,
    "home_team": "teams.home.team.abbreviation",
    "away_team": "teams.away.team.abbreviation",
    "umpire": None,
    # Pitch context
    "balls": "count.balls.start",
    "strikes": "count.strikes.start",
    "outs_when_up": "count.outs.start",
    "inning": "about.inning",
    "inning_topbot": "about.halfInning",
    # Outcomes
    "events": "result.eventType",
    "description": "details.description",
    "des": "result.description",
    # Pitch physics
    "release_speed": "pitchData.startSpeed",
    "release_spin_rate": "pitchData.breaks.spinRate",
    "release_extension": "pitchData.extension",
    "pitch_type": "details.type.code",
    "vx0": "pitchData.coordinates.vX0",
    "vy0": "pitchData.coordinates.vY0",
    "vz0": "pitchData.coordinates.vZ0",
    "ax": "pitchData.coordinates.aX",
    "ay": "pitchData.coordinates.aY",
    "az": "pitchData.coordinates.aZ",
    "pfx_x": "pitchData.breaks.breakingBalls.x",
    "pfx_z": "pitchData.breaks.breakingBalls.z",
    # Plate location
    "plate_x": "pitchData.coordinates.pX",
    "plate_z": "pitchData.coordinates.pZ",
    "sz_top": "pitchData.strikeZoneTop",
    "sz_bot": "pitchData.strikeZoneBottom",
    "zone": "details.zone",
    # Score state
    "home_score": "result.homeScore",
    "away_score": "result.awayScore",
    "bat_score": "liveData.linescore.teams.away.runs",
    "fld_score": "liveData.linescore.teams.home.runs",
    # Batted ball (no statsapi equivalent)
    "launch_speed": None,
    "launch_angle": None,
    "hit_distance_sc": None,
    "estimated_woba_using_speedangle": None,
    "estimated_ba_using_speedangle": None,
    "estimated_slg_using_speedangle": None,
    "bat_speed": None,
    "swing_length": None,
    "hc_x": None,
    "hc_y": None,
    "hit_location": None,
    # Runner state
    "on_1b": None,
    "on_2b": None,
    "on_3b": None,
    "sprint_speed": None,
    # Misc
    "stand": "matchup.batSide.code",
    "p_throws": "matchup.pitchHand.code",
    "post_home_score": None,
    "post_away_score": None,
    "post_bat_score": None,
    "post_fld_score": None,
}
