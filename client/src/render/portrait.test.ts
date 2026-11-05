// RT-4（#131）：傭兵頭像——出身區的框色、四種新配件（crest、circlet、cyber_eye、coral）、mercenaries.yaml 的資料都畫得出來。
import { describe, expect, it } from "vitest";
import mercsYaml from "../../../content/world/mercenaries.yaml?raw";
import { parse } from "yaml";
import type { NpcPortrait } from "../api/types";
import { portraitRaceLook } from "../world/npcLook";
import { drawPortrait, PORTRAIT_EXTRAS, PORTRAIT_REGION, portraitKey } from "./portrait";

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

  it("soot 加深加大（48～56px 原尺寸看得出來）", () => {
    const soot = added("soot");
    expect(soot).toContain("fillStyle=rgba(34,24,18,0.62)");
    expect(soot.some((c) => c.startsWith("ellipse(4.400,-38.400,3.600,1.900"))).toBe(true);
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

describe("四種新配件（照 merc-portraits.html 的畫法）", () => {
  it("crest：頭盔頂的藍紫冠飾", () => {
    expect(added("crest").join(" ")).toContain("#5a7ad0");
  });

  it("circlet：金色額環加一顆發光紫晶", () => {
    const out = added("circlet").join(" ");
    expect(out).toContain("#e8bb48");
    expect(out).toContain("shadowColor=#a898ff");
    expect(out).toContain("#a898ff");
  });

  it("cyber_eye：右眼青光（有發光）加耳側線路", () => {
    const out = added("cyber_eye");
    expect(out).toContain("shadowColor=#4ad0c8");
    expect(out).toContain("fillStyle=#7af0e8");
    expect(out.some((c) => c.startsWith("arc(3.400,-41.200,1.400"))).toBe(true);
  });

  it("coral：髮上三顆珊瑚珠", () => {
    const out = added("coral");
    expect(out.filter((c) => c.startsWith("arc(")).length).toBe(3);
    expect(out).toContain("fillStyle=#f2a090");
  });

  it("配件名單含四種新配件，畫法確定（同一位畫兩次一樣）", () => {
    for (const e of ["crest", "circlet", "cyber_eye", "coral"]) {
      expect(PORTRAIT_EXTRAS).toContain(e);
      expect(added(e).length).toBeGreaterThan(0);
      expect(draw(withExtra(e))).toEqual(draw(withExtra(e)));
    }
    expect(added("no_such_extra")).toEqual([]); // 不認得的略過
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
