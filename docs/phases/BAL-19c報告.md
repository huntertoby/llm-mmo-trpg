# BAL-19c 報告：召喚（玩法決定 #110，缺口 2）

規格：`docs/phases/PhaseBAL計畫.md` 第 12 節 BAL-19c；設計 `docs/design/06-技能.md` 6.27.3、6.27.4、6.29、6.34.1、6.34.9。召喚法術維持意志（6.10 不改）。

## 做法

1. **召喚物關鍵字的武器技**（9 招，`content/skills/skill_sum_*.yaml`）：骨架 `summon`、類別 `weapon`、單一召喚效果（AP 1、冷卻 3～4、耐力）。武器技看手上武器的屬性（3H-6），召喚物的 HP 與傷害成長（`growth_of`）跟著武器屬性走，不看意志。近戰提示屬性一律填 `str`（`weapon_class_mismatches` 要求近戰武器技的提示是武器大類主屬性；拿匕首時實際看敏捷），遠程填 `dex`。
2. **1 階召喚白板**：原本的兩個基本召喚白板配方（`summon_spirit` 元素之靈、`summon_skeleton` 骷髏戰士）`min_tier` 2 → 1，三選一 1 階就能抽到。依關鍵字挑的召喚物（火靈、冰靈、戰狼……）仍 2 階起。

## 新增技能（9 招）

| ID | 名稱 | 武器 | 提示屬性 | 召喚物（持續） | 專屬關鍵字 | 稀有度 | 費用 | 預算比例 | 最低角色階級 |
|---|---|---|---|---|---|---|---|---|---|
| skill_sum_grave_blade | 劍塚喚兵 | 近戰 | str | 骷髏戰士（2） | summon、prone | 稀有 | 耐力 6、冷卻 4 | 95.9% | **1** |
| skill_sum_war_howl | 戰嚎喚狼 | 近戰 | str | 戰狼（2） | summon、prone | 稀有 | 耐力 6、冷卻 3 | 80.4% | 2 |
| skill_sum_quake_idol | 撼地立像 | 近戰 | str | 石像（2） | summon、collision | 稀有 | 耐力 8、冷卻 4 | 84.3% | 2 |
| skill_sum_vanguard_spirit | 號令先鋒 | 近戰 | str | 守護之靈（4） | summon | 史詩 | 耐力 8、冷卻 4 | 93.7% | 2 |
| skill_sum_shadow_twin | 影隨刃 | 近戰 | str（匕首看敏捷） | 影魅（2） | summon、concealed | 稀有 | 耐力 6、冷卻 4 | 80.0% | 2 |
| skill_sum_whistle_arrow | 鳴鏑喚鷹 | 遠程 | dex | 鷹隼（3） | summon、marked、high_ground | 稀有 | 耐力 6、冷卻 4 | 93.1% | 2 |
| skill_sum_spirit_arrow | 符箭喚靈 | 遠程 | dex | 元素之靈（3） | summon | 稀有 | 耐力 6、冷卻 4 | 98.8% | **1** |
| skill_sum_ember_arrow | 火引箭靈 | 遠程 | dex | 火靈（2） | summon、ignite | 稀有 | 耐力 6、冷卻 4 | 77.1% | 2 |
| skill_sum_storm_arrow | 雷鳴箭靈 | 遠程 | dex | 雷靈（2） | summon、charged | 史詩 | 耐力 8、冷卻 4 | 98.4% | 2 |

- 稀有度：稀有 7、史詩 2（召喚原語最低稀有；手寫召喚技全是稀有）。全部 1 階、AP 1。
- 每招 `trpg skills budget` 合格、驗證通過；`trpg content check`：合併 19b 後 344 個技能通過預算與結構驗證。

## 白板配方改動（動到 `src/`，改動小）

- `content/skill_budget.yaml` 的 `min_character_tier` 新增 `basic_summon_units: [summon_elemental_spirit, summon_skeleton_warrior]`。
- `src/trpg/content/skill_rules.py`：`CharacterTierRules.basic_summon_units`（預設空）。
- `src/trpg/skillgen/validate.py` 的 `tier_requirements`：技能的召喚效果**全部**是一次 1 隻基本召喚物時，召喚原語與召喚骨架不列入最低角色階級需求（1 階）。其他召喚物、一次 2 隻（數量型分歧）仍 2 階。
- `content/skill_composer.yaml`：`summon_spirit`、`summon_skeleton` 的 `min_tier` 2 → 1（`creation_tier: 1` 保留）。
- 為什麼要動程式：驗證器的階級表把召喚原語與骨架定在 2 階，「從零產生」的白板（來源 `level_up`）在 1 階會被 `tier.primitive`／`tier.skeleton` 擋下；只改配方 `min_tier` 不夠。用「基本召喚物」的單位清單放寬，不改整張表，所以組合器、LLM 提議與其他召喚物不受影響。
- 測試：`tests/skillgen/test_skill_tier_3w9.py` 新增 `test_basic_summons_open_tier_one_offers`（1 階召喚白板通過驗證、其他召喚物與一次 2 隻仍 2 階），表格與驗證器測試改用非基本召喚物（戰狼）；`test_whiteboard_3w4b.py` 的 #72 階級表測試照 #110 更新（1 階的種類多了 summon）。新增 `tests/content/test_bal19c_summon_weapons.py`（力量、敏捷都有召喚武器技、各有 1 階可出的；召喚物成長跟著武器屬性；在引擎裡能施放）。

