// Phase 6C-7：字幕淡出與「多講一點」、對話框分段、選項圖示、骰子動畫的結束狀態與顏色、NPC 外觀映射（頭像 → 地圖紙娃娃）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { FieldView, NpcPortrait, WorldEventView, WorldSituationResult, WorldStory } from "../api/types";
import { EventCard, SituationResultCard } from "./EventCard";
import { fieldDrawModel, npcUnitId } from "./fieldModel";
import {
  attrKeys,
  canMore,
  dialogMore,
  dialogNext,
  dialogStart,
  diceFrame,
  DICE_MS,
  hasNext,
  OUTCOME_COLOR,
  sentences,
  solutionIcon,
  solutionLine,
  storyPages,
  subtitleHasMore,
  subtitleLine,
  subtitlePhase,
  SUBTITLE_FADE_MS,
  SUBTITLE_MS,
  usedDie,
} from "./narration";
import { NarratorSubtitle, StoryDialog, DiceRoll } from "./StoryParts";
import { EXTRA_HEAD, FOX_WHITE, npcFieldLook, portraitDollLook, portraitGear, portraitRaceLook } from "./npcLook";

const html = (el: ReturnType<typeof createElement>): string => renderToStaticMarkup(el);

function story(text: string, more = "", source: WorldStory["source"] = "llm"): WorldStory {
  return { text_zh: text, more_zh: more, source };
}

const LONG = "霧從河面爬上來。渡口的燈籠一盞盞熄了。有人在對岸喊你的名字。聲音很熟，卻想不起是誰。";

describe("字幕（21.7：上方一行，幾秒後淡出；多講一點）", () => {
  it("只取第一句，太長截斷", () => {
    expect(subtitleLine(LONG)).toBe("霧從河面爬上來。");
    expect(subtitleLine("一".repeat(60))).toBe(`${"一".repeat(40)}……`);
  });

  it("時間到淡出、淡出完消失；展開時一直顯示", () => {
    expect(subtitlePhase(0, false)).toBe("show");
    expect(subtitlePhase(SUBTITLE_MS - 1, false)).toBe("show");
    expect(subtitlePhase(SUBTITLE_MS, false)).toBe("fade");
    expect(subtitlePhase(SUBTITLE_MS + SUBTITLE_FADE_MS, false)).toBe("gone");
    expect(subtitlePhase(SUBTITLE_MS * 10, true)).toBe("show");
  });

  it("一行講不完或有補充才給「多講一點」", () => {
    expect(subtitleHasMore(story(LONG))).toBe(true);
    expect(subtitleHasMore(story("霧散了。"))).toBe(false);
    expect(subtitleHasMore(story("霧散了。", "對岸有人影。"))).toBe(true);
  });

  it("元件：一行字＋「多講一點」；淡出中標 fade；過了時間不輸出", () => {
    const shown = html(createElement(NarratorSubtitle, { story: story(LONG), elapsed: 0 }));
    expect(shown).toContain('data-phase="show"');
    expect(shown).toContain("霧從河面爬上來。");
    expect(shown).not.toContain("渡口的燈籠");
    expect(shown).toContain("多講一點");
    expect(html(createElement(NarratorSubtitle, { story: story(LONG), elapsed: SUBTITLE_MS + 1 }))).toContain('data-phase="fade"');
    expect(html(createElement(NarratorSubtitle, { story: story(LONG), elapsed: SUBTITLE_MS + SUBTITLE_FADE_MS }))).toBe("");
  });

  it("降級文字是角落的小圖示，不寫「（模板文字）」", () => {
    const out = html(createElement(NarratorSubtitle, { story: story("霧散了。", "", "fallback"), elapsed: 0 }));
    expect(out).toContain('data-icon="model_off"');
    expect(out).not.toContain("（模板文字）");
  });
});

describe("對話框（一次一段，按一下下一段）", () => {
  it("切句保留標點與引號", () => {
    expect(sentences("「走吧。」她說。好！")).toEqual(["「走吧。」", "她說。", "好！"]);
    expect(sentences("  ")).toEqual([]);
  });

  it("每段最多 2 句、不超過 48 字", () => {
    const pages = storyPages(LONG);
    expect(pages).toEqual(["霧從河面爬上來。渡口的燈籠一盞盞熄了。", "有人在對岸喊你的名字。聲音很熟，卻想不起是誰。"]);
    const long = storyPages(`${"長".repeat(40)}。${"句".repeat(20)}。`);
    expect(long).toHaveLength(2);
  });

  it("按一下播下一段，最後一段不動；有補充時接上「多講一點」", () => {
    const s = story(LONG, "對岸的人影舉起了燈。");
    let st = dialogStart(s);
    expect(st.index).toBe(0);
    expect(hasNext(st)).toBe(true);
    expect(canMore(st, s)).toBe(false);
    st = dialogNext(st);
    expect(st.index).toBe(1);
    expect(hasNext(st)).toBe(false);
    expect(dialogNext(st)).toBe(st);
    expect(canMore(st, s)).toBe(true);
    st = dialogMore(st, s);
    expect(st.pages[st.index]).toBe("對岸的人影舉起了燈。");
    expect(canMore(st, s)).toBe(false);
  });

  it("元件：先只顯示第一段、有「▼」，沒有「多講一點」", () => {
    const out = html(createElement(StoryDialog, { story: story(LONG, "補充。"), speaker: "說書人", portrait: null }));
    expect(out).toContain("霧從河面爬上來。渡口的燈籠一盞盞熄了。");
    expect(out).not.toContain("有人在對岸");
    expect(out).toContain('data-pages="2"');
    expect(out).toContain("▼");
    expect(out).not.toContain("多講一點");
    expect(out).toContain('data-portrait="silhouette"');
  });
});

