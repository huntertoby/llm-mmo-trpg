// 浮動字與行動連線（R1e 自 `BattleRenderer.ts` 拆出，純搬移）：同一格錯開往上堆（`FloatStack`）、夾在戰場內、狀態光環。
import { Container, Graphics, Sprite, Texture, type Text } from "pixi.js";
import type { Pos } from "../../api/types";
import type { FeedbackItem, FloatTone } from "../../battle/feedback";
import { TILE_SIZE } from "../../battle/geometry";
import type { Effect } from "../vfxEffects";
import { label } from "../labels";
import { HUMAN_TOP_Y, unitMarkTopY } from "../unitSprite";
import { BIG_REST, floatBaseY, floatFit, floatFontSize, floatFrame, FLOAT_HEAD_GAP, FLOAT_RISE_MAX } from "../uiAnim";
import { capRise, clampFloatCenter, FLOAT_EDGE_PAD, floatTopShift, groupRise, visibleFieldBounds, type FloatBounds } from "../floatStack";
import { RgMarkLayer } from "./rgMarkLayer";
import { drawGlance } from "../rgArt";
import { glanceDir, glanceY, RG_MIN, RG_TIMING } from "../../battle/rgMarks";
import { minMarkScale } from "../minMark";
import { devAnimFactor } from "../../battle/playback";

const T = TILE_SIZE;
const FLOAT_COLORS: Readonly<Record<FloatTone, number>> = {
  damage: 0xff4d4d,
  heal: 0x4cd964,
  shield: 0x9fd8ff,
  text: 0xffffff,
  bad: 0xff9f43,
  good: 0xffe066,
};
const LINE_COLOR = 0xfff1a8;
const STATUS_COLOR = 0xd9a0ff;
/** 量好大小、還沒放位置的浮動字（6F-6）。 */
interface FloatLabel {
  t: Text;
  big: boolean;
  isStatus: boolean;
  fit: number;
  /** 停住時的高度、寬度（已乘縮放）。 */
  restH: number;
  restW: number;
  /** 這個字自己最多往上飄多少。 */
  riseMax: number;
}

/** 浮動字在同一格那一組裡的位置（6F-6 `FloatStack`）。 */
interface FloatSpot {
  offset: number;
  /** 這一組第一個字停住時的高度（位移從它貼頭頂時的中心算，6F-10b）。 */
  firstH: number;
  /** 這一格整疊往下推的量（實際時間；頭頂放不下時，`FloatStack.placeGroup`）。 */
  shiftAt: (nowMs: number) => number;
  /** 這一組晚多久才出現（同一格的舊字要滑下來時等它們滑完；6F-10b）。 */
  waitMs: number;
  order: number;
  /** 整組一起飄的距離（組內最大的）。 */
  riseMax: number;
}

/** 看一眼跟著 `?anim=0.1` 放慢（逐格截圖用；正式畫面 1）。 */
const GLANCE_SLOW = devAnimFactor(typeof window === "undefined" ? "" : window.location.search);

type FloatLike = Exclude<FeedbackItem, { kind: "glance" }>;

