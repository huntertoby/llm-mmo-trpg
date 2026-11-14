// 頭目部位破壞的正式演出（PB-1e；美術移植需求 docs/art/頭目部位-移植需求.md 3.6、紀錄 docs/art/頭目部位.md 3.6、12.2）。
// 5 格約 0.6 秒、不擋回合（效果自己跑，播放不等它）：
//   1 命中（80 ms）：部位整塊白閃 0.9＋白黃小星；2 裂開（80 ms）：部位上亮金白裂紋＋三片碎屑；
//   3 斷開（160 ms）：碎塊飛出（剪下的白毛／斷下的劍尖）、大星＋光環（氣海：淡青氣爆＋三團霧）、部位上方冒「破」；
//   4 落地（160 ms）：腳邊揚灰、「破」淡到 55%、HP 條下那一條換成「×」；5 定格＝破壞後的樣子（伺服器的 `view`）。
// 人物那一部分（白閃、裂紋、斷了但地上還沒有掉落物）由繪製器蓋過（`ResultHost.partFx` → `UnitLayer.setPartFx`），
// 身上以外的特效畫在一張跟著頭目位置的貼圖上（`bossPartArt.breakFxCanvas`，每格一張）。
import { Sprite } from "pixi.js";
import type { VfxSpecial } from "../battle/vfx";
import { BREAK_BOX, BREAK_MS, breakFrameAt, breakFxCanvas, breakFxOf, partCenter, popScale, STRIP_BASE_SCALE, weaponToFeet } from "./bossPartArt";
import type { ResultHost } from "./resultEffects";
import { dollKey } from "./appearance";
import { arrowPolyOf, bossHudDy, dollPx, FEET, hpBoxOf, isGiantUnit, southArrowMoved, specOfUnit } from "./unitSprite";
import { giantBreakFxOf, STRIP_X_INK, STRIP_X_LINE, stripLayout } from "../battle/partStrip";
import type { UnitDraw } from "../battle/drawModel";
import { isCompactRow } from "./rowLayout";
import { GIANT_ANCHOR_DY, GIANT_FX_BOX, GIANT_PART_OF, giantBreakFx, giantPopScale, type GiantState } from "./qBossGiant";
import type { Effect } from "./vfxEffects";

/** 一次部位破壞的演出（`startMs`＝效果時鐘上的命中點，`scale`＝播放速度的時間倍率）。 */
export function partBreakEffect(host: ResultHost, s: VfxSpecial, startMs: number, scale: number): Effect | null {
  const unitId = s.unitId;
  const part = s.partId;
  const draw0 = unitId === null ? undefined : host.draw(unitId);
  if (unitId === null || part === undefined || draw0 === undefined || draw0.parts === undefined) return null;
  if (isGiantUnit(draw0)) return giantBreakEffect(host, s, unitId, part, draw0.bossPhase ?? 1, startMs, scale);
  // 部位中心、手持物的位置照「還沒破」的站姿算（伺服器的 view 可能已經是破了的樣子）
  const intact = { ...draw0, partFx: { part, k: "flash" as const } };
  const spec = specOfUnit(intact);
  const k = dollPx(intact);
  const facing = draw0.facing;
  const center = partCenter(spec, facing, part, k) ?? { x: 0, y: -20 };
  const weapon = weaponToFeet(spec, facing, part, k);
  const res = host.art.figureRes(1);
  const popK = popScale(host.boardScale?.() ?? 1); // PB-1f：「破」字在畫面上 ≥ 12 px
  const owner = host.art.uniqueOwner(`pbreak:${unitId}`);
  const node = new Sprite();
  node.visible = false;
  let frame = -1;
  const ms = Math.max(1, Math.round(BREAK_MS * scale));
  const show = (f: number): void => {
    host.partFx?.(unitId, breakFxOf(part, f));
    if (f >= 4) {
      node.visible = false;
      host.art.holdFor(owner, null);
      return;
    }
    const key = `pbfx|${res}|${part}|${f}|${dollKey(spec, facing, false)}|${k.toFixed(3)}|${popK.toFixed(3)}`;
    const tex = host.art.canvas(key, () => breakFxCanvas({ part, frame: f, center, weapon, west: facing === "west", popK }, res));
    if (tex === null) {
      node.visible = false;
      return;
    }
    host.art.holdFor(owner, tex);
    node.texture = tex;
    node.width = BREAK_BOX.w;
    node.height = BREAK_BOX.h;
    node.visible = true;
  };
  return {
    node,
    startMs,
    endMs: startMs + ms,
    motion: "fx",
    update: (t) => {
      const sprite = host.sprite(unitId);
      if (sprite !== null) node.position.set(sprite.x + BREAK_BOX.x, sprite.y + FEET + BREAK_BOX.y);
      const f = breakFrameAt(t * BREAK_MS);
      if (f !== frame) {
        frame = f;
        show(f);
      }
    },
    end: () => {
      if (frame < 4) host.partFx?.(unitId, null);
      host.art.holdFor(owner, null);
      frame = 4;
    },
  };
}

/** 朝向三角形的描邊寬度（同 `unitSprite` 的 `ARROW_STROKE`）。 */
const ARROW_STROKE_W = 1;
/** GB-4d：煙頂離 HUD 下緣至少幾個畫面 px（美術 GB-4c 待決 6）。 */
export const SMOKE_HUD_GAP_PX = 2;

/**
 * GB-4d：巨型頭目頭頂 HUD 的下緣（世界 px、相對中心格中心）：HP 條、部位小格（含紅「×」，800 寬照縮放加高）、
 * 朝南三角形（跟著部位條下緣往下挪）三者最低的那一點，再加 `bossHudDy`。沒有 HP 條 → `null`。
 */
