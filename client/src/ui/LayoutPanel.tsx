// 「版面」彈出面板（Phase 3-10）：地圖縮放的滑桿與「重設為預設」；技能特效的畫面震動開關（Phase 3-12）。
// 6A-3：「重新顯示操作說明」清掉操作說明句的次數（`battle/opHints.ts`）。
// 6A-4g：版面 A 沒有窄欄與分隔線，舊的欄寬、列高、主角卡寬滑桿刪掉。
// AU-1：最下面加「聲音」區（四軌音量、靜音、減少刺耳音效）。
// 6H-1：聲音區下面加「減少動態」（跟系統／開／關）。
import { useState } from "react";
import { ZOOM_MAX, ZOOM_MIN, zoomPercent, type LayoutPrefs } from "../battle/layoutPrefs";
import { resetOpHints } from "../battle/opHints";
import { AudioSettingsPanel } from "../audio/AudioSettingsPanel";
import { MotionSettingsSection } from "./MotionSettingsSection";

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
  /** 目前實際的地圖縮放（自動填滿時為算出的比例）。 */
  scale: number;
  onChange(patch: Partial<LayoutPrefs>): void;
  onReset(): void;
  /** 技能特效的畫面震動（Phase 3-12；另外存，不受「重設為預設」影響）。 */
  shake: boolean;
  onShake(on: boolean): void;
  /** 格子上有單位時，地形資訊卡收起成一行（Phase 3-18b；另外存）。 */
  collapseTile: boolean;
  onCollapseTile(on: boolean): void;
}

export function LayoutPanel({ prefs, scale, onChange, onReset, shake, onShake, collapseTile, onCollapseTile }: Props) {
  return (
    <div className="layout-panel" aria-label="版面設定">
      <div className="section-title">版面</div>
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
      <div className="small muted">Ctrl＋滾輪縮放地圖，放大後用捲軸或滑鼠中鍵拖曳平移。</div>
      <AudioSettingsPanel />
      <MotionSettingsSection />
    </div>
  );
}