function sol(kind: string, note = "", attrs = "", extra: Partial<WorldEventView["solutions"][number]> = {}): WorldEventView["solutions"][number] {
  return { index: 0, kind, kind_zh: { combat: "戰鬥", parley: "交涉", abandon: "放棄", opportunity: "機遇", situation: "情境判定" }[kind] ?? kind, note_zh: note, hint_zh: "", attributes_zh: attrs, template: kind === "situation" ? "t" : null, available: true, cost_supplies: 0, can_pay: true, ...extra };
}

describe("選項圖示（戰鬥、說服、潛行、調查……）", () => {
  it.each([
    [sol("combat"), "combat"],
    [sol("parley"), "trade"],
    [sol("opportunity"), "chance"],
    [sol("abandon"), "leave"],
    [sol("situation", "說服守衛放行", "意志"), "persuade"],
    [sol("situation", "趁夜潛過哨站", "敏捷"), "sneak"],
    [sol("situation", "查看腳印", "感知"), "investigate"],
    [sol("situation", "撞開木門", "力量"), "force"],
    [sol("situation", "想辦法過去", "敏捷、力量"), "sneak"],
    [sol("situation", "想辦法過去", ""), "investigate"],
  ] as const)("%# → %s", (s, icon) => {
    expect(solutionIcon(s)).toBe(icon);
  });

  it("按鈕只留一行字：情境、交涉用說明，戰鬥、放棄用種類名", () => {
    expect(solutionLine(sol("situation", "找安全路", "感知"))).toBe("找安全路");
    expect(solutionLine(sol("combat", "和他們打一場"))).toBe("戰鬥");
    expect(solutionLine(sol("abandon", "不管了"))).toBe("放棄");
  });

  it("屬性名 → 圖示鍵（不認得的略過）", () => {
    expect(attrKeys("感知、力量")).toEqual(["wis", "str"]);
    expect(attrKeys("運氣")).toEqual([]);
  });

  it("事件卡：插圖色塊＋選項圖示，文字一行，整句收進說明", () => {
    const event: WorldEventView = {
      skeleton: "lost_caravan",
      location_name_zh: "霧渡鎮",
      actor_zh: "迷路的商隊",
      motive_zh: "想找路回去",
      story: story(LONG),
      who_zh: "",
      want_zh: "",
      obstacle_zh: "",
      stakes_zh: "",
      solutions: [sol("situation", "找安全路", "感知、力量"), { ...sol("combat"), index: 1 }, { ...sol("parley", "給點補給", "", { cost_supplies: 2 }), index: 2 }, { ...sol("abandon"), index: 3 }],
      leave_zh: "離開這裡，事件就作罷",
      art_url: null,
    };
    const out = html(createElement(EventCard, { event, busy: false, onOpen: () => undefined, onSolve: () => undefined, onAnswer: () => undefined }));
    expect(out).toContain('data-art="scene"');
    expect(out).toContain('data-icon="investigate"');
    expect(out).toContain('data-icon="combat"');
    expect(out).toContain('data-icon="trade"');
    expect(out).toContain('data-icon="leave"');
    expect(out).toContain("−2 補給");
    expect(out).not.toContain("（感知、力量）");
    expect(out).toContain('data-testid="world-event-story"');
    expect(out).not.toContain("有人在對岸");
  });
});

function result(over: Partial<WorldSituationResult> = {}): WorldSituationResult {
  return {
    template: "t",
    note_zh: "找安全路",
    attribute_zh: "感知",
    method_zh: "觀察",
    dice: [3, 15],
    mode_zh: "優勢",
    roll: 15,
    attribute_mod: 2,
    care: [{ item_zh: "線索", text_zh: "河邊的腳印", counted: true, reason_zh: "" }],
    care_bonus: 1,
    race_bonus: 0,
    total: 18,
    base_dc: 13,
    dc_shift: 0,
    dc: 13,
    outcome: "success",
    outcome_zh: "成功",
    effects_zh: ["經驗 +10"],
    story: story("你找到了一條小路。路旁有新鮮的腳印。"),
    source: "llm",
    ...over,
  };
}

