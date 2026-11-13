// FL-1b：靈感閃現「選變體」畫面改版（docs/art/靈感閃現選擇-移植需求.md）。
// 夾具 `dev/fixtures/flashChoice.json` 由 `scripts/export_flash_choice_fixture.py` 用伺服器同一套函式產生（不是手寫）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { FlashOption, PendingFlash, RunHero, SkillCard, StatChange } from "../api/types";
import data from "../dev/fixtures/flashChoice.json";
import { FlashPendingPanel } from "../screens/RunFlashPending";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { pickChoice, pickReady } from "./flash";
import {
  FLASH_LOCK_NOTE_ZH,
  FLASH_MUST_PICK_ZH,
  FLASH_PICK_NONE_ZH,
  autoUnequip,
  headlineOf,
  nowStyle,
  nowText,
  parseTerms,
  pendingWhat,
  plainTerms,
  showsUnequipMenu,
  splitWhen,
  stepPick,
  unequipPrompt,
} from "./flashChoice";

type Fixture = { hero: RunHero; sets: Record<string, PendingFlash>; bases?: Record<string, SkillCard> };
const FIXTURE = data as unknown as Fixture;
const BASE = FIXTURE.sets.base!;
const noop = async () => null;
const html = (pending: PendingFlash, lockNote?: string) =>
  renderToStaticMarkup(createElement(FlashPendingPanel, { pending, hero: FIXTURE.hero, busy: false, onChoose: noop, ...(lockNote === undefined ? {} : { lockNote }) }));

function change(over: Partial<StatChange>): StatChange {
  return { field: "range", label_zh: "射程", effect_index: null, before: "4", after: "5", direction: "better", name_zh: "射程", term: null, before_zh: "4 格", after_zh: "5 格", icon: null, ...over } as StatChange;
}

describe("FL-1b 純函式", () => {
  it("「後」四種樣式；拿掉的效果照變弱、拿掉的代價寫「不用花」", () => {
    expect(nowStyle(change({ direction: "better" }))).toBe("up");
    expect(nowStyle(change({ direction: "cost" }))).toBe("cost");
    expect(nowStyle(change({ direction: "worse" }))).toBe("down");
    expect(nowStyle(change({ direction: "new", before: null }))).toBe("new");
    expect(nowStyle(change({ direction: "worse", after: null, after_zh: null }))).toBe("down");
    expect(nowText(change({ direction: "worse", after: null, after_zh: null }))).toBe("沒有");
    expect(nowText(change({ direction: "cost", after: null, after_zh: null }))).toBe("不用花");
    expect(nowStyle(change({ direction: "cost", after: null, after_zh: null }))).toBe("up");
  });

  it("術語標記：[[id|字]]、{{kw:id}}", () => {
    const text = "[[surface:water|積水]]，[[makes|會造成]] {{kw:wet}}[[kw:wet|潮濕]]";
    expect(parseTerms(text)).toEqual([
      { kind: "term", id: "surface:water", label: "積水" },
      { kind: "text", text: "，" },
      { kind: "term", id: "makes", label: "會造成" },
      { kind: "text", text: " " },
      { kind: "icon", cat: "kw", id: "wet" },
      { kind: "term", id: "kw:wet", label: "潮濕" },
    ]);
    expect(plainTerms(text)).toBe("積水，會造成 潮濕");
    expect(splitWhen("3 成[[weapon_damage:300|武器傷害]]（目標這回合被[[kw:collision|撞過]]才有）")).toEqual({
      main: "3 成[[weapon_damage:300|武器傷害]]",
      when: "（目標這回合被[[kw:collision|撞過]]才有）",
    });
    expect(splitWhen("5 格").when).toBeNull();
  });

  it("標頭：第幾次（重閃、大變化照現行）", () => {
    expect(pendingWhat(BASE)).toBe("第 1 次閃現");
    expect(pendingWhat(BASE, true)).toBe("第 1 次");
    expect(pendingWhat({ ...BASE, slot: 0 })).toBe("重閃調整欄");
    expect(pendingWhat({ ...BASE, slot: 2 })).toBe("重閃第 2 次");
    expect(pendingWhat(FIXTURE.sets.transform!)).toBe("第 3 次閃現（大變化）");
  });

  it("大標：有 headline_zh 用它，沒有退回 summary_zh", () => {
    const [range, charge] = BASE.options;
    expect(headlineOf(range as FlashOption)).toBe("射程變遠 1 格");
    expect(headlineOf(charge as FlashOption)).toBe("多等幾回合再用，換這招變強");
    expect(headlineOf({ ...(range as FlashOption), headline_zh: null })).toBe((range as FlashOption).summary_zh);
  });

  it("卸下選單：被動、反應填「被動欄」，主動填「主動欄」；姿態欄自動換下、不出選單", () => {
    const trans = FIXTURE.sets.transform!.options.find((o) => o.transform) as FlashOption;
    expect(showsUnequipMenu(trans)).toBe(true);
    expect(unequipPrompt(trans)).toBe("被動欄滿了，選一招卸下");
    expect(unequipPrompt({ ...trans, unequip_slot: "active" })).toBe("主動欄滿了，選一招卸下");
    expect(pickReady(trans, null)).toBe(false);
    const stance = FIXTURE.sets.stance!.options.find((o) => o.transform) as FlashOption;
    expect(showsUnequipMenu(stance)).toBe(false);
    expect(autoUnequip(stance)).toBe(stance.unequip_candidates[0]);
    expect(pickReady(stance, null)).toBe(true);
    expect(pickChoice(stance, null)).toEqual({ kind: "flash_pick", pick: stance.index, unequip: stance.unequip_candidates[0] });
  });

  it("方向鍵在選項間循環", () => {
    expect(stepPick([0, 1, 2, 3], null, "ArrowDown")).toBe(0);
    expect(stepPick([0, 1, 2, 3], 3, "ArrowDown")).toBe(0);
    expect(stepPick([0, 1, 2, 3], 0, "ArrowUp")).toBe(3);
    expect(stepPick([0, 1, 2, 3], 1, "End")).toBe(3);
    expect(stepPick([0, 1, 2, 3], 1, "a")).toBe(1);
  });
});

