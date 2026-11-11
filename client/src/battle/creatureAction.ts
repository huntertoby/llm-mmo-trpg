// CB-2b：異形出招的動作類型（美術 PM `docs/art/敵人招式動畫需求.md` 第 1 節）。依序判斷，先符合先用；只影響畫面，不動戰鬥結果，也不多一個技能資料欄位。
import { creatureAttackTypeOf, type CreatureAttackType } from "../render/creaturePose";

/** 靠原語挑不出衝鋒、但內容是衝鋒的指定招（第 5 條；放在這裡不放技能資料，LLM 與 YAML 都碰不到）。 */
export const CREATURE_CHARGE_SKILLS: ReadonlySet<string> = new Set(["skill_battering_ram", "skill_plunging_strike"]);

const WARP_PRIMITIVES: readonly string[] = ["teleport", "shadowstep", "swap", "swap_any"];
const CHARGE_PRIMITIVES: readonly string[] = ["dash", "charge_through", "leap"];

export interface CreatureActionInput {
  basic: boolean;
  skillId: string | null;
  /** 這一段的原語（卡上的順序；沒有卡時由事件推）。 */
  primitives: readonly string[];
  /** 這一段的形狀 ID。 */
  shape: string;
  /** 人形的出招片段（第 6 條照現行用）。 */
  strikeClip: string;
  /** 施放者到目標的距離。 */
  dist: number | null;
}

/**
 * 挑法順序：召喚 → 位移 → 衝鋒原語 → 錐形＝吐息 → 指定招 → 其餘照現行。普攻不走前五條（一律普攻片段，遠程普攻照現行）。
 * CB-3（`docs/art/異形第二種近戰移植需求.md` 第 3 節）：走到「其餘」而且是單體近戰技能（不是普攻、形狀 `single`、目標相鄰、照現行會播普攻片段）
 * → `melee2`（第二種近戰；身形沒有第二種時 `attackClipFor` 退回第一種）。同一隻的兩招單體近戰技能共用。只看這一招的資料，不用亂數。
 */
export function creatureActionOf(s: CreatureActionInput): CreatureAttackType {
  if (!s.basic) {
    const has = (ids: readonly string[]): boolean => s.primitives.some((p) => ids.includes(p));
    if (s.primitives.includes("summon")) return "summon";
    if (has(WARP_PRIMITIVES)) return "blink";
    if (has(CHARGE_PRIMITIVES)) return "charge";
    if (s.shape === "cone") return "breath";
    if (s.skillId !== null && CREATURE_CHARGE_SKILLS.has(s.skillId)) return "charge";
  }
  const type = creatureAttackTypeOf(s.strikeClip, s.dist);
  return !s.basic && type === "melee" && s.shape === "single" && s.dist === 1 ? "melee2" : type;
}

const SLIDE_MODES: readonly unknown[] = ["dash", "leap"];
const WARP_MODES: readonly unknown[] = ["teleport", "shadowstep", "swap"];

/** 施放者在這一段自己的位移：`slide`＝引擎已經把身體帶過去（片段不能再往前衝）；`warp`＝瞬間換格（閃現片段跟著傳送播）；`null`＝沒動。 */
export function casterMoveOf(casterId: string, events: ReadonlyArray<Record<string, unknown>>): "slide" | "warp" | null {
  for (const e of events) {
    if (e.type !== "unit_moved" || e.unit_id !== casterId) continue;
    if (SLIDE_MODES.includes(e.mode)) return "slide";
    if (WARP_MODES.includes(e.mode)) return "warp";
  }
  return null;
}
