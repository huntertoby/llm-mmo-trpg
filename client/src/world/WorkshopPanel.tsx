// 主城工坊師傅的選單（PR-2b，#147；樣張 docs/art/OB與PR樣張.md 第 2.1 節、第 6 節表「工坊師傅選單」列）：
// 標頭（郵差面板的 `mail-head`：師傅頭像＋名字＋身分行）、標頭下一行師傅的話、兩列選單（一般／滑過／停用三態；
// 停用列只寫一次「之後開放」）、面板下一行說明。文字、地名、能不能開、「新」小牌全部來自伺服器（`WorldView.workshop`）。
// 不能開「靶場試玩」時第 1 列停用，原因用共用的 `<Hint>`（6.5.1）說。
import type { WorldView } from "../api/types";
import { Hint } from "../ui/Hint";
import { WeaponIcon } from "../ui/WeaponIcon";
import { Portrait } from "./StoryIcons";

export type WorkshopData = NonNullable<WorldView["workshop"]>;

/** 「新」小牌的字（定稿補定 3：該角色第一次點開「靶場試玩」後消失）。 */
export const WORKSHOP_NEW_TAG = "新";

/** 第 1 列「靶場試玩」的狀態：能不能按、停用的原因、要不要掛「新」小牌。`seen`＝這次畫面裡剛點過（伺服器紀錄回來前先藏小牌）。 */
export function practiceRow(w: WorkshopData, seen: boolean): { enabled: boolean; reason: string | null; isNew: boolean } {
  const enabled = w.practice_available;
  return { enabled, reason: enabled ? null : (w.practice_blocked_zh ?? null), isNew: w.practice_new && !seen };
}

/** 選單列的木樁小圖（同場上木樁的畫法縮小：底座、木樁、橫臂、麻布身、布頭；樣張 `obSamples.js` 的 `dummy()`）。 */
function DummyGlyph() {
  const ink = { stroke: "#2b2118", strokeWidth: 0.9, strokeLinejoin: "round" as const };
  return (
    <svg viewBox="-31 -55 62 62" width="32" height="32" aria-hidden="true">
      <ellipse cx="0" cy="2" rx="16" ry="5" fill="rgb(0 0 0 / 25%)" />
      <path d="M-12 0H12L9 -6H-9Z" fill="#6a4a2a" {...ink} />
      <path d="M-3 -6H3V-34H-3Z" fill="#9a7046" {...ink} />
      <path d="M-16 -30H16V-26H-16Z" fill="#8a6038" {...ink} strokeWidth={0.8} />
      <path d="M-9 -34H9L10 -16H-10Z" fill="#c8b080" {...ink} />
      <path d="M-9 -30H9M-9 -24H9M-9 -19H9" stroke="#7a5a32" strokeWidth="0.6" />
      <circle cx="0" cy="-42" r="8" fill="#d8c49a" {...ink} />
      <path d="M-3 -45L-1 -43M1 -45L3 -43" stroke="#5a3a20" strokeWidth="0.8" strokeLinecap="round" />
    </svg>
  );
}

interface Props {
  workshop: WorkshopData;
  busy: boolean;
  /** 這次畫面裡已經點過「靶場試玩」（`seen_id` 在本機的看過紀錄）。 */
  seen: boolean;
  onPractice(): void;
}

export function WorkshopPanel({ workshop: w, busy, seen, onPractice }: Props) {
  const row = practiceRow(w, seen);
  const speaker = w.speaker ?? null;
  const go = row.enabled && !busy;
  const practice = (
    <button
      type="button"
      className={`workshop-menu-item${row.enabled ? "" : " is-disabled"}`}
      aria-disabled={!go}
      onClick={() => go && onPractice()}
      data-testid="workshop-practice"
    >
      <span className="workshop-menu-icon">
        <DummyGlyph />
      </span>
      <span className="workshop-menu-text">
        <b>
          {w.practice_zh}
          {row.isNew && (
            <span className="workshop-new-tag" data-testid="workshop-new">
              {WORKSHOP_NEW_TAG}
            </span>
          )}
        </b>
        <span>{w.practice_note_zh}</span>
      </span>
      {row.enabled && (
        <span className="workshop-menu-go" aria-hidden="true">
          ›
        </span>
      )}
    </button>
  );
  return (
    <div className="workshop-panel" data-testid="world-hud-workshop">
      <header className="mail-head">
        <Portrait portrait={speaker?.portrait ?? null} region={speaker?.region ?? null} size={56} label={speaker?.name_zh ?? w.line.speaker_zh} />
        <div className="mail-head-text">
          <h2>{speaker?.name_zh ?? w.line.speaker_zh}</h2>
          <div className="small muted" data-testid="workshop-title">
            {w.title_zh}
          </div>
        </div>
      </header>
      <p className="world-opening-line workshop-line" data-testid="workshop-line">
        <b>{w.line.speaker_zh}</b>：{w.line.text_zh}
      </p>
      <div className="workshop-menu">
        {row.reason !== null ? <Hint text={row.reason}>{practice}</Hint> : practice}
        <button type="button" className="workshop-menu-item" disabled data-testid="workshop-rework">
          <span className="workshop-menu-icon rework">
            <WeaponIcon weaponId="hammer" weaponClass="melee" size={30} />
          </span>
          <span className="workshop-menu-text">
            <b>{w.rework_zh}</b>
            <span>{w.rework_note_zh}</span>
          </span>
        </button>
      </div>
      <p className="small muted workshop-note" data-testid="workshop-footer">
        {w.footer_zh}
      </p>
    </div>
  );
}
