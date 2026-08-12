#!/usr/bin/env python3
"""Build the NBA players (3+ teams, 1980–present) database from Basketball Reference."""

from __future__ import annotations

import argparse
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nba_db.build import build_records, write_exports, write_sqlite
from nba_db.scrape import scrape_seasons


def current_season_end_year(now: datetime | None = None) -> int:
    """NBA season ending year for 'now' (season starts in October)."""
    now = now or datetime.now(timezone.utc)
    return now.year + 1 if now.month >= 10 else now.year


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=1980, help="First season ending year (default: 1980)")
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Last season ending year (default: current NBA season)",
    )
    parser.add_argument("--min-teams", type=int, default=3, help="Minimum distinct franchises (default: 3)")
    parser.add_argument(
        "--cache",
        type=Path,
        default=ROOT / "data" / "raw_appearances.pkl",
        help="Optional pickle cache of scraped appearances",
    )
    parser.add_argument("--use-cache", action="store_true", help="Reuse cached scrape if present")
    parser.add_argument("--delay", type=float, default=3.5, help="Seconds between BBRef requests")
    args = parser.parse_args()

    end_year = args.end_year or current_season_end_year()
    data_dir = ROOT / "data"

    if args.use_cache and args.cache.exists():
        print(f"Loading cached appearances from {args.cache}")
        appearances = pickle.loads(args.cache.read_bytes())
    else:
        appearances = scrape_seasons(args.start_year, end_year, delay=args.delay)
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        args.cache.write_bytes(pickle.dumps(appearances))
        print(f"Cached {len(appearances)} appearances → {args.cache}")

    players, player_teams, teams = build_records(appearances, min_teams=args.min_teams)
    meta = {
        "source": "Basketball Reference season totals",
        "source_url": "https://www.basketball-reference.com/leagues/",
        "start_season_end_year": str(args.start_year),
        "end_season_end_year": str(end_year),
        "min_teams": str(args.min_teams),
        "built_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "appearance_rows": str(len(appearances)),
        "player_count": str(len(players)),
        "notes": (
            "Players with at least min_teams distinct NBA franchises in regular-season "
            "games from the start season through the end season. Relocations/rebrands "
            "(e.g. SEA→OKC, NJN→BKN) count as one franchise."
        ),
    }

    db_path = data_dir / "nba_players.sqlite"
    write_sqlite(db_path, appearances, players, player_teams, teams, meta=meta)
    write_exports(data_dir, players, teams, meta)

    print(f"\nBuilt database with {len(players)} players (≥{args.min_teams} teams).")
    print(f"  SQLite: {db_path}")
    print(f"  JSON:   {data_dir / 'players_3plus_teams.json'}")
    print(f"  CSV:    {data_dir / 'players_3plus_teams.csv'}")
    if players:
        top = players[0]
        print(f"  Most teams: {top['player_name']} ({top['team_count']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
