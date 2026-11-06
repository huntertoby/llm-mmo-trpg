# Phase 3-5b 報告：專屬 Boss 地圖與 Boss 遭遇

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| c060608 | 新地圖 `content/maps/bandit_lair.yaml`、新單位 `content/units/bandit_warlord.yaml`、新地圖類型 `boss`（`BOSS_ARCHETYPE`，從 `sim maps` 預設清單與網頁一般地圖列表排除）、`tests/content/test_bandit_lair.py` |
| ef4d646 | `content/roguelite.yaml` 的 `boss:` 改用 `bandit_lair` ＋ `bandit_warlord`；測試固定值與跨檔案測試更新 |
| d67cff8、0af20c9 | import 排序；`tests/engine/test_source.py` 更新（精英清單、有源泉的地圖） |
| 19c5d8e | 油桶位置微調（避免 push check 的「單次移動封路」）；`VICTORY` 固定值、`test_push_check` 地圖數 |
| （本報告） | 報告 |

沒有 stash、reset、amend、切換分支，沒有 push。事件 schema 沒變，`LOG_FORMAT` 維持 `/34`。

## 2. 地圖與遭遇

- 地圖 `bandit_lair`（盜賊巢穴，12×10，類型 `boss`）：高 2 的東側高台（x 9–11、y 3–6）＋高 1 台階（x 8）、西南角高 1 矮坡；兩個 2×2 岩漿池（致命地形）；兩個源泉格 (5,5)、(6,4)（中場，要往前搶）；兩根可推倒的石柱 (3,3)、(3,6)；木箱 4、油桶 2（台階前南北各一）、矮牆 2、倒木 2；第 3 輪結束時兩名盜賊從東北、東南角援軍（`spawn_units` 事件）。
- 單位 `bandit_warlord`（盜賊首領）：力量 18、體質 18、意志 14、HP 110（`bandit_boss` 為 80）、護甲加值 5（原 4）、物理抗性 150、`boss`＋`elite`＋`steadfast`，技能同 `bandit_boss`。數值為初值。
- Boss 戰編制：`[bandit_warlord, bandit, bandit_archer, bandit_shieldbearer]` ＋ 第 3 輪 2 名援軍（共 3 名手下 ＋ 援軍）。

開場地圖（`uv run trpg battle --map bandit_lair --seed 1`）：

```
    0  1  2  3  4  5  6  7  8  9  10 11
 0  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.
 1  0.  0.  0[  0.  0.  0.  0.  0[  0.  0.  0.  0.
 2  0.  0.  0.  0.  0~  0~  0.  0.  0_  0.  0-  0.
 3  0A  0.  0.  0|  0~  0~  0.  0&  0.  2b  2.  2.
 4  0B  0.  0.  0.  0.  0.  0$  0.  0d  2.  2a  2.
 5  0C  0.  0.  0.  0.  0$  0.  0.  0.  2.  2.  2.
 6  0.  0.  0.  0|  0.  0.  0~  0&  0.  2c  2.  2.
 7  0.  0.  0.  0.  0.  0.  0~  0~  0_  0.  0-  0.
 8  0.  1.  1[  0.  0.  0.  0.  0.  0[  0.  0.  0.
 9  0.  1.  1.  0.  0.  0.  0.  0.  0.  0.  0.  0.
  圖例：[ 木箱、- 倒木、_ 矮牆、& 油桶、| 石柱、$ 源泉、~ 岩漿
  a 盜賊首領 b 盜賊 c 盜賊弓手 d 盜賊盾衛（敵）；A 戰士 B 弓手 C 法師（我）
```
（每格左邊數字為高度。）

## 3. 驗收條件（7.2、7.4 的 3-5b）

1. **內容驗證與卡路檢查通過**：`uv run trpg content check` 通過；`uv run python scripts/map_push_check.py --maps bandit_lair` 狀態「通」，單次移動不封路、推倒不封路；`tests/content/test_bandit_lair.py::test_lair_passes_content_validation_and_has_the_required_features`（`check_map`、岩漿、高 2、源泉、石柱／木箱／油桶、援軍事件）；`tests/sim/test_push_check.py::test_official_maps_are_all_connected_and_the_table_renders` 通過（地圖數 11 → 12）。
2. **不進一般抽選**：`test_lair_stays_out_of_the_general_pool_lists_and_sims`（不在 `map_pool`、`default_sim_maps`、`playable_maps`）；`test_a_run_plans_the_boss_battle_on_the_lair`。
3. **Boss 遭遇**：`test_boss_uses_the_lair_and_the_warlord`（`roguelite_problems` 空、頭目 `boss`＋`elite`、HP 高於舊頭目、手下 3–4 名）；`test_lair_battle_runs_to_the_end_and_reinforcements_arrive`。
4. **sim 10 場無異常**：見下。
5. `uv run python scripts/check.py` 全過（pytest 3038 通過、client vitest 191 通過）。

