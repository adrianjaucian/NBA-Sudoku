"""4×4 team-label Sudoku: row/col/box franchise labels are the only board clues."""

from __future__ import annotations

import hashlib
import random
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from nba_db.notable import resolve_notable_ids
from nba_db.teams import FRANCHISE_NAMES

GRID_SIZE = 4
CELL_COUNT = GRID_SIZE * GRID_SIZE
BOX_SIZE = 2

# Internal difficulty tiers (not exposed in UI; used for daily rotation later).
_TIER_FLEX: dict[int, tuple[float, float]] = {
    0: (1.0, 1.35),  # easiest
    1: (1.0, 1.55),
    2: (1.0, 2.0),
    3: (1.2, 3.5),  # hardest
}


def box_index(row: int, col: int) -> int:
    return (row // BOX_SIZE) * (GRID_SIZE // BOX_SIZE) + (col // BOX_SIZE)


def pack_team(key: str) -> dict:
    return {"key": key, "name": FRANCHISE_NAMES.get(key, key), "abbr": key}


def solution_hash(solution: list[str]) -> str:
    payload = ",".join(solution).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass
class Puzzle:
    solution: list[str]
    bank: list[str]
    row_teams: list[str]
    col_teams: list[str]
    box_teams: list[str]
    seed: int
    tier: int
    notable_count: int
    mean_flexibility: float

    def to_dict(self, players: dict[str, dict], *, include_solution: bool = False) -> dict:
        def pack_player(pid: str) -> dict:
            p = players[pid]
            return {"id": pid, "name": p["name"]}

        out: dict = {
            "seed": self.seed,
            "tier": self.tier,
            "grid_size": GRID_SIZE,
            "box_size": BOX_SIZE,
            "mode": "team_labels",
            "row_teams": [pack_team(t) for t in self.row_teams],
            "col_teams": [pack_team(t) for t in self.col_teams],
            "box_teams": [pack_team(t) for t in self.box_teams],
            "bank": [pack_player(b) for b in self.bank],
            "solution_hash": solution_hash(self.solution),
            "notable_count": self.notable_count,
        }
        if include_solution:
            out["solution"] = [pack_player(s) for s in self.solution]
        return out


class PuzzleEngine:
    """Generate unique team-label puzzles from the SQLite player DB."""

    MIN_NOTABLE = 15

    def __init__(self, db_path: Path | str) -> None:
        conn = sqlite3.connect(db_path)
        try:
            self.players: dict[str, dict] = {}
            names_by_id: dict[str, str] = {}
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
                names_by_id[pid] = name
            for pid, fk in conn.execute(
                "SELECT player_id, franchise_key FROM player_teams"
            ):
                if pid in self.players:
                    self.players[pid]["franchises"].add(fk)
        finally:
            conn.close()

        self.notable_ids = resolve_notable_ids(
            {name: pid for pid, name in names_by_id.items()}
        )
        self.by_team: dict[str, set[str]] = defaultdict(set)
        for pid, meta in self.players.items():
            for fk in meta["franchises"]:
                self.by_team[fk].add(pid)
        self.teams = sorted(self.by_team)
        # Big-market / iconic franchises first for readable puzzles
        self.popular_teams = sorted(
            self.teams, key=lambda t: len(self.by_team[t]), reverse=True
        )

    def fits(
        self, pid: str, row: int, col: int, row_t: list[str], col_t: list[str], box_t: list[str]
    ) -> bool:
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

    def _pick_teams(self, rng: random.Random) -> list[str]:
        pool = self.popular_teams[:18]
        return rng.sample(pool, 12)

    def _build_labeled_grid(
        self,
        rng: random.Random,
        *,
        prefer_notable: bool,
    ) -> tuple[list[str], list[str], list[str], list[str]] | None:
        labels = self._pick_teams(rng)
        row_t, col_t, box_t = labels[:4], labels[4:8], labels[8:]
        used: set[str] = set()
        sol: list[str] = []

        for r, c in product(range(GRID_SIZE), range(GRID_SIZE)):
            cands = [
                p
                for p in self.cell_candidates(r, c, row_t, col_t, box_t)
                if p not in used
            ]
            if not cands:
                return None

            if prefer_notable:
                notable = [p for p in cands if p in self.notable_ids]
                if notable:
                    cands = notable

            def score(pid: str) -> tuple[int, int]:
                is_notable = 0 if pid in self.notable_ids else 1
                flex = self.flexibility(pid, row_t, col_t, box_t)
                return (is_notable, flex)

            cands.sort(key=score)
            least = score(cands[0])
            top = [p for p in cands if score(p) == least]
            pick = rng.choice(top[: max(1, min(5, len(top)))])
            sol.append(pick)
            used.add(pick)

        return sol, row_t, col_t, box_t

    def generate(
        self,
        *,
        seed: int | None = None,
        tier: int | None = None,
        max_attempts: int = 6000,
    ) -> Puzzle:
        seed = random.randrange(1 << 30) if seed is None else seed
        tier = seed % 4 if tier is None else tier
        min_flex, max_flex = _TIER_FLEX.get(tier, (1.0, 2.0))
        rng = random.Random(seed)

        for attempt in range(max_attempts):
            ar = random.Random(seed + attempt * 7919)
            built = self._build_labeled_grid(ar, prefer_notable=True)
            if built is None:
                continue
            sol, row_t, col_t, box_t = built

            notable_n = sum(1 for pid in sol if pid in self.notable_ids)
            if notable_n < self.MIN_NOTABLE:
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
                solution=sol,
                bank=bank,
                row_teams=row_t,
                col_teams=col_t,
                box_teams=box_t,
                seed=seed + attempt,
                tier=tier,
                notable_count=notable_n,
                mean_flexibility=mean_flex,
            )

        raise RuntimeError(f"Could not generate notable puzzle (seed={seed}, tier={tier})")
