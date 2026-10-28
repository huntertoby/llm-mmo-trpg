// 底部技能列（Phase 3-8）：基本動作（攻擊、推擊……）＋主動技能排成一排（超出寬度換成兩排，不捲動）；
// 被動、反應、姿態、修正以小圖示放在同一列最右側，點開看卡片（可施放的姿態點了照樣選取）。
// 灰掉原因、滑過看卡片、選取提示照舊；卡片用共用的浮動卡規則（`useFloatCard`，Phase 3-30）：貼齊按鈕上方，滑過約 150ms 顯示，
// 離開有 250ms 寬限可滑進卡片，點卡片釘住，Esc／點外面關閉。
import type { RaceView, SkillCard } from "../api/types";
import { passiveLine, raceCardLines, raceUsesText } from "../battle/race";
import { minorGlyph, splitSkills } from "../battle/skillTray";
import type { ActionMode, SkillButton } from "../battle/targeting";
import { gearSkillBadge } from "../battle/gearSkills";
import { grantedBadge } from "../battle/granted";
import { activeVariantCard, variantBadge } from "../battle/variants";
import { levelBadge } from "../run/skillGrowth";
import { SkillCardView } from "./SkillCardView";
import { SkillIconView } from "./SkillIconView";
import { FloatCard, useFloatCard } from "./useFloatCard";
import { Hint } from "./Hint";

interface Props {
  /** 基本動作的模式（防禦除外，防禦在右下角）。 */
  basic: readonly ActionMode[];
  /** 主角的種族與種族技的模式（Phase 3R-2；不佔技能欄，另列一組按鈕；沒有種族時省略）。 */
  race?: RaceView | null;
  raceModes?: readonly ActionMode[];
  buttons: readonly SkillButton[];
  cards: Readonly<Record<string, SkillCard | undefined>>;
  /** 主角的技能等級（技能 ID → 等級，只列 2 級以上的；Phase 3-26a）：按鈕上顯示「Lv.N」。 */
  levels?: Readonly<Record<string, number>>;
  selectedKey: string | null;
  enabled: boolean;
  /** 技能列上方的一行提示（可移動格數、攻擊目標數、等待中……）。 */
  hint: string;
  onPickMode(mode: ActionMode): void;
  onSelect(skillId: string): void;
  /** 點到灰掉、有原因的技能：把原因交給畫面的訊息列（Phase 3-5c-2）。 */
  onBlocked?(button: SkillButton): void;
  /** 點到灰色的基本動作（例如推不動的「推動物件」）：把原因交給訊息列。 */
  onBlockedMode?(reason: string): void;
}

function costText(b: SkillButton): string {
  if (b.cooldown > 0) return `冷卻 ${b.cooldown}`;
  return b.costs.length > 0 ? b.costs.join("・") : "…";
}

function SkillSlot({
  b,
  card,
  level,
  selected,
  enabled,
  onSelect,
  onBlocked,
}: {
  b: SkillButton;
  card: SkillCard | undefined;
  level: number;
  selected: boolean;
  enabled: boolean;
  onSelect(id: string): void;
  onBlocked?(b: SkillButton): void;
}) {
  const blocked = !enabled || b.disabledReason !== null;
  const reasoned = b.disabledReason !== null;
  // 點按鈕是施放／選取，所以滑鼠點擊不釘住卡片；觸控沒有滑過，點一下同時顯示卡片
  const f = useFloatCard({ pinOn: "touch" });
  const variant = b.variant ?? null;
  const form = activeVariantCard(card, variant);
  return (
    <div className="skill-slot" {...f.triggerProps}>
      <button
        type="button"
        className={`skill-button${selected ? " selected" : ""}${b.grantedRemaining != null ? " granted" : ""}${b.gearSource != null ? " from-gear" : ""}${reasoned ? " blocked" : ""}${variant?.glow === true && !blocked ? " variant-ready" : ""}`}
        data-variant={form?.id}
        disabled={blocked && !reasoned}
        aria-disabled={blocked}
        onClick={() => (blocked ? onBlocked?.(b) : onSelect(b.skillId))}
      >
        <SkillIconView icon={form?.icon ?? card?.icon} size={40} className="skill-button-icon" />
        <span className="skill-button-text">
          <span className="skill-name">
            {b.name}
            {level > 1 && <span className="skill-lv">{levelBadge(level)}</span>}
          </span>
          {b.grantedRemaining != null && (
            <span className="skill-granted" aria-label="暫時技能">
              {grantedBadge(b.grantedRemaining)}
            </span>
          )}
          {b.gearSource != null && (
            <span className="skill-gear" aria-label={gearSkillBadge(b.gearSource)}>
              {gearSkillBadge(b.gearSource)}
            </span>
          )}
          {variant?.glow === true && (
            <span className="skill-variant" aria-label="戰場變奏">
              {variantBadge(card, variant)}
            </span>
          )}
          <span className="skill-cost">{costText(b)}</span>
        </span>
      </button>
      {f.open && card !== undefined && (
        <FloatCard float={f} className="skill-card-float">
          {b.disabledReason !== null && <div className="skill-card-reason">現在不能用：{b.disabledReason}</div>}
          <SkillCardView card={card} compact activeVariantId={form?.id ?? null} />
        </FloatCard>
      )}
    </div>
  );
}

