// 事件卡（Phase 5B-5；09 9.6.7 #6、#7、9.6.4）：旁白、解法按鈕、情境判定的輸入與結果。
// 6C-7 去文字化（21.7、docs/archive/art/HUD版面.md 5.7）：
// - 上方一張插圖（`art_url`；沒有時畫事件插圖，6C-ART2 `render/eventArt.ts`），地名一行；
// - 說書人敘事改成對話框（頭像＋一段字），一次一段，按一下下一段，「多講一點」維持；
// - 選項前面加圖示（戰鬥、說服、潛行、調查……），文字只留一行，原本的整句收進說明卡；
// - 情境判定：DC 用骰子圖示＋數字、屬性用圖示，方法與加值來源收進說明；引用的事實收進「線索」圖示；
// - 判定結果：兩顆骰的動畫＋成功失敗的顏色，算式與「兩顆骰：3、5」收進說明，結果敘述改成上方字幕；
//   「（模型關閉：照預設提議）」改成角落的小圖示。
// 說明一律用共用 `Hint`（6.5.1）。規則全在後端：可用的解法、可引用的事實、判定明細都照 `WorldView`。
// 情境判定「第一次送出即定案」：送出後後端清掉事件，回來的是 `situation_result`；送出中整張停用。
// 玩家文字是純資料欄位，後端把它包進 LLM 的 <player_input>（前端不自己包，代決 5B5-5）。
import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import type { WorldEventView, WorldSituationResult, WorldStory } from "../api/types";
import { eventArtBg, eventArtScale, eventArtScene, eventArtUrl, SCENES } from "../render/eventArt";
import { NARRATOR_PORTRAIT } from "../render/portrait";
import { Hint } from "../ui/Hint";
import { PopupFrame, type PopupPlacement } from "../ui/PopupFrame";

/** 事件卡疊在 HUD 中上方的欄裡（位置由欄決定；UI-E2 共用彈窗外觀）。 */
const INLINE: PopupPlacement = { kind: "inline" };
import { attrKey, attrKeys, OUTCOME_COLOR, solutionIcon, solutionLine, SOLUTION_ICON_ZH, type Outcome } from "./narration";
import { DiceRoll, NarratorSubtitle, StoryDialog } from "./StoryParts";
import { WaitScene } from "../ui/WaitScene";
import { AttrIcon, D20, MiscGlyph, SolutionGlyph } from "./StoryIcons";
import { canSubmitAnswer, checkFormula, insertCite, lengthLabel, PLAYER_TEXT_MAX, solutionClick, solutionHint, solutionLabel, toggleCite, waiveLabel } from "./story";

