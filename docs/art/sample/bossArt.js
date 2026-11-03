// 兩位頭目的專屬造型（美術 PM，2026-11-04）：灰燼之心、碎晶之主。C 手繪墨線畫法（storyDoll.js 的畫法層 H）。
// 取代 5A-ART4 的通用示意（灰燼之心＝晶靈 huge＋熔岩殼；碎晶之主＝傀儡 huge）。代決 #8 的後續，等使用者看過再定。
// 「部件＋關節」的寫法和骨架動畫一致：每塊殼片、每片浮晶都是一個部件，有自己的掛點，動畫只改掛點的位移、旋轉、縮放。
// 確定性：殼片脫落的方向、碎晶的軌道相位都由部件名稱雜湊決定，不用 Math.random()。
window.BossArt = (() => {
  const { ink, stroke, ellPts, INK, mix, dark, light } = StoryDoll.H;
  const TAU = Math.PI * 2;
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  function seedOf(s) { let h = 2166136261; for (const ch of s) h = Math.imul(h ^ (ch.codePointAt(0) ?? 0), 16777619); return h >>> 0; }
  const rnd = (key, k = 0) => ((seedOf(`${key}:${k}`) % 10000) / 10000);
  function glow(ctx, x, y, r, color, a) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, color); g.addColorStop(1, "rgba(0,0,0,0)"); ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); ctx.restore(); }

  // =========================== 灰燼之心 ===========================
  // 一塊會呼吸的源晶核心殘片，嵌在熔岩甲蟲堆成的殼裡；不移動。
  // 階段：1 殼（熔殼，傷害 −40%）→ 2 呼吸（殼裂開、脫落，殼縫爬出餘燼蜥）→ 3 熔毀（核心龜裂、白熱、滴熔岩）。
  const BASALT = "#3a3330", BASALT_L = "#5c504a", LAVA = "#ff6a1a", LAVA_HOT = "#ffd23a", CORE = "#ffb23a";
  /** 殼片：[名稱, 掛點 x, 掛點 y, 旋轉, 寬, 高]；掛點在核心周圍一圈（腳底為 0，往上為 -y）。 */
  const PLATES = [
    ["p-back-l", -20, -34, -0.5, 18, 13], ["p-back-r", 20, -34, 0.5, 18, 13], ["p-top", 0, -44, 0, 20, 12],
    ["p-left", -26, -20, -0.9, 16, 14], ["p-right", 26, -20, 0.9, 16, 14],
    ["p-low-l", -18, -8, -0.3, 20, 12], ["p-low-r", 18, -8, 0.3, 20, 12], ["p-front", 0, -12, 0, 22, 12],
    ["p-mid-l", -12, -30, -0.2, 14, 11], ["p-mid-r", 12, -30, 0.2, 14, 11],
  ];
  /** 一片甲蟲殼（橢圓背甲＋中線＋殼縫透光）。 */
  function plate(ctx, key, w, h, heat) {
    ink(ctx, key, ellPts(0, 0, w / 2, h / 2, 16), BASALT_L, { w: 0.9 });
    stroke(ctx, `${key}-mid`, [[0, -h / 2 + 1], [0, h / 2 - 1]], 0.8, INK);
    ctx.save(); ctx.globalAlpha = 0.35 + 0.5 * heat; stroke(ctx, `${key}-crack`, [[-w * 0.3, -1], [-w * 0.1, 1.5], [w * 0.15, -0.5], [w * 0.32, 1]], 1.1, LAVA_HOT); ctx.restore();
    ctx.fillStyle = "rgba(255,255,255,0.18)"; ctx.beginPath(); ctx.ellipse(-w * 0.18, -h * 0.2, w * 0.18, h * 0.12, -0.3, 0, TAU); ctx.fill();
  }
  /** 核心：多面的源晶，裡面一明一暗地呼吸；crack＝熔毀的龜裂程度 0～1。 */
  function core(ctx, cx, cy, breath, crack) {
    const s = 1 + 0.06 * breath;
    glow(ctx, cx, cy, 30 * s, "rgba(255,170,60,0.9)", 0.5 + 0.35 * breath + 0.3 * crack);
    ctx.save(); ctx.translate(cx, cy); ctx.scale(s, s);
    const pts = [[0, -15], [10, -8], [11, 4], [4, 13], [-6, 12], [-11, 3], [-9, -9]];
    ink(ctx, "core", pts, mix(CORE, "#fff4d0", 0.35 * breath + 0.4 * crack), { w: 1, shade: false });
    stroke(ctx, "core-f1", [[0, -15], [1, 0], [4, 13]], 0.7, "rgba(120,50,10,0.7)");
    stroke(ctx, "core-f2", [[-9, -9], [1, 0], [11, 4]], 0.7, "rgba(120,50,10,0.7)");
    ctx.fillStyle = `rgba(255,255,240,${0.5 + 0.4 * breath})`; ctx.beginPath(); ctx.ellipse(-3, -6, 3, 5, -0.4, 0, TAU); ctx.fill();
    if (crack > 0) { ctx.save(); ctx.globalAlpha = crack; ctx.shadowColor = "#ffffff"; ctx.shadowBlur = 8; stroke(ctx, "core-cr1", [[-2, -12], [2, -4], [-1, 3], [3, 10]], 1.4, "#ffffff"); stroke(ctx, "core-cr2", [[8, -6], [3, -2], [7, 6]], 1.2, "#fff4c0"); ctx.restore(); }
    ctx.restore();
  }
  /**
   * 畫灰燼之心。st：{phase: 1|2|3, shell: 0～1（熔殼還在＝1；status_traits molten_shell 決定）, breakT: 殼脫落進度 0～1, t: 毫秒, flash, spout: 0～1, inhale: 0～1}
   * 腳底在 (0,0)，大小約 3 格寬（huge）。
   */
  function drawAshenHeart(ctx, st) {
    const t = st.t ?? 0, breath = 0.5 + 0.5 * Math.sin(t / 420), phase = st.phase ?? 1;
    const crack = phase === 3 ? 0.6 + 0.4 * Math.sin(t / 160) : 0;
    // 底座：熔岩甲蟲堆（不會掉，是坑底的岩堆）
    ctx.fillStyle = "rgba(0,0,0,0.35)"; ctx.beginPath(); ctx.ellipse(0, 0, 40, 9, 0, 0, TAU); ctx.fill();
    ink(ctx, "base", [[-38, 0], [-34, -10], [-22, -16], [0, -18], [22, -16], [34, -10], [38, 0]], BASALT, { w: 1 });
    for (const [k, x] of [["b1", -24], ["b2", -8], ["b3", 10], ["b4", 26]]) { ink(ctx, k, ellPts(x, -6, 7, 4.4, 12), BASALT_L, { w: 0.6 }); stroke(ctx, `${k}-l`, [[x - 5, -3], [x - 8, 0]], 0.7, INK); }
    // 熔毀：坑底的熔岩光與滴落
    if (phase === 3) { glow(ctx, 0, -6, 46, "rgba(255,110,30,0.9)", 0.5); for (let k = 0; k < 4; k++) { const ph = ((t / 900 + rnd("drip", k)) % 1); ctx.fillStyle = LAVA; ctx.beginPath(); ctx.ellipse(-20 + k * 13, -14 + ph * 14, 1.6, 2.6, 0, 0, TAU); ctx.fill(); } }
    // 核心
    const cy = -28 - (st.inhale ?? 0) * 2;
    core(ctx, 0, cy, breath, crack);
    // 吸氣：火星往核心收
    if ((st.inhale ?? 0) > 0) for (let k = 0; k < 12; k++) { const a = rnd("in", k) * TAU, d = 60 * (1 - ((t / 600 + rnd("in2", k)) % 1)); ctx.fillStyle = LAVA_HOT; ctx.globalAlpha = st.inhale; ctx.beginPath(); ctx.arc(Math.cos(a) * d, cy + Math.sin(a) * d * 0.6, 1.8, 0, TAU); ctx.fill(); ctx.globalAlpha = 1; }
    // 噴發：殼頂的熔岩柱
    if ((st.spout ?? 0) > 0) { const k = st.spout; glow(ctx, 0, -60, 26, "rgba(255,140,40,0.9)", k); ctx.save(); ctx.globalAlpha = k; ctx.fillStyle = LAVA; ctx.beginPath(); ctx.moveTo(-5, -46); ctx.quadraticCurveTo(-8, -60 - 30 * k, 0, -70 - 34 * k); ctx.quadraticCurveTo(8, -60 - 30 * k, 5, -46); ctx.fill(); ctx.fillStyle = LAVA_HOT; ctx.beginPath(); ctx.ellipse(0, -60 - 20 * k, 2.4, 10 * k, 0, 0, TAU); ctx.fill(); ctx.restore(); }
    // 殼片：熔殼在＝全部貼著；脫落＝依名稱雜湊往外飛、旋轉、落下（重力），落地後留在地上變暗
    const shell = st.shell ?? 1, bt = st.breakT ?? (shell > 0 ? 0 : 1);
    for (const [key, x, y, r, w, h] of PLATES) {
      let px = x, py = y, pr = r, a = 1;
      if (shell <= 0) {
        const dir = Math.sign(x || (rnd(key) - 0.5)) || 1, vx = dir * (16 + 22 * rnd(key, 1)), vy = -(18 + 18 * rnd(key, 2)), spin = (rnd(key, 3) - 0.5) * 6;
        const tt = clamp(bt) * 0.9;
        px = x + vx * tt; py = Math.min(-2, y + vy * tt + 70 * tt * tt); pr = r + spin * tt;
        if (bt >= 1) { py = -2 - 2 * rnd(key, 4); px = x * 1.6 + dir * 8; pr = r + spin * 0.8; a = 0.75; }
      } else {
        // 殼在的時候也會隨呼吸微微張開，殼縫的光跟著亮
        const open = 0.6 * breath; px = x * (1 + 0.02 * open); py = y - open * 0.6;
      }
      ctx.save(); ctx.globalAlpha = a; ctx.translate(px, py); ctx.rotate(pr); plate(ctx, key, w, h, shell > 0 ? breath : 0.2); ctx.restore();
    }
    if (st.flash) { /* 受擊白閃由呼叫端用 filter 疊 */ }
  }

  // =========================== 碎晶之主 ===========================
  // 浮在裂界門浮台上的源晶君主：晶冠、胸口核心、兩片浮空的手晶、下半身拖著碎晶；三柱階段被三道光束灌注（不受骰值傷害）。
  // 階段：1 三柱（灌注光束、護罩）→ 2 碎界脈動（碎晶繞身旋轉）→ 3 核心過載（核心裂開發白、瞬步殘影）→ 4 界崩（全身崩解、紫紅色）。
  const CRYST = "#b8a8ff", CRYST_D = "#6a5ad0", RIFT = "#8a4ad0", CORE2 = "#e0ffff";
  function shard(ctx, key, x, y, len, wid, rot, color) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot);
    ink(ctx, key, [[0, -len], [wid, -len * 0.25], [wid * 0.6, len * 0.4], [0, len * 0.5], [-wid * 0.7, len * 0.3], [-wid, -len * 0.3]], color, { w: 0.8, sharp: true });
    stroke(ctx, `${key}-f`, [[0, -len], [0, len * 0.5]], 0.6, "rgba(255,255,255,0.55)");
    ctx.restore();
  }
  /** st：{phase: 1～4, t, cast: 0～1（手晶前伸）, blink: 0～1（瞬步殘影）, channel: 是否被三柱灌注} */
  function drawShardLord(ctx, st) {
    const t = st.t ?? 0, phase = st.phase ?? 1, hover = -10 - 3 * Math.sin(t / 500), cast = st.cast ?? 0;
    const tint = phase === 4 ? (c) => mix(c, "#ff5a8a", 0.35) : (c) => c;
    // 影子（浮空）
    ctx.fillStyle = "rgba(0,0,0,0.3)"; ctx.beginPath(); ctx.ellipse(0, 0, 26, 6, 0, 0, TAU); ctx.fill();
    // 瞬步殘影
    if ((st.blink ?? 0) > 0) for (let g = 1; g <= 3; g++) { ctx.save(); ctx.globalAlpha = 0.18 * st.blink; ctx.translate(-g * 14, 0); drawShardLordBody(ctx, { ...st, blink: 0 }, hover, cast, tint, phase); ctx.restore(); }
    drawShardLordBody(ctx, st, hover, cast, tint, phase);
    // 灌注光束（三柱階段）：三道光從畫面外打進核心
    if (phase === 1 && st.channel !== false) for (let k = 0; k < 3; k++) { const a = -Math.PI / 2 + (k - 1) * 0.9; ctx.save(); ctx.globalAlpha = 0.5 + 0.3 * Math.sin(t / 200 + k); ctx.strokeStyle = ["#ff7a2a", "#9ad8c8", "#c8a0ff"][k]; ctx.lineWidth = 3; ctx.shadowColor = ctx.strokeStyle; ctx.shadowBlur = 10; ctx.beginPath(); ctx.moveTo(Math.cos(a) * 90, hover - 40 + Math.sin(a) * 60); ctx.lineTo(0, hover - 40); ctx.stroke(); ctx.restore(); }
  }
  function drawShardLordBody(ctx, st, hover, cast, tint, phase) {
    const t = st.t ?? 0;
    ctx.save(); ctx.translate(0, hover);
    // 下半身：一串往下漸小的碎晶（崩解階段散得更開）
    const spread = phase === 4 ? 1.8 : 1;
    for (let k = 0; k < 5; k++) { const ph = t / 700 + rnd("tail", k) * TAU; shard(ctx, `tail-${k}`, Math.sin(ph) * 3 * spread + (rnd("tx", k) - 0.5) * 8 * spread, -8 + k * 5 * spread, 7 - k, 4 - k * 0.5, Math.sin(ph) * 0.3, tint(k % 2 ? CRYST_D : CRYST)); }
    // 軀幹：倒三角晶塊
    ink(ctx, "torso", [[-16, -52], [16, -52], [10, -30], [4, -14], [-4, -14], [-10, -30]], tint(CRYST), { w: 1.1 });
    stroke(ctx, "torso-f1", [[-16, -52], [0, -34], [16, -52]], 0.8, "rgba(60,40,140,0.6)");
    stroke(ctx, "torso-f2", [[0, -34], [0, -14]], 0.8, "rgba(60,40,140,0.6)");
    // 胸口核心：過載時裂開發白
    const over = phase >= 3 ? 0.7 + 0.3 * Math.sin(t / 130) : 0.4 + 0.2 * Math.sin(t / 400);
    glow(ctx, 0, -40, 22, phase === 4 ? "rgba(255,90,140,0.9)" : "rgba(160,240,255,0.9)", over);
    ink(ctx, "core2", [[0, -47], [6, -40], [0, -33], [-6, -40]], mix(CORE2, "#ffffff", over * 0.5), { w: 0.9, shade: false });
    if (phase >= 3) { ctx.save(); ctx.shadowColor = "#ffffff"; ctx.shadowBlur = 8; stroke(ctx, "core2-cr", [[-2, -46], [1, -41], [-1, -36]], 1.2, "#ffffff"); ctx.restore(); }
    // 頭：小晶面＋晶冠（5 根）
    ink(ctx, "head2", [[-6, -62], [6, -62], [7, -55], [0, -51], [-7, -55]], tint(light(CRYST, 0.2)), { w: 0.9 });
    ctx.fillStyle = phase >= 3 ? "#ffffff" : CORE2; for (const x of [-2.6, 2.6]) { ctx.beginPath(); ctx.ellipse(x, -57, 1.2, 0.8, 0, 0, TAU); ctx.fill(); }
    for (let k = 0; k < 5; k++) shard(ctx, `crown-${k}`, -10 + k * 5, -64 - (k === 2 ? 6 : k % 2 ? 3 : 0), 7 + (k === 2 ? 5 : 2), 2.2, (k - 2) * 0.22, tint(k === 2 ? CORE2 : CRYST));
    // 肩晶
    shard(ctx, "sh-l", -19, -50, 9, 4, -0.9, tint(CRYST_D)); shard(ctx, "sh-r", 19, -50, 9, 4, 0.9, tint(CRYST_D));
    // 浮空手晶：施法時往前伸（朝東），手心之間的裂界光
    const hx = 26 + 16 * cast, hy = -36 - 4 * Math.sin(t / 360);
    shard(ctx, "hand-l", -hx + 30 * cast, hy + 4, 9, 5, -0.4 + 1.6 * cast, tint(CRYST)); shard(ctx, "hand-r", hx, hy, 9, 5, 0.4 + 1.2 * cast, tint(CRYST));
    if (cast > 0) { glow(ctx, hx + 10, hy, 16, "rgba(200,160,255,0.9)", cast); }
    // 碎界脈動：碎晶繞身旋轉（相位由名稱雜湊）
    if (phase >= 2) for (let k = 0; k < 6; k++) { const a = t / 800 + rnd("orb", k) * TAU, r = 30 + 4 * Math.sin(t / 300 + k); const x = Math.cos(a) * r, y = -36 + Math.sin(a) * r * 0.35; if (Math.sin(a) < 0 === false) shard(ctx, `orb-${k}`, x, y, 5, 2.6, a, tint(k % 2 ? RIFT : CRYST)); }
    ctx.restore();
  }

  return { drawAshenHeart, drawShardLord, PLATES };
})();
