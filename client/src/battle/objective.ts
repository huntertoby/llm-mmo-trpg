// 勝利條件的顯示文字與格子標記（Phase 3-22，純函式）：選路／下一場畫面、戰鬥開場、HUD、結算與地圖上的
// 出口格／守點格都從這裡取文字，避免各處各寫一份。
import type { BattleView, Pos } from "../api/types";

/** 勝利條件的種類（後端 `Objective.kind`）。 */
export type ObjectiveKind = "eliminate" | "escape" | "defend";

/** 只需要勝利條件的三個欄位（`BattleView.objective` 與 `RunPlan.objective` 都符合）。 */
export interface ObjectiveLike {
  kind: ObjectiveKind;
  rounds?: number | null;
  /** 後端的格子是 `[x, y]` 對。 */
  tiles?: readonly (readonly [number, number])[] | null;
}

/** 地圖上的目標格種類：`exit` 出口格（撤離）、`point` 守點格（守點）。 */
export type MarkerKind = "exit" | "point";

export interface ObjectiveMarker extends Pos {
  kind: MarkerKind;
}

/** 圖示（純文字符號，HUD 與標題前面用）。 */
export const OBJECTIVE_ICONS: Readonly<Record<ObjectiveKind, string>> = {
  eliminate: "⚔",
  escape: "➜",
  defend: "◎",
};

export const OBJECTIVE_NAMES: Readonly<Record<ObjectiveKind, string>> = {
  eliminate: "全滅",
  escape: "撤離",
  defend: "守點",
};

function kindOf(objective: ObjectiveLike): ObjectiveKind {
  return objective.kind;
}

/** 一行說明，例如「撤離：5 輪內全員抵達出口」。 */
export function objectiveLine(objective: ObjectiveLike): string {
  const kind = kindOf(objective);
  const rounds = objective.rounds ?? null;
  if (kind === "escape") return `撤離：${rounds === null ? "限時內" : `${rounds} 輪內`}全員抵達出口`;
  if (kind === "defend") return `守點：守住守點 ${rounds === null ? "到時限" : `${rounds} 輪`}，別讓敵人站上去`;
  return "全滅：擊倒所有敵人";
}

/** 圖示加名稱，例如「➜ 撤離」。 */
export function objectiveBadge(objective: ObjectiveLike): string {
  const kind = kindOf(objective);
  return `${OBJECTIVE_ICONS[kind]} ${OBJECTIVE_NAMES[kind]}`;
}

/**
 * 剩餘輪數（含目前這一輪）：第 `round` 輪結束時判定，所以第 1 輪開始時剩 `rounds` 輪。
 * 全滅或沒有輪數時回傳 `null`。
 */
export function roundsLeft(objective: ObjectiveLike, round: number): number | null {
  if (kindOf(objective) === "eliminate" || objective.rounds == null) return null;
  return Math.max(0, objective.rounds - round + 1);
}

/** HUD 常駐的一行，例如「➜ 撤離・剩 3 輪」；全滅只寫名稱。 */
export function objectiveHud(objective: ObjectiveLike, round: number): string {
  const left = roundsLeft(objective, round);
  const base = objectiveBadge(objective);
  if (left === null) return base;
  return `${base}・${left <= 1 ? "最後 1 輪" : `剩 ${left} 輪`}`;
}

/** 戰鬥中該顯示哪些目標格標記（全滅沒有）。 */
export function objectiveMarkers(objective: ObjectiveLike): ObjectiveMarker[] {
  const kind = kindOf(objective);
  if (kind === "eliminate") return [];
  const marker: MarkerKind = kind === "escape" ? "exit" : "point";
  return (objective.tiles ?? []).map(([x, y]) => ({ x, y, kind: marker }));
}

/** 指定格子上的目標格標記；沒有時 `null`。 */
export function markerAt(view: Pick<BattleView, "objective">, pos: Pos): MarkerKind | null {
  const found = objectiveMarkers(view.objective).find((m) => m.x === pos.x && m.y === pos.y);
  return found === undefined ? null : found.kind;
}

/** 格子資訊卡的段落（標題＋規則）；不是目標格時 `null`。 */
export function markerCard(
  view: Pick<BattleView, "objective" | "round">,
  pos: Pos,
): { title: string; lines: string[] } | null {
  const kind = markerAt(view, pos);
  if (kind === null) return null;
  const left = roundsLeft(view.objective, view.round);
  const rounds = left === null ? "" : `（剩 ${left} 輪）`;
  if (kind === "exit") {
    return {
      title: `出口格・撤離${rounds}`,
      lines: ["我方單位站上出口格就撤離戰場。", "時限內全員撤離才算勝利；時限到仍有人留在場上即敗。"],
    };
  }
  return {
    title: `守點格・守住${rounds}`,
    lines: ["每輪結束時，若有敵方單位站在守點格上，守點失守（戰敗）。", "守到最後一輪結束即勝；我方單位站在上面可以擋住敵人。"],
  };
}

/** 結算畫面的原因說明（一句話）；沒有對應的原因時 `null`。 */
const END_DETAIL: Readonly<Record<string, string>> = {
  escaped: "撤離成功：全員抵達出口。",
  escape_failed: "撤離超時：時限到了，仍有人留在戰場上。",
  defended: "守住了：守點撐到最後一輪結束。",
  point_lost: "守點失守：敵人占領了守點。",
};

export function endDetail(reason: string | null): string | null {
  return reason === null ? null : (END_DETAIL[reason] ?? null);
}
