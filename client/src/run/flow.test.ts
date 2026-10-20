import { describe, expect, it } from "vitest";
import type { RunHero, RunNode, RunOffer, RunResponse, SkillCard } from "../api/types";
import {
  adjustAllocation,
  allocationComplete,
  baseAttributes,
  isNotFoundStatus,
  needsLogRestore,
  resumeRun,
  allocationTotal,
  battleName,
  cleanAllocation,
  CURRENT_RUN_KEY,
  displayOrder,
  downedBattles,
  levelUpReady,
  needsReplacement,
  offerGroupKey,
  pickChoice,
  pickReady,
  readCurrentRun,
  recordText,
  replaceOptions,
  runView,
  saveLabel,
  slotOf,
  slotUsage,
  writeCurrentRun,
} from "./flow";

function card(id: string, kind_id: string): SkillCard {
  return { id, name_zh: id, kind_id, kind: kind_id } as unknown as SkillCard;
}

function hero(skills: SkillCard[]): RunHero {
  return { level: 2, skills } as unknown as RunHero;
}

function offer(count = 3, offRoute: number[] = [2]): RunOffer {
  return {
    reason: "level_up",
    tier: 1,
    top_attribute: "int",
    candidates: Array.from({ length: count }, (_, i) => card(`new${i}`, "active")),
    off_route: offRoute,
  };
}

function run(node: RunNode, over: Partial<RunResponse> = {}): RunResponse {
  return {
    run_id: "abc",
    seed: 7,
    node,
    hero: hero([card("a", "active")]),
    battles_done: 0,
    plan: [
      { index: 1, map_id: "m1", map_name_zh: "冰湖", boss: false, enemies: ["盜賊", "弓手"], done: false },
      { index: 2, map_id: "m2", map_name_zh: "平原", boss: false, enemies: ["盜賊"], done: false },
      { index: 6, map_id: "mb", map_name_zh: "巢穴", boss: true, enemies: ["頭目"], done: false },
    ],
    history: [],
    battle_id: null,
    ...over,
  } as RunResponse;
}

describe("runView：每種節點", () => {
  it("battle：下一場的地圖與敵人，按鈕是開始", () => {
    const v = runView(run({ kind: "battle", battle_index: 1, boss: false }));
    expect(v).toMatchObject({
      screen: "progress",
      index: 1,
      boss: false,
      mapName: "冰湖",
      enemies: ["盜賊", "弓手"],
      resume: false,
      buttonLabel: "開始第 1 場",
    });
  });

  it("battle：Boss 戰", () => {
    const v = runView(run({ kind: "battle", battle_index: 6, boss: true }));
    expect(v).toMatchObject({ screen: "progress", boss: true, buttonLabel: "開始 Boss 戰", mapName: "巢穴" });
  });

  it("讀檔回來在戰鬥中：按鈕是繼續（有 battle_id）", () => {
    const v = runView(run({ kind: "battle", battle_index: 2, boss: false }, { battle_id: "b1" }));
    expect(v).toMatchObject({ screen: "progress", resume: true, buttonLabel: "繼續第 2 場" });
  });

  it("Boss 戰讀檔回來：「繼續 Boss 戰」有空格", () => {
    const v = runView(run({ kind: "battle", battle_index: 6, boss: true }, { battle_id: "b1" }));
    expect(v).toMatchObject({ buttonLabel: "繼續 Boss 戰" });
  });

  it("level_up：等級、點數、候選", () => {
    const o = offer();
    const v = runView(run({ kind: "level_up", level: 3, points: 2, offer: o }));
    expect(v).toEqual({ screen: "level_up", level: 3, points: 2, offer: o });
  });

  it("level_up 缺候選會丟錯，不會顯示空白畫面", () => {
    expect(() => runView(run({ kind: "level_up", level: 3, points: 2 }))).toThrow();
  });

  it("campfire：未重骰與已重骰", () => {
    expect(runView(run({ kind: "campfire", after_battle: 3, rerolls_left: 1 }))).toEqual({
      screen: "campfire",
      afterBattle: 3,
      rerollsLeft: 1,
      offer: null,
    });
    const o = offer();
    expect(runView(run({ kind: "campfire", after_battle: 3, rerolls_left: 0, offer: o }))).toMatchObject({
      screen: "campfire",
      rerollsLeft: 0,
      offer: o,
    });
  });

  it("ended：勝利與失敗", () => {
    expect(runView(run({ kind: "ended", victory: true }))).toEqual({ screen: "ended", victory: true });
    expect(runView(run({ kind: "ended", victory: false }))).toEqual({ screen: "ended", victory: false });
  });
});

