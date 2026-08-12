"""NBA franchise and abbreviation helpers.

Franchise keys collapse relocating / rebranded clubs so a player who only
moved with a franchise (e.g. SuperSonics → Thunder) is not counted as having
played for two different teams.
"""

from __future__ import annotations

# Abbreviation as shown on Basketball Reference → stable franchise key
ABBREV_TO_FRANCHISE: dict[str, str] = {
    # Atlantic
    "BOS": "BOS",
    "BKN": "BKN",
    "BRK": "BKN",
    "NJN": "BKN",
    "NYA": "BKN",  # ABA Nets (rare in post-1980 BBRef dumps)
    "NYN": "BKN",
    "NYK": "NYK",
    "PHI": "PHI",
    "TOR": "TOR",
    # Central
    "CHI": "CHI",
    "CLE": "CLE",
    "DET": "DET",
    "IND": "IND",
    "MIL": "MIL",
    # Southeast
    "ATL": "ATL",
    "CHA": "CHA",
    "CHH": "CHA",
    "CHO": "CHA",
    "MIA": "MIA",
    "ORL": "ORL",
    "WAS": "WAS",
    "WSB": "WAS",
    "BAL": "WAS",
    "CAP": "WAS",
    # Northwest
    "DEN": "DEN",
    "MIN": "MIN",
    "OKC": "OKC",
    "SEA": "OKC",
    "POR": "POR",
    "UTA": "UTA",
    "NOJ": "UTA",
    # Pacific
    "GSW": "GSW",
    "GOS": "GSW",
    "SFW": "GSW",
    "PHW": "GSW",
    "LAC": "LAC",
    "SDC": "LAC",
    "BUF": "LAC",
    "LAL": "LAL",
    "MNL": "LAL",
    "PHO": "PHX",
    "PHX": "PHX",
    "SAC": "SAC",
    "KCK": "SAC",
    "KCO": "SAC",
    "CIN": "SAC",
    "ROC": "SAC",
    # Southwest
    "DAL": "DAL",
    "HOU": "HOU",
    "SDR": "HOU",
    "MEM": "MEM",
    "VAN": "MEM",
    "NOP": "NOP",
    "NOH": "NOP",
    "NOK": "NOP",  # New Orleans/Oklahoma City Hornets
    "SAS": "SAS",
}

# Canonical display name for each franchise key (current identity)
FRANCHISE_NAMES: dict[str, str] = {
    "ATL": "Atlanta Hawks",
    "BKN": "Brooklyn Nets",
    "BOS": "Boston Celtics",
    "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",
    "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks",
    "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors",
    "HOU": "Houston Rockets",
    "IND": "Indiana Pacers",
    "LAC": "LA Clippers",
    "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",
    "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans",
    "NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers",
    "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",
    "WAS": "Washington Wizards",
}

# Historical / alternate abbreviation display labels
ABBREV_NAMES: dict[str, str] = {
    "ATL": "Atlanta Hawks",
    "BKN": "Brooklyn Nets",
    "BRK": "Brooklyn Nets",
    "NJN": "New Jersey Nets",
    "BOS": "Boston Celtics",
    "CHA": "Charlotte Hornets",
    "CHH": "Charlotte Hornets",
    "CHO": "Charlotte Hornets",
    "CHI": "Chicago Bulls",
    "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks",
    "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors",
    "HOU": "Houston Rockets",
    "IND": "Indiana Pacers",
    "LAC": "LA Clippers",
    "SDC": "San Diego Clippers",
    "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies",
    "VAN": "Vancouver Grizzlies",
    "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",
    "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans",
    "NOH": "New Orleans Hornets",
    "NOK": "New Orleans/Oklahoma City Hornets",
    "NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder",
    "SEA": "Seattle SuperSonics",
    "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers",
    "PHO": "Phoenix Suns",
    "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings",
    "KCK": "Kansas City Kings",
    "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",
    "WAS": "Washington Wizards",
    "WSB": "Washington Bullets",
}


def franchise_key(abbrev: str) -> str:
    """Return stable franchise key for a Basketball Reference team abbreviation."""
    key = abbrev.strip().upper()
    if key in ("TOT", "2TM", "3TM", "4TM", "5TM"):
        raise ValueError(f"Aggregate row abbreviation is not a franchise: {abbrev}")
    return ABBREV_TO_FRANCHISE.get(key, key)


def team_display_name(abbrev: str) -> str:
    """Human-readable name for a season abbreviation."""
    key = abbrev.strip().upper()
    return ABBREV_NAMES.get(key, FRANCHISE_NAMES.get(franchise_key(key), key))
