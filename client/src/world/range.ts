// 工坊靶場（Phase TR-1，#134；OB-5，#150；21 21.5、06 6.27.3）的畫面邏輯：模式、武器架分組、「看示範」要送哪些關鍵字、
// 選到一半的草稿、畫面上的字。規則全部在伺服器（`trpg.world.opening`）：這裡只決定畫面怎麼排、送什麼。
// 文字照玩法 PM 定稿（台詞-OB5與PR2定稿）；招名、武器名、地名一律從伺服器讀，這裡不寫死技能 ID、招名或地名。
import type { RangeView, SkillCard, StartWeaponOption } from "../api/types";

export const CLASS_LABELS: Record<string, string> = { melee: "近戰", ranged: "遠程", focus: "法器" };
/** 大類卡標題旁的一句定位（取自守印人的話「想貼身打、遠遠射，還是施法？」）。 */
export const CLASS_TAGS: Record<string, string> = { melee: "貼身打", ranged: "遠遠射", focus: "施法" };

/** 沙盒說明（選大類、正式選定兩頁共用；玩法 PM 補定）。 */
export const SANDBOX_NOTE = "靶場是沙盒：不算勝負，不耗任何資源，也沒有經驗與掉落。";
export const LOAN_NOTE = "入門配備是借的，正式選定時會換成你自己的。";
export const RACK_NOTE = "架上的武器都能先拿起來試打；確定出發只記你選的大類。";
export const CONFIRM_EMPTY = "先選一條路，才能出發。";
export const CONFIRM_LABEL = "確定出發";
export const CHOOSE_LABEL = "確定選這套";
export const CHOOSE_LATER = "之後再選";
/** 按了「之後再選」之後，世界畫面頂列再打開「正式選定」的那顆鈕。 */
export const CHOOSE_OPEN_LABEL = "正式選定武器與關鍵字";
export const TRY_LABEL = "拿起試打";
export const DEMO_LABEL = "看示範";
export const REC_LABEL = "推薦";
export const KEYWORD_NOTE = "每個關鍵字給 1 招起始技能，都能先「看示範」。";
export const REC_NOTE = "「推薦」是照你前兩場用得最多的招標的，不照著選也可以。";
export const ATTR_NOTE = "確定後，屬性點會照這把武器的推薦配法重新配好。";
/** 等伺服器計算（正式選定、三選一出題）時的提示。 */
export const CHOOSE_WAIT = "正在照你的選擇準備起始技能與三選一，稍等一下……";

// ---- OB-6：4 級前的免費重選（重選頁與確認彈窗的字是實作者暫寫，列在共用筆記「暫定字串-OB6」給玩法 PM 定稿） ----
/** 葛蘭面板、主城靶場面板上開重選頁的鈕。 */
export const RESELECT_PANEL_LABEL = "重選";
/** 人在能重選的地方時，世界畫面頂列開重選頁的鈕。 */
export const RESELECT_OPEN_LABEL = "重選武器與關鍵字";
export const RESELECT_HEADING = "重選";
export const RESELECT_LABEL = "確定重選";
export const RESELECT_LATER = "先不換";
export const RESELECT_CONFIRM_TITLE = "確定要重選嗎？";
export const RESELECT_CONFIRM_GO = "確定，換這套";
export const RESELECT_CONFIRM_BACK = "再想想";
export const RESELECT_ONCE = "免費重選只有這一次，換了就不能再換回來。";
export const RESELECT_WAIT = "正在照你的選擇換武器與起始技能，稍等一下……";

/** 重選頁標題牌的副標：「{地方}・換一次武器與 2 個關鍵字」（地方由伺服器給）。 */
export function reselectPlaqueSub(place: string, count: number): string {
  return `${place === "" ? "" : `${place}・`}換一次武器與 ${count} 個關鍵字`;
}

type Reselect = NonNullable<RangeView["reselect"]>;

/** 任務欄小牌（Q6）：還有重選資格（伺服器的 `window_open`）就顯示，不管人在哪；數字讀 `before_level`，前端不比等級。 */
export function reselectBadge(reselect: Reselect | null | undefined): string | null {
  if (reselect == null || reselect.window_open !== true) return null;
  return `${reselect.before_level} 級前可重選一次`;
}