describe("主角倒下與歷程", () => {
  const rec = (index: number, won: boolean, down: boolean, reason: string | null = null) =>
    ({ index, won, hero_downed: down, end_reason: reason, rounds: 4 }) as RunResponse["history"][number];

  it("downedBattles 列出主角曾倒下的場次", () => {
    const r = run({ kind: "ended", victory: true }, { history: [rec(1, true, false), rec(2, true, true)] });
    expect(downedBattles(r)).toEqual([2]);
  });

  it("recordText", () => {
    expect(recordText(rec(1, true, true))).toBe("勝利・4 輪・主角曾倒下");
    expect(recordText(rec(2, false, false, "eliminate"))).toBe("失敗（全滅）・4 輪");
    expect(battleName(6, true)).toBe("Boss 戰");
    expect(battleName(2, false)).toBe("第 2 場");
  });
});

describe("候選顯示順序（偏離路線不固定在最後）", () => {
  it("同一組永遠相同，且是 0..n-1 的排列", () => {
    const a = displayOrder(7, "level_up:2", 3);
    expect(displayOrder(7, "level_up:2", 3)).toEqual(a);
    expect([...a].sort()).toEqual([0, 1, 2]);
  });

  it("偏離路線（索引 2）出現在各個位置", () => {
    const positions = new Set<number>();
    for (let seed = 0; seed < 60; seed++) {
      positions.add(displayOrder(seed, "level_up:2", 3).indexOf(2));
    }
    expect(positions).toEqual(new Set([0, 1, 2]));
  });

  it("不同組或不同種子順序可以不同", () => {
    const groups = new Set<string>();
    for (let level = 2; level < 30; level++) groups.add(displayOrder(7, `level_up:${level}`, 3).join());
    expect(groups.size).toBeGreaterThan(1);
  });

  it("offerGroupKey 隨升級或營火變動", () => {
    const up = runView(run({ kind: "level_up", level: 3, points: 2, offer: offer() }));
    const camp = runView(run({ kind: "campfire", after_battle: 3, rerolls_left: 0, offer: offer() }));
    expect(offerGroupKey(up)).toBe("level_up:3");
    expect(offerGroupKey(camp)).toBe("campfire:3:0");
  });
});

describe("屬性配點", () => {
  it("可以全部加在同一項，不能超過總點數，不能減到負數", () => {
    let a = adjustAllocation({}, "int", 1, 2);
    a = adjustAllocation(a, "int", 1, 2);
    expect(a).toEqual({ int: 2 });
    expect(adjustAllocation(a, "str", 1, 2)).toBe(a);
    expect(adjustAllocation({}, "str", -1, 2)).toEqual({});
    expect(allocationTotal(a)).toBe(2);
    expect(allocationComplete(a, 2)).toBe(true);
    expect(allocationComplete({ int: 1 }, 2)).toBe(false);
  });

  it("分到任兩項；送出時只含非 0 項", () => {
    const a = adjustAllocation(adjustAllocation({}, "dex", 1, 2), "wis", 1, 2);
    expect(cleanAllocation({ ...a, str: 0 })).toEqual({ dex: 1, wis: 1 });
  });
});

describe("技能欄位", () => {
  it("修正技能占被動欄位", () => {
    expect(slotOf(card("x", "modifier"))).toBe("passive");
    expect(slotOf(card("x", "stance"))).toBe("stance");
    expect(slotOf(card("x", "active"))).toBe("active");
  });

  it("主動滿 6 個要替換；被動含修正滿 3 個要替換；反應 1 個", () => {
    const six = Array.from({ length: 6 }, (_, i) => card(`a${i}`, "active"));
    expect(needsReplacement(six, card("n", "active"))).toBe(true);
    expect(needsReplacement(six.slice(1), card("n", "active"))).toBe(false);
    const passives = [card("p1", "passive"), card("p2", "passive"), card("m", "modifier")];
    expect(slotUsage(passives).passive).toBe(3);
    expect(needsReplacement(passives, card("n", "passive"))).toBe(true);
    expect(needsReplacement(passives, card("n", "active"))).toBe(false);
    expect(needsReplacement([card("r", "reaction")], card("n", "reaction"))).toBe(true);
  });

  it("替換清單預設只列同欄位；強制時列全部", () => {
    const skills = [card("a", "active"), card("p", "passive"), card("m", "modifier")];
    expect(replaceOptions(skills, card("n", "passive")).map((s) => s.id)).toEqual(["p", "m"]);
    expect(replaceOptions(skills, card("n", "passive"), true)).toHaveLength(3);
  });
});

