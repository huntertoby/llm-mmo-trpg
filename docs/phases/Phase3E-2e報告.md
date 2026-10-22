# Phase 3E-2e 報告｜glossary API 與前端對照表

規格：`docs/phases/Phase3E計畫.md` 3.1 表的 3E-2e 列。分支 `worktree-agent-a11bbc0dd265b6572`（基於 5826670），未 push。

## 做了什麼

### 後端（內容即資料）

- **原語 `player_description`**：`PrimitiveDef` 新增選填欄位；`content/skill_primitives.yaml` 48 個原語全部補上一句給玩家看的說明（不含階段編號與程式識別字）。測試 `tests/content/test_player_description.py` 要求出貨原語一律要有；glossary 在欄位缺漏時退回 `description_zh`。
- **反應事件名稱**：`content/reactions.yaml` 新增 `events:`（12 個 `ReactionWhen.event` 的中文名與說明；`ReactionTable.events`、`ReactionEventDef`）；`tests/api/test_glossary_names.py` 檢查每個事件都有一列。
- **glossary API**：`Glossary` 新增 `effects`（原語；說明用 `player_description`，tag 為分類）、`conditions`、`triggers`（被動觸發＋反應事件）、`weapon_looks`（有 `look` 的武器）。皆有預設空值。
- **武器外觀**：`WeaponDef.look`（`WeaponLook`：kind、material、element、form）寫在 `content/weapons.yaml` 的 14 把武器；雙手與否沿用 `two_handed`。
- **英雄與單位外觀**：`UnitTemplate.doll`（`DollLook`：膚色、髮型、頭身手腳披風與副手、主手材質覆寫、稀有度外光）寫在 12 個單位範本檔；`UnitState.doll`（純顯示、`clone` 已帶）→ `UnitView.doll_look`，做法同 `SummonLookView`。
- **`FieldSpec` 旗標**：`card`（用卡片排列）與 `object_choice`（值是 `{type: ...}` 物件）為 `computed_field`，由欄位路徑末段推導（表在 `trpg.skillgen.option_models` 的 `CARD_FIELDS`／`OBJECT_CHOICE_FIELDS`）；寫入時忽略這兩個鍵，序列化再讀回不會壞。
- **前端測試快照**：`scripts/export_client_fixtures.py` 重產 `client/src/battle/fixtures/glossary.json`（原本已落後內容，一併更新）與 `client/src/render/fixtures/unitDolls.json`；`tests/api/test_client_fixtures.py` 檢查沒有過期。

### 前端

刪掉的寫死表：

| 檔案 | 刪除項 |
|---|---|
| `client/src/render/skillParts.ts` | `EFFECT_NAMES`、`CONDITION_NAMES`、`TRIGGER_NAMES` |
| `client/src/render/appearance.ts` | `WEAPON_LOOKS`、`APPEARANCES`、`ITEMS`、`SLOT_OF`、`build()` |
| `client/src/ui/workshop/FieldEditor.tsx` | `CARD_FIELDS`、`lastSegment`、依欄位名 `skeleton` 的徽章判斷 |
| `client/src/workshop/draft.ts` | `OBJECT_CHOICE_FIELDS` |

- 效果、條件、觸發的名稱與說明改讀 glossary（`effectName`／`conditionName`／`triggerName`／`glossaryDescription`）；找不到 ID 時顯示 ID，不壞。圖示畫法（`EFFECT`、`COND`、`TRIG` 等）留在前端，以 ID 查找並有 `?` 退回。
- 部件新增 `description`，浮動說明（`partTip`）顯示「分類：玩家說明」，補上審查指出「說明框只有分類字」。
- `weaponLook()` 讀 glossary 的武器外觀，沒有時依武器大類退回；`resolveDoll` 讀 `DollInput.dollLook`（來自 `UnitView.doll_look`），沒有時依陣營／召喚物退回。`drawModel`、`unitSprite`、殘影分身複製都已串好。
- 測試改用 `render/testDolls.ts`（`resolveDollT`）從 `unitDolls.json` 補外觀；新增 `glossaryNames.test.ts`，驗證「新增原語、武器、外觀只改 glossary／資料，不改前端即可顯示」。

## 驗收

- 新增原語或武器：只需在 `skill_primitives.yaml`（名稱、`player_description`）或 `weapons.yaml`（`look`）加一列，前端就顯示中文名與預設外觀（`glossaryNames.test.ts` 的 `brand_new`、`mystery_blade` 案例）。
- 相關檢查全過：`ruff check`、`ruff format --check`、`mypy`（261 檔）、`lint-imports`（6 kept）；`pytest`：`tests/content`、`tests/api`、`tests/skillgen`、`tests/roguelite`、`tests/cli`、`tests/test_architecture.py`、`tests/test_primitive_coverage.py`、`tests/engine/test_state_clone.py`、`tests/engine/test_view.py`；前端 `vitest` 73 檔 766 個測試、`typecheck`、`build`。未跑完整 `scripts/check.py`（依指示）。
- 瀏覽器實測（自己起的 8123 埠伺服器，已關閉）：開新一輪選火焰法杖、進第 1 場，我方主角、弓手隊友、鳶盾戰士隊友、敵方盜賊與弓手的紙娃娃與武器圖示正常；技能卡的部件名稱（傷害類、召喚、形狀、狀態）與說明框正常，效果原語說明框顯示「效果原語：在指定的格子召喚一個替你戰鬥的召喚物。」；工坊首頁骨架卡片與「非主動技」徽章正常。

## 待 PM 決定

1. **條件 `on_own_rune` 中文名**：前端舊字串為「目標站在自己的符文上」，YAML 為「站在自己的符文上」；以 YAML 為唯一來源，技能卡部件上的名稱因此少了「目標」兩字（工坊本來就顯示 YAML 名）。要統一成哪個？
2. **武器外觀走 glossary、單位外觀走單位視圖**：武器圖示也用在戰鬥以外（一輪英雄面板、起始選擇），所以武器 `look` 放 glossary 啟動載入；單位 `doll_look` 照 `SummonLookView` 放單位視圖。如要武器也放視圖欄位，可另加。
3. **hero_* 範本名在實測的戰鬥中不會出現**：實測（`build_fire`、一輪）玩家英雄的範本 ID 是 `build_*`，原本前端 `APPEARANCES` 的 `hero_fighter` 等只在其他路徑用到；這次保持原行為（有 `doll` 的範本才有外觀，英雄仍退回陣營預設）。要讓玩家英雄也有專屬外觀需另做決定（屬美術／玩法）。
4. **其餘前端寫死表未動**：`COST_LABEL`、`TAG_NAMES`、`LINK` 名稱、`TERRAIN`／`OBJECTS` 色塊等不在本段指定範圍；審查 4 點提到的 `skillParts.ts:1034`、`:1290` 屬於代價與標籤名，建議併入下一個前端整理。
5. **`FieldSpec` 旗標的判斷表仍是欄位名清單**（現在在後端 `option_models.py`，不再在前端）；若要完全資料驅動，需在每個 `FieldSpec(...)` 建立處明確傳旗標。
6. **殘影分身找不到召喚者時**的退回外觀由「戰士預設外觀」改為「陣營預設」（極少見的邊界情形）；`ruleset_hash` 因內容檔變更而改變，舊存檔會被判定為過期（開發期可接受）。
