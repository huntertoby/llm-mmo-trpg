// 6R-F（前端審查第 1、2、9 點）：貼圖 hold 在重畫後放開沒畫到的 owner；畫面上活著的 Sprite 拿著的貼圖一律不銷毀；
// 位元組預算；異形姿勢的位移不進貼圖鍵。
import { Container, Sprite, Texture, TextureSource } from "pixi.js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ArtTextures, liveSpriteTextures } from "./artTextures";
import { splitCreatureOffset } from "./creaturePose";

/** 假的離屏 canvas（node 環境沒有 DOM）：`Texture.from` 換成建一張新的貼圖。 */
const fakeCanvas = (w: number, h: number) => ({ width: w, height: h }) as unknown as HTMLCanvasElement;

describe("ArtTextures holds and the live-sprite safety net (6R-F)", () => {
  beforeEach(() => {
    vi.spyOn(Texture, "from").mockImplementation(() => new Texture({ source: new TextureSource({ width: 1, height: 1 }) }));
  });
  afterEach(() => vi.restoreAllMocks());

  it("owners not drawn this round (dead, left, other map, finished ghosts) are released at endFrame", () => {
    const art = new ArtTextures();
    const a = art.canvas("a", () => fakeCanvas(10, 10))!;
    const b = art.canvas("b", () => fakeCanvas(10, 10))!;
    art.holdFor("u_alive", a);
    art.holdFor("u_dead", b);
    art.holdFor("ghost:u_alive#1", b);
    art.beginFrame();
    art.canvas("a", () => fakeCanvas(10, 10));
    art.holdFor("u_alive", a); // 這一輪畫到的人
    art.endFrame();
    expect(art.stats().owners).toBe(1);
    expect(art.isHeld(a)).toBe(true);
    expect(art.isHeld(b)).toBe(false);
    expect(art.stats().count).toBe(1); // b 沒畫到、沒人 hold、也不在畫面上：銷毀
  });

  it("a texture still on a live Sprite is never destroyed, even when nobody holds it", () => {
    const art = new ArtTextures();
    const stage = new Container();
    art.setLiveProbe(() => liveSpriteTextures(stage));
    const ghostTex = art.canvas("ghost-pose", () => fakeCanvas(10, 10))!;
    const ghost = new Sprite(ghostTex);
    stage.addChild(ghost); // 還在播的殘影，owner 已在 endFrame 被放開
    art.beginFrame();
    art.endFrame();
    expect(ghostTex.destroyed).toBe(false);
    expect(art.stats().count).toBe(1);
    ghost.destroy();
    art.beginFrame();
    art.endFrame();
    expect(ghostTex.destroyed).toBe(true);
  });

  it("evicted textures on a live Sprite survive flushes until the Sprite is gone", () => {
    const bytes = 10 * 10 * 4;
    const art = new ArtTextures(bytes * 2);
    const stage = new Container();
    art.setLiveProbe(() => liveSpriteTextures(stage));
    const shown = art.canvas("turned", () => fakeCanvas(10, 10))!; // 轉身後新畫的朝向（重畫之間，沒有釘選）
    stage.addChild(new Sprite(shown));
    for (let i = 0; i < 6; i++) art.canvas(`walk${i}`, () => fakeCanvas(10, 10)); // 別人走路要了很多姿勢：超過預算
    expect(art.stats().bytes).toBeLessThanOrEqual(bytes * 2);
    expect(shown.destroyed).toBe(false);
    art.beginFrame();
    art.endFrame();
    expect(shown.destroyed).toBe(false);
  });

  it("budget is bytes (w*h*4): two big textures cost as much as many small ones", () => {
    const art = new ArtTextures(100 * 100 * 4);
    art.canvas("big1", () => fakeCanvas(100, 50));
    art.canvas("big2", () => fakeCanvas(100, 50));
    expect(art.stats().count).toBe(2);
    art.canvas("big3", () => fakeCanvas(100, 50));
    expect(art.stats().count).toBe(2); // 第三張大的進來就淘汰最舊的
    expect(art.stats().bytes).toBe(100 * 100 * 4);
  });

  it("unique owners: two dodges of the same unit in one step do not knock each other's hold off", () => {
    const art = new ArtTextures();
    const t1 = art.canvas("p1", () => fakeCanvas(4, 4))!;
    const t2 = art.canvas("p2", () => fakeCanvas(4, 4))!;
    const o1 = art.uniqueOwner("ghost:u1");
    const o2 = art.uniqueOwner("ghost:u1");
    expect(o1).not.toBe(o2);
    art.holdFor(o1, t1);
    art.holdFor(o2, t2);
    art.holdFor(o1, null); // 第一個殘影播完
    expect(art.isHeld(t2)).toBe(true);
  });
});

describe("creature pose offsets are not part of the texture key (6R-F)", () => {
  it("split keeps stretch, tilt, alpha and flash; dx/dy come out separately", () => {
    const s = splitCreatureOffset({ dx: -6, dy: 2, sx: 0.94, sy: 1.06, rot: -0.22, flash: 0.5, alpha: 0.9 });
    expect(s.pose).toEqual({ sx: 0.94, sy: 1.06, rot: -0.22, flash: 0.5, alpha: 0.9 });
    expect(s.dx).toBe(-6);
    expect(s.dy).toBe(2);
    expect(splitCreatureOffset({ sx: 1.1 })).toEqual({ pose: { sx: 1.1 }, dx: 0, dy: 0 });
  });
});
