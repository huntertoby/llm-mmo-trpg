// 單位資訊卡的「裝備加成」摺疊標題（Phase 3-30 第 32.2 項）：預設摺疊，標題列顯示條數。
export function gearFoldLabel(count: number, open: boolean): string {
  return `${open ? "▾" : "▸"} 裝備加成（${count} 條）`;
}
