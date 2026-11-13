// 靈感閃現「選變體」畫面（Phase 3W-6；FL-1b 改版，docs/art/靈感閃現選擇-移植需求.md）。點數已經扣了，一定要選一個。
// 三段：上固定區（標頭、說明行、原技能列，原技能只出現一次）＋選項清單（白話大標＋只列有變的「前 → 後」，點整張卡選中）＋
// 下固定區（選中的大標、一句話、轉型的卸下選單、「確定」）。一輪與大世界共用：
// - 大世界 HUD 面板（`PopupFrame slots`）：上下固定區 portal 進框的 `ui-popup-head`／`ui-popup-foot`，只有選項區在框內捲；
// - 一輪（`RunScreen` 直接放在 `run-main`，頁面本身會捲）：三段照排，下固定區 `position: sticky; bottom: 0`（第 12 節決定 3）。
// 寬版／窄版看面板寬（容器查詢 559px），兩種字都畫、CSS 切換。
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import type { FlashOption, PendingFlash, RunChoice, RunHero, RunResponse } from "../api/types";
import { ownedCards } from "../run/loadout";
import { optionTag, pickChoice, pickReady, sortedOptions } from "../run/flash";
import {
  FLASH_PICK_NONE_ZH,
  FLASH_PICK_SUBTITLE_ZH,
  FLASH_PICK_TITLE_ZH,
  FLASH_SAME_AS_NOW_ZH,
  anyUnequipMenu,
  hasTransform,
  headlineOf,
  llmNamed,
  noteOf,
  paidTag,
  renamedTo,
  pendingWhat,
  sameAsNow,
  sayText,
  showsUnequipMenu,
  stepPick,
  unequipPrompt,
} from "../run/flashChoice";
import { BaseStrip, DiffRows, Term, TermText, type Terms } from "../run/FlashChoiceParts";
import { mustPickText } from "../run/reflashWeaker";
import { HudBare, InfoTip, Tag } from "../ui/PanelKit";
import { usePopupSlots } from "../ui/PopupFrame";
import { PopupSlot } from "../ui/PopupSlot";
import { SkillIconView } from "../ui/SkillIconView";

type Props = {
  run: RunResponse;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
};

export function RunFlashPending({ run, busy, onChoose }: Props) {
  const pending = run.pending_flash;
  if (pending === null || pending === undefined) return null;
  return <FlashPendingPanel pending={pending} hero={run.hero} busy={busy} onChoose={onChoose} />;
}

type PanelProps = {
  pending: PendingFlash;
  hero: RunHero;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
  /** 大世界鎖住時的提示（寬版第 2 行下一行，窄版收進 (i)；一輪沒有）。 */
  lockNote?: string;
};

/** 上固定區：標頭（寬版兩行、窄版一行＋(i)）＋原技能列。 */
function FlashHead({ pending, name, lockNote, base }: { pending: PendingFlash; name: string; lockNote: string | undefined; base: ReactNode }) {
  const must = mustPickText(pending); // RR-2：較弱的重閃換成伺服器的 weaker_foot_zh
  const tip = lockNote === undefined ? `${must}。` : `${must}。${lockNote}`;
  return (
    <div className="fc-fixed" data-testid="flash-head">
      <div className="fc-head wide-only">
        <h2 className="fc-title">
          <HudBare id="bulb" px={22} />
          {FLASH_PICK_TITLE_ZH}
          <small>{FLASH_PICK_SUBTITLE_ZH}</small>
        </h2>
      </div>
      <div className="fc-sub wide-only">
        <b>
          「{name}」{pendingWhat(pending)}
        </b>
        <Tag tone="open">{paidTag(pending)}</Tag>
        <span className="pnl-l3">{must}</span>
      </div>
      {lockNote !== undefined && (
        <div className="fc-lock pnl-l3 wide-only" role="status" data-testid="flash-lock-note">
          {lockNote}
        </div>
      )}
      <div className="fc-head narrow-only">
        <h2 className="fc-title">
          <HudBare id="bulb" px={20} />
          {FLASH_PICK_TITLE_ZH}
        </h2>
        <span className="fc-sub inline">
          <b>
            <span className="fc-name">「{name}」</span>
            {pendingWhat(pending, true)}
          </b>
          <Tag tone="open">{paidTag(pending)}</Tag>
          <InfoTip text={tip} label="說明" />
        </span>
      </div>
      {base}
    </div>
  );
}

/** 事件真的發生在這個元素（DOM）裡面，不是從 portal 的說明卡經 React 元件樹冒泡上來的（PB-1f e3q，同 `PartMenu`）。 */
const ownEvent = (e: { target: EventTarget; currentTarget: EventTarget }): boolean => e.target instanceof Node && e.currentTarget instanceof Node && e.currentTarget.contains(e.target);

