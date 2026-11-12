// 任務日誌與線頭（Phase 5B-5；09 9.6.3、9.6.7 #6）：HUD 功能列「任務（J）」與舊左欄打開的面板。
// PNL-3（docs/art/資訊面板-移植需求.md 3.3「任務與線頭」，樣張 `infoPanels.js` 的 `questsProposal`、`infoPanelsTabs.js` 的 `Q`／`Q_TABS`）：
// 固定區（標題＋回到地點圖；「×」是 WorldHud 的正式關閉鈕）＋兩個分頁（任務日誌｜線頭，細框條數）。
// - 任務卡：名字＋類別標籤＋委託人小頭像與名字；摘要（L2）；建議（現行色）；藍色路線膠囊（地圖圖示）；步驟縱向時間軸 `StepTimeline`。
// - 線頭列：線軸 18、粗體內容、範圍標籤、鐘＋「剩 …」；NPC、指向地點在列尾加標籤；規則句進第一行 (i)。
// 這個檔不打 API（`PanelTabs` 量高度時分頁會多掛載一次）；字全部照伺服器（`QuestLogView`、`ThreadView`），新字在 `questPanel.ts`。
// 任務三選一待選時左欄固定顯示三選一（`WorldOfferPending`，重用一輪的 `OfferPicker`；野外學到的放進備用）。
import { useEffect, useRef, useState } from "react";
import type { WorldAction, WorldQuestLog, WorldThread, WorldView } from "../api/types";
import { OfferPicker } from "../run/OfferPicker";
import { ClockGlyph, EmptyNote, EventBare, HudBare, InfoTip, KeepNum, PanelHead, TabLine, Tag } from "../ui/PanelKit";
import { PanelTabs, type PanelTabDef } from "../ui/PanelTabs";
import {
  NO_QUEST_ZH,
  NO_THREAD_ZH,
  QUEST_DONE_ZH,
  QUEST_PANEL_TITLE_ZH,
  QUEST_TAB_ZH,
  questsBadge,
  stepParts,
  stepState,
  THREAD_LINE_ZH,
  THREAD_RULE_ZH,
  threadLeftText,
  threadPlaceText,
  threadsBadge,
} from "./questPanel";
import { Portrait } from "./StoryIcons";
import { sortQuests } from "./story";

/** 委託人小頭像（樣張 22）。 */
export const GIVER_FACE = 22;

