// 開發用：E4b 驗收畫面（`client/dev/e4b-gallery.html`，網址加 `?mute=1`；不屬於正式 build）。
// 規格 docs/phases/PhaseE4b計畫.md；美術移植需求 docs/art/E4-觸發圖示-美術.md 第 6 節；倒地小修 docs/art/E4驗收.md 小修 1。
// 名詞表用前端夾具 `battle/fixtures/glossary.json`（和 /api/glossary 同一份輸出）。畫好後 `document.body.dataset.ready = "1"`。
//   ?part=icons            觸發「格擋時」「你讓別人位移時」：組裝列 30／26／18 真 1 倍（左＝移植前暫借、右＝新）
//   ?part=icons&zoom=6     同上，真 1 倍的畫布 ×6 最近鄰放大（imageSmoothingEnabled=false）
//   ?part=card&t=on_block|on_displace   正式的 SkillCardView（技能列浮動卡的緊湊版、詳細展開）：被動技，組裝列第一格是觸發時機
//   ?part=prone            正式的戰鬥主角卡 Hud → StatusBadge → PartTip：主角倒地，點一下狀態圖示釘住說明框
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import type { GameRules, Glossary, SkillCard, SkillIconData, StatusView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGameRules, setGlossary } from "../battle/glossary";
import { smallView, unit } from "../battle/testFixtures";
import { waitForFonts } from "../render/fontLoad";
import { installPinBadge } from "../render/hudIcon";
import * as QP from "../render/qIcon/parts";
import cards from "../ui/fixtures/skillCards.json";
import { Hud } from "../ui/Hud";
import { SkillCardView } from "../ui/SkillCardView";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);
setGameRules((glossary as unknown as { rules: GameRules }).rules);
installPinBadge(document);
await waitForFonts();

const params = new URLSearchParams(location.search);
const part = params.get("part") ?? "icons";
const ZOOM = Number(params.get("zoom") ?? 1);

const h = <K extends keyof HTMLElementTagNameMap>(tag: K, props: Partial<HTMLElementTagNameMap[K]> = {}, ...kids: Node[]): HTMLElementTagNameMap[K] => {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...kids);
  return e;
};
const cap = (text: string): HTMLElement => h("div", { textContent: text, className: "cap" });
const cell = (...kids: Node[]): HTMLElement => h("div", { className: "cell" }, ...kids);
const line = (...kids: Node[]): HTMLElement => h("div", { className: "line" }, ...kids);
/** 最近鄰放大（真 1 倍的畫布 → k 倍）。 */
function nn(src: HTMLCanvasElement, k: number): HTMLCanvasElement {
  const c = h("canvas", { width: src.width * k, height: src.height * k, className: "px" });
  const x = c.getContext("2d") as CanvasRenderingContext2D;
  x.imageSmoothingEnabled = false;
  x.drawImage(src, 0, 0, src.width, src.height, 0, 0, src.width * k, src.height * k);
  return c;
}
/** 真 1 倍：畫布像素＝CSS 像素（截圖用 DPR 1）。 */
function t1(cv: HTMLCanvasElement): HTMLCanvasElement {
  cv.className = "px";
  cv.style.width = `${cv.width}px`;
  cv.style.height = `${cv.height}px`;
  return cv;
}

const ROWS: readonly [string, string, string][] = [
  ["on_block", "hit_by_melee", "被近戰命中時"],
  ["on_displace", "on_collision", "造成撞擊後"],
];

function icons(): void {
  const shot = h("div", { id: "shot" });
  shot.style.padding = "8px";
  document.body.append(shot);
  shot.append(h("h2", { textContent: `觸發部件（組裝列圓片 30／26／18，QP.chipCanvas res 1）${ZOOM === 1 ? "：真 1 倍" : `：真 1 倍 ×${ZOOM} 最近鄰`}；每組左＝移植前暫借、右＝E4b` }));
  for (const [id, old, oldZh] of ROWS) {
    const cells: Node[] = [];
    for (const px of [30, 26, 18]) {
      for (const [pid, tag] of [[old, "暫借"], [id, "新"]] as const) {
        const cv = QP.chipCanvas("trigger", pid, px, 1, { res: 1 });
        cells.push(cell(ZOOM === 1 ? t1(cv) : nn(cv, ZOOM), cap(`${px} ${tag}`)));
      }
    }
    shot.append(h("h3", { textContent: `${QP.entry("trigger", id).zh}（trigger:${id}；暫借：${oldZh}）` }), line(...cells));
  }
}

