// 影子循環賽（Phase 5F-4；09 9.7「季末保底」、#100、#101）：報名（每個帳號 1 個角色、第 13 天截止）、
// 勝場排行榜（報名地點已套隱藏地點的提示語）、場次列表與重播入口（既有戰鬥畫面）。全部由後端算好；左欄切換，
// 樣式沿用公告板。5F-4b：報名時可以免費重新配點（既有的配點元件）、場次分頁、規則已變的提示。
import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { LeagueView, WorldAction, WorldView } from "../api/types";
import { AttributeAllocator } from "../run/AttributeAllocator";
import { allocationTotal, type Allocation } from "../run/flow";
import { allocationToSend, pageLabel, progressLabel, rankLabel, recordLabel, signupNote, tiebreakLabel } from "./league";

interface Props {
  characterId: string;
  /** 世界畫面（每次動作之後換新：重新讀循環賽）。 */
  view: WorldView;
  busy: boolean;
  onAct(action: WorldAction): void;
  onReplay(matchId: string): void;
  onClose(): void;
}

/** 報名時預設的配點：自己這個角色已經配過就用那份，否則照自動配點。 */
function initialAllocation(l: LeagueView): Allocation {
  if (l.entry?.this_character === true && l.entry.allocation != null) return l.entry.allocation;
  return l.allocation?.auto ?? {};
}

