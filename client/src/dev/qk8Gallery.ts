// 開發用：QK-8 並排對照（修士 11、盜賊三套 15、NPC 36 × 正、東、西、背）。開 `client/qk8-gallery.html`（pnpm dev 後 /qk8-gallery.html）。
// 不屬於正式 build；每一列和樣張 docs/art/sample/q-npcs.html 同一個版面（每格 58 單位、高 104、1.5 倍、腳底在 CH−12；?z＝放大倍數）。
// 右邊是遊戲的畫法：外觀全部照 content（單位範本 doll＋武器、盜賊區域外觀 region_dolls、NPC 頭像換算成地圖紙娃娃 npcLook），
// 經 resolveDoll → qUnitOf → qStamp（遊戲配色 GAME_HOOKS）。`window.__qk8.row(id, z)` 回傳該列的 data URL（並排圖腳本用）。
import { parse } from "yaml";
import type { DollLook, FieldFigure, Glossary, NpcPortrait } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import { RARITY_GLOW, resolveDoll, type DollSpec } from "../render/appearance";
import type { QView } from "../render/qCore";
import { regionDollLook } from "../render/qNpcRegion";
import { GAME_HOOKS, qUnitOf } from "../render/qSpec";
import { qStamp } from "../render/qStamp";
import { UNIT_DOLLS } from "../render/testDolls";
import { figureFieldLook, npcFieldLook } from "../world/npcLook";
import ashenYaml from "../../../content/world/npcs/ashen_waste.yaml?raw";
import cloudYaml from "../../../content/world/npcs/cloud_ridge.yaml?raw";
import mercYaml from "../../../content/world/mercenaries.yaml?raw";
import tradeYaml from "../../../content/world/trade.yaml?raw";
import capitalYaml from "../../../content/world/fields/capital/capital.yaml?raw";
import smithyYaml from "../../../content/world/fields/capital/interiors/capital_smithy.yaml?raw";
import tavernYaml from "../../../content/world/fields/capital/interiors/capital_tavern.yaml?raw";
import mentorYaml from "../../../content/world/fields/capital/interiors/capital_mentor_hall.yaml?raw";

setGlossary(glossary as unknown as Glossary);

interface Row {
  id: string;
  zh: string;
  spec: () => DollSpec;
  elite?: boolean;
  k?: number;
}

/** 單位範本（doll＋weapon）；region：盜賊的區域外觀。 */
function unitSpec(template: string, weaponId: string, region: string | null = null): DollSpec {
  const doll = regionDollLook(region, template, UNIT_DOLLS[template] as DollLook | undefined);
  return resolveDoll({ template, dollLook: doll, team: "enemy", summon: false, weaponId });
}
const MONKS: ReadonlyArray<readonly [string, string, string, Partial<Row>?]> = [
  ["sect_acolyte", "青霧道童", "totem_staff", { k: 0.9 }],
  ["sect_swordsman", "持劍弟子", "one_handed_sword"],
  ["sect_talisman_caster", "符籙師", "totem_staff"],
  ["sect_alchemist", "煉丹師", "totem_staff"],
  ["sect_warrior_monk", "護法武僧", "fist"],
  ["sect_array_disciple", "劍陣弟子", "one_handed_sword"],
  ["sect_mist_walker", "霧行者", "dagger"],
  ["sect_crane_archer", "雲鶴使", "bow"],
  ["sect_puppeteer", "傀儡師", "totem_staff"],
  ["sect_steward", "青霧執事", "totem_staff", { elite: true }],
  ["sect_mist_lock_master", "霧鎖真人", "one_handed_sword"],
];
const BANDITS: ReadonlyArray<readonly [string, string, string, boolean]> = [
  ["bandit", "盜賊", "dagger", false],
  ["bandit_archer", "弓手", "bow", false],
  ["bandit_shieldbearer", "盾衛", "one_handed_sword", false],
  ["bandit_captain", "隊長", "one_handed_sword", true],
  ["bandit_boss", "頭目", "greatsword", false],
];
const SETS: ReadonlyArray<readonly [string, string | null, string]> = [
  ["base", null, "原版"],
  ["cliff", "cloud_ridge", "斷崖幫"],
  ["ash", "ashen_waste", "荒原"],
];

