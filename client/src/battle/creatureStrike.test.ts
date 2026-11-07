// QK-5（QK-4 待決 2）：異形攻擊片段的出手格對到命中那一刻。
import { describe, expect, it } from "vitest";
import type { BattleView, Pos } from "../api/types";
import { RIG_KEYS } from "../render/inkCreature";
import { creatureAttackHitU, creatureClipInfo, creatureClips } from "../render/qCreatureAnim";
import { skillTimeline, type StrikeOf } from "./skillSequence";
import { vfxFor } from "./vfx";

const at = (x: number, y: number): Pos => ({ x, y });
const view = { units: [{ id: "m", pos: at(2, 2), team: "enemy" }, { id: "h", pos: at(3, 2), team: "ally" }], tiles: [] } as unknown as BattleView;
const ev = [
  { seq: 1, round: 1, type: "attack_rolled", attacker_id: "m", target_id: "h", hit: true },
  { seq: 2, round: 1, type: "damage_dealt", target_id: "h", source_id: "m", element: "physical", amount: 5 },
];

describe("QK-5 異形攻擊的出手格", () => {
  it("16 款 × 每個攻擊片段：出手格在 (0, 1) 之間、兩次算一樣", () => {
    for (const key of RIG_KEYS)
      for (const clip of creatureClips(key).filter((c) => c.startsWith("atk:"))) {
        const u = creatureAttackHitU(key, clip);
        expect(u, `${key} ${clip}`).toBeGreaterThan(0);
        expect(u, `${key} ${clip}`).toBeLessThan(1);
        expect(creatureAttackHitU(key, clip)).toBe(u);
        expect(creatureClipInfo(key, clip)!.ms).toBeGreaterThan(0);
      }
  });

  it("時間軸：異形出招那一列＝異形片段的長度，命中點＝出手格，蓄力不播；特效、扣血對齊命中點", () => {
    const strikeOf: StrikeOf = (id) => (id === "m" ? { ms: 680, hitAt: 0.5 } : null);
    const tl = skillTimeline(ev, view, {}, vfxFor(ev, view, {}), () => "bare", () => null, strikeOf)!;
    const rows = tl.rows.filter((r) => r.unitId === "m");
    const strike = rows.find((r) => r.strike)!;
    expect(rows.filter((r) => !r.strike && !r.recover && !r.still)).toHaveLength(0);
    expect(strike.ms).toBe(680);
    expect(strike.hitMs! - strike.startMs).toBeCloseTo(340, 6);
    expect(tl.vfx.hits[0]!.atMs).toBeCloseTo(strike.hitMs!, 6);
    // 沒給（人形）照舊有蓄力
    const plain = skillTimeline(ev, view, {}, vfxFor(ev, view, {}), () => "bare", () => null)!;
    expect(plain.rows.some((r) => !r.strike && !r.recover)).toBe(true);
  });
});
