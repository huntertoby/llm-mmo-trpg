// 換地圖時主角播哪一段（Phase 6M-4）：走進門格＝進門／出門；走進邊緣出口＝走出畫面邊／從對面入口走進來；其他（傳送石、離開實地地圖）照舊只淡出淡入。
// 純函式；時間軸在 render/doorClips.ts。
import type { Facing, FieldView, Pos } from "../api/types";
import { ARRIVE_MS, FADE_LEAD_MS, LEAVE_MS, STAGE_FADE_MS, type TransitKind } from "../render/doorClips";
import { FIELD_HERO } from "./fieldModel";

export interface MapTransit {
  kind: TransitKind;
  /** 走進門格／出口格的方向（進門時轉身朝這個方向；新地圖從這個方向走進來）。 */
  facing: Facing;
}

const FACING_OF: Readonly<Record<FieldView["me"]["facing"], Facing>> = { n: "north", e: "east", s: "south", w: "west" };

/** 伺服器的朝向（n/e/s/w）→ 畫面的朝向。 */
export function fieldFacing(f: FieldView["me"]["facing"]): Facing {
  return FACING_OF[f];
}

/** 抵達新地圖時的朝向：邊緣入口照走進來的方向；出門照伺服器給的朝向（不轉身）。 */
export function arriveFacing(t: MapTransit, after: FieldView): Facing {
  return t.kind === "edge" ? t.facing : fieldFacing(after.me.facing);
}

/** 從 `from` 走到相鄰的 `to` 的方向；不相鄰或同一格時 `null`。 */
export function stepFacing(from: Pos, to: Pos): Facing | null {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (Math.abs(dx) + Math.abs(dy) !== 1) return null;
  return dx > 0 ? "east" : dx < 0 ? "west" : dy > 0 ? "south" : "north";
}

/** 需要的繪製器功能（BattleRenderer 的子集，測試可以換成假的）。 */
export interface TransitRenderer {
  playLeave(unitId: string, kind: TransitKind, facing: Facing, ms: number, skip: () => boolean): Promise<void>;
  playArrive(unitId: string, kind: TransitKind, facing: Facing, ms: number, skip: () => boolean): Promise<void>;
  nextDraw(timeoutMs: number): Promise<void>;
}

const wait = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));

/**
 * 離開：小人片段 `LEAVE_MS` 開始後 `FADE_LEAD_MS` 畫面開始淡出（`STAGE_FADE_MS`），兩者都結束才回傳（之後換地圖）。
 * 回傳時已經過 max(LEAVE_MS, FADE_LEAD_MS ＋ STAGE_FADE_MS) ＝ 300 毫秒。
 */
export async function leaveMap(renderer: TransitRenderer | null, t: MapTransit, setFading: (on: boolean) => void, skip: () => boolean): Promise<void> {
  const clip = renderer?.playLeave(FIELD_HERO, t.kind, t.facing, LEAVE_MS, skip) ?? Promise.resolve();
  await wait(FADE_LEAD_MS);
  setFading(true);
  await Promise.all([clip, wait(STAGE_FADE_MS)]);
}

/** 抵達：等新地圖畫好，和畫面淡入同時播抵達片段（出門／從對面入口走進來一步）。 */
export async function arriveMap(ref: { current: TransitRenderer | null }, t: MapTransit, after: FieldView, skip: () => boolean): Promise<void> {
  const r = ref.current;
  if (r === null) return;
  await r.nextDraw(STAGE_FADE_MS);
  await ref.current?.playArrive(FIELD_HERO, t.kind, arriveFacing(t, after), ARRIVE_MS, skip);
}

/**
 * 這一段走完之後換了地圖：最後一格是門＝進門，是出口＝邊緣出口，其他 `null`。
 * `from` ＝ 最後一步的起點（沒有走任何一步時用目前位置，方向照目前的朝向）。
 */
export function mapTransit(before: FieldView, from: Pos, last: Pos | undefined): MapTransit | null {
  if (last === undefined) return null;
  const facing = stepFacing(from, last) ?? FACING_OF[before.me.facing];
  if (before.doors.some((d) => d.x === last.x && d.y === last.y)) return { kind: "door", facing };
  if (before.exits.some((e) => e.cells.some(([x, y]) => x === last.x && y === last.y))) return { kind: "edge", facing };
  return null;
}
