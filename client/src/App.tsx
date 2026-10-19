// 畫面切換：開始畫面 ↔ 戰鬥畫面（之後 3-5 加入一輪流程的畫面）。啟動時先讀名詞對照表。
import { useEffect, useState } from "react";
import { api } from "./api/client";
import type { BattleResponse } from "./api/types";
import { setGlossary } from "./battle/glossary";
import { BattleScreen } from "./screens/BattleScreen";
import { StartScreen } from "./screens/StartScreen";
import { ErrorBanner } from "./ui/ErrorBanner";

export function App() {
  const [battle, setBattle] = useState<BattleResponse | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .glossary()
      .then((g) => {
        if (cancelled) return;
        setGlossary(g);
        setReady(true);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return (
      <div className="loading">
        <ErrorBanner message={error} onClose={() => setError(null)} />
        {error === null ? "載入中……" : "無法載入名詞對照表，請確認 `trpg serve` 正在執行後重新整理。"}
      </div>
    );
  }
  if (battle === null) return <StartScreen onStart={setBattle} />;
  return <BattleScreen key={battle.battle_id} initial={battle} onExit={() => setBattle(null)} />;
}
