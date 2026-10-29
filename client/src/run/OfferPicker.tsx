// 技能候選（升級三選一、營火重骰）：卡片順序由種子決定；每張標示「加深／橋接／新方向」與帶的關鍵字（Phase 3-24b2）；
// 偏離路線那張有明顯標籤；可跳過；欄位滿時選要換掉的技能。
import { useMemo } from "react";
import type { RunHero, RunOffer } from "../api/types";
import { Hint } from "../ui/Hint";
import { SkillCardView } from "../ui/SkillCardView";
import {
  displayOrder,
  needsReplacement,
  OFF_ROUTE_LABEL,
  offRouteHint,
  replaceOptions,
  SLOT_LABELS,
  slotOf,
} from "./flow";
import { isLlmTag, LLM_SOURCE_HINT, LLM_SOURCE_LABEL } from "./llmFlow";
import { offerTagHint, offerTagText } from "./startFlow";

interface Props {
  offer: RunOffer;
  hero: RunHero;
  runSeed: number;
  groupKey: string;
  pick: number | null;
  replace: string | null;
  /** 後端回 422（例如規則改變型傳說只能裝 1 個）後，替換清單改列全部技能。 */
  forceReplace?: boolean;
  disabled?: boolean;
  onPick(pick: number | null): void;
  onReplace(skillId: string | null): void;
}

export function OfferPicker({
  offer,
  hero,
  runSeed,
  groupKey,
  pick,
  replace,
  forceReplace = false,
  disabled = false,
  onPick,
  onReplace,
}: Props) {
  const order = useMemo(
    () => displayOrder(runSeed, groupKey, offer.candidates.length),
    [runSeed, groupKey, offer.candidates.length],
  );
  const picked = pick === null ? undefined : offer.candidates[pick];
  const must = picked !== undefined && (needsReplacement(hero.skills, picked) || forceReplace);
  return (
    <div className="run-offer">
      <div className="run-offer-cards">
        {order.map((index) => {
          const card = offer.candidates[index];
          if (card === undefined) return null;
          const off = offer.off_route.includes(index);
          const tag = offer.tags?.[index];
          return (
            <div
              key={card.id}
              className={`run-offer-card${pick === index ? " selected" : ""}${off ? " off-route" : ""}`}
            >
              {tag !== undefined && (
                <div className={`offer-kind-tag offer-kind-${tag.kind}`} data-testid="offer-kind">
                  <b>{offerTagText(tag)}</b>
                  <span className="small">　{offerTagHint(tag)}</span>
                </div>
              )}
              {isLlmTag(tag) && (
                <Hint text={LLM_SOURCE_HINT}>
                  <div className="offer-llm-tag" data-testid="offer-llm" tabIndex={0}>
                    <b>{LLM_SOURCE_LABEL}</b>
                  </div>
                </Hint>
              )}
              {off && (
                <div className="off-route-tag">
                  <b>{OFF_ROUTE_LABEL}</b>
                  <span className="small">　{offRouteHint(offer.top_attribute)}</span>
                </div>
              )}
              <SkillCardView card={card} />
              <button
                type="button"
                className={pick === index ? "primary" : ""}
                disabled={disabled}
                onClick={() => {
                  onPick(pick === index ? null : index);
                  onReplace(null);
                }}
              >
                {pick === index ? "已選這個（再按一次取消）" : "選這個"}
              </button>
            </div>
          );
        })}
      </div>
      <div className="muted small">
        不選任何一張就是跳過（技能不變）。{pick === null && "目前：跳過。"}
      </div>
      {picked !== undefined && must && (
        <div className="panel run-replace">
          <div className="section-title">{SLOT_LABELS[slotOf(picked)]}欄位已滿，請選一個要換掉的技能</div>
          <div className="run-replace-list">
            {replaceOptions(hero.skills, picked, forceReplace).map((s) => (
              <button
                key={s.id}
                type="button"
                className={replace === s.id ? "primary selected" : ""}
                disabled={disabled}
                onClick={() => onReplace(s.id)}
              >
                換掉「{s.name_zh}」
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
