// 底部技能列（Phase 3-8）：基本動作（攻擊、推擊……）＋主動技能排成一排（超出寬度換成兩排，不捲動）；
// 被動、反應、姿態、修正以小圖示放在同一列最右側，點開看卡片（可施放的姿態點了照樣選取）。
// 5D-4：腰包的道具（卡片標籤 `item`，8.17）不佔技能欄位，放在獨立的「道具」群組（同種族技的群組樣式）。
// 灰掉原因、滑過看卡片、選取提示照舊；卡片用共用的浮動卡規則（`useFloatCard`，Phase 3-30）：貼齊按鈕上方，滑過約 150ms 顯示，
// 離開有 250ms 寬限可滑進卡片，點卡片或按 Shift 釘住，Esc／點外面關閉。
// 6A-1（開發 PM 定案）：觸控點一下按鈕只執行動作；長按約 0.4 秒開技能卡（釘住），放開不執行——取代以前「點一下釘住技能卡」。
import type { RaceView, SkillCard } from "../api/types";
import { passiveLine, raceBattleCardLines, raceUsesText } from "../battle/race";
import { minorGlyph, splitSkills } from "../battle/skillTray";
import type { ActionMode, SkillButton } from "../battle/targeting";
import { gearSkillBadge } from "../battle/gearSkills";
import { grantedBadge } from "../battle/granted";
import { activeVariantCard, variantBadge } from "../battle/variants";
import { conditionOffClass, conditionOffLabel } from "../battle/conditionOff";
import { ConditionOffNote, NowOffNote } from "./ConditionOffNote";
import { SkillCardView, type CardPin } from "./SkillCardView";
import { SkillIconView } from "./SkillIconView";
import { FloatCard, useFloatCard, type FloatApi } from "./useFloatCard";
import { Hint } from "./Hint";
import { keepWords } from "./keepWords";
import { PartTip } from "./PartTip";
import { opHintFullOnce, type OpHintKind } from "../battle/opHints";
import { costPieces, costPiecesTrailing, fitCost, skillNameLines } from "./skillCost";

interface Props {
  /** 基本動作的模式（防禦除外，防禦在右下角）。 */
  basic: readonly ActionMode[];
  /** 主角的種族與種族技的模式（Phase 3R-2；不佔技能欄，另列一組按鈕；沒有種族時省略）。 */
  race?: RaceView | null;
  raceModes?: readonly ActionMode[];
  buttons: readonly SkillButton[];
  cards: Readonly<Record<string, SkillCard | undefined>>;
  selectedKey: string | null;
  enabled: boolean;
  /** 技能列上方的一行提示（可移動格數、攻擊目標數、等待中……）。 */
  hint: string;
  /** 這行是操作說明句時的種類與這次的識別（6A-3：同一識別只算一次，前 3 次之後收進「?」）；狀態句省略。 */
  hintOnce?: { kind: OpHintKind; token: string } | null;
  onPickMode(mode: ActionMode): void;
  onSelect(skillId: string): void;
  /** 點到灰掉、有原因的技能：把原因交給畫面的訊息列（Phase 3-5c-2）。 */
  onBlocked?(button: SkillButton): void;
  /** 點到灰色的基本動作（例如推不動的「推動物件」）：把原因交給訊息列。 */
  onBlockedMode?(reason: string): void;
  /** PR-2b：測試模式（`BattleView.practice`）：技能鈕不寫冷卻。省略＝實戰。 */
  practice?: boolean;
}

/** 技能卡上的圖釘：釘住或取消（取消時卡片關閉）。 */
function cardPin(f: FloatApi): CardPin {
  return { pinned: f.pinned, toggle: () => (f.pinned ? f.ctl.dismiss() : f.ctl.click(false)) };
}

/** 卡片代價裡的冷卻那一段（「冷卻 2 回合」）。 */
const COOLDOWN_PART = /^冷卻 ?\d+( ?回合)?$/;

