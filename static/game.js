// The page only DRAWS what the server says. All mahjong logic is in Python.
"use strict";

let state = null;

const $ = (id) => document.getElementById(id);

// ---------- talking to the server ----------

async function api(path, body) {
  const options = body === undefined && !path.startsWith("/api/new") ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  };
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    alert(data.error || "Something went wrong");
    return;
  }
  state = data;
  render();
}

const loadState = () => api("/api/state");
const newGame = () => api("/api/new");
const discard = (tile) => api("/api/discard", { tile });
const declareWin = () => api("/api/win", {});
const passClaim = () => api("/api/pass", {});

// ---------- small helpers ----------

const SUIT_LABEL = { bamboo: "bam", circles: "circ", characters: "char" };

function shortName(tile) {
  const match = tile.match(/^(\d)-(\w+)$/);
  if (match) return `${match[1]} ${SUIT_LABEL[match[2]]}`;
  return tile.replace("-wind", "").replace("-dragon", "");
}

function pct(x) {
  if (x >= 0.995) return "99%+";
  if (x > 0 && x < 0.01) return "<1%";
  return `${Math.round(x * 100)}%`;
}

function distanceText(shanten) {
  if (shanten < 0) return "Winning!";
  if (shanten === 0) return "Ready";
  return `${shanten} away`;
}

function tileEl(tile, { small = false, clickable = false, classes = [] } = {}) {
  const el = document.createElement(clickable ? "button" : "span");
  el.className = ["tile", small ? "small" : "", ...classes].join(" ").trim();
  // ︎ asks the browser for the plain (non-emoji) look of the tile.
  const glyph = document.createElement("span");
  glyph.className = "glyph";
  glyph.textContent = state.symbols[tile] + "︎";
  const label = document.createElement("span");
  label.className = "label";
  label.textContent = shortName(tile);
  el.append(glyph, label);
  el.title = tile.replace("-", " ");
  return el;
}

function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); }

// ---------- drawing the page ----------

function render() {
  $("round").textContent = state.round;
  $("wall").textContent = state.wall_count;
  renderBanner();
  renderHand();
  renderDiscards();
  renderLog();
  renderOdds();
  renderChart();
}

function renderBanner() {
  const banner = $("banner");
  let text = "";
  if (state.phase === "won") {
    text = state.winner === 0 ? "You won! 🎉 Start a new game to play again."
                              : `${state.winner_name} won this round. Start a new game to play again.`;
  } else if (state.phase === "drawn") {
    text = "The wall is empty – nobody wins this time.";
  } else if (state.phase === "claim") {
    text = `${state.offer.from_name} discarded a tile that completes your hand – win, or pass?`;
  } else if (state.can_declare_win) {
    text = "Your 14 tiles form a winning hand!";
  }
  banner.hidden = !text;
  banner.textContent = text;
}

function renderHand() {
  const handEl = $("hand");
  clear(handEl);
  const playing = state.phase === "playing";
  const best = playing ? state.analysis.options[0].discard : null;

  const tiles = state.hand.slice();
  let drawn = null;
  if (playing && state.drawn_tile) {
    tiles.splice(tiles.indexOf(state.drawn_tile), 1);
    drawn = state.drawn_tile;
  }
  for (const tile of tiles) {
    handEl.append(tileEl(tile, { clickable: playing, classes: tile === best ? ["suggest"] : [] }));
    handEl.lastChild.onclick = () => discard(tile);
  }
  if (drawn) {
    const el = tileEl(drawn, { clickable: true, classes: ["drawn", drawn === best ? "suggest" : ""] });
    el.onclick = () => discard(drawn);
    el.title += " (just drawn)";
    handEl.append(el);
  }

  $("hand-hint").textContent = playing
    ? "click a tile to discard it · green outline = best discard"
    : "";
  $("win-btn").hidden = !(state.can_declare_win || state.phase === "claim");
  $("win-btn").textContent = state.phase === "claim" ? "Win on this discard" : "Declare win";
  $("win-btn").onclick = declareWin;
  $("pass-btn").hidden = state.phase !== "claim";
  $("pass-btn").onclick = passClaim;
}

function renderDiscards() {
  const box = $("discards");
  clear(box);
  for (const { tile, who } of state.discards) {
    box.append(tileEl(tile, { small: true, classes: who === "You" ? ["from-you"] : [] }));
    box.lastChild.title += ` (${who})`;
  }
  if (state.offer && box.lastChild) {
    box.lastChild.classList.add("suggest");
  }
  box.scrollTop = box.scrollHeight;
}

