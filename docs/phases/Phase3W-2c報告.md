# Phase 3W-2c 完成報告：修正 3W-2b 的 3 個偏離點

> 實作者：implementer。依據：`docs/design/06-技能.md` 6.34（`f4ebd945`）。分支：`worktree-agent-a8e268c6e58b1df98`（從 main `f4ebd945` 起），**未 push**。

## 1. Commit 列表

| commit | 內容 |
|---|---|
| `1eb0f7da` | 雷霆架勢：拿掉致盲 +1 回合，改為「命中站在水上的目標時再多一點雷電傷害」 |
| `230e1ebb` | 指定類別不跨類補；新增 `category_counts`（每類合法變化數） |
| `b210a4eb` | 護盾橋接「帶電」（破盾電擊攻擊者）＋ 重產前端／圖示 fixture |
| （本報告） | `docs/phases/Phase3W-2c報告.md` |

## 2. 做了什麼

1. **雷霆架勢**
   - `StatusDef.element_dealt_wet_permille`（預設 1000，需搭配 `element_dealt`）：目標腳下是水時，該元素傷害再乘這個倍率。引擎 `damage_dealt_permille(..., on_water=)` 由傷害結算（`_dealt_permille`）傳入目標格是否為水。
   - 雷霆架勢 1～5 級：水上加成 +5／7.5／10／12.5／15%（疊在原本的 +10～30% 之上）；原本的 `status_duration_bonus: {blinded: 1}` 移除。`budget_points` 不變（15／17／19／22／28），所以預算窗與階梯不動。
   - 卡片（`status_rules`）多一句「目標站在水上時，雷電傷害再 ×N%」，說明文字也改了。
2. **指定類別不跨類補**
   - `make_offer` 指定類別時不再呼叫 `_fill_up`：只出該類，不到選項數就少出；0 個時照舊拋 `ValueError`（「沒有合格的變化」，不扣點）。不指定類別維持從任何類別補滿。
   - 新純函式 `skillgen.flash.category_counts(library, request, source=None) -> dict[類別, 數量]`：每個可指定類別目前的合法變化數，最多算到指定類別出題的選項數（玩家實際看到的數量）；`allow_focus` 關閉時回空表。目前後端沒有「選類別」的 API／請求驗證（3W-6 才接），所以 openapi 與 TS 型別沒有變（已跑 `export_openapi.py`，無差異）。
3. **護盾橋接「帶電」**
   - `StatusDef.shield_break_lightning`（0～10）＋新狀態 `shielded_charged`（帶電護盾，3 點雷電、預算 2 點，沿用 3W-2b 的 `shield_riders` 機制，不新增狀態種類）；破盾時對打破它的敵方攻擊者造成固定雷電傷害，到期不電。
   - 模板 `shield_charged`（橋接，關鍵字 `charged`）；`skill_keywords.yaml` 的「帶電」加上 `shield: shielded_charged`，所以橋接後技能真的帶「帶電」關鍵字。
   - 新模板欄位 `needs_held`：`shield_charged` 設為 true，**持有者其他技能沒有雷電（`charged`）關鍵字時不出現**；潮濕／標記橋接維持原樣（不需要持有，只是持有越多越優先）。
   - 前端：`statusIcon.ts` 加 `shielded_charged` 圖樣（盾＋閃電），狀態數 95 → 96。

## 3. 驗收證據

- 行為一致測試
  - 雷霆：`tests/engine/test_stance_upkeep_3w2b.py`（5 級都沒有致盲加成、水上倍率 > 乾地 > 1000、別的元素不受影響、實戰傷害水上 ≥ 乾地且有至少一個種子更高）；`tests/skillgen/test_flash_stance_3w2b.py`（卡片數字＝引擎倍率含水上句、水上加成逐級遞增且 ≤ +20%；原有的預算窗／強度下限測試照常通過）。
  - 類別：`tests/skillgen/test_flash_fill_3w2b.py`（指定類別的每個選項都屬該類、數量＝`category_counts`、少出與滿出兩種情況都測到；0 個的類別被拒絕；不指定仍可跨類）。原本「指定類別也補滿」的斷言已改掉。
  - 帶電：`tests/skillgen/test_flash_shield_3w2b.py`（3 階級過驗證器、預算窗、強度下限，橋接帶 `charged` 關鍵字；沒持有雷電不出、持有時出且排第一；實戰破盾電擊 1 次、元素雷電、沒打破不電）。
- 檢查：`ruff check`、`ruff format --check`、`mypy`（827 檔）、`lint-imports`（7 kept）全過。
- pytest（皆 `-m "(slow or not slow) and not llm" -n 8`）：`tests/skillgen content narrative api test_architecture engine llm roguelite sim` 9216 通過（跑完後唯一失敗是技能圖示 fixture 過期，已用 `python -m tests.narrative.icon_fixture` 重產並重跑 `tests/narrative` 通過）；`tests/cli --timeout=3000`：424 通過、1 xfail（3W-fix 已標）。
- 前端：vitest 1158 全過、`tsc --noEmit` 通過。fixture 以 `scripts/export_client_fixtures.py` 重產（glossary 含新狀態與新說明）。
- 沒有新事件或紀錄結構，**不遞增 `LOG_FORMAT`**。沒跑 `scripts/check.py`、沒跑大型模擬。

## 4. 待 PM 決定

1. **雷霆水上加成的幅度（+5～15%）是我的初值**：照「多一點」配，沒動 `budget_points`（沒有另外折算水上條件的價值）。需要的話請玩法 PM／平衡階段調整。
2. **「持有雷電關鍵字才出現」的實作解讀**：指令同時寫「持有雷電時才出現」與「比照標記／潮濕寫法」，而標記／潮濕其實是一直都出現、只是排序。我讓帶電 **只在持有者持有 `charged` 才出現**（新欄位 `needs_held`）；若要改成和另兩個一樣永遠出現（只排序），把 `flash_templates.yaml` 的 `needs_held: true` 拿掉即可。注意：持有判斷用的是 `held_keywords`（持有者其他技能的關鍵字分布）。LLM 提議的變化仍走 `try_variation`，不檢查 `needs_held`（保守，與 3W-2b 其他橋接一致）。
3. **指定類別時的「轉型」保底**：大變化指定類別時，3W-2b 的轉型保底選項（#70「有合法轉型時一定出現」）我沒有動，仍會附在指定類別的選項後面（類別是 `transform`，不計入 `category_counts`）。設計文字「玩家付 2 點買的是這一類，不能出現別類」若要連轉型也排除，需玩法 PM 明確說明（與 #70 有衝突）。
4. **`category_counts` 的上限**：最多算到指定類別出題的選項數（目前 3）。3W-6 若要顯示更大的數字或「0 個不可選」之外的資訊，改 `cap` 即可。
5. **3W-2b 待決 #2 的其他元素小特色**（毒素／風／神聖／暗影／物理仍是「持續 +1 回合」）本次沒動。
