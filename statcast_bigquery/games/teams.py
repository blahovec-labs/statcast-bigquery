"""MLB team taxonomy: team_id -> abbreviation, league, division.

Sourced from MLB statsapi team IDs (stable across seasons). Used by the
games writer to denormalize home/away team metadata so downstream queries
can filter by AL East etc. without a separate dim_teams join.

Note: team names occasionally change (e.g. Cleveland Indians -> Guardians,
2022). Team IDs are stable; this map reflects current (post-2022) names.
For pre-2022 historical accuracy, the upstream statsapi team object
returns the contemporaneous name, but our denormalized abbrev stays current.
"""

from __future__ import annotations

from typing import Final, TypedDict


class TeamInfo(TypedDict):
    abbr: str
    league: str
    division: str
    full_name: str


MLB_TEAMS: Final[dict[int, TeamInfo]] = {
    # AL West
    133: {"abbr": "OAK", "league": "AL", "division": "West",    "full_name": "Oakland Athletics"},
    108: {"abbr": "LAA", "league": "AL", "division": "West",    "full_name": "Los Angeles Angels"},
    136: {"abbr": "SEA", "league": "AL", "division": "West",    "full_name": "Seattle Mariners"},
    140: {"abbr": "TEX", "league": "AL", "division": "West",    "full_name": "Texas Rangers"},
    117: {"abbr": "HOU", "league": "AL", "division": "West",    "full_name": "Houston Astros"},
    # AL Central
    142: {"abbr": "MIN", "league": "AL", "division": "Central", "full_name": "Minnesota Twins"},
    145: {"abbr": "CWS", "league": "AL", "division": "Central", "full_name": "Chicago White Sox"},
    114: {"abbr": "CLE", "league": "AL", "division": "Central", "full_name": "Cleveland Guardians"},
    116: {"abbr": "DET", "league": "AL", "division": "Central", "full_name": "Detroit Tigers"},
    118: {"abbr": "KC",  "league": "AL", "division": "Central", "full_name": "Kansas City Royals"},
    # AL East
    147: {"abbr": "NYY", "league": "AL", "division": "East",    "full_name": "New York Yankees"},
    110: {"abbr": "BAL", "league": "AL", "division": "East",    "full_name": "Baltimore Orioles"},
    141: {"abbr": "TOR", "league": "AL", "division": "East",    "full_name": "Toronto Blue Jays"},
    111: {"abbr": "BOS", "league": "AL", "division": "East",    "full_name": "Boston Red Sox"},
    139: {"abbr": "TB",  "league": "AL", "division": "East",    "full_name": "Tampa Bay Rays"},
    # NL West
    109: {"abbr": "ARI", "league": "NL", "division": "West", "full_name": "Arizona Diamondbacks"},
    115: {"abbr": "COL", "league": "NL", "division": "West", "full_name": "Colorado Rockies"},
    119: {"abbr": "LAD", "league": "NL", "division": "West", "full_name": "Los Angeles Dodgers"},
    135: {"abbr": "SD",  "league": "NL", "division": "West", "full_name": "San Diego Padres"},
    137: {"abbr": "SF",  "league": "NL", "division": "West", "full_name": "San Francisco Giants"},
    # NL Central
    112: {"abbr": "CHC", "league": "NL", "division": "Central", "full_name": "Chicago Cubs"},
    113: {"abbr": "CIN", "league": "NL", "division": "Central", "full_name": "Cincinnati Reds"},
    158: {"abbr": "MIL", "league": "NL", "division": "Central", "full_name": "Milwaukee Brewers"},
    134: {"abbr": "PIT", "league": "NL", "division": "Central", "full_name": "Pittsburgh Pirates"},
    138: {"abbr": "STL", "league": "NL", "division": "Central", "full_name": "St. Louis Cardinals"},
    # NL East
    144: {"abbr": "ATL", "league": "NL", "division": "East", "full_name": "Atlanta Braves"},
    146: {"abbr": "MIA", "league": "NL", "division": "East", "full_name": "Miami Marlins"},
    121: {"abbr": "NYM", "league": "NL", "division": "East", "full_name": "New York Mets"},
    143: {"abbr": "PHI", "league": "NL", "division": "East", "full_name": "Philadelphia Phillies"},
    120: {"abbr": "WSH", "league": "NL", "division": "East", "full_name": "Washington Nationals"},
}


def team_info(team_id: int) -> TeamInfo | None:
    """Look up team metadata by MLB statsapi team_id. Returns None if unknown."""
    return MLB_TEAMS.get(team_id)
