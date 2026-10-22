// 拖曳分隔線（Phase 3-10）：按住拖曳調整寬度或高度，方向鍵微調，雙擊還原預設。
// 數值的計算（夾上下限）在 `layoutPrefs.dragValue`；這裡只處理指標事件。
import { useRef, type KeyboardEvent, type PointerEvent } from "react";
import { dragValue, type Range } from "../battle/layoutPrefs";
import { Hint } from "./Hint";

interface Props {
  /** `vertical`：垂直的線，左右拖曳；`horizontal`：水平的線，上下拖曳。 */
  orientation: "vertical" | "horizontal";
  /** 往右（下）拖會讓值變大為 1，變小為 -1。 */
  direction: 1 | -1;
  value: number;
  range: Range;
  label: string;
  onChange(value: number): void;
  onReset(): void;
}

const KEY_STEP = 16;

export function ResizeHandle({ orientation, direction, value, range, label, onChange, onReset }: Props) {
  const start = useRef<{ pointer: number; value: number } | null>(null);
  const axis = (e: { clientX: number; clientY: number }) => (orientation === "vertical" ? e.clientX : e.clientY);

  const onDown = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    start.current = { pointer: axis(e), value };
    e.preventDefault();
  };
  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    const s = start.current;
    if (s !== null) onChange(dragValue(s.value, axis(e) - s.pointer, direction, range));
  };
  const onUp = (e: PointerEvent<HTMLDivElement>) => {
    start.current = null;
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
  };
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const grow = orientation === "vertical" ? "ArrowRight" : "ArrowDown";
    const shrink = orientation === "vertical" ? "ArrowLeft" : "ArrowUp";
    if (e.key !== grow && e.key !== shrink) return;
    e.preventDefault();
    onChange(dragValue(value, e.key === grow ? KEY_STEP : -KEY_STEP, direction, range));
  };

  return (
    <Hint text={`${label}（拖曳調整，雙擊還原）`}>
      <div
        className={`resize-handle ${orientation}`}
        role="separator"
        aria-orientation={orientation}
        aria-label={label}
        aria-valuemin={range[0]}
        aria-valuemax={range[1]}
        aria-valuenow={value}
        tabIndex={0}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
        onDoubleClick={onReset}
        onKeyDown={onKey}
      />
    </Hint>
  );
}
