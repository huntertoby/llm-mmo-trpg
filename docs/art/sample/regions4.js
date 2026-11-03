// 碎界其他四區（晶冠、魔導樞市、灰燼荒原、霜潮海境）的地形與物件換皮樣張（美術 PM，2026-11-04）。
// 依據：docs/art/區域外觀換法.md、docs/art/四區移植需求.md。全部程式繪製，沒有下載素材。
// 座標以 52 的虛擬格為單位（同 client 的 ART_T）；物件畫在同一格內，高的物件（擋視線）往上畫到格子頂端。
window.Regions4 = (() => {
  const T = 52;
  const TAU = Math.PI * 2;
  const OUT = "#1c1712";
  function rng(seed) {
    let s = seed >>> 0 || 1;
    return () => {
      s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0;
      return (s % 100000) / 100000;
    };
  }
  const R = (gx, gy, k) => rng((gx * 73856093) ^ (gy * 19349663) ^ (k * 83492791));
  function hexRgb(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  const rgba = (h, a) => { const [r, g, b] = hexRgb(h); return `rgba(${r},${g},${b},${a})`; };
  function shade(h, f) {
    const c = (v) => Math.max(0, Math.min(255, Math.round(v)));
    const [r, g, b] = hexRgb(h);
    return `rgb(${c(r * f)},${c(g * f)},${c(b * f)})`;
  }
  function rr(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  function box(ctx, x, y, w, h, fill, stroke = OUT, lw = 2, r = 2) { rr(ctx, x, y, w, h, r); ctx.fillStyle = fill; ctx.fill(); if (stroke) { ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.stroke(); } }
  function shadow(ctx, cx, cy, rx, ry, a = 0.3) { ctx.fillStyle = `rgba(0,0,0,${a})`; ctx.beginPath(); ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU); ctx.fill(); }
  function glowLine(ctx, color, lw, blur, path) {
    ctx.save(); ctx.shadowColor = color; ctx.shadowBlur = blur; ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = "round";
    ctx.beginPath(); path(); ctx.stroke(); ctx.restore();
  }
  function dot(ctx, x, y, r, fill) { ctx.fillStyle = fill; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); }
  /** 危險記號（會爆）：黃底黑框三角＋驚嘆號，四區共用。 */
  function hazard(ctx, cx, cy, s = 7) {
    ctx.beginPath(); ctx.moveTo(cx, cy - s); ctx.lineTo(cx + s, cy + s * 0.8); ctx.lineTo(cx - s, cy + s * 0.8); ctx.closePath();
    ctx.fillStyle = "#ffd23a"; ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = "#1a1208"; ctx.stroke();
    ctx.fillStyle = "#1a1208"; ctx.fillRect(cx - 1, cy - s * 0.45, 2, s * 0.65); ctx.fillRect(cx - 1, cy + s * 0.32, 2, 2);
  }

  // ======================= 地形（參數化）=======================
  /** 石板類（晶冠白石、霜潮沙岸以外）：p = {base, gap, hi, moss?, inlay?} */
  function slabTile(ctx, gx, gy, p) {
    const r = R(gx, gy, 1);
    ctx.fillStyle = p.gap; ctx.fillRect(0, 0, T, T);
    const split = r() < 0.5;
    const blocks = split ? [[0, 0, 0.55, 0.5], [0.55, 0, 0.45, 0.5], [0, 0.5, 1, 0.5]] : [[0, 0, 1, 0.45], [0, 0.45, 0.4, 0.55], [0.4, 0.45, 0.6, 0.55]];
    for (const [bx, by, bw, bh] of blocks) {
      rr(ctx, bx * T + 1.5, by * T + 1.5, bw * T - 3, bh * T - 3, 3);
      ctx.fillStyle = shade(p.base, 0.93 + r() * 0.14); ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,0.14)"; ctx.fillRect(bx * T + 2, by * T + 2, bw * T - 4, 2);
    }
    if (p.inlay && (gx * 5 + gy * 3) % 7 === 0) { // 金色嵌線（晶冠：偶爾一格）
      ctx.strokeStyle = p.inlay; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(T / 2, 6); ctx.lineTo(T - 6, T / 2); ctx.lineTo(T / 2, T - 6); ctx.lineTo(6, T / 2); ctx.closePath(); ctx.stroke();
      dot(ctx, T / 2, T / 2, 2.5, p.glint ?? p.inlay);
    }
  }
  /** 鉚釘鐵板（樞市）：p = {base, joint, rivet, line} */
  function plateTile(ctx, gx, gy, p) {
    const r = R(gx, gy, 2);
    ctx.fillStyle = shade(p.base, 0.94 + r() * 0.12); ctx.fillRect(0, 0, T, T);
    ctx.strokeStyle = p.joint; ctx.lineWidth = 2; ctx.strokeRect(1, 1, T - 2, T - 2);
    ctx.fillStyle = "rgba(255,255,255,0.08)"; ctx.fillRect(3, 3, T - 6, 2);
    for (const [dx, dy] of [[5, 5], [T - 5, 5], [5, T - 5], [T - 5, T - 5]]) { dot(ctx, dx, dy, 2, p.rivet); dot(ctx, dx - 0.6, dy - 0.6, 0.8, "rgba(255,255,255,0.5)"); }
    if ((gx + gy * 2) % 3 === 0) {
      const horiz = (gx + gy) % 2 === 0;
      glowLine(ctx, p.line, 2, 6, () => {
        if (horiz) { ctx.moveTo(0, T / 2); ctx.lineTo(T * 0.4, T / 2); ctx.lineTo(T * 0.5, T * 0.38); ctx.lineTo(T, T * 0.38); }
        else { ctx.moveTo(T / 2, 0); ctx.lineTo(T / 2, T * 0.6); ctx.lineTo(T * 0.62, T * 0.7); ctx.lineTo(T * 0.62, T); }
      });
    }
  }
  /** 焦土裂地（灰燼）：p = {base, lava} */
  function scorchTile(ctx, gx, gy, p) {
    const r = R(gx, gy, 3);
    ctx.fillStyle = shade(p.base, 0.9 + r() * 0.2); ctx.fillRect(0, 0, T, T);
    for (let i = 0; i < 5; i++) dot(ctx, r() * T, r() * T, 3 + r() * 5, "rgba(0,0,0,0.18)");
    for (let i = 0; i < 6; i++) dot(ctx, r() * T, r() * T, 1, "rgba(200,180,160,0.25)");
    if (r() < 0.45) {
      let px = r() * T, py = 0;
      const pts = [[px, py]];
      for (let s = 0; s < 5; s++) { px += (r() - 0.5) * 16; py += T / 5; pts.push([px, py]); }
      ctx.strokeStyle = "#140c08"; ctx.lineWidth = 3; ctx.beginPath(); pts.forEach(([a, b], i) => (i ? ctx.lineTo(a, b) : ctx.moveTo(a, b))); ctx.stroke();
      glowLine(ctx, p.lava, 1.4, 5, () => pts.forEach(([a, b], i) => (i ? ctx.lineTo(a, b) : ctx.moveTo(a, b))));
    }
    ctx.strokeStyle = "rgba(0,0,0,0.25)"; ctx.lineWidth = 1; ctx.strokeRect(0.5, 0.5, T - 1, T - 1);
  }
  /** 散點地（泥土、灰燼、煤渣、沙、濕沙）：p = {base, fleck, fleck2?, n} */
  function speckTile(ctx, gx, gy, p) {
    const r = R(gx, gy, 4);
    ctx.fillStyle = shade(p.base, 0.94 + r() * 0.12); ctx.fillRect(0, 0, T, T);
    for (let i = 0; i < 3; i++) { ctx.fillStyle = r() < 0.5 ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.07)"; ctx.beginPath(); ctx.ellipse(r() * T, r() * T, 8 + r() * 10, 5 + r() * 7, r() * TAU, 0, TAU); ctx.fill(); }
    for (let i = 0; i < p.n; i++) { ctx.fillStyle = p.fleck2 && r() < 0.4 ? p.fleck2 : p.fleck; ctx.fillRect(r() * T, r() * T, 1.8, 1.8); }
    if (p.ripple) { ctx.strokeStyle = p.ripple; ctx.lineWidth = 1; for (let i = 0; i < 2; i++) { const y = 14 + i * 20 + r() * 4; ctx.beginPath(); ctx.moveTo(6, y); ctx.quadraticCurveTo(T / 2, y - 4, T - 6, y); ctx.stroke(); } }
  }
  /** 草地類：p = {base, blade, blade2, tuft?} */
  function grassTile(ctx, gx, gy, p) {
    const r = R(gx, gy, 5);
    ctx.fillStyle = shade(p.base, 0.95 + r() * 0.1); ctx.fillRect(0, 0, T, T);
    if (p.grate) { // 樞市：鐵格柵，下面是苔草
      ctx.strokeStyle = p.grate; ctx.lineWidth = 2;
      for (let k = 6; k < T; k += 10) { ctx.beginPath(); ctx.moveTo(k, 0); ctx.lineTo(k, T); ctx.stroke(); }
      ctx.strokeRect(1, 1, T - 2, T - 2);
    }
    ctx.lineWidth = 1.5; ctx.lineCap = "round";
    const n = 6 + Math.floor(r() * 4);
    for (let i = 0; i < n; i++) {
      const x = 5 + r() * (T - 10), y = 8 + r() * (T - 13);
      ctx.strokeStyle = r() < 0.55 ? p.blade : p.blade2;
      ctx.beginPath();
      if (p.wavy) { ctx.moveTo(x, y); ctx.bezierCurveTo(x - 3, y - 3, x + 3, y - 6, x, y - 9); }
      else { ctx.moveTo(x, y); ctx.quadraticCurveTo(x - 1, y - 5, x - 4, y - 8); ctx.moveTo(x, y); ctx.quadraticCurveTo(x + 1, y - 5, x + 4, y - 9); }
      ctx.stroke();
    }
  }
  /** 牆（立面＋頂面，看起來比單位高）：p = {top, face, line, kind} */
  function wallTile(ctx, gx, gy, p) {
    const r = R(gx, gy, 6);
    ctx.fillStyle = p.face; ctx.fillRect(0, 0, T, T);
    ctx.fillStyle = p.top; ctx.fillRect(0, 0, T, T * 0.42);
    ctx.fillStyle = "rgba(255,255,255,0.16)"; ctx.fillRect(0, 0, T, 3);
    ctx.fillStyle = "rgba(0,0,0,0.3)"; ctx.fillRect(0, T * 0.42, T, 3);
    ctx.strokeStyle = p.line; ctx.lineWidth = 1.5;
    if (p.kind === "bricks") {
      for (let row = 0; row < 3; row++) { const y = T * 0.42 + 4 + row * 10; ctx.beginPath(); ctx.moveTo(0, y + 10); ctx.lineTo(T, y + 10); ctx.stroke(); for (let k = (row % 2) * 13; k < T; k += 26) { ctx.beginPath(); ctx.moveTo(k, y); ctx.lineTo(k, y + 10); ctx.stroke(); } }
    } else if (p.kind === "iron") {
      for (const k of [T * 0.33, T * 0.66]) { ctx.beginPath(); ctx.moveTo(k, T * 0.42); ctx.lineTo(k, T); ctx.stroke(); }
      for (const k of [8, T / 2, T - 8]) dot(ctx, k, T * 0.42 + 7, 1.8, p.rivet);
      ctx.fillStyle = p.pipe; ctx.fillRect(0, T * 0.78, T, 5); ctx.fillStyle = "rgba(255,255,255,0.3)"; ctx.fillRect(0, T * 0.78, T, 1.5);
    } else if (p.kind === "rock") {
      for (let i = 0; i < 4; i++) { const x = r() * T; ctx.beginPath(); ctx.moveTo(x, T * 0.45); ctx.lineTo(x + (r() - 0.5) * 10, T * 0.7); ctx.lineTo(x + (r() - 0.5) * 12, T); ctx.stroke(); }
      if (p.ember) for (let i = 0; i < 3; i++) dot(ctx, r() * T, T * 0.5 + r() * T * 0.45, 1.3, p.ember);
    } else if (p.kind === "ice") {
      ctx.strokeStyle = "rgba(255,255,255,0.55)";
      for (let i = 0; i < 3; i++) { const x = 6 + r() * (T - 12); ctx.beginPath(); ctx.moveTo(x, T * 0.45); ctx.lineTo(x - 4, T); ctx.stroke(); }
      ctx.fillStyle = "rgba(255,255,255,0.5)"; for (let k = 4; k < T; k += 9) { ctx.beginPath(); ctx.moveTo(k, T * 0.42); ctx.lineTo(k + 4, T * 0.42); ctx.lineTo(k + 2, T * 0.42 + 6 + r() * 4); ctx.fill(); }
    }
    if (p.trim) { ctx.fillStyle = p.trim; ctx.fillRect(0, T * 0.42 - 3, T, 2); }
  }
  /** 深淵（致命）：p = {rim, depth, glow?, kind} */
  function chasmTile(ctx, gx, gy, p) {
    const r = R(gx, gy, 7);
    const g = ctx.createLinearGradient(0, 0, 0, T);
    g.addColorStop(0, p.depth[0]); g.addColorStop(1, p.depth[1]);
    ctx.fillStyle = g; ctx.fillRect(0, 0, T, T);
    if (p.kind === "shaft") { // 樞市：機械豎井（管線＋晶光）
      ctx.strokeStyle = "rgba(176,138,74,0.55)"; ctx.lineWidth = 3;
      for (const k of [12, 40]) { ctx.beginPath(); ctx.moveTo(k, 8); ctx.lineTo(k, T); ctx.stroke(); }
      for (let i = 0; i < 3; i++) dot(ctx, 8 + r() * (T - 16), 20 + r() * 28, 1.6, p.glow);
    } else if (p.kind === "rift") { // 灰燼：黑色裂谷，底部紅光
      const gg = ctx.createRadialGradient(T / 2, T, 2, T / 2, T, T * 0.45);
      gg.addColorStop(0, rgba(p.glow, 0.28)); gg.addColorStop(1, rgba(p.glow, 0));
      ctx.fillStyle = gg; ctx.fillRect(0, 0, T, T);
    } else if (p.kind === "trench") { // 霜潮：深海溝
      ctx.strokeStyle = "rgba(160,210,255,0.18)"; ctx.lineWidth = 1.2;
      for (let i = 0; i < 2; i++) { const y = 22 + i * 16 + r() * 4; ctx.beginPath(); ctx.moveTo(8, y); ctx.quadraticCurveTo(T / 2, y - 4, T - 8, y); ctx.stroke(); }
    } else if (p.kind === "void") { // 晶冠：預設深淵＋紫晶碎光
      for (let i = 0; i < 4; i++) dot(ctx, r() * T, 14 + r() * (T - 14), 1.2, p.glow);
    }
    ctx.fillStyle = p.rim; ctx.fillRect(0, 0, T, 9); // 崖線（北緣，致命地形的辨識）
    ctx.fillStyle = "rgba(0,0,0,0.5)"; ctx.fillRect(0, 9, T, 2);
  }
  /** 岩漿類（致命，保留紅橘）：p = {hot, deep, rim?, crust?, steam?} */
  function lavaTile(ctx, gx, gy, p) {
    const r = R(gx, gy, 8);
    ctx.fillStyle = p.deep; ctx.fillRect(0, 0, T, T);
    for (let i = 0; i < 4; i++) { const gg = ctx.createRadialGradient(r() * T, r() * T, 1, r() * T, r() * T, 18); gg.addColorStop(0, p.hot); gg.addColorStop(1, rgba(p.hot, 0)); ctx.fillStyle = gg; ctx.fillRect(0, 0, T, T); }
    if (p.crust) for (let i = 0; i < 3; i++) { const cx = r() * T, cy = r() * T; ctx.fillStyle = p.crust; ctx.beginPath(); ctx.moveTo(cx - 7, cy); ctx.lineTo(cx - 2, cy - 5); ctx.lineTo(cx + 7, cy - 3); ctx.lineTo(cx + 5, cy + 4); ctx.lineTo(cx - 4, cy + 5); ctx.closePath(); ctx.fill(); }
    if (p.rim) { ctx.strokeStyle = p.rim; ctx.lineWidth = 4; ctx.strokeRect(2, 2, T - 4, T - 4); for (const [dx, dy] of [[5, 5], [T - 5, 5], [5, T - 5], [T - 5, T - 5]]) dot(ctx, dx, dy, 1.6, "#d8b070"); }
    if (p.steam) for (let i = 0; i < 2; i++) { const gg = ctx.createRadialGradient(10 + r() * 32, 10 + r() * 20, 1, 20, 20, 14); gg.addColorStop(0, "rgba(240,240,235,0.45)"); gg.addColorStop(1, "rgba(240,240,235,0)"); ctx.fillStyle = gg; ctx.fillRect(0, 0, T, T); }
  }
  /** 冰窟類（致命，深色水）：p = {water, edge, film?, rim?} */
  function holeTile(ctx, gx, gy, p) {
    const r = R(gx, gy, 9);
    ctx.fillStyle = p.edge; ctx.fillRect(0, 0, T, T);
    rr(ctx, 4, 4, T - 8, T - 8, 10); ctx.fillStyle = p.water; ctx.fill();
    if (p.rim) { ctx.lineWidth = 3; ctx.strokeStyle = p.rim; ctx.stroke(); }
    if (p.film) { ctx.fillStyle = p.film; for (let i = 0; i < 4; i++) { ctx.beginPath(); ctx.ellipse(10 + r() * 32, 10 + r() * 32, 5 + r() * 4, 2 + r() * 2, r(), 0, TAU); ctx.fill(); } }
    ctx.strokeStyle = "rgba(255,255,255,0.3)"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(12, 18); ctx.quadraticCurveTo(20, 14, 28, 18); ctx.stroke();
  }

  // ======================= 物件（參數化）=======================
  function crate(ctx, p) {
    shadow(ctx, T / 2 + 3, T / 2 + 7, T * 0.34, T * 0.28);
    const s = T * 0.62, o = (T - s) / 2;
    box(ctx, o, o, s, s, p.wood, OUT, 2, 3);
    ctx.strokeStyle = p.grain; ctx.lineWidth = 1.2;
    for (let k = 1; k < 4; k++) { ctx.beginPath(); ctx.moveTo(o + 2, o + (s * k) / 4); ctx.lineTo(o + s - 2, o + (s * k) / 4); ctx.stroke(); }
    if (p.corner) for (const [cx, cy] of [[o, o], [o + s - 7, o], [o, o + s - 7], [o + s - 7, o + s - 7]]) box(ctx, cx, cy, 7, 7, p.corner, OUT, 1.2, 1);
    if (p.cross) { ctx.strokeStyle = p.cross; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(o + 3, o + 3); ctx.lineTo(o + s - 3, o + s - 3); ctx.stroke(); }
    if (p.broken) { ctx.fillStyle = "#1a120c"; ctx.beginPath(); ctx.moveTo(o + s * 0.55, o); ctx.lineTo(o + s * 0.8, o + s * 0.3); ctx.lineTo(o + s, o + s * 0.2); ctx.lineTo(o + s, o); ctx.closePath(); ctx.fill(); }
    if (p.fish) { ctx.strokeStyle = "#e8e0d0"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.ellipse(T / 2 - 2, T / 2, 7, 3.5, 0, 0, TAU); ctx.moveTo(T / 2 + 5, T / 2); ctx.lineTo(T / 2 + 10, T / 2 - 4); ctx.lineTo(T / 2 + 10, T / 2 + 4); ctx.closePath(); ctx.stroke(); }
    if (p.rune) dot(ctx, T / 2, T / 2, 3, p.rune);
  }
  function barrel(ctx, p) {
    shadow(ctx, T / 2 + 3, T / 2 + 8, T * 0.3, T * 0.24);
    const cx = T / 2, top = 10, bot = 42, w = 16;
    ctx.beginPath(); ctx.moveTo(cx - w, top + 4); ctx.lineTo(cx - w, bot); ctx.ellipse(cx, bot, w, 5, 0, Math.PI, 0, true); ctx.lineTo(cx + w, top + 4); ctx.closePath();
    ctx.fillStyle = p.body; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.fillStyle = "rgba(0,0,0,0.22)"; ctx.fillRect(cx + w * 0.4, top + 4, w * 0.55, bot - top - 2);
    ctx.strokeStyle = p.band; ctx.lineWidth = 2.5;
    for (const y of [top + 11, bot - 7]) { ctx.beginPath(); ctx.moveTo(cx - w, y); ctx.quadraticCurveTo(cx, y + 4, cx + w, y); ctx.stroke(); }
    ctx.beginPath(); ctx.ellipse(cx, top + 4, w, 5, 0, 0, TAU); ctx.fillStyle = p.lid; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    if (p.rust) { ctx.fillStyle = p.rust; for (const [dx, dy, rad] of [[-8, 22, 4], [6, 32, 3], [-3, 38, 2.5]]) dot(ctx, cx + dx, dy, rad, p.rust); }
    if (p.glow) { ctx.save(); ctx.shadowColor = p.glow; ctx.shadowBlur = 8; ctx.fillStyle = p.glow; ctx.fillRect(cx - 3, top + 14, 6, 14); ctx.restore(); }
    hazard(ctx, cx - 3, top + 24, 6.5);
  }
  function pillar(ctx, p) {
    const c = T / 2;
    ctx.fillStyle = "rgba(0,0,0,0.3)"; ctx.beginPath(); ctx.moveTo(c - 6, 46); ctx.lineTo(c + 6, 46); ctx.lineTo(c + 22, 52); ctx.lineTo(c + 8, 52); ctx.fill();
    box(ctx, c - 11, 40, 22, 8, p.base, OUT, 2, 2);
    if (p.kind === "crystal") { // 晶冠：晶柱
      ctx.save(); ctx.shadowColor = p.glow; ctx.shadowBlur = 10;
      ctx.beginPath(); ctx.moveTo(c - 8, 41); ctx.lineTo(c - 9, 14); ctx.lineTo(c, 2); ctx.lineTo(c + 9, 14); ctx.lineTo(c + 8, 41); ctx.closePath();
      ctx.fillStyle = p.body; ctx.fill(); ctx.restore(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
      ctx.fillStyle = "rgba(255,255,255,0.35)"; ctx.beginPath(); ctx.moveTo(c - 5, 38); ctx.lineTo(c - 6, 15); ctx.lineTo(c, 6); ctx.lineTo(c - 1, 38); ctx.fill();
      ctx.fillStyle = rgba("#000000", 0.18); ctx.beginPath(); ctx.moveTo(c + 2, 38); ctx.lineTo(c + 1, 6); ctx.lineTo(c + 8, 15); ctx.lineTo(c + 7, 38); ctx.fill();
      box(ctx, c - 11, 38, 22, 4, p.trim, OUT, 1.5, 1);
      return;
    }
    if (p.kind === "broken") { // 灰燼：斷柱（頂端斷口參差）
      ctx.beginPath(); ctx.moveTo(c - 7, 41); ctx.lineTo(c - 7, 10); ctx.lineTo(c - 3, 6); ctx.lineTo(c, 11); ctx.lineTo(c + 3, 4); ctx.lineTo(c + 7, 9); ctx.lineTo(c + 7, 41); ctx.closePath();
      ctx.fillStyle = p.body; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
      ctx.fillStyle = "rgba(0,0,0,0.28)"; ctx.fillRect(c + 2, 10, 4, 30);
      ctx.strokeStyle = "rgba(0,0,0,0.45)"; ctx.lineWidth = 1; for (const y of [18, 28]) { ctx.beginPath(); ctx.moveTo(c - 6, y); ctx.lineTo(c + 6, y + 2); ctx.stroke(); }
      ctx.fillStyle = "#1a120c"; for (const [dx, dy] of [[-4, 24], [2, 34]]) dot(ctx, c + dx, dy, 1.6, "#1a120c");
      return;
    }
    if (p.kind === "coral") { // 霜潮：珊瑚礁柱（不規則的岩柱＋珊瑚枝）
      ctx.beginPath(); ctx.moveTo(c - 9, 41); ctx.quadraticCurveTo(c - 11, 24, c - 6, 8); ctx.quadraticCurveTo(c, 3, c + 6, 8); ctx.quadraticCurveTo(c + 11, 24, c + 9, 41); ctx.closePath();
      ctx.fillStyle = p.body; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
      ctx.fillStyle = "rgba(0,0,0,0.22)"; ctx.fillRect(c + 3, 12, 5, 28);
      ctx.strokeStyle = p.coral; ctx.lineWidth = 2.5; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(c - 4, 20); ctx.lineTo(c - 10, 14); ctx.moveTo(c - 7, 17); ctx.lineTo(c - 7, 11); ctx.moveTo(c + 3, 30); ctx.lineTo(c + 10, 25); ctx.stroke();
      ctx.fillStyle = "rgba(255,255,255,0.4)"; for (const [dx, dy] of [[-3, 34], [1, 14], [4, 22]]) dot(ctx, c + dx, dy, 1.2, "rgba(255,255,255,0.4)");
      return;
    }
    // 樞市：黃銅管柱（豎管＋環箍＋壓力表）
    box(ctx, c - 7, 6, 14, 35, p.body, OUT, 2, 3);
    ctx.fillStyle = "rgba(255,255,255,0.3)"; ctx.fillRect(c - 5, 8, 2, 31);
    ctx.fillStyle = "rgba(0,0,0,0.25)"; ctx.fillRect(c + 2, 8, 4, 31);
    for (const y of [10, 24, 36]) box(ctx, c - 9, y, 18, 4, p.trim, OUT, 1.2, 1);
    ctx.beginPath(); ctx.arc(c, 17, 4.5, 0, TAU); ctx.fillStyle = "#f2ead8"; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.beginPath(); ctx.moveTo(c, 17); ctx.lineTo(c + 2.5, 14.5); ctx.strokeStyle = "#c03020"; ctx.lineWidth = 1.2; ctx.stroke();
    glowLine(ctx, p.glow, 1.5, 5, () => { ctx.moveTo(c, 29); ctx.lineTo(c, 34); });
  }
  function lowWallObj(ctx, p) { // 同 lowWallArt：頂面亮、正面錯縫、2px 外框
    shadow(ctx, T / 2 + 2, T * 0.72, T * 0.46, T * 0.12, 0.35);
    const x0 = 4, x1 = T - 4, capY = T * 0.3, baseY = T * 0.74;
    box(ctx, x0, capY + 6, x1 - x0, baseY - capY - 6, p.face, p.outline, 2, 2);
    ctx.strokeStyle = p.mortar; ctx.lineWidth = 1.2;
    for (let row = 0; row < 2; row++) { const y = capY + 6 + row * 8; ctx.beginPath(); ctx.moveTo(x0 + 1, y + 8); ctx.lineTo(x1 - 1, y + 8); ctx.stroke(); for (let k = x0 + 8 + row * 7; k < x1; k += 14) { ctx.beginPath(); ctx.moveTo(k, y); ctx.lineTo(k, y + 8); ctx.stroke(); } }
    box(ctx, x0 - 1, capY, x1 - x0 + 2, 8, p.top, p.outline, 2, 2);
    ctx.fillStyle = p.topEdge; ctx.fillRect(x0 + 1, capY + 1, x1 - x0 - 2, 2);
    if (p.extra) p.extra(ctx, x0, x1, capY, baseY);
  }
  function log(ctx, p) {
    shadow(ctx, T / 2 + 2, T / 2 + 9, T * 0.42, T * 0.14);
    const y = T / 2 - 4;
    box(ctx, 6, y, T - 12, 13, p.bark, OUT, 2, 6);
    ctx.strokeStyle = p.grain; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(10, y + 5); ctx.lineTo(T - 16, y + 4); ctx.moveTo(14, y + 9); ctx.lineTo(T - 12, y + 9); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(T - 8, y + 6.5, 4, 6.5, 0, 0, TAU); ctx.fillStyle = p.end; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke();
    if (p.char) { ctx.fillStyle = p.char; ctx.fillRect(16, y + 1, 10, 11); ctx.fillRect(30, y + 1, 5, 11); for (const x of [20, 32]) dot(ctx, x, y + 6, 1.2, "#ff7a2a"); }
    if (p.rivet) for (const x of [14, 26, 38]) dot(ctx, x, y + 6.5, 1.8, p.rivet);
    if (p.pale) { ctx.fillStyle = "rgba(255,255,255,0.25)"; ctx.fillRect(8, y + 2, T - 20, 2); }
  }
  function tree(ctx, p) {
    const c = T / 2;
    shadow(ctx, c + 3, 46, 12, 4, 0.35);
    if (p.kind === "crane") { // 樞市：木製吊臂
      box(ctx, c - 3, 8, 6, 38, p.trunk, OUT, 2, 1);
      box(ctx, c - 2, 6, 24, 5, p.trunk, OUT, 2, 1);
      ctx.strokeStyle = "#2a241e"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(c + 18, 11); ctx.lineTo(c + 18, 26); ctx.stroke();
      box(ctx, c + 15, 26, 6, 5, p.metal, OUT, 1.2, 1);
      ctx.strokeStyle = p.metal; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(c, 18); ctx.lineTo(c + 10, 9); ctx.stroke();
      for (const y of [16, 30]) box(ctx, c - 5, y, 10, 3, p.metal, OUT, 1, 1);
      return;
    }
    if (p.kind === "mast") { // 霜潮：斷桅（桅杆＋橫桁＋破帆）
      box(ctx, c - 3, 6, 6, 40, p.trunk, OUT, 2, 1);
      ctx.beginPath(); ctx.moveTo(c - 2, 4); ctx.lineTo(c + 1, 8); ctx.lineTo(c + 3, 3); ctx.stroke();
      box(ctx, c - 16, 13, 32, 4, p.trunk, OUT, 1.6, 1);
      ctx.beginPath(); ctx.moveTo(c - 14, 17); ctx.lineTo(c + 12, 17); ctx.lineTo(c + 8, 30); ctx.lineTo(c + 2, 26); ctx.lineTo(c - 4, 33); ctx.lineTo(c - 12, 28); ctx.closePath();
      ctx.fillStyle = p.sail; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke();
      ctx.strokeStyle = "rgba(60,50,40,0.6)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(c - 16, 15); ctx.lineTo(c - 6, 44); ctx.stroke();
      return;
    }
    // 枯樹（灰燼本區主場、晶冠預設）：焦黑分枝
    ctx.strokeStyle = OUT; ctx.lineCap = "round";
    const br = [[[c, 46], [c, 22], 7], [[c, 30], [c - 12, 16], 4], [[c, 26], [c + 12, 12], 4], [[c + 12, 12], [c + 18, 8], 2.5], [[c - 12, 16], [c - 16, 8], 2.5], [[c + 4, 22], [c + 2, 6], 3]];
    for (const [a, b, w] of br) { ctx.lineWidth = w + 3; ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke(); }
    ctx.strokeStyle = p.trunk; for (const [a, b, w] of br) { ctx.lineWidth = w; ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke(); }
    if (p.ember) for (const [x, y] of [[c - 1, 34], [c + 9, 15], [c - 10, 19]]) dot(ctx, x, y, 1.4, p.ember);
    if (p.crystal) { ctx.save(); ctx.shadowColor = p.crystal; ctx.shadowBlur = 6; for (const [x, y] of [[c + 18, 8], [c - 16, 8]]) dot(ctx, x, y, 2.4, p.crystal); ctx.restore(); }
  }
  function tuft(ctx, p) { // 草叢（隱蔽、可燃）
    shadow(ctx, T / 2 + 2, T * 0.7, T * 0.36, T * 0.12, 0.25);
    ctx.lineCap = "round";
    const r = rng(17);
    for (let i = 0; i < 16; i++) {
      const x = 10 + r() * (T - 20), y = T * 0.72, h = 14 + r() * 16;
      ctx.strokeStyle = i % 3 === 0 ? p.dark : p.blade; ctx.lineWidth = 2.6;
      ctx.beginPath(); ctx.moveTo(x, y);
      if (p.wavy) ctx.bezierCurveTo(x - 5, y - h * 0.3, x + 5, y - h * 0.6, x + (r() - 0.5) * 6, y - h);
      else ctx.quadraticCurveTo(x + (r() - 0.5) * 4, y - h * 0.6, x + (r() - 0.5) * 12, y - h);
      ctx.stroke();
    }
    if (p.steam) for (let i = 0; i < 3; i++) { const gg = ctx.createRadialGradient(14 + i * 12, 18, 1, 14 + i * 12, 18, 10); gg.addColorStop(0, "rgba(235,240,240,0.55)"); gg.addColorStop(1, "rgba(235,240,240,0)"); ctx.fillStyle = gg; ctx.fillRect(0, 0, T, T); }
    if (p.pipe) { box(ctx, 2, T * 0.62, T - 4, 6, p.pipe, OUT, 1.5, 2); }
  }
  function bridge(ctx, p) {
    const x0 = 6, x1 = T - 6;
    ctx.fillStyle = "rgba(0,0,0,0.35)"; ctx.fillRect(x0 + 3, 4, x1 - x0, T - 4);
    if (p.beam) { ctx.fillStyle = p.beam; ctx.fillRect(x0 - 2, 0, 5, T); ctx.fillRect(x1 - 3, 0, 5, T); for (let y = 4; y < T; y += 12) { dot(ctx, x0 + 0.5, y, 1.4, "#d8b070"); dot(ctx, x1 - 0.5, y, 1.4, "#d8b070"); } }
    for (let y = 1; y < T; y += 8) {
      box(ctx, x0 + 2, y, x1 - x0 - 4, 6.5, shade(p.plank, 0.9 + ((y * 7) % 10) / 50), OUT, 1.4, 1);
      if (p.char) { ctx.fillStyle = p.char; ctx.fillRect(x0 + 2, y, 5, 6.5); ctx.fillRect(x1 - 9, y, 7, 6.5); }
    }
    if (p.post) for (const y of [0, T - 8]) { box(ctx, x0 - 3, y, 6, 8, p.post, OUT, 1.4, 1); box(ctx, x1 - 3, y, 6, 8, p.post, OUT, 1.4, 1); }
    if (p.rope) { ctx.strokeStyle = p.rope; ctx.lineWidth = 1.6; for (const x of [x0 - 1, x1 + 1]) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, T); ctx.stroke(); } }
  }
  function iceSheet(ctx, p) { // 薄冰類（可破，架在冰窟上）
    ctx.globalAlpha = 0.92;
    rr(ctx, 5, 5, T - 10, T - 10, 6); ctx.fillStyle = p.fill; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = p.edge; ctx.stroke();
    ctx.globalAlpha = 1;
    if (p.grate) { ctx.strokeStyle = p.edge; ctx.lineWidth = 2; for (let k = 12; k < T - 6; k += 8) { ctx.beginPath(); ctx.moveTo(k, 7); ctx.lineTo(k, T - 7); ctx.stroke(); } }
    else if (p.planks) { ctx.strokeStyle = "rgba(0,0,0,0.35)"; ctx.lineWidth = 1.2; for (let y = 14; y < T - 8; y += 9) { ctx.beginPath(); ctx.moveTo(7, y); ctx.lineTo(T - 7, y); ctx.stroke(); } }
    else { ctx.strokeStyle = "rgba(90,138,168,0.7)"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(12, 14); ctx.lineTo(26, 26); ctx.lineTo(40, 20); ctx.moveTo(26, 26); ctx.lineTo(22, 40); ctx.stroke(); ctx.fillStyle = "rgba(255,255,255,0.5)"; ctx.fillRect(10, 10, 14, 3); }
  }

  // ======================= 五區對照（除了雲嶺）=======================
  const REGIONS = [
    {
      id: "ashen_waste", name: "灰燼荒原", order: 1,
      line: "焦土、炭黑、熔岩橘。最暗的一區，只有熔岩光是亮的；裂縫的光要細，不要搶走岩漿（致命）的紅。",
      swatch: [["#4a3a30", "焦土"], ["#2a1e18", "炭黑"], ["#ff6a1a", "熔岩"], ["#6a5e54", "殘牆"], ["#8a7a48", "枯草"], ["#5a5450", "灰燼"]],
      terrain: {
        stone: ["焦土裂地", (c, x, y) => scorchTile(c, x, y, { base: "#4a3a30", lava: "#ff6a1a" })],
        grass: ["枯黃草", (c, x, y) => grassTile(c, x, y, { base: "#6e6040", blade: "#b8a060", blade2: "#5a4a2a" })],
        dirt: ["灰燼", (c, x, y) => speckTile(c, x, y, { base: "#5a5450", fleck: "rgba(30,24,20,0.55)", fleck2: "rgba(210,200,190,0.35)", n: 14 })],
        wall: ["焦黑岩壁", (c, x, y) => wallTile(c, x, y, { top: "#4a3e38", face: "#2a221e", line: "rgba(0,0,0,0.6)", kind: "rock", ember: "#ff7a2a" })],
        chasm: ["黑色裂谷", (c, x, y) => chasmTile(c, x, y, { rim: "#3a302a", depth: ["#0c0806", "#1a0a06"], glow: "#ff4a10", kind: "rift" })],
        lava: ["岩漿（主場）", (c, x, y) => lavaTile(c, x, y, { hot: "#ffb030", deep: "#e0400a", crust: "rgba(40,20,12,0.75)" })],
        ice_hole: ["灰水坑", (c, x, y) => holeTile(c, x, y, { water: "#2c3034", edge: "#4a3a30", film: "rgba(150,140,130,0.35)" })],
      },
      objects: {
        crate: ["破木箱", (c) => crate(c, { wood: "#7a5a38", grain: "rgba(40,24,12,0.6)", broken: true, corner: "#5a5450" })],
        low_wall: ["殘牆", (c) => lowWallObj(c, { top: "#7a6e64", topEdge: "#9a8e84", face: "#5a4e44", mortar: "#2e2620", outline: "#1a1410", extra: (cx, x0, x1, capY) => { cx.fillStyle = "#1a1410"; cx.beginPath(); cx.moveTo(x1 - 14, capY - 1); cx.lineTo(x1 - 8, capY + 6); cx.lineTo(x1 + 1, capY + 2); cx.lineTo(x1 + 1, capY - 1); cx.fill(); } })],
        stone_pillar: ["斷柱", (c) => pillar(c, { kind: "broken", base: "#5a4e44", body: "#7a6e64" })],
        oil_barrel: ["鐵油桶（鏽）", (c) => barrel(c, { body: "#5a5e60", band: "#3a3c3e", lid: "#6a6e70", rust: "#9a4a20" })],
        fallen_log: ["焦黑倒木", (c) => log(c, { bark: "#4a3628", grain: "rgba(0,0,0,0.5)", end: "#8a6a48", char: "#1a120c" })],
        grass: ["枯草堆", (c) => tuft(c, { blade: "#c8b070", dark: "#7a6438" })],
        wooden_bridge: ["焦木渡橋", (c) => bridge(c, { plank: "#7a5a38", char: "#1e140c", post: "#3a2a1e" })],
        dead_tree: ["枯樹（主場）", (c) => tree(c, { trunk: "#3a2a20", ember: "#ff7a2a" })],
        thin_ice: ["灰水上的浮板", (c) => iceSheet(c, { fill: "#8a6a48", edge: "#3a2a1e", planks: true })],
      },
      scene: { // 岩漿渡橋（lava_crossing）的一角
        rows: ["ssss vv ssss", "ssss vv sgss", "sdss ==  sss", "ssss == ssWW", "ssgs vv ssWW"],
        objs: [[1, 0, "dead_tree"], [3, 1, "crate"], [9, 1, "oil_barrel"], [2, 4, "low_wall"], [3, 4, "low_wall"], [8, 2, "stone_pillar"], [0, 3, "grass"]],
      },
    },
    {
      id: "crystal_crown", name: "晶冠城邦", order: 2,
      line: "米白石材＋藍紫晶光、金飾。就是現在的預設畫法，只多三樣點綴（晶柱、金嵌線、城牆金邊），讓「預設」也像一個地方。",
      swatch: [["#d8ccb0", "石板"], ["#a89a7c", "接縫"], ["#8f7bff", "晶光"], ["#3a5ad0", "旗藍"], ["#e8bb48", "金飾"]],
      terrain: {
        stone: ["米白石板（偶有金嵌線）", (c, x, y) => slabTile(c, x, y, { base: "#d8ccb0", gap: "#a89a7c", inlay: "#e8bb48", glint: "#8f7bff" })],
        grass: ["草地（預設）", (c, x, y) => grassTile(c, x, y, { base: "#6a9a4a", blade: "#9ccf6a", blade2: "#4a7a32" })],
        dirt: ["泥土（預設）", (c, x, y) => speckTile(c, x, y, { base: "#8a6a48", fleck: "rgba(50,34,20,0.5)", n: 10 })],
        wall: ["白石城牆＋金邊", (c, x, y) => wallTile(c, x, y, { top: "#e8dcc0", face: "#b8aa8a", line: "rgba(90,74,50,0.6)", kind: "bricks", trim: "#e8bb48" })],
        chasm: ["深淵＋晶光碎點", (c, x, y) => chasmTile(c, x, y, { rim: "#b8aa8a", depth: ["#1a1830", "#0a0a14"], glow: "#8f7bff", kind: "void" })],
        lava: ["岩漿（預設）", (c, x, y) => lavaTile(c, x, y, { hot: "#ffb030", deep: "#e0400a" })],
        ice_hole: ["冰窟（預設）", (c, x, y) => holeTile(c, x, y, { water: "#1e3a5a", edge: "#cdeeff" })],
      },
      objects: {
        crate: ["木箱（預設）", (c) => crate(c, { wood: "#a07848", grain: "rgba(60,36,16,0.55)", cross: "rgba(60,36,16,0.6)" })],
        low_wall: ["石磚矮牆（預設）", (c) => lowWallObj(c, { top: "#d8c7a2", topEdge: "#f2e6c8", face: "#86704f", mortar: "#4c3d2a", outline: "#241c13" })],
        stone_pillar: ["晶柱", (c) => pillar(c, { kind: "crystal", base: "#d8ccb0", body: "#a898ff", glow: "#8f7bff", trim: "#e8bb48" })],
        oil_barrel: ["木油桶（預設）", (c) => barrel(c, { body: "#8a5a30", band: "#3a3a3a", lid: "#a07040" })],
        fallen_log: ["倒木（預設）", (c) => log(c, { bark: "#6a4a2a", grain: "rgba(0,0,0,0.4)", end: "#c8a070" })],
        grass: ["長草（預設）", (c) => tuft(c, { blade: "#8ac860", dark: "#4a7a32" })],
        wooden_bridge: ["木橋（預設）", (c) => bridge(c, { plank: "#a07848" })],
        dead_tree: ["枯樹（預設）", (c) => tree(c, { trunk: "#6a5040" })],
        thin_ice: ["薄冰（預設）", (c) => iceSheet(c, { fill: "#cdeeff", edge: "#5a8aa8" })],
      },
      scene: {
        rows: ["WWWWWWWWWWWW", "ssssssssssss", "ssssssssgggs", "sssss sssggs", "ssddssssssss"],
        objs: [[2, 1, "stone_pillar"], [9, 1, "stone_pillar"], [4, 3, "crate"], [6, 4, "low_wall"], [7, 4, "low_wall"], [10, 2, "grass"]],
        circle: [5, 2],
      },
    },
    {
      id: "arcane_hub", name: "魔導樞市", order: 3,
      line: "鐵板、黃銅、晶能青、符文橘。晶能線只是裝飾，亮度要比導電、雷電特效低；地板不要每格都發光。",
      swatch: [["#4a4238", "鐵板"], ["#2a241e", "煤黑"], ["#b08a4a", "黃銅"], ["#4ae0d0", "晶能"], ["#e8a040", "符文"]],
      terrain: {
        stone: ["鉚釘鐵板＋晶能線", (c, x, y) => plateTile(c, x, y, { base: "#4a4238", joint: "#2a241e", rivet: "#b08a4a", line: "#4ae0d0" })],
        grass: ["鐵格柵下的苔草", (c, x, y) => grassTile(c, x, y, { base: "#3e4a34", blade: "#7aa060", blade2: "#4a6a3a", grate: "#2a241e" })],
        dirt: ["煤渣地", (c, x, y) => speckTile(c, x, y, { base: "#3a3430", fleck: "rgba(10,8,6,0.6)", fleck2: "rgba(176,138,74,0.4)", n: 16 })],
        wall: ["鐵壁（鉚釘＋管線）", (c, x, y) => wallTile(c, x, y, { top: "#5a5248", face: "#3a342c", line: "rgba(0,0,0,0.55)", kind: "iron", rivet: "#b08a4a", pipe: "#b08a4a" })],
        chasm: ["機械豎井", (c, x, y) => chasmTile(c, x, y, { rim: "#5a5248", depth: ["#14181a", "#06080a"], glow: "#4ae0d0", kind: "shaft" })],
        lava: ["熔爐槽（金屬邊框）", (c, x, y) => lavaTile(c, x, y, { hot: "#ffb030", deep: "#e0400a", rim: "#5a5248" })],
        ice_hole: ["冷卻槽（冰藍液體）", (c, x, y) => holeTile(c, x, y, { water: "#2a7a9a", edge: "#4a4238", rim: "#b08a4a" })],
      },
      objects: {
        crate: ["木殼貨箱（黃銅包角）", (c) => crate(c, { wood: "#8a6a44", grain: "rgba(40,26,12,0.55)", corner: "#c89a52", rune: "#e8a040" })],
        low_wall: ["鐵欄杆＋沙包", (c) => lowWallObj(c, { top: "#a08a60", topEdge: "#c8b080", face: "#7a6a4a", mortar: "#4a3e2a", outline: "#1e1810", extra: (cx, x0, x1, capY) => { cx.strokeStyle = "#2a241e"; cx.lineWidth = 2; cx.beginPath(); cx.moveTo(x0, capY - 6); cx.lineTo(x1, capY - 6); for (let k = x0 + 4; k < x1; k += 10) { cx.moveTo(k, capY - 6); cx.lineTo(k, capY); } cx.stroke(); } })],
        stone_pillar: ["黃銅管柱", (c) => pillar(c, { kind: "pipe", base: "#4a4238", body: "#b08a4a", trim: "#7a5e30", glow: "#4ae0d0" })],
        oil_barrel: ["晶能罐（黃銅＋發光）", (c) => barrel(c, { body: "#9a7a40", band: "#5a4424", lid: "#c89a52", glow: "#4ae0d0" })],
        fallen_log: ["倒下的木樑（鉚釘）", (c) => log(c, { bark: "#7a5a38", grain: "rgba(0,0,0,0.35)", end: "#b8905a", rivet: "#c89a52" })],
        grass: ["管線間的蒸氣苔", (c) => tuft(c, { blade: "#7aa060", dark: "#4a6a3a", steam: true, pipe: "#b08a4a" })],
        wooden_bridge: ["鋼樑橋（木板鋪面）", (c) => bridge(c, { plank: "#9a7448", beam: "#4a4238" })],
        dead_tree: ["木製吊臂", (c) => tree(c, { kind: "crane", trunk: "#8a6a44", metal: "#b08a4a" })],
        thin_ice: ["冷卻槽上的格柵板", (c) => iceSheet(c, { fill: "#4a4238", edge: "#b08a4a", grate: true })],
      },
      scene: {
        rows: ["WWWWWWWWWWWW", "ssssssssssss", "ssss  ssssss", "sssssssshhss", "ggssssssssdd"],
        objs: [[1, 1, "stone_pillar"], [6, 1, "crate"], [10, 1, "oil_barrel"], [3, 4, "low_wall"], [4, 4, "low_wall"], [0, 3, "grass"], [10, 3, "dead_tree"]],
        bridge: [[4, 2], [5, 2]],
      },
    },
    {
      id: "frost_tide", name: "霜潮海境", order: 4,
      line: "沙色、淺海藍、浮冰白、珊瑚紅。地板是亮色系，物件與牆要靠深色外框才不會糊在沙上。",
      swatch: [["#d8c89a", "沙岸"], ["#b8a478", "濕沙"], ["#3f8ac8", "淺海"], ["#cdeeff", "浮冰"], ["#6a7a80", "礁石"], ["#e8807a", "珊瑚"]],
      terrain: {
        stone: ["沙岸", (c, x, y) => speckTile(c, x, y, { base: "#d8c89a", fleck: "rgba(122,106,72,0.5)", fleck2: "rgba(255,255,255,0.5)", n: 12 })],
        grass: ["海草灘", (c, x, y) => grassTile(c, x, y, { base: "#8a9a6a", blade: "#4a8a6a", blade2: "#2e6a50", wavy: true })],
        dirt: ["濕沙", (c, x, y) => speckTile(c, x, y, { base: "#b8a478", fleck: "rgba(90,74,48,0.5)", n: 8, ripple: "rgba(255,255,255,0.3)" })],
        wall: ["冰崖", (c, x, y) => wallTile(c, x, y, { top: "#e8f6ff", face: "#8ab8d8", line: "rgba(40,80,110,0.55)", kind: "ice" })],
        chasm: ["深海溝", (c, x, y) => chasmTile(c, x, y, { rim: "#c8b88a", depth: ["#123a6a", "#061a34"], kind: "trench" })],
        lava: ["海底熱泉（少見）", (c, x, y) => lavaTile(c, x, y, { hot: "#ffb030", deep: "#d04010", steam: true })],
        ice_hole: ["冰窟（主場）", (c, x, y) => holeTile(c, x, y, { water: "#1e3a5a", edge: "#e8f6ff", rim: "#9ad0f0" })],
      },
      objects: {
        crate: ["漁貨箱", (c) => crate(c, { wood: "#9a8460", grain: "rgba(40,30,16,0.5)", fish: true })],
        low_wall: ["防波石堤", (c) => lowWallObj(c, { top: "#8a989c", topEdge: "#b8c6ca", face: "#5a6a70", mortar: "#34404a", outline: "#18222a", extra: (cx, x0, x1, capY) => { cx.fillStyle = "rgba(255,255,255,0.7)"; for (let k = x0 + 6; k < x1 - 4; k += 9) { cx.beginPath(); cx.arc(k, capY + 22, 2, 0, TAU); cx.fill(); } } })],
        stone_pillar: ["珊瑚礁柱", (c) => pillar(c, { kind: "coral", base: "#5a6a70", body: "#6a7a80", coral: "#e8807a" })],
        oil_barrel: ["鯨油桶", (c) => barrel(c, { body: "#6a5a40", band: "#2a3a4a", lid: "#8a7650" })],
        fallen_log: ["漂流木", (c) => log(c, { bark: "#a8a090", grain: "rgba(60,56,48,0.5)", end: "#d8d0c0", pale: true })],
        grass: ["海草叢", (c) => tuft(c, { blade: "#3a8a6a", dark: "#1e5a44", wavy: true })],
        wooden_bridge: ["碼頭棧道", (c) => bridge(c, { plank: "#9a8460", post: "#5a4a36", rope: "#c8b48a" })],
        dead_tree: ["斷桅", (c) => tree(c, { kind: "mast", trunk: "#7a6448", sail: "#e8e0cc" })],
        thin_ice: ["薄冰（主場）", (c) => iceSheet(c, { fill: "#d8f2ff", edge: "#5a8aa8" })],
      },
      scene: {
        rows: ["sssssssddwww", "sssgsssddwww", "ssssssddwwii", "ssssssdwwwii", "sssssddwwiio"],
        objs: [[1, 0, "dead_tree"], [3, 1, "grass"], [5, 2, "stone_pillar"], [2, 3, "crate"], [4, 4, "low_wall"], [5, 4, "low_wall"], [11, 4, "thin_ice"]],
        water: true,
      },
    },
  ];

  /** 畫一格地形（座標 x, y 為格左上；gx, gy 為格子索引）。 */
  function tile(ctx, region, id, x, y, gx, gy) {
    ctx.save(); ctx.translate(x, y); region.terrain[id][1](ctx, gx, gy); ctx.restore();
  }
  function object(ctx, region, id, x, y) {
    ctx.save(); ctx.translate(x, y); region.objects[id][1](ctx); ctx.restore();
  }
  /** 水面（表面 water，五區相同，不換皮）：淺藍＋反光線。 */
  function water(ctx, x, y, gx, gy) {
    const r = R(gx, gy, 12);
    ctx.fillStyle = "#3f8ac8"; ctx.fillRect(x, y, T, T);
    ctx.strokeStyle = "rgba(255,255,255,0.45)"; ctx.lineWidth = 1.5;
    for (let i = 0; i < 2; i++) { const wy = y + 12 + i * 22 + r() * 6; ctx.beginPath(); ctx.moveTo(x + 8, wy); ctx.quadraticCurveTo(x + 18, wy - 5, x + 28, wy); ctx.stroke(); }
  }
  function magicCircle(ctx, x, y) {
    ctx.save(); ctx.translate(x + T / 2, y + T / 2); ctx.shadowColor = "#8f7bff"; ctx.shadowBlur = 8;
    ctx.strokeStyle = "rgba(143,123,255,0.85)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(0, 0, 20, 0, TAU); ctx.stroke();
    ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(0, 0, 14, 0, TAU); ctx.stroke();
    ctx.beginPath(); for (let k = 0; k < 6; k++) { const a = (k / 6) * TAU; ctx[k ? "lineTo" : "moveTo"](Math.cos(a * 2 + 0.5) * 14, Math.sin(a * 2 + 0.5) * 14); } ctx.closePath(); ctx.stroke(); ctx.restore();
  }
  const CODE = { s: "stone", g: "grass", d: "dirt", W: "wall", v: "lava", h: "ice_hole", " ": "chasm", i: "ice_hole" };
  /** 小戰場：12×5 格。 */
  function scene(ctx, region) {
    const sc = region.scene;
    sc.rows.forEach((row, gy) => [...row].forEach((ch, gx) => {
      const x = gx * T, y = gy * T;
      if (ch === "w") return water(ctx, x, y, gx, gy);
      if (ch === "=") { tile(ctx, region, "lava", x, y, gx, gy); return; }
      if (ch === "o") { tile(ctx, region, "ice_hole", x, y, gx, gy); return; }
      tile(ctx, region, CODE[ch] ?? "stone", x, y, gx, gy);
    }));
    if (sc.circle) magicCircle(ctx, sc.circle[0] * T, sc.circle[1] * T);
    sc.rows.forEach((row, gy) => [...row].forEach((ch, gx) => { if (ch === "=") object(ctx, region, "wooden_bridge", gx * T, gy * T); }));
    for (const [gx, gy] of sc.bridge ?? []) { ctx.save(); ctx.translate(gx * T + T, gy * T); ctx.rotate(Math.PI / 2); region.objects.wooden_bridge[1](ctx); ctx.restore(); }
    for (let gy = 0; gy < sc.rows.length; gy++) for (const [ox, oy, id] of sc.objs) if (oy === gy) object(ctx, region, id, ox * T, oy * T);
  }
  const TERRAIN_IDS = ["stone", "grass", "dirt", "wall", "chasm", "lava", "ice_hole"];
  const OBJECT_IDS = ["crate", "low_wall", "stone_pillar", "oil_barrel", "fallen_log", "grass", "wooden_bridge", "dead_tree", "thin_ice"];
  return { T, REGIONS, TERRAIN_IDS, OBJECT_IDS, tile, object, scene };
})();
