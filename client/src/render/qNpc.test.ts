// QK-8：人形敵人、NPC 的新部件（qNpc）、qDoll 新形制（赤膊、毛領／白羽披肩、手持物、副手法球）、頸飾接上、盜賊區域外觀。
import { describe, expect, it } from "vitest";
import type { DollLook } from "../api/types";
import { hex, vecCanvas } from "../test/vecRaster";
import { resolveDoll } from "./appearance";
import { drawQ } from "./qDoll";
import { npcNeedsLayers, npcPrep } from "./qNpc";
import { HELD_KINDS, QW_HELD } from "./qNpcHeld";
import { regionDollLook, REGION_DOLLS } from "./qNpcRegion";
import type { M6, QPose, QUnit, QView } from "./qCore";
import { SAMPLE_HOOKS as H } from "./qSample";
import { GAME_HOOKS, qUnitOf } from "./qSpec";
import { QW, qWeapon } from "./qWeapons";
import { resolveDollT, UNIT_DOLLS } from "./testDolls";

const VIEWS: ReadonlyArray<readonly [QView, boolean]> = [
  ["front", false],
  ["side", false],
  ["side", true],
  ["back", false],
];
const MONK: QUnit = { look: { skin: "#c08050", hair: "none", build: "stout" }, gear: { body: { kind: "bare", color: "#d8a030" }, neck: { kind: "beads", color: "#6a3a22" } } };

describe("npcPrep：資料 → Q 版部件", () => {
  it("赤膊：軀幹換膚色、原本的顏色當腰帶；圍裙兩種寫法收成同一個部件", () => {
    const p = npcPrep(MONK, null, false);
    expect(p.unit.gear.body).toEqual({ kind: "bare", color: "#c08050" });
    expect(p.unit.look.belt).toBe("#d8a030");
    const robe = npcPrep({ look: { skin: "#fff" }, gear: { body: { kind: "robe", color: "#4f8a6a", apron: "#e8dcc0" } as never } }, null, false);
    expect(robe.parts).toEqual([{ k: "apron", color: "#e8dcc0" }]);
    expect((robe.unit.gear.body as { apron?: string }).apron).toBeUndefined();
    const waist = npcPrep({ look: { skin: "#fff" }, gear: { waist: { kind: "apron", material: "leather", color: "#2e1e14", trim: "#b07a48" } } }, null, false);
    expect(waist.parts).toEqual([{ k: "apron", color: "#2e1e14", edge: "#b07a48", pocket: false }]);
    expect(waist.unit.gear.waist).toBeUndefined();
  });

  it("背物、黃符、斗笠、頭帶、額上護目鏡、白紗、白羽披肩、帽上護目鏡", () => {
    const u: QUnit = { look: { skin: "#fff" }, gear: { back: { kind: "gourd" }, waist: { kind: "talismans" }, head: { kind: "douli", color: "#3c4248" }, cloak: { kind: "cape", form: "feather", color: "#f2f0ea" } } };
    const p = npcPrep(u, null, false);
    expect(p.parts.map((x) => x.k).sort()).toEqual(["douli", "gourd", "talismans"]);
    expect(p.unit.gear.head).toBeUndefined();
    expect(p.unit.gear.neck).toEqual({ kind: "feathers", color: "#f2f0ea" });
    expect(p.unit.gear.cloak).toBeUndefined();
    const veil = npcPrep({ look: { skin: "#fff" }, gear: { head: { kind: "veil", material: "cloth" } } }, null, false);
    expect(veil.unit.gear.head).toEqual({ kind: "hood", color: "#eef2f2" });
    expect(veil.parts.map((x) => x.k)).toEqual(["gauze"]);
    const cap = npcPrep({ look: { skin: "#fff" }, gear: { head: { kind: "cap", form: "goggles_up" } } }, null, false);
    expect(cap.parts).toEqual([{ k: "goggles_up", cap: true }]);
    expect(cap.unit.gear.head?.kind).toBe("cap");
  });

  it("手持物補上手的顏色；傀儡十字 → 傀儡線，並包一層 probe 記下武器位置（原本的 probe 照呼叫）", () => {
    let inner = 0;
    const pose: QPose = { probe: () => void inner++ };
    const p = npcPrep({ look: { skin: "#abcdef" }, gear: { main_hand: { kind: "puppet_cross" }, off_hand: { kind: "whisk" } } }, pose, false);
    expect(p.unit.gear.main_hand).toMatchObject({ kind: "puppet_strings", skin: "#abcdef" });
    expect(p.unit.gear.off_hand).toMatchObject({ kind: "whisk", skin: "#abcdef" });
    expect(p.parts).toEqual([{ k: "strings", who: "main_hand" }]);
    expect(p.pose).not.toBe(pose);
    const m: M6 = { a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 };
    p.pose!.probe!("puppet_strings", [0, 0], [0, 0], "front", null, m, "puppet_strings");
    expect(p.wms["puppet_strings"]).toEqual([m]);
    expect(inner).toBe(1);
    expect(npcNeedsLayers(p.unit)).toBe(true);
    expect(npcPrep(MONK, pose, false).pose).toBe(pose); // 沒有劍穗、傀儡線不換姿勢
  });

  it("手持物在武器表裡（照持武器規則畫在手上）", () => {
    for (const k of HELD_KINDS) expect(QW[k]).toBe(QW_HELD[k]);
    expect(qWeapon({ kind: "puppet_cross" })?.kind).toBe("puppet_strings");
  });
});

