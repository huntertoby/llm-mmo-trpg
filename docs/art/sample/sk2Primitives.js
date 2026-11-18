// sk2Primitives.js：SK-2 三個新戰鬥原語的美術樣張（畫圖 agent，2026-11-19；紀錄 docs/art/SK-2原語-美術.md）。
// 範圍：① 三個效果的 Q 版部件圖樣（吸收表面 absorb_surface、疾病擴散 contagion、鉤 hook；取代 client/src/render/qIcon/parts.ts
//        EFFECT_ALIAS 暫借的清除表面、施加狀態、拉扯）；② 戰鬥演出（canvas，時間 t 毫秒 → 一格畫面）；③ 狀態框的「會擴散」記號。
// 畫法語言照第④批部件（qIconsParts.js）與第⑤批狀態（qIconsStatus.js）：±10 單位、平塗三階、剪影外框、光暈在外框底下。
// 不改任何過審的畫法檔：新圖樣只在呼叫 install() 的頁面塞進 QIconsParts.CATS.effect（同 KW 段的作法），狀態框記號是疊在
// QIconsStatus.paint() 之上的一層。戰場單位一律呼叫現行畫法（QDoll.stamp 經 OccludeOutline.drawRing／drawBody、QBossGiant.draw、Regions4.tile）。
// 確定性：沒有 Math.random；動畫只吃 t。
window.SK2Prim = (() => {
  const Q = window.QIcons, QS = window.QIconsSkills, QP = window.QIconsParts, QW = window.QIconsWeapons, QSt = window.QIconsStatus, OO = window.OccludeOutline;
  const { mix, f, rr, ci, el, poly, ln, starPts, drop, halo, flame } = Q.H;
  const TAU = Math.PI * 2, PI = Math.PI, OUT = "#16121a";
  const st = (c, col, w, fn, cap = "round") => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
  const at = (c, x, y, k, fn, rot = 0) => { c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k); fn(c); c.restore(); };
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const ease = (t) => { t = clamp(t); return t * t * (3 - 2 * t); };
  const span = (t, a, b) => clamp((t - a) / (b - a));
  const lerp = (a, b, t) => a + (b - a) * t;

  // =====================================================================
  // 1. 「會擴散」的共同色：病菌黃綠。只給這三個原語與狀態框的記號用（和中毒的綠 #7ddc3a 拉開：偏黃、較亮）。
  // =====================================================================
  const GERM = { body: "#c4e44c", hi: "#f0ffb0", dark: "#7a9a26", knob: "#e2f47a" };

  /** 病菌：圓身體＋一圈短柄圓頭的刺（6～8 根）＋兩三個暗斑。≤14px 刺減成 6 根、不畫柄與斑。 */
  function germ(c, o, x, y, R, n = 8, rot = 0) {
    const tiny = o.tiny, k = tiny ? 6 : n;
    for (let i = 0; i < k; i++) {
      const a = rot + (i / k) * TAU, ca = Math.cos(a), sa = Math.sin(a);
      if (!tiny) ln(c, GERM.dark, R * 0.26, [[x + ca * R * 0.8, y + sa * R * 0.8], [x + ca * R * 1.32, y + sa * R * 1.32]]);
      ci(c, GERM.knob, x + ca * R * (tiny ? 1.12 : 1.42), y + sa * R * (tiny ? 1.12 : 1.42), R * (tiny ? 0.36 : 0.27));
    }
    ci(c, GERM.body, x, y, R);
    if (tiny) ci(c, GERM.dark, x + R * 0.25, y + R * 0.25, R * 0.3); /* ≤14px 留一個暗斑：和消耗狀態的橘色爆星（同樣是一圈尖角的圓）剪影分開 */
    if (!tiny) { ci(c, GERM.dark, x + R * 0.32, y + R * 0.3, R * 0.24); ci(c, GERM.dark, x - R * 0.12, y + R * 0.52, R * 0.15); ci(c, GERM.dark, x + R * 0.55, y - R * 0.18, R * 0.13); }
    el(c, GERM.hi, x - R * 0.36, y - R * 0.38, R * 0.36, R * 0.22, -0.7);
  }

  /** 爪鉤（直立：繩環在下 (0, 9.4)、直柄、頂上一根尖刺＋左右兩支往回彎的爪，爪尖朝下＝朝繩環）。
   *  第 1 次試的單支 J 鉤（繩環＋彎鉤＋倒刺）在圓片裡讀成問號「?」與回轉箭頭，改成三爪的爪鉤。外接框 x ±8.4、y −11.6～12.4。
   *  w0＞0：外框那一遍（整個形加粗）；flat：只畫剪影。 */
  function hookJ(c, o, col = "#c3ccd6", w0 = 0, flat = false) {
    /* 爪：圓弧（中心 (±4.2, −4.6)、半徑 4.2）從柄頂往外、往下繞回來，爪尖一個朝柄的倒刺（像錨爪）；第 1 版的薄月牙爪讀成鎬頭 */
    const claw = (sx) => { c.save(); c.scale(sx, 1); st(c, col, 3.6 + w0, (x) => x.arc(-4.2, -4.6, 4.2, 0, PI * 0.84, true), "butt"); const ex = -4.2 + Math.cos(PI * 0.84) * 4.2, ey = -4.6 + Math.sin(PI * 0.84) * 4.2, tx = Math.sin(PI * 0.84), ty = -Math.cos(PI * 0.84); poly(c, col, [[ex + tx * (3 + w0 * 0.6), ey + ty * (3 + w0 * 0.6)], [ex - ty * (2.2 + w0 / 2) - tx * 0.6, ey + tx * (2.2 + w0 / 2) - ty * 0.6], [ex + ty * (2.2 + w0 / 2) - tx * 0.6, ey - tx * (2.2 + w0 / 2) - ty * 0.6]], 0.3); c.restore(); };
    ln(c, col, 3.8 + w0, [[0, 7], [0, -6]], "butt");
    poly(c, col, [[0, -11.6 - w0 * 0.7], [2 + w0 / 2, -6], [-2 - w0 / 2, -6]], 0.4);
    claw(-1); claw(1);
    ci(c, col, 0, 9.4, 3.2 + w0 / 2);
    if (flat) return;
    ci(c, OUT, 0, 9.4, 1.25);
    if (!o.tiny) { ln(c, "#ffffff", 1, [[-0.75, 5.6], [-0.75, -5]], "butt"); st(c, "#ffffff", 1, (x) => x.arc(-4.2, -4.6, 4.2, -PI * 0.15, -PI * 0.85, true), "butt"); ln(c, "#7d8794", 1, [[0.8, 5.6], [0.8, -3.4]], "butt"); }
  }
  /** 圖樣用：爪鉤轉 45°（繩環在左下、爪在右上），中心 (x,y)。 */
  function hookArt(c, o, x = 0, y = 0, k = 1) { at(c, x, y, k, (q) => { q.translate(0, -0.4); hookJ(q, o); }, PI / 4); }
  /** 一節鎖鏈（中心 x,y、沿 a 方向）：side＝true 是側面（細長條），false 是正面（橢圓環＋洞）。 */
  function link(c, x, y, a, L, side, col = "#c3ccd6", dk = "#7d8794", hole = OUT) {
    at(c, x, y, 1, (q) => {
      if (side) rr(q, dk, -L / 2, -L * 0.17, L, L * 0.34, L * 0.17);
      else { el(q, col, 0, 0, L / 2, L * 0.34); el(q, hole, 0, 0, L * 0.24, L * 0.11); }
    }, a);
  }

  /** 吸收表面的圖樣本體（±10 單位）：一灘＋從一灘裡長出來的粗箭頭＋兩側往上飛的倒水滴（≥26px）。 */
  function absorbArt(c, o, T) {
    const tint = T ?? QS.TINT.water;
    el(c, tint[0], 0, 7.4, 10.8, 3.3);
    // 箭桿從一灘裡長出來（底部往兩側攤開接進一灘）＋箭頭
    f(c, tint[0], () => { c.moveTo(-6.8, 6.4); c.quadraticCurveTo(-2.6, 5.6, -2.6, 0.6); c.lineTo(-2.6, -1.6); c.lineTo(-8, -1.6); c.lineTo(0, -10.8); c.lineTo(8, -1.6); c.lineTo(2.6, -1.6); c.lineTo(2.6, 0.6); c.quadraticCurveTo(2.6, 5.6, 6.8, 6.4); c.closePath(); });
    // 亮面：箭頭左半、箭桿左緣、一灘左邊一道
    poly(c, tint[1], [[0, -10.8], [-8, -1.6], [-2.6, -1.6], [-2.6, 0.6], [-0.6, 0.6], [-0.6, -6.4]]);
    el(c, tint[1], -4.8, 7.9, 3.4, 0.95);
    if (o.tiny) return;
    for (const [x, y, k] of [[-7.4, 1.6, 0.27], [7.4, 0.6, 0.23]]) halo(c, o, (q) => at(q, x, y, k, (p) => { drop(p, tint[0], 0, 0, 1); el(p, tint[1], -2.2, 3.4, 1.8, 3, 0.3); }, PI));
  }

  function contagionArt(c, o) {
    if (o.tiny) { germ(c, o, 0, 0.2, 6.2, 6, 0.26); return; }
    germ(c, o, -2.6, 2.6, 5.8, 8, 0.2);
    halo(c, o, (q) => { ci(q, GERM.knob, 3.6, -2.2, 1.15); ci(q, GERM.knob, 5.1, -4.3, 1.3); });
    halo(c, o, (q) => { for (let i = 0; i < 5; i++) { const a = 0.6 + (i / 5) * TAU; ci(q, GERM.knob, 7.2 + Math.cos(a) * 3.4, -6.8 + Math.sin(a) * 3.4, 1.05); } ci(q, GERM.body, 7.2, -6.8, 2.6); ci(q, GERM.hi, 6.4, -7.6, 0.9); });
  }
  function hookChip(c, o) {
    if (o.tiny) { hookArt(c, o, 0.4, -0.2, 0.9); return; }
    const k = 0.8, cx = 1.4, cy = -1.4, eye = [cx - 6.65 * k, cy + 6.65 * k];
    link(c, eye[0] - 3.4, eye[1] + 3.4, -PI / 4, 4.6, false, "#c3ccd6", "#a8b2be");
    halo(c, o, (q) => hookArt(q, o, cx, cy, k));
  }
  const EFFECT = {
    absorb_surface: {
      zh: "吸收表面", topic: "地上一灘表面（染表面色），中間被抽成一根往上的粗箭頭（箭桿從一灘裡長出來）；≥26px 兩側各一顆倒過來（尖端朝下＝往上飛）的小水滴",
      d: (c, o, T) => at(c, 0, 0.3, 0.86, (q) => absorbArt(q, o, T)), /* 縮到 0.86：箭頭尖不頂到色環（第 4 批 2.8 的 fit） */
    },
    contagion: {
      zh: "疾病擴散", topic: "一顆黃綠病菌（圓身、一圈短柄圓頭的刺、暗斑），往右上兩顆小點跳到一顆小病菌；≤14px 只留大的那顆",
      d: (c, o) => at(c, 0, 0, 0.84, (q) => contagionArt(q, o)), /* 縮到 0.84：刺與小病菌收在色環內 */
    },

    hook: {
      zh: "鉤", topic: "一支鋼爪鉤（繩環、直柄、頂上尖刺＋兩支往回彎的爪），斜放：繩環在左下、爪在右上；≥26px 繩環再往左下接一節鎖鏈；≤14px 只留爪鉤",
      d: (c, o) => at(c, 0, 0, 0.88, (q) => hookChip(q, o)), /* 縮到 0.88：爪與鎖鏈收在色環內 */
    },

  };
  /** 塞進第④批的效果表（只在呼叫的頁面；qIconsParts.js 原檔不動）。entry() 先查 EFFECT_ALIAS（樣張端沒有 SK-2 的三個別名），所以直接用原語代碼。 */
  function install() {
    for (const [id, e] of Object.entries(EFFECT)) QP.CATS.effect[id] = { ...e, src: "new:sk2" };
  }

  // =====================================================================
  // 2. 狀態框的「會擴散」記號：框的四個角各一顆病菌黃綠的「孢子」（深色 1 裝置像素外框），像從框裡往外噴。
  //    頭頂（框 < 14 CSS px，含戰場上放大縮小後的 10.2～12.4）：孢子中心在框角外側（離框心 0.478 框邊長），半徑＝框邊長 × 0.13（1.15～1.4 CSS px），整個圖示仍在 11×11 以內。
  //    狀態卡 20（框 16.8、裁成半徑 9.8 的圓）：框角已經被圓裁掉一點，孢子壓在框角上（中心離框心 0.345 框邊長），半徑 1.4。
  //    其他框形（增益圓框、中性六角）也照「框邊長 × 比例」放四個斜角；這三個狀態都是減益（圓角方框）。
  // =====================================================================
  const SPORE = { fill: "#e2f47a", ink: OUT };
  /** 框邊長（CSS px）小於這個值用「頭頂」的排法（孢子在框角外側）：狀態卡 16.8 不是；頭頂 11 的框 9、1600 寬放大後 12.4、800 寬反向放大後 10.2 都是（第一次照第⑤批的 HEAD_MAX 12 分，1600 寬的 12.4 走到狀態卡的排法、孢子壓在框角上，800 寬幾乎看不到）。 */
  const SPORE_HEAD = 14;
  /** ctx 原點＝框心；size＝框邊長（ctx 單位）；unitPx、res 同 QIconsStatus.paint。 */
  function spreadMark(ctx, size, unitPx = 1, res = 2) {
    const css = size * unitPx, head = css < SPORE_HEAD, a = (head ? 0.478 : 0.345) * size, r = (head ? Math.min(1.4, Math.max(1.15, css * 0.13)) : 1.4) / unitPx, ink = 1 / (res * unitPx);
    ctx.save();
    for (const [sx, sy] of [[1, -1], [1, 1], [-1, 1], [-1, -1]]) {
      ctx.beginPath(); ctx.arc(sx * a, sy * a, r + ink, 0, TAU); ctx.fillStyle = SPORE.ink; ctx.fill();
      ctx.beginPath(); ctx.arc(sx * a, sy * a, r, 0, TAU); ctx.fillStyle = SPORE.fill; ctx.fill();
    }
    ctx.restore();
  }
  /** 狀態圖示（Q 版框＋圖樣，第⑤批）＋會擴散記號。 */
  function paintStatus(ctx, id, cx, cy, size, unitPx = 1, res = 2, opt = {}) {
    QSt.paint(ctx, id, cx, cy, size, unitPx, res, opt);
    if (opt.spread) { ctx.save(); ctx.translate(cx, cy); spreadMark(ctx, size, unitPx, res); ctx.restore(); }
  }
  /** 戰場頭頂（statusIconCanvas(id, 11)：框 px−2）。 */
  function headCanvas(id, px, zoom = 1, opt = {}) { const res = opt.res ?? (zoom === 1 ? 2 : zoom), cv = Q.H.blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d"); x.scale(res, res); paintStatus(x, id, px / 2, px / 2, px - 2, 1, res, opt); return cv; }
  /** 狀態卡（statusIconTile＋tileCanvas：100 單位、裁成半徑 49 的圓，框 84）。 */
  function cardCanvas(id, px, zoom = 1, opt = {}) { const res = opt.res ?? (zoom === 1 ? 2 : zoom), cv = Q.H.blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d"); x.scale((px * res) / 100, (px * res) / 100); x.beginPath(); x.arc(50, 50, 49, 0, TAU); x.clip(); paintStatus(x, id, 50, 50, 84, px / 100, res, opt); return cv; }

  // =====================================================================
  // 3. 戰場上的鎖鏈與鉤（模型像素，1 格 48）
  // =====================================================================
  const STEEL = "#c3ccd6", STEEL_D = "#7d8794", STEEL_L = "#eef2f6";
  /** 鎖鏈：沿折線 pts（[x,y] 陣列）每 step 一節，交錯正面／側面；先整條畫外框色粗線，再畫鏈節。sag：中段往下垂（鬆掉時）。 */
  function chain(ctx, pts, opt = {}) {
    const step = opt.step ?? 3.6, L = opt.L ?? 4.2, glow = opt.glow ?? 0;
    // 沿路徑取樣
    const seg = []; let total = 0;
    for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); total += d; }
    const pos = (s) => { let i = 0; while (i < seg.length - 1 && s > seg[i]) { s -= seg[i]; i++; } const t = seg[i] ? s / seg[i] : 0, a = pts[i], b = pts[i + 1]; return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), Math.atan2(b[1] - a[1], b[0] - a[0])]; };
    if (total < 0.5) return;
    if (glow > 0) { ctx.save(); ctx.globalAlpha = glow; ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 5; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.stroke(); ctx.restore(); }
    ctx.save(); ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.strokeStyle = OUT; ctx.lineWidth = L * 0.68 + 1.6; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.stroke(); ctx.restore();
    const n = Math.max(1, Math.floor(total / step)), off = opt.phase ?? 0;
    for (let k = 0; k <= n; k++) { const s = Math.min(total, k * step + (off % step)); const [x, y, a] = pos(s); link(ctx, x, y, a, L, (k + Math.floor(off / step)) % 2 === 1, STEEL, STEEL_D, OUT); }
  }
  /** 鉤頭（戰場）：x,y＝繩環，a＝鉤指向的方向（弧度），k＝大小（1 ≈ 圖樣格 1 單位 = 0.7 模型 px）。open：鉤張開（飛行中）0～1。 */
  /** 戰場上的爪鉤：繩環在 (x,y)、爪朝 a 方向；k＝圖樣 1 單位幾個模型 px。 */
  function hookHead(ctx, x, y, a, k = 0.6) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(a + PI / 2); ctx.scale(k, k); ctx.translate(0, -9.4);
    hookJ(ctx, { tiny: false }, OUT, 2.6 / k, true); hookJ(ctx, { tiny: false }, STEEL, 0, false);
    ctx.restore();
  }

  // =====================================================================
  // 4. 特效小零件
  // =====================================================================
  const FIRE = ["#ff6a1a", "#ffd23f"], BLOOD = ["#e8455a", "#ffb0b8"], POISON = ["#7ddc3a", "#d6f59a"];
  const DOT = { burning: { T: FIRE, kind: "fire" }, bleed: { T: BLOOD, kind: "drop" }, poison: { T: POISON, kind: "bubble" } };
  /** 一顆狀態「微粒」（擴散時飛過去的那一團）：燃燒＝一小團火、流血＝一滴、中毒＝一顆帶亮點的泡。s＝大小（模型 px 半徑）。 */
  function mote(ctx, kind, x, y, s, a = 1, dir = 0) {
    const d = DOT[kind] ?? DOT.burning; ctx.save(); ctx.globalAlpha *= a; ctx.translate(x, y);
    if (d.kind === "fire") { ctx.rotate(dir + PI / 2); ctx.scale(s / 10, s / 10); flame(ctx, OUT, 0, 0, 1.22); flame(ctx, d.T[0], 0, 0, 1.0); flame(ctx, d.T[1], 0.4, 2.6, 0.58); }
    else if (d.kind === "drop") { ctx.rotate(dir - PI / 2); ctx.scale(s / 10, s / 10); drop(ctx, OUT, 0, 0, 1.22); drop(ctx, d.T[0], 0, 0, 1); el(ctx, d.T[1], -2.4, 3, 1.6, 2.8, 0.3); }
    else { ctx.scale(s / 10, s / 10); ci(ctx, OUT, 0, 0, 9.4); ci(ctx, d.T[0], 0, 0, 8); ci(ctx, d.T[1], -2.6, -2.8, 2.6); ci(ctx, OUT, 7.4, -7.4, 4); ci(ctx, d.T[0], 7.4, -7.4, 2.8); }
    ctx.restore();
  }
  /** 撞擊星（推不動算撞擊；同第③批「擊倒」的黃白七角星）＋往外飛的碎片。p＝0～1。 */
  function impact(ctx, x, y, p, R = 15) {
    const k = p < 0.3 ? ease(p / 0.3) : 1 - ease((p - 0.3) / 0.7) * 0.35, a = p < 0.7 ? 1 : 1 - (p - 0.7) / 0.3;
    ctx.save(); ctx.globalAlpha = a;
    poly(ctx, OUT, starPts(x, y, R * k + 1.6, R * k * 0.48 + 1.6, 7, -1.2)); poly(ctx, "#ffd23f", starPts(x, y, R * k, R * k * 0.48, 7, -1.2)); poly(ctx, "#ffffff", starPts(x, y, R * k * 0.5, R * k * 0.24, 7, -1.2));
    for (let i = 0; i < 6; i++) { const ang = -1.2 + (i / 6) * TAU + 0.3, d = R * (0.9 + 1.1 * ease(p)); rr(ctx, "#fff0b0", x + Math.cos(ang) * d - 1.2, y + Math.sin(ang) * d - 1.2, 2.4, 2.4, 0.8); }
    ctx.restore();
  }
  /** 地上的方向箭頭（擴散的方向）：從 a 到 b 一列三個 V（陣營中性的黃綠），p＝0～1 依序亮起。 */
  function chevrons(ctx, a, b, p, col = GERM.knob) {
    const dx = b.x - a.x, dy = b.y - a.y, L = Math.hypot(dx, dy), ang = Math.atan2(dy, dx);
    for (let i = 0; i < 3; i++) {
      const t = 0.3 + i * 0.2, on = clamp((p - i * 0.18) / 0.3); if (on <= 0) continue;
      ctx.save(); ctx.translate(a.x + dx * t, a.y + dy * t); ctx.rotate(ang); ctx.globalAlpha = on * (1 - clamp((p - 0.85) / 0.15));
      const v = (col2, w) => { ctx.beginPath(); ctx.moveTo(-3.4, -4.4); ctx.lineTo(1.6, 0); ctx.lineTo(-3.4, 4.4); ctx.strokeStyle = col2; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.stroke(); };
      v(OUT, 4.4); v(col, 2.4); ctx.restore();
    }
    void L;
  }

  return { GERM, SPORE, EFFECT, install, germ, hookArt, link, spreadMark, paintStatus, headCanvas, cardCanvas, chain, hookHead, mote, impact, chevrons, DOT, ease, span, lerp, clamp, STEEL, STEEL_D, STEEL_L };
})();
