# Phase 5D-3 完成報告：鐵匠與附魔台

> 規格：`docs/phases/Phase5計畫.md` 第 30 節（本段新增時是第 28 節；合併 main 後 5E-1、5E-2 佔了第 28、29 節，本段改成第 30 節，佔位節順延成第 31 節）。分支 `worktree-agent-a506e9f0dd780ea0e`。
> 內容依 `docs/design/20-第一季商店與裝備內容.md` 20.3、20.4（優先）、18.2.4、19.2.4、08 8.9、8.13～8.15、8.20、8.26；數值與文字都在 `content/`，被改時只動資料。

## 1. 交付

| 項目 | 內容 | 主要檔案 |
|---|---|---|
| 規格 | 第 30 節「5D-3 詳細規格」（範圍、規則、代決 5D3-1～12、驗收） | `docs/phases/Phase5計畫.md` |
| 內容 | `crafting.yaml`：霧渡鎮的石記鐵鋪（石師傅）與渡口附魔台、打造費用與用量、11 種特色材料的傾向（M2）與共鳴關鍵字、3 個隱藏配方、強化／重骰／指定／分解；`resonance.yaml`：7 個關鍵字的 2 件共鳴；`items.yaml` 加精華與荒原 3 種材料（熔岩核、寒燼、熔心晶，只定義）；`affixes.yaml` 加 3 條獨特詞條；`item_gen.yaml` 加 `unique_affixes`（不進一般產生器）；人設卡與聊天加石師傅 | `content/world/`、`content/affixes.yaml`、`content/item_gen.yaml`、`src/trpg/content/world_crafting.py`（新）、`library.py`、`item_budget.py` |
| 產生器 | `generate_item(..., forced=, leanings=)`：指定第 1 條 build 詞條（放不下就報錯）、材料傾向加權；不給時逐位元相同。新增 `affix_choices`／`pick_affix`／`replace_affix`（重骰與指定的候選：同稀有度類別、相容、放得進剩餘預算） | `src/trpg/content/item_gen.py` |
| 世界動作 | `craft`（欄位或配方碼）、`enhance`、`salvage`（鐵匠）、`reroll`、`imbue`（附魔台）；配方指紋 SHA-256、配方碼＝前 10 碼、打造亂數只由指紋衍生；`WorldState.recipes` 記首位發現者（M6）；`CharacterState.gear_mods`、`crafts`；賣裝備時一併刪改動紀錄 | `src/trpg/world/crafting.py`、`crafting_actions.py`（新）、`state.py`、`step.py`、`actions.py`、`economy.py` |
| 共鳴（M3） | 物品關鍵字＝技能強化詞條＋`resonance_<關鍵字>` 標籤；主角開戰時同關鍵字 ≥2 件 → 在帶該關鍵字的一件上加共鳴詞條（過穿戴驗證）；只改開戰快照 | `src/trpg/world/resonance.py`（新）、`gear.py` |
| API | `WorldActionRequest` 加 5 個動作；`WorldView.crafting`（設施、部位與詞條、稀有度費用、材料傾向、已知配方與首位發現者、可強化／分解／重骰／指定的裝備與原因）；`InventoryView.resonance_zh`；事件句子；OpenAPI 與前端型別重產 | `src/trpg/api/world_crafting_view.py`、`world_crafting_schemas.py`（新）、`world_schemas.py`、`world_presenter.py`、`world_economy_schemas.py` |
| 前端（最小） | 小鎮服務列「鐵匠」切換：打造表單（部位、稀有度、詞條、通用料、特色材料勾選、費用與傾向）、已發現的配方（照配方打造）、每件裝備的強化／分解、附魔台的重骰與指定；停用原因用共用 `<Hint>`；背包面板加共鳴一行 | `client/src/world/SmithyPanel.tsx`、`crafting.ts`（新）、`WorldPanel.tsx`、`EconomyPanel.tsx`、`client/src/api/types.ts` |
| 測試 | `tests/content/test_world_crafting.py`、`tests/world/test_crafting.py`、`tests/world/test_resonance.py`、`tests/api/test_world_crafting_api.py`、vitest `crafting.test.ts`；既有測試的詞條數 66→69、NPC 數 8→9 | — |

## 2. 版本與確定性

- 新欄位都有預設值（`CharacterState.gear_mods`／`crafts`、`WorldState.recipes`、`InventoryView.resonance_zh`、`ItemGenRules.unique_affixes`），`trpg-char/1`／`trpg-world/1`／`trpg-wlog/1` 不升版號；引擎、`LOG_FORMAT` 沒改。
- 打造：`Rng(指紋前 8 位元組)`；重骰：`SHA-256(指紋:位置:n)`。不耗角色亂數、不讀時間、不呼叫 LLM。同配方不同角色打出同一件（有測試）。
- 共鳴會讓穿 2 件同關鍵字裝備的角色開戰快照多一條詞條；舊日誌在新程式重播時，若當時已穿這類裝備，戰鬥會不同（同 5D-1、5D-2 的情況；格式沒變）。

## 3. 代決（規格 30.9；開發 PM 定，最保守預設）

