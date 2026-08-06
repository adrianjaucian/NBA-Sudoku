"""Smoke tests for teammate-Sudoku generation invariants."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from nba_db.graph import TeammateGraph
from nba_db.puzzle import GROUPS, PuzzleEngine


class PuzzleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = TeammateGraph.from_sqlite(ROOT / "data" / "nba_players.sqlite")
        cls.engine = PuzzleEngine(cls.graph)

    def test_example_row_is_clique(self) -> None:
        names = ["LeBron James", "Rajon Rondo", "Dwight Howard", "Carmelo Anthony"]
        ids = []
        for name in names:
            match = [p for p in self.graph.players.values() if p.name == name]
            self.assertTrue(match, name)
            ids.append(match[0].player_id)
        self.assertTrue(self.graph.is_clique(ids))

    def test_shipped_puzzles_are_unique(self) -> None:
        puzzle_dir = ROOT / "web" / "data" / "puzzles"
        files = sorted(puzzle_dir.glob("*.json"))
        self.assertGreaterEqual(len(files), 4)
        for path in files:
            payload = json.loads(path.read_text())
            clues = [c["id"] if c else None for c in payload["clues"]]
            bank = [b["id"] for b in payload["bank"]]
            solution = [s["id"] for s in payload["solution"]]
            self.assertEqual(len(solution), 16)
            self.assertTrue(self.engine.valid_partial_ids(solution))
            self.assertEqual(self.engine.count_solutions(clues, bank, limit=2), 1)
            # Every group in the solution is a teammate clique
            for group in GROUPS:
                self.assertTrue(self.graph.is_clique(solution[i] for i in group))


if __name__ == "__main__":
    unittest.main()
