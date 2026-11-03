// 動畫樣張（美術 PM，2026-11-04）：程式骨架動畫——紙娃娃拆成關節（頭、身、上下臂、上下腿、武器），每個動作是一個
// 「片段」：t（0→1）→ 關節角度＋位移＋特效。技能動畫＝依引擎事件順序把片段串起來播；LLM 不參與。只是示意，不代決。
// 使用者原話（專案 PM 轉達）：「動畫阿動畫 走路動畫 上樓動畫 放技能動畫 各種動畫阿」「砍+跳 跟跳+砍 就只差在撥放順序不同啊 不用給llm館阿」
window.Anim = (() => {
  const TAU = Math.PI * 2;
  const OUT = "#1c1712";
  const LOOK = { skin: "#f1c9a5", hair: "#3a2414", tunic: "#2f5a5a", tunicDark: "#244646", pants: "#4a3a2a", boot: "#5a3a20", belt: "#8a6440" };
  const FOE = { skin: "#a8724c", hair: "#1a1a1a", tunic: "#7a6a4a", tunicDark: "#5e5038", pants: "#3a3028", boot: "#3a2a1a", belt: "#5a4030", hat: "#a08a5a" };
  const ELEM = { fire: ["#ff7a2a", "#ffd23a"], ice: ["#7ad8ff", "#e8f8ff"], lightning: ["#c8a0ff", "#fff4a0"], physical: ["#e8eef4", "#ffffff"], holy: ["#ffe080", "#fffbe0"], crit: ["#ffb020", "#fff6c0"] };
  const ease = { in: (t) => t * t, out: (t) => 1 - (1 - t) * (1 - t), inOut: (t) => (t < 0.5 ? 2 * t * t : 1 - 2 * (1 - t) * (1 - t)) };
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const mix = (a, b, t) => a + (b - a) * t;

  // ---------------- 骨架紙娃娃 ----------------
  /** 姿勢：角度以「往下為 0、往前（臉朝的方向）為正」的弧度；knee／elbow 是相對上一節的彎曲。 */
  const REST = { bob: 0, lean: 0, hipF: 0, hipB: 0, kneeF: 0.1, kneeB: 0.1, shF: 0.15, shB: -0.1, elF: 0.35, elB: 0.3, wpn: 0, crouch: 0, flash: 0, tuck: 0 };
  function limb(ctx, a, b, w, color) {
    ctx.lineCap = "round"; ctx.strokeStyle = OUT; ctx.lineWidth = w + 3; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    ctx.strokeStyle = color; ctx.lineWidth = w; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
  }
  const at = (p, len, ang) => [p[0] + Math.sin(ang) * len, p[1] + Math.cos(ang) * len];
  function weapon(ctx, hand, ang, kind) {
    ctx.save(); ctx.translate(hand[0], hand[1]); ctx.rotate(-ang + Math.PI);
    if (kind === "sword") { limb(ctx, [0, -4], [0, 22], 2.4, "#dfe4ea"); limb(ctx, [-4, 0], [4, 0], 2, "#e8bb48"); limb(ctx, [0, 0], [0, -5], 2, "#6a4a2a"); }
    else if (kind === "staff") { limb(ctx, [0, -10], [0, 20], 2.4, "#8a6440"); ctx.fillStyle = "#c8bcff"; ctx.beginPath(); ctx.arc(0, 22, 3.6, 0, TAU); ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke(); }
    else if (kind === "bow") { ctx.strokeStyle = OUT; ctx.lineWidth = 4.5; ctx.beginPath(); ctx.arc(-6, 0, 13, -1.2, 1.2); ctx.stroke(); ctx.strokeStyle = "#8a6440"; ctx.lineWidth = 2.5; ctx.stroke(); }
    else if (kind === "axe") { limb(ctx, [0, -3], [0, 18], 2.4, "#8a6440"); ctx.fillStyle = "#9aa0a8"; ctx.beginPath(); ctx.moveTo(0, 13); ctx.lineTo(8, 10); ctx.lineTo(9, 20); ctx.lineTo(0, 18); ctx.closePath(); ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke(); }
    ctx.restore();
  }
  /** 側面（朝東；朝西由呼叫端鏡像）。 */
  function drawSide(ctx, P, L, wpn) {
    const hip = [0, -20 + P.bob + P.crouch * 4], len = 9 - P.tuck * 2;
    const sh = [hip[0] + Math.sin(P.lean) * 14, hip[1] - Math.cos(P.lean) * 14];
    // 後側的腿與手臂（暗一點）
    const kB = at(hip, len, P.hipB), fB = at(kB, len, P.hipB - P.kneeB);
    limb(ctx, hip, kB, 4.5, L.pants); limb(ctx, kB, fB, 4, L.boot);
    const eB = at(sh, 7, P.shB), hB = at(eB, 7, P.shB + P.elB);
    limb(ctx, sh, eB, 3.6, L.tunicDark); limb(ctx, eB, hB, 3.2, L.skin);
    if (wpn === "bow") weapon(ctx, hB, P.shB + P.elB + P.wpn, "bow");
    // 身體
    ctx.save(); ctx.translate(hip[0], hip[1]); ctx.rotate(P.lean);
    ctx.beginPath(); ctx.moveTo(-5, 1); ctx.lineTo(-5.5, -14); ctx.quadraticCurveTo(0, -17, 5.5, -14); ctx.lineTo(5, 1); ctx.closePath();
    ctx.fillStyle = L.tunic; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.fillStyle = L.belt; ctx.fillRect(-5, -3, 10, 2.5);
    ctx.restore();
    // 頭
    const head = [sh[0] + Math.sin(P.lean) * 7 + 1, sh[1] - Math.cos(P.lean) * 7];
    ctx.beginPath(); ctx.arc(head[0], head[1], 7, 0, TAU); ctx.fillStyle = L.skin; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.beginPath(); ctx.arc(head[0] - 1, head[1] - 1.5, 7.2, Math.PI * 0.95, Math.PI * 2.15); ctx.lineTo(head[0] - 6, head[1] + 2); ctx.closePath(); ctx.fillStyle = L.hair; ctx.fill(); ctx.stroke();
    if (L.hat) { ctx.beginPath(); ctx.ellipse(head[0], head[1] - 5, 11, 3, 0, 0, TAU); ctx.fillStyle = L.hat; ctx.fill(); ctx.stroke(); }
    ctx.fillStyle = OUT; ctx.beginPath(); ctx.arc(head[0] + 3.5, head[1] + 0.5, 1.1, 0, TAU); ctx.fill();
    // 前側的腿與手臂
    const kF = at(hip, len, P.hipF), fF = at(kF, len, P.hipF - P.kneeF);
    limb(ctx, hip, kF, 4.5, L.pants); limb(ctx, kF, fF, 4, L.boot);
    const eF = at(sh, 7, P.shF), hF = at(eF, 7, P.shF + P.elF);
    limb(ctx, sh, eF, 3.8, L.tunic); limb(ctx, eF, hF, 3.4, L.skin);
    if (wpn && wpn !== "bow") weapon(ctx, hF, P.shF + P.elF + P.wpn, wpn);
    return { hand: hF, back: hB, head };
  }
  /** 正面（south）與背面（north）：左右腳交替抬起、手臂前後擺（正面看是上下）。 */
  function drawFront(ctx, P, L, back, wpn, phase) {
    const lift = (s) => Math.max(0, s) * 3.5;
    const bob = P.bob;
    for (const [x, s] of [[-3.5, Math.sin(phase)], [3.5, -Math.sin(phase)]]) { limb(ctx, [x, -19 + bob], [x, -10 + bob - lift(s) * 0.5], 4.5, L.pants); limb(ctx, [x, -10 + bob - lift(s) * 0.5], [x, -1 - lift(s)], 4.2, L.boot); }
    const armY = (s) => s * 2.2;
    for (const [x, s] of [[-7.5, -Math.sin(phase)], [7.5, Math.sin(phase)]]) { limb(ctx, [x * 0.85, -32 + bob], [x, -26 + bob + armY(s) * 0.4], 3.6, L.tunic); limb(ctx, [x, -26 + bob + armY(s) * 0.4], [x * 1.05, -20 + bob + armY(s)], 3.2, L.skin); }
    ctx.beginPath(); ctx.moveTo(-6, -18 + bob); ctx.lineTo(-6.5, -33 + bob); ctx.quadraticCurveTo(0, -36 + bob, 6.5, -33 + bob); ctx.lineTo(6, -18 + bob); ctx.closePath();
    ctx.fillStyle = back ? L.tunicDark : L.tunic; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.fillStyle = L.belt; ctx.fillRect(-6, -21 + bob, 12, 2.5);
    const hy = -41 + bob;
    ctx.beginPath(); ctx.arc(0, hy, 7, 0, TAU); ctx.fillStyle = back ? L.hair : L.skin; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    if (!back) { ctx.beginPath(); ctx.arc(0, hy - 1.5, 7.2, Math.PI * 1.05, Math.PI * 1.95); ctx.closePath(); ctx.fillStyle = L.hair; ctx.fill(); ctx.stroke(); ctx.fillStyle = OUT; for (const x of [-2.5, 2.5]) { ctx.beginPath(); ctx.arc(x, hy + 1, 1.1, 0, TAU); ctx.fill(); } }
    if (wpn === "sword") { const hx = back ? -8 : 8; ctx.save(); ctx.translate(hx, -20 + bob + armY(back ? -Math.sin(phase) : Math.sin(phase))); limb(ctx, [0, 0], [0, 16], 2.4, "#dfe4ea"); limb(ctx, [-3.5, 0], [3.5, 0], 2, "#e8bb48"); ctx.restore(); }
  }
  /** 畫一個人：dir＝east／west／south／north；P＝姿勢；phase 給正背面走路用。 */
  function figure(ctx, x, y, dir, P, opt = {}) {
    const L = opt.look ?? LOOK, s = opt.scale ?? 1.6;
    ctx.save(); ctx.translate(x, y);
    ctx.fillStyle = "rgba(0,0,0,0.25)"; ctx.beginPath(); ctx.ellipse(0, 1, 12 * s * (1 - P.tuck * 0.3), 3.5 * s, 0, 0, TAU); ctx.fill();
    ctx.translate(0, -(opt.air ?? 0)); ctx.scale(dir === "west" ? -s : s, s);
    let out = null;
    if (dir === "east" || dir === "west") out = drawSide(ctx, P, L, opt.wpn);
    else drawFront(ctx, P, L, dir === "north", opt.wpn, opt.phase ?? 0);
    ctx.restore();
    if (P.flash > 0 && !opt.flashPass) { ctx.save(); ctx.globalAlpha = P.flash; ctx.filter = "brightness(0) invert(1)"; figure(ctx, x, y, dir, { ...P, flash: 0 }, { ...opt, flashPass: true }); ctx.restore(); }
    if (out) { const k = dir === "west" ? -s : s; const map = (p) => [x + p[0] * k, y - (opt.air ?? 0) + p[1] * s]; return { hand: map(out.hand), back: map(out.back), head: map(out.head) }; }
    return null;
  }

  // ---------------- 片段（clip）：t → 姿勢＋位移＋特效 ----------------
  /** 走路循環：phase 0→2π。kind：walk／run／sneak。 */
  function walkPose(phase, kind = "walk") {
    const amp = kind === "run" ? 0.8 : kind === "sneak" ? 0.35 : 0.5, s = Math.sin(phase);
    const P = { ...REST, hipF: amp * s, hipB: -amp * s, kneeF: 0.15 + 0.8 * Math.max(0, -Math.sin(phase + 0.9)) * (kind === "run" ? 1.3 : 1), kneeB: 0.15 + 0.8 * Math.max(0, Math.sin(phase + 0.9)) * (kind === "run" ? 1.3 : 1),
      shF: -amp * 0.9 * s, shB: amp * 0.9 * s, elF: kind === "run" ? 1.2 : 0.35, elB: kind === "run" ? 1.2 : 0.3, bob: -Math.abs(Math.cos(phase)) * (kind === "run" ? 2.5 : 1.4) };
    if (kind === "run") P.lean = 0.18;
    if (kind === "sneak") { P.crouch = 1; P.lean = 0.25; P.shF = 0.6 + 0.2 * s; P.shB = 0.2 - 0.2 * s; P.elF = 1; }
    return P;
  }
  /** 技能與反應的片段庫。每個片段：{dur 毫秒, pose(t), move?(t)→[dx,dy,air], fx?(ctx, t, actor, target, elem)}。 */
  const CLIP = {
    windup: { dur: 260, pose: (t) => ({ ...REST, shF: mix(0.15, -2.4, ease.out(t)), elF: mix(0.35, 0.5, t), lean: -0.12 * t, hipF: 0.25 * t, hipB: -0.2 * t, wpn: 0.3 * t }) },
    slash: {
      dur: 220, pose: (t) => ({ ...REST, shF: mix(-2.4, 1.3, ease.in(t)), elF: mix(0.5, 0.05, t), lean: mix(-0.12, 0.2, t), hipF: 0.45, hipB: -0.3, wpn: mix(0.3, -0.2, t) }),
      fx: (ctx, t, A, B, el, o) => arcTrail(ctx, A, mix(-2.4, 1.3, ease.in(t)), -2.4, el, 1 - Math.max(0, t - 0.8) * 5, 1, o.wk), hitAt: 0.65,
    },
    // ---- 揮砍的變體：同一個「揮砍」位置，播放時依事件雜湊挑一種（只影響畫面）----
    windup_lo: { dur: 240, pose: (t) => ({ ...REST, shF: mix(0.15, -0.9, ease.out(t)), elF: mix(0.35, 0.2, t), lean: 0.1 * t, crouch: 0.6 * t, hipF: 0.35 * t, hipB: -0.25 * t, wpn: -0.6 * t }) },
    slash_lo: {
      dur: 220, pose: (t) => ({ ...REST, shF: mix(-0.9, 2.7, ease.in(t)), elF: mix(0.2, 0.1, t), lean: mix(0.1, -0.15, t), crouch: mix(0.6, 0, t), hipF: 0.4, hipB: -0.3, wpn: mix(-0.6, 0.2, t) }),
      fx: (ctx, t, A, B, el, o) => arcTrail(ctx, A, mix(-0.9, 2.7, ease.in(t)), -0.9, el, 1 - Math.max(0, t - 0.8) * 5, 1, o.wk), hitAt: 0.6,
    },
    windup_side: { dur: 240, pose: (t) => ({ ...REST, shF: mix(0.15, -1.6, ease.out(t)), elF: mix(0.35, 0.05, t), lean: -0.05 * t, hipF: 0.3 * t, hipB: -0.2 * t, wpn: 1.2 * t }) },
    slash_side: {
      dur: 200, pose: (t) => ({ ...REST, shF: mix(-1.6, 1.7, ease.in(t)), elF: 0.05, lean: mix(-0.05, 0.18, t), hipF: 0.45, hipB: -0.3, wpn: mix(1.2, 1.5, t) }),
      fx: (ctx, t, A, B, el, o) => arcTrail(ctx, A, mix(-1.6, 1.7, ease.in(t)), -1.6, el, 1 - Math.max(0, t - 0.8) * 5, 0.38, o.wk), hitAt: 0.6,
    },
    thrust: { dur: 200, pose: (t) => ({ ...REST, shF: mix(0.4, 1.5, ease.in(t)), elF: mix(1.4, 0.05, ease.in(t)), lean: 0.2 * t, hipF: 0.5 * t, hipB: -0.35 * t }), move: (t) => [8 * ease.out(t), 0, 0], hitAt: 0.7 },
    draw: { dur: 380, pose: (t) => ({ ...REST, shB: 1.57, elB: 0, shF: mix(0.3, 1.45, ease.out(t)), elF: mix(0.4, 2.2, ease.out(t)), wpn: 0, lean: -0.05 }), bow: true },
    release: {
      dur: 300, pose: (t) => ({ ...REST, shB: 1.57, elB: 0, shF: mix(1.45, 1.2, t), elF: mix(2.2, 0.6, ease.out(t)), lean: -0.08 * (1 - t) }),
      fx: (ctx, t, A, B, el) => projectile(ctx, A.back, B.chest, t, el, "arrow"), hitAt: 0.95,
    },
    channel: {
      dur: 520, pose: (t) => ({ ...REST, shF: mix(0.15, 2.6, ease.out(clamp(t * 1.6))), elF: 0.2, shB: mix(-0.1, 2.2, ease.out(clamp(t * 1.6))), elB: 0.2, lean: -0.06, bob: -1.5 * Math.sin(t * Math.PI) }),
      fx: (ctx, t, A, B, el) => castCircle(ctx, A.foot, t, el),
    },
    cast: {
      dur: 420, pose: (t) => ({ ...REST, shF: mix(2.6, 1.5, ease.out(clamp(t * 3))), elF: 0.05, shB: mix(2.2, 0.6, clamp(t * 3)), elB: 0.3, lean: 0.12 }),
      fx: (ctx, t, A, B, el) => { castCircle(ctx, A.foot, 1 - t, el); projectile(ctx, A.hand, B.chest, t, el, "orb"); }, hitAt: 0.95,
    },
    dash: { dur: 260, pose: (t) => ({ ...REST, lean: 0.35, hipF: 0.8, hipB: -0.7, kneeB: 0.9, shF: -0.7, shB: 0.9 }), move: (t) => [ease.inOut(t), 0, 0], trail: true },
    leap: { dur: 420, pose: (t) => ({ ...REST, tuck: Math.sin(t * Math.PI), kneeF: 0.1 + 1.4 * Math.sin(t * Math.PI), kneeB: 0.1 + 1.6 * Math.sin(t * Math.PI), hipF: 0.9 * Math.sin(t * Math.PI), hipB: 0.5 * Math.sin(t * Math.PI), shF: -1.4 * Math.sin(t * Math.PI), shB: -1.2 * Math.sin(t * Math.PI) }), move: (t) => [ease.inOut(t), 0, 34 * Math.sin(t * Math.PI)] },
    hit: { dur: 360, pose: (t) => ({ ...REST, lean: -0.3 * Math.sin(Math.min(1, t * 2) * Math.PI), shF: 0.7 * Math.sin(t * Math.PI), shB: -0.8 * Math.sin(t * Math.PI), flash: Math.max(0, 1 - t * 4) * 0.85 }), move: (t) => [-7 * Math.sin(Math.min(1, t * 1.6) * Math.PI), 0, 0] },
    idle: { dur: 400, pose: (t) => ({ ...REST, bob: -0.6 * Math.sin(t * TAU) }) },
  };
  // ---------------- 特效 ----------------
  function arcTrail(ctx, A, a1, a0, el, alpha, squash = 1, wk = 1) {
    const [c1, c2] = ELEM[el]; const r = 30, cx = A.shoulder[0], cy = A.shoulder[1] + (squash < 1 ? 14 : 0), sgn = A.dirSign;
    ctx.save(); ctx.globalAlpha = clamp(alpha); ctx.lineCap = "round";
    if (wk > 1) { ctx.shadowColor = c2; ctx.shadowBlur = 16; }
    for (const [w, col] of [[10 * wk, c1], [4 * wk, c2]]) { ctx.strokeStyle = col; ctx.lineWidth = w; ctx.beginPath(); for (let k = 0; k <= 16; k++) { const a = mix(a0, a1, k / 16); const px = cx + Math.sin(a) * r * sgn, py = cy + Math.cos(a) * r * squash; k ? ctx.lineTo(px, py) : ctx.moveTo(px, py); } ctx.stroke(); }
    ctx.restore();
  }
  function projectile(ctx, from, to, t, el, kind) {
    if (t <= 0 || t >= 1) return;
    const [c1, c2] = ELEM[el]; const x = mix(from[0], to[0], t), y = mix(from[1], to[1], t) - Math.sin(t * Math.PI) * (kind === "orb" ? 10 : 4);
    ctx.save();
    if (kind === "arrow") { const a = Math.atan2(to[1] - from[1], to[0] - from[0]); ctx.translate(x, y); ctx.rotate(a); ctx.strokeStyle = OUT; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(-14, 0); ctx.lineTo(4, 0); ctx.stroke(); ctx.strokeStyle = "#c8a070"; ctx.lineWidth = 1.6; ctx.stroke(); ctx.fillStyle = "#dfe4ea"; ctx.beginPath(); ctx.moveTo(8, 0); ctx.lineTo(2, -3); ctx.lineTo(2, 3); ctx.fill(); }
    else { ctx.shadowColor = c1; ctx.shadowBlur = 14; ctx.fillStyle = c1; ctx.beginPath(); ctx.arc(x, y, 7, 0, TAU); ctx.fill(); ctx.fillStyle = c2; ctx.beginPath(); ctx.arc(x, y, 3.5, 0, TAU); ctx.fill(); for (let k = 1; k < 5; k++) { ctx.globalAlpha = 0.5 - k * 0.1; ctx.fillStyle = c1; ctx.beginPath(); ctx.arc(x - (to[0] - from[0]) * 0.04 * k, y + k, 6 - k, 0, TAU); ctx.fill(); } }
    ctx.restore();
  }
  function castCircle(ctx, foot, t, el) {
    if (t <= 0) return;
    const [c1] = ELEM[el]; ctx.save(); ctx.globalAlpha = clamp(t * 1.5); ctx.shadowColor = c1; ctx.shadowBlur = 10; ctx.strokeStyle = c1; ctx.lineWidth = 2;
    const r = 26 * ease.out(clamp(t * 1.4));
    ctx.beginPath(); ctx.ellipse(foot[0], foot[1], r, r * 0.35, 0, 0, TAU); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(foot[0], foot[1], r * 0.65, r * 0.23, 0, 0, TAU); ctx.stroke();
    for (let k = 0; k < 6; k++) { const a = k / 6 * TAU + t * 3; ctx.fillStyle = c1; ctx.beginPath(); ctx.arc(foot[0] + Math.cos(a) * r * 0.8, foot[1] + Math.sin(a) * r * 0.28 - t * 18 * ((k % 3) + 1) / 3, 1.8, 0, TAU); ctx.fill(); }
    ctx.restore();
  }
  function burst(ctx, p, t, el) {
    if (t <= 0 || t >= 1) return;
    const [c1, c2] = ELEM[el]; ctx.save(); ctx.globalAlpha = 1 - t; ctx.shadowColor = c1; ctx.shadowBlur = 12;
    for (let k = 0; k < 8; k++) { const a = k / 8 * TAU; ctx.strokeStyle = k % 2 ? c1 : c2; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(p[0] + Math.cos(a) * 6 * t, p[1] + Math.sin(a) * 6 * t); ctx.lineTo(p[0] + Math.cos(a) * (8 + 18 * t), p[1] + Math.sin(a) * (8 + 18 * t)); ctx.stroke(); }
    ctx.restore();
  }
  function damageNumber(ctx, p, t, n, crit = false) {
    if (t <= 0 || t >= 1) return;
    const size = (crit ? 24 : 16) + (crit ? 14 : 6) * Math.max(0, 1 - t * 4), label = crit ? `暴擊 −${n}` : `−${n}`;
    ctx.save(); ctx.globalAlpha = t > 0.7 ? (1 - t) / 0.3 : 1; ctx.font = `bold ${size}px 'Microsoft JhengHei', sans-serif`; ctx.textAlign = "center";
    ctx.lineWidth = crit ? 5 : 4; ctx.strokeStyle = OUT; ctx.strokeText(label, p[0], p[1] - 22 * ease.out(t)); ctx.fillStyle = crit ? "#ffd23a" : "#ff5a48"; ctx.fillText(label, p[0], p[1] - 22 * ease.out(t));
    ctx.restore();
  }

  // ---------------- 串接器：片段依序播放；命中時目標同時播「受擊」 ----------------
  /**
   * seq：[{clip, to?}]——to 給位移片段的終點 x（由引擎事件的落點決定，不是片段自己決定）。
   * 回傳在時間 ms 時要畫的狀態。這就是「同樣的片段、不同順序」：順序與方向全部來自技能結構與事件。
   */
  function sequence(seq, startX, target, el, wpn, opt = {}) {
    const parts = []; let t0 = 0, x = startX;
    for (const s of seq) { const c = CLIP[s.clip]; parts.push({ ...s, c, t0, x0: x, x1: s.to ?? x }); t0 += c.dur; if (s.to !== undefined) x = s.to; }
    const animTotal = t0;
    let hitAt = -1;
    for (const p of parts) if (p.c.hitAt !== undefined) hitAt = p.t0 + p.c.dur * p.c.hitAt;
    // 暴擊的時間扭曲：命中前 SLOW_IN 毫秒放慢到 SLOW_K 倍，命中瞬間停 STOP 毫秒
    const crit = !!opt.crit, SLOW_IN = 140, SLOW_K = 0.3, STOP = 110;
    const slowReal = SLOW_IN / SLOW_K;
    const warp = (r) => {
      if (!crit || hitAt < 0) return r;
      const a0 = hitAt - SLOW_IN;
      if (r < a0) return r;
      if (r < a0 + slowReal) return a0 + (r - a0) * SLOW_K;
      if (r < a0 + slowReal + STOP) return hitAt;
      return r - (slowReal - SLOW_IN) - STOP;
    };
    const total = crit && hitAt >= 0 ? animTotal + (slowReal - SLOW_IN) + STOP : animTotal;
    const hitReal = crit && hitAt >= 0 ? hitAt - SLOW_IN + slowReal : hitAt;
    return {
      total,
      draw(ctx, realMs, groundY, dir = "east") {
        const ms = warp(Math.min(realMs, total));
        ctx.save();
        if (crit && realMs >= hitReal && realMs < hitReal + 260) { const k2 = 1 - (realMs - hitReal) / 260; ctx.translate(Math.sin(realMs * 0.9) * 4 * k2, Math.cos(realMs * 1.3) * 3 * k2); }
        const r = this._draw(ctx, ms, groundY, dir);
        ctx.restore();
        if (crit && realMs >= hitReal && realMs < hitReal + 70) { ctx.save(); ctx.fillStyle = "rgba(255,250,230,0.35)"; ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height); ctx.restore(); }
        return r;
      },
      _draw(ctx, ms, groundY, dir) {
        const k = Math.min(ms, animTotal);
        let cur = parts[parts.length - 1], local = 1;
        for (const p of parts) if (k >= p.t0 && k < p.t0 + p.c.dur) { cur = p; local = (k - p.t0) / p.c.dur; break; }
        const P = cur.c.pose(local);
        const m = cur.c.move ? cur.c.move(local) : [0, 0, 0];
        const ax = cur.to !== undefined ? mix(cur.x0, cur.x1, m[0]) : cur.x0 + m[0];
        const faceSign = dir === "west" ? -1 : 1;
        // 殘影（衝刺）
        if (cur.c.trail) for (let g = 1; g <= 3; g++) { ctx.save(); ctx.globalAlpha = 0.18; figure(ctx, mix(cur.x0, cur.x1, Math.max(0, m[0] - g * 0.12)), groundY, dir, P, { wpn }); ctx.restore(); }
        // 目標：命中後播受擊
        const hitMs = hitAt;
        const tl = hitMs >= 0 && ms >= hitMs ? (ms - hitMs) / CLIP.hit.dur : -1;
        const TP = tl >= 0 && tl < 1 ? CLIP.hit.pose(tl) : CLIP.idle.pose((ms / 1600) % 1);
        const tdx = tl >= 0 && tl < 1 ? CLIP.hit.move(tl)[0] * -faceSign * -1 : 0;
        figure(ctx, target + tdx * faceSign, groundY, dir === "east" ? "west" : "east", TP, { look: FOE, wpn: "axe" });
        const B = { chest: [target, groundY - 46] };
        const out = figure(ctx, ax, groundY, dir, P, { wpn: cur.c.bow ? "bow" : wpn, air: m[2] });
        const A = { hand: out?.hand ?? [ax, groundY - 40], back: out?.back ?? [ax, groundY - 40], foot: [ax, groundY], shoulder: [ax + 1.6 * Math.sin(P.lean) * 14 * faceSign, groundY - 1.6 * (20 + 14)], dirSign: faceSign };
        if (cur.c.fx) cur.c.fx(ctx, local, A, B, crit ? "crit" : el, { wk: crit ? 1.7 : 1 });
        if (tl >= 0) { burst(ctx, B.chest, tl * (crit ? 0.9 : 1.4), crit ? "crit" : el); if (crit) burst(ctx, B.chest, tl * 0.6, "crit"); damageNumber(ctx, [target, groundY - 70], tl * 0.6, crit ? 24 : 12, crit); }
        return { clip: cur.clip, parts };
      },
    };
  }

  // ---------------- 樓梯：每階 12px，腳步抬高 ----------------
  function stairs(ctx, x0, gy, ms) {
    const steps = 4, sw = 34, sh = 12, period = 3600;
    for (let k = 0; k < steps; k++) { const x = x0 + 70 + k * sw; ctx.fillStyle = k % 2 ? "#8a948c" : "#9aa39c"; ctx.fillRect(x, gy - (k + 1) * sh, sw * (steps - k) + 40, sh); ctx.strokeStyle = OUT; ctx.lineWidth = 1.5; ctx.strokeRect(x, gy - (k + 1) * sh, sw * (steps - k) + 40, sh); ctx.fillStyle = "rgba(0,0,0,0.25)"; ctx.fillRect(x, gy - (k + 1) * sh + sh - 3, sw * (steps - k) + 40, 3); }
    const t = (ms % period) / period, x = x0 + 20 + t * (70 + steps * sw + 20);
    const stepIdx = clamp((x - (x0 + 70) + 12) / sw, 0, steps);
    const base = Math.floor(stepIdx), frac = stepIdx - base;
    const rise = (base + ease.inOut(clamp((frac - 0.55) / 0.45))) * sh;
    const phase = t * 12 * Math.PI;
    const P = walkPose(phase); if (x > x0 + 60 && x < x0 + 70 + steps * sw) { P.kneeF += 0.5 * Math.max(0, Math.sin(phase)); P.hipF += 0.3 * Math.max(0, Math.sin(phase)); P.lean = 0.08; }
    figure(ctx, x, gy - Math.min(steps * sh, rise), "east", P, { wpn: "sword" });
  }

  /** 同 client/src/render/inkStyle.ts 的 seedOf（FNV-1a）。 */
  function seedOf(str) { let h = 2166136261; for (const ch of str) h = Math.imul(h ^ (ch.codePointAt(0) ?? 0), 16777619); return h >>> 0; }
  /** 揮砍的變體表：[蓄力片段, 揮砍片段, 中文]。 */
  const SLASH_VARIANTS = [["windup", "slash", "由上往下"], ["windup_lo", "slash_lo", "由下往上"], ["windup_side", "slash_side", "橫掃"]];
  /** 挑變體：鍵＝戰鬥 ID、事件序號、施放者 ID（全部來自引擎事件），重播與觀戰看到的一樣。 */
  function pickVariant(battleId, eventSeq, unitId, n) { return seedOf(`${battleId}:${eventSeq}:${unitId}:anim`) % n; }
  return { CLIP, ELEM, REST, figure, walkPose, sequence, stairs, ease, LOOK, FOE, seedOf, pickVariant, SLASH_VARIANTS };
})();
