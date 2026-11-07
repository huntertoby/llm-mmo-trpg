// qPortrait.js：Q 版 NPC 頭像（畫圖 agent，2026-11-07；取代 C 墨線版 portraits.js 的畫法）。
// 做法：用 QNpc.stamp（＝QDoll 本體＋新部件，同一圈剪影外框）畫正面，取頭和肩膀放大裁進圓角框（QK移植需求.md 3 節 QK-2）。
// 頭像配件全部用 Q 語言重畫（純色塊、無內描線、方形眼的世界），而且畫在紙娃娃的體型座標裡（先套 build：stout 1.12×0.88、tall 0.96×1.1），
//   所以 tall、stout 的頭變形時配件跟著走：煤灰在右頰、裁在臉內；護目鏡在眼睛上；疤從眉骨到臉頰。
//   會伸出頭外的配件（斗笠、頭帶、羽冠、珊瑚、頭環、耳環、毛領）和本體一起描外框；臉上的（疤、皺紋、煤灰、義眼、符文、霧）不描外框。
// 名單：content 的 portrait 欄位原樣（world/npcs、mercenaries、trade 郵差、主城與室內的 figure.portrait），共 37 位（霜音是狐臉，不是紙娃娃）。
window.QPortrait = (() => {
  const TAU = Math.PI * 2, QN = () => window.QNpc;
  // 框色：區域色（RT-1）。傭兵用出身區（mercenaries.yaml origin），郵差用所在城鎮。
  const REGION = { cloud_ridge: ["#6aa84a", "#2f4a3a", "#8ab890"], ashen_waste: ["#ff6a1a", "#3a2418", "#b07050"], capital: ["#d9b24a", "#2a2a44", "#7a7aa8"], crystal_crown: ["#8ab0ff", "#26304a", "#9aaad8"], arcane_hub: ["#4ad0c8", "#1e3236", "#6aa0a0"], frost_tide: ["#7ad8ff", "#1e3448", "#7aa8c8"] };
  // [id, 名字, 身分, 群組, 框色區, look, gear, extras, 補充（held＝content 的 figure.held）]
  const N = [
    // 雲嶺（content/world/npcs/cloud_ridge.yaml）
    ["granny_du", "渡婆婆", "鎮長", "cloud_ridge", "cloud_ridge", { skin: "#e8c8a8", hair: "bun", hair_color: "#c8c8c0", bun_band: "#b8432f" }, { body: { kind: "robe", color: "#3c4a48", trim: "#e8bb48" } }, ["wrinkles"]],
    ["shopkeeper_liu", "柳掌櫃", "商人", "cloud_ridge", "cloud_ridge", { skin: "#f1c9a5", hair: "short", hair_color: "#2a1a10" }, { body: { kind: "robe", color: "#8a6a3a", trim: "#e8bb48" } }, ["cap", "mustache"]],
    ["daoist_qingya", "青崖道長", "技能導師", "cloud_ridge", "cloud_ridge", { skin: "#f1c9a5", hair: "bun", hair_color: "#e8e8e0", bun_band: "#2f5a5a", beard: true }, { body: { kind: "robe", color: "#2f5a5a", trim: "#e8e8e0" } }, []],
    ["hunter_ayue", "阿岳", "獵戶", "cloud_ridge", "cloud_ridge", { skin: "#d9a47a", hair: "short", hair_color: "#3a2414" }, { body: { kind: "leather", color: "#6a5040" } }, ["fur_collar"]],
    ["acolyte_xiaolian", "小蓮", "道童", "cloud_ridge", "cloud_ridge", { skin: "#f6e0cc", hair: "bun", hair_color: "#1a1a1a", bun_band: "#e86a8a" }, { body: { kind: "robe", color: "#e8ecea", trim: "#6aa84a" } }, [], { sample: "★樣張示範：月白道袍＋粉髮帶（content 是淺綠袍、綠髮帶，28px 和回春分不開）" }],
    ["mistlock_master", "霧鎖真人", "青霧觀觀主", "cloud_ridge", "cloud_ridge", { skin: "#e8d8c8", hair: "long", hair_color: "#9aa8b0" }, { body: { kind: "robe", color: "#e8e8e0", trim: "#3a5a5a" }, head: { kind: "veil", color: "#dfe4e2" } }, ["mist"]],
    ["scarface", "疤面", "斷崖幫二當家", "cloud_ridge", "cloud_ridge", { skin: "#a8724c", hair: "short", hair_color: "#1a1a1a" }, { body: { kind: "leather", color: "#7a6a4a" } }, ["wide_hat", "scar"]],
    ["frost_chime", "霜音", "白狐", "cloud_ridge", "cloud_ridge", null, null, ["fox"]],
    ["smith_shi", "石師傅", "鐵匠", "cloud_ridge", "cloud_ridge", { skin: "#d9a47a", hair: "short", hair_color: "#6a5440", beard: true, build: "stout" }, { body: { kind: "leather", color: "#5a4030" } }, ["headband"]],
    ["gran", "葛蘭", "導師堂駐堂導師", "cloud_ridge", "cloud_ridge", { skin: "#e8c8a8", hair: "short", hair_color: "#d8d4c8", beard: true }, { body: { kind: "coat", material: "cloth", color: "#4a4680", trim: "#d9b24a" }, hands: { kind: "bracers", material: "steel" } }, ["scar"]],
    // 灰燼荒原（content/world/npcs/ashen_waste.yaml）
    ["iron_lady", "鐵娘", "主事、商人", "ashen_waste", "ashen_waste", { skin: "#c8906a", hair: "long", hair_color: "#6a2a1a" }, { body: { kind: "leather", color: "#4a3a30" } }, ["bandana", "earring"]],
    ["greybeard", "灰鬚", "技能導師", "ashen_waste", "ashen_waste", { skin: "#d9a47a", hair: "short", hair_color: "#8a8a88", beard: true }, { body: { kind: "robe", color: "#6a5e54", trim: "#ff6a1a" }, head: { kind: "hood", color: "#5a4e44" } }, []],
    ["smith_lu", "爐叔", "鐵匠", "ashen_waste", "ashen_waste", { skin: "#a8724c", hair: "none", hair_color: "#3a2a1a", beard: true, build: "stout" }, { body: { kind: "bare" } }, ["goggles_up", "soot"]],
    ["scavenger_laotie", "老鐵", "拾荒者", "ashen_waste", "ashen_waste", { skin: "#c89a7a", hair: "short", hair_color: "#6a6a68" }, { body: { kind: "shirt", color: "#6a5e4a" } }, ["cap", "goggles"]],
    ["priestess_helin", "赫琳", "角魔祭司", "ashen_waste", "ashen_waste", { skin: "#b07a7a", hair: "long", hair_color: "#1e1418", horns: "curved", horn_color: "#bfb0a4" }, { body: { kind: "robe", color: "#4a1a2a", trim: "#c83a2a" } }, ["rune"]],
    ["overseer_scar", "鍛疤", "熔爐督工", "ashen_waste", "ashen_waste", { skin: "#8a5a3a", hair: "none", hair_color: "#1a1a1a", build: "stout" }, { body: { kind: "plate" } }, ["scar", "ember_eye"]],
    // 系統傭兵（content/world/mercenaries.yaml；框色＝出身區）
    ["merc_qingfeng", "青鋒", "近戰劍客", "merc", "cloud_ridge", { skin: "#f1c9a5", hair: "long", hair_color: "#1a1a1a" }, { body: { kind: "leather", color: "#2f5a5a" } }, ["headband"]],
    ["merc_chuanyun", "珊瑚", "弓手", "merc", "frost_tide", { skin: "#b07a52", hair: "long", hair_color: "#1e6a7a", pattern: "marks", mark_color: "#3aa8e0" }, { body: { kind: "leather", color: "#c8b08a" } }, ["coral", "earring"]],
    ["merc_chiyan", "灰燼瑪菈", "火術士", "merc", "ashen_waste", { skin: "#b07a7a", hair: "long", hair_color: "#2a1418", horns: "curved", horn_color: "#3a2a2a" }, { body: { kind: "robe", color: "#3a2420", trim: "#ff6a1a" } }, ["ember_eye", "rune"]],
    ["merc_tiebi", "賽倫", "盾衛", "merc", "crystal_crown", { skin: "#f1c9a5", hair: "short", hair_color: "#c8a868" }, { body: { kind: "plate", color: "#d8dde6", trim: "#8ab0ff" }, head: { kind: "helmet", material: "steel" } }, ["crest"]],
    ["merc_panshi", "鉚釘", "守護者", "merc", "arcane_hub", { skin: "#e8b890", hair: "short", hair_color: "#6a3a1a", beard: true, build: "stout" }, { body: { kind: "mail", color: "#b08a4a" } }, ["goggles", "soot"]],
    ["merc_huichun", "回春", "醫者", "merc", "cloud_ridge", { skin: "#f6e0cc", hair: "bun", hair_color: "#3a2414", bun_band: "#6aa84a" }, { body: { kind: "robe", color: "#6aa84a", trim: "#f2e6c8" } }, ["apron_cross"]],
    ["merc_qingyin", "莉瑟", "祝禱師", "merc", "crystal_crown", { skin: "#f6e0cc", hair: "long", hair_color: "#e8e0c8", ears: "pointed", build: "tall" }, { body: { kind: "robe", color: "#f2ece0", trim: "#8ab0ff" } }, ["circlet"]],
    ["merc_jinglei", "七號線圈", "雷水術士", "merc", "arcane_hub", { skin: "#e6c4a4", hair: "short", hair_color: "#4ad0c8", pattern: "circuit" }, { body: { kind: "leather", color: "#4a5058" } }, ["cyber_eye"]],
    ["merc_fuying", "鏽牙", "陷阱師", "merc", "ashen_waste", { skin: "#86a060", hair: "short", hair_color: "#1e1a14", tusks: true, build: "tall" }, { body: { kind: "leather", color: "#6a4a3a" } }, ["bandana", "scar", "earring"]],
    // 郵差（content/world/trade.yaml；郵寄外觀.md：郵袋 mailbag 是郵差專用配件）
    ["postman_bailu", "白鷺", "樞島的郵差", "postman", "capital", { skin: "#f6e0cc", hair: "long", hair_color: "#e8e0c8", ears: "pointed", build: "tall" }, { body: { kind: "coat", material: "cloth", color: "#5a4e8a", trim: "#d9b24a" }, head: { kind: "cap", material: "leather" } }, ["post_badge", "mailbag"]],
    ["postman_axin", "阿信", "霧渡鎮的郵差", "postman", "cloud_ridge", { skin: "#f1c9a5", hair: "short", hair_color: "#2a1a10" }, { body: { kind: "coat", material: "cloth", color: "#4a7a5a", trim: "#d9b24a" }, head: { kind: "cap", material: "leather" } }, ["post_badge", "mailbag"]],
    ["postman_huige", "灰鴿", "餘燼集的郵差", "postman", "ashen_waste", { skin: "#86a060", hair: "short", hair_color: "#1e1a14", tusks: true, build: "tall" }, { body: { kind: "coat", material: "cloth", color: "#a8582a", trim: "#d9b24a" }, head: { kind: "cap", material: "leather" } }, ["soot", "post_badge", "mailbag"]],
    // 主城樞島（content/world/fields/capital/ 的 figure.portrait）
    ["seal_keeper", "守印人", "封印、公告板", "capital", "capital", { skin: "#d9a47a", hair: "long", hair_color: "#d8d0c0", beard: true }, { body: { kind: "robe", color: "#3a3a6a", trim: "#e8bb48" }, head: { kind: "hood", color: "#2a2a4a" } }, [], { held: { kind: "staff", material: "crystal" } }],
    ["hire", "傭兵管事", "雇用傭兵", "capital", "capital", { skin: "#d9a47a", hair: "short", hair_color: "#8a8478", beard: true }, { body: { kind: "mail", color: "#7a7468" } }, ["scar", "wrinkles"]],
    ["pool_keeper", "守池人", "許願池", "capital", "capital", { skin: "#f1c9a5", hair: "bun", hair_color: "#c8d0d8", bun_band: "#4ad0c8" }, { body: { kind: "robe", color: "#2a5a7a", trim: "#cfe8f0" }, off_hand: { kind: "orb", material: "crystal" } }, ["earring", "wrinkles"]],
    ["workshop_master", "工坊師傅", "靶場、改造", "capital", "capital", { skin: "#d9a47a", hair: "short", hair_color: "#4a3a2a", beard: true, build: "stout" }, { body: { kind: "leather", color: "#5a4636" }, hands: { kind: "gloves", material: "leather" } }, ["goggles_up", "soot"], { held: { kind: "hammer", material: "iron" } }],
    ["mentor", "導師殿導師", "技能導師", "capital", "capital", { skin: "#f1c9a5", hair: "long", hair_color: "#e8e4ec", beard: true }, { body: { kind: "robe", color: "#e8e4f0", trim: "#8f7bff" }, head: { kind: "crown", color: "#c8bcff" } }, ["wrinkles"], { held: { kind: "staff", material: "crystal" } }],
    ["scribe", "書記", "導師殿書記", "capital", "capital", { skin: "#f1c9a5", hair: "short", hair_color: "#2a2a3a" }, { body: { kind: "robe", color: "#2e3a5a", trim: "#e8bb48" }, off_hand: { kind: "tome", material: "leather" } }, []],
    ["smithy", "樞島鐵匠", "鐵匠", "capital", "capital", { skin: "#c88a5a", hair: "short", hair_color: "#2a2420", beard: true, build: "stout" }, { body: { kind: "leather", color: "#4a3626" }, hands: { kind: "gloves", material: "leather" } }, ["soot"], { held: { kind: "hammer", material: "iron" } }],
    ["enchanter", "附魔師", "附魔", "capital", "capital", { skin: "#f1c9a5", hair: "long", hair_color: "#2a1a3a" }, { body: { kind: "robe", color: "#5a2a8a", trim: "#c8bcff" } }, ["earring"]],
    ["tavern", "酒館老闆", "酒館", "capital", "capital", { skin: "#e0b088", hair: "short", hair_color: "#6a4a2a", beard: true, build: "stout" }, { body: { kind: "shirt", color: "#e8dcc0" } }, ["mustache"]],
  ];
  // 全身樣張的補充（★＝content 沒有、為了「一眼看得出身分」建議補的；要不要寫進 content 由美術 PM 決定）
  const SUGGEST = {
    smith_shi: { parts: [{ k: "apron", color: "#2e1e14", edge: "#b07a48", pocket: false }], main_hand: { kind: "hammer", material: "iron" }, note: "★皮圍裙＋鎚" },
    smith_lu: { parts: [{ k: "apron", color: "#2e1e14", edge: "#b07a48", pocket: false }], main_hand: { kind: "hammer", material: "iron" }, note: "★皮圍裙＋鎚" },
    smithy: { parts: [{ k: "apron", color: "#2e1e14", edge: "#b07a48", pocket: false }], note: "★皮圍裙" },
    workshop_master: { parts: [{ k: "apron", color: "#2e1e14", edge: "#b07a48", pocket: false }], note: "★皮圍裙" },
    tavern: { parts: [{ k: "apron", color: "#f4efe2", edge: "#a89c80" }], note: "★白圍裙" },
    acolyte_xiaolian: { note: "★月白袍、粉髮帶（樣張示範：28px 和回春分開）" },
    hunter_ayue: { main_hand: { kind: "bow", material: "wood" }, note: "★弓（劇情夥伴＝弓手）" },
    shopkeeper_liu: { waist: { kind: "pouch", material: "leather" }, note: "★錢袋" },
    scavenger_laotie: { back: { kind: "backpack", material: "leather" }, note: "★背包" },
    iron_lady: { waist: { kind: "pouch", material: "leather" }, note: "★錢袋" },
    priestess_helin: { main_hand: { kind: "staff", material: "wood", element: "fire" }, note: "★杖" },
    greybeard: { main_hand: { kind: "staff", material: "wood" }, note: "★杖" },
    daoist_qingya: { main_hand: { kind: "whisk" }, note: "★拂塵" },
    mistlock_master: { main_hand: { kind: "sword", material: "steel" }, off_hand: { kind: "whisk" }, note: "★劍＋拂塵（同頭目）" },
    scarface: { main_hand: { kind: "saber", material: "steel" }, note: "★刀" },
        overseer_scar: { main_hand: { kind: "hammer", material: "iron" }, note: "★鎚" },
    // 傭兵：照 build 的武器（content/sim/builds.yaml）
    merc_qingfeng: { main_hand: { kind: "sword", material: "steel" } }, merc_chuanyun: { main_hand: { kind: "bow", material: "wood" } },
    merc_chiyan: { main_hand: { kind: "staff", material: "wood", element: "fire" } }, merc_tiebi: { main_hand: { kind: "sword", material: "steel" }, off_hand: { kind: "shield_kite", material: "steel" } },
    merc_panshi: { main_hand: { kind: "sword", material: "steel" }, off_hand: { kind: "shield_round", material: "iron" } }, merc_huichun: { main_hand: { kind: "staff", material: "wood", element: "ice" } },
    merc_qingyin: { main_hand: { kind: "staff", material: "crystal", element: "ice" } }, merc_jinglei: { main_hand: { kind: "staff", material: "crystal", element: "lightning" } },
    merc_fuying: { main_hand: { kind: "staff", material: "wood", element: "fire" } },
  };
  /** 全身用的 unit（含補充）。 */
  function bodyUnit(n, withSuggest = true) {
    const [id, , , , , look, gear, extras, more] = n, s = withSuggest ? SUGGEST[id] ?? {} : {};
    const g = { ...gear };
    if (more?.held) g.main_hand = more.held;
    for (const k of ["main_hand", "off_hand", "waist", "back"]) if (s[k] && !g[k]) g[k] = s[k];
    if (s.dropOff) delete g.off_hand;
    const parts = [...(s.parts ?? [])];
    if (extras.includes("mailbag")) parts.push({ k: "mailbag" });
    return { look, gear: g, extras, parts };
  }

  // ---------- 頭像配件（Q 語言：純色塊、圓角、無內描線；紙娃娃座標，頭心 (0,−29)、半徑 8.5） ----------
  function fill(ctx, c, path) { ctx.fillStyle = c; ctx.beginPath(); path(); ctx.fill(); }
  function line(ctx, c, w, pts) { ctx.strokeStyle = c; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke(); }
  const face = (ctx) => { ctx.beginPath(); ctx.arc(0, -29, 8.4, 0, TAU); ctx.clip(); }; // 裁在臉內
  // C 層（和本體一起描外框）：會伸出頭外的
  const EXC = {
    earring: (ctx) => { fill(ctx, "#e8bb48", () => ctx.arc(-8.9, -24.6, 1.05, 0, TAU)); }, // 左耳垂（畫面左＝角色右耳）
    coral: (ctx) => { for (const [x, y, r, c] of [[-6.4, -37, 1.5, "#e8806e"], [-4, -38.4, 1.3, "#f2a090"], [-1.8, -37.8, 1.1, "#e8806e"]]) fill(ctx, c, () => ctx.arc(x, y, r, 0, TAU)); fill(ctx, "#e8806e", () => ctx.roundRect(-6.8, -37.6, 5.4, 1.4, 0.6)); },
    crest: (ctx) => { fill(ctx, "#5a7ad0", () => { ctx.moveTo(-1.4, -38.6); ctx.quadraticCurveTo(-2.2, -45, 2.6, -47); ctx.quadraticCurveTo(1, -43, 1.6, -38.6); ctx.closePath(); }); fill(ctx, "#8ab0ff", () => ctx.roundRect(-1.6, -40, 3.2, 1.6, 0.6)); }, // 盔頂羽冠
    circlet: (ctx) => { fill(ctx, "#e8bb48", () => { ctx.moveTo(-8.9, -33.4); ctx.quadraticCurveTo(0, -36.6, 8.9, -33.4); ctx.lineTo(8.8, -32.2); ctx.quadraticCurveTo(0, -35.2, -8.8, -32.2); ctx.closePath(); }); fill(ctx, "#a898ff", () => { ctx.moveTo(0, -37.6); ctx.lineTo(1.7, -35.2); ctx.lineTo(0, -32.8); ctx.lineTo(-1.7, -35.2); ctx.closePath(); }); fill(ctx, "rgba(255,255,255,0.6)", () => ctx.arc(-0.5, -35.8, 0.5, 0, TAU)); },
    // 護目鏡戴在眼睛上（沒戴帽子時 QNpc.prep 已換成 qDoll 的 head goggles；戴帽子時在這裡補畫，同一個造型）
    goggles: (ctx, q) => { if (q.gear.head?.kind === "goggles") return; line(ctx, "#3a3a44", 1.3, [[-8.8, -29.6], [8.8, -29.6]]); for (const x of [-3, 3]) { fill(ctx, "#8d969f", () => ctx.ellipse(x, -29.5, 3, 2.6, 0, 0, TAU)); fill(ctx, "rgba(160,220,255,0.75)", () => ctx.ellipse(x, -29.5, 2.2, 1.9, 0, 0, TAU)); } },
    post_badge: (ctx) => { fill(ctx, "#d9b24a", () => ctx.roundRect(-2, -35.4, 4, 2.6, 0.6)); fill(ctx, "#f4efe2", () => ctx.roundRect(-1.3, -34.9, 2.6, 1.6, 0.3)); line(ctx, "#a8582a", 0.35, [[-1.3, -34.9], [0, -34], [1.3, -34.9]]); }, // 郵差帽：帽前的信封徽章
  };
  // 裁在臉的皮膚區域（頭圓扣掉頭髮、帽、頭巾、鏡片、鬍子；QNpc.stamp 的 extraSkin）
  const SKIN = new Set(["scar", "wrinkles", "soot"]);
  // D 層（不描外框）：臉上的
  const EXD = {
    scar: (ctx) => { line(ctx, "#8a3a2a", 0.9, [[-5.6, -33.2], [-3.4, -29.6], [-2.2, -25.4]]); for (const [x, y] of [[-4.9, -31.8], [-3.2, -28.2]]) line(ctx, "#8a3a2a", 0.55, [[x - 1, y + 0.4], [x + 1, y - 0.4]]); },
    wrinkles: (ctx) => { for (const s of [-1, 1]) line(ctx, "rgba(120,80,60,0.75)", 0.45, [[s * 6.2, -27.6], [s * 6.9, -26.4]]); line(ctx, "rgba(120,80,60,0.6)", 0.45, [[-2.4, -33.4], [2.4, -33.4]]); },
    soot: (ctx, look) => { fill(ctx, "rgba(40,30,25,0.45)", () => ctx.ellipse(5.4, -25.4, 2.3, 1.2, 0.2, 0, TAU)); if (look?.beard) fill(ctx, "rgba(40,30,25,0.45)", () => ctx.ellipse(6, -26.9, 2, 0.9, 0.2, 0, TAU)); }, // 右頰（畫面右）一抹；有大鬍子時頰被鬍子蓋住，往上移到鏡框和鬍子之間露出的那條皮膚
    ember_eye: (ctx) => { ctx.save(); ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 5; fill(ctx, "#ffb030", () => ctx.rect(1.9, -30.2, 2, 3.4)); ctx.restore(); }, // 右眼（畫面右）換成餘燼色的方眼
    cyber_eye: (ctx) => { fill(ctx, "#4a5058", () => ctx.roundRect(0.6, -31.4, 4.6, 5.2, 1.2)); ctx.save(); ctx.shadowColor = "#4ad0c8"; ctx.shadowBlur = 5; fill(ctx, "#7af0e8", () => ctx.rect(2.1, -30, 1.8, 2.4)); ctx.restore(); line(ctx, "#4ad0c8", 0.5, [[5.2, -29], [7.4, -29], [7.4, -26]]); }, // 義眼：方眼外一圈金屬框＋一條電路
    rune: (ctx) => { ctx.save(); ctx.shadowColor = "#ff3a2a"; ctx.shadowBlur = 3; fill(ctx, "#e84a2a", () => { ctx.moveTo(0, -35.6); ctx.lineTo(1.2, -33.6); ctx.lineTo(0, -32.2); ctx.lineTo(-1.2, -33.6); ctx.closePath(); }); ctx.restore(); }, // 額上一顆菱形符文
    mist: (ctx) => { const g = ctx.createRadialGradient(0, -24, 2, 0, -24, 20); g.addColorStop(0, "rgba(236,238,232,0.0)"); g.addColorStop(0.55, "rgba(236,238,232,0.35)"); g.addColorStop(1, "rgba(236,238,232,0)"); ctx.fillStyle = g; ctx.fillRect(-24, -48, 48, 44); },
    apron_cross: (ctx) => { fill(ctx, "#f4efe2", () => ctx.roundRect(-2.6, -18.6, 5.2, 5.2, 1)); fill(ctx, "#c83a2a", () => ctx.rect(-0.7, -17.8, 1.4, 3.6)); fill(ctx, "#c83a2a", () => ctx.rect(-1.8, -16.7, 3.6, 1.4)); }, // 胸前白底紅十字
  };
  // 好感五級表情（21.5）：0 敵意、1 冷淡、2 普通、3 友善、4 信賴。頭像上：眼睛、眉、嘴換掉；頭頂徽章另畫（mood）
  const MOOD = ["#c83a2a", "#8a8aa8", "#e8e0d0", "#ffd23a", "#ff8ab0"];
  // cover：哪些被配件遮住（eyes 兩眼、eyeR 畫面右那隻眼、mouth 嘴與腮紅）；被遮住的不換，配件畫在表情上面
  function covers(extras, gear) {
    const c = { eyes: extras.includes("goggles") || gear?.head?.kind === "goggles", eyeR: extras.includes("cyber_eye") || extras.includes("ember_eye"), mouth: gear?.head?.kind === "veil" };
    return c;
  }
  function expr(ctx, level, look, cv = {}) {
    if (level == null || level === 2) return;
    const ink = "#1d1a22", sk = look.skin, xs = cv.eyes ? [] : cv.eyeR ? [-2.9] : [-2.9, 2.9];
    const brow = (s, y0, y1) => line(ctx, ink, 0.9, [[s * 4.6, cv.eyes ? y0 - 1.4 : y0], [s * 1.6, cv.eyes ? y1 - 1.4 : y1]]);
    if (level === 0) { for (const s of [-1, 1]) brow(s, -32.6, -31.2); if (!cv.mouth) line(ctx, ink, 0.7, [[-1.4, -23.4], [0, -24.2], [1.4, -23.4]]); }
    if (level === 1) { for (const x of xs) { fill(ctx, sk, () => ctx.rect(x - 1.1, -30.4, 2.2, 1.6)); line(ctx, ink, 0.6, [[x - 1.2, -28.8], [x + 1.2, -28.8]]); } if (cv.eyes) for (const s of [-1, 1]) line(ctx, ink, 0.7, [[s * 4.4, -33.4], [s * 1.8, -33.4]]); if (!cv.mouth) line(ctx, ink, 0.6, [[-1.2, -23.8], [1.2, -23.8]]); }
    if (level >= 3) { for (const x of xs) { fill(ctx, sk, () => ctx.rect(x - 1.2, -30.4, 2.4, 3.8)); line(ctx, ink, 0.95, [[x - 1.3, -28.2], [x, -29.6], [x + 1.3, -28.2]]); } if (cv.eyes) for (const s of [-1, 1]) line(ctx, ink, 0.7, [[s * 4.4, -33], [s * 3, -33.8], [s * 1.6, -33]]); if (!cv.mouth) fill(ctx, "#8a3a3a", () => { ctx.moveTo(-1.6, -24.4); ctx.quadraticCurveTo(0, -22.2, 1.6, -24.4); ctx.closePath(); }); }
    if (level === 4 && !cv.mouth) { ctx.fillStyle = "rgba(240,90,110,0.5)"; for (const s of [-1, 1]) ctx.fillRect(s * 4.5 - 1.5, -26.8, 3, 1.6); }
  }
  /** 頭頂的好感徽章（Q 版：圓臉、方眼、腮紅；r＝半徑 px）。 */
  function mood(ctx, x, y, r, level) {
    ctx.save(); ctx.translate(x, y);
    ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fillStyle = MOOD[level]; ctx.fill(); ctx.lineWidth = Math.max(1.2, r * 0.16); ctx.strokeStyle = "#16121a"; ctx.stroke();
    const e = r * 0.36, ew = r * 0.17, eh = r * 0.32, ink = "#16121a";
    ctx.fillStyle = ink; ctx.strokeStyle = ink; ctx.lineCap = "round"; ctx.lineWidth = r * 0.13;
    if (level === 3 || level === 4) for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * e - ew * 1.3, -r * 0.08); ctx.lineTo(s * e, -r * 0.3); ctx.lineTo(s * e + ew * 1.3, -r * 0.08); ctx.stroke(); }
    else if (level === 1) for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * e - ew * 1.2, -r * 0.12); ctx.lineTo(s * e + ew * 1.2, -r * 0.12); ctx.stroke(); }
    else for (const s of [-1, 1]) ctx.fillRect(s * e - ew / 2, -r * 0.34, ew, eh);
    if (level === 0) for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * r * 0.62, -r * 0.56); ctx.lineTo(s * r * 0.16, -r * 0.4); ctx.stroke(); }
    ctx.fillStyle = "rgba(220,90,90,0.45)"; if (level >= 2) for (const s of [-1, 1]) ctx.fillRect(s * r * 0.58 - r * 0.15, r * 0.12, r * 0.3, r * 0.14);
    ctx.beginPath();
    if (level === 0) ctx.arc(0, r * 0.62, r * 0.28, Math.PI * 1.15, Math.PI * 1.85);
    else if (level === 1) { ctx.moveTo(-r * 0.22, r * 0.4); ctx.lineTo(r * 0.22, r * 0.4); }
    else if (level === 2) ctx.arc(0, r * 0.18, r * 0.22, Math.PI * 0.2, Math.PI * 0.8);
    else { ctx.moveTo(-r * 0.3, r * 0.2); ctx.quadraticCurveTo(0, r * 0.66, r * 0.3, r * 0.2); ctx.closePath(); ctx.fillStyle = "#8a3a3a"; ctx.fill(); }
    ctx.stroke();
    if (level === 4) { ctx.fillStyle = "#e83a5a"; ctx.lineWidth = r * 0.1; ctx.beginPath(); const hx = r * 0.86, hy = -r * 0.82, s = r * 0.42; ctx.moveTo(hx, hy + s * 0.9); ctx.bezierCurveTo(hx - s * 1.2, hy, hx - s * 0.6, hy - s * 0.8, hx, hy - s * 0.2); ctx.bezierCurveTo(hx + s * 0.6, hy - s * 0.8, hx + s * 1.2, hy, hx, hy + s * 0.9); ctx.fill(); ctx.stroke(); }
    ctx.restore();
  }
  // 霜音（白狐）：不是紙娃娃。用同一套 Q 語言畫狐臉：圓頭、三角耳、方眼（冰藍）、腮紅、額上冰紋，一樣描剪影外框
  function foxFill(ctx) {
    const W = "#f6f2ea", P = "#f0b0b0";
    fill(ctx, W, () => { ctx.ellipse(0, -14, 9, 8, 0, 0, TAU); }); // 胸前蓬毛
    for (const s of [-1, 1]) { fill(ctx, W, () => { ctx.moveTo(s * 3, -36); ctx.lineTo(s * 9.6, -44.6); ctx.lineTo(s * 9.2, -31); ctx.closePath(); }); fill(ctx, P, () => { ctx.moveTo(s * 4.6, -36); ctx.lineTo(s * 8.8, -41.8); ctx.lineTo(s * 8.4, -33.4); ctx.closePath(); }); }
    fill(ctx, W, () => ctx.arc(0, -29, 8.8, 0, TAU));
    for (const s of [-1, 1]) fill(ctx, W, () => { ctx.moveTo(s * 7.6, -27); ctx.lineTo(s * 11.4, -23.4); ctx.lineTo(s * 6.6, -22.6); ctx.closePath(); }); // 頰毛
    fill(ctx, "#ffffff", () => ctx.ellipse(0, -24.4, 4.2, 3, 0, 0, TAU)); // 吻部
    for (const s of [-1, 1]) { fill(ctx, "#3aa8e0", () => ctx.rect(s * 3.2 - 1, -30.6, 2, 3.2)); fill(ctx, "#ffffff", () => ctx.rect(s * 3.2 - 0.6, -30.2, 0.7, 0.8)); }
    ctx.fillStyle = "rgba(220,90,90,0.35)"; ctx.fillRect(-7.2, -26.4, 2, 1.2); ctx.fillRect(5.2, -26.4, 2, 1.2);
    fill(ctx, "#2a2430", () => ctx.ellipse(0, -25.4, 1.2, 0.9, 0, 0, TAU));
    fill(ctx, "#7ad8ff", () => { ctx.moveTo(0, -36.8); ctx.lineTo(1.3, -34.4); ctx.lineTo(0, -33); ctx.lineTo(-1.3, -34.4); ctx.closePath(); });
    for (const s of [-1, 1]) line(ctx, "#7ad8ff", 0.5, [[s * 1.6, -35.4], [s * 3.2, -36.6]]);
  }

  // ---------- 一張頭像 ----------
  // 頭心放在框的 (0.5, 0.47)；1 個紙娃娃單位＝size/38 px。體型 build 的縮放先套在紙娃娃座標裡，配件跟著走。
  const cache = new Map();
  function render(n, level, px) {
    const key = `${n[0]}|${level}|${px}`; if (cache.has(key)) return cache.get(key);
    const c = document.createElement("canvas"); c.width = c.height = px; const ctx = c.getContext("2d");
    const [, , , , region, look, gear, extras] = n, [frame, bgD, bgL] = REGION[region];
    const g = ctx.createLinearGradient(0, 0, 0, px); g.addColorStop(0, bgL); g.addColorStop(1, bgD); ctx.fillStyle = g; ctx.fillRect(0, 0, px, px);
    const k = px / 42, cyF = 0.53; /* 審查：角、羽冠、耳尖、斗笠不出框 → 縮一點、往下移 */
    if (extras.includes("fox")) {
      const off = document.createElement("canvas"); off.width = off.height = px; const o = off.getContext("2d"); o.translate(px / 2, px * cyF + 29 * k); o.scale(k, k); foxFill(o);
      QN().outlineOnto(ctx, off, 1.3 * k, 0, 0, px, px);
      const fr = ctx.createRadialGradient(px / 2, px * cyF, px * 0.2, px / 2, px * cyF, px * 0.7); fr.addColorStop(0, "rgba(200,240,255,0)"); fr.addColorStop(1, "rgba(200,240,255,0.32)"); ctx.fillStyle = fr; ctx.fillRect(0, 0, px, px);
    } else {
      const L = QN().normLook(look), by = QN().BUILD[L.build]?.[1] ?? 1, hy = -29 * by;
      const lk = level === 3 || level === 4 ? { ...look } : look;
      const unit = { look: lk, gear, extras: extras.filter((e) => e !== "mailbag"), parts: extras.includes("mailbag") ? [{ k: "mailbag" }] : [] }, cv = covers(extras, gear);
      QN().stamp(ctx, unit, "front", px / 2, px * cyF - hy * k, k, false, {
        portrait: true,
        extraSkin: (c, v, q) => { for (const e of extras) if (SKIN.has(e)) EXD[e]?.(c, q.look); },
        dpr: 1,
        extraC: (c, v, q) => { for (const e of extras) EXC[e]?.(c, q); },
        extraD: (c, v, q) => { expr(c, level, q.look, cv); for (const e of extras) if (!SKIN.has(e)) EXD[e]?.(c, q.look); }, /* 表情先畫，義眼、餘燼眼等配件蓋在上面 */
      });
    }
    // 外框：區域色＋墨線
    const out = document.createElement("canvas"); out.width = out.height = px; const oc = out.getContext("2d");
    oc.beginPath(); oc.roundRect(0, 0, px, px, px * 0.14); oc.save(); oc.clip(); oc.drawImage(c, 0, 0); oc.restore();
    oc.lineWidth = Math.max(2, px * 0.04); oc.strokeStyle = frame; oc.beginPath(); oc.roundRect(oc.lineWidth / 2, oc.lineWidth / 2, px - oc.lineWidth, px - oc.lineWidth, px * 0.13); oc.stroke();
    oc.lineWidth = 1; oc.strokeStyle = "#1c1712"; oc.beginPath(); oc.roundRect(0.5, 0.5, px - 1, px - 1, px * 0.14); oc.stroke();
    cache.set(key, out); return out;
  }
  /** 畫一張頭像到 ctx：size＝邊長 px；level＝好感（null＝普通）。大的先畫好、小的從 192 縮下來（和遊戲裡的快取一樣）。 */
  function portrait(ctx, x, y, size, n, level = null) {
    const base = size > 96 ? size : 192, img = render(n, level, base);
    ctx.save(); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high"; ctx.drawImage(img, x, y, size, size); ctx.restore();
  }
  const EXTRAS_ALL = ["wrinkles", "cap", "mustache", "fur_collar", "mist", "wide_hat（斗笠）", "scar", "fox", "headband", "bandana", "earring", "goggles_up", "soot", "goggles", "rune", "ember_eye", "coral", "crest", "apron_cross", "circlet", "cyber_eye", "post_badge（郵差帽徽）", "mailbag"];
  return { N, SUGGEST, REGION, bodyUnit, portrait, mood, EXC, EXD, EXTRAS_ALL };
})();
