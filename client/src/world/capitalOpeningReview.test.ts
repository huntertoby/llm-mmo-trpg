// Phase RT-5c：主城開場第二次驗收修正（docs/archive/art/RT-5b檢查.md）。半坐起髖部彎、夾邊箭頭加粗加描邊、石碑小牌避開人物、
// 夾邊泡泡避開別人的頭、鏡頭往上偏的深色帶、浮橋只有一個斷口、碑身不被說明列壓、浮橋每一段都算、浮動卡行尾不留「・」、
// 新手指引用完整名字點名任務 NPC。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import { type FieldView } from "../api/types";
import { drawSkyBridge } from "../render/capitalArt";
import { AWAKEN_HERO, AWAKEN_SIT_POSE, drawAwakenArt, awakenHeroSpec } from "../render/eventArtAwaken";
import { type DollSpec } from "../render/appearance";
import { HintPhrases } from "./AtlasMap";
import { EdgeArrow, FieldHeads } from "./FieldHeads";
import { hudLayout } from "./hud";
import { bridgeCells, captionShift, hudAvoidRects, hudReach, nudgeCamera, placeTag, tagSize, unitRect, captionShiftDecor, clearOfHud, NUDGE_FAR, NUDGE_MAX, type NudgeTarget } from "./hudAvoid";
import { guideAlertBox, guideAnchor, heroDoll, mainQuestNpc, mentionsName, otherHeadBox } from "./opening";
import { devCameraShift, shiftCamera } from "./devCamera";
import capitalYaml from "../../../content/world/fields/capital/capital.yaml?raw";
import newcomerYaml from "../../../content/world/newcomer.yaml?raw";
import npcsYaml from "../../../content/world/npcs/cloud_ridge.yaml?raw";
import questsYaml from "../../../content/world/quests/cloud_ridge.yaml?raw";
import { setDollSkin } from "../render/inkStyle";

// QK-1：這個檔案鎖 C 手繪墨線的畫法（C 的畫法留著給 QK-2～QK-4），畫面預設改成 Q 版之後在這裡指定 C。
setDollSkin("c");

type Obj = { at: [number, number]; kind: string; look?: string };
const CAPITAL = parse(capitalYaml) as { objects: Obj[] };
const NEWCOMER = parse(newcomerYaml) as { start_region: string; guide_town_zh: string; guide_capital_zh: string };
const NPCS = parse(npcsYaml) as { npcs: { id: string; name_zh: string; aliases_zh?: string[] }[] };
const QUESTS = parse(questsYaml) as { region: string; quests: { id: string; kind: string; giver: string }[] };

const VIEW = { width: 1568, height: 832 };
const LAYOUT = hudLayout(VIEW.width, VIEW.height, { mates: 2, narrow: false, collapsed: false });

type R = { left: number; top: number; width: number; height: number };
const hits = (a: R, b: R) => a.left < b.left + b.width && b.left < a.left + a.width && a.top < b.top + b.height && b.top < a.top + a.height;

/** 錄下 Canvas 呼叫的假 2D context（只記方法名稱與參數）。 */
function record(draw: (ctx: CanvasRenderingContext2D) => void): string[] {
  const calls: string[] = [];
  const target: Record<string, unknown> = {};
  const ctx = new Proxy(target, {
    get(t, k) {
      if (typeof k === "symbol") return undefined;
      if (k in t) return t[k];
      if (k === "createLinearGradient" || k === "createRadialGradient") return () => ({ addColorStop: () => undefined });
      if (k === "measureText") return () => ({ width: 10 });
      return (...args: unknown[]) => {
        calls.push(`${k}(${args.map((a) => (typeof a === "number" ? Math.round(a * 10) / 10 : String(a))).join(",")})`);
      };
    },
    set(t, k, v) {
      if (typeof k === "string") {
        t[k] = v;
        calls.push(`${k}=${String(v)}`);
      }
      return true;
    },
  });
  draw(ctx as unknown as CanvasRenderingContext2D);
  return calls;
}

