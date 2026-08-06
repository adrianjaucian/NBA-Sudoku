"""Same-season teammate graph built from the appearances table."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Player:
    player_id: str
    name: str
    first_season: str
    last_season: str
    team_count: int

    @property
    def era_start(self) -> int:
        return int(self.first_season.split("-")[0])

    @property
    def era_end(self) -> int:
        return int(self.last_season.split("-")[0])


class TeammateGraph:
    """Undirected graph: edge iff two players shared a franchise in the same season."""

    def __init__(
        self,
        players: dict[str, Player],
        adj: dict[str, set[str]],
        shared: dict[tuple[str, str], list[dict]],
    ) -> None:
        self.players = players
        self.adj = adj
        self.shared = shared  # frozenset-ordered pair -> list of {franchise, season}

    @classmethod
    def from_sqlite(cls, db_path: Path | str) -> TeammateGraph:
        conn = sqlite3.connect(db_path)
        try:
            players = {
                row[0]: Player(*row)
                for row in conn.execute(
                    """
                    SELECT player_id, player_name, first_season, last_season, team_count
                    FROM players
                    """
                )
            }
            by_team_season: dict[tuple[str, int], set[str]] = defaultdict(set)
            for pid, franchise, year in conn.execute(
                """
                SELECT player_id, franchise_key, season_end_year
                FROM appearances
                """
            ):
                if pid in players:
                    by_team_season[(franchise, year)].add(pid)
        finally:
            conn.close()

        adj: dict[str, set[str]] = {pid: set() for pid in players}
        shared: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for (franchise, year), group in by_team_season.items():
            season = f"{year - 1}-{str(year)[-2:]}"
            for a, b in combinations(sorted(group), 2):
                adj[a].add(b)
                adj[b].add(a)
                key = (a, b) if a < b else (b, a)
                shared[key].append({"franchise": franchise, "season": season})

        # Deduplicate shared entries while preserving order
        for key, entries in shared.items():
            seen: set[tuple[str, str]] = set()
            uniq = []
            for e in entries:
                t = (e["franchise"], e["season"])
                if t not in seen:
                    seen.add(t)
                    uniq.append(e)
            shared[key] = uniq

        return cls(players, adj, dict(shared))

    def are_teammates(self, a: str, b: str) -> bool:
        if a == b:
            return False
        return b in self.adj.get(a, ())

    def is_clique(self, player_ids: Iterable[str]) -> bool:
        ids = list(player_ids)
        return all(self.are_teammates(a, b) for a, b in combinations(ids, 2))

    def shared_stints(self, a: str, b: str) -> list[dict]:
        key = (a, b) if a < b else (b, a)
        return self.shared.get(key, [])

    def neighbors(self, player_id: str) -> set[str]:
        return self.adj.get(player_id, set())

    def filter_players(
        self,
        *,
        modern_only: bool = False,
        modern_year: int = 2000,
        min_teams: int | None = None,
        max_teams: int | None = None,
        journeyman_only: bool = False,
    ) -> list[str]:
        out = []
        for pid, p in self.players.items():
            if modern_only and p.era_end < modern_year and p.era_start < modern_year:
                continue
            if min_teams is not None and p.team_count < min_teams:
                continue
            if max_teams is not None and p.team_count > max_teams:
                continue
            if journeyman_only and not (6 <= p.team_count <= 10):
                continue
            out.append(pid)
        out.sort(key=lambda pid: (-len(self.adj[pid]), self.players[pid].name))
        return out

    def export_client_payload(self, player_ids: Iterable[str] | None = None) -> dict:
        """Compact JSON for the browser: players + adjacency lists."""
        ids = list(player_ids) if player_ids is not None else list(self.players)
        id_set = set(ids)
        players = []
        edges = []
        for pid in ids:
            p = self.players[pid]
            players.append(
                {
                    "id": pid,
                    "name": p.name,
                    "first_season": p.first_season,
                    "last_season": p.last_season,
                    "team_count": p.team_count,
                }
            )
            for other in sorted(self.adj[pid]):
                if other in id_set and pid < other:
                    edges.append([pid, other])
        return {"players": players, "edges": edges}


def save_graph_json(graph: TeammateGraph, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(graph.export_client_payload(), separators=(",", ":")), encoding="utf-8")
