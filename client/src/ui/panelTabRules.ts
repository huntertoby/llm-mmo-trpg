// 資訊面板的分頁規則（PNL-1a；docs/art/資訊面板-移植需求.md 3.2，使用者 2026-11-12 定案「照建議」）：純函式，元件在 `PanelTabs.tsx`。
// 照搬樣張 `docs/art/sample/infoPanelsTabs.js` 的 `pickTab`、`fitTabs`（分頁列四級縮）、`badge()`（五種記號）。

/** 分頁上的狀態記號（3.2 第 5 條；不新增顏色）：
 *  `n` 金底數字＝有事可做；`p` 細框數字＝進度或數量；`live` 綠點＝限時的事正在進行；`warn` 琥珀三角＝警告；`lock` 金鎖＝整頁都還沒開放。 */
export type TabBadgeKind = "n" | "p" | "live" | "warn" | "lock";

export interface TabBadgeSpec {
  kind: TabBadgeKind;
  /** 數字（`n`、`p` 才有；其他忽略）。 */
  value?: string | number | null;
  /** 滑過的說明（#42、#43；每種記號都要有）。 */
  hint: string;
}

/** 分頁列的四級（3.2 第 7 條）：樣子只看分頁列的寬度，不看目前是哪一頁。 */
export const FIT_NAMES = ["全名", "全部兩字短名", "全部只剩圖示", "折成兩列"] as const;
export type FitLevel = 0 | 1 | 2 | 3;

/**
 * 放得下就停（樣張 `fitTabs`）：0 全名 → 1 全部短名 → 2 全部只剩圖示 → 3 折兩列（仍只剩圖示；絕不藏分頁）。
 * `fits(lv)`：套上那一級的 class 後分頁列放不放得下（`scrollWidth ≤ clientWidth + 1`）。
 */
export function fitLevel(fits: (lv: FitLevel) => boolean): FitLevel {
  for (const lv of [0, 1, 2] as const) if (fits(lv)) return lv;
  return 3;
}

/** 那一級分頁列要掛的 class（0 沒有）。 */
export const fitClass = (lv: FitLevel): string => (lv === 0 ? "" : `fit${lv}`);

/**
 * 預設開哪一頁（3.2 第 3 條、樣張 `pickTab`）：照舊開第一個；只有第一個整頁鎖住（掛金鎖）時，
 * 改開第一個掛金底數字（有事可做）的，沒有就開第一個沒鎖的；全部鎖住時開第一個。
 */
export function pickTab<T extends { id: string; badge?: TabBadgeSpec | null }>(tabs: readonly T[]): string | null {
  const first = tabs[0];
  if (first === undefined) return null;
  if (first.badge?.kind !== "lock") return first.id;
  return (tabs.find((t) => t.badge?.kind === "n") ?? tabs.find((t) => t.badge?.kind !== "lock") ?? first).id;
}

/** 記號要不要寫數字：只有 `n`、`p`；鎖住時不掛數字（3.2 第 5 條）。 */
export const badgeShowsValue = (b: TabBadgeSpec): boolean => (b.kind === "n" || b.kind === "p") && b.value != null && b.value !== "";

/**
 * 分頁滑過的說明卡字：只剩圖示（第 2、3 級）時先寫名字（分頁的 `hint`，沒有就全名），再接記號的說明；
 * 全名、短名時只有記號說明（分頁自己有 `hint` 的照樣寫，例：「整備：重閃、溶掉與傳承、誓約」）。都沒有＝null（不開卡）。
 */
export function tabHintText(tab: { label: string; hint?: string | null; badge?: TabBadgeSpec | null }, fit: FitLevel): string | null {
  const name = tab.hint ?? (fit >= 2 ? tab.label : null);
  const parts = [name, tab.badge?.hint ?? null].filter((s): s is string => s != null && s !== "");
  return parts.length === 0 ? null : parts.join("　");
}
