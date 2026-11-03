// 城鎮公告板（Phase 5F-1；09 9.7、9.6.9 #99、9.6.10 #103、18.7.4）：賽季第幾天與日程、今日目標 3 條、
// 懸賞板（先搶先贏）、世界事件全服進度、已清空的地點。全部由後端算好（換日後的世界，只讀）；左欄切換，
// 樣式沿用任務日誌與一輪的進度條。
import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { SeasonBoardView, WorldView } from "../api/types";
import { barWidth, eventProgressLabel, goalProgressLabel, respawnLabel } from "./board";

interface Props {
  characterId: string;
  /** 世界畫面（每次動作之後換新：重新讀公告板）。 */
  view: WorldView;
  onClose(): void;
}

export function BoardPanel({ characterId, view, onClose }: Props) {
  const [board, setBoard] = useState<SeasonBoardView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .worldBoard(characterId)
      .then((b) => alive && setBoard(b))
      .catch((e: unknown) => alive && setError(e instanceof ApiError ? e.message : String(e)));
    return () => {
      alive = false;
    };
  }, [characterId, view]);

  return (
    <div className="panel world-quest-log world-board" data-testid="world-board">
      <div className="world-quest-head">
        <h2>公告板</h2>
        <button type="button" onClick={onClose}>
          回到地點圖
        </button>
      </div>
      {error !== null && <div className="error small">{error}</div>}
      {board === null ? (
        <div className="muted small">讀取中…</div>
      ) : (
        <>
          <div className="small" data-testid="world-board-season">
            <b>{board.season.status_zh}</b>
            <span className="muted">　{board.season.next_refresh_zh}</span>
          </div>
          {board.season.phase_zh != null && <div className="muted small">{board.season.phase_zh}</div>}
          {board.season.upcoming.length > 0 && (
            <div className="muted small">
              接下來：{board.season.upcoming.map((m) => `第 ${m.day} 天 ${m.name_zh}`).join("；")}
            </div>
          )}

          <div className="section-title">
            今日目標{board.goals_note_zh != null && <span className="muted small">　{board.goals_note_zh}</span>}
          </div>
          {board.goals.length === 0 ? (
            <div className="muted small">（尚未開放）</div>
          ) : (
            <ul className="world-quest-steps small" data-testid="world-board-goals">
              {board.goals.map((g) => (
                <li key={g.goal} className={g.done ? "done" : "todo"}>
                  <span className="world-step-mark">{g.done ? "✓" : "・"}</span> {g.text_zh}
                  <span className="muted">　{goalProgressLabel(g)}</span>
                </li>
              ))}
            </ul>
          )}

          <div className="section-title">懸賞板</div>
          {board.bounties.length === 0 ? (
            <div className="muted small">今天沒有懸賞。</div>
          ) : (
            <ul className="world-threads small" data-testid="world-board-bounties">
              {board.bounties.map((b) => (
                <li key={b.bounty} className={b.open ? "" : "muted"}>
                  <b>{b.name_zh}</b>
                  <span className="muted">{`　${b.location_zh}・建議 Lv ${b.level}・任務幣 ${b.coins}　`}</span>
                  <span className={b.open ? "world-board-open" : ""}>{b.status_zh}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="muted small">先打倒的人拿走當天的懸賞（{board.season.next_refresh_zh}）。</div>

          <div className="section-title">世界事件</div>
          {board.world_events.length === 0 ? (
            <div className="muted small">（尚未開放）</div>
          ) : (
            board.world_events.map((e) => (
              <div key={e.event} className="world-board-event" data-testid="world-board-event">
                <div className="small">
                  <b>{e.name_zh}</b>
                  <span className="muted">　{e.days_zh}</span>
                </div>
                {e.text_zh !== "" && <div className="muted small">{e.text_zh}</div>}
                <div className="run-bar">
                  <span className="run-bar-track">
                    <span className="run-bar-fill world-board-fill" style={{ width: barWidth(e.permille) }} />
                  </span>
                  <span className="small">{eventProgressLabel(e)}</span>
                </div>
                {e.target_note_zh != null && <div className="muted small">門檻：{e.target_note_zh}</div>}
              </div>
            ))
          )}

          {(board.cleared.length > 0 || board.level_bonus_zh.length > 0) && (
            <>
              <div className="section-title">世界變化</div>
              <ul className="world-threads small" data-testid="world-board-shared">
                {board.level_bonus_zh.map((t) => (
                  <li key={t}>{t}</li>
                ))}
                {board.cleared.map((c) => (
                  <li key={c.location_zh}>
                    {c.location_zh}：已清空<span className="muted">（{respawnLabel(c.respawn_at)} 重生）</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </div>
  );
}
