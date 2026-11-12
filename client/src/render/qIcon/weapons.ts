// Q 版小圖示第 1 批：武器 17 種 53 款＋副手 4 種 8 款（Phase QI-1a；照 docs/art/sample/qIconsWeapons.js 逐行搬，需求 3.2）。
// 一張圖放兩種框：米色圓章（武器小圖示 20、24、28px）與裝備格（32px 以上）。框照現行，這裡只畫框裡的圖。
// 座標：48×48。斜放的武器畫在「握把 +y、作用端 −y」的直立座標再轉 45°；槍畫在「槍口 +x」再轉 −45°；手槍只斜 −0.42；拳套、盾、書、法器珠直立。
// 和樣張不同的地方：
// - 不搬樣張的 resolve()、NO_FORM、shock／freeze 別名：一律吃 `gearIcon.resolveGear()` 的結果（需求 2.2 第 2 點、2.4 第 1 列），由 `qResolve` 轉成畫法要的欄位。
// - 材質色用 `material.ts`（第 0.0 節第 3 點）；關鍵字色用 `palette.ts` 的 `KEYWORD_COLOR`（同色）。
// - 稀有度框、關鍵字小圖樣、圓章底由遊戲端畫（`gearIcon.frame()`／`motif()`、CSS `.weapon-icon`），這裡不搬 gearFrame／motif／paint／canvas。
import { KEYWORD_COLOR, TINT_KEYWORDS } from "../palette";
import { MATERIAL } from "../material";
import {
  arcaneArt, badgeScale, bowArt, gemAccent, bowGeo, bowString, ci, el, EL, f, fistArt, glow, greatswordArt, halo, hammerArt, HI, HI2, ln, M, mix, poly, rr, SH, sparkle,
  staffArt, starPts, swordArt, TAU, towerShield, diag as up,
  type Ctx, type DrawFn, type ArtPal, type Pt, type QOpts,
} from "./core";

const WOOD = "#7a5232", WOODL = "#a87648", CREAM = "#e8e0c8", GOLD = "#e8bb48", GOLDL = "#f6d878";

/** 畫法要的外觀（由 `resolveGear` 的結果轉來；樣張 resolve() 的回傳）。 */
export interface QResolved {
  kind: string;
  form: string;
  material: string;
  keywords: readonly string[];
  /** 第一個會混色的元素關鍵字。 */
  tintKw: string | undefined;
  /** 元素（杖頭、法器珠的光球色）：武器表的 element，沒有就由 tintKw 推。 */
  element: string | undefined;
  rarity: string;
  /** 外觀覆寫色（D2：本段不接，一律 null）。 */
  color: string | null;
}
/** 配色：主色 a、暗色 d、亮一階 l；護手 guard／guard2；杖頭 orb、元素 orbEl；寶石 accent。 */
export interface QPal extends ArtPal {
  l: string;
  orb: string;
  orbEl: string | undefined;
  accent: string;
  rich: boolean;
}
type Spots = readonly [Pt, Pt];
interface Built {
  d: DrawFn;
  pre?: DrawFn | undefined;
  post?: DrawFn | undefined;
  /** 直立塊狀（規則 7 門檻 70%）。 */
  block?: boolean;
  /** 圓章裡的縮放上限。 */
  badge?: number;
  diag?: boolean;
  spots?: Spots;
  pairArt?: boolean;
}
type Builder = (r: QResolved, P: QPal, icon: boolean) => Built;
type ArtFn = (c: Ctx, o: QOpts, P: QPal) => void;

interface KindInfo {
  zh: string;
  forms: Readonly<Record<string, string>>;
  diag?: boolean;
}
/** 清單：遊戲端 gearAppearance.json 的 weapon 17 種、offhand 4 種（款名與 JSON 一致，測試比對）。diag＝45° 斜放的長條物。 */
export const Q_WEAPON_KINDS: Readonly<Record<string, KindInfo>> = {
  sword: { zh: "劍", forms: { straight: "直劍", curved: "彎刀", broad: "闊劍", arcane: "魔導劍" }, diag: true },
  greatsword: { zh: "巨劍", forms: { twohand: "雙手劍", zhanma: "斬馬刀", serrated: "鋸齒巨劍" }, diag: true },
  dagger: { zh: "匕首", forms: { short: "短刀", stiletto: "三稜刺", kris: "彎匕" }, diag: true },
  axe: { zh: "斧", forms: { hand: "手斧", battle: "戰斧", double: "雙刃斧" }, diag: true },
  hammer: { zh: "錘", forms: { mace: "釘頭錘", warhammer: "戰錘", flail: "連枷" }, diag: true },
  spear: { zh: "矛", forms: { spear: "長矛", halberd: "戟", trident: "三叉戟" }, diag: true },
  bow: { zh: "弓", forms: { short: "短弓", long: "長弓", recurve: "反曲弓" }, diag: true },
  crossbow: { zh: "弩", forms: { light: "輕弩", heavy: "重弩", repeater: "連弩" }, diag: true },
  longgun: { zh: "火槍", forms: { flintlock: "燧發火槍", hunting: "獵槍", sniper: "狙擊火槍" }, diag: true },
  shotgun: { zh: "霰彈槍", forms: { blunderbuss: "喇叭槍", double: "雙管", pump: "泵動" }, diag: true },
  pistol: { zh: "手槍", forms: { flintlock: "燧發手槍", revolver: "左輪", derringer: "短銃" } },
  dual_pistol: { zh: "雙手槍", forms: { flintlock: "燧發手槍", revolver: "左輪", derringer: "短銃" } },
  fist: { zh: "拳套", forms: { katar: "拳刃", knuckle: "鐵拳", claw: "爪" } },
  scythe: { zh: "鐮刀", forms: { long: "長柄鐮", crescent: "彎月鐮", hook: "鉤鐮" }, diag: true },
  whip: { zh: "鞭", forms: { leather: "皮鞭", chain: "鏈鞭", bladed: "蛇骨鞭" }, diag: true },
  dual_dagger: { zh: "雙匕首", forms: { short: "短刀", stiletto: "三稜刺", kris: "彎匕" } },
  staff: { zh: "杖", forms: { long: "長杖", scepter: "權杖", wand: "短杖", totem: "圖騰杖" }, diag: true },
  round_shield: { zh: "圓盾", forms: { wood: "木圓盾", banded: "包鐵圓盾" } },
  kite_shield: { zh: "鳶盾", forms: { kite: "鳶盾", tower: "塔盾" } },
  tome: { zh: "法書", forms: { book: "典籍", scroll: "卷軸匣" } },
  orb: { zh: "法器珠", forms: { ball: "水晶球", floating: "浮空寶珠" } },
};

/** 會混色的元素關鍵字 → 元素（`gearAppearance.json` 的 elementKeywords；沒有舊名別名）。 */
const EL_OF_KW: Readonly<Record<string, string>> = { ignite: "fire", wet: "water", charged: "lightning", frozen: "ice" };

/** `resolveGear` 的結果 → 畫法要的欄位。`element`：外觀的元素欄位（`GearLook.element`），沒有就由第一個元素關鍵字推。 */
export function qResolve(r: { kind: string; form: string; material: string; keywords: readonly string[]; rarity: string }, element?: string | null): QResolved {
  const tintKw = r.keywords.find((k) => TINT_KEYWORDS.has(k));
  const el2 = element ?? (tintKw !== undefined ? EL_OF_KW[tintKw] : undefined);
  return { kind: r.kind, form: r.form, material: r.material, keywords: r.keywords, tintKw, element: el2, rarity: r.rarity, color: null };
}

/** 配色：主色 a、暗色 d、亮一階 l；護手 guard（單手劍、匕首：暗銅；史詩以上金）、guard2（雙手劍：金）。 */
export function qPalette(r: QResolved): QPal {
  let [a, d] = r.color !== null ? [r.color, mix(r.color, "#000000", 0.32)] : ((MATERIAL[r.material] ?? MATERIAL["iron"]) as readonly [string, string]);
  const tc = r.tintKw !== undefined ? KEYWORD_COLOR[r.tintKw] ?? null : null;
  if (tc) { if (r.material === "crystal") { a = tc; d = mix(tc, "#000000", 0.4); } else { a = mix(a, tc, 0.4); d = mix(d, tc, 0.25); } }
  const rich = r.rarity === "epic" || r.rarity === "legendary", wood = r.material === "wood";
  const orbDef = r.kind === "orb" ? (r.material === "crystal" ? "#a898ff" : a) : r.material === "crystal" ? a : "#c8bcff"; /* 法器珠：人物掌上那顆 #a898ff；杖頭：人物的 #c8bcff */
  /* 寶石色：有元素關鍵字用元素色、沒有才用其他關鍵字的色，不受關鍵字順序影響（QI-1b，美術 PM 對 1a 的追加；core.gemAccent） */
  const accent = gemAccent(r.keywords, r.material);
  return { a, d, l: mix(a, "#ffffff", 0.45), guard: rich ? GOLD : M.brass, guard2: rich ? GOLDL : M.gold, arc: r.material === "steel" && !tc ? "#dcd8f4" : mix(a, "#f0e6ff", 0.55),
    wood: a, woodD: d, shaft: wood ? M.shaft : d, head: a, headD: d, orb: tc ?? orbDef, orbEl: r.element, accent, rich };
}

// ---------------- 小工具 ----------------
const st = (c: Ctx, col: string, w: number, fn: (c: Ctx) => void, cap: CanvasLineCap = "round"): void => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
/** 槍的座標：槍口朝 +x、上方朝 −y；a＝轉幾度（−45°＝槍口朝右上）。 */
const gunF = (c: Ctx, fn: (x: Ctx) => void, a = -Math.PI / 4, k = 1, ox = 0, oy = 0): void => { c.save(); c.translate(24, 24); c.rotate(a); c.scale(k, k); c.translate(ox, oy); fn(c); c.restore(); };
/** 直立座標的點 → 48 格座標（給光暈、閃光用）。 */
const R45 = (x: number, y: number): Pt => [24 + (x - y) * Math.SQRT1_2, 24 + (x + y) * Math.SQRT1_2];
const donut = (c: Ctx, col: string, x: number, y: number, R: number, r: number): void => { c.beginPath(); c.arc(x, y, R, 0, TAU); c.moveTo(x + r, y); c.arc(x, y, r, 0, TAU, true); c.fillStyle = col; c.fill("evenodd"); };
/** 依形制挑畫法（resolveGear 保證形制在清單內；表裡沒有時用第一個）。 */
const pick = <T>(table: Readonly<Record<string, T>>, form: string, first: T): T => table[form] ?? first;

