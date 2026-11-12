// 開發用：技能圖示的 Q 版主圖、部件小圓片、技能卡小圖一覽（Phase QI-2b；QI-2c 加遊戲端實際組裝與實例名單）。
// 開 `client/dev/skillicon-gallery.html`（自己的 vite 後 /dev/skillicon-gallery.html?mute=1）。不屬於正式 build。
// 資料：`render/fixtures/skill_icons.json`（402 招＋隨機 50＋工坊示範），主圖代碼一律用 fixture 的 `art`（QI-2a 的 `SkillIcon.art`；
//   QI-2c 刪掉 2b 的暫時資料 qi2bTempArt.json）。fixture 沒有招名，標籤寫技能 id（去掉 `skill_`）。
// QI-2c：有技能資料的格子一律走遊戲端 `render/skillIcon.ts` 的 `paintSkillIcon`（main＝主圖、mid／full＝`partsOf` → `toQParts` → `paintIcon`），
//   和遊戲畫面同一條路；只有合成的 look（道具、出手、記號總表沒有現成招時）直接畫主圖。
// 參數（驗收截圖用，規格 docs/phases/PhaseQI-2計畫.md 第 6 節 B4、第 8.2 節）：
//   ?px=<CSS px>[,<CSS px>…]  圖示邊長，可給多個並排（預設 40；部件預設 18、卡片小圖預設 16,18）
//   &res=<1|2>[,<1|2>]        內部解析度（預設 2＝遊戲的畫法；1＝真 1 倍：畫布寬高＝CSS px）；給兩個時兩種並排
//   &zoom=<k>                 放大 k 倍顯示（CSS zoom ＋ image-rendering: pixelated，最近鄰）；截圖用裝置像素比 1 拍
//   &level=main|mid|full      主圖（預設）／技能卡 56 的 mid／工坊 96 的 full（2b 只供對照，遊戲端組裝在 2c）
//   &set=skills|props|motions|acts|starters|named|iconprop|real|parts|card|change（逗號接多段，依序排在同一頁）
//        skills    402 招的全部不同長相（同一組 prop|motion|act|tint|el|el2|spark|kind|rarity 只列一次；第 8.2 節第 1 項）
//        props     道具總表（每個道具一招；沒有實際招用到的以合成 look 補，標「合成」；第 2 項）
//        motions   出手 9 種、acts 效果記號 23 種（各取第一招；第 2 項）
//        starters  六招入門招（第 3 項）
//        list      &skills=<id>[,…] 指定的招（特寫用）
//        named     點名款：化身 10、產下幼蜥、召喚守護靈、雙牙；弓槍配大記號＋散彈驅離；地面效果六種外形；拳套配記號；直線突刺（第 4 項）
//        iconprop  填了 icon_prop 的招（標道具值；改變出手的 6 招標紅；第 6 項）
//        real      實例：照樣張頁 q-icons-skills.html 的 realPicks()（六招入門招＋每種道具／出手／記號／元素底／技能類型各補到至少一招＋
//                  物理揮砍、物理飛行物兩個最大同圖群各補到 8 招）；用遊戲的 art（含 icon_prop）算，共 75 招（樣張 skills-real.png 也是 75 招；
//                  因 icon_prop 有 5 招和樣張不同，見 QI-2c 報告）；&old=1 並排現行畫法；第 5 項
//        motionchg icon_prop 改變出手的 6 招，標「招名｜舊道具・舊出手 → 新道具・新出手」（QI-2c 截圖給美術逐招看）
//        parts     部件小圓片全部（組裝列 chipCanvas，類別一列；&cat= 只列一類，&cat=&id= 只列一個；第 7 項）
//        card      技能卡小圖 22 個＋圖釘兩態（第 8 項）
//        change    修正內容 21 個鍵：數值正、負各一（箭頭朝上橘黃／朝下青色；第 11 項）
//   &ids=<cat:id>[,…]         set=parts 只列這幾個（例：第 2 版改過的款）
//   &from=<i>&n=<k>          只列第 i 項起的 k 項（截圖分張用）
//   &label=0                 不顯示名稱
//   &old=1                   並排現行畫法（`skillIcon.ts` 的 paintLegacySkillIcon；只有主圖類的 set）
// 另外掛 `window.__qiSkillDev`（和樣張逐像素比對用）：main(look, px, res)、icon(id, px, res, level)、chip(cat, id, px, res)、card(id, px, res, pinned)、
//   looks()、partList()、framePath（給樣張頁的 `AssembledIcon.framePath`）。
import data from "../render/fixtures/skill_icons.json";
import type { SkillIconData } from "../api/types";
import { paintLegacySkillIcon, paintSkillIcon, type SkillIconLevel } from "../render/skillIcon";
import { framePath } from "../render/skillGlyphs";
import { blank, ctxOf, M } from "../render/qIcon/core";
import { MATERIAL } from "../render/material";
import * as QS from "../render/qIcon/skills";
import * as QP from "../render/qIcon/parts";
import { skillLook, type SkillArt } from "../render/qIcon/partsAdapter";

