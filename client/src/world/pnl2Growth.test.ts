// PNL-2「成長與技能」面板（docs/art/資訊面板-移植需求.md 3.3、4.1 #13～#23、#35、#36、#43）：分頁記號、預設分頁、固定區、各頁內容、
// `FlashSection` 規則籌碼（一輪營火共用）、主角卡靈感點直開「靈感閃現」。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { RunHero, RunResponse, WorldView } from "../api/types";
import campfire from "../run/fixtures/run_campfire.json";
import { FlashSection, flashRuleChips, FLASH_RULE_TIP_ZH, flashRowState } from "../run/FlashSection";
import { RunCampfire } from "../screens/RunCampfire";
import { heroFaceKey } from "../ui/heroFace";
import { pickTab } from "../ui/panelTabRules";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { attrBadge, flashBadge, growthTabBadge, growthTabOf, growthWarning, raceLockTag } from "./growthPanel";
import { growthTabs, WorldGrowth } from "./WorldGrowth";

const CAMPFIRE = campfire as unknown as RunResponse;
const HERO: RunHero = CAMPFIRE.hero;
const noop = async () => null;
const html = (el: ReturnType<typeof createElement>) => renderToStaticMarkup(el);

interface Over {
  level?: number;
  insight?: number;
  points?: number;
  atService?: boolean;
  blocked?: string | null;
  limits?: Record<string, string>;
  starter?: string | null;
  race?: { free?: boolean; reason?: string | null };
  look?: string | null;
}

const FLASH_LIMIT = "到 4 級才能閃現";
const DISSOLVE_LIMIT = "4 級前不能溶掉技能或傳承";
const OATH_LIMIT = "入門期還不能立誓，找葛蘭正式選定後開放";

/** 測試用到的欄位（其他欄位不讀）。 */
function view(o: Over = {}): WorldView {
  const atService = o.atService ?? true;
  const blocked = o.blocked !== undefined ? o.blocked : atService ? null : "這裡不是城鎮或營火";
  return {
    character: {
      character_id: "c1",
      level: o.level ?? 2,
      attribute_points: o.points ?? 0,
      race: "human",
      look: {},
      look_change_zh: o.look !== undefined ? o.look : "只有在主城能改外觀",
      free_race_change: o.race?.free ?? false,
      free_race_change_zh: o.race?.reason ?? null,
      hero_look: null,
      origin_realm: null,
    },
    field: null,
    hero: { ...HERO, insight: o.insight ?? 0 },
    limits: o.limits ?? {},
    growth: {
      insight: o.insight ?? 0,
      skill_tier: 1,
      at_service: atService,
      service_zh: "閃現、重閃、溶掉、傳承、重配屬性、立誓只在城鎮與營火（和換技能同一處）",
      can_allocate: (o.points ?? 0) > 0,
      can_spend: blocked === null,
      blocked_zh: blocked,
      pending: false,
      can_flash: blocked === null,
      flash_blocked_zh: null,
      starter_note_zh: o.starter ?? null,
    },
    oath: {
      available: false,
      unavailable_zh: "尚未開放",
      current: null,
      cooldown_until: 0,
      cooldown_zh: null,
      can_swear: false,
      swear_problem_zh: "尚未開放",
      can_release: false,
      templates: [],
    },
  } as unknown as WorldView;
}

const STARTER: Over = { level: 2, insight: 1, points: 0, atService: false, limits: { flash: FLASH_LIMIT, dissolve: DISSOLVE_LIMIT, oath: OATH_LIMIT, race: "正式選定武器與關鍵字之前不能換種族" }, starter: "入門期可以自己配點，正式選定時會照新武器重配一次。" };
const LV4_TOWN: Over = { level: 4, insight: 3, points: 2, atService: true };