describe("RT-5c 必修 1：半坐起是髖部彎（腿平貼地面、只抬上半身），不是整個人直直往後斜", () => {
  it("整個人不轉；骨架把兩條腿在髖部往前抬 90°，上身往後仰約 20°（不是往後倒）", () => {
    const sit = AWAKEN_HERO[1];
    expect(sit.rot).toBe(0);
    expect(sit.pose).toBe(AWAKEN_SIT_POSE);
    expect(AWAKEN_SIT_POSE.hipN).toBeCloseTo(Math.PI / 2, 5);
    expect(AWAKEN_SIT_POSE.hipF).toBeCloseTo(Math.PI / 2, 5);
    // 後仰角度：RT-5d 改成 30～35°（capitalOpeningReview.test.ts 鎖住）
    expect(AWAKEN_SIT_POSE.lean ?? 0).toBeLessThan(-0.2);
    // 往下放到屁股貼地（髖在紙娃娃 y＝-15，腿平放後下緣約 -14）
    expect(sit.drop).toBeGreaterThan(12);
    expect(sit.drop).toBeLessThan(15);
    // 躺著照舊
    expect(AWAKEN_HERO[0].pose).toBeNull();
    expect(Math.abs(AWAKEN_HERO[0].rot)).toBeGreaterThan(1.3);
  });

  it("畫出來會走姿勢的畫法（和沒姿勢不同），而且確定", () => {
    const hero: DollSpec = heroDoll(null);
    const a = record((c) => drawAwakenArt(c, hero, 1, ["cloud_ridge"], "樞島"));
    expect(a).toEqual(record((c) => drawAwakenArt(c, hero, 1, ["cloud_ridge"], "樞島")));
    // 腿在髖部轉 -π/2（往前抬平）：畫布旋轉 -1.6
    expect(a).toContain("rotate(-1.6)");
  });
});

describe("RT-5c 必修 2：夾在畫面邊的箭頭（筆畫 ≥ 3px、整體 ≥ 18px、外面 2px 深色描邊）", () => {
  it("SVG 20×20：金色筆畫 3.5，底下深色 7.5（每邊多 2）；方向用旋轉", () => {
    const html = renderToStaticMarkup(createElement(EdgeArrow, { dir: "ne" }));
    expect(html).toContain('width="20"');
    expect(html).toContain('height="20"');
    const widths = [...html.matchAll(/stroke-width="([\d.]+)"/g)].map((m) => Number(m[1]));
    expect(widths).toEqual([7.5, 3.5]);
    expect(widths[1]).toBeGreaterThanOrEqual(3);
    expect(((widths[0] ?? 0) - (widths[1] ?? 0)) / 2).toBeGreaterThanOrEqual(2);
    expect(html).toContain("rotate(45deg)");
    expect(html).toContain('stroke="#3a2406"');
  });

  it("開場說話的人在畫面外時，泡泡的名字旁與收起來的「！」旁都畫 SVG 箭頭（不是文字箭頭）", () => {
    const grid = { width: 32, height: 24, tiles: [] } as never;
    const base = { key: "fig:keeper", id: "keeper", kind: "figure" as const, name: "守印人", pos: { x: 2, y: 0 }, alert: "quest" as const, alertZh: "開場", rank: null, rankZh: "", main: true };
    const box = { left: 200, top: 200, right: 700, bottom: 600 };
    for (const folded of [false, true]) {
      const marks = [{ ...base, bubble: folded ? null : "站上傳送陣。", folded }];
      const html = renderToStaticMarkup(createElement(FieldHeads, { marks: marks as never, grid, scale: 1, onPick: () => undefined, view: box, visible: box }));
      expect(html).toContain('data-testid="field-edge-arrow"');
      expect(html).not.toMatch(/[↑↓←→↗↖↘↙]</);
    }
  });
});

