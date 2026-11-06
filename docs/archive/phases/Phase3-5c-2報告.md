# Phase 3-5c-2 報告：介面小修

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| `3d54714` feat(api) | `GET /api/battles/{id}/skill-reasons`、工坊說明文字過濾（`api/player_text.py`）、`/api/builds` 加 `max_mana`、`/api/skills/{id}?battle_id=`、工坊試玩可選 Boss 地圖、OpenAPI／`schema.d.ts` 重產 |
| （第二個 feat(client)） | 灰掉技能的原因（tooltip＋點擊顯示）、`useSkillCards` 帶 `battle_id`、紫色圖例、試玩法力比對與 Boss 地圖標示 |
| （本報告） | docs |

做法說明：

- **灰掉原因（選擇新增輕量端點）**：`skill_reasons(state, hero_id)`（`src/trpg/api/skill_reasons.py`）。對每個沒有合法動作的主角技能：被動技 → 「被動技能：條件成立時自動生效，不能主動施放」；否則先問引擎的 `skill_problem`（AP、法力、冷卻、沉默、源力……）；資源都夠但無選取時，依距離由近到遠試敵方單位，取 `checked_area` 的拒絕理由（「視線被阻擋」「目標超出射程」……）；試不出來給「目前沒有合法目標」。端點只讀、不推進戰鬥。前端 `useSkillReasons` 在輪到主角時查一次；本地端能判斷的（冷卻、源力、已啟動）保留，只有「通用說明」會被伺服器原因取代。灰掉的按鈕改為 `aria-disabled`，滑過顯示 tooltip，點擊在訊息列（沿用錯誤橫幅）顯示「技能名不能用：原因」。
- **工坊說明文字**：選擇 API 層過濾（不改原語定義）。`/api/workshop/options` 回傳前，對 `description_zh`／`notes_zh`／`problems` 刪除 `Phase …`；程式識別字（含底線、點、斜線）換成同一份選項或內容庫的中文名（狀態、物件、反應、層數、元素、地形、欄位名、選項名），查不到的整段括號刪掉或單詞刪掉。
- **`/api/skills/{id}?battle_id=`**：內容庫沒有時查該場戰鬥規則包（`setup.ruleset.skills`），再查進行中各輪。前端戰鬥頁的 `useSkillCards(ids, battleId)` 帶入，重新整理後名稱正確。
- **Boss 地圖**：`playable_maps(include_boss=…)`；只有帶 `custom_skills` 的建立請求（工坊試玩）可用 Boss 地圖，一般開戰仍 422；`/api/workshop/arena` 把 Boss 地圖排在一般地圖之後，下拉選單標「（Boss 地圖）」。
- **圖例**：`battle/legend.ts`；複合技能的兩段選取中，或預覽含第二段範圍時，戰場下方顯示三個色塊（可選落點／目標、第一段影響、第二段範圍＝紫色）。

## 2. 驗收條件

| # | 條件 | 結果與證據 |
|---|---|---|
| 1 | 灰掉技能有原因（vitest＋API 測試） | 通過。API：`tests/api/test_skill_reasons_api.py`（`test_every_gray_skill_has_a_reason_and_legal_ones_have_none`、`test_reasons_name_the_missing_resource`〔冷卻、法力、AP〕、`test_out_of_reach_target_is_explained`、`test_reasons_are_empty_when_it_is_not_the_heros_turn`）。vitest：`src/battle/polish3c5c2.test.ts` 的 `gray skill reasons`。 |
| 2 | 工坊說明文字掃描測試 | 通過。`tests/api/test_player_text.py::test_workshop_texts_have_no_phase_numbers_or_identifiers`（三條手走路徑＋每個骨架的隨機技能，各截去後段共約數十份草稿，掃 `name_zh`／`description_zh`／`notes_zh`／`problems`）；`test_the_scan_catches_the_raw_texts` 證明未過濾的原文會被掃出。 |
| 3 | `/api/builds` 有法力上限、`/api/skills/{id}` 查得到戰鬥內自訂技能 | 通過。`test_builds_report_max_mana`、`test_battle_skill_card_lookup_finds_custom_skills`。 |
| 4 | 工坊試玩可選 `bandit_lair` | 通過。`test_workshop_arena_offers_the_boss_map`（arena 列出、`/api/maps` 不列、帶自訂技能開戰 201）。 |
| 5 | 紫色圖例 | 通過（vitest `battlefield legend`）；畫面未在瀏覽器實測（見第 6 節）。 |
| 6 | `pnpm build` 成功、`check.py` 全過 | 通過。`pnpm build` 成功（僅 chunk 大小警告，既有）；`uv run python scripts/check.py` 全部通過（vitest 223）。 |

## 3. noqa

src 沒有新增任何 noqa（複雜度類皆無）。測試新增 2 個：`test_player_text.py` 的 `PLC0415`（函式內匯入）與 `BLE001`（掃描時略過組不出隨機技能的骨架）。

## 4. 修改既有測試期望值

無。

## 5. 待 PM 決定

1. 點擊灰掉技能的原因沿用錯誤橫幅（紅色、可關閉）顯示，沒有另做訊息列；要不要換成較中性的提示樣式。
2. 工坊說明過濾是機械式（換名或刪除），少數句子會讀起來略斷（例如保留的英文欄位字 `affects`、`by`、`landing`）。根治需要原語定義加 `player_description`（內容工作量大），建議 Phase 4 前做。
3. 被動技在戰鬥技能列的原因現在是「被動技能：條件成立時自動生效，不能主動施放」（取代通用的「沒有合法目標」）。
4. Boss 地圖只對「帶自訂技能」的開戰開放（工坊試玩）；一般 `POST /api/battles` 選 Boss 地圖仍 422。
5. `skill-reasons` 在輪到主角、每個回應各查一次（不快取）；成本是每次多一個輕量請求。
6. 工坊試玩的法力比對現在在選 build 時就顯示（用 `max_mana`，是未分配屬性點的基礎值）；進戰鬥後的 `manaWarning` 仍保留。
7. 圖例只在複合技能（兩段選取或預覽含第二段）出現，其他顏色（炸彈、召喚等）未納入。
8. `schema.d.ts`／`openapi.json` 與 3-5c-1 同時修改，合併時請重新執行 `export_openapi.py` 與 `pnpm gen:api`（只新增型別 `SkillReasons`、`BuildSummary.max_mana`）。

## 6. 代表性輸出節錄與手動驗收建議

說明過濾前後：

```
RAW: 爆骰（Phase 3D-7b）：擲到最大值再加擲一次，每顆骰最多再擲 core.explode_max 次；只能填 true
NEW: 爆骰：擲到最大值再加擲一次，每顆骰最多再擲 核心規則的設定值 次；只能填 true
```

瀏覽器建議步驟：

1. 首頁開戰，把石柱擋在主角與敵人之間，滑過／點擊灰掉的技能，應看到「視線被阻擋」「目標超出射程」「法力不足」等原因。
2. 工坊組一個法力代價 8 的技能，切換 build，「裝上試玩」面板應顯示「法力上限 X，技能需要 8」；地圖選單最後有「盜賊巢穴（Boss 地圖）」，可試玩。
3. 試玩中重新整理戰鬥頁，技能名稱不應退回 ID。
4. 在工坊展開各骨架與原語，說明文字不應出現 `Phase` 或底線英文。
5. 裝上瞬影旋斬類複合技能進戰鬥，選技能後戰場下方出現三色圖例，紫色＝第二段。
