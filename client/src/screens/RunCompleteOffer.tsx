// 完整技能三選一（Phase 3W-5 最小版：沿用升級的候選卡挑選；正式畫面在 3W-6）。
import { useState } from "react";
import type { RunChoice, RunResponse } from "../api/types";
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
    <div className="panel run-complete-offer">
      <h2>完整技能三選一（第 {view.afterBattle} 場後）</h2>
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
        <button
          type="button"
          className="primary"
          disabled={busy || !pickReady(run.hero, view.offer, pick, replace, force)}
          onClick={() => void confirm()}
        >
          {pick === null ? "跳過" : "確定"}
        </button>
      </div>
    </div>
  );
}