describe("RT-5c 必修 3：石碑小牌不蓋到人物（含腳下的徽章與光圈）", () => {
  const avoid = hudAvoidRects(LAYOUT, VIEW);
  const grid = { width: 32, height: 24, tiles: [] } as never;
  const size = tagSize("灰燼荒原", "尚未開放");

  it("石碑正上方站著主角：小牌不放上方（會蓋到主角腳下的 A 徽章），改放旁邊，也不壓 HUD", () => {
    const stele = { left: 16 * 48 + 8, top: 400, width: 32, height: 66 };
    const hero = unitRect(grid, { x: 16, y: 6 }, 1);
    const at = placeTag(stele, size, { x: 0, y: 0 }, VIEW, avoid, [hero]);
    const r = { left: at.left, top: at.top, width: size.width, height: size.height };
    expect(hits(r, hero)).toBe(false);
    expect(avoid.some((h) => hits(r, h))).toBe(false);
    // 沒有人擋就照預設放上方
    expect(placeTag(stele, size, { x: 0, y: 0 }, VIEW, avoid, []).side).toBe("n");
  });

  it("人物的範圍含腳下徽章：格子下緣再往下、左右各多一點", () => {
    const r = unitRect(grid, { x: 3, y: 3 }, 1);
    expect(r.left).toBeLessThan(3 * 48);
    expect(r.left + r.width).toBeGreaterThan(4 * 48);
  });
});

describe("RT-5c 必修 4：夾在邊上的泡泡與「！」不落在別人頭上", () => {
  const box = { left: 100, top: 200, right: 700, bottom: 600 };

  it("夾到上緣時「！」剛好落在 NPC 頭頂 → 沿著上緣挪開，「！」和泡泡都不壓到那個人的頭", () => {
    const plain = guideAnchor({ left: 200, top: 50 }, box);
    expect(plain.edge).toBe("n");
    const npc = { left: plain.left, top: plain.top + 4 };
    const moved = guideAnchor({ left: 200, top: 50 }, box, null, { others: [npc] });
    expect(moved.edge).toBe("n");
    expect(moved.top).toBe(plain.top);
    expect(hits(guideAlertBox(moved), otherHeadBox(npc))).toBe(false);
    // 泡泡（e 邊）也不蓋到
    const bubble = { left: moved.left + 24, top: moved.top - 30, width: 210, height: 90 };
    expect(hits(bubble, otherHeadBox(npc))).toBe(false);
  });

  it("夾到左右邊時沿著邊上下挪；沒有人擋就照原位；確定", () => {
    const plain = guideAnchor({ left: 20, top: 400 }, box);
    expect(plain.edge).toBe("w");
    const npc = { left: plain.left, top: plain.top };
    const a = guideAnchor({ left: 20, top: 400 }, box, null, { others: [npc], bubble: false });
    expect(a.left).toBe(plain.left);
    expect(hits(guideAlertBox(a), otherHeadBox(npc))).toBe(false);
    expect(guideAnchor({ left: 20, top: 400 }, box, null, { others: [npc], bubble: false })).toEqual(a);
    expect(guideAnchor({ left: 20, top: 400 }, box, null, { others: [{ left: 600, top: 500 }] })).toEqual(plain);
  });
});

