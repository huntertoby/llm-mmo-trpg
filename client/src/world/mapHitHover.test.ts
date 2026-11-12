// FIX-ATLAS1（使用者：「荒原 怎麼有個圖跑不出來」）：大世界圖滑過鎖住的灰燼荒原，說明卡下面多一塊 #36364a 的實心圓角框。
// 根因：浮島、傳送鈕、區域圖的地點／任務／傳送石都是 <button class="… map-hit">（透明點擊區，外觀畫在畫布上），
// 共用的 `button:hover:not(:disabled)`（base.css，特異度 0,2,1）贏過 `.map-hit { background: transparent }`（0,1,0），
// 沒有自己滑過樣式的點擊區（鎖住／之後的賽季的浮島、地點、任務、未啟用的傳送石）滑過就整塊塗成深灰。
// 這裡掃 client/src 所有 CSS 的 :hover 規則，用和瀏覽器同樣的比對（簡化版）鎖住：
//  1. 任何點擊區都不吃「沒有指名任何 class」的共用滑過底色；
//  2. 不能點的點擊區（鎖住、之後的賽季、地點、任務、未啟用傳送石）滑過時沒有任何規則塗底色。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AtlasRegionView, AtlasView, WorldMapView } from "../api/types";
import { readStyleFiles, stripCssComments } from "../test/sourceScan";
import { AtlasMap } from "./AtlasMap";

/** 點擊區可能的祖先（WorldScreen → 區域圖／大世界圖外框 → MapStage）。祖先選擇器只認這些 class。 */
const ANCESTOR_CLASSES = new Set([
  "world-layout",
  "world-hud-stage",
  "region-map-backdrop",
  "region-map",
  "atlas-map",
  "can-teleport",
  "map-stage-box",
  "region-map-canvas",
  "atlas-canvas",
  "map-stage",
  "map-stage-hits",
]);

interface Hit {
  classes: ReadonlySet<string>;
  disabled: boolean;
}

/** 頂層逗號切開（括號內的不切）。 */
function splitTop(s: string, sep: (ch: string) => boolean): string[] {
  const out: string[] = [];
  let depth = 0;
  let cur = "";
  for (const ch of s) {
    if (ch === "(") depth += 1;
    if (ch === ")") depth -= 1;
    if (depth === 0 && sep(ch)) {
      if (cur.trim() !== "") out.push(cur.trim());
      cur = "";
    } else cur += ch;
  }
  if (cur.trim() !== "") out.push(cur.trim());
  return out;
}

/** 單一複合選擇器（沒有組合子）是否命中（`:hover` 一律視為成立）。看不懂的偽類一律當不命中。 */
function compoundMatches(compound: string, el: { tag: string; classes: ReadonlySet<string>; disabled: boolean }): boolean {
  let rest = compound;
  const tag = /^([a-z*][a-z0-9]*)/i.exec(rest);
  if (tag !== null) {
    if (tag[1] !== "*" && tag[1] !== el.tag) return false;
    rest = rest.slice(tag[1].length);
  }
  while (rest !== "") {
    let m: RegExpExecArray | null;
    if ((m = /^\.([\w-]+)/.exec(rest)) !== null) {
      if (!el.classes.has(m[1] ?? "")) return false;
    } else if ((m = /^:hover/.exec(rest)) !== null) {
      // 滑過中
    } else if ((m = /^:disabled/.exec(rest)) !== null) {
      if (!el.disabled) return false;
    } else if ((m = /^:not\(((?:[^()]|\([^()]*\))*)\)/.exec(rest)) !== null) {
      if (splitTop(m[1] ?? "", (c) => c === ",").some((arg) => compoundMatches(arg, el))) return false;
    } else {
      return false; // 屬性選擇器、其他偽類：保守當不命中
    }
    rest = rest.slice(m[0].length);
  }
  return true;
}

