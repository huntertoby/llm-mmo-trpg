# Phase UI-E3b（＋UI-E3c 美術退回 11 項）完成報告

實作者。前半（伺服器欄位、UI-E3c 部分）2026-11-05 中途收尾；後半 2026-11-06 接手做完。

## 1. UI-E3b

### 伺服器（`5b26c348`，前一位已完成）

- `EncounterEnemyView.rank`（`normal`／`elite`／`boss`）與 `look`（`FieldHeroView`，照開戰時的範本、詞綴、裝備；每名都有）。
- `MercenaryView.skill_ids`、`ShadowView.skill_ids`（和 `skills_zh` 同順序、同長度）。
- 不改規則、不改存檔、不升 `WORLD_RULES_VERSION`。測試 `tests/api/test_encounter_look_uie3b.py` 等。

### 前端（這次）

- **遇敵卡頭像**：新的 `client/src/world/enemyThumb.tsx`。每名敵人前面一個 36px 圓框頭像，照伺服器的 `look` 畫：
  - 人形用戰場紙娃娃（`resolveDoll` → `renderFigureCanvas`，正面），裁掉透明邊後取上半身（`DOLL_CROP` 0.62），臉才看得清楚；
  - 異形用戰場異形（`resolveCreature`，`field: true`，側面朝西，同戰場）整隻放進框；
  - 離屏畫好、依外觀＋階級快取成圖片網址；沒有 DOM（測試、SSR）或沒有外觀時留同大小的空框。
- **金環**：精英、Boss 的框是金色 `#ffbf3a`＋墨線 `#281e14`（`docs/art/敵人外觀.md`）；Boss 另加外光（外光只代表頭目）。第三方紫框。
- 遇敵卡的標籤：`rank === "boss"` 寫「Boss」，其餘精英照舊寫「精英」。
- **雇用面板改用 `skill_ids`**：`hireSkills.ts` 改成 `pairSkills(names, ids, cards)`，照 ID 一一取卡（`useSkillCards`）；
  拿掉「主題句 → `/api/builds` → 照招名對」的間接做法（`themeSkillIds`、`matchSkills`、`useBuilds` 刪除）。
  影子也改畫圖示列；生成技能查不到卡片時照舊寫字。
- 開發頁 `story-gallery.html#encounter-boss`：Boss 遇敵卡。資料 `client/src/dev/fixtures/encounterBoss.json` 是伺服器對 dev-boss 那場遭遇（雲頂觀、6 級）算出的 `EncounterView`，用正式 `EncounterPanel` 畫。
- 測試：`client/src/world/uiE3b.test.ts`（6 個）、`uiE3.test.ts` 的雇用測試改成 `pairSkills`、`party.test.ts` 補 `skill_ids`。

## 2. UI-E3c（`docs/archive/art/UI-E3與UI-E4檢查.md` 第 3 節）

| # | 狀態 | 做法 | 驗證 |
|---|---|---|---|
| 1 hire 800 寬不一致 | 完成 | 原因：開發頁 `Frame` 只在渲染時讀一次 `window.innerWidth`。改成跟著 resize 重算，並補上正式面板的「×」。這次雇用面板改在**正式遊戲**拍：800×600 兩張的面板都是 493px 寬 | `uie3b_hire_800`、`uie3c_hire_hover_800`；`uiE3c.test.ts` |
| 2 花費行開頭「・」 | 完成 | `costPiecesTrailing`：「・」留在上一段行尾，只用在 `SkillTile`；戰鬥底列不變 | `uie3c_skills_1600_zoom`；`uiE3c.test.ts` 3 個 |
| 3 橘點蓋角標 | 完成 | 橘點移到左上 | `uie3c_bag_gear_1600_dev_zoom` |
| 4 換裝標題空隙 | 完成 | 標題後加全形空白 | `uie3c_skills_1600_zoom` |
| 5 技能卡蓋主角卡 | 完成 | `SkillTile` 加 `prefer`（預設上方），只有技能面板（`HudPanels` 兩處）傳 `"below"`；`floatCard.ts` 註解列出例外。實測 1600、800 都開在下方，不碰主角卡 | `uie3c_float_skill_1600`／`_800`；`uiE3c.test.ts` 5 個 |
| 6 出口雙框、多一條線 | 完成 | 滑過出口格時不再畫白框（`hoverFrameCell`），只留綠框；白框的下緣原本壓在下一格綠框上緣。下一格裡那條短直線經對照是**石板縫**（沒滑過時也在，`uie3c_exit_nohover_1600_zoom`），不是多畫的線 | `uie3c_exit_hover_*_zoom`；`uiE4.test.ts` |
| 7 「往」後面不空格 | 完成 | `exitLabel` 改成「往渡口石階」；小地圖說明一起改 | `uie3c_exit_hover_*_zoom`；`uiE4.test.ts`、`fieldModel.test.ts` |
| 8 確認框標題列固定 | 完成 | `.world-bag-screen > .world-quest-head` 改 sticky（不透明底、z-index 5：蓋在上緣漸隱上、在「×」下） | `uie3c_bag_cross_confirm_800_dev`（捲到底仍看得到標題列） |
| 9 說明牌蓋住名字 | 完成 | 雇用圖示列的 `<Hint>` 改 `prefer="below"`。實測說明牌在圖示下方、不碰名字（會蓋到下一位頭像的上緣，不蓋名字） | `uie3c_hire_hover_1600_zoom`、`_800` |
| 10 已勾選列深藍 | 完成 | `rgba(61, 90, 153, 0.45)`＋1px `#5878c0` 內框（主要按鈕色系），不再用金色 10% | `uie3b_hire_*`、`uie3c_hire_hover_*` |
| 11 名字小牌 | 完成 | `tileLines`：`Intl.Segmenter` 斷詞，每行 ≤ 3 字、≤ 2 行、不拆詞（「小／回復藥」「霧青／染料」）；個數在小牌外、不壓框 | `uie3c_bag_gear_1600_dev_zoom`；`uiE3.test.ts` 2 個 |