describe("RT-5c 小修 5：鏡頭往上偏時，地圖外的深色帶不超過上方 HUD 列", () => {
  it("微調的上限是右上地名列的下緣（不是左欄隊友卡的下緣）", () => {
    const place = LAYOUT.blocks.place;
    const reach = hudReach(LAYOUT, VIEW);
    expect(reach.top).toBeLessThanOrEqual(place.top + place.height);
    // 目標在地圖上緣、鏡頭往上偏也看不全時，深色帶（−cam.y）不超過上限
    const cam = { x: 0, y: 40, scale: 1 };
    const content = { width: 32 * 48, height: 24 * 48 };
    const out = nudgeCamera({ cam, view: VIEW, content, insets: { top: 300, right: 0, bottom: 0, left: 0 }, reach, avoid: hudAvoidRects(LAYOUT, VIEW), hero: { left: 700, top: 400, width: 48, height: 70 }, targets: [{ left: 700, top: 20, width: 60, height: 60 }] });
    expect(-out.y).toBeLessThanOrEqual(reach.top);
  });

  it("跟隨鏡頭本身留了很高的深色帶（主角在右邊、不會被左欄蓋住）時往下收到上限；主角會被蓋住就不收", () => {
    const reach = hudReach(LAYOUT, VIEW);
    const avoid = hudAvoidRects(LAYOUT, VIEW);
    const content = { width: 32 * 48, height: 24 * 48 };
    const base = { view: VIEW, content, insets: { top: 220, right: 0, bottom: 0, left: 0 }, reach, avoid, targets: [] };
    const free = nudgeCamera({ ...base, cam: { x: 0, y: -150, scale: 1 }, hero: { left: 900, top: 100, width: 48, height: 96 } });
    expect(-free.y).toBeLessThanOrEqual(reach.top);
    // 主角在左上（收上去會被主角卡蓋住）：不收
    const kept = nudgeCamera({ ...base, cam: { x: 0, y: -150, scale: 1 }, hero: { left: 40, top: 0, width: 48, height: 96 } });
    expect(kept.y).toBe(-150);
  });
});

describe("RT-5c 小修 6：兩格寬的浮橋只畫一個斷口（在右端那一格）", () => {
  const breaks = (calls: string[]) => calls.filter((c) => c === "closePath()").length;
  it("單格照舊有斷口；兩格時一格有、另一格沒有，加起來和單格一樣多", () => {
    for (const side of ["n", "e", "s", "w"] as const) {
      const one = breaks(record((c) => drawSkyBridge(c, side, true, true)));
      const left = breaks(record((c) => drawSkyBridge(c, side, true, false)));
      const right = breaks(record((c) => drawSkyBridge(c, side, false, true)));
      expect(one).toBeGreaterThan(0);
      expect(left).toBe(0);
      expect(right).toBe(one);
    }
  });

  it("接鄰的那一邊木板畫到格子邊（沒有接縫的空隙）", () => {
    const left = record((c) => drawSkyBridge(c, "n", true, false));
    // 格子 52：沒接鄰的那一邊留 4（-22），接鄰的那一邊畫到 +26 → 寬 48
    expect(left).toContain("fillRect(-22,-3.5,48,7)");
    expect(record((c) => drawSkyBridge(c, "n", true, true))).not.toContain("fillRect(-22,-3.5,48,7)");
  });
});

describe("RT-5c 小修 7：說明列不壓碑身（鏡頭微調移不開時水平挪開）", () => {
  const cap = { left: 650, top: 715, width: 270, height: 24 };
  it("碑身在說明列底下 → 挪到碑身旁邊（挪得少的那一邊），挪過去也不壓到別的東西與 HUD；沒壓到就不挪", () => {
    const body = { left: 776, top: 680, width: 32, height: 66 };
    const dx = captionShift(cap, [body], [], 1568);
    expect(dx).not.toBe(0);
    expect(hits({ ...cap, left: cap.left + dx }, body)).toBe(false);
    expect(Math.abs(dx)).toBeLessThanOrEqual(160);
    expect(captionShift(cap, [{ left: 100, top: 680, width: 32, height: 66 }], [], 1568)).toBe(0);
    // 右邊有 HUD 擋住 → 往左
    const right = captionShift(cap, [body], [{ left: 820, top: 700, width: 400, height: 60 }], 1568);
    expect(right).toBeLessThan(0);
    // 確定
    expect(captionShift(cap, [body], [], 1568)).toBe(dx);
  });
});

