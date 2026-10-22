# Phase 3E-2f 報告｜YAML 唯一來源與落點函式

> 實作者（sonnet）撰寫。來源：`Phase3E計畫.md` 3.1 的 3E-2f 列（舊 3E-2 #2、#3）。純重構、行為不變：沒有改任何數值、事件或 `LOG_FORMAT`（維持 `/57`）。

## 做了什麼

### ① 落點與最近空格集中（`src/trpg/engine/rules/landing.py`，新）

- `landing_problem(state, xy, *, mover=None, clear_of_objects=False, occupancy=None) -> LandingBlock | None`：依序檢查地圖範圍、可站立（`is_standable`，已排除致命地形）、別的存活單位（`mover` 自己所在格不算）、（選用）物件；回傳阻擋原因碼 `OUT_OF_BOUNDS`／`NOT_STANDABLE`／`OCCUPIED`／`OBJECT`。**呼叫端自己組中文訊息**，所以各處原本的措辭與檢查順序完全不變。
- `nearest_free(state, origin, *, radius=None, mover=None, clear_of_objects=False)`：曼哈頓距離最近的空格，同距離依 `y` 再依 `x`；`radius=None` 為整張地圖。

| 原本的實作 | 改為 |
|---|---|
| `rules/movement.py` `nearest_safe_tile`（整張地圖掃描） | 刪除；`triggers.py`（精英墜落安全格）改 `nearest_free(..., mover=unit.id)` |
| `effects/world.py` `_free_tile`（整張地圖）＋`_spawn_unit` 的四項判斷 | `nearest_free` ＋ `landing_problem` |
| `effects/world.py` `hurl_landing`（半徑內、無物件） | `nearest_free(radius=hurl_scatter_radius, clear_of_objects=True)` |
| `skills/revive.py` `_free` ＋ `revive_landing`（原位置，再半徑內最近） | `nearest_free(unit.xy, radius=revive_landing_radius)`（距離 0 即原位置） |
| `basics._landing_problem`（攀爬／跳躍落點） | `landing_problem` |
| `skills/mobility.py` 跳躍落點、瞬步落點 | `landing_problem` |
| `skills/targeting.py` 傳送自己落點、`teleport_landing_problem`（傳送他人）、`_trap_site_problem`、`summon_site_problem` | `landing_problem` |
| `summons.py` `_platform_site`（高台升起格） | `landing_problem(clear_of_objects=True)` ＋ 高度條件 |
| `skills/charge.py` `_free_side`（衝撞推到旁邊） | 改用 `unit_push_block`（見「待 PM 決定」#1：致命地形額外排除以維持原行為） |

沒有合併的（理由）：`create_obstacle`、`inscribe` 的 `effect_fizzled` 原因碼順序（`occupied` 先於 `not_standable`）與 `landing_problem` 的順序不同，合併會改事件；`battle._place_units` 起始位置（訊息要附地形名）、`environment._weather`（要看表面）、`orders._standable_problem`（不看單位）、`_steps_to`（路徑搜尋）不是落點判斷。

### ② 範圍、清單與狀態 ID 以 YAML 為唯一來源

- **整數參數範圍**：`EffectSpec` 的 `lifesteal_permille`（1–500）、`max_hp_permille`（1–1000）、`multiplier_permille`（1–10000）、`power_permille`（100–999）、`radius`（0–2）、`rounds`（1–3）、`splash`（1–1）原本在 schema 寫死的 `ge`／`le` 與 `skill_primitives.yaml` 的 `params.min／max` 完全相同，現在 schema 只宣告型別；`EffectSpec._check_yaml_ranges` 在建構時讀 YAML 的範圍驗證（`YAML_RANGED_FIELDS`，訊息：`效果 damage 的 lifesteal_permille 必須在 1–500，收到 501`）。`MAX_LIFESTEAL_PERMILLE` 常數與 `option_params.py` 對它的夾限刪除（YAML 已是 500）。
- **形狀用途清單**：`skill_shapes.yaml` 新增 `shape_roles`（`followup`、`on_kill_second`、`pierce`、`zone_moving`、`zone_caster`、`shape_to`，順序即錯誤訊息的列舉順序）。`FOLLOWUP_SHAPES`、`ON_KILL_SECOND_SHAPES`、`PIERCE_SHAPES`、`ZONE_MOVING_SHAPES`、`ZONE_CASTER_SHAPES`、`SHAPE_TO_VALUES` 改從它讀；`composer_special.py` 的 `("line","chain","cone")` 改用 `SHAPE_TO_VALUES`。`ShapeTable` 驗證用途名稱齊全、形狀存在。
- **聖光雙效可用骨架**：`damage.params.split_heal.allowed_skeletons: [aura, area]`；`SPLIT_SKELETONS` 從它讀；`PrimitiveDef` 驗證骨架 ID 存在。
- **狀態 ID**：`cheat_death.status: undying`、`redirect_damage.status: soul_link`、`delayed_damage.status: time_bomb`，檔尾 `mechanic_statuses: {charging: charging}`；`CHEAT_DEATH_STATUS`、`REDIRECT_STATUS`、`TIME_BOMB`、`CHARGING` 從它們讀。`Ruleset` 載入時檢查這些狀態存在於 `statuses.yaml`（`skill_primitives.yaml 引用了未知的狀態：…`）；`REQUIRED_STATUSES` 補上 `armor_broken`、`revealed`、`shielded`（`engine/ids.py` 的常數原本沒檢查）。
- 讀取機制：`src/trpg/content/yaml_sources.py`（新）在 schema 匯入時直接讀專案內建 `content/`（`loader.bundled_content_dir()`，不受 `TRPG_CONTENT_DIR` 影響），因為這些清單是模組常數、匯入當下沒有規則包。

