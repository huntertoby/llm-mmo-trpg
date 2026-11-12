// 浮動卡的共用規則（Phase 3-30 第 32.1 項）：技能列的技能卡、部件說明框 `PartTip` 都用這一份。
// 純邏輯、不碰 React 與 DOM（計時器可用 vitest fake timers 測）；`useFloatCard.tsx` 負責接事件與量測。
//
// 規則：
// 1. 滑過觸發元素約 150ms 後顯示；離開後有約 250ms 寬限，期間移進卡片（或又移回按鈕）就保持開著。
// 2. 卡片貼齊觸發元素（預設上方、無空隙，兩者之間是透明橋接區），超出視窗就翻到下方或往內推。
// 3. 點一下釘住；Esc 或點外面關閉；同時只開一張（新的取代舊的；卡片內的部件說明框例外）。
// 4. 取得焦點（鍵盤）時顯示；觸控沒有滑過，點一下開關。
// 5. 有動作的按鈕（技能列、功能列；`pinOn: "hold"`，6A-1 開發 PM 定案）：觸控點一下執行動作、不開說明；
//    長按約 0.4 秒開說明（釘住），放開時不執行動作（`LongPress`）。

export const OPEN_DELAY_MS = 150;
export const CLOSE_GRACE_MS = 250;
/** 卡片與觸發元素之間的透明橋接區高度（像素）；視覺上的間距就是它。 */
export const BRIDGE_PX = 6;

/** 長按開說明的時間（6A-1：約 0.4 秒）。 */
export const LONG_PRESS_MS = 400;
/** 長按期間手指移動超過這麼多像素就當成捲動，取消長按。 */
export const LONG_PRESS_SLOP_PX = 10;

/**
 * 卡片的釘住方式：
 * - `always`：滑鼠與觸控點一下都釘住（本身沒有動作的元素）；
 * - `touch`：只有觸控點一下開關（滑鼠點擊留給元素自己的動作）；
 * - `hold`：有動作的按鈕——觸控長按才開說明，點一下只執行動作（6A-1）；
 * - `never`：不因點擊釘住。
 */
export type PinMode = "always" | "touch" | "hold" | "never";

/**
 * 長按判定（6A-1，純邏輯；計時器可用 fake timers 測）。
 * `down` 開始計時，`LONG_PRESS_MS` 內沒有 `up`／`move` 超過 `LONG_PRESS_SLOP_PX`／`cancel` 就觸發 `onFire`；
 * 觸發過的這次按壓，接下來的 click 由 `consumeClick()` 回傳 `true`，呼叫端吞掉它（放開不執行動作）。
 */
export class LongPress {
  private timer: ReturnType<typeof setTimeout> | null = null;
  private fired = false;
  private start: { x: number; y: number } | null = null;

  constructor(private readonly onFire: () => void) {}

  down(x = 0, y = 0): void {
    this.clear();
    this.fired = false;
    this.start = { x, y };
    this.timer = setTimeout(() => {
      this.timer = null;
      this.fired = true;
      this.onFire();
    }, LONG_PRESS_MS);
  }

  move(x: number, y: number): void {
    if (this.start === null || this.timer === null) return;
    if (Math.hypot(x - this.start.x, y - this.start.y) > LONG_PRESS_SLOP_PX) this.clear();
  }

  /** 放開：還沒到時間就取消（之後的 click 照常執行動作）。 */
  up(): void {
    this.clear();
  }

  cancel(): void {
    this.clear();
    this.fired = false;
  }

  /** 這次按壓有觸發長按嗎（有的話接下來的 click 要吞掉）；讀一次就清掉。 */
  consumeClick(): boolean {
    const was = this.fired;
    this.fired = false;
    return was;
  }

  /** 長按已觸發、還沒被 click 讀走（給 contextmenu 判斷要不要擋）。 */
  get pending(): boolean {
    return this.fired || this.timer !== null;
  }

  private clear(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.start = null;
  }

