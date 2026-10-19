// 戰鬥紀錄：最新在下，自動捲動到底。
import { useEffect, useRef } from "react";
import type { LogLine } from "../battle/log";

interface Props {
  lines: readonly LogLine[];
}

export function BattleLog({ lines }: Props) {
  const boxRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const box = boxRef.current;
    if (box !== null) box.scrollTop = box.scrollHeight;
  }, [lines.length]);
  return (
    <div className="panel battle-log">
      <div className="section-title">戰鬥紀錄</div>
      <div className="log-lines" ref={boxRef}>
        {lines.map((l, i) => (
          <div key={`${l.seq}:${i}`} className="log-line">
            <span className="log-round">{l.round}</span>
            {l.text}
          </div>
        ))}
      </div>
    </div>
  );
}
