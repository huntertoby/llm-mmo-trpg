// 升級畫面：＋2 屬性點配點、三選一技能卡片（可跳過；欄位滿時選要換掉的）。
import { useState } from "react";
import type { RunChoice, RunResponse } from "../api/types";
import { allocationComplete, offerGroupKey, pickChoice, levelUpReady, type Allocation, type RunView } from "../run/flow";
import { AttributeAllocator } from "../run/AttributeAllocator";
import { OfferPicker } from "../run/OfferPicker";

type Props = {
  run: RunResponse;
  view: Extract<RunView, { screen: "level_up" }>;
  busy: boolean;
  /** 送出選擇；回傳失敗時的 HTTP 狀態（成功為 `null`）。 */
  onChoose(choice: RunChoice): Promise<number | null>;
};

export function RunLevelUp({ run, view, busy, onChoose }: Props) {
  const [alloc, setAlloc] = useState<Allocation>({});
  const [pick, setPick] = useState<number | null>(null);
  const [replace, setReplace] = useState<string | null>(null);
  const [force, setForce] = useState(false);
  const ready = levelUpReady(view.points, alloc, run.hero, view.offer, pick, replace, force);

  async function confirm() {
    const status = await onChoose(pickChoice(view, alloc, pick, replace));
    // 後端另有前端不知道的限制（例如規則改變型傳說只能裝 1 個）：改列全部技能讓玩家選要換掉的。
    if (status === 422 && pick !== null && replace === null) setForce(true);
  }

  return (
    <div className="panel run-levelup">
      <h2>升級！　Lv {view.level}</h2>
      <AttributeAllocator
        base={run.hero.attributes}
        points={view.points}
        alloc={alloc}
        onChange={setAlloc}
        disabled={busy}
        hpPerCon={run.hero.hp_per_con_point}
      />
      <div className="section-title">選一張新技能（可跳過）</div>
      <OfferPicker
        offer={view.offer}
        hero={run.hero}
        runSeed={run.seed}
        groupKey={offerGroupKey(view)}
        pick={pick}
        replace={replace}
        forceReplace={force}
        disabled={busy}
        onPick={setPick}
        onReplace={setReplace}
      />
      <div className="run-actions">
        <button type="button" className="primary" disabled={busy || !ready} onClick={() => void confirm()}>
          {pick === null ? "確定（跳過技能）" : "確定"}
        </button>
        {!allocationComplete(alloc, view.points) && (
          <span className="muted small">請先把 {view.points} 點屬性配完。</span>
        )}
      </div>
    </div>
  );
}