/**
 * OB-6c：任務欄收合時，收合鈕（捲軸圖示）右上的提醒點。小牌會顯示的期間（`reselectBadge` 不是 `null`）且收合時才有；
 * 沿用功能列的通知點（`world-hud-dot red`）。回傳滑過的字（＝小牌的字）；沒有點時回 `null`。
 */
export function trackerFoldDot(reselect: Reselect | null | undefined, collapsed: boolean): string | null {
  return collapsed ? reselectBadge(reselect) : null;
}

/** 小牌的說明卡：去哪裡重選（伺服器給的地點句）＋只有一次。 */
export function reselectBadgeHint(reselect: Reselect): string {
  const place = reselect.place_zh ?? "";
  return `${place === "" ? "" : `${place}。`}可以換武器與 2 個關鍵字，但只有這一次。`;
}

/** 確認彈窗要列的項目：會收回的招、起始武器本體收不收、材料不退的改動（伺服器原句）、只有這一次。全部來自資料。 */
export function reselectConfirmLines(reselect: Reselect, weaponZh: string): string[] {
  const out: string[] = [];
  const returned = reselect.returned_zh ?? [];
  if (returned.length > 0) out.push(`會收回的招：${returned.join("、")}`);
  out.push(reselect.weapon_returned ? `會收回起始武器${weaponZh === "" ? "" : `「${weaponZh}」`}` : "起始武器已經不在身上：不收回，也不扣錢");
  for (const line of reselect.lost_zh ?? []) out.push(line);
  out.push(RESELECT_ONCE);
  return out;
}

/** 點這個 NPC 或情境物件的面板上要不要放「重選」鈕（伺服器給的導師 NPC、主城的靶場與工坊師傅；能重選時才放）。 */
export function opensReselect(reselect: Reselect | null | undefined, target: { npc?: string; object?: string }): boolean {
  if (reselect == null || !reselect.available) return false;
  if (target.npc !== undefined) return reselect.in_capital !== true && reselect.npc === target.npc;
  if (target.object !== undefined) return reselect.in_capital === true && (reselect.objects ?? []).includes(target.object);
  return false;
}

/**
 * 靶場畫面的模式（OB-5）：`class`＝選大類（整頁，未完成開局）；`choose`＝正式選定（葛蘭或主城開的整頁）；
 * `reselect`＝4 級前的免費重選（OB-6：現在可以重選；**不自動開**，由面板與頂列的鈕打開）；`null`＝沒有靶場畫面可開。
 */
export type RangeMode = "class" | "choose" | "reselect";

export function rangeMode(range: RangeView | null | undefined): RangeMode | null {
  if (range == null) return null;
  if (range.stage === "pick_class") return "class";
  if (range.stage === "starter") return range.choice?.available === true ? "choose" : null;
  return range.reselect?.available === true ? "reselect" : null;
}

/** 「正式選定」整頁的開關：`auto`＝伺服器說可以選定（教學 `choose`）、還沒自動開過就開一次；`closed`＝玩家按了「之後再選」；`open`＝玩家點
 * 葛蘭或主城靶場再打開。 */
export type ChoosePage = "auto" | "closed" | "open";

/** 自動打開過「正式選定」整頁的紀錄（記在角色的提示紀錄 `hints.seen`，不升存檔格式）。 */
export const CHOOSE_AUTO_SEEN = "lesson:choose";

/** 玩家自己打開的（頂列的鈕、點葛蘭或主城靶場；自動打開的那一次也會轉成 `open`）。 */
export function choosePageShown(page: ChoosePage): boolean {
  return page === "open";
}

/** 要不要自動打開：只在可以選定後**第一次**回到霧渡鎮或主城時開一次（玩法 PM 決定）；開過（有紀錄）就不再自動開。 */
export function chooseAutoOpens(page: ChoosePage, lessonChoose: boolean, seen: ReadonlySet<string>): boolean {
  return page === "auto" && lessonChoose && !seen.has(CHOOSE_AUTO_SEEN);
}

/** 「選定完成」那句話的彈窗還開著時，三選一先不出（美術 M5：先出話，按「好」之後才開三選一）。 */
export function holdOffer<T extends string | null, F>(pane: T, dialogOpen: boolean, fallback: F): T | F {
  return dialogOpen && pane === "offer" ? fallback : pane;
}

