// 開發用：RG-5 玩家大盾（#163 護陣：雲紋碑盾 sect_great、熔殼塔盾 molten_shell；`dev/rg5-shield-gallery.html`；不屬於正式 build）。
// 模式（?mode=）：
//   fp     「既有的不能變」指紋：現行武器、副手圖示（Q_WEAPON_KINDS 原有款 × 預設與全部材質 × 圓章 28／24／20、裝備格 64／48／42／32 × res 1／2）
//          ＋敵人持盾弟子整隻（GAME_HOOKS，4 方向 × 8 姿勢 × DPR 1／2／3）。一行一格「key fnv1a」，最後一行總指紋；改前改後文字必須相同。
//   pal    配色規則：遊戲端 sectPal／shellPal（紙娃娃）vs 樣張 sectPal／shellPal（材質色換成遊戲端 material.ts）。沒有關鍵字的應 SAME；
//          有元素關鍵字時紙娃娃混 45%（itemColors）、樣張用圖示的 40%，盾面／殼板會差一點（盾邊照材質本色，P-1，應相同）。
//   shield 只畫盾：樣張 FORMS[form].front／side／back(pal) vs 遊戲端 qSectShield／qMoltenShell（同一組 pal），
//          2 形制 × 12 種材質／關鍵字 × 3 方向 × 縮放 1、2、4 × DPR 1、2 × 錨點整數／小數，差異像素數（目標 0）。
//   doll   整隻玩家（hero_fighter）：遊戲端 qDoll＋樣張鑰匙色代理（RGPlayerShield.withShield 掛在塔盾流程上）vs 遊戲端 sect_great／molten_shell 分支，
//          2 形制 × 7 材質 × 4 方向 × 8 姿勢 × DPR 1～3。
//   icon   圖示：樣張 iconDef＋QIcons.render vs 遊戲端 qWeaponDef＋render（不含框；框是遊戲端現行的），裝備格 64／48／42／32、圓章 28／24／20 × res 1、2。
//   dolls｜materials｜icons  截圖用（遊戲端畫法）；（沒有 mode）樣張 vs 遊戲端並排。
// 重跑（無頭 Chrome）：chrome --headless=new --disable-gpu --mute-audio --dump-dom --virtual-time-budget=120000 "http://127.0.0.1:<port>/dev/rg5-shield-gallery.html?mode=fp&mute=1"
import currentSrc from "../../../docs/art/sample/current.js?raw";
import idleSrc from "../../../docs/art/sample/idleWeapons.js?raw";
import paperdollSrc from "../../../docs/art/sample/paperdoll.js?raw";
import qDollSrc from "../../../docs/art/sample/qDoll.js?raw";
import qIconsSrc from "../../../docs/art/sample/qIcons.js?raw";
import qIconsWeaponsSrc from "../../../docs/art/sample/qIconsWeapons.js?raw";
import raceArtSrc from "../../../docs/art/sample/raceArt.js?raw";
import rgPlayerShieldSrc from "../../../docs/art/sample/rgPlayerShield.js?raw";
import appearance from "../render/gearAppearance.json";
import type { DollSpec, GearItem } from "../render/appearance";
import { ELEMENT_OF_KEYWORD } from "../render/dollGear";
import { gearIconCanvas, resolveGear, type GearLook } from "../render/gearIcon";
import { weaponIdleFrame } from "../render/idleWeapons";
import { gaitPose } from "../render/motionClips";
import { S as QS, type QItem, type QPose, type QUnit, type QView } from "../render/qCore";
import { blit, GEAR_PAD, outlinePx, render } from "../render/qIcon/core";
import { qPalette, qResolve, qWeaponDef, type QResolved } from "../render/qIcon/weapons";
import { shellBack, shellFront, shellPal, shellSide } from "../render/qMoltenShell";
import { sampleHitPose } from "../render/qSample";
import { sectPal, sectShieldBack, sectShieldFront, sectShieldSide } from "../render/qSectShield";
import { GAME_HOOKS, qUnitOf } from "../render/qSpec";
import { qStamp } from "../render/qStamp";
import { resolveDollT } from "../render/testDolls";
import { weaponItemIconCanvas } from "../render/weaponIcon";

