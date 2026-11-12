// qIconsWeapons.js：「小圖示改 Q 版」全量重畫第 1 批——武器 17 種 53 款＋副手 4 種 8 款（畫圖 agent 2026-11-11）。
// 規則：docs/art/Q版小圖示樣張.md 第 2 節（14 條）；紀錄：docs/art/Q版小圖示-第1批武器.md；樣張頁：q-icons-weapons.html。
// 一張圖放兩種框：米色圓章（武器小圖示 20、24、28px）與裝備格（32、48、64px）。框照現行，這裡只畫框裡的圖。
// 清單照遊戲端 client/src/render/gearAppearance.json（kind × form）；變體照現行的分法，不新增規則：
//   材質 material → 主色／暗色；元素關鍵字（ignite、wet、charged、frozen，或武器表的 element）→ 主色混 40% 元素色、杖頭與法器珠換元素色；
//   稀有度 rarity → 外框（現行樣式）＋史詩以上護手改金色；其餘關鍵字的小圖樣（>36px 才畫）不在這一批，照現行原樣疊上去（位置在 meta.spots）。
// 造型與配色照 qDoll.js 的 QW／paperdoll.js（人物手上那一把），只加粗；人物沒有分的形制（彎刀、戟、權杖…）照現行裝備圖示的形制畫，材質色仍用人物那一份。
// 座標：48×48。斜放的武器畫在「握把 +y、作用端 −y」的直立座標再轉 45°（握把左下、作用端右上）；槍畫在「槍口 +x」再轉 −45°；手槍只斜 −0.42（側面 L 形）；拳套、盾、書、法器珠直立。
// 依賴 qIcons.js（先載入）：QIcons.H 畫法小工具、QIcons.W 八把樣本的畫法、QIcons.render 剪影外框。
window.QIconsWeapons = (() => {
  const Q = window.QIcons, { mix, f, rr, ci, el, poly, ln, starPts, glow, flame, sparkle, halo, HI, HI2, SH } = Q.H, W = Q.W, M = Q.M, TAU = Math.PI * 2, OUT = Q.OUT;
  const WOOD = "#7a5232", WOODL = "#a87648", CREAM = "#e8e0c8", GOLD = "#e8bb48", GOLDL = "#f6d878";
  /** 材質色：鐵、鋼、金、木、皮、布、骨照 paperdoll.js 的 MATERIAL（人物）；銅、銀、晶石人物沒有，照現行裝備圖示（gearIcon 的色票）。 */
  const MAT = { iron: ["#8d969f", "#5a6169"], steel: ["#c3ccd6", "#7d8794"], copper: ["#c27a48", "#7e4a28"], silver: ["#e8edf2", "#a8b0ba"], gold: ["#e8bb48", "#9c7420"], wood: ["#a06a36", "#6a4420"], leather: ["#8a5a32", "#5e3b1f"], cloth: ["#8a8f99", "#5d6168"], bone: ["#e9e3cf", "#a8a08a"], crystal: ["#b8a8ff", "#7a68c8"] };
  const MAT_ZH = { iron: "鐵", steel: "鋼", copper: "銅", silver: "銀", gold: "金", wood: "木", leather: "皮", cloth: "布", bone: "骨", crystal: "晶石" };
  const METAL = ["iron", "steel", "copper", "silver", "gold"];
  /** 會混色的元素關鍵字（照 gearAppearance.json 的 elementKeywords 與 artPalette 的色）；shock、freeze 是樣張端 gearArt.js 的舊名。 */
  const KW = { ignite: "#ff6a1a", wet: "#4aa8ff", charged: "#fff36b", frozen: "#8fe3ff", shock: "#fff36b", freeze: "#8fe3ff" };
  const KW_OF_EL = { fire: "ignite", water: "wet", lightning: "charged", ice: "frozen" }, EL_OF_KW = { ignite: "fire", wet: "water", charged: "lightning", frozen: "ice", shock: "lightning", freeze: "ice" };
  const RARITY = { common: ["#8a8f99", "普通"], uncommon: ["#5fd05f", "優良"], rare: ["#4f9dff", "稀有"], epic: ["#b06cff", "史詩"], legendary: ["#ffbf3a", "傳說"] };
  // 清單：遊戲端 gearAppearance.json 的 weapon 17 種、offhand 4 種（forms 的順序同資料檔）。diag＝45° 斜放的長條物（規則 7 門檻 60%，其餘 70%）。
  const KINDS = {
    sword: { zh: "劍", slot: "weapon", forms: { straight: "直劍", curved: "彎刀", broad: "闊劍", arcane: "魔導劍" }, mats: METAL, def: "iron", diag: true },
    greatsword: { zh: "巨劍", slot: "weapon", forms: { twohand: "雙手劍", zhanma: "斬馬刀", serrated: "鋸齒巨劍" }, mats: METAL, def: "iron", diag: true },
    dagger: { zh: "匕首", slot: "weapon", forms: { short: "短刀", stiletto: "三稜刺", kris: "彎匕" }, mats: [...METAL, "bone", "crystal"], def: "iron", diag: true },
    axe: { zh: "斧", slot: "weapon", forms: { hand: "手斧", battle: "戰斧", double: "雙刃斧" }, mats: METAL, def: "iron", diag: true },
    hammer: { zh: "錘", slot: "weapon", forms: { mace: "釘頭錘", warhammer: "戰錘", flail: "連枷" }, mats: METAL, def: "iron", diag: true },
    spear: { zh: "矛", slot: "weapon", forms: { spear: "長矛", halberd: "戟", trident: "三叉戟" }, mats: [...METAL, "wood"], def: "iron", diag: true },
    bow: { zh: "弓", slot: "weapon", forms: { short: "短弓", long: "長弓", recurve: "反曲弓" }, mats: ["wood", ...METAL], def: "wood", diag: true },
    crossbow: { zh: "弩", slot: "weapon", forms: { light: "輕弩", heavy: "重弩", repeater: "連弩" }, mats: ["wood", ...METAL], def: "wood", diag: true },
    longgun: { zh: "火槍", slot: "weapon", forms: { flintlock: "燧發火槍", hunting: "獵槍", sniper: "狙擊火槍" }, mats: METAL, def: "steel", diag: true },
    shotgun: { zh: "霰彈槍", slot: "weapon", forms: { blunderbuss: "喇叭槍", double: "雙管", pump: "泵動" }, mats: METAL, def: "iron", diag: true },
    pistol: { zh: "手槍", slot: "weapon", forms: { flintlock: "燧發手槍", revolver: "左輪", derringer: "短銃" }, mats: METAL, def: "steel" },
    dual_pistol: { zh: "雙手槍", slot: "weapon", forms: { flintlock: "燧發手槍", revolver: "左輪", derringer: "短銃" }, mats: METAL, def: "steel", pair: true },
    fist: { zh: "拳套", slot: "weapon", forms: { katar: "拳刃", knuckle: "鐵拳", claw: "爪" }, mats: [...METAL, "bone", "leather"], def: "iron" },
    scythe: { zh: "鐮刀", slot: "weapon", forms: { long: "長柄鐮", crescent: "彎月鐮", hook: "鉤鐮" }, mats: [...METAL, "bone"], def: "iron", diag: true },
    whip: { zh: "鞭", slot: "weapon", forms: { leather: "皮鞭", chain: "鏈鞭", bladed: "蛇骨鞭" }, mats: ["leather", ...METAL, "bone"], def: "leather", diag: true }, /* 握柄在左下、鞭梢甩到右上，算斜放 */
    dual_dagger: { zh: "雙匕首", slot: "weapon", forms: { short: "短刀", stiletto: "三稜刺", kris: "彎匕" }, mats: [...METAL, "bone", "crystal"], def: "iron", pair: true },
    staff: { zh: "杖", slot: "weapon", forms: { long: "長杖", scepter: "權杖", wand: "短杖", totem: "圖騰杖" }, mats: ["wood", ...METAL, "bone", "crystal"], def: "wood", diag: true },
    round_shield: { zh: "圓盾", slot: "offhand", forms: { wood: "木圓盾", banded: "包鐵圓盾" }, mats: ["wood", ...METAL], def: "wood" },
    kite_shield: { zh: "鳶盾", slot: "offhand", forms: { kite: "鳶盾", tower: "塔盾" }, mats: METAL, def: "iron" },
    tome: { zh: "法書", slot: "offhand", forms: { book: "典籍", scroll: "卷軸匣" }, mats: ["leather", "cloth"], def: "leather" },
    orb: { zh: "法器珠", slot: "offhand", forms: { ball: "水晶球", floating: "浮空寶珠" }, mats: ["crystal", "bone"], def: "crystal" },
  };
  /** 沒寫 form 時畫哪一款：照人物與現行武器小圖示（qDoll 的 QW.hammer 預設是方頭；現行裝備圖示會退回第一個形制「釘頭錘」，兩套現行不一致，見紀錄）。其餘都是清單第一個。 */
  const NO_FORM = { hammer: "warhammer" };

  /** 驗證＋補預設（同 gearIcon.resolveGear）：任何輸入都回傳畫得出來的外觀。look.color＝人物外觀的染色覆寫（例如範本給的木色塔盾）。 */
  function resolve(look) {
    const src = look ?? {}, kind = KINDS[src.kind] ? src.kind : "sword", K = KINDS[kind];
    const form = src.form in K.forms ? src.form : NO_FORM[kind] ?? Object.keys(K.forms)[0];
    const material = K.mats.includes(src.material) ? src.material : K.def;
    const given = (src.keywords ?? []).filter((k) => typeof k === "string"), fromEl = src.element ? KW_OF_EL[src.element] : undefined;
    const keywords = (fromEl && !given.includes(fromEl) ? [fromEl, ...given] : given).slice(0, 2);
    const tintKw = keywords.find((k) => KW[k]), element = src.element ?? (tintKw ? EL_OF_KW[tintKw] : undefined);
    return { kind, form, material, keywords, tintKw, element, rarity: RARITY[src.rarity] ? src.rarity : "common", color: src.color ?? null };
  }
  /** 配色：主色 a、暗色 d、亮一階 l；護手 guard（單手劍、匕首：暗銅；史詩以上金）、guard2（雙手劍：金）；其餘給 qIcons.js 的八把樣本用。 */
  function palette(r) {
    let [a, d] = r.color ? [r.color, mix(r.color, "#000000", 0.32)] : MAT[r.material];
    const tc = r.tintKw ? KW[r.tintKw] : null;
    if (tc) { if (r.material === "crystal") { a = tc; d = mix(tc, "#000000", 0.4); } else { a = mix(a, tc, 0.4); d = mix(d, tc, 0.25); } }
    const rich = r.rarity === "epic" || r.rarity === "legendary", wood = r.material === "wood";
    const orbDef = r.kind === "orb" ? (r.material === "crystal" ? "#a898ff" : a) : r.material === "crystal" ? a : "#c8bcff"; /* 法器珠：人物掌上那顆 #a898ff；杖頭：人物的 #c8bcff */
    return { a, d, l: mix(a, "#ffffff", 0.45), guard: rich ? GOLD : M.brass, guard2: rich ? GOLDL : M.gold, arc: r.material === "steel" && !tc ? "#dcd8f4" : mix(a, "#f0e6ff", 0.55),
      wood: a, woodD: d, shaft: wood ? M.shaft : d, head: a, headD: d, orb: tc ?? orbDef, orbEl: r.element, accent: tc ?? (r.material === "crystal" ? "#b8a8ff" : "#e04060"), rich };
  }

  // ---------------- 小工具 ----------------
  const up = W.diag; /* 直立座標（握把 +y、作用端 −y）轉 45° */
  const st = (c, col, w, fn, cap = "round") => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
  /** 槍的座標：槍口朝 +x、上方（準星、擊鎚）朝 −y；a＝轉幾度（−45°＝槍口朝右上）。 */
  const gunF = (c, fn, a = -Math.PI / 4, k = 1, ox = 0, oy = 0) => { c.save(); c.translate(24, 24); c.rotate(a); c.scale(k, k); c.translate(ox, oy); fn(c); c.restore(); };
  /** 直立座標的點 → 48 格座標（給光暈、閃光用）。 */
  const R45 = (x, y) => [24 + (x - y) * Math.SQRT1_2, 24 + (x + y) * Math.SQRT1_2];
  const donut = (c, col, x, y, R, r) => { c.beginPath(); c.arc(x, y, R, 0, TAU); c.moveTo(x + r, y); c.arc(x, y, r, 0, TAU, true); c.fillStyle = col; c.fill("evenodd"); };

  // =====================================================================
  // 劍（QW.sword：鋼刃、暗銅橫護手、深褐握柄；QW.saber：彎刃、橢圓護手）
  // =====================================================================
  /** 彎刀：刃往一側彎、越到前面越寬、刀尖斜削；橢圓小護手、柄尾一顆小圓頭（QW.saber 的零件）。剪影是一彎新月，和直劍的直條分開。 */
  function saberArt(c, o, P) {
    f(c, P.a, () => { c.moveTo(-3, 5); c.quadraticCurveTo(-7.6, -8, -0.4, -15.5); c.lineTo(6.6, -20.6); c.quadraticCurveTo(8.2, -10, 3.8, -2); c.lineTo(3.8, 5); c.closePath(); });
    f(c, SH, () => { c.moveTo(3.8, 5); c.lineTo(3.8, -2); c.quadraticCurveTo(8.2, -10, 6.6, -20.6); c.quadraticCurveTo(4.6, -10, 1.2, -3); c.lineTo(1.2, 5); c.closePath(); });
    st(c, HI2, 1.3, () => { c.moveTo(-1.5, 3.5); c.quadraticCurveTo(-5.2, -7.5, 0.4, -13.6); }, "butt");
    el(c, P.guard, 0.3, 6.5, 6.8, 2.7);
    rr(c, M.grip, -1.6, 8.6, 3.8, 9, 1.2);
    ci(c, P.guard, 0.5, 18.4, 2.7);
  }
  /** 闊劍：刃寬（根部是全長的 1/4）、從根部往前收窄成楔形、劍尖短而鈍、中間一道淺槽；護手兩端往上翹成新月、短握柄、一顆大圓柄頭。和雙手劍分開的地方：短柄＋大柄頭（雙手劍是長柄、沒有柄頭）、暗銅護手（雙手劍是金）。 */
  function broadArt(c, o, P) {
    poly(c, P.a, [[-5.6, 4], [-3.9, -14.5], [0, -20.6], [3.9, -14.5], [5.6, 4]]);
    f(c, SH, () => { c.moveTo(1.9, 4); c.lineTo(1.6, -18.2); c.lineTo(3.9, -14.5); c.lineTo(5.6, 4); c.closePath(); });
    f(c, HI2, () => { c.moveTo(-4.4, 3); c.lineTo(-3, -13.6); c.lineTo(-1.6, -13.6); c.lineTo(-2.9, 3); c.closePath(); });
    if (!o.small) rr(c, P.d, -1.1, -13, 1.9, 14.5, 0.9);
    f(c, P.guard, () => { c.moveTo(-10, 0.6); c.quadraticCurveTo(-9.6, 4, -5, 3.6); c.lineTo(5, 3.6); c.quadraticCurveTo(9.6, 4, 10, 0.6); c.quadraticCurveTo(11.6, 7.6, 5, 7.8); c.lineTo(-5, 7.8); c.quadraticCurveTo(-11.6, 7.6, -10, 0.6); c.closePath(); });
    rr(c, M.grip, -2.1, 7.4, 4.2, 7.6, 1);
    ci(c, P.guard, 0, 17.4, 3.6);
    if (!o.small) ci(c, HI, -1, 16.4, 1.1);
  }
  const SWORD = (r, P) => r.form === "arcane" ? { d: (c, o) => up(c, (x) => W.arcaneArt(x, o, P)), pre: (c) => glow(c, 29, 19, 15, M.arcane, 0.55), post: (c, o) => { if (!o.small) { sparkle(c, "#f6f0ff", 39, 21, 2.6); sparkle(c, "#f6f0ff", 27, 8.5, 2); } } }
    : { d: (c, o) => up(c, (x) => (r.form === "curved" ? saberArt : r.form === "broad" ? broadArt : W.swordArt)(x, o, P)) };

  // =====================================================================
  // 巨劍（QW.greatsword：寬刃、金色橫護手、一根深褐長柄）
  // =====================================================================
  const gsHilt = (c, o, P) => { rr(c, P.guard2, -11.5, 0.8, 23, 4.4, 2.2); if (!o.small) f(c, GOLDL, () => c.rect(-9.5, 1.5, 19, 1)); rr(c, M.grip, -2.2, 5.2, 4.4, 16.3, 1.6); if (!o.small) f(c, "rgba(255,255,255,0.18)", () => c.rect(-1.4, 6.5, 0.9, 13.5)); };
  /** 斬馬刀：單刃長刀——刀背筆直、刀尖往刀背那一側斜上去；沒有橫護手，只有一片金色橢圓刀鐔；長柄尾端一個金環（環首）。和雙手劍分開的地方：沒有十字護手、柄尾有環、刀尖歪一邊。 */
  /* 第 2 版（審查可修）：第 1 版刀身寬 10、長 21，像菜刀也比雙手劍短。刀身收窄到 7.6、拉長到 25，柄（刀鐔到環首）佔全長四成多。 */
  function zhanmaArt(c, o, P) {
    /* 第 3 版（複審可修）：20px 略單薄。刃口那一側從刀鐔往前慢慢放寬（7.6 → 前段 8.8），刀背仍筆直、刀尖仍斜向刀背；刀身長度不變，仍比雙手劍窄。 */
    f(c, P.a, () => { c.moveTo(-3.6, 4); c.lineTo(-4.8, -12.8); c.quadraticCurveTo(-4.6, -20.6, 4, -21.5); c.lineTo(4, 4); c.closePath(); });
    f(c, SH, () => { c.moveTo(1.8, 4); c.lineTo(1.8, -21); c.lineTo(4, -21.5); c.lineTo(4, 4); c.closePath(); });
    st(c, HI2, 1.3, () => { c.moveTo(-2.4, 2.5); c.lineTo(-3.5, -12.8); c.quadraticCurveTo(-3.3, -17.6, -0.2, -19.4); }, "butt");
    el(c, P.guard2, 0.2, 4.6, 6.6, 2.5);
    rr(c, M.grip, -2, 5.8, 4, 12, 1.4);
    if (!o.small) for (const y of [9, 12, 15]) f(c, "rgba(255,255,255,0.2)", () => { c.moveTo(-2, y); c.lineTo(2, y - 1.4); c.lineTo(2, y - 0.4); c.lineTo(-2, y + 1); c.closePath(); });
    donut(c, P.guard2, 0, 18.6, 3, 1.3);
  }
  /** 鋸齒巨劍：雙手劍的刃，一側切成三個大鋸齒（齒深是刃寬的四成，20px 還看得到缺口）；護手與長柄同雙手劍。 */
  function serratedArt(c, o, P) {
    poly(c, P.a, [[-5.6, 1.5], [-5.6, -16], [-0.8, -21.5], [4.2, -17.6], [8.6, -15], [4.2, -12.2], [8.6, -9.6], [4.2, -6.8], [8.6, -4.2], [4.2, -1.4], [4.2, 1.5]]);
    f(c, SH, () => c.rect(1.4, -17, 2.8, 18.5));
    f(c, HI2, () => c.rect(-4.4, -15.5, 1.5, 16));
    rr(c, P.d, -1.6, -15, 1.6, 15, 0.8);
    gsHilt(c, o, P);
  }
  const GREATSWORD = (r, P) => ({ d: (c, o) => up(c, (x) => (r.form === "zhanma" ? zhanmaArt : r.form === "serrated" ? serratedArt : W.greatswordArt)(x, o, P)) });

  // =====================================================================
  // 匕首（QW.dagger：三角短刃、深褐護手與握柄）。圖示把護手與柄頭畫成暗銅（和 qIcons.js 技能圖示裡的匕首同一把），深色裝備格上才看得到護手（規則 6）。
  // =====================================================================
  const dagHilt = (c, P, w = 14) => { rr(c, P.guard, -w / 2, 1, w, 3.6, 1.8); rr(c, M.grip, -2.1, 4.6, 4.2, 9.4, 1.2); ci(c, P.guard, 0, 16, 2.8); };
  /** 短刀：一片三角寬刃（根部最寬、直直收到尖，和人物手上那把同樣是三角形），橫護手。比單手劍短胖：劍是平行的長條刃，短刀是三角形、握柄和刃差不多長。 */
  function daggerShort(c, o, P) {
    poly(c, P.a, [[-4.7, 1.5], [0, -18], [4.7, 1.5]], 0.4);
    f(c, SH, () => { c.moveTo(0.8, 1.5); c.lineTo(0.8, -14.6); c.lineTo(4.7, 1.5); c.closePath(); });
    f(c, HI2, () => { c.moveTo(-3.7, 0.8); c.lineTo(-0.7, -11.6); c.lineTo(-0.7, 0.8); c.closePath(); });
    dagHilt(c, P);
  }
  /** 三稜刺：一根又細又長的錐（從根部一路收成針尖，中脊左亮右暗），圓盤小護手、細長握柄。剪影是針，不是葉。 */
  function daggerStiletto(c, o, P) {
    poly(c, P.a, [[-3, 2], [0, -21.5], [3, 2]]);
    f(c, SH, () => { c.moveTo(0, 2); c.lineTo(0, -21.5); c.lineTo(3, 2); c.closePath(); });
    f(c, HI2, () => { c.moveTo(-2, 1.5); c.lineTo(-0.5, -13); c.lineTo(-0.5, 1.5); c.closePath(); });
    el(c, P.guard, 0, 2.8, 5.4, 2.6);
    rr(c, M.grip, -1.8, 4.8, 3.6, 10, 1.2); ci(c, P.guard, 0, 16.6, 2.5);
  }
  /** 彎匕：刃只往一側彎一下再收回來，刃尖收尖、朝正前方；護手一邊長一邊短。
   *  第 2 版（審查必修 4）：第 1 版的刃左右擺三次，兩把交叉時像牛角／維京頭盔；改成一個彎、尖端收尖，單把與成對用同一把。 */
  function daggerKris(c, o, P) {
    const L = [], R = [], Cn = [], n = 16;
    for (let i = 0; i <= n; i++) { const t = i / n, y = 1.5 - t * 22.5, cx = -3 * Math.sin(Math.PI * Math.pow(t, 0.85)) ** 2, hw = 4.2 * Math.pow(1 - t, 0.85) + 0.2; L.push([cx - hw, y]); R.unshift([cx + hw, y]); Cn.push([cx, y]); }
    poly(c, P.a, [...L, ...R], 0.3);
    poly(c, SH, [...Cn, ...R]);
    st(c, HI2, 1.2, () => L.slice(0, 11).forEach(([x, y], i) => (i ? c.lineTo(x + 1.5, y) : c.moveTo(x + 1.5, y))), "butt");
    poly(c, P.guard, [[-8, 0.8], [6, -0.4], [5.4, 4.6], [-5.4, 4.6]], 0.8);
    rr(c, M.grip, -2.1, 4.6, 4.2, 9.4, 1.2); ci(c, P.guard, 0, 16, 2.8);
  }
  const DAGGER_ART = { short: daggerShort, stiletto: daggerStiletto, kris: daggerKris };
  /* 匕首本身比劍短（人物手上只有劍的一半長）；圖示裡放大到和其他武器差不多長，才撐得滿框（現行圖示也把匕首放大 1.5 倍）。 */
  const DAGGER = (r, P) => ({ d: (c, o) => up(c, (x) => { const k = r.form === "short" ? 1.1 : 1.05; x.translate(0, 0.4); x.scale(k, k); DAGGER_ART[r.form](x, o, P); }) });
  /** 成對武器：兩把交叉成 X（握把在下面兩角、作用端在上面兩角），前面那把自己包一圈外框。現行小圖示把雙匕首畫成單把（和匕首同一張），裝備圖示才畫兩把；Q 版兩種框都畫兩把。 */
  /* 第 2 版：畫法收到的 o 多兩個旗標——pair（成對裡的一把）、rear（後面那把；≤24px 時可以省零件，交叉處才不亂）。 */
  const crossed = (one) => ({ block: true, pairArt: true, d: (c, o) => { one(c, { ...o, pair: true, rear: true }, -1); halo(c, o, (x) => one(x, { ...o, pair: true }, 1)); } });
  /* 彎匕：第 2 版把交叉角收窄到 0.4 弧度（兩把的刃尖都朝上，不再往兩邊張開成牛角）；第 3 版改成並排，見下。 */
  /* 第 3 版（複審可修）：0.4 弧度時兩片彎刃同向靠攏、護手連成一條金帶，像兔耳或一顆牙。先試過「交叉角放回 0.6、兩片刃各自往外彎、護手錯開」，
     20px 仍黏成一塊（像王冠、M 字），所以照複審的備案改成兩把並排斜放、不交叉：兩把都是握把左下、刃尖右上（和單把彎匕同一個方向），沿垂直方向錯開 9.2 單位，後面那把在左上。短刀、三稜刺仍是 X 形。 */
  const DUAL_DAGGER = (r, P) => crossed((c, o, s) => { c.save();
    if (r.form === "kris") { const g = o.badge && o.small ? 5.8 : 4.6; c.translate(24 + s * g, 24 + s * g); c.rotate(Math.PI / 4); c.scale(0.98, 0.98); c.translate(0, 0.4); } /* 真 1 倍修正：圓章 ≤24px 兩把的間距再拉開（4.6 → 5.8 單位，約 1px），護手與彎刃不再擠成一團 */
    else { c.translate(24, 24.5); c.scale(s, 1); c.rotate(0.62); c.scale(1.12, 1.12); }
    DAGGER_ART[r.form](c, o, P); c.restore(); });

  // =====================================================================
  // 斧（QW.axe：木柄 #6a4420、單面斧刃在柄的一側）
  // =====================================================================
  const haft = (c, o, top, bottom = 20.5, wrap = true) => { rr(c, M.shaft, -1.9, top, 3.8, bottom - top, 1.4); if (!o.small) f(c, HI, () => c.rect(-1.1, top + 3, 0.8, bottom - top - 14)); if (wrap) { rr(c, M.grip, -2.5, bottom - 10.5, 5, 8, 1.2); rr(c, M.ironD, -2.8, bottom - 2.6, 5.6, 2.8, 1.2); } };
  /** 一片斧刃：s＝在柄的哪一側、k＝大小、y0＝斧刃中心高度。斧身包住柄（斧眼深一階），刃口一條亮面。 */
  function axeHead(c, P, s, k, y0, beard = 0) {
    f(c, P.a, () => { c.moveTo(-2.4 * s, y0 - 4.4); c.lineTo(2 * s, y0 - 4.4); c.quadraticCurveTo(7 * s * k, y0 - 5, 10.6 * s * k, y0 - 7.8 * k); c.quadraticCurveTo(15.4 * s * k, y0 + beard / 2, 10.6 * s * k, y0 + 7.8 * k + beard); c.quadraticCurveTo(7 * s * k, y0 + 5 + beard * 0.3, 2 * s, y0 + 4.4); c.lineTo(-2.4 * s, y0 + 4.4); c.closePath(); });
    f(c, HI2, () => { c.moveTo(10.6 * s * k, y0 - 7.8 * k); c.quadraticCurveTo(15.4 * s * k, y0 + beard / 2, 10.6 * s * k, y0 + 7.8 * k + beard); c.quadraticCurveTo(11.6 * s * k, y0 + beard / 2, 10.6 * s * k, y0 - 7.8 * k); c.closePath(); });
    f(c, P.d, () => c.rect(Math.min(-2.4 * s, 2.4 * s), y0 - 4.4, 4.8, 8.8));
  }
  const AXE = (r, P) => ({ d: (c, o) => up(c, (x) => {
    if (r.form === "battle") { haft(x, o, -18); poly(x, P.a, [[-1.5, -14.4], [-9.6, -10.2], [-1.5, -6]], 0.4); axeHead(x, P, 1, 1.04, -10.2, 1.6); } /* 第 2 版（審查可修）：拿掉柄頂的尖刺、只留背刺，20px 才不會和戟（斧刃＋頂尖）同一張 */
    else if (r.form === "double") { haft(x, o, -18.5); axeHead(x, P, -1, 0.92, -10.5); axeHead(x, P, 1, 0.92, -10.5); }
    else { haft(x, o, -17.5); axeHead(x, P, 1, 0.84, -10.6, 3); }
  }) });

  // =====================================================================
  // 錘（QW.hammer：木柄、方頭＋暗色橫帶；form: mace 是圓頭）
  // =====================================================================
  /** 釘頭錘：柄頂一顆鐵球，球外一圈八根短釘（暗一階），球上白色高光。剪影是帶刺的圓，和戰錘的長方塊分開。 */
  function maceArt(c, o, P) {
    haft(c, o, -8);
    poly(c, P.d, starPts(0, -12, 9, 6.2, 8), 0.3);
    ci(c, P.a, 0, -12, 6.6);
    f(c, SH, () => { c.arc(0, -12, 6.6, -0.2, Math.PI * 0.75); c.closePath(); });
    ci(c, HI2, -2.4, -14.4, 2);
    rr(c, P.d, -2.6, -6.6, 5.2, 2.6, 1);
  }
  /** 連枷：短柄、柄頂一個鐵環，兩節鐵鍊拉到斜上方一顆帶刺的鐵球。球不在柄的延長線上，和釘頭錘分開。 */
  /* 第 2 版（審查可修）：第 1 版的球緊貼柄頂，20px 鍊子不見、像歪掉的釘頭錘。柄往左移並縮短（不再伸到球那一頭），柄頂一個鐵箍，兩顆亮色鍊環橫拉出去，
     球垂在柄頂外側（45° 斜放後在柄頂的右下方）；柄和球之間留得出米色空隙。 */
  function flailArt(c, o, P) {
    c.save(); c.translate(-6.4, 0); haft(c, o, -9, 19.5); rr(c, P.d, -2.7, -11.4, 5.4, 4, 1.3); c.restore();
    ci(c, P.l, -1.2, -9.8, 2); ci(c, P.l, 2.9, -9.4, 2);
    poly(c, P.d, starPts(10.8, -7.4, 7.2, 4.9, 8, 0.3), 0.3);
    ci(c, P.a, 10.8, -7.4, 5.3);
    f(c, SH, () => { c.arc(10.8, -7.4, 5.3, -0.2, Math.PI * 0.75); c.closePath(); });
    ci(c, HI2, 8.8, -9.4, 1.9);
  }
  const HAMMER = (r, P) => ({ d: (c, o) => up(c, (x) => (r.form === "mace" ? maceArt : r.form === "flail" ? flailArt : W.hammerArt)(x, o, P)) });

  // =====================================================================
  // 矛（QW.spear：木桿、三角矛頭、暗銅箍；paperdoll 的 halberd 多一片斧刃、trident 多兩根側叉）
  // =====================================================================
  const pole = (c, o, top, col = M.shaft) => { rr(c, col, -1.5, top, 3, 21.5 - top, 1.2); if (!o.small) f(c, HI, () => c.rect(-0.9, top + 3, 0.7, 20)); };
  const SPEAR = (r, P) => ({ d: (c, o) => up(c, (x) => {
    const col = M.shaft; /* 桿一律木色（人物也是）；材質只換矛頭 */
    if (r.form === "halberd") {
      /* 第 2 版（審查可修）：頂尖加長（9 → 12.5）、斧刃縮小並往下移，剪影是「一根長尖＋旁邊一小片斧刃」，和戰斧（一大片斧刃、沒有頂尖）分開 */
      pole(x, o, -10, col);
      poly(x, P.a, [[0, -21.5], [2.7, -11], [0, -9], [-2.7, -11]], 0.3);
      f(x, HI2, () => { x.moveTo(-0.4, -19); x.lineTo(-1.7, -11.4); x.lineTo(-0.4, -10.4); x.closePath(); });
      f(x, P.a, () => { x.moveTo(1.2, -11.6); x.quadraticCurveTo(7.6, -14.4, 9.4, -3.4); x.quadraticCurveTo(5.4, -6.4, 1.2, -6); x.closePath(); });
      f(x, HI2, () => { x.moveTo(6.8, -11.2); x.quadraticCurveTo(9.4, -8.4, 9.4, -3.4); x.quadraticCurveTo(7.8, -7.8, 6.8, -11.2); x.closePath(); });
      poly(x, P.a, [[-1.2, -11], [-6.6, -8.8], [-1.2, -6.6]], 0.3);
      rr(x, M.brass, -2.5, -5.8, 5, 2.4, 1);
    } else if (r.form === "trident") {
      pole(x, o, -10, col);
      rr(x, P.a, -8.6, -12, 17.2, 3.4, 1.5);
      poly(x, P.a, [[0, -21.5], [2.2, -11], [-2.2, -11]], 0.3);
      for (const s of [-1, 1]) poly(x, P.a, [[s * 6.8, -19.4], [s * 8.8, -11], [s * 4.8, -11]], 0.3);
      f(x, HI2, () => { x.moveTo(-0.3, -19); x.lineTo(-1.4, -11.4); x.lineTo(-0.3, -11.4); x.closePath(); });
      rr(x, M.brass, -2.5, -8.8, 5, 2.4, 1);
    } else {
      pole(x, o, -10, col);
      poly(x, P.a, [[0, -21.5], [4.4, -14.6], [2.2, -9], [-2.2, -9], [-4.4, -14.6]], 0.4);
      f(x, SH, () => { x.moveTo(0, -21.5); x.lineTo(4.4, -14.6); x.lineTo(2.2, -9); x.lineTo(0, -9); x.closePath(); });
      f(x, HI2, () => { x.moveTo(-0.6, -18.6); x.lineTo(-3, -14.6); x.lineTo(-1.6, -11); x.lineTo(-0.6, -11); x.closePath(); });
      rr(x, M.brass, -2.6, -9.4, 5.2, 2.6, 1);
    }
  }) });

  // =====================================================================
  // 弓（QW.bow：一段圓弧的木弓臂、白弦、皮纏弓把）。短弓＝樣張第 3 版那把（弦在小尺寸改深色線）。
  // =====================================================================
  /* 第 2 版（審查必修 2）：三款的幾何都在 qIcons.js 的 BOW_FORM（W.bowGeo）——短弓＝半圓（兩端離中心 13.5、弓深 13.5）；長弓＝又長又淺的弧（18.5、12.8），弓梢換成骨色的弦扣；
     反曲弓＝弓把往後縮、兩邊各拱一下、弓梢反過來往外翹。三款都搭一支箭，圓章與裝備格同一個構圖；圓章裡的弦與箭桿是 post 的 1px 深褐線。 */
  const BOW = (r, P) => { const G = W.bowGeo(r.form), tip = r.form === "long" ? "#e9e3cf" : null; return { d: (c, o) => up(c, (x) => W.bowArt(x, o, P, G, tip)), post: (c, o) => up(c, (x) => W.bowString(x, o, G)) }; };

  // =====================================================================
  // 弩（QW.crossbow：木弩身 #7a5232、弩臂、弦、一支弩箭）
  // =====================================================================
  function crossbowArt(c, o, P, form) {
    const wide = form === "heavy" ? 16.4 : form === "repeater" ? 12.6 : 14.4, lw = form === "heavy" ? 5.2 : 3.8, py = -5.5;
    rr(c, WOOD, -2.3, -15, 4.6, 33, 1.6);
    poly(c, WOOD, [[-2.3, 8], [2.3, 8], [4, 19.6], [-4, 19.6]], 0.8);
    if (!o.small) f(c, WOODL, () => c.rect(-1.5, -3, 1, 20));
    if (!o.small) ln(c, "#e8e8e8", 1.4, [[-wide + 0.8, py + 0.6], [0, 1.5], [wide - 0.8, py + 0.6]]);
    ln(c, "#c8a070", 2, [[0, 1.5], [0, -15]]);
    st(c, P.a, lw, (x) => { x.moveTo(-wide, py); x.quadraticCurveTo(0, py - 12.5, wide, py); });
    if (!o.small) st(c, HI, 1, (x) => { x.moveTo(-wide + 3, py - 2.8); x.quadraticCurveTo(-wide * 0.45, py - 7.6, -1.5, py - 7.6); }, "butt");
    ci(c, P.d, -wide, py, lw * 0.55); ci(c, P.d, wide, py, lw * 0.55);
    poly(c, M.steel, [[-2.9, -15], [0, -21.5], [2.9, -15]], 0.3);
    if (form === "heavy") { /* 重弩：弩臂更寬更粗，尾端多一個上弦的絞盤（鐵輪＋搖柄） */
      ln(c, M.ironD, 2.2, [[0, 13], [7.4, 16.2]]); ci(c, GOLD, 7.4, 16.2, 2);
      ci(c, M.iron, 0, 13, 4.5); ci(c, M.ironD, 0, 13, 1.7); if (!o.small) ci(c, HI2, -1.6, 11.4, 1);
    } else if (form === "repeater") { /* 連弩：弩身上疊一個木箭匣，旁邊一根拉桿 */
      ln(c, M.ironD, 2.2, [[3, 2.5], [9.2, 9.8]]); ci(c, GOLD, 9.2, 9.8, 1.9);
      rr(c, "#96673c", -5.2, -13.6, 10.4, 13.6, 1.8); f(c, "#5e3b1f", () => c.rect(-5.2, -8.6, 10.4, 1.5));
      if (!o.small) { f(c, HI, () => c.rect(-4, -12.4, 1.2, 3)); f(c, "#5e3b1f", () => c.rect(-5.2, -4.4, 10.4, 1.1)); }
    } else rr(c, M.grip, -2.6, 9.5, 5.2, 5.5, 1.2);
  }
  const CROSSBOW = (r, P) => ({ d: (c, o) => up(c, (x) => crossbowArt(x, o, P, r.form)), post: (c, o) => { if (!o.small) return; const wide = r.form === "heavy" ? 16.4 : r.form === "repeater" ? 12.6 : 14.4; up(c, (x) => ln(x, "#2a1c14", 2.4, [[-wide + 1.4, -4.6], [0, 1.6], [wide - 1.4, -4.6]])); } });

  // =====================================================================
  // 火器（QW.gun：深色握把、木槍托 #7a5232、槍管用材質色、一道暗色箍；長度 rifle 17、shotgun 15、pistol 7）
  // =====================================================================
  const cock = (c, x, y) => poly(c, M.ironD, [[x, y], [x - 2.8, y - 5.2], [x + 1, y - 6.2], [x + 2.8, y]], 0.5); /* 燧發機的擊鎚 */
  const tguard = (c, o, x, y, col = GOLD, R = 2.9) => st(c, col, o.small ? 2 : 1.6, (k) => k.arc(x, y, R, 0, Math.PI), "butt");
  /** 燧發火槍：木槍托一路包到槍管下面，又長又細的槍管、兩道黃銅箍，機匣上一支翹起來的擊鎚。 */
  function gunFlint(c, o, P) {
    if (!o.small) tguard(c, o, -6, 1.8);
    f(c, WOOD, () => { c.moveTo(-20, -1.5); c.lineTo(-10.5, -4.6); c.lineTo(11, -3.6); c.lineTo(11, -0.4); c.lineTo(-8, 1.2); c.quadraticCurveTo(-13, 2, -20, 5.6); c.closePath(); });
    if (!o.small) f(c, WOODL, () => { c.moveTo(-19, -1); c.lineTo(-11, -3.6); c.lineTo(-11, -2.4); c.lineTo(-19, 0.2); c.closePath(); });
    rr(c, P.a, -9, -6.5, 28.8, 3.5, 1.4);
    f(c, HI2, () => c.rect(-7, -5.9, 24, 1));
    for (const x of [1, 9]) rr(c, GOLD, x, -7, 2.2, 6.6, 0.8);
    cock(c, -8.4, -5.6);
  }
  /** 獵槍：木槍托、一塊暗色機匣、槍管下一截短護木；沒有擊鎚、沒有瞄準鏡，三把長槍裡最素的一把。 */
  function gunHunting(c, o, P) {
    tguard(c, o, -4.6, 1.2, P.d);
    poly(c, WOOD, [[-20, -2.6], [-9.5, -5.2], [-8.5, 1.6], [-13, 2.2], [-20, 5.4]], 0.8);
    if (!o.small) f(c, WOODL, () => c.rect(-18.6, -2.4, 8, 1.2));
    rr(c, WOOD, 2, -2.8, 11.5, 3.6, 1.4);
    rr(c, P.a, 2, -6.2, 17.8, 3.8, 1.4); f(c, HI2, () => c.rect(3.5, -5.6, 14, 1));
    rr(c, P.d, -10, -6.8, 12.6, 7.8, 1.8); f(c, HI, () => c.rect(-8.6, -5.6, 9.6, 1.2));
  }
  /** 狙擊火槍：機匣上一支長瞄準鏡（深色鏡筒、前端一片青色鏡片）、槍管下一副兩腳架、槍口一塊制退器、金屬骨架槍托。 */
  function gunSniper(c, o, P) {
    ln(c, P.d, 2.2, [[11.5, -2.6], [8.4, 6.8]]); ln(c, P.d, 2.2, [[11.5, -2.6], [15.2, 6.8]]);
    poly(c, P.d, [[-20, -3.6], [-9.5, -5.2], [-8.5, 1.6], [-14.5, 1.6], [-16, 4.6], [-20, 5.2]], 0.6);
    rr(c, P.a, 4, -5.6, 13, 3.3, 1.2); rr(c, P.d, 15.6, -6.8, 3.9, 5.7, 1.2);
    rr(c, P.a, -10, -6.6, 14.5, 7.2, 1.6); f(c, HI2, () => c.rect(-8.6, -5.6, 11.4, 1.1));
    rr(c, "#4a5260", -4.4, -8.6, 2.2, 2.4, 0.4); rr(c, "#4a5260", 2, -8.6, 2.2, 2.4, 0.4);
    rr(c, "#4a5260", -8, -12.6, 16, 4.8, 2.2); if (!o.small) f(c, HI, () => c.rect(-6.4, -11.8, 10, 1));
    ci(c, "#8fe3ff", 7.2, -10.2, 2);
  }
  const LONGGUN = (r, P) => ({ d: (c, o) => gunF(c, (x) => (r.form === "hunting" ? gunHunting : r.form === "sniper" ? gunSniper : gunFlint)(x, o, P)) });
  /** 喇叭槍：槍管往槍口張開成喇叭、口上一圈深色的唇；燧發擊鎚、一道黃銅箍。 */
  function gunBlunder(c, o, P) {
    if (!o.small) tguard(c, o, -5.4, 2.6);
    poly(c, WOOD, [[-19.5, -2], [-8, -5.4], [-7, 2.4], [-12, 3], [-19.5, 6]], 0.9);
    f(c, P.a, () => { c.moveTo(-9, -6.2); c.lineTo(7, -5.2); c.quadraticCurveTo(12, -5.6, 16, -9.4); c.lineTo(16, 5.4); c.quadraticCurveTo(12, 1.6, 7, 1.2); c.lineTo(-9, 1.8); c.closePath(); });
    f(c, HI2, () => { c.moveTo(-7, -5.2); c.lineTo(7, -4.2); c.quadraticCurveTo(11.6, -4.6, 15, -7.4); c.lineTo(15, -5.6); c.quadraticCurveTo(11.6, -3.2, 7, -3); c.lineTo(-7, -4); c.closePath(); });
    rr(c, P.d, 15.2, -10.2, 3, 16.4, 1.4);
    rr(c, GOLD, -2, -6.5, 2.4, 8.6, 0.8);
    cock(c, -8.4, -5.4);
  }
  /** 雙管：上下兩根並排的粗槍管（中間一道暗縫）、槍口一圈箍、短木槍托、金色扳機護弓。和 qIcons.js「散彈驅離」裡那把同一把。 */
  function gunDouble(c, o, P) {
    tguard(c, o, -5.6, 5, GOLD, 3.2);
    poly(c, WOOD, [[-19.5, -2.2], [-8.5, -4.2], [-8.5, 4], [-13, 4.4], [-19.5, 7]], 1);
    if (!o.small) f(c, WOODL, () => c.rect(-18.5, -2.6, 9, 1.3));
    rr(c, P.d, -10, -5.6, 7.6, 11, 1.6);
    rr(c, P.a, -4, -5.2, 22.4, 10, 2); f(c, P.d, () => c.rect(-2.4, -0.8, 20.8, 1.5)); f(c, HI2, () => c.rect(-2, -4, 17, 1.3));
    rr(c, P.d, 15.8, -5.8, 2.8, 11.2, 1);
  }
  /** 泵動：一根槍管、下面一根彈倉管，套著一截淺色的木滑套（三道防滑紋）；槍托連著往下的握把。 */
  function gunPump(c, o, P) {
    poly(c, WOOD, [[-19.5, -2.6], [-9, -5], [-8, 0.5], [-11.6, 8], [-15.8, 6.6], [-13.6, 1.6], [-19.5, 3.6]], 0.8);
    rr(c, P.d, -10, -6.2, 9.5, 8.2, 1.6);
    rr(c, P.d, -1, -1.4, 16.5, 3.6, 1.4);
    rr(c, P.a, -1, -6.2, 20, 4.4, 1.6); f(c, HI2, () => c.rect(0.5, -5.4, 16, 1.1));
    rr(c, WOODL, 3.6, -2.6, 9.6, 6, 1.8); if (!o.small) for (const x of [5.8, 8, 10.2]) f(c, WOOD, () => c.rect(x, -1.6, 0.9, 4));
  }
  const SHOTGUN = (r, P) => ({ d: (c, o) => gunF(c, (x) => (r.form === "blunderbuss" ? gunBlunder : r.form === "pump" ? gunPump : gunDouble)(x, o, P)) });
  /** 燧發手槍：一整條往後下方彎的木握把（尾端一顆黃銅握把帽）、短槍管、槍管下一截護木、擊鎚。 */
  function pistolFlint(c, o, P) {
    if (!o.small) tguard(c, o, -1.2, 0.8, GOLD, 3);
    f(c, WOOD, () => { c.moveTo(-6, -5.5); c.lineTo(3, -5.5); c.lineTo(3, -0.5); c.quadraticCurveTo(-4, 0.5, -7.6, 10.4); c.lineTo(-13.6, 8); c.quadraticCurveTo(-11, -1, -6, -5.5); c.closePath(); });
    ci(c, GOLD, -10.8, 9.6, 3.3);
    rr(c, WOOD, 2, -3.4, 9.5, 3.2, 1.2);
    rr(c, P.a, -3, -8.2, 18, 5.2, 1.6); f(c, HI2, () => c.rect(-1, -7.4, 13, 1.2));
    rr(c, P.d, 13, -8.6, 2.5, 6, 1);
    cock(c, -5.4, -7.4);
  }
  /** 左輪：槍管、槍身中間一顆暗色的轉輪（兩道亮槽）、斜向後下方的木握把、擊鎚、扳機護弓、槍口一顆準星。 */
  function pistolRevolver(c, o, P) {
    const lite = o.small && o.rear; /* 第 2 版（審查可修）：成對時後面那把在 ≤24px 省掉轉輪與扳機護弓（只剩槍管、槍身、握把、擊鎚），交叉處不再擠兩顆轉輪 */
    if (!lite) st(c, P.d, o.small ? 2.1 : 1.7, (x) => x.arc(-0.2, 1.8, 3.3, 0, Math.PI), "butt");
    poly(c, WOOD, [[-9, -3.5], [-2.5, -1.5], [-6.5, 12], [-13.5, 9.5]], 1.4);
    if (!o.small) f(c, WOODL, () => { c.moveTo(-9.4, -1.6); c.lineTo(-7.6, -1); c.lineTo(-11.6, 9); c.lineTo(-13, 8.4); c.closePath(); });
    rr(c, P.a, 0, -8.4, 15.5, 5, 1.6); f(c, HI2, () => c.rect(1.5, -7.6, 11, 1.1));
    rr(c, P.a, -10, -8.8, 12, 4.2, 1.4);
    if (lite) rr(c, P.a, -6.8, -8.8, 9, 7.4, 2);
    else if (o.small && o.pair && o.badge) { rr(c, P.d, -7.8, -10.6, 11, 12.4, 3.4); f(c, HI2, () => c.rect(-6, -7.6, 7.4, 1.8)); f(c, mix(P.d, "#000000", 0.35), () => c.rect(-6, -3.4, 7.4, 1.8)); } /* 真 1 倍修正：圓章裡成對的前面那把在 ≤24px 轉輪放大、一道亮槽一道暗槽，交叉處才看得出是轉輪 */
    else { rr(c, P.d, -6.8, -9.8, 9, 10.8, 3); f(c, HI, () => c.rect(-5.4, -6.8, 6.2, o.small ? 1.5 : 1.1)); if (!o.small) f(c, HI, () => c.rect(-5.4, -3, 6.2, 1.1)); }
    poly(c, P.d, [[-9.6, -8], [-12.6, -11], [-10.2, -12.2], [-7.6, -9]], 0.4);
    rr(c, P.d, 13.4, -10.6, 1.9, 2.8, 0.6);
  }
  /** 短銃：上下兩根疊著的短槍管、後面一塊金色的槍身、一顆圓圓的鳥頭木握把；三把手槍裡最短最胖。 */
  /* 第 2 版（審查可修）：握把改成往後下方彎的鳥頭形（尾端一顆圓頭），弧度比第 1 版的斜方塊明顯；成對而且 ≤24px 時槍管加長（17 → 21），20px 才看得出是槍管。 */
  function pistolDerringer(c, o, P) {
    const L = o.pair && o.small ? 21 : 17;
    if (!o.small) tguard(c, o, -1.4, 2.6, GOLD, 2.7);
    f(c, WOOD, () => { c.moveTo(-8.8, -2.6); c.lineTo(-2.6, -0.8); c.quadraticCurveTo(-1.8, 4.4, -5, 7.6); c.quadraticCurveTo(-6.8, 11.6, -10.6, 11); c.quadraticCurveTo(-14, 10, -12.6, 6.4); c.quadraticCurveTo(-10.4, 3, -10.6, -1.4); c.closePath(); });
    if (!o.small) st(c, WOODL, 1.1, (x) => { x.moveTo(-9.4, 0.6); x.quadraticCurveTo(-9.4, 3.6, -11.2, 6.6); }, "butt");
    rr(c, P.a, -4, -9.2, L, 4.8, 1.4); rr(c, P.a, -4, -4.2, L, 4.8, 1.4);
    f(c, HI2, () => c.rect(-2, -8.4, L - 5, 1.1)); f(c, SH, () => c.rect(-4, -1.6, L, 2.2));
    rr(c, GOLD, -9.6, -9.8, 6.8, 11.2, 1.8); if (!o.small) f(c, "#fff0b0", () => c.rect(-8.5, -8.6, 1.2, 8));
  }
  const PISTOL_ART = { flintlock: [pistolFlint, 1.16, -0.6, -0.4], revolver: [pistolRevolver, 1.14, -0.4, -0.2], derringer: [pistolDerringer, 1.36, -1.6, -0.6] };
  const PISTOL = (r, P) => { const [fn, k, ox, oy] = PISTOL_ART[r.form]; return { block: true, d: (c, o) => gunF(c, (x) => fn(x, o, P), -0.42, k, ox, oy) }; };
  /* 雙手槍：兩把同款手槍交叉成 X（握把在下面兩角、槍口各朝左上與右上），兩把的中心左右拉開 15 單位，交叉點落在槍管上、握把各自分開。右邊那把在前面，自己包一圈外框。 */
  const DUAL_PISTOL = (r, P) => { const [fn] = PISTOL_ART[r.form], k = r.form === "derringer" ? 1.12 : r.form === "revolver" ? 0.96 : 1, dx = r.form === "derringer" ? 8 : 7.5; return crossed((c, o, s) => { c.save(); c.translate(24 + s * dx, 26.5); c.scale(s, 1); c.rotate(-1.02); c.scale(k, k); c.translate(1, 1.5); fn(c, o, P); c.restore(); }); };

  // =====================================================================
  // 拳套（qDoll.js 的 glove()：包住拳頭的圓拳、深一階的護腕與指節板；katar、claw 從指節往前伸出刃）。鐵拳與爪直立、指節朝上；拳刃第 3 版改成 45° 斜放。
  // =====================================================================
  const fistBase = (c, o, P, y) => { rr(c, P.headD, 15, y + 11.5, 18, 8.5, 3); rr(c, P.head, 9.5, y, 29, 13.5, 6.4); f(c, P.headD, () => c.roundRect(10.5, y - 1.6, 27, 3.8, 1.6)); for (let i = 0; i < 4; i++) f(c, i ? HI : HI2, () => c.roundRect(12.6 + i * 6.3, y + 3.6, 3.6, 1.8, 0.9)); };
  /** 拳刃：45° 斜放的側面（握把端在左下、刃尖在右上，和現行裝備圖示、人物手上同一個方向；規則 12）。直立座標：刃尖 −y、護腕 +y。
   *  一片寬三角刃（中脊左亮右暗）從指節往前伸，刃根一條橫檔，橫檔兩端各一根往後的側桿夾在拳頭兩邊；拳頭（材質色、一排指節）握在兩根側桿中間，後面是深一階的護腕。
   *  第 3 版（複審必修 2）：第 2 版是直立的正面（三角刃＋H 形握架＋縮小的鐵拳），所有尺寸都像戴尖帽的臉、小亭子，比現行難認。鐵拳與爪仍直立。 */
  function katarArt(c, o, P) {
    for (const s of [-1, 1]) rr(c, P.headD, s * 8.6 - 1.6, -1.6, 3.2, 17.2, 1.5);
    poly(c, P.a, [[-7, 0.4], [0, -20.6], [7, 0.4]], 0.7);
    f(c, SH, () => { c.moveTo(0.6, 0.6); c.lineTo(0.6, -19.4); c.lineTo(7.4, 0.6); c.closePath(); });
    f(c, HI2, () => { c.moveTo(-5.4, -0.4); c.lineTo(-1, -14.4); c.lineTo(-1, -0.4); c.closePath(); });
    rr(c, P.headD, -10.2, -1.8, 20.4, 3.8, 1.4);
    rr(c, P.headD, -5, 12.4, 10, 8.6, 2.2);
    rr(c, P.head, -6.2, 3, 12.4, 11.2, 4.2);
    f(c, P.headD, () => c.roundRect(-5.4, 4, 10.8, 2.2, 1));
    for (let i = 0; i < 4; i++) f(c, i ? HI : HI2, () => c.roundRect(-4.9 + i * 2.6, 7.2, 1.9, 1.5, 0.7));
    if (!o.small) f(c, HI, () => c.rect(-3.6, 14.2, 1, 5.4));
  }
  /** 爪：拳頭上三根往同一邊彎的長爪（每根一條亮面）。剪影是三根尖。 */
  function clawArt(c, o, P) {
    for (const [x, lean] of [[14.6, -0.6], [24, 2.2], [33.4, 5]]) {
      f(c, P.a, () => { c.moveTo(x - 3.2, 26); c.quadraticCurveTo(x - 5, 13, x + lean + 2, 3.4); c.quadraticCurveTo(x + 2.4, 14, x + 3.2, 26); c.closePath(); });
      f(c, HI2, () => { c.moveTo(x - 1.8, 24); c.quadraticCurveTo(x - 3, 14, x + lean + 0.6, 7.6); c.quadraticCurveTo(x - 1.4, 15, x - 0.4, 24); c.closePath(); });
    }
    fistBase(c, o, P, 25);
  }
  const FIST = (r, P) => r.form === "katar" ? { diag: true, spots: SPOTS.diag, d: (c, o) => up(c, (x) => katarArt(x, o, P)) } /* 拳刃是 45° 斜放的長條：規則 7 照斜放算（門檻 60%）；圓章裡不套直立塊狀的 0.86 上限，由自動縮放決定；關鍵字小圖樣的位置用斜放那一組 */
    : ({ block: true, badge: 0.86, d: r.form === "claw" ? (c, o) => clawArt(c, o, P) : (c, o) => W.fistArt(c, o, P) });

  // =====================================================================
  // 鐮刀（QW.scythe：木柄、柄頂往一側彎出去的鐮刃）
  // =====================================================================
  const scytheBlade = (c, P, k = 1) => {
    f(c, P.a, () => { c.moveTo(-1.6, -18.6); c.quadraticCurveTo(9 * k, -22.6, 16.6 * k, -7.4); c.quadraticCurveTo(8.6 * k, -15.4, -1.6, -13.4); c.closePath(); });
    f(c, HI2, () => { c.moveTo(0.5, -18.2); c.quadraticCurveTo(8.6 * k, -20.6, 14.4 * k, -10.6); c.quadraticCurveTo(8.4 * k, -18.2, 0.5, -16.8); c.closePath(); });
  };
  const SCYTHE = (r, P) => ({ d: (c, o) => up(c, (x) => {
    if (r.form === "hook") { /* 鉤鐮：短柄（纏皮握把）＋一片彎成問號的鉤刃 */
      rr(x, M.shaft, -1.9, -4, 3.8, 24.5, 1.4); rr(x, M.grip, -2.5, 8, 5, 10, 1.2); rr(x, M.ironD, -2.8, 17.8, 5.6, 2.8, 1.2);
      f(x, P.a, () => { x.moveTo(-2.4, -3); x.bezierCurveTo(-4.6, -19, 13.4, -22.4, 15.6, -6.4); x.bezierCurveTo(11.6, -15.6, 3.4, -15, 2.4, -3); x.closePath(); });
      f(x, HI2, () => { x.moveTo(-0.6, -9); x.bezierCurveTo(0.4, -17.4, 10.6, -19, 13.6, -11.4); x.bezierCurveTo(9.6, -17, 2.4, -15.6, 1, -9); x.closePath(); });
      rr(x, M.brass, -2.6, -4.6, 5.2, 2.6, 1);
      return;
    }
    rr(x, M.shaft, -1.6, -19.5, 3.2, 41, 1.3); if (!o.small) f(x, HI, () => x.rect(-0.9, -10, 0.7, 26));
    if (r.form === "crescent") { /* 彎月鐮，第 2 版（審查必修 3）：第 1 版是主刃加一片反向短刃，所有尺寸都像十字鎬。改成一片超過半圓（220°）的大新月刃：
         月牙的一個尖角剛好包過柄頂、露在柄的另一側一點點，刃身往右上鼓出去，另一個尖角彎回來指向柄。沒有反向刃。 */
      const D = Math.PI / 180, O = [5, -9.2], R1 = 10.8, aA = 215 * D, aB = 75 * D, mid = 145 * D, half = 70 * D, dI = 4.4;
      const I = [O[0] + Math.cos(mid) * dI, O[1] + Math.sin(mid) * dI], R2 = Math.hypot(R1 * Math.sin(half), R1 * Math.cos(half) - dI);
      const A = [O[0] + Math.cos(aA) * R1, O[1] + Math.sin(aA) * R1], B = [O[0] + Math.cos(aB) * R1, O[1] + Math.sin(aB) * R1];
      const moon = (k) => { k.arc(O[0], O[1], R1, aA, aB + TAU); k.arc(I[0], I[1], R2, Math.atan2(B[1] - I[1], B[0] - I[0]), Math.atan2(A[1] - I[1], A[0] - I[0]), true); k.closePath(); };
      f(x, P.a, moon);
      x.save(); x.beginPath(); moon(x); x.clip(); st(x, HI2, 2, (k) => k.arc(I[0], I[1], R2 + 0.6, -Math.PI * 0.62, Math.PI * 0.2), "butt"); st(x, SH, 2.2, (k) => k.arc(O[0], O[1], R1 - 0.8, -Math.PI * 0.45, Math.PI * 0.35), "butt"); x.restore();
      rr(x, M.brass, -2.5, -13.4, 5, 2.4, 1);
      return;
    }
    scytheBlade(x, P);
    rr(x, M.brass, -2.5, -13.2, 5, 2.4, 1);
  }) });

  // =====================================================================
  // 鞭（QW.whip：深褐握柄、皮色鞭身）。握柄在左下，鞭身繞一圈甩到右上。鞭身畫成粗條（線寬 ≥ 顯示邊長的 8%），不是細線。
  // =====================================================================
  const WHIP_SEG = [[[17, 31.5], [22.5, 26], [9, 21], [12.4, 13.4]], [[12.4, 13.4], [15, 6.4], [26.6, 6], [28, 14.4]], [[28, 14.4], [29.4, 22.6], [38, 22], [41, 10.6]]];
  const bez = ([p0, p1, p2, p3], t) => { const u = 1 - t, a = u * u * u, b = 3 * u * u * t, d = 3 * u * t * t, e = t * t * t; return [a * p0[0] + b * p1[0] + d * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + d * p2[1] + e * p3[1]]; };
  /** 沿鞭身每隔 step 單位取一點：[x, y, 切線角, 走了多遠 0～1]。 */
  function whipPts(step) {
    const dense = []; for (const s of WHIP_SEG) for (let i = 0; i < 40; i++) dense.push(bez(s, i / 40)); dense.push(WHIP_SEG[2][3]);
    let acc = 0, next = 0; const out = [], len = dense.reduce((n, p, i) => (i ? n + Math.hypot(p[0] - dense[i - 1][0], p[1] - dense[i - 1][1]) : 0), 0);
    for (let i = 1; i < dense.length; i++) { const d = Math.hypot(dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]); acc += d; if (acc >= next) { out.push([dense[i][0], dense[i][1], Math.atan2(dense[i][1] - dense[i - 1][1], dense[i][0] - dense[i - 1][0]), acc / len]); next += step; } }
    return out;
  }
  const whipPath = (c, from = 0, to = 3) => { c.moveTo(...WHIP_SEG[from][0]); for (let i = from; i < to; i++) c.bezierCurveTo(...WHIP_SEG[i][1], ...WHIP_SEG[i][2], ...WHIP_SEG[i][3]); };
  const whipHandle = (c, o, P) => { ln(c, M.grip, 5.4, [[10.4, 38.2], [16.6, 32]]); ci(c, P.guard, 9.4, 39.2, 3); ci(c, P.guard, 17, 31.5, 2.9); if (!o.small) ln(c, "rgba(255,255,255,0.22)", 1, [[11, 36], [14.6, 32.4]]); };
  /** 米色圓章裡（20／24／28px）的鞭：盤成一捲。第 1 版的 S 形在圓章 20px 加上外框就是一條蟲；裝備格（32px 以上）仍是 S 形。
   *  第 3 版（複審必修 1）：第 2 版是「粗圓環＋大米色洞＋沿半徑伸出的直柄」，像放大鏡（和事件卡的放大鏡、權杖撞圖）。改成：
   *  握柄照舊在左下、鞭梢照舊甩到右上（和裝備格的 S 形同一個方向），中間那一段盤成不留洞的一捲（一條螺旋暗線，看得出繞了兩三圈）掛在鞭身的右下側；
   *  握柄的延長線是繩捲的切線、不指向圓心，握柄與繩捲之間露一小段鞭身；鞭梢從繩捲甩出圈外一長段（超過圓章直徑的 1/4）。
   *  皮鞭＝皮色繩捲、梢端米白；鏈鞭＝一圈一圈的鏈節、梢端菱形墜；蛇骨鞭＝同一個繩捲（暗色的索），刃片只在甩出圈外那一段、梢端一片大矛頭。 */
  const COIL = { x: 30.2, y: 30.2, R: 9.5, T: [23.5, 23.5] };
  const COIL_TAIL = { leather: [[23.5, 23.5], [28.5, 18.5], [30.5, 8], [40, 12.4]], chain: [[23.5, 23.5], [28.5, 18.5], [30, 10], [37.6, 12.4]], bladed: [[23.5, 23.5], [27.5, 19.5], [28.4, 14.6], [32.6, 13.4]] };
  const tailAt = (S, t) => { const [x, y] = bez(S, t), a = bez(S, Math.max(0, t - 0.03)), b = bez(S, Math.min(1, t + 0.03)); return [x, y, Math.atan2(b[1] - a[1], b[0] - a[0])]; };
  const tailPath = (k, S) => { k.moveTo(...S[0]); k.bezierCurveTo(...S[1], ...S[2], ...S[3]); };
  /** 螺旋暗線：從繩捲外緣（鞭身碰到繩捲的切點）往裡繞 turns 圈。 */
  const coilSpiral = (k, turns) => { const a0 = Math.atan2(COIL.T[1] - COIL.y, COIL.T[0] - COIL.x), n = Math.ceil(turns * 48), pitch = COIL.R / (turns + 0.25); for (let i = 0; i <= n; i++) { const a = a0 + (i / 48) * TAU, q = COIL.R - pitch * (i / 48), x = COIL.x + Math.cos(a) * q, y = COIL.y + Math.sin(a) * q; if (i) k.lineTo(x, y); else k.moveTo(x, y); } };
  const tipBlade = (c, P, S, len, hw) => { const [tx, ty, ta] = tailAt(S, 1); c.save(); c.translate(tx, ty); c.rotate(ta); poly(c, P.a, [[-2.6, -hw], [len, 0], [-2.6, hw]], 0.4); f(c, HI2, () => { c.moveTo(-2, -hw + 0.8); c.lineTo(len - 2, 0); c.lineTo(-2, 0); c.closePath(); }); c.restore(); };
  const COIL_GRIP = [[10.6, 36.4], [16.2, 30.8]];
  function whipCoil(c, o, r, P) {
    const { x: X, y: Y, R, T } = COIL, S = COIL_TAIL[r.form] ?? COIL_TAIL.leather;
    if (r.form === "chain") {
      const dark = mix(P.d, "#000000", 0.45), rings = o.small ? [[R - 2.3, 10, 2.7, 2.3], [R - 6.4, 4, 2.4, 2.2]] : [[R - 2, 12, 2.4, 2], [R - 5.6, 7, 2.1, 1.8], [0, 1, 1.6, 1.6]];
      [[19.8, 27.2, 0], ...[0.2, 0.44, 0.68].map((t, i) => [...tailAt(S, t).slice(0, 2), i + 1, tailAt(S, t)[2]])].forEach(([x, y, i, a = -Math.PI / 4]) => el(c, i % 2 ? P.d : P.l, x, y, 2.9, 2.2, a));
      const [tx, ty, ta] = tailAt(S, 1); c.save(); c.translate(tx, ty); c.rotate(ta); poly(c, P.a, [[-1.6, -3.4], [5.8, 0], [-1.6, 3.4], [-3.6, 0]], 0.4); f(c, HI2, () => { c.moveTo(-1.2, -2.5); c.lineTo(4, 0); c.lineTo(-1.2, 0); c.closePath(); }); c.restore();
      ci(c, dark, X, Y, R);
      rings.forEach(([q, n, rx, ry], j) => { for (let i = 0; i < n; i++) { const a = (i / n) * TAU + j * 0.5; el(c, (i + j) % 2 ? P.d : P.l, X + Math.cos(a) * q, Y + Math.sin(a) * q, rx, ry, a + Math.PI / 2); } });
    } else {
      const bladed = r.form === "bladed", rope = bladed ? P.d : P.a, dark = mix(P.d, "#000000", bladed ? 0.55 : 0.35);
      ln(c, rope, 3, [COIL_GRIP[1], T]);
      st(c, rope, o.small ? 4 : 3.2, (k) => tailPath(k, S));
      if (bladed) { for (const t of [0.42, 0.8]) { const [x, y, a] = tailAt(S, t); c.save(); c.translate(x, y); c.rotate(a); poly(c, P.a, [[-2.6, -3.5], [3.8, 0], [-2.6, 3.5]], 0.3); f(c, HI2, () => { c.moveTo(-2, -2.6); c.lineTo(2.4, 0); c.lineTo(-2, 0); c.closePath(); }); c.restore(); } tipBlade(c, P, S, 8.8, 4.5); }
      else { const [x1, y1] = bez(S, 0.8); ln(c, CREAM, o.small ? 3 : 2.4, [[x1, y1], S[3]]); }
      ci(c, rope, X, Y, R);
      if (o.small) { /* 真 1 倍修正：20、24px 的繩捲半徑只有 4px，螺旋暗線繞不出來、和繩捲黏成一塊；改成一道粗的淺色弧（外圈）＋一小段暗弧（內圈），看得出「捲起來的繩」 */
        st(c, mix(rope, "#ffffff", 0.5), 2.6, (k) => k.arc(X, Y, R - 2.2, Math.PI * 0.95, Math.PI * 1.95), "butt");
        st(c, dark, 2.4, (k) => k.arc(X, Y, R - 5.4, Math.PI * 0.1, Math.PI * 1.25), "butt");
      } else {
        st(c, dark, 1.5, (k) => coilSpiral(k, 2.5), "butt");
        st(c, mix(rope, "#ffffff", bladed ? 0.3 : 0.38), 1.2, (k) => k.arc(X, Y, R - 1.3, Math.PI * 1.3, Math.PI * 1.75), "butt");
      }
    }
    ln(c, M.grip, 5.4, COIL_GRIP); ci(c, P.guard, COIL_GRIP[0][0] - 0.6, COIL_GRIP[0][1] + 0.6, 3); ci(c, P.guard, COIL_GRIP[1][0] + 0.4, COIL_GRIP[1][1] - 0.4, 2.9); if (!o.small) ln(c, "rgba(255,255,255,0.22)", 1, [[11.4, 34], [14.4, 31]]);
  }
  const WHIP = (r, P) => ({ d: (c, o) => {
    if (o.badge) { whipCoil(c, o, r, P); return; }
    if (r.form === "chain") { /* 鏈鞭：一節一節的鏈環（亮暗交替；第 2 版暗節再暗一階，銀、骨材質才不會整條變白），梢端一顆菱形的鐵墜 */
      const pts = whipPts(3.5);
      pts.forEach(([x, y, a], i) => el(c, i % 2 ? P.d : P.l, x, y, o.small ? 2.5 : 2.9, o.small ? 1.7 : 2.1, a));
      const [tx, ty, ta] = pts[pts.length - 1]; c.save(); c.translate(tx, ty); c.rotate(ta); poly(c, P.a, [[0, -3.6], [6.4, 0], [0, 3.6], [-2.4, 0]], 0.4); f(c, HI2, () => { c.moveTo(0, -2.6); c.lineTo(4.4, 0); c.lineTo(0, 0); c.closePath(); }); c.restore();
    } else if (r.form === "bladed") { /* 蛇骨鞭：一條暗色的索，上面一節一節朝前的三角刃片，梢端一片大的矛頭刃 */
      st(c, P.d, o.small ? 2 : 2.6, (x) => whipPath(x));
      /* 真 1 倍修正（補查可修）：原本整條每 5.2 單位一片小刃片（半寬 3.4），裝備格 32px 真 1 倍幾乎全被外框吃掉、和鏈鞭只差顏色。
         改成只在甩出去的後半段放四片大刃片（半寬 4.6、長 7.6），握柄那半段是光的索。 */
      const pts = whipPts(5.6);
      pts.slice(1, -1).filter((p) => p[3] >= 0.42).forEach(([x, y, a]) => { c.save(); c.translate(x, y); c.rotate(a); poly(c, P.a, [[-3, -4.6], [4.6, 0], [-3, 4.6]], 0.3); f(c, HI2, () => { c.moveTo(-2.3, -3.5); c.lineTo(3, 0); c.lineTo(-2.3, 0); c.closePath(); }); c.restore(); });
      const [tx, ty, ta] = pts[pts.length - 1]; c.save(); c.translate(tx, ty); c.rotate(ta); poly(c, P.a, [[-3, -3.8], [6.6, 0], [-3, 3.8]], 0.4); f(c, HI2, () => { c.moveTo(-2.4, -3); c.lineTo(4.6, 0); c.lineTo(-2.4, 0); c.closePath(); }); c.restore();
    } else { /* 皮鞭：一條粗皮繩繞一圈、越到梢端越細，梢端一小撮淺色的鞭梢 */
      st(c, P.a, o.small ? 2.6 : 3, (x) => whipPath(x)); st(c, P.a, o.small ? 3.4 : 4.4, (x) => whipPath(x, 0, 2)); /* ≤24px 收細，外框加上去才不會胖成一條蟲 */
      st(c, mix(P.a, "#ffffff", 0.38), 1.2, (x) => { x.moveTo(17.4, 29.6); x.bezierCurveTo(21.4, 25.6, 8.4, 20.6, 11.6, 13); x.bezierCurveTo(14.4, 5.4, 26, 5, 27.4, 13.6); }, "butt");
      ln(c, CREAM, 2.2, [[41, 10.6], [42.4, 6.4]]);
    }
    whipHandle(c, o, P);
  } });

  // =====================================================================
  // 杖（QW.staff：木杖身 #6a4420、杖頭一顆元素色光球、左上白色高光）。長杖＝樣張第 3 版那把（光球色＝元素色，沒有元素是 #c8bcff）。
  // =====================================================================
  const orbPair = (P) => Q.EL[P.orbEl] ?? [P.orb, "#ffffff"];
  /** 權杖：單手拿的短杖，杖頭是一個金環、環裡嵌一顆菱形寶石（寶石色＝元素色）；杖身兩道金箍、杖尾一顆金球。剪影是環，不是球。 */
  function scepterArt(c, o, P) {
    const [e1] = orbPair(P);
    rr(c, P.shaft, -1.6, -5, 3.2, 22, 1.2); if (!o.small) f(c, HI, () => c.rect(-0.9, -2, 0.7, 16));
    ci(c, GOLD, 0, 18, 2.7);
    rr(c, GOLD, -2.6, 6.6, 5.2, 2.4, 1); poly(c, GOLD, [[-4.4, -6.6], [4.4, -6.6], [2.2, -3.4], [-2.2, -3.4]], 0.5);
    donut(c, GOLD, 0, -13, 8, 4.6);
    if (!o.small) st(c, GOLDL, 1.1, (x) => x.arc(0, -13, 6.9, Math.PI * 0.95, Math.PI * 1.6), "butt");
    poly(c, e1, [[0, -19], [4.6, -13], [0, -7], [-4.6, -13]], 0.4);
    poly(c, HI2, [[0, -18], [0, -13], [-3.4, -13]]);
  }
  /** 短杖：一根握把粗、往前收細的小木杖（握把兩道金箍），杖尖一顆小光球。比長杖短、杖身粗細有變化、球小一半。 */
  function wandArt(c, o, P) {
    const [e1] = orbPair(P);
    poly(c, P.shaft, [[-2.6, 17], [-1.3, -10], [1.3, -10], [2.6, 17]], 0.8);
    if (!o.small) f(c, HI, () => { c.moveTo(-1.6, 14); c.lineTo(-0.7, -8); c.lineTo(-0.1, -8); c.lineTo(-0.7, 14); c.closePath(); });
    rr(c, GOLD, -3.4, 4.4, 6.8, 2.6, 1.1); rr(c, GOLD, -3.6, 14.4, 7.2, 2.8, 1.2);
    rr(c, GOLD, -2.2, -11.6, 4.4, 2.6, 1);
    ci(c, e1, 0, -15.6, 4.9); ci(c, HI2, -1.8, -17.4, 1.3);
  }
  /** 圖騰杖：杖頭是一截木雕圖騰——上下兩張臉（紅、青色的額帶，米白方眼），兩側各一片羽毛，頂上一顆小綠珠。和 qIcons.js「立起圖騰」的柱子同一種雕法。 */
  function totemArt(c, o, P) {
    rr(c, P.shaft, -1.7, -2, 3.4, 23.5, 1.3); if (!o.small) f(c, HI, () => c.rect(-0.9, 1, 0.7, 16));
    for (const s of [-1, 1]) poly(c, "#e9e3cf", [[s * 5, -14.6], [s * 11.6, -16.6], [s * 11.2, -9.6], [s * 5, -9.6]], 0.6);
    if (!o.small) for (const s of [-1, 1]) f(c, "#c0392b", () => { c.moveTo(s * 9.6, -16.6); c.lineTo(s * 12, -17.2); c.lineTo(s * 11.8, -13.6); c.lineTo(s * 9.6, -13.4); c.closePath(); });
    rr(c, M.wood, -5.6, -17, 11.2, 16, 2.2);
    f(c, "#b98048", () => c.roundRect(-5.6, -17, 3, 16, [2.2, 0, 0, 2.2]));
    f(c, "#c0392b", () => c.rect(-5.6, -15.4, 11.2, 2)); f(c, "#3a8a8a", () => c.rect(-5.6, -8.2, 11.2, 2));
    f(c, M.woodD, () => c.rect(-5.6, -9.6, 11.2, 1.2));
    for (const y of [-12.6, -5.4]) { rr(c, "#fff6c8", -3.8, y, 2.6, 2.6, 0.6); rr(c, "#fff6c8", 1.2, y, 2.6, 2.6, 0.6); }
    ci(c, P.orbEl ? orbPair(P)[0] : "#7dffb0", 0, -18.4, 2.5);
  }
  const STAFF = (r, P) => {
    const [e1] = orbPair(P), head = r.form === "scepter" ? R45(0, -13) : r.form === "wand" ? R45(0, -15.6) : R45(0, -13.6);
    if (r.form === "totem") return { d: (c, o) => up(c, (x) => totemArt(x, o, P)) };
    const art = r.form === "scepter" ? (x, o) => scepterArt(x, o, P) : r.form === "wand" ? (x, o) => wandArt(x, o, P) : W.staffArt(P.orbEl, P);
    return { d: (c, o) => up(c, (x) => art(x, o)), pre: (c) => glow(c, head[0], head[1], r.form === "wand" ? 9 : 12, e1, 0.6),
      post: r.form === "wand" ? (c, o) => { if (!o.small) { sparkle(c, "#ffffff", head[0] + 6.4, head[1] - 5.4, 2.4); sparkle(c, "#ffffff", head[0] - 7.4, head[1] - 1.4, 1.8); } } : undefined };
  };

  // =====================================================================
  // 副手：圓盾、鳶盾／塔盾（paperdoll.js drawWeapon／drawWeapon2 的 shield_round、shield_kite）、法書（tome）、法器珠（QW.orb）。全部直立。
  // =====================================================================
  /** 木圓盾：深木色的邊、木色盾面（兩道木板縫）、正中一顆金色盾心（人物手上是同一顆金盾心）。包鐵圓盾：盾邊換成一圈鋼箍（八顆鉚釘）、盾面一個鐵十字箍、鋼盾心。 */
  function roundShield(c, o, P, banded) {
    ci(c, banded ? M.steel : mix(P.a, "#ffffff", 0.36), 24, 24, 20); /* 第 2 版（審查可修）：木圓盾的邊從深木色改成淺木色（人物手上那面的邊是亮的）；鋼邊留給包鐵圓盾，兩款才分得開 */
    if (!banded) st(c, P.d, 1, (x) => x.arc(24, 24, 16.9, 0, TAU), "butt");
    ci(c, P.a, 24, 24, banded ? 15.6 : 16.4);
    c.save(); c.beginPath(); c.arc(24, 24, banded ? 15.6 : 16.4, 0, TAU); c.clip();
    f(c, mix(P.a, "#ffffff", 0.2), () => c.rect(6, 6, 10, 36)); f(c, SH, () => c.rect(32.5, 6, 10, 36));
    if (!banded && !o.small) for (const x of [17.4, 30]) f(c, P.d, () => c.rect(x, 6, 1.3, 36));
    if (banded) { f(c, M.iron, () => c.rect(21.4, 6, 5.2, 36)); f(c, M.iron, () => c.rect(6, 21.4, 36, 5.2)); }
    c.restore();
    if (banded) { st(c, M.steelD, 1.2, (x) => x.arc(24, 24, 15.9, 0.2, Math.PI * 0.8), "butt"); if (!o.small) for (let i = 0; i < 8; i++) ci(c, M.ironD, 24 + Math.cos((i + 0.5) * TAU / 8) * 17.8, 24 + Math.sin((i + 0.5) * TAU / 8) * 17.8, 1.1); st(c, HI2, 1.2, (x) => x.arc(24, 24, 18.6, Math.PI * 1.05, Math.PI * 1.45), "butt"); }
    ci(c, banded ? M.steel : GOLD, 24, 24, banded ? 5.6 : 5.2); ci(c, banded ? M.steelD : "#b8862a", 24, 24, banded ? 2.2 : 0); ci(c, HI2, 22.4, 22.2, 1.5);
  }
  /** 鳶盾：平頂、兩肩直下、尖底；深一階的邊、盾面、一個米白十字（直紋＋橫紋），和人物手上那面同樣的零件。 */
  function kiteShield(c, o, P) {
    const K = (k) => [[24 - 15 * k, 24.5 - 19 * k], [24 + 15 * k, 24.5 - 19 * k], [24 + 14 * k, 24.5 + 4.5 * k], [24, 24.5 + 19.5 * k], [24 - 14 * k, 24.5 + 4.5 * k]];
    poly(c, P.d, K(1), 1.4); poly(c, P.a, K(0.74), 0.8);
    c.save(); c.beginPath(); K(0.78).forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.closePath(); c.clip();
    f(c, mix(P.a, "#ffffff", 0.22), () => c.rect(0, 0, 17.4, 48)); f(c, SH, () => c.rect(30.6, 0, 18, 48)); c.restore();
    rr(c, CREAM, 22, 10.5, 4, 26.5, 1); rr(c, CREAM, 13.6, 16.6, 20.8, 4, 1);
    if (!o.small) f(c, "#ffffff", () => c.rect(22.7, 11.4, 1, 24.6));
  }
  /** 典籍：一本闔著的厚書——材質色的封面、左邊深一階的書脊、右邊與下面露出米白的書頁、封面正中一枚金色圓章（中間一顆寶石，色＝關鍵字色）、右邊兩個金書角、底下垂一條紅書籤。 */
  function tomeBook(c, o, P) {
    rr(c, "#f2ead6", 12, 8.6, 28.6, 34.4, 2.4);
    if (!o.small) for (const y of [36.6, 39]) f(c, "#c8bc9c", () => c.rect(14, y, 25.6, 0.8));
    rr(c, "#c0392b", 28.6, 38, 3.6, 7.4, 1);
    rr(c, P.a, 8, 5, 28.6, 34.6, 2.6);
    f(c, P.d, () => c.roundRect(8, 5, 5, 34.6, [2.6, 0, 0, 2.6]));
    f(c, mix(P.a, "#ffffff", 0.22), () => c.rect(14.4, 6.6, 2, 31.4));
    if (!o.small) { poly(c, GOLD, [[36.6, 5], [36.6, 11], [30.6, 5]], 0.3); poly(c, GOLD, [[36.6, 39.6], [36.6, 33.6], [30.6, 39.6]], 0.3); }
    ci(c, GOLD, 24.6, 22.2, 6.2); poly(c, P.accent, [[24.6, 17.8], [28.4, 22.2], [24.6, 26.6], [20.8, 22.2]], 0.3); poly(c, HI2, [[24.6, 18.6], [24.6, 22.2], [21.8, 22.2]]);
  }
  /** 卷軸匣：一支直立的圓筒匣（材質色）、上下各一道金箍與筒蓋，筒身側邊拉出一截米白的卷軸紙（兩行字），筒身正中一顆寶石。 */
  function tomeScroll(c, o, P) {
    poly(c, "#f2ead6", [[29, 15.6], [42, 19], [42, 32], [29, 29.4]], 0.8);
    if (!o.small) { ln(c, "#a8987a", 1.1, [[32.4, 21.4], [39.4, 23.2]]); ln(c, "#a8987a", 1.1, [[32.4, 25.4], [38, 26.8]]); }
    f(c, "#d8ccb0", () => c.rect(39.6, 18.6, 2.6, 13.6));
    rr(c, P.d, 17.6, 2.6, 9.8, 5, 2); rr(c, P.d, 17.6, 40.4, 9.8, 5, 2);
    rr(c, P.a, 14.6, 6.4, 15.8, 35.2, 5);
    f(c, mix(P.a, "#ffffff", 0.24), () => c.rect(16.6, 9, 2.4, 30)); f(c, SH, () => c.roundRect(26.4, 6.4, 4, 35.2, [0, 5, 5, 0]));
    rr(c, GOLD, 13, 9.6, 19, 4.6, 1.8); rr(c, GOLD, 13, 33.8, 19, 4.6, 1.8);
    poly(c, P.accent, [[22.5, 19.4], [26, 24], [22.5, 28.6], [19, 24]], 0.3); poly(c, HI2, [[22.5, 20.2], [22.5, 24], [20, 24]]);
  }
  /** 水晶球：一顆大水晶球（左上白色高光、右下暗面、球裡一彎亮弧）坐在暗銅色的梯形底座上。球色照人物掌上那顆（#a898ff；骨材質是骨白；有元素換元素色）。 */
  function orbBall(c, o, P) {
    const [e1] = orbPair(P);
    poly(c, M.brass, [[14.5, 43.6], [33.5, 43.6], [30, 34.6], [18, 34.6]], 1); if (!o.small) f(c, GOLD, () => c.rect(18.6, 35, 10.8, 1.4));
    ci(c, e1, 24, 20.6, 15.4);
    f(c, "rgba(40,20,90,0.28)", () => { c.arc(24, 20.6, 15.4, -0.25, Math.PI * 0.8); c.closePath(); });
    st(c, mix(e1, "#ffffff", 0.5), 2.2, (x) => x.arc(24, 20.6, 9.4, Math.PI * 0.15, Math.PI * 0.7), "round");
    el(c, HI2, 17.4, 13.6, 3.2, 4.6, 0.6); if (!o.small) ci(c, HI2, 29.6, 27, 1.2);
  }
  /** 浮空寶珠：一顆浮在半空的寶珠，外面繞一圈斜的金環（後半圈在珠子後面、前半圈壓在珠子前面），沒有底座。 */
  function orbFloating(c, o, P) {
    const [e1] = orbPair(P), ring = (x, a0, a1) => st(x, GOLD, 3.2, (k) => k.ellipse(24, 24.6, 20.4, 6.4, -0.3, a0, a1), "butt");
    ring(c, Math.PI, TAU);
    ci(c, e1, 24, 23.6, 12.6);
    f(c, "rgba(40,20,90,0.28)", () => { c.arc(24, 23.6, 12.6, -0.25, Math.PI * 0.8); c.closePath(); });
    el(c, HI2, 18.8, 18, 2.6, 3.8, 0.6);
    halo(c, o, (x) => { ring(x, 0, Math.PI); if (!o.small) st(x, GOLDL, 1, (k) => k.ellipse(24, 24.2, 20.2, 6.2, -0.3, Math.PI * 0.55, Math.PI * 0.95), "butt"); });
  }
  const OFF = {
    round_shield: (r, P) => ({ block: true, badge: 0.8, d: (c, o) => roundShield(c, o, P, r.form === "banded") }), /* 第 2 版（審查可修）：圓章裡縮到 80%（原本 94%，圓套圓、貼到金框） */
    kite_shield: (r, P) => (r.form === "tower" ? { block: true, badge: 0.87, d: (c, o) => W.towerShield(c, o, 24, 24, 1, 0, P.a, true) } : { block: true, badge: 0.86, d: (c, o) => kiteShield(c, o, P) }),
    tome: (r, P) => ({ block: true, badge: 0.84, d: r.form === "scroll" ? (c, o) => tomeScroll(c, o, P) : (c, o) => tomeBook(c, o, P) }),
    orb: (r, P) => ({ block: true, badge: r.form === "floating" ? 0.9 : 0.88, d: r.form === "floating" ? (c, o) => orbFloating(c, o, P) : (c, o) => orbBall(c, o, P), pre: (c) => glow(c, 24, r.form === "floating" ? 23.6 : 20.6, 23, orbPair(P)[0], 0.5), post: r.form === "floating" ? (c, o) => { if (!o.small) { sparkle(c, "#ffffff", 40, 9, 2.6); sparkle(c, "#ffffff", 8, 38, 2); } } : undefined }),
  };
  const BUILD = { sword: SWORD, greatsword: GREATSWORD, dagger: DAGGER, dual_dagger: DUAL_DAGGER, axe: AXE, hammer: HAMMER, spear: SPEAR, bow: BOW, crossbow: CROSSBOW, longgun: LONGGUN, shotgun: SHOTGUN, pistol: PISTOL, dual_pistol: DUAL_PISTOL, fist: FIST, scythe: SCYTHE, whip: WHIP, staff: STAFF, ...OFF };
  /** 現行「關鍵字小圖樣」畫在器物上的兩個位置（48 格座標；現行 gearIcon 各造型回傳的 spots 換算過來）。小圖樣本身不在這一批，照現行原樣疊。 */
  const SPOTS = { diag: [[30, 18], [20.5, 27.5]], block: [[17, 17], [31, 31]], gun: [[33, 13], [17, 33]] };

  const cache = new Map();
  /* 圓章裡的自動縮放（含外框不超出圓章外緣）第 2 版搬到 qIcons.js 的 Q.badgeScale，風格樣張的八把也用同一套。 */
  /** look → 圖樣定義（給 QIcons.render 用）：{ d, pre, post, meta: { badge, diag, spots, r } }。 */
  function def(look) {
    const r = resolve(look), key = [r.kind, r.form, r.material, r.keywords.join("+"), r.element ?? "", r.rarity, r.color ?? ""].join("|");
    let hit = cache.get(key);
    if (!hit) { const K = KINDS[r.kind], b = BUILD[r.kind](r, palette(r)), isGun = ["longgun", "shotgun", "pistol", "dual_pistol"].includes(r.kind);
      hit = { zh: K.forms[r.form], d: b.d, pre: b.pre, post: b.post, meta: { badge: Q.badgeScale(b.d, b.badge ?? 1), diag: b.diag ?? (!!K.diag && !b.block), spots: b.spots ?? (isGun ? SPOTS.gun : K.diag ? SPOTS.diag : SPOTS.block), r } }; cache.set(key, hit); }
    return hit;
  }
  /** 現行裝備格的外框（gearIcon.ts 的 frame() 原樣：深底、稀有度色框、非普通的右上角色塊、史詩以上的底光、傳說的內框）。64 單位。 */
  function gearFrame(ctx, rarity) {
    const [c] = RARITY[rarity];
    ctx.fillStyle = "#23262d"; ctx.beginPath(); ctx.roundRect(2, 2, 60, 60, 9); ctx.fill();
    if (rarity === "epic" || rarity === "legendary") { const g = ctx.createRadialGradient(32, 32, 4, 32, 32, 34); g.addColorStop(0, c + "66"); g.addColorStop(1, c + "00"); ctx.fillStyle = g; ctx.fill(); }
    ctx.lineWidth = rarity === "legendary" ? 3.5 : 2.5; ctx.strokeStyle = c; ctx.beginPath(); ctx.roundRect(2, 2, 60, 60, 9); ctx.stroke();
    if (rarity !== "common") { ctx.fillStyle = c; ctx.beginPath(); ctx.moveTo(50, 3.5); ctx.lineTo(60.5, 3.5); ctx.lineTo(60.5, 14); ctx.closePath(); ctx.fill(); }
    if (rarity === "legendary") { ctx.lineWidth = 1; ctx.globalAlpha = 0.6; ctx.beginPath(); ctx.roundRect(6, 6, 52, 52, 6); ctx.stroke(); ctx.globalAlpha = 1; }
  }
  /** 現行元素關鍵字的小圖樣（gearIcon.ts 的 motif() 原樣，64 單位）：只有樣張頁示意「>36px 時照現行疊在 Q 版圖上」用，不是這一批重畫的東西。 */
  function motif(ctx, kw, x, y) {
    const col = KW[kw]; if (!col) return; ctx.save(); ctx.fillStyle = col; ctx.strokeStyle = col; ctx.lineWidth = 1.6; ctx.lineCap = "round";
    if (kw === "ignite") { ctx.beginPath(); ctx.moveTo(x, y - 6); ctx.quadraticCurveTo(x + 4.5, y, x, y + 3); ctx.quadraticCurveTo(x - 4.5, y, x, y - 6); ctx.fill(); }
    else if (kw === "wet") { ctx.beginPath(); ctx.moveTo(x, y - 5); ctx.quadraticCurveTo(x + 4, y + 1, x, y + 3); ctx.quadraticCurveTo(x - 4, y + 1, x, y - 5); ctx.fill(); }
    else if (kw === "charged" || kw === "shock") { ctx.beginPath(); ctx.moveTo(x - 3, y - 5); ctx.lineTo(x + 1, y - 1); ctx.lineTo(x - 1, y + 1); ctx.lineTo(x + 3, y + 5); ctx.stroke(); }
    else { ctx.beginPath(); for (let i = 0; i < 3; i++) { const a = (i * Math.PI) / 3; ctx.moveTo(x - Math.cos(a) * 4.5, y - Math.sin(a) * 4.5); ctx.lineTo(x + Math.cos(a) * 4.5, y + Math.sin(a) * 4.5); } ctx.stroke(); }
    ctx.restore();
  }
  /** 裝備格裡圖樣四邊各留 6%（風格樣張是 8%；全量時 45° 斜放的劍、匕首在 8% 下佔框只有 59%，不到規則 7 的 60%，所以放大一點）。 */
  const GEAR_PAD = Q.GEAR_PAD; /* 0.06；第 2 版起定義在 qIcons.js，風格樣張的八把同一個值 */
  /** 真 1 倍修正：把 Q.render 畫好的圖樣 canvas（邊長 round(a×res) 裝置像素）貼到「以 (x,y)～(x+a,y+a) 為中心」的位置，
   *  照 canvas 原尺寸、左上角對齊整數裝置像素，不縮放（ctx 目前每單位 res 個裝置像素、原點在整數像素上）。
   *  不要用 drawImage(cv, x, y, a, a) 縮放貼到小數位置：差不到 1px 的縮放也會讓瀏覽器重新取樣，1px 外框被抹成半透明、整塊糊掉。 */
  function blit(ctx, cv, x, y, a, res) {
    const w = cv.width / res, snap = (v) => Math.round(v * res) / res;
    ctx.drawImage(cv, snap(x + (a - w) / 2), snap(y + (a - w) / 2), w, w);
  }
  /** 畫一個含框的圖示在 (0,0)～(size,size)。opt.frame：badge（米色圓章，預設）｜gear（裝備格，框色＝稀有度）｜none；opt.motif＝true 時 >36px 的裝備格照現行疊元素小圖樣。 */
  function paint(ctx, look, size, res, opt = {}) {
    const d = def(look), fr = opt.frame ?? "badge", put = (x, y, a, o) => ctx.drawImage(Q.render(d, a, res, o), x, y, a, a);
    ctx.save();
    if (fr === "badge") { const g = ctx.createRadialGradient(size / 2, size * 0.42, 0, size / 2, size / 2, size / 2); g.addColorStop(0, "#f6eed8"); g.addColorStop(1, "#d6c7a2"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(size / 2, size / 2, size / 2, 0, TAU); ctx.fill(); ctx.lineWidth = size / 24; ctx.strokeStyle = "#c8a868"; ctx.beginPath(); ctx.arc(size / 2, size / 2, size / 2 - size / 48, 0, TAU); ctx.stroke();
      /* 真 1 倍修正：圓章自動縮放（meta.badge < 1）時圖樣邊長不是整數裝置像素，原本把 round(a×res) 的 canvas 縮放貼到 a、而且貼在小數位置，
         瀏覽器會重新取樣——外框被抹掉、整塊糊掉（鞭三款、雙左輪在 20px 最明顯）。改成照 canvas 原尺寸、對齊到整數裝置像素貼上（blit）。 */
      const a = size * d.meta.badge, p = (size - a) / 2; blit(ctx, Q.render(d, a, res, { ow: Q.outlinePx(size), badge: true }), p, p, a, res); }
    else if (fr === "gear") { ctx.save(); ctx.scale(size / 64, size / 64); gearFrame(ctx, d.meta.r.rarity); ctx.restore(); const p = size * GEAR_PAD; put(p, p, size - p * 2, {});
      if (opt.motif && size > 36 && d.meta.r.tintKw) { ctx.save(); ctx.translate(p, p); ctx.scale((size - p * 2) / 48, (size - p * 2) / 48); for (const [x, y] of d.meta.spots) { ctx.save(); ctx.translate(x, y); ctx.scale(0.75, 0.75); motif(ctx, d.meta.r.tintKw, 0, 0); ctx.restore(); } ctx.restore(); } }
    else put(0, 0, size, {});
    ctx.restore();
  }
  /** 含框的圖示 canvas：顯示邊長 px×zoom；zoom 1 時內部解析度 ×2（和遊戲一樣），放大時直接用向量畫到該倍率（圖樣的簡化程度仍照 px）；opt.res＝指定內部解析度（預設不變；opt.res＝1 是真 1 倍：canvas 寬高＝CSS px，樣張頁 ?part=true1x 用）。 */
  function canvas(look, px, zoom = 1, opt = {}) {
    const res = opt.res ?? (zoom === 1 ? 2 : zoom), cv = document.createElement("canvas"); cv.width = cv.height = Math.round(px * res); cv.style.width = cv.style.height = px * zoom + "px";
    const x = cv.getContext("2d"); x.scale(res, res); paint(x, look, px, res, opt); return cv;
  }
  /** 全部款式（kind × form）：[{ kind, form, zh, kindZh, slot }]。 */
  const list = () => Object.entries(KINDS).flatMap(([kind, K]) => Object.entries(K.forms).map(([form, zh]) => ({ kind, form, zh, kindZh: K.zh, slot: K.slot })));
  return { KINDS, MAT, MAT_ZH, KW, RARITY, NO_FORM, GEAR_PAD, resolve, palette, def, paint, canvas, list, gearFrame, blit };
})();
