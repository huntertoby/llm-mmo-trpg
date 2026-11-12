// 網遊式 HUD 版面 A（Phase 6B-5；docs/archive/art/HUD移植需求.md、HUD版面.md 第 1、2 節）的純函式：
// 功能列與快捷鍵、單一浮動面板的開關、時間天氣換算、限制提示、任務追蹤、隊友卡、浮動提示、小地圖、
// 四角版面（以 1040×624 為基準等比縮放）、出口附近的半透明判定與排版煙霧檢查。
// 只用在大世界的城鎮與野外（有實地地圖 `WorldView.field` 時）；戰鬥與 roguelite 不用。
import type { FieldView, NpcPortrait, WorldView } from "../api/types";
import { TOAST_FADE_MS, TOAST_MAX, TOAST_TTL_MS } from "../battle/logToasts";
import { TILE_SIZE } from "../battle/geometry";
import { stagePixels, topReserve } from "../battle/elevation";
import { sortQuests } from "./story";
import { growthBadge } from "./growth";

// ---------------- 功能列、面板、快捷鍵 ----------------

/** 浮動面板（同時只開一個）。前 6 個是功能列的；`place`＝點地名條開的「這裡」（服務、這裡的人）；
 * `shop`、`smithy`、`board`、`league` 是走到設施旁邊互動時開的現有畫面；`npc`（一位 NPC 的對話）、`hire`（雇用）、
 * `friend`（朋友的名片）是 6B-4 走到人或櫃檯旁邊開的面板（對象另外記）。 */
export type HudPanel =
  | "bag"
  | "skills"
  | "growth"
  | "quests"
  | "shadow"
  | "notes"
  | "place"
  | "shop"
  | "smithy"
  | "board"
  | "league"
  | "npc"
  | "hire"
  | "friend"
  /** 情境物件的說明卡（6C-5；對象另外記）。 */
  | "object"
  /** 主城的橋頭石碑：該區的傳送選單（6D-5；區域另外記）。 */
  | "stele"
  /** 主城的整備亭：休息、換技能、配點、換裝（6D-5）。 */
  | "pavilion"
  /** 郵寄（6T-1b）：走到郵差或郵筒旁邊開。 */
  | "mail"
  /** PR-2（#147）：主城工坊師傅的選單（靶場試玩、改造技能；`WorldView.workshop`，對象＝師傅的情境物件 ID）。 */
  | "workshop";

export type HudButtonId = "bag" | "skills" | "growth" | "quests" | "shadow" | "notes" | "sneak";

export interface HudButton {
  id: HudButtonId;
  /** 快捷鍵（小寫）。 */
  key: string;
  name: string;
  /** 打開的面板；`null`＝不是面板（潛行 6C-5：按了就送 `sneak`）。 */
  panel: HudPanel | null;
}

/** 底部功能列 7 個圖示（Phase6計畫.md 0.4：第 7 個「趕路」改成「潛行」；快捷鍵 I K G J Y N R）。 */
export const HUD_BUTTONS: readonly HudButton[] = [
  { id: "bag", key: "i", name: "背包", panel: "bag" },
  { id: "skills", key: "k", name: "技能", panel: "skills" },
  { id: "growth", key: "g", name: "成長", panel: "growth" },
  { id: "quests", key: "j", name: "任務", panel: "quests" },
  { id: "shadow", key: "y", name: "影子", panel: "shadow" },
  { id: "notes", key: "n", name: "留言", panel: "notes" },
  { id: "sneak", key: "r", name: "潛行", panel: null },
];

/** 地圖鈕（M）：區域圖（6C-6；只能看，站在傳送石上或在城鎮裡可以點傳送石）。 */
export const MAP_KEY = "m";

/** 還沒開放的功能按了之後的提示。 */
export const NOT_OPEN_ZH = "尚未開放";

/**
 * 戰鬥畫面與可走動畫面已經用掉的鍵（查 `screens/battle/useBattleKeys.ts`、`ui/useFloatCard.tsx`、
 * `ui/BattleLogDock.tsx`、`world/WorldField.tsx`）：Esc、Shift、Tab、Enter、空白鍵、方向鍵、WASD、E。
 * HUD 的快捷鍵不能和這些重複（測試檢查）。
 */
export const RESERVED_KEYS: readonly string[] = ["escape", "shift", "tab", "enter", " ", "arrowup", "arrowdown", "arrowleft", "arrowright", "w", "a", "s", "d", "e"];

export type HudKey = { kind: "button"; id: HudButtonId } | { kind: "map" } | { kind: "escape" };

/** 鍵盤事件 → HUD 動作；有修飾鍵、在輸入框裡打字、不是 HUD 的鍵時為 `null`。 */
export function hudKey(e: { key: string; ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean; shiftKey?: boolean }, typing = false): HudKey | null {
  if (e.key === "Escape") return { kind: "escape" };
  if (e.ctrlKey === true || e.metaKey === true || e.altKey === true || typing) return null;
  const k = e.key.toLowerCase();
  if (e.shiftKey === true && k === "m") return null; // Shift＋M 是全部靜音（AU-1，`audio/index.ts`），不開地圖
  if (k === MAP_KEY) return { kind: "map" };
  const btn = HUD_BUTTONS.find((b) => b.key === k);
  return btn === undefined ? null : { kind: "button", id: btn.id };
}

