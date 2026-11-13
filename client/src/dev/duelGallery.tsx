// 開發用：RG-4 精英單挑插圖 A 暮色對峙（`dev/duel-gallery.html`；不屬於正式 build）。
// 模式（?mode=）：
//   diff    和樣張逐像素比對（目標 0）：四場（北坡狼王、疤面、熔核領主、荒原精英；spec 照 docs/art/sample/rg-duel-dialog.html 的 ELITES，
//           主角 hero_fighter＋steel sword）× DPR 1、2 的整張 duelCanvas；獸爪單獨（48 格，px 48、58 × res 1、2）；
//           另外逐項比（歸因用）：主角／精英剪影（cv、seam）、交叉的武器圖示、紙娃娃小人本身（樣張 QDoll.stamp／QNpc.stamp vs 遊戲端 qStamp）。
//           輸出 `<pre id="out">`。
//   weapons RG-6 主手不是劍：主角剪影 20 種（只比 alpha）、整張 劍／弓／斧／法杖／雙手槍 × 狼王／疤面、整組移量表（res 1、2；9.9.10）和樣張比。
//   sheet   &part=all｜cmp｜x4｜small｜sil｜contact｜silcmp：拼圖 PNG 的 dataURL 輸出到 #out（真 1 倍；截圖腳本存檔）。
//   dialog  正式的遇敵卡（EncounterPanel）＋單挑段＋插圖，假資料（&e=wolf｜lord｜scar｜forge，&hw=<主手 kind>（RG-6；預設單手劍），&w=1600｜800 只決定卡片外的舞台寬；&duel=none 沒有單挑提議，看「開戰」主鈕對照）。
//   fp      劍版指紋（RG-6：改非劍主手前後要逐字相同）：四場 × DPR 1、2 的整張 duelCanvas FNV-1a（同樣張 rg-duel-weapons.html 的 fnv），
//           兩條路：dev＝上面 diff 的 spec（樣張 hero_fighter、SAMPLE_HOOKS）、game＝dialog 的假 WorldView 經 duelPlan → duelSpecOf（GAME_HOOKS）。
//   （沒有 mode）並排看圖：四場樣張（上）vs 遊戲端（下），DPR 2；獸爪 ×4。
// 重跑（無頭 Chrome，一定要 --disable-gpu）：chrome --headless=new --disable-gpu --dump-dom --virtual-time-budget=60000 "http://127.0.0.1:<port>/dev/duel-gallery.html?mode=diff&mute=1"
import { createRoot } from "react-dom/client";
import currentSrc from "../../../docs/art/sample/current.js?raw";
import raceArtSrc from "../../../docs/art/sample/raceArt.js?raw";
import paperdollSrc from "../../../docs/art/sample/paperdoll.js?raw";
import qDollSrc from "../../../docs/art/sample/qDoll.js?raw";
import storyDollSrc from "../../../docs/art/sample/storyDoll.js?raw";
import realmsSrc from "../../../docs/art/sample/realms.js?raw";
import enemyArtSrc from "../../../docs/art/sample/enemyArt.js?raw";
import qCreatureSrc from "../../../docs/art/sample/qCreature.js?raw";
import qCreatureAnimSrc from "../../../docs/art/sample/qCreatureAnim.js?raw";
import qBossSrc from "../../../docs/art/sample/qBoss.js?raw";
import qNpcSrc from "../../../docs/art/sample/qNpc.js?raw";
import qIconsSrc from "../../../docs/art/sample/qIcons.js?raw";
import qIconsWeaponsSrc from "../../../docs/art/sample/qIconsWeapons.js?raw";
import occludeSrc from "../../../docs/art/sample/occludeOutline.js?raw";
import rgUnitsSrc from "../../../docs/art/sample/rgUnits.js?raw";
import type { WorldView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import { beastClawCanvas, duelCanvas, duelSilhouette, GROUP_POSE, HERO_K, HERO_POSE, HUMANOID_ELITE_K, propOf, silGroup, type DuelFigure, type DuelFit, type DuelMain, type DuelSpec, type DuelWeapon } from "../render/duelArt";
import { resolveGear } from "../render/gearResolve";
import { resolveCreature } from "../render/inkCreature";
import type { QUnit } from "../render/qCore";
import { render } from "../render/qIcon/core";
import { qResolve, qWeaponDef } from "../render/qIcon/weapons";
import { SAMPLE_HOOKS } from "../render/qSample";
import { qStamp } from "../render/qStamp";
import { drawQ } from "../render/qDoll";
import { useRegionTheme } from "../ui/regionTheme";
import { EncounterPanel } from "../world/WorldPanel";
import { duelPlan } from "../world/duelArtPlan";
import { duelSpecOf } from "../world/DuelArt";
import "../styles/index.css";

type C2 = CanvasRenderingContext2D;
type Any = Record<string, unknown>;
interface RG {
  duelCanvas: (spec: unknown, res: number) => HTMLCanvasElement;
  silhouetteOf: (who: unknown, cx: number, foot: number, k: number, res: number) => { cv: HTMLCanvasElement; seam: HTMLCanvasElement | null };
  beastClaw: (g: C2, px: number) => void;
}
interface W {
  RGUnits: RG;
  PaperDoll: { TEMPLATES: Record<string, Any> };
  QNpc: { BANDITS: Record<string, [string, Array<[string, string, Any]>]>; stamp: (...a: unknown[]) => void };
  QDoll: { stamp: (...a: unknown[]) => void; setPose: (p: unknown) => void };
  QIconsWeapons: { paint: (g: C2, look: unknown, px: number, res: number, opt: unknown) => void };
}
const win = (): W => window as unknown as W;

const P = new URLSearchParams(location.search);
const MODE = P.get("mode") ?? "";
setGlossary(glossary as never);

const lines: string[] = [];
const log = (s: string): void => void lines.push(s);

// ---------- 共用 ----------
function cv(w: number, h: number): [HTMLCanvasElement, C2] {
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.round(w));
  c.height = Math.max(1, Math.round(h));
  return [c, c.getContext("2d")!];
}
function diffMask(a: HTMLCanvasElement, b: HTMLCanvasElement): Uint8Array | null {
  if (a.width !== b.width || a.height !== b.height) return null;
  const A = a.getContext("2d")!.getImageData(0, 0, a.width, a.height).data;
  const B = b.getContext("2d")!.getImageData(0, 0, b.width, b.height).data;
  const m = new Uint8Array(A.length / 4);
  for (let i = 0; i < m.length; i++) m[i] = A[i * 4] !== B[i * 4] || A[i * 4 + 1] !== B[i * 4 + 1] || A[i * 4 + 2] !== B[i * 4 + 2] || A[i * 4 + 3] !== B[i * 4 + 3] ? 1 : 0;
  return m;
}
/** 只比 alpha（形狀一樣、只有顏色不同時是 0）。 */
function alphaDiff(a: HTMLCanvasElement, b: HTMLCanvasElement): number {
  const A = a.getContext("2d")!.getImageData(0, 0, a.width, a.height).data;
  const B = b.getContext("2d")!.getImageData(0, 0, b.width, b.height).data;
  let n = 0;
  for (let i = 3; i < A.length; i += 4) if (A[i] !== B[i]) n++;
  return n;
}
const count = (m: Uint8Array | null): number => (m === null ? -1 : m.reduce((s, v) => s + v, 0));
const diffPx = (a: HTMLCanvasElement, b: HTMLCanvasElement): number => count(diffMask(a, b));
/** 差異像素的外框（裝置像素）。 */
function bbox(m: Uint8Array | null, w: number): string {
  if (m === null) return "size-mismatch";
  let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
  for (let i = 0; i < m.length; i++)
    if (m[i]) {
      const x = i % w, y = Math.floor(i / w);
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    }
  return x1 < 0 ? "-" : `x${x0}-${x1} y${y0}-${y1}`;
}

