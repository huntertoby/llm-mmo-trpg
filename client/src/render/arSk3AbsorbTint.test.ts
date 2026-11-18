// AR-SK3：吸收表面的部件圖樣照表面的代表色染色（`docs/art/AR-SK2驗收.md` 裁定 3；沒有對應色用水色）。
import { describe, expect, it } from "vitest";
import * as QP from "./qIcon/parts";
import * as QS from "./qIcon/skills";
import { toQParts } from "./qIcon/partsAdapter";
import { effectPart } from "./skillParts";
import type { SkillIconData } from "../api/types";
import { partsOf } from "./skillIcon";

const water = QS.TINT.water;

describe("吸收表面的染色", () => {
  it("表面 → 代表色：火、冰、毒、聖光照元素色，黑暗＝暗影色，油、煙霧、不認得、沒指定＝水色", () => {
    expect(QP.surfaceTint("fire")).toEqual(QS.TINT.fire);
    expect(QP.surfaceTint("ice")).toEqual(QS.TINT.ice);
    expect(QP.surfaceTint("poison")).toEqual(QS.TINT.poison);
    expect(QP.surfaceTint("holy")).toEqual(QS.TINT.holy);
    expect(QP.surfaceTint("darkness")).toEqual(QS.TINT.shadow);
    expect(QP.surfaceTint("water")).toEqual(water);
    for (const s of ["oil", "smoke", "brand_new", "", null, undefined]) expect(QP.surfaceTint(s)).toEqual(water);
  });
  it("部件：指定表面時帶染色，沒有指定時照舊（不帶 tint，畫預設水色）", () => {
    expect(effectPart({ type: "absorb_surface", surface: "fire" }).q).toEqual({ cat: "effect", id: "absorb_surface", tint: QS.TINT.fire });
    expect(effectPart({ type: "absorb_surface" }).q).toEqual({ cat: "effect", id: "absorb_surface" });
    expect(effectPart({ type: "damage", surface: "fire" }).q).toEqual({ cat: "effect", id: "damage" });
  });
  it("完整圖示的效果列也帶同一個染色", () => {
    const icon = { kind: "active", rarity: "rare", elements: [], segments: [{ shape_id: "single", skeleton: "strike", effects: [{ type: "absorb_surface", surface: "poison" }, { type: "damage" }] }], costs: [], trigger: null, link: null, condition: null, modifier: null } as unknown as SkillIconData;
    const q = toQParts(icon, partsOf(icon));
    expect(q.row.find((r) => r.id === "absorb_surface")?.tint).toEqual(QS.TINT.poison);
    expect(q.row.find((r) => r.id === "damage")?.tint).toBeUndefined();
  });
});
