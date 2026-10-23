// 召喚技能卡可展開的「召喚物資訊」小卡（Phase 3-41a，說明整修清單 1.8）。
// 文字全部由後端依召喚物範本與規則產生（`SkillCard.summons`），前端只排版，不寫死規則數字。
import type { SummonInfoCard } from "../api/types";

function Lines({ items }: { items: readonly string[] }) {
  if (items.length === 1) return <>{items[0]}</>;
  return (
    <ul>
      {items.map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  );
}

interface Props {
  info: SummonInfoCard;
  /** 預設展開（完整卡片）；技能列的浮動卡預設收起。 */
  open?: boolean;
}

export function SummonInfo({ info, open = false }: Props) {
  const count = (info.count ?? 1) > 1 ? ` ×${info.count}` : "";
  return (
    <details className="summon-info small" open={open}>
      <summary>
        召喚物資訊：{info.name_zh}
        {count}（HP {info.hp}・{info.basis_zh}）
      </summary>
      <dl>
        <dt>HP</dt>
        <dd>
          {info.hp}
          <span className="muted">（{info.hp_note}）</span>
          {(info.hp_infusion_zh ?? "") !== "" && <div className="muted">{info.hp_infusion_zh}</div>}
        </dd>
        <dt>移動</dt>
        <dd>{info.move}</dd>
        <dt>防禦</dt>
        <dd>{info.defense}</dd>
        <dt>攻擊</dt>
        <dd>{info.attack}</dd>
        {info.innate.length > 0 && (
          <>
            <dt>自帶</dt>
            <dd>
              <Lines items={info.innate} />
            </dd>
          </>
        )}
        <dt>行為</dt>
        <dd>
          <Lines items={info.behavior} />
        </dd>
        <dt>灌注</dt>
        <dd>{info.infusion.replace(/^灌注：/, "")}</dd>
      </dl>
    </details>
  );
}
