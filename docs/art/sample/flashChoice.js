// 靈感閃現「選變體」畫面改版樣張（flash-choice.html 用）。紀錄：docs/art/靈感閃現選擇-改版提案.md。
// 使用者原話：「我感覺現在的文字理解還是不夠直觀」。現行＝client/src/screens/RunFlashPending.tsx（FlashPendingPanel）：每個選項
// 「類別標籤＋summary_zh＋cardDiff 差異行＋整張 SkillCardView＋選這個」，最下面「確定」。
// 新版：原技能只在固定區出現一次；每個選項＝一行白話大標＋只列有變的欄位「前 → 後」；點一下選中並展開（一次只開一個），
// 展開才有白話說明與「確定」。術語一律點線底線＋說明卡（遊戲端 Hint）。
// 資料照遊戲現況（使用者截圖 user-before-1／2，點燃斬第 1 次閃現的四個選項）；數值不改。
// 面板大小照派工單（client/src/world/hud.ts popupBox）：1600×900＝720×700、800×600＝493×414。
// 元件沿用 infoPanels.js（IP.tag、IP.newText、ip-* 樣式）；圖示一律呼叫前批 Q 版畫法，不另畫：
//   技能圖示 QIconsParts.canvas（第③④批：道具＋出手＋骨架徽章）、卡片小圖 QIconsParts.cardCanvas（第④批：AP、耐力、冷卻、射程、傷害）、
//   狀態 QIconsStatus.cardCanvas（第⑤批：燃燒）、關鍵字圓章 QIconsKeywords.chipCanvas（第⑤b 批：點燃、潮濕、撞擊）、
//   部件圖樣 IP.part（第④批：表面「水」、條件「目標本回合受過撞擊」）、靈感燈泡 IP.ICON.bulb（第⑦批 HUD）。
window.FC = (() => {
  const { h } = OB;
  const QP = QIconsParts;
  const BOX = { 1600: { w: 720, h: 700, zh: "1600×900" }, 800: { w: 493, h: 414, zh: "800×600" } };

  // ---------------- 圖示 ----------------
  const card = (id, px = 16) => { const c = QP.cardCanvas(id, px); c.className = "ip-ico"; return c; };
  const status = (id, px = 18) => { const c = QIconsStatus.cardCanvas(id, px); c.className = "ip-ico"; return c; };
  const kw = (id, px = 16) => { const c = QIconsKeywords.chipCanvas(id, px); c.className = "ip-ico"; return c; };
  const part = (cat, id, px = 20) => IP.part(cat, id, px);
  /** 點燃斬的技能圖示：主圖照第③批推導（同「餘燼啃咬」：劍＋揮砍＋持續傷害、火焰底），mid＝技能卡 56px 建議版（只有骨架徽章「控制」金鎖）。 */
  const SKILL_ICON = { kind: "active", rarity: "rare", elements: ["fire"], weapon_req: "melee", segments: [{ skeleton: "control", shape_id: "cross", range: 4, elements: ["fire"], effects: [{ type: "apply_status", status: "burning" }] }], link: null, condition: null, costs: [] };
  const SKILL_LOOK = { prop: "w:sword", motion: "swing", act: "dot", tint: "fire", el: "fire", el2: null, spark: null, kind: "active", rarity: "rare" };
  const skillIcon = (px) => { const c = QP.canvas(SKILL_ICON, SKILL_LOOK, px, 1, { level: "mid" }); c.className = "ip-ico"; return c; };

  // ---------------- 術語（白話＋說明卡）；字的來源寫在 src，給玩法 PM 對照 ----------------
  const T = {
    range: { cur: "射程（只在形狀括號裡：「十字（射程 4）」）", w: "射程", t: "射程", d: "從你站的格子算起，最遠能把技能放到幾格外。", src: "現行：形狀「十字（射程 4）」" },
    cross: { cur: "十字（沒有說明）", w: "十字", t: "十字範圍", d: "選射程內的一格當中心，打中心和上下左右各 1 格，共 5 格。", src: "content/skill_shapes.yaml cross" },
    cooldown: { cur: "冷卻 2 回合（沒有說明）", w: "冷卻", t: "冷卻", d: "用過之後要等幾回合才能再用。", src: "現行：「冷卻 2 回合」" },
    ap: { cur: "AP 2（沒有說明）", w: "AP", t: "AP（行動點）", d: "每回合能做幾件事。用技能、移動都要花 AP。", src: "現行：「AP 2」" },
    stamina: { cur: "花耐力／耐力 2", w: "耐力", t: "耐力", d: "武器技要花的資源（法術花法力）。", src: "現行：「花耐力」「耐力 2」" },
    burning: { cur: "狀態「燃燒」5 回合（敵方）", w: "燃燒", t: "燃燒", d: "身上著火：每回合開始受到 1d6 火焰傷害。再被點一次會重新算回合。", src: "content/statuses.yaml burning" },
    ignite: { cur: "製造：點燃（滑過有說明）", w: "點燃", t: "點燃（關鍵字）", d: "火焰讓目標燃燒；燃燒中的目標會受到更重的傷害，或被引爆。", src: "content/skill_keywords.yaml ignite" },
    wet: { cur: "製造：潮濕（滑過有說明）", w: "潮濕", t: "潮濕（關鍵字）", d: "水讓地面積水；站在水上的單位會被雷電傳導、被冰霜凍結。", src: "content/skill_keywords.yaml wet" },
    puddle: { cur: "生成「水」表面（影響的格子）", w: "積水", t: "積水（水表面）", d: "地上一灘水，預設留 3 回合。站在上面的單位會被雷電傳導、被冰霜凍結。", src: "content/surfaces.yaml water（duration 3）＋ wet 的說明" },
    collision: { cur: "利用：撞擊／若目標本回合受過撞擊", w: "撞擊", t: "撞擊（關鍵字）", d: "被推去撞上牆或別人，會受撞擊傷害；撞擊時可以觸發更多效果。", src: "content/skill_keywords.yaml 撞擊" },
    weaponDmg: { cur: "武器傷害 ×0.3（敵方）＋傷害算法：…（目前 +3）", w: "武器傷害", t: "武器傷害怎麼算", d: "（武器骰 1d8 ＋ 力量、智力的平均加成）× 0.3。屬性加成目前 +3。", src: "現行：「傷害算法：武器骰 1d8＋力量／智力（取平均） × 0.3（目前 +3）」" },
    scaling: { cur: "縮放：力量／智力（取平均）", w: "威力看", t: "威力看哪個屬性", d: "力量、智力越高，這招越強（兩個取平均）。", src: "現行：「縮放：力量／智力（取平均）」" },
    makes: { cur: "製造：", w: "會造成", t: "會造成（關鍵字）", d: "這招打中後，目標或地面會帶上這個關鍵字，可以接別的技能。", src: "現行：「製造：點燃」" },
    uses: { cur: "利用：", w: "對它加碼", t: "對它加碼（關鍵字）", d: "目標身上有這個關鍵字時，這招會變強。", src: "現行：「利用：撞擊」" },
    rare: { cur: "稀有（滑過有說明）", w: "稀有", t: "稀有", d: "稀有度表示這招長得多複雜，不代表強度。強度看角色階級與閃現次數。", src: "client/src/run/flash.ts RARITY_HINT（原句）" },
    control: { cur: "控場", w: "控場", t: "控場技", d: "主要用來限制、削弱敵人，傷害不是重點。", src: "現行：「控場」（骨架名）" },
    weaponSkill: { cur: "武器技・花耐力・看手上武器", w: "武器技", t: "武器技", d: "用手上的武器出招：要花耐力，傷害照武器的骰子算。", src: "現行：「武器技・花耐力・看手上武器」" },
    element: { cur: "技能元素：火焰", w: "元素", t: "元素", d: "火焰會和地面、狀態起反應（例：點燃油、引爆）。", src: "現行：「技能元素：火焰」" },
    power: { cur: "威力提高", w: "威力", t: "威力提高", d: "冷卻變長，換來這招的強度往上調（由預算器算）。現行卡上沒有寫出哪一項變強、變多少。", src: "content/flash_templates.yaml cost_charge「蓄力：冷卻 +2（最多 5 回合），威力提高」" },
  };
  let OPEN_TIP = null; /* &tip=<id> 把那個說明卡畫出來 */
  /** 術語：點線底線；遊戲裡滑過出現說明卡（Hint）。label 省略時用術語本身的字。 */
  function term(id, label, place = "below") {
    const e = T[id];
    return h("span.fc-term", { tabindex: "0", "data-term": id }, label ?? e.w,
      OPEN_TIP === id ? h("div.ip-tipcard", { class: place }, h("span.t", {}, e.t), e.d) : null);
  }

  // ---------------- 原技能（點燃斬；使用者截圖第 1 張的原本卡） ----------------
  const stat = (icon, label, value, cls) => h("span.fc-stat", { class: cls || null }, icon, label, value != null ? h("b", {}, value) : null);
  function baseStrip(opt) {
    return h("div.fc-base", { class: opt.narrow ? "narrow" : null },
      skillIcon(opt.narrow ? 32 : 40),
      opt.narrow ? h("span.fc-base-k", {}, IP.newText("原本")) : h("div.fc-base-name", {}, "點燃斬", h("span.k", {}, IP.newText("原本的樣子"))),
      h("div.fc-stats", {},
        stat(card("ap"), term("ap"), "2"),
        stat(card("stamina"), term("stamina"), "2"),
        stat(card("cooldown"), term("cooldown"), "2"),
        stat(card("range"), term("range"), "4"),
        stat(status("burning", 16), term("burning"), "5 回合")),
      h("span.fc-base-more", {}, h("button", { type: "button" }, IP.newText(opt.narrow ? "說明" : "完整說明")), opt.base ? basePop() : null));
  }
  /** 「完整說明」：原卡「詳細」裡的全部欄位，改成白話（沒有一項丟掉）。 */
  function basePop() {
    return h("div.fc-pop", {},
      h("h4", {}, "點燃斬"),
      h("dl", {},
        h("dt", {}, "類型"), h("dd", {}, term("rare"), "・主動・", term("control"), "・", term("weaponSkill")),
        h("dt", {}, "花費"), h("dd", {}, term("ap"), " 2、", term("stamina"), " 2；", term("cooldown"), " 2 回合"),
        h("dt", {}, "範圍"), h("dd", {}, term("cross"), "，", term("range"), " 4 格"),
        h("dt", {}, "效果"), h("dd", {}, "讓範圍裡的敵人", term("burning"), " 5 回合"),
        h("dt", {}, term("makes")), h("dd", {}, kw("ignite", 14), " ", term("ignite")),
        h("dt", {}, term("element")), h("dd", {}, "火焰"),
        h("dt", {}, term("scaling")), h("dd", {}, "力量、智力（取平均）")),
      h("p.concept", {}, "讓目標身上燒起來"));
  }

  // ---------------- 四個選項（照使用者截圖；was＝現行標題 summary_zh，放進紀錄的改字表） ----------------
  // diff：每列 [圖示, 欄位, 前（null＝原本沒有）, 後, 樣式 up｜cost, 新增?, 同一列再接一段（[圖示, 字]，樣式 unk）]
  const OPTS = [
    { cat: "範圍", tpl: "range_plus", was: "距離 +1（傷害依預算調整）", icon: () => card("range", 20), head: "射程變遠 1 格",
      diff: () => [[card("range"), term("range"), "4 格", "5 格", "up"]],
      say: () => ["十字範圍照舊，中心最遠可以放到 5 格外。"], dia: "range" },
    { cat: "費用", tpl: "cost_charge", was: "蓄力：冷卻 +2（最多 5 回合），威力提高", icon: () => card("cooldown", 20), head: "等久一點再用，換更強的威力",
      diff: () => [[card("cooldown"), term("cooldown"), "2 回合", "4 回合", "cost", false, [card("damage"), [term("power"), " 提高（卡上沒寫多少）"]]]],
      say: () => ["用過之後要等 4 回合才能再用（原本 2），", term("power"), "往上調。"] },
    { cat: "元素與關鍵字", tpl: "keyword_imbue", was: "加第二個關鍵字：命中時額外製造該關鍵字", icon: () => part("surface", "water", 22), head: "打中的格子還會積水",
      diff: () => [[part("surface", "water", 16), "地面", null, [term("puddle"), "，", term("makes"), " ", kw("wet", 14), " ", term("wet")], "up", true]],
      say: () => ["打中時，十字範圍的 5 格地上會", term("puddle", null, "above"), "；站在水上的敵人之後被雷電打會傳導、被冰霜打會結凍。"], dia: "water" },
    { cat: "元素與關鍵字", tpl: "keyword_exploit", was: "加第二個關鍵字：目標帶有該關鍵字時加碼", icon: () => part("condition", "target_collided", 22), head: "敵人剛被撞過，再多打一下",
      diff: () => [[card("damage"), "加打", null, ["3 成", term("weaponDmg"), h("span.fc-when", {}, "（目標這回合被", term("collision", "撞過"), "才有）")], "up", true]],
      say: () => ["目標這回合被推去", term("collision", "撞過", "above"), "牆或別人時，再多受 3 成", term("weaponDmg", null, "above"), "。"] },
  ];

  /** 射程示意：自己（黃）→ 中間格 → 十字（紅）；新多的那一格亮金框。照第④批卡片「射程」圖的配色（黃格自己、紅格目標）。 */
  function rangeDia(reach, grow) {
    const c = 9, gap = 1, cols = reach + 2, rows = 3, res = 2, W = cols * (c + gap), H = rows * (c + gap);
    const cv = document.createElement("canvas"); cv.width = W * res; cv.height = H * res; cv.style.width = W + "px"; cv.style.height = H + "px";
    const x = cv.getContext("2d"); x.scale(res, res);
    const cell = (i, j, fill, edge) => { const px = i * (c + gap), py = j * (c + gap); x.fillStyle = fill; x.fillRect(px, py, c, c); if (edge) { x.strokeStyle = edge; x.lineWidth = 1.2; x.strokeRect(px + 0.6, py + 0.6, c - 1.2, c - 1.2); } };
    for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) cell(i, j, "rgba(255,255,255,0.06)");
    cell(0, 1, "#f0c040"); /* 自己 */
    for (let i = 1; i < reach; i++) cell(i, 1, "rgba(255,255,255,0.18)");
    for (const [i, j] of [[reach, 1], [reach - 1, 1], [reach + 1, 1], [reach, 0], [reach, 2]]) cell(i, j, i === reach && j === 1 ? "#e8503a" : "rgba(232,80,58,0.62)");
    if (grow) cell(reach, 1, "#e8503a", "#ffe08a");
    return cv;
  }
  /** 積水示意：十字 5 格，水表面的藍＋白色反光（照第④批表面「水」的色）。 */
  function waterDia() {
    const c = 9, gap = 1, res = 2, W = 3 * (c + gap), cv = document.createElement("canvas"); cv.width = cv.height = W * res; cv.style.width = cv.style.height = W + "px";
    const x = cv.getContext("2d"); x.scale(res, res);
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) { x.fillStyle = "rgba(255,255,255,0.06)"; x.fillRect(i * (c + gap), j * (c + gap), c, c); }
    for (const [i, j] of [[1, 1], [0, 1], [2, 1], [1, 0], [1, 2]]) { const px = i * (c + gap), py = j * (c + gap); x.fillStyle = "#3f8fdc"; x.fillRect(px, py, c, c); x.fillStyle = "rgba(255,255,255,0.6)"; x.fillRect(px + 1.5, py + 2, 3.5, 1.4); x.fillRect(px + 5, py + 5.5, 2.5, 1.2); }
    return cv;
  }

  function diffRows(o) {
    const kids = [];
    for (const [icon, lab, was, now, cls, isNew, extra] of o.diff()) {
      kids.push(icon, h("span.fc-lab", {}, lab), h("span.fc-was", { class: was == null ? "none" : null }, was ?? "沒有"), h("span.fc-arrow", {}, "→"),
        h("span.fc-nows", {}, h("span.fc-now", { class: cls }, isNew ? h("span.fc-newtag", {}, "新") : null, h("span", {}, now)),
          extra ? h("span.fc-now.unk", {}, extra[0], h("span", {}, extra[1])) : null));
    }
    return h("div.fc-diffs", {}, kids);
  }
  /** 選項卡：選中＝亮金框（描框只表示狀態）；卡本身不展開，選中的說明與「確定」在下緣的固定區（點哪個都不跳）。 */
  function optCard(o, i, on) {
    return h("div.fc-opt", { class: on ? "on" : null, "data-opt": String(i + 1) },
      h("div.fc-opt-top", {}, h("span.fc-radio"), o.icon(), h("span.fc-headline", {}, IP.newText(o.head)), h("span.fc-cat", {}, IP.tag("", o.cat))),
      diffRows(o));
  }
  /** 下緣固定區：選中的白話說明＋確定。都沒選時提示先點一個、確定按不下去（同現行）。寬版多一張示意圖。 */
  function foot(pick, narrow) {
    const o = OPTS[pick - 1];
    const dia = !o || narrow ? null
      : o.dia === "range" ? h("div.fc-diagrams", {}, h("div.fc-dia", {}, rangeDia(4, false), h("span", {}, "原本 4 格")), h("div.fc-dia", {}, rangeDia(5, true), h("span", {}, "變成 ", h("b", {}, "5 格"))))
      : o.dia === "water" ? h("div.fc-diagrams", {}, h("div.fc-dia", {}, waterDia(), h("span", {}, "打到的 5 格"))) : null;
    return h("div.fc-foot", {},
      h("div.fc-say", {}, o ? [h("b.fc-picked", {}, IP.newText(o.head)), h("span", {}, "：", ...o.say())] : h("span.dim", {}, IP.newText("先點一個變化。點數已經扣了，一定要選一個。"))),
      dia,
      h("button.primary", { type: "button", disabled: o ? null : true }, "確定"));
  }

  // ---------------- 一屏（面板） ----------------
  // 上：固定區（標頭＋原技能列，只出現一次）；中：四個選項（捲動區）；下：固定區（選中的說明＋確定）。
  // 窄版（面板寬 < 560，800×600 的 493）：標題、技能名、已扣點數併成一行，「一定要選一個」收進 (i)；原技能列不再寫名字（標頭已有）；下緣不畫示意圖。
  // 面板高度＝「都沒選」與四個各自選中裡最高的那一次（同 11.4 第 8 條：點哪個都不跳框），不超過 popupBox 上限。
  const SCREENS = [];
  const opts = (pick) => h("div.fc-opts", {}, OPTS.map((o, i) => optCard(o, i, pick === i + 1)));
  /** vw＝1600｜800；opt.pick＝選中第幾個（1～4，0＝都沒選）；opt.tip＝要畫出來的說明卡；opt.base＝「完整說明」打開。 */
  function screen(vw, opt = {}) {
    const box = BOX[vw], narrow = box.w < 560;
    opt = { ...opt, narrow };
    OPEN_TIP = opt.tip ?? null;
    const x = h("button.ip-x", { type: "button", "aria-label": "關閉" }, "×");
    const must = IP.newText("一定要選一個，每個都不會讓這招變弱");
    const fixed = h("div.ip-fixed", {},
      narrow
        ? h("div.fc-head", {}, h("h2.fc-title", {}, IP.ICON.bulb(18), "靈感閃現"), h("span.fc-sub.inline", {}, IP.newText("「點燃斬」第 1 次"), IP.tag("open", "已扣 1 點"), IP.tip(must, { open: opt.tip === "must", right: true })), x)
        : h("div", {}, h("div.fc-head", {}, h("h2.fc-title", {}, IP.ICON.bulb(20), "靈感閃現", h("small", {}, IP.newText("選一個變化"))), x),
          h("div.fc-sub", {}, IP.newText("「點燃斬」第 1 次閃現"), IP.tag("open", "已扣 1 點"), h("span", {}, must))),
      baseStrip(opt));
    const body = h("div.ui-popup-body", {}, opts(opt.pick));
    const ft = foot(opt.pick, narrow);
    const panel = h("div.ui-popup.rt-frame.ui-popup-hud.world-hud-panel.ip-hudpanel", { "data-popup": "hud", class: narrow ? "fc-narrow" : null }, fixed, body, ft);
    OB.applyTheme("cloud_ridge", panel);
    const rail = h("div.ip-rail", {}, h("i"));
    const wrap = h("div.ip-screen.fc-screen", { style: `width:${box.w}px;height:${box.h}px` }, panel, rail);
    const meter = h("div.ip-meter", { style: `width:${box.w}px` });
    SCREENS.push({ wrap, body, fixed, ft, rail, meter, opt, vw });
    OPEN_TIP = null;
    return h("div.fc-stack", {}, wrap, meter);
  }
  const offsetIn = (body, el) => el.getBoundingClientRect().top - body.getBoundingClientRect().top + body.scrollTop;
  const usedHeight = (body) => Math.round(Math.max(0, ...[...body.children].map((c) => c.getBoundingClientRect().bottom)) - body.getBoundingClientRect().top + body.scrollTop);
  /** 說明卡浮在面板之上（遊戲端 Hint／float-card 是浮層，不會被面板的捲動區切掉）：把畫出來的說明卡搬到一屏的外層、照字的位置擺。
   *  同一個術語在一屏裡出現兩次時只開一張（「完整說明」打開時優先開它裡面的那一個）。 */
  function floatTips(wrap) {
    const W = wrap.getBoundingClientRect();
    const put = (card, anchor, place, alignRight) => {
      const r = anchor.getBoundingClientRect();
      wrap.append(card);
      card.classList.add("fc-float");
      const w = card.offsetWidth, hh = card.offsetHeight;
      let left = alignRight ? r.right - W.left + 12 - w : r.left - W.left - 12;
      const right = left + w > W.width + 60;
      if (right) left = r.right - W.left + 12 - w;
      card.classList.toggle("right-edge", right || !!alignRight);
      card.style.left = Math.max(-40, left) + "px";
      card.style.top = (place === "above" ? r.top - W.top - 8 - hh : r.bottom - W.top + 8) + "px";
    };
    const pop = wrap.querySelector(".fc-pop");
    if (pop) put(pop, pop.parentElement.querySelector("button"), "below", true);
    const cards = [...wrap.querySelectorAll(".fc-term > .ip-tipcard, .ip-tip > .ip-tipcard")];
    const keep = cards.find((c) => c.closest(".fc-pop")) ?? cards[0];
    for (const c of cards) {
      if (c !== keep) { c.remove(); continue; }
      const anchor = c.parentElement, place = c.classList.contains("above") ? "above" : "below";
      anchor.classList.add("fc-term-on");
      put(c, anchor, place, false);
    }
  }
  /** 頁面 load 後量高度：「都沒選」與四個各自選中（下緣固定區的字數不同）輪流量，取最高的定面板高；選中的那張捲到看得到。 */
  function finish() {
    for (const s of SCREENS) {
      const { wrap, body, rail, meter, opt, vw } = s;
      let { ft } = s;
      const panel = body.parentElement, keepBody = [...body.childNodes], keepFt = ft;
      const frame0 = () => wrap.getBoundingClientRect().height - body.clientHeight;
      let footMax = 0;
      const need = [0, 1, 2, 3, 4].map((n) => { body.replaceChildren(opts(n)); const f = foot(n, opt.narrow); panel.replaceChild(f, ft); ft = f; footMax = Math.max(footMax, f.getBoundingClientRect().height); return Math.ceil(frame0() + usedHeight(body) + 12); });
      panel.replaceChild(keepFt, ft); ft = keepFt; body.replaceChildren(...keepBody);
      ft.style.minHeight = Math.ceil(footMax) + "px"; /* 下固定區固定高（字數不同也不動分隔線） */
      const hh = Math.min(BOX[vw].h, Math.max(...need));
      wrap.style.height = hh + "px";
      const ch = body.clientHeight, used = usedHeight(body), over = used > ch + 1;
      body.dataset.overflow = over ? "1" : "0";
      if (opt.pick && over) {
        const el = body.querySelector(`[data-opt="${opt.pick}"]`), top = offsetIn(body, el), bottom = top + el.offsetHeight;
        if (bottom > body.scrollTop + ch - 20) body.scrollTop = Math.min(top - 6, bottom - ch + 24);
        body.dataset.scrolled = body.scrollTop > 0 ? "1" : "0";
        if (body.scrollTop + ch >= body.scrollHeight - 1) body.dataset.end = "1";
      }
      if (over) {
        const wr = wrap.getBoundingClientRect(), br = body.getBoundingClientRect(), sh = body.scrollHeight;
        const th = Math.max(24, (br.height * ch) / sh), tt = ((br.height - th) * body.scrollTop) / Math.max(1, sh - ch);
        rail.style.display = "block"; rail.style.top = br.top - wr.top + "px"; rail.style.height = br.height + "px";
        rail.firstChild.style.cssText = `top:${tt}px;height:${th}px`;
      }
      floatTips(wrap);
      const fx = Math.round(s.fixed.getBoundingClientRect().height + 18), fb = Math.round(ft.getBoundingClientRect().height);
      meter.innerHTML = `${BOX[vw].zh}：面板 <b>${BOX[vw].w}×${hh}</b>（上限 ${BOX[vw].h}；高＝都沒選與四個各自選中裡最高的那次：${need.join("／")}）；` +
        `上固定區 <b>${fx}</b>（含上緣 18）、下固定區 <b>${fb}</b>；選項區可視 <b>${ch}</b>、內容 <b>${used}</b> px` +
        (over ? `＝<b class="bad">${(used / ch).toFixed(2)} 屏</b>（捲了 ${Math.round(body.scrollTop)} px）` : `＝<b class="ok">一屏放得下</b>`);
    }
  }

  return { BOX, OPTS, T, screen, finish, term, skillIcon, card, status, kw, part, rangeDia, waterDia };
})();
