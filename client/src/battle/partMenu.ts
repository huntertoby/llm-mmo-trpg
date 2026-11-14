// 選部位小選單與角色卡部位列的資料（PB-1c；05 5.12.2 第 12 點、5.12.3；R6）。純函式：不碰 React、DOM。
// - 選單：第一列「本體」（預設選中、永遠打得到），之後照部位 ID（伺服器 `part_options` 已排序）；打不到的灰掉並寫原因。
// - 部位條狀態（美術移植需求 2.2）：完好＝米白、破壞中的空槽＝灰紫、已破壞＝暗紅底＋紅「×」、未露出或看不到資訊＝幾乎黑、不寫數字。
import type { PartOption, PartView, UnitView } from "../api/types";
import { FRONT_SHELL_ZH, isGiant } from "./footprint";

/** 部位條的狀態：`ok` 畫血量、`broken` 打叉、`hidden`（未露出、或頭目資訊被隱藏拿不到血量）＝這一格沒有條。 */
export type PartBarState = { kind: "ok"; hp: number; max: number } | { kind: "broken" } | { kind: "hidden" };

/** 一個部位的條（角色卡、選單共用）。 */
export function partBarState(part: PartView): PartBarState {
  if (part.broken) return { kind: "broken" };
  if (!part.exposed || part.hp == null || part.max_hp == null) return { kind: "hidden" };
  return { kind: "ok", hp: part.hp, max: part.max_hp };
}

/** 選單的一列。 */
export interface PartMenuRow {
  /** `"body"` 或部位 ID。 */
  id: string;
  name: string;
  /** 打得到（本體永遠是）。 */
  ok: boolean;
  /** 打不到的原因（伺服器的 `reason_zh`）；打得到時 `null`。 */
  reason: string | null;
  /** 本體：HP（拿不到時 `null`）；部位：條的狀態。 */
  bar: PartBarState | { kind: "body"; hp: number | null; max: number };
  broken: boolean;
  /** 原因是「從背後」時，原因前面加背刺小圖（美術移植需求 3.1 第 2 點）。 */
  back: boolean;
  /** 「破掉會：……」每一項；本體為空。 */
  breakLines: readonly string[];
}

/** 本體列的 ID。 */
export const BODY_ROW = "body";

/**
 * 本體列的字（GB-4c，美術 GB-4b 待決 8）：巨型頭目（佔格 > 1，`UnitView.footprint`／`tiles`）的本體是南排前殼，
 * 寫「前殼（本體）」（和滑過前殼格的提示同一個 `FRONT_SHELL_ZH`）；一格的頭目（霧鎖真人）維持「本體」。
 */
export function bodyRowName(boss: Pick<UnitView, "footprint" | "tiles">): string {
  return isGiant(boss) ? FRONT_SHELL_ZH : "本體";
}

/** 選單的列：本體＋伺服器給的部位選項（順序照伺服器，依部位 ID）。 */
export function partMenuRows(boss: UnitView, options: readonly PartOption[]): PartMenuRow[] {
  const views = new Map((boss.parts ?? []).map((p) => [p.id, p] as const));
  const rows: PartMenuRow[] = [
    { id: BODY_ROW, name: bodyRowName(boss), ok: true, reason: null, bar: { kind: "body", hp: boss.hp ?? null, max: boss.max_hp }, broken: false, back: false, breakLines: [] },
  ];
  for (const o of options) {
    const view = views.get(o.part_id);
    const broken = view?.broken === true;
    rows.push({
      id: o.part_id,
      name: o.name_zh,
      ok: o.ok,
      reason: o.ok ? null : (o.reason_zh ?? null),
      bar: view === undefined ? { kind: "hidden" } : partBarState(view),
      broken,
      back: !o.ok && !broken && view?.reach === "behind" && view.exposed,
      breakLines: view?.break_lines_zh ?? [],
    });
  }
  return rows;
}

/** 「破掉會：……」一行（沒有效果時 `null`）。 */
export function breakLine(row: Pick<PartMenuRow, "breakLines" | "broken">): string | null {
  if (row.breakLines.length === 0) return null;
  return `${row.broken ? "已破：" : "破掉會："}${row.breakLines.join("；")}`;
}

/** 方向鍵移動選取（上下循環）。 */
export function moveSelection(count: number, current: number, delta: 1 | -1): number {
  if (count <= 0) return 0;
  return (((current + delta) % count) + count) % count;
}

/** 按 Enter 或點一列：打得到才送出；回傳要帶的 `target_part`（本體為 `null`），打不到為 `undefined`（不送出）。 */
export function pickedPart(row: PartMenuRow | undefined): string | null | undefined {
  if (row === undefined || !row.ok) return undefined;
  return row.id === BODY_ROW ? null : row.id;
}

/** 選單標題右側：「選部位・{階段}」。 */
export function partMenuSubtitle(boss: UnitView): string {
  const phase = boss.boss_phase?.name_zh;
  return phase == null ? "選部位" : `選部位・${phase}`;
}
