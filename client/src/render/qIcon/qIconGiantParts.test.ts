// GB-4b：灰燼之心 3×3 的部位小圖與本體圖示（docs/art/GB巨型頭目-移植需求.md 4）。
// vitest 沒有 Canvas：用假畫布（`test/fakeCanvas.ts`）看呼叫；實際像素（真 1 倍四態、本體縮圖）在開發頁 `client/dev/gb4b-icons.html` 拍。
import { afterEach, describe, expect, it } from "vitest";
import { fakeCanvasFactory, type FakeCanvasLog } from "../../test/fakeCanvas";
import { setQCanvasFactory } from "./core";
import { BROKEN_X, bossBodyKind, bossPartDef, bossPartIcon, bossPartIconKey, bossPartStateIcon, clearBossPartIcons, type BossDoll } from "./bossParts";
import { GIANT_BODY, GIANT_BOSS_TEMPLATE, GIANT_PART_GLYPH, GIANT_PART_IDS, liftDarkPixels } from "./giantParts";

const ASH_DOLL: BossDoll = { template: GIANT_BOSS_TEMPLATE, dollLook: null, weaponId: null };
const MIST_DOLL: BossDoll = { template: "sect_mist_lock_master", dollLook: null, weaponId: "one_handed_sword" };

afterEach(() => {
  setQCanvasFactory(null);
  clearBossPartIcons();
});

/** 用假畫布畫一次，回傳所有呼叫。 */
function draw(fn: () => unknown): string[] {
  const log: FakeCanvasLog = { calls: [] };
  setQCanvasFactory(fakeCanvasFactory(log));
  clearBossPartIcons();
  fn();
  return log.calls ?? [];
}

describe("清單與 ID 對照", () => {
  it("伺服器部位 ID（content/units/ashen_heart.yaml）→ 熔岩噴口、殼縫、核心", () => {
    expect(GIANT_PART_IDS).toEqual(["core", "shell_seam", "vent"]);
    expect(Object.fromEntries(Object.entries(GIANT_PART_GLYPH).map(([id, g]) => [id, g.zh]))).toEqual({ vent: "熔岩噴口", shell_seam: "殼縫", core: "核心" });
  });

  it("只有核心有外框底下的光暈（pre）", () => {
    expect(bossPartDef("core").pre).toBeDefined();
    expect(bossPartDef("vent").pre).toBeUndefined();
    expect(bossPartDef("shell_seam").pre).toBeUndefined();
    expect(bossPartDef("whisk").pre).toBeUndefined(); // 霧鎖真人不變
  });

  it("三個部位與本體都畫得出來：畫布＝顯示 × 解析度", () => {
    setQCanvasFactory(fakeCanvasFactory({ calls: null }));
    for (const id of GIANT_PART_IDS) expect(bossPartIcon(id, 20, 2)!.width, id).toBe(40);
    expect(bossPartIcon("body", 20, 1, ASH_DOLL)!.width).toBe(20);
  });

  it("三個部位用玄武岩換亮一階的本色 #7c6c62，不是米白人形（未知部位才退回）", () => {
    for (const id of GIANT_PART_IDS) {
      const calls = draw(() => bossPartIcon(id, 20, 2));
      expect(calls, id).toContain("fillStyle=#7c6c62");
      expect(calls, id).not.toContain("fillStyle=#f2e6c8");
    }
  });
});

