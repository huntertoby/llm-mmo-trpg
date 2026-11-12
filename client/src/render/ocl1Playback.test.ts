// OCL-1b：被遮擋外框的播放（`docs/phases/PhaseOCL-1計畫.md`「行為一致測試」第 11、12 項；PM 裁定 1a 待決 1）。
// 繪製器層用 `OcclusionLayer` 的子類別：單位節點真的放進 `rows`（重算走正式的 `occlusionUnits(model, live)`），身體換成合成的 alpha。
import { Container, Sprite, Texture } from "pixi.js";
import { describe, expect, it } from "vitest";
import type { DrawModel, UnitDraw } from "../battle/drawModel";
import { RING } from "./artPalette";
import { CREATURE_CLIPS, CREATURE_HIT_FLASH } from "./creaturePose";
import { HUMAN_HIT_FLASH, humanHit } from "./motionClips";
import { flashAlpha, flashTint, OUTLINE_ALPHA, outlineFlashK, type AlphaImage } from "./occludeOutline";
import { BLOCK_FLASH, creatureReact, creatureReactFlashPeak, HEAVY_HIT_FLASH, reactFlashPeak, reactFrame, REACT_CLIPS, type ReactClip } from "./reactClips";
import { reactEffects, type ReactHost } from "./reactEffects";
import { ArtTextures } from "./artTextures";
import { canBeBig, planOcclusion, type OclSource, type OclUnit } from "./battle/outlineLayer";
import { OcclusionLayer, OUTLINE_MAX_ROTATION } from "./battle/occlusionLayer";
import { REDUCED_FLASH_PEAK } from "./battle/vfxLayer";
import { DUMMY_FLASH_ALPHA } from "./trainingDummy";
import { bareBodyOf, BODY_LABEL, DOLL_MAX_FILL, FEET, type BareBody } from "./unitSprite";
import { UNIT_DOLLS } from "./testDolls";
import { readFile, SRC_DIR, stripTsComments } from "../test/sourceScan";

// ---- 合成的身體（同 ocl1Outline.test.ts）----
function image(w: number, h: number, fill: (x: number, y: number) => boolean): AlphaImage {
  const alpha = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (fill(x, y)) alpha[y * w + x] = 255;
  return { w, h, alpha };
}
const rect = (w: number, h: number): AlphaImage => image(w, h, () => true);
const synth = (key: string, img: AlphaImage): BareBody => ({ key, box: { w: img.w, h: img.h, foot: img.h }, k: 1, display: 1, draw: () => null });
const draw = (id: string, x: number, y: number, over: Partial<UnitDraw> = {}): UnitDraw =>
  ({ id, x, y, template: "t", name: "n", marker: "A", team: "ally", summon: false, downed: false, statusIds: [], facing: "south", ...over }) as unknown as UnitDraw;