// =====================================================================
// 劍
// =====================================================================
/** 彎刀：刃往一側彎、越到前面越寬、刀尖斜削；橢圓小護手、柄尾一顆小圓頭。 */
function saberArt(c: Ctx, _o: QOpts, P: QPal): void {
  f(c, P.a, () => { c.moveTo(-3, 5); c.quadraticCurveTo(-7.6, -8, -0.4, -15.5); c.lineTo(6.6, -20.6); c.quadraticCurveTo(8.2, -10, 3.8, -2); c.lineTo(3.8, 5); c.closePath(); });
  f(c, SH, () => { c.moveTo(3.8, 5); c.lineTo(3.8, -2); c.quadraticCurveTo(8.2, -10, 6.6, -20.6); c.quadraticCurveTo(4.6, -10, 1.2, -3); c.lineTo(1.2, 5); c.closePath(); });
  st(c, HI2, 1.3, () => { c.moveTo(-1.5, 3.5); c.quadraticCurveTo(-5.2, -7.5, 0.4, -13.6); }, "butt");
  el(c, P.guard, 0.3, 6.5, 6.8, 2.7);
  rr(c, M.grip, -1.6, 8.6, 3.8, 9, 1.2);
  ci(c, P.guard, 0.5, 18.4, 2.7);
}
/** 闊劍：刃寬、從根部往前收窄成楔形、劍尖短而鈍、中間一道淺槽；護手兩端往上翹成新月、短握柄、一顆大圓柄頭。 */
function broadArt(c: Ctx, o: QOpts, P: QPal): void {
  poly(c, P.a, [[-5.6, 4], [-3.9, -14.5], [0, -20.6], [3.9, -14.5], [5.6, 4]]);
  f(c, SH, () => { c.moveTo(1.9, 4); c.lineTo(1.6, -18.2); c.lineTo(3.9, -14.5); c.lineTo(5.6, 4); c.closePath(); });
  f(c, HI2, () => { c.moveTo(-4.4, 3); c.lineTo(-3, -13.6); c.lineTo(-1.6, -13.6); c.lineTo(-2.9, 3); c.closePath(); });
  if (!o.small) rr(c, P.d, -1.1, -13, 1.9, 14.5, 0.9);
  f(c, P.guard, () => { c.moveTo(-10, 0.6); c.quadraticCurveTo(-9.6, 4, -5, 3.6); c.lineTo(5, 3.6); c.quadraticCurveTo(9.6, 4, 10, 0.6); c.quadraticCurveTo(11.6, 7.6, 5, 7.8); c.lineTo(-5, 7.8); c.quadraticCurveTo(-11.6, 7.6, -10, 0.6); c.closePath(); });
  rr(c, M.grip, -2.1, 7.4, 4.2, 7.6, 1);
  ci(c, P.guard, 0, 17.4, 3.6);
  if (!o.small) ci(c, HI, -1, 16.4, 1.1);
}
const SWORD: Builder = (r, P) => r.form === "arcane" ? { d: (c, o) => up(c, (x) => arcaneArt(x, o, P)), pre: (c) => glow(c, 29, 19, 15, M.arcane, 0.55), post: (c, o) => { if (!o.small) { sparkle(c, "#f6f0ff", 39, 21, 2.6); sparkle(c, "#f6f0ff", 27, 8.5, 2); } } }
  : { d: (c, o) => up(c, (x) => (r.form === "curved" ? saberArt : r.form === "broad" ? broadArt : swordArt)(x, o, P)) };

// =====================================================================
// 巨劍
// =====================================================================
const gsHilt = (c: Ctx, o: QOpts, P: QPal): void => { rr(c, P.guard2, -11.5, 0.8, 23, 4.4, 2.2); if (!o.small) f(c, GOLDL, () => c.rect(-9.5, 1.5, 19, 1)); rr(c, M.grip, -2.2, 5.2, 4.4, 16.3, 1.6); if (!o.small) f(c, "rgba(255,255,255,0.18)", () => c.rect(-1.4, 6.5, 0.9, 13.5)); };
/** 斬馬刀：單刃長刀——刀背筆直、刀尖往刀背那一側斜上去；一片金色橢圓刀鐔；長柄尾端一個金環。 */
function zhanmaArt(c: Ctx, o: QOpts, P: QPal): void {
  f(c, P.a, () => { c.moveTo(-3.6, 4); c.lineTo(-4.8, -12.8); c.quadraticCurveTo(-4.6, -20.6, 4, -21.5); c.lineTo(4, 4); c.closePath(); });
  f(c, SH, () => { c.moveTo(1.8, 4); c.lineTo(1.8, -21); c.lineTo(4, -21.5); c.lineTo(4, 4); c.closePath(); });
  st(c, HI2, 1.3, () => { c.moveTo(-2.4, 2.5); c.lineTo(-3.5, -12.8); c.quadraticCurveTo(-3.3, -17.6, -0.2, -19.4); }, "butt");
  el(c, P.guard2, 0.2, 4.6, 6.6, 2.5);
  rr(c, M.grip, -2, 5.8, 4, 12, 1.4);
  if (!o.small) for (const y of [9, 12, 15]) f(c, "rgba(255,255,255,0.2)", () => { c.moveTo(-2, y); c.lineTo(2, y - 1.4); c.lineTo(2, y - 0.4); c.lineTo(-2, y + 1); c.closePath(); });
  donut(c, P.guard2, 0, 18.6, 3, 1.3);
}
/** 鋸齒巨劍：雙手劍的刃，一側切成三個大鋸齒；護手與長柄同雙手劍。 */
function serratedArt(c: Ctx, o: QOpts, P: QPal): void {
  poly(c, P.a, [[-5.6, 1.5], [-5.6, -16], [-0.8, -21.5], [4.2, -17.6], [8.6, -15], [4.2, -12.2], [8.6, -9.6], [4.2, -6.8], [8.6, -4.2], [4.2, -1.4], [4.2, 1.5]]);
  f(c, SH, () => c.rect(1.4, -17, 2.8, 18.5));
  f(c, HI2, () => c.rect(-4.4, -15.5, 1.5, 16));
  rr(c, P.d, -1.6, -15, 1.6, 15, 0.8);
  gsHilt(c, o, P);
}
const GREATSWORD: Builder = (r, P) => ({ d: (c, o) => up(c, (x) => (r.form === "zhanma" ? zhanmaArt : r.form === "serrated" ? serratedArt : greatswordArt)(x, o, P)) });

// =====================================================================
// 匕首
// =====================================================================
const dagHilt = (c: Ctx, P: QPal, w = 14): void => { rr(c, P.guard, -w / 2, 1, w, 3.6, 1.8); rr(c, M.grip, -2.1, 4.6, 4.2, 9.4, 1.2); ci(c, P.guard, 0, 16, 2.8); };
/** 短刀：一片三角寬刃、橫護手。 */
function daggerShort(c: Ctx, _o: QOpts, P: QPal): void {
  poly(c, P.a, [[-4.7, 1.5], [0, -18], [4.7, 1.5]], 0.4);
  f(c, SH, () => { c.moveTo(0.8, 1.5); c.lineTo(0.8, -14.6); c.lineTo(4.7, 1.5); c.closePath(); });
  f(c, HI2, () => { c.moveTo(-3.7, 0.8); c.lineTo(-0.7, -11.6); c.lineTo(-0.7, 0.8); c.closePath(); });
  dagHilt(c, P);
}
/** 三稜刺：一根又細又長的錐，圓盤小護手、細長握柄。 */
function daggerStiletto(c: Ctx, _o: QOpts, P: QPal): void {
  poly(c, P.a, [[-3, 2], [0, -21.5], [3, 2]]);
  f(c, SH, () => { c.moveTo(0, 2); c.lineTo(0, -21.5); c.lineTo(3, 2); c.closePath(); });
  f(c, HI2, () => { c.moveTo(-2, 1.5); c.lineTo(-0.5, -13); c.lineTo(-0.5, 1.5); c.closePath(); });
  el(c, P.guard, 0, 2.8, 5.4, 2.6);
  rr(c, M.grip, -1.8, 4.8, 3.6, 10, 1.2); ci(c, P.guard, 0, 16.6, 2.5);
}
/** 彎匕：刃只往一側彎一下再收回來，刃尖收尖、朝正前方；護手一邊長一邊短。 */
function daggerKris(c: Ctx, _o: QOpts, P: QPal): void {
  const L: Pt[] = [], R: Pt[] = [], Cn: Pt[] = [], n = 16;
  for (let i = 0; i <= n; i++) { const t = i / n, y = 1.5 - t * 22.5, cx = -3 * Math.sin(Math.PI * Math.pow(t, 0.85)) ** 2, hw = 4.2 * Math.pow(1 - t, 0.85) + 0.2; L.push([cx - hw, y]); R.unshift([cx + hw, y]); Cn.push([cx, y]); }
  poly(c, P.a, [...L, ...R], 0.3);
  poly(c, SH, [...Cn, ...R]);
  st(c, HI2, 1.2, () => L.slice(0, 11).forEach(([x, y], i) => (i ? c.lineTo(x + 1.5, y) : c.moveTo(x + 1.5, y))), "butt");
  poly(c, P.guard, [[-8, 0.8], [6, -0.4], [5.4, 4.6], [-5.4, 4.6]], 0.8);
  rr(c, M.grip, -2.1, 4.6, 4.2, 9.4, 1.2); ci(c, P.guard, 0, 16, 2.8);
}
const DAGGER_ART: Readonly<Record<string, ArtFn>> = { short: daggerShort, stiletto: daggerStiletto, kris: daggerKris };
const daggerArtOf = (form: string): ArtFn => pick(DAGGER_ART, form, daggerShort);
/* 匕首本身比劍短；圖示裡放大到和其他武器差不多長，才撐得滿框。 */
const DAGGER: Builder = (r, P) => ({ d: (c, o) => up(c, (x) => { const k = r.form === "short" ? 1.1 : 1.05; x.translate(0, 0.4); x.scale(k, k); daggerArtOf(r.form)(x, o, P); }) });
/** 成對武器：兩把交叉（後面那把先畫、前面那把自己包一圈外框）。畫法收到的 o 多兩個旗標——pair、rear。 */
const crossed = (one: (c: Ctx, o: QOpts, s: number) => void): Built => ({ block: true, pairArt: true, d: (c, o) => { one(c, { ...o, pair: true, rear: true }, -1); halo(c, o, (x) => one(x, { ...o, pair: true }, 1)); } });
/* 彎匕兩把並排斜放、不交叉（後面那把在左上）；短刀、三稜刺是 X 形。 */
const DUAL_DAGGER: Builder = (r, P) => crossed((c, o, s) => { c.save();
  if (r.form === "kris") { const g = o.badge && o.small ? 5.8 : 4.6; c.translate(24 + s * g, 24 + s * g); c.rotate(Math.PI / 4); c.scale(0.98, 0.98); c.translate(0, 0.4); } /* 真 1 倍修正：圓章 ≤24px 兩把的間距再拉開 */
  else { c.translate(24, 24.5); c.scale(s, 1); c.rotate(0.62); c.scale(1.12, 1.12); }
  daggerArtOf(r.form)(c, o, P); c.restore(); });

