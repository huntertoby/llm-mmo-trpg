// 工坊靶場（TR-1，#134；OB-5，#150）：武器架分組、「看示範」送的關鍵字、本機草稿、模式切換（選大類／正式選定／重選）、
// 選大類的三張卡與確認列、正式選定的「推薦」小牌與黏底列、定稿的字、接線（選大類送 `opening_class`、正式選定送 `opening_confirm`）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { parse } from "yaml";
import type { RangeView, SkillCard, StartWeaponOption, WorldView } from "../api/types";
import newcomerYaml from "../../../content/world/newcomer.yaml?raw";
import { readFile, SRC_DIR } from "../test/sourceScan";
import cards from "../ui/fixtures/skillCards.json";
import {
  CHOOSE_LABEL,
  CHOOSE_LATER,
  CLASS_LABELS,
  CLASS_PLAQUE_SUB,
  CONFIRM_EMPTY,
  LOAN_NOTE,
  RACK_NOTE,
  REC_NOTE,
  RESELECT_LABEL,
  RESELECT_LATER,
  RESELECT_ONCE,
  RESELECT_OPEN_LABEL,
  SANDBOX_NOTE,
  opensReselect,
  reselectBadge,
  reselectBadgeHint,
  reselectConfirmLines,
  reselectPlaqueSub,
  chooseBarParts,
  CHOOSE_AUTO_SEEN,
  chooseAutoOpens,
  choosePageShown,
  holdOffer,
  choosePlaqueSub,
  confirmParts,
  costLine,
  demoKeywords,
  groupRacks,
  keywordState,
  opensChoose,
  rangeMode,
  rangePlaceName,
  readClassDraft,
  readDraft,
  trialNote,
  writeClassDraft,
  writeDraft,
} from "./range";
import { RangeClassPick } from "./RangeClassPick";
import { speakerPortraitSize } from "./RangeParts";
import { CONFIRM_LABEL, RangeDoneDialog, RangeScreen, ReselectConfirmDialog, chooseDoneLines, rangeDoneLines, reselectDoneLines } from "./RangeScreen";
import { ReselectEntry, allocateClosingLines } from "./ReselectEntry";

const weapon = (id: string, cls: string): StartWeaponOption => ({ id, name_zh: id, weapon_class: cls, traits_zh: [], hp: 30, mana: 10 });

/** 真實的技能卡（`ui/fixtures/skillCards.json`）改個名字當入門招：測試不寫死哪幾招是入門招。 */
const REAL = Object.values(cards as unknown as Record<string, SkillCard>);
const card = (i: number, id: string, name: string): SkillCard => ({ ...(REAL[i % REAL.length] as SkillCard), id, name_zh: name });

const KEEPER = { name_zh: "守印人", portrait: null, region: "capital" };
const RANGE: RangeView = {
  seed: 7,
  stage: "pick_class",
  weapon_class: null,
  recommended_keywords: [],
  racks: [
    { weapon_class: "melee", name_zh: "近戰", skills: [card(0, "m1", "甲招"), card(1, "m2", "乙招")], starter_weapon: "one_handed_sword", starter_weapon_zh: "單手劍", blurbs_zh: { m1: "甲招的一句說明。", m2: "乙招的一句說明。" } },
    { weapon_class: "ranged", name_zh: "遠程", skills: [card(2, "r1", "丙招"), card(3, "r2", "丁招")], starter_weapon: "bow", starter_weapon_zh: "弓", blurbs_zh: { r1: "丙招的一句說明。" } },
    { weapon_class: "focus", name_zh: "法器", skills: [card(4, "f1", "戊招"), card(5, "f2", "己招")], starter_weapon: "fire_staff", starter_weapon_zh: "火焰法杖" },
  ],
  dummies: [{ label_zh: "會動的木樁" }, { label_zh: "站在水上的木樁" }, { label_zh: "普通的木樁" }],
  intro: [{ speaker_zh: "守印人", text_zh: "這裡是工坊靶場。" }],
  done: [{ speaker_zh: "守印人", text_zh: "去霧渡鎮找渡婆婆。" }],
  loan: [{ speaker_zh: "守印人", text_zh: "手上這套是借你的。" }],
  keeper: KEEPER,
  capital_zh: "樞島",
};

