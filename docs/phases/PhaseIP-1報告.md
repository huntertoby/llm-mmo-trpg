# Phase IP-1 報告｜技能圖示道具 `icon_prop`（#151）

> 實作者 2026-11-12。規格 `docs/phases/PhaseIP-1計畫.md`；依據 06 6.36、#151、`docs/art/技能圖示道具清單.md`。
> 分支 `worktree-agent-ab052b031b9f62994`，從 `13652de7` 起，沒有 push。

## 1. 交付

| # | 交付 | 做了什麼 | 檔案 |
|---|---|---|---|
| 1 | schema、允許清單、資料檢查 | `SkillDef.icon_prop: str \| None`（`exclude_if` None，沒填的技能序列化不變）；允許清單 `content/skill_icon_props.yaml`（美術第 1 節 57 個值，每個值帶 `group` 與 `weapon_class`，沒有 `weapon_class`＝不限）＋ schema `IconPropTable`（ID 格式、不重複）；登記進 `KNOWN_CONTENT_FILES`；`load_library` 呼叫 `icon_prop_problems`（清單外、大類不符都拋 `ContentError`）；劇情技能填了也擋（只有 `content/skills/` 可填） | `src/trpg/content/skill_icon_props.py`、`content/skill_icon_props.yaml`、`src/trpg/content/skills/skill.py`、`src/trpg/content/library/skill_checks.py`、`load.py`、`src/trpg/content/registry.py` |
| 2 | 36 招填值 | 照美術第 2 節逐字，插在 `weapon_req` 下一行 | `content/skills/*.yaml`（36 檔） |
| 3 | LLM／白板輸入清洗（D3） | `drop_icon_prop()`（`trpg.content.skills`）：`evaluate_proposal` 解析 JSON 後先丟掉頂層 `icon_prop`（提議模型是 `extra=forbid`，不丟會報錯）；`proposal_from_skill` 不把它放進 few-shot 範例（否則有填的手寫技能會丟 `ValueError`）；`compose_whiteboard` 回傳前清成 `None`（配方的 `skill`／`vary` 是自由 dict，能帶進來）；工坊草稿 `build_skill` 與 `/api/workshop/check` 也丟掉（保守延伸，見待決 2） | `src/trpg/skillgen/proposal/evaluate.py`、`convert.py`、`whiteboard.py`、`draft.py`、`src/trpg/api/routes/workshop.py` |
| 4 | `icon_of()` 與 API（D5） | `SkillIcon.icon_prop`（`exclude_if` None）；`icon_of` 取字串值，非字串或空字串為 `None`；技能卡片、變奏卡片的 `icon` 跟著帶。`export_openapi.py` → `pnpm gen:api` 重產，並重產技能圖示快照與 `skillCards.json` | `src/trpg/narrative/skill_icon.py`、`client/openapi.json`、`client/src/api/schema.d.ts`、`client/src/render/fixtures/skill_icons.json`、`client/src/ui/fixtures/skillCards.json` |
| 5 | 行為一致與資料檢查測試 | 見第 2 節 | `tests/content/test_icon_prop_ip1.py`、`tests/content/test_icon_prop_battle_ip1.py`、`tests/skillgen/test_icon_prop_drop_ip1.py`、`tests/api/test_icon_prop_api_ip1.py` |
| 6 | 報告、上手文件 | 本檔；`docs/dev/上手-內容資料與模擬.md` 加清單檔、加技能第 8 步、digest 說明、測試對照，並更正「技能圖示快照由 `export_client_fixtures.py` 產生」的舊說法（實際是 `python -m tests.narrative.icon_fixture`） | |

前端畫法沒有改（`client/src/` 只有 `gen:api` 產物與兩個快照 JSON 變動）；`src/trpg/engine/`、`src/trpg/world/`、`src/trpg/api/world_range*` 沒有改動。

快照變動只有 `icon_prop` 一欄：`skill_icons.json` 的 402 招中 36 招多了 `icon_prop`，其餘欄位、隨機組合器 50 個種子、工坊示範逐步完全相同（腳本比對）；`skillCards.json` 只有一張卡（`w:fist`）多一欄。

## 2. 測試