describe("升級確定鈕與送出內容", () => {
  const full = Array.from({ length: 6 }, (_, i) => card(`a${i}`, "active"));
  const o = offer();

  it("配點沒配完不能確定；跳過可以", () => {
    const h = hero([card("a", "active")]);
    expect(levelUpReady(2, { int: 1 }, h, o, null, null)).toBe(false);
    expect(levelUpReady(2, { int: 2 }, h, o, null, null)).toBe(true);
  });

  it("欄位滿時要先選好換掉哪一個", () => {
    const h = hero(full);
    expect(levelUpReady(2, { int: 2 }, h, o, 0, null)).toBe(false);
    expect(levelUpReady(2, { int: 2 }, h, o, 0, "a3")).toBe(true);
    expect(pickReady(h, o, 0, null)).toBe(false);
    expect(pickReady(hero([card("a", "active")]), o, 0, null)).toBe(true);
    expect(pickReady(hero([card("a", "active")]), o, 0, null, true)).toBe(false); // 後端拒絕後強制選
  });

  it("pickChoice：升級帶配點，營火是 pick", () => {
    const up = runView(run({ kind: "level_up", level: 2, points: 2, offer: o }));
    expect(pickChoice(up, { int: 2, str: 0 }, 1, "a3")).toEqual({
      kind: "level_up",
      attributes: { int: 2 },
      pick: 1,
      replace: "a3",
    });
    const camp = runView(run({ kind: "campfire", after_battle: 3, rerolls_left: 0, offer: o }));
    expect(pickChoice(camp, {}, null, null)).toEqual({ kind: "pick", pick: null, replace: null });
  });
});

describe("存檔列表與目前的一輪", () => {
  it("saveLabel", () => {
    const base = { node: "battle", battles_done: 2, battles_total: 6, in_battle: true, level: 3 };
    expect(saveLabel(base)).toBe("2/6 場・Lv3・戰鬥中");
    expect(saveLabel({ ...base, in_battle: false, node: "campfire" })).toBe("2/6 場・Lv3・營火");
  });

  it("saveLabel：已結束標勝利或失敗", () => {
    const ended = { node: "ended", battles_done: 6, battles_total: 6, in_battle: false, level: 5 };
    expect(saveLabel({ ...ended, victory: true })).toBe("6/6 場・Lv5・已結束（勝利）");
    expect(saveLabel({ ...ended, victory: false })).toBe("6/6 場・Lv5・已結束（失敗）");
    expect(saveLabel(ended)).toBe("6/6 場・Lv5・已結束");
  });

  it("baseAttributes：六項都是基礎值（由 API 提供）", () => {
    expect(baseAttributes(10)).toEqual({ str: 10, dex: 10, con: 10, int: 10, wis: 10, wil: 10 });
  });

  it("localStorage 讀寫；壞掉或不能用時不丟錯", () => {
    const data = new Map<string, string>();
    const storage = {
      getItem: (k: string) => data.get(k) ?? null,
      setItem: (k: string, v: string) => void data.set(k, v),
      removeItem: (k: string) => void data.delete(k),
    };
    expect(readCurrentRun(storage)).toBeNull();
    writeCurrentRun("a1b2", storage);
    expect(data.get(CURRENT_RUN_KEY)).toBe("a1b2");
    expect(readCurrentRun(storage)).toBe("a1b2");
    writeCurrentRun(null, storage);
    expect(readCurrentRun(storage)).toBeNull();
    data.set(CURRENT_RUN_KEY, "../evil");
    expect(readCurrentRun(storage)).toBeNull();
    const broken = {
      getItem: () => {
        throw new Error("denied");
      },
      setItem: () => {
        throw new Error("denied");
      },
      removeItem: () => {
        throw new Error("denied");
      },
    };
    expect(readCurrentRun(broken)).toBeNull();
    expect(() => writeCurrentRun("x", broken)).not.toThrow();
    expect(() => writeCurrentRun(null, broken)).not.toThrow();
  });
});

describe("重新整理後回到一輪（Phase 3-6）", () => {
  const notFound = (e: unknown) => e instanceof Error && e.message === "404";

  it("伺服器有這一輪就直接用，不讀存檔（不丟步驟）", async () => {
    const calls: string[] = [];
    const got = await resumeRun(
      "r1",
      async (id) => (calls.push(`get:${id}`), "memory"),
      async (id) => (calls.push(`load:${id}`), "save"),
      notFound,
    );
    expect(got).toBe("memory");
    expect(calls).toEqual(["get:r1"]);
  });

  it("404 才讀存檔", async () => {
    const calls: string[] = [];
    const got = await resumeRun(
      "r1",
      async (id) => {
        calls.push(`get:${id}`);
        throw new Error("404");
      },
      async (id) => (calls.push(`load:${id}`), "save"),
      notFound,
    );
    expect(got).toBe("save");
    expect(calls).toEqual(["get:r1", "load:r1"]);
  });

  it("其他錯誤照樣丟出去，不讀存檔", async () => {
    let loaded = false;
    await expect(
      resumeRun(
        "r1",
        async () => {
          throw new Error("500");
        },
        async () => ((loaded = true), "save"),
        notFound,
      ),
    ).rejects.toThrow("500");
    expect(loaded).toBe(false);
  });

  it("狀態碼判斷與戰鬥紀錄還原條件", () => {
    expect(isNotFoundStatus(404)).toBe(true);
    expect(isNotFoundStatus(422)).toBe(false);
    expect(needsLogRestore({ steps: [] })).toBe(true); // 接續或讀檔：回應沒有步驟 → 取回紀錄
    expect(needsLogRestore({ steps: [{}] })).toBe(false); // 新戰鬥：開場的步驟已在回應裡
  });
});
