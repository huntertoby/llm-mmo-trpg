// 彈匣（Phase 3-24a2）：有彈匣的武器（火槍）在 HUD 與單位資訊顯示剩餘子彈；空膛時提示要裝填。
import type { UnitView } from "../api/types";

/** 單位的武器有彈匣（容量 > 0）。 */
export function hasMagazine(unit: Pick<UnitView, "magazine">): boolean {
  return unit.magazine > 0;
}

/** 彈匣的格子：依容量一格一發，裝著子彈的為 `true`（HUD 畫成實心圓點）。 */
export function ammoPips(ammo: number, magazine: number): boolean[] {
  return Array.from({ length: Math.max(0, magazine) }, (_, i) => i < ammo);
}

/** 一行文字：`彈匣 1/1`，空膛時加上「（空膛，需要裝填）」。 */
export function ammoText(unit: Pick<UnitView, "ammo" | "magazine">): string {
  const base = `彈匣 ${unit.ammo}/${unit.magazine}`;
  return unit.ammo <= 0 ? `${base}（空膛，需要裝填）` : base;
}