const CHOICE: NonNullable<RangeView["choice"]> = {
  available: true,
  blocked_zh: null,
  in_capital: false,
  place_zh: "霧渡鎮導師堂",
  speaker: { name_zh: "葛蘭", portrait: null, region: "cloud_ridge" },
  lines: [
    { speaker_zh: "葛蘭", text_zh: "該挑你自己的兵器了。" },
    { speaker_zh: "葛蘭", text_zh: "我標了適合你的。" },
  ],
  done: [{ speaker_zh: "葛蘭", text_zh: "借你的那套我收回了。" }],
  npc: "gran",
  objects: ["training_range", "workshop_master"],
};
const STARTER: RangeView = { ...RANGE, stage: "starter", weapon_class: "ranged", recommended_keywords: ["poisoned", "ignite"], choice: CHOICE };

/** OB-6：正式選定之後、在霧渡鎮、還能重選（文字是伺服器給的樣子，測試裡的字只是佔位）。 */
const RESELECT: NonNullable<RangeView["reselect"]> = {
  available: true,
  blocked_zh: null,
  used: false,
  before_level: 4,
  weapon: "greatsword",
  keywords: ["prone", "ignite"],
  returned_zh: ["甲招", "乙招", "丙招"],
  weapon_returned: true,
  lost_zh: ["雙手劍的強化 +2（材料不退）"],
  window_open: true,
  place_zh: "重選要回霧渡鎮找葛蘭，或到樞島的工坊靶場",
  in_capital: false,
  here_zh: "霧渡鎮導師堂",
  speaker: { name_zh: "葛蘭", portrait: null, region: "cloud_ridge" },
  lines: [{ speaker_zh: "葛蘭", text_zh: "想換？" }],
  done: [{ speaker_zh: "葛蘭", text_zh: "換好了。" }],
  npc: "gran",
  objects: ["training_range", "workshop_master"],
};
const CHOSEN: RangeView = { ...RANGE, stage: "chosen", weapon_class: "melee", reselect: RESELECT };

const VIEW = { character: { character_id: "c1", name: "小靶", race: "human", look: null } } as unknown as WorldView;
const noop = (): void => undefined;

function memoryStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    clear: () => map.clear(),
    getItem: (k) => map.get(k) ?? null,
    key: (i) => [...map.keys()][i] ?? null,
    removeItem: (k) => void map.delete(k),
    setItem: (k, v) => void map.set(k, v),
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("TR-1 靶場的畫面邏輯", () => {
  it("武器架照伺服器的大類順序分組（近戰、遠程、法器）", () => {
    const racks = groupRacks([weapon("bow", "ranged"), weapon("dagger", "melee"), weapon("fire_staff", "focus"), weapon("axe", "melee")], ["melee", "ranged", "focus"]);
    expect(racks.map((r) => r.name)).toEqual(["近戰", "遠程", "法器"]);
    expect(racks[0]?.weapons.map((w) => w.id)).toEqual(["dagger", "axe"]);
    expect(CLASS_LABELS.focus).toBe("法器");
  });

  it("看示範：已選的看那組；沒選的接在後面；選滿了換掉第 2 個", () => {
    expect(demoKeywords([], "burning", 2)).toEqual(["burning"]);
    expect(demoKeywords(["burning"], "charged", 2)).toEqual(["burning", "charged"]);
    expect(demoKeywords(["burning", "charged"], "charged", 2)).toEqual(["burning", "charged"]);
    expect(demoKeywords(["burning", "charged"], "frozen", 2)).toEqual(["burning", "frozen"]);
  });

  it("草稿存在本機（中途離開回來接著選）；讀不到或壞掉時 null", () => {
    vi.stubGlobal("window", { localStorage: memoryStorage() });
    expect(readDraft("c1")).toBeNull();
    writeDraft("c1", { weapon: "bow", keywords: ["burning"] });
    expect(readDraft("c1")).toEqual({ weapon: "bow", keywords: ["burning"] });
    writeDraft("c1", null);
    expect(readDraft("c1")).toBeNull();
    window.localStorage.setItem("trpg.rangeDraft.c2", "{oops");
    expect(readDraft("c2")).toBeNull();
    vi.stubGlobal("window", {});
    expect(readDraft("c1")).toBeNull(); // 沒有 localStorage（封鎖儲存）也不壞
    expect(() => writeDraft("c1", { weapon: "bow", keywords: [] })).not.toThrow();
  });

  it("選大類的草稿（去試打回來接著選）：大類、武器架開關、架上點的武器", () => {
    vi.stubGlobal("window", { localStorage: memoryStorage() });
    expect(readClassDraft("c1")).toBeNull();
    writeClassDraft("c1", { picked: "ranged", rackOpen: true, rackWeapon: "crossbow" });
    expect(readClassDraft("c1")).toEqual({ picked: "ranged", rackOpen: true, rackWeapon: "crossbow" });
    window.localStorage.setItem("trpg.rangeClassDraft.c2", JSON.stringify({ picked: 3, rackOpen: "yes" }));
    expect(readClassDraft("c2")).toEqual({ picked: null, rackOpen: false, rackWeapon: "" });
    writeClassDraft("c1", null);
    expect(readClassDraft("c1")).toBeNull();
  });

  it("內容檔有靶場：三大類各 2 招示範招與一句說明、3 個木樁、守印人與葛蘭的話（OB-5 定稿）", () => {
    const data = parse(newcomerYaml) as {
      range: { racks: string[]; demos: Record<string, string[]>; demo_blurbs: Record<string, string>; dummies: unknown[]; intro: { text_zh: string }[]; done: { text_zh: string }[]; loan: unknown[]; choose: unknown[]; choose_capital: unknown[]; choose_done: unknown[]; choose_capital_done: { speaker_zh: string; text_zh: string }[] };
    };
    expect(data.range.racks).toEqual(["melee", "ranged", "focus"]);
    for (const cls of data.range.racks) {
      expect(data.range.demos[cls]).toHaveLength(2);
      for (const id of data.range.demos[cls] ?? []) expect(data.range.demo_blurbs[id]).toBeTruthy();
    }
    expect(data.range.dummies).toHaveLength(3);
    expect(data.range.intro[1]?.text_zh).toContain("先挑一條路");
    expect(data.range.done[0]?.text_zh).toContain("先走這條路試試");
    expect(data.range.loan).toHaveLength(1);
    expect(data.range.choose).toHaveLength(2);
    expect(data.range.choose_capital).toHaveLength(1);
    expect(data.range.choose_done).toHaveLength(1);
    expect(data.range.choose_capital_done).toEqual([{ speaker_zh: "守印人", text_zh: "挑好了。借你的那套我收走，渡口和竹林欠你的，現在一起補上。" }]);
  });
});

