// 真側面的武器角度（Phase 3S-3）。面向右（+x ＝ 前）；朝西由 paperdoll.ts 整張左右鏡像。
// 純資料：每種武器 kind 在側面的握法。實際形狀沿用 paperdoll.ts / paperdollGear.ts 的畫法，只換「方向旗標」與「整體旋轉」。
// 規則（美術 PM 3S-1／3S-2 驗收）：長柄、劍都握在身前、往前傾，頂端落在臉的前面；槍一律槍口朝面向方向；成對武器的副手畫在遠側、較暗。
import type { GearItem } from "./appearance";

export interface SidePose {
  /** 傳給既有形狀函式的 front 旗標（決定形狀內部的左右：front ＝ true 時刃、鉤、擺幅在 +x 側）。 */
  front: boolean;
  /** 形狀函式內部會自己旋轉的角度（front 旗標對應的值）；先反向抵銷，才能精確指定最後的角度。 */
  inner: number;
  /** 最後的整體角度（弧度；正值＝頂端往前傾）。 */
  angle: number;
  /** 手的位置微調。 */
  dx: number;
  dy: number;
  /** 遠側（副手那把）變暗的程度，0 ＝ 不變。 */
  shade: number;
}

type Row = Pick<SidePose, "front" | "inner" | "angle"> & Partial<Pick<SidePose, "dx" | "dy">>;

/** 槍類（槍口朝 +x）。 */
const GUN: Row = { front: false, inner: -0.35, angle: 0.04 };

/** 各 kind 的主手角度表。形狀內部旋轉：劍 ∓0.25、匕首 ∓0.6、斧錘 ∓0.3、矛鐮 ∓0.15、槍弩 ±0.35（front 為 true 取第一個符號）。 */
const MAIN: Readonly<Record<string, Row>> = {
  sword: { front: true, inner: -0.25, angle: 0.95 },
  greatsword: { front: true, inner: -0.25, angle: 0.8 },
  dagger: { front: true, inner: -0.6, angle: 0.95 },
  axe: { front: true, inner: -0.3, angle: 0.5 },
  hammer: { front: true, inner: -0.3, angle: 0.75 },
  spear: { front: true, inner: -0.15, angle: 0.5 },
  scythe: { front: true, inner: -0.15, angle: 0.45 },
  staff: { front: true, inner: 0, angle: 0.4 },
  bow: { front: true, inner: 0, angle: 0, dx: -1 },
  crossbow: GUN,
  longgun: GUN,
  pistol: GUN,
  shotgun: GUN,
  whip: { front: false, inner: 0, angle: 0 },
  fist: { front: true, inner: 0, angle: 1.2 },
};

const FALLBACK: Row = { front: true, inner: 0, angle: 0.3 };

/** 槍類 kind（槍口方向測試與遠側處理用）。 */
export const GUN_KINDS: readonly string[] = ["longgun", "pistol", "shotgun", "crossbow"];

/** 取一件手持物在側面的姿勢。`far`：成對武器的副手（畫在遠側）。不認得的 kind 用保守的前傾角度。 */
export function sideWeaponPose(it: GearItem, far: boolean): SidePose {
  const row = MAIN[it.kind] ?? FALLBACK;
  const gun = GUN_KINDS.includes(it.kind);
  // 遠側那把：比主手更直一點（刃、柄），槍則略往下，才不會和主手那把完全疊在一起
  const angle = far ? (gun ? row.angle + 0.2 : row.angle - 0.3) : row.angle;
  return {
    front: row.front,
    inner: row.inner,
    angle,
    dx: (row.dx ?? 0) + (far ? -1.5 : 0),
    dy: (row.dy ?? 0) + (far && (gun || it.kind === "whip" || it.kind === "fist") ? 1.2 : 0),
    shade: far ? 0.3 : 0,
  };
}

/** 種族部件在側面的錨點（給 3R-3 用；座標同紙娃娃，面向右）。3S-3 不畫種族部件，只固定位置規則。 */
export const SIDE_RACE_ANCHORS = {
  /** 近側耳（尖耳、鰭耳往後上方伸）。 */
  ear: { x: -1.5, y: -28.5 },
  /** 獸耳：兩隻都看得到，遠側偏後、較暗。 */
  beastEar: { near: { x: -2.5, y: -36 }, far: { x: -5, y: -35 } },
  /** 角的底座（兩支都往後彎，遠側較暗；用 `drawHornSide`）。 */
  horn: { x: 0, y: -36 },
  /** 尾巴、背刺從背後出來。 */
  tail: { x: -5.5, y: -11 },
  /** 鬍子、獠牙、刺青、義體在臉的前半。 */
  face: { x: 4.2, y: -26 },
} as const;

/** 種族部件的繪製層（3R-3 實作時掛在 `SideHooks.race`）：`behind` ＝ 披風之後（尾巴、背刺）；`face` ＝ 頭之後、頭髮之前（鬍子、獠牙、刺青、義體）；`head` ＝ 頭部裝備之後（耳、角）。 */
export type SideRaceLayer = "behind" | "face" | "head";