export abstract class FeedbackLayer extends RgMarkLayer {
  /**
   * 播放一步的地圖回饋（浮動數字、字樣、行動連線、狀態彈出）；不等待結束，效果畫在獨立的圖層，
   * 場景重畫不會清掉。`durationMs` 是整組回饋的時間（已依播放速度縮放）。
   */
  playFeedback(all: readonly FeedbackItem[], durationMs: number): void {
    if (!this.ready || durationMs <= 0) return;
    const items = all.filter((x): x is FloatLike => x.kind !== "glance");
    const glances = all.filter((x): x is Extract<FeedbackItem, { kind: "glance" }> => x.kind === "glance");
    if (glances.length > 0) this.launch(glances.flatMap((g) => this.glanceEffect(g, this.realClock)).map((e) => ({ ...e, clock: "real" as const })));
    // 6H-1：傷害數字照實際時間走（停頓、最後一擊放慢時照常速彈出）
    const now = this.realClock;
    // 6F-6：同一格的字先量好高度，照實際高度錯開往上堆；這一格前幾步的字還沒播完時接在上面（`floatStack.ts`）
    const labels = items.map((item) => (item.kind === "line" ? null : this.floatLabel(item)));
    const groups = new Map<string, number[]>();
    items.forEach((item, i) => {
      if (item.kind === "line") return;
      const k = `${item.pos.x},${item.pos.y}`;
      groups.set(k, [...(groups.get(k) ?? []), i]);
    });
    const offsets = new Map<number, FloatSpot>();
    for (const [k, idx] of [...groups.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))) {
      const heights = idx.map((i) => labels[i]?.restH ?? 0);
      const first = items[idx[0] ?? 0];
      // 6F-10b：頭頂上方放不下時這一格整疊一起往下推（`FloatStack.placeGroup`），推回畫面內的字也照同一格的規則錯開
      const room = first === undefined || first.kind === "line" ? Number.POSITIVE_INFINITY : this.floatRoom(first.pos);
      const placed = this.floatStack.placeGroup(k, now, now + durationMs, heights, room);
      const firstH = heights[0] ?? 0;
      // 6F-11：停住時整組在戰場上緣以內的，飄到最高也不飄出去（`capRise`；最上排的「−7」）
      const fullRise = Math.max(...idx.map((i) => labels[i]?.riseMax ?? 0));
      const riseMax = first === undefined || first.kind === "line" ? fullRise : capRise(fullRise, this.groupRestTop(first.pos, firstH, heights, placed.offsets) + placed.shiftAt(now), this.mapTopY());      const waitMs = Math.min(placed.waitMs, durationMs * 0.4);
      idx.forEach((i, order) => offsets.set(i, { offset: placed.offsets[order] ?? 0, firstH, shiftAt: placed.shiftAt, waitMs, order, riseMax }));
    }
    const effects: Effect[] = [];
    items.forEach((item, i) => {
      const label = labels[i];
      const at = offsets.get(i);
      if (item.kind === "line") effects.push(this.lineEffect(item.from, item.to, now, durationMs));
      else if (label != null && at !== undefined) effects.push(...this.makeEffect(item, label, at, now, durationMs));
    });
    this.launch(effects.map((e) => ({ ...e, clock: "real" as const })));
  }

  /** 浮動字的字（還沒放位置）：停住時的高度、寬度、飄的最大距離。 */
  private floatLabel(item: Exclude<FloatLike, { kind: "line" }>): FloatLabel {
    const isStatus = item.kind === "status";
    const text = isStatus ? `＋${item.text}` : item.text;
    const color = isStatus ? STATUS_COLOR : FLOAT_COLORS[item.tone];
    const big = item.kind === "float" && item.big;
    const t = label(text, floatFontSize(big), color, true);
    t.anchor.set(0.5);
    t.style.stroke = { color: 0x000000, width: 4 };
    // 6N-6：放大字（暴擊）停住時 ＝ 一般字 1.3 倍，整串不超過格寬 1.8 倍
    const fit = floatFit(t.width, T, big);
    const rest = fit * (big ? BIG_REST : 1);
    return { t, big, isStatus, fit, restH: t.height * rest, restW: t.width * rest, riseMax: floatFrame(1, big).rise };
  }

  private makeEffect(item: Exclude<FloatLike, { kind: "line" }>, l: FloatLabel, at: FloatSpot, now: number, durationMs: number): Effect[] {
    const c = this.center(item.pos);
    // 同一組的字照順序延後出現（彈一下），但一起往上飄（6F-6 `groupRise`：後出現的字不會被先出現的追上）
    const delayFrac = Math.min(0.6, at.order * 0.15);
    const delay = at.waitMs + delayFrac * (durationMs - at.waitMs);
    const { t, big, isStatus, fit } = l;
    const node = new Container();
    node.addChild(t);
    // 6N-7：浮動字從單位頭頂往上冒（`unitTopY`，同 6N-4／6C-8b）；6N-8：狀態字（＋狀態）也一樣，光環另外畫
    // 6F-6：同一格的字照實際高度錯開（`at.offset`）；頭頂上方放不下時整格一起往下推（6F-10b `FloatStack.placeGroup`）
    // 6F-10b：位移從這一組第一個字貼頭頂時的中心算（`at.firstH`），頭頂放不下時整格一起往下推（`at.shiftAt`）
    const baseY = floatBaseY(c.y, this.floatTopY(item.pos), at.firstH, 0) - at.offset;
    const x0 = c.x + (isStatus ? T * 0.12 : 0);
    // 6F-10：每一幀照當下的大小（彈一下時比停住時大）把整個字夾在戰場裡，四個邊都一樣（`clampFloatCenter`）
    const put = (y: number, scale: number) => this.placeFloat(node, t, x0, y + at.shiftAt(this.realClock), scale);
    put(baseY, (big ? BIG_REST : 1) * fit);
    node.alpha = 0;
    const rise = (p: number) => (this.reduced ? 0 : groupRise(p, delayFrac, at.riseMax));
    if (!isStatus) {
      return [{
        node,
        startMs: now + delay,
        endMs: now + durationMs,
        update: (p) => {
          // 6N-10：彈一下再淡出（暴擊放大）；減少動態時直接顯示
          const f = floatFrame(p, big, this.reduced);
          node.alpha = f.alpha;
          put(baseY - rise(p), f.scale * fit);
        },
      }];
    }
    // 狀態：格子先閃一圈光環（6N-8 拆成自己的節點，位置、動態照 6N-7 以前：中心在格中心、跟著字的節奏往上飄一點）
    const ringY = c.y - T * 0.3 - at.order * 22;
    const ring = new Graphics().circle(0, T * 0.3, T * 0.4).stroke({ width: 3, color: STATUS_COLOR });
    ring.position.set(this.clampFloatX(c.x + T * 0.12, (t.width * fit) / 2), ringY);
    ring.alpha = 0;
    // 6F-7：光環放進浮動字下面那一層（`layer: "under"`），不會蓋住同一格前一步的「暴擊 −9」
    return [
      {
        node: ring,
        startMs: now + delay,
        endMs: now + durationMs,
        layer: "under",
        update: (p) => {
          const f = floatFrame(p, big, this.reduced);
          ring.alpha = f.alpha;
          ring.position.y = ringY - f.rise;
          ring.scale.set(f.scale * fit);
        },
      },
      {
        node,
        startMs: now + delay,
        endMs: now + durationMs,
        update: (p) => {
          const f = floatFrame(p, big, this.reduced);
          node.alpha = f.alpha;
          put(baseY - rise(p), f.scale * fit);
        },
      },
    ];
  }

  /**
   * RG-3：敵人放陷阱時「看那一格一眼」（樣張 2.6）：放置者頭頂（含頭飾）上方的小泡泡、兩隻眼往那一格看，0.6 秒（和浮字同一層）。
   * 每一幀重畫一張小畫布（彈出 → 瞳孔轉過去 → 視線 → 淡出）；減少動態時直接顯示、不彈。
   */
  private glanceEffect(g: Extract<FeedbackItem, { kind: "glance" }>, now: number): Effect[] {
    const k = minMarkScale(RG_MIN.glance.base, RG_MIN.glance.min, this.scale);
    const c = this.center(g.pos);
    const top = this.rgHeadTop(g.unitId) ?? c.y + this.floatTopY(g.pos);
    const res = Math.max(1, Math.ceil((typeof window === "undefined" ? 1 : window.devicePixelRatio || 1) * this.scale * k * 4) / 4);
    const box = 32;
    const canvas = typeof document === "undefined" ? null : document.createElement("canvas");
    const ctx = canvas?.getContext("2d") ?? null;
    if (canvas === null || ctx === null) return [];
    canvas.width = Math.ceil(box * res);
    canvas.height = Math.ceil(box * res);
    const dir = glanceDir(g.pos, g.to);
    const paint = (ms: number) => {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.setTransform(res, 0, 0, res, (box / 2) * res, (box / 2) * res);
      drawGlance(ctx, 0, 0, dir, ms, 1, this.reduced);
    };
    paint(0);
    const tex = Texture.from(canvas);
    const node = new Sprite(tex);
    node.anchor.set(0.5);
    node.width = box * k;
    node.height = box * k;
    node.position.set(c.x, glanceY(top, k));
    node.label = "rg-glance";
    return [
      {
        node,
        startMs: now,
        endMs: now + RG_TIMING.glanceMs * GLANCE_SLOW,
        update: (p) => {
          paint(p * RG_TIMING.glanceMs);
          tex.source.update();
        },
        end: () => tex.destroy(true),
      },
    ];
  }

  /** 6F-11：一組浮動字停住時（還沒往下推）最上面那個字的上緣 y（世界座標，和 `makeEffect` 的 `baseY` 同一個算法）。 */
  private groupRestTop(p: Pos, firstH: number, heights: readonly number[], offsets: readonly number[]): number {
    const last = heights.length - 1;
    return floatBaseY(this.center(p).y, this.floatTopY(p), firstH, 0) - (offsets[last] ?? 0) - (heights[last] ?? 0) / 2;
  }

  /** 6F-11：戰場（地圖）上緣的 y（世界座標，扣掉鏡頭偏移；畫布上緣再往上是頭頂預留）。 */
  private mapTopY(): number {
    return -this.cam.y;
  }

  /** 浮動字所在格的單位頂端（`unitTopY`）；那一格沒有人（已經移走）時用標準人形的頭頂。 */
  private floatTopY(p: Pos): number {
    const u = this.model?.units.find((x) => x.x === p.x && x.y === p.y);
    return u === undefined ? HUMAN_TOP_Y : unitMarkTopY(u); // QK-9：頭目從搬上去的 HUD 上方冒，不穿過 HUD
  }

  /**
   * 6F-10b：`p` 那一格頭頂上方給浮動字的空間（從頭頂線往上算）：字停住時的上緣最高到戰場上緣（`floatBounds`）
   * 再往下留飄的距離（`FLOAT_RISE_MAX`）和邊緣空隙（`FLOAT_EDGE_PAD`），飄到最高也不會被夾回來、壓到下面的字。
   * 6F-11：再往下 `FLOAT_TOP_SHIFT_PX`（畫面 px），最上排的字留在戰場上緣以內。
   */
  private floatRoom(p: Pos): number {
    const line = this.center(p).y + this.floatTopY(p) - FLOAT_HEAD_GAP;
    return line - (this.floatBounds().top + FLOAT_RISE_MAX + FLOAT_EDGE_PAD + floatTopShift(this.scale));
  }

  /**
   * 浮動字的畫布可見範圍（世界座標，扣掉鏡頭偏移與震動）：左右、下緣是地圖和畫布的交集，上面是畫布上緣（含頭頂預留）。
   */
  private floatBounds(): FloatBounds {
    const w = (this.model?.width ?? 0) * T;
    const h = (this.model?.height ?? 0) * T;
    // 6F-12：夾在震動、鏡頭偏移之後看得到的戰場裡（震動是整個場景的位移 `app.stage.position`）
    return visibleFieldBounds(w, h, this.worldBaseY, this.cam, this.app.stage.position);
  }

  /** 6F-10：把浮動字放在 (x, y)、縮放 `scale`，整個字（含黑邊）往內推到戰場裡（`clampFloatCenter`）。 */
  private placeFloat(node: Container, t: Text, x: number, y: number, scale: number): void {
    node.scale.set(scale);
    const p = clampFloatCenter(x, y, (t.width * scale) / 2, (t.height * scale) / 2, this.floatBounds());
    node.position.set(p.x, p.y);
  }

  /** 浮動文字的水平位置往內推，不超出地圖左右邊緣（UI-T1：邊緣格的「跑步 移動＋N」被切掉）。 */
  private clampFloatX(x: number, half: number): number {
    const width = (this.model?.width ?? 0) * T;
    if (width <= 0 || half * 2 >= width) return x;
    return Math.min(Math.max(x, half + 2), width - half - 2);
  }

  private lineEffect(from: Pos, to: Pos, now: number, durationMs: number): Effect {
    const a = this.center(from);
    const b = this.center(to);
    const angle = Math.atan2(b.y - a.y, b.x - a.x);
    const head = 10;
    const g = new Graphics()
      .moveTo(a.x, a.y)
      .lineTo(b.x, b.y)
      .stroke({ width: 4, color: LINE_COLOR })
      .poly([
        b.x,
        b.y,
        b.x - head * Math.cos(angle - 0.45),
        b.y - head * Math.sin(angle - 0.45),
        b.x - head * Math.cos(angle + 0.45),
        b.y - head * Math.sin(angle + 0.45),
      ])
      .fill(LINE_COLOR);
    const node = new Container();
    node.addChild(g);
    node.alpha = 0;
    return {
      node,
      startMs: now,
      endMs: now + durationMs * 0.6,
      update: (p) => {
        node.alpha = p < 0.4 ? 0.95 : 0.95 * (1 - (p - 0.4) / 0.6);
      },
    };
  }
}
