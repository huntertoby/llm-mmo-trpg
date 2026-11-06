# Phase 3K-2b 報告：戰後三選一小修（玩法決定 #49 回覆）

規格：`docs/phases/Phase3K計畫.md` 3K-2b 第 1～3 點。

## 做了什麼

### 1. 換主手武器的提示
- 後端 `roguelite/gear.py` 新 `weapon_swap_prompt`：換主手後主角的武器縮放屬性集合（主、次屬性）和目前武器 **不同** 才回傳「這把看〔屬性〕，你目前最高的是〔屬性〕」（最高＝有效屬性，並列取六屬性順序第一個）；屬性相同、或不是換主手武器為 `None`。`GearCandidateOut` 新欄位 `weapon_swap_zh`（OpenAPI 已重匯、`gen:api` 已重產）。
- 前端新 `ui/gear/WeaponSwapConfirm.tsx`（排在按鈕列位置的內嵌確認區，不是彈出層，不涉及浮動卡）：「這把看敏捷、力量，你目前最高的是智力。要把主手換成「優良匕首」嗎？」＋「換上」「不換」。三選一（`RunGearOffer`）與營火背包（`BackpackSection`）都接上；選別張卡會取消確認。屬性相同直接換。文字全為繁體中文。

### 2. 預算分數加入整件物品強度
- `content/item_gen.yaml` 新 `base_strength`：武器＝基礎傷害平均（骰平均＋固定傷害，乘打擊數）× 傷害單位價（8.21.2 表「傷害 1 點＝1」）；防具＝基礎防禦 × 3 點（防禦值 +2%＝3 點），身體依造型 id 取 08 8.12 表（布袍 1、外套 2、皮甲 3、鎖甲 5、板甲 7），頭／手／腳小防禦 1，副手、項鍊、戒指 0。
- `content/item_budget.py` 新 `item_base_points`、`item_strength`（＝詞條點數＋基礎加成＋基礎強度）；**預算檢查（`item_points`、70% 填滿）不變**。`roguelite.gear.item_score` 改用 `item_strength`，所以 API 的 `points`、比較行、`auto_gear_pick` 都跟著變。基礎武器 `base_<武器>` 不再是 0（單手劍 4.5）。
- 存檔／紀錄格式沒改（`trpg-run/6`、`LOG_FORMAT` 不變）。

## 驗證
- pytest：`tests/roguelite tests/content tests/api tests/narrative`（含新增 2 個測試）通過；`-m "slow or not slow" tests/cli` 148 passed（CLI 快照與 `run auto` 種子測試 **不需更新**，沒有寫死挑選結果）。engine 沒動。
- ruff、format、mypy（711 檔）、lint-imports（7 kept）通過；vitest 990 passed（新增 1）；`pnpm build` 通過。
- **內建瀏覽器實測**（埠 8029，已關）：用腳本做的存檔（單手劍，三選一候選＝優良匕首、優良矛、優良戒指）。卡片比較顯示「目前：單手劍 預算分數 4.5 → 14.5（+10）」（矛 → 17.5（+13））。選匕首按「換上「優良匕首」」→ 出現確認區：「這把看敏捷、力量，你目前最高的是智力。要把主手換成「優良匕首」嗎？」＋換上／不換；按「不換」回到按鈕列；選矛（同看力量）按換上 **直接換上**、進下一步，武器欄變矛、背包 1 件。營火背包使用同一元件，未另外實測。

## 待 PM 決定
1. 防具基礎防禦的 3 點／級、身體造型表、頭手腳 1 級都是初值（08 8.12 的數字是相對初值）；武器單位價 1 點／傷害，使基礎武器分數（約 3～8）遠小於詞條預算（等級 1 主手約 12），所以仍是詞條主導，要放大請調 `base_strength.weapon_damage`。
2. 測試物品（items.yaml）若無 `kind` 的身體防具基礎分為 0。
3. AI 仍不換武器（保守），分數變化只影響其他部位與同武器不同詞條的選擇。
