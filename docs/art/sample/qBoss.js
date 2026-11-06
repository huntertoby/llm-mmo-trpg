// qBoss.js：兩位頭目的 Q 版（畫圖 agent，2026-11-07）：灰燼之心、碎晶之主。結構照 bossArt.js（C 版）：「部件＋掛點」，
//   每塊殼片、每片浮晶都是一個部件，有自己的掛點（位置、旋轉），動畫只改掛點；狀態物件 st 的欄位和 bossArt.js 完全相同，可以直接替換。
// Q 版畫法：純色平塗、部件細縫線、整隻剪影粗外框（QCreature.layer，1.3 單位 #16121a，和 Q 版主角同粗）；不用漸層、不排線。
//   光（核心光暈、熔岩光、灌注光束）改成平塗的半透明同心圓／色帶。頭目外光（外光只代表頭目）＝剪影膨脹的平塗光，預設傳說金 #ffbf3a。
// 確定性：殼片脫落方向、碎晶相位都由部件名稱雜湊（FNV-1a）決定，不用 Math.random。不認得的 phase → 1；數值欄位缺 → 預設。
window.QBoss = (() => {
  const QC = window.QCreature, { mix, light, dark, OUT, layer, ring } = QC;
  const TAU = Math.PI * 2;
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  function seedOf(s) { let h = 2166136261; for (const ch of s) h = Math.imul(h ^ (ch.codePointAt(0) ?? 0), 16777619); return h >>> 0; }
  const rnd = (key, k = 0) => (seedOf(`${key}:${k}`) % 10000) / 10000;
  const num = (v, d) => (typeof v === "number" && Number.isFinite(v) ? v : d);
  const seam = (c) => mix(c, OUT, 0.55);
  function poly(g, pts, c, opt = {}) { g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.closePath(); g.fillStyle = c; g.fill(); if (opt.line !== false) { g.strokeStyle = seam(c); g.lineWidth = 0.6; g.lineJoin = "round"; g.stroke(); } }
  function ell(g, x, y, rx, ry, c, opt = {}) { g.beginPath(); g.ellipse(x, y, rx, ry, opt.rot ?? 0, 0, TAU); g.fillStyle = c; g.fill(); if (opt.line !== false) { g.strokeStyle = seam(c); g.lineWidth = 0.6; g.stroke(); } }
  function line(g, pts, w, c) { g.save(); g.strokeStyle = c; g.lineWidth = w; g.lineCap = "round"; g.lineJoin = "round"; g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.stroke(); g.restore(); }
  /** 平塗光暈：3 圈半透明同心圓（取代 C 的放射漸層）。 */
  function flatGlow(ctx, x, y, r, c, a) { ctx.save(); ctx.fillStyle = c; for (const [k, al] of [[1, 0.16], [0.72, 0.2], [0.46, 0.26]]) { ctx.globalAlpha = al * a; ctx.beginPath(); ctx.arc(x, y, r * k, 0, TAU); ctx.fill(); } ctx.restore(); }
  const GOLD = "#ffbf3a";

  // =========================== 灰燼之心 ===========================
  const BASALT = "#4a3b36", BASALT_L = "#6a5a52", LAVA = "#ff6a1a", LAVA_HOT = "#ffd23a", CORE = "#ffb23a";
  /** 殼片：[名稱, 掛點 x, 掛點 y, 旋轉, 寬, 高]（和 bossArt.js 的 PLATES 同一份）。 */
  const PLATES = [
    ["p-back-l", -20, -34, -0.5, 18, 13], ["p-back-r", 20, -34, 0.5, 18, 13], ["p-top", 0, -44, 0, 20, 12],
    ["p-left", -26, -20, -0.9, 16, 14], ["p-right", 26, -20, 0.9, 16, 14],
    ["p-low-l", -18, -8, -0.3, 20, 12], ["p-low-r", 18, -8, 0.3, 20, 12], ["p-front", 0, -12, 0, 22, 12],
    ["p-mid-l", -12, -30, -0.2, 14, 11], ["p-mid-r", 12, -30, 0.2, 14, 11],
  ];
  /** 一片甲蟲殼（Q）：圓圓的背甲＋中線＋一條鋸齒殼縫（熱度越高越黃）＋左上一塊亮面。 */
  function plate(g, w, h, heat) {
    ell(g, 0, 0, w / 2, h / 2, BASALT_L);
    g.save(); g.beginPath(); g.ellipse(0, 0, w / 2, h / 2, 0, 0, TAU); g.clip();
    ell(g, -w * 0.16, -h * 0.18, w * 0.22, h * 0.16, light(BASALT_L, 0.22), { line: false, rot: -0.3 });
    g.restore();
    line(g, [[0, -h / 2 + 0.8], [0, h / 2 - 0.8]], 0.9, OUT);
    const z = [[-w * 0.34, 0.6], [-w * 0.17, -1.2], [0, 1], [w * 0.17, -1], [w * 0.34, 0.8]];
    line(g, z, 2, "#7a2a08"); line(g, z, 1, mix(LAVA, LAVA_HOT, clamp(heat)));
  }
  function core(g, cx, cy, breath, crack) {
    const s = 1 + 0.06 * breath;
    g.save(); g.translate(cx, cy); g.scale(s, s);
    const pts = [[0, -15], [10, -8], [11, 4], [4, 13], [-6, 12], [-11, 3], [-9, -9]];
    const c = mix(CORE, "#fff4d0", 0.35 * breath + 0.4 * crack);
    poly(g, pts, c);
    g.save(); g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.closePath(); g.clip();
    poly(g, [[0, -15], [-9, -9], [-11, 3], [1, 0]], light(c, 0.35), { line: false }); // 亮面
    poly(g, [[11, 4], [4, 13], [1, 0]], dark(c, 0.12), { line: false }); // 暗面（一塊色，不排線）
    g.restore();
    g.fillStyle = "#ffffff"; g.fillRect(-5, -9, 2.2, 4.4); g.fillRect(-2, -10.4, 1.4, 1.4);
    if (crack > 0) { g.save(); g.globalAlpha = clamp(crack); line(g, [[-2, -12], [2, -4], [-1, 3], [3, 10]], 1.6, "#ffffff"); line(g, [[8, -6], [3, -2], [7, 6]], 1.3, "#fff4c0"); g.restore(); }
    g.restore();
  }
  /** 殼片的掛點（位置、旋轉、透明）：熔殼在＝貼著並隨呼吸張開；脫落＝依名稱雜湊飛出、落地。動畫只改這三個值。 */
  function plateAnchor(p, shell, bt, breath) {
    const [key, x, y, r] = p;
    if (shell > 0) { const open = 0.6 * breath; return { x: x * (1 + 0.02 * open), y: y - open * 0.6, r, a: 1 }; }
    const dir = Math.sign(x || rnd(key) - 0.5) || 1, vx = dir * (16 + 22 * rnd(key, 1)), vy = -(18 + 18 * rnd(key, 2)), spin = (rnd(key, 3) - 0.5) * 6;
    if (bt >= 1) return { x: x * 1.6 + dir * 8, y: -2 - 2 * rnd(key, 4), r: r + spin * 0.8, a: 0.8 };
    const tt = clamp(bt) * 0.9;
    return { x: x + vx * tt, y: Math.min(-2, y + vy * tt + 70 * tt * tt), r: r + spin * tt, a: 1 };
  }
  /**
   * 灰燼之心（Q）。st：同 bossArt.js {phase: 1|2|3, shell: 0～1, breakT: 0～1, t: 毫秒, spout: 0～1, inhale: 0～1}；opt.glow：頭目外光色（預設傳說金，false＝不畫）。
   * 腳底 (0,0)，寬約 76 單位（Q 版主角高 38～46 的 2 倍寬）。
   */
  function drawAshenHeart(ctx, st = {}, opt = {}) {
    const t = num(st.t, 0), breath = 0.5 + 0.5 * Math.sin(t / 420), phase = [1, 2, 3].includes(st.phase) ? st.phase : 1;
    const crack = phase === 3 ? 0.6 + 0.4 * Math.sin(t / 160) : 0, shell = clamp(num(st.shell, phase === 1 ? 1 : 0)), bt = clamp(num(st.breakT, shell > 0 ? 0 : 1));
    const inhale = clamp(num(st.inhale, 0)), spout = clamp(num(st.spout, 0)), cy = -28 - inhale * 2;
    ring(ctx, 40, { elite: true });
    ctx.fillStyle = "rgba(10,8,14,0.35)"; ctx.beginPath(); ctx.ellipse(0, 0, 40, 8, 0, 0, TAU); ctx.fill();
    if (phase === 3) flatGlow(ctx, 0, -6, 50, "#ff6e1e", 1);
    flatGlow(ctx, 0, cy, 32 * (1 + 0.06 * breath), "#ffaa3c", 0.6 + 0.4 * breath + 0.3 * crack);
    layer(ctx, [-90, -150, 90, 14], (g) => {
      // 底座：熔岩甲蟲堆（不會掉）
      g.save(); g.beginPath(); g.moveTo(-38, 0); g.quadraticCurveTo(-36, -12, -20, -16); g.quadraticCurveTo(0, -20, 20, -16); g.quadraticCurveTo(36, -12, 38, 0); g.closePath(); g.fillStyle = BASALT; g.fill(); g.restore();
      for (const x of [-24, -8, 10, 26]) { ell(g, x, -6, 7, 4.4, BASALT_L); line(g, [[x - 5, -3], [x - 8, 0]], 1, OUT); ell(g, x + 6.4, -6.4, 2, 1.8, BASALT); }
      core(g, 0, cy, breath, crack);
      if (spout > 0) { // 殼頂熔岩柱（平塗兩層）
        g.save(); g.fillStyle = LAVA; g.beginPath(); g.moveTo(-6, -46); g.quadraticCurveTo(-9, -60 - 30 * spout, 0, -70 - 36 * spout); g.quadraticCurveTo(9, -60 - 30 * spout, 6, -46); g.closePath(); g.fill();
        g.fillStyle = LAVA_HOT; g.beginPath(); g.ellipse(0, -58 - 20 * spout, 2.6, 10 * spout, 0, 0, TAU); g.fill(); g.restore();
      }
      for (const p of PLATES) { const A = plateAnchor(p, shell, bt, breath); g.save(); g.globalAlpha = A.a; g.translate(A.x, A.y); g.rotate(A.r); plate(g, p[4], p[5], shell > 0 ? breath : 0.15); g.restore(); }
    }, { glow: opt.glow === false ? null : (opt.glow ?? GOLD), glowW: 1.6, glowA: 0.5 });
    // 小粒子（吸氣的火星、熔毀滴落）：細外框
    const parts = [];
    if (inhale > 0) for (let k = 0; k < 12; k++) { const a = rnd("in", k) * TAU, d = 60 * (1 - ((t / 600 + rnd("in2", k)) % 1)); parts.push([Math.cos(a) * d, cy + Math.sin(a) * d * 0.6, 1.8, LAVA_HOT]); }
    if (phase === 3) for (let k = 0; k < 4; k++) { const ph = (t / 900 + rnd("drip", k)) % 1; parts.push([-20 + k * 13, -14 + ph * 14, 1.8, LAVA]); }
    if (parts.length) layer(ctx, [-90, -150, 90, 14], (g) => { for (const [x, y, r, c] of parts) { g.fillStyle = c; g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill(); } }, { ow: 0.8, alpha: inhale > 0 && phase !== 3 ? Math.max(0.3, inhale) : 1 });
  }

  // =========================== 碎晶之主 ===========================
  const CRYST = "#b8a8ff", CRYST_D = "#7a6ae0", RIFT = "#8a4ad0", CORE2 = "#e0ffff";
  /** 掛點（相對身體原點；浮空的上下位移另外加）。名稱和 bossArt.js 的部件名稱相同。Q 版：頭放大成 r≈11（大頭），軀幹縮短。 */
  const SL_ANCHORS = {
    head: [0, -62], torso: [0, -36], core2: [0, -40], "sh-l": [-17, -48], "sh-r": [17, -48], "hand-l": [-26, -36], "hand-r": [26, -36],
    ...Object.fromEntries([0, 1, 2, 3, 4].map((k) => [`crown-${k}`, [-10 + k * 5, -73 - (k === 2 ? 5 : k % 2 ? 2.4 : 0)]])),
    ...Object.fromEntries([0, 1, 2, 3, 4].map((k) => [`tail-${k}`, [0, -16 + k * 4.4]])),
  };
  function shard(g, x, y, len, wid, rot, color) {
    g.save(); g.translate(x, y); g.rotate(rot);
    const pts = [[0, -len], [wid, -len * 0.25], [wid * 0.6, len * 0.4], [0, len * 0.5], [-wid * 0.7, len * 0.3], [-wid, -len * 0.3]];
    poly(g, pts, color);
    poly(g, [[0, -len], [-wid, -len * 0.3], [-wid * 0.7, len * 0.3], [0, len * 0.5]], light(color, 0.3), { line: false });
    g.restore();
  }
  function slBody(g, st, hover, cast, tint, phase, t) {
    g.save(); g.translate(0, hover);
    const A = SL_ANCHORS, spread = phase === 4 ? 1.8 : 1;
    // 碎界脈動：後半圈的碎晶畫在身體後面
    const orbs = phase >= 2 ? [0, 1, 2, 3, 4, 5].map((k) => { const a = t / 800 + rnd("orb", k) * TAU, r = 30 + 4 * Math.sin(t / 300 + k); return { k, a, x: Math.cos(a) * r, y: -38 + Math.sin(a) * r * 0.35, front: Math.sin(a) >= 0 }; }) : [];
    for (const o of orbs) if (!o.front) shard(g, o.x, o.y, 5, 2.8, o.a, tint(o.k % 2 ? RIFT : CRYST));
    for (let k = 0; k < 5; k++) { const ph = t / 700 + rnd("tail", k) * TAU, [ax, ay] = A[`tail-${k}`]; shard(g, ax + Math.sin(ph) * 3 * spread + (rnd("tx", k) - 0.5) * 8 * spread, ay + k * 0.6 * (spread - 1) * 5, 7 - k, 4.4 - k * 0.6, Math.sin(ph) * 0.3, tint(k % 2 ? CRYST_D : CRYST)); }
    shard(g, ...A["sh-l"], 9, 4.4, -0.9, tint(CRYST_D)); shard(g, ...A["sh-r"], 9, 4.4, 0.9, tint(CRYST_D));
    // 軀幹：倒三角晶塊（亮面一塊）
    const torso = [[-14, -50], [14, -50], [9, -32], [3, -20], [-3, -20], [-9, -32]];
    poly(g, torso, tint(CRYST)); poly(g, [[-14, -50], [0, -50], [0, -36], [-3, -20], [-9, -32]], tint(light(CRYST, 0.22)), { line: false });
    line(g, [[-14, -50], [0, -38], [14, -50]], 0.7, tint(CRYST_D));
    // 胸口核心
    const over = phase >= 3 ? 0.7 + 0.3 * Math.sin(t / 130) : 0.4 + 0.2 * Math.sin(t / 400), [cx, cy] = A.core2;
    poly(g, [[cx, cy - 6.4], [cx + 5.6, cy], [cx, cy + 6.4], [cx - 5.6, cy]], mix(phase === 4 ? "#ffc0d8" : CORE2, "#ffffff", over * 0.5));
    g.fillStyle = "#ffffff"; g.fillRect(cx - 2, cy - 3, 1.6, 2.4);
    if (phase >= 3) line(g, [[cx - 2, cy - 5], [cx + 1, cy - 1], [cx - 1, cy + 4]], 1.2, "#ffffff");
    // 頭（Q 大頭）：六角晶面＋兩隻方眼
    const [hx, hy] = A.head, head = [[hx - 9, hy - 9], [hx + 9, hy - 9], [hx + 11.5, hy], [hx + 7, hy + 9], [hx - 7, hy + 9], [hx - 11.5, hy]];
    for (let k = 0; k < 5; k++) { const [x, y] = A[`crown-${k}`]; shard(g, x, y, 6 + (k === 2 ? 5 : 2), 2.6, (k - 2) * 0.24, tint(k === 2 ? CORE2 : CRYST)); }
    poly(g, head, tint(light(CRYST, 0.15))); poly(g, [[hx - 9, hy - 9], [hx, hy - 9], [hx - 4, hy + 9], [hx - 7, hy + 9], [hx - 11.5, hy]], tint(light(CRYST, 0.35)), { line: false });
    const eyeC = phase >= 3 ? "#ffffff" : CORE2;
    for (const x of [-4.2, 4.2]) { g.fillStyle = OUT; g.fillRect(hx + x - 1.6, hy - 2.4, 3.2, 4); g.fillStyle = eyeC; g.fillRect(hx + x - 1, hy - 1.8, 2, 2.8); }
    // 浮空手晶：施法時往前（東）伸
    const hxr = 26 + 16 * cast, hyr = -36 - 4 * Math.sin(t / 360);
    shard(g, -hxr + 30 * cast, hyr + 4, 9.5, 5.4, -0.4 + 1.6 * cast, tint(CRYST)); shard(g, hxr, hyr, 9.5, 5.4, 0.4 + 1.2 * cast, tint(CRYST));
    for (const o of orbs) if (o.front) shard(g, o.x, o.y, 5, 2.8, o.a, tint(o.k % 2 ? RIFT : CRYST));
    g.restore();
    return { hand: [hxr, hyr + hover] };
  }
  /** 碎晶之主（Q）。st：同 bossArt.js {phase: 1～4, t, cast: 0～1, blink: 0～1, channel}；opt.glow 同上。 */
  function drawShardLord(ctx, st = {}, opt = {}) {
    const t = num(st.t, 0), phase = [1, 2, 3, 4].includes(st.phase) ? st.phase : 1, hover = -10 - 3 * Math.sin(t / 500), cast = clamp(num(st.cast, 0)), blink = clamp(num(st.blink, 0));
    const tint = phase === 4 ? (c) => mix(c, "#ff5a8a", 0.35) : (c) => c, BOX = [-80, -112, 80, 14];
    ring(ctx, 26, { elite: true });
    ctx.fillStyle = "rgba(10,8,14,0.3)"; ctx.beginPath(); ctx.ellipse(0, 0, 24, 5, 0, 0, TAU); ctx.fill();
    flatGlow(ctx, 0, hover - 40, 24, phase === 4 ? "#ff5a8c" : "#a0f0ff", phase >= 3 ? 1 : 0.7);
    if (blink > 0) for (let g = 3; g >= 1; g--) { ctx.save(); ctx.translate(-g * 14, 0); layer(ctx, BOX, (o) => slBody(o, st, hover, cast, tint, phase, t), { alpha: 0.22 * blink, ow: 0 }); /* 殘影不描外框（半透明的黑框會變成髒影子） */ ctx.restore(); }
    let hand = null;
    layer(ctx, BOX, (g) => { hand = slBody(g, st, hover, cast, tint, phase, t).hand; }, { glow: opt.glow === false ? null : (opt.glow ?? GOLD), glowW: 1.6, glowA: 0.5 });
    if (cast > 0) { layer(ctx, BOX, (g) => { g.fillStyle = "#d8b8ff"; g.beginPath(); g.arc(hand[0] + 10, hand[1], 4.4 * cast, 0, TAU); g.fill(); g.fillStyle = "#ffffff"; g.beginPath(); g.arc(hand[0] + 10, hand[1], 2 * cast, 0, TAU); g.fill(); }, { ow: 0.9 }); flatGlow(ctx, hand[0] + 10, hand[1], 16, "#c8a0ff", cast); }
    // 灌注光束（三柱階段）：平塗色帶＋白芯
    if (phase === 1 && st.channel !== false) for (let k = 0; k < 3; k++) {
      const a = -Math.PI / 2 + (k - 1) * 0.9, c = ["#ff7a2a", "#9ad8c8", "#c8a0ff"][k], p0 = [Math.cos(a) * 90, hover - 40 + Math.sin(a) * 60], p1 = [0, hover - 40];
      ctx.save(); ctx.globalAlpha = 0.75 + 0.2 * Math.sin(t / 200 + k); line(ctx, [p0, p1], 4.4, OUT); line(ctx, [p0, p1], 3, c); line(ctx, [p0, p1], 0.9, "#ffffff"); ctx.restore();
    }
  }
  return { drawAshenHeart, drawShardLord, PLATES, SL_ANCHORS, plateAnchor };
})();
