// rgUnits.js：RG 段第二批樣張（畫圖 agent，2026-11-13）：持盾弟子的大盾、熔殼甲兵的熔殼大盾、精英單挑插圖。
// 依據 main 的 docs/phases/PhaseRG計畫.md 第 5 節表格最後三列；紀錄在 docs/art/RG樣張.md 第 9 節。
// 不改 qDoll.js、qCreature.js（只讀）：
//   - 大盾：單位的副手掛一面「鑰匙色」塔盾（shield_kite／tower，主色洋紅 #ff00ff）。qDoll 照塔盾的握法、圖層、手臂畫，
//     畫到盾的第一筆填色（鑰匙色）時，在「當下的變換」（qDoll 的盾錨點）改畫大盾，之後到那一層 restore 為止的填色、描線都不畫。
//     做法是 stampDoll() 期間把 canvas 的 2d context 換成代理（getContext 掛勾），只認鑰匙色，其他單位、其他筆畫照常。
//     所以大盾的圖層、手臂、外框、朝西換手都和現行塔盾一模一樣；移植時直接在 qGear.ts 的 shieldFront／shieldSide／shieldBack 加一個分支。
//   - 熔殼大盾：QCreature.TRAITS 加兩個特徵（molten_shield_a／_b），畫在身體之後、同一圈剪影外框裡（和 volcano、core 同一套）。
//   - 單挑插圖：精英、主角剪影由現行畫法（QDoll.stamp、QCreature.stamp）自動產生，交叉的武器呼叫 Q 版武器圖示（QIconsWeapons）。
// 座標：人物同 qDoll（腳底 (0,0)、往上 −y、頭心 (0,−29)）；異形同 qCreature（腳底 (0,0)、朝東）。確定性：沒有亂數。
window.RGUnits = (() => {
  const TAU = Math.PI * 2, OUT = "#16121a";
  const mix = (a, b, t) => { const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)); const A = p(a), B = p(b); return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, "0")).join(""); };
  const dk = (c, t = 0.25) => mix(c, "#000000", t), lt = (c, t = 0.3) => mix(c, "#ffffff", t);
  function fill(ctx, c, path) { ctx.fillStyle = c; ctx.beginPath(); path(); ctx.fill(); }
  function line(ctx, c, w, pts, cap = "round") { ctx.strokeStyle = c; ctx.lineWidth = w; ctx.lineCap = cap; ctx.lineJoin = "round"; ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke(); }

  // =====================================================================================
  // 1. 持盾弟子的大盾
  // =====================================================================================
  /** 雲嶺色票（敵人外觀.md 2 節）。 */
  const C = { qing: "#5f8f8a", moon: "#dfe4e2", ink: "#3c4248", red: "#c0392b", gray: "#8a9aa0", wood: "#7a5232", strap: "#3a2414", steel: "#c3ccd6", gold: "#e8bb48" };
  /**
   * 兩個候選（sect：盾的資料）。座標都在 qDoll 的盾錨點裡：
   *   正面＝paperdoll drawWeapon2 的 translate(手 x, −9.5)（塔盾 rr(−7.5,−16,15,21)）；側面＝shieldSide 的 translate(8.6, −13.5)；背面＝shieldBack 的 translate(手 x−1, 手 y−5)。
   * A 雲紋碑盾：上緣圓拱（碑形）、青面月白邊、盾心月白圓章裡一座三峰山＋一道雲。
   * B 太極方盾：切角長方（八角）、月白面青邊、盾心太極（墨灰／月白）圍一圈朱紅。
   */
  const SHIELDS = {
    A: { zh: "A 雲紋碑盾", face: C.qing, rim: C.moon, emblem: "peak", top: "arch" },
    B: { zh: "B 太極方盾", face: C.moon, rim: C.qing, emblem: "taiji", top: "chamfer" },
  };
  // 尺寸（模型單位）：正面寬 17、高 24（塔盾 15×21、鳶盾 14×19）；上緣到肩線（y −22.5，圓拱頂 −25.5），下緣離腳底 0.5。
  const FW = 8.5, FTOP = -13.5, FBOT = 9, ARCH = 4;
  /** 盾的外形（正面座標，x 置中）：A 碑形（上緣半橢圓拱）、B 八角（四角切 3）。i＝往內縮（畫邊框用）。 */
  function outlinePath(ctx, sh, x0, x1, top, bot, i = 0) {
    const L = x0 + i, R = x1 - i, T = top + i, B = bot - i;
    if (sh.top === "arch") {
      const a = ARCH - i * 0.4, cx = (L + R) / 2, rx = (R - L) / 2;
      ctx.moveTo(L, B - 1.2); ctx.lineTo(L, T); ctx.ellipse(cx, T, rx, a, 0, Math.PI, 0); ctx.lineTo(R, B - 1.2); ctx.quadraticCurveTo(R, B, R - 1.2, B); ctx.lineTo(L + 1.2, B); ctx.quadraticCurveTo(L, B, L, B - 1.2); ctx.closePath();
    } else {
      const c = Math.max(0.6, 3 - i * 0.5);
      ctx.moveTo(L + c, T); ctx.lineTo(R - c, T); ctx.lineTo(R, T + c); ctx.lineTo(R, B - c); ctx.lineTo(R - c, B); ctx.lineTo(L + c, B); ctx.lineTo(L, B - c); ctx.lineTo(L, T + c); ctx.closePath();
    }
  }
  /** 盾心紋樣（正面；cx, cy 圓心、r 半徑、sx 橫向壓扁＝側面的 3/4 視角）。 */
  function emblem(ctx, sh, cx, cy, r, sx = 1) {
    ctx.save(); ctx.translate(cx, cy); ctx.scale(sx, 1);
    if (sh.emblem === "peak") {
      fill(ctx, C.moon, () => ctx.arc(0, 0, r, 0, TAU));
      fill(ctx, dk(C.qing, 0.15), () => { ctx.moveTo(-r * 0.78, r * 0.42); ctx.lineTo(-r * 0.38, -r * 0.16); ctx.lineTo(-r * 0.12, r * 0.08); ctx.lineTo(r * 0.22, -r * 0.62); ctx.lineTo(r * 0.78, r * 0.42); ctx.closePath(); }); // 三峰（中峰最高）
      line(ctx, C.moon, r * 0.2, [[-r * 0.62, r * 0.18], [-r * 0.12, r * 0.3], [r * 0.36, r * 0.1]]); // 山腰一道雲
      fill(ctx, C.red, () => ctx.arc(r * 0.22, -r * 0.62, r * 0.17, 0, TAU)); // 峰頂朱紅一點
    } else {
      fill(ctx, C.red, () => ctx.arc(0, 0, r, 0, TAU));
      fill(ctx, C.moon, () => ctx.arc(0, 0, r * 0.8, 0, TAU));
      // 太極：左墨右白，上下兩個小半圓互補
      fill(ctx, C.ink, () => { ctx.arc(0, 0, r * 0.8, Math.PI / 2, Math.PI * 1.5); ctx.arc(0, -r * 0.4, r * 0.4, -Math.PI / 2, Math.PI / 2); ctx.arc(0, r * 0.4, r * 0.4, -Math.PI / 2, Math.PI / 2, true); ctx.closePath(); });
      fill(ctx, C.moon, () => ctx.arc(0, -r * 0.4, r * 0.15, 0, TAU));
      fill(ctx, C.ink, () => ctx.arc(0, r * 0.4, r * 0.15, 0, TAU));
    }
    ctx.restore();
  }
  /** 正面：盾面朝外。 */
  function front(ctx, sh) {
    const L = -FW, R = FW, rimW = 1.3;
    fill(ctx, sh.rim, () => outlinePath(ctx, sh, L, R, FTOP, FBOT));
    fill(ctx, sh.face, () => outlinePath(ctx, sh, L, R, FTOP, FBOT, rimW));
    ctx.save(); ctx.beginPath(); outlinePath(ctx, sh, L, R, FTOP, FBOT, rimW); ctx.clip();
    fill(ctx, dk(sh.face, 0.16), () => ctx.rect(R - 4.2, FTOP - ARCH, 6, FBOT - FTOP + ARCH + 2)); // 右側暗面
    fill(ctx, dk(sh.face, 0.16), () => ctx.rect(L, FBOT - 3.4, R - L, 4)); // 下緣暗面
    fill(ctx, "rgba(255,255,255,0.45)", () => ctx.roundRect(L + rimW + 0.9, FTOP + 0.2, 1.3, 9.5, 0.65)); // 左上亮面
    ctx.restore();
    // 橫帶兩道（盾骨），紋樣壓在上面
    for (const y of [FTOP + 3.2, FBOT - 5.2]) fill(ctx, dk(sh.rim, 0.1), () => ctx.rect(L + rimW, y, R - L - rimW * 2, 0.9));
    emblem(ctx, sh, 0, -3.2, 4.4);
    for (const [x, y] of [[L + 2.4, FTOP + 0.6], [R - 2.4, FTOP + 0.6], [L + 2.4, FBOT - 2.2], [R - 2.4, FBOT - 2.2]]) fill(ctx, C.gold, () => ctx.arc(x, y, 0.75, 0, TAU)); // 四顆銅釘
  }
  /** 側面：盾在胸前、轉 3/4（看得到盾邊厚度和一窄條盾面），朝東。塔盾側面 x −1.6～2.2，這裡 −2.2～5.2。 */
  function side(ctx, sh) {
    const top = -10, bot = 13.3, sx = 0.42;
    // 盾邊厚度（靠身體那一側）：本色暗一階
    fill(ctx, dk(sh.rim, 0.3), () => outlinePath(ctx, sh, -2.2, 0.6, top + 0.6, bot));
    // 盾面（壓扁的正面）：從 −0.6 到 5.2
    ctx.save(); ctx.translate(2.3, 0); ctx.scale(sx, 1);
    const L = -FW + 1.5, R = FW - 1.5;
    fill(ctx, sh.rim, () => outlinePath(ctx, sh, L, R, top, bot));
    fill(ctx, sh.face, () => outlinePath(ctx, sh, L, R, top, bot, 1.9));
    ctx.save(); ctx.beginPath(); outlinePath(ctx, sh, L, R, top, bot, 1.9); ctx.clip(); fill(ctx, dk(sh.face, 0.16), () => ctx.rect(L, bot - 3.4, R - L, 4)); ctx.restore();
    for (const y of [top + 3.2, bot - 5.2]) fill(ctx, dk(sh.rim, 0.1), () => ctx.rect(L + 1.9, y, R - L - 3.8, 0.9));
    ctx.restore();
    emblem(ctx, sh, 2.6, 0.2, 3.9, sx * 1.1);
    fill(ctx, "rgba(255,255,255,0.45)", () => ctx.roundRect(0.1, top + 0.8, 0.9, 8, 0.45));
  }
  /** 背面：看到盾背（木板＋兩條皮帶），盾在身體後面（qDoll 的圖層）。塔盾背面 rr(−7,−6,14,22)，這裡寬 17、高 24.5。 */
  function back(ctx, sh) {
    const L = -FW, R = FW, top = -7.5 + ARCH * 0, bot = 17;
    fill(ctx, dk(sh.rim, 0.25), () => outlinePath(ctx, sh, L, R, top, bot));
    fill(ctx, C.wood, () => outlinePath(ctx, sh, L, R, top, bot, 1.3));
    ctx.save(); ctx.beginPath(); outlinePath(ctx, sh, L, R, top, bot, 1.3); ctx.clip();
    for (const x of [-2.8, 2.8]) fill(ctx, dk(C.wood, 0.22), () => ctx.rect(x - 0.3, top - ARCH, 0.6, bot - top + ARCH)); // 木板縫
    fill(ctx, dk(C.wood, 0.18), () => ctx.rect(R - 3.6, top - ARCH, 5, bot - top + ARCH));
    ctx.restore();
    for (const y of [top + 4.2, bot - 6]) fill(ctx, C.strap, () => ctx.rect(L + 1.3, y, R - L - 2.6, 1.5)); // 兩條橫皮帶
  }
  const VIEW_DRAW = { front, side, back };

  // ---- 鑰匙色代理：只在 stampDoll() 期間掛上 ----
  const KEY = "#ff00ff", KEY_RE = /^#([0-9a-f]{2})00\1$/i;
  let HOOK = null; // { view, sh }
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
          if (k === "fill" && HOOK && style && KEY_RE.test(style)) { t.save(); VIEW_DRAW[HOOK.view](t, HOOK.sh); t.restore(); mute = depth; return undefined; }
          return t[k](...a);
        };
        const v = Reflect.get(t, k);
        return typeof v === "function" ? v.bind(t) : v;
      },
      set(t, k, v) { if (k === "fillStyle") style = typeof v === "string" ? v : null; t[k] = v; return true; },
    });
  }
  /** 有大盾的單位：gear.off_hand.rg＝"A"｜"B"。 */
  const shieldOf = (unit) => { const v = unit?.gear?.off_hand?.rg; return v && SHIELDS[v] ? SHIELDS[v] : null; };
  /** 在 fn() 執行期間掛上代理（fn 裡呼叫 QDoll.stamp、OccludeOutline.drawBody 都行）。 */
  function withShield(unit, view, fn) {
    const sh = shieldOf(unit);
    if (!sh) return fn();
    const saved = HTMLCanvasElement.prototype.getContext;
    HOOK = { view: view === "side" ? "side" : view === "back" ? "back" : "front", sh };
    HTMLCanvasElement.prototype.getContext = function (type, opt) { const c = realGet.call(this, type, opt); if (type !== "2d" || !c) return c; return (this.__rgP ??= proxy(c)); };
    try { return fn(); } finally { HTMLCanvasElement.prototype.getContext = saved; HOOK = null; }
  }
  /** 同 QDoll.stamp，多認大盾。 */
  function stampDoll(ctx, unit, view, cx, cy, size = 1, west = false, opts = {}) { return withShield(unit, view, () => QDoll.stamp(ctx, unit, view, cx, cy, size, west, opts)); }
  /** 持盾弟子（照持劍弟子：膚 #d9a47a、髮髻、青袍月白邊、單手劍；副手換大盾）。 */
  function sectShieldDisciple(variant = "A") {
    return { look: { skin: "#d9a47a", hair: "bun", hairColor: "#1c1c22" }, gear: { body: { kind: "robe", color: C.qing, trim: C.moon }, main_hand: { kind: "sword", material: "steel" }, off_hand: { kind: "shield_kite", form: "tower", color: KEY, rg: variant } } };
  }

  // =====================================================================================
  // 2. 熔殼甲兵（QCreature 特徵）
  // =====================================================================================
  const LAVA = { base: "#4a3631", plate: "#4a3631", rim: "#6a5048", dark: "#2e211d", glow: "#ff6a1a", core: "#ffd04a" }; /* 殼板＝熔岩甲蟲同一個玄武岩色 BASALT（qCreature.js），讀成「甲蟲的殼」；殼縫照甲蟲背上的鋸齒火紋 */
  function seam(ctx, pts, w = 1) { line(ctx, LAVA.glow, w, pts); line(ctx, LAVA.core, w * 0.38, pts); }
  /** 甲蟲的前腳扣住盾的內緣（腳色同 qCreature limb：外圈加深、內圈本色）。 */
  function grip(ctx, P, pts) { line(ctx, mix(P.base, OUT, 0.55), 2.0, pts); line(ctx, P.base, 0.9, pts); }
  /**
   * A 立殼（側看）：盾面朝前（朝敵人），側面看到的是盾的厚度＝一片往前鼓的新月形殼，高過甲蟲背（頂 −29），下緣抵地。
   *   四片殼板，三道橫向的殼縫透紅光；靠身體那一側是暗的內面，前腳從下面扣住內緣。
   * B 半圓殼盾（3/4）：盾轉向畫面，看得到半圓的殼面（扇形五片殼板、殼縫從下緣中心放射出去透紅光），立在頭前、蓋住頭與角。
   */
  const SHELL = {
    a: { zh: "A 立殼（側看新月）", draw(ctx, a, P) {
      // 外形：內緣（靠頭）近乎直立 x 18～19，外緣往前鼓到 x 28，頂端圓收在 −29
      const shape = () => { ctx.moveTo(18.2, 0); ctx.lineTo(18.6, -14); ctx.quadraticCurveTo(18.2, -25, 20.4, -28.8); ctx.quadraticCurveTo(23.6, -30, 25.6, -24.4); ctx.quadraticCurveTo(29, -15, 27.8, -5); ctx.quadraticCurveTo(27.4, -1.4, 26.4, 0); ctx.closePath(); };
      grip(ctx, P, [[12, -6.4], [16.4, -4.4], [20.6, -6]]); // 前腳從下面扣住盾的內緣（避開眼睛 (15.6, −11.6)）
      fill(ctx, LAVA.plate, shape);
      ctx.save(); ctx.beginPath(); shape(); ctx.clip();
      fill(ctx, LAVA.dark, () => { ctx.moveTo(17, 0); ctx.lineTo(17.4, -30); ctx.lineTo(21.4, -30); ctx.quadraticCurveTo(20.6, -14, 21.4, 0); ctx.closePath(); }); // 內面（靠身體那一側的厚度）
      // 四片殼板：上兩片亮一階（迎光），每片前緣一道亮邊
      fill(ctx, LAVA.rim, () => { ctx.moveTo(21.4, -30); ctx.lineTo(30, -30); ctx.lineTo(30, -20.6); ctx.quadraticCurveTo(25.4, -22.6, 21, -23); ctx.closePath(); });
      fill(ctx, dk(LAVA.plate, 0.18), () => { ctx.moveTo(21.4, -7.2); ctx.quadraticCurveTo(25, -8.4, 30, -7.6); ctx.lineTo(30, 1); ctx.lineTo(21.4, 1); ctx.closePath(); });
      fill(ctx, "rgba(255,255,255,0.4)", () => ctx.ellipse(23, -26.2, 0.8, 2.2, 0.5, 0, TAU));
      ctx.restore();
      seam(ctx, [[21, -22.6], [22.6, -24.2], [24.2, -22.2], [25.8, -23.4], [27.6, -20.8]], 1.1); /* 鋸齒殼縫（同甲蟲背上的火紋） */
      seam(ctx, [[21.2, -15], [22.8, -16.8], [24.4, -14.6], [26, -16.4], [28.4, -14]], 1.1);
      seam(ctx, [[21.4, -7.2], [23, -9], [24.6, -6.8], [26.2, -8.6], [28, -6.6]], 1.1);
      line(ctx, mix(LAVA.plate, OUT, 0.5), 0.5, [[21.4, 0], [20.8, -14], [21.6, -29]]); // 內外面的分界
    } },
    b: { zh: "B 半圓殼盾（3/4）", draw(ctx, a, P) {
      const cx = 23, rx = 6.6, ry = 24, base = 0.2, ANG = [Math.PI, -2.4, -1.85, -1.3, -0.75, 0];
      grip(ctx, P, [[12, -6.4], [15.6, -4.4], [18, -6]]);
      fill(ctx, LAVA.dark, () => { ctx.ellipse(cx - 1.6, base, rx, ry, 0, Math.PI, Math.PI * 1.5); ctx.lineTo(cx - 1.6, base); ctx.closePath(); }); // 盾的厚度
      ctx.save(); ctx.beginPath(); ctx.ellipse(cx, base, rx, ry, 0, Math.PI, 0); ctx.closePath(); ctx.clip();
      // 五片扇形殼板（從下緣中心放射），亮暗交替；右邊兩片在暗面
      const sh = [LAVA.rim, LAVA.plate, LAVA.rim, LAVA.plate, dk(LAVA.plate, 0.2)];
      for (let i = 0; i < 5; i++) fill(ctx, sh[i], () => { ctx.moveTo(cx, base); ctx.ellipse(cx, base, rx + 1, ry + 1, 0, ANG[i], ANG[i + 1]); ctx.closePath(); });
      fill(ctx, dk(LAVA.plate, 0.3), () => { ctx.ellipse(cx, base, rx, ry, 0, Math.PI, 0); ctx.ellipse(cx, base, rx - 1.1, ry - 1.5, 0, 0, Math.PI, true); ctx.closePath(); }); // 殼緣（暗一圈）
      fill(ctx, "rgba(255,255,255,0.4)", () => ctx.ellipse(cx - 3.6, -16, 0.7, 3, 0.2, 0, TAU));
      ctx.restore();
      for (const k of [0.42, 0.72]) { const pts = []; for (let i = 0; i <= 8; i++) { const ang = Math.PI + 0.2 + (i / 8) * (Math.PI - 0.4), r = k + (i % 2 ? 0.07 : 0); pts.push([cx + Math.cos(ang) * rx * r, base + Math.sin(ang) * ry * r]); } seam(ctx, pts, 0.95); } /* 兩圈拱形鋸齒殼縫（同甲蟲背上的火紋） */
      fill(ctx, LAVA.dark, () => ctx.ellipse(cx, base - 0.2, 3, 2.6, 0, Math.PI, 0)); // 盾心殼釘
      fill(ctx, LAVA.glow, () => ctx.arc(cx, base - 1.2, 0.9, 0, TAU));
    } },
  };
  /** 註冊到 QCreature.TRAITS（不改 qCreature.js：TRAITS 是匯出的物件）。 */
  function registerTraits() {
    const T = window.QCreature?.TRAITS; if (!T) return;
    T.molten_shield_a ??= { zh: "熔殼大盾 A（立殼）", draw: SHELL.a.draw };
    T.molten_shield_b ??= { zh: "熔殼大盾 B（半圓殼盾）", draw: SHELL.b.draw };
  }
  registerTraits();
  /** 熔殼甲兵：熔岩甲蟲（crawler／beetle／magma）＋熔殼大盾。 */
  const moltenShellTrooper = (variant = "a") => ({ body: "crawler", variant: "beetle", material: "magma", traits: [`molten_shield_${variant}`] });

  // =====================================================================================
  // 3. 精英單挑插圖（320×120）
  // =====================================================================================
  const DUEL_W = 320, DUEL_H = 120;
  /** 主角的架式（qDoll 姿勢鍵）：持劍的手往前舉、劍尖朝前上，重心前傾。 */
  let HERO_POSE = { arm: -0.5, wpn: 1.2, lean: 0.05 }; /* 劍往前上伸出身體外，剪影看得到劍 */
  const setHeroPose = (p) => { HERO_POSE = p; };
  /**
   * 單位 → 剪影 canvas（裝置像素；回傳 {cv, x0, y0, s}：cv 的 (0,0) 在插圖座標 (x0, y0)，每插圖 px＝res 個裝置像素）。
   * who＝{ doll, view, west } 或 { spec, west }。畫在 (cx, foot)，大小 k（插圖 px／模型單位）。
   */
  function silhouetteOf(who, cx, foot, k, res) {
    const W = 160, H = 130, lx = W / 2, ly = H - 10, R = Math.max(3, res * 2); /* 內部 R 倍畫（侵蝕、縫在高解析度做），貼上時縮回 */
    const mk = () => { const c = document.createElement("canvas"); c.width = W * R; c.height = H * R; return c; };
    const draw = (unit, npc) => { const cv = mk(), g = cv.getContext("2d"); g.scale(R, R);
      if (npc) withSilDouli(() => QNpc.stamp(g, unit, who.view ?? "side", lx, ly, k, !!who.west, { dpr: R * 1.5 })); // 有 QNpc 新部件的人形（斗笠…）
      else { if (who.pose) QDoll.setPose(who.pose); try { stampDoll(g, unit, who.view ?? "side", lx, ly, k, !!who.west, { dpr: R * 1.5 }); } finally { if (who.pose) QDoll.setPose(null); } }
      return cv; };
    if (!who.npc && !who.doll) { const cv = mk(), g = cv.getContext("2d"); g.scale(R, R); QCreature.stamp(noGround(g), who.spec, lx, ly, k, !!who.west); hard(cv, 40); /* 部件之間的半透明接縫填滿 */ return { cv, x0: cx - lx, y0: foot - ly, w: W, h: H }; }
    /* 人形（第 2 版）：
       1. 剪影去掉 qDoll／QNpc 的外框（半徑 1.3 單位）：侵蝕 1.0 單位。外框把劍身撐成一根「手指」，剪影讀成揮手（審查可修 3）。
       2. 主手武器和手、身體之間留一道輪廓光縫：拿掉主手再畫一次，相減得到「伸出身體外的武器」，往外 0.7 單位的那圈（落在身體上的部分）就是縫。
       3. 斗笠帽緣下一道縫（見 withSilDouli）。 */
    const unit = who.npc ?? who.doll, er = 1.0 * k * R;
    if (who.prop) return propSilhouette(who, unit, draw, mk, er, cx, foot, k, R, lx, ly, W, H); /* 9.9：主手不是劍（弓、弩、槍、杖）另走「道具」剪影 */
    const full = erode(draw(unit, !!who.npc), er);
    let seam = null;
    if (unit.gear?.main_hand) {
      const g0 = { ...unit.gear }; delete g0.main_hand; const bare = erode(draw({ ...unit, gear: g0 }, !!who.npc), er);
      const wpn = mk(), wg = wpn.getContext("2d"); wg.drawImage(full, 0, 0); wg.globalCompositeOperation = "destination-out"; wg.drawImage(bare, 0, 0);
      seam = mk(); const sg = seam.getContext("2d"); sg.drawImage(QNpc.dilate(wpn, 0.7 * k * R), 0, 0); sg.globalCompositeOperation = "destination-out"; sg.drawImage(wpn, 0, 0);
      sg.globalCompositeOperation = "destination-in"; sg.drawImage(full, 0, 0); hard(seam, 128);
    }
    if (who.npc && JSON.stringify(who.npc.gear?.head ?? {}).includes("douli") && (who.view ?? "side") === "side") {
      /* 斗笠帽緣下、臉那一側一道縫（模型座標 x 1.5～帽緣、y −32.2，寬 0.7）：寬帽緣和額頭分開，讀成「帽子下面一張臉」 */
      seam ??= mk(); const sg = seam.getContext("2d"), s = who.west ? -1 : 1; sg.save(); sg.scale(R, R); sg.strokeStyle = "#fff"; sg.lineWidth = 0.75 * k; sg.lineCap = "round";
      sg.beginPath(); sg.moveTo(lx + s * 1.5 * k, ly - 32.0 * k); sg.lineTo(lx + s * 10.5 * k, ly - 32.5 * k); sg.stroke(); sg.restore();
      sg.globalCompositeOperation = "destination-in"; sg.drawImage(full, 0, 0);
    }
    return { cv: full, seam, x0: cx - lx, y0: foot - ly, w: W, h: H };
  }
  // ---- 3b. 主手不是劍（RG樣張.md 9.9，RG-4 驗收 K2）：剪影組 ----
  /**
   * 剪影組：held＝紙娃娃照畫（同劍：拿掉主手相減開縫，劍走的就是這條，一行沒動）；bow／aim／staff＝「道具」剪影：
   * 紙娃娃改拿「載體」（拳套 knuckle：不是雙手武器，手臂照組別的架式往前舉，手上沒有東西伸出去），
   * 主手武器改用中間交叉的那個 Q 版武器圖示（alpha > 128 二值化）貼在手心（PROP：大小、位移、角度），不侵蝕；
   * 縫＝道具往外 0.7 單位、落在身體上的那圈（同劍）。弓、弩、槍在紙娃娃裡是抱在胸前或藏在身後，「相減」會把手臂、箭袋一起減出來，
   * 縫繞身體一圈（RG-4 驗收看到的鬼影）；杖頭的光暈在剪影裡是一顆大黑球。這三組一律拿到身體外面。
   */
  const SIL_GROUP = { bow: "bow", crossbow: "aim", longgun: "aim", shotgun: "aim", pistol: "aim", dual_pistol: "aim", staff: "staff" };
  const silGroup = (look) => SIL_GROUP[look?.kind] ?? "held";
  const CARRIER = { slot: "main_hand", kind: "fist", form: "knuckle", material: "iron" };
    /**
   * 道具（以 Q 版武器圖示當剪影，和中間交叉的那把同一個形）：px＝圖示大小（模型單位）、at＝圖示中心相對手心（模型單位，+x 朝敵人、−y 往上）、
   * rot＝圖示轉多少（斜放圖示的作用端在右上；+π/4＝轉成朝前水平）。icon＝剪影用的圖示（雙手槍畫兩把單手槍）。
   */
  const PROP = {
    bow: { px: 21, at: [3.5, -0.5], rot: Math.PI / 4 },
    crossbow: { px: 24, at: [5.5, 0.5], rot: Math.PI / 4 - 0.1 },
    longgun: { px: 27, at: [6.5, 0.5], rot: Math.PI / 4 - 0.1 },
    shotgun: { px: 25, at: [6, 0.5], rot: Math.PI / 4 - 0.1 },
    pistol: { px: 17, at: [3.8, -1.4], rot: 0.55 },
    dual_pistol: { px: 17, at: [3.8, -1.4], rot: 0.55, icon: { kind: "pistol" } },
    staff: { px: 26, at: [5, -7], rot: -Math.PI / 4 },
  };
  /** 剪影組的架式：弓、槍、弩手臂抬到肩高往前平舉（瞄準）；杖照劍的架式。 */
  const GROUP_POSE = { bow: { arm: -1.0, wpn: 1.2, lean: 0.05 }, aim: { arm: -1.0, wpn: 1.2, lean: 0.05 }, staff: { arm: -0.95, wpn: 1.2, lean: 0.05 } };
  /** 載體拿在手上時，手心在 R 倍 canvas 的位置（qDoll 的 probe；只取拳套那一筆）。 */
  function handOf(unit, pose, k, R, lx, ly) {
    let m = null; const c = document.createElement("canvas"); c.width = c.height = 4; const g = c.getContext("2d");
    g.scale(R, R); g.translate(lx, ly); g.scale(k, k);
    QDoll.setPose({ ...(pose ?? {}), probe: (kind, h, t, v, o, mm) => { if (kind === "gauntlet" && !m) m = mm; } });
    try { QDoll.draw(g, unit, "side"); } finally { QDoll.setPose(null); }
    return m ? [m.e, m.f] : [lx * R, (ly - 20) * R];
  }
  function propCanvas(mk, look, hand, s, extra = [0, 0]) {
    const P0 = PROP[look.kind], icon = { ...look, ...(P0.icon ?? {}) }, d = Math.round(P0.px * s);
    const ic = document.createElement("canvas"); ic.width = ic.height = d; QIconsWeapons.paint(ic.getContext("2d"), icon, d, 1, { frame: "none" });
    const cv = mk(), g = cv.getContext("2d");
    g.translate(hand[0], hand[1]); g.scale(s, s); g.translate(P0.at[0] + extra[0], P0.at[1] + extra[1]); g.rotate(P0.rot);
    g.drawImage(ic, -P0.px / 2, -P0.px / 2, P0.px, P0.px);
    return hard(cv, 128); /* 圖示的半透明光暈、亮點不算進剪影 */
  }
  function propSilhouette(who, unit, draw, mk, er, cx, foot, k, R, lx, ly, W, H) {
    const look = unit.gear.main_hand, gear = { ...unit.gear, main_hand: CARRIER };
    if (look.kind === "bow" && !gear.back) gear.back = { slot: "back", kind: "quiver", material: "leather" }; /* 弓手照紙娃娃背箭袋（箭羽露在後腦旁） */
    const carry = { ...unit, gear };
    const body = erode(draw(carry, false), er);
    const hand = handOf(carry, who.pose, k, R, lx, ly), s = k * R;
    /* 雙手槍：遠側那把（往前 1.5、往下 4.5）先畫，近側那把蓋在上面、兩把之間也開縫 */
    const props = look.kind === "dual_pistol" ? [propCanvas(mk, look, hand, s, [1.5, 4.5]), propCanvas(mk, look, hand, s)] : [propCanvas(mk, look, hand, s)];
    const seam = mk(), sg = seam.getContext("2d");
    const ring = (p, under) => { const r = mk(), rg = r.getContext("2d"); rg.drawImage(QNpc.dilate(p, 0.7 * s), 0, 0); rg.globalCompositeOperation = "destination-out"; rg.drawImage(p, 0, 0); rg.globalCompositeOperation = "destination-in"; rg.drawImage(under, 0, 0); return r; };
    const full = mk(), fg = full.getContext("2d"); fg.drawImage(body, 0, 0);
    for (const p of props) { sg.globalCompositeOperation = "destination-out"; sg.drawImage(p, 0, 0); sg.globalCompositeOperation = "source-over"; sg.drawImage(ring(p, full), 0, 0); fg.drawImage(p, 0, 0); }
    hard(seam, 128);
    return { cv: full, seam, x0: cx - lx, y0: foot - ly, w: W, h: H };
  }
  /** 侵蝕 r 像素（反相 → 膨脹 → 反相；膨脹用 QNpc.dilate＝qDoll 外框同一套 12 方向圓盤）。 */
  function erode(src, r) {
    const inv = (c0) => { const c = document.createElement("canvas"); c.width = c0.width; c.height = c0.height; const g = c.getContext("2d"); g.fillStyle = "#000"; g.fillRect(0, 0, c.width, c.height); g.globalCompositeOperation = "destination-out"; g.drawImage(c0, 0, 0); return c; };
    return hard(inv(QNpc.dilate(inv(src), r)), 128);
  }
  /** alpha 二值化（內部 R 倍解析度；縮回插圖大小時才有平滑邊）。膨脹、侵蝕的半透明邊會一路變寬，不切會在墨色剪影外透出一圈輪廓光色。 */
  function hard(c, th) {
    const g = c.getContext("2d"), d = g.getImageData(0, 0, c.width, c.height), q = d.data;
    for (let i = 3; i < q.length; i += 4) q[i] = q[i] > th ? 255 : 0;
    g.putImageData(d, 0, 0); return c;
  }
  /**
   * 插圖剪影專用的斗笠側面（第 2 版，審查可修 1）：現行 qNpc.js 的側面斗笠帽緣只比頭寬 1.5～4 單位、尖頂高，剪影讀成「方塊上一個屋頂」。
   * 剪影時換成寬帽緣（後 −15.2、前 +16.8，往前低 2 單位＝帽子微微前傾）、矮錐頂（−41.6）、帽緣下有厚度 1.2；
   * 前緣比臉（鼻尖 x ≈ 9.8）多伸 7 單位，帽緣下、臉前面留出一個缺口。戰場上的 sprite 不換（qNpc.js 只讀）。
   */
  const SIL_DOULI = { C(ctx, v, p) {
    if (v !== "side") return DOULI0.C(ctx, v, p);
    const c = p.color ?? "#c8b07a", d = dk(c, 0.22);
    fill(ctx, c, () => { ctx.moveTo(-15.2, -35.4); ctx.quadraticCurveTo(-6, -40.6, 0.6, -41.6); ctx.quadraticCurveTo(8, -39.6, 16.8, -33.4); ctx.lineTo(16.4, -32.4); ctx.quadraticCurveTo(0, -34.0, -14.8, -34.4); ctx.closePath(); });
    fill(ctx, d, () => { ctx.moveTo(16.4, -32.4); ctx.quadraticCurveTo(0, -34.0, -14.8, -34.4); ctx.lineTo(-14.6, -35.0); ctx.quadraticCurveTo(0, -34.8, 16.6, -33.2); ctx.closePath(); });
  } };
  let DOULI0 = null;
  function withSilDouli(fn) { DOULI0 = QNpc.PART.douli; QNpc.PART.douli = SIL_DOULI; try { return fn(); } finally { QNpc.PART.douli = DOULI0; } }
  /** QCreature.stamp 會先畫地面環與影子（直接上色的前幾筆）：全部跳過，只留 layer 貼上的身體（同 occludeOutline.js skipPaint(ctx, Infinity)）。 */
  function noGround(ctx) {
    const P = new Set(["fill", "stroke", "fillRect", "strokeRect"]);
    return new Proxy(ctx, { get(t, p) { if (P.has(p)) return () => undefined; const v = Reflect.get(t, p); return typeof v === "function" ? v.bind(t) : v; }, set(t, p, v) { t[p] = v; return true; } });
  }
  function tinted(src, color) { const c = document.createElement("canvas"); c.width = src.width; c.height = src.height; const g = c.getContext("2d"); g.drawImage(src, 0, 0); g.globalCompositeOperation = "source-in"; g.fillStyle = color; g.fillRect(0, 0, c.width, c.height); return c; }
  /** 交叉的武器：主角的主手＋精英的主手（異形用爪 fist／claw／bone）。每把是 Q 版武器圖示（無框），精英那把左右鏡像。 */
  function weaponCanvas(look, px, res) { const cv = document.createElement("canvas"); cv.width = cv.height = Math.round(px * res); const g = cv.getContext("2d"); g.scale(res, res); if (look.kind === "beast_claw") beastClaw(g, px); else QIconsWeapons.paint(g, look, px, res, { frame: "none" }); return cv; }
  /**
   * 異形精英的「武器」（第 2 版，審查必修 M2-1）：三道骨白彎弧爪痕。第 1 版「三根爪＋褐色掌」1 倍讀成書本、羽毛，已拿掉掌。
   * 48 格畫法：外框 #16121a（寬 2.4，第 3 版）、骨 #e9e3cf、凹側暗面 #a8a08a、凸側亮線白 75%。三道平行、由粗到尖（入爪端粗、收尾細），
   * 中間那道最長。畫的方向和 Q 版劍圖示同一條斜線（左下－右上）；crossed() 把精英那把左右鏡像，所以實際是「右上往左下」的
   * 另一條斜線，和主角的劍交叉成 X（爪痕蓋在劍上，劍柄、劍尖在兩端露出）。
   */
  function beastClaw(g, px) {
    g.save(); g.scale(px / 48, px / 48); g.translate(24, 24); g.rotate(Math.PI / 4); /* 軸線＝劍圖示的斜線；-y＝右上 */
    /* 一道爪痕：軸 x＝ox，從 (ox, top) 到 (ox, bot)，往 +x 彎 b；入爪端（top）粗、尾端（bot）尖。edge(-1) 凹側、edge(+1) 凸側 */
    const slash = (ox, top, bot, w, b) => {
      const L = bot - top, y1 = top + L * 0.3, y2 = top + L * 0.68;
      return (sc = 1) => { const ww = w * sc;
        g.moveTo(ox + 0.2, top);
        g.bezierCurveTo(ox + b + ww * 0.9, y1, ox + b + ww * 0.55, y2, ox, bot);
        g.bezierCurveTo(ox + b - ww * 0.35, y2, ox + b - ww * 0.55, y1, ox - 0.2, top);
        g.closePath(); };
    };
    const OX = [-17, -8, 1], LN = [[-14.5, 15], [-21, 21], [-17, 17]] /* 最靠劍尖那道兩端收短，不出 48 格 */, WD = [2.7, 3.1, 2.7], BD = [3.4, 4, 3.4]; /* 第 3 版：間距 9（1 倍縫 ≥ 2 px，劍身從縫裡露出）；長到接近劍長、兩端伸出劍的兩側；中心 -8＝劍身中段（鏡像後往劍尖那頭） */
    const S3 = OX.map((ox, i) => slash(ox, LN[i][0], LN[i][1], WD[i], BD[i]));
    g.lineJoin = "round"; g.strokeStyle = OUT; g.lineWidth = 2.4;
    for (const t of S3) { g.beginPath(); t(); g.stroke(); }
    for (const t of S3) fill(g, "#e9e3cf", () => t());
    /* 凹側暗面：同一道往 -x 縮一半寬 */
    for (const [i, t] of S3.entries()) { g.save(); g.beginPath(); t(); g.clip(); g.translate(-[2, 2.4, 2][i], 0); fill(g, "#a8a08a", () => t(0.75)); g.restore(); }
    /* 凸側亮線 */
    for (const [i, ox] of OX.entries()) { const [top, bot] = LN[i], b = BD[i];
      const L = bot - top; g.save(); g.strokeStyle = "rgba(255,255,255,0.75)"; g.lineWidth = 0.9; g.lineCap = "round"; g.beginPath(); g.moveTo(ox + 1.3, top + L * 0.14); g.quadraticCurveTo(ox + b + 1.4, top + L * 0.42, ox + 1.2, top + L * 0.66); g.stroke(); g.restore();
    }
    g.restore();
  }
  const isDiag = (look) => { if (look.kind === "beast_claw") return true; try { return !!QIconsWeapons.def(look).meta.diag; } catch (e) { return true; } };
  function crossed(ctx, heroW, eliteW, cx, cy, px0, res, mode, es = null) {
    const put = (look, mirror, k = 1, dx = 0, dy = 0) => {
      const px = px0 * k, c0 = weaponCanvas(look, px, res), c = mode === "flat" ? tinted(c0, "#f2e6c8") : c0;
      ctx.save(); ctx.translate(cx + dx, cy + dy); if (mirror) ctx.scale(-1, 1); if (!isDiag(look)) ctx.rotate(0.62);
      if (mode === "flat") { const o = tinted(c0, OUT); for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) ctx.drawImage(o, -px / 2 + dx * 0.9, -px / 2 + dy * 0.9, px, px); }
      ctx.drawImage(c, -px / 2, -px / 2, px, px); ctx.restore();
    };
    const claw = eliteW.kind === "beast_claw", F = mode !== "flat" && faceOf(heroW)?.[claw ? "claw" : "man"];
    if (F) { /* 9.9：不是長條斜放的主手（弓、拳套、手槍、成對…）：兩把錯開、只在邊上交疊，不疊在對方的主體上 */
      if (claw) { const sh = es ? clawShift(es, eliteW, F, cx, cy, px0, res) : 0; /* 9.9 D-2：爪痕右緣不越過精英剪影左緣 −3 px，只往左移 */ put(heroW, false, F.k, ...F.hero); put(eliteW, true, F.ek, F.elite[0] - sh, F.elite[1]); } else { put(eliteW, true, F.ek, ...F.elite); put(heroW, false, F.k, ...F.hero); }
      return;
    }
    /* 爪痕蓋在劍上（第 2 版）：劍蓋上去會把三道爪痕的中段切成六根尖刺，讀成羽毛扇；爪痕在上，劍從爪痕之間、兩端露出 */
    /* 第 3 版：異形精英的爪痕蓋在劍上、從劍身中段劃過，劍放大 1.12 倍讓劍身夠長、三道爪痕之間露得出鋼色；人形照舊先畫精英再畫主角 */
    if (claw) { put(heroW, false, 1.12); put(eliteW, true); } else { put(eliteW, true); put(heroW, false); }
  }
  // ---- 3b. 主手不是劍（RG樣張.md 9.9）：交叉組 ----
  /**
   * 交叉組（主角主手 → 和精英怎麼交叉）：
   *   blade＝長條、刃在前段（劍、巨劍、魔導劍、矛）：照劍（9.8 第 4 條），不在表裡；
   *   head＝頭重的長柄（斧、錘、鐮刀、三種杖）：爪痕改劃在柄上、主角那把往右上推，斧頭、錘頭、杖頭整個露出來；
   *   gun＝長槍（火槍、霰彈槍）：爪痕劃在槍管前段、主角那把往左下拉，槍托、扳機、護弓露出來；
   *   open＝有開口的（弓、弩、鞭）：和獸爪錯開，只在邊上交疊（疊在中間會把弓弦、弩臂關成籠子）；人形照劍交叉；
   *   block＝塊狀或自帶 X 的（拳套、匕首、雙匕首、手槍、雙手槍）：異形、人形都錯開，主角那把縮小。
   */
  const CROSS_GROUP = { axe: "head", hammer: "head", scythe: "head", staff: "head", longgun: "gun", shotgun: "gun", bow: "open", crossbow: "open", whip: "open", fist: "block", dagger: "block", dual_dagger: "block", pistol: "block", dual_pistol: "block" };
  const crossGroup = (look) => CROSS_GROUP[look?.kind] ?? "blade";
  /** 第 2 版（審查 D-1、D-3）：同組裡個別 kind 的例外。鞭對人形照劍（刀從鞭圈裡穿過、整把看得到），所以不帶 man；霰彈槍的爪痕劃在槍身中段，喇叭口和槍托都露出來。 */
  const FACE_KIND = {
    whip: { claw: { hero: [-14, 4], elite: [11, -3], k: 0.92, ek: 0.92 } },
    shotgun: { claw: { hero: [1, -1], elite: [-2, 2], k: 1.08, ek: 1 } },
  };
  const faceOf = (look) => FACE_KIND[look?.kind] ?? FACE[crossGroup(look)];
  /**
   * 審查 D-2：錯開組（FACE 有值）的爪痕，右緣不越過精英剪影（含 1.6 px 輪廓光）在同一列的最左緣 −3 px；超過就整組往左移（不縮小）。
   * 回傳要往左移的插圖 px。劍那組不走這裡（指紋不動）。
   */
  function clawShift(es, eliteW, F, cx, cy, px0, res) {
    const W = DUEL_W * res, H = DUEL_H * res, mkc = () => { const c = document.createElement("canvas"); c.width = W; c.height = H; return c; };
    const cc = mkc(), cg = cc.getContext("2d"), px = px0 * F.ek; cg.scale(res, res); cg.translate(cx + F.elite[0], cy + F.elite[1]); cg.scale(-1, 1); cg.drawImage(weaponCanvas(eliteW, px, res), -px / 2, -px / 2, px, px);
    const ec = mkc(), eg = ec.getContext("2d"); eg.scale(res, res); eg.drawImage(es.cv, es.x0 - 1.6, es.y0 - 0.6, es.w, es.h); eg.drawImage(es.cv, es.x0, es.y0, es.w, es.h);
    const a = cg.getImageData(0, 0, W, H).data, b = eg.getImageData(0, 0, W, H).data;
    let need = 0;
    for (let y = 0; y < H; y++) {
      let cr = -1, el = -1;
      for (let x = W - 1; x >= 0; x--) if (a[(y * W + x) * 4 + 3] > 64) { cr = x; break; }
      if (cr < 0) continue;
      for (let x = 0; x < W; x++) if (b[(y * W + x) * 4 + 3] > 64) { el = x; break; }
      if (el >= 0) need = Math.max(need, cr - (el - 3 * res));
    }
    return Math.ceil(need) / res;
  }
  /** 錯開：hero／elite＝[dx, dy]（插圖 px，交叉中心為原點）、k／ek＝主角／精英圖示倍率；claw＝異形（獸爪）、man＝人形（沒寫＝照劍交叉）。 */
  const FACE = {
    head: { claw: { hero: [6, -6], elite: [-3, 3], k: 1.05, ek: 1 } },
    gun: { claw: { hero: [-5, 5], elite: [4, -4], k: 1.08, ek: 1 } },
    open: { claw: { hero: [-14, 4], elite: [11, -3], k: 0.92, ek: 0.92 }, man: { hero: [-14, 5], elite: [10, -4], k: 0.8, ek: 0.95 } }, /* 第 2 版 D-1：弓、弩對人形也錯開（鞭見 FACE_KIND） */
    block: { claw: { hero: [-14, 4], elite: [11, -3], k: 0.88, ek: 0.92 }, man: { hero: [-14, 5], elite: [10, -4], k: 0.8, ek: 0.95 } },
  };
  /** 四芒星火花（交叉點）。 */
  function spark(ctx, x, y, r, c1 = "#fff7c0", c2 = "#ffffff") {
    const star = (rr, w) => { ctx.beginPath(); for (let i = 0; i < 8; i++) { const a = (i * Math.PI) / 4 - Math.PI / 2, q = i % 2 ? w : rr; ctx.lineTo(x + Math.cos(a) * q, y + Math.sin(a) * q); } ctx.closePath(); };
    ctx.save(); ctx.fillStyle = c1; star(r, r * 0.28); ctx.fill(); ctx.fillStyle = c2; star(r * 0.55, r * 0.16); ctx.fill(); ctx.restore();
  }
  /** 區域背景色（A 暮色：天、遠山、霧／餘燼光、地面）。 */
  const SKY = {
    cloud_ridge: { top: "#22363a", mid: "#4f6f6c", glow: "#d8d4b0", far: "#3a5552", near: "#1e2c2a", ground: "#1a2422", haze: "rgba(230,236,232,0.28)" },
    ashen_waste: { top: "#1e1210", mid: "#5a2a1a", glow: "#ff9a4a", far: "#3a1e18", near: "#24140f", ground: "#1c100c", haze: "rgba(255,140,60,0.22)" },
  };
  function farHills(ctx, reg, c) {
    ctx.fillStyle = c; ctx.beginPath(); ctx.moveTo(0, 92);
    const pts = reg === "ashen_waste" ? [[0, 84], [30, 80], [44, 70], [70, 70], [84, 80], [130, 82], [150, 74], [170, 76], [196, 84], [236, 80], [250, 66], [266, 60], [282, 66], [296, 78], [320, 80]] : [[0, 78], [22, 60], [40, 70], [60, 48], [84, 66], [110, 74], [138, 62], [160, 70], [190, 56], [214, 40], [238, 62], [262, 70], [288, 54], [306, 64], [320, 58]];
    for (const p of pts) ctx.lineTo(...p); ctx.lineTo(320, 92); ctx.closePath(); ctx.fill();
  }
  /**
   * 插圖。spec：{ hero: {doll, weapon}, elite: {doll|spec, weapon, zh}, region, variant: "A"｜"B" }。畫在 (0,0)～(320,120)。
   * A 暮色對峙：區域天色＋遠山＋地平線光；兩個剪影墨色（#16121a）、朝中間那一側描一道輪廓光（主角 #a9ccff 我方環色、精英 #ffbf3a 精英金）；
   *   中間交叉的武器用 Q 版武器圖示的本色、交叉點火花。
   * B 對角徽記：深藍底，左上我方藍、右下敵方紅兩片斜切，中間一道金斜線；剪影填陣營色（主角 #a9ccff、精英 #ffbf3a），墨色投影；
   *   交叉的武器壓成米白剪影（墨色外框），背後一圈金環當徽記。
   */
  function duel(ctx, spec, res = 2) {
    const W = DUEL_W, H = DUEL_H, reg = SKY[spec.region] ? spec.region : "cloud_ridge", sk = SKY[reg], A = spec.variant !== "B";
    const foot = 112, heroX = 72, eliteX = 250, kH = 1.9, kE = spec.elite.spec ? spec.elite.k ?? 1.5 : 1.9 * 1.15;
    ctx.save(); ctx.beginPath(); ctx.roundRect(0, 0, W, H, 6); ctx.clip();
    if (A) {
      const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, sk.top); g.addColorStop(0.62, sk.mid); g.addColorStop(0.8, sk.glow); g.addColorStop(0.81, sk.near); g.addColorStop(1, sk.ground);
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      const r = ctx.createRadialGradient(W / 2, 92, 4, W / 2, 92, 120); r.addColorStop(0, hexA(sk.glow, 0.55)); r.addColorStop(1, hexA(sk.glow, 0)); ctx.fillStyle = r; ctx.fillRect(0, 0, W, H);
      farHills(ctx, reg, sk.far);
      ctx.fillStyle = sk.near; ctx.beginPath(); ctx.moveTo(0, 104); ctx.quadraticCurveTo(80, 96, 160, 99); ctx.quadraticCurveTo(240, 102, 320, 96); ctx.lineTo(320, 120); ctx.lineTo(0, 120); ctx.closePath(); ctx.fill();
      ctx.fillStyle = sk.haze; ctx.fillRect(0, 86, W, 8);
    } else {
      ctx.fillStyle = "#18203a"; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = "rgba(47,111,208,0.42)"; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(186, 0); ctx.lineTo(134, H); ctx.lineTo(0, H); ctx.closePath(); ctx.fill();
      ctx.fillStyle = "rgba(198,59,59,0.42)"; ctx.beginPath(); ctx.moveTo(192, 0); ctx.lineTo(W, 0); ctx.lineTo(W, H); ctx.lineTo(140, H); ctx.closePath(); ctx.fill();
      line(ctx, "#e8bb48", 2, [[189, -2], [137, H + 2]], "butt");
      const v = ctx.createRadialGradient(W / 2, H / 2, 40, W / 2, H / 2, 190); v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(0,0,0,0.45)"); ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = "rgba(0,0,0,0.35)"; ctx.beginPath(); ctx.ellipse(heroX, foot, 30, 4, 0, 0, TAU); ctx.ellipse(eliteX, foot, 38, 4.5, 0, 0, TAU); ctx.fill();
    }
    const hs = silhouetteOf({ doll: spec.hero.doll, view: "side", west: false, pose: spec.hero.pose ?? (GROUP_POSE[silGroup(spec.hero.doll.gear?.main_hand)] ?? HERO_POSE), prop: silGroup(spec.hero.doll.gear?.main_hand) !== "held" }, heroX, foot, kH, res);
    const es = silhouetteOf(spec.elite.spec ? { spec: spec.elite.spec, west: true } : { doll: spec.elite.doll, npc: spec.elite.npc, view: "side", west: true }, eliteX, foot, kE, res);
    const put = (s, c, dx = 0, dy = 0) => { ctx.save(); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high"; ctx.drawImage(c, s.x0 + dx, s.y0 + dy, s.w, s.h); ctx.restore(); };
    if (A) {
      // 輪廓光：朝中間那側位移 1.6 px 的亮色剪影墊在下面，再蓋墨色剪影
      put(hs, tinted(hs.cv, "#a9ccff"), 1.6, -0.6); put(hs, tinted(hs.cv, OUT));
      put(es, tinted(es.cv, "#ffbf3a"), -1.6, -0.6); put(es, tinted(es.cv, OUT));
      /* 第 2 版：武器和手之間、斗笠帽緣下的輪廓光縫（同一側的輪廓光色） */
      if (hs.seam) put(hs, tinted(hs.seam, "#a9ccff"));
      if (es.seam) put(es, tinted(es.seam, "#ffbf3a"));
    } else {
      put(hs, tinted(hs.cv, OUT), 2, 2); put(hs, tinted(hs.cv, "#a9ccff"));
      put(es, tinted(es.cv, OUT), -2, 2); put(es, tinted(es.cv, "#ffbf3a"));
    }
    // 交叉的武器
    const cx = W / 2, cy = 56;
    if (A) {
      const r = ctx.createRadialGradient(cx, cy, 2, cx, cy, 34); r.addColorStop(0, "rgba(255,240,200,0.55)"); r.addColorStop(1, "rgba(255,240,200,0)"); ctx.fillStyle = r; ctx.fillRect(cx - 40, cy - 40, 80, 80);
      crossed(ctx, spec.hero.weapon, spec.elite.weapon, cx, cy, 58, res, "color", es);
      if (spec.elite.weapon?.kind !== "beast_claw") spark(ctx, cx, cy - 9, 7); /* 第 3 版：爪痕那組不加火花（白色火花疊在白爪痕上，整組更像一團白毛） */
    } else {
      ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, 27, 0, TAU); ctx.fillStyle = "rgba(10,12,24,0.7)"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = "#e8bb48"; ctx.stroke(); ctx.beginPath(); ctx.arc(cx, cy, 23.5, 0, TAU); ctx.lineWidth = 0.8; ctx.strokeStyle = "rgba(232,187,72,0.6)"; ctx.stroke(); ctx.restore();
      crossed(ctx, spec.hero.weapon, spec.elite.weapon, cx, cy, 50, res, "flat");
    }
    ctx.restore();
    // 框：1px 金邊（同事件插圖小牌外框色 #8a6a3a），內側一道暗線
    ctx.save(); ctx.lineWidth = 1; ctx.strokeStyle = "#8a6a3a"; ctx.beginPath(); ctx.roundRect(0.5, 0.5, W - 1, H - 1, 6); ctx.stroke(); ctx.strokeStyle = "rgba(0,0,0,0.5)"; ctx.beginPath(); ctx.roundRect(1.5, 1.5, W - 3, H - 3, 5); ctx.stroke(); ctx.restore();
  }
  function hexA(h, a) { const n = parseInt(h.slice(1, 7), 16); return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`; }
  function duelCanvas(spec, res = 2) { const cv = document.createElement("canvas"); cv.width = DUEL_W * res; cv.height = DUEL_H * res; const g = cv.getContext("2d"); g.scale(res, res); duel(g, spec, res); return cv; }

  return { beastClaw, SHIELDS, SHELL, C, LAVA, KEY, stampDoll, withShield, shieldOf, sectShieldDisciple, moltenShellTrooper, registerTraits, duel, duelCanvas, silhouetteOf, setHeroPose, DUEL_W, DUEL_H, VIEW_DRAW };
})();
