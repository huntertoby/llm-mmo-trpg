// 技能卡縮小版（UI-E3；巡檢 #8、偷懶自查 G3）：和戰鬥底列同一張（`.skill-slot`＋`.skill-button`：40px 組裝式圖示、技能名、花費行），
// 用在戰鬥以外的面板（大世界的技能面板）。按鈕本身沒有動作：滑過約 150ms 開完整技能卡（共用浮動卡 6.5.1，可滑進），點一下釘住。
import type { SkillCard } from "../api/types";
import { NowOffNote } from "./ConditionOffNote";
import { CostLine, costMaxLines, SkillName } from "./SkillBar";
import { SkillCardView, type CardPin } from "./SkillCardView";
import { SkillIconView } from "./SkillIconView";
import type { Side } from "./floatCard";
import { FloatCard, useFloatCard, type FloatApi } from "./useFloatCard";

/** 卡片的花費行（同戰鬥底列 `targeting.ts` 的寫法；戰鬥外沒有冷卻）：被動／反應另標，傳說啟動另標。 */
export function cardCosts(card: Pick<SkillCard, "ap_cost" | "cost" | "activation_id">): string[] {
  if (card.ap_cost === null) return ["被動／反應", ...card.cost];
  const parts = [...card.cost, ...((card.activation_id ?? null) === null ? [] : ["傳說啟動"])];
  return parts.length > 0 ? parts : ["…"];
}

function cardPin(f: FloatApi): CardPin {
  return { pinned: f.pinned, toggle: () => (f.pinned ? f.ctl.dismiss() : f.ctl.click(false)) };
}

interface Props {
  card: SkillCard;
  /** 灰掉（例如主手別大類時不能用的武器技）與原因（卡片第一行）。 */
  blockedReason?: string | null;
  testId?: string;
  /**
   * 技能卡先開在哪一邊（UI-E3c 小修 5，6.5.1 第 6 點「預設上方」的明文例外）：大世界的技能面板傳 `"below"`，
   * 避免卡片往上蓋到主角卡的血條、法力條；下方放不下時照舊翻到上方。
   */
  prefer?: Side;
}

export function SkillTile({ card, blockedReason = null, testId, prefer = "above" }: Props) {
  const f = useFloatCard({ pinOn: "always", shiftPin: true });
  const blocked = blockedReason !== null;
  return (
    <div className="skill-slot skill-tile" data-testid={testId} data-blocked={blocked ? "1" : undefined} {...f.triggerProps}>
      <button type="button" className={`skill-button${blocked ? " blocked" : ""}${f.pinned ? " selected" : ""}`} aria-label={card.name_zh} aria-pressed={f.pinned}>
        <SkillIconView icon={card.icon} size={40} className="skill-button-icon" />
        <span className="skill-button-text">
          <SkillName name={card.name_zh} />
          <CostLine parts={cardCosts(card)} maxLines={costMaxLines(card.name_zh)} trailingSep />
        </span>
      </button>
      {f.open && (
        <FloatCard float={f} className="skill-card-float" prefer={prefer}>
          <NowOffNote reason={blockedReason} />
          <SkillCardView card={card} compact pin={cardPin(f)} />
        </FloatCard>
      )}
    </div>
  );
}