describe("RT-5c 小修 8：浮橋的每一段都算（第二段不被任務欄蓋住）", () => {
  it("主城每座橋從 bridge_<區域> 那一格連到相鄰的浮橋，共兩段", () => {
    const objects = CAPITAL.objects.map((o) => ({ x: o.at[0], y: o.at[1], look: o.look ?? null }));
    expect(bridgeCells(objects, { x: 31, y: 7 })).toEqual([
      { x: 31, y: 7 },
      { x: 31, y: 8 },
    ]);
    for (const start of [
      { x: 9, y: 0 },
      { x: 0, y: 15 },
      { x: 15, y: 23 },
      { x: 29, y: 23 },
    ])
      expect(bridgeCells(objects, start)).toHaveLength(2);
  });
});

describe("RT-5c 小修 9：浮動卡的「・」在段尾，行尾的藏起來", () => {
  it("每一段一個 inline-block，「・」放在段尾（最後一段沒有）；不會有段以「・」開頭", () => {
    const html = renderToStaticMarkup(createElement(HintPhrases, { text: "雲嶺：已開放・點了看區域圖・點城鎮傳送到霧渡鎮（第一次免費）" }));
    expect(html.match(/class="atlas-hint-phrase"/g)).toHaveLength(3);
    expect(html.match(/atlas-hint-sep/g)).toHaveLength(2);
    expect(html).not.toMatch(/class="atlas-hint-phrase">・/);
    expect(html).toMatch(/（第一次免費）<\/span><\/span>$/);
  });
});

describe("RT-5c 小修 10：新手指引用完整名字點名任務 NPC", () => {
  const npc = (id: string, name: string, alert: "quest" | "rumor" | null) => ({ id, name_zh: name, x: 1, y: 1, alert, alert_zh: null, rank: "neutral", rank_zh: "中立" });
  const guide = (text: string) => ({ text_zh: text, how_zh: null, opening: [] });

  it("內容檔鎖住：任務欄與主城指引一定含新手任務給任務的人的完整名字", () => {
    const starter = QUESTS.quests.find((q) => q.kind === "starter");
    expect(QUESTS.region).toBe(NEWCOMER.start_region);
    const giver = NPCS.npcs.find((n) => n.id === starter?.giver);
    expect(giver?.name_zh).toBe("渡婆婆");
    const names = NPCS.npcs.map((n) => n.name_zh);
    for (const text of [NEWCOMER.guide_town_zh, NEWCOMER.guide_capital_zh]) expect(mentionsName(text, giver?.name_zh ?? "", names)).toBe(true);
    // 別名（婆婆）不算完整名字
    for (const alias of giver?.aliases_zh ?? []) expect(mentionsName(NEWCOMER.guide_town_zh, alias, names)).toBe(false);
  });

  it("完整名字：「婆婆」不會配到「找渡婆婆」；前後是動詞、助詞、標點才算", () => {
    expect(mentionsName("找渡婆婆", "渡婆婆")).toBe(true);
    expect(mentionsName("到霧渡鎮找渡婆婆", "渡婆婆")).toBe(true);
    expect(mentionsName("找「渡婆婆」說話", "渡婆婆")).toBe(true);
    expect(mentionsName("找渡婆婆說話", "渡婆婆")).toBe(true);
    expect(mentionsName("找渡婆婆", "婆婆")).toBe(false);
    expect(mentionsName("找渡婆婆", "婆婆", ["渡婆婆"])).toBe(false);
    expect(mentionsName("找婆婆", "婆婆", ["渡婆婆"])).toBe(true);
    expect(mentionsName("找渡婆婆們", "渡婆婆")).toBe(false);
    expect(mentionsName("找渡婆婆", "")).toBe(false);
  });

  it("反例：地圖上的「婆婆」有任務「！」、渡婆婆沒有時，指引「找渡婆婆」不會認「婆婆」當主線", () => {
    const field = { npcs: [npc("old_wife", "婆婆", "quest"), npc("granny_du", "渡婆婆", null)], friends: [], situation_objects: [] } as unknown as FieldView;
    expect(mainQuestNpc(guide("找渡婆婆"), field)).toBeNull();
    const both = { npcs: [npc("old_wife", "婆婆", "quest"), npc("granny_du", "渡婆婆", "quest")], friends: [], situation_objects: [] } as unknown as FieldView;
    expect(mainQuestNpc(guide("找渡婆婆"), both)).toBe("granny_du");
    expect(mainQuestNpc(guide("找婆婆"), both)).toBe("old_wife");
    // 渡婆婆不在這張地圖上也一樣（前一個字是「渡」）
    const alone = { npcs: [npc("old_wife", "婆婆", "quest")], friends: [], situation_objects: [] } as unknown as FieldView;
    expect(mainQuestNpc(guide("找渡婆婆"), alone)).toBeNull();
  });
});

