// 6V-3／6V-4 只換外觀：火表面（火苗＋焦痕）、室內後牆掛件、附魔台發光環（慢轉）、荒原祭壇黑曜岩石板、
// 主城廣場裝飾與許願池噴水。全部確定性；會動的（附魔環、噴水）減少動態時停在第 0 毫秒；來源不新增 Math.random。
import { describe, expect, it } from "vitest";
import { drawTile, fireTongue, scorchMarks, type TileArtSpec } from "./terrainArt";
import { SHIMMER, surfaceShimmer } from "./surfaceAnim";
import { backWallKey, drawBackWall, drawEnchantRunes, drawFurniture, ENCHANT_RING, ENCHANT_RUNES, HANGING_SETS, roomPalette, wallDecor, wallHangings, type RoomKind } from "./interiorArt";
import { enchantRingAngle, ENCHANT_RING_MS, fountainSpray, SPRAY_DROPS, SPRAY_MS } from "./ambientAnim";
import { AmbientLayer, enchantRingCenter, fountainSpout } from "./ambientLayer";
import { fountainGeom, FOUNTAIN_STONES, paintBuilding } from "./capitalArt";
import { drawEventArt } from "./eventArt";
import { OBSIDIAN, obsidianSlab } from "./eventArtParts";
import { TILE_SIZE } from "../battle/geometry";

// 沒有 @types/node：用變數名載入 node:fs（vitest 在 node 環境執行；來源掃描用）
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(3) : typeof a)).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") return { addColorStop: (o: number, c: string) => calls.push(`stop(${o},${c})`) };
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

function calls(fn: (ctx: CanvasRenderingContext2D) => void): string[] {
  const m = mockCtx();
  fn(m.ctx);
  return m.calls;
}

const NO = { n: false, s: false, w: false, e: false };
function spec(over: Partial<TileArtSpec> = {}): TileArtSpec {
  return { region: "", look: "", terrain: "stone", x: 2, y: 3, height: 0, surface: "none", surfSame: NO, lip: NO, wallFace: false, blocked: false, tint: null, ...over };
}

describe("火表面（6V-3）", () => {
  it("同一格畫兩次一樣、不同格不一樣（只看格子座標雜湊）", () => {
    const a = calls((c) => drawTile(c, spec({ surface: "fire" })));
    expect(a).toEqual(calls((c) => drawTile(c, spec({ surface: "fire" }))));
    expect(a).not.toEqual(calls((c) => drawTile(c, spec({ surface: "fire", x: 7 }))));
  });

  it("有黑底焦痕（深色不規則斑塊）與煙燻暈", () => {
    const got = calls((c) => drawTile(c, spec({ surface: "fire" })));
    expect(got).toContain("fillStyle=rgba(20,12,8,0.82)");
    expect(got.some((x) => x.startsWith("stop(0,rgba(18,10,6"))).toBe(true);
    // 焦斑是 8 點多邊形：至少 2 塊 → 至少 14 個 lineTo
    const scorch = calls((c) => {
      let i = 0;
      scorchMarks(c, () => ((i = (i * 7 + 3) % 10), i / 10));
    });
    expect(scorch.filter((x) => x.startsWith("lineTo(")).length).toBeGreaterThanOrEqual(14);
  });

  it("火苗是彎曲的火舌（貝茲曲線、三層色、兩側小火舌），不是三角錐", () => {
    const got = calls((c) => fireTongue(c, 26, 44, 16, 0.4));
    expect(got.filter((x) => x.startsWith("bezierCurveTo(")).length).toBe(6); // 3 層 × 左右
    expect(got.filter((x) => x.startsWith("quadraticCurveTo(")).length).toBeGreaterThanOrEqual(8);
    for (const c of ["fillStyle=rgba(214,58,20,0.95)", "fillStyle=#ff8a1e", "fillStyle=#ffe07a", "fillStyle=rgba(226,72,24,0.9)"]) expect(got).toContain(c);
    // 尖端往 lean 那一側偏：最外層的尖端 x > 底部中心
    const tipCall = got.find((x) => x.startsWith("bezierCurveTo("))!;
    const nums = tipCall.slice(14, -1).split(",").map(Number);
    expect(nums[4]).toBeGreaterThan(26);
    const fire = calls((c) => drawTile(c, spec({ surface: "fire" })));
    const tongues = fire.filter((x) => x === "fillStyle=#ffe07a").length;
    expect(tongues).toBeGreaterThanOrEqual(2);
    expect(tongues).toBeLessThanOrEqual(3);
  });

  it("火光閃動照舊是時間 → 相位的確定性函式（減少動態時 SurfaceAnimator 不登記，畫面靜止）", () => {
    expect(surfaceShimmer("fire", 3, 4, 1234)).toEqual(surfaceShimmer("fire", 3, 4, 1234));
    expect(surfaceShimmer("fire", 3, 4, 0)).not.toEqual(surfaceShimmer("fire", 3, 4, SHIMMER.fireMs / 3));
  });
});

