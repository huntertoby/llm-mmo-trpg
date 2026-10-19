// API 型別：由 OpenAPI 產生的 schema.d.ts 取別名；`events` 在 OpenAPI 中是任意 JSON，這裡手寫窄化。
import type { components } from "./schema";

type Schemas = components["schemas"];

export type BattleResponse = Schemas["BattleResponse"];
export type BattleView = Schemas["BattleView"];
export type TileView = Schemas["TileView"];
export type UnitView = Schemas["UnitView"];
export type ObjectView = Schemas["ObjectView"];
export type TrapView = Schemas["TrapView"];
export type StatusView = Schemas["StatusView"];
export type Pending = Schemas["Pending"];
export type Action = Schemas["Action"];
export type MoveAction = Schemas["Move"];
export type AttackAction = Schemas["Attack"];
export type UseSkillAction = Schemas["UseSkill"];
export type StepOut = Schemas["StepOut"];
export type Pos = Schemas["Pos"];
export type Team = Schemas["Team"];
export type Surface = Schemas["Surface"];
export type MapSummary = Schemas["MapSummary"];
export type BuildSummary = Schemas["BuildSummary"];
export type SkillCard = Schemas["SkillCard"];
/** openapi-typescript 把有預設值的欄位標成必填；建立戰鬥時 `max_rounds` 可省略（伺服器預設 30）。 */
export type CreateBattleRequest = Omit<Schemas["CreateBattleRequest"], "max_rounds"> & {
  max_rounds?: number;
};
export type Glossary = Schemas["Glossary"];
export type GlossaryEntry = Schemas["GlossaryEntry"];
export type PreviewOut = Schemas["PreviewOut"];
export type UseSkill = Schemas["UseSkill"];
export type Direction = Schemas["Direction"];
export type Awaiting = BattleResponse["awaiting"];
export type ReactionRuleView = Schemas["ReactionRuleView"];
export type ReactionMode = ReactionRuleView["mode"];
export type SetReactionModeAction = Schemas["SetReactionMode"];
export type InteractOption = Schemas["InteractOptionOut"];
export type TelegraphOut = Schemas["TelegraphOut"];
export type TelegraphChange = Schemas["TelegraphChangeOut"];
export type OrderSet = Schemas["OrderSet"];
export type TacticalOrder = Schemas["TacticalOrder"];
export type IgnoredOrder = Schemas["IgnoredOrder"];

/** 所有事件共有的欄位（`text` 只在有中文描述時存在）。 */
export interface EventBase {
  seq: number;
  round: number;
  type: string;
  text?: string;
  [key: string]: unknown;
}

export type MoveMode = "walk" | "forced" | "teleport";

export interface UnitMovedEvent extends EventBase {
  type: "unit_moved";
  unit_id: string;
  from_pos: Pos;
  to_pos: Pos;
  mode: MoveMode;
  cost: number;
}

/** `StepOut.events` 的元素 → 窄化的事件（只認得前端需要的型別，其他保持 `EventBase`）。 */
export function asEvent(raw: Record<string, unknown>): EventBase {
  return raw as EventBase;
}

export function isUnitMoved(e: EventBase): e is UnitMovedEvent {
  return e.type === "unit_moved";
}