/** 一張選項卡：單選圈＋白話大標＋類別標籤，下面「前 → 後」各列（LF-3：改名排第一列＋名稱來源標記，本機模型的一句話描述接在
 * 名稱下面）。點整張卡選中（再點不取消）。FL-1h：重閃選項整招和現在一樣（`same`）時，列的位置放一行「和現在一樣」。 */
function OptionCard({ o, current, same, selected, focusable, terms, onPick, onKey }: { o: FlashOption; current: string; same: boolean; selected: boolean; focusable: boolean; terms: Terms; onPick(): void; onKey(e: KeyboardEvent<HTMLDivElement>): void }) {
  const tag = optionTag(o);
  const after = renamedTo(o, current);
  const rename = after === null ? null : { before: current, after, llm: llmNamed(o) };
  return (
    <div
      role="radio"
      aria-checked={selected}
      tabIndex={focusable ? 0 : -1}
      className={`fc-opt${selected ? " on" : ""}${o.transform ? " transform" : ""}`}
      data-testid={`flash-option-${o.index}`}
      data-index={o.index}
      // PB-1f（e3q）：卡裡的術語說明卡 portal 到 body，React 事件照元件樹冒泡上來；點說明卡（釘住）或焦點在說明卡上按鍵不能當成選了這張
      onClick={(e) => {
        if (ownEvent(e)) onPick();
      }}
      onKeyDown={(e) => {
        if (ownEvent(e)) onKey(e);
      }}
    >
      <div className="fc-opt-top">
        <span className="fc-radio" aria-hidden="true" />
        <span className="fc-headline" data-testid="flash-headline">
          {headlineOf(o)}
        </span>
        <span className={`fc-cat${o.transform ? " transform" : ""}`} data-testid="flash-option-tag">
          <Tag tone={o.transform ? "warn" : undefined}>
            <Term id={o.tag_term} label={tag} terms={terms} />
          </Tag>
          {o.weaker_tag_zh && (
            <span className="fc-weaker" data-testid="flash-option-weaker">
              <i className="fc-down" aria-label="變弱" />
              {o.weaker_tag_zh}
            </span>
          )}
        </span>
      </div>
      {same ? (
        <p className="fc-same" data-testid="flash-same">
          {FLASH_SAME_AS_NOW_ZH}
        </p>
      ) : (
        <DiffRows changes={o.changes ?? []} terms={terms} rename={rename} note={noteOf(o)} />
      )}
    </div>
  );
}

/** 下固定區：選中的大標＋一句話＋（轉型要卸下時）卸下選單＋「確定」；都沒選時提示＋按不下去的「確定」。 */
function FlashFoot({
  picked,
  reserve,
  transformRoom,
  hero,
  terms,
  unequip,
  busy,
  onUnequip,
  onConfirm,
}: {
  picked: FlashOption | undefined;
  reserve: boolean;
  /** 有轉型選項：轉型卡的一句話多接一句，下固定區多留一行（點哪個都不跳）。 */
  transformRoom: boolean;
  hero: RunHero;
  terms: Terms;
  unequip: string | null;
  busy: boolean;
  onUnequip(id: string): void;
  onConfirm(): void;
}) {
  const owned = ownedCards(hero);
  return (
    <div className={`fc-foot${reserve ? " reserve" : ""}${transformRoom ? " transform-room" : ""}`} data-testid="flash-foot">
      {picked !== undefined && showsUnequipMenu(picked) && (
        <div className="fc-unequip" data-testid="flash-unequip">
          <span className="k">{unequipPrompt(picked)}</span>
          <span className="fc-unequip-list">
            {picked.unequip_candidates.map((id) => {
              const card = owned.get(id);
              return (
                <button key={id} type="button" className={unequip === id ? "on" : ""} aria-pressed={unequip === id} disabled={busy} onClick={() => onUnequip(id)} data-testid={`flash-unequip-${id}`}>
                  {card !== undefined && <SkillIconView icon={card.icon} size={20} level="main" label={card.name_zh} />}
                  {card?.name_zh ?? id}
                </button>
              );
            })}
          </span>
        </div>
      )}
      <div className="fc-foot-main">
        <div className={`fc-say${picked?.transform === true ? " transform" : ""}`} data-testid="flash-say">
          {picked === undefined ? (
            <span className="dim">{FLASH_PICK_NONE_ZH}</span>
          ) : (
            <>
              <b className="fc-picked">{headlineOf(picked)}</b>
              <span className="fc-say-line">
                <TermText text={sayText(picked)} terms={terms} nobr />
              </span>
            </>
          )}
        </div>
        <button data-sfx="ui_learn" type="button" className="primary" data-testid="flash-pick-confirm" disabled={busy || !pickReady(picked, unequip)} onClick={onConfirm}>
          確定
        </button>
      </div>
    </div>
  );
}