// --- 原 rt5d.test.ts ---
describe("原 rt5d.test.ts", () => {
// Phase RT-5d：主城開場第三次驗收修正（docs/archive/art/RT-5c檢查.md）。半坐起的手撐在地上、醒來時不握武器。

type M = [number, number, number, number, number, number];
const mul = (m: M, n: M): M => [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3], m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]];
const apply = (m: M, x: number, y: number): [number, number] => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];

/** 追蹤畫布變換的假 context：記下近側手（`translate(4.6,-24)` 之後的原點）與遠側手（半徑 1.7 的點）在插圖座標的位置。 */
function trace(draw: (ctx: CanvasRenderingContext2D) => void): { near: [number, number][]; far: [number, number][]; calls: string[] } {
  let m: M = [1, 0, 0, 1, 0, 0];
  const stack: M[] = [];
  const near: [number, number][] = [];
  const far: [number, number][] = [];
  const calls: string[] = [];
  const target: Record<string, unknown> = {};
  const fns: Record<string, (...a: number[]) => void> = {
    save: () => stack.push(m),
    restore: () => {
      m = stack.pop() ?? m;
    },
    translate: (x, y) => {
      m = mul(m, [1, 0, 0, 1, x, y]);
      if (Math.abs(x - 4.6) < 1e-9 && Math.abs(y + 24) < 1e-9) near.push(apply(m, 0, 0));
    },
    rotate: (a) => {
      m = mul(m, [Math.cos(a), Math.sin(a), -Math.sin(a), Math.cos(a), 0, 0]);
    },
    scale: (x, y) => {
      m = mul(m, [x, 0, 0, y, 0, 0]);
    },
    ellipse: (x, y, rx, ry) => {
      if (Math.abs(x - 5.6) < 1e-9 && Math.abs(y + 27) < 1e-9 && rx === 1.7 && ry === 1.7) far.push(apply(m, x, y));
    },
  };
  const ctx = new Proxy(target, {
    get(t, k) {
      if (typeof k === "symbol") return undefined;
      if (k in t) return t[k];
      if (k === "createLinearGradient" || k === "createRadialGradient" || k === "createPattern") return () => ({ addColorStop: () => undefined });
      if (k === "measureText") return () => ({ width: 10 });
      return (...args: number[]) => {
        calls.push(String(k));
        fns[k]?.(...args);
      };
    },
    set(t, k, v) {
      if (typeof k === "string") t[k] = v;
      return true;
    },
  });
  draw(ctx as unknown as CanvasRenderingContext2D);
  return { near, far, calls };
}

const armed = (): DollSpec => {
  const hero = heroDoll(null);
  return { ...hero, gear: { ...hero.gear, main_hand: { kind: "sword" }, off_hand: { kind: "shield_round" } } };
};