/** 點這個 NPC 或情境物件會不會打開「正式選定」整頁（伺服器給的導師 NPC、主城的靶場與工坊師傅）。 */
export function opensChoose(choice: RangeView["choice"] | undefined, target: { npc?: string; object?: string }): boolean {
  if (choice == null || !choice.available) return false;
  if (target.npc !== undefined) return !choice.in_capital && choice.npc === target.npc;
  if (target.object !== undefined) return choice.in_capital && (choice.objects ?? []).includes(target.object);
  return false;
}

/** 選大類的標題牌副標（玩法 PM 補定「工坊靶場・先挑一條路」：標題「工坊靶場」＋副標這一句，不寫地名）。 */
export const CLASS_PLAQUE_SUB = "先挑一條路";

/** 正式選定的標題牌副標：「{地方}・選你自己的武器與 2 個關鍵字」（地方由伺服器給：霧渡鎮導師堂／{主城地名}工坊靶場）。 */
export function choosePlaqueSub(place: string, count: number): string {
  return `${place === "" ? "" : `${place}・`}選你自己的武器與 ${count} 個關鍵字`;
}

/** 試打戰鬥右上的地名：「{主城地名}・工坊靶場」。主城地名：開局試打讀 `RangeView.capital_zh`、靶場試玩讀 `WorkshopView.capital_zh`。 */
export function rangePlaceName(capital: string | null | undefined): string {
  return capital == null || capital === "" ? "工坊靶場" : `${capital}・工坊靶場`;
}

// ---- PR-2b（#147）：靶場的兩種戰鬥（開局試打、工坊師傅的「靶場試玩」） ----

/** `trial`＝選大類、正式選定、重選畫面的「拿起試打」「看示範」（打完回靶場整頁）；`practice`＝工坊師傅的靶場試玩（打完回主城）。 */
export type RangeFight = "trial" | "practice";

/** 開局試打的離開鈕（維持原字）。 */
export const TRIAL_EXIT_LABEL = "回到靶場";
/** 靶場試玩的離開鈕（玩法 PM 定稿：只用在工坊師傅入口）。 */
export const PRACTICE_EXIT_LABEL = "離開靶場";

export function rangeExitLabel(kind: RangeFight): string {
  return kind === "practice" ? PRACTICE_EXIT_LABEL : TRIAL_EXIT_LABEL;
}

/** 戰鬥右上的地名：靶場試玩讀師傅選單的主城地名，開局試打讀靶場畫面的。 */
export function rangeFightPlace(kind: RangeFight, view: { opening?: Pick<RangeView, "capital_zh"> | null; workshop?: { capital_zh: string } | null } | null | undefined): string {
  return rangePlaceName(kind === "practice" ? view?.workshop?.capital_zh : view?.opening?.capital_zh);
}

/**
 * 開場訊息（標題＋沙盒說明）。開局試打的標題照 OB-5 定稿「靶場試打：{武器}＋{招 1}、{招 2}」（看示範比照）：伺服器的 `title_zh`
 * 只到武器，這裡接上 `skills_zh`；靶場試玩的標題就是「靶場試玩：{武器}」（技能是玩家自己的整列，不接）。
 */
export function rangeFightNotes(kind: RangeFight, res: { title_zh: string; skills_zh: readonly string[] }): string[] {
  const title = kind === "trial" && res.skills_zh.length > 0 ? `${res.title_zh}＋${res.skills_zh.join("、")}` : res.title_zh;
  return [title, SANDBOX_NOTE];
}

/** 招式的代價一行（「AP 2・耐力 10」）：卡上不寫冷卻與每場次數（樣張）。 */
export function costLine(card: SkillCard): string {
  return (card.stats.costs ?? [])
    .filter((c) => c.kind !== "cooldown" && c.kind !== "uses_per_battle")
    .map((c) => `${c.unit} ${c.label}`.trim())
    .join("・");
}

const names = (skills: readonly SkillCard[]): string => skills.map((s) => s.name_zh).join("、");

/** 武器卡的「試打用…」一行。`starter`＝選大類（入門招）；否則是正式選定（示範招、測試模式）。 */
export function trialNote(classZh: string, skills: readonly SkillCard[], starter: boolean): string {
  return starter
    ? `試打用：普攻＋${classZh}入門招 ${names(skills)}。試別把武器不會改掉你選的大類。`
    : `試打用：普攻＋${classZh}示範招 ${names(skills)}（測試模式，不耗任何資源）。`;
}

