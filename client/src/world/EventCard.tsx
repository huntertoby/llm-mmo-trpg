// 事件卡（Phase 5B-5；09 9.6.7 #6、#7、9.6.4）：旁白（1～3 句，可「多講一點」）、解法按鈕、情境判定的輸入與結果。
// 一般面板（不是浮動卡）；說明一律用共用 `Hint`（6.5.1）。規則全在後端：可用的解法、可引用的事實、判定明細都照 `WorldView`。
// 情境判定「第一次送出即定案」：送出後後端清掉事件，回來的是 `situation_result`；送出中整張停用。
// 玩家文字是純資料欄位，後端把它包進 LLM 的 <player_input>（前端不自己包，代決 5B5-5）。
import { useState } from "react";
import type { WorldEventView, WorldSituationResult, WorldStory } from "../api/types";
import { Hint } from "../ui/Hint";
import { canSubmitAnswer, checkFormula, insertCite, lengthLabel, PLAYER_TEXT_MAX, solutionClick, solutionHint, solutionLabel, toggleCite, waiveLabel } from "./story";

function StoryBlock({ story, testId }: { story: WorldStory; testId: string }) {
  const [more, setMore] = useState(false);
  return (
    <div className="world-story" data-testid={testId}>
      <p>{story.text_zh}</p>
      {story.more_zh !== "" && story.more_zh !== undefined && (
        <>
          {more && <p className="world-story-more">{story.more_zh}</p>}
          <button type="button" className="world-more-btn small" aria-expanded={more} onClick={() => setMore((v) => !v)} data-testid={`${testId}-more`}>
            {more ? "收起" : "多講一點"}
          </button>
        </>
      )}
      {story.source === "fallback" && <span className="muted small world-story-src">（模板文字）</span>}
    </div>
  );
}

interface EventProps {
  event: WorldEventView;
  busy: boolean;
  onOpen(template: string): void;
  /** 放棄、交涉、戰鬥解法（`event_solve`）；交涉可帶線頭抵掉付出。 */
  onSolve(solution: number, useThread: string | null): void;
  onAnswer(template: string, text: string, cite: string[]): void;
}

export function EventCard({ event, busy, onOpen, onSolve, onAnswer }: EventProps) {
  const situation = event.situation ?? null;
  return (
    <div className="panel world-event" data-testid="world-event" role="region" aria-label="事件">
      <div className="section-title">事件：{event.location_name_zh}</div>
      <div className="small world-event-actor">
        <b>{event.actor_zh}</b>
        <span className="muted">　{event.motive_zh}</span>
      </div>
      {event.story != null && <StoryBlock story={event.story} testId="world-event-story" />}
      {event.follows_zh != null && <div className="muted small">接著線頭：{event.follows_zh}</div>}
      <div className="world-event-solutions">
        {event.solutions.map((s) => {
          const click = solutionClick(s);
          const waive = waiveLabel(s);
          return (
            <span key={s.index} className="world-solution-group">
              <Hint text={solutionHint(s)}>
                <button
                  type="button"
                  className={click?.kind === "open" && situation?.template === click.template ? "primary" : ""}
                  disabled={busy || !s.available || click === null}
                  onClick={() => {
                    if (click?.kind === "open") onOpen(click.template);
                    else if (click?.kind === "solve") onSolve(click.solution, null);
                  }}
                  data-testid="world-solution"
                  data-kind={s.kind}
                >
                  {solutionLabel(s)}
                  {!s.available && <span className="small muted">（{s.unavailable_zh ?? "不能用"}）</span>}
                </button>
              </Hint>
              {waive !== null && (
                <Hint text="用掉這條線頭代替付出補給（線頭用掉就沒了）">
                  <button
                    type="button"
                    disabled={busy || s.waive_thread == null}
                    onClick={() => onSolve(s.index, s.waive_thread ?? null)}
                    data-testid="world-solution-waive"
                  >
                    {waive}
                  </button>
                </Hint>
              )}
            </span>
          );
        })}
      </div>
      <div className="muted small">{event.leave_zh}</div>
      {situation !== null && (
        <SituationForm key={situation.template} event={event} busy={busy} onAnswer={onAnswer} />
      )}
    </div>
  );
}

