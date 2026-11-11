// qIcons.js：小圖示的 Q 版畫法（風格樣張，畫圖 agent 2026-11-11）。範圍只有六類：武器、技能、物品、狀態、HUD、事件卡。
// 規則寫在 docs/art/Q版小圖示樣張.md 第 2 節；這裡是第一批代表樣本（38 個），不是全量。
// 畫法和 qDoll.js 同一套語言：平塗色塊（不描內線、不排線）＋一階亮面＋一階暗面，整個圖樣外面包一圈剪影外框（色 #16121a，和人物同色；做法同 qDoll.stamp：先畫色塊，再把剪影往外長一圈墊在底下）。
// 每個圖樣畫在 48×48 的格子裡（可用範圍 3～45，外圈留給外框）；d(c, o) 畫主體（會被包外框），pre 畫在外框底下（光暈），post 畫在最上面（閃光、速度線，不包外框）。
// o.small＝顯示尺寸 ≤ 24px（省掉小零件），o.tiny＝≤ 14px（只留主形與一階亮面）。外框、稀有度框、狀態框、事件卡圓環都沿用現行樣式，這裡只換框裡的圖。
window.QIcons = (() => {
  const TAU = Math.PI * 2, OUT = "#16121a";
  // 材質色與人物同一份（paperdoll.js 的 MATERIAL、qDoll.js 的武器色）
  const M = { steel: "#c3ccd6", steelD: "#7d8794", iron: "#8d969f", ironD: "#5a6169", wood: "#a06a36", woodD: "#6a4420", shaft: "#6a4420", grip: "#4a3020", brass: "#8a6a2a", gold: "#d8b04a", goldL: "#f6d878", leather: "#8a5a32", leatherD: "#5e3b1f", skin: "#f1c9a5", cream: "#f2e6c8", arcane: "#9a86ff" };
  // 元素色照 client/src/render/palette.ts（火 #ff6a1a、雷 #fff36b…），和技能特效、人物法杖的光球同一份
  const EL = { fire: ["#ff6a1a", "#ffd23f"], ice: ["#8fe3ff", "#ffffff"], lightning: ["#fff36b", "#ffffff"], poison: ["#7ddc3a", "#d6f59a"], holy: ["#ffd75e", "#fff6c8"], shadow: ["#9a6ad8", "#d2b0ff"], wind: ["#7fe0c0", "#dcfff1"], earth: ["#b0814a", "#f0c890"], water: ["#4aa8ff", "#cfe8ff"] };
  const HI = "rgba(255,255,255,0.45)", HI2 = "rgba(255,255,255,0.8)", SH = "rgba(0,0,0,0.22)";

  // ---------------- 畫法小工具 ----------------
  function mix(a, b, t) { const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)); const A = p(a), B = p(b); return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, "0")).join(""); }
  const f = (c, col, path) => { c.beginPath(); c.fillStyle = col; path(c); c.fill(); };
  const rr = (c, col, x, y, w, h, r) => f(c, col, () => c.roundRect(x, y, w, h, r));
  const ci = (c, col, x, y, r) => f(c, col, () => c.arc(x, y, r, 0, TAU));
  const el = (c, col, x, y, rx, ry, rot = 0) => f(c, col, () => c.ellipse(x, y, rx, ry, rot, 0, TAU));
  /** 多邊形；round＞0 時用同色粗線把角磨圓（外形往外長 round 單位）。 */
  function poly(c, col, pts, round = 0) {
    c.beginPath(); pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.closePath(); c.fillStyle = col; c.fill();
    if (round) { c.strokeStyle = col; c.lineWidth = round * 2; c.lineJoin = "round"; c.stroke(); }
  }
  function ln(c, col, w, pts, join = "round") { c.beginPath(); pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.strokeStyle = col; c.lineWidth = w; c.lineCap = join === "round" ? "round" : "butt"; c.lineJoin = join; c.miterLimit = 6; c.stroke(); }
  function starPts(x, y, R, r, n, rot = -Math.PI / 2) { const p = []; for (let i = 0; i < n * 2; i++) { const a = rot + (i * Math.PI) / n, q = i % 2 ? r : R; p.push([x + Math.cos(a) * q, y + Math.sin(a) * q]); } return p; }
  function glow(c, x, y, r, col, a = 0.5) { const g = c.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, col); g.addColorStop(1, mix(col, "#000000", 0) + "00"); c.save(); c.globalAlpha = a; c.fillStyle = g; c.beginPath(); c.arc(x, y, r, 0, TAU); c.fill(); c.restore(); }
  /** 火焰外形：中心 (x,y)、高 20s、寬 14s，尖端朝上，左邊一小撮分岔。 */
  function flame(c, col, x, y, s) {
    c.save(); c.translate(x, y); c.scale(s, s); c.beginPath(); c.moveTo(0.5, -10); c.bezierCurveTo(1.5, -5, 7, -3, 7, 3); c.bezierCurveTo(7, 7.5, 3.5, 10, 0, 10); c.bezierCurveTo(-3.5, 10, -7, 7.5, -7, 3);
    c.bezierCurveTo(-7, 0, -5, -2, -4.2, -4.8); c.bezierCurveTo(-3.5, -2.5, -2.6, -2, -1.8, -2.4); c.bezierCurveTo(-2.5, -5, -1.5, -8, 0.5, -10); c.closePath(); c.fillStyle = col; c.fill(); c.restore();
  }
  /** 水滴外形：中心 (x,y)、高 20s、寬 14s。 */
  function drop(c, col, x, y, s) { c.save(); c.translate(x, y); c.scale(s, s); c.beginPath(); c.moveTo(0, -10); c.bezierCurveTo(4, -4, 7, 0, 7, 4); c.bezierCurveTo(7, 8, 3.5, 10, 0, 10); c.bezierCurveTo(-3.5, 10, -7, 8, -7, 4); c.bezierCurveTo(-7, 0, -4, -4, 0, -10); c.closePath(); c.fillStyle = col; c.fill(); c.restore(); }
  function heart(c, col, x, y, s) { c.save(); c.translate(x, y); c.scale(s, s); c.beginPath(); c.moveTo(0, 7); c.bezierCurveTo(-11, -1, -7, -10, 0, -4.5); c.bezierCurveTo(7, -10, 11, -1, 0, 7); c.closePath(); c.fillStyle = col; c.fill(); c.restore(); }
  function sparkle(c, col, x, y, R) { poly(c, col, starPts(x, y, R, R * 0.3, 4)); }

  // ---------------- 剪影外框 ----------------
  const blank = (w, h = w) => { const cv = document.createElement("canvas"); cv.width = w; cv.height = h; return cv; };
  function dilate(src, r) {
    // 剪影往一圈方向各位移 r（外圈）與 r/2（內圈）疊起來。圖示的外框只有 1～10 個裝置像素，不用 qDoll 的逐步膨脹：
    // 逐步膨脹每一步都是不到 1px 的位移，邊緣的半透明像素會被一步步放大，外框會比指定的粗兩三倍。
    const w = src.width, h = src.height, o = blank(w, h), x = o.getContext("2d"), n = Math.max(16, Math.ceil(r * 5));
    for (const q of [1, 0.5]) for (let i = 0; i < n; i++) { const t = (i / n) * TAU; x.drawImage(src, Math.cos(t) * r * q, Math.sin(t) * r * q); }
    x.drawImage(src, 0, 0); x.globalCompositeOperation = "source-in"; x.fillStyle = OUT; x.fillRect(0, 0, w, h); return o;
  }
  /** 圖樣裡前後重疊的零件（交叉的兩把劍、壓在盾上的星）：後畫的那一件自己先包一圈外框，兩件才分得開。 */
  function halo(c, o, fn) {
    if (o.flat) { fn(c); return; } /* 量整體剪影的那一遍：不畫內圈外框，免得整體外框在這裡變兩倍粗 */
    const cv = blank(c.canvas.width, c.canvas.height), x = cv.getContext("2d"); x.setTransform(c.getTransform()); fn(x);
    c.save(); c.setTransform(1, 0, 0, 1, 0, 0); if (o.owPx > 0) c.drawImage(dilate(cv, o.owPx), 0, 0); c.drawImage(cv, 0, 0); c.restore();
  }
  /** 外框粗細（CSS px）：顯示邊長的 5%，最細 1px、最粗 1.6px——和戰場上人物的外框（約 1.5px）一樣粗：20px 圖示是 1px、24px 是 1.2px、32px 以上都是 1.6px。 */
  const outlinePx = (px) => Math.min(1.6, Math.max(1, px * 0.05));
  /** 只畫圖樣（不含框）：回傳邊長 px×res 的 canvas。 */
  function render(def, px, res, opt = {}) {
    const S = Math.max(4, Math.round(px * res)), o = { small: px <= 24, tiny: px <= 14, owPx: (opt.ow ?? outlinePx(px)) * res };
    const main = blank(S), m = main.getContext("2d"); m.scale(S / 48, S / 48); def.d(m, o);
    const out = blank(S), x = out.getContext("2d");
    if (def.pre) { x.save(); x.scale(S / 48, S / 48); def.pre(x, o); x.restore(); }
    if (o.owPx > 0) { const solid = blank(S), s = solid.getContext("2d"); s.scale(S / 48, S / 48); def.d(s, { ...o, flat: true }); x.drawImage(dilate(solid, o.owPx), 0, 0); }
    x.drawImage(main, 0, 0);
    if (def.post) { x.save(); x.scale(S / 48, S / 48); def.post(x, o); x.restore(); }
    return out;
  }

  // =====================================================================
  // 武器：握把在左下、作用端在右上（照現行小圖示的慣例，一律 45° 斜放；拳套、盾直立）。
  // 造型與配色照 qDoll.js 的 QW（人物手上的那一把），只把比例加粗，並把同類之間的差別誇大（見各把的註解）。
  // 斜放的武器畫在「握把在 +y、作用端在 −y」的直立座標，長度 ±21（放在米色圓章裡不超出圓）。
  // =====================================================================
  const diag = (c, fn) => { c.save(); c.translate(24, 24); c.rotate(Math.PI / 4); fn(c); c.restore(); };
  /** 單手劍：劍身細、劍尖收得長；銅色小護手、短握柄、圓柄頭（QW.sword：鋼刃、#8a6a2a 護手、#4a3020 握柄）。 */
  function swordArt(c, o) {
    poly(c, M.steel, [[-3.3, 5], [-3.3, -14], [0, -21], [3.3, -14], [3.3, 5]]);
    f(c, SH, () => { c.moveTo(0.9, 5); c.lineTo(0.9, -18.8); c.lineTo(3.3, -14); c.lineTo(3.3, 5); c.closePath(); });
    f(c, HI2, () => c.rect(-2.3, -13.5, 1.3, 17.5));
    rr(c, M.brass, -8, 4.6, 16, 3.8, 1.8);
    rr(c, M.grip, -1.9, 8.4, 3.8, 8.4, 1);
    ci(c, M.brass, 0, 18.2, 2.8);
  }
  /** 雙手劍：劍身寬一倍、劍尖鈍、中間一道血槽；金色大護手兩端有圓頭；握柄長（兩手握）纏兩道金箍（QW.greatsword：寬 4 的刃、#d8b04a 金護手、長握柄）。 */
  function greatswordArt(c, o) {
    poly(c, M.steel, [[-5.6, 1.5], [-5.6, -16], [0, -21.5], [5.6, -16], [5.6, 1.5]]);
    f(c, SH, () => { c.moveTo(2.2, 1.5); c.lineTo(2.2, -19.4); c.lineTo(5.6, -16); c.lineTo(5.6, 1.5); c.closePath(); });
    f(c, HI2, () => c.rect(-4.4, -15.5, 1.5, 16));
    rr(c, M.steelD, -0.8, -15, 1.6, 15, 0.8);
    rr(c, M.gold, -11, 1, 22, 4, 2); ci(c, M.gold, -11, 3, 2.7); ci(c, M.gold, 11, 3, 2.7);
    if (!o.small) f(c, M.goldL, () => c.rect(-9, 1.6, 18, 1));
    rr(c, M.grip, -2.1, 5, 4.2, 12.5, 1);
    rr(c, M.gold, -2.5, 8, 5, 1.7, 0.6); rr(c, M.gold, -2.5, 12.2, 5, 1.7, 0.6);
    poly(c, M.gold, [[0, 16], [3.2, 19], [0, 22], [-3.2, 19]], 0.4);
  }
  /** 魔導劍：淡紫的刃、中間一道發光的晶紫導槽、三道符紋橫槓；護手是齒輪形、中心一顆晶紫寶石（QW.arcane_blade 同樣的零件）。 */
  function arcaneArt(c, o) {
    poly(c, "#dcd8f4", [[-3.6, 3], [-3.6, -14.5], [0, -21], [3.6, -14.5], [3.6, 3]]);
    rr(c, M.arcane, -1.2, -17.5, 2.4, 20, 1.2);
    if (!o.tiny) for (const y of [-13.4, -8.8, -4.2]) rr(c, "#f6f0ff", -2.7, y, 5.4, 1.4, 0.5);
    poly(c, "#b08a4a", starPts(0, 5.4, 7.6, 5.3, 8, 0), 0.5);
    ci(c, M.arcane, 0, 5.4, 2.7); ci(c, HI2, -0.8, 4.6, 0.9);
    rr(c, M.grip, -1.8, 11, 3.6, 6.6, 1);
    poly(c, M.arcane, [[0, 16.6], [2.6, 19.2], [0, 21.8], [-2.6, 19.2]], 0.3);
  }
  /** 弓：木弓臂彎向作用端、白弦、皮纏弓把，搭一支箭（QW.bow：木色弓臂、#e8e8e8 弦、#4a3020 弓把、#c8a070 箭桿、鋼箭頭）。 */
  function bowArt(c, o) {
    ln(c, "#e8e8e8", 1.5, [[-17, 7], [0, 10.5], [17, 7]]);
    c.beginPath(); c.moveTo(-17, 7); c.quadraticCurveTo(0, -24, 17, 7); c.strokeStyle = M.wood; c.lineWidth = 4.6; c.lineCap = "round"; c.stroke();
    c.beginPath(); c.moveTo(-15.2, 3.6); c.quadraticCurveTo(-0.4, -20.4, 13.4, 1.2); c.strokeStyle = HI; c.lineWidth = 1.1; c.stroke();
    ci(c, M.woodD, -17, 7, 2.5); ci(c, M.woodD, 17, 7, 2.5);
    ln(c, "#c8a070", 2.2, [[0, 10.5], [0, -15]]);
    poly(c, M.steel, [[-3.4, -14], [0, -21.5], [3.4, -14]], 0.3);
    if (!o.tiny) { poly(c, "#c0392b", [[0, 5.5], [-3, 9.5], [-3, 12.5], [0, 9.5]]); poly(c, "#c0392b", [[0, 5.5], [3, 9.5], [3, 12.5], [0, 9.5]]); }
    rr(c, M.grip, -3, -11.6, 6, 6.6, 1.8);
  }
  /** 法杖：木杖身、杖頭一顆元素色光球、左上白色高光（QW.staff 的三樣零件與配色；光球色＝元素色）；球裡多畫一撮亮色，球下加托座，握的地方纏皮。 */
  const staffArt = (element) => (c, o) => {
    const [e1, e2] = EL[element] ?? ["#c8bcff", "#ffffff"];
    rr(c, M.shaft, -1.9, -7, 3.8, 28, 1.4);
    if (!o.small) f(c, HI, () => c.rect(-1.2, -4, 0.9, 22));
    rr(c, M.grip, -2.5, 6.5, 5, 6.5, 1.2);
    rr(c, M.brass, -2.7, 18.6, 5.4, 3.2, 1.2);
    poly(c, M.brass, [[-5.6, -8.6], [5.6, -8.6], [2.8, -4.6], [-2.8, -4.6]], 0.6);
    ci(c, e1, 0, -13.6, 6.6);
    if (element === "fire") flame(c, e2, 0.3, -12.6, 0.46); else if (element === "lightning") poly(c, e2, [[1.5, -18.5], [-3, -12.6], [0, -12.6], [-1.5, -8.6], [3, -14.4], [0, -14.4]]); else poly(c, e2, starPts(0, -13.2, 4.4, 1.6, 4));
    ci(c, HI2, -2.9, -16.4, 1.5);
  };
  /** 鎚：一大塊長方形鎚頭橫在柄頂（不是圓球、沒有釘），中間一道暗色箍（QW.hammer 預設造型：#6a4420 柄、鐵色方頭、暗色橫帶）。 */
  function hammerArt(c, o) {
    rr(c, M.shaft, -1.9, -10, 3.8, 31, 1.4);
    rr(c, M.grip, -2.5, 9.5, 5, 8, 1.2);
    rr(c, M.ironD, -2.8, 18.8, 5.6, 3, 1.2);
    rr(c, M.iron, -9.2, -19.5, 18.4, 11.4, 2.4);
    f(c, M.ironD, () => c.rect(-1.9, -19.5, 3.8, 11.4));
    f(c, SH, () => c.roundRect(-9.2, -12, 18.4, 3.9, [0, 0, 2.4, 2.4]));
    f(c, HI2, () => c.rect(-7.4, -18.1, 4.6, 1.5)); f(c, HI2, () => c.rect(2.8, -18.1, 4.6, 1.5));
  }
  /** 拳套：握緊的鐵拳正面直立——四塊指節鐵片、拇指橫壓在前、皮護腕（QW.gauntlet 是包住拳頭的鋼色圓拳；不畫尖刺）。 */
  function fistArt(c, o) {
    rr(c, M.leather, 15.5, 30, 17, 12.5, 3); f(c, M.leatherD, () => c.rect(15.5, 37.6, 17, 2.2));
    rr(c, M.iron, 8.5, 12.5, 31, 20.5, 7.5);
    for (let i = 0; i < 4; i++) rr(c, M.steel, 9.6 + i * 7.4, 8.6, 6.6, 9.4, 3);
    if (!o.tiny) for (let i = 1; i < 4; i++) f(c, M.ironD, () => c.rect(8.6 + i * 7.4, 17.6, 1.4, 7));
    f(c, HI2, () => c.rect(11.2, 10.4, 3.2, 1.4));
    halo(c, o, (x) => { rr(x, M.iron, 9.5, 23.5, 19.5, 8.6, 4.3); f(x, HI, () => x.rect(12.5, 25, 11, 1.3)); });
  }
  /** 塔盾：高的長方形木盾、鋼邊、兩道鐵箍、中央盾心（qDoll 的塔盾：#6a4a2e 木色、鋼色盾緣 #c3ccd6、高長方形）。cx,cy＝中心。 */
  function towerShield(c, o, cx = 24, cy = 24, k = 1, rot = 0) {
    c.save(); c.translate(cx, cy); c.rotate(rot); c.scale(k, k);
    rr(c, M.steel, -11.5, -18.5, 23, 37, 4.5);
    rr(c, "#6a4a2e", -8.7, -15.7, 17.4, 31.4, 2.2);
    f(c, "#855e3a", () => c.roundRect(-8.7, -15.7, 5.6, 31.4, [2.2, 0, 0, 2.2]));
    f(c, "#4e3620", () => c.roundRect(4.6, -15.7, 4.1, 31.4, [0, 2.2, 2.2, 0]));
    f(c, M.iron, () => c.rect(-8.7, -10.4, 17.4, 2.6)); f(c, M.iron, () => c.rect(-8.7, 8.2, 17.4, 2.6));
    ci(c, M.steel, 0, 0, 4.6); ci(c, HI2, -1.4, -1.4, 1.5);
    c.restore();
  }
  const WEAPON = {
    sword: { zh: "單手劍", d: (c, o) => diag(c, (x) => swordArt(x, o)) },
    greatsword: { zh: "雙手劍", d: (c, o) => diag(c, (x) => greatswordArt(x, o)) },
    arcane_blade: { zh: "魔導劍", d: (c, o) => diag(c, (x) => arcaneArt(x, o)), pre: (c) => glow(c, 29, 19, 15, M.arcane, 0.55), post: (c, o) => { if (!o.small) { sparkle(c, "#f6f0ff", 39, 21, 2.6); sparkle(c, "#f6f0ff", 27, 8.5, 2); } } },
    bow: { zh: "弓", d: (c, o) => diag(c, (x) => bowArt(x, o)) },
    fire_staff: { zh: "火焰法杖", d: (c, o) => diag(c, (x) => staffArt("fire")(x, o)), pre: (c) => glow(c, 33.6, 14.4, 12, "#ff6a1a", 0.6) },
    hammer: { zh: "鎚", d: (c, o) => diag(c, (x) => hammerArt(x, o)) },
    fist: { zh: "拳套", d: fistArt },
    tower_shield: { zh: "塔盾", d: (c, o) => towerShield(c, o) },
  };

  // =====================================================================
  // 技能：框（外形＝技能類型、顏色＝稀有度）與元素底色照現行，只把框裡的白色符號換成 Q 版的「道具＋動作」。
  // 道具來自技能的武器條件（wielding_weapon）、weapon_req 或元素；動作來自核心效果（瞬步、擊倒、推開、緩速…）。
  // =====================================================================
  function daggerArt(c) { // 直立座標，尖端朝 −y
    poly(c, M.steel, [[-3.2, 2], [-3.2, -9], [0, -18], [3.2, -9], [3.2, 2]]);
    f(c, SH, () => { c.moveTo(0.8, 2); c.lineTo(0.8, -15.6); c.lineTo(3.2, -9); c.lineTo(3.2, 2); c.closePath(); });
    f(c, HI2, () => c.rect(-2.2, -9, 1.2, 10));
    rr(c, M.brass, -6.6, 1.6, 13.2, 3.4, 1.6); rr(c, M.grip, -1.9, 5, 3.8, 8.6, 1.2); ci(c, M.brass, 0, 14.6, 2.5);
  }
  const daggerAt = (c, x, y, col) => { c.save(); c.translate(x, y); c.rotate(Math.PI / 4); c.scale(1.04, 1.04); if (col) { poly(c, col, [[-3.2, 2], [-3.2, -9], [0, -18], [3.2, -9], [3.2, 2]]); rr(c, col, -6.6, 1.6, 13.2, 3.4, 1.6); rr(c, col, -1.9, 5, 3.8, 8.6, 1.2); ci(c, col, 0, 14.6, 2.5); } else daggerArt(c); c.restore(); };
  function bullet(c, x, y, k) { c.save(); c.translate(x, y); c.scale(k, k); rr(c, "#e8bb48", -7, -3, 9, 6, 1.2); f(c, "#b06a3c", () => { c.moveTo(2, -3); c.quadraticCurveTo(7.5, -2.6, 8.4, 0); c.quadraticCurveTo(7.5, 2.6, 2, 3); c.closePath(); }); f(c, "#9c7420", () => c.rect(-7, -3, 1.8, 6)); f(c, HI2, () => c.rect(-4.6, -2, 6, 1.1)); c.restore(); }
  const SKILL = {
    skill_shadow_backstab: { zh: "瞬步背刺", meta: { el: "physical", rarity: "rare" },
      // 匕首（近戰）＋握柄後面拖著一道紫色的殘影尾巴（瞬步衝過去）＋刃尖的白色刺擊閃光（背刺）
      pre: (c, o) => { c.save(); c.translate(28.5, 19.5); c.rotate(Math.PI / 4); poly(c, "rgba(180,140,255,0.8)", [[-8, -3], [8, -3], [0, 27]], 0.6); poly(c, "rgba(236,224,255,0.75)", [[-4.2, 3], [4.2, 3], [0, 21]]); c.restore(); },
      d: (c) => daggerAt(c, 28.5, 19.5),
      post: (c, o) => { sparkle(c, "#ffffff", 41.5, 6.5, o.small ? 4.2 : 5); } },
    skill_tower_slam: { zh: "塔盾猛擊", meta: { el: "physical", rarity: "rare" },
      // 塔盾（武器條件）往右撞出去＋右上的撞擊星（擊倒）＋左邊三道速度線
      d: (c, o) => { towerShield(c, o, 21, 25.5, 0.86, 0.2); halo(c, o, (x) => { poly(x, "#ffd23f", starPts(37.5, 15.5, 9.2, 4.4, 7, -1.2), 0.4); poly(x, "#ffffff", starPts(37.5, 15.5, 4.4, 2.2, 7, -1.2)); }); },
      post: (c, o) => { for (const [y, x0, x1] of [[14, 2.5, 8], [24, 1.5, 6], [34, 3, 7.5]]) ln(c, "#f2f2f2", o.small ? 2.2 : 1.8, [[x0, y], [x1, y + 1.2]]); } },
    skill_scatter_shot: { zh: "散彈驅離", meta: { el: "physical", rarity: "rare" },
      // 左下的雙管槍口（霰彈槍）＋槍口火光＋往右上散開的五顆彈丸（散彈、把人推開）
      d: (c, o) => { c.save(); c.translate(13.5, 35.5); c.rotate(-Math.PI / 4);
        rr(c, "#7a5232", -11.5, -4, 11, 8.4, 3.4); rr(c, M.iron, -3, -4.6, 17.5, 9.2, 2); f(c, M.ironD, () => c.rect(-3, -0.7, 17.5, 1.4)); f(c, HI2, () => c.rect(-1, -3.4, 12, 1.2)); rr(c, M.ironD, 11.5, -5.2, 3, 10.4, 1);
        halo(c, o, (x) => { poly(x, "#ffb23a", [[14.5, -4.4], [21.5, -7.6], [19.6, -2.4], [25, 0], [19.6, 2.4], [21.5, 7.6], [14.5, 4.4]], 0.4); poly(x, "#fff7c0", [[14.5, -2.4], [19, -3], [21, 0], [19, 3], [14.5, 2.4]]); });
        for (const [d, a] of [[29, -0.52], [31.5, -0.26], [33, 0], [31.5, 0.26], [29, 0.52]]) { const x = Math.cos(a) * d, y = Math.sin(a) * d; ci(c, "#ffd23f", x, y, o.small ? 2.7 : 2.4); if (!o.small) ci(c, HI2, x - 0.7, y - 0.7, 0.8); }
        c.restore(); } },
    skill_suppressing_fire: { zh: "壓制射擊", meta: { el: "physical", rarity: "rare" },
      // 三發黃銅子彈一排排往右下壓（連續火力壓著打）＋後面的白色彈道線；不畫槍，和散彈的「槍口＋散開的圓彈丸」分開
      d: (c, o) => { c.save(); c.translate(24, 24); c.rotate(Math.PI / 5); for (const [x, y] of [[7, -12.5], [0.5, 0], [8.5, 12.5]]) bullet(c, x, y, 1.42); c.restore(); },
      pre: (c, o) => { c.save(); c.translate(24, 24); c.rotate(Math.PI / 5); for (const [x, y] of [[7, -12.5], [0.5, 0], [8.5, 12.5]]) { ln(c, "rgba(255,255,255,0.9)", 2, [[x - 11, y - 2], [x - 22, y - 2]]); ln(c, "rgba(255,255,255,0.6)", 1.6, [[x - 11, y + 2.2], [x - 18, y + 2.2]]); } c.restore(); } },
    skill_fire_bolt: { zh: "火焰箭", meta: { el: "fire", rarity: "common" },
      // 一支火做的箭：箭頭形的火舌朝右上、後面三條火尾（火＋飛行物）
      pre: (c) => glow(c, 28, 20, 20, "#ffb23a", 0.5),
      d: (c, o) => diag(c, (x) => { poly(x, "#ff6a1a", [[0, -20], [7, -8.5], [4.4, -4], [6, 4.5], [2.8, 1], [1.8, 11], [0, 5.5], [-1.8, 16], [-2.8, 2.5], [-6, 8], [-4.4, -4], [-7, -8.5]], 0.9); poly(x, "#ffd23f", [[0, -15.5], [3.9, -8], [2.2, -2], [0, 4], [-2.2, -2], [-3.9, -8]], 0.5); el(x, "#ffffff", 0, -9, 1.5, 3.4); }) },
    skill_spark_chain: { zh: "火花連鎖", meta: { el: "lightning", rarity: "rare" },
      // 一道電從左上的火花折兩折跳到右下的火花（雷＋連鎖）
      pre: (c) => { glow(c, 10, 11, 12, "#fff36b", 0.45); glow(c, 38.5, 37.5, 11, "#fff36b", 0.45); },
      d: (c, o) => { const P = [[10, 11], [25.5, 17], [18.5, 25.5], [38.5, 37.5]]; ln(c, "#fff36b", o.small ? 5.4 : 4.8, P, "miter"); ln(c, "#ffffff", 1.5, P, "miter"); poly(c, "#fff36b", starPts(10, 11, 7.6, 3, 4), 0.4); poly(c, "#ffffff", starPts(10, 11, 3.6, 1.5, 4)); poly(c, "#fff36b", starPts(38.5, 37.5, 6.4, 2.6, 4), 0.4); poly(c, "#ffffff", starPts(38.5, 37.5, 3, 1.3, 4)); } },
    skill_plant_totem: { zh: "立起圖騰", meta: { el: "default", rarity: "rare" },
      // 一根插在土堆上的木雕圖騰柱：頂上一對紅翅、兩張臉（召喚＋地面）
      pre: (c) => glow(c, 24, 40, 17, "#7fe0c0", 0.5),
      d: (c, o) => { el(c, "#6a4a2e", 24, 41.5, 14.5, 3.6); poly(c, "#c0392b", [[17, 9], [5, 6], [8, 11.5], [4.5, 13], [9.5, 15], [17, 15.5]], 0.5); poly(c, "#c0392b", [[31, 9], [43, 6], [40, 11.5], [43.5, 13], [38.5, 15], [31, 15.5]], 0.5);
        rr(c, M.wood, 16.5, 5, 15, 36.5, 3.4); f(c, "#b98048", () => c.roundRect(16.5, 5, 4.4, 36.5, [3.4, 0, 0, 3.4])); f(c, M.woodD, () => c.rect(16.5, 21.4, 15, 1.7));
        for (const y of [11, 28]) { rr(c, "#fff6c8", 19, y, 3.6, 3.6, 0.8); rr(c, "#fff6c8", 25.4, y, 3.6, 3.6, 0.8); if (!o.small) { f(c, OUT, () => c.rect(20.3, y + 1, 1.5, 1.8)); f(c, OUT, () => c.rect(26.7, y + 1, 1.5, 1.8)); } }
        rr(c, M.woodD, 20.6, 16.6, 6.8, 2.4, 1); poly(c, "#e8bb48", [[20, 34.5], [22, 37.5], [24, 34.5], [26, 37.5], [28, 34.5], [28, 36], [26, 39], [24, 36], [22, 39], [20, 36]]); } },
    skill_guardian_aegis: { zh: "守護之盾", meta: { el: "holy", rarity: "rare" },
      // 金邊的白盾、中央金色十字、周圍聖光（聖光＋護盾給隊友）；和塔盾猛擊的「木塔盾＋撞擊星」分開
      pre: (c) => glow(c, 24, 24, 23, "#fff6c8", 0.7),
      d: (c, o) => { const sh = (x, k) => { x.beginPath(); x.moveTo(24, 24 - 19.5 * k); x.lineTo(24 + 15.5 * k, 24 - 14.5 * k); x.lineTo(24 + 15.5 * k, 24); x.quadraticCurveTo(24 + 15.5 * k, 24 + 13 * k, 24, 24 + 20 * k); x.quadraticCurveTo(24 - 15.5 * k, 24 + 13 * k, 24 - 15.5 * k, 24); x.lineTo(24 - 15.5 * k, 24 - 14.5 * k); x.closePath(); };
        c.fillStyle = "#e8bb48"; sh(c, 1); c.fill(); c.fillStyle = "#fffaf0"; sh(c, 0.78); c.fill();
        c.save(); sh(c, 0.78); c.clip(); f(c, "rgba(232,187,72,0.28)", () => c.rect(24, 0, 24, 48)); c.restore();
        rr(c, "#e7a020", 21.4, 12.5, 5.2, 21, 1.6); rr(c, "#e7a020", 15, 18.4, 18, 5.2, 1.6); },
      post: (c, o) => { if (!o.small) { sparkle(c, "#ffffff", 40.5, 8, 3.4); sparkle(c, "#ffffff", 7, 38, 2.6); } } },
  };

  // =====================================================================
  // 物品：背包格的底色與外框（類別色、品質色）照現行 itemIcons.js，只換格子裡的圖。
  // =====================================================================
  const ITEM_CAT = { consumable: ["#2a3a30", "#6aa84a"], throwable: ["#2a3040", "#5ab0f0"], material: ["#2e2a26", "#9a8e7c"], currency: ["#3a3218", "#e8bb48"], quest: ["#3a2418", "#ff8a50"] };
  const ITEM_TIER = { 1: "#9a9a9a", 2: "#5a9ae0", 3: "#a870e0" };
  const GLASS = "#dcebf0";
  const liquid = (c, clip, col, top, surf) => { c.save(); c.beginPath(); clip(c); c.clip(); f(c, col, () => c.rect(0, top, 48, 48)); f(c, surf, () => c.rect(0, top, 48, 2)); c.restore(); };
  const ITEM = {
    item_hp_potion_small: { zh: "小回復藥", meta: { cat: "consumable" },
      // 圓肚瓶、軟木塞、紅藥水，瓶身一個白色十字（回復）
      d: (c, o) => { rr(c, GLASS, 20, 10, 8, 10, 1.5); rr(c, "#a06a36", 18.8, 4.6, 10.4, 6.6, 2.2); ci(c, GLASS, 24, 30, 13.4);
        liquid(c, (x) => x.arc(24, 30, 11.2, 0, TAU), "#e04a3a", 23.5, "#ff9a8a");
        rr(c, "#ffffff", 22.2, 26.6, 3.6, 10.4, 1); rr(c, "#ffffff", 18.8, 30, 10.4, 3.6, 1); el(c, HI2, 16.6, 24.5, 1.7, 3.6, 0.5); } },
    item_mana_potion: { zh: "回魔藥", meta: { cat: "consumable" },
      // 菱形尖肚瓶、水晶瓶塞、藍藥水，瓶身一顆白色四芒星（法力）；瓶形和回復藥不同，不只換顏色
      d: (c, o) => { rr(c, GLASS, 21, 9.5, 6, 8, 1.2); poly(c, "#c8bcff", [[24, 2.6], [28, 6.8], [24, 11], [20, 6.8]], 0.6);
        const body = [[24, 14.5], [35.5, 27], [30.5, 42], [17.5, 42], [12.5, 27]]; poly(c, GLASS, body, 1.6);
        liquid(c, (x) => { x.moveTo(24, 16.5); x.lineTo(33.8, 27.2); x.lineTo(29.4, 40.4); x.lineTo(18.6, 40.4); x.lineTo(14.2, 27.2); x.closePath(); }, "#4a8ae0", 24.5, "#9ac4ff");
        sparkle(c, "#ffffff", 24, 32.5, 5.4); el(c, HI2, 18.6, 25.5, 1.3, 3, 0.7); } },
    item_fire_flask: { zh: "火瓶", meta: { cat: "throwable" },
      // 方肩的投擲瓶、瓶口塞一條布、布頭點著火，瓶裡是橘色的油與火苗（丟出去會燒）；不靠右下角的小元素記號
      pre: (c) => glow(c, 29, 6, 10, "#ffb23a", 0.6),
      d: (c, o) => { rr(c, GLASS, 20.2, 12, 7.6, 9, 1.4); poly(c, "#e8dcc0", [[21.4, 13.5], [26.4, 13.5], [29.6, 7.4], [25.6, 7.2]], 0.8); flame(c, "#ff6a1a", 28.6, 4.6, 0.4);
        rr(c, GLASS, 12.5, 19.5, 23, 23.5, 5.5);
        liquid(c, (x) => x.roundRect(14.3, 21.3, 19.4, 19.9, 4), "#ff7a2a", 25, "#ffc070");
        flame(c, "#ffd23f", 24, 33, 0.62); if (!o.small) flame(c, "#ffffff", 24.2, 35.4, 0.28); el(c, HI2, 16.6, 28, 1.2, 3.2, 0); } },
    item_fine_material: { zh: "精料", meta: { cat: "material", tier: 2 },
      // 一塊藍灰礦石、三個切面（亮、中、暗），嵌兩顆亮晶
      d: (c, o) => { const P = [[9.5, 35], [13.5, 21], [23, 13.5], [35.5, 17.5], [39.5, 31], [31, 39.5], [16, 39.5]]; poly(c, "#8aa8c8", P, 1.4);
        poly(c, "#b4cbe2", [[13.5, 21], [23, 13.5], [35.5, 17.5], [25, 25.5]], 0.6); poly(c, "#6282a4", [[25, 25.5], [35.5, 17.5], [39.5, 31], [31, 39.5]], 0.6);
        poly(c, "#e8f8ff", [[17.5, 28], [20.3, 31.4], [17.5, 34.8], [14.7, 31.4]]); if (!o.small) poly(c, "#e8f8ff", [[29, 18.4], [31, 20.6], [29, 22.8], [27, 20.6]]); } },
    gold: { zh: "金幣", meta: { cat: "currency" },
      // 兩枚疊著的金幣，後面斜靠一枚大的（幣面一顆星）
      d: (c, o) => { ci(c, "#e8bb48", 29.5, 19.5, 12); ci(c, "#f6d878", 29.5, 19.5, 8.8); poly(c, "#b8862a", starPts(29.5, 19.5, 5.6, 2.4, 5), 0.3);
        halo(c, o, (x) => { for (const y of [36.5, 30.5]) { rr(x, "#c89a30", 6, y - 0.2, 24, 7.4, 3.6); el(x, "#f6d878", 18, y, 12, 3.7); if (!o.small) el(x, "#e8bb48", 18, y, 7.4, 1.9); } }); } },
    quest_key: { zh: "鑰匙", meta: { cat: "quest" },
      // 金色大圓環鑰匙（環中間是空的）、兩齒；斜放
      d: (c, o) => { c.save(); c.translate(24, 24); c.rotate(-0.72);
        c.beginPath(); c.arc(0, -11.5, 8.8, 0, TAU); c.moveTo(4.2, -11.5); c.arc(0, -11.5, 4.2, 0, TAU, true); c.fillStyle = "#e8bb48"; c.fill("evenodd");
        rr(c, "#e8bb48", -2.3, -4, 4.6, 23.5, 1.6); rr(c, "#e8bb48", 1.5, 8.6, 7, 4.2, 1); rr(c, "#e8bb48", 1.5, 14.6, 5.2, 4.2, 1);
        f(c, "#f6d878", () => c.rect(-1.3, -2.6, 1.1, 20)); c.beginPath(); c.arc(0, -11.5, 7.6, Math.PI * 0.95, Math.PI * 1.55); c.strokeStyle = "#f6d878"; c.lineWidth = 1.2; c.stroke(); c.restore(); } },
  };

  // =====================================================================
  // 狀態：外框形狀與框色（增益綠圓、減益紅圓角方、中性金六角）照現行；框裡的單色線條換成 Q 版的小東西（有顏色、有亮面）。
  // 頭頂最小 11px：≤14px 時圖樣不包外框（深色底已經夠分明）、只留主形與一階亮面，圖樣放大到撐滿框。
  // =====================================================================
  const STATUS = {
    burning: { zh: "燃燒", meta: { pol: "debuff" }, d: (c, o) => { flame(c, "#ff6a1a", 24, 24.5, 2.12); flame(c, "#ffd23f", 24.4, 30, 1.2); if (!o.tiny) el(c, "#ffffff", 24.6, 35, 2.4, 3.6); } },
    bleed: { zh: "流血", meta: { pol: "debuff" }, d: (c, o) => { drop(c, "#e0303a", 19.5, 23, 1.95); drop(c, "#e0303a", 37, 33.5, 0.98); el(c, "#ff9aa0", 15, 25.5, 2, 4.6, 0.5); if (!o.tiny) { f(c, "rgba(90,0,10,0.3)", () => { c.moveTo(27, 36); c.quadraticCurveTo(31, 31, 32.5, 24); c.quadraticCurveTo(35.5, 36, 26, 41.5); c.closePath(); }); el(c, "#ff9aa0", 35, 34.5, 1, 2.2, 0.5); } } },
    prone: { zh: "倒地", meta: { pol: "debuff" },
      // 一個趴倒的 Q 版小人：圓頭在左、身體橫躺在地面線上；頭上兩道撞擊線
      d: (c, o) => { if (o.tiny) { c.translate(24, 30); c.scale(1.18, 1.18); c.translate(-24, -28); }
        rr(c, "#8a7a6a", 2.5, 39, 43, 4.2, 2); rr(c, "#4a4038", 36.5, 24.5, 8.5, 14, 3.6); rr(c, "#5a8ac8", 19, 21.5, 23, 17, 6.5); if (!o.tiny) f(c, "rgba(255,255,255,0.3)", () => c.rect(24, 23.4, 13, 2.4));
        ci(c, M.skin, 14, 27, 11.6); f(c, "#3a2414", () => { c.arc(14, 27, 11.6, Math.PI * 0.95, Math.PI * 1.9); c.closePath(); });
        if (!o.tiny) { ln(c, OUT, 1.8, [[9.6, 28], [14, 32.4]]); ln(c, OUT, 1.8, [[14, 28], [9.6, 32.4]]); } },
      post: (c, o) => { if (!o.tiny) { ln(c, "#ffd84a", 2.4, [[5, 6.5], [8, 11]]); ln(c, "#ffd84a", 2.4, [[14.5, 3.5], [14.8, 9]]); ln(c, "#ffd84a", 2.4, [[24, 6.5], [21.4, 11]]); } } },
    stun: { zh: "暈眩", meta: { pol: "debuff" }, d: (c, o) => { poly(c, "#ffd84a", starPts(22, 27.5, 15, 6.6, 5), 1.2); if (!o.tiny) poly(c, "#fff3a0", [[22, 14], [24.6, 22], [19.4, 22]]); poly(c, "#ffd84a", starPts(39, 11.5, 6.4, 2.8, 5), 0.7); if (!o.tiny) poly(c, "#ffd84a", starPts(8, 9.5, 4.6, 2, 5), 0.6); } },
    frozen: { zh: "冰凍", meta: { pol: "debuff" },
      // 一叢冰晶（三根冰柱），不是雪花線條；和「緩速」的時鐘分得開
      d: (c, o) => { poly(c, "#8fe3ff", [[12, 17], [17.5, 25], [16.5, 42], [7, 42], [6, 26]], 0.8); poly(c, "#8fe3ff", [[36.5, 20], [42, 28], [41, 42], [32, 42], [31, 28]], 0.8); poly(c, "#b8efff", [[24, 4.5], [31.5, 17], [29.5, 42], [18.5, 42], [16.5, 17]], 0.8);
        poly(c, "#ffffff", [[24, 7], [24, 40.5], [19.6, 40.5], [18, 17.4]]); if (!o.tiny) { poly(c, "#3fa6d8", [[29.2, 20], [30.4, 17.6], [28.6, 41], [26.4, 41]]); poly(c, "#e8fbff", [[11.6, 20], [11.6, 41], [8.4, 41], [7.6, 26.4]]); poly(c, "#e8fbff", [[36, 23], [36, 41], [33.2, 41], [32.6, 28.4]]); } } },
    hasted: { zh: "加速", meta: { pol: "buff" },
      // 兩個並排往右的胖箭頭（上半亮、下半暗）＋左邊兩道速度線
      d: (c, o) => { for (const dx of [3, 20]) { poly(c, "#7dffb0", [[dx, 9], [dx + 10, 9], [dx + 22, 24], [dx + 10, 39], [dx, 39], [dx + 12, 24]], 0.9); poly(c, "#d6ffe6", [[dx + 1, 10], [dx + 9.6, 10], [dx + 20.6, 24], [dx + 12, 24]]); } } },
  };
  const STATUS_FRAME = { buff: "#3fbf6a", debuff: "#e04848", neutral: "#c8a048" };

  // =====================================================================
  // HUD：資源小圖（16px）、工具鈕（20px）、功能列（35px）。按鈕與底板照現行，只換圖。
  // =====================================================================
  const HUD = {
    ap: { zh: "AP（行動點）", d: (c, o) => { poly(c, "#ffd23a", [[27, 3.5], [9.5, 27], [21, 27], [16, 44.5], [38.5, 19.5], [27, 19.5], [33.5, 3.5]], 1); if (!o.tiny) poly(c, "#fff3a0", [[27.4, 5], [12.6, 25.6], [17, 25.6], [31, 5]]); } },
    mana: { zh: "法力", d: (c, o) => { drop(c, "#4a8ae0", 24, 24.5, 2.1); c.save(); c.beginPath(); c.rect(0, 0, 48, 48); c.clip(); f(c, "rgba(20,40,110,0.38)", () => { c.moveTo(24, 45.5); c.bezierCurveTo(34, 45.5, 40, 38, 38.4, 29.5); c.bezierCurveTo(37, 37, 31, 41, 24, 41.5); c.closePath(); }); c.restore(); el(c, "#cfe4ff", 18, 28.5, 2.6, 5.6, 0.45); } },
    stamina: { zh: "耐力", d: (c, o) => { const P = [[4.5, 26], [13.5, 26], [19, 11.5], [27.5, 37.5], [32.5, 24], [43.5, 24]]; ln(c, "#e8bb48", 6.4, P); if (!o.tiny) ln(c, "#fff0b0", 1.6, P.map(([x, y]) => [x - 0.6, y - 1.2])); } },
    move: { zh: "移動", d: (c, o) => { rr(c, "#a07040", 12.5, 5.5, 15.5, 30, 4); f(c, "#a07040", () => { c.moveTo(12.5, 24); c.lineTo(27, 24); c.quadraticCurveTo(41.5, 25.5, 42.5, 35.5); c.lineTo(42.5, 39); c.lineTo(12.5, 39); c.closePath(); });
        rr(c, "#5e3b1f", 11, 38, 33, 5.4, 2.2); rr(c, "#e0c088", 11, 4.5, 18.5, 7.6, 3.2); if (!o.tiny) { f(c, HI, () => c.rect(15, 13.5, 2.2, 20)); f(c, "rgba(0,0,0,0.2)", () => { c.moveTo(28, 26); c.quadraticCurveTo(39.5, 27.5, 41, 36); c.lineTo(28, 36); c.closePath(); }); } } },
    exit: { zh: "離開", d: (c, o) => { rr(c, "#5a3e28", 5.5, 4.5, 23, 39.5, 2.4); poly(c, "#a06a36", [[8, 7], [20, 11], [20, 43.6], [8, 41.4]], 0.6); ci(c, "#e8bb48", 16.6, 26.5, 2);
        halo(c, o, (x) => { poly(x, "#f2e6c8", [[23.5, 20], [33.5, 20], [33.5, 13.5], [45, 24], [33.5, 34.5], [33.5, 28], [23.5, 28]], 0.8); f(x, HI2, () => x.rect(24.5, 20.4, 8.6, 1.6)); }); } },
    bag: { zh: "背包", d: (c, o) => { c.beginPath(); c.moveTo(17.5, 16); c.lineTo(17.5, 10); c.quadraticCurveTo(24, 3, 30.5, 10); c.lineTo(30.5, 16); c.strokeStyle = "#5a3a1e"; c.lineWidth = 3.4; c.lineCap = "round"; c.stroke();
        rr(c, "#a06a36", 8.5, 15, 31, 28, 7.5); f(c, "#8a5a30", () => c.roundRect(8.5, 13.5, 31, 16.5, [7.5, 7.5, 10, 10])); rr(c, "#8a5a30", 14, 33.5, 20, 7, 2.6);
        f(c, HI, () => c.rect(12.5, 16, 12, 1.6)); rr(c, "#e8bb48", 21, 25.5, 6, 7.4, 1.6); if (!o.small) f(c, "#9c7420", () => c.rect(23.2, 27.6, 1.6, 3)); } },
  };

  // =====================================================================
  // 事件卡：深底圓＋選項色圓環照現行（storyIconArt.drawChip），只換環裡的圖。
  // =====================================================================
  const crossSword = (c, o, s) => { c.save(); c.translate(24, 24.5); c.scale(s, 1); c.rotate(Math.PI / 4); c.scale(0.98, 0.98); swordArt(c, o); c.restore(); };
  const EVENT = {
    combat: { zh: "戰鬥", meta: { ring: "#d0503a" }, d: (c, o) => { crossSword(c, o, -1); halo(c, o, (x) => crossSword(x, o, 1)); } },
    persuade: { zh: "說服", meta: { ring: "#e8bb48" }, d: (c, o) => { poly(c, "#f2e6c8", [[15, 30], [11.5, 42.5], [25, 31.5]], 0.8); rr(c, "#f2e6c8", 5, 7, 38, 25.5, 9.5); heart(c, "#e05a6a", 24, 19.8, 1.22); if (!o.small) el(c, "#ffb0b8", 19.6, 16.4, 1.6, 2.2, -0.5); } },
    investigate: { zh: "調查", meta: { ring: "#4ab0d0" }, d: (c, o) => { c.save(); c.translate(31, 31); c.rotate(Math.PI / 4); rr(c, "#6a4028", -2, 0, 17.5, 6.4, 2.6); c.restore(); ci(c, "#d8a040", 19.5, 19.5, 14); ci(c, "#bfe4f2", 19.5, 19.5, 9.8); el(c, "#ffffff", 15.6, 15.4, 2.6, 4.4, 0.7); if (!o.small) f(c, "rgba(40,110,150,0.3)", () => { c.arc(19.5, 19.5, 9.8, 0.1, Math.PI * 0.75); c.closePath(); }); } },
    trade: { zh: "交易", meta: { ring: "#e8bb48" }, d: (c, o) => { poly(c, "#b08a5a", [[15.5, 9], [19, 12], [24, 9.5], [29, 12], [32.5, 9], [28.5, 18.5], [39.5, 30.5], [36.5, 42], [11.5, 42], [8.5, 30.5], [19.5, 18.5]], 1.4); rr(c, "#6a4028", 17, 16.4, 14, 3.6, 1.6); if (!o.small) f(c, "rgba(255,255,255,0.25)", () => c.ellipse(15.5, 32, 2.6, 5.6, 0.3, 0, TAU));
        halo(c, o, (x) => { ci(x, "#ffd23a", 35, 35.5, 8); ci(x, "#fff0a0", 35, 35.5, 5.4); f(x, "#b8862a", () => x.rect(34, 32.5, 2, 6)); }); } },
  };

  const ART = { weapon: WEAPON, skill: SKILL, item: ITEM, status: STATUS, hud: HUD, event: EVENT };
  const SKILL_EL = { physical: ["#2c313b", "#7d8798"], fire: ["#4a1104", "#e8541a"], lightning: ["#1d1d4a", "#5a5ac8"], holy: ["#5a3a06", "#e7b23a"], default: ["#221c44", "#6a5ad0"] };
  const SKILL_RARITY = { common: "#9aa0a6", rare: "#4da3ff", epic: "#b06cff", legendary: "#ffbf3a" };

  /** 只畫圖樣（不含框），貼到 ctx 的 (x,y)、邊長 px。res＝ctx 目前每單位幾個裝置像素。 */
  function art(ctx, cat, id, x, y, px, res, opt) { const def = ART[cat][id]; if (def) ctx.drawImage(render(def, px, res, opt), x, y, px, px); }
  /** 畫一個含框的圖示在 (0,0)～(size,size)。框都是現行樣式。opt.frame：武器 badge（米色圓章，預設）｜gear（裝備格）｜none；HUD none（預設）｜backing（功能列的淺色圓底）。 */
  function paint(ctx, cat, id, size, res, opt = {}) {
    const def = ART[cat][id], meta = def.meta ?? {};
    ctx.save();
    if (cat === "weapon") {
      const fr = opt.frame ?? "badge";
      if (fr === "badge") { const g = ctx.createRadialGradient(size / 2, size * 0.42, 0, size / 2, size / 2, size / 2); g.addColorStop(0, "#f6eed8"); g.addColorStop(1, "#d6c7a2"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(size / 2, size / 2, size / 2, 0, TAU); ctx.fill(); ctx.lineWidth = size / 24; ctx.strokeStyle = "#c8a868"; ctx.beginPath(); ctx.arc(size / 2, size / 2, size / 2 - size / 48, 0, TAU); ctx.stroke(); art(ctx, cat, id, 0, 0, size, res); }
      else if (fr === "gear") { const k = size / 64; ctx.save(); ctx.scale(k, k); ctx.fillStyle = "#23262d"; ctx.beginPath(); ctx.roundRect(2, 2, 60, 60, 9); ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = "#8a8f99"; ctx.stroke(); ctx.restore(); const p = size * 0.08; art(ctx, cat, id, p, p, size - p * 2, res); }
      else art(ctx, cat, id, 0, 0, size, res);
    } else if (cat === "skill") {
      const [dk, lt] = SKILL_EL[meta.el] ?? SKILL_EL.default, k = size / 100, rar = SKILL_RARITY[meta.rarity] ?? SKILL_RARITY.common;
      ctx.save(); ctx.scale(k, k); ctx.beginPath(); ctx.roundRect(2, 2, 96, 96, 16); ctx.save(); ctx.clip(); ctx.fillStyle = dk; ctx.fillRect(0, 0, 100, 100); ctx.fillStyle = mix(dk, lt, 0.62); ctx.beginPath(); ctx.arc(50, 52, 39, 0, TAU); ctx.fill(); ctx.fillStyle = mix(dk, lt, 0.9); ctx.beginPath(); ctx.arc(50, 52, 27, 0, TAU); ctx.fill(); ctx.restore();
      ctx.restore(); const p = size * 0.09; art(ctx, cat, id, p, p, size - p * 2, res, { ow: outlinePx(size) });
      ctx.save(); ctx.scale(k, k); ctx.beginPath(); ctx.roundRect(2, 2, 96, 96, 16); ctx.lineWidth = meta.rarity === "legendary" ? 5 : 3.5; ctx.strokeStyle = rar; ctx.stroke(); ctx.restore();
    } else if (cat === "item") {
      const [bg, rim] = ITEM_CAT[meta.cat];
      ctx.beginPath(); ctx.roundRect(0, 0, size, size, size * 0.16); const g = ctx.createLinearGradient(0, 0, 0, size); g.addColorStop(0, bg); g.addColorStop(1, "#1a1612"); ctx.fillStyle = g; ctx.fill(); ctx.lineWidth = Math.max(1.5, size * 0.035); ctx.strokeStyle = meta.tier ? ITEM_TIER[meta.tier] : rim; ctx.stroke();
      const p = size * 0.07; art(ctx, cat, id, p, p, size - p * 2, res, { ow: outlinePx(size) });
      if (opt.count) { ctx.font = `bold ${Math.round(size * 0.24)}px Consolas, monospace`; ctx.textAlign = "right"; ctx.textBaseline = "alphabetic"; ctx.lineWidth = 3; ctx.strokeStyle = "#000"; ctx.strokeText(opt.count, size - 4, size - 4); ctx.fillStyle = "#fff"; ctx.fillText(opt.count, size - 4, size - 4); }
    } else if (cat === "status") {
      const pol = meta.pol, r = size / 2; ctx.save(); ctx.translate(r, r); ctx.beginPath();
      if (pol === "buff") ctx.arc(0, 0, r, 0, TAU); else if (pol === "debuff") ctx.roundRect(-r * 0.9, -r * 0.9, r * 1.8, r * 1.8, r * 0.35); else for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos((i / 6) * TAU + TAU / 12) * r, Math.sin((i / 6) * TAU + TAU / 12) * r);
      ctx.closePath(); ctx.fillStyle = "rgba(12,12,16,0.88)"; ctx.fill(); ctx.lineWidth = Math.max(1.5, size * 0.09); ctx.strokeStyle = STATUS_FRAME[pol]; ctx.stroke(); ctx.restore();
      const a = size * (size <= 14 ? 0.78 : 0.74), p = (size - a) / 2; art(ctx, cat, id, p, p, a, res, { ow: size <= 14 ? 0 : outlinePx(size) * 0.8 });
    } else if (cat === "event") {
      ctx.beginPath(); ctx.arc(size / 2, size / 2, size / 2, 0, TAU); ctx.fillStyle = "#2a241e"; ctx.fill(); ctx.lineWidth = Math.max(1.2, size * 0.06); ctx.strokeStyle = meta.ring; ctx.stroke();
      const a = size * 0.8, p = (size - a) / 2; art(ctx, cat, id, p, p, a, res, { ow: outlinePx(size) });
    } else if (cat === "hud") {
      // 功能列：現行每個圖示底下墊一個淺色圓底（HudBarIcons.tsx 的 HUD_BACKING，RT-3b 定案），照留；圖樣縮在圓底附近
      if (opt.frame === "backing") { ctx.beginPath(); ctx.arc(size / 2, size / 2, (15.5 / 48) * size, 0, TAU); ctx.fillStyle = "#d4dbef"; ctx.fill(); ctx.lineWidth = size / 48; ctx.strokeStyle = "#8a94b8"; ctx.stroke(); const p = size * 0.2; art(ctx, cat, id, p, p * 1.1, size - p * 2, res, { ow: outlinePx(size) }); }
      else art(ctx, cat, id, 0, 0, size, res);
    }
    ctx.restore();
  }
  /** 含框的圖示 canvas：顯示邊長 px×zoom；zoom 1 時內部解析度 ×2（和遊戲一樣），放大時直接用向量畫到該倍率（圖樣的簡化程度仍照 px）。 */
  function canvas(cat, id, px, zoom = 1, opt = {}) {
    const res = zoom === 1 ? 2 : zoom, cv = blank(Math.round(px * res)); cv.style.width = px * zoom + "px"; cv.style.height = px * zoom + "px";
    const x = cv.getContext("2d"); x.scale(res, res); paint(x, cat, id, px, res, opt); return cv;
  }
  const list = (cat) => Object.entries(ART[cat]).map(([id, d]) => ({ id, zh: d.zh, meta: d.meta ?? {} }));
  return { ART, OUT, M, EL, render, art, paint, canvas, list, outlinePx };
})();
