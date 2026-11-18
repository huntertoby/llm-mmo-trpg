// 戰前佈置（SK-3，06 6.38 第 11 點）：開戰前選一招、在我方起始區點格子放 1 個陷阱、刻印或表面；
// 也可以跳過直接開戰。格子在戰場上點（選了招之後高亮），這裡只列招與「直接開戰」。
import { DialogFrame } from "./DialogFrame";
import type { PrepOut } from "../api/types";
import { PREP_KIND_ZH, prepPromptText } from "../battle/prep";

interface Props {
  prep: PrepOut;
  skillNames: Readonly<Record<string, string>>;
  picked: string | null;
  enabled: boolean;
  onPick(skillId: string | null): void;
  onSkip(): void;
}

export function PrepDialog({ prep, skillNames, picked, enabled, onPick, onSkip }: Props) {
  const name = (id: string): string => skillNames[id] ?? id;
  return (
    <DialogFrame label="戰前佈置" title="戰前佈置">
      <p>{prepPromptText(prep, picked, picked === null ? "" : name(picked))}</p>
      <div className="modal-buttons">
        {prep.options.map((o) => (
          <button
            key={o.skill_id}
            type="button"
            disabled={!enabled}
            aria-pressed={picked === o.skill_id}
            className={picked === o.skill_id ? "primary" : undefined}
            onClick={() => onPick(picked === o.skill_id ? null : o.skill_id)}
          >
            {name(o.skill_id)}（{PREP_KIND_ZH[o.kind] ?? o.kind}）
          </button>
        ))}
        <button type="button" disabled={!enabled} onClick={onSkip}>
          不佈置，直接開戰
        </button>
      </div>
    </DialogFrame>
  );
}
