// 說書人文字與擲骰的元件（Phase 6C-7；21.7、docs/art/HUD版面.md 5.7）：
// - `NarratorSubtitle`：畫面上方一行字幕，幾秒後淡出；點「多講一點」看完整旁白（展開時不淡出）；
// - `StoryDialog`：對話框（頭像＋一段字），一次一段，按一下播下一段；最後一段有「多講一點」就接上補充；
// - `DiceRoll`：兩顆 d20 的動畫，結束時標出用的那一顆，結果用顏色表示。
// 「（模板文字）」改成角落的小圖示（說明卡寫原本的字）。
import { useEffect, useState } from "react";
import type { NpcPortrait, WorldStory } from "../api/types";
import { Hint } from "../ui/Hint";
import { canMore, dialogMore, dialogNext, dialogStart, diceFrame, DICE_MS, DICE_TICK_MS, hasNext, OUTCOME_COLOR, subtitleHasMore, subtitleLine, subtitlePhase, SUBTITLE_FADE_MS, SUBTITLE_MS, type Outcome } from "./narration";
import { D20, MiscGlyph, Portrait } from "./StoryIcons";
import "./story.css";

/** LLM 不可用時的降級文字：角落的小圖示。 */
export function FallbackMark({ testId }: { testId?: string }) {
  return (
    <Hint text="模板文字：說書人的模型沒有回應，這段用固定文字">
      <span className="story-fallback" tabIndex={0} data-testid={testId}>
        <MiscGlyph icon="model_off" size={14} />
      </span>
    </Hint>
  );
}

interface SubtitleProps {
  story: WorldStory;
  testId?: string;
  /** 測試用：字幕已經過了多久（毫秒）；不給＝跟著計時器走。 */
  elapsed?: number;
}

export function NarratorSubtitle({ story, testId = "world-subtitle", elapsed }: SubtitleProps) {
  const [expanded, setExpanded] = useState(false);
  const [timePassed, setTimePassed] = useState(0);
  useEffect(() => {
    if (elapsed !== undefined || expanded) return undefined;
    const fade = window.setTimeout(() => setTimePassed(SUBTITLE_MS), SUBTITLE_MS);
    const gone = window.setTimeout(() => setTimePassed(SUBTITLE_MS + SUBTITLE_FADE_MS), SUBTITLE_MS + SUBTITLE_FADE_MS);
    return () => {
      window.clearTimeout(fade);
      window.clearTimeout(gone);
    };
  }, [elapsed, expanded]);
  const phase = subtitlePhase(elapsed ?? timePassed, expanded);
  if (phase === "gone") return null;
  const more = subtitleHasMore(story);
  return (
    <div className={`world-subtitle ${phase}${expanded ? " expanded" : ""}`} role="status" data-testid={testId} data-phase={phase}>
      <MiscGlyph icon="narrator" size={16} />
      {expanded ? (
        <div className="world-subtitle-full" data-testid={`${testId}-full`}>
          <p>{story.text_zh}</p>
          {(story.more_zh ?? "") !== "" && <p className="world-story-more">{story.more_zh}</p>}
        </div>
      ) : (
        <span className="world-subtitle-line" data-testid={`${testId}-line`}>
          {subtitleLine(story.text_zh)}
        </span>
      )}
      {more && (
        <button type="button" className="world-more-btn small" aria-expanded={expanded} onClick={() => setExpanded((v) => !v)} data-testid={`${testId}-more`}>
          {expanded ? "收起" : "多講一點"}
        </button>
      )}
      {story.source === "fallback" && <FallbackMark />}
    </div>
  );
}

interface DialogProps {
  story: WorldStory;
  speaker: string;
  portrait: NpcPortrait | null;
  region?: string | null;
  testId?: string;
}

export function StoryDialog({ story, speaker, portrait, region, testId = "world-dialog" }: DialogProps) {
  const [state, setState] = useState(() => dialogStart(story));
  const page = state.pages[state.index] ?? "";
  const next = hasNext(state);
  const more = canMore(state, story);
  return (
    <div className="world-dialog" data-testid={testId} data-page={state.index} data-pages={state.pages.length}>
      <Portrait portrait={portrait} region={region ?? null} size={48} label={speaker} />
      <div className="world-dialog-body">
        <div className="world-dialog-name small">
          <b>{speaker}</b>
          {story.source === "fallback" && <FallbackMark testId={`${testId}-fallback`} />}
        </div>
        <button
          type="button"
          className="world-dialog-text"
          onClick={() => setState((s) => dialogNext(s))}
          disabled={!next}
          aria-label={next ? "下一段" : undefined}
          data-testid={`${testId}-text`}
        >
          {page}
          {next && (
            <span className="world-dialog-next" aria-hidden="true" data-testid={`${testId}-next`}>
              ▼
            </span>
          )}
        </button>
        {more && (
          <button type="button" className="world-more-btn small" onClick={() => setState((s) => dialogMore(s, story))} data-testid={`${testId}-more`}>
            多講一點
          </button>
        )}
      </div>
    </div>
  );
}

interface DiceProps {
  dice: readonly number[];
  roll: number;
  outcome: Outcome;
  /** 測試用：動畫已經過了多久（毫秒）；不給＝跟著計時器走。 */
  elapsed?: number;
}

export function DiceRoll({ dice, roll, outcome, elapsed }: DiceProps) {
  const [t, setT] = useState(0);
  useEffect(() => {
    if (elapsed !== undefined) return undefined;
    const start = Date.now();
    const timer = window.setInterval(() => {
      const now = Date.now() - start;
      setT(now);
      if (now >= DICE_MS) window.clearInterval(timer);
    }, DICE_TICK_MS);
    return () => window.clearInterval(timer);
  }, [elapsed]);
  const frame = diceFrame(dice, roll, elapsed ?? t);
  const color = OUTCOME_COLOR[outcome];
  return (
    <div className={`world-dice${frame.done ? " done" : " rolling"}`} data-testid="world-dice" data-done={frame.done ? "1" : "0"} data-outcome={outcome}>
      {frame.faces.map((f, i) => {
        const used = frame.used === i;
        return (
          <span key={i} className={`world-die${used ? " used" : frame.done ? " unused" : ""}`} data-testid="world-die" data-face={f} style={used ? { filter: `drop-shadow(0 0 4px ${color})` } : undefined}>
            <D20 size={42} value={f} color={used ? color : "#f2e6c8"} />
          </span>
        );
      })}
    </div>
  );
}
