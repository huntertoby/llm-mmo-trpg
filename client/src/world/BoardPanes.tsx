// 公告板分頁版的固定區與五個分頁（PNL-1b；docs/art/資訊面板-移植需求.md 3.3「公告板」，樣張 `infoPanelsTabs.js` 的 `N`／`N_TABS`）。
// **這個檔不打 API**：`PanelTabs` 量面板高度時每一頁（每個摺疊打開一次）會多掛載一遍（PNL-1a 裁定 5），所以讀公告板資料只在
// `BoardPanel.tsx`（`PanelTabs` 外面）；這裡的元件只吃已經讀好的 `SeasonBoardView`（測試掃原始碼確認沒有 `api`）。
// 字全部照伺服器（`SeasonBoardView`）；新字在 `boardTabs.ts`。
import type { ReactNode } from "react";
import type { BoardSeasonBossView, SeasonBoardView, WorldAction, WorldView } from "../api/types";
import { AccountTitles } from "../ui/AccountTitles";
import { Hint } from "../ui/Hint";
import { ClockGlyph, EmptyNote, EventBare, EventRing, Fold, FoldGroup, HudBare, InfoTip, LockGlyph, TabLine, Tag, TokenGlyph } from "../ui/PanelKit";
import type { PanelTabDef } from "../ui/PanelTabs";
import { barWidth, bossAttemptsLabel, bossEntryLabel, bossKeysLabel, bossKeysPermille, goalProgressLabel, respawnLabel } from "./board";
import {
  BOARD_TABS,
  BOARD_ZH,
  bossBadge,
  bossTone,
  bountyBadge,
  bountyRefreshText,
  bountyRuleText,
  bountyTone,
  daysAwayText,
  eventsBadge,
  eventTone,
  fullScheduleText,
  goalsBadge,
  nextMilestone,
  seasonRunning,
} from "./boardTabs";
import { EventCrest, SeasonTimeline } from "./SeasonTimeline";
import { Portrait } from "./StoryIcons";

type BoardKeeper = NonNullable<NonNullable<WorldView["field"]>["situation_objects"]>[number];

/** 守印人頭像（3.3）：1600＝36＋對話泡；面板 < 560（800×600）＝標題旁 28＋一行台詞（#44，CSS 容器查詢切換）。 */
export const KEEPER_FACE = { wide: 36, narrow: 28 } as const;

// ---------------- 固定區 ----------------

/** 標題列（樣張 `head()`＋800 的 `.ip-speaker-mini`）：「公告板」＋（窄版）守印人小頭像與一行台詞＋回到地點圖。 */
function BoardHead({ keeper, region, onBack }: { keeper: BoardKeeper | null; region: string | null; onBack?: () => void }) {
  const line = keeper?.figure?.line_zh ?? "";
  return (
    <div className="pnl-head" data-testid="world-board-head">
      <h2 className="pnl-title">{BOARD_ZH.title}</h2>
      {keeper?.figure != null && line !== "" && (
        <Hint text={`${keeper.name_zh}：${line}`}>
          <span className="pnl-speaker-mini" tabIndex={0} data-testid="world-board-keeper-mini">
            <Portrait portrait={keeper.figure.portrait} region={region} size={KEEPER_FACE.narrow} label={keeper.name_zh} />
            <span className="line">{line}</span>
          </span>
        </Hint>
      )}
      <span className="pnl-head-actions">
        {onBack !== undefined && (
          <button type="button" onClick={onBack} data-testid="pnl-back">
            回到地點圖
          </button>
        )}
      </span>
    </div>
  );
}

/** 寬版的守印人對話泡（1600；樣張 `.ip-speaker`）。 */
function KeeperBubble({ keeper, region }: { keeper: BoardKeeper; region: string | null }) {
  const line = keeper.figure?.line_zh ?? "";
  return (
    <div className="pnl-speaker" data-testid="world-board-keeper" data-keeper={keeper.id}>
      <Portrait portrait={keeper.figure?.portrait} region={region} size={KEEPER_FACE.wide} label={keeper.name_zh} />
      <div className="pnl-bubble">
        <span className="who">{keeper.name_zh}</span>
        {line}
      </div>
    </div>
  );
}