// ---- NPC：照 content 的頭像外觀換算成地圖紙娃娃（同遊戲的 npcFieldLook／figureFieldLook） ----
interface Card {
  id: string;
  name_zh?: string;
  portrait?: NpcPortrait;
}
const cards = new Map<string, Card>();
for (const y of [cloudYaml, ashenYaml]) for (const c of (parse(y) as { npcs: Card[] }).npcs) cards.set(c.id, c);
for (const c of (parse(mercYaml) as { mercenaries: Card[] }).mercenaries) cards.set(c.id, c);
const walk = (o: unknown, f: (d: Record<string, unknown>) => void): void => {
  if (Array.isArray(o)) o.forEach((x) => walk(x, f));
  else if (o !== null && typeof o === "object") {
    f(o as Record<string, unknown>);
    Object.values(o).forEach((x) => walk(x, f));
  }
};
walk(parse(tradeYaml), (d) => {
  if (typeof d["id"] === "string" && String(d["id"]).startsWith("postman_") && d["portrait"]) cards.set(String(d["id"]), d as unknown as Card);
});
/** 主城的情境物件人物：依頭像的膚色＋髮色認（樣張 qPortrait.js 的 N 表）。 */
const FIGURE_KEY: Readonly<Record<string, string>> = {
  "#d9a47a|#d8d0c0": "seal_keeper",
  "#d9a47a|#8a8478": "hire",
  "#f1c9a5|#c8d0d8": "pool_keeper",
  "#d9a47a|#4a3a2a": "workshop_master",
  "#f1c9a5|#e8e4ec": "mentor",
  "#f1c9a5|#2a2a3a": "scribe",
  "#c88a5a|#2a2420": "smithy",
  "#f1c9a5|#2a1a3a": "enchanter",
  "#e0b088|#6a4a2a": "tavern",
};
const figures = new Map<string, FieldFigure>();
for (const y of [capitalYaml, smithyYaml, tavernYaml, mentorYaml])
  walk(parse(y), (d) => {
    const fig = d["figure"] as FieldFigure | undefined;
    const l = fig?.portrait?.look;
    if (fig && l) {
      const id = FIGURE_KEY[`${l.skin}|${l.hair_color}`];
      if (id) figures.set(id, fig);
    }
  });
