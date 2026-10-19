// 操作面板：基本動作（攻擊、推擊、絆倒、推動物件、防禦、結束姿態、起身）、結束回合；
// 選了技能或基本動作之後的目標說明（方向箭頭、自身、取消）與預覽；備援的「其他動作」清單（收合）。
import type { Action, BattleView, InteractOption, PreviewOut } from "../api/types";
import type { LabeledAction } from "../battle/actions";
import { DIRECTIONS } from "../battle/glossary";
import { chainLines, previewLines } from "../battle/previewText";
import { objectStyle } from "../battle/glossary";
import {
  DIRECTION_ARROWS,
  DIRECTION_ORDER,
  asideRows,
  hurlLandings,
  hurlPromptText,
  isHurlMode,
  isSelfOnly,
  type ActionMode,
} from "../battle/targeting";
import type { UnitNames } from "../battle/units";

interface Props {
  enabled: boolean;
  basic: readonly ActionMode[];
  mode: ActionMode | null;
  /** 投擲物件的第一段已選好的物件 ID（還在選物件時 `null`）。 */
  hurlPick: string | null;
  /** 投擲物件：放棄已選的物件，回到第一段。 */
  onHurlReset(): void;
  endTurn: Action | null;
  fallback: readonly LabeledAction[];
  moveCount: number;
  attackCount: number;
  preview: PreviewOut | null;
  view: BattleView;
  /** 主角相鄰可推動物件的互動選項（含不合法與原因；撥開用）。 */
  interactOptions: readonly InteractOption[];
  names: UnitNames;
  onPickMode(mode: ActionMode): void;
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

/** 投擲物件：兩段選取的提示（第 1 段選物件、第 2 段選落點）與「重選物件」。 */
function HurlHelp({ mode, view, hurlPick, onHurlReset }: HelpProps) {
  const picked = hurlPick === null ? undefined : view.objects.find((o) => o.id === hurlPick);
  const name = picked === undefined ? null : objectStyle(picked.kind).name;
  const landings = hurlLandings(mode, hurlPick).length;
  return (
    <div className="mode-help">
      <div className="section-title">{mode.label}</div>
      <div className="small muted">{hurlPromptText(name, landings, mode.targets.hurls.size)}</div>
      {hurlPick !== null && (
        <button type="button" className="small-button" onClick={onHurlReset}>
          重選物件
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
              <button
                key={c.side}
                type="button"
                disabled={!enabled || c.action === null}
                title={c.reason ?? c.label}
                onMouseEnter={() => onPreviewAction(c.action)}
                onMouseLeave={() => onPreviewAction(null)}
                onClick={() => c.action !== null && onAction(c.action)}
              >
                {c.label}
              </button>
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

function ModeHelp(props: HelpProps) {
  const { mode, enabled, onAction, onPreviewAction } = props;
  if (mode.kind === "shove_aside") return <AsideHelp {...props} />;
  if (isHurlMode(mode)) return <HurlHelp {...props} />;
  const t = mode.targets;
  const pickable = t.units.size + t.objects.size + t.tiles.size;
  const hint = isSelfOnly(t)
    ? "對自身施放。"
    : `點選格子上的目標（紅框 ${pickable} 個${t.directions.size > 0 ? "，或選擇方向" : ""}）。Esc／右鍵取消。`;
  return (
    <div className="mode-help">
      <div className="section-title">{mode.label}</div>
      <div className="small muted">{hint}</div>
      {t.directions.size > 0 && (
        <div className="dir-buttons">
          {DIRECTION_ORDER.map((dir) => {
            const action = t.directions.get(dir);
            return (
              <button
                key={dir}
                type="button"
                disabled={!enabled || action === undefined}
                title={`向${DIRECTIONS[dir] ?? dir}`}
                onMouseEnter={() => onPreviewAction(action ?? null)}
                onMouseLeave={() => onPreviewAction(null)}
                onClick={() => action !== undefined && onAction(action)}
              >
                {DIRECTION_ARROWS[dir]}
              </button>
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

export function ActionPanel(props: Props) {
  const { enabled, basic, mode, endTurn, fallback, preview, view, names } = props;
  const chain = preview === null ? null : chainLines(preview);
  const hasChain = chain !== null && (chain.certain.length > 0 || chain.possible.length > 0);
  const lines = preview === null ? [] : previewLines(preview, names, view, hasChain);
  return (
    <div className="panel action-panel">
      <div className="action-hint">
        {enabled
          ? `點選藍色格子移動（${props.moveCount} 格），點選紅框敵人攻擊（${props.attackCount} 個）。`
          : "等待中……"}
      </div>
      <div className="mode-buttons">
        {basic.map((m) => (
          <button
            key={m.key}
            type="button"
            className={mode?.key === m.key ? "selected" : ""}
            disabled={!enabled}
            onClick={() => props.onPickMode(m)}
          >
            {m.label}
          </button>
        ))}
        <button
          type="button"
          className="primary"
          disabled={!enabled || endTurn === null}
          onClick={() => endTurn !== null && props.onAction(endTurn)}
        >
          結束回合
        </button>
      </div>
      {mode !== null && (
        <>
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
          <button type="button" className="small-button" onClick={props.onCancel}>
            取消選取
          </button>
        </>
      )}
      {(lines.length > 0 || hasChain) && (
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
      )}
      <details className="fallback">
        <summary>其他動作（備援，{fallback.length}）</summary>
        <ul className="action-list">
          {fallback.length === 0 && <li className="muted">（無）</li>}
          {fallback.map((o, i) => (
            <li key={`${i}:${o.label}`}>
              <button type="button" disabled={!enabled} onClick={() => props.onAction(o.action)}>
                {o.label}
              </button>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
