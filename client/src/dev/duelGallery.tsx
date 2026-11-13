// 開發用：RG-4 精英單挑插圖 A 暮色對峙（`dev/duel-gallery.html`；不屬於正式 build）。
// 模式（?mode=）：
//   diff    和樣張逐像素比對（目標 0）：四場（北坡狼王、疤面、熔核領主、荒原精英；spec 照 docs/art/sample/rg-duel-dialog.html 的 ELITES，
//           主角 hero_fighter＋steel sword）× DPR 1、2 的整張 duelCanvas；獸爪單獨（48 格，px 48、58 × res 1、2）；
//           另外逐項比（歸因用）：主角／精英剪影（cv、seam）、交叉的武器圖示、紙娃娃小人本身（樣張 QDoll.stamp／QNpc.stamp vs 遊戲端 qStamp）。
//           輸出 `<pre id="out">`。
//   dialog  正式的遇敵卡（EncounterPanel）＋單挑段＋插圖，假資料（&e=wolf｜lord｜scar｜forge，&w=1600｜800 只決定卡片外的舞台寬）。
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
import { beastClawCanvas, duelCanvas, duelSilhouette, HERO_K, HERO_POSE, HUMANOID_ELITE_K, type DuelFigure, type DuelSpec, type DuelWeapon } from "../render/duelArt";
import { resolveGear } from "../render/gearResolve";
import { resolveCreature } from "../render/inkCreature";
import type { QUnit } from "../render/qCore";
import { render } from "../render/qIcon/core";
import { qResolve, qWeaponDef } from "../render/qIcon/weapons";
import { SAMPLE_HOOKS } from "../render/qSample";
import { qStamp } from "../render/qStamp";
import { useRegionTheme } from "../ui/regionTheme";
import { EncounterPanel } from "../world/WorldPanel";
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
function DialogScene({ e }: { e: string }) {
  const E = ENEMY_LOOK[e] ?? ENEMY_LOOK["wolf"]!;
  useRegionTheme(E.region);
  const view = {
    character: { hero_look: HERO_LOOK },
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
      duel: "offered",
      duel_zh: `接受：只有你和${E.zh}上場，隊友、傭兵不上場。拒絕：照原本全隊開打。兩邊的獎勵一樣（經驗、掉落、懸賞照整個陣容算）。`,
    },
  } as unknown as WorldView;
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
