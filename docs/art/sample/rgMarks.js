// rgMarks.js：RG 段戰場標記樣張（畫圖 agent，2026-11-13；PhaseRG計畫.md 第 5 節、05 5.7、09 9.6.6）。
// 六項：被瞄準標記（準星）、瞄準線、落空／被擋下／被打斷浮字、盾兵擋住的小盾＋連結、可疑痕跡、看那一格一眼。
// 座標一律是模型像素（一格 T＝48，client/src/battle/geometry.ts TILE_SIZE）；呼叫端先把 ctx 換到地圖縮放。
// 確定性：不用 Math.random；時間一律由呼叫端傳入（毫秒）。只讀別的畫法檔，不改它們。
window.RGMarks = (() => {
  const TAU = Math.PI * 2;
  const T = 48;
  const INK = "#16121a"; // Q 版外框色（qDoll／qIcons 同一色）
  const FEET = T * 0.23; // unitSprite.ts FEET
  /** 人形頭頂（相對格子中心，往上為負）：unitSprite.ts unitTopY＝FEET − DOLL_HEAD_TOP(38) × (T/52) × DOLL_SCALE(1.06)。浮動字、敵群眼睛都從這裡起算。 */
  const HEAD_TOP = FEET - 38 * (T / 52) * 1.06;

  /** 兩案配色。A＝強招紫（telegraph.ts 的「蓄」0xb06bff 同一色）；B＝警示紅。 */
  const PAL = {
    A: { main: "#b06bff", hi: "#e9d8ff", deep: "#5a2a9a", name: "A 強招紫" },
    B: { main: "#ff4646", hi: "#ffd2c8", deep: "#8a1c1c", name: "B 警示紅" },
  };
  /** 被擋住之後的那一段、被擋時的準星：zone_neutral 灰（glossary.ts HIGHLIGHT.zone_neutral 0xb0b8c4）。 */
  const BLOCKED = "#b0b8c4";

  // ---------------- 時間參數（移植規格） ----------------
  const TIMING = {
    blinkMs: 900, // 準星一個週期：亮 520 ms ＋ 收 380 ms（2 段）
    blinkOnMs: 520,
    flowPxPerS: 24, // 瞄準線流速：每秒往目標走 24 模型像素（一個虛線週期 11 px ≈ 0.46 秒）
    glanceMs: 600, // 看一眼整段
  };
  /** 準星的狀態：0＝亮（原大）、1＝收（縮 0.86、外圈變細、內亮弧拿掉）。 */
  const blinkPhase = (ms) => ((((ms % TIMING.blinkMs) + TIMING.blinkMs) % TIMING.blinkMs) < TIMING.blinkOnMs ? 0 : 1);

  // ---------------- 小工具 ----------------
  function seedRand(seed) { let s = seed >>> 0 || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }
  const rgba = (hex, a) => { const n = parseInt(hex.slice(1, 7), 16); return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`; };

  // =====================================================================
  // 1. 被瞄準標記：Q 版準星（空心圓＋三根往外的刻度＋朝下的實心三角指著頭）
  //    20×20（一格 0.4）；外框色 #16121a 粗 1 px（先描粗的外框色、再描色）。中心不放點、不打叉：
  //    和「蓄力中」狀態（圓＋實心點）、「被標記」狀態（圓＋叉）分開。
  // =====================================================================
  /** (x, y)＝準星圓心；o＝{ pal, phase(0|1), blocked, k（畫面下限的反向放大）, alpha }。 */
  function reticle(ctx, x, y, o = {}) {
    const p = PAL[o.pal ?? "A"], k = o.k ?? 1, dim = o.phase === 1 && !o.blocked;
    const col = o.blocked ? BLOCKED : p.main;
    const s = dim ? 0.86 : 1;
    const R = 6.2, lw = dim ? 2.2 : 2.6;
    ctx.save(); ctx.translate(x, y); ctx.scale(k * s, k * s); ctx.globalAlpha = o.alpha ?? 1;
    ctx.lineCap = "round"; ctx.lineJoin = "round";
    const ticks = [[-1, 0], [1, 0], [0, -1]];
    const tri = () => { ctx.beginPath(); ctx.moveTo(-4.2, R + 1.6); ctx.lineTo(4.2, R + 1.6); ctx.lineTo(0, R + 6.4); ctx.closePath(); };
    const shape = () => {
      ctx.beginPath(); ctx.arc(0, 0, R, 0, TAU);
      for (const [dx, dy] of ticks) { ctx.moveTo(dx * (R - 1.6), dy * (R - 1.6)); ctx.lineTo(dx * (R + 3.4), dy * (R + 3.4)); }
    };
    // 外框（粗 2 個單位＝兩側各 1）
    ctx.strokeStyle = INK; ctx.lineWidth = lw + 2; shape(); ctx.stroke();
    tri(); ctx.lineWidth = 2; ctx.stroke(); ctx.fillStyle = INK; ctx.fill();
    // 本色
    ctx.strokeStyle = col; ctx.lineWidth = lw; shape(); ctx.stroke();
    tri(); ctx.fillStyle = col; ctx.fill();
    // 亮面：圓的左上一段白 80% 細弧（只在「亮」那一段）
    if (!dim && !o.blocked) { ctx.strokeStyle = "rgba(255,255,255,0.8)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(0, 0, R, Math.PI * 1.08, Math.PI * 1.42); ctx.stroke(); }
    ctx.restore();
  }
  /** 準星圓心相對格子中心的 y：頭頂往上 3（空隙）再 10（半個準星）。 */
  const RETICLE_DY = HEAD_TOP - 3 - 10;

  // =====================================================================
  // 2. 瞄準線：弓手胸口 → 準星，2 px 實線段的虛線（膠囊形、每段自己包外框色），往目標流動。
  //    和移動路徑線分開：路徑是 4 px、整條連續的黑底線、沿格子中心走直角＋圓角、每格中心一個點、畫在單位之上；
  //    瞄準線是 2 px、斜的直線、沒有點、只有每一段自己有細外框、畫在單位之下（每排的 frames 層）。
  // =====================================================================
  /** a＝起點（弓手胸口）、b＝終點（準星圓心）；o＝{ pal, ms（流動時間）, blockAt（0～1，被擋的位置，沒有＝不擋）, k（畫面下限放大）, endGap }。 */
  function lockLine(ctx, a, b, o = {}) {
    const p = PAL[o.pal ?? "A"], k = o.k ?? 1;
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy);
    if (len < 1) return;
    const ux = dx / len, uy = dy / len;
    const start = 6, end = len - (o.endGap ?? 11 * (o.rk ?? 1)); // 起點離弓手胸口 6、終點停在準星外緣
    const dash = 4 * k, gap = 7 * k, per = dash + gap;
    const off = -(((o.ms ?? 0) / 1000) * TIMING.flowPxPerS) * k; // 負 offset＝虛線往終點走
    const cut = o.blockAt == null ? end : Math.max(start, Math.min(end, o.blockAt * len));
    const seg = (s0, s1) => { ctx.beginPath(); ctx.moveTo(a.x + ux * s0, a.y + uy * s0); ctx.lineTo(a.x + ux * s1, a.y + uy * s1); };
    ctx.save(); ctx.lineCap = "round";
    // 前段：本色、流動
    ctx.setLineDash([dash, gap]); ctx.lineDashOffset = off - start;
    seg(start, cut); ctx.strokeStyle = rgba(INK, 0.85); ctx.lineWidth = 2 * k + 2; ctx.stroke();
    seg(start, cut); ctx.strokeStyle = p.main; ctx.lineWidth = 2 * k; ctx.stroke();
    if (cut < end) {
      // 被擋：擋住的人之後改灰、點線、不流動
      ctx.setLineDash([1.5 * k, 5 * k]); ctx.lineDashOffset = 0;
      seg(cut + 4, end); ctx.strokeStyle = rgba(INK, 0.6); ctx.lineWidth = 2 * k + 1.5; ctx.stroke();
      seg(cut + 4, end); ctx.strokeStyle = BLOCKED; ctx.lineWidth = 2 * k; ctx.stroke();
    }
    ctx.restore();
    void per;
  }
  /** 被擋的斷點記號（畫在最上層、擋住的人身前）：本色的短橫槓＋灰的短橫槓，垂直於線（像箭被盾面截住的「⊣」）。 */
  function blockStop(ctx, at, dir, o = {}) {
    const p = PAL[o.pal ?? "A"], k = o.k ?? 1, nx = -dir.y, ny = dir.x, h = 5.5 * k;
    ctx.save(); ctx.lineCap = "round";
    const bar = (cx, cy) => { ctx.beginPath(); ctx.moveTo(cx - nx * h, cy - ny * h); ctx.lineTo(cx + nx * h, cy + ny * h); };
    bar(at.x, at.y); ctx.strokeStyle = INK; ctx.lineWidth = 2.6 * k + 2; ctx.stroke(); ctx.strokeStyle = p.main; ctx.lineWidth = 2.6 * k; ctx.stroke();
    ctx.restore();
  }

  // =====================================================================
  // 3. 落空／被擋下／被打斷：沿用傷害浮字（20 px 粗體、黑描邊 4、彈一下再飄，uiAnim.ts floatFrame）。只換字與色。
  // =====================================================================
  const FLOAT = {
    fizzle: { text: "落空", color: "#ffe066", at: "caster" }, // tone good（同「格擋」「攔截」）；放在弓手頭上（目標隱蔽時不洩漏位置）
    blocked: { text: "被擋下", color: "#ffe066", at: "blocker" }, // 放在擋住的那個隊友頭上
    interrupted: { text: "被打斷", color: "#ffe066", at: "caster" }, // 放在弓手頭上
  };
  /** uiAnim.ts floatFrame（原樣）：p＝0～1。 */
  function floatFrame(p, big = false) {
    const rest = big ? 1.15 : 1, q = Math.max(0, Math.min(1, p)), POP = 0.22;
    const bounce = (u) => { if (u >= 1) return 1; const c = 2.2, v = u - 1; return 1 + (c + 1) * v * v * v + c * v * v; };
    const alpha = q < 0.7 ? 1 : 1 - (q - 0.7) / 0.3, rise = Math.min(1, q * 1.5) * (big ? 22 : 16), from = big ? 0.5 : 0.6;
    return { alpha, rise, scale: q < POP ? from + (rest - from) * bounce(q / POP) : rest };
  }
  /** 浮字：(x, headY)＝格子中心 x、頭頂 y（模型像素）；字的下緣貼頭頂上方 2（FLOAT_HEAD_GAP），往上飄。 */
  function floatText(ctx, text, x, headY, p, color = "#ffe066") {
    const f = floatFrame(p), px = 20;
    ctx.save(); ctx.globalAlpha = f.alpha; ctx.translate(x, headY - 2 - px * 0.5 - f.rise); ctx.scale(f.scale, f.scale);
    ctx.font = `700 ${px}px 'Noto Sans TC','Microsoft JhengHei',sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.lineJoin = "round"; ctx.strokeStyle = "#000"; ctx.lineWidth = 4; ctx.strokeText(text, 0, 0); ctx.fillStyle = color; ctx.fillText(text, 0, 0);
    ctx.restore();
  }

  // =====================================================================
  // 4. 盾兵擋住：被保護者頭上 14×14 小盾（盾後露出半顆米白人頭＝「有人拿著」）＋盾兵與被保護者之間的淡點線。
  //    同族的「物件掩護」（矮牆磚塊）一起畫，給美術 PM 比（遊戲現在沒有半掩護圖示，只有預覽文字）。
  // =====================================================================
  const STEEL = "#c3ccd6", STEEL_D = "#7d8794", CREAM = "#f2e6c8", CREAM_D = "#c8b894";
  /** (x, y)＝圖示中心；kind＝"unit"（盾兵）｜"object"（物件，提案）。 */
  function coverChip(ctx, x, y, kind = "unit", o = {}) {
    const k = o.k ?? 1;
    ctx.save(); ctx.translate(x, y); ctx.scale(k, k); ctx.lineJoin = "round";
    const shield = () => { ctx.beginPath(); ctx.moveTo(-4.6, -3.2); ctx.quadraticCurveTo(0, -4.6, 4.6, -3.2); ctx.lineTo(4.6, 0.8); ctx.quadraticCurveTo(4.2, 4.6, 0, 6.6); ctx.quadraticCurveTo(-4.2, 4.6, -4.6, 0.8); ctx.closePath(); };
    if (kind === "unit") {
      // 人頭（盾的左上後方）
      ctx.beginPath(); ctx.arc(-3.4, -5.2, 2.9, 0, TAU); ctx.lineWidth = 2; ctx.strokeStyle = INK; ctx.stroke(); ctx.fillStyle = CREAM; ctx.fill();
      // 盾：外框 1、鋼色、右半暗面、中線亮
      shield(); ctx.lineWidth = 2; ctx.strokeStyle = INK; ctx.stroke(); ctx.fillStyle = STEEL; ctx.fill();
      ctx.save(); shield(); ctx.clip(); ctx.fillStyle = STEEL_D; ctx.fillRect(0.6, -6, 6, 14); ctx.fillStyle = "rgba(255,255,255,0.8)"; ctx.fillRect(-3.4, -2.6, 1.2, 4.2); ctx.restore();
      // 盾心金釘
      ctx.beginPath(); ctx.arc(0.3, 0.6, 1.25, 0, TAU); ctx.fillStyle = "#e8bb48"; ctx.fill();
    } else {
      // 矮牆（兩層磚、上緣亮）
      const wall = () => { ctx.beginPath(); ctx.rect(-6, -1.5, 12, 7.5); };
      wall(); ctx.lineWidth = 2; ctx.strokeStyle = INK; ctx.stroke(); ctx.fillStyle = "#8a7e72"; ctx.fill();
      ctx.fillStyle = "#b0a496"; ctx.fillRect(-6, -1.5, 12, 2);
      ctx.strokeStyle = "#4e443c"; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(-6, 2.3); ctx.lineTo(6, 2.3); ctx.moveTo(-1.5, 0.5); ctx.lineTo(-1.5, 2.3); ctx.moveTo(3, 2.3); ctx.lineTo(3, 6); ctx.moveTo(-3.8, 2.3); ctx.lineTo(-3.8, 6); ctx.stroke();
    }
    ctx.restore();
  }
  /** 小盾圓心相對格子中心的 y：頭頂往上 2 再 7。 */
  const CHIP_DY = HEAD_TOP - 2 - 7;
  /** 盾兵 → 被保護者的淡連結：兩人胸口（格子中心往上 0.3 格）之間一排米白小點（點線，不是虛線），兩端各一個小圓；畫在單位之上（頭頂標記那一層）。 */
  function coverLink(ctx, a, b, o = {}) {
    const k = o.k ?? 1, y0 = o.y0 ?? -0.3 * T; /* 第 2 版：胸口高度、畫在頭頂標記層（第 1 版在腳邊、單位之下，上下相鄰時整條被盾兵身體蓋掉） */
    const d0 = Math.hypot(b.x - a.x, b.y - a.y) || 1, ux = (b.x - a.x) / d0, uy = (b.y - a.y) / d0; /* 只畫兩人之間那一段：盾兵端往前 0.25 格、被保護者端往回 0.45 格（第 2 版第 1 次整條穿過弓手的臉） */
    const A = { x: a.x + ux * 0.25 * T, y: a.y + y0 + uy * 0.25 * T }, B = { x: b.x - ux * 0.45 * T, y: b.y + y0 - uy * 0.45 * T };
    const len = Math.hypot(B.x - A.x, B.y - A.y), n = Math.max(2, Math.round(len / (4 * k)));
    ctx.save();
    for (let i = 0; i <= n; i++) {
      const t = i / n, x = A.x + (B.x - A.x) * t, y = A.y + (B.y - A.y) * t, r = (i === 0 || i === n ? 2.1 : 1.3) * k;
      ctx.beginPath(); ctx.arc(x, y, r + 0.8, 0, TAU); ctx.fillStyle = "rgba(22,18,26,0.45)"; ctx.fill();
      ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fillStyle = "rgba(232,240,248,0.85)"; ctx.fill();
    }
    ctx.restore();
  }

  // =====================================================================
  // 5. 可疑痕跡：格子地面的一塊翻土（深土＋淺色碎粒）＋兩道細線（拉過的細繩、刮痕）＋右上的米白「？」小圓。
  //    不畫任何陷阱的形（沒有夾齒、沙漏、圈、陣營色）。已揭露的陷阱是：淡紅虛線橢圓＋深色圓盤＋陣營色圈＋元素色夾齒／沙漏＋右上紅「！」。
  // =====================================================================
  /** (x0, y0)＝格子左上角；gx, gy 決定碎粒的位置（確定性）。o.k＝「？」的畫面下限放大。 */
  function trace(ctx, x0, y0, gx = 0, gy = 0, o = {}) {
    const r = seedRand(gx * 7919 + gy * 104729 + 17), cx = x0 + T / 2, cy = y0 + T / 2 + 4;
    ctx.save();
    // 翻土：不規則的一塊（10 個頂點），深土色 55%＋外緣淡
    const pts = [];
    for (let i = 0; i < 10; i++) { const a = (i / 10) * TAU, rr = 0.78 + r() * 0.3; pts.push([cx + Math.cos(a) * 14 * rr, cy + Math.sin(a) * 10.5 * rr]); } /* 第 2 版：圓一點（第 1 版長橢圓＋斜線像葉子、木片） */
    ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath();
    ctx.fillStyle = "rgba(118,90,60,0.78)"; ctx.fill(); ctx.strokeStyle = "rgba(20,14,8,0.55)"; ctx.lineWidth = 1.2; ctx.stroke();
    ctx.save(); ctx.clip(); ctx.fillStyle = "rgba(60,42,26,0.55)"; ctx.beginPath(); ctx.ellipse(cx + 3, cy + 4, 15, 6, 0, 0, TAU); ctx.fill(); ctx.restore(); /* 翻土：淺色新土＋下半一層深土（翻起來的那一面） */
    // 土塊與碎粒（深的鼓包＋淺的碎粒）
    for (let i = 0; i < 4; i++) { const x = cx - 9 + r() * 18, y = cy - 4 + r() * 7; ctx.beginPath(); ctx.ellipse(x, y, 2.6, 1.7, 0, 0, TAU); ctx.fillStyle = "#3a2a1c"; ctx.fill(); ctx.beginPath(); ctx.ellipse(x - 0.6, y - 0.6, 1.3, 0.8, 0, 0, TAU); ctx.fillStyle = "rgba(200,176,140,0.55)"; ctx.fill(); }
    for (let i = 0; i < 9; i++) { const x = cx - 14 + r() * 28, y = cy - 7 + r() * 14; ctx.fillStyle = "rgba(214,196,160,0.8)"; ctx.fillRect(x, y, 1.4, 1.2); }
    // 細線：一條拉直的淺色細線從土裡斜伸出去、兩端各一個小木樁（1 px；不穿過土塊中間，第 1 版穿過中間像葉脈）
    ctx.lineCap = "round"; const L0 = [x0 + 5, y0 + T - 9], L1 = [cx - 9, cy + 4], L2 = [cx + 10, cy - 3], L3 = [x0 + T - 6, y0 + 22];
    ctx.strokeStyle = "rgba(20,14,8,0.6)"; ctx.lineWidth = 2.2; for (const [a, b] of [[L0, L1], [L2, L3]]) { ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke(); }
    ctx.strokeStyle = "rgba(240,232,210,0.9)"; ctx.lineWidth = 1; for (const [a, b] of [[L0, L1], [L2, L3]]) { ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke(); }
    for (const [px, py] of [L0, L3]) { ctx.fillStyle = INK; ctx.fillRect(px - 1.6, py - 3.2, 3.2, 4.4); ctx.fillStyle = "#8a6440"; ctx.fillRect(px - 0.9, py - 2.5, 1.8, 3); }
    // 「？」小圓：右上（x0+T−11, y0+11），半徑 6；米白底、外框色 1、深褐「？」
    const k = o.k ?? 1, qx = x0 + T - 11, qy = y0 + 11;
    ctx.save(); ctx.translate(qx, qy); ctx.scale(k, k);
    ctx.beginPath(); ctx.arc(0, 0, 6, 0, TAU); ctx.lineWidth = 2; ctx.strokeStyle = INK; ctx.stroke(); ctx.fillStyle = CREAM; ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.8)"; ctx.beginPath(); ctx.arc(-2.4, -2.6, 1.2, 0, TAU); ctx.fill();
    ctx.fillStyle = "#3a2410"; ctx.font = "900 10px 'Noto Sans TC','Microsoft JhengHei',sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText("?", 0.2, 0.8);
    ctx.restore();
    ctx.restore();
  }

  // =====================================================================
  // 6. 看那一格一眼：頭上 14×14 的米白小泡泡（外框色 1、尾巴朝下），裡面兩顆直立的深色瞳孔（👀 的雙點，不用 emoji 字型），
  //    瞳孔往那一格的方向移；泡泡外朝那一格冒兩道短視線。0.6 秒：彈出 → 瞳孔轉過去 → 視線 → 淡出。
  // =====================================================================
  /** 0～600 ms 的樣子：{ scale, alpha, look（瞳孔移動 0～1）, sight（視線 0～1） }。 */
  function glanceFrame(ms) {
    const t = Math.max(0, Math.min(TIMING.glanceMs, ms));
    const scale = t < 90 ? 0.6 + 0.5 * (t / 90) : t < 150 ? 1.1 - 0.1 * ((t - 90) / 60) : 1;
    const look = t < 120 ? 0 : t < 240 ? (t - 120) / 120 : 1;
    const sight = t < 240 ? 0 : t < 360 ? (t - 240) / 120 : 1;
    const alpha = t < 480 ? 1 : 1 - (t - 480) / 120;
    return { scale, alpha, look, sight };
  }
  /** (x, y)＝泡泡中心；dir＝{x, y} 往那一格的單位向量；ms＝0～600。 */
  function glance(ctx, x, y, dir, ms, o = {}) {
    const f = glanceFrame(ms), k = (o.k ?? 1) * f.scale;
    if (f.alpha <= 0) return;
    const d = Math.hypot(dir.x, dir.y) || 1, ux = dir.x / d, uy = dir.y / d;
    ctx.save(); ctx.translate(x, y); ctx.scale(k, k); ctx.globalAlpha = f.alpha; ctx.lineJoin = "round";
    const body = () => { ctx.beginPath(); ctx.moveTo(-5, -5.5); ctx.lineTo(5, -5.5); ctx.quadraticCurveTo(7, -5.5, 7, -3.5); ctx.lineTo(7, 2); ctx.quadraticCurveTo(7, 4, 5, 4); ctx.lineTo(2, 4); ctx.lineTo(0, 7); ctx.lineTo(-2, 4); ctx.lineTo(-5, 4); ctx.quadraticCurveTo(-7, 4, -7, 2); ctx.lineTo(-7, -3.5); ctx.quadraticCurveTo(-7, -5.5, -5, -5.5); ctx.closePath(); };
    body(); ctx.lineWidth = 2; ctx.strokeStyle = INK; ctx.stroke(); ctx.fillStyle = "#e8d6a8"; ctx.fill(); /* 泡泡底：暖米色（眼白要比它亮才分得出兩隻眼） */
    // 兩隻眼（👀）：純白直立眼白、外框色 0.8；瞳孔深色，往那一格移到眼白邊上（最多橫 1.2、直 1.4）。第 1 版只有兩顆黑橢圓在白泡泡裡，像骷髏、鬼，改成有眼白的兩隻眼
    const mx = ux * 1.2 * f.look, my = uy * 1.4 * f.look;
    for (const ex of [-2.7, 2.7]) {
      ctx.beginPath(); ctx.ellipse(ex, -0.8, 2.5, 3.1, 0, 0, TAU); ctx.lineWidth = 0.8; ctx.strokeStyle = INK; ctx.stroke(); ctx.fillStyle = "#ffffff"; ctx.fill();
      ctx.beginPath(); ctx.arc(ex + mx, -0.8 + my, 1.35, 0, TAU); ctx.fillStyle = "#1c1410"; ctx.fill();
    }
    // 視線：泡泡外、朝那一格的兩道短線
    if (f.sight > 0) {
      const bx = ux * 9.5, by = uy * 8 - 0.8, nx = -uy, ny = ux, L = 3.4 * f.sight;
      ctx.lineCap = "round";
      for (const s of [-1, 1]) {
        const sx = bx + nx * s * 2.4, sy = by + ny * s * 2.4;
        ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(sx + ux * L, sy + uy * L); ctx.strokeStyle = INK; ctx.lineWidth = 2.6; ctx.stroke(); ctx.strokeStyle = "#fff8e8"; ctx.lineWidth = 1.2; ctx.stroke();
      }
    }
    ctx.restore();
  }
  /** 泡泡中心相對格子中心的 y：頭頂往上 2 再 7（尾巴尖約在頭頂上 2）。 */
  const GLANCE_DY = HEAD_TOP - 2 - 7;

  return { T, INK, FEET, HEAD_TOP, PAL, BLOCKED, TIMING, FLOAT, blinkPhase, reticle, RETICLE_DY, lockLine, blockStop, floatFrame, floatText, coverChip, CHIP_DY, coverLink, trace, glance, glanceFrame, GLANCE_DY, seedRand };
})();