describe("擲骰（兩顆骰的動畫＋成功失敗的顏色）", () => {
  it("用的是哪一顆：一般取第一顆，優勢劣勢取和結果相同的那顆", () => {
    expect(usedDie([3, 15], 3)).toBe(0);
    expect(usedDie([3, 15], 15)).toBe(1);
    expect(usedDie([7, 7], 7)).toBe(0);
  });

  it("動畫中換面、不標用哪顆；結束時是真的點數", () => {
    const mid = diceFrame([3, 15], 15, 100);
    expect(mid.done).toBe(false);
    expect(mid.used).toBeNull();
    for (const f of mid.faces) expect(f >= 1 && f <= 20).toBe(true);
    expect(diceFrame([3, 15], 15, 100)).toEqual(mid); // 確定性
    expect(diceFrame([3, 15], 15, DICE_MS)).toEqual({ faces: [3, 15], done: true, used: 1 });
  });

  it("元件結束狀態：用的那顆塗結果色（成功綠、勉強黃、失敗紅）", () => {
    for (const outcome of ["success", "partial", "failure"] as const) {
      const out = html(createElement(DiceRoll, { dice: [3, 15], roll: 15, outcome, elapsed: DICE_MS }));
      expect(out).toContain('data-done="1"');
      expect(out).toContain(`data-outcome="${outcome}"`);
      expect(out).toContain(`data-color="${OUTCOME_COLOR[outcome]}"`);
      expect(out).toContain('data-face="3"');
      expect(out).toContain('data-face="15"');
    }
    expect(OUTCOME_COLOR.success).not.toBe(OUTCOME_COLOR.failure);
  });

  it("結果卡：骰子、總和對 DC、算式與「兩顆骰」收進說明、敘述改成字幕、模型關閉是角落圖示", () => {
    const out = html(createElement(SituationResultCard, { result: result({ source: "fallback" }), onClose: () => undefined, diceElapsed: DICE_MS }));
    expect(out).toContain('data-testid="world-dice"');
    expect(out).toContain('data-testid="world-result-story"');
    expect(out).toContain("你找到了一條小路。");
    expect(out).not.toContain("兩顆骰：");
    expect(out).not.toContain("（模型關閉：照預設提議）");
    expect(out).toContain('data-testid="world-result-fallback"');
    expect(out).toContain('data-attr="wis"');
    expect(html(createElement(SituationResultCard, { result: result(), onClose: () => undefined }))).not.toContain("world-result-fallback");
  });
});

const GRANNY: NpcPortrait = {
  look: { skin: "#e8c8a8", hair: "bun", hair_color: "#c8c8c0", bun_band: "#b8432f", beard: false },
  gear: { body: { kind: "robe", color: "#3c4a48", trim: "#e8bb48" } },
  extras: ["wrinkles"],
};

