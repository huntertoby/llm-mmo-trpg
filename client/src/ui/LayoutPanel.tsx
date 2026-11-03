// 「版面」彈出面板（Phase 3-10）：右側窄欄寬、底部列高、主角狀態卡寬、地圖縮放的滑桿與「重設為預設」；
// 技能特效的畫面震動開關（Phase 3-12）。
// 6A-3：「重新顯示操作說明」清掉操作說明句的次數（`battle/opHints.ts`）。
import { useState } from "react";
import { ZOOM_MAX, ZOOM_MIN, zoomPercent, type LayoutLimits, type LayoutPrefs, type Range } from "../battle/layoutPrefs";
import { resetOpHints } from "../battle/opHints";

/** 設定：操作說明句（前 3 次之後收進「?」）全部重新顯示。 */
export function OpHintReset({ onReset = resetOpHints }: { onReset?: () => void }) {
  const [done, setDone] = useState(false);
  return (
    <div className="layout-actions op-hint-reset">
      <button
        type="button"
        onClick={() => {
          onReset();
          setDone(true);
        }}
      >
        重新顯示操作說明
      </button>
      {done && <span className="small muted">已重設，之後選取時會再顯示 3 次</span>}
    </div>
  );
}

interface Props {
  prefs: LayoutPrefs;
  limits: LayoutLimits;
  /** 目前實際的地圖縮放（自動填滿時為算出的比例）。 */
  scale: number;
  /** 窄螢幕：窄欄收合、底部列版型固定，只有地圖縮放有效。 */
  narrow: boolean;
  onChange(patch: Partial<LayoutPrefs>): void;
  onReset(): void;
  /** 技能特效的畫面震動（Phase 3-12；另外存，不受「重設為預設」影響）。 */
  shake: boolean;
  onShake(on: boolean): void;
  /** 格子上有單位時，地形資訊卡收起成一行（Phase 3-18b；另外存）。 */
  collapseTile: boolean;
  onCollapseTile(on: boolean): void;
  /** 版面 A（6A-4e）：四角 HUD 疊在戰場上、沒有窄欄與分隔線，不顯示欄寬與列高的滑桿。 */
  hudA?: boolean;
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

export function LayoutPanel({ prefs, limits, scale, narrow, onChange, onReset, shake, onShake, collapseTile, onCollapseTile, hudA = false }: Props) {
  return (
    <div className="layout-panel" aria-label="版面設定">
      <div className="section-title">版面</div>
      {!hudA && (
        <>
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
        </>
      )}
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
      <label className="layout-check">
        <input type="checkbox" checked={shake} onChange={(e) => onShake(e.target.checked)} />
        <span>技能特效的畫面震動</span>
      </label>
      <label className="layout-check">
        <input type="checkbox" checked={collapseTile} onChange={(e) => onCollapseTile(e.target.checked)} />
        <span>格子上有單位時，地形資訊卡只留一行</span>
      </label>
      <div className="layout-actions">
        <button type="button" disabled={prefs.zoom === null} onClick={() => onChange({ zoom: null })}>
          地圖自動填滿
        </button>
        <button type="button" onClick={onReset}>
          重設為預設
        </button>
      </div>
      <OpHintReset />
      {hudA ? (
        <div className="small muted">Ctrl＋滾輪縮放地圖，放大後用捲軸或滑鼠中鍵拖曳平移。</div>
      ) : (
        <>
          {narrow && <div className="small muted">視窗較窄時窄欄與底部列版型固定，這三項不生效。</div>}
          <div className="small muted">也可以直接拖曳畫面上的分隔線；Ctrl＋滾輪縮放地圖，放大後用捲軸或滑鼠中鍵拖曳平移。</div>
        </>
      )}
    </div>
  );
}
