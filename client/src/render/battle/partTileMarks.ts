// GB-4b：3×3 巨型頭目（灰燼之心）的部位格標示（A2；美術移植需求 docs/art/GB巨型頭目-移植需求.md 第 3 節、第 7 節第 3、4 條）。
// - 資料：`battle/footprint.giantPartStates`（和點擊判定 `giantAim` 同一份 `PartView.tiles`）→ 每塊的狀態（完好／打不到＋原因／破掉／未露出），
//   掛在 `Highlights.giantMarks`；只在「選打它的動作」時有（滑過、點下去會送出的動作打的是這個頭目、伺服器給了部位選項）。
// - 畫法：`qBossGiant.drawGiantMarks`（九種狀態、800 反向放大、殼縫背刺記號），畫在單位之上（同 `HighlightLayer` 的 marks）；
//   滑過部位格＝那一塊亮起＋身上那個部位亮起（`giantGlowCanvas`，遮罩由畫法直接給）；滑過前殼＝打本體：不另畫⑤，由目標紅框（框整個 3×3）表示。
// - 伺服器原因（引擎 `PART_REASON_ZH`，不改）→ 美術的短字與小圖（`REASON`；移植需求第 9 節）只在這裡用。
// - 背刺記號只畫給近戰攻擊者、`counts_as_behind` 的部位（R4）。
import { Sprite } from "pixi.js";
import type { Action, PartOption, Pos, UnitView } from "../../api/types";
import { giantAim, giantPartStates, isGiant, occupies, type GiantPartState } from "../../battle/footprint";
import { hoverActionAt, partOptionsFor, type TileClickState } from "../../battle/tileClick";
import type { ArtTextures } from "../artTextures";
import { drawGiantMarks, GIANT_ANCHOR_DY, GIANT_BOX, GIANT_MARK_BOX, GIANT_PART_OF, giantGlowCanvas, giantStateFor, REASON, type GiantLook, type GiantPart, type MarkPart, type MarkState, type MarkWhy } from "../qBossGiant";

/** 一隻巨型頭目這一刻的部位格標示（`Highlights.giantMarks`）。 */
export interface GiantMarksDraw {
  unitId: string;
  /** 中心格（標示原點＝中心格中心往南 `GIANT_ANCHOR_DY`）。 */
  pos: Pos;
  parts: Partial<Record<GiantPart, MarkPart>>;
  /** 滑過的部位（亮起）；滑過前殼、破掉、未露出的格＝`body`（打本體，標示不另畫）；沒滑過或打不到＝`null`。 */
  hover: GiantPart | "body" | null;
  /** 攻擊者是近戰（殼縫畫背刺記號）。 */
  melee: boolean;
  /** 殼縫算從背後（`PartView.counts_as_behind`）。 */
  behind: boolean;
}

/** 引擎的原因字（`PART_REASON_ZH`）→ 美術的原因小圖與短字（`REASON`）。不認得的退回「射程不夠」。 */
export const REASON_OF_ENGINE: Readonly<Record<string, MarkWhy>> = {
  只有遠程才打得到: "ranged",
  那一格超出射程: "range",
  要貼著那一格才打得到: "range",
  看不到那一格: "sight",
};

/** 原因字 → 小圖與短字（`null`＝沒有原因）。 */
export function markWhyOf(reason: string | null): MarkWhy | null {
  if (reason === null) return null;
  return REASON_OF_ENGINE[reason] ?? "range";
}

/** 格子標示用的短字（玩法 PM 定稿，移植需求第 9 節）：打不到照 `REASON`，未露出照伺服器的字（巨型頭目已是「呼吸階段才露出」）。 */
export function markReasonZh(s: GiantPartState): string | null {
  if (s.state === "blocked") return REASON[markWhyOf(s.reason) ?? "range"].zh;
  if (s.state === "hidden") return s.reason ?? "這個階段還沒露出";
  return null;
}

const STATE_OF: Readonly<Record<GiantPartState["state"], MarkState>> = { ok: "ok", blocked: "off", broken: "broken", hidden: "hidden" };

/** 部位狀態 → 標示（同一個畫法部位只取第一個；伺服器的 ID 不認得的略過）。 */
export function markPartsOf(states: readonly GiantPartState[]): Partial<Record<GiantPart, MarkPart>> {
  const out: Partial<Record<GiantPart, MarkPart>> = {};
  for (const s of states) {
    const g = GIANT_PART_OF[s.id];
    if (g === undefined || out[g] !== undefined) continue;
    const why = s.state === "blocked" ? markWhyOf(s.reason) : null;
    out[g] = { state: STATE_OF[s.state], ...(why === null ? {} : { why }) };
  }
  return out;
}

const MELEE_REASONS: ReadonlySet<string> = new Set(["只有遠程才打得到", "要貼著那一格才打得到"]);

/** 攻擊者是近戰：伺服器對某個部位回了近戰才有的原因；看不出來時普攻照武器大類。 */
export function meleeOf(options: readonly PartOption[], action: Action, hero: Pick<UnitView, "weapon_class"> | null): boolean {
  if (options.some((o) => o.reason_zh != null && MELEE_REASONS.has(o.reason_zh))) return true;
  return action.type === "attack" && hero?.weapon_class === "melee";
}

