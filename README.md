# TEAMMATE — NBA Sudoku

A **4×4 logic puzzle** where the **only clues** are franchise labels on every row, column, and 2×2 box.

Drag players from the bank onto the grid. Each drop is a **guess** — solve in as few as you can. Check is only available when all 16 cells are filled; wrong answers are never revealed.

## Play

**Live demo (Netlify):** [https://chic-tanuki-f73cc0.netlify.app](https://chic-tanuki-f73cc0.netlify.app)

Password (Netlify drop protection): `My-Drop-Site` — enter once per browser/device.

To keep this URL permanently, [claim the site on Netlify](https://app.netlify.com/drop/chic-tanuki-f73cc0) (free account) within 60 minutes of deploy.

**GitHub Pages (optional):** [https://adrianjaucian.github.io/NBA-Sudoku/](https://adrianjaucian.github.io/NBA-Sudoku/) — requires [enabling Pages with GitHub Actions](https://github.com/adrianjaucian/NBA-Sudoku/settings/pages) once.

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
