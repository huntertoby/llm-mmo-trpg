// 大世界的「成長與技能」面板（Phase 5A-7；docs/phases/Phase5計畫.md 13.3）：重用一輪的配點、閃現、重閃、溶掉、傳承元件
// （送出的選擇轉成世界動作），加上誓約區。地點限制（城鎮與營火）由後端 `growth` 下發，不在可花點的地方時按鈕停用並顯示原因。
// PNL-2（docs/art/資訊面板-移植需求.md 3.3「成長與技能」）：固定區（標題＋回到地點圖、四個籌碼、不能花點時一行琥珀警告＋(i)）＋
// 四個分頁（靈感閃現｜屬性點｜整備｜外觀與種族）；整備分頁是三列摺疊（重閃、溶掉或傳承、誓約；一次只開一個）。
// 入門期的限制（`view.limits` 的 flash／dissolve／oath）拆到各頁：閃現頁的鎖住提示、整備摺疊右邊的鎖標籤（說明卡是伺服器原句）。
import { useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { RunChoice, WorldAction, WorldView } from "../api/types";
import { AttributeRespecSection } from "../run/AttributeRespecSection";
import { OldSkillSection, ReflashSection } from "../run/CampfireSkillCare";
import { FlashChooser } from "../run/FlashChooser";
import { FlashRuleChips, flashRowState } from "../run/FlashSection";
import { CAN_FLASH_TEXT, flashCountText, noFlashOptions, NO_FLASH_OPTIONS_TEXT, ownedSkills, reflashable, showCanFlash } from "../run/flash";
import { FlashPendingPanel } from "../screens/RunFlashPending";
import { fieldHeroInput, HeroFace } from "../ui/heroFace";
import { Hint } from "../ui/Hint";
import { Callout, Chip, EmptyNote, Fold, FoldGroup, HudBare, InfoTip, KeepNum, LockGlyph, PanelHead, PartBare, TabLine, Tag, EventBare } from "../ui/PanelKit";
import { PanelTabs, type PanelTabDef } from "../ui/PanelTabs";
import { SkillCardView } from "../ui/SkillCardView";
import { SkillIconView } from "../ui/SkillIconView";
import { LookChangeRow, RaceChangeRow } from "./GrowthLookRows";
import { choiceLabel, defaultParams, oathButton, paramLabel, spendLock, swearAction } from "./growth";
import {
  ATTR_EMPTY_ZH,
  ATTR_LINE_ZH,
  ATTR_PER_LEVEL_ZH,
  CARE_FOLD_ZH,
  CARE_FOLDS,
  CARE_LINE_ZH,
  CARE_PLACE_ZH,
  CHOSEN_TAG_ZH,
  FLASH_LOCK_ZH,
  GROWTH_TAB_ZH,
  GROWTH_TITLE_ZH,
  growthTabBadge,
  growthWarning,
  LEVEL4_TAG_ZH,
  NO_REFLASH_TIP_ZH,
  NO_REFLASH_ZH,
  NOT_NOW_ZH,
  type CareFold,
  type GrowthTabId,
} from "./growthPanel";
import { limitOf } from "./limits";

interface Props {
  view: WorldView;
  busy: boolean;
  /** 送出一輪元件的選擇（轉成世界動作）；回傳失敗時的 HTTP 狀態（成功為 `null`）。 */
  onChoose(choice: RunChoice): Promise<number | null>;
  onAct(action: WorldAction): Promise<number | null>;
  onClose(): void;
  /** 從別處的提醒點進來直接開的分頁（例：主角卡的靈感點 → 「靈感閃現」）；省略＝照預設（`pickTab`）。 */
  initialTab?: GrowthTabId | null;
}

const PLACE = "只在城鎮與營火";

export function WorldFlashPending({ view, busy, onChoose }: Pick<Props, "view" | "busy" | "onChoose">) {
  const pending = view.pending_flash;
  if (pending == null) return null;
  return (
    <div className="world-growth" data-testid="world-flash-pending">
      <div className="world-growth-lock small" role="status">
        先選完閃現的變化：選之前不能移動、開戰或使用其他服務。
      </div>
      <FlashPendingPanel key={`${pending.skill_id}:${pending.nth}:${pending.slot}`} pending={pending} hero={view.hero} busy={busy} onChoose={onChoose} />
    </div>
  );
}

/** 固定區（不捲）：標題＋回到地點圖、四個籌碼（0 灰）、不能花點時一行琥珀警告（原次行進 (i)；在城鎮不顯示）。 */
function GrowthHead({ view, onClose }: Pick<Props, "view" | "onClose">) {
  const c = view.character;
  const insight = view.growth.insight;
  const points = c.attribute_points;
  const warn = growthWarning(view);
  return (
    <>
      <PanelHead heading={GROWTH_TITLE_ZH} onBack={onClose} testId="world-growth-head" />
      <div className="pnl-chips" data-testid="world-growth-chips">
        <Chip icon={<HudBare id="bar_G" px={16} />} label="Lv" value={c.level} />
        <Chip icon={<HudBare id="rank" px={16} />} label="角色階級" value={view.growth.skill_tier} />
        <Chip icon={<HudBare id="bulb" px={15} />} label="靈感點" value={insight} zero={insight <= 0} />
        <Chip icon={<PartBare cat="skeleton" id="aura" px={16} />} label="未分配屬性點" value={points} zero={points <= 0} />
      </div>
      {warn !== null && (
        <Callout tone="warn" testId="world-service-note" end={<InfoTip text={`${view.growth.service_zh}。`} />}>
          <b>{NOT_NOW_ZH}</b>：<KeepNum text={warn} />
        </Callout>
      )}
    </>
  );
}

/** 鎖標籤＋說明卡（伺服器原句）。 */
function LockTag({ text, reason, testId }: { text: string; reason: string | null; testId?: string }) {
  return (
    <Hint text={reason}>
      <span className="pnl-tag-hit" tabIndex={0}>
        <Tag tone="lock" icon={<LockGlyph px={14} />} testId={testId}>
          {text}
        </Tag>
      </span>
    </Hint>
  );
}

/** 靈感閃現分頁：（入門期）鎖住提示「閃現：4 級起」→ 規則籌碼＋(i) → 每招一列（圖示 32、名字、L3 已閃次數、鎖標籤、閃現鈕）。 */
function FlashPane({ view, busy, onChoose }: Pick<Props, "view" | "busy" | "onChoose">) {
  const [target, setTarget] = useState<string | null>(null);
  const hero = view.hero;
  const cid = view.character.character_id;
  const limit = limitOf(view, "flash");
  const lock = limit ?? spendLock(view);
  const insight = hero.insight ?? view.growth.insight;
  const skills = ownedSkills(hero);
  const chosen = skills.find((s) => s.card.id === target);
  return (
    <div className="world-flash-pane" data-testid="run-flash">
      {limit !== null && (
        <Callout tone="lock" testId="world-limit-note">
          <b>{FLASH_LOCK_ZH.head}</b>：<KeepNum text={FLASH_LOCK_ZH.tail} />
        </Callout>
      )}
      <FlashRuleChips rules={hero.flash_rules} />
      {chosen !== undefined && (
        <FlashChooser
          key={chosen.card.id}
          runId={cid}
          previewFlash={(skill, slot) => api.worldFlashPreview(cid, skill, slot)}
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
      <ul className="pnl-rows" data-testid="flash-skill-list">
        {skills.map(({ card, flash, equipped }) => {
          const { can, reason } = flashRowState(flash, insight, hero.flash_rules, lock);
          const none = noFlashOptions(flash);
          return (
            <li key={card.id} className={none ? "pnl-row pnl-skill flash-none" : "pnl-row pnl-skill"} data-skill={card.id} data-flash-none={none ? 1 : undefined}>
              <SkillIconView icon={card.icon} size={32} />
              <details>
                <summary>
                  <span className="pnl-skill-name">
                    <span className="name">{card.name_zh}</span>
                    {!equipped && <span className="pnl-l3">（備用）</span>}
                    {showCanFlash(flash) && limit === null && <span className="skill-flash-ready small">{CAN_FLASH_TEXT}</span>}
                  </span>
                  <span className="pnl-l3">
                    <KeepNum text={flashCountText(flash, hero.flash_rules)} />
                  </span>
                  {none && (
                    <span className="flash-none-note" data-testid={`flash-none-${card.id}`}>
                      {NO_FLASH_OPTIONS_TEXT}
                    </span>
                  )}
                </summary>
                <SkillCardView card={card} flash={flash} flashRules={hero.flash_rules} />
              </details>
              <span className="pnl-skill-tag">{limit !== null && <LockTag text={LEVEL4_TAG_ZH} reason={limit} />}</span>
              <Hint text={can ? undefined : reason}>
                <span className="pnl-skill-btn">
                  <button
                    type="button"
                    className={target === card.id ? "primary" : ""}
                    disabled={busy || !can}
                    data-testid={`flash-open-${card.id}`}
                    onClick={() => setTarget(target === card.id ? null : card.id)}
                  >
                    閃現
                  </button>
                </span>
              </Hint>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** 屬性點分頁：入門期資訊條（伺服器的字）→「未分配的屬性點」＋「升級時每級 +2」→ 沒有點時虛線空狀態；配點與重配照現行。 */
function AttrPane({ view, busy, onChoose }: Pick<Props, "view" | "busy" | "onChoose">) {
  const lock = spendLock(view);
  const cid = view.character.character_id;
  const starter = view.growth.starter_note_zh ?? null;
  return (
    <div className="world-attr-pane" data-testid="world-growth-attr">
      {starter !== null && (
        <Callout tone="info" testId="world-growth-starter">
          <KeepNum text={starter} />
        </Callout>
      )}
      <TabLine end={<Tag tone="dim">{ATTR_PER_LEVEL_ZH}</Tag>}>
        <span>{ATTR_LINE_ZH}</span>
      </TabLine>
      {view.character.attribute_points <= 0 && (
        <EmptyNote testId="world-growth-attr-empty">
          <KeepNum text={ATTR_EMPTY_ZH} />
        </EmptyNote>
      )}
      <AttributeRespecSection
        hero={view.hero}
        busy={busy || (!view.growth.can_allocate && !view.growth.can_spend)}
        onChoose={onChoose}
        campfire={view.growth.at_service}
        runId={cid}
        previewAllocation={(attrs) => api.worldAllocationPreview(cid, attrs)}
        respecLocked={view.growth.can_spend ? null : lock}
        allocateNote="沒有遭遇時隨時可以分配；重配只在城鎮與營火。"
      />
    </div>
  );
}

/** 整備摺疊右邊的狀態標籤（#22、#23；說明卡是原句）。 */
function careFoldEnd(view: WorldView, fold: CareFold): ReactNode {
  if (fold === "reflash") {
    if (reflashable(view.hero).length > 0) return null;
    return (
      <Hint text={NO_REFLASH_TIP_ZH}>
        <span className="pnl-tag-hit" tabIndex={0}>
          <Tag tone="dim" testId="world-care-reflash-tag">
            {NO_REFLASH_ZH}
          </Tag>
        </span>
      </Hint>
    );
  }
  if (fold === "dissolve") {
    const reason = limitOf(view, "dissolve");
    return reason === null ? null : <LockTag text={LEVEL4_TAG_ZH} reason={reason} testId="world-care-dissolve-tag" />;
  }
  const reason = limitOf(view, "oath");
  return reason === null ? null : <LockTag text={CHOSEN_TAG_ZH} reason={reason} testId="world-care-oath-tag" />;
}

/** 整備分頁：第一行「重閃、溶掉與傳承、誓約」＋「只在城鎮與營火」；三列摺疊（同一組、一次只開一個），展開後照現行內容。 */
function CarePane({ view, busy, onChoose, onAct }: Pick<Props, "view" | "busy" | "onChoose" | "onAct">) {
  const cid = view.character.character_id;
  const lock = spendLock(view);
  const previewFlash = (skill: string, slot: number | null) => api.worldFlashPreview(cid, skill, slot);
  const body: Record<CareFold, ReactNode> = {
    reflash: <ReflashSection runId={cid} hero={view.hero} busy={busy || lock !== null} onChoose={onChoose} previewFlash={previewFlash} place={PLACE} bare />,
    dissolve: <OldSkillSection hero={view.hero} busy={busy || lock !== null || limitOf(view, "dissolve") !== null} onChoose={onChoose} place={PLACE} bare />,
    oath: <OathSection view={view} busy={busy} onAct={onAct} bare />,
  };
  return (
    <div className="world-care-pane" data-testid="campfire-care">
      <TabLine end={<Tag>{CARE_PLACE_ZH}</Tag>}>
        <span>{CARE_LINE_ZH}</span>
      </TabLine>
      <FoldGroup name="world-growth-care">
        {CARE_FOLDS.map((f) => (
          <Fold
            key={f}
            id={f}
            testId={`world-care-${f}`}
            summary={
              <span>
                <b>{CARE_FOLD_ZH[f].name}</b>　{CARE_FOLD_ZH[f].note}
              </span>
            }
            end={careFoldEnd(view, f)}
          >
            {body[f]}
          </Fold>
        ))}
      </FoldGroup>
    </div>
  );
}

/** 外觀與種族分頁：兩列設定列（外觀；本季還能免費換種族時多一列種族）。 */
function LookPane({ view, busy, onAct }: Pick<Props, "view" | "busy" | "onAct">) {
  return (
    <div className="pnl-rows" data-testid="world-growth-look">
      <LookChangeRow view={view} busy={busy} onAct={(a) => void onAct(a)} />
      {view.character.free_race_change === true && <RaceChangeRow view={view} busy={busy} onAct={(a) => void onAct(a)} />}
    </div>
  );
}

/** 「外觀與種族」分頁圖示：主角頭像不帶框（HUD 主角卡同一份外觀）；沒有外觀資料時用 HUD 的角色階級圖。 */
function LookIcon({ view }: { view: WorldView }) {
  const input = fieldHeroInput(view.character.hero_look ?? view.field?.hero);
  if (input === null) return <HudBare id="rank" px={16} />;
  return <HeroFace input={input} realm={view.character.origin_realm ?? null} size={16} bare />;
}

/** 四個分頁（順序照「玩家最常來做的事」；記號照 `growthTabBadge`）。 */
export function growthTabs(props: Pick<Props, "view" | "busy" | "onChoose" | "onAct">): PanelTabDef[] {
  const { view } = props;
  const icon: Record<GrowthTabId, ReactNode> = {
    flash: <HudBare id="bulb" px={16} />,
    attr: <PartBare cat="skeleton" id="aura" px={16} />,
    care: <EventBare id="b_rest" px={16} />,
    look: <LookIcon view={view} />,
  };
  const render: Record<GrowthTabId, () => ReactNode> = {
    flash: () => <FlashPane {...props} />,
    attr: () => <AttrPane {...props} />,
    care: () => <CarePane {...props} />,
    look: () => <LookPane {...props} />,
  };
  return (["flash", "attr", "care", "look"] as const).map((id) => ({
    id,
    label: GROWTH_TAB_ZH[id].label,
    short: GROWTH_TAB_ZH[id].short,
    hint: GROWTH_TAB_ZH[id].hint,
    icon: icon[id],
    badge: growthTabBadge(view, id),
    folds: id === "care" ? CARE_FOLDS : undefined,
    render: render[id],
  }));
}

export function WorldGrowth({ view, busy, onChoose, onAct, onClose, initialTab = null }: Props) {
  const tabs = growthTabs({ view, busy, onChoose, onAct });
  return (
    <div className="world-growth" data-testid="world-growth">
      <PanelTabs tabs={tabs} head={<GrowthHead view={view} onClose={onClose} />} initial={initialTab} testId="world-growth-tabs" />
    </div>
  );
}

function OathSection({ view, busy, onAct, bare = false }: Pick<Props, "view" | "busy" | "onAct"> & { bare?: boolean }) {
  const oath = view.oath;
  const [templateId, setTemplateId] = useState<string>(oath.templates?.[0]?.id ?? "");
  const template = (oath.templates ?? []).find((t) => t.id === templateId);
  const [params, setParams] = useState<Record<string, string | number>>(() => (template ? defaultParams(template) : {}));
  const [text, setText] = useState("");
  const [confirmRelease, setConfirmRelease] = useState(false);
  const button = oathButton(view);
  return (
    <div className={bare ? "world-oath" : "panel world-oath"} data-testid="world-oath">
      {!bare && <div className="section-title">誓約</div>}
      <p className="small muted">在城鎮或營火立誓，同時 1 個，一直有效到自己解除；解除後現實 1 天內不能再立。</p>
      {oath.available && (
        <p className="small muted" data-testid="world-oath-rules">
          {[oath.slot_zh, oath.penalty_zh].filter((s) => s !== undefined && s !== "").join("。")}
        </p>
      )}
      {oath.current != null ? (
        <div className="small" data-testid="world-oath-current">
          目前的誓約：<b>{oath.current.name_zh}</b>（難度 {oath.current.difficulty_zh}
          {oath.current.params_zh !== "" ? `・${oath.current.params_zh}` : ""}）
          {(oath.current.bonus_zh ?? "") !== "" && <div className="small">加成：{oath.current.bonus_zh}</div>}
          {(oath.current.judge_zh ?? "") !== "" && <div className="small muted">{oath.current.judge_zh}</div>}
          <div className="run-actions">
            {!confirmRelease ? (
              <button type="button" disabled={busy || !oath.can_release} onClick={() => setConfirmRelease(true)} data-testid="world-oath-release">
                解除誓約
              </button>
            ) : (
              <>
                <span className="small">解除後現實 1 天內不能再立誓，確定？</span>
                <button
                  type="button"
                  className="danger primary"
                  disabled={busy}
                  data-testid="world-oath-release-yes"
                  onClick={() => void onAct({ kind: "release_oath" }).then(() => setConfirmRelease(false))}
                >
                  確定解除
                </button>
                <button data-sfx="ui_cancel" type="button" disabled={busy} onClick={() => setConfirmRelease(false)}>
                  取消
                </button>
              </>
            )}
          </div>
        </div>
      ) : (
        oath.cooldown_zh != null && <div className="small muted">剛解除過誓約：還要 {oath.cooldown_zh} 才能再立。</div>
      )}
      {oath.current == null && oath.available && (
        <div className="world-oath-form">
          <label className="small">
            模板：
            <select
              value={templateId}
              disabled={busy}
              onChange={(e) => {
                setTemplateId(e.target.value);
                const next = (oath.templates ?? []).find((t) => t.id === e.target.value);
                setParams(next ? defaultParams(next) : {});
              }}
            >
              {(oath.templates ?? []).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name_zh}（{t.difficulty_zh}）
                </option>
              ))}
            </select>
          </label>
          {template !== undefined && (
            <div className="small world-oath-detail" data-testid="world-oath-detail">
              {(template.description_zh ?? "") !== "" && <div>{template.description_zh}</div>}
              {(template.bonus_zh ?? "") !== "" && <div>加成：{template.bonus_zh}</div>}
              {(template.judge_zh ?? "") !== "" && <div className="muted">{template.judge_zh}</div>}
            </div>
          )}
          {(template?.params ?? []).map((p) => (
            <label key={p.id} className="small">
              {paramLabel(p)}：
              {p.kind === "choice" ? (
                <select value={String(params[p.id] ?? "")} disabled={busy} onChange={(e) => setParams({ ...params, [p.id]: e.target.value })}>
                  {(p.choices ?? []).map((c) => (
                    <option key={c} value={c}>
                      {choiceLabel(p, c)}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="number"
                  min={p.min}
                  max={p.max}
                  value={Number(params[p.id] ?? p.min)}
                  disabled={busy}
                  onChange={(e) => setParams({ ...params, [p.id]: Number(e.target.value) })}
                />
              )}
            </label>
          ))}
          <label className="small">
            誓言（選填）：
            <input type="text" maxLength={200} value={text} disabled={busy} onChange={(e) => setText(e.target.value)} />
          </label>
        </div>
      )}
      {oath.current == null && (
        <div className="run-actions">
          <Hint text={button.reason ?? undefined}>
            <button
              type="button"
              className="primary"
              disabled={busy || button.reason !== null || template === undefined}
              data-testid="world-oath-swear"
              onClick={() => template !== undefined && void onAct(swearAction(template.id, params, text))}
            >
              {button.label}
            </button>
          </Hint>
        </div>
      )}
    </div>
  );
}
