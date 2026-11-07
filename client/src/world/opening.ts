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
 * RT-5c（小修 10）：用完整名字比對（`mentionsName`），「婆婆」不會配到「找渡婆婆」裡的「渡婆婆」。
 * 之後在 `GuideView` 加 `npc` 欄位就不用比對名字（技術債，見 PhaseRT-5c報告）。
 */
export function mainQuestNpc(guide: WorldGuide | null | undefined, field: FieldView | null | undefined): string | null {
  if (guide == null || (guide.opening ?? []).length > 0 || guide.text_zh === "") return null;
  const npcs = field?.npcs ?? [];
  const names = [...npcs.map((n) => n.name_zh), ...(field?.situation_objects ?? []).filter((o) => o.figure != null).map((o) => o.name_zh)].filter((s) => s !== "");
  const npc = npcs.find((n) => n.alert === "quest" && n.name_zh !== "" && mentionsName(guide.text_zh, n.name_zh, names));
  return npc?.id ?? null;
}

/** 名字前面可以接的字（指引句的動詞、介詞：「找渡婆婆」「向葛蘭報到」）；其他的字（例「渡」）接在前面＝別人的名字的一部分。 */
const NAME_BEFORE = new Set([..."找問見向跟和與給到去請把被讓叫"]);
/** 名字後面可以接的字（「找渡婆婆說話」「渡婆婆的委託」）。 */
const NAME_AFTER = new Set([..."說談聊問報的那這拿領交"]);

function isLetter(ch: string | undefined): boolean {
  return ch !== undefined && /\p{L}/u.test(ch);
}

/**
 * 指引句 `text` 有沒有用「完整名字」點名 `name`（RT-5c 小修 10）：中文沒有空白分詞，所以名字的前後必須是句子頭尾、
 * 標點或空白，或是指引常用的動詞、助詞（`NAME_BEFORE`／`NAME_AFTER`）；而且這一段不能落在同一句裡另一個更長的名字
 *（`others`，例：地圖上的人名）裡面。「婆婆」不會配到「找渡婆婆」（前面是「渡」，而且落在「渡婆婆」裡）。
 */
