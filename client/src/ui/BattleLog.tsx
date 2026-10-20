// 戰鬥紀錄（Phase 3-9b）：依行動分組、每輪與每個單位回合有分隔；我方藍、敵方紅；
// 擲骰與修正細節預設收起（點「詳」看完整文字，或用右上角的開關全部展開）；滑過一組時高亮相關單位與格子。
// 最新在下，自動捲動到底。
import { useEffect, useMemo, useRef, useState } from "react";
import type { Pos } from "../api/types";
import type { LogLine, LogTone } from "../battle/log";
import { groupLog, type LogGroup, type LogItem } from "../battle/logGroups";

/** 滑過紀錄時要在戰場上高亮的單位與格子。 */
export interface LogHover {
  unitIds: readonly string[];
  tiles: readonly Pos[];
}

interface Props {
  lines: readonly LogLine[];
  onHover?: (hover: LogHover | null) => void;
}

const TONE_MARK: Record<LogTone, string> = {
  damage: "−",
  heal: "＋",
  shield: "◇",
  status: "◆",
  down: "✕",
  hit: "●",
  miss: "○",
};

function teamClass(line: LogLine): string {
  return line.team === undefined ? "" : ` team-${line.team}`;
}

interface LineProps {
  line: LogLine;
  head?: boolean;
  open: boolean;
  onToggle: (seq: number) => void;
}

function LogText({ line, head = false, open, onToggle }: LineProps) {
  const hasDetail = line.summary !== undefined;
  const shown = hasDetail && !open ? line.summary : line.text;
  return (
    <div className={`log-line${head ? " log-head" : ""}${teamClass(line)}${line.tone ? ` tone-${line.tone}` : ""}`}>
      {line.tone !== undefined && (
        <span className="log-mark" aria-hidden="true">
          {TONE_MARK[line.tone]}
        </span>
      )}
      <span className="log-text">{shown}</span>
      {hasDetail && (
        <button
          type="button"
          className="log-more"
          aria-expanded={open}
          title={open ? "收起擲骰與修正細節" : "展開擲骰與修正細節"}
          onClick={() => onToggle(line.seq)}
        >
          {open ? "收起" : "詳"}
        </button>
      )}
    </div>
  );
}

interface GroupProps {
  group: LogGroup;
  expanded: (seq: number) => boolean;
  onToggle: (seq: number) => void;
  onHover?: (hover: LogHover | null) => void;
}

function GroupView({ group, expanded, onToggle, onHover }: GroupProps) {
  const { head } = group;
  return (
    <div
      className={`log-group${group.isAction ? " log-action" : ""}${teamClass(head)}`}
      onMouseEnter={() => onHover?.({ unitIds: group.unitIds, tiles: group.tiles })}
      onMouseLeave={() => onHover?.(null)}
    >
      <LogText line={head} head={group.isAction} open={expanded(head.seq)} onToggle={onToggle} />
      {group.children.length > 0 && (
        <div className="log-children">
          {group.children.map((c, i) => (
            <LogText key={`${c.seq}:${i}`} line={c} open={expanded(c.seq)} onToggle={onToggle} />
          ))}
        </div>
      )}
    </div>
  );
}

type ItemProps = Omit<GroupProps, "group"> & { item: LogItem };

function ItemView({ item, ...rest }: ItemProps) {
  if (item.kind === "group") return <GroupView group={item} {...rest} />;
  if (item.kind === "round") return <div className="log-round-div">{item.text}</div>;
  return <div className={`log-turn${item.team ? ` team-${item.team}` : ""}`}>{item.text}</div>;
}

export function BattleLog({ lines, onHover }: Props) {
  const boxRef = useRef<HTMLDivElement>(null);
  const [all, setAll] = useState(false);
  const [open, setOpen] = useState<ReadonlySet<number>>(new Set());
  const items = useMemo(() => groupLog(lines), [lines]);
  useEffect(() => {
    const box = boxRef.current;
    if (box !== null) box.scrollTop = box.scrollHeight;
  }, [lines.length]);
  const expanded = (seq: number) => all || open.has(seq);
  const toggle = (seq: number) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (!next.delete(seq)) next.add(seq);
      return next;
    });
  return (
    <div className="panel battle-log">
      <div className="section-title log-title">
        <span>戰鬥紀錄</span>
        <button
          type="button"
          className={`log-all${all ? " on" : ""}`}
          aria-pressed={all}
          title="全部展開擲骰與修正細節"
          onClick={() => setAll((v) => !v)}
        >
          擲骰細節
        </button>
      </div>
      <div className="log-lines" ref={boxRef} onMouseLeave={() => onHover?.(null)}>
        {items.map((item, i) => (
          <ItemView
            key={`${item.kind}:${item.kind === "group" ? item.head.seq : item.seq}:${i}`}
            item={item}
            expanded={expanded}
            onToggle={toggle}
            {...(onHover === undefined ? {} : { onHover })}
          />
        ))}
      </div>
    </div>
  );
}
