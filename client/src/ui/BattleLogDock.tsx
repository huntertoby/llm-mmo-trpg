// 戰鬥紀錄（Phase 6A-3，去文字化④）：預設收成戰場左下 2～3 條浮動提示，舊的約 6 秒淡出（`battle/logToasts.ts`）；
// 點紀錄圖示展開完整清單（`BattleLog`），展開後可以釘選，釘住就一直顯示（釘選記在本機，讀寫失敗當作沒釘）。
// 沒釘住時再點一次圖示或按 Esc 收起。
import { useEffect, useLayoutEffect, useReducer, useRef, useState, type ReactNode } from "react";
import type { LogLine } from "../battle/log";
import { logDockMaxHeight, logLimit, type LogLimit } from "../battle/logRoom";
import { liveToasts, nextToastChange, stampArrivals, type LogToast } from "../battle/logToasts";
import { BattleLog, TONE_MARK, type LogHover } from "./BattleLog";
import { Hint } from "./Hint";
import { NoTurnTag } from "./NoTurnTag";
import { PinGlyph } from "./SkillCardGlyphs";

export const LOG_PIN_KEY = "trpg.battleLog.pinned";

function readPinned(): boolean {
  try {
    return localStorage.getItem(LOG_PIN_KEY) === "1";
  } catch {
    return false;
  }
}

function writePinned(on: boolean): void {
  try {
    if (on) localStorage.setItem(LOG_PIN_KEY, "1");
    else localStorage.removeItem(LOG_PIN_KEY);
  } catch {
    // 本機儲存不能用：這次照樣釘住，只是不記
  }
}

/** 紀錄圖示（捲軸）。 */
export function LogGlyph() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <path d="M3 2.5h8.5a1.5 1.5 0 0 1 1.5 1.5v9.5H4.5A1.5 1.5 0 0 1 3 12z" fill="none" stroke="currentColor" strokeWidth="1.3" />
      <path d="M5.5 5.5h5M5.5 8h5M5.5 10.5h3.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

function ToastLine({ toast }: { toast: LogToast }) {
  const { line } = toast;
  return (
    <div
      className={`log-toast${toast.fading ? " fading" : ""}${line.team === undefined ? "" : ` team-${line.team}`}`}
      data-testid="log-toast"
    >
      {line.tone !== undefined && (
        <span className="log-mark" aria-hidden="true">
          {TONE_MARK[line.tone]}
        </span>
      )}
      <span className="log-text">{line.summary ?? line.text}</span>
      {line.noTurn !== undefined && line.summary !== undefined && <NoTurnTag kind={line.noTurn.kind} backstab={line.noTurn.backstab} hint={false} />}
    </div>
  );
}

interface ViewProps {
  toasts: readonly LogToast[];
  /** 完整清單展開中（釘住也算展開）。 */
  open: boolean;
  pinned: boolean;
  onToggleOpen(): void;
  onTogglePin(): void;
  /** 展開時的完整清單（`BattleLog`，標題列帶釘選鈕）。 */
  log: (actions: ReactNode) => ReactNode;
  /** 選取中：縮短讓開選取面板（6A-4c，`battle/logRoom.ts`）；`null` 或省略 ＝ 照原本的高度。 */
  limit?: LogLimit | null;
  /** UI-1：沒選取時的高度上限，上緣停在主角卡下緣（`heroLogCap`）；`null` 或省略 ＝ 只用 CSS 的 58%。 */
  heroCap?: number | null;
}

