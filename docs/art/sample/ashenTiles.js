// 灰燼荒原實地地圖：地磚與地物圖庫（美術 PM，2026-11-04）。給 6D 的 18 張荒原實地地圖用；畫風同 explore.png。
// 地形與 9 種物件的荒原外觀已在 5A-ART6 做好（regions4.js 的 ashen_waste）；這裡補實地地圖才需要的：自動接邊、建築、村落、地物、氛圍。
// 座標以 52 虛擬格為單位；高低差每級 6.5。依賴：regions4.js、explore.js、cloudTiles.js、realms.js、storyDoll.js。全部程式繪製。
window.AshenTiles = (() => {
  const E = Explore, R4 = Regions4, CT = CloudTiles, T = 52, TAU = Math.PI * 2, OUT = "#1c1712";
  const { box, dot, rgba, shade } = E;
  const ASH = R4.REGIONS.find((r) => r.id === "ashen_waste");
  const A = { scorch: "#4a3a30", char: "#2a1e18", lava: "#ff6a1a", hot: "#ffb030", ruin: "#6a5e54", rust: "#9a4a20", iron: "#5a5e60", tar: "#1a1410", sand: "#b0703a", obs: "#1e1a24", sulfur: "#d8c84a", rag: "#c8b08a" };
  const R = E.R;
  const tile = (ctx, id, x, y, gx, gy) => R4.tile(ctx, ASH, id, x, y, gx, gy);
  const obj = (ctx, id, x, y) => R4.object(ctx, ASH, id, x, y);
  function shadow(ctx, cx, cy, rx, ry, a = 0.3) { ctx.fillStyle = `rgba(0,0,0,${a})`; ctx.beginPath(); ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU); ctx.fill(); }
  function glow(ctx, x, y, r, c, a) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, c); g.addColorStop(1, "rgba(0,0,0,0)"); ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); ctx.restore(); }

  // ============ 地面與自動接邊 ============
  /** 熔岩岸：焦土格鄰接岩漿的那一邊，結殼的黑邊＋往外漸弱的熱光（致命地形的邊界看得出來）。 */
  function lavaShore(ctx, x, y, gx, gy, sides) {
    tile(ctx, "stone", x, y, gx, gy);
    for (const s of sides) {
      const rect = { n: [x, y, T, 12], s: [x, y + T - 12, T, 12], w: [x, y, 12, T], e: [x + T - 12, y, 12, T] }[s];
      const g = s === "n" || s === "s" ? ctx.createLinearGradient(0, s === "n" ? y : y + T, 0, s === "n" ? y + 12 : y + T - 12) : ctx.createLinearGradient(s === "w" ? x : x + T, 0, s === "w" ? x + 12 : x + T - 12, 0);
      g.addColorStop(0, "rgba(255,120,40,0.75)"); g.addColorStop(1, "rgba(255,120,40,0)"); ctx.fillStyle = g; ctx.fillRect(...rect);
      const r = R(gx, gy, 11); ctx.fillStyle = A.char;
      for (let k = 0; k < 5; k++) { const px = s === "w" ? x + 1 : s === "e" ? x + T - 6 : x + k * 11 + r() * 4, py = s === "n" ? y + 1 : s === "s" ? y + T - 6 : y + k * 11 + r() * 4; box(ctx, px, py, 6 + r() * 3, 5, A.char, OUT, 0.8, 2); }
    }
  }
  /** 熔岩河（實地：慢慢流動的亮紋）＝lava。 */
  function lavaRiver(ctx, x, y, gx, gy, t = 0) { tile(ctx, "lava", x, y, gx, gy); ctx.strokeStyle = "rgba(255,240,180,0.55)"; ctx.lineWidth = 1.6; const r = R(gx, gy, 21); for (let k = 0; k < 2; k++) { const yy = y + 14 + k * 20, xx = x + ((r() * 30 + t * 0.02) % 30); ctx.beginPath(); ctx.moveTo(xx, yy); ctx.quadraticCurveTo(xx + 10, yy - 3, xx + 20, yy); ctx.stroke(); } }
  /** 焦油坑（tar_pits）：黑亮的油面＋氣泡；功能＝油表面。 */
  function tar(ctx, x, y, gx, gy) {
    tile(ctx, "stone", x, y, gx, gy); const r = R(gx, gy, 31);
    ctx.fillStyle = A.tar; ctx.beginPath(); ctx.ellipse(x + T / 2, y + T / 2, 22, 18, r() * 0.5, 0, TAU); ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = "rgba(200,170,90,0.6)"; ctx.stroke();
    for (let k = 0; k < 3; k++) { ctx.strokeStyle = "rgba(255,255,255,0.35)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(x + 14 + r() * 24, y + 14 + r() * 24, 2 + r() * 2, 0, TAU); ctx.stroke(); }
    ctx.fillStyle = "rgba(160,120,255,0.3)"; ctx.beginPath(); ctx.ellipse(x + 20, y + 20, 8, 3, -0.4, 0, TAU); ctx.fill();
  }
  /** 紅沙（赤沙村一帶的地面）。 */
  function redSand(ctx, x, y, gx, gy) { const r = R(gx, gy, 41); ctx.fillStyle = shade(A.sand, 0.92 + r() * 0.12); ctx.fillRect(x, y, T, T); ctx.strokeStyle = "rgba(255,220,180,0.3)"; ctx.lineWidth = 1; for (let k = 0; k < 2; k++) { const yy = y + 14 + k * 20 + r() * 4; ctx.beginPath(); ctx.moveTo(x + 6, yy); ctx.quadraticCurveTo(x + T / 2, yy - 4, x + T - 6, yy); ctx.stroke(); } for (let k = 0; k < 8; k++) { ctx.fillStyle = "rgba(60,30,10,0.35)"; ctx.fillRect(x + r() * T, y + r() * T, 1.8, 1.8); } }
  /** 黑曜石地（黑曜谷）：深紫黑、有尖銳的反光。 */
  function obsidian(ctx, x, y, gx, gy) { const r = R(gx, gy, 51); ctx.fillStyle = shade(A.obs, 0.9 + r() * 0.2); ctx.fillRect(x, y, T, T); for (let k = 0; k < 3; k++) { const px = x + 6 + r() * 36, py = y + 6 + r() * 36; ctx.fillStyle = "rgba(180,160,255,0.35)"; ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px + 6, py + 2); ctx.lineTo(px + 2, py + 8); ctx.closePath(); ctx.fill(); } ctx.strokeStyle = "rgba(0,0,0,0.4)"; ctx.strokeRect(x + 0.5, y + 0.5, T - 1, T - 1); }
  /** 岩壁立面（焦黑），用在高台邊。 */
  function cliff(ctx, x, y, h) { if (h <= 0) return; ctx.fillStyle = "#2a221e"; ctx.fillRect(x, y + T, T, h * CT.RAISE); for (let k = 1; k <= h; k++) { ctx.fillStyle = "rgba(255,106,26,0.25)"; ctx.fillRect(x + 6 + k * 9, y + T + k * CT.RAISE - 3, 2, 2); } }

  // ============ 自然 ============
  function deadGrove(ctx, x, y, w = 2, h = 2) { // 枯木林（擋視線、可燃、不可推倒）：大片焦黑枯樹＋枯草
    shadow(ctx, x + w * T / 2 + 6, y + h * T - 8, w * T * 0.5, 12, 0.35);
    const r = R(x, y, 61); for (let k = 0; k < w * h * 2 + 1; k++) obj(ctx, "dead_tree", x + r() * (w - 0.8) * T, y + r() * (h - 0.8) * T);
    for (let k = 0; k < w * h; k++) obj(ctx, "grass", x + r() * (w - 1) * T, y + (h - 1) * T * r());
  }
  function vent(ctx, x, y, t = 0) { // 硫磺噴口（裝飾＋可以當煙霧來源）
    const cx = x + T / 2, cy = y + T * 0.65; ctx.fillStyle = A.char; ctx.beginPath(); ctx.ellipse(cx, cy, 12, 6, 0, 0, TAU); ctx.fill(); ctx.strokeStyle = A.sulfur; ctx.lineWidth = 2; ctx.stroke();
    for (let k = 0; k < 3; k++) { const ph = ((t / 1200) + k / 3) % 1; const g = ctx.createRadialGradient(cx, cy - ph * 30, 1, cx, cy - ph * 30, 10 + ph * 8); g.addColorStop(0, `rgba(230,220,140,${0.5 * (1 - ph)})`); g.addColorStop(1, "rgba(230,220,140,0)"); ctx.fillStyle = g; ctx.fillRect(x - 10, y - 30, T + 20, T + 30); }
  }
  function obsidianSpike(ctx, x, y) { // 黑曜石柱（擋路、擋視線＝stone_pillar 的功能）
    shadow(ctx, x + T / 2 + 3, y + T * 0.85, 16, 5);
    for (const [dx, h, w] of [[-8, 34, 7], [4, 42, 8], [12, 24, 6]]) { const px = x + T / 2 + dx; ctx.beginPath(); ctx.moveTo(px - w, y + T * 0.85); ctx.lineTo(px, y + T * 0.85 - h); ctx.lineTo(px + w, y + T * 0.85); ctx.closePath(); ctx.fillStyle = A.obs; ctx.fill(); ctx.lineWidth = 1.8; ctx.strokeStyle = OUT; ctx.stroke(); ctx.fillStyle = "rgba(180,160,255,0.4)"; ctx.beginPath(); ctx.moveTo(px - 1, y + T * 0.8); ctx.lineTo(px, y + T * 0.85 - h + 4); ctx.lineTo(px + 2, y + T * 0.8); ctx.fill(); }
  }
  function ashFall(ctx, x, y, w, h, t = 0) { // 飄灰（裝飾層）：細小的灰點斜斜落下，夾幾顆餘燼
    for (let k = 0; k < w * h * 3; k++) { const r = R(k, 7, 71); const px = x + ((r() * w * T + t * 0.02) % (w * T)), py = y + ((r() * h * T + t * 0.03) % (h * T)); ctx.fillStyle = k % 9 === 0 ? "rgba(255,140,60,0.8)" : "rgba(200,190,180,0.55)"; ctx.fillRect(px, py, 1.6, 1.6); }
  }

  // ============ 建築（多格） ============
  /** 廢鐵屋：鏽鐵板拼的牆＋斜鐵皮屋頂＋布簾門（村落、餘燼集共用）。 */
  function scrapHouse(ctx, x, y, w, h, opt = {}) {
    const W = w * T, faceTop = y + (h - 1.2) * T;
    shadow(ctx, x + W / 2 + 8, y + h * T - 2, W / 2 + 4, 10, 0.4);
    for (let k = 0; k < w * 3; k++) box(ctx, x + 4 + k * (W - 8) / (w * 3), faceTop, (W - 8) / (w * 3) + 1, 1.2 * T - 4, shade(k % 2 ? A.iron : A.rust, 0.85 + (k % 3) * 0.08), OUT, 1.4, 1);
    for (let k = 0; k < w * 2; k++) dot(ctx, x + 10 + k * (W - 20) / (w * 2 - 1), faceTop + 6, 1.4, "#c8b8a0");
    ctx.beginPath(); ctx.moveTo(x - 4, faceTop + 4); ctx.lineTo(x + 8, y + 6); ctx.lineTo(x + W + 6, y + 14); ctx.lineTo(x + W + 4, faceTop + 6); ctx.closePath(); ctx.fillStyle = shade(A.iron, 0.8); ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.strokeStyle = "rgba(0,0,0,0.35)"; ctx.lineWidth = 1.2; for (let k = x + 14; k < x + W; k += 12) { ctx.beginPath(); ctx.moveTo(k, y + 8 + (k - x) * 0.06); ctx.lineTo(k - 6, faceTop + 4); ctx.stroke(); }
    const dx = x + (opt.door ?? w / 2) * T; box(ctx, dx - 12, faceTop + 1.2 * T - 34, 24, 30, A.rag, OUT, 1.6, 2); ctx.fillStyle = "rgba(0,0,0,0.25)"; ctx.fillRect(dx - 2, faceTop + 1.2 * T - 32, 2, 26);
    E.entrance(ctx, (opt.door ?? w / 2) + x / T - 0.5, y / T + h);
    if (opt.chimney) { box(ctx, x + W - 22, y - 10, 10, 26, A.iron, OUT, 1.6, 1); glow(ctx, x + W - 17, y - 14, 16, "rgba(255,140,60,0.9)", 0.6); }
    if (opt.sign) E.ICON && opt.sign && (() => { box(ctx, dx + 16, faceTop + 4, 22, 20, "#3a2a1e", OUT, 1.6, 3); box(ctx, dx + 19, faceTop + 7, 16, 14, "#f2e6c8", null, 0, 2); E.ICON[opt.sign](ctx, dx + 27, faceTop + 14, 11); })();
  }
  /** 帳篷（營地、斷崖幫運輸道）：破布三角帳。 */
  function tent(ctx, x, y) {
    shadow(ctx, x + T / 2 + 6, y + T * 0.88, 26, 7, 0.35);
    ctx.beginPath(); ctx.moveTo(x + 2, y + T * 0.85); ctx.lineTo(x + T / 2, y + 6); ctx.lineTo(x + T - 2, y + T * 0.85); ctx.closePath(); ctx.fillStyle = A.rag; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + T / 2, y + 10); ctx.lineTo(x + T / 2 - 8, y + T * 0.85); ctx.lineTo(x + T / 2 + 8, y + T * 0.85); ctx.closePath(); ctx.fillStyle = "#2a1e18"; ctx.fill();
    ctx.strokeStyle = "#8a6a4a"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(x + 14, y + 26); ctx.lineTo(x + 20, y + 30); ctx.stroke();
  }
  /** 瞭望塔（舊鐵哨站）：鐵架＋平台（高、擋視線＝stone_pillar）。 */
  function watchtower(ctx, x, y) {
    const cx = x + T / 2; shadow(ctx, cx + 6, y + T * 0.9, 18, 5, 0.4);
    ctx.strokeStyle = OUT; ctx.lineWidth = 4; for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(cx + s * 14, y + T * 0.9); ctx.lineTo(cx + s * 8, y - 18); ctx.stroke(); }
    ctx.strokeStyle = A.iron; ctx.lineWidth = 2.4; for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(cx + s * 14, y + T * 0.9); ctx.lineTo(cx + s * 8, y - 18); ctx.stroke(); } ctx.beginPath(); ctx.moveTo(cx - 12, y + 30); ctx.lineTo(cx + 10, y + 8); ctx.moveTo(cx + 12, y + 30); ctx.lineTo(cx - 10, y + 8); ctx.stroke();
    box(ctx, cx - 16, y - 24, 32, 8, A.rust, OUT, 1.8, 1); box(ctx, cx - 14, y - 36, 28, 12, "#3a2a1e", OUT, 1.6, 1); glow(ctx, cx, y - 30, 14, "rgba(255,160,60,0.9)", 0.5);
  }
  /** 熔心坑前廳的拱門：黑曜石與玄武岩疊成的拱（2 格寬，中間可走）。 */
  function obsidianArch(ctx, x, y) {
    const W = 2 * T; shadow(ctx, x + W / 2 + 6, y + T * 1.9, W * 0.5, 9, 0.4);
    for (const px of [x + 10, x + W - 22]) box(ctx, px, y + 20, 14, T * 1.5, "#3a3330", OUT, 2, 3);
    ctx.beginPath(); ctx.moveTo(x + 2, y + 26); ctx.quadraticCurveTo(x + W / 2, y - 18, x + W - 2, y + 26); ctx.lineTo(x + W - 14, y + 30); ctx.quadraticCurveTo(x + W / 2, y - 2, x + 14, y + 30); ctx.closePath(); ctx.fillStyle = A.obs; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    glow(ctx, x + W / 2, y + 2, 18, "rgba(255,120,40,0.9)", 0.7); dot(ctx, x + W / 2, y + 2, 4, A.hot);
  }

  // ============ 地物 ============
  function coolingWell(ctx, x, y) { // 冷卻井（熔心坑、冷卻井地點）：石井圈＋藍水＋鐵轆轤
    const cx = x + T / 2, cy = y + T * 0.58; shadow(ctx, cx + 3, cy + 14, 20, 6);
    ctx.beginPath(); ctx.ellipse(cx, cy, 18, 11, 0, 0, TAU); ctx.fillStyle = "#6a5e54"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.beginPath(); ctx.ellipse(cx, cy, 12, 7, 0, 0, TAU); ctx.fillStyle = "#3f8ac8"; ctx.fill(); ctx.strokeStyle = "rgba(255,255,255,0.5)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.ellipse(cx - 2, cy - 1, 6, 2, 0, 0, TAU); ctx.stroke();
    ctx.strokeStyle = A.iron; ctx.lineWidth = 2.6; ctx.beginPath(); ctx.moveTo(cx - 16, cy); ctx.lineTo(cx - 14, cy - 24); ctx.lineTo(cx + 14, cy - 24); ctx.lineTo(cx + 16, cy); ctx.stroke(); box(ctx, cx - 6, cy - 28, 12, 7, A.rust, OUT, 1.2, 2);
  }
  function forge(ctx, x, y) { // 鍛爐（鐵爐村、餘燼集鐵匠）：石爐＋火口＋鐵砧
    const cx = x + T / 2; shadow(ctx, cx + 4, y + T * 0.88, 22, 6);
    box(ctx, x + 6, y + 14, T - 12, 30, "#5a4e44", OUT, 2, 4); ctx.fillStyle = "#1a120c"; ctx.beginPath(); ctx.arc(cx, y + 32, 8, Math.PI, 0); ctx.fill(); glow(ctx, cx, y + 30, 16, "rgba(255,140,40,0.95)", 0.8); dot(ctx, cx, y + 31, 4, A.hot);
    box(ctx, x + T - 16, y + 2, 9, 16, "#5a4e44", OUT, 1.6, 1);
  }
  function scrapStall(ctx, x, y, awning = "#a83a2a") { // 攤位（餘燼集市集）：木架＋破布遮篷＋貨
    shadow(ctx, x + T / 2 + 3, y + T * 0.86, 22, 6);
    box(ctx, x + 6, y + 26, T - 12, 16, "#7a5a38", OUT, 1.8, 2); for (const [dx, c] of [[12, A.iron], [22, A.rust], [32, "#c8b08a"]]) box(ctx, x + dx, y + 20, 8, 8, c, OUT, 1, 2);
    ctx.beginPath(); ctx.moveTo(x + 2, y + 18); ctx.lineTo(x + T - 2, y + 18); ctx.lineTo(x + T - 6, y + 6); ctx.lineTo(x + 6, y + 6); ctx.closePath(); ctx.fillStyle = awning; ctx.fill(); ctx.lineWidth = 1.8; ctx.strokeStyle = OUT; ctx.stroke();
    for (let k = 0; k < 4; k++) { ctx.fillStyle = "rgba(255,255,255,0.18)"; ctx.fillRect(x + 8 + k * 10, y + 7, 4, 11); }
  }
  function hornAltar(ctx, x, y) { // 角魔古祭壇：黑石台＋兩支彎角＋暗紅符文
    const cx = x + T / 2; shadow(ctx, cx + 3, y + T * 0.86, 22, 6);
    box(ctx, x + 6, y + 28, T - 12, 14, "#2e2622", OUT, 2, 2);
    for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(cx + s * 12, y + 30); ctx.quadraticCurveTo(cx + s * 22, y + 8, cx + s * 8, y + 2); ctx.quadraticCurveTo(cx + s * 16, y + 12, cx + s * 6, y + 30); ctx.closePath(); ctx.fillStyle = "#bfb0a4"; ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = OUT; ctx.stroke(); }
    ctx.save(); ctx.shadowColor = "#ff3a2a"; ctx.shadowBlur = 6; ctx.strokeStyle = "#c83a2a"; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.arc(cx, y + 35, 4, 0, TAU); ctx.moveTo(cx - 8, y + 35); ctx.lineTo(cx + 8, y + 35); ctx.stroke(); ctx.restore();
  }
  function cart(ctx, x, y) { // 運輸車（斷崖幫運輸道）：鐵輪木車＋源晶碎片箱
    shadow(ctx, x + T / 2 + 4, y + T * 0.84, 24, 6);
    box(ctx, x + 4, y + 16, T - 8, 20, "#7a5a38", OUT, 2, 2); for (const px of [x + 12, x + T - 12]) { ctx.beginPath(); ctx.arc(px, y + 38, 7, 0, TAU); ctx.fillStyle = A.iron; ctx.fill(); ctx.lineWidth = 1.8; ctx.strokeStyle = OUT; ctx.stroke(); }
    box(ctx, x + 14, y + 8, 22, 10, "#5a4030", OUT, 1.4, 1); glow(ctx, x + 25, y + 12, 10, "rgba(140,220,255,0.9)", 0.6); dot(ctx, x + 25, y + 12, 2.6, "#c8f0ff");
  }
  function ruinWall(ctx, x, y) { // 要塞殘牆（高，擋視線＝wall 地形的廢墟外觀）
    ctx.fillStyle = "#3a302a"; ctx.fillRect(x, y + 14, T, T - 14); ctx.fillStyle = "#5a4e44"; ctx.beginPath(); ctx.moveTo(x, y + 14); ctx.lineTo(x + 10, y + 2); ctx.lineTo(x + 20, y + 10); ctx.lineTo(x + 34, y); ctx.lineTo(x + T, y + 12); ctx.lineTo(x + T, y + 20); ctx.lineTo(x, y + 22); ctx.closePath(); ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.strokeStyle = "rgba(0,0,0,0.4)"; ctx.lineWidth = 1; for (let k = 0; k < 3; k++) { ctx.beginPath(); ctx.moveTo(x, y + 30 + k * 8); ctx.lineTo(x + T, y + 30 + k * 8); ctx.stroke(); }
  }

  return { T, A, ASH, tile, obj, lavaShore, lavaRiver, tar, redSand, obsidian, cliff, deadGrove, vent, obsidianSpike, ashFall, scrapHouse, tent, watchtower, obsidianArch, coolingWell, forge, scrapStall, hornAltar, cart, ruinWall };
})();
