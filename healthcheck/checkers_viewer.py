"""
checkers_viewer.py - turns recorded checkers games into a self-contained HTML replay you can step through.

    python3 checkers_viewer.py checkers_games/latest.json     re-open a saved game in the browser

checkers.py calls write_replay() after the games finish; it saves the games as JSON next to the HTML so
they can be replayed later without running the models again.
"""
from __future__ import annotations

import json
import sys
import time
import webbrowser
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / "checkers_games"


def write_replay(games: list[dict], open_browser: bool = True, page: str | None = None, prefix: str = "game") -> Path:
    """games: [{"title", "black", "white", "result", "material", "history": [...]}]. Returns the HTML path.
    chess_viewer.py passes its own page and prefix="chess"; its latest files are chess-latest.*."""
    OUT_DIR.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    latest = "latest" if prefix == "game" else f"{prefix}-latest"
    data = json.dumps(games)
    (OUT_DIR / f"{prefix}-{stamp}.json").write_text(data)
    (OUT_DIR / f"{latest}.json").write_text(data)
    html = OUT_DIR / f"{prefix}-{stamp}.html"
    html.write_text((page or PAGE).replace("__DATA__", data.replace("</", "<\\/")))
    (OUT_DIR / f"{latest}.html").write_text(html.read_text())
    if open_browser:
        webbrowser.open(html.as_uri())
    return html


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Checkers Replay</title>
<style>
:root {
  --bg: #f4f1ea; --panel: #ffffff; --ink: #1f1d1a; --muted: #6f6a60; --line: #e2ddd2;
  --light: #ecd9b4; --dark: #9a6b43; --from: rgba(255, 214, 10, .55); --to: rgba(255, 214, 10, .8);
  --cap: rgba(220, 50, 40, .45); --black: #262322; --black-rim: #0c0b0a; --white: #f7f3ec; --white-rim: #b9b0a0;
  --accent: #b5542c; --chip: #f0ebe1;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161514; --panel: #201e1c; --ink: #ece7de; --muted: #9c958a; --line: #34312d;
    --light: #c9b18a; --dark: #6d4a2e; --accent: #e07a4f; --chip: #2b2926;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.wrap { max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }
header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 16px; margin-bottom: 18px; }
h1 { font-size: 22px; margin: 0; }
select { font: inherit; padding: 4px 8px; border-radius: 8px; border: 1px solid var(--line);
  background: var(--panel); color: var(--ink); }
.result { color: var(--muted); }
.grid { display: grid; grid-template-columns: minmax(0, 560px) minmax(260px, 1fr); gap: 20px; align-items: start; }
@media (max-width: 820px) { .grid { grid-template-columns: 1fr; } }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 14px; }
.players { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 10px; font-size: 14px; }
.player { display: flex; align-items: center; gap: 8px; padding: 4px 10px; border-radius: 999px; min-width: 0; }
.player span.name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.player.active { background: var(--chip); outline: 2px solid var(--accent); }
.dot { width: 14px; height: 14px; border-radius: 50%; flex: none; }
.dot.b { background: var(--black); border: 2px solid var(--black-rim); }
.dot.w { background: var(--white); border: 2px solid var(--white-rim); }
.count { color: var(--muted); font-variant-numeric: tabular-nums; }
.boardwrap { display: grid; grid-template-columns: 18px 1fr; grid-template-rows: 1fr 18px; gap: 4px; }
.ranks, .files { display: grid; color: var(--muted); font-size: 11px; text-align: center; align-items: center; }
.ranks { grid-template-rows: repeat(8, 1fr); }
.files { grid-template-columns: repeat(8, 1fr); grid-column: 2; }
.board { position: relative; aspect-ratio: 1; display: grid; grid-template-columns: repeat(8, 1fr);
  border-radius: 6px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,.18); }
