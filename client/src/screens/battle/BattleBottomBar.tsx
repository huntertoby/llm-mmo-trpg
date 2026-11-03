// 戰鬥畫面的底部列（由 BattleScreen 抽出，Phase 3T-7；6A-4e 起是版面 A 戰鬥版的底部）：中間技能列、右下回合操作
// （戰鬥結束後換成結束面板）。主角狀態卡移到左上（`BattleScreen` 的 `.bhud-left`）。

import type { RefObject } from "react";
import type { Action, BattleResponse, BattleView, SkillCard, UnitView } from "../../api/types";
import type { ClassifiedActions, LabeledAction } from "../../battle/actions";
import type { PlaySpeed } from "../../battle/playback";
import { runButton } from "../../battle/runAction";
import { blockedMessage } from "../../battle/skillReasons";
import { actionHintKind, actionHintText } from "../../battle/skillTray";
import { hasControllableSummon } from "../../battle/summons";
import { moreModes, TRAY_KINDS, type ActionMode, type SkillButton } from "../../battle/targeting";
import { EndPanel } from "../../ui/EndPanel";
import { SkillBar } from "../../ui/SkillBar";
import { SpeedControl } from "../../ui/SpeedControl";
import { TurnControls } from "../../ui/TurnControls";

interface Props {
  /** 量底部列高度用（戰場、左下紀錄讓開）。 */
  rootRef?: RefObject<HTMLDivElement>;
  response: BattleResponse;
  view: BattleView;
  hero: UnitView | null;
  cards: Readonly<Record<string, SkillCard | undefined>>;
  narrow: boolean;
  classified: ClassifiedActions;
  basic: ActionMode[];
  raceModeList: ActionMode[];
  buttons: SkillButton[];
  fallback: LabeledAction[];
  mode: ActionMode | null;
  canAct: boolean;
  copying: boolean;
  ended: boolean;
  exitLabel: string | undefined;
  /** 結束面板的中性勝負文字（循環賽重播，5F-4b）。 */
  endTitle?: string;
  onExit(): void;
  speed: PlaySpeed;
  playing: boolean;
  onSpeed(s: PlaySpeed): void;
  onSkipNow(): void;
  onPickMode(m: ActionMode): void;
  onPickSkill(skillId: string): void;
  onHint(text: string | null): void;
  onCancel(): void;
  onAct(a: Action): void;
  onPreviewAction(a: Action | null): void;
}

export function BattleBottomBar(p: Props) {
  const { narrow, classified, basic, mode, copying, canAct, hero, view } = p;
  const attackMode = basic.find((m) => m.kind === "attack") ?? null;
  const defendMode = basic.find((m) => m.kind === "defend") ?? null;
  const sprintMode = basic.find((m) => m.kind === "run") ?? null;
  const runReason = runButton(sprintMode, p.response.run_option).reason;
  const hintState = {
    copying,
    canAct,
    ended: p.ended,
    moveCount: classified.moves.size,
    attackCount: classified.attacks.size,
    summonIdle:
      hero !== null &&
      classified.endTurn !== null &&
      classified.moves.size === 0 &&
      classified.attacks.size === 0 &&
      classified.others.length === 0 &&
      hasControllableSummon(view, hero.id),
  };
  // 6A-3：操作說明句每一輪只算一次（同一輪中途「等待中」再回來不多記）
  const hintKind = actionHintKind(hintState);
  return (
    <div className={`battle-bottom${narrow ? " short" : ""}`} ref={p.rootRef}>
      <SkillBar
        basic={basic.filter((m) => TRAY_KINDS.includes(m.kind))}
        race={hero?.race ?? null}
        raceModes={p.raceModeList}
        buttons={p.buttons}
        cards={p.cards}
        selectedKey={mode?.key ?? null}
        enabled={canAct}
        hint={actionHintText(hintState)}
        hintOnce={hintKind === null ? null : { kind: hintKind, token: `${p.response.battle_id}:${view.round}` }}
        onPickMode={p.onPickMode}
        onSelect={p.onPickSkill}
        onBlocked={(b) => p.onHint(blockedMessage(b))}
        onBlockedMode={p.onHint}
      />
      <div className="battle-turn">
        {p.ended ? (
          <EndPanel response={p.response} onRestart={p.onExit} restartLabel={p.exitLabel} heading={p.endTitle} />
        ) : (
          <TurnControls
            enabled={canAct}
            endTurn={copying ? null : classified.endTurn}
            attack={copying ? null : attackMode}
            defend={copying ? null : defendMode}
            run={copying ? null : sprintMode}
            runReason={runReason}
            moveCount={classified.moves.size}
            moving={mode === null}
            onMove={p.onCancel}
            onPreviewAction={p.onPreviewAction}
            selectedKey={mode?.key ?? null}
            more={copying ? [] : moreModes(basic)}
            extra={copying ? [] : p.fallback}
            onPickMode={p.onPickMode}
            onAction={p.onAct}
            speed={<SpeedControl speed={p.speed} playing={p.playing} onSpeed={p.onSpeed} onSkipNow={p.onSkipNow} />}
          />
        )}
      </div>
    </div>
  );
}
