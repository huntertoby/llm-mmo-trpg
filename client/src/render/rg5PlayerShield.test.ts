// RG-5 玩家大盾（#163 護陣；docs/art/RG樣張.md 10.4、10.5、10.8 P-1／P-2）：雲紋碑盾 sect_great 給玩家（材質補色）、熔殼塔盾 molten_shell。
// 像素和樣張逐點相同由開發頁 dev/rg5-shield-gallery.html?mode=shield｜doll｜icon 檢查；這裡鎖住接線與配色規則。
import { describe, expect, it } from "vitest";
import { isTowerLike, S, type QItem, type QUnit, type QView } from "./qCore";
import { drawQ } from "./qDoll";
import { gearKinds, signatureFormZh } from "./gearResolve";
import { qPalette, qResolve, qWeaponDef, Q_WEAPON_KINDS } from "./qIcon/weapons";
import { crack, SHELL_FIX, shellPal, shellPalOf } from "./qMoltenShell";
import { sectPal, sectPalOf } from "./qSectShield";
import { GAME_HOOKS, qUnitOf } from "./qSpec";
import { resolveDollT } from "./testDolls";

function fills(u: QUnit, view: QView, west = false): string[] {
  const out: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(t, p: string) {
      if (p in t) return t[p];
      if (p === "getTransform") return () => ({ a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 });
      return () => undefined;
    },
    set(t, p: string, v) {
      t[p] = v;
      if (p === "fillStyle" || p === "strokeStyle") out.push(String(v).toLowerCase());
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  drawQ(ctx, u, view, GAME_HOOKS, null, west);
  return out;
}
const hero = (): QUnit => qUnitOf(resolveDollT({ template: "hero_fighter", team: "ally", summon: false, weaponId: "one_handed_sword" }));
const withOff = (u: QUnit, off: QItem): QUnit => ({ look: u.look, gear: { ...u.gear, off_hand: off } });
const shield = (form: string, material: string, element?: string): QItem => ({ kind: "shield_kite", form, material, ...(element !== undefined ? { element } : {}) });
/** S.hooks 只在 drawQ 裡面有值；直接呼叫配色函式時暫時掛上遊戲端的 hooks。 */
function withHooks<T>(fn: () => T): T {
  const keep = S.hooks;
  S.hooks = GAME_HOOKS;
  try {
    return fn();
  } finally {
    S.hooks = keep;
  }
}
const VIEWS: ReadonlyArray<readonly [QView, boolean]> = [
  ["front", false],
  ["back", false],
  ["side", false],
  ["side", true],
];

describe("RG-5 握法", () => {
  it("isTowerLike 認熔殼塔盾", () => {
    expect(isTowerLike({ kind: "shield_kite", form: "molten_shell" })).toBe(true);
    expect(isTowerLike({ kind: "shield_round", form: "molten_shell" })).toBe(false);
  });
});

describe("RG-5 雲紋碑盾配色（10.4、P-1）", () => {
  it("五種材質照 material.ts：鐵、銅月白邊；鋼、銀、金暗邊＋圓章圈；金的銅釘改盾邊暗 10%", () => {
    const p = (m: string) => withHooks(() => sectPal(shield("sect_great", m)));
    expect(p("iron")).toEqual({ face: "#7a828b", rim: "#dfe4e2", rivet: "#e8bb48", ring: null, emblem: "peak" });
    expect(p("copper")).toMatchObject({ face: "#b06a3c", rim: "#dfe4e2", ring: null });
    expect(p("steel")).toMatchObject({ face: "#a9b6c6", rim: "#626e7c", ring: "#626e7c", rivet: "#e8bb48" });
    expect(p("silver")).toMatchObject({ rim: "#979ea7", ring: "#979ea7" });
    expect(p("gold")).toMatchObject({ face: "#e8bb48", rim: "#8c681d", rivet: "#7e5e1a", ring: "#8c681d" });
  });

  it("P-1：盾邊照材質本色判斷，元素只染盾面（鐵、銅＋雷／冰仍是月白邊；鋼＋冰仍是本色暗邊）", () => {
    for (const [m, el] of [["iron", "lightning"], ["iron", "ice"], ["copper", "lightning"], ["copper", "ice"]] as const) {
      const pal = withHooks(() => sectPal(shield("sect_great", m, el)));
      expect(pal.rim, `${m}+${el}`).toBe("#dfe4e2");
      expect(pal.face, `${m}+${el}`).not.toBe(withHooks(() => sectPal(shield("sect_great", m))).face);
    }
    expect(withHooks(() => sectPal(shield("sect_great", "steel", "ice"))).rim).toBe("#626e7c");
  });

  it("敵人範本（帶 color、trim、emblem）照原樣，不補色", () => {
    expect(sectPal({ kind: "shield_kite", form: "sect_great", material: "wood", color: "#5f8f8a", trim: "#dfe4e2", emblem: "peak" })).toEqual({ face: "#5f8f8a", rim: "#dfe4e2", rivet: "#e8bb48", ring: null, emblem: "peak" });
  });

  it("玩家拿碑盾：四個方向都畫，正面、側面有紋樣（朱紅峰頂）與材質色盾面", () => {
    const u = withOff(hero(), shield("sect_great", "steel"));
    for (const [v, w] of VIEWS) {
      const f = fills(u, v, w);
      if (v === "back") expect(f, "back").toContain("#4a535d"); // 盾背的邊＝盾邊（#626e7c）暗 25%
      else {
        expect(f, `${v} ${w}`).toContain("#a9b6c6");
        expect(f, `${v} ${w}`).toContain("#c0392b");
        expect(f, `${v} ${w}`).toContain("#626e7c"); // 圓章圈
      }
    }
  });
});

describe("RG-5 熔殼塔盾（10.2、10.4、P-2）", () => {
  it("殼板＝材質主色往玄武岩混 0.35（10.4 表的金、銀）", () => {
    expect(shellPalOf("#e8bb48")).toEqual({ plate: "#b18c40", lit: "#bd9e5f", low: "#917334", inner: "#6e5728", edge: "#7c622d" });
    expect(shellPalOf("#e8edf2").plate).toBe("#b1adae");
    expect(withHooks(() => shellPal(shield("molten_shell", "iron"))).plate).toBe("#69676c");
  });

  it("四個方向都畫：殼板色與固定的殼縫紅光（元素不換殼縫色）", () => {
    for (const el of [undefined, "ice"]) {
      const it = shield("molten_shell", "gold", el);
      const plate = withHooks(() => shellPal(it)).plate;
      const u = withOff(hero(), it);
      for (const [v, w] of VIEWS) {
        const f = fills(u, v, w);
        expect(f, `${v} ${w}`).toContain(plate);
        expect(f, `${v} ${w}`).toContain(SHELL_FIX.glow);
        expect(f, `${v} ${w}`).toContain(SHELL_FIX.core);
      }
    }
  });

  it("P-2：三道殼縫長短、位置、間距都不同，中間最長、上面只裂左半邊、下面有分岔", () => {
    const ln = [0, 1, 2].map((v) => crack(v, 1.5));
    const span = (pts: ReadonlyArray<readonly [number, number]>): number => pts[pts.length - 1]![0] - pts[0]![0];
    const spans = ln.map((l) => span(l[0]!));
    expect(spans[1]).toBeGreaterThan(spans[0]!);
    expect(spans[1]).toBeGreaterThan(spans[2]!);
    expect(spans[0]).not.toBeCloseTo(spans[2]!, 1);
    expect(Math.max(...ln[0]![0]!.map(([x]) => x))).toBeLessThan(1.5); // 上面那道停在中線附近
    expect(ln.map((l) => l.length)).toEqual([1, 1, 2]);
    const ys = ln.map((l) => l[0]!.reduce((s, [, y]) => s + y, 0) / l[0]!.length); // 每道的平均高度
    expect(Math.abs(ys[1]! - ys[0]! - (ys[2]! - ys[1]!))).toBeGreaterThan(1); // 間距不等分
    expect(ln.map((l) => l[0]!.length)).not.toEqual([5, 5, 5]); // 節數不同
  });
});

describe("RG-5 圖示表", () => {
  it("kite_shield.forms 有兩款，名稱定案", () => {
    expect(Q_WEAPON_KINDS["kite_shield"]?.forms).toMatchObject({ sect_great: "雲紋碑盾", molten_shell: "熔殼塔盾" });
  });

  it("RG-8 K-1：形制名（物品卡副標、背包說明）只有限定副手特性的兩款大盾有，名字和圖示表同一份", () => {
    expect(signatureFormZh({ kind: "kite_shield", form: "sect_great" })).toBe("雲紋碑盾");
    expect(signatureFormZh({ kind: "kite_shield", form: "molten_shell" })).toBe("熔殼塔盾");
    for (const look of [{ kind: "kite_shield", form: "tower" }, { kind: "kite_shield", form: "kite" }, { kind: "kite_shield" }, { form: "sect_great" }, { kind: "round_shield", form: "sect_great" }, null]) {
      expect(signatureFormZh(look), JSON.stringify(look)).toBeNull();
    }
    const named = gearKinds().flatMap((k) => k.forms.filter((f) => signatureFormZh({ kind: k.id, form: f.id }) !== null).map((f) => `${k.id}.${f.id}`));
    expect(named).toEqual(["kite_shield.sect_great", "kite_shield.molten_shell"]);
  });

  it("兩款都有圖樣：直立塊狀（關鍵字小圖樣用 block 那組）、圓章縮放上限 0.87", () => {
    for (const form of ["sect_great", "molten_shell"]) {
      const def = qWeaponDef(qResolve({ kind: "kite_shield", form, material: "iron", keywords: [], rarity: "common" }));
      expect(def, form).not.toBeNull();
      expect(def!.meta.diag).toBe(false);
      expect(def!.meta.spots).toEqual([
        [17, 17],
        [31, 31],
      ]);
      expect(def!.meta.badge).toBeLessThanOrEqual(0.87);
    }
  });

  it("圖示的碑盾配色：盾面照圖示的關鍵字混色（40%），盾邊照材質本色", () => {
    const r = qResolve({ kind: "kite_shield", form: "sect_great", material: "iron", keywords: ["charged"], rarity: "common" });
    const P = qPalette(r);
    const B = qPalette({ ...r, keywords: [], tintKw: undefined });
    expect(sectPalOf(P.a, B.a, B.d).rim).toBe("#dfe4e2");
  });
});
