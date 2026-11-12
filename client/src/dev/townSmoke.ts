// 主城 HUD 的排版煙霧檢查（Phase RT-6；RT-6b 改：說明列只在真的重疊時讓位、寬視窗收合的任務鈕也檢查）：在大世界的實地畫面（主城、城鎮、野外都可以）量 HUD 各塊、說明列與功能列說明卡。
// 用法：先在頁面上進到大世界的實地地圖（開發模式建角色後「站起來」），再在內建瀏覽器的 `javascript_tool` 執行
// `await window.__layoutSmoke.runTown("標題")`，回傳 PASS／FAIL 表（同 `runCase`）。
// `evaluateTown(snapshot)` 是純函式（vitest 測它）；`collectTown()` 量畫面。
import { evaluateHudLayout, HUD_BLOCKS, type HudBlock, type Rect } from "../world/hud";
import type { CheckResult } from "./layoutSmoke";

export interface TownSnapshot {
  viewport: { width: number; height: number };
  /** HUD 舞台（`.world-hud`）。 */
  stage: Rect;
  /** HUD 各塊（`[data-hud-block]`）。 */
  blocks: Partial<Record<HudBlock, Rect>>;
  /** HUD 的縮放（`hudScale`）：設計座標 × scale＝畫面像素。 */
  scale: number;
  /** 窄視窗（`data-narrow`）。 */
  narrow: boolean;
  /** 任務追蹤收合成一個圖示。 */
  trackerCollapsed: boolean;
  /** 說明列（「點格子走過去……」）；沒有＝`null`。 */
  caption: Rect | null;
  /** 滑過功能列各鈕時：說明卡、當時說明列的不透明度。 */
  barCards: { name: string; card: Rect | null; captionOpacity: number }[];
  /** 說明卡關掉之後說明列的不透明度。 */
  captionOpacityAfter: number;
}

/** 收合的任務鈕要貼在錢包下方多近（設計座標）。 */
export const TUCK_GAP_MAX = 12;
const TOL = 1.5;

function hits(a: Rect, b: Rect): boolean {
  return a.left < b.left + b.width - TOL && b.left < a.left + a.width - TOL && a.top < b.top + b.height - TOL && b.top < a.top + a.height - TOL;
}

const r = (x: Rect): string => `[${[x.left, x.top, x.left + x.width, x.top + x.height].map(Math.round).join(",")}]`;

function res(id: string, label: string, pass: boolean, detail: string): CheckResult {
  return { id: `town/${id}`, label: `主城：${label}`, pass, detail };
}

/** 收合的任務鈕貼在右欄錢包正下方（RT-6 第 1 項；RT-6b：寬視窗手動收合也一樣）；展開時不檢查。 */
function trackerTucked(s: TownSnapshot): CheckResult {
  const label = "收合的任務鈕貼在錢包下方（不懸在地圖中段；寬窄一致）";
  if (!s.trackerCollapsed) return res("tracker-tuck", label, true, "任務欄展開，照原位");
  const t = s.blocks.tracker;
  const w = s.blocks.wallet;
  if (t === undefined || w === undefined) return res("tracker-tuck", label, false, "找不到任務鈕或錢包");
  const gap = (t.top - (w.top + w.height)) / s.scale;
  const right = Math.abs(t.left + t.width - (w.left + w.width)) <= TOL + 1;
  return res("tracker-tuck", label, gap >= -TOL && gap <= TUCK_GAP_MAX && right, `間距 ${Math.round(gap)}（設計座標）、右緣對齊 ${right}`);
}

/** 說明列不壓 HUD 各塊（提示列 toasts 會自己淡出，不算）。 */
function captionClear(s: TownSnapshot): CheckResult {
  const label = "說明列不壓 HUD 各塊";
  if (s.caption === null) return res("caption-hud", label, false, "找不到說明列");
  const cap = s.caption;
  const over = HUD_BLOCKS.filter((id) => id !== "toasts").filter((id) => {
    const b = s.blocks[id];
    return b !== undefined && b.width > 0 && b.height > 0 && hits(cap, b);
  });
  return res("caption-hud", label, over.length === 0, over.length === 0 ? `說明列 ${r(cap)}` : `壓到 ${over.join("、")}`);
}

/**
 * 功能列說明卡和說明列重疊時，說明列讓位（不透明度 ≤ 0.05）（RT-6 第 2 項）；RT-6b：沒重疊時說明列照常顯示（≥ 0.95），
 * 站在傳送石上時「傳送」不因沒重疊的說明卡消失。關掉之後說明列回來。
 */
