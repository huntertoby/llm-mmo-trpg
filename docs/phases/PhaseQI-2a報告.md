# Phase QI-2a 報告｜Q 版技能圖示後端：推導表入 `content/`、`icon_of()` 加 `art`、API

> 實作者 2026-11-12。規格 `docs/phases/PhaseQI-2計畫.md`（第 0.0 節定稿、第 1 節 D1～D7）；需求 `docs/art/Q版小圖示-技能圖示移植需求.md` 3.3；參考實作 `docs/art/sample/tools/qskills_derive.py`。
> 分支 `worktree-agent-a958ccd6bdbfb3c76`，從 `8d457ec6` 起（`git merge --ff-only main`），沒有 push。

## 1. 做了什麼

| # | 交付 | 內容 | commit |
|---|---|---|---|
| A1 | 推導表 | `content/skill_icon_art.yaml`：參考實作 19 張表逐筆照抄、順序不變（`AREA_SHAPES` 沒用到不搬）；有優先順序的表是列表；`late_action` 的 `terrain` 列照抄，載入時換成 `surface`＋`tint: stone`。schema `src/trpg/content/skill_icon_art.py`（`IconArtTable`；出手 9、記號 23＋`terrain`、染色 13＋`stone` 用 `Literal` 封閉；道具代碼格式、ID 不重複、dot／bind／curse 不重疊、effect／late 原語不重疊）。登記 `KNOWN_CONTENT_FILES`；`load_library` 載入，`ContentLibrary` 新增 `icon_art` 與 `icon_props`（IP-1 的允許清單）。檔頭維護者寫「美術 PM」（06 6.36 已定，規格 D2 的「待定」已過時） | `0d4e1f0e` |
| A2 | D4 | `skill_checks.icon_prop_fixed_problem`：效果（含 `followup.effects`）有 `enter_form`、或任一效果條件 `wielding_weapon` 的招填 `icon_prop` → `icon_prop_problems` 回問題 → `load_library` 拋 `ContentError`。目前內容 0 招被擋 | `db2deaa2` |
| A3 | 推導 | 新 `src/trpg/narrative/skill_icon_art.py`：`IconArt`（`prop`、`motion`、`act`：`str`；`tint`、`spark`：`str \| None`，五欄必有）、`IconArtRules`（表＋允許清單的查表包裝，`build(table, props)`）、`icon_art_rules(library)`、`default_icon_art_rules()`（`functools.cache`，讀預設內容資料夾）、`derive_art(skill, rules=None, *, elements=None)`。`SkillIcon.art: IconArt \| None`（`exclude_if` None；`icon_of` 一律填）；`icon_of(skill, art=None)`、`skill_icon(skill, art=None)`。容錯取值 `_map`／`_seq`／`_text`／`_enum_text` 從 `skill_icon.py` 搬到 `skill_icon_art.py`（`skill_icon.py` 匯入，避免循環匯入；行為不變） | `d9b283d6` |
| A4 | 呼叫處 | `narrative/skills.py`（技能卡、變奏卡）、`api/routes/workshop.py::_check`、`tests/narrative/icon_fixture.py` 傳 `icon_art_rules(library)` | `d9b283d6` |
| A5 | 型別與快照 | `export_openapi.py` → `pnpm gen:api`；`python -m tests.narrative.icon_fixture`；`export_client_fixtures.py` | `802ce3d9` |
| A6 | 測試 | 第 2 節；改寫 `test_icon_prop_api_ip1.py` 一處 | `db2deaa2`、`d9b283d6`、`3edc122f` |
| A7 | 報告、上手筆記 | 本檔；`docs/dev/上手-內容資料與模擬.md`（第一節表、第二節第 8 點、digest 表下說明、第四節第 16 點、第五節測試表） | 本 commit |

`src/trpg/engine/`、`src/trpg/world/`、`client/src/` 的程式沒有改（`client/src/` 只有 `schema.d.ts` 與兩個快照 JSON）。

## 2. 測試（規格第 7 節）

