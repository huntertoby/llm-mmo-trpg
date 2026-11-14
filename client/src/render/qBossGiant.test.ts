// GB-4b：3×3 巨型灰燼之心的畫法（`qBossGiant.ts`，照樣張 docs/art/sample/qBossGiant.js；移植需求 docs/art/GB巨型頭目-移植需求.md）。
// vitest 沒有 Canvas：這裡只測純函式與表（狀態 → 畫法參數、破壞演出每格、「破」字位置、800 判斷、戰場接點）；實際像素在開發頁
// `client/dev/gb4b-giant.html` 拍（docs/art/shots/GB-4b/）。
import { describe, expect, it } from "vitest";
import { PLATES } from "./qBoss";
import {
  BRK,
  GG,
  GIANT_ANCHOR_DY,
  GIANT_BOUNDS,
  GIANT_BOX,
  GIANT_CANVAS,
  GIANT_FEET_TO_ANCHOR,
  GIANT_PART_OF,
  GIANT_PLATES,
  giantLookKey,
  giantLookOf,
  giantPlateAnchor,
  giantStateFor,
  giantStateOf,
  marksCompact,
  plateFree,
  popAt,
  REASON,
} from "./qBossGiant";
import { FEET } from "./unitSprite";
import { readFile, SRC_DIR } from "../test/sourceScan";

describe("殼片與色票（照抄 1 格灰燼之心）", () => {
  it("殼片名稱和 `qBoss.PLATES` 同一組、同順序（雜湊相位一樣）", () => {
    expect(GIANT_PLATES.map((p) => p[0])).toEqual(PLATES.map((p) => p[0]));
  });

  it("熔殼脫落：往北飛、後 40% 淡出、breakT ≥ 1 不畫；飛出佔格的殼片算「離開佔格」", () => {
    for (const p of GIANT_PLATES) {
      expect(giantPlateAnchor(p, 0, 1, 0)).toBeNull();
      const end = giantPlateAnchor(p, 0, 0.95, 0)!;
      expect(end.y).toBeLessThan(-144);
      expect(end.a).toBeLessThan(0.2);
      expect(plateFree(end)).toBe(true);
      const on = giantPlateAnchor(p, 1, 0, 0.5)!;
      expect(on.a).toBe(1);
      expect(plateFree(on)).toBe(false);
    }
  });
});

describe("giantStateOf（狀態 → 畫法參數）", () => {
  it("中性值：第 1 階段熔殼在、沒有演出、沒有破", () => {
    const S = giantStateOf();
    expect(S.phase).toBe(1);
    expect(S.shell).toBe(1);
    expect(S.bt).toBe(0);
    expect([S.inhale, S.spout, S.die, S.charge, S.seamCool, S.coreDull, S.crack]).toEqual([0, 0, 0, 0, 0, 0, 0]);
    expect([S.coreScale, S.coreLight]).toEqual([1, 1]);
    expect(S.fx).toBeNull();
    expect(S.ventSealed).toBe(false);
    expect(S.coreBroken).toBe(false);
  });

  it("第 2 階段起熔殼預設不在（脫落完）；第 3 階段才有白熱裂紋", () => {
    expect(giantStateOf({ phase: 2 })).toMatchObject({ phase: 2, shell: 0, bt: 1, crack: 0 });
    expect(giantStateOf({ phase: 3 }).crack).toBeGreaterThan(0);
  });

  it("破壞演出每一格照 BRK（第 5 格＝定稿）", () => {
    for (let k = 0; k <= 4; k++) {
      const core = giantStateOf({ phase: 2, fx: { part: "core", k } });
      expect([core.coreScale, core.coreDull, core.coreLight, core.charge, core.inhale]).toEqual([BRK.coreScale[k], BRK.coreDull[k], BRK.coreLight[k], BRK.charge[k], BRK.inhale[k]]);
      expect(core.coreBroken).toBe(k >= 3);
      const seam = giantStateOf({ phase: 2, fx: { part: "seam", k, side: -1 } });
      expect(seam.seamCool).toBe(BRK.seamCool[k]);
      expect(seam.fx).toEqual({ part: "seam", k, side: -1 });
      const vent = giantStateOf({ phase: 2, fx: { part: "vent", k } });
      expect(vent.ventSealed).toBe(k >= 2);
      expect(vent.ventFlare).toBe(k === 1);
      expect(vent.crackPart).toBe(k === 1 ? "vent" : null);
    }
    expect(BRK.ms).toEqual([80, 80, 160, 160, 0]);
    expect(BRK.breakT).toEqual([0, 0, 0.35, 0.72, 1]);
  });

  it("破了的部位（沒有演出）照定稿畫", () => {
    const S = giantStateOf({ phase: 2, broken: { vent: true, seam: true, core: true } });
    expect(S.ventSealed).toBe(true);
    expect(S.seamCool).toBe(1);
    expect(S.coreBroken).toBe(true);
    expect(S.coreScale).toBe(BRK.coreScale[4]);
  });
});

