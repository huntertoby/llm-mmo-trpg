// 戰場右下角的縮放控制（由 BattleScreen 抽出，Phase 3T-7）：縮小、目前比例、放大、自動填滿。

import { ZOOM_STEP, zoomPercent } from "../../battle/layoutPrefs";
import { Hint } from "../../ui/Hint";

interface Props {
  /** 手動縮放比例；`null` ＝ 自動填滿。 */
  zoom: number | null;
  scale: number;
  onZoomStep(factor: number): void;
  onFill(): void;
}

export function ZoomControls({ zoom, scale, onZoomStep, onFill }: Props) {
  return (
    <div className="zoom-controls" aria-label="地圖縮放">
      <Hint text="縮小（Ctrl＋滾輪）">
        <button type="button" aria-label="縮小" onClick={() => onZoomStep(1 / ZOOM_STEP)}>
          －
        </button>
      </Hint>
      <Hint text={zoom === null ? "自動填滿" : "手動縮放"}>
        <span className="zoom-percent">{zoom === null ? `自動 ${zoomPercent(scale)}` : zoomPercent(scale)}</span>
      </Hint>
      <Hint text="放大（Ctrl＋滾輪）">
        <button type="button" aria-label="放大" onClick={() => onZoomStep(ZOOM_STEP)}>
          ＋
        </button>
      </Hint>
      <Hint text="自動填滿可用空間">
        <button type="button" disabled={zoom === null} onClick={onFill}>
          填滿
        </button>
      </Hint>
    </div>
  );
}