/**
 * 技能鈕第二行的幾段（6F-6：每段不拆開，段與段之間可以換行；冷卻中只有「冷卻 N」）。
 * PR-2b：測試模式（`practice`，靶場沒有冷卻）不寫冷卻；實戰照舊。
 */
export function costParts(b: Pick<SkillButton, "cooldown" | "costs">, practice = false): string[] {
  if (practice) {
    const parts = b.costs.filter((p) => !COOLDOWN_PART.test(p));
    return parts.length > 0 ? parts : ["…"];
  }
  if (b.cooldown > 0) return [`冷卻 ${b.cooldown}`];
  return b.costs.length > 0 ? b.costs : ["…"];
}

/** 名字超過這個字數改用小一號的字（6F-6：1040、800 寬時技能名被截斷）。 */
export const LONG_NAME_CHARS = 6;
/** 超過這個字數再縮一號、換成兩行（代價改成一行）。 */
export const XLONG_NAME_CHARS = 9;

/** 技能名的 class：長名字縮字（`long`），很長的再縮並換行（`xlong`）。字數照 Unicode 字元算。 */
export function skillNameClass(name: string): string {
  const n = [...name].length;
  if (n > XLONG_NAME_CHARS) return skillNameLines(name).tight ? "skill-name long xlong tight" : "skill-name long xlong";
  return n > LONG_NAME_CHARS ? "skill-name long" : "skill-name";
}

/**
 * 技能名（RT-3b，6F-7 檢查必修 1）：很長的名字由這裡決定斷點（「灰燼與霜雪交織的／鎖鏈陷阱」），
 * 不再讓瀏覽器任意斷（第二行只剩「阱」）；兩行放不下時縮字級（`tight`），再不行第二行加「…」。
 */
export function SkillName({ name }: { name: string }) {
  const cls = skillNameClass(name);
  if (!cls.includes("xlong")) return <span className={cls}>{name}</span>;
  const { lines } = skillNameLines(name);
  return (
    <span className={cls} aria-label={name}>
      {lines.map((l, i) => (
        <span key={i} className="skill-name-line">
          {l}
        </span>
      ))}
    </span>
  );
}

/** 第二行最多幾行：很長的名字（`xlong`，名字兩行）時一行，否則兩行（6F-6）。 */
export function costMaxLines(name: string): number {
  return skillNameClass(name).includes("xlong") ? 1 : 2;
}

/**
 * 第二行：「・」接在前一段後面，換行只發生在段與段之間（每段 `white-space: nowrap`；新的一行不以「・」開頭）。
 * 6F-7：放不下時先縮寫、再拿掉不是 AP、冷卻的段並加「…」（`skillCost.ts`），不會被裁成「AP 2・法力 5・」。
 */
export function CostLine({ parts, maxLines, trailingSep = false }: { parts: readonly string[]; maxLines: number; trailingSep?: boolean }) {
  // `trailingSep`（UI-E3c）：「・」留在上一段的行尾（技能面板的卡片）；戰鬥底列照舊
  const fit = fitCost(parts, maxLines);
  const pieces = trailingSep ? costPiecesTrailing(fit) : costPieces(fit);
  return (
    <span className="skill-cost">
      {pieces.map((p, i) => (
        <span key={`${i}:${p}`} className="skill-cost-part">
          {p}
        </span>
      ))}
    </span>
  );
}

