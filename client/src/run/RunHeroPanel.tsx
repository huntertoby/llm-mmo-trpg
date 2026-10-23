// 主角的一輪狀態：等級與經驗、HP／法力／耐力／源力、屬性、技能（點開看卡片）。
import type { RunHero } from "../api/types";
import { SkillCardView } from "../ui/SkillCardView";
import { WeaponIcon } from "../ui/WeaponIcon";
import { levelBadge, levelOf } from "./skillGrowth";
import {
  ATTRIBUTES,
  affectsOf,
  affectsText,
  attributeLabel,
  conHpBonus,
  hpDeltaText,
  perkText,
  SLOT_LABELS,
  SLOT_LIMITS,
  slotUsage,
  type SlotKind,
} from "./flow";

/** 有效屬性（含裝備；常駐數值的階數依它算）。舊回應沒有時退回基礎屬性。 */
function effectiveOf(hero: RunHero, id: string): number {
  const eff = (hero.effective_attributes ?? {}) as Record<string, number>;
  return eff[id] ?? (hero.attributes as Record<string, number>)[id] ?? 0;
}

function signed(n: number): string {
  return n >= 0 ? `+${n}` : `${n}`;
}

function Bar({ label, value, max, kind }: { label: string; value: number; max: number; kind: string }) {
  const pct = max <= 0 ? 0 : Math.max(0, Math.min(100, Math.round((value / max) * 100)));
  return (
    <div className="run-bar">
      <span className="run-bar-label">{label}</span>
      <span className="run-bar-track">
        <span className={`run-bar-fill run-bar-${kind}`} style={{ width: `${pct}%` }} />
      </span>
      <span className="run-bar-num">
        {value} / {max}
      </span>
    </div>
  );
}

export function RunHeroPanel({ hero }: { hero: RunHero }) {
  const usage = slotUsage(hero.skills);
  const traits: readonly string[] = (hero as { weapon_traits_zh?: readonly string[] }).weapon_traits_zh ?? [];
  const kinds = Object.keys(SLOT_LIMITS) as SlotKind[];
  return (
    <div className="panel run-hero">
      <div className="hud-title">
        {hero.name_zh}　<span className="muted">Lv {hero.level}</span>
        <span className="muted small">
          {" "}
          經驗 {hero.xp}
          {hero.xp_next !== null ? ` / ${hero.xp_next}` : "（已達上限）"}
        </span>
      </div>
      <Bar label="HP" value={hero.hp} max={hero.max_hp} kind="hp" />
      <Bar label="法力" value={hero.mana} max={hero.max_mana} kind="mana" />
      <Bar label="耐力" value={hero.stamina} max={hero.max_stamina} kind="stamina" />
      <div className="run-bar">
        <span className="run-bar-label">源力</span>
        <span className="run-source">
          {Array.from({ length: hero.source_max }, (_, i) => (i < hero.source ? "●" : "○")).join("")}
        </span>
      </div>
      <div className="run-weapon" data-testid="run-weapon">
        <WeaponIcon weaponId={hero.weapon} weaponClass={hero.weapon_class} size={24} />
        <span className="muted">武器</span> <b>{hero.weapon_name_zh === "" ? hero.weapon : hero.weapon_name_zh}</b>
      </div>
      {traits.length > 0 && (
        <div className="weapon-traits small muted" data-testid="run-weapon-traits">
          {traits.map((line) => (
            <div key={line}>{line}</div>
          ))}
        </div>
      )}
      <div className="run-attrs small">
        {ATTRIBUTES.map((a) => (
          <span key={a.id}>
            {a.label} <b>{effectiveOf(hero, a.id)}</b>
            {effectiveOf(hero, a.id) !== hero.attributes[a.id] && (
              <span className="muted" data-testid={`attr-gear-${a.id}`}>
                {" "}
                （基礎 {hero.attributes[a.id]}，裝備 {signed(effectiveOf(hero, a.id) - (hero.attributes[a.id] ?? 0))}）
              </span>
            )}
            {a.id === "con" && (
              <span className="muted" data-testid="con-hp-bonus">
                {" "}
                {hpDeltaText(conHpBonus(hero.attributes.con ?? hero.hp_con_base, hero.hp_con_base, hero.hp_per_con_point))}
              </span>
            )}
          </span>
        ))}
      </div>
      {(hero.attribute_perks ?? []).length > 0 && (
        <ul className="run-attr-perks small" data-testid="run-attr-perks">
          {(hero.attribute_perks ?? []).map((p) => (
            <li key={`${p.attr}-${p.per_tier_zh}`} className={p.tier > 0 ? "" : "muted"}>
              <b>{attributeLabel(p.attr)}</b>　{perkText(p)}
              {affectsText(affectsOf(hero.attribute_affects, p.attr)) !== null && (
                <div className="muted" data-testid={`panel-affects-${p.attr}`}>
                  {affectsText(affectsOf(hero.attribute_affects, p.attr))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      <div className="section-title">
        技能
        <span className="muted small">
          {kinds.map((k) => `${SLOT_LABELS[k]} ${usage[k]}/${SLOT_LIMITS[k]}`).join("・")}
        </span>
      </div>
      {(hero.skill_points ?? 0) > 0 && (
        <div className="small run-skill-points-hint" data-testid="run-skill-points">
          未花的技能點：<b>{hero.skill_points}</b>
        </div>
      )}
      <ul className="run-skill-list">
        {hero.skills.map((s) => (
          <li key={s.id}>
            <details>
              <summary>
                {s.name_zh}{" "}
                {s.growth != null && <b className="skill-level-badge">{levelBadge(levelOf(s))}</b>}{" "}
                <span className="muted small">
                  {s.kind}・{s.rarity}
                </span>
              </summary>
              <SkillCardView card={s} />
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}
