// 營火畫面：HP、法力、耐力已回滿（源力 +1）；可重骰一組新的技能候選（中段與 Boss 前各一次），選一張或放棄後離開。
// Phase 3-26a：也可以分配技能點、免費重配點數與換裝；Phase 3H-3：免費重配屬性點（同一個畫面）。
import { useState } from "react";
import type { RunChoice, RunResponse } from "../api/types";
import { offerGroupKey, pickChoice, pickReady, type RunView } from "../run/flow";
import { OfferPicker } from "../run/OfferPicker";
import { AttributeRespecSection } from "../run/AttributeRespecSection";
import { SkillPointsSection } from "../run/SkillPointsSection";

type Props = {
  run: RunResponse;
  view: Extract<RunView, { screen: "campfire" }>;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
};

export function RunCampfire({ run, view, busy, onChoose }: Props) {
  const [pick, setPick] = useState<number | null>(null);
  const [replace, setReplace] = useState<string | null>(null);
  const [force, setForce] = useState(false);
  const offer = view.offer;

  async function confirm() {
    const status = await onChoose(pickChoice(view, {}, pick, replace));
    if (status === 422 && pick !== null && replace === null) setForce(true);
  }

  return (
    <div className="panel run-campfire">
      <h2>營火（第 {view.afterBattle} 場後）</h2>
      <p>
        HP 與法力已回滿，源力 +1。
        {offer === null
          ? view.rerollsLeft > 0
            ? "可以重骰一次，得到一組新的技能候選。"
            : "這處營火的重骰已用完。"
          : "選一張新技能，或放棄後離開營火。"}
      </p>
      <SkillPointsSection hero={run.hero} busy={busy} onChoose={onChoose} campfire />
      <AttributeRespecSection hero={run.hero} busy={busy} onChoose={onChoose} campfire />
      {offer !== null && (
        <>
          <OfferPicker
            offer={offer}
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
              disabled={busy || !pickReady(run.hero, offer, pick, replace, force)}
              onClick={() => void confirm()}
            >
              {pick === null ? "放棄並離開營火" : "確定並離開營火"}
            </button>
          </div>
        </>
      )}
      {offer === null && (
        <div className="run-actions">
          {view.rerollsLeft > 0 && (
            <button type="button" disabled={busy} onClick={() => void onChoose({ kind: "reroll" })}>
              重骰技能候選（剩 {view.rerollsLeft} 次）
            </button>
          )}
          <button type="button" className="primary" disabled={busy} onClick={() => void onChoose({ kind: "leave" })}>
            離開營火
          </button>
        </div>
      )}
    </div>
  );
}
