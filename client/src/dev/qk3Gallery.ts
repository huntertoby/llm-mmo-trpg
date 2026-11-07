// 開發用：QK-3 並排對照（召喚物 17、形態 10、額外裝備 17 件 × 四方向）。開 `client/dev/qk3-gallery.html`（pnpm dev 後 /dev/qk3-gallery.html）。
// 不屬於正式 build；每一列和樣張 docs/art/sample/q-summons-forms.html、q-gear-extra.html 同一個比例（K 像素／單位）與腳底位置，
// 右邊是遊戲的畫法（召喚物、形態用遊戲的貼圖產生器＋陣營底圈；裝備用 qStamp＋樣張色，和 QK-1 的特寫同一套）。
// `window.__qk3.{summon,form,gear,hero}(id)` 回傳該列的 data URL（並排圖腳本用）。
import type { Facing } from "../api/types";
import type { DollSpec } from "../render/appearance";
import { RING } from "../render/artPalette";
import { DOLL_FOOT_Y, DOLL_H, DOLL_SCALE, DOLL_W } from "../render/paperdoll";
import { AURA_H, AURA_W, FORM_ARTS, FORM_FOOT_Y, FORM_H, FORM_W, formAuraRadius, renderAuraCanvas, renderFormCanvas } from "../render/inkForm";
import type { QItem, QSlot, QUnit, QView } from "../render/qCore";
import { SAMPLE_HOOKS, SAMPLE_TEMPLATES } from "../render/qSample";
import { qStamp } from "../render/qStamp";
import { humanoidSpec, Q_SUMMON_FOOT_Y, Q_SUMMON_H, Q_SUMMON_W, renderSummonCanvas, resolveSummonLook, summonRingSize, type SummonLookDraw } from "../render/summonArt";
import { resolveDollT } from "../render/testDolls";

const FACINGS: readonly Facing[] = ["south", "east", "west", "north"];
const DPR = 3;

/** 樣張 qSummon.js 的 17 種（外觀照 content/summon_looks.yaml）。 */
export const SUMMONS: ReadonlyArray<readonly [string, string, SummonLookDraw]> = [
  ["skeleton_warrior", "骷髏戰士", { body: "humanoid", variant: "skeleton", element: "prone", size: "medium", trait: "shield" }],
  ["shade", "影魅", { body: "humanoid", variant: "shade", element: "concealed", size: "medium", trait: "translucent" }],
  ["afterimage", "殘影分身", { body: "humanoid", variant: "afterimage", element: "concealed", size: "medium", trait: "translucent" }],
  ["guardian_spirit", "守護靈", { body: "humanoid", variant: "guardian", element: "summon", size: "medium", trait: "glow" }],
  ["fire_spirit", "火靈", { body: "spirit", element: "ignite", size: "medium" }],
  ["ice_spirit", "冰靈", { body: "spirit", element: "frozen", size: "medium" }],
  ["thunder_spirit", "雷靈", { body: "spirit", element: "charged", size: "medium" }],
  ["water_sprite", "水精", { body: "spirit", element: "wet", size: "small", trait: "puddle" }],
  ["golem", "石像", { body: "construct", variant: "golem", element: "collision", size: "large" }],
  ["bomb_puppet", "爆裂傀儡", { body: "construct", variant: "bomb", element: "ignite", size: "small", trait: "fuse" }],
  ["earth_wall", "土牆", { body: "construct", variant: "wall", element: "collision", size: "medium", trait: "no_ring" }],
  ["war_wolf", "戰狼", { body: "beast", variant: "wolf", element: "prone", size: "medium" }],
  ["hawk", "鷹隼", { body: "beast", variant: "bird", element: "marked", size: "small", trait: "flying" }],
  ["vine", "藤蔓", { body: "plant", element: "prone", size: "medium", trait: "ground" }],
  ["war_totem", "戰意圖騰", { body: "totem", variant: "war", element: "summon", size: "medium", trait: "aura" }],
  ["pull_totem", "吸引圖騰", { body: "totem", variant: "pull", element: "collision", size: "medium" }],
  ["plateau_totem", "高台圖騰", { body: "totem", variant: "plateau", element: "high_ground", size: "medium" }],
];
/** 遊戲的形態畫法 id → 樣張 qForm.js 的 id（roc＝bird）。 */
export const FORMS: ReadonlyArray<readonly [string, string, string]> = [
  ["bear", "bear", "熊"],
  ["cat", "cat", "貓"],
  ["roc", "bird", "鳥（巨鵰）"],
  ["demon", "demon", "惡魔"],
  ["giant", "giant", "巨人"],
  ["avatar", "avatar", "元素化身"],
  ["shadow", "shadow", "暗影形態"],
  ["treant", "treant", "樹人"],
  ["werewolf", "werewolf", "狼人"],
  ["dragon", "dragon", "龍"],
];
const LOOK_OF: Readonly<Record<string, string>> = { bear: "form_bear", cat: "form_cat", roc: "form_roc", demon: "form_demon", giant: "form_giant", avatar: "form_elemental", shadow: "form_shadow", treant: "form_treant", werewolf: "form_werewolf", dragon: "form_dragon" };

