// 單位資訊：滑過或點選單位時顯示的小卡。
// Phase 6A-2（去文字化③）：名稱＋精英詞綴金色徽章；HP 條與耐力條（和主角卡一樣粗、寫字）；
// 圖示＋數字（護盾、法力、AP、移動、武器）；狀態圖示＋回合數、腳下表面；朝向不寫字（看小人）；
// 特性、詞綴說明與其餘細項收進「▸ 詳細」；圖釘可以釘選（釘住的小卡在敵人回合也一直顯示，由 BattleScreen 放在戰場右上）。
import type { ReactNode } from "react";
import { RuleText } from "./ruleText";
import { tipLines } from "../gear/affixStatus";
import { withKeywordLine } from "../gear/gearKeywords";
import { ChargeChips } from "./ChargeChips";
import type { BattleView, SkillCard, StatusView, UnitView } from "../api/types";
import { ammoText, hasMagazine } from "../battle/ammo";
import { bombStatusText, TIME_BOMB } from "../battle/bombs";
import { CHARGING, chargeStatusText } from "../battle/followup";
import { COST_STATUS_NOTE, statusName, surfaceName } from "../battle/glossary";
import type { SkillNames } from "../battle/actions";
import { infusionName } from "../battle/infusion";
import { showsRevivable } from "../battle/drawModel";
import { heightNote } from "../battle/elevation";
import { remainingRounds, summonKind } from "../battle/summons";
import { modeText } from "../battle/summonControl";
import { HIDDEN_INFO_HINT, isHiddenInfo, UNKNOWN_MARK } from "../battle/hiddenInfo";
import type { UnitNames } from "../battle/units";
import { GearIcon } from "./GearIcon";
import { PartTip } from "./PartTip";
import { GearTotals } from "./GearTotals";
import { Hint } from "./Hint";
import { phaseText } from "../battle/bossPhase";
import { PinGlyph } from "./SkillCardGlyphs";
import { activeStacks, affixBadges, barData, surfaceAt, unitChips } from "./statusCard";
import { StackBadge, StatBar, StatChipView, StatusBadge, SurfaceBadge } from "./StatusCardParts";

interface Props {
  unit: UnitView | null;
  names: UnitNames;
  heroId: string;
  skills: SkillNames;
  /** 技能卡（層數說明框列出「你的技能」用；3-41c）。 */
  cards?: Readonly<Record<string, SkillCard | undefined>>;
  /** 召喚物的剩餘輪數、腳下表面要用目前的戰場。 */
  view?: BattleView;
  /** 這張小卡釘選中（6A-2）。 */
  pinned?: boolean;
  /** 圖釘：釘選或取消；省略時不畫圖釘。 */
  onTogglePin?(): void;
  /** 精簡版（6A-3：視窗不到 1000 寬的釘選小卡）：只留名稱、HP 條、耐力條。 */
  compact?: boolean;
}

export function statusText(s: StatusView, skills?: SkillNames): string {
  if (s.status_id === TIME_BOMB) return bombStatusText(s);
  if (s.status_id === CHARGING) return chargeStatusText(s, skills);
  const left = s.remaining === null ? "" : ` ${s.remaining} 回合`;
  const amount = s.amount === null ? "" : `（${s.amount}）`;
  return `${statusName(s.status_id)}${amount}${left}${s.cost_status ? COST_STATUS_NOTE : ""}`;
}

/** 形態（Phase 3J-1a）：目前形態、天生武器、形態效果、維持費，與冷卻中的形態（只有文字，外觀在 3J-5）。 */
export function formRows(unit: UnitView): [string, ReactNode][] {
  const rows: [string, ReactNode][] = [];
  const form = unit.form;
  if (form != null) {
    rows.push(["形態", form.name_zh]);
    rows.push(["　天生武器", <RuleText key="natural" text={form.natural_weapon_zh} />]);
    if (form.effects_zh.length > 0) rows.push(["　效果", form.effects_zh.join("、")]);
    if (form.upkeep_zh !== "") rows.push(["　維持", form.upkeep_zh]);
  }
  const cooling = unit.form_cooldowns ?? [];
  if (cooling.length > 0) {
    rows.push(["形態冷卻", cooling.map((c) => `${c.name_zh} ${c.remaining} 回合`).join("、")]);
  }
  return rows;
}