describe("分頁記號與預設分頁（3.2 第 3、5 條；#42、#43）", () => {
  it("入門期：靈感閃現掛金鎖（滑過「閃現 4 級起」、不掛數字），屬性點沒有點不掛 → 預設開「屬性點」", () => {
    const v = view(STARTER);
    expect(flashBadge(v)).toEqual({ kind: "lock", hint: "閃現 4 級起" });
    expect(attrBadge(v)).toBeNull();
    const tabs = growthTabs({ view: v, busy: false, onChoose: noop, onAct: noop });
    expect(tabs.map((t) => t.id)).toEqual(["flash", "attr", "care", "look"]);
    expect(pickTab(tabs)).toBe("attr");
  });

  it("Lv 4 在城鎮、靈感 3、屬性點 2：閃現金底「3」（可以閃現：靈感點 3）、屬性點金底「2」→ 預設開閃現", () => {
    const v = view(LV4_TOWN);
    expect(flashBadge(v)).toEqual({ kind: "n", value: 3, hint: "可以閃現：靈感點 3" });
    expect(attrBadge(v)).toEqual({ kind: "n", value: 2, hint: "未分配屬性點 2" });
    expect(pickTab(growthTabs({ view: v, busy: false, onChoose: noop, onAct: noop }))).toBe("flash");
  });

  it("不在城鎮時閃現不掛數字（花不了）；屬性點照掛（分配不看地點）；整備、外觀不掛", () => {
    const v = view({ ...LV4_TOWN, atService: false });
    expect(flashBadge(v)).toBeNull();
    expect(attrBadge(v)?.kind).toBe("n");
    expect(growthTabBadge(v, "care")).toBeNull();
    expect(growthTabBadge(view(STARTER), "care")).toBeNull();
    expect(growthTabBadge(v, "look")).toBeNull();
  });

  it("整備分頁滑過寫全名（#35）、只有整備有摺疊要量", () => {
    const tabs = growthTabs({ view: view(), busy: false, onChoose: noop, onAct: noop });
    const care = tabs.find((t) => t.id === "care")!;
    expect(care.hint).toBe("整備：重閃、溶掉與傳承、誓約");
    expect(care.folds).toEqual(["reflash", "dissolve", "oath"]);
    expect(tabs.map((t) => [t.label, t.short])).toEqual([
      ["靈感閃現", "閃現"],
      ["屬性點", "屬性"],
      ["整備", "整備"],
      ["外觀與種族", "外觀"],
    ]);
  });

  it("從提醒點進來的分頁：認得的照開，不認得＝照預設", () => {
    expect(growthTabOf("flash")).toBe("flash");
    expect(growthTabOf("nope")).toBeNull();
    expect(growthTabOf(null)).toBeNull();
  });
});

describe("固定區（#13、#14）", () => {
  it("四個籌碼（0 灰）、不在城鎮時一行警告＋(i) 原次行", () => {
    const out = html(createElement(WorldGrowth, { view: view(STARTER), busy: false, onChoose: noop, onAct: noop, onClose: () => undefined }));
    expect(out).toContain("成長與技能");
    expect(out).toContain('data-testid="pnl-back"');
    expect(out).toMatch(/Lv<b>2<\/b>/);
    expect(out).toMatch(/角色階級<b>1<\/b>/);
    expect(out).toMatch(/class="pnl-chip"[^>]*>.*?靈感點<b>1<\/b>/);
    expect(out).toMatch(/class="pnl-chip zero"[^>]*>.*?未分配屬性點<b>0<\/b>/);
    expect(out).toContain("<b>現在不行</b>：這裡不是城鎮或營火");
    expect(out).toContain('aria-label="閃現、重閃、溶掉、傳承、重配屬性、立誓只在城鎮與營火（和換技能同一處）。"');
    expect(growthWarning(view(STARTER))).toBe("這裡不是城鎮或營火");
  });

  it("在城鎮可以花點時不顯示警告", () => {
    const out = html(createElement(WorldGrowth, { view: view(LV4_TOWN), busy: false, onChoose: noop, onAct: noop, onClose: () => undefined }));
    expect(out).not.toContain('data-testid="world-service-note"');
    expect(growthWarning(view(LV4_TOWN))).toBeNull();
  });
});