export function giantHudLowY(d: UnitDraw, boardScale: number): number | null {
  const hp = hpBoxOf(d);
  if (hp === null) return null;
  const n = d.parts?.length ?? 0;
  let low = hp.b;
  let shift = 0;
  if (n > 0) {
    const L = stripLayout(n, boardScale);
    const xLow = L.top + L.h / 2 + L.xs / 2 + ((STRIP_X_LINE + STRIP_X_INK) * L.k) / 2;
    low = Math.max(L.bottom, xLow);
    if (southArrowMoved(d)) shift = L.bottom - stripLayout(n, STRIP_BASE_SCALE).bottom;
  }
  // 三角形照不縮的算（HUD 改掛最上層時只會縮小，下緣更高）
  const arrow = arrowPolyOf({ ...d, partHudUp: false });
  if (arrow !== null) low = Math.max(low, ...arrow.filter((_, i) => i % 2 === 1).map((y) => y + ARROW_STROKE_W / 2 + shift));
  return low + bossHudDy(d);
}

/**
 * GB-4d（美術 GB-4c 待決 6）：噴口黑煙的煙頂上限（模型 px、相對錨點）＝HUD 下緣往下 `SMOKE_HUD_GAP_PX` 畫面 px。
 * 只在 800 寬（地圖縮放 ≤ `COMPACT_ROW_MAX_SCALE`）壓；1600 照舊（美術裁定）→ `undefined`。
 */
export function giantSmokeCeil(d: UnitDraw, boardScale: number): number | undefined {
  if (!isCompactRow(boardScale)) return undefined;
  const low = giantHudLowY(d, boardScale);
  return low === null ? undefined : low - GIANT_ANCHOR_DY + SMOKE_HUD_GAP_PX / boardScale;
}

/**
 * GB-4b：3×3 巨型頭目（灰燼之心）的破壞演出（美術移植需求第 5 節；5 格約 0.6 秒、不擋回合，時間表同段 1 `BREAK_FRAMES_MS`）。
 * 本體那一部分（第 1 格部位白閃、裂紋、熔殼殼片彈起飛走、冷掉、核心一縮）由繪製器照這一格重畫（`ResultHost.partFx` →
 * `UnitLayer.setPartFx`，`PartFx.frame`；`qBossGiant.giantLookOf`）；本體以外的特效（星、光環、黑煙、火星、白汽、落灰、「破」字）
 * 畫在一張跟著頭目位置的貼圖上（`giantBreakFx`），放在特效層（所有單位與部位格標示之上）。第 5 格＝伺服器給的破壞後外觀（`broken`）。
 */
function giantBreakEffect(host: ResultHost, s: VfxSpecial, unitId: string, part: string, phase: number, startMs: number, scale: number): Effect | null {
  const gpart = GIANT_PART_OF[part];
  if (gpart === undefined) return null;
  const side: -1 | 1 = s.side === -1 ? -1 : 1;
  const shed = s.shed === true;
  const res = host.art.figureRes(1);
  const board = host.boardScale?.() ?? 1;
  const draw = host.draw(unitId);
  const ceil = draw === undefined ? undefined : giantSmokeCeil(draw, board);
  const owner = host.art.uniqueOwner(`gbreak:${unitId}`);
  const node = new Sprite();
  node.visible = false;
  let frame = -1;
  const ms = Math.max(1, Math.round(BREAK_MS * scale));
  const B = GIANT_FX_BOX;
  const show = (f: number): void => {
    host.partFx?.(unitId, giantBreakFxOf(part, f, side, shed));
    if (f >= 4) {
      node.visible = false;
      host.art.holdFor(owner, null);
      return;
    }
    const key = `gbfx|${res}|${gpart}|${f}|${side}|${phase}|${giantPopScale(board).toFixed(3)}${ceil === undefined ? "" : `|c${ceil.toFixed(2)}`}`;
    const tex = host.art.canvas(key, () => giantBreakCanvas({ phase, fx: { part: gpart, k: f, side } }, res, board, ceil));
    if (tex === null) {
      node.visible = false;
      return;
    }
    host.art.holdFor(owner, tex);
    node.texture = tex;
    node.width = B.w;
    node.height = B.h;
    node.visible = true;
  };
  return {
    node,
    startMs,
    endMs: startMs + ms,
    motion: "fx",
    update: (t) => {
      const sprite = host.sprite(unitId);
      if (sprite !== null) node.position.set(sprite.x + B.x, sprite.y + GIANT_ANCHOR_DY + B.y);
      const f = breakFrameAt(t * BREAK_MS);
      if (f !== frame) {
        frame = f;
        show(f);
      }
    },
    end: () => {
      if (frame < 4) host.partFx?.(unitId, null);
      host.art.holdFor(owner, null);
      frame = 4;
    },
  };
}

/** 破壞演出特效的一格（`GIANT_FX_BOX`、原點＝錨點；`res`＝每模型 px 幾個 canvas px；`smokeCeil`＝`giantSmokeCeil`）。沒有 DOM 時 `null`。 */
export function giantBreakCanvas(st: GiantState, res: number, boardScale: number, smokeCeil?: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const B = GIANT_FX_BOX;
  const c = document.createElement("canvas");
  c.width = Math.ceil(B.w * res);
  c.height = Math.ceil(B.h * res);
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.setTransform(res, 0, 0, res, -B.x * res, -B.y * res);
  giantBreakFx(ctx, st, boardScale, smokeCeil);
  return c;
}
