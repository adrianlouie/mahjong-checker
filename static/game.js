// The page only DRAWS what the server says. All mahjong logic is in Python.
"use strict";

let state = null;
let odds = null;        // simulated win chances for the current decision (arrive a moment later)
let oddsToken = 0;      // lets us ignore an answer that arrives after the game has moved on
let oddsRequest = null; // the in-flight odds request, cancelled when the game moves on

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
  odds = null;
  render();
  loadOdds();
}

const loadState = () => api("/api/state");
const newGame = () => api("/api/new");
const discard = (tile) => api("/api/discard", { tile });
const declareWin = () => api("/api/win", {});
const passClaim = () => api("/api/pass", {});
const claim = (kind, tiles) => api("/api/claim", { kind, tiles });

// The simulation takes ~2 seconds, so it is fetched separately from the fast state.
async function loadOdds() {
  const token = ++oddsToken;
  if (oddsRequest) oddsRequest.abort();
  if (state.phase !== "playing" && state.phase !== "claim") return;
  oddsRequest = new AbortController();
  try {
    const response = await fetch("/api/odds", { signal: oddsRequest.signal });
    const data = await response.json();
    if (token !== oddsToken || !response.ok) return;
    odds = data;
  } catch (error) {
    return;
  }
  renderActions();
  renderOdds();
}

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

// Simulated numbers for one choice, or undefined while the simulation is still running.
function oddsFor(action, tiles) {
  if (!odds) return undefined;
  return odds.options.find((o) => o.action === action && o.tiles.join() === tiles.join());
}

function marginText() {
  // 95% margin of error for a proportion near 50%, given how many games were simulated
  return odds && odds.playouts ? `±${Math.round(98 / Math.sqrt(odds.playouts))}%` : "";
}

// ---------- drawing the page ----------

function render() {
  $("round").textContent = state.round;
  $("wall").textContent = state.wall_count;
  renderBanner();
  renderOthers();
  renderDiscards();
  renderMelds($("my-melds"), state.melds);
  renderHand();
  renderActions();
  renderLog();
  renderOdds();
  renderChart();
}

function renderBanner() {
  const banner = $("banner");
  let text = "";
  const offer = state.offer;
  if (state.phase === "won") {
    text = state.winner === 0 ? "You won! 🎉 Start a new game to play again."
                              : `${state.winner_name} won this round. Start a new game to play again.`;
  } else if (state.phase === "drawn") {
    text = "The wall is empty – nobody wins this time.";
  } else if (state.phase === "claim" && offer.win) {
    text = `${offer.from_name} discarded a tile that completes your hand – win, or pass?`;
  } else if (state.phase === "claim") {
    const ways = [offer.pong ? "pong" : "", offer.chi.length ? "chi" : ""].filter(Boolean).join(" or ");
    text = `${offer.from_name} discarded ${offer.tile.replace("-", " ")} – you may ${ways} it.`;
  } else if (state.can_declare_win) {
    text = "Your hand is a winning hand!";
  }
  banner.hidden = !text;
  banner.textContent = text;
}

function renderMelds(container, melds) {
  clear(container);
  for (const meld of melds) {
    const group = document.createElement("span");
    group.className = "meld";
    group.title = meld.type;
    let markedClaimed = false;
    for (const tile of meld.tiles) {
      const isClaimed = !markedClaimed && tile === meld.claimed;
      markedClaimed = markedClaimed || isClaimed;
      group.append(tileEl(tile, { small: true, classes: isClaimed ? ["claimed"] : [] }));
    }
    container.append(group);
  }
}

function renderOthers() {
  const box = $("others");
  clear(box);
  for (const other of state.others) {
    const card = document.createElement("div");
    card.className = "opp";
    const name = document.createElement("div");
    name.className = "name";
    name.textContent = other.name + " ";
    const count = document.createElement("span");
    count.className = "count";
    count.textContent = `${other.concealed_count} hidden tiles`;
    name.append(count);
    card.append(name);

    const melds = document.createElement("div");
    melds.className = "melds";
    renderMelds(melds, other.melds);
    card.append(melds);

    if (other.hand) {                    // the game is over: show what they were holding
      const tiles = document.createElement("div");
      tiles.className = "tiles";
      for (const tile of other.hand) tiles.append(tileEl(tile, { small: true }));
      card.append(tiles);
    }
    box.append(card);
  }
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
}