| 測試 | 驗什麼 |
|---|---|
| `test_icon_prop_ip1.py::test_allow_list_has_the_57_values_of_the_art_list` | 57 個值、各組數量（17／5／2／10／12／10／1）、只有武器與副手有大類 |
| `test_icon_prop_ip1.py::test_icon_prop_check_table`（25 列） | 合法值；清單外（含大小寫不同）；大類不符（弓技能填劍、近戰填弓、近戰填杖）；`any` 技能填任何值（劍、弓、塔盾）；元素配近戰／遠程／法器；召喚、化身、拳套、飛刃、`none` 不限；副手：盾算近戰（遠程填鳶盾擋）、法書與法器珠算法器（近戰填法書、遠程填法器珠擋） |
| `test_icon_prop_ip1.py::test_every_filled_skill_is_in_the_list_and_matches_its_weapon_class` | 從內容讀：恰好 36 招有填，全部在清單內、大類對得上、`provenance.origin == builtin` |
| `test_icon_prop_ip1.py::test_skill_without_icon_prop_serializes_as_before` | 沒填的技能 `model_dump` 沒有這個鍵 |
| `test_icon_prop_ip1.py::test_story_skills_cannot_fill_icon_prop` | 劇情技能填了被擋 |
| `test_icon_prop_ip1.py::test_load_library_rejects_bad_icon_props`（2 列）、`test_load_library_accepts_any_prop_on_classless_skill` | 整份內容載入：清單外、弓技能填劍各拋 `ContentError`；`any` 技能填弓通過 |
| `test_icon_prop_battle_ip1.py::test_removing_icon_prop_gives_identical_battles`（36 列） | 每招裝在一個單位（敵人專用招裝敵方；限副手的堡壘突擊另裝圓盾），種子 1、2，原規則包 vs 拿掉全部 `icon_prop` 的規則包：步驟、事件、最終狀態逐筆相同（最終狀態內嵌規則包，比對前兩邊都換成拿掉後的版本） |
| `test_icon_prop_battle_ip1.py::test_identity_battles_actually_cast_icon_prop_skills` | 效用 AI 在這些場次至少放出 10 招（實測 11 招：其餘要條件、或是被動／修正型，不發 `SkillUsed`，但仍在規則包裡一起比對） |
| `test_icon_prop_battle_ip1.py::test_ruleset_hash_changes_but_replay_still_verifies` | 規則包雜湊因 `icon_prop` 不同；紀錄 `log_replay_problem` 為 `None`、`replay` 結果相同 |
| `test_icon_prop_drop_ip1.py`（5 項） | `drop_icon_prop` 只去該鍵且不改原 dict；LLM 提議帶 `icon_prop`（dict 與 JSON 字串、值是字串或數字）不報錯、結果和沒帶相同；few-shot 範例不帶；白板配方 `skill` 帶 `icon_prop` → 白板照樣組出、不帶、和原本相同（另手動確認拿掉清洗時這項會失敗）；工坊草稿與 `overrides` 帶了都丟掉 |
| `test_icon_prop_api_ip1.py`（5 項） | 每招 `skill_icon(s).icon_prop == s.icon_prop`；沒填的不輸出、改了只差這一欄；`icon_of` 對非字串、空字串回 `None`；技能卡片帶出；`/api/workshop/check` 送 `icon_prop` 結果和沒送相同 |

既有測試只改一處：`tests/skillgen/test_proposal.py::_same` 的比對多略過 `icon_prop`（提議往返依設計不帶它，`test_every_expressible_builtin_skill_round_trips` 原本會因此失敗）。

## 3. 驗收條件自我檢查

1. **交付 5 的測試全過；相關測試檔與 `tests/test_architecture.py` 過**：通過。一次跑（`-n 8`）：
   `tests/content/`：`test_icon_prop_ip1.py`、`test_icon_prop_battle_ip1.py`、`test_loader.py`、`test_coverage.py`、`test_skills_content.py`、`test_skill_scaling.py`、`test_skill_rules_content.py`、`test_enemy_only_skills.py`、`test_skill_same_name.py`、`test_ruleset_with_skills.py`；
   `tests/skillgen/`：`test_icon_prop_drop_ip1.py`、`test_enemy_only.py`、`test_proposal.py`、`test_proposal_coverage.py`、`test_llm_source.py`、`test_whiteboard.py`、`test_workshop_check.py`、`test_random_composer.py`；
   `tests/narrative/`：`test_skill_icon.py`、`test_card_text_scan.py`；
   `tests/api/`：`test_icon_prop_api_ip1.py`、`test_client_fixtures.py`、`test_openapi_snapshot.py`、`test_workshop_api.py`、`test_skill_card_stats.py`；
   `tests/test_primitive_coverage.py`、`tests/test_architecture.py`
   → **1265 passed, 13 skipped**（77 秒）。另 `tests/cli/test_skills_cli.py` 9 過。
   前端：`vitest run src/render/skillIcon.test.ts src/ui/skillCard.test.ts src/world/panelIcons.test.ts src/world/range.test.ts`（讀這兩個快照的檔）→ 4 檔 102 項全過。
2. **靜態檢查與內容、重播**：`ruff check .` 0、`ruff format --check .` 0（2348 檔）、`mypy` 0（1448 檔）、`lint-imports` 0（14 kept）、`trpg content check` 0（659 個檔、402 個技能）；`trpg battle --map open_plain --seed 7 --log-json …` 0、`trpg battle replay …` 0（「重播驗證通過：91 個動作、383 個事件，最終狀態一致」）；`corepack pnpm -C client typecheck` 0。
3. **`src/trpg/engine/` 沒有改動**：`git diff --stat 13652de7 -- src/trpg/engine/ src/trpg/world/ src/trpg/api/world_range.py` 輸出為空。（和本機 `main` 比會看到別段已合併的改動，所以用分支起點比。）
4. **版號**：`WORLD_RULES_VERSION`、`CHAR_FORMAT`、`LOG_FORMAT` 都沒動。理由：沒有改事件、動作、`BattleState`、`BattleLog` 的結構，也沒有改結算；`SkillDef` 加的是有預設值、`None` 時不輸出的欄位（`docs/dev/上手-引擎戰鬥結算.md` 三-5「`Ruleset` 加有預設值的欄位不加」）。

