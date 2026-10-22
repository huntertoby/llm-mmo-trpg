// 召喚物操控面板（Phase 3-33c，6.29.2）：浮在戰場右上角，列出主角場上的召喚物；
// 每隻有 4 個 0 AP 的模式按鈕（標示目前模式；集火再選一個敵人）與「指揮（1 AP）」。
// 指揮：伺服器給可到達的終點與各終點打得到的敵人，玩家點地圖上的藍格或用下拉清單選終點，
// 再選要打的敵人（或只移動）；滑過按鈕預覽那個指揮。說明一律用共用浮動卡（PartTip，6.5.1），
// 不用原生 title。
import { useState } from "react";
import type { Action, BattleView, CommandOption, CommandOptions, Pos, UnitView } from "../api/types";
import {
  commandAction,
  commandBlocked,
  focusTargets,
  MODE_HINTS,
  MODE_LABELS,
  MODE_ORDER,
  modeButtons,
  modeText,
  optionAt,
  optionLabel,
  setModeAction,
  type SummonMode,
} from "../battle/summonControl";
import { remainingRounds } from "../battle/summons";
import type { UnitNames } from "../battle/units";
import { posKey } from "../battle/geometry";
import { PartTip } from "./PartTip";

/** 進行中的指揮：哪隻、伺服器給的選項、目前選的終點（`null` ＝ 還沒選）。 */
export interface CommandSession {
  summonId: string;
  options: CommandOptions;
  dest: Pos | null;
}

interface Props {
  view: BattleView;
  hero: UnitView;
  summons: readonly UnitView[];
  names: UnitNames;
  /** 輪到主角、可以送動作。 */
  enabled: boolean;
  command: CommandSession | null;
  /** 正在向伺服器取得指揮選項。 */
  loadingCommand: boolean;
  onSetMode(action: Action): void;
  onStartCommand(summonId: string): void;
  onPickDest(dest: Pos): void;
  onCancelCommand(): void;
  onCommand(action: Action): void;
  /** 滑過指揮按鈕時預覽那個動作（離開時 `null`）。 */
  onPreviewAction(action: Action | null): void;
}

const MODES_TIP = MODE_ORDER.map((m) => `${MODE_LABELS[m]}：${MODE_HINTS[m]}`).join("\n");

const TIP_TEXT = `${MODES_TIP}
切換模式不花 AP、可以隨時換；指揮要花 1 AP，讓這隻召喚物立刻走到你指定的格子（用牠自己的移動力）並攻擊，不佔牠自己的回合；每隻每輪最多指揮 1 次。`;

