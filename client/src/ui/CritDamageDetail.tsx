// CR-1b／CR-1c（05 5.4.2 第 8 點）：「▸ 詳細」暴擊傷害列的內容：來源（後端排好的字），有「條件看目標」的
// 修正技時最後加一行提示。單位卡與一輪中的主角面板共用。
import { critDamageDetail, critDamageHint } from "../battle/critDamage";

type CritFields = {
  crit_damage_detail_zh?: string | null;
  crit_damage_hint_zh?: string | null;
};

export function CritDamageDetail({ unit }: { unit: CritFields }) {
  const detail = critDamageDetail(unit);
  const hint = critDamageHint(unit);
  return (
    <>
      {detail}
      {hint !== null && (
        <div className="crit-damage-hint muted" data-testid="crit-damage-hint">
          {hint}
        </div>
      )}
    </>
  );
}
