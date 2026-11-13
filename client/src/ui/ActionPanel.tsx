// 選取面板（Phase 3-8 起浮在戰場左上角）：選了技能或基本動作之後的目標說明（方向箭頭、自身、取消）
// 與預覽、連鎖。基本動作與技能在底部技能列，結束回合、防禦、備援在右下角（`TurnControls`）。
import { useEffect, useRef } from "react";
import type { Action, BattleView, InteractOption, PreviewOut } from "../api/types";
import { cssColor, type LegendEntry } from "../battle/legend";
import { DIRECTIONS } from "../battle/glossary";
import { compositePickedTag, secondChoices } from "../battle/composite";
import { chainLines, previewLines } from "../battle/previewText";
import { noTurnRows, type NoTurnKind } from "../battle/noTurn";
import { objectStyle } from "../battle/glossary";
import { pickCountText, tileCount } from "../battle/pickCount";
import { PRACTICE_SURE_NOTE_ZH, practiceWording } from "../battle/skillTray";
import {
  DIRECTION_ARROWS,
  DIRECTION_ORDER,
  asideRows,
  compositePromptFor,
  hurlPickedTag,
  hurlLandings,
  hurlPromptText,
  isHurlMode,
  isSelfOnly,
  type ActionMode,
} from "../battle/targeting";
import type { UnitNames } from "../battle/units";
import { Hint } from "./Hint";
import { OpHint } from "./OpHint";
import type { OpHintKind } from "../battle/opHints";

interface Props {
  enabled: boolean;
  mode: ActionMode | null;
  /** 投擲物件的第一段已選好的物件 ID（還在選物件時 `null`）。 */
  hurlPick: string | null;
  /** 投擲物件：放棄已選的物件，回到第一段。 */
  onHurlReset(): void;
  preview: PreviewOut | null;
  view: BattleView;
  /** 主角相鄰可推動物件的互動選項（含不合法與原因；撥開用）。 */
  interactOptions: readonly InteractOption[];
  names: UnitNames;
  /** 目前畫面上需要說明的顏色（複合技能）。 */
  legend: readonly LegendEntry[];
  /** 隊友指令等玩家點目標時的提示（沒有時 `null`）。 */
  orderHint: string | null;
  /** 隊友指令「保護」選取中：可直接保護主角。 */
  onProtectHero: (() => void) | null;
  /** 可以取消選取（技能、基本動作或隊友指令）；複製技能暫停時沒有取消鈕（用對話框的放棄）。 */
  cancellable: boolean;
  onCancel(): void;
  onAction(action: Action): void;
  /** 滑過面板上的按鈕時預覽那個動作（離開時 `null`）。 */
  onPreviewAction(action: Action | null): void;
}

type HelpProps = Pick<
  Props,
  "enabled" | "onAction" | "onPreviewAction" | "interactOptions" | "view" | "hurlPick" | "onHurlReset"
> & {
  mode: ActionMode;
};

