#!/usr/bin/env python3
"""Generate team-label Sudoku puzzles and client data assets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nba_db.puzzle import DIFFICULTY_CONFIG, Difficulty, PuzzleEngine
from nba_db.teams import FRANCHISE_NAMES


def export_players_json(engine: PuzzleEngine, path: Path) -> None:
    """Compact player → franchises map for the browser."""
    payload = {
        "teams": [
            {"key": k, "name": FRANCHISE_NAMES.get(k, k), "abbr": k}
            for k in engine.teams
        ],
        "players": [
            {
                "id": pid,
                "name": meta["name"],
                "team_count": meta["team_count"],
                "first_season": meta["first_season"],
                "last_season": meta["last_season"],
                "teams": sorted(meta["franchises"]),
            }
            for pid, meta in sorted(engine.players.items(), key=lambda x: x[1]["name"])
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "nba_players.sqlite")
    parser.add_argument("--out", type=Path, default=ROOT / "web" / "data")
    parser.add_argument("--per-difficulty", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260809)
    args = parser.parse_args()

    print(f"Loading players from {args.db} ...")
    engine = PuzzleEngine(args.db)
    args.out.mkdir(parents=True, exist_ok=True)

    players_path = args.out / "players.json"
    print(f"Writing {players_path} ...")
    export_players_json(engine, players_path)

    catalog: dict[str, list[str]] = {d: [] for d in DIFFICULTY_CONFIG}
    difficulties: list[Difficulty] = ["easy", "medium", "hard", "expert"]
    descriptions = {
        "easy": "Team labels only · mostly modern players · tighter cells",
        "medium": "Team labels only · mix of eras",
        "hard": "Team labels only · obscure teams · journeymen",
        "expert": "Team labels only · highest ambiguity still unique",
    }

    puzzle_dir = args.out / "puzzles"
    puzzle_dir.mkdir(parents=True, exist_ok=True)
    # Clear old puzzle format files
    for old in puzzle_dir.glob("*.json"):
        old.unlink()

    for diff in difficulties:
        for i in range(args.per_difficulty):
            seed = args.seed + (hash(diff) % 100000) + i * 19
            print(f"Generating {diff} #{i + 1} (seed={seed}) ...", flush=True)
            puzzle = None
            last_err: Exception | None = None
            for bump in range(12):
                try:
                    puzzle = engine.generate(diff, seed=seed + bump * 10007)
                    break
                except RuntimeError as err:
                    last_err = err
                    print(f"  retry {bump + 1}: {err}", flush=True)
            if puzzle is None:
                raise RuntimeError(f"Failed {diff} #{i + 1}: {last_err}")

            fname = f"{diff}_{i + 1:02d}.json"
            path = puzzle_dir / fname
            path.write_text(
                json.dumps(puzzle.to_dict(engine.players), indent=2) + "\n",
                encoding="utf-8",
            )
            catalog[diff].append(f"puzzles/{fname}")
            names = [engine.players[p]["name"] for p in puzzle.solution]
            print(
                f"  → flex={puzzle.mean_flexibility:.2f} | "
                f"rows={puzzle.row_teams} | {names[0]} / {names[1]} / ...",
                flush=True,
            )

    catalog_path = args.out / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "grid_size": 4,
                "box_size": 2,
                "mode": "team_labels",
                "difficulties": {
                    k: {
                        "puzzles": v,
                        "description": descriptions[k],
                    }
                    for k, v in catalog.items()
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote catalog → {catalog_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