function SituationForm({ event, busy, onAnswer }: Pick<EventProps, "event" | "busy" | "onAnswer">) {
  const situation = event.situation!;
  const [text, setText] = useState("");
  const [cited, setCited] = useState<string[]>([]);
  const facts = situation.facts ?? [];
  return (
    <div className="world-situation" data-testid="world-situation">
      <div className="section-title small">情境判定：{situation.note_zh}</div>
      {situation.story != null && <StoryBlock story={situation.story} testId="world-situation-story" />}
      <div className="muted small">
        可用屬性：{situation.attributes_zh}・方法：{situation.methods_zh}・基準難度 {situation.base_dc}
      </div>
      {facts.length > 0 && (
        <div className="world-cites" data-testid="world-cites">
          <div className="small">你持有的線索與往來（點一下引用，再點取消）：</div>
          {facts.map((f) => (
            <Hint key={f.fact} text={`${f.item_zh}：引用時會把「${f.insert_zh ?? f.text_zh}」寫進回答；回答裡要提到它，遊戲核對得到才 +1（最多 +2）`}>
              <button
                type="button"
                className={`world-cite${cited.includes(f.fact) ? " on" : ""}`}
                aria-pressed={cited.includes(f.fact)}
                disabled={busy}
                onClick={() => {
                  const next = toggleCite(cited, f.fact);
                  if (next.includes(f.fact) && !cited.includes(f.fact)) setText((cur) => insertCite(cur, f.insert_zh));
                  setCited(next);
                }}
                data-testid="world-cite"
              >
                〔{f.item_zh}〕{f.text_zh}
              </button>
            </Hint>
          ))}
        </div>
      )}
      <label className="small world-answer-label" htmlFor="world-answer">
        你打算怎麼做？
      </label>
      <textarea
        id="world-answer"
        className="world-answer"
        rows={3}
        maxLength={PLAYER_TEXT_MAX}
        value={text}
        disabled={busy}
        onChange={(e) => setText(e.target.value)}
        placeholder="用自己的話寫：用什麼方法、怎麼做（文字不換強度，只決定用哪個屬性與方法）"
        data-testid="world-answer"
      />
      <div className="muted small">
        {lengthLabel(text)}
        {cited.length > 0 && `・引用 ${cited.length} 筆`}
      </div>
      <div className="run-actions">
        <button
          type="button"
          className="primary"
          disabled={!canSubmitAnswer(text, busy)}
          onClick={() => onAnswer(situation.template, text, cited)}
          data-testid="world-answer-submit"
        >
          送出（送出後就定案，不能重來）
        </button>
      </div>
    </div>
  );
}

/** 判定結果（這次請求的 `situation_result`；前端保留到下一個動作）。 */
export function SituationResultCard({ result, onClose }: { result: WorldSituationResult; onClose(): void }) {
  return (
    <div className={`panel world-result outcome-${result.outcome}`} data-testid="world-result" role="region" aria-label="判定結果">
      <div className="section-title">
        判定結果：{result.outcome_zh}　<span className="muted small">{result.note_zh}</span>
      </div>
      <div className="small">
        {result.attribute_zh}・{result.method_zh}
        {result.source === "fallback" && <span className="muted">（模型關閉：照預設提議）</span>}
      </div>
      <div className="small" data-testid="world-result-formula">
        {checkFormula(result)}
      </div>
      <div className="muted small">兩顆骰：{result.dice.join("、")}</div>
      {result.care.length > 0 && (
        <ul className="small world-care">
          {result.care.map((c, i) => (
            <li key={i} className={c.counted ? "counted" : "missed"}>
              {c.counted ? "✔" : "✘"} 〔{c.item_zh}〕{c.text_zh}
              {!c.counted && c.reason_zh !== "" && <span className="muted">（{c.reason_zh}）</span>}
            </li>
          ))}
        </ul>
      )}
      {result.story != null && <StoryBlock story={result.story} testId="world-result-story" />}
      {result.effects_zh.length > 0 && (
        <ul className="small world-effects">
          {result.effects_zh.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
      <div className="run-actions">
        <button type="button" onClick={onClose} data-testid="world-result-close">
          知道了
        </button>
      </div>
    </div>
  );
}
