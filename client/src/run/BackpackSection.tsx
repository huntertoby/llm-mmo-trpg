// 營火的背包（Phase 3K-2）：換下的裝備放在這裡，營火可以免費換上（換下的再進背包，不限次數）；
// 每件附和該欄位目前裝備的比較。和技能換裝、屬性重配同一個畫面。
// 3K-2b：換主手武器且縮放屬性和目前的不同時，換上前先確認。
import { useState } from "react";
import type { RunChoice, RunHero } from "../api/types";
import { GearCardView } from "../ui/gear/GearCardView";
import { WeaponSwapConfirm } from "../ui/gear/WeaponSwapConfirm";
import { equipChoice, needsSwapConfirm } from "./gearOffer";

type Props = {
  hero: RunHero;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
};

export function BackpackSection({ hero, busy, onChoose }: Props) {
  const [asking, setAsking] = useState<string | null>(null);
  const pack = hero.backpack ?? [];
  if (pack.length === 0) return null;
  return (
    <div className="run-backpack" data-testid="run-backpack">
      <div className="section-title">
        背包<span className="muted small">　{pack.length} 件；營火可以免費換裝</span>
      </div>
      <div className="run-offer-cards">
        {pack.map((cand) => {
          const equip = () => {
            setAsking(null);
            void onChoose(equipChoice(cand.item.id, cand.slot));
          };
          return (
            <div key={cand.item.id} className="run-offer-card">
              <GearCardView cand={cand} />
              {asking === cand.item.id ? (
                <WeaponSwapConfirm cand={cand} busy={busy} onConfirm={equip} onCancel={() => setAsking(null)} />
              ) : (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => (needsSwapConfirm(cand) ? setAsking(cand.item.id) : equip())}
                  data-testid="backpack-equip"
                >
                  換上這件（{cand.slot_zh}）
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