const BASE = (cards as unknown as Record<string, SkillCard>)["skill_counterspell"]!;
/** 被動技的卡（只給截圖用）：觸發時機換成 E4 的新時機，效果是護盾（同 E4 實機截圖的「盾後蓄勢」）。 */
function passiveCard(trigger: "on_block" | "on_displace"): SkillCard {
  const icon = BASE.icon as SkillIconData;
  const zh = trigger === "on_block" ? "格擋時（只算近戰）" : "你讓別人位移時";
  return {
    ...BASE,
    id: `dev_e4b_${trigger}`,
    name_zh: trigger === "on_block" ? "盾後蓄勢" : "推後護身",
    skeleton: "passive",
    skeleton_zh: "被動",
    kind: "被動",
    kind_id: "passive",
    rarity: "史詩",
    rarity_id: "epic",
    scaling: "感知",
    scaling_attrs: ["per"],
    weapon_req: null,
    weapon_req_id: null,
    element: null,
    element_id: null,
    shape: "自身",
    cost: [],
    effects: ["護盾（吸收量 10–40＋感知加成，持續 2 回合；已有護盾時取較大值）（自己）"],
    effect_ids: ["shield"],
    timing: `觸發時機：${zh}`,
    keywords: { makes: [], uses: [], basic: true },
    formula_lines: ["護盾算法：骰值＋感知 × 0.5"],
    concept: null,
    cast_flavor: null,
    tags: ["passive"],
    stats: { ...BASE.stats, cooldown: null, range: null, timing: "trigger", costs: [], effects: [] },
    icon: {
      ...icon,
      kind: "passive",
      rarity: "epic",
      elements: [],
      weapon_req: null,
      segments: [{ skeleton: "passive", shape_id: "self", range: null, arm: null, elements: [], effects: [{ type: "shield", status: null, surface: null, condition: null }] }],
      trigger,
      art: { ...icon.art, prop: "act:shield", motion: "pulse", act: "self" },
    },
  } as unknown as SkillCard;
}

function card(): void {
  const t = params.get("t") === "on_displace" ? "on_displace" : "on_block";
  const wrap = h("div", { className: "cards" });
  document.body.append(h("h2", { textContent: `技能卡（正式 SkillCardView，緊湊版＝技能列浮動卡、詳細展開）：組裝列第一格是觸發時機「${QP.entry("trigger", t).zh}」` }), wrap);
  for (const compact of [true, false]) {
    const host = h("div", { className: "card-host" });
    wrap.append(host);
    flushSync(() => createRoot(host).render(<SkillCardView card={passiveCard(t)} compact={compact} detailOpen />));
  }
}

function prone(): void {
  const st = { status_id: "prone", remaining: null, amount: null, source_id: null, cost_status: false } as unknown as StatusView;
  const hero = unit("unit_0001", "ally", 0, 1, { name_zh: "冒險者", hp: 400, max_hp: 400, mana: 656, max_mana: 672, stamina: 200, max_stamina: 200, ap: 4, statuses: [st] });
  const view = { ...smallView(), units: [hero] };
  const host = h("div", { className: "host" });
  document.body.append(h("h2", { textContent: "倒地的說明框（正式的 Hud → StatusBadge → PartTip）：點一下狀態圖示釘住" }), host);
  flushSync(() => createRoot(host).render(<Hud view={view} hero={hero} skills={{}} />));
  const badge = host.querySelector<HTMLElement>(".status-badge");
  badge?.click();
}

if (part === "card") card();
else if (part === "prone") prone();
else icons();
await new Promise((r) => setTimeout(r, 300));
document.body.dataset.ready = "1";
