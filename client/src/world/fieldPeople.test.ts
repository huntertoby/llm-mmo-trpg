// Phase 6B-4：實地地圖上的人（NPC 好感表情、「！」、對話泡泡、朋友的影子）與走到旁邊開的浮動面板。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { ChronicleView, FieldView, WorldDialogLine, WorldView } from "../api/types";
import { headAnchor as anchorOf } from "./fieldPeople";
import { FieldHeads } from "./FieldHeads";
import { FriendCard, HudHirePanel, HudNpcPanel } from "./FieldPanels";
import {
  barlessIds,
  fieldDrawModel,
  FIELD_HERO,
  friendUnitId,
  hoverText,
  interactTarget,
  npcUnitId,
  targetAt,
  type FieldFriend,
} from "./fieldModel";
import { bubbleText, BUBBLE_MAX, friendChronicle, frozenFriends, headMarks, npcBubbles, RANK_FACE, rankOf } from "./fieldPeople";
import { panelAvailable, shownPanel } from "./hud";

const LOOK = { template_id: "hero_mage", weapon_id: "fire_staff", weapon_class: "focus", doll_look: null, race_look: null, equipment: [] };

function friend(owner: string, x: number, y: number): FieldFriend {
  return { owner, name_zh: owner === "bob" ? "阿博" : owner, level: 3, x, y, facing: "s", look: LOOK };
}

/** 6×4 的小鎮：渡婆（任務「！」、中立）、柳掌櫃（傳聞「！」、友善）、石師傅（沒有「！」、冷淡）；朋友阿博站在 (4,3)。 */
function town(over: Partial<FieldView> = {}): FieldView {
  const tiles = Array.from({ length: 24 }, (_, i) => ({ x: i % 6, y: Math.floor(i / 6), height: i === 5 ? 2 : 0, terrain: "stone", surface: "none", walkable: true }));
  return {
    map_id: "mist_ferry",
    name_zh: "霧渡鎮",
    region: "cloud_ridge",
    location: "mist_ferry",
    interior: false,
    width: 6,
    height: 4,
    tiles,
    tiles_hash: "",
    open_cells: [],
    objects: [],
    exits: [],
    doors: [],
    stones: [],
    npcs: [
      { id: "granny_du", name_zh: "渡婆婆", x: 1, y: 1, rank: "neutral", rank_zh: "中立", alert: "quest", alert_zh: "有任務可以接" },
      { id: "shopkeeper_liu", name_zh: "柳掌櫃", x: 3, y: 1, rank: "friendly", rank_zh: "友善", alert: "rumor", alert_zh: "有新的傳聞" },
      { id: "smith_shi", name_zh: "石師傅", x: 5, y: 1, rank: "cold", rank_zh: "冷淡", alert: null },
    ],
    facilities: [{ kind: "hire", x: 0, y: 3 }],
    me: { x: 2, y: 3, facing: "e" },
    max_climb: 1,
    walk_max_steps: 30,
    hero: LOOK,
    stone_targets: [],
    enemies: [],
    friends: [friend("bob", 4, 3)],
    campfires: [],
    situation_objects: [],
    sneaking: false,
    sneak_cost: 1,
    footprints: [],
    buildings: [],
    chasm_style: "default",
    decor: [],
    ...over,
  };
}

describe("好感表情（表格）", () => {
  it.each([
    ["hostile", -1],
    ["cold", -0.5],
    ["neutral", 0],
    ["friendly", 0.6],
    ["trusted", 1],
  ] as const)("%s → 嘴的彎度 %d", (rank, mood) => {
    expect(RANK_FACE[rank].mood).toBe(mood);
  });

  it("級別由低到高，表情越來越開心；不認得的級別當中立", () => {
    const order = ["hostile", "cold", "neutral", "friendly", "trusted"] as const;
    const moods = order.map((r) => RANK_FACE[r].mood);
    expect([...moods].sort((a, b) => a - b)).toEqual(moods);
    expect(rankOf("???")).toBe("neutral");
    expect(rankOf(undefined)).toBe("neutral");
  });
});

describe("頭上的「！」與表情（資料由伺服器給）", () => {
  it.each([
    ["granny_du", "quest", "neutral"],
    ["shopkeeper_liu", "rumor", "friendly"],
    ["smith_shi", null, "cold"],
  ] as const)("%s：「！」＝%s、表情＝%s", (id, alert, rank) => {
    const mark = headMarks(town()).find((m) => m.id === id)!;
    expect(mark.alert).toBe(alert);
    expect(mark.rank).toBe(rank);
  });

  it("畫出來：每位 NPC 一張臉、有「！」的才畫、朋友只畫名牌不畫表情", () => {
    const field = town();
    const html = renderToStaticMarkup(createElement(FieldHeads, { marks: headMarks(field), grid: field, scale: 1, onPick: () => undefined }));
    expect(html.match(/data-testid="field-face"/g)).toHaveLength(3);
    expect(html.match(/data-testid="field-alert"/g)).toHaveLength(2);
    expect(html).toContain('data-alert="quest"');
    expect(html).toContain('data-alert="rumor"');
    expect(html).toContain('data-head="friend:bob"');
    expect(html.match(/data-testid="field-friend-tag"/g)).toHaveLength(1);
  });

  it("頭頂的位置照格子中心、扣掉抬高（高的格子往上）", () => {
    const field = town();
    const flat = anchorOf(field, { x: 4, y: 0 }, 1);
    const high = anchorOf(field, { x: 5, y: 0 }, 1);
    expect(flat.left).toBe(4.5 * 48);
    expect(high.top).toBeLessThan(flat.top);
    expect(anchorOf(field, { x: 4, y: 0 }, 0.5).left).toBe(flat.left / 2);
  });
});

