// Phase 5A-ART3：修士用的紙娃娃新部件（docs/art/敵人外觀.md 第 3 節第 3 段、docs/art/sample/storyDoll.js）。
import { describe, expect, it } from "vitest";
import type { Facing } from "../api/types";
import type { DollSpec } from "./appearance";
import { drawFigure } from "./paperdoll";
import { resolveDollT, UNIT_DOLLS } from "./testDolls";

function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(2) : typeof a === "string" ? a : typeof a)).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") return { addColorStop: () => undefined };
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

const FACINGS: readonly Facing[] = ["south", "east", "north", "west"];

function drawn(spec: DollSpec, facing: Facing): string {
  const { ctx, calls } = mockCtx();
  drawFigure(ctx, spec, facing);
  return calls.join(";");
}

const base: DollSpec = { look: { skin: "#f1c9a5", hair: "short" }, gear: { body: { kind: "robe", material: "cloth", color: "#5f8f8a" } } };
const withPart = (patch: Partial<DollSpec["gear"]>, look: Partial<DollSpec["look"]> = {}): DollSpec => ({ look: { ...base.look, ...look }, gear: { ...base.gear, ...patch } });

describe("11 個新部件都畫得出來（四方向不丟錯），而且看得出差別", () => {
  const cases: Array<[string, DollSpec, string]> = [
    ["髮髻", withPart({}, { hair: "bun", bunBand: "#123456" }), "strokeStyle=#123456"],
    ["赤膊", withPart({ body: { kind: "bare", material: "cloth", color: "#d8a030" } }, { skin: "#c08050" }), "strokeStyle=#d8a030"],
    ["念珠", withPart({ neck: { kind: "beads", material: "wood", color: "#aa3311" } }), "fillStyle=#aa3311"],
    ["圍裙", withPart({ body: { kind: "robe", material: "cloth", color: "#4f8a6a", apron: "#e8dcc0" } }), "fillStyle=#e8dcc0"],
    ["藥葫蘆", withPart({ back: { kind: "gourd", material: "wood", color: "#e8bb48" } }), "fillStyle=#e8bb48"],
    ["木偶箱", withPart({ back: { kind: "puppet_box", material: "wood", color: "#7a5030" } }), "fillStyle=#7a5030"],
    ["腰掛黃符", withPart({ waist: { kind: "talismans", material: "paper", color: "#fff7c0" } }), "fillStyle=#fff7c0"],
    ["白紗面罩", withPart({ head: { kind: "veil", material: "cloth" } }), "fillStyle=#d8dcdc"],
    ["白羽披肩", withPart({ cloak: { kind: "cape", material: "cloth", form: "feather", color: "#f2f0ea" } }), "strokeStyle=#b8b4aa"],
    ["劍穗", withPart({ main_hand: { kind: "sword", material: "steel", tassel: "#c0392b" } }), "strokeStyle=#c0392b"],
    ["拂塵", withPart({ main_hand: { kind: "whisk", material: "wood" } }), "fillStyle=#f4f0e6"],
    ["符紙", withPart({ main_hand: { kind: "talisman", material: "paper" } }), "fillStyle=#e8c84a"],
    ["傀儡線", withPart({ main_hand: { kind: "puppet_cross", material: "wood" } }), "strokeStyle=#e8e0d0"],
  ];
  for (const [zh, spec, mark] of cases) {
    it(zh, () => {
      for (const f of FACINGS) expect(() => drawn(spec, f)).not.toThrow();
      expect(drawn(spec, "south")).toContain(mark);
      expect(drawn(base, "south")).not.toContain(mark);
    });
  }

  it("不認得的 kind／form 不畫、不出錯", () => {
    const odd = withPart({ back: { kind: "zzz", material: "wood" }, waist: { kind: "zzz", material: "wood" }, neck: { kind: "zzz", material: "wood" }, cloak: { kind: "cape", material: "cloth", form: "zzz" } });
    for (const f of FACINGS) expect(() => drawn(odd, f)).not.toThrow();
  });
});

describe("內容資料 → 紙娃娃（resolveDoll）", () => {
  it("煉丹師：竹青袍＋圍裙、背葫蘆、主手拂塵（main_kind 覆寫武器外觀）", () => {
    const spec = resolveDollT({ template: "sect_alchemist", team: "enemy", summon: false, weaponId: "totem_staff", weaponClass: "focus" });
    expect(spec.look.hair).toBe("bun");
    expect(spec.gear.body).toMatchObject({ kind: "robe", color: "#4f8a6a", apron: "#e8dcc0" });
    expect(spec.gear.back?.kind).toBe("gourd");
    expect(spec.gear.main_hand?.kind).toBe("whisk");
  });

  it("護法武僧：赤膊＋念珠、矮壯；劍陣弟子：劍穗；霧鎖真人：拂塵＋副手長劍、傳說外光", () => {
    const monk = resolveDollT({ template: "sect_warrior_monk", team: "enemy", summon: false, weaponId: "fist", weaponClass: "melee" });
    expect(monk.gear.body?.kind).toBe("bare");
    expect(monk.gear.neck?.kind).toBe("beads");
    expect(monk.look.build).toBe("stout");
    const array = resolveDollT({ template: "sect_array_disciple", team: "enemy", summon: false, weaponId: "one_handed_sword", weaponClass: "melee" });
    expect(array.gear.main_hand).toMatchObject({ kind: "sword", tassel: "#c0392b" });
    const master = resolveDollT({ template: "sect_mist_lock_master", team: "enemy", summon: false, weaponId: "one_handed_sword", weaponClass: "melee" });
    expect(master.gear.main_hand?.kind).toBe("whisk");
    expect(master.gear.off_hand?.kind).toBe("sword");
    expect(master.rarity).toBe("legendary");
    expect(master.look.beard).toBe(true);
  });

  it("夾具裡的修士都帶新部件；異形範本帶 creature", () => {
    expect(UNIT_DOLLS["sect_mist_walker"]?.gear?.head?.kind).toBe("veil");
    expect(UNIT_DOLLS["sect_crane_archer"]?.gear?.cloak?.form).toBe("feather");
    expect(UNIT_DOLLS["sect_puppeteer"]?.main_kind).toBe("puppet_cross");
    expect(UNIT_DOLLS["ashen_heart"]?.creature?.status_traits).toEqual({ molten_shell: ["crust"] });
  });
});
