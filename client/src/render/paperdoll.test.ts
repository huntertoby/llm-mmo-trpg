import { describe, expect, it, vi } from "vitest";
import type { Facing } from "../api/types";
import { ringArrow } from "../battle/facing";
import { dollKey, elementTint, KNOWN_KINDS, weaponLook, type DollSpec } from "./appearance";
import { resolveDollT, UNIT_DOLLS } from "./testDolls";
import { weaponLookEntry } from "../battle/glossary";
import { drawFigure, drawFigurePose, itemColors } from "./paperdoll";

function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(2) : typeof a)).join(",")})`);
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

const FACINGS: Facing[] = ["south", "north", "east", "west"];
const base = { team: "ally", summon: false } as const;

describe("resolveDoll（外觀表與退回）", () => {
  it("主手依 weapon_id；每個武器 id 都有對照，元素取自武器", () => {
    const ids = ["one_handed_sword", "greatsword", "dagger", "bow", "fire_staff", "axe", "scepter", "crossbow", "longgun"];
    for (const id of ids) expect(resolveDollT({ ...base, template: "x", weaponId: id }).gear.main_hand?.kind).toBe(weaponLookEntry(id)!.look.kind);
    expect(resolveDollT({ ...base, template: "x", weaponId: "fire_staff" }).gear.main_hand).toMatchObject({ kind: "staff", element: "fire" });
    expect(resolveDollT({ ...base, template: "x", weaponId: "frost_staff" }).gear.main_hand?.element).toBe("ice");
  });

  it("3-24a1 新武器：斧、錘、矛有自己的造型，權杖與圖騰杖是杖的形制（權杖單手、圖騰杖雙手）", () => {
    const look = (id: string) => resolveDollT({ ...base, template: "hero_fighter", weaponId: id }).gear;
    expect(look("axe").main_hand?.kind).toBe("axe");
    expect(look("hammer").main_hand?.kind).toBe("hammer");
    expect(look("spear").main_hand?.kind).toBe("spear");
    expect(look("scepter").main_hand).toMatchObject({ kind: "staff", form: "scepter" });
    expect(look("totem_staff").main_hand).toMatchObject({ kind: "staff", form: "totem" });
    expect(look("hammer").off_hand).toBeUndefined();
    expect(look("spear").off_hand).toBeUndefined();
    expect(look("totem_staff").off_hand).toBeUndefined();
    expect(look("axe").off_hand?.kind).toBe("shield_round");
    expect(look("scepter").off_hand?.kind).toBe("shield_round");
    // 形制進快取鍵：權杖、圖騰杖與一般杖不共用貼圖
    const keys = ["fire_staff", "scepter", "totem_staff"].map((id) => dollKey(resolveDollT({ ...base, template: "x", weaponId: id }), "south", false));
    expect(new Set(keys).size).toBe(3);
  });

  it("未知武器依 weapon_class，都沒有畫劍", () => {
    expect(weaponLook("mystery", "ranged").kind).toBe("bow");
    expect(weaponLook("mystery", "focus").kind).toBe("staff");
    expect(weaponLook("mystery", "melee").kind).toBe("sword");
    expect(weaponLook("mystery", "weird").kind).toBe("sword");
    expect(weaponLook("mystery").kind).toBe("sword");
    expect(weaponLook(null).kind).toBe("sword");
    expect(weaponLook("").kind).toBe("sword");
  });

  it("雙手武器副手留空，單手武器保留副手", () => {
    expect(resolveDollT({ ...base, template: "hero_fighter", weaponId: "greatsword" }).gear.off_hand).toBeUndefined();
    expect(resolveDollT({ ...base, template: "hero_fighter", weaponId: "one_handed_sword" }).gear.off_hand?.kind).toBe("shield_round");
    expect(resolveDollT({ ...base, template: "hero_mage", weaponId: "fire_staff" }).gear.off_hand).toBeUndefined();
  });

  it("未知範本依陣營預設：我方布衣＋靴，敵方皮甲＋頭巾＋靴；主手仍依武器", () => {
    const a = resolveDollT({ ...base, template: "new_thing", weaponId: "bow" });
    expect(a.gear).toMatchObject({ body: { kind: "shirt" }, feet: { kind: "boots" }, main_hand: { kind: "bow" } });
    expect(a.gear.head).toBeUndefined();
    const e = resolveDollT({ team: "enemy", summon: false, template: "new_thing", weaponId: "dagger" });
    expect(e.gear).toMatchObject({ body: { kind: "leather" }, head: { kind: "bandana" }, feet: { kind: "boots" }, main_hand: { kind: "dagger" } });
  });

  it("不在表內的召喚物用骷髏；圖騰畫圖騰柱", () => {
    const s = resolveDollT({ team: "ally", summon: true, template: "summon_new", weaponId: "dagger" });
    expect(s.gear.body?.kind).toBe("ribs");
    expect(s.look.skull).toBe(true);
    expect(resolveDollT({ team: "ally", summon: true, template: "summon_war_totem", totem: true }).totem).toBe(true);
  });

  it("不認得的 kind 只跳過該欄位；不認得的材質用布料色、元素不套色", () => {
    const bandit = UNIT_DOLLS["bandit"]!;
    const odd = { ...bandit, gear: { ...bandit.gear, head: { kind: "space_helmet", material: "unobtainium" } } };
    const d = resolveDollT({ team: "enemy", summon: false, template: "bandit", dollLook: odd, weaponId: "dagger" });
    expect(d.gear.head).toBeUndefined();
    expect(d.gear.body?.kind).toBe("leather");
    expect(d.gear.main_hand?.kind).toBe("dagger");
    expect(itemColors({ kind: "sword", material: "unobtainium" })).toEqual(itemColors({ kind: "sword", material: "cloth" }));
    expect(itemColors({ kind: "sword", material: "iron", element: "nope" })).toEqual(itemColors({ kind: "sword", material: "iron" }));
    expect(itemColors({ kind: "sword", material: "iron", element: "fire" })).not.toEqual(itemColors({ kind: "sword", material: "iron" }));
    expect(elementTint("physical")).toBeUndefined();
    expect(elementTint("fire")).toBe("#ff6a1a");
  });

  it("頭目範本帶史詩外光", () => {
    expect(resolveDollT({ team: "enemy", summon: false, template: "bandit_boss", weaponId: "greatsword" }).rarity).toBe("epic");
  });

  it("快取鍵：同組合相同、裝備／朝向／姿勢不同則不同", () => {
    const a = resolveDollT({ ...base, template: "hero_fighter", weaponId: "one_handed_sword" });
    const b = resolveDollT({ ...base, template: "hero_fighter", weaponId: "one_handed_sword" });
    expect(dollKey(a, "south", false)).toBe(dollKey(b, "south", false));
    expect(dollKey(a, "south", false)).not.toBe(dollKey(a, "north", false));
    expect(dollKey(a, "south", false)).not.toBe(dollKey(a, "south", true));
    const c = resolveDollT({ ...base, template: "hero_fighter", weaponId: "dagger" });
    expect(dollKey(a, "south", false)).not.toBe(dollKey(c, "south", false));
  });

  it("每個範本的每種欄位 kind 都認得", () => {
    for (const t of Object.keys(UNIT_DOLLS)) {
      const d = resolveDollT({ team: "enemy", summon: false, template: t, weaponId: "one_handed_sword" });
      for (const [slot, item] of Object.entries(d.gear)) expect(KNOWN_KINDS[slot as keyof typeof KNOWN_KINDS]).toContain(item.kind);
    }
  });
});

describe("drawFigure（假 Canvas）", () => {
  it("每個範本 × 4 朝向 × 站／倒都畫得出來、不丟例外", () => {
    const spy = vi.spyOn(Math, "random");
    for (const t of [...Object.keys(UNIT_DOLLS), "brand_new"]) {
      for (const f of FACINGS) {
        for (const downed of [false, true]) {
          const { ctx, calls } = mockCtx();
          const spec = resolveDollT({ team: "enemy", summon: false, template: t, weaponId: "bow" });
          expect(() => drawFigurePose(ctx, spec, f, downed)).not.toThrow();
          expect(calls.length).toBeGreaterThan(20);
        }
      }
    }
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it("所有欄位 kind（含武器）都畫得出來；未知 kind 不丟例外", () => {
    for (const slot of Object.keys(KNOWN_KINDS) as Array<keyof typeof KNOWN_KINDS>) {
      for (const kind of [...KNOWN_KINDS[slot], "weird_kind"]) {
        const spec: DollSpec = { look: { skin: "#fff", hair: "long" }, gear: { [slot]: { kind, material: "steel", element: "fire" } } };
        for (const f of FACINGS) {
          const { ctx } = mockCtx();
          expect(() => drawFigure(ctx, spec, f)).not.toThrow();
        }
      }
    }
  });

  it("圖騰、骷髏也畫得出來；朝向確定性（兩次呼叫序列相同）", () => {
    const run = (f: Facing): string[] => {
      const { ctx, calls } = mockCtx();
      drawFigure(ctx, resolveDollT({ team: "ally", summon: true, template: "summon_skeleton_warrior", weaponId: "one_handed_sword" }), f);
      return calls;
    };
    expect(run("east")).toEqual(run("east"));
    expect(run("east")).not.toEqual(run("west"));
    const { ctx, calls } = mockCtx();
    drawFigure(ctx, resolveDollT({ team: "ally", summon: true, template: "summon_war_totem", totem: true }), "south");
    expect(calls.length).toBeGreaterThan(5);
  });
});

describe("ringArrow（底圈朝向尖角）", () => {
  it("尖端在朝向那一側的最外面", () => {
    const [nx, ny] = ringArrow("north", 0, 10, 17, 8, 5);
    expect([nx, ny]).toEqual([0, 10 - 13]);
    const [sx, sy] = ringArrow("south", 0, 10, 17, 8, 5);
    expect([sx, sy]).toEqual([0, 10 + 13]);
    const [ex] = ringArrow("east", 0, 10, 17, 8, 5);
    expect(ex).toBe(22);
    const [wx] = ringArrow("west", 0, 10, 17, 8, 5);
    expect(wx).toBe(-22);
  });
});