let sampleLoaded = false;
/** 樣張腳本照 rg-duel-dialog.html 的順序以傳統 <script> 載入（共用全域詞法作用域；背景用的 explore／regions4／cloudTiles／obSamples 不載）。 */
function loadSample(): void {
  if (sampleLoaded) return;
  for (const src of [currentSrc, raceArtSrc, paperdollSrc, qDollSrc, storyDollSrc, realmsSrc, enemyArtSrc, qCreatureSrc, qCreatureAnimSrc, qBossSrc, qNpcSrc, qIconsSrc, qIconsWeaponsSrc, occludeSrc, rgUnitsSrc]) {
    const s = document.createElement("script");
    s.textContent = src;
    document.head.appendChild(s);
  }
  sampleLoaded = true;
}

// ---------- 四場（rg-duel-dialog.html 的 ELITES） ----------
const HERO_WEAPON = { kind: "sword", material: "steel" };
interface Scene {
  id: string;
  zh: string;
  region: string;
  sampleElite: () => Any;
  gameElite: () => { figure: DuelFigure; weapon: DuelWeapon | null };
}
const npcb = (zh: string): Any => {
  const all = Object.values(win().QNpc.BANDITS).flatMap(([, list]) => list);
  return all.find(([n]) => n === zh)![2];
};
const iconOf = (look: Any): DuelWeapon | null => {
  const def = qWeaponDef(qResolve(resolveGear(look as never, "main_hand"), (look["element"] as string | undefined) ?? null));
  return def === null ? null : { kind: "icon", def };
};
const CLAW: DuelWeapon = { kind: "beast_claw" };
const WOLF = { body: "hound", material: "fur", tint: "#c8ccd0", size: "large", traits: ["mist", "scar"] };
const LORD = { body: "crawler", variant: "beetle", material: "magma", size: "large", traits: ["lava_pool"] };
const SCENES: readonly Scene[] = [
  {
    id: "wolf",
    zh: "北坡狼王",
    region: "cloud_ridge",
    sampleElite: () => ({ spec: { ...WOLF, elite: true, affixes: ["berserk"] }, weapon: { kind: "beast_claw" }, k: 1.2 }),
    gameElite: () => ({ figure: { kind: "creature", creature: resolveCreature({ look: WOLF, elite: true, affixes: ["berserk"] }), k: 1.2 }, weapon: CLAW }),
  },
  {
    id: "scar",
    zh: "疤面",
    region: "cloud_ridge",
    sampleElite: () => ({ npc: npcb("斷崖幫隊長"), weapon: { kind: "saber", material: "steel" } }),
    gameElite: () => ({ figure: { kind: "doll", unit: npcb("斷崖幫隊長") as unknown as QUnit }, weapon: iconOf({ kind: "saber", material: "steel" }) }),
  },
  {
    id: "lord",
    zh: "熔核領主",
    region: "ashen_waste",
    sampleElite: () => ({ spec: { ...LORD, elite: true, affixes: ["hardshell"] }, weapon: { kind: "beast_claw" }, k: 1.8 }),
    gameElite: () => ({ figure: { kind: "creature", creature: resolveCreature({ look: LORD, elite: true, affixes: ["hardshell"] }), k: 1.8 }, weapon: CLAW }),
  },
  {
    id: "forge",
    zh: "荒原精英（鍛疤暫代）",
    region: "ashen_waste",
    sampleElite: () => ({ npc: npcb("荒原隊長"), weapon: { kind: "shotgun", form: "double", material: "iron" } }),
    gameElite: () => ({ figure: { kind: "doll", unit: npcb("荒原隊長") as unknown as QUnit }, weapon: iconOf({ kind: "shotgun", form: "double", material: "iron" }) }),
  },
];
const heroUnit = (): QUnit => win().PaperDoll.TEMPLATES["hero_fighter"] as unknown as QUnit;
const sampleSpec = (s: Scene): Any => ({ hero: { doll: heroUnit(), weapon: HERO_WEAPON }, elite: s.sampleElite(), region: s.region, variant: "A" });
const gameSpec = (s: Scene): DuelSpec => ({ hero: { unit: heroUnit(), weapon: iconOf(HERO_WEAPON) }, elite: s.gameElite(), region: s.region, hooks: SAMPLE_HOOKS });

