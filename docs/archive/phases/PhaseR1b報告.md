# Phase R1b 報告：`content/library.py` 按職責拆成子模組

依據：`docs/phases/整理提案-程式.md` 2.2 節 R1（含 R4 的 `_load_world` 一項）。分支 `dev/r1b`。做法照 R1a。

## 結果

`src/trpg/content/library.py`（2,779 行）→ `src/trpg/content/library/` 套件（共 3,131 行，多出的是各檔的 docstring 與 import）：

| 檔案 | 行數 | 內容 |
|---|---|---|
| `__init__.py` | 57 | 原模組 docstring＋子模組說明、re-export、原樣的 `__all__` |
| `ruleset.py` | 511 | `REQUIRED_STATUSES`、`_CacheDict`、`enemy_template_ids`、`Ruleset`；`skill_reference_problems` 與變奏檢查（`Ruleset.with_skills` 執行期呼叫它，放同檔避免循環匯入） |
| `container.py` | 287 | `ContentLibrary`、`skill_name_problems` |
| `load.py` | 419 | 入口 `load_library` 與 `_load_base_tables`／`_build_ruleset`／`_load_gear`／`_load_units`／`_load_maps`／`_load_run_extras`、`_apply_map_themes` |
| `base.py` | 118 | 共用工具：`_load_dir`、`_load_optional`、`_Loader`、`_BaseTables` |
| `world.py` | 825 | 大世界：`_load_world`（已拆）、`WORLD_*` 常數、地點圖／規則／誓約／傭兵／季節／敵人／遭遇／野外地圖的載入與檢查、`_load_newcomer`、`_hint_texts` |
| `tables.py` | 205 | 種族、修飾變化、技能成長、演化、閃現、開發用起始包、召喚物 |
| `skill_checks.py` | 198 | 技能、關鍵字、技能規則、裝備引用、`pool_region_problems` |
| `unit_checks.py` | 292 | 單位範本、測試 build、Boss 階段、地圖引用 |
| `gear_checks.py` | 219 | `_GearCatalog`、詞條、外觀、物品生成 |

每檔 < 900 行。子模組依賴單向：`ruleset`、`base` 為葉；`*_checks`、`tables` → 葉；`world` → 葉＋checks＋tables；`container` → `ruleset`＋`world`；`load` → 全部。沒有循環匯入、沒有延遲匯入、沒有新增 `noqa`。

## 做法

- 純搬移：腳本依原檔頂層敘述切段，每段（含前置註解、屬性 docstring）逐字搬到所屬子模組，未用到的 import 由 `ruff --fix F401` 清掉。AST 比對：原檔所有頂層敘述除了模組 docstring（擴充子模組說明）、`_LOG`、`_load_world` 外全部原樣出現在新檔。
- `_LOG` 改成 `logging.getLogger("trpg.content.library")`（原為 `__name__`），讓 logger 名稱與拆前相同。
- re-export：全專案從 `trpg.content.library` 匯入的名稱共 18 個（含私有 `_affix_reference_problems`、`_check_skills`、`_check_stele_regions`、`_load_flash`、`_load_world_maps`、`_story_skill_problems`、`_trait_problems`，以及不在 `__all__` 的 `pool_region_problems`）。`__init__` 另外 re-export 其餘公開名稱（`unit_phase_problems`、7 個 `WORLD_*` 常數），共 **27 個**；不在 `__all__` 的一律用 `import X as X` 明確 re-export，`__all__`（11 個）不變。
- 呼叫端 import 一行都沒改；import-linter 契約沒動。

## `_load_world` 拆段（R4 一項）

原 150 行 → 主函式 64 行（含簽名與 docstring），依序呼叫：

| 函式 | 內容 |
|---|---|
| `_load_world_battle` → `_WorldBattle` | 地點圖、規則、誓約、傭兵、敵人、遭遇表、季節 |
| `_load_world_story` | 事件內容、任務 |
| （主函式內）`_check_unit_races`、`_check_companions` | 原樣 |
| `_load_world_market` → `_WorldMarket` | 經濟、商店價格檢查、掉落、製作、交易 |
| `_load_world_field_maps` | 野外地圖 |
| （主函式內）`_check_post_facilities`、回傳 dict（`_load_address`、`load_world_resonance`、`_load_newcomer`） | 原樣 |
| `_region_npcs` | 原本重複 3 次的「區域 → NPC → 地點」推導式 |

所有載入、檢查與 `files.append` 的先後順序與拆前相同（錯誤訊息的先後、`files` 順序不變）；`keyword_ids` 改在主函式先算一次再傳入（純推導，無副作用）。

## 驗收

- `ruff check`、`ruff format --check`、`mypy`（1379 檔）、`lint-imports`（14 條契約 KEPT）：全過。
- `pytest -q tests/content tests/cli/test_output_snapshots.py tests/world tests/engine tests/api/test_openapi_snapshot.py -x -n 4`：8038 passed（CLI 快照、`frozen_replay`、`RULE_HASHES` 未重產）。
- 重播：`trpg battle --map swamp --seed 7` → `battle replay` 通過（88 個動作、313 個事件）。
- `scripts/export_openapi.py` 後 `client/openapi.json` 與拆前 byte 相同。
- 載入結果比對（scratchpad 一次性腳本，未 commit）：拆前與拆後 `load_library()` 整份序列化（pydantic 物件 `model_dump_json`、dataclass 逐欄位，含 `files` 順序）SHA-256 相同（6,524,013 字元）。

## 待 PM 決定

- `_LOG` 的 logger 名稱以字串寫死 `"trpg.content.library"`（保持拆前名稱）；若之後不在乎名稱，可改回 `__name__`。
- `world.py` 825 行，最接近 900 上限；之後大世界再加載入段時建議再拆（例如 `world_battle.py`／`world_market.py`）。
- 子模組名稱（`container`、`tables`）是保守選擇；其他 docstring 用 `:mod:\`trpg.content.library\`` 引用的地方透過 re-export 仍成立，沒改。