/** 「第 N 天／共 M 天」大字＋右邊兩行（日程標籤＋「第 a～b 天」；「下一個 ［第 N 天］ 名稱（明天）」）。 */
function SeasonTop({ board }: { board: SeasonBoardView }) {
  const s = board.season;
  if (!seasonRunning(s)) {
    return (
      <div className="pnl-season-top" data-testid="world-board-season">
        <span className="pnl-dayno">
          <b className="st">{s.status_zh}</b>
        </span>
      </div>
    );
  }
  const phase = s.phase ?? null;
  const next = nextMilestone(s);
  return (
    <div className="pnl-season-top" data-testid="world-board-season">
      <span className="pnl-dayno">
        第<b>{s.day}</b>天<span className="of">／共 {s.days} 天</span>
      </span>
      <span className="pnl-phase-nm">
        {phase !== null && (
          <>
            <Tag tone="open">{phase.name_zh}</Tag>
            <span>
              第 {phase.start_day}～{phase.end_day} 天
            </span>
          </>
        )}
      </span>
      {next !== null && (
        <span className="pnl-next" data-testid="world-board-next">
          <span className="k">{BOARD_ZH.next}</span>
          <Tag>第 {next.day} 天</Tag>
          <b>{next.names.join("；")}</b>
          <span className="pnl-l3">{daysAwayText(next.day, s.day)}</span>
        </span>
      )}
    </div>
  );
}

/** 固定區（3.3）：標題列 →（寬版）守印人對話泡 → 第 N 天與日程。分頁列由 `PanelTabs` 接在後面。 */
export function BoardFixed({ board, keeper, region, onBack }: { board: SeasonBoardView | null; keeper: BoardKeeper | null; region: string | null; onBack?: () => void }) {
  return (
    <>
      <BoardHead keeper={keeper} region={region} onBack={onBack} />
      {keeper?.figure != null && <KeeperBubble keeper={keeper} region={region} />}
      {board !== null && <SeasonTop board={board} />}
    </>
  );
}

// ---------------- 分頁：今日目標 ----------------

