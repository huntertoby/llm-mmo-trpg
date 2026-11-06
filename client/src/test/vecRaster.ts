// 測試用的向量點取樣畫布（QK-1）：vitest 的 node 環境沒有 Canvas，這裡記下每次 fill／stroke 的多邊形（已套變換、曲線攤平）、
// 顏色、透明度與當時的剪裁，之後可以在任一點「取樣」出合成後的顏色（source-over），用來做樣張 selfTest 的像素檢查
// （手在握把上、刃不被手臂蓋住、背面手被擋住、披風在最上層、輪廓寬度）。沒有反鋸齒；陰影、合成模式不支援（Q 版小人本體用不到）。
type P = [number, number];
type M = [number, number, number, number, number, number];
interface Shape {
  polys: P[][];
  even: boolean;
  box: [number, number, number, number];
}
interface Op {
  stroke: boolean;
  shape: Shape;
  hw: number; // stroke 半寬（裝置座標）
  rgba: [number, number, number, number];
  clips: Shape[];
}
interface St {
  m: M;
  fill: string;
  stroke: string;
  lw: number;
  alpha: number;
  clips: Shape[];
}

const TAU = Math.PI * 2;

export function parseColor(c: string): [number, number, number, number] {
  const s = c.trim().toLowerCase();
  if (s.startsWith("#")) {
    let h = s.slice(1);
    if (h.length === 3) h = h.split("").map((x) => x + x).join("");
    const n = parseInt(h.slice(0, 6), 16);
    const a = h.length === 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1;
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, a];
  }
  const m = /rgba?\(([^)]+)\)/.exec(s);
  if (m) {
    const v = m[1]!.split(",").map((x) => parseFloat(x));
    return [v[0] ?? 0, v[1] ?? 0, v[2] ?? 0, v[3] ?? 1];
  }
  return [0, 0, 0, 1];
}

function boxOf(polys: P[][], pad = 0): [number, number, number, number] {
  let x0 = Infinity;
  let y0 = Infinity;
  let x1 = -Infinity;
  let y1 = -Infinity;
  for (const p of polys)
    for (const [x, y] of p) {
      x0 = Math.min(x0, x);
      y0 = Math.min(y0, y);
      x1 = Math.max(x1, x);
      y1 = Math.max(y1, y);
    }
  return [x0 - pad, y0 - pad, x1 + pad, y1 + pad];
}

function inside(sh: Shape, x: number, y: number): boolean {
  const [x0, y0, x1, y1] = sh.box;
  if (x < x0 || x > x1 || y < y0 || y > y1) return false;
  let wind = 0;
  let cross = 0;
  for (const poly of sh.polys) {
    const n = poly.length;
    for (let i = 0; i < n; i++) {
      const [ax, ay] = poly[i]!;
      const [bx, by] = poly[(i + 1) % n]!;
      if (ay <= y) {
        if (by > y && (bx - ax) * (y - ay) - (x - ax) * (by - ay) > 0) {
          wind++;
          cross++;
        }
      } else if (by <= y && (bx - ax) * (y - ay) - (x - ax) * (by - ay) < 0) {
        wind--;
        cross++;
      }
    }
  }
  return sh.even ? cross % 2 === 1 : wind !== 0;
}

function segDist(x: number, y: number, a: P, b: P): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const l2 = dx * dx + dy * dy;
  const t = l2 === 0 ? 0 : Math.max(0, Math.min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / l2));
  return Math.hypot(x - (a[0] + t * dx), y - (a[1] + t * dy));
}

function onStroke(sh: Shape, hw: number, x: number, y: number, closed: boolean[]): boolean {
  const [x0, y0, x1, y1] = sh.box;
  if (x < x0 || x > x1 || y < y0 || y > y1) return false;
  for (let k = 0; k < sh.polys.length; k++) {
    const poly = sh.polys[k]!;
    const n = poly.length;
    if (n === 1 && Math.hypot(x - poly[0]![0], y - poly[0]![1]) <= hw) return true;
    for (let i = 0; i + 1 < n; i++) if (segDist(x, y, poly[i]!, poly[i + 1]!) <= hw) return true;
    if (closed[k] && n > 2 && segDist(x, y, poly[n - 1]!, poly[0]!) <= hw) return true;
  }
  return false;
}

