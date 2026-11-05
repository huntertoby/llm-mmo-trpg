# Phase UI-E3b（＋UI-E3c 追加）進度報告（WIP，中途收尾）

實作者，2026-11-05。使用者要重開電腦，依 PM 指示中途收尾。這份是**未完成**的進度紀錄。

## UI-E3b 已完成（commit `5b26c348`）

- 伺服器 `EncounterEnemyView` 加兩個顯示用欄位：
  - `rank`：`normal`／`elite`／`boss`。範本帶 `boss` 標籤的是 `boss`；精英範本或套了詞綴的是 `elite`。
  - `look`：`FieldHeroView`，格式同地圖人物。照開戰時的範本（已套詞綴）與裝備（`UnitSpawn.equipment`）產生，所以每一名都有外觀，不只領頭那名。
  - 寫在 `world_presenter._encounter_enemy`。
- `MercenaryView.skill_ids`、`ShadowView.skill_ids`：和 `skills_zh` 同順序、同長度。
  - 影子的生成技能不在內容庫，`/api/skills/{id}` 查不到，前端要照舊寫字（前端還沒改，見下面）。
- 不改規則，不改存檔格式，不升 `WORLD_RULES_VERSION`。
- 已重產 `client/openapi.json`、`client/src/api/schema.d.ts`。
- 測試：
  - 新增 `tests/api/test_encounter_look_uie3b.py`，10 個測試：一般、精英、Boss 的階級，人形、異形、詞綴的外觀，API 每名都有外觀。
  - `test_world_party_api.py`：`skill_ids` 都查得到技能卡，名字一致。
  - `test_world_shadow_api.py`：`skill_ids` 和 `skills_zh` 長度相同。
- 結束碼（commit 前）：
  - `ruff check`、`ruff format --check`、`mypy src`（542 檔無錯）、`lint-imports`（13 kept）全部 0。
  - 相關 pytest 46 passed，含 openapi 快照與 `test_architecture`。
  - 重播：`swamp` 種子 7，88 個動作，最終狀態一致。

## UI-E3b 未完成

- 前端遇敵卡的頭像（戰場紙娃娃縮圖），以及精英、Boss 的金環。
- 前端雇用面板改用 `skill_ids`，拿掉 `hireSkills.ts` 用主題句和招名去對圖示的間接做法。
- 全部截圖（`uie3b_*`）、6.5.1 浮動卡實測、vitest、build、排版煙霧檢查。

## UI-E3c（美術 PM 退回，`docs/art/UI-E3與UI-E4檢查.md`）

已 `git merge main`（`eac26b93`）。下面的改動在 WIP commit 裡，**vitest、build 都還沒跑，也沒拍截圖驗證**。

| # | 狀態 | 內容 |
|---|---|---|
| 1 hire 800 寬不一致 | 查到原因，還沒修 | 開發頁的 `Frame` 只在渲染時讀一次 `window.innerWidth`，改視窗大小後不會重算。所以 hover 那張是用舊尺寸的版面拍的。正式遊戲的 `WorldHud` 會重算。修法：`Frame` 跟著 resize 重新渲染，並補上「X」；能的話改在正式遊戲拍 |
| 2 花費行開頭「・」 | 已改（未驗） | `skillCost.costPiecesTrailing` 把「・」留在上一行尾；`CostLine` 加 `trailingSep`，只有 `SkillTile` 用。戰鬥底列不變 |
| 3 橘點蓋角標 | 已改（未驗） | `.world-bag-cell.cross::after` 從右上移到左上 |
| 4 換裝標題空隙 | 已改（未驗） | `LoadoutEditor` 的標題後面加全形空白 |
| 5 技能卡蓋主角卡 | 做一半 | `floatPlacement` 加了 `prefer` 參數（預設 `above`，行為不變）。還沒接到 `FloatCard`，`SkillTile` 也還沒用 `prefer="below"` |
| 6 出口雙框、多一條線 | 未做 | |
| 7 「往」後面不空格 | 未做 | |
| 8 確認框標題列固定 | 未做 | |
| 9 說明牌蓋住名字 | 未做 | |
| 10 已勾選列改深藍 | 未做 | |
| 11 名字小牌 | 已改（未驗） | 新的 `bagGrid.tileLines` 用 `Intl.Segmenter` 斷詞：每行最多 3 字、最多 2 行，不拆詞（「小／回復藥」「霧青／染料」）。小牌靠上，個數放在小牌下方，不壓框。`uiE3.test.ts` 還沒加 `tileLines` 的測試 |

## 下一步

1. 先跑 `corepack pnpm -C client exec vitest run`，再跑 build，修好壞掉的測試。可能受影響：`uiE3.test.ts`、`fix6f7`／`fix6f8`、LoadoutEditor 相關快照。
2. 補 `tileLines`、`costPiecesTrailing`、`floatPlacement prefer` 的測試。
3. 做完 UI-E3c 的 1、5～10。
4. 做 UI-E3b 前端：遇敵卡縮圖、金環，雇用面板改用 `skill_ids`，影子能查到卡就畫圖示。
5. 拍截圖：`uie3b_*`、`uie3c_*`，1600×900、800×600 各附 `_zoom`；開發頁拍的要標明。跑 6.5.1 實測與排版煙霧檢查。

## 待 PM 決定

- 5：技能面板的技能卡改成優先開在下方（`prefer="below"`）。這和 6.5.1「預設上方」不同，1600 寬也會一起改。
- Boss 遇敵卡實機到不了，打算在開發頁用 dev-boss 戰鬥的單位外觀畫出來。

## 程序

這段沒有啟動任何伺服器、vite 或瀏覽器。只跑過前景與背景的 pytest／mypy，都已結束。沒有用 8000、8001、8010。