/** 樣張 qGearExtra.js 的 17 件 → 遊戲的部件（形制長進 qDoll；樣張的「底」色照抄）。 */
const G = (slot: QSlot, it: QItem): Partial<Record<QSlot, QItem>> => ({ [slot]: { slot, ...it } });
export const GEAR: ReadonlyArray<readonly [string, string, Partial<Record<QSlot, QItem>>]> = [
  ["scale_mail", "鱗甲", G("body", { kind: "mail", form: "scale", material: "iron" })],
  ["hunter", "獵裝", G("body", { kind: "leather", form: "hunter", color: "#6a5a3a" })],
  ["plate_full", "全身板甲", G("body", { kind: "plate", form: "full", material: "steel" })],
  ["coat_cape", "披風外套", G("body", { kind: "coat", form: "cape", color: "#4a5058" })],
  ["apron", "圍裙", G("waist", { kind: "apron" })],
  ["hood_cowl", "斗篷帽", G("head", { kind: "hood", form: "cowl", color: "#5a4a6a" })],
  ["cap_fur", "毛帽", G("head", { kind: "cap", form: "fur", color: "#6a4a2e" })],
  ["gloves_fingerless", "露指手套", G("hands", { kind: "gloves", form: "fingerless", color: "#5a5a6a" })],
  ["gloves_long", "長皮手套", G("hands", { kind: "gloves", form: "long", material: "leather" })],
  ["gauntlet_mail", "鎖鏈護手", G("hands", { kind: "gauntlets", form: "mail", material: "steel" })],
  ["bracer_ring", "臂環", G("hands", { kind: "bracers", form: "ring" })],
  ["shoes_wrapped", "綁腿鞋", G("feet", { kind: "shoes", form: "wrapped", material: "cloth" })],
  ["sabaton", "尖頭鐵靴", G("feet", { kind: "iron_boots", form: "sabaton", material: "iron" })],
  ["greaves_knee", "護膝脛甲", G("feet", { kind: "greaves", form: "knee", material: "steel" })],
  ["pendant_tag", "吊牌", G("neck", { kind: "pendant", form: "tag" })],
  ["charm_tablet", "符牌", G("neck", { kind: "charm", form: "tablet" })],
  ["charm_bone", "骨符", G("neck", { kind: "charm", form: "bone" })],
];
export const HAND_IDS = ["gloves_long", "bracer_ring", "gauntlet_mail", "gloves_fingerless"] as const;

const hex = (n: number): string => `#${n.toString(16).padStart(6, "0")}`;
function mk(w: number, h: number, bg = "#20232f"): { c: HTMLCanvasElement; x: CanvasRenderingContext2D } {
  const c = document.createElement("canvas");
  c.width = Math.round(w);
  c.height = Math.round(h);
  const x = c.getContext("2d")!;
  x.fillStyle = bg;
  x.fillRect(0, 0, c.width, c.height);
  return { c, x };
}
/** 戰場的陣營底圈（unitSprite：rx＝格 0.36、ry＝格 0.15，召喚物可放寬），單位＝紙娃娃單位。 */
function teamRing(x: CanvasRenderingContext2D, cx: number, fy: number, K: number, rxU: number, dxU: number, ring: { fill: number; stroke: number }): void {
  const base = (52 * 0.36) / DOLL_SCALE;
  const R = Math.max(base, rxU);
  const ry = (R * 0.15) / 0.36;
  x.save();
  x.globalAlpha = 0.8;
  x.fillStyle = hex(ring.fill);
  x.beginPath();
  x.ellipse(cx + dxU * K, fy - K / DOLL_SCALE, R * K, ry * K, 0, 0, Math.PI * 2);
  x.fill();
  x.globalAlpha = 1;
  x.strokeStyle = hex(ring.stroke);
  x.lineWidth = (1.5 * K) / DOLL_SCALE;
  x.stroke();
  x.restore();
}

