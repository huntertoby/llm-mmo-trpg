// Phase QI-1a：Q 版小圖示（武器、副手）的行為一致測試——用實際內容資料（glossary.json、gearAppearance.json），不手寫清單。
// 規格 docs/phases/PhaseQI-1計畫.md 第 7 節 T1～T5、T7、T9。
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import glossary from "../../battle/fixtures/glossary.json";
import appearance from "../gearAppearance.json";
import { WEAPON_CLASS_KIND } from "../appearance";
import { dollGear, dollItem, pairedPart } from "../dollGear";
import { drawGear, gearIconKey, resolveGear } from "../gearIcon";
import { weaponIconDef, weaponIconItem, weaponIconKey } from "../weaponIcon";
import { blitOrigin, GEAR_PAD, ICON_RES, outlinePx, render, setQCanvasFactory } from "./core";
import { clearQWeaponDefs, hasQWeaponArt, Q_WEAPON_KINDS, qResolve, qWeaponDef } from "./weapons";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../../test/fakeCanvas";

interface KindJson { id: string; slotType: string; zh: string; paired: boolean; forms: Array<{ id: string; zh: string; materials?: string[] }>; materials: string[] }
const KINDS = appearance.kinds as unknown as KindJson[];
const WEAPON_KINDS = KINDS.filter((k) => k.slotType === "weapon" || k.slotType === "offhand");
const LOOKS = new Map(glossary.weapon_looks.map((w) => [w.id, w]));

describe("T1 每一把武器的圖示畫自己的那一款", () => {
  it("glossary 的每一把武器（含沒有 look 的）：resolveGear 結果等於外觀表；成對保留 dual_*；Q 版 def 取到該款自己的圖樣", () => {
    let withLook = 0;
    let without = 0;
    for (const w of glossary.weapon_ranges) {
      const item = weaponIconItem(w.id, w.weapon_class);
      const r = resolveGear(item);
      const entry = LOOKS.get(w.id);
      if (entry !== undefined) {
        withLook += 1;
        expect(item.kind, w.id).toBe(entry.look.kind); // 成對武器保留 dual_*（不再 pairedPart）
        expect(r.kind, w.id).toBe(entry.look.kind);
        expect(r.material, w.id).toBe(entry.look.material);
        expect(r.form, w.id).toBe(entry.look.form ?? resolveGear({ kind: entry.look.kind }).form);
      } else {
        without += 1;
        expect(r.kind, w.id).toBe(WEAPON_CLASS_KIND[w.weapon_class] ?? "sword");
      }
      const def = weaponIconDef(item);
      expect(def, w.id).not.toBeNull();
      expect(def?.meta.r.kind, w.id).toBe(r.kind);
      expect(def?.meta.r.form, w.id).toBe(r.form);
      const zh = KINDS.find((k) => k.id === r.kind)?.forms.find((f) => f.id === r.form)?.zh;
      expect(def?.zh, w.id).toBe(zh);
    }
    // 需求 2.3：有 look 的 23 把、沒有 look 的 10 把（從 glossary 算出，數字對照需求）
    expect(withLook).toBe(23);
    expect(without).toBe(10);
  });
});

describe("T2 gearAppearance.json 的武器、副手每一款都有 Q 版圖樣", () => {
  it("kind × form 都有圖樣、款名與 JSON 一致；總數 61（需求 1.1：武器 17 種 53 款＋副手 4 種 8 款）", () => {
    let count = 0;
    for (const k of WEAPON_KINDS) {
      expect(hasQWeaponArt(k.id), k.id).toBe(true);
      for (const f of k.forms) {
        count += 1;
        expect(Q_WEAPON_KINDS[k.id]?.forms[f.id], `${k.id}/${f.id}`).toBe(f.zh);
        const def = qWeaponDef(qResolve(resolveGear({ kind: k.id, form: f.id })));
        expect(def?.meta.r).toMatchObject({ kind: k.id, form: f.id });
        expect(def?.zh).toBe(f.zh);
      }
    }
    expect(WEAPON_KINDS.filter((k) => k.slotType === "weapon").length).toBe(17);
    expect(WEAPON_KINDS.filter((k) => k.slotType === "offhand").length).toBe(4);
    expect(count).toBe(61);
    // Q 版的清單沒有多出 JSON 以外的種類
    expect(Object.keys(Q_WEAPON_KINDS).sort()).toEqual(WEAPON_KINDS.map((k) => k.id).sort());
  });
});

