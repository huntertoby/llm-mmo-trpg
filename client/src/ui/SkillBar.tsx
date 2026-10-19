// 技能列：主角的技能按鈕（名稱、AP／法力、冷卻、停用原因）；滑過顯示技能卡片。
import { useState } from "react";
import type { SkillCard } from "../api/types";
import type { SkillButton } from "../battle/targeting";
import { SkillCardView } from "./SkillCardView";

interface Props {
  buttons: readonly SkillButton[];
  cards: Readonly<Record<string, SkillCard | undefined>>;
  selectedKey: string | null;
  enabled: boolean;
  onSelect(skillId: string): void;
}

export function SkillBar({ buttons, cards, selectedKey, enabled, onSelect }: Props) {
  const [hovered, setHovered] = useState<string | null>(null);
  const card = hovered === null ? undefined : cards[hovered];
  return (
    <div className="skill-bar">
      <div className="section-title">技能</div>
      <div className="skill-buttons">
        {buttons.length === 0 && <span className="muted">（沒有技能）</span>}
        {buttons.map((b) => {
          const blocked = !enabled || b.disabledReason !== null;
          const selected = selectedKey === `skill:${b.skillId}`;
          const cost = b.cooldown > 0 ? `冷卻 ${b.cooldown}` : b.costs.length > 0 ? b.costs.join("・") : "…";
          return (
            <div
              key={b.skillId}
              className="skill-slot"
              title={b.disabledReason ?? undefined}
              onMouseEnter={() => setHovered(b.skillId)}
              onMouseLeave={() => setHovered((h) => (h === b.skillId ? null : h))}
            >
              <button
                type="button"
                className={`skill-button${selected ? " selected" : ""}`}
                disabled={blocked}
                onClick={() => onSelect(b.skillId)}
              >
                <span className="skill-name">{b.name}</span>
                <span className="skill-cost">{cost}</span>
              </button>
            </div>
          );
        })}
      </div>
      {card !== undefined && <SkillCardView card={card} />}
    </div>
  );
}
