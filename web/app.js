const SIZE = 4;
const BOX = 2;

const ROWS = Array.from({ length: SIZE }, (_, r) =>
  Array.from({ length: SIZE }, (_, c) => r * SIZE + c)
);
const COLS = Array.from({ length: SIZE }, (_, c) =>
  Array.from({ length: SIZE }, (_, r) => r * SIZE + c)
);
const BOXES = [];
for (let br = 0; br < SIZE / BOX; br++) {
  for (let bc = 0; bc < SIZE / BOX; bc++) {
    const box = [];
    for (let r = 0; r < BOX; r++) {
      for (let c = 0; c < BOX; c++) {
        box.push((br * BOX + r) * SIZE + (bc * BOX + c));
      }
    }
    BOXES.push(box);
  }
}
const GROUPS = [...ROWS, ...COLS, ...BOXES];

const state = {
  catalog: null,
  graph: null, // Map id -> Set of teammate ids
  players: null, // Map id -> player meta from graph
  puzzle: null,
  grid: [], // (player object|null)[]
  given: [], // boolean[]
  selectedCell: null,
  selectedBankId: null,
  inspect: [],
};

const els = {
  difficulty: document.getElementById("difficulty"),
  puzzleSelect: document.getElementById("puzzle-select"),
  board: document.getElementById("board"),
  bank: document.getElementById("bank"),
  status: document.getElementById("status"),
  diffBlurb: document.getElementById("diff-blurb"),
  inspect: document.getElementById("inspect"),
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

function buildGraphIndex(payload) {
  const adj = new Map();
  const players = new Map();
  for (const p of payload.players) {
    players.set(p.id, p);
    adj.set(p.id, new Set());
  }
  for (const [a, b] of payload.edges) {
    adj.get(a)?.add(b);
    adj.get(b)?.add(a);
  }
  return { adj, players };
}

function areTeammates(a, b) {
  if (!a || !b || a === b) return false;
  return state.graph.get(a)?.has(b) ?? false;
}

function groupConflictIndices(grid) {
  const bad = new Set();
  for (const group of GROUPS) {
    const filled = group
      .map((i) => ({ i, id: grid[i]?.id }))
      .filter((x) => x.id);
    const ids = filled.map((x) => x.id);
    if (new Set(ids).size !== ids.length) {
      filled.forEach((x) => bad.add(x.i));
      continue;
    }
    for (let a = 0; a < filled.length; a++) {
      for (let b = a + 1; b < filled.length; b++) {
        if (!areTeammates(filled[a].id, filled[b].id)) {
          bad.add(filled[a].i);
          bad.add(filled[b].i);
        }
      }
    }
  }
  return bad;
}

function usedIds() {
  return new Set(state.grid.filter(Boolean).map((p) => p.id));
}

function setStatus(msg, kind = "") {
  els.status.textContent = msg;
  els.status.className = `status ${kind}`.trim();
}

function renderBoard() {
  const conflicts = groupConflictIndices(state.grid);
  els.board.innerHTML = "";
  state.grid.forEach((player, i) => {
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "cell";
    cell.setAttribute("role", "gridcell");
    cell.dataset.index = String(i);
    if (state.given[i]) cell.classList.add("clue");
    if (!player) cell.classList.add("empty");
    if (state.selectedCell === i) cell.classList.add("selected");
    if (conflicts.has(i)) cell.classList.add("conflict");
    if (state.inspect[0] === i) cell.classList.add("inspect-a");
    if (state.inspect[1] === i) cell.classList.add("inspect-b");

    if (player) {
      const name = document.createElement("div");
      name.className = "name";
      name.textContent = player.name;
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = `${player.team_count} teams`;
      cell.append(name, meta);
    } else {
      const ph = document.createElement("div");
      ph.className = "placeholder";
      ph.textContent = "Empty";
      cell.append(ph);
    }

    cell.addEventListener("click", () => onCellClick(i));
    els.board.appendChild(cell);
  });
}

function renderBank() {
  const used = usedIds();
  els.bank.innerHTML = "";
  for (const player of state.puzzle.bank) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = player.name;
    chip.title = `${player.first_season}–${player.last_season} · ${player.team_count} franchises`;
    if (used.has(player.id)) {
      chip.disabled = true;
      chip.classList.add("used");
    }
    if (state.selectedBankId === player.id) chip.classList.add("selected");
    chip.addEventListener("click", () => onBankClick(player));
    els.bank.appendChild(chip);
  }
}

function renderAll() {
  renderBoard();
  renderBank();
  renderInspect();
}

