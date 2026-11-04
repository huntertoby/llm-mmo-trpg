// 大世界戰後結算（6F-1，前 10 分鐘檢查 U5）：戰鬥播完時先向伺服器同步一次（回寫經驗、掉落、任務），
// 用回來的世界畫面組結算面板的句子。只用伺服器已有的資料：這次同步的事件句子、經驗、HP、任務追蹤。
import type { EndSummary } from "../ui/EndPanel";
import type { WorldView } from "../api/types";
import { trackedQuests } from "./hud";

/** HP 不會自動回的說明（勝利時；敗北會被抬回城鎮、HP 回滿，不需要）。 */
export const HP_NOTE_ZH = "HP 要到城鎮或營火才會回。";

/** 這次同步的事件裡有沒有「打贏了」（伺服器的戰鬥結果句子）。 */
function wonIn(lines: readonly string[]): boolean {
  return lines.some((l) => l.startsWith("打贏了"));
}

/** 結算句子：伺服器事件（經驗、金幣、掉落、任務、靈感）＋經驗進度＋沒掉落時說明＋任務進度＋HP 說明。 */
export function battleSummary(view: WorldView): EndSummary {
  const lines = [...view.events];
  const won = wonIn(lines);
  const c = view.character;
  if (c.xp_next !== null && c.xp_next !== undefined) lines.push(`經驗 ${c.xp}／${c.xp_next}（Lv ${c.level}）`);
  if (won && view.last_loot_zh == null) lines.push("戰利品：這場沒有掉落。");
  if (!lines.some((l) => l.includes("任務「"))) {
    const tracked = trackedQuests(view, 1).find((t) => t.kind === "quest");
    if (tracked !== undefined) lines.push(`任務「${tracked.name}」：${tracked.line}`);
  }
  const note = won ? `HP ${c.hp}／${c.max_hp}：${HP_NOTE_ZH}` : null;
  return { lines, note };
}