describe("NPC 外觀映射（NPC頭像.md 第 4 節第 5 項）", () => {
  it("look 與 gear 照搬，補材質", () => {
    const d = portraitDollLook(GRANNY, true) as unknown as Record<string, unknown>;
    expect(d["skin"]).toBe("#e8c8a8");
    expect(d["hair"]).toBe("bun");
    expect(d["bun_band"]).toBe("#b8432f");
    expect((d["gear"] as Record<string, unknown>)["body"]).toEqual({ kind: "robe", material: "cloth", color: "#3c4a48", trim: "#e8bb48" });
    expect((d["gear"] as Record<string, unknown>)["head"]).toBeUndefined(); // wrinkles 不畫
  });

  it.each([
    ["cap", { kind: "cap", material: "leather", color: "#3a2a1a" }],
    ["wide_hat", { kind: "douli", material: "cloth" }],
    ["bandana", { kind: "bandana", material: "cloth", color: "#a83a2a" }],
    ["headband", { kind: "headband", material: "cloth" }],
    ["goggles", { kind: "goggles", material: "iron" }],
    ["goggles_up", { kind: "goggles_up", material: "iron" }],
  ] as const)("配件 %s → 頭部裝備（QK-8：斗笠、頭帶、護目鏡是 Q 版頭部部件）", (extra, head) => {
    expect(EXTRA_HEAD[extra]).toEqual(head);
    expect(portraitGear({ ...GRANNY, extras: ["scar", extra] }, true)["head"]).toEqual(head);
  });

  it("只畫在頭像上的配件不換；gear.head 已經有值以它為準（護目鏡改成帽子的形制）；頭像自己畫配件時不換", () => {
    for (const e of ["fur_collar", "apron_cross", "scar", "mustache", "ember_eye", "rune", "mist", "soot", "earring"]) {
      expect(portraitGear({ ...GRANNY, extras: [e] }, true)["head"]).toBeUndefined();
    }
    const hooded: NpcPortrait = { ...GRANNY, gear: { head: { kind: "hood", color: "#5a4e44" } }, extras: ["cap"] };
    expect(portraitGear(hooded, true)["head"]).toEqual({ kind: "hood", material: "cloth", color: "#5a4e44" });
    expect(portraitGear({ ...GRANNY, extras: ["cap"] }, false)["head"]).toBeUndefined();
    // 老鐵：帽＋護目鏡（照配件順序）→ 帽子帶 form goggles；毛領 → 頸飾
    const laotie = portraitGear({ ...GRANNY, extras: ["cap", "goggles", "fur_collar"] }, true);
    expect(laotie["head"]).toEqual({ kind: "cap", material: "leather", color: "#3a2a1a", form: "goggles" });
    expect(laotie["neck"]).toEqual({ kind: "fur_collar", material: "fur" });
  });

  it("QK-8：頭像的手持物 → 主手造型覆寫（含元素）；霧氣配件 → 全身特徵 mist", () => {
    const helin: NpcPortrait = { ...GRANNY, gear: { main_hand: { kind: "staff", material: "wood", element: "fire" } }, extras: ["mist"] } as NpcPortrait;
    const d = portraitDollLook(helin, true) as unknown as Record<string, unknown>;
    expect([d["main_kind"], d["main_material"], d["main_element"]]).toEqual(["staff", "wood", "fire"]);
    expect((d["gear"] as Record<string, unknown>)["main_hand"]).toBeUndefined();
    expect(d["traits"]).toEqual(["mist"]);
    expect((portraitDollLook(helin, false) as unknown as Record<string, unknown>)["traits"]).toEqual([]);
  });

  it("種族部件（角、耳、紋路）照搬給紙娃娃", () => {
    const helin: NpcPortrait = { look: { skin: "#b07a7a", hair: "long", horns: "curved", horn_color: "#bfb0a4", beard: false }, gear: {}, extras: ["rune"] };
    expect(portraitRaceLook(helin)).toEqual({ horns: "curved", horn_color: "#bfb0a4" });
    expect(portraitRaceLook(GRANNY)).toBeNull();
  });

  it("霜音：白色犬骨架，不用紙娃娃", () => {
    const fox: NpcPortrait = { look: null, gear: {}, extras: ["fox"] };
    const d = portraitDollLook(fox, true) as unknown as { creature: { body: string; tint: string } };
    expect(d.creature.body).toBe("hound");
    expect(d.creature.tint).toBe(FOX_WHITE);
  });

  it("伺服器有 look 用 look；沒有用頭像；都沒有用預設", () => {
    const own = { template_id: "x", weapon_id: "unarmed", weapon_class: "melee", doll_look: null, race_look: null, equipment: [] };
    expect(npcFieldLook({ id: "a", look: own, portrait: GRANNY })).toBe(own);
    expect(npcFieldLook({ id: "a", look: null, portrait: GRANNY })?.template_id).toBe("npc_a");
    expect(npcFieldLook({ id: "a", look: null, portrait: null })).toBeNull();
  });

  it("地圖：NPC 的紙娃娃與種族外觀來自頭像", () => {
    const tiles = Array.from({ length: 4 }, (_, i) => ({ x: i % 2, y: Math.floor(i / 2), height: 0, terrain: "stone", surface: "none", walkable: true }));
    const helin: NpcPortrait = { look: { skin: "#b07a7a", hair: "long", horns: "curved", horn_color: "#bfb0a4", beard: false }, gear: {}, extras: [] };
    const field = {
      map_id: "m",
      name_zh: "m",
      region: "ashen_waste",
      location: "m",
      interior: false,
      width: 2,
      height: 2,
      tiles,
      objects: [],
      exits: [],
      doors: [],
      stones: [],
      npcs: [{ id: "priestess_helin", name_zh: "赫琳", x: 1, y: 0, rank: "neutral", rank_zh: "中立", alert: null, portrait: helin }],
      facilities: [],
      me: { x: 0, y: 1, facing: "e" },
      max_climb: 1,
      hero: null,
      stone_targets: [],
      enemies: [],
      friends: [],
      campfires: [],
      situation_objects: [],
      sneaking: false,
      sneak_cost: 1,
      footprints: [],
    } as unknown as FieldView;
    const u = fieldDrawModel(field).units.find((x) => x.id === npcUnitId("priestess_helin"))!;
    expect((u.dollLook as unknown as { skin: string }).skin).toBe("#b07a7a");
    expect(u.raceLook).toEqual({ horns: "curved", horn_color: "#bfb0a4" });
  });
});