## 4. 內容 digest

規則包內嵌技能全文，所以三個雜湊都因 36 招的 `icon_prop` 改變（規格允許，寫明如下）。比對方式：同一份程式，「改前」用 `13652de7` 的 `content/` 加上新清單檔（舊技能沒有 `icon_prop`，序列化與舊程式相同）。

| 雜湊 | 改前 | 改後 |
|---|---|---|
| `hash_ruleset(library.ruleset)` | `87e041e05e41e510…` | `21d09310ae4fd46d…` |
| `ruleset_hash(library)`（roguelite 存檔） | `33f47e9a792418b6…` | `f668838d76c5fa4f…` |
| `content_digest(library)`（世界日誌） | `a5ad22641a4c4185…` | `e640db82aa06a319…` |

影響：使用者重開伺服器後，進行中的一輪會從頭開始、舊世界日誌標成不能重播（只改內容的正常行為）；舊戰鬥紀錄內嵌當時的規則包，照樣能重播。重播驗證不因 `icon_prop` 失敗（第 2 節最後一項測試、第 3 節的 CLI 重播）。

**請使用者重開伺服器檢查的重點**：技能卡片與戰鬥中的技能圖示跟以前一樣（前端本段不畫 `icon_prop`）；API 回傳的 `icon` 對 36 招多一欄 `icon_prop`。

## 5. 複雜度類 noqa

沒有新增。

## 6. 沒驗證

- 沒跑完整 `scripts/check.py`、沒跑模擬（規格不要求）。
- CLI 輸出快照（slow）跑了一次：`battle_default_flat_42` 一鍵不符，**不是本段造成**：同一份程式用改前與改後的內容各跑 `trpg battle --map test_heights_8x8 --seed 42`，輸出逐字相同；這個鍵最後重產是在 `b86fbab6`，之後 `27717975`（BAL-20，燃燒估值）改了 AI 表，BAL-20 報告第 6 節也寫了沒跑這份快照。本段沒有重產它（見待決 1）。其餘 23 鍵（含 `skills_list`、`skills_show_all` 各片）通過。
- 前端沒有實機看；本段不改畫法，只跑了讀快照的 vitest 與 typecheck。

## 7. 待 PM 決定

1. **CLI 快照 `battle_default_flat_42` 過期（BAL-20 遺留）**：要在 PM 全量時照慣例 `UPDATE_CLI_SNAPSHOTS=1 … -k battle_default_flat_42` 只重產這一鍵，或另排給 BAL-20 收尾。本段沒動。
2. **工坊草稿也丟掉 `icon_prop`（保守延伸）**：規格 D3 只寫 LLM 與白板；06 6.36 說「只有手寫技能填」，工坊草稿是玩家（開發工具）組的，所以 `build_skill` 與 `/api/workshop/check` 也一律丟掉、不報錯。若要讓工坊能試填圖示，再開。
3. **劇情技能（`world/quests/` 的 `story_skills`）填了直接擋**（不是丟掉）：它們是手寫內容檔、不在 `content/skills/`，照 D3 字面「只有 `content/skills/` 可填」處理成內容錯誤。若要開放，改成套同一套清單與大類檢查即可。
4. **從手寫技能衍生的技能保留 `icon_prop`**：升階（`_t<階>`）、變奏型態、進化、閃現等以手寫技能為底的複本會帶著原招的值（同一招的不同形態，圖應該相同）。只有 LLM 提議、白板、工坊三個入口清掉。若進化／閃現產物也該照推導畫，要再加清洗點。
5. **`icon_of` 不對照允許清單**：它是純函式、沒有內容庫；手寫內容在載入時已擋過，LLM／白板／工坊在入口清掉，所以執行期不會出現清單外的值。美術建議的「執行期遇到清單外的值靜默退回」留給之後畫 `icon_prop` 的前端段處理。
6. **化身招（`enter_form`）與 `wielding_weapon` 招填了也不生效**（美術清單第 0 節）：目前資料檢查不擋，36 招裡也沒有這兩類。要不要擋由 PM 定。
7. **雜湊因只影響顯示的欄位改變**：若想讓之後改圖示道具不再讓進行中的一輪重開、世界日誌變成不能重播，可以把 `icon_prop` 從內嵌規則包與 digest 排除（需要改 `Ruleset` 組裝或 digest 的取法，牽動較大）。本段照規格接受改變。
8. **美術清單筆誤**：第 1.4 節標題寫「元素道具（11）」，表內與合計都是 10 個；YAML 照表內 10 個。請轉美術 PM 修標題。
9. **允許清單 ID 格式**：schema 限定 `none` 或 `前綴:名稱[/形制]`，前綴只開 `w`、`el`、`summon`、`form`；美術之後若加新前綴，要同時改 `ICON_PROP_PATTERN`。
