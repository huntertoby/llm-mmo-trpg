// 技能點分配（Phase 3-26a）：每個主動技能可加減等級（花技能點，營火可以免費重配）；升級畫面把草稿
// 跟著「確定」一起送出，戰前與營火有自己的「確認分配」。3-26b：升到分歧進化那一級時，該列下方顯示兩支
// 進化的技能卡比較，選一支才能送出；用過的次數不夠時不能升並顯示原因。
import type { RunHero, SkillCard } from "../api/types";
import { SkillCardView } from "../ui/SkillCardView";
import { EvolutionCompare } from "./EvolutionCompare";
import { Hint } from "../ui/Hint";
import {
  adjustLevel,
  canLower,
  canRaise,
  draftCost,
  draftLevel,
  evolutionOptions,
  hasDraft,
  levelBadge,
  levelOf,
  missingEvolutions,
  pointsLeft,
  raiseBlockedText,
  type EvolveDraft,
  type LevelDraft,
} from "./skillGrowth";

interface Props {
  hero: RunHero;
  draft: LevelDraft;
  onDraft(next: LevelDraft): void;
  /** 分歧進化的選擇（Phase 3-26b）。 */
  evolve: EvolveDraft;
  onEvolve(next: EvolveDraft): void;
  disabled?: boolean;
  /** 有值時顯示「確認分配」（升級畫面不需要：草稿跟著升級選擇一起送出）。 */
  onConfirm?(): void;
  /** 營火才有：全部退回 1 級、點數退回（免費）。 */
  onRespec?(): void;
}

function Row({
  hero,
  card,
  draft,
  onDraft,
  evolve,
  onEvolve,
  disabled,
}: {
  hero: RunHero;
  card: SkillCard;
  draft: LevelDraft;
  onDraft(next: LevelDraft): void;
  evolve: EvolveDraft;
  onEvolve(next: EvolveDraft): void;
  disabled: boolean;
}) {
  const max = hero.skill_growth?.max_level ?? 5;
  const level = draftLevel(card, draft);
  const raised = level > levelOf(card);
  const blocked = raiseBlockedText(hero, card, draft);
  const options = evolutionOptions(hero, card, draft);
  return (
    <li className="growth-row" data-testid={`growth-${card.id}`}>
      <details className="growth-skill">
        <summary>{card.name_zh}</summary>
        <SkillCardView card={card} compact />
      </details>
      <span className="growth-controls">
        <button
          type="button"
          aria-label={`${card.name_zh} 降一級`}
          disabled={disabled || !canLower(card, draft)}
          onClick={() => onDraft(adjustLevel(hero, card, draft, -1))}
        >
          −
        </button>
        <span className={`growth-level${raised ? " raised" : ""}`}>
          {levelBadge(level)}
          <span className="muted small">/{max}</span>
        </span>
        <button
          type="button"
          aria-label={`${card.name_zh} 升一級`}
          disabled={disabled || !canRaise(hero, card, draft)}
          onClick={() => onDraft(adjustLevel(hero, card, draft, 1))}
        >
          ＋
        </button>
      </span>
      <span className={`growth-next small${blocked != null ? " growth-blocked" : " muted"}`}>
        {blocked ?? (level < max ? (card.growth?.next_text ?? "") : (card.growth?.trait_text ?? ""))}
      </span>
      {options.length > 0 && (
        <EvolutionCompare
          skillId={card.id}
          name={card.name_zh}
          options={options}
          picked={evolve[card.id]}
          disabled={disabled}
          onPick={(index) => onEvolve({ ...evolve, [card.id]: index })}
        />
      )}
    </li>
  );
}

export function SkillGrowthPanel({
  hero,
  draft,
  onDraft,
  evolve,
  onEvolve,
  disabled = false,
  onConfirm,
  onRespec,
}: Props) {
  const growth = hero.skill_growth;
  const missing = missingEvolutions(hero, draft, evolve);
  const actives = hero.skills.filter((s) => s.growth != null);
  const left = pointsLeft(hero, draft);
  const cost = growth?.upgrade_cost ?? 1;
  return (
    <div className="growth-panel" data-testid="growth-panel">
      <div className="section-title">
        技能點
        <span className="muted small" data-testid="growth-points">
          剩餘 {left} 點（每升 1 級花 {cost} 點，最高 Lv.{growth?.max_level ?? 5}）
          {hasDraft(draft) ? `　本次要花 ${draftCost(hero, draft)} 點` : ""}
        </span>
      </div>
      {actives.length === 0 ? (
        <div className="muted small">目前沒有可以升級的主動技能。</div>
      ) : (
        <ul className="growth-list">
          {actives.map((card) => (
            <Row
              key={card.id}
              hero={hero}
              card={card}
              draft={draft}
              onDraft={onDraft}
              evolve={evolve}
              onEvolve={onEvolve}
              disabled={disabled}
            />
          ))}
        </ul>
      )}
      {(onConfirm !== undefined || onRespec !== undefined) && (
        <div className="run-actions">
          {onConfirm !== undefined && (
            <button type="button" disabled={disabled || !hasDraft(draft) || missing.length > 0} onClick={onConfirm}>
              確認分配
            </button>
          )}
          {onRespec !== undefined && (
            <Hint text="全部技能退回 1 級，點數全部退回，之後可以重新分配">
              <button type="button" disabled={disabled} onClick={onRespec}>
                免費重配點數
              </button>
            </Hint>
          )}
        </div>
      )}
      {missing.length > 0 && (
        <div className="muted small" data-testid="evolve-missing">
          請先替 {missing.join("、")} 選一支進化。
        </div>
      )}
    </div>
  );
}