/** 再按一次同一個面板＝關掉；按別的＝換成那個（同時只開一個）。 */
export function togglePanel(current: HudPanel | null, clicked: HudPanel): HudPanel | null {
  return current === clicked ? null : clicked;
}

/** 大世界 HUD 上的三種彈窗：設定面板（齒輪）、功能列等開的面板（背包、技能……）、區域圖／大世界圖。 */
export type HudPopup = "settings" | "panel" | "map";

/**
 * 同一時間只開一個彈窗（UI-E1b，UI-E1 待決 6 定案）：開 `opening` 時要關掉哪些已開的。
 * 面板在閃現、三選一待選時鎖住（`panelLocked`），不能關，所以不在清單裡（設定照常可以開在上面）。
 */
export function popupsToClose(opening: HudPopup, open: Readonly<Record<HudPopup, boolean>>, panelLocked = false): HudPopup[] {
  return (["settings", "panel", "map"] as const).filter((p) => p !== opening && open[p] && !(p === "panel" && panelLocked));
}

/** 面板能不能開（沒有資料的面板開不了；商店、鐵匠離開設施就關）。 */
export function panelAvailable(view: WorldView, panel: HudPanel): boolean {
  switch (panel) {
    case "bag":
      return view.inventory != null;
    case "shop":
      return view.shop != null;
    case "smithy":
      return view.crafting != null;
    case "shadow":
      return view.party != null || view.my_shadow != null;
    case "hire":
      return view.party != null;
    case "mail":
      return view.mail != null;
    case "workshop":
      return view.workshop != null; // PR-2：伺服器只在主城（有靶場內容）時給
    default:
      return true;
  }
}

/** 實際要畫的面板：閃現待選、任務三選一待選時固定顯示（不能關）；否則照玩家開的（開不了＝不畫）。 */
export function shownPanel(view: WorldView, open: HudPanel | null): HudPanel | "pending" | "offer" | null {
  if (view.pending_flash != null) return "pending";
  if (view.pending_offer != null) return "offer";
  if (open === null || !panelAvailable(view, open)) return null;
  return open;
}

/** 功能列圖示右上角的數字或點：成長有點數時紅點、任務是進行中的數量、影子有戰報時紫點。 */
export function buttonBadge(view: WorldView, id: HudButtonId): { text: string; tone: "red" | "purple" | "count" } | null {
  if (id === "growth") return growthBadge(view) !== "" ? { text: "", tone: "red" } : null;
  if (id === "quests") {
    const n = (view.quests ?? []).filter((q) => !q.done).length;
    return n > 0 ? { text: String(n), tone: "count" } : null;
  }
  if (id === "shadow") return (view.my_shadow?.reports_zh ?? []).length > 0 ? { text: "", tone: "purple" } : null;
  return null;
}

/** 功能列按鈕的狀態（docs/art/HUD功能列圖示.md 第 2 節；滑過由 CSS 處理）：
 * `open` 面板開著、`disabled` 面板沒有資料開不了（例：還沒存影子）、`normal` 其餘。 */
export type HudButtonState = "normal" | "open" | "disabled";

export function buttonState(view: WorldView, b: HudButton, openPanel: string | null): HudButtonState {
  if (b.id === "sneak") {
    const s = sneakState(view);
    return s.active ? "open" : s.problem === null ? "normal" : "disabled";
  }
  if (b.panel === null) return "normal";
  if (openPanel === b.panel) return "open";
  return panelAvailable(view, b.panel) ? "normal" : "disabled";
}

/** 滑過說明卡（HUD功能列圖示.md 第 3 節）：第二行目前狀態、第三行說明一句。 */
export interface HudButtonCard {
  status: string;
  desc: string;
}

export const HUD_TOUCH_ZH = "觸控：長按 0.4 秒看這張；點一下就打開";

export function hudButtonCard(view: WorldView, id: HudButtonId): HudButtonCard {
  switch (id) {
    case "bag": {
      const inv = view.inventory;
      const gold = (view.wallet?.gold ?? 0).toLocaleString("en-US");
      const slots = inv != null && typeof inv.slots_used === "number" ? `${inv.slots_used} / ${inv.slots_max} 格・` : "";
      return { status: inv == null ? "背包還沒打開過" : `${slots}金幣 ${gold}`, desc: "裝備、道具與腰包；在這裡換裝備" };
    }
    case "skills":
      return { status: `角色階級 ${view.character.skill_tier ?? 1}`, desc: "看技能卡與裝備的技能" };
    case "growth": {
      const badge = growthBadge(view);
      return { status: badge === "" ? "沒有可以花的點" : badge, desc: "花屬性點與靈感，讓角色成長" };
    }
    case "quests": {
      const n = (view.quests ?? []).filter((q) => !q.done).length;
      return { status: n > 0 ? `進行中 ${n} 條` : "沒有進行中的任務", desc: "任務與線頭；點一條可以追蹤" };
    }
    case "shadow": {
      const reports = (view.my_shadow?.reports_zh ?? []).length;
      if (!panelAvailable(view, "shadow")) return { status: "還沒存影子", desc: "你的影子在別人世界的動態" };
      return { status: reports > 0 ? `新戰報 ${reports} 則` : "沒有新戰報", desc: "你的影子在別人世界的動態" };
    }
    case "notes":
      return { status: view.here.name_zh, desc: "看別人留在這裡的留言，也可以留一則" };
    case "sneak": {
      const s = sneakState(view);
      return { status: s.status, desc: "壓低身形、放輕腳步：到下一張地圖為止，敵人的視野減半" };
    }
  }
}