type C2 = CanvasRenderingContext2D;

const MODE = new URLSearchParams(location.search).get("mode") ?? "";
const out = document.createElement("pre");
out.id = "out";
const lines: string[] = [];
const log = (s: string): void => void lines.push(s);

// ---------- 共用 ----------
function cv(w: number, h: number): [HTMLCanvasElement, C2] {
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.ceil(w));
  c.height = Math.max(1, Math.ceil(h));
  return [c, c.getContext("2d")!];
}
function fnv(c: HTMLCanvasElement): string {
  const d = c.getContext("2d")!.getImageData(0, 0, c.width, c.height).data;
  let h = 0x811c9dc5;
  for (let i = 0; i < d.length; i++) {
    h ^= d[i]!;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}
const VIEWS: ReadonlyArray<readonly [QView, boolean, string]> = [
  ["front", false, "front"],
  ["back", false, "back"],
  ["side", false, "east"],
  ["side", true, "west"],
];
function poses(view: QView): ReadonlyArray<readonly [string, QPose | null]> {
  const idle = (ms: number): QPose => weaponIdleFrame("sword_shield", "rg5", ms, { view, breath: false, live: false }).pose as QPose;
  return [
    ["rest", null],
    ["idle0", idle(0)],
    ["idle700", idle(700)],
    ["idle1400", idle(1400)],
    ["walk", gaitPose(1.1, "walk") as QPose],
    ["slash", sampleHitPose("sword")],
    ["fb1-2", { fbk: 1, fbt: 2 } as QPose],
    ["fb1-4", { fbk: 1, fbt: 4 } as QPose],
  ];
}
function dollCanvas(draw: (g: C2) => void, dpr: number): HTMLCanvasElement {
  const [c, g] = cv(96 * dpr, 96 * dpr);
  g.scale(dpr, dpr);
  draw(g);
  return c;
}

// ---------- 敵人持盾弟子（同 rg4ShieldGallery） ----------
const SECT_LOOK = { skin: "#d9a47a", hair: "bun" as const, hairColor: "#1c1c22" };
const ROBE: GearItem = { kind: "robe", material: "cloth", color: "#5f8f8a", trim: "#dfe4e2" };
const SWORD: GearItem = { kind: "sword", material: "iron" };
const SECT_SHIELD: QItem = { kind: "shield_kite", form: "sect_great", material: "wood", color: "#5f8f8a", trim: "#dfe4e2", emblem: "peak" };
const gameSect = (): QUnit => qUnitOf({ look: { ...SECT_LOOK }, gear: { body: ROBE, main_hand: SWORD, off_hand: SECT_SHIELD as GearItem } });

// ---------- fp：既有的不能變 ----------
interface Form { id: string; zh: string; materials?: string[] }
interface Kind { id: string; slotType: string; forms: Form[]; materials: string[] }
/** RG-5 之前就有的款（新加的 sect_great、molten_shell 不算進「既有」）。 */
const NEW_FORMS: ReadonlySet<string> = new Set(["kite_shield/sect_great", "kite_shield/molten_shell"]);
function runFp(): void {
  let all = 0x811c9dc5;
  const push = (line: string): void => {
    log(line);
    for (let i = 0; i < line.length; i++) all = Math.imul(all ^ line.charCodeAt(i), 0x01000193) >>> 0;
  };
  const kinds = (appearance.kinds as unknown as Kind[]).filter((k) => k.slotType === "weapon" || k.slotType === "offhand");
  for (const k of kinds)
    for (const f of k.forms) {
      if (NEW_FORMS.has(`${k.id}/${f.id}`)) continue;
      for (const m of [undefined, ...(f.materials ?? k.materials)]) {
        const look = { kind: k.id, form: f.id, ...(m !== undefined ? { material: m } : {}) } as GearLook & GearItem;
        const hs: string[] = [];
        for (const res of [1, 2]) {
          for (const px of [28, 24, 20]) {
            const c = weaponItemIconCanvas(look, px, res);
            hs.push(c ? fnv(c) : "-");
          }
          for (const px of [64, 48, 42, 32]) {
            const c = gearIconCanvas(look, px, "main_hand", res);
            hs.push(c ? fnv(c) : "-");
          }
        }
        push(`icon ${k.id}/${f.id}/${m ?? "default"} ${hs.join(" ")}`);
      }
    }
  for (const [v, west, vk] of VIEWS)
    for (const [pk, pose] of poses(v)) {
      const hs = [1, 2, 3].map((dpr) => fnv(dollCanvas((g) => qStamp(g, gameSect(), v, 48, 78, 1, west, GAME_HOOKS, pose, { dpr }), dpr)));
      push(`disciple ${vk}/${pk} ${hs.join(" ")}`);
    }
  log(`TOTAL ${lines.length} lines ${all.toString(16).padStart(8, "0")}`);
}

// =====================================================================================
// RG-5：和樣張 docs/art/sample/rgPlayerShield.js（P-1、P-2 改完）逐像素比
// =====================================================================================
let sampleLoaded = false;
/** 樣張腳本以傳統 <script> 載入（共用全域詞法作用域）；材質色換成遊戲端（QIconsWeapons.palette → qPalette，material.ts）。 */
function loadSample(): void {
  if (sampleLoaded) return;
  for (const src of [currentSrc, raceArtSrc, paperdollSrc, qDollSrc, idleSrc, qIconsSrc, qIconsWeaponsSrc, rgPlayerShieldSrc]) {
    const s = document.createElement("script");
    s.textContent = src;
    document.head.appendChild(s);
  }
  const W = window as unknown as { QIconsWeapons: { palette: (r: QResolved) => unknown } };
  W.QIconsWeapons.palette = (r: QResolved) => qPalette({ ...r, color: null });
  sampleLoaded = true;
}
type AnyPal = Record<string, unknown>;
interface PS {
  FORMS: Record<FormId, { pal: (look: Look) => AnyPal; front: (c: C2, p: AnyPal) => void; side: (c: C2, p: AnyPal) => void; back: (c: C2, p: AnyPal) => void }>;
  withShield: (unit: unknown, view: string, fn: () => void) => void;
  offHand: (form: FormId, look: Look) => Record<string, unknown>;
  iconDef: (form: FormId, look: Look) => { d: unknown; meta: { badge: number } };
  sectPal: (look: Look) => AnyPal;
  shellPal: (look: Look) => AnyPal;
}
const PSH = (): PS => (window as unknown as { RGPlayerShield: PS }).RGPlayerShield;
type FormId = "sect_great" | "molten_shell";
interface Look {
  material: string;
  keywords: string[];
}
const FORMS: readonly FormId[] = ["sect_great", "molten_shell"];
/** 7 種材質（10.4 的表：五種材質＋鐵點燃＋鋼冰凍）＋ P-1 會翻面的組合（鐵、銅＋帶電／冰凍）。 */
const LOOKS: ReadonlyArray<readonly [string, Look]> = [
  ["iron", { material: "iron", keywords: [] }],
  ["steel", { material: "steel", keywords: [] }],
  ["copper", { material: "copper", keywords: [] }],
  ["silver", { material: "silver", keywords: [] }],
  ["gold", { material: "gold", keywords: [] }],
  ["iron+ignite", { material: "iron", keywords: ["ignite"] }],
  ["steel+frozen", { material: "steel", keywords: ["frozen"] }],
];
const LOOKS_P1: ReadonlyArray<readonly [string, Look]> = [
  ["iron+charged", { material: "iron", keywords: ["charged"] }],
  ["iron+frozen", { material: "iron", keywords: ["frozen"] }],
  ["copper+charged", { material: "copper", keywords: ["charged"] }],
  ["copper+frozen", { material: "copper", keywords: ["frozen"] }],
  ["gold+wet", { material: "gold", keywords: ["wet"] }],
];
/** 遊戲端的玩家副手（紙娃娃）：dollItem 的形狀（kind／form／material，元素關鍵字 → element）。 */
function gameItem(form: FormId, look: Look): QItem {
  const element = look.keywords.map((k) => ELEMENT_OF_KEYWORD[k]).find((e) => e !== undefined);
  return { kind: "shield_kite", form, material: look.material, ...(element !== undefined ? { element } : {}) };
}
/** 遊戲端的配色（紙娃娃那一條：hooks＝GAME_HOOKS，itemColors／material.ts）。qDoll 外面呼叫時 S.hooks 是 null，這裡暫時掛上。 */
function gamePal(form: FormId, it: QItem): AnyPal {
  const keep = QS.hooks;
  QS.hooks = GAME_HOOKS;
  try {
    return (form === "sect_great" ? sectPal(it) : shellPal(it)) as unknown as AnyPal;
  } finally {
    QS.hooks = keep;
  }
}
const GAME_PART: Record<FormId, Record<"front" | "side" | "back", (c: C2, it: QItem) => void>> = {
  sect_great: { front: sectShieldFront, side: sectShieldSide, back: sectShieldBack },
  molten_shell: { front: shellFront, side: shellSide, back: shellBack },
};
function diffPx(a: HTMLCanvasElement, b: HTMLCanvasElement): [number, number] {
  const A = a.getContext("2d")!.getImageData(0, 0, a.width, a.height).data;
  const B = b.getContext("2d")!.getImageData(0, 0, b.width, b.height).data;
  let n = 0;
  let maxd = 0;
  for (let i = 0; i < A.length; i += 4) {
    const d = Math.max(Math.abs(A[i]! - B[i]!), Math.abs(A[i + 1]! - B[i + 1]!), Math.abs(A[i + 2]! - B[i + 2]!), Math.abs(A[i + 3]! - B[i + 3]!));
    if (d > 0) n++;
    maxd = Math.max(maxd, d);
  }
  return [n, maxd];
}

// ---------- pal：配色規則（遊戲端 vs 樣張 sectPal／shellPal） ----------
function runPal(): void {
  loadSample();
  const ps = PSH();
  for (const form of FORMS)
    for (const [k, look] of [...LOOKS, ...LOOKS_P1]) {
      const g = gamePal(form, gameItem(form, look));
      const s = form === "sect_great" ? ps.sectPal(look) : ps.shellPal(look);
      const keys = form === "sect_great" ? ["face", "rim", "rivet", "ring"] : ["plate", "lit", "low", "inner", "edge"];
      const same = keys.every((x) => g[x] === s[x]);
      log(`pal ${form} ${k} game=${keys.map((x) => `${x}:${String(g[x])}`).join(",")} sample=${keys.map((x) => `${x}:${String(s[x])}`).join(",")} ${same ? "SAME" : "DIFF"}`);
    }
}

// ---------- shield：只畫盾（同一組 pal） ----------
function shieldPair(form: FormId, look: Look, view: "front" | "side" | "back", k: number, dpr: number, ax: number, ay: number): [HTMLCanvasElement, HTMLCanvasElement] {
  const it = gameItem(form, look);
  const pal = gamePal(form, it);
  const res: HTMLCanvasElement[] = [];
  for (const who of ["sample", "game"] as const) {
    const [c, g] = cv(44 * k * dpr, 44 * k * dpr);
    g.scale(k * dpr, k * dpr);
    g.translate(ax, ay);
    if (who === "sample") {
      g.save();
      PSH().FORMS[form][view](g, pal);
      g.restore();
    } else {
      const keep = QS.hooks;
      QS.hooks = GAME_HOOKS;
      GAME_PART[form][view](g, it);
      QS.hooks = keep;
    }
    res.push(c);
  }
  return [res[0]!, res[1]!];
}
function runShield(): void {
  loadSample();
  let total = 0;
  let cells = 0;
  for (const form of FORMS)
    for (const [lk, look] of [...LOOKS, ...LOOKS_P1])
      for (const view of ["front", "side", "back"] as const)
        for (const k of [1, 2, 4])
          for (const dpr of [1, 2])
            for (const [ax, ay] of [
              [22, 22],
              [22.3, 21.6],
            ] as const) {
              const [a, b] = shieldPair(form, look, view, k, dpr, ax, ay);
              const [n, m] = diffPx(a, b);
              total += n;
              cells++;
              log(`shield ${form} ${lk} ${view} k${k} dpr${dpr} anchor(${ax},${ay}) diff=${n} max=${m}`);
            }
  log(`SHIELD TOTAL cells=${cells} diff=${total}`);
}

// ---------- doll：整隻玩家（遊戲 qDoll ＋ 樣張鑰匙色代理 vs 遊戲端 sect_great／molten_shell 分支） ----------
const heroSpec = (): DollSpec => resolveDollT({ template: "hero_fighter", team: "ally", summon: false, weaponId: "one_handed_sword" });
const heroWith = (off: QItem): QUnit => {
  const u = qUnitOf(heroSpec());
  return { look: u.look, gear: { ...u.gear, off_hand: off } };
};
function runDoll(): void {
  loadSample();
  const ps = PSH();
  let total = 0;
  let cells = 0;
  for (const form of FORMS)
    for (const [lk, look] of LOOKS) {
      const it = gameItem(form, look);
      const pal = gamePal(form, it);
      const F = ps.FORMS[form];
      const orig = F.pal;
      F.pal = () => pal; // 鑰匙色代理畫的盾用遊戲端同一組配色（元素混色 45% 是紙娃娃的規則，和圖示的 40% 不同）
      const key = ps.offHand(form, look) as unknown as QItem;
      const proxy = heroWith(key);
      const game = heroWith(it);
      for (const [v, west, vk] of VIEWS)
        for (const [pk, pose] of poses(v))
          for (const dpr of [1, 2, 3]) {
            const a = dollCanvas((g) => ps.withShield({ gear: { off_hand: key } }, v, () => qStamp(g, proxy, v, 48, 78, 1, west, GAME_HOOKS, pose, { dpr })), dpr);
            const b = dollCanvas((g) => qStamp(g, game, v, 48, 78, 1, west, GAME_HOOKS, pose, { dpr }), dpr);
            const [n, m] = diffPx(a, b);
            total += n;
            cells++;
            if (n > 0) log(`doll ${form} ${lk} ${vk}/${pk} dpr${dpr} diff=${n} max=${m}`);
          }
      F.pal = orig;
      log(`doll ${form} ${lk} done`);
    }
  log(`DOLL TOTAL cells=${cells} diff=${total}`);
}

// ---------- icon：圖示（樣張 iconDef ＋ QIcons.render vs 遊戲端 qWeaponDef ＋ render） ----------
interface QIconsG {
  render: (def: unknown, px: number, res: number, opt: Record<string, unknown>) => HTMLCanvasElement;
  outlinePx: (px: number) => number;
}
const gameDef = (form: FormId, look: Look) => qWeaponDef(qResolve({ kind: "kite_shield", form, material: look.material, keywords: look.keywords, rarity: "common" }))!;
/** 兩種框裡的圖樣（不含框）：裝備格＝邊長 px×(1−2×GEAR_PAD)、無 ow；圓章＝px×badge、ow＝outlinePx(px)、badge。 */
function iconPair(form: FormId, look: Look, frame: "gear" | "badge", px: number, res: number): [HTMLCanvasElement, HTMLCanvasElement, number, number] {
  const sd = PSH().iconDef(form, look);
  const gd = gameDef(form, look);
  const QI = (window as unknown as { QIcons: QIconsG }).QIcons;
  if (frame === "gear") {
    const a = px - px * GEAR_PAD * 2;
    return [QI.render(sd, a, res, {}), render(gd, a, res, {})!, sd.meta.badge, gd.meta.badge];
  }
  return [QI.render(sd, px * sd.meta.badge, res, { ow: QI.outlinePx(px), badge: true }), render(gd, px * gd.meta.badge, res, { ow: outlinePx(px), badge: true })!, sd.meta.badge, gd.meta.badge];
}
function runIcon(): void {
  loadSample();
  let total = 0;
  let cells = 0;
  for (const form of FORMS)
    for (const [lk, look] of [...LOOKS, ...LOOKS_P1])
      for (const [frame, px] of [["gear", 64], ["gear", 48], ["gear", 42], ["gear", 32], ["badge", 28], ["badge", 24], ["badge", 20]] as const)
        for (const res of [1, 2]) {
          const [a, b, sb, gb] = iconPair(form, look, frame, px, res);
          const [n, m] = a.width === b.width ? diffPx(a, b) : [-1, -1];
          total += Math.max(0, n);
          cells++;
          log(`icon ${form} ${lk} ${frame}${px} res${res} badge=${sb}/${gb} diff=${n} max=${m}`);
        }
  log(`ICON TOTAL cells=${cells} diff=${total}`);
}

// ---------- 看圖、截圖 ----------
function sec(title: string): HTMLDivElement {
  const h = document.createElement("h2");
  h.textContent = title;
  document.body.appendChild(h);
  const row = document.createElement("div");
  row.className = "row";
  document.body.appendChild(row);
  return row;
}
/** 放一張畫布：z＝顯示倍數（最近鄰），畫布像素＝CSS 像素 × res。 */
function put(row: HTMLElement, c: HTMLCanvasElement, cap: string, z = 1, res = 1): void {
  const d = document.createElement("div");
  d.className = "cell";
  c.style.width = `${(c.width / res) * z}px`;
  c.style.height = `${(c.height / res) * z}px`;
  d.appendChild(c);
  const t = document.createElement("div");
  t.textContent = cap;
  d.appendChild(t);
  row.appendChild(d);
}
const ZH: Record<FormId, string> = { sect_great: "雲紋碑盾", molten_shell: "熔殼塔盾" };
/** 一隻 48 格的玩家紙娃娃（DPR dpr），idle＝劍盾待機第 ms 毫秒。 */
function heroCanvas(it: QItem, v: QView, west: boolean, dpr: number, pose: QPose | null): HTMLCanvasElement {
  return dollCanvas((g) => qStamp(g, heroWith(it), v, 48, 78, 1, west, GAME_HOOKS, pose, { dpr }), dpr);
}
const idlePose = (v: QView, ms: number): QPose => weaponIdleFrame("sword_shield", "rg5", ms, { view: v, breath: false, live: false }).pose as QPose;
/** 最近鄰放大（真 1 倍 → ×k）。 */
function nearest(src: HTMLCanvasElement, k: number): HTMLCanvasElement {
  const [c, g] = cv(src.width * k, src.height * k);
  g.imageSmoothingEnabled = false;
  g.drawImage(src, 0, 0, c.width, c.height);
  return c;
}
function showDolls(): void {
  for (const form of FORMS) {
    const it = gameItem(form, { material: "iron", keywords: [] });
    const r1 = sec(`玩家（hero_fighter）拿${ZH[form]}（鐵）：真 1 倍（DPR 1）`);
    for (const [v, west, vk] of VIEWS) for (const ms of [0, 700]) put(r1, heroCanvas(it, v, west, 1, idlePose(v, ms)), `${vk} 待機 ${ms}`);
    const r2 = sec(`同上 最近鄰 ×4`);
    for (const [v, west, vk] of VIEWS) put(r2, nearest(heroCanvas(it, v, west, 1, idlePose(v, 0)), 4), vk);
    const r3 = sec(`同上 向量 ×4（DPR 4）`);
    for (const [v, west, vk] of VIEWS) put(r3, heroCanvas(it, v, west, 4, idlePose(v, 0)), vk, 1, 1);
  }
}
function showMaterials(): void {
  for (const form of FORMS) {
    const r1 = sec(`${ZH[form]} × 7 種材質：正面、側面、背面 真 1 倍（DPR 1）`);
    for (const [lk, look] of LOOKS) for (const [v, west] of [["front", false], ["side", false], ["back", false]] as const) put(r1, heroCanvas(gameItem(form, look), v, west, 1, null), `${lk} ${v}`);
    const r2 = sec(`同上 向量 ×3（DPR 3）`);
    for (const [lk, look] of LOOKS) for (const [v, west] of [["front", false], ["side", false]] as const) put(r2, heroCanvas(gameItem(form, look), v, west, 3, null), `${lk} ${v}`);
  }
}
/** 遊戲端的含框圖示（weaponIcon／gearIcon 的同一條路：qWeaponDef → render → blit；框是遊戲端的）。gearAppearance.json 還沒有這兩個形制時 resolveGear 會退回鳶盾，所以這裡直接用 qWeaponDef。 */
function gameIcon(form: FormId, look: Look, frame: "gear" | "badge", px: number, res: number): HTMLCanvasElement {
  const def = gameDef(form, look);
  const [c, g] = cv(Math.round(px * res), Math.round(px * res));
  g.scale(res, res);
  if (frame === "badge") {
    const grd = g.createRadialGradient(px / 2, px * 0.42, 0, px / 2, px / 2, px / 2);
    grd.addColorStop(0, "#f6eed8");
    grd.addColorStop(1, "#d6c7a2");
    g.fillStyle = grd;
    g.beginPath();
    g.arc(px / 2, px / 2, px / 2, 0, Math.PI * 2);
    g.fill();
    const a = px * def.meta.badge;
    blit(g, render(def, a, res, { ow: outlinePx(px), badge: true })!, (px - a) / 2, (px - a) / 2, a, res);
  } else {
    const lookG = { kind: "kite_shield", form, material: look.material, keywords: look.keywords, rarity: "common" } as GearLook;
    const framed = gearIconCanvas(lookG, px, "off_hand", res);
    if (framed !== null && resolveGear(lookG, "off_hand").form === form) g.drawImage(framed, 0, 0, px, px);
    else {
      g.fillStyle = "#2a2d34";
      g.fillRect(0, 0, px, px);
      const p = px * GEAR_PAD;
      blit(g, render(def, px - p * 2, res, {})!, p, p, px - p * 2, res);
    }
  }
  return c;
}
function showIcons(): void {
  for (const res of [2, 1]) {
    const r = sec(`圖示：裝備格 64／48／42／32、圓章 28／24／20（${res === 2 ? "DPR 2 原大" : "真 1 倍 ×4 最近鄰"}）`);
    for (const form of FORMS)
      for (const [frame, px] of [["gear", 64], ["gear", 48], ["gear", 42], ["gear", 32], ["badge", 28], ["badge", 24], ["badge", 20]] as const) {
        const c = gameIcon(form, { material: "iron", keywords: [] }, frame, px, res);
        put(r, res === 1 ? nearest(c, 4) : c, `${ZH[form]} ${frame}${px}`, 1, res === 1 ? 1 : 2);
      }
  }
  for (const form of FORMS) {
    const r = sec(`${ZH[form]} × 7 種材質：裝備格 32、背包 42、圓章 20 真 1 倍 ×4`);
    for (const [lk, look] of LOOKS)
      for (const [frame, px] of [["gear", 32], ["gear", 42], ["badge", 20]] as const) put(r, nearest(gameIcon(form, look, frame, px, 1), 4), `${lk} ${frame}${px}`);
  }
}
function showCompare(): void {
  loadSample();
  const r1 = sec("樣張 vs 遊戲端：盾 ×4、DPR 2（鐵、金、鋼＋冰凍）");
  for (const form of FORMS)
    for (const [lk, look] of [LOOKS[0]!, LOOKS[4]!, LOOKS[6]!])
      for (const view of ["front", "side", "back"] as const) {
        const [a, b] = shieldPair(form, look, view, 4, 2, 22, 22);
        put(r1, a, `樣張 ${form} ${lk} ${view}`, 1, 2);
        put(r1, b, `遊戲 diff=${diffPx(a, b)[0]}`, 1, 2);
      }
  const r2 = sec("樣張 vs 遊戲端：圖示裝備格 48（DPR 2）");
  for (const form of FORMS)
    for (const [lk, look] of LOOKS) {
      const [a, b] = iconPair(form, look, "gear", 48, 2);
      put(r2, a, `樣張 ${lk}`, 1, 2);
      put(r2, b, `遊戲 diff=${diffPx(a, b)[0]}`, 1, 2);
    }
}

try {
  if (MODE === "fp") runFp();
  else if (MODE === "pal") runPal();
  else if (MODE === "shield") runShield();
  else if (MODE === "doll") runDoll();
  else if (MODE === "icon") runIcon();
  else if (MODE === "dolls") showDolls();
  else if (MODE === "materials") showMaterials();
  else if (MODE === "icons") showIcons();
  else showCompare();
} catch (e) {
  log(`ERROR ${(e as Error).stack ?? String(e)}`);
}
out.textContent = lines.join("\n");
document.body.appendChild(out);
document.body.dataset["done"] = "1";
