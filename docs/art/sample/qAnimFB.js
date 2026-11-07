// qAnimFB.js：Q 版正面（朝南）、背面（朝北）的走路與出招樣板（畫圖 agent，2026-11-07）。
// 使用者原話（11-07）：「左右揮砍走路我不怕做不好 給我一些對上下走路和攻擊的動畫樣板」
// 做法：身體、頭、腿、外框照 qDoll.js；出招時用 qDoll 的 POSE.fb 由這裡畫兩隻手臂與武器，分三層：
//   under＝身體之前（會被身體、頭擋住：正面時在身後的東西、背面時在身前的東西）；over＝身體之後、頭之前；top＝頭之後（最靠鏡頭）。
// 四面分別畫：背面的每一幀另外寫，不是正面鏡像。手臂照第 17 版：彎肘兩段描邊、打直一圈（qDoll 的 arm()）；往鏡頭或往遠處伸的手臂打直時照距離縮短，不拉長。
// 每類 7 個關鍵幀：0 預備、1 起手、2 蓄力頂點、3 出招中、4 命中、5 收招、6 回位；播放每幀 140ms。
window.QAnimFB = (() => {
  const Q = QDoll, A = Anim, TAU = Math.PI * 2, FRAME_MS = 140;
  const STEEL = PaperDoll.itemColors({ material: "steel" })[0], SHAFT = "#6a4420", COLLAR = "#8a6a2a";
  const staffUnit = (() => { const u = A.unit("staff"); return { look: u.look, gear: { ...u.gear, main_hand: { kind: "staff", element: "fire" } } }; })();
  const UNITS = { walk: A.unit("sword"), sword: A.unit("sword"), spear: A.unit("spear"), bow: A.unit("bow"), staff: staffUnit, gauntlet: A.unit("gauntlet") };
  const FOE = A.FOE;

  // ---------------- 關鍵幀的寫法 ----------------
  // m／o：主手（右手）、副手（左手）手臂。{h:[x,y] 手的目標, st:1 打直（往鏡頭或往遠處時照距離縮短）, out:±1|"down" 手肘方向, f 手臂長度比例}
  // ops：依序畫的東西，各自指定圖層 L。
  const arm = (who, L, x = {}) => ({ t: "arm", who, L, ...x });          // big：拳頭放大（往鏡頭）；clip:"out" 只畫身體輪廓外面（背面伸到身前的手臂）
  const wpn = (L, a, x = {}) => ({ t: "w", L, a, on: "m", ...x });         // a＝武器的世界角度（作用端方向＝(sin a, −cos a)）；s＝長度比例（縮短）、wd＝寬度比例；wrap＝四指橫過握把
  const wrapOp = (L, a, on = "m") => ({ t: "wrap", L, a, on });
  const fnOp = (L, f) => ({ t: "fn", L, f });
  const Mof = (a, s = 1, wd = 1) => (s === 1 && wd === 1 ? null : [Math.cos(a) * wd, Math.sin(a) * wd, -Math.sin(a) * s, Math.cos(a) * s]);
  const norm = ([x, y]) => { const l = Math.hypot(x, y) || 1; return [x / l, y / l]; };
  const TORSO = [-7.5, -21, 15, 13.5];

  function solve(api, sx, s) {
    if (!s) return null;
    if (s.st) {
      const dx = s.h[0] - sx, dy = s.h[1] + 20, d = Math.hypot(dx, dy), f = Math.min(1, d / (api.UA + api.FA)), len = [api.UA * f, api.FA * f], sA = Math.atan2(-dx, dy);
      return { sx, sA, eA: 0, len, hand: api.fk(sx, sA, 0, len) };
    }
    const len = s.f ? [api.UA * s.f, api.FA * s.f] : null, r = api.ik(sx, s.h, s.out ?? Math.sign(sx), len);
    return { sx, sA: r.sA, eA: r.eA, len, hand: api.fk(sx, r.sA, r.eA, len) };
  }
  function drawArm(api, R, op) {
    api.arm(R.sx, R.sA, R.eA, null, R.len);
    if (op.big) { /* 往鏡頭的拳頭：在手的位置放大重畫一次（只畫拳頭那一圈） */
      const [x, y] = R.hand, c = api.ctx;
      c.save(); c.beginPath(); c.arc(x, y, 3.2 * op.big, 0, TAU); c.clip(); c.translate(x, y); c.scale(op.big, op.big); c.translate(-x, -y); api.arm(R.sx, R.sA, R.eA, null, R.len); c.restore();
    }
  }
  /** 縮短的長柄（槍、杖往鏡頭或往遠處）：R＝握點，d＝作用端方向（畫面），Lf＝握點到槍頭（杖頭）根部，Lb＝握點到尾端；w0／w1＝尾端、前端的桿寬（近大遠小）。 */
  function pole(c, R, d, Lf, Lb, w0, w1) {
    const n = [-d[1], d[0]], B = [R[0] - d[0] * Lb, R[1] - d[1] * Lb], T = [R[0] + d[0] * Lf, R[1] + d[1] * Lf];
    c.beginPath(); c.moveTo(B[0] + n[0] * w0 / 2, B[1] + n[1] * w0 / 2); c.lineTo(T[0] + n[0] * w1 / 2, T[1] + n[1] * w1 / 2); c.lineTo(T[0] - n[0] * w1 / 2, T[1] - n[1] * w1 / 2); c.lineTo(B[0] - n[0] * w0 / 2, B[1] - n[1] * w0 / 2); c.closePath(); c.fillStyle = SHAFT; c.fill();
    return T;
  }
  function spearHead(c, T, d, hl, hw) {
    const n = [-d[1], d[0]], P = [T[0] + d[0] * hl, T[1] + d[1] * hl];
    c.fillStyle = STEEL; c.beginPath(); c.moveTo(P[0], P[1]); c.lineTo(T[0] + n[0] * hw / 2, T[1] + n[1] * hw / 2); c.lineTo(T[0] - n[0] * hw / 2, T[1] - n[1] * hw / 2); c.closePath(); c.fill();
    c.fillStyle = "rgba(255,255,255,0.45)"; c.beginPath(); c.moveTo(P[0], P[1]); c.lineTo(T[0] + n[0] * hw * 0.12, T[1] + n[1] * hw * 0.12); c.lineTo(T[0] + n[0] * hw * 0.3, T[1] + n[1] * hw * 0.3); c.closePath(); c.fill();
    c.fillStyle = COLLAR; const cw = hw * 0.62; c.beginPath(); c.moveTo(T[0] + n[0] * cw / 2, T[1] + n[1] * cw / 2); c.lineTo(T[0] - n[0] * cw / 2, T[1] - n[1] * cw / 2); c.lineTo(T[0] - n[0] * cw / 2 - d[0] * 1.3, T[1] - n[1] * cw / 2 - d[1] * 1.3); c.lineTo(T[0] + n[0] * cw / 2 - d[0] * 1.3, T[1] + n[1] * cw / 2 - d[1] * 1.3); c.closePath(); c.fill();
    return P;
  }
  /** 長槍：rear＝後手（主手）握點；fwd＝前手的方向點（決定槍的方向）。 */
  let TIP = null; /* 這一幀槍尖、杖頭的位置（角色座標），特效從這裡出發 */
  const spearOp = (L, { Lf, Lb, hl, hw, w0 = 1.5, w1 = 1.9, d: d0 = null }) => fnOp(L, (api, H, c) => { const R = H.m.hand, d = d0 ? norm(d0) : norm([H.o.hand[0] - R[0], H.o.hand[1] - R[1]]); const T = pole(c, R, d, Lf, Lb, w0, w1); TIP = spearHead(c, T, d, hl, hw); });
  /** 杖頭（照 qDoll 的 staff：火屬性橙色、光暈 6.5＋2g）；sc＝近大遠小。 */
  function staffHead(c, P, sc, g) {
    const orb = "#ff6a1a";
    c.save(); c.globalAlpha = 0.35 + 0.35 * g; c.fillStyle = orb; c.beginPath(); c.arc(P[0], P[1], 5.2 * sc, 0, TAU); c.fill(); c.restore(); /* 光暈只畫一圈薄的（會被描外框）；放大的光改由頁面的特效 glow 畫（不描框） */
    c.fillStyle = orb; c.beginPath(); c.arc(P[0], P[1], 3.6 * sc, 0, TAU); c.fill();
    c.fillStyle = "rgba(255,255,255,0.8)"; c.beginPath(); c.arc(P[0] - 1.2 * sc, P[1] - 1.2 * sc, 1.1 * sc, 0, TAU); c.fill();
  }
  const staffFS = (L, d, Lf, Lb, sc, w0, w1) => fnOp(L, (api, H, c) => { const R = H.m.hand, T = pole(c, R, norm(d), Lf, Lb, w0, w1); staffHead(c, T, sc, 1); TIP = T; });
  /** 弓：G＝持弓手（副手）、N＝拉弦手（主手）；F＝弓背方向（箭的方向，畫面向量），U＝弓臂方向。 */
  const bowOp = (L, { U, pull, nock = true, F = null }) => fnOp(L, (api, H) => {
    const G = H.o.hand, N = H.m.hand, k = api.BOW_EY + pull, FF = F ?? [(G[0] - N[0]) / k, (G[1] - N[1]) / k];
    api.bow(G, U, FF, pull, nock);
  });

  // ---------------- 正面（朝南）：主手肩在畫面左 x −8.5 ----------------
  const IDLE_F = { m: { h: [-11.85, -10.06], st: 1 }, o: { h: [11.85, -10.06], st: 1 } };
  const IDLE_B = { m: { h: [11.85, -10.06], st: 1 }, o: { h: [-11.85, -10.06], st: 1 } };
  const C = {};
  // fx：t＝trail（揮砍弧，點用角色座標）、spark、flash、ring、proj、dmg、circle、glow、lines
  C.sword = {
    zh: "劍・揮砍",
    front: [
      { ...IDLE_F, ops: [arm("o", "over"), arm("m", "over"), wpn("over", -0.12, { wrap: 1 })] },
      { m: { h: [-13, -21.5], out: -1 }, o: { h: [12, -13], st: 1 }, bob: -0.4, ops: [arm("o", "over"), arm("m", "over"), wpn("over", -0.05, { wrap: 1 })] },
      { m: { h: [-12, -29.5], out: -1 }, o: { h: [11.5, -15], st: 1 }, bob: -0.6, ops: [wpn("under", 0.8), arm("o", "over"), arm("m", "over"), wrapOp("over", 0.8)] },
      { m: { h: [-11, -25], out: -1 }, o: { h: [12, -14], st: 1 }, bob: -0.3, ops: [arm("o", "over"), arm("m", "over"), wpn("top", -0.25, { s: 0.55, wd: 1.1, wrap: 1 })],
        fx: [{ t: "trail", pts: [[1.6, -42.7], [-14, -44], [-13.6, -35.1]], a: 0.55 }] },
      { m: { h: [-3, -14], st: 1 }, o: { h: [12.5, -14], st: 1 }, ops: [arm("o", "over"), arm("m", "top"), wpn("top", Math.PI - 0.4, { s: 0.75, wd: 1.15, wrap: 1 })],
        fx: [{ t: "trail", pts: [[1.6, -42.7], [-30, -30], [2.5, -0.9]], a: 1 }, { t: "spark", s: 1 }, { t: "dmg", u: 0.1 }], hit: 1 },
      { m: { h: [-1.5, -13], out: "down" }, o: { h: [12, -12], st: 1 }, ops: [arm("o", "over"), arm("m", "top"), wpn("top", 2.25, { s: 0.95, wd: 1.05, wrap: 1 })],
        fx: [{ t: "trail", pts: [[-14, -36], [-20, -6], [12.6, -1.6]], a: 0.45 }, { t: "spark", s: 0.6, a: 0.5 }, { t: "dmg", u: 0.5 }], hit: 0.5 },
      { m: { h: [-11, -12], st: 1 }, o: IDLE_F.o, ops: [arm("o", "over"), arm("m", "over"), wpn("over", -0.5, { wrap: 1 })], fx: [{ t: "dmg", u: 0.9 }] },
    ],
    back: [
      { ...IDLE_B, ops: [wpn("under", 0.12), arm("o", "over"), arm("m", "over"), wpn("over", 0.12, { clip: "hand" })] },
      { m: { h: [13, -21.5], out: 1 }, o: { h: [-12, -13], st: 1 }, bob: -0.4, ops: [arm("o", "over"), arm("m", "over"), wpn("over", 0.05)] },
      { m: { h: [12, -29.5], out: 1 }, o: { h: [-11.5, -15], st: 1 }, bob: -0.6, ops: [arm("o", "over"), arm("m", "over"), wpn("top", -0.8)] },
      { m: { h: [10.5, -28], out: 1 }, o: { h: [-12, -14], st: 1 }, bob: -0.3, ops: [arm("o", "over"), wpn("over", 0.1, { s: 0.6 }), arm("m", "over"), wpn("over", 0.1, { s: 0.6, clip: "hand" })],
        fx: [{ t: "lines", s: 0.6 }] },
      { m: { h: [3, -15], out: 1 }, o: { h: [-12.5, -16], st: 1 }, ops: [wpn("under", -2.2, { s: 0.8 }), arm("m", "over", { clip: "out" }), arm("o", "over")],
        fx: [{ t: "trail", far: 1, a: 1 }, { t: "spark", s: 0.75 }, { t: "dmg", u: 0.1 }], hit: 1 },
      { m: { h: [0.5, -14.5], out: 1 }, o: { h: [-12, -15], st: 1 }, ops: [wpn("under", -2.55, { s: 0.85 }), arm("m", "over", { clip: "out" }), arm("o", "over")],
        fx: [{ t: "trail", far: 1, a: 0.4 }, { t: "spark", s: 0.45, a: 0.5 }, { t: "dmg", u: 0.5 }], hit: 0.5 },
      { m: { h: [11, -12], st: 1 }, o: IDLE_B.o, ops: [wpn("under", 0.4), arm("o", "over"), arm("m", "over"), wpn("over", 0.4, { clip: "hand" })], fx: [{ t: "dmg", u: 0.9 }] },
    ],
  };
  // 長槍：主手＝後手、副手＝前手。正面：兩手在胸前中線上下握，槍身朝畫面下方（往鏡頭）縮短，槍頭變大；背面：後手在右腰外，槍頭與前手在身體前方被擋住，槍尾在右腰後方露出
  const spA = (H) => Math.atan2(H.o.hand[0] - H.m.hand[0], -(H.o.hand[1] - H.m.hand[1])); /* 槍的世界角度（後手 → 前手），四指橫過槍桿 */
  const SPF = (L, Lf, hl, hw) => [arm("o", "over"), arm("m", "over"), spearOp("over", { Lf, Lb: 4, hl, hw, w0: 1.5, w1: 2.1 + hw * 0.06 }), wrapOp("over", spA, "m"), wrapOp("over", spA, "o")];
  /* 背面：前手在身體前方看不到；d＝槍的方向（出招時槍往遠處伸、槍尖從頭頂上方露出一點） */
  const SPB = (Lf, Lb, d = null) => [arm("o", "under"), spearOp("under", { Lf, Lb, hl: 3, hw: 3.4, w0: 2.4, w1: 1.3, d }), arm("m", "over"), fnOp("over", (api, H, c) => { c.save(); c.beginPath(); c.arc(H.m.hand[0], H.m.hand[1], 2.6, 0, TAU); c.clip(); const R = H.m.hand, dd = d ? norm(d) : norm([H.o.hand[0] - R[0], H.o.hand[1] - R[1]]); pole(c, R, dd, Lf, Lb, 2.4, 1.3); c.restore(); })];
  C.spear = {
    zh: "長槍・刺",
    front: [
      { m: { h: [-1, -17.5], out: -1 }, o: { h: [1.5, -13.3], out: 1 }, ops: SPF("over", 14, 5, 6.5) },
      { m: { h: [-2.5, -19.5], out: -1 }, o: { h: [0.5, -15.5], out: 1 }, bob: -0.3, ops: SPF("over", 11, 4.5, 6) },
      { m: { h: [-3, -20], out: -1 }, o: { h: [0, -16.3], out: 1 }, bob: -0.5, ops: SPF("over", 10, 4.3, 5.8) },
      { m: { h: [-0.5, -16], st: 1 }, o: { h: [1.5, -12], st: 1 }, liftR: 1.5, ops: SPF("over", 18, 6.2, 8.4), fx: [{ t: "lines", s: 0.8 }] },
      { m: { h: [0, -15], st: 1 }, o: { h: [2, -11.5], st: 1 }, liftR: 1, ops: SPF("over", 20, 7, 9.6), fx: [{ t: "flash", s: 1, tip: "auto" }, { t: "dmg", u: 0.1 }], hit: 1 },
      { m: { h: [-0.3, -15.5], st: 1 }, o: { h: [1.8, -11.8], st: 1 }, ops: SPF("over", 18.5, 6.6, 9), fx: [{ t: "flash", s: 0.6, a: 0.5, tip: "auto" }, { t: "dmg", u: 0.5 }], hit: 0.5 },
      { m: { h: [-1, -17.5], out: -1 }, o: { h: [1.5, -13.3], out: 1 }, ops: SPF("over", 14, 5, 6.5), fx: [{ t: "dmg", u: 0.9 }] },
    ],
    back: [
      { m: { h: [9.3, -12.5], out: 1 }, o: { h: [2, -16.5], out: -1 }, ops: SPB(11, 9) },
      { m: { h: [10.2, -10.5], out: 1 }, o: { h: [0.5, -16.5], out: -1 }, bob: -0.3, ops: SPB(11, 10) },
      { m: { h: [10.4, -10], out: 1 }, o: { h: [0.2, -16.2], out: -1 }, bob: -0.5, ops: SPB(11, 10.5) },
      { m: { h: [8.6, -15], out: 1 }, o: { h: [0, -19], out: -1 }, liftL: 1.5, ops: SPB(22, 8, [-0.33, -0.94]), fx: [{ t: "lines", s: 0.6 }] },
      { m: { h: [8, -16], out: 1 }, o: { h: [-0.5, -19.5], out: -1 }, liftL: 1, ops: SPB(25, 7.5, [-0.34, -0.94]), fx: [{ t: "flash", s: 0.75, tip: "auto" }, { t: "dmg", u: 0.1 }], hit: 1 },
      { m: { h: [8.3, -15.5], out: 1 }, o: { h: [0, -19.2], out: -1 }, ops: SPB(24, 7.8, [-0.34, -0.94]), fx: [{ t: "flash", s: 0.45, a: 0.5, tip: "auto" }, { t: "dmg", u: 0.5 }], hit: 0.5 },
      { m: { h: [9.3, -12.5], out: 1 }, o: { h: [2, -16.5], out: -1 }, ops: SPB(11, 9), fx: [{ t: "dmg", u: 0.9 }] },
    ],
  };
  // 弓：副手（左手）握弓、主手（右手）拉弦。正面：持弓手往前（鏡頭）打直縮短、弓往外傾，拉弦手靠右臉頰、手肘抬到肩高；背面：弓在 under 層被頭和身體擋住大半
  const BF = (U, pull, nock = true, F = null) => [arm("o", "top"), bowOp("top", { U, pull, nock, F }), arm("m", "top")];
  const F_FULL = [(4.5 - -5.5) / (5.42 + 9), (-14.5 - -24) / (5.42 + 9)];
  /* 背面：箭在頭的正前方（遠處），整支被頭擋住，不畫（只畫弓和弦；放箭後箭從頭頂上方飛出） */
  const BB = (U, pull, nock = true, F = null, clipM = false) => [bowOp("under", { U, pull, nock, F }), arm("o", "over"), arm("m", "over", clipM ? { clip: "out" } : {})];
  const F_FULL_B = [(-7.3 - 6) / (5.42 + 9), (-29.5 - -24.5) / (5.42 + 9)];
  C.bow = {
    zh: "弓・拉放",
    front: [
      { m: { h: [0, -15], out: -1 }, o: { h: [5, -11.5], st: 1 }, ops: BF([-0.3, 0.95], 2) },
      { m: { h: [-1, -19], out: -1 }, o: { h: [5.5, -16.5], st: 1 }, bob: -0.2, ops: BF([-0.4, 0.92], 3) },
      { m: { h: [-3.5, -22], out: -1 }, o: { h: [5, -15.5], st: 1 }, bob: -0.3, ops: BF([-0.45, 0.89], 6) },
      { m: { h: [-5.5, -24], out: -1 }, o: { h: [4.5, -14.5], st: 1 }, bob: -0.3, ops: BF([-0.5, 0.87], 9) },
      { m: { h: [-8, -25.5], out: -1 }, o: { h: [4.5, -14.5], st: 1 }, bob: -0.2, ops: BF([-0.5, 0.87], 0, false, F_FULL), fx: [{ t: "proj", kind: "arrow", u: 0.55, from: [5, -12] }] },
      { m: { h: [-7, -21], out: -1 }, o: { h: [4.5, -14], st: 1 }, ops: BF([-0.5, 0.87], 0, false, F_FULL), fx: [{ t: "stuck", kind: "arrow" }, { t: "spark", s: 0.7 }, { t: "dmg", u: 0.15 }], hit: 1 },
      { ...IDLE_F, o: { h: [5, -12], st: 1 }, ops: [arm("o", "top"), bowOp("top", { U: [-0.3, 0.95], pull: 0, nock: false, F: [0.62, 0.42] }), arm("m", "over")], fx: [{ t: "stuck", kind: "arrow" }, { t: "dmg", u: 0.6 }], hit: 0.3 },
    ],
    back: [
      { m: { h: [1, -14], out: 1 }, o: { h: [-4, -12], st: 1 }, ops: [fnOp("under", (api, H, c) => { c.save(); c.beginPath(); c.rect(...TORSO); c.clip(); bowOp("under", { U: [0.3, 0.95], pull: 1.5 }).f(api, H, c); c.restore(); }), arm("o", "over", { clip: "out" }), arm("m", "over", { clip: "out" })] },
      { m: { h: [3, -21.5], out: 1 }, o: { h: [-5.5, -24], st: 1 }, bob: -0.2, ops: BB([0.5, 0.87], 3, false, null, true) },
      { m: { h: [5, -23.5], out: 1 }, o: { h: [-6.8, -28], st: 1 }, bob: -0.3, ops: BB([0.6, 0.8], 6, false) },
      { m: { h: [6, -24.5], out: 1 }, o: { h: [-7.3, -29.5], st: 1 }, bob: -0.3, ops: BB([0.7, 0.71], 9, false) },
      { m: { h: [11, -24.5], out: 1 }, o: { h: [-7.3, -29.5], st: 1 }, bob: -0.2, ops: BB([0.7, 0.71], 0, false, F_FULL_B), fx: [{ t: "proj", kind: "arrow", u: 0.5, from: [-4, -36] }] },
      { m: { h: [10, -21], out: 1 }, o: { h: [-7, -28.5], st: 1 }, ops: BB([0.7, 0.71], 0, false, F_FULL_B), fx: [{ t: "stuck", kind: "arrow" }, { t: "spark", s: 0.5 }, { t: "dmg", u: 0.15 }], hit: 1 },
      { m: { h: [1, -14], out: 1 }, o: { h: [-4, -12], st: 1 }, ops: [fnOp("under", (api, H, c) => { c.save(); c.beginPath(); c.rect(...TORSO); c.clip(); bowOp("under", { U: [0.3, 0.95], pull: 0, nock: false, F: [-0.5, -0.4] }).f(api, H, c); c.restore(); }), arm("o", "over", { clip: "out" }), arm("m", "over", { clip: "out" })], fx: [{ t: "stuck", kind: "arrow" }, { t: "dmg", u: 0.6 }], hit: 0.3 },
    ],
  };
  // 法杖（火）：舉杖（杖頭光放大）→ 施放（正面杖往鏡頭壓、杖頭變大；背面杖往遠處傾、杖頭變小從頭的右上露出）
  const STF = (a, mg = 0, L = "over") => [arm("o", "over"), arm("m", "over"), wpn(L, a, { mg, wrap: 1 })];
  const STB = (a, mg = 0) => [wpn("under", a, { mg }), arm("o", "over"), arm("m", "over")];
  C.staff = {
    zh: "法杖・施法",
    front: [
      { ...IDLE_F, ops: STF(0, -1.9) },
      { m: { h: [-12.5, -21], out: -1 }, o: { h: [11.5, -15], st: 1 }, glow: 0.4, bob: -0.3, ops: STF(0.05), fx: [{ t: "circle", u: 0.4 }] },
      { m: { h: [-11.5, -27], out: -1 }, o: { h: [11, -17], st: 1 }, glow: 1, bob: -0.5, ops: STF(0.12), fx: [{ t: "circle", u: 0.9 }, { t: "glow", at: [-7.7, -58.8], r: 16 }] },
      { m: { h: [-7, -17], st: 1 }, o: { h: [11.5, -15], st: 1 }, glow: 1, ops: [arm("o", "over"), arm("m", "over"), staffFS("top", [0.35, 0.94], 12, 4, 1.45, 2.4, 3), wrapOp("top", Math.PI - 0.36)], fx: [{ t: "circle", u: 1, a: 0.6 }, { t: "glow", at: [-2.8, -5.7], r: 22 }] },
      { m: { h: [-7, -17.5], st: 1 }, o: { h: [11.5, -15], st: 1 }, glow: 0.6, ops: [arm("o", "over"), arm("m", "over"), staffFS("top", [0.33, 0.94], 11, 4, 1.35, 2.4, 2.9), wrapOp("top", Math.PI - 0.34)], fx: [{ t: "proj", kind: "fire", u: 0.5, from: "auto" }] },
      { m: { h: [-10.5, -15], st: 1 }, o: { h: [11.8, -12], st: 1 }, glow: 0.3, ops: STF(0, -1), fx: [{ t: "ring", s: 1 }, { t: "spark", s: 0.9, el: "fire" }, { t: "dmg", u: 0.15 }], hit: 1 },
      { ...IDLE_F, ops: STF(0, -1.9), fx: [{ t: "ring", s: 0.6, a: 0.4 }, { t: "dmg", u: 0.6 }], hit: 0.3 },
    ],
    back: [
      { ...IDLE_B, ops: STB(0, -1.9) },
      { m: { h: [12.5, -21], out: 1 }, o: { h: [-11.5, -15], st: 1 }, glow: 0.4, bob: -0.3, ops: STB(-0.05), fx: [{ t: "circle", u: 0.4 }] },
      { m: { h: [11.5, -27], out: 1 }, o: { h: [-11, -17], st: 1 }, glow: 1, bob: -0.5, ops: STB(-0.12), fx: [{ t: "circle", u: 0.9 }, { t: "glow", at: [7.7, -58.8], r: 14 }] },
      { m: { h: [9.5, -25], out: 1 }, o: { h: [-11.5, -15], st: 1 }, glow: 1, ops: [staffFS("under", [-0.3, -0.95], 15, 3, 0.8, 2.2, 1.6), arm("o", "over"), arm("m", "over")], fx: [{ t: "circle", u: 1, a: 0.6 }, { t: "glow", at: [5, -39.3], r: 11 }] },
      { m: { h: [9.5, -25.5], out: 1 }, o: { h: [-11.5, -15], st: 1 }, glow: 0.6, ops: [staffFS("under", [-0.28, -0.96], 14, 3, 0.8, 2.2, 1.6), arm("o", "over"), arm("m", "over")], fx: [{ t: "proj", kind: "fire", u: 0.5, from: "auto" }] },
      { m: { h: [11, -15], st: 1 }, o: { h: [-11.8, -12], st: 1 }, glow: 0.3, ops: STB(0, -1), fx: [{ t: "ring", s: 0.75 }, { t: "spark", s: 0.6, el: "fire" }, { t: "dmg", u: 0.15 }], hit: 1 },
      { ...IDLE_B, ops: STB(0, -1.9), fx: [{ t: "ring", s: 0.45, a: 0.4 }, { t: "dmg", u: 0.6 }], hit: 0.3 },
    ],
  };
  // 拳（拳套）：正面直拳往鏡頭，手臂打直照距離縮短、拳頭放大；背面拳頭往遠處，出拳時手臂往上伸、拳頭被頭擋住一半
  const GD_F = { m: { h: [-4, -16.5], out: "down" }, o: { h: [4.5, -16], out: "down" } };
  const GD_B = { m: { h: [2.5, -15], out: 1 }, o: { h: [-3, -14.5], out: -1 } };
  C.gauntlet = {
    zh: "拳・拳套",
    front: [
      { ...GD_F, ops: [arm("o", "over"), arm("m", "over")] },
      { m: { h: [-9.5, -12.5], out: "down" }, o: GD_F.o, bob: -0.2, ops: [arm("m", "over"), arm("o", "over")] },
      { m: { h: [-7, -15], out: "down" }, o: GD_F.o, bob: -0.3, ops: [arm("m", "over"), arm("o", "over")] },
      { m: { h: [-3.5, -16], st: 1 }, o: { h: [5, -16.5], out: "down" }, ops: [arm("o", "over"), arm("m", "top", { big: 1.4 })], fx: [{ t: "lines", s: 0.7 }] },
      { m: { h: [-1.5, -13.5], st: 1 }, o: { h: [5, -16.5], out: "down" }, liftR: 1, ops: [arm("o", "over"), arm("m", "top", { big: 2.0 })], fx: [{ t: "ring", s: 1, el: "physical" }, { t: "spark", s: 0.8 }, { t: "dmg", u: 0.1 }], hit: 1 },
      { m: { h: [-2, -14], st: 1 }, o: { h: [5, -16.5], out: "down" }, ops: [arm("o", "over"), arm("m", "top", { big: 1.75 })], fx: [{ t: "ring", s: 0.6, a: 0.4, el: "physical" }, { t: "dmg", u: 0.5 }], hit: 0.5 },
      { ...GD_F, ops: [arm("o", "over"), arm("m", "over")], fx: [{ t: "dmg", u: 0.9 }] },
    ],
    back: [
      { ...GD_B, ops: [arm("o", "over", { clip: "out" }), arm("m", "over", { clip: "out" })] },
      { m: { h: [9.8, -12], out: 1 }, o: GD_B.o, bob: -0.2, ops: [arm("o", "over", { clip: "out" }), arm("m", "over", { big: 1.1 })] },
      { m: { h: [9, -17], out: 1 }, o: GD_B.o, bob: -0.3, ops: [arm("o", "over", { clip: "out" }), arm("m", "over")] },
      { m: { h: [9.3, -27], st: 1 }, o: { h: [-3, -14.5], out: -1 }, ops: [arm("o", "over", { clip: "out" }), arm("m", "over")], fx: [{ t: "lines", s: 0.6 }] },
      { m: { h: [8.9, -29], st: 1 }, o: { h: [-3, -14.5], out: -1 }, liftL: 1, ops: [arm("o", "over", { clip: "out" }), arm("m", "over")], fx: [{ t: "ring", s: 0.7, el: "physical" }, { t: "spark", s: 0.55 }, { t: "dmg", u: 0.1 }], hit: 1 },
      { m: { h: [9, -28.5], st: 1 }, o: { h: [-3, -14.5], out: -1 }, ops: [arm("o", "over", { clip: "out" }), arm("m", "over")], fx: [{ t: "ring", s: 0.45, a: 0.4, el: "physical" }, { t: "dmg", u: 0.5 }], hit: 0.5 },
      { ...GD_B, ops: [arm("o", "over", { clip: "out" }), arm("m", "over", { clip: "out" })], fx: [{ t: "dmg", u: 0.9 }] },
    ],
  };
  const ORDER = ["sword", "spear", "bow", "staff", "gauntlet"];

  // 每類每方向一行說明（難在哪／怎麼解）
  const NOTE = {
    walk: { front: ["正面看不出腿的前後；側面那套擺髖在正面會變成左右劈腿。", "正面不擺髖膝，只交替抬腳＋身體起伏，兩手前後擺用上下位移表現；持劍照待機握法。"],
      back: ["背面看不到臉，節奏只剩腳和手；劍要在背面那一側。", "同一套抬腳與起伏；背面另外畫（劍在畫面右、背面握法），不是正面鏡像。"] },
    sword: { front: ["往鏡頭下劈，劍身會縮短；還要交代劍從頭後面出來。", "蓄力時劍放 under 層（頭擋住劍根、只露頭上的劍身）；出招中劍和手改到 top 層並縮短；命中時劍朝前下在身前，揮砍弧從頭左外側繞到身前。"],
      back: ["落下時劍在身體前方，整把看不到，容易像沒出招。", "蓄力時劍在頭上方（top 層蓋在後腦）；命中時手和劍改到 under 層被身體擋住，只露劍尖從左腰外穿出；揮砍弧和火花畫在對面格（遠處上方）。"] },
    spear: { front: ["往鏡頭刺，槍身幾乎重疊成一點；Q 版手短，兩手只搆得到胸前中線。", "兩手在中線上下握，槍身往畫面下方縮短、槍頭放大到 1.5 倍；刺出時手臂打直但照距離變短（不拉長）；刺擊閃光在槍尖（靠鏡頭）。"],
      back: ["往遠方刺，槍頭和前手都在身體前面。", "後手握在右腰外、手肘往後彎（兩段描邊）；槍頭和前手在 under 層被身體擋住；槍尾從右腰後方伸出（靠鏡頭、畫粗）；刺出時槍尾往前收。"] },
    bow: { front: ["箭朝鏡頭，弓和弦會擋臉。", "持弓手往前打直（縮短）、弓往外傾（上弓梢在臉的右外緣），拉弦手靠右臉頰、手肘抬到肩高；放箭後箭往鏡頭飛、越飛越大。"],
      back: ["弓、箭、兩手都在身體前面。", "弓在 under 層被頭和身體擋住大半，只有上弓梢從頭左上露出；持弓手臂往上伸、拳頭藏在頭後；拉弦的右手肘往外抬（兩段描邊）、手被頭擋住；箭往遠處飛、越飛越小。"] },
    staff: { front: ["杖頭朝鏡頭時杖身縮短，光要放大。", "先舉杖（杖頭光脈動到最大、腳下法陣），施放時杖往鏡頭壓：杖身縮短、杖頭放大 1.45 倍、光暈加大；火球往前下飛、越飛越大。"],
      back: ["杖指向遠方，杖頭會被頭擋住。", "舉杖在畫面右；施放時杖往遠處傾（under 層）、杖身縮短、杖頭變小從頭的右上露出，握杖的拳頭被頭擋住一點；火球往上飛、越飛越小。"] },
    gauntlet: { front: ["直拳朝鏡頭，手臂不能拉長。", "手臂打直但照距離縮短；拳套拳頭放大 1.4→2 倍表現靠近鏡頭；護架時兩拳在胸前、不擋下巴。"],
      back: ["拳頭往遠處打，會被身體和頭擋住。", "護架時兩拳在身前（只畫身體輪廓外的上臂和手肘）；蓄力時拳頭收到右腰外（看得到）；出拳時手臂往上伸、拳頭到頭的右側被頭擋住一半；衝擊圈畫在對面格。"] },
  };

  // ---------------- 一格 ----------------
  const CW = 150, CH = 262, HK = 2.0, TK = 1.7;
  const ELEM = { physical: ["#e8eef4", "#ffffff"], fire: ["#ff7a2a", "#ffd23a"] };
  /** 走路：正面、背面不擺髖膝，只抬腳、起伏、兩手上下位移（側面那套擺髖在正面會變成左右劈腿） */
  function walkPose(k) { const P = A.walkPose((k / 7) * TAU); return { bob: P.bob, liftL: P.liftL, liftR: P.liftR, armL: P.armL, armR: P.armR }; }
  function geom(view) { return view === "front" ? { hx: 75, hy: 150, tx: 75, ty: 250 } : { hx: 75, hy: 250, tx: 75, ty: 108 }; }

  function tiles(c, G, front) {
    c.fillStyle = "#6a9a6a"; c.fillRect(0, 0, CW, CH);
    for (const [y, foe] of [[G.hy, false], [G.ty, true]]) {
      const T = 100, x0 = 75 - T / 2, y0 = y - T * 0.62;
      c.fillStyle = foe ? "rgba(120,40,40,0.16)" : "rgba(255,255,255,0.07)"; c.fillRect(x0, y0, T, T);
      c.strokeStyle = foe ? "rgba(150,40,40,0.55)" : "rgba(0,0,0,0.22)"; c.lineWidth = 1; c.strokeRect(x0 + 0.5, y0 + 0.5, T - 1, T - 1);
    }
  }
  let OFF = null;
  /** 對面格的敵人剪影（正面時看到敵人的背面、背面時看到敵人的正面） */
  function target(c, G, view, flash) {
    if (!OFF) { OFF = document.createElement("canvas"); OFF.width = CW; OFF.height = CH; }
    const o = OFF.getContext("2d"); o.setTransform(1, 0, 0, 1, 0, 0); o.clearRect(0, 0, CW, CH);
    Q.setPose(null); Q.stamp(o, FOE, view === "front" ? "back" : "front", G.tx, G.ty, TK, false);
    o.globalCompositeOperation = "source-atop"; o.fillStyle = "rgba(58,34,44,0.82)"; o.fillRect(0, 0, CW, CH); if (flash) { o.fillStyle = `rgba(255,236,220,${(0.42 * flash).toFixed(3)})`; o.fillRect(0, 0, CW, CH); } o.globalCompositeOperation = "source-over";
    c.beginPath(); c.ellipse(G.tx, G.ty, 30, 6, 0, 0, TAU); c.fillStyle = "rgba(0,0,0,0.22)"; c.fill();
    c.drawImage(OFF, 0, 0);
  }
  function hero(c, G, view, unit, P) {
    c.beginPath(); c.ellipse(G.hx, G.hy, 34, 7, 0, 0, TAU); c.fillStyle = "rgba(0,0,0,0.25)"; c.fill();
    Q.setPose(P); Q.stamp(c, unit, view, G.hx, G.hy, HK, false); Q.setPose(null);
  }
  const U2P = (G, [x, y], bob = 0) => [G.hx + x * HK, G.hy + (y + bob) * HK];

  // ---------------- 特效 ----------------
  function hitPt(G, view) { return view === "front" ? [G.tx - 2, G.ty - 60] : [G.tx, G.ty - 30]; }
  function dmgPt(G) { return [G.tx + 20, G.ty - 38 * TK - 4]; }
  function trail(c, pts, a, w = 1) {
    const [p0, p1, p2] = pts, N = 24;
    c.save(); c.lineCap = "round";
    for (const [col, k] of [["rgba(200,225,255,", 1], ["rgba(255,255,255,", 0.45]]) {
      for (let i = 0; i < N; i++) {
        const q = (t) => { const u = 1 - t; return [u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]]; };
        const t0 = i / N, t1 = (i + 1) / N, A0 = q(t0), A1 = q(t1), wd = (1.5 + 9 * Math.sin(Math.PI * Math.min(1, t1 * 1.15))) * k * w;
        c.strokeStyle = col + (a * (0.25 + 0.75 * t1)).toFixed(3) + ")"; c.lineWidth = wd; c.beginPath(); c.moveTo(A0[0], A0[1]); c.lineTo(A1[0], A1[1]); c.stroke();
      }
    }
    c.restore();
  }
  function star(c, p, s, a = 1, el = "physical") {
    const [c1, c2] = ELEM[el]; c.save(); c.globalAlpha = a; c.shadowColor = c1; c.shadowBlur = 10;
    c.fillStyle = c1; c.beginPath(); for (let k = 0; k < 16; k++) { const ang = -Math.PI / 2 + (k * Math.PI) / 8, r = (k % 2 ? 4 : k % 4 ? 13 : 20) * s; c.lineTo(p[0] + Math.cos(ang) * r, p[1] + Math.sin(ang) * r); } c.closePath(); c.fill();
    c.fillStyle = c2; c.beginPath(); c.arc(p[0], p[1], 5 * s, 0, TAU); c.fill(); c.restore();
  }
  function ring(c, p, s, a = 1, el = "fire") {
    const [c1, c2] = ELEM[el]; c.save(); c.globalAlpha = a; c.shadowColor = c1; c.shadowBlur = 12;
    c.strokeStyle = c1; c.lineWidth = 5 * s; c.beginPath(); c.ellipse(p[0], p[1], 24 * s, 15 * s, 0, 0, TAU); c.stroke();
    c.strokeStyle = c2; c.lineWidth = 2.2 * s; c.beginPath(); c.ellipse(p[0], p[1], 14 * s, 8.5 * s, 0, 0, TAU); c.stroke();
    for (let k = 0; k < 8; k++) { const ang = (k / 8) * TAU + 0.2; c.strokeStyle = k % 2 ? c1 : c2; c.lineWidth = 2.4 * s; c.beginPath(); c.moveTo(p[0] + Math.cos(ang) * 27 * s, p[1] + Math.sin(ang) * 17 * s); c.lineTo(p[0] + Math.cos(ang) * 36 * s, p[1] + Math.sin(ang) * 23 * s); c.stroke(); }
    c.restore();
  }
  /** 速度線：正面往下（鏡頭）、背面往上（遠處） */
  function lines(c, G, view, s) {
    c.save(); c.strokeStyle = "rgba(255,255,255,0.7)"; c.lineCap = "round";
    const dir = view === "front" ? 1 : -1, y0 = view === "front" ? G.hy + 4 : G.hy - 86;
    for (let k = -2; k <= 2; k++) { c.lineWidth = 1.6 * s + (k ? 0 : 0.8); const x = G.hx + k * 9 + (view === "front" ? -2 : 4), L = (22 - Math.abs(k) * 4) * s; c.beginPath(); c.moveTo(x, y0 + dir * Math.abs(k) * 3); c.lineTo(x, y0 + dir * (Math.abs(k) * 3 + L)); c.stroke(); }
    c.restore();
  }
  function circle(c, G, u, a = 1) {
    c.save(); c.globalAlpha = a * Math.min(1, u * 1.4); c.shadowColor = "#ff7a2a"; c.shadowBlur = 10; c.strokeStyle = "#ff8a3a"; c.lineWidth = 2;
    const r = 30 * (0.5 + 0.5 * u); c.beginPath(); c.ellipse(G.hx, G.hy, r, r * 0.33, 0, 0, TAU); c.stroke(); c.beginPath(); c.ellipse(G.hx, G.hy, r * 0.65, r * 0.21, 0, 0, TAU); c.stroke(); c.restore();
  }
  function glow(c, p, r) { const g = c.createRadialGradient(p[0], p[1], 0, p[0], p[1], r); g.addColorStop(0, "rgba(255,240,160,0.95)"); g.addColorStop(0.35, "rgba(255,140,40,0.6)"); g.addColorStop(1, "rgba(255,90,20,0)"); c.save(); c.fillStyle = g; c.beginPath(); c.arc(p[0], p[1], r, 0, TAU); c.fill(); c.restore(); }
  /** 飛行物：正面越近越大、背面越遠越小 */
  function proj(c, from, to, u, kind, view) {
    const x = from[0] + (to[0] - from[0]) * u, y = from[1] + (to[1] - from[1]) * u, sc = view === "front" ? 1 + 0.7 * u : 1 - 0.45 * u, ang = Math.atan2(to[1] - from[1], to[0] - from[0]);
    c.save(); c.translate(x, y);
    if (kind === "arrow") {
      c.rotate(ang); c.scale(sc, sc);
      const L = view === "front" ? 7 : 12; /* 正面：箭幾乎正對鏡頭，箭桿很短、箭頭大 */
      c.strokeStyle = "#16121a"; c.lineWidth = 3.4; c.beginPath(); c.moveTo(-L, 0); c.lineTo(2, 0); c.stroke();
      c.strokeStyle = "#c8a070"; c.lineWidth = 1.7; c.stroke();
      c.fillStyle = "#e8e0d0"; c.beginPath(); c.moveTo(-L, 0); c.lineTo(-L - 4, -3); c.lineTo(-L - 2, 0); c.lineTo(-L - 4, 3); c.closePath(); c.fill();
      c.fillStyle = "#16121a"; c.beginPath(); c.moveTo(9, 0); c.lineTo(1, -4.4); c.lineTo(1, 4.4); c.closePath(); c.fill();
      c.fillStyle = STEEL; c.beginPath(); c.moveTo(7.6, 0); c.lineTo(2, -3); c.lineTo(2, 3); c.closePath(); c.fill();
    } else {
      c.scale(sc, sc); const [c1, c2] = ELEM.fire; c.shadowColor = c1; c.shadowBlur = 14;
      for (let k = 4; k >= 1; k--) { c.globalAlpha = 0.18 * (5 - k); c.fillStyle = c1; c.beginPath(); c.arc(-Math.cos(ang) * 5 * k, -Math.sin(ang) * 5 * k, 7 - k, 0, TAU); c.fill(); }
      c.globalAlpha = 1; c.fillStyle = c1; c.beginPath(); c.arc(0, 0, 7.5, 0, TAU); c.fill(); c.fillStyle = c2; c.beginPath(); c.arc(0, 0, 3.8, 0, TAU); c.fill();
    }
    c.restore();
  }
  function stuck(c, G, view) { /* 箭插在目標上：正面箭尾朝畫面上方（從角色那邊射來）、背面箭尾朝下 */
    const p = hitPt(G, view), up = view === "front" ? -1 : 1;
    c.save(); c.translate(p[0] + 4, p[1] + 2); c.rotate(up < 0 ? -0.25 : 0.2);
    c.strokeStyle = "#16121a"; c.lineWidth = 3; c.beginPath(); c.moveTo(0, 0); c.lineTo(0, up * 12); c.stroke(); c.strokeStyle = "#c8a070"; c.lineWidth = 1.5; c.stroke();
    c.fillStyle = "#e8e0d0"; c.beginPath(); c.moveTo(0, up * 12); c.lineTo(-3, up * 16); c.lineTo(0, up * 14); c.lineTo(3, up * 16); c.closePath(); c.fill(); c.restore();
  }
  function dmg(c, G, u, n = 12) {
    const [x, y] = dmgPt(G), yy = y - 16 * Math.min(1, u * 1.4), size = 15 + 7 * Math.max(0, 1 - u * 4);
    c.save(); c.globalAlpha = u > 0.75 ? Math.max(0, (1 - u) / 0.25) * 0.9 + 0.1 : 1; c.font = `bold ${size.toFixed(1)}px "PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif`; c.textAlign = "center";
    c.lineWidth = 4; c.strokeStyle = "#1c1712"; c.strokeText(`−${n}`, x, yy); c.fillStyle = "#ff5a48"; c.fillText(`−${n}`, x, yy); c.restore();
  }
  function drawFx(c, G, view, fr) {
    for (const f of fr.fx ?? []) {
      const a = f.a ?? 1;
      if (f.t === "trail") {
        if (f.far) { const p = hitPt(G, view); trail(c, [[p[0] + 24, p[1] - 30], [p[0] + 18, p[1] + 6], [p[0] - 22, p[1] + 22]], a, 0.7); }
        else trail(c, f.pts.map((q) => U2P(G, q)), a, 1.15);
      } else if (f.t === "spark") star(c, hitPt(G, view), f.s * (view === "front" ? 1.15 : 0.8), a, f.el ?? "physical");
      else if (f.t === "flash") { const tp = f.tip === "auto" ? TIP : f.tip, p = tp ? U2P(G, tp) : hitPt(G, view); star(c, p, f.s * (view === "front" ? 1.2 : 0.75), a); if (tp) star(c, hitPt(G, view), f.s * 0.55, a * 0.8); }
      else if (f.t === "ring") ring(c, hitPt(G, view), f.s * (view === "front" ? 1 : 0.7), a, f.el ?? "fire");
      else if (f.t === "lines") lines(c, G, view, f.s);
      else if (f.t === "circle") circle(c, G, f.u, a);
      else if (f.t === "glow") glow(c, U2P(G, f.at), f.r);
      else if (f.t === "proj") proj(c, U2P(G, f.from === "auto" ? TIP : f.from), hitPt(G, view), f.u, f.kind, view);
      else if (f.t === "stuck") stuck(c, G, view);
      else if (f.t === "dmg") dmg(c, G, f.u);
    }
  }

  function hookOf(fr) {
    return (layer, api) => {
      const c = api.ctx, ms = api.view === "front" ? -8.5 : 8.5, H = { m: solve(api, ms, fr.m), o: solve(api, -ms, fr.o) };
      for (const op of fr.ops) {
        if (op.L !== layer) continue;
        c.save();
        if (op.clip === "out") { c.beginPath(); c.rect(-80, -120, 160, 200); c.rect(...TORSO); c.clip("evenodd"); }
        if (op.clip === "hand") { const h = H[op.on].hand; c.beginPath(); c.arc(h[0], h[1], 2.6, 0, TAU); c.clip(); }
        if (op.t === "arm") drawArm(api, H[op.who], op);
        else if (op.t === "w") { const h = H[op.on].hand; api.weapon(h, op.a, Mof(op.a, op.s, op.wd), op.mg ?? 0); if (op.wrap) api.wrap(h, op.a); }
        else if (op.t === "wrap") api.wrap(H[op.on].hand, typeof op.a === "function" ? op.a(H) : op.a);
        else op.f(api, H, c);
        c.restore();
      }
    };
  }
  /** 畫一格：kind＝walk 或五類之一；view＝front／back；k＝0～6 */
  function cell(c, kind, view, k) {
    const G = geom(view), front = view === "front";
    c.save(); c.beginPath(); c.rect(0, 0, CW, CH); c.clip();
    tiles(c, G, front);
    if (kind === "walk") {
      const P = walkPose(k);
      if (!front) target(c, G, view, 0);
      hero(c, G, view, UNITS.walk, P);
      if (front) target(c, G, view, 0);
      c.restore(); return;
    }
    const fr = C[kind][view][k], flash = fr.hit ?? 0; TIP = null;
    if (!front) target(c, G, view, flash);
    for (const f of fr.fx ?? []) if (f.t === "circle") circle(c, G, f.u, f.a ?? 1);
    hero(c, G, view, UNITS[kind], { bob: fr.bob ?? 0, liftL: fr.liftL ?? 0, liftR: fr.liftR ?? 0, glow: fr.glow ?? 0, fb: hookOf(fr) });
    if (front) target(c, G, view, flash);
    drawFx(c, G, view, { fx: (fr.fx ?? []).filter((f) => f.t !== "circle") });
    c.restore();
  }
  const ROWS = [["walk", "front"], ["walk", "back"], ...ORDER.flatMap((k) => [[k, "front"], [k, "back"]])];
  const ZH = { walk: "走路", ...Object.fromEntries(ORDER.map((k) => [k, C[k].zh])) }, VZ = { front: "正面（朝南）", back: "背面（朝北）" };
  /** 自查：每一幀主手有握到武器（作用端在畫布內）、手臂長度沒有超過原本（不拉長） */
  return { cell, ROWS, ZH, VZ, NOTE, C, CW, CH, FRAME_MS, ORDER };
})();
