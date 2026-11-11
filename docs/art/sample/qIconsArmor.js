// qIconsArmor.js：「小圖示改 Q 版」全量重畫第 2 批——防具 18 種 37 款＋飾品 3 種 7 款，共 21 種 44 款（畫圖 agent 2026-11-12）。
// 規則：docs/art/Q版小圖示樣張.md 第 2 節（14 條）；紀錄：docs/art/Q版小圖示-第2批防具飾品.md；樣張頁：q-icons-armor.html。
// 只放裝備格（64、48、42、32px），沒有米色圓章。框（稀有度框、裝備格底）照現行，這裡只畫框裡的圖，圖樣四邊留白 6%（和第 1 批同一個 Q.GEAR_PAD）。
// 清單照遊戲端 client/src/render/gearAppearance.json（kind × form，形制各自的可用材質與預設材質也照它）；變體照現行 gearIcon.ts 的分法，不新增規則：
//   材質 material → 主色／暗色；染色 dye（只有布、皮）→ 主色換染色；元素關鍵字（ignite、wet、charged、frozen）→ 主色混元素色（防具 25%、飾品 40%，晶石直接換色）；
//   稀有度 rarity → 外框（現行樣式）；關鍵字小圖樣（>36px 才畫）不在這一批，照現行原樣疊上去（位置在 meta.spots，從現行各造型回傳的位置換算）。
// 造型與配色照 qDoll.js 身上那一件（body()、Q_headgear()、leg()、handForm…），只加粗；人物沒有分的形制（皮背心／獵裝、毛帽、手套各款、鞋靴各款…）與人物身上看不到的飾品，照現行裝備圖示的題材畫。
// 座標：48×48，全部直立；鞋靴是單隻側面、鞋尖朝右（現行也是）。
// 依賴（先載入）：qIcons.js（QIcons.H 畫法小工具、QIcons.M 材質色、QIcons.render 剪影外框、QIcons.GEAR_PAD）、qIconsWeapons.js（材質表 MAT、稀有度 RARITY、裝備格外框 gearFrame——和第 1 批共用同一份，不另抄）。
window.QIconsArmor = (() => {
  const Q = window.QIcons, QW = window.QIconsWeapons, { mix, f, rr, ci, el, poly, ln, starPts, sparkle, halo, HI, HI2, SH } = Q.H, M = Q.M, TAU = Math.PI * 2, OUT = Q.OUT;
  const MAT = QW.MAT, MAT_ZH = QW.MAT_ZH, RARITY = QW.RARITY, KW = { ignite: "#ff6a1a", wet: "#4aa8ff", charged: "#fff36b", frozen: "#8fe3ff" };
  /** 染色（client/src/render/artPalette.ts 的 GEAR_DYE；只有布、皮能染）。 */
  const DYE = { red: "#b83a3a", blue: "#3a5fb8", green: "#3f8a4a", purple: "#7a4ab0", black: "#33363d", white: "#e6e6e0", brown: "#7a5232", gold: "#d9a83a" };
  const DYE_ZH = { red: "紅", blue: "藍", green: "綠", purple: "紫", black: "黑", white: "白", brown: "褐", gold: "金" };
  const DYEABLE = ["cloth", "leather"], METAL = ["iron", "steel", "copper", "silver", "gold"], ACC = [...METAL, "bone", "crystal"];
  const GOLD = M.gold, GOLDL = M.goldL, BELT = "#3a2a1c", BONE = "#e9e3cf", BONED = "#a8a08a", HORN = "#e8d8b8", CORD = "#c8483e", CREAM = "#e8e0c8";
  // 清單：遊戲端 gearAppearance.json 的 body 5 種、head 5 種、hands 4 種、feet 4 種、ring 1 種、neck 2 種（forms 的順序同資料檔）。formMats／formDef＝形制自己的可用材質與預設材質。
  const KINDS = {
    hood: { zh: "兜帽", slot: "head", forms: { cloth: "布兜帽", cowl: "斗篷帽" }, mats: ["cloth", "leather"], def: "cloth" },
    hat: { zh: "帽子", slot: "head", forms: { wizard: "法師帽", wide: "寬簷帽" }, mats: ["cloth", "leather"], def: "cloth" },
    circlet: { zh: "頭巾／頭冠", slot: "head", forms: { bandana: "頭巾", crown: "頭冠" }, mats: ["cloth", "leather", ...ACC], def: "cloth", formMats: { bandana: ["cloth", "leather"], crown: ACC }, formDef: { crown: "gold" } },
    cap: { zh: "皮帽", slot: "head", forms: { leather: "皮帽", fur: "毛帽" }, mats: ["leather", "cloth"], def: "leather" },
    helmet: { zh: "頭盔", slot: "head", forms: { iron: "鐵盔", horned: "角盔", greathelm: "全罩盔" }, mats: METAL, def: "iron" },
    robe: { zh: "布袍", slot: "body", forms: { long: "長袍", short: "短袍" }, mats: ["cloth"], def: "cloth" },
    leather: { zh: "皮甲", slot: "body", forms: { vest: "皮背心", hunter: "獵裝" }, mats: ["leather"], def: "leather" },
    mail: { zh: "鎖甲", slot: "body", forms: { chain: "鎖子甲", scale: "鱗甲" }, mats: METAL, def: "iron" },
    plate: { zh: "板甲", slot: "body", forms: { half: "半身板甲", full: "全身板甲" }, mats: METAL, def: "steel" },
    coat: { zh: "外套", slot: "body", forms: { travel: "旅行外套", cape: "披風外套" }, mats: ["cloth", "leather"], def: "cloth" },
    cloth_gloves: { zh: "布手套", slot: "hands", forms: { plain: "素手套", fingerless: "露指手套" }, mats: ["cloth"], def: "cloth" },
    leather_gloves: { zh: "皮手套", slot: "hands", forms: { short: "短皮手套", long: "長皮手套" }, mats: ["leather"], def: "leather" },
    gauntlets: { zh: "護手", slot: "hands", forms: { plate: "板金護手", mail: "鎖鏈護手" }, mats: METAL, def: "steel" },
    bracers: { zh: "臂甲", slot: "hands", forms: { leather: "皮臂甲", ring: "臂環" }, mats: ["leather", ...METAL], def: "leather", formMats: { leather: ["leather"], ring: METAL }, formDef: { ring: "copper" } },
    shoes: { zh: "布鞋", slot: "feet", forms: { slipper: "布鞋", wrapped: "綁腿鞋" }, mats: ["cloth"], def: "cloth" },
    boots: { zh: "皮靴", slot: "feet", forms: { short: "短靴", tall: "長靴" }, mats: ["leather"], def: "leather" },
    iron_boots: { zh: "鐵靴", slot: "feet", forms: { plain: "鐵靴", sabaton: "尖頭鐵靴" }, mats: METAL, def: "iron" },
    greaves: { zh: "脛甲", slot: "feet", forms: { plain: "脛甲", knee: "護膝脛甲" }, mats: METAL, def: "steel" },
    ring: { zh: "戒指", slot: "ring", forms: { plain: "素戒", gem: "寶石戒", signet: "印戒" }, mats: ACC, def: "gold" },
    pendant: { zh: "墜飾", slot: "neck", forms: { pendant: "項鍊墜", tag: "吊牌" }, mats: ACC, def: "gold" },
    charm: { zh: "護符", slot: "neck", forms: { tablet: "符牌", bone: "骨符" }, mats: [...ACC, "leather", "cloth"], def: "gold" },
  };
  const ARMOR_SLOTS = ["head", "body", "hands", "feet"];
  /** 沒有 kind 時依欄位退回的造型（gearIcon.ts 的 SLOT_DEFAULT_KIND，防具飾品的部分）。 */
  const SLOT_DEFAULT_KIND = { head: "helmet", body: "mail", hands: "leather_gloves", feet: "boots", neck: "pendant", ring_1: "ring", ring_2: "ring" };
  const matsOf = (kind, form) => KINDS[kind].formMats?.[form] ?? KINDS[kind].mats, defOf = (kind, form) => KINDS[kind].formDef?.[form] ?? KINDS[kind].def;

  /** 驗證＋補預設（同 gearIcon.resolveGear）：任何輸入都回傳畫得出來的外觀。look.color＝人物外觀的染色覆寫。 */
  function resolve(look, slot) {
    const src = look ?? {}, want = src.kind ?? SLOT_DEFAULT_KIND[slot], kind = KINDS[want] ? want : "helmet", K = KINDS[kind];
    const form = src.form in K.forms ? src.form : Object.keys(K.forms)[0];
    const material = matsOf(kind, form).includes(src.material) ? src.material : defOf(kind, form);
    const dye = DYEABLE.includes(material) && DYE[src.dye] ? src.dye : null;
    const keywords = (src.keywords ?? []).filter((k) => typeof k === "string").slice(0, 2), tintKw = keywords.find((k) => KW[k]);
    return { kind, form, material, dye, keywords, tintKw, rarity: RARITY[src.rarity] ? src.rarity : "common", color: src.color ?? null };
  }
  const lum = (h) => 0.299 * parseInt(h.slice(1, 3), 16) + 0.587 * parseInt(h.slice(3, 5), 16) + 0.114 * parseInt(h.slice(5, 7), 16);
  /** 規則 6：染色太暗（亮度 < 105：紅、藍、紫、黑、褐）在深色裝備格上整件的平均亮度到不了 100，換亮一階的同類色（每階混 15% 白；黑要兩階）。材質本色不動（照人物）。 */
  const lift = (a) => { let n = 0; while (lum(a) < 105 && n++ < 4) a = mix(a, "#ffffff", 0.15); return a; };
  /** 第 2 版：紅染不混白（混白會變粉橘紅）——三個色版同乘一個倍率，只提高明度、彩度不變（每階 ×1.09）。 */
  const brighten = (a, k = 1.09) => "#" + [1, 3, 5].map((i) => Math.min(255, Math.round(parseInt(a.slice(i, i + 2), 16) * k)).toString(16).padStart(2, "0")).join("");
  const liftRed = (a) => { let n = 0; while (lum(a) < 105 && n++ < 4) a = brighten(a); return a; };
  /** 第 2 版：黑染保留深色（規則 6 的例外，和塔盾、皮靴同樣處理）——本色只混 10% 白（亮度約 74，未染灰布是 142），滾邊與翻口用未染布的米灰，
   *  另外沿圖樣內緣包一圈淺色滾邊（RIM，見 rimLight()）把整件的平均亮度補回 100 以上。 */
  const BLACK_TRIM = mix(MAT.cloth[0], "#ffe6b8", 0.42), RIM = "#d6d8de";
  /** 配色：主色 a、暗色 d、亮一階 l（金屬亮面）、暖亮邊 t（皮、布的滾邊與翻口）、最深 dd（開口、洞裡）、寶石 accent；rim＝沿內緣包一圈的淺色滾邊（只有黑染）。 */
  function palette(r) {
    let [a, d] = MAT[r.material];
    const base = r.color ?? (r.dye ? DYE[r.dye] : null), red = !r.color && r.dye === "red", black = !r.color && r.dye === "black";
    if (base) { a = black ? mix(base, "#ffffff", r.kind === "hood" ? 0.17 : 0.1) : red ? liftRed(base) : lift(base); d = mix(a, "#000000", 0.35); } /* 黑兜帽（一大塊臉洞）多混一點白，亮度約 88 */
    if (r.kind === "hood" && lum(a) < 118 && !black) { a = red ? brighten(a) : mix(a, "#ffffff", 0.15); if (!base) d = mix(d, "#ffffff", 0.1); else d = mix(a, "#000000", 0.35); } /* 兜帽有一大塊深色臉洞，本色亮度 < 118（皮、多數染色）時整件到不了規則 6 的 100，再換亮一階（紅：再提高一階明度；黑：不換，靠滾邊） */
    const tc = r.tintKw ? KW[r.tintKw] : null, armor = ARMOR_SLOTS.includes(KINDS[r.kind].slot);
    if (tc) { if (r.material === "crystal") { a = tc; d = mix(tc, "#000000", 0.4); } else { a = mix(a, tc, armor ? 0.25 : 0.4); d = mix(d, tc, armor ? 0.15 : 0.25); } }
    const first = r.keywords.find((k) => KW[k]);
    return { a, d, l: mix(a, "#ffffff", 0.45), t: black ? BLACK_TRIM : mix(a, "#ffe6b8", 0.42), dd: mix(d, OUT, 0.55), accent: first ? KW[first] : r.material === "crystal" ? "#b8a8ff" : "#e04060", rim: black ? RIM : null, lifted: (!!base && a !== base) || (!base && a !== MAT[r.material][0] && !tc) };
  }
  /** 黑染的淺色滾邊：把已經畫好的圖樣（c 的整張畫布）沿剪影內緣 w 個單位寬的那一圈換成淺色——只換深色的像素（金扣、膚色指頭、白毛邊不動）。
   *  量整體剪影的那一遍（o.flat）不用畫。寬度＝1 個 CSS px，圖樣邊長超過 34px 時是邊長的 3%。 */
  function rimLight(c, o, col) {
    if (o.flat) return;
    const cv = c.canvas, W = cv.width, H = cv.height, w = Math.max(o.u, 1.44) * (W / 48), mk = () => { const k = document.createElement("canvas"); k.width = W; k.height = H; return k; };
    const core = mk(), cx = core.getContext("2d"); cx.drawImage(cv, 0, 0); cx.globalCompositeOperation = "destination-in";
    for (const q of [1, 0.5]) for (let i = 0; i < 16; i++) { const t = (i / 16) * TAU; cx.drawImage(cv, Math.cos(t) * w * q, Math.sin(t) * w * q); }
    const src = c.getImageData(0, 0, W, H), keep = cx.getImageData(0, 0, W, H).data, px = src.data, [R, G, B] = [1, 3, 5].map((i) => parseInt(col.slice(i, i + 2), 16));
    for (let i = 0; i < px.length; i += 4) { if (px[i + 3] < 8 || keep[i + 3] > 127 || 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2] > 112) continue; px[i] = R; px[i + 1] = G; px[i + 2] = B; }
    c.putImageData(src, 0, 0);
  }

  // ---------------- 小工具 ----------------
  const clip = (c, path, fn) => { c.save(); c.beginPath(); path(c); c.clip(); fn(c); c.restore(); };
  const st = (c, col, w, fn, cap = "round") => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
  /** 以 (24,24) 為中心縮放 k 倍，再位移 (dx,dy)、轉 rot。 */
  const at = (c, k, dx, dy, fn, rot = 0) => { c.save(); c.translate(24 + dx, 24 + dy); c.rotate(rot); c.scale(k, k); c.translate(-24, -24); fn(c); c.restore(); };
  /** 色塊＋右側一階暗面（x ≥ shX 的部分蓋黑 22%）。 */
  const body = (c, col, path, shX) => { f(c, col, path); if (shX != null) clip(c, path, () => f(c, SH, () => c.rect(shX, 0, 48, 48))); };
  const pts = (p) => (c) => { p.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.closePath(); };
  /** 菱形寶石＋左上一塊亮面。 */
  const gem = (c, col, x, y, r, o) => { poly(c, col, [[x, y - r], [x + r, y], [x, y + r], [x - r, y]], 0.5); poly(c, "rgba(255,255,255,0.6)", [[x, y - r + 0.6], [x, y], [x - r + 0.8, y]]); if (!o.small) poly(c, "rgba(0,0,0,0.25)", [[x, y], [x + r - 0.6, y], [x, y + r - 0.6]]); };
  /** 腰帶＋金扣（人物身上除了長袍、外套都有：深褐 #3a2a1c、金扣）。 */
  const belt = (c, path, y, bx = 24) => { clip(c, path, () => f(c, BELT, () => c.rect(0, y, 48, 3.6))); rr(c, GOLD, bx - 2.9, y - 1, 5.8, 5.6, 1.2); rr(c, BELT, bx - 1.2, y + 0.7, 2.4, 2.2, 0.5); };

  // =====================================================================
  // 頭（qDoll.js 的 Q_headgear：hood、wizard_hat、wide_hat、bandana、crown、cap、helmet、horned_helm、greathelm）
  // =====================================================================
  const hoodShape = (c) => { c.moveTo(6.5, 40); c.bezierCurveTo(4.5, 20, 13, 7, 26, 5.6); c.lineTo(33.2, 4); c.lineTo(31.6, 8.6); c.bezierCurveTo(40, 13, 43.5, 24, 41.5, 40); c.quadraticCurveTo(24, 44.4, 6.5, 40); c.closePath(); };
  /** 布兜帽：正面的兜帽——頂上一個往後倒的小尖、兩側垂到肩、中間一個拱門形的深色臉洞一路開到下襬（人物是兜帽＋臉的開口＋下緣一道深色）；洞口一圈細的、亮一階的同色裡布、洞口兩側外面的下襬上各垂一條米白束繩（cords；斗篷帽不畫，裝備格 32px 省掉）。
   *  臉洞用暗色的亮一階（不是全黑）；兜帽的本色太暗時（皮、深色染料）換亮一階，見 palette()。 */
  function hoodArt(c, o, P, cords = true) {
    body(c, P.a, hoodShape, 36.6);
    clip(c, hoodShape, () => { f(c, "rgba(255,255,255,0.14)", () => c.rect(0, 0, 17, 48)); f(c, mix(P.a, "#ffffff", 0.3), (x) => x.ellipse(24, 28, 11.8, 14, 0, 0, TAU)); f(c, mix(P.d, OUT, 0.25), (x) => x.ellipse(24.3, 29.4, 9.8, 12.4, 0, 0, TAU)); f(c, P.d, () => c.rect(0, 39.2, 48, 12)); });
    el(c, HI, 12.4, 19, 1.9, 6, 0.5);
    /* 第 2 版：束繩原本垂在洞口正下方，32px 是洞裡兩個米白點，像兩顆尖牙。移到洞口兩側外面的下襬上；裝備格 32px（o.u > 1.5）省掉 */
    if (cords && !o.small && o.u <= 1.5) for (const x of [10.4, 35.9]) { rr(c, CREAM, x, 35.4, 1.7, 5.4, 0.8); ci(c, CREAM, x + 0.85, 41.2, 1.5); }
  }
  /** 斗篷帽：兜帽下面接一片披領（人物的 cowl：兩肩外張、正面尖角垂到胸口、下緣一道深色），領口一條橫的深色扣帶加小金扣。剪影是「兜帽坐在一片寬披肩上」。 */
  function cowlArt(c, o, P) {
    const mantle = pts([[10, 27], [38, 27], [43.6, 36.4], [24, 43.4], [4.4, 36.4]]);
    poly(c, P.a, [[10, 27], [38, 27], [43.6, 36.4], [24, 43.4], [4.4, 36.4]], 1);
    clip(c, mantle, () => { f(c, SH, () => c.rect(33, 0, 20, 48)); st(c, P.d, 2.4, (x) => { x.moveTo(4.4, 37.4); x.lineTo(24, 44.4); x.lineTo(43.6, 37.4); }, "butt"); f(c, HI, () => c.rect(9.4, 28, 2, 7)); });
    at(c, 0.75, 0, -4.6, (x) => hoodArt(x, o, P, false));
    /* 第 2 版：領口正中一顆金球＋鈴形的剪影＝鈴鐺。改成一條橫的深色扣帶、中間一個小金扣 */
    rr(c, P.d, 16.4, 32.6, 15.2, 3, 1.2); rr(c, GOLD, 22.2, 32, 3.6, 4.2, 0.9); f(c, P.d, () => c.rect(23.4, 33.3, 1.2, 1.6));
  }
  /** 法師帽：寬帽簷＋往右歪的高尖帽、帽根一道深色帽帶（人物的 wizard_hat：帽簷、尖帽、深色帶）加一顆金扣。 */
  function wizardArt(c, o, P) {
    const cone = (x) => { x.moveTo(12.6, 35); x.quadraticCurveTo(17, 20, 22, 9.4); x.quadraticCurveTo(26.4, 3, 35.6, 6.8); x.quadraticCurveTo(30.4, 9.6, 30.8, 15.4); x.lineTo(35.6, 35); x.quadraticCurveTo(24, 39.4, 12.6, 35); x.closePath(); };
    body(c, P.a, (x) => x.ellipse(24, 36.6, 20.4, 6.6, 0, 0, TAU), 37);
    st(c, P.t, 1.8, (x) => x.ellipse(24, 36.6, 18.2, 4.6, 0, Math.PI * 0.2, Math.PI * 0.8), "butt");
    el(c, P.d, 24, 35.8, 13.4, 3.8);
    body(c, P.a, cone, 29.6);
    clip(c, cone, () => st(c, P.d, 4.8, (x) => { x.moveTo(10, 31); x.quadraticCurveTo(24, 37.4, 38, 31); }, "butt"));
    el(c, HI, 19.4, 21.5, 2, 6.4, 0.3);
    rr(c, GOLD, 21.2, 31.2, 5.6, 5.6, 1.2); rr(c, P.d, 22.9, 32.9, 2.2, 2.2, 0.5);
    if (!o.small) sparkle(c, CREAM, 26.6, 18.6, 2.4);
  }
  /** 寬簷帽：一圈寬扁的帽簷、低矮的圓帽冠（人物的 wide_hat：亮帽簷＋暗一階的帽冠）、帽帶，右邊插一根白羽毛（現行圖示有）。 */
  function wideHatArt(c, o, P) {
    const crown = (x) => { x.moveTo(12.4, 30.6); x.lineTo(13.6, 20); x.quadraticCurveTo(24, 10, 34.4, 20); x.lineTo(35.6, 30.6); x.quadraticCurveTo(24, 35, 12.4, 30.6); x.closePath(); };
    f(c, "#e6e6e0", (x) => { x.moveTo(32.6, 27.4); x.quadraticCurveTo(46.4, 22, 43.4, 7.6); x.quadraticCurveTo(35.4, 12.6, 30.6, 25); x.closePath(); });
    if (!o.small) st(c, "#a8a69c", 1, (x) => { x.moveTo(33, 25.6); x.quadraticCurveTo(41, 20, 42.4, 10.4); }, "butt");
    body(c, P.a, (x) => x.ellipse(24, 32, 20.5, 8.6, 0, 0, TAU), 37.5);
    st(c, HI, 1.5, (x) => x.ellipse(24, 32, 18.4, 6.8, 0, Math.PI * 0.55, Math.PI * 0.95), "butt");
    el(c, P.d, 24, 31.2, 13, 4.4);
    body(c, mix(P.a, P.d, 0.5), crown, 30);
    clip(c, crown, () => st(c, mix(P.d, "#000000", 0.3), 3.8, (x) => { x.moveTo(11, 27); x.quadraticCurveTo(24, 32.6, 37, 27); }, "butt"));
    el(c, HI, 18.4, 20, 1.7, 4.2, 0.45);
  }
  /** 頭巾：包住頭頂的一片布（人物的 bandana：半圓的布、結在後腦、兩條尾巴），結拉到右側、兩條尾巴垂下來；下緣一道淺色的摺邊、布面三顆米白圓點（現行圖示有圓點）。 */
  function bandanaArt(c, o, P) {
    const dome = (x) => { x.moveTo(5.4, 31.6); x.quadraticCurveTo(4.8, 7.2, 23.2, 7.2); x.quadraticCurveTo(41.6, 7.2, 41, 31.6); x.quadraticCurveTo(23.2, 23, 5.4, 31.6); x.closePath(); };
    f(c, mix(P.a, P.d, 0.6), pts([[37.4, 31.6], [37.6, 44], [32.4, 42], [34.6, 30.6]]));
    f(c, P.a, pts([[38.6, 31], [44.6, 41], [40, 43.6], [36.2, 33]]));
    body(c, P.a, dome, 33.5);
    clip(c, dome, () => st(c, P.t, 3.6, (x) => { x.moveTo(5.4, 30.4); x.quadraticCurveTo(23.2, 21.6, 41, 30.4); }, "butt"));
    el(c, HI, 12.6, 15.6, 1.9, 4.6, 0.6);
    if (!o.small) for (const [x, y] of [[15, 21], [23.2, 14.4], [31.4, 20.4]]) ci(c, CREAM, x, y, 1.6);
    ci(c, P.d, 39, 31, 3.3); ci(c, HI, 38.2, 30.2, 1);
  }
  /** 頭冠：一圈冠帶上三個尖（中間最高）、尖頂各一顆亮珠、正中一顆寶石（人物的 crown：冠帶＋三個尖＋紅寶石）。 */
  function crownArt(c, o, P) {
    const shape = pts([[6.6, 40], [6.6, 15], [15.4, 26], [24, 10.6], [32.6, 26], [41.4, 15], [41.4, 40]]);
    poly(c, P.a, [[6.6, 40], [6.6, 15], [15.4, 26], [24, 10.6], [32.6, 26], [41.4, 15], [41.4, 40]], 0.8);
    clip(c, shape, () => { f(c, SH, () => c.rect(33.6, 0, 20, 48)); f(c, HI2, () => c.rect(8, 16, 1.8, 17)); });
    rr(c, P.d, 5.8, 35.4, 36.4, 5.4, 2);
    for (const [x, y, r] of [[6.8, 14, 2.6], [24, 9.2, 3], [41.2, 14, 2.6]]) { ci(c, P.l, x, y, r); ci(c, HI2, x - 0.8, y - 0.8, 0.9); }
    gem(c, P.accent, 24, 29.6, 5, o);
    if (!o.small) for (const x of [12.6, 35.4]) ci(c, CREAM, x, 32, 1.7);
  }
  /** 皮帽：圓頂的皮帽、帽頂一顆扣、帽緣一道深色帶、往右前方伸出去的帽舌（人物側面的 cap：圓頂＋朝前的深色帽舌），中間一道縫線。 */
  function capArt(c, o, P) {
    const dome = (x) => { x.moveTo(6.6, 35); x.quadraticCurveTo(6.2, 10.6, 22, 10.6); x.quadraticCurveTo(37.8, 10.6, 37.4, 35); x.closePath(); };
    f(c, P.d, (x) => { x.moveTo(31, 30.6); x.quadraticCurveTo(44.6, 30.4, 44.6, 39.4); x.lineTo(28, 38.4); x.closePath(); });
    st(c, P.t, 1.3, (x) => { x.moveTo(35.4, 32.4); x.quadraticCurveTo(42, 33, 43, 37.6); }, "butt");
    body(c, P.a, dome, 30.5);
    if (!o.small) f(c, P.d, () => c.rect(21.4, 11.4, 1.2, 20));
    el(c, HI, 13.2, 19.4, 2, 5.2, 0.5);
    rr(c, P.t, 5.2, 31.2, 33.6, 5.6, 2.2); f(c, P.d, () => c.rect(6.4, 35.6, 31.2, 1.3));
    ci(c, P.t, 22, 9.8, 2.6);
  }
  /** 毛帽：圓的皮帽頂＋一圈厚厚的米白毛邊（上緣一排圓圓的毛球；現行圖示的毛帽就是白毛邊）、右邊垂一條米白毛尾巴（兩道皮色環紋）。人物身上和皮帽同一頂（沒有分）。第一稿是「帽頂毛球＋波浪毛邊」，像杯子蛋糕，改掉了。 */
  function furCapArt(c, o, P) {
    const dome = (x) => { x.moveTo(8, 30); x.quadraticCurveTo(7.6, 6.4, 22, 6.4); x.quadraticCurveTo(36.4, 6.4, 36, 30); x.closePath(); };
    const tail = (x) => { x.moveTo(32, 27.6); x.quadraticCurveTo(45.6, 27.6, 44.4, 37.6); x.quadraticCurveTo(43.4, 43.8, 39.2, 44.4); x.quadraticCurveTo(35.4, 41.4, 37.4, 36.4); x.quadraticCurveTo(37.6, 33.6, 32, 34); x.closePath(); };
    body(c, BONE, tail, null); clip(c, tail, () => { for (const [x0, y0, x1, y1] of [[36, 37.4, 46, 34.4], [35, 42.6, 45, 40]]) st(c, P.a, 2.6, (x) => { x.moveTo(x0, y0); x.lineTo(x1, y1); }, "butt"); });
    body(c, P.a, dome, 29.5); el(c, HI, 13.6, 16, 2, 5, 0.5);
    rr(c, BONE, 4.6, 25.6, 34.8, 11.4, 5.4);
    for (let i = 0; i < 6; i++) ci(c, BONE, 8.8 + i * 5.3, 26.4, 2.9);
    f(c, BONED, () => c.rect(8, 34.4, 28, 1.5));
    if (!o.small) for (let i = 0; i < 6; i++) rr(c, BONED, 9.4 + i * 5, 27.6 + (i % 2) * 1.4, 1.2, 3.2, 0.6);
  }
  /** 鐵盔：圓頂、深一階的帽緣、兩片護頰、一條亮色鼻樑護片、帽緣四顆鉚釘（人物的 helmet：材質色圓頂＋兩側護頰＋深色帽緣）。和風格樣張對照 9 的頭盔同一頂。 */
  function helmetArt(c, o, P, cheeks = true) {
    const dome = (x) => { x.moveTo(5.5, 31); x.bezierCurveTo(5.5, 12, 14.5, 4.5, 24, 4.5); x.bezierCurveTo(33.5, 4.5, 42.5, 12, 42.5, 31); x.closePath(); };
    if (cheeks) { f(c, P.a, (x) => x.roundRect(7, 31, 9.5, 12.5, [0, 0, 4.5, 4.5])); f(c, P.a, (x) => x.roundRect(31.5, 31, 9.5, 12.5, [0, 0, 4.5, 4.5])); f(c, SH, (x) => x.roundRect(36.6, 31, 4.4, 12.5, [0, 0, 4.5, 0])); }
    f(c, P.a, dome);
    f(c, SH, (x) => { x.moveTo(32, 6.6); x.bezierCurveTo(39.5, 11.5, 42.5, 19, 42.5, 31); x.lineTo(36.4, 31); x.bezierCurveTo(36.4, 19, 35, 12, 32, 6.6); x.closePath(); });
    el(c, HI2, 15, 14.5, 2.6, 5.6, 0.55);
    rr(c, P.d, 4, 27.6, 40, 5.6, 2.4); rr(c, P.l, 21.4, 27.6, 5.2, cheeks ? 15.4 : 13, 2);
    if (!o.small) for (const x of [10, 17, 31, 38]) ci(c, P.l, x, 30.4, 1.1);
  }
  /** 角盔：同一頂圓頂盔（沒有護頰）縮小，兩側各一支往外、往上彎的骨白色牛角（人物的 horned_helm：頭盔＋兩支角），角根一圈深色箍。 */
  function hornedArt(c, o, P) {
    for (const s of [-1, 1]) { c.save(); c.translate(24, 0); c.scale(s, 1);
      f(c, HORN, (x) => { x.moveTo(-9.4, 27.6); x.quadraticCurveTo(-22, 27, -19.4, 5); x.quadraticCurveTo(-15.4, 16.4, -6.4, 18.6); x.closePath(); });
      f(c, s < 0 ? HI2 : SH, (x) => { x.moveTo(-18.2, 23); x.quadraticCurveTo(-20.4, 15, -19.2, 8); x.quadraticCurveTo(-17.4, 15.4, -15.6, 21.4); x.closePath(); });
      c.restore(); }
    at(c, 0.8, 0, 3.4, (x) => helmetArt(x, o, P, false));
    for (const s of [-1, 1]) { c.save(); c.translate(24, 0); c.scale(s, 1); f(c, P.d, pts([[-12.6, 28.2], [-9.2, 17.6], [-6.4, 18.6], [-9.4, 28.6]])); c.restore(); }
  }
  /** 全罩盔：整顆罩住的桶形盔——平頂、兩側略往下收、平底圓角；正面一條金色橫護條（兩側各一道深色視縫）加一條往下的金色鼻樑護條，合起來是 T 字（人物的 greathelm：整顆罩住＋一道視縫＋鼻樑），右下兩排透氣孔；盔頂一撮往右飄的紅纓。
   *  第一稿下緣收成尖角、護條是十字，32px 和第 1 批的鳶盾（盾形＋米白十字）撞圖；改成平底、T 字、加紅纓。和鐵灰塔盾（圓角長方形＋米白直紋）分開的地方：紅纓、金色 T 字、深色視縫。 */
  function greathelmArt(c, o, P) {
    const shape = (x) => { x.moveTo(9.6, 16.5); x.quadraticCurveTo(9.6, 10.6, 15.6, 10.6); x.lineTo(32.4, 10.6); x.quadraticCurveTo(38.4, 10.6, 38.4, 16.5); x.lineTo(36.6, 39.6); x.quadraticCurveTo(36.4, 43.6, 32.4, 43.6); x.lineTo(15.6, 43.6); x.quadraticCurveTo(11.6, 43.6, 11.4, 39.6); x.closePath(); };
    f(c, CORD, (x) => { x.moveTo(20.6, 11.6); x.quadraticCurveTo(21.6, 3.2, 31, 4.4); x.quadraticCurveTo(38.6, 5.4, 41.4, 10.4); x.quadraticCurveTo(34.6, 8, 29.6, 12); x.closePath(); });
    f(c, "rgba(255,255,255,0.35)", (x) => { x.moveTo(23, 9.6); x.quadraticCurveTo(24.6, 5.4, 30, 5.6); x.quadraticCurveTo(26.6, 7, 25.4, 10); x.closePath(); });
    body(c, P.a, shape, 32);
    clip(c, shape, () => { f(c, HI2, () => c.rect(12, 13.6, 2.2, 7)); f(c, HI2, () => c.rect(12.6, 30, 2, 9)); f(c, P.d, () => c.rect(0, 10, 48, 3.2)); f(c, P.d, () => c.rect(0, 41, 48, 3)); });
    rr(c, GOLD, 9.8, 19.6, 28.4, 8.4, 1.6); rr(c, GOLD, 21.4, 21, 5.2, 21.4, 1.6);
    f(c, "rgba(120,80,0,0.35)", () => c.rect(24.6, 28, 2, 14.4)); f(c, GOLDL, () => c.rect(10.8, 20.2, 26.4, 1.3));
    rr(c, "#1c1a22", 12, 22.4, 8.4, 3.2, 1.2); rr(c, "#1c1a22", 27.6, 22.4, 8.4, 3.2, 1.2);
    if (!o.small) for (const [x, y] of [[29.8, 32], [33.2, 32], [29.8, 35.6], [33, 35.6]]) ci(c, P.dd, x, y, 1);
  }

  // =====================================================================
  // 身體（qDoll.js 的 body()：robe 梯形長袍＋前襟與下襬的深色邊；coat 下襬正中開衩＋深色領＋三顆金扣；leather 斜背帶；mail 鎖子點／鱗片；plate 左胸亮面＋腰線；除了長袍、外套都有深褐腰帶與金扣）
  // =====================================================================
  /** 長袍：及地的 A 字長袍、兩隻垂下來的喇叭袖；前襟一條深色直邊、下襬與袖口一圈深色邊（人物的 robe 就是這三道邊），腰上一條深色腰帶打一個金結。 */
  function robeLongArt(c, o, P) {
    const shape = pts([[17.6, 5], [24, 9.6], [30.4, 5], [35.6, 6.8], [44.4, 25], [42.4, 32.4], [36.4, 30], [34.8, 22], [40.4, 44], [7.6, 44], [13.2, 22], [11.6, 30], [5.6, 32.4], [3.6, 25], [12.4, 6.8]]);
    body(c, P.a, shape, 33);
    clip(c, shape, () => { f(c, P.d, () => c.rect(0, 40.4, 48, 5)); f(c, HI, () => c.rect(14.6, 11, 2.6, 27));
      for (const s of [-1, 1]) st(c, P.d, 3, (x) => { x.moveTo(24 + s * 11.4, 28.6); x.lineTo(24 + s * 19.4, 32); }, "butt"); });
    rr(c, P.d, 22.5, 8.6, 3, 32, 1); poly(c, P.t, [[18.6, 5.6], [24, 12.4], [29.4, 5.6], [27.6, 5], [24, 9.4], [20.4, 5]], 0.3);
    clip(c, shape, () => f(c, P.d, () => c.rect(13, 23.4, 22, 3.2))); ci(c, GOLD, 24, 25, 2.5);
  }
  /** 短袍：只到膝上的短袍——兩隻袖子往兩邊張開（T 字形）、下襬短而外張；前襟與下襬同樣的深色邊，腰上繫一條米白繩帶、繩尾垂在右邊。人物的短袍只是下襬短一截。 */
  function robeShortArt(c, o, P) {
    const shape = pts([[17.4, 7.6], [24, 12.4], [30.6, 7.6], [36, 9], [44.6, 19.6], [40.4, 26.6], [34.6, 22.6], [34.4, 28], [39.4, 40.6], [8.6, 40.6], [13.6, 28], [13.4, 22.6], [7.6, 26.6], [3.4, 19.6], [12, 9]]);
    body(c, P.a, shape, 33);
    clip(c, shape, () => { f(c, P.d, () => c.rect(0, 37, 48, 5)); f(c, HI, () => c.rect(15, 13, 2, 22));
      for (const s of [-1, 1]) st(c, P.d, 3, (x) => { x.moveTo(24 + s * 14.4, 26.4); x.lineTo(24 + s * 21.4, 17); }, "butt"); });
    rr(c, P.d, 22.5, 11.4, 3, 26.4, 1); poly(c, P.t, [[18.4, 8.2], [24, 15], [29.6, 8.2], [27.8, 7.6], [24, 12.2], [20.2, 7.6]], 0.3);
    clip(c, shape, () => f(c, CREAM, () => c.rect(12, 27.6, 24, 2.6)));
    rr(c, CREAM, 28.4, 28.6, 2, 8, 1); rr(c, CREAM, 31.4, 28.6, 2, 6, 1); ci(c, CREAM, 30.2, 28.9, 2.1);
  }
  /** 皮背心：沒有袖子的皮背心（兩條寬肩帶、深 V 領、兩個袖洞）、從左肩斜到右腰的深色背帶（人物的 leather 就是這條斜背帶）、腰帶與金扣；領口與袖洞一圈淺皮色的滾邊。 */
  function vestArt(c, o, P) {
    const shape = (x) => { x.moveTo(13.6, 5.4); x.lineTo(19.4, 5.4); x.quadraticCurveTo(24, 17, 28.6, 5.4); x.lineTo(34.4, 5.4); x.quadraticCurveTo(34.4, 14, 39.6, 17.6); x.lineTo(38.4, 33); x.lineTo(40.8, 43); x.lineTo(7.2, 43); x.lineTo(9.6, 33); x.lineTo(8.4, 17.6); x.quadraticCurveTo(13.6, 14, 13.6, 5.4); x.closePath(); };
    body(c, P.a, shape, 33);
    clip(c, shape, () => { f(c, HI, () => c.rect(11.4, 19, 2.2, 21));
      st(c, P.t, 2.6, (x) => { x.moveTo(19.4, 5.4); x.quadraticCurveTo(24, 17, 28.6, 5.4); }, "butt");
      for (const s of [-1, 1]) st(c, P.t, 2.4, (x) => { x.moveTo(24 + s * 10.4, 5.4); x.quadraticCurveTo(24 + s * 10.4, 14, 24 + s * 15.6, 17.6); }, "butt");
      st(c, P.d, 3.4, (x) => { x.moveTo(14.4, 6); x.lineTo(37, 31); }, "butt"); f(c, P.t, () => c.rect(0, 40.6, 48, 3)); });
    if (!o.small) rr(c, GOLD, 23.6, 15.6, 3.6, 3.6, 0.8);
    belt(c, shape, 30.6);
  }
  /** 獵裝：有長袖的皮獵裝——兩隻袖子往外下方垂、深色袖口；左肩一片淺皮色的護肩（兩顆釘）、斜背帶、腰帶與金扣、立領。人物身上和皮背心同一件（沒有分）。 */
  function hunterArt(c, o, P) {
    const shape = pts([[17, 6.4], [24, 11.6], [31, 6.4], [36, 8], [44.4, 26.4], [38.6, 29.6], [34.8, 21], [35.2, 33], [37.6, 42], [10.4, 42], [12.8, 33], [13.2, 21], [9.4, 29.6], [3.6, 26.4], [12, 8]]);
    body(c, P.a, shape, 33.4);
    clip(c, shape, () => { f(c, HI, () => c.rect(15, 14, 2, 15));
      for (const s of [-1, 1]) st(c, P.d, 3.2, (x) => { x.moveTo(24 + s * 14.4, 29.6); x.lineTo(24 + s * 21.4, 25.4); }, "butt");
      st(c, P.d, 3.2, (x) => { x.moveTo(15, 9); x.lineTo(35.6, 30.4); }, "butt"); f(c, P.t, () => c.rect(0, 39.8, 48, 3)); });
    poly(c, P.t, [[17.8, 6.8], [24, 14.2], [30.2, 6.8], [28.4, 6], [24, 11.4], [19.6, 6]], 0.3);
    el(c, P.t, 11.4, 10.6, 7, 4.8, -0.5); st(c, P.d, 1.5, (x) => x.ellipse(11.4, 10.6, 6.2, 4, -0.5, Math.PI * 0.1, Math.PI * 0.9), "butt"); if (!o.small) ci(c, GOLD, 10.8, 9.6, 1.3);
    belt(c, shape, 30.4);
  }
  /** 鎖子甲：T 字形的短袖鎖子衫（袖子平伸到手肘）、圓領一圈深色邊、下襬剪成一排尖齒；甲面一格一格的深色鎖子點（人物的 mail 就是這樣的方點），腰帶與金扣。 */
  function chainArt(c, o, P) {
    const hem = []; for (let i = 0; i <= 6; i++) hem.push([35.4 - i * 3.8, i % 2 ? 44 : 39.6]);
    const P0 = [[17, 6.2], [24, 11], [31, 6.2], [36, 7.6], [44.4, 15.4], [41, 24.4], [35.4, 21.4], ...hem, [12.6, 21.4], [7, 24.4], [3.6, 15.4], [12, 7.6]], shape = pts(P0);
    body(c, P.a, shape, 33.6);
    clip(c, shape, () => { c.fillStyle = P.d; const s = o.small ? 4.8 : 4, q = o.small ? 2 : 1.7; let row = 0;
      for (let y = 13; y < 44; y += s, row++) for (let x = 4 + (row % 2 ? s / 2 : 0); x < 45; x += s) c.fillRect(x, y, q, q);
      f(c, HI2, () => c.rect(14, 12.6, 1.8, 15));
      for (const k of [-1, 1]) st(c, P.d, 3, (x) => { x.moveTo(24 + k * 13, 22); x.lineTo(24 + k * 20.4, 25.6); }, "butt");
      st(c, P.d, 2.8, (x) => { x.moveTo(17, 6.2); x.lineTo(24, 11); x.lineTo(31, 6.2); }, "butt"); });
    belt(c, shape, 29.6);
  }
  /** 鱗甲：沒有袖子的鱗甲背心——兩肩各一片圓的肩片、下襬是四片大圓鱗；甲面一排排 U 形魚鱗（人物的 mail・scale 就是 U 形鱗片），腰帶與金扣。和鎖子甲分開：沒有袖子、下襬是圓的、紋路是大 U 形。 */
  function scaleArt(c, o, P) {
    const shape = (x) => { x.moveTo(15.4, 6.4); x.quadraticCurveTo(24, 12.6, 32.6, 6.4); x.lineTo(37, 7); x.quadraticCurveTo(43.6, 9.4, 42.6, 16.4); x.lineTo(36.6, 19); x.lineTo(37.4, 30); x.lineTo(41, 39.4);
      for (let i = 0; i < 4; i++) x.arc(36.75 - i * 8.5, 39.4, 4.25, 0, Math.PI); x.lineTo(10.6, 30); x.lineTo(11.4, 19); x.lineTo(5.4, 16.4); x.quadraticCurveTo(4.4, 9.4, 11, 7); x.closePath(); };
    body(c, P.a, shape, 33.6);
    clip(c, shape, () => { let row = 0;
      for (const y of [12.6, 18.4, 24.2, 35.4]) { for (let x = 3.6 + (row % 2 ? 3.6 : 0); x < 46; x += 7.2) { f(c, P.l, (k) => k.arc(x, y, 3.3, Math.PI * 1.1, Math.PI * 1.9)); st(c, P.d, 1.4, (k) => k.arc(x, y, 3.5, 0.08 * Math.PI, 0.92 * Math.PI), "butt"); } row++; }
      st(c, P.d, 2.6, (x) => { x.moveTo(15.4, 6.4); x.quadraticCurveTo(24, 12.6, 32.6, 6.4); }, "butt"); });
    belt(c, shape, 28.6);
  }
  /** 半身板甲：鋼板胸甲——兩肩、V 領、收腰、下襬外張；左胸一塊亮面（人物的 plate 也有）、正中一道稜線、腰上一條深色帶加金扣。和風格樣張對照 9 的胸甲同一件。 */
  function plateArt(c, o, P) {
    const P0 = [[11.5, 8.5], [19, 6], [24, 11.5], [29, 6], [36.5, 8.5], [42, 16.5], [37.5, 22.5], [37.5, 33], [41, 42.5], [7, 42.5], [10.5, 33], [10.5, 22.5], [6, 16.5]];
    poly(c, P.a, P0, 1.2);
    f(c, SH, pts([[33, 7.6], [36.5, 8.5], [42, 16.5], [37.5, 22.5], [37.5, 33], [41, 42.5], [34, 42.5], [33, 33]]));
    rr(c, mix(P.a, "#ffffff", 0.6), 13.5, 14, 8.6, 11.5, 3.2);
    if (!o.small) f(c, P.d, () => c.rect(23.3, 13, 1.4, 19.5));
    rr(c, P.d, 9.6, 31.4, 28.8, 4, 1.2); rr(c, GOLD, 21, 30.6, 6, 5.6, 1.2);
  }
  /** 全身板甲：同一件胸甲縮窄，兩肩各加一顆亮一階的大圓肩甲（人物的全身板甲就是多兩顆亮肩甲）、頸口一圈護頸、腰下兩層裙甲片。剪影是「兩顆圓肩＋層層往下張」。 */
  function plateFullArt(c, o, P) {
    const chest = pts([[14, 9], [20, 7], [24, 11.6], [28, 7], [34, 9], [36.4, 20], [35.6, 31.6], [12.4, 31.6], [11.6, 20]]);
    for (const [y, w] of [[38.6, 31.6], [34, 27.6]]) { rr(c, P.a, 24 - w / 2, y, w, 5.6, 2); f(c, P.d, () => c.rect(24 - w / 2 + 1, y + 4.2, w - 2, 1.3)); f(c, SH, () => c.rect(33.4, y, w / 2 - 9.4, 4.2)); }
    body(c, P.a, chest, 31.6);
    rr(c, mix(P.a, "#ffffff", 0.6), 15.4, 14.6, 7, 10, 2.8);
    if (!o.small) f(c, P.d, () => c.rect(23.3, 13, 1.4, 17));
    rr(c, P.d, 11.6, 29.8, 24.8, 3.8, 1.2); rr(c, GOLD, 21.2, 29, 5.6, 5.4, 1.2);
    rr(c, P.d, 18.4, 5, 11.2, 4, 1.8);
    for (const s of [-1, 1]) { el(c, P.l, 24 + s * 13.4, 13.6, 7.4, 6.4, s * 0.35); st(c, P.d, 1.5, (x) => x.ellipse(24 + s * 13.4, 13.6, 6.6, 5.6, s * 0.35, Math.PI * 0.1, Math.PI * 0.9), "butt"); }
    el(c, HI2, 8.6, 11, 2.4, 1.5, -0.5);
  }
  /** 旅行外套：過膝的長外套——兩隻袖子貼著身體垂下來、下襬正中開一個衩（人物的 coat 就是這個倒 V 開衩）、深色翻領、門襟右邊三顆金扣、深色袖口與口袋蓋。 */
  function coatArt(c, o, P, sleeves = true) {
    const P0 = sleeves ? [[15.4, 5.6], [32.6, 5.6], [37, 8], [43.8, 30], [38.2, 32], [35.8, 21], [37.4, 43.6], [28.2, 43.6], [24, 31.6], [19.8, 43.6], [10.6, 43.6], [12.2, 21], [9.8, 32], [4.2, 30], [11, 8]]
      : [[15.4, 5.6], [32.6, 5.6], [36, 8], [35.4, 21], [36.4, 43.6], [28.2, 43.6], [24, 31.6], [19.8, 43.6], [11.6, 43.6], [12.6, 21], [12, 8]], shape = pts(P0);
    body(c, P.a, shape, 32.6);
    clip(c, shape, () => { f(c, HI, () => c.rect(14.4, 12, 2, 26));
      if (sleeves) for (const s of [-1, 1]) st(c, P.d, 3.2, (x) => { x.moveTo(24 + s * 14, 31.6); x.lineTo(24 + s * 20.6, 29.4); }, "butt"); });
    f(c, P.d, pts([[17.4, 5.6], [24, 17.4], [30.6, 5.6]]));
    for (const s of [-1, 1]) f(c, P.t, pts([[24 + s * 9.4, 5.6], [24 + s * 6.6, 5.6], [24, 17.4], [24 + s * 2.4, 19.4], [24 + s * 9, 11.6]]));
    f(c, P.d, () => c.rect(23.4, 18.6, 1.2, 16.4));
    for (const y of [22.4, 27.6, 32.8]) ci(c, GOLD, 27.2, y, 1.6);
    if (!o.small && sleeves) rr(c, P.d, 14, 30.6, 5.6, 2, 0.8);
  }
  /** 披風外套（第 2 版重畫）：窄肩＋立領（領口正中一個凹口）、背後一片暗一階的披風從兩肩往下張開（底邊三個波浪、下襬淺色邊）；披風前襟拉開，露出中間的外套身（米色翻領夾深色 V、門襟、三顆金扣、下襬開衩）
   *  與左邊一隻垂下來的袖子（深色袖口）；右邊的披風前襟搭在肩上往下垂（內緣一道淺色邊）；胸口一條金鍊扣住兩邊。人物身上和旅行外套同一件（沒有分）。
   *  第 1 版是「梯形＋上緣一條金鍊」，沒有肩也沒有袖，48px 以下像金腰頭的百褶裙、鈴鐺。 */
  function capeCoatArt(c, o, P) {
    const capeC = mix(P.a, P.d, 0.45);
    const cape = (x) => { x.moveTo(16.4, 8.6); x.quadraticCurveTo(10.6, 9.2, 9.8, 14.6); x.lineTo(3.4, 39.6); x.quadraticCurveTo(7, 44.6, 10.6, 40.6); x.quadraticCurveTo(24, 46.4, 37.4, 40.6); x.quadraticCurveTo(41, 44.6, 44.6, 39.6); x.lineTo(38.2, 14.6); x.quadraticCurveTo(37.4, 9.2, 31.6, 8.6); x.closePath(); };
    f(c, capeC, cape);
    clip(c, cape, () => { f(c, SH, () => c.rect(39, 0, 12, 48)); st(c, P.t, 2.4, (x) => { x.moveTo(11.4, 44.6); x.lineTo(2, 40.4); }, "butt"); });
    const coat = pts([[16.8, 8.6], [31.2, 8.6], [33.6, 14.6], [34.8, 42.6], [27.6, 42.6], [24, 33.4], [20.4, 42.6], [13.2, 42.6], [14.4, 14.6]]), arm = pts([[15.4, 9.8], [11, 12], [6.8, 30.4], [12, 32], [15.6, 17.6]]);
    halo(c, o, (x) => {
      body(x, P.a, coat, 31.6); f(x, P.a, arm);
      clip(x, arm, () => st(x, P.d, 3.2, (k) => { k.moveTo(5.4, 27.6); k.lineTo(13.6, 30); }, "butt"));
      clip(x, coat, () => f(x, HI, () => x.rect(16.4, 17, 1.8, 21)));
      f(x, P.d, pts([[19.4, 8.6], [24, 18], [28.6, 8.6]]));
      for (const s of [-1, 1]) f(x, P.t, pts([[24 + s * 7.6, 8.6], [24 + s * 4.6, 8.6], [24, 18], [24 + s * 2.6, 20.4], [24 + s * 8.4, 13.6]]));
      f(x, P.d, () => x.rect(23.4, 19.6, 1.2, 14.4));
      for (const y of [24, 29.2, 34.4]) ci(x, GOLD, 27.4, y, 1.6);
    });
    /* 右邊的披風前襟：從右肩往下垂、蓋住外套身的右緣 */
    const flap = (x) => { x.moveTo(30.4, 8.6); x.quadraticCurveTo(37.4, 9.2, 38.2, 14.6); x.lineTo(44.6, 39.6); x.quadraticCurveTo(41, 44.6, 37.4, 40.6); x.lineTo(34.2, 41.8); x.quadraticCurveTo(33.4, 22, 30.4, 8.6); x.closePath(); };
    halo(c, o, (x) => { f(x, capeC, flap); clip(x, flap, () => { f(x, SH, () => x.rect(39, 0, 12, 48)); st(x, P.t, 2.2, (k) => { k.moveTo(30.4, 8.6); k.quadraticCurveTo(33.4, 22, 34.2, 41.8); }, "butt"); st(x, P.t, 2.4, (k) => { k.moveTo(36.6, 44.6); k.lineTo(46, 40.4); }, "butt"); }); });
    /* 立領：兩片領尖往上、正中一個凹口 */
    halo(c, o, (x) => { f(x, P.a, pts([[15.6, 10.4], [17.2, 4], [24, 9], [30.8, 4], [32.4, 10.4], [24, 12.4]])); f(x, HI, pts([[17.2, 4], [19.4, 5.6], [18, 10], [16, 10.2]])); f(x, SH, pts([[30.8, 4], [32.4, 10.4], [29.6, 11], [28.6, 5.6]])); });
    st(c, GOLD, 1.6, (x) => { x.moveTo(17.6, 14.4); x.quadraticCurveTo(24.4, 19.6, 31.6, 14.4); }, "butt");
    ci(c, GOLD, 17.2, 14, 2.1); ci(c, GOLD, 32, 14, 2.3); ci(c, GOLDL, 31.4, 13.4, 0.8);
  }

  // =====================================================================
  // 手（人物身上只看得到拳頭的顏色、露指手套的膚色指頭、鎖鏈護手的喇叭袖口與護腕的一圈帶子；圖示照現行的題材：一隻手背朝外、四指朝上、拇指在左的手套）
  // =====================================================================
  const FX = [15.4, 22, 28.6, 35.2], FW = 5.2;
  /** 四根手指：tops＝各指頂端的 y、bot＝指根的 y、fan＝張開的角度；pointed＝尖指甲套（板金護手）。指縫 1.4 單位，外框會把它填成深色。 */
  function fingers(c, col, tops, bot = 28, fan = 0, pointed = false) {
    FX.forEach((x, i) => { c.save(); c.translate(x + FW / 2, 28); c.rotate((i - 1.5) * fan);
      if (pointed) poly(c, col, [[-FW / 2, bot - 28], [-FW / 2, tops[i] - 24], [0, tops[i] - 28], [FW / 2, tops[i] - 24], [FW / 2, bot - 28]], 0.3);
      else rr(c, col, -FW / 2, tops[i] - 28, FW, bot - tops[i], Math.min(2.6, (bot - tops[i]) / 2)); c.restore(); });
  }
  const palm = (c, col) => rr(c, col, 14.6, 21.4, 26.6, 15, 4.5), thumb = (c, col) => el(c, col, 12, 25.6, 3.3, 7.6, -0.55), TOPS = [9.6, 5.6, 7, 12];
  /** 素手套：五指張開的薄布手套、手腕一截直筒、腕口一道深色收邊，手背三道淺色的車縫線。 */
  function clothGloveArt(c, o, P) {
    rr(c, P.a, 18, 33, 19.6, 10.6, 2.4);
    fingers(c, P.a, TOPS, 28, 0.085); thumb(c, P.a); palm(c, P.a);
    f(c, SH, (x) => x.roundRect(36.4, 21.4, 4.8, 15, [0, 4.5, 4.5, 0]));
    f(c, HI, () => c.rect(16.4, 12, 1.5, 12));
    if (!o.small) for (const x of [22.6, 27.8, 33]) rr(c, P.t, x, 24, 1.3, 7, 0.6);
    rr(c, P.d, 16.8, 38.4, 22, 5.2, 1.8); f(c, P.t, () => c.rect(18, 39.6, 19.6, 1.2));
  }
  /** 露指手套：手指只包到第一節，露出四根膚色的指頭與拇指尖（人物的 fingerless 也是露出膚色指頭），指根各一道深色收口，手腕一圈深色寬帶加一顆金扣。 */
  function fingerlessArt(c, o, P) {
    rr(c, P.a, 18, 34, 19.6, 9.6, 2.4);
    const TIP = [11.6, 8, 9.4, 14], CUT = [18.6, 16, 17, 20];
    fingers(c, M.skin, TIP); fingers(c, P.a, CUT); FX.forEach((x, i) => rr(c, P.d, x, CUT[i], FW, 2.2, 0.8));
    thumb(c, M.skin); clip(c, (x) => x.rect(0, 23.4, 48, 30), () => thumb(c, P.a)); st(c, P.d, 1.8, (x) => { x.moveTo(9.6, 22.4); x.lineTo(14.4, 25.4); }, "butt");
    palm(c, P.a); f(c, SH, (x) => x.roundRect(36.4, 21.4, 4.8, 15, [0, 4.5, 4.5, 0]));
    if (!o.small) FX.forEach((x, i) => ci(c, "#ffe2c8", x + 1.7, TIP[i] + 2, 0.9));
    rr(c, P.d, 16.6, 34.6, 22.4, 5, 1.6); rr(c, GOLD, 25.6, 34.2, 4.6, 5.8, 1.1);
  }
  /** 短皮手套：四指併攏的皮手套，手腕一圈往外翻、比手還寬的淺皮色厚翻口，翻口上三顆金釘（現行圖示也是腕帶加三顆金釘），翻口上緣一道深色陰影。 */
  function leatherGloveArt(c, o, P) {
    fingers(c, P.a, TOPS); thumb(c, P.a); palm(c, P.a);
    f(c, SH, (x) => x.roundRect(36.4, 21.4, 4.8, 15, [0, 4.5, 4.5, 0]));
    for (const x of [16.6, 23.2]) f(c, HI, () => c.rect(x, x < 20 ? 12 : 8.4, 1.5, 11));
    rr(c, P.d, 13.6, 31.6, 28.4, 3.4, 1.4);
    rr(c, P.t, 11.4, 33.4, 32.8, 10.4, 4);
    f(c, "rgba(0,0,0,0.16)", (x) => x.roundRect(36, 33.4, 8.2, 10.4, [0, 4, 4, 0]));
    for (const x of [18.2, 27.8, 37.4]) { ci(c, GOLD, x, 38.6, 1.9); ci(c, GOLDL, x - 0.5, 38.1, 0.7); }
  }
  /** 長皮手套：手縮小，手腕以下接一截往手肘張開的長喇叭筒（騎士手套）；筒口一圈淺皮色的邊、筒身一道深色的開衩用米白皮繩交叉綁起來、腕上一顆金扣。 */
  function longGloveArt(c, o, P) {
    const cuff = pts([[19.6, 24], [36.6, 24], [42.6, 43.6], [10.6, 43.6]]);
    at(c, 0.7, 0, -5.8, (x) => { fingers(x, P.a, TOPS); thumb(x, P.a); palm(x, P.a); f(x, HI, () => x.rect(16.6, 12, 1.8, 11)); });
    body(c, P.a, cuff, 35.6);
    clip(c, cuff, () => { f(c, P.t, () => c.rect(0, 39.4, 48, 5)); f(c, HI, () => c.rect(16.6, 27, 1.8, 11)); });
    f(c, P.d, pts([[27, 26.6], [29.4, 26.6], [30.6, 39.4], [26, 39.4]]));
    if (!o.small) for (const y of [29, 32.8, 36.6]) st(c, CREAM, 1.2, (x) => { x.moveTo(25.4, y - 0.8); x.lineTo(31.2, y + 0.8); }, "butt");
    rr(c, P.d, 18.2, 22.6, 19.8, 3.2, 1.2); ci(c, GOLD, 23.2, 24.2, 1.9);
  }
  /** 板金護手：鋼板護手——四根尖頭的指甲套（上半節亮一階）、一整片亮色的指節護板（四顆鉚釘）、手背甲片，手腕以下是一截往外張、下緣收成尖角的腕甲。稜角分明，和布、皮手套的圓指頭分開。 */
  function gauntletArt(c, o, P) {
    const cuff = [[15.6, 33], [40, 33], [43.6, 40.4], [27.8, 43.6], [12, 40.4]];
    poly(c, P.a, cuff, 0.6); clip(c, pts(cuff), () => { f(c, SH, () => c.rect(35.4, 0, 12, 48)); f(c, HI2, () => c.rect(15.6, 35.4, 1.8, 5)); });
    fingers(c, P.a, [8.6, 4.6, 6, 11], 28, 0, true);
    FX.forEach((x, i) => { const t = [8.6, 4.6, 6, 11][i]; poly(c, P.l, [[x, t + 9], [x, t + 4], [x + FW / 2, t], [x + FW, t + 4], [x + FW, t + 9]], 0.3); f(c, P.d, () => c.rect(x, t + 9.2, FW, 1.3)); });
    el(c, P.a, 11.4, 25.6, 3.3, 7.6, -0.55); poly(c, P.l, [[8.2, 21.6], [6.6, 17], [10.6, 19.6]], 0.4);
    palm(c, P.a); f(c, SH, (x) => x.roundRect(36.4, 21.4, 4.8, 15, [0, 4.5, 4.5, 0]));
    rr(c, P.l, 13.8, 19.6, 28.2, 6, 2.2); if (!o.small) for (const x of [18, 24.6, 31.2, 37.8]) ci(c, P.d, x, 22.6, 1);
    rr(c, P.d, 14.6, 31.6, 26.4, 3.2, 1.2);
  }
  /** 鎖鏈護手：四指併攏的鎖鏈手套（圓頭、上半三道指縫）＋拇指，手腕以下一截喇叭袖口、袖口一道深色邊（人物的 gauntlets・mail 就是喇叭袖口加鎖子點）；整隻佈滿鎖子點。 */
  function mailMittArt(c, o, P) {
    const mitt = (x) => { x.moveTo(15, 31); x.lineTo(15, 15); x.quadraticCurveTo(15, 5.4, 28, 5.4); x.quadraticCurveTo(41, 5.4, 41, 15); x.lineTo(41, 31); x.closePath(); }, cuff = pts([[15.6, 29.4], [40.4, 29.4], [44, 43], [12, 43]]);
    const dots = (path, y0, y1) => clip(c, path, () => { c.fillStyle = P.d; const s = o.small ? 4.8 : 4, q = o.small ? 2 : 1.7; let row = 0; for (let y = y0; y < y1; y += s, row++) for (let x = 12 + (row % 2 ? s / 2 : 0); x < 45; x += s) c.fillRect(x, y, q, q); });
    thumb(c, P.a); body(c, P.a, cuff, 36.4); dots(cuff, 32.4, 39);
    clip(c, cuff, () => { f(c, P.l, () => c.rect(0, 39.2, 48, 5)); f(c, P.d, () => c.rect(0, 38.2, 48, 1.2)); });
    body(c, P.a, mitt, 36); dots(mitt, 9, 28); f(c, HI2, (x) => x.roundRect(17, 9.6, 2.6, 15, 1.3));
    /* 第 2 版：整塊圓頭沒有指縫，像隔熱手套。上半挖三道指縫（真的挖空，外框會把它填成深色線、頂端切成四個圓指頭） */
    c.save(); c.globalCompositeOperation = "destination-out"; for (const [x, y] of [[21.5, 4.6], [28, 3.6], [34.5, 5]]) rr(c, "#000", x - 0.6, y, 1.2, 15.4 - (y - 3.6), 0.6); c.restore();
    rr(c, P.d, 13.8, 28.2, 28.4, 3, 1.2);
  }
  /** 皮臂甲：一片包住前臂的皮護臂——（第 2 版上下顛倒：窄的手腕端朝上、露出膚色的手，斜的手肘端朝下）兩端各一道淺皮色的滾邊；正中一道深色開衩用米白皮繩交叉綁起來、兩道深色束帶各一顆金釘（現行圖示是梯形加三道帶扣）。整個往左斜一點。人物手腕上是一圈護腕帶加一道深色線。第一稿是「看得到筒口的皮筒」，像水桶，改掉了。 */
  function bracerArt(c, o, P) {
    const sh = (x) => { x.moveTo(9.4, 14.6); x.quadraticCurveTo(8.4, 4.6, 16, 4.6); x.quadraticCurveTo(28, 7.4, 38, 12.6); x.lineTo(33.4, 40.4); x.quadraticCurveTo(24, 44.4, 14.6, 40.4); x.closePath(); };
    /* 第 2 版：不看名稱不知道戴在哪。整片上下顛倒（窄的手腕端朝上、斜的手肘端朝下）、壓短，上端露出一小截膚色的手腕與握起來的手（拇指在左、三道指節線），和手套同一個方向 */
    rr(c, M.skin, 18.6, 9, 11.6, 8, 2); rr(c, M.skin, 16.2, 2.8, 16.4, 9.6, 4.2); el(c, M.skin, 15.6, 9, 2.6, 4.2, -0.5);
    f(c, "rgba(0,0,0,0.14)", (x) => x.roundRect(28.6, 2.8, 4, 9.6, [0, 4.2, 4.2, 0])); el(c, "#ffe2c8", 19.6, 5.4, 1.8, 1.1, -0.4);
    if (!o.small) for (const x of [20.8, 24.6, 28.4]) f(c, "#c99a78", () => c.rect(x, 3.4, 1, 4.2));
    c.save(); c.translate(0, 44.6); c.scale(1, -0.8); c.translate(0, -4.6); /* 上下顛倒：原本 y 4.6（上緣）→ 44.6（下緣），y 44.4 → 12.8 */
    at(c, 1, 0.6, 0, (k) => {
      body(k, P.a, sh, 31);
      clip(k, sh, () => { f(k, HI, () => k.rect(12.6, 12, 2.2, 26));
        st(k, P.t, 4.4, (x) => { x.moveTo(8.4, 6); x.quadraticCurveTo(12, 3.6, 16, 4.6); x.quadraticCurveTo(28, 7.4, 38, 12.6); }, "butt"); st(k, P.t, 4.6, (x) => { x.moveTo(13, 40.4); x.quadraticCurveTo(24, 45, 35, 40.4); }, "butt");
        for (const y of [17.6, 29.4]) st(k, P.d, 2.8, (x) => { x.moveTo(8, y - 1.6); x.quadraticCurveTo(24, y + 3.4, 40, y + 0.6); }, "butt"); });
      rr(k, P.d, 21.6, 10.4, 3.4, 27.6, 1.4);
      for (let i = 0; i < 5; i++) st(k, CREAM, 1.5, (x) => { x.moveTo(20.2, 12.6 + i * 5.4 + (i % 2 ? 2.2 : 0)); x.lineTo(26.4, 12.6 + i * 5.4 + (i % 2 ? 0 : 2.2)); }, "round");
      for (const y of [19.6, 31.4]) { ci(k, GOLD, 32.4 - (y > 25 ? 1.6 : 0), y, 1.9); }
    }, -0.08);
    c.restore();
  }
  /** 臂環：一個平放的寬金屬環（從斜上方看）：看得到環的上緣（亮一階）、環內側的後壁（暗一階）與穿過去的洞；正面的環壁上一顆菱形寶石、兩側各一顆圓釘。
   *  和戒指分開的地方：戒指是立著的圓圈、寶石在頂上；臂環是橫躺的扁寬橢圓、寶石在正面。人物手腕上是一圈護腕帶。 */
  function armRingArt(c, o, P) {
    const cy = 19, h = 9.4, E = (x, y, rx, ry) => x.ellipse(24, y, rx, ry, 0, 0, TAU);
    f(c, P.a, (x) => { E(x, cy + h, 19.6, 11); x.rect(4.4, cy, 39.2, h); });
    clip(c, (x) => { E(x, cy + h, 19.6, 11); x.rect(4.4, cy, 39.2, h); }, () => { f(c, SH, () => c.rect(34, 0, 12, 48)); f(c, HI2, () => c.rect(7.4, 22, 1.8, 9)); f(c, P.d, (x) => { x.ellipse(24, cy + h, 19.6, 11, 0, 0, Math.PI); x.ellipse(24, cy + h - 2.2, 19.6, 11, 0, Math.PI, 0, true); }); });
    f(c, P.l, (x) => E(x, cy, 19.6, 11));
    f(c, P.d, (x) => E(x, cy, 14.6, 7));
    c.save(); c.beginPath(); E(c, cy, 14.6, 7); c.clip(); c.globalCompositeOperation = "destination-out"; f(c, "#000", (x) => E(x, cy + h * 0.62, 14.6, 7)); c.restore();
    rr(c, GOLD, 19.6, 30.4, 8.8, 8.8, 2); gem(c, P.accent, 24, 34.8, 3.4, o);
    if (!o.small) for (const x of [11.6, 36.4]) ci(c, P.l, x, 31.6, 1.5);
  }

  // =====================================================================
  // 腳（qDoll.js 的 leg()：靴筒是材質本色、腳掌是暗一階；布鞋沒有靴筒）。全部畫單隻側面、鞋尖朝右（現行圖示也是）。
  // =====================================================================
  /** 一隻靴：靴筒（x0～x0+sw、頂在 top）＋往右伸的腳掌＋鞋底。 */
  function bootBody(c, col, top, x0 = 8, sw = 15.5) {
    rr(c, col, x0, top, sw, 34 - top, 4);
    f(c, col, (x) => { x.moveTo(x0, 24.5); x.lineTo(x0 + sw - 0.5, 24.5); x.quadraticCurveTo(38.5, 26, 40, 35.6); x.lineTo(40, 39.4); x.lineTo(x0, 39.4); x.closePath(); });
  }
  const toeShade = (c, x0 = 8, sw = 15.5) => f(c, "rgba(0,0,0,0.2)", (x) => { x.moveTo(x0 + sw + 0.5, 26.6); x.quadraticCurveTo(36.4, 28, 38.2, 36.4); x.lineTo(x0 + sw + 0.5, 36.4); x.closePath(); });
  /** 布鞋：一隻低口的平底布鞋——沒有靴筒（人物的 shoes 也沒有）、圓鞋頭、鞋口一圈淺色滾邊與深色的鞋內、腳背一條扣帶加一顆米白布扣、白色的千層底。 */
  function slipperArt(c, o, P) {
    const up = (x) => { x.moveTo(4.4, 33.4); x.quadraticCurveTo(3.6, 17.4, 12, 16.6); x.lineTo(22.6, 17.4); x.quadraticCurveTo(27, 24.6, 33.6, 24.6); x.quadraticCurveTo(43.4, 25.4, 44.4, 32.6); x.lineTo(44.4, 34.6); x.lineTo(4.4, 34.6); x.closePath(); };
    body(c, P.a, up, 36.4);
    el(c, P.t, 14.4, 18.6, 9.4, 3.4, 0.1); el(c, P.dd, 14.8, 19.2, 7.2, 2);
    clip(c, up, () => { st(c, P.d, 3.2, (x) => { x.moveTo(22.4, 16.6); x.lineTo(27.4, 34); }, "butt"); f(c, HI, () => c.rect(31, 26.4, 8, 1.8)); });
    ci(c, CREAM, 25.6, 25.6, 1.9);
    rr(c, "#e6e6e0", 3.6, 33.4, 41.2, 5.2, 2.2); if (!o.small) f(c, "#a8a69c", () => c.rect(5.6, 36.4, 37.2, 1));
  }
  /** 綁腿鞋：同一款布鞋（縮小），腳踝以上用布條一圈一圈斜纏到小腿（淺色與本色相間），頂端平口，腳踝後側一個短結。現行圖示也是鞋加斜纏的綁腿。 */
  function wrappedArt(c, o, P) {
    const leg = (x) => x.roundRect(9.6, 5, 13.6, 29, 3.4);
    /* 第 2 版：頂端往左翹的布條尾巴讓整隻像數字「1」，拿掉（頂端平口）；改成腳踝後側一個短結、兩條短尾巴往下垂 */
    f(c, P.t, pts([[9.8, 21.4], [4.2, 27.4], [6.6, 29.4], [10.4, 25]])); f(c, mix(P.t, P.d, 0.35), pts([[10, 22.6], [7.4, 31.4], [10, 32], [11.4, 25]]));
    body(c, P.a, leg, 19.4);
    clip(c, leg, () => { for (let y = 3; y < 34; y += 7.4) st(c, P.t, 3.2, (x) => { x.moveTo(8, y + 5); x.lineTo(25, y); }, "butt"); f(c, SH, () => c.rect(19.6, 0, 6, 48)); });
    f(c, P.a, (x) => { x.moveTo(9.6, 26.4); x.lineTo(22.4, 26.4); x.quadraticCurveTo(36.4, 27.4, 41, 34); x.lineTo(41, 37.6); x.lineTo(9.6, 37.6); x.closePath(); });
    f(c, HI, () => c.rect(27, 30.4, 8, 1.6)); st(c, P.d, 2.8, (x) => { x.moveTo(9.6, 27.2); x.lineTo(23.2, 27.2); }, "butt"); ci(c, P.t, 9.4, 22.4, 2.3);
    rr(c, "#e6e6e0", 8.4, 37, 34.2, 5.2, 2.2); if (!o.small) f(c, "#a8a69c", () => c.rect(10.4, 40, 30.2, 1));
  }
  /** 短靴：一隻到腳踝的皮短靴——米色的翻口、腳踝一條深色束帶加金扣、深色靴底（人物腳上是皮色靴筒＋暗一階的腳掌）。和風格樣張對照 9 的皮短靴同一款（樣張原本畫一雙，這批改成單隻放大）。 */
  function bootShortArt(c, o, P) {
    at(c, 1.12, 0.6, -5, (x) => { bootBody(x, P.a, 14.6); toeShade(x); f(x, HI, () => x.rect(10.6, 21, 2.6, 13));
      rr(x, P.d, 7.6, 25.4, 16.4, 3, 1); rr(x, GOLD, 17.6, 24.6, 4.4, 4.6, 1);
      rr(x, mix(P.d, "#000000", 0.2), 6.6, 38.2, 34.8, 5, 2.2); rr(x, P.t, 6.4, 11.6, 18.6, 8.2, 3); f(x, "rgba(0,0,0,0.14)", (k) => k.roundRect(19.4, 11.6, 5.6, 8.2, [0, 3, 3, 0])); f(x, HI, (k) => k.ellipse(31.4, 30.4, 3.6, 1.3, 0.35, 0, TAU)); });
  }
  /** 長靴：及膝的長筒皮靴——靴口一圈往外翻、比靴筒寬的淺皮色大翻口，靴筒上兩條深色束帶各一顆金扣（現行圖示是兩顆金釘），深色靴底。 */
  function bootTallArt(c, o, P) {
    at(c, 1, 2, 0, (x) => { bootBody(x, P.a, 9, 9, 14); toeShade(x, 9, 14); f(x, HI, () => x.rect(11.4, 15, 2, 19));
      for (const y of [17.6, 24.6]) { rr(x, P.d, 8.6, y, 14.8, 2.8, 1); rr(x, GOLD, 17.4, y - 0.8, 4.2, 4.4, 1); }
      rr(x, mix(P.d, "#000000", 0.2), 7.6, 38.2, 33.8, 5, 2.2);
      poly(x, P.t, [[6, 5], [26, 5], [24.2, 13.6], [7.8, 13.6]], 1.2); f(x, "rgba(0,0,0,0.14)", pts([[20.6, 4], [27, 4], [25, 14.6], [20, 14.6]])); f(x, P.d, () => x.rect(9.4, 14.4, 13.2, 1.3)); });
  }
  /** 鐵靴：一隻到小腿的圓頭鐵靴——靴口一圈深色的箍（三顆亮釘）、靴筒兩道甲片接縫、亮一階的圓鞋頭護片、厚鞋底（人物的 iron_boots：材質色靴筒＋較大的腳掌）。 */
  function ironBootArt(c, o, P) {
    at(c, 1.06, 1.4, -0.6, (x) => { bootBody(x, P.a, 9.6, 8, 17);
      clip(x, (k) => { k.moveTo(8, 24.5); k.lineTo(24.5, 24.5); k.quadraticCurveTo(38.5, 26, 40, 35.6); k.lineTo(40, 39.4); k.lineTo(8, 39.4); k.closePath(); }, () => { f(x, P.l, () => x.rect(30.4, 20, 12, 22)); f(x, P.d, () => x.rect(29.2, 20, 1.4, 22)); });
      f(x, HI2, () => x.rect(10.4, 15, 2, 19)); for (const y of [18.6, 25.2]) f(x, P.d, () => x.rect(8, y, 17, 1.4));
      f(x, SH, () => x.rect(20.6, 14.4, 4.4, 10)); rr(x, mix(P.d, "#000000", 0.35), 6.6, 38, 34.8, 5.4, 2.2);
      rr(x, P.d, 6.8, 8.6, 19.4, 5, 2.2); if (!o.small) for (const k of [10.4, 16.5, 22.6]) ci(x, P.l, k, 11.1, 1.1); });
  }
  /** 尖頭鐵靴：鞋頭拉成一根往前翹的長尖（兩片腳背甲片、弧形分界）、靴筒比鐵靴短、腳跟一根金色馬刺（刺輪）。剪影是「短筒＋長尖頭＋腳跟一顆星」。 */
  function sabatonArt(c, o, P) {
    const foot = (x) => { x.moveTo(9, 24.6); x.lineTo(23, 24.6); x.quadraticCurveTo(33, 27.4, 44.6, 29.6); x.quadraticCurveTo(40.6, 36, 33.6, 37.6); x.lineTo(9, 37.6); x.closePath(); };
    ln(c, GOLD, 2, [[10, 32.6], [6.6, 34.4]]); poly(c, GOLD, starPts(6.4, 34.6, 3, 1.3, 6), 0.2);
    rr(c, P.a, 9, 9.6, 14.6, 24, 3.6); f(c, HI2, () => c.rect(11.4, 15.6, 2, 12)); f(c, SH, () => c.rect(19.6, 14.6, 4, 10));
    body(c, P.a, foot, null);
    /* 第 2 版：三片亮暗相間的斜條像鑽頭。減成兩片、分界改成往鞋尖鼓的弧線：腳背一片（本色）、鞋尖一片（亮一階） */
    clip(c, foot, () => { f(c, P.l, (x) => { x.moveTo(33.4, 22); x.quadraticCurveTo(38.6, 30, 32.4, 40); x.lineTo(48, 40); x.lineTo(48, 22); x.closePath(); });
      for (const x0 of [25.4, 33.4]) st(c, P.d, 1.5, (x) => { x.moveTo(x0, 22); x.quadraticCurveTo(x0 + 5.2, 30, x0 - 1, 40); }, "butt");
      f(c, HI2, () => c.rect(27.6, 27.4, 3.4, 1.3)); });
    for (const y of [18.4]) f(c, P.d, () => c.rect(9, y, 14.6, 1.4));
    rr(c, mix(P.d, "#000000", 0.35), 7.6, 37, 28.4, 5, 2.2);
    rr(c, P.d, 7.8, 8.6, 17, 4.8, 2.2); if (!o.small) for (const k of [11.4, 16.3, 21.2]) ci(c, P.l, k, 11, 1.1);
  }
  /** 脛甲：一片護住小腿的長甲片——前緣（右邊）鼓出來、正中一道亮色的稜線、上緣一道捲邊；後面（左邊）兩條皮帶扣；腳踝一道深色箍，底下是暗一階的鐵鞋與鞋底（人物的 greaves：最高的靴筒＋暗一階的腳掌）。 */
  function greaveArt(c, o, P) {
    const plate = (x) => { x.moveTo(12.4, 5.6); x.quadraticCurveTo(20, 3.2, 28.2, 6.2); x.quadraticCurveTo(33, 19, 27.8, 31.6); x.lineTo(14.2, 31.6); x.quadraticCurveTo(11.4, 18, 12.4, 5.6); x.closePath(); };
    for (const y of [11.6, 21.4]) { rr(c, M.leather, 6.6, y, 8, 3.8, 1.2); ci(c, GOLD, 8.8, y + 1.9, 1.3); }
    f(c, P.d, (x) => { x.moveTo(13, 31); x.lineTo(28, 31); x.quadraticCurveTo(40.4, 32.4, 42.4, 38.4); x.lineTo(42.4, 40); x.lineTo(13, 40); x.closePath(); });
    f(c, P.a, pts([[30.6, 33.4], [38, 35.4], [39.6, 37.6], [30.6, 37.6]]));
    rr(c, mix(P.d, "#000000", 0.35), 11.6, 39, 32, 4.8, 2.2);
    body(c, P.a, plate, 26);
    f(c, P.l, (x) => { x.moveTo(19.4, 5.4); x.lineTo(22.4, 5.6); x.quadraticCurveTo(24.8, 19, 22.4, 31); x.lineTo(20, 31); x.quadraticCurveTo(21.6, 19, 19.4, 5.4); x.closePath(); });
    clip(c, plate, () => { f(c, P.l, () => c.rect(0, 0, 48, 8)); f(c, P.d, () => c.rect(0, 28.4, 48, 4)); f(c, HI2, () => c.rect(13.6, 10, 1.6, 16)); });
  }
  /** 護膝脛甲：同一片脛甲縮短，前緣膝蓋位置貼一片盾形小護膝（見下面第 2 版的註解）。第 1 版是頂上一顆亮白的大圓護膝加側翼，像廚師帽。第一稿護膝前面有一片尖翼加一顆鉚釘，像鳥頭，改掉了。 */
  function kneeGreaveArt(c, o, P) {
    c.save(); c.translate(0, 43.8); c.scale(1, 0.85); c.translate(0, -43.8); greaveArt(c, o, P); c.restore();
    /* 第 2 版：護膝改成貼在脛甲前緣（右邊）膝蓋位置的一片菱形小甲片——上短下長、正中一道亮稜線、右半暗一階、左上一條亮邊；和脛甲同一階亮度，自己包一圈外框才和脛甲分得開。側翼拿掉 */
    const cop = (x) => { x.moveTo(20.6, 12.6); x.quadraticCurveTo(21.6, 7.6, 28.2, 6.6); x.quadraticCurveTo(34.8, 7.6, 35.8, 12.6); x.quadraticCurveTo(35.6, 21, 28.4, 26); x.quadraticCurveTo(21, 21, 20.6, 12.6); x.closePath(); };
    c.save(); c.translate(28.6, 17.4); c.scale(0.86, 0.86); c.translate(-28.2, -16.4);
    halo(c, o, (x) => { f(x, P.a, cop); clip(x, cop, () => { f(x, SH, () => x.rect(28.3, 0, 12, 48)); st(x, HI2, 1.6, (k) => { k.moveTo(21.4, 13.4); k.quadraticCurveTo(22.4, 8.6, 28, 7.6); }, "butt"); });
      st(x, P.l, 1.9, (k) => { k.moveTo(28.2, 7); k.lineTo(28.4, 25.4); }, "butt"); });
    c.restore();
  }

  // =====================================================================
  // 飾品（人物身上不畫；照現行裝備圖示的題材：戒指、項鍊墜、吊牌、符牌、骨符）
  // =====================================================================
  /** 素戒：一個斜立著的寬戒圈（看得到戒圈的外壁、朝前的亮戒緣、戒圈內側的暗壁、穿過去的洞），外壁一條白亮線，右上一顆閃光。沒有寶石、沒有戒台。 */
  function ringPlainArt(c, o, P) {
    const E = (x, cx, rx, ry) => x.ellipse(cx, 24, rx, ry, 0, 0, TAU), hull = (x) => { E(x, 20.4, 12.6, 18.6); x.rect(20.4, 5.4, 7.4, 37.2); E(x, 27.8, 12.6, 18.6); };
    f(c, P.a, hull);
    clip(c, hull, () => { f(c, SH, () => c.rect(0, 33, 48, 12)); st(c, HI2, 1.6, (x) => x.ellipse(20.4, 24, 10.4, 16.4, 0, Math.PI * 0.75, Math.PI * 1.3), "butt"); });
    f(c, P.l, (x) => E(x, 27.8, 12.6, 18.6)); f(c, "rgba(0,0,0,0.14)", (x) => { x.ellipse(27.8, 24, 12.6, 18.6, 0, 0.3, Math.PI * 0.9); x.closePath(); });
    f(c, P.d, (x) => E(x, 27.8, 8, 13.8));
    c.save(); c.beginPath(); E(c, 27.8, 8, 13.8); c.clip(); c.globalCompositeOperation = "destination-out"; f(c, "#000", (x) => E(x, 22.6, 8, 13.8)); c.restore();
  }
  /** 寶石戒：金戒圈（中空）＋頂上一顆菱形寶石、深一階的戒台；戒圈左上一道亮線、右下一道暗面。和風格樣張對照 9 的寶石戒同一款（往下移一點，寶石尖不貼格邊）。 */
  function ringGemArt(c, o, P) {
    c.beginPath(); c.ellipse(24, 30.4, 15.5, 13.4, 0, 0, TAU); c.moveTo(33.6, 30.4); c.ellipse(24, 30.4, 9.6, 8, 0, 0, TAU, true); c.fillStyle = P.a; c.fill("evenodd");
    st(c, mix(P.a, "#ffffff", 0.6), 1.5, (x) => x.ellipse(24, 30.4, 13.6, 11.6, 0, Math.PI * 0.9, Math.PI * 1.45), "butt");
    st(c, "rgba(0,0,0,0.22)", 5.4, (x) => x.ellipse(24, 30.4, 12.6, 10.6, 0, 0.15, Math.PI * 0.6), "butt");
    rr(c, mix(P.a, P.d, 0.45), 17.5, 14.4, 13, 5.4, 1.6);
    poly(c, P.accent, [[24, 4.6], [32.5, 10.6], [24, 18.4], [15.5, 10.6]], 0.9); poly(c, "rgba(255,255,255,0.6)", [[24, 5.6], [24, 10.6], [17, 10.6]]); if (!o.small) poly(c, "rgba(0,0,0,0.28)", [[24, 10.6], [31.5, 10.6], [24, 17.4]]);
  }
  /** 印戒：細戒圈（和寶石戒同一個）頂上一塊橫的圓角長方戒面（戒圈直徑的六成）、嵌一塊深色的印面、印面上一顆亮色的四芒星徽記；戒面兩側露出戒圈的肩。現行圖示是方戒面加一個 ^ 形刻痕。 */
  function ringSignetArt(c, o, P) {
    /* 第 2 版：第 1 版戒面和戒圈一樣寬、洞很小，像數字 8（骨白的像雪人）。戒圈改用寶石戒那一個（細帶、大洞），戒面縮到戒圈直徑的六成、壓扁成橫的圓角長方，兩側露出戒圈的肩 */
    c.beginPath(); c.ellipse(24, 29.8, 16.4, 14, 0, 0, TAU); c.moveTo(34.6, 29.8); c.ellipse(24, 29.8, 10.6, 8.6, 0, 0, TAU, true); c.fillStyle = P.a; c.fill("evenodd");
    st(c, mix(P.a, "#ffffff", 0.6), 1.5, (x) => x.ellipse(24, 29.8, 14.6, 12.2, 0, Math.PI * 0.9, Math.PI * 1.3), "butt");
    st(c, "rgba(0,0,0,0.22)", 5.4, (x) => x.ellipse(24, 29.8, 13.5, 11.3, 0, 0.15, Math.PI * 0.6), "butt");
    rr(c, mix(P.a, P.d, 0.45), 15.6, 16.2, 16.8, 3, 1);
    rr(c, P.a, 14, 5.6, 20, 11.6, 3.4); f(c, SH, (x) => x.roundRect(30.4, 5.6, 3.6, 11.6, [0, 3.4, 3.4, 0])); f(c, HI2, () => c.rect(15.4, 8.2, 1.4, 6));
    rr(c, P.d, 17, 7.6, 14, 7.6, 1.8);
    poly(c, P.l, starPts(24, 11.4, 3.5, 1.3, 4), 0.2);
  }
  /** V 形的鍊子：兩邊各一串圓鍊珠，從上面兩角垂到 (24, y1)。 */
  const chain = (c, P, y1, n = 5) => { for (const s of [-1, 1]) for (let i = 0; i < n; i++) { const t = i / n; ci(c, i % 2 ? P.d : P.a, 24 + s * (18.6 - t * 17), 5.6 + t * (y1 - 5.6), 2.1); } };
  /** 項鍊墜：V 形的鍊子吊著一顆圓墜——墜子一圈深一階的內框、正中一顆菱形寶石、左上一道亮弧，墜頂一個小吊環。現行圖示是虛線鍊加圓墜與寶石。 */
  function pendantArt(c, o, P) {
    chain(c, P, 21.4);
    ci(c, P.a, 24, 21.6, 3.2); ci(c, P.dd, 24, 21.6, 1.2);
    ci(c, P.a, 24, 33.4, 10.8); f(c, SH, (x) => { x.arc(24, 33.4, 10.8, -0.3, Math.PI * 0.75); x.closePath(); });
    ci(c, P.d, 24, 33.4, 7.8); st(c, HI2, 1.5, (x) => x.arc(24, 33.4, 9.4, Math.PI * 0.95, Math.PI * 1.45), "butt");
    gem(c, P.accent, 24, 33.4, 5.6, o);
  }
  /** 吊牌：V 形的鍊子吊著兩片疊在一起的長方牌子（軍牌）：後面那片暗一階、往左歪；前面那片往右歪，頂上一個穿孔、牌面兩道刻線、左邊一條亮面。 */
  function tagArt(c, o, P) {
    chain(c, P, 17.6, 4);
    const tag = (k, col, rot, front) => { k.save(); k.translate(24, 18.4); k.rotate(rot); rr(k, col, -8.2, -2.6, 16.4, 26.4, 3.4);
      if (front) { f(k, SH, (x) => x.roundRect(4, -2.6, 4.2, 26.4, [0, 3.4, 3.4, 0])); f(k, HI2, () => k.rect(-6.4, 4.4, 2.4, 16)); ci(k, P.l, 0, 1.6, 3); ci(k, P.dd, 0, 1.6, 1.6); rr(k, P.d, -4, 9.4, 8.6, 1.9, 0.8); rr(k, P.d, -4, 14, 6.2, 1.9, 0.8); }
      k.restore(); };
    tag(c, mix(P.a, P.d, 0.75), 0.36, false);
    halo(c, o, (x) => tag(x, P.a, -0.2, true));
  }
  /** 符牌：一塊直立的長牌——頂上一個紅繩圈與繩結、牌面一圈亮邊、中間三道深色的符文刻痕（一直兩橫，現行圖示也是）、底下垂一撮紅流蘇（現行圖示是兩條紅線）。 */
  function tabletArt(c, o, P) {
    st(c, CORD, 2, (x) => x.arc(24, 6.4, 2.5, 0, TAU), "butt");
    poly(c, CORD, [[21.2, 36.4], [26.8, 36.4], [28.6, 44.4], [19.4, 44.4]], 0.4); if (!o.small) for (const x of [22.2, 25]) f(c, "rgba(0,0,0,0.25)", () => c.rect(x, 39, 0.9, 5.4));
    rr(c, P.a, 12.4, 9.6, 23.2, 26.4, 3.6); f(c, SH, (x) => x.roundRect(30.4, 9.6, 5.2, 26.4, [0, 3.6, 3.6, 0]));
    st(c, P.l, 1.4, (x) => x.roundRect(14.6, 11.8, 18.8, 22, 2), "butt");
    rr(c, P.d, 22.8, 14.4, 2.6, 17, 1); rr(c, P.d, 18, 17.6, 12, 2.4, 1); st(c, P.d, 2.4, (x) => { x.moveTo(19, 24.4); x.lineTo(29.4, 28.4); }, "butt");
    ci(c, CORD, 24, 9.6, 2.5); ci(c, CORD, 24, 36.2, 2.3);
  }
  /** 骨符：一顆往右彎的獸牙（骨白、右側暗一階、兩道刻痕），牙根套一個材質色的箍、箍頂一個吊環；左邊掛一根米白羽毛（羽尖紅）。現行圖示是一片骨白的尖葉加橫紋，底下一條材質色的橫槓。 */
  function boneCharmArt(c, o, P) {
    const fang = (x) => { x.moveTo(15.4, 13.6); x.bezierCurveTo(13.4, 26, 20, 38.6, 33.6, 44.2); x.bezierCurveTo(36.4, 34, 36.4, 23.6, 33, 13.6); x.closePath(); };
    f(c, CREAM, (x) => { x.moveTo(14.4, 14); x.quadraticCurveTo(3.6, 20, 5.6, 34.6); x.quadraticCurveTo(12.4, 28, 16, 16.4); x.closePath(); });
    f(c, CORD, (x) => { x.moveTo(5.2, 29.6); x.lineTo(5.6, 34.6); x.lineTo(8.8, 30.6); x.closePath(); });
    body(c, BONE, fang, null);
    clip(c, fang, () => { f(c, BONED, (x) => { x.moveTo(33, 13.6); x.bezierCurveTo(36.4, 23.6, 36.4, 34, 33.6, 44.2); x.bezierCurveTo(31, 36, 30, 24, 27.4, 13.6); x.closePath(); }); f(c, "#ffffff", () => c.rect(17.4, 16, 1.8, 10));
      if (!o.small) for (const y of [20.4, 25.6]) st(c, BONED, 1.5, (x) => { x.moveTo(16, y); x.lineTo(30, y + 2); }, "butt"); });
    rr(c, P.a, 13.4, 9.4, 21.6, 6.6, 2.4); f(c, P.d, () => c.rect(14.4, 14, 19.6, 1.4)); f(c, HI2, () => c.rect(15.6, 10.6, 5, 1.3));
    c.beginPath(); c.arc(24.2, 6.6, 3.3, 0, TAU); c.moveTo(25.5, 6.6); c.arc(24.2, 6.6, 1.3, 0, TAU, true); c.fillStyle = P.a; c.fill("evenodd");
  }

  const ART = {
    hood: { cloth: hoodArt, cowl: cowlArt }, hat: { wizard: wizardArt, wide: wideHatArt }, circlet: { bandana: bandanaArt, crown: crownArt }, cap: { leather: capArt, fur: furCapArt }, helmet: { iron: helmetArt, horned: hornedArt, greathelm: greathelmArt },
    robe: { long: robeLongArt, short: robeShortArt }, leather: { vest: vestArt, hunter: hunterArt }, mail: { chain: chainArt, scale: scaleArt }, plate: { half: plateArt, full: plateFullArt }, coat: { travel: coatArt, cape: capeCoatArt },
    cloth_gloves: { plain: clothGloveArt, fingerless: fingerlessArt }, leather_gloves: { short: leatherGloveArt, long: longGloveArt }, gauntlets: { plate: gauntletArt, mail: mailMittArt }, bracers: { leather: bracerArt, ring: armRingArt },
    shoes: { slipper: slipperArt, wrapped: wrappedArt }, boots: { short: bootShortArt, tall: bootTallArt }, iron_boots: { plain: ironBootArt, sabaton: sabatonArt }, greaves: { plain: greaveArt, knee: kneeGreaveArt },
    ring: { plain: ringPlainArt, gem: ringGemArt, signet: ringSignetArt }, pendant: { pendant: pendantArt, tag: tagArt }, charm: { tablet: tabletArt, bone: boneCharmArt },
  };
  /** 現行「關鍵字小圖樣」畫在器物上的兩個位置：client/src/render/gearIcon.ts 各造型回傳的 spots（64 格座標），換算到 48 格（圖樣佔裝備格的 6%～94%）。小圖樣本身不在這一批，照現行原樣疊。 */
  const SPOTS64 = { robe: [[25, 42], [39, 24]], leather: [[24, 30], [40, 30]], mail: [[25, 30], [39, 44]], plate: [[26, 32], [38, 22]], coat: [[25, 34], [40, 46]], ring: [[46, 44], [18, 46]], pendant: [[46, 44], [18, 44]], charm: [[46, 30], [18, 40]],
    hood: [[46, 22], [18, 26]], hat: [[48, 22], [16, 30]], circlet: [[48, 18], [16, 18]], cap: [[46, 24], [18, 24]], helmet: [[46, 22], [18, 28]], cloth_gloves: [[40, 30], [26, 38]], leather_gloves: [[40, 22], [26, 38]], gauntlets: [[42, 18], [24, 50]], bracers: [[48, 30], [16, 30]],
    shoes: [[46, 30], [28, 46]], boots: [[46, 30], [28, 46]], iron_boots: [[48, 30], [28, 46]], greaves: [[48, 28], [28, 46]] };
  const GEAR_PAD = Q.GEAR_PAD, to48 = (v) => Math.round(((v / 64 - GEAR_PAD) / (1 - GEAR_PAD * 2)) * 480) / 10;

  const cache = new Map();
  /** look → 圖樣定義（給 QIcons.render 用）：{ zh, d, meta: { spots, r, lifted } }。slot＝物品所在欄位（kind 缺漏時選預設造型）。 */
  function def(look, slot) {
    const r = resolve(look, slot), key = [r.kind, r.form, r.material, r.dye ?? "", r.keywords.join("+"), r.rarity, r.color ?? ""].join("|");
    let hit = cache.get(key);
    if (!hit) { const P = palette(r), art = ART[r.kind][r.form]; hit = { zh: KINDS[r.kind].forms[r.form], d: (c, o) => { art(c, o, P); if (P.rim) rimLight(c, o, P.rim); }, meta: { spots: SPOTS64[r.kind].map(([x, y]) => [to48(x), to48(y)]), r, lifted: P.lifted } }; cache.set(key, hit); }
    return hit;
  }
  /** 現行元素關鍵字的小圖樣（gearIcon.ts 的 motif() 原樣，64 單位；和 qIconsWeapons.js 裡那一份相同）：只有樣張頁示意「>36px 時照現行疊在 Q 版圖上」用，不是這一批重畫的東西。 */
  function motif(ctx, kw, x, y) {
    const col = KW[kw]; if (!col) return; ctx.save(); ctx.fillStyle = col; ctx.strokeStyle = col; ctx.lineWidth = 1.6; ctx.lineCap = "round";
    if (kw === "ignite") { ctx.beginPath(); ctx.moveTo(x, y - 6); ctx.quadraticCurveTo(x + 4.5, y, x, y + 3); ctx.quadraticCurveTo(x - 4.5, y, x, y - 6); ctx.fill(); }
    else if (kw === "wet") { ctx.beginPath(); ctx.moveTo(x, y - 5); ctx.quadraticCurveTo(x + 4, y + 1, x, y + 3); ctx.quadraticCurveTo(x - 4, y + 1, x, y - 5); ctx.fill(); }
    else if (kw === "charged") { ctx.beginPath(); ctx.moveTo(x - 3, y - 5); ctx.lineTo(x + 1, y - 1); ctx.lineTo(x - 1, y + 1); ctx.lineTo(x + 3, y + 5); ctx.stroke(); }
    else { ctx.beginPath(); for (let i = 0; i < 3; i++) { const a = (i * Math.PI) / 3; ctx.moveTo(x - Math.cos(a) * 4.5, y - Math.sin(a) * 4.5); ctx.lineTo(x + Math.cos(a) * 4.5, y + Math.sin(a) * 4.5); } ctx.stroke(); }
    ctx.restore();
  }
  /** 畫一個含框的圖示在 (0,0)～(size,size)。opt.frame：gear（裝備格，框色＝稀有度，預設）｜none；opt.motif＝true 時 >36px 照現行疊元素小圖樣；opt.slot＝欄位。 */
  function paint(ctx, look, size, res, opt = {}) {
    const d = def(look, opt.slot), fr = opt.frame ?? "gear", put = (x, y, a) => ctx.drawImage(Q.render(d, a, res, {}), x, y, a, a);
    ctx.save();
    if (fr === "gear") { ctx.save(); ctx.scale(size / 64, size / 64); QW.gearFrame(ctx, d.meta.r.rarity); ctx.restore(); const p = size * GEAR_PAD; put(p, p, size - p * 2);
      if (opt.motif && size > 36 && d.meta.r.tintKw) { ctx.save(); ctx.translate(p, p); ctx.scale((size - p * 2) / 48, (size - p * 2) / 48); for (const [x, y] of d.meta.spots) { ctx.save(); ctx.translate(x, y); ctx.scale(0.75, 0.75); motif(ctx, d.meta.r.tintKw, 0, 0); ctx.restore(); } ctx.restore(); } }
    else put(0, 0, size);
    ctx.restore();
  }
  /** 含框的圖示 canvas：顯示邊長 px×zoom；zoom 1 時內部解析度 ×2（和遊戲一樣），放大時直接用向量畫到該倍率（圖樣的簡化程度仍照 px）。 */
  function canvas(look, px, zoom = 1, opt = {}) {
    const res = zoom === 1 ? 2 : zoom, cv = document.createElement("canvas"); cv.width = cv.height = Math.round(px * res); cv.style.width = cv.style.height = px * zoom + "px";
    const x = cv.getContext("2d"); x.scale(res, res); paint(x, look, px, res, opt); return cv;
  }
  /** 全部款式（kind × form）：[{ kind, form, zh, kindZh, slot, mats, def }]。 */
  const list = () => Object.entries(KINDS).flatMap(([kind, K]) => Object.entries(K.forms).map(([form, zh]) => ({ kind, form, zh, kindZh: K.zh, slot: K.slot, mats: matsOf(kind, form), def: defOf(kind, form) })));
  return { KINDS, MAT, MAT_ZH, DYE, DYE_ZH, KW, RARITY, GEAR_PAD, SLOT_DEFAULT_KIND, resolve, palette, def, paint, canvas, list };
})();