function SkillSlot({
  b,
  card,
  selected,
  enabled,
  onSelect,
  onBlocked,
  practice = false,
}: {
  b: SkillButton;
  card: SkillCard | undefined;
  selected: boolean;
  enabled: boolean;
  onSelect(id: string): void;
  onBlocked?(b: SkillButton): void;
  practice?: boolean;
}) {
  const blocked = !enabled || b.disabledReason !== null;
  const reasoned = b.disabledReason !== null;
  // 點按鈕是施放／選取，所以點擊不釘住卡片；觸控長按才開卡片（6A-1）
  const f = useFloatCard({ pinOn: "hold", shiftPin: true });
  const variant = b.variant ?? null;
  const form = activeVariantCard(card, variant);
  return (
    <div className="skill-slot" {...f.triggerProps}>
      <button
        type="button"
        className={`skill-button${selected ? " selected" : ""}${b.grantedRemaining != null ? " granted" : ""}${b.gearSource != null ? " from-gear" : ""}${reasoned ? " blocked" : ""}${variant?.glow === true && !blocked ? " variant-ready" : ""}${conditionOffClass(b.conditionOff)}`}
        data-variant={form?.id}
        aria-label={b.conditionOff != null ? conditionOffLabel(b.name, b.conditionOff) : undefined}
        disabled={blocked && !reasoned}
        aria-disabled={blocked}
        onClick={() => (blocked ? onBlocked?.(b) : onSelect(b.skillId))}
      >
        <SkillIconView icon={form?.icon ?? card?.icon} size={40} className="skill-button-icon" />
        <span className="skill-button-text">
          <SkillName name={b.name} />
          {b.grantedRemaining != null && (
            <span className="skill-granted" aria-label="暫時技能">
              {grantedBadge(b.grantedRemaining)}
            </span>
          )}
          {b.gearSource != null && (
            <span className="skill-gear" aria-label={gearSkillBadge(b.gearSource)}>
              {gearSkillBadge(b.gearSource)}
            </span>
          )}
          {variant?.glow === true && (
            <span className="skill-variant" aria-label="戰場變奏">
              {variantBadge(card, variant)}
            </span>
          )}
          <CostLine parts={costParts(b, practice)} maxLines={costMaxLines(b.name)} />
        </span>
      </button>
      {f.open && card !== undefined && (
        <FloatCard float={f} className="skill-card-float">
          <NowOffNote reason={b.disabledReason} />
          <ConditionOffNote mark={b.conditionOff} />
          <SkillCardView card={card} compact activeVariantId={form?.id ?? null} pin={cardPin(f)} />
        </FloatCard>
      )}
    </div>
  );
}

/** 種族技按鈕（Phase 3R-2）：浮動卡列出說明、花費與次數、選取方式與環境被動；灰掉時卡片第一行說原因。 */
function RaceSlot({
  m,
  race,
  selected,
  enabled,
  onPick,
  onBlocked,
}: {
  m: ActionMode;
  race: RaceView;
  selected: boolean;
  enabled: boolean;
  onPick(m: ActionMode): void;
  onBlocked?(reason: string): void;
}) {
  const f = useFloatCard({ pinOn: "hold" });
  const reason = m.blockedReason;
  return (
    <div className="skill-slot race-slot" {...f.triggerProps}>
      <button
        type="button"
        className={`skill-button race-button${selected ? " selected" : ""}${reason !== undefined ? " blocked" : ""}`}
        disabled={!enabled}
        aria-disabled={reason !== undefined ? true : undefined}
        onClick={() => (reason === undefined ? onPick(m) : onBlocked?.(reason))}
      >
        <span className="skill-button-text">
          <span className="skill-name">{m.label}</span>
          <span className="skill-cost">{raceUsesText(race)}</span>
        </span>
      </button>
      {f.open && (
        <FloatCard float={f} className="skill-card-float float-panel race-card">
          <div className="section-title">
            {race.name_zh}・{race.skill_name_zh}
          </div>
          <NowOffNote reason={reason} />
          {raceBattleCardLines(race).map((line) => (
            <div key={line} className="small">
              {line}
            </div>
          ))}
          <div className="small muted">{passiveLine(race)}</div>
        </FloatCard>
      )}
    </div>
  );
}

