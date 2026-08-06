#!/usr/bin/env python3
"""Generate teammate-Sudoku puzzles and client graph assets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nba_db.graph import TeammateGraph, save_graph_json
from nba_db.puzzle import DIFFICULTY_CONFIG, Difficulty, PuzzleEngine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=ROOT / "data" / "nba_players.sqlite",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "web" / "data",
    )
    parser.add_argument(
        "--per-difficulty",
        type=int,
        default=5,
        help="Number of puzzles to generate per difficulty",
    )
    parser.add_argument("--seed", type=int, default=20260806)
    args = parser.parse_args()

    print(f"Loading graph from {args.db} ...")
    graph = TeammateGraph.from_sqlite(args.db)
    engine = PuzzleEngine(graph)
    args.out.mkdir(parents=True, exist_ok=True)

    # Full graph for client-side validation / tooltips (ids + edges only)
    graph_path = args.out / "teammate_graph.json"
    print(f"Writing {graph_path} ...")
    save_graph_json(graph, graph_path)

    catalog: dict[str, list[str]] = {d: [] for d in DIFFICULTY_CONFIG}
    difficulties: list[Difficulty] = ["easy", "medium", "hard", "expert"]

    for diff in difficulties:
        for i in range(args.per_difficulty):
            seed = args.seed + hash(diff) % 100000 + i * 17
            print(f"Generating {diff} #{i + 1} (seed={seed}) ...", flush=True)
            puzzle = None
            last_err: Exception | None = None
            for bump in range(8):
                try:
                    puzzle = engine.generate(diff, seed=seed + bump * 10007)
                    break
                except RuntimeError as err:
                    last_err = err
                    print(f"  retry {bump + 1}: {err}", flush=True)
            if puzzle is None:
                raise RuntimeError(f"Failed {diff} #{i + 1}: {last_err}")
            fname = f"{diff}_{i + 1:02d}.json"
            path = args.out / "puzzles" / fname
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = puzzle.to_dict(graph)
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            catalog[diff].append(f"puzzles/{fname}")
            names = [graph.players[p].name for p in puzzle.solution]
            print(
                f"  → {puzzle.clue_count} clues | "
                + " / ".join(names[:4])
                + " ...",
                flush=True,
            )

    catalog_path = args.out / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "grid_size": 4,
                "box_size": 2,
                "difficulties": {
                    k: {
                        "clues": DIFFICULTY_CONFIG[k]["clues"],  # type: ignore[index]
                        "puzzles": v,
                        "description": {
                            "easy": "8 clues · mostly modern players (2000+)",
                            "medium": "6 clues · mix of eras",
                            "hard": "4 clues · journeymen with 6–10 teams",
                            "expert": "3 clues · full teammate graph",
                        }[k],
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