describe("各分頁內容", () => {
  const pane = (v: WorldView, tab: "flash" | "attr" | "care" | "look") =>
    html(createElement(WorldGrowth, { view: v, busy: false, onChoose: noop, onAct: noop, onClose: () => undefined, initialTab: tab }));

  it("屬性點（入門期）：資訊條照伺服器、「未分配的屬性點」＋「升級時每級 +2」、虛線空狀態", () => {
    const out = pane(view(STARTER), "attr");
    expect(out).toContain('data-pane="attr"');
    expect(out).toContain("入門期可以自己配點，正式選定時會照新武器重配一次。");
    expect(out).toContain("未分配的屬性點");
    expect(out).toContain("升級時每級 +2");
    expect(out).toContain("沒有未分配的屬性點。");
  });

  it("靈感閃現（入門期）：鎖住提示「閃現：4 級起」、規則籌碼、每招鎖標籤「4 級起」、閃現鈕停用", () => {
    const out = pane(view(STARTER), "flash");
    expect(out).toContain("<b>閃現</b>：4 級起");
    expect(out).toContain('data-testid="flash-rule-chips"');
    expect(out).toContain("已閃 ");
    expect((out.match(/4 級起<\/span>/g) ?? []).length).toBeGreaterThan(0);
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*data-testid="flash-open-/);
    expect(out).not.toContain('class="skill-flash-ready small"');
  });

  it("整備：第一行＋「只在城鎮與營火」、三列摺疊（新字）、右邊鎖標籤「4 級起」「正式選定後」、重閃沒有時「還沒有可以重閃的技能」", () => {
    const out = pane(view(STARTER), "care");
    expect(out).toContain("重閃、溶掉與傳承、誓約");
    expect(out).toContain("只在城鎮與營火");
    expect(out).toContain("<b>重閃</b>　把以前的一次變化換掉");
    expect(out).toContain("<b>溶掉或傳承</b>　二選一，舊技能會消失");
    expect(out).toContain("<b>誓約</b>　同時 1 個，到城鎮或營火才能換");
    expect(out).toContain('name="world-growth-care"');
    expect(out).toMatch(/data-testid="world-care-dissolve-tag"[^>]*>.*?4 級起/);
    expect(out).toMatch(/data-testid="world-care-oath-tag"[^>]*>.*?正式選定後/);
    // 摺疊展開後照現行內容（原段落），但不再畫一次區塊標題
    expect(out).toContain("把一招以前某一次的變化換掉");
    expect(out).not.toContain("重閃（只在城鎮與營火）");
    expect(out).not.toContain('<div class="section-title">誓約</div>');
  });

  it("外觀與種族：外觀列鎖標籤（伺服器的字）、能改時「主城隨時免費」；種族列（入門期「正式選定後才能換」）", () => {
    const away = pane(view({ ...STARTER, race: { free: true, reason: "正式選定武器與關鍵字之前不能換種族" } }), "look");
    expect(away).toMatch(/data-testid="world-look-tag"[^>]*>.*?只有在主城能改外觀/);
    expect(away).toContain("本季可以免費換一次");
    expect(away).toMatch(/data-testid="world-race-tag"[^>]*>.*?正式選定後才能換/);
    const home = pane(view({ look: null }), "look");
    expect(home).toMatch(/data-testid="world-look-tag"[^>]*>主城隨時免費/);
    expect(home).not.toContain("world-race-change");
  });

  it("種族鎖標籤：入門期＝新字；其他原因照伺服器；可以換＝沒有", () => {
    expect(raceLockTag(view({ limits: { race: "x" }, race: { free: true, reason: "x" } }))).toBe("正式選定後才能換");
    expect(raceLockTag(view({ race: { free: true, reason: "只有在主城能換種族" } }))).toBe("只有在主城能換種族");
    expect(raceLockTag(view({ race: { free: true, reason: null } }))).toBeNull();
  });
});

