"""Build and query the NBA multi-team player database."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from nba_db.scrape import SeasonAppearance, season_label, unique_players
from nba_db.teams import FRANCHISE_NAMES, franchise_key, team_display_name


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    player_id TEXT PRIMARY KEY,
    player_name TEXT NOT NULL,
    first_season TEXT NOT NULL,
    last_season TEXT NOT NULL,
    team_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    franchise_key TEXT PRIMARY KEY,
    franchise_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS player_teams (
    player_id TEXT NOT NULL REFERENCES players(player_id),
    franchise_key TEXT NOT NULL REFERENCES teams(franchise_key),
    abbreviations TEXT NOT NULL,
    first_season TEXT NOT NULL,
    last_season TEXT NOT NULL,
    seasons_played INTEGER NOT NULL,
    PRIMARY KEY (player_id, franchise_key)
);

CREATE TABLE IF NOT EXISTS appearances (
    player_id TEXT NOT NULL,
    franchise_key TEXT NOT NULL,
    team_abbrev TEXT NOT NULL,
    season_end_year INTEGER NOT NULL,
    season TEXT NOT NULL,
    games INTEGER,
    PRIMARY KEY (player_id, team_abbrev, season_end_year)
);

CREATE INDEX IF NOT EXISTS idx_players_team_count ON players(team_count DESC);
CREATE INDEX IF NOT EXISTS idx_player_teams_franchise ON player_teams(franchise_key);
"""