describe("「破」字位置與 800 判斷", () => {
  it("噴口在中間噴口上、殼縫在被打中的那一側、核心在核心上方（模型 px）", () => {
    expect(popAt("vent")).toEqual([0, -140]); // GB-4c：移植需求 5.4（原 −168 蓋頭頂 HUD）
    expect(popAt("seam", -1)).toEqual([-57, -106]);
    expect(popAt("seam", 1)).toEqual([57, -106]);
    expect(popAt("core")).toEqual([0, -114]);
  });

  it("窄畫面＝一格畫面寬 < 40 px（800 寬 0.531 是；1600 寬 1.308 不是）", () => {
    expect(marksCompact(0.531)).toBe(true);
    expect(marksCompact(1.308)).toBe(false);
    expect(marksCompact(40 / 48)).toBe(false);
    expect(marksCompact(39.9 / 48)).toBe(true);
  });

  it("原因短字照玩法 PM 定稿（移植需求第 9 節）", () => {
    expect(REASON.ranged.zh).toBe("要遠程攻擊才打得到");
    expect(REASON.range.zh).toBe("射程不夠");
    expect(REASON.sight.zh).toBe("看不到這一格");
  });
});

describe("戰場接點", () => {
  it("錨點＝中心格中心往南 72；畫布原點是一格單位的腳底（FEET），再往南到錨點", () => {
    expect(GIANT_ANCHOR_DY).toBe(72);
    expect(GIANT_FEET_TO_ANCHOR).toBeCloseTo(GIANT_ANCHOR_DY - FEET, 9);
    // 畫布（虛擬單位）包住整個圖層範圍 GIANT_BOX
    expect(GIANT_CANVAS.foot * GG).toBeGreaterThanOrEqual(GIANT_FEET_TO_ANCHOR - GIANT_BOX[1]);
    expect((GIANT_CANVAS.h - GIANT_CANVAS.foot) * GG).toBeGreaterThanOrEqual(GIANT_BOX[3] + GIANT_FEET_TO_ANCHOR);
    expect((GIANT_CANVAS.w / 2) * GG).toBeGreaterThanOrEqual(GIANT_BOX[2]);
    // 頭頂（含金外光）往上 3.33 格
    expect(-(GIANT_CANVAS.top * GG - GIANT_FEET_TO_ANCHOR) / 48).toBeCloseTo(-GIANT_BOUNDS.y0 / 48, 6);
  });

  it("伺服器的部位 ID → 畫法部位", () => {
    expect(GIANT_PART_OF).toEqual({ vent: "vent", shell_seam: "seam", core: "core" });
  });

  it("giantLookOf：熔殼照 molten_shell、破了的部位、演出中那個部位當成還沒破", () => {
    const parts = [
      { id: "vent", broken: true },
      { id: "shell_seam", broken: true },
      { id: "core", broken: false },
    ];
    expect(giantLookOf({ phase: 1, statusIds: ["molten_shell"], parts })).toEqual({ phase: 1, shell: 1, broken: { vent: true, seam: true }, fx: null });
    const mid = giantLookOf({ phase: 2, parts, partFx: { part: "vent", frame: 1, side: 1 } });
    expect(mid.broken).toEqual({ seam: true });
    expect(mid.fx).toEqual({ part: "vent", k: 1, side: 1 });
    // 霧鎖真人式的 PartFx（沒有 frame）不算巨型演出
    expect(giantLookOf({ phase: 2, parts, partFx: { part: "vent" } }).fx).toBeNull();
  });

  it("第 1 階段殼縫破（熔殼掉落）：前兩格蓋回熔殼，第 3、4 格照 BRK.breakT 飛走", () => {
    const parts = [{ id: "shell_seam", broken: true }];
    const at = (frame: number) => giantLookOf({ phase: 1, statusIds: [], parts, partFx: { part: "shell_seam", frame, side: -1, shed: true } });
    expect(at(0)).toMatchObject({ shell: 1, fx: { part: "seam", k: 0, side: -1 } });
    expect(at(1).shell).toBe(1);
    expect(at(2)).toMatchObject({ shell: 0, breakT: 0.35 });
    expect(at(3)).toMatchObject({ shell: 0, breakT: 0.72 });
    expect(at(0).broken).toEqual({});
    // 第 2 階段（熔殼本來就不在）沒有殼片
    expect(giantLookOf({ phase: 2, parts, partFx: { part: "shell_seam", frame: 2, side: 1, shed: false } })).toMatchObject({ shell: 0 });
    expect("breakT" in giantLookOf({ phase: 2, parts, partFx: { part: "shell_seam", frame: 2, side: 1, shed: false } })).toBe(false);
  });

  it("外觀鍵：不同外觀不同鍵", () => {
    const keys = new Set<string>();
    for (const phase of [1, 2, 3] as const)
      for (const shell of [0, 1] as const)
        for (const p of [null, "vent", "seam", "core"] as const) keys.add(giantLookKey({ phase, shell, broken: p === null ? {} : { [p]: true }, fx: null }));
    expect(keys.size).toBe(24);
    for (let k = 0; k < 4; k++) keys.add(giantLookKey({ phase: 2, shell: 0, broken: {}, fx: { part: "core", k, side: 1 } }));
    expect(keys.size).toBe(28);
  });

  it("片段 → 狀態：沿用 qBoss 灰燼之心的時間軸，只取參數、不位移", () => {
    const look = giantLookOf({ phase: 2, statusIds: [] });
    expect(giantStateFor(look, null).st.t).toBe(1200);
    const idle = giantStateFor(look, { clip: "idle", u: 0.5 });
    expect(idle.st.loop).toBe(0.5);
    const spout = giantStateFor(look, { clip: "atk:@area", u: 0.6 });
    expect(spout.st.spout).toBeGreaterThan(0.5);
    expect(spout.st.phase).toBe(2); // 不像 1 格版強制回第 1 階段
    const bolt = giantStateFor(look, { clip: "atk:@cast", u: 0.3 });
    expect(bolt.st.charge).toBeGreaterThan(0);
    expect(giantStateFor(look, { clip: "hit", u: 0 }).flash).toBeCloseTo(0.9, 6);
    expect(giantStateFor(look, { clip: "death", u: 1 }).st.dieT).toBe(1);
    // 第 1 階段近戰（1 格版是衝撞 ram）：3×3 只取時間，沒有 dx、rot
    const ram = giantStateFor(giantLookOf({ phase: 1, statusIds: ["molten_shell"] }), { clip: "atk:@melee", u: 0.55 });
    expect(Object.keys(ram.st).sort()).toEqual(["broken", "fx", "phase", "shell", "t"]);
  });

  it("沒有 Math.random（確定性；殼片、火星、黑煙照名稱雜湊）", () => {
    const src = readFile(SRC_DIR, "render/qBossGiant.ts");
    expect(/Math\.random\s*\(/.test(src)).toBe(false); // 檔頭註解提到「沒有 Math.random」不算
  });
});