## 3. 截圖（19 張；jpg 80、單張 ≤ 170 KB；尺寸已核對）

無頭 Chrome（CDP，`--mute-audio`）。`_dev` 是開發頁拍的，其餘是正式遊戲（`/?dev=1&mute=1`，開發模式入口進同一個正式 `WorldScreen`）。

`docs/art/shots/uie3b/`
- `uie3b_encounter_1600.jpg`、`_1600_zoom`、`_800`、`_800_zoom`：正式遊戲，渡口石階走進盜賊視野的遇敵卡（3 名一般敵人）。
- `uie3b_encounter_boss_1600_dev.jpg`、`_1600_dev_zoom`、`_800_dev`：開發頁 `story-gallery.html#encounter-boss`，霧鎖真人（Boss 金環＋外光）＋劍陣弟子×2＋陣眼石靈（異形）。
- `uie3b_hire_1600.jpg`、`_800`：正式遊戲，霧渡鎮地點面板 → 雇用隊友；技能圖示列用 `skill_ids`，已勾選列深藍。

`docs/art/shots/uie3c/`
- `uie3c_hire_hover_1600_zoom.jpg`、`uie3c_hire_hover_800.jpg`：滑過已勾選傭兵（賽倫）的圖示，說明牌在下方（9、10；800 是 1）。
- `uie3c_skills_1600_zoom.jpg`：技能面板，花費行換行不以「・」開頭、換裝標題有空隙（2、4）。
- `uie3c_float_skill_1600.jpg`、`_800`：技能卡開在下方，不蓋主角卡（5）。
- `uie3c_bag_gear_1600_dev_zoom.jpg`：背包格子，橘點左上、名字小牌斷詞、個數不壓框（3、11；開發頁 `#bag-full`）。
- `uie3c_bag_cross_confirm_800_dev.jpg`：800 寬捲到底，標題列固定（8；開發頁 `#bag-confirm`）。
- `uie3c_exit_hover_1600_zoom.jpg`、`_800_zoom`、`uie3c_exit_nohover_1600_zoom.jpg`：霧渡鎮東出口，滑過只有綠框、「往渡口石階」；沒滑過的對照圖看得到同一條石板縫（6、7）。

精英（非 Boss）的金環實機與開發頁都沒有現成資料，沒有另拍；和 Boss 同一條 CSS，`uiE3b.test.ts` 有測框的樣式。

## 4. 驗收

- 浮動卡 6.5.1 實測（正式遊戲技能面板的技能卡，1600×900 與 800×600）：滑過開卡（開在下方）→ 從觸發元素直線滑進卡片仍開著 → 展開「詳細」→ 捲到底 → 點一下釘住（按鈕 `aria-pressed`）→ 滑鼠離開仍開著 → Esc 關閉，兩個尺寸全過。這張卡展開後高 260px，兩個尺寸都放得下，**沒有超出、不需捲動**（捲動行為由 `floatCard.test.ts` 覆蓋）。
- 排版煙霧檢查（`/?dev=1&anim=0.1&mute=1`，每個尺寸先 `localStorage.clear()`，`runCase`）：1600×900、1040×624、800×600 各 13 項全 PASS。
- 前端：全量 vitest 269 檔、3076 個測試全過；`pnpm -C client typecheck`、`pnpm -C client build` 結束碼 0。
- Python（這次沒改 Python）：`tests/api` 的 encounter look、openapi 快照、party、shadow，`tests/world` 的 encounters、party、shadows，加 `test_architecture`，`-n 4` 共 85 passed；`ruff check`、`ruff format --check`、`mypy src`（546 檔無錯）、`lint-imports`（14 kept）全部 0。

## 5. 待 PM 決定

1. **6.5.1 例外多一處**：除了 PM 已同意的技能面板 `SkillTile`（小修 5），小修 9 的雇用面板技能圖示說明牌也改成 `prefer="below"`（往上開一定會蓋到傭兵名字：名字和圖示之間只有約 27px，說明牌 36px 高）。已寫進 `floatCard.ts` 註解與 `PartyPanel.tsx`。代價是說明牌會蓋到下一位傭兵頭像的上緣（不蓋名字）。若不同意，替代做法是拉開每列的上下間距。
2. **小修 6 那條線**：查證是石板地磚本身的縫，不是程式多畫的線；這次只拿掉了白框。若美術 PM 仍覺得綠框裡的縫太明顯，要改的是出口格綠框的填色不透明度（目前 12%），請美術 PM 決定。
3. **頭像裁法（原型數值）**：人形取上半身 62%、異形整隻；頭像 36px。照最保守的預設先做，請美術 PM 看截圖決定。
4. 遇敵卡的 Boss 標籤從「精英」改寫「Boss」（`elite` 欄位照舊為真，只改顯示字）。
5. `bagGrid.tileName` 已沒有正式碼在用（只剩舊測試），留著沒刪；要不要刪下一段順手處理。

## 6. 程序

啟動過：`uv run trpg serve --port 8127`（`TRPG_DEV_ROUTES=1`、存檔在 scratchpad）、vite 開發伺服器 5187（暫時設定檔轉 8127，已刪、沒有 commit）、無頭 Chrome（CDP 9333）。都已用自己的 PID 關掉，8127／5187／9333 沒有程序在聽。沒有用 8000、8001。
