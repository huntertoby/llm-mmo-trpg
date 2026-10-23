// 基本動作的說明浮動卡文字（Phase 3-41b）：全部來自 /api/glossary 的 `actions`
// （後端 `trpg.narrative.action_info` 依 `rules/core.yaml` 產生），前端不寫死 AP、格數、百分比。
import { glossaryEntry } from "./glossary";

/** 一句話：「跑步：花 1 AP，本回合移動點數 +3 格（每回合 1 次）」；對照表沒有這個動作時 `null`。 */
export function actionSummary(id: string): string | null {
  const e = glossaryEntry("actions", id);
  if (e === undefined) return null;
  return `${e.name_zh}：${e.description_zh ?? ""}`;
}

/** 完整浮動卡文字：標題一行，之後逐條規則（浮動卡會換行顯示）；對照表沒有時 `null`。 */
export function actionCardText(id: string): string | null {
  const e = glossaryEntry("actions", id);
  if (e === undefined) return null;
  return [e.name_zh, ...e.rules_zh.map((line) => `・${line}`)].join("\n");
}

/**
 * 常駐按鈕的浮動卡：第一行是 `head`（可帶當下狀態，例如「目前可到 5 格」；省略時為動作名稱），
 * 之後逐條規則。對照表沒有這個動作時只剩 `head`（沒有 `head` 則 `null`）。
 */
export function actionHint(id: string, head?: string): string | null {
  const e = glossaryEntry("actions", id);
  if (e === undefined) return head ?? null;
  return [head ?? e.name_zh, ...e.rules_zh.map((line) => `・${line}`)].join("\n");
}

/** 「更多動作」鈕的說明：列出選單可能出現的動作名稱（取自對照表）。 */
export function moreActionsSummary(kinds: readonly string[]): string {
  const names = kinds.flatMap((k) => {
    const e = glossaryEntry("actions", k);
    return e === undefined ? [] : [e.name_zh];
  });
  return `${names.join("、")}（只列出現在合法的）`;
}
