// 技能卡片（滑過技能按鈕時顯示；升級與營火候選卡、任務獎勵、工坊也用）。
// Phase 3-18a：大圖示用小圖模式；部件區是「組裝算式」，每個部件都能滑過或點一下看說明。
// Phase 6A-1（去文字化②）：常駐 3 行——名稱；AP 圓點、冷卻、射程、時機圖示；一行效果數字＋元素／縮放圖示。
// 其餘（稀有度與類型、代價句、形狀、組裝算式、關鍵字、條件、效果句、修正、算式、層數、召喚物、變奏、縮放與專精）
// 收進「▸ 詳細」，原本的資訊一項都不少。稀有度看外框顏色、類型看圖示形狀，標題列不再寫字。
// 每個圖示與效果數字都有說明卡（`Hint`，用卡片原本的句子；效果數字滑過看算式）。
import { useState } from "react";
import type { FlashRules, SkillCard, SkillFlash } from "../api/types";
import { RARITY_HINT } from "../run/flash";
import { Hint } from "./Hint";
import { SkillFlashInfo } from "./SkillFlashInfo";
import { categoryLabel, kindLabel, skeletonLabel, sourceCostText } from "../battle/source";
import { KeywordLine } from "./KeywordLine";
import { RuleText } from "./ruleText";
import { StackTip } from "./StackTip";
import { SummonInfo } from "./SummonInfo";
import { VariantList } from "./VariantList";
import { AssemblyFormula, SkillIconView } from "./SkillIconView";
import { SKILL_CARD_ICON_LEVEL } from "../render/skillIcon";
import { AttrGlyph, ChipGlyph, EffectGlyph, PinGlyph } from "./SkillCardGlyphs";
import { chipLine, effectLine } from "./skillCardLines";

/** 源力上限（`content/rules/core.yaml` 的 `source_max`）；HUD 與卡片都用 3 格圖示。 */
const SOURCE_MAX = 3;

/** 浮動卡的固定控制（技能列傳入）：圖釘按鈕＋「Shift 固定」提示。 */
export interface CardPin {
  pinned: boolean;
  toggle(): void;
}

interface Props {
  card: SkillCard;
  /** 緊湊版（技能列的浮動卡）：更小的圖示與間距，「詳細」裡不寫縮放、專精與設計概念。 */
  compact?: boolean;
  /** 目前生效的戰場變奏型態 id（技能列的浮動卡傳入，Phase 3-25b）。 */
  activeVariantId?: string | null;
  /** 不顯示設計概念（工坊玩家模式：隨機組合器的暫定句，Phase 3H-8）。 */
  hideConcept?: boolean;
  /** 這招的閃現狀態與規則（3W-6）：卡片上顯示「已閃 N／5 次」「可以閃現了」與變化歷程。 */
  flash?: SkillFlash | undefined;
  flashRules?: FlashRules | null | undefined;
  /** 「詳細」預設展開（工坊：本來就是看細節的地方，6A-1）。 */
  detailOpen?: boolean;
  /** 浮動卡的固定控制（技能列）；省略時不畫圖釘。 */
  pin?: CardPin | undefined;
}

/** 第 2 行：AP 圓點、資源、冷卻、射程、時機（每個圖示滑過有說明）。 */
function ChipRow({ card }: { card: SkillCard }) {
  const chips = chipLine(card);
  if (chips.length === 0) return null;
  return (
    <div className="skill-card-chips" data-testid="skill-card-line">
      {chips.map((c) => (
        <Hint key={c.key} text={c.hint}>
          <span className={`skill-chip chip-${c.icon}`} data-chip={c.icon} tabIndex={0}>
            <ChipGlyph icon={c.icon} />
            {c.pips !== undefined && Array.from({ length: c.pips }, (_, i) => <span key={i} className="skill-pip" />)}
            {c.label !== "" && <span className="skill-chip-label">{c.label}</span>}
          </span>
        </Hint>
      ))}
    </div>
  );
}

/** 第 3 行：效果數字＋元素／狀態名＋縮放屬性（數字滑過看效果句與算式）。 */
function EffectRow({ card }: { card: SkillCard }) {
  const line = effectLine(card);
  if (line.items.length === 0 && line.fallback === null) return null;
  return (
    <div className="skill-card-effline" data-testid="skill-card-line">
      {line.items.map((e) => (
        <Hint key={e.key} text={e.hint}>
          <span className={`skill-eff eff-${e.icon}`} data-effect={e.icon} data-element={e.element ?? undefined} tabIndex={0}>
            <EffectGlyph icon={e.icon} element={e.element} />
            {e.label !== "" && <b className="skill-eff-num">{e.label}</b>}
            {e.tag !== "" && <span className="skill-eff-tag">{e.tag}</span>}
          </span>
        </Hint>
      ))}
      {line.scaling.map((a) => (
        <Hint key={a.id} text={`縮放：${card.scaling}`}>
          <span className="skill-eff skill-eff-attr" data-attr={a.id} tabIndex={0}>
            <AttrGlyph label={a.label} />
            <span className="skill-eff-tag">{a.label}</span>
          </span>
        </Hint>
      ))}
      {line.fallback !== null && <span className="skill-eff-fallback">{line.fallback}</span>}
    </div>
  );
}

