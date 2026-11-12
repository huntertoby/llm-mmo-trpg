// 任務日誌與線頭（Phase 5B-5；09 9.6.3、9.6.7 #6）：左欄切換（地點圖 ↔ 任務與線頭，代決 5B5-10）。
// 任務三選一待選時左欄固定顯示三選一（`WorldOfferPending`，重用一輪的 `OfferPicker`；野外學到的放進備用）。
import { useEffect, useRef, useState } from "react";
import type { WorldAction, WorldView } from "../api/types";
import { OfferPicker } from "../run/OfferPicker";
import { sortQuests, stepMark } from "./story";

export function QuestLog({ view, onClose }: { view: WorldView; onClose(): void }) {
  const quests = sortQuests(view.quests ?? []);
  const threads = view.threads ?? [];
  return (
    <div className="panel world-quest-log" data-testid="world-quest-log">
      <div className="world-quest-head">
        <h2>任務與線頭</h2>
        <button type="button" onClick={onClose}>
          回到地點圖
        </button>
      </div>
      <div className="section-title">任務日誌</div>
      {quests.length === 0 ? (
        <div className="muted small">還沒有接任務。到小鎮找人說話，看看「可以接的任務」。</div>
      ) : (
        quests.map((q) => (
          <div key={q.id} className={`world-quest${q.done ? " done" : ""}`} data-testid="world-quest">
            <div>
              <b>{q.name_zh}</b>
              <span className="muted small lead-gap">
                {q.kind_zh}
                {q.giver_zh != null ? `・${q.giver_zh}` : ""}
                {q.done ? "・已完成" : ""}
              </span>
            </div>
            {q.summary_zh !== "" && <div className="muted small">{q.summary_zh}</div>}
            {/* 6F-2（筆記 U3、U4）：往哪走、主線的建議 */}
            {q.advice_zh != null && <div className="world-quest-advice small">{q.advice_zh}</div>}
            {q.route_zh != null && <div className="world-quest-route small">{q.route_zh}</div>}
            <ol className="world-quest-steps small">
              {q.steps.map((s, i) => (
                <li key={i} className={s.done ? "done" : s.current ? "current" : "todo"} data-testid="world-quest-step">
                  <span className="world-step-mark">{stepMark(s)}</span> {s.text_zh}
                </li>
              ))}
            </ol>
          </div>
        ))
      )}
      <div className="section-title">線頭</div>
      {threads.length === 0 ? (
        <div className="muted small">還沒有線頭。事件的結果會留下線頭（每人約 5 條，約 3 天到期）。</div>
      ) : (
        <ul className="world-threads small" data-testid="world-threads">
          {threads.map((t) => (
            <li key={t.id}>
              <b>{t.text_zh}</b>
              <span className="muted lead-gap">
                {t.scope_zh}・{t.expires_zh}
                {t.npc_zh != null ? `・${t.npc_zh}` : ""}
                {t.location_zh != null ? `・指向${t.location_zh}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
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
