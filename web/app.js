const SIZE = 4;
const BOX = 2;

function boxIndex(r, c) {
  return Math.floor(r / BOX) * (SIZE / BOX) + Math.floor(c / BOX);
}

const state = {
  catalog: null,
  puzzle: null,
  grid: [],
  guesses: 0,
  checked: false,
  drag: null, // { player, fromCell: number|null }
};

const els = {
  board: document.getElementById("board"),
  bank: document.getElementById("bank"),
  status: document.getElementById("status"),
  colLabels: document.getElementById("col-labels"),
  rowLabels: document.getElementById("row-labels"),
  boxLabels: document.getElementById("box-labels"),
  btnCheck: document.getElementById("btn-check"),
  btnNew: document.getElementById("btn-new"),
  guessCount: document.getElementById("guess-count"),
  filledCount: document.getElementById("filled-count"),
  dragGhost: document.getElementById("drag-ghost"),
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

function filledCount() {
  return state.grid.filter(Boolean).length;
}

function updateStats() {
  els.guessCount.textContent = String(state.guesses);
  els.filledCount.textContent = `${filledCount()}/16`;
  els.btnCheck.disabled = filledCount() !== 16 || state.checked;
}

function usedIds() {
  return new Set(state.grid.filter(Boolean).map((p) => p.id));
}

function renderLabels() {
  els.colLabels.innerHTML = "";
  els.colLabels.appendChild(document.createElement("div"));
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

function makeDraggable(el, player, fromCell) {
  el.dataset.playerId = player.id;
  if (fromCell != null) el.dataset.fromCell = String(fromCell);

  el.addEventListener("pointerdown", (e) => {
    if (state.checked) return;
    e.preventDefault();
    startDrag(e, player, fromCell);
  });
}

function renderBoard() {
  els.board.innerHTML = "";
  state.grid.forEach((player, i) => {
    const cell = document.createElement("div");
    cell.className = "cell";
    cell.dataset.index = String(i);
    cell.setAttribute("role", "gridcell");
    if (!player) cell.classList.add("empty");

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
      name.className = "name draggable";
      name.textContent = player.name;
      makeDraggable(name, player, i);
      cell.appendChild(name);
    } else {
      const ph = document.createElement("div");
      ph.className = "placeholder";
      ph.textContent = "Drop here";
      cell.appendChild(ph);
    }

    cell.addEventListener("pointerenter", () => {
      if (state.drag) cell.classList.add("drop-target");
    });
    cell.addEventListener("pointerleave", () => {
      cell.classList.remove("drop-target");
    });

    els.board.appendChild(cell);
  });
  updateStats();
}

function renderBank() {
  const used = usedIds();
  els.bank.innerHTML = "";
  for (const player of state.puzzle.bank) {
    if (used.has(player.id)) continue;
    const chip = document.createElement("div");
    chip.className = "chip draggable";
    chip.textContent = player.name;
    makeDraggable(chip, player, null);
    els.bank.appendChild(chip);
  }
}

function renderAll() {
  renderLabels();
  renderBoard();
  renderBank();
}

function recordGuess() {
  state.guesses += 1;
  updateStats();
}

function placePlayerAt(index, player, fromCell) {
  if (state.checked) return;

  const targetHad = state.grid[index];
  const sameSpot = fromCell === index;
  const movingExisting = fromCell != null;

  if (sameSpot) return;

  // Swap if dropping onto occupied cell
  if (targetHad && movingExisting) {
    state.grid[fromCell] = targetHad;
    state.grid[index] = player;
  } else if (targetHad && !movingExisting) {
    // Can't drop bank player onto occupied — ignore
    return;
  } else if (movingExisting) {
    state.grid[fromCell] = null;
    state.grid[index] = player;
  } else {
    state.grid[index] = player;
  }

  recordGuess();
  renderAll();
}

function returnToBank(fromCell) {
  if (state.checked || fromCell == null) return;
  if (!state.grid[fromCell]) return;
  state.grid[fromCell] = null;
  renderAll();
}

function startDrag(e, player, fromCell) {
  state.drag = { player, fromCell };
  els.dragGhost.textContent = player.name;
  els.dragGhost.hidden = false;
  moveGhost(e.clientX, e.clientY);
  e.target.setPointerCapture?.(e.pointerId);

  const onMove = (ev) => moveGhost(ev.clientX, ev.clientY);
  const onUp = (ev) => {
    document.removeEventListener("pointermove", onMove);
    document.removeEventListener("pointerup", onUp);
    document.removeEventListener("pointercancel", onUp);
    finishDrag(ev);
  };

  document.addEventListener("pointermove", onMove);
  document.addEventListener("pointerup", onUp);
  document.addEventListener("pointercancel", onUp);
}

function moveGhost(x, y) {
  els.dragGhost.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`;
}

function finishDrag(e) {
  els.dragGhost.hidden = true;
  const drag = state.drag;
  state.drag = null;
  if (!drag) return;

  document.querySelectorAll(".drop-target").forEach((el) => {
    el.classList.remove("drop-target");
  });

  const target = document.elementFromPoint(e.clientX, e.clientY);
  const cellEl = target?.closest?.(".cell");
  const bankEl = target?.closest?.("#bank");

  if (cellEl && cellEl.dataset.index != null) {
    placePlayerAt(Number(cellEl.dataset.index), drag.player, drag.fromCell);
    return;
  }

  if (bankEl && drag.fromCell != null) {
    returnToBank(drag.fromCell);
  }
}

async function sha256Hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function checkPuzzle() {
  if (filledCount() !== 16) {
    setStatus("Fill every cell before checking.", "bad");
    return;
  }

  const ids = state.grid.map((p) => p.id);
  const hash = await sha256Hex(ids.join(","));

  state.checked = true;
  els.btnCheck.disabled = true;

  if (hash === state.puzzle.solution_hash) {
    setStatus(`Solved in ${state.guesses} guess${state.guesses === 1 ? "" : "es"}.`, "ok");
  } else {
    setStatus(
      `Not quite — ${state.guesses} guess${state.guesses === 1 ? "" : "es"} so far. Keep trying or start a new puzzle.`,
      "bad"
    );
    state.checked = false;
    els.btnCheck.disabled = false;
  }
  updateStats();
}

function resetBoard() {
  state.grid = Array(SIZE * SIZE).fill(null);
  state.guesses = 0;
  state.checked = false;
  setStatus("Drag players from the bank onto the grid.");
  renderAll();
}

function pickRandomPuzzle() {
  const pool = state.catalog.puzzles;
  const idx = Math.floor(Math.random() * pool.length);
  return pool[idx];
}

async function loadPuzzle(path) {
  const puzzle = await loadJson(`data/${path}`);
  state.puzzle = puzzle;
  resetBoard();
}

async function loadNewPuzzle() {
  if (!state.catalog?.puzzles?.length) return;
  const path = pickRandomPuzzle();
  await loadPuzzle(path);
}

async function boot() {
  setStatus("Loading…");
  state.catalog = await loadJson("data/catalog.json");
  await loadNewPuzzle();

  els.btnCheck.addEventListener("click", () => checkPuzzle());
  els.btnNew.addEventListener("click", () => loadNewPuzzle());
}

boot().catch((err) => {
  console.error(err);
  setStatus(String(err.message || err), "bad");
});
