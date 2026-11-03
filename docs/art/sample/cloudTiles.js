// 雲嶺實地地圖：地磚與地物圖庫（美術 PM，2026-11-04）。給 6C 的 18 張實地地圖用；畫風同 explore.png（戰鬥格子的同一套畫法）。
// 座標以 52 的虛擬格為單位（同 client 的 ART_T；實際畫到 48 的格子上）。高低差每級 6.5（＝遊戲的 RAISE 6 換算成 52 單位）。
// 依賴：realms.js（Realms.OBJ、雲嶺地板）、explore.js（地面、屋舍、營火、寶箱、石碑、傳送點）、storyDoll.js（H 畫法層）。全部程式繪製。
window.CloudTiles = (() => {
  const E = Explore, T = 52, TAU = Math.PI * 2, OUT = "#1c1712", RAISE = 6.5;
  const { box, rr, dot, rgba, shade } = E;
  const C = { slate: "#7d8c84", ink: "#56645c", moss: "#5a8a3a", bamboo: "#6aa84a", red: "#b8432f", redDark: "#8a2f20", tile: "#3c4a48", mist: "#e8e8e0", lamp: "#ffcf6a", water: "#3f7aa8", rock: "#6e6a62", rockD: "#4e4a44", mud: "#7a6a48", wood: "#8a6440" };
  const R = E.R;
  function shadow(ctx, cx, cy, rx, ry, a = 0.3) { ctx.fillStyle = `rgba(0,0,0,${a})`; ctx.beginPath(); ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU); ctx.fill(); }

  // ============ 地面與自動接邊 ============
  /** 石階：一格裡 3 階，往北（上方）升高；用在高度相差 1 的相鄰格之間（自動判斷）。 */
  function stairs(ctx, x, y, gx, gy) {
    ctx.fillStyle = C.ink; ctx.fillRect(x, y, T, T);
    for (let k = 0; k < 3; k++) { const yy = y + 2 + k * 17, f = 1.08 - k * 0.06; box(ctx, x + 2, yy, T - 4, 14, shade(C.slate, f), null, 0, 2); ctx.fillStyle = "rgba(255,255,255,0.18)"; ctx.fillRect(x + 3, yy + 1, T - 6, 2); ctx.fillStyle = "rgba(0,0,0,0.35)"; ctx.fillRect(x + 2, yy + 13, T - 4, 3); }
    const r = R(gx, gy, 31); if (r() < 0.5) dot(ctx, x + 6 + r() * 40, y + 10 + r() * 30, 2.4, rgba(C.moss, 0.7));
    for (const sx of [x + 1, x + T - 5]) { ctx.fillStyle = shade(C.rock, 0.9); ctx.fillRect(sx, y, 4, T); }
  }
  /** 水岸：陸地格，sides 是哪幾邊接水（n/s/w/e）；岸邊有淺色水線、卵石、蘆葦。 */
  function shore(ctx, x, y, gx, gy, sides) {
    E.ground(ctx, "g", gx, gy);
    const r = R(gx, gy, 41);
    for (const s of sides) {
      ctx.save();
      const edge = { n: [x, y, T, 10], s: [x, y + T - 10, T, 10], w: [x, y, 10, T], e: [x + T - 10, y, 10, T] }[s];
      const g = s === "n" || s === "s" ? ctx.createLinearGradient(0, edge[1] + (s === "n" ? 0 : 10), 0, edge[1] + (s === "n" ? 10 : 0)) : ctx.createLinearGradient(edge[0] + (s === "w" ? 0 : 10), 0, edge[0] + (s === "w" ? 10 : 0), 0);
      g.addColorStop(0, "#d8c89a"); g.addColorStop(1, "rgba(216,200,154,0)");
      ctx.fillStyle = g; ctx.fillRect(...edge);
      for (let k = 0; k < 4; k++) { const px = s === "w" ? x + 3 + r() * 5 : s === "e" ? x + T - 8 + r() * 5 : x + 6 + r() * 40, py = s === "n" ? y + 3 + r() * 5 : s === "s" ? y + T - 8 + r() * 5 : y + 6 + r() * 40; box(ctx, px, py, 4 + r() * 3, 3 + r() * 2, shade("#9a948a", 0.9 + r() * 0.2), OUT, 0.8, 2); }
      ctx.restore();
    }
    if (sides.length && r() < 0.6) { ctx.strokeStyle = "#5a8a3a"; ctx.lineWidth = 1.6; ctx.lineCap = "round"; const bx = x + 14 + r() * 20, by = y + 24; for (let k = 0; k < 5; k++) { ctx.beginPath(); ctx.moveTo(bx + k * 3, by + 10); ctx.quadraticCurveTo(bx + k * 3 + 2, by, bx + k * 3 + 1, by - 8 - k % 2 * 4); ctx.stroke(); } ctx.fillStyle = "#8a6a3a"; ctx.fillRect(bx + 5, by - 12, 2, 6); }
  }
  /** 河水（實地地圖用；戰鬥照舊是水表面或深淵）：流動的反光線往同一個方向。 */
  function river(ctx, x, y, gx, gy, deep = false) {
    ctx.fillStyle = deep ? shade(C.water, 0.75) : C.water; ctx.fillRect(x, y, T, T);
    const r = R(gx, gy, 51); ctx.strokeStyle = "rgba(255,255,255,0.4)"; ctx.lineWidth = 1.4; ctx.lineCap = "round";
    for (let k = 0; k < 3; k++) { const yy = y + 8 + k * 16 + r() * 4, xx = x + r() * 20; ctx.beginPath(); ctx.moveTo(xx, yy); ctx.lineTo(xx + 14 + r() * 8, yy); ctx.stroke(); }
  }
  /** 梯田：泥水田＋秧苗列＋田埂（look floor=paddy 的實地版）。 */
  function paddy(ctx, x, y, gx, gy) {
    ctx.fillStyle = "#6a7a5a"; ctx.fillRect(x, y, T, T);
    ctx.fillStyle = "rgba(120,170,200,0.35)"; ctx.fillRect(x + 3, y + 3, T - 6, T - 9);
    ctx.strokeStyle = "#7aa850"; ctx.lineWidth = 1.4; for (let row = 0; row < 4; row++) for (let k = 0; k < 5; k++) { const px = x + 7 + k * 9.5, py = y + 9 + row * 10; ctx.beginPath(); ctx.moveTo(px, py + 3); ctx.lineTo(px - 2, py - 2); ctx.moveTo(px, py + 3); ctx.lineTo(px + 2, py - 2); ctx.stroke(); }
    box(ctx, x, y + T - 7, T, 7, "#8a7a52", OUT, 1, 2);
  }
  /** 石板小徑：草地上的踏石。 */
  function steppingPath(ctx, x, y, gx, gy) {
    E.ground(ctx, "g", gx, gy); const r = R(gx, gy, 61);
    for (const [dx, dy] of [[10, 10], [28, 20], [14, 34]]) box(ctx, x + dx + r() * 4, y + dy + r() * 3, 15, 11, shade(C.slate, 0.95 + r() * 0.1), OUT, 1, 4);
  }
  /** 雲海（雲嶺的深淵）：往下是流動的白霧；崖邊是青石。 */
  function cloudSea(ctx, x, y, gx, gy, t = 0) {
    const g = ctx.createLinearGradient(0, y, 0, y + T); g.addColorStop(0, "#9aa8b0"); g.addColorStop(1, "#cfd8dc"); ctx.fillStyle = g; ctx.fillRect(x, y, T, T);
    const r = R(gx, gy, 71); for (let k = 0; k < 3; k++) { const px = x + ((r() * T + t * 0.01) % T), py = y + 10 + k * 15; const gg = ctx.createRadialGradient(px, py, 1, px, py, 18); gg.addColorStop(0, "rgba(255,255,255,0.75)"); gg.addColorStop(1, "rgba(255,255,255,0)"); ctx.fillStyle = gg; ctx.fillRect(x, y, T, T); }
  }

  // ============ 自然 ============
  function bambooGrove(ctx, x, y, w = 2, h = 2) { // 大片竹林（擋視線、可燃、不可推倒）
    shadow(ctx, x + w * T / 2 + 6, y + h * T - 8, w * T * 0.5, 12, 0.35);
    const r = R(x, y, 81);
    for (let k = 0; k < w * h * 3; k++) Realms.OBJ.bamboo(ctx, x + r() * (w - 1) * T, y + r() * (h - 0.6) * T);
  }
  function pine(ctx, x, y) { // 古松（大，1 格）
    const cx = x + T / 2; shadow(ctx, cx + 4, y + T * 0.9, 20, 6, 0.35);
    ctx.strokeStyle = OUT; ctx.lineWidth = 7; ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(cx, y + T * 0.92); ctx.quadraticCurveTo(cx - 6, y + 24, cx + 4, y + 8); ctx.stroke(); ctx.strokeStyle = "#6a4a30"; ctx.lineWidth = 4.5; ctx.stroke();
    for (const [dx, dy, rw] of [[-14, 10, 16], [12, 4, 15], [-2, -4, 14], [14, 20, 11]]) { ctx.fillStyle = "#2f5a3a"; ctx.beginPath(); ctx.ellipse(cx + dx, y + dy, rw, rw * 0.45, 0, 0, TAU); ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = OUT; ctx.stroke(); ctx.fillStyle = "rgba(160,220,140,0.25)"; ctx.beginPath(); ctx.ellipse(cx + dx - 3, y + dy - 2, rw * 0.6, rw * 0.2, 0, 0, TAU); ctx.fill(); }
  }
  function boulder(ctx, x, y) { // 山石（擋路、半掩護＝low_wall 的功能）
    shadow(ctx, x + T / 2 + 3, y + T * 0.78, 20, 6);
    ctx.beginPath(); ctx.moveTo(x + 8, y + 40); ctx.lineTo(x + 12, y + 20); ctx.lineTo(x + 26, y + 12); ctx.lineTo(x + 40, y + 18); ctx.lineTo(x + 45, y + 38); ctx.closePath(); ctx.fillStyle = C.rock; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.18)"; ctx.beginPath(); ctx.moveTo(14, 0); ctx.closePath(); ctx.fillRect(x + 16, y + 18, 12, 3); dot(ctx, x + 34, y + 30, 3, rgba(C.moss, 0.8));
  }
  function flowers(ctx, x, y, gx, gy) { // 花草（純裝飾）
    const r = R(gx, gy, 91); for (let k = 0; k < 6; k++) { const px = x + 6 + r() * 40, py = y + 10 + r() * 34; ctx.strokeStyle = "#4f8a3a"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(px, py + 5); ctx.lineTo(px, py); ctx.stroke(); dot(ctx, px, py, 2.2, ["#f2e6c8", "#e8a0b0", "#ffd23a"][k % 3]); }
  }

  // ============ 建築（多格） ============
  /** 山門：兩根朱紅柱＋黛瓦門頂＋匾額，跨 3 格寬；中間是通道（出口或門）。 */
  function mountainGate(ctx, x, y) {
    const W = 3 * T; shadow(ctx, x + W / 2 + 8, y + T * 1.92, W * 0.48, 10, 0.35);
    for (const px of [x + T * 0.55, x + W - T * 0.55]) { box(ctx, px - 8, y + T * 0.45, 16, T * 1.45, C.red, OUT, 2, 2); ctx.fillStyle = C.redDark; ctx.fillRect(px + 2, y + T * 0.5, 5, T * 1.35); box(ctx, px - 12, y + T * 1.82, 24, 9, C.slate, OUT, 2, 2); }
    box(ctx, x + T * 0.3, y + T * 0.45, W - T * 0.6, 10, C.redDark, OUT, 2, 1);
    ctx.beginPath(); ctx.moveTo(x - 10, y + T * 0.48); ctx.lineTo(x + 8, y + 6); ctx.lineTo(x + W - 8, y + 6); ctx.lineTo(x + W + 10, y + T * 0.48); ctx.quadraticCurveTo(x + W / 2, y + T * 0.32, x - 10, y + T * 0.48); ctx.fillStyle = C.tile; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = "#141c1a"; ctx.stroke();
    box(ctx, x + 6, y + 2, W - 12, 6, "#2a3634", "#141c1a", 1.5, 2);
    box(ctx, x + W / 2 - 20, y + T * 0.62, 40, 16, "#2a2018", "#e8bb48", 1.6, 2);
    ctx.fillStyle = "#e8bb48"; ctx.font = "bold 10px 'Microsoft JhengHei'"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText("青霧觀", x + W / 2, y + T * 0.62 + 8.5); ctx.textAlign = "left";
  }
  /** 亭子：2×2，四柱＋攢尖頂（可以站在底下；擋視線只有柱子）。 */
  function pavilion(ctx, x, y) {
    const W = 2 * T; shadow(ctx, x + W / 2 + 6, y + W - 6, W * 0.46, 10, 0.3);
    box(ctx, x + 6, y + T * 0.9, W - 12, W - T * 0.9 - 6, shade(C.slate, 1.05), OUT, 2, 3);
    for (const [px, py] of [[x + 14, y + T * 0.75], [x + W - 14, y + T * 0.75], [x + 14, y + W - 18], [x + W - 14, y + W - 18]]) box(ctx, px - 4, py - 26, 8, 30, C.red, OUT, 1.6, 1);
    ctx.beginPath(); ctx.moveTo(x - 6, y + T * 0.72); ctx.lineTo(x + W / 2, y + 2); ctx.lineTo(x + W + 6, y + T * 0.72); ctx.quadraticCurveTo(x + W / 2, y + T * 0.55, x - 6, y + T * 0.72); ctx.fillStyle = C.tile; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = "#141c1a"; ctx.stroke();
    dot(ctx, x + W / 2, y + 2, 3.5, "#e8bb48");
  }
  /** 竹籬：一格的籬笆段（擋路、可燃、半掩護）。 */
  function fence(ctx, x, y) {
    shadow(ctx, x + T / 2, y + T * 0.72, T * 0.45, 5, 0.25);
    for (let k = 0; k < 6; k++) box(ctx, x + 2 + k * 8.4, y + 14 + (k % 2) * 3, 5, 26, "#b9a05a", OUT, 1.2, 2);
    for (const yy of [22, 32]) box(ctx, x, y + yy, T, 4, "#9a8448", OUT, 1, 1);
  }

  // ============ 地物 ============
  function altar(ctx, x, y) { // 祭壇（情境物件）：石台＋香爐＋裊裊煙
    const cx = x + T / 2; shadow(ctx, cx + 3, y + T * 0.84, 22, 6);
    box(ctx, x + 6, y + 26, T - 12, 16, shade(C.slate, 1.1), OUT, 2, 2); box(ctx, x + 10, y + 22, T - 20, 6, C.slate, OUT, 1.6, 1);
    ctx.beginPath(); ctx.ellipse(cx, y + 20, 8, 4, 0, 0, TAU); ctx.fillStyle = "#8a6a3a"; ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = OUT; ctx.stroke(); box(ctx, cx - 7, y + 14, 14, 7, "#a07a40", OUT, 1.6, 2);
    ctx.strokeStyle = "rgba(240,240,235,0.7)"; ctx.lineWidth = 1.5; for (let k = -1; k <= 1; k++) { ctx.beginPath(); ctx.moveTo(cx + k * 3, y + 13); ctx.bezierCurveTo(cx + k * 3 - 4, y + 6, cx + k * 3 + 4, y + 2, cx + k * 3, y - 4); ctx.stroke(); }
    dot(ctx, x + 12, y + 30, 2, C.red); dot(ctx, x + T - 12, y + 30, 2, C.red);
  }
  function caveMouth(ctx, x, y) { // 洞口（門／隱藏入口）：岩壁上的黑洞＋入口光圈
    ctx.fillStyle = C.rockD; ctx.fillRect(x, y, T, T * 0.7); for (let k = 0; k < 4; k++) { ctx.strokeStyle = "rgba(0,0,0,0.4)"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(x + 6 + k * 12, y); ctx.lineTo(x + 2 + k * 12, y + T * 0.7); ctx.stroke(); }
    ctx.beginPath(); ctx.moveTo(x + 10, y + T * 0.72); ctx.quadraticCurveTo(x + 10, y + 10, x + T / 2, y + 8); ctx.quadraticCurveTo(x + T - 10, y + 10, x + T - 10, y + T * 0.72); ctx.closePath(); ctx.fillStyle = "#0e0c0a"; ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = OUT; ctx.stroke();
    E.entrance(ctx, x / T - 0.5 + 0.5, y / T + 0.62);
  }
  function ropeBridge(ctx, x, y, n = 3) { // 吊橋（wooden_bridge 的雲嶺外觀）：竹板、兩側繩索，下面是雲海
    for (let k = 0; k < n; k++) for (let p = 0; p < T; p += 8) box(ctx, x + k * T + p, y + 12, 6.5, T - 24, shade("#b9a05a", 0.9 + ((p * 7 + k) % 10) / 50), OUT, 1.2, 1);
    ctx.strokeStyle = "#8a6a3a"; ctx.lineWidth = 2; for (const yy of [y + 12, y + T - 12]) { ctx.beginPath(); ctx.moveTo(x - 6, yy - 6); ctx.quadraticCurveTo(x + n * T / 2, yy + 6, x + n * T + 6, yy - 6); ctx.stroke(); }
    for (const px of [x - 6, x + n * T + 2]) for (const yy of [y + 2, y + T - 20]) box(ctx, px, yy, 6, 16, C.wood, OUT, 1.4, 1);
  }
  function teleportStone(ctx, x, y) { E.waypoint(ctx, x / T, y / T); }

  // ============ 氛圍 ============
  /** 迷霧三段（6C-6）：level 0＝沒探索（濃霧蓋住）、1＝探索過但看不到（淡霧、看得到地形）、2＝看得見（無霧）。 */
  function fogCell(ctx, x, y, level, gx, gy) {
    if (level >= 2) return;
    const r = R(gx, gy, 101), cx = x + T / 2 + (r() - 0.5) * 8, cy = y + T / 2 + (r() - 0.5) * 8;
    const g = ctx.createRadialGradient(cx, cy, 4, cx, cy, T * 0.95);
    const a = level === 0 ? 0.92 : 0.45;
    g.addColorStop(0, `rgba(214,220,216,${a})`); g.addColorStop(0.65, `rgba(206,214,210,${a * 0.75})`); g.addColorStop(1, "rgba(206,214,210,0)");
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, T * 0.95, 0, TAU); ctx.fill();
  }
  function mistWisp(ctx, x, y, t = 0) { // 飄霧（裝飾層，不影響視線）
    for (let k = 0; k < 3; k++) { const px = x + 10 + k * 14 + Math.sin(t / 900 + k) * 4, py = y + 20 + k * 6; const g = ctx.createRadialGradient(px, py, 1, px, py, 16); g.addColorStop(0, "rgba(232,232,224,0.45)"); g.addColorStop(1, "rgba(232,232,224,0)"); ctx.fillStyle = g; ctx.fillRect(x - 10, y, T + 20, T); }
  }

  /** 高低差：格子往上抬 RAISE×級數，南側畫岩壁立面（雲嶺的山壁質感）。 */
  function cliffFace(ctx, x, y, h) {
    if (h <= 0) return;
    ctx.fillStyle = C.rockD; ctx.fillRect(x, y + T, T, h * RAISE);
    ctx.strokeStyle = "rgba(0,0,0,0.35)"; ctx.lineWidth = 1; for (let k = 1; k < h; k++) { ctx.beginPath(); ctx.moveTo(x, y + T + k * RAISE); ctx.lineTo(x + T, y + T + k * RAISE); ctx.stroke(); }
    ctx.fillStyle = "rgba(255,255,255,0.12)"; ctx.fillRect(x, y + T, T, 1.5);
  }

  return { T, RAISE, C, stairs, shore, river, paddy, steppingPath, cloudSea, bambooGrove, pine, boulder, flowers, mountainGate, pavilion, fence, altar, caveMouth, ropeBridge, teleportStone, fogCell, mistWisp, cliffFace };
})();