function ModeRow({ summon, view, names, enabled, onSetMode }: Pick<Props, "view" | "names" | "enabled" | "onSetMode"> & { summon: UnitView }) {
  const [picking, setPicking] = useState(false);
  const buttons = modeButtons(summon, enabled, view);
  const foes = focusTargets(view);
  const heroId = summon.owner_id ?? "";
  return (
    <div className="summon-modes">
      <div className="summon-mode-buttons" role="group" aria-label={`${summon.name_zh}的模式`}>
        {buttons.map((b) => (
          <PartTip key={b.mode} cat="召喚物模式" label={b.label} tip={b.hint} pin={false}>
            <button
              type="button"
              className={`summon-mode${b.current ? " selected" : ""}`}
              aria-pressed={b.current}
              disabled={b.disabled}
              onClick={() => {
                if (b.needsTarget) setPicking((v) => !v);
                else {
                  setPicking(false);
                  onSetMode(setModeAction(heroId, summon.id, b.mode as SummonMode));
                }
              }}
            >
              {b.label}
            </button>
          </PartTip>
        ))}
      </div>
      {picking && (
        <div className="summon-focus-list" role="group" aria-label="選擇集火目標">
          <div className="small muted">選一個敵人集火（0 AP）：</div>
          {foes.map((f) => (
            <button
              key={f.id}
              type="button"
              className="small-button"
              disabled={!enabled || (summon.summon_mode === "focus" && summon.summon_target_id === f.id)}
              onClick={() => {
                setPicking(false);
                onSetMode(setModeAction(heroId, summon.id, "focus", f.id));
              }}
            >
              {names.label(f.id)}
              <span className="muted small">　HP {f.hp}/{f.max_hp}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function CommandBox({
  session,
  summon,
  hero,
  names,
  enabled,
  onPickDest,
  onCancelCommand,
  onCommand,
  onPreviewAction,
}: Pick<Props, "hero" | "names" | "enabled" | "onPickDest" | "onCancelCommand" | "onCommand" | "onPreviewAction"> & {
  session: CommandSession;
  summon: UnitView;
}) {
  const options = session.options.options;
  const chosen: CommandOption | undefined = session.dest === null ? undefined : optionAt(session.options, session.dest);
  const moveAction: Action | null = chosen === undefined ? null : commandAction(hero.id, summon.id, chosen);
  return (
    <div className="summon-command" aria-label={`指揮 ${summon.name_zh}`}>
      <div className="small muted">
        點地圖上的藍格，或從清單選終點；再選要打的敵人（也可以只移動）。花 {session.options.ap_cost} AP。
      </div>
      <select
        aria-label="指揮終點"
        value={session.dest === null ? "" : posKey(session.dest)}
        onChange={(e) => {
          const o = options.find((x) => posKey(x.dest) === e.target.value);
          if (o !== undefined) onPickDest(o.dest);
        }}
      >
        <option value="" disabled>
          選擇終點…
        </option>
        {options.map((o) => (
          <option key={posKey(o.dest)} value={posKey(o.dest)}>
            {optionLabel(o, names)}
          </option>
        ))}
      </select>
      {chosen !== undefined && (
        <div className="summon-command-actions">
          {chosen.targets.map((id) => {
            const action = commandAction(hero.id, summon.id, chosen, id);
            return (
              <button
                key={id}
                type="button"
                className="primary"
                disabled={!enabled || action === null}
                onMouseEnter={() => onPreviewAction(action)}
                onMouseLeave={() => onPreviewAction(null)}
                onClick={() => action !== null && onCommand(action)}
              >
                {chosen.path.length > 1 ? "移動並攻擊 " : "攻擊 "}
                {names.label(id)}
              </button>
            );
          })}
          {moveAction !== null && (
            <button
              type="button"
              disabled={!enabled}
              onMouseEnter={() => onPreviewAction(moveAction)}
              onMouseLeave={() => onPreviewAction(null)}
              onClick={() => onCommand(moveAction)}
            >
              只移動
            </button>
          )}
          {moveAction === null && chosen.targets.length === 0 && <span className="small muted">原地沒有打得到的敵人，請改選終點。</span>}
        </div>
      )}
      <button type="button" className="small-button" onClick={onCancelCommand}>
        取消指揮
      </button>
      <span className="small muted">　Esc／右鍵也可取消</span>
    </div>
  );
}

export function SummonPanel(props: Props) {
  const { view, hero, summons, names, enabled, command, loadingCommand } = props;
  if (summons.length === 0) return null;
  return (
    <div className="panel summon-panel" aria-label="召喚物操控">
      <div className="section-title">
        <PartTip cat="召喚物" label="操控" tip={TIP_TEXT}>
          召喚物操控 ⓘ
        </PartTip>
      </div>
      {summons.map((s) => {
        const blocked = commandBlocked(view, hero, s, enabled);
        const left = remainingRounds(view, s);
        const active = command !== null && command.summonId === s.id;
        return (
          <div key={s.id} className={`summon-row${active ? " commanding" : ""}`}>
            <div className="summon-title">
              <b>{names.label(s.id)}</b>
              <span className="muted small">
                　HP {s.hp}/{s.max_hp}
                {left === null ? "" : `・剩 ${left} 輪`}
              </span>
            </div>
            <div className="small summon-current">
              模式：<b>{modeText(s, names)}</b>
              {s.commanded && <span className="muted">　（本輪已指揮）</span>}
            </div>
            <ModeRow summon={s} view={view} names={names} enabled={enabled} onSetMode={props.onSetMode} />
            <div className="summon-command-row">
              <PartTip cat="召喚物指揮" label={`指揮（${view.summon_command_ap_cost} AP）`} tip={blocked ?? "讓牠立刻走到指定格子並攻擊，不佔牠自己的回合；每隻每輪 1 次。"} pin={false}>
                <button
                  type="button"
                  disabled={blocked !== null || loadingCommand}
                  aria-pressed={active}
                  onClick={() => (active ? props.onCancelCommand() : props.onStartCommand(s.id))}
                >
                  指揮（{view.summon_command_ap_cost} AP）
                </button>
              </PartTip>
              {blocked !== null && !s.commanded && <span className="muted small">　{blocked}</span>}
            </div>
            {active && command !== null && (
              <CommandBox
                session={command}
                summon={s}
                hero={hero}
                names={names}
                enabled={enabled}
                onPickDest={props.onPickDest}
                onCancelCommand={props.onCancelCommand}
                onCommand={props.onCommand}
                onPreviewAction={props.onPreviewAction}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
