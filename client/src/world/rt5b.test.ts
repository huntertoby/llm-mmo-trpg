// Phase RT-5b：主城開場的驗收修正（docs/art/RT-5檢查.md）。石碑小牌與重要的人避開 HUD、守印人泡泡收起與展開、
// 主線「！」突出、浮動卡換行、醒來插圖、斷橋、守印人站位與南側石碑對齊、任務欄文字。
import capitalYaml from "../../../content/world/fields/capital/capital.yaml?raw";
import newcomerYaml from "../../../content/world/newcomer.yaml?raw";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import type { FieldView } from "../api/types";
import { BRIDGE_BREAK_Y, BRIDGE_PLANKS, drawSkyBridge } from "../render/capitalArt";
import { AWAKEN_BANNERS, AWAKEN_HERO, AWAKEN_RING } from "../render/eventArtAwaken";
import { T } from "../render/eventArtParts";
import { FieldHeads, FieldSteleTags } from "./FieldHeads";
import { headMarks } from "./fieldPeople";
import { hudLayout } from "./hud";
import { captionRect, clearOfHud, hudAvoidRects, hudReach, nudgeCamera, placeTag, tagSize } from "./hudAvoid";
import { GUIDE_BUBBLE_MS, guideAnchor, mainQuestNpc } from "./opening";

type Spot = { id: string; at: [number, number]; figure?: { facing?: string } };
type Obj = { at: [number, number]; kind: string; look?: string };
const CAPITAL = parse(capitalYaml) as { situation_objects: Spot[]; objects: Obj[]; teleport_stones: { at: [number, number] }[]; entry: [number, number]; terrain: string };
const NEWCOMER = parse(newcomerYaml) as { guide_town_zh: string };

const VIEW = { width: 1568, height: 832 };
const LAYOUT = hudLayout(VIEW.width, VIEW.height, { mates: 2, narrow: false, collapsed: false });

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