function renderLog() {
  const list = $("log");
  clear(list);
  for (const line of state.log.slice().reverse()) {
    const li = document.createElement("li");
    li.textContent = line;
    list.append(li);
  }
}

function metric(name, value, ready = false) {
  const div = document.createElement("div");
  div.className = "metric" + (ready ? " ready" : "");
  const v = document.createElement("div");
  v.className = "value";
  v.textContent = value;
  const n = document.createElement("div");
  n.className = "name";
  n.textContent = name;
  div.append(v, n);
  return div;
}

function renderOdds() {
  const metrics = $("metrics");
  const tbody = document.querySelector("#options tbody");
  clear(metrics);
  clear(tbody);
  $("waits-box").hidden = true;

  // "current" = the hand we're analysing (best discard, or the hand we hold when claiming)
  const options = state.analysis.options;
  const current = options ? options[0] : state.analysis.current;
  if (!current) {
    $("odds-sub").textContent = "";
    return;
  }

  const ready = current.shanten === 0;
  $("odds-sub").textContent = options ? "assuming you make the best discard" : "";
  metrics.append(
    metric("Distance to winning", distanceText(current.shanten), ready),
    metric("Helpful tiles still unseen", current.useful_copies, ready),
    metric(ready ? "Win chance, next round" : "Chance of a helpful tile, next round",
           pct(current.chance_next_round), ready),
  );
  if (ready) {
    // Only meaningful once you're ready: otherwise it is trivially ~100%.
    metrics.append(metric("Win chance, before the wall runs out",
                          pct(current.chance_rest_of_game), true));
  }

  if (current.useful.length) {
    $("waits-box").hidden = false;
    $("waits-title").textContent = ready ? "You're waiting on" : "Tiles that bring you closer";
    const waits = $("waits");
    clear(waits);
    for (const [tile, copies] of current.useful) {
      const wrap = document.createElement("span");
      wrap.className = "wait";
      wrap.append(tileEl(tile, { small: true }), `× ${copies}`);
      waits.append(wrap);
    }
  }

  for (const [index, row] of (options || []).entries()) {
    const tr = document.createElement("tr");
    if (index === 0) tr.className = "best";
    const cells = [
      tileEl(row.discard, { small: true }),
      distanceText(row.shanten),
      row.useful.length ? `${row.useful.length} ${row.useful.length === 1 ? "kind" : "kinds"}` : "–",
      row.useful_copies,
      pct(row.chance_next_round),
    ];
    for (const cell of cells) {
      const td = document.createElement("td");
      td.append(cell);
      tr.append(td);
    }
    tbody.append(tr);
  }
}

function renderChart() {
  // Distance from winning each round (0 = ready, lower is better).
  const svg = $("chart");
  clear(svg);
  const ns = "http://www.w3.org/2000/svg";
  const W = 320, H = 120, left = 30, right = 8, top = 10, bottom = 20;
  const make = (name, attrs, text) => {
    const el = document.createElementNS(ns, name);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    if (text !== undefined) el.textContent = text;
    svg.append(el);
    return el;
  };

  const points = state.history;
  const maxDistance = Math.max(3, ...points.map((p) => p.shanten));
  const xFor = (i) => left + (points.length === 1 ? 0 : (i / (points.length - 1)) * (W - left - right));
  const yFor = (d) => top + (Math.max(d, 0) / maxDistance) * (H - top - bottom);   // 0 at the top

  for (let d = 0; d <= maxDistance; d++) {
    const y = yFor(d);
    make("line", { x1: left, x2: W - right, y1: y, y2: y, stroke: "#d9cfb2", "stroke-width": 1 });
    make("text", { x: left - 4, y: y + 3, "text-anchor": "end", "font-size": 9, fill: "#6b665c" }, d);
  }
  if (points.length > 1) {
    make("polyline", {
      points: points.map((p, i) => `${xFor(i)},${yFor(p.shanten)}`).join(" "),
      fill: "none", stroke: "#b45309", "stroke-width": 2,
    });
  }
  points.forEach((p, i) => {
    const dot = make("circle", {
      cx: xFor(i), cy: yFor(p.shanten), r: 3.5,
      fill: p.shanten <= 0 ? "#15803d" : "#b45309",
    });
    make("title", {}, `Round ${p.round}: ${distanceText(p.shanten)}, ${pct(p.chance_next_round)} next round`);
    dot.append(svg.lastChild);
  });
  make("text", { x: (left + W - right) / 2, y: H - 4, "text-anchor": "middle", "font-size": 9, fill: "#6b665c" },
       "round (green dot = ready hand; hover a dot for details)");
}

$("new-game").onclick = newGame;
loadState();
