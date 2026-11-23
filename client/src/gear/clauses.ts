// 裝備文字的小工具（E6-b2 美術小修，`docs/art/E6-b2驗收.md`）。

/** 用「；」把幾段接成一行：先拿掉每段結尾的「。」，不會出現「……不會滑倒。；基礎加成……」。 */
export function joinClauses(parts: readonly string[]): string {
  return parts.map((p) => p.replace(/。+$/u, "")).join("；");
}
