// 技能卡片（滑過技能按鈕時顯示）。
import type { SkillCard } from "../api/types";
import { kindLabel, sourceCostText } from "../battle/source";
import { AssemblyRow, SkillIconView } from "./SkillIconView";

/** 源力上限（`content/rules/core.yaml` 的 `source_max`）；HUD 與卡片都用 3 格圖示。 */
const SOURCE_MAX = 3;

export function SkillCardView({ card }: { card: SkillCard }) {
  const source = sourceCostText(card, SOURCE_MAX);
  return (
    <div className={`skill-card rarity-${card.rarity_id}`}>
      <div className="skill-card-head">
        <SkillIconView icon={card.icon} size={72} title={card.name_zh} />
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
      <AssemblyRow icon={card.icon} />
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
      <div className="small muted">縮放：{card.scaling}</div>
      {card.mastery !== null && <div className="small">專精：{card.mastery}</div>}
      {card.concept !== "" && <div className="small muted">{card.concept}</div>}
    </div>
  );
}
