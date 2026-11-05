// 主城開場四格（Phase RT-5；09 9.6.9 #125、21 21.5；docs/art/區域主題移植需求.md 第 5 節、樣張 capital-opening.png）的純函式。
// 規則與文案全部來自伺服器與內容檔：開場的句子是 `WorldView.guide.opening`（content/world/newcomer.yaml），
// 「免費」是 `AtlasRegionView.free`，石碑小牌照 `atlas.regions` 的開放狀態；這裡只決定哪一句放哪裡、怎麼畫。
// ① 醒來：說書人那幾句（說話的人不是主城上站著的人）放進 `awaken` 插圖卡；
// ② 守印人：說話的人＝主城上站著的人（情境物件的 `figure`，名稱相同）那幾句，變成他頭上的對話泡泡＋「！」；
// ③ 大世界圖：五座島依序從雲裡浮起（只播一次：前端記在本機；減少動態時不播）；
// ④ 抵達霧渡鎮：主題換雲嶺（RT-1，照 `field.region`）、渡婆婆頭上的「！」是伺服器原本的任務標記。
import type { AtlasView, FieldView, WorldGuide, WorldOpeningLine } from "../api/types";
import { resolveDoll, type DollSpec } from "../render/appearance";

type FieldLook = NonNullable<FieldView["hero"]>;

/** 主角的紙娃娃規格（同實地地圖的畫法：範本、`doll_look`、武器、種族外觀、裝備；沒有外觀時用我方預設）。 */
export function heroDoll(look: FieldLook | null | undefined): DollSpec {
  return resolveDoll({
    template: look?.template_id ?? "hero",
    dollLook: look?.doll_look ?? null,
    team: "ally",
    summon: false,
    weaponId: look?.weapon_id ?? null,
    weaponClass: look?.weapon_class ?? null,
    raceLook: (look?.race_look ?? null) as Readonly<Record<string, unknown>> | null,
    equipment: (look?.equipment ?? []).map((e) => ({ slot: e.slot, appearance: e.appearance ?? null })),
  });
}

/** 地圖上站著的人（情境物件的 `figure`）：名稱 → 物件。 */
function figuresByName(field: FieldView | null | undefined): Map<string, { id: string; x: number; y: number }> {
  const out = new Map<string, { id: string; x: number; y: number }>();
  for (const o of field?.situation_objects ?? []) if (o.figure != null && !out.has(o.name_zh)) out.set(o.name_zh, { id: o.id, x: o.x, y: o.y });
  return out;
}

export interface OpeningSplit {
  /** ① 插圖卡上的句子（說書人）。 */
  narrator: WorldOpeningLine[];
  /** ② 地圖上的人說的句子：物件 ID → 句子（照順序接起來）。 */
  spoken: Map<string, { name: string; text: string; x: number; y: number }>;
}

/**
 * 開場的句子分兩邊：說話的人＝這張地圖上站著的人（名稱相同的 `figure` 物件）→ 那人頭上的泡泡；其他（說書人、
 * 地圖上沒有的人）→ 插圖卡。地圖上沒有任何人時全部放在插圖卡（照舊不會漏句子）。
 */
export function splitOpening(lines: readonly WorldOpeningLine[], field: FieldView | null | undefined): OpeningSplit {
  const figures = figuresByName(field);
  const narrator: WorldOpeningLine[] = [];
  const spoken = new Map<string, { name: string; text: string; x: number; y: number }>();
  for (const line of lines) {
    const who = figures.get(line.speaker_zh);
    if (who === undefined) {
      narrator.push(line);
      continue;
    }
    const cur = spoken.get(who.id);
    spoken.set(who.id, { name: line.speaker_zh, text: cur === undefined ? line.text_zh : `${cur.text}${line.text_zh}`, x: who.x, y: who.y });
  }
  return { narrator, spoken };
}

/** 開場的階段：`awaken`＝①插圖卡還沒按「站起來」；`guide`＝②守印人頭上「！」＋泡泡；`none`＝沒有開場（到過霧渡鎮了）。 */
export type OpeningStage = "awaken" | "guide" | "none";

