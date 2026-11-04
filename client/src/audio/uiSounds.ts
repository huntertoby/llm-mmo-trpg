// 介面音（AU-2；docs/art/音效與音樂方案.md 第 2.2 節）：
// - 點擊：全站一個委派的 click 監聽（`installUiSounds`），依元素挑音：`data-sfx="<id>"` 指定（`none`＝不出聲）；
//   勾選、分頁、按下式按鈕＝開關；aria-disabled／HUD 停用狀態＝錯誤；送出、主要按鈕＝確認；取消、關閉＝取消；翻頁鈕＝翻頁；其他按鈕＝輕觸。
// - 事件：面板開關、錯誤提示、拿到物品、升級、任務、骰子、說書人字幕由元件呼叫；等待聲（羽毛筆、沙漏、翻頁）由等待動畫 `ui/WaitScene.tsx` 呼叫 `uiSound(id)`。
//   同一次點擊若已經觸發了事件音（例如按鈕打開面板），就不再疊一聲輕觸（輕觸延到這一輪事件之後才決定）。
import { audio, type AudioEngine, type PlayResult } from "./index";

export const UI_SOUNDS = [
  "ui_tap",
  "ui_confirm",
  "ui_cancel",
  "ui_error",
  "ui_toggle",
  "ui_select",
  "ui_panel_open",
  "ui_panel_close",
  "ui_page",
  "ui_item",
  "ui_coin",
  "ui_levelup",
  "ui_learn",
  "ui_quest_update",
  "ui_quest_done",
  "ui_dice_roll",
  "ui_dice_success",
  "ui_dice_fail",
  "ui_narrator",
  "ui_wait_quill",
  "ui_wait_sand",
  "ui_wait_page",
] as const;
export type UiSound = (typeof UI_SOUNDS)[number];

let eventSeq = 0;
/** 這一輪（同一個事件處理）已經放過事件音：同一下點擊只放一聲（例如「關閉」鈕的取消聲和面板收起聲只留先到的）。 */
let playedThisTurn = false;
let nextTurn: (fn: () => void) => void = (fn) => {
  if (typeof window === "undefined") fn();
  else window.setTimeout(fn, 0);
};

/** 測試用：換掉「下一輪」的排程。 */
export function setUiTurnScheduler(fn: (cb: () => void) => void): void {
  nextTurn = fn;
}

function claimTurn(): boolean {
  if (playedThisTurn) return false;
  playedThisTurn = true;
  nextTurn(() => {
    playedThisTurn = false;
  });
  return true;
}

/** 元件觸發的介面音（事件音）。同一輪已經有事件音時不再疊。 */
export function uiSound(id: UiSound, engine: AudioEngine = audio): PlayResult | "skipped" {
  eventSeq += 1;
  if (!claimTurn()) return "skipped";
  return engine.play(id);
}

/** 點擊時要找的元素。 */
const CLICKABLE = "[data-sfx], button, [role=button], [role=tab], [role=switch], [role=option], [role=menuitem], input[type=checkbox], input[type=radio], a[href]";
const CANCEL_RE = /^(取消|關閉|返回|×|✕|不要|算了)/;
const PAGE_RE = /(上一頁|下一頁|翻頁|前一頁|後一頁)/;
const LEARN_RE = /^(學會|學習)/;

/** 最小的元素介面（測試用假物件）。 */
export interface ElLike {
  closest(sel: string): ElLike | null;
  getAttribute(name: string): string | null;
  readonly tagName: string;
  readonly textContent: string | null;
  readonly className?: unknown;
}

/** 點到 `target` 要放哪個介面音（null＝不出聲）。 */
export function clickSoundFor(target: ElLike | null): UiSound | string | null {
  const el = target?.closest(CLICKABLE) ?? null;
  if (el === null) return null;
  const explicit = el.getAttribute("data-sfx");
  if (explicit !== null) return explicit === "none" || explicit === "" ? null : explicit;
  if (el.getAttribute("aria-disabled") === "true" || el.getAttribute("data-state") === "disabled") return "ui_error";
  const role = el.getAttribute("role");
  const type = el.getAttribute("type");
  if (el.tagName === "INPUT" && (type === "checkbox" || type === "radio")) return "ui_toggle";
  if (role === "tab" || role === "switch" || el.getAttribute("aria-pressed") !== null) return "ui_toggle";
  if (role === "option") return "ui_select";
  const label = `${el.getAttribute("aria-label") ?? ""} ${el.textContent ?? ""}`.trim();
  const text = (el.textContent ?? "").trim();
  if (PAGE_RE.test(label)) return "ui_page";
  if (CANCEL_RE.test(text) || CANCEL_RE.test(el.getAttribute("aria-label") ?? "")) return "ui_cancel";
  if (LEARN_RE.test(text)) return "ui_learn";
  const cls = typeof el.className === "string" ? el.className : "";
  if (type === "submit" || /\bprimary\b/.test(cls)) return "ui_confirm";
  return "ui_tap";
}

interface ClickTarget {
  addEventListener(type: "click", fn: (e: Event) => void): void;
  removeEventListener(type: "click", fn: (e: Event) => void): void;
}

/** 掛上全站的點擊介面音。`defer`：輕觸延後的方式（測試用同步版）。回傳移除函式。 */
export function installUiSounds(doc: ClickTarget, engine: AudioEngine = audio, defer: (fn: () => void) => void = (fn) => window.setTimeout(fn, 0)): () => void {
  const onClick = (e: Event): void => {
    const id = clickSoundFor(e.target as unknown as ElLike | null);
    if (id === null) return;
    if (id !== "ui_tap") {
      eventSeq += 1;
      if (claimTurn()) engine.play(id);
      return;
    }
    const seq = eventSeq;
    defer(() => {
      if (eventSeq === seq) engine.play("ui_tap");
    });
  };
  doc.addEventListener("click", onClick);
  return () => doc.removeEventListener("click", onClick);
}