describe("OB-5 模式與字", () => {
  it("模式：選大類中＝class；入門期能選定才是 choose；選定後能重選＝reselect（OB-6 才畫，且不自動開）", () => {
    expect(rangeMode(null)).toBeNull();
    expect(rangeMode(RANGE)).toBe("class");
    expect(rangeMode(STARTER)).toBe("choose");
    expect(rangeMode({ ...STARTER, choice: { ...CHOICE, available: false, blocked_zh: "還不能正式選定" } })).toBeNull();
    expect(rangeMode({ ...RANGE, stage: "starter", weapon_class: "melee" })).toBeNull();
    expect(rangeMode(CHOSEN)).toBe("reselect");
    expect(rangeMode({ ...CHOSEN, reselect: { ...RESELECT, available: false } })).toBeNull();
    // OB-6：重選頁畫出來了（沿用正式選定整頁；不標推薦）
    const html = renderToStaticMarkup(createElement(RangeScreen, { ...screenProps(CHOSEN), mode: "reselect" }));
    expect(html).toContain("重選");
    expect(html).toContain(RESELECT_LABEL);
    expect(html).toContain(RESELECT_LATER);
    expect(html).not.toContain("range-rec");
    expect(html).not.toContain(REC_NOTE);
  });

  it("「正式選定」整頁的開關：到了就開、按「之後再選」關掉、點葛蘭或主城靶場再打開", () => {
    const none = new Set<string>();
    const seen = new Set([CHOOSE_AUTO_SEEN]);
    // OB-5b：自動打開只有第一次（沒有紀錄時）；開過、按過「之後再選」都不再自動開
    expect(chooseAutoOpens("auto", true, none)).toBe(true);
    expect(chooseAutoOpens("auto", false, none)).toBe(false);
    expect(chooseAutoOpens("auto", true, seen)).toBe(false);
    expect(chooseAutoOpens("closed", true, none)).toBe(false);
    expect(choosePageShown("auto")).toBe(false);
    expect(choosePageShown("closed")).toBe(false);
    expect(choosePageShown("open")).toBe(true);
    // 美術 M5：彈窗開著時三選一先不出
    expect(holdOffer("offer", true, null)).toBeNull();
    expect(holdOffer("offer", false, null)).toBe("offer");
    expect(holdOffer("bag", true, "map")).toBe("bag");
    expect(opensChoose(CHOICE, { npc: "gran" })).toBe(true);
    expect(opensChoose(CHOICE, { npc: "granny_du" })).toBe(false);
    expect(opensChoose(CHOICE, { object: "training_range" })).toBe(false); // 人在霧渡鎮：主城的物件不算
    const capital = { ...CHOICE, in_capital: true };
    expect(opensChoose(capital, { object: "workshop_master" })).toBe(true);
    expect(opensChoose(capital, { npc: "gran" })).toBe(false);
    expect(opensChoose({ ...capital, available: false }, { object: "workshop_master" })).toBe(false);
    expect(opensChoose(undefined, { npc: "gran" })).toBe(false);
  });

  it("地名讀伺服器給的主城地名，不寫死「主城」", () => {
    expect(CLASS_PLAQUE_SUB).toBe("先挑一條路");
    expect(choosePlaqueSub("霧渡鎮導師堂", 2)).toBe("霧渡鎮導師堂・選你自己的武器與 2 個關鍵字");
    expect(choosePlaqueSub("樞島工坊靶場", 2)).toBe("樞島工坊靶場・選你自己的武器與 2 個關鍵字");
    expect(rangePlaceName("樞島")).toBe("樞島・工坊靶場");
    expect(rangePlaceName("")).toBe("工坊靶場");
    for (const file of ["world/RangeScreen.tsx", "world/RangeClassPick.tsx", "world/RangeParts.tsx", "world/range.ts"]) expect(readFile(SRC_DIR, file)).not.toMatch(/["'`>]主城/); // 字串與 JSX 文字裡沒有（註解不算）
    expect(readFile(SRC_DIR, "screens/WorldScreen.tsx")).not.toContain("主城・工坊靶場");
  });

  it("定稿的字：沙盒說明、武器卡、確認列、黏底列", () => {
    expect(SANDBOX_NOTE).toBe("靶場是沙盒：不算勝負，不耗任何資源，也沒有經驗與掉落。");
    const skills = RANGE.racks[1]?.skills ?? [];
    expect(trialNote("遠程", skills, true)).toBe("試打用：普攻＋遠程入門招 丙招、丁招。試別把武器不會改掉你選的大類。");
    expect(trialNote("遠程", skills, false)).toBe("試打用：普攻＋遠程示範招 丙招、丁招（測試模式，不耗任何資源）。");
    expect(confirmParts("遠程", "弓", skills)).toEqual(["已選：遠程", "弓＋丙招、丁招。"]);
    expect(chooseBarParts("弓", ["點燃", "撞擊"], 2)).toEqual(["手上：弓", "已選 2/2：點燃、撞擊"]);
    expect(chooseBarParts("弓", [], 2)).toEqual(["手上：弓", "已選 0/2"]);
  });

  it("代價一行不寫冷卻與每場次數", () => {
    const base = REAL[0] as SkillCard;
    const costs = [
      { index: 0, kind: "ap" as const, value: 2, unit: "AP", label: "2" },
      { index: 1, kind: "stamina" as const, value: 10, unit: "耐力", label: "10" },
      { index: 2, kind: "cooldown" as const, value: 3, unit: "回合", label: "3" },
      { index: 3, kind: "uses_per_battle" as const, value: 1, unit: "次", label: "1" },
    ];
    expect(costLine({ ...base, stats: { ...base.stats, costs } })).toBe("AP 2・耐力 10");
  });

  it("關鍵字四種狀態：推薦且已選、推薦未選、已選非推薦、一般", () => {
    expect(keywordState(true, true)).toBe("rec-sel");
    expect(keywordState(false, true)).toBe("rec");
    expect(keywordState(true, false)).toBe("sel");
    expect(keywordState(false, false)).toBe("plain");
  });

  it("頭像：手機寬 48，其餘 64", () => {
    expect(speakerPortraitSize(390)).toBe(48);
    expect(speakerPortraitSize(1280)).toBe(64);
    expect(speakerPortraitSize(null)).toBe(64);
  });
});

function screenProps(range: RangeView) {
  return { view: VIEW, range, mode: "class" as const, busy: false, error: null, onCloseError: noop, onTrial: noop, onClass: noop, onConfirm: noop, onHome: noop, onLater: noop };
}

describe("OB-5 選大類畫面", () => {
  const html = renderToStaticMarkup(createElement(RangeScreen, screenProps(RANGE)));

  it("標題牌、守印人的話與頭像、沙盒說明", () => {
    expect(html).toContain("工坊靶場");
    expect(html).toContain(CLASS_PLAQUE_SUB);
    expect(html).toContain("這裡是工坊靶場。");
    expect(html).toContain(SANDBOX_NOTE);
    expect(html).toMatch(/data-testid="range-speaker-portrait"[^>]*data-speaker="守印人"/);
    expect(html).not.toContain("手上這套是借你的。"); // 選了才說
  });

  it("三張大類卡：入門武器、2 招入門招（名字、一句說明、代價）都是伺服器給的；有「借」小牌與卡底兩顆鈕", () => {
    for (const rack of RANGE.racks) {
      expect(html).toContain(`data-testid="range-class-${rack.weapon_class}"`);
      expect(html).toContain(rack.starter_weapon_zh);
      for (const s of rack.skills) {
        expect(html).toContain(s.name_zh);
        const blurb = rack.blurbs_zh?.[s.id];
        if (blurb !== undefined) expect(html).toContain(blurb);
      }
    }
    expect(html.match(/data-testid="range-class-skill"/g)).toHaveLength(6);
    expect(html.match(/class="ob-loan"/g)).toHaveLength(6);
    expect(html.match(new RegExp(LOAN_NOTE, "g"))).toHaveLength(3);
    expect(html.match(/>選這條路</g)).toHaveLength(3);
    expect(html.match(/>拿起試打</g)).toHaveLength(3);
    expect(html).not.toContain("已選這條路");
  });

  it("武器架收著：一列說明與「試其他武器」；畫面上不寫武器數量", () => {
    expect(html).toContain(RACK_NOTE);
    expect(html).toMatch(/data-testid="range-rack-toggle"[^>]*>試其他武器</);
    expect(html).not.toContain('data-testid="range-racks"');
    expect(html).not.toMatch(/\d+ 把/);
  });

  it("確認列：還沒選＝提示句、「確定出發」停用；有「先離開」的長短兩種寫法", () => {
    expect(html).toContain(CONFIRM_EMPTY);
    expect(html).toMatch(new RegExp(`disabled=""[^>]*data-testid="range-confirm"[^>]*>${CONFIRM_LABEL}`));
    expect(html).toContain("先離開（下次回到靶場）");
    expect(html).toContain('<span class="ob-leave-short">先離開</span>');
  });

  it("選大類直接畫元件也一樣（不經模式分派）", () => {
    const direct = renderToStaticMarkup(createElement(RangeClassPick, { view: VIEW, range: RANGE, busy: false, error: null, onCloseError: noop, onTrial: noop, onConfirm: noop, onHome: noop }));
    expect(direct).toBe(html);
  });

  it("樣式：三欄、窄版一欄與人物 104 欄、確認列窄版黏底、「確定出發」min-width 寫死 220", () => {
    const css = readFile(SRC_DIR, "styles/range-ob.css");
    expect(css).toMatch(/\.ob-class-grid \{[^}]*grid-template-columns: repeat\(3, minmax\(0, 1fr\)\);[^}]*gap: 14px/);
    expect(css).toMatch(/\.ob-class-top \{[^}]*grid-template-columns: 104px minmax\(0, 1fr\)/);
    expect(css).toMatch(/\.entry-skin \.ob-confirm button\.entry-create-go \{\s*min-width: 220px;/);
    expect(css).toMatch(/\.ob-confirm \{[^}]*grid-template-columns: minmax\(0, 1fr\) auto/);
    expect(css).toMatch(/@media \(max-width: 560px\)[\s\S]*\.ob-confirm-panel \{[^}]*position: sticky;[^}]*bottom: 0/);
    expect(css).toMatch(/\.ob-class-card\.selected \{[^}]*0 0 0 2px var\(--ui-gold-hi\)/);
    expect(css).toMatch(/\.ob-class-card:hover:not\(\.selected\)[\s\S]*?translateY\(-3px\)/);
    expect(readFile(SRC_DIR, "styles/index.css")).toContain('@import "./range-ob.css";');
  });
});

describe("OB-5 正式選定畫面", () => {
  const html = renderToStaticMarkup(createElement(RangeScreen, { ...screenProps(STARTER), mode: "choose" }));

  it("整頁：標題牌讀伺服器給的地方、葛蘭的兩句與頭像、沙盒說明", () => {
    expect(html).toContain("正式選定");
    expect(html).toContain("霧渡鎮導師堂・選你自己的武器與 2 個關鍵字");
    expect(html).toContain("該挑你自己的兵器了。");
    expect(html).toContain("我標了適合你的。");
    expect(html).toMatch(/data-testid="range-speaker-portrait"[^>]*data-speaker="葛蘭"/);
    expect(html).toContain(SANDBOX_NOTE);
  });

  it("三塊照現行靶場：預覽、武器架、關鍵字；有推薦時多一句說明", () => {
    for (const id of ["range-preview", "range-racks", "range-keywords"]) expect(html).toContain(`data-testid="${id}"`);
    expect(html).toContain("每個關鍵字給 1 招起始技能，都能先「看示範」。「推薦」是照你前兩場用得最多的招標的，不照著選也可以。");
    expect(html).toContain("確定後，屬性點會照這把武器的推薦配法重新配好。");
    const none = renderToStaticMarkup(createElement(RangeScreen, { ...screenProps({ ...STARTER, recommended_keywords: [] }), mode: "choose" }));
    expect(none).toContain("每個關鍵字給 1 招起始技能，都能先「看示範」。");
    expect(none).not.toContain("「推薦」是照你前兩場");
  });

  it("按鈕：寬版在關鍵字那一塊，窄版在黏底列（拿起試打用一般按鈕色，一列只有一顆藍色主鈕）", () => {
    expect(html).toMatch(new RegExp(`data-testid="range-later"[^>]*>${CHOOSE_LATER}`));
    expect(html).toMatch(new RegExp(`disabled=""[^>]*data-testid="range-confirm"[^>]*>${CHOOSE_LABEL}`));
    const bar = html.slice(html.indexOf('data-testid="range-choose-bar"'));
    expect(bar).toMatch(/class="range-try"[^>]*data-testid="range-bar-try"/);
    expect(bar.match(/class="primary /g)).toHaveLength(1);
    expect(bar).toContain(CHOOSE_LATER);
    expect(bar).toContain(CHOOSE_LABEL);
    expect(bar).toContain("已選 0/2");
  });

  it("被拒的原因顯示在頁面上（背包放不下等）；等伺服器計算時有等待提示", () => {
    const refused = renderToStaticMarkup(createElement(RangeScreen, { ...screenProps(STARTER), mode: "choose", error: "不能選雙手劍：它占用副手，副手要收進背包，但背包放不下" }));
    expect(refused).toMatch(/data-testid="range-problem"[^>]*>不能選雙手劍/);
    // 等待提示：按了「確定選這套」、伺服器還沒回來時才出（去試打的等待不出）
    const source = readFile(SRC_DIR, "world/RangeScreen.tsx");
    expect(source).toMatch(/const waiting = busy && confirming;/);
    expect(source).toMatch(/\{waiting && \(\s*<div className="small range-wait" role="status" data-testid="range-wait">/);
    expect(html).not.toContain('data-testid="range-wait"');
    expect(readFile(SRC_DIR, "world/QuestLog.tsx")).toMatch(/\{busy && \(\s*<div className="small world-offer-wait"/);
  });

  it("樣式：推薦小牌靠右、黏底列三欄 1fr 1fr 1.25fr 且按鈕 min-width 0、窄版才出現並黏在底部", () => {
    const css = readFile(SRC_DIR, "styles/range-ob.css");
    expect(css).toMatch(/\.ob-rec \{[^}]*margin-left: auto;[^}]*font-size: 11px/);
    expect(css).toMatch(/\.ob-bar-actions \{[^}]*grid-template-columns: minmax\(0, 1fr\) minmax\(0, 1fr\) minmax\(0, 1\.25fr\)/);
    expect(css).toMatch(/\.entry-skin \.ob-bar-actions button \{[^}]*min-width: 0/);
    expect(css).toMatch(/@media \(max-width: 1039px\)[\s\S]*\.ob-choose-bar \{[^}]*position: sticky;[^}]*bottom: 0/);
  });
});

describe("OB-5 完成後的話與接線", () => {
  it("確定出發之後：守印人指示去霧渡鎮（共用彈窗外框）", () => {
    const html = renderToStaticMarkup(createElement(RangeDoneDialog, { lines: rangeDoneLines(RANGE), onClose: noop }));
    expect(html).toContain("去霧渡鎮找渡婆婆。");
    expect(html).toContain("出發");
    expect(rangeDoneLines(null)).toEqual([]);
  });

  it("正式選定之後：葛蘭收回入門配備的那句（在主城選時沒有）", () => {
    expect(chooseDoneLines(STARTER)).toEqual([{ speaker_zh: "葛蘭", text_zh: "借你的那套我收回了。" }]);
    expect(chooseDoneLines(RANGE)).toEqual([]);
    const html = renderToStaticMarkup(createElement(RangeDoneDialog, { lines: chooseDoneLines(STARTER), heading: "正式選定", closeLabel: "好", onClose: noop }));
    expect(html).toContain("借你的那套我收回了。");
  });

  it("接線：建角不送武器；選大類送 opening_class、正式選定送 opening_confirm；試打不回寫、結束回到靶場", () => {
    const pick = readFile(SRC_DIR, "world/WorldCharacterPicker.tsx");
    expect(pick).not.toMatch(/weapon: picker/);
    const screen = readFile(SRC_DIR, "screens/WorldScreen.tsx");
    expect(screen).toMatch(/view\.opening != null && !shouldShowOpening/);
    expect(screen).toContain('"回到靶場"');
    expect(screen).toContain("api.worldRangeTrial");
    expect(screen).toContain('kind: "opening_class"');
    expect(screen.match(/kind: "opening_confirm"/g)).toHaveLength(1);
    expect(screen).toMatch(/rangeKind === "class" \|\| choosing/);
  });

  it("入門招、示範招、關鍵字不寫死在前端：靶場的程式裡沒有技能 ID", () => {
    for (const file of ["world/RangeScreen.tsx", "world/RangeClassPick.tsx", "world/RangeParts.tsx", "world/range.ts"]) expect(readFile(SRC_DIR, file)).not.toMatch(/skill_[a-z_]+/);
  });
});

describe("OB-6 重選頁、確認彈窗、入口、小牌", () => {
  it("重選頁：葛蘭的話與頭像、標題牌寫地方、不標推薦；在主城是守印人（金框）", () => {
    const html = renderToStaticMarkup(createElement(RangeScreen, { ...screenProps(CHOSEN), mode: "reselect" }));
    expect(html).toContain("想換？");
    expect(html).toMatch(/data-testid="range-speaker-portrait"[^>]*data-speaker="葛蘭"/);
    expect(html).toContain(reselectPlaqueSub("霧渡鎮導師堂", 2));
    expect(reselectPlaqueSub("樞島工坊靶場", 2)).toBe("樞島工坊靶場・換一次武器與 2 個關鍵字");
    const capital: RangeView = { ...CHOSEN, reselect: { ...RESELECT, in_capital: true, here_zh: "樞島工坊靶場", speaker: KEEPER, lines: [{ speaker_zh: "守印人", text_zh: "不順手？" }] } };
    const keeper = renderToStaticMarkup(createElement(RangeScreen, { ...screenProps(capital), mode: "reselect" }));
    expect(keeper).toContain("不順手？");
    expect(keeper).toMatch(/data-testid="range-speaker-portrait"[^>]*data-speaker="守印人"[^>]*data-frame="gold"/);
  });

  it("確認彈窗列的項目全部來自資料：會收回的招、起始武器、材料不退、只有一次", () => {
    const lines = reselectConfirmLines(RESELECT, "雙手劍");
    expect(lines).toEqual(["會收回的招：甲招、乙招、丙招", "會收回起始武器「雙手劍」", "雙手劍的強化 +2（材料不退）", RESELECT_ONCE]);
    const bare = reselectConfirmLines({ ...RESELECT, returned_zh: [], weapon_returned: false, lost_zh: [] }, "");
    expect(bare).toEqual(["起始武器已經不在身上：不收回，也不扣錢", RESELECT_ONCE]);
    const html = renderToStaticMarkup(createElement(ReselectConfirmDialog, { lines, busy: false, onGo: noop, onBack: noop }));
    for (const line of lines) expect(html).toContain(line);
    expect(html.match(/data-testid="range-reselect-line"/g)).toHaveLength(lines.length);
    expect(html).toContain('data-testid="range-reselect-go"');
  });

  it("入口：葛蘭本人或主城靶場的面板才有「重選」鈕，不能重選就沒有", () => {
    expect(opensReselect(RESELECT, { npc: "gran" })).toBe(true);
    expect(opensReselect(RESELECT, { npc: "granny_du" })).toBe(false);
    expect(opensReselect(RESELECT, { object: "training_range" })).toBe(false);
    const capital = { ...RESELECT, in_capital: true };
    expect(opensReselect(capital, { object: "workshop_master" })).toBe(true);
    expect(opensReselect(capital, { npc: "gran" })).toBe(false);
    expect(opensReselect({ ...RESELECT, available: false }, { npc: "gran" })).toBe(false);
    expect(opensReselect(null, { npc: "gran" })).toBe(false);
    const child = createElement("div", { "data-testid": "inner" });
    const withButton = renderToStaticMarkup(createElement(ReselectEntry, { reselect: RESELECT, target: { npc: "gran" }, busy: false, onOpen: noop, children: child }));
    expect(withButton).toContain('data-testid="world-reselect-panel"');
    expect(withButton).toContain('data-testid="inner"');
    const plain = renderToStaticMarkup(createElement(ReselectEntry, { reselect: RESELECT, target: { npc: "granny_du" }, busy: false, onOpen: noop, children: child }));
    expect(plain).toBe('<div data-testid="inner"></div>');
  });

  it("不自動開：WorldScreen 只在按鈕後打開重選頁", () => {
    const screen = readFile(SRC_DIR, "screens/WorldScreen.tsx");
    expect(screen.match(/setReselectOpen\(true\)/g)?.length).toBe(3); // 頂列、葛蘭面板、主城靶場面板
    expect(screen).not.toMatch(/useEffect\([^)]*setReselectOpen\(true\)/);
    expect(screen).toContain('kind: "opening_reselect"');
    expect(screen).toContain("RESELECT_OPEN_LABEL");
    expect(RESELECT_OPEN_LABEL).not.toBe("");
  });

  it("任務欄小牌：照 window_open 顯示（人在野外也顯示），數字讀 before_level；說明卡寫去哪裡", () => {
    expect(reselectBadge(RESELECT)).toBe("4 級前可重選一次");
    expect(reselectBadge({ ...RESELECT, before_level: 5 })).toBe("5 級前可重選一次");
    expect(reselectBadge({ ...RESELECT, available: false })).toBe("4 級前可重選一次");
    expect(reselectBadge({ ...RESELECT, window_open: false })).toBeNull();
    expect(reselectBadge(null)).toBeNull();
    expect(reselectBadgeHint(RESELECT)).toContain(RESELECT.place_zh);
  });

  it("重選完成的話；配點收尾彈窗第二段是重選提醒", () => {
    expect(reselectDoneLines(CHOSEN)).toEqual([{ speaker_zh: "葛蘭", text_zh: "換好了。" }]);
    expect(reselectDoneLines(STARTER)).toEqual([]);
    const reminder = [{ speaker_zh: "葛蘭", text_zh: "到 4 級之前，能免費重選一次。" }];
    expect(allocateClosingLines("葛蘭", "好。去雨中梯田。", reminder)).toEqual([{ speaker_zh: "葛蘭", text_zh: "好。去雨中梯田。" }, ...reminder]);
    expect(allocateClosingLines("葛蘭", "好。", [])).toHaveLength(1);
    expect(allocateClosingLines("葛蘭", null, undefined)).toEqual([]);
  });

  it("內容檔的重選台詞（定稿逐字）", () => {
    const data = parse(newcomerYaml) as { range: Record<string, { speaker_zh: string; text_zh: string }[]> };
    expect(data.range.reselect).toEqual([{ speaker_zh: "葛蘭", text_zh: "想換？來，這次挑準一點，機會只有一次。" }]);
    expect(data.range.reselect_capital).toEqual([{ speaker_zh: "守印人", text_zh: "不順手？換一次可以，只有這一次。到 4 級，這架子就不替你改了。" }]);
    expect(data.range.reselect_done).toEqual([{ speaker_zh: "葛蘭", text_zh: "換好了。之前的招我收回了，新的也給你補上了。" }]);
    expect(data.range.reselect_capital_done).toEqual([{ speaker_zh: "守印人", text_zh: "換好了。舊的那套我收走，新的也替你補上。這是最後一次，好好用。" }]);
    expect(data.range.reselect_reminder).toEqual([{ speaker_zh: "葛蘭", text_zh: "打起來不順手就回來找我。到 4 級之前，能免費重選一次。" }]);
  });
});
