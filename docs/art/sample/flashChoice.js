// 靈感閃現「選變體」畫面改版樣張（flash-choice.html 用）。紀錄：docs/art/靈感閃現選擇-改版提案.md。
// 使用者原話：「我感覺現在的文字理解還是不夠直觀」。現行＝client/src/screens/RunFlashPending.tsx（FlashPendingPanel）：每個選項
// 「類別標籤＋summary_zh＋cardDiff 差異行＋整張 SkillCardView＋選這個」，最下面「確定」。
// 新版：原技能只在上固定區出現一次；每個選項＝一行白話大標＋只列有變的欄位「前 → 後」；點整張卡就選中（金框），卡本身不變大，
// 選中的白話說明與「確定」都在下固定區（點哪個都不跳）。術語一律點線底線＋說明卡（遊戲端 Hint）。
// 「後」的四種樣式（第 2 版，審查必修 1）：變好＝實心淡金底；代價＝琥珀細框＋警告小三角；變弱＝無底無框、次文字色＋向下小三角；
// 待資料＝虛線框＋「待資料／待規則」小標。新加的另掛實心綠「新」。不靠顏色也分得開（?state=marks 有色盲模擬）。
// 資料：第 1 組（set=base）照使用者截圖 user-before-1／2（點燃斬第 1 次閃現的四個選項），數值不改；
// 壓力情況 rows／wrap／transform 是示意資料（數值不是遊戲算的），用來證明 800 也放得下「常見最多」。
// 面板大小照 client/src/world/hud.ts popupBox：1600×900＝720×700、800×600＝493×414（PNL-1a 驗收實量）。
// 元件沿用 infoPanels.js（IP.tag、IP.newText、ip-* 樣式）；圖示一律呼叫前批 Q 版畫法，不另畫：
//   技能圖示 QIconsParts.canvas（第③④批：道具＋出手＋骨架徽章）、卡片小圖 QIconsParts.cardCanvas（第④批：AP、耐力、冷卻、射程、傷害）、
//   組裝圓片 QIconsParts.chipCanvas（第④批：骨架、形狀、效果）、狀態 QIconsStatus.cardCanvas（第⑤批：燃燒）、
//   關鍵字圓章 QIconsKeywords.chipCanvas（第⑤b 批：點燃、潮濕、撞擊）、部件圖樣 IP.part（第④批：表面「水」）、
//   靈感燈泡、警告三角 IP.ICON（第⑦批 HUD）。
window.FC = (() => {
  const { h } = OB;
  const QP = QIconsParts;
  const BOX = { 1600: { w: 720, h: 700, zh: "1600×900" }, 800: { w: 493, h: 414, zh: "800×600" } };

  // ---------------- 圖示 ----------------
  const card = (id, px = 16) => { const c = QP.cardCanvas(id, px); c.className = "ip-ico"; return c; };
  const status = (id, px = 18) => { const c = QIconsStatus.cardCanvas(id, px); c.className = "ip-ico"; return c; };
  const kw = (id, px = 16) => { const c = QIconsKeywords.chipCanvas(id, px); c.className = "ip-ico"; return c; };
  const part = (cat, id, px = 20) => IP.part(cat, id, px);
  const chip = (cat, id, px = 22) => { const c = QP.chipCanvas(cat, id, px); c.className = "ip-ico"; return c; };
  /** 點燃斬的技能圖示：主圖照第③批推導（同「餘燼啃咬」：劍＋揮砍＋持續傷害、火焰底），mid＝技能卡 56px 建議版（只有骨架徽章「控制」金鎖）。 */
  const SKILL_ICON = { kind: "active", rarity: "rare", elements: ["fire"], weapon_req: "melee", segments: [{ skeleton: "control", shape_id: "cross", range: 4, elements: ["fire"], effects: [{ type: "apply_status", status: "burning" }] }], link: null, condition: null, costs: [] };
  const SKILL_LOOK = { prop: "w:sword", motion: "swing", act: "dot", tint: "fire", el: "fire", el2: null, spark: null, kind: "active", rarity: "rare" };
  const skillIcon = (px) => { const c = QP.canvas(SKILL_ICON, SKILL_LOOK, px, 1, { level: "mid" }); c.className = "ip-ico"; return c; };
  /** 內容裡現有技能的圖示（第③④批，QPARTS_ICONS＋QSKILLS 的 q）：轉型卸下選單用。 */
  const SK = Object.fromEntries((window.QSKILLS ?? []).map((s) => [s.id, s]));
  const ownedIcon = (id, px) => { const s = SK[id]; const c = QP.canvas(window.QPARTS_ICONS[id], { ...s.q, kind: s.kind, rarity: s.rarity }, px, 1, { level: "mid" }); c.className = "ip-ico"; return c; };

  // ---------------- 術語（白話＋說明卡）；字的來源寫在 src，給玩法 PM 對照 ----------------
  // rule：說明卡裡有規則敘述（包二：問「對不對」）；orig：照內容原句（不另問）；pend：待確認的一句（標小標）。
  // 第 2 版：全部對照 docs/design/ 重看一次（05 5.2 行動經濟、05 撞擊與表面互動表、06 6.12／6.13、07 資源回復）。
  const T = {
    range: { cur: "射程（只在形狀括號裡：「十字（射程 4）」）", w: "射程", t: "射程", d: "從你站的格子算起，最遠能把技能放到幾格外。", src: "現行：形狀「十字（射程 4）」" },
    cross: { cur: "十字（沒有說明）", w: "十字", t: "十字範圍", d: "選射程內的一格當中心，打中心和上下左右各 1 格，共 5 格。", src: "content/skill_shapes.yaml cross", orig: true },
    square3: { cur: "3×3", w: "3×3", t: "3×3 範圍", d: "選射程內的一格當中心，打它和周圍一圈，共 9 格。", src: "content/skill_shapes.yaml square3（壓力情況用）", orig: true },
    cooldown: { cur: "冷卻 2 回合（沒有說明）", w: "冷卻", t: "冷卻", d: "用過之後要等幾回合才能再用。", src: "現行：「冷卻 2 回合」" },
    ap: { cur: "AP 2（沒有說明）", w: "AP", t: "AP（行動點）", d: "每回合 3 點，用技能、攻擊、道具、互動都要花；移動不花 AP。最多留 1 點到下回合。", src: "docs/design/05-戰鬥.md 5.2（第 2 版改：移動不花 AP）", rule: true },
    stamina: { cur: "花耐力／耐力 2", w: "耐力", t: "耐力", d: "武器技要花的資源（法術花法力）。每回合開始回一些，每場打完回滿。", src: "06 6.12 費用；07 資源回復", rule: true },
    burning: { cur: "狀態「燃燒」5 回合（敵方）", w: "燃燒", t: "燃燒", d: "身上著火：每回合開始受到 1d6 火焰傷害。再被點一次會重新算回合。", src: "content/statuses.yaml burning", orig: true },
    ignite: { cur: "製造：點燃（滑過有說明）", w: "點燃", t: "點燃（關鍵字）", d: "火焰讓目標燃燒；燃燒中的目標會受到更重的傷害，或被引爆。", src: "content/skill_keywords.yaml ignite", orig: true },
    wet: { cur: "製造：潮濕（滑過有說明）", w: "潮濕", t: "潮濕（關鍵字）", d: "水讓地面積水；站在水上的單位會被雷電傳導、被冰霜凍結。", src: "content/skill_keywords.yaml wet", orig: true },
    puddle: { cur: "生成「水」表面（影響的格子）", w: "積水", t: "積水（水表面）", d: "地上一灘水，預設留 3 回合。站在上面的單位會被雷電傳導、被冰霜凍結；受到的治療 +20%。",
      pend: ["不會澆熄敵人身上的燃燒；地上的火會被澆熄。", "待玩法 PM 確認"], src: "content/surfaces.yaml water（duration 3）＋ interactions.yaml＋ 05 #93；末句照 main 資料（審查決定 2）", rule: true },
    collision: { cur: "利用：撞擊／若目標本回合受過撞擊", w: "撞擊", t: "撞擊（關鍵字）", d: "被推、拉、擊退時撞上牆、物件或別人而提前停下，每少走 1 格受一次撞擊傷害；撞到人兩邊都受傷。", src: "docs/design/05-戰鬥.md 撞擊（第 2 版照規則改寫）", rule: true },
    weaponDmg: { cur: "武器傷害 ×0.3（敵方）＋傷害算法：…（目前 +3）", w: "武器傷害", t: "武器傷害怎麼算", d: "（武器骰 1d8 ＋ 力量、智力的平均加成）× 0.3。屬性加成目前 +3。", src: "現行：「傷害算法：武器骰 1d8＋力量／智力（取平均） × 0.3（目前 +3）」", rule: true },
    scaling: { cur: "縮放：力量／智力（取平均）", w: "威力看", t: "威力看哪個屬性", d: "力量、智力越高，這招越強（兩個取平均）。", src: "現行：「縮放：力量／智力（取平均）」；06 6.12 雙屬性" },
    makes: { cur: "製造：", w: "會造成", t: "會造成（關鍵字）", d: "這招打中後，目標或地面會帶上這個關鍵字，可以接別的技能。", src: "現行：「製造：點燃」" },
    uses: { cur: "利用：", w: "對它加碼", t: "對它加碼（關鍵字）", d: "目標身上有這個關鍵字時，這招會變強。", src: "現行：「利用：撞擊」（這次四個選項沒用到）" },
    rare: { cur: "稀有（滑過有說明）", w: "稀有", t: "稀有", d: "稀有度表示這招長得多複雜，不代表強度。強度看角色階級與閃現次數。", src: "client/src/run/flash.ts RARITY_HINT（原句）；06 6.12 #72", orig: true, rule: true },
    control: { cur: "控場", w: "控場", t: "控場技", d: "以狀態為主、傷害為輔：主要用來限制、削弱敵人。", src: "06 6.12 骨架表「控場 control：狀態為主，傷害為輔」", rule: true },
    weaponSkill: { cur: "武器技・花耐力・看手上武器", w: "武器技", t: "武器技", d: "用手上的武器出招：花耐力，傷害照武器的骰子算，威力看武器用的屬性。", src: "06 6.12 縮放與費用（第 2 版補「威力看武器的屬性」）", rule: true },
    element: { cur: "技能元素：火焰", w: "元素", t: "元素", d: "火焰會和地面、物件起反應（例：點燃油、引爆易爆物、把冰融成水）。", src: "05 標籤 × 元素互動表（第 2 版改：原本寫「狀態」不對）", rule: true },
    power: { cur: "威力提高", w: "威力", t: "威力提高", d: "冷卻變長，換來這招整體變強一點（由預算器重算）。", pend: ["開發查過：點燃斬選蓄力後沒有一項變強，只有冷卻 2 → 4。", "待資料／待規則"], src: "content/flash_templates.yaml cost_charge「蓄力：冷卻 +2（最多 5 回合），威力提高」；開發調查（閃現蓄力調查）：只有冷卻變，已交玩法 PM（決定 1）", rule: true },
    assembly: { cur: "控制＋十字＋燃燒（組裝圓片，沒有欄位名）", w: "組成", t: "組成", d: "這招由三塊拼成：骨架（怎麼出手）＋範圍形狀（打哪些格）＋效果（打中會怎樣）。", src: "現行卡「詳細」的組裝列（審查必修 6 補回）" },
    passiveKind: { cur: "被動（壓力情況：轉型）", w: "被動", t: "被動技", d: "不用自己按：條件到了自動發動，不花 AP。裝在被動欄（3 格）。", src: "06 6.13 欄位：主動 6、被動 3、反應 1（壓力情況用）", rule: true },
  };
  let OPEN_TIP = null; /* &tip=<id> 把那個說明卡畫出來 */
  const pendTag = (t) => h("span.fc-pending", {}, t);
  /** 術語：點線底線；遊戲裡滑過出現說明卡（Hint）。label 省略時用術語本身的字。 */
  function term(id, label, place = "below") {
    const e = T[id];
    return h("span.fc-term", { tabindex: "0", "data-term": id }, label ?? e.w,
      OPEN_TIP === id ? h("div.ip-tipcard", { class: place }, h("span.t", {}, e.t), e.d, e.pend ? h("span.fc-pendline", {}, e.pend[0], pendTag(e.pend[1])) : null) : null);
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
  /** 「完整說明」：原卡「詳細」裡的全部欄位，改成白話（第 2 版補回組裝列「組成」，現在沒有一項丟掉）。 */
  function basePop() {
    const plus = () => h("span.fc-plus", {}, "＋");
    return h("div.fc-pop", {},
      h("h4", {}, "點燃斬"),
      h("dl", {},
        h("dt", {}, "類型"), h("dd", {}, term("rare"), "・主動・", term("control"), "・", term("weaponSkill")),
        h("dt", {}, term("assembly", IP.newText("組成"))), h("dd.fc-asm", {},
          h("span", {}, chip("skeleton", "control"), "控制"), plus(), h("span", {}, chip("shape", "cross"), "十字"), plus(), h("span", {}, chip("effect", "status:burning"), "燃燒")),
        h("dt", {}, "花費"), h("dd", {}, term("ap"), " 2、", term("stamina"), " 2；", term("cooldown"), " 2 回合"),
        h("dt", {}, "範圍"), h("dd", {}, term("cross"), "，", term("range"), " 4 格"),
        h("dt", {}, "效果"), h("dd", {}, "讓範圍裡的敵人", term("burning"), " 5 回合"),
        h("dt", {}, term("makes")), h("dd", {}, kw("ignite", 14), " ", term("ignite")),
        h("dt", {}, term("element")), h("dd", {}, "火焰"),
        h("dt", {}, term("scaling")), h("dd", {}, "力量、智力（取平均）")),
      h("p.concept", {}, "讓目標身上燒起來"));
  }

  // ---------------- 選項（was＝現行標題 summary_zh，放進紀錄的改字表） ----------------
  // diff：每列 { icon, lab, was（null＝原本沒有）, now, cls: up｜cost｜down｜unk, isNew, extra:{icon, now, cls, pend} 同一列再接一段 }
  // 第 2 版：大標前不再放圖示（審查可修 3：和下一行欄位圖示重複，射程那個在大標位置讀不出意思）。
  const R = (icon, lab, was, now, cls, more = {}) => ({ icon, lab, was, now, cls, ...more });
  const sayCharge = () => ["用過之後要等 4 回合才能再用（原本 2），", term("power"), "往上調。"];
  const OPT_RANGE = { cat: "範圍", tpl: "range_plus", was: "距離 +1（傷害依預算調整）", head: "射程變遠 1 格",
    diff: () => [R(card("range"), term("range"), "4 格", "5 格", "up")],
    say: () => ["十字範圍照舊，中心最遠可以放到 5 格外。"], dia: "range" };
  const OPT_CHARGE = { cat: "費用", tpl: "cost_charge", was: "蓄力：冷卻 +2（最多 5 回合），威力提高", head: "等久一點再用，換更強的威力",
    diff: () => [R(card("cooldown"), term("cooldown"), "2 回合", "4 回合", "cost", { extra: { icon: card("damage"), now: [term("power"), " 提高"], cls: "unk", pend: "待資料／待規則" } })],
    say: sayCharge };
  const OPT_WATER = { cat: "元素與關鍵字", tpl: "keyword_imbue", was: "加第二個關鍵字：命中時額外製造該關鍵字", head: "打中的格子還會積水",
    diff: () => [R(part("surface", "water", 16), "地面", null, [term("puddle"), "，", term("makes"), " ", kw("wet", 14), " ", term("wet")], "up", { isNew: true })],
    say: () => ["打中時，十字範圍的 5 格地上會", term("puddle", null, "above"), "；站在水上的敵人之後被雷電打會傳導、被冰霜打會結凍。"], dia: "water" };
  const OPT_BUMP = { cat: "元素與關鍵字", tpl: "keyword_exploit", was: "加第二個關鍵字：目標帶有該關鍵字時加碼", head: "敵人剛被撞過，這招多傷一截",
    diff: () => [R(card("damage"), "額外傷害", null, ["3 成", term("weaponDmg"), h("span.fc-when", {}, "（目標這回合被", term("collision", "撞過"), "才有）")], "up", { isNew: true })],
    say: () => ["目標這回合被推去", term("collision", "撞過", "above"), "牆或別人時，這招對它多 3 成", term("weaponDmg", null, "above"), "。"] };

  // 壓力情況（審查必修 2）：示意資料，數值不是遊戲算的。
  const OPT_LIGHT = { cat: "費用", tpl: "cost_light", was: "輕巧：AP −1（最少 1）、冷卻縮短，威力降低；…", head: "更省更快，但燒得短一點",
    diff: () => [R(card("ap"), term("ap"), "2", "1", "up"), R(card("cooldown"), term("cooldown"), "2 回合", "1 回合", "up"), R(status("burning", 16), term("burning"), "5 回合", "3 回合", "down")],
    say: () => ["只要 1 AP、隔 1 回合就能再用；燃燒從 5 回合變 3 回合。"] };
  const OPT_SQUARE = { cat: "範圍", tpl: "reshape_square3", was: "換成 3×3（傷害依預算調整）", head: "換成 3×3，一次燒到更多敵人",
    diff: () => [R(chip("shape", "square3", 16), "範圍", ["十字 5 格"], [term("square3"), "，9 格"], "up"), R(card("range"), term("range"), "4 格", "3 格", "down"), R(status("burning", 16), term("burning"), "5 回合", "3 回合", "down")],
    say: () => ["打中心和周圍一圈共 9 格；射程少 1 格，燃燒變 3 回合。"] };
  const OPT_SINGLE = { cat: "範圍", tpl: "converge_single", was: "收成單體：範圍收成一個目標，省下的預算全部換成威力（…）", head: "收成單體：只打中心那一個敵人，省下來的力氣全部換成更久的燃燒",
    diff: () => [R(chip("shape", "single", 16), "範圍", ["十字 5 格"], "單體 1 格", "down"), R(status("burning", 16), term("burning"), "5 回合", "8 回合", "up")],
    say: () => ["只打中心那一個敵人，但燃燒變成 8 回合。"] };
  const OPT_FOLLOW = { cat: "連段", tpl: "followup_hit", was: "接續段：命中後再接一小段傷害（6.23 複合技，傷害依預算調整）", head: "命中後再接一小段火焰傷害：中心那格的敵人會再受一次火焰傷害",
    diff: () => [R(card("damage"), "接續", null, ["1d4 火焰傷害", h("span.fc-when", {}, "（只打中心那格）")], "up", { isNew: true }), R(card("cooldown"), term("cooldown"), "2 回合", "3 回合", "cost")],
    say: () => ["打中後，對中心那格的敵人再補 1d4 火焰傷害；冷卻多 1 回合。"] };
  const OPT_FROST = { cat: "元素與關鍵字", tpl: "element_second", was: "加第二元素：多一段別種元素的傷害（傷害依預算調整）", head: "加上冰霜：多一段冰霜傷害，打到積水的格子還會結成冰面",
    diff: () => [R(card("damage"), "第二元素", null, "1d4 冰霜傷害", "up", { isNew: true }), R(status("burning", 16), term("burning"), "5 回合", "4 回合", "down")],
    say: () => ["多一段 1d4 冰霜傷害；燃燒變 4 回合。"] };
  // 第 3 次閃現（大變化）：加深、橋接＋轉型保底（轉型永遠排最後）。
  const OPT_EXTEND = { cat: "加深", tpl: "major_extend", was: "（大變化）延長", head: "燒得更久",
    diff: () => [R(status("burning", 16), term("burning"), "5 回合", "7 回合", "up"), R(card("cooldown"), term("cooldown"), "2 回合", "3 回合", "cost")],
    say: () => ["燃燒變成 7 回合；冷卻多 1 回合。"] };
  const OPT_PUSH = { cat: "橋接", tpl: "major_bridge_imbue", was: "（大變化）橋接撞擊", head: "打中時把敵人往外推 1 格，可以接撞擊",
    diff: () => [R(card("damage"), "效果", null, ["推開 1 格，", term("makes"), " ", kw("collision", 14), " ", term("collision")], "up", { isNew: true }), R(status("burning", 16), term("burning"), "5 回合", "4 回合", "down")],
    say: () => ["打中時把十字裡的敵人往外推 1 格，推去撞牆就會受撞擊傷害；燃燒變 4 回合。"] };
  const OPT_PASSIVE = { cat: "轉型", tpl: "to_passive_on_hit", was: "轉成被動：你的攻擊命中時，自動對被打中的敵人補上縮小版的這招", head: "變成被動：你的攻擊打中敵人時，自動補上縮小版的點燃斬",
    diff: () => [R(chip("skeleton", "passive", 16), "種類", "主動", term("passiveKind", "被動"), "up"), R(card("ap"), term("ap"), "2", "不用花", "up"), R(status("burning", 16), term("burning"), "5 回合", "2 回合", "down")],
    say: () => ["不用自己按、不花 AP；燃燒變 2 回合。"], unequip: ["skill_bloodlust", "skill_thorn_skin", "skill_ember_ward"] };

  const SETS = {
    base: { n: 1, opts: [OPT_RANGE, OPT_CHARGE, OPT_WATER, OPT_BUMP] },
    rows: { n: 1, zh: "一個選項多列前 → 後＋變弱", opts: [OPT_LIGHT, OPT_SQUARE, OPT_WATER, OPT_BUMP] },
    wrap: { n: 2, zh: "大標折兩行", opts: [OPT_SINGLE, OPT_FOLLOW, OPT_FROST, OPT_BUMP] },
    transform: { n: 3, zh: "第 3 次（大變化）＋轉型要卸下一招", opts: [OPT_EXTEND, OPT_SQUARE, OPT_PUSH, OPT_PASSIVE] },
  };
  const OPTS = SETS.base.opts;

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

  /** 「後」那一塊：四種樣式。代價前面掛第⑦批 HUD 警告三角；變弱前面掛向下小三角（CSS）；待資料後面掛「待資料／待規則」。 */
  function nowChip(now, cls, isNew, pend, icon) {
    return h("span.fc-now", { class: cls },
      cls === "cost" ? IP.ICON.warn(13) : cls === "down" ? h("i.fc-down") : null,
      isNew ? h("span.fc-newtag", {}, "新") : null,
      icon ?? null,
      h("span", {}, now),
      pend ? pendTag(pend) : null);
  }
  function diffRows(o) {
    const kids = [];
    for (const r of o.diff()) {
      kids.push(r.icon, h("span.fc-lab", {}, r.lab), h("span.fc-was", { class: r.was == null ? "none" : null }, r.was ?? "沒有"), h("span.fc-arrow", {}, "→"),
        h("span.fc-nows", {}, nowChip(r.now, r.cls, r.isNew), r.extra ? nowChip(r.extra.now, r.extra.cls, false, r.extra.pend, r.extra.icon) : null));
    }
    return h("div.fc-diffs", {}, kids);
  }
  /** 橫向排法（11-13，使用者：「閃現選擇畫面的新排法 可以是橫向嗎」）的前 → 後：卡寬只有約 100～160，一列拆成「欄位」與「前 → 後」兩段，
   *  放得下就同一行、放不下「前 → 後」整段換到下一行（「後」還放不下再換行）。四種樣式、圖示、字級和直向版同一套（nowChip）。 */
  function diffStack(o) {
    return h("div.fc-rdiffs", {}, o.diff().map((r) => h("div.fc-rdiff", {},
      h("span.k", {}, r.icon, h("span.fc-lab", {}, r.lab)),
      h("span.v", {}, h("span.wa", {}, h("span.fc-was", { class: r.was == null ? "none" : null }, r.was ?? "沒有"), h("span.fc-arrow", {}, "→")),
        nowChip(r.now, r.cls, r.isNew), r.extra ? nowChip(r.extra.now, r.extra.cls, false, r.extra.pend, r.extra.icon) : null))));
  }
  /** 橫向的大標斷行：卡窄（800 時字寬只有 5～7 個字），keep-all 遇到沒有空格的長句只能任意斷（「打中的格子還會積／水」「撞過／，」）。
   *  照 infoPanels.js wordBreaks 的做法用 Intl.Segmenter 切詞、詞間插 <wbr>；單字的詞併進下一個詞，標點黏在前一個詞後面，
   *  數字和單位之間的空格換成不斷行空格（「1 格」不拆）。字不變，只加斷點。 */
  const SEG = typeof Intl !== "undefined" && Intl.Segmenter ? new Intl.Segmenter("zh-Hant", { granularity: "word" }) : null;
  function headBreaks(text) {
    text = text.replace(/(\d) /g, "$1\u00a0");
    if (!SEG) return [text];
    const words = [];
    let carry = "";
    for (const { segment } of SEG.segment(text)) {
      if (/^[，、；：。！？）」\s\u00a0]+$/.test(segment) && words.length && !carry) { words[words.length - 1] += segment; continue; }
      if ([...segment].length === 1 && /\p{Script=Han}/u.test(segment)) carry += segment; else { words.push(carry + segment); carry = ""; }
    }
    if (carry) words.length ? (words[words.length - 1] += carry) : words.push(carry);
    return words.flatMap((w, i) => (i ? [h("wbr"), w] : [w]));
  }
  /** 選項卡：選中＝亮金框（描框只表示狀態）；卡本身不變大，選中的說明與「確定」在下固定區（點哪個都不跳）。 */
  function optCard(o, i, on, layout) {
    /* 橫向四張並排：由上而下＝單選圈＋大標（第二行起繞到單選圈底下）、類別標籤、前 → 後。數字與單位之間不斷行（字不變，只把空格換成不斷行空格） */
    if (layout === "row")
      return h("div.fc-opt", { class: on ? "on" : null, "data-opt": String(i + 1) },
        h("div.fc-opt-top.stack", {}, h("span.fc-radio"), h("span.fc-headline", {}, IP.newText(h("span", {}, headBreaks(o.head))))),
        h("div.fc-opt-cat", {}, IP.tag(o.cat === "轉型" ? "warn" : "", o.cat)),
        diffStack(o));
    /* 2×2（800 的建議版）：卡寬約 230，標頭照直向版（單選圈｜大標｜類別標籤靠右），前 → 後照橫向的疊法 */
    if (layout === "grid")
      return h("div.fc-opt", { class: on ? "on" : null, "data-opt": String(i + 1) },
        h("div.fc-opt-top", {}, h("span.fc-radio"), h("span.fc-headline", {}, IP.newText(h("span", {}, headBreaks(o.head)))), h("span.fc-cat", {}, IP.tag(o.cat === "轉型" ? "warn" : "", o.cat))),
        diffStack(o));
    return h("div.fc-opt", { class: on ? "on" : null, "data-opt": String(i + 1) },
      h("div.fc-opt-top", {}, h("span.fc-radio"), h("span.fc-headline", {}, IP.newText(o.head)), h("span.fc-cat", {}, IP.tag(o.cat === "轉型" ? "warn" : "", o.cat))),
      diffRows(o));
  }
  /** 轉型換到已滿的欄位時，要先選卸下哪一招（現行 RunFlashPending 的 unequip_candidates）：放在下固定區「確定」的上面。 */
  function unequipRow(ids, chosen, narrow) {
    return h("div.fc-unequip", {},
      h("span.k", {}, IP.newText(narrow ? "被動欄滿了，卸下一招：" : "被動欄 3 格滿了，選一招卸下（放回備用）：")),
      h("span.fc-unequip-list", {}, ids.map((id, i) => h("button", { type: "button", class: chosen === i + 1 ? "on" : null }, ownedIcon(id, narrow ? 18 : 20), SK[id].name))));
  }
  /** 下緣固定區：選中的白話說明＋確定。都沒選時提示先點一個、確定按不下去（同現行）。寬版多一張示意圖。 */
  function foot(set, pick, narrow, un) {
    const o = SETS[set].opts[pick - 1];
    const dia = !o || narrow ? null
      : o.dia === "range" ? h("div.fc-diagrams", {}, h("div.fc-dia", {}, rangeDia(4, false), h("span", {}, IP.newText("原本 4 格"))), h("div.fc-dia", {}, rangeDia(5, true), h("span", {}, IP.newText(h("span", {}, "變成 ", h("b", {}, "5 格"))))))
      : o.dia === "water" ? h("div.fc-diagrams", {}, h("div.fc-dia", {}, waterDia(), h("span", {}, IP.newText("打到的 5 格")))) : null;
    const ready = o && (!o.unequip || un > 0);
    const main = h("div.fc-foot-main", {},
      h("div.fc-say", {}, o ? [h("b.fc-picked", {}, IP.newText(o.head)), h("span", {}, "：", ...o.say())] : h("span.dim", {}, IP.newText("先點一個變化。點數已經扣了，一定要選一個。"))),
      dia,
      h("button.primary", { type: "button", disabled: ready ? null : true }, "確定"));
    return h("div.fc-foot", {}, o?.unequip ? unequipRow(o.unequip, un, narrow) : null, main);
  }

  // ---------------- 一屏（面板） ----------------
  // 上：固定區（標頭＋原技能列，只出現一次）；中：選項（捲動區）；下：固定區（選中的說明＋確定）。
  // 窄版（面板寬 < 560，800×600 的 493）：標題、技能名、已扣點數併成一行，「一定要選一個」收進 (i)；原技能列不再寫名字（標頭已有）；下緣不畫示意圖。
  // 面板高度＝「都沒選」與每個選項各自選中裡最高的那一次（11.4 第 8 條：點哪個都不跳框），不超過 popupBox 上限；
  // 放不下時選項區在面板內捲動，上下固定區不動，選中的那張捲到看得到。
  const SCREENS = [];
  const opts = (set, pick, layout) => h("div.fc-opts", {}, SETS[set].opts.map((o, i) => optCard(o, i, pick === i + 1, layout)));
  /** vw＝1600｜800；opt.set＝base｜rows｜wrap｜transform；opt.pick＝選中第幾個（0＝都沒選）；opt.un＝轉型卸下第幾招；opt.tip＝要畫出來的說明卡；opt.base＝「完整說明」打開。 */
  function screen(vw, opt = {}) {
    const box = opt.w ? { ...BOX[vw], w: opt.w } : BOX[vw], narrow = box.w < 560, set = opt.set ?? "base", nth = SETS[set].n;
    opt = { ...opt, narrow, set, un: opt.un ?? 0, layout: opt.layout ?? "col", box };
    OPEN_TIP = opt.tip ?? null;
    const x = h("button.ip-x", { type: "button", "aria-label": "關閉" }, "×");
    const must = IP.newText("一定要選一個。選哪個這招整體都會強一點，標 ▼ 的是拿來換的"); /* 決定 3 的建議字（複審） */
    const fixed = h("div.ip-fixed", {},
      narrow
        ? h("div.fc-head", {}, h("h2.fc-title", {}, IP.ICON.bulb(18), "靈感閃現"), h("span.fc-sub.inline", {}, IP.newText(`「點燃斬」第 ${nth} 次`), IP.tag("open", "已扣 1 點"), IP.tip(must, { open: opt.tip === "must", right: true })), x)
        : h("div", {}, h("div.fc-head", {}, h("h2.fc-title", {}, IP.ICON.bulb(20), "靈感閃現", h("small", {}, IP.newText("選一個變化"))), x),
          h("div.fc-sub", {}, IP.newText(`「點燃斬」第 ${nth} 次閃現`), IP.tag("open", "已扣 1 點"), h("span", {}, must))),
      baseStrip(opt));
    const body = h("div.ui-popup-body", {}, opts(set, opt.pick, opt.layout));
    const ft = foot(set, opt.pick, narrow, opt.un);
    const panel = h("div.ui-popup.rt-frame.ui-popup-hud.world-hud-panel.ip-hudpanel", { "data-popup": "hud", class: [narrow ? "fc-narrow" : "", opt.layout !== "col" ? "fc-lay-" + opt.layout : ""].join(" ").trim() || null }, fixed, body, ft);
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
  /** 頁面 load 後量高度：「都沒選」與每個各自選中（下緣固定區的字數不同；轉型多一列卸下選單）輪流量，取最高的定面板高；選中的那張捲到看得到。 */
  function finish() {
    for (const s of SCREENS) {
      const { wrap, body, rail, meter, opt, vw } = s;
      let { ft } = s;
      const panel = body.parentElement, keepBody = [...body.childNodes], keepFt = ft, n = SETS[opt.set].opts.length;
      const frame0 = () => wrap.getBoundingClientRect().height - body.clientHeight;
      let footMax = 0;
      const need = Array.from({ length: n + 1 }, (_, k) => { body.replaceChildren(opts(opt.set, k, opt.layout)); const f = foot(opt.set, k, opt.narrow, opt.un); panel.replaceChild(f, ft); ft = f; footMax = Math.max(footMax, f.getBoundingClientRect().height); return Math.ceil(frame0() + usedHeight(body) + 12); });
      panel.replaceChild(keepFt, ft); ft = keepFt; body.replaceChildren(...keepBody);
      ft.style.minHeight = Math.ceil(footMax) + "px"; /* 下固定區固定高（字數不同也不動分隔線） */
      const B = opt.box, hh = Math.min(B.h, Math.max(...need));
      wrap.style.height = hh + "px";
      const ch = body.clientHeight, used = usedHeight(body), over = used > ch + 1;
      body.dataset.overflow = over ? "1" : "0";
      if (opt.pick && over) {
        const el = body.querySelector(`[data-opt="${opt.pick}"]`), top = offsetIn(body, el), bottom = top + el.offsetHeight;
        /* 複審：捲到整張卡與下框都露出下緣漸隱區（多留約 20px）；捲得到底時直接捲到底、標 data-end（漸隱色塊收掉）。遊戲端：scrollIntoView＋一段留白 */
        if (bottom > body.scrollTop + ch - 20) {
          const want = Math.min(top - 6, bottom - ch + 44);
          if (want >= body.scrollHeight - ch - 40) { body.dataset.end = "1"; body.scrollTop = body.scrollHeight; } else body.scrollTop = want;
        }
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
      /* 每張選項卡的大標折幾行（壓力情況 wrap 用） */
      const lines = [...body.querySelectorAll(".fc-headline")].map((e) => Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)));
      const fx = Math.round(s.fixed.getBoundingClientRect().height + 18), fb = Math.round(ft.getBoundingClientRect().height);
      const cards = [...body.querySelectorAll(".fc-opt")].map((e) => Math.round(e.getBoundingClientRect().width));
      const cardH = [...body.querySelectorAll(".fc-opt")].map((e) => Math.round(e.getBoundingClientRect().height));
      s.result = { w: B.w, h: hh, fixed: fx, foot: fb, visible: ch, content: used, over, scrolled: Math.round(body.scrollTop), lines, need, layout: opt.layout, cards, cardH };
      meter.innerHTML = `${B.zh}：面板 <b>${B.w}×${hh}</b>（上限 ${B.h}；高＝都沒選與各自選中裡最高的那次：${need.join("／")}）；` +
        `上固定區 <b>${fx}</b>（含上緣 18）、下固定區 <b>${fb}</b>；選項區可視 <b>${ch}</b>、內容 <b>${used}</b> px` +
        (over ? `＝<b class="bad">${(used / ch).toFixed(2)} 屏，選項區在面板內捲動</b>（捲了 ${Math.round(body.scrollTop)} px；上下固定區不動）` : `＝<b class="ok">一屏放得下</b>`) +
        `；大標行數 ${lines.join("／")}` +
        (opt.layout !== "col" ? `；卡寬 ${cards.join("／")}、卡高 ${cardH.join("／")}` : "");
    }
    document.documentElement.dataset.results = JSON.stringify(SCREENS.map((s) => ({ set: s.opt.set, vw: s.vw, pick: s.opt.pick ?? 0, ...s.result })));
  }

  return { BOX, SETS, OPTS, T, screen, finish, term, skillIcon, card, status, kw, part, chip, nowChip, diffRows, rangeDia, waterDia, R };
})();
