// rgMarks.js：RG 段戰場標記樣張（畫圖 agent，2026-11-13；PhaseRG計畫.md 第 5 節、05 5.7、09 9.6.6）。
// 第 2 版（2026-11-13，審查 M1、可修 1～7 與美術 PM 決定）。六項：被瞄準標記（準星）、瞄準線、落空／被擋下／被打斷浮字、盾兵擋住的小盾＋連結、可疑痕跡、看那一格一眼。
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
  /** 準星圓心到三角外框下緣的距離（三角尖 R＋6.4＝12.6，外框再 1）。 */
  const RETICLE_BELOW = 13.6;
  /** 準星圓心相對格子中心的 y（標準人形、沒有頭飾）：頭頂往上 4（空隙）再 13.6×k。第 2 版：頭頂改用「含頭飾」的最高點（樣張頁 topOf）。 */
  const RETICLE_DY = HEAD_TOP - 4 - RETICLE_BELOW;

  // =====================================================================
  // 2. 瞄準線：弓手胸口 → 準星，2 px 實線段的虛線（膠囊形、每段自己包外框色），往目標流動。
  //    和移動路徑線分開：路徑是 4 px、整條連續的黑底線、沿格子中心走直角＋圓角、每格中心一個點、畫在單位之上；
  //    瞄準線是 2 px、斜的直線、沒有點、只有每一段自己有細外框、畫在單位之下（每排的 frames 層）。
  // =====================================================================
  /**
   * a＝弓手胸口、b＝終點（準星圓心）；o＝{ pal, ms（流動時間）, blockAt（0～1，被擋的位置，沒有＝不擋）, k（畫面下限放大）, endGap, start, avoid }。
   * 第 2 版：起點從胸口往目標 0.4 格（出了身體）；若那一點還在 avoid 的圓裡（弓手的蓄力徽章：半徑 10＋2），沿線往前推到出了圓再起。
   */
  function lockLine(ctx, a, b, o = {}) {
    const p = PAL[o.pal ?? "A"], k = o.k ?? 1;
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy);
    if (len < 1) return;
    const ux = dx / len, uy = dy / len;
    const end = len - (o.endGap ?? 11 * (o.rk ?? 1)); // 終點停在準星外緣
    let start = o.start ?? 0.4 * T;
    for (const c of o.avoid ?? []) while (start < end && Math.hypot(a.x + ux * start - c.x, a.y + uy * start - c.y) < c.r) start += 0.5;
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
    /* 第 2 版（必修 M1）：拿掉盾後的人頭（1 倍讀成燈泡、冰淇淋），鳶形盾放大撐滿 14×14（寬 11.2、高 12.8）；「來源是人」交給盾兵連結（終點接在盾的側邊）。 */
    const shield = () => { ctx.beginPath(); ctx.moveTo(-5.6, -5.1); ctx.quadraticCurveTo(0, -6.8, 5.6, -5.1); ctx.lineTo(5.6, -0.2); ctx.quadraticCurveTo(5.1, 4.4, 0, 6.85); ctx.quadraticCurveTo(-5.1, 4.4, -5.6, -0.2); ctx.closePath(); };
    if (kind === "unit") {
      // 盾：外框 1、鋼色、右半暗面、左側亮條
      shield(); ctx.lineWidth = 2; ctx.strokeStyle = INK; ctx.stroke(); ctx.fillStyle = STEEL; ctx.fill();
      ctx.save(); shield(); ctx.clip(); ctx.fillStyle = STEEL_D; ctx.fillRect(0.7, -8, 8, 16); ctx.fillStyle = "rgba(255,255,255,0.8)"; ctx.fillRect(-4.2, -3.6, 1.4, 5.4); ctx.restore();
      // 盾心金釘
      ctx.beginPath(); ctx.arc(0.35, -0.5, 1.5, 0, TAU); ctx.fillStyle = "#e8bb48"; ctx.fill();
    } else {
      // 矮牆（兩層磚、上緣亮）：半掩護物件版，未採用（2026-11-13 美術 PM：半掩護小圖示這段不做），留作備用
      const wall = () => { ctx.beginPath(); ctx.rect(-6, -1.5, 12, 7.5); };
      wall(); ctx.lineWidth = 2; ctx.strokeStyle = INK; ctx.stroke(); ctx.fillStyle = "#8a7e72"; ctx.fill();
      ctx.fillStyle = "#b0a496"; ctx.fillRect(-6, -1.5, 12, 2);
      ctx.strokeStyle = "#4e443c"; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(-6, 2.3); ctx.lineTo(6, 2.3); ctx.moveTo(-1.5, 0.5); ctx.lineTo(-1.5, 2.3); ctx.moveTo(3, 2.3); ctx.lineTo(3, 6); ctx.moveTo(-3.8, 2.3); ctx.lineTo(-3.8, 6); ctx.stroke();
    }
    ctx.restore();
  }
  /** 小盾中心到下緣外框的距離（盾尖 6.85＋外框 1）。 */
  const CHIP_BELOW = 7.85;
  /** 小盾中心相對格子中心的 y（標準人形、沒有頭飾）：頭頂往上 2 再 7.85×k。 */
  const CHIP_DY = HEAD_TOP - 2 - CHIP_BELOW;
  /**
   * 盾兵 → 小盾的淡連結（第 2 版）：一排米白小點（點線，不是虛線、不流動），起點在盾兵胸口、終點的圓點貼在小盾的側邊，
   * 讓盾「掛」在盾兵的點線上（「來源是人」由連結交代）。畫在頭頂標記層。
   * a＝盾兵格子中心、b＝被保護者格子中心、chip＝小盾中心；o.k＝小盾的畫面下限放大。
   * 走法：二次曲線，從盾兵那一側繞到小盾的側邊，不穿過被保護者的身體：
   *   side＝盾兵在被保護者的東（＋1）或西（−1）；同一直行（上下相鄰）時取東（＋1，蓄力徽章在西邊）。
   *   起點 A：同一直行＝盾兵胸口往外側 0.46 格（出了盾兵的身體與被保護者的 HP 條）；其他＝盾兵胸口往被保護者 0.25 格。
   *   終點 E：小盾中心＋(side × 8.1k, −2.5k)（盾的直邊中段，圓點貼著盾的外框）。
   *   控制點 C：(b.x＋side × max(1 格, |A.x − b.x|), E.y)：曲線先往上、在被保護者身體外側爬到頭頂高度，再橫著接到盾。
   *     盾兵在正北（同一直行、在上）：C＝(b.x＋side × 0.75 格, (A.y＋E.y)÷2)，只輕輕往外彎（小盾就在盾兵腳邊）。
   */
  function coverLink(ctx, a, b, chip, o = {}) {
    const k = o.k ?? 1, y0 = -0.3 * T, same = Math.abs(a.x - b.x) < 1, side = same ? 1 : Math.sign(a.x - b.x);
    let A;
    if (same) A = { x: a.x + side * 0.46 * T, y: a.y + y0 };
    else { const d = Math.hypot(b.x - a.x, b.y - a.y) || 1; A = { x: a.x + ((b.x - a.x) / d) * 0.25 * T, y: a.y + y0 + ((b.y - a.y) / d) * 0.25 * T }; }
    const E = { x: chip.x + side * 8.1 * k, y: chip.y - 2.5 * k };
    const C = same && a.y < b.y ? { x: b.x + side * 0.75 * T, y: (A.y + E.y) / 2 } : { x: b.x + side * Math.max(T, Math.abs(A.x - b.x)), y: E.y }; // 盾兵在正北：小盾就在盾兵腳邊，只輕輕往外彎
    const at = (t) => ({ x: (1 - t) * (1 - t) * A.x + 2 * t * (1 - t) * C.x + t * t * E.x, y: (1 - t) * (1 - t) * A.y + 2 * t * (1 - t) * C.y + t * t * E.y });
    const N = 96, acc = [0]; let prev = at(0);
    for (let i = 1; i <= N; i++) { const q = at(i / N); acc.push(acc[i - 1] + Math.hypot(q.x - prev.x, q.y - prev.y)); prev = q; }
    const len = acc[N], n = Math.max(2, Math.round(len / (4.5 * k)));
    const byLen = (L) => { let i = 1; while (i < N && acc[i] < L) i++; const f = (L - acc[i - 1]) / Math.max(1e-6, acc[i] - acc[i - 1]); return at((i - 1 + f) / N); };
    ctx.save();
    for (let i = 0; i <= n; i++) {
      const q = byLen((len * i) / n), r = (i === 0 || i === n ? 2.1 : 1.3) * k;
      ctx.beginPath(); ctx.arc(q.x, q.y, r + 0.8, 0, TAU); ctx.fillStyle = "rgba(22,18,26,0.45)"; ctx.fill();
      ctx.beginPath(); ctx.arc(q.x, q.y, r, 0, TAU); ctx.fillStyle = "rgba(232,240,248,0.85)"; ctx.fill();
    }
    ctx.restore();
  }

  // =====================================================================
  // 5. 可疑痕跡：格子地面的一塊翻土（深土＋淺色碎粒）＋兩道細線（拉過的細繩、刮痕）＋右上的米白「？」小圓。
  //    不畫任何陷阱的形（沒有夾齒、沙漏、圈、陣營色）。已揭露的陷阱是：淡紅虛線橢圓＋深色圓盤＋陣營色圈＋元素色夾齒／沙漏＋右上紅「！」。
  // =====================================================================
  /**
   * (x0, y0)＝格子左上角。o.k＝「？」的畫面下限放大。第 2 版（可修 4）：拿掉淺色碎粒（像巧克力豆餅乾），
   * 改成「左邊高起的一堆新土（凹凸的上緣亮、下緣暗）＋右下一個挖開的暗坑（近側坑緣亮）」，兩顆深色土塊濺在坑邊；細線與「？」保留。
   * gx, gy 保留參數（不用亂數，形固定）。
   */
  function trace(ctx, x0, y0, gx = 0, gy = 0, o = {}) {
    void gx; void gy;
    const cx = x0 + T / 2, cy = y0 + T / 2 + 4;
    ctx.save(); ctx.lineCap = "round"; ctx.lineJoin = "round";
    // 細線（先畫，根被土堆、坑蓋住＝從土裡伸出來）：左下、右上各一段，兩端小木樁
    const L0 = [x0 + 5, y0 + T - 9], L1 = [cx - 9, cy + 3], L2 = [cx + 9, cy + 2], L3 = [x0 + T - 6, y0 + 22];
    ctx.strokeStyle = "rgba(20,14,8,0.6)"; ctx.lineWidth = 2.2; for (const [a, b] of [[L0, L1], [L2, L3]]) { ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke(); }
    ctx.strokeStyle = "rgba(240,232,210,0.9)"; ctx.lineWidth = 1; for (const [a, b] of [[L0, L1], [L2, L3]]) { ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke(); }
    // 挖開的坑（右下）：暗橢圓，近側（下緣）坑唇亮、遠側（上緣）內壁更暗
    const hx = cx + 7, hy = cy + 4.5;
    ctx.beginPath(); ctx.ellipse(hx, hy, 8, 3.6, 0, 0, TAU); ctx.fillStyle = "rgba(74,54,34,0.9)"; ctx.fill();
    ctx.beginPath(); ctx.ellipse(hx, hy + 0.6, 6.6, 2.6, 0, 0, TAU); ctx.fillStyle = "rgba(18,11,6,0.95)"; ctx.fill();
    ctx.beginPath(); ctx.ellipse(hx, hy + 0.2, 7.6, 3.3, 0, 0.12 * Math.PI, 0.88 * Math.PI); ctx.strokeStyle = "rgba(222,196,150,0.85)"; ctx.lineWidth = 1.1; ctx.stroke();
    // 土堆（左上、左邊高）：凹凸三個鼓包的上緣，下緣微彎；坑的左端被它壓住
    const top = () => { ctx.moveTo(cx - 15, cy + 4); ctx.quadraticCurveTo(cx - 17, cy - 2, cx - 11.5, cy - 4); ctx.quadraticCurveTo(cx - 9, cy - 10.5, cx - 3.5, cy - 7.5); ctx.quadraticCurveTo(cx + 1.5, cy - 7, cx + 1.5, cy - 2); ctx.quadraticCurveTo(cx + 5, cy - 1, cx + 4.5, cy + 3.5); };
    const heap = () => { ctx.beginPath(); top(); ctx.quadraticCurveTo(cx - 5, cy + 8, cx - 15, cy + 4); ctx.closePath(); };
    heap(); ctx.fillStyle = "rgba(128,96,62,0.97)"; ctx.fill();
    ctx.save(); heap(); ctx.clip();
    ctx.fillStyle = "rgba(46,32,18,0.6)"; ctx.beginPath(); ctx.ellipse(cx - 4, cy + 7, 14, 4.8, 0, 0, TAU); ctx.fill(); // 下緣暗
    ctx.strokeStyle = "rgba(232,208,164,0.85)"; ctx.lineWidth = 1.8; ctx.translate(0.4, 1.1); ctx.beginPath(); top(); ctx.stroke(); // 上緣亮
    ctx.restore();
    heap(); ctx.strokeStyle = "rgba(20,14,8,0.75)"; ctx.lineWidth = 1.2; ctx.stroke();
    // 濺出的兩顆深色土塊（坑的右邊）
    for (const [x, y, rr] of [[cx + 17, cy + 1.5, 1.6], [cx + 15.5, cy + 8.5, 1.3]]) { ctx.beginPath(); ctx.arc(x, y, rr + 0.6, 0, TAU); ctx.fillStyle = "rgba(20,14,8,0.5)"; ctx.fill(); ctx.beginPath(); ctx.arc(x, y, rr, 0, TAU); ctx.fillStyle = "#6a4c30"; ctx.fill(); }
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
    const look = t < 60 ? 0 : t < 150 ? (t - 60) / 90 : 1; // 第 2 版（可修 5）：瞳孔 60～150 ms 轉過去
    const sight = t < 150 ? 0 : t < 240 ? (t - 150) / 90 : 1; // 視線 150～240 ms 冒出
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
  /** 泡泡中心到尾巴尖外框的距離（尾巴尖 7＋外框 1）。 */
  const GLANCE_BELOW = 8;
  /** 泡泡中心相對格子中心的 y（標準人形、沒有頭飾）：頭頂往上 2 再 8×k。 */
  const GLANCE_DY = HEAD_TOP - 2 - GLANCE_BELOW;

  return { T, INK, FEET, HEAD_TOP, PAL, BLOCKED, TIMING, FLOAT, blinkPhase, reticle, RETICLE_DY, RETICLE_BELOW, lockLine, blockStop, floatFrame, floatText, coverChip, CHIP_DY, CHIP_BELOW, coverLink, trace, glance, glanceFrame, GLANCE_DY, GLANCE_BELOW, seedRand };
})();
