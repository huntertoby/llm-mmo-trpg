// 「版面」彈出面板（Phase 3-10）：右側窄欄寬、底部列高、主角狀態卡寬、地圖縮放的滑桿與「重設為預設」。
import { ZOOM_MAX, ZOOM_MIN, zoomPercent, type LayoutLimits, type LayoutPrefs, type Range } from "../battle/layoutPrefs";

interface Props {
  prefs: LayoutPrefs;
  limits: LayoutLimits;
  /** 目前實際的地圖縮放（自動填滿時為算出的比例）。 */
  scale: number;
  /** 窄螢幕：窄欄收合、底部列版型固定，只有地圖縮放有效。 */
  narrow: boolean;
  onChange(patch: Partial<LayoutPrefs>): void;
  onReset(): void;
}

function SliderRow({
  label,
  value,
  range,
  disabled,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  range: Range;
  disabled?: boolean;
  unit: string;
  onChange(value: number): void;
}) {
  return (
    <label className="layout-row">
      <span>{label}</span>
      <input
        type="range"
        min={range[0]}
        max={range[1]}
        value={Math.max(range[0], Math.min(range[1], value))}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <span className="layout-value">
        {Math.round(value)}
        {unit}
      </span>
    </label>
  );
}

export function LayoutPanel({ prefs, limits, scale, narrow, onChange, onReset }: Props) {
  return (
    <div className="layout-panel" aria-label="版面設定">
      <div className="section-title">版面</div>
      <SliderRow
        label="右側窄欄寬"
        unit=" px"
        value={prefs.sideWidth}
        range={limits.side}
        disabled={narrow}
        onChange={(v) => onChange({ sideWidth: v })}
      />
      <SliderRow
        label="底部列高"
        unit=" px"
        value={prefs.bottomHeight}
        range={limits.bottom}
        disabled={narrow}
        onChange={(v) => onChange({ bottomHeight: v })}
      />
      <SliderRow
        label="主角狀態卡寬"
        unit=" px"
        value={prefs.heroWidth}
        range={limits.hero}
        disabled={narrow}
        onChange={(v) => onChange({ heroWidth: v })}
      />
      <label className="layout-row">
        <span>地圖縮放</span>
        <input
          type="range"
          min={Math.round(ZOOM_MIN * 100)}
          max={Math.round(ZOOM_MAX * 100)}
          value={Math.round(scale * 100)}
          onChange={(e) => onChange({ zoom: Number(e.target.value) / 100 })}
        />
        <span className="layout-value">{prefs.zoom === null ? `自動 ${zoomPercent(scale)}` : zoomPercent(scale)}</span>
      </label>
      <div className="layout-actions">
        <button type="button" disabled={prefs.zoom === null} onClick={() => onChange({ zoom: null })}>
          地圖自動填滿
        </button>
        <button type="button" onClick={onReset}>
          重設為預設
        </button>
      </div>
      {narrow && <div className="small muted">視窗較窄時窄欄與底部列版型固定，這三項不生效。</div>}
      <div className="small muted">也可以直接拖曳畫面上的分隔線；Ctrl＋滾輪縮放地圖，放大後用捲軸或滑鼠中鍵拖曳平移。</div>
    </div>
  );
}
