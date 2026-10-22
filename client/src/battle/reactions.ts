// 反應規則設定與反應詢問（純函式）。
// 主角的每條反應規則可設為「自動／詢問／關閉」，用 `set_reaction_mode` 動作送出（只能在自己的回合）。
// 詢問視窗的「之後都自動」：詢問時不能送動作（伺服器在等決定），所以先記在本地的佇列，
// 等到下一次輪到主角時才送出 `set_reaction_mode`。
import type {
  Action,
  BattleResponse,
  EventBase,
  Pending,
  ReactionMode,
  ReactionRuleView,
  UnitView,
} from "../api/types";
import { asEvent } from "../api/types";

export const REACTION_MODES: readonly ReactionMode[] = ["auto", "prompt", "off"];

export const REACTION_MODE_LABELS: Readonly<Record<ReactionMode, string>> = {
  auto: "自動",
  prompt: "詢問",
  off: "關閉",
};

export function setModeAction(heroId: string, reaction: string, mode: ReactionMode): Action {
  return { type: "set_reaction_mode", unit_id: heroId, reaction, mode };
}

/** 接受時要付出的代價（耐力／法力／HP）；沒有代價時「無代價」。 */
export function costText(c: { stamina_cost: number; mana_cost: number; hp_cost_permille: number }): string {
  const parts: string[] = [];
  if (c.stamina_cost > 0) parts.push(`耐力 ${c.stamina_cost}`);
  if (c.mana_cost > 0) parts.push(`法力 ${c.mana_cost}`);
  if (c.hp_cost_permille > 0) parts.push(`HP ${c.hp_cost_permille / 10}%`);
  return parts.length === 0 ? "無代價" : parts.join("、");
}

/** 規則的一行說明：「被近戰攻擊命中時・耐力 10・耐力低於 15 時不觸發」。 */
export function ruleSummary(rule: ReactionRuleView): string {
  const parts = [rule.trigger_zh, costText(rule)];
  if (rule.unless_stamina_below != null) parts.push(`耐力低於 ${rule.unless_stamina_below} 時不觸發`);
  return parts.join("・");
}

/** 反應規則的「來自裝備」說明（Phase 3G-G3b，授予或擴充這條反應的物品與詞條）；不是裝備來的為空字串。 */
export function gearSourceText(rule: Pick<ReactionRuleView, "gear_source_zh">): string {
  const source = rule.gear_source_zh ?? "";
  return source === "" ? "" : `來自裝備・${source}`;
}

/** 主角的規則（同一個反應可能有多條規則，介面只列一個）。 */
export function uniqueRules(hero: UnitView): ReactionRuleView[] {
  const seen = new Set<string>();
  return hero.reaction_rules.filter((r) => {
    if (seen.has(r.reaction)) return false;
    seen.add(r.reaction);
    return true;
  });
}

/** 詢問對應的規則（要顯示說明與觸發條件）。 */
export function ruleOfPending(hero: UnitView | null, pending: Pending): ReactionRuleView | null {
  return hero?.reaction_rules.find((r) => r.reaction === pending.reaction) ?? null;
}

/** 輪到主角時要補送的 `set_reaction_mode`：佇列中的反應，目前還不是「自動」的。 */
export function pendingAutoActions(queue: readonly string[], hero: UnitView): Action[] {
  return queue.flatMap((reaction) => {
    const rule = hero.reaction_rules.find((r) => r.reaction === reaction);
    return rule === undefined || rule.mode === "auto" ? [] : [setModeAction(hero.id, reaction, "auto")];
  });
}

/** 把反應加進佇列（不重複）。 */
export function queueAuto(queue: readonly string[], reaction: string): string[] {
  return queue.includes(reaction) ? [...queue] : [...queue, reaction];
}

/** 引發詢問的事件（`trigger_event_seq`）在這次回應中的中文描述；找不到時 `null`。 */
export function triggerEventText(res: BattleResponse): string | null {
  const seq = res.pending?.trigger_event_seq;
  if (seq == null) return null;
  for (const step of res.steps) {
    for (const raw of step.events) {
      const e: EventBase = asEvent(raw);
      if (e.seq === seq && e.text !== undefined) return e.text.trim();
    }
  }
  return null;
}
