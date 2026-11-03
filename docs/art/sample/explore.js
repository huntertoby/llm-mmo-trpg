// 可走動的城鎮／野外畫面樣張（美術 PM，2026-11-04）。只是示意，不是定案。
// 方向（使用者原話，專案 PM 轉達）：「不是這種點大地圖移動的 真實畫面地圖入口移動」——一張張畫面地圖靠路口互相銜接。
// 用戰鬥格子的同一套畫法（52 單位一格、光從左上、深色外框、紙娃娃），雲嶺配色。全部程式繪製，沒有下載素材。
// 依賴：paperdoll.js（PaperDoll）、realms.js（Realms.OBJ、雲嶺地板）、enemyArt.js（EnemyArt）。
window.Explore = (() => {
  const T = 52;
  const TAU = Math.PI * 2;
  const OUT = "#1c1712";
  const C = {
    slate: "#7d8c84", ink: "#56645c", moss: "#5a8a3a", bamboo: "#6aa84a", red: "#b8432f", redDark: "#8a2f20",
    tile: "#3c4a48", mist: "#e8e8e0", lamp: "#ffcf6a", path: "#b89a62", grass: "#689a70", water: "#3f7aa8", wood: "#8a6440",
  };
  function rng(seed) { let s = seed >>> 0 || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return (s % 100000) / 100000; }; }
  const R = (gx, gy, k) => rng((gx * 73856093) ^ (gy * 19349663) ^ (k * 83492791));
  function hexRgb(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  const rgba = (h, a) => { const [r, g, b] = hexRgb(h); return `rgba(${r},${g},${b},${a})`; };
  function shade(h, f) { const c = (v) => Math.max(0, Math.min(255, Math.round(v))); const [r, g, b] = hexRgb(h); return `rgb(${c(r * f)},${c(g * f)},${c(b * f)})`; }
  function rr(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  function box(ctx, x, y, w, h, fill, stroke = OUT, lw = 2, r = 2) { rr(ctx, x, y, w, h, r); ctx.fillStyle = fill; ctx.fill(); if (stroke) { ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.stroke(); } }
  function dot(ctx, x, y, r, fill) { ctx.fillStyle = fill; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); }
  function shadow(ctx, cx, cy, rx, ry, a = 0.3) { ctx.fillStyle = `rgba(0,0,0,${a})`; ctx.beginPath(); ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU); ctx.fill(); }

  // ---------------- 地面 ----------------
  function ground(ctx, kind, gx, gy) {
    const x = gx * T, y = gy * T, r = R(gx, gy, 3);
    if (kind === "s") return Realms.REALMS[1].floor(ctx, x, y, gx, gy); // 雲嶺青石板（同戰鬥）
    if (kind === "w" || kind === "W") { // 河水（W＝深水，不能走）
      ctx.fillStyle = kind === "W" ? shade(C.water, 0.78) : C.water; ctx.fillRect(x, y, T, T);
      ctx.strokeStyle = "rgba(255,255,255,0.4)"; ctx.lineWidth = 1.5;
      for (let i = 0; i < 2; i++) { const wy = y + 12 + i * 22 + r() * 6, wx = x + r() * 18; ctx.beginPath(); ctx.moveTo(wx, wy); ctx.quadraticCurveTo(wx + 10, wy - 5, wx + 20, wy); ctx.stroke(); }
      return;
    }
    if (kind === "p") { // 黃土路
      ctx.fillStyle = shade(C.path, 0.95 + r() * 0.1); ctx.fillRect(x, y, T, T);
      for (let i = 0; i < 8; i++) { ctx.fillStyle = r() < 0.5 ? "rgba(90,70,40,0.4)" : "rgba(255,240,210,0.35)"; ctx.fillRect(x + r() * T, y + r() * T, 2, 2); }
      return;
    }
    if (kind === "t") { // 石階（一階一階，往上變亮）
      ctx.fillStyle = C.ink; ctx.fillRect(x, y, T, T);
      for (let k = 0; k < 3; k++) { box(ctx, x + 1, y + 2 + k * 17, T - 2, 14, shade(C.slate, 0.92 + k * 0.06), null, 0, 2); ctx.fillStyle = "rgba(0,0,0,0.35)"; ctx.fillRect(x + 1, y + 15 + k * 17, T - 2, 3); }
      if (r() < 0.4) dot(ctx, x + r() * T, y + r() * T, 3, rgba(C.moss, 0.7));
      return;
    }
    // 草地（預設）
    ctx.fillStyle = shade(C.grass, 0.95 + r() * 0.1); ctx.fillRect(x, y, T, T);
    ctx.lineWidth = 1.5; ctx.lineCap = "round";
    for (let i = 0; i < 6; i++) { const gx2 = x + 5 + r() * (T - 10), gy2 = y + 8 + r() * (T - 13); ctx.strokeStyle = r() < 0.55 ? "#9ccf86" : "#4f8a3a"; ctx.beginPath(); ctx.moveTo(gx2, gy2); ctx.quadraticCurveTo(gx2 - 1, gy2 - 5, gx2 - 4, gy2 - 8); ctx.moveTo(gx2, gy2); ctx.quadraticCurveTo(gx2 + 1, gy2 - 5, gx2 + 4, gy2 - 9); ctx.stroke(); }
  }
  function drawGround(ctx, rows) { rows.forEach((row, gy) => [...row].forEach((ch, gx) => ground(ctx, ch, gx, gy))); }

  // ---------------- 建築（白牆黛瓦，3/4 視角；gx, gy 為屋子左上格，w 格寬、h 格深）----------------
  function house(ctx, gx, gy, w, h, opt) {
    const x = gx * T, y = gy * T, W = w * T;
    const faceTop = y + (h - 1.3) * T, faceH = 1.3 * T;
    shadow(ctx, x + W / 2 + 10, y + h * T - 2, W / 2 + 6, 10, 0.35);
    box(ctx, x + 4, faceTop, W - 8, faceH - 4, C.mist, "#1f2a28", 2, 2); // 白牆立面
    ctx.fillStyle = "rgba(0,0,0,0.08)"; ctx.fillRect(x + 6, faceTop + faceH - 18, W - 12, 12);
    box(ctx, x + 4, faceTop + faceH - 10, W - 8, 6, C.ink, "#1f2a28", 1.5, 1); // 牆基
    // 屋頂：深色瓦，前簷翹起
    ctx.beginPath(); ctx.moveTo(x - 6, faceTop + 6); ctx.lineTo(x + 6, y + 4); ctx.lineTo(x + W - 6, y + 4); ctx.lineTo(x + W + 6, faceTop + 6); ctx.quadraticCurveTo(x + W / 2, faceTop - 2, x - 6, faceTop + 6); ctx.closePath();
    ctx.fillStyle = C.tile; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = "#141c1a"; ctx.stroke();
    ctx.strokeStyle = "rgba(255,255,255,0.12)"; ctx.lineWidth = 1.2;
    for (let k = x + 10; k < x + W - 6; k += 7) { ctx.beginPath(); ctx.moveTo(k, y + 6); ctx.lineTo(k + (k - x - W / 2) * 0.08, faceTop + 2); ctx.stroke(); }
    box(ctx, x + 4, y + 2, W - 8, 5, "#2a3634", "#141c1a", 1.5, 2); // 屋脊
    if (opt.accent) { ctx.fillStyle = opt.accent; ctx.fillRect(x + 6, faceTop + 4, W - 12, 3); }
    // 窗
    for (const wx of opt.windows ?? []) { box(ctx, x + wx * T - 9, faceTop + 18, 18, 14, "#3a2a1e", "#1f2a28", 1.5, 1); ctx.strokeStyle = "#8a6a44"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x + wx * T, faceTop + 18); ctx.lineTo(x + wx * T, faceTop + 32); ctx.stroke(); if (opt.lit) { ctx.fillStyle = rgba(C.lamp, 0.55); ctx.fillRect(x + wx * T - 7, faceTop + 20, 14, 10); } }
    // 門：門口就是入口（走進去換畫面）
    const dx = x + opt.door * T;
    box(ctx, dx - 12, faceTop + faceH - 36, 24, 30, "#4a3020", "#1f2a28", 2, 2);
    ctx.fillStyle = C.red; ctx.fillRect(dx - 12, faceTop + faceH - 36, 24, 4);
    ctx.fillStyle = "rgba(255,207,106,0.35)"; ctx.fillRect(dx - 2, faceTop + faceH - 30, 4, 22);
    // 門前的入口格：淡淡的光圈（走上去就進門）
    entrance(ctx, opt.door + gx - 0.5, gy + h);
    // 招牌：只放圖示，不放字
    if (opt.sign) sign(ctx, dx + 20, faceTop + 6, opt.sign);
    for (const lx of opt.lanterns ?? []) lantern(ctx, x + lx * T, faceTop + 2);
  }
  function entrance(ctx, gx, gy) {
    const cx = gx * T + T / 2, cy = gy * T + T * 0.45;
    ctx.save(); ctx.globalAlpha = 0.85;
    const g = ctx.createRadialGradient(cx, cy, 2, cx, cy, 22); g.addColorStop(0, "rgba(255,230,160,0.55)"); g.addColorStop(1, "rgba(255,230,160,0)");
    ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(cx, cy, 22, 13, 0, 0, TAU); ctx.fill();
    ctx.strokeStyle = "rgba(255,230,160,0.9)"; ctx.lineWidth = 1.5; ctx.setLineDash([4, 3]); ctx.beginPath(); ctx.ellipse(cx, cy, 16, 9, 0, 0, TAU); ctx.stroke();
    ctx.restore();
  }
  function lantern(ctx, x, y) {
    ctx.save(); ctx.shadowColor = C.lamp; ctx.shadowBlur = 10; box(ctx, x - 5, y, 10, 13, C.red, OUT, 1.5, 4); ctx.restore();
    ctx.fillStyle = C.lamp; ctx.fillRect(x - 2, y + 3, 4, 7);
  }
  // ---------------- 圖示（招牌、泡泡共用）----------------
  const ICON = {
    coin(ctx, x, y, s) { dot(ctx, x, y + s * 0.1, s * 0.55, "#e8bb48"); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.beginPath(); ctx.arc(x, y + s * 0.1, s * 0.55, 0, TAU); ctx.stroke(); ctx.fillStyle = OUT; ctx.fillRect(x - s * 0.15, y - s * 0.12, s * 0.3, s * 0.45); },
    anvil(ctx, x, y, s) { ctx.fillStyle = "#5a5e64"; ctx.beginPath(); ctx.moveTo(x - s * 0.7, y - s * 0.3); ctx.lineTo(x + s * 0.6, y - s * 0.3); ctx.lineTo(x + s * 0.3, y); ctx.lineTo(x + s * 0.2, y + s * 0.1); ctx.lineTo(x + s * 0.4, y + s * 0.5); ctx.lineTo(x - s * 0.4, y + s * 0.5); ctx.lineTo(x - s * 0.2, y + s * 0.1); ctx.lineTo(x - s * 0.3, y - s * 0.05); ctx.closePath(); ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke(); },
    jar(ctx, x, y, s) { ctx.fillStyle = "#8a5a30"; ctx.beginPath(); ctx.ellipse(x, y + s * 0.15, s * 0.45, s * 0.45, 0, 0, TAU); ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke(); ctx.fillStyle = C.red; ctx.fillRect(x - s * 0.25, y - s * 0.5, s * 0.5, s * 0.25); ctx.strokeRect(x - s * 0.25, y - s * 0.5, s * 0.5, s * 0.25); },
    scroll(ctx, x, y, s) { box(ctx, x - s * 0.5, y - s * 0.4, s, s * 0.8, "#f2e6c8", OUT, 1.5, 1); ctx.fillStyle = C.redDark; ctx.fillRect(x - s * 0.6, y - s * 0.5, s * 1.2, s * 0.15); ctx.fillRect(x - s * 0.6, y + s * 0.35, s * 1.2, s * 0.15); ctx.strokeStyle = "#8a7a5a"; ctx.lineWidth = 1; for (let k = -0.15; k < 0.3; k += 0.15) { ctx.beginPath(); ctx.moveTo(x - s * 0.3, y + s * k); ctx.lineTo(x + s * 0.3, y + s * k); ctx.stroke(); } },
    sword(ctx, x, y, s) { ctx.strokeStyle = OUT; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(x - s * 0.5, y + s * 0.5); ctx.lineTo(x + s * 0.5, y - s * 0.5); ctx.stroke(); ctx.strokeStyle = "#dfe4ea"; ctx.lineWidth = 2; ctx.stroke(); ctx.strokeStyle = "#e8bb48"; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(x - s * 0.45, y + s * 0.1); ctx.lineTo(x - s * 0.1, y + s * 0.45); ctx.stroke(); },
    bang(ctx, x, y, s) { ctx.fillStyle = OUT; ctx.fillRect(x - s * 0.12, y - s * 0.5, s * 0.24, s * 0.65); ctx.fillRect(x - s * 0.12, y + s * 0.3, s * 0.24, s * 0.22); },
    ask(ctx, x, y, s) { ctx.strokeStyle = OUT; ctx.lineWidth = s * 0.22; ctx.lineCap = "round"; ctx.beginPath(); ctx.arc(x, y - s * 0.18, s * 0.28, Math.PI * 1.05, Math.PI * 0.45); ctx.lineTo(x, y + s * 0.18); ctx.stroke(); dot(ctx, x, y + s * 0.45, s * 0.12, OUT); },
    dots(ctx, x, y, s) { for (const k of [-0.35, 0, 0.35]) dot(ctx, x + s * k, y + s * 0.05, s * 0.11, OUT); },
    boat(ctx, x, y, s) { ctx.fillStyle = C.wood; ctx.beginPath(); ctx.moveTo(x - s * 0.6, y); ctx.lineTo(x + s * 0.6, y); ctx.lineTo(x + s * 0.4, y + s * 0.35); ctx.lineTo(x - s * 0.4, y + s * 0.35); ctx.closePath(); ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke(); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - s * 0.6); ctx.lineTo(x + s * 0.4, y - s * 0.1); ctx.closePath(); ctx.fillStyle = C.mist; ctx.fill(); ctx.stroke(); },
    portal(ctx, x, y, s) { ctx.save(); ctx.shadowColor = "#8fe0ff"; ctx.shadowBlur = 6; ctx.strokeStyle = "#5ac8f0"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y, s * 0.45, 0, TAU); ctx.stroke(); ctx.beginPath(); ctx.arc(x, y, s * 0.2, 0, TAU); ctx.stroke(); ctx.restore(); },
    rest(ctx, x, y, s) { ctx.fillStyle = "#ff8a2a"; ctx.beginPath(); ctx.moveTo(x, y - s * 0.55); ctx.quadraticCurveTo(x + s * 0.45, y, x, y + s * 0.4); ctx.quadraticCurveTo(x - s * 0.45, y, x, y - s * 0.55); ctx.fill(); ctx.fillStyle = "#ffd23a"; ctx.beginPath(); ctx.ellipse(x, y + s * 0.12, s * 0.15, s * 0.25, 0, 0, TAU); ctx.fill(); },
  };
  function sign(ctx, x, y, icon) {
    ctx.strokeStyle = OUT; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(x - 10, y); ctx.lineTo(x + 10, y); ctx.stroke();
    box(ctx, x - 12, y + 2, 24, 22, "#5a3a24", OUT, 2, 3);
    box(ctx, x - 9, y + 5, 18, 16, "#f2e6c8", null, 0, 2);
    ICON[icon](ctx, x, y + 13, 13);
  }
  /** 對話泡泡（只放圖示）。kind：quest＝黃底（有任務）、talk＝白底（可聊）、shop＝白底金幣、danger＝紅底。 */
  function bubble(ctx, x, y, icon, kind = "talk") {
    const fill = { quest: "#ffd23a", talk: "#ffffff", danger: "#ff6a5a", info: "#bfe8ff" }[kind];
    ctx.save(); ctx.shadowColor = "rgba(0,0,0,0.35)"; ctx.shadowOffsetY = 2; ctx.shadowBlur = 3;
    rr(ctx, x - 13, y - 26, 26, 22, 8); ctx.fillStyle = fill; ctx.fill(); ctx.restore();
    ctx.beginPath(); ctx.moveTo(x - 4, y - 5); ctx.lineTo(x, y + 2); ctx.lineTo(x + 4, y - 5); ctx.fillStyle = fill; ctx.fill();
    rr(ctx, x - 13, y - 26, 26, 22, 8); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.fillStyle = fill; ctx.fillRect(x - 3, y - 6, 6, 3);
    ICON[icon](ctx, x, y - 15, 13);
  }
  // ---------------- 物件 ----------------
  function board(ctx, gx, gy) { // 懸賞板
    const x = gx * T, y = gy * T;
    shadow(ctx, x + T / 2 + 3, y + T * 0.85, 20, 5);
    box(ctx, x + 10, y + 22, 4, 26, C.wood, OUT, 1.5, 1); box(ctx, x + T - 14, y + 22, 4, 26, C.wood, OUT, 1.5, 1);
    box(ctx, x + 4, y + 6, T - 8, 26, "#a07848", OUT, 2, 2);
    for (const [px, py, c] of [[10, 10, "#f2e6c8"], [24, 12, "#f2e6c8"], [36, 9, "#ffd8a0"], [16, 20, "#f2e6c8"], [30, 21, "#f2e6c8"]]) { box(ctx, x + px, y + py, 9, 9, c, "#6a5030", 1, 1); dot(ctx, x + px + 4.5, y + py + 1.5, 1.2, C.red); }
    box(ctx, x + 2, y + 3, T - 4, 5, C.tile, OUT, 1.5, 1);
  }
  function waypoint(ctx, gx, gy) { // 傳送點：石碑＋藍光圈
    const x = gx * T, y = gy * T, cx = x + T / 2;
    ctx.save(); ctx.shadowColor = "#8fe0ff"; ctx.shadowBlur = 10; ctx.strokeStyle = "rgba(120,210,255,0.85)"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.ellipse(cx, y + T * 0.75, 24, 10, 0, 0, TAU); ctx.stroke(); ctx.restore();
    box(ctx, cx - 8, y + 6, 16, 36, "#9aa39c", OUT, 2, 4);
    ctx.save(); ctx.shadowColor = "#8fe0ff"; ctx.shadowBlur = 8; ctx.strokeStyle = "#5ac8f0"; ctx.lineWidth = 1.8; ctx.beginPath(); ctx.arc(cx, y + 20, 4, 0, TAU); ctx.moveTo(cx, y + 26); ctx.lineTo(cx, y + 36); ctx.stroke(); ctx.restore();
  }
  function dock(ctx, gx, gy, w, h) { // 碼頭棧板
    const x = gx * T, y = gy * T;
    ctx.fillStyle = "rgba(0,0,0,0.3)"; ctx.fillRect(x + 4, y + 4, w * T, h * T);
    for (let k = 0; k < h * T; k += 9) box(ctx, x, y + k, w * T, 7.5, shade("#9a7a50", 0.92 + ((k * 7) % 10) / 60), OUT, 1.2, 1);
    for (const [px, py] of [[0, 0], [w * T - 6, 0], [0, h * T - 6], [w * T - 6, h * T - 6]]) box(ctx, x + px - 1, y + py - 1, 8, 8, "#5a4030", OUT, 1.2, 1);
  }
  function boat(ctx, gx, gy) {
    const x = gx * T, y = gy * T;
    shadow(ctx, x + T, y + T * 0.75, T * 0.95, 8, 0.25);
    ctx.beginPath(); ctx.moveTo(x + 4, y + 16); ctx.quadraticCurveTo(x + T, y + 6, x + 2 * T - 4, y + 16); ctx.lineTo(x + 2 * T - 14, y + 40); ctx.quadraticCurveTo(x + T, y + 46, x + 14, y + 40); ctx.closePath();
    ctx.fillStyle = C.wood; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.fillStyle = "#6a4a30"; ctx.beginPath(); ctx.ellipse(x + T, y + 25, T * 0.7, 9, 0, 0, TAU); ctx.fill();
    box(ctx, x + T - 14, y + 14, 28, 18, "#3c4a48", OUT, 1.5, 3); // 篷
  }
  function campfire(ctx, gx, gy) {
    const x = gx * T, y = gy * T, cx = x + T / 2, cy = y + T * 0.6;
    const g = ctx.createRadialGradient(cx, cy, 3, cx, cy, 46); g.addColorStop(0, "rgba(255,190,90,0.45)"); g.addColorStop(1, "rgba(255,190,90,0)");
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, 46, 0, TAU); ctx.fill();
    for (let k = 0; k < 7; k++) { const a = (k / 7) * TAU; box(ctx, cx + Math.cos(a) * 13 - 4, cy + Math.sin(a) * 7 - 3, 8, 6, "#8a8a84", OUT, 1.2, 3); }
    ctx.strokeStyle = "#5a3a20"; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(cx - 9, cy + 3); ctx.lineTo(cx + 9, cy - 3); ctx.moveTo(cx - 9, cy - 3); ctx.lineTo(cx + 9, cy + 3); ctx.stroke();
    ctx.save(); ctx.shadowColor = "#ff8a2a"; ctx.shadowBlur = 12; ICON.rest(ctx, cx, cy - 8, 22); ctx.restore();
  }
  function chest(ctx, gx, gy) {
    const x = gx * T, y = gy * T, cx = x + T / 2;
    shadow(ctx, cx + 3, y + T * 0.78, 16, 5);
    box(ctx, cx - 14, y + 22, 28, 18, "#8a5a30", OUT, 2, 2);
    ctx.beginPath(); ctx.moveTo(cx - 14, y + 24); ctx.quadraticCurveTo(cx, y + 8, cx + 14, y + 24); ctx.closePath(); ctx.fillStyle = "#a06a38"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.fillStyle = "#e8bb48"; ctx.fillRect(cx - 15, y + 22, 30, 3); box(ctx, cx - 3, y + 24, 6, 7, "#e8bb48", OUT, 1.2, 1);
    ctx.save(); ctx.globalAlpha = 0.9; for (const [sx, sy] of [[-16, 8], [15, 12], [4, 2]]) { ctx.fillStyle = "#fff4c0"; ctx.beginPath(); ctx.moveTo(cx + sx, y + sy - 4); ctx.lineTo(cx + sx + 1.2, y + sy - 1.2); ctx.lineTo(cx + sx + 4, y + sy); ctx.lineTo(cx + sx + 1.2, y + sy + 1.2); ctx.lineTo(cx + sx, y + sy + 4); ctx.lineTo(cx + sx - 1.2, y + sy + 1.2); ctx.lineTo(cx + sx - 4, y + sy); ctx.lineTo(cx + sx - 1.2, y + sy - 1.2); ctx.fill(); } ctx.restore();
  }
  function stele(ctx, gx, gy) { // 事件：古碑（? 標記）
    const x = gx * T, y = gy * T, cx = x + T / 2;
    shadow(ctx, cx + 4, y + T * 0.85, 16, 5);
    box(ctx, cx - 10, y + 10, 20, 34, "#8a948c", OUT, 2, 6);
    ctx.fillStyle = rgba(C.moss, 0.8); ctx.beginPath(); ctx.arc(cx - 6, y + 40, 5, 0, TAU); ctx.fill();
    ctx.strokeStyle = "#4a524c"; ctx.lineWidth = 1.2; for (const k of [18, 24, 30]) { ctx.beginPath(); ctx.moveTo(cx - 5, y + k); ctx.lineTo(cx + 5, y + k); ctx.stroke(); }
  }
  // ---------------- 人物 ----------------
  const SKIN = ["#f1c9a5", "#d9a47a", "#a8724c"];
  const PARTY = [
    [{ skin: SKIN[0], hair: "short", hairColor: "#3a2414" }, { body: { kind: "leather", material: "leather", color: "#2f5a5a" }, main_hand: { kind: "sword", material: "steel" }, feet: { kind: "boots", material: "leather" }, cloak: { kind: "cape", color: "#3a5ad0" } }],
    [{ skin: SKIN[1], hair: "long", hairColor: "#1a1a1a" }, { body: { kind: "robe", color: "#5a3a9a" }, main_hand: { kind: "staff", material: "wood", element: "ice" } }],
  ];
  function ring(ctx, cx, cy, color) {
    ctx.save(); ctx.beginPath(); ctx.ellipse(cx, cy, T * 0.32, T * 0.11, 0, 0, TAU);
    ctx.fillStyle = rgba(color, 0.3); ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = color; ctx.stroke(); ctx.restore();
  }
  function person(ctx, gx, gy, look, gear, facing = "south", ringColor = null) {
    const cx = gx * T + T / 2, foot = gy * T + T * 0.82;
    if (ringColor) ring(ctx, cx, foot, ringColor); else shadow(ctx, cx, foot, T * 0.24, T * 0.08, 0.3);
    PaperDoll.stamp(ctx, { look, gear }, facing, cx, foot, 0.78, { dpr: 3 });
    return { cx, top: foot - 50 };
  }
  function npc(ctx, gx, gy, look, gear, icon, kind, facing = "south") {
    const p = person(ctx, gx, gy, look, gear, facing);
    if (icon) bubble(ctx, p.cx, p.top - 2, icon, kind);
  }
  // ---------------- 路口（畫面邊緣的出口）----------------
  /** side：w/e/n/s；at：沿邊的格子範圍 [起, 迄]；icon：目的地圖示；label 只放地名（最少的字）。 */
  function exit(ctx, side, a, b, label, icon, cols, rows) {
    const horiz = side === "n" || side === "s";
    const x0 = horiz ? a * T : side === "w" ? 0 : (cols - 1) * T;
    const y0 = horiz ? (side === "n" ? 0 : (rows - 1) * T) : a * T;
    const w = horiz ? (b - a + 1) * T : T, h = horiz ? T : (b - a + 1) * T;
    const g = side === "w" ? ctx.createLinearGradient(x0, 0, x0 + T, 0) : side === "e" ? ctx.createLinearGradient(x0 + T, 0, x0, 0) : side === "n" ? ctx.createLinearGradient(0, y0, 0, y0 + T) : ctx.createLinearGradient(0, y0 + T, 0, y0);
    g.addColorStop(0, "rgba(255,240,190,0.55)"); g.addColorStop(1, "rgba(255,240,190,0)");
    ctx.fillStyle = g; ctx.fillRect(x0, y0, w, h);
    // 箭頭
    const cx = x0 + w / 2, cy = y0 + h / 2;
    const dir = { w: [-1, 0], e: [1, 0], n: [0, -1], s: [0, 1] }[side];
    const ax = cx + dir[0] * T * 0.18, ay = cy + dir[1] * T * 0.18;
    ctx.save(); ctx.translate(ax, ay); ctx.rotate(Math.atan2(dir[1], dir[0]));
    ctx.beginPath(); ctx.moveTo(14, 0); ctx.lineTo(-4, -12); ctx.lineTo(-4, -5); ctx.lineTo(-14, -5); ctx.lineTo(-14, 5); ctx.lineTo(-4, 5); ctx.lineTo(-4, 12); ctx.closePath();
    ctx.fillStyle = "#fff4d0"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); ctx.restore();
    // 地名牌：木牌＋圖示＋地名
    ctx.font = "bold 13px 'Microsoft JhengHei', sans-serif";
    const tw = ctx.measureText(label).width + 30;
    let lx = cx - tw / 2, ly = cy - dir[1] * 30 - 11 - (horiz ? 0 : 34);
    lx = Math.max(4, Math.min(cols * T - tw - 4, lx - dir[0] * 34)); ly = Math.max(4, Math.min(rows * T - 26, ly));
    box(ctx, lx, ly, tw, 22, "#5a3a24", OUT, 2, 4);
    ICON[icon](ctx, lx + 12, ly + 11, 12);
    ctx.fillStyle = "#fff4d0"; ctx.textBaseline = "middle"; ctx.fillText(label, lx + 22, ly + 12);
  }
  // ---------------- 介面（盡量少字）----------------
  function hud(ctx, cols, rows, place, icon) {
    const W = cols * T, H = rows * T;
    ctx.font = "bold 15px 'Microsoft JhengHei', sans-serif";
    const tw = ctx.measureText(place).width + 44;
    box(ctx, 10, 10, tw, 30, "rgba(28,23,18,0.82)", "#c8a868", 1.5, 6);
    ICON[icon](ctx, 26, 25, 14);
    ctx.fillStyle = "#f2e6c8"; ctx.textBaseline = "middle"; ctx.fillText(place, 40, 26);
    // 隊伍頭像（左下）
    PARTY.forEach(([look, gear], i) => {
      const x = 16 + i * 64, y = H - 70;
      box(ctx, x, y, 56, 56, "rgba(28,23,18,0.85)", "#c8a868", 1.5, 8);
      ctx.save(); rr(ctx, x + 2, y + 2, 52, 40, 6); ctx.clip(); PaperDoll.stamp(ctx, { look, gear }, "south", x + 28, y + 76, 1.25, { dpr: 3 }); ctx.restore();
      box(ctx, x + 5, y + 44, 46, 7, "#2a1a14", null, 0, 2); box(ctx, x + 5, y + 44, 46 * (i ? 0.7 : 0.95), 7, "#5ad06a", null, 0, 2);
    });
    // 互動鍵提示（右下）：圖示＋按鍵，不寫說明句
    const keys = [["E", "dots"], ["M", "scroll"], ["I", "jar"]];
    keys.forEach(([k, ic], i) => {
      const x = W - 58 * (keys.length - i) - 6, y = H - 56;
      box(ctx, x, y, 50, 44, "rgba(28,23,18,0.82)", "#c8a868", 1.5, 6);
      ICON[ic](ctx, x + 32, y + 22, 14);
      box(ctx, x + 5, y + 12, 16, 18, "#f2e6c8", OUT, 1.5, 3);
      ctx.fillStyle = OUT; ctx.font = "bold 12px Consolas, monospace"; ctx.textBaseline = "middle"; ctx.fillText(k, x + 9.5, y + 22);
    });
  }
  /** 互動提示：玩家站在 NPC／門口旁邊時，頭上浮出按鍵＋圖示。 */
  function prompt(ctx, cx, cy, key, icon) {
    box(ctx, cx - 26, cy - 14, 52, 26, "rgba(28,23,18,0.88)", "#ffd23a", 2, 8);
    box(ctx, cx - 21, cy - 9, 16, 16, "#ffd23a", OUT, 1.5, 3);
    ctx.fillStyle = OUT; ctx.font = "bold 12px Consolas, monospace"; ctx.textBaseline = "middle"; ctx.fillText(key, cx - 16.5, cy);
    ICON[icon](ctx, cx + 11, cy - 1, 14);
  }

  // ======================= 畫面 1：霧渡鎮（主城）=======================
  function town(ctx, hudFn = hud) {
    const cols = 20, rows = 12;
    drawGround(ctx, [
      "gggggggppgggggggggggg",
      "gggggggppggggggggggg",
      "gggggggppggggggggggg",
      "gggggggppggggggggggg",
      "ggppppppppppppppppgg",
      "ggpsssssssssssssspppp",
      "ggpsssssssssssssspppp",
      "ggpsssssssssssssspgg",
      "ggppppppppppppppppgg",
      "gggggggggpppgggggggg",
      "wwwwwwwwwppwwwwwwwww",
      "WWWWWWWWWppWWWWWWWWW",
    ]);
    // 竹林邊（北、西）
    for (const [gx, gy] of [[0, 0], [1, 0], [0, 1], [0, 2], [18, 0], [19, 0], [19, 1], [0, 9], [1, 9], [17, 9], [18, 9], [19, 9]]) Realms.OBJ.bamboo(ctx, gx * T, gy * T);
    // 建築：商鋪、鐵匠、酒館、導師
    house(ctx, 2, 1, 4, 3, { door: 2, sign: "coin", windows: [1, 3], lanterns: [0.5, 3.5] });
    house(ctx, 10, 1, 3, 3, { door: 1.5, sign: "anvil", windows: [0.6] });
    house(ctx, 13, 1, 5, 3, { door: 2.5, sign: "jar", windows: [1, 4], lit: true, lanterns: [1.5, 3.5], accent: C.red });
    // 廣場：懸賞板、傳送點、石燈籠
    board(ctx, 6, 5); waypoint(ctx, 13, 5);
    Realms.OBJ.stoneLantern(ctx, 3 * T, 5 * T); Realms.OBJ.stoneLantern(ctx, 16 * T, 5 * T);
    // 南邊渡口：碼頭＋渡船（往灰燼荒原的渡口）
    dock(ctx, 9, 10, 2, 2); boat(ctx, 11, 10);
    // NPC（只用泡泡圖示）
    npc(ctx, 5, 4, { skin: SKIN[0], hair: "short", hairColor: "#1a1a1a" }, { body: { kind: "robe", color: "#8a6a3a" }, head: { kind: "cap", color: "#3a2a1a" } }, "coin", "talk");
    npc(ctx, 12, 4, { skin: SKIN[2], hair: "short", hairColor: "#2a1a10" }, { body: { kind: "leather", material: "leather", color: "#4a3a2a" }, main_hand: { kind: "hammer", material: "iron" } }, "anvil", "talk");
    npc(ctx, 7, 6, { skin: SKIN[1], hair: "long", hairColor: "#3a3a3a" }, { body: { kind: "robe", color: "#2f5a5a" }, head: { kind: "wide_hat", material: "wood", color: "#c8a868" }, main_hand: { kind: "sword", material: "steel" } }, "bang", "quest");
    npc(ctx, 17, 4, { skin: SKIN[0], hair: "long", hairColor: "#6a3d1e" }, { body: { kind: "robe", color: C.red } }, "dots", "talk");
    npc(ctx, 10, 9, { skin: SKIN[1], hair: "short", hairColor: "#1a1a1a" }, { body: { kind: "coat", color: "#3c4a48" }, head: { kind: "wide_hat", material: "wood", color: "#c8a868" } }, "boat", "info");
    // 玩家與隊友（藍環）：站在懸賞板旁，浮出互動提示
    person(ctx, 8, 6, ...PARTY[0], "west", "#5aa0ff");
    person(ctx, 9, 7, ...PARTY[1], "west", "#5aa0ff");
    prompt(ctx, 8 * T + T / 2, 6 * T - 22, "E", "scroll");
    // 出口
    exit(ctx, "e", 5, 6, "渡口石階", "sword", cols, rows);
    exit(ctx, "n", 7, 8, "獵戶小屋", "dots", cols, rows);
    hudFn(ctx, cols, rows, "霧渡鎮", "portal", { scene: "town" });
  }

  // ======================= 畫面 2：渡口石階（雲嶺野外）=======================
  function field(ctx, hudFn = hud) {
    const cols = 20, rows = 12;
    drawGround(ctx, [
      "gggggggggggggggppggg",
      "gggggggggggggggppggg",
      "ggggggggggggggtttggg",
      "gggggggggggggttgggggg",
      "pppppgggggttttgggggg",
      "ppppppppttttgggggggg",
      "gggggppptgggggggggggg",
      "gggggggggggggggggggg",
      "gggggggggggggggggggg",
      "wwwwwwwwwwwwwwwwwwww",
      "WWWWWWWWWWWWWWWWWWWW",
      "WWWWWWWWWWWWWWWWWWWW",
    ]);
    for (const [gx, gy] of [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [0, 2], [12, 0], [13, 0], [11, 1], [19, 2], [19, 3], [18, 4], [3, 7], [4, 7]]) Realms.OBJ.bamboo(ctx, gx * T, gy * T);
    Realms.OBJ.stoneLantern(ctx, 9 * T, 4 * T); Realms.OBJ.stoneLantern(ctx, 12 * T, 2 * T);
    // 小碼頭和被搶的渡船（新手任務 1：盜賊搶渡船）
    dock(ctx, 13, 8, 3, 1); boat(ctx, 14, 9);
    // 營火（休息點）、寶箱、事件古碑
    campfire(ctx, 6, 7);
    chest(ctx, 2, 3);
    stele(ctx, 10, 6);
    bubble(ctx, 10 * T + T / 2, 6 * T + 6, "ask", "info");
    // 看得見的敵群：盜賊兩人＋霧狼；紅環＋頭上一個危險泡泡（碰到就開戰）
    const bandit = [{ skin: SKIN[2], hair: "short", hairColor: "#1a1a1a" }, { body: { kind: "leather", material: "leather", color: "#7a6a4a" }, head: { kind: "wide_hat", material: "wood", color: "#a08a5a" }, main_hand: { kind: "axe", material: "iron" } }];
    const archer = [{ skin: SKIN[1], hair: "short", hairColor: "#2a1a10" }, { body: { kind: "leather", material: "leather", color: "#6a5a3a" }, main_hand: { kind: "bow", material: "wood" } }];
    const hostile = "#e0483a";
    person(ctx, 14, 7, ...bandit, "west", hostile);
    person(ctx, 16, 7, ...archer, "west", hostile);
    ring(ctx, 15 * T + T / 2, 8 * T + T * 0.82, hostile);
    EnemyArt.stamp(ctx, { body: "hound", material: "fur", tint: "#c8ccd0", traits: ["mist"] }, 15 * T + T / 2, 8 * T + T * 0.82, 0.78, true);
    bubble(ctx, 14 * T + T / 2, 7 * T - 20, "sword", "danger");
    // 敵群的警戒範圍（淡紅虛線）：走進去會被發現
    ctx.save(); ctx.setLineDash([6, 5]); ctx.strokeStyle = "rgba(224,72,58,0.75)"; ctx.lineWidth = 2; ctx.fillStyle = "rgba(224,72,58,0.08)";
    ctx.beginPath(); ctx.ellipse(15 * T + T / 2, 7.9 * T, 3.1 * T, 1.9 * T, 0, 0, TAU); ctx.fill(); ctx.stroke(); ctx.restore();
    // 玩家隊伍：從西邊路口進來
    person(ctx, 3, 5, ...PARTY[0], "east", "#5aa0ff");
    person(ctx, 2, 5, ...PARTY[1], "east", "#5aa0ff");
    // 未探索的區域：霧（北東）
    const fogCells = [];
    for (let gy = 0; gy < 5; gy++) for (let gx = 14; gx < 20; gx++) if (!(gx >= 15 && gx <= 16 && gy <= 1)) fogCells.push([gx, gy]);
    for (let gy = 0; gy < 3; gy++) for (let gx = 11; gx < 14; gx++) fogCells.push([gx, gy]);
    ctx.save();
    for (const [gx, gy] of fogCells) {
      const r = R(gx, gy, 77), cx = gx * T + T / 2, cy = gy * T + T / 2;
      const g = ctx.createRadialGradient(cx, cy, 4, cx, cy, T * 0.95);
      g.addColorStop(0, "rgba(220,226,222,0.92)"); g.addColorStop(0.6, "rgba(210,218,214,0.7)"); g.addColorStop(1, "rgba(210,218,214,0)");
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx + (r() - 0.5) * 8, cy + (r() - 0.5) * 8, T * 0.95, 0, TAU); ctx.fill();
    }
    ctx.restore();
    // 出口
    exit(ctx, "w", 4, 5, "霧渡鎮", "portal", cols, rows);
    exit(ctx, "n", 15, 16, "竹林小徑", "dots", cols, rows);
    hudFn(ctx, cols, rows, "渡口石階", "sword", { scene: "field" });
  }

  return { T, town, field, ICON, box, rr, dot, rgba, PARTY, OUT };
})();