/** 繪製器：單位節點放進 `rows`，身體節點在 (0, FEET)；`occlusionUnits` 走正式的程式，只把身體換成合成的。 */
class PlayLayer extends OcclusionLayer {
  readonly imgs = new Map<string, AlphaImage>();
  readonly draws = new Map<string, UnitDraw>();
  calls: string[] = [];
  constructor() {
    super();
    this.rows.reset(8);
    (this.art as unknown as { outline: () => Texture }).outline = () => Texture.WHITE;
    const imgOf = (b: BareBody) => this.imgs.get(b.key.slice(2)) ?? null;
    (this as unknown as { oclSource: OclSource }).oclSource = {
      maskImage: (b) => {
        this.calls.push(`mask:${b.key}`);
        return imgOf(b);
      },
      texImage: (b) => {
        this.calls.push(`tex:${b.key}`);
        const img = imgOf(b);
        return img === null ? null : { key: b.key, img };
      },
    };
  }
  protected override occlusionUnits(model: DrawModel, live = false): OclUnit[] {
    return super.occlusionUnits(model, live).map((e) => ({ ...e, body: synth(`k:${e.id}`, this.imgs.get(e.id)!) }));
  }
  protected override terrainOccluded(): boolean {
    return false;
  }
  /** 單位 `id` 站在格 (x, y)，單位節點再往上 `lift` 模型像素。 */
  add(id: string, img: AlphaImage, x: number, y: number, lift = 0, over: Partial<UnitDraw> = {}): Container {
    const u = draw(id, x, y, over);
    this.imgs.set(id, img);
    this.draws.set(id, u);
    const c = new Container();
    const body = new Sprite(Texture.WHITE);
    body.label = BODY_LABEL;
    body.position.set(0, FEET);
    c.addChild(body);
    c.position.set(x * 48 + 24, y * 48 + 24 - lift);
    this.rows.row(y).units.addChild(c);
    this.unitSprites.set(id, c);
    this.unitDrawOf.set(id, u);
    return c;
  }
  drawNow(): void {
    this.drawOcclusion({ units: [...this.draws.values()], height: 8 } as unknown as DrawModel);
  }
  sprite(id: string): Container {
    return this.unitSprites.get(id)!;
  }
  body(id: string): Sprite {
    return this.sprite(id).children[0] as Sprite;
  }
  outline(id: string): Sprite | undefined {
    return this.outlineOf.get(id);
  }
  ratio(id: string): number {
    return this.occlusionStats().entries.find((e) => e.id === id)?.ratio ?? 0;
  }
  // 播放的掛鉤（正式由 motionLayer、skillLayer、vfxLayer 呼叫）
  move(id: string, on: boolean): void {
    if (on) this.beginMove(id);
    else this.endMove(id);
  }
  rowEnd(): void {
    this.refreshOcclusion();
  }
  tick(): void {
    this.tickOutlines();
  }
  flash(id: string, f: number, peak: number): void {
    this.flashOutline(id, f, peak);
  }
  hide(id: string): void {
    this.hideOutline(id);
  }
}

/** 被擋者 b 60×60 在 (2, 1)、大型前排 f 100×60 在 (2, 2) 往上 30（前排上緣到被擋者下緣 42 列 ＝ 擋 70%）。 */
function scene(): PlayLayer {
  const r = new PlayLayer();
  r.add("b", rect(60, 60), 2, 1);
  r.add("f", rect(100, 60), 2, 2, 30);
  r.drawNow();
  return r;
}

describe("OCL-1b 第 12 項：片段中沿用、片段結束重算", () => {
  it("draw 之後 b 有外框（70%）", () => {
    const r = scene();
    expect(r.ratio("b")).toBeCloseTo(0.7, 3);
    expect(r.outline("b")).toBeDefined();
  });

  it("出招片段中頭目前推（身體節點位移）：片段結束重算時擺位沒變 → 同一個 Sprite、同一張貼圖、比例不變、不算重算", () => {
    const r = scene();
    const s = r.outline("b")!;
    const tex = s.texture;
    r.body("f").position.set(0, FEET - 30); // 頭目往北前推 30（片段的位移）
    r.calls = [];
    r.rowEnd(); // 某一列結束時重算：擺位用「站好」的身體位置
    expect(r.outline("b")).toBe(s);
    expect(r.outline("b")!.texture).toBe(tex);
    expect(r.ratio("b")).toBeCloseTo(0.7, 3);
    expect(r.occlusionStats().refreshes).toBe(0);
    expect(r.calls).toEqual([]); // 沒有重算任何遮罩
  });

  it("前排移動中（走開）：別人的外框沿用移動前的結果；移動中的重算延後；移動結束重算一次（不再被擋 → 拿掉）", () => {
    const r = scene();
    const s = r.outline("b")!;
    r.move("f", true);
    r.sprite("f").position.set(7 * 48 + 24, 2 * 48 + 24); // 走到很遠的地方
    r.rowEnd(); // 移動中：不重算
    r.tick();
    expect(r.outline("b")).toBe(s);
    expect(s.visible).toBe(true);
    expect(r.ratio("b")).toBeCloseTo(0.7, 3);
    expect(r.occlusionStats().refreshes).toBe(0);
    r.move("f", false); // 移動結束
    expect(r.occlusionStats().refreshes).toBe(1);
    expect(r.outline("b")).toBeUndefined();
    expect(s.destroyed).toBe(true);
  });

  it("前排走過來（移動結束）才畫；移動中不畫", () => {
    const r = new PlayLayer();
    r.add("b", rect(60, 60), 2, 1);
    r.add("f", rect(100, 60), 6, 2, 30);
    r.drawNow();
    expect(r.outline("b")).toBeUndefined();
    r.move("f", true);
    r.sprite("f").position.set(2 * 48 + 24, 2 * 48 + 24 - 30);
    r.rowEnd();
    expect(r.outline("b")).toBeUndefined();
    r.move("f", false);
    expect(r.outline("b")).toBeDefined();
  });

  it("移動者自己的外框 visible ＝ false（每格的對齊也不會再打開），停下重算後才回來", () => {
    const r = scene();
    r.move("b", true);
    expect(r.outline("b")!.visible).toBe(false);
    r.tick();
    expect(r.outline("b")!.visible).toBe(false);
    r.move("b", false); // 停在原地：重算後照畫
    r.tick();
    expect(r.outline("b")!.visible).toBe(true);
  });
});

