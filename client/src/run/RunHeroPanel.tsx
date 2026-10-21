// 主角的一輪狀態：等級與經驗、HP／法力／源力、屬性、技能（點開看卡片）。
import type { RunHero } from "../api/types";
import { SkillCardView } from "../ui/SkillCardView";
import { WeaponIcon } from "../ui/WeaponIcon";
import { ATTRIBUTES, conHpBonus, hpDeltaText, SLOT_LABELS, SLOT_LIMITS, slotUsage, type SlotKind } from "./flow";

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
            {a.label} <b>{hero.attributes[a.id]}</b>
            {a.id === "con" && (
              <span className="muted" data-testid="con-hp-bonus">
                {" "}
                {hpDeltaText(conHpBonus(hero.attributes.con ?? hero.hp_con_base, hero.hp_con_base, hero.hp_per_con_point))}
              </span>
            )}
          </span>
        ))}
      </div>
      <div className="section-title">
        技能
        <span className="muted small">
          {kinds.map((k) => `${SLOT_LABELS[k]} ${usage[k]}/${SLOT_LIMITS[k]}`).join("・")}
        </span>
      </div>
      <ul className="run-skill-list">
        {hero.skills.map((s) => (
          <li key={s.id}>
            <details>
              <summary>
                {s.name_zh}{" "}
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
