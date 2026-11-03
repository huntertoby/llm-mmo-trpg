// 大世界圖（M）與雲嶺區域圖的插畫樣張（美術 PM，2026-11-04；#120 第 21.1 節）。全部程式繪製。
// 大世界圖：五區是漂浮的界域，主城在中央浮島；已開放的區是彩色，沒解鎖的是灰色剪影加解鎖條件。
// 區域圖：一張插畫，地點照 content/world/maps/cloud_ridge.yaml 的 pos；去過＝彩色、相鄰沒去過＝灰色「？？？」、更遠＝霧；隱藏地點不顯示。
window.WorldMap = (() => {
  const TAU = Math.PI * 2, OUT = "#1c1712";
  function rng(seed) { let s = seed >>> 0 || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return (s % 100000) / 100000; }; }
  function glow(ctx, x, y, r, c, a) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, c); g.addColorStop(1, c.replace(/[\d.]+\)$/, "0)")); ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); ctx.restore(); }
  function label(ctx, text, x, y, size = 14, color = "#f2e6c8", bg = "rgba(24,20,16,0.78)", border = "#c8a868") {
    ctx.font = `bold ${size}px 'Microsoft JhengHei', sans-serif`; const w = ctx.measureText(text).width + 14;
    ctx.fillStyle = bg; ctx.strokeStyle = border; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.roundRect(x - w / 2, y - size * 0.75 - 3, w, size * 1.5 + 2, 6); ctx.fill(); ctx.stroke();
    ctx.fillStyle = color; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(text, x, y + 1); ctx.textAlign = "left";
  }

  // ============================ 大世界圖 ============================
  /** 一座浮島：上面是該區的地景，下面是倒錐形的岩塊；gray＝未解鎖的灰色剪影。 */
  function island(ctx, cx, cy, r, kind, gray) {
    const R = rng(cx * 7 + cy);
    // 下方倒錐岩塊
    ctx.beginPath(); ctx.moveTo(cx - r, cy); for (let k = 0; k <= 8; k++) { const t = k / 8, x = cx - r + t * 2 * r, y = cy + Math.sin(t * Math.PI) * r * (0.9 + R() * 0.25) + (k % 2) * 6; ctx.lineTo(x, y); } ctx.closePath();
    const rock = ctx.createLinearGradient(0, cy, 0, cy + r); rock.addColorStop(0, gray ? "#6a6a70" : "#6a5a4a"); rock.addColorStop(1, gray ? "#3a3a40" : "#2a2018"); ctx.fillStyle = rock; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    // 頂面
    const top = { cloud: "#6a9a6a", ashen: "#4a3a30", crown: "#d8ccb0", arcane: "#4a4238", frost: "#d8c89a", capital: "#e8dcc0" }[kind];
    ctx.beginPath(); ctx.ellipse(cx, cy, r, r * 0.38, 0, 0, TAU); ctx.fillStyle = gray ? "#8a8a90" : top; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.save(); ctx.beginPath(); ctx.ellipse(cx, cy, r, r * 0.38, 0, 0, TAU); ctx.clip();
    if (gray) { ctx.fillStyle = "rgba(60,60,70,0.35)"; for (let k = 0; k < 5; k++) { const x = cx - r * 0.7 + k * r * 0.35, h = 10 + R() * 22; ctx.beginPath(); ctx.moveTo(x - 10, cy + 6); ctx.lineTo(x, cy + 6 - h); ctx.lineTo(x + 10, cy + 6); ctx.fill(); } }
    else if (kind === "cloud") { // 青山、竹林、雲霧
      for (let k = 0; k < 4; k++) { const x = cx - r * 0.6 + k * r * 0.4, h = 22 + R() * 18; ctx.fillStyle = k % 2 ? "#4f7a5a" : "#5a8a64"; ctx.beginPath(); ctx.moveTo(x - 22, cy + 10); ctx.lineTo(x, cy + 10 - h); ctx.lineTo(x + 22, cy + 10); ctx.fill(); ctx.fillStyle = "rgba(232,232,224,0.8)"; ctx.beginPath(); ctx.moveTo(x - 5, cy + 10 - h + 6); ctx.lineTo(x, cy + 10 - h); ctx.lineTo(x + 5, cy + 10 - h + 6); ctx.fill(); }
      glow(ctx, cx, cy, r * 0.7, "rgba(240,240,235,0.9)", 0.35); ctx.fillStyle = "#b8432f"; ctx.fillRect(cx - 4, cy - 2, 8, 8);
    } else if (kind === "ashen") { // 焦土、熔岩河、火山
      ctx.strokeStyle = "#ff6a1a"; ctx.lineWidth = 3; ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 8; ctx.beginPath(); ctx.moveTo(cx - r, cy + 4); ctx.quadraticCurveTo(cx - r * 0.2, cy - 10, cx + r, cy + 6); ctx.stroke(); ctx.shadowBlur = 0;
      ctx.fillStyle = "#2a1e18"; ctx.beginPath(); ctx.moveTo(cx + r * 0.1, cy + 10); ctx.lineTo(cx + r * 0.35, cy - 26); ctx.lineTo(cx + r * 0.6, cy + 10); ctx.fill(); glow(ctx, cx + r * 0.35, cy - 26, 18, "rgba(255,120,40,0.9)", 0.8);
    } else if (kind === "capital") { // 主城：白牆藍頂、中央晶塔
      for (let k = -2; k <= 2; k++) { ctx.fillStyle = "#f2e6c8"; ctx.fillRect(cx + k * 16 - 6, cy - 6, 12, 10); ctx.fillStyle = "#3a5ad0"; ctx.beginPath(); ctx.moveTo(cx + k * 16 - 8, cy - 6); ctx.lineTo(cx + k * 16, cy - 14); ctx.lineTo(cx + k * 16 + 8, cy - 6); ctx.fill(); }
    }
    ctx.restore();
    if (kind === "capital") { ctx.beginPath(); ctx.moveTo(cx - 7, cy - 4); ctx.lineTo(cx, cy - 44); ctx.lineTo(cx + 7, cy - 4); ctx.closePath(); ctx.fillStyle = "#c8bcff"; ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = OUT; ctx.stroke(); glow(ctx, cx, cy - 26, 30, "rgba(143,123,255,0.9)", 0.6); }
    if (gray) { // 鎖頭
      const lx = cx, ly = cy - 4; ctx.fillStyle = "#c8c8cc"; ctx.strokeStyle = OUT; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(lx, ly - 8, 7, Math.PI, 0); ctx.stroke(); ctx.beginPath(); ctx.roundRect(lx - 10, ly - 8, 20, 16, 3); ctx.fill(); ctx.stroke();
    }
  }
  function drawWorld(ctx, W, H) {
    const bg = ctx.createRadialGradient(W / 2, H / 2, 40, W / 2, H / 2, W * 0.7); bg.addColorStop(0, "#2a2a48"); bg.addColorStop(1, "#0e0e1c"); ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
    const R = rng(11); for (let k = 0; k < 140; k++) { ctx.fillStyle = `rgba(255,255,255,${0.2 + R() * 0.6})`; ctx.fillRect(R() * W, R() * H, 1.5, 1.5); }
    // 碎界的光帶與漂浮碎石
    ctx.save(); ctx.globalAlpha = 0.25; ctx.strokeStyle = "#8f7bff"; ctx.lineWidth = 30; ctx.beginPath(); ctx.ellipse(W / 2, H / 2 + 20, W * 0.38, H * 0.3, -0.1, 0, TAU); ctx.stroke(); ctx.restore();
    for (let k = 0; k < 18; k++) { const x = R() * W, y = R() * H, s = 3 + R() * 7; ctx.fillStyle = "#4a4a5a"; ctx.beginPath(); ctx.moveTo(x, y - s); ctx.lineTo(x + s, y); ctx.lineTo(x, y + s * 0.8); ctx.lineTo(x - s, y); ctx.closePath(); ctx.fill(); }
    // 主城與五區（位置照五角形，主城在中央）
    const C = [W / 2, H / 2 + 10];
    const realms = [
      ["crown", "晶冠城邦", -Math.PI / 2, true, "之後的賽季"], ["cloud", "雲嶺", -Math.PI / 2 + TAU / 5, false, "Lv 1–6"], ["ashen", "灰燼荒原", -Math.PI / 2 + TAU * 2 / 5, false, "Lv 5–9"],
      ["frost", "霜潮海境", -Math.PI / 2 + TAU * 3 / 5, true, "之後的賽季"], ["arcane", "魔導樞市", -Math.PI / 2 + TAU * 4 / 5, true, "之後的賽季"],
    ];
    // 傳送航線：主城到已開放的區
    for (const [kind, , a, gray] of realms) { if (gray) continue; const x = C[0] + Math.cos(a) * W * 0.32, y = C[1] + Math.sin(a) * H * 0.33; ctx.save(); ctx.setLineDash([6, 6]); ctx.strokeStyle = "rgba(255,230,160,0.7)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(C[0], C[1]); ctx.lineTo(x, y); ctx.stroke(); ctx.restore(); }
    for (const [kind, zh, a, gray, sub] of realms) {
      const x = C[0] + Math.cos(a) * W * 0.32, y = C[1] + Math.sin(a) * H * 0.33;
      if (!gray) glow(ctx, x, y, 110, kind === "ashen" ? "rgba(255,120,40,0.8)" : "rgba(140,220,160,0.8)", 0.25);
      island(ctx, x, y, 78, kind, gray);
      label(ctx, zh, x, y + 92, 15, gray ? "#b8b8bc" : "#f2e6c8", "rgba(24,20,16,0.8)", gray ? "#6a6a70" : "#c8a868");
      label(ctx, sub, x, y + 116, 11, gray ? "#9a9aa0" : "#ffd23a", "rgba(24,20,16,0.6)", "rgba(0,0,0,0)");
    }
    island(ctx, C[0], C[1], 62, "capital", false); label(ctx, "主城", C[0], C[1] + 74, 15);
    // 自己的位置（雲嶺）
    const ca = realms[1][2], px = C[0] + Math.cos(ca) * W * 0.32 + 20, py = C[1] + Math.sin(ca) * H * 0.33 - 18;
    ctx.fillStyle = "#5aa0ff"; ctx.beginPath(); ctx.arc(px, py, 7, 0, TAU); ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = "#ffffff"; ctx.stroke();
    label(ctx, "大世界（M）　點已開放的區進區域圖；在城鎮裡可以點城鎮傳送", W / 2, 22, 12, "#d8ccb8", "rgba(24,20,16,0.7)", "rgba(200,168,104,0.5)");
  }

  // ============================ 雲嶺區域圖 ============================
  const LOC = [["mist_ferry", "霧渡鎮", "town", 10, 80, null], ["ferry_steps", "渡口石階", "camp", 25, 85, 1], ["bamboo_path", "竹林小徑", "camp", 30, 65, 1], ["rain_terraces", "雨中梯田", "camp", 45, 70, 2], ["mist_temple_gate", "青霧觀山門", "village", 50, 55, 2], ["hunter_hut", "獵戶小屋", "village", 15, 55, 2], ["cliff_gang_fort", "斷崖幫寨", "camp", 60, 80, 3], ["old_pine_altar", "古松祭壇", "altar", 35, 45, 3], ["cloud_sea_bridge", "雲海吊橋", "camp", 60, 45, 3], ["herb_valley", "藥師谷", "ruin", 75, 65, 4], ["elixir_cave", "丹爐洞", "secret", 90, 70, 5, true], ["north_slope", "北坡獵場", "elite_lair", 25, 25, 4], ["winter_lake", "冬湖", "camp", 15, 40, 4], ["sword_tomb", "劍冢", "ruin", 70, 30, 5], ["crystal_rift", "源晶裂痕", "anomaly", 50, 20, 5], ["crane_cliff", "鶴歸崖", "secret", 30, 8, 6, true], ["cloud_summit", "雲頂觀", "boss", 75, 10, 6], ["ashen_ferry", "往灰燼荒原的渡口", "gate", 5, 95, null]];
  const EDGES = [["mist_ferry", "ferry_steps"], ["mist_ferry", "hunter_hut"], ["mist_ferry", "ashen_ferry"], ["ferry_steps", "bamboo_path"], ["bamboo_path", "hunter_hut"], ["bamboo_path", "rain_terraces"], ["rain_terraces", "mist_temple_gate"], ["rain_terraces", "cliff_gang_fort"], ["rain_terraces", "old_pine_altar"], ["hunter_hut", "winter_lake"], ["old_pine_altar", "cloud_sea_bridge"], ["mist_temple_gate", "cloud_sea_bridge"], ["cliff_gang_fort", "herb_valley"], ["cloud_sea_bridge", "herb_valley"], ["cloud_sea_bridge", "sword_tomb"], ["herb_valley", "elixir_cave"], ["winter_lake", "north_slope"], ["north_slope", "crane_cliff"], ["north_slope", "crystal_rift"], ["sword_tomb", "crystal_rift"], ["crystal_rift", "cloud_summit"]];
  // 樣張的進度：去過 6 個地點
  const VISITED = new Set(["mist_ferry", "ferry_steps", "bamboo_path", "hunter_hut", "rain_terraces", "ashen_ferry"]);
  const CLEARED = new Set(["ferry_steps", "bamboo_path"]);
  const STONES = new Set(["mist_ferry", "rain_terraces"]);
  function icon(ctx, kind, x, y, gray) {
    const col = gray ? "#8a8a8a" : { town: "#e8bb48", camp: "#c83a2a", village: "#6aa84a", altar: "#a898ff", ruin: "#9a8e7c", elite_lair: "#ff6a50", boss: "#ff3a2a", anomaly: "#5ae0f0", gate: "#7ad8ff", secret: "#8a6aa8" }[kind];
    ctx.fillStyle = "rgba(0,0,0,0.35)"; ctx.beginPath(); ctx.ellipse(x + 2, y + 12, 12, 4, 0, 0, TAU); ctx.fill();
    ctx.beginPath(); ctx.arc(x, y, 11, 0, TAU); ctx.fillStyle = gray ? "#5a5a5e" : "#f2e6c8"; ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = col; ctx.stroke(); ctx.lineWidth = 1; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.fillStyle = col; ctx.strokeStyle = col; ctx.lineWidth = 2;
    if (kind === "town") { ctx.beginPath(); ctx.moveTo(x - 6, y + 4); ctx.lineTo(x, y - 6); ctx.lineTo(x + 6, y + 4); ctx.closePath(); ctx.fill(); }
    else if (kind === "camp" || kind === "elite_lair" || kind === "boss") { ctx.beginPath(); ctx.moveTo(x - 5, y + 5); ctx.lineTo(x + 5, y - 5); ctx.moveTo(x + 5, y + 5); ctx.lineTo(x - 5, y - 5); ctx.stroke(); if (kind === "boss") { ctx.beginPath(); ctx.arc(x, y, 7, 0, TAU); ctx.stroke(); } }
    else if (kind === "village") { ctx.fillRect(x - 5, y - 2, 10, 7); ctx.beginPath(); ctx.moveTo(x - 7, y - 2); ctx.lineTo(x, y - 7); ctx.lineTo(x + 7, y - 2); ctx.fill(); }
    else if (kind === "gate") { ctx.beginPath(); ctx.moveTo(x - 6, y + 2); ctx.quadraticCurveTo(x, y + 6, x + 6, y + 2); ctx.lineTo(x + 4, y + 5); ctx.lineTo(x - 4, y + 5); ctx.closePath(); ctx.fill(); }
    else { ctx.beginPath(); ctx.arc(x, y, 4, 0, TAU); ctx.fill(); }
  }
  function drawRegion(ctx, W, H) {
    const P = (l) => [40 + l[3] / 100 * (W - 80), 30 + l[4] / 100 * (H - 70)];
    const byId = Object.fromEntries(LOC.map((l) => [l[0], l]));
    // ---- 地景插畫 ----
    const sky = ctx.createLinearGradient(0, 0, 0, H); sky.addColorStop(0, "#c8d4cc"); sky.addColorStop(0.25, "#9ab8a0"); sky.addColorStop(1, "#7aa07a"); ctx.fillStyle = sky; ctx.fillRect(0, 0, W, H);
    const R = rng(5);
    // 北方群山（雲頂觀在東北的最高峰）
    for (let k = 0; k < 9; k++) { const x = k * W / 8 - 20 + R() * 30, h = 120 + R() * 90 + (k === 6 ? 70 : 0); ctx.fillStyle = `rgba(${70 + k * 4},${100 + k * 3},${96},1)`; ctx.beginPath(); ctx.moveTo(x - 140, H * 0.42); ctx.lineTo(x, H * 0.42 - h); ctx.lineTo(x + 140, H * 0.42); ctx.closePath(); ctx.fill(); ctx.fillStyle = "rgba(240,244,240,0.85)"; ctx.beginPath(); ctx.moveTo(x - 24, H * 0.42 - h + 28); ctx.lineTo(x, H * 0.42 - h); ctx.lineTo(x + 24, H * 0.42 - h + 28); ctx.closePath(); ctx.fill(); }
    // 雲海帶（中段）
    for (let k = 0; k < 14; k++) { const x = R() * W, y = H * 0.38 + R() * 60; glow(ctx, x, y, 70 + R() * 40, "rgba(250,250,245,0.95)", 0.55); }
    // 南方：竹林、梯田、霧河
    for (let k = 0; k < 40; k++) { const x = W * 0.18 + R() * W * 0.22, y = H * 0.62 + R() * H * 0.14; ctx.strokeStyle = R() < 0.5 ? "#4f8a3a" : "#6aa84a"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x, y + 12); ctx.lineTo(x + 1, y - 10); ctx.stroke(); }
    for (let k = 0; k < 5; k++) { ctx.strokeStyle = "rgba(120,170,200,0.7)"; ctx.lineWidth = 3; ctx.beginPath(); ctx.ellipse(W * 0.47, H * 0.75 + k * 8, 70 - k * 8, 10, 0, Math.PI, TAU); ctx.stroke(); }
    ctx.strokeStyle = "#5a8ab8"; ctx.lineWidth = 16; ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(0, H * 0.96); ctx.quadraticCurveTo(W * 0.3, H * 0.86, W * 0.7, H * 0.96); ctx.stroke(); ctx.strokeStyle = "rgba(255,255,255,0.4)"; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = "rgba(120,160,190,0.9)"; ctx.beginPath(); ctx.ellipse(W * 0.17, H * 0.43, 46, 18, 0, 0, TAU); ctx.fill(); // 冬湖
    // 紙張質感的邊框
    ctx.strokeStyle = "#5a4030"; ctx.lineWidth = 6; ctx.strokeRect(3, 3, W - 6, H - 6);
    // ---- 地點狀態 ----
    const adj = new Set(); for (const [a, b] of EDGES) { if (VISITED.has(a) && !VISITED.has(b)) adj.add(b); if (VISITED.has(b) && !VISITED.has(a)) adj.add(a); }
    const state = (id) => (byId[id][6] ? "hidden" : VISITED.has(id) ? "visited" : adj.has(id) ? "adjacent" : "far");
    // 路：去過之間實線，通往相鄰沒去過的虛線
    for (const [a, b] of EDGES) {
      const sa = state(a), sb = state(b); if (sa === "hidden" || sb === "hidden" || sa === "far" || sb === "far") continue;
      const [x1, y1] = P(byId[a]), [x2, y2] = P(byId[b]); ctx.save(); ctx.lineCap = "round";
      ctx.strokeStyle = sa === "visited" && sb === "visited" ? "#8a6a3a" : "rgba(90,80,60,0.7)"; ctx.lineWidth = sa === "visited" && sb === "visited" ? 4 : 2.5; if (!(sa === "visited" && sb === "visited")) ctx.setLineDash([6, 6]);
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke(); ctx.restore();
    }
    // 朋友的足跡（獵戶小屋往冬湖）
    { const [x1, y1] = P(byId.hunter_hut), [x2, y2] = P(byId.winter_lake); for (let k = 1; k < 6; k++) { const t = k / 6, x = x1 + (x2 - x1) * t + (k % 2 ? 4 : -4), y = y1 + (y2 - y1) * t; ctx.fillStyle = "rgba(255,255,255,0.85)"; ctx.beginPath(); ctx.ellipse(x, y, 2.4, 3.6, 0.3, 0, TAU); ctx.fill(); } }
    // 戰爭迷霧：更遠的地點被霧蓋住（霧的範圍＝far 地點的周圍）
    for (const l of LOC) if (state(l[0]) === "far") { const [x, y] = P(l); for (let k = 0; k < 3; k++) glow(ctx, x + (k - 1) * 30, y + (k % 2) * 16, 90, "rgba(210,216,214,0.98)", 0.8); }
    glow(ctx, W * 0.75, H * 0.2, 240, "rgba(214,220,218,0.98)", 0.75);
    // 地點
    for (const l of LOC) {
      const st = state(l[0]); if (st === "hidden" || st === "far") continue;
      const [x, y] = P(l), gray = st === "adjacent"; icon(ctx, l[2], x, y, gray);
      const name = gray ? "？？？" : l[1], lv = l[5] ? `Lv ${l[5]}` : "";
      label(ctx, name + (lv ? `　${lv}` : ""), x, y + 26, 11, gray ? "#c8c8cc" : "#f2e6c8", "rgba(24,20,16,0.75)", gray ? "#6a6a70" : "#c8a868");
      if (CLEARED.has(l[0])) { ctx.fillStyle = "#5ad06a"; ctx.beginPath(); ctx.arc(x + 11, y - 10, 6, 0, TAU); ctx.fill(); ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x + 8, y - 10); ctx.lineTo(x + 10.5, y - 7.5); ctx.lineTo(x + 14, y - 13); ctx.stroke(); }
      if (STONES.has(l[0])) { ctx.save(); ctx.shadowColor = "#5ac8f0"; ctx.shadowBlur = 8; ctx.strokeStyle = "#5ac8f0"; ctx.lineWidth = 2; ctx.beginPath(); ctx.ellipse(x - 14, y + 8, 7, 3.5, 0, 0, TAU); ctx.stroke(); ctx.restore(); }
    }
    // 任務標記（斷崖幫寨：新手任務 1 的後續）與自己的位置
    { const [x, y] = P(byId.cliff_gang_fort); ctx.fillStyle = "#ffd23a"; ctx.beginPath(); ctx.roundRect(x - 8, y - 38, 16, 18, 5); ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = OUT; ctx.stroke(); ctx.fillStyle = OUT; ctx.fillRect(x - 1.5, y - 35, 3, 8); ctx.fillRect(x - 1.5, y - 25, 3, 3); }
    { const [x, y] = P(byId.bamboo_path); ctx.fillStyle = "#5aa0ff"; ctx.beginPath(); ctx.arc(x - 16, y - 12, 7, 0, TAU); ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = "#fff"; ctx.stroke(); }
    // 圖例
    const lg = [["彩色＝去過（名字、建議等級、✓＝清空）", "#f2e6c8"], ["灰色？？？＝相鄰但沒去過", "#c8c8cc"], ["霧＝更遠；隱藏地點不顯示", "#d8dcd8"], ["藍圈＝傳送石　黃「！」＝任務　白腳印＝朋友的足跡", "#9ad8ff"]];
    ctx.fillStyle = "rgba(24,20,16,0.78)"; ctx.beginPath(); ctx.roundRect(W - 330, H - 104, 316, 90, 8); ctx.fill();
    lg.forEach(([t, c], i) => { ctx.fillStyle = c; ctx.font = "12px 'Microsoft JhengHei'"; ctx.textBaseline = "middle"; ctx.fillText(t, W - 318, H - 88 + i * 20); });
    label(ctx, "雲嶺（區域圖：只能看；站在傳送石上或城鎮裡才能點傳送石）", W / 2, 22, 13);
  }
  return { drawWorld, drawRegion };
})();