describe("OCL-1b 第 2 點（Q4）：外框跟著身體節點平移、旋轉時藏起來", () => {
  it("受擊往後彈（身體節點位移）：外框跟著同一個位移、貼圖不換", () => {
    const r = scene();
    const s = r.outline("b")!;
    const tex = s.texture;
    const c = r.sprite("b");
    r.body("b").position.set(4, FEET - 3);
    r.tick();
    expect(s.position.x).toBe(c.x + 4);
    expect(s.position.y).toBe(c.y + FEET - 3);
    expect(s.texture).toBe(tex);
    r.body("b").position.set(0, FEET);
    r.tick();
    expect(s.position.x).toBe(c.x);
    expect(s.position.y).toBe(c.y + FEET);
  });
  it("轉身重建小人節點（換成新節點）：照單位 ID 找到新的節點", () => {
    const r = scene();
    const old = r.sprite("b");
    const fresh = new Container();
    const body = new Sprite(Texture.WHITE);
    body.label = BODY_LABEL;
    body.position.set(2, FEET);
    fresh.addChild(body);
    fresh.position.copyFrom(old.position);
    old.parent!.addChild(fresh);
    (r as unknown as { unitSprites: Map<string, Container> }).unitSprites.set("b", fresh);
    r.tick();
    expect(r.outline("b")!.position.x).toBe(old.x + 2);
  });
  it("OCL-1c：身體轉 10°（受擊側彎）外框看得到、跟著轉；轉 0.5 rad（空翻、倒下）藏；轉回 0 再出現", () => {
    const r = scene();
    const ten = (10 * Math.PI) / 180; // 0.1745
    r.body("b").rotation = ten;
    r.tick();
    expect(r.outline("b")!.visible).toBe(true);
    expect(r.outline("b")!.rotation).toBeCloseTo(ten, 9);
    r.body("b").rotation = -ten;
    r.tick();
    expect(r.outline("b")!.visible).toBe(true);
    expect(r.outline("b")!.rotation).toBeCloseTo(-ten, 9);
    expect(OUTLINE_MAX_ROTATION).toBe(0.35);
    r.body("b").rotation = 0.5;
    r.tick();
    expect(r.outline("b")!.visible).toBe(false);
    r.body("b").rotation = 0;
    r.tick();
    expect(r.outline("b")!.visible).toBe(true);
    expect(r.outline("b")!.rotation).toBe(0);
  });
  it("倒下片段（hideOutline）：藏起來，直到下次 draw", () => {
    const r = scene();
    r.hide("b");
    r.tick();
    expect(r.outline("b")!.visible).toBe(false);
    r.drawNow();
    r.tick();
    expect(r.outline("b")!.visible).toBe(true);
  });
});

// ---- 第 11 項：閃白 k ----
const sample = (f: (t: number) => number): number => {
  let m = 0;
  for (let i = 0; i <= 2000; i++) m = Math.max(m, f(i / 2000));
  return m;
};
/**
 * 每一種白閃：片段裡最大的白閃、呼叫點傳給外框的峰值、兩者容許的差（預設 1e-6 只容浮點誤差）。
 * OCL-1c：異形重擊的峰值照實際片段（0.9 × 1.1 經 `quantizeCreaturePose` 量化後 1.0），和最大的白閃完全相等（容許 0）。
 */