// ---------- diff ----------
function sampleWeapon(look: Any, px: number, res: number): HTMLCanvasElement {
  const [c, g] = cv(px * res, px * res);
  g.scale(res, res);
  if (look["kind"] === "beast_claw") win().RGUnits.beastClaw(g, px);
  else win().QIconsWeapons.paint(g, look, px, res, { frame: "none" });
  return c;
}
function gameWeapon(w: DuelWeapon, px: number, res: number): HTMLCanvasElement {
  if (w.kind === "beast_claw") return beastClawCanvas(px, res)!;
  const [c, g] = cv(px * res, px * res);
  g.scale(res, res);
  const art = render(w.def, px, res, {});
  if (art) g.drawImage(art, 0, 0, px, px);
  return c;
}
function stampPair(unit: QUnit, npc: boolean, west: boolean, k: number, res: number, pose: Any | null): [HTMLCanvasElement, HTMLCanvasElement] {
  const R = Math.max(3, res * 2);
  const [a, ga] = cv(160 * R, 130 * R);
  ga.scale(R, R);
  if (npc) win().QNpc.stamp(ga, unit, "side", 80, 120, k, west, { dpr: R * 1.5 });
  else {
    if (pose) win().QDoll.setPose(pose);
    try {
      win().QDoll.stamp(ga, unit, "side", 80, 120, k, west, { dpr: R * 1.5 });
    } finally {
      if (pose) win().QDoll.setPose(null);
    }
  }
  const [b, gb] = cv(160 * R, 130 * R);
  gb.scale(R, R);
  qStamp(gb, unit, "side", 80, 120, k, west, SAMPLE_HOOKS, pose as never, { dpr: R * 1.5 });
  return [a, b];
}
/**
 * 整張的差異像素裡，「不在交叉武器那一塊（中心 ±40 px）、也不在精英剪影（兩邊的剪影聯集、含輪廓光位移、外擴 2 px）上」的有幾個。
 * 0 ＝差異全部來自武器圖示與精英剪影（逐項比對見下面 part 列）。
 */
function unexplained(s: Scene, res: number, m: Uint8Array | null): number {
  if (m === null) return -1;
  const rg = win().RGUnits;
  const se = s.sampleElite();
  const ge = s.gameElite();
  const k = ge.figure.kind === "creature" ? ge.figure.k : HUMANOID_ELITE_K;
  const ss = rg.silhouetteOf(se["spec"] ? { spec: se["spec"], west: true } : { npc: se["npc"], view: "side", west: true }, 250, 112, k, res);
  const gs = duelSilhouette(ge.figure, true, 250, 112, k, res, SAMPLE_HOOKS);
  const [c, g] = cv(320 * res, 120 * res);
  g.scale(res, res);
  for (const sil of [ss.cv, gs.cv]) for (const [dx, dy] of [[0, 0], [-1.6, -0.6]]) for (const [ex, ey] of [[0, 0], [2, 0], [-2, 0], [0, 2], [0, -2], [1.5, 1.5], [-1.5, 1.5], [1.5, -1.5], [-1.5, -1.5]]) g.drawImage(sil, 250 - 80 + dx! + ex!, 112 - 120 + dy! + ey!, 160, 130);
  g.fillStyle = "#000";
  g.fillRect(160 - 40, 56 - 40, 80, 80);
  const A = g.getImageData(0, 0, c.width, c.height).data;
  let n = 0;
  for (let i = 0; i < m.length; i++) if (m[i] && A[i * 4 + 3] === 0) n++;
  return n;
}
function runDiff(): void {
  loadSample();
  const rg = win().RGUnits;
  let total = 0;
  for (const s of SCENES)
    for (const res of [1, 2]) {
      const a = rg.duelCanvas(sampleSpec(s), res);
      const b = duelCanvas(gameSpec(s), res)!;
      const m = diffMask(a, b);
      const n = count(m);
      total += n;
      log(`duel ${s.id} dpr${res} diff=${n} bbox=${bbox(m, a.width)} (${a.width}x${a.height}) unexplained=${unexplained(s, res, m)}`);
    }
  log(`DUEL TOTAL diff=${total}`);
  let ct = 0;
  for (const px of [48, 58])
    for (const res of [1, 2]) {
      const n = diffPx(sampleWeapon({ kind: "beast_claw" }, px, res), beastClawCanvas(px, res)!);
      ct += n;
      log(`beastClaw px${px} res${res} diff=${n}`);
    }
  log(`BEASTCLAW TOTAL diff=${ct}`);
  // ---- 歸因：逐項 ----
  {
    // 樣張自己：同一個人形走 QNpc.stamp（npc）與 QDoll.stamp（doll）兩條路的剪影差（遊戲端只有一條路＝qDoll）
    const noDouli = (u: Any): Any => { const gear = { ...(u["gear"] as Any) }; delete gear["head"]; return { ...u, gear }; };
    for (const res of [1, 2])
      for (const [id, u] of [["forge", npcb("荒原隊長")], ["scar-no-douli", noDouli(npcb("斷崖幫隊長"))]] as const) {
        const viaNpc = win().RGUnits.silhouetteOf({ npc: u, view: "side", west: true }, 250, 112, HUMANOID_ELITE_K, res);
        const viaDoll = win().RGUnits.silhouetteOf({ doll: u, view: "side", west: true }, 250, 112, HUMANOID_ELITE_K, res);
        const game = duelSilhouette({ kind: "doll", unit: u as unknown as QUnit }, true, 250, 112, HUMANOID_ELITE_K, res, SAMPLE_HOOKS);
        log(`part npcpath ${id} res${res} sample(npc vs doll)=${diffPx(viaNpc.cv, viaDoll.cv)} game-vs-sample(npc)=${diffPx(game.cv, viaNpc.cv)} game-vs-sample(doll)=${diffPx(game.cv, viaDoll.cv)}`);
      }
    // 熔核領主：拿掉詞綴、特徵看差異在哪
    for (const res of [1, 2])
      for (const [id, look, aff] of [["lord", LORD, ["hardshell"]], ["lord-noaffix", LORD, []], ["lord-notrait", { ...LORD, traits: [] }, ["hardshell"]], ["lord-bare", { ...LORD, traits: [] }, []], ["wolf-bare", { ...WOLF, traits: [] }, []]] as const) {
        const sa = win().RGUnits.silhouetteOf({ spec: { ...look, elite: true, affixes: [...aff] }, west: true }, 250, 112, 1.8, res);
        const ga = duelSilhouette({ kind: "creature", creature: resolveCreature({ look: look as never, elite: true, affixes: [...aff] }), k: 1.8 }, true, 250, 112, 1.8, res, SAMPLE_HOOKS);
        log(`part creature ${id} res${res} cv=${diffPx(sa.cv, ga.cv)}`);
      }
  }
  for (const res of [1, 2]) {
    for (const [zh, look, w] of [
      ["hero sword", HERO_WEAPON, iconOf(HERO_WEAPON)!],
      ["saber", { kind: "saber", material: "steel" }, iconOf({ kind: "saber", material: "steel" })!],
      ["shotgun", { kind: "shotgun", form: "double", material: "iron" }, iconOf({ kind: "shotgun", form: "double", material: "iron" })!],
    ] as const)
      for (const px of [58, 58 * 1.12]) {
        const a = sampleWeapon(look as Any, px, res);
        const b = gameWeapon(w, px, res);
        log(`part weapon-icon ${zh} px${px.toFixed(2)} res${res} diff=${diffPx(a, b)} alpha-diff=${alphaDiff(a, b)}`);
      }
    const hs = rg.silhouetteOf({ doll: heroUnit(), view: "side", west: false, pose: HERO_POSE }, 72, 112, HERO_K, res);
    const hg = duelSilhouette({ kind: "doll", unit: heroUnit(), pose: HERO_POSE }, false, 72, 112, HERO_K, res, SAMPLE_HOOKS);
    log(`part sil hero res${res} cv=${diffPx(hs.cv, hg.cv)} seam=${hs.seam && hg.seam ? diffPx(hs.seam, hg.seam) : "missing"}`);
    const [sa, sb] = stampPair(heroUnit(), false, false, HERO_K, res, HERO_POSE as Any);
    log(`part stamp hero (sample QDoll.stamp vs game qStamp) res${res} diff=${diffPx(sa, sb)}`);
    for (const s of SCENES) {
      const se = s.sampleElite();
      const ge = s.gameElite();
      const k = ge.figure.kind === "creature" ? ge.figure.k : HUMANOID_ELITE_K;
      const ss = rg.silhouetteOf(se["spec"] ? { spec: se["spec"], west: true } : { npc: se["npc"], view: "side", west: true }, 250, 112, se["spec"] ? (se["k"] as number) : HUMANOID_ELITE_K, res);
      const gs = duelSilhouette(ge.figure, true, 250, 112, k, res, SAMPLE_HOOKS);
      log(`part sil ${s.id} res${res} cv=${diffPx(ss.cv, gs.cv)} seam=${!ss.seam && !gs.seam ? "none" : ss.seam && gs.seam ? diffPx(ss.seam, gs.seam) : "missing"}`);
      if (ge.figure.kind === "doll") {
        const [na, nb] = stampPair(ge.figure.unit, true, true, HUMANOID_ELITE_K, res, null);
        log(`part stamp ${s.id} (sample QNpc.stamp vs game qStamp) res${res} diff=${diffPx(na, nb)}`);
      }
    }
  }
}