| # | 事項 | 代決 |
|---|---|---|
| 5D3-1 | 鐵匠是誰、在哪 | 18、20 沒寫：霧渡鎮加最小人設卡「石師傅」（含聊天傳聞與祕密）；附魔台是同鎮的設施，沒有 NPC |
| 5D3-2 | 打造的稀有度 | 稀有或史詩；史詩另收任務幣 2（8.15 高階打造） |
| 5D3-3 | 防具的「1 條關鍵字詞條」 | 技能強化詞條掛不上防具，照 item_gen 的 build 詞條規則改用條件數值／防守型觸發 |
| 5D3-4 | 材料組合與用量 | 1 種通用料（主手 3、身體 2、其餘 1）＋0～3 種特色材料各 1；金幣 稀有 10／史詩 20 × 物品等級 |
| 5D3-5 | 傾向（M2） | 特色材料的傾向詞條權重 ×4（是偏向，不是限制） |
| 5D3-6 | 重骰後能不能用配方碼復刻 | 配方碼只含基礎配方；重骰序列在日誌與 `gear_mods` |
| 5D3-7 | 隱藏配方條件 | 部位相同＋特色材料組合完全相同；玩家選的詞條換成獨特詞條；固定史詩 |
| 5D3-8 | 共鳴 | 只算主角；效果是現成詞條；同一件不能有兩條同 ID，所以多數共鳴備一條「最大 HP +8」 |
| 5D3-9 | 獨特效果 | 「自身周圍」＝自己腳下 1 格；蒸汽護腕「被火攻擊時」先用「受到傷害時」 |
| 5D3-10 | 強化 | 每級基礎加成 +2%（武器傷害、其他防禦），不算進物品預算；材料＝物品等級對應的通用料 × 目標等級 |
| 5D3-11 | 亂數 | 用配方指紋衍生的亂數（8.20 要求同配方同結果），不用角色的串流 |
| 5D3-12 | 首位發現者 | 世界快照記角色 ID 與名字；不給稱號、不給獎勵 |
| — | 重骰、指定、分解費用 | 重骰 精華 1＋金幣 20＋20×已改次數；指定 精華 3＋金幣 60＋20×次數；分解 普通／優良 1、稀有 2、史詩 3 精華 |

## 4. 待 PM 決定

1. **小部位放不下 build 詞條**：戒指的詞條預算在物品等級 4 以下只有 4～7 點，技能強化（8 點）與觸發（8.4 點）放不下，打造會被拒絕（訊息「詞條預算放不下指定的詞條」）。冰火雙生戒要物品等級 ≥6（精料＋角色 6 級）。要不要讓打造在這種情況下照 8.22「每條至少 2 點」下修，或放寬戒指的比例。
2. **蒸汽護腕「被火攻擊時」**：要精確需要引擎的觸發加元素篩選（`TriggerAffix` 多一個欄位、`on_damaged` 傳元素）；「自身周圍」3×3 也要觸發效果支援範圍形狀。兩者都是引擎改動，本段沒做。
3. **重骰過的裝備分享**（8.20「配方＝基礎配方＋重骰序列」）：目前配方碼只含基礎配方。
4. **共鳴的效果與預算**：7 個共鳴的詞條與數值是開發 PM 定的初值，不計入物品預算（8.9 說「計入預算」）；4 件門檻留正式季。傭兵、影子沒有共鳴。
5. **強化不計預算**：+3 等於傷害／防禦 +6%，沒有跑模擬。
6. **費用與用量**全部是初值，沒有跑模擬（守則：不跑大型模擬）。
7. **另外兩個隱藏配方的提示**（餘燼集酒館與傳聞）與荒原材料的掉落：等灰燼荒原內容段。驚雷霧袍的提示已在霧渡鎮酒館（既有內容）。
8. **石師傅的人設卡**請玩法 PM 補完或換人；09 9.6.1 說鐵匠與附魔台在主城，主城還沒做，先放霧渡鎮。
9. LLM 命名與外觀綁定配方（8.20）尚未做：名稱是「稀有度＋底材名」，隱藏配方用固定名稱；名稱在配方第一次打造時記進世界。
10. 合併 main 時看到 20.2 新增的 5D-2 代決（補潮濕、隱蔽的技能強化詞條）：補上後會自動出現在打造的詞條選單，不用改程式。

## 5. 檢查（最後一次合併 main〔含 5E-1、5E-2〕之後）

- `ruff check .`、`ruff format --check .`、`mypy`（1133 檔）、`lint-imports`（11 契約）通過。
- `tests/world tests/api tests/content`（`-n 8`）：2963 通過（含修正後的 `test_gear_api`）；另跑 `tests/roguelite tests/test_architecture.py` 236 通過、`tests/engine -k "gear or affix or trigger"` 323 通過。
- vitest 132 檔 1244 通過；`npm run build`（含 `tsc --noEmit`）通過。
- swamp 種子 7 重播：88 個動作、313 個事件，最終狀態一致。
- OpenAPI 重產（`scripts/export_openapi.py` → `pnpm gen:api`）；合併 main 後再產一次沒有差異。
- 沒做瀏覽器實測：面板是最小版（完整畫面在 5D-4），vitest 有靜態輸出與停用原因的測試，API 測試走完打造 → 照配方碼打造 → 強化 → 分解 → 重骰。
- 沒有新增 `# noqa` 的複雜度例外（測試裡一個 `PLR0917` 是 pytest 參數化）。
