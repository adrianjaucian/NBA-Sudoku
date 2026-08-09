"""4×4 team-label Sudoku: row/col/box franchise labels are the only board clues."""

from __future__ import annotations

import random
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Literal

from nba_db.teams import FRANCHISE_NAMES

GRID_SIZE = 4
CELL_COUNT = GRID_SIZE * GRID_SIZE
BOX_SIZE = 2

Difficulty = Literal["easy", "medium", "hard", "expert"]

DIFFICULTY_CONFIG: dict[Difficulty, dict] = {
    "easy": {
        "modern_only": True,
        "modern_year": 2000,
        "prefer_journeymen": False,
        "prefer_obscure_teams": False,
        "max_mean_flexibility": 2.2,
    },
    "medium": {
        "modern_only": False,
        "modern_year": 2000,
        "prefer_journeymen": False,
        "prefer_obscure_teams": False,
        "require_era_mix": True,
        "max_mean_flexibility": 3.0,
    },
    "hard": {
        "modern_only": False,
        "modern_year": 2000,
        "prefer_journeymen": True,
        "prefer_obscure_teams": True,
        "min_journeymen": 6,
        "max_mean_flexibility": 3.5,
    },
    "expert": {
        "modern_only": False,
        "modern_year": 2000,
        "prefer_journeymen": False,
        "prefer_obscure_teams": True,
        "max_mean_flexibility": 6.0,
        "min_mean_flexibility": 1.4,
        "prefer_flexible_picks": True,
    },
}