export function mentionsName(text: string, name: string, others: readonly string[] = []): boolean {
  if (name === "") return false;
  const longer = [...new Set(others)].filter((o) => o.length > name.length && o.includes(name)).sort();
  for (let i = text.indexOf(name); i >= 0; i = text.indexOf(name, i + 1)) {
    const end = i + name.length;
    const before = i === 0 ? undefined : text[i - 1];
    const after = end >= text.length ? undefined : text[end];
    if (isLetter(before) && !NAME_BEFORE.has(before as string)) continue;
    if (isLetter(after) && !NAME_AFTER.has(after as string)) continue;
    const covered = longer.some((o) => {
      for (let j = text.indexOf(o); j >= 0; j = text.indexOf(o, j + 1)) if (j <= i && j + o.length >= end) return true;
      return false;
    });
    if (!covered) return true;
  }
  return false;
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
 * RT-5c（必修 4）：夾到邊上時避開其他人物的頭頂（`opts.others`），沿著夾住的那條邊挪開。
 * RT-6b（RT-6 檢查決定 1）：有 `opts.columns`（左欄、右欄的 HUD 塊）時，上緣只在那些塊的水平範圍內才用它們的下緣，
 * 畫面中間夾在 `opts.mapTop`（地圖可見範圍的上緣）往下一個「！」的高度。
 * RT-6b（決定 2）：有 `opts.units`（每個人物的範圍，`hudAvoid.unitRect`）時，「！」和每個人的頭頂、腳下、朝向三角形
 * 至少隔 `opts.pad`（半格），太近就沿邊挪。
 */
export function guideAnchor(
  at: { left: number; top: number },
  box: ViewBox | null,
  visible: ViewBox | null = null,
  opts: GuideAvoid = {},
): { left: number; top: number; side: BubbleSide; edge: string } {
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
  if (left > box.right - GUIDE_EDGE_X) {
    left = box.right - GUIDE_EDGE_X;
    ew = "e";
  } else if (left < box.left + GUIDE_EDGE_X) {
    left = box.left + GUIDE_EDGE_X;
    ew = "w";
  }
  // 泡泡往畫面中間那一邊放（RT-5b：夾在左半邊時往左放會壓到左上的隊友卡、被畫面左緣切掉）
  const sideAt = (l: number): BubbleSide => (l - GUIDE_GAP - GUIDE_BUBBLE_W < box.left || l < (box.left + box.right) / 2 ? "e" : "w");
  const topAt = (l: number): number => guideTopLimit(l, box, opts, sideAt(l)) + GUIDE_TOP;
  if (top < topAt(left)) {
    top = topAt(left);
    ns = "n";
  } else if (top > box.bottom - 8) {
    top = box.bottom - 8;
    ns = "s";
  }
  const edge = `${ns}${ew}`;
  // RT-5c（必修 4）：夾到畫面邊的「！」與泡泡不能落在別人頭上（看起來像那個人的主線）：沿著夾住的那條邊挪開
  const moved = avoidHeads({ left, top }, box, opts, ns === "n" ? "n" : ns !== "" ? "s" : "y", sideAt, topAt);
  return { ...moved, side: sideAt(moved.left), edge };
}

/** `guideAnchor` 的選項（RT-5c）：`others`＝畫面上其他人物的頭頂（`headAnchor`，畫布座標）；`bubble`＝有沒有整句泡泡（收起來時只看「！」）。 */
export interface GuideAvoid {
  others?: readonly { left: number; top: number }[];
  bubble?: boolean;
  /** RT-6b：其他人物的範圍（畫布座標，`hudAvoid.unitRect`：頭頂的「！」到腳下的徽章與朝向三角形）；有就取代 `others`。 */
  units?: readonly Box[];
  /** RT-6b：「！」和 `units` 至少隔多遠（半格＝24×縮放）。 */
  pad?: number;
  /** RT-6b：左欄、右欄的 HUD 塊（畫布座標）；夾到上緣時只在它們的水平範圍內才避開（省略＝整條上緣用 `box.top`）。 */
  columns?: readonly Box[];
  /** RT-6b：地圖可見範圍的上緣（畫布座標）；有 `columns` 時畫面中間夾在這裡往下一個「！」的高度。 */
  mapTop?: number;
}

/**
 * 夾到上緣時「！」與泡泡最高可以到哪（畫布座標，「！」的上緣）：`columns` 裡和「！」（有泡泡時連同泡泡）水平重疊的塊的下緣，
 * 都沒有就用 `mapTop`；沒有 `columns`＝`box.top`（RT-5 的舊規則）。
 */
export function guideTopLimit(left: number, box: ViewBox, opts: GuideAvoid, side: BubbleSide = "w"): number {
  if (opts.columns === undefined) return box.top;
  const probe = { left, top: 0 };
  const spans: Box[] = [guideAlertBox(probe)];
  if (opts.bubble ?? true) spans.push(guideBubbleBox(probe, side));
  let lim = opts.mapTop ?? box.top;
  for (const c of opts.columns) {
    if (c.width <= 0 || c.height <= 0) continue;
    if (spans.some((s) => s.left < c.left + c.width && c.left < s.left + s.width)) lim = Math.max(lim, c.top + c.height);
  }
  return lim;
}

/** 夾邊時沿著邊挪的步距與最遠距離。 */
const AVOID_STEP = 8;
const AVOID_MAX = 240;

type Box = { left: number; top: number; width: number; height: number };

function overlap(a: Box, b: Box): boolean {
  return a.left < b.left + b.width && b.left < a.left + a.width && a.top < b.top + b.height && b.top < a.top + a.height;
}

/** 「！」（含夾邊時旁邊的箭頭）佔的範圍：圖示列的下緣在頭頂、水平置中（CSS `.field-head`）。 */
export function guideAlertBox(at: { left: number; top: number }): Box {
  return { left: at.left - 24, top: at.top - 30, width: 48, height: 32 };
}

/** 整句泡泡佔的範圍（`e`／`w`：`.field-bubble.guide`，在圖示列旁邊、上緣比圖示列高 6px）。 */
export function guideBubbleBox(at: { left: number; top: number }, side: BubbleSide): Box {
  const top = at.top - 30;
  if (side === "e") return { left: at.left + 12 + GUIDE_GAP, top, width: GUIDE_BUBBLE_W, height: GUIDE_BUBBLE_H + 10 };
  if (side === "w") return { left: at.left - 12 - GUIDE_GAP - GUIDE_BUBBLE_W, top, width: GUIDE_BUBBLE_W, height: GUIDE_BUBBLE_H + 10 };
  return { left: at.left + GUIDE_NW_RIGHT - GUIDE_BUBBLE_W, top: at.top - GUIDE_TOP - GUIDE_BUBBLE_H, width: GUIDE_BUBBLE_W, height: GUIDE_BUBBLE_H };
}

/** 別人的頭（含他自己頭上的「！」）：頭頂往上 26、往下 22，左右各 20。 */
export function otherHeadBox(h: { left: number; top: number }): Box {
  return { left: h.left - 20, top: h.top - 26, width: 40, height: 48 };
}

/** 往外擴 `pad`。 */
export function padBox(b: Box, pad: number): Box {
  return { left: b.left - pad, top: b.top - pad, width: b.width + pad * 2, height: b.height + pad * 2 };
}

/**
 * 沿著夾住的邊挪開：`along`＝`n`（上緣：左右挪，每個位置重算上緣）、`s`（下緣：左右挪）、`y`（左右邊：上下挪）。
 * 「！」要避開的是 `units` 往外擴 `pad`（RT-6b）或 `others` 的頭（RT-5c）；泡泡避開人本身（不擴）。
 */
function avoidHeads(
  at: { left: number; top: number },
  box: ViewBox,
  opts: GuideAvoid,
  along: "n" | "s" | "y",
  sideAt: (l: number) => BubbleSide,
  topAt: (l: number) => number,
): { left: number; top: number } {
  const units = opts.units;
  const near = units !== undefined ? units.map((u) => padBox(u, opts.pad ?? 0)) : (opts.others ?? []).map(otherHeadBox);
  const bodies = units !== undefined ? units : near;
  if (near.length === 0) return at;
  const clear = (p: { left: number; top: number }, withBubble: boolean): boolean => {
    if (near.some((h) => overlap(guideAlertBox(p), h))) return false;
    return !withBubble || !bodies.some((h) => overlap(guideBubbleBox(p, sideAt(p.left)), h));
  };
  const wantBubble = opts.bubble ?? true;
  if (clear(at, wantBubble)) return at;
  const alongX = along !== "y";
  const [lo, hi] = alongX ? [box.left + GUIDE_EDGE_X, box.right - GUIDE_EDGE_X] : [topAt(at.left), box.bottom - 8];
  const cur = alongX ? at.left : at.top;
  // RT-6b：有 `units` 時整條邊都可以試（半格的距離比頭的範圍大，240 內可能找不到）
  const far = units !== undefined ? Math.max(cur - lo, hi - cur) : AVOID_MAX;
  const spots: { left: number; top: number }[] = [];
  for (let d = AVOID_STEP; d <= far; d += AVOID_STEP)
    for (const v of [cur + d, cur - d]) {
      if (v < lo || v > hi) continue;
      if (!alongX) spots.push({ left: at.left, top: v });
      else spots.push({ left: v, top: along === "n" ? topAt(v) : at.top });
    }
  // 先找「！」和泡泡都不壓到人的位置；找不到就至少讓「！」不落在別人頭上
  return spots.find((p) => clear(p, wantBubble)) ?? spots.find((p) => clear(p, false)) ?? at;
}

/** 畫面外的方向 → 箭頭（文字版，說明卡與無障礙用；畫面上畫的是 `EDGE_ANGLE` 轉的 SVG 箭頭）。 */
export const EDGE_ARROW: Readonly<Record<string, string>> = { n: "↑", s: "↓", e: "→", w: "←", ne: "↗", nw: "↖", se: "↘", sw: "↙" };

/** 畫面外的方向 → 箭頭的角度（度，順時針；0＝朝上）。RT-5c 必修 2：箭頭改畫 SVG（筆畫 3.5px、外面 2px 深色描邊）。 */
export const EDGE_ANGLE: Readonly<Record<string, number>> = { n: 0, ne: 45, e: 90, se: 135, s: 180, sw: 225, w: 270, nw: 315 };

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