describe("NPC 與朋友不畫血條", () => {
  it("NPC、朋友的單位帶 noBar；主角照畫", () => {
    const field = town();
    const model = fieldDrawModel(field);
    const byId = new Map(model.units.map((u) => [u.id, u]));
    for (const n of field.npcs) expect(byId.get(npcUnitId(n.id))?.noBar).toBe(true);
    expect(byId.get(friendUnitId("bob"))?.noBar).toBe(true);
    expect(byId.get(FIELD_HERO)?.noBar).toBeUndefined();
    expect(barlessIds(field).size).toBe(4);
  });

  it("沒有外觀資料的 NPC 用預設範本（npc_<id>）；朋友用存影子時的外觀", () => {
    const model = fieldDrawModel(town());
    expect(model.units.find((u) => u.id === npcUnitId("granny_du"))?.template).toBe("npc_granny_du");
    const bob = model.units.find((u) => u.id === friendUnitId("bob"));
    expect(bob?.template).toBe("hero_mage");
    expect(bob?.weaponId).toBe("fire_staff");
    expect(bob?.team).toBe("ally");
  });
});

describe("朋友", () => {
  it("點朋友的格子＝朋友（NPC 優先）；說明列寫名片", () => {
    const field = town();
    expect(targetAt(field, { x: 4, y: 3 })).toEqual({ kind: "friend", owner: "bob", name: "阿博", x: 4, y: 3 });
    expect(hoverText(field, { x: 4, y: 3 })).toBe("阿博的影子（點了看名片）");
    expect(interactTarget({ ...field, me: { x: 3, y: 3, facing: "e" } })).toMatchObject({ kind: "friend", owner: "bob" }); // 面向東、旁邊就是他
  });

  it("名單每次進城更新一次：同一張地圖沿用進來時的名單，換地圖才換", () => {
    const first = frozenFriends(null, town());
    const later = frozenFriends(first, town({ friends: [friend("bob", 4, 3), friend("carol", 1, 3)] }));
    expect(later).toBe(first);
    expect(later.friends.map((f) => f.owner)).toEqual(["bob"]);
    const inside = frozenFriends(later, town({ map_id: "mist_ferry_tavern", friends: [] }));
    expect(inside.friends).toEqual([]);
    const back = frozenFriends(inside, town({ friends: [friend("bob", 4, 3), friend("carol", 1, 3)] }));
    expect(back.friends.map((f) => f.owner)).toEqual(["bob", "carol"]);
  });

  it("編年史只列這位朋友的紀錄", () => {
    const chronicle = {
      current_season: "s1",
      seasons: [
        {
          season_id: "s1",
          name_zh: "第一季",
          current: true,
          started_at: null,
          reset_at: null,
          heroes: [
            { name: "阿博", text_zh: "打倒霧狼王", character_id: "bob", titles: [] },
            { name: "小卡", text_zh: "完成青霧之爭", character_id: "carol", titles: [] },
          ],
          recipes: [],
          first_kills: [{ kind: "elite", target_name_zh: "斷崖幫頭目", name: "阿博", character_id: "bob", titles: [] }],
          league: [],
          boss_board: [{ name: "小卡", score: 90, rounds: 8, title_zh: "", character_id: "carol", titles: [] }],
        },
      ],
    } as unknown as ChronicleView;
    expect(friendChronicle(chronicle, "bob")).toEqual(["第一季（進行中）：打倒霧狼王", "第一季（進行中）：首殺 斷崖幫頭目"]);
    expect(friendChronicle(chronicle, "carol")).toEqual(["第一季（進行中）：完成青霧之爭", "第一季（進行中）：賽季頭目評分 90 分"]);
    expect(friendChronicle(null, "bob")).toEqual([]);
  });
});

