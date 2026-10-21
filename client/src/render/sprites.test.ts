/// <reference types="vite/client" />
import { describe, expect, it } from "vitest";
import {
  allSpriteRefs,
  objectSprite,
  SpriteBook,
  spriteUrl,
  terrainSprite,
  unitSprite,
} from "./sprites";

// 用 Vite 的 glob 列出 client/public 內的檔案（不需要 Node 型別）。
const FILES = new Set(Object.keys(import.meta.glob("../../public/assets/kenney/**/*", { query: "?url" })));
const has = (path: string): boolean => FILES.has(`../../public${path}`);

describe("sprites 對照表", () => {
  it("用到的每一張圖與每個包的 License.txt 都在 client/public", () => {
    const packs = new Set<string>();
    for (const ref of allSpriteRefs()) {
      expect(has(spriteUrl(ref)), spriteUrl(ref)).toBe(true);
      packs.add(ref.pack);
    }
    for (const pack of packs) expect(has(`/assets/kenney/${pack}/License.txt`)).toBe(true);
  });

  it("沒有對照的地形與物件回傳 null（退回色塊）", () => {
    expect(terrainSprite("no_such_terrain_2")).toBeNull();
    expect(terrainSprite("lava")).toBeNull(); // 程式繪製紋理（3-14）
    expect(terrainSprite("stone")).not.toBeNull();
    expect(terrainSprite("no_such_terrain")).toBeNull();
    expect(objectSprite("no_such_object")).toBeNull();
  });

  it("沒有對照的單位範本用陣營預設圖", () => {
    expect(unitSprite("brand_new_unit", "ally")).toEqual(unitSprite("another_new_unit", "ally"));
    expect(unitSprite("brand_new_unit", "ally")).not.toEqual(unitSprite("brand_new_unit", "enemy"));
    expect(unitSprite("hero_mage", "ally").tile).toBe("0084");
  });

  it("貼圖庫沒載入的圖查不到、參考為 null 也不出錯", () => {
    const book = new SpriteBook<string>();
    const ref = unitSprite("hero_mage", "ally");
    expect(book.get(ref)).toBeUndefined();
    expect(book.get(null)).toBeUndefined();
    book.set(ref, "tex");
    expect(book.get(ref)).toBe("tex");
  });
});
