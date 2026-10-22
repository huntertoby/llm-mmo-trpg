// 召喚物操控面板（Phase 3-33c，6.29.2）：浮在戰場右上角，列出主角場上的召喚物；
// 每隻有 4 個 0 AP 的模式按鈕（標示目前模式；集火再選一個敵人）與「指揮（1 AP）」。
// 指揮：伺服器給可到達的終點與各終點打得到的敵人，玩家點地圖上的藍格或用下拉清單選終點，
// 再選要打的敵人（或只移動）；滑過按鈕預覽那個指揮。說明一律用共用浮動卡（PartTip，6.5.1），
// 不用原生 title。
// 灌注（Phase 3-33d）：「灌注（1 AP）」→ 伺服器給技能選單（不能灌注的變灰、附中文原因）→ 滑過技能預覽
// 召喚物從自己位置施放的範圍 → 點一下灌注；有待施放的技能時列上顯示「待施放：〔技能〕」。
import { useState } from "react";
import type { Action, BattleView, CommandOption, CommandOptions, InfuseOptions, InfusionPreview, Pos, SkillCard, UnitView } from "../api/types";
import {
  commandAction,
  commandBlocked,
  focusTargets,
  INFUSE_HINT,
  infuseAction,
  infuseBlocked,
  infuseRows,
  infusionPreviewText,
  MODE_HINTS,
  MODE_LABELS,
  MODE_ORDER,
  modeButtons,
  modeText,
  optionAt,
  optionLabel,
  pendingInfusionText,
  setModeAction,
  type SummonMode,
} from "../battle/summonControl";
import { remainingRounds } from "../battle/summons";
import type { UnitNames } from "../battle/units";
import { posKey } from "../battle/geometry";
import { PartTip } from "./PartTip";
import { SkillIconView } from "./SkillIconView";

/** 進行中的灌注：哪隻、伺服器給的技能選單。 */
export interface InfuseSession {
  summonId: string;
  options: InfuseOptions;
}

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
  /** 灌注（3-33d）：進行中的選單、正在取得選單、開始／取消／送出。 */
  infuse: InfuseSession | null;
  loadingInfuse: boolean;
  onStartInfuse(summonId: string): void;
  onCancelInfuse(): void;
  onInfuse(action: Action): void;
  /** 目前滑過的灌注技能的預覽（召喚物會從哪裡、打誰）；沒有時 `null`。 */
  infusePreview?: InfusionPreview | null;
  /** 技能卡（選單的技能圖示用）。 */
  cards?: Readonly<Record<string, SkillCard | undefined>>;
}

const MODES_TIP = MODE_ORDER.map((m) => `${MODE_LABELS[m]}：${MODE_HINTS[m]}`).join("\n");

const TIP_TEXT = `${MODES_TIP}
切換模式不花 AP、可以隨時換；指揮要花 1 AP，讓這隻召喚物立刻走到你指定的格子（用牠自己的移動力）並攻擊，不佔牠自己的回合；每隻每輪最多指揮 1 次。
灌注要花 1 AP：${INFUSE_HINT}`;

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

function InfuseBox({
  session,
  summon,
  hero,
  enabled,
  names,
  cards,
  infusePreview,
  onInfuse,
  onCancelInfuse,
  onPreviewAction,
}: Pick<Props, "hero" | "names" | "enabled" | "cards" | "infusePreview" | "onInfuse" | "onCancelInfuse" | "onPreviewAction"> & {
  session: InfuseSession;
  summon: UnitView;
}) {
  const rows = infuseRows(session.options);
  return (
    <div className="summon-infuse" aria-label={`灌注給 ${summon.name_zh}`}>
      <div className="small muted">選一招技能（花 {session.options.ap_cost} AP＋技能的法力與冷卻）；滑過預覽牠從自己位置施放的範圍。</div>
      {session.options.problem != null && <div className="small summon-infuse-warn">{session.options.problem}</div>}
      <div className="summon-infuse-list" role="group" aria-label="可灌注的技能">
        {rows.length === 0 && <span className="small muted">沒有主動技能。</span>}
        {rows.map((r) => {
          const action = infuseAction(hero.id, summon.id, r.skillId);
          const blocked = !enabled || r.reason !== null;
          return (
            <div key={r.skillId} className="summon-infuse-row">
              <PartTip cat="灌注技能" label={r.name} tip={r.reason ?? "點一下灌注；牠在下一個自己的回合開始時施放。"} pin={false}>
                <button
                  type="button"
                  className={`skill-button infuse-skill${blocked ? " blocked" : ""}`}
                  aria-disabled={blocked}
                  disabled={blocked}
                  onMouseEnter={() => onPreviewAction(blocked ? null : action)}
                  onMouseLeave={() => onPreviewAction(null)}
                  onFocus={() => onPreviewAction(blocked ? null : action)}
                  onBlur={() => onPreviewAction(null)}
                  onClick={() => !blocked && onInfuse(action)}
                >
                  <SkillIconView icon={cards?.[r.skillId]?.icon} size={28} className="skill-button-icon" />
                  <span className="skill-name">{r.name}</span>
                </button>
              </PartTip>
              {r.reason !== null && <span className="small muted infuse-reason">{r.reason}</span>}
            </div>
          );
        })}
      </div>
      {infusePreview != null && infusePreview.summon_id === summon.id && (
        <div className={`small ${infusePreview.no_target ? "summon-infuse-warn" : "summon-infuse-preview"}`}>{infusionPreviewText(infusePreview, names)}</div>
      )}
      <button type="button" className="small-button" onClick={onCancelInfuse}>
        取消灌注
      </button>
      <span className="small muted">　Esc 也可取消</span>
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
        const infusing = props.infuse !== null && props.infuse.summonId === s.id;
        const infuseNo = infuseBlocked(view, hero, s, enabled);
        const pending = pendingInfusionText(s);
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
            {pending !== null && <div className="small summon-pending">{pending}</div>}
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
            <div className="summon-command-row">
              <PartTip cat="灌注技能" label={`灌注（${view.summon_infuse_ap_cost} AP）`} tip={infuseNo ?? INFUSE_HINT} pin={false}>
                <button
                  type="button"
                  disabled={infuseNo !== null || props.loadingInfuse}
                  aria-pressed={infusing}
                  onClick={() => (infusing ? props.onCancelInfuse() : props.onStartInfuse(s.id))}
                >
                  灌注（{view.summon_infuse_ap_cost} AP）
                </button>
              </PartTip>
              {infuseNo !== null && enabled && <span className="muted small">　{infuseNo}</span>}
            </div>
            {infusing && props.infuse !== null && (
              <InfuseBox
                session={props.infuse}
                summon={s}
                hero={hero}
                names={names}
                enabled={enabled}
                cards={props.cards}
                infusePreview={props.infusePreview ?? null}
                onInfuse={props.onInfuse}
                onCancelInfuse={props.onCancelInfuse}
                onPreviewAction={props.onPreviewAction}
              />
            )}
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