/** 畫面本體（不含計時與本機儲存，方便測試）。 */
export function BattleLogDockView({ toasts, open, pinned, onToggleOpen, onTogglePin, log, limit = null, heroCap = null }: ViewProps) {
  const maxHeight = logDockMaxHeight(limit, heroCap);
  const pin = (
    <Hint text={pinned ? "取消釘選（收起後回到浮動提示）" : "釘選：一直顯示完整紀錄"}>
      <button type="button" className={`log-pin${pinned ? " on" : ""}`} aria-pressed={pinned} aria-label={pinned ? "取消釘選" : "釘選"} onClick={onTogglePin}>
        <PinGlyph pinned={pinned} />
      </button>
    </Hint>
  );
  return (
    <div
      className={`log-dock${open ? " open" : ""}${pinned ? " pinned" : ""}${limit === null ? "" : " squeezed"}${limit?.tight === true ? " tight" : ""}`}
      aria-label="戰鬥紀錄"
      style={maxHeight === undefined ? undefined : { maxHeight }}
    >
      {open ? (
        <div className="log-dock-panel">{log(pin)}</div>
      ) : (
        toasts.length > 0 && (
          <div className="log-toasts" role="log" aria-live="polite">
            {toasts.map((t) => (
              <ToastLine key={t.seq} toast={t} />
            ))}
          </div>
        )
      )}
      <Hint text={open ? (pinned ? "完整戰鬥紀錄（已釘選）" : "收起戰鬥紀錄") : "展開完整戰鬥紀錄"}>
        <button type="button" className={`log-dock-icon${open ? " on" : ""}`} aria-expanded={open} aria-label="戰鬥紀錄" onClick={onToggleOpen}>
          <LogGlyph />
        </button>
      </Hint>
    </div>
  );
}

interface Props {
  lines: readonly LogLine[];
  onHover?: (hover: LogHover | null) => void;
  /** 選取時可用的高度（`useLogRoom`）；`null` 或省略 ＝ 沒有選取。 */
  room?: number | null;
  /** UI-1：沒選取時主角卡底下的可用高度（`useHeroLogCap`）。 */
  heroCap?: number | null;
}

export function BattleLogDock({ lines, onHover, room = null, heroCap = null }: Props) {
  const limit = logLimit(room);
  const rootRef = useRef<HTMLDivElement>(null);
  // 縮短或恢復時捲到最新一行（只顯示最新的幾行）
  useLayoutEffect(() => {
    const box = rootRef.current?.querySelector<HTMLElement>(".log-lines");
    if (box != null) box.scrollTop = box.scrollHeight;
  }, [limit?.maxHeight]);
  const [pinned, setPinned] = useState(readPinned);
  const [expanded, setExpanded] = useState(false);
  const [, tick] = useReducer((n: number) => n + 1, 0);
  const arrivals = useRef<ReadonlyMap<number, number>>(new Map());
  const first = useRef(true);
  const now = Date.now();
  // 第一次畫時已經有的紀錄（讀檔、重新整理）不冒提示；之後新出現的行記下出現時間。重複執行結果相同。
  arrivals.current = stampArrivals(arrivals.current, lines, now, first.current);
  first.current = false;
  const open = pinned || expanded;
  const toasts = open ? [] : liveToasts(lines, arrivals.current, now);
  const wait = nextToastChange(toasts, arrivals.current, now);
  useEffect(() => {
    if (wait === null) return undefined;
    const id = window.setTimeout(tick, wait + 16);
    return () => window.clearTimeout(id);
  });
  useEffect(() => {
    if (!expanded || pinned) return undefined;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [expanded, pinned]);
  return (
    <div ref={rootRef} className="log-dock-root">
    <BattleLogDockView
      limit={limit}
      heroCap={heroCap}
      toasts={toasts}
      open={open}
      pinned={pinned}
      onToggleOpen={() => {
        if (pinned) {
          setPinned(false);
          writePinned(false);
          setExpanded(false);
        } else setExpanded((v) => !v);
      }}
      onTogglePin={() => {
        const next = !pinned;
        setPinned(next);
        writePinned(next);
        setExpanded(true); // 取消釘選時清單先留著，再點圖示或按 Esc 才收起
      }}
      log={(actions) => <BattleLog lines={lines} actions={actions} {...(onHover === undefined ? {} : { onHover })} />}
    />
    </div>
  );
}
