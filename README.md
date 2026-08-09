# TEAMMATE — NBA Sudoku

A **4×4 logic puzzle** where the **only clues** are franchise labels on every **row**, **column**, and **2×2 box**.

A player belongs in a cell only if they played for that cell’s **row team + column team + box team**. Each puzzle uses the 3+ franchise player database (1980–present) and has **exactly one** solution.

## Play

```bash
pip install -r requirements.txt
python scripts/generate_puzzles.py --per-difficulty 3
cd web && python3 -m http.server 8080 --bind 0.0.0.0
```

Open `http://localhost:8080` (or a tunnel/CDN link on mobile).

## Rules

1. The board starts **empty** — no pre-filled players.
2. Each row, column, and 2×2 box shows a franchise label.
3. Place each **bank** player once so every cell matches its three labels.
4. Unique solution, verified by exhaustive search over the bank.

## Difficulty

| Level | Focus |
|-------|--------|
| Easy | Modern players, tighter cells |
| Medium | Mix of eras |
| Hard | Obscure teams + journeymen |
| Expert | Higher ambiguity, still unique |

## Data

| File | Description |
|------|-------------|
| `data/nba_players.sqlite` | Players with ≥3 franchises + appearances |
| `web/data/players.json` | Browser player → teams map |
| `web/data/puzzles/*.json` | Unique team-label puzzles |
| `web/data/catalog.json` | Difficulty index |

Rebuild:

```bash
python scripts/build_database.py
python scripts/generate_puzzles.py
PYTHONPATH=src python3 -m unittest tests.test_puzzles -v
```
