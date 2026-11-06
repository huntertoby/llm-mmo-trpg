// 主城改外觀（Phase 6R-2，#137：外觀在主城隨時免費改；換種族另外照 #108）。
// 不另做新畫面：在世界側欄的角色狀態下面加一行「改外觀」，展開後是和建角同一套外觀選單＋預覽，按「換上」送 `change_look`。
// 不在主城等原因（`look_change_zh`）照字顯示、按鈕灰掉。
import { useState } from "react";
import type { LookChoice, WorldAction, WorldView } from "../api/types";
import { LookPicker, LookPreview } from "../run/LookPicker";
import { lookBody } from "../run/lookOptions";

/** 純函式：改外觀的世界動作（全空＝回到種族預設）。 */
export function lookChangeAction(choice: LookChoice): WorldAction {
  const look = lookBody(choice);
  return look === null ? { kind: "change_look" } : { kind: "change_look", look };
}

interface Props {
  character: WorldView["character"];
  busy: boolean;
  onAct(action: WorldAction): void;
}

export function LookChangeLine({ character, busy, onAct }: Props) {
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState<LookChoice>(character.look ?? {});
  const race = character.race ?? "";
  const reason = character.look_change_zh ?? null;
  if (race === "") return null;
  return (
    <div className="small look-change" data-testid="world-look-change">
      <button type="button" disabled={busy || reason !== null} aria-expanded={open} onClick={() => setOpen((o) => !o)} data-testid="world-look-open">
        改外觀
      </button>
      <span className="muted">{reason !== null ? `（${reason}）` : "（主城隨時免費）"}</span>
      {open && reason === null && (
        <div className="look-change-panel" data-testid="world-look-panel">
          <div className="look-change-body">
            <LookPreview race={race} choice={choice} height={150} />
            <LookPicker race={race} choice={choice} onChoice={setChoice} disabled={busy} seed={`town-${character.character_id}`} />
          </div>
          <div className="run-actions">
            <button type="button" onClick={() => setOpen(false)}>
              取消
            </button>
            <button
              type="button"
              className="primary"
              disabled={busy}
              onClick={() => {
                onAct(lookChangeAction(choice));
                setOpen(false);
              }}
              data-testid="world-look-save"
            >
              換上
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