function actionButton(label, onclick, { secondary = false, sub = "", tiles = [] } = {}) {
  const button = document.createElement("button");
  if (secondary) button.className = "secondary";
  const top = document.createElement("span");
  top.textContent = label + " ";
  if (tiles.length) {
    const wrap = document.createElement("span");
    wrap.className = "tiles";
    for (const tile of tiles) wrap.append(tileEl(tile, { small: true }));
    top.append(wrap);
  }
  button.append(top);
  if (sub) {
    const line = document.createElement("span");
    line.className = "sub";
    line.textContent = sub;
    button.append(line);
  }
  button.onclick = onclick;
  return button;
}

function claimSub(action, tiles) {
  const choice = (state.analysis.claims || []).find(
    (c) => c.action === action && (action === "pong" || c.tiles.join() === tiles.join()));
  const parts = [];
  if (choice) parts.push(`then ${distanceText(choice.shanten).toLowerCase()}`);
  const sim = oddsFor(action, action === "pong" ? [] : tiles);
  if (sim) parts.push(`${pct(sim.you)} to win`);
  return parts.join(" · ");
}

function renderActions() {
  const box = $("actions");
  clear(box);
  const offer = state.offer;
  if (state.phase === "claim" && offer.win) {
    box.append(actionButton("Win on this discard", declareWin));
    box.append(actionButton("Pass", passClaim, { secondary: true }));
  } else if (state.phase === "claim") {
    if (offer.pong) {
      box.append(actionButton("Pong", () => claim("pong"), { sub: claimSub("pong", []) }));
    }
    for (const pair of offer.chi) {
      box.append(actionButton("Chi", () => claim("chi", pair), {
        tiles: [...pair, offer.tile].sort((a, b) => parseInt(a) - parseInt(b)),   // same suit: sort by rank
        sub: claimSub("chi", pair),
      }));
    }
    box.append(actionButton("Pass", passClaim, { secondary: true, sub: claimSub("pass", []) }));
  } else if (state.can_declare_win) {
    box.append(actionButton("Declare win", declareWin));
  }
}

function renderDiscards() {
  const box = $("discards");
  clear(box);
  for (const { tile, who } of state.discards) {
    box.append(tileEl(tile, { small: true, classes: who === "You" ? ["from-you"] : [] }));
    box.lastChild.title += ` (${who})`;
  }
  if (state.offer && box.lastChild) {
    box.lastChild.classList.add("suggest");      // the tile you may claim
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
  $("odds-sub").textContent = options ? "assuming you make the best discard" : "if you pass";
  metrics.append(
    metric("Distance to winning", distanceText(current.shanten), ready),
    metric("Helpful tiles still unseen", current.useful_copies, ready),
    metric(ready ? "Win chance, next round" : "Chance of a helpful tile, next round",
           pct(current.chance_next_round), ready),
  );
  if (ready) {
    metrics.append(metric("Win chance, before the wall runs out",
                          pct(current.chance_rest_of_game), true));
  }

  // simulated: replays the game many times, with bots racing you
  if (odds && odds.options.length) {
    const best = odds.options.reduce((a, b) => (b.you > a.you ? b : a));
    metrics.append(
      metric(`Simulated win chance, best option ${marginText()}`, pct(best.you), true),
      metric("A bot wins first (simulated)", pct(best.bots)),
    );
  } else if (!odds && (state.phase === "playing" || state.phase === "claim") && !state.can_declare_win) {
    const pending = document.createElement("div");
    pending.className = "metric sim-pending";
    pending.textContent = "Simulating the rest of the game…";
    metrics.append(pending);
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
    const sim = oddsFor("discard", [row.discard]);
    const cells = [
      tileEl(row.discard, { small: true }),
      distanceText(row.shanten),
      row.useful.length ? `${row.useful.length} ${row.useful.length === 1 ? "kind" : "kinds"}` : "–",
      row.useful_copies,
      pct(row.chance_next_round),
      sim ? pct(sim.you) : (odds ? "–" : "…"),
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
       "turn (green dot = ready hand; hover a dot for details)");
}

$("new-game").onclick = newGame;
loadState();
