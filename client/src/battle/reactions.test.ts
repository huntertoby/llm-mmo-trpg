import { describe, expect, it } from "vitest";
import type { BattleResponse, Pending, ReactionRuleView } from "../api/types";
import { actionLabel } from "./actions";
import {
  costText,
  pendingAutoActions,
  queueAuto,
  REACTION_MODE_LABELS,
  ruleOfPending,
  ruleSummary,
  setModeAction,
  triggerEventText,
  uniqueRules,
} from "./reactions";
import { smallView, unit } from "./testFixtures";

function rule(reaction: string, mode: ReactionRuleView["mode"], over: Partial<ReactionRuleView> = {}): ReactionRuleView {
  return {
    reaction,
    name_zh: reaction,
    description_zh: "說明",
    event: "targeted_by_melee",
    trigger_zh: "被近戰攻擊命中時",
    mode,
    unless_stamina_below: null,
    stamina_cost: 10,
    mana_cost: 0,
    hp_cost_permille: 0,
    gear_source_zh: "",
    ...over,
  };
}

const pending: Pending = {
  kind: "reaction",
  unit_id: "unit_0001",
  reaction: "block",
  trigger_unit_id: "unit_0003",
  skill_id: null,
  trigger_event_seq: 7,
  stamina_cost: 10,
  mana_cost: 0,
  hp_cost_permille: 0,
};

describe("reaction settings", () => {
  it("builds the set_reaction_mode action for the hero", () => {
    expect(setModeAction("unit_0001", "block", "off")).toEqual({
      type: "set_reaction_mode",
      unit_id: "unit_0001",
      reaction: "block",
      mode: "off",
    });
    expect(Object.keys(REACTION_MODE_LABELS)).toEqual(["auto", "prompt", "off"]);
  });

  it("describes costs and the trigger of a rule", () => {
    expect(costText({ stamina_cost: 10, mana_cost: 0, hp_cost_permille: 0 })).toBe("耐力 10");
    expect(costText({ stamina_cost: 0, mana_cost: 3, hp_cost_permille: 50 })).toBe("法力 3、HP 5%");
    expect(costText({ stamina_cost: 0, mana_cost: 0, hp_cost_permille: 0 })).toBe("無代價");
    expect(ruleSummary(rule("block", "auto", { unless_stamina_below: 15 }))).toBe(
      "被近戰攻擊命中時・耐力 10・耐力低於 15 時不觸發",
    );
  });

  it("lists each reaction once and finds the rule of a pending question", () => {
    const hero = unit("unit_0001", "ally", 0, 0, {
      reaction_rules: [rule("block", "auto"), rule("block", "auto", { event: "targeted_by_attack" }), rule("oa", "prompt")],
    });
    expect(uniqueRules(hero).map((r) => r.reaction)).toEqual(["block", "oa"]);
    expect(ruleOfPending(hero, pending)?.reaction).toBe("block");
    expect(ruleOfPending(null, pending)).toBeNull();
  });
});

describe("'always automatic' queue", () => {
  const hero = unit("unit_0001", "ally", 0, 0, {
    reaction_rules: [rule("block", "prompt"), rule("oa", "auto"), rule("parry", "off")],
  });

  it("queues without duplicates", () => {
    expect(queueAuto(queueAuto([], "block"), "block")).toEqual(["block"]);
  });

  it("sends set_reaction_mode auto only for rules that are not already automatic", () => {
    const sent = pendingAutoActions(["block", "oa", "parry", "ghost"], hero);
    expect(sent.map((a) => (a.type === "set_reaction_mode" ? [a.reaction, a.mode] : null))).toEqual([
      ["block", "auto"],
      ["parry", "auto"],
    ]);
    expect(pendingAutoActions([], hero)).toEqual([]);
  });
});

describe("trigger event text", () => {
  const step = (seq: number, text?: string) =>
    ({ actor_id: "unit_0003", step: null, view: smallView(), events: [{ seq, round: 1, type: "x", ...(text ? { text } : {}) }] }) as never;

  it("finds the event that raised the question", () => {
    const res = { pending, steps: [step(6, "別的"), step(7, "  b 攻擊 A")] } as unknown as BattleResponse;
    expect(triggerEventText(res)).toBe("b 攻擊 A");
  });

  it("returns null when the sequence number is unknown or not in this response", () => {
    const none = { pending: { ...pending, trigger_event_seq: null }, steps: [] } as unknown as BattleResponse;
    expect(triggerEventText(none)).toBeNull();
    const missing = { pending, steps: [step(1, "x")] } as unknown as BattleResponse;
    expect(triggerEventText(missing)).toBeNull();
  });
});

describe("action labels", () => {
  it("labels set_reaction_mode", () => {
    const label = actionLabel(setModeAction("unit_0001", "block", "prompt"), smallView(), {});
    expect(label).toContain("詢問");
  });
});