/** 「詳細」：原本卡片上的全部資訊（6A-1 以前的內容，順序不變）。 */
function Detail({ card, compact, activeVariantId, hideConcept }: Required<Pick<Props, "compact" | "hideConcept">> & Pick<Props, "card" | "activeVariantId">) {
  const source = sourceCostText(card, SOURCE_MAX);
  return (
    <>
      <div className="small muted skill-card-kind">
        <Hint text={RARITY_HINT}>
          <span className="skill-card-rarity" data-testid="skill-card-rarity" tabIndex={0}>
            {card.rarity}
          </span>
        </Hint>
        ・{kindLabel(card)}
        {skeletonLabel(card) !== "" && `・${skeletonLabel(card)}`}・{categoryLabel(card)}
      </div>
      <div className="small">{card.cost.join("，")}</div>
      {source !== null && <div className="small skill-card-source">傳說代價：{source}</div>}
      <div className="small muted">{card.shape}</div>
      <AssemblyFormula icon={card.icon} />
      <KeywordLine keywords={card.keywords} />
      {(card.weapon_only ?? null) !== null && (
        <div className="small skill-card-weapon-only">
          {card.weapon_only}（沒拿就不能裝備、不能施放）
        </div>
      )}
      {card.condition !== null && <div className="small">條件：{card.condition}</div>}
      {(card.timing ?? null) !== null && <div className="small">{card.timing}</div>}
      {(card.activation ?? null) !== null && <div className="small">啟動：{card.activation}（啟動前不生效）</div>}
      <ul className="skill-card-effects">
        {card.effects.map((e, i) => (
          <li key={`${i}:${e}`}>{e}</li>
        ))}
        {card.modifiers.map((m, i) => (
          <li key={`modifier:${i}:${m}`}>修正：{m}</li>
        ))}
      </ul>
      {(card.formula_lines ?? []).map((line) => (
        <div key={line} className="small skill-card-formula" data-testid="skill-formula">
          <RuleText text={line} />
        </div>
      ))}
      {(card.stacks ?? []).length > 0 && (
        <div className="small skill-card-stacks">
          層數：
          {(card.stacks ?? []).map((ref, i) => (
            <span key={`${ref.id}:${ref.role}`}>
              {i > 0 && "、"}
              <StackTip id={ref.id}>
                {ref.name_zh}（{ref.role === "makes" ? "累積" : "消耗／利用"}）
              </StackTip>
            </span>
          ))}
        </div>
      )}
      {(card.summons ?? []).map((info, i) => (
        <SummonInfo key={`${i}:${info.id}`} info={info} open={!compact} />
      ))}
      <VariantList card={card} activeId={activeVariantId ?? null} />
      {!compact && card.element != null && (
        <div className="small" data-testid="skill-element" data-element={card.element_id ?? undefined}>
          技能元素：{card.element}
        </div>
      )}
      {!compact && <div className="small muted">縮放：{card.scaling}</div>}
      {card.mastery !== null && !compact && <div className="small">專精：{card.mastery}</div>}
      {card.concept !== "" && !compact && !hideConcept && <div className="small muted">{card.concept}</div>}
    </>
  );
}

export function SkillCardView({ card, compact = false, activeVariantId = null, hideConcept = false, flash, flashRules, detailOpen = false, pin }: Props) {
  const [open, setOpen] = useState(detailOpen);
  return (
    <div className={`skill-card rarity-${card.rarity_id}${compact ? " compact" : ""}`} data-testid="skill-card">
      <div className="skill-card-head">
        <SkillIconView icon={card.icon} size={compact ? 48 : 56} level={SKILL_CARD_ICON_LEVEL} label={card.name_zh} />
        <div className="skill-card-headtext">
          <div className="skill-card-title" data-testid="skill-card-line">
            {card.name_zh}
          </div>
          <ChipRow card={card} />
        </div>
        {pin !== undefined && (
          <button
            type="button"
            className={`skill-card-pin${pin.pinned ? " pinned" : ""}`}
            aria-label={pin.pinned ? "取消固定" : "固定技能卡"}
            aria-pressed={pin.pinned}
            onClick={(e) => {
              e.stopPropagation(); // 卡片本身的點擊會釘住；圖釘要能取消
              pin.toggle();
            }}
          >
            <PinGlyph pinned={pin.pinned} />
          </button>
        )}
      </div>
      <EffectRow card={card} />
      <SkillFlashInfo flash={flash} rules={flashRules} />
      <details className="skill-card-detail" open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
        <summary className="skill-card-more small">
          <span>詳細</span>
          {pin !== undefined && <span className="skill-card-shift muted">Shift 固定</span>}
        </summary>
        <Detail card={card} compact={compact} activeVariantId={activeVariantId} hideConcept={hideConcept} />
      </details>
    </div>
  );
}