// =====================================================================
// 斧
// =====================================================================
const haft = (c: Ctx, o: QOpts, top: number, bottom = 20.5, wrap = true, shaft: string = M.shaft): void => { rr(c, shaft, -1.9, top, 3.8, bottom - top, 1.4); if (!o.small) f(c, HI, () => c.rect(-1.1, top + 3, 0.8, bottom - top - 14)); if (wrap) { rr(c, M.grip, -2.5, bottom - 10.5, 5, 8, 1.2); rr(c, M.ironD, -2.8, bottom - 2.6, 5.6, 2.8, 1.2); } };
/** 一片斧刃：s＝在柄的哪一側、k＝大小、y0＝斧刃中心高度。 */
function axeHead(c: Ctx, P: QPal, s: number, k: number, y0: number, beard = 0): void {
  f(c, P.a, () => { c.moveTo(-2.4 * s, y0 - 4.4); c.lineTo(2 * s, y0 - 4.4); c.quadraticCurveTo(7 * s * k, y0 - 5, 10.6 * s * k, y0 - 7.8 * k); c.quadraticCurveTo(15.4 * s * k, y0 + beard / 2, 10.6 * s * k, y0 + 7.8 * k + beard); c.quadraticCurveTo(7 * s * k, y0 + 5 + beard * 0.3, 2 * s, y0 + 4.4); c.lineTo(-2.4 * s, y0 + 4.4); c.closePath(); });
  f(c, HI2, () => { c.moveTo(10.6 * s * k, y0 - 7.8 * k); c.quadraticCurveTo(15.4 * s * k, y0 + beard / 2, 10.6 * s * k, y0 + 7.8 * k + beard); c.quadraticCurveTo(11.6 * s * k, y0 + beard / 2, 10.6 * s * k, y0 - 7.8 * k); c.closePath(); });
  f(c, P.d, () => c.rect(Math.min(-2.4 * s, 2.4 * s), y0 - 4.4, 4.8, 8.8));
}
const AXE: Builder = (r, P) => ({ d: (c, o) => up(c, (x) => {
  if (r.form === "battle") { haft(x, o, -18); poly(x, P.a, [[-1.5, -14.4], [-9.6, -10.2], [-1.5, -6]], 0.4); axeHead(x, P, 1, 1.04, -10.2, 1.6); }
  else if (r.form === "double") { haft(x, o, -18.5); axeHead(x, P, -1, 0.92, -10.5); axeHead(x, P, 1, 0.92, -10.5); }
  else { haft(x, o, -17.5); axeHead(x, P, 1, 0.84, -10.6, 3); }
}) });

// =====================================================================
// 錘
// =====================================================================
/** 戰錘、釘頭錘的錘柄木色：只在圖示亮一階 `#6a4420` → `#a06a36`（＝material.ts 的木），人物不動。
 *  美術 PM 驗收 QI-1a 的決定（docs/art/QI-1檢查.md，規則 6：鐵的兩把錘平均亮度不到 100）；連枷、斧照舊。 */
const HAMMER_SHAFT = M.wood;
/** 釘頭錘：柄頂一顆鐵球，球外一圈八根短釘。 */
function maceArt(c: Ctx, o: QOpts, P: QPal, icon = true): void {
  haft(c, o, -8, 20.5, true, icon ? HAMMER_SHAFT : M.shaft);
  poly(c, P.d, starPts(0, -12, 9, 6.2, 8), 0.3);
  ci(c, P.a, 0, -12, 6.6);
  f(c, SH, () => { c.arc(0, -12, 6.6, -0.2, Math.PI * 0.75); c.closePath(); });
  ci(c, HI2, -2.4, -14.4, 2);
  rr(c, P.d, -2.6, -6.6, 5.2, 2.6, 1);
}
/** 連枷：短柄、柄頂一個鐵箍，兩顆亮色鍊環拉到斜上方一顆帶刺的鐵球。 */
function flailArt(c: Ctx, o: QOpts, P: QPal): void {
  c.save(); c.translate(-6.4, 0); haft(c, o, -9, 19.5); rr(c, P.d, -2.7, -11.4, 5.4, 4, 1.3); c.restore();
  ci(c, P.l, -1.2, -9.8, 2); ci(c, P.l, 2.9, -9.4, 2);
  poly(c, P.d, starPts(10.8, -7.4, 7.2, 4.9, 8, 0.3), 0.3);
  ci(c, P.a, 10.8, -7.4, 5.3);
  f(c, SH, () => { c.arc(10.8, -7.4, 5.3, -0.2, Math.PI * 0.75); c.closePath(); });
  ci(c, HI2, 8.8, -9.4, 1.9);
}
const HAMMER: Builder = (r, P, icon) => ({ d: (c, o) => up(c, (x) => (r.form === "mace" ? maceArt(x, o, P, icon) : r.form === "flail" ? flailArt(x, o, P) : hammerArt(x, o, P, icon ? HAMMER_SHAFT : M.shaft))) });

// =====================================================================
// 矛
// =====================================================================
const pole = (c: Ctx, o: QOpts, top: number, col: string = M.shaft): void => { rr(c, col, -1.5, top, 3, 21.5 - top, 1.2); if (!o.small) f(c, HI, () => c.rect(-0.9, top + 3, 0.7, 20)); };
const SPEAR: Builder = (r, P) => ({ d: (c, o) => up(c, (x) => {
  const col = M.shaft; /* 桿一律木色（人物也是）；材質只換矛頭 */
  if (r.form === "halberd") {
    pole(x, o, -10, col);
    poly(x, P.a, [[0, -21.5], [2.7, -11], [0, -9], [-2.7, -11]], 0.3);
    f(x, HI2, () => { x.moveTo(-0.4, -19); x.lineTo(-1.7, -11.4); x.lineTo(-0.4, -10.4); x.closePath(); });
    f(x, P.a, () => { x.moveTo(1.2, -11.6); x.quadraticCurveTo(7.6, -14.4, 9.4, -3.4); x.quadraticCurveTo(5.4, -6.4, 1.2, -6); x.closePath(); });
    f(x, HI2, () => { x.moveTo(6.8, -11.2); x.quadraticCurveTo(9.4, -8.4, 9.4, -3.4); x.quadraticCurveTo(7.8, -7.8, 6.8, -11.2); x.closePath(); });
    poly(x, P.a, [[-1.2, -11], [-6.6, -8.8], [-1.2, -6.6]], 0.3);
    rr(x, M.brass, -2.5, -5.8, 5, 2.4, 1);
  } else if (r.form === "trident") {
    pole(x, o, -10, col);
    rr(x, P.a, -8.6, -12, 17.2, 3.4, 1.5);
    poly(x, P.a, [[0, -21.5], [2.2, -11], [-2.2, -11]], 0.3);
    for (const s of [-1, 1]) poly(x, P.a, [[s * 6.8, -19.4], [s * 8.8, -11], [s * 4.8, -11]], 0.3);
    f(x, HI2, () => { x.moveTo(-0.3, -19); x.lineTo(-1.4, -11.4); x.lineTo(-0.3, -11.4); x.closePath(); });
    rr(x, M.brass, -2.5, -8.8, 5, 2.4, 1);
  } else {
    pole(x, o, -10, col);
    poly(x, P.a, [[0, -21.5], [4.4, -14.6], [2.2, -9], [-2.2, -9], [-4.4, -14.6]], 0.4);
    f(x, SH, () => { x.moveTo(0, -21.5); x.lineTo(4.4, -14.6); x.lineTo(2.2, -9); x.lineTo(0, -9); x.closePath(); });
    f(x, HI2, () => { x.moveTo(-0.6, -18.6); x.lineTo(-3, -14.6); x.lineTo(-1.6, -11); x.lineTo(-0.6, -11); x.closePath(); });
    rr(x, M.brass, -2.6, -9.4, 5.2, 2.6, 1);
  }
}) });

// =====================================================================
// 弓（三款的幾何在 core.ts 的 bowGeo）
// =====================================================================
const BOW: Builder = (r, P) => { const G = bowGeo(r.form), tip = r.form === "long" ? "#e9e3cf" : null; return { d: (c, o) => up(c, (x) => bowArt(x, o, P, G, tip)), post: (c, o) => up(c, (x) => bowString(x, o, G)) }; };