describe("RT-5b 必修 1、2：石碑小牌與重要的人避開 HUD", () => {
  const avoid = hudAvoidRects(LAYOUT, VIEW);

  it("要避開的 HUD 有右上的小地圖、金幣欄、底部的功能列與說明列（說明列疊在功能列上方中央）", () => {
    const ids = ["hero", "mates", "place", "minimap", "clock", "wallet", "tracker", "bar"] as const;
    for (const id of ids) expect(avoid).toContainEqual(LAYOUT.blocks[id]);
    const cap = captionRect(VIEW, LAYOUT.scale);
    expect(avoid).toContainEqual(cap);
    expect(cap.top + cap.height).toBeLessThanOrEqual(LAYOUT.blocks.bar.top);
    // 地圖下緣微調時可以捲到說明列上面
    expect(hudReach(LAYOUT, VIEW).bottom).toBeGreaterThan(VIEW.height - LAYOUT.blocks.bar.top);
  });

  it("小牌預設在石碑上方；壓到右上的金幣欄時換到石碑左邊；壓到下方功能列時抬到說明列上面；都放不下就不畫", () => {
    const size = tagSize("魔導樞市", "之後的賽季");
    const cam = { x: 0, y: 0 };
    const wallet = LAYOUT.blocks.wallet;
    // 石碑在畫面中央：照預設放上方
    const mid = { left: 700, top: 400, width: 32, height: 66 };
    expect(placeTag(mid, size, cam, VIEW, avoid).side).toBe("n");
    // 石碑就在金幣欄正下方、靠右欄的左緣：上方會壓到金幣欄 → 換位置，而且不壓 HUD
    const east = { left: wallet.left - 40, top: wallet.top + wallet.height + 8, width: 32, height: 66 };
    const at = placeTag(east, size, cam, VIEW, avoid);
    expect(at.left + size.width).toBeLessThanOrEqual(wallet.left);
    expect(clearOfHud({ left: at.left, top: at.top, ...size }, cam, VIEW, avoid)).toBe(true);
    // 石碑被功能列蓋住：小牌抬到說明列上面
    const bar = LAYOUT.blocks.bar;
    const south = { left: bar.left + bar.width / 2 - 16, top: bar.top + 4, width: 32, height: 66 };
    const lifted = placeTag(south, size, cam, VIEW, avoid);
    expect(lifted.side).toBe("lift");
    expect(lifted.top + size.height).toBeLessThanOrEqual(captionRect(VIEW, LAYOUT.scale).top);
    // 石碑整個在功能列底下更下面（抬超過 2 格）：不畫，也不壓在 HUD 上
    const deep = { ...south, top: VIEW.height - 10 };
    expect(placeTag(deep, size, cam, VIEW, avoid).side).toBe("hidden");
    // 沒有 HUD（不是 HUD 版面）照預設
    expect(placeTag(east, size, null, null, []).side).toBe("n");
  });

  it("鏡頭微調：露出一部分的石碑整個露出來，主角不被蓋住，最多移 2 格；完全在畫面外的不拉鏡頭；同樣輸入同樣結果", () => {
    const insets = { top: 300, right: VIEW.width - LAYOUT.blocks.minimap.left, bottom: VIEW.height - LAYOUT.blocks.bar.top, left: 0 };
    const content = { width: 1536, height: 1180 };
    const cam = { x: 111, y: 100, scale: 1 };
    const hero = { left: 768, top: 520, width: 48, height: 76 };
    // 東側石碑（含上方小牌）一半在右欄底下
    const wallet = LAYOUT.blocks.wallet;
    const stele = { left: wallet.left + cam.x - 30, top: wallet.top + cam.y - 5, width: 83, height: 110 };
    expect(clearOfHud(stele, cam, VIEW, hudAvoidRects(LAYOUT, VIEW))).toBe(false);
    const input = { cam, view: VIEW, content, insets, avoid: hudAvoidRects(LAYOUT, VIEW), hero, targets: [stele] };
    const moved = nudgeCamera(input);
    expect(moved).not.toEqual(cam);
    expect(Math.abs(moved.x - cam.x) + Math.abs(moved.y - cam.y)).toBeLessThanOrEqual(96 * 2);
    expect(clearOfHud(stele, moved, VIEW, input.avoid)).toBe(true);
    expect(clearOfHud(hero, moved, VIEW, input.avoid)).toBe(true);
    expect(nudgeCamera(input)).toEqual(moved);
    // 在畫面外的東西不拉鏡頭
    expect(nudgeCamera({ ...input, targets: [{ ...stele, left: 5000 }] })).toBe(cam);
    // 都已經露出來：不動
    expect(nudgeCamera({ ...input, targets: [{ left: 600, top: 400, width: 40, height: 60 }] })).toBe(cam);
  });

  it("石碑小牌畫出來時帶 data-side（給截圖與煙霧檢查看）", () => {
    const html = renderToStaticMarkup(
      createElement(FieldSteleTags, {
        tags: [{ id: "stele_arcane_hub", region: "arcane_hub", x: 30, y: 6, name: "魔導樞市", status: "later", sub: "之後的賽季" }],
        grid: { width: 32, height: 24, tiles: [] } as never,
        scale: 1,
        colors: {},
        cam: { x: 0, y: 0 },
        view: VIEW,
        avoid: hudAvoidRects(LAYOUT, VIEW),
      }),
    );
    expect(html).toMatch(/data-side="(n|w|e|s|lift|hidden)"/);
  });
});