/** 潛行鈕（R，6C-5）的狀態：潛行中、能不能開、說明。 */
export interface SneakState {
  active: boolean;
  /** 不能開的原因；可以開（或已經在潛行）為 `null`。 */
  problem: string | null;
  status: string;
}

export function sneakState(view: WorldView): SneakState {
  const field = view.field;
  if (field == null) return { active: false, problem: "這裡沒有實地地圖", status: "這裡沒有實地地圖" };
  if (field.sneaking === true) return { active: true, problem: null, status: "潛行中（到下一張地圖為止）" };
  const problem = field.sneak_problem_zh ?? null;
  return { active: false, problem, status: problem ?? `花 ${field.sneak_cost ?? 1} 補給` };
}

// ---------------- 時間、天氣、限制 ----------------

export interface DayPart {
  /** 一個字：早、午、晚、夜。 */
  char: string;
  icon: "sun" | "moon";
}

/**
 * 白天／夜晚一律照伺服器的 `day_phase`（6F-1：和遇敵卡、事件同一個來源；伺服器 06:00～18:00 是白天），
 * 時刻只決定同一個時段裡的字：白天＝早（11 點前）、午；夜晚＝晚（21 點前）、夜。讀不懂時刻時白天「午」、夜晚「夜」。
 */
export function dayPart(clock: { time_zh: string; day_phase: "day" | "night" }): DayPart {
  const m = /^(\d{1,2}):(\d{2})/.exec(clock.time_zh);
  const h = m === null ? null : Number(m[1]) % 24;
  if (clock.day_phase === "day") return { char: h !== null && h < 11 ? "早" : "午", icon: "sun" };
  return { char: h !== null && h >= 18 && h < 21 ? "晚" : "夜", icon: "moon" };
}

export interface WeatherMark {
  char: string;
  icon: "clear" | "rain" | "fog" | "snow" | "wind" | "night";
}

/** 天氣名稱 → 一個字與圖示（晴朗→晴、下雨→雨、濃霧→霧；其他取第一個字）。 */
export function weatherMark(weather: string): WeatherMark {
  if (weather.includes("雨")) return { char: "雨", icon: "rain" };
  if (weather.includes("霧")) return { char: "霧", icon: "fog" };
  if (weather.includes("雪")) return { char: "雪", icon: "snow" };
  if (weather.includes("風")) return { char: "風", icon: "wind" };
  // 6F-1：「夜晚」天氣＝晚上沒有雨霧（晴夜）；時段欄已經寫「晚／夜」，天氣欄寫「晴」配夜晚圖示，不重複
  if (weather.includes("夜")) return { char: "晴", icon: "night" };
  if (weather.includes("晴")) return { char: "晴", icon: "clear" };
  return { char: [...weather][0] ?? "？", icon: "clear" };
}

/** 「天氣・時段」一行（6F-1）：天氣是「夜晚」（晴夜）時不寫成「夜晚・夜晚」，改「晴朗・夜晚」。 */
export function weatherPhaseText(weather: string, phase: string): string {
  return `${weather === phase || weather === "夜晚" ? "晴朗" : weather}・${phase}`;
}

/** 這個地點的限制（原本側欄「這裡不能閃現……」與「紮營：……」兩句）；沒有限制為空陣列。 */
export function restrictions(view: WorldView): string[] {
  const out: string[] = [];
  if (!view.growth.at_service) out.push("這裡不能閃現、重閃、溶掉、傳承、重配屬性、立誓（只在城鎮與營火）。");
  const free = view.encounter === null && view.battle_id === null;
  if (free && view.here.camp_problem_zh !== null && !view.here.can_rest) out.push(`紮營：${view.here.camp_problem_zh}`);
  return out;
}

// ---------------- 任務追蹤、隊友 ----------------

export interface TrackedLine {
  id: string;
  /** `guide`＝新手指引（6F-2：還沒有任務時「到霧渡鎮找渡婆婆」）。 */
  kind: "quest" | "thread" | "guide";
  name: string;
  /** 一行進度（目前的步驟，或線頭的期限）。 */
  line: string;
  /** 往哪走（6F-2，筆記 U3：方向與出口）；沒有＝`null`。 */
  route: string | null;
  /** 建議（6F-2，筆記 U4：「建議先完成霧渡新手路」）；沒有＝`null`。 */
  advice: string | null;
}

