// 戰鬥畫面的底部列（由 BattleScreen 抽出，Phase 3T-7）：左下主角狀態卡（右緣有寬度拖曳線）、中間技能列、右下回合操作
// （戰鬥結束後換成結束面板）。

import type { Action, BattleResponse, BattleView, SkillCard, UnitView } from "../../api/types";
import type { ClassifiedActions, LabeledAction } from "../../battle/actions";
import { DEFAULT_LAYOUT, type LayoutPrefs, type layoutLimits } from "../../battle/layoutPrefs";
import { blockedMessage } from "../../battle/skillReasons";
import { actionHintText } from "../../battle/skillTray";
import { hasControllableSummon } from "../../battle/summons";
import { moreModes, TRAY_KINDS, type ActionMode, type SkillButton } from "../../battle/targeting";
import { EndPanel } from "../../ui/EndPanel";
import { Hud } from "../../ui/Hud";
import { ResizeHandle } from "../../ui/ResizeHandle";
import { SkillBar } from "../../ui/SkillBar";
import { SpeedControl } from "../../ui/SpeedControl";
import { TurnControls } from "../../ui/TurnControls";
import type { PlaySpeed } from "../../battle/playback";
import { runButton } from "../../battle/runAction";

interface Props {
  response: BattleResponse;
  view: BattleView;
  /** 播放中畫面上的視圖與主角（Hud 顯示播放中的狀態）。 */
  shown: BattleView;
  shownHero: UnitView | null;
  hero: UnitView | null;
  cards: Readonly<Record<string, SkillCard | undefined>>;
  skillNames: Readonly<Record<string, string>>;
  layout: LayoutPrefs;
  limits: ReturnType<typeof layoutLimits>;
  narrow: boolean;
  onLayoutChange(patch: Partial<LayoutPrefs>): void;
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
  const { layout, narrow, classified, basic, mode, copying, canAct, hero, view } = p;
  const attackMode = basic.find((m) => m.kind === "attack") ?? null;
  const defendMode = basic.find((m) => m.kind === "defend") ?? null;
  const sprintMode = basic.find((m) => m.kind === "run") ?? null;
  const runReason = runButton(sprintMode, p.response.run_option).reason;
  return (
    <div className={`battle-bottom${layout.bottomHeight < DEFAULT_LAYOUT.bottomHeight || narrow ? " short" : ""}`}>
      <div className="battle-hero">
        <Hud view={p.shown} hero={p.shownHero} skills={p.skillNames} cards={p.cards} compact={narrow} />
        {!narrow && (
          <ResizeHandle
            orientation="vertical"
            direction={1}
            value={layout.heroWidth}
            range={p.limits.hero}
            label="調整主角狀態卡寬度"
            onChange={(v) => p.onLayoutChange({ heroWidth: v })}
            onReset={() => p.onLayoutChange({ heroWidth: DEFAULT_LAYOUT.heroWidth })}
          />
        )}
      </div>
      <SkillBar
        basic={basic.filter((m) => TRAY_KINDS.includes(m.kind))}
        race={hero?.race ?? null}
        raceModes={p.raceModeList}
        buttons={p.buttons}
        cards={p.cards}
        levels={hero?.skill_levels}
        selectedKey={mode?.key ?? null}
        enabled={canAct}
        hint={actionHintText({
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
        })}
        onPickMode={p.onPickMode}
        onSelect={p.onPickSkill}
        onBlocked={(b) => p.onHint(blockedMessage(b))}
        onBlockedMode={p.onHint}
      />
      <div className="battle-turn">
        {p.ended ? (
          <EndPanel response={p.response} onRestart={p.onExit} restartLabel={p.exitLabel} />
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