// =====================================================================
// 弩
// =====================================================================
function crossbowArt(c: Ctx, o: QOpts, P: QPal, form: string): void {
  const wide = form === "heavy" ? 16.4 : form === "repeater" ? 12.6 : 14.4, lw = form === "heavy" ? 5.2 : 3.8, py = -5.5;
  rr(c, WOOD, -2.3, -15, 4.6, 33, 1.6);
  poly(c, WOOD, [[-2.3, 8], [2.3, 8], [4, 19.6], [-4, 19.6]], 0.8);
  if (!o.small) f(c, WOODL, () => c.rect(-1.5, -3, 1, 20));
  if (!o.small) ln(c, "#e8e8e8", 1.4, [[-wide + 0.8, py + 0.6], [0, 1.5], [wide - 0.8, py + 0.6]]);
  ln(c, "#c8a070", 2, [[0, 1.5], [0, -15]]);
  st(c, P.a, lw, (x) => { x.moveTo(-wide, py); x.quadraticCurveTo(0, py - 12.5, wide, py); });
  if (!o.small) st(c, HI, 1, (x) => { x.moveTo(-wide + 3, py - 2.8); x.quadraticCurveTo(-wide * 0.45, py - 7.6, -1.5, py - 7.6); }, "butt");
  ci(c, P.d, -wide, py, lw * 0.55); ci(c, P.d, wide, py, lw * 0.55);
  poly(c, M.steel, [[-2.9, -15], [0, -21.5], [2.9, -15]], 0.3);
  if (form === "heavy") { /* 重弩：弩臂更寬更粗，尾端多一個上弦的絞盤 */
    ln(c, M.ironD, 2.2, [[0, 13], [7.4, 16.2]]); ci(c, GOLD, 7.4, 16.2, 2);
    ci(c, M.iron, 0, 13, 4.5); ci(c, M.ironD, 0, 13, 1.7); if (!o.small) ci(c, HI2, -1.6, 11.4, 1);
  } else if (form === "repeater") { /* 連弩：弩身上疊一個木箭匣，旁邊一根拉桿 */
    ln(c, M.ironD, 2.2, [[3, 2.5], [9.2, 9.8]]); ci(c, GOLD, 9.2, 9.8, 1.9);
    rr(c, "#96673c", -5.2, -13.6, 10.4, 13.6, 1.8); f(c, "#5e3b1f", () => c.rect(-5.2, -8.6, 10.4, 1.5));
    if (!o.small) { f(c, HI, () => c.rect(-4, -12.4, 1.2, 3)); f(c, "#5e3b1f", () => c.rect(-5.2, -4.4, 10.4, 1.1)); }
  } else rr(c, M.grip, -2.6, 9.5, 5.2, 5.5, 1.2);
}
const CROSSBOW: Builder = (r, P) => ({ d: (c, o) => up(c, (x) => crossbowArt(x, o, P, r.form)), post: (c, o) => { if (!o.small) return; const wide = r.form === "heavy" ? 16.4 : r.form === "repeater" ? 12.6 : 14.4; up(c, (x) => ln(x, "#2a1c14", 2.4, [[-wide + 1.4, -4.6], [0, 1.6], [wide - 1.4, -4.6]])); } });

// =====================================================================
// 火器
// =====================================================================
const cock = (c: Ctx, x: number, y: number): void => poly(c, M.ironD, [[x, y], [x - 2.8, y - 5.2], [x + 1, y - 6.2], [x + 2.8, y]], 0.5); /* 燧發機的擊鎚 */
const tguard = (c: Ctx, o: QOpts, x: number, y: number, col = GOLD, R = 2.9): void => st(c, col, o.small ? 2 : 1.6, (k) => k.arc(x, y, R, 0, Math.PI), "butt");
/** 燧發火槍：木槍托一路包到槍管下面，又長又細的槍管、兩道黃銅箍，機匣上一支翹起來的擊鎚。 */
function gunFlint(c: Ctx, o: QOpts, P: QPal): void {
  if (!o.small) tguard(c, o, -6, 1.8);
  f(c, WOOD, () => { c.moveTo(-20, -1.5); c.lineTo(-10.5, -4.6); c.lineTo(11, -3.6); c.lineTo(11, -0.4); c.lineTo(-8, 1.2); c.quadraticCurveTo(-13, 2, -20, 5.6); c.closePath(); });
  if (!o.small) f(c, WOODL, () => { c.moveTo(-19, -1); c.lineTo(-11, -3.6); c.lineTo(-11, -2.4); c.lineTo(-19, 0.2); c.closePath(); });
  rr(c, P.a, -9, -6.5, 28.8, 3.5, 1.4);
  f(c, HI2, () => c.rect(-7, -5.9, 24, 1));
  for (const x of [1, 9]) rr(c, GOLD, x, -7, 2.2, 6.6, 0.8);
  cock(c, -8.4, -5.6);
}
/** 獵槍：木槍托、一塊暗色機匣、槍管下一截短護木。 */
function gunHunting(c: Ctx, o: QOpts, P: QPal): void {
  tguard(c, o, -4.6, 1.2, P.d);
  poly(c, WOOD, [[-20, -2.6], [-9.5, -5.2], [-8.5, 1.6], [-13, 2.2], [-20, 5.4]], 0.8);
  if (!o.small) f(c, WOODL, () => c.rect(-18.6, -2.4, 8, 1.2));
  rr(c, WOOD, 2, -2.8, 11.5, 3.6, 1.4);
  rr(c, P.a, 2, -6.2, 17.8, 3.8, 1.4); f(c, HI2, () => c.rect(3.5, -5.6, 14, 1));
  rr(c, P.d, -10, -6.8, 12.6, 7.8, 1.8); f(c, HI, () => c.rect(-8.6, -5.6, 9.6, 1.2));
}
/** 狙擊火槍：長瞄準鏡、兩腳架、制退器、金屬骨架槍托。 */
function gunSniper(c: Ctx, o: QOpts, P: QPal): void {
  ln(c, P.d, 2.2, [[11.5, -2.6], [8.4, 6.8]]); ln(c, P.d, 2.2, [[11.5, -2.6], [15.2, 6.8]]);
  poly(c, P.d, [[-20, -3.6], [-9.5, -5.2], [-8.5, 1.6], [-14.5, 1.6], [-16, 4.6], [-20, 5.2]], 0.6);
  rr(c, P.a, 4, -5.6, 13, 3.3, 1.2); rr(c, P.d, 15.6, -6.8, 3.9, 5.7, 1.2);
  rr(c, P.a, -10, -6.6, 14.5, 7.2, 1.6); f(c, HI2, () => c.rect(-8.6, -5.6, 11.4, 1.1));
  rr(c, "#4a5260", -4.4, -8.6, 2.2, 2.4, 0.4); rr(c, "#4a5260", 2, -8.6, 2.2, 2.4, 0.4);
  rr(c, "#4a5260", -8, -12.6, 16, 4.8, 2.2); if (!o.small) f(c, HI, () => c.rect(-6.4, -11.8, 10, 1));
  ci(c, "#8fe3ff", 7.2, -10.2, 2);
}
const LONGGUN: Builder = (r, P) => ({ d: (c, o) => gunF(c, (x) => (r.form === "hunting" ? gunHunting : r.form === "sniper" ? gunSniper : gunFlint)(x, o, P)) });
/** 喇叭槍：槍管往槍口張開成喇叭、口上一圈深色的唇；燧發擊鎚、一道黃銅箍。 */
function gunBlunder(c: Ctx, o: QOpts, P: QPal): void {
  if (!o.small) tguard(c, o, -5.4, 2.6);
  poly(c, WOOD, [[-19.5, -2], [-8, -5.4], [-7, 2.4], [-12, 3], [-19.5, 6]], 0.9);
  f(c, P.a, () => { c.moveTo(-9, -6.2); c.lineTo(7, -5.2); c.quadraticCurveTo(12, -5.6, 16, -9.4); c.lineTo(16, 5.4); c.quadraticCurveTo(12, 1.6, 7, 1.2); c.lineTo(-9, 1.8); c.closePath(); });
  f(c, HI2, () => { c.moveTo(-7, -5.2); c.lineTo(7, -4.2); c.quadraticCurveTo(11.6, -4.6, 15, -7.4); c.lineTo(15, -5.6); c.quadraticCurveTo(11.6, -3.2, 7, -3); c.lineTo(-7, -4); c.closePath(); });
  rr(c, P.d, 15.2, -10.2, 3, 16.4, 1.4);
  rr(c, GOLD, -2, -6.5, 2.4, 8.6, 0.8);
  cock(c, -8.4, -5.4);
}
/** 雙管：上下兩根並排的粗槍管、槍口一圈箍、短木槍托、金色扳機護弓。 */
function gunDouble(c: Ctx, o: QOpts, P: QPal): void {
  tguard(c, o, -5.6, 5, GOLD, 3.2);
  poly(c, WOOD, [[-19.5, -2.2], [-8.5, -4.2], [-8.5, 4], [-13, 4.4], [-19.5, 7]], 1);
  if (!o.small) f(c, WOODL, () => c.rect(-18.5, -2.6, 9, 1.3));
  rr(c, P.d, -10, -5.6, 7.6, 11, 1.6);
  rr(c, P.a, -4, -5.2, 22.4, 10, 2); f(c, P.d, () => c.rect(-2.4, -0.8, 20.8, 1.5)); f(c, HI2, () => c.rect(-2, -4, 17, 1.3));
  rr(c, P.d, 15.8, -5.8, 2.8, 11.2, 1);
}
/** 泵動：一根槍管、下面一根彈倉管，套著一截淺色的木滑套。 */
function gunPump(c: Ctx, o: QOpts, P: QPal): void {
  poly(c, WOOD, [[-19.5, -2.6], [-9, -5], [-8, 0.5], [-11.6, 8], [-15.8, 6.6], [-13.6, 1.6], [-19.5, 3.6]], 0.8);
  rr(c, P.d, -10, -6.2, 9.5, 8.2, 1.6);
  rr(c, P.d, -1, -1.4, 16.5, 3.6, 1.4);
  rr(c, P.a, -1, -6.2, 20, 4.4, 1.6); f(c, HI2, () => c.rect(0.5, -5.4, 16, 1.1));
  rr(c, WOODL, 3.6, -2.6, 9.6, 6, 1.8); if (!o.small) for (const x of [5.8, 8, 10.2]) f(c, WOOD, () => c.rect(x, -1.6, 0.9, 4));
}
const SHOTGUN: Builder = (r, P) => ({ d: (c, o) => gunF(c, (x) => (r.form === "blunderbuss" ? gunBlunder : r.form === "pump" ? gunPump : gunDouble)(x, o, P)) });
/** 燧發手槍：往後下方彎的木握把（尾端一顆黃銅握把帽）、短槍管、護木、擊鎚。 */
function pistolFlint(c: Ctx, o: QOpts, P: QPal): void {
  if (!o.small) tguard(c, o, -1.2, 0.8, GOLD, 3);
  f(c, WOOD, () => { c.moveTo(-6, -5.5); c.lineTo(3, -5.5); c.lineTo(3, -0.5); c.quadraticCurveTo(-4, 0.5, -7.6, 10.4); c.lineTo(-13.6, 8); c.quadraticCurveTo(-11, -1, -6, -5.5); c.closePath(); });
  ci(c, GOLD, -10.8, 9.6, 3.3);
  rr(c, WOOD, 2, -3.4, 9.5, 3.2, 1.2);
  rr(c, P.a, -3, -8.2, 18, 5.2, 1.6); f(c, HI2, () => c.rect(-1, -7.4, 13, 1.2));
  rr(c, P.d, 13, -8.6, 2.5, 6, 1);
  cock(c, -5.4, -7.4);
}
/** 左輪：槍管、暗色的轉輪、斜向後下方的木握把、擊鎚、扳機護弓、準星。 */
function pistolRevolver(c: Ctx, o: QOpts, P: QPal): void {
  const lite = o.small && o.rear; /* 成對時後面那把在 ≤24px 省掉轉輪與扳機護弓 */
  if (!lite) st(c, P.d, o.small ? 2.1 : 1.7, (x) => x.arc(-0.2, 1.8, 3.3, 0, Math.PI), "butt");
  poly(c, WOOD, [[-9, -3.5], [-2.5, -1.5], [-6.5, 12], [-13.5, 9.5]], 1.4);
  if (!o.small) f(c, WOODL, () => { c.moveTo(-9.4, -1.6); c.lineTo(-7.6, -1); c.lineTo(-11.6, 9); c.lineTo(-13, 8.4); c.closePath(); });
  rr(c, P.a, 0, -8.4, 15.5, 5, 1.6); f(c, HI2, () => c.rect(1.5, -7.6, 11, 1.1));
  rr(c, P.a, -10, -8.8, 12, 4.2, 1.4);
  if (lite) rr(c, P.a, -6.8, -8.8, 9, 7.4, 2);
  else if (o.small && o.pair && o.badge) { rr(c, P.d, -7.8, -10.6, 11, 12.4, 3.4); f(c, HI2, () => c.rect(-6, -7.6, 7.4, 1.8)); f(c, mix(P.d, "#000000", 0.35), () => c.rect(-6, -3.4, 7.4, 1.8)); } /* 真 1 倍修正：圓章裡成對的前面那把在 ≤24px 轉輪放大 */
  else { rr(c, P.d, -6.8, -9.8, 9, 10.8, 3); f(c, HI, () => c.rect(-5.4, -6.8, 6.2, o.small ? 1.5 : 1.1)); if (!o.small) f(c, HI, () => c.rect(-5.4, -3, 6.2, 1.1)); }
  poly(c, P.d, [[-9.6, -8], [-12.6, -11], [-10.2, -12.2], [-7.6, -9]], 0.4);
  rr(c, P.d, 13.4, -10.6, 1.9, 2.8, 0.6);
}
/** 短銃：上下兩根疊著的短槍管、金色的槍身、鳥頭木握把；成對而且 ≤24px 時槍管加長（17 → 21）。 */
function pistolDerringer(c: Ctx, o: QOpts, P: QPal): void {
  const L = o.pair && o.small ? 21 : 17;
  if (!o.small) tguard(c, o, -1.4, 2.6, GOLD, 2.7);
  f(c, WOOD, () => { c.moveTo(-8.8, -2.6); c.lineTo(-2.6, -0.8); c.quadraticCurveTo(-1.8, 4.4, -5, 7.6); c.quadraticCurveTo(-6.8, 11.6, -10.6, 11); c.quadraticCurveTo(-14, 10, -12.6, 6.4); c.quadraticCurveTo(-10.4, 3, -10.6, -1.4); c.closePath(); });
  if (!o.small) st(c, WOODL, 1.1, (x) => { x.moveTo(-9.4, 0.6); x.quadraticCurveTo(-9.4, 3.6, -11.2, 6.6); }, "butt");
  rr(c, P.a, -4, -9.2, L, 4.8, 1.4); rr(c, P.a, -4, -4.2, L, 4.8, 1.4);
  f(c, HI2, () => c.rect(-2, -8.4, L - 5, 1.1)); f(c, SH, () => c.rect(-4, -1.6, L, 2.2));
  rr(c, GOLD, -9.6, -9.8, 6.8, 11.2, 1.8); if (!o.small) f(c, "#fff0b0", () => c.rect(-8.5, -8.6, 1.2, 8));
}
const PISTOL_ART: Readonly<Record<string, readonly [ArtFn, number, number, number]>> = { flintlock: [pistolFlint, 1.16, -0.6, -0.4], revolver: [pistolRevolver, 1.14, -0.4, -0.2], derringer: [pistolDerringer, 1.36, -1.6, -0.6] };
const pistolOf = (form: string): readonly [ArtFn, number, number, number] => pick(PISTOL_ART, form, [pistolFlint, 1.16, -0.6, -0.4]);
const PISTOL: Builder = (r, P) => { const [fn, k, ox, oy] = pistolOf(r.form); return { block: true, d: (c, o) => gunF(c, (x) => fn(x, o, P), -0.42, k, ox, oy) }; };
/* 雙手槍：兩把同款手槍交叉成 X，兩把的中心左右拉開，右邊那把在前面、自己包一圈外框。 */
const DUAL_PISTOL: Builder = (r, P) => { const [fn] = pistolOf(r.form), k = r.form === "derringer" ? 1.12 : r.form === "revolver" ? 0.96 : 1, dx = r.form === "derringer" ? 8 : 7.5; return crossed((c, o, s) => { c.save(); c.translate(24 + s * dx, 26.5); c.scale(s, 1); c.rotate(-1.02); c.scale(k, k); c.translate(1, 1.5); fn(c, o, P); c.restore(); }); };

