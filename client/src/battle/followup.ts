// 複合技能的第二段（Phase 3F-4b）：
// - 「動作 → 位移」「擊殺 → 接下一段」暫停時的選取：伺服器給的 `followup_options` 當成一個模式，
//   滑過會預覽（伺服器把原本的施放帶上這個選取重新模擬），點到就送 `/decision`；
// - 延遲段（蓄力）的倒數與預計範圍的文字與格子標記。
import type { Action, BattleResponse, ChargeOut, FollowupOption, Pending, Pos, StatusView } from "../api/types";
import { buildTargets, type ActionMode } from "./targeting";

export function isFollowupPending(pending: Pending | null): pending is Pending {
  return pending !== null && pending.kind === "followup";
}

/** 第二段的一個選取 → 模式用的動作（選取的欄位提到最上層，讓戰場上的格子、單位、方向能點）。 */
export function followupAction(pending: Pending, option: FollowupOption): Action {
  const t = option.followup_target;
  return {
    type: "use_skill",
    unit_id: pending.unit_id,
    skill_id: pending.skill_id ?? "",
    target_id: t.target_id ?? null,
    target_object_id: t.target_object_id ?? null,
    target_pos: t.target_pos ?? null,
    direction: t.direction ?? null,
    followup_target: t,
  } as Action;
}

export function followupMode(pending: Pending, options: readonly FollowupOption[], skillName: string): ActionMode {
  const actions = options.map((o) => followupAction(pending, o));
  return {
    key: `followup:${pending.skill_id ?? ""}`,
    kind: "skill",
    label: `${skillName}（第二段）`,
    skillId: pending.skill_id ?? null,
    actions,
    targets: buildTargets(actions),
  };
}

export function followupPromptText(skillName: string, optionCount: number): string {
  if (optionCount === 0) return `「${skillName}」的第二段目前沒有合法的選取，請放棄第二段。`;
  return `「${skillName}」的第一段已結算：在戰場上點選高亮的目標或格子（共 ${optionCount} 個可選）施展第二段，或放棄第二段。`;
}

/** 決定請求裡的第二段選取（取消時 `null`）。 */
export function followupTargetOf(pick: Action | null): Extract<Action, { type: "use_skill" }>["followup_target"] {
  if (pick === null || pick.type !== "use_skill") return null;
  return pick.followup_target ?? null;
}

// ---- 延遲段 -------------------------------------------------------------------

export const RELEASE_TEXT: Readonly<Record<string, string>> = {
  next_turn: "下回合開始時釋放",
  attacked: "下回合開始前被敵人攻擊就釋放（沒被攻擊就失效）",
};

export const CHARGING = "charging";

/** 單位身上蓄力狀態的說明（HUD、單位資訊）：「蓄力「蓄力斬」：下回合開始時釋放，以自己為中心
 * 影響 9 格」；`names` 是技能 ID → 名稱（沒有時不寫技能名）。 */
export function chargeStatusText(status: StatusView, names?: Readonly<Record<string, string>>): string {
  const skill = status.skill_id == null ? undefined : (names?.[status.skill_id] ?? undefined);
  const head = skill === undefined ? "蓄力" : `蓄力「${skill}」`;
  const when = RELEASE_TEXT[status.release ?? ""] ?? "等待釋放";
  return `${head}：${when}，以自己為中心影響 ${status.charge_tiles?.length ?? 0} 格`;
}

/** 還要幾回合釋放（1 ＝ 施放者下回合開始）；沒有蓄力時 `null`。 */
export function chargeCountdown(statuses: readonly StatusView[]): number | null {
  const s = statuses.find((x) => x.status_id === CHARGING);
  return s === undefined ? null : (s.remaining ?? 1);
}

/** 環境預告裡等待中的延遲段。 */
export function charges(response: BattleResponse | null): readonly ChargeOut[] {
  return response?.telegraph?.charges ?? [];
}

/** 延遲段預計範圍的格子（去重，依 y、x）。 */
export function chargeTiles(list: readonly ChargeOut[]): Pos[] {
  const seen = new Map<string, Pos>();
  for (const c of list) for (const p of c.tiles) seen.set(`${p.x},${p.y}`, p);
  return [...seen.values()].sort((a, b) => a.y - b.y || a.x - b.x);
}