### sim 結果

`uv run trpg sim maps --maps bandit_lair --seeds 10`（預設陣容：戰士、弓手、法師 vs 編制）：

```
勝負：我方 3（30.0%）／敵方 7（70.0%）／平手 0
輪數：平均 7.90、中位數 7.5、最小 5、最大 15
DPR：我方 25.06／敵方 17.84；受環境傷害：我方 1.20／場、敵方 7.50／場
異常：long_battle ×2（種子 2、9），one_shot ×1（種子 8）——皆為資訊性旗標，無例外、無 max_actions
```
平均輪數 7.9 落在目標 6–10。勝率 30% 偏低（只記錄不調）。注意：油桶位置從 (7,4)(7,5) 改到 (7,3)(7,6) 前，勝率是 90%、平均 11 輪——開場法師炸油桶會直接重創盾衛；結果對單一物件很敏感，10 場樣本也小。

`trpg run auto --seed 0…9`（自動代打）：10 場中 3 場打到 Boss（種子 3、6、8），皆敗於 Boss（6 輪左右被擊敗）；其餘敗在第 2–5 場（與 3-5a 相同，HP 不回復的累積）。`--seed 0 --build build_banisher` 完整打贏（Boss 戰 12 輪）。

## 4. 複雜度 noqa

沒有新增或移除（總數前後都是 11）。

## 5. 修改既有測試期望值

- `tests/roguelite/helpers.py` 的 `VICTORY`：`("build_fire", 0)` → `("build_banisher", 0)`。換了 Boss 地圖與頭目後原組合在 Boss 戰失敗，找出能完整打贏的 build 與種子。
- `tests/content/test_roguelite_content.py`：兩處原本拿 `ruined_fort` 當 Boss 地圖來測「Boss 地圖不可在池內」與「起始區放不下」，改用 `bandit_lair`（敵人改 6 名，因起始區有 5 格）。
- `tests/content/test_map_archetypes.py`：`ARCHETYPES` 多了 `boss`；「10 張正式地圖」排除 `boss`。
- `tests/engine/test_source.py`：精英清單多 `bandit_warlord`；有源泉的地圖多 `bandit_lair`（測試改名為 `test_only_the_boss_units_are_elites_in_content`）。
- `tests/sim/test_push_check.py`：非測試地圖數 11 → 12。

## 6. 待 PM 決定

1. **新增地圖類型 `boss`**：為了讓 Boss 地圖不出現在 `sim maps`／`sim matrix` 預設清單與網頁一般地圖列表，新增了 `boss` 類型（改了 `maps.py`、`cli/sim.py`、`api/sessions.py` 各幾行；規格說「原則上只改內容」）。替代做法是沿用 `ruined_heights`，但會污染矩陣的類型統計。
2. **勝率 30%（預設陣容）**：偏難，且對開場油桶位置很敏感（90% ↔ 30%）。依規格只記錄不調；平衡階段再決定是否降低首領 HP 或援軍人數。
3. **`run auto` 的 Boss 戰**：10 種子只有 3 場打到 Boss，AI 代打到 Boss 時多半資源已耗盡，Boss 難度是否合適要等 3-6 人工試玩。
4. **`bandit_warlord` 技能沿用 `bandit_boss`**（劈砍、疾風踢），只調高數值；要不要加專屬技能（例如推擊、召喚）留給後續。
5. **援軍固定 2 名盜賊、第 3 輪**：沒有多次援軍或隨輪數增強；援軍出現在東側角落，離我方遠。
6. **岩漿與石柱的互動效果沒有專門測試**（沿用既有的推擊、致命地形機制）；只測地圖含這些元素。
7. **Boss 地圖可用 `trpg battle --map bandit_lair`、`sim maps --maps bandit_lair` 明確指定**，但不出現在網頁的地圖選單（`playable_maps` 排除）。若 PM 想在網頁手動選來測，要放行。
