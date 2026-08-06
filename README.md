# NBA Player–Team Database

Database of NBA players who have played for **3 or more franchises** in the regular season from the **1979–80** season through the present.

Data is scraped from [Basketball Reference](https://www.basketball-reference.com/) season totals pages.

## What's included

| File | Description |
|------|-------------|
| `data/nba_players.sqlite` | SQLite database (players, teams, player_teams, appearances) |
| `data/players_3plus_teams.json` | Full JSON export with nested team history |
| `data/players_3plus_teams.csv` | One row per player |
| `data/player_teams.csv` | One row per player–franchise stint |

### Filters

- **Era:** seasons ending 1980 → current NBA season
- **Minimum teams:** 3 distinct franchises
- **Franchise continuity:** relocations/rebrands count as one team (e.g. SEA→OKC, NJN→BKN, VAN→MEM, NOH→NOP)
- **Aggregate rows** (`TOT`, `2TM`, …) are excluded; individual team rows are kept

## Rebuild

```bash
pip install -r requirements.txt
python scripts/build_database.py
```

Useful flags:

```bash
python scripts/build_database.py --use-cache          # reuse last scrape
python scripts/build_database.py --start-year 1980 --end-year 2026
python scripts/build_database.py --min-teams 3
```

Respect Basketball Reference's rate limits (default ~3.5s between requests).

## Query examples

```bash
sqlite3 data/nba_players.sqlite \
  "SELECT player_name, team_count FROM players ORDER BY team_count DESC LIMIT 10;"
```

```bash
sqlite3 data/nba_players.sqlite \
  "SELECT p.player_name, t.franchise_name
   FROM player_teams pt
   JOIN players p USING (player_id)
   JOIN teams t USING (franchise_key)
   WHERE p.player_name = 'James Harden'
   ORDER BY pt.first_season;"
```

## Schema

- `players` — id, name, first/last season, team_count  
- `teams` — franchise_key, franchise_name  
- `player_teams` — player ↔ franchise with seasons and abbreviations used  
- `appearances` — season-level player–team rows (filtered players only)  
- `meta` — build provenance  
