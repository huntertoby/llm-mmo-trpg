// 組裝式裝備圖示（美術樣張，08-裝備.md 8.18）：外觀只看資料欄位。
// 外觀 ＝ 造型 kind × 形制 form × 外觀材質 material（＋選填染色 dye）× 風格 style ＋ 關鍵字 keywords ＋ 稀有度 rarity。
// 不認得的值一律退回預設，不會出錯；材質不合造型時退回該造型的預設材質。
// 座標：64 × 64 的虛擬格。
window.GearArt = (() => {
  const TAU = Math.PI * 2;
  const INK = "#16181d";

  // ---- 色票 ----
  const MATERIAL = {
    iron: { zh: "鐵", c: ["#6e757d", "#474c52"] },
    steel: { zh: "鋼", c: ["#a9b6c6", "#6d7a8a"] },
    copper: { zh: "銅", c: ["#c27a48", "#7e4a28"] },
    silver: { zh: "銀", c: ["#e8edf2", "#a8b0ba"], shine: true },
    gold: { zh: "金", c: ["#e8bb48", "#9c7420"] },
    wood: { zh: "木", c: ["#a06a36", "#6a4420"] },
    leather: { zh: "皮", c: ["#8a5a32", "#5e3b1f"] },
    cloth: { zh: "布", c: ["#8a8f99", "#5d6168"] },
    bone: { zh: "骨", c: ["#e9e3cf", "#a8a08a"] },
    crystal: { zh: "晶石", c: ["#b8a8ff", "#7a68c8"] },
  };
  const DYE = { red: "#b83a3a", blue: "#3a5fb8", green: "#3f8a4a", purple: "#7a4ab0", black: "#33363d", white: "#e6e6e0", brown: "#7a5232", gold: "#d9a83a" };
  const DYE_ZH = { red: "紅", blue: "藍", green: "綠", purple: "紫", black: "黑", white: "白", brown: "褐", gold: "金" };
  // 關鍵字（06 6.27）：元素類混色＋小圖樣；其他只加小圖樣
  const KEYWORD = {
    ignite: { zh: "點燃", c: "#ff6a1a", tint: true },
    wet: { zh: "潮濕", c: "#4aa8ff", tint: true },
    shock: { zh: "帶電", c: "#fff36b", tint: true },
    freeze: { zh: "冰凍", c: "#8fe3ff", tint: true },
    prone: { zh: "倒地", c: "#e0b080" },
    impact: { zh: "撞擊", c: "#ff9a4a" },
    mark: { zh: "標記", c: "#d06aff" },
    high: { zh: "高處", c: "#ffe9a8" },
    hidden: { zh: "隱蔽", c: "#a0a0c8" },
    summon: { zh: "召喚物", c: "#7dffb0" },
  };
  // 第一季到史詩；傳說留到正式季（樣張一併示意）
  const RARITY = { common: ["#8a8f99", "普通"], uncommon: ["#5fd05f", "優良"], rare: ["#4f9dff", "稀有"], epic: ["#b06cff", "史詩"], legendary: ["#ffbf3a", "傳說"] };

  // ---- 造型 → 部位、形制、可用材質、預設材質 ----
  const METAL = ["iron", "steel", "copper", "silver", "gold"];
  const KINDS = {
    sword: { slot: "main", zh: "劍", forms: { straight: "直劍", curved: "彎刀", broad: "闊劍" }, mats: [...METAL], def: "iron" },
    greatsword: { slot: "main", zh: "巨劍", forms: { twohand: "雙手劍", zhanma: "斬馬刀", serrated: "鋸齒巨劍" }, mats: [...METAL], def: "iron" },
    dagger: { slot: "main", zh: "匕首", forms: { short: "短刀", stiletto: "三稜刺", kris: "彎匕" }, mats: [...METAL, "bone", "crystal"], def: "iron" },
    axe: { slot: "main", zh: "斧", forms: { hand: "手斧", battle: "戰斧", double: "雙刃斧" }, mats: [...METAL], def: "iron" },
    hammer: { slot: "main", zh: "錘", forms: { mace: "釘頭錘", warhammer: "戰錘", flail: "連枷" }, mats: [...METAL], def: "iron" },
    spear: { slot: "main", zh: "矛", forms: { spear: "長矛", halberd: "戟", trident: "三叉戟" }, mats: [...METAL, "wood"], def: "iron" },
    bow: { slot: "main", zh: "弓", forms: { short: "短弓", long: "長弓", recurve: "反曲弓" }, mats: ["wood", ...METAL], def: "wood" },
    crossbow: { slot: "main", zh: "弩", forms: { light: "輕弩", heavy: "重弩", repeater: "連弩" }, mats: ["wood", ...METAL], def: "wood" },
    longgun: { slot: "main", zh: "長槍", forms: { flintlock: "燧發長槍", hunting: "獵槍", sniper: "狙擊長槍" }, mats: [...METAL], def: "steel" },
    shotgun: { slot: "main", zh: "霰彈槍", forms: { blunderbuss: "喇叭槍", double: "雙管", pump: "泵動" }, mats: [...METAL], def: "iron" },
    pistol: { slot: "main", zh: "手槍", forms: { flintlock: "燧發手槍", revolver: "左輪", derringer: "短銃" }, mats: [...METAL], def: "steel" },
    dual_pistol: { slot: "main", zh: "雙手槍", forms: { flintlock: "燧發手槍", revolver: "左輪", derringer: "短銃" }, mats: [...METAL], def: "steel", pair: true },
    fist: { slot: "main", zh: "拳套", forms: { katar: "拳刃", knuckle: "鐵拳", claw: "爪" }, mats: [...METAL, "bone", "leather"], def: "iron" },
    scythe: { slot: "main", zh: "鐮刀", forms: { long: "長柄鐮", crescent: "彎月鐮", hook: "鉤鐮" }, mats: [...METAL, "bone"], def: "iron" },
    whip: { slot: "main", zh: "鞭", forms: { leather: "皮鞭", chain: "鏈鞭", bladed: "蛇骨鞭" }, mats: ["leather", ...METAL, "bone"], def: "leather" },
    dual_dagger: { slot: "main", zh: "雙匕首", forms: { short: "短刀", stiletto: "三稜刺", kris: "彎匕" }, mats: [...METAL, "bone", "crystal"], def: "iron", pair: true },
    // 舊樣張（gear3.html）用的合併造型；正式清單改用 longgun／shotgun／pistol
    gun: { legacy: true, slot: "main", zh: "槍", forms: { pistol: "手槍", rifle: "步槍", shotgun: "霰彈槍", energy: "能量槍" }, mats: [...METAL, "wood"], def: "steel" },
    staff: { slot: "main", zh: "杖", forms: { long: "長杖", scepter: "權杖", wand: "短杖", totem: "圖騰杖" }, mats: ["wood", ...METAL, "bone", "crystal"], def: "wood" },
    round_shield: { slot: "off", zh: "圓盾", forms: { wood: "木圓盾", banded: "包鐵圓盾" }, mats: ["wood", ...METAL], def: "wood" },
    kite_shield: { slot: "off", zh: "鳶盾", forms: { kite: "鳶盾", tower: "塔盾" }, mats: [...METAL], def: "iron" },
    tome: { slot: "off", zh: "法書", forms: { book: "典籍", scroll: "卷軸匣" }, mats: ["leather", "cloth"], def: "leather" },
    orb: { slot: "off", zh: "法器珠", forms: { ball: "水晶球", floating: "浮空寶珠" }, mats: ["crystal", "bone"], def: "crystal" },
    robe: { slot: "body", zh: "布袍", forms: { long: "長袍", short: "短袍" }, mats: ["cloth"], def: "cloth" },
    leather: { slot: "body", zh: "皮甲", forms: { vest: "皮背心", hunter: "獵裝" }, mats: ["leather"], def: "leather" },
    mail: { slot: "body", zh: "鎖甲", forms: { chain: "鎖子甲", scale: "鱗甲" }, mats: [...METAL], def: "iron" },
    plate: { slot: "body", zh: "板甲", forms: { half: "半身板甲", full: "全身板甲" }, mats: [...METAL], def: "steel" },
    coat: { slot: "body", zh: "外套", forms: { travel: "旅行外套", cape: "披風外套" }, mats: ["cloth", "leather"], def: "cloth" },
    // ---- 9 格：頭、手、腳（#37）----
    hood: { slot: "head", zh: "兜帽", forms: { cloth: "布兜帽", cowl: "斗篷帽" }, mats: ["cloth", "leather"], def: "cloth" },
    hat: { slot: "head", zh: "帽子", forms: { wizard: "法師帽", wide: "寬簷帽" }, mats: ["cloth", "leather"], def: "cloth" },
    circlet: { slot: "head", zh: "頭巾／頭冠", forms: { bandana: "頭巾", crown: "頭冠" }, mats: ["cloth", "leather", ...METAL, "bone", "crystal"], def: "cloth", formDef: { crown: "gold" }, formMats: { bandana: ["cloth", "leather"], crown: [...METAL, "bone", "crystal"] } },
    cap: { slot: "head", zh: "皮帽", forms: { leather: "皮帽", fur: "毛帽" }, mats: ["leather", "cloth"], def: "leather" },
    helmet: { slot: "head", zh: "頭盔", forms: { iron: "鐵盔", horned: "角盔", greathelm: "全罩盔" }, mats: [...METAL], def: "iron" },
    cloth_gloves: { slot: "hands", zh: "布手套", forms: { plain: "素手套", fingerless: "露指手套" }, mats: ["cloth"], def: "cloth" },
    leather_gloves: { slot: "hands", zh: "皮手套", forms: { short: "短皮手套", long: "長皮手套" }, mats: ["leather"], def: "leather" },
    gauntlets: { slot: "hands", zh: "護手", forms: { plate: "板金護手", mail: "鎖鏈護手" }, mats: [...METAL], def: "steel" },
    bracers: { slot: "hands", zh: "臂甲", forms: { leather: "皮臂甲", ring: "臂環" }, mats: ["leather", ...METAL], def: "leather", formDef: { ring: "copper" }, formMats: { leather: ["leather"], ring: [...METAL] } },
    shoes: { slot: "feet", zh: "布鞋", forms: { slipper: "布鞋", wrapped: "綁腿鞋" }, mats: ["cloth"], def: "cloth" },
    boots: { slot: "feet", zh: "皮靴", forms: { short: "短靴", tall: "長靴" }, mats: ["leather"], def: "leather" },
    iron_boots: { slot: "feet", zh: "鐵靴", forms: { plain: "鐵靴", sabaton: "尖頭鐵靴" }, mats: [...METAL], def: "iron" },
    greaves: { slot: "feet", zh: "脛甲", forms: { plain: "脛甲", knee: "護膝脛甲" }, mats: [...METAL], def: "steel" },
    // 舊樣張（gear5.html）用的皮手套；正式清單改用 leather_gloves
    gloves: { legacy: true, slot: "hands", zh: "手套", forms: { leather: "皮手套" }, mats: ["leather", "cloth"], def: "leather" },
    ring: { slot: "ring", zh: "戒指", forms: { plain: "素戒", gem: "寶石戒", signet: "印戒" }, mats: [...METAL, "bone", "crystal"], def: "gold" },
    pendant: { slot: "neck", zh: "墜飾", forms: { pendant: "項鍊墜", tag: "吊牌" }, mats: [...METAL, "bone", "crystal"], def: "gold" },
    charm: { slot: "neck", zh: "護符", forms: { tablet: "符牌", bone: "骨符" }, mats: [...METAL, "bone", "crystal", "leather", "cloth"], def: "gold" },
    bracelet: { legacy: true, slot: "acc", zh: "手環", forms: { metal: "金屬環", woven: "編織環" }, mats: [...METAL, "bone", "crystal", "leather", "cloth"], def: "gold" },
  };

  /** 驗證＋補預設：任何輸入都回傳畫得出來的外觀。 */
  function resolve(it) {
    const kind = KINDS[it.kind] ? it.kind : "sword";
    const K = KINDS[kind];
    const form = it.form in K.forms ? it.form : Object.keys(K.forms)[0];
    const mats = K.formMats?.[form] ?? K.mats;
    const material = mats.includes(it.material) ? it.material : K.formDef?.[form] ?? K.def;
    const dye = (material === "cloth" || material === "leather") && DYE[it.dye] ? it.dye : null;
    const keywords = (it.keywords ?? []).filter((k) => KEYWORD[k]).slice(0, 2);
    const rarity = RARITY[it.rarity] ? it.rarity : "common";
    return { kind, form, material, dye, keywords, rarity, style: STYLES[it.style] ? it.style : "common" };
  }

  function mix(a, b, t) {
    const pa = parseInt(a.slice(1), 16), pb = parseInt(b.slice(1), 16);
    const m = (s) => Math.round(((pa >> s) & 255) * (1 - t) + ((pb >> s) & 255) * t);
    return `#${((m(16) << 16) | (m(8) << 8) | m(0)).toString(16).padStart(6, "0")}`;
  }
  /** 主色、暗色、強調色（寶石、寶珠用）。 */
  function palette(r) {
    let [a, d] = MATERIAL[r.material].c;
    if (r.dye) { a = DYE[r.dye]; d = mix(DYE[r.dye], "#000000", 0.35); }
    const el = r.keywords.map((k) => KEYWORD[k]).find((k) => k.tint);
    if (el) {
      if (r.material === "crystal") { a = el.c; d = mix(el.c, "#000000", 0.4); }
      else { a = mix(a, el.c, 0.4); d = mix(d, el.c, 0.25); }
    }
    const accent = r.keywords.length ? KEYWORD[r.keywords[0]].c : r.material === "crystal" ? "#b8a8ff" : "#e04060";
    return { a, d, accent, shine: MATERIAL[r.material].shine === true, handle: "#5e3b1f", guard: r.rarity === "epic" || r.rarity === "legendary" ? "#e8bb48" : "#7a5a3a" };
  }

  // ---- 小工具 ----
  function shape(ctx, fillC, path, lw = 2) {
    ctx.beginPath(); path(); ctx.fillStyle = fillC; ctx.fill(); ctx.lineWidth = lw; ctx.strokeStyle = INK; ctx.stroke();
  }
  function line(ctx, c, w, pts) { ctx.beginPath(); ctx.moveTo(...pts[0]); for (const p of pts.slice(1)) ctx.lineTo(...p); ctx.strokeStyle = c; ctx.lineWidth = w; ctx.stroke(); }
  function diag(ctx, fn) { ctx.save(); ctx.translate(32, 33); ctx.rotate(Math.PI / 4); fn(); ctx.restore(); }
  function grip(ctx, P, y0, len) {
    shape(ctx, P.handle, () => ctx.roundRect(-2.5, y0, 5, len, 1.5), 1.5);
    ctx.strokeStyle = "rgba(0,0,0,0.35)"; ctx.lineWidth = 1;
    for (let y = y0 + 2.5; y < y0 + len - 1; y += 3) { ctx.beginPath(); ctx.moveTo(-2.5, y); ctx.lineTo(2.5, y + 1.2); ctx.stroke(); }
  }
  function guard(ctx, P, y, w) { shape(ctx, P.guard, () => ctx.roundRect(-w / 2, y, w, 4, 2), 1.5); }
  function shine(ctx, P, pts) { if (P.shine) line(ctx, "rgba(255,255,255,0.95)", 1.4, pts); }
  function gem(ctx, x, y, r, c) {
    shape(ctx, c, () => { ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r); ctx.lineTo(x - r, y); ctx.closePath(); }, 1.5);
    ctx.fillStyle = "rgba(255,255,255,0.55)"; ctx.beginPath(); ctx.moveTo(x, y - r); ctx.lineTo(x + r * 0.5, y - r * 0.2); ctx.lineTo(x, y); ctx.closePath(); ctx.fill();
  }

  // ---- 關鍵字小圖樣（畫在器物上，最多 2 個關鍵字、各 2 處）----
  function motif(ctx, kw, x, y) {
    const k = KEYWORD[kw]; ctx.save(); ctx.fillStyle = k.c; ctx.strokeStyle = k.c; ctx.lineWidth = 1.6; ctx.lineCap = "round";
    switch (kw) {
      case "ignite": ctx.beginPath(); ctx.moveTo(x, y - 6); ctx.quadraticCurveTo(x + 4.5, y, x, y + 3); ctx.quadraticCurveTo(x - 4.5, y, x, y - 6); ctx.fill(); break;
      case "wet": ctx.beginPath(); ctx.moveTo(x, y - 5); ctx.quadraticCurveTo(x + 4, y + 1, x, y + 3); ctx.quadraticCurveTo(x - 4, y + 1, x, y - 5); ctx.fill(); break;
      case "shock": ctx.beginPath(); ctx.moveTo(x - 3, y - 5); ctx.lineTo(x + 1, y - 1); ctx.lineTo(x - 1, y + 1); ctx.lineTo(x + 3, y + 5); ctx.stroke(); break;
      case "freeze": ctx.beginPath(); for (let i = 0; i < 3; i++) { const a = (i * Math.PI) / 3; ctx.moveTo(x - Math.cos(a) * 4.5, y - Math.sin(a) * 4.5); ctx.lineTo(x + Math.cos(a) * 4.5, y + Math.sin(a) * 4.5); } ctx.stroke(); break;
      case "prone": ctx.beginPath(); ctx.moveTo(x - 4, y - 2); ctx.lineTo(x, y + 2); ctx.lineTo(x + 4, y - 2); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x - 4, y + 2); ctx.lineTo(x + 4, y + 2); ctx.stroke(); break;
      case "impact": ctx.beginPath(); for (let i = 0; i < 8; i++) { const a = (i / 8) * TAU, r = i % 2 ? 2 : 5; ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); } ctx.closePath(); ctx.fill(); break;
      case "mark": ctx.beginPath(); ctx.arc(x, y, 3.5, 0, TAU); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x - 6, y); ctx.lineTo(x - 4, y); ctx.moveTo(x + 4, y); ctx.lineTo(x + 6, y); ctx.moveTo(x, y - 6); ctx.lineTo(x, y - 4); ctx.moveTo(x, y + 4); ctx.lineTo(x, y + 6); ctx.stroke(); break;
      case "high": ctx.beginPath(); ctx.moveTo(x - 4, y + 2); ctx.lineTo(x, y - 3); ctx.lineTo(x + 4, y + 2); ctx.stroke(); break;
      case "hidden": ctx.globalAlpha = 0.85; ctx.beginPath(); ctx.arc(x - 2, y, 2.6, 0, TAU); ctx.arc(x + 2, y - 1, 3, 0, TAU); ctx.arc(x + 1, y + 2, 2.2, 0, TAU); ctx.fill(); break;
      case "summon": ctx.beginPath(); ctx.arc(x, y - 1, 3.4, Math.PI, 0); ctx.lineTo(x + 3.4, y + 4); ctx.lineTo(x + 1.2, y + 2.5); ctx.lineTo(x, y + 4); ctx.lineTo(x - 1.2, y + 2.5); ctx.lineTo(x - 3.4, y + 4); ctx.closePath(); ctx.fill(); break;
    }
    ctx.restore();
  }

  // ---- 造型畫法：每個回傳「小圖樣位置」（在 64 格座標）----
  const D = {};
  D.sword = (ctx, r, P) => {
    diag(ctx, () => {
      const blade = {
        straight: () => { ctx.moveTo(-3.5, 8); ctx.lineTo(-3.5, -22); ctx.lineTo(0, -28); ctx.lineTo(3.5, -22); ctx.lineTo(3.5, 8); ctx.closePath(); },
        curved: () => { ctx.moveTo(-3, 8); ctx.quadraticCurveTo(-6, -12, 6, -28); ctx.quadraticCurveTo(4, -10, 4, 8); ctx.closePath(); },
        broad: () => { ctx.moveTo(-6, 8); ctx.lineTo(-6, -18); ctx.lineTo(0, -28); ctx.lineTo(6, -18); ctx.lineTo(6, 8); ctx.closePath(); },
      }[r.form];
      shape(ctx, P.a, blade); if (r.form !== "curved") line(ctx, P.d, 1.2, [[0, 6], [0, -20]]);
      shine(ctx, P, [[-1.5, 4], [-1.5, -18]]);
      guard(ctx, P, 8, r.form === "broad" ? 22 : 18); grip(ctx, P, 12, 10);
      shape(ctx, P.guard, () => ctx.arc(0, 24, 2.5, 0, TAU), 1.2);
    });
    return [[36, 26], [28, 36]];
  };
  D.greatsword = (ctx, r, P) => {
    diag(ctx, () => {
      if (r.form === "twohand") shape(ctx, P.a, () => { ctx.moveTo(-4.5, 5); ctx.lineTo(-4.5, -27); ctx.lineTo(0, -32); ctx.lineTo(4.5, -27); ctx.lineTo(4.5, 5); ctx.closePath(); });
      else if (r.form === "zhanma") shape(ctx, P.a, () => { ctx.moveTo(-4, 5); ctx.lineTo(-4, -26); ctx.quadraticCurveTo(-1, -33, 7, -31); ctx.lineTo(6, 5); ctx.closePath(); });
      else shape(ctx, P.a, () => { ctx.moveTo(-5, 5); ctx.lineTo(-5, -26); ctx.lineTo(0, -32); ctx.lineTo(5, -26); for (let y = -22; y < 5; y += 5) { ctx.lineTo(8, y); ctx.lineTo(5, y + 2.5); } ctx.lineTo(5, 5); ctx.closePath(); });
      line(ctx, P.d, 1.2, [[0, 3], [0, -25]]); shine(ctx, P, [[-2, 2], [-2, -24]]);
      guard(ctx, P, 5, 20); grip(ctx, P, 9, 16);
    });
    return [[38, 22], [30, 32]];
  };
  D.dagger = (ctx, r, P) => {
    diag(ctx, () => {
      if (r.form === "short") shape(ctx, P.a, () => { ctx.moveTo(-3.5, 6); ctx.lineTo(-3.5, -10); ctx.lineTo(0, -16); ctx.lineTo(3.5, -10); ctx.lineTo(3.5, 6); ctx.closePath(); });
      else if (r.form === "stiletto") shape(ctx, P.a, () => { ctx.moveTo(-2.5, 6); ctx.lineTo(0, -20); ctx.lineTo(2.5, 6); ctx.closePath(); });
      else shape(ctx, P.a, () => { ctx.moveTo(-3, 6); ctx.quadraticCurveTo(-5, -4, 0, -8); ctx.quadraticCurveTo(5, -12, 2, -18); ctx.quadraticCurveTo(9, -10, 3, -3); ctx.lineTo(3, 6); ctx.closePath(); });
      shine(ctx, P, [[-1, 4], [-1, -10]]);
      guard(ctx, P, 6, 14); grip(ctx, P, 10, 9);
    });
    return [[33, 30], [27, 34]];
  };
  D.axe = (ctx, r, P) => {
    diag(ctx, () => {
      shape(ctx, P.handle, () => ctx.roundRect(-2.5, -24, 5, 46, 2), 1.5);
      const head = (s) => () => { ctx.moveTo(2, -22); ctx.quadraticCurveTo(14 * s, -28, 16 * s, -14); ctx.quadraticCurveTo(12 * s, -12, 2, -10); ctx.closePath(); };
      if (r.form === "hand") { ctx.save(); ctx.scale(0.8, 0.8); shape(ctx, P.a, head(1)); ctx.restore(); }
      else if (r.form === "battle") shape(ctx, P.a, () => { ctx.moveTo(2, -26); ctx.quadraticCurveTo(20, -32, 20, -12); ctx.quadraticCurveTo(14, -6, 2, -8); ctx.closePath(); });
      else { shape(ctx, P.a, head(1)); ctx.save(); ctx.scale(-1, 1); shape(ctx, P.a, head(1)); ctx.restore(); }
      shine(ctx, P, [[8, -22], [13, -16]]);
    });
    return [[40, 20], [24, 40]];
  };
  D.hammer = (ctx, r, P) => {
    diag(ctx, () => {
      shape(ctx, P.handle, () => ctx.roundRect(-2.5, -14, 5, 36, 2), 1.5);
      if (r.form === "mace") {
        for (let i = 0; i < 8; i++) { const a = (i / 8) * TAU; shape(ctx, P.d, () => { ctx.moveTo(Math.cos(a) * 7, -20 + Math.sin(a) * 7); ctx.lineTo(Math.cos(a + 0.25) * 12, -20 + Math.sin(a + 0.25) * 12); ctx.lineTo(Math.cos(a + 0.5) * 7, -20 + Math.sin(a + 0.5) * 7); }, 1); }
        shape(ctx, P.a, () => ctx.arc(0, -20, 8, 0, TAU));
      } else if (r.form === "warhammer") { shape(ctx, P.a, () => ctx.roundRect(-11, -26, 22, 12, 2)); line(ctx, P.d, 1.5, [[-11, -20], [11, -20]]); }
      else {
        line(ctx, INK, 3.5, [[0, -14], [6, -20], [4, -26]]); line(ctx, P.d, 2, [[0, -14], [6, -20], [4, -26]]);
        for (let i = 0; i < 8; i++) { const a = (i / 8) * TAU; shape(ctx, P.d, () => { ctx.moveTo(4 + Math.cos(a) * 5, -31 + Math.sin(a) * 5); ctx.lineTo(4 + Math.cos(a + 0.3) * 9, -31 + Math.sin(a + 0.3) * 9); ctx.lineTo(4 + Math.cos(a + 0.6) * 5, -31 + Math.sin(a + 0.6) * 5); }, 1); }
        shape(ctx, P.a, () => ctx.arc(4, -31, 6, 0, TAU));
      }
      shine(ctx, P, [[-4, -24], [-1, -24]]);
    });
    return [[40, 18], [28, 38]];
  };
  D.spear = (ctx, r, P) => {
    diag(ctx, () => {
      shape(ctx, P.handle, () => ctx.roundRect(-2, -18, 4, 46, 2), 1.5);
      if (r.form === "spear") shape(ctx, P.a, () => { ctx.moveTo(0, -32); ctx.quadraticCurveTo(6, -22, 0, -16); ctx.quadraticCurveTo(-6, -22, 0, -32); });
      else if (r.form === "halberd") { shape(ctx, P.a, () => { ctx.moveTo(0, -33); ctx.lineTo(3, -18); ctx.lineTo(-3, -18); ctx.closePath(); }); shape(ctx, P.a, () => { ctx.moveTo(2, -26); ctx.quadraticCurveTo(14, -28, 13, -16); ctx.lineTo(2, -18); ctx.closePath(); }); }
      else { shape(ctx, P.a, () => ctx.roundRect(-8, -20, 16, 3, 1), 1.5); for (const x of [-7, 0, 7]) shape(ctx, P.a, () => { ctx.moveTo(x, -32); ctx.lineTo(x + 2, -20); ctx.lineTo(x - 2, -20); ctx.closePath(); }, 1.5); }
      shine(ctx, P, [[-1, -28], [-1, -20]]);
    });
    return [[42, 18], [26, 40]];
  };
  D.bow = (ctx, r, P) => {
    const L = r.form === "long" ? 26 : 20;
    ctx.save(); ctx.translate(30, 32);
    ctx.beginPath();
    if (r.form === "recurve") { ctx.moveTo(4, -L); ctx.quadraticCurveTo(-2, -L + 4, 8, -L / 2); ctx.quadraticCurveTo(16, 0, 8, L / 2); ctx.quadraticCurveTo(-2, L - 4, 4, L); }
    else { ctx.moveTo(0, -L); ctx.quadraticCurveTo(18, 0, 0, L); }
    ctx.lineWidth = 6; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = 3.5; ctx.strokeStyle = P.a; ctx.stroke();
    line(ctx, "#e6e0d0", 1, [[r.form === "recurve" ? 4 : 0, -L], [r.form === "recurve" ? 4 : 0, L]]);
    shape(ctx, P.handle, () => ctx.roundRect(r.form === "recurve" ? 9 : 6, -4, 5, 8, 1), 1.2);
    ctx.restore();
    return [[38, 20], [38, 44]];
  };
  D.staff = (ctx, r, P) => {
    const orb = r.keywords.length ? P.accent : r.material === "crystal" ? P.a : "#9ad0ff";
    diag(ctx, () => {
      const len = r.form === "wand" ? 26 : 40;
      shape(ctx, r.material === "wood" ? P.a : P.d, () => ctx.roundRect(-2.5, -14, 5, len, 2), 1.5);
      if (r.form === "scepter") { ctx.beginPath(); ctx.arc(0, -20, 8, 0, TAU); ctx.lineWidth = 5; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = 3; ctx.strokeStyle = r.material === "wood" ? "#e8bb48" : P.a; ctx.stroke(); gem(ctx, 0, -20, 4.5, orb); }
      else { shape(ctx, orb, () => ctx.arc(0, -20, r.form === "wand" ? 5 : 7, 0, TAU)); ctx.fillStyle = "rgba(255,255,255,0.6)"; ctx.beginPath(); ctx.arc(-2, -22, 2, 0, TAU); ctx.fill(); }
      if (r.form === "long") { line(ctx, INK, 3, [[-5, -14], [5, -14]]); line(ctx, r.material === "wood" ? "#6a4420" : P.d, 1.6, [[-5, -14], [5, -14]]); }
    });
    return [[40, 22], [28, 38]];
  };
  D.round_shield = (ctx, r, P) => {
    shape(ctx, P.a, () => ctx.arc(32, 33, 22, 0, TAU), 2.5);
    if (r.form === "wood") { for (const x of [-11, 0, 11]) line(ctx, P.d, 1.5, [[32 + x, 13 + Math.abs(x) / 3], [32 + x, 53 - Math.abs(x) / 3]]); }
    else { ctx.beginPath(); ctx.arc(32, 33, 19, 0, TAU); ctx.lineWidth = 4; ctx.strokeStyle = "#8d969f"; ctx.stroke(); for (let i = 0; i < 8; i++) { const a = (i / 8) * TAU; shape(ctx, "#c3ccd6", () => ctx.arc(32 + Math.cos(a) * 19, 33 + Math.sin(a) * 19, 1.6, 0, TAU), 0.8); } }
    shape(ctx, r.form === "wood" ? "#8d969f" : P.d, () => ctx.arc(32, 33, 6, 0, TAU), 1.5);
    shine(ctx, P, [[20, 22], [26, 16]]);
    return [[22, 26], [42, 42]];
  };
  D.kite_shield = (ctx, r, P) => {
    if (r.form === "kite") shape(ctx, P.a, () => { ctx.moveTo(14, 12); ctx.lineTo(50, 12); ctx.lineTo(50, 30); ctx.quadraticCurveTo(48, 48, 32, 57); ctx.quadraticCurveTo(16, 48, 14, 30); ctx.closePath(); }, 2.5);
    else shape(ctx, P.a, () => ctx.roundRect(15, 8, 34, 50, 4), 2.5);
    line(ctx, P.d, 3, [[32, 13], [32, r.form === "kite" ? 52 : 54]]); line(ctx, P.d, 3, [[19, 27], [45, 27]]);
    if (r.form === "tower") for (const y of [12, 54]) for (const x of [19, 45]) shape(ctx, P.d, () => ctx.arc(x, y, 1.6, 0, TAU), 0.8);
    shine(ctx, P, [[18, 16], [18, 26]]);
    return [[23, 20], [41, 40]];
  };
  D.tome = (ctx, r, P) => {
    if (r.form === "book") {
      shape(ctx, "#efe6cf", () => ctx.roundRect(17, 14, 32, 40, 3), 1.5);
      shape(ctx, P.a, () => ctx.roundRect(14, 12, 32, 40, 3), 2.5);
      line(ctx, P.d, 3, [[19, 12], [19, 52]]);
      gem(ctx, 32, 32, 6, P.accent);
      for (const y of [16, 48]) line(ctx, "#e8bb48", 2, [[38, y], [44, y]]);
    } else {
      shape(ctx, P.a, () => ctx.roundRect(22, 10, 20, 44, 6), 2.5);
      for (const y of [16, 48]) { shape(ctx, "#e8bb48", () => ctx.roundRect(20, y - 2, 24, 4, 1.5), 1.2); }
      shape(ctx, "#efe6cf", () => { ctx.moveTo(42, 26); ctx.lineTo(54, 30); ctx.lineTo(54, 40); ctx.lineTo(42, 36); ctx.closePath(); }, 1.5);
      gem(ctx, 32, 32, 4, P.accent);
    }
    return [[24, 22], [40, 44]];
  };
  D.orb = (ctx, r, P) => {
    const c = r.keywords.length && KEYWORD[r.keywords[0]].tint ? P.a : r.material === "crystal" ? P.a : P.a;
    if (r.form === "ball") {
      shape(ctx, "#7a5a3a", () => { ctx.moveTo(20, 54); ctx.lineTo(44, 54); ctx.lineTo(38, 44); ctx.lineTo(26, 44); ctx.closePath(); }, 2);
      shape(ctx, c, () => ctx.arc(32, 30, 15, 0, TAU), 2.5);
    } else {
      ctx.beginPath(); ctx.ellipse(32, 32, 24, 7, -0.3, 0, TAU); ctx.lineWidth = 4; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = 2; ctx.strokeStyle = "#e8bb48"; ctx.stroke();
      shape(ctx, c, () => ctx.arc(32, 31, 12, 0, TAU), 2.5);
      ctx.beginPath(); ctx.ellipse(32, 32, 24, 7, -0.3, 0, Math.PI); ctx.lineWidth = 4; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = 2; ctx.strokeStyle = "#e8bb48"; ctx.stroke();
    }
    ctx.fillStyle = "rgba(255,255,255,0.6)"; ctx.beginPath(); ctx.arc(26, 24, 4, 0, TAU); ctx.fill();
    return [[32, 30], [40, 36]];
  };
  function torso(ctx, P, sleeves, hem) {
    shape(ctx, P.a, () => {
      ctx.moveTo(22, 12); ctx.quadraticCurveTo(32, 18, 42, 12);
      if (sleeves) { ctx.lineTo(54, 20); ctx.lineTo(50, 32); ctx.lineTo(44, 28); } else ctx.lineTo(46, 18);
      ctx.lineTo(45, hem); ctx.lineTo(19, hem);
      if (sleeves) { ctx.lineTo(20, 28); ctx.lineTo(14, 32); ctx.lineTo(10, 20); } else ctx.lineTo(18, 18);
      ctx.closePath();
    }, 2.5);
  }
  D.robe = (ctx, r, P) => {
    const hem = r.form === "long" ? 58 : 46;
    shape(ctx, P.a, () => { ctx.moveTo(22, 12); ctx.quadraticCurveTo(32, 18, 42, 12); ctx.lineTo(54, 22); ctx.lineTo(48, 30); ctx.lineTo(44, 26); ctx.lineTo(48, hem); ctx.lineTo(16, hem); ctx.lineTo(20, 26); ctx.lineTo(16, 30); ctx.lineTo(10, 22); ctx.closePath(); }, 2.5);
    line(ctx, P.d, 2, [[32, 17], [32, hem]]); line(ctx, "#e8bb48", 2.5, [[17, hem - 2], [47, hem - 2]]);
    shape(ctx, P.d, () => ctx.roundRect(20, 32, 24, 4, 1), 1.2);
    return [[25, 42], [39, 24]];
  };
  D.leather = (ctx, r, P) => {
    torso(ctx, P, r.form === "hunter", 52);
    line(ctx, P.d, 1.5, [[32, 16], [32, 52]]);
    for (const y of [24, 31, 38]) { line(ctx, "#2a1c10", 1.5, [[29, y], [35, y]]); }
    shape(ctx, "#3a2a1a", () => ctx.roundRect(19, 42, 26, 5, 1), 1.2); shape(ctx, "#c8a040", () => ctx.roundRect(30, 42, 5, 5, 1), 1);
    return [[24, 30], [40, 30]];
  };
  D.mail = (ctx, r, P) => {
    torso(ctx, P, true, 54);
    ctx.save(); ctx.beginPath(); ctx.rect(19, 14, 26, 40); ctx.clip();
    ctx.strokeStyle = P.d; ctx.lineWidth = 1;
    if (r.form === "chain") { for (let y = 16; y < 54; y += 3.5) for (let x = 19 + ((y / 3.5) % 2) * 1.75; x < 46; x += 3.5) { ctx.beginPath(); ctx.arc(x, y, 1.4, 0, TAU); ctx.stroke(); } }
    else { for (let y = 16; y < 56; y += 5) for (let x = 19 + ((y / 5) % 2) * 3; x < 47; x += 6) { ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI); ctx.stroke(); } }
    ctx.restore(); shine(ctx, P, [[22, 18], [22, 30]]);
    return [[25, 30], [39, 44]];
  };
  D.plate = (ctx, r, P) => {
    if (r.form === "full") { shape(ctx, P.a, () => ctx.ellipse(16, 20, 9, 7, -0.4, 0, TAU), 2); shape(ctx, P.a, () => ctx.ellipse(48, 20, 9, 7, 0.4, 0, TAU), 2); }
    shape(ctx, P.a, () => { ctx.moveTo(20, 14); ctx.quadraticCurveTo(32, 20, 44, 14); ctx.lineTo(46, 34); ctx.quadraticCurveTo(32, 46, 18, 34); ctx.closePath(); }, 2.5);
    if (r.form === "full") for (const y of [42, 48, 54]) shape(ctx, P.a, () => ctx.roundRect(21, y - 6 + (y - 42) * 0, 22, 6, 2), 1.5);
    line(ctx, P.d, 1.5, [[32, 20], [32, 40]]); line(ctx, P.d, 1.5, [[22, 26], [42, 26]]);
    shine(ctx, P, [[24, 18], [25, 32]]);
    return [[26, 32], [38, 22]];
  };
  D.coat = (ctx, r, P) => {
    if (r.form === "cape") shape(ctx, P.d, () => { ctx.moveTo(18, 14); ctx.lineTo(46, 14); ctx.lineTo(54, 58); ctx.lineTo(10, 58); ctx.closePath(); }, 2);
    torso(ctx, P, true, 56);
    line(ctx, P.d, 2, [[32, 16], [32, 56]]);
    shape(ctx, P.d, () => { ctx.moveTo(24, 12); ctx.lineTo(32, 22); ctx.lineTo(40, 12); ctx.lineTo(36, 10); ctx.lineTo(32, 16); ctx.lineTo(28, 10); ctx.closePath(); }, 1.5);
    for (const y of [28, 36, 44]) shape(ctx, "#e8bb48", () => ctx.arc(35, y, 1.6, 0, TAU), 0.8);
    return [[25, 34], [40, 46]];
  };
  D.ring = (ctx, r, P) => {
    ctx.beginPath(); ctx.ellipse(32, 38, 15, 13, 0, 0, TAU); ctx.lineWidth = 8; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = 5; ctx.strokeStyle = P.a; ctx.stroke();
    shine(ctx, P, [[20, 34], [23, 28]]);
    if (r.form === "gem") { shape(ctx, P.a, () => ctx.roundRect(25, 18, 14, 9, 2), 1.5); gem(ctx, 32, 18, 7, P.accent); }
    return [[46, 44], [18, 46]];
  };
  D.pendant = (ctx, r, P) => {
    ctx.beginPath(); ctx.arc(32, 14, 18, 0.15 * Math.PI, 0.85 * Math.PI, true); ctx.strokeStyle = "#9c7420"; ctx.lineWidth = 1.8; ctx.setLineDash([2, 1.5]); ctx.stroke(); ctx.setLineDash([]);
    if (r.form === "pendant") { shape(ctx, P.a, () => ctx.arc(32, 40, 12, 0, TAU), 2); gem(ctx, 32, 40, 6, P.accent); }
    else { shape(ctx, P.a, () => ctx.roundRect(22, 28, 20, 26, 3), 2); line(ctx, P.d, 1.5, [[26, 36], [38, 36]]); line(ctx, P.d, 1.5, [[26, 42], [36, 42]]); shape(ctx, INK, () => ctx.arc(32, 32, 1.6, 0, TAU), 0.5); }
    return [[46, 44], [18, 44]];
  };
  D.charm = (ctx, r, P) => {
    if (r.form === "tablet") {
      shape(ctx, P.a, () => ctx.roundRect(20, 12, 24, 40, 4), 2.5);
      line(ctx, P.d, 2, [[32, 18], [32, 46]]); line(ctx, P.d, 2, [[26, 24], [38, 24]]); line(ctx, P.d, 2, [[27, 34], [37, 40]]);
      line(ctx, "#b83a3a", 2.5, [[32, 52], [30, 60]]); line(ctx, "#b83a3a", 2.5, [[32, 52], [35, 60]]);
    } else {
      shape(ctx, "#e9e3cf", () => { ctx.moveTo(32, 10); ctx.quadraticCurveTo(44, 24, 36, 50); ctx.lineTo(28, 50); ctx.quadraticCurveTo(20, 24, 32, 10); }, 2.5);
      for (const y of [24, 32, 40]) line(ctx, "#8a8070", 1.5, [[28, y], [36, y]]);
      line(ctx, P.a, 3, [[26, 50], [38, 50]]);
    }
    return [[46, 30], [18, 40]];
  };
  D.bracelet = (ctx, r, P) => {
    if (r.form === "metal") {
      ctx.beginPath(); ctx.ellipse(32, 34, 20, 12, 0, 0, TAU); ctx.lineWidth = 10; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = 7; ctx.strokeStyle = P.a; ctx.stroke();
      shine(ctx, P, [[18, 30], [26, 24]]); gem(ctx, 32, 46, 4, P.accent);
    } else {
      for (let i = 0; i < 14; i++) { const a = (i / 14) * TAU; shape(ctx, i % 2 ? P.a : P.d, () => ctx.ellipse(32 + Math.cos(a) * 19, 34 + Math.sin(a) * 11, 4.5, 3, a + 0.8, 0, TAU), 1.2); }
      gem(ctx, 32, 46, 4, P.accent);
    }
    return [[50, 22], [14, 46]];
  };

  // ---- 風格包示意：東方（只覆寫有專屬造型的部分，其餘退回通用版）----
  const EASTERN = {
    sword: (ctx, r, P) => {
      diag(ctx, () => {
        shape(ctx, P.a, () => { ctx.moveTo(-3, 8); ctx.lineTo(-3, -24); ctx.lineTo(0, -29); ctx.lineTo(3, -24); ctx.lineTo(3, 8); ctx.closePath(); });
        line(ctx, P.d, 1, [[0, 6], [0, -22]]);
        shape(ctx, "#2f6a5a", () => ctx.ellipse(0, 9.5, 8, 3, 0, 0, TAU), 1.5); // 劍格：玉色
        shape(ctx, "#2a1c14", () => ctx.roundRect(-2.2, 12, 4.4, 11, 1.5), 1.5);
        ctx.strokeStyle = "#b83a3a"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(0, 23); ctx.quadraticCurveTo(-4, 28, -2, 34); ctx.moveTo(0, 23); ctx.quadraticCurveTo(3, 29, 2, 34); ctx.stroke(); // 劍穗
      });
      return [[36, 26], [28, 36]];
    },
    round_shield: (ctx, r, P) => {
      shape(ctx, "#b89a5a", () => ctx.arc(32, 33, 22, 0, TAU), 2.5); // 藤牌
      ctx.strokeStyle = "#7a5a2a"; ctx.lineWidth = 1.5; for (let rr = 6; rr < 22; rr += 4) { ctx.beginPath(); ctx.arc(32, 33, rr, 0, TAU); ctx.stroke(); }
      shape(ctx, "#b83a3a", () => ctx.arc(32, 33, 6, 0, TAU), 1.5);
      line(ctx, "#e8bb48", 2, [[28, 33], [36, 33]]); line(ctx, "#e8bb48", 2, [[32, 29], [32, 37]]);
      return [[22, 26], [42, 42]];
    },
    robe: (ctx, r, P) => {
      const hem = 58;
      shape(ctx, P.a, () => { ctx.moveTo(24, 12); ctx.lineTo(40, 12); ctx.lineTo(58, 26); ctx.lineTo(50, 34); ctx.lineTo(44, 30); ctx.lineTo(46, hem); ctx.lineTo(18, hem); ctx.lineTo(20, 30); ctx.lineTo(14, 34); ctx.lineTo(6, 26); ctx.closePath(); }, 2.5); // 寬袖
      shape(ctx, "#efe6cf", () => { ctx.moveTo(26, 12); ctx.lineTo(32, 26); ctx.lineTo(38, 12); ctx.lineTo(35, 12); ctx.lineTo(32, 19); ctx.lineTo(29, 12); ctx.closePath(); }, 1.2); // 交領
      line(ctx, P.d, 2, [[32, 26], [40, 40]]);
      shape(ctx, "#2f6a5a", () => ctx.roundRect(19, 33, 26, 5, 1), 1.2); // 腰帶
      ctx.strokeStyle = "#e8bb48"; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.arc(24, 48, 3, Math.PI, 0); ctx.arc(30, 48, 3, Math.PI, 0); ctx.stroke(); // 雲紋
      return [[25, 44], [39, 22]];
    },
  };

  // ---- 槍（遠程主手；槍口朝右上）----
  D.gun = (ctx, r, P) => {
    ctx.save(); ctx.translate(32, 34); ctx.rotate(-0.42);
    const wood = "#7a5232";
    if (r.form === "pistol") {
      ctx.scale(1.45, 1.45);
      shape(ctx, P.a, () => ctx.roundRect(-12, -9, 26, 8, 2));
      shape(ctx, P.d, () => { ctx.moveTo(-10, -2); ctx.lineTo(-2, -2); ctx.lineTo(-4, 12); ctx.lineTo(-12, 12); ctx.closePath(); });
      line(ctx, INK, 1.8, [[-2, -1], [2, 3], [-1, 4]]);
      shine(ctx, P, [[-9, -7], [10, -7]]);
      var muzzle = [20, -7];
    } else if (r.form === "rifle") {
      shape(ctx, wood, () => { ctx.moveTo(-26, -4); ctx.lineTo(-12, -6); ctx.lineTo(-10, 2); ctx.lineTo(-26, 6); ctx.closePath(); });
      shape(ctx, P.a, () => ctx.roundRect(-12, -7, 22, 7, 1.5));
      shape(ctx, P.d, () => ctx.roundRect(10, -5.5, 18, 3.5, 1), 1.5);
      shape(ctx, P.d, () => ctx.roundRect(-6, -12, 12, 4, 1.5), 1.5); // 瞄準鏡
      shape(ctx, P.d, () => { ctx.moveTo(-6, 0); ctx.lineTo(-1, 0); ctx.lineTo(-3, 9); ctx.lineTo(-8, 9); ctx.closePath(); });
      muzzle = [28, -4];
    } else if (r.form === "shotgun") {
      shape(ctx, wood, () => { ctx.moveTo(-26, -4); ctx.lineTo(-12, -7); ctx.lineTo(-10, 2); ctx.lineTo(-26, 7); ctx.closePath(); });
      shape(ctx, P.a, () => ctx.roundRect(-12, -8, 14, 9, 2));
      shape(ctx, P.d, () => ctx.roundRect(2, -8, 24, 4, 1), 1.5);
      shape(ctx, P.d, () => ctx.roundRect(2, -4, 24, 4, 1), 1.5);
      shape(ctx, wood, () => ctx.roundRect(6, 0, 12, 4, 1.5), 1.5); // 泵動護木
      muzzle = [26, -4];
    } else {
      const glow = r.keywords.length ? P.accent : "#5ad8ff";
      shape(ctx, "#e8edf2", () => { ctx.moveTo(-16, -9); ctx.lineTo(14, -9); ctx.quadraticCurveTo(22, -6, 14, -1); ctx.lineTo(-16, -1); ctx.closePath(); });
      shape(ctx, "#3a3f4a", () => { ctx.moveTo(-12, -1); ctx.lineTo(-3, -1); ctx.lineTo(-6, 12); ctx.lineTo(-14, 12); ctx.closePath(); });
      ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 6; shape(ctx, glow, () => ctx.roundRect(-10, -6.5, 22, 3, 1.5), 1); ctx.restore();
      shape(ctx, glow, () => ctx.arc(20, -5, 2.5, 0, TAU), 1.2);
      muzzle = [20, -5];
    }
    ctx.restore();
    const a = -0.42, mx = 32 + Math.cos(a) * muzzle[0] - Math.sin(a) * muzzle[1], my = 34 + Math.sin(a) * muzzle[0] + Math.cos(a) * muzzle[1];
    return [[mx + 2, my - 4], [24, 44]];
  };

  // ---- 手（9 格草案；樣張只先畫皮手套）----
  D.gloves = (ctx, r, P) => {
    shape(ctx, P.a, () => {
      ctx.moveTo(20, 56); ctx.lineTo(20, 34); ctx.lineTo(16, 26); ctx.quadraticCurveTo(14, 21, 19, 22); ctx.lineTo(23, 28);
      ctx.lineTo(23, 12); ctx.quadraticCurveTo(26, 8, 29, 12); ctx.lineTo(29, 24);
      ctx.lineTo(30, 9); ctx.quadraticCurveTo(33, 5, 36, 9); ctx.lineTo(35, 24);
      ctx.lineTo(37, 11); ctx.quadraticCurveTo(40, 8, 42, 12); ctx.lineTo(41, 26);
      ctx.lineTo(43, 17); ctx.quadraticCurveTo(46, 15, 47, 19); ctx.lineTo(45, 38); ctx.lineTo(44, 56); ctx.closePath();
    }, 2.5);
    shape(ctx, P.d, () => ctx.roundRect(18, 46, 28, 10, 2), 2);
    line(ctx, P.d, 1.2, [[26, 30], [38, 30]]);
    for (const x of [24, 32, 40]) shape(ctx, "#c8a040", () => ctx.arc(x, 51, 1.4, 0, TAU), 0.6);
    return [[40, 22], [26, 38]];
  };

  // ======== 9 格：頭（#37）========
  const SKIN_HINT = "#3a3f4a"; // 圖示裡的臉部空洞
  D.hood = (ctx, r, P) => {
    shape(ctx, P.a, () => { ctx.moveTo(12, 52); ctx.quadraticCurveTo(10, 14, 32, 10); ctx.quadraticCurveTo(54, 14, 52, 52); ctx.closePath(); }, 2.5);
    shape(ctx, SKIN_HINT, () => ctx.ellipse(32, 34, 11, 13, 0, 0, TAU), 1.5);
    if (r.form === "cowl") shape(ctx, P.d, () => { ctx.moveTo(8, 50); ctx.quadraticCurveTo(32, 60, 56, 50); ctx.lineTo(58, 58); ctx.lineTo(6, 58); ctx.closePath(); }, 2);
    else line(ctx, P.d, 2, [[14, 48], [50, 48]]);
    return [[46, 22], [18, 26]];
  };
  D.hat = (ctx, r, P) => {
    if (r.form === "wizard") {
      shape(ctx, P.d, () => ctx.ellipse(32, 46, 26, 7, 0, 0, TAU), 2.5);
      shape(ctx, P.a, () => { ctx.moveTo(18, 46); ctx.quadraticCurveTo(26, 26, 30, 8); ctx.quadraticCurveTo(38, 6, 44, 14); ctx.quadraticCurveTo(38, 14, 36, 20); ctx.lineTo(46, 46); ctx.closePath(); }, 2.5);
      shape(ctx, "#e8bb48", () => ctx.roundRect(19, 39, 26, 4, 1), 1.2);
    } else {
      shape(ctx, P.d, () => ctx.ellipse(32, 44, 28, 9, 0, 0, TAU), 2.5);
      shape(ctx, P.a, () => { ctx.moveTo(18, 44); ctx.lineTo(19, 24); ctx.quadraticCurveTo(32, 16, 45, 24); ctx.lineTo(46, 44); ctx.closePath(); }, 2.5);
      shape(ctx, P.d, () => ctx.roundRect(18, 36, 28, 5, 1), 1.2);
      shape(ctx, "#e6e6e0", () => { ctx.moveTo(42, 36); ctx.quadraticCurveTo(52, 22, 48, 14); ctx.quadraticCurveTo(46, 26, 40, 34); ctx.closePath(); }, 1.2); // 羽毛
    }
    return [[48, 22], [16, 30]];
  };
  D.circlet = (ctx, r, P) => {
    if (r.form === "bandana") {
      shape(ctx, P.a, () => { ctx.moveTo(10, 40); ctx.quadraticCurveTo(12, 14, 32, 14); ctx.quadraticCurveTo(52, 14, 54, 40); ctx.quadraticCurveTo(32, 32, 10, 40); }, 2.5);
      shape(ctx, P.d, () => { ctx.moveTo(48, 36); ctx.lineTo(58, 48); ctx.lineTo(52, 52); ctx.lineTo(46, 40); ctx.closePath(); }, 1.8);
      for (const [x, y] of [[22, 24], [32, 21], [42, 24]]) shape(ctx, P.d, () => ctx.arc(x, y, 1.6, 0, TAU), 0.6);
    } else {
      shape(ctx, P.a, () => { ctx.moveTo(12, 44); ctx.lineTo(12, 22); ctx.lineTo(20, 32); ctx.lineTo(26, 16); ctx.lineTo(32, 30); ctx.lineTo(38, 16); ctx.lineTo(44, 32); ctx.lineTo(52, 22); ctx.lineTo(52, 44); ctx.closePath(); }, 2.5);
      shape(ctx, P.d, () => ctx.roundRect(12, 38, 40, 6, 1.5), 1.5);
      gem(ctx, 32, 36, 5, P.accent);
      shine(ctx, P, [[15, 26], [15, 36]]);
    }
    return [[48, 18], [16, 18]];
  };
  D.cap = (ctx, r, P) => {
    shape(ctx, P.a, () => { ctx.moveTo(12, 42); ctx.quadraticCurveTo(12, 14, 32, 14); ctx.quadraticCurveTo(52, 14, 52, 42); ctx.closePath(); }, 2.5);
    if (r.form === "fur") { shape(ctx, "#e9e3cf", () => ctx.roundRect(9, 38, 46, 11, 5), 2); for (let x = 13; x < 52; x += 5) line(ctx, "#b8b09a", 1, [[x, 41], [x + 1.5, 46]]); }
    else { shape(ctx, P.d, () => ctx.roundRect(10, 38, 44, 7, 2), 2); line(ctx, P.d, 1.4, [[32, 15], [32, 38]]); for (const y of [20, 27, 34]) line(ctx, "#2a1c10", 1, [[30, y], [34, y]]); }
    return [[46, 24], [18, 24]];
  };
  D.helmet = (ctx, r, P) => {
    if (r.form === "greathelm") {
      shape(ctx, P.a, () => ctx.roundRect(14, 12, 36, 42, 7), 2.5);
      shape(ctx, INK, () => ctx.roundRect(18, 28, 28, 4, 1), 0.5);
      line(ctx, P.d, 2, [[32, 32], [32, 50]]);
      for (const y of [38, 43]) for (const x of [24, 40]) shape(ctx, INK, () => ctx.arc(x, y, 1, 0, TAU), 0);
    } else {
      shape(ctx, P.a, () => { ctx.moveTo(12, 44); ctx.lineTo(12, 32); ctx.quadraticCurveTo(12, 12, 32, 12); ctx.quadraticCurveTo(52, 12, 52, 32); ctx.lineTo(52, 44); ctx.closePath(); }, 2.5);
      shape(ctx, P.d, () => ctx.roundRect(10, 38, 44, 7, 2), 2);
      shape(ctx, P.d, () => ctx.roundRect(29.5, 38, 5, 14, 1.5), 1.5);
      if (r.form === "horned") for (const s of [-1, 1]) shape(ctx, "#efe6cc", () => { ctx.moveTo(32 + s * 16, 26); ctx.quadraticCurveTo(32 + s * 30, 22, 32 + s * 28, 6); ctx.quadraticCurveTo(32 + s * 24, 18, 32 + s * 14, 20); ctx.closePath(); }, 2);
    }
    shine(ctx, P, [[19, 22], [24, 17]]);
    return [[46, 22], [18, 28]];
  };
  // ======== 9 格：手 ========
  function glove(ctx, P, fingerless, cuff) {
    if (cuff) shape(ctx, P.d, () => ctx.roundRect(17, 44, 30, 14, 3), 2);
    shape(ctx, P.a, () => {
      ctx.moveTo(20, 50); ctx.lineTo(20, 34); ctx.lineTo(16, 26); ctx.quadraticCurveTo(14, 21, 19, 22); ctx.lineTo(23, 28);
      if (fingerless) { ctx.lineTo(23, 20); ctx.lineTo(29, 20); ctx.lineTo(30, 18); ctx.lineTo(36, 18); ctx.lineTo(37, 20); ctx.lineTo(42, 20); ctx.lineTo(43, 24); ctx.lineTo(47, 24); }
      else { ctx.lineTo(23, 12); ctx.quadraticCurveTo(26, 8, 29, 12); ctx.lineTo(29, 24); ctx.lineTo(30, 9); ctx.quadraticCurveTo(33, 5, 36, 9); ctx.lineTo(35, 24); ctx.lineTo(37, 11); ctx.quadraticCurveTo(40, 8, 42, 12); ctx.lineTo(41, 26); ctx.lineTo(43, 17); ctx.quadraticCurveTo(46, 15, 47, 19); }
      ctx.lineTo(45, 38); ctx.lineTo(44, 50); ctx.closePath();
    }, 2.5);
    if (fingerless) for (const [x, y] of [[26, 14], [33, 12], [39.5, 14], [45, 19]]) shape(ctx, "#f0c8a0", () => ctx.roundRect(x - 2.5, y, 5, 7, 2.5), 1.5);
  }
  D.cloth_gloves = (ctx, r, P) => { glove(ctx, P, r.form === "fingerless", false); line(ctx, P.d, 1.5, [[21, 44], [44, 44]]); return [[40, 30], [26, 38]]; };
  D.leather_gloves = (ctx, r, P) => {
    glove(ctx, P, false, r.form === "long");
    line(ctx, P.d, 1.2, [[26, 30], [38, 30]]);
    if (r.form === "short") shape(ctx, P.d, () => ctx.roundRect(19, 44, 26, 7, 2), 1.8);
    for (const x of [24, 32, 40]) shape(ctx, "#c8a040", () => ctx.arc(x, 48, 1.3, 0, TAU), 0.6);
    return [[40, 22], [26, 38]];
  };
  D.gauntlets = (ctx, r, P) => {
    shape(ctx, P.d, () => ctx.roundRect(16, 42, 32, 16, 3), 2);
    glove(ctx, P, false, false);
    if (r.form === "plate") { for (const y of [28, 34, 40]) line(ctx, P.d, 1.5, [[21, y], [45, y - 1]]); shape(ctx, P.a, () => ctx.ellipse(32, 46, 14, 5, 0, 0, TAU), 1.8); }
    else { ctx.save(); ctx.beginPath(); ctx.rect(20, 26, 26, 30); ctx.clip(); ctx.strokeStyle = P.d; ctx.lineWidth = 1; for (let y = 27; y < 56; y += 3) for (let x = 20 + ((y / 3) % 2) * 1.5; x < 46; x += 3) { ctx.beginPath(); ctx.arc(x, y, 1.2, 0, TAU); ctx.stroke(); } ctx.restore(); }
    shine(ctx, P, [[23, 30], [23, 40]]);
    return [[42, 18], [24, 50]];
  };
  D.bracers = (ctx, r, P) => {
    if (r.form === "ring") {
      for (const y of [22, 40]) { ctx.beginPath(); ctx.ellipse(32, y, 18, 7, 0, 0, TAU); ctx.lineWidth = 9; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = 6; ctx.strokeStyle = P.a; ctx.stroke(); }
      shine(ctx, P, [[18, 20], [24, 16]]); gem(ctx, 32, 47, 3.5, P.accent);
    } else {
      shape(ctx, P.a, () => { ctx.moveTo(18, 12); ctx.lineTo(46, 12); ctx.lineTo(44, 54); ctx.lineTo(20, 54); ctx.closePath(); }, 2.5);
      for (const y of [20, 32, 44]) { shape(ctx, P.d, () => ctx.roundRect(18, y - 2, 28, 4, 1), 1.2); shape(ctx, "#c8a040", () => ctx.roundRect(30, y - 2.5, 4, 5, 1), 0.8); }
      line(ctx, "#2a1c10", 1, [[24, 14], [22, 52]]);
    }
    return [[48, 30], [16, 30]];
  };
  // ======== 9 格：腳 ========
  function boot(ctx, P, top, toe) {
    shape(ctx, P.a, () => { ctx.moveTo(22, top); ctx.lineTo(38, top); ctx.lineTo(38, 42); ctx.quadraticCurveTo(52, 42, 54, 50); ctx.lineTo(54, 54); ctx.lineTo(20, 54); ctx.lineTo(20, 46); ctx.closePath(); }, 2.5);
    shape(ctx, P.d, () => ctx.roundRect(18, 52, 38, 5, 2), 2);
    if (toe) shape(ctx, P.d, () => { ctx.moveTo(42, 44); ctx.quadraticCurveTo(54, 44, 58, 52); ctx.lineTo(44, 52); ctx.closePath(); }, 1.8);
  }
  D.shoes = (ctx, r, P) => {
    boot(ctx, P, 36, false);
    if (r.form === "wrapped") { boot(ctx, P, 14, false); for (let y = 18; y < 44; y += 6) line(ctx, P.d, 1.5, [[22, y], [38, y + 3]]); }
    line(ctx, P.d, 1.5, [[22, 40], [38, 40]]);
    return [[46, 30], [28, 46]];
  };
  D.boots = (ctx, r, P) => {
    boot(ctx, P, r.form === "tall" ? 8 : 24, false);
    shape(ctx, P.d, () => ctx.roundRect(20, (r.form === "tall" ? 8 : 24) - 2, 20, 5, 1.5), 1.5);
    for (const y of [32, 38]) shape(ctx, "#c8a040", () => ctx.arc(36, y, 1.2, 0, TAU), 0.5);
    return [[46, 30], [28, 46]];
  };
  D.iron_boots = (ctx, r, P) => {
    boot(ctx, P, 20, r.form === "sabaton");
    for (const y of [28, 36]) line(ctx, P.d, 1.6, [[21, y], [38, y]]);
    shine(ctx, P, [[24, 24], [24, 44]]);
    return [[48, 30], [28, 46]];
  };
  D.greaves = (ctx, r, P) => {
    boot(ctx, P, 6, false);
    shape(ctx, P.d, () => ctx.roundRect(20, 18, 20, 3, 1), 1.2);
    if (r.form === "knee") shape(ctx, P.a, () => ctx.ellipse(30, 10, 11, 7, 0, 0, TAU), 2);
    shine(ctx, P, [[24, 12], [24, 44]]);
    return [[48, 28], [28, 46]];
  };
  // 戒指加「印戒」形制
  const baseRing = D.ring;
  D.ring = (ctx, r, P) => {
    if (r.form !== "signet") return baseRing(ctx, r, P);
    ctx.beginPath(); ctx.ellipse(32, 40, 15, 12, 0, 0, TAU); ctx.lineWidth = 8; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = 5; ctx.strokeStyle = P.a; ctx.stroke();
    shape(ctx, P.a, () => ctx.roundRect(21, 14, 22, 16, 3), 2.2);
    shape(ctx, P.d, () => ctx.roundRect(24, 17, 16, 10, 2), 1.2);
    line(ctx, P.a, 1.6, [[28, 25], [32, 19], [36, 25]]);
    shine(ctx, P, [[20, 36], [23, 30]]);
    return [[50, 44], [14, 44]];
  };

  /** 外觀 → 紙娃娃部件（slot 用紙娃娃的欄位名）。項鍊、戒指不畫，回傳 null。 */
  const ELEMENT_OF = { ignite: "fire", wet: "water", shock: "lightning", freeze: "ice" };
  const DOLL = {
    head: { hood: () => "hood", hat: (f) => (f === "wide" ? "wide_hat" : "wizard_hat"), circlet: (f) => (f === "crown" ? "crown" : "bandana"), cap: () => "cap", helmet: (f) => ({ horned: "horned_helm", greathelm: "greathelm" })[f] ?? "helmet" },
    hands: { cloth_gloves: () => "gloves", leather_gloves: () => "gloves", gauntlets: () => "gauntlets", bracers: () => "bracers" },
    feet: { shoes: () => "shoes", boots: () => "boots", iron_boots: () => "iron_boots", greaves: () => "greaves" },
    off_hand: { round_shield: () => "shield_round", kite_shield: () => "shield_kite", tome: () => "tome", orb: () => "orb" },
  };
  function dollItem(item) {
    const r = resolve(item); const K = KINDS[r.kind];
    if (K.slot === "neck" || K.slot === "ring") return null;
    const slot = { main: "main_hand", off: "off_hand", body: "body", head: "head", hands: "hands", feet: "feet" }[K.slot];
    const kind = DOLL[slot]?.[r.kind]?.(r.form) ?? r.kind;
    const el = r.keywords.map((k) => ELEMENT_OF[k]).find(Boolean);
    const out = { slot, kind, form: r.form, material: r.material };
    if (r.dye) out.color = DYE[r.dye];
    if (el) out.element = el;
    return out;
  }
  /** 一整套裝備 → 紙娃娃的 gear；成對武器主手、副手各一把。 */
  function dollGear(items) {
    const gear = {};
    for (const it of items) {
      const d = dollItem(it); if (!d) continue;
      gear[d.slot] = d;
      if (KINDS[resolve(it).kind].pair) gear.off_hand = { ...d, slot: "off_hand", kind: d.kind === "dual_dagger" ? "dagger" : "pistol" };
    }
    if (gear.main_hand?.kind === "dual_dagger") gear.main_hand = { ...gear.main_hand, kind: "dagger" };
    if (gear.main_hand?.kind === "dual_pistol") gear.main_hand = { ...gear.main_hand, kind: "pistol" };
    return gear;
  }

  // ======== 武器擴充（#34，08-裝備.md 8.11）========
  const WOOD = "#7a5232", WOOD_D = "#4e321c";
  /** 以槍身方向（往右上 −0.42 rad）畫；回傳槍口位置（64 格座標）。 */
  function gunFrame(ctx, fn, muzzle) {
    ctx.save(); ctx.translate(32, 34); ctx.rotate(-0.42); fn(); ctx.restore();
    const a = -0.42;
    return [32 + Math.cos(a) * muzzle[0] - Math.sin(a) * muzzle[1], 34 + Math.sin(a) * muzzle[0] + Math.cos(a) * muzzle[1]];
  }
  function flintHammer(ctx, x, y) { shape(ctx, "#454c58", () => { ctx.moveTo(x, y); ctx.lineTo(x - 2, y - 6); ctx.lineTo(x + 2, y - 7); ctx.lineTo(x + 3, y); ctx.closePath(); }, 1.2); }
  D.longgun = (ctx, r, P) => {
    const m = gunFrame(ctx, () => {
      if (r.form === "flintlock") {
        shape(ctx, WOOD, () => { ctx.moveTo(-28, -2); ctx.lineTo(-14, -6); ctx.lineTo(16, -6); ctx.lineTo(16, -2); ctx.lineTo(-12, 0); ctx.lineTo(-28, 6); ctx.closePath(); });
        shape(ctx, P.a, () => ctx.roundRect(-12, -9, 40, 3.5, 1.2), 1.5);
        for (const x of [-2, 10]) shape(ctx, P.d, () => ctx.roundRect(x, -9.5, 2.5, 7, 0.8), 1);
        flintHammer(ctx, -10, -6);
      } else if (r.form === "hunting") {
        shape(ctx, WOOD, () => { ctx.moveTo(-28, -3); ctx.lineTo(-12, -6); ctx.lineTo(-10, 2); ctx.lineTo(-28, 6); ctx.closePath(); });
        shape(ctx, P.a, () => ctx.roundRect(-12, -7, 18, 7, 1.5));
        shape(ctx, P.d, () => ctx.roundRect(6, -6, 22, 3.5, 1), 1.5);
        shape(ctx, WOOD, () => ctx.roundRect(6, -2.5, 14, 3.5, 1.2), 1.2);
        shape(ctx, P.d, () => { ctx.moveTo(-6, 0); ctx.lineTo(-1, 0); ctx.lineTo(-3, 8); ctx.lineTo(-8, 8); ctx.closePath(); });
      } else {
        shape(ctx, P.d, () => { ctx.moveTo(-28, -4); ctx.lineTo(-12, -6); ctx.lineTo(-10, 2); ctx.lineTo(-22, 2); ctx.lineTo(-28, 6); ctx.closePath(); });
        shape(ctx, P.a, () => ctx.roundRect(-12, -7, 20, 7, 1.5));
        shape(ctx, P.d, () => ctx.roundRect(8, -5.5, 22, 3, 1), 1.5);
        shape(ctx, "#2a2d33", () => ctx.roundRect(-8, -14, 16, 5, 2), 1.5); // 瞄準鏡
        shape(ctx, "#8fe3ff", () => ctx.arc(8, -11.5, 1.6, 0, TAU), 0.8);
        line(ctx, INK, 1.8, [[18, -2], [14, 8]]); line(ctx, INK, 1.8, [[18, -2], [22, 8]]); // 腳架
      }
      shine(ctx, P, [[-10, -8], [8, -8]]);
    }, [r.form === "flintlock" ? 28 : 30, -6]);
    return [[m[0] - 2, m[1] - 4], [24, 44]];
  };
  D.pistol = (ctx, r, P) => {
    const m = gunFrame(ctx, () => {
      ctx.scale(1.4, 1.4);
      if (r.form === "flintlock") {
        shape(ctx, WOOD, () => { ctx.moveTo(-6, -6); ctx.lineTo(4, -6); ctx.lineTo(4, -2); ctx.quadraticCurveTo(-4, 0, -10, 10); ctx.lineTo(-15, 8); ctx.quadraticCurveTo(-10, 0, -6, -6); });
        shape(ctx, P.a, () => ctx.roundRect(-2, -8.5, 20, 3.5, 1.2), 1.5);
        flintHammer(ctx, -4, -6);
      } else if (r.form === "revolver") {
        shape(ctx, P.a, () => ctx.roundRect(-2, -8, 20, 4, 1.2), 1.5);
        shape(ctx, P.d, () => ctx.roundRect(-4, -9, 9, 8, 2.5), 1.5);
        for (const x of [-1.5, 2.5]) line(ctx, INK, 1, [[x, -8], [x, -2]]);
        shape(ctx, WOOD, () => { ctx.moveTo(-6, -4); ctx.lineTo(-2, -2); ctx.lineTo(-6, 10); ctx.lineTo(-11, 8); ctx.closePath(); });
        line(ctx, INK, 1.6, [[-1, -1], [2, 2], [-1, 3]]);
      } else {
        shape(ctx, P.a, () => ctx.roundRect(-4, -9, 14, 3.5, 1), 1.5);
        shape(ctx, P.a, () => ctx.roundRect(-4, -5.5, 14, 3.5, 1), 1.5);
        shape(ctx, "#e8bb48", () => ctx.roundRect(-6, -9, 4, 7, 1), 1.2);
        shape(ctx, WOOD, () => { ctx.moveTo(-6, -2); ctx.lineTo(-2, -2); ctx.lineTo(-4, 6); ctx.lineTo(-8, 5); ctx.closePath(); });
      }
      shine(ctx, P, [[0, -7.5], [14, -7.5]]);
    }, [24, -9]);
    return [[m[0], m[1] - 4], [24, 44]];
  };
  D.shotgun = (ctx, r, P) => {
    const m = gunFrame(ctx, () => {
      shape(ctx, WOOD, () => { ctx.moveTo(-28, -3); ctx.lineTo(-12, -7); ctx.lineTo(-10, 2); ctx.lineTo(-28, 7); ctx.closePath(); });
      if (r.form === "blunderbuss") {
        shape(ctx, P.a, () => { ctx.moveTo(-12, -8); ctx.lineTo(16, -7); ctx.lineTo(26, -12); ctx.lineTo(26, 2); ctx.lineTo(16, -2); ctx.lineTo(-12, -1); ctx.closePath(); });
        flintHammer(ctx, -10, -7);
      } else if (r.form === "double") {
        shape(ctx, P.a, () => ctx.roundRect(-12, -8, 10, 9, 2));
        shape(ctx, P.d, () => ctx.roundRect(-2, -8, 28, 4, 1), 1.5); shape(ctx, P.d, () => ctx.roundRect(-2, -4, 28, 4, 1), 1.5);
        shape(ctx, WOOD, () => ctx.roundRect(0, 0, 10, 3.5, 1.2), 1.2);
      } else {
        shape(ctx, P.a, () => ctx.roundRect(-12, -8, 14, 9, 2));
        shape(ctx, P.d, () => ctx.roundRect(2, -8, 24, 4, 1), 1.5); shape(ctx, P.d, () => ctx.roundRect(2, -4, 24, 4, 1), 1.5);
        shape(ctx, WOOD, () => ctx.roundRect(6, 0, 12, 4, 1.5), 1.5);
      }
      shape(ctx, P.d, () => { ctx.moveTo(-6, 0); ctx.lineTo(-1, 0); ctx.lineTo(-3, 8); ctx.lineTo(-8, 8); ctx.closePath(); });
      shine(ctx, P, [[-10, -6], [0, -6]]);
    }, [26, -5]);
    return [[m[0] - 2, m[1] - 4], [24, 44]];
  };
  D.crossbow = (ctx, r, P) => {
    ctx.save(); ctx.translate(32, 34); ctx.rotate(-Math.PI / 4);
    const wide = r.form === "heavy" ? 24 : 19;
    shape(ctx, r.material === "wood" ? WOOD : P.d, () => ctx.roundRect(-3, -14, 6, 32, 2), 1.8); // 弩身
    ctx.beginPath(); ctx.moveTo(-wide, -4); ctx.quadraticCurveTo(0, -18, wide, -4);
    ctx.lineWidth = r.form === "heavy" ? 7 : 5.5; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = r.form === "heavy" ? 4.5 : 3.2; ctx.strokeStyle = P.a; ctx.stroke(); // 弩臂
    line(ctx, "#e6e0d0", 1, [[-wide + 1, -4], [0, 4], [wide - 1, -4]]); // 弦
    shape(ctx, "#c3ccd6", () => { ctx.moveTo(0, -22); ctx.lineTo(1.8, -17); ctx.lineTo(-1.8, -17); ctx.closePath(); }, 1); // 弩箭頭
    line(ctx, "#a06a36", 1.6, [[0, -17], [0, 3]]);
    if (r.form === "heavy") { shape(ctx, P.d, () => ctx.arc(0, 14, 4.5, 0, TAU), 1.5); line(ctx, INK, 1.6, [[0, 14], [7, 18]]); }
    if (r.form === "repeater") shape(ctx, WOOD_D, () => ctx.roundRect(-5, -12, 10, 12, 1.5), 1.5);
    shape(ctx, P.handle, () => ctx.roundRect(-2.5, 6, 5, 9, 1.5), 1.2);
    ctx.restore();
    return [[40, 18], [24, 40]];
  };
  D.fist = (ctx, r, P) => {
    // 拳頭朝右上；套在拳上的部分＝P.a
    ctx.save(); ctx.translate(30, 36); ctx.rotate(-0.6);
    shape(ctx, "#8a5a32", () => ctx.roundRect(-14, -6, 12, 12, 3), 1.8); // 腕套
    shape(ctx, "#f0c8a0", () => ctx.roundRect(-3, -8, 13, 16, 5), 1.8); // 拳
    if (r.form === "katar") {
      shape(ctx, P.a, () => { ctx.moveTo(8, -4); ctx.lineTo(28, 0); ctx.lineTo(8, 4); ctx.closePath(); });
      shape(ctx, P.d, () => ctx.roundRect(4, -9, 4, 18, 1), 1.5);
    } else if (r.form === "knuckle") {
      shape(ctx, P.a, () => ctx.roundRect(7, -9, 6, 18, 2.5));
      for (const y of [-6, -1.5, 3]) shape(ctx, P.d, () => ctx.arc(14, y + 1.5, 1.8, 0, TAU), 1);
    } else {
      for (const y of [-6, 0, 6]) shape(ctx, P.a, () => { ctx.moveTo(8, y - 1.6); ctx.quadraticCurveTo(22, y - 4, 27, y + 2); ctx.quadraticCurveTo(20, y, 8, y + 1.6); ctx.closePath(); }, 1.5);
    }
    ctx.restore();
    return [[44, 18], [18, 46]];
  };
  D.scythe = (ctx, r, P) => {
    diag(ctx, () => {
      const len = r.form === "hook" ? 30 : 46;
      shape(ctx, P.handle, () => ctx.roundRect(-2.2, -24, 4.4, len, 2), 1.5);
      if (r.form === "long") shape(ctx, P.a, () => { ctx.moveTo(1, -24); ctx.quadraticCurveTo(-18, -30, -26, -12); ctx.quadraticCurveTo(-16, -22, 1, -19); ctx.closePath(); });
      else if (r.form === "crescent") { shape(ctx, P.a, () => { ctx.moveTo(1, -24); ctx.quadraticCurveTo(-18, -30, -24, -14); ctx.quadraticCurveTo(-14, -22, 1, -19); ctx.closePath(); }); shape(ctx, P.a, () => { ctx.moveTo(-1, -24); ctx.quadraticCurveTo(14, -30, 18, -18); ctx.quadraticCurveTo(10, -23, -1, -20); ctx.closePath(); }); }
      else shape(ctx, P.a, () => { ctx.moveTo(1, -24); ctx.quadraticCurveTo(-12, -28, -14, -16); ctx.quadraticCurveTo(-10, -12, -7, -15); ctx.quadraticCurveTo(-8, -21, 1, -19); ctx.closePath(); });
      shine(ctx, P, [[-6, -25], [-14, -22]]);
    });
    return [[22, 18], [40, 40]];
  };
  D.whip = (ctx, r, P) => {
    shape(ctx, P.handle, () => { ctx.save(); ctx.translate(16, 48); ctx.rotate(-0.7); ctx.roundRect(-2.5, -10, 5, 14, 2); ctx.restore(); }, 1.5);
    const pts = []; for (let i = 0; i <= 24; i++) { const t = i / 24; pts.push([20 + t * 34 - Math.sin(t * Math.PI) * 6, 42 - t * 30 + Math.sin(t * Math.PI * 2.2) * 9 * t]); }
    if (r.form === "chain") {
      pts.forEach(([x, y], i) => { if (i % 2 === 0) { ctx.beginPath(); ctx.ellipse(x, y, 2.6, 1.8, i * 0.4, 0, TAU); ctx.lineWidth = 2.8; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = 1.6; ctx.strokeStyle = P.a; ctx.stroke(); } });
    } else {
      ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.lineCap = "round"; ctx.lineWidth = 5; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = 3; ctx.strokeStyle = r.form === "bladed" ? P.d : P.a; ctx.stroke(); ctx.lineCap = "butt";
      if (r.form === "bladed") pts.forEach(([x, y], i) => { if (i % 3 === 1) shape(ctx, P.a, () => { ctx.moveTo(x - 3, y + 1); ctx.lineTo(x, y - 4); ctx.lineTo(x + 3, y + 1); ctx.closePath(); }, 1); });
    }
    return [[44, 16], [30, 34]];
  };
  /** 成對武器：畫兩把（左邊一把縮小、右邊鏡像）。 */
  function pair(base) {
    return (ctx, r, P) => {
      ctx.save(); ctx.translate(32, 33); ctx.scale(0.78, 0.78); ctx.translate(-36, -33); const s = base(ctx, r, P); ctx.restore();
      ctx.save(); ctx.translate(32, 33); ctx.scale(-0.78, 0.78); ctx.translate(-36, -31); base(ctx, r, P); ctx.restore();
      return [[32 + (s[0][0] - 36) * 0.78, 33 + (s[0][1] - 33) * 0.78], [32 - (s[0][0] - 36) * 0.78, 33 + (s[0][1] - 31) * 0.78]];
    };
  }
  D.dual_dagger = pair(D.dagger);
  D.dual_pistol = pair(D.pistol);
  // 圖騰杖：疊兩張刻臉＋羽毛
  const baseStaff = D.staff;
  D.staff = (ctx, r, P) => {
    if (r.form !== "totem") return baseStaff(ctx, r, P);
    diag(ctx, () => {
      shape(ctx, P.a, () => ctx.roundRect(-3, -12, 6, 38, 2), 1.5);
      for (const [y, c] of [[-26, "#b83a3a"], [-17, "#3a8a8a"]]) {
        shape(ctx, P.a, () => ctx.roundRect(-6, y, 12, 9, 2.5), 1.5);
        shape(ctx, c, () => ctx.rect(-4, y + 2, 8, 2), 0.8);
        shape(ctx, INK, () => ctx.rect(-3, y + 5.5, 6, 1.5), 0);
      }
      for (const s of [-1, 1]) shape(ctx, "#e6e6e0", () => { ctx.moveTo(s * 6, -24); ctx.quadraticCurveTo(s * 16, -30, s * 14, -20); ctx.quadraticCurveTo(s * 10, -21, s * 6, -21); ctx.closePath(); }, 1.2);
      const orb = r.keywords.length ? P.accent : "#7dffb0";
      shape(ctx, orb, () => ctx.arc(0, -30, 3, 0, TAU), 1.2);
    });
    return [[42, 18], [28, 38]];
  };
  // 科技風包的槍：全部改成能量槍外型（形制仍決定長短）
  function energyGun(len) {
    return (ctx, r, P) => {
      const glow = r.keywords.length ? P.accent : "#5ad8ff";
      const m = gunFrame(ctx, () => {
        const L = len[r.form] ?? 14;
        shape(ctx, "#e8edf2", () => { ctx.moveTo(-12, -9); ctx.lineTo(L, -9); ctx.quadraticCurveTo(L + 8, -6, L, -1); ctx.lineTo(-12, -1); ctx.closePath(); });
        if (L > 16) shape(ctx, "#3a3f4a", () => { ctx.moveTo(-26, -6); ctx.lineTo(-12, -8); ctx.lineTo(-12, 0); ctx.lineTo(-26, 4); ctx.closePath(); });
        shape(ctx, "#3a3f4a", () => { ctx.moveTo(-10, -1); ctx.lineTo(-3, -1); ctx.lineTo(-6, 11); ctx.lineTo(-13, 11); ctx.closePath(); });
        ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 6; shape(ctx, glow, () => ctx.roundRect(-8, -6.5, L + 2, 3, 1.5), 1); ctx.restore();
        shape(ctx, glow, () => ctx.arc(L + 5, -5, 2.4, 0, TAU), 1.2);
      }, [26, -5]);
      return [[m[0] - 2, m[1] - 4], [24, 44]];
    };
  }
  const SCIFI_GUNS = {
    longgun: energyGun({ flintlock: 26, hunting: 22, sniper: 28 }),
    pistol: energyGun({ flintlock: 12, revolver: 10, derringer: 6 }),
    shotgun: energyGun({ blunderbuss: 16, double: 18, pump: 18 }),
  };
  SCIFI_GUNS.dual_pistol = pair(SCIFI_GUNS.pistol);

  // ---- 風格包：魔導科技（黃銅＋晶能＋符文）----
  const BRASS = "#c8963c", BRASS_D = "#7a5a22";
  const MAGITECH = {
    sword: (ctx, r, P) => {
      const glow = r.keywords.length ? P.accent : "#8fe3ff";
      diag(ctx, () => {
        shape(ctx, P.a, () => { ctx.moveTo(-4, 8); ctx.lineTo(-4, -22); ctx.lineTo(0, -28); ctx.lineTo(4, -22); ctx.lineTo(4, 8); ctx.closePath(); });
        ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 5; line(ctx, glow, 1.6, [[0, 6], [0, -22]]); ctx.restore();
        for (const y of [-4, -12]) line(ctx, glow, 1.2, [[-3, y], [-1, y - 2], [1, y], [3, y - 2]]);
        shape(ctx, BRASS, () => ctx.arc(0, 10, 5.5, 0, TAU), 1.5); // 齒輪護手
        for (let i = 0; i < 8; i++) { const t = (i / 8) * TAU; shape(ctx, BRASS, () => ctx.rect(Math.cos(t) * 6 - 1.2, 10 + Math.sin(t) * 6 - 1.2, 2.4, 2.4), 0.8); }
        shape(ctx, glow, () => ctx.arc(0, 10, 2, 0, TAU), 1);
        shape(ctx, BRASS_D, () => ctx.roundRect(-2.2, 15, 4.4, 9, 1.5), 1.5);
      });
      return [[36, 26], [28, 36]];
    },
    round_shield: (ctx, r, P) => {
      const glow = r.keywords.length ? P.accent : "#8fe3ff";
      shape(ctx, BRASS, () => ctx.arc(32, 33, 22, 0, TAU), 2.5);
      for (let i = 0; i < 12; i++) { const t = (i / 12) * TAU; shape(ctx, BRASS_D, () => ctx.arc(32 + Math.cos(t) * 18, 33 + Math.sin(t) * 18, 1.4, 0, TAU), 0.6); }
      ctx.strokeStyle = BRASS_D; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(32, 33, 13, 0, TAU); ctx.stroke();
      ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 8; gem(ctx, 32, 33, 8, glow); ctx.restore();
      return [[22, 26], [42, 42]];
    },
    robe: (ctx, r, P) => {
      const glow = r.keywords.length ? P.accent : "#8fe3ff";
      D.robe(ctx, r, P);
      shape(ctx, BRASS, () => ctx.roundRect(19, 31, 26, 6, 1.5), 1.2);
      ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 5; shape(ctx, glow, () => ctx.arc(32, 34, 2.5, 0, TAU), 1); line(ctx, glow, 1.4, [[24, 40], [24, 54]]); line(ctx, glow, 1.4, [[40, 40], [40, 54]]); ctx.restore();
      shape(ctx, BRASS, () => ctx.ellipse(16, 22, 5, 4, -0.4, 0, TAU), 1.2); shape(ctx, BRASS, () => ctx.ellipse(48, 22, 5, 4, 0.4, 0, TAU), 1.2);
      return [[25, 46], [39, 22]];
    },
    axe: (ctx, r, P) => {
      const glow = r.keywords.length ? P.accent : "#8fe3ff";
      diag(ctx, () => {
        shape(ctx, BRASS_D, () => ctx.roundRect(-2.5, -24, 5, 46, 2), 1.5);
        shape(ctx, P.a, () => { ctx.moveTo(2, -26); ctx.quadraticCurveTo(20, -32, 20, -12); ctx.quadraticCurveTo(14, -6, 2, -8); ctx.closePath(); });
        ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 5; ctx.beginPath(); ctx.moveTo(5, -24); ctx.quadraticCurveTo(18, -27, 18, -12); ctx.strokeStyle = glow; ctx.lineWidth = 1.6; ctx.stroke(); ctx.restore();
        shape(ctx, BRASS, () => ctx.arc(0, -17, 4, 0, TAU), 1.2); shape(ctx, glow, () => ctx.arc(0, -17, 1.6, 0, TAU), 0.6);
      });
      return [[40, 20], [24, 40]];
    },
  };
  // ---- 風格包：科技（深色金屬＋電路＋發光）----
  const DARK = "#2a2f38", DARK2 = "#454c58";
  const SCIFI = {
    sword: (ctx, r, P) => {
      const glow = r.keywords.length ? P.accent : "#5ad8ff";
      diag(ctx, () => {
        ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 10;
        shape(ctx, glow, () => { ctx.moveTo(-3, 6); ctx.lineTo(-3, -24); ctx.quadraticCurveTo(0, -30, 3, -24); ctx.lineTo(3, 6); ctx.closePath(); }, 1);
        ctx.restore();
        shape(ctx, "rgba(255,255,255,0.85)", () => ctx.roundRect(-1, -22, 2, 27, 1), 0);
        shape(ctx, DARK2, () => ctx.roundRect(-5, 6, 10, 4, 1), 1.5);
        shape(ctx, DARK, () => ctx.roundRect(-3, 10, 6, 14, 1.5), 1.5);
        for (const y of [13, 17, 21]) line(ctx, glow, 1, [[-2, y], [2, y]]);
      });
      return [[36, 26], [28, 36]];
    },
    round_shield: (ctx, r, P) => {
      const glow = r.keywords.length ? P.accent : "#5ad8ff";
      ctx.save(); ctx.globalAlpha = 0.35; shape(ctx, glow, () => { for (let i = 0; i < 6; i++) { const t = (i / 6) * TAU - Math.PI / 2; ctx.lineTo(32 + Math.cos(t) * 23, 33 + Math.sin(t) * 23); } ctx.closePath(); }, 0); ctx.restore();
      ctx.strokeStyle = glow; ctx.lineWidth = 1; ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 6;
      for (const [hx, hy] of [[32, 33], [32, 21], [32, 45], [21.6, 27], [42.4, 27], [21.6, 39], [42.4, 39]]) { ctx.beginPath(); for (let i = 0; i < 6; i++) { const t = (i / 6) * TAU; ctx.lineTo(hx + Math.cos(t) * 6.5, hy + Math.sin(t) * 6.5); } ctx.closePath(); ctx.stroke(); }
      ctx.restore();
      shape(ctx, DARK, () => ctx.roundRect(26, 50, 12, 8, 2), 1.5); shape(ctx, glow, () => ctx.arc(32, 54, 1.8, 0, TAU), 0.6);
      return [[22, 26], [42, 42]];
    },
    robe: (ctx, r, P) => {
      const glow = r.keywords.length ? P.accent : "#5ad8ff";
      shape(ctx, DARK2, () => { ctx.moveTo(22, 12); ctx.quadraticCurveTo(32, 16, 42, 12); ctx.lineTo(54, 22); ctx.lineTo(50, 34); ctx.lineTo(45, 30); ctx.lineTo(45, 56); ctx.lineTo(19, 56); ctx.lineTo(19, 30); ctx.lineTo(14, 34); ctx.lineTo(10, 22); ctx.closePath(); }, 2.5);
      shape(ctx, DARK, () => ctx.roundRect(23, 18, 18, 18, 3), 1.5);
      ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 6;
      line(ctx, glow, 1.6, [[32, 22], [32, 30], [36, 34], [36, 52]]); line(ctx, glow, 1.6, [[26, 40], [26, 52]]); shape(ctx, glow, () => ctx.arc(32, 22, 2.2, 0, TAU), 0.8);
      ctx.restore();
      return [[25, 46], [40, 22]];
    },
    axe: (ctx, r, P) => {
      const glow = r.keywords.length ? P.accent : "#5ad8ff";
      diag(ctx, () => {
        shape(ctx, DARK, () => ctx.roundRect(-2.5, -24, 5, 46, 2), 1.5);
        for (const y of [4, 10, 16]) line(ctx, glow, 1, [[-2, y], [2, y]]);
        ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 10; shape(ctx, glow, () => { ctx.moveTo(3, -26); ctx.quadraticCurveTo(20, -30, 19, -12); ctx.quadraticCurveTo(13, -8, 3, -9); ctx.closePath(); }, 1); ctx.restore();
        shape(ctx, DARK2, () => ctx.roundRect(-4, -27, 9, 20, 2), 1.5);
      });
      return [[40, 20], [24, 40]];
    },
  };
  // ---- 風格包：現代（工業製品、橡膠、塗裝）----
  const MODERN = {
    sword: (ctx, r, P) => { // 開山刀
      diag(ctx, () => {
        shape(ctx, P.a, () => { ctx.moveTo(-3, 8); ctx.lineTo(-3, -18); ctx.quadraticCurveTo(-3, -28, 5, -27); ctx.lineTo(5, 8); ctx.closePath(); });
        line(ctx, "rgba(255,255,255,0.7)", 1.2, [[-1.5, 6], [-1.5, -18]]);
        shape(ctx, "#2a2d33", () => ctx.roundRect(-3.5, 8, 9, 15, 3), 1.5);
        for (const y of [11, 15, 19]) shape(ctx, "#5a5f68", () => ctx.arc(1, y, 1, 0, TAU), 0);
      });
      return [[36, 26], [28, 36]];
    },
    round_shield: (ctx, r, P) => { // 鎮暴盾
      ctx.save(); ctx.globalAlpha = 0.45; shape(ctx, "#b8d4e8", () => ctx.roundRect(16, 8, 32, 50, 5), 0); ctx.restore();
      ctx.beginPath(); ctx.roundRect(16, 8, 32, 50, 5); ctx.lineWidth = 2.5; ctx.strokeStyle = INK; ctx.stroke(); ctx.lineWidth = 2; ctx.strokeStyle = "#2a2d33"; ctx.stroke();
      line(ctx, "rgba(255,255,255,0.8)", 2, [[21, 14], [21, 30]]);
      shape(ctx, "#2a2d33", () => ctx.roundRect(19, 40, 26, 6, 1), 1.2);
      return [[24, 24], [40, 50]];
    },
    robe: (ctx, r, P) => { // 連帽外套
      shape(ctx, P.a, () => { ctx.moveTo(20, 14); ctx.quadraticCurveTo(32, 4, 44, 14); ctx.lineTo(54, 22); ctx.lineTo(51, 38); ctx.lineTo(45, 36); ctx.lineTo(45, 54); ctx.lineTo(19, 54); ctx.lineTo(19, 36); ctx.lineTo(13, 38); ctx.lineTo(10, 22); ctx.closePath(); }, 2.5);
      shape(ctx, P.d, () => { ctx.moveTo(24, 14); ctx.quadraticCurveTo(32, 8, 40, 14); ctx.quadraticCurveTo(32, 20, 24, 14); }, 1.5); // 帽口
      line(ctx, "#d0d4da", 1.6, [[32, 18], [32, 54]]);
      shape(ctx, P.d, () => ctx.roundRect(22, 40, 20, 8, 2), 1.2); // 口袋
      line(ctx, "#e6e6e0", 1.2, [[29, 18], [28, 26]]); line(ctx, "#e6e6e0", 1.2, [[35, 18], [36, 26]]);
      return [[25, 30], [39, 30]];
    },
    axe: (ctx, r, P) => { // 消防斧
      diag(ctx, () => {
        shape(ctx, "#c03030", () => ctx.roundRect(-2.5, -24, 5, 46, 2), 1.5);
        shape(ctx, "#2a2d33", () => ctx.roundRect(-3, 12, 6, 10, 2), 1.5);
        shape(ctx, "#c03030", () => { ctx.moveTo(2, -24); ctx.lineTo(16, -26); ctx.lineTo(17, -12); ctx.lineTo(2, -12); ctx.closePath(); });
        shape(ctx, "#c3ccd6", () => { ctx.moveTo(13, -26); ctx.lineTo(17, -26.5); ctx.lineTo(18, -11.5); ctx.lineTo(14, -12); ctx.closePath(); }, 1);
        shape(ctx, "#454c58", () => { ctx.moveTo(-2, -23); ctx.lineTo(-11, -16); ctx.lineTo(-2, -15); ctx.closePath(); }, 1.5); // 尖鎬
      });
      return [[40, 20], [24, 40]];
    },
  };
  const STYLES = { common: {}, eastern: EASTERN, magitech: MAGITECH, scifi: { ...SCIFI, ...SCIFI_GUNS }, modern: MODERN };

  // ---- 外框（稀有度）----
  function frame(ctx, rarity) {
    const [c] = RARITY[rarity];
    ctx.fillStyle = "#23262d"; ctx.beginPath(); ctx.roundRect(2, 2, 60, 60, 9); ctx.fill();
    if (rarity === "epic" || rarity === "legendary") { const g = ctx.createRadialGradient(32, 32, 4, 32, 32, 34); g.addColorStop(0, c + "66"); g.addColorStop(1, c + "00"); ctx.fillStyle = g; ctx.fill(); }
    ctx.lineWidth = rarity === "legendary" ? 3.5 : 2.5; ctx.strokeStyle = c; ctx.beginPath(); ctx.roundRect(2, 2, 60, 60, 9); ctx.stroke();
    if (rarity !== "common") { ctx.fillStyle = c; ctx.beginPath(); ctx.moveTo(50, 3.5); ctx.lineTo(60.5, 3.5); ctx.lineTo(60.5, 14); ctx.closePath(); ctx.fill(); }
    if (rarity === "legendary") { ctx.lineWidth = 1; ctx.globalAlpha = 0.6; ctx.beginPath(); ctx.roundRect(6, 6, 52, 52, 6); ctx.stroke(); ctx.globalAlpha = 1; }
  }

  /** small：顯示尺寸 ≤ 36px 時不畫關鍵字小圖樣（元素混色照留），避免糊成一團。 */
  function draw(ctx, item, small = false) {
    const r = resolve(item);
    const P = palette(r);
    frame(ctx, r.rarity);
    const fn = STYLES[r.style][r.kind] || D[r.kind];
    // 細長的造型放大一點，讓圖示填滿外框
    const k = { sword: 1.15, dagger: 1.5, axe: 1.0, hammer: 1.1, spear: 1.05, bow: 1.15, staff: 1.1, gun: 1.15, longgun: 1.0, shotgun: 1.0, crossbow: 1.15, scythe: 1.05, dual_dagger: 1.3 }[r.kind] ?? 1;
    ctx.save(); ctx.beginPath(); ctx.roundRect(3, 3, 58, 58, 8); ctx.clip(); ctx.translate(32, 33); ctx.scale(k, k); ctx.translate(-32, -33);
    const spots = fn(ctx, r, P);
    if (!small) {
      r.keywords.forEach((kw, i) => motif(ctx, kw, ...spots[i % spots.length]));
      if (r.keywords.length === 1) motif(ctx, r.keywords[0], ...spots[1]);
    }
    ctx.restore();
  }
  function icon(item, px = 64) {
    const cv = document.createElement("canvas");
    cv.width = px * 2; cv.height = px * 2; cv.style.width = `${px}px`; cv.style.height = `${px}px`;
    const ctx = cv.getContext("2d"); ctx.scale((px * 2) / 64, (px * 2) / 64); ctx.lineJoin = "round";
    draw(ctx, item, px <= 36);
    return cv;
  }
  function describe(item) {
    const r = resolve(item); const K = KINDS[r.kind];
    return { kind: K.zh, form: K.forms[r.form], material: MATERIAL[r.material].zh, dye: r.dye ? DYE_ZH[r.dye] : null, keywords: r.keywords.map((k) => KEYWORD[k].zh), rarity: RARITY[r.rarity][1], rarityColor: RARITY[r.rarity][0], slot: K.slot };
  }
  return { icon, draw, resolve, describe, dollItem, dollGear, KINDS, MATERIAL, DYE, DYE_ZH, KEYWORD, RARITY };
})();