describe("RT-5d 必修 1：半坐起是兩手在髖後撐地", () => {
  it("醒來時先把武器收起來：主手、副手都不畫（躺著、坐起兩格都是）", () => {
    const spec = awakenHeroSpec(armed());
    expect(spec.gear.main_hand).toBeUndefined();
    expect(spec.gear.off_hand).toBeUndefined();
    // 其他裝備不動
    expect(spec.look).toEqual(armed().look);
    // 實際畫出來：有武器的主角和空手的主角，兩格的指令流都一樣（武器沒有畫）
    const gear = { ...armed().gear };
    delete gear.main_hand;
    delete gear.off_hand;
    const bare: DollSpec = { ...armed(), gear };
    for (const pose of [0, 1] as const) expect(trace((c) => drawAwakenArt(c, armed(), pose, [], "")).calls).toEqual(trace((c) => drawAwakenArt(c, bare, pose, [], "")).calls);
  });

  it("上半身往後仰 30～35°", () => {
    const deg = (-(AWAKEN_SIT_POSE.lean ?? 0) * 180) / Math.PI;
    expect(deg).toBeGreaterThanOrEqual(30);
    expect(deg).toBeLessThanOrEqual(35);
  });

  it("兩手都在髖部後方，手掌（手的下緣）落在地面線上（容差 1.5）；手臂打直（手肘不彎）", () => {
    const sit = AWAKEN_HERO[1];
    const { near, far } = trace((c) => drawAwakenArt(c, heroDoll(null), 1, [], ""));
    expect(near).toHaveLength(1);
    expect(far).toHaveLength(1);
    const ground = sit.y; // 坐著時原點＝髖部正下方的地面
    const palm = 1.8 * 1.05; // 手的半徑（紙娃娃 1.8，插圖放大 1.05）
    for (const [x, y] of [near[0]!, far[0]!]) {
      expect(x).toBeLessThan(sit.x - 4); // 髖部後方（主角面向東，後方＝西）
      expect(Math.abs(y + palm - ground)).toBeLessThanOrEqual(1.5);
    }
    expect(AWAKEN_SIT_POSE.elbow ?? 0).toBe(0);
    expect(AWAKEN_SIT_POSE.elbowF ?? 0).toBe(0);
    // 遠側的手在更後面一點（從近側的手後面露出來）
    expect(far[0]![0]).toBeLessThan(near[0]![0]);
  });
});

describe("RT-5d 必修 2：開發用的鏡頭位移（拍 1600 寬的夾邊畫面）", () => {
  it("只在 `?dev=1` 時有效；格式不對或 0,0 時不位移", () => {
    expect(devCameraShift("?dev=1&devcam=0,260")).toEqual({ x: 0, y: 260 });
    expect(devCameraShift("?dev=1&devcam=-40,12.5")).toEqual({ x: -40, y: 12.5 });
    expect(devCameraShift("?devcam=0,260")).toBeNull();
    expect(devCameraShift("?dev=0&devcam=0,260")).toBeNull();
    expect(devCameraShift("?dev=1")).toBeNull();
    expect(devCameraShift("?dev=1&devcam=0,0")).toBeNull();
    expect(devCameraShift("?dev=1&devcam=abc")).toBeNull();
    expect(devCameraShift("?dev=1&devcam=1,2,3")).toBeNull();
  });

  it("位移加在鏡頭上；沒位移時原樣回傳", () => {
    const cam = { x: 134, y: 465, scale: 1 };
    expect(shiftCamera(cam, null)).toBe(cam);
    expect(shiftCamera(cam, { x: 0, y: 260 })).toEqual({ x: 134, y: 725, scale: 1 });
  });
});

