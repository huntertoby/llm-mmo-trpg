// 4 級前免費重選的入口（OB-6，#150 第 5 點；21.5「OB-6 補充」）：重選頁不自動開、不攔截點葛蘭——
// 葛蘭的對話面板與主城靶場（靶場、工坊師傅）的面板上各放一顆「重選」鈕（能不能重選、在哪裡由伺服器的 `opening.reselect` 決定）。
// 另外放配點教學收尾彈窗要說的話（Q2：第二段是葛蘭提醒 4 級前可重選）。
import type { ReactNode } from "react";
import type { RangeView } from "../api/types";
import { RESELECT_PANEL_LABEL, opensReselect } from "./range";

type Line = { speaker_zh: string; text_zh: string };

interface Props {
  reselect: RangeView["reselect"] | undefined;
  /** 這個面板是哪個 NPC 或情境物件的。 */
  target: { npc?: string; object?: string };
  busy: boolean;
  onOpen(): void;
  children: ReactNode;
}

/** 面板上方的「重選」鈕（能重選、而且是葛蘭本人或主城靶場的面板才有）；其他時候原樣顯示面板。 */
export function ReselectEntry({ reselect, target, busy, onOpen, children }: Props) {
  if (!opensReselect(reselect, target)) return <>{children}</>;
  return (
    <div className="world-hud-stack" data-testid="world-reselect-entry">
      <div className="panel ob-reselect-entry">
        <button type="button" className="primary" disabled={busy} onClick={onOpen} data-testid="world-reselect-panel">
          {RESELECT_PANEL_LABEL}
        </button>
        {reselect?.before_level != null && <span className="muted small">　{reselect.before_level} 級前可以免費換一次武器與關鍵字</span>}
      </div>
      {children}
    </div>
  );
}

/** 正式選定後配點教學的收尾彈窗（OB-5b）：第一段是葛蘭收尾那句，第二段（OB-6 Q2）是伺服器給的重選提醒（沒有資格時空）。 */
export function allocateClosingLines(speaker: string, said: string | null | undefined, reminder: readonly Line[] | null | undefined): Line[] {
  const out: Line[] = [];
  if (said != null && said !== "") out.push({ speaker_zh: speaker, text_zh: said });
  for (const line of reminder ?? []) out.push({ speaker_zh: line.speaker_zh, text_zh: line.text_zh });
  return out;
}
