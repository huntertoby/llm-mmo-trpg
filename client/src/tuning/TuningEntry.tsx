// 開發選單（`?dev=1`）的「數值工坊」入口（NW-1b B1）：先問伺服器開關有沒有開；沒開時按鈕顯示「未開啟」並說明怎麼開，不會壞掉。
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { probeEntry, type TuningApi } from "./flow";
import type { EntryState } from "./model";

interface ViewProps {
  state: EntryState;
  onOpen(): void;
}

/** 入口的畫面（純顯示；vitest 用 renderToStaticMarkup 測）。 */
export function TuningEntryView({ state, onOpen }: ViewProps) {
  const open = state.kind === "open";
  return (
    <div className="panel start-tuning" data-entry={state.kind}>
      <div className="section-title">數值工坊</div>
      <div className="muted small">改敵人與頭目的血量、屬性、抗性、階段門檻等數值，跑小模擬比較改前改後，確定後寫回遊戲（要重開伺服器生效）。</div>
      <button type="button" disabled={!open} onClick={onOpen} data-testid="enter-tuning">
        {state.kind === "checking" ? "數值工坊（檢查中……）" : open ? "進入數值工坊" : "數值工坊（未開啟）"}
      </button>
      {state.kind !== "open" && state.kind !== "checking" && (
        <div className="tn-entry-why small" data-testid="tuning-entry-why">
          {state.reason}
        </div>
      )}
    </div>
  );
}

export function TuningEntry({ onOpen, tapi = api }: { onOpen(): void; tapi?: Pick<TuningApi, "tuningStatus"> }) {
  const [state, setState] = useState<EntryState>({ kind: "checking" });
  useEffect(() => {
    let cancelled = false;
    void probeEntry(tapi).then((s) => {
      if (!cancelled) setState(s);
    });
    return () => {
      cancelled = true;
    };
  }, [tapi]);
  return <TuningEntryView state={state} onOpen={onOpen} />;
}
