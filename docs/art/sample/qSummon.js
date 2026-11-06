// qSummon.js：召喚物 17 種的 Q 版畫法（美術 PM 畫圖 agent，2026-11-07）。
// 使用者（11-07）：「所有人先停下 先讓q板完成再開始工作 把所有需要q版的都完成 腳色 動畫 怪物 npc 等 全部」。
// 外觀資料照 summonArt.js（docs/archive/art/召喚物外觀.md 的移植表）：體型 body × 元素配色 × 大小 size × 特徵 trait；不認得的一律退回骷髏戰士。
// 畫法層和 qCreature.js（已通過的 Q 版異形）同一套：平塗、部件之間一條細縫線、整隻剪影外框 1.3 單位 #16121a（QCreature.layer）、方眼。
//   人形召喚物（骷髏、影魅、殘影、守護靈）直接用 QDoll（骷髏的肋骨用 QGearExtra 的軀幹遮罩疊上去）。
//   改動：「外光只代表頭目」→ 影魅、殘影、守護靈不再發外光，只用半透明＋整隻染色；腳下是召喚物的淡綠平塗環（陣營環）。
// 座標：腳底 (0,0)、往上 −y；身高和 Q 版主角同一套（主角約 46）。朝向：漂浮靈、構造體、圖騰、植物畫正面，只差眼睛位置（背面不畫眼睛）；
//   野獸畫側面，朝西鏡像，朝南用朝東、朝北用朝西（同 summonArt.js）；人形四面照 QDoll。確定性：不用 Math.random。
window.QSummon = (() => {
  const TAU = Math.PI * 2, C = window.QCreature, OUT = C.OUT, mix = C.mix, dark = C.dark, light = C.light, ellPts = C.ellPts;

  // ============================== Q 畫法層（同 qCreature.js 的 ink／stroke／limb／dot／eye） ==============================
  function smooth(ctx, pts, closed = true) {
    ctx.beginPath();
    const n = pts.length, mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    if (!closed) { ctx.moveTo(...pts[0]); for (let i = 1; i < n - 1; i++) { const m = mid(pts[i], pts[i + 1]); ctx.quadraticCurveTo(pts[i][0], pts[i][1], m[0], m[1]); } ctx.lineTo(...pts[n - 1]); return; }
    const m0 = mid(pts[n - 1], pts[0]); ctx.moveTo(m0[0], m0[1]);
    for (let i = 0; i < n; i++) { const p = pts[i], m = mid(p, pts[(i + 1) % n]); ctx.quadraticCurveTo(p[0], p[1], m[0], m[1]); }
    ctx.closePath();
  }
  function poly(ctx, pts) { ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); }
  /** 平塗一塊＋本色加深的細縫線（外輪廓由剪影外框負責）。o.sharp＝直線多邊形；o.line＝false 不畫縫線。 */
  function ink(ctx, pts, color, o = {}) { ctx.save(); (o.sharp ? poly : smooth)(ctx, pts); ctx.fillStyle = color; ctx.fill(); if (o.line !== false) { ctx.strokeStyle = mix(color, OUT, 0.55); ctx.lineWidth = o.w ?? 0.55; ctx.lineJoin = "round"; ctx.stroke(); } ctx.restore(); }
  function stroke(ctx, pts, w = 0.7, color = OUT) { ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.lineJoin = "round"; smooth(ctx, pts, false); ctx.stroke(); ctx.restore(); }
  function limb(ctx, pts, w, color) { stroke(ctx, pts, w + 1.1, mix(color, OUT, 0.55)); stroke(ctx, pts, w, color); }
  function dot(ctx, x, y, rx, ry, c) { ctx.fillStyle = c; ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, TAU); ctx.fill(); }
  /** 野獸的眼睛（同 qCreature）：圓角方眼＋方瞳＋高光。 */
  function beye(ctx, x, y, col = "#ffd23a", r = 1) { const s = r * 1.25; ctx.fillStyle = col; ctx.beginPath(); ctx.roundRect(x - 1.15 * s, y - 1.25 * s, 2.3 * s, 2.5 * s, 0.7 * s); ctx.fill(); ctx.fillStyle = OUT; ctx.fillRect(x - 0.2 * s, y - 0.95 * s, 1.0 * s, 1.9 * s); ctx.fillStyle = "#ffffff"; ctx.fillRect(x + 0.15 * s, y - 0.85 * s, 0.45 * s, 0.45 * s); }
  /** 精靈、構造體的眼睛（同 qDoll 的方眼）：深色方塊＋一點高光。 */
  function qeye(ctx, x, y, col = "#1d1a22", r = 1) { ctx.fillStyle = col; ctx.beginPath(); ctx.roundRect(x - 0.95 * r, y - 1.5 * r, 1.9 * r, 3 * r, 0.6 * r); ctx.fill(); ctx.fillStyle = "#ffffff"; ctx.fillRect(x - 0.6 * r, y - 1.2 * r, 0.6 * r, 0.6 * r); }
  const eyesAt = (ctx, f, y, gap, fn) => { if (f.ex === null) return; fn(f.ex - gap, y); fn(f.ex + gap, y); };
  /** 一層平塗＋外框（QCreature.layer），ctx 已在單位座標。 */
  const BOX = [-46, -78, 46, 14];
  const lay = (ctx, size, fn, o = {}) => C.layer(ctx, o.box ?? BOX, fn, { ow: 1.3 / size, alpha: o.alpha, fade: o.fade });
  function shadow(ctx, rx, y = 0.2, a = 0.3) { ctx.fillStyle = `rgba(10,8,14,${a})`; ctx.beginPath(); ctx.ellipse(0, y, rx, rx * 0.3, 0, 0, TAU); ctx.fill(); }
  /** 召喚物的陣營環：淡綠平塗（同 qCreature 的敵方紅環，只換色）。 */
  function summonRing(ctx, rx) { ctx.save(); ctx.globalAlpha = 0.3; ctx.fillStyle = "#7dffb0"; ctx.beginPath(); ctx.ellipse(0, 0, rx, rx * 0.3, 0, 0, TAU); ctx.fill(); ctx.globalAlpha = 0.95; ctx.strokeStyle = "#7dffb0"; ctx.lineWidth = 1.1; ctx.stroke(); ctx.restore(); }

  // ============================== 資料（同 summonArt.js） ==============================
  const KW = { ignite: "#ff6a1a", wet: "#4aa8ff", shock: "#fff36b", freeze: "#8fe3ff", prone: "#e0b080", impact: "#ff9a4a", mark: "#d06aff", high: "#ffe9a8", hidden: "#a0a0c8", summon: "#7dffb0" };
  const SIZE = { small: 0.8, medium: 1, large: 1.25 };
  const SUMMONS = {
    skeleton_warrior: { zh: "骷髏戰士", body: "humanoid", variant: "skeleton", element: "prone", size: "medium", trait: "shield" },
    shade: { zh: "影魅", body: "humanoid", variant: "shade", element: "hidden", size: "medium", trait: "translucent" },
    afterimage: { zh: "殘影分身", body: "humanoid", variant: "afterimage", element: "hidden", size: "medium", trait: "translucent" },
    guardian_spirit: { zh: "守護靈", body: "humanoid", variant: "guardian", element: "summon", size: "medium", trait: "glow" },
    fire_spirit: { zh: "火靈", body: "spirit", element: "ignite", size: "medium" },
    ice_spirit: { zh: "冰靈", body: "spirit", element: "freeze", size: "medium" },
    thunder_spirit: { zh: "雷靈", body: "spirit", element: "shock", size: "medium" },
    water_sprite: { zh: "水精", body: "spirit", element: "wet", size: "small", trait: "puddle" },
    golem: { zh: "石像", body: "construct", variant: "golem", element: "impact", size: "large" },
    bomb_puppet: { zh: "爆裂傀儡", body: "construct", variant: "bomb", element: "ignite", size: "small", trait: "fuse" },
    earth_wall: { zh: "土牆", body: "construct", variant: "wall", element: "impact", size: "medium" },
    war_wolf: { zh: "戰狼", body: "beast", variant: "wolf", element: "prone", size: "medium" },
    hawk: { zh: "鷹隼", body: "beast", variant: "bird", element: "mark", size: "small", trait: "flying" },
    vine: { zh: "藤蔓", body: "plant", element: "prone", size: "medium" },
    war_totem: { zh: "戰意圖騰", body: "totem", variant: "war", element: "summon", size: "medium", trait: "aura" },
    pull_totem: { zh: "吸引圖騰", body: "totem", variant: "pull", element: "impact", size: "medium" },
    plateau_totem: { zh: "高台圖騰", body: "totem", variant: "plateau", element: "high", size: "medium" },
  };
  const BODIES = ["humanoid", "spirit", "construct", "beast", "plant", "totem"];
  /** id 或外觀物件 → 正規化；不認得的體型退回骷髏戰士，不認得的大小退回 medium。 */
  function resolve(spec) {
    let s = typeof spec === "string" ? SUMMONS[spec] : spec;
    if (!s || !BODIES.includes(s.body)) s = SUMMONS.skeleton_warrior;
    return { ...s, k: SIZE[s.size] ?? 1 };
  }

  // ============================== 漂浮靈（火、冰、雷、水） ==============================
  // 水滴形身體（整隻就是大頭）＋元素決定頭頂與身邊的形狀；底下沒有腳，影子較小、身體離地。
  const SPIRIT = {
    ignite: { c: "#ff7a2a", l: "#ffd04a", d: "#c84a14" }, freeze: { c: "#8fd8f5", l: "#e8fbff", d: "#4a9ac0" },
    shock: { c: "#ffd84a", l: "#fff7c0", d: "#b88a10" }, wet: { c: "#4a9aff", l: "#d8f0ff", d: "#2a64c0" },
  };
  function spirit(ctx, s, f) {
    const P = SPIRIT[s.element] ?? SPIRIT.ignite, el = s.element;
    ctx.save(); ctx.translate(0, -7);
    // 身後：元素的小碎片（冰晶、水滴、電光）
    if (el === "freeze") for (const [x, y, h] of [[-13, -22, 3.4], [12.5, -16, 2.8]]) ink(ctx, [[x, y - h], [x + h * 0.55, y], [x, y + h], [x - h * 0.55, y]], P.l, { sharp: true });
    if (el === "wet") for (const [x, y, r] of [[-12, -19, 1.6], [11.6, -25, 1.3]]) ink(ctx, [[x, y - r * 2.2], [x + r, y], [x, y + r], [x - r, y]], P.l);
    if (el === "shock") for (const [x, y, sg] of [[-13, -24, 1], [12.5, -18, -1]]) stroke(ctx, [[x, y - 3], [x + sg * 1.6, y - 0.6], [x - sg * 0.6, y + 0.4], [x + sg * 1.2, y + 3]], 1.1, P.d);
    // 尾巴（下緣收成一個尖）
    ink(ctx, el === "ignite" ? [[-6, -13], [-3, -6], [-1, -9], [1, -3], [3, -9], [6, -13]] : [[-6, -13], [0, -3], [6, -13]], P.c, { sharp: el === "freeze" || el === "shock" });
    // 頭頂：火焰三舌／冰晶三根／雷角兩根／水滴尖
    if (el === "ignite") ink(ctx, [[-8, -28], [-6.6, -38], [-3.4, -32], [0, -44], [3.4, -32], [6.6, -39], [8, -28]], P.c);
    else if (el === "freeze") for (const [x, h, a] of [[-5, 7, -0.35], [0, 10, 0], [5, 7, 0.35]]) { ctx.save(); ctx.translate(x, -31); ctx.rotate(a); ink(ctx, [[-2.2, 2], [0, -h], [2.2, 2]], P.l, { sharp: true }); ctx.restore(); }
    else if (el === "shock") for (const sg of [-1, 1]) ink(ctx, [[sg * 3, -31], [sg * 6.6, -38], [sg * 5, -38.4], [sg * 8.6, -44], [sg * 8.4, -37], [sg * 9.6, -37.4], [sg * 7.4, -30]], P.c, { sharp: true });
    else ink(ctx, [[-7, -27], [0, -40], [7, -27]], P.c);
    // 身體
    const body = [[0, -36], [7.6, -32], [10.6, -23], [8.6, -14.4], [0, -11.4], [-8.6, -14.4], [-10.6, -23], [-7.6, -32]];
    ink(ctx, body, P.c);
    ink(ctx, ellPts(f.ex === null ? 0 : (f.ex ?? 0) * 0.5, -17.6, 5.4, 3.6, 14), P.l, { line: false }); // 肚子亮色（背面在正中）
    if (el === "shock" && f.ex !== null) stroke(ctx, [[-6, -29], [-3.6, -26], [-5.4, -25], [-2.6, -21.6]], 0.8, P.d);
    if (el === "wet") ink(ctx, ellPts(-4.4, -29, 1.4, 2.4, 10), "#ffffff", { line: false });
    // 小手
    for (const sg of [-1, 1]) ink(ctx, ellPts(sg * 10.8, -19.6, 2.2, 2.6, 10), P.c);
    eyesAt(ctx, f, -24, 3.3, (x, y) => qeye(ctx, x, y, "#1d1a22", 1));
    if (f.ex !== null) { ctx.fillStyle = "rgba(220,90,90,0.35)"; ctx.fillRect(f.ex - 6.4, -21, 2, 1.1); ctx.fillRect(f.ex + 4.4, -21, 2, 1.1); }
    ctx.restore();
  }

  // ============================== 構造體（石像、爆裂傀儡、土牆） ==============================
  const STONE = "#8f969a", STONE_D = "#6e7478";
  function golem(ctx, s, f) {
    const acc = KW[s.element] ?? KW.impact, B = f.ex === null;
    for (const sg of [-1, 1]) ink(ctx, [[sg * 1.2, -13], [sg * 8, -13], [sg * 8.4, 0], [sg * 0.8, 0]], STONE_D, { sharp: true }); // 腿
    for (const sg of [-1, 1]) { ink(ctx, [[sg * 10.6, -30], [sg * 17.6, -28.4], [sg * 18.4, -14], [sg * 11.6, -14.6]], STONE_D, { sharp: true }); ink(ctx, ellPts(sg * 15.2, -11.6, 4.4, 3.8, 12), STONE); } // 手臂、拳頭
    ink(ctx, [[-12, -31], [12, -31], [11, -13], [-11, -13]], STONE, { sharp: true }); // 軀幹
    if (!B) stroke(ctx, [[-5, -26], [-2, -22.4], [-4.4, -19.6], [-1, -16]], 1.1, acc); // 胸口發光刻紋（撞擊色）
    else stroke(ctx, [[0, -30], [0, -14]], 0.6, STONE_D);
    for (const sg of [-1, 1]) dot(ctx, sg * 12.6, -31, 2.4, 1.3, "#6a9a4a"); // 肩上青苔
    ink(ctx, [[-8.4, -42], [8.4, -42], [9, -30.6], [-9, -30.6]], STONE, { sharp: true }); // 頭（Q：頭放大）
    if (!B) eyesAt(ctx, f, -36.4, 3.4, (x, y) => { ctx.fillStyle = acc; ctx.fillRect(x - 1.6, y - 0.9, 3.2, 1.8); });
  }
  function bomb(ctx, s, f) {
    const acc = SPIRIT.ignite;
    for (const sg of [-1, 1]) ink(ctx, [[sg * 1.5, -5], [sg * 6, -5], [sg * 6.4, 0], [sg * 1.1, 0]], "#3e3a44", { sharp: true });
    for (const sg of [-1, 1]) ink(ctx, ellPts(sg * 10.6, -11.4, 2.2, 2.6, 10), "#4a4650");
    ink(ctx, ellPts(0, -13, 9.6, 9, 20), "#55505c");
    ctx.save(); smooth(ctx, ellPts(0, -13, 9.6, 9, 20)); ctx.clip();
    stroke(ctx, [[-9, -9], [-5, -11.4], [-6, -6.6], [-1, -8]], 1.5, acc.c); stroke(ctx, [[-9, -9], [-5, -11.4], [-6, -6.6], [-1, -8]], 0.6, acc.l); // 發光裂紋
    stroke(ctx, [[9, -17], [5.4, -15], [6, -19.6]], 1.4, acc.c); stroke(ctx, [[9, -17], [5.4, -15], [6, -19.6]], 0.55, acc.l);
    ctx.restore();
    ink(ctx, [[-2.4, -21], [2.4, -21], [2.2, -23.4], [-2.2, -23.4]], "#8a8478", { sharp: true }); // 引信座
    stroke(ctx, [[0, -23.2], [1.6, -26.6], [4.4, -27.4]], 1.4, "#a8845a");
    ink(ctx, [[4.4, -31.4], [5.6, -28.6], [8.4, -27.4], [5.6, -26.2], [4.4, -23.4], [3.2, -26.2], [0.4, -27.4], [3.2, -28.6]], "#ffd04a", { sharp: true, line: false }); // 火花（平塗星）
    dot(ctx, 4.4, -27.4, 1, 1, "#ffffff");
    eyesAt(ctx, f, -14, 3, (x, y) => qeye(ctx, x, y, acc.l, 0.9));
  }
  function wall(ctx, s, f) {
    const c = "#b08a5a", d = "#7a5a34", top = "#c8a070";
    ink(ctx, [[-20, 0], [-20, -22], [20, -22], [20, 0]], c, { sharp: true }); // 牆身（方正，和石像、藤蔓分得開）
    ink(ctx, [[-21, -22], [-21, -25], [-12, -25.6], [-4, -24.8], [5, -25.8], [13, -25], [21, -25.4], [21, -22]], top, { sharp: true }); // 牆頂
    for (const [i, y] of [-15, -8].entries()) { stroke(ctx, [[-19.6, y], [19.6, y]], 0.7, d); for (const x of i ? [-13, -1, 11] : [-7, 5, 16]) stroke(ctx, [[x, y], [x, y + 7]], 0.7, d); }
    for (const x of [-12, 1, 12]) stroke(ctx, [[x, -22], [x, -15]], 0.7, d);
    for (const x of [-15, 3, 16]) ink(ctx, [[x - 2.4, -24.6], [x - 1, -28], [x, -25.4], [x + 1.4, -28.4], [x + 2.4, -24.8]], "#6a9a4a", { sharp: true, line: false }); // 牆頭的草
    stroke(ctx, [[6, -21.4], [8, -18], [6.6, -15.4]], 0.7, d); // 一道裂縫
  }

  // ============================== 野獸（戰狼、鷹隼）：側面，Q 大頭 ==============================
  function wolf(ctx, s) {
    const P = { base: "#7a7a82", d: "#5e5e66", l: "#b8b8c0" }, acc = KW[s.element] ?? KW.prone;
    for (const x of [-12, 6]) ink(ctx, [[x, -12], [x + 4, -12], [x + 4.4, 0], [x - 0.4, 0]], P.d);
    ink(ctx, [[-14, -20], [-22, -25], [-26, -21], [-20, -17], [-13, -15]], P.base);
    ink(ctx, [[-16, -12], [-17, -20], [-10, -25], [4, -25], [12, -22], [13, -12], [0, -10]], P.base);
    ink(ctx, ellPts(-1, -13.4, 9, 2.4, 14), P.l, { line: false }); // 肚子亮色
    for (const x of [-9, 8]) ink(ctx, [[x, -13], [x + 4, -13], [x + 4.6, 0], [x - 0.4, 0]], P.base);
    ctx.save(); ctx.translate(12, -22); ctx.scale(1.3, 1.3); ctx.translate(-12, 22); // Q 大頭：以頸為中心放大 1.3（同 qCreature hound）
    ink(ctx, [[12, -29], [13, -36], [16.4, -30]], P.d, { sharp: true });
    ink(ctx, [[8, -22], [11, -30], [17, -31], [22, -28], [28, -26], [28, -23], [21, -21], [14, -18]], P.base);
    dot(ctx, 28, -25, 0.9, 0.8, OUT); beye(ctx, 19, -27.4, "#ffd23a"); ink(ctx, [[23.2, -22.2], [24, -20.2], [24.8, -22.2]], "#f4ecd8", { sharp: true, line: false });
    ctx.restore();
    ink(ctx, [[7.4, -24.6], [12.6, -27], [14.6, -19], [9.4, -17.4]], acc); // 戰狼的頸甲（元素色皮項圈）
    dot(ctx, 11.4, -21.6, 0.9, 0.9, "#e8bb48");
  }
  function hawk(ctx, s) {
    const c = "#8a6a40", d = "#5e4628", acc = KW[s.element] ?? KW.mark;
    ctx.save(); ctx.translate(0, -10);
    ink(ctx, [[-2, -4], [-12, -14], [-20, -15], [-16, -10], [-21, -9], [-13, -4], [-4, 2]], d, { sharp: true }); // 遠側翅（平飛）
    ink(ctx, [[-8, 2], [-17, 6], [-15, 1.4], [-18.6, 2.4], [-9, -1]], d, { sharp: true, line: false });
    ink(ctx, ellPts(0, 0, 8.6, 5.4, 16), c);
    ink(ctx, ellPts(1.4, 1.8, 5.6, 2.6, 12), "#f0e6d0", { line: false });
    ink(ctx, [[1, -3], [9, -15], [18, -17], [14, -11], [20, -10], [12, -4], [3, 2]], c, { sharp: true }); // 近側翅
    ink(ctx, [[13, -12.6], [18, -17], [20, -10], [15.6, -10.6]], acc, { sharp: true }); // 翼尖：標記色
    ctx.save(); ctx.translate(7, -1); ctx.scale(1.25, 1.25); ctx.translate(-7, 1); // Q 大頭
    ink(ctx, ellPts(9, -4, 4.2, 4.2, 12), c);
    ink(ctx, [[12.4, -5.2], [16.6, -3.2], [12.4, -1.2]], "#e8bb48", { sharp: true, line: false });
    beye(ctx, 10.6, -5, "#ffd23a", 0.8); stroke(ctx, [[8.4, -7.6], [12, -6.8]], 0.7, acc);
    ctx.restore();
    for (const x of [-2, 2.6]) stroke(ctx, [[x, 4.6], [x, 7.6]], 1.2, "#e8bb48");
    ctx.restore();
  }

  // ============================== 植物（藤蔓）：貼地、半透明 0.9 ==============================
  function vine(ctx) {
    const g = "#4f8a3a", l = "#7ab84a";
    for (const pts of [[[0, -2], [-7, -3], [-13, -1], [-16, -5], [-13, -8]], [[0, -2], [6, -5], [12, -3], [15, -7], [12.4, -10]], [[0, -2], [-2, -8], [1, -12], [4, -10]]]) limb(ctx, pts, 1.6, g);
    for (const [x, y, a] of [[-9, -4.4, -0.6], [8.6, -6, 0.5], [-1.6, -10, -0.2], [13.6, -2.2, 1.2], [-14, -2.4, -1.4]]) { ctx.save(); ctx.translate(x, y); ctx.rotate(a); ink(ctx, [[0, 0], [-1.8, -2.4], [0, -4.6], [1.8, -2.4]], l); ctx.restore(); }
    for (const [x, y] of [[-4, -3.4], [5, -4.4]]) ink(ctx, [[x - 0.8, y], [x, y - 2], [x + 0.8, y]], "#e8e0c8", { sharp: true, line: false }); // 刺
  }

  // ============================== 圖騰（戰意、吸引、高台） ==============================
  function totem(ctx, s, f) {
    const wood = "#8a5a32", wl = "#a8763e", B = f.ex === null;
    for (const [x, r] of [[-6, 3], [5.6, 2.6], [0, 3.4]]) ink(ctx, ellPts(x, -1.4, r, r * 0.6, 10), "#8a847e"); // 底座石頭
    ink(ctx, [[-3.2, -1], [-3.2, -34], [3.2, -34], [3.2, -1]], wood, { sharp: true });
    ink(ctx, [[-7, -28], [7, -28], [6.4, -13], [-6.4, -13]], wl, { sharp: true }); // 雕臉的木塊
    if (!B) { eyesAt(ctx, f, -23.6, 2.6, (x, y) => { ctx.fillStyle = "#2b1e16"; ctx.fillRect(x - 1.2, y - 1.4, 2.4, 2.8); }); ctx.fillStyle = "#2b1e16"; ctx.fillRect((f.ex ?? 0) - 2.6, -17.4, 5.2, 1.4); }
    else stroke(ctx, [[0, -27], [0, -14]], 0.6, wood);
    if (s.variant === "war") { stroke(ctx, [[0, -34], [0, -46]], 1.6, wood); ink(ctx, [[0.6, -46], [15, -42.6], [11, -40.4], [15, -38], [0.6, -36.4]], "#d23c3c", { sharp: true }); }
    else if (s.variant === "pull") { const c = "#a86ad8"; ink(ctx, ellPts(0, -40, 7.4, 7.4, 20), c); stroke(ctx, [[0, -40], [2.6, -41], [2.4, -43.4], [-1, -44], [-4, -41.6], [-3.4, -37.4], [1, -35.6], [5, -37.6]], 0.9, "#e8d0ff"); }
    else if (s.variant === "plateau") { ink(ctx, [[-10.6, -38], [10.6, -38], [11.4, -33.4], [-11.4, -33.4]], "#b8b0a0", { sharp: true }); if (!B) ink(ctx, [[-3, -34.6], [0, -37.2], [3, -34.6], [1.6, -34.6], [0, -35.8], [-1.6, -34.6]], KW.high, { sharp: true, line: false }); stroke(ctx, [[-2, -33.6], [-2, -32]], 1.2, wood); }
  }
  function aura(ctx, rx) { ctx.save(); ctx.strokeStyle = "#7dffb0"; ctx.globalAlpha = 0.9; ctx.lineWidth = 1.1; ctx.setLineDash([3, 2.4]); ctx.beginPath(); ctx.ellipse(0, 0, rx, rx * 0.3, 0, 0, TAU); ctx.stroke(); ctx.restore(); }

  // ============================== 人形（QDoll） ==============================
  const PD = window.PaperDoll, I = (slot, kind, m) => ({ slot, kind, ...m });
  const HUMAN = {
    skeleton: { unit: { look: { skin: "#e9e3cf", skull: true, hair: "none", eyes: "#2a1030", eyeStyle: "big", pants: "#d9d2bd", belt: "#5a4a3a" }, gear: { body: I("body", "shirt", { color: "#ddd6c2" }), main_hand: I("main_hand", "sword", { material: "iron", color: "#9a8a76" }), off_hand: I("off_hand", "shield_round", { material: "wood", color: "#7a5a3a" }) } }, ids: ["ribs"] },
    shade: { unit: { look: { skin: "#7a6a9a", hair: "none", eyes: "#e8d0ff", eyeStyle: "big" }, gear: { head: I("head", "hood", { color: "#2e2440" }), body: I("body", "leather", { color: "#3a3050" }), feet: I("feet", "boots", { color: "#2a2236" }), main_hand: I("main_hand", "paired", { material: "steel" }) } }, tint: "#6a3aa8", t: 0.28, alpha: 0.74 },
    afterimage: { unit: null, tint: "#8fd0ff", t: 0.5, alpha: 0.55, trail: true },
    guardian: { unit: { look: { skin: "#f4ecd8", hair: "short", hairColor: "#e8d8a0", eyes: "#6a5a2a" }, gear: { head: I("head", "helmet", { color: "#e8dcae" }), body: I("body", "plate", { color: "#e8dcae" }), feet: I("feet", "greaves", { color: "#d8cc9e" }), main_hand: I("main_hand", "sword", { material: "gold" }), off_hand: I("off_hand", "shield_kite", { color: "#f0e6c0" }) } }, tint: "#fff2b0", t: 0.3, alpha: 0.86 },
  };
  const VIEW = { south: ["front", false], north: ["back", false], east: ["side", false], west: ["side", true] };
  /** QDoll 畫到離屏 → 整隻染色、半透明 → 貼回（不加外光）。 */
  function doll(ctx, h, summoner, view, west, cx, cy, k) {
    const unit = h.unit ?? summoner ?? PD.TEMPLATES.hero_fighter, W = Math.ceil(140 * k), H = Math.ceil(120 * k);
    const c = document.createElement("canvas"); c.width = W * 2; c.height = H * 2; const g = c.getContext("2d");
    const ox = W, oy = H * 2 - 16 * k * 2;
    if (h.ids && window.QGearExtra) window.QGearExtra.stamp(g, unit, h.ids, view, ox, oy, k * 2, west); else window.QDoll.stamp(g, unit, view, ox, oy, k * 2, west);
    if (h.tint) { g.globalCompositeOperation = "source-atop"; g.globalAlpha = h.t; g.fillStyle = h.tint; g.fillRect(0, 0, c.width, c.height); }
    ctx.save();
    if (h.trail) { ctx.globalAlpha = h.alpha * 0.4; ctx.drawImage(c, cx - W / 2 - (view === "side" ? (west ? -7 : 7) * k : 5 * k), cy - (H - 16 * k), W, H); } // 殘影：身後再一個更淡的影
    ctx.globalAlpha = h.alpha ?? 1; ctx.drawImage(c, cx - W / 2, cy - (H - 16 * k), W, H); ctx.restore();
  }

  // ============================== 貼上 ==============================
  const FACE = { south: { ex: 0 }, east: { ex: 2.4 }, west: { ex: -2.4 }, north: { ex: null } };
  /**
   * 畫一隻召喚物。spec＝召喚物 id 或外觀物件；facing＝south／east／west／north（不認得當 south）；k＝每單位幾 px（和 QDoll.stamp 的 size 同義）。
   * opts.summoner＝召喚者的 QDoll unit（殘影分身複製它）；opts.ring＝false 不畫陣營環。
   */
  function stamp(ctx, spec, facing, cx, cy, k = 1, opts = {}) {
    const s = resolve(spec), fc = FACE[facing] ? facing : "south", sz = s.k;
    ctx.save(); ctx.translate(cx, cy);
    const ringOn = opts.ring !== false && !(s.body === "construct" && s.variant === "wall");
    if (ringOn) { ctx.save(); ctx.scale(k * Math.max(1, sz * 0.9), k * Math.max(1, sz * 0.9)); summonRing(ctx, 13); if (s.trait === "aura") aura(ctx, 17); ctx.restore(); }
    if (s.body === "humanoid") { ctx.restore(); const [v, w] = VIEW[fc]; doll(ctx, HUMAN[s.variant] ?? HUMAN.skeleton, opts.summoner, v, w, cx, cy, k * sz); return; }
    ctx.scale(k * sz, k * sz);
    const flying = s.trait === "flying", hover = s.body === "spirit";
    if (s.trait === "puddle") { ctx.save(); ctx.globalAlpha = 0.45; ctx.fillStyle = "#4aa8ff"; ctx.beginPath(); ctx.ellipse(0, 0, 14, 4.2, 0, 0, TAU); ctx.fill(); ctx.restore(); }
    if (s.body !== "plant") shadow(ctx, hover ? 7 : flying ? 8 : s.variant === "wall" ? 20 : 10, 0.2, hover || flying ? 0.22 : 0.3);
    const side = s.body === "beast", west = side ? fc === "west" || fc === "north" : false, f = FACE[fc];
    ctx.scale(west ? -1 : 1, 1);
    if (flying) ctx.translate(0, -22);
    const fn = (g) => {
      if (s.body === "spirit") spirit(g, s, f);
      else if (s.body === "construct") (s.variant === "bomb" ? bomb : s.variant === "wall" ? wall : golem)(g, s, f);
      else if (s.body === "beast") (s.variant === "bird" ? hawk : wolf)(g, s);
      else if (s.body === "plant") vine(g, s);
      else totem(g, s, f);
    };
    lay(ctx, sz, fn, { alpha: s.body === "plant" ? 0.9 : undefined });
    ctx.restore();
  }
  return { stamp, resolve, SUMMONS, KW, SIZE, H: { smooth, poly, ink, stroke, limb, dot, beye, qeye, eyesAt, lay, shadow, mix, dark, light, ellPts, OUT, TAU, BOX } };
})();
