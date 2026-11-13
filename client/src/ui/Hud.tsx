// 戰鬥 HUD（設計文件 7.3）：固定顯示主角當下需要的資訊。
// Phase 6A-2（去文字化③）：三條（HP、法力、耐力）＋一排圖示，每個都能滑過看說明；細項收進「▸ 詳細」。
import type { ReactNode } from "react";
import type { BattleView, SkillCard, StatusView, UnitView } from "../api/types";
import { chargeText } from "../battle/charges";
import { hasMagazine, ammoText } from "../battle/ammo";
import { ChargeChips } from "./ChargeChips";
import { COST_STATUS_NOTE, stackName, statusName, surfaceName } from "../battle/glossary";
import type { SkillNames } from "../battle/actions";
import { activationLine } from "../battle/activations";
import { grantedLine } from "../battle/granted";
import { bombStatusText, TIME_BOMB } from "../battle/bombs";
import { CHARGING, chargeStatusText } from "../battle/followup";
import { summonLine, summonsOf } from "../battle/summons";
import { unitNames } from "../battle/units";
import { hpValueText } from "../battle/hiddenInfo";
import { zoneLine, zoneNextText, zonesOf } from "../battle/zones";
import { Hint } from "./Hint";
import { HeroCard } from "./HeroCard";
import { unitHeroInput } from "./heroFace";
import { passiveLine, raceHudText } from "../battle/race";
import { barData, heroChips, hudStacks, surfaceAt } from "./statusCard";
import { StackPips } from "./StackPips";
import { StackBadge, StatBar, StatChipView, StatusBadge, SurfaceBadge } from "./StatusCardParts";

interface Props {
  view: BattleView;
  hero: UnitView | null;
  skills: SkillNames;
  /** 技能卡（技能 ID → 卡片）：層數說明框用它列出「你的技能」中會累積／消耗該層數的（3-41c）。 */
  cards?: Readonly<Record<string, SkillCard | undefined>>;
  /** 縮成一行（窄螢幕，Phase 3-8）。 */
  compact?: boolean;
  /** 主角的出身區（QK-2b：Q 版頭像框色；沒有＝傭兵金）。 */
  heroOrigin?: string | null;
}

export function statusLine(s: StatusView): string {
  if (s.status_id === TIME_BOMB) return bombStatusText(s);
  if (s.status_id === CHARGING) return chargeStatusText(s);
  const left = s.remaining === null ? "" : `（${s.remaining} 回合）`;
  const amount = s.amount === null ? "" : ` ${s.amount}`;
  return `${statusName(s.status_id)}${amount}${left}${s.cost_status ? COST_STATUS_NOTE : ""}`;
}

/** 主角腳下的表面（中文）；沒有表面時「無」。 */
export function surfaceUnder(view: BattleView, hero: UnitView): string {
  const tile = view.tiles.find((t) => t.x === hero.pos.x && t.y === hero.pos.y);
  if (tile === undefined || tile.surface === "none") return "無";
  const left = tile.surface_remaining === null ? "" : `（${tile.surface_remaining} 輪）`;
  return `${surfaceName(tile.surface)}${left}`;
}

/** 一行文字版的主角狀態（Phase 3-8；6A-2 起畫面改用圖示，這段文字留給無障礙與測試）。 */
export function compactHudText(view: BattleView, hero: UnitView): string {
  const stacks = Object.entries(hero.stacks).filter(([, n]) => n > 0);
  const parts = [
    `HP ${hpValueText(hero)}/${hero.max_hp}${(hero.shield ?? 0) > 0 ? `（盾 ${hero.shield}）` : ""}`,
    `法力 ${hero.mana}/${hero.max_mana}`,
    `耐力 ${hero.stamina}/${hero.max_stamina}`,
    `AP ${hero.ap}`,
    `移動 ${hero.move_points}`,
    ...(hasMagazine(hero) ? [ammoText(hero)] : []),
    ...(hero.charges ?? []).map((c) => `充能 ${chargeText(c)}`),
    `反應${hero.reaction_available ? "可用" : "已用"}`,
    `源力 ${hero.source}/${hero.source_max}`,
    `狀態 ${hero.statuses.length === 0 ? "無" : hero.statuses.map(statusLine).join("、")}`,
    `腳下 ${surfaceUnder(view, hero)}`,
  ];
  if (stacks.length > 0) parts.push(`層數 ${stacks.map(([k, n]) => `${stackName(k)}×${n}`).join("、")}`);
  const race = raceHudText(hero);
  if (race !== null) parts.push(race);
  return parts.join("｜");
}

/** 狀態列：狀態圖示（右下角回合數）、層數（右下角層數；KW-3 起連擊、怒氣、專注、氣是格子計量 `StackPips`）、腳下表面。 */
function HudBadges({ view, hero, cards }: { view: BattleView; hero: UnitView; cards?: Props["cards"] }) {
  const surface = surfaceAt(view, hero);
  return (
    <>
      {hero.statuses.map((s, i) => (
        <StatusBadge key={`${i}:${s.status_id}`} status={s} text={statusLine(s)} />
      ))}
      {hudStacks(hero, cards).map(({ id, count, gauge }) =>
        gauge ? <StackPips key={id} id={id} count={count} cards={cards} owned={hero.skills} /> : <StackBadge key={id} id={id} count={count} cards={cards} owned={hero.skills} />,
      )}
      {surface !== null && <SurfaceBadge surface={surface} text={surfaceUnder(view, hero)} />}
    </>
  );
}