describe("FlashSection 規則籌碼（#19；一輪營火共用）", () => {
  it("三個籌碼照伺服器的規則數字＋(i)", () => {
    expect(flashRuleChips(HERO.flash_rules).map((c) => (c.after === undefined ? `${c.strong}　${c.text}` : `${c.text}${c.strong}${c.after}`))).toEqual([
      "1 點　4 個變化選 1",
      "+1 點　指定類別、該類 3 選 1",
      "每招最多閃 5 次",
    ]);
    expect(FLASH_RULE_TIP_ZH).toBe("出題就會扣點，一定要選一個。要先在戰鬥中用過才能再閃。");
  });

  it("一輪的閃現區與營火也換成籌碼，原本那一段不見了、營火其他區塊照舊", () => {
    const section = html(createElement(FlashSection, { runId: "r", hero: HERO, busy: false, onChoose: noop }));
    expect(section).toContain('data-testid="flash-rule-chips"');
    expect(section).not.toContain("點靈感讓一招技能閃現");
    const camp = html(createElement(RunCampfire, { run: CAMPFIRE, view: { screen: "campfire", afterBattle: 1 } as never, busy: false, onChoose: noop }));
    expect(camp).toContain('data-testid="flash-rule-chips"');
    expect(camp).toContain("重閃（只在營火）");
    expect(camp).toContain("溶掉或傳承（二選一，只在營火）");
  });

  it("閃現鈕的停用原因：鎖住原因優先，其次完整技能、伺服器原因、靈感點不足", () => {
    expect(flashRowState(undefined, 3, HERO.flash_rules, "到 4 級才能閃現")).toEqual({ can: false, reason: "到 4 級才能閃現" });
    expect(flashRowState({ complete: true } as never, 3, HERO.flash_rules, null).reason).toBe("完整技能不能再閃現");
    expect(flashRowState({ complete: false, can_flash: true } as never, 0, HERO.flash_rules, null)).toEqual({ can: false, reason: "靈感點不足" });
    expect(flashRowState({ complete: false, can_flash: true } as never, 1, HERO.flash_rules, null).can).toBe(true);
  });
});

describe("主角卡靈感點直開「靈感閃現」（3.2 第 3 條）", () => {
  it("HUD 的靈感點籌碼有 onGrowthTab 時是按鈕；WorldScreen 用 key 讓面板重新掛到那一頁", () => {
    const hud = readFile(SRC_DIR, "world/WorldHud.tsx");
    expect(hud).toContain('onInsight={props.onGrowthTab !== undefined ? () => props.onGrowthTab?.("flash") : undefined}');
    const screen = readFile(SRC_DIR, "screens/WorldScreen.tsx");
    expect(screen).toContain("<WorldGrowth key={growthTab.seq}");
    expect(screen).toContain("initialTab={growthTab.tab}");
    expect(screen).toContain("onGrowthTab={openGrowthTab}");
  });

  it("指定 initialTab 時就算第一頁鎖住也開那一頁", () => {
    const out = html(createElement(WorldGrowth, { view: view(STARTER), busy: false, onChoose: noop, onAct: noop, onClose: () => undefined, initialTab: "flash" }));
    expect(out).toContain('data-pane="flash"');
  });
});

describe("不帶框的主角頭像（第 5 節第 11 點：加選項，同一份外觀）", () => {
  it("快取鍵：帶框的不變、不帶框的另加 |bare", () => {
    const input = { template: "hero", dollLook: null, team: "ally", summon: false, weaponId: null, weaponClass: null, equipment: [], raceLook: null } as never;
    expect(heroFaceKey(input, null, 16, 2)).not.toContain("bare");
    expect(heroFaceKey(input, null, 16, 2, true)).toBe(`${heroFaceKey(input, null, 16, 2)}|bare`);
  });
});
