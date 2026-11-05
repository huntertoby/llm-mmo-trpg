// RT-5d（必修 2）：開發用的鏡頭位移。1600×900 時主城整張地圖都在畫面裡，開場的守印人不會出畫面，
// 拍不到「夾到畫面邊的箭頭／泡泡」；開發模式下可以用 `?dev=1&devcam=dx,dy`（畫布像素）把鏡頭推開，讓守印人走出畫面。
// 不帶 `?dev=1` 時一律不理（正式畫面不受影響）。
import { isDevMode } from "../run/startFlow";
import type { Camera } from "./camera";

/** 讀 `devcam=dx,dy`；不是開發模式、沒給、格式不對 → null。 */
export function devCameraShift(search: string): { x: number; y: number } | null {
  if (!isDevMode(search)) return null;
  const raw = new URLSearchParams(search).get("devcam");
  if (raw === null) return null;
  const parts = raw.split(",").map((s) => Number(s.trim()));
  if (parts.length !== 2 || parts.some((n) => !Number.isFinite(n))) return null;
  const [x = 0, y = 0] = parts;
  return x === 0 && y === 0 ? null : { x, y };
}

/** 把位移加到鏡頭上（沒位移時原樣回傳）。 */
export function shiftCamera(cam: Camera, shift: { x: number; y: number } | null): Camera {
  return shift === null ? cam : { ...cam, x: cam.x + shift.x, y: cam.y + shift.y };
}