| # | 測試 | 內容 |
|---|---|---|
| T-A1 | `tests/narrative/test_skill_icon_art_qi2a.py::test_prop_table_rows`（32 列）、`test_motion_table_rows`（13 列）＋`test_motion_without_shape_is_aura`、`test_act_table_rows`（30 列）、`test_spark_is_the_first_variant_element`（3 列） | 每列斷言結果，並用拆出的各列函式（`_prop_special`、`_icon_prop`、`_prop_modifier`、`_prop_spell`、`_action_setup`、`_action_effect`、`_action_status`、`_action_damage`）照順序找出「第一個成立的列」，斷言等於這一列。實例全部照規格表（腳本重確認：每個實例都走到所列的那一列） |
| T-A2 | `test_every_skill_matches_the_reference_implementation` | 402 招：參考實作吃 YAML 原文、`icon_of` 走 `skill_icon(SkillDef)`。**差異 0**（366 招五欄＋元素底全同；36 招 `prop == icon_prop`、`motion == derive_motion(原文, icon_prop)`、其餘同） |
| T-A2 補 | `test_model_dump_none_keys_count_as_missing` | 修正技用 `model_dump()` 與 `model_dump(exclude_none=True)` 結果相同，且染色不只一種。**突變驗證**：把 `_filled` 換成「鍵存在就算」，這項與 T-A2 都失敗（11 招變 `blood`） |
| T-A3 | `test_content_table_equals_the_reference_constants`、`test_default_rules_are_the_content_rules` | YAML 載入後逐表、逐筆、照順序等於參考實作同名常數（`terrain` → `surface`＋`stone` 除外）。檔頭註明：改表時這項要和表一起改 |
| T-A4 | `test_icon_prop_sits_between_rows_2_and_3`（5 列） | 化身填 `w:axe` → `form:bear`；雙槍填 `w:sword` → `w:dual_pistol`；普攻精通填 `w:hammer`、靜電弩填 `w:longgun`、氣爆填 `w:fist` → 填的值 |
| T-A5 | `test_motion_follows_the_final_prop`、`test_icon_prop_none_still_gets_the_arcane_prop_for_marks_on_a_prop` | 36 招 `motion` 等於用 `icon_prop` 重算；和沒填時不同的**恰好** 6 招（`skill_ambush_stab`、`skill_ember_bite`、`skill_flurry_jab`、`skill_ground_finish`、`skill_marrow_thorn`、`skill_venom_blade`；`ember_bite` 是 `shot`）；孤注一擲填 `none` → `el:arcane`，出手用 `el:arcane` 算 |
| T-A6 | `test_icon_prop_outside_the_list_falls_back_to_derivation`（6 列） | `"w:banana"`、`"W:SWORD"`、`3`、`""`、`None`、`["w:sword"]`：`art` 與沒填相同、不丟例外；`SkillIcon.icon_prop` 照 IP-1（字串原樣、其餘 `None`） |
| T-A7 | `tests/content/test_icon_prop_d4_qi2a.py`（7 項） | 化身、`wielding_weapon`（第一段）、`wielding_weapon` 只在複合第二段（合成）填 `icon_prop` 都回問題；一般招不算；目前內容 0 招被擋（化身 10、`wielding_weapon` 24）；整份內容載入時化身與雙槍填值拋 `ContentError` |
| T-A8 | `test_empty_draft_is_none_aura_buff`、`test_garbage_drafts_never_raise`（16 列）、`test_workshop_walk_steps_all_get_art` | `icon_of({})` → `none`／`aura`／`buff`、`None`、`None`；規格列的型別錯草稿全部回傳 `IconArt`；工坊示範三條每一步都有 |
| T-A9 | `tests/content/test_icon_art_battle_qi2a.py`（5 項） | 內容複本把 `skill_icon_art.yaml` 換成 `{}` 重新 `load_library`：`hash_ruleset` 相同；`ruleset_hash`、`content_digest` 不同（預期）；4 招 × 種子 1、2（沿用 IP-1 的單位配法）兩份規則包對戰，步驟、事件、最終狀態逐筆相同 |
| T-A10 | `tests/api/test_icon_art_api_qi2a.py`（3 項）、改寫 `test_icon_prop_api_ip1.py::test_icon_without_prop_is_unchanged` | 402 張技能卡與全部變奏卡的 `icon.art` 等於 `derive_art`；允許清單換空時技能卡退回推導（證明呼叫處吃內容庫上的表）；`/api/workshop/check` 的 `icon.art` 等於 `derive_art(草稿)` |
| 跨檔參照 | `test_table_references_are_listed` | 表引用的武器、召喚物、狀態、條件、表面、原語、形狀、修正鍵在目前內容裡都存在（清單 `KNOWN_MISSING` 為空）；不在載入時擋 |

**改寫的既有測試（舊斷言 → 新斷言，不放寬）**：`tests/api/test_icon_prop_api_ip1.py::test_icon_without_prop_is_unchanged`
- 舊：巨劍劈砍填 `icon_prop: w:axe` 後，`pop("icon_prop")` 剩下的整份 dump 和沒填完全相同。
- 新：`pop("icon_prop")` 與 `pop("art")` 後剩下的完全相同；`art` 沒填時 `prop == "w:greatsword"`、填後 `prop == "w:axe"`；`motion`、`act`、`tint`、`spark` 逐一相同；兩邊 `art` 的鍵都恰好是五個。

