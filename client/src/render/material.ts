// 材質色（Phase 3T-4：從 appearance.ts 搬出，讓墨線畫法層 `inkStyle.ts` 與 `artPalette.ts` 能匯入而不形成循環）。
// 這是材質色的唯一來源：紙娃娃（`itemColors`）、裝備圖示（`artPalette.GEAR_MATERIAL`）、墨線畫風（`inkStyle.MAT`）都由此導出。

/** 材質 → [主色, 暗色]；不認得的材質用布料色。 */
export const MATERIAL: Readonly<Record<string, readonly [string, string]>> = {
  cloth: ["#8a8f99", "#5d6168"],
  leather: ["#8a5a32", "#5e3b1f"],
  iron: ["#7a828b", "#474c52"],
  steel: ["#a9b6c6", "#6d7a8a"],
  gold: ["#e8bb48", "#9c7420"],
  wood: ["#a06a36", "#6a4420"],
  bone: ["#e9e3cf", "#a8a08a"],
  // Phase 3G-G5b：裝備外觀新增的材質；原有 7 種不動，舊單位畫面不變
  copper: ["#b06a3c", "#6e3e20"],
  silver: ["#e8edf2", "#a8b0ba"],
  crystal: ["#b8a8ff", "#7a68c8"],
};