/** 選擇器命中這個點擊區（滑過中）嗎：最後一段要命中點擊區，前面的祖先段只能用 ANCESTOR_CLASSES 裡的 class。 */
function selectorHitsWhileHover(selector: string, hit: Hit): boolean {
  if (!selector.includes(":hover")) return false;
  const parts = splitTop(selector, (c) => c === " " || c === ">" || c === "+" || c === "~");
  const last = parts.pop();
  if (last === undefined || !compoundMatches(last, { tag: "button", ...hit })) return false;
  return parts.every((p) => {
    const cls = [...p.matchAll(/\.([\w-]+)/g)].map((m) => m[1] ?? "");
    return /^(div|\*)?(\.[\w-]+)*$/.test(p) && cls.every((c) => ANCESTOR_CLASSES.has(c));
  });
}

interface HoverRule {
  file: string;
  selector: string;
  /** 最後一段有沒有指名任何 class（沒有＝共用的全域規則）。 */
  generic: boolean;
}

/** 所有會塗底色的 :hover 規則（最內層的 `選擇器 { 宣告 }`，@media 裡的也算）。 */
function hoverBackgroundRules(): HoverRule[] {
  const out: HoverRule[] = [];
  for (const [file, raw] of readStyleFiles()) {
    const css = stripCssComments(raw);
    for (const m of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      if (!/(^|[\s;])background(-color)?\s*:/.test(m[2] ?? "")) continue;
      for (const selector of splitTop(m[1] ?? "", (c) => c === ",")) {
        if (!selector.includes(":hover")) continue;
        const last = splitTop(selector, (c) => c === " " || c === ">" || c === "+" || c === "~").pop() ?? "";
        out.push({ file, selector, generic: !/\.[\w-]/.test(last.replace(/:not\([^)]*\)/g, "")) });
      }
    }
  }
  return out;
}

function region(over: Partial<AtlasRegionView> & { region: string; name_zh: string }): AtlasRegionView {
  return { status: "open", condition_zh: null, town: null, town_name_zh: null, current: false, can_teleport: false, free: false, ...over };
}

function map(regionId: string): WorldMapView {
  return { region: regionId, name_zh: regionId, level_zh: "", locations: [], edges: [], stones: [], can_teleport: false, hub: regionId === "capital" };
}

const ATLAS: AtlasView = {
  regions: [
    region({ region: "cloud_ridge", name_zh: "雲嶺", town: "mist_ferry", town_name_zh: "霧渡鎮", can_teleport: true, free: true }),
    region({ region: "crystal_crown", name_zh: "晶冠城邦", status: "later", condition_zh: "之後的賽季" }),
    region({ region: "arcane_hub", name_zh: "魔導樞市", status: "later", condition_zh: "之後的賽季" }),
    region({ region: "ashen_waste", name_zh: "灰燼荒原", status: "locked", condition_zh: "世界事件：霧潮入侵", town: "ember_market", town_name_zh: "餘燼集" }),
    region({ region: "frost_tide", name_zh: "霜潮海境", status: "later", condition_zh: "之後的賽季" }),
  ],
  capital: region({ region: "capital", name_zh: "主城", town: "capital", town_name_zh: "樞島", current: true }),
  can_teleport: true,
  teleport_problem_zh: null,
  art_url: null,
  maps: [map("cloud_ridge")],
};

/** 大世界圖實際畫出來的所有點擊區（含傳送鈕），busy 時傳送鈕是 disabled。 */
function atlasHits(busy: boolean): { testId: string; hit: Hit }[] {
  const html = renderToStaticMarkup(
    createElement(AtlasMap, { atlas: ATLAS, map: map("capital"), busy, onOpenRegion: () => {}, onTeleport: () => {}, onClose: () => {} }),
  );
  return [...html.matchAll(/<button\b[^>]*>/g)]
    .map((m) => m[0])
    .filter((tag) => /class="[^"]*\bmap-hit\b/.test(tag))
    .map((tag) => ({
      testId: /data-testid="([^"]+)"/.exec(tag)?.[1] ?? "?",
      hit: { classes: new Set((/class="([^"]*)"/.exec(tag)?.[1] ?? "").split(/\s+/)), disabled: /\sdisabled(=|\s|>)/.test(tag) },
    }));
}