/** 選中的卡要捲到哪裡：整張放得進可視區（扣掉上下的 scroll-margin）用 `nearest`，放不下用 `start`（對齊上緣）。
 * 大世界看外面的捲動區（`.ui-popup-body`）；一輪是整頁捲，看視窗高。 */
export function scrollBlock(el: HTMLElement): ScrollLogicalPosition {
  const scroller = el.closest<HTMLElement>(".ui-popup-body");
  const room = scroller === null ? window.innerHeight : scroller.clientHeight;
  const style = window.getComputedStyle(el);
  const margins = (Number.parseFloat(style.scrollMarginTop) || 0) + (Number.parseFloat(style.scrollMarginBottom) || 0);
  return el.getBoundingClientRect().height + margins > room ? "start" : "nearest";
}

/** 待選閃現的選項畫面本體（一輪與大世界共用；5A-7）。 */
export function FlashPendingPanel({ pending, hero, busy, onChoose, lockNote }: PanelProps) {
  const [pick, setPick] = useState<number | null>(null);
  const [unequip, setUnequip] = useState<string | null>(null);
  const list = useRef<HTMLDivElement | null>(null);
  const slots = usePopupSlots();
  const before = ownedCards(hero).get(pending.skill_id);
  const options = sortedOptions(pending.options);
  const order = options.map((o) => o.index);
  const picked = options.find((o) => o.index === pick);
  const terms: Terms = pending.terms ?? {};
  const name = before?.name_zh ?? pending.skill_id;

  // 選中的那張整張看得到（5 第 3 條）：nearest＋CSS scroll-margin（上緣讓出漸隱、下緣多留約 20px）；內容沒超出時不捲。
  // FL-1g（LF-3 驗收必修 1）：卡比可視區高時改對齊卡的上緣（start），標頭落在上緣漸隱下面，下半截讓玩家自己捲
  useEffect(() => {
    if (pick === null || list.current === null) return;
    const el = list.current.querySelector<HTMLElement>(`[data-index="${pick}"]`);
    if (el === null) return;
    el.scrollIntoView?.({ block: scrollBlock(el) });
  }, [pick]);

  const choose = (index: number) => {
    if (index === pick) return; // 再點一次已選的卡不取消（1.3 第 2 條）
    setPick(index);
    setUnequip(null);
  };
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      const index = Number((e.currentTarget as HTMLElement).dataset.index);
      choose(index);
      return;
    }
    const next = stepPick(order, pick, e.key);
    if (next === pick || next === null) return;
    e.preventDefault();
    choose(next);
    list.current?.querySelector<HTMLElement>(`[data-index="${next}"]`)?.focus();
  };

  const base = before === undefined ? null : <BaseStrip card={before} stats={pending.base_stats ?? []} terms={terms} />;
  const head = <FlashHead pending={pending} name={name} lockNote={lockNote} base={base} />;
  const foot = (
    <FlashFoot
      picked={picked}
      reserve={anyUnequipMenu(options)}
      transformRoom={hasTransform(options)}
      hero={hero}
      terms={terms}
      unequip={unequip}
      busy={busy}
      onUnequip={setUnequip}
      onConfirm={() => picked !== undefined && void onChoose(pickChoice(picked, unequip))}
    />
  );
  const body = (
    <div ref={list} className="fc-opts" role="radiogroup" aria-label="閃現的變化" data-testid="flash-options">
      {options.map((o, i) => (
        <OptionCard key={o.index} o={o} current={name} same={sameAsNow(pending, o, before)} selected={pick === o.index} focusable={pick === null ? i === 0 : pick === o.index} terms={terms} onPick={() => choose(o.index)} onKey={onKey} />
      ))}
    </div>
  );

  if (slots !== null) {
    // 大世界 HUD 面板：上下固定區放進框的插槽（不捲），這裡只留選項區
    return (
      <div className="run-flash-pending fc-panel fc-in-popup" data-testid="run-flash-pending">
        <PopupSlot slots={slots} where="head">
          <div className="fc-panel">{head}</div>
        </PopupSlot>
        {body}
        <PopupSlot slots={slots} where="foot">
          <div className="fc-panel">{foot}</div>
        </PopupSlot>
      </div>
    );
  }
  return (
    <div className="panel run-flash-pending fc-panel fc-run" data-testid="run-flash-pending">
      {head}
      {body}
      {foot}
    </div>
  );
}