const SKILLS = (data as unknown as { skills: Record<string, SkillIconData & { art?: SkillArt | null; icon_prop?: string | null }> }).skills;
const q = new URLSearchParams(location.search);
const nums = (v: string | null, d: number[]): number[] => (v === null ? d : v.split(",").map(Number).filter((n) => n > 0));
const SET = q.get("set") ?? "skills";
const PX = nums(q.get("px"), SET.startsWith("parts") ? [18] : SET === "card" ? [16, 18] : SET === "change" ? [30, 18] : [40]);
const RES = nums(q.get("res"), [2]);
const ZOOM = Number(q.get("zoom") ?? 1);
const LEVEL = q.get("level") ?? "main";
const LABEL = q.get("label") !== "0";
const OLD = q.get("old") === "1";
const FROM = Number(q.get("from") ?? 0);
const N = q.get("n") === null ? Infinity : Number(q.get("n"));
/** icon_prop 改變出手的 6 招（規格第 0 節第 6 列）：招名、沒有 icon_prop 時的道具與出手（樣張 qSkillsData.js 的推導值，QI-2c 對照算出）。 */
const MOTION_CHANGED: Readonly<Record<string, readonly [string, string, string]>> = {
  skill_ambush_stab: ["迎頭痛擊", "w:sword", "swing"],
  skill_flurry_jab: ["連環快刺", "w:sword", "swing"],
  skill_ground_finish: ["倒地補刀", "w:sword", "swing"],
  skill_marrow_thorn: ["蝕骨刺", "w:sword", "swing"],
  skill_venom_blade: ["毒刃", "w:sword", "swing"],
  skill_ember_bite: ["餘燼啃咬", "w:sword", "swing"],
};

/** 一招的 art（fixture；沒有時 skillLook 退 none／aura／buff）。 */
const artOf = (id: string): SkillArt | null => SKILLS[id]?.art ?? null;
const nameOf = (id: string): string => MOTION_CHANGED[id]?.[0] ?? id.replace(/^skill_/, "");
const lookOf = (id: string): QS.SkillLook => skillLook(SKILLS[id] as SkillIconData, artOf(id));
const lookKey = (l: QS.SkillLook): string => [l.prop, l.motion, l.act, l.tint, l.el, l.el2, l.spark, l.kind, l.rarity].join("|");

// ---------------- 畫 ----------------
/** 技能圖示：有技能資料時走遊戲端 `paintSkillIcon`（main／mid／full）；只有 look（合成）時畫主圖。 */
function mainCanvas(look: QS.SkillLook, px: number, res: number, icon?: SkillIconData, level = LEVEL): HTMLCanvasElement {
  const cv = blank(Math.round(px * res)), x = ctxOf(cv);
  x.scale(res, res);
  if (icon) paintSkillIcon(x, icon, level as SkillIconLevel, px, res);
  else QS.paint(x, look, px, res);
  return cv;
}
/** 現行（QI-2c 前）畫法：100×100 座標、內部解析度 2。 */
function oldCanvas(icon: SkillIconData, px: number): HTMLCanvasElement {
  const cv = blank(px * 2), x = ctxOf(cv);
  x.scale((px * 2) / 100, (px * 2) / 100);
  paintLegacySkillIcon(x, icon, px <= 40);
  return cv;
}
const chipCanvas = (cat: string, id: string, px: number, res: number, opt: QP.PartOpt = {}): HTMLCanvasElement => QP.chipCanvas(cat, id, px, 1, { ...opt, res });
const cardCanvas = (id: string, px: number, res: number, pinned = true): HTMLCanvasElement => QP.cardCanvas(id, px, 1, { res, pinned });

