// API 型別：由 OpenAPI 產生的 schema.d.ts 取別名；`events` 在 OpenAPI 中是任意 JSON，這裡手寫窄化。
import type { components } from "./schema";

type Schemas = components["schemas"];

export type BattleResponse = Schemas["BattleResponse"];
export type BattleView = Schemas["BattleView"];
export type TileView = Schemas["TileView"];
export type UnitView = Schemas["UnitView"];
export type ObjectView = Schemas["ObjectView"];
export type TrapView = Schemas["TrapView"];
export type ZoneView = Schemas["ZoneView"];
export type ActivationView = Schemas["ActivationView"];
export type GrantedSkillView = Schemas["GrantedSkillView"];
export type StatusView = Schemas["StatusView"];
export type Pending = Schemas["Pending"];
export type Action = Schemas["Action"];
export type MoveAction = Schemas["Move"];
export type AttackAction = Schemas["Attack"];
export type UseSkillAction = Schemas["UseSkill-Output"];
export type StepOut = Schemas["StepOut"];
export type Pos = Schemas["Pos"];
export type Team = Schemas["Team"];
export type Surface = Schemas["Surface"];
export type MapSummary = Schemas["MapSummary"];
export type BuildSummary = Schemas["BuildSummary"];
export type SkillCard = Schemas["SkillCard"];
export type SkillReasons = Schemas["SkillReasons"];
/** openapi-typescript 把有預設值的欄位標成必填；建立戰鬥時 `max_rounds` 可省略（伺服器預設 30），
 * 技能工坊的 `custom_skills`、`replace_skills` 也可省略（預設空串列，Phase 3F-1）。 */
export type CreateBattleRequest = Omit<
  Schemas["CreateBattleRequest"],
  "max_rounds" | "custom_skills" | "replace_skills"
> & {
  max_rounds?: number;
  custom_skills?: Record<string, unknown>[];
  replace_skills?: string[];
};
// 技能工坊（Phase 3F）
export type StepId = Schemas["StepId"];
export type FieldSpec = Schemas["FieldSpec"];
export type FieldType = Schemas["FieldType"];
export type Choice = Schemas["Choice"];
export type StepOptions = Schemas["StepOptions"];
export type DraftOptions = Schemas["DraftOptions"];
export type WorkshopCheck = Schemas["WorkshopCheck"];
export type WorkshopProblem = Schemas["Problem"];
export type BudgetSummary = Schemas["BudgetSummary"];
export type BudgetLine = Schemas["BudgetLine"];
export type WorkshopArena = Schemas["WorkshopArena"];
export type ArenaOpponents = Schemas["ArenaOpponents"];
export type WorkshopRandom = Schemas["WorkshopRandom"];
export type WorkshopRandomRequest = Schemas["WorkshopRandomRequest"];
export type WorkshopExport = Schemas["WorkshopExport"];
export type SkillRarity = Schemas["SkillRarity"];
export type Glossary = Schemas["Glossary"];
export type GlossaryEntry = Schemas["GlossaryEntry"];
export type PreviewOut = Schemas["PreviewOut"];
export type UseSkill = Schemas["UseSkill-Output"];
export type Direction = Schemas["Direction"];
export type Awaiting = BattleResponse["awaiting"];
export type FollowupTarget = Schemas["FollowupTarget"];
export type FollowupOption = Schemas["FollowupOptionOut"];
export type ChargeOut = Schemas["ChargeOut"];
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

export type MoveMode = "walk" | "forced" | "teleport" | "teleported" | "dash" | "leap" | "swap" | "shadowstep";
export type Facing = UnitView["facing"];

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
// roguelite 一輪（Phase 3-5c-1）
export type RunResponse = Schemas["RunResponse"];
export type RunBattleResponse = Schemas["RunBattleResponse"];
export type RunHero = Schemas["HeroOut"];
export type RunNode = Schemas["NodeOut"];
export type RunOffer = Schemas["OfferOut"];
export type RunPlan = Schemas["BattlePlanOut"];
export type RunRecord = Schemas["BattleRecord"];
export type RunSaveOut = Schemas["SaveOut"];
export type RunSaveSummary = Schemas["SaveSummary"];
export type AttributeId = Schemas["Attribute"];
/** `POST /api/runs/{id}/choice` 的請求（工坊另有同名的 `Choice`，所以加前綴）。 */
export type RunChoice =
  | Schemas["LevelUpChoice"]
  | Schemas["RerollChoice"]
  | Schemas["PickChoice"]
  | Schemas["LeaveChoice"];
/** 開新一輪；`attributes` 省略時伺服器把開局點數全部點在技能最常用的縮放屬性。 */
export type CreateRunRequest = Omit<Schemas["CreateRunRequest"], "attributes"> & {
  attributes?: Partial<Record<AttributeId, number>>;
};
