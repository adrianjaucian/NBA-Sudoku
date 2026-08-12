"""Scrape Basketball Reference season totals for player–team appearances."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.basketball-reference.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NBA-Sudoku-data-builder/1.0; "
        "+https://github.com/adrianjaucian/NBA-Sudoku)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Basketball Reference asks scrapers to pause ~3s between requests.
REQUEST_DELAY_SECONDS = 3.5
AGGREGATE_TEAMS = {"TOT", "2TM", "3TM", "4TM", "5TM"}
PLAYER_HREF_RE = re.compile(r"/players/[a-z]/([a-z0-9]+)\.html", re.I)


@dataclass(frozen=True)
class SeasonAppearance:
    player_id: str
    player_name: str
    team_abbrev: str
    season_end_year: int
    games: int | None


def season_label(season_end_year: int) -> str:
    """Return NBA season label like 2023-24 for ending year 2024."""
    start = season_end_year - 1
    return f"{start}-{str(season_end_year)[-2:]}"


def fetch_season_html(season_end_year: int, session: requests.Session) -> str:
    url = f"{BASE_URL}/leagues/NBA_{season_end_year}_totals.html"
    response = session.get(url, headers=HEADERS, timeout=90)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def parse_season_totals(html: str, season_end_year: int) -> list[SeasonAppearance]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="totals_stats")
    if table is None:
        # Some pages wrap the table in comments; unwrap if needed.
        for comment in soup.find_all(string=lambda t: isinstance(t, str) and "totals_stats" in t):
            commented = BeautifulSoup(comment, "lxml")
            table = commented.find("table", id="totals_stats")
            if table:
                break
    if table is None:
        raise RuntimeError(f"Could not find totals_stats table for {season_end_year}")

    appearances: list[SeasonAppearance] = []
    tbody = table.find("tbody")
    if tbody is None:
        return appearances

    for row in tbody.find_all("tr"):
        if row.get("class") and "thead" in row.get("class", []):
            continue
        player_cell = row.find("td", {"data-stat": "player"}) or row.find(
            "td", {"data-stat": "name_display"}
        )
        team_cell = row.find("td", {"data-stat": "team_name_abbr"}) or row.find(
            "td", {"data-stat": "team_id"}
        )
        if not player_cell or not team_cell:
            continue

        team_abbrev = team_cell.get_text(strip=True).upper()
        if not team_abbrev or team_abbrev in AGGREGATE_TEAMS:
            continue

        link = player_cell.find("a")
        if link is None or not link.get("href"):
            continue
        match = PLAYER_HREF_RE.search(link["href"])
        if not match:
            continue
        player_id = match.group(1)
        player_name = link.get_text(strip=True)

        games = None
        games_cell = row.find("td", {"data-stat": "games"}) or row.find(
            "td", {"data-stat": "g"}
        )
        if games_cell and games_cell.get_text(strip=True).isdigit():
            games = int(games_cell.get_text(strip=True))

        appearances.append(
            SeasonAppearance(
                player_id=player_id,
                player_name=player_name,
                team_abbrev=team_abbrev,
                season_end_year=season_end_year,
                games=games,
            )
        )
    return appearances


def scrape_seasons(
    start_end_year: int,
    end_end_year: int,
    *,
    delay: float = REQUEST_DELAY_SECONDS,
    session: requests.Session | None = None,
) -> list[SeasonAppearance]:
    """Scrape regular-season totals for seasons ending in [start, end]."""
    own_session = session is None
    session = session or requests.Session()
    all_rows: list[SeasonAppearance] = []
    try:
        years = list(range(start_end_year, end_end_year + 1))
        for i, year in enumerate(years):
            print(f"[{i + 1}/{len(years)}] Fetching {season_label(year)} ...", flush=True)
            html = fetch_season_html(year, session)
            rows = parse_season_totals(html, year)
            print(f"  → {len(rows)} player-team rows", flush=True)
            all_rows.extend(rows)
            if i < len(years) - 1:
                time.sleep(delay)
    finally:
        if own_session:
            session.close()
    return all_rows


def unique_players(appearances: Iterable[SeasonAppearance]) -> dict[str, str]:
    """Map player_id → most recent display name."""
    names: dict[str, str] = {}
    latest: dict[str, int] = {}
    for row in appearances:
        if row.player_id not in latest or row.season_end_year >= latest[row.player_id]:
            names[row.player_id] = row.player_name
            latest[row.player_id] = row.season_end_year
    return names