function show(src: HTMLCanvasElement, px: number, cls = ""): HTMLElement {
  const c = document.createElement("canvas");
  c.width = src.width;
  c.height = src.height;
  c.style.width = `${px}px`;
  c.style.height = `${px}px`;
  if (cls) c.className = cls;
  c.getContext("2d")?.drawImage(src, 0, 0);
  const z = document.createElement("div");
  z.className = "zoom";
  z.style.zoom = String(ZOOM);
  z.appendChild(c);
  return z;
}
interface Item { label: string; mark?: boolean; draw: (px: number, res: number) => HTMLCanvasElement; old?: (px: number) => HTMLCanvasElement }
function cell(it: Item): HTMLElement {
  const box = document.createElement("div");
  box.className = it.mark ? "cell mark" : "cell";
  const pics = document.createElement("div");
  pics.className = "pics";
  for (const res of RES) for (const px of PX) pics.appendChild(show(it.draw(px, res), px));
  if (OLD && it.old) for (const px of PX) pics.appendChild(show(it.old(px), px, "old"));
  box.appendChild(pics);
  if (LABEL) {
    const t = document.createElement("div");
    t.className = "label";
    t.textContent = it.label;
    box.appendChild(t);
  }
  return box;
}
function section(title: string, items: Item[]): void {
  const h = document.createElement("h2");
  h.textContent = `${title}（${items.length}）`;
  const row = document.createElement("div");
  row.className = "row";
  for (const it of items.slice(FROM, FROM + N)) row.appendChild(cell(it));
  document.body.append(h, row);
}
const skillItem = (id: string, label = nameOf(id), mark = false): Item => ({
  label,
  mark,
  draw: (px, res) => mainCanvas(lookOf(id), px, res, SKILLS[id]),
  old: (px) => oldCanvas(SKILLS[id] as SkillIconData, px),
});
const lookItem = (look: QS.SkillLook, label: string): Item => ({ label, draw: (px, res) => mainCanvas(look, px, res) });

// ---------------- 清單 ----------------
const IDS = Object.keys(SKILLS).sort();

/**
 * 實例名單：照樣張頁 `docs/art/sample/q-icons-skills.html` 的 `realPicks()` 逐行搬（QI-2c，開發 PM 追加 2）。
 * 欄位對照：樣張 `s.q`＝這裡的 look（prop、motion、act、el＝elements[0] ?? null）、`s.kind`＝icon.kind、`s.shape`＝第一段 shape_id、
 * `s.range === "weapon"`＝第一段 range 為 null 且只有一段（遊戲 fixture 沒有 "weapon" 字串；對 402 招逐招比過，判定和樣張相同）、
 * `s.effects`＝全部段的效果。
 */
