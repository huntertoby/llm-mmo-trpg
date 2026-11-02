// 隊伍與系統傭兵（Phase 5C-1；docs/phases/Phase5計畫.md 22.7）：右側「隊伍」面板、小鎮的「雇用傭兵」清單
// （面板內展開，不是新的彈出層；主題說明用共用 <Hint>，浮動卡規則 6.5.1）。
import { useState } from "react";
import type { WorldAction, WorldPartyView } from "../api/types";
import { Hint } from "../ui/Hint";
import { groupByRole, hireLabel, hiredIds, sameParty, toggleMercenary } from "./party";

export function PartyPanel({ party }: { party: WorldPartyView }) {
  return (
    <div className="panel world-party" data-testid="world-party">
      <div className="section-title">
        隊伍　<span className="muted small">{party.members.length} 人（主角＋最多 {party.max_hired} 名）</span>
      </div>
      <ul className="world-party-members small">
        {party.members.map((m, i) => (
          <li key={i}>
            {m.name_zh}　<span className="muted">{m.title_zh}・{m.level} 級</span>
          </li>
        ))}
      </ul>
      {!party.can_hire && party.hire_problem_zh !== null && <div className="muted small">換傭兵：{party.hire_problem_zh}</div>}
    </div>
  );
}

interface HireProps {
  party: WorldPartyView;
  busy: boolean;
  onAct(action: WorldAction): void;
}

/** 雇用清單：依定位分組，每列＝勾選、暫名、稱號、技能概要；最多勾 `max_hired` 名。 */
export function HireEditor({ party, busy, onAct }: HireProps) {
  const [chosen, setChosen] = useState<string[]>(() => hiredIds(party));
  const full = chosen.length >= party.max_hired;
  return (
    <div className="world-hire" data-testid="world-hire">
      <div className="muted small">
        免費；最多 {party.max_hired} 名，勾選順序＝出場順序。強度照主角等級；出城後就不能換。
      </div>
      {groupByRole(party.mercenaries ?? []).map((g) => (
        <div key={g.role} className="world-hire-group">
          <div className="section-title small">{g.role_zh}</div>
          <ul className="world-hire-list">
            {g.members.map((m) => {
              const on = chosen.includes(m.id);
              return (
                <li key={m.id} className={on ? "chosen" : undefined}>
                  <label>
                    <input
                      type="checkbox"
                      checked={on}
                      disabled={busy || (!on && full)}
                      onChange={() => setChosen((cur) => toggleMercenary(cur, m.id, party.max_hired))}
                      data-testid={`world-hire-${m.id}`}
                    />
                    <Hint text={m.theme_zh}>
                      <span className="world-hire-name">{m.name_zh}</span>
                    </Hint>
                    <span className="muted small">{m.title_zh}</span>
                    {on && <span className="world-hire-order small">第 {chosen.indexOf(m.id) + 1} 位</span>}
                  </label>
                  <div className="muted small world-hire-skills">技能：{m.skills_zh.join("、")}</div>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
      <div className="run-actions">
        <button
          type="button"
          className="primary"
          disabled={busy || sameParty(party, chosen)}
          onClick={() => onAct({ kind: "hire", mercenaries: chosen })}
          data-testid="world-hire-apply"
        >
          {hireLabel(chosen, party.mercenaries ?? [])}
        </button>
      </div>
    </div>
  );
}

/** 小鎮選單的「雇用傭兵」按鈕＋展開的清單（`aria-expanded`，6.5.1）。 */
export function useHireToggle(party: WorldPartyView | null | undefined) {
  const [open, setOpen] = useState(false);
  const can = party != null && party.can_hire && (party.mercenaries ?? []).length > 0;
  return { open: open && can, can, toggle: () => setOpen((v) => !v), close: () => setOpen(false) };
}