const ROWS: ReadonlyArray<readonly [string, number, number, number?]> = [
  ["人形受擊（dollHit、疊層 overlayHit）", sample((t) => humanHit(t).flash), HUMAN_HIT_FLASH],
  ...(["hit", "heavy", "block", "down", "trapped"] as const).flatMap((clip) =>
    [0, 1, 2].map((variant) => [`人形反應 ${clip}（變體 ${variant}）`, sample((t) => reactFrame(clip, t, { side: 1, guard: "arm", variant }).flash), reactFlashPeak(clip)] as const),
  ),
  ["異形、頭目受擊（creatureHit）", sample((t) => CREATURE_CLIPS.hit.pose(t).flash ?? 0), CREATURE_HIT_FLASH],
  ["異形反應 hit", sample((t) => creatureReact("hit", t).flash ?? 0), creatureReactFlashPeak("hit")],
  ["異形反應 heavy", sample((t) => creatureReact("heavy", t).flash ?? 0), creatureReactFlashPeak("heavy"), 0],
  ["異形反應 trapped", sample((t) => creatureReact("trapped", t).flash ?? 0), creatureReactFlashPeak("trapped")],
  ["減少動態（steadyFlashAt）", REDUCED_FLASH_PEAK * (1 - 0), REDUCED_FLASH_PEAK],
  ["木樁（dummyFlashEffect）", DUMMY_FLASH_ALPHA, DUMMY_FLASH_ALPHA],
  ["疊層格擋（overlayEffect × 0.4）", sample((t) => reactFrame("hit", t).flash * 0.4), HUMAN_HIT_FLASH * 0.4],
];

describe("OCL-1b 第 11 項：閃白 k ＝ 當下白閃 ÷ 這個效果自己的峰值（Q6）", () => {
  for (const [name, max, peak, tol = 1e-6] of ROWS) {
    it(`${name}：峰值 ${peak.toFixed(3)}＝片段裡最大的白閃；白閃＝峰值時 k＝1、tint 白、alpha 1；白閃 0 時原色 0.8`, () => {
      expect(Math.abs(max - peak)).toBeLessThanOrEqual(tol);
      expect(outlineFlashK(max, peak)).toBeCloseTo(1, 6);
      expect(flashTint(RING.enemy.stroke, outlineFlashK(peak, peak))).toBe(0xffffff);
      expect(flashAlpha(outlineFlashK(peak, peak))).toBe(1);
      expect(outlineFlashK(0, peak)).toBe(0);
      expect(flashTint(RING.enemy.stroke, 0)).toBe(RING.enemy.stroke);
      expect(flashAlpha(0)).toBe(OUTLINE_ALPHA);
    });
  }
  it("峰值表：0.85、0.95、0.9、1.0（異形重擊，OCL-1c 照實際）、0.35、減少動態 0.85；閃避、異形格擋沒有白閃（0）", () => {
    expect(HUMAN_HIT_FLASH).toBe(0.85);
    expect(HEAVY_HIT_FLASH).toBe(0.95);
    expect(CREATURE_HIT_FLASH).toBe(0.9);
    expect(creatureReactFlashPeak("heavy")).toBe(1);
    expect(BLOCK_FLASH).toBe(0.35);
    expect(REDUCED_FLASH_PEAK).toBe(0.85);
    expect(reactFlashPeak("dodge")).toBe(0);
    expect(sample((t) => reactFrame("dodge", t, { side: 1, guard: "arm", variant: 0 }).flash)).toBe(0);
    for (const clip of ["dodge", "block"] as const) expect(sample((t) => creatureReact(clip, t).flash ?? 0)).toBe(0);
  });
  it("k 不寫死 0.85：異形、頭目的分母不是 0.85（白閃 0.45 → k 0.5，不是 0.53）", () => {
    for (const clip of REACT_CLIPS as readonly ReactClip[]) expect(creatureReactFlashPeak(clip)).not.toBe(0.85);
    expect(outlineFlashK(0.45, CREATURE_HIT_FLASH)).toBeCloseTo(0.5, 9);
    expect(outlineFlashK(0.175, BLOCK_FLASH)).toBeCloseTo(0.5, 9); // 格擋很淡，k 照樣到 1
    expect(outlineFlashK(1, 0.35)).toBe(1); // 夾在 1
    expect(outlineFlashK(0.5, 0)).toBe(0);
  });
  it("原始碼：每個交給外框的白閃都傳峰值常數或峰值函式，沒有寫死的數字（只有結束時的 0, 1）", () => {
    const calls: string[] = [];
    for (const f of ["render/battle/vfxLayer.ts", "render/battle/skillLayer.ts", "render/reactEffects.ts"]) {
      const src = stripTsComments(readFile(SRC_DIR, f));
      for (const m of src.matchAll(/(?:flashOutline|outline\?\.flash)\(([^;]*?)\);/g)) calls.push(`${f}: ${m[1]}`);
    }
    expect(calls.length).toBeGreaterThanOrEqual(14);
    for (const c of calls) expect(c, c).not.toMatch(/\b0\.\d+/);
    // 異形與頭目的受擊（creatureHit）用異形的峰值
    const vfx = stripTsComments(readFile(SRC_DIR, "render/battle/vfxLayer.ts"));
    const creature = vfx.slice(vfx.indexOf("private creatureHit("), vfx.indexOf("private dollAt("));
    expect(creature).toContain("CREATURE_HIT_FLASH");
    expect(creature).not.toContain("HUMAN_HIT_FLASH");
  });
});