describe("室內後牆掛件（6V-3）", () => {
  it("掛件避開擺設與緊貼後牆的物件、相鄰兩欄只掛一個；種類照室內輪流", () => {
    for (const kind of ["tavern", "smithy", "mentor", "plain"] as RoomKind[]) {
      const blocked = kind === "mentor" ? [1, 2, 3, 6] : [5, 6, 7];
      const decor = wallDecor(kind, 10, blocked);
      const hang = wallHangings(kind, 10, blocked, decor);
      expect(hang.length, kind).toBeGreaterThan(0);
      const taken = new Set([...blocked, ...decor.flatMap((d) => Array.from({ length: d.w }, (_, i) => d.x + i))]);
      for (const h of hang) {
        expect(taken.has(h.x), `${kind}@${h.x}`).toBe(false);
        expect(h.x).toBeGreaterThanOrEqual(1);
        expect(h.x).toBeLessThanOrEqual(8);
      }
      for (let i = 1; i < hang.length; i++) expect(hang[i]!.x - hang[i - 1]!.x).toBeGreaterThanOrEqual(2);
      expect(hang.map((h) => h.kind)).toEqual(HANGING_SETS[kind].slice(0, hang.length));
      expect(wallHangings(kind, 10, blocked, decor)).toEqual(hang);
    }
    // 主城三間室內（緊貼後牆的物件照內容）：每間都至少有一個掛件
    expect(wallHangings("tavern", 10, [5, 6, 7], wallDecor("tavern", 10, [5, 6, 7])).length).toBeGreaterThanOrEqual(1);
    expect(wallHangings("smithy", 10, [1], wallDecor("smithy", 10, [1])).map((h) => h.kind)).toContain("tools");
  });

  it("後牆畫法確定、掛件進快取鍵；小窗（天色）、掛燈（暖光）、工具板都畫得出來", () => {
    const p = roomPalette("smithy", "town");
    const decor = wallDecor("smithy", 10, []);
    const hang = wallHangings("smithy", 10, [], decor);
    const a = calls((c) => drawBackWall(c, 10, p, decor, hang));
    expect(a).toEqual(calls((c) => drawBackWall(c, 10, p, decor, hang)));
    expect(a).not.toEqual(calls((c) => drawBackWall(c, 10, p, decor)));
    expect(backWallKey(10, p, decor, hang)).not.toBe(backWallKey(10, p, decor));
    expect(backWallKey(10, p, decor)).toBe(`wall|10|${p.wall}|${decor.map((d) => `${d.kind}@${d.x}`).join(",")}`); // 沒有掛件時鍵照舊
    const all = calls((c) => drawBackWall(c, 10, roomPalette("tavern", "town"), [], [{ kind: "window", x: 1 }, { kind: "wall_lamp", x: 3 }, { kind: "tools", x: 5 }, { kind: "pans", x: 7 }]));
    expect(all).toContain("stop(0,#9fd0f0)");
    expect(all.some((x) => x.startsWith("stop(0,rgba(255,200,110"))).toBe(true);
    expect(all).toContain("strokeStyle=#9aa2aa");
    expect(all).toContain("fillStyle=#b8743a");
    const ashen = calls((c) => drawBackWall(c, 10, roomPalette("tavern", "ashen"), [], [{ kind: "window", x: 1 }]));
    expect(ashen).toContain("stop(0,#5a3a3a)"); // 荒原窗外是暗紅黃昏
  });
});

describe("附魔台的發光環（6V-3）", () => {
  it("靜態貼圖：粗亮環（線寬 3、紫色光暈 12）＋內細環＋外圈暈染", () => {
    const got = calls((c) => drawFurniture(c, { look: "enchant", joinW: false, joinE: false }));
    expect(got).toContain("lineWidth=3");
    expect(got).toContain("shadowBlur=12");
    expect(got).toContain("strokeStyle=#e6e0ff");
    expect(got.some((x) => x.startsWith("stop(0.6,rgba(168,152,255,0.45)"))).toBe(true);
    expect(got).toEqual(calls((c) => drawFurniture(c, { look: "enchant", joinW: false, joinE: false })));
  });

  it("符文環 8 個符文；角度是時間 → 相位（慢轉：一圈 ≥ 10 秒）、確定性", () => {
    const runes = calls((c) => drawEnchantRunes(c, 28, 28, 24));
    expect(runes.filter((x) => x.startsWith("rotate(")).length).toBe(ENCHANT_RUNES);
    expect(ENCHANT_RING_MS).toBeGreaterThanOrEqual(10000);
    expect(enchantRingAngle("a", 500)).toBe(enchantRingAngle("a", 500));
    expect(enchantRingAngle("a", ENCHANT_RING_MS) - enchantRingAngle("a", 0)).toBeCloseTo(Math.PI * 2, 6);
    // 環的中心在家具畫布的所在格頂往下 cy：和靜態貼圖同一個位置
    const k = TILE_SIZE / 52;
    expect(enchantRingCenter({ x: 7, y: 2 }, 0)).toEqual({ x: 7 * TILE_SIZE + 26 * k, y: 2 * TILE_SIZE + ENCHANT_RING.cy * k, rx: ENCHANT_RING.rx * k, ry: ENCHANT_RING.ry * k });
  });
});

