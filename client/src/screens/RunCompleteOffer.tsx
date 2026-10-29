// 完整技能三選一（Phase 3W-6 正式畫面；06 6.34.6）：一輪中段（第 3 場後）與 Boss 前（第 5 場後）各一次，排在營火之前。
// 完整技能是整招設計好的技能，強度視為已閃 3 次（預算 +120‰），不能再閃現，但可以在營火重閃它的調整欄。
import { useState } from "react";
import type { RunChoice, RunResponse } from "../api/types";
import { COMPLETE_BADGE, COMPLETE_INTRO, completeSkipText } from "../run/flash";
import { offerGroupKey, pickChoice, pickReady, type RunView } from "../run/flow";
import { OfferPicker } from "../run/OfferPicker";

type Props = {
  run: RunResponse;
  view: Extract<RunView, { screen: "complete_offer" }>;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
};

export function RunCompleteOffer({ run, view, busy, onChoose }: Props) {
  const [pick, setPick] = useState<number | null>(null);
  const [replace, setReplace] = useState<string | null>(null);
  const [force, setForce] = useState(false);

  async function confirm() {
    const status = await onChoose(pickChoice(view, {}, pick, replace));
    if (status === 422 && pick !== null && replace === null) setForce(true);
  }

  return (
    <div className="panel run-complete-offer" data-testid="run-complete-offer">
      <h2>完整技能三選一（第 {view.afterBattle} 場後）</h2>
      <ul className="complete-intro small" data-testid="complete-intro">
        {COMPLETE_INTRO.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <OfferPicker
        offer={view.offer}
        hero={run.hero}
        runSeed={run.seed}
        groupKey={offerGroupKey(view)}
        pick={pick}
        replace={replace}
        forceReplace={force}
        badge={COMPLETE_BADGE}
        disabled={busy}
        onPick={setPick}
        onReplace={setReplace}
      />
      <div className="run-actions">
        <button
          type="button"
          className="primary"
          disabled={busy || !pickReady(run.hero, view.offer, pick, replace, force)}
          onClick={() => void confirm()}
        >
          {pick === null ? "跳過" : "確定"}
        </button>
        {pick === null && <span className="muted small">{completeSkipText()}</span>}
      </div>
    </div>
  );
}