/** 單位的「特性」欄（Phase 5A-M1b，玩法決定 #82）：招牌被動、反應、開場狀態與精英詞綴，一項一行；沒有時不列。 */
export function traitRows(unit: UnitView): [string, ReactNode][] {
  const lines = unit.traits_zh ?? [];
  if (lines.length === 0) return [];
  return [
    [
      "特性",
      <div key="traits" className="unit-traits">
        {lines.map((line) => (
          <div key={line}>
            <RuleText text={line} />
          </div>
        ))}
      </div>,
    ],
  ];
}

/** Boss 的「階段」列（Phase 5F-2）：目前階段與下一個 HP 門檻；沒有階段時不列。 */
export function phaseRows(unit: UnitView): [string, ReactNode][] {
  const text = phaseText(unit);
  return text === null ? [] : [["階段", text]];
}

/** 「▸ 詳細」的表格列：特性與詞綴、階段、速度、武器特性、副手、種族、位置、召喚者、灌注、模式、光環、形態。 */
export function detailRows(unit: UnitView, names: UnitNames, view?: BattleView): [string, ReactNode][] {
  const rows: [string, ReactNode][] = [
    ...traitRows(unit),
    ...phaseRows(unit),
    ["速度", String(unit.speed)],
    ...unit.weapon_traits_zh.map((line): [string, ReactNode] => ["武器特性", <RuleText key={line} text={line} />]),
    ...(hasMagazine(unit) ? [["彈匣", ammoText(unit).replace("彈匣 ", "")] as [string, ReactNode]] : []),
    ...(unit.offhand_name_zh === "" ? [] : [["副手", unit.offhand_name_zh] as [string, ReactNode]]),
    ...unit.offhand_traits_zh.map((line): [string, ReactNode] => ["　特性", <RuleText key={line} text={line} />]),
    ...(unit.race == null
      ? []
      : [["種族", `${unit.race.name_zh}（種族技：${unit.race.skill_name_zh}；被動：${unit.race.passive_name_zh}）`] as [string, ReactNode]]),
    ["位置", `(${unit.pos.x}, ${unit.pos.y})`],
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
  rows.push(...formRows(unit));
  return rows;
}

const TEAM_ZH = { ally: "我方", enemy: "敵方", third: "第三方" } as const;

function surfaceText(view: BattleView, unit: UnitView): string {
  const tile = view.tiles.find((t) => t.x === unit.pos.x && t.y === unit.pos.y);
  if (tile === undefined || tile.surface === "none") return "無";
  const left = tile.surface_remaining === null ? "" : `（${tile.surface_remaining} 輪）`;
  return `${surfaceName(tile.surface)}${left}`;
}

/** 6F-18：單位站的格子的「高地 ▲N」（沒有戰場資料或高度 0 時 `null`）。 */
export function heightNoteOf(view: BattleView | undefined, unit: UnitView): string | null {
  const tile = view?.tiles.find((t) => t.x === unit.pos.x && t.y === unit.pos.y);
  return tile === undefined ? null : heightNote(tile.height);
}

export function UnitInfo(props: Props) {
  const { unit, names, heroId, pinned = false, onTogglePin, compact = false, view } = props;
  if (unit === null) {
    return <div className="panel unit-info muted">滑過或點選單位以查看資訊</div>;
  }
  const kind = summonKind(unit);
  // 6F-6：敵方倒地不寫「可復活」，和戰場上的愛心／墓碑同一個判斷（沒有戰場資料時把主角陣營當 ally）
  const revivable = view !== undefined ? showsRevivable(view, unit, heroId) : unit.downed && unit.revivable && unit.team === "ally";
  const tags = [unit.id === heroId ? "主角" : "", kind ?? "", unit.downed ? (revivable ? "倒下・可復活" : "倒下") : ""].filter(Boolean);
  // 6F-18：站著的人那一格地圖上不畫「▲N」，高度寫在卡上
  const height = heightNoteOf(view, unit);
  return (
    <div className={`panel unit-info unit-card${pinned ? " pinned" : ""}${compact ? " compact" : ""}`} data-unit={unit.id}>
      <div className="unit-title">
        <Hint text={TEAM_ZH[unit.team]}>
          <span className={`unit-badge ${unit.team}`}>{names.marker(unit.id)}</span>
        </Hint>
        <span className="unit-name">{unit.name_zh}</span>
        {!compact && tags.length > 0 && <span className="muted small">（{tags.join("・")}）</span>}
        {/* 6F-19（美術 PM 6F-18 檢查 D3）：精簡版也寫（窄畫面多半是觸控，沒有大卡可看），放在名字後面 */}
        {height !== null && <span className="unit-height">{height}</span>}
        {(compact ? [] : affixBadges(unit)).map((b) => (
          <Hint key={b.label} text={b.hint}>
            <span className="affix-badge" data-testid="affix-badge">
              ◆ {b.label}
            </span>
          </Hint>
        ))}
        {onTogglePin !== undefined && (
          <button
            type="button"
            className={`unit-pin${pinned ? " on" : ""}`}
            aria-pressed={pinned}
            aria-label={pinned ? "取消釘選" : "釘選"}
            onClick={(e) => {
              e.stopPropagation(); // 不要算成點卡片（那是釘住格子資訊卡）
              onTogglePin();
            }}
          >
            <PinGlyph pinned={pinned} />
            {pinned ? "取消釘選" : "釘選"}
          </button>
        )}
      </div>
      <div className="hud-bars">
        <StatBar bar={barData("hp", unit)} />
        <StatBar bar={barData("stamina", unit)} />
      </div>
      {!compact && <UnitCardMore {...props} unit={unit} />}
    </div>
  );
}

/** 小卡的條以下：圖示＋數字、狀態與表面、「▸ 詳細」（精簡版不畫）。 */
function UnitCardMore({ unit, names, heroId, skills, cards, view }: Props & { unit: UnitView }) {
  const cooldowns = Object.entries(unit.cooldowns).filter(([, n]) => n > 0);
  const surface = view === undefined ? null : surfaceAt(view, unit);
  const rows = detailRows(unit, names, view);
  const hidden = isHiddenInfo(unit); // HID-1：伺服器沒給狀態，寫「？」
  return (
    <>
      <div className="hud-icons">
        {unitChips(unit).map((c) => (
          <StatChipView key={c.key} chip={c} />
        ))}
      </div>
      {(hidden || unit.statuses.length > 0 || activeStacks(unit).length > 0 || surface !== null) && (
        <div className="hud-icons">
          {hidden && (
            <PartTip cat="狀態" label={UNKNOWN_MARK} tip={HIDDEN_INFO_HINT} className="stat-badge status-badge status-unknown">
              <b data-testid="status-unknown">{UNKNOWN_MARK}</b>
            </PartTip>
          )}
          {unit.statuses.map((s, i) => (
            <StatusBadge key={`${i}:${s.status_id}`} status={s} text={statusText(s, skills)} />
          ))}
          {activeStacks(unit).map(([k, n]) => (
            <StackBadge key={k} id={k} count={n} cards={cards} owned={unit.id === heroId ? unit.skills : null} />
          ))}
          {surface !== null && view !== undefined && <SurfaceBadge surface={surface} text={surfaceText(view, unit)} />}
        </div>
      )}
      <details className="unit-details">
        <summary>詳細</summary>
        <table className="unit-stats">
          <tbody>
            {rows.map(([k, v], i) => (
              <tr key={`${i}:${k}`}>
                <th>{k}</th>
                <td>{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {unit.equipment.length > 0 && (
          <div className="unit-line gear-row">
            裝備：
            {unit.equipment.map((e) => (
              <PartTip key={e.slot} cat={e.slot_zh} label={e.name_zh} tip="" lines={withKeywordLine(tipLines(e.affixes), e.appearance, e.slot)}>
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
        {cooldowns.length > 0 && (
          <div className="unit-line">冷卻：{cooldowns.map(([k, v]) => `${skills[k] ?? k} ${v}`).join("、")}</div>
        )}
      </details>
    </>
  );
}
