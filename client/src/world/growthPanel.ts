// 「成長與技能」面板的純函式與新字（PNL-2；docs/art/資訊面板-移植需求.md 3.3「成長與技能」、4.1 #13～#23、#35、#36、#43）。
// 規則與能不能用照舊由伺服器給（`WorldView.growth`、`limits`、`oath`、`character`）；這裡只決定分頁的記號、預設分頁、標籤的字。
// 記號判斷沿用 `growth.ts` 的 `spendLock`（花點被擋的原因）與 `growthBadge` 同一組條件（屬性點、靈感點）。
import type { WorldView } from "../api/types";
import type { TabBadgeSpec } from "../ui/panelTabRules";
import { limitOf } from "./limits";
import { spendLock } from "./growth";

export type GrowthTabId = "flash" | "attr" | "care" | "look";
/** 分頁順序（玩家最常來做的事；3.3）。 */
export const GROWTH_TAB_IDS: readonly GrowthTabId[] = ["flash", "attr", "care", "look"];

/** 標題（字不變）。 */
export const GROWTH_TITLE_ZH = "成長與技能";
/** 分頁名、兩字短名（#35、#36）；「整備」滑過寫全名（#35）。 */
export const GROWTH_TAB_ZH: Readonly<Record<GrowthTabId, { label: string; short: string; hint?: string }>> = {
  flash: { label: "靈感閃現", short: "閃現" },
  attr: { label: "屬性點", short: "屬性" },
  care: { label: "整備", short: "整備", hint: "整備：重閃、溶掉與傳承、誓約" },
  look: { label: "外觀與種族", short: "外觀" },
};

/** 固定區的警告結論（#14）：「現在不行」＋伺服器給的原因（例「這裡不是城鎮或營火」）；原次行（`service_zh`）進右邊 (i)。 */
export const NOT_NOW_ZH = "現在不行";

/** 入門期的鎖標籤（#15、#20、#23；新字）。說明卡仍是伺服器的原句（`limits`）。 */
export const FLASH_LOCK_ZH = { head: "閃現", tail: "4 級起" } as const;
export const LEVEL4_TAG_ZH = "4 級起";
export const CHOSEN_TAG_ZH = "正式選定後";

/** 屬性點分頁（#18）。 */
export const ATTR_LINE_ZH = "未分配的屬性點";
export const ATTR_PER_LEVEL_ZH = "升級時每級 +2";
export const ATTR_EMPTY_ZH = "沒有未分配的屬性點。";

/** 整備分頁（#21～#23）。 */
export const CARE_LINE_ZH = "重閃、溶掉與傳承、誓約";
export const CARE_PLACE_ZH = "只在城鎮與營火";
export const CARE_FOLDS = ["reflash", "dissolve", "oath"] as const;
export type CareFold = (typeof CARE_FOLDS)[number];
export const CARE_FOLD_ZH: Readonly<Record<CareFold, { name: string; note: string }>> = {
  reflash: { name: "重閃", note: "把以前的一次變化換掉" },
  dissolve: { name: "溶掉或傳承", note: "二選一，舊技能會消失" },
  oath: { name: "誓約", note: "同時 1 個，到城鎮或營火才能換" },
};
/** 重閃摺疊右邊（#22）：主字＋說明卡（原句括號裡的那段）。 */
export const NO_REFLASH_ZH = "還沒有可以重閃的技能";
export const NO_REFLASH_TIP_ZH = "要先閃現過，或有完整技能。";

/** 外觀與種族分頁（#16、#17）。 */
export const LOOK_ROW_ZH = "外觀";
export const LOOK_FREE_ZH = "主城隨時免費";
export const RACE_ROW_ZH = "種族";
export const RACE_NOTE_ZH = "本季可以免費換一次";
export const RACE_LOCK_ZH = "正式選定後才能換";

/** 靈感閃現分頁的記號（#42、#43）：入門期整頁鎖住＝金鎖（「閃現 4 級起」，鎖住時不掛數字）；
 *  4 級以上、現在能花點、有靈感點＝金底數字（「可以閃現：靈感點 3」）；其他不掛。 */
export function flashBadge(view: WorldView): TabBadgeSpec | null {
  if (limitOf(view, "flash") !== null) return { kind: "lock", hint: `${FLASH_LOCK_ZH.head} ${FLASH_LOCK_ZH.tail}` };
  const insight = view.growth.insight;
  if (insight > 0 && spendLock(view) === null) return { kind: "n", value: insight, hint: `可以閃現：靈感點 ${insight}` };
  return null;
}

/** 屬性點分頁的記號（#43）：有未分配的屬性點＝金底數字（「未分配屬性點 2」）。分配不受地點限制，所以不看 `spendLock`。 */
export function attrBadge(view: WorldView): TabBadgeSpec | null {
  const points = view.character.attribute_points;
  return points > 0 ? { kind: "n", value: points, hint: `未分配屬性點 ${points}` } : null;
}

/** 分頁上的記號（整備、外觀與種族不掛：部分鎖住不掛、純資訊不掛，3.2 第 5 條）。 */
export function growthTabBadge(view: WorldView, id: GrowthTabId): TabBadgeSpec | null {
  if (id === "flash") return flashBadge(view);
  if (id === "attr") return attrBadge(view);
  return null;
}

/** 固定區的警告（#14）：不能花點時（不在城鎮或營火、有遭遇、戰鬥中）＝原因；在城鎮且可以花點＝不顯示。 */
export function growthWarning(view: WorldView): string | null {
  return view.growth.blocked_zh ?? null;
}

/** 從別處的提醒點進來要開的分頁（3.2 第 3 條：功能列「靈感 N」→「靈感閃現」）。不認得＝null（照預設）。 */
export function growthTabOf(hint: string | null | undefined): GrowthTabId | null {
  return GROWTH_TAB_IDS.find((id) => id === hint) ?? null;
}

/** 種族列的鎖標籤：入門期（`limits.race`）＝「正式選定後才能換」；其他原因（例不在主城）照伺服器的字；可以換＝null。 */
export function raceLockTag(view: Pick<WorldView, "limits" | "character">): string | null {
  const reason = view.character.free_race_change_zh ?? null;
  if (reason === null) return null;
  return limitOf(view, "race") !== null ? RACE_LOCK_ZH : reason;
}
