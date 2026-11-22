// 開發用：WL-1 b 不認得的骨架（開 `client/dev/wl1b-gallery.html`；自己的 vite 後 /dev/wl1b-gallery.html?mute=1）。不屬於正式 build。
// 美術 PM 裁定 docs/art/WL-1b退回圖示.md 最後一節的第 2、3 組截圖：
// - 上：技能卡小圖（56px、mid＝骨架徽章在右下）的不認得骨架，一般與史詩兩種稀有度；左邊是同一招原本的骨架（打擊）對照。
//   `&set=icons` 只畫這一段；`&res=1`（預設）＝真 1 倍（畫布寬高＝CSS px），`&zoom=<k>` 最近鄰放大。
// - 下：正式的 `SkillCardView`（詳細展開）：組裝列的骨架格、卡片種類行；`&set=cards` 只畫這一段。
//   不認得的骨架：伺服器的 `skeleton_zh` 是空字串（`narrative/skills.py` 的 `skeleton_name`），種類行不寫骨架；組裝列顯示「未知骨架」。
//   另一張是「名詞表有、前端覆寫表沒有」的假骨架（名詞表加 `dev_data_skeleton`＝「資料骨架（假）」），組裝列顯示名詞表的中文名。
// 名詞表用前端夾具 `battle/fixtures/glossary.json`。畫好後 `document.body.dataset.ready = "1"`。
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import type { GameRules, Glossary, SkillCard, SkillIconData } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGameRules, setGlossary } from "../battle/glossary";
import { waitForFonts } from "../render/fontLoad";
import { installPinBadge } from "../render/hudIcon";
import { assemblyFormula, skillIconCanvas, SKILL_CARD_ICON_LEVEL, tileTitle } from "../render/skillIcon";
import cards from "../ui/fixtures/skillCards.json";
import { SkillCardView } from "../ui/SkillCardView";
import "../styles/index.css";

const real = glossary as unknown as Glossary;
const DATA_SKELETON = "dev_data_skeleton";
setGlossary({
  ...real,
  skeletons: [...(real.skeletons ?? []), { id: DATA_SKELETON, name_zh: "資料骨架（假）", description_zh: "開發頁的假骨架", tags: [], rules_zh: [], rules_dice: [], status_look: null }],
} as unknown as Glossary);
setGameRules((glossary as unknown as { rules: GameRules }).rules);
installPinBadge(document);
await waitForFonts();

const q = new URLSearchParams(location.search);
const SET = q.get("set") ?? "icons,cards";
const RES = Number(q.get("res") ?? 1);
const ZOOM = Number(q.get("zoom") ?? 1);
const UNKNOWN = "brand_new_skeleton";

const BASE = (cards as unknown as Record<string, SkillCard>)["skill_ash_harvest"]!;
const RARITY_ZH: Record<string, string> = { common: "普通", epic: "史詩" };
/** 開發頁卡名的標註（卡名不放英文 id）。 */
const SKELETON_ZH: Record<string, string> = { strike: "打擊", [UNKNOWN]: "不認得的骨架", [DATA_SKELETON]: "名詞表才有的骨架" };

function withSkeleton(card: SkillCard, skeleton: string, rarity: string, skeletonZh: string): SkillCard {
  const icon = card.icon as SkillIconData;
  return {
    ...card,
    id: `${card.id}_${skeleton}_${rarity}`,
    name_zh: `${card.name_zh}（${RARITY_ZH[rarity] ?? rarity}・${SKELETON_ZH[skeleton] ?? "?"}）`,
    skeleton,
    skeleton_zh: skeletonZh,
    rarity: RARITY_ZH[rarity] ?? rarity,
    rarity_id: rarity,
    icon: { ...icon, rarity, segments: icon.segments.map((s, i) => (i === 0 ? { ...s, skeleton } : s)) },
  } as SkillCard;
}

const h = (tag: string, props: Record<string, string> = {}, ...kids: (Node | string)[]): HTMLElement => {
  const e = document.createElement(tag);
  Object.assign(e, props);
  e.append(...kids);
  return e;
};

if (SET.includes("icons")) {
  document.body.append(h("h2", { textContent: `技能卡小圖 56px（${SKILL_CARD_ICON_LEVEL}）・res ${RES}${ZOOM !== 1 ? `・×${ZOOM}` : ""}：骨架徽章（右下）——打擊（對照）｜不認得的骨架` }));
  const row = h("div", { className: "icons" });
  for (const rarity of ["common", "epic"]) {
    for (const skeleton of ["strike", UNKNOWN]) {
      const icon = withSkeleton(BASE, skeleton, rarity, "").icon as SkillIconData;
      const cv = skillIconCanvas(icon, 56, SKILL_CARD_ICON_LEVEL, RES);
      cv.style.width = cv.style.height = `${56 * ZOOM}px`;
      row.append(h("figure", {}, cv, h("figcaption", { textContent: `${RARITY_ZH[rarity]}｜${skeleton === UNKNOWN ? "不認得" : "打擊"}` })));
    }
  }
  document.body.append(row);
}

if (SET.includes("cards")) {
  document.body.append(h("h2", { textContent: "技能卡（詳細展開）：組裝列的骨架格、種類行（不認得的骨架＝未知骨架；名詞表有的＝名詞表的中文名）" }));
  const list = [withSkeleton(BASE, UNKNOWN, "common", ""), withSkeleton(BASE, UNKNOWN, "epic", ""), withSkeleton(BASE, DATA_SKELETON, "common", "資料骨架（假）")];
  const row = h("div", { className: "row" });
  document.body.append(row);
  for (const card of list) {
    const host = h("div", { className: "card-host" });
    row.append(host);
    flushSync(() => createRoot(host).render(<SkillCardView card={card} detailOpen />));
    const tile = assemblyFormula(card.icon as SkillIconData).rows[0]?.find((t) => t.cat === "骨架");
    host.append(h("div", { className: "note", textContent: `骨架格的說明框標題：${tile === undefined ? "（沒有骨架格）" : tileTitle(tile)}` }));
  }
}

document.body.dataset.ready = "1";
