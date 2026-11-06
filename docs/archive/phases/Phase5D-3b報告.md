# Phase 5D-3b 完成報告：5D-3 收尾（配方碼帶重骰序列、石師傅、荒原隱藏配方提示、爐叔）

> 範圍：`docs/phases/Phase5計畫.md` 第 1 節 5D-3b 列（沒有另開詳細規格節）。分支 `worktree-agent-acb78ad536376f785`。
> 依據：08 8.20（#33 使用者寫入的決定：「配方 ＝ 基礎配方＋重骰序列，所以重骰過的裝備也能被復刻」）、18 18.5（石師傅）、19 19.5（爐叔）、20 20.3、20.4；5D-3 規格第 30 節與報告。

## 1. 交付

| 項目 | 內容 | 主要檔案 |
|---|---|---|
| 配方＝基礎配方＋重骰序列（#33） | `RecipeStep {index, affix}`（`affix` 是 `None`＝重骰，否則＝精華指定）。打造品每重骰／指定一次：序列記進 `GearMod.steps`，算出帶序列的配方碼 `variant`＝SHA-256(`{"base": 基礎指紋, "steps": [...]}`) 前 10 碼，世界沒有這個碼就記一份 `RecipeRecord`（`base`＝基礎配方碼、`steps`＝序列、首位發現者＝改的人）。用帶序列的碼打造：先打基礎配方，再照序列重骰與指定（亂數仍是「基礎指紋＋位置＋n」，所以結果和原裝備一樣），費用照付（基礎打造費＋每一步當時的重骰／指定費用，精華一併扣） | `src/trpg/world/state.py`、`src/trpg/world/crafting.py`、`src/trpg/world/crafting_actions.py` |
| 重骰與重現共用一個函式 | `_apply_step`：附魔台的重骰／指定與打造時照序列重現走同一段，避免兩邊規則分岔 | `src/trpg/world/crafting.py` |
| API 顯示 | 背包裝備的 `code` 顯示帶序列的碼（沒有時顯示基礎碼）；配方表的摘要多「重骰 n 次、指定 m 次（基礎配方 XXXXXXXXXX）」；重骰／指定的事件句子多「新的配方碼 …（含重骰序列）」與首位發現者。API 型別沒變，OpenAPI 不用重產 | `src/trpg/api/world_crafting_view.py` |
| 石師傅人設卡（18.5） | 個性、說話方式、祕密、關係照玩法 PM 補的 18.5 改寫；聊天的中立傳聞與信賴祕密照新說話方式改寫（祕密＝「劍陣弟子落單最弱」，只是資訊） | `content/world/npcs/cloud_ridge.yaml`、`content/world/social/cloud_ridge.yaml` |
| 隱藏配方提示（20.4） | `HiddenRecipe.hints: [RecipeHint {source: tavern／rumor, region, location, place_zh, text_zh}]`；3 個隱藏配方都填上（驚雷霧袍＝霧渡鎮酒館；蒸汽護腕＝餘燼集酒館「霧與火相遇之處」；冰火雙生戒＝餘燼集傳聞「冰與火在同一隻蜥蜴身上」）。接口 `CraftingRules.hints_at(region, location?, source?)`；提示所在區域有地點圖才檢查地點 | `src/trpg/content/world_crafting.py`、`content/world/crafting.yaml` |
| 爐叔（19.5） | 荒原地點圖還沒到位：只放人設卡資料，不接店。`content/world/pending/ashen_waste.yaml`（schema 同 `NpcCardTable`，測試驗證；遊戲不載入） | `content/world/pending/ashen_waste.yaml` |
| 測試 | `tests/world/test_crafting_variants.py`（新，7 個）：重骰／指定記序列與首位發現者、別人用帶序列的碼打出同一件且費用照付、繼續重骰換新發現者、基礎碼照舊、舊格式紀錄不產生碼、世界快照往返、精華不夠不能打；`tests/content/test_world_crafting.py` 加提示與待接人設卡 3 個；`tests/api/test_world_crafting_api.py` 加重骰後的新配方碼 → 用它打造 → 同一件 | — |

## 2. 版本與相容（舊碼、舊存檔）

