// 排版煙霧檢查（Phase 3-47，流程改善 D）：在瀏覽器開戰鬥畫面，量關鍵元件的位置，輸出 PASS／FAIL 表。
//
// 為什麼要有：共用說明卡 `Hint` 曾外包一層元素，讓 `父 > 子` 的 CSS 失效，先後造成拖曳線跑位、「結束回合」變直條、
// 播放列被擠掉、說明卡蓋住選單（docs/開發PM交接.md 6.5.1）；這些都是單元測試抓不到、一打開畫面就看得出來的錯。
//
// 結構：`evaluate(snapshot)` 是純函式（vitest 測它）；`collect()` 把畫面量成 `LayoutSnapshot`；
// `runCase()` 在頁面裡開一場戰鬥、量測、回傳表格。`main.tsx` 把它掛在 `window.__layoutSmoke`，
// 用內建瀏覽器（`mcp__Claude_Browser__*`）的 `javascript_tool` 呼叫；步驟見 docs/開發PM交接.md 6.2 第 5 點。
// 不需要安裝任何套件。

import { NARROW_WIDTH } from "../battle/skillTray";

export interface Box {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface LayoutSnapshot {
  viewport: { width: number; height: number };
  /** 戰鬥畫面右欄（`.turn-controls`）。 */
  turnControls: Box | null;
  /** 「結束回合」按鈕。 */
  endTurn: Box | null;
  /** 播放列（`.speed-control`）與它的按鈕。 */
  speed: Box | null;
  speedButtons: Box[];
  /** 戰場（`.battle-board`）與它底緣、右緣的拖曳線；主角狀態卡與它右緣的拖曳線。 */
  board: Box | null;
  bottomHandle: Box | null;
  sideHandle: Box | null;
  hero: Box | null;
  heroHandle: Box | null;
  /** 格子資訊卡：整張浮動卡、底部提示列、提示列背景色的不透明度（0～1）。 */
  tileCard: { float: Box; bar: Box | null; barAlpha: number } | null;
  /** 「更多動作」：選單是否開著、此時畫面上有幾張說明卡（`role=tooltip`）。 */
  moreMenu: { open: boolean; tooltips: number; hintBefore: number } | null;
  /** 畫面上多餘的說明卡外框（舊版 `Hint` 的 `.hint-tip`）數量，應為 0。 */
  hintWrappers: number;
}

export interface CheckResult {
  id: string;
  label: string;
  pass: boolean;
  detail: string;
}

/** 長度誤差容許（CSS 像素；子像素與邊框）。 */
export const TOL = 1.5;
const w = (b: Box): number => b.right - b.left;
const near = (a: number, b: number): boolean => Math.abs(a - b) <= TOL;
const fmt = (b: Box | null): string => (b === null ? "找不到" : `[${[b.left, b.top, b.right, b.bottom].map(Math.round).join(",")}]`);
const inside = (inner: Box, outer: Box): boolean =>
  inner.left >= outer.left - TOL && inner.top >= outer.top - TOL && inner.right <= outer.right + TOL && inner.bottom <= outer.bottom + TOL;

function result(id: string, label: string, pass: boolean, detail: string): CheckResult {
  return { id, label, pass, detail };
}

function endTurnWide(s: LayoutSnapshot): CheckResult {
  const label = "「結束回合」寬度 ≥ 右欄 90%";
  if (s.endTurn === null || s.turnControls === null) return result("end-turn-wide", label, false, "找不到按鈕或右欄");
  const ratio = w(s.endTurn) / Math.max(1, w(s.turnControls));
  return result("end-turn-wide", label, ratio >= 0.9, `${Math.round(w(s.endTurn))}px／${Math.round(w(s.turnControls))}px = ${Math.round(ratio * 100)}%`);
}

function speedVisible(s: LayoutSnapshot): CheckResult {
  const label = "播放列與每顆按鈕都在畫面內、沒超出播放列";
  if (s.speed === null) return result("speed-visible", label, false, "找不到播放列");
  const view: Box = { left: 0, top: 0, right: s.viewport.width, bottom: s.viewport.height };
  const spill = s.speedButtons.filter((b) => !inside(b, view) || !inside(b, s.speed as Box)).length;
  const detail = `${fmt(s.speed)} 視窗 ${s.viewport.width}×${s.viewport.height}，超出的按鈕 ${spill} 顆`;
  return result("speed-visible", label, inside(s.speed, view) && spill === 0, detail);
}

function speedOneRow(s: LayoutSnapshot): CheckResult {
  const label = "播放列一行（按鈕同高度、沒折行）";
  if (s.speedButtons.length === 0) return result("speed-one-row", label, false, "找不到播放按鈕");
  const tops = s.speedButtons.map((b) => b.top);
  const spread = Math.max(...tops) - Math.min(...tops);
  return result("speed-one-row", label, spread <= TOL, `${s.speedButtons.length} 顆按鈕，頂端落差 ${Math.round(spread)}px`);
}

function bottomHandleFlush(s: LayoutSnapshot): CheckResult {
  const label = "底部拖曳線貼齊戰場底緣";
  if (s.bottomHandle === null || s.board === null) return result("bottom-handle", label, false, "找不到拖曳線或戰場");
  const pass = near(s.bottomHandle.bottom, s.board.bottom) && near(s.bottomHandle.left, s.board.left) && near(s.bottomHandle.right, s.board.right);
  return result("bottom-handle", label, pass, `拖曳線 ${fmt(s.bottomHandle)} 戰場 ${fmt(s.board)}`);
}

function sideHandleFlush(s: LayoutSnapshot): CheckResult {
  const label = "右側拖曳線貼齊戰場右緣";
  if (s.sideHandle === null || s.board === null) return result("side-handle", label, false, "找不到拖曳線或戰場");
  const pass = near(s.sideHandle.right, s.board.right) && near(s.sideHandle.top, s.board.top) && near(s.sideHandle.bottom, s.board.bottom);
  return result("side-handle", label, pass, `拖曳線 ${fmt(s.sideHandle)} 戰場 ${fmt(s.board)}`);
}

function heroHandleFlush(s: LayoutSnapshot): CheckResult {
  const label = "主角狀態卡的拖曳線跨在卡片右緣、與卡片等高";
  if (s.heroHandle === null || s.hero === null) return result("hero-handle", label, false, "找不到拖曳線或主角狀態卡");
  const straddle = s.heroHandle.left <= s.hero.right + TOL && s.heroHandle.right >= s.hero.right - TOL;
  const pass = straddle && near(s.heroHandle.top, s.hero.top) && near(s.heroHandle.bottom, s.hero.bottom);
  return result("hero-handle", label, pass, `拖曳線 ${fmt(s.heroHandle)} 主角卡 ${fmt(s.hero)}`);
}

function tileHint(s: LayoutSnapshot): CheckResult {
  const label = "格子資訊卡的提示列在卡片底色內";
  if (s.tileCard === null) return result("tile-hint", label, false, "沒有出現格子資訊卡");
  const { float, bar, barAlpha } = s.tileCard;
  if (bar === null) return result("tile-hint", label, false, "卡片沒有提示列");
  const view: Box = { left: 0, top: 0, right: s.viewport.width, bottom: s.viewport.height };
  const pass = inside(bar, float) && barAlpha >= 0.5 && inside(float, view);
  return result("tile-hint", label, pass, `提示列 ${fmt(bar)} 卡片 ${fmt(float)} 底色不透明度 ${barAlpha.toFixed(2)}`);
}

function moreMenu(s: LayoutSnapshot): CheckResult {
  const label = "「更多動作」選單開著時沒有說明卡蓋住";
  if (s.moreMenu === null) return result("more-menu", label, false, "找不到「更多動作」或選單沒打開");
  const m = s.moreMenu;
  const pass = m.hintBefore > 0 && m.open && m.tooltips === 0;
  return result("more-menu", label, pass, `滑過時說明卡 ${m.hintBefore} 張；選單${m.open ? "開著" : "沒開"}，說明卡 ${m.tooltips} 張`);
}

function noWrapper(s: LayoutSnapshot): CheckResult {
  return result("no-hint-wrapper", "說明卡不外包元素（.hint-tip 數量 0）", s.hintWrappers === 0, `${s.hintWrappers} 個`);
}

/** 窄螢幕（視窗寬 < `NARROW_WIDTH`）不顯示拖曳線：沒有才對，不是「找不到」。 */
function handleCheck(s: LayoutSnapshot, check: (s: LayoutSnapshot) => CheckResult, handle: Box | null): CheckResult {
  const r = check(s);
  if (s.viewport.width >= NARROW_WIDTH) return r;
  return { ...r, pass: handle === null, detail: handle === null ? "窄螢幕不顯示拖曳線（略過）" : "窄螢幕卻出現拖曳線" };
}

/** 純函式：把量測結果轉成逐項 PASS／FAIL。 */
export function evaluate(s: LayoutSnapshot): CheckResult[] {
  return [
    endTurnWide(s),
    speedVisible(s),
    speedOneRow(s),
    handleCheck(s, bottomHandleFlush, s.bottomHandle),
    handleCheck(s, sideHandleFlush, s.sideHandle),
    handleCheck(s, heroHandleFlush, s.heroHandle),
    tileHint(s),
    moreMenu(s),
    noWrapper(s),
  ];
}

/** 純函式：PASS／FAIL 表（文字）；`failed` 是未通過的項目數。 */
export function formatTable(title: string, results: readonly CheckResult[]): { text: string; failed: number } {
  const failed = results.filter((r) => !r.pass).length;
  const rows = results.map((r) => `${r.pass ? "PASS" : "FAIL"}  ${r.label}｜${r.detail}`);
  return { text: [`== ${title}：${failed === 0 ? "全 PASS" : `${failed} 項 FAIL`} ==`, ...rows].join("\n"), failed };
}

// ---------------------------------------------------------------------------
// 以下需要瀏覽器 DOM（不在 vitest 裡跑）
// ---------------------------------------------------------------------------

const box = (e: Element | null): Box | null => {
  if (e === null) return null;
  const r = e.getBoundingClientRect();
  return { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
};

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

/** 背景色字串（`rgb(…)`／`rgba(…)`）的不透明度；沒有背景色為 0。 */
export function alphaOf(color: string): number {
  if (color === "transparent") return 0;
  const m = /^rgba?\(([^)]+)\)$/.exec(color.trim());
  if (m?.[1] === undefined) return 0;
  const parts = m[1].split(/[\s,/]+/).filter((p) => p !== "");
  const a = parts[3];
  if (a === undefined) return 1;
  return a.endsWith("%") ? Number.parseFloat(a) / 100 : Number.parseFloat(a);
}

function isHandle(el: Element, orientation: "vertical" | "horizontal", parent: string): boolean {
  return el.classList.contains(orientation) && el.parentElement?.classList.contains(parent) === true;
}

function collectBase(doc: Document, win: Window): LayoutSnapshot {
  const q = (sel: string): Element | null => doc.querySelector(sel);
  const handles = [...doc.querySelectorAll(".resize-handle")];
  const handle = (o: "vertical" | "horizontal", parent: string): Element | null => handles.find((e) => isHandle(e, o, parent)) ?? null;
  return {
    viewport: { width: win.innerWidth, height: win.innerHeight },
    turnControls: box(q(".turn-controls")),
    endTurn: box(q(".end-turn-button")),
    speed: box(q(".speed-control")),
    speedButtons: [...doc.querySelectorAll(".speed-control button")].map((e) => box(e)).filter((b): b is Box => b !== null),
    board: box(q(".battle-board")),
    bottomHandle: box(handle("horizontal", "battle-board")),
    sideHandle: box(handle("vertical", "battle-board")),
    hero: box(q(".battle-hero")),
    heroHandle: box(handle("vertical", "battle-hero")),
    tileCard: null,
    moreMenu: null,
    hintWrappers: doc.querySelectorAll(".hint-tip").length,
  };
}

function collectTileCard(doc: Document, win: Window): LayoutSnapshot["tileCard"] {
  const float = doc.querySelector(".unit-float");
  if (float === null) return null;
  const bar = float.querySelector(".tile-pin-bar");
  return {
    float: box(float) as Box,
    bar: box(bar),
    barAlpha: bar === null ? 0 : alphaOf(win.getComputedStyle(bar).backgroundColor),
  };
}

/** 在戰場畫布上掃過幾個點，直到格子資訊卡出現（用合成的 pointermove；React 的 onPointerMove 會收到）。 */
async function hoverUntilCard(doc: Document): Promise<boolean> {
  const canvas = doc.querySelector(".battle-canvas");
  if (canvas === null) return false;
  const r = canvas.getBoundingClientRect();
  for (const [fx, fy] of [
    [0.5, 0.5],
    [0.4, 0.45],
    [0.6, 0.55],
    [0.3, 0.3],
    [0.7, 0.7],
    [0.5, 0.2],
  ] as const) {
    canvas.dispatchEvent(
      new PointerEvent("pointermove", { clientX: r.left + r.width * fx, clientY: r.top + r.height * fy, pointerType: "mouse", pointerId: 1, bubbles: true, isPrimary: true }),
    );
    await sleep(700);
    if (doc.querySelector(".unit-float .tile-pin-bar") !== null) return true;
  }
  return false;
}

/** 滑過「更多動作」（說明卡出現）→ 點開選單 → 看說明卡是否消失。 */
async function probeMoreMenu(doc: Document): Promise<LayoutSnapshot["moreMenu"]> {
  const button = [...doc.querySelectorAll<HTMLButtonElement>("button")].find((b) => (b.textContent ?? "").includes("更多動作"));
  if (button === undefined || button.disabled) return null;
  button.dispatchEvent(new PointerEvent("pointerover", { pointerType: "mouse", pointerId: 1, bubbles: true, isPrimary: true }));
  await sleep(700);
  const hintBefore = doc.querySelectorAll('[role="tooltip"]').length; // 選單還沒開：說明卡應該出現（不然下面的檢查沒意義）
  button.click();
  await sleep(400);
  const open = button.getAttribute("aria-expanded") === "true" && doc.querySelector(".more-actions ul") !== null;
  return { open, tooltips: doc.querySelectorAll('[role="tooltip"]').length, hintBefore };
}

export interface CaseOptions {
  /** 先把底部列高度設成最矮（`BOTTOM_MIN`），測「拉到最矮」。 */
  shortBottom?: boolean;
}

const LAYOUT_KEY = "trpg.battleLayout";
/** 固定種子：每次開同一場戰鬥，量測才可比較（「更多動作」有沒有可用的動作也看種子）。 */
export const SMOKE_SEED = 20261024;
/** 起始武器：弓（遠程）一開場就有「瞄準」可放進「更多動作」，選單測得到。 */
export const SMOKE_WEAPON = "弓";

/** 開始畫面的種子欄（React 受控輸入：要用原生 setter 再送 input 事件）。 */
function setSeed(doc: Document, seed: number): void {
  const input = doc.querySelector<HTMLInputElement>(".seed-row input");
  if (input === null) return;
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, String(seed));
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

/** 從開始畫面進入一場戰鬥（選前兩個關鍵字）。 */
export async function startBattle(doc: Document = document, seed = SMOKE_SEED, weapon = SMOKE_WEAPON): Promise<void> {
  for (let i = 0; i < 30 && doc.querySelector(".run-keyword") === null; i++) await sleep(200);
  setSeed(doc, seed);
  [...doc.querySelectorAll<HTMLElement>(".run-weapon")].find((b) => (b.textContent ?? "").startsWith(weapon))?.click();
  await sleep(300);
  const keywords = doc.querySelectorAll<HTMLElement>(".run-keyword");
  keywords[0]?.click();
  await sleep(200);
  doc.querySelectorAll<HTMLElement>(".run-keyword")[1]?.click();
  await sleep(300);
  [...doc.querySelectorAll<HTMLButtonElement>("button")].find((b) => (b.textContent ?? "").trim().startsWith("開始戰鬥"))?.click();
  for (let i = 0; i < 50 && doc.querySelector(".battle-bottom") === null; i++) await sleep(200);
  await sleep(1500); // 等第一次畫面與動畫
}

/** 一個情況：（設定版面）→ 開戰鬥 → 量測 → 回傳 PASS／FAIL 表。視窗大小由呼叫端（resize_window）先設好、並重新載入頁面。 */
export async function runCase(title: string, options: CaseOptions = {}): Promise<string> {
  const storage = window.localStorage;
  if (options.shortBottom === true) storage.setItem(LAYOUT_KEY, JSON.stringify({ sideWidth: 300, bottomHeight: 120, heroWidth: 300, zoom: null }));
  else storage.removeItem(LAYOUT_KEY);
  await startBattle();
  const snap = collectBase(document, window);
  await hoverUntilCard(document);
  snap.tileCard = collectTileCard(document, window);
  snap.moreMenu = await probeMoreMenu(document);
  storage.removeItem(LAYOUT_KEY);
  const { text } = formatTable(`${title}（視窗 ${snap.viewport.width}×${snap.viewport.height}）`, evaluate(snap));
  return text;
}

declare global {
  interface Window {
    __layoutSmoke?: { runCase: typeof runCase; startBattle: typeof startBattle; evaluate: typeof evaluate; formatTable: typeof formatTable };
  }
}

export function installLayoutSmoke(win: Window): void {
  win.__layoutSmoke = { runCase, startBattle, evaluate, formatTable };
}
