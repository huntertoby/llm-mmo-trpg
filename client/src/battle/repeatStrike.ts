// DD-2（#153，08 8.11）：雙匕首單體武器技的第二下（之後幾下）怎麼從事件認出來。純函式。
//
// 引擎在技能的全部效果結算完（第一下）之後，對同一個目標再發一次 `attack_rolled`（`Cast.extra_strikes`），
// 沒有另一個 `skill_used`。播放時把這一下切成新的一段、照普攻播（普攻雙匕首也是每個 `attack_rolled` 一段），
// 所以出招是兩次打擊；第一下打倒目標時引擎不打第二下、沒有第二個 `attack_rolled`，就只播一下。
//
// 認法：在一段技能（不是普攻）裡，同一個施放者對「這一段已經擲過命中的單位」又擲一次命中。
// 一次施放對同一個單位只擲一次命中（`Cast.roll_hits` 每個目標一次；衝撞每個穿過的敵人一次），
// 只有連擊武器多打的那幾下會重複。守護者攔下（`attack_intercepted`）時之後幾下打守護者，所以守護者也記進來。
// `vfx.ts` 的 `vfxFor` 與 `skillSequence.ts` 的 `splitSegments` 都用這裡，兩邊切出來的段一一對應。
import type { EventBase } from "../api/types";

/** 一段裡記下的「施放者已擲過命中的單位」。 */
export interface StrikeLedger {
  /** 這一段的施放者。 */
  readonly caster: string;
  /** 一般攻擊的段（不記、也不切）。 */
  readonly basic: boolean;
  readonly rolled: string[];
}

/** 把這個事件記進這一段（技能段裡施放者的命中判定、施放者被守護者攔下）。 */
export function noteStrike(seg: StrikeLedger | null, e: EventBase): void {
  if (seg === null || seg.basic || String(e.attacker_id) !== seg.caster) return;
  const id = e.type === "attack_rolled" ? e.target_id : e.type === "attack_intercepted" ? e.guardian_id : undefined;
  if (typeof id === "string" && !seg.rolled.includes(id)) seg.rolled.push(id);
}

/** 這個 `attack_rolled` 是不是連擊武器多打的那一下（要開新的一段、照普攻播）。 */
export function repeatsStrike(seg: StrikeLedger | null, e: EventBase): boolean {
  if (seg === null || seg.basic || e.type !== "attack_rolled" || String(e.attacker_id) !== seg.caster) return false;
  return typeof e.target_id === "string" && seg.rolled.includes(e.target_id);
}