describe("T3 錘一律方頭（D1）", () => {
  it("glossary 的錘外觀是戰錘；沒寫或不認得 form 的錘退戰錘；其他種類照舊退 JSON 第一款；人物也是戰錘", () => {
    expect(LOOKS.get("hammer")?.look.form).toBe("warhammer");
    expect(resolveGear({ kind: "hammer" }).form).toBe("warhammer");
    expect(resolveGear({ kind: "hammer", form: "???" }).form).toBe("warhammer");
    expect(resolveGear({ kind: "hammer", form: "mace" }).form).toBe("mace");
    for (const k of KINDS) {
      if (k.id === "hammer") continue;
      expect(resolveGear({ kind: k.id }).form, k.id).toBe(k.forms[0]?.id);
      expect(resolveGear({ kind: k.id, form: "???" }).form, k.id).toBe(k.forms[0]?.id);
    }
    expect(dollItem({ kind: "hammer" }, "main_hand")?.item).toMatchObject({ kind: "hammer", form: "warhammer" });
  });
});

describe("T4 成對武器", () => {
  it("圖示收到成對種類（畫兩把），人物仍主手、副手各畫一把單把", () => {
    const paired = KINDS.filter((k) => k.paired);
    expect(paired.map((k) => k.id).sort()).toEqual(["dual_dagger", "dual_pistol"]);
    for (const k of paired) {
      expect(weaponIconDef({ kind: k.id })?.meta.r.kind).toBe(k.id);
      expect(weaponIconDef({ kind: k.id })?.meta.diag).toBe(false); // 兩把交叉／並排是塊狀構圖
      const single = pairedPart(k.id);
      expect(single).not.toBeNull();
      const g = dollGear([{ slot: "main_hand", appearance: { kind: k.id } }]);
      expect(g.paired).toBe(true);
      expect(g.gear.main_hand?.kind).toBe(single);
      expect(g.gear.off_hand?.kind).toBe(single);
    }
    for (const id of ["dual_dagger", "dual_pistol"]) expect(weaponIconItem(id, "melee").kind).toBe(id);
  });
});

describe("T5 快取鍵", () => {
  it("圓章與裝備格的鍵都含 res：同一件 res 1 與 2 不同鍵", () => {
    const item = { kind: "sword", form: "broad", material: "steel" };
    expect(weaponIconKey(item, 20, 1)).not.toBe(weaponIconKey(item, 20, 2));
    expect(weaponIconKey(item, 20)).toBe(weaponIconKey(item, 20, ICON_RES));
    expect(gearIconKey(item, 32, undefined, 1)).not.toBe(gearIconKey(item, 32, undefined, 2));
    expect(gearIconKey(item, 32)).toBe(gearIconKey(item, 32, undefined, ICON_RES));
  });
  it("與輸入屬性順序無關；不認得的值與預設同鍵；不含 color（D2）", () => {
    const a = weaponIconKey({ kind: "staff", form: "wand", material: "bone", element: "ice" }, 24);
    const b = weaponIconKey({ element: "ice", material: "bone", form: "wand", kind: "staff" }, 24);
    expect(a).toBe(b);
    expect(weaponIconKey({ kind: "hammer" }, 24)).toBe(weaponIconKey({ kind: "hammer", form: "warhammer", material: "iron" }, 24));
    expect(weaponIconKey({ kind: "sword", color: "#ff0000" }, 24)).toBe(weaponIconKey({ kind: "sword" }, 24));
    expect(weaponIconKey({ kind: "sword" }, 24)).not.toContain("#");
    expect(gearIconKey({ kind: "axe", rarity: "epic", keywords: ["wet"] }, 64)).toBe(gearIconKey({ keywords: ["wet"], rarity: "epic", kind: "axe" }, 64));
  });
  it("鍵含 kind、form、material、keywords、element、rarity、px、frame", () => {
    const base = { kind: "staff", form: "long", material: "wood" };
    const k = weaponIconKey(base, 24);
    expect(weaponIconKey({ ...base, form: "wand" }, 24)).not.toBe(k);
    expect(weaponIconKey({ ...base, material: "bone" }, 24)).not.toBe(k);
    expect(weaponIconKey({ ...base, element: "fire" }, 24)).not.toBe(k);
    expect(weaponIconKey({ ...base, element: "holy" }, 24)).not.toBe(k);
    expect(weaponIconKey(base, 28)).not.toBe(k);
    expect(k.split("|")).toContain("badge");
  });
});

