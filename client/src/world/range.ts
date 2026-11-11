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

/**
 * 靶場畫面的模式（OB-5）：`class`＝選大類（整頁，未完成開局）；`choose`＝正式選定（葛蘭或主城開的整頁）；
 * `reselect`＝4 級前的免費重選（OB-6 才有畫面，這裡先留位置）；`null`＝沒有靶場畫面可開。
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

/** 試打戰鬥右上的地名：「{主城地名}・工坊靶場」。 */
export function rangePlaceName(capital: string | null | undefined): string {
  return capital == null || capital === "" ? "工坊靶場" : `${capital}・工坊靶場`;
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
