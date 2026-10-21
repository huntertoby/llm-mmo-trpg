// 技能卡片（滑過技能按鈕時顯示；升級與營火候選卡、工坊也用）。
// Phase 3-18a：大圖示用小圖模式；部件區是「組裝算式」，每個部件都能滑過或點一下看說明。
import type { SkillCard } from "../api/types";
import { kindLabel, sourceCostText } from "../battle/source";
import { KeywordLine } from "./KeywordLine";
import { AssemblyFormula, SkillIconView } from "./SkillIconView";

/** 源力上限（`content/rules/core.yaml` 的 `source_max`）；HUD 與卡片都用 3 格圖示。 */
const SOURCE_MAX = 3;

interface Props {
  card: SkillCard;
  /** 緊湊版（技能列的浮動卡）：更小的圖示與間距，不寫縮放、專精與設計概念。 */
  compact?: boolean;
}

export function SkillCardView({ card, compact = false }: Props) {
  const source = sourceCostText(card, SOURCE_MAX);
  return (
    <div className={`skill-card rarity-${card.rarity_id}${compact ? " compact" : ""}`}>
      <div className="skill-card-head">
        <SkillIconView icon={card.icon} size={compact ? 48 : 72} small title={card.name_zh} />
        <div className="skill-card-headtext">
          <div className="skill-card-title">
            {card.name_zh}
            <span className="muted small">
              {" "}
              <span className="skill-card-rarity">{card.rarity}</span>・{kindLabel(card)}・{card.skeleton}
            </span>
          </div>
          <div className="small">{card.cost.join("，")}</div>
          {source !== null && <div className="small skill-card-source">傳說代價：{source}</div>}
          <div className="small muted">{card.shape}</div>
        </div>
      </div>
      <AssemblyFormula icon={card.icon} />
      <KeywordLine keywords={card.keywords} />
      {card.condition !== null && <div className="small">條件：{card.condition}</div>}
      {(card.timing ?? null) !== null && <div className="small">{card.timing}</div>}
      {(card.activation ?? null) !== null && <div className="small">啟動：{card.activation}（啟動前不生效）</div>}
      <ul className="skill-card-effects">
        {card.effects.map((e, i) => (
          <li key={`${i}:${e}`}>{e}</li>
        ))}
        {card.modifiers.map((m, i) => (
          <li key={`modifier:${i}:${m}`}>修正：{m}</li>
        ))}
      </ul>
      {!compact && <div className="small muted">縮放：{card.scaling}</div>}
      {card.mastery !== null && !compact && <div className="small">專精：{card.mastery}</div>}
      {card.concept !== "" && !compact && <div className="small muted">{card.concept}</div>}
    </div>
  );
}
