// 開發用：QK-4 異形、頭目的 Q 版畫廊（開 `client/dev/creature-gallery.html`，pnpm dev 後 /dev/creature-gallery.html）。
// 版面、倍率、背景照美術 PM 樣張 docs/art/sample/q-creatures.html、q-bosses.html、q-creature-anim.html（左樣張、右遊戲並排用）；
// 畫的都是遊戲的 inkCreature／qCreatureAnim／qBoss（不 import 樣張程式）。不屬於正式 build。
// 網址：（預設）身形 × 材質、元素、大小、詞綴、名單；`?anim=<身形>` 動畫格表（每格 520×220）；`?boss=atlas` 頭目動作格表（420×300）；
// `?boss=page` 頭目造型；`?view=strip` 關鍵格總表；`&reduce=1` 減少動態。
// CB-3：`?melee2=<身形>`（`&west=1` 朝西、`&look=1` 精英＋大型外觀）第一種與第二種近戰逐格並排（同樣張 q-melee2-<身形>.png 的排法）；
// `?cb3=first` 五款普攻命中格；`?cb3=spots` 山豹各片段；`?cb3=reduce` 減少動態五款。
import { TAU, type Ctx } from "../render/artDraw";
import type { CreaturePose } from "../render/creaturePose";
import { BODIES, MATERIALS, SIZES, drawCreature, resolveCreature, type CreatureLookDraw, type ResolvedCreature } from "../render/inkCreature";
import { ATTACK_TYPE_ZH, BODY_ANIM, LOOP_N, attackClipFor, creatureAttackHitU, creatureClipInfo, creatureClips, creatureOwnFrames } from "../render/qCreatureAnim";
import { BOSS_CLIP_ZH, BOSS_CLIPS, BOSS_IDLE_N, BOSS_MS, bossAct, drawAshenHeart, drawShardLord, type BossId } from "../render/qBoss";
import { CREATURE_ELEM } from "../render/qCreatureElem";
import { QC_OUT } from "../render/qCreatureLayer";

const Q = new URLSearchParams(location.search);
const REDUCE = Q.get("reduce") === "1";
const FONT = "'Noto Sans TC','Microsoft JhengHei',sans-serif";

/** 樣張的外觀規格（body × material × … ＋ elite、affixes、glow）。 */
interface Spec extends CreatureLookDraw {
  elite?: boolean;
  affixes?: string[];
  glow?: string;
}

function resolveSpec(s: Spec): ResolvedCreature {
  const rarity = s.glow === "#ffbf3a" ? "legendary" : s.glow === "#b06cff" ? "epic" : null;
  const r = resolveCreature({ look: s, elite: s.elite, affixes: s.affixes, rarity });
  // 樣張頁：精英一律 ×1.15（遊戲裡頭目不放大，畫廊照樣張比對）
  if (s.elite === true && rarity !== null) r.size *= 1.15;
  return r;
}