const skeleton = (): DollSpec => resolveDollT({ template: "summon_skeleton_warrior", team: "ally", summon: true });
const hero = (): DollSpec => resolveDollT({ template: "hero_fighter", team: "ally", summon: false });

/** 召喚物一列：南、東、西、北（每格寬 slot 單位、高 70、腳底 60；K＝像素／單位）。 */
export function summonRow(id: string, K = 2.4): HTMLCanvasElement {
  // QK-3b：`elemental_spirit:<關鍵字>`＝元素之靈灌注成該元素（火冰雷水以外畫水滴身體＋元素色＋頭頂圖示）
  const [base, el] = id.split(":");
  const e = SUMMONS.find((s) => s[0] === base);
  const look = resolveSummonLook(el !== undefined ? { body: "spirit", element: el, size: "medium" } : e![2]);
  const wide = id === "war_wolf" || id === "earth_wall";
  const slot = wide ? 84 : 66;
  const { c, x } = mk(slot * 4 * K, 70 * K);
  FACINGS.forEach((f, i) => {
    const cx = (i + 0.5) * slot * K;
    const fy = 60 * K;
    const ring = summonRingSize(look, f);
    if (!(look.body === "construct" && look.variant === "wall")) teamRing(x, cx, fy, K, look.body === "humanoid" ? 0 : ring.rx, look.body === "humanoid" ? 0 : ring.dx, RING.summon);
    const hum = look.body === "humanoid" ? humanoidSpec(look, skeleton(), hero()) : null;
    const tex = renderSummonCanvas(look, f, hum, DPR);
    if (!tex) return;
    const [w, h, fy0] = look.body === "humanoid" ? [DOLL_W, DOLL_H, DOLL_FOOT_Y] : [Q_SUMMON_W, Q_SUMMON_H, Q_SUMMON_FOOT_Y];
    x.drawImage(tex, cx - (w / 2) * K, fy - fy0 * K, w * K, h * K);
  });
  return c;
}

/** 形態一列：南、東、西、北（主角主色藍 #2f5fae、元素冰；每格寬 slot、高 92、腳底 78）。 */
export function formRow(id: string, K = 1.9, heroC = "#2f5fae", element = "ice"): HTMLCanvasElement {
  const slot = id === "dragon" ? 112 : FORM_ARTS[id] && ["bear", "cat", "roc"].includes(id) ? 76 : 62;
  const { c, x } = mk(slot * 4 * K, 92 * K);
  const look = LOOK_OF[id]!;
  FACINGS.forEach((f, i) => {
    const cx = (i + 0.5) * slot * K;
    const fy = 78 * K;
    teamRing(x, cx, fy, K, 0, 0, RING.ally);
    const aura = renderAuraCanvas("#9a86ff", formAuraRadius(look, DOLL_SCALE), DPR);
    const a = K / DOLL_SCALE; // 光環貼圖單位＝52px 格
    if (aura) x.drawImage(aura, cx - (AURA_W / 2) * a, fy - K / DOLL_SCALE - (AURA_H / 2) * a, AURA_W * a, AURA_H * a);
    const tex = renderFormCanvas(id, heroC, element, f, false, DPR, DOLL_SCALE);
    if (tex) x.drawImage(tex, cx - (FORM_W / 2) * K, fy - FORM_FOOT_Y * K, FORM_W * K, FORM_H * K);
  });
  return c;
}

