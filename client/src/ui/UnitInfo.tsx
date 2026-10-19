// 單位資訊：滑過或點選單位時顯示（文字即可）。
import type { BattleView, StatusView, UnitView } from "../api/types";
import { bombStatusText, TIME_BOMB } from "../battle/bombs";
import { stackName, statusName } from "../battle/glossary";
import type { SkillNames } from "../battle/actions";
import { remainingRounds, summonKind } from "../battle/summons";
import type { UnitNames } from "../battle/units";

interface Props {
  unit: UnitView | null;
  names: UnitNames;
  heroId: string;
  skills: SkillNames;
  /** 召喚物的剩餘輪數要用目前輪數計算。 */
  view?: BattleView;
}

function statusText(s: StatusView): string {
  if (s.status_id === TIME_BOMB) return bombStatusText(s);
  const left = s.remaining === null ? "" : ` ${s.remaining} 回合`;
  const amount = s.amount === null ? "" : `（${s.amount}）`;
  return `${statusName(s.status_id)}${amount}${left}`;
}

export function UnitInfo({ unit, names, heroId, skills, view }: Props) {
  if (unit === null) {
    return <div className="panel unit-info muted">滑過或點選單位以查看資訊</div>;
  }
  const team = unit.team === "ally" ? "我方" : "敵方";
  const kind = summonKind(unit);
  const tags = [team, unit.id === heroId ? "主角" : "", kind ?? "", unit.downed ? (unit.revivable ? "倒下・可復活" : "倒下") : ""].filter(Boolean);
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
  if (unit.owner_id !== null) {
    const left = view === undefined ? null : remainingRounds(view, unit);
    rows.push([
      "召喚者",
      `${names.name(unit.owner_id)}${left === null ? "" : `；剩 ${left} 輪（第 ${unit.summon_expires_round} 輪結束時消失）`}`,
    ]);
  }
  if (unit.totem_radius !== null) rows.push(["光環", `${unit.totem_radius} 格內的友方在圖騰行動時獲得增益`]);
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