def box_index(row: int, col: int) -> int:
    return (row // BOX_SIZE) * (GRID_SIZE // BOX_SIZE) + (col // BOX_SIZE)


def pack_team(key: str) -> dict:
    return {"key": key, "name": FRANCHISE_NAMES.get(key, key), "abbr": key}


@dataclass
class Puzzle:
    difficulty: Difficulty
    solution: list[str]
    bank: list[str]
    row_teams: list[str]
    col_teams: list[str]
    box_teams: list[str]
    seed: int
    mean_flexibility: float

    def to_dict(self, players: dict[str, dict]) -> dict:
        def pack_player(pid: str) -> dict:
            p = players[pid]
            return {
                "id": pid,
                "name": p["name"],
                "team_count": p["team_count"],
                "first_season": p["first_season"],
                "last_season": p["last_season"],
                "teams": sorted(p["franchises"]),
            }

        return {
            "difficulty": self.difficulty,
            "seed": self.seed,
            "grid_size": GRID_SIZE,
            "box_size": BOX_SIZE,
            "mode": "team_labels",
            "row_teams": [pack_team(t) for t in self.row_teams],
            "col_teams": [pack_team(t) for t in self.col_teams],
            "box_teams": [pack_team(t) for t in self.box_teams],
            "clues": [None] * CELL_COUNT,  # no pre-filled players
            "solution": [pack_player(s) for s in self.solution],
            "bank": [pack_player(b) for b in self.bank],
            "mean_flexibility": round(self.mean_flexibility, 3),
            "rules": (
                "Team labels on each row, column, and 2×2 box are the only clues. "
                "A player belongs in a cell only if they played for that cell's "
                "row team, column team, and box team. Use each bank player once. "
                "Each puzzle has exactly one solution."
            ),
        }


class PuzzleEngine:
    """Generate unique team-label puzzles from the SQLite player DB."""

    def __init__(self, db_path: Path | str) -> None:
        conn = sqlite3.connect(db_path)
        try:
            self.players: dict[str, dict] = {}
            for pid, name, first, last, tc in conn.execute(
                """
                SELECT player_id, player_name, first_season, last_season, team_count
                FROM players
                """
            ):
                self.players[pid] = {
                    "name": name,
                    "first_season": first,
                    "last_season": last,
                    "team_count": tc,
                    "franchises": set(),
                    "era_start": int(first.split("-")[0]),
                    "era_end": int(last.split("-")[0]),
                }
            for pid, fk in conn.execute(
                "SELECT player_id, franchise_key FROM player_teams"
            ):
                if pid in self.players:
                    self.players[pid]["franchises"].add(fk)
        finally:
            conn.close()

        self.by_team: dict[str, set[str]] = defaultdict(set)
        for pid, meta in self.players.items():
            for fk in meta["franchises"]:
                self.by_team[fk].add(pid)
        self.teams = sorted(self.by_team)
        self.teams_by_size = sorted(self.teams, key=lambda t: len(self.by_team[t]))

    def fits(self, pid: str, row: int, col: int, row_t: list[str], col_t: list[str], box_t: list[str]) -> bool:
        f = self.players[pid]["franchises"]
        return (
            row_t[row] in f
            and col_t[col] in f
            and box_t[box_index(row, col)] in f
        )

    def cell_candidates(
        self, row: int, col: int, row_t: list[str], col_t: list[str], box_t: list[str]
    ) -> set[str]:
        return (
            self.by_team[row_t[row]]
            & self.by_team[col_t[col]]
            & self.by_team[box_t[box_index(row, col)]]
        )

    def flexibility(self, pid: str, row_t: list[str], col_t: list[str], box_t: list[str]) -> int:
        return sum(
            1
            for r, c in product(range(GRID_SIZE), range(GRID_SIZE))
            if self.fits(pid, r, c, row_t, col_t, box_t)
        )

    def count_solutions(
        self,
        row_t: list[str],
        col_t: list[str],
        box_t: list[str],
        bank: list[str],
        *,
        limit: int = 2,
    ) -> tuple[int, list[str] | None]:
        cands: list[list[str]] = [[] for _ in range(CELL_COUNT)]
        for r, c in product(range(GRID_SIZE), range(GRID_SIZE)):
            i = r * GRID_SIZE + c
            for pid in bank:
                if self.fits(pid, r, c, row_t, col_t, box_t):
                    cands[i].append(pid)
            if not cands[i]:
                return 0, None

        grid: list[str | None] = [None] * CELL_COUNT
        used: set[str] = set()
        found = 0
        solution: list[str] | None = None

        def bt() -> None:
            nonlocal found, solution
            if found >= limit:
                return
            best_i = None
            best: list[str] | None = None
            for i in range(CELL_COUNT):
                if grid[i] is not None:
                    continue
                opts = [p for p in cands[i] if p not in used]
                if best is None or len(opts) < len(best):
                    best = opts
                    best_i = i
                    if not opts:
                        break
            if best_i is None:
                found += 1
                if solution is None:
                    solution = [p for p in grid if p is not None]  # type: ignore[misc]
                return
            assert best is not None
            if not best:
                return
            for pid in best:
                grid[best_i] = pid
                used.add(pid)
                bt()
                used.remove(pid)
                grid[best_i] = None
                if found >= limit:
                    return

        bt()
        return found, solution

    def _pick_teams(self, rng: random.Random, obscure: bool) -> list[str]:
        if obscure:
            # Bias toward smaller franchises in the DB (harder intersections)
            pool = self.teams_by_size[:22] + self.teams_by_size[-10:]
            pool = list(dict.fromkeys(pool))
            return rng.sample(pool, 12)
        # Prefer well-known / larger franchises
        pool = self.teams_by_size[-20:]
        return rng.sample(pool, 12)

    def _build_labeled_grid(
        self,
        rng: random.Random,
        *,
        obscure: bool,
        player_filter,
        prefer_flexible_picks: bool = False,
    ) -> tuple[list[str], list[str], list[str], list[str]] | None:
        labels = self._pick_teams(rng, obscure=obscure)
        row_t, col_t, box_t = labels[:4], labels[4:8], labels[8:]
        used: set[str] = set()
        sol: list[str] = []

        for r, c in product(range(GRID_SIZE), range(GRID_SIZE)):
            cands = [
                p
                for p in self.cell_candidates(r, c, row_t, col_t, box_t)
                if p not in used and player_filter(p)
            ]
            if not cands:
                return None

            def flex(pid: str) -> int:
                return self.flexibility(pid, row_t, col_t, box_t)

            cands.sort(key=flex, reverse=prefer_flexible_picks)
            if prefer_flexible_picks:
                # Bias toward players who could fit multiple cells (harder)
                top = cands[: max(3, min(8, len(cands)))]
            else:
                least = flex(cands[0])
                top = [p for p in cands if flex(p) == least]
                top = top[: max(1, min(4, len(top)))]
            pick = rng.choice(top)
            sol.append(pick)
            used.add(pick)

        return sol, row_t, col_t, box_t

    def generate(
        self,
        difficulty: Difficulty,
        *,
        seed: int | None = None,
        max_attempts: int = 4000,
    ) -> Puzzle:
        cfg = DIFFICULTY_CONFIG[difficulty]
        seed = random.randrange(1 << 30) if seed is None else seed
        rng = random.Random(seed)

        modern_only = bool(cfg.get("modern_only"))
        modern_year = int(cfg.get("modern_year", 2000))
        prefer_j = bool(cfg.get("prefer_journeymen"))
        obscure = bool(cfg.get("prefer_obscure_teams"))
        min_j = int(cfg.get("min_journeymen", 0))
        require_era_mix = bool(cfg.get("require_era_mix"))
        max_flex = float(cfg.get("max_mean_flexibility", 99))
        min_flex = float(cfg.get("min_mean_flexibility", 0))
        prefer_flexible = bool(cfg.get("prefer_flexible_picks"))

        def player_filter(pid: str) -> bool:
            p = self.players[pid]
            if modern_only and p["era_end"] < modern_year and p["era_start"] < modern_year:
                return False
            return True

        for attempt in range(max_attempts):
            ar = random.Random(seed + attempt * 7919)
            built = self._build_labeled_grid(
                ar,
                obscure=obscure,
                player_filter=player_filter,
                prefer_flexible_picks=prefer_flexible,
            )
            if built is None:
                continue
            sol, row_t, col_t, box_t = built

            if prefer_j:
                journey = sum(
                    1 for pid in sol if 6 <= self.players[pid]["team_count"] <= 10
                )
                if journey < min_j:
                    continue

            if require_era_mix:
                older = sum(1 for pid in sol if self.players[pid]["era_start"] < 2000)
                newer = sum(1 for pid in sol if self.players[pid]["era_end"] >= 2010)
                if older < 2 or newer < 2:
                    continue

            if modern_only:
                if any(self.players[pid]["era_end"] < modern_year for pid in sol):
                    # allow if they also started modern era games
                    if any(
                        self.players[pid]["era_start"] < modern_year
                        and self.players[pid]["era_end"] < modern_year
                        for pid in sol
                    ):
                        continue

            n, _ = self.count_solutions(row_t, col_t, box_t, sol, limit=2)
            if n != 1:
                continue

            mean_flex = sum(self.flexibility(p, row_t, col_t, box_t) for p in sol) / 16
            if mean_flex > max_flex or mean_flex < min_flex:
                continue

            bank = sol[:]
            ar.shuffle(bank)
            return Puzzle(
                difficulty=difficulty,
                solution=sol,
                bank=bank,
                row_teams=row_t,
                col_teams=col_t,
                box_teams=box_t,
                seed=seed + attempt,
                mean_flexibility=mean_flex,
            )

        raise RuntimeError(f"Could not generate {difficulty} team-label puzzle (seed={seed})")