// 1600×900 主角站在西邊（rt5c_7 那一幀）時實機量到的鏡頭微調輸入（舞台 1568×832）
const R = (l: number, t: number, w: number, h: number, weight?: number): NudgeTarget => ({ left: l, top: t, width: w, height: h, ...(weight === undefined ? {} : { weight }) });
const WEST = {
  cam: { x: 0, y: 284.75, scale: 1 },
  view: { width: 1568, height: 832 },
  content: { width: 1536, height: 1180 },
  insets: { top: 220, right: 222.5, bottom: 77.5, left: 0 },
  reach: { top: 12, right: 222.5, bottom: 127.5, left: 0 },
  avoid: [R(10, 10, 313, 93), R(10, 123, 188, 98), R(10, 228, 45, 45), R(1346, 10, 213, 30), R(1346, 45, 213, 130), R(1346, 180, 213, 38), R(1346, 223, 213, 30), R(1346, 458, 213, 188), R(548, 755, 473, 70), R(423, 715, 721, 30)],
  hero: R(96, 700, 48, 96),
};
const MAIN = [R(672, 556, 48, 96, 3)];
const STONES = [R(1422.5, 257, 105.5, 203), R(728, 1025, 100, 155), R(8, 655, 84.5, 189), R(440, 10, 153.5, 114), R(1374.5, 1025, 105.5, 155)];
const BODIES = [R(1448, 298, 32, 66, 3), R(776, 1066, 32, 66, 3), R(56, 682, 32, 66, 3), R(536, 58, 32, 66, 3), R(1400, 1066, 32, 66, 3)];
const ASH = BODIES[1]!;

describe("RT-5d 小修 3：碑身露出一部分、被下方 HUD 蓋住時，鏡頭優先往上推（可以超過 2 格）", () => {
  it("主角在西邊：荒原碑身整個露出來（不再被快捷列、說明列蓋住），主角也沒被蓋", () => {
    const cam = nudgeCamera({ ...WEST, targets: [...MAIN, ...STONES, ...BODIES.map((b) => ({ ...b, far: true }))] });
    expect(clearOfHud(ASH, cam, WEST.view, WEST.avoid)).toBe(true);
    expect(clearOfHud(WEST.hero, cam, WEST.view, WEST.avoid)).toBe(true);
    expect(cam.y - WEST.cam.y).toBeGreaterThan(NUDGE_MAX);
    expect(cam.y - WEST.cam.y).toBeLessThanOrEqual(NUDGE_FAR);
    expect(cam.x).toBe(WEST.cam.x);
  });

  it("沒標 `far` 的目標照舊最多 2 格（RT-5c 的行為：荒原碑身推不出來）", () => {
    const cam = nudgeCamera({ ...WEST, targets: [...MAIN, ...STONES, ...BODIES] });
    expect(Math.abs(cam.y - WEST.cam.y)).toBeLessThanOrEqual(NUDGE_MAX);
    expect(clearOfHud(ASH, cam, WEST.view, WEST.avoid)).toBe(false);
  });
});

describe("RT-5d 小修 4：說明列也盡量不壓源晶燈的柱身", () => {
  const cap = { left: 665, top: 725, width: 270, height: 21 };
  const hud = [R(548, 755, 473, 70), cap];
  const lamp = R(797, 680, 22, 68);
  it("壓到燈柱時挪開（挪得少的那邊），挪過去也不壓燈柱", () => {
    const dx = captionShiftDecor(cap, [], [lamp], hud, 1568);
    expect(dx).not.toBe(0);
    const moved = { ...cap, left: cap.left + dx };
    expect(moved.left + moved.width <= lamp.left || moved.left >= lamp.left + lamp.width).toBe(true);
    expect(Math.abs(dx)).toBeLessThan(170);
  });

  it("沒壓到東西就不挪；兩邊都讓不開燈柱時，退回只避開碑身", () => {
    expect(captionShiftDecor(cap, [], [R(100, 100, 20, 60)], hud, 1568)).toBe(0);
    // 一整排燈柱擋住說明列可以去的地方（讓不開），碑身也壓在說明列下面：只避開碑身
    const body = R(700, 700, 32, 66);
    const lamps = [R(4, 690, 1560, 68)];
    const dx = captionShiftDecor(cap, [body], lamps, hud, 1568);
    const moved = { ...cap, left: cap.left + dx };
    expect(dx).not.toBe(0);
    expect(moved.left + moved.width <= body.left || moved.left >= body.left + body.width).toBe(true);
  });
});
});