**T-A1「合成」列**（實際技能複製後改最少的欄位）：

| 列 | 合成方式 | 結果 |
|---|---|---|
| 道具 3「攻擊遠程」 | `skill_attack_mastery` 改 `weapon_req: ranged` | `w:bow` |
| 道具 4a「槍」 | `skill_armor_piercing_arrow` 改名「穿甲槍擊」 | `w:longgun` |
| 道具 4b 拳／匕／矛槍／斧／鐮／錘鎚 | `skill_all_in` 改名「孤注一拳／一匕／一槍／一斧／一鐮／一鎚」 | `w:fist`／`dagger`／`spear`／`axe`／`scythe`／`hammer` |
| 道具「最後」 | `skill_bear_trap` 只留 `damage` 效果 | `el:arcane` |
| 出手 1「沒有形狀」 | `skill_cleave` 的 dump 拿掉 `shape`（`SkillDef` 形狀必填，只能用 dict） | `aura` |
| 記號 24 | `skill_bear_trap` 只留一個效果、型別換成不在任何記號表的原語（照 ID 排序取第一個） | `buff` |

## 3. 驗收條件逐條（第 8.1 節第 2 點；第 8 點 (b)）

1. **第 7 節測試全過**：見第 2 節。
2. **QI-2a 指令**（結束碼分開記）：
   - `UV_NO_SYNC=1 uv run trpg content check` → 0（**660 個檔、402 個技能**）
   - `ruff check .` 0、`ruff format --check .` 0（2368 檔）、`mypy` 0（1455 檔）、`lint-imports` 0（14 kept）
   - pytest：`tests/narrative/ tests/content/ tests/api/ tests/skillgen/`（`-m "not llm"`，含 slow，`-n 8`）→ **9121 passed、15 skipped、92 failed**；失敗全部在 `tests/skillgen/test_refactor_parity.py`（90）與 `test_proposal_l8.py`（2），是 FIX-1 在修的既有失敗：在乾淨的 `8d457ec6` 樹（`git archive` 到暫存區、用同一個 venv 跑）跑同兩個檔，失敗清單**逐條相同**（92 failed、836 passed），與本段無關。本段之後追加的測試再跑：`tests/narrative/test_skill_icon_art_qi2a.py tests/narrative/test_skill_icon.py` 132 passed
   - `tests/cli/test_output_snapshots.py -m slow` → 0（24 passed，含 `skills_list`、`skills_show_all`，快照沒動）
   - `tests/test_architecture.py`（最後跑）→ 0（13 passed）
   - `trpg battle --map open_plain --seed 7 --log-json …` 0；`trpg battle replay …` 0（「重播驗證通過：91 個動作、383 個事件，最終狀態一致」）
   - `corepack pnpm -C client typecheck` 0；`vitest run src/render/skillIcon.test.ts src/ui/skillCard.test.ts src/world/panelIcons.test.ts src/world/range.test.ts` 0（4 檔 102 項）
3. **(b) 後端推導 vs `qskills_derive.derive()`**：402 招逐招比對差異 0（T-A2）；另用暫存腳本以同樣方法獨立跑一次，`diff 0 filled 36`。

## 4. 快照與雜湊變動（每一項都證明只來自本段）

**快照 JSON**：寫腳本把 HEAD 版與重產版各自拿掉 `art`（鍵恰好五個的物件）後比對：
- `client/src/render/fixtures/skill_icons.json`：拿掉後**完全相同**；新增 `art` 473 個（402 招＋隨機 50＋工坊示範 7×3）。
- `client/src/ui/fixtures/skillCards.json`：拿掉後**完全相同**；新增 `art` 6 個（卡片與變奏卡）。
- `client/openapi.json`：只多 `IconArt` schema 與 `SkillIcon.art` 一個屬性（`git diff -U0` 逐行看過）；`client/src/api/schema.d.ts` 同（`IconArt` 型別、`art?: IconArt | null`）。
- `export_client_fixtures.py` 也寫了 `unitDolls.json`、`raceLooks.json`、`glossary.json`：沒有變動。
- CLI 快照：沒有變動、沒有重產。

**內容雜湊**（改前＝`8d457ec6` 的 `src`＋`content` 用 `git archive` 匯出、以 `PYTHONPATH` 載入）：

