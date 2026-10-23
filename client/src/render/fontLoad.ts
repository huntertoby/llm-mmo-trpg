// 字型載入（Phase 3-35）：Noto Sans TC 是 self-host、依 unicode-range 切片載入的 woff2。
// 畫布文字（Pixi 文字、技能圖示）在字型還沒好時會用備援字型畫並被快取，
// 所以：開畫面前先等 400／700 載入（有逾時，不卡畫面）；之後只要又有字型載入完成（`loadingdone`），
// 就清掉技能圖示快取並把 `fontEpoch` 加一，讓畫布與圖示元件重畫。
import { clearSkillIconCache } from "./skillIcon";
import { clearStatusIconCache } from "./statusIcon";

export const FONT_LOAD_TIMEOUT_MS = 3000;
/** 先預載的常用字（其餘切片在畫到時才載入，載入完成會觸發重畫）。 */
const SAMPLE = "技能攻擊防禦傷害治療回合 0123456789";

let epoch = 0;
const listeners = new Set<() => void>();
let hooked = false;

function bump(): void {
  clearSkillIconCache();
  clearStatusIconCache();
  epoch += 1;
  for (const l of [...listeners]) l();
}

/** 掛上 `loadingdone`（只掛一次）。沒有 `document.fonts`（測試環境）時什麼都不做。 */
function hook(): void {
  if (hooked || typeof document === "undefined" || document.fonts === undefined) return;
  hooked = true;
  document.fonts.addEventListener("loadingdone", bump);
}

export function subscribeFonts(cb: () => void): () => void {
  hook();
  listeners.add(cb);
  return () => listeners.delete(cb);
}

export const fontEpoch = (): number => epoch;

/** 等 400／700 載入，最多 `FONT_LOAD_TIMEOUT_MS`；失敗或逾時都照常往下（用備援字型）。 */
export async function waitForFonts(): Promise<void> {
  hook();
  if (typeof document === "undefined" || document.fonts === undefined) return;
  const load = Promise.all([
    document.fonts.load('400 16px "Noto Sans TC"', SAMPLE),
    document.fonts.load('700 16px "Noto Sans TC"', SAMPLE),
  ]).then(() => undefined);
  const timeout = new Promise<void>((resolve) => setTimeout(resolve, FONT_LOAD_TIMEOUT_MS));
  try {
    await Promise.race([load, timeout]);
  } catch {
    // 字型載入失敗就用備援字型
  }
}
