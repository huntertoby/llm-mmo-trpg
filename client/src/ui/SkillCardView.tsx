// 技能卡片（滑過技能按鈕時顯示）。
import type { SkillCard } from "../api/types";

export function SkillCardView({ card }: { card: SkillCard }) {
  return (
    <div className="skill-card">
      <div className="skill-card-title">
        {card.name_zh}
        <span className="muted small">
          {" "}
          {card.rarity}・{card.skeleton}
        </span>
      </div>
      <div className="small">{card.cost.join("，")}</div>
      <div className="small muted">{card.shape}</div>
      {card.condition !== null && <div className="small">條件：{card.condition}</div>}
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
