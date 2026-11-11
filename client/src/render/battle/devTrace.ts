// CB-3b：開發用的播放紀錄（實機巡檢看「每次重畫的格號」與「這一招播的是哪個片段」）。
// 只在開發伺服器（`import.meta.env.DEV`）而且頁面自己先放了 `window.__battleTrace = []` 時才記；
// 正式建置時 `import.meta.env.DEV` 是 false，整段被移除，不輸出任何東西。只記錄，不影響畫面與時間。

/** 一筆紀錄：`kind`＝`row`（一招的時間軸列）、`frame`（異形出招片段這一次重畫的格）或 `walk`（一段走路的開始、結束）。 */
export type BattleTrace = Record<string, unknown> & { kind: "row" | "frame" | "walk" };

export function battleTrace(entry: () => BattleTrace): void {
  if (!import.meta.env.DEV) return;
  const log = (globalThis as { __battleTrace?: unknown }).__battleTrace;
  if (Array.isArray(log)) log.push(entry());
}