/** 區域圖的點擊區（RegionMap.tsx 的 class 組法）：地點、城鎮、任務、各狀態的傳送石。 */
const REGION_HITS: { testId: string; hit: Hit }[] = ([
  ["region-node", "region-node map-hit visited"],
  ["region-node-fog", "region-node map-hit fog"],
  ["region-node-silhouette", "region-node map-hit silhouette"],
  ["region-node-town-here", "region-node map-hit visited town current"],
  ["region-quest", "region-quest map-hit"],
  ["region-stone-here", "region-stone map-hit here"],
  ["region-stone-view", "region-stone map-hit view"],
  ["region-stone-locked", "region-stone map-hit locked"],
] as const).map(([testId, cls]) => ({ testId, hit: { classes: new Set(cls.split(" ")), disabled: false } }));

describe("FIX-ATLAS1：地圖透明點擊區滑過不畫實心框", () => {
  const rules = hoverBackgroundRules();

  it("掃得到規則（防掃描失效）：共用 button 滑過、可開浮島、傳送鈕的滑過底色", () => {
    const sels = rules.map((r) => r.selector);
    expect(sels).toContain("button:hover:not(:disabled, .map-hit)");
    expect(sels).toContain(".atlas-island.openable:hover");
    expect(sels).toContain(".atlas-town.go:hover");
  });

  it("大世界圖畫出鎖住、之後的賽季、可開的浮島與傳送鈕，都是 map-hit", () => {
    const ids = atlasHits(false).map((h) => h.testId);
    expect(ids).toEqual(
      expect.arrayContaining(["atlas-ashen_waste", "atlas-crystal_crown", "atlas-cloud_ridge", "atlas-capital", "atlas-teleport-cloud_ridge"]),
    );
    const ashen = atlasHits(false).find((h) => h.testId === "atlas-ashen_waste");
    expect([...(ashen?.hit.classes ?? [])]).toEqual(expect.arrayContaining(["atlas-island", "map-hit", "locked"]));
    expect(ashen?.hit.classes.has("openable")).toBe(false);
  });

  it("任何點擊區（含 busy 時的傳送鈕）都不吃沒指名 class 的共用滑過底色", () => {
    const hits = [...atlasHits(false), ...atlasHits(true), ...REGION_HITS];
    const bad = hits.flatMap(({ testId, hit }) =>
      rules.filter((r) => r.generic && selectorHitsWhileHover(r.selector, hit)).map((r) => `${testId} ← ${r.file}: ${r.selector}`),
    );
    expect(bad).toEqual([]);
  });

  it("不能點的點擊區（鎖住／之後的賽季浮島、地點、任務、未啟用傳送石）滑過時沒有任何規則塗底色", () => {
    const passive = [...atlasHits(false).filter((h) => h.testId.startsWith("atlas-") && !h.hit.classes.has("openable") && !h.hit.classes.has("go")), ...REGION_HITS];
    expect(passive.map((h) => h.testId)).toEqual(expect.arrayContaining(["atlas-ashen_waste", "atlas-crystal_crown", "atlas-arcane_hub", "atlas-frost_tide"]));
    const bad = passive.flatMap(({ testId, hit }) => rules.filter((r) => selectorHitsWhileHover(r.selector, hit)).map((r) => `${testId} ← ${r.file}: ${r.selector}`));
    expect(bad).toEqual([]);
  });

  it("可開的浮島與傳送鈕仍有自己的滑過底色（修法沒有把它們一起拿掉）", () => {
    const hits = atlasHits(false);
    const open = hits.find((h) => h.testId === "atlas-cloud_ridge");
    const tp = hits.find((h) => h.testId === "atlas-teleport-cloud_ridge");
    expect(open !== undefined && rules.some((r) => selectorHitsWhileHover(r.selector, open.hit))).toBe(true);
    expect(tp !== undefined && rules.some((r) => selectorHitsWhileHover(r.selector, tp.hit))).toBe(true);
  });
});

/** 所有規則（最內層的 `選擇器 { 宣告 }`），拆成單一選擇器。 */
function allRules(): { file: string; selector: string; body: string }[] {
  const out: { file: string; selector: string; body: string }[] = [];
  for (const [file, raw] of readStyleFiles()) {
    const css = stripCssComments(raw);
    for (const m of css.matchAll(/([^{}]+)\{([^{}]*)\}/g))
      for (const selector of splitTop(m[1] ?? "", (c) => c === ",")) out.push({ file, selector: selector.trim(), body: m[2] ?? "" });
  }
  return out;
}

