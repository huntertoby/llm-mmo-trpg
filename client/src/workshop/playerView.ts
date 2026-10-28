// 工坊的玩家模式／開發者模式（?dev=1）顯示規則（3-48c）。
// 後端把說明換成玩家版（`description_zh`），開發者語氣的原文放在 `dev_description_zh`；
// 巢狀效果等「之後開放」的欄位與選項帶 `later` 旗標；條件顯示的欄位帶 `show_when`。
import type { Choice, FieldSpec } from "../api/types";
import { isDevMode } from "../run/startFlow";
import { getPath, joinPath, type Json } from "./draft";

/** 開發者模式：網址帶 `?dev=1`（呼叫時才讀，測試可以改網址）。 */
export function isDev(): boolean {
  try {
    return isDevMode(window.location.search);
  } catch {
    return false;
  }
}

interface Described {
  description_zh: string;
  dev_description_zh?: string;
}

/** 要顯示的說明：玩家模式是玩家版，開發者模式是原文（沒有原文時同玩家版）。 */
export function descOf(item: Described, dev: boolean = isDev()): string {
  if (dev && item.dev_description_zh !== undefined && item.dev_description_zh !== "") return item.dev_description_zh;
  return item.description_zh;
}

/** 玩家模式隱藏「之後開放」的選項（開發者模式全部列出）。 */
export function shownChoices(choices: readonly Choice[], dev: boolean = isDev()): Choice[] {
  return dev ? [...choices] : choices.filter((c) => c.later !== true);
}

/** 有多少選項在玩家模式被隱藏（畫面用來寫「這類效果之後開放」）。 */
export function hiddenCount(choices: readonly Choice[], dev: boolean = isDev()): number {
  return dev ? 0 : choices.filter((c) => c.later === true).length;
}

/** 欄位現在要不要顯示：玩家模式隱藏 `later`；`show_when`（同一層另一個欄位的值）不符就隱藏。 */
export function fieldShown(spec: FieldSpec, container: Json, base: string, dev: boolean = isDev()): boolean {
  if (!dev && spec.later === true) return false;
  if (!dev && spec.auto_generated === true) return false; // 玩家模式自動產生（例：變奏的型態代碼）
  const when = spec.show_when ?? {};
  return Object.entries(when).every(([key, want]) => String(getPath(container, joinPath(base, key)) ?? "") === want);
}

/** 選項分組（3-52：層數依「累積在你身上」「疊在敵人身上」分組）：後端用 `info.group_zh` 標示，
 * 沒有分組名的選項（一般欄位）都在同一組、不顯示組名；組的順序照第一次出現。 */
export function groupChoices(choices: readonly Choice[]): [string | null, Choice[]][] {
  const groups: [string | null, Choice[]][] = [];
  for (const c of choices) {
    const label = typeof c.info["group_zh"] === "string" ? c.info["group_zh"] : null;
    const found = groups.find((g) => g[0] === label);
    if (found === undefined) groups.push([label, [c]]);
    else found[1].push(c);
  }
  return groups;
}