describe("本體列（需求 4.2）", () => {
  it("範本是灰燼之心時用整隻縮圖；霧鎖真人仍是頭像；沒有外觀時米白人形", () => {
    expect(bossBodyKind(ASH_DOLL)).toBe("giant");
    expect(bossBodyKind({ ...ASH_DOLL, dollLook: { any: 1 } as unknown as BossDoll["dollLook"] })).toBe("giant");
    expect(bossBodyKind(MIST_DOLL)).toBe("portrait");
    expect(bossBodyKind(null)).toBe("placeholder");
  });

  it("灰燼之心本體不畫霧鎖真人的米白人形（沒有 DOM 時退回玄武岩剪影）", () => {
    const giant = draw(() => bossPartIcon("body", 20, 2, ASH_DOLL));
    expect(giant).toContain("fillStyle=#7c6c62");
    expect(giant).not.toContain("fillStyle=#f2e6c8");
    const placeholder = draw(() => bossPartIcon("body", 20, 2, null));
    expect(placeholder).toContain("fillStyle=#f2e6c8");
  });

  it("取第 2 階段・熔殼不在；裁切框、圖樣寬照樣張", () => {
    expect(GIANT_BODY.st).toMatchObject({ phase: 2, shell: 0 });
    expect(GIANT_BODY.box).toEqual([-78, -159, 156, 160]);
    expect(GIANT_BODY.span).toBe(22.6);
    expect(GIANT_BODY.eyes).toHaveLength(3);
  });

  it("暗色像素換亮一階：亮度 < 120 的不透明像素 ×1.25＋6，亮的、透明的不動", () => {
    const d = new Uint8ClampedArray([74, 59, 54, 255, 255, 106, 26, 255, 10, 10, 10, 0, 220, 220, 220, 255]);
    liftDarkPixels(d);
    expect(Array.from(d.slice(0, 4))).toEqual([99, 80, 74, 255]); // 玄武岩 #4a3b36
    expect(Array.from(d.slice(4, 8))).toEqual([255, 106, 26, 255]); // 熔岩亮度 > 120
    expect(Array.from(d.slice(8, 12))).toEqual([10, 10, 10, 0]); // 透明
    expect(Array.from(d.slice(12, 16))).toEqual([220, 220, 220, 255]);
  });
});

describe("四態（同霧鎖真人 `grayIcon`、紅×）", () => {
  const states = [
    ["一般", true, false],
    ["打不到／未露出", false, false],
    ["已破壞", false, true],
  ] as const;

  for (const id of ["vent", "shell_seam", "core", "whisk"]) {
    it(`${id}：一般不灰、打不到灰化（去色＋亮度 0.8＋透明度 0.45）、已破壞灰化＋紅×`, () => {
      for (const [name, ok, broken] of states) {
        let out: HTMLCanvasElement | null = null;
        const calls = draw(() => (out = bossPartStateIcon(id, 20, 2, ok, broken)));
        expect(out!.width, name).toBe(40);
        const gray = calls.includes("filter=grayscale(1) brightness(0.8)") && calls.includes("globalAlpha=0.450");
        expect(gray, `${id} ${name}`).toBe(!ok);
        expect(calls.includes(`strokeStyle=${BROKEN_X}`), `${id} ${name}`).toBe(broken);
      }
    });
  }

  it("紅×：外框色 3.4＋#ff6a5a 1.8，20px 內縮 3", () => {
    const calls = draw(() => bossPartStateIcon("vent", 20, 1, false, true));
    const i = calls.indexOf(`strokeStyle=${BROKEN_X}`);
    expect(calls.slice(i - 12, i)).toContain("strokeStyle=#16121a");
    expect(calls.slice(i, i + 3)).toContain("lineWidth=1.800");
    expect(calls).toContain("moveTo(3.000,3.000)");
    expect(calls).toContain("lineTo(17.000,17.000)");
  });
});

describe("快取鍵", () => {
  it("灰燼之心的部位、本體和霧鎖真人不撞", () => {
    const keys = [
      ...GIANT_PART_IDS.map((id) => bossPartIconKey(id, 20, 2)),
      bossPartIconKey("body", 20, 2, ASH_DOLL),
      ...["whisk", "dantian", "sword", "back"].map((id) => bossPartIconKey(id, 20, 2)),
      bossPartIconKey("body", 20, 2, MIST_DOLL),
      bossPartIconKey("body", 20, 2),
    ];
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("灰燼之心本體只有一種圖：外觀資料不同也同一個鍵", () => {
    expect(bossPartIconKey("body", 20, 2, ASH_DOLL)).toBe(bossPartIconKey("body", 20, 2, { ...ASH_DOLL, weaponId: "x" }));
  });

  it("霧鎖真人的鍵不變（PB-1c 格式）", () => {
    expect(bossPartIconKey("whisk", 20, 2)).toBe("whisk|20|2|");
    expect(bossPartIconKey("body", 20, 2, MIST_DOLL)).toBe(`body|20|2|${JSON.stringify(MIST_DOLL)}`);
  });
});
