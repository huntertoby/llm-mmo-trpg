// 武器的統一座標（Phase 6M-2；需求 docs/archive/art/動畫移植需求.md 第 1 節第 4 點，照樣張 docs/art/sample/anim.js 的 WEAPONS）。
// 規則：每種武器一律「握把在原點（＝手）、作用端（刃尖、槍口、杖頭、箭的方向）朝區域 -y」，再由姿勢的 `wpn` 轉到需要的角度。
// 做法：各武器的輪廓（inkGear／inkWeapons／inkOffhand／inkSect）沿用現有座標，這裡記下每種武器的作用端 `tip`（現有座標，握把＝原點），
// 由 `tip` 算出「現有座標 → 統一座標」的旋轉 `base`：統一座標下作用端正好在 (0, -len)。
// 預設握法（沒給 `wpn`）＝ 現有的傾斜角度 `restLean`，畫出來和 6M-1 逐像素相同（inkDollSnapshot.test.ts 鎖住）；
// 換成統一座標的角度就是 `holdOf`（＝ restLean − base），每種武器只有側面、正面兩個值。
import type { GearItem } from "./appearance";
import type { Ctx } from "./artDraw";
import { inIconMode, type Pt } from "./inkStyle";

/** 姿勢給手持物的參數（沒給＝照預設握法，畫法與指令流和 6M-1 相同）。 */
export interface WeaponPoseOpt {
  /** 武器相對手的角度（統一座標：0 ＝ 作用端朝上，順時針為正，弧度）；只在側面主手生效。 */
  wpn?: number | undefined;
  /** 弓弦拉開的距離（虛擬像素，往握把的反方向）；> 0.5 時搭上一支箭。 */
  pull?: number | undefined;
  /** 測試用：回報手（＝握把）、作用端與刃點（斧、戟、鐮才有，6M-3）在畫布座標的位置。正式畫面不給。 */
  probe?: ((hand: Pt, tip: Pt, edge?: Pt) => void) | undefined;
}

/** 畫一件手持物需要知道的握法資訊（inkGear 的 HeldOpt 是它的超集）。 */
export interface HoldView {
  side: boolean;
  far?: boolean;
  back?: boolean;
}

/** 槍弩（現有座標朝 +x）。 */
export const GUN_KINDS: readonly string[] = ["pistol", "shotgun", "longgun", "crossbow"];

/** inkWeapons 的傾斜表：[正面／背面往外斜, 側面往前傾]（弧度）；槍弩是朝上抬的角度。 */
const LEAN: Readonly<Record<string, readonly [number, number]>> = {
  greatsword: [0.18, 0.8],
  hammer: [0.2, 0.5],
  spear: [0.12, 0.4],
  scythe: [0.12, 0.3],
  fist: [0.1, 1.2],
  whip: [0, 0],
  pistol: [0.35, 0.05],
  shotgun: [0.35, 0.05],
  longgun: [0.35, 0.05],
  crossbow: [0.35, 0.05],
};

/** 側面劍、匕首、拂塵往前上斜（inkGear、inkSect 的 SIDE_TILT）。 */
const SIDE_TILT = 0.75;

/**
 * 預設握法：現有畫法在「平移到手、鏡像」之後的旋轉角度；`null` ＝ 現有畫法不旋轉（法杖、弓、符紙、傀儡線、法球、書）。
 * 數值和運算式照搬原本各檔案的寫法，浮點結果完全相同（快照鎖住）。
 */
