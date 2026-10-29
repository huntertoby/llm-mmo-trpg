// 靈感閃現區（Phase 3W-6）：戰鬥之間（含營火）花靈感點讓一招技能閃現。列出學會的技能、已閃次數與能不能閃，
// 按「閃現」進入出題前畫面（`FlashChooser`：不指定／指定類別）；出題後的 3 選 1 在 `RunFlashPending`。
import { useState } from "react";
import type { RunChoice, RunHero } from "../api/types";
import { Hint } from "../ui/Hint";
import { SkillCardView } from "../ui/SkillCardView";
import { FlashChooser } from "./FlashChooser";
import { ownedSkills, rulesOf, showCanFlash, flashCountText, CAN_FLASH_TEXT } from "./flash";

interface Props {
  runId: string;
  hero: RunHero;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
}

export function FlashSection({ runId, hero, busy, onChoose }: Props) {
  const [target, setTarget] = useState<string | null>(null);
  const rules = rulesOf(hero.flash_rules);
  const insight = hero.insight ?? 0;
  const skills = ownedSkills(hero);
  const chosen = skills.find((s) => s.card.id === target);
  return (
    <div className="panel run-flash" data-testid="run-flash">
      <h2>
        靈感閃現　<span className="muted small">靈感點 {insight}</span>
      </h2>
      <p className="small muted">
        花 {rules.open_cost} 點靈感讓一招技能閃現：從 {rules.open_options} 個變化裡選 1 個；多花 {rules.focused_cost - rules.open_cost} 點可以指定類別，
        從該類 {rules.focused_options} 選 1。出題就會扣點，一定要選一個。每招最多閃 {rules.max_flashes} 次，要先在戰鬥中用過才能再閃。
      </p>
      {chosen !== undefined && (
        <FlashChooser
          key={chosen.card.id}
          runId={runId}
          hero={hero}
          skillId={chosen.card.id}
          skillName={chosen.card.name_zh}
          slot={null}
          busy={busy}
          onChoose={async (c) => {
            const status = await onChoose(c);
            if (status === null) setTarget(null);
            return status;
          }}
          onCancel={() => setTarget(null)}
        />
      )}
      <ul className="flash-skill-list" data-testid="flash-skill-list">
        {skills.map(({ card, flash, equipped }) => {
          const can = showCanFlash(flash) && insight >= rules.open_cost;
          const reason = flash?.complete
            ? "完整技能不能再閃現"
            : (flash?.flash_problem_zh ?? (insight < rules.open_cost ? "靈感點不足" : undefined));
          return (
            <li key={card.id} className="flash-skill-row">
              <details>
                <summary>
                  <b>{card.name_zh}</b>
                  {!equipped && <span className="muted small">（備用）</span>}
                  <span className="muted small">　{flashCountText(flash, hero.flash_rules)}</span>
                  {showCanFlash(flash) && <span className="skill-flash-ready small">{CAN_FLASH_TEXT}</span>}
                </summary>
                <SkillCardView card={card} flash={flash} flashRules={hero.flash_rules} />
              </details>
              <Hint text={can ? undefined : reason}>
                <button
                  type="button"
                  className={target === card.id ? "primary" : ""}
                  disabled={busy || !can}
                  data-testid={`flash-open-${card.id}`}
                  onClick={() => setTarget(target === card.id ? null : card.id)}
                >
                  閃現
                </button>
              </Hint>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