def build_records(
    appearances: list[SeasonAppearance],
    *,
    min_teams: int = 3,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Aggregate appearances into filtered players / player_teams / teams."""
    names = unique_players(appearances)

    # player_id → franchise_key → list of (abbrev, year, games)
    by_player: dict[str, dict[str, list[tuple[str, int, int | None]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in appearances:
        try:
            key = franchise_key(row.team_abbrev)
        except ValueError:
            continue
        by_player[row.player_id][key].append(
            (row.team_abbrev, row.season_end_year, row.games)
        )

    players_out: list[dict[str, Any]] = []
    player_teams_out: list[dict[str, Any]] = []
    teams_used: set[str] = set()

    for player_id, franchises in by_player.items():
        if len(franchises) < min_teams:
            continue

        all_years = [
            year
            for stints in franchises.values()
            for (_, year, _) in stints
        ]
        first_year = min(all_years)
        last_year = max(all_years)

        teams_payload = []
        for fkey, stints in sorted(franchises.items(), key=lambda x: min(s[1] for s in x[1])):
            abbrevs = sorted({a for a, _, _ in stints})
            years = [y for _, y, _ in stints]
            teams_used.add(fkey)
            entry = {
                "franchise_key": fkey,
                "franchise_name": FRANCHISE_NAMES.get(fkey, fkey),
                "abbreviations": abbrevs,
                "abbreviation_names": [team_display_name(a) for a in abbrevs],
                "first_season": season_label(min(years)),
                "last_season": season_label(max(years)),
                "seasons_played": len({y for _, y, _ in stints}),
            }
            teams_payload.append(entry)
            player_teams_out.append({"player_id": player_id, **entry})

        players_out.append(
            {
                "player_id": player_id,
                "player_name": names[player_id],
                "first_season": season_label(first_year),
                "last_season": season_label(last_year),
                "team_count": len(franchises),
                "teams": teams_payload,
                "team_names": [t["franchise_name"] for t in teams_payload],
                "bbref_url": f"https://www.basketball-reference.com/players/{player_id[0]}/{player_id}.html",
            }
        )

    players_out.sort(key=lambda p: (-p["team_count"], p["player_name"]))
    teams_out = [
        {"franchise_key": k, "franchise_name": FRANCHISE_NAMES.get(k, k)}
        for k in sorted(teams_used)
    ]
    return players_out, player_teams_out, teams_out


def write_sqlite(
    db_path: Path,
    appearances: list[SeasonAppearance],
    players: list[dict[str, Any]],
    player_teams: list[dict[str, Any]],
    teams: list[dict[str, Any]],
    *,
    meta: dict[str, str],
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.executemany(
            "INSERT INTO meta(key, value) VALUES (?, ?)",
            list(meta.items()),
        )
        conn.executemany(
            "INSERT INTO teams(franchise_key, franchise_name) VALUES (:franchise_key, :franchise_name)",
            teams,
        )
        conn.executemany(
            """
            INSERT INTO players(player_id, player_name, first_season, last_season, team_count)
            VALUES (:player_id, :player_name, :first_season, :last_season, :team_count)
            """,
            [
                {
                    "player_id": p["player_id"],
                    "player_name": p["player_name"],
                    "first_season": p["first_season"],
                    "last_season": p["last_season"],
                    "team_count": p["team_count"],
                }
                for p in players
            ],
        )
        conn.executemany(
            """
            INSERT INTO player_teams(
                player_id, franchise_key, abbreviations, first_season, last_season, seasons_played
            ) VALUES (
                :player_id, :franchise_key, :abbreviations, :first_season, :last_season, :seasons_played
            )
            """,
            [
                {
                    **pt,
                    "abbreviations": ",".join(pt["abbreviations"]),
                }
                for pt in player_teams
            ],
        )

        keep_ids = {p["player_id"] for p in players}
        appearance_rows = []
        for row in appearances:
            if row.player_id not in keep_ids:
                continue
            try:
                fkey = franchise_key(row.team_abbrev)
            except ValueError:
                continue
            appearance_rows.append(
                {
                    "player_id": row.player_id,
                    "franchise_key": fkey,
                    "team_abbrev": row.team_abbrev,
                    "season_end_year": row.season_end_year,
                    "season": season_label(row.season_end_year),
                    "games": row.games,
                }
            )
        conn.executemany(
            """
            INSERT OR IGNORE INTO appearances(
                player_id, franchise_key, team_abbrev, season_end_year, season, games
            ) VALUES (
                :player_id, :franchise_key, :team_abbrev, :season_end_year, :season, :games
            )
            """,
            appearance_rows,
        )
        conn.commit()
    finally:
        conn.close()


def write_exports(
    data_dir: Path,
    players: list[dict[str, Any]],
    teams: list[dict[str, Any]],
    meta: dict[str, str],
) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "meta": meta,
        "player_count": len(players),
        "players": players,
        "teams": teams,
    }
    json_path = data_dir / "players_3plus_teams.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Flat CSV: one row per player with teams as pipe-separated list
    import csv

    csv_path = data_dir / "players_3plus_teams.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "player_id",
                "player_name",
                "first_season",
                "last_season",
                "team_count",
                "teams",
                "bbref_url",
            ],
        )
        writer.writeheader()
        for p in players:
            writer.writerow(
                {
                    "player_id": p["player_id"],
                    "player_name": p["player_name"],
                    "first_season": p["first_season"],
                    "last_season": p["last_season"],
                    "team_count": p["team_count"],
                    "teams": " | ".join(p["team_names"]),
                    "bbref_url": p["bbref_url"],
                }
            )

    # Junction CSV
    junction_path = data_dir / "player_teams.csv"
    with junction_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "player_id",
                "player_name",
                "franchise_key",
                "franchise_name",
                "abbreviations",
                "first_season",
                "last_season",
                "seasons_played",
            ],
        )
        writer.writeheader()
        for p in players:
            for t in p["teams"]:
                writer.writerow(
                    {
                        "player_id": p["player_id"],
                        "player_name": p["player_name"],
                        "franchise_key": t["franchise_key"],
                        "franchise_name": t["franchise_name"],
                        "abbreviations": ",".join(t["abbreviations"]),
                        "first_season": t["first_season"],
                        "last_season": t["last_season"],
                        "seasons_played": t["seasons_played"],
                    }
                )
