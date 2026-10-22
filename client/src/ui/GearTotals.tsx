// 裝備加成的來源（Phase 3G-G4）：實際值（遞減、截斷後）、截斷前的值、每條詞條的貢獻。
// 英雄面板（裝備測試）與單位資訊共用。
import { useState } from "react";
import type { GearTotalView } from "../api/types";
import { totalLine } from "../gear/gearDraft";
import { gearFoldLabel } from "./gearFold";

interface Props {
  totals: readonly GearTotalView[];
  /** 單位資訊的小卡用：每項只一行，來源與說明放在滑過的提示。 */
  compact?: boolean;
}

export function GearTotals({ totals, compact = false }: Props) {
  const [open, setOpen] = useState(false);
  if (totals.length === 0) return null;
  if (compact) {
    return (
      <div className="gear-totals compact">
        <button type="button" className="gear-totals-title gear-fold" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
          {gearFoldLabel(totals.length, open)}
        </button>
        {open && (
        <ul>
          {totals.map((t) => {
            const line = totalLine(t);
            return (
              <li key={t.key} className={t.capped ? "capped" : ""} title={[line.detail, ...t.sources_zh].join(" / ")}>
                <span className="gear-total-text">{line.main}</span>
                <span className="gear-total-from">來自裝備</span>
                {line.badge !== null && <span className="gear-total-capped">{line.badge}</span>}
              </li>
            );
          })}
        </ul>
        )}
      </div>
    );
  }
  return (
    <div className="gear-totals">
      <div className="gear-totals-title">裝備加成（來自裝備；已套用遞減與上限）</div>
      <ul>
        {totals.map((t) => {
          const line = totalLine(t);
          return (
            <li key={t.key} className={t.capped ? "capped" : ""}>
              <div className="gear-total-main">
                <span className="gear-total-text">{line.main}</span>
                <span className="gear-total-from">來自裝備</span>
                {line.badge !== null && <span className="gear-total-capped">{line.badge}</span>}
              </div>
              <div className="gear-total-note muted small">{line.detail}</div>
              {t.sources_zh.length > 0 && (
                <ul className="gear-total-sources muted small">
                  {t.sources_zh.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
