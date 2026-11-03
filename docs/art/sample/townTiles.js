// 城鎮圖庫：主城、霧渡鎮的建築與街景，以及 3 間室內（酒館、鐵匠鋪含附魔台、導師殿）。美術 PM，2026-11-04。
// 主城在五區中央的浮島上（21.1）：白石街道、藍頂金飾（晶冠城邦的基準風格），廣場中央是通往五區的傳送陣，五面區旗。
// 霧渡鎮沿用 explore.js 的白牆黛瓦屋舍。室內 10×8，畫在 20×12 畫面的中央（四周暗）。
// 依賴：storyDoll.js、paperdoll.js、realms.js、explore.js、regions4.js、ashenTiles.js。全部程式繪製。
window.TownTiles = (() => {
  const E = Explore, R4 = Regions4, T = 52, TAU = Math.PI * 2, OUT = "#1c1712";
  const { box, dot, rgba, shade } = E;
  const CROWN = R4.REGIONS.find((r) => r.id === "crystal_crown");
  const K = { stone: "#e8dcc0", stoneD: "#b8aa8a", roof: "#3a5ad0", roofD: "#2a4098", gold: "#e8bb48", crystal: "#8f7bff", wood: "#8a6440", woodL: "#a8804e", plank: "#9a7448", rug: "#8a2f3a", wall: "#5a4030" };
  const REGION_COL = { crystal_crown: "#8f7bff", cloud_ridge: "#6aa84a", arcane_hub: "#4ae0d0", ashen_waste: "#ff6a1a", frost_tide: "#7ad8ff" };
  function shadow(ctx, cx, cy, rx, ry, a = 0.3) { ctx.fillStyle = `rgba(0,0,0,${a})`; ctx.beginPath(); ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU); ctx.fill(); }
  function glow(ctx, x, y, r, c, a) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, c); g.addColorStop(1, "rgba(0,0,0,0)"); ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); ctx.restore(); }
  const plaza = (ctx, gx, gy) => R4.tile(ctx, CROWN, "stone", gx * T, gy * T, gx, gy);

  // ============ 主城的建築 ============
  /** 白石藍頂的建築（主城）：立面白石＋金邊，藍色瓦頂，門口有入口光圈；sign 是招牌圖示。 */
  function stoneHall(ctx, gx, gy, w, h, opt = {}) {
    const x = gx * T, y = gy * T, W = w * T, faceTop = y + (h - 1.4) * T, faceH = 1.4 * T;
    shadow(ctx, x + W / 2 + 10, y + h * T - 2, W / 2 + 6, 10, 0.35);
    box(ctx, x + 4, faceTop, W - 8, faceH - 4, K.stone, OUT, 2, 2);
    ctx.strokeStyle = "rgba(120,100,70,0.45)"; ctx.lineWidth = 1; for (let k = 1; k < 4; k++) { ctx.beginPath(); ctx.moveTo(x + 6, faceTop + k * 17); ctx.lineTo(x + W - 6, faceTop + k * 17); ctx.stroke(); }
    ctx.fillStyle = K.gold; ctx.fillRect(x + 4, faceTop, W - 8, 3);
    ctx.beginPath(); ctx.moveTo(x - 6, faceTop + 6); ctx.lineTo(x + 10, y + 4); ctx.lineTo(x + W - 10, y + 4); ctx.lineTo(x + W + 6, faceTop + 6); ctx.closePath(); ctx.fillStyle = K.roof; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.strokeStyle = rgba(K.roofD, 0.8); ctx.lineWidth = 1.2; for (let k = x + 12; k < x + W - 8; k += 8) { ctx.beginPath(); ctx.moveTo(k, y + 6); ctx.lineTo(k + (k - x - W / 2) * 0.08, faceTop + 4); ctx.stroke(); }
    box(ctx, x + 8, y, W - 16, 6, K.gold, OUT, 1.5, 2);
    for (const wx of opt.windows ?? []) { box(ctx, x + wx * T - 7, faceTop + 14, 14, 18, "#3a4a6a", OUT, 1.5, 6); ctx.fillStyle = "rgba(255,230,160,0.5)"; ctx.fillRect(x + wx * T - 5, faceTop + 18, 10, 12); }
    const dx = x + opt.door * T; box(ctx, dx - 13, faceTop + faceH - 38, 26, 34, "#4a3020", OUT, 2, 10); ctx.fillStyle = K.gold; ctx.fillRect(dx - 13, faceTop + faceH - 38, 26, 3);
    E.entrance(ctx, gx + opt.door - 0.5, gy + h);
    if (opt.sign) { box(ctx, dx + 18, faceTop + 6, 24, 22, "#2a3a6a", OUT, 2, 3); box(ctx, dx + 21, faceTop + 9, 18, 16, "#f2e6c8", null, 0, 2); E.ICON[opt.sign](ctx, dx + 30, faceTop + 17, 12); }
    if (opt.spire) { const cx = x + W / 2; ctx.beginPath(); ctx.moveTo(cx - 12, y + 6); ctx.lineTo(cx, y - 40); ctx.lineTo(cx + 12, y + 6); ctx.closePath(); ctx.fillStyle = "#c8bcff"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); glow(ctx, cx, y - 20, 26, "rgba(143,123,255,0.9)", 0.6); }
  }
  /** 中央傳送陣：通往五區的五個光圈＋中央晶柱（已開放的區有顏色，沒開放的是灰色）。 */
  function portalPlaza(ctx, gx, gy, open = ["cloud_ridge", "ashen_waste"]) {
    const cx = (gx + 1.5) * T, cy = (gy + 1.5) * T;
    ctx.save(); ctx.strokeStyle = rgba(K.gold, 0.9); ctx.lineWidth = 2.5; ctx.beginPath(); ctx.ellipse(cx, cy, 70, 46, 0, 0, TAU); ctx.stroke(); ctx.lineWidth = 1.2; ctx.beginPath(); ctx.ellipse(cx, cy, 58, 38, 0, 0, TAU); ctx.stroke(); ctx.restore();
    Object.keys(REGION_COL).forEach((id, k) => {
      const a = -Math.PI / 2 + k * TAU / 5, px = cx + Math.cos(a) * 64, py = cy + Math.sin(a) * 42, on = open.includes(id), col = on ? REGION_COL[id] : "#8a8a8a";
      if (on) glow(ctx, px, py, 20, col, 0.6);
      ctx.beginPath(); ctx.ellipse(px, py, 13, 8, 0, 0, TAU); ctx.fillStyle = on ? rgba(col, 0.35) : "rgba(60,60,60,0.35)"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = col; ctx.stroke();
    });
    shadow(ctx, cx + 4, cy + 16, 16, 5, 0.35);
    ctx.beginPath(); ctx.moveTo(cx - 9, cy + 14); ctx.lineTo(cx - 10, cy - 20); ctx.lineTo(cx, cy - 40); ctx.lineTo(cx + 10, cy - 20); ctx.lineTo(cx + 9, cy + 14); ctx.closePath(); ctx.fillStyle = "#c8bcff"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); glow(ctx, cx, cy - 16, 30, "rgba(143,123,255,0.9)", 0.55);
  }
  function banner(ctx, x, y, region) { // 區旗（主城的五面旗）
    box(ctx, x + T / 2 - 2, y + 4, 4, 44, "#6a5a4a", OUT, 1.2, 1); dot(ctx, x + T / 2, y + 4, 3, K.gold);
    ctx.beginPath(); ctx.moveTo(x + T / 2 + 2, y + 8); ctx.lineTo(x + T / 2 + 20, y + 8); ctx.lineTo(x + T / 2 + 20, y + 30); ctx.lineTo(x + T / 2 + 11, y + 25); ctx.lineTo(x + T / 2 + 2, y + 30); ctx.closePath(); ctx.fillStyle = REGION_COL[region]; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke();
  }
  function fountain(ctx, gx, gy) {
    const cx = (gx + 1) * T, cy = (gy + 1) * T; shadow(ctx, cx + 4, cy + 14, 40, 10, 0.3);
    ctx.beginPath(); ctx.ellipse(cx, cy, 40, 24, 0, 0, TAU); ctx.fillStyle = K.stoneD; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.beginPath(); ctx.ellipse(cx, cy, 33, 18, 0, 0, TAU); ctx.fillStyle = "#3f8ac8"; ctx.fill();
    box(ctx, cx - 5, cy - 26, 10, 26, K.stone, OUT, 1.6, 2); ctx.strokeStyle = "rgba(220,240,255,0.8)"; ctx.lineWidth = 1.5; for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(cx, cy - 26); ctx.quadraticCurveTo(cx + s * 16, cy - 32, cx + s * 22, cy - 4); ctx.stroke(); }
  }
  function stall(ctx, gx, gy, color) { const x = gx * T, y = gy * T; shadow(ctx, x + T / 2 + 3, y + T * 0.86, 22, 6); box(ctx, x + 6, y + 26, T - 12, 16, K.woodL, OUT, 1.8, 2); for (const [dx, c] of [[12, "#c83a2a"], [22, "#e8bb48"], [32, "#6aa84a"]]) dot(ctx, x + dx + 4, y + 24, 4, c); ctx.beginPath(); ctx.moveTo(x + 2, y + 18); ctx.lineTo(x + T - 2, y + 18); ctx.lineTo(x + T - 6, y + 6); ctx.lineTo(x + 6, y + 6); ctx.closePath(); ctx.fillStyle = color; ctx.fill(); ctx.lineWidth = 1.8; ctx.strokeStyle = OUT; ctx.stroke(); for (let k = 0; k < 4; k++) { ctx.fillStyle = "rgba(255,255,255,0.35)"; ctx.fillRect(x + 8 + k * 10, y + 7, 4, 11); } }

  // ============ 室內 ============
  /** 室內底：木地板＋後牆（2 列高）＋左右牆；畫在 (ox, oy) 起的 w×h 格。 */
  function room(ctx, ox, oy, w, h, wallCol = K.wall, floor = K.plank) {
    ctx.fillStyle = "#14100c"; ctx.fillRect(0, 0, 20 * T, 12 * T);
    for (let gy = 0; gy < h; gy++) for (let gx = 0; gx < w; gx++) { const x = (ox + gx) * T, y = (oy + gy) * T; ctx.fillStyle = shade(floor, 0.92 + ((gx * 7 + gy * 3) % 5) / 30); ctx.fillRect(x, y, T, T); ctx.strokeStyle = "rgba(0,0,0,0.25)"; ctx.lineWidth = 1; for (let k = 1; k < 4; k++) { ctx.beginPath(); ctx.moveTo(x, y + k * 13); ctx.lineTo(x + T, y + k * 13); ctx.stroke(); } }
    const x0 = ox * T, y0 = oy * T, W = w * T;
    ctx.fillStyle = wallCol; ctx.fillRect(x0, y0, W, 1.6 * T); ctx.fillStyle = "rgba(0,0,0,0.25)"; for (let k = 0; k < w * 2; k++) ctx.fillRect(x0 + k * T / 2, y0, 2, 1.6 * T);
    ctx.fillStyle = shade(wallCol, 0.7); ctx.fillRect(x0, y0 + 1.6 * T - 8, W, 8);
    ctx.fillStyle = shade(wallCol, 0.8); ctx.fillRect(x0 - 10, y0, 10, h * T); ctx.fillRect(x0 + W, y0, 10, h * T); ctx.fillRect(x0 - 10, y0 + h * T, W + 20, 8);
    ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.strokeRect(x0 - 10, y0, W + 20, h * T + 8);
    // 出口（門墊）：下牆中間
    const dx = x0 + W / 2; ctx.fillStyle = "#14100c"; ctx.fillRect(dx - T / 2, y0 + h * T, T, 8); E.entrance(ctx, ox + w / 2 - 0.5, oy + h - 1);
  }
  const P = {
    counter(ctx, gx, gy, w) { const x = gx * T, y = gy * T; shadow(ctx, x + w * T / 2, y + T * 0.9, w * T / 2, 6, 0.3); box(ctx, x + 2, y + 18, w * T - 4, 28, K.wood, OUT, 2, 2); box(ctx, x, y + 12, w * T, 9, K.woodL, OUT, 2, 2); },
    table(ctx, gx, gy) { const x = gx * T, y = gy * T, cx = x + T / 2; shadow(ctx, cx + 3, y + T * 0.8, 20, 6); ctx.beginPath(); ctx.ellipse(cx, y + 26, 18, 11, 0, 0, TAU); ctx.fillStyle = K.woodL; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); dot(ctx, cx - 6, y + 24, 3, "#c8a070"); dot(ctx, cx + 6, y + 27, 3, "#e8e0d0"); for (const s of [-1, 1]) { ctx.beginPath(); ctx.ellipse(cx + s * 22, y + 34, 6, 4, 0, 0, TAU); ctx.fillStyle = K.wood; ctx.fill(); ctx.stroke(); } },
    keg(ctx, gx, gy) { const x = gx * T, y = gy * T; for (const [dx, dy] of [[4, 16], [24, 16], [14, 2]]) { ctx.beginPath(); ctx.ellipse(x + dx + 10, y + dy + 12, 10, 12, 0, 0, TAU); ctx.fillStyle = "#8a5a30"; ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = OUT; ctx.stroke(); ctx.strokeStyle = "#3a3a3a"; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.ellipse(x + dx + 10, y + dy + 12, 10, 4, 0, 0, TAU); ctx.stroke(); } },
    fireplace(ctx, gx, gy) { const x = gx * T, y = gy * T; box(ctx, x + 4, y + 8, T * 2 - 8, T * 1.2, "#6a5e54", OUT, 2, 3); ctx.fillStyle = "#14100c"; ctx.beginPath(); ctx.arc(x + T, y + T * 1.2, 22, Math.PI, 0); ctx.fill(); glow(ctx, x + T, y + T, 40, "rgba(255,150,60,0.9)", 0.7); E.ICON.rest(ctx, x + T, y + T * 1.05, 22); },
    shelf(ctx, gx, gy, w = 2, items = ["#c83a2a", "#3a5ad0", "#6aa84a", "#e8bb48"]) { const x = gx * T, y = gy * T; box(ctx, x + 4, y + 4, w * T - 8, T * 1.3, K.wood, OUT, 2, 2); for (let r = 0; r < 3; r++) { ctx.fillStyle = shade(K.wood, 0.7); ctx.fillRect(x + 6, y + 18 + r * 20, w * T - 12, 3); for (let k = 0; k < w * 5; k++) { ctx.fillStyle = items[(k + r) % items.length]; ctx.fillRect(x + 8 + k * 9.5, y + 6 + r * 20, 6, 12); } } },
    anvil(ctx, gx, gy) { const x = gx * T, y = gy * T; shadow(ctx, x + T / 2 + 3, y + T * 0.8, 18, 5); E.ICON.anvil(ctx, x + T / 2, y + T / 2, 34); },
    rack(ctx, gx, gy) { const x = gx * T, y = gy * T; box(ctx, x + 6, y + 6, T - 12, 6, K.wood, OUT, 1.6, 1); box(ctx, x + 6, y + T * 0.8, T - 12, 6, K.wood, OUT, 1.6, 1); for (let k = 0; k < 3; k++) { ctx.strokeStyle = OUT; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x + 14 + k * 12, y + 10); ctx.lineTo(x + 14 + k * 12, y + T * 0.82); ctx.stroke(); ctx.strokeStyle = "#dfe4ea"; ctx.lineWidth = 1.6; ctx.stroke(); } },
    enchant(ctx, gx, gy, t = 0) { const x = gx * T, y = gy * T, cx = x + T / 2; shadow(ctx, cx + 3, y + T * 0.84, 20, 6); box(ctx, x + 8, y + 24, T - 16, 18, "#3a3450", OUT, 2, 3); ctx.save(); ctx.shadowColor = "#a898ff"; ctx.shadowBlur = 10; ctx.strokeStyle = "#c8bcff"; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.ellipse(cx, y + 18, 16, 6, 0, 0, TAU); ctx.stroke(); for (let k = 0; k < 5; k++) { const a = t / 600 + k * TAU / 5; dot(ctx, cx + Math.cos(a) * 16, y + 18 + Math.sin(a) * 6 - 6, 2, "#e0d8ff"); } ctx.restore(); dot(ctx, cx, y + 10, 5, "#c8bcff"); },
    statue(ctx, gx, gy) { const x = gx * T, y = gy * T, cx = x + T / 2; shadow(ctx, cx + 4, y + T * 1.85, 24, 6); box(ctx, cx - 18, y + T * 1.5, 36, 18, K.stoneD, OUT, 2, 2); ctx.beginPath(); ctx.moveTo(cx - 12, y + T * 1.5); ctx.lineTo(cx - 14, y + 16); ctx.lineTo(cx, y - 10); ctx.lineTo(cx + 14, y + 16); ctx.lineTo(cx + 12, y + T * 1.5); ctx.closePath(); ctx.fillStyle = "#c8bcff"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); glow(ctx, cx, y + 20, 40, "rgba(143,123,255,0.9)", 0.5); },
    rug(ctx, gx, gy, w, h) { const x = gx * T, y = gy * T; box(ctx, x + 6, y + 6, w * T - 12, h * T - 12, K.rug, OUT, 2, 3); ctx.strokeStyle = K.gold; ctx.lineWidth = 2; ctx.strokeRect(x + 14, y + 14, w * T - 28, h * T - 28); },
    candle(ctx, gx, gy) { const x = gx * T, y = gy * T; box(ctx, x + T / 2 - 3, y + 20, 6, 20, "#f2e6c8", OUT, 1.2, 1); glow(ctx, x + T / 2, y + 16, 14, "rgba(255,210,120,0.9)", 0.7); E.ICON.rest(ctx, x + T / 2, y + 17, 9); },
    board(ctx, gx, gy) { E.board(ctx, gx, gy); },
  };

  return { T, K, REGION_COL, plaza, stoneHall, portalPlaza, banner, fountain, stall, room, P };
})();