/**
 * 主角狀態卡（Phase 6A-2，去文字化③）：HP、法力、耐力三條一樣粗、條上寫字（護盾疊在 HP 條上）；
 * 下面一排 AP 圓點、移動、彈匣、反應（用過變灰）、源力圓點、狀態、層數、腳下表面，每個都能滑過看說明。
 * 充能與冷卻畫在技能列，這裡不重複；裝備充能、種族、傳說、暫時技能、召喚物、持續區域收進「▸ 詳細」。
 * 窄螢幕（`compact`）：三條與圖示排成一列，沒有「詳細」。
 */
export function Hud({ view, hero, cards, compact = false, heroOrigin = null }: Props) {
  if (hero === null) return null;
  const bars = (["hp", "mana", "stamina"] as const).map((k) => <StatBar key={k} bar={barData(k, hero)} />);
  const icons = (
    <div className="hud-icons">
      {heroChips(hero).map((c) => (
        <StatChipView key={c.key} chip={c} />
      ))}
      <HudBadges view={view} hero={hero} cards={cards} />
    </div>
  );
  // UI-E2（巡檢 #5）：和大世界同一張主角卡（`HeroCard`：頭像＋三條＋區域四角飾件）；資料不變
  if (compact) {
    return (
      <HeroCard where="battle" compact className="panel hud hud-compact" bars={<div className="hud-bars">{bars}</div>}>
        {icons}
      </HeroCard>
    );
  }
  const details = heroDetails(view, hero);
  return (
    <HeroCard
      where="battle"
      className="panel hud"
      name={<span className="hud-title">{hero.name_zh}</span>}
      bars={<div className="hud-bars">{bars}</div>}
      hero={unitHeroInput(hero)}
      realm={heroOrigin}
    >
      {icons}
      {details.length > 0 && (
        <details className="hud-details">
          <summary>詳細</summary>
          {details}
        </details>
      )}
    </HeroCard>
  );
}

/** 「▸ 詳細」裡的行：裝備充能、種族、生效中的傳說、暫時技能、召喚物、持續區域（沒有就不列）。 */
export function heroDetails(view: BattleView, hero: UnitView): ReactNode[] {
  const rows: ReactNode[] = [];
  const summons = summonsOf(view, hero.id);
  const zones = zonesOf(view);
  if ((hero.charges ?? []).length > 0) {
    rows.push(
      <div key="charges" className="hud-line charge-line" aria-label="裝備充能">
        <span className="muted">裝備充能：</span>
        <ChargeChips charges={hero.charges ?? []} />
      </div>,
    );
  }
  if (hero.race != null) {
    rows.push(
      <div key="race" className="hud-line hud-race" aria-label="種族">
        <span className="muted">種族：</span>
        <Hint text={passiveLine(hero.race)}>
          <span className="has-hint">{hero.race.name_zh}</span>
        </Hint>
        <span className="muted small">
          {" "}
          ・{hero.race.skill_name_zh}剩 {hero.race.skill_uses_left}／{hero.race.skill_uses_max} 次・被動「{hero.race.passive_name_zh}」
          {hero.race.passive_active ? "（目前有作用）" : ""}
        </span>
      </div>,
    );
  }
  if ((hero.activations ?? []).length > 0) {
    rows.push(
      <div key="activations" className="hud-line hud-activations" aria-label="生效中的傳說">
        <span className="muted">傳說：</span>
        <ul className="hud-summon-list">
          {(hero.activations ?? []).map((a) => (
            <li key={a.skill_id}>{activationLine(view, a)}</li>
          ))}
        </ul>
      </div>,
    );
  }
  if ((hero.granted_skills ?? []).length > 0) {
    rows.push(
      <div key="granted" className="hud-line hud-granted" aria-label="暫時技能">
        <span className="muted">暫時技能：</span>
        {(hero.granted_skills ?? []).map(grantedLine).join("、")}
      </div>,
    );
  }
  if (summons.length > 0) {
    rows.push(
      <div key="summons" className="hud-line hud-summons" aria-label="召喚物">
        <span className="muted">召喚物：</span>
        <ul className="hud-summon-list">
          {summons.map((u) => (
            <li key={u.id}>{summonLine(view, u)}</li>
          ))}
        </ul>
      </div>,
    );
  }
  if (zones.length > 0) {
    rows.push(
      <div key="zones" className="hud-line hud-zones" aria-label="持續區域">
        <span className="muted">持續區域：</span>
        <ul className="hud-summon-list">
          {zones.map((z) => {
            const next = zoneNextText(z);
            return (
              <li key={z.id}>
                {zoneLine(view, z, unitNames(view))}
                {next === "" ? "" : `；${next}`}
              </li>
            );
          })}
        </ul>
      </div>,
    );
  }
  return rows;
}
