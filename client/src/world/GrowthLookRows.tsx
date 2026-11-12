// 「成長與技能」面板的「外觀與種族」分頁（PNL-2；docs/art/資訊面板-移植需求.md 3.3、4.1 #16、#17）：兩列設定列
// （列名＋次行；右邊鎖標籤＋鈕／選單）。動作與字照舊：外觀＝`LookChange.tsx` 的 `lookChangeAction` 與同一套選單，
// 種族＝`RaceChange.tsx` 的 `raceChangeOptions`／`raceChangeAction`。舊側欄（`WorldPanel`）仍用 `LookChangeLine`／`RaceChangeLine`。
import { useState } from "react";
import type { LookChoice, WorldAction, WorldView } from "../api/types";
import { LookPicker, LookPreview } from "../run/LookPicker";
import { Hint } from "../ui/Hint";
import { LockGlyph, Tag } from "../ui/PanelKit";
import { LOOK_FREE_ZH, LOOK_ROW_ZH, RACE_NOTE_ZH, RACE_ROW_ZH, raceLockTag } from "./growthPanel";
import { lookChangeAction } from "./LookChange";
import { raceChangeAction, raceChangeOptions } from "./RaceChange";

interface Props {
  view: Pick<WorldView, "limits" | "character">;
  busy: boolean;
  onAct(action: WorldAction): void;
}

/** 外觀列：右邊鎖標籤（伺服器的字，例「只有在主城能改外觀」；能改時「主城隨時免費」）＋「改外觀」；展開後外觀選單＋預覽。 */
export function LookChangeRow({ view, busy, onAct }: Props) {
  const character = view.character;
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState<LookChoice>(character.look ?? {});
  const race = character.race ?? "";
  const reason = character.look_change_zh ?? null;
  if (race === "") return null;
  return (
    <>
      <div className="pnl-row pnl-set" data-testid="world-look-change">
        <span className="lbl">
          <span className="pnl-l1">{LOOK_ROW_ZH}</span>
        </span>
        <span className="ctl">
          {reason !== null ? (
            <Tag tone="lock" icon={<LockGlyph px={14} />} testId="world-look-tag">
              {reason}
            </Tag>
          ) : (
            <Tag testId="world-look-tag">{LOOK_FREE_ZH}</Tag>
          )}
          <button type="button" disabled={busy || reason !== null} aria-expanded={open} onClick={() => setOpen((o) => !o)} data-testid="world-look-open">
            改外觀
          </button>
        </span>
      </div>
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
    </>
  );
}

/** 種族列（伺服器說本季還能免費換才出現）：右邊鎖標籤（入門期「正式選定後才能換」；原句進說明卡）＋新種族選單＋「換種族」。 */
export function RaceChangeRow({ view, busy, onAct }: Props) {
  const character = view.character;
  const options = raceChangeOptions(character.race ?? null);
  const [pick, setPick] = useState(options[0]?.id ?? "");
  const reason = character.free_race_change_zh ?? null;
  const tag = raceLockTag(view);
  const blocked = busy || reason !== null || pick === "";
  const go = () => {
    const name = options.find((o) => o.id === pick)?.name ?? pick;
    if (typeof window === "undefined" || window.confirm(`換成${name}？這一季的免費換種族只有一次。`)) onAct(raceChangeAction(pick));
  };
  return (
    <div className="pnl-row pnl-set" data-testid="world-race-change">
      <span className="lbl">
        <span className="pnl-l1">{RACE_ROW_ZH}</span>
        <span className="pnl-l3">{RACE_NOTE_ZH}</span>
      </span>
      <span className="ctl">
        {tag !== null && (
          <Hint text={reason}>
            <span className="pnl-tag-hit" tabIndex={0}>
              <Tag tone="lock" icon={<LockGlyph px={14} />} testId="world-race-tag">
                {tag}
              </Tag>
            </span>
          </Hint>
        )}
        <select value={pick} disabled={busy || reason !== null} onChange={(e) => setPick(e.target.value)} aria-label="新種族">
          {options.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
        <button type="button" disabled={blocked} onClick={go}>
          換種族
        </button>
      </span>
    </div>
  );
}
