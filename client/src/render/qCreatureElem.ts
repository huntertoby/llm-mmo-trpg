// QK-4：異形的元素色（palette.ts 同一份元素主色；第二色是亮色，眼睛與晶光用）。inkCreature、qCreatureAnim、qBoss 共用。
export const CREATURE_ELEM: Readonly<Record<string, readonly [string, string]>> = {
  fire: ["#ff6a1a", "#ffd04a"],
  ice: ["#8fe3ff", "#e8fbff"],
  lightning: ["#fff36b", "#fff7c0"],
  poison: ["#7ddc3a", "#d6f59a"],
  wind: ["#c8ffe8", "#effff8"],
  earth: ["#b0814a", "#e6c89a"],
  holy: ["#fff2b0", "#fffbe0"],
  shadow: ["#9a6ad8", "#c8a8f0"],
  water: ["#3a7bd5", "#d8f0ff"],
};
export const FIRE: readonly [string, string] = CREATURE_ELEM["fire"]!;
/** 元素色（不認得 → 預設）。 */
export const elemOr = (element: string | undefined, d: readonly [string, string]): readonly [string, string] => (element !== undefined ? (CREATURE_ELEM[element] ?? d) : d);
