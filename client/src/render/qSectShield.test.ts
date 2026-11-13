// RG-4 持盾弟子的雲紋碑盾（docs/art/RG樣張.md 9.8 第 1、2 條）：isTowerLike、emblem 一路傳到 QItem、sect_great 三個方向都畫。
// 像素和樣張逐點相同由開發頁 dev/rg4-shield-gallery.html?mode=shield／doll 檢查，這裡只鎖住接線。
import { describe, expect, it } from "vitest";
import { isTowerLike, type QItem, type QUnit, type QView } from "./qCore";
import { drawQ } from "./qDoll";
import { qUnitOf, GAME_HOOKS } from "./qSpec";
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

const disciple = (): QUnit => qUnitOf(resolveDollT({ template: "sect_shield_disciple", team: "enemy", summon: false, weaponId: "one_handed_sword" }));
const withOff = (u: QUnit, off: QItem): QUnit => ({ look: u.look, gear: { ...u.gear, off_hand: off } });
const RED = "#c0392b"; // 峰頂朱紅（紋樣）
const BACK_RIM = "#a7abaa"; // 盾背的邊（盾邊色月白暗 25%）
const VIEWS: ReadonlyArray<readonly [QView, boolean]> = [
  ["front", false],
  ["back", false],
  ["side", false],
  ["side", true],
];

describe("RG-4 雲紋碑盾", () => {
  it("isTowerLike：塔盾與門派大盾；鳶盾、圓盾、沒有形制都不是", () => {
    expect(isTowerLike({ kind: "shield_kite", form: "tower" })).toBe(true);
    expect(isTowerLike({ kind: "shield_kite", form: "sect_great" })).toBe(true);
    expect(isTowerLike({ kind: "shield_kite", form: "kite" })).toBe(false);
    expect(isTowerLike({ kind: "shield_kite" })).toBe(false);
    expect(isTowerLike({ kind: "shield_round", form: "tower" })).toBe(false);
    expect(isTowerLike({ kind: "tome", form: "sect_great" })).toBe(false);
    expect(isTowerLike(undefined)).toBe(false);
    expect(isTowerLike(null)).toBe(false);
  });

  it("持盾弟子的 doll（content → unitDolls.json → resolveDoll → qUnitOf）帶著 sect_great、盾邊色與 emblem", () => {
    expect(disciple().gear.off_hand).toMatchObject({ kind: "shield_kite", form: "sect_great", color: "#5f8f8a", trim: "#dfe4e2", emblem: "peak" });
  });

  it("沒寫 emblem 的裝備不多出欄位", () => {
    const u = qUnitOf(resolveDollT({ template: "bandit_shieldbearer", team: "enemy", summon: false, weaponId: "one_handed_sword" }));
    expect(u.gear.off_hand).toBeDefined();
    expect("emblem" in (u.gear.off_hand ?? {})).toBe(false);
  });

  it("sect_great 四個方向都畫（正面、側面畫盾面與盾邊；背面畫盾背的邊）；正面、側面有紋樣，背面沒有", () => {
    const u = disciple();
    for (const [v, w] of VIEWS) {
      const f = fills(u, v, w);
      if (v === "back") {
        expect(f, "back").toContain(BACK_RIM);
        expect(f, "back").not.toContain(RED);
      } else {
        expect(f, `${v} ${w}`).toContain("#5f8f8a");
        expect(f, `${v} ${w}`).toContain("#dfe4e2");
        expect(f, `${v} ${w}`).toContain(RED);
      }
    }
    // 換成塔盾就沒有碑盾的盾背邊、紋樣
    const tower = withOff(u, { kind: "shield_kite", form: "tower", material: "wood", color: "#5f8f8a" });
    expect(fills(tower, "back")).not.toContain(BACK_RIM);
    expect(fills(tower, "front")).not.toContain(RED);
  });

  it("不認得的 emblem 不畫紋樣；沒有顏色時用樣張預設的青面月白邊", () => {
    const u = disciple();
    const odd = withOff(u, { kind: "shield_kite", form: "sect_great", material: "wood", emblem: "taiji" });
    for (const v of ["front", "side"] as const) {
      const f = fills(odd, v);
      expect(f, v).not.toContain(RED);
      expect(f, v).toContain("#5f8f8a");
      expect(f, v).toContain("#dfe4e2");
    }
  });
});
