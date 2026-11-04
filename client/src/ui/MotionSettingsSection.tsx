// 設定面板的「減少動態」區（6H-1；美術 PM 6R-F 檢查待決 1）：跟系統（預設）／開／關，三選一。
// 放在戰鬥「版面」面板的聲音區下面；大世界的齒輪由 PM 合併時接（共用同一個元件）。設定存在 `motionPrefs.ts`。
import { useEffect, useState } from "react";
import { loadMotionPref, MOTION_PREF_LABELS, MOTION_PREFS, saveMotionPref, subscribeMotion, systemReducedMotion, type MotionPref } from "./motionPrefs";

interface Props {
  /** 測試用：初始值與改動（預設讀寫 `motionPrefs`）。 */
  value?: MotionPref;
  onChange?(pref: MotionPref): void;
}

export function MotionSettingsSection({ value, onChange }: Props) {
  const [pref, setPref] = useState<MotionPref>(value ?? loadMotionPref);
  const [system, setSystem] = useState<boolean>(systemReducedMotion);
  useEffect(
    () =>
      subscribeMotion(() => {
        setPref(loadMotionPref());
        setSystem(systemReducedMotion());
      }),
    [],
  );
  const pick = (p: MotionPref): void => {
    setPref(p);
    if (onChange !== undefined) onChange(p);
    else saveMotionPref(p);
  };
  return (
    <div className="motion-settings" role="radiogroup" aria-label="減少動態" data-testid="motion-settings">
      <div className="section-title">減少動態</div>
      <div className="layout-actions motion-choices">
        {MOTION_PREFS.map((p) => (
          <label className="layout-check" key={p} data-testid={`motion-${p}`}>
            <input type="radio" name="trpg-reduced-motion" value={p} checked={pref === p} onChange={() => pick(p)} />
            <span>{p === "system" ? `${MOTION_PREF_LABELS[p]}（預設）` : MOTION_PREF_LABELS[p]}</span>
          </label>
        ))}
      </div>
      <div className="small muted">
        開啟時不震動、不停頓、最後一擊不放慢，動作直接顯示結果。{pref === "system" ? `目前系統設定：${system ? "開" : "關"}。` : ""}
      </div>
    </div>
  );
}