/** 現在在哪一段：伺服器有給開場（還沒到過新手區的小鎮）→ 沒看過＝①、看過＝②；沒給＝`none`。 */
export function openingStage(guide: WorldGuide | null | undefined, seen: boolean): OpeningStage {
  if (guide == null || (guide.opening ?? []).length === 0) return "none";
  return seen ? "guide" : "awaken";
}

/**
 * 主線（新手任務）給任務的人（RT-5b 小修 10）：到了新手區的小鎮、還沒接新手任務時，伺服器的指引（`guide.text_zh`，
 * 內容檔的 `guide_town_zh`，例「找渡婆婆」）點名的那位、頭上有任務「！」的 NPC。他的「！」畫得比支線突出。
 * 開場（主城、`guide.opening` 有句子）或沒有指引＝`null`。同名的取地圖上第一位。
 */
export function mainQuestNpc(guide: WorldGuide | null | undefined, field: FieldView | null | undefined): string | null {
  if (guide == null || (guide.opening ?? []).length > 0 || guide.text_zh === "") return null;
  const npc = (field?.npcs ?? []).find((n) => n.alert === "quest" && n.name_zh !== "" && guide.text_zh.includes(n.name_zh));
  return npc?.id ?? null;
}

/** 開場指示的整句泡泡留多久才收成只剩「！」（RT-5b 必修 6，美術 PM：約 8 秒）。 */
export const GUIDE_BUBBLE_MS = 8000;

