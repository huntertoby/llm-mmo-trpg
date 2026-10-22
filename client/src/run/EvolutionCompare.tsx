// 分歧進化的兩支比較（Phase 3-26b）：升到 3 級時並排顯示「加深」與「橋接」進化後的技能卡（沿用組裝式
// 圖示的技能卡），玩家選一支；選定後跟著技能走，重選不做。
import type { EvolutionOption } from "../api/types";
import { SkillCardView } from "../ui/SkillCardView";

interface Props {
  skillId: string;
  name: string;
  options: EvolutionOption[];
  picked: number | undefined;
  disabled: boolean;
  onPick(index: number): void;
}

function optionTitle(option: EvolutionOption): string {
  const keyword = option.keyword != null ? `・${option.keyword.name_zh}` : "";
  return `${option.label_zh}${keyword}${option.fallback ? "（橋接做不出來，改給第二種加深）" : ""}`;
}

export function EvolutionCompare({ skillId, name, options, picked, disabled, onPick }: Props) {
  return (
    <div className="evo-compare" data-testid={`evo-${skillId}`}>
      <div className="evo-title">
        分歧進化：{name} 升到這一級要選一支進化<span className="muted small">（選定後跟著技能走，之後不能重選）</span>
      </div>
      <div className="evo-options">
        {options.map((option) => (
          <label
            key={option.index}
            className={`evo-option evo-${option.branch}${picked === option.index ? " picked" : ""}`}
            data-testid={`evo-${skillId}-${option.index}`}
          >
            <span className="evo-head">
              <input
                type="radio"
                name={`evo-${skillId}`}
                checked={picked === option.index}
                disabled={disabled}
                onChange={() => onPick(option.index)}
              />
              <b className="evo-tag">{optionTitle(option)}</b>
            </span>
            <span className="evo-summary small">{option.summary_zh}</span>
            <SkillCardView card={option.card} />
          </label>
        ))}
      </div>
    </div>
  );
}