/** 複合技能（位移 → 動作）：第 1 段選落點或目標，第 2 段選方向或目標（也可以用這裡的按鈕）。 */
function CompositeHelp({ mode, enabled, view, hurlPick, onHurlReset, onAction, onPreviewAction }: HelpProps) {
  const first = hurlPick === null ? undefined : mode.targets.composite?.get(hurlPick);
  const choices = first === undefined ? [] : secondChoices(first, view);
  return (
    <div className="mode-help">
      <div className="section-title">{mode.label}</div>
      <OpHint
        kind="composite"
        token={mode.key}
        label={mode.label}
        text={practiceWording(compositePromptFor(mode, hurlPick), view.practice)}
        tag={first === undefined ? null : compositePickedTag(first)}
      />
      {choices.length > 0 && (
        <div className="dir-buttons" aria-label="第二段">
          {choices.map(({ second, label }) => (
            <button
              key={second.key}
              type="button"
              disabled={!enabled}
              onMouseEnter={() => onPreviewAction(second.action)}
              onMouseLeave={() => onPreviewAction(null)}
              onClick={() => onAction(second.action)}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      {hurlPick !== null && (
        <button type="button" className="small-button" onClick={onHurlReset}>
          重選落點
        </button>
      )}
    </div>
  );
}

/** 兩段選取（投擲物件、傳送他人、任意兩者互換）的提示與「重選」。 */
function HurlHelp({ mode, view, hurlPick, onHurlReset }: HelpProps) {
  const pickedObject = hurlPick === null ? undefined : view.objects.find((o) => o.id === hurlPick);
  const pickedUnit = hurlPick === null ? undefined : view.units.find((u) => u.id === hurlPick);
  const name = pickedObject !== undefined ? objectStyle(pickedObject.kind).name : (pickedUnit?.name_zh ?? null);
  const seconds = hurlLandings(mode, hurlPick, view).length;
  const kind = mode.targets.pairKind ?? "hurl";
  return (
    <div className="mode-help">
      <div className="section-title">{mode.label}</div>
      <OpHint
        kind="hurl"
        token={mode.key}
        label={mode.label}
        text={practiceWording(hurlPromptText(name, seconds, mode.targets.hurls.size, kind), view.practice)}
        tag={name === null ? null : hurlPickedTag(name, kind)}
      />
      {hurlPick !== null && (
        <button type="button" className="small-button" onClick={onHurlReset}>
          {kind === "hurl" ? "重選物件" : "重選單位"}
        </button>
      )}
    </div>
  );
}

/** 撥開：每個相鄰的可推動物件一列「往左撥／往右撥」；不合法的灰掉並顯示原因。 */
function AsideHelp({ mode, enabled, interactOptions, view, onAction, onPreviewAction }: HelpProps) {
  const rows = asideRows(interactOptions, mode.actions, view);
  return (
    <div className="mode-help">
      <div className="section-title">{mode.label}</div>
      <OpHint kind="aside" token={mode.key} label={mode.label} text="選擇要把物件撥向哪一邊（主角不動；左右以「主角 → 物件」方向為前方）。Esc／右鍵取消。" />
      {rows.map((row) => (
        <div key={row.objectId} className="aside-row">
          <div className="small">{row.name}</div>
          <div className="dir-buttons">
            {row.choices.map((c) => (
              <Hint key={c.side} text={c.reason ?? c.label}>
                <button
                  type="button"
                  disabled={!enabled || c.action === null}
                  onMouseEnter={() => onPreviewAction(c.action)}
                  onMouseLeave={() => onPreviewAction(null)}
                  onClick={() => c.action !== null && onAction(c.action)}
                >
                  {c.label}
                </button>
              </Hint>
            ))}
          </div>
          {row.choices.map(
            (c) =>
              c.reason !== null && (
                <div key={`${c.side}:r`} className="small muted">
                  {c.label}：{c.reason}
                </div>
              ),
          )}
        </div>
      ))}
    </div>
  );
}

/** 一般選目標模式的說明句種類（6A-3：同一種共用「前 3 次」的次數）。 */
export function modeHintKind(mode: ActionMode): OpHintKind {
  if (mode.kind === "vault") return "vault";
  if (mode.kind === "defend" && mode.targets.self !== null) return "defend";
  if (isSelfOnly(mode.targets)) return "self";
  return "target";
}

/** 一般選目標模式的提示文字（攀跳與守護有自己的說法）。 */
export function modeHint(mode: ActionMode): string {
  const t = mode.targets;
  if (mode.kind === "vault") return `點選紫色格子（攀＝爬上高台，跳＝跳過缺口；共 ${tileCount(t.tiles.size)}）。Esc／右鍵取消。`;
  if (mode.kind === "defend" && t.self !== null)
    return `點自己守護自己，或點相鄰的隊友（紅框）改由你替他承受單體攻擊。Esc／右鍵取消。`;
  if (isSelfOnly(t)) return "對自身施放。";
  return `點選格子上的目標（紅框 ${pickCountText(t.units.size + t.objects.size, t.tiles.size)}${t.directions.size > 0 ? "，或選擇方向" : ""}）。Esc／右鍵取消。`;
}

function ModeHelp(props: HelpProps) {
  const { mode, enabled, onAction, onPreviewAction } = props;
  if (mode.kind === "shove_aside") return <AsideHelp {...props} />;
  if (mode.targets.composite !== null) return <CompositeHelp {...props} />;
  if (isHurlMode(mode)) return <HurlHelp {...props} />;
  const t = mode.targets;
  const hint = practiceWording(modeHint(mode), props.view.practice);
  return (
    <div className="mode-help">
      <div className="section-title">{mode.label}</div>
      <OpHint kind={modeHintKind(mode)} token={mode.key} label={mode.label} text={hint} />
      {t.directions.size > 0 && (
        <div className="dir-buttons">
          {DIRECTION_ORDER.map((dir) => {
            const action = t.directions.get(dir);
            return (
              <Hint key={dir} text={`向${DIRECTIONS[dir] ?? dir}`}>
                <button
                  type="button"
                  disabled={!enabled || action === undefined}
                  onMouseEnter={() => onPreviewAction(action ?? null)}
                  onMouseLeave={() => onPreviewAction(null)}
                  onClick={() => action !== undefined && onAction(action)}
                >
                  {DIRECTION_ARROWS[dir]}
                </button>
              </Hint>
            );
          })}
        </div>
      )}
      {t.self !== null && (
        <button
          type="button"
          className="primary"
          disabled={!enabled}
          onMouseEnter={() => onPreviewAction(t.self)}
          onMouseLeave={() => onPreviewAction(null)}
          onClick={() => t.self !== null && onAction(t.self)}
        >
          {isSelfOnly(t) ? "施放" : "施放於自身"}
        </button>
      )}
    </div>
  );
}

interface PreviewContent {
  lines: string[];
  chain: ReturnType<typeof chainLines> | null;
  hasChain: boolean;
  /** BS-2：「背刺・無聲（不會轉身）：盜賊」這幾列（字 → 種類），畫成標籤＋說明卡。 */
  noTurn: ReadonlyMap<string, NoTurnKind>;
}

function previewContent({ preview, view, names }: Pick<Props, "preview" | "view" | "names">): PreviewContent | null {
  const chain = preview === null ? null : chainLines(preview);
  const hasChain = chain !== null && (chain.certain.length > 0 || chain.possible.length > 0);
  const lines = preview === null ? [] : previewLines(preview, names, view, hasChain);
  const noTurn = new Map(preview === null ? [] : noTurnRows(preview, names).map((r) => [r.text, r.kind] as const));
  return lines.length === 0 && !hasChain ? null : { lines, chain, hasChain, noTurn };
}

/** 預覽內容的鍵（內容變了才重新捲動）。 */
function previewKey(content: PreviewContent | null): string {
  if (content === null) return "";
  return [...content.lines, ...(content.chain?.certain ?? []), ...(content.chain?.possible ?? [])].join("\n");
}

/**
 * 6F-20：捲動面板（目前 `scrollTop`，可見範圍 `view`）讓預覽框（`box`，畫面座標）的下緣看得到；
 * 不捲過預覽框的上緣（預覽框比面板高時先看得到上面）。不用捲時照原值。
 */
export function revealScrollTop(scrollTop: number, view: { top: number; bottom: number }, box: { top: number; bottom: number }): number {
  const below = box.bottom - view.bottom;
  if (below <= 0) return scrollTop;
  return scrollTop + Math.max(0, Math.min(below, box.top - view.top));
}

/** 預覽的總覽行（`previewLines` 用「　」接起「命中」「暴擊」「傷害」三段）。 */
const HEAD_PART = /^(命中|暴擊|傷害) /;

/**
 * PR-2b（#147 測試模式；樣張第 3 節第 3 項）：預覽的總覽行拆成各自不換行的段（「傷害 3–10」不拆開），
 * 有命中率時多一行淡金色的必中句（`sure`）。數字照引擎給的（靶場是 100%）。實戰不用這個函式。
 */
export function practicePreviewRows(lines: readonly string[]): { rows: { text: string; parts: string[] | null }[]; sure: boolean } {
  let sure = false;
  const rows = lines.map((text) => {
    const parts = text.split("　");
    if (!parts.every((p) => HEAD_PART.test(p))) return { text, parts: null };
    if (parts.some((p) => p.startsWith("命中 "))) sure = true;
    return { text, parts };
  });
  return { rows, sure };
}

function PracticePreviewLines({ lines }: { lines: readonly string[] }) {
  const { rows, sure } = practicePreviewRows(lines);
  return (
    <ul>
      {rows.map(({ text, parts }, i) =>
        parts === null ? (
          <li key={`${i}:${text}`}>{text}</li>
        ) : (
          <li key={`${i}:${text}`} className="practice-preview-line">
            {parts.map((p) => (
              <span key={p} className="practice-nowrap">
                {p.startsWith("命中 ") ? (
                  <>
                    命中 <b className="practice-sure">{p.slice(3)}</b>
                  </>
                ) : (
                  p
                )}
              </span>
            ))}
          </li>
        ),
      )}
      {sure && (
        <li className="practice-sure-note" data-testid="practice-sure-note">
          {PRACTICE_SURE_NOTE_ZH}
        </li>
      )}
    </ul>
  );
}

/**
 * BS-2：預覽裡「不會轉身」那一列：只畫標籤樣式。BS-2b（美術驗收可修 2）拿掉說明卡：預覽只在滑鼠停在目標上時顯示，
 * 滑鼠移向預覽框預覽就消失，說明卡永遠打不開；同一段說明在出手後的紀錄標籤上看得到。
 */
export function NoTurnLine({ text, kind }: { text: string; kind: NoTurnKind }) {
  return (
    <li className="preview-no-turn" data-no-turn={kind}>
      <span className="no-turn-tag">{text}</span>
    </li>
  );
}

function PreviewBox({ content, practice }: { content: PreviewContent; practice: boolean }) {
  const { lines, chain, hasChain, noTurn } = content;
  return (
    <div className="preview-box" aria-label="預覽">
      <div className="section-title">預覽</div>
      {practice ? (
        <PracticePreviewLines lines={lines} />
      ) : (
        <ul>
          {lines.map((l, i) => {
            const kind = noTurn.get(l);
            return kind === undefined ? <li key={`${i}:${l}`}>{l}</li> : <NoTurnLine key={`${i}:${l}`} text={l} kind={kind} />;
          })}
        </ul>
      )}
      {chain !== null && hasChain && (
        <div className="chain-box" aria-label="可能發生的連鎖">
          <div className="section-title">可能發生的連鎖</div>
          <ul>
            {chain.certain.map((t) => (
              <li key={`c:${t}`}>
                <b>確定</b>　{t}
              </li>
            ))}
            {chain.possible.map((t) => (
              <li key={`p:${t}`}>
                <span className="muted">可能</span>　{t}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** 浮在戰場左上角的選取面板；沒有選取、沒有預覽時不顯示。 */
export function ModePanel(props: Props) {
  const { enabled, mode, preview, view, names, legend, orderHint } = props;
  const content = previewContent({ preview, view, names });
  const panelRef = useRef<HTMLDivElement>(null);
  const contentKey = previewKey(content);
  // 6F-20（美術 PM 6F-19 檢查第 3 節第 3 點：800 寬預覽框最後一行被技能列切掉）：面板放不下時捲到預覽框整個看得到
  useEffect(() => {
    const panel = panelRef.current;
    const box = panel?.querySelector<HTMLElement>(".preview-box");
    if (panel == null || box == null) return;
    const p = panel.getBoundingClientRect();
    const b = box.getBoundingClientRect();
    const cs = getComputedStyle(panel);
    const padB = (parseFloat(cs.paddingBottom) || 0) + (parseFloat(cs.borderBottomWidth) || 0); // 下面的內距也露出來
    panel.scrollTop = revealScrollTop(panel.scrollTop, { top: p.top, bottom: p.bottom - padB }, { top: b.top, bottom: b.bottom });
  }, [contentKey]);
  if (mode === null && orderHint === null && content === null && legend.length === 0) return null;
  return (
    <div ref={panelRef} className="panel mode-panel" aria-label="選取">
      {orderHint !== null && (
        <div className="mode-help">
          <div className="section-title">隊友指令</div>
          <OpHint kind="order" token={orderHint} label="隊友指令" text={practiceWording(`${orderHint} Esc／右鍵取消。`, view.practice)} />
          {props.onProtectHero !== null && (
            <button type="button" onClick={props.onProtectHero}>
              保護主角
            </button>
          )}
        </div>
      )}
      {mode !== null && (
        <ModeHelp
          mode={mode}
          enabled={enabled}
          hurlPick={props.hurlPick}
          onHurlReset={props.onHurlReset}
          interactOptions={props.interactOptions}
          view={view}
          onAction={props.onAction}
          onPreviewAction={props.onPreviewAction}
        />
      )}
      {props.cancellable && (mode !== null || orderHint !== null) && (
        <button data-sfx="ui_cancel" type="button" className="small-button" onClick={props.onCancel}>
          取消選取
        </button>
      )}
      {legend.length > 0 && (
        <div className="mode-legend" aria-label="顏色圖例">
          {legend.map((e) => (
            <span key={e.label} className="legend-item">
              <span className="legend-swatch" style={{ background: cssColor(e.color) }} />
              {e.label}
            </span>
          ))}
        </div>
      )}
      {content !== null && <PreviewBox content={content} practice={view.practice} />}
    </div>
  );
}
