// 測試用假畫布（QI-1a）：Q 版小圖示的 `render` 會另外建畫布（`qIcon/core.ts` 的 `setQCanvasFactory`），vitest 沒有 DOM，用這個代替。
// 每張假畫布的 2D context 把所有呼叫與屬性設定記進同一份 `log.calls`（`null` 時不記，只求跑得快）；
// `getImageData` 回傳空資料（圓章自動縮放量不到範圍，退回 meta 的上限），`getTransform` 回傳單位矩陣。

export interface FakeCanvasLog {
  calls: string[] | null;
}

const fmt = (a: unknown): string => {
  if (typeof a === "number") return a.toFixed(3);
  if (typeof a === "string") return a;
  if (a !== null && typeof a === "object" && "width" in a && "height" in a) return `canvas(${String((a as { width: unknown }).width)}x${String((a as { height: unknown }).height)})`;
  return typeof a;
};

function recordingCtx(canvas: object, log: FakeCanvasLog): CanvasRenderingContext2D {
  const store: Record<string, unknown> = { canvas };
  return new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        log.calls?.push(`${prop}(${args.map(fmt).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") return { addColorStop: (...s: unknown[]) => log.calls?.push(`stop(${s.map(fmt).join(",")})`) };
        if (prop === "getTransform") return { a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 };
        if (prop === "getImageData") return { data: new Uint8ClampedArray(0) };
        return undefined;
      };
    },
    set(target, prop: string, value: unknown) {
      target[prop] = value;
      log.calls?.push(`${prop}=${fmt(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
}

/** 建立假畫布的函式（給 `setQCanvasFactory`）。 */
export function fakeCanvasFactory(log: FakeCanvasLog): (w: number, h: number) => HTMLCanvasElement {
  return (w, h) => {
    const cv: Record<string, unknown> = { width: w, height: h };
    const ctx = recordingCtx(cv, log);
    cv.getContext = () => ctx;
    return cv as unknown as HTMLCanvasElement;
  };
}

/** 外層的假 2D context（記到 `log.calls`）。 */
export function fakeCtx(log: FakeCanvasLog, width = 128, height = 128): CanvasRenderingContext2D {
  return recordingCtx({ width, height }, log);
}