// ---------- fp：劍版指紋 ----------
function fnv(c: HTMLCanvasElement): string {
  const d = c.getContext("2d")!.getImageData(0, 0, c.width, c.height).data;
  let h = 0x811c9dc5;
  for (let i = 0; i < d.length; i++) {
    h ^= d[i]!;
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, "0");
}
function runFp(): void {
  loadSample();
  const all: string[] = [];
  for (const res of [1, 2])
    for (const s of SCENES) {
      const f = fnv(duelCanvas(gameSpec(s), res)!);
      all.push(f);
      log(`fp dev ${s.id} res${res} ${f}`);
    }
  for (const res of [1, 2])
    for (const e of ["wolf", "scar", "lord", "forge"]) {
      const f = fnv(duelCanvas(duelSpecOf(duelPlan(dialogView(e, true))!), res)!);
      all.push(f);
      log(`fp game ${e} res${res} ${f}`);
    }
  log(`FP TOTAL ${all.join(" ")}`);
}

// ---------- RG-6：主手不是劍（9.9）----------
/** 主手 20 種（樣張 rg-duel-weapons.html 的 W20）。 */
const W20: ReadonlyArray<{ zh: string; look: { kind: string; form: string; material: string } }> = (
  [
    ["劍", "sword", "straight", "steel"], ["巨劍", "greatsword", "twohand", "steel"], ["匕首", "dagger", "short", "iron"], ["斧", "axe", "hand", "iron"],
    ["錘", "hammer", "mace", "iron"], ["矛", "spear", "spear", "iron"], ["拳套", "fist", "knuckle", "iron"], ["鐮刀", "scythe", "long", "iron"],
    ["鞭", "whip", "leather", "leather"], ["魔導劍", "sword", "arcane", "steel"], ["雙匕首", "dual_dagger", "short", "iron"], ["弓", "bow", "short", "wood"],
    ["弩", "crossbow", "light", "wood"], ["火槍", "longgun", "flintlock", "steel"], ["霰彈槍", "shotgun", "blunderbuss", "iron"], ["手槍", "pistol", "flintlock", "steel"],
    ["雙手槍", "dual_pistol", "flintlock", "steel"], ["法杖", "staff", "long", "wood"], ["權杖", "staff", "scepter", "gold"], ["圖騰杖", "staff", "totem", "wood"],
  ] as const
).map(([zh, kind, form, material]) => ({ zh, look: { kind, form, material } }));
const wz = (zh: string): (typeof W20)[number] => W20.find((w) => w.zh === zh)!;
const W5 = ["劍", "弓", "斧", "法杖", "雙手槍"].map(wz);
const CONTACT_W = ["劍", "弓", "弩", "鞭", "匕首", "手槍", "雙手槍", "斧", "霰彈槍"].map(wz);
const TWO = new Set(["greatsword", "spear", "scythe", "dual_dagger", "bow", "crossbow", "longgun", "shotgun", "dual_pistol"]);
/** 樣張 heroOf：弓弩用 hero_archer、杖用 hero_mage、其他 hero_fighter；雙手、成對、弓弩槍不拿盾。 */
function heroOfLook(look: Any): QUnit {
  const T = win().PaperDoll.TEMPLATES;
  const k = look["kind"];
  const base = (k === "bow" || k === "crossbow" ? T["hero_archer"] : k === "staff" ? T["hero_mage"] : T["hero_fighter"]) as unknown as QUnit;
  const gear: Any = { ...(base.gear as Any), main_hand: { slot: "main_hand", ...look } };
  if (TWO.has(k as string)) delete gear["off_hand"];
  return { look: base.look, gear } as unknown as QUnit;
}
type ESpec = { zh: string; region: string; sample: () => Any; game: () => { figure: DuelFigure; weapon: DuelWeapon | null } };
const sceneE = (id: string): ESpec => {
  const s = SCENES.find((x) => x.id === id)!;
  return { zh: s.zh, region: s.region, sample: s.sampleElite, game: s.gameElite };
};
const BEAR = { body: "bear", material: "fur", size: "large" };
const SNAKE = { body: "serpent", material: "scale", size: "large" };
const bigE = (zh: string, look: Any): ESpec => ({
  zh,
  region: "cloud_ridge",
  sample: () => ({ spec: { ...look, elite: true }, weapon: { kind: "beast_claw" }, k: 1.5 }),
  game: () => ({ figure: { kind: "creature", creature: resolveCreature({ look: look as never, elite: true }), k: 1.5 }, weapon: CLAW }),
});
const sampleW = (look: Any, e: ESpec): Any => ({ hero: { doll: heroOfLook(look), weapon: look }, elite: e.sample(), region: e.region, variant: "A" });
const gameW = (look: Any, e: ESpec, onFit?: (f: DuelFit) => void): DuelSpec => ({
  hero: { unit: heroOfLook(look), weapon: iconOf(look), main: look as unknown as DuelMain },
  elite: e.game(),
  region: e.region,
  hooks: SAMPLE_HOOKS,
  ...(onFit ? { onFit } : {}),
});
interface FitLike {
  dx: number;
  dy: number;
  s: number;
  ok: boolean;
}
const fitText = (t: FitLike | null): string => (!t ? "照劍／人形" : [t.dx ? `左 ${-t.dx}` : "", t.dy ? `上 ${-t.dy}` : "", t.s !== 1 ? `×${t.s.toFixed(2)}` : "", t.ok ? "" : "（不夠 3 px）"].filter(Boolean).join(" ") || "不動");
function gameFit(look: Any, e: ESpec, res: number): [HTMLCanvasElement, DuelFit | null] {
  let fit: DuelFit | null = null;
  const c = duelCanvas(gameW(look, e, (f) => void (fit = f)), res)!;
  return [c, fit];
}
function sampleFit(look: Any, e: ESpec, res: number): [HTMLCanvasElement, FitLike | null] {
  const rg = win().RGUnits as unknown as RG & { resetFit: () => void; fitOf: () => FitLike | null };
  rg.resetFit();
  const c = rg.duelCanvas(sampleW(look, e), res);
  return [c, rg.fitOf()];
}
function heroSilPair(look: Any, res: number): [{ cv: HTMLCanvasElement; seam: HTMLCanvasElement | null }, { cv: HTMLCanvasElement; seam: HTMLCanvasElement | null }] {
  const unit = heroOfLook(look);
  const sg = silGroup(look["kind"] as string);
  const pose = GROUP_POSE[sg] ?? HERO_POSE;
  const a = win().RGUnits.silhouetteOf({ doll: unit, view: "side", west: false, pose, prop: sg !== "held" }, 72, 112, HERO_K, res);
  const b = duelSilhouette({ kind: "doll", unit, pose, prop: sg === "held" ? null : propOf(look as unknown as DuelMain, iconOf(look)) }, false, 72, 112, HERO_K, res, SAMPLE_HOOKS);
  return [a, b];
}
/** weapons：和樣張逐像素（主角剪影 20 種、整張 W5 × 狼王／疤面、整組移的量表）。 */
function runWeapons(): void {
  loadSample();
  for (const res of [1, 2]) {
    let tot = 0;
    for (const w of W20) {
      const [a, b] = heroSilPair(w.look, res);
      // 剪影用時一律染色（tinted），只有 alpha 有意義；道具那塊保留圖示本色（遊戲端材質色暗一階，QI-1a），所以 RGBA 會差
      const n = alphaDiff(a.cv, b.cv);
      const sn = a.seam && b.seam ? alphaDiff(a.seam, b.seam) : a.seam || b.seam ? "missing" : "none";
      tot += n + (typeof sn === "number" ? sn : 0);
      log(`sil ${w.zh}(${w.look.kind}/${silGroup(w.look.kind)}) res${res} cv-alpha=${n} seam-alpha=${sn} cv-rgba=${diffPx(a.cv, b.cv)}`);
    }
    log(`SIL TOTAL res${res} ${tot}`);
  }
  // 歸因：道具剪影的差來自哪裡——① 身體（拿載體、弓手掛箭袋、組別架式，走 held 路不開道具）② 圖示本身（樣張 QIconsWeapons.paint vs 遊戲 render，只比 alpha）
  for (const res of [1, 2])
    for (const w of W20.filter((x) => silGroup(x.look.kind) !== "held")) {
      const sg = silGroup(w.look.kind);
      const pose = GROUP_POSE[sg]!;
      const unit = heroOfLook(w.look);
      const gear: Any = { ...(unit.gear as Any), main_hand: { slot: "main_hand", kind: "fist", form: "knuckle", material: "iron" } };
      if (w.look.kind === "bow" && !gear["back"]) gear["back"] = { slot: "back", kind: "quiver", material: "leather" };
      const carry = { look: unit.look, gear } as unknown as QUnit;
      const a = win().RGUnits.silhouetteOf({ doll: carry, view: "side", west: false, pose }, 72, 112, HERO_K, res);
      const b = duelSilhouette({ kind: "doll", unit: carry, pose }, false, 72, 112, HERO_K, res, SAMPLE_HOOKS);
      const look = w.look.kind === "dual_pistol" ? { ...w.look, kind: "pistol" } : w.look;
      const d = Math.round(({ bow: 21, crossbow: 24, longgun: 27, shotgun: 25, pistol: 17, dual_pistol: 17, staff: 26 } as Record<string, number>)[w.look.kind]! * HERO_K * Math.max(3, res * 2));
      const ia = sampleWeapon(look, d, 1);
      const ib = gameWeapon(iconOf(look)!, d, 1);
      const hard = (c: HTMLCanvasElement): HTMLCanvasElement => {
        const g = c.getContext("2d")!;
        const q = g.getImageData(0, 0, c.width, c.height);
        for (let i = 3; i < q.data.length; i += 4) q.data[i] = q.data[i]! > 128 ? 255 : 0;
        g.putImageData(q, 0, 0);
        return c;
      };
      const R = Math.max(3, res * 2);
      const hands: string[] = [];
      for (const side of ["sample", "game"]) {
        const ms: string[] = [];
        const [, g] = cv(4, 4);
        g.scale(R, R);
        g.translate(80, 120);
        g.scale(HERO_K, HERO_K);
        const probe = (kind: string, _h: unknown, _t: unknown, _v: unknown, _o: unknown, mm: { e: number; f: number }): void => void ms.push(`${kind}@${mm.e.toFixed(1)},${mm.f.toFixed(1)}`);
        if (side === "sample") {
          const QD = win().QDoll as unknown as { setPose: (p: unknown) => void; draw: (g: C2, u: unknown, v: string) => void };
          QD.setPose({ ...pose, probe });
          try {
            QD.draw(g, carry, "side");
          } finally {
            QD.setPose(null);
          }
        } else drawQ(g, carry, "side", SAMPLE_HOOKS, { ...pose, probe: probe as never }, false);
        hands.push(`${side}[${ms.join(" ")}]`);
      }
      log(`part prop ${w.zh} res${res} body-cv=${diffPx(a.cv, b.cv)} icon${d}-alpha>128-diff=${alphaDiff(hard(ia), hard(ib))} ${hands.join(" ")}`);
    }
  for (const res of [1, 2])
    for (const w of W5)
      for (const id of ["wolf", "scar"]) {
        const s = SCENES.find((x) => x.id === id)!;
        const a = win().RGUnits.duelCanvas(sampleW(w.look, sceneE(id)), res);
        const b = duelCanvas(gameW(w.look, sceneE(id)), res)!;
        const m = diffMask(a, b);
        log(`duel ${w.zh} × ${id} dpr${res} diff=${count(m)} bbox=${bbox(m, a.width)} unexplained=${unexplained(s, res, m)}`);
      }
  const ES: Array<[string, ESpec]> = [["wolf", sceneE("wolf")], ["lord", sceneE("lord")], ["bear", bigE("熊", BEAR)], ["snake", bigE("蛇", SNAKE)]];
  for (const res of [1, 2])
    for (const [id, e] of ES) {
      const row: string[] = [];
      let same = 0;
      for (const w of CONTACT_W) {
        const [, gf] = gameFit(w.look, e, res);
        const [, sf] = sampleFit(w.look, e, res);
        const g = fitText(gf);
        const sm = fitText(sf);
        if (g === sm) same++;
        row.push(g === sm ? `${w.zh} ${g}` : `${w.zh} game=${g} sample=${sm}`);
      }
      log(`fit ${id} res${res} same=${same}/${CONTACT_W.length}: ${row.join(" | ")}`);
    }
}
// ---- 拼圖（輸出 PNG 的 dataURL 到 #out，腳本存檔；真 1 倍） ----
interface Cell {
  c: HTMLCanvasElement;
  cap: string;
  z?: number;
}
function sheet(title: string, rows: Cell[][], gap = 12): HTMLCanvasElement {
  const pad = 14;
  const capH = 16;
  const W = Math.max(...rows.map((r) => r.reduce((s, x) => s + x.c.width * (x.z ?? 1) + gap, pad * 2 - gap)), 400);
  const H = pad * 2 + 22 + rows.reduce((s, r) => s + Math.max(...r.map((x) => x.c.height * (x.z ?? 1))) + capH + gap, 0);
  const [c, g] = cv(W, H);
  g.fillStyle = "#14161f";
  g.fillRect(0, 0, W, H);
  g.fillStyle = "#eadfcc";
  g.font = "14px 'Noto Sans TC','Microsoft JhengHei',sans-serif";
  g.fillText(title, pad, pad + 14);
  let y = pad + 22;
  for (const r of rows) {
    let x = pad;
    const rh = Math.max(...r.map((q) => q.c.height * (q.z ?? 1)));
    for (const q of r) {
      const z = q.z ?? 1;
      g.imageSmoothingEnabled = false;
      g.drawImage(q.c, x, y, q.c.width * z, q.c.height * z);
      g.fillStyle = "#c8c0b0";
      g.font = "12px 'Noto Sans TC','Microsoft JhengHei',sans-serif";
      g.fillText(q.cap, x, y + rh + 13);
      x += q.c.width * z + gap;
    }
    y += rh + capH + gap;
  }
  return c;
}
const crop = (src: HTMLCanvasElement, x: number, y: number, w: number, h: number): HTMLCanvasElement => {
  const [c, g] = cv(w, h);
  g.drawImage(src, -x, -y);
  return c;
};
const shrink = (src: HTMLCanvasElement): HTMLCanvasElement => {
  const [c, g] = cv(259, 97);
  g.imageSmoothingEnabled = true;
  g.imageSmoothingQuality = "high";
  g.drawImage(src, 0, 0, 259, 97);
  return c;
};
function runSheet(part: string): HTMLCanvasElement {
  loadSample();
  const wolf = sceneE("wolf");
  const scar = sceneE("scar");
  if (part === "silcmp") {
    // 主角剪影（cv＋縫）樣張 vs 遊戲：道具三組 9 種，×2
    const rows: Cell[][] = [];
    for (const w of W20.filter((x) => silGroup(x.look.kind) !== "held")) {
      const [a, b] = heroSilPair(w.look, 1);
      const flat = (s: { cv: HTMLCanvasElement; seam: HTMLCanvasElement | null }): HTMLCanvasElement => {
        const [c, g] = cv(s.cv.width, s.cv.height);
        g.fillStyle = "#4f6f6c";
        g.fillRect(0, 0, c.width, c.height);
        g.drawImage(s.cv, 0, 0);
        if (s.seam) {
          const [t, tg] = cv(s.seam.width, s.seam.height);
          tg.drawImage(s.seam, 0, 0);
          tg.globalCompositeOperation = "source-in";
          tg.fillStyle = "#a9ccff";
          tg.fillRect(0, 0, t.width, t.height);
          g.drawImage(t, 0, 0);
        }
        return crop(c, 180, 120, 300, 300);
      };
      rows.push([{ c: flat(a), cap: `樣張 ${w.zh}` }, { c: flat(b), cap: `遊戲 ${w.zh}` }]);
    }
    return sheet("主角剪影（內部 R 倍）樣張 vs 遊戲", rows);
  }
  if (part === "all") {
    const rows: Cell[][] = [];
    for (let i = 0; i < W20.length; i += 2)
      rows.push(W20.slice(i, i + 2).flatMap((w) => [{ c: duelCanvas(gameW(w.look, wolf), 1)!, cap: `${w.zh} × 北坡狼王` }, { c: duelCanvas(gameW(w.look, scar), 1)!, cap: `${w.zh} × 疤面` }]));
    return sheet("遊戲端 render/duelArt.ts：主手 20 種 × 北坡狼王／疤面，DPR 1 真 1 倍", rows);
  }
  if (part === "cmp") {
    const rows: Cell[][] = W5.map((w) => [
      { c: win().RGUnits.duelCanvas(sampleW(w.look, wolf), 1), cap: `樣張 ${w.zh} × 北坡狼王` },
      { c: duelCanvas(gameW(w.look, wolf), 1)!, cap: `遊戲 ${w.zh} × 北坡狼王` },
      { c: win().RGUnits.duelCanvas(sampleW(w.look, scar), 1), cap: `樣張 ${w.zh} × 疤面` },
      { c: duelCanvas(gameW(w.look, scar), 1)!, cap: `遊戲 ${w.zh} × 疤面` },
    ]);
    return sheet("樣張（duel-weapons-3-duel-v3）vs 遊戲端：五種主手 × 兩場，DPR 1 真 1 倍", rows);
  }
  if (part === "x4") {
    const rows: Cell[][] = W5.map((w) => [
      { c: duelCanvas(gameW(w.look, wolf), 1)!, cap: `${w.zh} × 北坡狼王 ×4`, z: 4 },
      { c: duelCanvas(gameW(w.look, scar), 1)!, cap: `${w.zh} × 疤面 ×4`, z: 4 },
    ]);
    return sheet("遊戲端：五種主手 × 兩場，DPR 1 最近鄰 ×4（對照 duel-weapons-4-duel-x4-v3）", rows, 16);
  }
  if (part === "small") {
    const S = W5.map((w) => ({ zh: w.zh, a: shrink(duelCanvas(gameW(w.look, wolf), 1)!), b: shrink(duelCanvas(gameW(w.look, scar), 1)!) }));
    const rows: Cell[][] = [S.flatMap((d) => [{ c: d.a, cap: `${d.zh} × 狼王` }, { c: d.b, cap: `${d.zh} × 疤面` }]).slice(0, 4), S.flatMap((d) => [{ c: d.a, cap: `${d.zh} × 狼王` }, { c: d.b, cap: `${d.zh} × 疤面` }]).slice(4, 8), S.flatMap((d) => [{ c: d.a, cap: `${d.zh} × 狼王` }, { c: d.b, cap: `${d.zh} × 疤面` }]).slice(8)];
    for (const d of S) rows.push([{ c: d.a, cap: `${d.zh} × 狼王 ×3`, z: 3 }, { c: d.b, cap: `${d.zh} × 疤面 ×3`, z: 3 }]);
    return sheet("遊戲端 800×600：插圖 DPR 1 等比縮成 259×97，真 1 倍；下方最近鄰 ×3（對照 duel-weapons-5-small-259-v3）", rows);
  }
  if (part === "sil") {
    const rows: Cell[][] = [];
    for (let i = 0; i < W20.length; i += 5)
      rows.push(W20.slice(i, i + 5).map((w) => ({ c: crop(duelCanvas(gameW(w.look, scar), 1)!, 0, 0, 150, 120), cap: `${w.zh}（${silGroup(w.look.kind)}）` })));
    for (let i = 0; i < W20.length; i += 10)
      rows.push(W20.slice(i, i + 10).map((w) => ({ c: crop(duelCanvas(gameW(w.look, scar), 1)!, 22, 8, 100, 106), cap: `${w.zh} ×2`, z: 2 })));
    return sheet("遊戲端主角剪影 20 種：插圖左半 150×120 真 1 倍；下方人物 100×106 最近鄰 ×2（對照 duel-weapons-1-sil）", rows);
  }
  // contact：會單挑的四場 × 九種，中間 130×84，真 1 倍與 ×2，下面寫整組移動量（res 1）
  const ES: Array<[string, ESpec]> = [["北坡狼王 1.2", wolf], ["疤面（人形）", scar], ["鍛疤暫代（荒原隊長，人形）", sceneE("forge")], ["熔核領主 1.8", sceneE("lord")]];
  const rows: Cell[][] = [];
  for (const [zh, e] of ES) {
    const D = CONTACT_W.map((w) => {
      const [c, f] = gameFit(w.look, e, 1);
      return { c: crop(c, 110, 14, 130, 84), cap: `${w.zh}：${f ? fitText(f) : w.zh === "劍" ? "照劍" : "人形／不走"}` };
    });
    rows.push(D.map((d, i) => (i === 0 ? { ...d, cap: `${zh}｜${d.cap}` } : d)));
    rows.push(D.map((d) => ({ c: d.c, cap: "", z: 2 })));
  }
  return sheet("遊戲端：會單挑的四場 × 九種主手，中間 130×84 真 1 倍與 ×2；字是整組移動（插圖 px，res 1；對照 duel-weapons-6-contact-v3）", rows, 8);
}

