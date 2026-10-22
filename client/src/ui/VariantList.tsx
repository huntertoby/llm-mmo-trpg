// 技能卡的「戰場變奏」區（Phase 3-25b）：列出所有型態（型態名、條件、替換內容），生效中的標出來。
// 純顯示，沒有彈出層；圖示與型態名的說明沿用技能卡本身（技能列的浮動卡、升級卡、工坊都用同一個 SkillCardView）。
import type { SkillCard } from "../api/types";
import { conditionNote } from "../battle/variants";
import { SkillIconView } from "./SkillIconView";

interface Props {
  card: SkillCard;
  /** 目前生效的型態 id（技能列的浮動卡傳入）；省略就不標。 */
  activeId?: string | null;
}

export function VariantList({ card, activeId = null }: Props) {
  const variants = card.variants ?? [];
  if (variants.length === 0) return null;
  return (
    <div className="skill-variants" aria-label="戰場變奏">
      <div className="small skill-variants-title">戰場變奏（條件成立時自動換型態，資料中排前面的優先）</div>
      <ul className="skill-variant-list">
        {variants.map((v) => (
          <li key={v.id} className={`skill-variant-item${v.id === activeId ? " active" : ""}`}>
            <SkillIconView icon={v.icon} size={28} small className="skill-variant-icon" title={v.name_zh} />
            <div>
              <div className="small">
                <b>{v.name_zh}</b>
                {v.id === activeId && <span className="skill-variant-now">　目前生效</span>}
              </div>
              <div className="small muted">
                條件：{v.condition}
                {conditionNote(v)}
              </div>
              <div className="small">{v.change}</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
