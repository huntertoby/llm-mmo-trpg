// 召喚技能的灌注關鍵字選擇（Phase 3-33b）：目標選好、送出之前多一步。沿用戰鬥詢問視窗外框
// （DialogFrame，沒有遮罩、戰場仍可看）；選項說明直接寫在按鈕旁，不另做彈出層（不涉及浮動卡）。
import { DialogFrame } from "./DialogFrame";
import { infusionPromptText, type InfusionOption } from "../battle/infusion";

interface Props {
  skillName: string;
  options: readonly InfusionOption[];
  enabled: boolean;
  onPick(keywordId: string): void;
  onCancel(): void;
}

export function InfusionDialog({ skillName, options, enabled, onPick, onCancel }: Props) {
  return (
    <DialogFrame label="灌注關鍵字" title="灌注關鍵字">
      <p>{infusionPromptText(skillName, options.length)}</p>
      <ul className="infusion-options">
        {options.map((o, i) => (
          <li key={o.id}>
            <button type="button" disabled={!enabled} onClick={() => onPick(o.id)}>
              {o.name_zh}
              {i === 0 ? "（預設）" : ""}
            </button>
            <span className="small muted">　{o.effect_zh}</span>
          </li>
        ))}
      </ul>
      <div className="modal-buttons">
        <button type="button" disabled={!enabled} onClick={onCancel}>
          取消施放
        </button>
      </div>
    </DialogFrame>
  );
}
