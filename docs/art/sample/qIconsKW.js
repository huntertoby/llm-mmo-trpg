// qIconsKW.js：KW 段（Phase KW 第 3 節美術需求）——連擊、怒氣、專注、氣四個新關鍵字的美術樣張（畫圖 agent 2026-11-13）。
// 紀錄：docs/art/KW樣張.md；樣張頁：q-icons-kw.html；拍圖：tools/kw_shots.py。
// 五項：①關鍵字圓章圖樣（每個 A／B 兩案）②關鍵字色 ③創角關鍵字圖示（SVG，同 CreateIcons.tsx 的畫法）④HUD 層數計量（格子）⑤技能組裝列的條件部件「層數達 N」。
// 規則：圓章照第⑤b 批（qIconsKeywords.js：深色圓底混 28% 關鍵字色、外圈 1 裝置像素外框、沒有環、≤14px 只留一個主體、不包外框）；
//       條件部件照第④批（qIconsParts.js：±10 單位、18px 圓片、條件色環 #ffe9a8、「自身」＝右下米白小人形）。
// 這個檔**不改**任何既有畫法檔：圓章的底、外框、貼法直接呼叫 qIconsKeywords.js 的 geom／BOX、qIconsWeapons.js 的 blit；
//   條件部件在樣張頁才把兩案塞進 QIconsParts.CATS.condition（鍵帶 __kw 後綴，只在 q-icons-kw.html 裡），第④批的清單與指紋不動。
// 依賴（先載入）：qIcons.js、qIconsWeapons.js、qIconsSkills.js、qIconsParts.js、qIconsKeywords.js。
window.QIconsKW = (() => {
  const Q = window.QIcons, QW = window.QIconsWeapons, QS = window.QIconsSkills, QP = window.QIconsParts, K = window.QIconsKeywords;
  const { mix, f, rr, ci, el, poly, ln, starPts, halo, blank } = Q.H, TAU = Math.PI * 2, PI = Math.PI, OUT = Q.OUT;
  const CREAM = "#f2e6c8", GOLD = "#e8bb48", GOLD_L = "#fff6c8";
  const st = (c, col, w, fn, cap = "round") => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
  /** 人形（同 qIconsParts.js 的 bust，沒有匯出，照抄一筆不改）：圓頭加圓肩的半身，高約 15k。 */
  const bust = (c, col, x, y, k = 1) => { ci(c, col, x, y - 4.6 * k, 3.7 * k); f(c, col, () => { c.moveTo(x - 6.2 * k, y + 7 * k); c.quadraticCurveTo(x - 6.2 * k, y - 0.4 * k, x, y - 0.4 * k); c.quadraticCurveTo(x + 6.2 * k, y - 0.4 * k, x + 6.2 * k, y + 7 * k); c.closePath(); }); };

  // =====================================================================
  // ② 關鍵字色（推薦一組＋對照一組）。推薦組用 OKLab 距離挑：四個新色和既有 12 色、彼此之間，在正常、紅色弱、綠色弱、藍色弱（Machado 2009，嚴重度 0.6）下最近的距離都 ≥ 8（既有 12 色彼此最近只有 2.0～4.4）。
  // =====================================================================
  const COLOR = { combo_point: "#ff3d8b", fury: "#df2046", focus: "#476deb", ki: "#29e0bc" };
  /** 對照組（第一直覺的配色）：連擊鋼白、怒氣亮紅、專注藍紫、氣青綠——和既有色撞得較多，頁面 color 段並排給美術 PM 看。 */
  const COLOR_ALT = { combo_point: "#f0f4ff", fury: "#ff2f4f", focus: "#5a62ff", ki: "#30d0b8" };
  const ZH = { combo_point: "連擊", fury: "怒氣", focus: "專注", ki: "氣" };
  const KEYS = Object.keys(ZH);
  /** 每個關鍵字圖樣自己的三階色（本色、亮一階、白芯／最亮）：由推薦色推出來，深底上平均亮度 ≥100。 */
  const TONE = {
    combo_point: ["#ff3d8b", "#ff9cc4", "#ffffff"],
    fury: ["#df2046", "#ff7a8c", "#fff0c8"],
    focus: ["#6f8cff", "#b8c6ff", "#ffffff"],
    ki: ["#1fb89a", "#c8fff0", "#ffffff"],
  };

  // =====================================================================
  // ① 圓章圖樣（±10 單位，原點為中心；o.tiny＝圖樣 ≤14px：只留一個主體、不包外框）
  // =====================================================================
  /** 一道刀光（新月形）：從 (x1,y1) 到 (x2,y2)，往 (nx,ny) 那一側鼓 b 單位；內緣鼓 b×0.3（兩頭尖、中間厚）。 */
  const slash = (c, col, x1, y1, x2, y2, nx, ny, b) => f(c, col, () => { const mx = (x1 + x2) / 2, my = (y1 + y2) / 2; c.moveTo(x1, y1); c.quadraticCurveTo(mx + nx * b, my + ny * b, x2, y2); c.quadraticCurveTo(mx + nx * b * 0.3, my + ny * b * 0.3, x1, y1); c.closePath(); });
  /** 連擊 A：三道平行的斜刀光（「/」方向、往左上鼓）。前面（左上）那道最亮最長（白芯＋粉邊），後面兩道是殘影，一道比一道暗、短。≤14px 只留兩道、加粗。 */
  function comboSlashes(c, o) {
    const T = TONE.combo_point, u = [0.7071, -0.7071], n = [-0.7071, -0.7071]; /* u＝刀光方向（往右上）、n＝鼓起的方向（往左上） */
    /* 第 2 輪：第 1 輪的粉色殘影在圓章 13 真 1 倍和染粉的圓底黏成一片，前面那道改純白、殘影用亮粉、整體加粗 */
    const rows = o.tiny ? [[3.8, 7, T[1], 5.6], [-3.4, 9.2, "#ffffff", 6]] : [[6.2, 6, "#ff6aa8", 4], [0.6, 8.4, T[1], 4.4], [-5, 9.4, "#ffffff", 4.6]]; /* [離中心（沿 −n）、半長、色、鼓] */
    for (const [off, L, col, b] of rows) {
      const cx = -n[0] * off, cy = -n[1] * off;
      slash(c, col, cx - u[0] * L, cy - u[1] * L, cx + u[0] * L, cy + u[1] * L, n[0], n[1], b);
    }
  }
  /** 連擊 B：第 3 批效果記號「追擊／連擊」（一大一小兩顆四芒閃光＝打兩下）直接呼叫，小的染連擊色。 */
  const comboSparks = (c, o) => QS.ACT.combo.d(c, o, [TONE.combo_point[0], "#ffd0e4"]);
  /** 怒氣 A：怒目——兩道往中間壓低的緋紅粗眉，下面兩隻發亮的米黃斜眼（沒有臉的輪廓）。≤14px 眉更粗、眼放大，不畫眉上的亮邊。 */
  function furyEyes(c, o) {
    const T = TONE.fury, t = o.tiny;
    for (const s of [-1, 1]) {
      const B = t ? [[-9.6, -6.8], [-0.8, -2.4], [-1.4, 1.8], [-9.8, -2.2]] : [[-9.4, -6.4], [-1.2, -2.6], [-1.6, 0.8], [-9.6, -3]]; /* 第 2 輪：外角往內收（第 1 輪出圓 7%） */
      poly(c, T[0], B.map(([x, y]) => [s < 0 ? x : -x, y]), 0.5);
      if (!t) poly(c, T[1], [[-9.4, -6.4], [-1.2, -2.6], [-1.6, -1.4], [-9.5, -5]].map(([x, y]) => [s < 0 ? x : -x, y]));
      const E = t ? [[-9.4, 2.6], [-1.6, 4.4], [-2.6, 8.8], [-8.2, 7.6]] : [[-8.8, 2.4], [-2.2, 4.2], [-3, 7.6], [-7.6, 6.6]];
      poly(c, T[2], E.map(([x, y]) => [s < 0 ? x : -x, y]), 0.6);
      if (!t) ci(c, T[0], s < 0 ? -4.6 : 4.6, 5.4, 1.3);
    }
  }
  /** 怒氣 B：張口怒吼——緋紅的嘴、深紅喉、上兩根大白獠牙、下兩根小獠牙。≤14px 拿掉下獠牙與唇上亮面。 */
  function furyMouth(c, o) {
    const T = TONE.fury, mouth = (k, col) => f(c, col, () => { c.moveTo(-10 * k, -4.6 * k + (1 - k) * 2); c.quadraticCurveTo(0, -8 * k + (1 - k) * 2, 10 * k, -4.6 * k + (1 - k) * 2); c.quadraticCurveTo(9.4 * k, 9.6 * k, 0, 9.8 * k); c.quadraticCurveTo(-9.4 * k, 9.6 * k, -10 * k, -4.6 * k + (1 - k) * 2); c.closePath(); });
    mouth(1, T[0]); mouth(0.7, "#7a1426");
    if (!o.tiny) el(c, T[1], -5.2, -4.6, 3.4, 1.3, -0.12);
    for (const s of [-1, 1]) poly(c, T[2], [[s * 6.8, -3.6], [s * 2.2, -4.2], [s * 4.2, o.tiny ? 4.6 : 3.4]], 0.4);
    if (!o.tiny) for (const s of [-1, 1]) poly(c, T[2], [[s * 4.4, 6.8], [s * 1.4, 7], [s * 2.8, 3.6]], 0.3);
  }
  /** 專注 A：對焦框＋凝聚的光點——四個粗的角括號（亮靛藍）圍住中心一顆菱形光點（靛藍外、白芯）。≤14px 括號更粗更短、光點放大。 */
  function focusFrame(c, o) {
    const T = TONE.focus, t = o.tiny, R = t ? 7.6 : 7.8, A = t ? 3.6 : 4.4, W = t ? 3.4 : 2.8;
    for (const [sx, sy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) st(c, T[1], W, (x) => { x.moveTo(sx * R, sy * (R - A)); x.lineTo(sx * R, sy * R); x.lineTo(sx * (R - A), sy * R); });
    const D = t ? 4.8 : 4.6; poly(c, T[0], [[0, -D * 1.2], [D, 0], [0, D * 1.2], [-D, 0]], 0.4); poly(c, T[2], [[0, -D * 0.62], [D * 0.5, 0], [0, D * 0.62], [-D * 0.5, 0]]);
  }
  /** 專注 B：閉目凝神——一隻閉著的眼（往下彎的粗弧＋下緣三根睫毛），眉心一顆菱形光點。≤14px 睫毛只留兩根、弧加粗。 */
  function focusEye(c, o) {
    const T = TONE.focus, t = o.tiny;
    st(c, T[1], t ? 3.6 : 3, (x) => { x.moveTo(-9.4, -0.4); x.quadraticCurveTo(0, 8.6, 9.4, -0.4); });
    const lashes = t ? [[-4.6, 3.2, -6.4, 7.4], [4.6, 3.2, 6.4, 7.4]] : [[-5.4, 3, -7.2, 6.8], [0, 4.2, 0, 8.6], [5.4, 3, 7.2, 6.8]];
    for (const [x1, y1, x2, y2] of lashes) st(c, T[1], t ? 2.8 : 2.2, (x) => { x.moveTo(x1, y1); x.lineTo(x2, y2); });
    const D = t ? 4 : 3.4, y = t ? -6.2 : -6.6; poly(c, T[0], [[0, y - D * 1.25], [D, y], [0, y + D * 1.25], [-D, y]], 0.4); poly(c, T[2], [[0, y - D * 0.6], [D * 0.45, y], [0, y + D * 0.6], [-D * 0.45, y]]);
  }
  /** 氣 A：雙勾玉氣團（太極形）——一圓分成淺青白與青綠兩個勾玉，各帶一顆對方顏色的「眼」；左上一點白亮面。≤14px 眼放大、不畫亮面。 */
  function kiTaiji(c, o) {
    const T = TONE.ki, R = 9.6, e = o.tiny ? 2.3 : 1.7;
    ci(c, T[1], 0, 0, R);
    f(c, T[0], () => { c.moveTo(0, -R); c.arc(0, 0, R, -PI / 2, PI / 2, false); c.arc(0, R / 2, R / 2, PI / 2, -PI / 2, false); c.arc(0, -R / 2, R / 2, PI / 2, -PI / 2, true); c.closePath(); });
    ci(c, T[0], 0, -R / 2, e); ci(c, T[1], 0, R / 2, e);
    if (!o.tiny) el(c, T[2], -5.2, -2.6, 1.3, 2.6, 0.5);
  }
  /** 氣 B：氣旋（派工單建議的螺旋氣旋）——白芯青綠的氣團，外面兩道繞著轉的青綠氣流（往外變細）。≤14px 只留一道氣流、氣團放大。 */
  function kiSwirl(c, o) {
    const T = TONE.ki, t = o.tiny;
    const arm = (a0) => f(c, T[0], () => { const s = 24; for (let i = 0; i <= s; i++) { const a = a0 + (i / s) * PI * 1.05, r = 5.4 + (i / s) * 4.4, w = 2.6 * (1 - i / s) + 0.4; const x = Math.cos(a) * (r + w), y = Math.sin(a) * (r + w); i ? c.lineTo(x, y) : c.moveTo(x, y); } for (let i = s; i >= 0; i--) { const a = a0 + (i / s) * PI * 1.05, r = 5.4 + (i / s) * 4.4, w = 2.6 * (1 - i / s) + 0.4; c.lineTo(Math.cos(a) * (r - w * 0.2), Math.sin(a) * (r - w * 0.2)); } c.closePath(); });
    arm(-PI / 2); if (!t) arm(PI / 2);
    ci(c, T[0], 0, 0, t ? 6 : 5.2); ci(c, T[1], 0, 0, t ? 4.2 : 3.6); ci(c, T[2], -0.8, -0.8, t ? 2 : 1.7);
  }
  /** 每個關鍵字兩案：k＝圖樣在圓章裡再縮放（同第⑤b 批的 k；方的、四角有東西的收進圓底內）；src＝沿用哪一批的哪個形（新畫的寫「新」）。 */
  const CAND = {
    combo_point: {
      a: { topic: "三道平行的斜刀光（前亮後暗的殘影）；≤14px 兩道", src: "新", k: 0.96, d: comboSlashes },
      b: { topic: "一大一小兩顆四芒閃光（大的白、小的連擊色）", src: "b3:combo（追擊／連擊）＝b4:skeleton.combo", k: 0.82, d: comboSparks },
    },
    fury: {
      a: { topic: "怒目：兩道往中間壓低的緋紅粗眉＋兩隻發亮的米黃斜眼", src: "新", k: 0.84, d: furyEyes },
      b: { topic: "張口怒吼：緋紅的嘴、深紅喉、上下獠牙", src: "新", k: 0.94, d: furyMouth },
    },
    focus: {
      a: { topic: "對焦框：四個粗角括號圍住一顆菱形光點", src: "新", k: 0.8, d: focusFrame },
      b: { topic: "閉目凝神：往下彎的閉眼弧＋睫毛，眉心一顆菱形光點", src: "新", k: 0.86, d: focusEye },
    },
    ki: {
      a: { topic: "雙勾玉氣團（太極形）：淺青白與青綠兩個勾玉", src: "新", k: 0.92, d: kiTaiji },
      b: { topic: "氣旋：白芯氣團，外面兩道繞著轉的氣流", src: "新（派工單建議題材）", k: 0.96, d: kiSwirl },
    },
  };
  /** 推薦（美術 PM 決定前的預設）：每個關鍵字哪一案。 */
  const PICK = { combo_point: "a", fury: "a", focus: "a", ki: "a" };
  const entryOf = (kw, cand) => CAND[kw][cand ?? PICK[kw]];
  const isNew = (kw) => kw in CAND;
  const colorOf = (kw, opt = {}) => (isNew(kw) ? (opt.alt ? COLOR_ALT : COLOR)[kw] : K.KC[kw]);
  /** 只有圖樣的 canvas：cpx＝圖樣本身（±10 單位）顯示的 CSS px；≤14px 不包外框（規則 8）。同 qIconsKeywords.js 的 glyph()。opt.flat＝量剪影用（只畫 d 的剪影、不包外框）。 */
  function glyph(kw, cpx, res = 2, opt = {}) {
    const e = entryOf(kw, opt.cand); return Q.render({ d: (c, o) => { c.save(); c.translate(24, 24); c.scale(1.8, 1.8); e.d(c, { ...o, small: cpx <= 24, tiny: cpx <= 14 }); c.restore(); } }, cpx * K.BOX, res, { ow: opt.ow ?? (cpx <= 14 ? 0 : Q.outlinePx(cpx)) });
  }
  /** 在 (x0,y0) 左上角畫一個直徑 D 的關鍵字圓章（同 qIconsKeywords.js 的 chip()：外框色一圈 1 裝置像素＋深色混 28% 關鍵字色的圓底＋圖樣，沒有環）。既有 12 個直接呼叫 K.chip。 */
  function chip(ctx, kw, x0, y0, D, res, opt = {}) {
    if (!isNew(kw)) { K.chip(ctx, kw, x0, y0, D, res, opt); return; }
    const e = entryOf(kw, opt.cand), { ow, inner } = K.geom(D, res), cx = x0 + D / 2, cy = y0 + D / 2;
    ctx.save();
    ctx.fillStyle = OUT; ctx.beginPath(); ctx.arc(cx, cy, D / 2, 0, TAU); ctx.fill();
    ctx.fillStyle = opt.bg ?? mix(colorOf(kw, opt), "#191b22", 0.72); ctx.beginPath(); ctx.arc(cx, cy, D / 2 - ow, 0, TAU); ctx.fill();
    ctx.restore();
    const cpx = inner * e.k, g = glyph(kw, cpx, res, opt), a = cpx * K.BOX;
    QW.blit(ctx, g, cx - a / 2, cy - a / 2, a, res);
  }
  /** 單獨一個圓章的 canvas（px 邊長、圓章撐滿）。zoom＝CSS 放大（最近鄰放大由頁面設 image-rendering）；o.res＝內部解析度（1＝真 1 倍）。 */
  function chipCanvas(kw, px, zoom = 1, o = {}) { const res = o.res ?? (zoom === 1 ? 2 : zoom), cv = blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d"); x.scale(res, res); chip(x, kw, 0, 0, px, res, o); return cv; }
  /** 圓章四個尺寸（裝備格 32、背包格 42、48、64 → 圓章邊長，真 1 倍取整數）。 */
  const SIZES = [32, 42, 48, 64];

  // =====================================================================
  // ⑤ 條件部件「層數達 N」（self_stack_at_least）：±10 單位，畫進第④批的條件圓片（18px、色環 #ffe9a8）。
  // =====================================================================
  /** A：滿格計量＋自身——三個全亮的金色計量格（同 HUD 層數計量的格子）排一排，右下一個米白小人形（同「自身血量低於」：自己）。≤14px 格子間距放大到 1 個裝置像素以上。 */
  function condPips(c, o) {
    /* 第 2 輪：第 1 輪三格疊在小人形上、18 真 1 倍黏成一條、左格頂到色環 → 三格移到上半（底在 y≈0）、小人形在右下不重疊、整體縮 0.9 收進色環 */
    const t = o.tiny, w = t ? 4.6 : 4.8, g = t ? 2.4 : 1.6, h = 9, x0 = -9.8, y0 = -9;
    c.save(); c.scale(0.9, 0.9);
    for (let i = 0; i < 3; i++) { const x = x0 + i * (w + g); rr(c, GOLD, x, y0, w, h, 1.2); f(c, GOLD_L, () => c.roundRect(x, y0, w, t ? 2.8 : 2.6, [1.2, 1.2, 0, 0])); }
    halo(c, o, (q) => bust(q, CREAM, 5.4, 5.8, 0.66));
    c.restore();
  }
  /** B：金條頂到門檻——三根等高的金條（同「累積層數」的金條形，但一樣高＝滿了）頂到上面一道米白門檻橫槓，右下一個米白小人形。 */
  function condBars(c, o) {
    const t = o.tiny, w = t ? 4.6 : 4.8, g = t ? 1.8 : 1.2, x0 = -10.4, top = -4.2, bot = 6.8;
    for (let i = 0; i < 3; i++) { const x = x0 + i * (w + g); rr(c, GOLD, x, top, w, bot - top, 1.2); if (!t) f(c, GOLD_L, () => c.rect(x, top, w, 2.2)); }
    rr(c, CREAM, x0 - 0.6, top - 3.6, 3 * w + 2 * g + 1.2, 2.8, 1.2);
    halo(c, o, (q) => bust(q, CREAM, 6, 4.6, 0.62));
  }
  const COND = {
    a: { zh: "自身層數達到（A 滿格計量）", topic: "三個全亮的金色計量格（同 HUD 層數計量的格子）＋右下米白小人形（自身）", src: "新；小人形＝b4:condition.self_hp_below 的 bust", d: condPips },
    b: { zh: "自身層數達到（B 金條頂到門檻）", topic: "三根等高金條頂到一道米白門檻橫槓＋右下米白小人形（自身）", src: "新；金條＝b3:builder 的形、小人形同上", d: condBars },
  };
  const COND_PICK = "a";
  /** 樣張頁呼叫一次：把兩案塞進第④批的條件表（鍵 self_stack_at_least__a／__b），用第④批的 chipCanvas、paintIcon 畫。只在 q-icons-kw.html 裡做，第④批的頁、清單、指紋不受影響。 */
  function installCond() { for (const k of ["a", "b"]) QP.CATS.condition["self_stack_at_least__" + k] = COND[k]; }

  // =====================================================================
  // ③ 創角關鍵字圖示（SVG 16×16 座標，單色，同 client/src/ui/CreateIcons.tsx 的 keywordGlyph；顯示 15px，派工單說按鈕內 28～32）
  // =====================================================================
  const CREATE = {
    combo_point: {
      a: (c) => `<path d="M4 15C5 10 8.5 6.5 13.5 4.6C9.5 7.6 7 10.6 6.2 15Z" fill="${c}"/><path d="M1.4 11.6C2.4 7.6 5.6 4.4 9.6 2.6C6.6 5.4 4.6 8 3.6 11.6Z" fill="${c}" fill-opacity="0.75"/><path d="M8.4 15.4C9.4 12.6 11.6 10.2 15 8.8C12.6 11 11.4 13 10.8 15.4Z" fill="${c}" fill-opacity="0.5"/>`,
      b: (c) => `<path d="M6 0.8L7.4 4.6L11.2 6L7.4 7.4L6 11.2L4.6 7.4L0.8 6L4.6 4.6Z" fill="${c}"/><path d="M11.6 8L12.6 10.4L15 11.4L12.6 12.4L11.6 14.8L10.6 12.4L8.2 11.4L10.6 10.4Z" fill="${c}" fill-opacity="0.75"/>`,
    },
    fury: {
      /* 第 2 輪：第 1 輪四塊分開的眉與眼在 15px 讀成兩撇鬍子 → 改成一整條怒目面罩（中間往下壓的 V），眼是挖空的兩道斜縫 */
      a: (c) => `<path fill-rule="evenodd" d="M0.6 3.6L8 8L15.4 3.6L15.2 10.6Q8 14.6 0.8 10.6ZM2.6 8L6.6 9.8L6 11.6L2.8 10.2ZM13.4 8L9.4 9.8L10 11.6L13.2 10.2Z" fill="${c}"/>`,
      b: (c) => `<path fill-rule="evenodd" d="M1 5Q8 2 15 5Q14.6 14.6 8 14.8Q1.4 14.6 1 5ZM3.4 6.4L5.8 6.2L4.8 10.4ZM12.6 6.4L10.2 6.2L11.2 10.4ZM6.4 12.6L7.4 10.6L7.6 12.8Z" fill="${c}"/>`,
    },
    focus: {
      a: (c) => `<g fill="none" stroke="${c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1.6 5V1.6H5M11 1.6H14.4V5M14.4 11V14.4H11M5 14.4H1.6V11"/></g><path d="M8 4.4L10.6 8L8 11.6L5.4 8Z" fill="${c}"/>`,
      b: (c) => `<g fill="none" stroke="${c}" stroke-width="1.6" stroke-linecap="round"><path d="M1.6 8.4Q8 14.4 14.4 8.4"/><path d="M4.2 11.2L3.2 13.6M8 12.6V15M11.8 11.2L12.8 13.6"/></g><path d="M8 1.2L10 4.2L8 7.2L6 4.2Z" fill="${c}"/>`,
    },
    ki: {
      a: (c) => `<circle cx="8" cy="8" r="6.6" fill="none" stroke="${c}" stroke-width="1.3"/><path d="M8 1.4A6.6 6.6 0 0 1 8 14.6A3.3 3.3 0 0 1 8 8A3.3 3.3 0 0 0 8 1.4Z" fill="${c}"/><circle cx="8" cy="4.7" r="1.1" fill="${c}"/><circle cx="8" cy="11.3" r="1.1" fill="#1a1410"/>`,
      b: (c) => `<circle cx="8" cy="8" r="3.2" fill="${c}"/><g fill="none" stroke="${c}" stroke-width="1.6" stroke-linecap="round"><path d="M8 2.6A5.4 5.4 0 0 1 13.4 8.6"/><path d="M8 13.4A5.4 5.4 0 0 1 2.6 7.4"/></g>`,
    },
  };
  /** 創角圖示的 SVG 字串（viewBox 16、單色 c；同 KeywordIcon）。 */
  /** 創角圖示色：派工單要和 KEYWORD_COLOR 同色；怒氣、專注的原色在創角按鈕的深褐底上偏暗（第 1 輪截圖），這兩個建議亮一階（美術 PM 決定：同色或亮一階）。 */
  const CREATE_COLOR = { combo_point: COLOR.combo_point, fury: "#ff4a62", focus: "#7d96ff", ki: COLOR.ki };
  const createSvg = (kw, cand, c, size = 15) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="${size}" height="${size}">${CREATE[kw][cand ?? PICK[kw]](c ?? CREATE_COLOR[kw])}</svg>`;

  // =====================================================================
  // ④ HUD 層數計量（格子式）：一個膠囊（照 status-card.css 的 .stat-chip：高 22、底 #1a1410、框 #5a4a38、圓角 11、左內距 4、右 7、間距 3）
  //    裡面：關鍵字圓章 14px（同①，最小那一級）＋N 格。滿層：格子換亮一階＋白亮條、膠囊框換關鍵字色並往外暈 3px、圓章外加一圈關鍵字色。
  // =====================================================================
  const MAX = { combo_point: 5, fury: 4, focus: 3, ki: 3 };
  const SLOT = "#2a2418", SLOT_EDGE = "#5a4a38";
  /** 格子的形（CSS px，左上原點、寬 w 高 h 的格）：A＝通用斜切段；B＝各關鍵字自己的形（連擊斜刀片、怒氣尖角、專注菱形、氣圓珠）。 */
  const PIP = {
    a: { w: 7, h: 10, step: 8, path: (c, x, y, w, h) => { c.moveTo(x + 2, y); c.lineTo(x + w, y); c.lineTo(x + w - 2, y + h); c.lineTo(x, y + h); c.closePath(); }, extra: 0 },
    b: {
      combo_point: { w: 7, h: 10, step: 7, path: (c, x, y, w, h) => { c.moveTo(x + 3.5, y); c.lineTo(x + w, y); c.lineTo(x + w - 3.5, y + h); c.lineTo(x, y + h); c.closePath(); } },
      fury: { w: 8, h: 10, step: 9, path: (c, x, y, w, h) => { c.moveTo(x + w / 2, y); c.lineTo(x + w, y + h * 0.42); c.lineTo(x + w, y + h); c.lineTo(x, y + h); c.lineTo(x, y + h * 0.42); c.closePath(); } },
      focus: { w: 9, h: 10, step: 10, path: (c, x, y, w, h) => { c.moveTo(x + w / 2, y); c.lineTo(x + w, y + h / 2); c.lineTo(x + w / 2, y + h); c.lineTo(x, y + h / 2); c.closePath(); } },
      ki: { w: 9, h: 9, step: 10, path: (c, x, y, w, h) => { c.arc(x + w / 2, y + h / 2, w / 2, 0, TAU); } },
    },
  };
  const pipOf = (kw, cand) => (cand === "b" ? PIP.b[kw] : PIP.a);
  /** 一格：外形先填外框色（亮格）或槽框色（暗格），再往內縮 1 裝置像素填本色；亮格加上緣亮條。 */
  function pip(c, P, x, y, on, full, col, res) {
    const u = 1 / res, path = (k) => { c.beginPath(); const cx = x + P.w / 2, cy = y + P.h / 2, sx = (P.w - 2 * k) / P.w, sy = (P.h - 2 * k) / P.h; c.save(); c.translate(cx, cy); c.scale(sx, sy); c.translate(-cx, -cy); P.path(c, x, y, P.w, P.h); c.restore(); };
    path(0); c.fillStyle = on ? OUT : SLOT_EDGE; c.fill();
    path(u); c.fillStyle = on ? (full ? mix(col, "#ffffff", 0.28) : col) : SLOT; c.fill();
    if (on) { c.save(); path(u); c.clip(); c.fillStyle = full ? "rgba(255,255,255,0.8)" : "rgba(255,255,255,0.45)"; c.fillRect(x, y, P.w, Math.max(2 * u, Math.round(P.h * 0.28 * res) / res)); c.fillStyle = "rgba(0,0,0,0.22)"; c.fillRect(x, y + P.h - 2 * u, P.w, 2 * u); c.restore(); }
  }
  /** 整條的寬（CSS px）：圓章 14＋間距 3＋格子。 */
  const gaugeW = (kw, cand) => { const P = pipOf(kw, cand), n = MAX[kw]; return 14 + 3 + (n - 1) * P.step + P.w; };
  /** 在 (x,y) 畫一個層數膠囊（左上角；膠囊高 22）：n＝目前層數。回傳膠囊寬。opt.bare＝不畫膠囊（只畫圓章＋格子）。 */
  function gauge(c, kw, n, x, y, res, opt = {}) {
    const cand = opt.cand ?? "a", P = pipOf(kw, cand), max = MAX[kw], full = n >= max, col = COLOR[kw], W = 4 + gaugeW(kw, cand) + 7, H = 22;
    c.save();
    if (!opt.bare) {
      if (full) { c.save(); c.shadowColor = col; c.shadowBlur = 5 * res; c.fillStyle = col; c.beginPath(); c.roundRect(x, y, W, H, 11); c.fill(); c.restore(); }
      c.fillStyle = full ? col : SLOT_EDGE; c.beginPath(); c.roundRect(x, y, W, H, 11); c.fill();
      c.fillStyle = "#1a1410"; c.beginPath(); c.roundRect(x + 1, y + 1, W - 2, H - 2, 10); c.fill();
    }
    const cx = x + 4, cy = y + 4;
    if (full) { c.fillStyle = col; c.beginPath(); c.arc(cx + 7, cy + 7, 8, 0, TAU); c.fill(); }
    chip(c, kw, cx, cy, 14, res, { cand: opt.chipCand });
    const px0 = cx + 14 + 3, py = y + Math.round((H - P.h) / 2);
    for (let i = 0; i < max; i++) pip(c, P, px0 + i * P.step, py, i < n, full, col, res);
    c.restore(); return W;
  }
  /** 一個膠囊的 canvas（真 1 倍或 2 倍；zoom＝CSS 放大）。留 4px 給滿層的外暈。 */
  function gaugeCanvas(kw, n, zoom = 1, o = {}) { const res = o.res ?? (zoom === 1 ? 2 : zoom), cand = o.cand ?? "a", W = 4 + gaugeW(kw, cand) + 7 + 8, H = 30, cv = blank(Math.round(W * res), Math.round(H * res)); cv.style.width = W * zoom + "px"; cv.style.height = H * zoom + "px"; const x = cv.getContext("2d"); x.scale(res, res); gauge(x, kw, n, 4, 4, res, o); return cv; }

  return { CREATE_COLOR, COLOR, COLOR_ALT, TONE, ZH, KEYS, CAND, PICK, COND, COND_PICK, CREATE, MAX, PIP, SIZES, isNew, colorOf, entryOf, glyph, chip, chipCanvas, installCond, createSvg, gauge, gaugeW, gaugeCanvas, pipOf };
})();