export function restLean(ctx: Ctx, it: GearItem, o: HoldView): number | null {
  switch (it.kind) {
    case "sword":
      if (it.form === "arcane") return inIconMode(ctx) ? 0 : o.side ? 0.75 : 0;
      return o.side ? SIDE_TILT : 0;
    case "dagger":
      return o.side ? SIDE_TILT : o.back !== true ? -0.5 : 0;
    case "axe":
      return (o.side ? SIDE_TILT : 0) * 0.8;
    case "staff":
      if (it.form === "scepter" || it.form === "totem") return inIconMode(ctx) ? 0 : o.side ? 0.4 : 0;
      return null;
    case "whisk":
      return o.side ? SIDE_TILT : null;
    case "bow":
    case "talisman":
    case "puppet_cross":
    case "orb":
    case "tome":
      return null;
    default:
      break;
  }
  if (inIconMode(ctx)) return 0; // 小圖示一律 45° 斜放，由圖示自己轉，不再加握法的傾斜
  const [front, side] = LEAN[it.kind] ?? [0, 0];
  const gun = GUN_KINDS.includes(it.kind);
  if (!o.side) return gun ? -front : front;
  return gun ? -side + (o.far ? 0.2 : 0) : side;
}

/** 彎刀、彎匕的刀尖往外彎的量（同 inkGear 的 drawBlade）。 */
function bladeBow(it: GearItem, o: HoldView): number {
  const outward = !o.side && o.back !== true ? -1 : 1;
  return it.form === "curved" ? 3 * outward : it.form === "kris" ? 3 : 0;
}

const PISTOL_LEN: Readonly<Record<string, number>> = { derringer: 6.5, revolver: 10.5 };
const LONGGUN_LEN: Readonly<Record<string, number>> = { sniper: 25, hunting: 24 };

function meleeTip(it: GearItem, o: HoldView): Pt | undefined {
  switch (it.kind) {
    case "sword":
      return it.form === "arcane" ? [0, -21] : [bladeBow(it, o), -21];
    case "dagger":
      return [bladeBow(it, o), -10];
    case "greatsword":
      return it.form === "zhanma" ? [2.8, -28] : [0, -28];
    case "axe":
      return [0, -24];
    case "hammer":
      return it.form === "mace" ? [0, -30] : it.form === "flail" ? [3, -34.4] : [0, -35];
    case "spear":
      return it.form === "trident" ? [0, -52] : [0, -50];
    case "scythe":
      return [0, -35];
    case "fist":
      return it.form === "knuckle" ? [0, -5.7] : it.form === "claw" ? [0, -11] : [0, -13];
    case "whip":
      return it.form === "bladed" ? [20, 9.6] : [16, 9];
    case "whisk":
      return [0, -22];
    default:
      return undefined;
  }
}

function rangedTip(it: GearItem, o: HoldView): Pt | undefined {
  switch (it.kind) {
    case "staff":
      if (it.form === "totem") return [0, -46];
      if (it.form === "scepter") return [0, -34];
      return it.form === "wand" ? [0, -30.4 * 0.75] : [0, -30.4]; // 魔杖在旋轉之後縮 0.75
    case "bow":
      // 箭的方向：正面、背面照現有輪廓（弓弦在 +x、弓身往 -x 彎）；側面左右翻過來，弓身朝前、弓弦朝自己（6M-3）
      return o.side ? [6, 0] : [-6, 0];
    case "crossbow":
      return it.form === "heavy" ? [18.6, -4.8] : [17.6, -4.8];
    case "pistol":
      return [PISTOL_LEN[it.form ?? ""] ?? 9, -2.8];
    case "shotgun":
      return it.form === "blunderbuss" ? [17.4, -3] : [20, -3.2];
    case "longgun":
      return [LONGGUN_LEN[it.form ?? ""] ?? 22, -3];
    case "talisman":
      return [0.4, -11.2];
    case "puppet_cross":
      return [0, 11]; // 傀儡線往下垂，作用端是線的末端
    case "orb":
      return [o.side ? 3.4 : 0, it.form === "floating" ? -9.4 : -5.6];
    default:
      return undefined;
  }
}

/** 作用端在現有座標（握把＝原點、平移到手並鏡像之後、旋轉之前）；不是武器（盾、書）回傳 `undefined`。 */
export function weaponTip(it: GearItem, o: HoldView): Pt | undefined {
  return meleeTip(it, o) ?? rangedTip(it, o);
}

