// 大世界地點圖的純函式（Phase 5A-5；docs/phases/Phase5計畫.md 10.5）。
// 規則一律由後端算好（`WorldView`）：這裡只決定外觀（樣式、說明文字、可不可以點）與表單驗證。
import type { WorldCharacterView, WorldLocationView, WorldView } from "../api/types";

/** 最後使用的角色 ID（瀏覽器記住，重新整理後回到同一個角色；帳號是 5E-1）。 */
export const WORLD_CHAR_KEY = "trpg.world.character";

export const NAME_MAX = 12;

/** 地點種類 → 外觀（形狀用 CSS class，顏色依種類）。 */
const KIND_STYLE: Record<string, string> = {
  town: "town",
  gate: "gate",
  camp: "danger",
  elite_lair: "elite",
  boss: "boss",
  secret: "secret",
};

/** 地點按鈕的 class：種類外觀＋目前位置／可走／不可走／已清空。 */
export function locationClass(loc: WorldLocationView, encounter: boolean): string {
  const parts = ["world-loc", `kind-${KIND_STYLE[loc.kind] ?? "site"}`];
  if (loc.current) parts.push("current");
  else if (canTravel(loc, encounter)) parts.push("reachable");
  else parts.push("far");
  if (loc.cleared) parts.push("cleared");
  return parts.join(" ");
}

/** 這個地點現在能不能點了走過去（相鄰、沒被擋、沒有遭遇）。 */
export function canTravel(loc: WorldLocationView, encounter: boolean): boolean {
  return !loc.current && loc.adjacent && loc.blocked_zh === null && !encounter;
}

/** 地點的說明卡文字（一行一段，用「・」連）。 */
export function locationHint(loc: WorldLocationView, encounter: boolean): string {
  const head = [loc.kind_zh, loc.level_zh, loc.cleared ? "已清空" : null].filter((s): s is string => s !== null && s !== "");
  const lines = [`${loc.name_zh}（${head.join("・")}）`];
  if (loc.description_zh !== "") lines.push(loc.description_zh);
  if (loc.current) lines.push("目前位置");
  else if (canTravel(loc, encounter)) lines.push("點一下走過去（路上可能遇敵）");
  else if (loc.adjacent && loc.blocked_zh !== null) lines.push(`不能走：${loc.blocked_zh}`);
  else if (!loc.adjacent) lines.push("不相鄰：先走到旁邊的地點");
  return lines.join("\n");
}

/** 地點按鈕上的小字：建議等級或「已清空」。 */
export function locationBadge(loc: WorldLocationView): string | null {
  if (loc.cleared) return "已清空";
  return loc.level_zh;
}

/** 連線兩端的座標（百分比）；找不到端點時 `null`。 */
export function edgeLine(
  view: WorldView,
  [a, b]: readonly [string, string],
): { x1: number; y1: number; x2: number; y2: number; near: boolean } | null {
  const from = view.map.locations.find((l) => l.id === a);
  const to = view.map.locations.find((l) => l.id === b);
  if (from === undefined || to === undefined) return null;
  return { x1: from.x, y1: from.y, x2: to.x, y2: to.y, near: from.current || to.current };
}

/** 角色狀態的一行文字。 */
export function statusLine(c: WorldCharacterView): string {
  const xp = c.xp_next === null ? `經驗 ${c.xp}（已到頂）` : `經驗 ${c.xp}／${c.xp_next}`;
  return `Lv ${c.level}・${xp}・HP ${c.hp}／${c.max_hp}・法力 ${c.mana}／${c.max_mana}・補給 ${c.supplies}／${c.max_supplies}`;
}

/** 角色名稱的問題（空白、太長）；沒問題時 `null`。 */
export function nameProblem(name: string): string | null {
  const trimmed = name.trim();
  if (trimmed === "") return "請輸入角色名稱";
  if ([...trimmed].length > NAME_MAX) return `名稱最多 ${NAME_MAX} 個字`;
  return null;
}

/** 讀／寫最後使用的角色 ID（瀏覽器不能存時當作沒有）。 */
export function readWorldChar(): string | null {
  try {
    return window.localStorage.getItem(WORLD_CHAR_KEY);
  } catch {
    return null;
  }
}

export function writeWorldChar(id: string | null): void {
  try {
    if (id === null) window.localStorage.removeItem(WORLD_CHAR_KEY);
    else window.localStorage.setItem(WORLD_CHAR_KEY, id);
  } catch {
    // 不能存就算了（只影響重新整理後要不要自動回到角色）
  }
}