export function realPicks(): string[] {
  const STARTER_IDS = ["skill_shadow_backstab", "skill_wild_blade", "skill_rng_venom_arrow", "skill_oil_spark_throw", "skill_fire_bolt", "skill_spark_chain"];
  const out = [...STARTER_IDS], seen = new Set<string>();
  const want = (id: string): string[] => { const l = lookOf(id), k = SKILLS[id]?.kind ?? ""; return [String(l.prop), "m:" + String(l.motion), "a:" + String(l.act), "e:" + String(l.el ?? null), "k:" + k].filter((x) => !seen.has(x)); };
  const add = (id: string): void => { if (!out.includes(id)) out.push(id); for (const k of want(id)) seen.add(k); };
  out.forEach(add);
  for (const id of IDS) if (want(id).some((k) => !k.startsWith("k:") && !k.startsWith("e:"))) add(id);
  for (const id of IDS) if (want(id).length) add(id);
  const plain = (id: string, req: string): boolean => {
    const i = SKILLS[id] as SkillIconData;
    return i.kind === "active" && i.elements[0] === "physical" && i.segments.length === 1 && i.segments[0]?.shape_id === "single" && i.segments[0]?.range == null && i.weapon_req === req && i.segments.every((g) => g.effects.every((e) => e.type === "damage"));
  };
  for (const req of ["melee", "ranged"]) { let n = out.filter((id) => plain(id, req)).length; for (const id of IDS) if (plain(id, req) && !out.includes(id) && n < 8) { n++; add(id); } }
  return out;
}
/** 第一招符合的（沒有就 null）。 */
const firstId = (ok: (l: QS.SkillLook, id: string) => boolean): string | null => IDS.find((id) => ok(lookOf(id), id)) ?? null;
const byTable = (keys: { key: string; zh: string }[], field: "prop" | "motion" | "act", synth: (key: string) => QS.SkillLook): Item[] =>
  keys.map((k) => {
    const id = firstId((l) => l[field] === k.key);
    return id ? skillItem(id, `${k.key}｜${nameOf(id)}`) : lookItem(synth(k.key), `${k.key}｜合成`);
  });

