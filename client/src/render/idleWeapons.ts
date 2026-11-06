// 武器專屬待機（QK-7；需求 docs/art/武器待機移植需求.md，真相來源 docs/art/sample/idleWeapons.js 的 IDLE 表，照搬數值）。
// 全部是純函式：（武器種類、單位 ID、待機時鐘毫秒）→ 這一格的姿勢。不用 Math.random、不讀時間；
// 相位用 `idHash(`${unitId}:weaponIdle`) % 1000 / 1000`（FNV-1a，同 idleClips），同一個 ID、同一個時鐘永遠同一格，同一隊錯開。
// - 動作量化成 8 格（同裝備、同朝向、同一格共用貼圖）；杖頭光、符文光（glow）是疊加層，不量化，照時鐘即時算。
//   法球（glow、orbY）在遊戲裡跟著 8 格放進貼圖（`live: false`）：持球的手畫在法球上面，疊加層會蓋住手（見 QK-7 報告待決）。
// - 側面播完整動作；正面、背面只套 bob、glow、orbY、shieldUp、pull（手臂與武器角度不變，避免和正面的雙手握法打架）。
// - 減少動態：一律站好（空姿勢、光不脈動）。
// - `breath`：樣張每種（拳套以外）都疊一個 bob 呼吸；遊戲裡呼吸已由 6M-4 的垂直縮放做（不換貼圖），所以遊戲用 `breath: false`。
import { idHash } from "./idleClips";
import type { QPose, QUnit, QView } from "./qCore";
import { qWeapon } from "./qWeapons";

export type WeaponIdleKind =
  | "sword"
  | "sword_shield"
  | "saber"
  | "arcane_blade"
  | "paired"
  | "spear"
  | "scythe"
  | "whip"
  | "gauntlet"
  | "staff"
  | "orb"
  | "bow"
  | "crossbow"
  | "gun"
  | "greatsword";

/** 15 種（樣張 idle-weapons.html 的順序）。 */
export const WEAPON_IDLE_KINDS: readonly WeaponIdleKind[] = ["sword", "sword_shield", "saber", "arcane_blade", "paired", "spear", "scythe", "whip", "gauntlet", "staff", "orb", "bow", "crossbow", "gun", "greatsword"];

export const WEAPON_IDLE_ZH: Readonly<Record<WeaponIdleKind, string>> = {
  sword: "劍",
  sword_shield: "劍盾",
  saber: "刀",
  arcane_blade: "魔導劍",
  paired: "成對武器",
  spear: "長槍",
  scythe: "鐮",
  whip: "鞭",
  gauntlet: "拳套",
  staff: "法杖",
  orb: "法球",
  bow: "弓",
  crossbow: "弩",
  gun: "火槍",
  greatsword: "雙手劍",
};

const TAU = Math.PI * 2;
const S = (u: number): number => Math.sin(u * TAU);
const C = (u: number): number => Math.cos(u * TAU);
/** a～b 之間 0→1→0。 */
const bump = (u: number, a: number, b: number): number => (u < a || u > b ? 0 : Math.sin(((u - a) / (b - a)) * Math.PI));
const breathOf = (u: number): QPose => ({ bob: -0.5 * (0.5 - 0.5 * C(u)) });

export interface WeaponIdleDef {
  /** 循環長度（毫秒）。 */
  ms: number;
  /** 說明（樣張 zh）。 */
  zh: string;
  /** 特寫的「中段」取哪一格（樣張 mid；沒給 ＝ 0.5）。 */
  mid?: number;
  /** 疊樣張的 bob 呼吸（拳套沒有，它自己會跳）。 */
  breath: boolean;
  /** 不含呼吸的側面姿勢（u ＝ 0～1）。 */
  core: (u: number) => QPose;
}