// ---------- 看圖 ----------
function show(): void {
  loadSample();
  const sec = (title: string): HTMLDivElement => {
    const h = document.createElement("h2");
    h.textContent = title;
    document.body.appendChild(h);
    const row = document.createElement("div");
    row.className = "row";
    document.body.appendChild(row);
    return row;
  };
  const put = (row: HTMLElement, c: HTMLCanvasElement, cap: string, cssW: number): void => {
    const d = document.createElement("div");
    d.className = "cell";
    c.style.width = `${cssW}px`;
    d.appendChild(c);
    const t = document.createElement("div");
    t.textContent = cap;
    d.appendChild(t);
    row.appendChild(d);
  };
  const res = Number(P.get("dpr") ?? 2);
  const r1 = sec(`樣張 duelCanvas（DPR ${res}）`);
  for (const s of SCENES) put(r1, win().RGUnits.duelCanvas(sampleSpec(s), res), s.zh, 320);
  const r2 = sec(`遊戲端 render/duelArt.ts（DPR ${res}）`);
  for (const s of SCENES) put(r2, duelCanvas(gameSpec(s), res)!, s.zh, 320);
  const r3 = sec("獸爪 48 格：樣張 vs 遊戲端（×4）");
  for (const px of [48, 58]) {
    put(r3, sampleWeapon({ kind: "beast_claw" }, px, 4), `樣張 ${px}`, px * 4);
    put(r3, beastClawCanvas(px, 4)!, `遊戲 ${px}`, px * 4);
  }
}