describe("FL-1b 畫面", () => {
  const out = html(BASE, FLASH_LOCK_NOTE_ZH);

  it("上固定區：標題、第幾次＋已扣標籤、說明行、鎖住提示、原技能列（只出現一次）", () => {
    expect(out).toContain("靈感閃現");
    expect(out).toContain("選一個變化");
    expect(out).toContain("「點燃斬」第 1 次閃現");
    expect(out).toContain("已扣 1 點");
    expect(out).toContain(FLASH_MUST_PICK_ZH);
    expect(out).toContain(FLASH_LOCK_NOTE_ZH);
    expect(out.match(/data-testid="flash-base"/g)?.length).toBe(1);
    expect(out).toContain("原本的樣子");
    expect(out).toContain("完整說明");
    // 拿掉的舊東西：每個選項的整張技能卡、「選這個」、「看原本的技能」
    expect(out).not.toContain("選這個");
    expect(out).not.toContain("看原本的技能");
    expect(out).not.toContain("skill-card ");
    expect(out).not.toContain("閃現！");
  });

  it("一輪沒有鎖住提示", () => {
    expect(html(BASE)).not.toContain(FLASH_LOCK_NOTE_ZH);
  });

  it("選項卡：單選、白話大標、類別標籤、前 → 後（四種樣式都照資料）", () => {
    expect(out).toContain('role="radiogroup"');
    expect(out.match(/role="radio"/g)?.length).toBe(4);
    expect(out).toContain("射程變遠 1 格");
    expect(out).toContain("打中的格子還會積水");
    expect(out).toContain("敵人剛被撞過，這招多傷一截");
    expect(out).toMatch(/class="fc-now cost"/);
    expect(out).toMatch(/class="fc-now up"/);
    expect(out).toMatch(/class="fc-now new"/);
    expect(out).toContain(">新<");
    // 蓄力：冷卻 2 回合 → ⚠ 4 回合、燃燒 5 回合 → 6 回合；不再有「威力 提高」那一列
    expect(out).toContain("4 回合");
    expect(out).toContain("6 回合");
    expect(out).not.toContain("威力 提高");
  });

  it("一升一降（輕巧）：代價框與變弱三角在同一張卡", () => {
    const rows = html(FIXTURE.sets.rows!);
    const light = rows.slice(rows.indexOf('data-testid="flash-option-0"'), rows.indexOf('data-testid="flash-option-1"'));
    expect(light).toContain('class="fc-now cost"');
    expect(light).toContain('class="fc-down"');
  });

  it("術語：有說明卡的畫點線底線（fc-term），查不到的只畫字", () => {
    expect(out).toContain('data-term="range"');
    expect(out).toContain('data-term="surface:water"');
    expect(out).toContain('data-term="weapon_damage:300"');
    const noTerms = html({ ...BASE, terms: {} });
    expect(noTerms).not.toContain("fc-term");
  });

  it("下固定區：都沒選時提示＋按不下去的確定", () => {
    expect(out).toContain(FLASH_PICK_NONE_ZH);
    expect(out).toMatch(/<button[^>]*data-testid="flash-pick-confirm"[^>]*disabled=""|<button[^>]*disabled=""[^>]*data-testid="flash-pick-confirm"/);
  });

  it("說明卡字：威力提高／降低用玩法 PM 確認的字，數字照資料填", () => {
    const terms = BASE.terms ?? {};
    const sets = Object.values(FIXTURE.sets);
    const all = Object.assign({}, ...sets.map((s) => s.terms ?? {})) as Record<string, { title_zh: string; text_zh: string }>;
    expect(all.power_up?.text_zh).toContain("換來這招至少一項真的變強");
    expect(all.power_down?.text_zh).toContain("其他都不會變強");
    expect(terms.ap?.text_zh).toMatch(/每回合 \d+ 點/);
    expect(terms["surface:water"]?.text_zh).toMatch(/預設留 \d+ 回合/);
  });
});

describe("FL-1b 原始碼", () => {
  it("cardDiff 的整句比對拿掉了（改讀伺服器 changes）", () => {
    expect(readFile(SRC_DIR, "run/flash.ts")).not.toContain("cardDiff");
  });
});
