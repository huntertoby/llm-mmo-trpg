// 遊戲內的「減少動態」開關（6H-1；美術 PM 6R-F 檢查待決 1）：跟系統（預設）／開／關，三選一，存 localStorage。
// - 有效值 ＝ 「開」→ 減少、「關」→ 不減少、「跟系統」→ 照 `prefers-reduced-motion: reduce`；
// - 所有畫面端（繪製器、大世界、升級光柱、震動預設）讀 `reducedMotion()`（`world/frameLoop.ts` 的 `prefersReducedMotion` 轉到這裡）；
// - CSS 看 `<html data-reduced-motion="true|false">`（`applyMotionAttr`）；JS 還沒跑之前退回 `@media (prefers-reduced-motion)`。
// 讀寫都包 try/catch：私密視窗、禁用儲存時只在本次有效。只影響畫面，不碰規則與數值。

export type MotionPref = "system" | "on" | "off";

export const MOTION_PREFS: readonly MotionPref[] = ["system", "on", "off"];
export const MOTION_PREF_LABELS: Readonly<Record<MotionPref, string>> = { system: "跟系統", on: "開", off: "關" };

export const MOTION_KEY = "trpg.reducedMotion";
const REDUCE_QUERY = "(prefers-reduced-motion: reduce)";
/** `<html>` 上的屬性（CSS 用 `:root[data-reduced-motion="true"]`）。 */
export const MOTION_ATTR = "data-reduced-motion";

const isPref = (v: unknown): v is MotionPref => v === "system" || v === "on" || v === "off";

let memo: MotionPref | null = null;
const listeners = new Set<() => void>();

function query(): MediaQueryList | null {
  try {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return null;
    return window.matchMedia(REDUCE_QUERY);
  } catch {
    return null;
  }
}

/** 系統設定（`prefers-reduced-motion: reduce`；查不到＝否）。 */
export const systemReducedMotion = (): boolean => query()?.matches ?? false;

/** 有效值（純函式）：開 → 是、關 → 否、跟系統 → 系統設定。 */
export function effectiveReduced(pref: MotionPref, system: boolean): boolean {
  return pref === "on" ? true : pref === "off" ? false : system;
}

/** 讀存的設定；沒存過、存的值不認得、無法存取時「跟系統」。 */
export function loadMotionPref(): MotionPref {
  if (memo !== null) return memo;
  let saved: unknown = null;
  try {
    saved = window.localStorage.getItem(MOTION_KEY);
  } catch {
    // 無法存取 localStorage 時跟系統
  }
  return isPref(saved) ? saved : "system";
}

/** 改設定：存起來（存不了時只在本次有效）、更新 `<html>` 屬性、通知訂閱者。 */
export function saveMotionPref(pref: MotionPref): void {
  memo = pref;
  try {
    if (pref === "system") window.localStorage.removeItem(MOTION_KEY);
    else window.localStorage.setItem(MOTION_KEY, pref);
  } catch {
    // 私密視窗等：只在本次有效
  }
  applyMotionAttr();
  for (const cb of [...listeners]) cb();
}

/** 目前是否減少動態（遊戲內設定 ＋ 系統設定的有效值）。 */
export const reducedMotion = (): boolean => effectiveReduced(loadMotionPref(), systemReducedMotion());

/** 訂閱有效值可能改變（遊戲內設定或系統設定）。 */
export function subscribeMotion(cb: () => void): () => void {
  listeners.add(cb);
  const q = query();
  q?.addEventListener?.("change", cb);
  return () => {
    listeners.delete(cb);
    q?.removeEventListener?.("change", cb);
  };
}

/** 把有效值寫到 `<html data-reduced-motion>`（CSS 用）。沒有 document 時不做事。 */
export function applyMotionAttr(doc: Document | undefined = typeof document === "undefined" ? undefined : document): void {
  try {
    doc?.documentElement.setAttribute(MOTION_ATTR, reducedMotion() ? "true" : "false");
  } catch {
    // 沒有 DOM（測試）時不做事
  }
}

/** 開機時呼叫一次：寫好屬性，系統設定改變時跟著更新。 */
export function installMotionPrefs(doc: Document): void {
  applyMotionAttr(doc);
  query()?.addEventListener?.("change", () => applyMotionAttr(doc));
}

/** 測試用：清掉本次記住的設定（下次重新讀 localStorage）。 */
export function resetMotionPrefMemo(): void {
  memo = null;
}