describe("OCL-1b 第 4 點：外框層只動 tint／alpha，不換貼圖；白閃結束回原色", () => {
  it("繪製器：k＝1 → 白、alpha 1；k＝0.5 → mix、0.9；結束 → 陣營色、0.8；貼圖一直是同一張", () => {
    const r = scene();
    const s = r.outline("b")!;
    const tex = s.texture;
    r.flash("b", CREATURE_HIT_FLASH, CREATURE_HIT_FLASH);
    expect(s.tint).toBe(0xffffff);
    expect(s.alpha).toBe(1);
    r.flash("b", 0.425, HUMAN_HIT_FLASH);
    expect(s.tint).toBe(flashTint(RING.ally.stroke, 0.5));
    expect(s.alpha).toBeCloseTo(0.9, 9);
    r.flash("b", 0, 1);
    expect(s.tint).toBe(RING.ally.stroke);
    expect(s.alpha).toBe(OUTLINE_ALPHA);
    expect(s.texture).toBe(tex);
  });
  it("閃白中重畫（命中時換成步後畫面）：新外框接著同一個 k", () => {
    const r = scene();
    r.flash("b", 0.9, 0.9);
    r.drawNow();
    expect(r.outline("b")!.tint).toBe(0xffffff);
    r.flash("b", 0, 1);
    expect(r.outline("b")!.tint).toBe(RING.ally.stroke);
  });
});

describe("OCL-1b：受擊反應把（白閃, 峰值）交給外框（reactEffects）", () => {
  const LIZARD = draw("liz", 2, 1, { dollLook: UNIT_DOLLS.ember_lizard, template: "ember_lizard", team: "enemy" } as Partial<UnitDraw>);
  const DOLL = draw("man", 2, 1, { team: "enemy" });
  function host(u: UnitDraw): ReactHost & { log: Array<[string, number, number] | ["hide"]> } {
    const c = new Container();
    const body = new Sprite(Texture.WHITE);
    body.label = BODY_LABEL;
    c.addChild(body);
    const log: Array<[string, number, number] | ["hide"]> = [];
    return {
      art: new ArtTextures(),
      sprite: () => c,
      draw: () => u,
      hold: () => undefined,
      release: () => undefined,
      setTexture: (_id, node, tex) => {
        node.texture = tex;
      },
      restBody: () => undefined,
      outline: { flash: (id, f, p) => log.push([id, f, p]), hide: () => log.push(["hide"]) },
      log,
    };
  }
  const run = (u: UnitDraw, kind: "hit" | "heavy" | "block" | "dodge" | "down") => {
    const h = host(u);
    const effects = reactEffects(h, { unitId: u.id, pos: { x: 2, y: 1 }, kind, atMs: 0, seq: 1, cast: 0 }, 0, 1);
    for (const e of effects) {
      for (let i = 0; i <= 20; i++) e.update(i / 20);
      e.end?.();
    }
    return h.log;
  };
  it("異形受擊：峰值 0.9、重擊 1.0（OCL-1c）；最大的白閃 ÷ 峰值 ＝ 1；結束送 0", () => {
    for (const [kind, peak] of [["hit", 0.9], ["heavy", 1]] as const) {
      const log = run(LIZARD, kind).filter((x): x is [string, number, number] => x.length === 3);
      expect(new Set(log.slice(0, -1).map((x) => x[2].toFixed(4)))).toEqual(new Set([peak.toFixed(4)]));
      expect(Math.max(...log.map((x) => outlineFlashK(x[1], x[2])))).toBeCloseTo(1, 6);
      expect(log.at(-1)).toEqual(["liz", 0, 1]);
    }
  });
  it("人形受擊 0.85、重擊 0.95、格擋 0.35", () => {
    for (const [kind, peak] of [["hit", 0.85], ["heavy", 0.95], ["block", 0.35]] as const) {
      const log = run(DOLL, kind).filter((x): x is [string, number, number] => x.length === 3);
      expect(new Set(log.slice(0, -1).map((x) => x[2]))).toEqual(new Set([peak]));
      expect(Math.max(...log.map((x) => x[1] / x[2]))).toBeCloseTo(1, 6);
    }
  });
  it("倒下（人形、異形）：藏外框", () => {
    expect(run(DOLL, "down").some((x) => x[0] === "hide")).toBe(true);
    expect(run(LIZARD, "down").some((x) => x[0] === "hide")).toBe(true);
    expect(run(LIZARD, "down").some((x) => x.length === 3 && x[1] > 0)).toBe(false); // 頭目倒下的白閃不傳
  });
});