function onCellClick(i) {
  if (state.given[i]) {
    // Still allow inspect on clues
    toggleInspect(i);
    state.selectedCell = i;
    renderAll();
    return;
  }

  if (state.selectedBankId) {
    placePlayer(i, state.selectedBankId);
    return;
  }

  // Toggle inspect when clicking filled cells without a bank selection
  if (state.grid[i] && state.selectedCell === i) {
    toggleInspect(i);
  } else if (state.grid[i] && state.inspect.length) {
    toggleInspect(i);
  }

  state.selectedCell = i;
  renderAll();
}

function onBankClick(player) {
  const used = usedIds();
  if (used.has(player.id)) return;

  if (state.selectedCell != null && !state.given[state.selectedCell]) {
    placePlayer(state.selectedCell, player.id);
    return;
  }

  state.selectedBankId =
    state.selectedBankId === player.id ? null : player.id;
  setStatus(
    state.selectedBankId
      ? `Selected ${player.name} — click an empty cell.`
      : ""
  );
  renderAll();
}

function placePlayer(index, playerId) {
  if (state.given[index]) return;
  const player = state.puzzle.bank.find((p) => p.id === playerId);
  if (!player) return;

  // If this player is already elsewhere (non-clue), move them
  state.grid = state.grid.map((p, i) => {
    if (i === index) return player;
    if (p?.id === playerId && !state.given[i]) return null;
    return p;
  });

  state.selectedBankId = null;
  state.selectedCell = index;
  setStatus(`Placed ${player.name}`);
  renderAll();
  maybeAutoCheck();
}

function toggleInspect(i) {
  if (!state.grid[i]) return;
  const idx = state.inspect.indexOf(i);
  if (idx >= 0) {
    state.inspect.splice(idx, 1);
  } else {
    state.inspect.push(i);
    if (state.inspect.length > 2) state.inspect.shift();
  }
}

function renderInspect() {
  if (state.inspect.length < 2) {
    els.inspect.textContent = "Pick two players on the board.";
    return;
  }
  const [a, b] = state.inspect.map((i) => state.grid[i]);
  if (!a || !b) {
    els.inspect.textContent = "Pick two filled cells.";
    return;
  }
  const ok = areTeammates(a.id, b.id);
  els.inspect.innerHTML = ok
    ? `<strong>${a.name}</strong> and <strong>${b.name}</strong> were teammates at least once.`
    : `<strong>${a.name}</strong> and <strong>${b.name}</strong> never overlapped on a roster in this dataset.`;
}

function maybeAutoCheck() {
  if (state.grid.every(Boolean)) {
    checkPuzzle(false);
  }
}

function checkPuzzle(announceEmpty = true) {
  if (state.grid.some((p) => !p)) {
    if (announceEmpty) setStatus("Fill every cell before checking.", "bad");
    renderBoard();
    return false;
  }
  const conflicts = groupConflictIndices(state.grid);
  if (conflicts.size) {
    setStatus("Conflicts in a row, column, or box — every pair must be teammates.", "bad");
    renderBoard();
    return false;
  }
  // Unique solution guarantee: also match canonical solution order
  const solved = state.grid.every(
    (p, i) => p.id === state.puzzle.solution[i].id
  );
  if (solved) {
    setStatus("Solved — every unit is a teammate clique.", "ok");
  } else {
    // Valid alternate shouldn't exist; treat as incomplete logic path
    setStatus("No row/box conflicts, but this isn't the unique solution.", "bad");
  }
  renderBoard();
  return solved;
}

function resetPuzzle() {
  state.grid = state.puzzle.clues.map((c) => (c ? { ...c } : null));
  state.given = state.puzzle.clues.map((c) => c != null);
  state.selectedCell = null;
  state.selectedBankId = null;
  state.inspect = [];
  setStatus(`Loaded ${state.puzzle.difficulty} · ${state.puzzle.clue_count} clues`);
  renderAll();
}

function hint() {
  const empties = state.grid
    .map((p, i) => ({ p, i }))
    .filter(({ p, i }) => !p && !state.given[i]);
  if (!empties.length) {
    setStatus("No empty cells left.");
    return;
  }
  const pick = empties[Math.floor(Math.random() * empties.length)];
  const correct = state.puzzle.solution[pick.i];
  state.grid[pick.i] = { ...correct };
  state.given[pick.i] = true; // lock hint as a clue
  setStatus(`Hint: ${correct.name}`);
  state.selectedBankId = null;
  renderAll();
}

function reveal() {
  state.grid = state.puzzle.solution.map((p) => ({ ...p }));
  state.given = state.grid.map(() => true);
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
  setStatus("Loading teammate graph…");
  const [catalog, graphPayload] = await Promise.all([
    loadJson("data/catalog.json"),
    loadJson("data/teammate_graph.json"),
  ]);
  state.catalog = catalog;
  const indexed = buildGraphIndex(graphPayload);
  state.graph = indexed.adj;
  state.players = indexed.players;

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
