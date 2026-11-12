// 隊伍、系統傭兵與朋友的影子（Phase 5C-1、5C-2；docs/phases/Phase5計畫.md 22.7、23.9）：右側「隊伍」與
// 「我的影子」面板、小鎮的雇用清單（面板內展開、分「傭兵」「影子」兩頁，不是新的彈出層；說明用共用
// <Hint>，浮動卡規則 6.5.1）。
// UI-E3：傭兵的技能改成技能圖示列（最多 8 個，滑過看名字；`hireSkills.ts`）。
// UI-E3b：改用伺服器給的 `skill_ids` 取卡片；影子也畫圖示列（查不到卡片的生成技能照舊寫字）。
import { useMemo, useState } from "react";
import type { WorldAction, WorldAiChoice, WorldMyShadow, WorldPartyView } from "../api/types";
import { AccountTitles } from "../ui/AccountTitles";
import { Hint } from "../ui/Hint";
import { SkillIconView } from "../ui/SkillIconView";
import { useSkillCards } from "../ui/useSkillCards";
import { pairSkills, type HireSkill } from "./hireSkills";
import { PORTRAIT_SIZES } from "../render/portrait";
import { Portrait } from "./StoryIcons";
import { groupByRole, hireAction, hireLabel, hireLimit, hiredIds, hiredShadows, sameParty, toggleMercenary } from "./party";

export function PartyPanel({ party }: { party: WorldPartyView }) {
  return (
    <div className="panel world-party" data-testid="world-party">
      <div className="section-title">
        隊伍　<span className="muted small">{party.members.length} 人（主角＋最多 {party.max_hired} 名）</span>
      </div>
      <ul className="world-party-members small">
        {party.members.map((m, i) => (
          <li key={i}>
            {m.name_zh}　<span className="muted">{m.title_zh}・{m.level} 級{m.ai_zh != null ? `・打法 ${m.ai_zh}` : ""}</span>
            {m.note_zh != null && <span className="muted">（{m.note_zh}）</span>}
            {m.backstory_zh != null && m.backstory_zh !== "" && (
              <div className="muted world-party-backstory" data-testid="world-party-backstory">
                {m.backstory_zh}
              </div>
            )}
          </li>
        ))}
      </ul>
      {party.companion_zh != null && (
        <div className="muted small" data-testid="world-party-companion">
          {party.companion_zh}
        </div>
      )}
      {party.members.length === 1 && <div className="muted small">獨行：只帶主角（可以在城鎮雇傭兵或借影子）</div>}
      {party.season_boss_zh != null && <div className="muted small" data-testid="world-party-boss">{party.season_boss_zh}</div>}
      {!party.can_hire && party.hire_problem_zh !== null && <div className="muted small">換隊友：{party.hire_problem_zh}</div>}
    </div>
  );
}

function AiSelect({
  id,
  name,
  value,
  choices,
  busy,
  onChange,
}: {
  id: string;
  name: string;
  value: string | undefined;
  choices: readonly WorldAiChoice[];
  busy: boolean;
  onChange(value: string | undefined): void;
}) {
  const desc = choices.find((c) => c.id === value)?.description_zh;
  return (
    <div className="world-hire-ai small">
      <label>
        {name}的打法：
        <select
          value={value ?? ""}
          disabled={busy}
          onChange={(e) => onChange(e.target.value === "" ? undefined : e.target.value)}
          data-testid={`world-hire-ai-${id}`}
        >
          <option value="">預設</option>
          {choices.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name_zh}
            </option>
          ))}
        </select>
      </label>
      {desc !== undefined && <span className="muted">　{desc}</span>}
    </div>
  );
}

interface HireProps {
  party: WorldPartyView;
  busy: boolean;
  onAct(action: WorldAction): void;
}

type Tab = "mercenaries" | "shadows";

/**
 * 技能圖示列（UI-E3）：每招一個 24px 組裝式圖示，滑過看名字；對不上卡片的名字照舊寫字；超過 8 個寫「+N」。
 * UI-E3c 小修 9：圖示的說明牌優先開在下方（`prefer="below"`，6.5.1「預設上方」的例外），往上開會蓋住傭兵名字。
 */