/** 地面環（照樣張 qCreature.js 的 ring；戰場上由 unitSprite 畫）。 */
function ring(ctx: Ctx, rx: number, elite: boolean): void {
  ctx.save();
  ctx.globalAlpha = 0.3;
  ctx.fillStyle = "#d24a3a";
  ctx.beginPath();
  ctx.ellipse(0, 0, rx, rx * 0.3, 0, 0, TAU);
  ctx.fill();
  ctx.globalAlpha = 0.95;
  ctx.strokeStyle = "#d24a3a";
  ctx.lineWidth = 1.1;
  ctx.stroke();
  if (elite) {
    ctx.globalAlpha = 1;
    ctx.strokeStyle = QC_OUT;
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    ctx.ellipse(0, 0, rx + 2.2, (rx + 2.2) * 0.3, 0, 0, TAU);
    ctx.stroke();
    ctx.strokeStyle = "#ffbf3a";
    ctx.lineWidth = 1.2;
    ctx.stroke();
    const y0 = (rx + 2.2) * 0.3 - 0.4;
    ctx.beginPath();
    ([[0, y0], [2.6, y0 + 2.6], [0, y0 + 5.2], [-2.6, y0 + 2.6]] as const).forEach(([x, y], i) => (i > 0 ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.closePath();
    ctx.lineJoin = "round";
    ctx.strokeStyle = QC_OUT;
    ctx.lineWidth = 1.6;
    ctx.stroke();
    ctx.fillStyle = "#ffbf3a";
    ctx.fill();
    ctx.fillStyle = "#fff2c0";
    ctx.fillRect(-0.5, y0 + 1.2, 1, 1);
  }
  ctx.restore();
}

/** 樣張 stamp 的對應：地面環＋異形（腳底 (cx, cy)、倍率 k、west 鏡像、pose 動畫格）。 */
function stamp(x: Ctx, s: Spec, cx: number, cy: number, k: number, west = false, pose: CreaturePose | null = null): void {
  const r = resolveSpec(s);
  x.save();
  x.translate(cx, cy);
  x.save();
  const rk = k * Math.max(1, r.size * 0.9);
  x.scale(rk, rk);
  ring(x, 13, s.elite === true || s.glow !== undefined);
  x.restore();
  x.scale(west ? -k : k, k);
  drawCreature(x, r, pose);
  x.restore();
}

function cv(w: number, h: number, parent: HTMLElement = document.body): Ctx {
  const c = document.createElement("canvas");
  c.width = w * 2;
  c.height = h * 2;
  c.style.width = `${w}px`;
  c.style.height = `${h}px`;
  parent.appendChild(c);
  const x = c.getContext("2d")!;
  x.scale(2, 2);
  return x;
}
function cell(x: Ctx, X: number, Y: number, w: number, h: number, alt: boolean | number): void {
  x.fillStyle = alt ? "#232638" : "#1e2030";
  x.fillRect(X + 1, Y + 1, w - 2, h - 2);
}
function label(x: Ctx, t: string, X: number, Y: number, c = "#d8ccb8", sz = 11, al: CanvasTextAlign = "center"): void {
  x.font = `${sz}px ${FONT}`;
  x.fillStyle = c;
  x.textAlign = al;
  x.fillText(t, X, Y);
}
function h2(t: string): void {
  const h = document.createElement("h2");
  h.textContent = t;
  document.body.appendChild(h);
}
const ZH_MAT: Readonly<Record<string, string>> = { fur: "毛皮", magma: "熔岩", crystal: "源晶", stone: "青石", wood: "木", mist: "霧" };
const ALL: ReadonlyArray<readonly [string, string | undefined]> = Object.keys(BODIES).flatMap((b): Array<readonly [string, string | undefined]> =>
  b === "flyer" ? [[b, "bird"], [b, "bat"]] : b === "crawler" ? [[b, "beetle"], [b, "spider"]] : [[b, undefined]],
);
const bodyZh = (b: string, v: string | undefined): string => (v === "bat" ? "蝠" : v === "bird" ? "鳥" : v === "spider" ? "蜘蛛" : v === "beetle" ? "甲蟲" : (BODIES[b]?.zh ?? b));

// ============================== 造型頁（q-creatures.html 第 2～6 段同版面） ==============================
function page(): void {
  document.body.style.width = "1280px";
  // 2. 身形 × 材質（第 1 欄是樣張的 C 版欄：遊戲不畫，空著對位）
  h2("2. 身形 × 材質（遊戲 Q 版；第 1 欄留空，對位樣張的 C 版欄）");
  {
    const cols = ["（C 版欄）", ...MATERIALS.map((m) => ZH_MAT[m]!)];
    const CW = 1280 / cols.length;
    const RH = 104;
    const HD = 22;
    const k = 1.5;
    const x = cv(1280, HD + ALL.length * RH);
    cols.forEach((t, i) => label(x, t, i * CW + CW / 2, 15, i === 0 ? "#6a6e88" : "#f2e6c8", 12));
    ALL.forEach(([b, v], r) => {
      const Y = HD + r * RH;
      const fy = Y + RH - 18;
      cols.forEach((_, i) => {
        const X = i * CW;
        cell(x, X, Y, CW, RH, (r + i) % 2);
        if (i > 0) stamp(x, { body: b, variant: v ?? null, material: MATERIALS[i - 1]! }, X + CW / 2 + (b === "lizard" ? 10 : 0), fy, k);
      });
      label(x, bodyZh(b, v), 6, Y + 14, "#f2e6c8", 12, "left");
    });
  }
  // 3. 元素
  h2("3. 元素");
  {
    const E = Object.keys(CREATURE_ELEM);
    const CW = 1280 / (E.length + 1);
    const RH = 100;
    const x = cv(1280, RH * 2 + 4);
    ["無", ...E].forEach((el, i) => {
      for (let r = 0; r < 2; r++) {
        const X = i * CW;
        const Y = r * (RH + 4);
        const spec: Spec = r === 0 ? { body: "hound", material: "fur", element: el } : i % 2 ? { body: "ooze", material: "magma", element: el } : { body: "wisp", material: "crystal", element: el };
        cell(x, X, Y, CW, RH, (i + r) % 2);
        stamp(x, spec, X + CW / 2, Y + RH - 18, 1.5);
        label(x, el, X + CW / 2, Y + 13);
      }
    });
  }
  // 4. 大小、精英、頭目外光
  h2("4. 大小、精英、頭目外光（第 1 格樣張是 Q 主角，這裡留空）");
  {
    const W = 1280;
    const H = 150;
    const x = cv(W, H);
    const k = 1.5;
    const fy = 122;
    cell(x, 0, 0, W, H, false);
    const L: Array<[string, { size?: string; elite?: boolean; glow?: string; material?: string }]> = [
      ["tiny", {}],
      ["small", {}],
      ["normal", {}],
      ["large", {}],
      ["huge", {}],
      ["normal 精英", { elite: true }],
      ["large 精英", { size: "large", elite: true }],
      ["頭目（傳說外光）", { size: "large", glow: "#ffbf3a" }],
      ["頭目（史詩外光）", { size: "large", glow: "#b06cff", material: "crystal" }],
    ];
    let cx = 100;
    for (const [t, o] of L) {
      const sz = o.size ?? (["tiny", "small", "normal", "large", "huge"].includes(t) ? t : "normal");
      const s = (SIZES[sz] ?? 1) * (o.elite === true ? 1.15 : 1);
      cx += 40 * s + 22;
      stamp(x, { body: "lizard", material: o.material ?? "magma", size: sz, ...(o.elite === true ? { elite: true } : {}), ...(o.glow !== undefined ? { glow: o.glow } : {}) }, cx, fy, k);
      label(x, t, cx, H - 8);
      cx += 40 * s + 12;
    }
  }
  // 5. 詞綴
  h2("5. 精英詞綴（同一隻霧狼，精英）");
  {
    const A = ["(無)", "regen", "mist_hidden", "linked", "berserk", "blazing", "hardshell", "armored", "swift", "mirror", "elemental", "unknown"];
    const CW = 1280 / A.length;
    const H = 165;
    const x = cv(1280, H);
    A.forEach((a, i) => {
      const X = i * CW;
      cell(x, X, 0, CW, H, i % 2);
      stamp(x, { body: "hound", material: "fur", tint: "#c8ccd0", element: a === "elemental" ? "fire" : null, elite: true, affixes: a === "(無)" ? [] : [a] }, X + CW / 2 + 6, H - 24, 1.2);
      label(x, a, X + CW / 2, 14, "#f2e6c8", 12);
    });
  }
  // 6. 名單（樣張左半是 C 版，這裡只畫右半 Q 版）
  h2("6. 名單上的單位（只畫樣張右半的 Q 版位置）");
  {
    const U: Array<[string, Spec]> = [
      ["餘燼蜥", { body: "lizard", material: "magma", size: "small" }],
      ["寒燼蜥", { body: "lizard", material: "magma", element: "ice", size: "small" }],
      ["熔岩甲蟲", { body: "crawler", variant: "beetle", material: "magma" }],
      ["火塵蝠", { body: "flyer", variant: "bat", material: "magma" }],
      ["熔核蛞蝓", { body: "ooze", material: "magma", traits: ["core"] }],
      ["噴岩龜", { body: "shell", material: "magma", traits: ["volcano"] }],
      ["焦岩巨像", { body: "golem", material: "stone", tint: "#5a4e48", element: "fire", traits: ["core"] }],
      ["熔爐母獸", { body: "lizard", material: "magma", size: "large", traits: ["brood", "core"] }],
      ["硫煙獸", { body: "boar", material: "fur", tint: "#8a7a3a", element: "poison", traits: ["smoke"] }],
      ["熔核領主（精英）", { body: "crawler", variant: "beetle", material: "magma", size: "large", traits: ["lava_pool"], elite: true, affixes: ["hardshell"] }],
      ["霧狼", { body: "hound", material: "fur", tint: "#c8ccd0", traits: ["mist"] }],
      ["山豹", { body: "feline", material: "fur", traits: ["spots"] }],
      ["石背熊", { body: "bear", material: "fur", element: "earth", traits: ["stone_back"] }],
      ["雷羽鷹", { body: "flyer", variant: "bird", material: "fur", tint: "#c8d8f0", element: "lightning", traits: ["sparks"] }],
      ["北坡狼王（精英）", { body: "hound", material: "fur", tint: "#c8ccd0", size: "large", traits: ["mist", "scar"], elite: true, affixes: ["berserk"] }],
      ["霧魅", { body: "wraith", material: "mist", element: "shadow" }],
      ["熔晶魅", { body: "wraith", material: "mist", element: "fire" }],
      ["碎晶傀儡", { body: "golem", material: "crystal", element: "lightning" }],
      ["源晶柱・霧", { body: "pylon", material: "crystal", element: "wind" }],
      ["源晶柱・雷", { body: "pylon", material: "crystal", element: "lightning" }],
      ["源晶柱・火", { body: "pylon", material: "crystal", element: "fire" }],
      ["餘燼幼蜥（召喚 tiny）", { body: "lizard", material: "magma", size: "tiny" }],
      ["木傀儡", { body: "golem", material: "wood", size: "small" }],
      ["陣眼石靈", { body: "pylon", material: "stone" }],
    ];
    const PER = 6;
    const CW = 1280 / PER;
    const RH = 150;
    const x = cv(1280, Math.ceil(U.length / PER) * RH);
    U.forEach(([t, s], i) => {
      const X = (i % PER) * CW;
      const Y = Math.floor(i / PER) * RH;
      cell(x, X, Y, CW, RH, (i + Math.floor(i / PER)) % 2);
      stamp(x, s, X + CW * 0.73, Y + RH - 22, 1.2);
      label(x, t, X + CW / 2, Y + 14, "#f2e6c8", 12);
    });
  }
  // 7. 朝西＝朝東鏡像（遊戲朝西用 stamp 的鏡像）
  h2("7. 朝東／朝西");
  {
    const x = cv(1280, 120);
    cell(x, 0, 0, 1280, 120, false);
    ALL.slice(0, 8).forEach(([b, v], i) => {
      stamp(x, { body: b, variant: v ?? null, material: "fur" }, 60 + i * 155, 96, 1.2, false);
      stamp(x, { body: b, variant: v ?? null, material: "fur" }, 120 + i * 155, 96, 1.2, true);
    });
  }
  document.body.dataset.h = String(document.documentElement.scrollHeight);
}

// ============================== 動畫（q-creature-anim.html 同一組外觀） ==============================
const LOOK: Readonly<Record<string, readonly [Spec, Spec]>> = {
  hound: [{ body: "hound", material: "magma" }, { body: "hound", material: "fur", tint: "#c8ccd0", size: "large", elite: true, affixes: ["berserk"], traits: ["mist", "scar"] }],
  boar: [{ body: "boar", material: "fur", tint: "#8a7a3a", element: "poison", traits: ["smoke"] }, { body: "boar", material: "stone", elite: true, affixes: ["armored"] }],
  bear: [{ body: "bear", material: "fur", element: "earth", traits: ["stone_back"] }, { body: "bear", material: "magma", elite: true, affixes: ["blazing"] }],
  feline: [{ body: "feline", material: "fur", traits: ["spots"] }, { body: "feline", material: "mist", elite: true, affixes: ["swift"] }],
  lizard: [{ body: "lizard", material: "magma" }, { body: "lizard", material: "magma", size: "large", elite: true, traits: ["brood", "core"], affixes: ["regen"] }],
  shell: [{ body: "shell", material: "magma", traits: ["volcano"] }, { body: "shell", material: "stone", elite: true, affixes: ["hardshell"] }],
  beetle: [{ body: "crawler", variant: "beetle", material: "magma" }, { body: "crawler", variant: "beetle", material: "magma", size: "large", elite: true, traits: ["lava_pool"], affixes: ["hardshell"] }],
  spider: [{ body: "crawler", variant: "spider", material: "fur" }, { body: "crawler", variant: "spider", material: "crystal", element: "shadow", elite: true, affixes: ["mirror"] }],
  serpent: [{ body: "serpent", material: "fur" }, { body: "serpent", material: "magma", element: "lightning", elite: true, affixes: ["elemental"] }],
  ooze: [{ body: "ooze", material: "magma", traits: ["core"] }, { body: "ooze", material: "fur", element: "poison", elite: true, affixes: ["regen"] }],
  golem: [{ body: "golem", material: "crystal", element: "lightning" }, { body: "golem", material: "stone", tint: "#5a4e48", element: "fire", traits: ["core"], elite: true, affixes: ["armored"] }],
  wisp: [{ body: "wisp", material: "crystal" }, { body: "wisp", material: "crystal", element: "fire", elite: true, glow: "#ffbf3a" }],
  wraith: [{ body: "wraith", material: "mist", element: "shadow" }, { body: "wraith", material: "mist", element: "fire", elite: true, affixes: ["linked"] }],
  pylon: [{ body: "pylon", material: "crystal", element: "wind" }, { body: "pylon", material: "crystal", element: "lightning", elite: true, affixes: ["regen"] }],
  bird: [{ body: "flyer", variant: "bird", material: "fur", tint: "#c8d8f0", element: "lightning", traits: ["sparks"] }, { body: "flyer", variant: "bird", material: "magma", elite: true, affixes: ["swift"] }],
  bat: [{ body: "flyer", variant: "bat", material: "magma" }, { body: "flyer", variant: "bat", material: "mist", element: "shadow", elite: true, affixes: ["mist_hidden"] }],
};
const CLIP_LOOK: Readonly<Record<string, Readonly<Record<string, readonly [Spec, Spec]>>>> = {
  lizard: { "atk:cast": [{ body: "lizard", material: "magma", element: "ice" }, { body: "lizard", material: "magma", element: "ice", size: "large", elite: true, traits: ["core"], affixes: ["regen"] }] },
};
const lookOf = (bk: string, clip: string, i: 0 | 1): Spec => (CLIP_LOOK[bk]?.[clip] ?? LOOK[bk]!)[i];
const VARIANT_ZH: Readonly<Record<string, string>> = { bat: "蝠", bird: "鳥", spider: "蜘蛛", beetle: "甲蟲" };
const ZH = (bk: string): string => VARIANT_ZH[bk] ?? BODIES[bk]?.zh ?? bk;
function ground(x: Ctx, X: number, Y: number, w: number, h: number, alt: boolean): void {
  x.fillStyle = alt ? "#232638" : "#1e2030";
  x.fillRect(X, Y, w, h);
  x.fillStyle = "#2a2d44";
  x.fillRect(X, Y + h - 22, w, 22);
}
/** 片段的每一格的 u（循環 8 格；單次 12 格／秒）。 */
function frameUs(bk: string, clip: string): number[] {
  const info = creatureClipInfo(bk, clip)!;
  return info.loop ? Array.from({ length: LOOP_N }, (_, f) => f / LOOP_N) : Array.from({ length: info.n }, (_, f) => f / (info.n - 1));
}
const poseOf = (clip: string, u: number): CreaturePose => ({ clip, u, fxAll: true, ...(REDUCE ? { reduce: true } : {}) });

function atlas(bk: string): void {
  document.body.style.margin = "0";
  const CW = 520;
  const CH = 220;
  const COLS = 4;
  const k = 2.3;
  const frames: Array<{ clip: string; u: number; f: number; n: number }> = [];
  for (const clip of creatureClips(bk)) frameUs(bk, clip).forEach((u, f, arr) => frames.push({ clip, u, f, n: arr.length }));
  const x = cv(CW * COLS, CH * Math.ceil(frames.length / COLS));
  frames.forEach(({ clip, u, f, n }, i) => {
    const X = (i % COLS) * CW;
    const Y = Math.floor(i / COLS) * CH;
    const info = creatureClipInfo(bk, clip)!;
    x.save();
    x.beginPath();
    x.rect(X, Y, CW, CH);
    x.clip();
    ground(x, X, Y, CW, CH, false);
    stamp(x, lookOf(bk, clip, 0), X + 120, Y + CH - 34, k, false, poseOf(clip, u));
    stamp(x, lookOf(bk, clip, 1), X + 350, Y + CH - 34, k, false, poseOf(clip, u));
    label(x, `${ZH(bk)}・${info.type !== undefined ? `${ATTACK_TYPE_ZH[info.type]}：` : ""}${info.zh}`, X + 10, Y + 18, "#f2e6c8", 13, "left");
    label(x, `${f + 1}/${n}`, X + CW - 10, Y + 18, "#8a8070", 11, "right");
    x.restore();
  });
  document.body.dataset.frames = JSON.stringify(frames.map((q) => [q.clip, q.f, q.n]));
}

const ORDER = ["hound", "boar", "bear", "feline", "lizard", "shell", "beetle", "spider", "serpent", "ooze", "golem", "wisp", "wraith", "pylon", "bird", "bat"];
function strip(): void {
  document.body.style.margin = "0";
  const KEYS: Readonly<Record<string, readonly number[]>> = { idle: [0, 0.5], move: [0, 0.25, 0.5], atk: [0.3, 0.5, 0.7], hit: [0.15], death: [0.6, 1] };
  const W = 1316;
  const LW = 150;
  const CW = 68;
  const RH = 118;
  const HD = 30;
  const k = 1.15;
  const x = cv(W, HD + ORDER.length * RH + 8);
  x.fillStyle = "#14161f";
  x.fillRect(0, 0, W, HD + ORDER.length * RH + 8);
  label(x, "遊戲（QK-4）：關鍵格總表（同樣張 q-creature-strip.png 的格）", 8, 19, "#f2e6c8", 13, "left");
  let Y = HD;
  ORDER.forEach((bk, r) => {
    const B = BODY_ANIM[bk]!;
    const atks = Object.entries(B.attacks);
    x.fillStyle = r % 2 ? "#1a1c2a" : "#1e2030";
    x.fillRect(0, Y, W, RH - 2);
    label(x, `${ZH(bk)}（${atks.length} 種攻擊）`, 8, Y + 18, "#e8bb48", 13, "left");
    let X = LW;
    const one = (clip: string, u: number, hue: string): void => {
      const info = creatureClipInfo(bk, clip)!;
      const uu = info.loop ? (Math.round(u * LOOP_N) % LOOP_N) / LOOP_N : Math.round(u * (info.n - 1)) / (info.n - 1);
      x.save();
      x.beginPath();
      x.rect(X, Y + 30, CW - 1, RH - 32);
      x.clip();
      x.fillStyle = hue;
      x.fillRect(X, Y + 30, CW - 1, RH - 32);
      stamp(x, lookOf(bk, clip, 0), X + CW * 0.36, Y + RH - 14, k, false, poseOf(clip, uu));
      x.restore();
      X += CW;
    };
    const group = (clip: string, us: readonly number[], t1: string, hue: string): void => {
      const X0 = X;
      us.forEach((u) => one(clip, u, hue));
      label(x, t1, X0 + 3, Y + 13, "#f2e6c8", 10.5, "left");
    };
    group("idle", KEYS["idle"]!, "待機", "#24283c");
    group("move", KEYS["move"]!, "移動", "#262a40");
    atks.forEach(([id, a], j) => group(`atk:${id}`, KEYS["atk"]!, ATTACK_TYPE_ZH[a.type], j % 2 ? "#2c2a3a" : "#322a34"));
    group("hit", KEYS["hit"]!, "受擊", "#3a2a2e");
    group("death", KEYS["death"]!, "倒下", "#26262c");
    Y += RH;
  });
}

// ============================== 頭目 ==============================
function bossAtlas(): void {
  document.body.style.margin = "0";
  const CW = 420;
  const CH = 300;
  const frames: Array<{ who: BossId; clip: string; u: number; f: number; n: number; phase?: number }> = [];
  // QK-4b（同樣張 ?boss=atlas）：每個階段先放待機 16 格（看各階段外觀），再放動作片段；&who=ah|sl 只拍一位
  const only = Q.get("who");
  const WHO = (only === "ah" || only === "sl" ? [only] : ["ah", "sl"]) as BossId[];
  for (const who of WHO) {
    for (const phase of who === "ah" ? [1, 2, 3] : [1, 2, 3, 4]) for (let f = 0; f < BOSS_IDLE_N; f++) frames.push({ who, clip: "idle", u: f / BOSS_IDLE_N, f, n: BOSS_IDLE_N, phase });
    for (const clip of who === "ah" ? ["spout", "firebolt", "ram", "hit", "hit2", "death"] : BOSS_CLIPS[who]) {
      const n = Math.max(2, Math.round((BOSS_MS[clip === "hit2" ? "hit" : clip] ?? 0) / (1000 / 12)));
      for (let f = 0; f < n; f++) frames.push({ who, clip, u: f / (n - 1), f, n });
    }
  }
  const COLS = 4;
  const x = cv(CW * COLS, CH * Math.ceil(frames.length / COLS));
  frames.forEach(({ who, clip, u, f, n, phase }, i) => {
    const X = (i % COLS) * CW;
    const Y = Math.floor(i / COLS) * CH;
    x.save();
    x.beginPath();
    x.rect(X, Y, CW, CH);
    x.clip();
    x.fillStyle = who === "ah" ? "#2e221c" : "#1e1c34";
    x.fillRect(X, Y, CW, CH);
    x.fillStyle = who === "ah" ? "#3e2e24" : "#2a2848";
    x.fillRect(X, Y + CH - 34, CW, 34);
    x.save();
    x.translate(X + CW * 0.4, Y + CH - 34);
    const sc = who === "ah" ? 2.2 : 2;
    x.scale(sc, sc);
    bossAct(x, who, clip === "hit2" ? "hit" : clip, u, { reduce: REDUCE, fxAll: true, ring: (c, rx) => ring(c, rx, true), ...(clip === "hit2" ? { phase: 2 } : phase !== undefined ? { phase } : {}) });
    x.restore();
    label(x, `${who === "ah" ? "灰燼之心" : "碎晶之主"}・${clip === "hit2" ? "受擊（第 2 階段外觀）" : (BOSS_CLIP_ZH[clip] ?? clip)}${phase !== undefined ? `（第 ${phase} 階段）` : ""}`, X + 10, Y + 18, "#f2e6c8", 13, "left");
    label(x, `${f + 1}/${n}`, X + CW - 10, Y + 18, "#8a8070", 11, "right");
    x.restore();
  });
  document.body.dataset.frames = JSON.stringify(frames.map((q) => [`${q.who}:${q.clip}${q.phase ?? ""}`, q.f, q.n]));
}

function bossPage(): void {
  document.body.style.width = "1280px";
  const W = 200;
  const H = 230;
  const bg = (ctx: Ctx, w: number, kind: BossId): void => {
    ctx.fillStyle = kind === "ah" ? "#2e221c" : "#1e1c34";
    ctx.fillRect(0, 0, w, H);
    if (kind === "ah") {
      ctx.fillStyle = "#3e2e24";
      ctx.fillRect(0, H - 30, w, 30);
      ctx.fillStyle = "rgba(255,106,26,0.18)";
      ctx.fillRect(0, H - 30, w, 4);
    } else {
      ctx.fillStyle = "#34325a";
      ctx.beginPath();
      ctx.ellipse(w / 2, H - 30, w * 0.42, 16, 0, 0, TAU);
      ctx.fill();
      ctx.strokeStyle = "#8a7aff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  };
  const row = (): HTMLElement => {
    const d = document.createElement("div");
    d.style.cssText = "display:flex;gap:10px;flex-wrap:wrap";
    document.body.appendChild(d);
    return d;
  };
  const card = (parent: HTMLElement, cap: string, kind: BossId, draw: (c: Ctx) => void, scale = 2.2): void => {
    const f = document.createElement("figure");
    f.style.cssText = "margin:0;text-align:center;font-size:12px";
    parent.appendChild(f);
    const ctx = cv(W, H, f);
    bg(ctx, W, kind);
    ctx.save();
    ctx.translate(W / 2, H - 30);
    ctx.scale(scale, scale);
    draw(ctx);
    ctx.restore();
    const c = document.createElement("div");
    c.innerHTML = cap;
    f.appendChild(c);
  };
  const rg = (c: Ctx, rx: number): void => ring(c, rx, true);
  h2("1. 灰燼之心");
  const AH = row();
  card(AH, "比例尺位置（樣張這格有主角）", "ah", (c) => drawAshenHeart(c, { phase: 1, shell: 1, t: 300 }, { ring: rg }), 1.3);
  card(AH, "第 1 階段・殼", "ah", (c) => drawAshenHeart(c, { phase: 1, shell: 1, t: 1300 }, { ring: rg }));
  card(AH, "第 1 階段・熔岩噴發", "ah", (c) => drawAshenHeart(c, { phase: 1, shell: 1, t: 300, spout: 0.9 }, { ring: rg }));
  card(AH, "進入第 2 階段・殼裂開", "ah", (c) => drawAshenHeart(c, { phase: 2, shell: 0, breakT: 0.45, t: 600 }, { ring: rg }));
  card(AH, "第 2 階段・呼吸、吸氣", "ah", (c) => drawAshenHeart(c, { phase: 2, shell: 0, breakT: 1, t: 900, inhale: 0.9 }, { ring: rg }));
  card(AH, "第 3 階段・熔毀", "ah", (c) => drawAshenHeart(c, { phase: 3, shell: 0, breakT: 1, t: 1200 }, { ring: rg }), 2.2);
  h2("2. 碎晶之主");
  const SL = row();
  card(SL, "比例尺位置（樣張這格有主角）", "sl", (c) => drawShardLord(c, { phase: 2, t: 900 }, { ring: rg }), 1.3);
  card(SL, "第 1 階段・三柱", "sl", (c) => drawShardLord(c, { phase: 1, t: 400 }, { ring: rg }), 1.9);
  card(SL, "第 2 階段・碎界脈動", "sl", (c) => drawShardLord(c, { phase: 2, t: 900 }, { ring: rg }), 1.9);
  card(SL, "第 2 階段・施法", "sl", (c) => drawShardLord(c, { phase: 2, t: 900, cast: 1 }, { ring: rg }), 1.9);
  card(SL, "第 3 階段・核心過載", "sl", (c) => drawShardLord(c, { phase: 3, t: 1300, blink: 1 }, { ring: rg }), 1.9);
  card(SL, "第 4 階段・界崩", "sl", (c) => drawShardLord(c, { phase: 4, t: 1600 }, { ring: rg }), 1.9);
  h2("3. 東側（朝西）整隻鏡像");
  card(row(), "站在東側：手晶往西伸", "sl", (c) => {
    c.scale(-1, 1);
    drawShardLord(c, { phase: 2, t: 900, cast: 1 }, { ring: rg });
  }, 1.9);
  document.body.dataset.h = String(document.documentElement.scrollHeight);
}

// QK-4b：鳥的待機（落地收翅）與起飛／落地過場（`?view=perch`）：上排待機 8 格；下排移動開頭 perch 1→0（起飛 4 格）、飛行、結尾 0→1（落地）
function perchStrip(): void {
  document.body.style.margin = "0";
  const CW = 150;
  const CH = 150;
  const k = 2.3;
  const look: Spec = { body: "flyer", variant: "bird", material: "fur", tint: "#c8d8f0", element: "lightning" };
  const idle = Array.from({ length: 8 }, (_, f) => ({ t: `待機 ${f + 1}/8`, p: { clip: "idle", u: f / 8 } as CreaturePose }));
  const take = [1, 0.75, 0.5, 0.25, 0].map((q, i) => ({ t: `起飛 ${i + 1}/5`, p: { clip: "move", u: (i % 8) / 8, perch: q } as CreaturePose }));
  const land = [0.25, 0.5, 0.75, 1].map((q, i) => ({ t: `落地 ${i + 1}/4`, p: { clip: "move", u: ((i + 5) % 8) / 8, perch: q } as CreaturePose }));
  const rows = [idle, [...take, ...land.slice(0, 3)], [land[3]!]];
  const x = cv(CW * 8, CH * rows.length);
  rows.forEach((row, r) =>
    row.forEach((c, i) => {
      const X = i * CW;
      const Y = r * CH;
      x.fillStyle = (r + i) % 2 ? "#232638" : "#1e2030";
      x.fillRect(X, Y, CW, CH);
      x.fillStyle = "#2a2d44";
      x.fillRect(X, Y + CH - 22, CW, 22);
      stamp(x, look, X + CW * 0.45, Y + CH - 30, k, false, c.p);
      label(x, c.t, X + 6, Y + 14, "#f2e6c8", 11, "left");
    }),
  );
  document.body.dataset.frames = "[]";
}

// ============================== CB-3：第二種近戰 ==============================
const MELEE2 = ["hound", "feline", "bear", "boar", "lizard"] as const;
const TGT_X = 52; // 目標（相鄰格）的位置：前方 52 單位（同樣張的虛線）
function targetLine(x: Ctx, cx: number, top: number, bottom: number): void {
  x.save();
  x.strokeStyle = "#b04a4a";
  x.lineWidth = 0.8;
  x.setLineDash([3, 3]);
  x.beginPath();
  x.moveTo(cx, top);
  x.lineTo(cx, bottom);
  x.stroke();
  x.restore();
}
/** 第一種（上排）與第二種近戰（下排）逐格並排：每欄同一時間（83.33 ms 一格），片段已結束的欄寫「已結束」。 */
function melee2Strip(bk: string): void {
  document.body.style.margin = "0";
  const west = Q.get("west") === "1";
  const lk = Q.get("look") === "1" ? 1 : 0;
  const k = lk === 1 ? 1.5 : 1.7;
  const CW = lk === 1 ? 190 : 170;
  const CH = lk === 1 ? 230 : 180;
  const HD = 22;
  const clips = [attackClipFor(bk, "melee")!, attackClipFor(bk, "melee2")!];
  const n = Math.max(...clips.map((c) => creatureClipInfo(bk, c)!.n));
  const x = cv(CW * n, (CH + HD) * 2);
  x.fillStyle = "#14161f";
  x.fillRect(0, 0, CW * n, (CH + HD) * 2);
  clips.forEach((clip, row) => {
    const info = creatureClipInfo(bk, clip)!;
    const Y = row * (CH + HD);
    const own = creatureOwnFrames(bk, clip);
    const hit = own !== null ? `，命中格 t=${Math.round(own.hitF * (1000 / 12))}` : "";
    label(x, `${row === 0 ? "現有" : "新增"}：${info.zh}（${clip}，${info.ms} ms，${info.n} 格${hit}）${west ? "朝西" : "朝東"}${REDUCE ? "・減少動態" : ""}`, 6, Y + 15, row === 0 ? "#f2e6c8" : "#e8bb48", 12, "left");
    for (let f = 0; f < n; f++) {
      const X = f * CW;
      const Y0 = Y + HD;
      x.save();
      x.beginPath();
      x.rect(X, Y0, CW, CH);
      x.clip();
      ground(x, X + 1, Y0, CW - 2, CH, f % 2 === 1);
      const cx = west ? X + CW * 0.68 : X + CW * 0.32;
      const gy = Y0 + CH - 22;
      targetLine(x, cx + (west ? -1 : 1) * TGT_X * k, Y0 + 40, gy);
      const done = f >= info.n;
      if (!done) stamp(x, lookOf(bk, clip, lk), cx, gy, k, west, poseOf(clip, f / (info.n - 1)));
      label(x, `t=${Math.round((f * 1000) / 12)}${done ? "（已結束）" : ""}`, X + 5, Y0 + 14, "#f2e6c8", 11, "left");
      x.restore();
    }
  });
  document.body.dataset.frames = JSON.stringify(clips.map((c) => [c, creatureClipInfo(bk, c)!.n]));
}
/** 一列放大的格（3 倍）：每格一個片段的一格。 */
function cb3Row(title: string, cells: ReadonlyArray<{ bk: string; clip: string; u: number; t: string; reduce?: boolean; look?: 0 | 1 }>, k = 3): void {
  document.body.style.margin = "0";
  const CW = 330;
  const CH = 250;
  const HD = 24;
  const x = cv(CW * cells.length, CH + HD);
  x.fillStyle = "#14161f";
  x.fillRect(0, 0, CW * cells.length, CH + HD);
  label(x, title, 6, 16, "#e8bb48", 13, "left");
  cells.forEach((c, i) => {
    const X = i * CW;
    x.save();
    x.beginPath();
    x.rect(X, HD, CW, CH);
    x.clip();
    ground(x, X + 1, HD, CW - 2, CH, i % 2 === 1);
    const gy = HD + CH - 22;
    targetLine(x, X + CW * 0.36 + TGT_X * k, HD + 40, gy);
    stamp(x, lookOf(c.bk, c.clip, c.look ?? 0), X + CW * 0.36, gy, k, false, { clip: c.clip, u: c.u, fxAll: true, ...(c.reduce === true || REDUCE ? { reduce: true } : {}) });
    label(x, c.t, X + 6, HD + 16, "#f2e6c8", 12, "left");
    x.restore();
  });
  document.body.dataset.frames = "[]";
}
function cb3(mode: string): void {
  const hitU = (bk: string, clip: string): number => {
    const info = creatureClipInfo(bk, clip)!;
    const own = creatureOwnFrames(bk, clip);
    return own !== null ? own.hitF / (own.n - 1) : Math.round(creatureAttackHitU(bk, clip) * (info.n - 1)) / (info.n - 1);
  };
  if (mode === "first")
    cb3Row(
      "CB-3・五款的普攻仍是第一種片段（attackClipFor(身形, \"melee\") 的命中格）",
      MELEE2.map((bk) => {
        const clip = attackClipFor(bk, "melee")!;
        return { bk, clip, u: hitU(bk, clip), t: `${ZH(bk)}・普攻＝${creatureClipInfo(bk, clip)!.zh}（${clip}）` };
      }),
    );
  else if (mode === "spots") {
    const pick: ReadonlyArray<readonly [string, number]> = [["idle", 0.5], ["move", 0.25], ["atk:claw", 4 / 7], ["atk:pounce", 5 / 9], ["hit", 0.25], ["death", 7 / 11], ["atk:upcut", 6 / 11]];
    cb3Row("CB-3・山豹斑點改到身體組：各片段的斑點都在身體輪廓內", pick.map(([clip, u]) => ({ bk: "feline", clip, u, t: `山豹・${creatureClipInfo("feline", clip)!.zh}（${clip}，u=${u.toFixed(2)}）` })));
  } else if (mode === "frames") {
    // 逐格放大（3 倍）：&b=<身形>&from=<格>&to=<格>&look=1
    const bk = Q.get("b") ?? "lizard";
    const clip = attackClipFor(bk, "melee2")!;
    const n = creatureClipInfo(bk, clip)!.n;
    const from = Number(Q.get("from") ?? 0);
    const to = Math.min(n - 1, Number(Q.get("to") ?? n - 1));
    cb3Row(`CB-3・${ZH(bk)} ${clip} 逐格放大`, Array.from({ length: to - from + 1 }, (_, i) => ({ bk, clip, u: (from + i) / (n - 1), t: `t=${Math.round(((from + i) * 1000) / 12)}`, look: Q.get("look") === "1" ? (1 as const) : (0 as const) })), Q.get("look") === "1" ? 2 : 3);
  } else
    cb3Row(
      "CB-3・減少動態：第二種近戰的命中格（身體站著、只往前推 2 單位，特效照放）",
      MELEE2.map((bk) => {
        const clip = attackClipFor(bk, "melee2")!;
        return { bk, clip, u: hitU(bk, clip), t: `${ZH(bk)}・${creatureClipInfo(bk, clip)!.zh.split("（")[0]}（減少動態）`, reduce: true };
      }),
    );
}

const anim = Q.get("anim");
const boss = Q.get("boss");
const melee2 = Q.get("melee2");
const cb3Mode = Q.get("cb3");
if (melee2 !== null && (MELEE2 as readonly string[]).includes(melee2)) melee2Strip(melee2);
else if (cb3Mode !== null) cb3(cb3Mode);
else if (anim !== null && BODY_ANIM[anim] !== undefined) atlas(anim);
else if (boss === "atlas") bossAtlas();
else if (boss !== null) bossPage();
else if (Q.get("view") === "strip") strip();
else if (Q.get("view") === "perch") perchStrip();
else page();
