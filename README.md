# TEAMMATE — NBA Sudoku

A **4×4 logic puzzle** where the **only clues** are franchise labels on every row, column, and 2×2 box.

Drag players from the bank onto the grid. Each drop is a **guess** — solve in as few as you can. Check is only available when all 16 cells are filled; wrong answers are never revealed.

## Play

**Live (iPad / phone):** [https://adrianjaucian.github.io/NBA-Sudoku/](https://adrianjaucian.github.io/NBA-Sudoku/)

> **One-time setup:** In the repo go to **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**. Then re-run the “Deploy GitHub Pages” workflow (or push any commit). Until that is done, the link above will 404.

Do **not** open the jsDelivr `index.html` link — that CDN serves HTML as `text/plain`, so the browser shows source code instead of running the game.

**Local dev:**

```bash
pip install -r requirements.txt
python scripts/generate_puzzles.py --count 30
cd web && python3 -m http.server 8080 --bind 0.0.0.0
```

Then open `http://localhost:8080` on this machine, or `http://<your-lan-ip>:8080` on another device on the same Wi‑Fi.

**Practice mode:** tap **New puzzle** anytime. **Daily mode** (Wordle-style, one play per day, rotating difficulty) is planned.

## Rules

1. Team labels only — no starting players.
2. A player fits a cell if they played for that cell’s row + column + box teams.
3. Use each bank player once.
4. Every puzzle uses mostly **memorable NBA names** (15+ of 16).
5. Exactly one solution (verified at generation time).

## Rebuild

```bash
python scripts/build_database.py
python scripts/generate_puzzles.py
PYTHONPATH=src python3 -m unittest tests.test_puzzles -v
```

Client puzzle JSON does **not** include the solution — only a hash for checking.