function sets(SET: string): void {
  const L = QS.list();
  switch (SET) {
    case "skills": {
      const seen = new Set<string>(), items: Item[] = [];
      for (const id of IDS) { const k = lookKey(lookOf(id)); if (!seen.has(k)) { seen.add(k); items.push(skillItem(id)); } }
      section("主圖：不同長相", items);
      break;
    }
    case "props":
      section("道具", byTable(L.props, "prop", (k) => ({ prop: k, motion: k.startsWith("w:") ? "swing" : "aura", act: "hit", el: null })));
      break;
    case "motions":
      section("出手", byTable(L.motions, "motion", (k) => ({ prop: "el:arcane", motion: k, act: "hit", el: "default" })));
      break;
    case "acts":
      section("效果記號", byTable(L.acts, "act", (k) => ({ prop: "w:sword", motion: "swing", act: k, el: null })));
      break;
    case "list":
      section("指定招", (q.get("skills") ?? "").split(",").filter((id) => SKILLS[id] !== undefined).map((id) => skillItem(id)));
      break;
    case "starters":
      section("六招入門招", ["skill_shadow_backstab", "skill_wild_blade", "skill_rng_venom_arrow", "skill_oil_spark_throw", "skill_fire_bolt", "skill_spark_chain"].map((id) => skillItem(id)));
      break;
    case "named": {
      section("化身", IDS.filter((id) => lookOf(id).prop?.startsWith("form:")).map((id) => skillItem(id)));
      section("產下幼蜥、召喚守護靈、雙牙", ["skill_summon_ember_whelp", "skill_summon_guardian_spirit", "skill_twin_fang"].map((id) => skillItem(id)));
      const kindOf = (l: QS.SkillLook): string => (l.prop ?? "").slice(2).split("/")[0] ?? "";
      section("弓、火槍、霰彈槍配大記號＋散彈驅離", IDS.filter((id) => { const l = lookOf(id); return (["bow", "longgun", "shotgun"].includes(kindOf(l)) && l.prop?.startsWith("w:") && QS.def(l).meta.side === "br") || id === "skill_scatter_shot"; }).map((id) => skillItem(id)));
      const shapeOf = (t: string | null | undefined): string => (t === "stone" || t === "holy" || t === "ice" || t === "fire" ? t : t === "steel" || t === "shadow" ? "cloud" : "liquid");
      const seen = new Set<string>();
      section("地面效果六種外形", IDS.filter((id) => { const l = lookOf(id); if (l.act !== "surface" && l.act !== "terrain") return false; const s = shapeOf(l.act === "terrain" ? "stone" : l.tint); if (seen.has(s)) return false; seen.add(s); return true; }).map((id) => skillItem(id, `${nameOf(id)}｜${lookOf(id).tint ?? ""}`)));
      section("拳套配記號", IDS.filter((id) => { const l = lookOf(id); return l.prop?.startsWith("w:fist") === true && QS.def(l).meta.side !== "none"; }).map((id) => skillItem(id, `${nameOf(id)}｜${lookOf(id).act ?? ""}`)));
      section("直線突刺（武器）", IDS.filter((id) => { const l = lookOf(id); return l.motion === "thrust" && l.prop?.startsWith("w:") === true; }).map((id) => skillItem(id)));
      break;
    }
    case "iconprop":
      section("icon_prop", IDS.filter((id) => SKILLS[id]?.icon_prop).map((id) => skillItem(id, `${nameOf(id)}｜${SKILLS[id]?.icon_prop ?? ""}｜${lookOf(id).motion ?? ""}`, MOTION_CHANGED[id] !== undefined)));
      break;
    case "motionchg":
      section(
        "icon_prop 改變出手的 6 招（舊＝沒有 icon_prop 時的推導 → 新）",
        Object.entries(MOTION_CHANGED).map(([id, [name, prop, motion]]) => skillItem(id, `${name}｜${prop}・${motion} → ${lookOf(id).prop ?? ""}・${lookOf(id).motion ?? ""}`, true)),
      );
      break;
    case "real":
      section("實例（樣張 realPicks 規則）：Q 版｜現行", realPicks().map((id) => skillItem(id)));
      break;
    case "parts": {
      const cat = q.get("cat"), id = q.get("id"), ids = q.get("ids")?.split(",") ?? null, all = QP.list();
      for (const [c, list] of Object.entries(all)) {
        if (c === "card" || (cat !== null && c !== cat)) continue;
        section(`${QP.CAT_ZH[c] ?? c}`, list.filter((e) => (id === null || e.id === id) && (ids === null || ids.includes(`${c}:${e.id}`))).map((e) => ({ label: `${e.id}`, draw: (px, res) => chipCanvas(c, e.id, px, res) })));
      }
      break;
    }
    case "card": {
      const items: Item[] = Object.keys(QP.CARD).map((id) => ({ label: id, draw: (px, res) => cardCanvas(id, px, res) }));
      items.push({ label: "pin（未釘）", draw: (px, res) => cardCanvas("pin", px, res, false) });
      section("技能卡小圖", items);
      break;
    }
    case "change": {
      const values: Record<string, unknown[]> = {};
      for (const icon of Object.values(SKILLS)) for (const ch of icon.modifier?.changes ?? []) (values[ch.key] ??= []).push(ch.value);
      section("修正內容（實際數值）", Object.keys(QP.CHANGE).map((k) => { const v = values[k]?.[0]; return { label: `${k}｜${v === undefined ? "—" : String(v)}`, draw: (px, res) => chipCanvas("change", k, px, res, { value: v as QP.PartOpt["value"] }) }; }));
      section("修正內容（+1／−1）", Object.keys(QP.CHANGE).flatMap((k) => [1, -1].map((v) => ({ label: `${k}｜${v > 0 ? "+" : "−"}`, draw: (px: number, res: number) => chipCanvas("change", k, px, res, { value: v }) }))));
      break;
    }
    default:
      section(`不認得的 set：${SET}`, []);
  }
}

for (const s of SET.split(",")) sets(s);

declare global {
  interface Window {
    __qiSkillDev?: unknown;
  }
}
window.__qiSkillDev = {
  main: (look: QS.SkillLook, px: number, res: number) => mainCanvas(look, px, res, undefined, "main"),
  icon: (id: string, px: number, res: number, level: string) => mainCanvas(lookOf(id), px, res, SKILLS[id], level),
  chip: chipCanvas,
  card: cardCanvas,
  looks: () => IDS.map((id) => ({ id, look: lookOf(id), icon: SKILLS[id] })),
  partList: () => QP.list(),
  framePath,
  /** 遊戲端的材質色（樣張的 M／MAT 換成這份再比，QI-1 第 0.0 節第 3 點）。 */
  M,
  MATERIAL,
};
document.body.dataset["ready"] = "1";
