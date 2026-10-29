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
import { enterDevScreen, type DevScreen } from "./devScreens";

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
  /** 畫面上顯示中的每張浮動卡（`.float-card`、`.unit-float`）與它是否有底色（3U-1）。 */
  floatCards: FloatCardBg[];
  /** 文字溢出自己的框、或相鄰元素矩形互相重疊的描述（3U-1）；應為空。 */
  textIssues: string[];
}

export interface FloatCardBg {
  /** 卡片的 class 與開頭文字，方便定位。 */
  name: string;
  /** 外框、內容區、或其中的 `.skill-card` 的最大底色不透明度（0～1）。 */
  alpha: number;
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

function floatCardsOpaque(s: LayoutSnapshot): CheckResult {
  const label = "每張顯示中的浮動卡有底色（3U-1）";
  const bad = s.floatCards.filter((c) => c.alpha < 0.5);
  return result("float-card-bg", label, bad.length === 0, bad.length === 0 ? `${s.floatCards.length} 張` : `無底色：${bad.map((c) => c.name).join("；")}`);
}

function noTextClash(s: LayoutSnapshot): CheckResult {
  const label = "沒有文字溢出自己的框、相鄰元素沒有互相重疊（3U-1）";
  return result("no-text-clash", label, s.textIssues.length === 0, s.textIssues.length === 0 ? "0 項" : s.textIssues.join("；"));
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
    floatCardsOpaque(s),
    noTextClash(s),
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
    floatCards: collectFloatCards(doc, win),
    textIssues: scanTextIssues(doc, win),
  };
}

const isShown = (el: Element, win: Window): boolean => {
  const r = el.getBoundingClientRect();
  const cs = win.getComputedStyle(el);
  return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && el.checkVisibility?.({ contentVisibilityAuto: true }) !== false;
};

/** 顯示中的浮動卡的底色：外框、內容區、內容區裡的 `.skill-card` 取最大不透明度。 */
export function collectFloatCards(doc: Document, win: Window): FloatCardBg[] {
  const out: FloatCardBg[] = [];
  for (const el of doc.querySelectorAll(".float-card, .unit-float")) {
    if (!isShown(el, win)) continue;
    const parts = [el, el.querySelector(".float-card-body"), el.querySelector(".skill-card")].filter((e): e is Element => e !== null);
    const alpha = Math.max(...parts.map((e) => alphaOf(win.getComputedStyle(e).backgroundColor)));
    out.push({ name: `${el.className.toString().replace(/\s+/g, ".")}「${(el.textContent ?? "").trim().slice(0, 12)}」`, alpha });
  }
  return out;
}

const describe = (el: Element): string => `${el.tagName.toLowerCase()}${el.className.toString() === "" ? "" : "." + el.className.toString().trim().split(/\s+/).join(".")}「${(el.textContent ?? "").trim().slice(0, 10)}」`;
const MAX_ISSUES = 12;

/** 文字溢出：自己的內容比框寬、又沒有 `overflow` 處理（溢出的字會畫到鄰居身上）。 */
function overflowIssues(doc: Document, win: Window): string[] {
  const out: string[] = [];
  for (const el of doc.body.querySelectorAll("*")) {
    if (el.closest("svg, canvas") !== null) continue;
    if (el.clientWidth === 0 || el.scrollWidth <= el.clientWidth + 1) continue;
    const cs = win.getComputedStyle(el);
    if (cs.overflowX !== "visible" || !isShown(el, win)) continue;
    // 只看自己有文字的元素（直接子文字節點），避免容器內含超寬子元素重複回報
    if (![...el.childNodes].some((n) => n.nodeType === Node.TEXT_NODE && (n.textContent ?? "").trim() !== "")) continue;
    out.push(`溢出 ${describe(el)} ${el.scrollWidth}>${el.clientWidth}`);
    if (out.length >= MAX_ISSUES) break;
  }
  return out;
}

const overlapArea = (a: DOMRect, b: DOMRect): { x: number; y: number } => ({
  x: Math.min(a.right, b.right) - Math.max(a.left, b.left),
  y: Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top),
});

