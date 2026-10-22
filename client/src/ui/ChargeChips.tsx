// 裝備充能的層數顯示（Phase 3G-G3a）：每條充能詞條一個小標籤，格子數＝裝備版上限。
import type { ChargeView } from "../api/types";
import { chargeHint, chargePips, chargeText } from "../battle/charges";
import { Hint } from "./Hint";

export function ChargeChips({ charges }: { charges: readonly ChargeView[] }) {
  return (
    <>
      {charges.map((c) => (
        <Hint key={c.affix_id} text={chargeHint(c)}>
          <span className={`hud-chip charge-chip${c.ready ? " ready" : ""}`} aria-label={chargeText(c)}>
            {c.stack_name_zh}{" "}
            <span className="charge-pips">
              {chargePips(c).map((filled, i) => (
                <span key={i} className={`charge-pip${filled ? " filled" : ""}`} />
              ))}
            </span>
            {c.ready && <b className="charge-ready">可啟動</b>}
          </span>
        </Hint>
      ))}
    </>
  );
}
