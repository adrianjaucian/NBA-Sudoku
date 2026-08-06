# TEAMMATE — NBA Sudoku

A **4×4 Sudoku-style logic puzzle** where every pair of players in the same row, column, or 2×2 box must have been **NBA teammates** (same franchise, same season).

Only players who suited up for **3+ franchises** (1980–present) are used, so the graph stays rich with journeymen instead of one-team lifers.

## Play

```bash
pip install -r requirements.txt
# regenerate data/puzzles if needed:
python scripts/generate_puzzles.py --per-difficulty 3

cd web && python3 -m http.server 8080
```

Open `http://localhost:8080`.

## Rules

1. Place each **bank** player exactly once on the board.
2. In every row, column, and 2×2 box, **every pair** must have been teammates.
3. Each generated puzzle has **exactly one** solution (verified by exhaustive search over the 16-player bank).

## Difficulty

| Level  | Clues | Pool |
|--------|------:|------|
| Easy   | 8 | Mostly modern (2000+) |
| Medium | 6 | Mix of eras |
| Hard   | 4 | Prefers journeymen (6–10 teams) |
| Expert | 3 | Full teammate graph |

> Expert targets **3** clues. Truly unique **2**-clue puzzles are vanishingly rare for a fixed 16-player bank (every 2-clue pattern was tested on many grids).

## Database

| File | Description |
|------|-------------|
| `data/nba_players.sqlite` | Players with ≥3 franchises + season appearances |
| `web/data/teammate_graph.json` | Same-season teammate edges for the browser |
| `web/data/puzzles/*.json` | Pre-generated unique puzzles |
| `web/data/catalog.json` | Difficulty index |

Rebuild player DB from Basketball Reference:

```bash
python scripts/build_database.py
python scripts/generate_puzzles.py
```

## How uniqueness works

1. Search the teammate graph for a complete valid 4×4 grid (16 distinct players).
2. Remove clues while `count_solutions(clues, bank) == 1`.
3. Ship only puzzles that survive that check.

Teammates are defined from the appearances table: two players share an edge if they appear for the same franchise in the same season.