- **配方碼格式沒變**：仍是 10 碼十六進位；帶序列的碼和基礎碼放在同一張世界配方表，打造時只查表。舊的基礎配方碼的指紋算法沒改（序列空時 `variant_print` 直接回傳基礎指紋），所以舊碼照常能讀、照常打出同一件。
- 新欄位都有預設值：`GearMod.steps`／`variant`、`RecipeRecord.base`／`steps`、`AffixChangedEvent.code`／`discovered`、`HiddenRecipe.hints`。`trpg-char/1`／`trpg-world/1`／`trpg-wlog/1`、`LOG_FORMAT` 都不升版號（同 5D-1～5D-3 的慣例）。
- **5D-3 舊存檔裡已重骰過的裝備**：舊紀錄只有 `rerolls`（位置）與 `imbues`（次數），沒有指定成哪一條、也沒有重骰與指定的先後，序列無法還原。保守做法：`GearMod.traceable`（打造品且 `len(steps) == changes`）為假時，照常可以重骰／指定，但不產生帶序列的配方碼（事件 `code` 為 `None`，裝備顯示原本的基礎碼）。
- 確定性：打造與重現都只用配方指紋衍生的亂數，不耗角色亂數；相同輸入同結果（測試比對整個 `StepResult`）。swamp 種子 7 重播一致。

## 3. 代決（最保守預設）

| # | 事項 | 代決 |
|---|---|---|
| 5D3b-1 | 帶序列的配方什麼時候進世界配方表 | 每次重骰或指定打造品就記一份（中間每一步都是一件真的出現過的裝備）；首位發現者＝做這次重骰／指定的人。配方表因此會變長（每一步一筆） |
| 5D3b-2 | 強化要不要記進配方 | 不記。#33 只說重骰與精華指定；強化不是隨機、自己打好後可以再強化。所以「結果和原裝備一致」指詞條與數值，強化等級（`base_bonus_permille`）不含在內 |
| 5D3b-3 | 用帶序列的碼打造的費用 | 基礎打造費＋序列每一步「當時」的費用（第 i 步用 `gold(i)`，和原裝備改的時候一樣越改越貴）；精華一起扣；任務幣只算基礎打造 |
| 5D3b-4 | 在哪裡打帶序列的配方 | 鐵匠，且同一地點要有附魔台（重骰本來在附魔台做）；霧渡鎮兩個都有 |
| 5D3b-5 | 餘燼集的 ID | 地點 `ember_market`、爐叔 `smith_lu` 是開發 PM 暫定；荒原地點圖用別的 ID 時改資料即可 |
| 5D3b-6 | 序列在目前內容下重現不了（例如詞條表改過） | 不能打，訊息「這份配方的重骰序列在目前的內容下重現不了（原因）」，狀態不變 |
| 5D3b-7 | 石師傅聊天文字 | 照 18.5 的說話方式（短句、「嗯」）重寫中立傳聞與信賴祕密；文字是開發 PM 寫的 |
| 5D3b-8 | 驚雷霧袍的提示 | 也在 `hints` 記一筆（霧渡鎮酒館）；畫面上仍由既有的酒館傳聞與事件 4 的線頭顯示，沒有重複接 |

## 4. 待 PM 決定

1. **荒原內容段要接的東西**：(a) 把 `content/world/pending/ashen_waste.yaml` 的爐叔搬到 `world/npcs/ashen_waste.yaml`，在 `crafting.yaml` 加餘燼集的鐵匠與附魔台（店名 19、20 沒寫）；(b) 餘燼集酒館與傳聞接 `CraftingRules.hints_at("ashen_waste", ...)`（酒館的傳聞池目前在 `world/social/<region>.yaml` 的 `rumors`，提示要變成傳聞池的一則，還是另開「配方提示」一行，由荒原段定）；(c) 確認地點 ID。
2. **配方表會變長**（代決 5D3b-1）：每一步重骰都是一筆。要不要改成「只有裝備被分享（例如玩家按『公開配方』）時才記」，或配方表只列每件裝備最新的一筆。
3. **強化要不要也進配方**（代決 5D3b-2）。
4. **舊存檔的已重骰裝備**不能產生帶序列的碼（序列無法還原）；目前試玩存檔若有這類裝備，影響只有「不能分享改過的版本」。
5. 帶序列的碼打造要求同地點有附魔台（代決 5D3b-4）；主城或其他城鎮只有鐵匠時會打不了，之後若有這種配置要再定。

## 5. 檢查（合併 main〔含 5D-2b〕之後）

- `ruff check .`、`ruff format --check .`、`mypy`（1150 檔）、`lint-imports`（11 契約）通過。
- `tests/world tests/api tests/content`（`-n 8`）：3034 通過。
- swamp 種子 7 重播：88 個動作、313 個事件，最終狀態一致。
- 沒改前端與 API 型別：不跑 vitest／build、不重產 OpenAPI。
- 沒有新增 `# noqa`；`crafting_problems` 分支數超標，拆出 `_hidden_problems`。