describe("OCL-1b：播放的掛鉤接在哪裡（原始碼）", () => {
  it("走路、位移、進出門都 beginMove／endMove；出招前轉向、出招列結束 refreshOcclusion；外框每格對齊在算繪之前", () => {
    const motion = stripTsComments(readFile(SRC_DIR, "render/battle/motionLayer.ts"));
    for (const fn of ["async animate(", "async animateWalk(", "async playLeave(", "async playArrive("]) {
      const at = motion.indexOf(fn);
      const body = motion.slice(at, motion.indexOf("\n  }\n", at));
      expect(body, fn).toContain("this.beginMove(");
      expect(body, fn).toContain("this.endMove(");
    }
    const skill = stripTsComments(readFile(SRC_DIR, "render/battle/skillLayer.ts"));
    expect(skill.slice(skill.indexOf("playSkill("), skill.indexOf("private rowFrame("))).toContain("this.refreshOcclusion()");
    const rowEnd = skill.slice(skill.indexOf("private rowEffect("), skill.indexOf("private placeTurnedFx("));
    expect(rowEnd.slice(rowEnd.indexOf("end: () =>"))).toContain("this.refreshOcclusion()");
    const br = stripTsComments(readFile(SRC_DIR, "render/BattleRenderer.ts"));
    expect(br).toMatch(/this\.tickOutlines\(\)\), this, UPDATE_PRIORITY\.LOW \+ 1\)/);
  });
});

