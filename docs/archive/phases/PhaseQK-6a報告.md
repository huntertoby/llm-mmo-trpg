# Phase QK-6a 報告：一般敵人依 id 挑外觀（資料與確定性挑選）

依 `docs/art/QK移植需求.md` 第 7 節第 2 點（#137 第 4 點）與 `docs/archive/phases/Phase6R-2報告.md` 待 PM 決定第 1 項。只做資料與挑選，不改前端畫法（`client/src/render/` 沒動；前端 6R-2 起已讀 `DollLook.custom`，`withLookChoice` 疊在範本外觀之後，自然生效）。協調者補充：只做人形敵人（紙娃娃），異形、頭目的外觀分類不依賴、資料不改。

## 1. 做了什麼

| 項目 | 內容 | 檔案 |
|---|---|---|
| schema | `LookRange`（`race`、`skin`、`hair`、`hair_color`、`beard`；各項選填、至少一項、不可重複）；`UnitTemplate.look_range` 選填；召喚物、異形（`doll.creature`）、沒有 `doll`、已寫 `doll.custom` 的範本不能寫 | `src/trpg/content/battle.py` |
| 載入驗證 | 範圍值要在 `look_range.race` 這一族的 `look_options` 內（`RaceDef.options()`），種族要存在；不合法 `ContentError` | `src/trpg/content/library/tables.py`（併進 `_check_unit_races`） |
| 挑選 | `pick_look`／`ordinary_enemy_doll`：純函式，每一項用 `fnv1a64("戰鬥初始種子|範本ID|單位ID|欄位名")` 取餘數挑；不用 `hash()`、`random`，不耗戰鬥亂數（種子是 `BattleState.seed`，只讀） | `src/trpg/content/enemy_looks.py`（新） |
| 套用 | `make_unit` 多一個關鍵字參數 `seed`（預設 0），建單位時 `doll=ordinary_enemy_doll(template, uid, team, seed)`；開場（`start_battle` 傳初始種子）與援軍（`spawn` 效果傳 `state.seed`）都會傳；召喚物不挑，呼叫處不用傳 | `src/trpg/engine/lifecycle.py`、`engine/battle.py`、`engine/effects/world.py` |
| 測試 | 同種子同 id 兩次相同、不同種子不同（同一編號 30 個種子挑出 10 種以上）、200 個 id 涵蓋每一項範圍、`make_unit` 寫入、我方不挑、頭目／異形／召喚不受影響、身分特徵保留、範圍外載入失敗、schema | `tests/content/test_ordinary_enemy_looks.py`（新） |

「一般敵人」判斷（`is_ordinary_enemy`）：`team == enemy`、非召喚、`tags` 不含 `boss`、有 `doll` 且沒有 `creature`、不是骷髏。只看 `creature is None`，沒有用到異形或頭目的外觀分類細項。

身分特徵保留：範本髮型是 `bun`（髮髻）或 `none`（光頭）時不換髮型；範本 `beard: true`（大鬍子）時不換鬍子；骷髏整個不變。其他範本欄位（裝備、頭巾、主手）照舊，只多 `custom`。

`race` 欄位是「外觀參照的種族」（範圍要在這一族的清單內），**不是**引擎的 `UnitTemplate.race`：不給種族技、不改被動，戰鬥規則不變。

## 2. 加了範圍的敵人

參照種族都是 `human`。

| 範本 | 膚色 | 髮型 | 髮色 | 鬍子 |
|---|---|---|---|---|
| `bandit`、`bandit_archer`、`bandit_shieldbearer`、`bandit_guard`、`bandit_archer_guard`、`bandit_shieldbearer_guard` | 人類 4 色全部 | 短、長、刺蝟、馬尾 | 深褐、褐、栗、淺褐、灰（5 色） | 無、鬍渣、八字、山羊、大鬍子 |
| `bandit_rookie`、`bandit_archer_rookie` | 同上 | 短、刺蝟、齊肩、馬尾 | 同上 | 無、鬍渣（新手年輕些） |

其餘範本沒加，維持原樣（頭目 `bandit_boss`、`bandit_warlord`，精英隊長 `bandit_captain`，宗門人形全部、異形全部）。

## 3. 快照與重播變動

- **CLI 輸出快照**（`tests/cli/test_output_snapshots.py`，含 slow）：25 個全過，**沒有重產**（終端輸出不印外觀）。
- **`client/openapi.json`**：重新匯出後 byte 相同（`UnitView`、`DollLook` 欄位沒變；`LookRange` 不在 API 裡），`schema.d.ts` 不用重產。
- **`trpg battle --map swamp --seed 7 --log-json`**：和「關掉挑選」的同一份程式比，動作列表與事件逐字相同；JSON 只差 3 處（種子進鍵後重新比過）：`final_state.units.unit_0004／0005／0006.doll.custom`（盜賊、盜賊盾兵、盜賊弓手；頭目 `unit_0007` 不變）。`battle replay` 驗證通過（88 個動作、313 個事件）。
- **`tests/world/test_field_ctx_replay.py`**（凍結重播）：陣容會序列化敵人範本，多了 `look_range` 鍵；照慣例加進 `DROPPED`（凍結後才加的欄位），雜湊仍是 `BEFORE_6CR2`。
- **`WORLD_RULES_VERSION`／規則雜湊**：沒升。改的是內容資料（`content/units/*.yaml`），內容 digest 本來就會變；世界規則程式沒改。

## 4. 驗收

- `ruff check`、`ruff format --check`、`mypy`（583 檔）、`lint-imports`（14 kept）：通過。
- `uv run pytest -q tests/content tests/engine tests/world tests/api -x -n 4`：8837 passed、1 skipped（種子進鍵後重跑）。
- CLI 快照（`-m ""`）：25 passed。
- swamp 種子 7 重播：通過。

## 5. 待 PM 決定

1. **「種族」範圍沒做成隨機挑種族**：規格寫「外觀範圍（種族、髮型、膚色、鬍子）」。換引擎種族會帶來種族技與環境被動（改戰鬥規則），所以 `race` 只當「範圍參照哪一族的 `look_options`」，每個範本一族、不隨機。若要「同範本有人類／矮人／獸人外觀」，需要一個只給畫面的種族欄位（前端目前從 `UnitView.race.look` 畫種族部件，那是引擎種族），請美術 PM／玩法 PM 決定。
2. **頭目可以寫 `look_range` 但不挑**：本來想在 schema 擋頭目，但很多引擎測試把 `bandit` 加上 `boss` 標籤當頭目用，會被擋；改成執行時不挑（頭目外觀固定）。召喚物、異形仍在 schema 擋。
3. **沒做「粗獷／柔和」軟性抽**（`外觀變化方案.md` 第 4 節）：各項獨立挑，盜賊範圍裡沒有睫毛，所以不會抽出「睫毛配大鬍子」；也沒挑臉型、眼睛、體型。要加時在 `LookRange` 多欄位即可。
4. **（已做）雜湊鍵加戰鬥初始種子**（PM 決定）：鍵改成 `種子|範本ID|單位ID|欄位名`。單位 ID 每場從同一組編號開始，種子進鍵後不同場的同範本長得不一樣；同一場重播仍相同（種子在 `BattleState.seed`、不耗戰鬥亂數）。
5. **前端目前畫不出部分值**（6R-2 報告第 2 項）：刺蝟、馬尾、齊肩先畫最接近的；鬍渣、八字、山羊鬍等 QK-1／QK-6 補畫後自然生效。
6. **範圍數值**（哪些範本、色票子集）是原型預設，可再調。