/** 樣張 IDLE 表（數值照搬）。 */
export const WEAPON_IDLE: Readonly<Record<WeaponIdleKind, WeaponIdleDef>> = {
  sword: { ms: 2400, zh: "劍：劍尖輕輕晃、重心微移", breath: true, core: (u) => ({ wpn: 0.75 + 0.08 * S(u), arm: 0.05 * S(u), hipN: 0.05 * S(u), hipF: -0.05 * S(u) }) },
  sword_shield: { ms: 2400, zh: "劍盾：舉盾微晃", breath: true, core: (u) => ({ shieldUp: 1.6 * (0.5 - 0.5 * C(u)), wpn: 0.75 + 0.05 * S(u), lean: -0.03 * (0.5 - 0.5 * C(u)) }) },
  saber: { ms: 2400, zh: "刀：刀尖畫小圈", breath: true, core: (u) => ({ wpn: 0.75 + 0.16 * S(u), arm: 0.08 * C(u) }) },
  arcane_blade: { ms: 2400, zh: "魔導劍：劍槽符文光脈動", breath: true, core: (u) => ({ wpn: 0.75 + 0.05 * S(u), glow: 0.5 - 0.5 * C(u) }) },
  // 成對武器（樣張第 7 版）：一手一把；手腕往前轉、刃尖往前下壓再收回（刃一直朝前）
  paired: { ms: 2400, zh: "成對武器：一手一把，手腕轉一下匕首", breath: true, core: (u) => ({ idle: 1, wpn: 0.75 + 0.45 * bump(u, 0.3, 0.65), arm: -0.15 * bump(u, 0.25, 0.65) }) },
  spear: {
    ms: 2400,
    zh: "長槍：槍尖往前點兩下",
    breath: true,
    core: (u) => {
      const k = bump(u, 0.15, 0.3) + bump(u, 0.35, 0.5);
      return { dw: 0.1 * k, arm: -0.04 * k };
    },
  },
  scythe: { ms: 2400, zh: "鐮：刃緩慢前後擺", breath: true, core: (u) => ({ dw: 0.08 * S(u), lean: 0.03 * S(u) }) },
  whip: { ms: 1200, zh: "鞭：鞭梢甩動", breath: true, core: (u) => ({ lash: u, arm: 0.06 * S(u) }) },
  // 樣張第 10 版：|sin| 在 0 和 0.5 都是 0，特寫的「中段」取跳到最高的 0.25
  gauntlet: {
    ms: 1200,
    mid: 0.25,
    zh: "拳套：舉拳原地小跳",
    breath: false,
    core: (u) => {
      const h = Math.abs(S(u));
      return { bob: -2.2 * h, arm: -0.55, wpn: 1.0, kneeN: 0.35 * (1 - h), kneeF: 0.35 * (1 - h), liftL: 0.8 * h, liftR: 0.8 * h };
    },
  },
  staff: { ms: 2400, zh: "法杖：杖頭光點脈動、杖身微晃", breath: true, core: (u) => ({ glow: 0.5 - 0.5 * C(u), dw: 0.04 * S(u) }) },
  orb: { ms: 2400, zh: "法球：法球在掌上浮沉、光脈動", breath: true, core: (u) => ({ orbY: -1.4 * (0.5 - 0.5 * C(u)), glow: 0.5 - 0.5 * C(u) }) },
  // 弓：箭搭在弦上、弓口朝前下，持弓手垂在身側；循環中段把弓抬起來看一下再放下（使用者：「收先不可能是這樣拉弓待機」）
  bow: {
    ms: 2400,
    zh: "弓：箭搭在弦上、弓口朝下，偶爾把弓抬起來看一下",
    breath: true,
    core: (u) => {
      const k = bump(u, 0.35, 0.8);
      return { nock: 1, arm: -0.3 * k, dw: -0.2 * k };
    },
  },
  crossbow: {
    ms: 2400,
    zh: "弩：托著待命，弩口往下點一下再抬回",
    breath: true,
    core: (u) => {
      const k = bump(u, 0.2, 0.6);
      return { dw: 0.25 * k, arm: 0.06 * k };
    },
  },
  gun: { ms: 2400, zh: "火槍：持槍待命、重心左右換", breath: true, core: (u) => ({ dw: 0.08 * bump(u, 0.1, 0.35), hipN: 0.08 * S(u), hipF: -0.08 * S(u), lean: 0.03 * S(u) }) },
  // 雙手劍：拄劍站著，重心左右換（劍跟著手走；使用者定案不做扛肩）
  greatsword: { ms: 2400, zh: "雙手劍：拄劍、重心左右換", breath: true, core: (u) => ({ dw: 0.03 * S(u), hipN: 0.1 * S(u), hipF: -0.1 * S(u), lean: 0.03 * S(u) }) },
};

