// 英雄面板（裝備測試，Phase 3G-G4）：穿上這組裝備後開戰時的主角——數值旁標出「來自裝備」，
// 以及遞減、截斷後的實際值與每條詞條的貢獻。
import { tipLines } from "../../gear/affixStatus";
import type { UnitView } from "../../api/types";
import { GearIcon } from "../GearIcon";
import { PartTip } from "../PartTip";
import { GearTotals } from "../GearTotals";

interface Props {
  hero: UnitView | null | undefined;
  pending: boolean;
}

export function HeroGearPanel({ hero, pending }: Props) {
  if (hero == null) {
    return <div className="gear-hero muted">{pending ? "計算中……" : "裝備合法時，這裡顯示穿上後的主角與加成來源。"}</div>;
  }
  return (
    <div className="gear-hero" aria-label="英雄面板">
      <div className="unit-title">
        {hero.name_zh}
        <span className="muted">（開戰時）</span>
      </div>
      <table className="unit-stats">
        <tbody>
          <tr>
            <th>HP</th>
            <td>
              {hero.max_hp}
              {hero.gear_totals.some((t) => t.key === "max_hp") && <span className="gear-total-from">含裝備</span>}
            </td>
          </tr>
          <tr>
            <th>AP／移動</th>
            <td>
              {hero.ap}／{hero.move_points}（速度 {hero.speed}）
              {hero.gear_totals.some((t) => t.key === "move") && <span className="gear-total-from">含裝備</span>}
            </td>
          </tr>
          <tr>
            <th>武器</th>
            <td>{hero.weapon_name_zh}</td>
          </tr>
        </tbody>
      </table>
      {hero.equipment.length > 0 && (
        <div className="gear-row">
          {hero.equipment.map((e) => (
            <PartTip key={e.slot} cat={e.slot_zh} label={e.name_zh} tip="" lines={tipLines(e.affixes)}>
              <GearIcon look={e.appearance} slot={e.slot} size={32} />
            </PartTip>
          ))}
        </div>
      )}
      {hero.gear_totals.length === 0 && <div className="muted small">沒有任何裝備加成。</div>}
      <GearTotals totals={hero.gear_totals} />
    </div>
  );
}