.sq { position: relative; }
.sq.l { background: var(--light); } .sq.d { background: var(--dark); }
.sq.from::after, .sq.to::after, .sq.cap::after, .sq.via::after { content: ""; position: absolute; inset: 0; }
.sq.from::after { background: var(--from); }
.sq.via::after { background: var(--from); }
.sq.to::after { background: var(--to); }
.sq.cap::after { background: var(--cap); }
.piece { position: absolute; width: 12.5%; height: 12.5%; display: grid; place-items: center;
  transition: transform .35s ease, opacity .3s ease; z-index: 2; pointer-events: none; }
.piece i { width: 78%; height: 78%; border-radius: 50%; display: grid; place-items: center;
  box-shadow: inset 0 -3px 0 rgba(0,0,0,.25), 0 2px 4px rgba(0,0,0,.35); font-style: normal; font-size: 3.2vmin; }
@media (min-width: 820px) { .piece i { font-size: 26px; } }
.piece.b i { background: radial-gradient(circle at 35% 30%, #4a4441, var(--black)); border: 3px solid var(--black-rim); color: #e7c35a; }
.piece.w i { background: radial-gradient(circle at 35% 30%, #fff, var(--white)); border: 3px solid var(--white-rim); color: #b5842a; }
.piece.gone { opacity: 0; }
.controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 14px; }
button { font: inherit; border: 1px solid var(--line); background: var(--chip); color: var(--ink);
  padding: 6px 12px; border-radius: 8px; cursor: pointer; min-width: 40px; }
button:hover { border-color: var(--accent); }
button.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
input[type=range] { flex: 1; min-width: 120px; accent-color: var(--accent); }
.speed { color: var(--muted); font-size: 13px; display: flex; align-items: center; gap: 6px; }
.now { margin-top: 12px; min-height: 44px; }
.now b { font-size: 17px; }
.tag { display: inline-block; font-size: 12px; padding: 1px 8px; border-radius: 999px; background: var(--chip);
  color: var(--muted); margin-left: 6px; }
.tag.warn { background: #f5d0c3; color: #8a2d12; }
.moves h2 { font-size: 15px; margin: 0 0 8px; }
.list { position: relative; max-height: 560px; overflow-y: auto; font-variant-numeric: tabular-nums; font-size: 14px; }
.row { display: grid; grid-template-columns: 38px 1fr 1fr; gap: 4px; }
.row .n { color: var(--muted); padding: 3px 0; }
.mv { padding: 3px 6px; border-radius: 6px; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mv:hover { background: var(--chip); }
.mv.cur { background: var(--accent); color: #fff; }
.mv.capt { font-weight: 600; }
.hint { color: var(--muted); font-size: 12px; margin-top: 10px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Checkers replay</h1>
    <select id="gamePick" aria-label="Game"></select>
    <span class="result" id="result"></span>
  </header>
  <div class="grid">
    <div class="card">
      <div class="players">
        <div class="player" id="pB"><span class="dot b"></span><span class="name" id="nB"></span><span class="count" id="cB"></span></div>
        <div class="player" id="pW"><span class="dot w"></span><span class="name" id="nW"></span><span class="count" id="cW"></span></div>
      </div>
      <div class="boardwrap">
        <div class="ranks" id="ranks"></div>
        <div class="board" id="board"></div>
        <div class="files" id="files"></div>
      </div>
      <div class="now" id="now"></div>
      <div class="controls">
        <button id="first" title="Start (Home)">⏮</button>
        <button id="prev" title="Previous (←)">◀</button>
        <button id="play" class="primary" title="Play / pause (space)">▶ Play</button>
        <button id="next" title="Next (→)">▶</button>
        <button id="last" title="End (End)">⏭</button>
        <input type="range" id="scrub" min="0" value="0" aria-label="Turn">
        <label class="speed">Speed <select id="speed">
          <option value="1500">slow</option><option value="800" selected>normal</option>
          <option value="350">fast</option></select></label>
      </div>
      <div class="hint">← → step · space play/pause · click any move to jump</div>
    </div>
    <div class="card moves">
      <h2>Moves</h2>
      <div class="list" id="list"></div>
    </div>
  </div>
</div>
<script>
const GAMES = __DATA__;
const FILES = "abcdefgh";
const $ = id => document.getElementById(id);
let g = 0, ply = 0, timer = null, pieces = [];

const sqName = (r, c) => FILES[c] + (8 - r);
for (let r = 0; r < 8; r++) $("ranks").insertAdjacentHTML("beforeend", `<div>${8 - r}</div>`);
for (const f of FILES) $("files").insertAdjacentHTML("beforeend", `<div>${f}</div>`);
GAMES.forEach((gm, i) => $("gamePick").insertAdjacentHTML("beforeend", `<option value="${i}">${gm.title}</option>`));
if (GAMES.length < 2) $("gamePick").style.display = "none";

function buildBoard() {
  const b = $("board");
  b.innerHTML = "";
  for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) {
    const d = document.createElement("div");
    d.className = "sq " + ((r + c) % 2 ? "d" : "l");
    d.id = `s${r}${c}`;
    b.appendChild(d);
  }
}

// Track pieces as objects so they can slide between squares instead of just redrawing.
function placePieces(board) {
  $("board").querySelectorAll(".piece").forEach(p => p.remove());
  pieces = [];
  board.forEach((row, r) => [...row].forEach((ch, c) => { if (ch !== ".") addPiece(ch, r, c); }));
}
function addPiece(ch, r, c) {
  const el = document.createElement("div");
  el.innerHTML = "<i></i>";
  $("board").appendChild(el);
  const p = { el, ch, r, c };
  setPiece(p, ch, r, c);
  pieces.push(p);
}
function setPiece(p, ch, r, c) {
  p.ch = ch; p.r = r; p.c = c;
  p.el.className = "piece " + ch.toLowerCase();
  p.el.firstChild.textContent = ch === ch.toUpperCase() ? "♛" : "";
  p.el.style.transform = `translate(${c * 100}%, ${r * 100}%)`;
}

function counts(board) {
  const s = board.join("");
  const n = ch => s.split(ch).length - 1;
  return { b: n("b"), B: n("B"), w: n("w"), W: n("W") };
}

function highlight(turn) {
  document.querySelectorAll(".sq").forEach(s => s.classList.remove("from", "to", "cap", "via"));
  if (!turn) return;
  const path = turn.path;
  $(`s${path[0][0]}${path[0][1]}`).classList.add("from");
  path.slice(1, -1).forEach(([r, c]) => $(`s${r}${c}`).classList.add("via"));
  const [lr, lc] = path[path.length - 1];
  $(`s${lr}${lc}`).classList.add("to");
  turn.captured.forEach(([r, c]) => $(`s${r}${c}`).classList.add("cap"));
}

// Scroll only the move list to the current move. (scrollIntoView would also scroll the page itself,
// dragging the board off screen every turn.)
function keepVisible(el) {
  const box = $("list"), top = el.offsetTop, bottom = top + el.offsetHeight;
  if (top < box.scrollTop) box.scrollTop = top;
  else if (bottom > box.scrollTop + box.clientHeight) box.scrollTop = bottom - box.clientHeight;
}

function show(n, animate) {
  const game = GAMES[g], H = game.history;
  n = Math.max(0, Math.min(H.length - 1, n));
  const turn = n > 0 ? H[n] : null;
  if (animate && n === ply + 1 && turn) {
    // Slide the moving piece, fade captured ones, then settle on the exact recorded board.
    const [fr, fc] = turn.path[0], [lr, lc] = turn.path[turn.path.length - 1];
    const mover = pieces.find(p => p.r === fr && p.c === fc);
    turn.captured.forEach(([r, c]) => {
      const p = pieces.find(q => q.r === r && q.c === c);
      if (p) { p.el.classList.add("gone"); p.r = p.c = -9; }
    });
    if (mover) setPiece(mover, H[n].board[lr][lc], lr, lc);
    setTimeout(() => { if (ply === n) placePieces(H[n].board); }, 380);
  } else {
    placePieces(H[n].board);
  }
  ply = n;
  highlight(turn);

  const k = counts(H[n].board);
  $("cB").textContent = `${k.b}${k.B ? " +" + k.B + "♛" : ""}`;
  $("cW").textContent = `${k.w}${k.W ? " +" + k.W + "♛" : ""}`;
  const toMove = n === H.length - 1 ? null : (n % 2 === 0 ? "b" : "w");
  $("pB").classList.toggle("active", toMove === "b");
  $("pW").classList.toggle("active", toMove === "w");

  if (!turn) {
    $("now").innerHTML = `<b>Start position</b><div class="result">${H.length - 1} half-moves in this game. Black moves first.</div>`;
  } else {
    const who = turn.color === "b" ? "Black" : "White";
    const tags = [];
    if (turn.captured.length) tags.push(`<span class="tag">captured ${turn.captured.length}</span>`);
    if (turn.crowned) tags.push(`<span class="tag">crowned ♛</span>`);
    if (turn.how) tags.push(`<span class="tag ${turn.how === "random fallback" ? "warn" : ""}">${turn.how}</span>`);
    const end = n === H.length - 1 ? `<div class="result"><b>${game.result}</b> · ${game.material}</div>` : "";
    $("now").innerHTML = `<b>${turn.ply}. ${who} ${turn.notation}</b>${tags.join("")}
      <div class="result">${turn.player}</div>${end}`;
  }
  $("scrub").value = n;
  document.querySelectorAll(".mv").forEach(m => m.classList.toggle("cur", +m.dataset.n === n));
  const cur = document.querySelector(".mv.cur");
  if (cur) keepVisible(cur);
}

function loadGame(i) {
  stop();
  g = i;
  const game = GAMES[g], H = game.history;
  $("nB").textContent = game.black; $("nB").title = game.black;
  $("nW").textContent = game.white; $("nW").title = game.white;
  $("result").textContent = `${game.result} · ${game.material}`;
  $("scrub").max = H.length - 1;
  let html = "";
  for (let i = 1; i < H.length; i += 2) {
    const cell = t => t ? `<div class="mv ${t.captured.length ? "capt" : ""}" data-n="${t.ply}" title="${t.how || t.player}">${t.notation}${t.crowned ? " ♛" : ""}</div>` : "<div></div>";
    html += `<div class="row"><div class="n">${(i + 1) / 2}.</div>${cell(H[i])}${cell(H[i + 1])}</div>`;
  }
  $("list").innerHTML = html;
  buildBoard();
  ply = 0;
  show(0, false);
}

function stop() { clearInterval(timer); timer = null; $("play").textContent = "▶ Play"; }
function play() {
  if (timer) return stop();
  if (ply >= GAMES[g].history.length - 1) show(0, false);
  $("play").textContent = "⏸ Pause";
  timer = setInterval(() => {
    if (ply >= GAMES[g].history.length - 1) return stop();
    show(ply + 1, true);
  }, +$("speed").value);
}

$("first").onclick = () => { stop(); show(0, false); };
$("prev").onclick = () => { stop(); show(ply - 1, false); };
$("next").onclick = () => { stop(); show(ply + 1, true); };
$("last").onclick = () => { stop(); show(GAMES[g].history.length - 1, false); };
$("play").onclick = play;
$("scrub").oninput = e => { stop(); show(+e.target.value, false); };
$("speed").onchange = () => { if (timer) { stop(); play(); } };
$("gamePick").onchange = e => loadGame(+e.target.value);
$("list").onclick = e => { const m = e.target.closest(".mv"); if (m) { stop(); show(+m.dataset.n, false); } };
document.addEventListener("keydown", e => {
  if (e.target.tagName === "SELECT") return;
  if (e.key === "ArrowRight") { stop(); show(ply + 1, true); }
  else if (e.key === "ArrowLeft") { stop(); show(ply - 1, false); }
  else if (e.key === "Home") { stop(); show(0, false); }
  else if (e.key === "End") { stop(); show(GAMES[g].history.length - 1, false); }
  else if (e.key === " ") { e.preventDefault(); play(); }
});
loadGame(0);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT_DIR / "latest.json"
    if not src.exists():
        sys.exit(f"no saved game at {src} - run checkers.py first")
    print(write_replay(json.loads(src.read_text())))
