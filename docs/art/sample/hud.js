// 網遊式 HUD 版面樣張（美術 PM，2026-11-04）。疊在 explore.js 的可走動城鎮／野外畫面上。只是示意，等使用者選。
// 使用者原話（專案 PM 轉達）：「能用圖式加文字 或者純圖示 還有不要直接一長條往下 在中間畫面的周邊 像網遊一樣」
// 三種版面：A 四角分散（推薦）、B 底部集中、C 極簡純圖示。全部程式繪製。
window.Hud = (() => {
  const { T, ICON, box, rr, dot, rgba, PARTY, OUT } = Explore;
  const TAU = Math.PI * 2;
  const GOLD = "#c8a868", PANEL = "rgba(24,20,16,0.84)", TEXT = "#f2e6c8", DIM = "#b8ab96";
  const HP = "#e04a3a", MP = "#4a8ae0", XP = "#e8bb48";
  // ---------------- 額外圖示 ----------------
  const I = {
    ...ICON,
    bag(c, x, y, s) { box(c, x - s * 0.45, y - s * 0.2, s * 0.9, s * 0.7, "#a07040", OUT, 1.5, s * 0.15); c.strokeStyle = OUT; c.lineWidth = 1.5; c.beginPath(); c.arc(x, y - s * 0.2, s * 0.25, Math.PI, 0); c.stroke(); box(c, x - s * 0.15, y - s * 0.05, s * 0.3, s * 0.2, "#e8bb48", OUT, 1, 1); },
    growth(c, x, y, s) { c.fillStyle = "#5ad06a"; c.beginPath(); c.moveTo(x, y - s * 0.55); c.lineTo(x + s * 0.45, y); c.lineTo(x + s * 0.18, y); c.lineTo(x + s * 0.18, y + s * 0.5); c.lineTo(x - s * 0.18, y + s * 0.5); c.lineTo(x - s * 0.18, y); c.lineTo(x - s * 0.45, y); c.closePath(); c.fill(); c.lineWidth = 1.5; c.strokeStyle = OUT; c.stroke(); },
    shadow(c, x, y, s) { c.fillStyle = "#3a3450"; c.beginPath(); c.arc(x, y - s * 0.22, s * 0.22, 0, TAU); c.fill(); c.beginPath(); c.ellipse(x, y + s * 0.3, s * 0.38, s * 0.3, 0, Math.PI, 0); c.fill(); c.strokeStyle = "#a898ff"; c.lineWidth = 1.5; c.setLineDash([2, 2]); c.beginPath(); c.arc(x, y - s * 0.22, s * 0.22, 0, TAU); c.stroke(); c.setLineDash([]); },
    notes(c, x, y, s) { box(c, x - s * 0.5, y - s * 0.4, s, s * 0.7, "#f2e6c8", OUT, 1.5, 3); c.fillStyle = "#f2e6c8"; c.beginPath(); c.moveTo(x - s * 0.2, y + s * 0.28); c.lineTo(x - s * 0.3, y + s * 0.5); c.lineTo(x, y + s * 0.28); c.fill(); c.strokeStyle = "#8a7a5a"; c.lineWidth = 1; for (const k of [-0.18, 0.02]) { c.beginPath(); c.moveTo(x - s * 0.3, y + s * k); c.lineTo(x + s * 0.3, y + s * k); c.stroke(); } },
    map(c, x, y, s) { c.fillStyle = "#e8dcb8"; c.beginPath(); c.moveTo(x - s * 0.5, y - s * 0.35); c.lineTo(x - s * 0.17, y - s * 0.45); c.lineTo(x + s * 0.17, y - s * 0.35); c.lineTo(x + s * 0.5, y - s * 0.45); c.lineTo(x + s * 0.5, y + s * 0.35); c.lineTo(x + s * 0.17, y + s * 0.45); c.lineTo(x - s * 0.17, y + s * 0.35); c.lineTo(x - s * 0.5, y + s * 0.45); c.closePath(); c.fill(); c.lineWidth = 1.5; c.strokeStyle = OUT; c.stroke(); c.strokeStyle = "#c03020"; c.beginPath(); c.moveTo(x - s * 0.1, y - s * 0.1); c.lineTo(x + s * 0.1, y + s * 0.1); c.moveTo(x + s * 0.1, y - s * 0.1); c.lineTo(x - s * 0.1, y + s * 0.1); c.stroke(); },
    boots(c, x, y, s) { c.fillStyle = "#8a5a30"; c.beginPath(); c.moveTo(x - s * 0.25, y - s * 0.5); c.lineTo(x + s * 0.1, y - s * 0.5); c.lineTo(x + s * 0.1, y + s * 0.15); c.lineTo(x + s * 0.5, y + s * 0.25); c.lineTo(x + s * 0.5, y + s * 0.45); c.lineTo(x - s * 0.25, y + s * 0.45); c.closePath(); c.fill(); c.lineWidth = 1.5; c.strokeStyle = OUT; c.stroke(); c.strokeStyle = "#ffd23a"; c.lineWidth = 1.8; for (const k of [-0.2, 0, 0.2]) { c.beginPath(); c.moveTo(x - s * 0.7, y + s * k); c.lineTo(x - s * 0.38, y + s * k); c.stroke(); } },
    sun(c, x, y, s) { c.strokeStyle = "#ffb030"; c.lineWidth = 1.8; for (let k = 0; k < 8; k++) { const a = (k / 8) * TAU; c.beginPath(); c.moveTo(x + Math.cos(a) * s * 0.35, y + Math.sin(a) * s * 0.35); c.lineTo(x + Math.cos(a) * s * 0.52, y + Math.sin(a) * s * 0.52); c.stroke(); } dot(c, x, y, s * 0.27, "#ffd23a"); },
    rain(c, x, y, s) { c.fillStyle = "#c8d0d8"; for (const [dx, dy, r] of [[-0.18, -0.08, 0.22], [0.12, -0.15, 0.27], [0.32, 0, 0.18], [-0.36, 0.05, 0.16]]) { c.beginPath(); c.arc(x + dx * s, y + dy * s, r * s, 0, TAU); c.fill(); } c.fillRect(x - s * 0.36, y, s * 0.68, s * 0.16); c.strokeStyle = "#5ab0f0"; c.lineWidth = 1.5; for (const k of [-0.2, 0.05, 0.3]) { c.beginPath(); c.moveTo(x + s * k, y + s * 0.28); c.lineTo(x + s * (k - 0.08), y + s * 0.5); c.stroke(); } },
    fog(c, x, y, s) { c.strokeStyle = "#d8dee0"; c.lineWidth = 2.2; c.lineCap = "round"; for (const [k, w] of [[-0.25, 0.4], [0, 0.5], [0.25, 0.35]]) { c.beginPath(); c.moveTo(x - s * w, y + s * k); c.lineTo(x + s * w, y + s * k); c.stroke(); } },
    token(c, x, y, s) { c.fillStyle = "#c86a3a"; c.beginPath(); for (let k = 0; k < 6; k++) { const a = (k / 6) * TAU - Math.PI / 2; c.lineTo(x + Math.cos(a) * s * 0.5, y + Math.sin(a) * s * 0.5); } c.closePath(); c.fill(); c.lineWidth = 1.5; c.strokeStyle = OUT; c.stroke(); I.scroll(c, x, y, s * 0.5); },
    ration(c, x, y, s) { c.fillStyle = "#c89a5a"; c.beginPath(); c.ellipse(x, y + s * 0.05, s * 0.5, s * 0.32, -0.2, 0, TAU); c.fill(); c.lineWidth = 1.5; c.strokeStyle = OUT; c.stroke(); c.strokeStyle = "#8a5a30"; c.lineWidth = 1.2; for (const k of [-0.2, 0, 0.2]) { c.beginPath(); c.moveTo(x + s * k - s * 0.06, y - s * 0.15); c.lineTo(x + s * k + s * 0.06, y + s * 0.2); c.stroke(); } },
    bulb(c, x, y, s) { c.save(); c.shadowColor = "#ffe080"; c.shadowBlur = 6; dot(c, x, y - s * 0.1, s * 0.33, "#ffe080"); c.restore(); c.lineWidth = 1.5; c.strokeStyle = OUT; c.beginPath(); c.arc(x, y - s * 0.1, s * 0.33, 0, TAU); c.stroke(); box(c, x - s * 0.15, y + s * 0.22, s * 0.3, s * 0.2, "#8a8a84", OUT, 1, 1); },
    rank(c, x, y, s) { c.fillStyle = "#c0c8d0"; c.beginPath(); c.moveTo(x - s * 0.4, y - s * 0.45); c.lineTo(x + s * 0.4, y - s * 0.45); c.lineTo(x + s * 0.4, y + s * 0.1); c.lineTo(x, y + s * 0.5); c.lineTo(x - s * 0.4, y + s * 0.1); c.closePath(); c.fill(); c.lineWidth = 1.5; c.strokeStyle = OUT; c.stroke(); c.fillStyle = "#3a5ad0"; c.fillRect(x - s * 0.25, y - s * 0.3, s * 0.5, s * 0.12); c.fillRect(x - s * 0.25, y - s * 0.1, s * 0.5, s * 0.12); },
    book(c, x, y, s) { box(c, x - s * 0.45, y - s * 0.45, s * 0.9, s * 0.9, "#5a3a9a", OUT, 1.5, 2); c.fillStyle = "#f2e6c8"; c.fillRect(x - s * 0.3, y - s * 0.45, s * 0.12, s * 0.9); c.save(); c.shadowColor = "#a898ff"; c.shadowBlur = 5; dot(c, x + s * 0.08, y, s * 0.16, "#c8bcff"); c.restore(); },
    gear(c, x, y, s) { c.fillStyle = "#9aa0a8"; c.beginPath(); for (let k = 0; k < 16; k++) { const a = (k / 16) * TAU, r = k % 2 ? s * 0.38 : s * 0.5; c.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); } c.closePath(); c.fill(); c.lineWidth = 1.5; c.strokeStyle = OUT; c.stroke(); dot(c, x, y, s * 0.15, "#2a241e"); },
    warn(c, x, y, s) { c.beginPath(); c.moveTo(x, y - s * 0.5); c.lineTo(x + s * 0.5, y + s * 0.4); c.lineTo(x - s * 0.5, y + s * 0.4); c.closePath(); c.fillStyle = "#ffd23a"; c.fill(); c.lineWidth = 1.5; c.strokeStyle = OUT; c.stroke(); I.bang(c, x, y + s * 0.02, s * 0.6); },
    clock(c, x, y, s) { dot(c, x, y, s * 0.45, "#f2e6c8"); c.lineWidth = 1.5; c.strokeStyle = OUT; c.beginPath(); c.arc(x, y, s * 0.45, 0, TAU); c.moveTo(x, y); c.lineTo(x, y - s * 0.3); c.moveTo(x, y); c.lineTo(x + s * 0.2, y + s * 0.1); c.stroke(); },
  };
  // ---------------- 小元件 ----------------
  function text(c, s, x, y, size = 12, color = TEXT, align = "left", bold = true) {
    c.font = `${bold ? "bold " : ""}${size}px 'Microsoft JhengHei', sans-serif`; c.fillStyle = color; c.textAlign = align; c.textBaseline = "middle";
    c.lineWidth = 3; c.strokeStyle = "rgba(0,0,0,0.6)"; c.strokeText(s, x, y); c.fillText(s, x, y); c.textAlign = "left";
  }
  function bar(c, x, y, w, h, frac, color, label) {
    box(c, x, y, w, h, "#1a1410", OUT, 1.5, h / 2);
    box(c, x + 1.5, y + 1.5, Math.max(0, (w - 3) * frac), h - 3, color, null, 0, (h - 3) / 2);
    c.fillStyle = "rgba(255,255,255,0.25)"; c.fillRect(x + 4, y + 2.5, Math.max(0, (w - 8) * frac), 1.5);
    if (label) text(c, label, x + w / 2, y + h / 2 + 0.5, Math.min(11, h - 2), "#ffffff", "center");
  }
  function portrait(c, x, y, size, idx, ringColor = GOLD) {
    const [look, gear] = PARTY[idx];
    c.save(); c.beginPath(); c.arc(x, y, size / 2, 0, TAU); c.fillStyle = "#2a3634"; c.fill(); c.clip();
    PaperDoll.stamp(c, { look, gear }, "south", x, y + size * 0.95, size / 40, { dpr: 3 }); c.restore();
    c.lineWidth = 2.5; c.strokeStyle = ringColor; c.beginPath(); c.arc(x, y, size / 2, 0, TAU); c.stroke();
  }
  function badge(c, x, y, s, fill = "#e04a3a") {
    c.font = "bold 10px Consolas, monospace"; const w = Math.max(14, c.measureText(s).width + 8);
    box(c, x - w / 2, y - 7, w, 14, fill, OUT, 1.2, 7); c.fillStyle = "#fff"; c.textAlign = "center"; c.textBaseline = "middle"; c.fillText(s, x, y + 0.5); c.textAlign = "left";
  }
  function iconBtn(c, x, y, icon, size = 40, opts = {}) {
    box(c, x, y, size, size, opts.on ? "rgba(90,70,30,0.92)" : PANEL, opts.on ? "#ffd23a" : GOLD, 1.8, 7);
    I[icon](c, x + size / 2, y + size / 2 + (opts.key ? -2 : 0), size * 0.5);
    if (opts.key) text(c, opts.key, x + size - 7, y + size - 7, 9, DIM, "center");
    if (opts.badge) badge(c, x + size - 3, y + 3, opts.badge, opts.badgeFill);
  }
  function chip(c, x, y, icon, val, w = 70) { // 圖示＋數字
    box(c, x, y, w, 22, PANEL, "rgba(200,168,104,0.6)", 1.2, 11);
    I[icon](c, x + 12, y + 11, 13); text(c, val, x + 24, y + 11.5, 12);
  }
  function minimap(c, x, y, w, h, scene) {
    box(c, x, y, w, h, "rgba(20,26,24,0.9)", GOLD, 2, 8);
    c.save(); rr(c, x + 3, y + 3, w - 6, h - 6, 6); c.clip();
    const cw = (w - 6) / 20, ch = (h - 6) / 12, ox = x + 3, oy = y + 3;
    const fill = (gx, gy, gw, gh, col) => { c.fillStyle = col; c.fillRect(ox + gx * cw, oy + gy * ch, gw * cw, gh * ch); };
    fill(0, 0, 20, 12, "#5a7a5e");
    if (scene === "town") {
      fill(2, 4, 16, 5, "#b89a62"); fill(3, 5, 14, 3, "#7d8c84"); fill(7, 0, 2, 4, "#b89a62"); fill(17, 5, 3, 2, "#b89a62");
      fill(2, 1, 4, 3, "#3c4a48"); fill(10, 1, 3, 3, "#3c4a48"); fill(13, 1, 5, 3, "#3c4a48"); fill(0, 10, 20, 2, "#3f7aa8"); fill(9, 9, 2, 3, "#b89a62");
      for (const [gx, gy] of [[5, 4], [12, 4], [17, 4], [10, 9]]) dot(c, ox + (gx + 0.5) * cw, oy + (gy + 0.5) * ch, 2.2, "#ffd23a");
      dot(c, ox + 8.5 * cw, oy + 6.5 * ch, 3, "#5aa0ff");
    } else {
      fill(0, 4, 8, 2, "#b89a62"); fill(8, 2, 6, 5, "#7d8c84"); fill(15, 0, 2, 2, "#b89a62"); fill(0, 9, 20, 3, "#3f7aa8"); fill(13, 8, 3, 1, "#9a7a50");
      fill(11, 0, 9, 5, "rgba(220,226,222,0.85)");
      for (const [gx, gy] of [[14, 7], [16, 7], [15, 8]]) dot(c, ox + (gx + 0.5) * cw, oy + (gy + 0.5) * ch, 2.4, "#e0483a");
      dot(c, ox + 2.5 * cw, oy + 3.5 * ch, 2.2, "#ffd23a"); dot(c, ox + 6.5 * cw, oy + 7.5 * ch, 2.2, "#ff8a2a");
      dot(c, ox + 3.5 * cw, oy + 5.5 * ch, 3, "#5aa0ff");
    }
    c.restore();
    // 出口箭頭（小地圖邊）
    c.fillStyle = "#fff4d0";
    const arrows = scene === "town" ? [[x + w - 5, y + h * 0.5, 0], [x + w * 0.4, y + 5, -Math.PI / 2]] : [[x + 5, y + h * 0.42, Math.PI], [x + w * 0.8, y + 5, -Math.PI / 2]];
    for (const [ax, ay, a] of arrows) { c.save(); c.translate(ax, ay); c.rotate(a); c.beginPath(); c.moveTo(5, 0); c.lineTo(-3, -5); c.lineTo(-3, 5); c.closePath(); c.fill(); c.lineWidth = 1; c.strokeStyle = OUT; c.stroke(); c.restore(); }
  }
  function toast(c, x, y, w, icon, msg, color = GOLD, alpha = 1) {
    c.save(); c.globalAlpha = alpha;
    box(c, x, y, w, 26, "rgba(24,20,16,0.78)", color, 1.5, 13);
    I[icon](c, x + 14, y + 13, 14); text(c, msg, x + 28, y + 13.5, 12, TEXT, "left", false);
    c.restore();
  }
  function tracker(c, x, y, w, scene) { // 任務追蹤（地點卡的精簡版，可收合）
    const lines = scene === "town" ? [["bang", "盜賊搶渡船", "東邊・渡口石階"], ["scroll", "懸賞：霧狼 ×3", "0 / 3"]] : [["bang", "盜賊搶渡船", "擊退碼頭的盜賊"], ["ask", "古碑上的字", "調查"]];
    box(c, x, y, w, 20 + lines.length * 36, PANEL, "rgba(200,168,104,0.6)", 1.2, 8);
    I.scroll(c, x + 14, y + 11, 12); text(c, "任務", x + 26, y + 11, 11, DIM); text(c, "－", x + w - 12, y + 11, 12, DIM, "center");
    lines.forEach(([ic, a, b], i) => { const ly = y + 22 + i * 36; I[ic](c, x + 14, ly + 10, 14); text(c, a, x + 28, ly + 8, 12); text(c, b, x + 28, ly + 24, 10.5, DIM, "left", false); });
  }
  function timeWeather(c, x, y, scene) {
    box(c, x, y, 86, 26, PANEL, "rgba(200,168,104,0.6)", 1.2, 13);
    I.sun(c, x + 14, y + 13, 16); text(c, "午", x + 26, y + 13.5, 12);
    I[scene === "town" ? "fog" : "rain"](c, x + 56, y + 13, 16); text(c, scene === "town" ? "霧" : "雨", x + 68, y + 13.5, 12);
  }

  // ======================= A：四角分散（推薦）=======================
  function hudA(c, cols, rows, place, placeIcon, info) {
    const W = cols * T, H = rows * T, sc = info.scene;
    // 左上：主角
    box(c, 8, 8, 250, 74, PANEL, GOLD, 1.5, 10);
    portrait(c, 46, 45, 62, 0);
    badge(c, 70, 72, "Lv 4", "#3a5ad0");
    I.rank(c, 22, 72, 14);
    bar(c, 84, 18, 164, 15, 0.82, HP, "HP 41 / 50");
    bar(c, 84, 37, 164, 13, 0.6, MP, "法力 18 / 30");
    bar(c, 84, 55, 164, 5, 0.45, XP);
    chip(c, 84, 63, "ration", "6", 56); chip(c, 144, 63, "bulb", "2", 50);
    // 隊友（主角框下）＋影子
    [[1, 0.7], [0, 0.95]].forEach(([idx, hp], i) => {
      const y = 98 + i * 42;
      box(c, 8, y, 150, 36, PANEL, "rgba(200,168,104,0.6)", 1.2, 18);
      portrait(c, 26, y + 18, 30, idx, "#8fb0d0"); text(c, i ? "傭兵・岳" : "傭兵・青", 46, y + 11, 11);
      bar(c, 46, y + 20, 104, 9, hp, HP);
    });
    iconBtn(c, 8, 184, "shadow", 36, { badge: "!" , badgeFill: "#8a6ad0" });
    // 右上：地名、小地圖、時間天氣、錢
    const mx = W - 178;
    box(c, mx, 8, 170, 24, PANEL, GOLD, 1.5, 6); I[placeIcon](c, mx + 14, 20, 13); text(c, place, mx + 28, 20.5, 13);
    I.warn(c, mx + 156, 20, 14);
    minimap(c, mx, 36, 170, 104, sc);
    timeWeather(c, mx, 146, sc);
    iconBtn(c, mx + 92, 144, "map", 30, { key: "M" }); iconBtn(c, mx + 128, 144, "gear", 30);
    chip(c, mx, 178, "coin", "1,240", 84); chip(c, mx + 88, 178, "token", "35", 82);
    // 右側：任務追蹤
    tracker(c, W - 178, 372, 170, sc);
    // 底部中央：功能列
    const btns = [["bag", "I", null], ["book", "K", "2"], ["growth", "G", null], ["scroll", "J", null], ["shadow", "Y", null], ["notes", "N", "3"], ["boots", "R", null]];
    const bw = 46, gap = 6, total = btns.length * (bw + gap) - gap, bx = (W - total) / 2;
    box(c, bx - 10, H - 62, total + 20, 56, "rgba(24,20,16,0.6)", null, 0, 12);
    btns.forEach(([ic, k, b], i) => iconBtn(c, bx + i * (bw + gap), H - 56, ic, bw, { key: k, badge: b, on: ic === "boots" }));
    // 左下：事件浮動提示（新的在下，舊的淡出）
    toast(c, 10, H - 112, 230, "notes", "有人在這裡留了話", GOLD, 0.55);
    toast(c, 10, H - 82, 230, sc === "town" ? "coin" : "ask", sc === "town" ? "賣出 3 件雜物，+45" : "發現了古碑", GOLD, 1);
    toast(c, 10, H - 52, 230, "warn", sc === "town" ? "渡船：晚上不開" : "前方有盜賊的警戒", "#ff6a5a", 1);
  }

  // ======================= B：底部集中 =======================
  function hudB(c, cols, rows, place, placeIcon, info) {
    const W = cols * T, H = rows * T, sc = info.scene;
    // 底部一整條
    box(c, 0, H - 84, W, 84, "rgba(24,20,16,0.88)", GOLD, 1.5, 0);
    portrait(c, 46, H - 42, 64, 0); badge(c, 70, H - 14, "Lv 4", "#3a5ad0");
    bar(c, 86, H - 72, 200, 16, 0.82, HP, "HP 41 / 50"); bar(c, 86, H - 51, 200, 14, 0.6, MP, "法力 18 / 30"); bar(c, 86, H - 32, 200, 6, 0.45, XP);
    chip(c, 86, H - 22, "ration", "6", 56); chip(c, 146, H - 22, "bulb", "2", 50); chip(c, 200, H - 22, "rank", "銅", 56);
    const btns = [["bag", "I"], ["book", "K"], ["growth", "G"], ["scroll", "J"], ["shadow", "Y"], ["notes", "N"], ["boots", "R"], ["map", "M"]];
    btns.forEach(([ic, k], i) => iconBtn(c, 310 + i * 52, H - 70, ic, 46, { key: k, badge: ic === "notes" ? "3" : ic === "book" ? "2" : null, on: ic === "boots" }));
    chip(c, W - 186, H - 70, "coin", "1,240", 84); chip(c, W - 98, H - 70, "token", "35", 88);
    timeWeather(c, W - 186, H - 40, sc); iconBtn(c, W - 92, H - 42, "gear", 30);
    // 左側中：隊友直排
    [[1, 0.7], [0, 0.95]].forEach(([idx, hp], i) => { const y = 120 + i * 50; portrait(c, 30, y, 40, idx, "#8fb0d0"); bar(c, 54, y + 6, 70, 8, hp, HP); });
    iconBtn(c, 10, 214, "shadow", 36);
    // 右上：小地圖（小）＋地名
    minimap(c, W - 150, 8, 142, 88, sc); text(c, place, W - 79, 108, 13, TEXT, "center");
    // 事件：畫面上方中央的橫幅
    toast(c, W / 2 - 130, 10, 260, sc === "town" ? "coin" : "ask", sc === "town" ? "賣出 3 件雜物，+45" : "發現了古碑");
  }

  // ======================= C：極簡純圖示 =======================
  function hudC(c, cols, rows, place, placeIcon, info) {
    const W = cols * T, H = rows * T, sc = info.scene;
    // 左上：頭像外圈就是血條（紅弧＝HP、藍弧＝法力）
    const px = 44, py = 44;
    c.lineCap = "butt";
    c.lineWidth = 6; c.strokeStyle = "#1a1410"; c.beginPath(); c.arc(px, py, 38, 0, TAU); c.stroke();
    c.strokeStyle = HP; c.beginPath(); c.arc(px, py, 38, Math.PI * 0.6, Math.PI * 0.6 + Math.PI * 0.82 * 0.9); c.stroke();
    c.strokeStyle = MP; c.beginPath(); c.arc(px, py, 38, Math.PI * 1.5 + 0.1, Math.PI * 1.5 + 0.1 + Math.PI * 0.82 * 0.6); c.stroke();
    portrait(c, px, py, 60, 0); badge(c, px, py + 36, "4", "#3a5ad0");
    [[1, 0.7], [0, 0.95]].forEach(([idx, hp], i) => { const x = 98 + i * 40; portrait(c, x, 30, 32, idx, hp > 0.8 ? "#5ad06a" : "#e8bb48"); });
    // 右上：小地圖收成羅盤圖示＋時間天氣圖示
    iconBtn(c, W - 50, 8, "map", 42, { key: "M" }); iconBtn(c, W - 96, 8, sc === "town" ? "fog" : "rain", 42); iconBtn(c, W - 142, 8, "sun", 42);
    // 右下：功能圖示直排
    ["bag", "book", "growth", "scroll", "shadow", "notes", "boots"].forEach((ic, i) => iconBtn(c, W - 50, 120 + i * 48, ic, 42, { badge: ic === "notes" ? "3" : ic === "book" ? "2" : null, on: ic === "boots" }));
    // 打開的面板示意：背包從右邊滑出（點了才開）
    const pw = 300, pxl = W - 60 - pw, pyl = 120;
    box(c, pxl, pyl, pw, 230, "rgba(24,20,16,0.93)", GOLD, 2, 10);
    I.bag(c, pxl + 18, pyl + 18, 16); text(c, "背包", pxl + 34, pyl + 18, 13); text(c, "×", pxl + pw - 16, pyl + 18, 14, DIM, "center");
    chip(c, pxl + 120, pyl + 7, "coin", "1,240", 84); chip(c, pxl + 208, pyl + 7, "token", "35", 80);
    const items = ["jar", "sword", "scroll", "ration", "bulb", "coin", "map", "rank", "jar", "ration"];
    for (let k = 0; k < 20; k++) { const ix = pxl + 14 + (k % 5) * 56, iy = pyl + 40 + Math.floor(k / 5) * 46; box(c, ix, iy, 48, 40, "rgba(255,255,255,0.05)", "rgba(200,168,104,0.45)", 1.2, 6); if (k < items.length) I[items[k]](c, ix + 24, iy + 20, 22); }
    // 地名只在進畫面時淡入一次
    text(c, place, W / 2, 30, 20, TEXT, "center");
  }

  return { hudA, hudB, hudC, I, text, bar, portrait, badge, iconBtn, chip, toast, PANEL, GOLD, DIM, HP, MP };
})();