function captionYields(s: TownSnapshot): CheckResult[] {
  const label = "說明列只在和功能列說明卡重疊時讓位（沒重疊照常顯示）";
  if (s.barCards.length === 0) return [res("caption-card", label, false, "沒有量到功能列說明卡")];
  const bad: string[] = [];
  const notes: string[] = [];
  for (const c of s.barCards) {
    if (c.card === null) {
      bad.push(`${c.name}：說明卡沒出現`);
      continue;
    }
    const over = s.caption !== null && hits(s.caption, c.card);
    if (over && c.captionOpacity > 0.05) bad.push(`${c.name}：說明卡 ${r(c.card)} 壓在說明列上（不透明度 ${c.captionOpacity.toFixed(2)}）`);
    else if (!over && s.caption !== null && c.captionOpacity < 0.95) bad.push(`${c.name}：說明卡 ${r(c.card)} 沒重疊，說明列卻隱藏（不透明度 ${c.captionOpacity.toFixed(2)}）`);
    else notes.push(`${c.name}${over ? " 重疊・讓位" : " 不重疊・照常"}`);
  }
  const back = s.captionOpacityAfter >= 0.95;
  return [
    res("caption-card", label, bad.length === 0, bad.length === 0 ? notes.join("、") : bad.join("；")),
    res("caption-back", "說明卡關掉之後說明列回來", back, `不透明度 ${s.captionOpacityAfter.toFixed(2)}`),
  ];
}

export function evaluateTown(s: TownSnapshot): CheckResult[] {
  const hud = evaluateHudLayout({ viewport: s.viewport, stage: s.stage, blocks: s.blocks }).map((c) => res(`hud-${c.id}`, c.label, c.pass, c.detail));
  return [...hud, trackerTucked(s), captionClear(s), ...captionYields(s)];
}

// ---------------- 量測（瀏覽器裡） ----------------

const sleep = (ms: number): Promise<void> => new Promise((ok) => setTimeout(ok, ms));

function rectOf(el: Element | null): Rect | null {
  if (el === null) return null;
  const b = el.getBoundingClientRect();
  return { left: b.left, top: b.top, width: b.width, height: b.height };
}

function opacityOf(el: Element | null, win: Window): number {
  if (el === null) return 0;
  return Number(win.getComputedStyle(el).opacity);
}

/** 功能列要滑過的鈕（左、中、右各一；中間是技能 K）。 */
const BAR_PROBES = ["btn-bag", "btn-skills", "btn-sneak"] as const;

export async function collectTown(doc: Document, win: Window): Promise<TownSnapshot | null> {
  const root = doc.querySelector<HTMLElement>('[data-testid="world-hud"]');
  if (root === null) return null;
  const blocks: Partial<Record<HudBlock, Rect>> = {};
  for (const el of root.querySelectorAll<HTMLElement>("[data-hud-block]")) {
    const id = el.dataset.hudBlock as HudBlock;
    const box = rectOf(el);
    if (box !== null && box.width > 0 && box.height > 0) blocks[id] = box;
  }
  const inner = root.querySelector<HTMLElement>(".world-hud-at-hero .world-hud-inner");
  const heroBox = blocks.hero;
  const scale = heroBox !== undefined && inner !== null && inner.offsetWidth > 0 ? heroBox.width / inner.offsetWidth : 1;
  const captionEl = doc.querySelector(".world-field.hud .world-field-bar");
  const trackerCollapsed = root.querySelector(".world-hud-tracker") === null;
  const barCards: TownSnapshot["barCards"] = [];
  for (const id of BAR_PROBES) {
    const btn = root.querySelector(`[data-hud="${id}"]`);
    if (btn === null) continue;
    btn.dispatchEvent(new PointerEvent("pointerover", { pointerType: "mouse", pointerId: 1, bubbles: true, isPrimary: true }));
    await sleep(600);
    const card = doc.querySelector(".float-card .hud-bar-card")?.closest(".float-card") ?? null;
    barCards.push({ name: id, card: rectOf(card), captionOpacity: opacityOf(captionEl, win) });
    btn.dispatchEvent(new PointerEvent("pointerout", { pointerType: "mouse", pointerId: 1, bubbles: true, isPrimary: true }));
    await sleep(450);
  }
  await sleep(200);
  return {
    viewport: { width: win.innerWidth, height: win.innerHeight },
    stage: rectOf(root) ?? { left: 0, top: 0, width: 0, height: 0 },
    blocks,
    scale,
    narrow: root.dataset.narrow === "1",
    trackerCollapsed,
    caption: rectOf(captionEl),
    barCards,
    captionOpacityAfter: opacityOf(captionEl, win),
  };
}

/** 量目前的大世界實地畫面，回傳 PASS／FAIL 表（`formatTable` 由呼叫端傳進來，避免循環匯入）。 */
export async function runTownWith(title: string, format: (title: string, rows: readonly CheckResult[]) => { text: string }, extra: () => readonly CheckResult[] = () => []): Promise<string> {
  const snap = await collectTown(document, window);
  if (snap === null) return format(`${title}（視窗 ${window.innerWidth}×${window.innerHeight}）`, [res("enter", "在大世界的實地畫面", false, "找不到 [data-testid=world-hud]")]).text;
  return format(`${title}（視窗 ${snap.viewport.width}×${snap.viewport.height}）`, [...evaluateTown(snap), ...extra()]).text;
}