/** 種族技按鈕（Phase 3R-2）：浮動卡列出說明、花費與次數、選取方式與環境被動；灰掉時卡片第一行說原因。 */
function RaceSlot({
  m,
  race,
  selected,
  enabled,
  onPick,
  onBlocked,
}: {
  m: ActionMode;
  race: RaceView;
  selected: boolean;
  enabled: boolean;
  onPick(m: ActionMode): void;
  onBlocked?(reason: string): void;
}) {
  const f = useFloatCard({ pinOn: "touch" });
  const reason = m.blockedReason;
  return (
    <div className="skill-slot race-slot" {...f.triggerProps}>
      <button
        type="button"
        className={`skill-button race-button${selected ? " selected" : ""}${reason !== undefined ? " blocked" : ""}`}
        disabled={!enabled}
        aria-disabled={reason !== undefined ? true : undefined}
        onClick={() => (reason === undefined ? onPick(m) : onBlocked?.(reason))}
      >
        <span className="skill-button-text">
          <span className="skill-name">{m.label}</span>
          <span className="skill-cost">{raceUsesText(race)}</span>
        </span>
      </button>
      {f.open && (
        <FloatCard float={f} className="skill-card-float race-card">
          <div className="section-title">
            {race.name_zh}・{race.skill_name_zh}
          </div>
          {reason !== undefined && <div className="skill-card-reason">現在不能用：{reason}</div>}
          {raceCardLines(race).map((line) => (
            <div key={line} className="small">
              {line}
            </div>
          ))}
          <div className="small muted">{passiveLine(race)}</div>
        </FloatCard>
      )}
    </div>
  );
}

/** 被動、反應、姿態的小圖示：可施放的姿態點了選取，其他點一下釘住卡片。 */
function MiniSlot({
  b,
  card,
  selected,
  enabled,
  onSelect,
}: {
  b: SkillButton;
  card: SkillCard | undefined;
  selected: boolean;
  enabled: boolean;
  onSelect(id: string): void;
}) {
  const usable = enabled && b.disabledReason === null && b.actions.length > 0;
  const f = useFloatCard({ pinOn: usable ? "touch" : "always" });
  return (
    <span className="skill-mini-wrap" {...f.triggerProps}>
      <button
        type="button"
        className={`skill-mini${selected || f.pinned ? " selected" : ""}`}
        aria-label={b.name}
        aria-pressed={f.pinned}
        onClick={() => usable && onSelect(b.skillId)}
      >
        {card?.icon == null ? minorGlyph(b.name) : <SkillIconView icon={card.icon} size={28} />}
      </button>
      {f.open && card !== undefined && (
        <FloatCard float={f} className="skill-card-float">
          <SkillCardView card={card} compact />
        </FloatCard>
      )}
    </span>
  );
}

export function SkillBar(props: Props) {
  const { basic, buttons, cards, selectedKey, enabled, hint } = props;
  const { main, minor } = splitSkills(buttons, cards);
  return (
    <div className="skill-bar" aria-label="技能列">
      <div className="skill-hint small muted">{hint}</div>
      <div className="skill-row">
        <div className="skill-buttons">
          {basic.map((m) => (
            <Hint key={m.key} text={m.blockedReason}>
              <button
                type="button"
                className={`basic-button${selectedKey === m.key ? " selected" : ""}${m.blockedReason !== undefined ? " blocked" : ""}`}
                disabled={!enabled}
                aria-disabled={m.blockedReason !== undefined ? true : undefined}
                onClick={() => (m.blockedReason === undefined ? props.onPickMode(m) : props.onBlockedMode?.(m.blockedReason))}
              >
                {m.label}
              </button>
            </Hint>
          ))}
          {main.map((b) => (
            <SkillSlot
              key={b.skillId}
              b={b}
              card={cards[b.skillId]}
              level={props.levels?.[b.skillId] ?? 1}
              selected={selectedKey === `skill:${b.skillId}`}
              enabled={enabled}
              onSelect={props.onSelect}
              onBlocked={props.onBlocked}
            />
          ))}
          {props.race != null && (props.raceModes ?? []).length > 0 && (
            <div className="race-group" aria-label="種族技">
              {(props.raceModes ?? []).map((m) => (
                <RaceSlot
                  key={m.key}
                  m={m}
                  race={props.race as RaceView}
                  selected={selectedKey === m.key}
                  enabled={enabled}
                  onPick={props.onPickMode}
                  onBlocked={props.onBlockedMode}
                />
              ))}
            </div>
          )}
          {basic.length === 0 && main.length === 0 && (props.raceModes ?? []).length === 0 && (
            <span className="muted small">（沒有可用的動作）</span>
          )}
        </div>
        {minor.length > 0 && (
          <div className="skill-minor" aria-label="被動、反應與姿態">
            {minor.map((b) => (
              <MiniSlot
                key={b.skillId}
                b={b}
                card={cards[b.skillId]}
                selected={selectedKey === `skill:${b.skillId}`}
                enabled={enabled}
                onSelect={props.onSelect}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