// =====================================================================
// 拳套（鐵拳與爪直立、指節朝上；拳刃 45° 斜放）
// =====================================================================
const fistBase = (c: Ctx, _o: QOpts, P: QPal, y: number): void => { rr(c, P.headD, 15, y + 11.5, 18, 8.5, 3); rr(c, P.head, 9.5, y, 29, 13.5, 6.4); f(c, P.headD, () => c.roundRect(10.5, y - 1.6, 27, 3.8, 1.6)); for (let i = 0; i < 4; i++) f(c, i ? HI : HI2, () => c.roundRect(12.6 + i * 6.3, y + 3.6, 3.6, 1.8, 0.9)); };
/** 拳刃：45° 斜放的側面；一片寬三角刃從指節往前伸，刃根一條橫檔，兩根側桿夾在拳頭兩邊。 */
function katarArt(c: Ctx, o: QOpts, P: QPal): void {
  for (const s of [-1, 1]) rr(c, P.headD, s * 8.6 - 1.6, -1.6, 3.2, 17.2, 1.5);
  poly(c, P.a, [[-7, 0.4], [0, -20.6], [7, 0.4]], 0.7);
  f(c, SH, () => { c.moveTo(0.6, 0.6); c.lineTo(0.6, -19.4); c.lineTo(7.4, 0.6); c.closePath(); });
  f(c, HI2, () => { c.moveTo(-5.4, -0.4); c.lineTo(-1, -14.4); c.lineTo(-1, -0.4); c.closePath(); });
  rr(c, P.headD, -10.2, -1.8, 20.4, 3.8, 1.4);
  rr(c, P.headD, -5, 12.4, 10, 8.6, 2.2);
  rr(c, P.head, -6.2, 3, 12.4, 11.2, 4.2);
  f(c, P.headD, () => c.roundRect(-5.4, 4, 10.8, 2.2, 1));
  for (let i = 0; i < 4; i++) f(c, i ? HI : HI2, () => c.roundRect(-4.9 + i * 2.6, 7.2, 1.9, 1.5, 0.7));
  if (!o.small) f(c, HI, () => c.rect(-3.6, 14.2, 1, 5.4));
}
/** 爪：拳頭上三根往同一邊彎的長爪。 */
function clawArt(c: Ctx, o: QOpts, P: QPal): void {
  for (const [x, lean] of [[14.6, -0.6], [24, 2.2], [33.4, 5]] as const) {
    f(c, P.a, () => { c.moveTo(x - 3.2, 26); c.quadraticCurveTo(x - 5, 13, x + lean + 2, 3.4); c.quadraticCurveTo(x + 2.4, 14, x + 3.2, 26); c.closePath(); });
    f(c, HI2, () => { c.moveTo(x - 1.8, 24); c.quadraticCurveTo(x - 3, 14, x + lean + 0.6, 7.6); c.quadraticCurveTo(x - 1.4, 15, x - 0.4, 24); c.closePath(); });
  }
  fistBase(c, o, P, 25);
}
/** 現行「關鍵字小圖樣」畫在器物上的兩個位置（48 格座標）。 */
export const SPOTS: Readonly<Record<"diag" | "block" | "gun", Spots>> = { diag: [[30, 18], [20.5, 27.5]], block: [[17, 17], [31, 31]], gun: [[33, 13], [17, 33]] };
const FIST: Builder = (r, P) => r.form === "katar" ? { diag: true, spots: SPOTS.diag, d: (c, o) => up(c, (x) => katarArt(x, o, P)) } /* 拳刃是 45° 斜放的長條：圓章裡不套 0.86 上限；關鍵字小圖樣用斜放那一組 */
  : ({ block: true, badge: 0.86, d: r.form === "claw" ? (c, o) => clawArt(c, o, P) : (c, o) => fistArt(c, o, P) });

// =====================================================================
// 鐮刀
// =====================================================================
const scytheBlade = (c: Ctx, P: QPal, k = 1): void => {
  f(c, P.a, () => { c.moveTo(-1.6, -18.6); c.quadraticCurveTo(9 * k, -22.6, 16.6 * k, -7.4); c.quadraticCurveTo(8.6 * k, -15.4, -1.6, -13.4); c.closePath(); });
  f(c, HI2, () => { c.moveTo(0.5, -18.2); c.quadraticCurveTo(8.6 * k, -20.6, 14.4 * k, -10.6); c.quadraticCurveTo(8.4 * k, -18.2, 0.5, -16.8); c.closePath(); });
};
const SCYTHE: Builder = (r, P) => ({ d: (c, o) => up(c, (x) => {
  if (r.form === "hook") { /* 鉤鐮：短柄（纏皮握把）＋一片彎成問號的鉤刃 */
    rr(x, M.shaft, -1.9, -4, 3.8, 24.5, 1.4); rr(x, M.grip, -2.5, 8, 5, 10, 1.2); rr(x, M.ironD, -2.8, 17.8, 5.6, 2.8, 1.2);
    f(x, P.a, () => { x.moveTo(-2.4, -3); x.bezierCurveTo(-4.6, -19, 13.4, -22.4, 15.6, -6.4); x.bezierCurveTo(11.6, -15.6, 3.4, -15, 2.4, -3); x.closePath(); });
    f(x, HI2, () => { x.moveTo(-0.6, -9); x.bezierCurveTo(0.4, -17.4, 10.6, -19, 13.6, -11.4); x.bezierCurveTo(9.6, -17, 2.4, -15.6, 1, -9); x.closePath(); });
    rr(x, M.brass, -2.6, -4.6, 5.2, 2.6, 1);
    return;
  }
  rr(x, M.shaft, -1.6, -19.5, 3.2, 41, 1.3); if (!o.small) f(x, HI, () => x.rect(-0.9, -10, 0.7, 26));
  if (r.form === "crescent") { /* 彎月鐮：一片超過半圓（220°）的大新月刃 */
    const D = Math.PI / 180, O: Pt = [5, -9.2], R1 = 10.8, aA = 215 * D, aB = 75 * D, mid = 145 * D, half = 70 * D, dI = 4.4;
    const I: Pt = [O[0] + Math.cos(mid) * dI, O[1] + Math.sin(mid) * dI], R2 = Math.hypot(R1 * Math.sin(half), R1 * Math.cos(half) - dI);
    const A: Pt = [O[0] + Math.cos(aA) * R1, O[1] + Math.sin(aA) * R1], B: Pt = [O[0] + Math.cos(aB) * R1, O[1] + Math.sin(aB) * R1];
    const moon = (k: Ctx): void => { k.arc(O[0], O[1], R1, aA, aB + TAU); k.arc(I[0], I[1], R2, Math.atan2(B[1] - I[1], B[0] - I[0]), Math.atan2(A[1] - I[1], A[0] - I[0]), true); k.closePath(); };
    f(x, P.a, moon);
    x.save(); x.beginPath(); moon(x); x.clip(); st(x, HI2, 2, (k) => k.arc(I[0], I[1], R2 + 0.6, -Math.PI * 0.62, Math.PI * 0.2), "butt"); st(x, SH, 2.2, (k) => k.arc(O[0], O[1], R1 - 0.8, -Math.PI * 0.45, Math.PI * 0.35), "butt"); x.restore();
    rr(x, M.brass, -2.5, -13.4, 5, 2.4, 1);
    return;
  }
  scytheBlade(x, P);
  rr(x, M.brass, -2.5, -13.2, 5, 2.4, 1);
}) });