## 交叉表前後（`scripts/skill_balance_audit.py --sections 2,4`）

第 4 節（武器大類 × 關鍵字，`手寫 同路線／可用 ＋ 模板`）summon 列：

| 開局 | 前 | 後 |
|---|---|---|
| 劍 力量 | **0** = 0/20 + 0.0/1 | 5.0 = 5/25 + 0.0/1 |
| 匕首 敏捷 | **0** = 0/20 + 0.0/1 | 5.0 = 5/25 + 0.0/1 |
| 弓 敏捷 | **0** = 0/20 + 0.0/1 | 4.0 = 4/24 + 0.0/1 |
| 魔導劍 力量／智力 | **0** = 0/20 + 0.0/1 | 5.0 = 5/25 + 0.0/1 |
| 鐮刀 意志 | 21.0 = 20/20 + 1.0/1 | 26.0 = 25/25 + 1.0/1 |
| 火杖 智力／權杖 感知 | **0** | **0**（不變，召喚法術只看意志） |
| 圖騰杖 意志 | 21.0 | 21.0（不變） |

第 2 節：腳本把骨架 `summon` 的技能算在「召喚」種類，不算「武器技」，所以 2 節「summon × 力量／敏捷 × 武器技」仍顯示 0；2g 的召喚欄 20 → 29。

## 快照與 fixture

- `tests/skillgen/fixtures/refactor_3wr2.json`：重產。complete／retier 只新增 9 招，既有條目不變；flash 抽樣依技能排序取樣，新增技能讓抽到的技能換了一批（既有同 key 的值不變）。合併 19b 後再重產一次。
- `client/src/render/fixtures/skill_icons.json`：重產，只新增條目，沒有既有條目改變。
- `tests/cli/snapshots/cli_output_hashes.json`：合併 19b 後重產（不加 -n），只有 `skills_list`、`skills_show_all/00～15` 改變。
- 計數：`_BAL19_PREFIXES = ("skill_wis_", "skill_wil_", "skill_sum_")`；內建技能數 335 → 344。

## 檢查

- 合併 main（BAL-19b，807ea049）後：`uv run pytest -n 8 --timeout=1800 tests/content tests/skillgen tests/narrative tests/roguelite tests/api/test_client_fixtures.py`：5544 passed、14 skipped。
- CLI 快照：重產 25 passed；`-n 14` 驗證 25 passed。
- `ruff check`、`ruff format --check`、`mypy`（941 檔沒有問題）、`lint-imports`（7 契約）通過。
- 重播：`trpg battle --map swamp --seed 7` → `battle replay`：88 個動作、313 個事件，一致。

## 待 PM 決定

1. **手寫的基本召喚技也跟著變 1 階**：「基本召喚物 1 階」寫在單位清單上，所以手寫的 `skill_raise_skeleton`（喚起骷髏）、`skill_summon_spirit`（召喚元素之靈）和本段的劍塚喚兵、符箭喚靈最低角色階級都變成 1，1 階三選一的手寫池也拿得到。這和 6.34.9「2 階：召喚」的表不完全一致（#110 只寫「開放 1 階召喚白板」）；若只想開放白板，要改成依來源判斷（比較繞），請玩法 PM 定。
2. **召喚白板仍是法術（意志）**：1 階召喚白板配方只有法術版，力量、敏捷開局在三選一拿到的召喚白板會標偏離；力量、敏捷的同路線召喚靠本段的手寫武器技（1 階只有劍塚喚兵、符箭喚靈兩招）。要不要加武器版的召喚白板配方由 PM 定。
3. **法器的智力、感知路線仍是 0**（火杖、權杖）：照「召喚維持意志」沒有補；若要補只能用雙屬性或改規則。
4. 數值是初值，未經模擬；號令先鋒持續 4 輪（守護之靈點數低，要 4 輪才到 70% 以上）。影隨刃的提示屬性照近戰規則填力量（拿匕首時實際看敏捷）。
5. 沒有重跑第 5 節（偏離率），留給 BAL-19 最後的驗收。