/** 畫面上看得到的範圍（畫布座標、CSS 像素；鏡頭的可視區扣掉 HUD 佔掉的四邊）。 */
export interface ViewBox {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

/**
 * 泡泡在人的哪一邊：`nw`＝頭頂往左上（RT-5b：守印人站到傳送陣旁，上面放得下時用這個，不蓋到東邊的主角與晶柱）、
 * `w`＝左邊、和「！」同高（上面放不下時）、`e`＝右邊（左邊也放不下時）。
 */
export type BubbleSide = "nw" | "w" | "e";

/** 開場指示泡泡的寬度（CSS `.field-bubble.guide`）與泡泡到人的間距。 */
export const GUIDE_BUBBLE_W = 210;
const GUIDE_GAP = 12;
/** 「！」與泡泡上緣要留的高度（頭頂往上）。 */
const GUIDE_TOP = 30;
/** 開場指示泡泡的高度（名字一行＋整句約三行，CSS `.field-bubble.guide`）。 */
export const GUIDE_BUBBLE_H = 80;
/** `nw` 泡泡的右緣超過人的中心幾像素（尾巴指著「！」）。 */
const GUIDE_NW_RIGHT = 24;
/** 夾到畫面左右邊時離邊多遠（RT-5b：收起來的「！」旁邊多一個箭頭，12 會被畫面邊切掉一半）。 */
const GUIDE_EDGE_X = 26;

/**
 * 開場說話的人不在畫面裡（小視窗：守印人站在北邊）時，把「！」和泡泡夾到畫面邊上，加一個往那人方向的箭頭（`edge`），
 * 不會漏看第一個指示；在畫面裡就照原位。`at`＝頭頂位置（`headAnchor`）；`box`＝夾的範圍（扣掉 HUD 的安全區）；
 * `visible`＝整個可視區（判斷人在不在畫面裡；省略＝用 `box`）。沒有鏡頭（`box` 為 `null`）＝照原位。
 */
export function guideAnchor(at: { left: number; top: number }, box: ViewBox | null, visible: ViewBox | null = null): { left: number; top: number; side: BubbleSide; edge: string } {
  if (box === null) return { ...at, side: "w", edge: "" };
  // 人在畫面裡（`visible`＝整個可視區，含 HUD 蓋住的邊）就照原位，只決定泡泡放哪邊
  if (visible !== null && at.top - GUIDE_TOP >= visible.top && at.top <= visible.bottom && at.left >= visible.left && at.left <= visible.right) {
    const roomAbove = at.top - GUIDE_TOP - GUIDE_BUBBLE_H >= visible.top && at.left + GUIDE_NW_RIGHT - GUIDE_BUBBLE_W >= visible.left;
    if (roomAbove) return { ...at, side: "nw", edge: "" };
    return { ...at, side: at.left - GUIDE_GAP - GUIDE_BUBBLE_W < visible.left ? "e" : "w", edge: "" };
  }
  let { left, top } = at;
  let ns = "";
  let ew = "";
  if (top - GUIDE_TOP < box.top) {
    top = box.top + GUIDE_TOP;
    ns = "n";
  } else if (top > box.bottom - 8) {
    top = box.bottom - 8;
    ns = "s";
  }
  if (left > box.right - GUIDE_EDGE_X) {
    left = box.right - GUIDE_EDGE_X;
    ew = "e";
  } else if (left < box.left + GUIDE_EDGE_X) {
    left = box.left + GUIDE_EDGE_X;
    ew = "w";
  }
  // 泡泡往畫面中間那一邊放（RT-5b：夾在左半邊時往左放會壓到左上的隊友卡、被畫面左緣切掉）
  const side: BubbleSide = left - GUIDE_GAP - GUIDE_BUBBLE_W < box.left || left < (box.left + box.right) / 2 ? "e" : "w";
  return { left, top, side, edge: `${ns}${ew}` };
}

/** 畫面外的方向 → 箭頭。 */
export const EDGE_ARROW: Readonly<Record<string, string>> = { n: "↑", s: "↓", e: "→", w: "←", ne: "↗", nw: "↖", se: "↘", sw: "↙" };

// ---------------- ② 橋頭石碑的小牌 ----------------

export type SteleStatus = "open" | "locked" | "later";

export interface SteleTag {
  /** 情境物件 ID（`stele_<區域>`）。 */
  id: string;
  region: string;
  x: number;
  y: number;
  /** 區名（大世界圖的 `name_zh`）。 */
  name: string;
  status: SteleStatus;
  /** 第二行：已開放＝空字串；荒原這類有地點圖但還沒開放＝「尚未開放」；這一季沒有地點圖＝「之後的賽季」。 */
  sub: string;
}

/** 小牌第二行的字（UI 標籤；區名與開放狀態照伺服器）。 */
export const STELE_SUB_ZH: Readonly<Record<SteleStatus, string>> = { open: "", locked: "尚未開放", later: "之後的賽季" };

/** 每座橋頭石碑（`stele_region` 有值的物件）的小牌：照大世界圖的開放狀態（`atlas.regions`，不新增欄位）。大世界圖沒有那一區＝不畫。 */
export function steleTags(field: FieldView | null | undefined, atlas: AtlasView | null | undefined): SteleTag[] {
  const regions = new Map((atlas?.regions ?? []).map((r) => [r.region, r]));
  const out: SteleTag[] = [];
  for (const o of field?.situation_objects ?? []) {
    const region = o.stele_region;
    if (region == null) continue;
    const r = regions.get(region);
    if (r === undefined) continue;
    out.push({ id: o.id, region, x: o.x, y: o.y, name: r.name_zh, status: r.status, sub: STELE_SUB_ZH[r.status] });
  }
  return out.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

// ---------------- ③ 大世界圖：五座島依序浮起 ----------------

// 畫法（每座 0.3 秒、依 `regions.yaml` 的順序）在 render/worldMapPainter.ts 的 `riseAt`；這裡只管「播過了沒」。

/** 本機記住「這個角色的大世界圖已經播過浮起」的鍵。 */
export const RISE_KEY = "trpg.atlasRise";

function readRisen(): string[] {
  try {
    const raw = window.localStorage.getItem(RISE_KEY);
    const v: unknown = raw === null ? [] : JSON.parse(raw);
    return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

/** 這個角色播過了沒（讀不到本機儲存＝沒播過）。 */
export function atlasRisen(charId: string): boolean {
  return readRisen().includes(charId);
}

/** 記下播過了（寫不進去就算了：下次再播一次，不影響規則）。 */
export function markAtlasRisen(charId: string): void {
  const list = readRisen();
  if (list.includes(charId)) return;
  try {
    window.localStorage.setItem(RISE_KEY, JSON.stringify([...list, charId].slice(-50)));
  } catch {
    // 私密視窗、禁用儲存
  }
}

/** 打開大世界圖時要不要播浮起：沒播過、沒有減少動態。播了就記下（第二次打開不播）；減少動態時不記（之後關掉減少動態再看到一次）。 */
export function takeAtlasRise(charId: string | null, reduced: boolean): boolean {
  if (charId === null || reduced || atlasRisen(charId)) return false;
  markAtlasRisen(charId);
  return true;
}