// =====================================================================
// 鞭：裝備格是 S 形；圓章裡（o.badge）盤成一捲（whipCoil）。
// =====================================================================
type Seg = readonly [Pt, Pt, Pt, Pt];
const WHIP_SEG: readonly Seg[] = [[[17, 31.5], [22.5, 26], [9, 21], [12.4, 13.4]], [[12.4, 13.4], [15, 6.4], [26.6, 6], [28, 14.4]], [[28, 14.4], [29.4, 22.6], [38, 22], [41, 10.6]]];
const seg = (i: number): Seg => WHIP_SEG[i] as Seg;
const bez = ([p0, p1, p2, p3]: Seg, t: number): Pt => { const u = 1 - t, a = u * u * u, b = 3 * u * u * t, d = 3 * u * t * t, e = t * t * t; return [a * p0[0] + b * p1[0] + d * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + d * p2[1] + e * p3[1]]; };
type WhipPt = readonly [number, number, number, number];
/** 沿鞭身每隔 step 單位取一點：[x, y, 切線角, 走了多遠 0～1]。 */
function whipPts(step: number): WhipPt[] {
  const dense: Pt[] = []; for (const s of WHIP_SEG) for (let i = 0; i < 40; i++) dense.push(bez(s, i / 40)); dense.push(seg(2)[3]);
  const at = (i: number): Pt => dense[i] as Pt;
  let acc = 0, next = 0; const out: WhipPt[] = [], len = dense.reduce((n, p, i) => (i ? n + Math.hypot(p[0] - at(i - 1)[0], p[1] - at(i - 1)[1]) : 0), 0);
  for (let i = 1; i < dense.length; i++) { const d = Math.hypot(at(i)[0] - at(i - 1)[0], at(i)[1] - at(i - 1)[1]); acc += d; if (acc >= next) { out.push([at(i)[0], at(i)[1], Math.atan2(at(i)[1] - at(i - 1)[1], at(i)[0] - at(i - 1)[0]), acc / len]); next += step; } }
  return out;
}
const whipPath = (c: Ctx, from = 0, to = 3): void => { c.moveTo(...seg(from)[0]); for (let i = from; i < to; i++) c.bezierCurveTo(...seg(i)[1], ...seg(i)[2], ...seg(i)[3]); };
const whipHandle = (c: Ctx, o: QOpts, P: QPal): void => { ln(c, M.grip, 5.4, [[10.4, 38.2], [16.6, 32]]); ci(c, P.guard, 9.4, 39.2, 3); ci(c, P.guard, 17, 31.5, 2.9); if (!o.small) ln(c, "rgba(255,255,255,0.22)", 1, [[11, 36], [14.6, 32.4]]); };
/* 圓章裡的鞭：握柄在左下、鞭梢甩到右上，中間盤成不留洞的一捲（一條螺旋暗線）。皮鞭＝皮色繩捲、梢端米白；鏈鞭＝鏈節、梢端菱形墜；蛇骨鞭＝暗色的索，刃片只在甩出圈外那一段。 */
const COIL = { x: 30.2, y: 30.2, R: 9.5, T: [23.5, 23.5] as Pt };
const COIL_TAIL: Readonly<Record<string, Seg>> = { leather: [[23.5, 23.5], [28.5, 18.5], [30.5, 8], [40, 12.4]], chain: [[23.5, 23.5], [28.5, 18.5], [30, 10], [37.6, 12.4]], bladed: [[23.5, 23.5], [27.5, 19.5], [28.4, 14.6], [32.6, 13.4]] };
const tailAt = (S: Seg, t: number): readonly [number, number, number] => { const [x, y] = bez(S, t), a = bez(S, Math.max(0, t - 0.03)), b = bez(S, Math.min(1, t + 0.03)); return [x, y, Math.atan2(b[1] - a[1], b[0] - a[0])]; };
const tailPath = (k: Ctx, S: Seg): void => { k.moveTo(...S[0]); k.bezierCurveTo(...S[1], ...S[2], ...S[3]); };
/** 螺旋暗線：從繩捲外緣往裡繞 turns 圈。 */
const coilSpiral = (k: Ctx, turns: number): void => { const a0 = Math.atan2(COIL.T[1] - COIL.y, COIL.T[0] - COIL.x), n = Math.ceil(turns * 48), pitch = COIL.R / (turns + 0.25); for (let i = 0; i <= n; i++) { const a = a0 + (i / 48) * TAU, q = COIL.R - pitch * (i / 48), x = COIL.x + Math.cos(a) * q, y = COIL.y + Math.sin(a) * q; if (i) k.lineTo(x, y); else k.moveTo(x, y); } };
const tipBlade = (c: Ctx, P: QPal, S: Seg, len: number, hw: number): void => { const [tx, ty, ta] = tailAt(S, 1); c.save(); c.translate(tx, ty); c.rotate(ta); poly(c, P.a, [[-2.6, -hw], [len, 0], [-2.6, hw]], 0.4); f(c, HI2, () => { c.moveTo(-2, -hw + 0.8); c.lineTo(len - 2, 0); c.lineTo(-2, 0); c.closePath(); }); c.restore(); };
const COIL_GRIP: readonly [Pt, Pt] = [[10.6, 36.4], [16.2, 30.8]];
function whipCoil(c: Ctx, o: QOpts, r: QResolved, P: QPal): void {
  const { x: X, y: Y, R, T } = COIL, S = COIL_TAIL[r.form] ?? (COIL_TAIL["leather"] as Seg);
  if (r.form === "chain") {
    const dark = mix(P.d, "#000000", 0.45), rings: ReadonlyArray<readonly [number, number, number, number]> = o.small ? [[R - 2.3, 10, 2.7, 2.3], [R - 6.4, 4, 2.4, 2.2]] : [[R - 2, 12, 2.4, 2], [R - 5.6, 7, 2.1, 1.8], [0, 1, 1.6, 1.6]];
    const links: ReadonlyArray<readonly [number, number, number, number?]> = [[19.8, 27.2, 0], ...[0.2, 0.44, 0.68].map((t, i): readonly [number, number, number, number] => { const q = tailAt(S, t); return [q[0], q[1], i + 1, q[2]]; })];
    links.forEach(([x, y, i, a = -Math.PI / 4]) => el(c, i % 2 ? P.d : P.l, x, y, 2.9, 2.2, a));
    const [tx, ty, ta] = tailAt(S, 1); c.save(); c.translate(tx, ty); c.rotate(ta); poly(c, P.a, [[-1.6, -3.4], [5.8, 0], [-1.6, 3.4], [-3.6, 0]], 0.4); f(c, HI2, () => { c.moveTo(-1.2, -2.5); c.lineTo(4, 0); c.lineTo(-1.2, 0); c.closePath(); }); c.restore();
    ci(c, dark, X, Y, R);
    rings.forEach(([q, n, rx, ry], j) => { for (let i = 0; i < n; i++) { const a = (i / n) * TAU + j * 0.5; el(c, (i + j) % 2 ? P.d : P.l, X + Math.cos(a) * q, Y + Math.sin(a) * q, rx, ry, a + Math.PI / 2); } });
  } else {
    const bladed = r.form === "bladed", rope = bladed ? P.d : P.a, dark = mix(P.d, "#000000", bladed ? 0.55 : 0.35);
    ln(c, rope, 3, [COIL_GRIP[1], T]);
    st(c, rope, o.small ? 4 : 3.2, (k) => tailPath(k, S));
    if (bladed) { for (const t of [0.42, 0.8]) { const [x, y, a] = tailAt(S, t); c.save(); c.translate(x, y); c.rotate(a); poly(c, P.a, [[-2.6, -3.5], [3.8, 0], [-2.6, 3.5]], 0.3); f(c, HI2, () => { c.moveTo(-2, -2.6); c.lineTo(2.4, 0); c.lineTo(-2, 0); c.closePath(); }); c.restore(); } tipBlade(c, P, S, 8.8, 4.5); }
    else { const [x1, y1] = bez(S, 0.8); ln(c, CREAM, o.small ? 3 : 2.4, [[x1, y1], S[3]]); }
    ci(c, rope, X, Y, R);
    if (o.small) { /* 真 1 倍修正：20、24px 改成一道粗的淺色弧（外圈）＋一小段暗弧（內圈） */
      st(c, mix(rope, "#ffffff", 0.5), 2.6, (k) => k.arc(X, Y, R - 2.2, Math.PI * 0.95, Math.PI * 1.95), "butt");
      st(c, dark, 2.4, (k) => k.arc(X, Y, R - 5.4, Math.PI * 0.1, Math.PI * 1.25), "butt");
    } else {
      st(c, dark, 1.5, (k) => coilSpiral(k, 2.5), "butt");
      st(c, mix(rope, "#ffffff", bladed ? 0.3 : 0.38), 1.2, (k) => k.arc(X, Y, R - 1.3, Math.PI * 1.3, Math.PI * 1.75), "butt");
    }
  }
  ln(c, M.grip, 5.4, COIL_GRIP); ci(c, P.guard, COIL_GRIP[0][0] - 0.6, COIL_GRIP[0][1] + 0.6, 3); ci(c, P.guard, COIL_GRIP[1][0] + 0.4, COIL_GRIP[1][1] - 0.4, 2.9); if (!o.small) ln(c, "rgba(255,255,255,0.22)", 1, [[11.4, 34], [14.4, 31]]);
}
const WHIP: Builder = (r, P) => ({ d: (c, o) => {
  if (o.badge) { whipCoil(c, o, r, P); return; }
  if (r.form === "chain") { /* 鏈鞭：一節一節的鏈環（亮暗交替），梢端一顆菱形的鐵墜 */
    const pts = whipPts(3.5);
    pts.forEach(([x, y, a], i) => el(c, i % 2 ? P.d : P.l, x, y, o.small ? 2.5 : 2.9, o.small ? 1.7 : 2.1, a));
    const [tx, ty, ta] = pts[pts.length - 1] as WhipPt; c.save(); c.translate(tx, ty); c.rotate(ta); poly(c, P.a, [[0, -3.6], [6.4, 0], [0, 3.6], [-2.4, 0]], 0.4); f(c, HI2, () => { c.moveTo(0, -2.6); c.lineTo(4.4, 0); c.lineTo(0, 0); c.closePath(); }); c.restore();
  } else if (r.form === "bladed") { /* 蛇骨鞭：一條暗色的索，只在甩出去的後半段放四片大刃片，梢端一片大的矛頭刃 */
    st(c, P.d, o.small ? 2 : 2.6, (x) => whipPath(x));
    const pts = whipPts(5.6);
    pts.slice(1, -1).filter((p) => p[3] >= 0.42).forEach(([x, y, a]) => { c.save(); c.translate(x, y); c.rotate(a); poly(c, P.a, [[-3, -4.6], [4.6, 0], [-3, 4.6]], 0.3); f(c, HI2, () => { c.moveTo(-2.3, -3.5); c.lineTo(3, 0); c.lineTo(-2.3, 0); c.closePath(); }); c.restore(); });
    const [tx, ty, ta] = pts[pts.length - 1] as WhipPt; c.save(); c.translate(tx, ty); c.rotate(ta); poly(c, P.a, [[-3, -3.8], [6.6, 0], [-3, 3.8]], 0.4); f(c, HI2, () => { c.moveTo(-2.4, -3); c.lineTo(4.6, 0); c.lineTo(-2.4, 0); c.closePath(); }); c.restore();
  } else { /* 皮鞭：一條粗皮繩繞一圈、越到梢端越細，梢端一小撮淺色的鞭梢 */
    st(c, P.a, o.small ? 2.6 : 3, (x) => whipPath(x)); st(c, P.a, o.small ? 3.4 : 4.4, (x) => whipPath(x, 0, 2));
    st(c, mix(P.a, "#ffffff", 0.38), 1.2, (x) => { x.moveTo(17.4, 29.6); x.bezierCurveTo(21.4, 25.6, 8.4, 20.6, 11.6, 13); x.bezierCurveTo(14.4, 5.4, 26, 5, 27.4, 13.6); }, "butt");
    ln(c, CREAM, 2.2, [[41, 10.6], [42.4, 6.4]]);
  }
  whipHandle(c, o, P);
} });