// ---------- dialog：正式的遇敵卡 ----------
const HERO_LOOK = { template_id: "hero", doll_look: null, weapon_id: "one_handed_sword", weapon_class: "melee", race_look: null, equipment: [] };
const dl = (extra: Any): Any => ({ skin: "#a8724c", hair: "short", hair_color: "#1c1410", pants: null, trim: null, eyes: null, skull: false, gear: {}, main_material: null, main_color: null, rarity: null, main_kind: null, main_tassel: null, bun_band: null, beard: false, build: null, main_glow: null, scale: null, creature: null, affixes: [], traits: [], ...extra });
const g = (kind: string, material: string, color: string | null = null): Any => ({ kind, material, color, form: null, trim: null, apron: null });
const ENEMY_LOOK: Record<string, { zh: string; region: string; look: Any }> = {
  wolf: { zh: "北坡狼王", region: "cloud_ridge", look: { template_id: "wolf_king", doll_look: dl({ creature: { ...WOLF }, affixes: ["berserk"] }), weapon_id: "fang", weapon_class: "melee", race_look: null, equipment: [] } },
  lord: { zh: "熔核領主", region: "ashen_waste", look: { template_id: "molten_lord", doll_look: dl({ creature: { ...LORD }, affixes: ["hardshell"] }), weapon_id: "stone_fist", weapon_class: "melee", race_look: null, equipment: [] } },
  scar: { zh: "疤面", region: "cloud_ridge", look: { template_id: "bandit_scarface", doll_look: dl({ hair: "long", hair_color: "#1c1c22", gear: { head: g("douli", "cloth", "#3c4248"), body: g("coat", "cloth", "#3c4248"), cloak: g("cape", "cloth", "#c0392b"), feet: g("boots", "leather") }, main_kind: "saber", main_material: "steel" }), weapon_id: "saber", weapon_class: "melee", race_look: null, equipment: [] } },
  forge: { zh: "熔爐督工「鍛疤」", region: "ashen_waste", look: { template_id: "bandit_captain", doll_look: dl({ gear: { head: g("bandana", "cloth", "#ff6a1a"), body: g("mail", "iron"), cloak: g("cape", "cloth", "#5a4a3e"), feet: g("boots", "leather") }, main_kind: "shotgun", main_material: "iron" }), weapon_id: "shotgun", weapon_class: "ranged", race_look: null, equipment: [] } },
};
/** dialog 的主角：預設單手劍（fp 用這個）；&hw=<kind>（W20 第一筆同 kind 的形制、材質）時主手裝備換成那件。 */
function heroLookOf(hw: string | null): Any {
  const w = hw === null ? undefined : W20.find((x) => x.look.kind === hw);
  return w === undefined ? HERO_LOOK : { ...HERO_LOOK, equipment: [{ slot: "main_hand", appearance: { ...w.look } }] };
}
function dialogView(e: string, duel: boolean): WorldView {
  const E = ENEMY_LOOK[e] ?? ENEMY_LOOK["wolf"]!;
  return {
    character: { hero_look: heroLookOf(duel ? P.get("hw") : null) },
    map: { region: E.region },
    encounter: {
      location: "dev",
      location_name_zh: "開發頁",
      enemy_level: 4,
      map_name_zh: "開發頁",
      weather_zh: "晴",
      day_phase_zh: "傍晚",
      enemies: [
        { name_zh: E.zh, elite: true, affix_zh: null, third: false, rank: "elite", look: E.look },
        { name_zh: "嘍囉", elite: false, affix_zh: null, third: false, rank: "normal", look: null },
      ],
      retreat_to_zh: "霧渡鎮",
      fatigued: false,
      hero_hp: 60,
      in_battle: false,
      reinforcements: 0,
      hero_statuses: [],
      opening_zh: [],
      allies_zh: "主角（開場 HP 60）",
      battlefield_fallback_zh: null,
      duel: duel ? "offered" : null,
      duel_zh: duel ? `接受：只有你和${E.zh}上場，隊友、傭兵不上場。拒絕：照原本全隊開打。兩邊的獎勵一樣（經驗、掉落、懸賞照整個陣容算）。` : null,
    },
  } as unknown as WorldView;
}
function DialogScene({ e }: { e: string }) {
  const E = ENEMY_LOOK[e] ?? ENEMY_LOOK["wolf"]!;
  useRegionTheme(E.region);
  const view = dialogView(e, P.get("duel") !== "none");
  const w = Number(P.get("w") ?? 1600);
  return (
    <div style={{ position: "relative", width: w, height: w <= 800 ? 600 : 900, background: "#14161f" }}>
      <div className="world-hud-center" style={{ top: 8, maxHeight: w <= 800 ? 580 : 880 }}>
        <EncounterPanel view={view} busy={false} onAct={() => undefined} onBattle={() => undefined} />
      </div>
    </div>
  );
}

try {
  if (MODE === "diff") runDiff();
  else if (MODE === "fp") runFp();
  else if (MODE === "weapons") runWeapons();
  else if (MODE === "sheet") log(runSheet(P.get("part") ?? "cmp").toDataURL("image/png"));
  else if (MODE === "dialog") createRoot(document.getElementById("root")!).render(<DialogScene e={P.get("e") ?? "wolf"} />);
  else show();
} catch (err) {
  log(`ERROR ${(err as Error).stack ?? String(err)}`);
}
if (MODE !== "dialog") {
  const out = document.createElement("pre");
  out.id = "out";
  out.textContent = lines.join("\n");
  document.body.appendChild(out);
}
document.body.dataset["done"] = "1";