describe("荒原祭壇的黑曜岩石板（6V-3）", () => {
  it("荒原祭壇前三格是黑曜岩（近黑、暗紅發光裂紋），不再畫雲嶺青石板；雲嶺照舊", () => {
    const ash = calls((c) => drawEventArt(c, "altar", "ashen"));
    expect(ash).toContain(`fillStyle=${OBSIDIAN.base}`);
    expect(ash.filter((x) => x === `shadowColor=${OBSIDIAN.glow}`).length).toBe(3);
    expect(ash).not.toContain("fillStyle=#56645c");
    const cloud = calls((c) => drawEventArt(c, "altar", "cloud"));
    expect(cloud).toContain("fillStyle=#56645c");
    expect(cloud).not.toContain(`fillStyle=${OBSIDIAN.base}`);
    expect(calls((c) => obsidianSlab(c, 2, 1))).toEqual(calls((c) => obsidianSlab(c, 2, 1)));
    expect(calls((c) => obsidianSlab(c, 2, 1))).not.toEqual(calls((c) => obsidianSlab(c, 3, 1)));
  });
});

describe("許願池（6V-4）", () => {
  const spec = { kind: "fountain" as const, w: 2, h: 2, doors: [], roof: 0 };

  it("圓形石緣水池：前緣立面、石塊接縫、池水；畫法確定；石座與噴口在池心正上方", () => {
    const got = calls((c) => paintBuilding(c, spec));
    expect(got).toEqual(calls((c) => paintBuilding(c, spec)));
    expect(got).toContain("fillStyle=#a89a7c"); // 前緣立面
    expect(got.some((x) => x.startsWith("stop(0,#2f74b8"))).toBe(true); // 池水
    expect(got.filter((x) => x.startsWith("lineTo(")).length).toBeGreaterThanOrEqual(FOUNTAIN_STONES);
    const g = fountainGeom(spec);
    expect(g.ry / g.rx).toBeCloseTo(0.62, 2); // 透視的圓
    expect(g.spoutX).toBe(g.cx);
    expect(g.cy + g.ry + g.lip).toBeLessThanOrEqual(2 * 52);
  });

  it("噴水：左右兩道水弧＋中央水柱；從噴口出發、落在池裡；時間 → 位置，確定性", () => {
    const sp = fountainSpout({ x: 4, y: 3, spec }, 0);
    const g = fountainGeom(spec);
    const k = TILE_SIZE / 52;
    expect(sp.x).toBeCloseTo(4 * TILE_SIZE + g.spoutX * k, 6);
    expect(sp.reach).toBeLessThan((g.rx - g.rim) * k); // 落點在池水內
    const a = fountainSpray("s", 333, sp.reach, sp.drop);
    expect(a).toEqual(fountainSpray("s", 333, sp.reach, sp.drop));
    expect(a).toHaveLength(SPRAY_DROPS * 2 + 3);
    expect(a).not.toEqual(fountainSpray("s", 333 + SPRAY_MS / 4, sp.reach, sp.drop));
    for (const d of a) {
      expect(Math.abs(d.x)).toBeLessThanOrEqual(sp.reach + 1e-9);
      expect(d.y).toBeLessThanOrEqual(sp.drop + 1e-9);
      expect(d.alpha).toBeGreaterThanOrEqual(0);
    }
    expect(a.some((d) => d.x < 0) && a.some((d) => d.x > 0)).toBe(true);
  });

  it("減少動態（或關掉）時環境動態層不推進時鐘：噴水、符文環停在第 0 毫秒", () => {
    const layer = new AmbientLayer();
    layer.reduced = true;
    layer.tick(500);
    expect(layer.clock).toBe(0);
    layer.reduced = false;
    layer.enabled = false;
    layer.tick(500);
    expect(layer.clock).toBe(0);
    layer.enabled = true;
    layer.tick(500);
    expect(layer.clock).toBe(500);
  });
});

describe("來源掃描", () => {
  it("6V-3／6V-4 動到的畫法檔沒有 Math.random(", () => {
    const files = ["terrainArt.ts", "interiorArt.ts", "ambientAnim.ts", "ambientLayer.ts", "capitalArt.ts", "eventArt.ts", "eventArtParts.ts", "sceneryLayer.ts", "plazaDecor.ts", "sceneryModel.ts"];
    for (const f of files) {
      const src = readFileSync(`src/render/${f}`, "utf-8")
        .split("\n")
        .filter((l) => !l.trim().startsWith("//") && !l.trim().startsWith("*"))
        .join("\n");
      expect(src, f).not.toMatch(/Math\.random\(/);
    }
  });
});
