// 戰鬥 HUD（設計文件 7.3）：固定顯示主角當下需要的資訊。
import type { BattleView, SkillCard, StatusView, UnitView } from "../api/types";
import { ammoPips, ammoText, hasMagazine } from "../battle/ammo";
import { chargeText } from "../battle/charges";
import { sourcePips } from "../battle/source";
import { statusIconTile, surfaceTile } from "../render/skillIcon";
import { ChargeChips } from "./ChargeChips";
import { TipGlyph } from "./SkillIconView";
import { COST_STATUS_NOTE, glossaryHasTag, glossaryName, stackName, statusName, surfaceName } from "../battle/glossary";
import type { SkillNames } from "../battle/actions";
import { activationLine } from "../battle/activations";
import { grantedLine } from "../battle/granted";
import { bombStatusText, TIME_BOMB } from "../battle/bombs";
import { CHARGING, chargeStatusText } from "../battle/followup";
import { summonLine, summonsOf } from "../battle/summons";
import { unitNames } from "../battle/units";
import { zoneLine, zoneNextText, zonesOf } from "../battle/zones";
import { Hint } from "./Hint";
import { StackTip } from "./StackTip";
import { actionCardText } from "../battle/actionInfo";
import { passiveLine, raceHudText } from "../battle/race";

interface Props {
  view: BattleView;
  hero: UnitView | null;
  skills: SkillNames;
  /** 技能卡（技能 ID → 卡片）：層數說明框用它列出「你的技能」中會累積／消耗該層數的（3-41c）。 */
  cards?: Readonly<Record<string, SkillCard | undefined>>;
  /** 縮成一行（窄螢幕，Phase 3-8）。 */
  compact?: boolean;
}

function Bar({ label, value, max, className, extra, hint }: { label: string; value: number; max: number; className: string; extra?: string; hint?: string | null }) {
  const ratio = max <= 0 ? 0 : Math.max(0, Math.min(1, value / max));
  return (
    <Hint text={hint}>
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
    </Hint>
  );
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

function SurfaceUnder({ view, hero }: { view: BattleView; hero: UnitView }) {
  const tile = view.tiles.find((t) => t.x === hero.pos.x && t.y === hero.pos.y);
  if (tile === undefined || tile.surface === "none") return <>無</>;
  return <TipGlyph tile={surfaceTile(tile.surface)} text={surfaceUnder(view, hero)} />;
}

/** 一行版的主角狀態（窄螢幕，Phase 3-8）。 */
export function compactHudText(view: BattleView, hero: UnitView): string {
  const stacks = Object.entries(hero.stacks).filter(([, n]) => n > 0);
  const parts = [
    `HP ${hero.hp}/${hero.max_hp}${hero.shield > 0 ? `（盾 ${hero.shield}）` : ""}`,
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

export function Hud({ view, hero, skills, cards, compact = false }: Props) {
  if (hero === null) return null;
  if (compact) {
    const text = compactHudText(view, hero);
    return (
      <Hint text={text}>
        <div className="panel hud hud-compact" aria-label="主角狀態">
          <b>{hero.name_zh}</b>　{text}
        </div>
      </Hint>
    );
  }
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
      <Bar label="耐力" value={hero.stamina} max={hero.max_stamina} className="stamina" hint={actionCardText("stamina")} />
      <div className="hud-row">
        <Hint text="剩餘行動點數（自己的回合已含上回合保留的 AP）">
          <span className="hud-chip">
            AP <b>{hero.ap}</b>
            {hero.ap_carry > 0 && <span className="muted">（下回合保留 +{hero.ap_carry}）</span>}
          </span>
        </Hint>
        <Hint text="剩餘移動點數">
          <span className="hud-chip">
            移動 <b>{hero.move_points}</b>
          </span>
        </Hint>
        {hasMagazine(hero) && (
          <Hint text={`${ammoText(hero)}：開火一次用掉 1 發，空膛時從「更多動作」選單裝填`}>
            <span className={`hud-chip ammo-chip${hero.ammo <= 0 ? " empty" : ""}`} aria-label={ammoText(hero)}>
              彈匣{" "}
              <span className="ammo-pips">
                {ammoPips(hero.ammo, hero.magazine).map((loaded, i) => (
                  <span key={i} className={`ammo-pip${loaded ? " loaded" : ""}`} />
                ))}
              </span>
              {hero.ammo <= 0 && <b className="ammo-empty">空膛</b>}
            </span>
          </Hint>
        )}
        <ChargeChips charges={hero.charges ?? []} />
        <Hint text={`源力 ${hero.source}/${hero.source_max}：傳說技能的代價（跨戰鬥保留，每場至少 1 點；走上地圖上的「源」格 +1）`}>
          <span className="hud-chip" aria-label={`源力 ${hero.source}/${hero.source_max}`}>
            源力{" "}
            <span className="source-pips">
              {sourcePips(hero.source, hero.source_max).map((filled, i) => (
                <span key={i} className={`source-pip${filled ? " filled" : ""}`} />
              ))}
            </span>
          </span>
        </Hint>
        <Hint text="本輪還能反應嗎">
          <span className={`hud-chip ${hero.reaction_available ? "on" : "off"}`}>
            反應 <b>{hero.reaction_available ? "可用" : "已用"}</b>
          </span>
        </Hint>
      </div>
      {hero.race != null && (
        <div className="hud-line hud-race" aria-label="種族">
          <span className="muted">種族：</span>
          <Hint text={passiveLine(hero.race)}>
            <span className="has-hint">{hero.race.name_zh}</span>
          </Hint>
          <span className="muted small">
            {" "}
            ・{hero.race.skill_name_zh}剩 {hero.race.skill_uses_left}／{hero.race.skill_uses_max} 次・被動「{hero.race.passive_name_zh}」
            {hero.race.passive_active ? "（目前有作用）" : ""}
          </span>
        </div>
      )}
      <div className="hud-line">
        <span className="muted">腳下表面：</span>
        <SurfaceUnder view={view} hero={hero} />
      </div>
      <div className="hud-line">
        <span className="muted">層數：</span>
        {stacks.length === 0
          ? "無"
          : stacks.map(([k, n], i) => (
              <span key={k}>
                {i > 0 && "、"}
                <StackTip id={k} cards={cards} owned={hero.skills}>
                  {stackName(k)} ×{n}
                </StackTip>
                {glossaryHasTag("stacks", k, "auto_consume") && (
                  <span className="muted small">（下一個傷害技能會吃掉）</span>
                )}
              </span>
            ))}
      </div>
      <div className="hud-line">
        <span className="muted">狀態：</span>
        {hero.statuses.length === 0 ? (
          "無"
        ) : (
          <span className="status-chips">
            {hero.statuses.map((s, i) => (
              <TipGlyph key={`${i}:${s.status_id}`} tile={statusIconTile(s.status_id)} text={statusLine(s)} />
            ))}
          </span>
        )}
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