export function SkillIconRow({ shown, rest, testId }: { shown: readonly HireSkill[]; rest: readonly string[]; testId?: string }) {
  const missing = shown.filter((s) => s.card === null).map((s) => s.name);
  return (
    <div className="world-hire-skills world-hire-icons" data-testid={testId}>
      {shown
        .filter((s) => s.card !== null)
        .map((s) => (
          <Hint key={s.name} text={s.name} prefer="below">
            <span className="world-hire-icon" tabIndex={0} aria-label={s.name}>
              <SkillIconView icon={s.card?.icon} size={24} label={s.name} />
            </span>
          </Hint>
        ))}
      {missing.length > 0 && <span className="muted small">{missing.join("、")}</span>}
      {rest.length > 0 && (
        <Hint text={rest.join("、")} prefer="below">
          <span className="world-hire-more small" tabIndex={0}>
            +{rest.length}
          </span>
        </Hint>
      )}
    </div>
  );
}

/** 雇用清單：「傭兵」依定位分組、「影子」列出其他角色存的影子；兩頁共用 `max_hired` 個隊友位。 */
export function HireEditor({ party, busy, onAct }: HireProps) {
  const [tab, setTab] = useState<Tab>("mercenaries");
  const [chosen, setChosen] = useState<string[]>(() => hiredIds(party));
  const [shadows, setShadows] = useState<string[]>(() => hiredShadows(party));
  const [ai, setAi] = useState<Record<string, string>>(() => ({ ...(party.ai ?? {}) }));
  const roster = party.mercenaries ?? [];
  const shadowList = party.shadows ?? [];
  const idKey = [...roster.flatMap((m) => m.skill_ids), ...shadowList.flatMap((s) => s.skill_ids)].join(",");
  const skillIds = useMemo(() => (idKey === "" ? [] : [...new Set(idKey.split(","))].sort()), [idKey]);
  const cardMap = useSkillCards(skillIds);
  const choices = party.ai_choices ?? [];
  const limit = hireLimit(party);
  const full = chosen.length + shadows.length >= limit;
  const setMemberAi = (id: string, value: string | undefined) =>
    setAi((cur) => {
      const next = { ...cur };
      if (value === undefined) delete next[id];
      else next[id] = value;
      return next;
    });
  const nameOf = (id: string) =>
    roster.find((m) => m.id === id)?.name_zh ?? `${shadowList.find((s) => s.owner === id)?.name_zh ?? id}的影子`;
  return (
    <div className="world-hire" data-testid="world-hire">
      <div className="muted small">
        免費；最多 {limit} 名隊友（傭兵與影子合計），勾選順序＝出場順序；全不勾＝獨行。出城後就不能換。
      </div>
      {party.companion_zh != null && <div className="muted small">{party.companion_zh}（不能換掉）</div>}
      <div className="run-actions world-hire-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "mercenaries"}
          className={tab === "mercenaries" ? "primary" : ""}
          onClick={() => setTab("mercenaries")}
          data-testid="world-hire-tab-mercenaries"
        >
          傭兵（{roster.length}）
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "shadows"}
          className={tab === "shadows" ? "primary" : ""}
          onClick={() => setTab("shadows")}
          data-testid="world-hire-tab-shadows"
        >
          影子（{shadowList.length}）
        </button>
      </div>
      {tab === "mercenaries" &&
        groupByRole(roster).map((g) => (
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
                        onChange={() => setChosen((cur) => toggleMercenary(cur, m.id, limit, shadows.length))}
                        data-testid={`world-hire-${m.id}`}
                      />
                      {/* RT-4（#131）：頭像框用出身區的區域色；沒有出身＝傭兵金 */}
                      <span className="world-hire-portrait" style={{ display: "inline-block", verticalAlign: "middle", margin: "0 6px" }}>
                        <Portrait portrait={m.portrait} region={m.origin ?? "merc"} size={PORTRAIT_SIZES.line} label={m.name_zh} />
                      </span>
                      <Hint text={m.theme_zh}>
                        <span className="world-hire-name">{m.name_zh}</span>
                      </Hint>
                      <span className="muted small">{m.title_zh}</span>
                      {on && <span className="world-hire-order small">第 {chosen.indexOf(m.id) + 1} 位</span>}
                    </label>
                    <SkillIconRow {...pairSkills(m.skills_zh, m.skill_ids, cardMap)} testId={`world-hire-skills-${m.id}`} />
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      {tab === "shadows" && (
        <div className="world-hire-group" data-testid="world-hire-shadows">
          <div className="muted small">其他角色最後一次在城鎮整備時存的影子；可以同時被很多人借。借用時強度不超過你（等級、技能階級）。</div>
          {shadowList.length === 0 ? (
            <div className="muted small">還沒有可借的影子（其他角色在城鎮整備後就會出現）。</div>
          ) : (
            <ul className="world-hire-list">
              {shadowList.map((s) => {
                const on = shadows.includes(s.owner);
                return (
                  <li key={s.owner} className={on ? "chosen" : undefined}>
                    <label>
                      <input
                        type="checkbox"
                        checked={on}
                        disabled={busy || (!on && full)}
                        onChange={() => setShadows((cur) => toggleMercenary(cur, s.owner, limit, chosen.length))}
                        data-testid={`world-hire-shadow-${s.owner}`}
                      />
                      <Hint text={`存在${s.saved_zh}・技能：${s.skills_zh.join("、") || "（無）"}`}>
                        <span className="world-hire-name">{s.name_zh}的影子</span>
                      </Hint>
                      <AccountTitles titles={s.titles} testId={`world-hire-titles-${s.owner}`} />
                      <span className="muted small">
                        Lv {s.level}・{s.role_zh}
                        {s.own === true ? "・自己的角色" : ""}
                      </span>
                      {on && <span className="world-hire-order small">第 {chosen.length + shadows.indexOf(s.owner) + 1} 位</span>}
                    </label>
                    {s.skills_zh.length === 0 ? (
                      <div className="muted small world-hire-skills">技能：（無）</div>
                    ) : (
                      <SkillIconRow {...pairSkills(s.skills_zh, s.skill_ids, cardMap)} testId={`world-hire-shadow-skills-${s.owner}`} />
                    )}
                    {s.cap_zh != null && (
                      <div className="small world-hire-cap" data-testid={`world-hire-cap-${s.owner}`}>
                        {s.cap_zh}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
      {choices.length > 0 &&
        [...chosen, ...shadows].map((id) => (
          <AiSelect key={id} id={id} name={nameOf(id)} value={ai[id]} choices={choices} busy={busy} onChange={(v) => setMemberAi(id, v)} />
        ))}
      <div className="run-actions">
        <button
          type="button"
          className="primary"
          disabled={busy || sameParty(party, chosen, shadows, ai)}
          onClick={() => onAct(hireAction(chosen, shadows, ai))}
          data-testid="world-hire-apply"
        >
          {hireLabel(chosen, roster, shadows, shadowList)}
        </button>
      </div>
    </div>
  );
}

/** 小鎮選單的「雇用隊友」按鈕＋展開的清單（`aria-expanded`，6.5.1）。 */
export function useHireToggle(party: WorldPartyView | null | undefined) {
  const [open, setOpen] = useState(false);
  const can = party != null && party.can_hire && (party.mercenaries ?? []).length > 0;
  return { open: open && can, can, toggle: () => setOpen((v) => !v), close: () => setOpen(false) };
}

/** 右側「我的影子」：等級、存的地點、預設打法、累計任務幣、被借用的戰報（#102）。 */
export function MyShadowPanel({
  shadow,
  choices,
  busy,
  onAct,
}: {
  shadow: WorldMyShadow;
  choices: readonly WorldAiChoice[];
  busy: boolean;
  onAct(action: WorldAction): void;
}) {
  const reports = shadow.reports_zh ?? [];
  return (
    <div className="panel world-my-shadow" data-testid="world-my-shadow">
      <div className="section-title">
        我的影子
        <span className="muted small">{shadow.saved ? shadow.saved_zh : "還沒存（在城鎮休息、換技能等整備時自動存）"}</span>
      </div>
      <div className="small">
        預設打法：
        {shadow.can_set_ai === true && choices.length > 0 ? (
          <select
            value={shadow.ai ?? ""}
            disabled={busy}
            onChange={(e) => onAct({ kind: "shadow_ai", profile: e.target.value === "" ? null : e.target.value })}
            data-testid="world-shadow-ai"
          >
            <option value="">預設</option>
            {choices.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name_zh}
              </option>
            ))}
          </select>
        ) : (
          <span>{shadow.ai_zh}</span>
        )}
        <span className="muted">　被借用得到的任務幣：{shadow.coins ?? 0}</span>
      </div>
      {reports.length === 0 ? (
        <div className="muted small">還沒有人借過你的影子。</div>
      ) : (
        <ul className="small world-shadow-reports" data-testid="world-shadow-reports">
          {reports.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
