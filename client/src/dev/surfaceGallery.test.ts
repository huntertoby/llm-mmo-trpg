import { describe, expect, it } from "vitest";
import { buildDrawModel } from "../battle/drawModel";
import { tileArtSpec } from "../render/artSpecs";
import { drawTile } from "../render/terrainArt";
import { SURFACE_GALLERY_HERO, surfaceGalleryView } from "./surfaceGallery";

describe("地表併塊示範場景（6A-4a）", () => {
  it("八種地表都有，含內凹角與異種相鄰；每格都畫得出來", () => {
    const model = buildDrawModel(surfaceGalleryView(), SURFACE_GALLERY_HERO);
    const surfaces = new Set<string>(model.tiles.map((t) => t.surface));
    for (const s of ["ice", "oil", "fire", "water", "poison", "holy", "darkness", "smoke"]) expect(surfaces.has(s), s).toBe(true);
    const specs = model.tiles.map((t) => tileArtSpec(model, t));
    // 內凹角：兩邊接縫、斜鄰不是同種
    const concave = specs.some((s) => s.surface !== "none" && ((s.surfSame.n && s.surfSame.e && s.surfDiag?.ne === false) || (s.surfSame.s && s.surfSame.w && s.surfDiag?.sw === false)));
    expect(concave).toBe(true);
    // 異種相鄰（冰接油）
    const ice = specs.find((s) => s.x === 6 && s.y === 7)!;
    expect(ice.surface).toBe("ice");
    expect(ice.surfSame.e).toBe(false);
    expect(model.traps).toHaveLength(2);
    const ctx = new Proxy({}, { get: () => () => ({ addColorStop: () => undefined }), set: () => true }) as unknown as CanvasRenderingContext2D;
    for (const s of specs) expect(() => drawTile(ctx, s)).not.toThrow();
  });
});
