// 戰鬥中的詢問視窗外框（Phase 3-8）：水平置中、靠上或靠下（靠下時蓋住詢問期間用不到的技能列）；
// 要看被擋住的格子時可以按「移到下方／移到上方」切換位置。沒有背景遮罩，戰場仍可點選。
// UI-E2：外觀收進共用彈窗元件 `PopupFrame`（深藍底、金框、區域四角飾件；標題列不跟著捲，內容在框內捲）。
// 大世界的開場、配點教學（6F-4）、升級、你不在的時候也用這個外框。
// UI-E1 追加：
// - 1：`tone="danger"`（反應詢問：敵人行動觸發、要馬上決定）走共用彈窗的危險類，上緣加紅帶；
// - 2：大世界（`DialogHudBox` 有值）套 6F-3 避開四角 HUD 的位置規則（上緣在主角卡下方、下緣停在功能列上方），
//   這時不顯示「移到下方」（位置由 HUD 決定）。戰鬥沒有給，照舊靠上／靠下。
import { createContext, useContext, useState, type ReactNode } from "react";
import { Hint } from "./Hint";
import { PopupFrame, type PopupBoxLike, type PopupTone } from "./PopupFrame";

/** 大世界的詢問視窗位置（視窗座標的 `popupBox`）；`null`＝不用 HUD 規則（戰鬥）。 */
export const DialogHudBox = createContext<PopupBoxLike | null>(null);

interface Props {
  label: string;
  title: ReactNode;
  children: ReactNode;
  /** 一開始放在下方（例如反應詢問的觸發者在戰場上半部時，見 `dialogStartsLow`）。 */
  startLow?: boolean;
  /** 危險類（反應詢問）：上緣紅帶。 */
  tone?: PopupTone;
}

export function DialogFrame({ label, title, children, startLow = false, tone = "normal" }: Props) {
  const [low, setLow] = useState(startLow);
  const hud = useContext(DialogHudBox);
  const head = (
    <div className="decision-head">
      <div className="modal-title">{title}</div>
      {hud === null && (
        <Hint text={low ? "把視窗移到畫面上方" : "把視窗移到畫面下方（看被擋住的格子）"}>
          <button type="button" className="small-button dialog-move" onClick={() => setLow((v) => !v)}>
            {low ? "移到上方 ▲" : "移到下方 ▼"}
          </button>
        </Hint>
      )}
    </div>
  );
  const placement = hud === null ? ({ kind: "dialog", low } as const) : ({ kind: "hud", box: hud } as const);
  return (
    <PopupFrame placement={placement} tone={tone} className={`decision-card${hud === null ? "" : " world-hud-dialog"}`} role="dialog" label={label} head={head}>
      {children}
    </PopupFrame>
  );
}