describe("RT-5b 必修 6：守印人的泡泡", () => {
  const field = { npcs: [], friends: [] } as unknown as FieldView;
  const guides = new Map([["seal_keeper", { name: "守印人", text: "新來的？雲嶺那邊缺人手。站上傳送陣，去霧渡鎮找渡婆婆。", x: 14, y: 12 }]]);

  it("整句留約 8 秒；收起來只剩「！」（沒有泡泡、標記 folded），「！」照樣在、是主線樣式", () => {
    expect(GUIDE_BUBBLE_MS).toBe(8000);
    const open = headMarks(field, new Map(), guides)[0]!;
    expect(open).toMatchObject({ folded: false, main: true, alert: "quest" });
    expect(open.bubble).toContain("霧渡鎮");
    const folded = headMarks(field, new Map(), guides, { guideFolded: true })[0]!;
    expect(folded).toMatchObject({ folded: true, bubble: null, alert: "quest", main: true });
  });

  it("收起時點「！」＝展開（onExpand），展開時點＝照舊走過去開公告板（onPick）", () => {
    const folded = headMarks(field, new Map(), guides, { guideFolded: true });
    const html = renderToStaticMarkup(createElement(FieldHeads, { marks: folded, grid: { width: 32, height: 24, tiles: [] } as never, scale: 1, onPick: () => undefined, onExpand: () => undefined }));
    expect(html).toContain('data-guide="folded"');
    expect(html).toContain("點了看指示");
    expect(html).not.toContain("field-bubble\"");
    const open = renderToStaticMarkup(createElement(FieldHeads, { marks: headMarks(field, new Map(), guides), grid: { width: 32, height: 24, tiles: [] } as never, scale: 1, onPick: () => undefined }));
    expect(open).toContain('data-guide="open"');
    expect(open).toContain("field-bubble");
  });

  it("站在傳送陣旁、上面放得下時泡泡放頭頂往左上（nw），不蓋到東邊的主角；夾到畫面邊上時往畫面中間那一邊放", () => {
    const visible = { left: 0, top: 0, right: 1600, bottom: 900 };
    expect(guideAnchor({ left: 700, top: 500 }, visible, visible).side).toBe("nw");
    expect(guideAnchor({ left: 700, top: 60 }, visible, visible).side).toBe("w");
    const box = { left: 100, top: 200, right: 700, bottom: 600 };
    expect(guideAnchor({ left: 120, top: 50 }, box)).toMatchObject({ edge: "n", side: "e" });
    expect(guideAnchor({ left: 650, top: 50 }, box)).toMatchObject({ edge: "n", side: "w" });
  });
});