export function GoalsPane({ board }: { board: SeasonBoardView }) {
  const coins = board.goals[0]?.coins ?? 0;
  return (
    <div data-testid="world-board-goals-pane">
      <TabLine
        end={
          coins > 0 ? (
            <>
              {BOARD_ZH.goalLinePrefix}
              <TokenGlyph px={15} />
              <b className="pnl-num">+{coins}</b>
            </>
          ) : undefined
        }
      >
        {board.goals_note_zh != null && <Tag tone="info">{board.goals_note_zh}</Tag>}
      </TabLine>
      {board.goals.length === 0 ? (
        <EmptyNote>尚未開放</EmptyNote>
      ) : (
        <ul className="pnl-rows" data-testid="world-board-goals">
          {board.goals.map((g) => (
            <li key={g.goal} className={g.done ? "pnl-row pnl-goal done" : "pnl-row pnl-goal"}>
              <span className={g.done ? "pnl-check done" : "pnl-check"} />
              <span className="text">{g.text_zh}</span>
              <span className="pnl-prog">
                {!g.done && (
                  <span className="pnl-mini">
                    <i style={{ width: barWidth(Math.floor((g.progress * 1000) / Math.max(1, g.count))) }} />
                  </span>
                )}
                {goalProgressLabel(g)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------- 分頁：懸賞板 ----------------

export function BountyPane({ board }: { board: SeasonBoardView }) {
  const [colWhere, colLv, colReward, colState] = BOARD_ZH.bountyCols;
  return (
    <div data-testid="world-board-bounty-pane">
      <TabLine
        end={
          <>
            <ClockGlyph px={15} />
            {bountyRefreshText(board.season)}
            <InfoTip text={bountyRuleText(board.season)} />
          </>
        }
      >
        <span>{BOARD_ZH.bountyFirst}</span>
      </TabLine>
      {board.bounties.length === 0 ? (
        <EmptyNote>今天沒有懸賞。</EmptyNote>
      ) : (
        <>
          <div className="pnl-cols-head pnl-bounty-cols" aria-hidden="true">
            <span />
            <span>{colWhere}</span>
            <span>{colLv}</span>
            <span className="reward-h">{colReward}</span>
            <span className="state-h">{colState}</span>
          </div>
          <ul className="pnl-rows" data-testid="world-board-bounties">
            {board.bounties.map((b) => {
              const tone = bountyTone(b);
              const note = b.status_note_zh ?? null;
              return (
                <li key={b.bounty} className={`pnl-row pnl-bounty pnl-bounty-cols${b.open ? "" : " closed"}`} data-bounty={b.bounty}>
                  <EventRing id="combat" px={24} />
                  <span className="stack">
                    <span className="name">{b.name_zh}</span>
                    <span className="where">
                      <HudBare id="town" px={14} />
                      {b.location_zh}
                    </span>
                  </span>
                  <span className="lv">
                    Lv <b>{b.level}</b>
                  </span>
                  <span className="reward">
                    <TokenGlyph px={15} />
                    {b.coins}
                  </span>
                  <span className="state">
                    {note !== null ? (
                      <Hint text={note}>
                        <span className="pnl-tag-wrap" tabIndex={0} data-testid="world-board-bounty-note">
                          <Tag tone={tone}>{b.status_zh}</Tag>
                        </span>
                      </Hint>
                    ) : (
                      <Tag tone={tone}>{b.status_zh}</Tag>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}

// ---------------- 分頁：賽季時程 ----------------

export const SCHED_FOLD = "full";

export function SchedPane({ board }: { board: SeasonBoardView }) {
  const s = board.season;
  const today = seasonRunning(s) ? s.day : 0;
  return (
    <div data-testid="world-board-sched-pane">
      <TabLine
        end={
          <>
            <ClockGlyph px={16} />
            {s.next_refresh_zh}
          </>
        }
      >
        {s.phase != null && s.phase.text_zh !== "" && <span className="pnl-l2">{s.phase.text_zh}</span>}
      </TabLine>
      <SeasonTimeline season={s} events={board.world_events} />
      <FoldGroup name="board-sched">
        <Fold id={SCHED_FOLD} summary={<b>{fullScheduleText(s)}</b>} testId="world-board-sched-fold">
          <ul className="pnl-sched" data-testid="world-board-sched-list">
            {(s.milestones ?? []).map((m) => (
              <li key={`${m.id}-${m.day}`} className={m.day < today ? "past" : undefined}>
                <span className="d">第 {m.day} 天</span>
                <span className="nm">{m.name_zh}</span>
              </li>
            ))}
          </ul>
        </Fold>
      </FoldGroup>
    </div>
  );
}

// ---------------- 分頁：世界事件（＋世界變化） ----------------

export function EventsPane({ board }: { board: SeasonBoardView }) {
  const changes = board.level_bonus_zh.length > 0 || board.cleared.length > 0;
  return (
    <div data-testid="world-board-events-pane">
      <TabLine>
        <span>{BOARD_ZH.eventsLine}</span>
      </TabLine>
      {board.world_events.length === 0 ? (
        <EmptyNote>尚未開放</EmptyNote>
      ) : (
        board.world_events.map((e) => (
          <div key={e.event} className={e.status === "pending" ? "pnl-event pending" : "pnl-event"} data-testid="world-board-event" data-event={e.event}>
            <div className="pnl-event-head">
              <EventCrest region={e.region} px={18} />
              <span className="name">{e.name_zh}</span>
              <Tag>{e.days_zh}</Tag>
              <span className="end">
                <Tag tone={eventTone(e.status)}>{e.status_zh}</Tag>
              </span>
            </div>
            {e.text_zh !== "" && <div className="pnl-l2">{e.text_zh}</div>}
            <div className="pnl-bar">
              <span className="pnl-bar-track">
                <i style={{ width: barWidth(e.permille) }} />
              </span>
              <span className="pnl-bar-num">
                <b>{e.progress}</b>／{e.target}
              </span>
              {e.target_note_zh != null && <InfoTip text={`門檻：${e.target_note_zh}`} />}
            </div>
          </div>
        ))
      )}
      {changes && (
        <section className="pnl-sec" data-testid="world-board-shared">
          <div className="pnl-sec-head">
            <HudBare id="town" px={18} />
            <span className="pnl-sec-title">{BOARD_ZH.worldChanges}</span>
          </div>
          <ul className="pnl-rows">
            {board.level_bonus_zh.map((t) => (
              <li key={t} className="pnl-row pnl-change">
                <span className="text">{t}</span>
              </li>
            ))}
            {board.cleared.map((c) => (
              <li key={c.location_zh} className="pnl-row pnl-cleared">
                <span className="name">{c.location_zh}</span>
                <span className="end">
                  <Tag tone="dim">{BOARD_ZH.cleared}</Tag>
                  <ClockGlyph px={14} />
                  {respawnLabel(c.respawn_at)} 重生
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

// ---------------- 分頁：賽季頭目 ----------------

export const BOSS_FOLD = "rules";

function bossFoldEnd(boss: BoardSeasonBossView): ReactNode {
  const top = boss.board[0];
  if (top === undefined) return <Tag tone="dim">{BOARD_ZH.bossNobody}</Tag>;
  return <Tag tone="mine">第 1 名 {top.name}</Tag>;
}

export function BossPane({ boss, busy, onAct, onClose }: { boss: BoardSeasonBossView; busy: boolean; onAct?: (action: WorldAction) => void; onClose(): void }) {
  const tone = bossTone(boss.status);
  return (
    <div data-testid="world-board-boss">
      <TabLine end={<Tag tone={tone} icon={tone === "lock" ? <LockGlyph px={14} /> : undefined}>{boss.status_zh}</Tag>}>
        <b className="pnl-boss-name">{boss.name_zh}</b>
      </TabLine>
      {boss.note_zh != null && <div className="pnl-l2">{boss.note_zh}</div>}
      <div className="pnl-bar pnl-keys">
        <HudBare id="r_source" px={16} />
        <span className="pnl-l2">封印鑰匙</span>
        <span className="pnl-bar-track">
          <i style={{ width: barWidth(bossKeysPermille(boss)) }} />
        </span>
        <span className="pnl-bar-num">{bossKeysLabel(boss).replace(/^封印鑰匙：/, "")}</span>
      </div>
      {boss.first_kill_zh != null && (
        <div className="pnl-l2" data-testid="world-board-boss-first-kill">
          {boss.first_kill_zh}
          <AccountTitles titles={boss.first_kill_titles} />
        </div>
      )}
      {onAct !== undefined && boss.status === "open" && (
        <div className="pnl-boss-act">
          <button
            type="button"
            disabled={busy || !boss.can_challenge}
            data-testid="world-board-boss-challenge"
            onClick={() => {
              onAct({ kind: "season_boss" });
              onClose();
            }}
          >
            挑戰「{boss.name_zh}」
          </button>
          {boss.problem_zh != null && <span className="pnl-l3">{boss.problem_zh}</span>}
        </div>
      )}
      <FoldGroup name="board-boss">
        <Fold id={BOSS_FOLD} summary={<b>{BOARD_ZH.bossRules}</b>} end={bossFoldEnd(boss)} testId="world-board-boss-fold">
          <div className="pnl-l2">{bossAttemptsLabel(boss)}；只准系統傭兵，失敗只扣次數。</div>
          <div className="pnl-l2">通關評分榜（稱號「{boss.title_zh}」）</div>
          {boss.board.length === 0 ? (
            <div className="pnl-l3">還沒有人打倒。</div>
          ) : (
            <ul className="pnl-rows pnl-ranking" data-testid="world-board-boss-ranking">
              {boss.board.map((e) => (
                <li key={`${e.rank}-${e.name}`} className={e.mine ? "pnl-row mine" : "pnl-row"}>
                  <span>
                    {bossEntryLabel(e)}
                    <AccountTitles titles={e.titles} />
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Fold>
      </FoldGroup>
    </div>
  );
}

// ---------------- 分頁定義 ----------------

/**
 * 五個分頁（3.3：順序、短名、圖示、記號）：今日目標｜懸賞板｜賽季時程｜世界事件｜賽季頭目（沒有賽季頭目時不放）。
 * `render` 只用已讀好的 `board`，可以被 `PanelTabs` 量高度時多掛載一次。
 */
export function boardTabs(board: SeasonBoardView, opt: { busy: boolean; onAct?: (action: WorldAction) => void; onClose(): void }): PanelTabDef[] {
  const tabs: PanelTabDef[] = [
    { id: "goals", ...BOARD_TABS.goals, icon: <EventBare id="clue" px={16} />, badge: goalsBadge(board.goals), render: () => <GoalsPane board={board} /> },
    { id: "bounty", ...BOARD_TABS.bounty, icon: <EventBare id="combat" px={16} />, badge: bountyBadge(board.bounties), render: () => <BountyPane board={board} /> },
    { id: "sched", ...BOARD_TABS.sched, icon: <HudBare id="t_telegraph" px={16} />, folds: [SCHED_FOLD], render: () => <SchedPane board={board} /> },
    { id: "events", ...BOARD_TABS.events, icon: <HudBare id="bar_M" px={16} />, badge: eventsBadge(board.world_events), render: () => <EventsPane board={board} /> },
  ];
  const boss = board.season_boss ?? null;
  if (boss !== null) {
    tabs.push({
      id: "boss",
      ...BOARD_TABS.boss,
      icon: <EventBare id="b_portal" px={16} />,
      badge: bossBadge(boss),
      folds: [BOSS_FOLD],
      render: () => <BossPane boss={boss} busy={opt.busy} onAct={opt.onAct} onClose={opt.onClose} />,
    });
  }
  return tabs;
}
