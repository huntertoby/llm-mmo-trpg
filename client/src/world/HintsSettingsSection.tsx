// 設定面板的「提示」區（6F-4，6F-2b）：「重新顯示提示」清掉這個角色出過的戰鬥短提示、看過的開場與教學、
// 「不再顯示提示」（紀錄記在角色身上，送 `hints_reset`）。升級畫面的紀錄不清。
import { useState } from "react";

interface Props {
  onReset(): void;
}

export function HintsSettingsSection({ onReset }: Props) {
  const [done, setDone] = useState(false);
  return (
    <div className="motion-settings" data-testid="hints-settings">
      <div className="section-title">提示</div>
      <div className="layout-actions">
        <button
          type="button"
          className="small-button"
          onClick={() => {
            onReset();
            setDone(true);
          }}
          data-testid="hints-reset"
        >
          重新顯示提示
        </button>
      </div>
      <div className="small muted">{done ? "好了：戰鬥短提示、開場與教學會再出現一次。" : "戰鬥短提示、開場與教學再出現一次（也會取消「不再顯示提示」）。"}</div>
    </div>
  );
}
