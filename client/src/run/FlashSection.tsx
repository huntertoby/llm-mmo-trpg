// 靈感閃現區（Phase 3W-6）：戰鬥之間（含營火）花靈感點讓一招技能閃現。列出學會的技能、已閃次數與能不能閃，
// 按「閃現」進入出題前畫面（`FlashChooser`：不指定／指定類別）；出題後的 3 選 1 在 `RunFlashPending`。
import { useState } from "react";
import type { RunChoice, RunHero, SkillFlash } from "../api/types";
import { Hint } from "../ui/Hint";
import { HudBare, InfoTip } from "../ui/PanelKit";
import { SkillCardView } from "../ui/SkillCardView";
import { FlashChooser, type FlashPreviewLoader } from "./FlashChooser";
import { ownedSkills, rulesOf, showCanFlash, flashCountText, CAN_FLASH_TEXT } from "./flash";

interface Props {
  runId: string;
  hero: RunHero;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
  /** 閃現預覽的來源（大世界）；省略 ＝ 一輪的端點。 */
  previewFlash?: FlashPreviewLoader;
  /** 不能花點時的原因（大世界：不在城鎮或營火）；有值時閃現按鈕停用並以它為說明。 */
  lockedReason?: string | null;
}

/** 規則籌碼的 (i)（#19；原段落的後兩句）。 */
export const FLASH_RULE_TIP_ZH = "出題就會扣點，一定要選一個。要先在戰鬥中用過才能再閃。";

/** 一招能不能閃現、不能時的原因（閃現鈕的停用與說明卡；大世界面板與一輪共用）。 */
export function flashRowState(flash: SkillFlash | undefined, insight: number, rules: RunHero["flash_rules"], lockedReason: string | null): { can: boolean; reason: string | undefined } {
  const cost = rulesOf(rules).open_cost;
  const can = showCanFlash(flash) && insight >= cost && lockedReason === null;
  const reason = lockedReason ?? (flash?.complete ? "完整技能不能再閃現" : (flash?.flash_problem_zh ?? (insight < cost ? "靈感點不足" : undefined)));
  return { can, reason };
}

/** 規則籌碼三格（#19 新字）：「1 點　4 個變化選 1」「+1 點　指定類別、該類 3 選 1」「每招最多閃 5 次」＋(i)。數字照伺服器的 `flash_rules`。 */
export function flashRuleChips(rules: RunHero["flash_rules"]): { key: string; icon: "bulb" | "book"; strong: string; text: string; after?: string }[] {
  const r = rulesOf(rules);
  return [
    { key: "open", icon: "bulb", strong: `${r.open_cost} 點`, text: `${r.open_options} 個變化選 1` },
    { key: "focused", icon: "bulb", strong: `+${r.focused_cost - r.open_cost} 點`, text: `指定類別、該類 ${r.focused_options} 選 1` },
    { key: "max", icon: "book", strong: String(r.max_flashes), text: "每招最多閃 ", after: " 次" },
  ];
}

/**
 * 閃現規則籌碼（PNL-2；資訊面板-移植需求 4.1 #19）：原本一整段規則改成三個籌碼＋(i)。
 * 共用元件：大世界成長面板、一輪的營火與戰鬥之間（`FlashSection`）都用這一塊；營火其他排法不動（1.2）。
 */
export function FlashRuleChips({ rules }: { rules: RunHero["flash_rules"] }) {
  return (
    <div className="pnl-rule-chips" data-testid="flash-rule-chips">
      {flashRuleChips(rules).map((c) => (
        <span key={c.key} className="pnl-rule" data-rule={c.key}>
          <HudBare id={c.icon === "bulb" ? "bulb" : "bar_K"} px={14} />
          {c.after === undefined ? (
            <>
              <b>{c.strong}</b>
              {c.text}
            </>
          ) : (
            <>
              {c.text}
              <b>{c.strong}</b>
              {c.after}
            </>
          )}
        </span>
      ))}
      <InfoTip text={FLASH_RULE_TIP_ZH} />
    </div>
  );
}

export function FlashSection({ runId, hero, busy, onChoose, previewFlash, lockedReason = null }: Props) {
  const [target, setTarget] = useState<string | null>(null);
  const insight = hero.insight ?? 0;
  const skills = ownedSkills(hero);
  const chosen = skills.find((s) => s.card.id === target);
  return (
    <div className="panel run-flash" data-testid="run-flash">
      <h2>
        靈感閃現　<span className="muted small">靈感點 {insight}</span>
      </h2>
      <FlashRuleChips rules={hero.flash_rules} />
      {chosen !== undefined && (
        <FlashChooser
          key={chosen.card.id}
          runId={runId}
          previewFlash={previewFlash}
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
          const { can, reason } = flashRowState(flash, insight, hero.flash_rules, lockedReason);
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
