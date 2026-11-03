// Phase 6M-1：鎖住「沒設姿勢時」紙娃娃的畫布指令流（逐像素相同的保證：指令與參數全精度相同 ⇒ 畫出來的像素相同）。
// 快照在加姿勢鉤子之前產生；之後任何改動讓沒設姿勢的外觀變了，這裡就會失敗。
// 範圍：所有人形單位範本 × 四朝向、10 族 × 四朝向、各欄位每種 kind（含武器各形制、成對武器、盾書珠）× 四朝向、體型、倒地。
import { describe, expect, it } from "vitest";
import type { Facing } from "../api/types";
import { KNOWN_KINDS, type DollSpec, type GearItem, type GearSlot } from "./appearance";
import { raceLookToLook } from "./inkRace";
import { drawFigurePose } from "./paperdoll";
import { resolveDollT, UNIT_DOLLS } from "./testDolls";
import raceLooks from "./fixtures/raceLooks.json";

function fmt(a: unknown): string {
  if (typeof a === "number") return Object.is(a, -0) ? "-0" : String(a);
  if (typeof a === "string") return JSON.stringify(a);
  if (Array.isArray(a)) return `[${a.map(fmt).join(",")}]`;
  return typeof a;
}

/** 全精度的畫布指令紀錄（含屬性設定），回傳 FNV-1a 雜湊與指令數。 */
export function streamHash(draw: (ctx: CanvasRenderingContext2D) => void): string {
  let h = 2166136261;
  let n = 0;
  const push = (s: string): void => {
    n++;
    for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
    h = Math.imul(h ^ 10, 16777619);
  };
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        push(`${prop}(${args.map(fmt).join(",")})`);
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      push(`${prop}=${fmt(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  draw(ctx);
  return `${(h >>> 0).toString(16).padStart(8, "0")}:${n}`;
}

const FACINGS: Facing[] = ["south", "north", "east", "west"];
const hashAll = (spec: DollSpec, downed = false): string => FACINGS.map((f) => streamHash((ctx) => drawFigurePose(ctx, spec, f, downed))).join(" ");

const BASE = resolveDollT({ team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword" });
const withGear = (g: DollSpec["gear"]): DollSpec => ({ ...BASE, gear: { ...BASE.gear, ...g } });
const W = (kind: string, form?: string, extra: Partial<GearItem> = {}): GearItem => ({ kind, ...(form === undefined ? {} : { form }), material: kind === "bow" || kind === "staff" ? "wood" : "steel", ...extra });

const WEAPON_FORMS: GearItem[] = [
  W("sword"), W("sword", "curved"), W("sword", "broad"), W("sword", "arcane"), W("sword", "arcane", { element: "fire" }),
  W("greatsword"), W("greatsword", "zhanma"), W("greatsword", "serrated"), W("dagger"), W("dagger", "kris"), W("axe"),
  W("hammer", "mace"), W("hammer", "flail"), W("hammer", "warhammer"), W("scythe"), W("fist", "knuckle"), W("fist", "katar"), W("fist", "claw"),
  W("spear"), W("spear", "halberd"), W("spear", "trident"), W("staff"), W("staff", "long", { element: "ice" }), W("staff", "totem"), W("staff", "scepter"), W("staff", "wand", { element: "fire" }),
  W("whip"), W("whip", "chain"), W("whip", "bladed"), W("bow"), W("crossbow", "light"), W("crossbow", "heavy"), W("crossbow", "repeater"),
  W("longgun", "flintlock"), W("longgun", "hunting"), W("longgun", "sniper"), W("pistol", "flintlock"), W("pistol", "revolver"), W("pistol", "derringer"),
  W("shotgun", "blunderbuss"), W("shotgun", "double"), W("shotgun", "pump"), W("whisk"), W("talisman"), W("puppet_cross"),
];
const PAIRS: GearItem[] = [W("dagger"), W("dagger", "kris"), W("sword"), W("axe"), W("pistol", "revolver"), W("hammer", "mace"), W("whip", "chain"), W("fist", "claw")];
const OFFS: GearItem[] = [{ kind: "shield_round", material: "wood", color: "#2f5fae" }, { kind: "shield_kite", material: "iron" }, { kind: "shield_kite", form: "tower", material: "steel" }, { kind: "tome", form: "book", material: "leather" }, { kind: "tome", form: "scroll" }, { kind: "orb", form: "ball", element: "ice", material: "crystal" }, { kind: "orb", form: "floating" }];
const label = (it: GearItem): string => [it.kind, it.form, it.element].filter((x) => x !== undefined).join("・");

describe("6M-1：沒設姿勢時紙娃娃逐像素相同（指令流快照）", () => {
  it("人形單位範本 × 四朝向", () => {
    const out: Record<string, string> = {};
    for (const tpl of Object.keys(UNIT_DOLLS).sort()) {
      if (UNIT_DOLLS[tpl]?.creature !== undefined) continue;
      out[tpl] = hashAll(resolveDollT({ team: "ally", summon: false, template: tpl, weaponId: "" }));
    }
    expect(out).toMatchSnapshot();
  });

  it("10 族 × 四朝向（含帽子、長袍、披風）", () => {
    const looks = raceLooks as Readonly<Record<string, Readonly<Record<string, unknown>>>>;
    const out: Record<string, string> = {};
    const variants: Array<[string, DollSpec["gear"]]> = [["", {}], ["+hood", { head: { kind: "hood", color: "#5a4a7a" } }], ["+wizard", { head: { kind: "wizard_hat", color: "#2c4f8a" } }], ["+helmet", { head: { kind: "helmet", material: "steel" } }], ["+robe+cape", { body: { kind: "robe", color: "#5a3a8a" }, cloak: { kind: "cape", color: "#a83030" } }]];
    for (const race of Object.keys(looks).sort()) {
      for (const [n, g] of variants) {
        const d = withGear({ main_hand: W("sword"), off_hand: undefined, ...g });
        out[`${race}${n}`] = hashAll({ ...d, look: { ...d.look, ...raceLookToLook(looks[race]) } });
      }
    }
    expect(out).toMatchSnapshot();
  });

  it("各欄位每種 kind × 四朝向", () => {
    const out: Record<string, string> = {};
    for (const slot of Object.keys(KNOWN_KINDS).sort() as GearSlot[]) {
      if (slot === "main_hand" || slot === "off_hand") continue;
      for (const kind of KNOWN_KINDS[slot]) out[`${slot}:${kind}`] = hashAll(withGear({ [slot]: { kind, material: "steel" } }));
    }
    out["hands:none"] = hashAll(withGear({ hands: undefined, main_hand: undefined, off_hand: undefined }));
    expect(out).toMatchSnapshot();
  });

  it("武器各形制、成對武器、副手 × 四朝向", () => {
    const out: Record<string, string> = {};
    for (const w of WEAPON_FORMS) out[`main:${label(w)}`] = hashAll(withGear({ main_hand: w, off_hand: undefined }));
    for (const w of PAIRS) out[`pair:${label(w)}`] = hashAll(withGear({ main_hand: w, off_hand: w }));
    for (const o of OFFS) out[`off:${label(o)}`] = hashAll(withGear({ main_hand: W("sword"), off_hand: o }));
    expect(out).toMatchSnapshot();
  });

  it("體型、倒地、空手", () => {
    const out: Record<string, string> = {};
    for (const build of ["stout", "tall"] as const) out[`build:${build}`] = hashAll({ ...BASE, look: { ...BASE.look, build } });
    out["downed"] = hashAll(BASE, true);
    out["bare"] = hashAll({ ...BASE, gear: {} });
    expect(out).toMatchSnapshot();
  });
});
