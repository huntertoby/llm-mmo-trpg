// 戰鬥 HUD（設計文件 7.3）：固定顯示主角當下需要的資訊。
import type { BattleView, StatusView, UnitView } from "../api/types";
import { glossaryName, stackName, statusName, surfaceName } from "../battle/glossary";
import type { SkillNames } from "../battle/actions";
import { activationLine } from "../battle/activations";
import { grantedLine } from "../battle/granted";
import { bombStatusText, TIME_BOMB } from "../battle/bombs";
import { summonLine, summonsOf } from "../battle/summons";
import { unitNames } from "../battle/units";
import { zoneLine, zoneNextText, zonesOf } from "../battle/zones";

interface Props {
  view: BattleView;
  hero: UnitView | null;
  skills: SkillNames;
}

function Bar({ label, value, max, className, extra }: { label: string; value: number; max: number; className: string; extra?: string }) {
  const ratio = max <= 0 ? 0 : Math.max(0, Math.min(1, value / max));
  return (
    <div className="hud-bar">
      <span className="hud-bar-label">{label}</span>
      <div className="hud-bar-track">
        <div className={`hud-bar-fill ${className}`} style={{ width: `${ratio * 100}%` }} />
      </div>
      <span className="hud-bar-value">
        {value} / {max}
        {extra ?? ""}
      </span>
    </div>
  );
}

export function statusLine(s: StatusView): string {
  if (s.status_id === TIME_BOMB) return bombStatusText(s);
  const left = s.remaining === null ? "" : `（${s.remaining} 回合）`;
  const amount = s.amount === null ? "" : ` ${s.amount}`;
  return `${statusName(s.status_id)}${amount}${left}`;
}

/** 主角腳下的表面（中文）；沒有表面時「無」。 */
export function surfaceUnder(view: BattleView, hero: UnitView): string {
  const tile = view.tiles.find((t) => t.x === hero.pos.x && t.y === hero.pos.y);
  if (tile === undefined || tile.surface === "none") return "無";
  const left = tile.surface_remaining === null ? "" : `（${tile.surface_remaining} 輪）`;
  return `${surfaceName(tile.surface)}${left}`;
}

export function Hud({ view, hero, skills }: Props) {
  if (hero === null) return null;
  const stacks = Object.entries(hero.stacks).filter(([, n]) => n > 0);
  const cooldowns = Object.entries(hero.cooldowns).filter(([, n]) => n > 0);
  const summons = summonsOf(view, hero.id);
  return (
    <div className="panel hud" aria-label="主角狀態">
      <div className="hud-title">{hero.name_zh}</div>
      <Bar
        label="HP"
        value={hero.hp}
        max={hero.max_hp}
        className="hp"
        extra={hero.shield > 0 ? `（護盾 ${hero.shield}）` : ""}
      />
      <Bar label="法力" value={hero.mana} max={hero.max_mana} className="mana" />
      <Bar label="耐力" value={hero.stamina} max={hero.max_stamina} className="stamina" />
      <div className="hud-row">
        <span className="hud-chip" title="剩餘行動點數（自己的回合已含上回合保留的 AP）">
          AP <b>{hero.ap}</b>
          {hero.ap_carry > 0 && <span className="muted">（下回合保留 +{hero.ap_carry}）</span>}
        </span>
        <span className="hud-chip" title="剩餘移動點數">
          移動 <b>{hero.move_points}</b>
        </span>
        <span className="hud-chip" title="源力：傳說技能的代價（跨戰鬥保留，每場至少 1 點）">
          源力 <b>{hero.source}</b>/{hero.source_max}
        </span>
        <span className={`hud-chip ${hero.reaction_available ? "on" : "off"}`} title="本輪還能反應嗎">
          反應 <b>{hero.reaction_available ? "可用" : "已用"}</b>
        </span>
      </div>
      <div className="hud-line">
        <span className="muted">腳下表面：</span>
        {surfaceUnder(view, hero)}
      </div>
      <div className="hud-line">
        <span className="muted">層數：</span>
        {stacks.length === 0 ? "無" : stacks.map(([k, n]) => `${stackName(k)} ×${n}`).join("、")}
      </div>
      <div className="hud-line">
        <span className="muted">狀態：</span>
        {hero.statuses.length === 0 ? "無" : hero.statuses.map(statusLine).join("、")}
      </div>
      {(hero.activations ?? []).length > 0 && (
        <div className="hud-line hud-activations" aria-label="生效中的傳說">
          <span className="muted">傳說：</span>
          <ul className="hud-summon-list">
            {(hero.activations ?? []).map((a) => (
              <li key={a.skill_id}>{activationLine(view, a)}</li>
            ))}
          </ul>
        </div>
      )}
      {(hero.granted_skills ?? []).length > 0 && (
        <div className="hud-line hud-granted" aria-label="暫時技能">
          <span className="muted">暫時技能：</span>
          {(hero.granted_skills ?? []).map(grantedLine).join("、")}
        </div>
      )}
      {summons.length > 0 && (
        <div className="hud-line hud-summons" aria-label="召喚物">
          <span className="muted">召喚物：</span>
          <ul className="hud-summon-list">
            {summons.map((u) => (
              <li key={u.id}>{summonLine(view, u)}</li>
            ))}
          </ul>
        </div>
      )}
      {zonesOf(view).length > 0 && (
        <div className="hud-line hud-zones" aria-label="持續區域">
          <span className="muted">持續區域：</span>
          <ul className="hud-summon-list">
            {zonesOf(view).map((z) => {
              const next = zoneNextText(z);
              return (
                <li key={z.id}>
                  {zoneLine(view, z, unitNames(view))}
                  {next === "" ? "" : `；${next}`}
                </li>
              );
            })}
          </ul>
        </div>
      )}
      {cooldowns.length > 0 && (
        <div className="hud-line">
          <span className="muted">冷卻：</span>
          {cooldowns.map(([k, n]) => `${skills[k] ?? glossaryName("statuses", k)} ${n}`).join("、")}
        </div>
      )}
    </div>
  );
}