/**
 * 這一刻要畫的部位格標示：每隻巨型頭目，點它中心格會送出的動作（`hoverActionAt`：有選取模式照模式，否則普攻）
 * 有伺服器的部位選項才畫（＝選打它的動作）。滑過的那一格照 `giantAim`（和點擊同一套判斷）。
 */
export function giantMarksOf(s: Pick<TileClickState, "view" | "hero" | "canAct" | "copying" | "command" | "mode" | "hurlPick" | "classified" | "partActions">, hover: Pos | null): GiantMarksDraw[] {
  const out: GiantMarksDraw[] = [];
  for (const boss of s.view.units) {
    if (!isGiant(boss) || boss.downed || boss.escaped) continue;
    const action = hoverActionAt(s, boss.pos);
    if (action === null) continue;
    const found = partOptionsFor(s.partActions, action);
    if (found === null || found.target_id !== boss.id) continue;
    const states = giantPartStates(boss, found.options);
    out.push({
      unitId: boss.id,
      pos: { x: boss.pos.x, y: boss.pos.y },
      parts: markPartsOf(states),
      hover: hoverOf(boss, found.options, action, hover),
      melee: meleeOf(found.options, action, s.hero),
      behind: (boss.parts ?? []).some((p) => p.counts_as_behind === true),
    });
  }
  return out;
}

function hoverOf(boss: UnitView, options: readonly PartOption[], action: Action, hover: Pos | null): GiantMarksDraw["hover"] {
  if (hover === null || !occupies(boss, hover)) return null;
  const aim = giantAim(boss, options, action, hover);
  if (aim.kind === "blocked") return null;
  if (aim.kind === "body") return "body";
  return GIANT_PART_OF[aim.part.id] ?? null;
}

/** 標示畫布的快取鍵（同狀態同鍵）。 */
function marksKey(d: GiantMarksDraw, hover: GiantPart | null, S: number, res: number): string {
  const parts = (["vent", "seam", "core"] as const).map((p) => `${p}:${d.parts[p]?.state ?? "ok"}${d.parts[p]?.why ?? ""}`).join(",");
  return `gmarks|${parts}|${hover ?? ""}|${d.melee ? 1 : 0}${d.behind ? 1 : 0}|${S.toFixed(3)}|${res.toFixed(2)}`;
}

/**
 * 標示的節點（世界座標由呼叫端放：`center`＝中心格抬高後的中心）：部位格標示一張、滑過的部位亮起一張（在標示之下、本體之上）。
 * `S`＝地圖縮放（畫面 px／模型 px）、`dpr`＝裝置 px／畫面 px。`look`＝本體這一刻的外觀（亮起的遮罩照它畫）。
 */
export function giantMarkNodes(art: ArtTextures, d: GiantMarksDraw, look: GiantLook | null, center: { x: number; y: number }, S: number, dpr: number): Sprite[] {
  const nodes: Sprite[] = [];
  const res = Math.max(1, S * dpr);
  const hoverPart = d.hover === "body" ? null : d.hover;
  const ax = center.x;
  const ay = center.y + GIANT_ANCHOR_DY;
  // 身上部位亮起（滑過「打得到」的部位格；遮罩由畫法直接給：`giantPartMask`）
  if (hoverPart !== null && look !== null && d.parts[hoverPart]?.state !== "broken") {
    const st = giantStateFor(look, null).st;
    const key = `gglow-part|${hoverPart}|${res.toFixed(2)}|${S.toFixed(3)}|${look.phase}${look.shell}|${Object.keys(look.broken).sort().join("+")}`;
    const tex = art.canvas(key, () => giantGlowCanvas(st, hoverPart, res, S));
    if (tex !== null) {
      const g = new Sprite(tex);
      g.position.set(ax + GIANT_BOX[0], ay + GIANT_BOX[1]);
      g.width = GIANT_BOX[2] - GIANT_BOX[0];
      g.height = GIANT_BOX[3] - GIANT_BOX[1];
      nodes.push(g);
    }
  }
  const B = GIANT_MARK_BOX;
  const tex = art.canvas(marksKey(d, hoverPart, S, res), () => marksCanvas(d, hoverPart, S, dpr, res));
  if (tex !== null) {
    const m = new Sprite(tex);
    m.position.set(ax + B.x, ay + B.y);
    m.width = B.w;
    m.height = B.h;
    nodes.push(m);
  }
  return nodes;
}

function marksCanvas(d: GiantMarksDraw, hover: GiantPart | null, S: number, dpr: number, res: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const B = GIANT_MARK_BOX;
  const c = document.createElement("canvas");
  c.width = Math.ceil(B.w * res);
  c.height = Math.ceil(B.h * res);
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.setTransform(res, 0, 0, res, -B.x * res, -B.y * res);
  drawGiantMarks(ctx, d.parts, { S, res: dpr, hover, melee: d.melee, behind: d.behind });
  return c;
}

