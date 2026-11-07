// RT-4（#131）：傭兵頭像——出身區的框色、mercenaries.yaml 的資料都畫得出來。QK-2：Q 版頭像（配件 23 個、跟著體型、好感五級）。
import { describe, expect, it } from "vitest";
import mercsYaml from "../../../content/world/mercenaries.yaml?raw";
import { parse } from "yaml";
import type { NpcPortrait } from "../api/types";
import { regionThemeFor } from "../ui/regionTheme";
import { RANK_LEVEL } from "../world/fieldPeople";
import { portraitRaceLook } from "../world/npcLook";
import { drawPortrait, PORTRAIT_EXTRAS, PORTRAIT_REGION, portraitKey } from "./portrait";
import { drawMoodBadge, MOOD_COLORS, Q_SOOT, qPortraitPrep } from "./qPortrait";

/** 記錄所有呼叫與屬性設定的假 Canvas 2D。 */
function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const fmt = (a: unknown): string => (typeof a === "number" ? a.toFixed(3) : typeof a === "string" ? a : typeof a);
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map(fmt).join(",")})`);
        if (prop === "createRadialGradient" || prop === "createLinearGradient") return { addColorStop: (o: number, c: string) => calls.push(`stop(${fmt(o)},${c})`) };
        if (prop === "measureText") return { width: String(args[0]).length * 6 };
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${String(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

const BASE: NpcPortrait = {
  look: { skin: "#f1c9a5", hair: "short", hair_color: "#c8a868" },
  gear: { body: { kind: "leather", color: "#4a5058" } },
  extras: [],
} as unknown as NpcPortrait;

const draw = (p: NpcPortrait | null, region: string | null = "merc"): string[] => {
  const { ctx, calls } = mockCtx();
  drawPortrait(ctx, 0, 0, 96, p, region);
  return calls;
};

const drawL = (p: NpcPortrait, level: number | null): string[] => {
  const { ctx, calls } = mockCtx();
  drawPortrait(ctx, 0, 0, 96, p, "merc", level);
  return calls;
};

const withExtra = (e: string): NpcPortrait => ({ ...BASE, extras: [e] }) as NpcPortrait;

/** 加上配件後多出來的呼叫（同一張底圖相減）。 */
function added(e: string): string[] {
  const base = new Set(draw(BASE));
  return draw(withExtra(e)).filter((c) => !base.has(c));
}

interface MercRow {
  id: string;
  name_zh: string;
  origin?: string;
  portrait?: NpcPortrait;
}
const MERCS = (parse(mercsYaml) as { mercenaries: MercRow[] }).mercenaries;

describe("6T-1c（美術 PM 6T-1b 檢查）", () => {
  it("通用剪影不寫「?」（看起來像上鎖）；底色照區域", () => {
    const sil = draw(null, "cloud_ridge");
    expect(sil.some((c) => c.startsWith("fillText("))).toBe(false);
    expect(sil).toContain(`stop(0.000,${PORTRAIT_REGION["cloud_ridge"]![2]})`);
  });
});

describe("QK-2：Q 版頭像（qPortrait.js）", () => {
  const f = (n: number): string => n.toFixed(3);
  it("每 42 單位對應邊長、頭心在 0.53（96px：k＝96/42，腳底在 96×0.53＋29k）", () => {
    const k = 96 / 42;
    const all = draw(BASE);
    expect(all).toContain(`translate(${f(48)},${f(96 * 0.53 + 29 * k)})`);
    expect(all).toContain(`scale(${f(k)},${f(k)})`);
  });

  it("soot（6T-1d）：裁在臉的皮膚區域（沒有 DOM 時用臉圓），位置在右頰", () => {
    const all = draw(withExtra("soot"));
    const face = all.indexOf(`arc(${f(0)},${f(-29)},${f(8.4)},${f(0)},${f(Math.PI * 2)})`);
    expect(face).toBeGreaterThan(-1);
    expect(all[face + 1]).toBe("clip()");
    const soot = all.findIndex((c, i) => i > face && c.startsWith(`ellipse(${f(Q_SOOT.x)},${f(Q_SOOT.y)},`));
    expect(soot).toBeGreaterThan(face);
    expect(Q_SOOT.x - Q_SOOT.rx).toBeGreaterThan(1.6); // 不碰嘴（嘴寬 ±1.6）
    expect(Q_SOOT.y - Q_SOOT.ry).toBeGreaterThan(-28); // 在眼睛下方（方眼下緣約 −27.2）
  });

  it("配件跟著體型（6T-1d）：stout、tall 先套 build 再畫配件", () => {
    for (const [build, sx, sy] of [["stout", 1.12, 0.88], ["tall", 0.96, 1.1]] as const) {
      const p = { ...BASE, look: { ...BASE.look, build }, extras: ["scar"] } as unknown as NpcPortrait;
      const all = draw(p);
      const sc = all.lastIndexOf(`scale(${f(sx)},${f(sy)})`);
      const scar = all.findIndex((c) => c === "strokeStyle=#8a3a2a");
      expect(sc, build).toBeGreaterThan(-1);
      expect(scar, build).toBeGreaterThan(sc);
    }
  });

  it("23 個配件都畫得出來（白狐另畫狐臉），不認得的略過", () => {
    expect(PORTRAIT_EXTRAS).toHaveLength(23);
    for (const e of PORTRAIT_EXTRAS) {
      if (e === "fox") continue;
      expect(added(e).length, e).toBeGreaterThan(0);
      expect(draw(withExtra(e)), e).toEqual(draw(withExtra(e)));
    }
    expect(added("no_such_extra")).toEqual([]);
    const fox = draw(withExtra("fox"));
    expect(fox).toContain("fillStyle=#3aa8e0");
  });

  it("好感五級：0、1、3、4 各不相同，2 與不給一樣", () => {
    const lv = (l: number | null): string => drawL(BASE, l).join("|");
    expect(lv(2)).toBe(lv(null));
    expect(new Set([0, 1, 2, 3, 4].map(lv)).size).toBe(5);
  });

  it("被護目鏡遮住的眼睛不換、面紗遮住的嘴不換", () => {
    const gog = withExtra("goggles");
    const eyes = drawL(gog, 3).filter((c) => c.startsWith(`rect(${f(-2.9 - 1.2)},${f(-30.4)}`));
    expect(eyes).toEqual([]);
    const veil = { ...BASE, gear: { ...BASE.gear, head: { kind: "veil", color: "#dfe4e2" } } } as unknown as NpcPortrait;
    expect(drawL(veil, 3)).not.toContain("fillStyle=#8a3a3a");
    expect(drawL(BASE, 3)).toContain("fillStyle=#8a3a3a");
  });

  it("好感級別對到五級（敵視 0～信賴 4），中立＝普通不換表情", () => {
    expect(RANK_LEVEL).toEqual({ hostile: 0, cold: 1, neutral: 2, friendly: 3, trusted: 4 });
    expect(drawL(BASE, RANK_LEVEL.neutral)).toEqual(drawL(BASE, null));
  });

  it("頭頂徽章：五級五色", () => {
    for (let l = 0; l < 5; l++) {
      const { ctx, calls } = mockCtx();
      drawMoodBadge(ctx, 10, 10, 8, l);
      expect(calls).toContain(`fillStyle=${MOOD_COLORS[l]}`);
    }
  });

  it("配件換成頭部裝備（qNpc.prep）：沒戴帽才換，八字鬍在沒鬍子時才換", () => {
    const u = { look: { skin: "#f1c9a5" }, gear: {} };
    expect(qPortraitPrep(u, ["cap"]).unit.gear.head?.kind).toBe("cap");
    expect(qPortraitPrep(u, ["goggles"]).unit.gear.head?.kind).toBe("goggles");
    expect(qPortraitPrep(u, ["wide_hat"]).parts.map((p) => p.k)).toEqual(["douli"]);
    const hatted = { look: { skin: "#f1c9a5" }, gear: { head: { kind: "hood" } } };
    expect(qPortraitPrep(hatted, ["cap", "wide_hat", "headband"]).unit.gear.head?.kind).toBe("hood");
    expect(qPortraitPrep(hatted, ["wide_hat", "headband"]).parts).toEqual([]);
    expect(qPortraitPrep(u, ["mustache"]).unit.look.beardStyle).toBe("mustache");
    expect(qPortraitPrep({ look: { skin: "#fff", beard: true }, gear: {} }, ["mustache"]).unit.look.beardStyle).toBeUndefined();
  });
});

describe("出身區的框色（RT-4：框色＝RT-1 的 portrait_ring）", () => {
  it("五區都有框色，傭兵金留作沒有出身時的預設", () => {
    expect(PORTRAIT_REGION["crystal_crown"]?.[0]).toBe("#8ab0ff");
    expect(PORTRAIT_REGION["arcane_hub"]?.[0]).toBe("#4ad0c8");
    expect(PORTRAIT_REGION["frost_tide"]?.[0]).toBe("#6ac0e8");
    expect(PORTRAIT_REGION["cloud_ridge"]?.[0]).toBe("#6aa84a");
    expect(PORTRAIT_REGION["ashen_waste"]?.[0]).toBe("#ff6a1a");
    expect(PORTRAIT_REGION["merc"]?.[0]).toBe("#c8a868");
  });

  it("QK-2b：主城框色＝RT-1 設定檔（region_themes.yaml）capital 的 portrait_ring 晶紫 #a898ff，不再是傭兵金", () => {
    expect(PORTRAIT_REGION["capital"]?.[0]).toBe("#a898ff");
    expect(PORTRAIT_REGION["capital"]?.[0]).toBe(regionThemeFor("capital").portrait_ring);
    const capital = draw(BASE, "capital");
    expect(capital).toContain("strokeStyle=#a898ff");
    expect(capital).not.toContain("strokeStyle=#c8a868");
  });

  it("框線用該區的顏色；不認得的區域退回傭兵金", () => {
    for (const r of ["crystal_crown", "arcane_hub", "frost_tide"]) {
      expect(draw(BASE, r)).toContain(`strokeStyle=${PORTRAIT_REGION[r]![0]}`);
    }
    const odd = draw(BASE, "nowhere");
    expect(odd).toContain("strokeStyle=#c8a868");
    expect(draw(BASE, null)).toEqual(draw(BASE, "merc"));
  });

  it("區域不同快取鍵就不同", () => {
    expect(portraitKey(BASE, "crystal_crown", 48)).not.toBe(portraitKey(BASE, "frost_tide", 48));
  });
});

describe("mercenaries.yaml 的 9 名傭兵（#131）", () => {
  it("每名都有出身與頭像，配件都畫得出來", () => {
    expect(MERCS).toHaveLength(9);
    const known: readonly string[] = PORTRAIT_EXTRAS;
    for (const m of MERCS) {
      expect(m.origin, m.id).toBeDefined();
      expect(PORTRAIT_REGION[m.origin!], m.id).toBeDefined();
      expect(m.portrait, m.id).toBeDefined();
      for (const e of m.portrait!.extras ?? []) expect(known, `${m.id} ${e}`).toContain(e);
      expect(draw(m.portrait!, m.origin!)).toContain(`strokeStyle=${PORTRAIT_REGION[m.origin!]![0]}`);
    }
    expect(new Set(MERCS.map((m) => m.origin)).size).toBe(5); // 五區都有人
  });

  it("名字對應（id 不變）", () => {
    const names = Object.fromEntries(MERCS.map((m) => [m.id, m.name_zh]));
    expect(names).toEqual({
      merc_qingfeng: "青鋒",
      merc_chuanyun: "珊瑚",
      merc_chiyan: "灰燼瑪菈",
      merc_tiebi: "賽倫",
      merc_panshi: "鉚釘",
      merc_huichun: "回春",
      merc_qingyin: "莉瑟",
      merc_jinglei: "七號線圈",
      merc_fuying: "鏽牙",
    });
  });

  it("鏽牙的獠牙帶進紙娃娃的種族部件", () => {
    const rust = MERCS.find((m) => m.id === "merc_fuying")!;
    expect(portraitRaceLook(rust.portrait!)).toMatchObject({ tusks: true });
  });
});

describe("QK-2b：毛領走紙娃娃的頸飾（QK-8 待決 1）", () => {
  it("fur_collar → gear.neck（fur_collar），不再是頭像外框層的部件；已有頸飾就不換", () => {
    const unit = { look: { skin: "#f1c9a5" }, gear: {} };
    const { unit: out, parts } = qPortraitPrep(unit, ["fur_collar"]);
    expect(out.gear.neck).toEqual({ kind: "fur_collar", material: "fur" });
    expect(parts.map((p) => p.k)).not.toContain("fur_collar");
    expect(unit.gear).toEqual({});
    const worn = qPortraitPrep({ look: { skin: "#f1c9a5" }, gear: { neck: { kind: "beads" } } }, ["fur_collar"]);
    expect(worn.unit.gear.neck).toEqual({ kind: "beads" });
  });

  it("頭像有毛領時畫得出來，且和沒有毛領的不同", () => {
    const withFur = { ...BASE, extras: ["fur_collar"] } as NpcPortrait;
    expect(draw(withFur).join("|")).not.toBe(draw(BASE).join("|"));
  });
});