/** 被動、反應、姿態的小圖示：可施放的姿態點了選取（觸控長按看卡片），其他點一下釘住卡片。 */
function MiniSlot({
  b,
  card,
  selected,
  enabled,
  onSelect,
}: {
  b: SkillButton;
  card: SkillCard | undefined;
  selected: boolean;
  enabled: boolean;
  onSelect(id: string): void;
}) {
  const usable = enabled && b.disabledReason === null && b.actions.length > 0;
  const f = useFloatCard({ pinOn: usable ? "hold" : "always", shiftPin: true });
  return (
    <span className="skill-mini-wrap" {...f.triggerProps}>
      <button
        type="button"
        className={`skill-mini${selected || f.pinned ? " selected" : ""}${conditionOffClass(b.conditionOff)}`}
        aria-label={conditionOffLabel(b.name, b.conditionOff)}
        aria-pressed={f.pinned}
        onClick={() => usable && onSelect(b.skillId)}
      >
        {card?.icon == null ? minorGlyph(b.name) : <SkillIconView icon={card.icon} size={28} />}
      </button>
      {f.open && card !== undefined && (
        <FloatCard float={f} className="skill-card-float">
          <ConditionOffNote mark={b.conditionOff} />
          <SkillCardView card={card} compact pin={cardPin(f)} />
        </FloatCard>
      )}
    </span>
  );
}

export function SkillBar(props: Props) {
  const { basic, buttons, cards, selectedKey, enabled, hint, hintOnce } = props;
  const { main, minor, items } = splitSkills(buttons, cards);
  const full = hintOnce == null || opHintFullOnce(hintOnce.kind, hintOnce.token);
  return (
    <div className="skill-bar" aria-label="技能列">
      {full ? (
        <div className="skill-hint small muted">{keepWords(hint)}</div>
      ) : (
        <div className="skill-hint small muted op-hint collapsed">
          <PartTip cat="操作說明" label={hintOnce.kind === "copy" ? "複製技能" : "移動與攻擊"} tip={hint}>
            <span className="op-hint-q" data-testid="op-hint-q">
              ?
            </span>
          </PartTip>
        </div>
      )}
      <div className="skill-row">
        <div className="skill-buttons">
          {basic.map((m) => (
            <Hint key={m.key} text={m.blockedReason}>
              <button
                type="button"
                className={`basic-button${selectedKey === m.key ? " selected" : ""}${m.blockedReason !== undefined ? " blocked" : ""}`}
                disabled={!enabled}
                aria-disabled={m.blockedReason !== undefined ? true : undefined}
                onClick={() => (m.blockedReason === undefined ? props.onPickMode(m) : props.onBlockedMode?.(m.blockedReason))}
              >
                {m.label}
              </button>
            </Hint>
          ))}
          {main.map((b) => (
            <SkillSlot
              key={b.skillId}
              b={b}
              card={cards[b.skillId]}
              selected={selectedKey === `skill:${b.skillId}`}
              enabled={enabled}
              onSelect={props.onSelect}
              onBlocked={props.onBlocked}
              practice={props.practice === true}
            />
          ))}
          {props.race != null && (props.raceModes ?? []).length > 0 && (
            <div className="race-group" aria-label="種族技">
              {(props.raceModes ?? []).map((m) => (
                <RaceSlot
                  key={m.key}
                  m={m}
                  race={props.race as RaceView}
                  selected={selectedKey === m.key}
                  enabled={enabled}
                  onPick={props.onPickMode}
                  onBlocked={props.onBlockedMode}
                />
              ))}
            </div>
          )}
          {items.length > 0 && (
            <div className="race-group item-group" aria-label="道具" data-testid="skill-item-group">
              <span className="item-group-label small muted">道具</span>
              {items.map((b) => (
                <SkillSlot
                  key={b.skillId}
                  b={b}
                  card={cards[b.skillId]}
                  selected={selectedKey === `skill:${b.skillId}`}
                  enabled={enabled}
                  onSelect={props.onSelect}
                  onBlocked={props.onBlocked}
                  practice={props.practice === true}
                />
              ))}
            </div>
          )}
          {basic.length === 0 && main.length === 0 && items.length === 0 && (props.raceModes ?? []).length === 0 && (
            <span className="muted small">（沒有可用的動作）</span>
          )}
        </div>
        {minor.length > 0 && (
          <div className="skill-minor" aria-label="被動、反應與姿態">
            {minor.map((b) => (
              <MiniSlot
                key={b.skillId}
                b={b}
                card={cards[b.skillId]}
                selected={selectedKey === `skill:${b.skillId}`}
                enabled={enabled}
                onSelect={props.onSelect}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
