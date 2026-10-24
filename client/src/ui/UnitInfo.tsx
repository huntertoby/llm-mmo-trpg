// 單位資訊：滑過或點選單位時顯示（文字即可）。
import type { ReactNode } from "react";
import { RuleText } from "./ruleText";
import { tipLines } from "../gear/affixStatus";
import { ChargeChips } from "./ChargeChips";
import type { BattleView, SkillCard, StatusView, UnitView } from "../api/types";
import { ammoText, hasMagazine } from "../battle/ammo";
import { bombStatusText, TIME_BOMB } from "../battle/bombs";
import { CHARGING, chargeStatusText } from "../battle/followup";
import { facingText } from "../battle/facing";
import { statusIconTile } from "../render/skillIcon";
import { TipGlyph } from "./SkillIconView";
import { COST_STATUS_NOTE, stackName, statusName } from "../battle/glossary";
import type { SkillNames } from "../battle/actions";
import { infusionName } from "../battle/infusion";
import { remainingRounds, summonKind } from "../battle/summons";
import { modeText } from "../battle/summonControl";
import type { UnitNames } from "../battle/units";
import { GearIcon } from "./GearIcon";
import { PartTip } from "./PartTip";
import { GearTotals } from "./GearTotals";
import { Hint } from "./Hint";
import { StackTip } from "./StackTip";
import { actionCardText } from "../battle/actionInfo";

interface Props {
  unit: UnitView | null;
  names: UnitNames;
  heroId: string;
  skills: SkillNames;
  /** 技能卡（層數說明框列出「你的技能」用；3-41c）。 */
  cards?: Readonly<Record<string, SkillCard | undefined>>;
  /** 召喚物的剩餘輪數要用目前輪數計算。 */
  view?: BattleView;
}

function statusText(s: StatusView, skills?: SkillNames): string {
  if (s.status_id === TIME_BOMB) return bombStatusText(s);
  if (s.status_id === CHARGING) return chargeStatusText(s, skills);
  const left = s.remaining === null ? "" : ` ${s.remaining} 回合`;
  const amount = s.amount === null ? "" : `（${s.amount}）`;
  return `${statusName(s.status_id)}${amount}${left}${s.cost_status ? COST_STATUS_NOTE : ""}`;
}

export function UnitInfo({ unit, names, heroId, skills, cards, view }: Props) {
  if (unit === null) {
    return <div className="panel unit-info muted">滑過或點選單位以查看資訊</div>;
  }
  const team = unit.team === "ally" ? "我方" : "敵方";
  const kind = summonKind(unit);
  const tags = [team, unit.id === heroId ? "主角" : "", kind ?? "", unit.downed ? (unit.revivable ? "倒下・可復活" : "倒下") : ""].filter(Boolean);
  const stacks = Object.entries(unit.stacks);
  const cooldowns = Object.entries(unit.cooldowns);
  const rows: [string, ReactNode][] = [
    ["HP", `${unit.hp} / ${unit.max_hp}${unit.shield > 0 ? `（護盾 ${unit.shield}）` : ""}`],
    ["法力", `${unit.mana} / ${unit.max_mana}`],
    ["耐力", `${unit.stamina} / ${unit.max_stamina}`],
    ["AP／移動", `${unit.ap}／${unit.move_points}（速度 ${unit.speed}）`],
    ["武器", unit.weapon_name_zh],
    ...unit.weapon_traits_zh.map((line): [string, ReactNode] => ["　特性", <RuleText key={line} text={line} />]),
    ...(hasMagazine(unit) ? [["　彈匣", ammoText(unit).replace("彈匣 ", "")] as [string, ReactNode]] : []),
    ...(unit.offhand_name_zh === "" ? [] : [["副手", unit.offhand_name_zh] as [string, ReactNode]]),
    ...unit.offhand_traits_zh.map((line): [string, ReactNode] => ["　特性", <RuleText key={line} text={line} />]),
    ["位置", `(${unit.pos.x}, ${unit.pos.y})`],
    ["朝向", facingText(unit)],
  ];
  if (unit.owner_id !== null) {
    const left = view === undefined ? null : remainingRounds(view, unit);
    rows.push([
      "召喚者",
      `${names.name(unit.owner_id)}${left === null ? "" : `；剩 ${left} 輪（第 ${unit.summon_expires_round} 輪結束時消失）`}`,
    ]);
  }
  const infusion = infusionName(unit, view?.units.find((u) => u.id === unit.owner_id) ?? null);
  if (infusion !== null) rows.push(["灌注", infusion]);
  if (unit.summon_mode != null) rows.push(["模式", modeText(unit, names)]);
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
              <th>
                {k === "耐力" ? (
                  <Hint text={actionCardText("stamina")}>
                    <span className="has-hint">{k}</span>
                  </Hint>
                ) : (
                  k
                )}
              </th>
              <td>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="unit-line">
        狀態：
        {unit.statuses.length === 0 ? (
          "無"
        ) : (
          <span className="status-chips">
            {unit.statuses.map((s, i) => (
              <TipGlyph key={`${i}:${s.status_id}`} tile={statusIconTile(s.status_id)} text={statusText(s, skills)} />
            ))}
          </span>
        )}
      </div>
      {unit.equipment.length > 0 && (
        <div className="unit-line gear-row">
          裝備：
          {unit.equipment.map((e) => (
            <PartTip key={e.slot} cat={e.slot_zh} label={e.name_zh} tip="" lines={tipLines(e.affixes)}>
              <GearIcon look={e.appearance} slot={e.slot} size={32} />
            </PartTip>
          ))}
        </div>
      )}
      <GearTotals totals={unit.gear_totals} compact />
      {(unit.charges ?? []).length > 0 && (
        <div className="unit-line charge-line">
          充能：<ChargeChips charges={unit.charges ?? []} />
        </div>
      )}
      {stacks.length > 0 && (
        <div className="unit-line">
          層數：
          {stacks.map(([k, v], i) => (
            <span key={k}>
              {i > 0 && "、"}
              <StackTip id={k} cards={cards} owned={unit.id === heroId ? unit.skills : null}>
                {stackName(k)} ×{v}
              </StackTip>
            </span>
          ))}
        </div>
      )}
      {cooldowns.length > 0 && (
        <div className="unit-line">冷卻：{cooldowns.map(([k, v]) => `${skills[k] ?? k} ${v}`).join("、")}</div>
      )}
    </div>
  );
}
