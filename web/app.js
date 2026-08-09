const SIZE = 4;
const BOX = 2;

function boxIndex(r, c) {
  return Math.floor(r / BOX) * (SIZE / BOX) + Math.floor(c / BOX);
}

const state = {
  catalog: null,
  puzzle: null,
  grid: [], // (player|null)[]
  selectedCell: null,
  selectedBankId: null,
};

const els = {
  difficulty: document.getElementById("difficulty"),
  puzzleSelect: document.getElementById("puzzle-select"),
  board: document.getElementById("board"),
  bank: document.getElementById("bank"),
  status: document.getElementById("status"),
  diffBlurb: document.getElementById("diff-blurb"),
  inspect: document.getElementById("inspect"),
  colLabels: document.getElementById("col-labels"),
  rowLabels: document.getElementById("row-labels"),
  boxLabels: document.getElementById("box-labels"),
  btnCheck: document.getElementById("btn-check"),
  btnHint: document.getElementById("btn-hint"),
  btnReset: document.getElementById("btn-reset"),
  btnSolve: document.getElementById("btn-solve"),
};

async function loadJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path}`);
  return res.json();
}

function setStatus(msg, kind = "") {
  els.status.textContent = msg;
  els.status.className = `status ${kind}`.trim();
}

function usedIds() {
  return new Set(state.grid.filter(Boolean).map((p) => p.id));
}

function cellTeams(index) {
  const r = Math.floor(index / SIZE);
  const c = index % SIZE;
  const b = boxIndex(r, c);
  return {
    row: state.puzzle.row_teams[r],
    col: state.puzzle.col_teams[c],
    box: state.puzzle.box_teams[b],
  };
}

function playerFits(player, index) {
  const t = cellTeams(index);
  const teams = new Set(player.teams || []);
  return teams.has(t.row.key) && teams.has(t.col.key) && teams.has(t.box.key);
}

function conflictIndices() {
  const bad = new Set();
  const used = new Map();
  state.grid.forEach((p, i) => {
    if (!p) return;
    if (used.has(p.id)) {
      bad.add(i);
      bad.add(used.get(p.id));
    } else {
      used.set(p.id, i);
    }
    if (!playerFits(p, i)) bad.add(i);
  });
  return bad;
}

function renderLabels() {
  els.colLabels.innerHTML = "";
  els.colLabels.appendChild(document.createElement("div")); // corner spacer
  for (const team of state.puzzle.col_teams) {
    const el = document.createElement("div");
    el.className = "axis-label col";
    el.innerHTML = `<span class="abbr">${team.abbr}</span><span class="full">${team.name}</span>`;
    els.colLabels.appendChild(el);
  }

  els.rowLabels.innerHTML = "";
  for (const team of state.puzzle.row_teams) {
    const el = document.createElement("div");
    el.className = "axis-label row";
    el.innerHTML = `<span class="abbr">${team.abbr}</span><span class="full">${team.name}</span>`;
    els.rowLabels.appendChild(el);
  }

  els.boxLabels.innerHTML = "";
  state.puzzle.box_teams.forEach((team, i) => {
    const el = document.createElement("div");
    el.className = "axis-label box";
    const br = Math.floor(i / 2);
    const bc = i % 2;
    el.innerHTML = `<span class="tag">Box ${br * 2 + bc + 1}</span><span class="abbr">${team.abbr}</span><span class="full">${team.name}</span>`;
    els.boxLabels.appendChild(el);
  });
}

function renderBoard() {
  const conflicts = conflictIndices();
  els.board.innerHTML = "";
  state.grid.forEach((player, i) => {
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "cell";
    cell.dataset.index = String(i);
    if (!player) cell.classList.add("empty");
    if (state.selectedCell === i) cell.classList.add("selected");
    if (conflicts.has(i)) cell.classList.add("conflict");

    // Box label watermark on top-left of each 2x2
    const r = Math.floor(i / SIZE);
    const c = i % SIZE;
    if (r % BOX === 0 && c % BOX === 0) {
      const b = boxIndex(r, c);
      const mark = document.createElement("div");
      mark.className = "box-watermark";
      mark.textContent = state.puzzle.box_teams[b].abbr;
      cell.appendChild(mark);
    }

    if (player) {
      const name = document.createElement("div");
      name.className = "name";
      name.textContent = player.name;
      cell.appendChild(name);
    } else {
      const ph = document.createElement("div");
      ph.className = "placeholder";
      ph.textContent = "Empty";
      cell.appendChild(ph);
    }

    cell.addEventListener("click", () => onCellClick(i));
    els.board.appendChild(cell);
  });
}

function renderBank() {
  const used = usedIds();
  const selectedTeams =
    state.selectedCell != null ? cellTeams(state.selectedCell) : null;

  els.bank.innerHTML = "";
  for (const player of state.puzzle.bank) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = player.name;
    chip.title = `${player.teams.join(", ")} · ${player.team_count} franchises`;

    const placed = used.has(player.id);
    if (placed) {
      chip.disabled = true;
      chip.classList.add("used");
    } else if (selectedTeams) {
      const fits = playerFits(player, state.selectedCell);
      if (fits) chip.classList.add("fits");
      else chip.classList.add("nofit");
    }
    if (state.selectedBankId === player.id) chip.classList.add("selected");

    chip.addEventListener("click", () => onBankClick(player));
    els.bank.appendChild(chip);
  }
}

function renderInspect() {
  if (state.selectedCell == null) {
    els.inspect.textContent = "Select a cell.";
    return;
  }
  const t = cellTeams(state.selectedCell);
  const player = state.grid[state.selectedCell];
  const fits = player ? playerFits(player, state.selectedCell) : null;
  els.inspect.innerHTML = `
    <div><strong>Row:</strong> ${t.row.name} (${t.row.abbr})</div>
    <div><strong>Column:</strong> ${t.col.name} (${t.col.abbr})</div>
    <div><strong>Box:</strong> ${t.box.name} (${t.box.abbr})</div>
    ${
      player
        ? `<div class="${fits ? "ok" : "bad"}">${player.name} ${
            fits ? "satisfies all three." : "does not satisfy all three."
          }</div>`
        : "<div>Place a bank player who suited up for all three.</div>"
    }
  `;
}

function renderAll() {
  renderLabels();
  renderBoard();
  renderBank();
  renderInspect();
}

function onCellClick(i) {
  if (state.selectedBankId) {
    placePlayer(i, state.selectedBankId);
    return;
  }
  state.selectedCell = i;
  renderAll();
}

function onBankClick(player) {
  const used = usedIds();
  if (used.has(player.id)) return;

  if (state.selectedCell != null) {
    placePlayer(state.selectedCell, player.id);
    return;
  }
  state.selectedBankId =
    state.selectedBankId === player.id ? null : player.id;
  setStatus(
    state.selectedBankId
      ? `Selected ${player.name} — tap a cell.`
      : ""
  );
  renderAll();
}

function placePlayer(index, playerId) {
  const player = state.puzzle.bank.find((p) => p.id === playerId);
  if (!player) return;
  state.grid = state.grid.map((p, i) => {
    if (i === index) return player;
    if (p?.id === playerId) return null;
    return p;
  });
  state.selectedBankId = null;
  state.selectedCell = index;
  setStatus(`Placed ${player.name}`);
  renderAll();
  if (state.grid.every(Boolean)) checkPuzzle(false);
}

function checkPuzzle(announceEmpty = true) {
  if (state.grid.some((p) => !p)) {
    if (announceEmpty) setStatus("Fill every cell before checking.", "bad");
    renderBoard();
    return false;
  }
  const conflicts = conflictIndices();
  if (conflicts.size) {
    setStatus("Some players don’t match their row + column + box teams.", "bad");
    renderBoard();
    return false;
  }
  const solved = state.grid.every(
    (p, i) => p.id === state.puzzle.solution[i].id
  );
  setStatus(
    solved
      ? "Solved — every cell matches its three team labels."
      : "All placements are legal, but this isn’t the unique solution.",
    solved ? "ok" : "bad"
  );
  renderBoard();
  return solved;
}

function resetPuzzle() {
  state.grid = Array(SIZE * SIZE).fill(null);
  state.selectedCell = null;
  state.selectedBankId = null;
  setStatus("Team labels only — fill the grid from the bank.");
  renderAll();
}

function hint() {
  const empties = state.grid
    .map((p, i) => ({ p, i }))
    .filter(({ p }) => !p);
  if (!empties.length) {
    setStatus("No empty cells left.");
    return;
  }
  // Prefer a cell with few remaining legal bank options
  const used = usedIds();
  empties.sort((a, b) => {
    const ca = state.puzzle.bank.filter(
      (p) => !used.has(p.id) && playerFits(p, a.i)
    ).length;
    const cb = state.puzzle.bank.filter(
      (p) => !used.has(p.id) && playerFits(p, b.i)
    ).length;
    return ca - cb;
  });
  const pick = empties[0];
  const correct = state.puzzle.solution[pick.i];
  state.grid[pick.i] = { ...correct };
  setStatus(`Hint: ${correct.name}`);
  state.selectedBankId = null;
  state.selectedCell = pick.i;
  renderAll();
}

function reveal() {
  state.grid = state.puzzle.solution.map((p) => ({ ...p }));
  setStatus("Solution revealed.", "ok");
  renderAll();
}

async function loadPuzzle(path) {
  const puzzle = await loadJson(`data/${path}`);
  state.puzzle = puzzle;
  resetPuzzle();
}

function fillDifficultySelect() {
  const diffs = Object.keys(state.catalog.difficulties);
  els.difficulty.innerHTML = diffs
    .map((d) => `<option value="${d}">${d}</option>`)
    .join("");
}

function fillPuzzleSelect() {
  const diff = els.difficulty.value;
  const info = state.catalog.difficulties[diff];
  els.diffBlurb.textContent = info.description;
  els.puzzleSelect.innerHTML = info.puzzles
    .map((p, i) => `<option value="${p}">Puzzle ${i + 1}</option>`)
    .join("");
}

async function onDifficultyChange() {
  fillPuzzleSelect();
  await loadPuzzle(els.puzzleSelect.value);
}

async function boot() {
  setStatus("Loading puzzles…");
  state.catalog = await loadJson("data/catalog.json");
  fillDifficultySelect();
  fillPuzzleSelect();
  await loadPuzzle(els.puzzleSelect.value);

  els.difficulty.addEventListener("change", onDifficultyChange);
  els.puzzleSelect.addEventListener("change", () =>
    loadPuzzle(els.puzzleSelect.value)
  );
  els.btnCheck.addEventListener("click", () => checkPuzzle(true));
  els.btnHint.addEventListener("click", hint);
  els.btnReset.addEventListener("click", resetPuzzle);
  els.btnSolve.addEventListener("click", reveal);
}

boot().catch((err) => {
  console.error(err);
  setStatus(String(err.message || err), "bad");
});