/** 傭兵：武器照 build（content/sim/builds.yaml；同樣張 SUGGEST）。 */
const MERC_WEAPON: Readonly<Record<string, string>> = {
  merc_qingfeng: "one_handed_sword",
  merc_chuanyun: "bow",
  merc_chiyan: "fire_staff",
  merc_tiebi: "one_handed_sword",
  merc_panshi: "one_handed_sword",
  merc_huichun: "frost_staff",
  merc_qingyin: "frost_staff",
  merc_jinglei: "lightning_staff",
  merc_fuying: "fire_staff",
};
const MERC_OFF: Readonly<Record<string, { kind: string; material: string }>> = { merc_tiebi: { kind: "shield_kite", material: "steel" }, merc_panshi: { kind: "shield_round", material: "iron" } };
/** 樣張 N 表的順序（群組：傭兵、主城、郵差、雲嶺、荒原）。 */
const NPC_ORDER: ReadonlyArray<readonly [string, string]> = [
  ["merc_qingfeng", "青鋒"], ["merc_chuanyun", "珊瑚"], ["merc_chiyan", "灰燼瑪菈"], ["merc_tiebi", "賽倫"], ["merc_panshi", "鉚釘"],
  ["merc_huichun", "回春"], ["merc_qingyin", "莉瑟"], ["merc_jinglei", "七號線圈"], ["merc_fuying", "鏽牙"],
  ["seal_keeper", "守印人"], ["hire", "傭兵管事"], ["pool_keeper", "守池人"], ["workshop_master", "工坊師傅"], ["mentor", "導師殿導師"],
  ["scribe", "書記"], ["smithy", "樞島鐵匠"], ["enchanter", "附魔師"], ["tavern", "酒館老闆"],
  ["postman_bailu", "白鷺"], ["postman_axin", "阿信"], ["postman_huige", "灰鴿"],
  ["granny_du", "渡婆婆"], ["shopkeeper_liu", "柳掌櫃"], ["daoist_qingya", "青崖道長"], ["hunter_ayue", "阿岳"], ["acolyte_xiaolian", "小蓮"],
  ["mistlock_master", "霧鎖真人"], ["scarface", "疤面"], ["smith_shi", "石師傅"], ["gran", "葛蘭"],
  ["iron_lady", "鐵娘"], ["greybeard", "灰鬚"], ["smith_lu", "爐叔"], ["scavenger_laotie", "老鐵"], ["priestess_helin", "赫琳"], ["overseer_scar", "鍛疤"],
];
function npcSpec(id: string): DollSpec {
  const fig = figures.get(id);
  const look = fig ? figureFieldLook(id, fig) : npcFieldLook({ id, portrait: cards.get(id)?.portrait ?? null });
  if (look === null) return resolveDoll({ template: id, team: "third", summon: false });
  const mw = MERC_WEAPON[id];
  let doll = look.doll_look as DollLook;
  if (mw) {
    doll = { ...doll } as DollLook;
    delete (doll as { main_kind?: string }).main_kind;
    const off = MERC_OFF[id];
    if (off) doll = { ...doll, gear: { ...(doll.gear ?? {}), off_hand: off } } as DollLook;
  }
  return resolveDoll({ template: look.template_id, dollLook: doll, team: "third", summon: false, weaponId: mw ?? look.weapon_id, weaponClass: look.weapon_class, raceLook: look.race_look as Record<string, unknown> | null });
}

export const ROWS: Row[] = [
  ...MONKS.map(([t, zh, w, o]) => ({ id: `monk_${t}`, zh, spec: () => unitSpec(t, w), ...(o ?? {}) })),
  ...SETS.flatMap(([set, region, szh]) => BANDITS.map(([t, zh, w, elite]) => ({ id: `bandit_${set}_${t}`, zh: `${szh}${zh}`, elite, spec: () => unitSpec(t, w, region) }))),
  ...NPC_ORDER.map(([id, zh]) => ({ id: `npc_${id}`, zh, spec: () => npcSpec(id) })),
];

const VIEWS: ReadonlyArray<readonly [QView, boolean]> = [
  ["front", false],
  ["side", false],
  ["side", true],
  ["back", false],
];

/** 一列四方向（同 q-npcs.html 的 cell 版面；z＝放大）。 */
export function row(id: string, z = 1): HTMLCanvasElement {
  const r = ROWS.find((x) => x.id === id)!;
  const spec = r.spec();
  const unit = qUnitOf(spec);
  const SZ = 1.5 * z;
  const CW = 58 * z;
  const CH = 104 * z;
  const PAD = 4 * z;
  const dpr = 2;
  const c = document.createElement("canvas");
  c.width = (CW * 4 + PAD * 2) * dpr;
  c.height = CH * dpr;
  const x = c.getContext("2d")!;
  x.scale(dpr, dpr);
  const k = SZ * (r.k ?? 1);
  const glow = spec.rarity ? RARITY_GLOW[spec.rarity] : undefined;
  VIEWS.forEach(([v, w], i) => {
    const cx = PAD + CW * i + CW / 2;
    const cy = CH - 12 * z;
    x.fillStyle = "rgba(0,0,0,0.25)";
    x.beginPath();
    x.ellipse(cx, cy, 11 * k, 3.2 * k, 0, 0, Math.PI * 2);
    x.fill();
    if (r.elite) {
      x.strokeStyle = "#16121a";
      x.lineWidth = 2.6;
      x.beginPath();
      x.ellipse(cx, cy, 13 * k, 4 * k, 0, 0, Math.PI * 2);
      x.stroke();
      x.strokeStyle = "#ffbf3a";
      x.lineWidth = 1.3;
      x.stroke();
    }
    if (glow) {
      // 頭目外光：照遊戲 paperdoll.renderFigureCanvas 的畫法（剪影染色、半透明、12 個方向各偏 2.6 單位疊一圈），沿輪廓一圈。
      // QK-8b：原本用 shadowBlur 14×size×dpr（樣張 opts.glow），2 倍放大時模糊半徑 84 像素、四格的外光連成一片鋪滿整列，和遊戲不同。
      const t = document.createElement("canvas");
      t.width = c.width;
      t.height = c.height;
      const tx = t.getContext("2d")!;
      tx.scale(dpr, dpr);
      qStamp(tx, unit, v, cx, cy, k, w, GAME_HOOKS, null, { dpr: 2 });
      tx.setTransform(1, 0, 0, 1, 0, 0);
      tx.globalCompositeOperation = "source-in";
      tx.fillStyle = glow;
      tx.fillRect(0, 0, t.width, t.height);
      x.save();
      x.setTransform(1, 0, 0, 1, 0, 0);
      x.globalAlpha = 0.5;
      for (let a = 0; a < 12; a++) {
        const ang = (a / 12) * Math.PI * 2;
        x.drawImage(t, Math.cos(ang) * 2.6 * k * dpr, Math.sin(ang) * 2.6 * k * dpr);
      }
      x.restore();
    }
    qStamp(x, unit, v, cx, cy, k, w, GAME_HOOKS, null, { dpr: 2 });
  });
  return c;
}

