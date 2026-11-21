# Phase HC-4d 計畫：大世界的預設值搬進 content（HC-4 收尾）

> 來源：`docs/phases/寫死數值-清單.md` HC-4 節 d 項；`docs/開發PM交接.md` 現況（「HC-4d 世界（含 content 時段表，前端 hud 鐘點改讀）」）；HC-4c 報告的開發 PM 裁定。
> 原則：**結果不變**。只換數字放的地方，數值不變。做法照 HC-4a～HC-4c 的計畫與報告。

## 範圍

1. **大世界搬家**。`src/trpg/content/` 底下的 config todo：
   - `world_rules.py` 55、`fields.py` 31、`world_season.py` 12、`world_trade.py` 11、`world_situations.py` 9、`world_economy.py` 8
   - `world_crafting.py`、`roguelite.py` 各 6
   - `world_quests.py`、`world.py` 各 5
   - `races.py` 4
   - `world_newcomer.py`、`world_mercenaries.py`、`world_loot.py` 各 3
   - `world_oaths.py`、`world_narration.py`、`world_map.py`、`world_events.py`、`world_encounters.py` 各 2

   **搬法**：
   - content 的 schema 預設值：內容檔有寫的，拿掉程式預設值、改成必填。沒寫的，先把值寫進 content，再改成必填。
   - 「有某欄才用到」的欄位：可以省略，用到時才必填。
   - 遊戲規則型的上下限：搬進 content 的規則檔，在載入層驗證。
   - 世界規則的數字改了，`WORLD_RULES_VERSION` 要不要升：照 `src/trpg/world/save.py` 常數下的說明判斷。這段只換數字放的地方、數值不變，預設不升，並在報告寫理由。
2. **時段表**：`client/src/world/hud.ts` 237～239 行的 24、11、18、21（規則 `ts-day-phase-hours`）。
   - 後端 content 新增時段表，寫上早、午、晚、夜的起始鐘點，值照現在前端用的。
   - 經 API 帶給前端，`hud.ts` 改讀 API，不再寫死。
   - 後端若已有判斷 `day_phase` 的鐘點（例如世界時鐘），要和這張表一致：能共用同一張就共用；不能共用就加對照驗證。
   - API 改了就重產 OpenAPI 和 `client/src/api/schema.d.ts`。
3. **其餘 content 尾巴**（HC-4 全部清完）：
   - `skills/specs.py` 5、`skills/skill.py` 3、`enemy_moves.py` 3、`skill_triggers.py` 2
   - `stacks.py`、`skills/reactions.py`、`skills/conditions.py`、`skill_scaling.py`、`rule_changes.py`、`maps.py` 各 1

   搬法同第 1 項。純結構常數照分類規則改判 const 或 guard，附上理由。
4. **開進工坊**：
   - 搬進 content 的世界數值（經濟、交易、季節、委託等）照現有工坊分組放。沒有合適的表才新開，並寫理由。
   - 每格要有中文名稱，說明寫清楚調高、調低的效果。
   - 數量多、意思相近的可以只開代表性的幾格，其餘列在報告。
5. **收尾**：搬完後變成 0 筆的規則直接刪掉（照 HC-4c 的前例）。刪完後，沒歸類的筆數要是 0。

## 不做

- `skillgen/` 的常數留給 HC-5，包括 `skill_pick.py` 的 `thin_reasons`。
- text 類留給 HC-6。
- `world/*`、`engine/*`、`api/*` 的模組常數留給 HC-7。這段只做 `src/trpg/content/` 和 hud 時段。
- 不動 `docs/design/`、`config/`、`llm.toml`。不改任何數值。

## 驗收

- **比對**（對照基準 commit）：
  - 434 招逐招預算 different=0。
  - 78 場戰鬥 different=0，`ruleset_hash` 除外。
  - parity、CLI 快照不變。
  - **世界不變**：用固定種子跑小樣本，前後逐位元組比對 different=0。要跑兩組：
    - 世界生成（地圖、地區、場地），加上幾天的世界推進（經濟、交易、季節、委託）；
    - roguelite 開局。
    - 可以用既有的 world 測試工具或 `trpg` CLI。腳本放在 scratch，用法和結果寫進報告。
  - 前端 hud：同樣的鐘點，顯示的字（早／午／晚／夜）和圖示前後相同。用 vitest 驗證。
- **靜態檢查**：ruff、format、mypy、lint-imports、`trpg content check`、`classify.py --check` 都要是 0。
- **測試一律經看門狗**：
  - 開發中只跑相關測試：`uv run python scripts/run_pytest.py -q <路徑> -n 8`。
  - **交件前一次跑完全部非 slow 測試**：`uv run python scripts/run_pytest.py -q tests -n 8`（2026-11-21 使用者：「改成一次跑完」）。
  - 再跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
  - 前端：tsc、vitest、build 結束碼都要是 0。
- **快照、夾具**：先預測會變的地方，再逐鍵核對，不整批重產。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseHC-4d報告.md`，要附：
  - config todo 剩幾筆（HC-4c 之後是 554）；
  - `src/trpg/content/` 剩幾筆，目標是 0；
  - 新開的工坊欄位。
