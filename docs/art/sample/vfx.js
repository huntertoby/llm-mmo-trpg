// 技能特效細部樣張（美術 PM，2026-11-04）：雲嶺、荒原常見的 6 種元素——火、冰、雷、水、霧、毒。
// 每種元素一條時間軸：飛行物（0～0.4）→ 命中爆發（0.4～0.6）→ 地表擴散（0.6～1，十字 5 格，一格一格長出來）。
// 變體照 動畫方案.md 2.11：飛行軌跡（微弧／直線／螺旋）、爆發形狀（放射／圓環／星形）、粒子分布；顏色與範圍不變。
// 確定性：粒子位置由「元素＋粒子序號」雜湊決定，不用 Math.random()。全部程式繪製。
window.Vfx = (() => {
  const TAU = Math.PI * 2;
  function seedOf(s) { let h = 2166136261; for (const ch of s) h = Math.imul(h ^ (ch.codePointAt(0) ?? 0), 16777619); return h >>> 0; }
  const rnd = (k, i) => (seedOf(`${k}:${i}`) % 10000) / 10000;
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const mix = (a, b, t) => a + (b - a) * t;
  const ease = (t) => 1 - (1 - t) * (1 - t);
  function glow(ctx, x, y, r, c, a) { if (a <= 0 || r <= 0) return; const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, c); g.addColorStop(1, c.replace(/[\d.]+\)$/, "0)")); ctx.save(); ctx.globalAlpha = clamp(a); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); ctx.restore(); }
  const EL = {
    fire: { zh: "火", c1: "#ff7a2a", c2: "#ffd23a", g: "rgba(255,140,50,0.9)", surf: "rgba(120,40,10,0.85)" },
    ice: { zh: "冰", c1: "#7ad8ff", c2: "#f2fbff", g: "rgba(150,220,255,0.9)", surf: "rgba(205,238,255,0.92)" },
    lightning: { zh: "雷", c1: "#c8a0ff", c2: "#fff4a0", g: "rgba(200,170,255,0.9)", surf: "rgba(63,138,200,0.9)" },
    water: { zh: "水", c1: "#3f8ac8", c2: "#cdeeff", g: "rgba(90,170,240,0.9)", surf: "rgba(63,138,200,0.85)" },
    mist: { zh: "霧", c1: "#dfe4e2", c2: "#ffffff", g: "rgba(232,236,234,0.9)", surf: "rgba(220,226,224,0.7)" },
    poison: { zh: "毒", c1: "#7ac83a", c2: "#d8f0a0", g: "rgba(130,210,70,0.9)", surf: "rgba(90,150,40,0.8)" },
  };
  // ---------- 飛行物 ----------
  function projectile(ctx, el, from, to, t, traj) {
    if (t <= 0 || t >= 1) return;
    const E = EL[el]; let x = mix(from[0], to[0], t), y = mix(from[1], to[1], t);
    if (traj === "arc") y -= Math.sin(t * Math.PI) * 22; else if (traj === "spiral") { const r = 8 * Math.sin(t * Math.PI); y += Math.sin(t * 20) * r; }
    if (el === "lightning") { // 雷：瞬間的鋸齒線，閃兩下
      if (Math.floor(t * 8) % 2 === 1) return;
      ctx.save(); ctx.shadowColor = E.c1; ctx.shadowBlur = 10; ctx.strokeStyle = E.c2; ctx.lineWidth = 2.4; ctx.beginPath(); ctx.moveTo(from[0], from[1]);
      const n = 7; for (let k = 1; k <= n; k++) { const u = k / n * Math.min(1, t * 2.5); ctx.lineTo(mix(from[0], to[0], u) + (k < n ? (rnd(el + t.toFixed(1), k) - 0.5) * 16 : 0), mix(from[1], to[1], u) + (k < n ? (rnd(el, k + 9) - 0.5) * 12 : 0)); }
      ctx.stroke(); ctx.restore(); return;
    }
    // 尾跡
    for (let k = 1; k <= 6; k++) { const u = Math.max(0, t - k * 0.03); let tx = mix(from[0], to[0], u), ty = mix(from[1], to[1], u); if (traj === "arc") ty -= Math.sin(u * Math.PI) * 22; else if (traj === "spiral") ty += Math.sin(u * 20) * 8 * Math.sin(u * Math.PI); glow(ctx, tx, ty, 7 - k * 0.8, E.g, 0.5 - k * 0.07); }
    if (el === "ice") { ctx.save(); ctx.translate(x, y); ctx.rotate(Math.atan2(to[1] - from[1], to[0] - from[0])); ctx.fillStyle = E.c1; ctx.beginPath(); ctx.moveTo(10, 0); ctx.lineTo(-4, -5); ctx.lineTo(-8, 0); ctx.lineTo(-4, 5); ctx.closePath(); ctx.fill(); ctx.strokeStyle = E.c2; ctx.lineWidth = 1.2; ctx.stroke(); ctx.restore(); }
    else if (el === "mist") { for (let k = 0; k < 3; k++) glow(ctx, x + (k - 1) * 5, y + (k % 2) * 3, 10, E.g, 0.7); }
    else if (el === "water" || el === "poison") { ctx.fillStyle = E.c1; ctx.beginPath(); ctx.ellipse(x, y, 6, 5, 0, 0, TAU); ctx.fill(); ctx.fillStyle = "rgba(255,255,255,0.6)"; ctx.beginPath(); ctx.arc(x - 2, y - 2, 1.6, 0, TAU); ctx.fill(); }
    else { glow(ctx, x, y, 12, E.g, 0.9); ctx.fillStyle = E.c2; ctx.beginPath(); ctx.arc(x, y, 4, 0, TAU); ctx.fill(); }
  }
  // ---------- 爆發 ----------
  function burst(ctx, el, p, t, shape) {
    if (t <= 0 || t >= 1) return;
    const E = EL[el], a = 1 - t; glow(ctx, p[0], p[1], 20 + 20 * t, E.g, a * 0.8);
    ctx.save(); ctx.globalAlpha = a; ctx.shadowColor = E.c1; ctx.shadowBlur = 8;
    if (shape === "ring") { ctx.strokeStyle = E.c1; ctx.lineWidth = 4 * a + 1; ctx.beginPath(); ctx.ellipse(p[0], p[1], 6 + 26 * t, 3 + 12 * t, 0, 0, TAU); ctx.stroke(); }
    else if (shape === "star") { ctx.fillStyle = E.c1; ctx.beginPath(); for (let k = 0; k < 10; k++) { const ang = -Math.PI / 2 + k * Math.PI / 5, r = (k % 2 ? 5 : 14 + 10 * t) * (0.7 + t); ctx[k ? "lineTo" : "moveTo"](p[0] + Math.cos(ang) * r, p[1] + Math.sin(ang) * r * 0.7); } ctx.closePath(); ctx.fill(); }
    else for (let k = 0; k < 10; k++) { const ang = k / 10 * TAU + rnd(el, k) * 0.3; ctx.strokeStyle = k % 2 ? E.c1 : E.c2; ctx.lineWidth = 2.2; ctx.beginPath(); ctx.moveTo(p[0] + Math.cos(ang) * 5 * t, p[1] + Math.sin(ang) * 3 * t); ctx.lineTo(p[0] + Math.cos(ang) * (8 + 22 * t), p[1] + Math.sin(ang) * (5 + 12 * t)); ctx.stroke(); }
    // 元素的專屬粒子
    for (let k = 0; k < 8; k++) { const ang = rnd(el + "p", k) * TAU, d = 10 + 26 * t * (0.6 + rnd(el + "d", k) * 0.6), x = p[0] + Math.cos(ang) * d, y = p[1] + Math.sin(ang) * d * 0.6 - (el === "fire" ? 14 * t : 0) + (el === "water" || el === "poison" ? 16 * t * t : 0);
      ctx.fillStyle = k % 2 ? E.c1 : E.c2; if (el === "ice") { ctx.fillRect(x - 1.5, y - 1.5, 3, 3); } else { ctx.beginPath(); ctx.arc(x, y, el === "mist" ? 4 : 2, 0, TAU); ctx.fill(); } }
    ctx.restore();
  }
  // ---------- 地表擴散：十字 5 格，從中心一格一格長出去 ----------
  function surface(ctx, el, center, T, t, variant) {
    if (t <= 0) return;
    const E = EL[el], cells = [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]];
    cells.forEach(([dx, dy], i) => {
      const local = clamp((t - (i === 0 ? 0 : 0.25 + (variant === "sweep" ? i * 0.1 : 0.05))) / 0.5); if (local <= 0) return;
      const cx = center[0] + dx * T, cy = center[1] + dy * T * 0.62, r = T * 0.46 * ease(local);
      ctx.save(); ctx.globalAlpha = 0.95;
      // 有機形狀：幾個圓疊在一起（位置由雜湊決定）
      ctx.fillStyle = E.surf; for (let k = 0; k < 4; k++) { const ox = (rnd(el + i, k) - 0.5) * T * 0.3, oy = (rnd(el + i, k + 4) - 0.5) * T * 0.18; ctx.beginPath(); ctx.ellipse(cx + ox, cy + oy, r * 0.7, r * 0.42, 0, 0, TAU); ctx.fill(); }
      ctx.restore();
      if (el === "fire") for (let k = 0; k < 3; k++) { const fx = cx + (rnd("ff" + i, k) - 0.5) * r, fy = cy + (rnd("fy" + i, k) - 0.5) * r * 0.3, h = (6 + 6 * Math.sin(t * 20 + k + i)) * local; ctx.fillStyle = k % 2 ? EL.fire.c1 : EL.fire.c2; ctx.beginPath(); ctx.moveTo(fx - 3, fy); ctx.quadraticCurveTo(fx, fy - h * 2, fx + 3, fy); ctx.fill(); }
      if (el === "ice") { ctx.strokeStyle = "rgba(255,255,255,0.9)"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(cx - r * 0.4, cy - 2); ctx.lineTo(cx + r * 0.2, cy + 3); ctx.lineTo(cx + r * 0.5, cy - 1); ctx.stroke(); }
      if (el === "lightning" && local > 0.3) { ctx.save(); ctx.shadowColor = EL.lightning.c1; ctx.shadowBlur = 8; ctx.strokeStyle = EL.lightning.c2; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.moveTo(center[0], center[1]); for (let k = 1; k <= 4; k++) ctx.lineTo(mix(center[0], cx, k / 4) + (rnd("ch" + i + Math.floor(t * 10), k) - 0.5) * 8, mix(center[1], cy, k / 4) + (rnd("cv" + i, k) - 0.5) * 6); ctx.stroke(); ctx.restore(); }
      if (el === "water" || el === "poison") { ctx.strokeStyle = el === "water" ? "rgba(255,255,255,0.5)" : "rgba(220,255,160,0.6)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.ellipse(cx, cy, r * 0.35 * (1 + 0.3 * Math.sin(t * 10 + i)), r * 0.15, 0, 0, TAU); ctx.stroke(); }
      if (el === "poison") for (let k = 0; k < 2; k++) { ctx.fillStyle = EL.poison.c2; ctx.beginPath(); ctx.arc(cx + (rnd("pb" + i, k) - 0.5) * r, cy - ((t * 3 + k * 0.5) % 1) * 8, 1.8, 0, TAU); ctx.fill(); }
      if (el === "mist") glow(ctx, cx + Math.sin(t * 3 + i) * 4, cy - 4, r * 1.1, "rgba(240,244,242,0.9)", 0.5 * local);
    });
  }
  /** 一格畫面：地面（雲嶺草地或荒原焦土）、施放者、目標區；t＝0～1 的時間軸。 */
  function frame(ctx, W, H, el, t, opt = {}) {
    const region = opt.region ?? "cloud", T = 46;
    ctx.fillStyle = region === "ashen" ? "#4a3a30" : "#6a9a6a"; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "rgba(0,0,0,0.12)"; for (let x = 0; x < W; x += T) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    if (region === "ashen") { ctx.strokeStyle = "rgba(255,106,26,0.5)"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(30, H); ctx.lineTo(44, H * 0.6); ctx.lineTo(36, H * 0.3); ctx.stroke(); }
    const from = [26, H * 0.55], to = [W * 0.66, H * 0.55];
    // 施放者（小紙娃娃）
    if (window.StoryDoll) StoryDoll.stamp(ctx, { look: { skin: "#f1c9a5", hair: "long", hairColor: "#1a1a1a" }, gear: { body: { kind: "robe", color: "#5a3a9a" } } }, "side", from[0], from[1] + 16, 0.7, false);
    surface(ctx, el, to, T, (t - 0.6) / 0.4, opt.spread);
    projectile(ctx, el, [from[0] + 6, from[1] - 14], to, t / 0.4, opt.traj ?? "arc");
    burst(ctx, el, to, (t - 0.4) / 0.25, opt.burst ?? "rays");
  }
  return { EL, frame };
})();
