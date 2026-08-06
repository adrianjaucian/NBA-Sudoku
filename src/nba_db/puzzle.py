"""4×4 teammate-Sudoku grid validation, solving, and unique-puzzle generation."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

from nba_db.graph import TeammateGraph

GRID_SIZE = 4
CELL_COUNT = GRID_SIZE * GRID_SIZE
BOX_SIZE = 2

Difficulty = Literal["easy", "medium", "hard", "expert"]

DIFFICULTY_CONFIG: dict[Difficulty, dict] = {
    "easy": {
        "clues": 8,
        "modern_only": True,
        "modern_year": 2000,
        "prefer_journeymen": False,
        "min_journeymen": 0,
    },
    "medium": {
        "clues": 6,
        "modern_only": False,
        "modern_year": 2000,
        "prefer_journeymen": False,
        "min_journeymen": 0,
        "require_era_mix": True,
    },
    "hard": {
        "clues": 4,
        "modern_only": False,
        "modern_year": 2000,
        "prefer_journeymen": True,
        "min_journeymen": 3,
    },
    "expert": {
        # True 2-clue uniqueness is vanishingly rare for a 16-player bank;
        # expert targets the minimal reliably unique clue count (3).
        "clues": 3,
        "modern_only": False,
        "modern_year": 2000,
        "prefer_journeymen": False,
        "min_journeymen": 0,
    },
}


def _groups() -> list[list[int]]:
    rows = [[r * GRID_SIZE + c for c in range(GRID_SIZE)] for r in range(GRID_SIZE)]
    cols = [[r * GRID_SIZE + c for r in range(GRID_SIZE)] for c in range(GRID_SIZE)]
    boxes = [
        [
            (br * BOX_SIZE + r) * GRID_SIZE + (bc * BOX_SIZE + c)
            for r in range(BOX_SIZE)
            for c in range(BOX_SIZE)
        ]
        for br in range(GRID_SIZE // BOX_SIZE)
        for bc in range(GRID_SIZE // BOX_SIZE)
    ]
    return rows + cols + boxes


GROUPS = _groups()
# For each cell, which group-mate indices must be teammates with it
CELL_PEERS: list[set[int]] = []
for i in range(CELL_COUNT):
    peers: set[int] = set()
    for g in GROUPS:
        if i in g:
            peers.update(j for j in g if j != i)
    CELL_PEERS.append(peers)


@dataclass
class Puzzle:
    difficulty: Difficulty
    solution: list[str]
    clues: list[str | None]
    bank: list[str]
    seed: int

    @property
    def clue_count(self) -> int:
        return sum(1 for c in self.clues if c is not None)

    def to_dict(self, graph: TeammateGraph) -> dict:
        def pack(pid: str | None) -> dict | None:
            if pid is None:
                return None
            p = graph.players[pid]
            return {
                "id": pid,
                "name": p.name,
                "team_count": p.team_count,
                "first_season": p.first_season,
                "last_season": p.last_season,
            }

        return {
            "difficulty": self.difficulty,
            "seed": self.seed,
            "clue_count": self.clue_count,
            "grid_size": GRID_SIZE,
            "box_size": BOX_SIZE,
            "clues": [pack(c) for c in self.clues],
            "solution": [pack(s) for s in self.solution],
            "bank": [pack(b) for b in self.bank],
            "rules": (
                "Place each bank player once. Every pair of players in the same "
                "row, column, or 2×2 box must have been NBA teammates "
                "(same franchise, same season) at least once."
            ),
        }


class PuzzleEngine:
    def __init__(self, graph: TeammateGraph) -> None:
        self.graph = graph
        # Compact index space for hot loops
        self._ids = list(graph.players)
        self._id_to_idx = {pid: i for i, pid in enumerate(self._ids)}
        n = len(self._ids)
        self._bits = [0] * n
        for i, pid in enumerate(self._ids):
            mask = 0
            for nb in graph.adj[pid]:
                j = self._id_to_idx.get(nb)
                if j is not None:
                    mask |= 1 << j
            self._bits[i] = mask

    def _idx(self, pid: str) -> int:
        return self._id_to_idx[pid]

    def _teammates_idx(self, a: int, b: int) -> bool:
        return bool(self._bits[a] & (1 << b))

    def valid_partial_ids(self, grid: list[str | None]) -> bool:
        for group in GROUPS:
            filled = [grid[i] for i in group if grid[i] is not None]
            if len(filled) != len(set(filled)):
                return False
            if not self.graph.is_clique(filled):
                return False
        return True

    def cell_ok(self, grid: list[str | None], index: int, pid: str) -> bool:
        """Check placing pid at index against already-filled peers only."""
        for j in CELL_PEERS[index]:
            other = grid[j]
            if other is None:
                continue
            if other == pid or not self.graph.are_teammates(pid, other):
                return False
        return True

    def count_solutions(
        self,
        clues: list[str | None],
        bank: list[str],
        *,
        limit: int = 2,
    ) -> int:
        grid = list(clues)
        used = {p for p in grid if p is not None}
        bank_set = list(bank)
        found = 0

        def bt() -> None:
            nonlocal found
            if found >= limit:
                return
            empties = [i for i, v in enumerate(grid) if v is None]
            if not empties:
                found += 1
                return

            best_i = None
            best_cands: list[str] | None = None
            for i in empties:
                cands = [
                    p
                    for p in bank_set
                    if p not in used and self.cell_ok(grid, i, p)
                ]
                if best_cands is None or len(cands) < len(best_cands):
                    best_cands = cands
                    best_i = i
                    if len(cands) == 0:
                        break
            assert best_i is not None and best_cands is not None
            if not best_cands:
                return
            for pid in best_cands:
                grid[best_i] = pid
                used.add(pid)
                bt()
                used.remove(pid)
                grid[best_i] = None
                if found >= limit:
                    return

        bt()
        return found

    def find_complete_grid(
        self,
        pool: list[str],
        rng: random.Random,
        *,
        max_nodes: int = 100_000,
    ) -> list[str] | None:
        grid: list[str | None] = [None] * CELL_COUNT
        used: set[str] = set()
        nodes = 0
        solution: list[str] | None = None

        pool_set = set(pool)
        # Rank by connectivity inside this pool; keep a workable core
        ranked = sorted(
            pool,
            key=lambda pid: sum(1 for nb in self.graph.adj[pid] if nb in pool_set),
            reverse=True,
        )
        pool = ranked[: min(280, len(ranked))]

        def bt() -> bool:
            nonlocal nodes, solution
            nodes += 1
            if nodes > max_nodes:
                return False
            empties = [i for i, v in enumerate(grid) if v is None]
            if not empties:
                solution = [p for p in grid if p is not None]  # type: ignore[misc]
                return True

            best_i = None
            best_cands: list[str] | None = None
            for i in empties:
                cands = [p for p in pool if p not in used and self.cell_ok(grid, i, p)]
                if best_cands is None or len(cands) < len(best_cands):
                    best_cands = cands
                    best_i = i
                    if len(cands) == 0:
                        break
            assert best_i is not None and best_cands is not None
            if not best_cands:
                return False
            rng.shuffle(best_cands)
            for pid in best_cands[:30]:
                grid[best_i] = pid
                used.add(pid)
                if bt():
                    return True
                used.remove(pid)
                grid[best_i] = None
            return False

        bt()
        return solution

    def dig_unique(
        self,
        solution: list[str],
        target_clues: int,
        rng: random.Random,
        *,
        attempts: int = 40,
    ) -> list[str | None] | None:
        bank = list(solution)
        cells = list(range(CELL_COUNT))
        best: list[str | None] | None = None
        best_count = CELL_COUNT

        for _ in range(attempts):
            clues: list[str | None] = list(solution)
            order = cells[:]
            rng.shuffle(order)
            for i in order:
                if sum(1 for c in clues if c is not None) <= target_clues:
                    break
                saved = clues[i]
                clues[i] = None
                if self.count_solutions(clues, bank, limit=2) != 1:
                    clues[i] = saved
            n = sum(1 for c in clues if c is not None)
            if n < best_count:
                best = list(clues)
                best_count = n
            if n <= target_clues:
                return clues
        return best if best is not None and best_count <= target_clues + 1 else None

    def _build_pool(self, difficulty: Difficulty, rng: random.Random) -> list[str]:
        cfg = DIFFICULTY_CONFIG[difficulty]
        base = self.graph.filter_players(
            modern_only=bool(cfg.get("modern_only")),
            modern_year=int(cfg.get("modern_year", 2000)),
        )
        if cfg.get("prefer_journeymen"):
            journey = [
                p
                for p in base
                if 6 <= self.graph.players[p].team_count <= 10
            ]
            journey.sort(key=lambda p: -len(self.graph.adj[p]))
            hubs = base[:80]
            return list(dict.fromkeys(journey[:200] + hubs + base))
        return base

    def generate(
        self,
        difficulty: Difficulty,
        *,
        seed: int | None = None,
        max_grid_attempts: int = 50,
    ) -> Puzzle:
        cfg = DIFFICULTY_CONFIG[difficulty]
        seed = random.randrange(1 << 30) if seed is None else seed
        rng = random.Random(seed)
        target = int(cfg["clues"])
        min_j = int(cfg.get("min_journeymen", 0))
        require_era_mix = bool(cfg.get("require_era_mix"))

        pool = self._build_pool(difficulty, rng)
        dig_attempts = 40 if difficulty in ("hard", "expert") else 20

        for attempt in range(max_grid_attempts):
            attempt_rng = random.Random(seed + attempt * 9973)
            local = pool[:]
            attempt_rng.shuffle(local)
            if difficulty == "hard":
                journey = [
                    p
                    for p in pool
                    if 6 <= self.graph.players[p].team_count <= 10
                ][:150]
                search_pool = list(dict.fromkeys(journey + pool[:50] + local[:100]))
            else:
                search_pool = list(dict.fromkeys(pool[:100] + local[:200]))

            solution = self.find_complete_grid(
                search_pool, attempt_rng, max_nodes=80_000
            )
            if solution is None:
                continue

            journey_n = sum(
                1
                for pid in solution
                if 6 <= self.graph.players[pid].team_count <= 10
            )
            if journey_n < min_j:
                continue

            if require_era_mix:
                older = sum(
                    1 for pid in solution if self.graph.players[pid].era_start < 2000
                )
                newer = sum(
                    1 for pid in solution if self.graph.players[pid].era_end >= 2010
                )
                if older < 2 or newer < 2:
                    continue

            clues = self.dig_unique(
                solution, target, attempt_rng, attempts=dig_attempts
            )
            if clues is None:
                continue

            clue_count = sum(1 for c in clues if c is not None)
            if clue_count <= target and self.count_solutions(clues, solution, limit=2) == 1:
                bank = solution[:]
                attempt_rng.shuffle(bank)
                return Puzzle(
                    difficulty=difficulty,
                    solution=solution,
                    clues=clues,
                    bank=bank,
                    seed=seed + attempt,
                )

        raise RuntimeError(
            f"Could not generate a unique {difficulty} puzzle (seed={seed})"
        )
