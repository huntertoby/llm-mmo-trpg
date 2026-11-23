// 按住連走（WM-1 第 1 項）：記住「正在按哪個方向」，不靠作業系統的按鍵重複。
// - `keydown`（不是 `e.repeat`）＝按下：放進按住的清單（最後按的優先），並記一次「點按」（按下馬上放開也走一格）；
// - `keyup`＝放開：從清單拿掉；視窗失焦或分頁藏起來＝全部放開；
// - 走路迴圈每播完一格呼叫 `take()`：還按著的方向（最後按的），沒有就看有沒有沒用掉的點按，都沒有就停。
// 純資料結構，不碰 DOM；`WorldField` 接鍵盤事件。
import type { Direction } from "./fieldModel";

export class HeldKeys {
  private held: Direction[] = [];
  private tap: Direction | null = null;

  /** 按下（`repeat`＝作業系統的重複，不算新的按下）；回傳是不是新的按下。 */
  press(dir: Direction, repeat: boolean): boolean {
    if (repeat) return false;
    this.held = [...this.held.filter((d) => d !== dir), dir];
    this.tap = dir;
    return true;
  }

  /** 放開。 */
  release(dir: Direction): void {
    this.held = this.held.filter((d) => d !== dir);
  }

  /** 全部放開（視窗失焦、分頁藏起來、遇敵、離開畫面）。 */
  clear(): void {
    this.held = [];
    this.tap = null;
  }

  /** 現在按著的方向（最後按的）；沒有為 `null`。 */
  get active(): Direction | null {
    return this.held[this.held.length - 1] ?? null;
  }

  /** 下一步要走的方向：還按著的優先，再來是沒用掉的點按（用掉）；都沒有為 `null`。 */
  take(): Direction | null {
    const dir = this.active ?? this.tap;
    this.tap = null;
    return dir;
  }
}