/** 相鄰（同一父元素的）元素矩形互相重疊 > 2px：只看正常流程排版的（不含 absolute／fixed）。 */
function overlapIssues(doc: Document, win: Window): string[] {
  const out: string[] = [];
  for (const parent of doc.body.querySelectorAll("*")) {
    if (parent.closest("svg, canvas") !== null) continue;
    const kids = [...parent.children].filter((k) => {
      const cs = win.getComputedStyle(k);
      // 行內元素（inline）折行時外框矩形本來就會互相重疊，不算
      return cs.display !== "inline" && cs.position !== "absolute" && cs.position !== "fixed" && cs.display !== "contents" && isShown(k, win) && (k.textContent ?? "").trim() !== "";
    });
    for (let i = 0; i < kids.length; i++) {
      for (let j = i + 1; j < kids.length; j++) {
        const a = kids[i] as Element;
        const b = kids[j] as Element;
        const o = overlapArea(a.getBoundingClientRect(), b.getBoundingClientRect());
        if (o.x > 2 && o.y > 2) out.push(`重疊 ${describe(a)} × ${describe(b)}`);
      }
    }
    if (out.length >= MAX_ISSUES) break;
  }
  return out;
}

/** 掃描目前畫面的文字溢出與相鄰重疊（3U-1）。 */
export function scanTextIssues(doc: Document, win: Window): string[] {
  return [...overflowIssues(doc, win), ...overlapIssues(doc, win)].slice(0, MAX_ISSUES);
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
  /** 走「開新一輪」（種族與出身 → 武器 → 關鍵字 → 第 1 場）而不是首頁的單場戰鬥。 */
  viaRun?: boolean;
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

const buttonOf = (doc: Document, text: string): HTMLButtonElement | undefined =>
  [...doc.querySelectorAll<HTMLButtonElement>("button")].find((b) => (b.textContent ?? "").trim().startsWith(text));

/** 開始畫面：固定種族／出身、選武器、選前兩個關鍵字（viaRun 時先按「開新一輪」）。 */
async function fillStart(doc: Document, seed: number, weapon: string, viaRun: boolean): Promise<void> {
  if (viaRun) buttonOf(doc, "開新一輪")?.click();
  const ready = () => doc.querySelector(".run-keyword") !== null && (!viaRun || doc.querySelector('[data-testid="start-races"]') !== null);
  for (let i = 0; i < 30 && !ready(); i++) await sleep(200);
  setSeed(doc, seed);
  // 一輪的開局第一步：固定種族（人類）與出身（第一個）；首頁的單場戰鬥沒有這一步
  if (doc.querySelector('[data-testid="start-races"]') !== null) {
    doc.querySelector<HTMLElement>('[data-testid="race-human"]')?.click();
    await sleep(200); // 等重繪：兩次點擊之間不等的話，出身會用舊的選擇蓋掉種族
    doc.querySelector<HTMLElement>('[data-testid="start-origins"] button')?.click();
    await sleep(200);
  }
  [...doc.querySelectorAll<HTMLElement>(".run-weapon")].find((b) => (b.textContent ?? "").startsWith(weapon))?.click();
  // 關鍵字：換武器後預覽才回來，湊不到起始技能的會被取消；一律挑「目前可選、還沒選」的第一個，直到選滿 2 個
  for (let tries = 0; tries < 12 && doc.querySelectorAll(".run-keyword.selected").length < 2; tries++) {
    await sleep(600);
    const next = [...doc.querySelectorAll<HTMLButtonElement>(".run-keyword")].find((b) => !b.disabled && !b.classList.contains("selected") && !b.classList.contains("unavailable"));
    next?.click();
  }
  await sleep(400);
}

/** 從開始畫面進入一場戰鬥（選前兩個關鍵字）。 */
export async function startBattle(doc: Document = document, seed = SMOKE_SEED, weapon = SMOKE_WEAPON, viaRun = false): Promise<void> {
  const button = (text: string) => buttonOf(doc, text);
  if (doc.querySelector(".battle-bottom") !== null) return; // 已經在戰鬥畫面
  await fillStart(doc, seed, weapon, viaRun);
  if (viaRun) {
    button("自動配點並開始")?.click();
    for (let i = 0; i < 30 && button("開始第 1 場") === undefined; i++) await sleep(200);
    button("開始第 1 場")?.click();
  } else button("開始戰鬥")?.click();
  for (let i = 0; i < 50 && doc.querySelector(".battle-bottom") === null; i++) await sleep(200);
  await sleep(1500); // 等第一次畫面與動畫
}

/** 一個情況：（設定版面）→ 開戰鬥 → 量測 → 回傳 PASS／FAIL 表。視窗大小由呼叫端（resize_window）先設好、並重新載入頁面。 */
export async function runCase(title: string, options: CaseOptions = {}): Promise<string> {
  const storage = window.localStorage;
  if (options.shortBottom === true) storage.setItem(LAYOUT_KEY, JSON.stringify({ sideWidth: 300, bottomHeight: 120, heroWidth: 300, zoom: null }));
  else storage.removeItem(LAYOUT_KEY);
  await startBattle(document, SMOKE_SEED, SMOKE_WEAPON, options.viaRun === true);
  const snap = collectBase(document, window);
  await hoverUntilCard(document);
  snap.tileCard = collectTileCard(document, window);
  snap.moreMenu = await probeMoreMenu(document);
  await hoverFirst(document, ".skill-slot button, .race-slot button");
  snap.floatCards = collectFloatCards(document, window);
  snap.textIssues = scanTextIssues(document, window);
  storage.removeItem(LAYOUT_KEY);
  const { text } = formatTable(`${title}（視窗 ${snap.viewport.width}×${snap.viewport.height}）`, evaluate(snap));
  return text;
}

/** 對符合的第一個元素送 pointerover（觸發浮動卡的滑過），等卡片出現。 */
async function hoverFirst(doc: Document, selector: string, index = 0): Promise<boolean> {
  const el = doc.querySelectorAll(selector)[index];
  if (el === undefined) return false;
  el.dispatchEvent(new PointerEvent("pointerover", { pointerType: "mouse", pointerId: 1, bubbles: true, isPrimary: true }));
  await sleep(600);
  return true;
}

async function unhover(doc: Document, selector: string, index = 0): Promise<void> {
  doc.querySelectorAll(selector)[index]?.dispatchEvent(new PointerEvent("pointerout", { pointerType: "mouse", pointerId: 1, bubbles: true, isPrimary: true }));
  await sleep(450); // 離開寬限約 250ms
}

/** 一個畫面階段的掃描結果轉成兩列檢查（浮動卡底色、文字溢出／重疊）。 */
function stageRows(stage: string, doc: Document, win: Window, needCard: boolean): CheckResult[] {
  const cards = collectFloatCards(doc, win);
  const issues = scanTextIssues(doc, win);
  const missing = needCard && cards.length === 0;
  const clear = cards.filter((c) => c.alpha < 0.5);
  return [
    result(`${stage}/card-bg`, `${stage}：顯示中的浮動卡有底色`, clear.length === 0 && !missing, missing ? "應該出現浮動卡卻沒有" : clear.length === 0 ? `${cards.length} 張` : `無底色：${clear.map((c) => c.name).join("；")}`),
    result(`${stage}/text-clash`, `${stage}：沒有文字溢出或相鄰重疊`, issues.length === 0, issues.length === 0 ? "0 項" : issues.join("；")),
  ];
}

/**
 * 全站排版掃描（3U-1）：技能工坊 → 開始畫面（種族卡、出身卡、武器、關鍵字、屬性分配）→ 一輪畫面 → 戰鬥畫面。
 * 每個階段量「浮動卡有底色」與「文字溢出／相鄰重疊」。從首頁開始（先 `localStorage.clear()` 並重新載入）。
 */
export async function runScreens(title: string): Promise<string> {
  const doc = document;
  const win = window;
  const rows: CheckResult[] = [];
  // 首頁與技能工坊
  rows.push(...stageRows("首頁", doc, win, false));
  buttonOf(doc, "進入技能工坊")?.click();
  await sleep(600);
  rows.push(...stageRows("工坊・技能", doc, win, false));
  buttonOf(doc, "裝備")?.click();
  await sleep(600);
  rows.push(...stageRows("工坊・裝備", doc, win, false));
  buttonOf(doc, "回首頁")?.click();
  await sleep(600);
  // 開始畫面
  await fillStartPartial(doc, rows, win);
  // 戰後畫面（3U-3）：用開發入口直接進（需要 `?dev=1` 與伺服器 `TRPG_DEV_ROUTES=1`）；進不去就記一項失敗
  rows.push(...(await postBattleStages(doc, win)));
  const viewport = `${win.innerWidth}×${win.innerHeight}`;
  const { text } = formatTable(`${title}（視窗 ${viewport}）`, rows);
  return text;
}

/** 戰後畫面階段：畫面名、進去之後要等的元素、要滑過看浮動卡的選擇器（依序滑過第一個、中間、最後一個）。 */
const POST_BATTLE: readonly { screen: DevScreen; label: string; waitFor: string; hover: string }[] = [
  { screen: "gear_offer", label: "戰後・裝備三選一", waitFor: '[data-testid="gear-offer"]', hover: ".run-offer-card .part-tip" },
  { screen: "level_up", label: "戰後・升級選技", waitFor: ".run-levelup .run-offer-card", hover: ".run-levelup .run-offer-card .part-tip" },
  { screen: "complete_offer", label: "戰後・完整技能三選一", waitFor: ".run-complete-offer .run-offer-card", hover: ".run-complete-offer .run-offer-card .part-tip" },
  { screen: "campfire", label: "戰後・營火", waitFor: ".run-campfire", hover: ".run-campfire .part-tip" },
  { screen: "ended", label: "戰後・一輪結束", waitFor: ".run-actions", hover: ".part-tip" },
];

async function waitFor(doc: Document, selector: string, tries = 40): Promise<boolean> {
  for (let i = 0; i < tries && doc.querySelector(selector) === null; i++) await sleep(150);
  return doc.querySelector(selector) !== null;
}

/** 只掃戰後畫面（3U-3）：不必從首頁開始，需要 `?dev=1` 與伺服器 `TRPG_DEV_ROUTES=1`。 */
export async function runPostBattle(title: string): Promise<string> {
  const rows = await postBattleStages(document, window);
  return formatTable(`${title}（視窗 ${window.innerWidth}×${window.innerHeight}）`, rows).text;
}

async function postBattleStages(doc: Document, win: Window): Promise<CheckResult[]> {
  const rows: CheckResult[] = [];
  for (const stage of POST_BATTLE) {
    try {
      await enterDevScreen(stage.screen, win);
    } catch (e) {
      rows.push(result(`${stage.label}/enter`, `${stage.label}：進得了畫面`, false, e instanceof Error ? e.message : String(e)));
      continue;
    }
    if (!(await waitFor(doc, stage.waitFor))) {
      rows.push(result(`${stage.label}/enter`, `${stage.label}：進得了畫面`, false, `等不到 ${stage.waitFor}`));
      continue;
    }
    for (const d of doc.querySelectorAll("details")) d.open = true; // 展開的技能卡也要量（關著的 details 內容不會畫出來）
    await sleep(500);
    rows.push(...stageRows(stage.label, doc, win, false));
    const count = doc.querySelectorAll(stage.hover).length;
    const picks = [...new Set([0, Math.floor(count / 2), count - 1])].filter((i) => i >= 0 && i < count);
    for (const i of picks) {
      await hoverFirst(doc, stage.hover, i);
      rows.push(...stageRows(`${stage.label}・滑過#${i}`, doc, win, true));
      await unhover(doc, stage.hover, i);
    }
  }
  return rows;
}

async function fillStartPartial(doc: Document, rows: CheckResult[], win: Window): Promise<void> {
  buttonOf(doc, "開新一輪")?.click();
  for (let i = 0; i < 30 && doc.querySelector('[data-testid="start-races"]') === null; i++) await sleep(200);
  rows.push(...stageRows("開局", doc, win, false));
  await hoverFirst(doc, '[data-testid^="race-"]', 0);
  rows.push(...stageRows("開局・種族卡", doc, win, true));
  await unhover(doc, '[data-testid^="race-"]', 0);
  await hoverFirst(doc, '[data-testid^="origin-"]', 0);
  rows.push(...stageRows("開局・出身卡", doc, win, true));
  await unhover(doc, '[data-testid^="origin-"]', 0);
  await fillStart(doc, SMOKE_SEED, SMOKE_WEAPON, false);
  await hoverFirst(doc, ".run-keyword", 0);
  rows.push(...stageRows("開局・關鍵字", doc, win, true));
  await unhover(doc, ".run-keyword", 0);
  rows.push(...stageRows("開局・屬性分配", doc, win, false));
  buttonOf(doc, "自動配點並開始")?.click();
  for (let i = 0; i < 30 && buttonOf(doc, "開始第 1 場") === undefined; i++) await sleep(200);
  rows.push(...stageRows("一輪畫面", doc, win, false));
  buttonOf(doc, "開始第 1 場")?.click();
  for (let i = 0; i < 50 && doc.querySelector(".battle-bottom") === null; i++) await sleep(200);
  await sleep(1500);
  await hoverFirst(doc, ".skill-slot button, .race-slot button");
  rows.push(...stageRows("戰鬥・技能卡", doc, win, true));
}

declare global {
  interface Window {
    __layoutSmoke?: { runCase: typeof runCase; runScreens: typeof runScreens; runPostBattle: typeof runPostBattle; enterDevScreen: typeof enterDevScreen; scan: () => string[]; startBattle: typeof startBattle; evaluate: typeof evaluate; formatTable: typeof formatTable };
  }
}

export function installLayoutSmoke(win: Window): void {
  win.__layoutSmoke = { runCase, runScreens, runPostBattle, enterDevScreen, scan: () => scanTextIssues(win.document, win), startBattle, evaluate, formatTable };
}
