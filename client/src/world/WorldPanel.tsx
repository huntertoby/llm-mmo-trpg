// 地點圖右側（Phase 5A-5）：遇敵陣容（開戰／撤退，9.6.6）、角色狀態、時刻與天氣、目前地點的服務
// （城鎮：休息、換技能、傳送；野外：紮營；營火：換技能，9.6.7 #2、#114）、趕路切換、最近事件。
import { useState } from "react";
import type { WorldAction, WorldView } from "../api/types";
import { LoadoutEditor } from "../run/LoadoutEditor";
import { Hint } from "../ui/Hint";
import { statusLine } from "./mapView";

interface Props {
  view: WorldView;
  busy: boolean;
  hasten: boolean;
  onHasten(on: boolean): void;
  onAct(action: WorldAction): void;
  onBattle(): void;
  log: readonly string[];
}

export function EncounterPanel({ view, busy, onAct, onBattle }: Pick<Props, "view" | "busy" | "onAct" | "onBattle">) {
  const e = view.encounter;
  if (e === null) return null;
  return (
    <div className="panel world-encounter" data-testid="world-encounter" role="region" aria-label="遇敵">
      <div className="section-title">遇敵！{e.location_name_zh}</div>
      <div className="small">
        敵人等級 {e.enemy_level}・戰場 {e.map_name_zh}・{e.weather_zh}・{e.day_phase_zh}
      </div>
      <ul className="world-enemies">
        {e.enemies.map((x, i) => (
          <li key={i} className={x.elite ? "elite" : undefined}>
            {x.name_zh}
            {x.elite && <span className="world-elite-tag">精英{x.affix_zh !== null ? `・${x.affix_zh}` : ""}</span>}
          </li>
        ))}
      </ul>
      <div className="muted small">
        我方：主角（開場 HP {e.hero_hp}{e.fatigued ? "，疲憊" : ""}）＋ 2 名標準隊友
      </div>
      <div className="run-actions">
        <button type="button" className="primary" disabled={busy} onClick={onBattle} data-testid="world-fight">
          {e.in_battle ? "繼續戰鬥" : "開戰"}
        </button>
        {!e.in_battle && (
          <Hint text={`不打，退回${e.retreat_to_zh}（不扣任何東西）`}>
            <button type="button" disabled={busy} onClick={() => onAct({ kind: "retreat" })} data-testid="world-retreat">
              撤退
            </button>
          </Hint>
        )}
      </div>
    </div>
  );
}

function HerePanel({ view, busy, hasten, onHasten, onAct }: Pick<Props, "view" | "busy" | "hasten" | "onHasten" | "onAct">) {
  const here = view.here;
  const [editing, setEditing] = useState(false);
  const free = view.encounter === null && view.battle_id === null;
  return (
    <div className="panel world-here" data-testid="world-here">
      <div className="section-title">
        {here.name_zh}　<span className="muted small">{here.kind_zh}{here.camped ? "・營火中" : ""}</span>
      </div>
      {here.description_zh !== "" && <div className="muted small">{here.description_zh}</div>}
      <div className="run-actions">
        {here.can_rest && (
          <Hint text="HP、法力、耐力回滿，補給補到初值（免費）">
            <button type="button" disabled={busy} onClick={() => onAct({ kind: "rest" })} data-testid="world-rest">
              休息
            </button>
          </Hint>
        )}
        {free && here.camp_problem_zh === null && (
          <Hint text={`花 ${here.camp_cost} 補給紮營：HP、法力、耐力回滿，可以換技能`}>
            <button type="button" disabled={busy} onClick={() => onAct({ kind: "camp" })} data-testid="world-camp">
              紮營
            </button>
          </Hint>
        )}
        {here.can_loadout && (
          <button type="button" aria-expanded={editing} disabled={busy} onClick={() => setEditing((v) => !v)} data-testid="world-loadout">
            {editing ? "收起換技能" : "換技能"}
          </button>
        )}
        {here.teleports.map((t) => (
          <button key={t.region} type="button" disabled={busy} onClick={() => onAct({ kind: "teleport", region: t.region })}>
            傳送到{t.name_zh}
          </button>
        ))}
      </div>
      {free && here.camp_problem_zh !== null && !here.can_rest && <div className="muted small">紮營：{here.camp_problem_zh}</div>}
      {here.can_loadout && editing && (
        <LoadoutEditor
          key={view.character.skills.map((s) => s.id).join(",")}
          hero={view.character}
          disabled={busy}
          onApply={(ids) => onAct({ kind: "loadout", skills: [...ids] })}
        />
      )}
      {here.can_loadout && editing && <div className="muted small">欄位上限：{view.character.slots_zh}</div>}
      <label className="world-hasten">
        <input type="checkbox" checked={hasten} disabled={busy} onChange={(e) => onHasten(e.target.checked)} data-testid="world-hasten" />
        趕路（每步花 {here.hasten_cost} 補給，遇敵機率減半）
      </label>
    </div>
  );
}

export function WorldPanel(props: Props) {
  const { view, log } = props;
  const c = view.character;
  return (
    <div className="world-side">
      <EncounterPanel {...props} />
      <div className="panel world-status" data-testid="world-status">
        <div className="section-title">
          {c.name}　<span className="muted small">{c.weapon_name_zh}{c.race_name_zh !== null ? `・${c.race_name_zh}` : ""}</span>
          {c.fatigued && (
            <Hint text="上一場全滅：下一場戰鬥開場 HP 打折，打完一場就消失">
              <span className="world-fatigue">疲憊</span>
            </Hint>
          )}
        </div>
        <div className="small">{statusLine(c)}</div>
        {c.attribute_points > 0 && <div className="muted small">未分配屬性點 {c.attribute_points}（分配之後的段開放）</div>}
        <div className="small world-skills">技能：{c.skills.map((s) => s.name_zh).join("、") || "（無）"}</div>
        <div className="muted small">
          {view.map.name_zh}・{view.clock.time_zh}（{view.clock.day_phase_zh}）・{view.clock.weather_zh}
        </div>
      </div>
      <HerePanel {...props} />
      <div className="panel world-log" data-testid="world-log">
        <div className="section-title">最近發生的事</div>
        {log.length === 0 ? (
          <div className="muted small">點地圖上發亮的相鄰地點走過去。</div>
        ) : (
          <ul>
            {log.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
