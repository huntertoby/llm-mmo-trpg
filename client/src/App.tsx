// 畫面切換：開始畫面 ↔ 戰鬥畫面（之後 3-5 加入一輪流程的畫面）。
import { useState } from "react";
import type { BattleResponse } from "./api/types";
import { BattleScreen } from "./screens/BattleScreen";
import { StartScreen } from "./screens/StartScreen";

export function App() {
  const [battle, setBattle] = useState<BattleResponse | null>(null);
  if (battle === null) return <StartScreen onStart={setBattle} />;
  return <BattleScreen key={battle.battle_id} initial={battle} onExit={() => setBattle(null)} />;
}
