// 背包與商店的物品圖示（美術 PM，2026-11-04）：裝備圖示（gearIcon／weaponIcon）沒涵蓋的類別——藥水、投擲瓶、補給、材料、染料、貨幣、任務物品。
// C 手繪墨線畫法（storyDoll.js 的畫法層 H）；每個圖示畫在 48×48 的框裡，底色依類別、外框依品質。ID 照 content/world/items.yaml。全部程式繪製。
window.ItemIcons = (() => {
  const { ink, stroke, ellPts, INK } = StoryDoll.H, TAU = Math.PI * 2;
  const CAT = { consumable: ["#2a3a30", "#6aa84a"], throwable: ["#2a3040", "#5ab0f0"], supply: ["#3a3020", "#c8a868"], material: ["#2e2a26", "#9a8e7c"], dye: ["#30283a", "#c8a0d8"], currency: ["#3a3218", "#e8bb48"], quest: ["#3a2418", "#ff8a50"] };
  const TIER = { 1: "#9a9a9a", 2: "#5a9ae0", 3: "#a870e0" };
  function glow(ctx, x, y, r, c, a) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, c); g.addColorStop(1, c.replace(/[\d.]+\)$/, "0)")); ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); ctx.restore(); }
  // ---------- 零件 ----------
  function flask(ctx, key, liquid, round = true, big = false) { // 藥瓶：圓肚或細長，瓶塞，液面反光
    const s = big ? 1.15 : 1;
    if (round) ink(ctx, `${key}-glass`, ellPts(24, 30, 13 * s, 12 * s, 18), "rgba(220,235,240,0.55)", { shade: false, w: 0.9 });
    else ink(ctx, `${key}-glass`, [[17, 16], [31, 16], [33, 40], [15, 40]], "rgba(220,235,240,0.55)", { shade: false, w: 0.9 });
    ctx.save(); if (round) { ctx.beginPath(); ctx.ellipse(24, 30, 12 * s, 11 * s, 0, 0, TAU); } else { ctx.beginPath(); ctx.rect(16, 16, 16, 24); } ctx.clip(); ctx.fillStyle = liquid; ctx.fillRect(0, round ? 28 : 24, 48, 30); ctx.fillStyle = "rgba(255,255,255,0.35)"; ctx.fillRect(0, round ? 28 : 24, 48, 2); ctx.restore();
    ink(ctx, `${key}-neck`, [[20, 10], [28, 10], [28, 18], [20, 18]], "rgba(220,235,240,0.6)", { shade: false, w: 0.7 });
    ink(ctx, `${key}-cork`, [[19, 5], [29, 5], [28, 11], [20, 11]], "#a06a36", { shade: false, w: 0.7 });
    ctx.fillStyle = "rgba(255,255,255,0.6)"; ctx.beginPath(); ctx.ellipse(18, 26, 2, 4, 0.3, 0, TAU); ctx.fill();
  }
  function ore(ctx, key, col) { ink(ctx, key, [[10, 34], [14, 20], [24, 13], [36, 18], [39, 32], [30, 40], [16, 40]], col, { w: 0.9 }); stroke(ctx, `${key}-f`, [[14, 20], [24, 28], [36, 18]], 0.7, "rgba(0,0,0,0.4)"); stroke(ctx, `${key}-f2`, [[24, 28], [30, 40]], 0.7, "rgba(0,0,0,0.4)"); }
  function crystal(ctx, key, col, glowCol) { if (glowCol) glow(ctx, 24, 26, 20, glowCol, 0.6); for (const [dx, h, w, r] of [[-7, 22, 6, -0.3], [0, 30, 7, 0], [8, 20, 6, 0.35]]) { ctx.save(); ctx.translate(24 + dx, 40); ctx.rotate(r); ink(ctx, `${key}${dx}`, [[-w, 0], [-w * 0.8, -h * 0.7], [0, -h], [w * 0.8, -h * 0.7], [w, 0]], col, { w: 0.8, sharp: true }); ctx.restore(); } }
  function feather(ctx, key, col, tip) { ctx.save(); ctx.translate(24, 26); ctx.rotate(-0.6); ink(ctx, key, [[0, -20], [7, -10], [6, 8], [0, 18], [-6, 8], [-7, -10]], col, { w: 0.8 }); stroke(ctx, `${key}-q`, [[0, -18], [0, 22]], 0.8, INK); ctx.fillStyle = tip; ctx.beginPath(); ctx.ellipse(0, -14, 4, 6, 0, 0, TAU); ctx.fill(); ctx.restore(); }
  function jar(ctx, key, col) { ink(ctx, `${key}-jar`, [[14, 18], [34, 18], [36, 38], [12, 38]], "#e8dcc0", { w: 0.8 }); ink(ctx, `${key}-lid`, [[12, 12], [36, 12], [36, 18], [12, 18]], "#8a6440", { shade: false, w: 0.7 }); ctx.fillStyle = col; ctx.beginPath(); ctx.ellipse(24, 27, 8, 6, 0, 0, TAU); ctx.fill(); ctx.lineWidth = 0.8; ctx.strokeStyle = INK; ctx.stroke(); }
  function elementMark(ctx, el) { ctx.save(); ctx.translate(36, 36); ctx.fillStyle = "rgba(24,20,16,0.85)"; ctx.beginPath(); ctx.arc(0, 0, 7, 0, TAU); ctx.fill(); ctx.lineWidth = 1.2; ctx.strokeStyle = "#f2e6c8"; ctx.beginPath();
    if (el === "fire") { ctx.fillStyle = "#ff7a2a"; ctx.moveTo(0, -5); ctx.quadraticCurveTo(5, 0, 0, 5); ctx.quadraticCurveTo(-5, 0, 0, -5); ctx.fill(); }
    else if (el === "water") { ctx.fillStyle = "#5ab0f0"; ctx.moveTo(0, -5); ctx.quadraticCurveTo(5, 2, 0, 5); ctx.quadraticCurveTo(-5, 2, 0, -5); ctx.fill(); }
    else if (el === "ice") { for (let k = 0; k < 3; k++) { const a = k * Math.PI / 3; ctx.moveTo(Math.cos(a) * 5, Math.sin(a) * 5); ctx.lineTo(-Math.cos(a) * 5, -Math.sin(a) * 5); } ctx.strokeStyle = "#cdeeff"; ctx.stroke(); }
    else if (el === "oil") { ctx.fillStyle = "#3a2a18"; ctx.arc(0, 0, 4.5, 0, TAU); ctx.fill(); ctx.strokeStyle = "#c8a050"; ctx.stroke(); }
    else if (el === "mist") { ctx.strokeStyle = "#e8e8e0"; for (const y of [-2, 2]) { ctx.moveTo(-5, y); ctx.lineTo(5, y); } ctx.stroke(); }
    ctx.restore(); }
  // ---------- 圖示表：[id, 名稱, 類別, 畫法, 品質(材料用 1～3)] ----------
  const LIST = [
    ["item_hp_potion_small", "小回復藥", "consumable", (c) => flask(c, "hp-s", "#e04a3a")],
    ["item_hp_potion_medium", "中回復藥", "consumable", (c) => flask(c, "hp-m", "#c8202a", true, true)],
    ["item_mana_potion", "回魔藥", "consumable", (c) => flask(c, "mp", "#4a8ae0")],
    ["item_antidote_herb", "解毒草", "consumable", (c) => { for (const [dx, r] of [[-6, -0.4], [0, 0], [6, 0.4]]) { c.save(); c.translate(24 + dx, 40); c.rotate(r); ink(c, `herb${dx}`, [[0, 0], [-6, -14], [0, -30], [6, -14]], "#6aa84a", { w: 0.7 }); stroke(c, `herb-v${dx}`, [[0, 0], [0, -26]], 0.6, "#2f5a22"); c.restore(); } stroke(c, "herb-tie", [[17, 36], [31, 36]], 1.8, "#b8432f"); }],
    ["item_water_flask", "水瓶", "throwable", (c) => { flask(c, "fw", "#3f8ac8", false); elementMark(c, "water"); }],
    ["item_oil_flask", "油瓶", "throwable", (c) => { flask(c, "fo", "#3a2a18", false); elementMark(c, "oil"); }],
    ["item_mist_flask", "霧瓶", "throwable", (c) => { flask(c, "fm", "#c8ccd0", false); elementMark(c, "mist"); }],
    ["item_frost_flask", "冰瓶", "throwable", (c) => { flask(c, "ff", "#9ad8f0", false); elementMark(c, "ice"); }],
    ["item_fire_flask", "火瓶", "throwable", (c) => { flask(c, "fr", "#ff7a2a", false); elementMark(c, "fire"); }],
    ["item_supplies", "補給", "supply", (c) => { ink(c, "sup-roll", [[8, 30], [40, 30], [40, 40], [8, 40]], "#8a6a3a", { w: 0.8 }); stroke(c, "sup-strap", [[16, 30], [16, 40]], 1.4, "#3a2a1a"); stroke(c, "sup-strap2", [[32, 30], [32, 40]], 1.4, "#3a2a1a"); ink(c, "sup-bread", ellPts(20, 22, 10, 7, 16), "#d8a860", { w: 0.8 }); ink(c, "sup-flask", [[28, 10], [36, 10], [38, 28], [26, 28]], "#a06a36", { w: 0.7 }); stroke(c, "sup-cut", [[15, 20], [18, 24]], 0.7, "#8a5a30"); }],
    ["item_coarse_material", "粗料", "material", (c) => ore(c, "m1", "#8a8a88"), 1],
    ["item_fine_material", "精料", "material", (c) => ore(c, "m2", "#8aa8c8"), 2],
    ["item_superior_material", "上料", "material", (c) => { glow(c, 24, 26, 18, "rgba(180,140,255,0.9)", 0.5); ore(c, "m3", "#b8a0e0"); }, 3],
    ["item_mist_crystal", "霧晶", "material", (c) => crystal(c, "mc", "#dfe8ec", "rgba(232,240,240,0.9)"), 2],
    ["item_summit_mist_crystal", "雲頂霧晶", "material", (c) => crystal(c, "smc", "#c8f0ff", "rgba(160,230,255,0.9)"), 3],
    ["item_talisman_ash", "符紙灰", "material", (c) => { ink(c, "ash-pile", [[8, 40], [16, 30], [24, 27], [32, 30], [40, 40]], "#8a8480", { w: 0.7 }); c.save(); c.translate(26, 20); c.rotate(0.3); ink(c, "ash-paper", [[-5, -9], [5, -9], [5, 9], [-5, 9]], "#e8c84a", { shade: false, w: 0.6, sharp: true }); stroke(c, "ash-mark", [[0, -6], [1, -2], [-1, 2], [1, 6]], 0.6, "#c0392b"); c.restore(); }, 1],
    ["item_cinnabar", "丹砂", "material", (c) => { ink(c, "cin-dish", [[8, 32], [40, 32], [34, 40], [14, 40]], "#e8dcc0", { w: 0.7 }); ink(c, "cin-pile", [[12, 32], [18, 24], [24, 21], [30, 24], [36, 32]], "#c8302a", { w: 0.7 }); }, 2],
    ["item_wolf_fang", "狼牙", "material", (c) => { c.save(); c.translate(24, 24); c.rotate(-0.5); ink(c, "fang", [[-6, -14], [6, -14], [4, 4], [0, 16], [-4, 4]], "#f2ecd8", { w: 0.8 }); stroke(c, "fang-cord", [[-8, -14], [8, -14]], 1.4, "#6a4a2a"); c.restore(); }, 1],
    ["item_thunder_feather", "雷羽", "material", (c) => { feather(c, "tf", "#c8b0ff", "#fff4a0"); stroke(c, "tf-bolt", [[34, 10], [30, 16], [35, 16], [31, 23]], 1.2, "#ffd23a"); }, 2],
    ["item_ember_feather", "餘燼羽", "material", (c) => feather(c, "ef", "#ff8a40", "#ffd23a"), 2],
    ["item_living_bone", "活血骨", "material", (c) => { c.save(); c.translate(24, 24); c.rotate(-0.7); ink(c, "bone", [[-3, -14], [3, -14], [3, 14], [-3, 14]], "#e8dcc0", { w: 0.8 }); for (const y of [-15, 15]) ink(c, `bone-k${y}`, ellPts(0, y, 6, 3.6, 12), "#e8dcc0", { w: 0.7 }); stroke(c, "bone-vein", [[0, -10], [1, -2], [-1, 6], [0, 12]], 0.9, "#c8302a"); c.restore(); }, 2],
    ["item_green_bamboo", "青竹節", "material", (c) => { c.save(); c.translate(24, 24); c.rotate(-0.6); ink(c, "bb", [[-4, -18], [4, -18], [4, 18], [-4, 18]], "#6aa84a", { w: 0.8 }); for (const y of [-6, 6]) stroke(c, `bb-n${y}`, [[-4, y], [4, y]], 1.2, "#2f5a22"); c.restore(); }, 1],
    ["item_essence", "精華", "material", (c) => { glow(c, 24, 26, 20, "rgba(255,240,180,0.9)", 0.7); ink(c, "ess", [[24, 10], [33, 26], [24, 40], [15, 26]], "#fff4c0", { w: 0.8, shade: false }); }, 3],
    ["item_lava_core", "熔岩核", "material", (c) => { glow(c, 24, 26, 18, "rgba(255,120,40,0.9)", 0.6); ink(c, "lc", ellPts(24, 26, 12, 12, 16), "#3a3330", { w: 0.9 }); stroke(c, "lc-c", [[16, 22], [22, 27], [20, 33]], 1.4, "#ffb030"); stroke(c, "lc-c2", [[28, 18], [26, 26], [32, 30]], 1.4, "#ffb030"); }, 2],
    ["item_scorched_iron", "焦鐵", "material", (c) => { ink(c, "si", [[8, 34], [14, 24], [40, 24], [34, 34]], "#5a5e60", { w: 0.9 }); ink(c, "si-top", [[14, 24], [18, 18], [42, 18], [40, 24]], "#7a7e80", { w: 0.7 }); c.fillStyle = "rgba(20,14,10,0.55)"; c.beginPath(); c.ellipse(24, 30, 6, 3, 0, 0, TAU); c.fill(); }, 1],
    ["item_frost_ember", "寒燼", "material", (c) => { glow(c, 24, 26, 18, "rgba(120,210,255,0.9)", 0.6); ink(c, "fe", [[12, 36], [16, 22], [24, 14], [32, 22], [36, 36]], "#2a3448", { w: 0.8 }); stroke(c, "fe-c", [[18, 30], [24, 22], [30, 30]], 1.4, "#7ad8ff"); }, 3],
    ["item_molten_heart", "熔心晶", "material", (c) => { glow(c, 24, 26, 20, "rgba(255,160,60,0.95)", 0.7); ink(c, "mh", [[24, 10], [34, 18], [34, 32], [24, 40], [14, 32], [14, 18]], "#ffb23a", { w: 0.9, shade: false }); c.fillStyle = "rgba(255,255,240,0.6)"; c.beginPath(); c.ellipse(20, 20, 3, 5, -0.4, 0, TAU); c.fill(); }, 3],
    ["item_sulfur_crystal", "硫磺結晶", "material", (c) => crystal(c, "sc", "#e8d84a", null), 1],
    ["item_obsidian_shard", "黑曜片", "material", (c) => crystal(c, "ob", "#2a2434", "rgba(160,140,255,0.6)"), 2],
    ...[["indigo", "靛青", "#2a4a8a"], ["cinnabar", "朱砂", "#c8302a"], ["ink", "墨色", "#1a1a1a"], ["jade", "翠綠", "#3a9a5a"], ["ochre", "赭黃", "#c8902a"], ["snow", "雪白", "#f2f2ee"]].map(([id, zh, col]) => [`item_dye_${id}`, `${zh}染料`, "dye", (c) => jar(c, `dye-${id}`, col)]),
    ["gold", "金幣", "currency", (c) => { for (const [dx, dy] of [[-6, 6], [6, 6], [0, -2]]) { ink(c, `coin${dx}${dy}`, ellPts(24 + dx, 26 + dy, 9, 9, 16), "#e8bb48", { w: 0.8 }); c.fillStyle = "#a07a20"; c.fillRect(22 + dx, 22 + dy, 4, 8); } }],
    ["quest_coin", "任務幣", "currency", (c) => { ink(c, "qc", [[24, 8], [39, 16], [39, 32], [24, 40], [9, 32], [9, 16]], "#c86a3a", { w: 0.9 }); ink(c, "qc-in", [[18, 18], [30, 18], [30, 30], [18, 30]], "#f2e6c8", { shade: false, w: 0.6 }); stroke(c, "qc-l", [[20, 22], [28, 22]], 0.7, "#6a4a2a"); stroke(c, "qc-l2", [[20, 26], [28, 26]], 0.7, "#6a4a2a"); }],
    ["source_shard", "源晶碎片", "currency", (c) => crystal(c, "ss", "#c8bcff", "rgba(143,123,255,0.9)")],
    ["quest_letter", "信件", "quest", (c) => { ink(c, "let", [[8, 14], [40, 14], [40, 36], [8, 36]], "#f2e6c8", { w: 0.8 }); stroke(c, "let-v", [[8, 14], [24, 27], [40, 14]], 0.8, INK); ink(c, "let-seal", ellPts(24, 27, 4, 4, 10), "#b8432f", { shade: false, w: 0.5 }); }],
    ["quest_key", "鑰匙", "quest", (c) => { c.save(); c.translate(24, 24); c.rotate(-0.7); ink(c, "key-bow", ellPts(0, -12, 7, 7, 14), "#e8bb48", { w: 0.8 }); ink(c, "key-shaft", [[-2, -6], [2, -6], [2, 16], [-2, 16]], "#e8bb48", { w: 0.7 }); ink(c, "key-bit", [[2, 10], [7, 10], [7, 15], [2, 15]], "#e8bb48", { w: 0.6 }); c.fillStyle = "#3a2a1a"; c.beginPath(); c.arc(0, -12, 3, 0, TAU); c.fill(); c.restore(); }],
    ["quest_map", "地圖殘頁", "quest", (c) => { ink(c, "map", [[8, 12], [30, 10], [40, 16], [38, 38], [12, 40]], "#e8dcb8", { w: 0.8 }); stroke(c, "map-route", [[14, 32], [20, 24], [28, 26], [32, 18]], 0.9, "#8a6a3a"); stroke(c, "map-x", [[30, 15], [34, 21]], 1.2, "#c8302a"); stroke(c, "map-x2", [[34, 15], [30, 21]], 1.2, "#c8302a"); }],
    ["quest_charm", "護符", "quest", (c) => { stroke(c, "charm-cord", [[24, 6], [24, 14]], 1.2, "#b8432f"); ink(c, "charm", [[16, 14], [32, 14], [32, 38], [24, 42], [16, 38]], "#b8432f", { w: 0.8 }); ink(c, "charm-in", [[19, 18], [29, 18], [29, 34], [19, 34]], "#e8bb48", { shade: false, w: 0.6 }); stroke(c, "charm-mark", [[24, 21], [24, 31]], 1, "#b8432f"); }],
  ];
  /** 畫一格圖示（size 是邊長）：底色依類別、外框依品質（材料）或類別色。 */
  function draw(ctx, x, y, size, item, opt = {}) {
    const [, , cat, fn, tier] = item, [bg, rim] = CAT[cat];
    ctx.save(); ctx.translate(x, y);
    ctx.beginPath(); ctx.roundRect(0, 0, size, size, size * 0.16); const g = ctx.createLinearGradient(0, 0, 0, size); g.addColorStop(0, bg); g.addColorStop(1, "#1a1612"); ctx.fillStyle = g; ctx.fill();
    ctx.lineWidth = Math.max(1.5, size * 0.035); ctx.strokeStyle = tier ? TIER[tier] : rim; ctx.stroke();
    ctx.save(); ctx.beginPath(); ctx.roundRect(0, 0, size, size, size * 0.16); ctx.clip(); ctx.scale(size / 48, size / 48); fn(ctx); ctx.restore();
    if (opt.count) { ctx.font = `bold ${Math.round(size * 0.24)}px Consolas, monospace`; ctx.textAlign = "right"; ctx.textBaseline = "alphabetic"; ctx.lineWidth = 3; ctx.strokeStyle = "#000"; ctx.strokeText(opt.count, size - 4, size - 4); ctx.fillStyle = "#fff"; ctx.fillText(opt.count, size - 4, size - 4); ctx.textAlign = "left"; }
    ctx.restore();
  }
  return { LIST, CAT, TIER, draw };
})();
