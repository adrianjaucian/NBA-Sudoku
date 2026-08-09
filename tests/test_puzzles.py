"""Tests for team-label Sudoku generation."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nba_db.puzzle import PuzzleEngine, box_index


class TeamLabelPuzzleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = PuzzleEngine(ROOT / "data" / "nba_players.sqlite")

    def test_shipped_puzzles_unique_and_consistent(self) -> None:
        puzzle_dir = ROOT / "web" / "data" / "puzzles"
        files = sorted(puzzle_dir.glob("*.json"))
        self.assertGreaterEqual(len(files), 4)
        for path in files:
            payload = json.loads(path.read_text())
            self.assertEqual(payload.get("mode"), "team_labels")
            row_t = [t["key"] for t in payload["row_teams"]]
            col_t = [t["key"] for t in payload["col_teams"]]
            box_t = [t["key"] for t in payload["box_teams"]]
            solution = [s["id"] for s in payload["solution"]]
            bank = [b["id"] for b in payload["bank"]]
            self.assertEqual(len(solution), 16)
            self.assertEqual(set(solution), set(bank))

            # Solution satisfies every cell's three labels
            for i, pid in enumerate(solution):
                r, c = divmod(i, 4)
                self.assertTrue(self.engine.fits(pid, r, c, row_t, col_t, box_t), path.name)

            n, sol = self.engine.count_solutions(row_t, col_t, box_t, bank, limit=2)
            self.assertEqual(n, 1, path.name)
            self.assertEqual(sol, solution)

    def test_generate_easy_unique(self) -> None:
        puzzle = self.engine.generate("easy", seed=123)
        n, _ = self.engine.count_solutions(
            puzzle.row_teams, puzzle.col_teams, puzzle.box_teams, puzzle.bank, limit=2
        )
        self.assertEqual(n, 1)
        self.assertEqual(len(puzzle.row_teams), 4)
        self.assertEqual(box_index(3, 3), 3)


if __name__ == "__main__":
    unittest.main()