  dispose(): void {
    this.cancel();
  }
}

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

  /**
   * 觸發元素被捲出視窗（QK-2b，`docs/art/QK-2檢查.md` 小修 1）：沒釘住的卡片立刻關，不再被夾在視窗邊緣、
   * 指著看不到的觸發元素等 250ms 寬限（滑鼠沒動時瀏覽器也不一定送離開事件）；釘住的照舊留著。
   */
  triggerOutOfView(): void {
    if (this.pinned || !this.visible) return;
    this.dismiss();
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

/** 觸發元素整個在視窗外（捲走了，或寬高為 0 被收起來）。 */
export function anchorOutOfView(anchor: Box, viewport: { width: number; height: number }): boolean {
  if (anchor.width <= 0 && anchor.height <= 0) return true;
  return anchor.top + anchor.height <= 0 || anchor.top >= viewport.height || anchor.left + anchor.width <= 0 || anchor.left >= viewport.width;
}

/**
 * 卡片（含橋接區）的位置，`position: fixed` 用的 left／top：貼齊觸發元素、不留空隙；
 * 預設放上方，放不下就翻到下方，兩邊都放不下就選空間大的一邊再往內推；左右夾在視窗內。
 * `prefer`（6T-1d、UI-E3c）：先試哪一邊（預設上方；觸發元素正上方緊貼著標題時用 `"below"`），放不下才翻到另一邊。
 * 用 `"below"` 的地方（6.5.1 第 6 點「預設上方」的明文例外，其他浮動卡仍預設上方）：郵寄面板的部分 `<Hint>`（6T-1d）；
 * 大世界技能面板的技能卡 `SkillTile`（UI-E3c 小修 5，美術 PM 退回：往上開會蓋到主角卡的血條、法力條）；
 * 雇用面板技能圖示列的說明牌（UI-E3c 小修 9：往上開會蓋住傭兵名字）。
 * `size` 是整個外框（含橋接區）的大小。
 */
export function floatPlacement(
  anchor: Box,
  size: { width: number; height: number },
  viewport: { width: number; height: number },
  align?: Align,
  margin?: number,
  prefer?: Side,
): { left: number; top: number; side: Side };
export function floatPlacement(
  anchor: Box,
  size: { width: number; height: number },
  viewport: { width: number; height: number },
  align: Align,
  margin: number,
  prefer: "above",
  fallback: SidesFallback,
): { left: number; top: number; side: Side | SideX };
export function floatPlacement(
  anchor: Box,
  size: { width: number; height: number },
  viewport: { width: number; height: number },
  align: Align = "start",
  margin = 4,
  prefer: Side = "above",
  fallback?: SidesFallback,
): { left: number; top: number; side: Side | SideX } {
  if (fallback !== undefined) return aboveOrSides(anchor, size, viewport, align, margin, fallback.gap);
  const room = {
    above: anchor.top - margin,
    below: viewport.height - margin - (anchor.top + anchor.height),
  };
  // 先試 `prefer` 那一邊；放不下再翻到另一邊（兩邊都放不下選空間大的）
  const other: Side = prefer === "above" ? "below" : "above";
  let side: Side = prefer;
  if (room[prefer] < size.height) side = room[other] >= size.height || room[other] > room[prefer] ? other : prefer;
  const rawTop = side === "above" ? anchor.top - size.height : anchor.top + anchor.height;
  const rawLeft = align === "center" ? anchor.left + anchor.width / 2 - size.width / 2 : anchor.left;
  return {
    left: clamp(rawLeft, margin, viewport.width - size.width - margin),
    top: clamp(rawTop, margin, viewport.height - size.height - margin),
    side,
  };
}

/** 左右兩側（`floatPlacement` 的 `fallback: "sides"`、`sidePlacement`）。 */
export type SideX = "left" | "right";

/**
 * PB-1c（美術移植需求 3.2、使用者「其他都按照建議」）：上方放不下時**退回左右**，不翻到下方。
 * 只給選部位小選單在窄畫面用（`ui/PartMenu.tsx`）；`gap`＝和觸發元素之間的距離。
 */
export interface SidesFallback {
  kind: "sides";
  gap: number;
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(v, Math.max(lo, hi)));

function aboveOrSides(
  anchor: Box,
  size: { width: number; height: number },
  viewport: { width: number; height: number },
  align: Align,
  margin: number,
  gap: number,
): { left: number; top: number; side: Side | SideX } {
  if (anchor.top - gap - margin >= size.height) {
    const rawLeft = align === "center" ? anchor.left + anchor.width / 2 - size.width / 2 : anchor.left;
    return { left: clamp(rawLeft, margin, viewport.width - size.width - margin), top: anchor.top - gap - size.height, side: "above" };
  }
  return sidePlacement(anchor, size, viewport, margin, gap);
}

/**
 * 放在觸發元素的右邊或左邊（PB-1c 選部位小選單；寬畫面「照舊放右邊」，美術移植需求 3.2）：右邊放得下放右邊，
 * 不然左邊，兩邊都放不下選空間大的一邊；上緣對齊觸發元素上緣，上下夾在視窗內。
 */
export function sidePlacement(
  anchor: Box,
  size: { width: number; height: number },
  viewport: { width: number; height: number },
  margin = 4,
  gap = 0,
): { left: number; top: number; side: SideX } {
  const right = viewport.width - margin - (anchor.left + anchor.width) - gap;
  const left = anchor.left - margin - gap;
  const side: SideX = right >= size.width || (left < size.width && right >= left) ? "right" : "left";
  const rawLeft = side === "right" ? anchor.left + anchor.width + gap : anchor.left - gap - size.width;
  return {
    left: clamp(rawLeft, margin, viewport.width - size.width - margin),
    top: clamp(anchor.top, margin, viewport.height - size.height - margin),
    side,
  };
}
