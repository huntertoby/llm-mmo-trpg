// 主城工坊師傅的選單（PR-2b，#147；樣張 docs/art/OB與PR樣張.md 第 2.1 節、第 6 節表「工坊師傅選單」列）：
// 標頭（郵差面板的 `mail-head`：師傅頭像＋名字＋身分行）、標頭下一行師傅的話、兩列選單（一般／滑過／停用三態；
// 停用列只寫一次「之後開放」）、面板下一行說明。文字、地名、能不能開、「新」小牌全部來自伺服器（`WorldView.workshop`）。
// 不能開「靶場試玩」時第 1 列停用，原因用共用的 `<Hint>`（6.5.1）說。
import { useEffect, useRef } from "react";
import type { WorldView } from "../api/types";
import { drawTrainingDummyIcon } from "../render/trainingDummy";
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

/** 選單列木樁小圖的大小（CSS px）與畫布倍率。 */
export const DUMMY_ICON_PX = 32;
const DUMMY_ICON_RES = 2;

/**
 * 選單列的木樁小圖（PR-2d：重用戰場上木樁的 `drawTrainingDummy`，取代原本內嵌的 SVG；`render/trainingDummy.ts` 的
 * `drawTrainingDummyIcon`）。畫布照原尺寸 × 2 出圖、CSS 不縮放。
 */
function DummyGlyph() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const ctx = ref.current?.getContext("2d");
    if (ctx == null) return;
    ctx.clearRect(0, 0, DUMMY_ICON_PX * DUMMY_ICON_RES, DUMMY_ICON_PX * DUMMY_ICON_RES);
    drawTrainingDummyIcon(ctx, DUMMY_ICON_PX, DUMMY_ICON_RES);
  }, []);
  return (
    <canvas
      ref={ref}
      className="workshop-dummy-icon"
      data-testid="workshop-dummy-icon"
      width={DUMMY_ICON_PX * DUMMY_ICON_RES}
      height={DUMMY_ICON_PX * DUMMY_ICON_RES}
      style={{ width: DUMMY_ICON_PX, height: DUMMY_ICON_PX }}
      aria-hidden="true"
    />
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
