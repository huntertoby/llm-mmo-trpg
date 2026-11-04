// 戰鬥短提示（Phase 6F-2；09 9.6.9 #99、玩法 PM 筆記 U1）：放在戰場上方的提示列（`.board-toasts`，和其他
// 提示同一欄、不是新的彈出層）。一次一則；按「知道了」關掉後，下一則成立的才出現。每種提示每個角色只出一次
// （出現就記下）；「不再顯示提示」關掉全部。6F-4（6F-2b）起兩者都記在角色身上：開戰時帶伺服器的紀錄進來，
// 出現、關掉時呼叫 `onSeen`／`onOff`（送世界動作；只記紀錄，戰鬥中也能送）。只影響畫面，不改戰鬥結果。
import { useEffect, useMemo, useState } from "react";
import type { BattleHint, BattleView } from "../api/types";
import { nextHint, type HintEvent } from "../world/battleHints";

export interface BattleHintSet {
  characterId: string;
  hints: readonly BattleHint[];
  /** 開戰時伺服器記的「出過的提示」（`WorldView.hints.seen`）。 */
  seen?: readonly string[];
  /** 開戰時的「不再顯示提示」。 */
  off?: boolean;
  /** 一則提示出現了（記到角色身上）。 */
  onSeen?(id: string): void;
  /** 按了「不再顯示提示」。 */
  onOff?(): void;
}

interface Props {
  set: BattleHintSet;
  view: BattleView;
  heroId: string;
  events: readonly HintEvent[];
}

export function BattleHints({ set, view, heroId, events }: Props) {
  const { hints, onSeen, onOff } = set;
  const [seen, setSeen] = useState<ReadonlySet<string>>(() => new Set(set.seen ?? []));
  const [off, setOff] = useState(set.off ?? false);
  const [current, setCurrent] = useState<BattleHint | null>(null);
  const candidate = useMemo(() => (current !== null ? null : nextHint(hints, view, heroId, events, seen, off)), [current, hints, view, heroId, events, seen, off]);

  useEffect(() => {
    if (candidate === null) return;
    const next = new Set(seen);
    next.add(candidate.id);
    onSeen?.(candidate.id);
    setSeen(next);
    setCurrent(candidate);
  }, [candidate, seen, onSeen]);

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
          onOff?.();
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