/**
 * 刃點（6M-3，6M-2 驗收第 2 點）：斧、戟、鐮的刃在柄的側邊，揮砍弧光與受擊點從刃的中心畫（技能特效批用）。
 * 座標和 `weaponTip` 相同（現有座標，握把＝原點）；取刃口的中點，落在畫出來的輪廓上。
 * 斧：主刃刃口 (9.4,-20.6)；戟：斧刃刃口中點 (8.5,-42.4)；鐮：內彎刃口的中段 (11,-28)。
 */
const EDGE: Readonly<Record<string, Pt>> = {
  axe: [9.4, -20.6],
  halberd: [8.5, -42.4],
  scythe: [11, -28],
};

/** 有側刃的武器（斧、戟、鐮）的刃點；其他武器回傳 `undefined`（揮砍弧光與受擊點照作用端）。 */
export function weaponEdge(it: GearItem): Pt | undefined {
  if (it.kind === "axe") return EDGE["axe"];
  if (it.kind === "spear" && it.form === "halberd") return EDGE["halberd"];
  if (it.kind === "scythe") return EDGE["scythe"];
  return undefined;
}

/** 揮砍弧光與受擊點：有刃點用刃點，否則用作用端。 */
export function weaponStrikePoint(it: GearItem, o: HoldView): Pt | undefined {
  return weaponEdge(it) ?? weaponTip(it, o);
}

/** 一件武器的統一座標：`base` ＝ 現有座標 → 統一座標的旋轉；`len` ＝ 握把到作用端的距離。 */
export interface WeaponFrame {
  tip: Pt;
  base: number;
  len: number;
}

export function weaponFrame(it: GearItem, o: HoldView): WeaponFrame | undefined {
  const tip = weaponTip(it, o);
  if (tip === undefined) return undefined;
  const base = -Math.PI / 2 - Math.atan2(tip[1], tip[0]);
  return { tip, base, len: Math.hypot(tip[0], tip[1]) };
}

/** 統一座標下的預設握法角度（0 ＝ 作用端朝上，順時針為正）：側面、正面各一個值（正面在鏡像後的座標）。 */
export function holdOf(ctx: Ctx, it: GearItem, o: HoldView): number | undefined {
  const f = weaponFrame(it, o);
  if (f === undefined) return undefined;
  return (restLean(ctx, it, o) ?? 0) - f.base;
}

/**
 * 轉到握法：沒給 `wpn`（或不是側面）＝ 照現有傾斜（指令和 6M-1 相同）；給了 `wpn` ＝ 統一座標下轉 `wpn`。
 * 呼叫端已平移到手、做好鏡像；之後接著畫現有輪廓。有 `probe` 時回報手與作用端（在 `extraScale` 之前算好作用端）。
 */
export function orientWeapon(ctx: Ctx, it: GearItem, o: HoldView & WeaponPoseOpt, lean: number | null): void {
  const f = o.wpn !== undefined && o.side ? weaponFrame(it, o) : undefined;
  if (f !== undefined) ctx.rotate(o.wpn! + f.base);
  else if (lean !== null) ctx.rotate(lean);
  if (o.probe !== undefined) probeWeapon(ctx, it, o, o.probe);
}

function probeWeapon(ctx: Ctx, it: GearItem, o: HoldView, probe: (hand: Pt, tip: Pt, edge?: Pt) => void): void {
  const tip = weaponTip(it, o);
  if (tip === undefined) return;
  const m = ctx.getTransform();
  const at = (p: Pt): Pt => [m.a * p[0] + m.c * p[1] + m.e, m.b * p[0] + m.d * p[1] + m.f];
  const edge = weaponEdge(it);
  probe(at([0, 0]), at(tip), edge === undefined ? undefined : at(edge));
}
