// 浮動卡的共用規則（Phase 3-30 第 32.1 項）：技能列的技能卡、部件說明框 `PartTip` 都用這一份。
// 純邏輯、不碰 React 與 DOM（計時器可用 vitest fake timers 測）；`useFloatCard.tsx` 負責接事件與量測。
//
// 規則：
// 1. 滑過觸發元素約 150ms 後顯示；離開後有約 250ms 寬限，期間移進卡片（或又移回按鈕）就保持開著。
// 2. 卡片貼齊觸發元素（預設上方、無空隙，兩者之間是透明橋接區），超出視窗就翻到下方或往內推。
// 3. 點一下釘住；Esc 或點外面關閉；同時只開一張（新的取代舊的；卡片內的部件說明框例外）。
// 4. 取得焦點（鍵盤）時顯示；觸控沒有滑過，點一下開關。

export const OPEN_DELAY_MS = 150;
export const CLOSE_GRACE_MS = 250;
/** 卡片與觸發元素之間的透明橋接區高度（像素）；視覺上的間距就是它。 */
export const BRIDGE_PX = 6;

export type PinMode = "always" | "touch" | "never";

export class FloatController {
  hover = false;
  pinned = false;
  focused = false;
  /** 卡片內有東西還開著（巢狀的部件說明框）時，不可關閉。 */
  private holds = 0;
  private overTrigger = false;
  private overCard = false;
  private timer: ReturnType<typeof setTimeout> | null = null;
  onChange: () => void = () => undefined;

  /** `nested`：自己在另一張卡片裡面（部件說明框）：不參與「同時只開一張」。 */
  constructor(readonly nested = false) {}

  get visible(): boolean {
    return this.hover || this.pinned || this.focused;
  }

  private clearTimer(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
  }

  /** 改狀態：處理「同時只開一張」並通知畫面。 */
  private update(fn: () => void): void {
    const was = this.visible;
    fn();
    if (this.visible && !was) claim(this);
    else if (!this.visible && was) release(this);
    this.onChange();
  }

  private scheduleClose(): void {
    this.clearTimer();
    if (!this.hover) return;
    this.timer = setTimeout(() => {
      this.timer = null;
      if (!this.overTrigger && !this.overCard && this.holds === 0) this.update(() => (this.hover = false));
    }, CLOSE_GRACE_MS);
  }

  triggerEnter(): void {
    this.overTrigger = true;
    this.clearTimer();
    if (this.hover) return;
    this.timer = setTimeout(() => {
      this.timer = null;
      if (this.overTrigger) this.update(() => (this.hover = true));
    }, OPEN_DELAY_MS);
  }

  triggerLeave(): void {
    this.overTrigger = false;
    this.scheduleClose();
  }

  /** 滑進卡片：卡片已經看得到，保持開著；若釘住就維持釘住。 */
  cardEnter(): void {
    this.overCard = true;
    this.clearTimer();
    if (this.visible) this.update(() => (this.hover = true));
  }

  cardLeave(): void {
    this.overCard = false;
    this.scheduleClose();
  }

  /** 點觸發元素（`toggle`）釘住或取消；點卡片只會釘住。 */
  click(toggle: boolean): void {
    this.update(() => {
      this.pinned = toggle ? !this.pinned : true;
    });
  }

  focusIn(): void {
    this.update(() => (this.focused = true));
  }

  focusOut(): void {
    this.update(() => (this.focused = false));
  }

  /** 巢狀的部件說明框開著時呼叫（+1），關掉時呼叫（-1）。 */
  hold(delta: 1 | -1): void {
    this.holds += delta;
    if (this.holds === 0 && this.hover && !this.overTrigger && !this.overCard) this.scheduleClose();
  }

  /** Esc、點外面、被另一張卡片取代：全部關掉。 */
  dismiss(): void {
    this.clearTimer();
    this.overTrigger = false;
    this.overCard = false;
    this.update(() => {
      this.hover = false;
      this.pinned = false;
      this.focused = false;
    });
  }

  dispose(): void {
    this.clearTimer();
    release(this);
  }
}

/** 參與「同時只開一張」的浮動卡（技能卡、單位資訊卡……）。 */
export interface Dismissable {
  readonly nested: boolean;
  dismiss(): void;
}

/** 卡片裡的部件說明框開著時，用它讓外面的卡片不關閉。 */
export interface Holdable {
  hold(delta: 1 | -1): void;
}

let active: Dismissable | null = null;

export function claim(c: Dismissable): void {
  if (c.nested) return;
  const previous = active;
  active = c;
  if (previous !== null && previous !== c) previous.dismiss();
}

export function release(c: Dismissable): void {
  if (active === c) active = null;
}

/** 測試用：清掉「目前開著的卡片」記錄。 */
export function resetFloatRegistry(): void {
  active = null;
}

export interface Box {
  left: number;
  top: number;
  width: number;
  height: number;
}

export type Side = "above" | "below";
export type Align = "start" | "center";

/**
 * 卡片（含橋接區）的位置，`position: fixed` 用的 left／top：貼齊觸發元素、不留空隙；
 * 預設放上方，放不下就翻到下方，兩邊都放不下就選空間大的一邊再往內推；左右夾在視窗內。
 * `size` 是整個外框（含橋接區）的大小。
 */
export function floatPlacement(
  anchor: Box,
  size: { width: number; height: number },
  viewport: { width: number; height: number },
  align: Align = "start",
  margin = 4,
): { left: number; top: number; side: Side } {
  const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(v, Math.max(lo, hi)));
  const room = {
    above: anchor.top - margin,
    below: viewport.height - margin - (anchor.top + anchor.height),
  };
  let side: Side = "above";
  if (room.above < size.height) side = room.below >= size.height || room.below > room.above ? "below" : "above";
  const rawTop = side === "above" ? anchor.top - size.height : anchor.top + anchor.height;
  const rawLeft = align === "center" ? anchor.left + anchor.width / 2 - size.width / 2 : anchor.left;
  return {
    left: clamp(rawLeft, margin, viewport.width - size.width - margin),
    top: clamp(rawTop, margin, viewport.height - size.height - margin),
    side,
  };
}
