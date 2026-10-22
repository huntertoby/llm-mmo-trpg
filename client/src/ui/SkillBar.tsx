// 底部技能列（Phase 3-8）：基本動作（攻擊、推擊……）＋主動技能排成一排（超出寬度換成兩排，不捲動）；
// 被動、反應、姿態、修正以小圖示放在同一列最右側，點開看卡片（可施放的姿態點了照樣選取）。
// 灰掉原因、滑過看卡片、選取提示照舊；卡片浮在技能列上方。
import { useEffect, useRef, useState } from "react";
import type { SkillCard } from "../api/types";
import { minorGlyph, splitSkills } from "../battle/skillTray";
import type { ActionMode, SkillButton } from "../battle/targeting";
import { grantedBadge } from "../battle/granted";
import { levelBadge } from "../run/skillGrowth";
import { SkillCardView } from "./SkillCardView";
import { SkillIconView } from "./SkillIconView";

interface Props {
  /** 基本動作的模式（防禦除外，防禦在右下角）。 */
  basic: readonly ActionMode[];
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

/** 滑鼠離開技能按鈕後，浮動卡再停留多久（毫秒）；期間移進卡片就不關閉。 */
export const FLOAT_CLOSE_MS = 180;

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
  onHover,
}: {
  b: SkillButton;
  card: SkillCard | undefined;
  level: number;
  selected: boolean;
  enabled: boolean;
  onSelect(id: string): void;
  onBlocked?(b: SkillButton): void;
  onHover(id: string | null): void;
}) {
  const blocked = !enabled || b.disabledReason !== null;
  const reasoned = b.disabledReason !== null;
  return (
    <div
      className="skill-slot"
      title={b.disabledReason ?? undefined}
      onMouseEnter={() => onHover(b.skillId)}
      onMouseLeave={() => onHover(null)}
    >
      <button
        type="button"
        className={`skill-button${selected ? " selected" : ""}${b.grantedRemaining != null ? " granted" : ""}${reasoned ? " blocked" : ""}`}
        disabled={blocked && !reasoned}
        aria-disabled={blocked}
        onClick={() => (blocked ? onBlocked?.(b) : onSelect(b.skillId))}
      >
        <SkillIconView icon={card?.icon} size={40} className="skill-button-icon" />
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
          <span className="skill-cost">{costText(b)}</span>
        </span>
      </button>
    </div>
  );
}

export function SkillBar(props: Props) {
  const { basic, buttons, cards, selectedKey, enabled, hint } = props;
  const [hovered, setHovered] = useState<string | null>(null);
  /** 點開的小圖示（被動、反應、姿態）：卡片固定顯示，再點一次收起。 */
  const [pinned, setPinned] = useState<string | null>(null);
  const { main, minor } = splitSkills(buttons, cards);
  const shownId = hovered ?? pinned;
  const card = shownId === null ? undefined : cards[shownId];
  // 滑鼠從技能按鈕移到浮動卡上（要滑過卡上的部件看說明）時不關閉：離開後稍等一下才收起，移進卡片就取消
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelClose = () => {
    if (closeTimer.current !== null) clearTimeout(closeTimer.current);
    closeTimer.current = null;
  };
  useEffect(() => cancelClose, []);
  const leave = (id: string) => {
    cancelClose();
    closeTimer.current = setTimeout(() => setHovered((h) => (h === id ? null : h)), FLOAT_CLOSE_MS);
  };
  const enter = (id: string) => {
    cancelClose();
    setHovered(id);
  };
  return (
    <div className="skill-bar" aria-label="技能列">
      <div className="skill-hint small muted">{hint}</div>
      <div className="skill-row">
        <div className="skill-buttons">
          {basic.map((m) => (
            <button
              key={m.key}
              type="button"
              className={`basic-button${selectedKey === m.key ? " selected" : ""}${m.blockedReason !== undefined ? " blocked" : ""}`}
              disabled={!enabled}
              aria-disabled={m.blockedReason !== undefined ? true : undefined}
              title={m.blockedReason}
              onClick={() => (m.blockedReason === undefined ? props.onPickMode(m) : props.onBlockedMode?.(m.blockedReason))}
            >
              {m.label}
            </button>
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
              onHover={(id) => (id === null ? leave(b.skillId) : enter(id))}
            />
          ))}
          {basic.length === 0 && main.length === 0 && <span className="muted small">（沒有可用的動作）</span>}
        </div>
        {minor.length > 0 && (
          <div className="skill-minor" aria-label="被動、反應與姿態">
            {minor.map((b) => {
              const usable = enabled && b.disabledReason === null && b.actions.length > 0;
              const selected = selectedKey === `skill:${b.skillId}` || pinned === b.skillId;
              return (
                <button
                  key={b.skillId}
                  type="button"
                  className={`skill-mini${selected ? " selected" : ""}`}
                  title={`${b.name}（${costText(b)}）`}
                  aria-label={b.name}
                  aria-pressed={pinned === b.skillId}
                  onMouseEnter={() => enter(b.skillId)}
                  onMouseLeave={() => leave(b.skillId)}
                  onClick={() => {
                    if (usable) props.onSelect(b.skillId);
                    else setPinned((p) => (p === b.skillId ? null : b.skillId));
                  }}
                >
                  {cards[b.skillId]?.icon == null ? minorGlyph(b.name) : <SkillIconView icon={cards[b.skillId]?.icon} size={28} />}
                </button>
              );
            })}
          </div>
        )}
      </div>
      {card !== undefined && (
        <div
          className="skill-card-float"
          onMouseEnter={() => (shownId === null ? undefined : enter(shownId))}
          onMouseLeave={() => (shownId === null ? undefined : leave(shownId))}
        >
          <SkillCardView card={card} compact />
        </div>
      )}
    </div>
  );
}