/** QK-8b 補拍：玩家（主角預設外觀＋單手劍）戴頸飾，走遊戲的裝備路徑（`equipment` → dollGear → resolveDoll），四方向。 */
export const NECKS: ReadonlyArray<readonly [string, string, string]> = [
  ["pendant", "pendant", "墜飾"],
  ["pendant", "tag", "吊牌"],
  ["charm", "tablet", "符牌（護符）"],
  ["charm", "bone", "骨符（護符）"],
];
export function neckRow(i: number, z = 2): HTMLCanvasElement {
  const [kind, form] = NECKS[i]!;
  const spec = resolveDoll({ template: "hero", team: "ally", summon: false, weaponId: "one_handed_sword", equipment: [{ slot: "neck", appearance: { kind, form } }] });
  const unit = qUnitOf(spec);
  const k = 1.5 * z;
  const CW = 58 * z;
  const CH = 104 * z;
  const PAD = 4 * z;
  const dpr = 2;
  const c = document.createElement("canvas");
  c.width = (CW * 4 + PAD * 2) * dpr;
  c.height = CH * dpr;
  const x = c.getContext("2d")!;
  x.scale(dpr, dpr);
  x.fillStyle = "#20232f";
  x.fillRect(0, 0, c.width, c.height);
  VIEWS.forEach(([v, w], j) => {
    const cx = PAD + CW * j + CW / 2;
    const cy = CH - 12 * z;
    x.fillStyle = "rgba(0,0,0,0.25)";
    x.beginPath();
    x.ellipse(cx, cy, 11 * k, 3.2 * k, 0, 0, Math.PI * 2);
    x.fill();
    qStamp(x, unit, v, cx, cy, k, w, GAME_HOOKS, null, { dpr: 2 });
  });
  return c;
}

declare global {
  interface Window {
    __qk8?: { ids: string[]; row: (id: string, z?: number) => string; neck: (i: number, z?: number) => string };
  }
}
window.__qk8 = { ids: ROWS.map((r) => r.id), row: (id, z) => row(id, z).toDataURL(), neck: (i, z) => neckRow(i, z).toDataURL() };

const root = document.body;
const z = Number(new URLSearchParams(location.search).get("z") ?? "1");
let last = "";
for (const r of ROWS) {
  const g = r.id.split("_").slice(0, r.id.startsWith("bandit") ? 2 : 1).join("_");
  if (g !== last) root.insertAdjacentHTML("beforeend", `<h2>${g}</h2>`);
  last = g;
  const d = document.createElement("div");
  d.className = "cell";
  d.appendChild(row(r.id, z));
  d.insertAdjacentHTML("beforeend", `<div class="t">${r.zh}</div>`);
  root.appendChild(d);
}
document.body.dataset.ready = "1";