## 測試與行為不變的證據

- 既有測試一個都沒改：`tests/content`、`tests/skillgen`、`tests/engine`、`tests/cli`、`tests/test_architecture.py` 共 4284 個通過。
- 新增 `tests/engine/test_landing.py`（5 個：每種阻擋原因、`mover`、物件、排序、半徑）與 `tests/content/test_yaml_sources.py`（11 個：常數值與原本相同、`shape_roles` 驗證、未知狀態、七個欄位的範圍訊息）。
- 以 5826670（本段之前）對照：`sim maps --seeds 4 --jobs 4 --json`（全部地圖）與 `sim skills --demo --seeds 1 --jobs 4 --json`（217 場）兩份 JSON **逐位元組相同**（`cmp`）。
- `ruff check`、`ruff format --check`、`mypy` 乾淨；`LOG_FORMAT` 未改。

## 待 PM 決定

1. **`charge` 的 `_free_side` 改用 `unit_push_block` 後仍額外排除致命地形**：`unit_push_block` 允許把單位推進致命地形（推擊會把人推下去），但原本「被撞開到旁邊」要避開深淵、岩漿；為了行為不變保留 `and not is_deadly(...)`。若 PM 想讓衝撞也能把人撞進致命地形，拿掉那一項即可（會改變行為，需升 `LOG_FORMAT`）。
2. **只搬了七個「與 YAML 完全相同」的範圍**：其他欄位（`chance_permille`、`permille`、`per_stack_permille`、`hp_permille`、`duration`、`range`、`speed`）schema 的範圍比 YAML 寬（例如 `chance_permille` schema 1–999、YAML 50–950），既有測試明確要求「schema 擋 0／1000、YAML 擋 20／980」兩層，所以保留 schema 的粗範圍、細範圍仍在跨檔案驗證；`SkillCost`、修正規則 `change`、`ScaleSpec`、`damage_multiplier_permille` 等不在原語表的範圍沒有 YAML 對應，未動。要完全移除粗範圍，需改這些測試。
3. **狀態 ID 常數仍是 Python 名稱**：引擎規則直接引用的狀態（`PRONE`、`SHIELDED`、`DEFENDING` 等 `engine/ids.py`）名稱必然寫在程式裡，只能靠 `REQUIRED_STATUSES` 載入時檢查存在；原語固定施加的四個已改由 YAML 提供。`sim/metrics.py` 的 `CONTROL_STATUSES`、`composer_special.py` 的 `_CONDITION_STATUSES` 沒動（後者決定亂數抽樣的內容，改成從 YAML 推導會改變組合器的種子結果）。
4. **匯入時讀 YAML**：`trpg.content.skills` 匯入時會讀兩個內建 YAML（固定 `content/`，忽略 `TRPG_CONTENT_DIR`）。若之後希望不同內容資料夾有不同的形狀用途清單，需要把這些常數改成從規則包取得（要動所有驗證器的簽名），這段沒做。
5. **`landing_problem` 的順序固定為範圍 → 可站立 → 單位 → 物件**：與 `create_obstacle`／`inscribe` 的 fizzle 原因順序不同，這兩處因此沒合併（見上）；若 PM 認為可以統一原因碼順序，可再合併（會改事件內容）。
