// 選取面板（Phase 3-8 起浮在戰場左上角）：選了技能或基本動作之後的目標說明（方向箭頭、自身、取消）
// 與預覽、連鎖。基本動作與技能在底部技能列，結束回合、防禦、備援在右下角（`TurnControls`）。
import type { Action, BattleView, InteractOption, PreviewOut } from "../api/types";
import { cssColor, type LegendEntry } from "../battle/legend";
import { DIRECTIONS } from "../battle/glossary";
import { secondChoices } from "../battle/composite";
import { chainLines, previewLines } from "../battle/previewText";
import { objectStyle } from "../battle/glossary";
import {
  DIRECTION_ARROWS,
  DIRECTION_ORDER,
  asideRows,
  compositePromptFor,
  hurlLandings,
  hurlPromptText,
  isHurlMode,
  isSelfOnly,
  type ActionMode,
} from "../battle/targeting";
import type { UnitNames } from "../battle/units";
import { Hint } from "./Hint";

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
      <div className="small muted">{compositePromptFor(mode, hurlPick)}</div>
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
      <div className="small muted">{hurlPromptText(name, seconds, mode.targets.hurls.size, kind)}</div>
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
      <div className="small muted">選擇要把物件撥向哪一邊（主角不動；左右以「主角 → 物件」方向為前方）。Esc／右鍵取消。</div>
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

/** 一般選目標模式的提示文字（攀跳與守護有自己的說法）。 */
function modeHint(mode: ActionMode, pickable: number): string {
  const t = mode.targets;
  if (mode.kind === "vault") return `點選紫色格子（攀＝爬上高台，跳＝跳過缺口；共 ${pickable} 個）。Esc／右鍵取消。`;
  if (mode.kind === "defend" && t.self !== null)
    return `點自己守護自己，或點相鄰的隊友（紅框）改由你替他承受單體攻擊。Esc／右鍵取消。`;
  if (isSelfOnly(t)) return "對自身施放。";
  return `點選格子上的目標（紅框 ${pickable} 個${t.directions.size > 0 ? "，或選擇方向" : ""}）。Esc／右鍵取消。`;
}

function ModeHelp(props: HelpProps) {
  const { mode, enabled, onAction, onPreviewAction } = props;
  if (mode.kind === "shove_aside") return <AsideHelp {...props} />;
  if (mode.targets.composite !== null) return <CompositeHelp {...props} />;
  if (isHurlMode(mode)) return <HurlHelp {...props} />;
  const t = mode.targets;
  const pickable = t.units.size + t.objects.size + t.tiles.size;
  const hint = modeHint(mode, pickable);
  return (
    <div className="mode-help">
      <div className="section-title">{mode.label}</div>
      <div className="small muted">{hint}</div>
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
}

function previewContent({ preview, view, names }: Pick<Props, "preview" | "view" | "names">): PreviewContent | null {
  const chain = preview === null ? null : chainLines(preview);
  const hasChain = chain !== null && (chain.certain.length > 0 || chain.possible.length > 0);
  const lines = preview === null ? [] : previewLines(preview, names, view, hasChain);
  return lines.length === 0 && !hasChain ? null : { lines, chain, hasChain };
}

function PreviewBox({ content }: { content: PreviewContent }) {
  const { lines, chain, hasChain } = content;
  return (
    <div className="preview-box" aria-label="預覽">
      <div className="section-title">預覽</div>
      <ul>
        {lines.map((l, i) => (
          <li key={`${i}:${l}`}>{l}</li>
        ))}
      </ul>
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
  if (mode === null && orderHint === null && content === null && legend.length === 0) return null;
  return (
    <div className="panel mode-panel" aria-label="選取">
      {orderHint !== null && (
        <div className="mode-help">
          <div className="section-title">隊友指令</div>
          <div className="small muted">{orderHint} Esc／右鍵取消。</div>
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
        <button type="button" className="small-button" onClick={props.onCancel}>
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
      {content !== null && <PreviewBox content={content} />}
    </div>
  );
}