// =====================================================================
// 杖（長杖＝樣張的 staffArt：光球色＝元素色，沒有元素是 #c8bcff）
// =====================================================================
const orbPair = (P: QPal): readonly [string, string] => (P.orbEl !== undefined ? EL[P.orbEl] : undefined) ?? [P.orb, "#ffffff"];
/** 權杖：杖頭一個金環、環裡嵌一顆菱形寶石；杖身兩道金箍、杖尾一顆金球。 */
function scepterArt(c: Ctx, o: QOpts, P: QPal): void {
  const [e1] = orbPair(P);
  rr(c, P.shaft, -1.6, -5, 3.2, 22, 1.2); if (!o.small) f(c, HI, () => c.rect(-0.9, -2, 0.7, 16));
  ci(c, GOLD, 0, 18, 2.7);
  rr(c, GOLD, -2.6, 6.6, 5.2, 2.4, 1); poly(c, GOLD, [[-4.4, -6.6], [4.4, -6.6], [2.2, -3.4], [-2.2, -3.4]], 0.5);
  donut(c, GOLD, 0, -13, 8, 4.6);
  if (!o.small) st(c, GOLDL, 1.1, (x) => x.arc(0, -13, 6.9, Math.PI * 0.95, Math.PI * 1.6), "butt");
  poly(c, e1, [[0, -19], [4.6, -13], [0, -7], [-4.6, -13]], 0.4);
  poly(c, HI2, [[0, -18], [0, -13], [-3.4, -13]]);
}
/** 短杖：握把粗、往前收細的小木杖（兩道金箍），杖尖一顆小光球。 */
function wandArt(c: Ctx, o: QOpts, P: QPal): void {
  const [e1] = orbPair(P);
  poly(c, P.shaft, [[-2.6, 17], [-1.3, -10], [1.3, -10], [2.6, 17]], 0.8);
  if (!o.small) f(c, HI, () => { c.moveTo(-1.6, 14); c.lineTo(-0.7, -8); c.lineTo(-0.1, -8); c.lineTo(-0.7, 14); c.closePath(); });
  rr(c, GOLD, -3.4, 4.4, 6.8, 2.6, 1.1); rr(c, GOLD, -3.6, 14.4, 7.2, 2.8, 1.2);
  rr(c, GOLD, -2.2, -11.6, 4.4, 2.6, 1);
  ci(c, e1, 0, -15.6, 4.9); ci(c, HI2, -1.8, -17.4, 1.3);
}
/** 圖騰杖：杖頭一截木雕圖騰——上下兩張臉，兩側各一片羽毛，頂上一顆小綠珠。 */
function totemArt(c: Ctx, o: QOpts, P: QPal): void {
  rr(c, P.shaft, -1.7, -2, 3.4, 23.5, 1.3); if (!o.small) f(c, HI, () => c.rect(-0.9, 1, 0.7, 16));
  for (const s of [-1, 1]) poly(c, "#e9e3cf", [[s * 5, -14.6], [s * 11.6, -16.6], [s * 11.2, -9.6], [s * 5, -9.6]], 0.6);
  if (!o.small) for (const s of [-1, 1]) f(c, "#c0392b", () => { c.moveTo(s * 9.6, -16.6); c.lineTo(s * 12, -17.2); c.lineTo(s * 11.8, -13.6); c.lineTo(s * 9.6, -13.4); c.closePath(); });
  rr(c, M.wood, -5.6, -17, 11.2, 16, 2.2);
  f(c, "#b98048", () => c.roundRect(-5.6, -17, 3, 16, [2.2, 0, 0, 2.2]));
  f(c, "#c0392b", () => c.rect(-5.6, -15.4, 11.2, 2)); f(c, "#3a8a8a", () => c.rect(-5.6, -8.2, 11.2, 2));
  f(c, M.woodD, () => c.rect(-5.6, -9.6, 11.2, 1.2));
  for (const y of [-12.6, -5.4]) { rr(c, "#fff6c8", -3.8, y, 2.6, 2.6, 0.6); rr(c, "#fff6c8", 1.2, y, 2.6, 2.6, 0.6); }
  ci(c, P.orbEl ? orbPair(P)[0] : "#7dffb0", 0, -18.4, 2.5);
}
const STAFF: Builder = (r, P) => {
  const [e1] = orbPair(P), head = r.form === "scepter" ? R45(0, -13) : r.form === "wand" ? R45(0, -15.6) : R45(0, -13.6);
  if (r.form === "totem") return { d: (c, o) => up(c, (x) => totemArt(x, o, P)) };
  const art: DrawFn = r.form === "scepter" ? (x, o) => scepterArt(x, o, P) : r.form === "wand" ? (x, o) => wandArt(x, o, P) : staffArt(P.orbEl, P);
  return { d: (c, o) => up(c, (x) => art(x, o)), pre: (c) => glow(c, head[0], head[1], r.form === "wand" ? 9 : 12, e1, 0.6),
    post: r.form === "wand" ? (c, o) => { if (!o.small) { sparkle(c, "#ffffff", head[0] + 6.4, head[1] - 5.4, 2.4); sparkle(c, "#ffffff", head[0] - 7.4, head[1] - 1.4, 1.8); } } : undefined };
};

