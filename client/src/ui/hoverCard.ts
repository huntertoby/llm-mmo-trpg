// 滑過戰場格子的單位資訊卡規則（Phase 3-30 第 32.2 項）：與 32.1 的浮動卡相同——
// 滑過格子顯示（格子沒有按鈕，立即顯示）；離開原本的格子後有 250ms 寬限，期間滑進卡片（含橋接區）就保持開著，
// 且滑過途中其他格子不會換成別人的卡；點一下卡片釘住；Esc 或點外面關閉；同時只開一張。
// 純邏輯、不碰 React 與 DOM（計時器可用 vitest fake timers 測）。
import type { Pos } from "../api/types";
import { posKey } from "../battle/geometry";
import { CLOSE_GRACE_MS, TILE_SWITCH_MS, claim, release, type Dismissable, type Holdable } from "./floatCard";

const same = (a: Pos | null, b: Pos | null): boolean => (a === null || b === null ? a === b : posKey(a) === posKey(b));

export class TileCardController implements Dismissable, Holdable {
  readonly nested = false;
  /** 滑鼠目前所在的格子。 */
  hover: Pos | null = null;
  /** 卡片顯示的格子（寬限期內可能與 `hover` 不同）。 */
  shown: Pos | null = null;
  pinned = false;
  /** 這個格子有東西可顯示嗎（單位或地形資訊）；由畫面每次繪製時更新。 */
  hasContent: (tile: Pos) => boolean = () => true;
  onChange: () => void = () => undefined;
  private holds = 0;
  private overCard = false;
  private suppressed: Pos | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;

  get visible(): boolean {
    return this.shown !== null && this.hasContent(this.shown);
  }

  private clearTimer(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
  }

  private update(fn: () => void): void {
    const was = this.visible;
    fn();
    if (this.visible && !was) claim(this);
    else if (!this.visible && was) release(this);
    this.onChange();
  }

  private target(): Pos | null {
    return same(this.hover, this.suppressed) ? null : this.hover;
  }

  /** 換到另一個有內容的格子用短延遲（``TILE_SWITCH_MS``）；離開卡片或滑到沒有內容的地方用寬限。 */
  private scheduleSwitch(grace = false): void {
    this.clearTimer();
    const next = this.target();
    const delay = !grace && next !== null && this.hasContent(next) ? TILE_SWITCH_MS : CLOSE_GRACE_MS;
    this.timer = setTimeout(() => {
      this.timer = null;
      if (this.overCard || this.holds > 0 || this.pinned) return;
      if (!same(this.shown, this.target())) this.update(() => (this.shown = this.target()));
    }, delay);
  }

  setHover(tile: Pos | null): void {
    if (same(tile, this.hover)) return;
    this.hover = tile;
    if (this.suppressed !== null && !same(tile, this.suppressed)) this.suppressed = null;
    if (this.pinned) return;
    if (same(tile, this.shown)) {
      this.clearTimer();
      return;
    }
    if (!this.visible) {
      this.clearTimer();
      this.update(() => (this.shown = this.target()));
      return;
    }
    if (!this.overCard) this.scheduleSwitch();
  }

  cardEnter(): void {
    this.overCard = true;
    this.clearTimer();
  }

  cardLeave(): void {
    this.overCard = false;
    if (!this.pinned) this.scheduleSwitch(true);
  }

  /** 點卡片：釘住。 */
  pin(): void {
    if (this.visible && !this.pinned) {
      this.pinned = true;
      this.clearTimer();
      this.onChange();
    }
  }

  hold(delta: 1 | -1): void {
    this.holds += delta;
    if (this.holds === 0 && !this.overCard && !this.pinned) this.scheduleSwitch();
  }

  /** 左鍵點格子釘住（3-40）：已釘在同一格就取消；釘在別格就改釘這一格；沒有內容的格子只取消。 */
  pinAt(tile: Pos): void {
    if (this.pinned && same(this.shown, tile)) {
      this.dismiss();
      return;
    }
    this.clearTimer();
    this.hover = tile;
    this.suppressed = null;
    if (!this.hasContent(tile)) {
      if (this.visible) this.dismiss();
      return;
    }
    this.update(() => {
      this.shown = tile;
      this.pinned = true;
    });
  }

  /** Esc、點外面、被另一張卡片取代：全部關掉（滑鼠沒換格子之前不再自己跳出來）。 */
  dismiss(): void {
    this.clearTimer();
    this.overCard = false;
    this.suppressed = this.hover;
    this.pinned = false;
    this.update(() => (this.shown = null));
  }

  dispose(): void {
    this.clearTimer();
    release(this);
  }
}

/** 資訊卡的最大高度：不超出戰場區，也不超出視窗（上下各留邊）；超出時卡片內捲動。 */
export function cardMaxHeight(room: number, viewportHeight: number, margin = 8, floor = 120): number {
  return Math.max(floor, Math.min(room, viewportHeight - 2 * margin));
}
