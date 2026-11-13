// 公告板的固定資料（pnl2-merge：開發頁 panel-gallery.html#board 實測切分頁捲動歸零與鎖高；內容照 world/pnl1bBoard.test.ts）。
import type { BoardSeasonBossView, BoardWorldEventView, SeasonBoardView, WorldView } from "../api/types";

const ev = (event: string, name: string, a: number, b: number, status: BoardWorldEventView["status"], region: string | null): BoardWorldEventView => ({
  event,
  name_zh: name,
  text_zh: `${name}的說明`,
  status,
  status_zh: { pending: "尚未開始", active: "進行中", succeeded: "成功", failed: "失敗" }[status],
  progress: 0,
  target: 30,
  permille: 0,
  days_zh: `第 ${a}～${b} 天`,
  start_day: a,
  end_day: b,
  region,
  target_note_zh: status === "active" ? "沒有前一天的上線紀錄，用原門檻" : null,
});

const boss: BoardSeasonBossView = {
  boss: "rift_shard_lord",
  name_zh: "碎晶之主",
  status: "sealed",
  status_zh: "封印中",
  note_zh: "11 月 10 日 06:00 解鎖",
  announce_at: 0,
  unlock_at: 0,
  close_at: 0,
  world_keys: 0,
  keys_target: null,
  my_keys: 0,
  keys_required: 1,
  attempts_left: 3,
  daily_attempts: 3,
  can_challenge: false,
  problem_zh: null,
  first_kill_zh: null,
  first_kill_titles: [],
  title_zh: "碎晶的終結者",
  board: [],
};

const ms = (id: string, day: number, name: string, kinds: ("story_skill" | "boss_unlock" | "league" | "other")[]) => ({ id, day, name_zh: name, kind: kinds[0]!, kinds });

export const DEV_BOARD: SeasonBoardView = {
  season: {
    day: 1,
    days: 14,
    status: "running",
    status_zh: "賽季第 1 天／共 14 天",
    phase_zh: "霧中裂痕：主線第 1～2 章、雲嶺；世界事件「霧潮入侵」",
    phase: { id: "act1", name_zh: "霧中裂痕", text_zh: "主線第 1～2 章、雲嶺；世界事件「霧潮入侵」", start_day: 1, end_day: 3 },
    phases: [
      { id: "act1", name_zh: "霧中裂痕", text_zh: "a", start_day: 1, end_day: 3 },
      { id: "act2", name_zh: "灰燼之心", text_zh: "b", start_day: 4, end_day: 7 },
      { id: "act3", name_zh: "封印", text_zh: "c", start_day: 8, end_day: 10 },
      { id: "race", name_zh: "頭目競賽", text_zh: "d", start_day: 11, end_day: 13 },
      { id: "finale", name_zh: "季末", text_zh: "e", start_day: 14, end_day: 14 },
    ],
    upcoming: [],
    milestones: [
      ms("story_skill_1", 2, "主線第 1 章的劇情技能", ["story_skill"]),
      ms("story_skill_2", 6, "主線第 2 章的劇情技能", ["story_skill"]),
      ms("boss_earliest", 8, "賽季頭目最早解鎖", ["boss_unlock"]),
      ms("boss_forced", 10, "賽季頭目強制解鎖；主線第 3 章的劇情技能", ["boss_unlock", "story_skill"]),
      ms("league_signup_close", 13, "影子循環賽截止報名", ["league"]),
      ms("league", 14, "影子循環賽", ["league"]),
    ],
    next_refresh_at: 0,
    next_refresh_zh: "每天 06:00 刷新",
    refresh_time_zh: "06:00",
  },
  goals: [
    { goal: "starter_steps", text_zh: "完成新手任務 2 步", progress: 0, count: 2, done: false, coins: 1 },
    { goal: "reveal_hidden", text_zh: "發現 1 個隱藏地點", progress: 1, count: 1, done: true, coins: 1 },
    { goal: "elite_once", text_zh: "打倒 1 隻精英", progress: 0, count: 1, done: false, coins: 1 },
  ],
  goals_note_zh: "新手期：教學目標",
  bounties: [
    { bounty: "north_wolf_king", name_zh: "北坡狼王", location_zh: "北坡獵場", level: 5, coins: 3, open: true, claimed_by: null, status_zh: "懸賞中", status_note_zh: null },
    { bounty: "mist_swordsman", name_zh: "霧中劍客", location_zh: "劍冢", level: 5, coins: 3, open: true, claimed_by: null, status_zh: "懸賞中", status_note_zh: null },
    { bounty: "scarface", name_zh: "斷崖幫二當家「疤面」", location_zh: "斷崖幫寨", level: 4, coins: 3, open: false, claimed_by: "小美", status_zh: "已被 小美 搶下", status_note_zh: "今天第一次交手打倒仍有小獎：任務幣 1" },
  ],
  world_events: [ev("mist_tide", "霧潮入侵", 1, 3, "active", "cloud_ridge"), { ...ev("lava_breach", "熔岩潰堤", 4, 7, "pending", "ashen_waste"), text_zh: "全服在赤沙村、灰井村、鐵爐村打贏守點戰；成功則熔心坑提早開放、封印鑰匙 +5" }, ev("seal_resonance", "封印共鳴", 7, 10, "pending", null)],
  cleared: [{ location_zh: "斷崖哨站", respawn_at: 0 }],
  level_bonus_zh: ["灰燼荒原：建議等級 +1"],
  season_boss: boss,
};

export const DEV_BOARD_VIEW = {
  field: {
    region: "capital",
    situation_objects: [{ id: "seal_keeper", name_zh: "守印人", panel: "board", figure: { portrait: null, line_zh: "封印和懸賞的消息，都貼在板上了。" } }],
  },
} as unknown as WorldView;