describe("PM 裁定 1a 待決 1：只有附近可能有大型前排時才建遮罩（被擋判定結果不變）", () => {
  const doll = (id: string, x: number, y: number, over: Partial<UnitDraw> = {}): UnitDraw =>
    draw(id, x, y, { template: "bandit", dollLook: UNIT_DOLLS.bandit, team: "enemy", ...over } as Partial<UnitDraw>);
  it("紙娃娃的身體帶 DOLL_MAX_FILL；基本大小與精英都不可能是大型前排，外觀放大 1.5 倍的精英才要畫遮罩判斷", () => {
    expect(DOLL_MAX_FILL).toBe(0.45);
    expect(bareBodyOf(doll("a", 0, 0)).fill).toBe(DOLL_MAX_FILL);
    expect(canBeBig({ body: bareBodyOf(doll("a", 0, 0)) })).toBe(false);
    expect(canBeBig({ body: bareBodyOf(doll("a", 0, 0, { elite: true })) })).toBe(false);
    const huge = doll("a", 0, 0, { elite: true, dollLook: { ...UNIT_DOLLS.bandit!, scale: 1.5 } } as Partial<UnitDraw>);
    expect(canBeBig({ body: bareBodyOf(huge) })).toBe(true);
    // 異形、頭目沒有預篩（畫布本來就 > 4000，照舊畫遮罩算面積）
    expect(bareBodyOf(draw("l", 0, 0, { template: "ember_lizard", dollLook: UNIT_DOLLS.ember_lizard } as Partial<UnitDraw>)).fill).toBeUndefined();
  });
  it("場上沒有大型前排（只有紙娃娃）：drawOcclusion 不取任何遮罩、getImageData 0 次", () => {
    class Real extends OcclusionLayer {
      asks = 0;
      constructor() {
        super();
        this.rows.reset(8);
        const art = this.art as unknown as { alphaMask: (k: string, m: () => HTMLCanvasElement | null) => unknown };
        const orig = art.alphaMask.bind(this.art);
        art.alphaMask = (k, m) => {
          this.asks += 1;
          return orig(k, m);
        };
      }
      put(u: UnitDraw): void {
        const c = new Container();
        const body = new Sprite(Texture.WHITE);
        body.label = BODY_LABEL;
        body.position.set(0, FEET);
        c.addChild(body);
        c.position.set(u.x * 48 + 24, u.y * 48 + 24);
        this.rows.row(u.y).units.addChild(c);
        this.unitSprites.set(u.id, c);
        this.unitDrawOf.set(u.id, u);
      }
      go(units: UnitDraw[]): void {
        for (const u of units) this.put(u);
        this.drawOcclusion({ units, height: 8 } as unknown as DrawModel);
      }
      get reads(): number {
        return this.art.alphaReads;
      }
    }
    const r = new Real();
    // 一排排緊貼著站（每個人南邊 0～3 排都有人、外接矩形都相交）
    r.go([doll("a", 2, 1), doll("b", 2, 2, { elite: true }), doll("c", 3, 2), doll("d", 2, 3), doll("e", 2, 4, { team: "ally" })]);
    expect(r.asks).toBe(0);
    expect(r.reads).toBe(0);
    expect(r.occlusionStats().entries.every((e) => e.skip === "nobig")).toBe(true);
  });
  it("大型前排的像素碰不到被擋者的整張畫布：不畫被擋者的遮罩（結果同「算了、沒相交」）；碰得到才畫", () => {
    const run = (dx: number) => {
      const back: OclUnit = { id: "b", u: draw("b", 2, 1), order: 0, feet: { x: 120, y: 72 + FEET }, body: synth("b", rect(20, 30)) };
      const front: OclUnit = { id: "f", u: draw("f", 2, 2), order: 1, feet: { x: 120 + dx, y: 120 + FEET - 40 }, body: synth("f", image(200, 100, (x) => x >= 150)) };
      const img = new Map([["b", rect(20, 30)], ["f", image(200, 100, (x) => x >= 150)]]);
      const calls: string[] = [];
      const src: OclSource = { maskImage: (b) => (calls.push(b.key), img.get(b.key) ?? null), texImage: (b) => ({ key: b.key, img: img.get(b.key)! }) };
      return { e: planOcclusion([back, front], new Map(), src).get("b")!, calls };
    };
    // 前排畫布 200 寬罩住被擋者，但有像素的只有右邊 50 列（面積 5000；離被擋者畫布 37 px 以上）
    const far = run(0);
    expect(far.e.drawn).toBe(false);
    expect(far.e.skip).toBe("nobig");
    expect(far.calls).toEqual(["f"]);
    const near = run(-60); // 前排往西 60：右邊那 50 列蓋到被擋者
    expect(near.calls).toEqual(["f", "b"]);
    expect(near.e.drawn).toBe(true);
  });
  it("對照：畫布本身 ≥ 4000、沒有 fill 的合成身體照舊畫遮罩判斷（面積 4000 填滿照樣算大型前排）", () => {
    const back: OclUnit = { id: "b", u: draw("b", 2, 1), order: 0, feet: { x: 120, y: 72 + FEET }, body: synth("b", rect(20, 30)) };
    const front: OclUnit = { id: "f", u: draw("f", 2, 2), order: 1, feet: { x: 120, y: 120 + FEET - 40 }, body: synth("f", rect(80, 50)) };
    const img = new Map([["b", rect(20, 30)], ["f", rect(80, 50)]]);
    const calls: string[] = [];
    const src: OclSource = {
      maskImage: (b) => (calls.push(b.key), img.get(b.key) ?? null),
      texImage: (b) => ({ key: b.key, img: img.get(b.key)! }),
    };
    expect(planOcclusion([back, front], new Map(), src).get("b")!.drawn).toBe(true);
    expect(calls).toContain("f");
  });
});
