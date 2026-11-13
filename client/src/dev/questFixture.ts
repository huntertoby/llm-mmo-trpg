// 開發頁 `#quest`（PNL-3）的固定資料：三個任務（新手進行中、主線進行中、支線已完成）、三條線頭。字照內容檔與伺服器的格式。
import type { NpcPortrait, WorldQuestLog, WorldThread } from "../api/types";

const GRANNY: NpcPortrait = {
  look: { skin: "#e8c8a8", hair: "bun", hair_color: "#c8c8c0", bun_band: "#b8432f" },
  gear: { body: { kind: "robe", color: "#3c4a48", trim: "#e8bb48" } },
} as unknown as NpcPortrait;

const step = (text: string, done: boolean, current: boolean): WorldQuestLog["steps"][number] => {
  const i = text.indexOf("：");
  return i > 0 ? { text_zh: text, done, current, place_zh: text.slice(0, i), task_zh: text.slice(i + 1) } : { text_zh: text, done, current, place_zh: null, task_zh: text };
};

export const DEV_QUESTS: WorldQuestLog[] = [
  {
    id: "starter_ferry",
    name_zh: "霧渡新手路",
    kind_zh: "新手",
    summary_zh: "渡婆婆要你先把渡口到梯田這一路走通。",
    giver_zh: "渡婆婆",
    giver_portrait: GRANNY,
    giver_region: "cloud_ridge",
    steps: [step("渡口石階：趕走搶渡船的盜賊", true, false), step("竹林小徑：突破雨裡包圍的霧狼", false, true), step("雨中梯田：平息盜賊和修士的衝突", false, false)],
    done: false,
    route_zh: "往北邊的出口 → 竹林小徑",
    advice_zh: null,
  },
  {
    id: "main_mist_rift",
    name_zh: "霧中的裂痕",
    kind_zh: "主線",
    summary_zh: "雲嶺的霧越來越濃，封印鑰匙 +5 才能壓住裂痕。",
    giver_zh: "渡婆婆",
    giver_portrait: GRANNY,
    giver_region: "cloud_ridge",
    steps: [step("在霧渡鎮打聽霧的來處", false, true), step("青霧觀：請觀主看看古碑", false, false), step("霧谷深處：封住裂痕", false, false)],
    done: false,
    route_zh: null,
    advice_zh: "建議先完成霧渡新手路",
  },
  {
    id: "willow_errand",
    name_zh: "柳的委託",
    kind_zh: "支線",
    summary_zh: "",
    giver_zh: "柳掌櫃",
    giver_portrait: null,
    giver_region: "cloud_ridge",
    steps: [step("把藥草送到柳掌櫃的鋪子", true, false)],
    done: true,
  },
];

const thread = (id: string, text: string, over: Partial<WorldThread> = {}): WorldThread => ({
  id,
  text_zh: text,
  scope: "personal",
  scope_zh: "個人",
  expires_zh: "2 天 23 小時後到期",
  left_zh: "剩 2 天 23 小時",
  npc_zh: null,
  location_zh: null,
  ...over,
});

export const DEV_THREADS: WorldThread[] = [
  thread("peddler_owes_you", "商人欠你人情", { npc_zh: "行商老周" }),
  thread("wolves_driven_down", "狼群是被趕下山的", { location_zh: "竹林小徑" }),
  thread("rift_whisper", "霧裡傳來的低語", { scope: "world", scope_zh: "世界", expires_zh: "不到 1 小時後到期", left_zh: "剩不到 1 小時" }),
];

export const DEV_QUEST_VIEW = { quests: DEV_QUESTS, threads: DEV_THREADS };
