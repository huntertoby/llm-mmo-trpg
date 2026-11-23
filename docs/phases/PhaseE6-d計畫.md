# Phase E6-d 計畫｜併第 10 步招牌內容、打開招牌與傳說開關

規則：`docs/design/` 08 8.27、8.30（#180，使用者「全部照建議」）。玩法 PM 的第 10 步內容（50 條招牌、5 條限傳說專屬、30 招新技能、5 條新改寫規則）在分支 `worktree-agent-a5191cef93c4bc9c3`（最後 commit 0a397e494），報告 `docs/phases/第10步-招牌內容報告.md`（併進來後就在這個路徑），**先讀第 3、4、7、8 節和附錄 A**。

這段之後，掉落、打造、傭兵與一輪的結果**照預期會變**；不是「結果不變」段。

## 0. 起點

在自己的 worktree（從 main 開）先 `git merge --no-edit worktree-agent-a5191cef93c4bc9c3`。main 上比內容分支多了 QF-7 和玩法 PM 的平衡待查第 44 條；有衝突就停下回報。

## 1. 要做的事

1. **打造指定詞條的招牌計價**（玩法答覆待決 3，8.30 第 9 點）：`src/trpg/content/item_gen.py` 的 `forced` 詞條若是招牌詞條，照 60% 計價（和招牌路徑同一套），不再照類別固定點數。這條**不看** `signature_enabled`（隱藏配方的獨特裝備本來就該能打）。
2. **貼回附錄 A**：3 條獨特詞條（`affix_unique_thunder_mist`、`affix_unique_steam_guard`、`affix_unique_frostfire`）照附錄 A 改成招牌版本，3 招技能放進 `content/skills/`。部位照配方原本的部位（玩法答覆待決 4：蒸汽護腕在手、冰火雙生戒在戒指可以帶招牌；8.27「頭手戒指不帶」只管產生器掉落與打造，不管隱藏配方的獨特裝備）。三個隱藏配方都要打得出來（`tests/world/test_crafting.py`）。附錄 A 的註解也要拿掉。
3. **裝備授予的技能不進玩家技能池**（待決 10）：`src/trpg/content/player_pool.py` 的 `player_skills` 排除 `gear` 標籤；閃現不會挑到。第 10 步測試裡「先排除 gear」的寫法（`tests/skillgen/test_flash_templates.py`、`test_flash_bal10b.py`）改成依賴正式規則，加一個 `player_skills` 不含 gear 技能的測試。
4. **(ag) 內容檢查**：限傳說詞條（`legendary_only: true`）必須標五種招牌之一（`signature` 有值；改寫規則也是標 `signature: rule`）。違反時 `trpg content check` 失敗並寫出詞條 id。加測試。
5. **打開兩個開關**：`signature_enabled`、`legendary_enabled` 在內容的 `item_gen.yaml`（或其實際所在處）設成 true。依 `docs/dev/` 上手筆記判斷要不要升 WORLD_RULES_VERSION（現 38）、LOG_FORMAT（現 /139）、存檔或規則包版本；有升就寫進報告並說理由。
6. **測試**：開關打開後失敗的測試，若只是「寫死開關關著」的掉落／打造結果，改成新結果並在報告逐檔列出；若是真的壞掉，修程式。不要為了讓測試過而改 `docs/design/` 或既有 `config/` 值。

## 2. 審查第 10 步的測試改動

玩法 PM 那邊把 65 處「內容沒有招牌」改成用 `tests/signature_baseline.py`（第 10 步之前的白名單）。請看一遍，確認：機制測試確實還在測原本的機制（不是變成空測試）；`test_signature_content_step10.py` 真的檢查到真實內容。有問題就修並列在報告。

## 3. 比對（基準：起點的 main，合併內容分支之前）

照往例跑，但這段**預期會有差異**，報告要說明每項差異是不是開關或新內容造成的：

- 442 招預算 cmp：**舊的 442 招**結果要不變（新 30 招 ＋ 附錄 A 3 招另列）。
- compare78（78 場）：預期不變或只因規則包內容雜湊不同；若戰鬥事件有差，找出原因寫進報告。
- census 204 格：同上。
- 物品產生器種子比對（`scratchpad/e6a1/gen_seed.py` 的做法）、世界掉落種子（`scratchpad/e6c2/loot_seed.py` 的做法）：預期會變，報告列出變化的大概（多少件帶招牌、多少件傳說、有沒有出在頭／手／戒指的招牌——後者應為 0）。
- 舊配方代碼：不變。

不跑模擬、不量平衡；數值疑慮記在報告第「平衡疑慮」節（玩法 PM 已記平衡待查第 44 條，不重複）。

## 4. 交件

- 全部 commit 後跑 `uv run python scripts/check.py --all`，加上 slow（`tests/skillgen/test_refactor_parity.py`、`tests/cli`，`-n 8`）、`corepack pnpm -C client build`。結束碼都要 0。
- `skill_icons.json` 等夾具若要重產，照錯誤訊息重產並列在報告。
- 報告 `docs/phases/PhaseE6-d報告.md`：commit 列表、結束碼表、比對結果與差異說明、版本號有沒有升、待 PM 決定。
- 截圖：開發頁或實機能看到一件帶招牌的稀有／史詩物品、一件傳說物品的物品卡各一張，800 寬，存 `docs/art/shots/e6-d/`（瀏覽器靜音；不用 8000、8001 埠；只用 PID 關自己開的程序）。
