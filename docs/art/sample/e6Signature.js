// e6Signature.js：E6「裝備招牌效果」的介面樣張（畫圖 agent，2026-11-23；紀錄 docs/art/E6-招牌-美術.md）。
// 規則：docs/design/08-裝備.md 8.27、8.30；開發草案 docs/phases/E6草案.md E6-b2。
// 範圍：① 裝備卡第一行的招牌框（五種、傳說獨特效果、標灰）；② 撿到時的展示（一輪三選一、大世界掉落）；
//       ③ 角色面板的勾選樣式；④ 五種招牌的類型小圖示（A 有圖示／B 只有文字）。
// 卡片、面板、按鈕、字一律用現行 client/src/styles/index.css 的 class（gear-card、run-offer-card、run-hero…）；這裡只加 e6-* 的新元件。
// 小圖示：四種直接呼叫第④批部件（同一個題材同一個形）——新動作＝效果「暫時獲得技能」、新反應＝效果「額外反應」、
//         行為改寫＝骨架徽章「改造」、改寫規則＝效果「規則改變」；只有地形規則是新畫的（install() 時塞進 QIconsParts.CATS.effect，過審的畫法檔不動）。
// 全部是假資料；確定性：沒有 Math.random。
window.E6Sig = (() => {
  const Q = window.QIcons, QP = window.QIconsParts, QW = window.QIconsWeapons, QA = window.QIconsArmor;
  const { f, poly, el, halo } = Q.H;

  // ---------------------------------------------------------------------
  // 1. 五種招牌與顏色
  // ---------------------------------------------------------------------
  /** 五種招牌：中文照 content/equipment.py 的 SIGNATURE_KIND_ZH；cat／id＝小圖示用哪個部件圖樣。 */
  const KINDS = {
    action: { zh: "新動作", cat: "effect", id: "grant_skill", src: "第④批效果「暫時獲得技能」：米白卡（金星）＋白加號" },
    reaction: { zh: "新反應", cat: "effect", id: "extra_reaction", src: "第④批效果「額外反應」：綠回轉箭頭＋白加號" },
    terrain: { zh: "地形規則", cat: "effect", id: "e6_terrain", src: "新畫：草地格（側面看得到土層）上一對霜白腳印" },
    behavior: { zh: "行為改寫", cat: "skeleton", id: "modifier", src: "第④批骨架徽章「改造」：金齒輪（第③批 modify）" },
    rule: { zh: "改寫規則", cat: "effect", id: "rule_change", src: "第④批效果「規則改變」：金桿卷軸" },
  };
  const ORDER = ["action", "reaction", "terrain", "behavior", "rule"];
  /** 稀有度色：照 gear.css 的 .gear-rarity-* 徽章色（卡片標題旁那個字的顏色），招牌框沿用同一個色，不另開新色。 */
  const RARITY = { rare: ["#6fb4ff", "稀有"], epic: ["#c58cff", "史詩"], legendary: ["#ffb938", "傳說"], uncommon: ["#7fd08a", "優良"], common: ["#9a98a6", "普通"] };
  const GRAY = "#6a6878";
  /** B2（只做比較、不建議）：每種一個框色。 */
  const KIND_COLOR = { action: "#ffd23f", reaction: "#5ad06a", terrain: "#c8925a", behavior: "#ff9a3a", rule: "#c8a0d8" };
  /** 灰字（玩家看得到，用字已定：8.30 第 4 點、8.27 改寫規則）。 */
  const OFF_FULL = "身上已經有 3 個招牌效果生效，這個沒有效果，可以在角色面板換選";
  const offRule = (slotZh) => `和${slotZh}的改寫規則衝突，沒有效果`;

  // ---------------------------------------------------------------------
  // 2. 新圖樣：地形規則（±10 單位，第④批部件的座標）
  //    要說的是「腳下的格子照另一套規則」：一塊草地格（3/4 俯視的菱形格，側面露出土層）＋一對霜白腳印（霜行＝最常見的地形規則）。
  //    不用靴子（「移動」「移動後」「敵人進入你的表面時」都是靴子），不用水漬（「產生表面」）。≤14：腳印只留兩顆橢圓、沒有後跟。
  // ---------------------------------------------------------------------
  const GRASS = "#7cbf5a", GRASS_HI = "#b4e48c", DIRT = "#a06a36", DIRT_D = "#6a4420", FROST = "#eef8ff";
  const foot = (c, o, x, y, rot) => { c.save(); c.translate(x, y); c.rotate(rot);
    if (o.tiny) el(c, FROST, 0, 0, 1.7, 2.7); else { el(c, FROST, 0, -0.9, 1.6, 2.5); el(c, FROST, 0, 2.6, 1.15, 1.2); } c.restore(); };
  function terrainArt(c, o) {
    c.save(); c.translate(0, -1.2);
    poly(c, DIRT, [[-10.4, 0], [0, 5.4], [0, 10.4], [-10.4, 5]], 0.4); /* 左側面：土 */
    poly(c, DIRT_D, [[0, 5.4], [10.4, 0], [10.4, 5], [0, 10.4]], 0.4); /* 右側面：暗一階 */
    poly(c, GRASS, [[-10.4, 0], [0, -5.4], [10.4, 0], [0, 5.4]], 0.4); /* 上面：草 */
    if (!o.tiny) poly(c, GRASS_HI, [[-10.4, 0], [0, -5.4], [1.8, -4.4], [-7.6, 0.4]]); /* 左上緣亮面 */
    foot(c, o, -3.4, 0.9, -1.05); foot(c, o, 3.4, -1.1, -1.05); /* 一前一後，沿菱形斜邊的方向走 */
    c.restore();
  }
  function install() {
    QP.CATS.effect.e6_terrain = { zh: "地形規則（招牌）", topic: "草地格（側面土層）上一對霜白腳印", d: terrainArt };
  }

  // ---------------------------------------------------------------------
  // 3. 小圖示 canvas
  // ---------------------------------------------------------------------
  /** 一個招牌小圖示：box＝格子邊長（CSS px），圖樣本身＝box×0.75（同部件圓片的比例；18 → 13.5 px，走 tiny、不包外框）。
   *  res＝內部解析度（DOM 用 2＝遊戲的 DPR 2；真 1 倍傳 1）。 */
  function icon(kind, box, res = 2) {
    const K = KINDS[kind], cv = QP.glyph(K.cat, K.id, box * 0.75, res);
    cv.style.width = cv.style.height = box + "px"; cv.className = "e6-ico"; cv.dataset.kind = kind; return cv;
  }

  // ---------------------------------------------------------------------
  // 4. 假資料（數值照 3.3：×10 後的寫法）
  // ---------------------------------------------------------------------
  const W = (kind, form, material, rarity) => ({ lib: "w", look: { kind, form, material, rarity } });
  const A = (kind, form, material, rarity, slot, dye) => ({ lib: "a", slot, look: { kind, form, material, rarity, dye } });
  const ITEMS = {
    hook: { name: "勾魂鐮", slot: "主手", rarity: "rare", lv: 12, form: "鉤鐮・雙手", art: W("scythe", "hook", "steel", "rare"),
      sig: { kind: "action", name: "鉤爪拉近", text: "1 AP，射程 4：把一個敵人拉到你身旁。冷卻 3 回合。" },
      lines: ["力量 +3", "流血傷害 +12%"], now: "鐵鐮刀", nowSub: "普通・Lv8・長柄鐮", score: ["24", "41", "+17"] },
    vest: { name: "巡林者獵裝", slot: "身體", rarity: "epic", lv: 14, form: "", art: A("leather", "hunter", "leather", "epic", "body"),
      sig: { kind: "reaction", name: "回身一刺", text: "敵人離開你身旁時，用主手打他一下。和其他反應共用每輪 1 次。" },
      lines: ["基礎加成：防禦值 +4%", "敏捷 +3", "閃避 +3%"], now: "皮背心", nowSub: "優良・Lv10", score: ["30", "46", "+16"] },
    frost: { name: "霜行長靴", slot: "腳", rarity: "rare", lv: 12, form: "", art: A("boots", "tall", "leather", "rare", "feet"),
      sig: { kind: "terrain", name: "霜行", text: "你走過的格子結 1 回合冰；你自己踩不會滑倒。" },
      lines: ["基礎加成：防禦值 +1%"], now: "短靴", nowSub: "普通・Lv6", score: ["12", "38", "+26"] },
    cleave: { name: "裂地大劍", slot: "主手", rarity: "epic", lv: 15, form: "雙手劍・雙手", art: W("greatsword", "twohand", "steel", "epic"),
      sig: { kind: "behavior", name: "劈出直線", text: "普攻改成往前打 2 格直線，只打敵人；傷害照形狀係數降低。" },
      lines: ["力量 +4", "暴擊傷害 +15%", "技能強化：「橫掃」範圍 +1"], now: "勾魂鐮", nowSub: "稀有・Lv12・鉤鐮・雙手", score: ["41", "48", "+7"] },
    ember: { name: "餘燼墜飾", slot: "項鍊", rarity: "epic", lv: 14, form: "", art: A("pendant", "pendant", "gold", "epic", "neck"),
      sig: { kind: "rule", name: "慈焰", text: "你的火焰傷害打到隊友時，改成治療他。" },
      lines: ["智力 +3", "火焰傷害 +10%"], now: "銅項鍊", nowSub: "普通・Lv5", score: ["9", "44", "+35"] },
    mountain: { name: "移山者之盾", slot: "副手", rarity: "legendary", lv: 16, form: "包鐵圓盾", art: W("round_shield", "banded", "steel", "legendary"), legendary: true,
      sig: { kind: "rule", name: "移山", text: "你可以推動任何物件，連巨石、石柱也推得動。" },
      lines: ["體質 +4", "格擋 +8%"], now: "木圓盾", nowSub: "優良・Lv11・木圓盾", score: ["33", "49", "+16"] },
    lava: { name: "熔岩踏靴", slot: "腳", rarity: "rare", lv: 13, form: "", art: A("iron_boots", "sabaton", "iron", "rare", "feet"),
      sig: { kind: "terrain", name: "火行", text: "火表面不傷你，你站在火上也不會被點燃。" }, off: OFF_FULL,
      lines: ["基礎加成：防禦值 +3%", "火焰抗性 +10%"], now: "霜行長靴", nowSub: "稀有・Lv12", score: ["38", "40", "+2"] },
    blood: { name: "血痕皮甲", slot: "身體", rarity: "rare", lv: 13, form: "", art: A("leather", "vest", "leather", "rare", "body", "red"),
      sig: { kind: "rule", name: "血痕", text: "你穿過敵人身旁的格子時，讓他流血 2 回合。" }, off: offRule("項鍊"),
      lines: ["基礎加成：防禦值 +3%", "敏捷 +2"], now: "巡林者獵裝", nowSub: "史詩・Lv14", score: ["46", "37", "−9"] },
    gloves: { name: "獵人皮手套", slot: "手", rarity: "uncommon", lv: 12, form: "", art: A("leather_gloves", "short", "leather", "uncommon", "hands"),
      lines: ["敏捷 +2", "命中 +4%"], now: "素手套", nowSub: "普通・Lv6", score: ["10", "22", "+12"] },
  };

  // ---------------------------------------------------------------------
  // 5. DOM 小工具與元件
  // ---------------------------------------------------------------------
  /** h("div.a.b", { attrs }, ...children)：建 DOM；子節點可以是字串、節點、陣列、null。 */
  function h(sel, attrs, ...kids) {
    const [tag, ...cls] = sel.split("."), e = document.createElement(tag || "div");
    if (cls.length) e.className = cls.join(" ");
    for (const [k, v] of Object.entries(attrs ?? {})) { if (v == null) continue; if (k === "style") e.style.cssText = v; else if (k.startsWith("--")) e.style.setProperty(k, v); else e.setAttribute(k, v); }
    const add = (k) => { if (k == null || k === false) return; if (Array.isArray(k)) k.forEach(add); else e.append(k instanceof Node ? k : document.createTextNode(String(k))); };
    kids.forEach(add); return e;
  }
  /** 裝備圖示（現行 Q 版裝備格，稀有度框）：包在 .gear-icon 裡，同 GearIcon。 */
  function gearIcon(it, size) {
    const a = it.art, cv = a.lib === "w" ? QW.canvas(a.look, size, 1, { frame: "gear" }) : QA.canvas(a.look, size, 1, { slot: a.slot });
    return h("span.gear-icon", { style: `width:${size}px;height:${size}px;display:inline-block` }, cv);
  }
  /** 招牌框。opt.mode：A（圖示＋字，建議）｜B1（只有字）｜B2（字＋每種一個框色）；opt.fx＝撿到時的一次性強調；opt.offOverride＝換掉灰字。 */
  function sigBox(it, opt = {}) {
    const s = it.sig, mode = opt.mode ?? "A", off = opt.off ?? it.off ?? null, legend = !!it.legendary;
    const col = off ? GRAY : mode === "B2" ? KIND_COLOR[s.kind] : RARITY[it.rarity][0];
    const label = (legend ? "獨特效果" : "招牌") + "・" + KINDS[s.kind].zh;
    return h(`div.e6-sig${off ? ".off" : ""}${opt.fx ? ".fx" : ""}${legend ? ".legend" : ""}`, { "--sig": col, "data-kind": s.kind, "data-testid": "gear-card-signature" },
      h("div.e6-sig-head", null,
        h("span.e6-sig-tag", null, mode === "A" ? icon(s.kind, 18) : null, h("span", null, label)),
        h("span.e6-sig-name", null, s.name)),
      h("div.e6-sig-text", null, s.text),
      off ? h("div.e6-sig-off", null, off) : null);
  }
  /** 裝備卡（照 GearCardView.tsx：標題、部位・稀有度・Lv、詞條、和目前裝備比較）；招牌框放在詞條清單之前＝卡片第一行。 */
  function card(it, opt = {}) {
    const R = RARITY[it.rarity], sub = [it.slot, R[1], `Lv${it.lv}`, it.form].filter(Boolean).join("・");
    const tone = it.score[2].startsWith("−") ? "down" : "up";
    return h(`div.gear-card.gear-rarity-${it.rarity}`, { "data-testid": "gear-card" },
      h("div.gear-card-head", null, gearIcon(it, 64),
        h("div.gear-card-headtext", null,
          h("div.gear-card-title", null, it.name, h("span.gear-rarity-badge", null, " " + R[1])),
          h("div.small.muted", null, sub))),
      it.sig && opt.sig !== false ? sigBox(it, opt) : null,
      h("ul.gear-card-lines", null, it.lines.map((t) => h("li", null, t))),
      opt.compare === false ? null : h(`div.gear-card-compare.tone-${tone}`, null,
        h("div.gear-card-current", null, h("span", null, `目前：${it.now}`, h("span.muted.small", null, " " + it.nowSub))),
        h("div.small.gear-card-score", null, `預算分數 ${it.score[0]} → ${it.score[1]}（${it.score[2]}）`)));
  }
  /** 勾選框（招牌＝方框、改寫規則＝圓鈕）。 */
  const box = (on, round) => h(`span.e6-box${round ? ".round" : ""}${on ? ".on" : ""}`, { role: round ? "radio" : "checkbox", "aria-checked": on ? "true" : "false" });
  /** 角色面板的招牌清單。rows：[{ it, on, off? }]；hint＝按了第 4 個時的提示（新字）。 */
  function pickList(rows, opt = {}) {
    const live = rows.filter((r) => r.on), lives = live.length, rules = live.filter((r) => r.it.sig.kind === "rule").length;
    const hasRule = rows.some((r) => r.it.sig.kind === "rule");
    return h("div.e6-pick", { "data-testid": "run-signatures" },
      h("div.section-title", null, "招牌效果",
        h("span.muted.small.lead-gap", { "data-testid": "run-signature-count" }, `生效 ${lives}／3` + (hasRule ? `・改寫規則 ${rules}／1` : ""))),
      opt.hint ? h("div.small.e6-pick-hint", null, opt.hint) : null,
      h("ul.e6-pick-list", null, rows.map((r) => {
        const s = r.it.sig, off = r.on ? null : (r.off ?? OFF_FULL);
        return h(`li.e6-pick-row${off ? ".off" : ""}${r.press ? ".press" : ""}`, { "--sig": off ? GRAY : RARITY[r.it.rarity][0] },
          box(r.on, s.kind === "rule"),
          icon(s.kind, 16),
          h("div.e6-pick-main", null,
            h("div.e6-pick-line", null, h("b.e6-pick-name", null, s.name), h("span.muted.small", null, `${KINDS[s.kind].zh}・${r.it.slot}：${r.it.name}`)),
            off ? h("div.small.e6-pick-off", null, off) : null));
      })));
  }
  return { KINDS, ORDER, RARITY, GRAY, KIND_COLOR, OFF_FULL, offRule, ITEMS, install, icon, terrainArt, h, gearIcon, sigBox, card, box, pickList };
})();