// =====================================================================
// 副手：圓盾、鳶盾／塔盾、法書、法器珠。全部直立。
// =====================================================================
/** 木圓盾：淺木色的邊、木色盾面（兩道木板縫）、金色盾心。包鐵圓盾：鋼箍（八顆鉚釘）、鐵十字箍、鋼盾心。 */
function roundShield(c: Ctx, o: QOpts, P: QPal, banded: boolean): void {
  ci(c, banded ? M.steel : mix(P.a, "#ffffff", 0.36), 24, 24, 20);
  if (!banded) st(c, P.d, 1, (x) => x.arc(24, 24, 16.9, 0, TAU), "butt");
  ci(c, P.a, 24, 24, banded ? 15.6 : 16.4);
  c.save(); c.beginPath(); c.arc(24, 24, banded ? 15.6 : 16.4, 0, TAU); c.clip();
  f(c, mix(P.a, "#ffffff", 0.2), () => c.rect(6, 6, 10, 36)); f(c, SH, () => c.rect(32.5, 6, 10, 36));
  if (!banded && !o.small) for (const x of [17.4, 30]) f(c, P.d, () => c.rect(x, 6, 1.3, 36));
  if (banded) { f(c, M.iron, () => c.rect(21.4, 6, 5.2, 36)); f(c, M.iron, () => c.rect(6, 21.4, 36, 5.2)); }
  c.restore();
  if (banded) { st(c, M.steelD, 1.2, (x) => x.arc(24, 24, 15.9, 0.2, Math.PI * 0.8), "butt"); if (!o.small) for (let i = 0; i < 8; i++) ci(c, M.ironD, 24 + Math.cos(((i + 0.5) * TAU) / 8) * 17.8, 24 + Math.sin(((i + 0.5) * TAU) / 8) * 17.8, 1.1); st(c, HI2, 1.2, (x) => x.arc(24, 24, 18.6, Math.PI * 1.05, Math.PI * 1.45), "butt"); }
  ci(c, banded ? M.steel : GOLD, 24, 24, banded ? 5.6 : 5.2); ci(c, banded ? M.steelD : "#b8862a", 24, 24, banded ? 2.2 : 0); ci(c, HI2, 22.4, 22.2, 1.5);
}
/** 鳶盾：平頂、兩肩直下、尖底；深一階的邊、盾面、一個米白十字。 */
function kiteShield(c: Ctx, o: QOpts, P: QPal): void {
  const K = (k: number): Pt[] => [[24 - 15 * k, 24.5 - 19 * k], [24 + 15 * k, 24.5 - 19 * k], [24 + 14 * k, 24.5 + 4.5 * k], [24, 24.5 + 19.5 * k], [24 - 14 * k, 24.5 + 4.5 * k]];
  poly(c, P.d, K(1), 1.4); poly(c, P.a, K(0.74), 0.8);
  c.save(); c.beginPath(); K(0.78).forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.closePath(); c.clip();
  f(c, mix(P.a, "#ffffff", 0.22), () => c.rect(0, 0, 17.4, 48)); f(c, SH, () => c.rect(30.6, 0, 18, 48)); c.restore();
  rr(c, CREAM, 22, 10.5, 4, 26.5, 1); rr(c, CREAM, 13.6, 16.6, 20.8, 4, 1);
  if (!o.small) f(c, "#ffffff", () => c.rect(22.7, 11.4, 1, 24.6));
}
/** 典籍：一本闔著的厚書——封面、書脊、書頁、金色圓章（中間一顆寶石）、金書角、紅書籤。 */
function tomeBook(c: Ctx, o: QOpts, P: QPal): void {
  rr(c, "#f2ead6", 12, 8.6, 28.6, 34.4, 2.4);
  if (!o.small) for (const y of [36.6, 39]) f(c, "#c8bc9c", () => c.rect(14, y, 25.6, 0.8));
  rr(c, "#c0392b", 28.6, 38, 3.6, 7.4, 1);
  rr(c, P.a, 8, 5, 28.6, 34.6, 2.6);
  f(c, P.d, () => c.roundRect(8, 5, 5, 34.6, [2.6, 0, 0, 2.6]));
  f(c, mix(P.a, "#ffffff", 0.22), () => c.rect(14.4, 6.6, 2, 31.4));
  if (!o.small) { poly(c, GOLD, [[36.6, 5], [36.6, 11], [30.6, 5]], 0.3); poly(c, GOLD, [[36.6, 39.6], [36.6, 33.6], [30.6, 39.6]], 0.3); }
  ci(c, GOLD, 24.6, 22.2, 6.2); poly(c, P.accent, [[24.6, 17.8], [28.4, 22.2], [24.6, 26.6], [20.8, 22.2]], 0.3); poly(c, HI2, [[24.6, 18.6], [24.6, 22.2], [21.8, 22.2]]);
}
/** 卷軸匣：直立的圓筒匣、上下金箍與筒蓋，側邊拉出一截米白的卷軸紙，筒身正中一顆寶石。 */
function tomeScroll(c: Ctx, o: QOpts, P: QPal): void {
  poly(c, "#f2ead6", [[29, 15.6], [42, 19], [42, 32], [29, 29.4]], 0.8);
  if (!o.small) { ln(c, "#a8987a", 1.1, [[32.4, 21.4], [39.4, 23.2]]); ln(c, "#a8987a", 1.1, [[32.4, 25.4], [38, 26.8]]); }
  f(c, "#d8ccb0", () => c.rect(39.6, 18.6, 2.6, 13.6));
  rr(c, P.d, 17.6, 2.6, 9.8, 5, 2); rr(c, P.d, 17.6, 40.4, 9.8, 5, 2);
  rr(c, P.a, 14.6, 6.4, 15.8, 35.2, 5);
  f(c, mix(P.a, "#ffffff", 0.24), () => c.rect(16.6, 9, 2.4, 30)); f(c, SH, () => c.roundRect(26.4, 6.4, 4, 35.2, [0, 5, 5, 0]));
  rr(c, GOLD, 13, 9.6, 19, 4.6, 1.8); rr(c, GOLD, 13, 33.8, 19, 4.6, 1.8);
  poly(c, P.accent, [[22.5, 19.4], [26, 24], [22.5, 28.6], [19, 24]], 0.3); poly(c, HI2, [[22.5, 20.2], [22.5, 24], [20, 24]]);
}
/** 水晶球：大水晶球坐在暗銅色的梯形底座上（骨材質是骨白；有元素換元素色）。 */
function orbBall(c: Ctx, o: QOpts, P: QPal): void {
  const [e1] = orbPair(P);
  poly(c, M.brass, [[14.5, 43.6], [33.5, 43.6], [30, 34.6], [18, 34.6]], 1); if (!o.small) f(c, GOLD, () => c.rect(18.6, 35, 10.8, 1.4));
  ci(c, e1, 24, 20.6, 15.4);
  f(c, "rgba(40,20,90,0.28)", () => { c.arc(24, 20.6, 15.4, -0.25, Math.PI * 0.8); c.closePath(); });
  st(c, mix(e1, "#ffffff", 0.5), 2.2, (x) => x.arc(24, 20.6, 9.4, Math.PI * 0.15, Math.PI * 0.7), "round");
  el(c, HI2, 17.4, 13.6, 3.2, 4.6, 0.6); if (!o.small) ci(c, HI2, 29.6, 27, 1.2);
}
/** 浮空寶珠：一顆浮在半空的寶珠，外面繞一圈斜的金環（前半圈壓在珠子前面），沒有底座。 */
function orbFloating(c: Ctx, o: QOpts, P: QPal): void {
  const [e1] = orbPair(P), ring = (x: Ctx, a0: number, a1: number): void => st(x, GOLD, 3.2, (k) => k.ellipse(24, 24.6, 20.4, 6.4, -0.3, a0, a1), "butt");
  ring(c, Math.PI, TAU);
  ci(c, e1, 24, 23.6, 12.6);
  f(c, "rgba(40,20,90,0.28)", () => { c.arc(24, 23.6, 12.6, -0.25, Math.PI * 0.8); c.closePath(); });
  el(c, HI2, 18.8, 18, 2.6, 3.8, 0.6);
  halo(c, o, (x) => { ring(x, 0, Math.PI); if (!o.small) st(x, GOLDL, 1, (k) => k.ellipse(24, 24.2, 20.2, 6.2, -0.3, Math.PI * 0.55, Math.PI * 0.95), "butt"); });
}
const OFF: Readonly<Record<string, Builder>> = {
  round_shield: (r, P) => ({ block: true, badge: 0.8, d: (c, o) => roundShield(c, o, P, r.form === "banded") }),
  kite_shield: (r, P) => (r.form === "tower" ? { block: true, badge: 0.87, d: (c, o) => towerShield(c, o, 24, 24, 1, 0, P.a, true) } : { block: true, badge: 0.86, d: (c, o) => kiteShield(c, o, P) }),
  tome: (r, P) => ({ block: true, badge: 0.84, d: r.form === "scroll" ? (c, o) => tomeScroll(c, o, P) : (c, o) => tomeBook(c, o, P) }),
  orb: (r, P) => ({ block: true, badge: r.form === "floating" ? 0.9 : 0.88, d: r.form === "floating" ? (c, o) => orbFloating(c, o, P) : (c, o) => orbBall(c, o, P), pre: (c) => glow(c, 24, r.form === "floating" ? 23.6 : 20.6, 23, orbPair(P)[0], 0.5), post: r.form === "floating" ? (c, o) => { if (!o.small) { sparkle(c, "#ffffff", 40, 9, 2.6); sparkle(c, "#ffffff", 8, 38, 2); } } : undefined }),
};
const BUILD: Readonly<Record<string, Builder>> = { sword: SWORD, greatsword: GREATSWORD, dagger: DAGGER, dual_dagger: DUAL_DAGGER, axe: AXE, hammer: HAMMER, spear: SPEAR, bow: BOW, crossbow: CROSSBOW, longgun: LONGGUN, shotgun: SHOTGUN, pistol: PISTOL, dual_pistol: DUAL_PISTOL, fist: FIST, scythe: SCYTHE, whip: WHIP, staff: STAFF, ...OFF };
const GUNS: ReadonlySet<string> = new Set(["longgun", "shotgun", "pistol", "dual_pistol"]);

/** 有 Q 版畫法的種類（武器、副手）。 */
export const hasQWeaponArt = (kind: string): boolean => BUILD[kind] !== undefined;

/** 一個圖樣定義（給 `render` 用）：meta.badge＝圓章裡的縮放、diag＝斜放、spots＝關鍵字小圖樣位置（48 格）、r＝畫的是哪一款。 */
export interface QWeaponDef {
  zh: string;
  d: DrawFn;
  pre?: DrawFn | undefined;
  post?: DrawFn | undefined;
  meta: { badge: number; diag: boolean; spots: Spots; r: QResolved };
}
const cache = new Map<string, QWeaponDef>();
/** 外觀 → 圖樣定義（同一組外觀共用；圓章縮放第一次會量一次圖樣範圍）。種類不是武器、副手時回傳 null。
 *  `icon`（QI-2c，樣張 `def(look, icon)`）：true（預設）＝裝備圖示（錘柄亮一階）；false＝技能主圖的道具（錘柄照舊 `M.shaft`，對上樣張第 3 批）。 */
export function qWeaponDef(r: QResolved, icon = true): QWeaponDef | null {
  const build = BUILD[r.kind], K = Q_WEAPON_KINDS[r.kind];
  if (build === undefined || K === undefined) return null;
  const key = [r.kind, r.form, r.material, r.keywords.join("+"), r.element ?? "", r.rarity, r.color ?? ""].join("|") + (icon ? "" : "|art");
  let hit = cache.get(key);
  if (!hit) { const b = build(r, qPalette(r), icon), isGun = GUNS.has(r.kind);
    hit = { zh: K.forms[r.form] ?? r.form, d: b.d, pre: b.pre, post: b.post, meta: { badge: badgeScale(b.d, b.badge ?? 1), diag: b.diag ?? (!!K.diag && !b.block), spots: b.spots ?? (isGun ? SPOTS.gun : K.diag ? SPOTS.diag : SPOTS.block), r } }; cache.set(key, hit); }
  return hit;
}
/** 清掉圖樣快取（測試換畫布時用：圓章縮放是量出來的）。 */
export const clearQWeaponDefs = (): void => cache.clear();
