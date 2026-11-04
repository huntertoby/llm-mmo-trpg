// 6R-F（前端審查第 7、8 點）：變體一律用 variantHash 挑（不再 `seedOf % n`）；反應合併時變體、閃避方向跟著升級。
import { describe, expect, it } from "vitest";
import { variantHash } from "../render/attackVariants";
import { seedOf } from "../render/inkStyle";
import { npcFidgetPick, ROLE_FIDGETS } from "../render/npcFidgets";
import { arcAt } from "../render/statusAnim";
import { readSources, stripTsComments } from "../test/sourceScan";
import { upgradeReact, type ReactKind } from "./vfx";

type R = { kind: ReactKind; seq: number; side?: 1 | -1; variant?: number };

describe("upgradeReact (6R-F; shared by addReact and the last-moment merge)", () => {
  it("upgrades kind, seq, variant and side together", () => {
    const old: R = { kind: "dodge", seq: 2, side: 1, variant: 0 };
    upgradeReact(old, { kind: "down", seq: 7, side: -1, variant: 2 });
    expect(old).toEqual({ kind: "down", seq: 7, side: -1, variant: 2 });
  });

  it("a stronger reaction without side/variant clears the old ones (they belonged to the weaker event)", () => {
    const old: R = { kind: "dodge", seq: 2, side: -1, variant: 3 };
    upgradeReact(old, { kind: "block", seq: 4 });
    expect(old).toEqual({ kind: "block", seq: 4 });
  });

  it("never downgrades", () => {
    const old: R = { kind: "down", seq: 7, variant: 1 };
    upgradeReact(old, { kind: "hit", seq: 9, side: 1, variant: 4 });
    expect(old).toEqual({ kind: "down", seq: 7, variant: 1 });
  });
});

describe("variant picks use variantHash, never seedOf % n (6R-F)", () => {
  it("NPC fidgets: the pick is variantHash of scene:id:n", () => {
    for (let n = 1; n < 40; n++) {
      const list = ROLE_FIDGETS.town;
      expect(npcFidgetPick("town_a", "npc_1", "town", n)).toBe(list[variantHash(`town_a:npc_1:${n}`) % list.length]);
    }
  });

  it("NPC fidgets: consecutive picks are not locked to a rotation (same pick two apart ≈ 1/3 for 3 kinds)", () => {
    let same = 0;
    let total = 0;
    for (let u = 0; u < 20; u++) {
      const picks = Array.from({ length: 60 }, (_, n) => npcFidgetPick("town_a", `npc_${u}`, "town", n + 1));
      for (let i = 2; i < picks.length; i++) {
        total += 1;
        if (picks[i] === picks[i - 2]) same += 1;
      }
    }
    expect(same / total).toBeGreaterThan(0.2);
    expect(same / total).toBeLessThan(0.47);
  });

  it("charged status arcs pick their shape with variantHash", () => {
    let found = 0;
    for (let ms = 0; ms < 20000 && found < 5; ms += 7) {
      const p = arcAt("u_x", ms);
      if (p === null) continue;
      found += 1;
      expect(["arc0", "arc1", "arc2"]).toContain(p.tex);
    }
    expect(found).toBeGreaterThan(0);
  });

  it("no client source picks a variant with `seedOf(...) % n` (value-noise uses like phases/offsets are not picks)", () => {
    // 會挑「第幾個變體」的寫法：`list[seedOf(...) % list.length]`、`` `name${seedOf(...) % n}` ``
    const bad = /\[\s*seedOf\([^)]*\)\s*%|\$\{\s*seedOf\([^)]*\)\s*%|seedOf\([^)]*\)\s*%\s*\w+\.length/;
    const hits = readSources()
      .filter(([path, code]) => bad.test(stripTsComments(code, path)))
      .map(([path]) => path);
    expect(hits).toEqual([]);
    expect(seedOf("x")).not.toBe(variantHash("x")); // 兩個雜湊真的不同
  }, 30_000); // 掃描全部原始碼並剖析註解：完整平行跑時會超過預設 5 秒
});
