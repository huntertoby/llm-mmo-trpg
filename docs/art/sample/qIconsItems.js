// qIconsItems.js：「小圖示改 Q 版」全量重畫第⑥批——物品（背包裡不是裝備的東西：消耗品、補給、材料、染料；拿到物品飛進背包的通用圖示）。畫圖 agent 2026-11-12。
// 規則：docs/art/Q版小圖示樣張.md 第 2 節；紀錄：docs/art/Q版小圖示-第6批物品.md；樣張頁：q-icons-items.html。
// 清單以遊戲端為準：content/world/items.yaml（ItemKind＝consumable｜material｜dye｜supply，35 個）＋ client/src/world/GainEffects.tsx 的 GainIcon（通用 2 個）。
// 遊戲端目前沒有物品圖示：背包格畫「名字小牌」（bagGrid.ts 的 tileLines、world-economy.css 的 .world-bag-tile），商店、戰利品、腰包是文字列，信件附件是「名稱＋個數」小牌，
// 拿到物品飛進背包用 GainIcon（劍／布袋）。樣張端有一份墨線的 itemIcons.js（42 個，沒移植），只當參考；它的類別底色與品質框（ItemIcons.CAT、TIER）是這批的框，
// 風格樣張 qIcons.js 已經照它畫過（第 2 版過審）。第 2 版（美術 PM 決定 1）：底色照 ItemIcons.CAT，框線色改成材料＝GEAR_RARITY 的 common／rare／epic、其他＝中性 #8a6a3a（bagFrame、rimOf）；飛進背包一律深底圓金邊（frameOf）。
// 和前幾批同題材的一律直接呼叫（src 欄）：風格樣張 ART.item 的小回復藥、回魔藥、火瓶、精料；第 7 批 HUD「補給」麵包；第 4 批徽章「打擊」斜劍（通用：裝備）。
// 依賴（先載入）：qIcons.js、qIconsWeapons.js、qIconsSkills.js、qIconsParts.js、qIconsStatus.js、qIconsHud.js；框用 itemIcons.js（現行樣張，只讀）。
window.QIconsItems = (() => {
  const Q = window.QIcons, QW = window.QIconsWeapons, QP = window.QIconsParts, QH = window.QIconsHud;
  const { mix, f, rr, ci, el, poly, ln, starPts, glow, flame, drop, sparkle, halo, blank } = Q.H, TAU = Math.PI * 2, PI = Math.PI, OUT = Q.OUT, HI2 = Q.H.HI2;
  const at = (c, x, y, k, fn, rot = 0) => { c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k); fn(c); c.restore(); };
  const st = (c, col, w, fn) => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = "round"; c.lineJoin = "round"; c.stroke(); };
  const clip = (c, path, fn) => { c.save(); c.beginPath(); path(c); c.clip(); fn(c); c.restore(); };
  /** ±10 單位的圖樣（第 4 批）放進 48 格（和第 4 批 def() 同一個倍率 1.8×k）。 */
  const b10 = (fn, k = 1, dx = 0, dy = 0) => (c, o) => at(c, 24 + dx, 24 + dy, 1.8 * k, (q) => fn(q, o));
  const GLASS = "#dcebf0";
  /** 沿用前批的圖、原樣貼邊時整個縮一點收進格內（同第 4 批 fit()）：以 (24,25) 為中心縮 k。 */
  const fitIn = (k, fn) => (c, o) => at(c, 24, 25, k, (q) => { q.translate(-24, -25); fn(q, o); });
  /** 葉片：基部在原點、尖端在 (0,−len)，最寬 w；左半亮一階、右半暗一階，中脈（≥24px）。 */
  const leafPath = (q, len, w) => { q.beginPath(); q.moveTo(0, 0); q.bezierCurveTo(-w * 1.25, -len * 0.3, -w * 0.9, -len * 0.78, 0, -len); q.bezierCurveTo(w * 0.9, -len * 0.78, w * 1.25, -len * 0.3, 0, 0); q.closePath(); };
  const leaf = (c, o, len, w, col, lite, dark, vein) => { leafPath(c, len, w); c.fillStyle = col; c.fill(); clip(c, (q) => leafPath(q, len, w), (q) => { f(q, dark, () => q.rect(0.4, -len, w * 2, len)); f(q, lite, () => q.rect(-w * 0.62, -len * 0.82, w * 0.3, len * 0.5)); }); if (!o.small) ln(c, vein, 1.3, [[0, -1.5], [0, -len * 0.82]]); };
  /** 晶柱：底在原點、尖在 (0,−h)、半寬 w；左面亮、右面暗，頂端一道亮邊。 */
  const prism = (c, h, w, col, lite, dark) => { const P = [[-w, 0], [-w, -h * 0.72], [0, -h], [w, -h * 0.72], [w, 0]]; poly(c, col, P, 0.6); poly(c, lite, [[-w, 0], [-w, -h * 0.72], [0, -h], [0, 0]]); poly(c, dark, [[w * 0.45, 0], [w * 0.45, -h * 0.78], [w, -h * 0.72], [w, 0]]); };
  /** 雲團（三顆圓＋平底）。 */
  const cloud = (c, col, x, y, k) => at(c, x, y, k, (q) => f(q, col, () => { q.arc(-7, 0, 5.4, PI * 0.5, PI * 1.5); q.arc(-1.5, -4, 6.6, PI, PI * 1.85); q.arc(6, -0.6, 5, PI * 1.3, PI * 0.5); q.closePath(); }));

  // ---------------- 藥與草 ----------------
  /** 中回復藥：比小回復藥大一號的圓肚瓶，長瓶頸、金色頸環、深紅藥水、大白十字，瓶塞上一滴紅封蠟。和小回復藥同家族：靠大小、金頸環、深一階的紅分。 */
  const hpMediumArt = (c, o) => { c.save(); c.translate(24, 24); c.scale(0.9, 0.9); c.translate(-24, -24.1);
    rr(c, GLASS, 19.4, 7.4, 9.2, 12, 1.6); rr(c, "#a06a36", 17.6, 2.6, 12.8, 6.4, 2.4); el(c, "#c8202a", 27.6, 5.2, 2.6, 3.2, 0.3);
    ci(c, GLASS, 24, 30.4, 15.2); liquid(c, (x) => x.arc(24, 30.4, 13, 0, TAU), "#c8202a", 22.4, "#f07a70");
    rr(c, "#d8b04a", 17.2, 15.2, 13.6, 3.8, 1.8); if (!o.small) f(c, "#f6d878", () => c.rect(18.6, 15.8, 6, 1.2));
    rr(c, "#ffffff", 21.8, 24.6, 4.4, 13.4, 1.2); rr(c, "#ffffff", 17.4, 29.2, 13.2, 4.4, 1.2); el(c, HI2, 15.6, 24, 1.9, 4.2, 0.5); c.restore();
  };
  const liquid = (c, clipPath, col, top, surf) => clip(c, clipPath, (q) => { f(q, col, () => q.rect(0, top, 48, 48)); f(q, surf, () => q.rect(0, top, 48, 2)); });
  /** 解毒草：三片長葉子扇形攤開（中間最長），葉柄束在一起、綁一圈紅繩；葉子左半亮、右半暗、中脈。 */
  const herbArt = (c, o) => {
    for (const [r, len, w] of [[-0.62, 27, 6.6], [0.62, 27, 6.6], [0, 33, 7.4]]) at(c, 24, 38, 1, (q) => leaf(q, o, len, w, "#62b444", "#a8e078", "#3f8a2e", "#2f6a22"), r);
    rr(c, "#6a8a3a", 20.6, 35, 6.8, 9.6, 2.4); rr(c, "#d04a34", 18.6, 35.6, 10.8, 4.2, 1.8); if (!o.small) f(c, "#f08a70", () => c.rect(19.8, 36.2, 4.4, 1.1));
  };

  // ---------------- 投擲瓶（瓶形各不同：規則 11；照 items.yaml 的敘述：水、油是陶瓶，霧瓶是修士煉的，冰瓶是瓷瓶，火瓶是塞布條的火油瓶） ----------------
  /** 水瓶：赭紅陶罐（圓肚、細頸、外撇的口、右邊一個把手），肚上一道藍色水紋，罐口湧出一團藍水、旁邊一顆水滴。 */
  const waterArt = (c, o) => {
    st(c, "#a85e34", 3.4, (q) => { q.moveTo(31.4, 17); q.bezierCurveTo(40, 16.4, 41, 28, 33.6, 30.4); });
    rr(c, "#c8834e", 17.4, 11.6, 11.2, 10, 2); rr(c, "#d8956a", 14.6, 9, 16.8, 4.6, 2.2);
    ci(c, "#c8834e", 23, 31.4, 13.2); clip(c, (q) => q.arc(23, 31.4, 13.2, 0, TAU), (q) => { f(q, "#9a5a32", () => q.rect(26.6, 14, 14, 34)); f(q, "#4aa8ff", () => { q.moveTo(8, 30); q.quadraticCurveTo(14, 26.4, 19, 30); q.quadraticCurveTo(24, 33.6, 29, 30); q.quadraticCurveTo(34, 26.4, 40, 30); q.lineTo(40, 34.6); q.quadraticCurveTo(34, 31, 29, 34.6); q.quadraticCurveTo(24, 38.2, 19, 34.6); q.quadraticCurveTo(14, 31, 8, 34.6); q.closePath(); }); });
    el(c, "#f0b88a", 16.4, 25, 2, 4, 0.5);
    el(c, "#4aa8ff", 23, 8.4, 7.6, 3.6); el(c, "#9ad0ff", 21, 7.4, 3.6, 1.5); drop(c, "#4aa8ff", 35.6, 6.6, 0.42); if (!o.small) el(c, "#ffffff", 34.6, 7.4, 0.8, 1.4);
  };
  /** 油瓶：黃釉的陶油壺（圓肚、短頸、木塞，右邊一支往上翹的壺嘴），壺嘴尖端用一條細油線垂著一滴琥珀色的淚滴形燈油（上尖下圓、左上一點白亮面）。
   *  第 1 次試做是沒有壺嘴的矮胖褐陶罐加一道油痕：24 讀成布袋、洋蔥，加壺嘴、換黃釉才是「裝油的壺」。
   *  第 2 版：油滴原本是一顆深褐圓點，24 讀成一顆黑球（像茶壺），改琥珀色淚滴＋亮點、和壺嘴連一條細線（審查可修 1）。 */
  const oilArt = (c, o) => { c.save(); c.translate(-1.4, 0.6);
    st(c, "#c89a50", 5.4, (q) => { q.moveTo(31, 27); q.quadraticCurveTo(38, 25.6, 41.4, 17.6); });
    rr(c, "#a06a36", 15.6, 7, 10.8, 6.6, 2.2); rr(c, "#d8b06a", 16.4, 12, 9.2, 7.6, 1.6);
    el(c, "#d8b06a", 21, 31.4, 15.4, 12.8); clip(c, (q) => q.ellipse(21, 31.4, 15.4, 12.8, 0, 0, TAU), (q) => { f(q, "#a8783a", () => { q.moveTo(48, 22); q.lineTo(48, 48); q.lineTo(10, 48); q.quadraticCurveTo(32, 42, 34, 22); q.closePath(); }); f(q, "#f0d090", () => q.rect(0, 19, 48, 2.6)); });
    el(c, "#fff0c8", 11.6, 27, 2, 3.8, 0.5);
    ln(c, "#d8a040", o.small ? 1.8 : 1.3, [[41.4, 18.4], [41.4, 23]]); drop(c, "#d8a040", 41.4, 28.4, 0.66);
    f(c, "#a86a1e", () => { c.moveTo(45.4, 29.6); c.bezierCurveTo(45.4, 33.4, 43, 35, 41.4, 35); c.lineTo(41.4, 33.4); c.bezierCurveTo(43, 33.2, 44.4, 32, 45.4, 29.6); c.closePath(); });
    el(c, "#ffffff", 39.8, 29.4, 0.95, 1.7, 0.3); c.restore();
  };
  /** 霧瓶：淡青瓷色的葫蘆（上小下大、腰間一圈紅繩、木塞），右上冒出一縷白霧往右上飄（霧放在旁邊，不壓在瓶口上：壓在瓶口像蘑菇，2.11）。 */
  const mistArt = (c, o) => {
    rr(c, "#a06a36", 15.2, 6.6, 7.6, 6, 2);
    ci(c, "#b8d4cc", 19, 16.6, 7.6); ci(c, "#b8d4cc", 20.6, 32.6, 12.4);
    clip(c, (q) => { q.arc(19, 16.6, 7.6, 0, TAU); q.moveTo(33, 32.6); q.arc(20.6, 32.6, 12.4, 0, TAU); }, (q) => { f(q, "#88aca2", () => { q.rect(24, 6, 12, 18); q.rect(26.6, 20, 12, 28); }); });
    el(c, "#e8f6f0", 14.4, 28, 2, 4.2, 0.4); el(c, "#e8f6f0", 16, 14, 1.4, 2.4, 0.4);
    rr(c, "#c84030", 13, 22.4, 12.8, 3.6, 1.6);
    cloud(c, "#eef2f4", 33.4, 13.6, 1.02); cloud(c, "#ffffff", 32, 12.6, 0.52); if (!o.small) cloud(c, "#dfe6ea", 39.6, 24, 0.5);
  };
  /** 冰瓶：白瓷梅瓶（寬肩、往下收窄），肩上一道青花藍紋，瓶口長出三根淡青冰柱、一顆白色四芒星閃光。 */
  const frostArt = (c, o) => { c.save(); c.translate(24, 25); c.scale(0.9, 0.9); c.translate(-24, -22.6);
    for (const [x, h, w, r] of [[19.4, 10, 2.6, -0.42], [24, 13, 3.2, 0], [28.6, 10, 2.6, 0.42]]) at(c, x, 12.4, 1, (q) => prism(q, h, w, "#8fe3ff", "#d8f6ff", "#5ab8e0"), r);
    rr(c, "#e8eef4", 19, 11, 10, 6, 2);
    const V = (q) => { q.moveTo(19.6, 15.4); q.bezierCurveTo(8, 17, 8.6, 27, 13.4, 34); q.quadraticCurveTo(16.4, 39, 17.4, 44); q.lineTo(30.6, 44); q.quadraticCurveTo(31.6, 39, 34.6, 34); q.bezierCurveTo(39.4, 27, 40, 17, 28.4, 15.4); q.closePath(); };
    f(c, "#eef4f8", V); clip(c, V, (q) => { f(q, "#c2ccd8", () => q.rect(30, 14, 12, 32)); f(q, "#3a68c0", () => q.rect(0, 22, 48, 4.6)); if (!o.small) f(q, "#3a68c0", () => q.rect(0, 38.6, 48, 1.8)); f(q, "#9ab8ee", () => q.rect(0, 22.8, 48, 1.1)); });
    el(c, "#ffffff", 14.6, 29.6, 1.6, 4, 0.3);
    sparkle(c, "#ffffff", 37.4, 9.6, 4.6); c.restore();
  };

  // ---------------- 材料 ----------------
  /** 粗料：兩塊疊著的灰色粗石塊（前面一塊大、後面一塊小、都是不規則的多邊形，上面一面亮、右面暗），前面那塊一道深色裂紋。沒有晶面、沒有亮晶——和精料（藍灰切面＋亮晶）、上料（長出紫晶）先分剪影。
   *  第 1 次試做是一顆圓石加幾個小坑：24 讀成月亮、餅乾，改成有稜角的兩塊碎石。 */
  const rock = (c, P, top, side, col, lite, dark) => { poly(c, col, P, 1.2); poly(c, lite, top); poly(c, dark, side); };
  const coarseArt = (c, o) => {
    halo(c, o, (x) => rock(x, [[26, 17.6], [31.6, 9.6], [40.6, 10.6], [43.4, 19.6], [38.6, 25], [28.6, 24]], [[26, 17.6], [31.6, 9.6], [40.6, 10.6], [36, 16.6]], [[36, 16.6], [40.6, 10.6], [43.4, 19.6], [38.6, 25]], "#9a9a94", "#c4c4bc", "#70706c"));
    halo(c, o, (x) => rock(x, [[5.4, 33], [9.6, 20.6], [20.4, 15.6], [31.4, 19.4], [36.4, 30.4], [31, 41.6], [13, 42.4]], [[9.6, 20.6], [20.4, 15.6], [31.4, 19.4], [21.6, 25.4]], [[21.6, 25.4], [31.4, 19.4], [36.4, 30.4], [31, 41.6], [24.6, 35]], "#a4a49e", "#cacac2", "#76766f"));
    ln(c, "#55554f", o.small ? 1.8 : 1.4, [[13.6, 29], [18.4, 31.4], [17, 36.6]]);
    if (!o.small) for (const [x, y] of [[26.6, 30.4], [12, 37]]) ci(c, "#86867e", x, y, 1.1);
  };
  /** 上料：紫灰色的礦石底座，上面長出一叢三根發光的紫晶（中間最高），晶柱左面亮、右面暗。 */
  const superiorArt = (c, o) => {
    poly(c, "#8a7aa8", [[7.6, 38], [11, 30.4], [20, 27.4], [31, 28], [39.4, 31.4], [41.4, 38.4], [34, 43.6], [14, 43.6]], 1.4);
    poly(c, "#ac9ccc", [[11, 30.4], [20, 27.4], [31, 28], [26, 33], [13, 34]]); poly(c, "#6a5a88", [[31, 28], [39.4, 31.4], [41.4, 38.4], [34, 43.6], [29, 38]]);
    for (const [x, h, w, r] of [[16, 19, 4.4, -0.36], [32, 18, 4.4, 0.36], [24, 26, 5.4, 0]]) at(c, x, 32, 1, (q) => prism(q, h, w, "#b89cff", "#e4d8ff", "#8a6ae0"), r);
  };
  /** 霧晶：三根淡灰白的晶柱（中間最高、左右斜開），晶柱腳下橫著一條扁的雲帶（上緣一排圓鼓、平底、往左右伸出晶柱外），雲帶自己包一圈外框、和晶柱分開。
   *  第 2 版：第 1 版是一條圓角白霧帶，真 1 倍和晶柱底連成一塊白、看不出是霧（審查可修 2）；改成伸出晶柱外的扁雲帶，剪影多一條橫帶，也和上料、硫磺的晶叢拉開。 */
  const fogBand = (q) => { q.moveTo(3.4, 42.6); q.arc(7.4, 38.8, 4, PI * 0.8, PI * 1.6); q.arc(14.6, 36, 5, PI * 1.15, PI * 1.85); q.arc(24, 35.4, 5.4, PI * 1.12, PI * 1.88); q.arc(33.4, 36, 5, PI * 1.15, PI * 1.85); q.arc(40.6, 38.8, 4, PI * 1.4, PI * 0.2); q.lineTo(43.4, 42.6); q.closePath(); };
  const mistCrystalArt = (c, o) => {
    for (const [x, h, w, r] of [[15.4, 20, 4.6, -0.42], [32.6, 18, 4.6, 0.42], [24, 29, 5.8, 0]]) at(c, x, 36, 1, (q) => prism(q, h, w, "#d8e2e6", "#ffffff", "#a8b8c0"), r);
    halo(c, o, (x) => { f(x, "#e6eef2", fogBand); clip(x, fogBand, (q) => { f(q, "#b4c4cc", () => q.rect(0, 40.4, 48, 4)); el(q, "#ffffff", 13.2, 33.6, 3.2, 1.4, -0.35); el(q, "#ffffff", 22.6, 32.8, 3.4, 1.4, 0); }); if (!o.small) f(x, "#c4d2d8", () => x.rect(19, 38.2, 12, 1)); });
  };
  /** 雲頂霧晶（稀有）：一大根發光的淡青晶石立在一朵白雲上（兩旁兩根小的），雲的平底。和霧晶分剪影：雲團底＋一根獨大。 */
  const summitArt = (c, o) => { c.save(); c.translate(24, 23.4); c.scale(0.84, 0.84); c.translate(-24, -24);
    for (const [x, h, w, r] of [[14.6, 14, 3.8, -0.5], [33.4, 14, 3.8, 0.5]]) at(c, x, 31.6, 1, (q) => prism(q, h, w, "#9adcf4", "#e0f8ff", "#5aaed0"), r);
    at(c, 24, 32, 1, (q) => prism(q, 29, 6.6, "#a8e8ff", "#f0fcff", "#62b8dc"));
    cloud(c, "#ffffff", 24.4, 40.6, 1.72); f(c, "#d6e4ec", () => c.rect(8, 40.2, 32, 3.4)); if (!o.small) cloud(c, "#ffffff", 21, 35.6, 0.6); c.restore();
  };
  /** 符紙灰：一堆灰色的灰燼（圓丘、左上亮），斜插一張燒了一半的黃符紙（紅色符文、下緣焦黑），旁邊一顆橘色火星。 */
  const ashArt = (c, o) => {
    at(c, 27.6, 20, 1, (q) => { poly(q, "#f0d050", [[-6.6, -13], [6.6, -13], [6.6, 12], [-6.6, 12]], 0.6); f(q, "#c89a20", () => q.rect(2.6, -13, 4, 25)); st(q, "#c0302a", 2.2, (p) => { p.moveTo(-0.6, -9.4); p.lineTo(1.6, -5.4); p.lineTo(-1.6, -1.4); p.lineTo(1.4, 3); }); if (!o.small) rr(q, "#c0302a", -3.4, -11, 6.4, 1.6, 0.6); f(q, "#3a2a20", () => { q.moveTo(-6.6, 6); q.lineTo(-3, 8.4); q.lineTo(0, 5.6); q.lineTo(3.4, 8.6); q.lineTo(6.6, 6.4); q.lineTo(6.6, 12); q.lineTo(-6.6, 12); q.closePath(); }); }, 0.34);
    f(c, "#a8a49e", () => { c.moveTo(5, 42.6); c.bezierCurveTo(8, 30, 17, 26.6, 24, 26.6); c.bezierCurveTo(31, 26.6, 40, 30, 43, 42.6); c.closePath(); });
    f(c, "#cfcac2", () => { c.moveTo(9.4, 36); c.bezierCurveTo(12, 30.6, 17, 28.8, 22, 28.6); c.lineTo(21, 31.4); c.bezierCurveTo(16.4, 31.6, 13, 33.4, 11, 37); c.closePath(); });
    f(c, "#86827c", () => { c.moveTo(43, 42.6); c.bezierCurveTo(41, 35, 36.4, 31, 32, 29.4); c.quadraticCurveTo(35, 36, 34, 42.6); c.closePath(); });
    if (!o.small) for (const [x, y] of [[17, 37], [27, 35], [22, 40]]) ci(c, "#8a8680", x, y, 1);
    ci(c, "#ff8a2a", 38.6, 22.4, 2.4); ci(c, "#ffe08a", 38.2, 22, 1.1);
  };
  /** 丹砂：淺白瓷的淺碟，碟裡一堆朱紅色的丹砂粉（圓丘、左上亮），上面兩顆朱紅小晶塊。 */
  const cinnabarArt = (c, o) => {
    f(c, "#c84030", () => { c.moveTo(9, 33); c.bezierCurveTo(12, 21, 19, 17.6, 24, 17.6); c.bezierCurveTo(29, 17.6, 36, 21, 39, 33); c.closePath(); });
    f(c, "#f07058", () => { c.moveTo(12.4, 29); c.bezierCurveTo(14.6, 22.6, 18.6, 20, 22.6, 19.8); c.lineTo(22, 22.6); c.bezierCurveTo(18.6, 23, 16, 25.4, 14.6, 30); c.closePath(); });
    f(c, "#962a20", () => { c.moveTo(39, 33); c.bezierCurveTo(37, 26, 33.4, 21.6, 30, 20.4); c.quadraticCurveTo(32.6, 27, 31.6, 33); c.closePath(); });
    poly(c, "#e04a36", [[19, 17.4], [22.4, 12.6], [26, 14.4], [24.6, 19]], 0.5); poly(c, "#ff9a80", [[19, 17.4], [22.4, 12.6], [23.2, 15.4]]);
    if (!o.small) { poly(c, "#e04a36", [[29.6, 22], [32.6, 19], [34.6, 22.4], [32, 24.6]], 0.4); for (const [x, y] of [[17, 27], [26, 25], [30, 29], [21, 30.6]]) ci(c, "#ffb0a0", x, y, 0.8); }
    f(c, "#e8e4da", () => { c.moveTo(4, 31); c.lineTo(44, 31); c.bezierCurveTo(42, 39, 35, 42.6, 24, 42.6); c.bezierCurveTo(13, 42.6, 6, 39, 4, 31); c.closePath(); });
    f(c, "#bcb6a8", () => { c.moveTo(44, 31); c.bezierCurveTo(42, 39, 35, 42.6, 24, 42.6); c.lineTo(24, 39.6); c.bezierCurveTo(33, 39.6, 39, 37, 41, 31); c.closePath(); });
    rr(c, "#ffffff", 4, 30, 40, 2.4, 1.2); if (!o.small) rr(c, "#4a78c0", 8.6, 34.4, 30.8, 1.6, 0.8);
  };
  /** 狼牙：一顆彎的大獸牙（象牙白、右緣暗一階、尖端朝右下），牙根綁一圈褐皮繩、繩結垂下一小段。 */
  const fangArt = (c, o) => at(c, 24, 24, 1, (q) => {
    const F = (p) => { p.moveTo(-8.4, -15.6); p.lineTo(5, -17.2); p.bezierCurveTo(9.6, -6, 8, 8, -2, 19.4); p.bezierCurveTo(-1.4, 8, -4.4, -3, -8.4, -15.6); p.closePath(); };
    f(q, "#f2ecd8", F); clip(q, F, (p) => { f(p, "#c8bc9c", () => { p.moveTo(3.6, -18); p.bezierCurveTo(9, -6, 7, 8, -2.4, 19.6); p.lineTo(10, 20); p.lineTo(10, -18); p.closePath(); }); f(p, "#ffffff", () => { p.moveTo(-6.4, -12); p.bezierCurveTo(-3.4, -3, -2, 4, -2, 9); p.lineTo(-3.6, 8.4); p.bezierCurveTo(-4, 3, -5.6, -4, -7.8, -11.4); p.closePath(); }); });
    rr(q, "#7a4a28", -10, -19.4, 17.4, 5.6, 2.4); if (!o.small) f(q, "#a8743e", () => q.rect(-8.6, -18.6, 8, 1.4));
    ln(q, "#7a4a28", 2.6, [[-9.4, -15.4], [-14, -9.6]]);
  }, -0.32);
  /** 雷羽：一根淡紫白的大羽毛斜放（羽根在左下、羽尖在右上；右半暗一階、羽軸深紫），右下一道黃色閃電劈過羽毛旁邊。 */
  const featherP = (q) => { q.beginPath(); q.moveTo(0, 16); q.bezierCurveTo(-9.6, 6, -9.4, -13, 0, -23); q.bezierCurveTo(9.4, -13, 9.6, 6, 0, 16); q.closePath(); };
  const thunderArt = (c, o) => {
    at(c, 22.6, 24.6, 1, (q) => {
      featherP(q); q.fillStyle = "#e0d8ff"; q.fill(); clip(q, featherP, (p) => { f(p, "#a898e0", () => p.rect(0.6, -25, 11, 42)); f(p, "#ffffff", () => p.rect(-5.4, -14, 2.2, 16)); f(p, OUT, () => { p.moveTo(-10, 4); p.lineTo(-3.6, 1.6); p.lineTo(-10, 0.4); p.closePath(); }); });
      ln(q, "#6a58b8", o.small ? 2.4 : 1.8, [[0, 22.4], [0, -17]]);
    }, PI / 4);
    halo(c, o, (x) => poly(x, "#ffe14a", [[34.6, 24.4], [29.2, 34.4], [33.4, 34.6], [29.6, 44.4], [40.4, 31.2], [36, 31.2], [39.6, 24.4]], 0.4));
  };
  /** 餘燼羽：一根往右彎的橘紅羽毛（羽根在左下、羽尖在右上；右半暗一階、羽軸深紅褐），羽片外緣一圈透亮的黃橘（還透著火光），羽尖一小朵火，旁邊兩顆火星。
   *  和雷羽分剪影：彎的羽毛＋羽尖的火 vs 直的羽毛＋旁邊的閃電。第 1 次試做照 items.yaml「火塵蝠翅膜」畫成三根指骨撐開的膜：24 讀成橘色的旗子、窗簾，改回羽毛。 */
  /*  第 2 版（審查必修 2）：第 1 版深紅褐的主脈＋外緣細鋸齒＝葉子的畫法，24 讀成秋葉。照雷羽的結構改：淺色羽軸（亮黃橘）從羽片下端伸出一截光羽根、
   *  外緣切兩道 V 形缺口（羽支分岔）、拿掉鋸齒感的內層、本色提亮到火色。雷羽與餘燼羽成為「同一個羽毛結構、不同顏色與記號（閃電 vs 火）」。 */
  const curvedP = (q) => { q.beginPath(); q.moveTo(0, 15); q.bezierCurveTo(-11, 8, -10, -12, 3, -22); q.bezierCurveTo(9.4, -10, 9, 6, 0, 15); q.closePath(); };
  const emberArt = (c, o) => {
    at(c, 22, 25, 1, (q) => {
      curvedP(q); q.fillStyle = "#ff6a1a"; q.fill();
      clip(q, curvedP, (p) => {
        f(p, "#c8461a", () => { p.moveTo(1.4, -24); p.quadraticCurveTo(-0.6, 0, 1.2, 18); p.lineTo(14, 18); p.lineTo(14, -24); p.closePath(); });
        st(p, "#ffb040", 2.4, (s) => { s.moveTo(-1, 15.6); s.bezierCurveTo(-12, 8, -11, -12, 2.6, -23); });
        f(p, "#ffa060", () => p.rect(-6, -12, 2.2, 13));
        f(p, OUT, () => { p.moveTo(-11, 6.4); p.lineTo(-3.4, 2.2); p.lineTo(-11, -0.6); p.closePath(); });
        f(p, OUT, () => { p.moveTo(12, -5); p.lineTo(3.6, -7); p.lineTo(12, -12.4); p.closePath(); });
      });
      st(q, "#ffd23f", o.small ? 2.4 : 1.8, (p) => { p.moveTo(0, 21); p.quadraticCurveTo(-1.6, 0, 2.4, -17); });
    }, PI / 4);
    flame(c, "#ffd23f", 38.4, 9, 0.5); flame(c, "#ffffff", 38.4, 10.6, 0.22);
    ci(c, "#ffd23f", 31.4, 6, 1.7); if (!o.small) ci(c, "#ffb23a", 42.6, 19.4, 1.4);
  };
  /** 活血骨：一根斜放的骨頭（兩端各兩顆圓節），骨上一道紅色的血脈，骨頭中間一顆跳動的紅色血珠（外圍紅光）。 */
  const boneArt = (c, o) => at(c, 24, 24, 1, (q) => {
    rr(q, "#ece2c6", -3.8, -15, 7.6, 30, 2.2);
    for (const s of [-1, 1]) for (const dx of [-3.8, 3.8]) ci(q, "#ece2c6", dx, s * 16.6, 4.8);
    f(q, "#c8b890", () => q.rect(1.2, -14, 2.6, 28)); for (const s of [-1, 1]) ci(q, "#ffffff", -5, s * 16.6 - 1.4, 1.5);
    st(q, "#c8202a", 2, (p) => { p.moveTo(-1.6, -12.6); p.quadraticCurveTo(1.6, -6, -1, -1.4); p.quadraticCurveTo(-2.6, 5, 0.6, 12.6); });
    halo(q, o, (x) => { ci(x, "#e0282e", 4.6, 2, 4.8); el(x, "#ff8a8a", 3.2, 0.4, 1.6, 1.1, -0.6); });
  }, PI / 4);
  /** 青竹節：一段斜放的青竹（兩個竹節、節上一道深綠環），上端切口露出淺黃的竹肉圈，節上長出一片竹葉。 */
  const bambooArt = (c, o) => {
    at(c, 21.4, 25, 1, (q) => {
      rr(q, "#5aa83c", -6, -19, 12, 37, 2.4); f(q, "#3f8a2e", () => q.rect(2.6, -19, 3.4, 37)); f(q, "#a8e078", () => q.rect(-4.4, -15, 2, 30));
      for (const y of [-4, 11]) { rr(q, "#2f6a22", -6.8, y - 1.6, 13.6, 3.2, 1.4); if (!o.small) f(q, "#8ccc5a", () => q.rect(-5.6, y - 2.6, 9, 1)); }
      el(q, "#e8e0a8", 0, -19, 6, 2.6); el(q, "#c8b878", 0, -19, 3.4, 1.2);
    }, 0.62);
    at(c, 24, 29.6, 1, (q) => leaf(q, o, 15, 4.4, "#7cc850", "#c0f090", "#4f9a36", "#2f6a22"), 2.1); /* 葉柄接在下面那個竹節上（第 1 次試做浮在旁邊） */
  };
  /** 精華：一顆淡金色的菱形結晶（四個切面：左上兩面亮、右下兩面暗），外圍金色光暈，旁邊兩顆白色四芒星閃光。 */
  const essenceArt = (c, o) => {
    const T = [24, 6], R = [37, 24], B = [24, 43], L = [11, 24], C = [24, 24];
    poly(c, "#f6d878", [T, R, B, L], 0.8); poly(c, "#fff6d0", [T, C, L]); poly(c, "#fbe8a0", [T, R, C]); poly(c, "#d8b04a", [C, R, B]); poly(c, "#e8c460", [L, C, B]);
    el(c, "#ffffff", 18.6, 17, 1.6, 3.4, 0.7);
    sparkle(c, "#ffffff", 38.6, 10, 4.6); if (!o.small) sparkle(c, "#fff6c8", 9.4, 37, 3.2);
  };
  /** 熔岩核：一顆圓的灰褐熔岩石（左上亮、右下暗），表面三道發亮的橘黃裂縫，外圍橘色光暈。 */
  const lavaArt = (c, o) => { c.save(); c.translate(24, 25); c.scale(1.1, 1.1); c.translate(-24, -25);
    ci(c, "#7c645a", 24, 25, 18.4); clip(c, (q) => q.arc(24, 25, 18.4, 0, TAU), (q) => { f(q, "#5a463e", () => { q.arc(24, 25, 16.4, -PI * 0.15, PI * 0.8); q.arc(20, 21, 16.4, PI * 0.8, -PI * 0.15, true); q.closePath(); }); f(q, "#a88a7c", () => { q.arc(24, 25, 16.4, PI * 1.05, PI * 1.5); q.arc(26, 27.4, 15, PI * 1.5, PI * 1.05, true); q.closePath(); }); });
    for (const [pts, w] of [[[[13, 21], [19.6, 25.6], [17.6, 32.4]], 3.4], [[[27.4, 12.4], [25.4, 21.4], [32.4, 26], [36.6, 24]], 3.4], [[[22, 30], [27, 35.4], [25, 39]], 2.8]]) { ln(c, "#ff7a1a", w, pts); ln(c, "#ffe06a", w * 0.42, pts); } c.restore();
  };
  /** 焦鐵：三片疊在一起、扇形攤開的鐵札甲片（長圓角的小甲片，上下各兩個穿繩的孔，左上亮、右緣暗），下半截燒成焦黑（鋸齒焦痕邊），中間那片的焦痕上一點還發紅的餘火。
   *  items.yaml「盜賊身上燒黑的舊鐵護甲片」。第 1 次試做是彎的長方甲片加兩塊橢圓焦斑：讀成烤箱、收音機；第 2 次是一片盾形甲片：讀成盾。改成札甲片（一片一片、有穿繩孔），和盾、防具分開。 */
  /*  第 2 版（審查必修 1）：第 1 版三片圓頭甲片扇形攤開＋正中一顆橘點，24 讀成子彈、指虎、長紅眼的小機器人。改成「一小段札甲」：
   *  三片平頂（只磨小圓角）的長方甲片左右並排、彼此疊一點，整段往右上斜 15°；上三分之一橫綁一條褐皮繩穿過每一片、兩端露出繩頭（繩子＝這是甲）；
   *  下緣是不規則的焦黑缺口（佔每片高 30～40%），焦黑與鋼色交界兩道細的橘紅裂紋、最亮一點白黃芯（火三層），不放正中的圓點。 */
  /*  焦鐵小修（複審可修，2026-11-12）：第 2 版三片的焦黑都在同一高度切成一條整齊的橫線（上銀下黑），24 並排有乾電池感。
   *  改成三片焦黑高度錯開、上緣是不規則的斜邊：左片燒到約三分之二（左高右低）、中片燒到三分之一多（左低右高，餘火在這片）、
   *  右片只燒掉右下一個角（左緣在格外、右緣約 1/3 高）。IRON_CHAR[i]＝[左緣佔片高, 右緣佔片高, 六個點各自的上下抖動]。 */
  const IRON_CHAR = [
    [0.62, 0.36, [0.5, -1.5, 1.0, -0.6, 1.4, -0.3]],
    [0.26, 0.5, [-0.4, 1.2, -1.5, 0.8, -1.1, 0.4]],
    [-0.12, 0.38, [0.6, -0.8, 1.1, -1.3, 0.7, -0.5]],
  ];
  const IRON_W = 11.6, IRON_H = 27, IRON_STEP = 10.2, IRON_X0 = -16.3;
  const lamella = (q, o, i) => {
    const x0 = IRON_X0 + i * IRON_STEP, top = -IRON_H / 2, bot = IRON_H / 2, P = (p) => p.roundRect(x0, top, IRON_W, IRON_H, 1.8);
    const [fl, fr, jit] = IRON_CHAR[i], J = [0, 0.2, 0.42, 0.6, 0.8, 1].map((k, n) => [x0 - 0.5 + k * (IRON_W + 1), bot - IRON_H * (fl + (fr - fl) * k) + jit[n]]);
    f(q, "#8d969f", P);
    clip(q, P, (p) => { f(p, "#5e666e", () => p.rect(x0 + IRON_W - 3, top, 3.2, IRON_H)); f(p, "#d0d8de", () => p.rect(x0 + 1.6, top + 1.6, 2, IRON_H * 0.42)); f(p, "#c4ccd2", () => p.rect(x0 + 1.6, top + 1.4, IRON_W - 4.8, 1.4)); poly(p, "#2a2420", [...J, [x0 + IRON_W + 1, bot + 1], [x0 - 1, bot + 1]]); });
    return J;
  };
  const ironArt = (c, o) => at(c, 24, 25.4, 0.93, (q) => {
    let mid = null, right = null;
    for (let i = 0; i < 3; i++) { const draw = (x) => { const J = lamella(x, o, i); if (i === 1) mid = J; if (i === 2) right = J; }; if (i === 0) draw(q); else halo(q, o, draw); }
    /* 交界的餘火：中間那片沿缺口一道、右邊那片焦角的斜邊上一小段（≥32px；小修起跟著右片的焦角走）；主色＋亮色＋白黃芯 */
    const crack = [mid[1], mid[2], mid[3]];
    ln(q, "#ff6a1a", o.small ? 2.4 : 1.8, crack); ln(q, "#ffd23f", o.small ? 1.1 : 0.8, crack);
    if (!o.small) ln(q, "#ff6a1a", 1.4, [right[3], right[4]]);
    ci(q, "#fff6c8", mid[2][0], mid[2][1], o.small ? 1.3 : 1);
    /* 皮繩：上三分之一橫穿三片、兩端露出繩頭（右端往下垂一點） */
    const y = -IRON_H / 2 + IRON_H * 0.28, xa = IRON_X0 - 3.4, xb = IRON_X0 + 2 * IRON_STEP + IRON_W + 3.4;
    ln(q, "#8a5a32", 3.6, [[xa, y + 0.4], [xb - 3, y], [xb, y + 3.2]]); ln(q, "#b88050", 1.1, [[xa + 0.6, y - 0.8], [xb - 3.6, y - 1.2]]);
  }, -0.26);
  /** 寒燼（稀有）：一塊有稜角的深藍灰燼石（左上一面亮），石上兩道發亮的冰藍裂縫、裂縫交會處透出一點橘紅的餘燼（冰與火並存），右上長出兩根淡青冰刺。和熔岩核分剪影：稜角石＋冰刺 vs 圓球。
   *  第 1 次試做是石頭頂上一小朵火：圓石＋頂上的火＝炸彈（引信），火改進裂縫裡、頂上換冰刺。 */
  const frostEmberArt = (c, o) => {
    for (const [x, y, h, w, r] of [[33, 15.6, 12, 3.2, 0.5], [26.4, 13.2, 9, 2.6, 0.1]]) at(c, x, y, 1, (q) => prism(q, h, w, "#8fe3ff", "#e0faff", "#4ab0d8"), r);
    const P = [[6.4, 31], [11.4, 18.6], [21.6, 13], [33, 16.4], [41, 28], [36.4, 40.6], [22, 43.4], [10, 40.4]];
    poly(c, "#5a6c88", P, 1.2); poly(c, "#8a9cba", [[11.4, 18.6], [21.6, 13], [24.6, 25], [9, 29]]); poly(c, "#3e4c64", [[24.6, 25], [41, 28], [36.4, 40.6], [26, 38]]);
    for (const pts of [[[12, 32], [19.4, 28], [24.6, 34], [32, 29.4]], [[25.4, 17], [26.6, 23.6], [24.6, 34]]]) { ln(c, "#5ad0ff", 3.4, pts); ln(c, "#e8fcff", 1.3, pts); }
    ci(c, "#ff6a2a", 24.6, 34, 3.4); ci(c, "#ffd23f", 24.4, 33.6, 1.6);
  };
  /** 熔心晶（稀有）：一顆八角形的橘紅寶石（正面一塊平的八角桌面、周圍一圈切面：左上亮、右下暗），桌面裡透出一團黃白的火（灰燼之心），外圍橘色光暈。
   *  第 1 次試做是心形的橘色結晶：24 一眼是「愛心」，和生命、體質的紅心撞、又像回血，改成寶石＋裡面一團火。 */
  const moltenArt = (c, o) => {
    const O = [0, 1, 2, 3, 4, 5, 6, 7].map((i) => [24 + Math.cos(-PI / 2 + PI / 8 + (i * PI) / 4) * 19, 25 + Math.sin(-PI / 2 + PI / 8 + (i * PI) / 4) * 18]);
    const I = O.map(([x, y]) => [24 + (x - 24) * 0.56, 25 + (y - 25) * 0.56]);
    poly(c, "#e86a1e", O, 0.8);
    /* 第 2 版（審查必修 3、規則 2 例外放寬到切割寶石）：8 片切面只用 4 階——亮 #ffc060、本色 #e86a1e、暗一 #c8501a、暗二 #a8400e；
     * 第 i 片的中心在 −45°＋i×45°（i＝0 右上、1 右、2 右下、3 下、4 左下、5 左、6 左上、7 上）；相鄰兩片一定不同階（繞回來也不同）。
     * 桌面是最亮的一塊：填火的亮色 #ffe27a（比所有切面亮），裡面的火照規則 5 是主色＋白芯。 */
    const LT = "#ffc060", BASE = "#e86a1e", D1 = "#c8501a", D2 = "#a8400e";
    const col = [BASE, D1, D2, D1, BASE, LT, BASE, LT];
    for (let i = 0; i < 8; i++) poly(c, col[i], [O[i], O[(i + 1) % 8], I[(i + 1) % 8], I[i]]);
    poly(c, "#ffe27a", I); flame(c, "#ff6a1a", 24, 26.6, 0.86); flame(c, "#fff6d8", 24, 29.4, 0.4);
    el(c, "#ffffff", 15, 13.6, 1.6, 3, 0.8);
  };
  /** 硫磺結晶：一塊褐灰的小石頭上長出三顆鮮黃的雙錐形結晶（中間最大），旁邊一縷淡黃的煙。和霧晶分剪影：矮胖的雙錐晶 vs 細長的晶柱。 */
  const bipyr = (c, x, y, w, h, col, lite, dark, r) => at(c, x, y, 1, (q) => { poly(q, col, [[0, -h], [w, 0], [0, h * 0.62], [-w, 0]], 0.6); poly(q, lite, [[0, -h], [-w, 0], [0, 0]]); poly(q, dark, [[0, 0], [w, 0], [0, h * 0.62]]); }, r);
  const sulfurArt = (c, o) => {
    if (!o.small) cloud(c, "#e8e0a0", 37.6, 11.6, 0.6);
    poly(c, "#8a7a66", [[7, 40], [11.4, 33.6], [22, 31.6], [34, 32], [41, 37], [38.6, 43.4], [10, 43.4]], 1.2); f(c, "#ac9c86", () => c.rect(11.6, 33.6, 22, 2));
    bipyr(c, 13.6, 30.4, 6, 12, "#e8d43a", "#fff49a", "#b8a020", -0.36); bipyr(c, 34.6, 30, 5.6, 11, "#e8d43a", "#fff49a", "#b8a020", 0.4); bipyr(c, 24, 25.6, 8, 17, "#f0dc40", "#fff8b0", "#c0a822", 0);
  };
  /** 黑曜片：一片尖的黑曜石碎片（深灰黑帶一點紫的玻璃），貝殼狀的弧形紋，左上一面寬的灰紫反光、白色的銳利邊緣亮線。
   *  第 2 版（審查可修 3）：第 1 版為了過平均亮度 100 把主色提亮成淡紫，像紫水晶、和上料與源力同色系；本體回深灰黑帶紫，
   *  亮度靠白邊亮線與寬反光撐（規則 6 的近黑例外延伸到黑色材料，2026-11-12 美術 PM 決定；自查表另列實際亮度）。 */
  const obsidianArt = (c, o) => {
    const P = [[8.6, 40], [13, 22], [27.6, 5.4], [39.6, 18], [37, 34], [24.6, 43]];
    poly(c, "#3a3446", P, 0.8); poly(c, "#a49cb8", [[13, 22], [27.6, 5.4], [27, 20], [17.4, 30]]); poly(c, "#26222e", [[27, 20], [39.6, 18], [37, 34], [24.6, 43]]);
    for (const [r, a0, a1] of [[10, 0.2, 1.4], [16, 0.3, 1.2], ...(o.small ? [] : [[22, 0.4, 1.05]])]) st(c, "#5a5070", 1.6, (q) => q.arc(8.6, 40, r, -a1, -a0));
    ln(c, "#ffffff", o.small ? 2 : 1.6, [[13.6, 21.2], [27, 6.6]]); ln(c, "#d8d2e6", o.small ? 1.6 : 1.2, [[28.4, 6.8], [38.4, 18]]); el(c, "#ffffff", 21.4, 15.6, 1.5, 3.2, 0.7);
  };

  // ---------------- 染料（同一家族：同一個陶罐、只換染料的顏色——刻意同形，靠顏色分，同第 4 批六個姿態徽章的做法） ----------------
  /** 染料罐：矮胖的灰褐粗陶罐（寬口、米白口沿、左上亮、右下暗），從上面斜看罐口是一大面染料（亮面一道），染料從口沿往下流一道粗的；罐裡斜插一根木攪棒、棒頭沾著同色。col＝items.yaml 的 color。
   *  罐身用中間亮度的灰褐（不是米白）：第 1 次試做是米白罐，雪白染料在米白罐上看不出來；灰褐對六色（含墨色、雪白）都拉得開。 */
  const dyeArt = (col) => (c, o) => {
    const lite = mix(col, "#ffffff", 0.45), deep = mix(col, "#000000", 0.3);
    ln(c, "#a06a36", 3.4, [[27, 18], [38.4, 7.4]]); ln(c, col, 3.6, [[36.4, 9.6], [39.2, 6.6]]);
    const J = (q) => { q.moveTo(10, 20); q.lineTo(38, 20); q.bezierCurveTo(46, 26, 45, 39, 37.6, 44); q.lineTo(10.4, 44); q.bezierCurveTo(3, 39, 2, 26, 10, 20); q.closePath(); };
    f(c, "#a8987e", J); clip(c, J, (q) => { f(q, "#7e705c", () => { q.moveTo(48, 20); q.lineTo(48, 48); q.lineTo(24, 48); q.bezierCurveTo(38, 42, 40, 30, 36, 20); q.closePath(); }); f(q, "#c8baa0", () => q.rect(6.4, 24, 3, 14));
      f(q, col, () => { q.moveTo(13, 20); q.lineTo(21, 20); q.quadraticCurveTo(20, 30, 19.4, 33.4); q.quadraticCurveTo(17.6, 37, 15.6, 33.6); q.quadraticCurveTo(14.6, 28, 13, 20); q.closePath(); }); });
    el(c, "#e8dcc0", 24, 17.6, 17.6, 6); el(c, deep, 24, 17.8, 14.4, 4.4); el(c, col, 24, 17.4, 13.4, 3.8); el(c, lite, 18.4, 16.4, 4.6, 1.2);
    ln(c, "#a06a36", 3.4, [[24.6, 17.4], [28.6, 13]]);
    if (!o.small) el(c, "#ffffff", 16.4, 18.6, 1.2, 0.5);
  };

  // ---------------- 通用（拿到物品飛進背包；GainEffects.tsx 的 GainIcon：深底圓＋金邊） ----------------
  /** 通用物品：米黃色的粗布袋（圓肚、口上紮緊、袋口一圈荷葉邊往外翻），束口一圈褐繩、繩頭垂下，袋身一塊補丁。和選項「交易」的錢袋分：不畫金幣、布色淺、袋口翻開。 */
  const sackArt = (c, o) => { c.save(); c.translate(24, 26); c.scale(1.12, 1.12); c.translate(-24, -26.6);
    const S = (q) => { q.moveTo(17, 21); q.bezierCurveTo(4, 26, 5, 43, 24, 43.4); q.bezierCurveTo(43, 43, 44, 26, 31, 21); q.closePath(); };
    f(c, "#d8a868", S); clip(c, S, (q) => { f(q, "#a8783e", () => { q.moveTo(48, 20); q.lineTo(48, 48); q.lineTo(20, 48); q.bezierCurveTo(36, 42, 38, 30, 31, 20); q.closePath(); }); f(q, "#f0c890", () => q.ellipse(13.6, 29, 2.4, 5, 0.4, 0, TAU)); });
    if (!o.small) { rr(c, "#b88a50", 24.4, 30.4, 8.6, 7.4, 1.2); f(c, "#d8a868", () => c.rect(25.6, 31.4, 1, 5.4)); }
    poly(c, "#e8bc7c", [[14.6, 10.6], [20, 14.6], [24, 9.4], [28, 14.6], [33.4, 10.6], [31.4, 20], [16.6, 20]], 1); f(c, "#b8864a", () => c.rect(18, 17, 12, 3));
    rr(c, "#7a4a28", 15.6, 19.4, 16.8, 4.4, 2); ln(c, "#7a4a28", 2.2, [[30.6, 22], [35, 27.6]]); c.restore();
  };

  // =====================================================================
  // 圖示表。grp：potion 藥與草｜throw 投擲瓶｜supply 補給｜mat 通用材料｜cloud 雲嶺材料｜ashen 荒原材料｜dye 染料｜gain 通用（飛進背包）
  // cat／tier：框（itemIcons.js 的類別底色、品質框；tier 照 itemIcons.js 的 LIST）。kind：items.yaml 的 kind。src：沿用出處。
  // sizes：用到的大小（CSS px）。42＝背包格／腰包格（.world-bag-cell 50px 裡和裝備圖示同樣畫 42）、32＝信件附件（和裝備圖示格同高）、
  //        28＝拿到物品飛進背包（GainIcon 28；第 2 版起一律畫在深底圓金邊裡，frameOf）、24＝清單列（商店、戰利品、腰包整理：提案，現行是純文字列）。
  // =====================================================================
  const BAG = [42, 32, 28, 24];
  const ICON = {
    item_hp_potion_small: { zh: "小回復藥", grp: "potion", kind: "consumable", cat: "consumable", src: "style:item.item_hp_potion_small", topic: "圓肚玻璃瓶、褐色軟木塞、紅藥水、瓶身白十字（風格樣張）", d: (c, o) => Q.ART.item.item_hp_potion_small.d(c, o) },
    item_hp_potion_medium: { zh: "中回復藥", grp: "potion", kind: "consumable", cat: "consumable", topic: "大一號的圓肚瓶、長瓶頸、金色頸環、深紅藥水、大白十字，瓶塞上一滴紅封蠟", d: hpMediumArt },
    item_mana_potion: { zh: "回魔藥", grp: "potion", kind: "consumable", cat: "consumable", src: "style:item.item_mana_potion", topic: "菱形尖肚瓶、淡紫水晶瓶塞、藍藥水、瓶身白色四芒星（風格樣張）", d: fitIn(0.92, (c, o) => Q.ART.item.item_mana_potion.d(c, o)) },
    item_antidote_herb: { zh: "解毒草", grp: "potion", kind: "consumable", cat: "consumable", topic: "三片長葉子扇形攤開（中間最長、左半亮、中脈），葉柄束在一起、綁一圈紅繩", d: herbArt },
    item_water_flask: { zh: "水瓶", grp: "throw", kind: "consumable", cat: "throwable", topic: "赭紅陶罐（圓肚、細頸、外撇口、右邊把手），肚上一道藍色水紋，罐口湧出一團藍水、右上一顆水滴", d: waterArt },
    item_oil_flask: { zh: "油瓶", grp: "throw", kind: "consumable", cat: "throwable", topic: "黃釉陶油壺（圓肚、短頸、木塞、右邊往上翹的壺嘴），壺嘴尖用一條細油線垂一滴琥珀色淚滴（左上白亮點）", d: oilArt },
    item_mist_flask: { zh: "霧瓶", grp: "throw", kind: "consumable", cat: "throwable", topic: "淡青瓷色的葫蘆（上小下大、腰間紅繩、木塞），右上冒出一團白霧（不壓在瓶口上）", d: mistArt },
    item_frost_flask: { zh: "冰瓶", grp: "throw", kind: "consumable", cat: "throwable", topic: "白瓷梅瓶（寬肩、往下收窄，肩上一道青花藍紋），瓶口長出三根淡青冰柱，右上一顆白色閃光", d: frostArt },
    item_fire_flask: { zh: "火瓶", grp: "throw", kind: "consumable", cat: "throwable", src: "style:item.item_fire_flask", topic: "方肩投擲瓶、瓶口塞布條、布頭點著火，瓶裡橘色的油與火苗（風格樣張）", pre: fitIn(0.9, (c, o) => Q.ART.item.item_fire_flask.pre(c, o)), d: fitIn(0.9, (c, o) => Q.ART.item.item_fire_flask.d(c, o)) },
    item_supplies: { zh: "補給", grp: "supply", kind: "supply", cat: "supply", src: "b7:ration", topic: "一條圓胖的麵包、表面三道斜刀痕（第 7 批 HUD「補給」同一個）；買了直接加補給、不進背包，只出現在商店", d: (c, o) => QH.def("ration").d(c, o) },
    item_coarse_material: { zh: "粗料", grp: "mat", kind: "material", cat: "material", tier: 1, topic: "兩塊疊著的灰色粗石塊（不規則多邊形、上面亮、右面暗），前面那塊一道深色裂紋；沒有晶面、沒有亮晶", d: coarseArt },
    item_fine_material: { zh: "精料", grp: "mat", kind: "material", cat: "material", tier: 2, src: "style:item.item_fine_material", topic: "一塊藍灰色多邊形礦石、三個切面、嵌亮晶（風格樣張）", d: (c, o) => Q.ART.item.item_fine_material.d(c, o) },
    item_superior_material: { zh: "上料", grp: "mat", kind: "material", cat: "material", tier: 3, topic: "紫灰礦石底座上長出一叢三根發光的紫晶（中間最高）", pre: (c) => glow(c, 24, 20, 20, "#b48cff", 0.5), d: superiorArt },
    item_essence: { zh: "精華", grp: "mat", kind: "material", cat: "material", tier: 3, topic: "淡金色的菱形結晶（四個切面），外圍金色光暈，旁邊白色四芒星閃光", pre: (c) => glow(c, 24, 24, 21, "#ffe8a0", 0.6), d: essenceArt },
    item_scorched_iron: { zh: "焦鐵", grp: "mat", kind: "material", cat: "material", tier: 1, topic: "一小段札甲：三片平頂長方鐵甲片並排互疊、整段往右上斜，上三分之一橫綁一條褐皮繩（兩端露繩頭），下半燒黑：三片焦黑高度錯開（左片三分之二、中片三分之一多、右片只燒右下角）、上緣不規則斜邊，交界兩道橘紅裂紋（白黃芯）", d: ironArt },
    item_mist_crystal: { zh: "霧晶", grp: "cloud", kind: "material", cat: "material", tier: 2, topic: "三根淡灰白的晶柱（中間最高、左右斜開），腳下一條往左右伸出晶柱外的扁雲帶（上緣圓鼓、平底、自己包外框）", pre: (c) => glow(c, 24, 26, 20, "#e8f0f0", 0.45), d: mistCrystalArt, fly: 0.77 },
    item_summit_mist_crystal: { zh: "雲頂霧晶", grp: "cloud", kind: "material", cat: "material", tier: 3, topic: "一大根發光的淡青晶石立在一朵白雲上，兩旁兩根小的（稀有）", pre: (c) => glow(c, 24, 20, 21, "#a0e6ff", 0.6), d: summitArt },
    item_talisman_ash: { zh: "符紙灰", grp: "cloud", kind: "material", cat: "material", tier: 1, topic: "一堆灰色灰燼（圓丘），斜插一張燒了一半的黃符紙（紅符文、下緣焦黑），右邊一顆火星", d: ashArt },
    item_cinnabar: { zh: "丹砂", grp: "cloud", kind: "material", cat: "material", tier: 2, topic: "白瓷淺碟（一道藍邊）裡一堆朱紅色丹砂粉，上面兩顆朱紅小晶塊", d: cinnabarArt },
    item_wolf_fang: { zh: "狼牙", grp: "cloud", kind: "material", cat: "material", tier: 1, topic: "一顆彎的象牙白大獸牙（尖朝右下、右緣暗），牙根綁褐皮繩、繩頭垂下", d: fangArt },
    item_thunder_feather: { zh: "雷羽", grp: "cloud", kind: "material", cat: "material", tier: 2, topic: "淡紫白的大羽毛斜放（右半暗、羽軸深紫、下緣一道缺口），右下一道黃色閃電", d: thunderArt },
    item_living_bone: { zh: "活血骨", grp: "cloud", kind: "material", cat: "material", tier: 2, topic: "斜放的骨頭（兩端圓節），一道紅色血脈，中間一顆紅血珠（外圍紅光）", pre: (c) => glow(c, 26, 26, 12, "#ff4a4a", 0.55), d: boneArt },
    item_green_bamboo: { zh: "青竹節", grp: "cloud", kind: "material", cat: "material", tier: 1, topic: "一段斜放的青竹（兩個深綠竹節），上端切口露淺黃竹肉，右下長一片竹葉", d: bambooArt },
    item_lava_core: { zh: "熔岩核", grp: "ashen", kind: "material", cat: "material", tier: 2, topic: "一顆圓的灰褐熔岩石（左上亮、右下暗），三道發亮的橘黃裂縫，外圍橘色光暈", pre: (c) => glow(c, 24, 25, 22, "#ff7a2a", 0.55), d: lavaArt },
    item_frost_ember: { zh: "寒燼", grp: "ashen", kind: "material", cat: "material", tier: 3, topic: "一塊有稜角的深藍灰燼石，兩道發亮的冰藍裂縫、交會處透出一點橘紅餘燼，右上兩根淡青冰刺（稀有）", pre: (c) => glow(c, 24, 27, 20, "#78d2ff", 0.55), d: frostEmberArt },
    item_molten_heart: { zh: "熔心晶", grp: "ashen", kind: "material", cat: "material", tier: 3, topic: "八角形的橘紅寶石（平的八角桌面、一圈 8 片切面只用 4 階、左上亮右下暗、相鄰不同階），桌面最亮（火的亮黃）、裡面一團橘火＋白芯，外圍橘色光暈（稀有）", pre: (c) => glow(c, 24, 25, 22, "#ffa03c", 0.6), d: moltenArt, fly: 0.82 },
    item_ember_feather: { zh: "餘燼羽", grp: "ashen", kind: "material", cat: "material", tier: 2, topic: "往右彎的火橘羽毛（右半暗、淺黃羽軸從羽片下端伸出一截羽根、外緣透黃、兩道 V 形缺口），羽尖一小朵火，旁邊火星", pre: (c) => glow(c, 24, 24, 20, "#ff8a3a", 0.45), d: emberArt },
    item_sulfur_crystal: { zh: "硫磺結晶", grp: "ashen", kind: "material", cat: "material", tier: 1, topic: "褐灰小石上長出三顆鮮黃的雙錐形結晶（中間最大），右上一縷淡黃煙", d: sulfurArt },
    item_obsidian_shard: { zh: "黑曜片", grp: "ashen", kind: "material", cat: "material", tier: 2, topic: "一片尖的深灰黑（帶一點紫）玻璃碎片，貝殼狀弧紋、左上一面寬的灰紫反光、白色銳利邊緣亮線（黑色材料：規則 6 近黑例外）", d: obsidianArt },
    ...Object.fromEntries([["indigo", "靛青", "#2E4A7D"], ["cinnabar", "朱砂", "#B23A2E"], ["ink", "墨色", "#2B2B2B"], ["jade", "翠綠", "#3E8E6A"], ["ochre", "赭黃", "#C08A3E"], ["snow", "雪白", "#E8E8E8"]].map(([id, zh, col]) => [`item_dye_${id}`,
      { zh: `${zh}染料`, grp: "dye", kind: "dye", cat: "dye", color: col, topic: `灰褐粗陶罐（米白口沿），罐口一大面${zh}染料、往下流一道，斜插一根沾了同色的木攪棒（染料色 ${col}，items.yaml 原樣）；六罐同形只換色`, d: dyeArt(col) }])),
    gain_gear: { zh: "通用：裝備", grp: "gain", frame: "fly", sizes: [28], src: "b4:skeleton.strike", topic: "斜放的亮色單手劍（第 4 批徽章「打擊」、第⑧批小牌劍同一個）；現行 6Q-1 起裝備已畫實際的裝備圖示，這個只在沒有外觀資料時用", d: b10((c, o) => QP.entry("skeleton", "strike").d(c, o), 1.2) },
    gain_item: { zh: "通用：物品", grp: "gain", frame: "fly", sizes: [28], topic: "米黃粗布袋（圓肚、束口紮褐繩、袋口荷葉邊翻開、一塊補丁）；物品圖示移植後只在沒有對應圖示時用", d: sackArt },
  };
  /* 品質框（tier）照 itemIcons.js 的 LIST 第 5 欄（材料 1～3）抄在上表；沒有 tier 的照類別色框。 */
  for (const e of Object.values(ICON)) { e.sizes = e.sizes ?? BAG; e.frame = e.frame ?? "bag"; }

  // ---------------- 出圖 ----------------
  const def = (id) => { const e = ICON[id]; return { d: e.d, pre: e.pre, post: e.post }; };
  /** 飛進背包的大小（GainIcon 28）。第 2 版（美術 PM 決定 3）：物品飛進背包一律用深底圓金邊（和 GainIcon、6Q-1 的裝備飛行一致），不用物品自己的方框。 */
  const FLY_PX = 28;
  /** 這個大小用哪一種框：通用 2 個永遠是飛行圓；物品在 28（飛進背包）也是飛行圓，其他大小是背包框。opt.frame 可以指定。 */
  const frameOf = (id, size, opt = {}) => opt.frame ?? (ICON[id].frame === "fly" || size === FLY_PX ? "fly" : ICON[id].frame);
  /** 圖樣本身（不含框）的邊長：背包框裡四邊留白 7%（風格樣張 paint 的 item 同一個值）；飛行的深底圓裡 0.8（裁在內圓裡；ICON 的 fly 可以個別改：主形出內圓或佔圓不到 70% 的幾個，見自查表下半）。 */
  const glyphPx = (id, size, opt = {}) => (frameOf(id, size, opt) === "fly" ? size * (ICON[id].fly ?? 0.8) : size * 0.86);
  /** 只畫圖樣（不含框）。外框粗細照顯示大小（規則 1）；這批最小 24，圖樣 20.6px 仍包外框（≤14px 才不包）。 */
  const glyph = (id, size, res = 2, opt = {}) => { const a = glyphPx(id, size, opt); return Q.render(opt.noPre ? { d: def(id).d } : def(id), a, res, { ow: opt.ow ?? (a <= 14 ? 0 : Q.outlinePx(size)) }); };
  const CAT_ZH = { consumable: "消耗品（綠底）", throwable: "投擲瓶（藍底）", supply: "補給（褐底）", material: "材料（灰底，框＝品質）", dye: "染料（紫底）" };
  /** 框線色（第 2 版，美術 PM 決定 1）：材料的品質 1／2／3 直接用裝備稀有度 GEAR_RARITY（client/src/render/artPalette.ts；樣張端 QIconsWeapons.RARITY 同一份）
   *  的 common／rare／epic；消耗品、投擲瓶、補給、染料的框線一律中性色 #8a6a3a（現行名字小牌 .world-bag-tile 的框色），類別只靠底色漸層分。
   *  #8a6a3a 而不用 #8a8f99：#8a8f99 就是 GEAR_RARITY 的 common，非材料類用它會讀成「普通稀有度」、和品質 1 的材料同框，框色的意思又混了；
   *  #8a6a3a 不在稀有度色裡、只表示「這是物品」，而且就是玩家現在在背包裡看到的物品框色。 */
  const NEUTRAL_RIM = "#8a6a3a", TIER_RARITY = { 1: "common", 2: "rare", 3: "epic" };
  const rimOf = (id) => { const t = ICON[id].tier; return t ? QW.RARITY[TIER_RARITY[t]][0] : NEUTRAL_RIM; };
  /** 背包框：itemIcons.js 的 draw 的框（類別底色漸層 ItemIcons.CAT[cat][0] → #1a1612、圓角 16%、線寬 max(1.5, 3.5%)）照原樣畫，只換框線色（rimOf）。
   *  itemIcons.js 本身不動（風格樣張也用它），這裡照它的幾行重畫框、不畫圖樣。 */
  function bagFrame(ctx, id, size) {
    const bg = window.ItemIcons.CAT[ICON[id].cat][0];
    ctx.save(); ctx.beginPath(); ctx.roundRect(0, 0, size, size, size * 0.16); const g = ctx.createLinearGradient(0, 0, 0, size); g.addColorStop(0, bg); g.addColorStop(1, "#1a1612"); ctx.fillStyle = g; ctx.fill();
    ctx.lineWidth = Math.max(1.5, size * 0.035); ctx.strokeStyle = rimOf(id); ctx.stroke(); ctx.restore();
  }
  /** GainIcon 的框（GainEffects.tsx 原樣）：深底 #2a2018 圓（r＝13/28）、金邊 #e8bb48 線寬 1.6/28。 */
  function flyFrame(ctx, size) { const k = size / 28; ctx.beginPath(); ctx.arc(size / 2, size / 2, 13 * k, 0, TAU); ctx.fillStyle = "#2a2018"; ctx.fill(); ctx.lineWidth = 1.6 * k; ctx.strokeStyle = "#e8bb48"; ctx.stroke(); }
  /** 數量（itemIcons.js 的 draw 同一個寫法：右下粗體、黑描邊）。 */
  function countText(ctx, size, n) { ctx.font = `bold ${Math.round(size * 0.24)}px Consolas, monospace`; ctx.textAlign = "right"; ctx.textBaseline = "alphabetic"; ctx.lineWidth = 3; ctx.strokeStyle = "#000"; ctx.strokeText(String(n), size - 4, size - 4); ctx.fillStyle = "#fff"; ctx.fillText(String(n), size - 4, size - 4); }
  /** 含框的圖示畫在 (0,0)～(size,size)；ctx 已 scale(res)。opt.frame："none" 只畫圖樣；opt.count：右下數量。 */
  function paint(ctx, id, size, res, opt = {}) {
    const fr = frameOf(id, size, opt), a = glyphPx(id, size, opt), p = (size - a) / 2;
    ctx.save();
    if (fr === "bag") bagFrame(ctx, id, size);
    if (fr === "fly") { flyFrame(ctx, size); ctx.save(); ctx.beginPath(); ctx.arc(size / 2, size / 2, (12.2 / 28) * size, 0, TAU); ctx.clip(); }
    QW.blit(ctx, glyph(id, size, res, opt), p, p, a, res);
    if (fr === "fly") ctx.restore();
    if (opt.count) countText(ctx, size, opt.count);
    ctx.restore();
  }
  function canvas(id, px, zoom = 1, opt = {}) { const res = opt.res ?? (zoom === 1 ? 2 : zoom), cv = blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d"); x.scale(res, res); paint(x, id, px, res, opt); x.setTransform(1, 0, 0, 1, 0, 0); return cv; }
  const GRP_ZH = { potion: "藥與草（消耗品 4）", throw: "投擲瓶（消耗品 5）", supply: "補給（1）", mat: "通用材料（5）", cloud: "雲嶺材料（8）", ashen: "灰燼荒原材料（6）", dye: "染料（6）", gain: "通用：拿到物品飛進背包（2）" };
  const list = (grp) => Object.entries(ICON).filter(([, e]) => !grp || e.grp === grp).map(([id, e]) => ({ id, ...e, min: Math.min(...e.sizes) }));
  return { ICON, GRP_ZH, CAT_ZH, BAG, FLY_PX, NEUTRAL_RIM, def, frameOf, rimOf, glyph, glyphPx, paint, canvas, bagFrame, flyFrame, countText, list };
})();