/** 不管滑過與否，選擇器命中這個點擊區嗎（`:hover` 視為成立；祖先段同 selectorHitsWhileHover）。 */
function selectorHits(selector: string, hit: Hit): boolean {
  const parts = splitTop(selector, (c) => c === " " || c === ">" || c === "+" || c === "~");
  const last = parts.pop();
  if (last === undefined || !compoundMatches(last, { tag: "button", ...hit })) return false;
  return parts.every((p) => {
    const cls = [...p.matchAll(/\.([\w-]+)/g)].map((m) => m[1] ?? "");
    return /^(div|\*)?(\.[\w-]+)*$/.test(p) && cls.every((c) => ANCESTOR_CLASSES.has(c));
  });
}

describe("FIX-ATLAS2：鎖住浮島滑過不用「能去」的語言", () => {
  const rules = allRules();
  const hits = atlasHits(false);
  const locked = hits.filter((h) => h.hit.classes.has("atlas-island") && !h.hit.classes.has("openable") && !h.hit.classes.has("capital"));
  const LOUD = /(^|[\s;])(background(-color)?|box-shadow|transform|scale|filter|outline|border(-color)?)\s*:/;

  it("鎖住／之後的賽季浮島：滑過時沒有任何 CSS 規則加底色、光暈、放大、濾鏡、框（亮一點畫在畫布上）", () => {
    expect(locked.map((h) => h.testId).sort()).toEqual(["atlas-arcane_hub", "atlas-ashen_waste", "atlas-crystal_crown", "atlas-frost_tide"]);
    const bad = locked.flatMap(({ testId, hit }) =>
      rules.filter((r) => r.selector.includes(":hover") && LOUD.test(r.body) && selectorHits(r.selector, hit)).map((r) => `${testId} ← ${r.file}: ${r.selector}`),
    );
    expect(bad).toEqual([]);
  });

  it("鎖住浮島游標維持 default（命中的 cursor 宣告裡特異度最高的是 .map-hit 的 default，不是手指）", () => {
    // 特異度（簡化）：class 與偽類算一級、標籤算一級；:not(…) 取參數裡最高的一個（同 CSS 規範）
    const spec = (sel: string): number => {
      let s = sel;
      let best = 0;
      for (const m of sel.matchAll(/:not\(((?:[^()]|\([^()]*\))*)\)/g)) best = Math.max(best, ...splitTop(m[1] ?? "", (c) => c === ",").map(spec));
      s = s.replace(/:not\(((?:[^()]|\([^()]*\))*)\)/g, "");
      const b = (s.match(/\.[\w-]+|:[\w-]+/g) ?? []).length;
      const c = (s.match(/(^|[\s>+~])[a-z]+/gi) ?? []).length;
      return best + b * 100 + c;
    };
    for (const { testId, hit } of locked) {
      const decl = rules
        .map((r, i) => ({ ...r, i }))
        .filter((r) => /(^|[\s;])cursor\s*:/.test(r.body) && selectorHits(r.selector, hit))
        .sort((a, b) => spec(b.selector) - spec(a.selector) || b.i - a.i);
      expect(decl.length, testId).toBeGreaterThan(0);
      expect(/cursor\s*:\s*([^;]+)/.exec(decl[0]!.body)?.[1]?.trim(), `${testId} ← ${decl[0]!.selector}`).toBe("default");
      expect(decl.filter((r) => r.selector.includes(":hover")), testId).toEqual([]); // 滑過時不換游標
    }
  });

  it("解鎖浮島滑過效果逐字不變：.atlas-island.openable:hover 的底色、.atlas-island.openable 的手指游標", () => {
    const body = (sel: string) => rules.find((r) => r.selector === sel)?.body.replace(/\s+/g, " ").trim();
    expect(body(".atlas-island.openable:hover")).toBe("background: rgba(255, 240, 200, 0.12);");
    expect(body(".atlas-island.openable")).toBe("cursor: pointer; border-radius: 50%;");
  });
});
