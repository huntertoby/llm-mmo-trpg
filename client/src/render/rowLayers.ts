// 由北到南一排一排的圖層（Phase 3-19 整格抬高）：每排依序畫地形與崖面、表面裝飾、物件、高度徽章、
// 陷阱、單位，讓南邊的高格自然蓋住北邊一排。另外記下每個「跟著格子抬高」的節點，升降動畫時一起移動。
import { Container } from "pixi.js";
import type { Pos } from "../api/types";
import { posKey } from "../battle/geometry";

export interface RowLayer {
  root: Container;
  ground: Container;
  deco: Container;
  objects: Container;
  badges: Container;
  traps: Container;
  units: Container;
}

function makeRow(): RowLayer {
  const row: RowLayer = {
    root: new Container(),
    ground: new Container(),
    deco: new Container(),
    objects: new Container(),
    badges: new Container(),
    traps: new Container(),
    units: new Container(),
  };
  row.root.addChild(row.ground, row.deco, row.objects, row.badges, row.traps, row.units);
  return row;
}

/** 跟著格子抬高的節點：`baseY` 是未抬高時的 y；`redraw` 給崖面這類會跟著抬高量改形狀的圖。 */
interface LiftNode {
  node: Container;
  baseY: number;
  redraw?: (lift: number) => void;
}

export class RowStack {
  readonly root = new Container();
  private rows: RowLayer[] = [];
  private readonly nodes = new Map<string, LiftNode[]>();

  /** 重建 `n` 排空圖層（舊的全部銷毀）。 */
  reset(n: number): void {
    for (const child of this.root.removeChildren()) child.destroy({ children: true });
    this.nodes.clear();
    this.rows = Array.from({ length: Math.max(0, n) }, makeRow);
    for (const r of this.rows) this.root.addChild(r.root);
  }

  /** 第 y 排；超出範圍時取最近的一排（不會發生在正常的模型上）。 */
  row(y: number): RowLayer {
    const i = Math.max(0, Math.min(this.rows.length - 1, y));
    return this.rows[i] as RowLayer;
  }

  /** 把節點放在 (x, y − lift)，並登記成跟著格子 `p` 抬高。 */
  place(node: Container, p: Pos, x: number, y: number, lift: number, redraw?: (lift: number) => void): void {
    node.position.set(x, y - lift);
    const key = posKey(p);
    const list = this.nodes.get(key) ?? [];
    list.push({ node, baseY: y, redraw });
    this.nodes.set(key, list);
  }

  /** 升降動畫：把格子 `p` 上登記的節點移到抬高 `lift` 的位置。 */
  setLift(p: Pos, lift: number): void {
    for (const n of this.nodes.get(posKey(p)) ?? []) {
      if (n.node.destroyed) continue;
      n.node.y = n.baseY - lift;
      n.redraw?.(lift);
    }
  }
}