describe("RT-5b 小修 10：主線「！」比支線突出；任務欄文字（玩法 PM 決定）", () => {
  const npc = (id: string, name: string, alert: "quest" | "rumor" | null) => ({ id, name_zh: name, x: 1, y: 1, alert, alert_zh: null, rank: "neutral", rank_zh: "中立" });
  const ferry = { npcs: [npc("granny_du", "渡婆婆", "quest"), npc("shopkeeper_liu", "柳掌櫃", "quest"), npc("gran", "葛蘭", "rumor")], friends: [] } as unknown as FieldView;

  it("任務欄是內容檔的「找渡婆婆」（拿掉「頭上有「！」的」）", () => {
    expect(NEWCOMER.guide_town_zh).toBe("找渡婆婆");
  });

  it("指引點名的那位（有任務「！」）是主線；開場（主城）、沒有指引、點名的人沒有任務「！」時沒有主線", () => {
    expect(mainQuestNpc({ text_zh: NEWCOMER.guide_town_zh, how_zh: null, opening: [] }, ferry)).toBe("granny_du");
    expect(mainQuestNpc({ text_zh: "到霧渡鎮找渡婆婆", how_zh: null, opening: [{ speaker_zh: "說書人", text_zh: "……" }] }, ferry)).toBeNull();
    expect(mainQuestNpc(null, ferry)).toBeNull();
    expect(mainQuestNpc({ text_zh: "找葛蘭", how_zh: null, opening: [] }, ferry)).toBeNull();
  });

  it("主線的「！」多一個 main 樣式，支線照舊", () => {
    const marks = headMarks(ferry, new Map(), new Map(), { main: "granny_du" });
    expect(marks.map((m) => [m.id, m.main])).toEqual([
      ["granny_du", true],
      ["shopkeeper_liu", false],
      ["gran", false],
    ]);
    const html = renderToStaticMarkup(createElement(FieldHeads, { marks, grid: { width: 32, height: 24, tiles: [] } as never, scale: 1, onPick: () => undefined }));
    expect(html.match(/field-alert quest main/g)).toHaveLength(1);
    expect(html.match(/field-alert quest"/g)).toHaveLength(1);
    expect(html.match(/field-alert rumor"/g)).toHaveLength(1);
  });
});

describe("RT-5b 必修 4、7：醒來插圖與斷橋", () => {
  it("主角在晶柱右側（頭不壓晶柱），半坐起的角度比 RT-5 小；晶冠的旗桿在遠處建築（4.2～5.7 格）左邊", () => {
    for (const pose of [0, 1] as const) expect(AWAKEN_HERO[pose].x - AWAKEN_RING.x).toBeGreaterThan(60);
    expect(Math.abs(AWAKEN_HERO[1].rot)).toBeLessThan(0.6);
    expect(Math.abs(AWAKEN_HERO[1].rot)).toBeGreaterThan(0.2);
    const [bx] = AWAKEN_BANNERS.crystal_crown;
    const poleX = bx * T + 24; // drawBanner：旗桿在畫布中央（U/2），旗面往右 20
    expect(poleX + 20).toBeLessThan(4.2 * T);
  });

  it("斷口：最後一塊整板斷了一半（鋸齒）、脫落的碎板、斷繩末端散成三股；四個方向確定", () => {
    expect(BRIDGE_PLANKS.filter((p) => p === null)).toHaveLength(2);
    for (const side of ["n", "e", "s", "w"] as const) {
      const a = record((c) => drawSkyBridge(c, side, true, true));
      expect(a).toEqual(record((c) => drawSkyBridge(c, side, true, true)));
      expect(a.filter((x) => x.startsWith("quadraticCurveTo"))).toHaveLength(2);
      // 斷繩粗 2.6、深色
      expect(a).toContain("lineWidth=2.6");
      // 兩條斷繩各三股
      expect(a.filter((x) => x.startsWith("lineTo")).length).toBeGreaterThan(10);
    }
    expect(BRIDGE_BREAK_Y).toBeLessThan(0);
  });
});

describe("RT-5b 必修 8、小修 9：守印人站位與南側石碑", () => {
  const spot = (id: string) => CAPITAL.situation_objects.find((s) => s.id === id)!;
  const objAt = (x: number, y: number) => CAPITAL.objects.filter((o) => o.at[0] === x && o.at[1] === y);

  it("守印人站在傳送石旁相鄰的空格，不在傳送石、抵達點上，那一格沒有擋路的物件", () => {
    const keeper = spot("seal_keeper");
    const stone = CAPITAL.teleport_stones[0]!.at;
    expect(Math.max(Math.abs(keeper.at[0] - stone[0]), Math.abs(keeper.at[1] - stone[1]))).toBe(1);
    expect(keeper.at).not.toEqual(stone);
    expect(keeper.at).not.toEqual(CAPITAL.entry);
    expect(objAt(...keeper.at)).toEqual([]);
    expect(CAPITAL.terrain.split("\n").map((r) => r.trim())[keeper.at[1]]![keeper.at[0]]).toBe(".");
    expect(keeper.figure?.facing).toBe("e");
  });

  it("南側兩座石碑站在各自浮橋的那一欄（橋頭），石碑的物件與情境物件同一格", () => {
    for (const region of ["ashen_waste", "frost_tide"]) {
      const stele = spot(`stele_${region}`);
      const bridge = spot(`bridge_${region}`);
      const bridgeCols = CAPITAL.objects.filter((o) => o.look === "sky_bridge" && o.at[1] === bridge.at[1] && Math.abs(o.at[0] - bridge.at[0]) <= 1).map((o) => o.at[0]);
      expect(bridgeCols).toContain(stele.at[0]);
      expect(stele.at[1]).toBe(bridge.at[1] - 1);
      expect(objAt(...stele.at).map((o) => o.look)).toEqual(["stele"]);
    }
  });
});

