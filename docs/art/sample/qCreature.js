// qCreature.js：異形（野獸、熔岩獸、源晶造物、傀儡、霧魅…）的 Q 版畫法（美術 PM 畫圖 agent，2026-11-07）。
// 使用者（11-07）：「所有人先停下 先讓q板完成再開始工作 把所有需要q版的都完成 腳色 動畫 怪物 npc 等 全部」。
// 做法（為了開發改動最小）：身形的點座標、部件順序、特徵、詞綴全部「原封不動」沿用 enemyArt.js（遊戲 inkCreature.ts 已移植的那一份），
//   只換掉畫法層：C 的 ink（抖線、水彩、暗面斜線、墨線描邊）→ Q 的平塗（純色、無抖動、無排線）＋部件之間一條細縫線＋整隻剪影粗外框（同 qDoll.js 的 stamp，1.3 單位 #16121a）。
//   改的只有：眼睛（Q 的方眼＋高光）、材質紋樣改平塗線條／色塊（tiny／small 簡化成 1 筆）、地面環平塗、頭目外光改「剪影膨脹」的平塗光。
// 規則照 enemyArt.js：外觀 ＝ 身形 body × 材質 material × 元素 element × 大小 size × 精英詞綴 affixes；不認得的值一律退回、不出錯：
//   body → ooze；variant → 預設款（鳥、甲蟲）；material → fur；element → 沒有；size → 1；affix → 跳過（只畫精英金環）；trait → 跳過。
// 座標：腳底 (0,0)、往上 −y、朝東；朝西由 stamp 鏡像（代決 #3：只畫側面，正面、背面沿用側面）。確定性：不用 Math.random（紋樣抖動用名稱雜湊）。
window.QCreature = (() => {
  const TAU = Math.PI * 2, OUT = "#16121a", INK = OUT;
  function hexRgb(h) { const n = parseInt(h.slice(1, 7), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  function mix(a, b, t) { const A = hexRgb(a), B = hexRgb(b), m = (x, y) => Math.round(x * (1 - t) + y * t); return `#${((m(A[0], B[0]) << 16) | (m(A[1], B[1]) << 8) | m(A[2], B[2])).toString(16).padStart(6, "0")}`; }
  const dark = (c, t = 0.3) => mix(c, "#000000", t), light = (c, t = 0.3) => mix(c, "#ffffff", t);
  function seedOf(s) { let h = 2166136261; for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; }
  function rng(seed) { let s = seed >>> 0; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); }
  const bbox = (pts) => { let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity; for (const [x, y] of pts) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); } return { x0, x1, y0, y1 }; };
  function ellPts(cx, cy, rx, ry, n = 18) { return Array.from({ length: n }, (_, i) => [cx + Math.cos((i / n) * TAU) * rx, cy + Math.sin((i / n) * TAU) * ry]); }

  // ============================== Q 畫法層（和 StoryDoll.H 同介面：ink、stroke、limb、dot） ==============================
  // 圓潤的部件用「中點二次曲線」（和 C 同一條曲線、但不抖）；sharp 的部件（晶、石）用直線多邊形。
  function smooth(ctx, pts, closed = true) {
    ctx.beginPath();
    const n = pts.length, mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    if (!closed) { ctx.moveTo(...pts[0]); for (let i = 1; i < n - 1; i++) { const m = mid(pts[i], pts[i + 1]); ctx.quadraticCurveTo(pts[i][0], pts[i][1], m[0], m[1]); } ctx.lineTo(...pts[n - 1]); return; }
    const m0 = mid(pts[n - 1], pts[0]); ctx.moveTo(m0[0], m0[1]);
    for (let i = 0; i < n; i++) { const p = pts[i], m = mid(p, pts[(i + 1) % n]); ctx.quadraticCurveTo(p[0], p[1], m[0], m[1]); }
    ctx.closePath();
  }
  function outline(ctx, pts, sharp) { if (!sharp) return smooth(ctx, pts); ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); }
  /** 平塗一塊；部件之間一條細縫線（顏色＝本色加深，像 qDoll 袖子的 seam），外輪廓由剪影外框負責。 */
  // Q 大頭：身形的 qHead＝[第一個頭部部件的名稱開頭, 支點 x, 支點 y, 倍率]。畫到那個部件起，之後的部件（頭、耳、口鼻、眼、牙）
  //   以支點（頸部）為中心放大，頭往前上方長大、身體不動；畫完身體就還原（特徵、詞綴的位置照 enemyArt.js 的 head 點）。
  //   第 5 個值（選填）＝結束部件的名稱開頭：畫到它時還原（傀儡的近側手臂、鳥的爪子在頭之後才畫，不跟著放大）。
  let QHEAD = null, IN_HEAD = false, HEAD_DONE = false;
  function headHook(ctx, key) {
    if (!QHEAD) return;
    if (IN_HEAD && QHEAD[4] && key.startsWith(QHEAD[4])) { ctx.restore(); IN_HEAD = false; HEAD_DONE = true; return; }
    if (IN_HEAD || HEAD_DONE || !key.startsWith(QHEAD[0])) return;
    const [, x, y, s] = QHEAD; IN_HEAD = true; ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.translate(-x, -y);
  }
  // ---- 動畫掛點（qCreatureAnim.js 用）：每個部件依名稱開頭歸到一個「部件組」（腿、翅、尾、頭、身體…），組有支點 pivots；
  //   POSE＝{ parts: {組: {rot, dx, dy, kx, sx, sy, a, pivot}} }。沒有 POSE（預設靜態）時 part() 只呼叫 headHook、直接畫，像素和原本相同。
  //   沒有名稱的 dot／eye 跟著「上一個部件組」（LAST）；需要時用 mark() 換組（不畫東西）。
  let POSE = null, GROUPS = null, PIVOTS = null, LAST = "body", DEPTH = 0;
  const UNIVERSAL = [["tr-scar", "head"], ["af-bz", "head"]];
  function groupOf(key) { for (const [p, g] of GROUPS ?? []) if (key.startsWith(p)) return g; for (const [p, g] of UNIVERSAL) if (key.startsWith(p)) return g; return "body"; }
  function applyXf(ctx, g) {
    const f = POSE.parts?.[g]; if (!f) return false;
    const [px, py] = f.pivot ?? PIVOTS?.[g] ?? [0, 0];
    ctx.save(); ctx.translate(px + (f.dx ?? 0), py + (f.dy ?? 0)); if (f.rot) ctx.rotate(f.rot); if (f.kx) ctx.transform(1, 0, f.kx, 1, 0, 0);
    ctx.scale(f.sx ?? 1, f.sy ?? 1); ctx.translate(-px, -py); if (f.a !== undefined) ctx.globalAlpha *= Math.max(0, Math.min(1, f.a));
    return true;
  }
  // POSE.split（動畫用，傀儡崩塌）：{組: [{clip: [[x,y]…], dx, dy, rot, pivot}…]}：同一組畫好幾次，每次只畫 clip 多邊形裡的那一塊、各自位移旋轉（斷成幾塊）；靜態不變
  function drawSplit(ctx, pieces, fn) {
    for (const q of pieces) {
      ctx.save(); const [px, py] = q.pivot ?? [0, 0];
      ctx.translate(px + (q.dx ?? 0), py + (q.dy ?? 0)); if (q.rot) ctx.rotate(q.rot); ctx.translate(-px, -py);
      ctx.beginPath(); q.clip.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.clip(); fn(); ctx.restore();
    }
  }
  function inPart(ctx, g, fn) { if (!POSE || DEPTH > 0) return fn(); DEPTH++; const on = applyXf(ctx, g); try { const sp = POSE.split?.[g]; if (sp) drawSplit(ctx, sp, fn); else fn(); } finally { if (on) ctx.restore(); DEPTH--; } }
  function part(ctx, key, fn) { headHook(ctx, key); if (!POSE) return fn(); LAST = groupOf(key); inPart(ctx, LAST, fn); }
  function mark(key) { if (POSE) LAST = groupOf(key); }
  function ink(ctx, key, pts, color, opt = {}) {
    part(ctx, key, () => {
      ctx.save(); outline(ctx, pts, opt.sharp); ctx.fillStyle = color; ctx.fill();
      if (opt.line !== false) { ctx.strokeStyle = mix(color, OUT, 0.55); ctx.lineWidth = 0.55; ctx.lineJoin = "round"; ctx.stroke(); }
      ctx.restore();
    });
  }
  function stroke(ctx, key, pts, w = 0.7, color = OUT) { part(ctx, key, () => { ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.lineJoin = "round"; smooth(ctx, pts, false); ctx.stroke(); ctx.restore(); }); }
  // POSE.limbRim（動畫用，蜘蛛）：細腳的邊改亮色、腳加粗一點，小尺寸也看得出腳在動；靜態不變
  function limb(ctx, key, pts, w, color) { const rim = POSE?.limbRim; stroke(ctx, key, pts, w + 1.1 + (rim ? 0.5 : 0), rim ? light(color, 0.38) : mix(color, OUT, 0.55)); stroke(ctx, key, pts, w + (rim ? 0.7 : 0), color); }
  function dot(ctx, x, y, rx, ry, c) { inPart(ctx, LAST, () => { ctx.fillStyle = c; ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, TAU); ctx.fill(); }); }

  // 元素色（palette.ts 同一份）
  const ELEM = {
    fire: ["#ff6a1a", "#ffd04a"], ice: ["#8fe3ff", "#e8fbff"], lightning: ["#fff36b", "#fff7c0"], poison: ["#7ddc3a", "#d6f59a"],
    wind: ["#c8ffe8", "#effff8"], earth: ["#b0814a", "#e6c89a"], holy: ["#fff2b0", "#fffbe0"], shadow: ["#9a6ad8", "#c8a8f0"], water: ["#3a7bd5", "#d8f0ff"],
  };
  const CRYSTAL = "#9a86ff";
  const BASALT = "#4a3631";
  // 顏色分開（11-07；只改這兩組）：熔岩的雷、聖原本都是淡黃裂縫 → 雷維持黃色鋸齒（全遊戲雷＝黃）；
  //   聖（美術 PM 決定 11-07）＝乳白主紋＋小十字形亮點（形狀和雷的鋸齒不同）、金眼；
  //   源晶的暗原本和無元素同一個淡紫 → 暗＝深靛紫晶（無元素維持淡紫）。
  const MAGMA_ELEM = { holy: ["#fff4dc", "#ffbf3a"] }, MAGMA_CROSS = { holy: "#fffbe8" };
  const CRYSTAL_SHADOW = "#4e3a8e"; // C 的 #3b2c28 在 Q 的黑外框裡會糊成一團，提亮一階

  // ---- 材質 → 色票（同 enemyArt.js；熔岩底色提亮） ----
  function palette(spec, body, size) {
    const mat = MATERIALS.includes(spec.material) ? spec.material : "fur";
    const el = ELEM[spec.element];
    let base, accent, eye;
    if (mat === "magma") { const me = MAGMA_ELEM[spec.element] ?? el; base = spec.tint ?? BASALT; accent = me ? me[0] : ELEM.fire[0]; eye = me ? me[1] : ELEM.fire[1]; }
    else if (mat === "stone") { base = spec.tint ?? "#7f8f94"; accent = el ? el[0] : "#8fe3ff"; eye = el ? el[1] : "#e8fbff"; }
    else if (mat === "wood") { base = spec.tint ?? "#a8763e"; accent = el ? el[0] : null; eye = "#2b1e16"; }
    else if (mat === "mist") { base = spec.tint ?? (el ? mix("#e6ecef", el[0], 0.45) : "#e6ecef"); accent = el ? el[0] : "#b8c4cc"; eye = el ? el[1] : "#5a6a7a"; }
    else if (mat === "crystal") { base = spec.element === "shadow" ? CRYSTAL_SHADOW : el ? mix(CRYSTAL, el[0], 0.4) : (spec.tint ?? CRYSTAL); accent = el ? el[1] : "#e4dcff"; eye = "#ffffff"; }
    else { base = spec.tint ?? body.fur; if (el) base = mix(base, el[0], 0.22); accent = el ? el[0] : null; eye = el ? el[1] : "#ffd23a"; }
    return { mat, base, d: dark(base, 0.28), l: light(base, 0.3), accent, eye, cross: mat === "magma" ? MAGMA_CROSS[spec.element] : undefined, sharp: mat === "crystal" || mat === "stone", alpha: mat === "mist" ? 0.62 : undefined, lite: size < 0.95 };
  }

  // ---- 材質紋樣（平塗線條、色塊；不排線）。lite＝tiny／small：只畫 1 筆 ----
  const clipTo = (ctx, pts, P) => { ctx.save(); outline(ctx, pts, P.sharp); ctx.clip(); };
  function cracks(ctx, key, pts, P) { // 熔岩：一～兩道鋸齒裂縫，暗紅底＋亮色芯
    const b = bbox(pts), r = rng(seedOf(key)), n = !P.lite && b.x1 - b.x0 > 18 ? 2 : 1;
    clipTo(ctx, pts, P);
    for (let i = 0; i < n; i++) {
      const y = b.y0 + (b.y1 - b.y0) * (n === 1 ? 0.5 : 0.35 + 0.3 * i), line = [];
      for (let x = b.x0 + 2; x <= b.x1 - 2; x += 3.6) line.push([x, y + (line.length % 2 ? -1.4 : 1.4) + (r() - 0.5) * 1.2]);
      if (line.length < 2) continue;
      ctx.save(); ctx.strokeStyle = "#7a2a08"; ctx.lineWidth = 2; ctx.lineJoin = "miter"; ctx.beginPath(); line.forEach(([x, y], j) => (j ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke();
      ctx.strokeStyle = P.accent; ctx.lineWidth = 1; ctx.stroke(); ctx.restore();
    }
    if (P.cross) { // 聖：裂縫上方的小十字亮點（暗紅底＋乳白芯，同裂縫的兩層）
      const cs = P.lite ? [[0.4, 0.22]] : [[0.24, 0.22], [0.56, 0.18]];
      for (const [fx, fy] of cs) { const x = b.x0 + (b.x1 - b.x0) * fx, y = b.y0 + (b.y1 - b.y0) * fy + 1.2, h = 2.3;
        ctx.save(); ctx.lineCap = "round"; for (const [c, w] of [["#7a2a08", 1.9], [P.cross, 0.9]]) { ctx.strokeStyle = c; ctx.lineWidth = w; ctx.beginPath(); ctx.moveTo(x - h, y); ctx.lineTo(x + h, y); ctx.moveTo(x, y - h); ctx.lineTo(x, y + h); ctx.stroke(); } ctx.restore(); }
    }
    ctx.restore();
  }
  function facets(ctx, key, pts, P) { // 源晶：左上一塊亮面（色塊）＋一條晶面線
    const b = bbox(pts), w = b.x1 - b.x0, h = b.y1 - b.y0;
    clipTo(ctx, pts, P);
    ctx.fillStyle = light(P.base, 0.28); ctx.beginPath(); ctx.moveTo(b.x0 - 1, b.y0 - 1); ctx.lineTo(b.x0 + w * 0.5, b.y0 - 1); ctx.lineTo(b.x0 + w * 0.22, b.y1 + 1); ctx.lineTo(b.x0 - 1, b.y1 + 1); ctx.closePath(); ctx.fill();
    if (!P.lite) stroke(ctx, `${key}-f2`, [[b.x0 + w * 0.6, b.y0], [b.x0 + w * 0.5, b.y0 + h * 0.6], [b.x1, b.y0 + h * 0.7]], 0.7, light(P.base, 0.55));
    ctx.restore();
  }
  function runes(ctx, key, pts, P) { // 青石：發光刻符（平塗兩層線）
    const b = bbox(pts), cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2;
    // 刻符 ᛉ：一豎＋兩撇（lite 只畫一豎）
    const lines = P.lite ? [[[cx, cy - 3], [cx, cy + 3]]] : [[[cx, cy - 3.6], [cx, cy + 3.6]], [[cx - 2.6, cy - 3], [cx, cy - 0.4], [cx + 2.6, cy - 3]]];
    clipTo(ctx, pts, P);
    lines.forEach((l, i) => { ctx.save(); ctx.lineJoin = "miter"; ctx.lineCap = "round"; ctx.beginPath(); l.forEach(([x, y], j) => (j ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.strokeStyle = dark(P.base, 0.35); ctx.lineWidth = 1.8; ctx.stroke(); ctx.strokeStyle = P.accent; ctx.lineWidth = 0.85; ctx.stroke(); ctx.restore(); });
    ctx.restore();
  }
  function grain(ctx, key, pts, P) { // 木：一～兩道木紋（平塗深色線）
    const b = bbox(pts);
    clipTo(ctx, pts, P);
    for (const i of P.lite ? [1.5] : [1, 2]) { const y = b.y0 + ((b.y1 - b.y0) * i) / 3; stroke(ctx, `${key}-gr${i}`, [[b.x0, y], [(b.x0 + b.x1) / 2, y - 0.8], [b.x1, y + 0.4]], 0.7, P.d); }
    ctx.restore();
  }
  function furBelly(ctx, key, pts, P) { // 毛皮：肚子下緣一塊亮色（平塗），一眼分得出上下
    const b = bbox(pts), w = b.x1 - b.x0, h = b.y1 - b.y0;
    if (w < 8 || h < 6) return;
    clipTo(ctx, pts, P);
    ctx.fillStyle = P.l; ctx.beginPath(); ctx.ellipse((b.x0 + b.x1) / 2 + w * 0.08, b.y1 + h * 0.08, w * 0.36, h * 0.32, 0, 0, TAU); ctx.fill();
    ctx.restore();
  }
  function swirl(ctx, key, pts, P) { // 霧：一道亮色漩渦線（平塗）
    const b = bbox(pts), w = b.x1 - b.x0, h = b.y1 - b.y0, cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2;
    if (w < 6 || h < 5) return;
    clipTo(ctx, pts, P);
    ctx.save(); ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 0.9; ctx.lineCap = "round"; ctx.beginPath(); ctx.ellipse(cx - w * 0.05, cy, w * 0.22, h * 0.2, 0, Math.PI * 0.9, Math.PI * 2.3); ctx.stroke(); ctx.restore();
    ctx.restore();
  }
  function mass(ctx, key, pts, P, opt = {}) { part(ctx, key, () => massDraw(ctx, key, pts, P, opt)); }
  function massDraw(ctx, key, pts, P, opt) {
    ink(ctx, key, pts, opt.color ?? P.base, { sharp: P.sharp, ...opt });
    if (!opt.main) return;
    if (/head/.test(key) && P.mat !== "crystal") return; // Q 的大頭保持乾淨：紋樣只畫在身體（源晶的亮面例外）
    if (P.mat === "magma") cracks(ctx, key, pts, P);
    else if (P.mat === "crystal") facets(ctx, key, pts, P);
    else if (P.mat === "stone") runes(ctx, key, pts, P);
    else if (P.mat === "wood") grain(ctx, key, pts, P);
    else if (P.mat === "mist" && !P.lite) swirl(ctx, key, pts, P);
    else if (P.mat === "fur" && !opt.color && !P.lite && /body|blob|torso|abd/.test(key)) furBelly(ctx, key, pts, P);
  }
  function back(ctx, key, list, P) {
    list.forEach(([x, y], i) => part(ctx, `${key}-sh${i}`, () => {
      if (P.lite && i > 0) return;
      if (P.mat === "crystal") {
        const h = 5 + (i % 2) * 2.4;
        ink(ctx, `${key}-sh${i}`, [[x - 2, y + 1], [x + 0.6, y - h], [x + 2.4, y + 1]], light(P.base, 0.25), { sharp: true });
        stroke(ctx, `${key}-shl${i}`, [[x + 0.2, y - h + 1.6], [x - 0.6, y]], 0.6, "#ffffff");
      } else if (P.mat === "stone") {
        dot(ctx, x, y + 0.6, 1.8, 1, "#6a9a4a");
      } else if (P.mat === "wood" || P.mat === "mist") {
        // 木頭、霧：背上不加東西
      } else if (P.mat === "magma") {
        ctx.fillStyle = P.accent; ctx.fillRect(x + 0.2, y - 3.8 - (i % 2) * 2.4, 1.6, 1.6);
      } else {
        ink(ctx, `${key}-tuft${i}`, [[x - 1.8, y + 0.8], [x, y - 2.6], [x + 1.6, y + 0.6]], P.d, { sharp: true, line: false });
      }
    }));
  }
  /** Q 的眼睛：圓角方眼（眼色）＋方瞳＋一點高光（qDoll 的「big」眼同一語言）。 */
  const eye = (ctx, x, y, P, r = 1) => inPart(ctx, LAST, () => {
    const s = r * 1.25;
    if (POSE?.eyeShut) { // 動畫用（熊、野豬倒下）：閉眼＝深色 ×；靜態不變
      ctx.save(); ctx.strokeStyle = OUT; ctx.lineWidth = 0.7 * s; ctx.lineCap = "round"; ctx.beginPath();
      ctx.moveTo(x - 1.05 * s, y - 1.05 * s); ctx.lineTo(x + 1.05 * s, y + 1.05 * s); ctx.moveTo(x + 1.05 * s, y - 1.05 * s); ctx.lineTo(x - 1.05 * s, y + 1.05 * s); ctx.stroke(); ctx.restore(); return;
    }
    ctx.fillStyle = P.eye; ctx.beginPath(); ctx.roundRect(x - 1.15 * s, y - 1.25 * s, 2.3 * s, 2.5 * s, 0.7 * s); ctx.fill();
    ctx.fillStyle = OUT; ctx.fillRect(x - 0.2 * s, y - 0.95 * s, 1.0 * s, 1.9 * s);
    ctx.fillStyle = "#ffffff"; ctx.fillRect(x + 0.15 * s, y - 0.85 * s, 0.45 * s, 0.45 * s);
  });
  const fang = (ctx, key, x, y, h = 2) => ink(ctx, key, [[x - 0.8, y], [x, y + h], [x + 0.8, y]], "#f4ecd8", { sharp: true, line: false });

  // ============================== 身形 ==============================
  // 以下身形的點座標、部件順序全部原樣沿用 enemyArt.js；Q 版只多一個 qHead（大頭，見 headHook）。
  // 每種身形：fur 預設毛色、top 最高點（頭頂狀態列避開）、head 頭的位置（詞綴特效用）、len 身長的一半、draw。
  const BODIES = {
    hound: { qHead: ["hd-ear", 12, -22, 1.3],  zh: "犬狼", fur: "#7a7a82", top: -36, head: [20, -28], len: 24, sp: [[-10, -25], [-4, -25.6], [2, -25.4]], draw(ctx, P) {
      for (const x of [-12, 6]) mass(ctx, `hd-lf${x}`, [[x, -12], [x + 4, -12], [x + 4.4, 0], [x - 0.4, 0]], P, { color: P.d });
      mass(ctx, "hd-tail", [[-14, -20], [-22, -25], [-26, -21], [-20, -17], [-13, -15]], P);
      const body = [[-16, -12], [-17, -20], [-10, -25], [4, -25], [12, -22], [13, -12], [0, -10]];
      mass(ctx, "hd-body", body, P, { main: true });
      back(ctx, "hd", [[-10, -25], [-4, -25.6], [2, -25.4]], P);
      for (const x of [-9, 8]) mass(ctx, `hd-l${x}`, [[x, -13], [x + 4, -13], [x + 4.6, 0], [x - 0.4, 0]], P);
      mass(ctx, "hd-ear", [[12, -29], [13, -36], [16.4, -30]], P, { color: P.d, w: 0.7, sharp: true });
      mass(ctx, "hd-head", [[8, -22], [11, -30], [17, -31], [22, -28], [28, -26], [28, -23], [21, -21], [14, -18]], P, { main: true });
      dot(ctx, 28, -25, 0.9, 0.8, INK); eye(ctx, 19, -27.4, P); fang(ctx, "hd-fang", 24, -22.2);
    } },
    boar: { qHead: ["bo-ear", 11, -15, 1.25],  zh: "野豬", fur: "#6a4a36", top: -28, head: [16, -18], len: 22, sp: [[-8, -24], [-1, -25], [6, -23]], draw(ctx, P) {
      for (const x of [-10, 6]) mass(ctx, `bo-lf${x}`, [[x, -9], [x + 4, -9], [x + 4, 0], [x, 0]], P, { color: P.d });
      stroke(ctx, "bo-tail", [[-15, -16], [-18, -18], [-17.4, -20]], 0.8);
      const body = [[-15, -8], [-16, -18], [-8, -24], [4, -25], [12, -20], [13, -9], [0, -7]];
      mass(ctx, "bo-body", body, P, { main: true });
      for (const [i, x] of [-11, -6, -1, 4].entries()) ink(ctx, `bo-br${i}`, [[x - 2, -23 - (x > -8 ? 1 : 0)], [x, -27.4], [x + 2, -24]], P.d, { sharp: true, shade: false, w: 0.5 });
      back(ctx, "bo", [[-8, -24], [6, -23]], P);
      for (const x of [-7, 8]) mass(ctx, `bo-l${x}`, [[x, -9], [x + 4, -9], [x + 4, 0], [x, 0]], P);
      mass(ctx, "bo-ear", [[11, -21], [12, -26], [15, -21]], P, { color: P.d, w: 0.6, sharp: true });
      mass(ctx, "bo-head", [[9, -22], [16, -21], [22, -16], [23, -11], [17, -9], [10, -11]], P, { main: true });
      ink(ctx, "bo-snout", ellPts(22.4, -13.2, 2.2, 2.8, 10), P.l, { shade: false, w: 0.6 });
      ink(ctx, "bo-tusk", [[18.6, -11.4], [21.4, -17.4], [20.4, -11]], "#f4ecd8", { sharp: true, shade: false, w: 0.45 });
      eye(ctx, 16.6, -17.4, P, 0.9);
    } },
    bear: { qHead: ["be-head", 11, -21, 1.3],  zh: "熊", fur: "#6a4a32", top: -33, head: [18, -26], len: 22, sp: [[-10, -28.4], [-3, -29.8], [4, -29.2]], draw(ctx, P) {
      for (const x of [-11, 6]) mass(ctx, `be-lf${x}`, [[x - 2.8, -12], [x + 2.8, -12], [x + 3, 0], [x - 3, 0]], P, { color: P.d });
      mass(ctx, "be-body", [[-17, -9], [-17, -22], [-8, -29.6], [4, -29], [14, -22], [15, -9], [-2, -7]], P, { main: true });
      back(ctx, "be", [[-10, -28.4], [-3, -29.8], [4, -29.2]], P);
      for (const x of [-6, 11]) mass(ctx, `be-l${x}`, [[x - 3, -12], [x + 3, -12], [x + 3.4, 0], [x - 3.2, 0]], P);
      mass(ctx, "be-head", [[9, -26], [14, -31], [21, -29.4], [25.6, -23], [23.6, -19.6], [16, -18], [10, -20]], P, { main: true });
      mass(ctx, "be-ear", ellPts(13.6, -30.6, 2.2, 2.2, 10), P, { shade: false, w: 0.7 });
      ink(ctx, "be-snout", ellPts(23.4, -22.2, 2.6, 2, 10), P.l, { shade: false, w: 0.6 });
      dot(ctx, 25.2, -23, 0.9, 0.8, INK); eye(ctx, 18.6, -25.6, P, 0.9);
    } },
    flyer: { qHeadBy: { bat: ["fl-be", 4, -2, 1.25], bird: ["fl-head", 6, -2, 1.18, "fl-claw"] },  zh: "飛禽", fur: "#a07a4a", top: -50, head: [9, -22], len: 20, hover: true, sp: [[-4, -22], [0, -24], [4, -22]], draw(ctx, P, v) {
      ctx.save(); ctx.translate(0, -18);
      if (v === "bat") {
        mass(ctx, "fl-bwf", [[-1, -3], [-10, -16], [-20, -14], [-17, -9], [-22, -6], [-15, -3], [-16, 2], [-4, 1]], P, { color: P.d });
        mass(ctx, "fl-bbody", ellPts(0, 0, 6, 7, 16), P, { main: true });
        mass(ctx, "fl-bwn", [[1, -3], [10, -18], [21, -17], [18, -11], [24, -8], [16, -4], [17, 1], [4, 1]], P, { main: true });
        for (const [x, t] of [[3, -14], [7.4, -14.6]]) mass(ctx, `fl-be${x}`, [[x - 1.6, -8.4], [x, t], [x + 1.6, -8.4]], P, { sharp: true, w: 0.6 });
        mass(ctx, "fl-bhead", ellPts(5, -6.4, 4, 3.6, 12), P);
        eye(ctx, 7, -7, P, 0.8); fang(ctx, "fl-bfang", 7.6, -3.6, 1.6);
        // Q 版：蝠不畫 back()（enemyArt.js 的背點在翅尖外，晶刺、苔點會浮在半空，審查退回 #4）
      } else {
        mass(ctx, "fl-wf", [[-2, -4], [-12, -26], [-20, -30], [-16, -22], [-22, -24], [-14, -12], [-4, 2]], P, { color: P.d, sharp: true });
        mass(ctx, "fl-tail", [[-8, 2], [-18, 8], [-16, 2], [-20, 4], [-9, -1]], P, { color: P.d, sharp: true, shade: false, w: 0.6 });
        mass(ctx, "fl-body", ellPts(0, 0, 9, 6, 16), P, { main: true });
        ink(ctx, "fl-belly", ellPts(1.5, 2, 6, 3, 12), P.mat === "fur" ? "#f0e6d0" : P.l, { shade: false, w: 0.5 });
        mass(ctx, "fl-wn", [[2, -4], [10, -28], [18, -34], [15, -24], [22, -27], [14, -12], [4, 2]], P, { main: true, sharp: true });
        mass(ctx, "fl-head", ellPts(9, -4, 4.2, 4.2, 12), P);
        ink(ctx, "fl-beak", [[12.5, -5.2], [17, -3], [12.5, -1]], "#e8bb48", { sharp: true, shade: false, w: 0.5 });
        eye(ctx, 10.6, -5, P, 0.8);
        for (const x of [-2, 3]) stroke(ctx, `fl-claw${x}`, [[x, 5], [x, 9]], 1.4, "#e8bb48");
        back(ctx, "fl", [[10, -28], [18, -34]], P);
      }
      ctx.restore();
    } },
    crawler: { zh: "爬蟲", fur: "#3a3440", top: -24, head: [15, -12], len: 18, sp: [[-8, -20], [-2, -20.4]], draw(ctx, P, v) {
      if (v === "spider") {
        const legs = [[[1, -10], [-6, -19], [-13, 0]], [[3, -10], [0, -21], [-4, 0]], [[5, -10], [9, -21], [8, 0]], [[7, -10], [16, -18], [18, 0]]];
        legs.forEach((l, i) => limb(ctx, `sp-lf${i}`, l.map(([x, y]) => [x - 2.2, y - 0.6]), 0.9, P.d));
        mass(ctx, "sp-abd", ellPts(-9, -12, 9, 8, 18), P, { main: true });
        back(ctx, "sp", [[-12, -19.6], [-6, -19.4]], P);
        stroke(ctx, "sp-mark", [[-11, -15], [-8, -11], [-11, -8]], 1.2, P.accent ?? "#c0392b");
        mass(ctx, "sp-head", ellPts(5, -9, 6, 5, 14), P);
        legs.forEach((l, i) => limb(ctx, `sp-l${i}`, l, 1, P.base));
        mark("sp-eyes"); for (const [x, y] of [[9.4, -11], [10.6, -9.4], [8.6, -9.2]]) dot(ctx, x, y, 0.7, 0.7, P.eye);
        fang(ctx, "sp-fang", 10, -6, 2);
      } else {
        const legs = [[[-8, -6], [-12, -3], [-13, 0]], [[0, -6], [-1, -2], [-2, 0]], [[7, -6], [9, -3], [11, 0]]];
        legs.forEach((l, i) => limb(ctx, `bt-lf${i}`, l.map(([x, y]) => [x + 2, y]), 0.8, P.d));
        const shell = [[-14, -8], [-13, -15], [-6, -20], [4, -20], [11, -15], [12, -8], [0, -6]];
        mass(ctx, "bt-shell", shell, P, { main: true });
        stroke(ctx, "bt-seam", [[-13, -10], [-4, -14.6], [8, -16.6]], 0.6);
        back(ctx, "bt", [[-6, -20], [1, -20.4]], P);
        mass(ctx, "bt-head", [[11, -14], [16, -15], [19, -11], [17, -7], [11, -7]], P, { color: P.d });
        mass(ctx, "bt-horn", [[16, -13.4], [23, -18], [19.4, -11]], P, { color: P.l, sharp: true, shade: false, w: 0.6 });
        legs.forEach((l, i) => limb(ctx, `bt-l${i}`, l, 0.9, P.base));
        mark("bt-eye"); eye(ctx, 15.6, -11.6, P, 0.8);
      }
    } },
    lizard: { qHead: ["lz-head", 13, -9, 1.3],  zh: "蜥蜴", fur: "#6a7a3a", top: -19, core: [2, -7.4], head: [20, -12], len: 30, sp: [[-6, -13.6], [-1, -14], [4, -13.6]], draw(ctx, P) {
      for (const x of [-6, 9]) mass(ctx, `lz-lf${x}`, [[x - 2, -6], [x + 2, -6], [x + 1, 0], [x - 3, 0]], P, { color: P.d });
      mass(ctx, "lz-tail", [[-8, -10], [-20, -9], [-30, -3], [-32, -1], [-22, -4], [-8, -5]], P, { main: true });
      mass(ctx, "lz-body", [[-10, -5], [-10, -11], [-2, -14], [10, -13], [14, -9], [12, -5], [0, -4]], P, { main: true });
      for (const x of [-6, -1, 4]) ink(ctx, `lz-sp${x}`, [[x - 2, -13.4], [x, -18.4], [x + 2, -13.6]], P.mat === "fur" ? "#c0392b" : P.l, { sharp: true, shade: false, w: 0.5 });
      back(ctx, "lz", [[-14, -9], [8, -13]], P);
      for (const x of [-7, 10]) mass(ctx, `lz-l${x}`, [[x - 2, -7], [x + 2, -7], [x + 3, 0], [x - 2.6, 0]], P);
      mass(ctx, "lz-head", [[12, -12], [16, -15], [23, -14], [27, -11], [26, -9], [18, -8], [13, -8]], P, { main: true });
      eye(ctx, 19, -12.4, P, 0.85);
    } },
    serpent: { qHead: ["sn-head", 6, -23, 1.3],  zh: "蛇", fur: "#5a7a3a", top: -30, head: [12, -26], len: 17, sp: [[-10, -7], [-1, -10.4]], draw(ctx, P) {
      mass(ctx, "sn-coil", ellPts(-4, -3.6, 13, 4.2, 20), P, { main: true });
      mass(ctx, "sn-coil2", ellPts(-2, -7.4, 8.4, 3.2, 16), P, { color: P.d });
      mass(ctx, "sn-neck", [[1, -6], [8, -6], [10, -16], [9, -24], [4, -24], [5, -16]], P, { main: true });
      stroke(ctx, "sn-belly", [[8.6, -7], [9.4, -16], [8.4, -23]], 1.4, P.mat === "fur" ? "#e8dca0" : P.l);
      back(ctx, "sn", [[-10, -7], [-1, -10.4]], P);
      mass(ctx, "sn-head", [[3, -25], [8, -29.4], [15, -28.4], [18.4, -25], [14, -22], [6, -22]], P, { main: true });
      stroke(ctx, "sn-tongue", [[18.4, -24.6], [21.6, -24.6], [23, -26]], 0.5, "#d23c3c"); stroke(ctx, "sn-tongue2", [[21.6, -24.6], [23, -23.4]], 0.5, "#d23c3c");
      eye(ctx, 12, -26.4, P, 0.85);
    } },
    shell: { qHead: ["sh-head", 12, -7, 1.3],  zh: "龜殼", fur: "#5a6a4a", top: -23, head: [16, -9], len: 20, sp: [[-9, -21], [-2, -22.6], [5, -21.4]], draw(ctx, P) {
      for (const x of [-9, 6]) mass(ctx, `sh-lf${x}`, [[x - 3, -7], [x + 2, -7], [x + 2, 0], [x - 3.4, 0]], P, { color: P.d });
      const dome = [[-15, -6], [-14, -15], [-7, -22], [4, -22], [11, -16], [12, -6], [0, -5]];
      mass(ctx, "sh-dome", dome, P, { main: true });
      for (const [i, l] of [[[-8, -21], [-9, -7]], [[3, -21], [2, -7]], [[-14, -12.4], [11.4, -12.4]]].entries()) stroke(ctx, `sh-plate${i}`, l, 0.6);
      stroke(ctx, "sh-rim", [[-16, -6], [13, -6]], 2.2, INK); stroke(ctx, "sh-rim2", [[-16, -6], [13, -6]], 1.2, P.l);
      back(ctx, "sh", [[-9, -21], [-2, -22.6], [5, -21.4]], P);
      for (const x of [-11, 5]) mass(ctx, `sh-l${x}`, [[x, -7], [x + 5, -7], [x + 5.6, 0], [x - 0.4, 0]], P, { color: P.l });
      mass(ctx, "sh-head", [[11, -11], [16, -12], [20, -9], [19, -5], [13, -5]], P, { color: P.l });
      eye(ctx, 17, -9.4, P, 0.8);
    } },
    ooze: { zh: "軟泥", fur: "#6a9a5a", top: -18, head: [6, -10], len: 15, sp: [[-6, -15], [2, -16.6]], draw(ctx, P) {
      const blob = [[-13, 0], [-14, -6], [-10, -13], [-3, -17], [5, -16], [11, -11], [13, -4], [12, 0]];
      mass(ctx, "oz-blob", blob, P, { main: true, alpha: 0.9 });
      for (const [x, y, r] of [[-6, -6, 1.8], [-2, -11, 1.2], [8, -5, 1.4]]) ink(ctx, `oz-bub${x}`, ellPts(x, y, r, r, 8), P.l, { shade: false, w: 0.4 });
      back(ctx, "oz", [[-6, -15], [2, -16.6]], P);
      mark("oz-face"); eye(ctx, 4.6, -10, P, 0.9); eye(ctx, 8.4, -10.2, P, 0.8);
    } },
    golem: { qHead: ["go-head", 1, -40, 1.28, "go-arm"], zh: "傀儡", core: [-1, -29], fur: "#8a847e", top: -49, head: [2, -44], len: 17, sp: [[-9, -38.4], [-3, -39.6], [3, -40]], draw(ctx, P) {
      mass(ctx, "go-legf", [[-7, -16], [-1, -16], [-1.6, 0], [-8, 0]], P, { color: P.d });
      mass(ctx, "go-armf", [[-10, -37], [-15, -34], [-17, -18], [-12, -17], [-11, -30]], P, { color: P.d });
      mass(ctx, "go-legn", [[0, -16], [6, -16], [6.6, 0], [-0.4, 0]], P);
      const torso = [[-11, -38], [8, -40], [12, -30], [9, -16], [-9, -16], [-12, -28]];
      mass(ctx, "go-torso", torso, P, { main: true });
      back(ctx, "go", [[-9, -38.4], [-3, -39.6]], P);
      mass(ctx, "go-head", [[-4, -40], [-3, -47], [4, -48], [7, -43], [5, -39]], P);
      ink(ctx, "go-eye", [[2.4, -44.6], [6.4, -44.6], [6.4, -43], [2.4, -43]], P.accent ?? "#ffd23a", { shade: false, w: 0.4, sharp: true });
      mass(ctx, "go-arm", [[4, -38], [11, -38], [16, -24], [16, -14], [10, -14], [9, -24]], P, { main: true });
      mass(ctx, "go-fist", ellPts(13, -12, 4, 3.6, 12), P);
    } },
    wisp: { zh: "晶靈", fur: "#9a86ff", top: -34, core: [0, -20], head: [0, -22], len: 12, hover: true, sp: [[0, -31]], draw(ctx, P) {
      ctx.save(); ctx.translate(0, -20);
      for (const [i, [x, y, s]] of [[-11, -5, 2.4], [10, -8, 2], [3, 9, 1.8]].entries()) mass(ctx, `wp-or${i}`, [[x, y - s * 1.6], [x + s, y], [x, y + s * 1.6], [x - s, y]], P, { sharp: true, shade: false, w: 0.5, color: P.l });
      const core = [[0, -11], [7.4, 0], [0, 11], [-7.4, 0]];
      mass(ctx, "wp-core", core, P, { main: true, sharp: true });
      ink(ctx, "wp-in", [[0, -5], [3.4, 0], [0, 5], [-3.4, 0]], P.accent ?? P.eye, { sharp: true, shade: false, w: 0.4 });
      dot(ctx, 1.2, -0.6, 0.9, 1.3, INK);
      ctx.restore();
    } },
    feline: { qHead: ["fe-ear", 11, -12, 1.35],  zh: "豹", fur: "#c8a060", top: -23, head: [15, -15], len: 22, sp: [[-8, -15], [-2, -16], [4, -15.6]], draw(ctx, P) {
      for (const x of [-8, 10]) mass(ctx, `fe-lf${x}`, [[x - 1.6, -9], [x + 1.6, -9], [x + 1.8, 0], [x - 1.8, 0]], P, { color: P.d, shade: false, w: 0.6 });
      mass(ctx, "fe-tail", [[-12, -12.4], [-21, -12], [-26, -7], [-24, -5.4], [-20, -9], [-12, -9]], P);
      mass(ctx, "fe-body", ellPts(0, -11, 14, 5, 20), P, { main: true });
      back(ctx, "fe", [[-6, -15.6], [2, -16]], P);
      for (const x of [-11, 7]) mass(ctx, `fe-l${x}`, [[x - 1.7, -9], [x + 1.7, -9], [x + 2, 0], [x - 2, 0]], P, { shade: false, w: 0.6 });
      for (const x of [13, 17.4]) mass(ctx, `fe-ear${x}`, [[x - 2.2, -16.6], [x, -21.6], [x + 2.2, -16.6]], P, { w: 0.6, sharp: true });
      mass(ctx, "fe-head", ellPts(15, -14.5, 5.4, 4.6, 16), P, { main: true });
      ink(ctx, "fe-muzzle", ellPts(19.2, -13, 2.2, 1.6, 10), P.l, { shade: false, w: 0.5 });
      eye(ctx, 17.2, -15.4, P, 0.9); dot(ctx, 21, -13.4, 0.6, 0.5, INK);
    } },
    wraith: { zh: "霧魅", fur: "#e6ecef", top: -46, head: [0, -42], len: 12, hover: true, sp: [[-4, -40], [4, -40]], draw(ctx, P) {
      ctx.save(); ctx.translate(0, -4);
      limb(ctx, "wr-arm-l", [[-7, -30], [-12, -22], [-14, -16]], 2.2, P.base);
      mass(ctx, "wr-body", [[-8, -34], [-10, -20], [-7, -8], [-4, -2], [-1, -6], [2, -1], [5, -6], [9, -18], [8, -34]], P, { main: true });
      mass(ctx, "wr-head", ellPts(0, -38, 6, 6.4, 14), P);
      for (const x of [-2.4, 2.4]) { dot(ctx, x, -38, 1.9, 2.1, dark(P.base, 0.55)); eye(ctx, x, -38, { eye: light(P.eye, 0.4) }, 0.85); } // Q：暗色眼窩＋方眼，霧材質、任何元素都看得到
      limb(ctx, "wr-arm-r", [[7, -30], [12, -23], [15, -18]], 2.2, P.base);
      ctx.restore();
    } },
    pylon: { zh: "晶塔", fur: "#8a847e", top: -40, head: [1, -24], len: 9, sp: [[0, -38]], draw(ctx, P) {
      ink(ctx, "py-base", [[-8, 0], [-9, -5], [9, -5], [8, 0]], "#6a645e", { w: 0.7 });
      mass(ctx, "py-ob", [[-5, -5], [-4, -30], [0, -38], [4, -30], [5, -5]], P, { main: true, sharp: true });
      ink(ctx, "py-eye", ellPts(1.6, -22, 1.8, 2.4, 10), P.accent ?? P.eye, { shade: false, w: 0.4 });
      dot(ctx, 2, -22, 0.5, 1.2, INK);
      ctx.save(); ctx.globalAlpha = 0.8; stroke(ctx, "py-ring", ellPts(0, -22, 8.6, 2.4, 20).concat([[8.6, -22]]), 0.7, P.accent ?? P.l); ctx.restore();
    } },
  };
  // ============================== 動畫掛點（RIG）：部件名稱開頭 → 部件組；組的支點（身形座標；飛禽、晶靈、霧魅是 draw 裡平移後的區域座標） ==============================
  // 腿：支點在髖／肩（埋在身體裡），動畫用斜切 kx（腳底前後擺、上緣不動）＋sy（抬腳＝腿縮短），不會和身體脫開。
  // 腿名：BF＝遠側後腿、FF＝遠側前腿、BN＝近側後腿、FN＝近側前腿（對角步：FN＋BF 一組、FF＋BN 一組）。
  const RIG = {
    hound: { groups: [["hd-lf-12", "BF"], ["hd-lf6", "FF"], ["hd-l-9", "BN"], ["hd-l8", "FN"], ["hd-tail", "tail"], ["hd-ear", "head"], ["hd-head", "head"], ["hd-fang", "head"]],
      pivots: { BF: [-10, -15], FF: [8, -15], BN: [-7, -16], FN: [10, -16], tail: [-14, -18], head: [12, -21], body: [0, -12] } },
    boar: { groups: [["bo-lf-10", "BF"], ["bo-lf6", "FF"], ["bo-l-7", "BN"], ["bo-l8", "FN"], ["bo-tail", "tail"], ["bo-ear", "head"], ["bo-head", "head"], ["bo-snout", "head"], ["bo-tusk", "head"]],
      pivots: { BF: [-8, -12], FF: [8, -12], BN: [-5, -12], FN: [10, -12], tail: [-15, -16], head: [11, -15], body: [0, -9] } },
    bear: { groups: [["be-lf-11", "BF"], ["be-lf6", "FF"], ["be-l-6", "BN"], ["be-l11", "FN"], ["be-head", "head"], ["be-ear", "head"], ["be-snout", "head"]],
      pivots: { BF: [-11, -15], FF: [6, -15], BN: [-6, -15], FN: [11, -15], head: [12, -22], body: [0, -10] } },
    bat: { groups: [["fl-bwf", "wingF"], ["fl-bwn", "wingN"], ["fl-be", "head"], ["fl-bhead", "head"], ["fl-bfang", "head"]],
      pivots: { wingF: [-1, -2], wingN: [2, -2], head: [4, -3], body: [0, 0] } },
    bird: { groups: [["fl-wf", "wingF"], ["fl-tail", "tail"], ["fl-wn", "wingN"], ["fl-sh", "wingN"], ["fl-head", "head"], ["fl-beak", "head"], ["fl-claw", "legs"]],
      pivots: { wingF: [-1, -3], wingN: [3, -3], tail: [-8, 0], head: [6, -2], legs: [0, 4], body: [0, 0] } },
    spider: { groups: [["sp-lf0", "F0"], ["sp-lf1", "F1"], ["sp-lf2", "F2"], ["sp-lf3", "F3"], ["sp-abd", "abd"], ["sp-sh", "spikes"], ["sp-mark", "abd"], ["sp-head", "head"], ["sp-eyes", "head"], ["sp-fang", "head"],
      ["sp-l0", "N0"], ["sp-l1", "N1"], ["sp-l2", "N2"], ["sp-l3", "N3"]],
      pivots: { F0: [-1.2, -10.6], F1: [0.8, -10.6], F2: [2.8, -10.6], F3: [4.8, -10.6], N0: [1, -10], N1: [3, -10], N2: [5, -10], N3: [7, -10], abd: [-3, -10], spikes: [-9, -19.5], head: [2, -9], body: [0, -6] } },
    beetle: { groups: [["bt-lf0", "F0"], ["bt-lf1", "F1"], ["bt-lf2", "F2"], ["bt-l0", "N0"], ["bt-l1", "N1"], ["bt-l2", "N2"], ["bt-head", "head"], ["bt-horn", "head"], ["bt-eye", "head"], ["bt-sh", "spikes"]],
      pivots: { F0: [-6, -7], F1: [2, -7], F2: [9, -7], N0: [-8, -7], N1: [0, -7], N2: [7, -7], head: [11, -10], spikes: [-2, -20], body: [0, -8] } },
    lizard: { groups: [["lz-lf-6", "BF"], ["lz-lf9", "FF"], ["lz-l-7", "BN"], ["lz-l10", "FN"], ["lz-tail", "tail"], ["lz-head", "head"]],
      pivots: { BF: [-6, -7], FF: [9, -7], BN: [-7, -8], FN: [10, -8], tail: [-8, -7.5], head: [13, -10], body: [2, -8] } },
    serpent: { groups: [["sn-coil", "coil"], ["sn-sh", "coil"], ["sn-neck", "neck"], ["sn-belly", "neck"], ["sn-head", "head"], ["sn-tongue", "head"]],
      pivots: { coil: [-4, -1], neck: [5, -6], head: [7, -24], body: [0, -6] } },
    shell: { groups: [["sh-lf-9", "BF"], ["sh-lf6", "FF"], ["sh-l-11", "BN"], ["sh-l5", "FN"], ["sh-head", "head"]],
      pivots: { BF: [-10, -9], FF: [5, -9], BN: [-9, -9], FN: [8, -9], head: [12, -8], body: [0, -6] } },
    ooze: { groups: [["oz-face", "face"]], pivots: { face: [6, -10], body: [0, 0] } },
    golem: { groups: [["go-legf", "legF"], ["go-armf", "armF"], ["go-legn", "legN"], ["go-head", "head"], ["go-eye", "head"], ["go-arm", "armN"], ["go-fist", "armN"]],
      pivots: { legF: [-4, -17], legN: [3, -17], armF: [-11, -35], armN: [7, -37], head: [1, -40], body: [0, -16] } },
    wisp: { groups: [["wp-or0", "orb0"], ["wp-or1", "orb1"], ["wp-or2", "orb2"], ["wp-core", "core"], ["wp-in", "core"]],
      pivots: { orb0: [-11, -5], orb1: [10, -8], orb2: [3, 9], core: [0, 0], body: [0, 0] } },
    feline: { groups: [["fe-lf-8", "BF"], ["fe-lf10", "FF"], ["fe-l-11", "BN"], ["fe-l7", "FN"], ["fe-tail", "tail"], ["fe-ear", "head"], ["fe-head", "head"], ["fe-muzzle", "head"]],
      pivots: { BF: [-8, -12], FF: [10, -12], BN: [-11, -12], FN: [7, -12], tail: [-12, -11], head: [11, -12], body: [0, -9] } },
    wraith: { groups: [["wr-arm-l", "armB"], ["wr-arm-r", "armN"], ["wr-head", "head"]],
      pivots: { armB: [-7, -30], armN: [7, -30], head: [0, -33], body: [0, -20] } },
    pylon: { groups: [["py-base", "base"], ["py-ob", "ob"], ["py-eye", "eye"], ["py-ring", "ring"]],
      pivots: { base: [0, 0], ob: [0, -5], eye: [1.6, -22], ring: [0, -22], body: [0, -5] } },
  };
  const rigKey = (r) => r.variant ?? r.body;
  const MATERIALS = ["fur", "magma", "crystal", "stone", "wood", "mist"];
  const SIZES = { tiny: 0.62, small: 0.8, normal: 1, medium: 1, large: 1.25, huge: 1.6 };
  // ============================== 特徵 traits（外觀提示用的小部件；不認得的跳過） ==============================
  const TRAITS = {
    stone_back: { zh: "背上石板", draw(ctx, a, P) { a.sp.forEach(([x, y], i) => ink(ctx, `tr-sb${i}`, [[x - 3, y + 1.4], [x - 1.6, y - 4.4 - (i % 2) * 1.6], [x + 2.6, y - 3.4], [x + 3, y + 1.4]], "#8a8f94", { sharp: true, w: 0.7 })); } },
    volcano: { zh: "背上小火山", draw(ctx, a, P) {
      const [x, y] = a.sp[Math.floor(a.sp.length / 2)];
      ink(ctx, "tr-vc", [[x - 6, y + 2], [x - 2, y - 6], [x + 2, y - 6], [x + 6, y + 2]], "#4a3a34", { w: 0.7 });
      ink(ctx, "tr-vc-mouth", ellPts(x, y - 6, 2, 0.8, 10), P.accent ?? ELEM.fire[0], { shade: false, w: 0.4 });
      for (const [i, [dx, dy, r]] of [[-0.6, -9.6, 1.6], [1.6, -12.4, 1.9]].entries()) ink(ctx, `tr-vc-sm${i}`, ellPts(x + dx, y + dy, r, r, 10), "#9a9490", { shade: false, w: 0.4, alpha: 0.75 });
    } },
    smoke: { zh: "黃煙", soft: true, draw(ctx, a) { // Q：無外框、半透明，從背上往上飄、越高越大越淡
      for (const [i, [x, y, r, al]] of [[-a.len * 0.25, a.top - 1, 2, 0.6], [-a.len * 0.1, a.top - 5.5, 2.8, 0.45], [a.len * 0.05, a.top - 11, 3.6, 0.3]].entries()) { ctx.save(); ctx.globalAlpha = al; ink(ctx, `tr-sk${i}`, ellPts(x, y, r, r * 0.85, 12), "#e8d860", { line: false }); ctx.restore(); }
    } },
    mist: { zh: "霧氣繞身", soft: true, draw(ctx, a) {
      ctx.save(); ctx.globalAlpha = 0.55;
      for (const [i, [x, y, r]] of [[-a.len * 0.7, -2, 3.4], [-a.len * 0.1, -1, 4], [a.len * 0.6, -2.4, 3]].entries()) ink(ctx, `tr-ms${i}`, ellPts(x, y, r, r * 0.55, 12), "#eef2f4", { shade: false, line: false });
      stroke(ctx, "tr-ms-l", [[-a.len, -6], [-a.len * 0.4, -8], [0, -6]], 0.5, "#ffffff");
      ctx.restore();
    } },
    core: { zh: "胸口熔核", draw(ctx, a, P) {
      const [x, y] = a.core ?? a.head, c = P.accent ?? ELEM.fire[0];
      ink(ctx, "tr-core", ellPts(x, y, 3.2, 3.2, 12), c, { shade: false, w: 0.6 }); dot(ctx, x - 0.6, y - 0.8, 1.2, 1.2, light(c, 0.6));
    } },
    crust: { zh: "甲蟲殼堆（熔殼）", draw(ctx, a) {
      // 灰燼之心第 1 階段：熔岩甲蟲背殼一片片疊成外殼，殼縫透出火光；殼裂開（移除熔殼）後就不畫
      const [cx, cy] = a.core ?? a.head;
      const plates = [[-7, 3, -0.5], [6.6, 3.4, 0.5], [-8.6, -5, -1.1], [8, -5.6, 1.1], [-3.4, -10.6, -0.3], [3.8, -10.4, 0.35], [0, 6.6, 0]];
      for (const [i, [dx, dy, rot]] of plates.entries()) {
        const x = cx + dx, y = cy + dy, c = Math.cos(rot), sn = Math.sin(rot), q = (u, v) => [x + u * c - v * sn, y + u * sn + v * c];
        ink(ctx, `tr-cr${i}`, [q(-4.4, 2.6), q(-3.6, -2.4), q(0, -3.6), q(3.6, -2.4), q(4.4, 2.6), q(0, 3.4)], BASALT, { w: 0.7 });
        stroke(ctx, `tr-crl${i}`, [q(0, -3.2), q(0, 3)], 0.45, "#1c1412");
      }
      for (const [i, [x0, y0, x1, y1]] of [[-2, -1, 2, -2], [-4, 6, -1, 9], [3, 5, 5, 8]].entries()) stroke(ctx, `tr-crg${i}`, [[cx + x0, cy + y0], [cx + x1, cy + y1]], 0.9, ELEM.fire[1]);
    } },
    scar: { zh: "疤", draw(ctx, a) { const [x, y] = a.head; stroke(ctx, "tr-scar1", [[x - 3, y - 3], [x + 1, y + 2]], 0.8, "#5a2a22"); stroke(ctx, "tr-scar2", [[x - 1.6, y - 1.2], [x - 3, y]], 0.6, "#5a2a22"); } },
    brood: { zh: "背負卵囊", draw(ctx, a, P) { a.sp.forEach(([x, y], i) => ink(ctx, `tr-egg${i}`, ellPts(x, y - 2, 2.4, 3, 10), P.accent ?? "#ffb23a", { shade: false, w: 0.5 })); } },
    lava_pool: { zh: "背負熔岩池", draw(ctx, a, P) {
      const [x0, y0] = a.sp[0], [x1] = a.sp[a.sp.length - 1];
      ink(ctx, "tr-pool-rim", [[x0 - 5, y0 + 1], [x0 - 3, y0 - 3], [x1 + 3, y0 - 4], [x1 + 5, y0], [x1 + 3, y0 + 3], [x0 - 3, y0 + 3]], "#4a3a34", { w: 0.7 });
      ink(ctx, "tr-pool", ellPts((x0 + x1) / 2, y0 - 1.4, (x1 - x0) / 2 + 2, 1.4, 14), P.accent ?? ELEM.fire[0], { shade: false, w: 0.4 });
    } },
    spots: { zh: "斑紋", draw(ctx, a, P) { mark("tr-spots"); for (const [x, y] of [[-8, -12], [-3, -14], [2, -11.4], [-5, -9.4], [8, -12.4]]) dot(ctx, x, y, 1.1, 0.8, P.d); } },
    sparks: { zh: "電光", draw(ctx, a) { for (const [i, [x, y]] of [[-a.len * 0.5, a.top * 0.75], [a.len * 0.6, a.top * 0.85]].entries()) stroke(ctx, `tr-spk${i}`, [[x, y], [x + 2, y + 2], [x, y + 3], [x + 2.4, y + 5.4]], 0.9, "#fff36b"); } },
  };

  // ============================== 精英詞綴（疊在身上；人形敵人同一套） ==============================
  const AFFIX = {
    berserk: { zh: "狂暴的", draw(ctx, a) {
      const [hx, hy] = a.head;
      for (const [i, [dx, dy, r]] of [[-3, -6, 1.8], [1, -9, 2.2], [4.6, -6.4, 1.6]].entries()) ink(ctx, `af-bz${i}`, ellPts(hx + dx, hy + dy, r, r, 10), "#ff8a7a", { shade: false, w: 0.45, alpha: 0.8 });
      for (const s of [-1, 1]) stroke(ctx, `af-bzv${s}`, [[hx - 1 + s * 1.4, hy - 3.2], [hx + s * 0.6, hy - 2], [hx + 1 + s * 1.4, hy - 3.2]], 0.8, "#e02a2a");
    } },
    regen: { zh: "再生的", draw(ctx, a) {
      for (const [i, [x, y]] of [[-a.len * 0.7, a.top * 0.45], [a.len * 0.5, a.top * 0.75], [-a.len * 0.2, a.top * 0.95], [a.len * 0.85, a.top * 0.3]].entries()) {
        stroke(ctx, `af-rg${i}a`, [[x - 1.8, y], [x + 1.8, y]], 1.1, "#3f9a4a"); stroke(ctx, `af-rg${i}b`, [[x, y - 1.8], [x, y + 1.8]], 1.1, "#3f9a4a");
        stroke(ctx, `af-rg${i}c`, [[x - 1.4, y], [x + 1.4, y]], 0.55, "#b6f0a0"); stroke(ctx, `af-rg${i}d`, [[x, y - 1.4], [x, y + 1.4]], 0.55, "#b6f0a0");
      }
    } },
    armored: { zh: "堅甲的", draw(ctx, a) {
      const y = a.armorY ?? a.top * (a.hover ? 0.55 : 0.6);
      for (const [i, x] of [-a.len * 0.35, a.len * 0.1].entries()) ink(ctx, `af-ar${i}`, [[x - 4, y - 1.4], [x + 4, y - 2.4], [x + 4.6, y + 3], [x - 3.6, y + 3.6]], "#8d969f", { w: 0.7 });
      for (const [i, x] of [-a.len * 0.35, a.len * 0.1].entries()) dot(ctx, x, y + 0.6, 0.6, 0.6, "#3c4248");
    } },
    swift: { zh: "迅捷的", draw(ctx, a) {
      for (const [i, y] of [a.top * 0.3, a.top * 0.55, a.top * 0.8].entries()) stroke(ctx, `af-sw${i}`, [[-a.len - 3 - i * 2, y], [-a.len - 11 - i * 2, y]], 0.9, "#e8e8ea");
    } },
    elemental: { zh: "元素的", draw(ctx, a) {
      const c = ELEM[a.element] ?? ELEM.fire;
      for (const [i, x] of [-a.len * 0.6, a.len * 0.1, a.len * 0.75].entries()) {
        ink(ctx, `af-el${i}`, [[x - 2, 0.6], [x - 0.6, -4.4], [x, -2.4], [x + 1, -6.4], [x + 2.2, 0.6]], c[0], { sharp: true, shade: false, w: 0.45, alpha: 0.9 });
        dot(ctx, x + 0.2, -1, 0.8, 1, c[1]);
      }
    } },
    // 玩法 PM 清單（#111）的區域詞綴
    mist_hidden: { zh: "霧隱的", soft: true, draw(ctx, a) { // 邊緣模糊：身邊幾團白霧（本體在 stamp 裡另外降到 75% 不透明）
      ctx.save(); ctx.globalAlpha = 0.6;
      for (const [i, [x, y, r]] of [[-a.len * 0.8, a.top * 0.4, 3.6], [a.len * 0.7, a.top * 0.65, 3.2], [-a.len * 0.2, a.top * 0.95, 3], [a.len * 0.2, -1.4, 4]].entries()) ink(ctx, `af-mh${i}`, ellPts(x, y, r, r * 0.7, 12), "#eef2f4", { shade: false, line: false });
      ctx.restore();
    } },
    linked: { zh: "連心的", draw(ctx, a) { // 與同伴連線：頭上一顆青色連心結；連到相鄰同門的虛線由戰場繪製器畫（樣張畫兩段示意）
      const [hx] = a.head, y = a.top - 4;
      for (const s of [-1, 1]) stroke(ctx, `af-lk${s}`, [[hx + s * 1.6, y + 2], [hx + s * 3.4, y - 0.4], [hx + s * 1.6, y - 2.4], [hx, y - 0.6]], 1, "#3fd0c0");
      ctx.save(); ctx.setLineDash([1.6, 1.4]); for (const s of [-1, 1]) stroke(ctx, `af-lkl${s}`, [[s * (a.len + 2), -3], [s * (a.len + 12), -4]], 0.8, "#3fd0c0"); ctx.restore();
    } },
    blazing: { zh: "熾熱的", draw(ctx, a) { // 周圍熱浪：頭上方三道波浪線
      for (const [i, x] of [-a.len * 0.5, 0, a.len * 0.5].entries()) stroke(ctx, `af-bl${i}`, [[x, a.top - 1], [x + 1.4, a.top - 3.4], [x - 0.4, a.top - 5.8], [x + 1, a.top - 8]], 0.8, "#ffb23a");
    } },
    hardshell: { zh: "硬殼的", draw(ctx, a) { // 外殼發亮：背上兩道白色反光
      a.sp.forEach(([x, y], i) => { if (i < 2) stroke(ctx, `af-hs${i}`, [[x - 2.4, y + 2], [x + 1.6, y + 0.6]], 1.1, "#ffffff"); });
      dot(ctx, a.sp[0][0] + 3, a.sp[0][1] - 1, 0.9, 0.9, "#ffffff");
    } },
    // mirror（分身的）在 stamp 裡畫：身後錯開一個 35% 半透明的分身
  };
  const AFFIX_ZH = Object.fromEntries(Object.entries(AFFIX).map(([k, v]) => [k, v.zh]).concat([["mirror", "分身的"]]));

  // ============================== 地面環（陣營環＋精英金環；平塗） ==============================
  function ring(ctx, rx, opt = {}) {
    ctx.save();
    ctx.globalAlpha = 0.3; ctx.fillStyle = "#d24a3a"; ctx.beginPath(); ctx.ellipse(0, 0, rx, rx * 0.3, 0, 0, TAU); ctx.fill();
    ctx.globalAlpha = 0.95; ctx.strokeStyle = "#d24a3a"; ctx.lineWidth = 1.1; ctx.stroke();
    if (opt.elite) {
      ctx.globalAlpha = 1; ctx.strokeStyle = OUT; ctx.lineWidth = 2.4; ctx.beginPath(); ctx.ellipse(0, 0, rx + 2.2, (rx + 2.2) * 0.3, 0, 0, TAU); ctx.stroke();
      ctx.strokeStyle = "#ffbf3a"; ctx.lineWidth = 1.2; ctx.stroke();
      // 環前方一顆金菱形（精英記號，小尺寸也看得到）：金色平塗＋黑外框
      const y0 = (rx + 2.2) * 0.3 - 0.4, gem = [[0, y0], [2.6, y0 + 2.6], [0, y0 + 5.2], [-2.6, y0 + 2.6]];
      ctx.beginPath(); gem.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath();
      ctx.lineJoin = "round"; ctx.strokeStyle = OUT; ctx.lineWidth = 1.6; ctx.stroke(); ctx.fillStyle = "#ffbf3a"; ctx.fill();
      ctx.fillStyle = "#fff2c0"; ctx.fillRect(-0.5, y0 + 1.2, 1, 1);
    }
    ctx.restore();
  }

  // ============================== 剪影外框（同 qDoll.js stamp：離屏畫好 → 剪影染黑 → 膨脹 → 墊在底下） ==============================
  const mkc = (w, h) => { const c = document.createElement("canvas"); c.width = Math.max(1, w); c.height = Math.max(1, h); return c; };
  function tint(src, color) { const c = mkc(src.width, src.height), g = c.getContext("2d"); g.drawImage(src, 0, 0); g.globalCompositeOperation = "source-in"; g.fillStyle = color; g.fillRect(0, 0, c.width, c.height); return c; }
  function dilate(src, r, N = 16) {
    const c = mkc(src.width, src.height), g = c.getContext("2d");
    for (const f of [1, 0.66, 0.33]) for (let i = 0; i < N; i++) { const a = (i / N) * TAU; g.drawImage(src, Math.cos(a) * r * f, Math.sin(a) * r * f); }
    g.drawImage(src, 0, 0); return c;
  }
  /**
   * 在目前座標系的 box [x0, y0, x1, y1]（單位）裡畫一層：draw(g) 畫平塗部件；外框 ow 單位（預設 1.3，和 Q 版主角同粗）。
   * o.alpha：本體透明度（霧）；o.glow：頭目外光色（剪影再膨脹 glowW 單位、半透明平塗，外光只給頭目）。
   * 離屏解析度跟著目前的變換走（getTransform），放大縮小都清楚；鏡像由呼叫端的 ctx.scale(-1, 1) 處理。
   */
  function layer(ctx, box, draw, o = {}) {
    const T = ctx.getTransform(), m = Math.max(0.5, Math.hypot(T.a, T.b));
    const W = Math.ceil((box[2] - box[0]) * m), H = Math.ceil((box[3] - box[1]) * m);
    const off = mkc(W, H), g = off.getContext("2d"); g.setTransform(m, 0, 0, m, -box[0] * m, -box[1] * m); draw(g);
    const ow = (o.ow ?? 1.3) * m, rim = dilate(tint(off, OUT), ow), rg = rim.getContext("2d");
    rg.globalCompositeOperation = "destination-out"; rg.drawImage(off, 0, 0);
    if (o.fade) { // o.fade＝[下緣 y, 開始淡出的 y]（單位）：分 3 段平塗淡出（不是漸層），本體和外框一起
      const [yb, yt] = o.fade;
      for (const c of [off, rim]) { const q = c.getContext("2d"); q.save(); q.setTransform(m, 0, 0, m, -box[0] * m, -box[1] * m); q.globalCompositeOperation = "destination-out";
        [0.35, 0.65, 0.92].forEach((al, i) => { const y0 = yt + ((yb - yt) * i) / 3, y1 = i === 2 ? box[3] : yt + ((yb - yt) * (i + 1)) / 3; q.globalAlpha = al; q.fillRect(box[0], y0, box[2] - box[0], y1 - y0); }); q.restore(); }
    }
    ctx.save();
    const put = (c, a) => { ctx.globalAlpha = a; ctx.drawImage(c, box[0], box[1], W / m, H / m); };
    if (o.flat) { put(tint(off, o.flat), o.alpha ?? 1); ctx.restore(); return; } // 整隻剪影單色平塗（殘影用）
    if (o.glow) { const gl = dilate(tint(off, o.glow), ow + (o.glowW ?? 2.6) * m, 24), gg = gl.getContext("2d"); gg.globalCompositeOperation = "destination-out"; gg.drawImage(off, 0, 0); put(gl, o.glowA ?? 0.6); }
    const a = o.alpha ?? 1;
    put(rim, a < 1 ? Math.min(1, a + 0.2 * Math.min(1, a * 5)) : 1); // 外框比本體實一點；本體淡到 0.2 以下時外框跟著淡（動畫消散用；靜態的霧 0.62 不變）
    put(off, a);
    if (o.flash > 0) put(tint(off, o.flashColor ?? "#ffffff"), Math.min(1, o.flash) * a); // 受擊白閃（動畫用；預設沒有）
    ctx.restore();
  }

  // ============================== 組合 ==============================
  function resolve(spec) {
    const body = BODIES[spec.body] ? spec.body : "ooze";
    const b = BODIES[body];
    const size = (SIZES[spec.size] ?? 1) * (spec.elite ? 1.15 : 1);
    const affixes = (spec.affixes ?? []).filter((a) => AFFIX[a] || a === "mirror");
    const traits = (spec.traits ?? []).filter((t) => TRAITS[t]);
    const element = ELEM[spec.element] ? spec.element : undefined;
    const variant = body === "flyer" ? (spec.variant === "bat" ? "bat" : "bird") : body === "crawler" ? (spec.variant === "spider" ? "spider" : "beetle") : undefined;
    return { ...spec, body, b, size, affixes, traits, element, variant, P: palette({ ...spec, element }, b, SIZES[spec.size] ?? 1) };
  }
  function drawBody(ctx, r) {
    const info = { head: r.b.head, top: r.b.top, len: r.b.len, sp: r.b.sp, core: r.b.core };
    QHEAD = (r.b.qHeadBy ? r.b.qHeadBy[r.variant] : r.b.qHead) ?? null; IN_HEAD = false; HEAD_DONE = false; LAST = "body";
    r.b.draw(ctx, r.P, r.variant);
    if (IN_HEAD) ctx.restore();
    QHEAD = null; IN_HEAD = false; HEAD_DONE = false;
    for (const t of r.traits) if (!TRAITS[t].soft && t !== "sparks") TRAITS[t].draw(ctx, info, r.P);
  }
  const BOX = [-62, -84, 62, 18];
  /** 畫在 (cx, cy)（腳底）、倍率 k、west 鏡像。spec.glow：頭目外光色（史詩 #b06cff、傳說 #ffbf3a）。 */
  function stamp(ctx, spec, cx, cy, k = 1, west = false) {
    const pose = spec.pose ?? null;
    if (pose) { const rg = RIG[rigKey(resolve(spec))]; POSE = pose; GROUPS = rg?.groups ?? null; PIVOTS = rg?.pivots ?? null; }
    try { stampInner(ctx, spec, cx, cy, k, west, pose); } finally { POSE = null; GROUPS = null; PIVOTS = null; LAST = "body"; }
  }
  /** 整隻的變換（pose.root）：{dx, dy, rot, sx, sy, kx, pivot}，支點預設腳底。 */
  function rootXf(ctx, f) {
    if (!f) return; const [px, py] = f.pivot ?? [0, 0];
    ctx.translate(px + (f.dx ?? 0), py + (f.dy ?? 0)); if (f.rot) ctx.rotate(f.rot); if (f.kx) ctx.transform(1, 0, f.kx, 1, 0, 0); ctx.scale(f.sx ?? 1, f.sy ?? 1); ctx.translate(-px, -py);
  }
  function stampInner(ctx, spec, cx, cy, k, west, pose) {
    const r = resolve(spec), s = k * r.size, ow = 1.3 / r.size;
    const info = { head: r.b.head, top: r.b.top, len: r.b.len, sp: r.b.sp, hover: r.b.hover, element: r.element, core: r.b.core };
    ctx.save(); ctx.translate(cx, cy);
    ctx.save(); const rk = k * Math.max(1, r.size * 0.9); ctx.scale(rk, rk); ring(ctx, 13, { elite: spec.elite || !!spec.glow }); ctx.restore();
    const sh = pose?.shadow ?? 1, shx = pose ? (pose.root?.dx ?? 0) * (west ? -1 : 1) : 0;
    if (sh > 0) { ctx.save(); ctx.scale(s, s); ctx.fillStyle = "rgba(10,8,14,0.32)"; ctx.beginPath(); ctx.ellipse(shx, 0.2, Math.max(7, r.b.len * 0.62) * sh, 2.4 * sh, 0, 0, TAU); ctx.fill(); ctx.restore(); }
    ctx.scale(west ? -s : s, s);
    const T0 = ctx.getTransform(); // pose.softGround：霧團、霧隱這類貼地的軟特效留在地面，不跟著整隻掉下去（飛禽倒下用）
    const soft = (fn) => { if (!pose?.softGround) return fn(); ctx.save(); ctx.setTransform(T0); fn(); ctx.restore(); };
    if (pose) { rootXf(ctx, pose.root); if (pose.under) pose.under(ctx, r); }
    const pa = pose?.alpha ?? 1, fl = pose?.flash ?? 0;
    const mist = r.P.mat === "mist" ? 0.62 : 1, hid = r.affixes.includes("mist_hidden") ? 0.75 : 1;
    // 霧團、黃煙、霧隱：無外框、半透明，直接畫（描了黑框會像石頭，審查退回 #5、#6）
    if (r.traits.includes("mist")) soft(() => TRAITS.mist.draw(ctx, info, r.P)); // 霧在身體後面
    const fade = r.P.mat === "mist" ? [1, r.b.top * 0.3] : null; // 霧材質：下緣分 3 段淡出（腳、尾巴斷開），和淺色毛皮分得開
    if (r.affixes.includes("mirror")) layer(ctx, BOX, (g) => { g.translate(-9, -1); drawBody(g, r); }, { ow, alpha: 0.35 * pa, fade });
    layer(ctx, BOX, (g) => drawBody(g, r), pose ? { ow, alpha: mist * hid * pa, glow: spec.glow, fade, flash: fl, flashColor: pose.flashColor } : { ow, alpha: mist * hid, glow: spec.glow, fade });
    if (pose?.over) pose.over(ctx, r);
    for (const t of r.traits) if (TRAITS[t].soft && t !== "mist") soft(() => TRAITS[t].draw(ctx, info, r.P));
    for (const a of r.affixes) if (AFFIX[a]?.soft) soft(() => AFFIX[a].draw(ctx, info));
    const fx = r.affixes.filter((a) => AFFIX[a] && !AFFIX[a].soft), tfx = r.traits.filter((t) => t === "sparks");
    if (fx.length || tfx.length) layer(ctx, BOX, (g) => { for (const t of tfx) TRAITS[t].draw(g, info, r.P); for (const a of fx) AFFIX[a].draw(g, info); }, pa < 1 ? { ow: 0.8 / r.size, alpha: pa } : { ow: 0.8 / r.size });
    ctx.restore();
  }
  // 人形敵人用：精英環＋詞綴特效（Q 版人形畫完後疊上去）。Q 版頭：圓心 (0,-29)、r 8.5，頭頂 -38；
  //   head 點放在頭頂上方（-34）：狂暴的紅霧在頭頂外；堅甲的鐵片在肩胸（armorY -20），不蓋臉。精英由呼叫端把倍率 ×1.15（ELITE_K）。
  const HUMANOID_INFO = { head: [2, -35], top: -40, len: 10, armorY: -20, sp: [[-4, -20], [3, -20]] };
  const ELITE_K = 1.15;
  function ringAt(ctx, cx, cy, k, elite) { ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k); ring(ctx, 13, { elite }); ctx.restore(); }
  function overlay(ctx, affixes, cx, cy, k, element) {
    ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k);
    const fx = (affixes ?? []).filter((a) => AFFIX[a] && !AFFIX[a].soft), info = { ...HUMANOID_INFO, element };
    for (const a of affixes ?? []) if (AFFIX[a]?.soft) AFFIX[a].draw(ctx, info);
    if (fx.length) layer(ctx, BOX, (g) => { for (const a of fx) AFFIX[a].draw(g, info); }, { ow: 0.8 });
    ctx.restore();
  }
  /** 全部身形（含變體）：[body, variant] */
  const ALL = Object.keys(BODIES).flatMap((b) => (b === "flyer" ? [[b, "bird"], [b, "bat"]] : b === "crawler" ? [[b, "beetle"], [b, "spider"]] : [[b, undefined]]));
  return { stamp, resolve, layer, RIG, rigKey, ELITE_K, HUMANOID_INFO, ring, ringAt, overlay, BODIES, ALL, MATERIALS, SIZES, AFFIX_ZH, TRAITS, ELEM, OUT, mix, dark, light, ellPts, seedOf };
})();
