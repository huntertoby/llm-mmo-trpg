// 戰鬥中的詢問視窗外框（Phase 3-8）：水平置中、靠上或靠下（靠下時蓋住詢問期間用不到的技能列）；
// 要看被擋住的格子時可以按「移到下方／移到上方」切換位置。沒有背景遮罩，戰場仍可點選。
// UI-E2：外觀收進共用彈窗元件 `PopupFrame`（深藍底、金框、區域四角飾件；標題列不跟著捲，內容在框內捲）。
// 大世界的開場、配點教學（6F-4）、升級、你不在的時候也用這個外框。
import { useState, type ReactNode } from "react";
import { Hint } from "./Hint";
import { PopupFrame } from "./PopupFrame";

interface Props {
  label: string;
  title: ReactNode;
  children: ReactNode;
  /** 一開始放在下方（例如反應詢問的觸發者在戰場上半部時，見 `dialogStartsLow`）。 */
  startLow?: boolean;
}

export function DialogFrame({ label, title, children, startLow = false }: Props) {
  const [low, setLow] = useState(startLow);
  const head = (
    <div className="decision-head">
      <div className="modal-title">{title}</div>
      <Hint text={low ? "把視窗移到畫面上方" : "把視窗移到畫面下方（看被擋住的格子）"}>
        <button type="button" className="small-button dialog-move" onClick={() => setLow((v) => !v)}>
          {low ? "移到上方 ▲" : "移到下方 ▼"}
        </button>
      </Hint>
    </div>
  );
  return (
    <PopupFrame placement={{ kind: "dialog", low }} className="decision-card" role="dialog" label={label} head={head}>
      {children}
    </PopupFrame>
  );
}