/** 任務追蹤沒有任何一條時的空白句（6F-2，筆記 U2）。 */
export const TRACKER_EMPTY = "找頭上有「！」的人說話";

/** 任務追蹤：新手指引（6F-2，有的話排最前）、進行中的任務（照任務日誌的排序）、再補線頭，最多 `max` 條。 */
export function trackedQuests(view: WorldView, max = 2): TrackedLine[] {
  const out: TrackedLine[] = [];
  const guide = view.guide;
  if (guide != null) out.push({ id: "guide", kind: "guide", name: guide.text_zh, line: guide.how_zh ?? "", route: null, advice: null });
  for (const q of sortQuests(view.quests ?? [])) {
    if (q.done) continue;
    const step = q.steps.find((s) => s.current) ?? q.steps.find((s) => !s.done);
    const done = q.steps.filter((s) => s.done).length;
    out.push({
      id: q.id,
      kind: "quest",
      name: q.name_zh,
      line: `${step?.text_zh ?? q.summary_zh}（${done}/${q.steps.length}）`,
      route: q.route_zh ?? null,
      advice: q.advice_zh ?? null,
    });
  }
  for (const t of view.threads ?? []) out.push({ id: t.id, kind: "thread", name: t.text_zh, line: t.expires_zh, route: null, advice: null });
  return out.slice(0, max);
}

/** 任務追蹤一條的說明卡文字。 */
export function trackHint(t: TrackedLine): string {
  const kind = t.kind === "quest" ? "任務" : t.kind === "thread" ? "線頭" : "指引";
  const parts = [t.name, t.line, t.advice, t.route].filter((s): s is string => s !== null && s !== "");
  return `${kind}：${parts.join("・")}（點了打開任務面板）`;
}

/** 兩三個字的名字（傭兵名字只留兩三個字，HUD版面.md 第 2 節）。 */
export function shortName(name: string, max = 3): string {
  return [...name].slice(0, max).join("");
}

export interface MateCard {
  name: string;
  short: string;
  title: string;
  level: number;
  /** 血量比例（0～1）。伺服器沒有隊友的 HP（每場開戰都是滿的），所以一律 1。 */
  hp: number;
  /** 頭像（傭兵名冊裡的外觀；影子、同伴沒有＝通用剪影；UI-E2）。 */
  portrait: NpcPortrait | null;
  /** 頭像框色用的出身區（傭兵的 origin；沒有＝`merc` 金框）。 */
  origin: string;
}

/** 隊友卡（主角以外，最多 2 人）。 */
export function mateCards(view: WorldView): MateCard[] {
  const members = view.party?.members ?? [];
  return members
    .filter((m, i) => !(i === 0 && m.mercenary == null && m.shadow == null && m.companion == null))
    .slice(0, 2)
    .map((m) => {
      const merc = m.mercenary != null ? (view.party?.mercenaries ?? []).find((x) => x.id === m.mercenary) : undefined;
      /* PNL-4：劇情夥伴的頭像與框色由伺服器給（`PartyMemberView.portrait`／`region`，人設卡）；傭兵照名冊 */
      return {
        name: m.name_zh,
        short: shortName(m.name_zh),
        title: m.title_zh,
        level: m.level,
        hp: 1,
        portrait: merc?.portrait ?? m.portrait ?? null,
        origin: merc?.origin ?? m.region ?? "merc",
      };
    });
}

/** 條的比例（0～1；最大值為 0 時為 0）。 */
export function ratio(cur: number, max: number | null | undefined): number {
  if (max == null || max <= 0) return 0;
  return Math.max(0, Math.min(1, cur / max));
}

// ---------------- 浮動提示（最近發生的事） ----------------

export interface HudToast {
  seq: number;
  text: string;
  /** 警告（紅框）：第一次進入有限制的地點。 */
  warn: boolean;
  at: number;
}

/** 保留的提示上限（過期的會被下一次加入時清掉）。 */
const TOAST_KEEP = 12;

/** 加進新的提示（新的在後面）；順手丟掉已經過期的。 */
export function addToasts(list: readonly HudToast[], texts: readonly string[], warn: boolean, now: number, seq: number): HudToast[] {
  const alive = list.filter((t) => now - t.at < TOAST_TTL_MS);
  const added = texts.map((text, i) => ({ seq: seq + i, text, warn, at: now }));
  return [...alive, ...added].slice(-TOAST_KEEP);
}

export interface LiveToast {
  toast: HudToast;
  fading: boolean;
}

/** 現在要畫的提示：最新的 `max` 條、還沒過期的；舊的在上、新的在下；最後 1 秒在淡出。 */
export function liveHudToasts(list: readonly HudToast[], now: number, max = TOAST_MAX): LiveToast[] {
  const out: LiveToast[] = [];
  for (let i = list.length - 1; i >= 0 && out.length < max; i -= 1) {
    const t = list[i]!;
    const age = now - t.at;
    if (age >= TOAST_TTL_MS) continue;
    out.push({ toast: t, fading: age >= TOAST_TTL_MS - TOAST_FADE_MS });
  }
  return out.reverse();
}