describe("畫得出來（四方向、朝西）", () => {
  const draw = (u: QUnit, v: QView, west: boolean): ReturnType<typeof vecCanvas> => {
    const c = vecCanvas();
    c.ctx.setTransform(west ? -4 : 4, 0, 0, 4, 128, 220);
    drawQ(c.ctx, u, v, H, null, west);
    return c;
  };
  const MONKS = ["sect_acolyte", "sect_swordsman", "sect_talisman_caster", "sect_alchemist", "sect_warrior_monk", "sect_array_disciple", "sect_mist_walker", "sect_crane_archer", "sect_puppeteer", "sect_steward", "sect_mist_lock_master"];
  it("修士 11 種 × 四方向不丟錯", () => {
    for (const t of MONKS) {
      const u = qUnitOf(resolveDollT({ template: t, team: "enemy", summon: false, weaponId: "one_handed_sword" }));
      for (const [v, w] of VIEWS) expect(() => draw(u, v, w), `${t} ${v} ${w}`).not.toThrow();
    }
  });

  it("赤膊：胸口是膚色（不是上衣色）；斗笠在頭頂上方", () => {
    const c = draw(MONK, "front", false);
    expect(hex(c.at(128, 220 - 4 * 13))).toBe("#c08050");
    const hat = draw({ look: { skin: "#f1c9a5", hair: "short" }, gear: { head: { kind: "douli", color: "#c8b07a" } } }, "front", false);
    expect(hex(hat.at(128 + 4 * 3.5, 220 - 4 * 36))).toBe("#c8b07a");
  });

  it("副手法球、拂塵畫成物件，不是書（背面也是）", () => {
    for (const off of [{ kind: "orb", color: "#123456" }, { kind: "whisk" }]) {
      const u: QUnit = { look: { skin: "#f1c9a5" }, gear: { body: { kind: "robe", color: "#2a5a7a" }, off_hand: off } };
      for (const [v, w] of VIEWS) {
        const c = vecCanvas();
        c.ctx.setTransform(w ? -4 : 4, 0, 0, 4, 128, 220);
        let book = false;
        const ctx = new Proxy(c.ctx, {
          get(t, p) {
            const f = (t as unknown as Record<string | symbol, unknown>)[p];
            if (p === "fillStyle") return t.fillStyle;
            return typeof f === "function" ? (f as (...a: unknown[]) => unknown).bind(t) : f;
          },
          set(t, p, val) {
            if (p === "fillStyle" && (val === "#7a2a3a" || val === "#f2ead6")) book = true;
            (t as unknown as Record<string | symbol, unknown>)[p] = val;
            return true;
          },
        });
        drawQ(ctx, u, v, H, null, w);
        expect(book, `${off.kind} ${v}`).toBe(false);
      }
    }
  });
});

describe("頸飾接上紙娃娃（QK-3 待決 6）", () => {
  it("穿吊牌、符牌時 resolveDoll 帶出 neck", () => {
    const spec = resolveDoll({ template: "hero_fighter", team: "ally", summon: false, weaponId: "one_handed_sword", equipment: [{ slot: "neck", appearance: { kind: "charm", form: "bone" } }] });
    expect(spec.gear.neck).toMatchObject({ kind: "charm", form: "bone" });
  });
});

describe("盜賊三套的區域外觀（content/ui/region_dolls.yaml）", () => {
  it("雲嶺換斗笠，武器、詞綴照範本；不在表上照舊", () => {
    const base = UNIT_DOLLS["bandit"] as DollLook;
    const withAffix = { ...base, affixes: ["berserk"], main_material: "iron" } as DollLook;
    const cliff = regionDollLook("cloud_ridge", "bandit", withAffix)!;
    expect(cliff.gear?.["head"]?.kind).toBe("douli");
    expect(cliff.affixes).toEqual(["berserk"]);
    expect((cliff as { main_material?: string }).main_material).toBe("iron");
    expect(regionDollLook("capital", "bandit", base)).toBe(base);
    expect(regionDollLook("cloud_ridge", "sect_swordsman", UNIT_DOLLS["sect_swordsman"] as DollLook)).toBe(UNIT_DOLLS["sect_swordsman"]);
    expect(Object.keys(REGION_DOLLS).sort()).toEqual(["ashen_waste", "cloud_ridge"]);
  });

  it("每一筆都是畫得出來的紙娃娃（四方向）", () => {
    for (const [region, table] of Object.entries(REGION_DOLLS))
      for (const t of Object.keys(table)) {
        const d = regionDollLook(region, t, (UNIT_DOLLS[t] ?? UNIT_DOLLS["bandit_archer"]) as DollLook);
        const u = qUnitOf(resolveDoll({ template: t, dollLook: d, team: "enemy", summon: false, weaponId: "dagger" }));
        for (const [v, w] of VIEWS) {
          const c = vecCanvas();
          c.ctx.setTransform(w ? -4 : 4, 0, 0, 4, 128, 220);
          expect(() => drawQ(c.ctx, u, v, GAME_HOOKS, null, w)).not.toThrow();
        }
      }
  });
});
