// QK-4：頭目 Q 版（docs/art/sample/qBoss.js 的移植）：範本 → 頭目、階段、確定性、片段、減少動態、戰場接法。
import { describe, expect, it } from "vitest";
import { creatureCanvasSize, creatureIdlePose, creatureKey, creatureTop, drawCreature, resolveCreature } from "./inkCreature";
import { BOSS_BOX, BOSS_CLIPS, PLATES, bossAttackClip, bossAct, bossFrameU, bossOf, plateAnchor } from "./qBoss";

function stream(draw: (c: CanvasRenderingContext2D) => void): string {
  const out: string[] = [];
  const ctx = new Proxy({} as Record<string, unknown>, {
    get: (t, p: string) => (p in t ? t[p] : (...a: unknown[]) => void out.push(`${p}(${a.map((x) => (typeof x === "number" ? x.toFixed(3) : String(x))).join(",")})`)),
    set: (t, p: string, v) => ((t[p] = v), out.push(`${p}=${String(v)}`), true),
  }) as unknown as CanvasRenderingContext2D;
  draw(ctx);
  return out.join(";");
}
const HEART = { body: "wisp", material: "crystal", element: "fire", size: "huge", traits: ["core"], status_traits: { molten_shell: ["crust"] } };
const LORD = { body: "golem", material: "crystal", size: "huge", traits: ["core"] };

describe("QK-4：頭目", () => {
  it("範本 → 頭目畫法；階段照 boss_phase，沒有時灰燼之心看熔殼；不認得的範本 → 一般異形", () => {
    expect(bossOf("ashen_heart", null, ["molten_shell"])).toEqual({ id: "ah", phase: 1 });
    expect(bossOf("ashen_heart", null, [])).toEqual({ id: "ah", phase: 2 });
    expect(bossOf("ashen_heart", 3)).toEqual({ id: "ah", phase: 3 });
    expect(bossOf("ashen_heart", 9, ["molten_shell"])).toEqual({ id: "ah", phase: 1 });
    expect(bossOf("rift_shard_lord", 4)).toEqual({ id: "sl", phase: 4 });
    expect(bossOf("rift_shard_lord", undefined)).toEqual({ id: "sl", phase: 1 });
    expect(bossOf("hound_alpha", 1)).toBeNull();
    const r = resolveCreature({ look: HEART, rarity: "legendary", template: "ashen_heart", bossPhase: 2, field: true });
    expect(r.boss).toEqual({ id: "ah", phase: 2 });
    expect(creatureKey(r, "west")).not.toBe(creatureKey({ ...r, boss: { id: "ah", phase: 3 } }, "west"));
    expect(creatureCanvasSize(r)).toEqual({ w: BOSS_BOX.w, h: BOSS_BOX.h, foot: BOSS_BOX.foot });
    expect(creatureTop(r)).toBe(BOSS_BOX.top.ah);
    expect(resolveCreature({ look: LORD, template: "shard_golem" }).boss).toBeUndefined();
  });

  it("確定性：每個階段 × 每個片段 × 每一格，畫兩次指令流相同；不出錯", () => {
    for (const [id, phases] of [["ah", [1, 2, 3]], ["sl", [1, 2, 3, 4]]] as const)
      for (const phase of phases)
        for (const clip of ["idle", "static", ...BOSS_CLIPS[id], "nope"])
          for (const u of [0, 0.25, 0.5, 0.75, 1]) {
            const a = stream((c) => bossAct(c, id, clip, u, { phase }));
            expect(a.length).toBeGreaterThan(50);
            expect(stream((c) => bossAct(c, id, clip, u, { phase }))).toBe(a);
          }
  });

  it("殼片 10 塊；脫落位置只由名稱決定（和呼吸無關），落點不超過 ±36", () => {
    expect(PLATES).toHaveLength(10);
    for (const p of PLATES) {
      expect(plateAnchor(p, 0, 0.5, 0)).toEqual(plateAnchor(p, 0, 0.5, 0.9));
      expect(Math.abs(plateAnchor(p, 0, 1, 0).x)).toBeLessThanOrEqual(36);
    }
  });

  it("片段：12 格／秒、倒下停在最後一格；減少動態的倒下直接最後一格", () => {
    expect(bossFrameU("death", 0)).toBe(0);
    expect(bossFrameU("death", 99_999)).toBe(1);
    expect(bossFrameU("idle", 5278)).toBe(bossFrameU("idle", 0));
    expect(stream((c) => bossAct(c, "sl", "death", 0, { reduce: true }))).toBe(stream((c) => bossAct(c, "sl", "death", 1, { reduce: true })));
    expect(stream((c) => bossAct(c, "ah", "spout", 0.5, { reduce: true, fxAll: true }))).not.toBe(stream((c) => bossAct(c, "ah", "spout", 0.5, { fxAll: true })));
  });

  it("依動作類型挑攻擊：灰燼之心範圍＝噴發、遠程＝火焰箭、相鄰普攻＝殼撞（只有第 1 階段）；碎晶之主遠程＝聚雷、普攻＝揮擊", () => {
    expect(bossAttackClip("ah", "area", 1)).toBe("spout");
    expect(bossAttackClip("ah", "cast", 2)).toBe("firebolt");
    expect(bossAttackClip("ah", "melee", 1)).toBe("ram");
    expect(bossAttackClip("ah", "melee", 2)).toBe("firebolt");
    expect(bossAttackClip("sl", "cast", 2)).toBe("thunder");
    expect(bossAttackClip("sl", "melee", 2)).toBe("swing");
  });

  it("戰場接法：drawCreature 走頭目畫法；atk:@類型、受擊、倒下、待機都畫得出來；飛向目標的特效只在 fxAll 時畫", () => {
    const r = resolveCreature({ look: LORD, rarity: "legendary", template: "rift_shard_lord", bossPhase: 2 });
    for (const pose of [null, { clip: "atk:@cast", u: 0.6 }, { clip: "hit", u: 0 }, { clip: "death", u: 1 }, creatureIdlePose(r, 1234, "u9"), { flash: 0.85 }]) expect(stream((c) => drawCreature(c, r, pose)).length).toBeGreaterThan(100);
    const field = stream((c) => drawCreature(c, r, { clip: "atk:@cast", u: 0.6 }));
    const all = stream((c) => drawCreature(c, r, { clip: "atk:@cast", u: 0.6, fxAll: true }));
    expect(all.length).toBeGreaterThan(field.length);
    expect(stream((c) => drawCreature(c, r, null, "only")).length).toBeLessThan(200); // 只有影子
    expect(creatureIdlePose(r, 0, "u9")).toEqual(creatureIdlePose(r, 0, "u9"));
  });
});
