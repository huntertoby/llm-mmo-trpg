// 戰後裝備三選一（Phase 3K-2，07 7.1）：打贏一般戰鬥後先看 3 件裝備（部位不重複），選 1 件直接換上、換下的進背包，
// 或跳過；之後才是升級。卡片排版照升級的技能候選（選這個／再按一次取消）。
import { useState } from "react";
import type { RunChoice } from "../api/types";
import { displayOrder, type RunView } from "../run/flow";
import { gearPickChoice, needsSwapConfirm } from "../run/gearOffer";
import { GearCardView } from "../ui/gear/GearCardView";
import { WeaponSwapConfirm } from "../ui/gear/WeaponSwapConfirm";

type Props = {
  seed: number;
  view: Extract<RunView, { screen: "gear_offer" }>;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
};

export function RunGearOffer({ seed, view, busy, onChoose }: Props) {
  const [pick, setPick] = useState<number | null>(null);
  const [asking, setAsking] = useState(false);
  const order = displayOrder(seed, `gear:${view.afterBattle}`, view.candidates.length);
  const chosen = pick === null ? undefined : view.candidates[pick];
  return (
    <div className="panel run-gear-offer" data-testid="gear-offer">
      <h2>戰利品：裝備三選一（第 {view.afterBattle} 場後）</h2>
      <p className="muted small">
        選 1 件直接換上，換下的裝備進背包（營火可以換回來）；不想換就跳過。選完之後才是升級。
      </p>
      <div className="run-offer-cards">
        {order.map((index) => {
          const cand = view.candidates[index];
          if (cand === undefined) return null;
          return (
            <div key={cand.item.id} className={`run-offer-card${pick === index ? " selected" : ""}`}>
              <GearCardView cand={cand} />
              <button
                type="button"
                className={pick === index ? "primary" : ""}
                disabled={busy}
                onClick={() => {
                  setAsking(false);
                  setPick(pick === index ? null : index);
                }}
              >
                {pick === index ? "已選這個（再按一次取消）" : "選這個"}
              </button>
            </div>
          );
        })}
      </div>
      {asking && chosen !== undefined ? (
        <WeaponSwapConfirm
          cand={chosen}
          busy={busy}
          onConfirm={() => void onChoose(gearPickChoice(pick))}
          onCancel={() => setAsking(false)}
        />
      ) : (
        <div className="run-actions">
          <button
            type="button"
            className="primary"
            disabled={busy}
            onClick={() => {
              if (chosen !== undefined && needsSwapConfirm(chosen)) setAsking(true);
              else void onChoose(gearPickChoice(pick));
            }}
          >
            {chosen === undefined ? "跳過（不換裝備）" : `換上「${chosen.item.name_zh}」`}
          </button>
        </div>
      )}
    </div>
  );
}