/** 確認列（已選）：粗體的「已選：{大類}」與後半「{入門武器}＋{招 1}、{招 2}。」。 */
export function confirmParts(classZh: string, weaponZh: string, skills: readonly SkillCard[]): [string, string] {
  return [`已選：${classZh}`, `${weaponZh}＋${names(skills)}。`];
}

/** 正式選定窄版黏底列的一行：「手上：{武器}」與「已選 {n}/{count}：{關鍵字}」。 */
export function chooseBarParts(weaponZh: string, picked: readonly string[], count: number): [string, string] {
  return [`手上：${weaponZh === "" ? "還沒拿武器" : weaponZh}`, `已選 ${picked.length}/${count}${picked.length > 0 ? `：${picked.join("、")}` : ""}`];
}

/** 關鍵字列的狀態（樣張四種：推薦且已選、推薦未選、已選非推薦、一般）。 */
export function keywordState(on: boolean, recommended: boolean): "rec-sel" | "rec" | "sel" | "plain" {
  if (recommended) return on ? "rec-sel" : "rec";
  return on ? "sel" : "plain";
}

export interface Rack {
  weaponClass: string;
  name: string;
  weapons: StartWeaponOption[];
}

/** 武器架：照伺服器給的大類順序（近戰、遠程、法器）把可選的武器分組；沒列到的大類接在最後。 */
export function groupRacks(weapons: readonly StartWeaponOption[], order: readonly string[]): Rack[] {
  const classes = [...order, ...weapons.map((w) => w.weapon_class).filter((c) => !order.includes(c))];
  const seen = new Set<string>();
  const out: Rack[] = [];
  for (const cls of classes) {
    if (seen.has(cls)) continue;
    seen.add(cls);
    const list = weapons.filter((w) => w.weapon_class === cls);
    if (list.length > 0) out.push({ weaponClass: cls, name: CLASS_LABELS[cls] ?? cls, weapons: list });
  }
  return out;
}

/** 「看示範」要送的關鍵字（依序給起始技能，伺服器最多收 `count` 個）：已選的就看已選的那組；沒選的接在已選的後面
 * （選滿了就換掉第 2 個），看到的招就是「改選它」時會拿到的那招。 */
export function demoKeywords(selected: readonly string[], keyword: string, count: number): string[] {
  if (selected.includes(keyword)) return [...selected];
  if (selected.length < count) return [...selected, keyword];
  return [...selected.slice(0, count - 1), keyword];
}

export interface RangeDraft {
  weapon: string;
  keywords: string[];
}

const DRAFT_PREFIX = "trpg.rangeDraft.";
const CLASS_DRAFT_PREFIX = "trpg.rangeClassDraft.";

function readJson(key: string): Record<string, unknown> | null {
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) return null;
    const data: unknown = JSON.parse(raw);
    return typeof data === "object" && data !== null ? (data as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function writeJson(key: string, value: unknown): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // 私密視窗或封鎖儲存：不記草稿，照樣能選
  }
}

/** 選到一半的武器與關鍵字（中途離開、去試打回來時接著選；只是本機的方便，伺服器不記）。讀不到時 `null`。 */
export function readDraft(characterId: string): RangeDraft | null {
  const data = readJson(DRAFT_PREFIX + characterId);
  if (data === null) return null;
  const { weapon, keywords } = data;
  if (typeof weapon !== "string" || !Array.isArray(keywords)) return null;
  return { weapon, keywords: keywords.filter((k): k is string => typeof k === "string") };
}

export function writeDraft(characterId: string, draft: RangeDraft | null): void {
  writeJson(DRAFT_PREFIX + characterId, draft);
}

/** 選大類畫面的草稿（去試打回來時接著選）：選的大類、武器架有沒有打開、架上點的那一把。 */
export interface ClassDraft {
  picked: string | null;
  rackOpen: boolean;
  rackWeapon: string;
}

export function readClassDraft(characterId: string): ClassDraft | null {
  const data = readJson(CLASS_DRAFT_PREFIX + characterId);
  if (data === null) return null;
  const { picked, rackOpen, rackWeapon } = data;
  return { picked: typeof picked === "string" ? picked : null, rackOpen: rackOpen === true, rackWeapon: typeof rackWeapon === "string" ? rackWeapon : "" };
}

export function writeClassDraft(characterId: string, draft: ClassDraft | null): void {
  writeJson(CLASS_DRAFT_PREFIX + characterId, draft);
}