const VIEWS: ReadonlyArray<readonly [QView, boolean]> = [
  ["front", false],
  ["back", false],
  ["side", false],
  ["side", true],
];
const BASE: QUnit = { look: { skin: "#f1c9a5", hair: "short", hairColor: "#6a3d1e" }, gear: { body: { slot: "body", kind: "shirt", color: "#4f7fbf" }, feet: { slot: "feet", kind: "boots", material: "leather" } } };
function shadowAt(x: CanvasRenderingContext2D, cx: number, fy: number, K: number): void {
  x.fillStyle = "rgba(0,0,0,0.28)";
  x.beginPath();
  x.ellipse(cx, fy, (22 * K) / 2.5, (4.5 * K) / 2.5, 0, 0, Math.PI * 2);
  x.fill();
}

/** 放大檢查用：格子跟著 K 放大（比例同 K 2.5）。 */
const gearRowK = (id: string, K = 2.5): HTMLCanvasElement => gearRow(id, K, K / 2.5);
const heroRowK = (id: string, K = 2.5): HTMLCanvasElement => heroRow(id, K, K / 2.5);

/** 裝備一列（同 q-gear-extra.html：正面、背面、朝東、朝西；K 2.5、每格 118×150、腳底 136）。 */
export function gearRow(id: string, K = 2.5, z = 1): HTMLCanvasElement {
  const e = GEAR.find((g) => g[0] === id)!;
  const unit: QUnit = { look: BASE.look, gear: { ...BASE.gear, ...e[2] } };
  const CW = 118 * z;
  const { c, x } = mk(CW * 4, 150 * z);
  VIEWS.forEach(([v, w], j) => {
    const cx = CW * j + CW / 2;
    shadowAt(x, cx, 136 * z, K);
    qStamp(x, unit, v, cx, 132 * z, K, w, SAMPLE_HOOKS, null);
  });
  return c;
}

/** 拿劍盾披風那列：hero_fighter（劍、圓盾、披風）＋手部件＋鱗甲，四方向。 */
export function heroRow(id: string, K = 2.5, z = 1): HTMLCanvasElement {
  const e = GEAR.find((g) => g[0] === id)!;
  const HF = SAMPLE_TEMPLATES.hero_fighter;
  const unit: QUnit = { look: HF.look, gear: { ...HF.gear, ...e[2], body: { slot: "body", kind: "mail", form: "scale", material: "iron" } } };
  const { c, x } = mk(140 * 4 * z, 150 * z);
  VIEWS.forEach(([v, w], j) => {
    const cx = (70 + j * 140) * z;
    shadowAt(x, cx, 136 * z, K);
    qStamp(x, unit, v, cx, 132 * z, K, w, SAMPLE_HOOKS, null);
  });
  return c;
}

declare global {
  interface Window {
    __qk3?: Record<string, (id: string, K?: number) => string>;
  }
}
window.__qk3 = {
  summon: (id) => summonRow(id).toDataURL(),
  form: (id) => formRow(id).toDataURL(),
  gear: (id) => gearRow(id).toDataURL(),
  hero: (id) => heroRow(id).toDataURL(),
  summonK: (id, K) => summonRow(id, K).toDataURL(),
  formK: (id, K) => formRow(id, K).toDataURL(),
  gearK: (id, K) => gearRowK(id, K).toDataURL(),
  heroK: (id, K) => heroRowK(id, K).toDataURL(),
};

// ---- 頁面：全部列出來 ----
const root = document.body;
const sec = (t: string): void => void root.insertAdjacentHTML("beforeend", `<h2>${t}</h2>`);
const put = (c: HTMLCanvasElement, t: string): void => {
  const d = document.createElement("div");
  d.className = "cell";
  d.appendChild(c);
  d.insertAdjacentHTML("beforeend", `<div class="t">${t}</div>`);
  root.appendChild(d);
};
const only = new URLSearchParams(location.search).get("set");
if (!only || only === "summon") {
  sec("召喚物 17 種 × 南、東、西、北");
  for (const [id, zh] of SUMMONS) put(summonRow(id), zh);
}
if (!only || only === "form") {
  sec("形態 10 種 × 南、東、西、北（主色藍、元素冰）");
  for (const [id, , zh] of FORMS) put(formRow(id), zh);
}
if (!only || only === "gear") {
  sec("額外裝備 17 件 × 正面、背面、朝東、朝西");
  for (const [id, zh] of GEAR) put(gearRow(id), zh);
  sec("拿劍盾披風：hero_fighter＋手部件＋鱗甲");
  for (const id of HAND_IDS) put(heroRow(id), id);
}
document.body.dataset.ready = "1";