/** 一段旁白（舊的整段顯示；「（模板文字）」只標 LLM 不可用時的降級文字 `fallback`，保底機遇的 `authored` 與 LLM 的不標）。 */
export function StoryBlock({ story, testId = "world-story" }: { story: WorldStory; testId?: string }) {
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

/**
 * 上方插圖（6C-ART2）：`art_url` 有值時仍優先用圖片；否則畫事件插圖（場景照 `art`，沒寫照第一個不是放棄的
 * 選項的圖示挑；背景依區域），離屏畫好的圖片網址依（場景、背景）快取。
 */
function EventArt({ event }: { event: WorldEventView }) {
  const url = event.art_url ?? null;
  const scene = eventArtScene(event);
  const bg = eventArtBg(event.region);
  // QI-6：照插圖實際顯示的寬（含外層 CSS 縮放）× 裝置像素比出圖，小牌、泡泡的 Q 版圖樣才不會被 CSS 縮放拉糊（`eventArtScale`）。量到之前用 2。
  const box = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(2);
  useEffect(() => {
    const el = box.current;
    if (url !== null || el === null || typeof ResizeObserver === "undefined") return undefined;
    const measure = () => setScale(eventArtScale(el.getBoundingClientRect().width, window.devicePixelRatio || 1));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [url]);
  const drawn = url === null ? eventArtUrl(scene, bg, scale) : null;
  const src = url ?? drawn;
  const style: CSSProperties = src !== null ? { backgroundImage: `url(${src})` } : {};
  return (
    <div
      ref={box}
      className={`world-event-art${url === null ? " drawn" : ""}`}
      style={style}
      data-testid="world-event-art"
      data-art={url !== null ? "image" : "scene"}
      data-scene={url === null ? scene : undefined}
      data-bg={url === null ? bg : undefined}
      role="img"
      aria-label={url === null ? SCENES[scene].zh : undefined}
    >
      <div className="world-event-art-title">
        <Hint text={`${event.actor_zh}：${event.motive_zh}`}>
          <b tabIndex={0}>{event.location_name_zh}</b>
        </Hint>
        {event.follows_zh != null && (
          <Hint text={`接著線頭：${event.follows_zh}`}>
            <span className="world-event-thread" tabIndex={0} data-testid="world-event-thread">
              <MiscGlyph icon="thread" size={14} />
            </span>
          </Hint>
        )}
        <Hint text={event.leave_zh}>
          <span className="world-event-info" tabIndex={0} data-testid="world-event-leave">
            <MiscGlyph icon="info" size={14} />
          </span>
        </Hint>
      </div>
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
    <PopupFrame placement={INLINE} className="world-event" testId="world-event" role="region" label={`事件：${event.location_name_zh}`}>
      <EventArt event={event} />
      {event.story != null && <StoryDialog key={event.story.text_zh} story={event.story} speaker="說書人" portrait={NARRATOR_PORTRAIT} testId="world-event-story" />}
      <div className="world-event-solutions">
        {event.solutions.map((s) => {
          const click = solutionClick(s);
          const waive = waiveLabel(s);
          const icon = solutionIcon(s);
          const hint = `${solutionLabel(s)}\n${solutionHint(s)}`;
          return (
            <span key={s.index} className="world-solution-group">
              <Hint text={hint}>
                <button
                  type="button"
                  className={`world-solution${click?.kind === "open" && situation?.template === click.template ? " primary" : ""}`}
                  disabled={busy || !s.available || click === null}
                  onClick={() => {
                    if (click?.kind === "open") onOpen(click.template);
                    else if (click?.kind === "solve") onSolve(click.solution, null);
                  }}
                  aria-label={`${SOLUTION_ICON_ZH[icon]}：${solutionLine(s)}`}
                  data-testid="world-solution"
                  data-kind={s.kind}
                  data-icon={icon}
                >
                  <SolutionGlyph icon={icon} size={24} />
                  <span className="world-solution-line">{solutionLine(s)}</span>
                  {s.kind === "parley" && s.cost_supplies > 0 && <span className="world-solution-cost small">−{s.cost_supplies} 補給</span>}
                </button>
              </Hint>
              {waive !== null && (
                <Hint text="用掉這條線頭代替付出補給（線頭用掉就沒了）">
                  <button type="button" disabled={busy || s.waive_thread == null} onClick={() => onSolve(s.index, s.waive_thread ?? null)} data-testid="world-solution-waive">
                    {waive}
                  </button>
                </Hint>
              )}
            </span>
          );
        })}
      </div>
      {situation !== null && <SituationForm key={situation.template} event={event} busy={busy} onAnswer={onAnswer} />}
    </PopupFrame>
  );
}

/** 屬性圖示一排（說明卡是屬性名）；不認得的屬性名直接寫字。 */
function AttrRow({ text }: { text: string }) {
  const names = text.split(/[、,，／/]/u).filter((n) => n.trim() !== "");
  return (
    <span className="world-attr-row" data-testid="world-attrs">
      {names.map((n) => {
        const key = attrKey(n);
        return (
          <Hint key={n} text={`可用屬性：${n}`}>
            <span className="world-attr" tabIndex={0} data-attr={key ?? n}>
              {key !== null ? <AttrIcon attr={key} /> : <span className="small">{n}</span>}
            </span>
          </Hint>
        );
      })}
    </span>
  );
}

function SituationForm({ event, busy, onAnswer }: Pick<EventProps, "event" | "busy" | "onAnswer">) {
  const situation = event.situation!;
  const [text, setText] = useState("");
  const [cited, setCited] = useState<string[]>([]);
  const [cluesOpen, setCluesOpen] = useState(false);
  /** RT-3：按了「擲骰」（等說書人判定時畫沙漏；送出失敗、還留在這張卡上＝失敗狀態加重試）。 */
  const [sent, setSent] = useState(false);
  /** RT-3b：沙漏出現、失敗出現重試鈕時，連「擲骰」這一列一起捲進事件卡的可視範圍。 */
  const actions = useRef<HTMLDivElement | null>(null);
  const submit = () => {
    setSent(true);
    onAnswer(situation.template, text, cited);
  };
  const facts = situation.facts ?? [];
  const icon = solutionIcon({ kind: "situation", note_zh: situation.note_zh, attributes_zh: situation.attributes_zh });
  return (
    <div className="world-situation" data-testid="world-situation">
      <div className="world-situation-head">
        <SolutionGlyph icon={icon} size={24} />
        <b className="world-situation-note">{situation.note_zh}</b>
        <Hint text={`基準難度 ${situation.base_dc}（引用的線索、種族會調整）`}>
          <span className="world-dc" tabIndex={0} data-testid="world-dc" data-dc={situation.base_dc}>
            <D20 size={24} />
            <b>{situation.base_dc}</b>
          </span>
        </Hint>
        <AttrRow text={situation.attributes_zh} />
        <Hint text={`方法：${situation.methods_zh}`}>
          <span className="world-event-info" tabIndex={0} data-testid="world-methods">
            <MiscGlyph icon="info" size={14} />
          </span>
        </Hint>
        {facts.length > 0 && (
          <Hint text={`線索：你持有的線索與往來 ${facts.length} 筆（點開來引用；回答裡要提到它，遊戲核對得到才 +1，最多 +2）`}>
            <button type="button" className={`world-clue-btn${cluesOpen ? " on" : ""}`} aria-expanded={cluesOpen} aria-label={`線索 ${facts.length} 筆`} onClick={() => setCluesOpen((v) => !v)} data-testid="world-clues">
              <MiscGlyph icon="clue" size={16} />
              <span className="small">{cited.length > 0 ? `${cited.length}／${facts.length}` : facts.length}</span>
            </button>
          </Hint>
        )}
      </div>
      {situation.story != null && <StoryDialog key={situation.story.text_zh} story={situation.story} speaker="說書人" portrait={NARRATOR_PORTRAIT} testId="world-situation-story" />}
      {sent && (
        <div className="world-situation-wait">
          <WaitScene scene="judge" requestId={`judge:${situation.template}`} region={event.region ?? null} status={busy ? "wait" : "fail"} onRetry={submit} revealUntil={actions} testId="world-judge-wait" />
        </div>
      )}
      {facts.length > 0 && cluesOpen && (
        <div className="world-cites" data-testid="world-cites">
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
      <textarea
        id="world-answer"
        className="world-answer"
        rows={3}
        maxLength={PLAYER_TEXT_MAX}
        value={text}
        disabled={busy}
        onChange={(e) => setText(e.target.value)}
        aria-label="你打算怎麼做？"
        placeholder="你打算怎麼做？（文字不換強度，只決定用哪個屬性與方法）"
        data-testid="world-answer"
      />
      <div className="run-actions" ref={actions}>
        <span className="muted small">{lengthLabel(text)}</span>
        <Hint text="送出後就定案，不能重來">
          <button type="button" className="primary" disabled={!canSubmitAnswer(text, busy)} onClick={submit} data-testid="world-answer-submit">
            <D20 size={16} /> 擲骰
          </button>
        </Hint>
      </div>
    </div>
  );
}

/** 判定明細的說明卡：算式＋兩顆骰＋用心的明細。 */
export function resultHint(result: WorldSituationResult): string {
  const lines = [checkFormula(result), `兩顆骰：${result.dice.join("、")}（${result.mode_zh}）`, `屬性：${result.attribute_zh}・方法：${result.method_zh}`];
  return lines.join("\n");
}

/** 判定結果（這次請求的 `situation_result`；前端保留到下一個動作）。 */
export function SituationResultCard({ result, onClose, diceElapsed }: { result: WorldSituationResult; onClose(): void; diceElapsed?: number }) {
  const [storyOpen, setStoryOpen] = useState(false);
  const outcome = result.outcome as Outcome;
  const color = OUTCOME_COLOR[outcome] ?? OUTCOME_COLOR.failure;
  const attrs = attrKeys(result.attribute_zh);
  const counted = result.care.filter((c) => c.counted).length;
  return (
    <>
      {result.story != null && <NarratorSubtitle key={result.story.text_zh} story={result.story} testId="world-result-story" />}
      <div className={`panel world-result outcome-${result.outcome}`} style={{ borderColor: color }} data-testid="world-result" role="region" aria-label={`判定結果：${result.outcome_zh}`}>
        {result.source === "fallback" && (
          <Hint text="模型關閉：照預設提議">
            <span className="world-result-corner" tabIndex={0} data-testid="world-result-fallback">
              <MiscGlyph icon="model_off" size={14} />
            </span>
          </Hint>
        )}
        <div className="world-result-head">
          <b className="world-result-outcome" style={{ color }}>
            {result.outcome_zh}
          </b>
          <span className="muted small world-situation-note">{result.note_zh}</span>
        </div>
        <DiceRoll dice={result.dice} roll={result.roll} outcome={outcome} elapsed={diceElapsed} />
        <Hint text={resultHint(result)}>
          <div className="world-result-sum" tabIndex={0} data-testid="world-result-formula" aria-label={checkFormula(result)}>
            {attrs[0] !== undefined ? <AttrIcon attr={attrs[0]} size={18} /> : <span className="small">{result.attribute_zh}</span>}
            <b style={{ color }}>{result.total}</b>
            <span className="muted small">vs</span>
            <D20 size={20} />
            <b>{result.dc}</b>
            <MiscGlyph icon="info" size={12} />
          </div>
        </Hint>
        {result.care.length > 0 && (
          <Hint text={result.care.map((c) => `${c.counted ? "✔" : "✘"} 〔${c.item_zh}〕${c.text_zh}${!c.counted && c.reason_zh !== "" ? `（${c.reason_zh}）` : ""}`).join("\n")}>
            <span className="world-result-clues" tabIndex={0} data-testid="world-result-clues">
              <MiscGlyph icon="clue" size={16} />
              <span className="small">
                {counted}／{result.care.length}
              </span>
            </span>
          </Hint>
        )}
        {result.effects_zh.length > 0 && (
          <ul className="small world-effects">
            {result.effects_zh.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        )}
        {storyOpen && result.story != null && <StoryDialog story={result.story} speaker="說書人" portrait={NARRATOR_PORTRAIT} testId="world-result-dialog" />}
        <div className="run-actions">
          {result.story != null && (
            <Hint text="再看一次說書人的敘述">
              <button type="button" aria-pressed={storyOpen} onClick={() => setStoryOpen((v) => !v)} data-testid="world-result-story-open">
                <MiscGlyph icon="narrator" size={14} />
              </button>
            </Hint>
          )}
          <button type="button" onClick={onClose} data-testid="world-result-close">
            知道了
          </button>
        </div>
      </div>
    </>
  );
}

