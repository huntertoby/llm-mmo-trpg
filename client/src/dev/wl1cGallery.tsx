// 開發用：WL-1 c 骨架、狀態名稱統一（開 `client/dev/wl1c-gallery.html`；自己的 vite 後 /dev/wl1c-gallery.html?mute=1）。不屬於正式 build。
// `&set=` 逗號接多段：
// - `rename`：資料和舊前端表用字不同的 6 個骨架，用正式的 `SkillCardView`（詳細展開）畫：組裝列骨架格＋種類行。
//   aura、control、reaction 用夾具的真技能卡；builder_finisher、consume_status、modifier 夾具沒有，借「灰燼收割」換骨架（種類行照名詞表）。
// - `status`：名詞表沒有的狀態（`brand_new_status`）：狀態卡 `StatusBadge`（`#unk-badge`，點一下開說明框）、狀態的部件圓片 `statusTile`（`#unk-tile`，工坊狀態選項與組裝列同一套圓片；點一下開說明框）、
//   技能卡組裝列的附加狀態格（借「驟雨」把緩速換成它）。
// - `empty`：骨架是空字串（當作沒有骨架）：技能卡（詳細展開）的組裝列沒有骨架格、卡片小圖沒有徽章；旁邊是同一招 null 與原本「打擊」的對照。
// 名詞表用前端夾具 `battle/fixtures/glossary.json`。畫好後 `document.body.dataset.ready = "1"`。
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import type { GameRules, Glossary, SkillCard, SkillIconData, StatusView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGameRules, setGlossary, skeletonName } from "../battle/glossary";
import { waitForFonts } from "../render/fontLoad";
import { installPinBadge } from "../render/hudIcon";
import cards from "../ui/fixtures/skillCards.json";
import { SkillCardView } from "../ui/SkillCardView";
import { statusLine } from "../ui/Hud";
import { StatusBadge } from "../ui/StatusCardParts";
import { TipGlyph } from "../ui/SkillIconView";
import { statusTile } from "../render/skillIcon";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);
setGameRules((glossary as unknown as { rules: GameRules }).rules);
installPinBadge(document);
await waitForFonts();

const q = new URLSearchParams(location.search);
const SET = q.get("set") ?? "rename";
const ALL = cards as unknown as Record<string, SkillCard>;
const BASE = ALL["skill_ash_harvest"]!;

function withSkeleton(card: SkillCard, skeleton: string, tag: string): SkillCard {
  const icon = card.icon as SkillIconData;
  return {
    ...card,
    id: `${card.id}_${skeleton}`,
    name_zh: `${card.name_zh}（${tag}）`,
    skeleton,
    skeleton_zh: skeleton === "" ? "" : skeletonName(skeleton),
    icon: { ...icon, segments: icon.segments.map((s, i) => (i === 0 ? { ...s, skeleton } : s)) },
  } as SkillCard;
}

const h = (tag: string, props: Record<string, string> = {}, ...kids: (Node | string)[]): HTMLElement => {
  const e = document.createElement(tag);
  Object.assign(e, props);
  e.append(...kids);
  return e;
};

function cardRow(title: string, list: SkillCard[]): void {
  document.body.append(h("h2", { textContent: title }));
  const row = h("div", { className: "row" });
  document.body.append(row);
  for (const card of list) {
    const host = h("div", { className: "card-host" });
    row.append(host);
    flushSync(() => createRoot(host).render(<SkillCardView card={card} detailOpen />));
  }
}

if (SET.includes("rename")) {
  const real = (sk: string): SkillCard => Object.values(ALL).find((c) => c.skeleton === sk)!;
  const list = [
    withSkeleton(BASE, "builder_finisher", "借來換骨架"),
    real("aura"),
    real("control"),
    withSkeleton(BASE, "consume_status", "借來換骨架"),
    withSkeleton(BASE, "modifier", "借來換骨架"),
    real("reaction"),
  ];
  cardRow("技能卡（詳細展開）：改了名字的 6 個骨架（組裝列骨架格＝資料的 name_zh）", list);
}

if (SET.includes("status")) {
  const UNK = "brand_new_status";
  const sv = { status_id: UNK, remaining: 2, amount: null, cost_status: false } as unknown as StatusView;
  document.body.append(h("h2", { textContent: "名詞表沒有的狀態：狀態卡（點一下開說明框）" }));
  const host = h("div", { className: "tile-host", id: "unk-badge" });
  document.body.append(host);
  flushSync(() => createRoot(host).render(<StatusBadge status={sv} text={statusLine(sv)} />));
  document.body.append(h("h2", { textContent: "名詞表沒有的狀態：狀態的部件圓片 statusTile（30 px；點一下開說明框）" }));
  const tileHost = h("div", { className: "tile-host", id: "unk-tile" });
  document.body.append(tileHost);
  flushSync(() => createRoot(tileHost).render(<TipGlyph tile={statusTile(UNK)} px={30} />));
  const base = ALL["skill_downpour"]!;
  const icon = base.icon as SkillIconData;
  const card = {
    ...base,
    id: `${base.id}_unknown_status`,
    name_zh: `${base.name_zh}（緩速換成不認得的狀態）`,
    icon: { ...icon, segments: icon.segments.map((s) => ({ ...s, effects: s.effects.map((e) => (e.type === "apply_status" ? { ...e, status: UNK } : e)) })) },
  } as SkillCard;
  cardRow("技能卡：組裝列的狀態圓片（不認得的狀態）", [card]);
}

if (SET.includes("empty")) {
  const nul = withSkeleton(BASE, "", "骨架 null");
  const asNull = { ...nul, skeleton: null, icon: { ...(nul.icon as SkillIconData), segments: (nul.icon as SkillIconData).segments.map((s, i) => (i === 0 ? { ...s, skeleton: null } : s)) } } as unknown as SkillCard;
  cardRow("骨架是空字串（當作沒有骨架）：組裝列不放骨架格、小圖不畫徽章｜對照：null、打擊", [withSkeleton(BASE, "", "骨架空字串"), asNull, { ...BASE, name_zh: `${BASE.name_zh}（打擊，對照）` }]);
}

document.body.dataset.ready = "1";
