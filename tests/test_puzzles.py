"""Tests for team-label Sudoku generation."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nba_db.puzzle import PuzzleEngine, solution_hash, box_index


class TeamLabelPuzzleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = PuzzleEngine(ROOT / "data" / "nba_players.sqlite")

    def test_shipped_puzzles_unique_notable_no_client_solution(self) -> None:
        puzzle_dir = ROOT / "web" / "data" / "puzzles"
        sol_dir = ROOT / "web" / "data" / "solutions"
        files = sorted(puzzle_dir.glob("puzzle_*.json"))
        self.assertGreaterEqual(len(files), 4)
        for path in files:
            payload = json.loads(path.read_text())
            self.assertNotIn("solution", payload)
            self.assertIn("solution_hash", payload)
            self.assertGreaterEqual(payload.get("notable_count", 0), 15)

            sol_path = sol_dir / path.name
            self.assertTrue(sol_path.exists(), sol_path)
            full = json.loads(sol_path.read_text())
            solution = [s["id"] for s in full["solution"]]
            self.assertEqual(payload["solution_hash"], solution_hash(solution))

            row_t = [t["key"] for t in payload["row_teams"]]
            col_t = [t["key"] for t in payload["col_teams"]]
            box_t = [t["key"] for t in payload["box_teams"]]
            bank = [b["id"] for b in payload["bank"]]
            n, sol = self.engine.count_solutions(row_t, col_t, box_t, bank, limit=2)
            self.assertEqual(n, 1, path.name)
            self.assertEqual(sol, solution)

    def test_generate_notable_unique(self) -> None:
        puzzle = self.engine.generate(seed=123, tier=1)
        self.assertGreaterEqual(puzzle.notable_count, PuzzleEngine.MIN_NOTABLE)
        n, _ = self.engine.count_solutions(
            puzzle.row_teams, puzzle.col_teams, puzzle.box_teams, puzzle.bank, limit=2
        )
        self.assertEqual(n, 1)
        self.assertEqual(box_index(3, 3), 3)


if __name__ == "__main__":
    unittest.main()