| 雜湊 | 改前 | 改後 | 歸因 |
|---|---|---|---|
| `hash_ruleset(library.ruleset)`（戰鬥紀錄） | `21d09310ae4fd46d…` | `21d09310ae4fd46d…`（不變） | 表不進規則包 |
| `ruleset_hash(library)`（一輪存檔） | `5195eef990e983b1…` | `57420f4cbee82d8c…` | 改後的內容庫用 `dataclasses.replace` 拿掉 `skill_icon_art.yaml` 那一筆 `files` 重算 → `5195eef990e983b1…`，回到改前 |
| `content_digest(library)`（世界日誌） | `451d7bf5039c6d72…` | `8a884ff8f3c9c3a9…` | 同上拿掉 → `451d7bf5039c6d72…`，回到改前 |

版號（`LOG_FORMAT`、`WORLD_RULES_VERSION`、`CHAR_FORMAT`）都沒動：沒改事件、動作、狀態、紀錄結構與結算。`SkillIcon` 不進一輪存檔、世界存檔、戰鬥紀錄，也不進 LLM prompt（`skill_icon`／`icon_of`／`SkillCard` 只在 `trpg.narrative` 與 `trpg.api` 使用，grep 確認）。

**請使用者重開伺服器檢查的重點**：內容檔有新增（`skill_icon_art.yaml`），重開後**進行中的一輪會從頭開始、舊世界日誌標成不能重播**（一次）；舊戰鬥紀錄照樣重播。畫面本段不變（前端還沒畫 `art`，2b／2c 才畫）；API 的技能圖示 `icon` 多一欄 `art`。

## 5. 需求第 6 節 (a)～(d)

- (a) 逐像素對照：2b 負責，本段無。
- (b) 見第 3 節第 3 點（差異 0）。
- (c)、(d)：2c 負責，本段無。

## 6. 複雜度類 noqa

- `tests/narrative/test_skill_icon_art_qi2a.py::prop_row`：`# noqa: PLR0911`（7 個 return）。理由：測試用的「第幾列」判定，一列一個 return 才能和需求 3.3 的道具表逐列對照；拆開反而看不出順序。正式程式沒有新增 noqa（`skill_icon_art.py` 拆成每列一個函式，`C901` ≤ 15）。

## 7. 沒驗證

- 前端沒有畫 `art`（2b、2c）；沒有實機看。沒跑完整 `scripts/check.py`、沒跑模擬（規格不要求）。
- 平行段：沒改 FIX-1 的三個測試檔；本段的改動不影響它們的期望值（第 3 節：失敗清單和改前逐條相同；`tests/cli/test_run_cli.py` 沒跑；grep 確認它不引用技能卡、`skillCards` 或工坊 API，預期不受影響）。

## 8. 待 PM 決定

1. **推導表維護者**：規格 D2 寫「待定」，但 06 6.36 已寫「由美術 PM 維護」；YAML 檔頭照 06 寫美術 PM。（06 6.36 第 3 點）
2. **`enter_form` 沒有 `form` 欄位時**（只在草稿可能出現）：參考實作會輸出 `form:None`；本段當作這列不成立、往下推導（保守，不輸出不存在的代碼）。真技能沒有這種資料，T-A2 不受影響。（需求 3.3 道具第 1 列）
3. **D4 只看效果層級的條件**：技能層級 `condition`（不在效果上）是 `wielding_weapon` 的招不擋——推導表道具第 2 列也只看效果上的條件，兩邊一致；目前 0 招有技能層級的 `wielding_weapon`。要擋更多需改推導表的規則（美術）。（規格 A2、需求 3.3）
4. **`tint`／`spark` 為 `None` 時照樣輸出 `null`**（`IconArt` 五欄必有，前端型別是 `string | null` 而不是選填）；`SkillIcon.art` 本身選填（`art?:`），沒填的舊資料前端畫 `none`／`aura`／`buff`。（規格第 5 節 API 列）
5. **`icon_art_rules(library)` 每次呼叫重建查表**（約百筆，技能卡逐張呼叫）：沒量到可見的成本，先不快取；之後若 API 回應變慢可掛在內容庫上快取。
6. **schema 比規格多擋兩件事**：dot／bind／curse 三張表的狀態不能重疊、`effect_action` 與 `late_action` 的原語不能重疊（重疊時後面那列永遠不會被用到）。參考表目前都符合；美術 PM 若要刻意重疊，再放寬。（規格 A1「ID 不重複」的延伸）
7. **`ContentLibrary.icon_art` 預設 `None`**：不是 `load_library` 建的內容庫（目前沒有）會退回讀預設內容資料夾的表；`icon_props` 預設空清單（＝沒有任何 `icon_prop` 生效）。（規格第 0 節第 13 列）
