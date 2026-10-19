// 單位資訊：滑過或點選單位時顯示（文字即可）。
import type { StatusView, UnitView } from "../api/types";
import { stackName, statusName } from "../battle/glossary";
import type { SkillNames } from "../battle/actions";
import type { UnitNames } from "../battle/units";

interface Props {
  unit: UnitView | null;
  names: UnitNames;
  heroId: string;
  skills: SkillNames;
}

function statusText(s: StatusView): string {
  const left = s.remaining === null ? "" : ` ${s.remaining} 回合`;
  const amount = s.amount === null ? "" : `（${s.amount}）`;
  return `${statusName(s.status_id)}${amount}${left}`;
}

export function UnitInfo({ unit, names, heroId, skills }: Props) {
  if (unit === null) {
    return <div className="panel unit-info muted">滑過或點選單位以查看資訊</div>;
  }
  const team = unit.team === "ally" ? "我方" : "敵方";
  const tags = [team, unit.id === heroId ? "主角" : "", unit.downed ? "倒下" : ""].filter(Boolean);
  const stacks = Object.entries(unit.stacks);
  const cooldowns = Object.entries(unit.cooldowns);
  const rows: [string, string][] = [
    ["HP", `${unit.hp} / ${unit.max_hp}${unit.shield > 0 ? `（護盾 ${unit.shield}）` : ""}`],
    ["法力", `${unit.mana} / ${unit.max_mana}`],
    ["耐力", `${unit.stamina} / ${unit.max_stamina}`],
    ["AP／移動", `${unit.ap}／${unit.move_points}（速度 ${unit.speed}）`],
    ["武器", unit.weapon_name_zh],
    ["位置", `(${unit.pos.x}, ${unit.pos.y})`],
  ];
  return (
    <div className="panel unit-info">
      <div className="unit-title">
        <span className={`unit-badge ${unit.team}`}>{names.marker(unit.id)}</span>
        {unit.name_zh}
        <span className="muted">（{tags.join("・")}）</span>
      </div>
      <table className="unit-stats">
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <th>{k}</th>
              <td>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="unit-line">
        狀態：{unit.statuses.length === 0 ? "無" : unit.statuses.map(statusText).join("、")}
      </div>
      {stacks.length > 0 && (
        <div className="unit-line">層數：{stacks.map(([k, v]) => `${stackName(k)} ×${v}`).join("、")}</div>
      )}
      {cooldowns.length > 0 && (
        <div className="unit-line">冷卻：{cooldowns.map(([k, v]) => `${skills[k] ?? k} ${v}`).join("、")}</div>
      )}
    </div>
  );
}
