# Phase OB-3｜#150：OB-2 後續、#148 換示範招、免費重選、閃現 4 級限制、配點教學

> 來源：`docs/design/21-探索地圖與城鎮.md` 21.5（#150 共 9 點含「OB-2 補充」、#134 工坊靶場的示範招段，**以它為準**）、`docs/玩法決定紀錄.md` #148、#150。前置：OB-1、OB-2（報告 `docs/phases/PhaseOB-1報告.md`、`PhaseOB-2報告.md`，後者第 5 節的待決已由玩法 PM 定，結論在 21.5「OB-2 補充」）。
> 盤點：共用筆記 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_1dc515fa-6fa4-4841-956e-bdff26ae2844\盤點-150與147.md` 第 1.0、1.1（第 5、6 點與「接著教配點」列）、4.3 節；#148 核對數字在 `...\local_c2d54362-e4f7-4f75-b1dd-07933f64c2aa\核對-148示範招B案.md`。

## PM 決定（不要再問）

| 項目 | 決定 |
|---|---|
| 兩組延後三選一不得重複 | **選完第 1 組才出第 2 組**（和不延後時的出題規則一致，第 2 組排除已擁有的招）；若這樣改動過大，可改成第 2 組裡與第 1 組選走的招相同的那張換掉，報告說明 |
| 推薦關鍵字 | 找不到能互相觸發的第 2 個就只標 1 個；照玩家**當下選的那把武器**算 → 新增帶武器的查詢端點，`RangeView` 既有欄位保留 |
| 背包滿拒絕選定／重選 | 回應要帶玩家看得懂的原因（繁體中文） |
| 入門招辨識 | 維持讀 `range.demos`，不加欄位 |
| 4 級前 | 一律看等級；到 4 級把 `opening` 清成 `None`（重選過期、溶掉與傳承解鎖） |
| 重選邊界 | 照 21.5 第 9 點「重選的邊界」；HP、法力回滿 |
| 版號 | 行為改變就把 `WORLD_RULES_VERSION` 加一（只加一次）；`CHAR_FORMAT` 只有加存檔欄位才動，報告說明 |

## 範圍外

- OB-4 戰鬥閘與入門期活動限制（另一個 agent 平行在做：`world/field_enemies.py`、節點遭遇、事件戰鬥、雇傭兵、聯賽、賽季 Boss、誓約、換技能）——**不要碰這些檔案**。
- OB-5／6 前端畫面與台詞；本段前端只重產 `client/openapi.json`、`schema.d.ts` 並讓 typecheck、相關 vitest 過。
- 不動 `src/trpg/engine/`、`src/trpg/roguelite/`；不調任何技能數值。

## 交付項目（照順序，每項一個 commit）

**A. OB-2 後續與 #148**

1. **#148 換示範招**：`content/world/newcomer.yaml` 的 demos 與註解改成近戰 `skill_shadow_backstab`＋`skill_wild_blade`、遠程 `skill_rng_venom_arrow`＋`skill_oil_spark_throw`、法器不變；`tests/world/test_opening.py` 的 `DEMOS_148` 同步；燧石飛刃在靶場示範卡片的說明加一句「靶場的油桶打破會流出油」（放在示範招的資料或靶場內容，不改技能本體說明；找不到合適欄位就加在 `range` 內容並由 API 帶出，報告說明）。新增資料測試：示範招不得有 `weapon_only`，也不得有要特定武器或副手才生效的條件。
2. **兩組三選一不重複**：照上表；補測試（實際跑世界動作，含兩組候選有交集的種子）。
3. **拒絕原因**：背包放不下時的拒絕訊息；補測試。
4. **帶武器的推薦查詢**：新端點（或既有靶場端點加參數），輸入武器、回推薦關鍵字（0～2 個）；只在可正式選定或可重選時回應；有快取。補 API 測試。
5. **回報用**：換招後三大類（各取入門武器與另外至少 2 把）推薦得出哪些關鍵字，列表寫進報告。

**B. OB-3 本體**

6. **免費重選**：新動作 `opening_reselect {weapon, keywords}`。條件：已正式選定、`char.level < 4`、沒用過、人在葛蘭所在城鎮或主城、沒有進行中的遭遇。收回起始武器本體（已賣掉就不收回也不扣錢）、起始 2 招、第 1、2 步三選一拿到的招（裝備中與 `bench`、對應的 `generated_skills`、`flash`、`skill_usage`、`skill_regions`），依新選擇重給並重新出題，屬性全部重配，HP、法力回滿。玩家自己換上的裝備留在背包；背包放不下就拒絕並說明原因。花在起始武器上的強化材料不退：動作回應或檢視資料要列出會損失的強化（給前端確認用）。
7. **閃現 4 級限制**：`opening is not None` 的角色 4 級前不能閃現；第一次閃現的引導改到第 3 步打完回霧渡鎮；閃現的預先生成（`api/world_pregen.py`）在不能閃現時跳過；`api/world_growth_view.py` 的按鈕狀態與原因。靈感照常累積。
8. **配點教學**：正式選定後才出（已選定、沒上過）；略過與完成分開記錄，略過後第一次進城鎮或營火再提示（盤點 Q13）；入門期不出。
9. **4 級**：升到 4 級時把 `opening` 清成 `None`；之後重選被擋、溶掉與傳承恢復。4 級前溶掉、傳承一律擋（確認 OB-1／OB-2 是否已擋，沒有就補）。

## 受影響的既有功能

見盤點 4.3：`tests/world/test_first_flash.py`、`test_newcomer.py`、`test_flash_world.py`、`tests/api/test_world_pregen*.py`、`test_flash_api.py`、`test_range_api.py`、`test_newcomer_api.py`、`tests/world/test_dispatch.py`、`tests/narrative/test_events_text.py`；換示範招另影響 `tests/skillgen`（`test_exploit_starter_links.py` 等）、`tests/content/test_coverage.py`、`tests/roguelite` 固定種子（只有真的引用到示範招名單時才會變，變了要逐項說明）。所有新判斷以 `char.opening is not None` 為前提，舊角色與 roguelite 不變。

## 行為一致測試

- 表格測試，**實際跑世界動作**：三大類 × 正式選定 → 重選到另一大類：武器、招、點數、HP、法力正確；舊的起始招與三選一招全部收回（含已閃現紀錄不存在的確認）；重選只能一次；4 級後被擋。
- 邊界：起始武器已賣、已強化、背包滿、雙手武器與副手。
- 閃現：4 級前擋、4 級後可；預先生成在 4 級前不觸發（用 `MockLLMClient` 計數）。
- 舊角色（`opening is None`）的閃現、教學順序與改前相同。
- 世界日誌重播一條含選定、重選、升 4 級的完整流程。

## 驗收條件

- `ruff check`、`ruff format --check`、`uv run mypy`、`lint-imports` 通過。
- `tests/world`、`tests/api`、`tests/content`、`tests/narrative`、`tests/skillgen`、`tests/roguelite`、`tests/server`、`tests/test_architecture.py` 通過。`tests/api/test_world_dev_boss.py::test_dev_boss_rehearses_to_the_boss_charge` 是已知不穩定的測試，失敗時單獨重跑確認即可，不要改它。
- 前端：`corepack pnpm -C client typecheck` 通過；有改到的前端測試檔與 `src/render/inkDollSnapshot.test.ts`、`src/world/range.test.ts` 通過。
- 一場戰鬥 `--log-json` ＋ `replay` 通過。

## 報告

`docs/phases/PhaseOB-3報告.md`：逐條驗收、三大類的推薦關鍵字表、重選收回的順序與理由、版號、待 PM 決定。