/** 記錄式畫布。`ctx` 給要測的程式畫；`at(x,y)` 取樣（裝置座標）。 */
export function vecCanvas(): {
  ctx: CanvasRenderingContext2D;
  at: (x: number, y: number) => [number, number, number, number];
  ops: () => number;
} {
  let st: St = { m: [1, 0, 0, 1, 0, 0], fill: "#000", stroke: "#000", lw: 1, alpha: 1, clips: [] };
  const stack: St[] = [];
  let polys: P[][] = [];
  let closed: boolean[] = [];
  let cur: P[] | null = null;
  const ops: Array<Op & { closed: boolean[] }> = [];
  const T = (x: number, y: number): P => [st.m[0] * x + st.m[2] * y + st.m[4], st.m[1] * x + st.m[3] * y + st.m[5]];
  const mul = (n: M): void => {
    const [a, b, c, d, e, f] = st.m;
    st.m = [a * n[0] + c * n[1], b * n[0] + d * n[1], a * n[2] + c * n[3], b * n[2] + d * n[3], a * n[4] + c * n[5] + e, b * n[4] + d * n[5] + f];
  };
  const last = (): P | null => (cur && cur.length ? cur[cur.length - 1]! : null);
  const lastLocal = { x: 0, y: 0 };
  const startSub = (p: P): void => {
    cur = [p];
    polys.push(cur);
    closed.push(false);
  };
  const lineTo = (x: number, y: number): void => {
    const p = T(x, y);
    if (!cur) startSub(p);
    else cur.push(p);
    lastLocal.x = x;
    lastLocal.y = y;
  };
  const scaleK = (): number => Math.sqrt(Math.abs(st.m[0] * st.m[3] - st.m[1] * st.m[2]));
  const ellipse = (cx: number, cy: number, rx: number, ry: number, rot: number, a0: number, a1: number, ccw = false): void => {
    let d = a1 - a0;
    if (!ccw) {
      if (d >= TAU) d = TAU;
      else {
        d %= TAU;
        if (d < 0) d += TAU;
      }
    } else if (-d >= TAU) d = -TAU;
    else {
      d %= TAU;
      if (d > 0) d -= TAU;
    }
    const n = Math.max(8, Math.ceil((Math.abs(d) / TAU) * 48));
    const cr = Math.cos(rot);
    const sr = Math.sin(rot);
    for (let i = 0; i <= n; i++) {
      const a = a0 + (d * i) / n;
      const ex = rx * Math.cos(a);
      const ey = ry * Math.sin(a);
      lineTo(cx + ex * cr - ey * sr, cy + ex * sr + ey * cr);
    }
  };
  const rectSub = (pts: Array<[number, number]>): void => {
    cur = null;
    for (const [x, y] of pts) lineTo(x, y);
    closed[closed.length - 1] = true;
    cur = null;
  };
  const rrect = (x: number, y: number, w: number, h: number, r0: number): void => {
    const r = Math.max(0, Math.min(r0, Math.abs(w) / 2, Math.abs(h) / 2));
    cur = null;
    const arcPts = (cx: number, cy: number, a0: number): void => {
      for (let i = 0; i <= 6; i++) {
        const a = a0 + (Math.PI / 2) * (i / 6);
        lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
      }
    };
    arcPts(x + w - r, y + r, -Math.PI / 2);
    arcPts(x + w - r, y + h - r, 0);
    arcPts(x + r, y + h - r, Math.PI / 2);
    arcPts(x + r, y + r, Math.PI);
    closed[closed.length - 1] = true;
    cur = null;
  };
  const shape = (even: boolean, pad = 0): Shape => {
    const ps = polys.filter((p) => p.length > 0).map((p) => [...p]);
    return { polys: ps, even, box: boxOf(ps, pad) };
  };
  const api: Record<string, (...a: never[]) => unknown> = {
    save: () => void stack.push({ ...st, clips: [...st.clips] }),
    restore: () => {
      st = stack.pop() ?? st;
    },
    translate: (x: number, y: number) => mul([1, 0, 0, 1, x, y]),
    rotate: (r: number) => mul([Math.cos(r), Math.sin(r), -Math.sin(r), Math.cos(r), 0, 0]),
    scale: (x: number, y: number) => mul([x, 0, 0, y, 0, 0]),
    transform: (a: number, b: number, c: number, d: number, e: number, f: number) => mul([a, b, c, d, e, f]),
    setTransform: (a: number, b: number, c: number, d: number, e: number, f: number) => {
      st.m = [a, b, c, d, e, f];
    },
    resetTransform: () => {
      st.m = [1, 0, 0, 1, 0, 0];
    },
    getTransform: () => ({ a: st.m[0], b: st.m[1], c: st.m[2], d: st.m[3], e: st.m[4], f: st.m[5] }),
    beginPath: () => {
      polys = [];
      closed = [];
      cur = null;
    },
    moveTo: (x: number, y: number) => {
      startSub(T(x, y));
      lastLocal.x = x;
      lastLocal.y = y;
    },
    lineTo: (x: number, y: number) => lineTo(x, y),
    closePath: () => {
      if (cur) closed[closed.length - 1] = true;
      const f = cur?.[0];
      cur = null;
      if (f) startSub(f);
      polys.pop();
      closed.pop();
      cur = null;
    },
    quadraticCurveTo: (cx: number, cy: number, x: number, y: number) => {
      const x0 = lastLocal.x;
      const y0 = lastLocal.y;
      if (!last()) lineTo(cx, cy);
      for (let i = 1; i <= 10; i++) {
        const t = i / 10;
        const u = 1 - t;
        lineTo(u * u * x0 + 2 * u * t * cx + t * t * x, u * u * y0 + 2 * u * t * cy + t * t * y);
      }
    },
    bezierCurveTo: (c1x: number, c1y: number, c2x: number, c2y: number, x: number, y: number) => {
      const x0 = lastLocal.x;
      const y0 = lastLocal.y;
      for (let i = 1; i <= 12; i++) {
        const t = i / 12;
        const u = 1 - t;
        lineTo(u * u * u * x0 + 3 * u * u * t * c1x + 3 * u * t * t * c2x + t * t * t * x, u * u * u * y0 + 3 * u * u * t * c1y + 3 * u * t * t * c2y + t * t * t * y);
      }
    },
    arc: (x: number, y: number, r: number, a0: number, a1: number, ccw?: boolean) => ellipse(x, y, r, r, 0, a0, a1, ccw === true),
    ellipse: (x: number, y: number, rx: number, ry: number, rot: number, a0: number, a1: number, ccw?: boolean) => ellipse(x, y, rx, ry, rot, a0, a1, ccw === true),
    rect: (x: number, y: number, w: number, h: number) =>
      rectSub([
        [x, y],
        [x + w, y],
        [x + w, y + h],
        [x, y + h],
      ]),
    roundRect: (x: number, y: number, w: number, h: number, r: number) => rrect(x, y, w, h, typeof r === "number" ? r : 0),
    fill: (rule?: string) => {
      const sh = shape(rule === "evenodd");
      if (sh.polys.length) ops.push({ stroke: false, shape: sh, hw: 0, rgba: col(st.fill), clips: st.clips, closed: [...closed] });
    },
    stroke: () => {
      const hw = (st.lw * scaleK()) / 2;
      const sh = shape(false, hw);
      if (sh.polys.length) ops.push({ stroke: true, shape: sh, hw, rgba: col(st.stroke), clips: st.clips, closed: [...closed] });
    },
    clip: (rule?: string) => {
      st.clips = [...st.clips, shape(rule === "evenodd")];
    },
    fillRect: (x: number, y: number, w: number, h: number) => {
      const keep = { polys, closed, cur };
      polys = [];
      closed = [];
      rectSub([
        [x, y],
        [x + w, y],
        [x + w, y + h],
        [x, y + h],
      ]);
      ops.push({ stroke: false, shape: shape(false), hw: 0, rgba: col(st.fill), clips: st.clips, closed: [...closed] });
      polys = keep.polys;
      closed = keep.closed;
      cur = keep.cur;
    },
  };
  const col = (c: string): [number, number, number, number] => {
    const [r, g, b, a] = parseColor(c);
    return [r, g, b, a * st.alpha];
  };
  const props: Record<string, unknown> = {};
  const ctx = new Proxy(props, {
    get(_t, prop: string) {
      if (prop in api) return api[prop];
      if (prop === "fillStyle") return st.fill;
      if (prop === "strokeStyle") return st.stroke;
      if (prop === "lineWidth") return st.lw;
      if (prop === "globalAlpha") return st.alpha;
      if (prop in props) return props[prop];
      return () => undefined;
    },
    set(_t, prop: string, v) {
      if (prop === "fillStyle") st.fill = String(v);
      else if (prop === "strokeStyle") st.stroke = String(v);
      else if (prop === "lineWidth") st.lw = Number(v);
      else if (prop === "globalAlpha") st.alpha = Number(v);
      else props[prop] = v;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  const at = (x: number, y: number): [number, number, number, number] => {
    let r = 0;
    let g = 0;
    let b = 0;
    let a = 0;
    for (const op of ops) {
      const hit = op.stroke ? onStroke(op.shape, op.hw, x, y, op.closed) : inside(op.shape, x, y);
      if (!hit || !op.clips.every((c) => inside(c, x, y))) continue;
      const [sr, sg, sb, sa] = op.rgba;
      const na = sa + a * (1 - sa);
      if (na <= 0) continue;
      r = (sr * sa + r * a * (1 - sa)) / na;
      g = (sg * sa + g * a * (1 - sa)) / na;
      b = (sb * sa + b * a * (1 - sa)) / na;
      a = na;
    }
    return [Math.round(r), Math.round(g), Math.round(b), a];
  };
  return { ctx, at, ops: () => ops.length };
}

export const hex = ([r, g, b]: readonly number[]): string => "#" + [r, g, b].map((v) => (v ?? 0).toString(16).padStart(2, "0")).join("");