describe("T7 貼圖對齊整數裝置像素", () => {
  const isInt = (v: number): boolean => Math.abs(v - Math.round(v)) < 1e-9;
  /** 需求 3.1 第 1、2 點列的例子：圓章 20px、meta.badge 0.966；裝備格 32／42／48／64 留白 6%。 */
  const cases: Array<{ name: string; px: number; a: number; p: number }> = [
    { name: "圓章 20 × 0.966", px: 20, a: 20 * 0.966, p: (20 - 20 * 0.966) / 2 },
    ...[32, 42, 48, 64].map((px) => ({ name: `裝備格 ${px}`, px, a: px * (1 - 2 * GEAR_PAD), p: px * GEAR_PAD })),
  ];
  for (const res of [1, 2]) {
    for (const c of cases) {
      it(`${c.name}、res ${res}：左上角 × res 是整數、照原尺寸貼、離原本的中心不到半個裝置像素`, () => {
        const cvW = Math.max(4, Math.round(c.a * res));
        const o = blitOrigin(cvW, c.p, c.p, c.a, res);
        expect(isInt(o.x * res)).toBe(true);
        expect(isInt(o.y * res)).toBe(true);
        expect(o.w * res).toBe(cvW);
        expect(Math.abs(o.x + o.w / 2 - (c.p + c.a / 2))).toBeLessThanOrEqual(0.5 / res + 1e-9);
      });
    }
  }
  it("需求列的數值：圓章 20px a=19.32、p=0.34；裝備格 32px p=1.92、a=28.16；42px 2.52、36.96；48px 2.88、42.24；64px 3.84、56.32", () => {
    expect(20 * 0.966).toBeCloseTo(19.32, 9);
    expect((20 - 19.32) / 2).toBeCloseTo(0.34, 9);
    for (const [px, p, a] of [[32, 1.92, 28.16], [42, 2.52, 36.96], [48, 2.88, 42.24], [64, 3.84, 56.32]] as const) {
      expect(px * GEAR_PAD).toBeCloseTo(p, 9);
      expect(px * (1 - 2 * GEAR_PAD)).toBeCloseTo(a, 9);
    }
  });
});

describe("T9 確定性與不丟例外（假畫布）", () => {
  const log: FakeCanvasLog = { calls: null };
  beforeAll(() => {
    clearQWeaponDefs();
    setQCanvasFactory(fakeCanvasFactory(log));
  });
  afterAll(() => {
    setQCanvasFactory(null);
    clearQWeaponDefs();
  });
  const record = (fn: () => void): string[] => {
    const calls: string[] = [];
    log.calls = calls;
    fn();
    log.calls = null;
    return calls;
  };

  it("每款 × 材質（含不認得）× 關鍵字（無、1、2、不認得）× 稀有度 × 尺寸（≤24 圓章、>36 裝備格）畫兩次呼叫紀錄相同", () => {
    const KEYWORD_SETS: string[][] = [[], ["ignite"], ["charged", "marked"], ["nope"]];
    const seen = new Set<string>();
    let combos = 0;
    for (const k of WEAPON_KINDS) {
      for (const f of k.forms) {
        for (const material of [...appearance.materials, "unobtainium"]) {
          for (const keywords of KEYWORD_SETS) {
            for (const rarity of ["common", "epic", "mythic"]) {
              const look = { kind: k.id, form: f.id, material, keywords, rarity };
              const r = resolveGear(look);
              const key = [r.kind, r.form, r.material, r.keywords.join("+"), r.rarity].join("|");
              if (seen.has(key)) continue;
              seen.add(key);
              const def = qWeaponDef(qResolve(r));
              expect(def).not.toBeNull();
              if (def === null) continue;
              // 圓章 20px（≤24：small 分支）
              const badge = (): void => void render(def, 20 * def.meta.badge, 2, { ow: outlinePx(20), badge: true });
              expect(record(badge)).toEqual(record(badge));
              // 裝備格 48px（>36：畫關鍵字小圖樣）
              const gear = (): void => drawGear(fakeCtx(log, 96, 96), look, false, undefined, 48, 2);
              const once = record(gear);
              expect(once.length).toBeGreaterThan(0);
              expect(record(gear)).toEqual(once);
              combos += 1;
            }
          }
        }
      }
    }
    expect(combos).toBeGreaterThan(61 * 4 * 2);
  });
});
