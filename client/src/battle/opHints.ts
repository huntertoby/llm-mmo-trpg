// 行動列的操作說明句（Phase 6A-3，去文字化④；docs/art/去文字化移植需求.md 第 4 節）：
// 每一種說明句（選目標、攀跳、守護、撥開、兩段選取……）只在前 3 次出現，之後收進「?」圖示，滑過或點一下才看。
// 次數記在本機（localStorage）；讀寫都包 try/catch，失敗時當作 0 次照常顯示。設定的「重新顯示操作說明」清掉次數。

/** 每種說明句完整顯示的次數。 */
export const OP_HINT_LIMIT = 3;

export const OP_HINTS_KEY = "trpg.opHints.v1";

/** 說明句的種類：同一種共用次數。 */
export type OpHintKind = "move" | "copy" | "target" | "vault" | "defend" | "self" | "aside" | "composite" | "hurl" | "order";

/** 讀寫次數用的儲存區（測試可換成假的）。 */
export interface HintStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

function defaultStore(): HintStore | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

/** 全部的次數；讀不到或格式不對時空物件（＝每種 0 次）。 */
export function readOpHintCounts(store: HintStore | null = defaultStore()): Record<string, number> {
  if (store === null) return {};
  try {
    const raw = store.getItem(OP_HINTS_KEY);
    if (raw === null) return {};
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return {};
    const out: Record<string, number> = {};
    for (const [k, v] of Object.entries(parsed as Record<string, unknown>)) {
      if (typeof v === "number" && Number.isFinite(v) && v > 0) out[k] = Math.floor(v);
    }
    return out;
  } catch {
    return {};
  }
}

export function opHintCount(kind: OpHintKind, store: HintStore | null = defaultStore()): number {
  return readOpHintCounts(store)[kind] ?? 0;
}

/** 這一種說明句還要完整顯示嗎（前 `OP_HINT_LIMIT` 次）。 */
export function showOpHint(kind: OpHintKind, store: HintStore | null = defaultStore()): boolean {
  return opHintCount(kind, store) < OP_HINT_LIMIT;
}

/** 記一次出現；寫入失敗就算了（下次仍當作原本的次數）。 */
export function bumpOpHint(kind: OpHintKind, store: HintStore | null = defaultStore()): void {
  if (store === null) return;
  const counts = readOpHintCounts(store);
  counts[kind] = (counts[kind] ?? 0) + 1;
  try {
    store.setItem(OP_HINTS_KEY, JSON.stringify(counts));
  } catch {
    // 本機儲存不能用（隱私模式、空間滿了）：不記，照常顯示
  }
}

/** 這個頁面已經決定過的（種類＋識別）：同一個識別只算一次、結果不變。 */
const decidedOnce = new Map<string, boolean>();

/**
 * 常駐的說明句（技能列上方「點選藍色格子移動…」）用：同一個 `token`（例如「這場戰鬥的第 N 輪」）只算一次，
 * 第一次問的時候決定要不要完整顯示，之後同一個 `token` 都回傳同樣的結果。中途「等待中……」再回來也不會多記。
 */
export function opHintFullOnce(kind: OpHintKind, token: string, store: HintStore | null = defaultStore()): boolean {
  const id = `${kind}\u0000${token}`;
  const known = decidedOnce.get(id);
  if (known !== undefined) return known;
  const full = showOpHint(kind, store);
  decidedOnce.set(id, full);
  if (full) bumpOpHint(kind, store);
  return full;
}

/** 設定的「重新顯示操作說明」：清掉全部次數。 */
export function resetOpHints(store: HintStore | null = defaultStore()): void {
  decidedOnce.clear();
  if (store === null) return;
  try {
    store.removeItem(OP_HINTS_KEY);
  } catch {
    // 同上
  }
}