describe("對話泡泡（21.7：1～2 句）", () => {
  it("取前兩句、太長截斷；酒館傳聞不算", () => {
    expect(bubbleText("第一句。第二句！第三句？")).toBe("第一句。第二句！");
    expect(bubbleText("長".repeat(60))).toBe(`${"長".repeat(BUBBLE_MAX)}……`);
    const lines = [
      { npc: "granny_du", speaker_zh: "渡婆婆", kind: "rumor", text_zh: "夜裡有燈籠隊。往山裡去了。還有別的。" },
      { npc: "granny_du", speaker_zh: "渡婆婆", kind: "chat", text_zh: "第二段" },
      { npc: null, speaker_zh: "酒館", kind: "tavern", text_zh: "傳聞" },
    ] as unknown as WorldDialogLine[];
    const bubbles = npcBubbles(lines);
    expect([...bubbles.entries()]).toEqual([["granny_du", "夜裡有燈籠隊。往山裡去了。"]]);
    expect(headMarks(town(), bubbles).find((m) => m.id === "granny_du")?.bubble).toBe("夜裡有燈籠隊。往山裡去了。");
  });
});

// ---- 浮動面板 ----

function worldView(over: Partial<WorldView> = {}): WorldView {
  return {
    field: town(),
    npcs_here: [
      { id: "granny_du", name_zh: "渡婆婆", role_zh: "擺渡人", affinity: 0, rank: "neutral", rank_zh: "中立", range_zh: "中立（−9～19）", talk_zh: "一般傳聞" },
      { id: "shopkeeper_liu", name_zh: "柳掌櫃", role_zh: "雜貨", affinity: 20, rank: "friendly", rank_zh: "友善", range_zh: "", talk_zh: "" },
    ],
    quests_here: [
      { id: "starter_ferry", name_zh: "霧渡新手路", kind_zh: "新手", summary_zh: "", giver_zh: "渡婆婆", can_accept: true },
      { id: "other", name_zh: "柳的委託", kind_zh: "支線", summary_zh: "", giver_zh: "柳掌櫃", can_accept: true },
    ],
    encounter: null,
    battle_id: null,
    party: {
      members: [{ name_zh: "阿霧", title_zh: "主角", level: 1 }],
      max_hired: 2,
      can_hire: true,
      hire_problem_zh: null,
      mercenaries: [{ id: "merc_a", name_zh: "賽倫", title_zh: "坦", role: "tank", role_zh: "坦", theme_zh: "", skills_zh: [], hired: false }],
      shadows: [
        {
          owner: "bob",
          name_zh: "阿博",
          level: 3,
          role_zh: "長劍・人類",
          skills_zh: ["火球", "護盾"],
          borrowed_level: 1,
          borrowed_tier: 1,
          capped: true,
          cap_zh: "借用時壓到 Lv 1",
          hired: false,
          saved_zh: "霧渡鎮",
          titles: [],
        },
      ],
      ai_choices: [],
      ai: {},
    },
    ...over,
  } as unknown as WorldView;
}

describe("走到旁邊開的浮動面板", () => {
  const noop = () => undefined;
  const chat = () => Promise.resolve(true);

  it("NPC 面板只有這一位與他給的任務，上方有頭像（好感表情）與「！」說明", () => {
    const html = renderToStaticMarkup(createElement(HudNpcPanel, { view: worldView(), npc: "granny_du", busy: false, chats: {}, onAct: noop, onChat: chat }));
    expect(html).toContain('data-testid="world-hud-npc"');
    expect(html.match(/data-testid="world-npc"/g)).toHaveLength(1);
    expect(html).toContain('data-npc="granny_du"');
    expect(html).not.toContain('data-npc="shopkeeper_liu"');
    expect(html).toContain("霧渡新手路");
    expect(html).not.toContain("柳的委託");
    expect(html).toContain("rank-neutral");
    expect(html).toContain("有任務可以接");
  });

  it("雇用面板直接展開雇用清單；不能雇用時寫理由", () => {
    const html = renderToStaticMarkup(createElement(HudHirePanel, { view: worldView(), busy: false, onAct: noop }));
    expect(html).toContain('data-testid="world-hud-hire"');
    expect(html).toContain('data-testid="world-hire"');
    const party = { ...worldView().party!, can_hire: false, hire_problem_zh: "出城前在城鎮選好" };
    const no = renderToStaticMarkup(createElement(HudHirePanel, { view: worldView({ party }), busy: false, onAct: noop }));
    expect(no).not.toContain('data-testid="world-hire"');
    expect(no).toContain("出城前在城鎮選好");
  });

  it("朋友名片：build（等級、定位、技能、存的地點）＋編年史（讀取中）", () => {
    const html = renderToStaticMarkup(createElement(FriendCard, { view: worldView(), owner: "bob" }));
    expect(html).toContain("阿博的影子");
    expect(html).toContain("Lv 3・長劍・人類・存在霧渡鎮");
    expect(html).toContain("火球、護盾");
    expect(html).toContain("編年史");
    expect(html).toContain("讀取中");
  });

  it("面板同時只開一個：npc、hire、friend 都是 HUD 面板", () => {
    const v = worldView();
    for (const p of ["npc", "hire", "friend"] as const) {
      expect(panelAvailable(v, p)).toBe(true);
      expect(shownPanel(v, p)).toBe(p);
    }
    expect(panelAvailable(worldView({ party: null }), "hire")).toBe(false);
  });
});