/** 樣張 `IDLE[kind].pose(u)`（含呼吸）；`breath: false` 時不疊呼吸。 */
export function weaponIdlePose(kind: WeaponIdleKind, u: number, breath = true): QPose {
  const I = WEAPON_IDLE[kind];
  return breath && I.breath ? { ...breathOf(u), ...I.core(u) } : I.core(u);
}

/** 動作量化的格數。 */
export const WEAPON_IDLE_FRAMES = 8;

/** 疊加層的鍵（不量化、不換貼圖）。 */
export const OVERLAY_KEYS = ["glow", "orbY"] as const;
/** 正面、背面只套這幾個鍵。 */
export const FRONT_KEYS: readonly (keyof QPose)[] = ["bob", "glow", "orbY", "shieldUp", "pull"];

/** 這個人的待機相位（0～1）。 */
export function weaponIdlePhase(id: string): number {
  return (idHash(`${id}:weaponIdle`) % 1000) / 1000;
}

export interface WeaponIdleOpt {
  /** 減少動態：一律站好。 */
  reduce?: boolean;
  /** false：不量化（樣張 quantize: false）。 */
  quantize?: boolean;
  /** 疊樣張的 bob 呼吸（預設 true ＝ 同樣張；遊戲用 false）。 */
  breath?: boolean;
  /** false：glow、orbY 也量化（沒有疊加層時放進貼圖用）；預設 true（即時）。 */
  live?: boolean;
  /** 朝向（預設側面）：正面、背面只留 FRONT_KEYS。 */
  view?: QView;
}

export interface WeaponIdleFrame {
  /** 這一格的姿勢：動作是量化後的，glow、orbY 是即時的。 */
  pose: QPose;
  /** 第幾格（0～7）。 */
  frame: number;
  /** 循環中的位置（0～1，未量化）。 */
  u: number;
}

const frac = (x: number): number => ((x % 1) + 1) % 1;

/** 樣張 `frame(kind, id, ms, opt)`。 */
export function weaponIdleFrame(kind: WeaponIdleKind, id: string, ms: number, opt: WeaponIdleOpt = {}): WeaponIdleFrame {
  if (opt.reduce === true) return { pose: {}, frame: 0, u: 0 };
  const I = WEAPON_IDLE[kind];
  const u = frac(ms / I.ms + weaponIdlePhase(id));
  const n = Math.min(WEAPON_IDLE_FRAMES - 1, Math.floor(u * WEAPON_IDLE_FRAMES));
  const q = opt.quantize === false ? u : n / WEAPON_IDLE_FRAMES;
  const breath = opt.breath ?? true;
  const p = weaponIdlePose(kind, q, breath);
  const live = opt.live === false ? p : weaponIdlePose(kind, u, breath);
  for (const k of OVERLAY_KEYS) {
    if (live[k] !== undefined) p[k] = live[k];
    else delete p[k];
  }
  const view = opt.view ?? "side";
  return { pose: view === "side" ? p : onlyKeys(p, FRONT_KEYS), frame: n, u };
}

function onlyKeys(p: QPose, keys: readonly (keyof QPose)[]): QPose {
  const out: Record<string, unknown> = {};
  for (const k of keys) if (p[k] !== undefined) out[k] = p[k];
  return out as QPose;
}

/** 單手揮砍類（握法同劍）：匕首、斧、鎚照劍的待機；副手是盾時照劍盾。 */
const SWORDLIKE: ReadonlySet<string> = new Set(["sword", "saber", "dagger", "axe", "hammer"]);
const OWN: ReadonlySet<string> = new Set<string>(WEAPON_IDLE_KINDS);

/** 這個人用哪一種待機（看主手武器；Q 版不會畫的手持物〔拂塵、符紙…〕與空手 → null，只呼吸）。 */
export function weaponIdleKindOf(unit: QUnit): WeaponIdleKind | null {
  const q = qWeapon(unit.gear.main_hand);
  if (q === null) return null;
  const kind = q.kind;
  const shield = unit.gear.off_hand?.kind.startsWith("shield") === true;
  if (shield && SWORDLIKE.has(kind)) return "sword_shield";
  if (OWN.has(kind)) return kind as WeaponIdleKind;
  if (SWORDLIKE.has(kind)) return "sword";
  return null;
}