/** 任務步驟縱向時間軸（樣張 `.ip-steps`）：綠勾＝完成、金圈＝目前（亮金粗體）、空圈數字＝未到；圈之間直線。左欄地點、右欄要做的事。 */
export function StepTimeline({ steps }: { steps: WorldQuestLog["steps"] }) {
  return (
    <ol className="pnl-steps">
      {steps.map((s, i) => {
        const st = stepState(s);
        const { place, task } = stepParts(s);
        return (
          <li key={i} className={st} data-step={st} data-testid="world-quest-step">
            <span className="dot" aria-label={st === "done" ? "完成" : st === "current" ? "目前" : `第 ${i + 1} 步`}>
              {st === "done" ? "✓" : st === "todo" ? String(i + 1) : null}
            </span>
            <span className="place">{place ?? ""}</span>
            <span className="what">
              <KeepNum text={task} />
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function QuestCard({ quest }: { quest: WorldQuestLog }) {
  return (
    <div className={quest.done ? "pnl-quest done" : "pnl-quest"} data-testid="world-quest" data-quest={quest.id}>
      <div className="pnl-quest-head">
        <span className="name">{quest.name_zh}</span>
        <Tag tone="open">{quest.kind_zh}</Tag>
        {quest.done && <Tag tone="mine">{QUEST_DONE_ZH}</Tag>}
        {quest.giver_zh != null && (
          <span className="giver" data-testid="world-quest-giver">
            <Portrait portrait={quest.giver_portrait ?? null} region={quest.giver_region ?? null} size={GIVER_FACE} label={quest.giver_zh} />
            {quest.giver_zh}
          </span>
        )}
      </div>
      {quest.summary_zh !== "" && (
        <div className="pnl-l2">
          <KeepNum text={quest.summary_zh} />
        </div>
      )}
      {/* 6F-2（筆記 U3、U4）：主線的建議（照現行色）在路線膠囊上面一行；往哪走＝藍色路線膠囊 */}
      {quest.advice_zh != null && <div className="world-quest-advice small">{quest.advice_zh}</div>}
      {quest.route_zh != null && (
        <span className="pnl-route" data-testid="world-quest-route">
          <HudBare id="bar_M" px={18} />
          {quest.route_zh}
        </span>
      )}
      <StepTimeline steps={quest.steps} />
    </div>
  );
}

export function QuestsPane({ quests }: { quests: readonly WorldQuestLog[] }) {
  if (quests.length === 0) return <EmptyNote testId="world-quest-empty">{NO_QUEST_ZH}</EmptyNote>;
  return (
    <div className="pnl-quests">
      {sortQuests(quests).map((q) => (
        <QuestCard key={q.id} quest={q} />
      ))}
    </div>
  );
}

export function ThreadsPane({ threads }: { threads: readonly WorldThread[] }) {
  if (threads.length === 0) return <EmptyNote testId="world-thread-empty">{NO_THREAD_ZH}</EmptyNote>;
  return (
    <>
      <TabLine end={<InfoTip text={THREAD_RULE_ZH} />}>
        <span className="pnl-l2">{THREAD_LINE_ZH}</span>
      </TabLine>
      <ul className="pnl-rows pnl-threads" data-testid="world-threads">
        {threads.map((t) => (
          <li key={t.id} className="pnl-row pnl-thread" data-thread={t.id}>
            <EventBare id="thread" px={18} />
            <span className="name">
              <KeepNum text={t.text_zh} />
            </span>
            <span className="end">
              <Tag>{t.scope_zh}</Tag>
              <Tag icon={<ClockGlyph px={14} />}>{threadLeftText(t)}</Tag>
              {t.npc_zh != null && <Tag>{t.npc_zh}</Tag>}
              {t.location_zh != null && <Tag>{threadPlaceText(t.location_zh)}</Tag>}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

/** 分頁定義（任務日誌｜線頭）。 */
export function questTabs(view: WorldView): PanelTabDef[] {
  const quests = view.quests ?? [];
  const threads = view.threads ?? [];
  return [
    {
      id: "quests",
      label: QUEST_TAB_ZH.quests,
      short: QUEST_TAB_ZH.questsShort,
      icon: <HudBare id="bar_J" px={16} />,
      badge: questsBadge(view),
      render: () => <QuestsPane quests={quests} />,
    },
    {
      id: "threads",
      label: QUEST_TAB_ZH.threads,
      short: QUEST_TAB_ZH.threadsShort,
      icon: <EventBare id="thread" px={16} />,
      badge: threadsBadge(view),
      render: () => <ThreadsPane threads={threads} />,
    },
  ];
}

export function QuestLog({ view, onClose }: { view: WorldView; onClose(): void }) {
  return (
    <div className="world-hud-stack world-quest-log" data-testid="world-quest-log">
      <PanelTabs tabs={questTabs(view)} head={<PanelHead heading={QUEST_PANEL_TITLE_ZH} onBack={onClose} testId="world-quest-head" />} testId="world-quest-tabs" />
    </div>
  );
}

/** 送出三選一之後等伺服器（正式選定後的下一組要現算，約 1～3 秒）的提示。 */
export const OFFER_WAIT = "正在記下你的選擇、準備下一步，稍等一下……";

/** 把元素自己與外面每一層會捲動的容器都捲回最上面（不動整頁的視窗捲動以外的東西）。 */
export function scrollToTop(el: { scrollTop: number; parentElement: unknown } | null): number {
  let n = 0;
  let node = el as { scrollTop: number; parentElement: unknown } | null;
  while (node != null) {
    if (node.scrollTop > 0) {
      node.scrollTop = 0;
      n += 1;
    }
    node = node.parentElement as typeof node;
  }
  return n;
}

export function WorldOfferPending({ view, busy, onAct }: { view: WorldView; busy: boolean; onAct(action: WorldAction): void }) {
  const pending = view.pending_offer!;
  const [pick, setPick] = useState<number | null>(null);
  const [replace, setReplace] = useState<string | null>(null);
  const groupKey = `${pending.quest_name_zh}:${pending.step_zh}`;
  // OB-5（#150 第 3 點）：正式選定後延後的兩組三選一依序出（選完一組才出下一組）——換了一組就把上一組的選擇清掉
  // OB-6（美術追蹤①）：每次開啟（含換下一組）都捲到最上面，標題區一定看得到
  const top = useRef<HTMLDivElement>(null);
  useEffect(() => {
    setPick(null);
    setReplace(null);
    scrollToTop(top.current);
  }, [groupKey]);
  return (
    <div className="panel world-offer" data-testid="world-offer" ref={top}>
      <h2>任務給的技能三選一</h2>
      <div className="small">
        {pending.quest_name_zh}：{pending.step_zh}
      </div>
      <div className="muted small">{pending.place_zh}選之前不能移動或使用其他服務。</div>
      <OfferPicker
        offer={pending.offer}
        hero={view.hero}
        runSeed={0}
        groupKey={groupKey}
        pick={pick}
        replace={pending.can_replace ? replace : null}
        disabled={busy}
        onPick={setPick}
        onReplace={(id) => setReplace(pending.can_replace ? id : null)}
      />
      {busy && (
        <div className="small world-offer-wait" role="status" data-testid="world-offer-wait">
          {OFFER_WAIT}
        </div>
      )}
      <div className="run-actions">
        <button data-sfx="ui_learn"
          type="button"
          className="primary"
          disabled={busy || pick === null}
          onClick={() => onAct({ kind: "offer_pick", pick, replace: pending.can_replace ? replace : null })}
          data-testid="world-offer-take"
        >
          學這招
        </button>
        <button type="button" disabled={busy} onClick={() => onAct({ kind: "offer_pick", pick: null })} data-testid="world-offer-skip">
          跳過
        </button>
      </div>
    </div>
  );
}