export function LeaguePanel({ characterId, view, busy, onAct, onReplay, onClose }: Props) {
  const [league, setLeague] = useState<LeagueView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ai, setAi] = useState<string>("");
  const [page, setPage] = useState(1);
  const [alloc, setAlloc] = useState<Allocation>({});

  useEffect(() => {
    let alive = true;
    api
      .worldLeague(characterId, page)
      .then((l) => {
        if (!alive) return;
        setLeague(l);
        setAi(l.entry?.this_character === true ? (l.entry.ai ?? "") : "");
        setAlloc(initialAllocation(l));
      })
      .catch((e: unknown) => alive && setError(e instanceof ApiError ? e.message : String(e)));
    return () => {
      alive = false;
    };
  }, [characterId, view, page]);

  const pool = league?.allocation ?? null;
  const allocReady = pool === null || allocationTotal(alloc) === pool.points;
  const enter = () =>
    onAct({
      kind: "league_enter",
      ai: ai === "" ? null : ai,
      allocation: pool === null ? null : allocationToSend(alloc, pool.auto),
    });
  const mine = league?.entry?.this_character === true;

  return (
    <div className="panel world-quest-log world-board world-league" data-testid="world-league">
      <div className="world-quest-head">
        <h2>影子循環賽</h2>
        <button type="button" onClick={onClose}>
          回到地點圖
        </button>
      </div>
      {error !== null && <div className="error small">{error}</div>}
      {league === null ? (
        <div className="muted small">讀取中…</div>
      ) : (
        <>
          <div className="small" data-testid="world-league-status">
            <b>{league.status_zh}</b>
            <span className="muted">
              　賽季第 {league.season_day} 天・第 {league.signup_close_day} 天截止報名・參賽 {league.entrants} 人
            </span>
          </div>
          <div className="muted small">{league.rules_zh}</div>
          {league.maps_zh.length > 0 && (
            <div className="muted small">
              地圖：{league.maps_zh.join("、")}（每對組合 {league.per_pair} 場）
            </div>
          )}
          {league.stale_zh != null && (
            <div className="error small" data-testid="world-league-stale">
              {league.stale_zh}
            </div>
          )}

          <div className="section-title">報名</div>
          <div className="small" data-testid="world-league-signup">
            {signupNote(league)}
          </div>
          {(league.can_enter || league.can_withdraw) && (
            <>
              {league.can_enter && pool !== null && (
                <div data-testid="world-league-alloc">
                  <AttributeAllocator
                    heading="循環賽配點（拉到等級上限後，全部的點免費重新分配；不改角色本身）"
                    base={pool.base}
                    points={pool.points}
                    alloc={alloc}
                    onChange={setAlloc}
                    disabled={busy}
                  />
                  <button type="button" disabled={busy} onClick={() => setAlloc(pool.auto)} data-testid="world-league-alloc-auto">
                    照自動配點
                  </button>
                </div>
              )}
              <div className="run-actions">
                <label className="small">
                  打法{" "}
                  <select value={ai} disabled={busy} onChange={(e) => setAi(e.target.value)} data-testid="world-league-ai">
                    <option value="">預設（影子的打法）</option>
                    {league.ai_choices.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name_zh}
                      </option>
                    ))}
                  </select>
                </label>
                {league.can_enter && (
                  <button
                    type="button"
                    className="primary"
                    disabled={busy || !allocReady}
                    onClick={enter}
                    data-testid="world-league-enter"
                  >
                    {mine ? "用目前的配置更新報名" : "用目前的配置報名"}
                  </button>
                )}
                {league.can_withdraw && (
                  <button data-sfx="ui_cancel" type="button" disabled={busy} onClick={() => onAct({ kind: "league_withdraw" })} data-testid="world-league-withdraw">
                    取消報名
                  </button>
                )}
              </div>
              {!allocReady && <div className="muted small">配點要剛好用完才能報名。</div>}
            </>
          )}

          <div className="section-title">
            排行榜
            {progressLabel(league) !== null && <span className="muted small">　{progressLabel(league)}</span>}
          </div>
          {league.champion_zh != null && (
            <div className="small" data-testid="world-league-champion">
              <b>{league.champion_zh}</b>
            </div>
          )}
          {league.standings.length === 0 ? (
            <div className="muted small">還沒有人報名。</div>
          ) : (
            <table className="run-history small" data-testid="world-league-standings">
              <thead>
                <tr>
                  <th>名次</th>
                  <th>角色</th>
                  <th>定位</th>
                  <th>報名地點</th>
                  <th>戰績</th>
                </tr>
              </thead>
              <tbody>
                {league.standings.map((r) => (
                  <tr key={`${r.name}-${r.role_zh}-${r.place_zh}`} className={r.mine ? "world-league-mine" : ""}>
                    <td>{rankLabel(r)}</td>
                    <td>
                      {r.name}
                      <span className="muted">　Lv {r.level}</span>
                    </td>
                    <td>{r.role_zh}</td>
                    <td>{r.place_zh}</td>
                    <td>
                      {recordLabel(r)}
                      {tiebreakLabel(r) !== null && <div className="muted">{tiebreakLabel(r)}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {league.matches.length > 0 && (
            <>
              <div className="section-title">
                場次
                {pageLabel(league) !== null && <span className="muted small">　{pageLabel(league)}（自己的場次在前）</span>}
              </div>
              <ul className="world-threads small world-league-matches" data-testid="world-league-matches">
                {league.matches.map((m) => (
                  <li key={m.id} className={m.mine ? "" : "muted"}>
                    <span className="muted">{m.id}　</span>
                    {m.ally_name}（先手） vs {m.enemy_name}
                    <span className="muted">{`・${m.map_zh}・種子 ${m.seed_index + 1}　`}</span>
                    {m.result_zh}
                    {m.replayable && (
                      <button type="button" className="world-league-replay" disabled={busy} onClick={() => onReplay(m.id)} data-testid="world-league-replay">
                        重播
                      </button>
                    )}
                    {m.replay_problem_zh != null && <span className="muted">　（{m.replay_problem_zh}）</span>}
                  </li>
                ))}
              </ul>
              {league.pages > 1 && (
                <div className="run-actions" data-testid="world-league-pages">
                  <button data-sfx="ui_page" type="button" disabled={league.page <= 1} onClick={() => setPage(league.page - 1)}>
                    上一頁
                  </button>
                  <span className="small">{pageLabel(league)}</span>
                  <button data-sfx="ui_page" type="button" disabled={league.page >= league.pages} onClick={() => setPage(league.page + 1)}>
                    下一頁
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
