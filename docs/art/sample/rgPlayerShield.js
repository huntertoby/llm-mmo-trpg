// rgPlayerShield.js：#163「護陣」——RG 兩種敵人大盾改成玩家塔盾的新形制（畫圖 agent，2026-11-13）。
// 紀錄 docs/art/RG樣張.md 第 10 節。依據 main 的 docs/design/08-裝備.md 8.11「塔盾詞條『護陣』」最後一條（外觀）。
// 不改任何既有畫法檔（qDoll.js、qIcons.js、qIconsWeapons.js、rgUnits.js 只讀）：
//   - 紙娃娃：同 rgUnits.js 的做法——單位的副手掛一面「鑰匙色」塔盾（shield_kite／tower，主色 #ff00ff），
//     qDoll 畫到盾的第一筆鑰匙色填色時，在當下的變換（qDoll 的盾錨點）改畫新形制，之後到那一層 restore 為止都不畫。
//     所以握法、手臂、圖層、朝西換手、剪影外框都和現行塔盾一模一樣（rgUnits.js 已驗過）。
//   - 兩個形制（建議 form id；玩家可見名稱待玩法 PM）：
//       sect_great  雲紋碑盾：持盾弟子那面（rgUnits.js 的 A）參數化——盾面跟材質走，盾邊照盾面亮度換（暗面配月白、亮面配材質暗色），
//                   雲紋章（月白圓章、青色三峰、月白雲、朱紅點）固定；敵人配色（青面月白邊）畫出來和 rgUnits.js 逐像素相同（頁面 ?part=check）。
//       molten_shell 熔殼立殼：熔殼甲兵的立殼（rgUnits.js SHELL.a）改成手持塔盾——正面是一片蛋形頂的殼、三道橫向鋸齒殼縫；
//                   側面是同一個新月形（敵人那面等比縮進塔盾的側面錨點）；背面是殼的內面＋兩條皮帶。殼板＝材質色混玄武岩，殼縫紅光固定。
//   - Q 版圖示（48 格，照 qIconsWeapons.js 的副手畫法與 paint() 流程）：sectIcon、shellIcon。
// 座標：盾錨點同 qDoll（正面 translate(手 x, −9.5)＋1.5；側面 translate(8.6, −13.5)；背面 shieldBack）。確定性：沒有亂數。
window.RGPlayerShield = (() => {
  const TAU = Math.PI * 2, OUT = "#16121a";
  const mix = (a, b, t) => { const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)); const A = p(a), B = p(b); return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, "0")).join(""); };
  const dk = (c, t = 0.25) => mix(c, "#000000", t);
  const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const lum = (h) => { const [r, g, b] = rgb(h); return 0.299 * r + 0.587 * g + 0.114 * b; };
  const dist = (a, b) => { const A = rgb(a), B = rgb(b); return Math.hypot(A[0] - B[0], A[1] - B[1], A[2] - B[2]); };
  function fill(ctx, c, path) { ctx.fillStyle = c; ctx.beginPath(); path(); ctx.fill(); }
  function line(ctx, c, w, pts, cap = "round") { ctx.strokeStyle = c; ctx.lineWidth = w; ctx.lineCap = cap; ctx.lineJoin = "round"; ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke(); }

  // =====================================================================================
  // 0. 配色
  // =====================================================================================
  /** 固定色（不跟材質）：雲紋章、銅釘、盾背木板與皮帶（rgUnits.js 的 C）；殼縫紅光（rgUnits.js 的 LAVA）。 */
  const FIX = { qing: "#5f8f8a", moon: "#dfe4e2", red: "#c0392b", brass: "#e8bb48", wood: "#7a5232", strap: "#3a2414", basalt: "#4a3631", glow: "#ff6a1a", core: "#ffd04a" };
  /** 盾邊換色的門檻：盾面亮度 < 150 配月白邊（同敵人：青面月白邊），≥ 150 配材質暗色再暗 10%。照顏色判斷，不照材質名。 */
  const RIM_LUM = 150;
  /** 熔殼立殼：殼板＝材質主色往玄武岩混 SHELL_K（推薦 0.35；頁面 ?part=materials 有 0／0.35／0.6 三列對照）。 */
  let SHELL_K = 0.35;
  /** 玩家的材質 → 主色 a、暗色 d（照 qIconsWeapons.palette：材質表＋元素關鍵字混色；樣張用樣張材質表，遊戲端用 material.ts）。 */
  function matPal(look) {
    const QW = window.QIconsWeapons, r = QW.resolve({ kind: "kite_shield", form: "tower", material: look.material, keywords: look.keywords, rarity: look.rarity, color: look.color });
    const P = QW.palette(r); return { a: P.a, d: P.d, r };
  }
  /** 雲紋碑盾的配色：look＝{ material, keywords } 或 { enemy: true }（持盾弟子：青面月白邊，和 rgUnits.js A 相同）。 */
  function sectPal(look = {}) {
    if (look.enemy) return { face: FIX.qing, rim: FIX.moon, rivet: FIX.brass, ring: null, enemy: true };
    const { a, d } = matPal(look), face = a, rim = lum(face) < RIM_LUM ? FIX.moon : dk(d, 0.1);
    return { face, rim, rivet: dist(face, FIX.brass) < 70 ? dk(rim, 0.1) : FIX.brass, ring: rim === FIX.moon ? null : rim, enemy: false };
  }
  /** 熔殼立殼的配色：plate＝殼板本色、lit＝迎光那片、low＝下片、inner＝殼的內面（厚度、背面）、edge＝殼緣。look.k 覆寫混玄武岩的比例。 */
  function shellPal(look = {}) {
    if (look.enemy) return { plate: FIX.basalt, lit: "#6a5048", low: dk(FIX.basalt, 0.18), inner: "#2e211d", edge: dk(FIX.basalt, 0.3), enemy: true };
    const { a } = matPal(look), k = look.k ?? SHELL_K, plate = mix(a, FIX.basalt, k);
    return { plate, lit: mix(plate, "#ffffff", 0.16), low: dk(plate, 0.18), inner: dk(plate, 0.38), edge: dk(plate, 0.3), enemy: false };
  }

  // =====================================================================================
  // 1. 雲紋碑盾（sect_great）：rgUnits.js 的 front／side／back 參數化（形狀、尺寸、紋樣都同 A）
  // =====================================================================================
  const FW = 8.5, FTOP = -13.5, FBOT = 9, ARCH = 4;
  function archPath(ctx, x0, x1, top, bot, i = 0) {
    const L = x0 + i, R = x1 - i, T = top + i, B = bot - i, a = ARCH - i * 0.4, cx = (L + R) / 2, rx = (R - L) / 2;
    ctx.moveTo(L, B - 1.2); ctx.lineTo(L, T); ctx.ellipse(cx, T, rx, a, 0, Math.PI, 0); ctx.lineTo(R, B - 1.2); ctx.quadraticCurveTo(R, B, R - 1.2, B); ctx.lineTo(L + 1.2, B); ctx.quadraticCurveTo(L, B, L, B - 1.2); ctx.closePath();
  }
  /** 雲紋章（固定色）。ring＝亮盾面時圓章內緣一圈盾邊色（月白圓章壓在銀、鋼盾面上才分得開）；敵人配色不畫（和 rgUnits.js 逐像素相同）。 */
  function emblem(ctx, pal, cx, cy, r, sx = 1) {
    ctx.save(); ctx.translate(cx, cy); ctx.scale(sx, 1);
    fill(ctx, FIX.moon, () => ctx.arc(0, 0, r, 0, TAU));
    fill(ctx, dk(FIX.qing, 0.15), () => { ctx.moveTo(-r * 0.78, r * 0.42); ctx.lineTo(-r * 0.38, -r * 0.16); ctx.lineTo(-r * 0.12, r * 0.08); ctx.lineTo(r * 0.22, -r * 0.62); ctx.lineTo(r * 0.78, r * 0.42); ctx.closePath(); });
    line(ctx, FIX.moon, r * 0.2, [[-r * 0.62, r * 0.18], [-r * 0.12, r * 0.3], [r * 0.36, r * 0.1]]);
    fill(ctx, FIX.red, () => ctx.arc(r * 0.22, -r * 0.62, r * 0.17, 0, TAU));
    if (pal.ring) { ctx.strokeStyle = pal.ring; ctx.lineWidth = r * 0.16; ctx.beginPath(); ctx.arc(0, 0, r * 0.92, 0, TAU); ctx.stroke(); }
    ctx.restore();
  }
  function sectFront(ctx, pal) {
    const L = -FW, R = FW, rimW = 1.3;
    fill(ctx, pal.rim, () => archPath(ctx, L, R, FTOP, FBOT));
    fill(ctx, pal.face, () => archPath(ctx, L, R, FTOP, FBOT, rimW));
    ctx.save(); ctx.beginPath(); archPath(ctx, L, R, FTOP, FBOT, rimW); ctx.clip();
    fill(ctx, dk(pal.face, 0.16), () => ctx.rect(R - 4.2, FTOP - ARCH, 6, FBOT - FTOP + ARCH + 2));
    fill(ctx, dk(pal.face, 0.16), () => ctx.rect(L, FBOT - 3.4, R - L, 4));
    fill(ctx, "rgba(255,255,255,0.45)", () => ctx.roundRect(L + rimW + 0.9, FTOP + 0.2, 1.3, 9.5, 0.65));
    ctx.restore();
    for (const y of [FTOP + 3.2, FBOT - 5.2]) fill(ctx, dk(pal.rim, 0.1), () => ctx.rect(L + rimW, y, R - L - rimW * 2, 0.9));
    emblem(ctx, pal, 0, -3.2, 4.4);
    for (const [x, y] of [[L + 2.4, FTOP + 0.6], [R - 2.4, FTOP + 0.6], [L + 2.4, FBOT - 2.2], [R - 2.4, FBOT - 2.2]]) fill(ctx, pal.rivet, () => ctx.arc(x, y, 0.75, 0, TAU));
  }
  function sectSide(ctx, pal) {
    const top = -10, bot = 13.3, sx = 0.42;
    fill(ctx, dk(pal.rim, 0.3), () => archPath(ctx, -2.2, 0.6, top + 0.6, bot));
    ctx.save(); ctx.translate(2.3, 0); ctx.scale(sx, 1);
    const L = -FW + 1.5, R = FW - 1.5;
    fill(ctx, pal.rim, () => archPath(ctx, L, R, top, bot));
    fill(ctx, pal.face, () => archPath(ctx, L, R, top, bot, 1.9));
    ctx.save(); ctx.beginPath(); archPath(ctx, L, R, top, bot, 1.9); ctx.clip(); fill(ctx, dk(pal.face, 0.16), () => ctx.rect(L, bot - 3.4, R - L, 4)); ctx.restore();
    for (const y of [top + 3.2, bot - 5.2]) fill(ctx, dk(pal.rim, 0.1), () => ctx.rect(L + 1.9, y, R - L - 3.8, 0.9));
    ctx.restore();
    emblem(ctx, pal, 2.6, 0.2, 3.9, 0.42 * 1.1);
    fill(ctx, "rgba(255,255,255,0.45)", () => ctx.roundRect(0.1, top + 0.8, 0.9, 8, 0.45));
  }
  function sectBack(ctx, pal) {
    const L = -FW, R = FW, top = -7.5, bot = 17;
    fill(ctx, dk(pal.rim, 0.25), () => archPath(ctx, L, R, top, bot));
    fill(ctx, FIX.wood, () => archPath(ctx, L, R, top, bot, 1.3));
    ctx.save(); ctx.beginPath(); archPath(ctx, L, R, top, bot, 1.3); ctx.clip();
    for (const x of [-2.8, 2.8]) fill(ctx, dk(FIX.wood, 0.22), () => ctx.rect(x - 0.3, top - ARCH, 0.6, bot - top + ARCH));
    fill(ctx, dk(FIX.wood, 0.18), () => ctx.rect(R - 3.6, top - ARCH, 5, bot - top + ARCH));
    ctx.restore();
    for (const y of [top + 4.2, bot - 6]) fill(ctx, FIX.strap, () => ctx.rect(L + 1.3, y, R - L - 2.6, 1.5));
  }

  // =====================================================================================
  // 2. 熔殼立殼（molten_shell）：手持塔盾版
  // =====================================================================================
  function seam(ctx, pts, w = 1, a = 1) { ctx.save(); ctx.globalAlpha = a; line(ctx, FIX.glow, w, pts); line(ctx, FIX.core, w * 0.38, pts); ctx.restore(); }
  /** 鋸齒殼縫：從 x0 到 x1、中心高 y、齒高 h、n 段（同甲蟲背上的火紋：一上一下）。 */
  const zig = (x0, x1, y, h, n = 4) => Array.from({ length: n + 1 }, (_, i) => [x0 + ((x1 - x0) * i) / n, y + (i % 2 ? -h : h * 0.3)]);
  /** 不規則的裂縫（第 2 版：等高的鋸齒讀成彩蛋的花紋；照敵人殼縫的寫法，齒高、間距錯開）。v＝第幾道（三道各錯一點）。 */
  const CRACK = [[0, 0.25], [0.17, -0.9], [0.33, 0.35], [0.47, -0.55], [0.63, 0.5], [0.8, -1], [1, 0.1]];
  const crack = (x0, x1, y, h, v = 0) => CRACK.map(([t, d], i) => [x0 + (x1 - x0) * Math.min(1, Math.max(0, t + (i % 3 === v % 3 ? 0.04 : 0))), y + d * h * (i % 2 === v % 2 ? 0.8 : 1.1)]);
  /** 一道殼縫：裂縫下緣一條下一片殼板的亮邊（板緣），紅光壓在上面。 */
  function plateSeam(ctx, pts, w, lit, dy) { line(ctx, lit, w * 0.55, pts.map(([x, y]) => [x, y + dy])); line(ctx, FIX.glow, w, pts); line(ctx, FIX.core, w * 0.38, pts); }
  /** 正面外形：蛋形頂（比雲紋碑盾的淺拱高、尖）、兩側往外鼓、下緣微收、圓角。和碑盾同高同寬：x ±8.5、y −18～9。 */
  function shellPath(ctx, s = 1, ox = 0, oy = 0, i = 0) {
    const [sx, sy] = Array.isArray(s) ? s : [s, s], X = (x) => ox + x * sx, Y = (y) => oy + y * sy, w = 8.5 - i, wb = 7.2 - i, top = -18 + i, bot = 9 - i;
    ctx.moveTo(X(-wb + 1.4), Y(bot)); ctx.quadraticCurveTo(X(-wb), Y(bot), X(-wb - 0.2), Y(bot - 2));
    ctx.quadraticCurveTo(X(-w - 0.4), Y(-4), X(-w + 0.6), Y(-11));
    ctx.quadraticCurveTo(X(-w * 0.55), Y(top + 0.4), X(0), Y(top));
    ctx.quadraticCurveTo(X(w * 0.55), Y(top + 0.4), X(w - 0.6), Y(-11));
    ctx.quadraticCurveTo(X(w + 0.4), Y(-4), X(wb + 0.2), Y(bot - 2));
    ctx.quadraticCurveTo(X(wb), Y(bot), X(wb - 1.4), Y(bot)); ctx.closePath();
  }
  function shellFront(ctx, pal) {
    fill(ctx, pal.edge, () => shellPath(ctx));
    fill(ctx, pal.plate, () => shellPath(ctx, 1, 0, 0, 1.1));
    ctx.save(); ctx.beginPath(); shellPath(ctx, 1, 0, 0, 1.1); ctx.clip();
    fill(ctx, pal.lit, () => ctx.rect(-10, -20, 20, 9.6)); // 上片迎光
    fill(ctx, pal.low, () => ctx.rect(-10, 3.2, 20, 7)); // 下片暗
    fill(ctx, pal.inner, () => { ctx.moveTo(5.6, -16); ctx.quadraticCurveTo(9.6, -4, 6.4, 10); ctx.lineTo(12, 10); ctx.lineTo(12, -16); ctx.closePath(); }); // 右緣看到一點殼的厚度（內面）
    fill(ctx, "rgba(255,255,255,0.4)", () => ctx.ellipse(-4.2, -12.4, 0.9, 2.6, 0.5, 0, TAU));
    ctx.restore();
    plateSeam(ctx, crack(-6.4, 5.6, -10.6, 1.5, 0), 1.1, mix(pal.plate, "#ffffff", 0.3), 1.0);
    plateSeam(ctx, crack(-7.2, 6.2, -3.4, 1.5, 1), 1.1, mix(pal.plate, "#ffffff", 0.3), 1.0);
    plateSeam(ctx, crack(-6.6, 5.6, 3.4, 1.5, 2), 1.1, mix(pal.plate, "#ffffff", 0.3), 1.0);
  }
  /** 側面：敵人那片立殼（rgUnits.js SHELL.a，x 18～29、y 0～−30）等比縮進塔盾側面錨點（y −10～13.3，縮 0.777），新月形、三道殼縫。不畫扣盾的前腳（手握）。 */
  function shellSide(ctx, pal) {
    const s = 23.3 / 30;
    ctx.save(); ctx.translate(-2.2 - 18.2 * s, 13.3); ctx.scale(s, s);
    const shape = () => { ctx.moveTo(18.2, 0); ctx.lineTo(18.6, -14); ctx.quadraticCurveTo(18.2, -25, 20.4, -28.8); ctx.quadraticCurveTo(23.6, -30, 25.6, -24.4); ctx.quadraticCurveTo(29, -15, 27.8, -5); ctx.quadraticCurveTo(27.4, -1.4, 26.4, 0); ctx.closePath(); };
    fill(ctx, pal.plate, shape);
    ctx.save(); ctx.beginPath(); shape(); ctx.clip();
    fill(ctx, pal.inner, () => { ctx.moveTo(17, 0); ctx.lineTo(17.4, -30); ctx.lineTo(21.4, -30); ctx.quadraticCurveTo(20.6, -14, 21.4, 0); ctx.closePath(); });
    fill(ctx, pal.lit, () => { ctx.moveTo(21.4, -30); ctx.lineTo(30, -30); ctx.lineTo(30, -20.6); ctx.quadraticCurveTo(25.4, -22.6, 21, -23); ctx.closePath(); });
    fill(ctx, pal.low, () => { ctx.moveTo(21.4, -7.2); ctx.quadraticCurveTo(25, -8.4, 30, -7.6); ctx.lineTo(30, 1); ctx.lineTo(21.4, 1); ctx.closePath(); });
    fill(ctx, "rgba(255,255,255,0.4)", () => ctx.ellipse(23, -26.2, 0.8, 2.2, 0.5, 0, TAU));
    ctx.restore();
    seam(ctx, [[21, -22.6], [22.6, -24.2], [24.2, -22.2], [25.8, -23.4], [27.6, -20.8]], 1.1 / s * 0.85);
    seam(ctx, [[21.2, -15], [22.8, -16.8], [24.4, -14.6], [26, -16.4], [28.4, -14]], 1.1 / s * 0.85);
    seam(ctx, [[21.4, -7.2], [23, -9], [24.6, -6.8], [26.2, -8.6], [28, -6.6]], 1.1 / s * 0.85);
    line(ctx, mix(pal.plate, OUT, 0.5), 0.5, [[21.4, 0], [20.8, -14], [21.6, -29]]);
    ctx.restore();
  }
  /** 背面：殼的內面（暗）、殼緣一圈材質色、兩條皮帶；殼縫從裡面透出來（細、淡一點）。 */
  function shellBack(ctx, pal) {
    const oy = 8; /* 和雲紋碑盾背面同一段（y −10～17） */
    fill(ctx, pal.plate, () => shellPath(ctx, 1, 0, oy));
    fill(ctx, pal.inner, () => shellPath(ctx, 1, 0, oy, 1.2));
    ctx.save(); ctx.beginPath(); shellPath(ctx, 1, 0, oy, 1.2); ctx.clip(); fill(ctx, dk(pal.inner, 0.25), () => ctx.rect(4.4, -12, 6, 32)); ctx.restore();
    [-10.6, -3.4, 3.4].forEach((y, v) => seam(ctx, crack(-5.6, 5, y + oy, 1.1, v), 0.7, 0.75));
    for (const y of [-1.4, 9.6]) fill(ctx, FIX.strap, () => ctx.rect(-7.6, y, 15.2, 1.5));
  }

  const FORMS = {
    sect_great: { zh: "雲紋碑盾", pal: sectPal, front: sectFront, side: sectSide, back: sectBack },
    molten_shell: { zh: "熔殼立殼", pal: shellPal, front: shellFront, side: shellSide, back: shellBack },
  };

  // ---- 鑰匙色代理（同 rgUnits.js，只在 stampDoll() 期間掛上；快取屬性另取名，不和 rgUnits.js 混用） ----
  const KEY = "#ff00ff", KEY_RE = /^#([0-9a-f]{2})00\1$/i;
  let HOOK = null;
  const realGet = HTMLCanvasElement.prototype.getContext;
  const PAINT = new Set(["fill", "stroke", "fillRect", "strokeRect"]);
  function proxy(ctx) {
    let depth = 0, mute = -1, style = null;
    return new Proxy(ctx, {
      get(t, k) {
        if (k === "save") return () => { depth++; t.save(); };
        if (k === "restore") return () => { depth--; t.restore(); if (mute >= 0 && depth < mute) mute = -1; };
        if (PAINT.has(k)) return (...a) => {
          if (mute >= 0) return undefined;
          if (k === "fill" && HOOK && style && KEY_RE.test(style)) { t.save(); HOOK.draw(t); t.restore(); mute = depth; return undefined; }
          return t[k](...a);
        };
        const v = Reflect.get(t, k);
        return typeof v === "function" ? v.bind(t) : v;
      },
      set(t, k, v) { if (k === "fillStyle") style = typeof v === "string" ? v : null; t[k] = v; return true; },
    });
  }
  /** 單位的副手：{ kind: "shield_kite", form: "tower", color: KEY, ps: { form, look } }。 */
  const psOf = (unit) => { const v = unit?.gear?.off_hand?.ps; return v && FORMS[v.form] ? v : null; };
  function withShield(unit, view, fn) {
    const ps = psOf(unit); if (!ps) return fn();
    const F = FORMS[ps.form], pal = F.pal(ps.look ?? {}), vw = view === "side" ? "side" : view === "back" ? "back" : "front";
    const saved = HTMLCanvasElement.prototype.getContext;
    HOOK = { draw: (t) => F[vw](t, pal) };
    HTMLCanvasElement.prototype.getContext = function (type, opt) { const c = realGet.call(this, type, opt); if (type !== "2d" || !c) return c; return (this.__psP ??= proxy(c)); };
    try { return fn(); } finally { HTMLCanvasElement.prototype.getContext = saved; HOOK = null; }
  }
  function stampDoll(ctx, unit, view, cx, cy, size = 1, west = false, opts = {}) { return withShield(unit, view, () => QDoll.stamp(ctx, unit, view, cx, cy, size, west, opts)); }
  /** 副手欄：玩家的新形制（look＝{ material, keywords, rarity } 或 { enemy: true }）。 */
  const offHand = (form, look = {}) => ({ slot: "off_hand", kind: "shield_kite", form: "tower", color: KEY, ps: { form, look } });

  // =====================================================================================
  // 3. Q 版圖示（48 格；照 qIconsWeapons.js 的副手：直立、外框由 QIcons.render 包、≤24px 省小零件）
  // =====================================================================================
  const HI = "rgba(255,255,255,0.45)", HI2 = "rgba(255,255,255,0.8)", SH = "rgba(0,0,0,0.22)";
  /** 雲紋碑盾圖示：碑形（淺拱頂、直邊、下緣小圓角），盾邊寬 13%（同塔盾圖示），盾心大雲紋章（直徑佔盾寬 55%），兩道盾骨、四顆銅釘（>24px）。
   *  和人物手上同一面：拱高／寬＝4／17、盾邊色、盾骨、銅釘、紋章都照 sectFront，只加粗。 */
  function sectIcon(c, o, pal) {
    const L = 9.5, R = 38.5, T = 15, B = 44, a = 9; /* 第 2 版：拱加高（誇大碑形）、盾邊 3.6 → 2.4（月白邊太寬整面讀成白色相框、材質看不出來） */
    const body = (i) => { const l = L + i, r = R - i, t = T + i * 0.7, b = B - i, aa = a - i * 0.35, cx = 24, rx = (r - l) / 2; c.moveTo(l, b - 2.4); c.lineTo(l, t); c.ellipse(cx, t, rx, aa, 0, Math.PI, 0); c.lineTo(r, b - 2.4); c.quadraticCurveTo(r, b, r - 2.4, b); c.lineTo(l + 2.4, b); c.quadraticCurveTo(l, b, l, b - 2.4); c.closePath(); };
    fill(c, pal.rim, () => body(0)); fill(c, pal.face, () => body(2.4));
    c.save(); c.beginPath(); body(2.4); c.clip();
    fill(c, mix(pal.face, "#ffffff", 0.18), () => c.rect(L, 0, 5.6, 48)); fill(c, SH, () => c.rect(R - 7.6, 0, 8, 48));
    if (!o.small) for (const y of [18.4, 37.2]) fill(c, dk(pal.rim, 0.1), () => c.rect(L, y, R - L, 1.8));
    c.restore();
    /* 雲紋章：月白圓章、青色三峰（中峰最高）、山腰月白雲、峰頂朱紅點；≤24px 省雲與紅點 */
    const r = o.small ? 8 : 7.2, cy = 27.6;
    c.save(); c.translate(24, cy);
    if (pal.ring) fill(c, pal.ring, () => c.arc(0, 0, r + 1.2, 0, TAU));
    fill(c, FIX.moon, () => c.arc(0, 0, r, 0, TAU));
    fill(c, dk(FIX.qing, 0.15), () => { c.moveTo(-r * 0.8, r * 0.46); c.lineTo(-r * 0.38, -r * 0.16); c.lineTo(-r * 0.1, r * 0.1); c.lineTo(r * 0.22, -r * 0.66); c.lineTo(r * 0.8, r * 0.46); c.closePath(); });
    if (!o.small) { line(c, FIX.moon, r * 0.18, [[-r * 0.62, r * 0.2], [-r * 0.12, r * 0.32], [r * 0.38, r * 0.12]]); fill(c, FIX.red, () => c.arc(r * 0.22, -r * 0.66, r * 0.17, 0, TAU)); fill(c, HI2, () => c.ellipse(-r * 0.42, -r * 0.5, r * 0.22, r * 0.12, -0.6, 0, TAU)); }
    c.restore();
    fill(c, HI, () => c.roundRect(L + 4, T - 2.4, 1.6, 12, 0.8));
    if (!o.small) for (const [x, y] of [[L + 5.2, T + 0.8], [R - 5.2, T + 0.8], [L + 5.2, B - 4.8], [R - 5.2, B - 4.8]]) { fill(c, dk(pal.rivet, 0.4), () => c.arc(x + 0.3, y + 0.4, 1.6, 0, TAU)); fill(c, pal.rivet, () => c.arc(x, y, 1.35, 0, TAU)); }
  }
  /** 熔殼立殼圖示：正面的蛋形殼（照 shellFront，加粗）、殼緣暗一圈、右緣露一條內面（厚度）、三道橫向鋸齒殼縫（紅＋黃芯，固定色）。 */
  function shellIcon(c, o, pal) {
    const SX = 1.75, SY = 1.42, S = [SX, SY], OX = 24, OY = 31.2; /* 殼的正面比例在圖示裡加寬（17×27 → 31×38），和碑盾同寬 */
    fill(c, pal.edge, () => shellPath(c, S, OX, OY));
    fill(c, pal.plate, () => shellPath(c, S, OX, OY, 1.25));
    c.save(); c.beginPath(); shellPath(c, S, OX, OY, 1.25); c.clip();
    fill(c, pal.lit, () => c.rect(0, 0, 48, OY - 11 * SY));
    fill(c, pal.low, () => c.rect(0, OY + 3.2 * SY, 48, 20));
    fill(c, pal.inner, () => { c.moveTo(OX + 5.4 * SX, OY - 16 * SY); c.quadraticCurveTo(OX + 9.4 * SX, OY - 4 * SY, OX + 6.2 * SX, OY + 10 * SY); c.lineTo(48, 48); c.lineTo(48, 0); c.closePath(); });
    fill(c, HI, () => c.ellipse(OX - 4.4 * SX, OY - 13 * SY, 1.9, 4.4, 0.5, 0, TAU));
    c.restore();
    const w = o.small ? 3 : 2.6, h = o.small ? 2.4 : 2.6;
    [[-10.6, -6.2, 5.2], [-3.4, -7, 5.8], [3.4, -6.4, 5.2]].forEach(([y, x0, x1], v) => { const pts = crack(OX + x0 * SX, OX + x1 * SX, OY + y * SY, h, v); line(c, mix(pal.plate, "#ffffff", 0.32), w * 0.6, pts.map(([x, yy]) => [x, yy + w * 0.75])); line(c, FIX.glow, w, pts); line(c, FIX.core, w * 0.4, pts); });
  }
  /** 圖樣定義（給 QIcons.render）：{ zh, d, meta: { badge, r } }；look 同紙娃娃（material、keywords、rarity 或 enemy）。 */
  function iconDef(form, look = {}) {
    const pal = FORMS[form].pal(look), d = form === "sect_great" ? (c, o) => sectIcon(c, o, pal) : (c, o) => shellIcon(c, o, pal);
    const r = look.enemy ? { rarity: "common", keywords: [] } : matPal(look).r;
    return { zh: FORMS[form].zh, d, meta: { badge: QIcons.badgeScale(d, 0.87), r, spots: [[17, 17], [31, 31]] } };
  }
  /** 含框的圖示（同 QIconsWeapons.paint：badge＝米色圓章、gear＝裝備格、none）。 */
  function paintIcon(ctx, form, look, size, res, opt = {}) {
    const QW = window.QIconsWeapons, d = iconDef(form, look), fr = opt.frame ?? "gear";
    ctx.save();
    if (fr === "badge") { const g = ctx.createRadialGradient(size / 2, size * 0.42, 0, size / 2, size / 2, size / 2); g.addColorStop(0, "#f6eed8"); g.addColorStop(1, "#d6c7a2"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(size / 2, size / 2, size / 2, 0, TAU); ctx.fill(); ctx.lineWidth = size / 24; ctx.strokeStyle = "#c8a868"; ctx.beginPath(); ctx.arc(size / 2, size / 2, size / 2 - size / 48, 0, TAU); ctx.stroke();
      const a = size * d.meta.badge, p = (size - a) / 2; QW.blit(ctx, QIcons.render(d, a, res, { ow: QIcons.outlinePx(size), badge: true }), p, p, a, res); }
    else if (fr === "gear") { ctx.save(); ctx.scale(size / 64, size / 64); QW.gearFrame(ctx, opt.rarity ?? d.meta.r.rarity); ctx.restore(); const p = size * QIcons.GEAR_PAD; QW.blit(ctx, QIcons.render(d, size - p * 2, res, {}), p, p, size - p * 2, res); }
    else ctx.drawImage(QIcons.render(d, size, res, {}), 0, 0, size, size);
    ctx.restore();
  }
  function iconCanvas(form, look, px, zoom = 1, opt = {}) {
    const res = opt.res ?? (zoom === 1 ? 2 : zoom), cv = document.createElement("canvas"); cv.width = cv.height = Math.round(px * res);
    const x = cv.getContext("2d"); x.scale(res, res); paintIcon(x, form, look, px, res, opt); return cv;
  }

  const setShellK = (k) => { SHELL_K = k; };
  return { FORMS, FIX, RIM_LUM, KEY, sectPal, shellPal, matPal, stampDoll, withShield, offHand, iconDef, paintIcon, iconCanvas, sectIcon, shellIcon, setShellK, lum, mix, get SHELL_K() { return SHELL_K; } };
})();
