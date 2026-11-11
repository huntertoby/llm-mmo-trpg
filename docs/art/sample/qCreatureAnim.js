// qCreatureAnim.js：Q 版異形的動畫片段（畫圖 agent，2026-11-07）。使用者（11-07）：「分然後這些怪物都要有動畫」。
// 美術 PM 追加（11-07，使用者問「這些怪物都只有一種攻擊方式嗎只有一個技能」）：攻擊依「動作類型」分開做，
//   每款身形照實際用它的單位（content/units/*.yaml 的普攻武器＋技能）做對應的類型；類型的骨架可跨身形共用，但依身形換部件。
// 做法：qCreature.js 的部件名稱 → 部件組（RIG：腿、翅、尾、頭、身體、手臂…，各有支點），這裡只算每個組的變換（旋轉、位移、斜切、縮放、透明）
//   ＋整隻的變換（root）＋白閃、透明度、影子；特效（飛行物、吐息、震地環…）畫在地面座標。不碰畫法，靜態畫面不變。
// 確定性：全部是 t（毫秒）的純函式，不用 Math.random；循環片段的相位用 id 的 FNV-1a 雜湊（同 client idleClips.idHash）。
// 量化：循環片段（待機、移動）一圈 8 格；攻擊、受擊、倒下 12 格／秒（83 毫秒一格），倒下停在最後一格。
// 減少動態（reduce）：待機、移動站好不動；攻擊只往前推 2 單位再回來（特效照放，因為它是資訊）；受擊只白閃 1 格；倒下直接最後一格。
window.QCreatureAnim = (() => {
  const QC = window.QCreature, TAU = Math.PI * 2, OUT = QC.OUT;
  const cl = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const seg = (u, a, b) => cl((u - a) / (b - a));
  const sm = (x) => x * x * (3 - 2 * x);
  const bump = (u, a, b) => Math.sin(Math.PI * seg(u, a, b));
  const S = (u, n = 1, ph = 0) => Math.sin(TAU * (u * n + ph));
  const Cn = (u, n = 1, ph = 0) => Math.cos(TAU * (u * n + ph));
  /** 關鍵格內插：pts＝[[u, 值], …]，兩格之間用 smoothstep。 */
  function kf(u, pts) {
    if (u <= pts[0][0]) return pts[0][1];
    for (let i = 1; i < pts.length; i++) if (u <= pts[i][0]) { const [a, va] = pts[i - 1], [b, vb] = pts[i]; return va + (vb - va) * sm((u - a) / (b - a || 1)); }
    return pts[pts.length - 1][1];
  }
  function idHash(id) { let h = 2166136261; for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619); return h >>> 0; }
  const ELEM = QC.ELEM;
  const MUL = new Set(["sx", "sy", "a"]);
  function newPose() { return { root: {}, parts: {}, flash: 0, alpha: 1, shadow: 1, fx: [] }; }
  function merge(o, f) { for (const k in f) { if (k === "pivot") o.pivot = f.pivot; else if (MUL.has(k)) o[k] = (o[k] ?? 1) * f[k]; else o[k] = (o[k] ?? 0) + f[k]; } }
  const A = (p, g, f) => merge(p.parts[g] ?? (p.parts[g] = {}), f);
  const R = (p, f) => merge(p.root, f);
  const FX = (p, f) => p.fx.push(f);
  /** 飛行物：u 在 [a, b] 從 (x0,y0) 飛到 (x1,y1)，拱高 h；回傳 null＝還沒出手／已到。 */
  function proj(u, a, b, x0, y0, x1, y1, h = 0) { if (u < a || u > b) return null; const q = seg(u, a, b); return [x0 + (x1 - x0) * q, y0 + (y1 - y0) * q - h * Math.sin(Math.PI * q)]; }
  const TGT = 52; // 目標（相鄰格）的 x：1 格＝48 像素／倍率約 1，取 52 單位

  // ============================== 共用骨架 ==============================
  const LEGS4 = [["FN", 0], ["BF", 0], ["FF", 0.5], ["BN", 0.5]]; // 對角步：近前＋遠後一組、遠前＋近後一組
  function breathe(p, u, amt = 0.025) { R(p, { sy: 1 + amt * (0.5 - 0.5 * Cn(u)) }); }
  /** 四足對角步：腳底前後＝斜切 kx（往前擺時抬腳＝sy 縮短）；身體一步一顛（一圈兩顛）。 */
  function quadWalk(p, u, c) {
    for (const [g, ph] of LEGS4) { const sw = S(u, 1, ph), lift = Math.max(0, Cn(u, 1, ph)); A(p, g, { kx: -c.amp * sw, sy: 1 - c.lift * lift }); }
    R(p, { dy: -c.bob * (0.5 - 0.5 * Cn(u, 2)) });
    A(p, "head", { rot: c.nod * S(u, 2, 0.15) }); if (c.tail) A(p, "tail", { rot: c.tail * S(u, 1, 0.25) });
  }
  /** 六腳三腳架步：一組 3 隻同相。 */
  function hexWalk(p, u, groups, c) { groups.forEach((gs, i) => gs.forEach((g) => { const sw = S(u, 1, i * 0.5), lift = Math.max(0, Cn(u, 1, i * 0.5)); A(p, g, c.rot ? { rot: c.amp * sw, dy: -c.lift * lift } : { kx: -c.amp * sw, sy: 1 - c.lift * lift }); })); R(p, { dy: -c.bob * (0.5 - 0.5 * Cn(u, 2)) }); }
  /** 拍翅：wing sy 從 1.05（上舉）到 -0.55（下壓）；下拍快（前 40%）、上收慢；下拍時身體往上。 */
  function flap(p, u, c = {}) {
    const q = u < 0.4 ? sm(u / 0.4) : 1 - sm((u - 0.4) / 0.6), up = c.up ?? 1.05, dn = c.dn ?? -0.55, sy = up + (dn - up) * q;
    A(p, "wingN", { sy, rot: 0.12 * q }); A(p, "wingF", { sy: up + (dn - up) * cl(q * 0.92), rot: 0.1 * q });
    R(p, { dy: -(c.bob ?? 1.6) * Math.sin(Math.PI * q) + (c.base ?? 0) });
    return q;
  }
  /** 翻面的 sy：跳過 0 附近（不會出現「一條線」的那格；審查退回 #1）。 */
  const flipSy = (f) => { const c = Math.cos(Math.PI * f); return Math.abs(c) < 0.5 ? (f < 0.5 ? 0.5 : -0.5) : c; };
  function quadLegsTuck(p, k) { for (const [g] of LEGS4) A(p, g, { sy: 1 - k }); }
  /** 以 N 為分母的關鍵格（格號 → u＝格號／N），命中格落在量化格上。 */
  const kfN = (u, N, pts) => kf(u, pts.map(([f, v]) => [f / N, v]));
  /** 腳踩地（第二種近戰片段用）：腳底留在「靜止位置＋off」、離地 lift，由髖的實際位置反推腿的斜切與長度，不穿地、不打滑；抵消 root 的旋轉。
   *  髖抬太高時腿最多拉到 maxS 倍，再高就自然離地。feet＝[[組, off, lift], …]；root 要先設好。 */
  function plant(p, e, feet, maxS = 1.12) {
    const piv = QC.RIG[e.bk].pivots, o = p.root, [rx, ry] = o.pivot ?? [0, 0], th = o.rot ?? 0, c = Math.cos(th), s = Math.sin(th);
    for (const [g, off = 0, lift0 = 0] of feet) {
      const [px, py] = piv[g], a = px - rx, b = py - ry, X = rx + (o.dx ?? 0) + a * c - b * s, Y = ry + (o.dy ?? 0) + a * s + b * c, L = -py;
      const lift = Math.max(lift0, -Y - L * maxS), h = Math.max(1, -Y - lift);
      A(p, g, { rot: -th, kx: (px + off - X) / h, sy: h / L });
    }
  }

  /** 部件上的一點（靜態座標）算到地面座標：套部件變換、大頭倍率、root。特效要從部件出發時用（pose 先設好）。 */
  function ptOf(p, e, g, x, y) {
    const f = p.parts[g] ?? {}, [px, py] = f.pivot ?? QC.RIG[e.bk].pivots[g] ?? [0, 0], o = p.root, [rx, ry] = o.pivot ?? [0, 0];
    let a = (x - px) * (f.sx ?? 1), b = (y - py) * (f.sy ?? 1); a += (f.kx ?? 0) * b;
    const r = f.rot ?? 0; let X = px + (f.dx ?? 0) + a * Math.cos(r) - b * Math.sin(r), Y = py + (f.dy ?? 0) + a * Math.sin(r) + b * Math.cos(r);
    if (g === "head" && e.r.b.qHead) { const [, hx, hy, s] = e.r.b.qHead; X = hx + (X - hx) * s; Y = hy + (Y - hy) * s; }
    const th = o.rot ?? 0, c = Math.cos(th), s = Math.sin(th), A0 = X - rx, B0 = Y - ry;
    return [rx + (o.dx ?? 0) + A0 * c - B0 * s, ry + (o.dy ?? 0) + A0 * s + B0 * c];
  }

  // ---- 受擊、倒下（依類別） ----
  function hitCommon(p, u, back = 3, tilt = 0.08) { p.flash = u < 0.2 ? 0.9 : 0; R(p, { dx: -kf(u, [[0, 0], [0.18, back], [1, 0]]), rot: -tilt * kf(u, [[0, 0], [0.18, 1], [1, 0]]) }); }
  const HIT = {
    quad(p, u) { hitCommon(p, u); A(p, "head", { rot: -0.28 * kf(u, [[0, 0], [0.18, 1], [1, 0]]) }); A(p, "tail", { rot: 0.2 * bump(u, 0, 0.6) }); for (const g of ["FN", "FF"]) A(p, g, { kx: 0.18 * bump(u, 0, 0.7) }); },
    flyer(p, u) { hitCommon(p, u, 4, 0.22); R(p, { dy: -3 * bump(u, 0, 0.8) }); for (const g of ["wingN", "wingF"]) A(p, g, { sy: 1 + 0.25 * bump(u, 0, 0.5) }); A(p, "head", { rot: -0.3 * bump(u, 0, 0.7) }); },
    crawler(p, u) { hitCommon(p, u, 2.5, 0.1); A(p, "head", { rot: -0.25 * bump(u, 0, 0.7) }); for (const g of ["N0", "N1", "N2", "N3", "F0", "F1", "F2", "F3"]) A(p, g, { kx: 0.12 * bump(u, 0, 0.6) }); },
    serpent(p, u) { hitCommon(p, u, 2, 0.04); const k = kf(u, [[0, 0], [0.18, 1], [1, 0]]); A(p, "neck", { kx: 0.32 * k }); A(p, "head", { dx: -5.5 * k, rot: -0.35 * k }); },
    shell(p, u) { hitCommon(p, u, 2, 0.05); const k = kf(u, [[0, 0], [0.15, 1], [0.7, 1], [1, 0]]); A(p, "head", { dx: -3.5 * k, sx: 1 - 0.3 * k }); quadLegsTuck(p, 0.45 * k); R(p, { dy: 3 * 0.45 * k * 0.8 }); },
    ooze(p, u) { p.flash = u < 0.2 ? 0.9 : 0; const k = kf(u, [[0, 0], [0.15, 1], [1, 0]]), w = Math.sin(u * 14) * (1 - u); R(p, { dx: -2.5 * k, sx: 1 + 0.2 * k + 0.06 * w, sy: 1 - 0.2 * k - 0.06 * w, kx: -0.12 * k }); A(p, "face", { dx: -1.5 * k, dy: 1.5 * k }); },
    golem(p, u) { hitCommon(p, u, 1.5, 0.05); A(p, "head", { rot: -0.18 * bump(u, 0, 0.6) }); A(p, "armN", { rot: 0.25 * bump(u, 0, 0.6) }); A(p, "armF", { rot: 0.2 * bump(u, 0, 0.6) }); },
    wisp(p, u) { p.flash = u < 0.2 ? 0.9 : 0; const k = kf(u, [[0, 0], [0.15, 1], [1, 0]]); R(p, { dx: -3 * k + (u < 0.6 ? 0.8 * Math.sign(Math.sin(u * 40)) * (1 - u) : 0) }); A(p, "core", { sx: 1 - 0.15 * k, sy: 1 - 0.15 * k }); [[-1, -0.6], [1, -1], [0.3, 1]].forEach(([x, y], i) => A(p, `orb${i}`, { dx: 4 * x * k, dy: 4 * y * k })); },
    wraith(p, u) { hitCommon(p, u, 3, 0.06); const k = bump(u, 0, 0.8); A(p, "body", { kx: -0.25 * k }); A(p, "head", { dx: -2 * k }); A(p, "armN", { rot: 0.5 * k }); A(p, "armB", { rot: 0.4 * k }); p.alpha = 1 - 0.3 * k; },
    pylon(p, u) { p.flash = u < 0.2 ? 0.9 : 0; const j = u < 0.55 ? Math.sign(Math.sin(u * 46)) * (1 - u / 0.55) : 0; A(p, "ob", { dx: -1.2 * j, rot: -0.03 * j }); A(p, "eye", { dx: -1.2 * j, sy: 1 - 0.6 * bump(u, 0, 0.5) }); A(p, "ring", { dx: -1.2 * j, dy: 2 * bump(u, 0, 0.6) }); },
  };
  function deathQuad(p, u, legH, c = {}) {
    p.flash = u < 0.12 ? 0.7 : 0;
    const st = bump(u, 0, 0.35), k = sm(seg(u, 0.25, 0.75));
    R(p, { dx: -2 * st - 1.5 * k, rot: -0.07 * st + 0.04 * k, dy: legH * 0.62 * k });
    quadLegsTuck(p, 0.7 * k);
    A(p, "head", { rot: -0.25 * st + (c.headRot ?? 0.4) * sm(seg(u, 0.45, 0.9)), dy: (c.headDy ?? 3) * sm(seg(u, 0.45, 0.9)) });
    A(p, "tail", { rot: -0.35 * k });
    p.shadow = 1 - 0.15 * k;
  }
  /** 側倒（熊、野豬；QK-4 檢查 §3-1：原本趴著收腳、睜眼像在休息）：晃一下 → 身體落地、四腳伸直往前後攤開（不收在肚子下）、
   *  頭垂到地上、最後閉眼（×）。legH＝腳長（身體落下的量）。 */
  function deathSide(p, u, legH, c = {}) {
    p.flash = u < 0.12 ? 0.7 : 0;
    const st = bump(u, 0, 0.35), k = sm(seg(u, 0.25, 0.75)), hk = sm(seg(u, 0.4, 0.85));
    R(p, { dx: -2 * st - 1 * k, rot: -0.07 * st + 0.05 * k, dy: legH * (c.drop ?? 0.6) * k });
    for (const [g, sgn, f] of [["FN", -1, 1], ["FF", -1, 0.75], ["BN", 1, 1], ["BF", 1, 0.75]]) A(p, g, { rot: sgn * (c.legRot ?? 1.2) * f * k, sy: 1 - 0.08 * k });
    A(p, "head", { rot: -0.25 * st + (c.headRot ?? 0.5) * hk, dy: (c.headDy ?? 3) * hk });
    A(p, "tail", { rot: 0.5 * k });
    if (u >= 0.6) p.eyeShut = true;
    if (u > 0.55 && u < 0.9) FX(p, { k: "dust", x: 0, y: -1, r: 4, a: 1 - seg(u, 0.55, 0.9) });
    p.shadow = 1 - 0.1 * k;
  }

  // ============================== 特效（地面座標，跟著朝向鏡像；實體特效有細外框） ==============================
  const elc = (r, d) => (r.element && ELEM[r.element] ? ELEM[r.element] : d);
  function drawFx(ctx, fxs, r, box = [-70, -90, 74, 18]) {
    const solid = [];
    for (const f of fxs) {
      const a = f.a ?? 1;
      if (f.k === "dust") { ctx.save(); ctx.fillStyle = f.c ?? "#b8a890"; for (const [dx, dy, s] of [[-1, 0, 1], [0.2, -0.5, 1.25], [1.2, 0.1, 0.9]]) { ctx.globalAlpha = 0.55 * a; ctx.beginPath(); ctx.ellipse(f.x + dx * f.r, f.y + dy * f.r * 0.6, f.r * 0.7 * s, f.r * 0.5 * s, 0, 0, TAU); ctx.fill(); } ctx.restore(); }
      else if (f.k === "ring") { const w = f.w ?? 1.4; ctx.save(); ctx.globalAlpha = a; ctx.strokeStyle = OUT; ctx.lineWidth = w + 1.2; ctx.beginPath(); ctx.ellipse(f.x, f.y ?? 0, f.rx, f.rx * 0.3, 0, 0, TAU); ctx.stroke(); ctx.strokeStyle = f.c; ctx.lineWidth = w; ctx.stroke(); ctx.restore(); }
      else if (f.k === "glow") { ctx.save(); ctx.fillStyle = f.c; for (const [s, al] of [[1, 0.18], [0.65, 0.26], [0.35, 0.4]]) { ctx.globalAlpha = al * a; ctx.beginPath(); ctx.arc(f.x, f.y, f.r * s, 0, TAU); ctx.fill(); } ctx.restore(); }
      else if (f.k === "cone") { // 吐息：一串越遠越大越淡的團（平塗），從 (x, y) 往 ang 方向
        ctx.save(); const n = 5; for (let i = 0; i < n; i++) { const q = (i + 0.5) / n; if (q > f.len) continue; const d = q * f.max, rr = 2.2 + q * f.spread, x = f.x + Math.cos(f.ang ?? 0) * d, y = f.y + Math.sin(f.ang ?? 0) * d + Math.sin(i * 2.1 + (f.t ?? 0)) * 1.2;
          ctx.globalAlpha = a * (0.75 - 0.4 * q); ctx.fillStyle = f.c; ctx.beginPath(); ctx.arc(x, y, rr, 0, TAU); ctx.fill(); ctx.globalAlpha = a * (0.8 - 0.5 * q); ctx.fillStyle = f.c2 ?? "#ffffff"; ctx.beginPath(); ctx.arc(x - rr * 0.2, y - rr * 0.2, rr * 0.45, 0, TAU); ctx.fill(); } ctx.restore(); }
      else if (f.k === "wave") { ctx.save(); ctx.globalAlpha = a; for (const [w, c] of [[2.4, OUT], [1.2, f.c]]) { ctx.strokeStyle = c; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.beginPath(); ctx.arc(f.x, f.y, f.r, -0.7, 0.7); ctx.stroke(); } ctx.restore(); }
      else if (f.k === "puff") { ctx.save(); ctx.globalAlpha = 0.5 * a; ctx.fillStyle = f.c ?? "#eef2f4"; ctx.beginPath(); ctx.ellipse(f.x, f.y, f.r, f.r * 0.7, 0, 0, TAU); ctx.fill(); ctx.restore(); }
      else solid.push(f);
    }
    if (!solid.length) return;
    QC.layer(ctx, box, (g) => {
      for (const f of solid) {
        g.save(); g.globalAlpha = f.a ?? 1;
        if (f.k === "orb") { g.fillStyle = f.c; g.beginPath(); g.arc(f.x, f.y, f.r, 0, TAU); g.fill(); g.fillStyle = f.c2 ?? "#ffffff"; g.beginPath(); g.arc(f.x - f.r * 0.15, f.y - f.r * 0.15, f.r * 0.5, 0, TAU); g.fill();
          if (f.tail) { g.globalAlpha *= 0.6; g.fillStyle = f.c; g.beginPath(); g.ellipse(f.x - f.r * 1.6 * f.tail, f.y, f.r * 1.3 * f.tail, f.r * 0.55, 0, 0, TAU); g.fill(); } }
        else if (f.k === "burst") { const n = 7, rr = f.r; g.fillStyle = f.c; g.beginPath(); for (let i = 0; i < n * 2; i++) { const an = (i / (n * 2)) * TAU + 0.2, d = i % 2 ? rr * 0.45 : rr; g[i ? "lineTo" : "moveTo"](f.x + Math.cos(an) * d, f.y + Math.sin(an) * d); } g.closePath(); g.fill(); g.fillStyle = f.c2 ?? "#ffffff"; g.beginPath(); g.arc(f.x, f.y, rr * 0.32, 0, TAU); g.fill(); }
        else if (f.k === "bolt") { const pts = [[f.x0, f.y0]], n = 5; for (let i = 1; i < n; i++) { const q = i / n; pts.push([f.x0 + (f.x1 - f.x0) * q, f.y0 + (f.y1 - f.y0) * q + (i % 2 ? -2.6 : 2.6) * (f.amp ?? 1)]); } pts.push([f.x1, f.y1]);
          for (const [w, c] of [[2.2, f.c], [0.8, "#ffffff"]]) { g.strokeStyle = c; g.lineWidth = w; g.lineJoin = "miter"; g.lineCap = "round"; g.beginPath(); pts.forEach(([x, y], i) => g[i ? "lineTo" : "moveTo"](x, y)); g.stroke(); } }
        else if (f.k === "beam") { g.lineCap = "round"; for (const [w, c] of [[f.w, f.c], [f.w * 0.4, "#ffffff"]]) { g.strokeStyle = c; g.lineWidth = w; g.beginPath(); g.moveTo(f.x0, f.y0); g.lineTo(f.x1, f.y1); g.stroke(); } }
        else if (f.k === "slash") { g.lineCap = "round"; for (let i = 0; i < 3; i++) { g.strokeStyle = f.c ?? "#ffffff"; g.lineWidth = 1.1; g.beginPath(); g.arc(f.x + i * 2.2 - 2.2, f.y + i * 1.2, f.r, (f.ang ?? -0.3) - 0.9 * (f.len ?? 1), (f.ang ?? -0.3) + 0.5); g.stroke(); } }
        else if (f.k === "chomp") { const o = (1 - f.q) * 3.2 + 0.6; g.fillStyle = "#ffffff"; for (const sgn of [-1, 1]) { g.beginPath(); g.moveTo(f.x - 4, f.y + sgn * o); g.quadraticCurveTo(f.x, f.y + sgn * (o + 3), f.x + 4, f.y + sgn * o); for (let i = 3; i >= 0; i--) { const xx = f.x - 3 + i * 2; g.lineTo(xx + 1, f.y + sgn * (o - 1.6)); g.lineTo(xx, f.y + sgn * o); } g.closePath(); g.fill(); } }
        else if (f.k === "shard") { g.translate(f.x, f.y); g.rotate(f.rot ?? 0); const s = f.s ?? 2.4; g.fillStyle = f.c; g.beginPath(); g.moveTo(0, -s * 1.5); g.lineTo(s * 0.7, 0); g.lineTo(0, s * 1.2); g.lineTo(-s * 0.7, 0); g.closePath(); g.fill(); g.fillStyle = "#ffffff"; g.fillRect(-s * 0.2, -s * 0.8, s * 0.3, s * 0.7); }
        else if (f.k === "egg") { g.translate(f.x, f.y); g.rotate(f.rot ?? 0); g.fillStyle = f.c ?? "#ffb23a"; g.beginPath(); g.ellipse(0, -3.2 * f.s, 2.6 * f.s, 3.3 * f.s, 0, 0, TAU); g.fill(); g.fillStyle = "#ffe08a"; g.beginPath(); g.ellipse(-0.8 * f.s, -4.4 * f.s, 0.8 * f.s, 1.1 * f.s, 0, 0, TAU); g.fill();
          if (f.crack) { g.strokeStyle = OUT; g.lineWidth = 0.6; g.beginPath(); g.moveTo(-2.4 * f.s, -3.6 * f.s); g.lineTo(-1, -2.4 * f.s); g.lineTo(0.4, -3.8 * f.s); g.lineTo(2.4 * f.s, -2.8 * f.s); g.stroke(); } }
        else if (f.k === "flame") { const h = f.h; g.fillStyle = f.c; g.beginPath(); g.moveTo(f.x - 2.6, f.y); g.quadraticCurveTo(f.x - 2.8, f.y - h * 0.5, f.x, f.y - h); g.quadraticCurveTo(f.x + 2.8, f.y - h * 0.5, f.x + 2.6, f.y); g.closePath(); g.fill(); g.fillStyle = f.c2 ?? "#ffd04a"; g.beginPath(); g.ellipse(f.x, f.y - h * 0.3, 1.2, h * 0.28, 0, 0, TAU); g.fill(); }
        else if (f.k === "blob") { g.fillStyle = f.c; g.beginPath(); g.ellipse(f.x, f.y, f.rx ?? f.r, f.ry ?? f.r, 0, 0, TAU); g.fill(); if (f.rim) { g.strokeStyle = f.rim; g.lineWidth = 0.7; g.stroke(); } g.fillStyle = "#ffffff"; g.globalAlpha *= 0.6; g.beginPath(); g.arc(f.x - (f.rx ?? f.r) * 0.35, f.y - (f.ry ?? f.r) * 0.35, Math.min(f.rx ?? f.r, f.ry ?? f.r) * 0.25, 0, TAU); g.fill(); }
        else if (f.k === "sweep") { const n = 18, w = f.w ?? 3, at = (q, r) => [f.x + Math.cos(f.a0 + (f.a1 - f.a0) * q) * r, f.y + Math.sin(f.a0 + (f.a1 - f.a0) * q) * r]; g.fillStyle = f.c ?? "#ffffff"; g.beginPath(); for (let i = 0; i <= n; i++) g[i ? "lineTo" : "moveTo"](...at(i / n, f.r)); for (let i = n; i >= 0; i--) { const q = i / n; g.lineTo(...at(q, f.r - w * Math.sin(Math.PI * Math.pow(q, 1.7)))); } g.closePath(); g.fill(); }
        else if (f.k === "rock") { g.fillStyle = f.c ?? "#7f8f94"; g.beginPath(); const s = f.s; g.moveTo(f.x - s, f.y); g.lineTo(f.x - s * 0.6, f.y - s * 1.2); g.lineTo(f.x + s * 0.5, f.y - s * 1.5); g.lineTo(f.x + s, f.y); g.closePath(); g.fill(); }
        g.restore();
      }
    }, { ow: 0.8 });
  }
  /** 一顆飛行物（出手 → 命中爆開）。 */
  function shot(p, u, a, b, from, c, o = {}) {
    const q = proj(u, a, b, from[0], from[1], o.x1 ?? TGT, o.y1 ?? -12, o.h ?? 0);
    if (q) FX(p, { k: o.kind ?? "orb", x: q[0], y: q[1], r: o.r ?? 2.6, c: c[0], c2: c[1], tail: o.kind ? undefined : 1, rot: u * 20 });
    if (u > b) { const k = seg(u, b, Math.min(1, b + 0.25)); if (k < 1) { FX(p, { k: "glow", x: o.x1 ?? TGT, y: o.y1 ?? -12, r: 10 + 6 * k, c: c[0], a: 1 - k }); FX(p, { k: "burst", x: o.x1 ?? TGT, y: o.y1 ?? -12, r: 4 + 4 * k, c: c[0], c2: c[1], a: 1 - k * 0.8 }); } }
  }
  /** 蓄力：在 at 聚一顆光（u 在 [a, b] 長大）。 */
  function charge(p, u, a, b, at, c, r = 2.6) { if (u >= a && u <= b) { const k = seg(u, a, b); FX(p, { k: "glow", x: at[0], y: at[1], r: 4 + 6 * k, c: c[0], a: 0.4 + 0.6 * k }); FX(p, { k: "orb", x: at[0], y: at[1], r: r * (0.4 + 0.6 * k), c: c[0], c2: c[1] }); } }
  const QUAKE = "#ffe9a8"; // 震地環：亮色（深色地面、晶傀儡旁都看得到；審查退回 #3）
  function quakeFx(p, u, a, x, c = QUAKE) { if (u < a) return; const k = seg(u, a, 1); FX(p, { k: "ring", x, rx: 8 + 34 * k, c, a: 1 - k, w: 1.8 }); FX(p, { k: "ring", x, rx: 4 + 18 * k, c, a: (1 - k) * 0.9, w: 1.8 }); FX(p, { k: "glow", x, y: -2, r: 10 * (1 - k) + 4, c, a: 0.6 * (1 - k) }); FX(p, { k: "dust", x: x - 6 - 8 * k, y: -1, r: 3 + 3 * k, a: 1 - k }); FX(p, { k: "dust", x: x + 6 + 8 * k, y: -1, r: 3 + 3 * k, a: 1 - k }); for (let i = 0; i < 3; i++) FX(p, { k: "rock", x: x - 8 + i * 8 + (i - 1) * 6 * k, y: -1 - 8 * Math.sin(Math.PI * cl(k * 1.6 - i * 0.1)), s: 1.6, a: 1 - k }); }
  const chompFx = (p, u, a, b, x, y) => { if (u >= a && u <= b) FX(p, { k: "chomp", x, y, q: seg(u, a, b), a: 1 - 0.5 * seg(u, a, b) }); };
  const slashFx = (p, u, a, b, x, y, c, r = 6) => { if (u >= a && u <= b) FX(p, { k: "slash", x, y, r, c, a: 1 - seg(u, a, b) * 0.7, len: 0.5 + seg(u, a, b) }); };

  // ============================== 身形 ==============================
  // 每款：mouth（嘴／放出點，地面座標）、kind（受擊、倒下類別）、idle、move、attacks（id → {zh, type, ms, units, fn}）、death。
  // type：melee 普攻、charge 衝鋒／撲擊、breath 吐息／噴吐、cast 遠程施放、area 範圍震地／爆發、summon 召喚、blink 位移。
  const T = { melee: "普攻", charge: "衝鋒／撲擊", breath: "吐息／噴吐", cast: "遠程施放", area: "範圍震地／爆發", summon: "召喚", blink: "位移" };
  const BODY = {};

  // ---- 犬狼 ----
  BODY.hound = { kind: "quad", mouth: [29, -24], units: "灰燼犬、霧狼",
    idle(p, u) { breathe(p, u); A(p, "tail", { rot: 0.2 * S(u, 2) }); A(p, "head", { rot: -0.05 * S(u, 1, 0.1) }); },
    move(p, u) { quadWalk(p, u, { amp: 0.3, lift: 0.32, bob: 0.9, nod: 0.06, tail: 0.18 }); },
    attacks: {
      bite: { zh: "雙咬（fangs／雙牙）", type: "melee", ms: 760, fn(p, u, e) {
        const lunge = kf(u, [[0, 0], [0.18, -2], [0.32, 6], [0.42, 4], [0.55, 7], [0.7, 6], [1, 0]]);
        R(p, { dx: lunge, rot: kf(u, [[0, 0], [0.18, -0.07], [0.32, 0.06], [0.45, -0.02], [0.55, 0.07], [1, 0]]), pivot: [-10, 0] });
        A(p, "head", { rot: kf(u, [[0, 0], [0.18, -0.35], [0.3, 0.22], [0.42, -0.3], [0.55, 0.26], [0.7, 0.1], [1, 0]]) });
        for (const g of ["FN", "FF"]) A(p, g, { kx: -0.25 * bump(u, 0.2, 0.75) }); for (const g of ["BN", "BF"]) A(p, g, { kx: 0.2 * bump(u, 0.2, 0.75) });
        chompFx(p, u, 0.28, 0.42, 37, -23); chompFx(p, u, 0.5, 0.66, 38, -21);
      } },
      maul: { zh: "撲咬拉扯（咬住後身體後坐、往後拉扯）", type: "melee", ms: 1100, fn(p, u, e) {
        const k = (pts) => kfN(u, 12, pts), f = Math.round(u * 12);
        // 拉扯：s＞0 頭往後拉，身體同一格反向往前頂、前身下壓；s＜0 被扯回，頭前伸、身體後坐回來
        const s = k([[0, 0], [4, 0], [5, 1], [6, -0.45], [7, 1], [8, -0.45], [9, 1.15], [10, 0], [12, 0]]);
        const dx = k([[0, 0], [1, -1.5], [2, -3.5], [3, 6], [4, 13], [5, 9.5], [9, 9.5], [10, 4], [11, 0], [12, 0]]) + 2.4 * s;
        const rot = k([[0, 0], [1, 0.05], [2, 0.09], [3, -0.17], [4, 0.08], [5, -0.1], [9, -0.1], [10, -0.08], [11, 0.05], [12, 0]]) + 0.08 * s;
        R(p, { dx, dy: k([[0, 0], [1, 1.5], [2, 3], [3, -6], [4, 0.6], [5, 1.6], [9, 1.6], [10, -6], [11, 2], [12, 0]]), rot, pivot: [0, -12] });
        A(p, "head", { rot: k([[0, 0], [1, 0.08], [2, 0.16], [3, -0.42], [4, 0], [5, 0.04], [9, 0.04], [10, 0.1], [12, 0]]) - 0.34 * s, dx: -4.2 * s, dy: 0.6 * s });
        const ff = k([[0, 0], [2, 0], [3, 9], [4, 15], [9, 15], [10, 6], [11, 0], [12, 0]]), bf = k([[0, 0], [2, 0], [3, -3], [4, 12], [9, 12], [10, 3], [11, 0], [12, 0]]);
        const lf = k([[2, 0], [3, 5], [4, 0], [9, 0], [10, 4], [11, 0]]), lb = k([[2, 0], [3, 3], [4, 0], [9, 0], [10, 4], [11, 0]]);
        plant(p, e, [["FN", ff, lf], ["FF", ff, lf], ["BN", bf, lb], ["BF", bf, lb]]);
        A(p, "tail", { rot: k([[0, 0], [2, 0.4], [3, -0.25], [4, 0.1], [9, 0.1], [10, -0.3], [11, 0.25], [12, 0]]) + 0.75 * s });
        if (f >= 4 && f <= 9) {
          const [mx, my] = ptOf(p, e, "head", 28, -23.4);
          FX(p, { k: "chomp", x: mx + 0.5, y: my, q: f === 4 ? 0.3 : 0.72 });
          if (f === 4) FX(p, { k: "burst", x: mx + 6.5, y: my, r: 7, c: "#ffffff", c2: "#ffe9a8" });
        }
      } },
      cast: { zh: "火種爆燃（口中引爆）", type: "cast", ms: 900, fn(p, u, e) {
        const c = elc(e.r, ELEM.fire);
        R(p, { rot: kf(u, [[0, 0], [0.35, -0.1], [0.48, 0.05], [1, 0]]), pivot: [-10, 0], dx: kf(u, [[0, 0], [0.35, -1.5], [0.48, 2], [1, 0]]) });
        A(p, "head", { rot: kf(u, [[0, 0], [0.35, -0.45], [0.48, 0.18], [1, 0]]) });
        charge(p, u, 0.08, 0.42, [29, -27], c); shot(p, u, 0.44, 0.62, [31, -25], c, { r: 2.2 });
      } },
    },
    death(p, u, e) { deathQuad(p, u, 15, { headRot: 0.45, headDy: 6 }); },
  };
  // ---- 野豬 ----
  BODY.boar = { kind: "quad", mouth: [24, -13], units: "硫煙獸",
    idle(p, u) { breathe(p, u, 0.03); A(p, "head", { rot: 0.05 * S(u, 2) }); A(p, "tail", { rot: 0.4 * Math.max(0, S(u, 2, 0.2)) }); },
    move(p, u) { quadWalk(p, u, { amp: 0.32, lift: 0.3, bob: 0.7, nod: 0.08, tail: 0.3 }); },
    attacks: {
      gore: { zh: "獠牙撞（fangs）", type: "melee", ms: 820, fn(p, u) {
        A(p, "FN", { kx: u < 0.32 ? 0.35 * S(u / 0.32, 2) : 0, sy: u < 0.32 ? 1 - 0.2 * Math.max(0, Cn(u / 0.32, 2)) : 1 });
        R(p, { dx: kf(u, [[0, 0], [0.3, -1.5], [0.5, 9], [0.62, 8], [1, 0]]), rot: kf(u, [[0, 0], [0.3, 0.06], [0.5, 0.04], [0.6, -0.1], [0.75, 0], [1, 0]]), pivot: [-8, 0] });
        A(p, "head", { rot: kf(u, [[0, 0], [0.3, 0.32], [0.5, 0.25], [0.6, -0.5], [0.78, 0], [1, 0]]) });
        for (const [g, ph] of LEGS4) A(p, g, { kx: u > 0.3 && u < 0.52 ? -0.35 * S(seg(u, 0.3, 0.52), 1, ph) : 0 });
        if (u > 0.3 && u < 0.5) FX(p, { k: "dust", x: -14, y: -1, r: 3, a: 1 - seg(u, 0.3, 0.5) });
        slashFx(p, u, 0.55, 0.7, 34, -18, "#ffffff", 5);
      } },
      uptusk: { zh: "獠牙上挑（低頭貼地、猛然上挑）", type: "melee", ms: 1000, fn(p, u, e) {
        const k = (pts) => kfN(u, 11, pts), f = Math.round(u * 11);
        const rot = k([[0, 0], [1, 0.05], [2, 0.09], [3, 0.11], [4, 0.11], [5, -0.24], [6, -0.44], [7, -0.3], [8, -0.08], [9, -0.02], [11, 0]]);
        R(p, { dx: k([[0, 0], [3, -1], [4, -1.2], [5, 2], [6, 2.4], [8, 1], [11, 0]]), rot, pivot: [-6.5, -12] });
        plant(p, e, [["FN"], ["FF"], ["BN"], ["BF"]]);
        A(p, "head", { rot: k([[0, 0], [1, 0.16], [2, 0.26], [3, 0.31], [4, 0.33], [5, 0.34], [6, 0.34], [7, 0.3], [8, 0.14], [9, 0.04], [11, 0]]) });
        A(p, "tail", { rot: k([[0, 0], [3, 0.6], [4, 0.6], [6, -0.3], [11, 0]]) });
        if (f >= 2 && f <= 4) FX(p, { k: "dust", x: 30, y: -1, r: 3.5, a: f === 4 ? 0.6 : 1 });
        if (f >= 5 && f <= 8) {
          const [tx, ty] = ptOf(p, e, "head", 21.4, -17.4), [bx, by] = ptOf(p, e, "head", 20, -11), d = Math.hypot(tx - bx, ty - by), dirx = (tx - bx) / d, diry = (ty - by) / d;
          const C = [15, -11], [a0, a1] = [[0.42, -0.35], [0.22, -0.82], [-0.25, -0.6]][Math.min(f - 5, 2)];
          if (f <= 7) FX(p, { k: "sweep", x: C[0], y: C[1], r: 21, a0, a1, w: f === 7 ? 1.6 : 3.4 });
          if (f <= 6) FX(p, { k: "burst", x: tx + dirx * 5.5 + 1.5, y: ty + diry * 5.5, r: f === 5 ? 6 : 5, c: "#ffffff", c2: "#ffe9a8" });
          if (f <= 6) for (let i = 0; i < 3; i++) FX(p, { k: "rock", x: 39 + i * 5 + (f - 5) * 2, y: -2 - [9, 15][f - 5] * (1 + i * 0.22), s: 1.6 * [1, 0.8][f - 5] });
        }
      } },
      breath: { zh: "硫煙吐息（錐形）", type: "breath", ms: 1000, fn(p, u, e) {
        breathe(p, cl(u / 0.3) * 0.5, 0.06 * (u < 0.3 ? 1 : 0));
        R(p, { dx: kf(u, [[0, 0], [0.28, -1.5], [0.4, 0.5], [0.85, 0.5], [1, 0]]) });
        A(p, "head", { rot: kf(u, [[0, 0], [0.28, -0.3], [0.4, 0.12], [0.85, 0.1], [1, 0]]) });
        if (u > 0.36 && u < 0.92) FX(p, { k: "cone", x: 25, y: -12, max: 36, spread: 9, len: seg(u, 0.36, 0.6), c: e.r.element === "poison" || !e.r.element ? "#c8d040" : elc(e.r, ELEM.poison)[0], c2: "#f2f0b0", a: 1 - seg(u, 0.8, 0.92), t: u * 12 });
      } },
    },
    death(p, u, e) { deathSide(p, u, 9, { headRot: 0.35, headDy: 2.5 }); },
  };
  // ---- 熊 ----
  BODY.bear = { kind: "quad", mouth: [26, -23], units: "石背熊",
    idle(p, u) { breathe(p, u, 0.03); A(p, "head", { rot: 0.06 * S(u, 1) }); R(p, { kx: 0.015 * S(u, 1, 0.25) }); },
    move(p, u) { quadWalk(p, u, { amp: 0.24, lift: 0.3, bob: 0.6, nod: 0.05 }); R(p, { rot: 0.025 * S(u, 2) }); },
    attacks: {
      swipe: { zh: "熊掌拍（talons）", type: "melee", ms: 820, fn(p, u) {
        R(p, { rot: kf(u, [[0, 0], [0.35, -0.3], [0.5, 0.07], [0.65, 0.04], [1, 0]]), pivot: [-8, 0], dx: kf(u, [[0, 0], [0.35, -1], [0.5, 3], [1, 0]]) });
        A(p, "FN", { rot: kf(u, [[0, 0], [0.35, -1.25], [0.5, 0.35], [0.65, 0.1], [1, 0]]) });
        A(p, "FF", { rot: kf(u, [[0, 0], [0.38, -0.7], [0.55, 0.1], [1, 0]]) });
        A(p, "head", { rot: kf(u, [[0, 0], [0.35, -0.15], [0.5, 0.2], [1, 0]]) });
        slashFx(p, u, 0.45, 0.62, 31, -9, "#ffffff", 7);
      } },
      slam: { zh: "人立重拍（人立舉掌、單掌拍地）", type: "melee", ms: 1100, fn(p, u, e) {
        const k = (pts) => kfN(u, 12, pts), f = Math.round(u * 12);
        const rot = k([[0, 0], [1, -0.26], [2, -0.52], [3, -0.68], [4, -0.74], [5, -0.74], [6, -0.42], [7, 0.13], [8, 0.13], [9, 0.09], [10, -0.05], [11, 0.03], [12, 0]]);
        R(p, { rot, dx: k([[0, 0], [2, -1], [5, -1.5], [6, 5], [7, 13], [8, 13], [9, 11], [10, 5], [11, 0], [12, 0]]), dy: k([[0, 0], [5, 0], [6, -2], [7, 1.5], [8, 1.5], [9, 1], [10, -4], [11, 1.5], [12, 0]]), pivot: [-8.5, -15] });
        // 跳步：出手時後腳跟著往前落、收招時四腳離地跳回原位，腳踩地時不滑動
        const hb = k([[0, 0], [5, 0], [6, 5], [7, 9], [9, 9], [10, 4], [11, 0], [12, 0]]), hl = k([[5, 0], [6, 2], [7, 0], [9, 0], [10, 2.5], [11, 0]]);
        plant(p, e, [["BN", hb, hl], ["BF", hb, hl]]);
        // 頭讓開：世界座標往後上，換算回頭部組（在大頭倍率內）
        const hw = k([[0, 0], [1, -3], [2, -6.5], [3, -7.5], [5, -8], [6, -5], [7, 0], [12, 0]]), hv = k([[0, 0], [2, -1.5], [3, -5], [5, -5.5], [6, -1], [7, -3], [8, -3], [9, -1.5], [10, 0], [12, 0]]), c = Math.cos(rot), s = Math.sin(rot);
        A(p, "head", { rot: k([[0, 0], [1, -0.12], [2, -0.34], [3, -0.68], [5, -0.74], [6, -0.3], [7, 0.3], [8, 0.3], [9, 0.2], [10, 0.08], [12, 0]]) - rot, dx: (hw * c + hv * s) / 1.3, dy: (-hw * s + hv * c) / 1.3 });
        if (f >= 1 && f <= 6) {
          A(p, "FN", { rot: k([[1, -0.9], [2, -1.75], [3, -2.32], [4, -2.5], [5, -2.5], [6, -1.5]]) - rot, sy: 1.08, sx: 1.06, dx: k([[1, 0.5], [3, 1.6], [6, 1.6]]), dy: k([[1, 0], [3, 1], [6, 1]]) });
          A(p, "FF", { rot: k([[1, -0.5], [3, -0.9], [5, -0.9], [6, -0.5]]) - rot, sy: 0.85 });
        } else if (f >= 7) {
          // 重拍：手臂用旋轉（不用斜切，粗細不變），掌底剛好到地面
          if (f <= 9) A(p, "FN", { rot: k([[7, -1.05], [8, -1.05], [9, -1.25]]) - rot, sy: 1.08, sx: 1.06 });
          else plant(p, e, [["FN", k([[10, 6], [11, 0], [12, 0]]), k([[10, 2.5], [11, 0]])]]);
          plant(p, e, [["FF", k([[7, 15], [9, 15], [10, 6], [11, 0], [12, 0]]), k([[9, 0], [10, 2.5], [11, 0]])]]);
        }
        // 人立時背上石板往身體壓一點（石板底邊和身體圓弧本來只有角接觸）：把身體上緣這一帶切開往內移
        if (f >= 1 && f <= 6 && e.r.traits.includes("stone_back")) { const ins = 2 * cl(-rot / 0.5); p.split = { body: [{ clip: [[-40, -60], [40, -60], [40, -26.2], [-40, -26.2]], dy: ins }, { clip: [[-40, -26.2], [40, -26.2], [40, 20], [-40, 20]] }] }; }
        if (f >= 1 && f <= 10) p.over = (ctx) => {
          const [ax, ay] = QC.RIG.bear.pivots.FN, fn = p.parts.FN;
          QC.layer(ctx, [-70, -90, 74, 18], (g) => {
            g.translate(ax + (fn.dx ?? 0), ay + (fn.dy ?? 0)); g.rotate(fn.rot ?? 0); g.transform(1, 0, fn.kx ?? 0, 1, 0, 0); g.scale(fn.sx ?? 1, fn.sy ?? 1); g.fillStyle = "#f4ecd8";
            for (const dx of [-2.6, 0, 2.6]) { g.beginPath(); g.moveTo(dx - 1, 13); g.lineTo(dx + 0.6, 16.4); g.lineTo(dx + 1, 13); g.closePath(); g.fill(); }
          }, { ow: 0.5 });
        };
        if (f >= 7 && f <= 10) {
          const q = (f - 7) / 3, px = f <= 8 ? ptOf(p, e, "FN", 11, -1)[0] : 36;
          FX(p, { k: "dust", x: px + 8 + 6 * q, y: -1, r: 3.2 + 3 * q, a: 1 - q * 0.8 }); FX(p, { k: "dust", x: px - 9 - 5 * q, y: -1, r: 2.6 + 2 * q, a: 1 - q * 0.8 });
          if (f === 7) FX(p, { k: "burst", x: px + 13, y: -7, r: 6.5, c: "#ffffff", c2: "#ffe9a8" });
          if (f <= 8) FX(p, { k: "sweep", x: px - 1, y: -18, r: 17, a0: f === 7 ? -0.6 : 0.5, a1: 1.35, w: f === 7 ? 3.2 : 1.8 });
        }
      } },
      quake: { zh: "雙掌震地（震地推倒）", type: "area", ms: 1050, fn(p, u, e) {
        const rise = kf(u, [[0, 0], [0.4, -0.5], [0.52, 0.09], [0.62, 0.05], [1, 0]]);
        R(p, { rot: rise, pivot: [-9, 0], dy: u > 0.5 && u < 0.6 ? 0.6 * Math.sign(Math.sin(u * 90)) : 0 });
        for (const g of ["FN", "FF"]) A(p, g, { rot: kf(u, [[0, 0], [0.4, -1.1], [0.52, 0.15], [0.7, 0], [1, 0]]) });
        A(p, "head", { rot: kf(u, [[0, 0], [0.4, -0.25], [0.52, 0.25], [1, 0]]) });
        quakeFx(p, u, 0.5, 24);
      } },
    },
    death(p, u, e) { deathSide(p, u, 12, { headRot: 0.45, headDy: 4 }); },
  };
  // ---- 豹 ----
  BODY.feline = { kind: "quad", mouth: [21, -14], units: "山豹",
    idle(p, u) { breathe(p, u); A(p, "tail", { rot: 0.14 * S(u, 1), kx: 0.1 * S(u, 1, 0.2) }); A(p, "head", { rot: 0.04 * S(u, 1, 0.4) }); },
    move(p, u) { R(p, { sy: 0.96 }); quadWalk(p, u, { amp: 0.34, lift: 0.32, bob: 0.45, nod: 0.03, tail: 0.12 }); },
    attacks: {
      claw: { zh: "爪擊（talons）", type: "melee", ms: 640, fn(p, u) {
        R(p, { dx: kf(u, [[0, 0], [0.25, -1.5], [0.45, 4], [0.6, 3], [1, 0]]), sy: kf(u, [[0, 1], [0.25, 0.92], [0.45, 1.03], [1, 1]]) });
        A(p, "FN", { rot: kf(u, [[0, 0], [0.28, -1.3], [0.45, 0.35], [0.6, 0.1], [1, 0]]) });
        A(p, "head", { rot: kf(u, [[0, 0], [0.25, -0.15], [0.45, 0.15], [1, 0]]) }); A(p, "tail", { rot: 0.3 * bump(u, 0.1, 0.7) });
        slashFx(p, u, 0.4, 0.58, 29, -12, "#ffffff", 6);
      } },
      upcut: { zh: "反手上撩爪（壓低身體、前爪由下往上）", type: "melee", ms: 1000, fn(p, u, e) {
        const k = (pts) => kfN(u, 11, pts), f = Math.round(u * 11);
        const rot = k([[0, 0], [1, 0.05], [2, 0.09], [3, 0.1], [4, 0.1], [5, -0.24], [6, -0.56], [7, -0.5], [8, -0.22], [9, -0.07], [10, -0.01], [11, 0]]);
        R(p, { rot, dx: k([[0, 0], [2, -1], [3, -1.5], [4, -1.5], [5, 2], [6, 5], [7, 5], [8, 3], [9, 1], [10, 0.3], [11, 0]]), dy: k([[0, 0], [1, 2.4], [2, 3.6], [3, 4.2], [4, 4.2], [5, 1.5], [6, -0.5], [7, -0.3], [8, 0], [11, 0]]), pivot: [-9.5, -12] });
        plant(p, e, [["FF"], ["BN"], ["BF"]]);
        if (f <= 4 || f >= 10) plant(p, e, [["FN"]]);
        else A(p, "FN", { rot: k([[5, -0.6], [6, -1.4], [7, -1.85], [8, -1.15], [9, -0.45]]) - rot, sy: 1.12, sx: 1.08 });
        A(p, "head", { rot: k([[0, 0], [2, 0.12], [3, 0.14], [4, 0.14], [5, 0.12], [6, -0.08], [7, -0.22], [8, 0.02], [10, 0], [11, 0]]), dy: k([[4, 0], [6, -1.5], [7, -1.5], [8, -0.4], [9, 0]]) });
        A(p, "tail", { rot: k([[0, 0], [3, -0.25], [4, -0.3], [6, 0.55], [11, 0]]) });
        if (f >= 5 && f <= 7) { const [a0, a1] = [[1.15, 0.25], [0.8, -0.5], [-0.1, -0.55]][f - 5]; FX(p, { k: "sweep", x: 9, y: -20, r: 22, a0, a1, w: f === 7 ? 1.6 : 3 }); }
      } },
      pounce: { zh: "衝鋒撲擊（衝鋒撞擊）", type: "charge", ms: 860, fn(p, u) {
        const air = seg(u, 0.3, 0.66);
        R(p, { dx: kf(u, [[0, 0], [0.3, -2], [0.66, 14], [0.76, 15], [1, 0]]), dy: u > 0.3 && u < 0.66 ? -9 * Math.sin(Math.PI * air) : 0,
          rot: kf(u, [[0, 0], [0.3, 0.04], [0.42, -0.2], [0.6, 0.18], [0.7, 0], [1, 0]]), sy: kf(u, [[0, 1], [0.3, 0.86], [0.38, 1.05], [0.66, 1], [0.72, 0.9], [0.8, 1]]), pivot: [0, -6] });
        for (const g of ["FN", "FF"]) A(p, g, { rot: -1.0 * bump(u, 0.32, 0.68) }); for (const g of ["BN", "BF"]) A(p, g, { rot: 0.8 * bump(u, 0.3, 0.66) });
        A(p, "tail", { rot: -0.3 * bump(u, 0.3, 0.7) });
        if (u > 0.66 && u < 0.86) FX(p, { k: "dust", x: 18, y: -1, r: 3.5, a: 1 - seg(u, 0.66, 0.86) });
        p.shadow = 1 - 0.3 * Math.sin(Math.PI * air);
      } },
    },
    death(p, u, e) { deathQuad(p, u, 11, { headRot: 0.3, headDy: 2.5 }); },
  };
  // ---- 蜥蜴 ----
  BODY.lizard = { kind: "quad", mouth: [27, -11], units: "餘燼蜥、寒燼蜥、殼縫餘燼蜥、熔爐母獸",
    idle(p, u) { breathe(p, u, 0.03); A(p, "tail", { rot: 0.1 * S(u, 1) }); R(p, { dy: -0.8 * Math.max(0, S(u, 2, 0.1)) }); A(p, "head", { rot: -0.06 * Math.max(0, S(u, 2, 0.1)) }); },
    move(p, u) { quadWalk(p, u, { amp: 0.5, lift: 0.35, bob: 0.3, nod: 0 }); A(p, "body", { rot: 0.05 * S(u, 1) }); A(p, "tail", { rot: -0.18 * S(u, 1, 0.1) }); A(p, "head", { rot: -0.06 * S(u, 1) }); },
    attacks: {
      bite: { zh: "咬（fangs／餘燼啃咬）", type: "melee", ms: 660, fn(p, u, e) {
        R(p, { dx: kf(u, [[0, 0], [0.28, -2], [0.45, 7], [0.6, 6], [1, 0]]) });
        A(p, "head", { rot: kf(u, [[0, 0], [0.28, -0.38], [0.42, 0.22], [0.6, 0.1], [1, 0]]) }); A(p, "tail", { rot: kf(u, [[0, 0], [0.28, 0.2], [0.45, -0.15], [1, 0]]) });
        for (const g of ["FN", "FF"]) A(p, g, { kx: -0.35 * bump(u, 0.25, 0.7) });
        if (e.r.P.mat === "magma" && u > 0.42 && u < 0.62) FX(p, { k: "burst", x: 36, y: -10, r: 3 + 3 * seg(u, 0.42, 0.62), c: elc(e.r, ELEM.fire)[0], c2: elc(e.r, ELEM.fire)[1], a: 1 - seg(u, 0.42, 0.62) });
        chompFx(p, u, 0.4, 0.58, 36, -11);
      } },
      tailover: { zh: "掄尾砸擊（尾巴從身後掄過身體砸向目標）", type: "melee", ms: 1060, fn(p, u, e) {
        const k = (pts) => kfN(u, 12, pts), f = Math.round(u * 12);
        R(p, { rot: k([[0, 0], [1, 0.03], [2, 0.08], [4, 0.16], [5, 0.2], [6, 0.26], [7, 0.24], [8, 0.2], [9, 0.14], [10, 0.08], [11, 0.03], [12, 0]]), dx: k([[0, 0], [2, -1], [4, 0], [6, 2], [8, 2], [10, 1], [12, 0]]), pivot: [-7, -5] });
        plant(p, e, [["FN"], ["FF"], ["BN"], ["BF"]]);
        const tr = k([[0, 0], [1, -0.2], [2, 0.7], [3, 1.6], [4, 2.4], [5, 2.9], [6, 3.36], [7, 3.36], [8, 3.3], [9, 2.7], [10, 1.7], [11, 0.6], [12, 0]]);
        A(p, "tail", { rot: tr, sx: k([[0, 1], [4, 1.08], [6, 1.25], [8, 1.22], [10, 1.05], [12, 1]]), dx: k([[0, 0], [3, 2], [4, 5], [5, 11], [6, 15], [8, 15], [9, 9], [10, 3], [11, 1], [12, 0]]), dy: k([[0, 0], [3, -2], [5, -4], [6, -5], [8, -5], [9, -4], [10, -2], [12, 0]]) });
        A(p, "head", { rot: k([[0, 0], [1, 0.05], [2, 0.1], [5, 0.06], [6, -0.05], [8, -0.03], [10, 0], [12, 0]]), dx: k([[0, 0], [3, -2], [4, -4], [6, -7], [8, -7], [10, -2], [12, 0]]), dy: k([[0, 0], [6, 1.6], [8, 1.6], [10, 0.3], [12, 0]]) });
        if (f >= 4 && f <= 8) {
          const [tx, ty] = ptOf(p, e, "tail", -32, -1), c = elc(e.r, ELEM.fire);
          if (f <= 6) { const [cx, cy] = ptOf(p, e, "tail", -8, -7.5); const d = Math.hypot(tx - cx, ty - cy), a1 = Math.atan2(ty - cy, tx - cx); FX(p, { k: "sweep", x: cx, y: cy, r: d, a0: a1 - 1.25, a1, w: 2.8 }); }
          if (f >= 6) { const q = (f - 6) / 2; FX(p, { k: "dust", x: tx + 7 + 3 * q, y: -1, r: 3 + 2 * q, a: 1 - 0.7 * q }); FX(p, { k: "dust", x: tx + 13 + 4 * q, y: -1, r: 2.2 + 1.6 * q, a: 1 - 0.7 * q }); }
          if (f === 6) FX(p, { k: "burst", x: tx + 4, y: Math.min(ty - 2, -7), r: 6.5, c: e.r.P.mat === "magma" ? c[0] : "#ffffff", c2: e.r.P.mat === "magma" ? c[1] : "#ffe9a8" });
        }
      } },
      cast: { zh: "寒霜（口吐冰彈；展示用寒燼蜥）", type: "cast", ms: 860, fn(p, u, e) {
        // 投射物顏色：有元素用元素色；沒元素依材質（熔岩＝火、其他＝冰）（審查退回 #7）；冰是冰晶、其他是火球
        const c = e.r.element ? elc(e.r, ELEM.ice) : e.r.P.mat === "magma" ? ELEM.fire : ELEM.ice, ice = c === ELEM.ice;
        R(p, { dx: kf(u, [[0, 0], [0.4, -1.5], [0.5, 1.5], [1, 0]]), rot: kf(u, [[0, 0], [0.4, -0.08], [0.5, 0.03], [1, 0]]), pivot: [-6, 0] });
        A(p, "head", { rot: kf(u, [[0, 0], [0.4, -0.35], [0.5, 0.15], [1, 0]]) });
        charge(p, u, 0.1, 0.45, [28, -13], c); shot(p, u, 0.46, 0.66, [30, -11], c, ice ? { kind: "shard", r: 2.4 } : { r: 2.4 });
      } },
      summon: { zh: "產下幼蜥（召喚）", type: "summon", ms: 1150, fn(p, u, e) {
        const c = elc(e.r, ELEM.fire);
        R(p, { sy: kf(u, [[0, 1], [0.35, 0.9], [0.45, 1.06], [0.6, 1], [1, 1]]), rot: kf(u, [[0, 0], [0.35, 0.05], [0.45, -0.06], [0.6, 0], [1, 0]]), pivot: [0, 0] });
        A(p, "tail", { rot: kf(u, [[0, 0], [0.35, 0.45], [0.5, -0.1], [0.7, 0], [1, 0]]) });
        const q = proj(u, 0.42, 0.68, -6, -16, 34, 0, 18);
        if (q) FX(p, { k: "egg", x: q[0], y: q[1], s: 1.3, c: c[0], rot: u * 8 });
        if (u >= 0.68) { const k = seg(u, 0.68, 1), wob = u < 0.85 ? 0.25 * Math.sin(u * 70) : 0; FX(p, { k: "egg", x: 34, y: 0, s: 1.3, c: c[0], rot: wob, crack: u > 0.8 });
          if (u > 0.86) { FX(p, { k: "glow", x: 34, y: -4, r: 10, c: c[1], a: 1 - seg(u, 0.86, 1) }); FX(p, { k: "burst", x: 34, y: -4, r: 5, c: c[0], c2: c[1], a: 1 - seg(u, 0.86, 1) }); } }
      } },
    },
    death(p, u, e) { deathQuad(p, u, 8, { headRot: 0.3, headDy: 3 }); const k = sm(seg(u, 0.3, 0.8)); A(p, "tail", { rot: 0.4 * k }); for (const g of ["FN", "FF"]) A(p, g, { kx: -0.9 * k, sy: 1.5 }); for (const g of ["BN", "BF"]) A(p, g, { kx: 0.9 * k, sy: 1.5 }); A(p, "body", { sy: 1 - 0.12 * k }); },
  };
  // ---- 龜殼 ----
  BODY.shell = { kind: "shell", mouth: [21, -8], units: "噴岩龜",
    idle(p, u) { breathe(p, u, 0.02); A(p, "head", { dx: -0.8 * (0.5 - 0.5 * Cn(u, 1)), rot: 0.06 * S(u, 2) }); },
    move(p, u) { quadWalk(p, u, { amp: 0.28, lift: 0.3, bob: 0.4, nod: 0.04 }); R(p, { rot: 0.02 * S(u, 2) }); },
    attacks: {
      lob: { zh: "背火山拋射（fire_staff）", type: "cast", ms: 950, fn(p, u, e) {
        const c = elc(e.r, ELEM.fire);
        R(p, { sy: kf(u, [[0, 1], [0.3, 0.93], [0.4, 1.05], [0.55, 1], [1, 1]]) });
        A(p, "head", { dx: kf(u, [[0, 0], [0.3, -2], [0.6, 0], [1, 0]]) }); quadLegsTuck(p, 0.2 * bump(u, 0, 0.45));
        if (u > 0.36 && u < 0.5) FX(p, { k: "burst", x: -2, y: -30, r: 4 + 3 * seg(u, 0.36, 0.5), c: c[0], c2: c[1], a: 1 - seg(u, 0.36, 0.5) });
        shot(p, u, 0.38, 0.78, [-2, -30], c, { h: 26, y1: -2, r: 3 });
      } },
      breath: { zh: "火牆（噴吐）", type: "breath", ms: 1050, fn(p, u, e) {
        const c = elc(e.r, ELEM.fire);
        A(p, "head", { dx: kf(u, [[0, 0], [0.25, -1.5], [0.35, 2], [0.85, 2], [1, 0]]), rot: kf(u, [[0, 0], [0.25, -0.2], [0.35, 0.1], [0.85, 0.1], [1, 0]]) });
        R(p, { dx: kf(u, [[0, 0], [0.35, -1], [0.85, -1], [1, 0]]) });
        if (u > 0.32 && u < 0.7) FX(p, { k: "cone", x: 22, y: -7, max: 22, spread: 5, len: seg(u, 0.32, 0.5), c: c[0], c2: c[1], a: 1 - seg(u, 0.6, 0.7), t: u * 12 });
        if (u > 0.5) for (let i = 0; i < 4; i++) { const k = seg(u, 0.5 + i * 0.05, 0.62 + i * 0.05); if (k > 0) FX(p, { k: "flame", x: 34 + i * 6, y: 0, h: (9 + 3 * Math.sin(u * 30 + i)) * k * (1 - seg(u, 0.88, 1)), c: c[0], c2: c[1] }); }
      } },
    },
    death(p, u, e) { p.flash = u < 0.12 ? 0.7 : 0; const k = sm(seg(u, 0.15, 0.6)); A(p, "head", { dx: -3 * k, sx: 1 - 0.5 * k, rot: 0.3 * k }); quadLegsTuck(p, 0.75 * k); R(p, { dy: 6.5 * k, rot: 0.08 * sm(seg(u, 0.55, 0.9)), pivot: [10, 0] }); p.shadow = 1 - 0.2 * k; },
  };
  // ---- 甲蟲 ----
  const BT_TRI = [["N0", "N2", "F1"], ["F0", "F2", "N1"]];
  BODY.beetle = { kind: "crawler", mouth: [22, -14], units: "熔岩甲蟲、熔核領主",
    idle(p, u) { breathe(p, u, 0.02); A(p, "head", { rot: 0.06 * S(u, 2) }); A(p, "N2", { kx: -0.2 * Math.max(0, S(u, 1, 0.3)) }); },
    move(p, u) { hexWalk(p, u, BT_TRI, { amp: 0.5, lift: 0.35, bob: 0.4 }); A(p, "head", { rot: 0.04 * S(u, 2) }); },
    attacks: {
      horn: { zh: "角頂（stone_fist）", type: "melee", ms: 680, fn(p, u) {
        R(p, { dx: kf(u, [[0, 0], [0.3, -1], [0.48, 5], [0.62, 4], [1, 0]]), rot: kf(u, [[0, 0], [0.3, 0.1], [0.48, 0.06], [0.58, -0.14], [0.75, 0], [1, 0]]), pivot: [14, 0] });
        A(p, "head", { rot: kf(u, [[0, 0], [0.3, 0.28], [0.48, 0.15], [0.58, -0.55], [0.8, 0], [1, 0]]) });
        slashFx(p, u, 0.52, 0.68, 30, -20, "#ffffff", 5);
      } },
      ram: { zh: "破城衝撞（衝鋒）", type: "charge", ms: 880, fn(p, u) {
        R(p, { dx: kf(u, [[0, 0], [0.3, -3], [0.55, 14], [0.62, 12.5], [1, 0]]), rot: kf(u, [[0, 0], [0.3, 0.05], [0.55, 0.08], [0.62, -0.06], [0.8, 0], [1, 0]]), pivot: [12, 0] });
        A(p, "head", { rot: kf(u, [[0, 0], [0.3, 0.2], [0.55, 0.2], [0.62, -0.25], [0.85, 0], [1, 0]]) });
        if (u < 0.6) hexWalk(p, (u * 3) % 1, BT_TRI, { amp: 0.5, lift: 0.35, bob: 0 });
        if (u > 0.5 && u < 0.75) { FX(p, { k: "burst", x: 40, y: -10, r: 5 + 3 * seg(u, 0.5, 0.75), c: "#ffffff", c2: "#ffe08a", a: 1 - seg(u, 0.55, 0.75) }); FX(p, { k: "dust", x: 4, y: -1, r: 3.5, a: 1 - seg(u, 0.5, 0.75) }); }
      } },
      burst: { zh: "熔流潰堤（殼爆發）", type: "area", ms: 950, fn(p, u, e) {
        const c = elc(e.r, ELEM.fire);
        R(p, { sy: kf(u, [[0, 1], [0.35, 0.88], [0.45, 1.08], [0.6, 1], [1, 1]]), sx: kf(u, [[0, 1], [0.35, 1.04], [0.45, 1.06], [0.6, 1], [1, 1]]), dy: u < 0.35 ? 0.4 * Math.sign(Math.sin(u * 80)) * seg(u, 0.1, 0.35) : 0 });
        quadLegsTuck(p, 0); for (const g of ["N0", "N1", "N2", "F0", "F1", "F2"]) A(p, g, { sy: 1 - 0.3 * bump(u, 0.1, 0.5) });
        p.flash = u > 0.2 && u < 0.42 ? 0.35 : 0; p.flashColor = c[0];
        if (u > 0.4) { const k = seg(u, 0.4, 1); FX(p, { k: "ring", x: 0, rx: 10 + 26 * k, c: c[0], a: 1 - k }); FX(p, { k: "glow", x: 0, y: -12, r: 18 + 8 * k, c: c[0], a: (1 - k) * 0.8 });
          for (let i = 0; i < 5; i++) { const an = -Math.PI * (0.15 + 0.7 * (i / 4)), d = 8 + 20 * k; FX(p, { k: "orb", x: Math.cos(an) * d, y: -12 + Math.sin(an) * d * 0.8 + 18 * k * k, r: 1.6, c: c[0], c2: c[1], a: 1 - k }); } }
      } },
    },
    death(p, u, e) { // 翻肚：彈起沿長軸翻面，腳朝上亂踢後停
      p.flash = u < 0.12 ? 0.7 : 0; const f = sm(seg(u, 0.15, 0.55));
      R(p, { sy: flipSy(f), dy: -7 * Math.sin(Math.PI * seg(u, 0.15, 0.55)), pivot: [0, -10] }); A(p, "spikes", { sy: 1 - 0.85 * f }); // 沿身體長軸翻（頭仍朝前）；背刺壓平，不插地
      const kick = u > 0.55 ? Math.sin(u * 46) * (1 - seg(u, 0.55, 0.92)) : 0;
      ["N0", "N1", "N2", "F0", "F1", "F2"].forEach((g, i) => A(p, g, { kx: 0.4 * kick * (i % 2 ? 1 : -1), sy: 1 - 0.25 * f }));
      A(p, "head", { rot: 0.2 * f }); p.shadow = 1 - 0.1 * f;
    },
  };
  // ---- 蜘蛛 ----
  const SP_TETRA = [["N0", "F1", "N2", "F3"], ["F0", "N1", "F2", "N3"]];
  BODY.spider = { kind: "crawler", mouth: [11, -6], units: "（目前沒有單位）",
    idle(p, u) { A(p, "abd", { sy: 1 + 0.04 * S(u, 1), sx: 1 + 0.02 * S(u, 1) }); ["N0", "N1", "N2", "N3"].forEach((g, i) => A(p, g, { rot: 0.05 * S(u, 1, i * 0.25) })); A(p, "head", { rot: 0.04 * S(u, 2) }); },
    move(p, u) { hexWalk(p, u, SP_TETRA, { amp: 0.32, lift: 2.2, bob: 0.6, rot: true }); A(p, "abd", { rot: 0.05 * S(u, 2) }); },
    attacks: {
      bite: { zh: "毒咬（前腳舉起撲咬）", type: "melee", ms: 720, fn(p, u, e) {
        R(p, { rot: kf(u, [[0, 0], [0.35, -0.22], [0.5, 0.1], [0.65, 0.05], [1, 0]]), pivot: [-14, 0], dx: kf(u, [[0, 0], [0.35, -1], [0.5, 6], [0.62, 5], [1, 0]]) });
        for (const g of ["N3", "F3"]) A(p, g, { rot: kf(u, [[0, 0], [0.35, -0.9], [0.5, 0.25], [1, 0]]) }); for (const g of ["N2", "F2"]) A(p, g, { rot: kf(u, [[0, 0], [0.35, -0.5], [0.5, 0.15], [1, 0]]) });
        A(p, "head", { dx: 2 * bump(u, 0.4, 0.65), rot: 0.15 * bump(u, 0.4, 0.65) });
        if (u > 0.45 && u < 0.7) FX(p, { k: "burst", x: 20, y: -6, r: 3 + 2 * seg(u, 0.45, 0.7), c: "#7ddc3a", c2: "#d6f59a", a: 1 - seg(u, 0.45, 0.7) });
      } },
    },
    death(p, u, e) { p.flash = u < 0.12 ? 0.7 : 0; const f = sm(seg(u, 0.15, 0.5)), c = sm(seg(u, 0.45, 0.9));
      R(p, { sy: flipSy(f), dy: -6 * Math.sin(Math.PI * seg(u, 0.15, 0.5)), pivot: [-2, -10.5] }); A(p, "spikes", { sy: 1 - 0.85 * f }); // 背上晶刺壓平，不插進地面
      ["N0", "N1", "N2", "N3"].forEach((g) => A(p, g, { rot: -0.7 * c, sy: 1 - 0.3 * c })); ["F0", "F1", "F2", "F3"].forEach((g) => A(p, g, { rot: 0.7 * c, sy: 1 - 0.3 * c })); },
  };
  // ---- 蛇 ----
  function neck(p, kx, rot = 0, extra = 0) { A(p, "neck", { kx }); A(p, "head", { dx: -18 * kx + extra, rot }); } // 頸部斜切 kx：頸頂（y −24）位移 −18·kx，頭跟著
  BODY.serpent = { kind: "serpent", mouth: [19, -25], units: "（目前沒有單位）",
    idle(p, u) { neck(p, 0.07 * S(u, 1), -0.05 * S(u, 1)); A(p, "coil", { sy: 1 + 0.03 * S(u, 1, 0.25) }); },
    move(p, u) { A(p, "coil", { kx: 0.18 * S(u, 1), sx: 1 + 0.06 * S(u, 2) }); neck(p, -0.1 * S(u, 1, 0.2), 0.05 * S(u, 1, 0.4)); R(p, { dx: 0.8 * S(u, 2) }); },
    attacks: {
      strike: { zh: "突咬", type: "melee", ms: 620, fn(p, u) {
        const k = kf(u, [[0, 0], [0.3, 0.32], [0.45, -0.48], [0.58, -0.42], [1, 0]]);
        neck(p, k, kf(u, [[0, 0], [0.3, -0.3], [0.45, 0.2], [1, 0]])); A(p, "coil", { kx: 0.1 * bump(u, 0.35, 0.7) }); R(p, { dx: 2 * bump(u, 0.35, 0.7) });
        chompFx(p, u, 0.4, 0.58, 34, -24);
      } },
    },
    death(p, u, e) { p.flash = u < 0.12 ? 0.7 : 0; const k = sm(seg(u, 0.2, 0.8)); A(p, "neck", { sy: 1 - 0.75 * k, kx: -0.3 * k }); A(p, "head", { dx: 6 * k, dy: 16 * k, rot: 0.25 * k }); A(p, "coil", { sy: 1 - 0.15 * k }); },
  };
  // ---- 軟泥 ----
  BODY.ooze = { kind: "ooze", mouth: [8, -10], units: "熔核蛞蝓",
    idle(p, u) { R(p, { sx: 1 + 0.04 * S(u, 1), sy: 1 - 0.04 * S(u, 1), kx: 0.04 * S(u, 1, 0.25) }); A(p, "face", { dy: 0.5 * S(u, 1) }); },
    move(p, u) { R(p, { kx: 0.12 * S(u, 1), sx: 1 + 0.1 * S(u, 1, 0.25), sy: 1 - 0.09 * S(u, 1, 0.25), dx: 1.2 * S(u, 1, 0.1) }); A(p, "face", { dx: 0.8 * S(u, 1) }); },
    attacks: {
      slam: { zh: "彈跳壓（stone_fist）", type: "melee", ms: 820, fn(p, u, e) {
        const air = seg(u, 0.3, 0.56);
        R(p, { sy: kf(u, [[0, 1], [0.28, 0.7], [0.36, 1.25], [0.55, 1.1], [0.62, 0.6], [0.78, 1.08], [0.9, 0.97], [1, 1]]), sx: kf(u, [[0, 1], [0.28, 1.25], [0.36, 0.85], [0.55, 0.92], [0.62, 1.4], [0.78, 0.95], [1, 1]]),
          dx: kf(u, [[0, 0], [0.3, 0], [0.58, 8], [0.75, 8], [1, 0]]), dy: u > 0.3 && u < 0.58 ? -12 * Math.sin(Math.PI * seg(u, 0.3, 0.58)) : 0 });
        A(p, "face", { dy: kf(u, [[0, 0], [0.28, 2], [0.36, -2], [0.62, 3], [1, 0]]) });
        if (u > 0.58 && u < 0.85) { const k = seg(u, 0.58, 0.85); FX(p, { k: "blob", x: 8 - 16 - 4 * k, y: -1, rx: 2.4, ry: 1.4, c: e.r.P.base, a: 1 - k }); FX(p, { k: "blob", x: 8 + 16 + 4 * k, y: -1, rx: 2.4, ry: 1.4, c: e.r.P.base, a: 1 - k }); FX(p, { k: "dust", x: 8, y: -1, r: 5, a: 1 - k }); }
        p.shadow = 1 - 0.35 * Math.sin(Math.PI * air);
      } },
      spit: { zh: "燈油瓶（拋吐油團）", type: "cast", ms: 900, fn(p, u, e) {
        R(p, { sy: kf(u, [[0, 1], [0.32, 0.8], [0.42, 1.18], [0.55, 0.96], [0.7, 1], [1, 1]]), sx: kf(u, [[0, 1], [0.32, 1.15], [0.42, 0.88], [0.55, 1.03], [1, 1]]), kx: kf(u, [[0, 0], [0.32, -0.08], [0.42, 0.12], [0.6, 0], [1, 0]]) });
        A(p, "face", { dy: kf(u, [[0, 0], [0.32, 1.5], [0.42, -2], [0.7, 0], [1, 0]]) });
        // 油團亮一階＋亮邊；落地爆開濺油、油灘亮邊；有元素時換元素色（審查退回 #8）
        const oc = e.r.element ? elc(e.r, ELEM.fire)[0] : "#6a5640", rim = e.r.element ? elc(e.r, ELEM.fire)[1] : "#d8c08a";
        const q = proj(u, 0.4, 0.74, 8, -16, 46, -2, 22);
        if (q) FX(p, { k: "blob", x: q[0], y: q[1], r: 3.8, c: oc, rim });
        if (u > 0.74) { const k = seg(u, 0.74, 1); FX(p, { k: "blob", x: 46, y: 0, rx: 5 + 7 * k, ry: 1.6 + 0.6 * k, c: oc, rim, a: 1 - 0.2 * k });
          if (k < 0.7) FX(p, { k: "burst", x: 46, y: -3, r: 4 + 4 * k, c: oc, c2: rim, a: 1 - k / 0.7 });
          for (let i = 0; i < 4; i++) { const dx = [-1, -0.4, 0.5, 1][i]; FX(p, { k: "blob", x: 46 + dx * (4 + 9 * k), y: Math.min(-0.5, -2 - (7 - 2 * Math.abs(dx)) * Math.sin(Math.PI * k)), r: 1.3, c: oc, rim, a: 1 - 0.6 * k }); } }
      } },
    },
    death(p, u, e) { p.flash = u < 0.12 ? 0.7 : 0; const k = sm(seg(u, 0.1, 0.8)); R(p, { sy: 1 - 0.68 * k + 0.08 * Math.sin(u * 30) * (1 - k), sx: 1 + 0.55 * k }); A(p, "face", { dy: 5 * k, a: 1 - 0.7 * k }); p.alpha = 1 - 0.3 * sm(seg(u, 0.5, 1)); },
  };
  // ---- 傀儡 ----
  BODY.golem = { kind: "golem", mouth: [-1, -29], units: "晶傀儡、碎晶傀儡、焦岩巨像",
    idle(p, u) { breathe(p, u, 0.015); A(p, "armN", { rot: -0.04 * S(u, 1) }); A(p, "armF", { rot: 0.04 * S(u, 1) }); A(p, "head", { rot: 0.04 * S(u, 1, 0.3) }); },
    move(p, u) {
      [["legN", 0], ["legF", 0.5]].forEach(([g, ph]) => A(p, g, { kx: -0.28 * S(u, 1, ph), sy: 1 - 0.18 * Math.max(0, Cn(u, 1, ph)) }));
      R(p, { dy: -0.9 * Math.abs(Cn(u, 1, 0.25)), rot: 0.03 * S(u, 1) }); // 每步落地「咚」
      A(p, "armN", { rot: 0.22 * S(u, 1, 0.5) }); A(p, "armF", { rot: 0.22 * S(u, 1) }); A(p, "head", { rot: 0.03 * S(u, 2) });
    },
    attacks: {
      smash: { zh: "拳砸（stone_fist／碎岩擊）", type: "melee", ms: 920, fn(p, u, e) {
        A(p, "armN", { rot: kf(u, [[0, 0], [0.4, -2.7], [0.55, -0.75], [0.7, -0.7], [1, 0]]) });
        A(p, "armF", { rot: kf(u, [[0, 0], [0.4, 0.4], [0.55, -0.2], [1, 0]]) });
        R(p, { rot: kf(u, [[0, 0], [0.4, -0.09], [0.55, 0.13], [0.7, 0.1], [1, 0]]), pivot: [-3, 0], dx: kf(u, [[0, 0], [0.4, -1], [0.55, 3], [1, 0]]), dy: u > 0.55 && u < 0.65 ? 0.6 * Math.sign(Math.sin(u * 120)) : 0 });
        A(p, "head", { rot: kf(u, [[0, 0], [0.4, -0.12], [0.55, 0.15], [1, 0]]) });
        if (u > 0.53) { const k = seg(u, 0.53, 0.85); if (k < 1) { FX(p, { k: "burst", x: 27, y: -4, r: 4 + 3 * k, c: "#ffffff", c2: "#e8dcc8", a: 1 - k }); FX(p, { k: "dust", x: 27, y: -1, r: 4 + 2 * k, a: 1 - k }); } }
      } },
      quake: { zh: "雙拳震地（震地波）", type: "area", ms: 1100, fn(p, u, e) {
        // 雙臂一起舉過頭、一起砸地（和單拳砸分開：拳砸是一隻手從後上方砸前方；審查退回 #3）
        A(p, "armN", { rot: kf(u, [[0, 0], [0.42, -3.05], [0.55, -0.95], [0.75, -0.9], [1, 0]]) });
        // 遠側手臂：舉起時支點留在肩膀（不平移，接在身體上）；砸下時肩膀往前滑進軀幹裡（支點被軀幹蓋住、看不到接縫），拳頭落在近側拳頭左下方（複查退回）
        A(p, "armF", { rot: kf(u, [[0, 0], [0.42, -3.3], [0.55, -0.85], [0.75, -0.8], [1, 0]]), dx: kf(u, [[0, 0], [0.42, 0], [0.55, 16], [0.75, 16], [1, 0]]) });
        R(p, { rot: kf(u, [[0, 0], [0.42, -0.14], [0.55, 0.2], [0.75, 0.16], [1, 0]]), pivot: [-3, 0], dy: kf(u, [[0, 0], [0.42, -2.5], [0.55, 1], [0.75, 0.6], [1, 0]]) + (u > 0.55 && u < 0.68 ? 0.7 * Math.sign(Math.sin(u * 120)) : 0) });
        A(p, "head", { rot: kf(u, [[0, 0], [0.42, -0.15], [0.55, 0.2], [1, 0]]) });
        if (u > 0.55) { const k = seg(u, 0.55, 1); for (let i = 0; i < 4; i++) { const q = cl(k * 1.6 - i * 0.18); if (q > 0 && q < 1) FX(p, { k: "rock", x: 24 + i * 10, y: 0, s: 2.6 * Math.sin(Math.PI * q) + 0.5, c: e.r.P.mat === "crystal" ? "#b8a8ff" : "#8a847e" }); }
          FX(p, { k: "dust", x: 24 + 30 * k, y: -1, r: 3 + 2 * k, a: 1 - k }); }
        quakeFx(p, u, 0.55, 22);
      } },
      cast: { zh: "核心聚雷（從胸口放出）", type: "cast", ms: 920, fn(p, u, e) {
        const c = e.r.element ? elc(e.r, ELEM.lightning) : ELEM.lightning;
        A(p, "armN", { rot: kf(u, [[0, 0], [0.4, 0.7], [0.55, -0.9], [0.8, -0.6], [1, 0]]) }); A(p, "armF", { rot: kf(u, [[0, 0], [0.4, 0.6], [0.55, -0.3], [1, 0]]) });
        R(p, { rot: kf(u, [[0, 0], [0.4, -0.06], [0.55, 0.04], [1, 0]]), pivot: [0, 0] });
        charge(p, u, 0.1, 0.46, [1, -29], c, 3.2);
        if (u > 0.48 && u < 0.72) { FX(p, { k: "bolt", x0: 3, y0: -29, x1: TGT, y1: -14, c: c[0], amp: 1 + 0.6 * Math.sin(u * 60) }); FX(p, { k: "glow", x: TGT, y: -14, r: 10, c: c[0], a: 1 - seg(u, 0.48, 0.72) * 0.6 }); }
      } },
    },
    death(p, u, e) { // 崩塌（QK-4 檢查 §3-2）：晃 → 軀幹沿裂縫斷成 3 塊落地、頭往前滾到一旁、兩隻手臂往兩邊散落、腿垮成殘樁
      p.flash = u < 0.12 ? 0.7 : 0; const sh = u < 0.25 ? 0.6 * Math.sign(Math.sin(u * 120)) : 0, k = sm(seg(u, 0.22, 0.72)), k2 = sm(seg(u, 0.3, 0.8));
      R(p, { dx: sh });
      // 裂縫（軀幹 y −40～−16）：上塊＝肩與背刺；下面左右兩塊；三塊各自掉落、翻轉
      const TOP = [[-30, -70], [30, -70], [30, -31], [7, -33], [2, -29.5], [-4, -32.5], [-30, -30]];
      const LEFT = [[-30, -30], [-4, -32.5], [2, -29.5], [0.5, -24], [-2.5, -20], [-0.5, -8], [-30, -8]];
      const RIGHT = [[2, -29.5], [7, -33], [30, -31], [30, -8], [-0.5, -8], [-2.5, -20], [0.5, -24]];
      p.split = { body: [
        { clip: LEFT, pivot: [-6, -16], dx: -3 * k, dy: 13 * k, rot: -0.35 * k },
        { clip: RIGHT, pivot: [6, -16], dx: 5 * k, dy: 13 * k, rot: 0.5 * k },
        { clip: TOP, pivot: [-2, -31], dx: -1 * k2 + 0.5 * bump(u, 0.7, 0.85), dy: 24 * k2 - 2 * bump(u, 0.78, 0.9), rot: -0.25 * k2 },
      ] };
      const roll = sm(seg(u, 0.25, 0.95));
      A(p, "head", { dy: 27 * sm(seg(u, 0.25, 0.6)) - 4 * bump(u, 0.6, 0.75), dx: -15 * roll, rot: -(1.6 + TAU) * roll }); // 頭往後滾到一旁、側躺（滾一圈多）
      A(p, "armN", { dy: 30 * sm(seg(u, 0.3, 0.7)), dx: 0, rot: -1.5 * sm(seg(u, 0.3, 0.78)) }); // 近側手臂往前平躺在地上
      A(p, "armF", { dy: 17 * sm(seg(u, 0.28, 0.68)), dx: -3 * k, rot: 0.55 * k }); // 遠側手臂斜靠在碎塊後面
      for (const g of ["legN", "legF"]) A(p, g, { sy: 1 - 0.6 * k });
      A(p, "legN", { rot: 0.25 * k }); A(p, "legF", { rot: -0.25 * k });
      if (u > 0.62 && u < 1) { FX(p, { k: "dust", x: -2, y: -1, r: 6, a: 1 - seg(u, 0.62, 1) }); FX(p, { k: "dust", x: 24, y: -1, r: 3.5, a: 1 - seg(u, 0.7, 1) }); }
    },
  };
  // ---- 晶靈 ----
  const ORB_HOME = [[-11, -5], [10, -8], [3, 9]];
  BODY.wisp = { kind: "wisp", mouth: [0, -20], units: "（灰燼之心另有頭目畫法）",
    idle(p, u) { R(p, { dy: -2 * S(u, 1) }); A(p, "core", { sx: 1 + 0.04 * S(u, 2), sy: 1 + 0.04 * S(u, 2) }); ORB_HOME.forEach((_, i) => A(p, `orb${i}`, { dx: 2 * Cn(u, 1, i / 3), dy: 1.4 * S(u, 1, i / 3) })); },
    move(p, u) { R(p, { dy: -1.5 - 1.5 * S(u, 1), rot: 0.1 }); ORB_HOME.forEach((_, i) => A(p, `orb${i}`, { dx: -2.5 + 1.5 * Cn(u, 1, i / 3), dy: 1.2 * S(u, 1, i / 3) })); },
    attacks: {
      shards: { zh: "晶刺射出（從核心）", type: "cast", ms: 880, fn(p, u, e) {
        R(p, { dy: -1.5 * S(u, 1) });
        ORB_HOME.forEach(([hx, hy], i) => {
          const fx = 13 - hx, fy = -3 + (i - 1) * 4 - hy, g = seg(u, 0.05 + i * 0.05, 0.35 + i * 0.05), fly = seg(u, 0.42 + i * 0.06, 0.62 + i * 0.06), back = seg(u, 0.78, 1);
          if (fly >= 1) A(p, `orb${i}`, { a: back, sx: 0.4 + 0.6 * back, sy: 0.4 + 0.6 * back }); // 命中後回到原位重新長出來
          else A(p, `orb${i}`, { dx: fx * sm(g) + (TGT - 13) * fly, dy: fy * sm(g), rot: 0.6 * g + 0.97 * (fly > 0 ? 1 : 0) });
          if (u > 0.62 + i * 0.06 && u < 0.78 + i * 0.06) FX(p, { k: "burst", x: TGT, y: -20 + (i - 1) * 4, r: 4, c: e.r.P.base, c2: "#ffffff", a: 1 - seg(u, 0.62 + i * 0.06, 0.78 + i * 0.06) });
        });
        A(p, "core", { sx: 1 + 0.15 * bump(u, 0.3, 0.55), sy: 1 + 0.15 * bump(u, 0.3, 0.55) });
      } },
      pulse: { zh: "晶脈衝（範圍爆發）", type: "area", ms: 940, fn(p, u, e) {
        const k = kf(u, [[0, 0], [0.35, -0.25], [0.48, 0.3], [0.7, 0.05], [1, 0]]);
        A(p, "core", { sx: 1 + k, sy: 1 + k }); ORB_HOME.forEach(([hx, hy], i) => A(p, `orb${i}`, { dx: hx * k * 2.2, dy: hy * k * 2.2 }));
        R(p, { dy: -1 * S(u, 1) }); p.flash = u > 0.42 && u < 0.52 ? 0.5 : 0; p.flashColor = e.r.P.accent ?? "#ffffff";
        if (u > 0.45) { const q = seg(u, 0.45, 1); FX(p, { k: "ring", x: 0, rx: 8 + 30 * q, c: e.r.P.base, a: 1 - q }); FX(p, { k: "glow", x: 0, y: -20, r: 16 + 10 * q, c: e.r.P.base, a: 1 - q }); }
      } },
    },
    death(p, u, e) { // 碎裂：閃白、核心縮掉，晶片往外噴再落地
      p.flash = u < 0.2 ? 0.9 : 0; const k = seg(u, 0.18, 0.4);
      A(p, "core", { sx: 1 - 0.85 * sm(k), sy: 1 - 0.85 * sm(k), a: 1 - sm(k), rot: 0.6 * k });
      ORB_HOME.forEach(([hx, hy], i) => { const f = seg(u, 0.2, 0.75); A(p, `orb${i}`, { dx: hx * 0.8 * f, dy: (20 - hy - 2.4) * f * f - 8 * Math.sin(Math.PI * f) * (1 - f), rot: (i - 1) * 2 * f + 1.57 * sm(f) }); });
      R(p, { dy: 0 }); p.shadow = 1 - 0.6 * sm(seg(u, 0.2, 0.6));
      if (u > 0.2) for (let i = 0; i < 6; i++) { const an = -Math.PI * (0.1 + 0.8 * (i / 5)), f = seg(u, 0.2, 0.8), d = 4 + 16 * f; FX(p, { k: "shard", x: Math.cos(an) * d * (i % 2 ? 1 : 0.7), y: Math.min(-1.5, -20 + Math.sin(an) * d * 0.6 + 26 * f * f), rot: an + f * 4 * (i % 2 ? 1 : -1) + (f >= 1 ? 0 : 0), s: 1.8, c: QC.light(e.r.P.base, 0.2) }); }
    },
  };
  // ---- 霧魅 ----
  BODY.wraith = { kind: "wraith", mouth: [2, -42], units: "霧魅、熔晶魅",
    idle(p, u) { R(p, { dy: -1.5 * S(u, 1) }); A(p, "body", { kx: 0.06 * S(u, 1, 0.2) }); A(p, "armN", { rot: 0.1 * S(u, 1, 0.1) }); A(p, "armB", { rot: 0.1 * S(u, 1, 0.35) }); A(p, "head", { rot: 0.05 * S(u, 1, 0.5) }); },
    move(p, u) { R(p, { dy: -1.5 - 1 * S(u, 2), rot: 0.08 }); A(p, "body", { kx: 0.12 + 0.05 * S(u, 1) }); A(p, "armN", { rot: 0.35 + 0.08 * S(u, 1) }); A(p, "armB", { rot: 0.4 + 0.08 * S(u, 1, 0.3) }); },
    attacks: {
      claw: { zh: "影刃爪（shade_blades）", type: "melee", ms: 680, fn(p, u, e) {
        R(p, { dx: kf(u, [[0, 0], [0.3, -2], [0.5, 7], [0.65, 6], [1, 0]]), rot: kf(u, [[0, 0], [0.3, -0.06], [0.5, 0.14], [1, 0]]), pivot: [0, -20] });
        A(p, "armN", { rot: kf(u, [[0, 0], [0.3, 1.0], [0.5, -1.5], [0.65, -1.2], [1, 0]]) }); A(p, "armB", { rot: kf(u, [[0, 0], [0.35, 0.9], [0.58, -1.2], [0.72, -1], [1, 0]]) });
        A(p, "body", { kx: kf(u, [[0, 0], [0.3, -0.1], [0.5, 0.2], [1, 0]]) });
        slashFx(p, u, 0.45, 0.65, 30, -26, e.r.element ? elc(e.r, ELEM.shadow)[0] : "#c8a8f0", 7);
      } },
      blink: { zh: "閃現（淡出→淡入）", type: "blink", ms: 900, fn(p, u, e) {
        const out = sm(seg(u, 0.05, 0.38)), inn = sm(seg(u, 0.58, 0.9)), v = out * (1 - inn);
        R(p, { sx: 1 - 0.6 * v, sy: 1 + 0.35 * v, dy: -4 * v }); p.alpha = 1 - v;
        for (let i = 0; i < 4; i++) { const an = (i / 4) * TAU + u * 6, q = u < 0.5 ? seg(u, 0.1, 0.45) : seg(u, 0.55, 0.9); FX(p, { k: "puff", x: Math.cos(an) * (6 + 6 * q), y: -20 + Math.sin(an) * 9, r: 3.6 * (1 - q * 0.5), c: e.r.P.base, a: Math.sin(Math.PI * q) }); }
      } },
      gaze: { zh: "威懾凝視（眼放恐懼波）", type: "cast", ms: 900, fn(p, u, e) {
        const c = e.r.element ? elc(e.r, ELEM.shadow) : ELEM.shadow;
        R(p, { dx: kf(u, [[0, 0], [0.35, 2], [0.8, 2], [1, 0]]), rot: kf(u, [[0, 0], [0.35, 0.06], [0.8, 0.06], [1, 0]]), pivot: [0, -20] });
        A(p, "head", { dx: kf(u, [[0, 0], [0.35, 1.5], [0.8, 1.5], [1, 0]]), sx: 1 + 0.12 * bump(u, 0.3, 0.8), sy: 1 + 0.12 * bump(u, 0.3, 0.8) });
        A(p, "armN", { rot: kf(u, [[0, 0], [0.35, -0.6], [0.8, -0.5], [1, 0]]) }); A(p, "armB", { rot: kf(u, [[0, 0], [0.35, 0.6], [0.8, 0.5], [1, 0]]) });
        if (u > 0.3 && u < 0.5) FX(p, { k: "glow", x: 3, y: -42, r: 8, c: c[1], a: bump(u, 0.3, 0.5) });
        for (let i = 0; i < 3; i++) { const q = seg(u, 0.38 + i * 0.1, 0.72 + i * 0.1); if (q > 0 && q < 1) FX(p, { k: "wave", x: 6 + (TGT - 6) * q, y: -42 + 26 * q, r: 3 + 5 * q, c: c[0], a: 1 - q * 0.6 }); }
      } },
    },
    death(p, u, e) { p.flash = u < 0.15 ? 0.8 : 0; const k = sm(seg(u, 0.1, 0.9)); R(p, { dy: -7 * k, sx: 1 - 0.45 * k, sy: 1 + 0.4 * k }); A(p, "body", { kx: 0.2 * Math.sin(u * 14) * k }); A(p, "armN", { rot: 0.8 * k }); A(p, "armB", { rot: 0.7 * k }); p.alpha = 1 - k; p.shadow = 1 - k;
      for (let i = 0; i < 5; i++) { const q = seg(u, 0.15 + i * 0.08, 0.75 + i * 0.05); if (q > 0 && q < 1) FX(p, { k: "puff", x: (i - 2) * 5, y: -12 - i * 6 - 12 * q, r: 3 + 2 * q, c: e.r.P.base, a: 1 - q }); } },
  };
  // ---- 晶塔 ----
  BODY.pylon = { kind: "pylon", mouth: [2, -22], units: "火／霧／雷之源晶柱、陣眼石靈",
    idle(p, u) { A(p, "ring", { dy: 1.2 * S(u, 1), sx: 1 + 0.05 * S(u, 2) }); A(p, "eye", { sy: u > 0.82 && u < 0.92 ? 0.25 : 1 }); A(p, "ob", { sy: 1 + 0.01 * S(u, 1) }); },
    move(p, u) { const lift = -2.5 - 0.8 * S(u, 1); for (const g of ["ob", "eye", "ring"]) A(p, g, { dy: lift, rot: 0.05 * S(u, 1, 0.25), pivot: [0, -5] }); A(p, "ring", { sx: 1 + 0.06 * S(u, 2) }); p.shadow = 0.85; },
    attacks: {
      beam: { zh: "晶射線（fist 普攻）", type: "cast", ms: 920, fn(p, u, e) {
        const c = e.r.element ? elc(e.r, ELEM.lightning) : [e.r.P.accent ?? "#e4dcff", "#ffffff"];
        A(p, "ring", { sx: kf(u, [[0, 1], [0.38, 0.6], [0.5, 1.2], [0.8, 1.1], [1, 1]]), dy: kf(u, [[0, 0], [0.38, -3], [0.5, 1], [1, 0]]) });
        A(p, "eye", { sx: 1 + 0.4 * bump(u, 0.1, 0.8), sy: 1 + 0.4 * bump(u, 0.1, 0.8) });
        for (const g of ["ob", "eye", "ring"]) A(p, g, { dx: u > 0.45 && u < 0.75 ? -0.8 : 0 });
        charge(p, u, 0.1, 0.42, [3, -22], c, 2.6);
        if (u > 0.44 && u < 0.78) { const w = 3.2 * (1 - 0.6 * seg(u, 0.65, 0.78)); FX(p, { k: "beam", x0: 4, y0: -22, x1: TGT, y1: -16, w, c: c[0] }); FX(p, { k: "glow", x: TGT, y: -16, r: 9, c: c[0], a: 0.8 }); }
      } },
      pulse: { zh: "晶脈衝（自身範圍）", type: "area", ms: 960, fn(p, u, e) {
        const c = e.r.element ? elc(e.r, ELEM.fire) : [e.r.P.base, "#ffffff"];
        A(p, "ring", { sx: kf(u, [[0, 1], [0.35, 0.7], [0.5, 1.9], [0.75, 1.3], [1, 1]]), a: kf(u, [[0, 1], [0.5, 0.6], [0.75, 0.3], [1, 1]]), dy: kf(u, [[0, 0], [0.35, -4], [0.5, 0], [1, 0]]) });
        p.flash = u > 0.4 && u < 0.52 ? 0.5 : 0; p.flashColor = c[0];
        if (u > 0.45) for (const d of [0, 0.15]) { const q = seg(u, 0.45 + d, 1); if (q > 0 && q < 1) FX(p, { k: "ring", x: 0, rx: 10 + 30 * q, c: c[0], a: 1 - q }); }
        if (u > 0.4 && u < 0.7) FX(p, { k: "glow", x: 0, y: -22, r: 16, c: c[0], a: bump(u, 0.4, 0.7) });
      } },
    },
    death(p, u, e) { // 龜裂、往前倒、晶片散落
      p.flash = u < 0.2 ? 0.8 : 0; const j = u < 0.28 ? 0.7 * Math.sign(Math.sin(u * 100)) : 0, f = sm(seg(u, 0.25, 0.68)) - 0.06 * bump(u, 0.68, 0.8);
      // 整隻（含詞綴）繞底座右上角倒下，底座反向轉回原位不動（審查退回 #4：詞綴留在半空）
      R(p, { dx: j, rot: 1.42 * f, pivot: [5, -5] }); A(p, "base", { dx: -j, rot: -1.42 * f, pivot: [5, -5] }); A(p, "eye", { a: 1 - 0.7 * seg(u, 0.3, 0.7) }); A(p, "ring", { a: 1 - seg(u, 0.25, 0.5) });
      if (u > 0.66) { const k = seg(u, 0.66, 1); FX(p, { k: "dust", x: 22, y: -1, r: 5, a: 1 - k }); for (let i = 0; i < 4; i++) FX(p, { k: "shard", x: 14 + i * 7 + 4 * k * (i - 1.5), y: Math.min(-1.5, -6 - 6 * Math.sin(Math.PI * k) + i), rot: i + 3 * k, s: 1.6, c: QC.light(e.r.P.base, 0.2) }); }
    },
  };
  // ---- 鳥 ----
  BODY.bird = { kind: "flyer", mouth: [17, -21], units: "雷羽鷹",
    // 待機（QK-4 檢查 §3-3）：落地收翅站著（翅膀往後下貼著身體）；一圈抖一次翅膀（半開、收回，兩下）；頭左右看、尾巴輕擺
    idle(p, u) {
      R(p, { dy: 9 }); p.shadow = 1;
      const sh = u >= 0.55 && u < 0.8 ? Math.abs(Math.sin(TAU * seg(u, 0.55, 0.8))) : 0; // 抖翅：0→1→0 兩下
      A(p, "wingN", { sy: -0.42 - 0.2 * sh, rot: 2.1 + 0.75 * sh }); A(p, "wingF", { sy: -0.38 - 0.2 * sh, rot: 0.3 + 0.5 * sh });
      R(p, { dy: -0.6 * sh }); A(p, "head", { rot: 0.07 * S(u, 1, 0.3) }); A(p, "tail", { rot: 0.06 * S(u, 1) + 0.1 * sh });
    },
    move(p, u) { flap(p, u, { bob: 2.2, dn: -0.6, base: -6 }); // 飛高一點、下拍收小：翅尖不穿地（審查退回 #5）
      R(p, { rot: 0.08 }); A(p, "tail", { rot: 0.08 * S(u, 1) }); A(p, "legs", { rot: 0.5 }); },
    attacks: {
      rake: { zh: "爪擊（talons）", type: "melee", ms: 700, fn(p, u) {
        R(p, { dx: kf(u, [[0, 0], [0.3, -2], [0.52, 8], [0.68, 6], [1, 0]]), dy: kf(u, [[0, 0], [0.3, -6], [0.52, 3], [0.68, 1], [1, 0]]), rot: kf(u, [[0, 0], [0.3, -0.15], [0.52, -0.3], [1, 0]]) });
        const w = kf(u, [[0, 1], [0.3, 1.15], [0.52, -0.3], [0.7, 0.4], [1, 1]]); A(p, "wingN", { sy: w }); A(p, "wingF", { sy: w });
        A(p, "legs", { rot: kf(u, [[0, 0], [0.3, -0.4], [0.5, -1.35], [0.68, -0.8], [1, 0]]) }); A(p, "head", { rot: kf(u, [[0, 0], [0.5, 0.2], [1, 0]]) });
        slashFx(p, u, 0.48, 0.65, 26, -10, "#ffffff", 6);
      } },
      dive: { zh: "俯衝斬（衝鋒）", type: "charge", ms: 920, fn(p, u) {
        R(p, { dx: kf(u, [[0, 0], [0.35, -5], [0.58, 15], [0.7, 14], [1, 0]]), dy: kf(u, [[0, 0], [0.35, -14], [0.58, 6], [0.7, 4], [1, 0]]), rot: kf(u, [[0, 0], [0.35, -0.25], [0.45, 0.55], [0.58, 0.45], [0.72, -0.2], [1, 0]]) });
        const w = u < 0.35 ? 1.05 - 1.6 * Math.max(0, S(u / 0.35, 2)) : kf(u, [[0.35, 1], [0.42, 0.25], [0.58, 0.25], [0.7, -0.25], [0.85, 1], [1, 1]]);
        A(p, "wingN", { sy: w, rot: u > 0.38 && u < 0.6 ? 0.5 : 0 }); A(p, "wingF", { sy: w, rot: u > 0.38 && u < 0.6 ? 0.5 : 0 });
        A(p, "legs", { rot: kf(u, [[0, 0], [0.45, 0.4], [0.56, -1.2], [0.72, -0.5], [1, 0]]) });
        slashFx(p, u, 0.55, 0.72, 33, -6, "#ffffff", 7); if (u > 0.55 && u < 0.8) FX(p, { k: "dust", x: 30, y: -1, r: 3.5, a: 1 - seg(u, 0.55, 0.8) });
        p.shadow = 1 - 0.3 * bump(u, 0.1, 0.45);
      } },
      cast: { zh: "靜電掌（翅尖放電）", type: "cast", ms: 880, fn(p, u, e) {
        const c = elc(e.r, ELEM.lightning);
        const w = kf(u, [[0, 1], [0.38, 1.25], [0.52, -0.55], [0.7, -0.3], [1, 1]]); A(p, "wingN", { sy: w }); A(p, "wingF", { sy: w });
        R(p, { dy: kf(u, [[0, 0], [0.38, 2], [0.52, -4], [1, 0]]), rot: kf(u, [[0, 0], [0.38, -0.1], [0.52, 0.12], [1, 0]]) });
        if (u > 0.1 && u < 0.5) for (const [x, y] of [[17, -51], [-19, -47]]) FX(p, { k: "bolt", x0: x - 2, y0: y, x1: x + 2, y1: y + 5, c: c[0], amp: 0.5 * Math.sin(u * 50) });
        if (u > 0.5 && u < 0.72) { FX(p, { k: "bolt", x0: 12, y0: -22, x1: TGT - 16, y1: -14, c: c[0], amp: 1 + 0.5 * Math.sin(u * 70) }); FX(p, { k: "glow", x: TGT - 16, y: -14, r: 10, c: c[0], a: 1 - seg(u, 0.5, 0.72) * 0.5 }); }
      } },
    },
    death(p, u, e) { p.flash = u < 0.15 ? 0.8 : 0; const fall = sm(seg(u, 0.2, 0.7)), j = bump(u, 0, 0.25);
      R(p, { dy: -3 * j + 11 * fall - 1.2 * bump(u, 0.7, 0.82), rot: -0.2 * j + 0.22 * fall, dx: 3 * fall, pivot: [0, -18] }); p.softGround = true;
      const w = 1 - 0.75 * fall; A(p, "wingN", { sy: w, rot: 0.3 * fall }); A(p, "wingF", { sy: w * 0.8, rot: 0.2 * fall }); A(p, "head", { rot: 0.5 * sm(seg(u, 0.6, 0.95)) }); A(p, "legs", { rot: -0.8 * fall }); p.shadow = 1;
      if (u > 0.68 && u < 0.95) FX(p, { k: "dust", x: 4, y: -1, r: 4, a: 1 - seg(u, 0.68, 0.95) }); },
  };
  // ---- 蝠 ----
  BODY.bat = { kind: "flyer", mouth: [8, -21], units: "火塵蝠",
    idle(p, u) { R(p, { dy: -1.6 * S(u, 2) }); flap(p, (u * 2) % 1, { up: 1, dn: 0.55, bob: 0.6 }); A(p, "head", { rot: 0.06 * S(u, 1) }); },
    move(p, u) { flap(p, u, { bob: 2, dn: -0.7 }); R(p, { rot: 0.1 }); },
    attacks: {
      fire: { zh: "火焰箭（fire_staff 普攻＋技能，口吐）", type: "cast", ms: 800, fn(p, u, e) {
        const c = elc(e.r, ELEM.fire);
        R(p, { dx: kf(u, [[0, 0], [0.35, -3], [0.48, 2], [1, 0]]), dy: kf(u, [[0, 0], [0.35, -3], [0.48, 0], [1, 0]]), rot: kf(u, [[0, 0], [0.35, -0.2], [0.48, 0.15], [1, 0]]) });
        flap(p, (u * 2) % 1, { bob: 0.8 }); A(p, "head", { rot: kf(u, [[0, 0], [0.35, -0.35], [0.48, 0.25], [1, 0]]) });
        charge(p, u, 0.08, 0.42, [10, -24], c, 2.2); shot(p, u, 0.44, 0.66, [12, -22], c, { r: 2.4, y1: -16 });
      } },
      bite: { zh: "撲咬", type: "melee", ms: 660, fn(p, u) {
        R(p, { dx: kf(u, [[0, 0], [0.25, -3], [0.5, 10], [0.65, 9], [1, 0]]), dy: kf(u, [[0, 0], [0.25, -4], [0.5, 3], [1, 0]]), rot: kf(u, [[0, 0], [0.25, -0.15], [0.5, 0.3], [1, 0]]) });
        const w = kf(u, [[0, 1], [0.25, 1.1], [0.45, 0.35], [0.6, -0.5], [0.8, 1], [1, 1]]); A(p, "wingN", { sy: w }); A(p, "wingF", { sy: w });
        A(p, "head", { rot: kf(u, [[0, 0], [0.3, -0.3], [0.5, 0.3], [1, 0]]) }); chompFx(p, u, 0.42, 0.62, 25, -20);
      } },
    },
    death(p, u, e) { p.flash = u < 0.15 ? 0.8 : 0; const fall = sm(seg(u, 0.18, 0.65));
      R(p, { dy: -2 * bump(u, 0, 0.2) + 7.6 * fall - 1 * bump(u, 0.65, 0.78), rot: 0.4 * fall, pivot: [0, -18] }); p.softGround = true; A(p, "wingN", { sy: 1 - 0.7 * fall, rot: 0.35 * fall }); A(p, "wingF", { sy: 1 - 0.6 * fall }); A(p, "head", { rot: 0.4 * fall });
      if (u > 0.64 && u < 0.92) FX(p, { k: "dust", x: 0, y: -1, r: 3.5, a: 1 - seg(u, 0.64, 0.92) }); },
  };

  // ============================== 片段表、量化、對外 ==============================
  const IDLE_MS = { hound: 2200, boar: 2000, bear: 2400, feline: 2200, lizard: 2200, shell: 2400, beetle: 2000, spider: 2000, serpent: 2200, ooze: 2000, golem: 2400, wisp: 2000, wraith: 2400, pylon: 2400, bird: 2000, bat: 2000 };
  const MOVE_MS = { hound: 640, boar: 560, bear: 820, feline: 640, lizard: 560, shell: 960, beetle: 520, spider: 480, serpent: 720, ooze: 760, golem: 960, wisp: 800, wraith: 900, pylon: 1000, bird: 520, bat: 360 };
  const HIT_MS = 400, DEATH_MS = 1000, FPS_MS = 1000 / 12, LOOP_N = 8;
  const keyOf = (spec) => QC.rigKey(QC.resolve(spec));
  /** 這款身形的片段清單：["idle", "move", "atk:<id>"…, "hit", "death"]。 */
  function clips(bk) { return ["idle", "move", ...Object.keys(BODY[bk].attacks).map((a) => `atk:${a}`), "hit", "death"]; }
  function clipInfo(bk, clip) {
    if (clip === "idle") return { ms: IDLE_MS[bk], loop: true, zh: "待機" };
    if (clip === "move") return { ms: MOVE_MS[bk], loop: true, zh: "移動" };
    if (clip === "hit") return { ms: HIT_MS, loop: false, zh: "受擊" };
    if (clip === "death") return { ms: DEATH_MS, loop: false, zh: "倒下", hold: true };
    const a = BODY[bk].attacks[String(clip).replace(/^atk:/, "")];
    return a ? { ms: a.ms, loop: false, zh: a.zh, type: a.type, typeZh: T[a.type] } : null;
  }
  /** 片段在 t 毫秒的格號與 u（0～1）。循環：一圈 8 格，相位由 id 決定；單次：12 格／秒，最後一格是 u＝1。 */
  function frameOf(info, t, id) {
    if (info.loop) { const step = info.ms / LOOP_N, ph = id ? (idHash(id) % 1000) / 1000 : 0, tt = (((t + ph * info.ms) % info.ms) + info.ms) % info.ms, f = Math.floor(tt / step); return { f, n: LOOP_N, u: f / LOOP_N }; }
    const n = Math.max(2, Math.round(info.ms / FPS_MS)), f = Math.min(n - 1, Math.max(0, Math.floor(t / FPS_MS))); return { f, n, u: f / (n - 1) };
  }
  /** 片段在 t 的姿勢。opt：{id, reduce}。不認得的片段 → null（靜態）。 */
  function pose(spec, clip, t, opt = {}) {
    const r = QC.resolve(spec), bk = QC.rigKey(r), B = BODY[bk], info = B && clipInfo(bk, clip);
    if (!info) return null;
    const { u } = frameOf(info, Math.max(0, +t || 0), opt.id), p = newPose(), e = { r, bk };
    if (bk === "spider") p.limbRim = true; // 蜘蛛的細腳加亮邊（審查退回 #6）
    if (opt.reduce) {
      if (clip === "idle" || clip === "move") return null;
      if (clip === "hit") { p.flash = u < 0.2 ? 0.9 : 0; return p; }
      if (clip === "death") { B.death(p, 1, e); p.fx = []; return p; }
      const a = B.attacks[clip.slice(4)]; a.fn(p, u, e); const fx = p.fx, q = newPose(); q.fx = fx; R(q, { dx: 2 * Math.sin(Math.PI * u) }); return q;
    }
    if (clip === "idle") B.idle(p, u, e);
    else if (clip === "move") B.move(p, u, e);
    else if (clip === "hit") HIT[B.kind === "quad" ? "quad" : B.kind](p, u, e);
    else if (clip === "death") B.death(p, u, e);
    else B.attacks[clip.slice(4)].fn(p, u, e);
    return p;
  }
  /** 畫一格：和 QCreature.stamp 同參數，多 clip、t（毫秒）、opt。 */
  function stamp(ctx, spec, clip, t, cx, cy, k = 1, west = false, opt = {}) {
    const p = pose(spec, clip, t, opt);
    QC.stamp(ctx, p ? { ...spec, pose: p } : spec, cx, cy, k, west);
    if (p && p.fx.length) { const r = QC.resolve(spec), s = k * r.size; ctx.save(); ctx.translate(cx, cy); ctx.scale(west ? -s : s, s); drawFx(ctx, p.fx, r); ctx.restore(); }
    return p;
  }
  return { BODY, T, clips, clipInfo, frameOf, pose, stamp, idHash, keyOf, drawFx, kf };
})();