/** 下一次畫面要變（開始淡出或消失）還要幾毫秒；沒有提示時 `null`。 */
export function nextHudToastChange(live: readonly LiveToast[], now: number): number | null {
  let soonest: number | null = null;
  for (const { toast, fading } of live) {
    const edge = fading ? toast.at + TOAST_TTL_MS : toast.at + TOAST_TTL_MS - TOAST_FADE_MS;
    const wait = Math.max(0, edge - now);
    soonest = soonest === null ? wait : Math.min(soonest, wait);
  }
  return soonest;
}

// ---------------- 任務追蹤的收合（本機） ----------------

export const TRACKER_KEY = "trpg.worldHud.trackerCollapsed";

type Store = Pick<Storage, "getItem" | "setItem">;

function storage(): Store | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

export function readTrackerCollapsed(store: Store | null = storage()): boolean {
  try {
    return store?.getItem(TRACKER_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeTrackerCollapsed(on: boolean, store: Store | null = storage()): void {
  try {
    store?.setItem(TRACKER_KEY, on ? "1" : "0");
  } catch {
    // 私密視窗或封鎖網站資料：只是不記住
  }
}

// ---------------- 小地圖 ----------------

export type MiniDotKind = "npc" | "enemy" | "rest" | "me" | "stone";

export interface MiniDot {
  x: number;
  y: number;
  kind: MiniDotKind;
  label: string;
}

export interface MiniExit {
  x: number;
  y: number;
  dir: "up" | "down" | "left" | "right";
  label: string;
}

export interface MiniMap {
  cols: number;
  rows: number;
  /** 每格的顏色（列優先）。 */
  colors: string[];
  exits: MiniExit[];
  dots: MiniDot[];
  /** 沒走過的格子（蓋霧）。伺服器沒有「走過」的資料，目前一律空（整張顯示）。 */
  fog: boolean[];
}

const MINI_COLOR = {
  wall: "#3a3630",
  chasm: "#1c2430",
  water: "#3f6f9e",
  lava: "#a8442c",
  stone: "#8d8a82",
  dirt: "#a8875a",
  grass: "#5d8a4a",
  other: "#6f7a5c",
  blocked: "#4a4740",
} as const;

function tileColor(t: FieldView["tiles"][number]): string {
  if (t.terrain === "wall") return MINI_COLOR.wall;
  if (t.terrain === "chasm" || t.terrain === "ice_hole") return MINI_COLOR.chasm;
  if (t.terrain === "lava") return MINI_COLOR.lava;
  if (t.surface === "water" || t.surface === "deep_water") return MINI_COLOR.water;
  if (t.walkable === false) return MINI_COLOR.blocked;
  if (t.terrain === "stone") return MINI_COLOR.stone;
  if (t.terrain === "dirt") return MINI_COLOR.dirt;
  if (t.terrain === "grass") return MINI_COLOR.grass;
  return MINI_COLOR.other;
}

function exitDir(field: FieldView, x: number, y: number): MiniExit["dir"] {
  if (x === 0) return "left";
  if (x === field.width - 1) return "right";
  if (y === 0) return "up";
  if (y === field.height - 1) return "down";
  // 不在邊上：看離哪一邊近
  const d = [
    { dir: "left" as const, v: x },
    { dir: "right" as const, v: field.width - 1 - x },
    { dir: "up" as const, v: y },
    { dir: "down" as const, v: field.height - 1 - y },
  ].sort((a, b) => a.v - b.v);
  return d[0]!.dir;
}

/** 休息點（橘）：有休息的設施（酒館）。營火點是 6C-5 的內容，伺服器還沒有給。 */
const REST_FACILITIES = new Set(["tavern", "inn", "campfire"]);

/** 實地地圖 → 小地圖：地形顏色、出口箭頭（每個出口一個，在出口格的中間）、NPC（黃）、休息點（橘）、傳送石、自己（藍）。
 * 敵群（紅）：`FieldView` 目前沒有敵人位置（巡邏 6C 之後），所以沒有。 */
export function minimapModel(field: FieldView): MiniMap {
  const colors = new Array<string>(field.width * field.height).fill(MINI_COLOR.other);
  for (const t of field.tiles) {
    if (t.x >= 0 && t.y >= 0 && t.x < field.width && t.y < field.height) colors[t.y * field.width + t.x] = tileColor(t);
  }
  const exits: MiniExit[] = field.exits.map((e) => {
    const mid = e.cells[Math.floor((e.cells.length - 1) / 2)] ?? [0, 0];
    return { x: mid[0], y: mid[1], dir: exitDir(field, mid[0], mid[1]), label: e.to_name_zh };
  });
  const dots: MiniDot[] = [
    ...field.npcs.map((n) => ({ x: n.x, y: n.y, kind: "npc" as const, label: n.name_zh })),
    ...field.facilities.filter((f) => REST_FACILITIES.has(f.kind)).map((f) => ({ x: f.x, y: f.y, kind: "rest" as const, label: "休息" })),
    ...field.stones.map((s) => ({ x: s.x, y: s.y, kind: "stone" as const, label: "傳送石" })),
    { x: field.me.x, y: field.me.y, kind: "me" as const, label: "你" },
  ];
  return { cols: field.width, rows: field.height, colors, exits, dots, fog: new Array<boolean>(field.width * field.height).fill(false) };
}

// ---------------- 版面（以 1040×624 為基準） ----------------

export const HUD_BASE = { width: 1040, height: 624 } as const;
/** 窄視窗（寬度不到 900px）：任務追蹤自動收合、提示減為 1 條、隊友卡只留頭像和血條。 */
export const HUD_NARROW = 900;

export function isNarrow(viewportWidth: number): boolean {
  return viewportWidth < HUD_NARROW;
}

/** HUD 的縮放：依畫面大小等比例，夾在 0.7～1.25。 */
export function hudScale(width: number, height: number): number {
  if (!(width > 0) || !(height > 0)) return 1;
  const s = Math.min(width / HUD_BASE.width, height / HUD_BASE.height);
  return Math.max(0.7, Math.min(1.25, s));
}

export interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export type HudBlock = "hero" | "mates" | "shadow" | "place" | "minimap" | "clock" | "wallet" | "tracker" | "bar" | "toasts";

export const HUD_BLOCKS: readonly HudBlock[] = ["hero", "mates", "shadow", "place", "minimap", "clock", "wallet", "tracker", "bar", "toasts"];

export interface HudLayout {
  scale: number;
  narrow: boolean;
  blocks: Record<HudBlock, Rect>;
}

/** 功能列的設計尺寸：7 個 46 的鈕、間距 6、左右各留 10。 */
export const BAR_BTN = 46;
const BAR_GAP = 6;
export const BAR_W = HUD_BUTTONS.length * (BAR_BTN + BAR_GAP) - BAR_GAP + 20;
const BAR_H = 56;
const RIGHT_W = 170;
/** RT-6、RT-6b：收合的任務鈕（窄、寬視窗都一樣）貼在錢包（設計座標 178＋24）下方 6。 */
export const TRACKER_TUCK_TOP = 208;

/**
 * 每一塊在畫面（舞台）上的位置（CSS 像素）。設計尺寸照 `sample/hud.js` 的 `hudA()`，乘上 `hudScale`。
 * `mates`＝隊友人數（0～2），`collapsed`＝任務追蹤收成一個圖示。
 */
export function hudLayout(width: number, height: number, opts: { mates: number; narrow: boolean; collapsed: boolean; toasts?: number }): HudLayout {
  const s = hudScale(width, height);
  const W = width / s; // 設計座標下的畫面寬高
  const H = height / s;
  const mateW = opts.narrow ? 96 : 150;
  const mates = Math.max(0, Math.min(2, opts.mates));
  const shadowTop = 98 + mates * 42;
  const right = W - 8 - RIGHT_W;
  const trackerH = opts.collapsed ? 36 : 150; // 6F-2：多了方向與建議兩行（原 112）
  // RT-6（6F-20 待決 3，美術 PM）：收合時任務鈕貼在右欄（錢包）正下方，不懸在地圖中段蓋到房子；
  // RT-6b（RT-6 檢查決定 4）：寬視窗手動收合也一樣（寬窄一致）；展開的任務欄照舊
  const tuck = opts.collapsed;
  const trackerTop = tuck ? TRACKER_TUCK_TOP : Math.max(214, Math.min(H * 0.55, H - BAR_H - 14 - trackerH - 8));
  const toastN = Math.max(1, Math.min(TOAST_MAX, opts.toasts ?? (opts.narrow ? 1 : TOAST_MAX)));
  const toastH = toastN * 30 - 6;
  const design: Record<HudBlock, Rect> = {
    hero: { left: 8, top: 8, width: 250, height: 74 },
    mates: { left: 8, top: 98, width: mateW, height: mates === 0 ? 0 : mates * 42 - 6 },
    shadow: { left: 8, top: shadowTop, width: 36, height: 36 },
    place: { left: right, top: 8, width: RIGHT_W, height: 24 },
    minimap: { left: right, top: 36, width: RIGHT_W, height: 104 },
    clock: { left: right, top: 144, width: RIGHT_W, height: 30 },
    wallet: { left: right, top: 178, width: RIGHT_W, height: 24 },
    tracker: { left: opts.collapsed ? W - 8 - 36 : right, top: trackerTop, width: opts.collapsed ? 36 : RIGHT_W, height: trackerH },
    bar: { left: (W - BAR_W) / 2, top: H - BAR_H - 6, width: BAR_W, height: BAR_H },
    toasts: { left: 10, top: H - 28 - toastH, width: 230, height: toastH },
  };
  const blocks = {} as Record<HudBlock, Rect>;
  for (const id of HUD_BLOCKS) {
    const r = design[id];
    blocks[id] = { left: r.left * s, top: r.top * s, width: r.width * s, height: r.height * s };
  }
  return { scale: s, narrow: opts.narrow, blocks };
}

/** 實地地圖放進舞台的縮放（用滿整個舞台；HUD 疊在上面，出口附近的 HUD 變半透明）。 */
export function fieldFitScale(stage: { width: number; height: number }, field: FieldView, min = 0.4, max = 1.5): number {
  const px = stagePixels(field);
  if (px.width <= 0 || px.height <= 0 || !(stage.width > 0) || !(stage.height > 0)) return 1;
  return Math.max(min, Math.min(max, Math.min(stage.width / px.width, stage.height / px.height)));
}

/** 出口格在舞台上的矩形（畫布在舞台裡水平、垂直置中）。 */
export function exitRects(field: FieldView, stage: { width: number; height: number }, scale: number): Rect[] {
  const px = stagePixels(field);
  const cw = Math.floor(px.width * scale);
  const ch = Math.floor(px.height * scale);
  const ox = Math.max(0, (stage.width - cw) / 2);
  const oy = Math.max(0, (stage.height - ch) / 2);
  const reserve = topReserve(field);
  const cell = TILE_SIZE * scale;
  return field.exits.flatMap((e) =>
    e.cells.map(([x, y]) => ({ left: ox + x * cell, top: oy + (reserve + y * TILE_SIZE) * scale, width: cell, height: cell })),
  );
}

function overlaps(a: Rect, b: Rect, pad = 0): boolean {
  return a.left - pad < b.left + b.width && b.left < a.left + a.width + pad && a.top - pad < b.top + b.height && b.top < a.top + a.height + pad;
}

/**
 * 不因出口變半透明的區塊（6F-1，前 10 分鐘 U16：鎮內的「出」口格透過半透明的小地圖畫在它上面）：右上整組
 * （地名、小地圖、時間天氣、錢包）保持不透明；出口在小地圖上本來就有標示。
 */
export const NEVER_FADED: readonly HudBlock[] = ["place", "minimap", "clock", "wallet"];

/** 蓋到出口（含半格的緩衝）的 HUD 區塊：這些變半透明，出口標示看得到（小地圖除外）。依 `HUD_BLOCKS` 的順序。 */
export function fadedBlocks(layout: HudLayout, exits: readonly Rect[]): HudBlock[] {
  return HUD_BLOCKS.filter((id) => {
    if (NEVER_FADED.includes(id)) return false;
    const r = layout.blocks[id];
    if (r.width <= 0 || r.height <= 0) return false;
    return exits.some((e) => overlaps(r, e, e.width / 2));
  });
}

/** HUD 在舞台四邊佔掉的寬度（鏡頭的安全區用，6F-3 巡檢 bug 3；同 `camera.ts` 的 `ViewInsets`）。 */
export interface HudInsets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

/** 右側那一欄（地名、小地圖、時間天氣、錢包、任務追蹤）。 */
const RIGHT_COLUMN: readonly HudBlock[] = ["place", "minimap", "clock", "wallet", "tracker"];

/**
 * 鏡頭要避開的 HUD：上＝左上主角卡（與隊友卡）的下緣、下＝底部快捷列的上緣、右＝右側那一欄的左緣。
 * 左邊只有主角卡和提示，寬度不大，用上緣處理就好（不扣左邊，畫面不會太窄）。
 */
export function hudInsets(layout: HudLayout, stage: { width: number; height: number }): HudInsets {
  const b = layout.blocks;
  const bottomOf = (r: Rect): number => (r.width > 0 && r.height > 0 ? r.top + r.height : 0);
  const top = Math.max(bottomOf(b.hero), bottomOf(b.mates));
  const bottom = b.bar.height > 0 ? Math.max(0, stage.height - b.bar.top) : 0;
  const lefts = RIGHT_COLUMN.map((id) => b[id]).filter((r) => r.width > 0 && r.height > 0).map((r) => r.left);
  const right = lefts.length === 0 ? 0 : Math.max(0, stage.width - Math.min(...lefts));
  return { top, right, bottom, left: 0 };
}

/** 彈窗（浮動面板、遇敵卡、事件卡）的位置與大小上限（CSS 像素，相對舞台）。 */
export interface PopupBox {
  top: number;
  maxHeight: number;
  /** 寬度上限（水平置中，兩側讓出左右兩欄 HUD）。 */
  maxWidth: number;
}

/**
 * 彈窗避開四角的 HUD（6F-3，美術 PM 一致性巡檢 #10、實機巡檢 bug 6）：水平置中；上緣放在左上主角卡的下方；下緣停在底部快捷列上方，不夠高就在彈窗裡往下捲；寬度讓出左右兩欄（取較寬的一邊，
 * 兩邊對稱才能置中），不蓋到右側的小地圖、任務追蹤與左側的隊友卡。`want`＝彈窗想要的寬度。
 */
export function popupBox(layout: HudLayout, want: number): PopupBox {
  const b = layout.blocks;
  const s = layout.scale;
  const width = b.place.left + b.place.width + 8 * s; // 舞台寬（右欄貼右邊 8）
  const shown = (r: Rect): boolean => r.width > 0 && r.height > 0;
  const top = b.hero.top + b.hero.height + 8 * s; // 隊友卡在左欄（寬度已讓出），不必再往下
  const leftCol = Math.max(...(["mates", "shadow"] as const).map((id) => (shown(b[id]) ? b[id].left + b[id].width : 0)));
  const lefts = RIGHT_COLUMN.map((id) => b[id]).filter(shown).map((r) => r.left);
  const rightCol = lefts.length === 0 ? 0 : width - Math.min(...lefts);
  const side = Math.max(leftCol, rightCol) + 8 * s;
  const maxWidth = Math.max(Math.min(want, 280 * s), Math.min(want, width - side * 2));
  const maxHeight = Math.max(120 * s, b.bar.top - 8 * s - top);
  return { top, maxHeight, maxWidth };
}

/** 大世界詢問視窗（開場、配點教學、升級、你不在的時候）想要的寬度。 */
export const DIALOG_W = 480;

/**
 * 大世界詢問視窗的位置（UI-E1 追加 2）：同 `popupBox` 的避開四角規則，換成視窗座標（詢問視窗是 position: fixed，
 * `stageTop`＝HUD 舞台上緣在視窗裡的位置）。寬度上限同 `.decision-card`（480）。
 */
export function dialogBox(layout: HudLayout, stageTop: number, want = DIALOG_W): PopupBox {
  const b = popupBox(layout, want);
  return { top: stageTop + b.top, maxHeight: b.maxHeight, maxWidth: b.maxWidth };
}

// ---------------- 排版煙霧檢查 ----------------

export interface HudSnapshot {
  viewport: { width: number; height: number };
  stage: Rect;
  blocks: Partial<Record<HudBlock, Rect>>;
}

export interface HudCheck {
  id: string;
  label: string;
  pass: boolean;
  detail: string;
}

const TOL = 1.5;

function inside(inner: Rect, outer: Rect): boolean {
  return (
    inner.left >= outer.left - TOL &&
    inner.top >= outer.top - TOL &&
    inner.left + inner.width <= outer.left + outer.width + TOL &&
    inner.top + inner.height <= outer.top + outer.height + TOL
  );
}

/** 四角的版面檢查：每塊都在舞台裡、兩兩不重疊、四塊各在自己的角、中間（舞台中央 40%×40%）沒有被擋。 */
export function evaluateHudLayout(snap: HudSnapshot): HudCheck[] {
  const out: HudCheck[] = [];
  const present = HUD_BLOCKS.filter((id) => {
    const r = snap.blocks[id];
    return r !== undefined && r.width > 0 && r.height > 0;
  });
  const missing = ["hero", "place", "minimap", "bar", "toasts"].filter((id) => !present.includes(id as HudBlock));
  out.push({ id: "present", label: "主角卡、地名、小地圖、功能列、提示都在", pass: missing.length === 0, detail: missing.length === 0 ? "OK" : `缺 ${missing.join("、")}` });
  const outside = present.filter((id) => !inside(snap.blocks[id]!, snap.stage));
  out.push({ id: "inside", label: "每一塊都在畫面裡", pass: outside.length === 0, detail: outside.length === 0 ? "OK" : outside.join("、") });
  const pairs: string[] = [];
  present.forEach((a, i) =>
    present.slice(i + 1).forEach((b) => {
      if (overlaps(snap.blocks[a]!, snap.blocks[b]!, -TOL)) pairs.push(`${a}×${b}`);
    }),
  );
  out.push({ id: "no-overlap", label: "HUD 各塊互不重疊", pass: pairs.length === 0, detail: pairs.length === 0 ? "OK" : pairs.join("、") });
  const st = snap.stage;
  const cx = st.left + st.width / 2;
  const cy = st.top + st.height / 2;
  const corner = (id: HudBlock, wantLeft: boolean, wantTop: boolean): boolean => {
    const r = snap.blocks[id];
    if (r === undefined) return false;
    const mx = r.left + r.width / 2;
    const my = r.top + r.height / 2;
    return (wantLeft ? mx < cx : mx > cx) && (wantTop ? my < cy : my > cy);
  };
  const corners = [corner("hero", true, true), corner("minimap", false, true), corner("toasts", true, false)];
  const barMid = snap.blocks.bar === undefined ? null : snap.blocks.bar.left + snap.blocks.bar.width / 2;
  const barOk = barMid !== null && Math.abs(barMid - cx) <= TOL + 1 && (snap.blocks.bar?.top ?? 0) > cy;
  out.push({
    id: "corners",
    label: "主角左上、小地圖右上、提示左下、功能列底部置中",
    pass: corners.every(Boolean) && barOk,
    detail: `左上 ${corners[0]}・右上 ${corners[1]}・左下 ${corners[2]}・功能列 ${barOk}`,
  });
  const center: Rect = { left: st.left + st.width * 0.3, top: st.top + st.height * 0.3, width: st.width * 0.4, height: st.height * 0.4 };
  const blocking = present.filter((id) => overlaps(snap.blocks[id]!, center, -TOL));
  out.push({ id: "center-free", label: "中間的畫面沒有被 HUD 擋住", pass: blocking.length === 0, detail: blocking.length === 0 ? "OK" : blocking.join("、") });
  return out;
}
