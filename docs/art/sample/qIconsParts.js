// qIconsParts.js：「小圖示改 Q 版」全量重畫第 4 批——骨架徽章、部件小圓片、技能卡小圖、56／96px 完整技能圖示的組裝（畫圖 agent 2026-11-12）。
// 規則：docs/art/Q版小圖示樣張.md 第 2 節（尤其 8、9、10、11）；紀錄：docs/art/Q版小圖示-第4批徽章與部件.md；樣張頁：q-icons-parts.html。
// 這一批只換「圓片、徽章、卡片小圖裡面的圖」：圓片的深色圓底與色環、徽章的圓底與稀有度色環、技能外框都照現行（client/src/render/skillParts.ts 的 drawChip、skillIcon.ts 的 skeletonBadge）。
// 每個圖樣畫在以 (0,0) 為中心、半徑約 10 單位的範圍（和第 3 批的效果記號同一個座標，所以第 3 批的 23 個記號直接呼叫 QIconsSkills.ACT[x].d，不另畫）；
// 風格樣張已有的狀態（冰凍、暈眩、倒地、加速、恐懼）、HUD 的 AP、法力、耐力、靴子、第 3 批的元素道具與毒液是畫在 48 格的，這裡包一層縮放後原樣呼叫（box48）。
// o.small＝圖樣本身 ≤24px、o.tiny＝≤14px（圖樣本身的大小＝圓片直徑的 78%；18px 的組裝列小圓片裡圖樣只有 12px，一律走 tiny：只留一個主體、不包外框）。
// 依賴（先載入）：qIcons.js（H、W.swordArt、ART.status／hud、render）、qIconsWeapons.js、qIconsSkills.js（ACT、ELEMENT、TINT、def、base、framePath）。
window.QIconsParts = (() => {
  const Q = window.QIcons, QS = window.QIconsSkills, QW = window.QIconsWeapons, { mix, f, rr, ci, el, poly, ln, starPts, flame, drop, halo, blank } = Q.H, TAU = Math.PI * 2, PI = Math.PI, OUT = Q.OUT;
  const CREAM = "#f2e6c8", ALLY = "#7de0a8", ENEMY = "#ff5a5a", STEEL = "#c3ccd6", GOLD = "#e8bb48", LILAC = "#c8a0d8", STONE = "#b4ac9a", STONE_L = "#ece6d6", STONE_D = "#8c8474", INK = "#2a1c36";
  const st = (c, col, w, fn, cap = "round") => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
  const at = (c, x, y, k, fn, rot = 0) => { c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k); fn(c); c.restore(); };
  /** 第 3 批的效果記號（同一個題材同一個形，直接呼叫）。 */
  const act = (id, T, t) => (c, o) => QS.ACT[id].d(c, o, T ?? QS.ACT[id].def ?? ["#ffd23f", "#ffffff"], t);
  /** 畫在 48 格的既有圖樣：縮到 ±10 單位的座標裡。 */
  const from48 = (d, k = 0.47) => (c, o) => { c.save(); c.scale(k, k); c.translate(-24, -24); d(c, o); c.restore(); };

  // ---------------- 共用的小零件 ----------------
  /** 人形（規則 9：單色剪影，圓頭加圓肩的半身）；高約 15k。 */
  const bust = (c, col, x, y, k = 1) => { ci(c, col, x, y - 4.6 * k, 3.7 * k); f(c, col, () => { c.moveTo(x - 6.2 * k, y + 7 * k); c.quadraticCurveTo(x - 6.2 * k, y - 0.4 * k, x, y - 0.4 * k); c.quadraticCurveTo(x + 6.2 * k, y - 0.4 * k, x + 6.2 * k, y + 7 * k); c.closePath(); }); };
  /** 朝右的細長箭頭（高 11.2）。 */
  const arrowS = (c, col, hi) => { poly(c, col, [[-10, -2.4], [1, -2.4], [1, -5.6], [10, 0], [1, 5.6], [1, 2.4], [-10, 2.4]], 0.4); if (hi) poly(c, hi, [[-10, -2.4], [1, -2.4], [1, -5.6], [10, 0], [-10, 0]]); };
  const heart = (c, col, x, y, s) => { c.save(); c.translate(x, y); c.scale(s, s); c.beginPath(); c.moveTo(0, 7); c.bezierCurveTo(-11, -1, -7, -10, 0, -4.5); c.bezierCurveTo(7, -10, 11, -1, 0, 7); c.closePath(); c.fillStyle = col; c.fill(); c.restore(); };
  const heartArt = (c, o, col = "#f0503e", hi = "#ffb0a0", s = 1.25) => { heart(c, col, 0, 1.4, s); el(c, hi, -3.6 * (s / 1.25), -2.6 * (s / 1.25), 2.6, 1.7, -0.6); };
  const plus = (c, o, x, y, k = 1, col = "#ffffff") => halo(c, o, (q) => { rr(q, col, x - 1.5 * k, y - 4.4 * k, 3 * k, 8.8 * k, 0.8 * k); rr(q, col, x - 4.4 * k, y - 1.5 * k, 8.8 * k, 3 * k, 0.8 * k); });
  const minus = (c, o, x, y, k = 1, col = "#ffffff") => halo(c, o, (q) => rr(q, col, x - 4.4 * k, y - 1.5 * k, 8.8 * k, 3 * k, 0.8 * k)); /* 11-12：加號的橫槓（召喚物上限 −1） */
  const star4 = (c, col, x, y, R, core = "#ffffff") => { poly(c, col, starPts(x, y, R, R * 0.36, 4), 0.3); if (core) poly(c, core, starPts(x, y, R * 0.55, R * 0.2, 4)); };
  const burstStar = (c, x, y, R, col = "#ffd23f") => { poly(c, col, starPts(x, y, R, R * 0.48, 7, -1.2), 0.3); poly(c, "#ffffff", starPts(x, y, R * 0.48, R * 0.24, 7, -1.2)); };
  /** 靴子（HUD「移動」的同一隻，qIcons.js）加兩道速度線：移動過、移動後、移動時共用。 */
  const boot = (c, o) => { at(c, 2.6, 0.4, 0.4, (q) => { q.translate(-27, -24); Q.ART.hud.move.d(q, o); }); rr(c, CREAM, -10.6, -4.4, 4.6, 2.4, 1.2); rr(c, CREAM, -10.6, 1.4, 3.4, 2.4, 1.2); };
  const bootOnly = (c, o) => at(c, 0, 0, 0.47, (q) => { q.translate(-27, -24); Q.ART.hud.move.d(q, o); });
  /** 逆時針的回轉箭頭（反應：卡片小圖、骨架徽章、額外反應共用）。 */
  const react = (c, o, col = "#5ad06a", hi = "#c8f8d0") => { st(c, col, 4.2, (x) => x.arc(0, 0.6, 7, -PI * 0.2, PI * 1.22), "butt"); if (!o.tiny) st(c, hi, 1.4, (x) => x.arc(0, 0.6, 8, PI * 0.25, PI * 0.8), "butt"); at(c, -5.6, -3.6, 1, (q) => poly(q, col, [[-5.4, 1.6], [5.4, 1.6], [0, -5.6]], 0.4), 0.85); };
  const hourglass = (c, o) => { rr(c, "#8ab8f0", -7.8, -10.6, 15.6, 3.4, 1.5); rr(c, "#8ab8f0", -7.8, 7.2, 15.6, 3.4, 1.5); poly(c, "#e6f4ff", [[-6, -7.4], [6, -7.4], [1.1, 0], [6, 7.4], [-6, 7.4], [-1.1, 0]], 0.4); poly(c, "#ffc23a", [[-4, -6], [4, -6], [0, -0.8]]); poly(c, "#e8962a", [[-4.6, 7], [4.6, 7], [0, 3.4]]); };
  const clock = (c, o) => { ci(c, "#8ab8f0", 0, 0, 10.2); ci(c, "#f2f8ff", 0, 0, 7.3); if (!o.tiny) el(c, "#ffffff", -2.6, -3, 2.6, 1.5, -0.6); ln(c, "#26365a", 2.1, [[0, -4.6], [0, 0], [3.7, 2.3]]); };
  const bolt = (c, o) => { poly(c, "#ffd23a", [[1.6, -10.6], [-7.6, 1.6], [-1.6, 1.6], [-4.2, 10.6], [7, -2.6], [1, -2.6], [4.2, -10.6]], 0.5); if (!o.tiny) poly(c, "#fff6b0", [[1.8, -9.4], [-5.6, 0.6], [-3.4, 0.6], [3.2, -9.4]]); };
  const crystal = (c) => { poly(c, "#b8a8ff", [[0, -10.6], [7.8, -4.6], [7.8, 4.6], [0, 10.6], [-7.8, 4.6], [-7.8, -4.6]], 0.6); poly(c, "#f2ecff", [[0, -10.6], [-7.8, -4.6], [0, -1]]); poly(c, "#d6ccff", [[-7.8, -4.6], [-7.8, 4.6], [0, -1]]); poly(c, "#7a68c8", [[7.8, -4.6], [7.8, 4.6], [0, 10.6], [0, -1]]); poly(c, "#9a86ff", [[-7.8, 4.6], [0, 10.6], [0, -1]]); };
  const dice = (c, o) => at(c, 0, 0, 1, (q) => { rr(q, "#f6f2e6", -8.2, -8.2, 16.4, 16.4, 3.6); f(q, "rgba(0,0,0,0.16)", () => q.roundRect(-8.2, 4.6, 16.4, 3.6, [0, 0, 3.6, 3.6])); for (const [x, y] of o.tiny ? [[-3.8, -3.8], [0, 0], [3.8, 3.8]] : [[-4, -4], [4, 4], [0, 0], [4, -4], [-4, 4]]) ci(q, INK, x, y, o.tiny ? 2.1 : 1.8); }, 0.2);
  const banner = (c, o) => { rr(c, "#9a6ab8", -8.6, -10.6, 17.2, 3.6, 1.6); poly(c, LILAC, [[-6.6, -8], [6.6, -8], [6.6, 9.6], [0, 4.4], [-6.6, 9.6]], 0.8); f(c, "#eed8f6", () => c.rect(-6.6, -7, 3, 13)); if (!o.tiny) star4(c, "#ffffff", 1.2, -1.4, 4.4, null); };
  const tag = (c, o) => at(c, 0, 0, 0.9, (q) => { poly(q, GOLD, [[-9.6, 0], [-3.4, -7.4], [9.6, -7.4], [9.6, 7.4], [-3.4, 7.4]], 1); f(q, "#fff0b0", () => q.rect(-2.6, -7.4, 12.2, 3)); ci(q, "#5a3a06", -4.4, 0, 2.1); if (!o.tiny) { f(q, "#9c7420", () => q.rect(0, -0.6, 7, 1.8)); f(q, "#9c7420", () => q.rect(0, 3, 5, 1.8)); } }, -0.5);
  const wall = (c, x = 5.4) => { rr(c, STONE, x, -10.4, 5, 20.8, 1.4); f(c, STONE_L, () => c.rect(x, -9.4, 1.8, 18.8)); };
  const puddle = (c, col = "#4aa8ff", hi = "#cfe8ff", y = 7) => { el(c, col, 0, y, 10.6, 3.6); el(c, hi, -2.6, y - 0.8, 5, 1.2); };
  const tablet = (c, o) => { f(c, "#9a9282", () => c.roundRect(-7.6, -10.4, 15.2, 20.8, [6.4, 6.4, 1.8, 1.8])); f(c, "#cfc8b6", () => c.roundRect(-7.6, -10.4, 3.8, 20.8, [6.4, 0, 0, 1.8])); poly(c, "#ffd23f", [[0, -6.2], [5, 0.4], [0, 7], [-5, 0.4]], 0.4); poly(c, "#fff6c8", [[0, -2.6], [2.4, 0.4], [0, 3.4], [-2.4, 0.4]]); };
  const paw = (c, o, col = "#c9a0ff", hi = "#ecdcff") => { el(c, col, 0, 4, 6.4, 5.2); for (const [x, y, r] of [[-7, -1.8, 2.7], [-2.6, -6.8, 3], [2.6, -6.8, 3], [7, -1.8, 2.7]]) ci(c, col, x, y, r); if (!o.tiny) el(c, hi, -2, 2.4, 2.6, 1.5, -0.4); };
  const shieldBlue = (c, o, T = ["#6ab8f0", "#cfe8ff"]) => { const P = [[-9.4, -9.6], [9.4, -9.6], [8.8, 2], [0, 10], [-8.8, 2]]; poly(c, T[0], P, 1); poly(c, T[1], [[-9.4, -9.6], [0, -9.6], [0, 10], [-8.8, 2]], 1); };
  const hood = (c, o) => { f(c, "#8a6ad8", () => { c.moveTo(0, -10.6); c.bezierCurveTo(8.6, -10.6, 10, -2, 9.6, 10.2); c.lineTo(-9.6, 10.2); c.bezierCurveTo(-10, -2, -8.6, -10.6, 0, -10.6); c.closePath(); }); f(c, "#b89af0", () => c.ellipse(-5.6, -3, 2, 6, 0.25, 0, TAU)); el(c, "#2a1650", 0, 0.6, 5.8, 5.6); poly(c, "#ffe14d", [[-4.4, -0.8], [-0.8, 0.8], [-1.2, 2.4], [-4, 1.6]], 0.2); poly(c, "#ffe14d", [[4.4, -0.8], [0.8, 0.8], [1.2, 2.4], [4, 1.6]], 0.2); };
  const crate = (c, o, x = 0, y = 0, s = 17) => { rr(c, "#a06a36", x - s / 2, y - s / 2, s, s, s * 0.12); f(c, "#d8a868", () => c.roundRect(x - s / 2, y - s / 2, s, s * 0.2, [s * 0.12, s * 0.12, 0, 0])); f(c, "#6a4420", () => c.roundRect(x - s / 2, y + s * 0.32, s, s * 0.18, [0, 0, s * 0.12, s * 0.12])); if (!o.small) ln(c, "#6a4420", s * 0.09, [[x - s * 0.3, y - s * 0.2], [x + s * 0.3, y + s * 0.24]]); };
  const grid3 = (c, lit = "#ffb23a", mid = "#fff6c8") => { c.save(); c.scale(0.8, 0.8); for (let i = 0; i < 9; i++) rr(c, i === 4 ? mid : lit, -10 + (i % 3) * 6.9, -10 + Math.floor(i / 3) * 6.9, 6.2, 6.2, 1.4); c.restore(); }; /* 縮到 0.8：九宮格的四角才不會頂到圓片的色環 */
  const qmark = (c, o, x, y, k = 1) => halo(c, o, (q) => { st(q, "#ffe9a8", 2.4 * k, (p) => { p.arc(x, y - 2.6 * k, 2.6 * k, PI * 1.05, PI * 0.5); p.lineTo(x, y + 1.6 * k); }); ci(q, "#ffe9a8", x, y + 4.6 * k, 1.4 * k); });
  /** 主圖樣縮到左下、右上角壓一個小圖（修正的「改了什麼」、召喚物數值用）。 */
  const withBadge = (base, small, bk = 0.8, sk = 0.48) => (c, o, T, opt) => { at(c, -2.2, 2.2, bk, (q) => base(q, o)); halo(c, o, (q) => at(q, 6, -5.6, sk, (p) => small(p, { ...o, tiny: true, small: true, owPx: 0, flat: true }, T, opt))); };
  const upArrow = (c, o, T = ["#ffb23a", "#fff6c8"]) => { poly(c, T[0], [[0, -11], [10, -1], [4, -1], [4, 9.6], [-4, 9.6], [-4, -1], [-10, -1]], 0.6); poly(c, T[1], [[0, -11], [-10, -1], [-4, -1], [-4, 9.6], [0, 9.6]]); };
  const downArrow = (c, o, T = ["#6ae0ff", "#d8f8ff"]) => { c.save(); c.scale(1, -1); upArrow(c, o, T); c.restore(); };
  /** 修正內容的小箭頭照數值正負（第 2 版；沒給數值當正）：正＝朝上的橘黃、負＝朝下的青色。 */
  const signArrow = (c, o, opt) => ((opt?.value ?? 1) < 0 || opt?.value === false ? downArrow(c, o) : upArrow(c, o));

  // ---------------- 第 2 版新增的共用零件 ----------------
  /** 亮色單手劍（第 2 版：必修 1）。第 1 批 W.swordArt 的柄是深握柄色、護手是暗金，在深色圓底上整把只剩一條灰褐細線；
   *  這裡照規則 6 換亮一階：刃亮鋼加寬到上限（刃寬 5.8／全長 28.5≈1/5）、護手換金、握柄換皮色（混亮一階 #a8703e）、柄頭金。直立座標：刃尖朝 −y，中心在原點。
   *  B＝刃的三色（本色、亮面、暗面），附魔的劍換刃色。 */
  const BLADE_STEEL = [STEEL, "#ffffff", "#98a2ae"];
  const bladeSword = (c, o, B = BLADE_STEEL) => { c.save(); c.translate(0, -0.65);
    poly(c, B[0], [[-2.9, 3.6], [-2.9, -9.4], [0, -13.6], [2.9, -9.4], [2.9, 3.6]], 0.4);
    poly(c, B[1], [[-2.9, 3.6], [-2.9, -9.4], [0, -13.6], [-0.4, -9.4], [-0.4, 3.6]]); f(c, B[2], () => c.rect(1.3, -9, 1.6, 12.6));
    rr(c, GOLD, -6.4, 3.4, 12.8, 3.4, 1.5); f(c, "#fff0b0", () => c.roundRect(-6.4, 3.4, 12.8, 1.2, [1.5, 1.5, 0, 0]));
    rr(c, "#a8703e", -1.7, 6.6, 3.4, 5.4, 1); ci(c, GOLD, 0, 12.6, 2.4); c.restore(); };
  /** 斜放（刃尖朝右上）的亮劍，k＝縮放。k 0.84 時劍尖、柄頭剛好貼到圓片色環的內緣。 */
  const diagSword = (k = 0.84, B) => (c, o) => at(c, 0, 0, k, (q) => bladeSword(q, o, B), PI / 4);
  /** 亮鋼匕首（第 2 版：必修 1 的背刺）：刃寬 5.6、刃尖朝 +y。 */
  const dagger = (c, o) => { poly(c, STEEL, [[-2.8, -3.4], [2.8, -3.4], [2.8, 2.6], [0, 8.6], [-2.8, 2.6]], 0.4); poly(c, "#ffffff", [[-2.8, -3.4], [-0.3, -3.4], [-0.3, 8], [-2.8, 2.6]]); rr(c, GOLD, -4.8, -5.6, 9.6, 2.8, 1.2); rr(c, "#a8703e", -1.5, -10, 3, 4.6, 1); ci(c, GOLD, 0, -10.4, 1.9); };
  /** 雙 V（第 2 版：必修 2 的衝鋒、位移徽章）：兩個朝右的粗 V 拉開，中間留 ≥4 單位（12px 圖樣裡約 2.5 個裝置像素）的底色；後面那個降一階色。 */
  const chevron = (c, x, col, hi) => { const P = [[x - 5.4, -9], [x - 0.4, -9], [x + 5.4, 0], [x - 0.4, 9], [x - 5.4, 9], [x + 0.4, 0]]; poly(c, col, P, 0.5); if (hi) poly(c, hi, [[x - 5.4, -9], [x - 0.4, -9], [x + 5.4, 0], [x + 0.4, 0]]); };
  const dashArt = (c, o) => { chevron(c, -5.2, "#b9a57e", o.tiny ? null : "#d8c8a0"); chevron(c, 5.2, CREAM, o.tiny ? null : "#ffffff"); };
  /** 範圍徽章（第 2 版：必修 4）：九宮格留給形狀，徽章改成「向外擴的衝擊環」——中心一顆黃白的小爆星，外面一圈斷成四段的橘色粗環（斷口在上下左右），環外四個斜角各一道往外的短衝擊線。 */
  const areaBurst = (c, o) => { for (let i = 0; i < 4; i++) { const a = (i * PI) / 2; st(c, "#ffb23a", 3.2, (x) => x.arc(0, 0, 7.4, a + 0.32, a + PI / 2 - 0.32), "butt"); at(c, 0, 0, 1, (q) => poly(q, "#ffe08a", [[9.4, -1.3], [11.6, 0], [9.4, 1.3]], 0.6), a + PI / 4); }
    poly(c, "#ffd23f", starPts(0, 0, 4.8, 2.4, 6, -PI / 2), 0.4); ci(c, "#ffffff", 0, 0, 1.7); if (!o.tiny) st(c, "#fff0b0", 1.2, (x) => x.arc(0, 0, 8.4, PI * 1.1, PI * 1.4), "butt"); };
  /** 中間破口的短厚磚牆（第 2 版：必修 3）：上下兩塊石磚，破口邊緣是鋸齒，旁邊兩顆碎石。 */
  const brokenWall = (c, o) => { poly(c, STONE, [[-4, -10.6], [4, -10.6], [4, -4.6], [2, -3.4], [0.4, -5], [-1.8, -3.2], [-4, -4.4]], 0.4); poly(c, STONE, [[-4, 10.6], [4, 10.6], [4, 4.2], [1.8, 3.2], [0, 4.8], [-2, 3.4], [-4, 4.8]], 0.4);
    f(c, STONE_L, () => { c.rect(-4, -10.6, 8, 1.8); c.rect(-4, 4.8, 2, 5.8); c.rect(-4, -10.6, 2, 6); }); if (!o.tiny) { f(c, STONE_D, () => { c.rect(-4, -7.2, 8, 1); c.rect(-4, 7.6, 8, 1); }); ci(c, STONE_L, 7.6, -6.6, 1.3); ci(c, STONE_L, 8.4, 6.8, 1.1); } };
  /** 油表面（第 2 版：可修）：第 3 批的「一灘加一滴」染成褐色像一坨醬；圓片裡換成琥珀黃（同一個液體外形），水滴上加白色反光。試過壓扁成一灘不畫那一滴：18px 像麵包、熱狗。 */
  const oilPool = (c, o) => { QS.ACT.surface.d(c, o, ["#e8a830", "#fff0b0"], "oil"); el(c, "#ffffff", -3.7, -3.6, 1.1, 2.2, 0.4); if (!o.tiny) el(c, "#ffffff", 4.6, 5.2, 2, 0.7); };
  /** 靈魂連結的雙環（11-12：效果「分擔傷害」改用；畫法照抄 qIconsStatus.js 的 NEW.soul_link，一筆不改——這個檔比第⑤批先載入，不能呼叫它）。 */
  const soulRings = (c, o) => { const ring = (q, x, a0 = 0, a1 = TAU) => st(q, "#c8a0ff", o.tiny ? 3.2 : 2.8, (p) => p.arc(x, 0.4, 5.6, a0, a1), "butt"); ring(c, -3.8); halo(c, o, (q) => { ring(q, 3.8); if (!o.tiny) st(q, "#efe2ff", 1.1, (p) => p.arc(3.8, 0.4, 5.6, PI * 1.15, PI * 1.55), "butt"); }); halo(c, o, (q) => ring(q, -3.8, -0.75, 0.05)); if (!o.tiny) st(c, "#efe2ff", 1.1, (p) => p.arc(-3.8, 0.4, 5.6, PI * 1.15, PI * 1.55), "butt"); };
  /** 縮到圓片色環以內（第 2 版：可修「畫出圓片」）：方的、寬的圖樣四角會頂到色環。 */
  const fit = (d, k = 0.84) => (c, o, T, opt) => at(c, 0, 0, k, (q) => d(q, o, T, opt));
  /** 姿態類狀態（第 2 版：補畫）：骨架徽章「姿態」同一個六角臂章外形，底色與中間的紋章換成各姿態的題材。 */
  const hexPts = (R) => [0, 1, 2, 3, 4, 5].map((i) => [Math.cos((i / 6) * TAU - PI / 2) * R, Math.sin((i / 6) * TAU - PI / 2) * R]);
  const stancePlate = (col, hi, emblem) => (c, o) => { const P = hexPts(10.6); poly(c, col, P, 0.5); poly(c, hi, [P[0], P[5], P[4], [-5.6, 3], [-5.6, -4.4]]); halo(c, o, (q) => emblem(q, o)); };

  // =====================================================================
  // 效果 51 個（client/src/render/skillParts.ts 的 EFFECT；teleport_target、swap_any 兩個別名和 swap 同圖）。src＝這個圖樣哪裡來的。
  // =====================================================================
  const SURF_TINT = { fire: "fire", water: "water", ice: "ice", poison: "poison", holy: "holy", oil: "earth", darkness: "shadow", smoke: "steel" };
  const surface = (id) => (c, o) => { const t = SURF_TINT[id] ?? "water"; QS.ACT.surface.d(c, o, QS.TINT[t] ?? QS.TINT.water, t); };
  const spirit = (T) => (c, o) => QS.ACT.summon.d(c, o, T ?? QS.ACT.summon.def);
  const EFFECT = {
    damage: { zh: "傷害", topic: "白色四芒閃光", src: "b3:hit", d: act("hit") },
    heal: { zh: "治療", topic: "綠色粗十字", src: "b3:heal", d: act("heal") },
    shield: { zh: "護盾", topic: "淡藍小盾（白十字紋）", src: "b3:shield", d: act("shield") },
    cleanse: { zh: "淨化", topic: "一大兩小三顆薄荷綠的亮晶晶", d: (c, o) => { star4(c, "#9af0d0", -2, 1.6, 9); star4(c, "#d8fff0", 6.6, -6.4, 4.2, null); if (!o.tiny) star4(c, "#d8fff0", 6.4, 6.6, 3, null); } },
    push: { zh: "推擊", topic: "朝右上的黃白粗箭頭", src: "b3:push", d: act("push") },
    pull: { zh: "拉扯", topic: "朝左下的青色粗箭頭、尾端圓鉤", src: "b3:pull", d: act("pull") },
    knock_prone: { zh: "擊倒", topic: "黃色撞擊星壓在地面線上", src: "b3:knockdown", d: act("knockdown") },
    shockwave: { zh: "震波", topic: "地面線上一顆撞擊星，兩側各一道往外的弧", d: (c, o) => { rr(c, "#b8862a", -11, 6.4, 22, 4.4, 2); burstStar(c, 0, -0.6, 6.6); for (const s of [-1, 1]) st(c, "#ffe9a8", 2.8, (x) => x.arc(0, 1, 10.2, s > 0 ? -PI * 0.36 : PI * 1.1, s > 0 ? -PI * 0.1 : PI * 1.36), "round"); } },
    teleport: { zh: "傳送", topic: "紫色傳送圈（看得到洞），中心一顆白閃光", d: (c, o) => { ci(c, "#2a1650", 0, 0, 7.6); st(c, "#9a6ad8", 4.4, (x) => x.arc(0, 0, 8, 0, TAU)); st(c, "#e0c8ff", 1.6, (x) => x.arc(0, 0, 8.8, PI * 1.05, PI * 1.6), "butt"); star4(c, "#ffffff", 0, 0, 5.6, null); } },
    dash: { zh: "衝鋒", topic: "兩個朝右的粗 V 拉開（前米白、後降一階的褐米色）", d: dashArt }, /* 第 2 版：第 3 批的兩個 V 在 18px 黏成一塊米白折角（像紙飛機），圓片裡改成拉開的雙 V；主圖記號不動 */
    charge_through: { zh: "直線衝撞", topic: "黃色長箭頭從一道短厚磚牆中間的破口穿過去", d: (c, o) => { brokenWall(c, o); halo(c, o, (q) => at(q, 0.4, 0, 1.06, (p) => arrowS(p, "#ffd23f", "#ffffff"))); } }, /* 第 2 版：等長的灰直桿＋黃箭頭＝十字、加號；牆改短厚、上下兩塊中間破口 */
    shadowstep: { zh: "瞬步", topic: "米白人形背後繞過來一道紫色弧箭頭", d: (c, o) => { bust(c, CREAM, 3.4, 2.6, 0.82); st(c, "#b48aee", 3.6, (x) => x.arc(2.6, 0.6, 9, PI * 0.6, PI * 1.66), "butt"); at(c, 2.6 + Math.cos(PI * 1.66) * 9, 0.6 + Math.sin(PI * 1.66) * 9, 1, (q) => poly(q, "#b48aee", [[-4.8, -1], [4.8, -1], [0, 5]], 0.4), -1.1); } },
    leap: { zh: "跳躍", topic: "一道拱形的跳躍軌跡，落點朝下的箭頭", d: (c, o) => { st(c, CREAM, 3.8, (x) => { x.moveTo(-9, 7.6); x.quadraticCurveTo(-2, -15.5, 6, 1.6); }, "butt"); poly(c, CREAM, [[1.4, 1.6], [10.8, 0.4], [7.6, 9.6]], 0.5); rr(c, "#b8862a", -11, 7.6, 6, 3, 1.5); } },
    swap: { zh: "交換位置（傳送他人、任意兩者互換同圖）", topic: "上下兩個反向的箭頭（米白朝右、青色朝左）", d: (c, o) => { at(c, 0, -5, 1, (q) => arrowS(q, CREAM, "#ffffff")); at(c, 0, 5, 1, (q) => arrowS(q, "#6ae0ff", "#d8f8ff"), PI); } },
    apply_status: { zh: "施加狀態（沒指定是哪個狀態時）", topic: "掛在橫桿上的淡紫小旗（燕尾）", d: banner },
    create_surface: { zh: "產生表面（沒指定哪種表面時）", topic: "一灘水漬上落下一滴", src: "b3:surface", d: surface("water") },
    blow_surface: { zh: "吹送", topic: "一道捲起來的風，吹著一顆水滴", d: (c, o) => { st(c, "#7fe0c0", 3.6, (x) => { x.moveTo(-10, -2.4); x.lineTo(2.6, -2.4); x.arc(2.6, -6, 3.6, PI / 2, -PI * 0.8, true); }); st(c, "#dcfff1", 2.8, (x) => { x.moveTo(-9, 3.6); x.lineTo(-1.6, 3.6); }); at(c, 6.4, 4.6, 0.46, (q) => drop(q, "#4aa8ff", 0, 0, 1), -0.9); } },
    enter_form: { zh: "進入形態", topic: "淡紫色的獸掌印", d: (c, o) => paw(c, o) },
    leave_form: { zh: "解除形態", topic: "米白人形，左下一個變暗縮小的掌印", d: (c, o) => { at(c, -6.4, 5.4, 0.46, (q) => paw(q, { tiny: true }, "#9a7ad0")); halo(c, o, (q) => bust(q, CREAM, 2.6, 1.2, 1.02)); } },
    clear_surface: { zh: "清除表面", topic: "一把掃帚（木柄、金色帚頭）", d: (c, o) => { ln(c, "#a06a36", 2.8, [[8, -9.6], [-1, -1]]); poly(c, GOLD, [[-4.4, -3.4], [2.4, 3.4], [-3.4, 9.8], [-10.4, 2.8]], 0.6); poly(c, "#fff0b0", [[-4.4, -3.4], [-1.6, -0.6], [-8, 5], [-10.4, 2.8]]); ln(c, "#8a5a32", 2.2, [[-3.6, -2.6], [1.4, 2.4]]); if (!o.tiny) star4(c, "#ffffff", 7, 6, 3.6, null); } },
    destroy_object: { zh: "摧毀物件", topic: "一個木箱，中間一道裂開的閃電形裂縫", d: (c, o) => { crate(c, { small: true }, 0, 0, 18); ln(c, OUT, 3.6, [[-1.6, -9.4], [2, -2.6], [-2.4, 1.6], [1.4, 9.4]], "miter"); ln(c, "#ffd23f", 1.3, [[-1.6, -9.4], [2, -2.6], [-2.4, 1.6], [1.4, 9.4]], "miter"); } },
    create_obstacle: { zh: "產生障礙", topic: "三排交錯的灰石磚牆", d: fit((c, o) => { for (const [x, y, w] of [[-10, -9.6, 9.4], [0.6, -9.6, 9.4], [-10, -3, 4.6], [-4.2, -3, 8.4], [5.4, -3, 4.6], [-10, 3.6, 9.4], [0.6, 3.6, 9.4]]) { rr(c, STONE, x, y, w, 5.6, 1.2); f(c, STONE_L, () => c.roundRect(x, y, w, 1.8, [1.2, 1.2, 0, 0])); } }, 0.82) }, /* 第 2 版：縮到色環以內 */
    raise_terrain: { zh: "隆起地形", topic: "地面裂開、中間頂出一根高高的石柱，柱頂左上一個小黃箭頭", d: (c, o) => { rr(c, STONE_D, -10.8, 6.6, 21.6, 4, 1.6); rr(c, STONE, -4.6, -8.6, 9.2, 16.4, 1.4); f(c, STONE_L, () => c.roundRect(-4.6, -8.6, 9.2, 2.6, [1.4, 1.4, 0, 0])); f(c, STONE_L, () => c.rect(-4.6, -8.6, 2.4, 16)); for (const s of [-1, 1]) poly(c, STONE, [[s * 5.8, 6.6], [s * 9.4, 2.6], [s * 10.4, 6.6]], 0.3); at(c, -7.8, -2.4, 0.4, (q) => upArrow(q, o, ["#ffd23f", "#ffffff"])); } }, /* 第 2 版：梯形石台＋大箭頭和「增益」徽章（箭頭＋底槓）同一個構圖；改成石柱變高、箭頭縮小 */
    lower_terrain: { zh: "下陷地形", topic: "地面中間凹下去一個坑，上面一個朝下的黃箭頭", d: (c, o) => { poly(c, STONE, [[-10.4, 2.6], [-5.4, 2.6], [-3.6, 8], [3.6, 8], [5.4, 2.6], [10.4, 2.6], [10.4, 10.4], [-10.4, 10.4]], 0.4); f(c, STONE_L, () => { c.rect(-10.6, 2.2, 5.4, 1.8); c.rect(5.2, 2.2, 5.4, 1.8); }); at(c, 0, -2.8, 0.6, (q) => { q.scale(1, -1); upArrow(q, o, ["#ffd23f", "#ffffff"]); }); } },
    intercept: { zh: "替隊友擋攻擊", topic: "米白人形前面擋著一面藍盾", d: (c, o) => { bust(c, CREAM, -3.6, 0.6, 0.98); halo(c, o, (q) => at(q, 4.6, 2.8, 0.62, (p) => QS.ACT.shield.d(p, o, QS.ACT.shield.def))); } },
    add_stack: { zh: "累積層數", topic: "三根越來越高的金色粗條", src: "b3:builder", d: act("builder") },
    consume_stack: { zh: "消耗層數", topic: "兩根金色粗條，第三根的位置炸成一顆橘色爆星", d: (c, o) => { for (const [x, h] of [[-10.6, 7.6], [-3.4, 12.6]]) { rr(c, GOLD, x, 9.6 - h, 6.6, h, 1.6); f(c, "#fff6c8", () => c.roundRect(x, 9.6 - h, 6.6, 2.8, [1.6, 1.6, 0, 0])); } halo(c, o, (q) => at(q, 5.6, -3.6, 0.6, (p) => QS.ACT.detonate.d(p, o, QS.ACT.detonate.def))); } },
    consume_status: { zh: "消耗狀態", topic: "橘色十角爆炸、黃白芯", src: "b3:detonate", d: act("detonate") },
    place_trap: { zh: "放置陷阱", topic: "底板上一排朝上的鋼牙", src: "b3:trap", d: fit(act("trap"), 0.8) }, /* 第 2 版：縮到色環以內 */
    grant_ap: { zh: "給予 AP", topic: "黃色閃電（和卡片的 AP 同一個）加白色加號", d: (c, o) => { at(c, -1.6, 0.6, 0.95, (q) => bolt(q, o)); plus(c, o, 6.6, 6, 0.86); } },
    reset_cooldown: { zh: "重置冷卻", topic: "藍邊白面的鐘，右上角一顆白閃光", d: (c, o) => { at(c, -1.2, 1.2, 0.9, (q) => clock(q, o)); halo(c, o, (q) => star4(q, "#ffe14d", 6.6, -6.4, 5, "#ffffff")); } },
    cheat_death: { zh: "免死", topic: "紅心，右下一面小藍盾", d: (c, o) => { at(c, -1.2, -1, 1, (q) => heartArt(q, o)); halo(c, o, (q) => at(q, 5.6, 5, 0.5, (p) => QS.ACT.shield.d(p, o, QS.ACT.shield.def))); } },
    redirect_damage: { zh: "分擔傷害", topic: "兩個扣在一起的淡紫圓環（前後交扣；同第⑤批狀態「靈魂連結」）", src: "b5:status.soul_link", d: soulRings }, /* 11-12（第⑤批複審可修 7）：原本是 Y 形分岔箭頭；唯一施加「靈魂連結」的效果就是分擔傷害，改成同一個雙環 */
    copy_skill: { zh: "複製技能", topic: "兩張疊著的卡（後面紫、前面米白有金星）", d: (c, o) => { rr(c, "#9a86d8", -9, -10, 11.4, 14.6, 2); halo(c, o, (q) => { rr(q, CREAM, -2.4, -4.6, 11.4, 14.6, 2); poly(q, "#e8a020", starPts(3.3, 2.7, 4, 1.7, 5), 0.2); }); } },
    extra_reaction: { zh: "額外反應", topic: "綠色回轉箭頭（和「反應」同一個）加白色加號", d: (c, o) => { at(c, -1.4, 1.4, 0.88, (q) => react(q, o)); plus(c, o, 6.8, -6.6, 0.8); } },
    hurl_object: { zh: "投擲物件", topic: "一個木箱沿弧線飛出去", d: (c, o) => { st(c, CREAM, 2.8, (x) => { x.moveTo(-9.8, 9); x.quadraticCurveTo(-8.6, -2.6, -1.6, -4.4); }, "round"); crate(c, { small: true }, 3.8, -3.4, 12.4); } },
    topple: { zh: "推倒", topic: "一根斜倒的石柱，底下地面線", d: (c, o) => { rr(c, "#b8862a", -11, 6.8, 22, 4, 2); at(c, -4.6, 6.6, 1, (q) => { rr(q, STONE, -3.2, -16.4, 6.4, 16.4, 1.2); f(q, STONE_L, () => q.rect(-3.2, -16, 2.2, 15.6)); rr(q, STONE_D, -4.4, -18, 8.8, 3.2, 1); }, 0.74); if (!o.tiny) burstStar(c, 7.6, 3.4, 3.4); } },
    restore_resource: { zh: "回復資源", topic: "軟木塞圓底藥瓶，裝著藍色的水", d: (c, o) => { rr(c, "#dcecff", -2.4, -9, 4.8, 6, 1); rr(c, "#a06a36", -3.2, -11, 6.4, 3, 1); ci(c, "#dcecff", 0, 2.6, 8); c.save(); c.beginPath(); c.rect(-9, -0.6, 18, 12); c.clip(); ci(c, "#4a8ae0", 0, 2.6, 6.4); c.restore(); el(c, "#ffffff", -3, 4, 1.3, 2.6, 0.4); } },
    steal_buff: { zh: "奪取增益", topic: "紫色馬蹄形磁鐵（白色兩極）吸著一顆金星", d: (c, o) => { st(c, "#9a6ad8", 5.2, (x) => { x.moveTo(-5.6, -1); x.lineTo(-5.6, 3.6); x.arc(0, 3.6, 5.6, PI, 0, true); x.lineTo(5.6, -1); }, "butt"); rr(c, "#ffffff", -8.2, -4.6, 5.2, 4, 0.8); rr(c, "#ffffff", 3, -4.6, 5.2, 4, 0.8); halo(c, o, (q) => poly(q, "#ffd23f", starPts(0, -6.6, 4.6, 1.9, 5), 0.2)); } },
    dispel: { zh: "驅散", topic: "淡紫的增益箭頭（同「增益」徽章的外形）被一道紅斜槓劃掉", d: (c, o) => { at(c, 0, 0.4, 0.92, (q) => QS.ACT.buff.d(q, o, ["#cfc4ff", "#ffffff"])); halo(c, o, (q) => { if (o.tiny) ln(q, OUT, 5.4, [[-8.6, 8.6], [8.6, -8.6]]); ln(q, "#ff4a5a", 3.4, [[-8.6, 8.6], [8.6, -8.6]]); }); } }, /* 第 2 版：斷成兩截的箭頭像「上傳」；改成增益箭頭被劃掉（和致盲同一個劃掉的語言） */
    reveal: { zh: "揭露", topic: "一隻睜開的眼睛（米白眼白、藍瞳）", d: (c, o) => { f(c, CREAM, () => { c.moveTo(-10.8, 0); c.quadraticCurveTo(0, -11, 10.8, 0); c.quadraticCurveTo(0, 11, -10.8, 0); c.closePath(); }); ci(c, "#4aa8ff", 0, 0, 4.8); ci(c, "#16223a", 0, 0, 2.3); if (!o.tiny) ci(c, "#ffffff", -1.5, -1.6, 1.1); } },
    revive: { zh: "復活", topic: "金色的心，兩側一對白翅膀", d: fit((c, o) => { for (const s of [-1, 1]) poly(c, "#fffaf0", [[s * 3.6, -3], [s * 11, -9], [s * 10.6, -2], [s * 8.4, 2.4], [s * 4, 3.6]], 0.5); heart(c, "#ffd04a", 0, 1.6, 1.02); if (!o.tiny) el(c, "#fff6c8", -2.8, -1.8, 1.8, 1.2, -0.6); }, 0.9) }, /* 第 2 版：縮到色環以內 */
    delayed_damage: { zh: "定時炸彈", topic: "圓炸彈、彎引信、引信頭一顆火花", d: (c, o) => { st(c, "#a06a36", 2.2, (x) => { x.moveTo(2.6, -5.6); x.quadraticCurveTo(4.6, -10, 7.6, -8.6); }); rr(c, "#8a8f99", -0.4, -7.2, 5, 3.6, 1); ci(c, "#5f6a8c", -1, 2.8, 7.8); el(c, "#a8b2d0", -3.8, -0.4, 2.8, 1.7, -0.6); poly(c, "#ffd23f", starPts(8.2, -8.2, 3.6, 1.5, 6), 0.2); } },
    summon: { zh: "召喚", topic: "一隻青色的小靈", src: "b3:summon", d: spirit() },
    zone: { zh: "持續區域", topic: "地上一圈藍色虛線環，上面浮著一個小沙漏", d: (c, o) => { for (let i = 0; i < 6; i++) st(c, "#8ab8f0", 2.8, (x) => x.ellipse(0, 6.2, 9.6, 3.6, 0, (i / 6) * TAU + 0.18, ((i + 1) / 6) * TAU - 0.18), "butt"); halo(c, o, (q) => at(q, 0, -3.4, 0.64, (p) => hourglass(p, o))); } }, /* 第 2 版：金環＋光點和聖光表面撞；環換成沙漏框的藍色、虛線 */
    rule_change: { zh: "規則改變", topic: "一張卷軸（上下金色卷軸桿、三行字）", d: (c, o) => { rr(c, CREAM, -6.8, -8.4, 13.6, 16.8, 1.2); rr(c, "#d8b04a", -8.8, -10.6, 17.6, 4, 2); rr(c, "#d8b04a", -8.8, 6.6, 17.6, 4, 2); if (!o.tiny) for (const [y, w] of [[-4, 8.4], [-0.8, 8.4], [2.4, 5.4]]) f(c, "#8a6a2a", () => c.rect(-4.2, y, w, 1.7)); } },
    gamble: { zh: "賭注", topic: "一顆斜放的白骰子", d: dice },
    grant_skill: { zh: "暫時獲得技能", topic: "一張米白的卡（金星）加白色加號", d: (c, o) => { rr(c, CREAM, -8.8, -8.4, 11.6, 16.4, 2); poly(c, "#e8a020", starPts(-3, 0, 4, 1.7, 5), 0.2); plus(c, o, 6.6, -5.8, 0.82); } },
    sacrifice_summon: { zh: "獻祭召喚物", topic: "小靈背後一圈橘色的爆炸", d: fit((c, o) => { poly(c, "#ff7a2a", starPts(0, 0, 11, 6.6, 10), 0.3); halo(c, o, (q) => at(q, 0, 0.6, 0.74, (p) => QS.ACT.summon.d(p, o, QS.ACT.summon.def))); }, 0.9) }, /* 第 2 版：縮到色環以內 */
    inscribe: { zh: "刻印", topic: "圓頂的石碑，上面一個金色菱形符文", d: tablet },
    detonate_runes: { zh: "引爆符文", topic: "符文石碑背後一圈橘色的爆炸", d: fit((c, o) => { poly(c, "#ff7a2a", starPts(0, 0, 11, 6.6, 10), 0.3); halo(c, o, (q) => at(q, 0, 0.4, 0.64, (p) => tablet(p, o))); }, 0.9) }, /* 第 2 版：縮到色環以內 */
  };
  const EFFECT_ALIAS = { teleport_target: "swap", swap_any: "swap" };

  // =====================================================================
  // 表面 1 個形（8 種表面染色；第 3 批的地面效果記號，依表面換外形）
  // =====================================================================
  const SURFACE = Object.fromEntries(Object.entries({ water: "水", poison: "毒", oil: "油", fire: "火焰", ice: "冰", holy: "聖光", darkness: "黑暗", smoke: "煙霧" }).map(([id, zh]) => [id, { zh: zh + "表面", topic: { fire: "餘燼上三撮火苗", ice: "薄冰加兩根冰刺", holy: "地上一圈金光加一顆光點", darkness: "兩團紫色的霧", smoke: "兩團灰白的煙", oil: "一灘加一滴（琥珀黃、白色反光）" }[id] ?? "一灘水漬上落下一滴（染表面色）", src: id === "oil" ? "new" : "b3:surface", d: id === "oil" ? oilPool : surface(id) }]));

  // =====================================================================
  // 狀態（圓片裡「施加狀態：某某」用的 16 個；狀態圖示本身是另一批，沒列在這裡的由頁面用現行圖樣頂著）
  // =====================================================================
  const S48 = (id) => from48((c, o) => Q.ART.status[id].d(c, o));
  const STATUS = {
    slow: { zh: "緩速", topic: "一只金殼懷錶", src: "b3:slow", d: act("slow") },
    frozen: { zh: "冰凍", topic: "三根淡藍冰晶", src: "style:status.frozen", d: S48("frozen") },
    root: { zh: "定身", topic: "鐵球加兩節鎖鏈（腳鐐）", d: (c, o) => { for (const [x, y] of [[-3.6, -3], [-7.2, -6.8]]) st(c, "#e4e9ef", 2.4, (p) => p.ellipse(x, y, 2.5, 1.7, 0.8, 0, TAU)); ci(c, "#b4bcc6", 3, 3.4, 7.2); el(c, "#f2f5f8", 0.4, 0.6, 2.8, 1.7, -0.6); f(c, "rgba(0,0,0,0.18)", () => { c.arc(3, 3.4, 7.2, -0.2, 1.8); c.closePath(); }); } }, /* 第 2 版：鐵球與鎖鏈提亮一階 */
    stun: { zh: "暈眩", topic: "頭上繞一圈的暈眩弧，弧上一大一小兩顆黃星", d: (c, o) => { st(c, "#fff0b0", 2.4, (x) => x.ellipse(0, 1.6, 10, 4.4, 0, PI * 0.05, PI * 0.95), "round"); poly(c, "#ffd23f", starPts(-3.4, -2.4, 7.4, 3.2, 5), 0.5); if (!o.tiny) poly(c, "#fff6c8", [[-3.4, -9.8], [-5.4, -4], [-3.4, -2.4]]); poly(c, "#ffd23f", starPts(6.4, 4.4, 4.2, 1.8, 5), 0.4); } }, /* 第 2 版：風格樣張的三顆星在 18px 只剩一顆（和卡片「啟動」的金星同形）；改成一大一小兩顆加一道暈眩弧 */
    silenced: { zh: "沉默", topic: "紫色對話框，裡面一個深色的叉", d: fit((c, o) => { poly(c, "#c890ff", [[-5.4, 3], [-6.8, 10], [0.6, 3.6]], 0.4); rr(c, "#c890ff", -10, -9.4, 20, 13.8, 5); f(c, "#e6ccff", () => c.roundRect(-8.4, -8.4, 16.8, 3, 3)); ln(c, INK, 2.6, [[-4.4, -6], [4.4, 1.6]]); ln(c, INK, 2.6, [[4.4, -6], [-4.4, 1.6]]); }, 0.86) }, /* 第 2 版：縮到色環以內 */
    weaken: { zh: "虛弱", topic: "鋼灰色朝下的粗箭頭加頂槓", src: "b3:curse", d: act("curse", ["#c3ccd6", "#ffffff"]) },
    vulnerable: { zh: "易傷", topic: "一面裂開的紅盾", d: fit((c, o) => { shieldBlue(c, o, ["#e8455a", "#ffb0b8"]); ln(c, OUT, 2.6, [[1.4, -10.4], [-1.8, -3.6], [2.2, 0.6], [-0.8, 5], [0.6, 10.4]], "miter"); }, 0.86) }, /* 第 2 版：縮到色環以內 */
    feared: { zh: "恐懼", topic: "風格樣張的恐懼", src: "style:status.feared", d: S48("feared") },
    blinded: { zh: "致盲", topic: "淡紫的眼睛被一道紅斜槓劃掉", d: (c, o) => { f(c, "#e6d2ff", () => { c.moveTo(-10.8, 0); c.quadraticCurveTo(0, -9.6, 10.8, 0); c.quadraticCurveTo(0, 9.6, -10.8, 0); c.closePath(); }); ci(c, "#7a4ec0", 0, 0, 4); halo(c, o, (q) => ln(q, "#ff5a6a", 3.4, [[-8, 8.4], [8, -8.4]])); } },
    taunted: { zh: "嘲諷", topic: "橘紅色的青筋記號（四道彎角）", d: (c, o) => { for (let i = 0; i < 4; i++) { c.save(); c.rotate((i * PI) / 2); st(c, "#ff7a3a", 3.8, (x) => { x.moveTo(2.6, 9.4); x.quadraticCurveTo(2.6, 2.6, 9.4, 2.6); }); c.restore(); } } },
    marked: { zh: "被標記", topic: "紅色準星", src: "b3:mark", d: act("mark") },
    burning: { zh: "燃燒", topic: "一團火（橘外焰、黃內焰）", src: "b3:dot", d: act("dot", QS.TINT.fire, "fire") },
    poison: { zh: "中毒", topic: "一大顆綠毒滴，右上一顆泡", src: "b3:el:poison", d: from48((c, o) => QS.ELEMENT.poison.d(c, { ...o, small: true })) },
    bleed: { zh: "流血", topic: "一大一小兩顆紅血滴", src: "b3:dot", d: act("dot", QS.TINT.blood, "blood") },
    prone: { zh: "倒地", topic: "風格樣張的倒地（躺平的人形加撞擊星）", src: "style:status.prone", d: S48("prone") },
    hasted: { zh: "加速", topic: "風格樣張的加速（綠色雙箭頭）", src: "style:status.hasted", d: S48("hasted") },
    concealed: { zh: "隱蔽", topic: "紫色兜帽，裡面兩道發亮的斜眼", d: hood },
    // ---- 第 2 版補畫：技能會施加、第 1 版沒畫的 15 種（盤點見紀錄檔第 1 節）----
    guarded: { zh: "護衛", topic: "一面圓木盾（鋼邊、直木板、鋼盾心）", d: (c, o) => { ci(c, "#c3ccd6", 0, 0, 10.4); ci(c, "#b8824a", 0, 0, 8.4); f(c, "#d6a46a", () => { c.arc(0, 0, 8.4, PI * 0.5, PI * 1.5); c.closePath(); }); for (const x of [-3.4, 3.4]) f(c, "#7e5a30", () => c.rect(x - 0.6, -Math.sqrt(8.4 * 8.4 - x * x), 1.2, 2 * Math.sqrt(8.4 * 8.4 - x * x))); ci(c, "#c3ccd6", 0, 0, 3.8); ci(c, "#ffffff", -1.2, -1.2, 1.5); if (!o.tiny) st(c, "#ffffff", 1.2, (x) => x.arc(0, 0, 9.6, PI * 1.05, PI * 1.45), "butt"); } }, /* 第 1 稿金邊白盤金心像荷包蛋、第 2 稿鋼藍素面像鏡頭；改成圓木盾（木板紋讀得出是盾），和守護的鳶形盾靠剪影分 */
    defending: { zh: "守護", topic: "一面木製鳶形盾（鋼邊、中間一道米白直紋）", d: fit((c, o) => { const P = [[-9.4, -10.2], [9.4, -10.2], [9.4, 0.6], [0, 10.8], [-9.4, 0.6]], I = [[-7.2, -8.2], [7.2, -8.2], [7.2, -0.2], [0, 7.8], [-7.2, -0.2]]; poly(c, "#c3ccd6", P, 1); poly(c, "#b8824a", I, 0.6); poly(c, "#d0a068", [[-7.2, -8.2], [0, -8.2], [0, 7.8], [-7.2, -0.2]], 0.6); f(c, "#e8e0c8", () => c.rect(-1.6, -8.6, 3.2, 15.4)); if (!o.tiny) { f(c, "#ffffff", () => c.rect(-9.4, -10.2, 18.8, 1.4)); ci(c, "#ffffff", -4.6, -4.6, 1); ci(c, "#ffffff", 4.6, -4.6, 1); } }, 0.86) }, /* 圓頂長方的塔盾在 18px 像門；改成下緣尖的鳶形盾 */
    stoneskin: { zh: "石膚", topic: "灰石色的人形，身上幾道石板裂紋", d: (c, o) => { bust(c, STONE, 0, 1.6, 1.32); f(c, STONE_L, () => { c.arc(-1.4, -5.6, 2.6, PI, PI * 1.6); c.lineTo(-1.4, -5.6); c.closePath(); }); ln(c, "#6e6858", 1.6, [[-6.4, 4], [-2, 5.4], [1.6, 3.4], [6, 5.6]]); ln(c, "#6e6858", 1.6, [[-1.4, -4.6], [1.4, -2.6]]); if (!o.tiny) f(c, STONE_L, () => c.rect(-6.6, 6, 3.6, 3)); } },
    regenerating: { zh: "再生", topic: "一株綠色的嫩芽（一莖兩葉）", d: (c, o) => { ln(c, "#4aa84a", 2.8, [[0, 10.2], [0, -1.6]]); for (const s of [-1, 1]) { c.save(); c.translate(0, -1.4); c.scale(s, 1); f(c, "#6ad86a", () => { c.moveTo(0, 0); c.bezierCurveTo(1.4, -7.6, 7.4, -9.6, 10.4, -8.4); c.bezierCurveTo(9.6, -3, 5.4, 1.6, 0, 0); c.closePath(); }); if (!o.tiny) f(c, "#c8f8b8", () => { c.moveTo(1.6, -2); c.bezierCurveTo(3, -5.4, 6, -7, 8.6, -7.6); c.lineTo(8, -6.4); c.bezierCurveTo(5.4, -5.6, 3.4, -4, 1.6, -2); c.closePath(); }); c.restore(); } rr(c, "#8a5a32", -6.4, 8, 12.8, 3, 1.4); } },
    empowered: { zh: "激昂", topic: "一隻彎起來使力的手臂（膚色、握拳朝上）", d: (c, o) => { f(c, "#f0c49a", () => { c.moveTo(-10.6, 9.4); c.lineTo(-10.6, 3); c.quadraticCurveTo(-8.6, -1.6, -1.6, 0.6); c.quadraticCurveTo(3.6, -3.4, 1.6, -6.2); c.lineTo(6.6, -9); c.quadraticCurveTo(10.8, -2, 6.4, 4.6); c.quadraticCurveTo(1, 10, -4, 9.4); c.closePath(); }); ci(c, "#f0c49a", 4.4, -7.6, 4.2); el(c, "#ffe8d0", -4.4, -0.4, 3, 2, -0.3); if (!o.tiny) { el(c, "#ffe8d0", 3, -9, 1.8, 1.1, -0.5); ln(c, "#c8885a", 1.2, [[2.6, -6.2], [5.6, -5.4]]); } } },
    overwatch: { zh: "監視", topic: "一支斜舉的黃銅望遠鏡（鏡口淡藍）", d: (c, o) => at(c, 0, 0, 1, (q) => { rr(q, "#a06a36", -12.4, -2.4, 7.4, 4.8, 1.2); rr(q, "#e8bb48", -6, -3.2, 8.6, 6.4, 1.4); rr(q, "#f6d878", 1.6, -4.2, 9.4, 8.4, 1.6); f(q, "#fff6c8", () => { q.rect(-6, -3.2, 8.6, 1.6); q.rect(1.6, -4.2, 9.4, 1.8); }); rr(q, "#9c7420", 1.2, -4.4, 1.6, 8.8, 0.6); el(q, "#8fe3ff", 11.2, 0, 1.8, 3.8); if (!o.tiny) el(q, "#ffffff", 11.4, -1.4, 0.8, 1.4); }, -PI / 4) },
    infused_fire: { zh: "火焰附魔", topic: "刃換成火焰色的斜劍，劍尖一撮火", d: (c, o) => { diagSword(0.8, ["#ff8a2a", "#ffd23f", "#d8501a"])(c, o); halo(c, o, (q) => flame(q, "#ffd23f", 6.4, -6.6, 0.34)); } },
    infused_holy: { zh: "神聖附魔", topic: "刃換成金色的斜劍，劍尖一顆白色四芒光", d: (c, o) => { diagSword(0.8, ["#ffd75e", "#fff6c8", "#d8a830"])(c, o); halo(c, o, (q) => star4(q, "#ffffff", 6.2, -6.2, 4.6, null)); } },
    shielded_charged: { zh: "帶電護盾", topic: "淡藍小盾（同「護盾」），盾面一道黃閃電（取代白十字）", d: fit((c, o) => { shieldBlue(c, o); halo(c, o, (q) => at(q, 0, -0.2, 0.72, (p) => bolt(p, o))); }, 0.86) },
    stance_guard: { zh: "堅守姿態", topic: "藍色六角臂章（姿態的外形），中間一面白盾", d: stancePlate("#5a86d8", "#9ab8f0", (c, o) => at(c, 0, 0.4, 0.5, (q) => shieldBlue(q, o, ["#e8eef6", "#ffffff"]))) },
    stance_bulwark: { zh: "堅壁姿態", topic: "沙岩色六角臂章，中間一面亮色磚牆（深色磚縫）", d: stancePlate("#c89a5a", "#ecc890", (c) => { rr(c, "#5e3b1f", -6.6, -5.8, 13.2, 11.6, 1); for (const [x, y, w] of [[-6, -5.2, 5.4], [0.6, -5.2, 5.4], [-6, -0.6, 2.8], [-2.4, -0.6, 4.8], [3.2, -0.6, 2.8], [-6, 4, 5.4], [0.6, 4, 5.4]]) rr(c, "#f2dcb0", x, y, w, 3.6, 0.6); }) }, /* 第 2 版：底色換暖沙岩、磚換亮色，和鐵壁的鋼灰分開 */
    stance_ironwall: { zh: "鐵壁姿態", topic: "深鋼灰六角臂章，中間三根亮色直鐵條", d: stancePlate("#7d8794", "#aab4c0", (c, o) => { for (const x of [-4.6, 0, 4.6]) { rr(c, "#eef2f6", x - 1.5, -7, 3, 14, 1.2); if (!o.tiny) f(c, "#ffffff", () => c.rect(x - 1.5, -7, 1, 14)); } if (!o.tiny) for (const [x, y] of [[-7.6, -2.6], [7.6, -2.6], [-7.6, 2.6], [7.6, 2.6]]) ci(c, "#3a4048", x, y, 0.9); }) }, /* 第 2 版：深鋼底、三根亮鐵條 */
    stance_fury: { zh: "狂怒姿態", topic: "紅色六角臂章，中間一團黃火", d: stancePlate("#e04a3a", "#ff9a8a", (c) => { flame(c, "#ffd23f", 0, 0.6, 0.66); flame(c, "#ffffff", 0, 3.4, 0.3); }) },
    stance_holy_1: { zh: "聖輝架勢·壹", topic: "金色六角臂章，中間一顆白色四芒光", d: stancePlate("#e0a830", "#ffe08a", (c) => star4(c, "#ffffff", 0, 0.4, 7.4, "#fff6c8")) },
    stance_shadow_1: { zh: "暗影架勢·壹", topic: "紫色六角臂章，中間一彎淡紫月牙", d: stancePlate("#8a5ac8", "#b89af0", (c) => f(c, "#f0e4ff", () => { c.arc(-0.6, 0.4, 6.4, 0.6, 5.7, false); c.arc(2.2, -0.8, 5, 4.9, 1.2, true); c.closePath(); })) },
  };

  // =====================================================================
  // 條件 17 個
  // =====================================================================
  const halfHeart = (c, o, s = 1.25) => { heart(c, "#7a2a3a", 0, 1.4, s); c.save(); c.beginPath(); c.rect(-12, 1, 24, 12); c.clip(); heart(c, "#ff5a4a", 0, 1.4, s); c.restore(); st(c, "#ff9a8a", 1.5, (x) => { x.moveTo(-8.4 * (s / 1.25), 1); x.lineTo(8.4 * (s / 1.25), 1); }, "butt"); };
  /** 獨狼（11-13）：「我」單獨＝玩家自己是那隻狼（技能名孤狼撲擊、獨行者）。和「目標落單」（光柱罩住米白人形）的剪影完全不同：
   *  側面仰頭嚎叫的狼頭：口鼻朝左上、兩隻尖耳（後面那隻暗一階）、胸前一排鋸齒毛、頸後往右下拖到圖樣底。銀灰本色＋米白喉胸（亮面）＋頸後暗面；
   *  >14px 多鼻頭、閉著的眼、耳內。試過右上加一彎金色新月（夜裡嚎叫）：剪影上新月貼在後腦，20px 讀成圓耳朵（熊、老鼠），拿掉。 */
  const WOLF = [[-10.4, -9], [-5.4, -7], [-3.6, -7.2], [-1.6, -11.6], [1.4, -7.6], [3.8, -5.8], [6, -2.4], [8, 2.4], [8.8, 6.2], [7.6, 9.4], [4.6, 10.8], [-3.4, 10.4], [-2.6, 7.8], [-4.6, 6.6], [-3.2, 4.8], [-5, 3.4], [-3.6, 1.6], [-4.8, -1.6], [-8.6, -5], [-10, -7.4]];
  const loneWolf = (c, o) => {
    /* 整隻縮 0.86、往右下移：口鼻尖與頸後下緣才收在圓片色環內（半徑約 12 單位；同第 2 版「圖樣收在色環內」） */
    halo(c, o, (h0) => at(h0, 0.6, 0.4, 0.86, (q) => {
      poly(q, "#7d8794", [[0.2, -7.4], [1.6, -10.6], [3.4, -6.4]], 0.4); /* 後面那隻耳朵 */
      poly(q, "#aeb8c6", WOLF, 0.6);
      poly(q, "#eef2f6", [[-10, -7.4], [-8.6, -5], [-4.8, -1.6], [-3.6, 1.6], [-5, 3.4], [-3.2, 4.8], [-4.6, 6.6], [-2.6, 7.8], [-3.4, 10.4], [0.4, 10.4], [0, 4], [-1.6, -1.6], [-5.8, -5], [-9.4, -8]], 0.4); /* 亮面：喉與胸前的白毛 */
      poly(q, "#eef2f6", [[-10.4, -9], [-5.4, -7], [-3.6, -7.2], [-3.2, -8.4], [-6, -8.4]], 0.3); /* 亮面：口鼻上緣（審查可修 3：和喉胸同一個亮面色，規則 2 三階） */
      poly(q, "#7d8794", [[3.8, -5.8], [6, -2.4], [8, 2.4], [8.8, 6.2], [7.6, 9.4], [4.6, 10.8], [4, 3], [2.8, -3]], 0.4); /* 暗面：頸後（右下） */
      if (!o.tiny) { poly(q, "#5a6169", [[-2.6, -8], [-1.6, -10.2], [0.2, -7.8]], 0.2); ci(q, "#2a2a36", -9.8, -8.6, 0.9); ln(q, "#2a2a36", 0.9, [[-4.8, -5.8], [-3.2, -5.2]]); }
    }));
  };
  /** 自身沒有狀態（11-13）：「目標帶有狀態」的淡紫旗，被紅斜槓劃掉（＝沒有；同驅散、致盲的劃掉），右下米白小人形（＝自己；同自身血量低於、在自己的符文上）。 */
  const selfLacks = (c, o) => {
    at(c, -2, -0.6, 0.78, (q) => banner(q, o));
    halo(c, o, (q) => { const P = [[-9.4, 6.2], [5.4, -9.6]]; if (o.tiny) ln(q, OUT, 5.2, P); ln(q, "#ff4a5a", 3.4, P); });
    halo(c, o, (q) => bust(q, CREAM, 4.8, 4, 0.62)); /* 比自身血量低於的人形往內 0.8：肩膀不頂到色環 */
  };
  /** 每一下都命中（11-13，BS-1／DD-3 雙牙）：一面紅白靶，靶心插著兩把亮鋼匕首（柄朝右上、微微扇開）＝兩下都中同一個目標。
   *  和「手持指定武器」（斜放單手劍，遊戲端暫代借的）剪影不同：一個圓靶加兩根柄，對一條斜長條；和命中修正、被標記的紅準星（空心環＋十字刻度）分：靶是實心的同心圓。
   *  三階：靶本色紅 #f0503e、暗面 #b8302a（右下）；匕首照背刺那把（亮鋼、金護手、皮柄）；亮面全圖只用 #ffffff（規則 2）。≤14px 拿掉刃上的亮面與入口的洞。 */
  const BULL_RED = "#f0503e", BULL_D = "#b8302a", BULL_W = "#f6f2e6";
  /** 插在靶上的匕首（原點＝入口、柄朝 −y）：露出一截細刃、窄金護手、皮柄、金柄頭。和背刺那把同色，護手收窄（背刺的 9.6 寬護手插在靶上兩把交疊成一團）。 */
  const stuckDagger = (c, o, x, y, k, rot) => at(c, x, y, k, (q) => {
    poly(q, STEEL, [[-1.6, 0.6], [-1.6, -5.6], [1.6, -5.6], [1.6, 0.6]], 0.3); if (!o.tiny) f(q, "#ffffff", () => q.rect(-1.6, -5.6, 1.1, 6.2)); /* 刃（亮面＝左半） */
    rr(q, GOLD, -3.8, -7.8, 7.6, 2.6, 1.1); rr(q, "#a8703e", -1.5, -12, 3, 4.6, 1); ci(q, GOLD, 0, -12.8, 2);
  }, rot);
  const allStrikesHit = (c, o) => {
    /* 第 1 次試：靶小（半徑 8）、匕首 0.8 倍露出整片刃，剪影是圓身加兩根細長的柄＝甲蟲的觸角；第 2 次只露柄、寬護手，兩把交疊成一團金（像兩支毛刷）。
       這版：靶撐滿圓片、匕首收窄（刃寬 3.2、護手 7.6），兩個入口沿垂直方向拉開、微微扇開往右上，柄頭稍微超出靶緣 */
    const bx = -1.8, by = 1.8;
    ci(c, BULL_D, bx, by, 8.8); ci(c, BULL_RED, bx - 0.6, by - 0.6, 8.1); ci(c, BULL_W, bx, by, 5.8); ci(c, BULL_RED, bx, by, 3.2);
    if (!o.tiny) el(c, "#ffffff", bx - 4.4, by - 4.2, 1.9, 1.1, -0.75);
    for (const [s, dx, dy] of [[-1, -2, -1.4], [1, 1.4, 2]]) {
      if (!o.tiny) el(c, OUT, bx + dx, by + dy, 1.2, 1);
      halo(c, o, (q) => stuckDagger(q, o, bx + dx, by + dy, 0.8, PI / 4 + s * 0.22));
    }
  };
  /** 無聲（11-13，BS-1 修正內容 silent_strike）：一根淡紫羽毛（＝無聲，輕到沒有聲音；隱蔽家族的紫），前面平行壓一把亮鋼匕首（＝只在手持匕首類時生效）。
   *  兩件都照武器圖示的方向斜放（尖朝右上）、平行錯開，剪影是一條寬的斜帶加羽毛的缺口，和遊戲端暫代借的「潛行偷襲」兜帽（圓頂）分得開，也不和「所有攻擊」的交叉雙劍成 X。
   *  三階：羽毛本色 #b89af0（兜帽的亮紫）、暗面 #8a6ad8（兜帽本色）、羽軸米白；亮面全圖只用 #ffffff（規則 2）。≤14px 只留羽毛一個主體（規則 8；只剩匕首會和手持武器的劍撞）。 */
  const FEATHER = [[0, -11.2], [2.6, -9.4], [4.2, -6], [4.6, -2.6], [4.4, -0.8], [1.8, -1.8], [4, 0.6], [3.6, 3.6], [1.2, 6.4], [-1.2, 6.4], [-3.2, 4.4], [-4.2, 1.6], [-2, 0.6], [-4.4, -0.6], [-4.4, -4.4], [-3, -8.6]];
  const feather = (c, o) => {
    poly(c, "#b89af0", FEATHER, 0.5);
    poly(c, "#8a6ad8", [[0.6, -10.6], [2.6, -9.4], [4.2, -6], [4.6, -2.6], [4.4, -0.8], [1.8, -1.8], [4, 0.6], [3.6, 3.6], [1.2, 6.4], [0.6, 6.4]], 0.3); /* 暗面：羽軸右邊那半 */
    if (!o.tiny) poly(c, "#ffffff", [[-0.6, -9.6], [-2.6, -7.8], [-3.6, -4.4], [-3.4, -1.4], [-0.6, -3]], 0.3); /* 亮面：左上一片 */
    ln(c, CREAM, 1.5, [[0, -8.6], [0, 10.4]]); /* 羽軸，下面露出一截 */
  };
  const silentStrike = (c, o) => {
    if (o.tiny) { at(c, 0, 0, 0.98, (q) => feather(q, o), PI / 4); return; }
    at(c, -2.4, -2.4, 0.9, (q) => feather(q, o), PI / 4);
    halo(c, o, (q) => at(q, 3, 3, 0.8, (p) => { p.translate(0, 1.85); dagger(p, o); }, -3 * PI / 4));
  };
  const COND = {
    height_advantage: { zh: "居高臨下", topic: "一座山，山頂一個米白小人頭，右上一個朝上的黃箭頭", d: (c, o) => { poly(c, STONE, [[-10.6, 9.8], [-2.4, -3.6], [2.4, 2.6], [5, -0.6], [10.6, 9.8]], 0.6); f(c, STONE_L, () => { c.moveTo(-10.6, 9.8); c.lineTo(-2.4, -3.6); c.lineTo(-3.4, 9.8); c.closePath(); }); /* 第 2 版：山提亮一階（暗石→石、左坡亮面） */ poly(c, "#f6f2e6", [[-2.4, -3.8], [0.4, 0], [-2, 1.4], [-4.8, 0.4]], 0.3); ci(c, CREAM, -2.4, -7.6, 2.7); if (!o.tiny) poly(c, "#ffd23f", [[6.6, -10.6], [10.8, -5.4], [2.4, -5.4]], 0.3); } },
    target_hp_below: { zh: "目標血量低於", topic: "一顆心，上半暗紅、下半亮紅", d: (c, o) => halfHeart(c, o) },
    self_hp_below: { zh: "自身血量低於", topic: "半滿的心，右下一個米白小人形", d: (c, o) => { at(c, -2.4, -1.6, 0.86, (q) => halfHeart(q, o)); halo(c, o, (q) => bust(q, CREAM, 5.6, 4.6, 0.62)); } },
    target_has_status: { zh: "目標帶有狀態（沒指定狀態時）", topic: "淡紫小旗，右上一個問號", d: (c, o) => { at(c, -2, 1, 0.9, (q) => banner(q, o)); qmark(c, o, 7, -5.6, 0.9); } },
    target_on_surface: { zh: "目標站在表面上", topic: "一灘藍水漬上站著米白人形", d: (c, o) => { puddle(c); halo(c, o, (q) => bust(q, CREAM, 0, -0.8, 0.96)); } },
    from_behind: { zh: "背刺", topic: "米白人形，左上一把亮鋼匕首（金護手、皮柄）刺向背後", d: (c, o) => { bust(c, CREAM, 5.2, 3.6, 0.84); halo(c, o, (q) => { if (o.tiny) at(q, -0.4, -0.4, 0.75, (p) => poly(p, OUT, [[-5, -4.6], [5, -4.6], [5, 3.2], [0, 11.6], [-5, 3.2]], 0.6), -PI / 4); at(q, -0.4, -0.4, 0.75, (p) => dagger(p, o), -PI / 4); }); } }, /* 第 2 版：匕首換亮鋼加寬（刃寬 5.6）、放大到佔圖樣約一半；18px 時在刃和人形之間墊一道底色縫 */
    flanked: { zh: "夾擊", topic: "中間米白人形，左右各一個朝內的紅色三角", d: (c, o) => { bust(c, CREAM, 0, 0.8, 0.8); for (const s of [-1, 1]) poly(c, ENEMY, [[s * 10.8, -4.6], [s * 5.6, 0.6], [s * 10.8, 5.8]], 0.5); } },
    target_isolated: { zh: "目標落單", topic: "一道從上面打下來的光柱，底下一個米白人形", d: (c, o) => { f(c, "rgba(255,236,170,0.72)", () => { /* 第 2 版：光柱提亮一階（0.42→0.72 不透明） */ c.moveTo(-2.8, -10.8); c.lineTo(2.8, -10.8); c.lineTo(9.8, 8); c.lineTo(-9.8, 8); c.closePath(); }); el(c, "#ffe9a8", 0, 8, 9.8, 2.6); halo(c, o, (q) => bust(q, CREAM, 0, 1.6, 0.8)); } },
    moved_this_turn: { zh: "本回合移動過", topic: "一隻褐色的靴子，後面兩道速度線", src: "style:hud.move", d: boot },
    first_round: { zh: "第一輪", topic: "一個金色的粗體數字 1", d: (c, o) => { poly(c, "#ffd23f", [[-1.6, -10.2], [3.2, -10.2], [3.2, 6], [6.8, 6], [6.8, 10.2], [-6.2, 10.2], [-6.2, 6], [-1.6, 6], [-1.6, -4.4], [-5.8, -2.4], [-5.8, -6.8]], 0.5); f(c, "#fff6c8", () => c.rect(-1.6, -10.2, 1.8, 16)); } },
    cast_tag_this_turn: { zh: "本回合施放過同類技能", topic: "一張斜放的金色吊牌（有孔）", d: fit(tag, 0.88) },
    self_concealed: { zh: "潛行偷襲", topic: "紫色兜帽，裡面兩道發亮的斜眼", d: hood },
    on_own_rune: { zh: "目標站在自己的符文上", topic: "符文石碑，右下一個米白小人形", d: (c, o) => { at(c, -2.6, -0.6, 0.86, (q) => tablet(q, o)); halo(c, o, (q) => bust(q, CREAM, 5.4, 4.6, 0.62)); } },
    adjacent_ally: { zh: "身旁有友方", topic: "並排兩個人形（米白與綠）", d: (c, o) => { bust(c, CREAM, -4.6, 1, 0.84); halo(c, o, (q) => bust(q, ALLY, 4.6, 1, 0.84)); } },
    target_collided: { zh: "目標本回合受過撞擊", topic: "米白人形撞在右邊一道石牆上，中間一顆撞擊星", d: (c, o) => { wall(c, 5.6); bust(c, CREAM, -3, 1.2, 0.86); halo(c, o, (q) => burstStar(q, 3.6, -4.6, 4.8)); } },
    wielding_weapon: { zh: "手持指定武器", topic: "一把斜放的亮色單手劍（亮鋼寬刃、金護手、皮柄）", d: diagSword() }, /* 第 2 版：同打擊徽章 */
    in_form: { zh: "在形態中", topic: "三道淡紫色的爪痕", d: (c, o) => at(c, 0, 0, 1, (q) => { for (const i of [-1, 0, 1]) poly(q, i === 0 ? "#e6d2ff" : "#c9a0ff", [[i * 6.4 - 2.2, -10], [i * 6.4 + 1.6, -10], [i * 6.4 + 2.8, 2], [i * 6.4 + 0.2, 10.2], [i * 6.4 - 1.8, 2]], 0.3); }, 0.28) },
    /* 11-13 獨狼（LW-1 新條件）：加在條件表最後，前面 17 個的畫法不動。 */
    lone_wolf: { zh: "獨狼", topic: "一隻仰頭嚎叫的銀灰狼頭（側面、口鼻朝左上、兩隻尖耳、米白喉胸一排鋸齒毛）", d: (c, o) => loneWolf(c, o) },
    self_lacks_status: { zh: "自身沒有狀態", topic: "淡紫小旗被一道紅斜槓劃掉（同驅散、致盲劃掉的語言），右下一個米白小人形（同自身血量：自己）", d: (c, o) => selfLacks(c, o) },
    /* 11-13 BS-1（DD-3 雙牙）新條件：加在條件表最後，前面 19 個的畫法不動。 */
    all_strikes_hit: { zh: "每一下都命中", topic: "一面紅白靶，靶心插著兩把亮鋼匕首（柄朝右上、微微扇開）", d: (c, o) => allStrikesHit(c, o) },
  };

  // =====================================================================
  // 代價 6 個
  // =====================================================================
  const COST = {
    source: { zh: "源力", topic: "六角的淡紫晶石", d: crystal },
    gamble: { zh: "賭注", topic: "一顆斜放的白骰子", d: dice },
    self: { zh: "自身代價（失手自傷等）", topic: "一顆裂開的紅心", d: (c, o) => { heartArt(c, o); ln(c, OUT, 2.6, [[0.8, -4.6], [-2.2, -0.6], [2, 2.4], [-0.6, 5.6], [0.2, 10]], "miter"); } },
    stacks: { zh: "消耗層數", topic: "兩根金條加一顆橘色爆星", d: (c, o) => EFFECT.consume_stack.d(c, o) },
    once: { zh: "每場一次", topic: "一張米白票券（兩側缺口），上面一個深色的 1", d: (c, o) => { c.scale(0.86, 0.86); rr(c, CREAM, -10.4, -6.8, 20.8, 13.6, 2.2); f(c, "#fffaf0", () => c.roundRect(-10.4, -6.8, 20.8, 3, [2.2, 2.2, 0, 0])); ci(c, OUT, -10.6, 0, 2.3); ci(c, OUT, 10.6, 0, 2.3); poly(c, "#2a1c14", [[-0.6, -4.6], [2, -4.6], [2, 4.6], [-1.2, 4.6], [-1.2, -1.4], [-3.2, -0.6], [-3.2, -3.2]], 0.2); } },
    delay: { zh: "延遲", topic: "沙漏（藍框、白玻璃、金沙）", d: hourglass },
  };

  // =====================================================================
  // 觸發與反應時機 22 個
  // =====================================================================
  const redStar = (c, x, y, R = 5.4) => { poly(c, "#ff4a5a", starPts(x, y, R, R * 0.45, 6), 0.3); poly(c, "#ffffff", starPts(x, y, R * 0.5, R * 0.22, 6)); };
  const shieldAt = (c, o) => at(c, 4.6, 4.6, 0.56, (q) => QS.ACT.shield.d(q, o, QS.ACT.shield.def));
  const TRIG = {
    on_hit: { zh: "命中時", topic: "右上一顆大的黃色撞擊閃光，左下短粗的亮劍刺進去", d: fit((c, o) => { at(c, -2.2, 2.2, 0.6, (q) => bladeSword(q, o), PI / 4); halo(c, o, (q) => burstStar(q, 3.4, -3.4, 7.6, "#ffd23f")); }, 0.9) }, /* 第 2 版：細劍＋小閃光在 18px 是一條灰線；改成撞擊閃光為主、亮劍為輔（傷害是白四芒、暴擊是橘黃八芒） */
    on_kill: { zh: "擊倒時", topic: "骷髏頭、紅眼", src: "b3:finisher", d: fit(act("finisher"), 0.88) },
    on_crit: { zh: "暴擊時", topic: "橘黃兩層的八芒大閃光、白芯", d: (c, o) => { poly(c, "#ff9a2a", starPts(0, 0, 11, 4.2, 4), 0.3); poly(c, "#ffd23f", starPts(0, 0, 8.2, 3.2, 4, -PI / 4), 0.3); poly(c, "#ffffff", starPts(0, 0, 5, 1.9, 4)); } },
    on_natural_20: { zh: "擲出自然 20 時", topic: "淡紫的二十面骰（六角、三個切面），正面寫 20", d: (c, o) => { poly(c, "#cfc4ff", [0, 1, 2, 3, 4, 5].map((i) => [Math.cos((i / 6) * TAU - PI / 2) * 10.6, Math.sin((i / 6) * TAU - PI / 2) * 10.6]), 0.5); poly(c, "#8a76d8", [[9.2, -5.3], [9.2, 5.3], [0, 10.6], [5.6, 4]]); poly(c, "#8a76d8", [[-9.2, 5.3], [0, 10.6], [-5.6, 4]]); poly(c, "#ffffff", [[0, -6.2], [5.8, 4], [-5.8, 4]], 0.4); if (!o.tiny) { c.fillStyle = "#3a2a7a"; c.font = "900 6.2px Arial, sans-serif"; c.textAlign = "center"; c.textBaseline = "middle"; c.fillText("20", 0, 1.2); } } },
    on_move: { zh: "移動後", topic: "一隻褐色的靴子，後面兩道速度線", src: "style:hud.move", d: boot },
    on_damaged: { zh: "受傷時", topic: "米白人形，右上一顆紅色撞擊星", d: (c, o) => { bust(c, CREAM, -1.8, 1.4, 1); halo(c, o, (q) => redStar(q, 5, -4.8, 5.6)); } },
    on_status_applied: { zh: "施加狀態後", topic: "掛在橫桿上的淡紫小旗", d: banner },
    on_cast_tag: { zh: "施放帶標籤的技能後", topic: "一張斜放的金色吊牌", d: fit(tag, 0.88) },
    on_collision: { zh: "造成撞擊後", topic: "一個米白的三角撞上右邊的石牆，中間一顆撞擊星", d: (c, o) => { wall(c, 5.4); poly(c, CREAM, [[-10.6, -4], [-3.6, 0], [-10.6, 4]], 0.5); halo(c, o, (q) => burstStar(q, 2.6, 0, 6)); } },
    on_turn_start: { zh: "回合開始時", topic: "藍色地平線上升起半個太陽，五道短光芒", d: (c, o) => { for (const a of [-1.2, -0.6, 0, 0.6, 1.2]) at(c, 0, 5, 1, (q) => rr(q, "#ffd23f", -1.3, -12.6, 2.6, 3.8, 1.2), a); f(c, "#ffb23a", () => { c.arc(0, 5, 7.4, PI, 0); c.closePath(); }); f(c, "#ffe14d", () => { c.arc(0, 5, 5.4, PI, 0); c.closePath(); }); rr(c, "#7ab8f0", -10.4, 5, 20.8, 2.8, 1.4); } },
    on_turn_end: { zh: "回合結束時", topic: "地平線上一彎淡紫的月牙", d: (c, o) => { f(c, "#d8c0ff", () => { c.arc(-0.6, -2.4, 8.2, 0.2417, 4.652, false); c.arc(2.4, -4.9, 6.6, -2.137, 0.747, true); c.closePath(); }); rr(c, "#7a5ac8", -11, 6.2, 22, 3.8, 1.9); if (!o.tiny) star4(c, "#ffffff", 6.6, -6.6, 2.8, null); } },
    on_enter_surface: { zh: "敵人進入你的表面時", topic: "一隻靴子踩進一灘藍水漬", d: (c, o) => { puddle(c, "#4aa8ff", "#cfe8ff", 7.2); halo(c, o, (q) => at(q, 0.6, -2, 0.82, (p) => bootOnly(p, o))); } },
    on_summon_downed: { zh: "召喚物倒下時", topic: "一隻歪倒、變灰的小靈，右下一個朝下的紅箭頭", d: (c, o) => { at(c, -1.8, -1.2, 0.86, (q) => QS.ACT.summon.d(q, o, ["#8ab0a8", "#d6e6e2"]), 0.5); halo(c, o, (q) => poly(q, ENEMY, [[6, 10.6], [10.8, 4.6], [8, 4.6], [8, -1], [4, -1], [4, 4.6], [1.2, 4.6]], 0.3)); } },
    every_n_hits: { zh: "每命中 n 次", topic: "由小到大斜排的三顆四芒閃光，最後一顆是金色", d: (c, o) => { star4(c, "#ffffff", -6.8, 4.6, 4.6, null); star4(c, "#ffffff", -0.6, 0.6, 5.2, null); halo(c, o, (q) => star4(q, "#ffc23a", 5.6, -4.6, 6.4, "#ffffff")); } },
    enemy_enters_adjacent: { zh: "敵人靠近時", topic: "右邊米白人形，左邊一個朝它的紅箭頭", d: (c, o) => { bust(c, CREAM, 5, 1.2, 0.84); at(c, -5.6, 1.6, 0.56, (q) => arrowS(q, ENEMY, "#ffb0a8")); } },
    enemy_leaves_adjacent: { zh: "敵人離開時", topic: "左邊米白人形，右邊一個往外的紅箭頭", d: (c, o) => { bust(c, CREAM, -5, 1.2, 0.84); at(c, 5.6, 1.6, 0.56, (q) => arrowS(q, ENEMY, "#ffb0a8")); if (!o.tiny) { rr(c, ENEMY, -0.6, -4.4, 2.4, 2, 1); rr(c, ENEMY, -0.6, 5.6, 2.4, 2, 1); } } },
    hit_by_spell: { zh: "被法術擊中時", topic: "左上一顆大的紫色法術星（佔一半），右下一面小藍盾", d: (c, o) => { shieldAt(c, o); halo(c, o, (q) => star4(q, "#c890ff", -3.4, -3.4, 8.6, "#ffffff")); } },
    hit_by_attack: { zh: "被攻擊時", topic: "左上一個大的紅箭頭（佔一半）朝右下的小藍盾", d: (c, o) => { shieldAt(c, o); halo(c, o, (q) => at(q, -3.2, -3.2, 0.88, (p) => arrowS(p, ENEMY, "#ffb0a8"), PI / 4)); } },
    hit_by_melee: { zh: "被近戰擊中時", topic: "左上一把大的亮劍（佔一半）砍向右下的小藍盾", d: (c, o) => { shieldAt(c, o); halo(c, o, (q) => at(q, -1.8, -1.8, 0.58, (p) => bladeSword(p, o), PI * 0.75)); } }, /* 第 2 版：三個在 18px 都是藍盾、只差左上一小塊色；來襲的東西放大到佔一半、盾縮小 */
    ally_targeted: { zh: "隊友被瞄準時", topic: "綠色人形，外面一圈紅色準星", d: (c, o) => { bust(c, ALLY, 0, 1.2, 0.86); for (let i = 0; i < 4; i++) st(c, "#ff4a5a", 2.8, (x) => x.arc(0, 0, 9.4, (i * PI) / 2 + 0.3, ((i + 1) * PI) / 2 - 0.3), "butt"); } },
    ally_downed: { zh: "隊友倒下時", topic: "躺平的綠色人形，上面一顆小骷髏", d: (c, o) => { rr(c, ALLY, -10, 3, 13.6, 6, 3); ci(c, ALLY, 6.6, 5.6, 3.8); rr(c, "#3f7a5a", -10.6, 9, 21.2, 1.8, 0.9); halo(c, o, (q) => at(q, -1.6, -4.4, 0.56, (p) => QS.ACT.finisher.d(p, { ...o, small: true }))); } },
    ally_hit_adjacent: { zh: "身旁隊友受擊時", topic: "綠色人形，右上一顆紅色撞擊星", d: (c, o) => { bust(c, ALLY, -3.4, 1.4, 0.92); halo(c, o, (q) => redStar(q, 5.2, -4.6, 5.4)); } },
  };
  /** 名詞表（glossary）有、現行沒有專屬圖的 5 個觸發（現行畫「?」）：建議各用哪一個。不算在 22 個裡。 */
  const TRIG_ALIAS = { targeted_by_melee: "hit_by_melee", targeted_by_attack: "hit_by_attack", enemy_moves_in_range: "enemy_enters_adjacent", ally_hit_in_range: "ally_hit_adjacent", kin_hit_in_range: "ally_hit_adjacent" };

  // =====================================================================
  // 接續 6 個
  // =====================================================================
  const LINK = {
    after_action: { zh: "接著做", topic: "一個朝右的米白粗箭頭", d: (c, o) => { poly(c, CREAM, [[-10.5, -3.6], [-0.5, -3.6], [-0.5, -9.6], [10.5, 0], [-0.5, 9.6], [-0.5, 3.6], [-10.5, 3.6]], 0.5); poly(c, "#ffffff", [[-10.5, -3.6], [-0.5, -3.6], [-0.5, -9.6], [10.5, 0], [-10.5, 0]]); } },
    on_hit: { zh: "命中才觸發", topic: "一個綠色的粗勾", d: (c, o) => { ln(c, "#5ad06a", 4.8, [[-8.4, 0.8], [-2.8, 6.4], [8.4, -6.4]]); if (!o.tiny) ln(c, "#d8ffe0", 1.4, [[-7.4, -0.4], [-3.6, 3.4]]); } },
    on_kill: { zh: "擊殺才觸發", topic: "骷髏頭、紅眼", src: "b3:finisher", d: fit(act("finisher"), 0.88) },
    delayed: { zh: "延遲觸發", topic: "沙漏", d: hourglass },
    after_move: { zh: "移動後觸發", topic: "靴子加速度線", src: "style:hud.move", d: boot },
    after_gather: { zh: "聚集後觸發", topic: "左右兩個朝中間的米白大三角，中間一顆金色四芒星", d: (c, o) => { for (const s of [-1, 1]) { poly(c, CREAM, [[s * 10.6, -6.4], [s * 4.2, 0], [s * 10.6, 6.4]], 0.5); poly(c, "#ffffff", [[s * 10.6, -6.4], [s * 4.2, 0], [s * 10.6, 0]]); } star4(c, "#ffd23f", 0, 0, 4.6, "#ffffff"); } },
  };

  // =====================================================================
  // 骨架徽章 16 個（現行 skeletonGlyph 有專屬圖的 12 個；modifier、passive、combo、sacrifice 四個現行是同一個空心圓）
  // =====================================================================
  const SKELETON = {
    strike: { zh: "打擊", topic: "一把斜放的亮色單手劍（亮鋼寬刃、金護手、皮柄，放大到貼色環）", d: diagSword() }, /* 第 2 版：第 1 批的劍在深色圓底上整排最暗；照規則 6 換亮 */
    area: { zh: "範圍", topic: "向外擴的衝擊環：中心黃白小爆星，外面一圈斷成四段的橘色粗環，四個斜角各一道往外的淡黃短衝擊", d: areaBurst }, /* 第 2 版：九宮格和形狀 3×3 緊鄰時撞圖，九宮格留給形狀 */
    control: { zh: "控制", topic: "一把金鎖", src: "b3:bind", d: act("bind") },
    aura: { zh: "增益", topic: "朝上的粗箭頭加底槓", src: "b3:buff", d: act("buff") },
    summon: { zh: "召喚", topic: "一隻青色的小靈", src: "b3:summon", d: spirit() },
    trap: { zh: "陷阱", topic: "底板上一排朝上的鋼牙", src: "b3:trap", d: fit(act("trap"), 0.8) },
    displace: { zh: "位移", topic: "兩個朝右的粗 V 拉開（同效果「衝鋒」）", d: dashArt },
    rune: { zh: "刻印", topic: "圓頂石碑加金色菱形符文", d: tablet },
    consume_status: { zh: "引爆狀態", topic: "橘色十角爆炸", src: "b3:detonate", d: act("detonate") },
    builder_finisher: { zh: "累積終結", topic: "三根越來越高的金色粗條", src: "b3:builder", d: act("builder") },
    stance: { zh: "姿態", topic: "藍色六角臂章，上面兩道金色 V 形階級條", d: (c, o) => { const P = [0, 1, 2, 3, 4, 5].map((i) => [Math.cos((i / 6) * TAU - PI / 2) * 10.6, Math.sin((i / 6) * TAU - PI / 2) * 10.6]); poly(c, "#5a86d8", P, 0.5); poly(c, "#9ab8f0", [P[0], P[5], P[4], [-5.6, 3], [-5.6, -4.4]]); for (const y of [-2.6, 3.4]) poly(c, "#ffd23f", [[-6, y + 1.4], [0, y - 3.8], [6, y + 1.4], [6, y + 4.6], [0, y - 0.6], [-6, y + 4.6]], 0.2); } },
    reaction: { zh: "反應", topic: "綠色逆時針回轉箭頭", d: (c, o) => react(c, o) },
    modifier: { zh: "改造", topic: "一顆金色齒輪", src: "b3:modify", d: act("modify") },
    passive: { zh: "被動", topic: "金色的無限符號（一直生效）", d: (c, o) => { const P = (x) => { x.moveTo(0, 0); x.bezierCurveTo(3.6, -8.6, 11, -7, 10, 0); x.bezierCurveTo(11, 7, 3.6, 8.6, 0, 0); x.bezierCurveTo(-3.6, -8.6, -11, -7, -10, 0); x.bezierCurveTo(-11, 7, -3.6, 8.6, 0, 0); }; st(c, "#ffc23a", 4, P); if (!o.tiny) st(c, "#fff6c8", 1.3, (x) => { x.moveTo(-9, -1.6); x.bezierCurveTo(-8.6, -5.4, -4.6, -5.6, -2.6, -2.6); }); } },
    combo: { zh: "連段", topic: "一大一小兩顆四芒閃光", src: "b3:combo", d: act("combo") },
    sacrifice: { zh: "獻祭", topic: "小靈背後一圈橘色的爆炸", d: (c, o) => EFFECT.sacrifice_summon.d(c, o) },
  };

  // =====================================================================
  // 形狀 13 個（組裝列的「形狀」方塊：九宮格示意，亮格＝打到的格子、米白＝自己、綠＝隊友、褐＝物件）
  // =====================================================================
  const SHAPE_MAP = { single: ["單體", "..#/.../@.."], self: ["自身", ".../.@./..."], ground_tile: ["指定地格", ".v./.#./..."], square3: ["3×3", "###/###/###"], cross: ["十字", ".#./###/.#."], ring: ["環形（自己周圍一圈）", "###/#@#/###"], cone: ["錐形", "###/.#./.@."], line: ["直線", ".../@##/..."], chain: ["連鎖", "#../..#/.#."],
    allies_in_radius: ["範圍內友方", ".a./a@a/.a."], unit_then_tile: ["單位再指定格", ".../@>#/..."], object_then_tile: ["物件再指定格", ".../o>#/..."], unit_pair: ["兩個單位", ".../@=@/..."] };
  /* 第 2 版（必修 5）：命中格固定用橘（不再染元素色：物理是白、和米白的「自己」分不出）；單位（自己、隊友）畫成圓、格子畫成方；
     沒打到的格縮小、再暗一階（UNLIT），打到的格放大一點；自查的亮度以亮格為準（UNLIT 的像素不算，見樣張頁 audit）。兩個單位之間改成一個雙頭箭頭。 */
  const UNLIT = "#3a3f4e", LIT = "#ffb23a";
  const shapeArt = (rows) => (c, o) => { c.scale(0.8, 0.8); rows.split("/").forEach((row, r) => [...row].forEach((ch, i) => { const cx = -6.9 + i * 6.9, cy = -6.9 + r * 6.9;
    if (ch === ">") { poly(c, "#ffffff", [[cx - 2.8, cy - 3.4], [cx + 3, cy], [cx - 2.8, cy + 3.4]], 0.4); return; }
    if (ch === "=") { poly(c, "#ffffff", [[cx - 3.8, cy], [cx - 1.2, cy - 2.8], [cx - 1.2, cy - 0.9], [cx + 1.2, cy - 0.9], [cx + 1.2, cy - 2.8], [cx + 3.8, cy], [cx + 1.2, cy + 2.8], [cx + 1.2, cy + 0.9], [cx - 1.2, cy + 0.9], [cx - 1.2, cy + 2.8]], 0.2); return; }
    if (ch === "v") { poly(c, "#ffffff", [[cx - 3.2, cy - 2.2], [cx + 3.2, cy - 2.2], [cx, cy + 3]], 0.4); return; }
    if (ch === "@" || ch === "a") { ci(c, ch === "@" ? CREAM : ALLY, cx, cy, 3.5); if (!o.tiny) ci(c, "#ffffff", cx - 1.1, cy - 1.1, 1.1); return; }
    if (ch === "#") { rr(c, LIT, cx - 3.25, cy - 3.25, 6.5, 6.5, 1.4); if (!o.tiny) f(c, "#ffe0a0", () => c.roundRect(cx - 3.25, cy - 3.25, 6.5, 1.8, [1.4, 1.4, 0, 0])); return; }
    if (ch === "o") { rr(c, "#c08a4a", cx - 3, cy - 3, 6, 6, 1); f(c, "#8a5a2a", () => c.rect(cx - 3, cy + 1.4, 6, 1.6)); return; }
    rr(c, UNLIT, cx - 2.2, cy - 2.2, 4.4, 4.4, 1); })); };
  const SHAPE = Object.fromEntries(Object.entries(SHAPE_MAP).map(([id, [zh, rows]]) => [id, { zh, topic: "九宮格示意：" + rows, d: shapeArt(rows) }]));

  // =====================================================================
  // 修正技「改了什麼」16 個鍵（現行 modifierChangePart；form_upkeep_permille、form_entry_permille 現行是「?」）
  // =====================================================================
  const rangeArt = (c, o) => { rr(c, "#ffd23a", -10.4, -3.6, 6.6, 7.2, 1.6); poly(c, "#ffffff", [[-2.2, -3.4], [1.8, 0], [-2.2, 3.4]], 0.5); rr(c, "#e04a3a", 3.8, -3.6, 6.6, 7.2, 1.6); if (!o.tiny) { f(c, "#fff3a0", () => c.roundRect(-10.4, -3.6, 6.6, 2, [1.6, 1.6, 0, 0])); f(c, "#ff9a8a", () => c.roundRect(3.8, -3.6, 6.6, 2, [1.6, 1.6, 0, 0])); } };
  /** 第 2 版：右上的小箭頭照數值正負（opt.value；正＝朝上橘黃、負＝朝下青色），不再寫死。 */
  const up = (base, bk, sk) => withBadge(base, (c, o, T, opt) => signArrow(c, o, opt), bk, sk);
  const elementArt = (id) => (id === "physical" || !QS.ELEMENT[id] ? act("hit", [STEEL, "#ffffff"]) : from48((c, o) => QS.ELEMENT[id].d(c, { ...o, small: true })));
  const CHANGE = {
    add_element: { zh: "加上元素", topic: "該元素的道具（第 3 批）加白色加號", d: (c, o, T, opt) => { at(c, -1.6, 1.6, 0.86, (q) => elementArt(opt?.value ?? "fire")(q, o)); plus(c, o, 6.8, -6.6, 0.8); } },
    damage_permille: { zh: "傷害增減", topic: "白閃光，右上一個小箭頭（照數值正負朝上或朝下）", d: up(act("hit")) },
    hit_bonus: { zh: "命中", topic: "紅準星，右上一個小箭頭（照正負）", d: up(act("mark")) },
    cooldown_delta: { zh: "冷卻", topic: "藍鐘，右上一個小箭頭（照正負；冷卻 −1＝朝下青色）", d: up(clock) },
    area_delta: { zh: "範圍", topic: "九宮格，右上一個小箭頭（照正負）", d: up((c) => grid3(c)) },
    push_distance_delta: { zh: "推距", topic: "推開的箭頭，右上一個小箭頭（照正負）", d: up(act("push"), 0.74, 0.44) },
    ap_delta: { zh: "AP", topic: "黃色閃電，右上一個小箭頭（照正負；AP −1＝朝下青色）", d: up(bolt) },
    range_delta: { zh: "射程", topic: "黃格、白箭頭、紅格（和卡片的射程同一個），右上一個小箭頭（照正負）", d: up(rangeArt) },
    add_tags: { zh: "加上標籤", topic: "金色吊牌加白色加號", d: (c, o) => { at(c, -1.4, 1.4, 0.86, (q) => tag(q, o)); plus(c, o, 6.8, -6.6, 0.8); } },
    on_hit_effects: { zh: "命中後效果", topic: "那個效果的圖，右上一顆小白閃光", d: (c, o, T, opt) => withBadge(opt?.base ?? act("detonate"), (q) => star4(q, "#ffffff", 0, 0, 10.6, null))(c, o) },
    shape_to: { zh: "形狀改為", topic: "新形狀的九宮格示意", d: (c, o, T, opt) => (SHAPE[opt?.value] ?? SHAPE.square3).d(c, o, T) },
    allow_self_target: { zh: "可以對自己用", topic: "米白人形，外面一圈綠色的環", d: (c, o) => { st(c, "#5ad06a", 2.8, (x) => x.arc(0, 0, 9.4, 0, TAU)); bust(c, CREAM, 0, 1.2, 0.84); } },
    grant_pierce: { zh: "穿透", topic: "黃箭頭穿過一道石牆", d: (c, o) => EFFECT.charge_through.d(c, o) },
    heal_permille: { zh: "治療量", topic: "綠十字，右上一個小箭頭（照正負）", d: up(act("heal")) },
    summon_hp_permille: { zh: "召喚物 HP", topic: "小靈，右上一顆紅心", d: withBadge(spirit(), (c, o) => heart(c, "#ff5a4a", 0, 1, 1.3)) },
    summon_limit_delta: { zh: "召喚物上限", topic: "小靈，右上一個白色加號（照數值：負＝白色減號）", d: (c, o, T, opt) => { at(c, -2.2, 2.2, 0.8, (q) => spirit()(q, o)); if ((opt?.value ?? 1) < 0) minus(c, o, 6.6, -6.4, 0.8); else plus(c, o, 6.6, -6.4, 0.8); } }, /* 11-12（追加 E）：−1 原本也畫加號；正照舊（指紋不變），負改減號 */
    summon_duration_delta: { zh: "召喚物持續", topic: "小靈，右上一個小沙漏", d: withBadge(spirit(), hourglass) },
    summon_damage_permille: { zh: "召喚物傷害", topic: "小靈，右上一顆白閃光", d: withBadge(spirit(), (c) => star4(c, "#ffffff", 0, 0, 10.6, null)) },
    summon_attack_dice: { zh: "召喚物攻擊骰", topic: "小靈，右上一顆小骰子", d: withBadge(spirit(), dice) },
    form_upkeep_permille: { zh: "形態維持消耗", topic: "獸掌印、右下壓一個小沙漏，右上一個小箭頭（照正負；−500‰＝朝下青色）", d: up((c, o) => { paw(c, o); halo(c, o, (q) => at(q, 6.4, 6.6, 0.46, (p) => hourglass(p, o))); }) }, /* 11-12（追加 E）：原本右上是固定的沙漏、沒有正負；沙漏移到掌印右下（和「形態進入消耗」分得開），右上換成照正負的箭頭 */
    form_entry_permille: { zh: "形態進入消耗", topic: "獸掌印，右上一個小箭頭（照正負）", d: up((c, o) => paw(c, o)) },
    /* 11-13 BS-1 新修正內容：加在修正表最後，前面 21 個的畫法不動。沒有數值（true_only），不畫正負箭頭。 */
    silent_strike: { zh: "無聲（目標不轉身）", topic: "一根淡紫羽毛，前面平行壓一把亮鋼匕首（都斜放、尖朝右上）；≤14px 只留羽毛", d: (c, o) => silentStrike(c, o) },
  };

  // =====================================================================
  // 元素小圓片（96px 圖示左上角）：第 3 批的元素道具縮小；物理是鋼白的四芒閃光
  // =====================================================================
  const ELEMENT = Object.fromEntries(["physical", "fire", "ice", "lightning", "poison", "wind", "earth", "holy", "shadow"].map((id) => [id, { zh: QS.BASE_ZH[id] ?? id, topic: id === "physical" ? "鋼白的四芒閃光" : "第 3 批的元素道具：" + QS.ELEMENT[id].zh, src: id === "physical" ? "b3:hit" : "b3:el:" + id, d: elementArt(id) }]));

  // =====================================================================
  // 技能卡小圖（client/src/ui/SkillCardGlyphs.tsx）：常駐行 13 個（16px）、效果行 8 個（18px）、圖釘 1 個（13px）
  // =====================================================================
  const hud = (id) => from48((c, o) => Q.ART.hud[id].d(c, o), 0.46);
  const CARD = {
    ap: { zh: "AP", topic: "黃色閃電（HUD 的 AP 同一個）", src: "style:hud.ap", px: 16, d: hud("ap") },
    mana: { zh: "法力", topic: "藍色水滴（HUD 的法力同一個）", src: "style:hud.mana", px: 16, d: hud("mana") },
    stamina: { zh: "耐力", topic: "金色的脈搏折線（HUD 的耐力同一個）", src: "style:hud.stamina", px: 16, d: hud("stamina") },
    hp: { zh: "生命", topic: "紅心", px: 16, d: (c, o) => heartArt(c, o, "#f0503e", "#ffb0a0", 1.3) },
    source: { zh: "源力", topic: "六角的淡紫晶石（和圓片的源力同一個；現行是淡紫五角星）", px: 16, d: crystal },
    uses: { zh: "次數", topic: "米白票券（兩側缺口、中間一道虛線）", px: 16, d: (c, o) => { c.scale(0.86, 0.86); rr(c, CREAM, -10.4, -6.8, 20.8, 13.6, 2.2); f(c, "#fffaf0", () => c.roundRect(-10.4, -6.8, 20.8, 3, [2.2, 2.2, 0, 0])); ci(c, OUT, -10.6, 0, 2.3); ci(c, OUT, 10.6, 0, 2.3); for (const x of [-5, -1, 3]) f(c, "#8a6a2a", () => c.rect(x, -0.9, 2.6, 1.8)); } },
    cooldown: { zh: "冷卻", topic: "藍邊白面的鐘", px: 16, d: clock },
    range: { zh: "射程", topic: "黃格（自己）、白箭頭、紅格（目標）", px: 16, d: rangeArt },
    reaction: { zh: "反應", topic: "綠色逆時針回轉箭頭", px: 16, d: (c, o) => react(c, o) },
    trigger: { zh: "觸發", topic: "一個橘色的鈴（金色鈴舌）", px: 16, d: (c, o) => { ci(c, "#f0a040", 0, -9.2, 1.8); f(c, "#f0a040", () => { c.moveTo(-7.8, 5); c.quadraticCurveTo(-7, -8.6, 0, -8.6); c.quadraticCurveTo(7, -8.6, 7.8, 5); c.lineTo(10.2, 7.4); c.lineTo(-10.2, 7.4); c.closePath(); }); ci(c, "#ffd23f", 0, 8.8, 2.3); if (!o.tiny) el(c, "#ffe0b0", -3.2, -2.6, 1.5, 4.2, 0.2); } },
    delayed: { zh: "延遲", topic: "沙漏（和圓片的延遲同一個；現行是米白的鐘，和冷卻只差顏色）", px: 16, d: hourglass },
    activation: { zh: "啟動", topic: "金色五角星", px: 16, d: (c, o) => { poly(c, "#ffb938", starPts(0, 0.6, 10.6, 4.5, 5), 0.5); if (!o.tiny) poly(c, "#fff0b0", [[0, -10], [-2.6, -2.8], [0, 0.6]]); } },
    drawback: { zh: "缺點", topic: "琥珀色警告三角，裡面深色驚嘆號", px: 16, d: (c, o) => { poly(c, "#e0a040", [[0, -9.2], [9.6, 7.8], [-9.6, 7.8]], 1.3); rr(c, "#2a1c14", -1.4, -4.4, 2.8, 7, 1); ci(c, "#2a1c14", 0, 5.4, 1.6); } },
    damage: { zh: "傷害", topic: "四芒閃光（染元素色；物理是白）", src: "b3:hit", px: 18, d: (c, o, T) => QS.ACT.hit.d(c, o, T ?? ["#e8eef4", "#ffffff"]) },
    heal: { zh: "治療", topic: "綠色粗十字", src: "b3:heal", px: 18, d: act("heal") },
    shield: { zh: "護盾", topic: "淡藍小盾", src: "b3:shield", px: 18, d: act("shield") },
    move: { zh: "移動", topic: "褐色靴子加速度線", src: "style:hud.move", px: 18, d: boot },
    status: { zh: "狀態", topic: "淡紫小旗", px: 18, d: banner },
    surface: { zh: "表面", topic: "一灘水漬上落下一滴", src: "b3:surface", px: 18, d: surface("water") },
    summon: { zh: "召喚", topic: "青色小靈", src: "b3:summon", px: 18, d: spirit() },
    stack: { zh: "層數", topic: "三根越來越高的金條", src: "b3:builder", px: 18, d: act("builder") },
    /* 第 2 版：圖釘收一個狀態參數 opt.pinned（預設 true＝已釘、紅頭）；false＝未釘：同外形的灰鋼色、約 55% 不透明（美術 PM 定） */
    pin: { zh: "圖釘", topic: "斜放的圖釘：已釘＝紅頭；未釘（opt.pinned false）＝同外形灰鋼色、55% 不透明", px: 13, d: (c, o, T, opt) => { const on = opt?.pinned !== false; c.save(); if (!on) c.globalAlpha = 0.55; at(c, 0, 0, 1, (q) => { ln(q, on ? STEEL : "#9aa2ac", 2.2, [[0, 2], [0, 10.6]]); poly(q, on ? "#c8382e" : "#8a929c", [[-3, -5], [3, -5], [5.8, 2.8], [-5.8, 2.8]], 0.6); rr(q, on ? "#f05a48" : "#b4bcc6", -5.4, -10.6, 10.8, 5.4, 2.2); }, 0.6); c.restore(); } },
  };

  // =====================================================================
  // 修正技的「改造對象」（11-12 補圖；現行 skillParts.ts 的 modifierTargetPart，組裝算式第一格、白環）。畫法和修正內容同一類：±10 單位、直接呼叫第 3、4 批同題材的圖。
  // 代碼由 targetOf(applies_to) 算，判斷順序照現行：all_skills → all_attacks／actions 含 attack → skill_tags 的第一個 → 其他 actions → 預設。
  // =====================================================================
  /** 亮色的弓與箭（遠程技能）：木色弓臂往右鼓、白弦、鋼箭頭朝右（現行是一道弧加一支箭）。 */
  const bowArrow = (c, o) => { st(c, "#d8a868", 3.4, (x) => x.arc(-7, 0, 11, -1.15, 1.15), "round"); if (!o.tiny) st(c, "#fff0d0", 1, (x) => x.arc(-7.6, 0, 11, -0.9, -0.2), "butt"); ln(c, "#ffffff", 1.2, [[-2.5, -10], [-2.5, 10]]); rr(c, "#c3ccd6", -10.4, -1.3, 15, 2.6, 1); poly(c, "#ffffff", [[4, -4.4], [10.8, 0], [4, 4.4]], 0.4); poly(c, "#f2e6c8", [[-10.8, -4], [-6.6, -1.2], [-6.6, 1.2], [-10.8, 4]], 0.3); };
  /** 三張扇開的米白卡（所有技能）：後兩張降一階，前面一張金星。 */
  const cardFan = (c, o) => { for (const [a, col] of [[-0.42, "#a8a08a"], [-0.14, "#d8ccae"]]) at(c, 0, 4, 1, (q) => rr(q, col, -5.4, -14, 10.8, 14.4, 1.8), a); at(c, 0, 4, 1, (q) => { rr(q, CREAM, -5.4, -14, 10.8, 14.4, 1.8); poly(q, GOLD, starPts(0, -6.8, 4, 1.7, 5), 0.3); }, 0.2); };
  const TARGET = {
    all_skills: { zh: "所有技能", topic: "三張扇開的米白卡（前面一張金星）", d: cardFan },
    all_attacks: { zh: "所有攻擊", topic: "兩把交叉的亮色劍（打擊徽章那把，成對）", src: "b4:skeleton.strike×2", d: (c, o) => { diagSword(0.76)(c, o); halo(c, o, (q) => at(q, 0, 0, 1, (p) => { p.scale(-1, 1); diagSword(0.76)(p, o); })); } },
    attack: { zh: "普通攻擊", topic: "斜放的亮色單手劍（同打擊徽章）", src: "b4:skeleton.strike", d: diagSword() },
    tag_push: { zh: "推擊技能", topic: "朝右上的黃白粗箭頭（同效果「推擊」）", src: "b3:push", d: act("push") },
    tag_heal: { zh: "治療技能", topic: "綠色粗十字（同效果「治療」）", src: "b3:heal", d: act("heal") },
    tag_control: { zh: "控制技能", topic: "一把金鎖（同骨架徽章「控制」）", src: "b3:bind", d: act("bind") },
    tag_ranged: { zh: "遠程技能", topic: "木色弓臂、白弦、一支鋼頭箭朝右", d: bowArrow },
    tag_shout: { zh: "吼叫技能", topic: "象牙號角加聲波（同第 3 批中性道具「吼聲」）", src: "b3:w:roar", d: from48((c, o) => QS.THINGS.roar.d(c, { ...o, small: true }), 0.44) },
    tag_area: { zh: "範圍技能", topic: "向外擴的衝擊環（同骨架徽章「範圍」）", src: "b4:skeleton.area", d: areaBurst },
    tag_summon: { zh: "召喚技能", topic: "一隻青色小靈（同效果「召喚」；現行畫傷害閃光）", src: "b3:summon", d: spirit() },
    tag_other: { zh: "其他標籤的技能", topic: "白色四芒閃光（同現行：沒列的標籤畫傷害）", src: "b3:hit", d: act("hit") },
    actions: { zh: "其他動作", topic: "斜放的亮色單手劍（同普通攻擊；現行同一把劍）", src: "b4:skeleton.strike", d: diagSword() },
    default: { zh: "沒寫對象（所有技能）", topic: "白色四芒閃光（同現行預設）", src: "b3:hit", d: act("hit") },
  };
  const TARGET_TAG = { push: "tag_push", heal: "tag_heal", control: "tag_control", ranged: "tag_ranged", shout: "tag_shout", area: "tag_area", summon: "tag_summon" };
  /** applies_to → 改造對象的代碼（判斷順序照現行 modifierTargetPart）。 */
  const targetOf = (applies) => { const a = applies ?? {}, actions = Array.isArray(a.actions) ? a.actions : [], tags = Array.isArray(a.skill_tags) ? a.skill_tags.map(String) : [];
    if (a.all_skills === true) return "all_skills"; if (a.all_attacks === true) return "all_attacks"; if (actions.includes("attack")) return "attack"; if (tags.length) return TARGET_TAG[tags[0]] ?? "tag_other"; if (actions.length) return "actions"; return "default"; };

  const CATS = { skeleton: SKELETON, effect: EFFECT, surface: SURFACE, status: STATUS, condition: COND, cost: COST, trigger: TRIG, link: LINK, shape: SHAPE, change: CHANGE, element: ELEMENT, card: CARD, target: TARGET }; /* target 放最後（11-12）：前面各類的順序與真 1 倍分段不動 */
  const CAT_ZH = { skeleton: "骨架徽章", effect: "效果", surface: "表面", status: "狀態（圓片用）", condition: "條件", cost: "代價", trigger: "觸發／反應時機", link: "接續", shape: "形狀", change: "修正內容", element: "元素", card: "技能卡小圖", target: "修正技的改造對象" };
  /** 沒有 Q 版圖樣的狀態由這個掛鉤畫（樣張頁掛上現行的白色狀態圖樣）；沒掛時畫增益箭頭。 */
  const hooks = { status: null };
  function entry(cat, id) {
    if (cat === "effect" && typeof id === "string") { if (id.startsWith("status:")) return entry("status", id.slice(7)); if (id.startsWith("surface:")) return entry("surface", id.slice(8)); id = EFFECT_ALIAS[id] ?? id; }
    if (cat === "trigger") id = TRIG[id] ? id : (TRIG_ALIAS[id] ?? id);
    if (cat === "condition" && typeof id === "string" && id.startsWith("target_has_status:")) { const s = entry("status", id.slice(18)); return { zh: "目標帶有狀態：" + (s.zh ?? id.slice(18)), topic: "那個狀態的圖，右上一個問號", live: s.live, d: (c, o, T, opt) => { at(c, -1.6, 1.4, 0.84, (q) => s.d(q, o, T, opt)); if (!o.tiny) qmark(c, o, 7.4, -6, 0.8); } }; }
    const e = CATS[cat]?.[id]; if (e) return e;
    if (cat === "status") return { zh: id, topic: "（沒有 Q 版圖樣：現行圖樣頂著）", live: true, d: (c, o) => (hooks.status ? hooks.status(c, o, id) : QS.ACT.buff.d(c, o, QS.ACT.buff.def)) };
    return { zh: id, topic: "（不認得）", unknown: true, d: (c, o) => qmark(c, { ...o, flat: true }, 0, 0, 2) };
  }
  /** 圖樣定義（給 QIcons.render；畫在 48 格，±10 單位放大 1.8 倍）。cpx＝圖樣本身（±10 單位）顯示的 CSS px，決定簡化程度。 */
  function def(cat, id, cpx = 20, opt = {}) {
    const e = entry(cat, id);
    return { zh: e.zh, entry: e, d: (c, o) => { c.save(); c.translate(24, 24); c.scale(1.8, 1.8); e.d(c, { ...o, small: cpx <= 24, tiny: cpx <= 14 }, opt.tint, opt); c.restore(); } };
  }
  const BOX = 48 / 36; /* 圖樣格邊長＝圖樣本身（±10 單位）的 1.333 倍 */
  /** 只有圖樣的 canvas（不含圓底）：≤14px 不包外框（規則 8）。 */
  const glyph = (cat, id, cpx, res = 2, opt = {}) => Q.render(def(cat, id, cpx, opt), cpx * BOX, res, { ow: opt.ow ?? (cpx <= 14 ? 0 : Q.outlinePx(cpx)) });
  /** 在 ctx 目前的座標畫一個圖樣：中心 (x,y)，圖樣本身邊長 size（ctx 的單位）；unitPx＝ctx 的 1 單位是幾個 CSS px。 */
  /* 第 2 版（真 1 倍修正）：原本 drawImage(g, x, y, a, a) 把 round(a×res) 的 canvas 縮放貼到小數位置，瀏覽器重新取樣，外框與 1px 細節被抹糊（18px 圓片、56 角落最明顯）。
     改成照 canvas 原尺寸、左上角對齊整數裝置像素（直接呼叫 QIconsWeapons.blit；ctx 每單位＝unitPx×res 個裝置像素，原點要在整數像素上）。 */
  function paint(ctx, cat, id, x, y, size, unitPx = 1, res = 2, opt = {}) { const g = glyph(cat, id, size * unitPx, res, opt), a = size * BOX; QW.blit(ctx, g, x - a / 2, y - a / 2, a, unitPx * res); }
  /** 部件小圓片：深色圓底＋色環照現行（skillParts.ts 的 drawChip），裡面換 Q 版圖樣（圖樣本身＝直徑的 78%）。 */
  function chip(ctx, cat, id, x, y, r, o = {}) {
    ctx.save(); ctx.fillStyle = o.bg ?? "rgba(10,12,18,0.85)"; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
    if (o.ring !== false) { ctx.strokeStyle = o.ring ?? "rgba(255,255,255,0.35)"; ctx.lineWidth = Math.max(1, r * 0.12); ctx.stroke(); }
    paint(ctx, cat, id, x, y, r * 1.56, o.unitPx ?? 1, o.res ?? 2, o); ctx.restore();
  }
  const RING = { condition: "#ffe9a8", trigger: "#ffffff", link: "#ffffff", target: "#ffffff" }; /* target：現行 CORE_RING 白環 */
  /** 組裝列的一塊（現行 tileCanvas：100 單位、圓片半徑 42）：px 邊長的 canvas。chipCanvas、cardCanvas、canvas 三個都收 o.res／opt.res＝指定內部解析度（預設不變；1 是真 1 倍：canvas 寬高＝CSS px，樣張頁 ?part=true1x 用）。 */
  function chipCanvas(cat, id, px, zoom = 1, o = {}) {
    const res = o.res ?? (zoom === 1 ? 2 : zoom), cv = blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d"); x.scale((px * res) / 100, (px * res) / 100);
    if (cat === "skeleton") { x.fillStyle = "#14161c"; x.beginPath(); x.arc(50, 50, 40, 0, TAU); x.fill(); paint(x, cat, id, 50, 50, 62, px / 100, res, o); } /* 現行 skeletonTile：深色圓底、沒有色環、圖樣放大 3 倍 */
    else chip(x, cat, id, 50, 50, o.r ?? 42, { ring: RING[cat] ?? "rgba(255,255,255,0.3)", ...o, unitPx: px / 100, res });
    return cv;
  }
  /** 卡片小圖的圖樣本身（±10 單位）在 px 邊長的格子裡畫多大：最大 14px（≤14px 不包外框，圖樣才撐得滿格子；第 3 批的記號畫到 ±11.6 單位）。 */
  const cardPx = (px) => Math.min(14, px * 0.84);
  /** 技能卡小圖：px 邊長（常駐行 16、效果行 18、圖釘 13）；圖樣撐滿整格。 */
  function cardCanvas(id, px, zoom = 1, o = {}) { const res = o.res ?? (zoom === 1 ? 2 : zoom), cv = blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d"), cpx = cardPx(px); QW.blit(x, glyph("card", id, cpx, res, o), 0, 0, px * res, 1); return cv; } /* 第 2 版：原本貼在小數位置（-1.9 裝置像素），改成對齊整數像素 */

  // =====================================================================
  // 56／96px 完整技能圖示：主圖（第 3 批）＋四角小圓片＋骨架徽章＋底部效果列，擺位照現行 skillIcon.ts 的 paintSkillIcon。
  // 和現行不同的三處（主圖換成「道具＋動作」之後才有的）：被動／反應的觸發時機原本是主圖，現在放左上角（元素小圓片讓到它下面）；
  // 複合技的接續記號原本在斜切線中央，現在排進底部效果列、放在第二段效果的前面；沒有元素的技能不畫元素小圓片。
  // =====================================================================
  const effKey = (e) => (e.type === "apply_status" && e.status ? "status:" + e.status : e.type === "create_surface" && e.surface ? "surface:" + e.surface : e.type);
  /** 技能圖示資料（後端 SkillIcon）→ 部件清單；規則照現行 partsOf（核心效果＝第一個不是單純傷害的效果，放第一個，最多 4 個）。 */
  function partsOf(icon) {
    const kind = icon.kind || "active", segs = icon.segments ?? [], seen = new Set(); let list = [];
    segs.forEach((s, si) => { for (const e of s.effects ?? []) { const key = effKey(e); if (!seen.has(key)) { seen.add(key); list.push({ cat: "effect", id: key, seg: si }); } } });
    if (icon.modifier) list = icon.modifier.changes.map((ch) => ({ cat: "change", id: ch.key, seg: 0, value: ch.value, base: ch.key === "on_hit_effects" && ch.part_ids?.[0] ? (c, o) => entry("effect", ch.part_ids[0].replace(/^apply_status:/, "status:")).d(c, o) : undefined }));
    const ci0 = list.findIndex((e) => e.id !== "damage"), core = list.length ? list[ci0 === -1 ? 0 : ci0] : null; if (core) list = [core, ...list.filter((e) => e !== core)];
    const row = list.slice(0, 4), cond = icon.condition ? { cat: "condition", id: icon.condition.id === "target_has_status" && icon.condition.status ? "target_has_status:" + icon.condition.status : icon.condition.id } : null;
    return { kind, rarity: icon.rarity, el: icon.elements?.[0] ?? null, skeleton: segs[0]?.skeleton ?? null, trigger: (kind === "reaction" || kind === "passive") && icon.trigger ? icon.trigger : null, link: icon.link ?? null, cond, costs: icon.costs ?? [], row, core, shape: segs.map((s) => s.shape_id) };
  }
  const LINK_RING = "#7fd8ff";
  const COST_RING = { source: "#c89cff", gamble: "#ffffff", self: "#ff6a6a", stacks: "#ffd04a", once: "#ffd75e", delay: "#a8e0ff" };
  /** level："full"＝全部小圓片（現行 >40px 的擺位）；"mid"＝只有骨架徽章與觸發時機（技能卡 56px 的建議版）；"main"＝只有主圖（≤40px）。 */
  function paintIcon(ctx, icon, look, size, res = 2, opt = {}) {
    const level = opt.level ?? (size <= 40 ? "main" : "full"), P = partsOf(icon), kind = QS.PAD[look.kind] ? look.kind : "active", rar = QS.RARITY[look.rarity] ?? QS.RARITY.common, k = size / 100, u = size / 100;
    ctx.save(); ctx.scale(k, k); ctx.save(); QS.framePath(ctx, kind); ctx.clip(); QS.base(ctx, look);
    /* 主圖：full 時縮到 62（方框）／56（其他框形）單位、往上移，底下讓給效果列；mid 與 main 照第 3 批的留白 */
    const [pad, dy] = QS.PAD[kind], box = level === "full" ? (kind === "active" ? 62 : 56) : 100 * (1 - pad * 2), cx = 50, cy = level === "full" ? (kind === "active" ? 41 : 43) : 50 + 100 * dy;
    QW.blit(ctx, Q.render(QS.def(look), box * u, res, { ow: Q.outlinePx(size) }), cx - box / 2, cy - box / 2, box, u * res); ctx.restore(); /* 第 2 版：主圖也對齊整數裝置像素（同第 3 批 paint） */
    QS.framePath(ctx, kind, 1); ctx.lineWidth = look.rarity === "legendary" ? 5 : 3.5; ctx.strokeStyle = rar; ctx.stroke(); if (look.rarity === "legendary" || look.rarity === "epic") { QS.framePath(ctx, kind, 6); ctx.lineWidth = 1; ctx.globalAlpha = 0.6; ctx.stroke(); ctx.globalAlpha = 1; }
    const C = (cat, id, x, y, r, ring, extra = {}) => chip(ctx, cat, id, x, y, r, { ring, unitPx: u, res, ...extra });
    const badge = (x, y, r) => { ctx.fillStyle = "rgba(8,10,16,0.88)"; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); ctx.strokeStyle = rar; ctx.lineWidth = 2; ctx.stroke(); paint(ctx, "skeleton", P.skeleton, x, y, r * 1.56, u, res); };
    if (level === "mid") { if (P.trigger) C("trigger", P.trigger, 17, 17, 15, "#ffffff"); if (P.skeleton) badge(83, 83, 15); }
    if (level === "full") {
      /* 第 2 版：物理也不畫元素片（物理元素片＝白四芒閃光，和效果列的傷害圓片同圖，一張圖出現兩顆；美術 PM 定） */
      const el = P.el && P.el !== "physical" ? P.el : null;
      if (P.trigger) { C("trigger", P.trigger, 15, 15, 12.5, "#ffffff"); if (el) C("element", el, 12, 39, 8, false, { bg: "rgba(8,10,16,0.8)" }); }
      else if (el) C("element", el, 15, 15, 11, false, { bg: "rgba(8,10,16,0.8)" });
      const [c1, c2] = P.costs; if (c1) C("cost", c1, 85, 15, 11, COST_RING[c1]); if (c2) C("cost", c2, 85, 36, 8, COST_RING[c2]);
      if (P.cond) C("condition", P.cond.id, 14, 86, 11, "#ffe9a8");
      if (P.skeleton) badge(86, 86, 11);
      /* 底部效果列：算法照現行 effectRow（核心 11.5、其餘 8.5，放不下就縮）；接續記號（半徑 7）排在第二段第一個效果前面，沒有就放最後 */
      const items = P.row.map((e, i) => ({ ...e, r: i === 0 ? 11.5 : 8.5 })); if (P.link && items.length) { const j = items.findIndex((e, i) => i > 0 && e.seg === 1); items.splice(j === -1 ? items.length : j, 0, { cat: "link", id: P.link, r: 9, link: true }); } /* 第 2 版：接續記號 7→9 單位、色環換青色（LINK_RING），和效果圓片分開 */
      if (items.length) { const left = P.cond ? 26 : 5, right = 75, gap = 1.5; let total = items.reduce((a, e) => a + e.r * 2, 0) + (items.length - 1) * gap; if (total > right - left) { const f0 = (right - left - 23 - (items.length - 1) * gap) / (total - 23 - (items.length - 1) * gap); for (const e of items.slice(1)) e.r = Math.max(4.5, e.r * f0); total = items.reduce((a, e) => a + e.r * 2, 0) + (items.length - 1) * gap; }
        let x = (left + right) / 2 - total / 2; items.forEach((e, i) => { C(e.cat, e.id, x + e.r, 85 + (i === 0 ? 0 : 2), e.r, i === 0 ? "#ffffff" : e.link ? LINK_RING : "rgba(255,255,255,0.3)", { value: e.value, base: e.base, tint: e.cat === "shape" ? null : undefined }); x += e.r * 2 + gap; }); }
    }
    ctx.restore();
  }
  function canvas(icon, look, px, zoom = 1, opt = {}) { const res = opt.res ?? (zoom === 1 ? 2 : zoom), cv = blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d"); x.scale(res, res); paintIcon(x, icon, look, px, res, opt); return cv; }

  /** 每一類的清單（樣張總表、紀錄檔用）。 */
  const list = () => Object.fromEntries(Object.entries(CATS).map(([cat, T]) => [cat, Object.entries(T).map(([id, e]) => ({ cat, id, zh: e.zh, topic: e.topic, src: e.src ?? "new", px: e.px }))]));
  return { CATS, CAT_ZH, TARGET_TAG, targetOf, EFFECT_ALIAS, TRIG_ALIAS, SURF_TINT, RING, COST_RING, LINK_RING, UNLIT, BOX, hooks, entry, def, glyph, paint, chip, chipCanvas, cardCanvas, cardPx, partsOf, paintIcon, canvas, list };
})();
