// 城鎮公告板（Phase 5F-1；09 9.7、9.6.9 #99、9.6.10 #103、18.7.4；5F-3 賽季 Boss）。全部由後端算好（換日後的世界，只讀）。
// PNL-1b（docs/art/資訊面板-移植需求.md 3.3）：改成上方分頁——固定區（標題、守印人、第 N 天與日程、下一個）＋五個分頁
// （今日目標｜懸賞板｜賽季時程｜世界事件｜賽季頭目）；分頁內容在 `BoardPanes.tsx`。
// **讀公告板（`api.worldBoard`）只在這裡、在 `PanelTabs` 外面**：`PanelTabs` 量面板高度時分頁內容會多掛載一次（PNL-1a 裁定 5），
// 放進分頁裡會重複打 API。每次世界畫面換新（動作之後）重新讀一次，讀到之前沿用上一份（不閃）。
import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { SeasonBoardView, WorldAction, WorldView } from "../api/types";
import { PanelTabs } from "../ui/PanelTabs";
import { BoardFixed, boardTabs } from "./BoardPanes";

interface Props {
  characterId: string;
  /** 世界畫面（每次動作之後換新：重新讀公告板）。 */
  view: WorldView;
  busy?: boolean;
  /** 送世界動作（5F-3 賽季 Boss 的「挑戰」）；沒給時不顯示按鈕。 */
  onAct?(action: WorldAction): void;
  onClose(): void;
}

type BoardKeeper = NonNullable<NonNullable<WorldView["field"]>["situation_objects"]>[number];

/**
 * 公告板上緣的「頭像＋一句話」（6V-3；美術 PM 6V-1 檢查待決 1，版面照 NPC 面板）：這張實地地圖上點了開公告板
 * （`panel: board`）、有站著人（`figure`）的情境物件，依 ID 排第一個（主城＝守印人）；一句話是 `figure.line_zh`。
 * 沒有（其他城鎮的公告板）＝ `null`，面板照舊。
 */
export function boardKeeper(view: WorldView): BoardKeeper | null {
  const list = (view.field?.situation_objects ?? []).filter((o) => o.panel === "board" && o.figure != null);
  return [...list].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0))[0] ?? null;
}

/** 讀公告板（`api.worldBoard`）：角色或世界畫面換了才重讀。 */
export function useBoard(characterId: string, view: WorldView): { board: SeasonBoardView | null; error: string | null } {
  const [board, setBoard] = useState<SeasonBoardView | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    api
      .worldBoard(characterId)
      .then((b) => {
        if (!alive) return;
        setBoard(b);
        setError(null);
      })
      .catch((e: unknown) => alive && setError(e instanceof ApiError ? e.message : String(e)));
    return () => {
      alive = false;
    };
  }, [characterId, view]);
  return { board, error };
}

/** 讀好之後的面板本體（純畫面，不打 API；測試直接畫這個）。 */
export function BoardView({
  board,
  view,
  error = null,
  busy = false,
  onAct,
  onClose,
  initial,
}: {
  board: SeasonBoardView | null;
  view: WorldView;
  error?: string | null;
  busy?: boolean;
  onAct?(action: WorldAction): void;
  onClose(): void;
  initial?: string | null;
}) {
  const keeper = boardKeeper(view);
  const head = (
    <>
      <BoardFixed board={board} keeper={keeper} region={view.field?.region ?? null} onBack={onClose} />
      {error !== null && <div className="error small">{error}</div>}
    </>
  );
  return (
    <div className="world-hud-stack world-board" data-testid="world-board">
      {board === null ? (
        <div className="pnl-tabs">
          <div className="pnl-fixed">{head}</div>
          <div className="pnl-l3">讀取中…</div>
        </div>
      ) : (
        <PanelTabs tabs={boardTabs(board, { busy, onAct, onClose })} head={head} initial={initial} testId="world-board-tabs" />
      )}
    </div>
  );
}

export function BoardPanel({ characterId, view, busy = false, onAct, onClose }: Props) {
  const { board, error } = useBoard(characterId, view);
  return <BoardView board={board} view={view} error={error} busy={busy} onAct={onAct} onClose={onClose} />;
}
