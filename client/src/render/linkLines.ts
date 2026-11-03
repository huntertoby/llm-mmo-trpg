// 「連心的」精英的連線（Phase 5A-ART2，docs/art/敵人外觀.md 1.2）：有 linked 詞綴的單位 ↔ 相鄰（曼哈頓距離 1，同 heart_link 的
// share_damage range 1）的同陣營、沒倒下的單位。純函式，可用 vitest 檢查；每一對只出現一次，依單位 ID 排序。
export interface LinkUnit {
  id: string;
  x: number;
  y: number;
  team: string;
  downed: boolean;
}

export function linkPairs<U extends LinkUnit>(units: readonly U[], linked: (u: U) => boolean): Array<[U, U]> {
  const out: Array<[U, U]> = [];
  const seen = new Set<string>();
  const sorted = [...units].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  for (const a of sorted) {
    if (a.downed || !linked(a)) continue;
    for (const b of sorted) {
      if (b === a || b.downed || b.team !== a.team) continue;
      if (Math.abs(a.x - b.x) + Math.abs(a.y - b.y) !== 1) continue;
      const key = a.id < b.id ? `${a.id}|${b.id}` : `${b.id}|${a.id}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(a.id < b.id ? [a, b] : [b, a]);
    }
  }
  return out;
}
