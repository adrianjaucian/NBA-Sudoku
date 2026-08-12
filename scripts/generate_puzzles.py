#!/usr/bin/env python3
"""Generate team-label puzzles (notable players) and client-safe assets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nba_db.puzzle import PuzzleEngine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "nba_players.sqlite")
    parser.add_argument("--out", type=Path, default=ROOT / "web" / "data")
    parser.add_argument("--count", type=int, default=40, help="Puzzles in practice pool")
    parser.add_argument("--seed", type=int, default=20260812)
    args = parser.parse_args()

    print(f"Loading players from {args.db} ...")
    engine = PuzzleEngine(args.db)
    print(f"Notable player IDs in DB: {len(engine.notable_ids)}")

    args.out.mkdir(parents=True, exist_ok=True)
    puzzle_dir = args.out / "puzzles"
    puzzle_dir.mkdir(parents=True, exist_ok=True)
    for old in puzzle_dir.glob("*.json"):
        old.unlink()

    solutions_dir = args.out / "solutions"
    solutions_dir.mkdir(parents=True, exist_ok=True)
    for old in solutions_dir.glob("*.json"):
        old.unlink()

    catalog_entries: list[str] = []
    for i in range(args.count):
        seed = args.seed + i * 9973
        tier = i % 4
        print(f"Generating puzzle {i + 1}/{args.count} (seed={seed}, tier={tier}) ...", flush=True)
        puzzle = None
        last_err: Exception | None = None
        for bump in range(16):
            try:
                puzzle = engine.generate(seed=seed + bump * 10007, tier=tier)
                break
            except RuntimeError as err:
                last_err = err
        if puzzle is None:
            raise RuntimeError(f"Failed puzzle {i + 1}: {last_err}")

        fname = f"puzzle_{i + 1:03d}.json"
        path = puzzle_dir / fname
        client_payload = puzzle.to_dict(engine.players, include_solution=False)
        path.write_text(json.dumps(client_payload, indent=2) + "\n", encoding="utf-8")

        sol_path = solutions_dir / fname
        sol_path.write_text(
            json.dumps(puzzle.to_dict(engine.players, include_solution=True), indent=2)
            + "\n",
            encoding="utf-8",
        )

        catalog_entries.append(f"puzzles/{fname}")
        names = [engine.players[p]["name"] for p in puzzle.solution]
        print(
            f"  → tier={puzzle.tier} notable={puzzle.notable_count}/16 flex={puzzle.mean_flexibility:.2f} | "
            + " / ".join(names[:3])
            + " ...",
            flush=True,
        )

    catalog_path = args.out / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "grid_size": 4,
                "box_size": 2,
                "mode": "team_labels",
                "practice": True,
                "puzzles": catalog_entries,
                "note": "Daily Wordle-style mode will pick one puzzle per calendar day. For testing, refresh loads a random puzzle from this pool.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(catalog_entries)} puzzles → {catalog_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
