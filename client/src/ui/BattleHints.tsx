// 戰鬥短提示（Phase 6F-2；09 9.6.9 #99、玩法 PM 筆記 U1）：放在戰場上方的提示列（`.board-toasts`，和其他
// 提示同一欄、不是新的彈出層）。一次一則；按「知道了」關掉後，下一則成立的才出現。每種提示每個角色只出一次
// （出現就記下）；「不再顯示提示」關掉全部（本機）。只影響畫面，不改戰鬥結果。
import { useEffect, useMemo, useState } from "react";
import type { BattleHint, BattleView } from "../api/types";
import { nextHint, readHintsOff, readSeen, writeHintsOff, writeSeen, type HintEvent } from "../world/battleHints";

export interface BattleHintSet {
  characterId: string;
  hints: readonly BattleHint[];
}

interface Props {
  set: BattleHintSet;
  view: BattleView;
  heroId: string;
  events: readonly HintEvent[];
}

export function BattleHints({ set, view, heroId, events }: Props) {
  const { characterId, hints } = set;
  const [seen, setSeen] = useState<ReadonlySet<string>>(() => readSeen(characterId));
  const [off, setOff] = useState(readHintsOff);
  const [current, setCurrent] = useState<BattleHint | null>(null);
  const candidate = useMemo(() => (current !== null ? null : nextHint(hints, view, heroId, events, seen, off)), [current, hints, view, heroId, events, seen, off]);

  useEffect(() => {
    if (candidate === null) return;
    const next = new Set(seen);
    next.add(candidate.id);
    writeSeen(characterId, next);
    setSeen(next);
    setCurrent(candidate);
  }, [candidate, characterId, seen]);

  if (current === null || off) return null;
  return (
    <div className="battle-hint" role="status" data-testid="battle-hint" data-hint={current.id}>
      <span className="battle-hint-tag">提示</span>
      <span className="battle-hint-text">{current.text_zh}</span>
      <button type="button" className="small-button" onClick={() => setCurrent(null)} data-testid="battle-hint-close">
        知道了
      </button>
      <button
        type="button"
        className="small-button battle-hint-off"
        onClick={() => {
          writeHintsOff(true);
          setOff(true);
          setCurrent(null);
        }}
        data-testid="battle-hint-off"
      >
        不再顯示提示
      </button>
    </div>
  );
}
