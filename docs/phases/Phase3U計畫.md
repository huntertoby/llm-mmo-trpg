# Phase 3U｜使用者試玩回報的介面修正（2026-10-29）

> 使用者原話：「ui有問題 人 變好小喔」（附 3 張截圖，專案 PM 轉達）。截圖：`C:\Users\tobby\AppData\Local\Temp\claude\F--PythonProject-LLM-MMO-TRPG\bb70c859-9c7e-4ff5-922e-deb3b06797c3\images\1.png`～`3.png`。

## 0. 原因（開發 PM 查證）
1. **開局種族卡滑過時，說明文字疊在「種族與出身」標題上**（圖 1）：種族卡、出身卡的浮動卡（`RaceOriginPicker.tsx` 的 `FloatCard className="skill-card-float race-pick-card"`）**沒有底色**。共用 `.float-card` 與 `.float-card-body` 本身透明，底色一向來自裡面的 `.skill-card`；種族卡內容不是技能卡，所以整張透明（實測 `background-color: rgba(0,0,0,0)`）。3R-3a 起就有，**不是 3T-7 拆樣式造成的**（拆分前後規則相同）。
2. **屬性分配「敏捷 ★建議」壓到按鈕**（圖 2）：`.run-alloc-row` 第一欄固定 `3em`、`.run-alloc-name` 不換行，帶「★建議」時溢出到減號按鈕上。3H-3 起就有。
3. **戰場人物變小**（圖 3）：C 畫風 `DOLL_SCALE = 0.74`（52px 格人約 38～40px），照 C 畫風移植需求定的；使用者覺得太小 → 比例請美術 PM 定（3U-2）。

## 1. 3U-1｜浮動卡底色＋屬性列＋全站排版掃描（sonnet；約 0.4 段）
1. **浮動卡底色（流程改善 E：全面掃描）**：找出所有 `FloatCard`／`useFloatCard`／`PartTip`／`Hint` 的使用處，凡內容不是自帶底色的 `.skill-card` 者都要有底色（建議：共用元件給 `.float-card-body` 一個預設面板底色與邊框，`.skill-card-float` 內含技能卡的維持現狀不疊兩層；或新增一個明確的 `panel` 變體）。逐一列表（元件、改前有無底色、改後）。
2. **自動檢查**：`client/src/dev/layoutSmoke.ts` 加一項「每張顯示中的浮動卡有不透明底色」（看 `.float-card` 或其 body／第一個子元素的計算底色，不是全透明）；`floatCardRule.test.ts` 或新 vitest 加靜態規則（新增 `FloatCard` 使用處要嘛帶 `.skill-card`，要嘛用有底色的變體）。
3. **屬性列**：`.run-alloc-row` 第一欄改成能容納「名稱＋★建議」（例如 `max-content` 或讓 ★建議換到下一行），按鈕與數值對齊；「影響：…」那行維持跨整列。
4. **全站排版掃描**：新增或擴充 `layoutSmoke` 案例，涵蓋開始畫面（滑過種族卡、出身卡、屬性分配、關鍵字）、一輪畫面、工坊、戰鬥畫面，三種視窗 1600×900、1280×720、800×600；量測「文字溢出自己的框並壓到相鄰元素」（例如 `scrollWidth > clientWidth` 的 `nowrap` 元素、兄弟元素矩形互相重疊）。發現的其他問題一起修，逐條寫進報告。
5. 驗收：vitest、tsc、build、排版煙霧檢查（新舊案例全 PASS）、內建瀏覽器截圖（種族卡滑過、屬性分配，前後對照，`docs/phases/img/3U-1-*`）。報告 `Phase3U-1報告.md`。

## 2. 3U-2｜戰場人物比例（等美術 PM 定數字後排）
