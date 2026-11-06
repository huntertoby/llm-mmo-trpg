// 沒有骨架的單位受擊白閃（Phase 6C-8；docs/archive/art/6A-4g與6C-5與6M-4與6C-7檢查.md 第 3 節待決 6）：形態、召喚物、倒地的人
// 不再畫整片白圓，改成和 6M-3／6M-4 一樣只閃剪影——把同一張圖（不含地上影子）再畫一次、用 `brightness(0) invert(1)`
// 變成白色剪影（`whiteCanvas`），疊在小人上、照受擊片段的白閃強度調不透明度。不需要骨架，任何畫得出來的單位都能用。
import { Sprite, type Container, type Texture } from "pixi.js";
import { whiteSilhouette } from "./creaturePose";

/** 白色剪影節點的名稱（疊在小人上面，結束時拿掉）。 */
export const FLASH_LABEL = "body-flash";

/**
 * 把畫布原地變成白色剪影（等同 CSS／Canvas 濾鏡 `brightness(0) invert(1)`）：每個像素的 RGB 變成白、不透明度不變，
 * 透明的像素維持透明（剪影外不變白）。用像素運算而不是 `ctx.filter`，結果在每個瀏覽器都一樣。`null` 原樣回傳。
 */
export function whiteCanvas(canvas: HTMLCanvasElement | null): HTMLCanvasElement | null {
  if (canvas === null) return null;
  const ctx = canvas.getContext("2d");
  if (ctx === null || canvas.width <= 0 || canvas.height <= 0) return canvas;
  const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
  whiteSilhouette(img.data, 1);
  ctx.putImageData(img, 0, 0);
  return canvas;
}

/**
 * 在小人（`body`）上疊一層白色剪影：同一個父節點、緊接在小人後面，錨點、縮放、位置、旋轉和小人相同（貼圖畫布大小相同，像素對齊）。
 * 已經疊過就沿用、只換不透明度；`alpha` ＝ 白閃強度（0～1）。
 */
export function overlayFlash(body: Sprite, texture: Texture, alpha: number): Sprite | null {
  const parent = body.parent as Container | null;
  if (parent === null) return null;
  let top = parent.children.find((n): n is Sprite => n instanceof Sprite && n.label === FLASH_LABEL) ?? null;
  if (top === null) {
    top = new Sprite(texture);
    top.label = FLASH_LABEL;
    parent.addChildAt(top, parent.getChildIndex(body) + 1);
  } else if (top.texture !== texture) top.texture = texture;
  top.anchor.copyFrom(body.anchor);
  top.scale.copyFrom(body.scale);
  top.position.copyFrom(body.position);
  top.rotation = body.rotation;
  top.alpha = Math.max(0, Math.min(1, alpha));
  top.visible = top.alpha > 0;
  return top;
}

/** 拿掉疊上去的白色剪影（受擊片段結束時）。 */
export function clearFlash(unit: Container): void {
  for (const n of [...unit.children]) if (n.label === FLASH_LABEL) n.destroy();
}
