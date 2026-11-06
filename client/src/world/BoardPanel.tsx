// 城鎮公告板（Phase 5F-1；09 9.7、9.6.9 #99、9.6.10 #103、18.7.4）：賽季第幾天與日程、今日目標 3 條、
// 懸賞板（先搶先贏）、世界事件全服進度、已清空的地點；5F-3 加賽季 Boss（封印、鑰匙、帳號今天的次數、
// 首殺、評分榜、挑戰按鈕）。全部由後端算好（換日後的世界，只讀）；左欄切換，樣式沿用任務日誌與一輪的進度條。
import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { AccountTitles } from "../ui/AccountTitles";
import type { SeasonBoardView, WorldAction, WorldView } from "../api/types";
import { PORTRAIT_SIZES } from "../render/portrait";
import { Portrait } from "./StoryIcons";
import {
  barWidth,
  bossAttemptsLabel,
  bossEntryLabel,
  bossKeysLabel,
  bossKeysPermille,
  eventProgressLabel,
  goalProgressLabel,
  respawnLabel,
} from "./board";

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

export function BoardPanel({ characterId, view, busy = false, onAct, onClose }: Props) {
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

  const keeper = boardKeeper(view);
  return (
    <div className="panel world-quest-log world-board" data-testid="world-board">
      <div className="world-quest-head">
        <h2>公告板</h2>
        <button type="button" onClick={onClose}>
          回到地點圖
        </button>
      </div>
      {keeper?.figure != null && (
        <div className="world-npc-portrait" data-testid="world-board-keeper" data-keeper={keeper.id}>
          <span className="world-npc-face">
            <Portrait portrait={keeper.figure.portrait} region={view.field?.region ?? null} size={PORTRAIT_SIZES.line} label={keeper.name_zh} />
          </span>
          <div>
            <b>{keeper.name_zh}</b>
            {(keeper.figure.line_zh ?? "") !== "" && <div className="small">{keeper.figure.line_zh}</div>}
          </div>
        </div>
      )}
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

          {board.season_boss != null && (
            <div className="world-board-event" data-testid="world-board-boss">
              <div className="section-title">賽季頭目</div>
              <div className="small">
                <b>{board.season_boss.name_zh}</b>
                <span className={`lead-gap ${board.season_boss.status === "open" ? "world-board-open" : "muted"}`}>
                  {board.season_boss.status_zh}
                </span>
              </div>
              {board.season_boss.note_zh != null && <div className="muted small">{board.season_boss.note_zh}</div>}
              <div className="run-bar">
                <span className="run-bar-track">
                  <span
                    className="run-bar-fill world-board-fill"
                    style={{ width: barWidth(bossKeysPermille(board.season_boss)) }}
                  />
                </span>
                <span className="small">封印鑰匙：{bossKeysLabel(board.season_boss)}</span>
              </div>
              <div className="muted small">
                {bossAttemptsLabel(board.season_boss)}；只准系統傭兵，失敗只扣次數。
              </div>
              {board.season_boss.first_kill_zh != null && (
                <div className="small" data-testid="world-board-boss-first-kill">
                  {board.season_boss.first_kill_zh}
                  <AccountTitles titles={board.season_boss.first_kill_titles} />
                </div>
              )}
              {onAct !== undefined && board.season_boss.status === "open" && (
                <div>
                  <button
                    type="button"
                    disabled={busy || !board.season_boss.can_challenge}
                    data-testid="world-board-boss-challenge"
                    onClick={() => {
                      onAct({ kind: "season_boss" });
                      onClose();
                    }}
                  >
                    挑戰「{board.season_boss.name_zh}」
                  </button>
                  {board.season_boss.problem_zh != null && (
                    <span className="muted small">　{board.season_boss.problem_zh}</span>
                  )}
                </div>
              )}
              <div className="small">通關評分榜（稱號「{board.season_boss.title_zh}」）</div>
              {board.season_boss.board.length === 0 ? (
                <div className="muted small">還沒有人打倒。</div>
              ) : (
                <ul className="world-threads small" data-testid="world-board-boss-ranking">
                  {board.season_boss.board.map((e) => (
                    <li key={`${e.rank}-${e.name}`} className={e.mine ? "world-board-open" : ""}>
                      {bossEntryLabel(e)}
                      <AccountTitles titles={e.titles} />
                    </li>
                  ))}
                </ul>
              )}
            </div>
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
