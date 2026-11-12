// qIconsStatus.js：「小圖示改 Q 版」全量重畫第 5 批——狀態圖示（畫圖 agent 2026-11-12）。
// 規則：docs/art/Q版小圖示樣張.md 第 2 節（尤其 6、8、11、13）；紀錄：docs/art/Q版小圖示-第5批狀態.md；樣張頁：q-icons-status.html。
// 範圍：content/statuses.yaml 的全部 118 個狀態（遊戲端靠名詞表 status_look 顯示，不寫死清單）。
//   ・第 4 批已畫的 32 個（qIconsParts.js 的 STATUS）直接呼叫，不重畫（src "b4:status.<id>"）；
//   ・和第 3、4 批別的部件同題材的，直接呼叫那一個（src "b3:…"／"b4:effect.…"）；
//   ・其餘新畫，畫法照第 4 批同一套（±10 單位、原點為中心；o.tiny＝圖樣本身 ≤14px：一個主體、不包外框）。
// 框不動（規則 13）：外框形狀與顏色照現行 client/src/render/statusIcon.ts 的 paintStatusIcon（buff 圓、debuff 圓角方、neutral 六角；框色依 polarity），
//   只換框裡的圖。現行靠「圖樣顏色」表示控制類別（硬控黃、移動藍、心智紫），Q 版每個圖樣自帶本色，所以類別色改畫在**框的底色**（CLASS_BG，美術 PM 定）。
// 依賴（先載入）：qIcons.js、qIconsWeapons.js（blit）、qIconsSkills.js（ACT、ELEMENT）、qIconsParts.js（entry、BOX）。狀態框的邏輯只在這個檔，不放進 qIconsParts.js。
window.QIconsStatus = (() => {
  const Q = window.QIcons, QS = window.QIconsSkills, QW = window.QIconsWeapons, QP = window.QIconsParts, { mix, f, rr, ci, el, poly, ln, starPts, flame, drop, halo } = Q.H, TAU = Math.PI * 2, PI = Math.PI, OUT = Q.OUT;
  const CREAM = "#f2e6c8", STEEL = "#c3ccd6", GOLD = "#e8bb48", STONE = "#b4ac9a", STONE_L = "#ece6d6", STONE_D = "#8c8474";
  const st = (c, col, w, fn, cap = "round") => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
  const at = (c, x, y, k, fn, rot = 0) => { c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k); fn(c); c.restore(); };
  const fit = (d, k) => (c, o, T, opt) => at(c, 0, 0, k, (q) => d(q, o, T, opt));
  /** 第 3 批的效果記號、第 4 批的部件：同一個題材同一個形，直接呼叫。 */
  const act = (id, T) => (c, o) => QS.ACT[id].d(c, o, T ?? QS.ACT[id].def);
  const part = (cat, id) => (c, o, T, opt) => QP.entry(cat, id).d(c, o, T, opt);

  // ---------------- 共用零件（和第 4 批同一個畫法；第 4 批沒有匯出的照原樣抄一份，註明出處） ----------------
  /** 第 4 批 qIconsParts.js 的 shieldBlue（帶電護盾、易傷用的盾形）原樣。 */
  const shieldBlue = (c, o, T = ["#6ab8f0", "#cfe8ff"]) => { const P = [[-9.4, -9.6], [9.4, -9.6], [8.8, 2], [0, 10], [-8.8, 2]]; poly(c, T[0], P, 1); poly(c, T[1], [[-9.4, -9.6], [0, -9.6], [0, 10], [-8.8, 2]], 1); };
  /** 第 4 批的 hexPts、stancePlate（姿態六角臂章）原樣。 */
  const hexPts = (R) => [0, 1, 2, 3, 4, 5].map((i) => [Math.cos((i / 6) * TAU - PI / 2) * R, Math.sin((i / 6) * TAU - PI / 2) * R]);
  const stancePlate = (col, hi, emblem) => (c, o) => { const P = hexPts(10.6); poly(c, col, P, 0.5); poly(c, hi, [P[0], P[5], P[4], [-5.6, 3], [-5.6, -4.4]]); halo(c, o, (q) => emblem(q, o)); };
  /** 第 4 批的 bladeSword（亮色單手劍，直立、刃尖朝 −y），B＝刃的三色。 */
  const bladeSword = (c, o, B = [STEEL, "#ffffff", "#98a2ae"]) => { c.save(); c.translate(0, -0.65);
    poly(c, B[0], [[-2.9, 3.6], [-2.9, -9.4], [0, -13.6], [2.9, -9.4], [2.9, 3.6]], 0.4);
    poly(c, B[1], [[-2.9, 3.6], [-2.9, -9.4], [0, -13.6], [-0.4, -9.4], [-0.4, 3.6]]); f(c, B[2], () => c.rect(1.3, -9, 1.6, 12.6));
    rr(c, GOLD, -6.4, 3.4, 12.8, 3.4, 1.5); f(c, "#fff0b0", () => c.roundRect(-6.4, 3.4, 12.8, 1.2, [1.5, 1.5, 0, 0]));
    rr(c, "#a8703e", -1.7, 6.6, 3.4, 5.4, 1); ci(c, GOLD, 0, 12.6, 2.4); c.restore(); };
  const diagSword = (k, B) => (c, o) => at(c, 0, 0, k, (q) => bladeSword(q, o, B), PI / 4);
  /** 第 4 批的 bolt（卡片 AP、給予 AP 的黃閃電）原樣。 */
  const bolt = (c, o) => { poly(c, "#ffd23a", [[1.6, -10.6], [-7.6, 1.6], [-1.6, 1.6], [-4.2, 10.6], [7, -2.6], [1, -2.6], [4.2, -10.6]], 0.5); if (!o.tiny) poly(c, "#fff6b0", [[1.8, -9.4], [-5.6, 0.6], [-3.4, 0.6], [3.2, -9.4]]); };
  /** 第 4 批的 crystal（代價「源力」的淡紫六角晶石）原樣；源晶家族（碎晶、共鳴、灌注、湧動）都從它變化。 */
  const crystal = (c) => { poly(c, "#b8a8ff", [[0, -10.6], [7.8, -4.6], [7.8, 4.6], [0, 10.6], [-7.8, 4.6], [-7.8, -4.6]], 0.6); poly(c, "#f2ecff", [[0, -10.6], [-7.8, -4.6], [0, -1]]); poly(c, "#d6ccff", [[-7.8, -4.6], [-7.8, 4.6], [0, -1]]); poly(c, "#7a68c8", [[7.8, -4.6], [7.8, 4.6], [0, 10.6], [0, -1]]); poly(c, "#9a86ff", [[-7.8, 4.6], [0, 10.6], [0, -1]]); };
  /** 第 4 批的 upArrow（修正內容的「＋」箭頭）原樣。 */
  const upArrow = (c, o, T = ["#ffb23a", "#fff6c8"]) => { poly(c, T[0], [[0, -11], [10, -1], [4, -1], [4, 9.6], [-4, 9.6], [-4, -1], [-10, -1]], 0.6); poly(c, T[1], [[0, -11], [-10, -1], [-4, -1], [-4, 9.6], [0, 9.6]]); };
  /** 第 4 批的 bust（≤24px 的米白人形：圓頭加圓肩的半身）原樣。 */
  const bust = (c, col, x, y, k = 1) => { ci(c, col, x, y - 4.6 * k, 3.7 * k); f(c, col, () => { c.moveTo(x - 6.2 * k, y + 7 * k); c.quadraticCurveTo(x - 6.2 * k, y - 0.4 * k, x, y - 0.4 * k); c.quadraticCurveTo(x + 6.2 * k, y - 0.4 * k, x + 6.2 * k, y + 7 * k); c.closePath(); }); };
  const heart = (c, col, x, y, s) => { c.save(); c.translate(x, y); c.scale(s, s); c.beginPath(); c.moveTo(0, 7); c.bezierCurveTo(-11, -1, -7, -10, 0, -4.5); c.bezierCurveTo(7, -10, 11, -1, 0, 7); c.closePath(); c.fillStyle = col; c.fill(); c.restore(); };
  const star4 = (c, col, x, y, R, core = "#ffffff") => { poly(c, col, starPts(x, y, R, R * 0.36, 4), 0.3); if (core) poly(c, core, starPts(x, y, R * 0.55, R * 0.2, 4)); };

  // ---------------- 這批新增的零件 ----------------
  /** 旗桿（木桿＋金頂珠）：戰意的紅三角旗、開場休戰的白旗共用；旗的形不同（三角 vs 方形波浪）。 */
  const pole = (c) => { rr(c, "#a06a36", -8.4, -8.6, 2.8, 19.2, 1.2); f(c, "#d8a868", () => c.rect(-8.4, -8.6, 1, 19)); ci(c, GOLD, -7, -9.4, 2.2); };
  /** 誓約徽章：一枚金屬圓章（中間一顆五角星）掛在兩條紅緞帶上；三個難度用銅、銀、金分。 */
  const MEDAL = { bronze: ["#c27a48", "#f0b088", "#8a4a22"], silver: ["#d0d8e0", "#ffffff", "#8a96a4"], gold: ["#e8bb48", "#fff0b0", "#9c7420"] };
  const medal = (m) => (c, o) => { const [a, b, d] = MEDAL[m];
    for (const s of [-1, 1]) poly(c, s < 0 ? "#d8404a" : "#b02a36", [[s * 1.2, 2], [s * 6.6, 2], [s * 8.2, 10.6], [s * 5.4, 8.6], [s * 3, 10.6]], 0.3);
    ci(c, a, 0, -2.6, 8); f(c, d, () => { c.arc(0, -2.6, 8, -0.3, PI * 0.8); c.arc(0, -2.6, 6.2, PI * 0.8, -0.3, true); c.closePath(); }); poly(c, b, starPts(0, -2.6, 5, 2.1, 5), 0.2); if (!o.tiny) el(c, "#ffffff", -4, -6, 1.8, 1.1, -0.6); };
  /** 熔核：一顆橘紅的熾熱圓核，表面幾塊深色硬殼、殼縫透出黃白的光；寒燼換冰色。 */
  const CORE = { lava: ["#ff6a1a", "#ffe08a", "#6a3424", "#ffb23a"], frost: ["#5ab8f0", "#ffffff", "#2a4a7a", "#bfefff"] };
  const core = (kind, R = 9.4) => (c, o) => { const [body, glow, crust, mid] = CORE[kind];
    ci(c, body, 0, 0.4, R); ci(c, mid, -1, -0.4, R * 0.62); ci(c, glow, -1.4, -0.8, R * 0.3);
    const k = R / 9.4; for (const P of [[[-9, -2.4], [-4.6, -8.2], [-1.6, -4.4], [-5, -0.6]], [[2.6, -8.6], [8.4, -4.6], [5.4, -1.4], [1.2, -3.8]], [[-6.2, 5.4], [-1.6, 3.4], [0.6, 8.8], [-3.6, 9.4]], [[4.2, 2.6], [9.2, 2.2], [6.8, 7.8], [3.2, 6.6]]]) poly(c, crust, P.map(([x, y]) => [x * k, y * k + 0.4]), 0.3); };
  /** 龜殼形的殼（熔殼、硬殼）：上緣圓、下緣一排小圓弧（殼的邊片），殼面中間一塊六角殼片、四周放射的縫；不畫帽簷（第 1 稿有一條橫的底座，像安全帽）。 */
  const dome = (body, hi, seam, w = 1.6, rim = body) => (c, o) => { f(c, body, () => { c.moveTo(-10.4, 4.6); c.bezierCurveTo(-10.6, -11.4, 10.6, -11.4, 10.4, 4.6); c.closePath(); }); for (let i = 0; i < 5; i++) ci(c, rim, -8.4 + i * 4.2, 4.8, 2.4);
    f(c, hi, () => { c.moveTo(-8.4, 1.6); c.bezierCurveTo(-8.4, -5.6, -4.6, -8, -1.4, -8.4); c.lineTo(-1.6, -6.4); c.bezierCurveTo(-4.4, -5.8, -6.4, -3.6, -6.4, 1.6); c.closePath(); });
    const H = [[-3.4, -5], [3.4, -5], [5, -1], [3.4, 2.6], [-3.4, 2.6], [-5, -1]]; ln(c, seam, w, [...H, H[0]]); for (const [a, b] of [[H[0], [-5.6, -8.6]], [H[1], [5.6, -8.6]], [H[2], [10.2, -1]], [H[5], [-10.2, -1]], [H[3], [5.4, 4.6]], [H[4], [-5.4, 4.6]]]) ln(c, seam, w, [a, b]); };

  // ---------------- 元素架勢的紋章（第 4 批 stance_holy_1、stance_shadow_1 的做法：元素色的六角臂章＋淺色紋章） ----------------
  const EMBLEM = {
    physical: { plate: ["#6e7884", "#a4aeba"], zh: "鋼灰臂章＋亮色直劍", d: (c, o) => at(c, 0, 0.6, 0.6, (q) => bladeSword(q, o)) },
    fire: { plate: ["#e8601a", "#ffa86a"], zh: "橘色臂章＋黃白火球（圓球拖一道往左上的火尾）", d: (c, o) => { f(c, "#ffe08a", () => { c.moveTo(-7.6, -7.6); c.quadraticCurveTo(-1.6, -4.6, 1.8, -3.2); c.lineTo(-3.2, 1.8); c.quadraticCurveTo(-4.6, -1.6, -7.6, -7.6); c.closePath(); }); ci(c, "#ffe08a", 1.6, 1.6, 5); ci(c, "#ffffff", 0.8, 0.8, 2.6); } },
    ice: { plate: ["#3f96d0", "#94d0f4"], zh: "冰藍臂章＋白色粗雪花", d: (c, o) => { for (let i = 0; i < 3; i++) at(c, 0, 0.4, 1, (q) => { rr(q, "#ffffff", -1.3, -7, 2.6, 14, 1.3); if (!o.tiny) for (const s of [-1, 1]) ln(q, "#ffffff", 1.4, [[0, s * -4.4], [2.2, s * -6.4]]); }, (i * PI) / 3); ci(c, "#e0f6ff", 0, 0.4, 2.2); } },
    lightning: { plate: ["#5a5ac8", "#9a9af0"], zh: "靛藍臂章＋黃閃電", d: (c, o) => at(c, 0, 0.4, 0.66, (q) => bolt(q, o)) },
    poison: { plate: ["#3f8a24", "#86c85a"], zh: "綠色臂章＋淡綠毒滴（右上一顆泡）", d: (c, o) => { drop(c, "#e6ffd0", -0.8, 1, 0.68); ci(c, "#e6ffd0", 4.8, -4.6, 1.8); if (!o.tiny) el(c, "#ffffff", -2.6, 1.4, 1, 1.8, 0.4); } },
    wind: { plate: ["#24907a", "#6ad0b8"], zh: "青綠臂章＋白色旋風（一圈半的螺旋，尾巴往左下甩）", d: (c, o) => { const P = [[-7.4, 6.4], [-4.6, 5.4]]; for (let i = 0; i <= 28; i++) { const t = i / 28, a = PI * 0.62 - t * PI * 2.6, r = 6.4 - t * 4.8; P.push([0.6 + Math.cos(a) * r, -0.6 + Math.sin(a) * r]); } ln(c, "#ffffff", 2.3, P); } },
    earth: { plate: ["#8a5a2a", "#c48c52"], zh: "褐色臂章＋淺土色岩塊", d: (c, o) => { poly(c, "#f0d0a0", [[-6, 4.6], [-6.4, -1.4], [-2, -6], [4.4, -5], [6.6, 0.6], [4, 5.4]], 0.6); poly(c, "#fff0d4", [[-6.4, -1.4], [-2, -6], [-0.6, -1.4]]); poly(c, "#c89a60", [[4.4, -5], [6.6, 0.6], [4, 5.4], [1.6, 0.4]]); } },
  };
  /* 第 4 批已畫的兩個元素架勢（聖輝、暗影）：壹級直接呼叫第 4 批；貳～伍級同一個圖（級數不畫在圖上，見紀錄檔 6.2）。 */
  const ELEMENTS = ["physical", "fire", "ice", "lightning", "poison", "wind", "earth", "holy", "shadow"];

  // =====================================================================
  // 新畫與借用（第 4 批沒有的 86 個裡，元素架勢以外的 43 個）
  // =====================================================================
  const NEW = {
    // ---- 借用第 3、4 批同題材的部件（同一個題材同一個形） ----
    revealed: { zh: "被揭露", topic: "睜開的眼睛（同效果「揭露」）", src: "b4:effect.reveal", d: part("effect", "reveal") },
    time_bomb: { zh: "定時炸彈", topic: "圓炸彈、引信頭黃火花（同效果「定時炸彈」）", src: "b4:effect.delayed_damage", d: part("effect", "delayed_damage") },
    shielded: { zh: "護盾", topic: "淡藍小盾、白十字（同效果「護盾」）", src: "b3:shield", d: act("shield") },
    undying: { zh: "免死", topic: "紅心、右下一面小藍盾（同效果「免死」）", src: "b4:effect.cheat_death", d: part("effect", "cheat_death") },
    soul_link: { zh: "靈魂連結", topic: "兩個扣在一起的淡紫圓環（前後交扣）", d: (c, o) => { const ring = (q, x, a0 = 0, a1 = TAU) => st(q, "#c8a0ff", o.tiny ? 3.2 : 2.8, (p) => p.arc(x, 0.4, 5.6, a0, a1), "butt"); ring(c, -3.8); halo(c, o, (q) => { ring(q, 3.8); if (!o.tiny) st(q, "#efe2ff", 1.1, (p) => p.arc(3.8, 0.4, 5.6, PI * 1.15, PI * 1.55), "butt"); }); halo(c, o, (q) => ring(q, -3.8, -0.75, 0.05)); if (!o.tiny) st(c, "#efe2ff", 1.1, (p) => p.arc(-3.8, 0.4, 5.6, PI * 1.15, PI * 1.55), "butt"); } }, /* 第 4 批效果「分擔傷害」（Y 形分岔箭頭）在 1 倍下讀不出連結，也比現行的雙環難認，這裡另畫；同題材不同形，寫進紀錄檔待決 */
    // ---- 護盾家族（第 4 批帶電護盾的做法：同一面淡藍盾，白十字換成各自的記號） ----
    shielded_thorns: { zh: "反傷護盾", topic: "淡藍盾，盾緣往外長出五根鐵刺", d: fit((c, o) => { halo(c, o, (q) => { for (const [x, y, a] of [[-9.4, -9.6, -2.36], [9.4, -9.6, -0.79], [0, -9.6, -1.57], [-9.2, -2, -2.9], [9.2, -2, -0.24]]) at(q, x, y, 1, (p) => poly(p, "#7d8794", [[0, -2.2], [4.6, 0], [0, 2.2]], 0.3), a); }); shieldBlue(c, o); halo(c, o, (q) => poly(q, "#5a6169", [[-4.6, 3.6], [0, -5.4], [4.6, 3.6], [0, 1.2]], 0.3)); }, 0.8) }, /* 第 1 稿盾面三根刺像遠山、城市天際線；改成盾緣長刺＋盾面一個鐵刺尖 */
    shielded_mending: { zh: "回春護盾", topic: "淡藍盾、盾面一株綠芽（同狀態「再生」的嫩芽）", d: fit((c, o) => { shieldBlue(c, o); halo(c, o, (q) => at(q, 0, -0.6, 0.62, (p) => QP.entry("status", "regenerating").d(p, o))); }, 0.86) },
    shielded_wet: { zh: "水幕護盾", topic: "淡藍盾、盾面一顆深藍水滴", d: fit((c, o) => { shieldBlue(c, o); halo(c, o, (q) => { drop(q, "#2a78d8", 0, -0.6, 0.58); if (!o.tiny) el(q, "#cfe8ff", -1.6, 0.6, 0.9, 1.6, 0.4); }); }, 0.86) },
    shielded_marking: { zh: "烙印護盾", topic: "淡藍盾、盾面一個紅準星（同狀態「被標記」）", d: fit((c, o) => { shieldBlue(c, o); halo(c, o, (q) => at(q, 0, -1, 0.56, (p) => QS.ACT.mark.d(p, o, QS.ACT.mark.def))); }, 0.86) },
    // ---- 姿態（第 4 批的六角臂章，換底色與紋章） ----
    stance_flame: { zh: "焰刃姿態", topic: "焦橘臂章、一把刃換成黃白的斜劍（劍尖一撮火）", d: stancePlate("#c4481c", "#f08a58", (c, o) => { at(c, 0, 0, 0.56, (q) => diagSword(1, ["#ffe08a", "#ffffff", "#ffb23a"])(q, o)); if (!o.tiny) flame(c, "#ffffff", 4.4, -4.6, 0.2); }) },
    stance_blaze: { zh: "烈焰姿態", topic: "深紅橘臂章、一團大火焰後面立著一把黃白斜劍", d: stancePlate("#d23a1a", "#ff8a6a", (c, o) => { flame(c, "#ffd23f", 0, 0.6, 0.66); at(c, 0, 0.4, 0.5, (q) => diagSword(1, ["#ffffff", "#ffffff", "#ffe08a"])(q, o)); }) },
    stance_frost: { zh: "霜刃姿態", topic: "冰藍臂章、一把淡青白刃的斜劍", d: stancePlate("#3a7cc0", "#86b8e8", (c, o) => at(c, 0, 0, 0.56, (q) => diagSword(1, ["#d8f6ff", "#ffffff", "#8fe3ff"])(q, o))) },
    stance_glacier: { zh: "冰川姿態", topic: "深藍臂章、三根白色冰柱（中間高）", d: stancePlate("#2a5aa8", "#6a9ad8", (c, o) => { poly(c, "#d8f6ff", [[-6.4, 6], [-6.4, -0.6], [-4.4, -3.6], [-2.4, -0.6], [-2.4, 6]], 0.3); poly(c, "#d8f6ff", [[2.4, 6], [2.4, -0.6], [4.4, -3.6], [6.4, -0.6], [6.4, 6]], 0.3); poly(c, "#ffffff", [[-2.2, 6], [-2.2, -3.6], [0, -7.4], [2.2, -3.6], [2.2, 6]], 0.3); }) },
    stance_bastion: { zh: "堡壘姿態", topic: "石板灰臂章、一座米白的城塔（頂上三個垛口）", d: stancePlate("#5a6478", "#8e9aae", (c, o) => { f(c, "#f2ead6", () => { c.moveTo(-5.2, 6.6); c.lineTo(-5.2, -6.6); c.lineTo(-2.6, -6.6); c.lineTo(-2.6, -4.4); c.lineTo(-0.9, -4.4); c.lineTo(-0.9, -6.6); c.lineTo(0.9, -6.6); c.lineTo(0.9, -4.4); c.lineTo(2.6, -4.4); c.lineTo(2.6, -6.6); c.lineTo(5.2, -6.6); c.lineTo(5.2, 6.6); c.closePath(); }); f(c, "#4a5262", () => c.roundRect(-1.6, 1.4, 3.2, 5.2, [1.6, 1.6, 0, 0])); if (!o.tiny) f(c, "#c8bea6", () => c.rect(2.6, -4.4, 2.6, 11)); }) },
    // ---- 種族技 ----
    race_adapt: { zh: "應變", topic: "米白人形往右閃，背後兩道速度線，一支紅箭頭從頭頂上面擦過去", d: (c, o) => { for (const [y, w] of [[-1.4, 6.4], [3.4, 4.6]]) rr(c, CREAM, -10.6, y, w, 2.4, 1.2); bust(c, CREAM, 3, 2.4, 1.02); halo(c, o, (q) => { ln(q, "#ff5a5a", 2.2, [[-9.4, -8.6], [5, -8.6]]); poly(q, "#ff5a5a", [[4.4, -11.6], [10.4, -8.6], [4.4, -5.6]], 0.3); }); } },
    race_stonewall: { zh: "穩若磐石", topic: "地上一塊大灰石，左邊一支紅箭頭撞上去停住", d: (c, o) => { rr(c, "#8a6a40", -10.6, 7, 21.2, 3.6, 1.6); poly(c, STONE, [[-5.4, 7.2], [-7, 0], [-3.6, -6.6], [3.6, -8.4], [8.4, -3], [8.6, 7.2]], 0.6); poly(c, STONE_L, [[-7, 0], [-3.6, -6.6], [3.6, -8.4], [1, -2], [-3.4, 0.6]]); poly(c, STONE_D, [[8.4, -3], [8.6, 7.2], [3, 7.2], [3.6, 1]]); halo(c, o, (q) => { ln(q, "#ff5a5a", 2.2, [[-11, 2.4], [-8.4, 2.4]], "butt"); poly(q, "#ff5a5a", [[-9, -0.4], [-6, 2.4], [-9, 5.2]], 0.2); }); } },
    // ---- 一般增益、減益 ----
    rallied: { zh: "戰意", topic: "木旗桿上一面紅色三角旗", d: (c, o) => { pole(c); poly(c, "#e8403a", [[-5.6, -8.4], [10.4, -3.6], [-5.6, 1.4]], 0.6); poly(c, "#ff8a7a", [[-5.6, -8.4], [10.4, -3.6], [-5.6, -4.6]]); } },
    league_truce: { zh: "開場休戰", topic: "木旗桿上一面白旗（方形、右緣波浪）", d: (c, o) => { pole(c); f(c, "#f6f2e6", () => { c.moveTo(-5.6, -8.8); c.lineTo(9.4, -8.8); c.quadraticCurveTo(7.4, -6, 9.8, -3.6); c.quadraticCurveTo(11, -1, 9.4, 1.6); c.lineTo(-5.6, 1.6); c.closePath(); }); f(c, "#c8c0ac", () => { c.moveTo(-5.6, -2); c.lineTo(9.6, -2); c.quadraticCurveTo(11, -0.4, 9.4, 1.6); c.lineTo(-5.6, 1.6); c.closePath(); }); } },
    commanding: { zh: "號令", topic: "青色小靈（召喚物），右上一個橘黃的朝上箭頭", d: (c, o) => { at(c, -2, 1.8, 0.84, (q) => QS.ACT.summon.d(q, o, QS.ACT.summon.def)); halo(c, o, (q) => at(q, 6, -5.6, 0.46, (p) => upArrow(p, o))); } },
    armor_broken: { zh: "破甲", topic: "亮鋼胸甲（圓肩、V 領、收腰），一道深色裂縫，右下崩掉一塊", d: (c, o) => { const P = [[-10.2, -6.6], [-6.4, -9.6], [-2.8, -9.6], [0, -6], [2.8, -9.6], [6.4, -9.6], [10.2, -6.6], [8.2, 0.4], [7.2, 9.8], [-7.2, 9.8], [-8.2, 0.4]]; c.save(); c.beginPath(); P.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.closePath(); c.moveTo(7.6, 3); c.lineTo(3.4, 5.4); c.lineTo(4.6, 10.4); c.lineTo(8.6, 10.4); c.closePath(); c.clip("evenodd"); poly(c, "#c3ccd6", P, 0.6); poly(c, "#eef2f6", [[-10.2, -6.6], [-6.4, -9.6], [-2.8, -9.6], [0, -6], [0, 9.8], [-7.2, 9.8], [-8.2, 0.4]]); f(c, "#8a96a4", () => c.rect(5, -6, 3.4, 16)); f(c, "#9aa4b0", () => c.rect(-8, 3.6, 16, 1.6)); c.restore(); ln(c, OUT, 1.8, [[1.2, -5.4], [-1.4, -1.6], [1.4, 1.4], [-0.6, 5], [0.8, 9.6]], "miter"); halo(c, o, (q) => poly(q, "#a8b2be", [[8.6, 5.2], [5.4, 7], [6.4, 10.6], [9.6, 9.6]], 0.3)); } },
    entangled: { zh: "纏繞", topic: "褐色靴子（同 HUD「移動」）的靴筒被兩圈淡褐繩子纏住", d: (c, o) => { at(c, 0.6, 0.6, 0.47, (q) => { q.translate(-27, -24); Q.ART.hud.move.d(q, o); }); halo(c, o, (q) => { for (const y of [-6.4, -1.2]) { ln(q, "#ecc890", 2.6, [[-8.6, y + 2.4], [7.2, y - 1.8]]); } ln(q, "#ecc890", 2.2, [[7.2, -3], [10, -7.4]]); }); } },
    overdrawn: { zh: "透支", topic: "黃閃電（同卡片 AP），右下一個紅色減號", d: (c, o) => { at(c, -1.6, -0.6, 0.95, (q) => bolt(q, o)); halo(c, o, (q) => rr(q, "#ff5a5a", 2.6, 5.4, 8.6, 3.4, 1.2)); } },
    heart_link: { zh: "連心", topic: "兩顆疊著的心（後面粉、前面紅）", d: (c, o) => { heart(c, "#f49ab0", -3.6, -1.8, 0.86); if (!o.tiny) el(c, "#ffd8e0", -7, -4.6, 1.8, 1.1, -0.6); halo(c, o, (q) => { heart(q, "#f0503e", 3.4, 2.6, 0.9); if (!o.tiny) el(q, "#ffb0a0", 0.4, 0.4, 1.8, 1.1, -0.6); }); } },
    mist_return: { zh: "歸一", topic: "一道灰白的霧旋往中心收，中心一個綠十字（回血）", d: (c, o) => { st(c, "#dfe4ee", 3, (x) => { x.arc(0, 0, 8.6, PI * 0.9, PI * 2.1); }, "butt"); st(c, "#b8c0d0", 2.6, (x) => { x.arc(0.6, 0.6, 5.4, PI * 1.9, PI * 3.0); }, "butt"); halo(c, o, (q) => { rr(q, "#5ad06a", -1.5, -4.2, 3, 8.4, 0.8); rr(q, "#5ad06a", -4.2, -1.5, 8.4, 3, 0.8); }); } },
    // ---- 陣法（劍陣、護陣、鎖霧大陣） ----
    sword_formation: { zh: "劍陣", topic: "三把並排直立的亮劍（中間那把高一點）", d: (c, o) => { for (const x of [-6.4, 6.4]) at(c, x, 1.6, 0.6, (q) => bladeSword(q, o)); halo(c, o, (q) => at(q, 0, -0.4, 0.68, (p) => bladeSword(p, o))); } },
    array_ward: { zh: "護陣", topic: "地上一圈青綠的陣紋環，中心一顆陣眼玉石", d: (c, o) => { st(c, "#5ad0b0", 3, (x) => x.arc(0, 0, 8.8, 0, TAU)); if (!o.tiny) for (let i = 0; i < 6; i++) ci(c, "#c8fff0", Math.cos((i / 6) * TAU) * 8.8, Math.sin((i / 6) * TAU) * 8.8, 1); poly(c, "#7fe0c0", [[0, -5.6], [4.4, 0], [0, 5.6], [-4.4, 0]], 0.4); poly(c, "#e6fff6", [[0, -5.6], [-4.4, 0], [0, 0]]); } },
    summit_array_ward: { zh: "鎖霧大陣", topic: "同護陣的陣紋環與陣眼，下半一團灰白的霧", d: (c, o) => { NEW.array_ward.d(c, o); halo(c, o, (q) => { for (const [x, y, r] of [[-5.4, 6.4, 3.6], [0, 5.4, 4.2], [5.4, 6.6, 3.4]]) ci(q, "#e4e8f0", x, y, r); rr(q, "#e4e8f0", -8.6, 6.4, 17.2, 3.6, 1.8); if (!o.tiny) f(q, "#b8c0d0", () => q.rect(-8.6, 8.6, 17.2, 1.4)); }); } },
    // ---- 源晶（碎晶之主一戰） ----
    shard_burst: { zh: "碎晶", topic: "淡紫源晶裂成兩半往兩邊散開，右下一顆藍水滴（晶液）", d: (c, o) => { c.save(); c.beginPath(); c.moveTo(-12, -12); c.lineTo(1.4, -12); c.lineTo(-1.2, -2); c.lineTo(1.6, 3); c.lineTo(-0.6, 12); c.lineTo(-12, 12); c.closePath(); c.clip(); at(c, -1.8, -0.6, 0.92, crystal); c.restore(); c.save(); c.beginPath(); c.moveTo(12, -12); c.lineTo(1.4, -12); c.lineTo(-1.2, -2); c.lineTo(1.6, 3); c.lineTo(-0.6, 12); c.lineTo(12, 12); c.closePath(); c.clip(); at(c, 1.8, 0.4, 0.92, crystal); c.restore(); if (!o.tiny) halo(c, o, (q) => drop(q, "#4aa8ff", 7.4, 6.6, 0.3)); } },
    rift_resonance: { zh: "源晶共鳴", topic: "淡紫源晶，左右各兩道往外的共鳴弧", d: (c, o) => { at(c, 0, 0, 0.66, crystal); for (const s of [-1, 1]) { st(c, "#e0d4ff", 2.2, (x) => x.arc(0, 0, 7.6, s > 0 ? -0.6 : PI - 0.6, s > 0 ? 0.6 : PI + 0.6), "round"); if (!o.tiny) st(c, "#b8a8ff", 1.8, (x) => x.arc(0, 0, 10.2, s > 0 ? -0.5 : PI - 0.5, s > 0 ? 0.5 : PI + 0.5), "round"); } } },
    rift_channel: { zh: "灌注源晶", topic: "中間一顆淡紫源晶，三道光往外灌進三根小晶柱", d: (c, o) => { for (let i = 0; i < 3; i++) { const a = -PI / 2 + (i * TAU) / 3, x = Math.cos(a) * 8, y = Math.sin(a) * 8; ln(c, "#d6ccff", 1.8, [[Math.cos(a) * 3.6, Math.sin(a) * 3.6], [x, y]]); poly(c, "#b8a8ff", [[x, y - 3], [x + 2, y - 1], [x + 2, y + 2.4], [x - 2, y + 2.4], [x - 2, y - 1]], 0.3); } halo(c, o, (q) => at(q, 0, 0, 0.46, crystal)); } },
    crystal_surge: { zh: "晶能湧動", topic: "淡紫源晶，右上一個橘黃的朝上箭頭", d: (c, o) => { at(c, -2.2, 1.6, 0.82, crystal); halo(c, o, (q) => at(q, 6, -5.8, 0.46, (p) => upArrow(p, o))); } },
    crystal_surge_2: { zh: "晶能狂湧", topic: "淡紫源晶，右上兩個疊著的橘黃朝上箭頭", d: (c, o) => { at(c, -2.2, 1.6, 0.82, crystal); halo(c, o, (q) => { at(q, 6.2, -2.4, 0.42, (p) => upArrow(p, o)); at(q, 6.2, -7.6, 0.42, (p) => upArrow(p, o)); }); } },
    rift_collapse: { zh: "界崩", topic: "一塊灰石浮台（平頂、底下尖）從中間裂開，右半塊往下掉、歪一邊，底下兩顆碎石", d: (c, o) => { const half = (s) => (q) => { q.save(); q.scale(s, 1); poly(q, STONE, [[0.4, -4.4], [9.6, -4.4], [8.4, -0.6], [3.6, 5.6], [0.4, 6.4], [1.8, 2], [-0.2, -1.2]], 0.4); f(q, STONE_L, () => q.rect(0.6, -4.4, 9, 1.8)); poly(q, STONE_D, [[9.6, -2.6], [8.4, -0.6], [3.6, 5.6], [5, -0.6]]); q.restore(); }; at(c, -0.6, -4, 1, half(-1), 0); at(c, 1.6, -0.6, 1, half(1), 0.42); for (const [x, y, r] of [[-1.6, 7.4, 1.8], [1.4, 9.8, 1.3]]) poly(c, STONE_D, [[x - r, y], [x, y - r], [x + r, y], [x, y + r]], 0.3); } }, /* 第 1 稿兩片斜板拼成一個 V（像翅膀、打開的書）、第 2 稿左右對稱往下歪（像飛蛾）；改成左半不動、右半往下掉的不對稱構圖 */
    charging: { zh: "蓄力", topic: "一顆黃白的能量球，外面兩道往內捲的橘色弧", d: (c, o) => { for (let i = 0; i < 2; i++) st(c, "#ffb23a", 2.8, (x) => x.arc(0, 0, 8.6, i * PI + 0.2, i * PI + 1.9), "round"); for (let i = 0; i < 2; i++) at(c, Math.cos(i * PI + 1.9) * 8.6, Math.sin(i * PI + 1.9) * 8.6, 1, (q) => poly(q, "#ffb23a", [[-3, -2.4], [3, -2.4], [0, 2.4]], 0.3), i * PI + 1.9 + PI); ci(c, "#ffe08a", 0, 0, 5); ci(c, "#ffffff", -0.8, -0.8, 2.4); } },
    // ---- 誓約、循環賽 ----
    oath_bonus_easy: { zh: "誓約之力・易", topic: "銅色誓約徽章（紅緞帶、中間一顆星）", d: medal("bronze") },
    oath_bonus_medium: { zh: "誓約之力・中", topic: "銀色誓約徽章", d: medal("silver") },
    oath_bonus_hard: { zh: "誓約之力・難", topic: "金色誓約徽章", d: medal("gold") },
    oath_broken: { zh: "破誓", topic: "金色誓約徽章被一道紅斜槓劃掉", d: (c, o) => { medal("gold")(c, o); halo(c, o, (q) => { if (o.tiny) ln(q, OUT, 5.4, [[-8.6, 8.6], [8.6, -8.6]]); ln(q, "#ff4a5a", 3.4, [[-8.6, 8.6], [8.6, -8.6]]); }); } },
    // ---- 熔核、殼（灰燼之心一戰） ----
    molten_burst: { zh: "熔核爆裂", topic: "一顆橘紅熾熱的熔核（幾塊深色硬殼、殼縫透黃光）", d: core("lava") },
    heart_ember_burst: { zh: "殼縫熔核", topic: "同熔核，左上蓋著一片灰色的殼", d: (c, o) => { at(c, 1.4, 1.4, 0.86, (q) => core("lava")(q, o)); halo(c, o, (q) => { f(q, "#9a928a", () => { q.moveTo(-10.6, 3); q.bezierCurveTo(-11, -8, -4, -11, 4, -10); q.lineTo(2.6, -6.6); q.bezierCurveTo(-3, -7, -7, -4, -6.6, 3); q.closePath(); }); if (!o.tiny) f(q, "#d0c8bc", () => { q.moveTo(-9.4, -1); q.bezierCurveTo(-9.4, -6, -5.6, -8.6, -1, -9.2); q.lineTo(-1.4, -8); q.bezierCurveTo(-5, -7.4, -7.8, -5, -8, -1); q.closePath(); }); }); } },
    frost_ember_burst: { zh: "寒燼爆裂", topic: "一顆冰藍的寒燼核（深藍硬殼、殼縫透白光）", d: core("frost") },
    molten_shell: { zh: "熔殼", topic: "暗紅褐的龜殼形外殼（中間一塊六角殼片），殼片之間的縫透橘光", d: (c, o) => dome("#8a3a22", "#c46a42", "#ffb23a", 1.8, "#6a2a18")(c, o) },
    hard_shell: { zh: "硬殼", topic: "灰褐色的龜殼形硬殼（中間一塊六角殼片），殼片之間深色的縫", d: (c, o) => dome("#b0a084", "#e6dac2", "#5e4a3a", 1.6, "#8a7a62")(c, o) },
  };

  // =====================================================================
  // 118 個狀態的清單：src 寫明圖樣從哪裡來
  // =====================================================================
  const G = () => window.QPARTS_GLOSSARY?.statuses ?? [];
  const B4 = new Set(QP.list().status.map((e) => e.id));
  function entry(id) {
    if (B4.has(id)) { const e = QP.entry("status", id); return { zh: e.zh, topic: e.topic, src: "b4:status." + id, kind: "b4", d: e.d }; }
    const m = /^stance_(\w+)_([1-5])$/.exec(id);
    if (m && ELEMENTS.includes(m[1])) {
      if (m[1] === "holy" || m[1] === "shadow") { const e = QP.entry("status", "stance_" + m[1] + "_1"); return { zh: e.zh.replace("·壹", ""), topic: e.topic + "（各級同一個圖）", src: "b4:status.stance_" + m[1] + "_1", kind: "b4", d: e.d, level: Number(m[2]) }; }
      const E = EMBLEM[m[1]]; return { zh: m[1], topic: E.zh + "（各級同一個圖）", src: "new:emblem." + m[1], kind: "new", family: "element_stance", d: stancePlate(E.plate[0], E.plate[1], E.d), level: Number(m[2]) };
    }
    const n = NEW[id]; if (n) return { ...n, kind: n.src ? "borrow" : "new", src: n.src ?? "new" };
    return null;
  }
  /** 類別 → 框的底色（美術 PM 定：類別色畫在底色；硬控偏黃不偏褐、提亮後和圖樣再比一次亮度）。沒有類別的照現行的深底。 */
  const BASE_BG = "rgba(12,12,16,0.88)";
  const CLASS_BG = { hard: "#d4ac20", movement: "#2f78c8", mental: "#8a4ccc" };
  const CLASS_ZH = { hard: "硬控（暈眩、冰凍）", movement: "移動控制（緩速、定身）", mental: "心智控制（嘲諷、恐懼、沉默）" };
  const lookOf = (id) => G().find((s) => s.id === id)?.status_look ?? null;
  const polOf = (id) => { const p = lookOf(id)?.polarity; return p === "buff" || p === "debuff" ? p : "neutral"; };
  const clsOf = (id) => lookOf(id)?.control_group ?? null;
  const FRAME = { buff: "#3fbf6a", debuff: "#e04848", neutral: "#c8a048" };
  /** 框形照現行 framePath。 */
  function framePath(ctx, pol, r) { ctx.beginPath(); if (pol === "buff") ctx.arc(0, 0, r, 0, TAU); else if (pol === "debuff") ctx.roundRect(-r * 0.9, -r * 0.9, r * 1.8, r * 1.8, r * 0.35); else for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos((i / 6) * TAU + TAU / 12) * r, Math.sin((i / 6) * TAU + TAU / 12) * r); ctx.closePath(); }

  /** 圖樣本身（±10 單位）在框裡畫多大：框邊長的 GLYPH_K（現行圖樣是 ±10 單位 × size/26 × 0.95 ≈ 0.73）。 */
  const GLYPH_K = 0.74;
  /** 圖樣定義（給 QIcons.render）：畫在 48 格，±10 單位放大 1.8 倍。cpx＝圖樣本身顯示的 CSS px。 */
  function def(id, cpx) { const e = entry(id) ?? { d: (c, o) => QP.entry("status", id).d(c, o) }; return { d: (c, o) => { c.save(); c.translate(24, 24); c.scale(1.8, 1.8); e.d(c, { ...o, small: cpx <= 24, tiny: cpx <= 14 }); c.restore(); } }; }
  /** 只有圖樣的 canvas：≤14px 不包外框（規則 8）；opt.ow 指定外框（CSS px）。染類別底色的框裡給 1 個裝置像素的外框（見 paint）。 */
  const glyph = (id, cpx, res = 2, opt = {}) => Q.render(def(id, cpx), cpx * QP.BOX, res, { ow: opt.ow ?? (cpx <= 14 ? 0 : Q.outlinePx(cpx)) });
  /** 畫一個完整的狀態圖示（現行的框＋Q 版圖樣），中心 (cx,cy)、框邊長 size（ctx 的單位）；unitPx＝ctx 1 單位是幾個 CSS px，res＝每 CSS px 幾個裝置像素。
   *  opt.tint＝false 時不染類別底色（對照用）。 */
  /** 框線的內緣（CSS px，中心在原點）：圖樣要收在這裡面，不然會蓋掉框（極性的形狀）。size＝框邊長，線寬照現行 max(1.5, size×0.09)。 */
  function innerPath(pol, size) { const r = size / 2, lw = Math.max(1.5, size * 0.09), hw = lw / 2, p = new Path2D();
    if (pol === "buff") p.arc(0, 0, r - hw, 0, TAU); else if (pol === "debuff") p.roundRect(-r * 0.9 + hw, -r * 0.9 + hw, r * 1.8 - lw, r * 1.8 - lw, Math.max(0, r * 0.35 - hw));
    else { const R = (r * 0.866 - hw) / 0.866; for (let i = 0; i < 6; i++) p.lineTo(Math.cos((i / 6) * TAU + TAU / 12) * R, Math.sin((i / 6) * TAU + TAU / 12) * R); } p.closePath(); return p; }
  /** 框的內緣以內有多大（CSS px）：圓＝直徑、圓角方＝邊長、六角＝對邊距離。佔框比例（規則 7）的分母。 */
  const innerWidth = (pol, size) => { const r = size / 2, lw = Math.max(1.5, size * 0.09); return pol === "buff" ? 2 * r - lw : pol === "debuff" ? 1.8 * r - lw : 2 * r * 0.866 - lw; };
  const FIT_K = 6, maskMemo = new Map(), fitMemo = new Map();
  /** 框內緣的遮罩（FIT_K 倍解析度）。 */
  function maskOf(pol, size) { const key = pol + "|" + size.toFixed(2); if (!maskMemo.has(key)) { const M = Math.ceil(size * 1.6 * FIT_K), cv = Q.H.blank(M), x = cv.getContext("2d"); x.translate(M / 2, M / 2); x.scale(FIT_K, FIT_K); x.fillStyle = "#fff"; x.fill(innerPath(pol, size)); maskMemo.set(key, { M, d: x.getImageData(0, 0, M, M).data }); } return maskMemo.get(key); }
  /** 圖樣畫到框內緣以外的像素比例（k＝圖樣再縮放的倍率）。 */
  function outsideFrac(id, size, k = 1) { const { M, d: md } = maskOf(polOf(id), size), g = glyph(id, size * GLYPH_K * k, FIT_K, { ow: 0 }), S = g.width, d = g.getContext("2d").getImageData(0, 0, S, S).data, off = Math.round((M - S) / 2); let all = 0, out = 0;
    for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) { if (d[(y * S + x) * 4 + 3] < 128) continue; all++; const mx = x + off, my = y + off; if (mx < 0 || my < 0 || mx >= M || my >= M || md[(my * M + mx) * 4 + 3] < 128) out++; } return out / Math.max(1, all); }
  /** 圖樣收進框內緣的縮放（照圓章自動縮放的做法：從 1 往下，每次 0.02，直到畫到框外的像素 ≤0.5%；最小 0.7）。框邊長不同（狀態卡 16.8、頭頂 9）各算一次。 */
  function fitK(id, size) { const key = id + "|" + size.toFixed(2); if (!fitMemo.has(key)) { let k = 1; while (k > 0.7 && outsideFrac(id, size, k) > 0.005) k = Math.round((k - 0.02) * 100) / 100; fitMemo.set(key, k); } return fitMemo.get(key); }
  function paint(ctx, id, cx, cy, size, unitPx = 1, res = 2, opt = {}) {
    const pol = polOf(id), cls = opt.tint === false ? null : clsOf(id), r = size / 2;
    ctx.save(); ctx.translate(cx, cy); framePath(ctx, pol, r); ctx.fillStyle = BASE_BG; ctx.fill(); if (cls && CLASS_BG[cls]) { ctx.fillStyle = CLASS_BG[cls]; ctx.fill(); }
    ctx.lineWidth = Math.max(1.5, size * unitPx * 0.09) / unitPx; ctx.strokeStyle = FRAME[pol]; ctx.stroke(); ctx.restore();
    const cpx = size * unitPx * GLYPH_K * fitK(id, size * unitPx), g = glyph(id, cpx, res, cls ? { ow: 1 / res } : {}), a = cpx * QP.BOX / unitPx;
    QW.blit(ctx, g, cx - a / 2, cy - a / 2, a, unitPx * res);
  }
  /** 戰場頭頂（現行 statusIconCanvas）：px 邊長的 canvas，框邊長 px−2。 */
  function headCanvas(id, px, zoom = 1, opt = {}) { const res = opt.res ?? (zoom === 1 ? 2 : zoom), cv = Q.H.blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d"); x.scale(res, res); paint(x, id, px / 2, px / 2, px - 2, 1, res, opt); return cv; }
  /** 狀態卡（現行 statusIconTile＋tileCanvas）：100 單位的方塊、裁成半徑 49 的圓，框畫在 50,50、邊長 84。 */
  function cardCanvas(id, px, zoom = 1, opt = {}) { const res = opt.res ?? (zoom === 1 ? 2 : zoom), cv = Q.H.blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d"); x.scale((px * res) / 100, (px * res) / 100); x.beginPath(); x.arc(50, 50, 49, 0, TAU); x.clip(); paint(x, id, 50, 50, 84, px / 100, res, opt); return cv; }
  /** 全部狀態（名詞表的順序）。 */
  const list = () => G().map((s) => { const e = entry(s.id); return { id: s.id, zh: s.name_zh, pol: polOf(s.id), cls: clsOf(s.id), dot: s.status_look?.dot_element ?? null, kind: e?.kind ?? "missing", src: e?.src ?? "-", topic: e?.topic ?? "（沒有圖樣）", family: e?.family ?? null, level: e?.level ?? null }; });
  return { NEW, EMBLEM, ELEMENTS, CLASS_BG, CLASS_ZH, BASE_BG, FRAME, GLYPH_K, CARD_FRAME: 16.8, HEAD_FRAME: 9, entry, def, glyph, paint, headCanvas, cardCanvas, list, polOf, clsOf, framePath, innerPath, innerWidth, outsideFrac, fitK };
})();
