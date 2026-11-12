// 靶場木樁（PR-2c，#147；畫法照 docs/art/sample/obSamples.js 的 `dummy()`，#134 range.html 已定案）：
// 底座、木樁、橫臂、麻布身、布頭；沒有血條、沒有陣營圈；被打中閃白 0.1 秒。
// 單位範本 `training_dummy`／`training_dummy_moving` 一律這樣畫（測試模式與技能工坊 3F 都換，PR-2 第 8 點）。
// 座標：紙娃娃畫布的虛擬像素（一格 52、腳底為原點，`ArtTextures.dollFx`）；樣張在 52 格的戰場用 0.86 倍畫，這裡照抄。
import type { Ctx } from "./artDraw";
import { ellPts, ink, stroke } from "./inkStyle";
import { whiteSilhouette } from "./creaturePose";

/** 畫成木樁的單位範本（`UnitView.template_id`）。 */
export const TRAINING_DUMMY_TEMPLATES: readonly string[] = ["training_dummy", "training_dummy_moving"];

export function isTrainingDummy(u: { template: string } | undefined | null): boolean {
  return u != null && TRAINING_DUMMY_TEMPLATES.includes(u.template);
}

/** 樣張戰場上木樁的縮放（`boardCanvas` 的 `dummy(…, 0.86)`）。 */
export const DUMMY_SCALE = 0.86;

/** 被打中閃白的長度（毫秒，正常播放速度；靶場移植需求第 2 節「被打中閃白 0.1 秒」）。 */
export const DUMMY_FLASH_MS = 100;
/** 閃白的不透明度（和人形受擊白閃的開頭相同）。 */
export const DUMMY_FLASH_ALPHA = 0.85;

/**
 * 閃白在片段時間 `t`（0～1）的不透明度：整段同一個強度、不淡出（只有 0.1 秒，約一格畫面）。
 * 減少動態時效果標成身體片段（`motion: "body"`），`reduceEffects` 會直接畫最後一格、不再動——也就是同一張白閃停一下，
 * 一樣是「一格」，不會多閃（PR-2c 交付第 1 點「減少動態時改成不閃或一格」取一格）。
 */
export function dummyFlashAlpha(t: number): number {
  return t >= 0 && t <= 1 ? DUMMY_FLASH_ALPHA : 0;
}

/** 閃白的長度（毫秒）：照播放速度的時間倍率 `scale` 縮放（慢放截圖時看得到），至少 1。 */
export function dummyFlashMs(scale: number): number {
  return Math.max(1, Math.round(DUMMY_FLASH_MS * scale));
}

const TAU = Math.PI * 2;

/** 畫一個木樁（腳底在原點）；`shadow` 為假時不畫地上的影子（白閃剪影用）。 */
export function drawTrainingDummy(c: Ctx, shadow = true): void {
  c.save();
  c.scale(DUMMY_SCALE, DUMMY_SCALE);
  if (shadow) {
    c.fillStyle = "rgba(0,0,0,0.25)";
    c.beginPath();
    c.ellipse(0, 2, 16, 5, 0, 0, TAU);
    c.fill();
  }
  ink(c, "dm-base", [[-12, 0], [12, 0], [9, -6], [-9, -6]], "#6a4a2a", { w: 0.9 });
  ink(c, "dm-post", [[-3, -6], [3, -6], [3, -34], [-3, -34]], "#9a7046", { w: 0.9 });
  ink(c, "dm-arm", [[-16, -30], [16, -30], [16, -26], [-16, -26]], "#8a6038", { w: 0.8 });
  ink(c, "dm-body", [[-9, -34], [9, -34], [10, -16], [-10, -16]], "#c8b080", { w: 0.9 });
  for (const y of [-30, -24, -19]) stroke(c, `dm-rope${y}`, [[-9, y], [9, y]], 0.6, "#7a5a32");
  ink(c, "dm-head", ellPts(0, -42, 8, 8, 14), "#d8c49a", { w: 0.9 });
  stroke(c, "dm-x1", [[-3, -45], [-1, -43]], 0.8, "#5a3a20");
  stroke(c, "dm-x2", [[1, -45], [3, -43]], 0.8, "#5a3a20");
  c.restore();
}

/**
 * 選單小圖（PR-2d：工坊師傅選單「靶場試玩」那列，取代原本內嵌的 SVG）：同一個 `drawTrainingDummy` 畫在 `px`×`px`（CSS px）的
 * 畫布上，畫布像素 ＝ `px × res`。取景照原本 SVG 的 viewBox（木樁座標 -31～31、-55～7，腳底在下緣往上 7 的位置）。
 */
export const DUMMY_ICON_VIEW = { x: -31, y: -55, size: 62 } as const;

export function drawTrainingDummyIcon(c: Ctx, px: number, res: number): void {
  const k = (px * res) / (DUMMY_ICON_VIEW.size * DUMMY_SCALE);
  c.save();
  // `drawTrainingDummy` 內部再乘 0.86：外面除掉，取景和原本 SVG（未縮放的木樁座標）一樣大
  c.setTransform(k, 0, 0, k, -DUMMY_ICON_VIEW.x * DUMMY_SCALE * k, -DUMMY_ICON_VIEW.y * DUMMY_SCALE * k);
  drawTrainingDummy(c);
  c.restore();
}

/** 白閃用：同一個木樁不含影子、轉成白色剪影（不透明度不變；同 6C-8 `whiteCanvas`）。 */
export function drawTrainingDummyFlash(c: Ctx): void {
  drawTrainingDummy(c, false);
  const canvas = c.canvas;
  if (canvas === undefined || canvas.width <= 0 || canvas.height <= 0) return;
  const img = c.getImageData(0, 0, canvas.width, canvas.height);
  whiteSilhouette(img.data, 1);
  c.putImageData(img, 0, 0);
}
