import { describe, expect, it } from "vitest";
import type { StepOut } from "../api/types";
import { logLines, summarize } from "./log";
import { groupLog, type LogDivider, type LogGroup } from "./logGroups";
import { smallView } from "./testFixtures";
import { unitNames } from "./units";

const names = unitNames(smallView());
let seq = 0;
const ev = (type: string, round: number, extra: Record<string, unknown> = {}, text?: string) => ({
  seq: seq++,
  round,
  type,
  ...(text === undefined ? {} : { text }),
  ...extra,
});
const step = (...events: Record<string, unknown>[]): Pick<StepOut, "events"> => ({ events });
const A = "unit_0001";
const E1 = "unit_0003";

const turn = (r: number, id: string, text: string) => ev("turn_started", r, { unit_id: id }, `— ${text} 的回合（AP 3）`);
const skill = (r: number, id: string, text: string) =>
  ev("skill_used", r, { unit_id: id, skill_id: "s", tiles: [{ x: 2, y: 1 }] }, text);
const attack = (r: number, from: string, to: string, hit: boolean, skillId: string | null) =>
  ev(
    "attack_rolled",
    r,
    { attacker_id: from, target_id: to, skill_id: skillId, hit },
    `${from} 攻擊 ${to}：d20=17 修正 +0 熟練 +2 = 19（目標 11）→ ${hit ? "命中" : "失手"}`,
  );
const damage = (r: number, to: string, amount: number) =>
  ev("damage_dealt", r, { target_id: to, source_id: A, amount }, `${to} 受到 ${amount} 點物理傷害［骰 4］，HP 30 → 22`);

describe("summarize", () => {
  it("shortens roll events to subject and verdict, keeping the full text elsewhere", () => {
    expect(summarize("attack_rolled", "弓手 攻擊 盜賊：d20=17 修正 +0 熟練 +2 = 19（目標 11）→ 命中")).toBe(
      "弓手 攻擊 盜賊 → 命中",
    );
    expect(summarize("status_save_rolled", "甲（抵抗 體質 12）：d20=3 修正 +0 = 3 → 抵抗失敗")).toBe("甲 → 抵抗失敗");
    expect(summarize("initiative_rolled", "先攻：戰士 d20=1 +1 = 2")).toBe("先攻：戰士 2");
  });
  it("drops dice and modifier brackets from damage and heal lines", () => {
    expect(summarize("damage_dealt", "盜賊 受到 7 點雷電傷害［骰 2+2］（天氣 ×1.2），HP 32 → 25")).toBe(
      "盜賊 受到 7 點雷電傷害，HP 32 → 25",
    );
    expect(summarize("healed", "甲 回復 5 點 HP，HP 1 → 6")).toBeUndefined();
    expect(summarize("unit_downed", "＊ 甲 倒下了！")).toBeUndefined();
  });
});

describe("logLines metadata", () => {
  it("fills type, team, tone, units, tiles and the action flag", () => {
    const lines = logLines(
      [step(skill(1, A, "A 施放「閃電」"), attack(1, A, E1, true, "s"), attack(1, A, E1, false, null), damage(1, E1, 8))],
      names,
    );
    expect(lines.map((l) => l.type)).toEqual(["skill_used", "attack_rolled", "attack_rolled", "damage_dealt"]);
    expect(lines.map((l) => l.action === true)).toEqual([true, false, true, false]);
    expect(lines[0]!.tiles).toEqual([{ x: 2, y: 1 }]);
    expect(lines[1]!.team).toBe("ally");
    expect(lines[3]!.team).toBe("enemy"); // 傷害以被打的單位為主
    expect(lines[3]!.tone).toBe("damage");
    expect(lines[3]!.unitIds).toEqual([E1, A]);
    expect(lines[1]!.tone).toBe("hit");
    expect(lines[2]!.tone).toBe("miss");
    expect(lines[1]!.text).toContain("d20=17"); // 完整文字保留
  });
  it("marks merged walks as actions with start and end tiles", () => {
    const walk = (fx: number, tx: number) =>
      ev("unit_moved", 1, { unit_id: A, from_pos: { x: fx, y: 0 }, to_pos: { x: tx, y: 0 }, mode: "walk", cost: 1 });
    const [line] = logLines([step(walk(0, 1), walk(1, 2))], names);
    expect(line!.action).toBe(true);
    expect(line!.tiles).toEqual([
      { x: 0, y: 0 },
      { x: 2, y: 0 },
    ]);
    expect(line!.team).toBe("ally");
  });
});

describe("groupLog", () => {
  const sample = () =>
    logLines(
      [
        step(
          turn(1, A, "A"),
          skill(1, A, "A 施放「閃電」"),
          attack(1, A, E1, true, "s"),
          damage(1, E1, 8),
          ev("unit_downed", 1, { unit_id: E1 }, "＊ 敵 倒下了！"),
          attack(1, A, E1, false, null),
          ev("turn_ended", 1, { unit_id: A }, "A 結束回合"),
          turn(1, E1, "敵"),
          ev("status_applied", 1, { target_id: E1, status_id: "poison" }, "敵 中毒"),
          ev("environment_started", 1, {}, "～ 環境回合 ～"),
          ev("surface_changed", 2, {}, "(1, 1) 出現了水"),
        ),
      ],
      names,
    );

  it("groups results under their action head, with round and turn dividers", () => {
    const items = groupLog(sample());
    expect(items.map((i) => i.kind)).toEqual([
      "round",
      "turn",
      "group", // 技能 ＋ 命中 ＋ 傷害 ＋ 倒下
      "group", // 普攻
      "group", // 結束回合（單獨一行）
      "turn",
      "group", // 回合開始時的狀態（單獨一行）
      "turn", // 環境回合
      "round",
      "group",
    ]);
    const skillGroup = items[2] as LogGroup;
    expect(skillGroup.head.type).toBe("skill_used");
    expect(skillGroup.children.map((c) => c.type)).toEqual(["attack_rolled", "damage_dealt", "unit_downed"]);
    expect(skillGroup.unitIds).toEqual([A, E1]);
    expect(skillGroup.tiles).toContainEqual({ x: 2, y: 1 });
    expect((items[3] as LogGroup).head.type).toBe("attack_rolled");
    expect((items[3] as LogGroup).isAction).toBe(true);
    expect((items[4] as LogGroup).isAction).toBe(false);
  });

  it("colours turn dividers by the acting team and strips the dash", () => {
    const items = groupLog(sample());
    const turns = items.filter((i): i is LogDivider => i.kind === "turn");
    expect(turns.map((t) => t.text)).toEqual(["A 的回合（AP 3）", "敵 的回合（AP 3）", "環境回合"]);
    expect(turns[0]!.team).toBe("ally");
    expect(turns[1]!.team).toBe("enemy");
  });

  it("returns nothing for no lines and groups restored history the same way", () => {
    expect(groupLog([])).toEqual([]);
    const restored = logLines([step(skill(1, A, "x"), damage(1, E1, 1))], names);
    expect(groupLog(restored).filter((i) => i.kind === "group")).toHaveLength(1);
  });
});
