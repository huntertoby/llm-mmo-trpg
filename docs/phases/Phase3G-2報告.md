# Phase 3G-2 報告：技能強化、普攻附加、武器特性強化（G2）

規格：`docs/phases/Phase3G計畫.md` 第 0、2、6 節；設計：`docs/design/08-裝備.md` 8.21.2.3～8.21.2.5、8.21.5.3、8.24。
分支 `worktree-agent-a586d30e5704b408c`（從 main 的 5fa60fc 分出），未 push、未合併。

## 新增與修改

| 檔案 | 內容 |
|---|---|
| `src/trpg/content/keyword_derive.py`（新） | 關鍵字推導核心（`derive_keywords`、`Facts`、`derive_from_facts`…）從 `trpg.skillgen.keywords` **搬到 content**：引擎不得匯入 skillgen，但技能強化要在戰鬥中依關鍵字選技能。`skillgen.keywords` 重新匯出同名函式，外部匯入不受影響 |
| `src/trpg/content/weapon_params.py`（新） | 武器參數路徑的修改（`set_weapon_param`）：整數欄位（`knockback`）、巢狀欄位（`armor_break.rounds`、`steady.hit`…）、特例 `range_mod.penalty`（距離修正的懲罰部分乘倍率）；詞條結算與載入時檢查共用 |
| `src/trpg/engine/gear_enhance.py`（新） | 第 3、4、5 類結算：`gear_status_duration`、`gear_keyword_damage_permille`、`gear_area_delta`、`attack_keywords`、`gear_attack_element`、`gear_on_hit_statuses`、`geared_weapon` |
| `src/trpg/content/library.py` | `Ruleset.keywords`（嵌入規則包）、`Ruleset.skill_keywords()`（依技能 ID 快取）；載入時檢查：技能強化的關鍵字 id、武器特性強化的武器與參數（見 #9） |
| `src/trpg/engine/modifiers.py` | `damage_permille` 改為 **所有來源合計** 的 +50% 上限；`damage_element` 接普攻附加；`shaped_skill` 接裝備的範圍加成；新增 `status_duration_bonus` |
| `src/trpg/engine/gear.py` | `gear_damage_parts`（裝備傷害分成加成／減益） |
| `src/trpg/engine/skills/interpreter.py` | `status_duration` 加上技能強化的持續回合 |
| `src/trpg/engine/weapon_traits.py` | 普攻命中附帶狀態；震退距離上限（`max_displace_distance`），超過的格數改為額外撞擊 |
| `src/trpg/engine/lifecycle.py` | `make_unit` 建立單位時套用武器特性強化 |
| `content/affixes.yaml` | `affix_kw_shock_area` 的關鍵字改為 `charged`；`affix_trait_longgun_pointblank` 的參數改為 `range_mod.penalty` |
| `content/items.yaml`、`content/units/gear_tester_g2.yaml` | 測試物品 `item_g2_hammer`、`item_g2_amulet` 與持錘測試單位（`--log-json` 驗收用） |
| `src/trpg/engine/runner.py` | `LOG_FORMAT` → `trpg-battle-log/41` |
| `tests/engine/test_gear_g2.py`（新，27 個）、`tests/cli/*`（`/40` → `/41`） | 測試 |

## 設計重點

- **技能強化（第 3 類）**：詞條的 `keyword`＋`direction`（create＝製造、exploit＝利用）對照推導結果選取技能；普攻只在詞條 `include_attack` 時選取，普攻的關鍵字由它的元素傷害與命中附帶狀態推導（同一份推導表，沒有寫死）。數字走 G1 的遞減（`diminished_total`）。
  - `status_duration`：技能施加該狀態時持續回合 +N（`_Cast.status_duration`）；普攻命中附帶的狀態也算。
  - `damage_permille`：進入 `modifiers.damage_permille`，和其他傷害加成一起受上限。
  - `area_delta`：進入 `shaped_skill`，沿用 `_grow`，被形狀最大值（6.6）約束。
- **傷害加成 +50% = 所有來源合計（G1 驗收 #4）**：修正型被動的 `damage_permille`、裝備的條件數值與代價型、技能強化的 **正值** 合計後截斷在 +50%；負值（減益）不受上限、直接相加。
- **普攻附加（第 4 類）**：`add_element` 只改物理普攻（修正技能的 `add_element` 優先；武器已有元素不變）；`on_hit_status` 在傷害結算後用 `ApplyStatusEffect` 施加（與破甲同路徑，不擲抵抗）。
- **武器特性強化（第 5 類）**：開戰（`make_unit`）時算一次，產生單位自己的 `WeaponDef`（存在單位狀態中，重播一致）。`delta` 加減；`scale_permille` 是「懲罰縮小」倍率，多件同 id 時 *縮小量* 依 100／50／25% 遞減（兩件貼臉詞條：縮小 50%＋25%＝75%）。改完重新通過 `WeaponDef` 驗證；暴擊範圍不低於 `caps.crit_range_min`（含站定的暴擊擴大）。
- **推擊距離上限 2**：普攻震退距離 > `max_displace_distance` 時，距離取上限，超過的每格改為一次額外撞擊（`PushEffect.extra_collisions`）。

## 逐條驗收

| 規格 | 證據（`tests/engine/test_gear_g2.py`，除非另註） |
|---|---|
| 3 `affix_kw_burn_duration` | `test_burn_duration_follows_the_keyword_not_the_skill_name`、`test_fire_bolt_burns_one_round_longer_with_the_affix`（實際施放，持續 +1）、`test_burn_duration_two_copies_still_one_extra_round`（遞減：1＋0.5 捨去仍 +1） |
| 3 `affix_kw_prone_damage` | `test_prone_damage_applies_only_to_skills_that_exploit_prone`、`test_keyword_damage_diminishes_by_copies`（100／150／175／175，第 4 件 0%） |
| 3 `affix_kw_shock_area`（受 6.6 範圍上限） | `test_shock_area_grows_a_skill_that_creates_charged`、`test_shock_area_never_exceeds_the_shape_maximum` |
| 4 `affix_attack_lightning`（法杖不出現） | `test_attack_lightning_changes_physical_attacks_only`、`test_attack_lightning_is_not_offered_on_elemental_staffs` |
| 4 `affix_attack_mark` | `test_attack_mark_applies_marked_after_a_hit`、`test_attack_mark_same_id_counts_once`、`test_attack_status_gets_keyword_duration_bonus` |
| 5 錘震退 +1、推擊上限 2 改撞擊 | `test_hammer_knockback_plus_one`、`test_hammer_knockback_over_the_displace_cap_becomes_collisions` |
| 5 斧破甲 +1 回合 | `test_axe_sunder_plus_one_round`（含兩件遞減） |
| 5 長槍貼臉懲罰減半 | `test_longgun_point_blank_penalty_is_halved`、`test_longgun_point_blank_two_copies_diminish`、`test_weapon_trait_changes_flow_into_the_hit_resolution`（命中 −2→−1、傷害 500→750 進入實際命中／傷害計算）；只對自己的武器：`test_weapon_trait_only_applies_to_its_own_weapon` |
| 暴擊範圍最低 18 | `test_crit_range_never_goes_below_the_cap` |
| 傷害加成 +50% 含技能修正型被動（G1 #4） | `test_total_damage_bonus_cap_includes_skill_modifiers`（被動 100＋玻璃 200＋強化 225＝525→500；沒有被動 425 不截斷）；G1 的 `test_damage_bonus_capped_at_50_percent_after_diminishing` 仍通過 |
| 暫定 id 對齊並開啟載入時檢查（G1 #9） | `test_unresolvable_trait_param_fails_at_load_time`、`test_every_whitelist_keyword_and_trait_resolves_against_the_content`；載入時 `_check_affixes` 對照關鍵字推導表與武器資料（錯的參數 `point_blank` 當場被擋，已修正為 `range_mod.penalty`） |
| 一場 `--log-json` ＋ `replay` | `test_g2_gear_battle_log_json_and_replay`；手動：`uv run trpg battle --map test_flat_6x6 --allies gear_tester_g2 --enemies bandit,bandit --seed 7 --log-json g.json` → `uv run trpg battle replay g.json` |
| 既有行為不變 | tests/engine、tests/cli、tests/api、tests/content、tests/skillgen 全數通過（見最終檢查）；沒有換任何種子 |

## LOG_FORMAT

`trpg-battle-log/40` → **`/41`**：規則包新增 `Ruleset.keywords`（關鍵字推導表）。戰鬥事件沒有新增；武器與裝備效果由裝備快照在開戰時算出。與 3-24b2、3G-G5a 合併時若也遞增，版號由 PM 處理（測試中寫死 `/40` 的五處已改 `/41`）。

## 新增的複雜度 noqa

**沒有**。

## 最終檢查

`uv run python scripts/check.py`：ruff check、ruff format --check、mypy、lint-imports、pytest、client install／typecheck／test 全部通過（「全部檢查通過。」）；`corepack pnpm -C client build` 成功（只有既有的 chunk 大於 500 kB 警告）。
新增測試 27 個（`tests/engine/test_gear_g2.py`）；順帶更新 `tests/content/test_equipment_content.py`（測試物品可掛第 3、4、5 類）、`tests/content/test_con_hp.py`（新單位 HP 表）。

## 待 PM 決定

1. **關鍵字推導搬到 `trpg.content`**：為了讓引擎依關鍵字選技能（引擎不得匯入 skillgen）。`skillgen.keywords` 保留重新匯出；若 3-24b2 也改 `skillgen/keywords.py`，合併時只需保留匯入段落。
2. **傷害加成上限的正負分開**：正值合計後截斷，負值不截斷直接相加（G1 是淨值截斷）。這會讓「+80% 與 −30%」得 +20%，而非 +50%。
3. **利用倒地的技能傷害 +N% 是無條件加成**（只要技能「利用倒地」，不看目標是否倒地）；而「利用倒地」包含 3-24b1 的通用規則（近戰武器傷害技），所以此詞條實際上對多數近戰技都生效。池太大的問題（3-24b1 待決 #2）在此同樣出現。
4. **現有「製造帶電」的技能沒有一個有可增長的形狀**（皆為單體、連鎖、十字），所以 `affix_kw_shock_area` 目前對內容庫技能實際沒有效果，只對改造後（例如工坊做的錐形／環形雷電技能）有效；測試用合成技能驗證。是否要補一個雷電範圍技能，請玩法 PM 決定。
5. **普攻的關鍵字推導只看元素與命中附帶狀態**（不看修正技能的 `add_element`）。火焰法杖的普攻視為製造點燃，但普攻本身不施加燃燒，所以「燃燒 +1 回合」對它沒有可延長的狀態。
6. **暴擊範圍下限 18 只在武器特性強化路徑上套用**（`geared_weapon`）：長槍站定 20−2＝18 加上背刺 −1 仍是 17（既有規則，未改，避免改變 3-24a2 行為）。是否要在最終暴擊判定處全域套用 18，請決定。
7. **`scale_permille` 的遞減解讀**：多件同 id 時，是「縮小量」（1000 − 倍率）依 100／50／25% 加總，不是倍率相乘。
8. **武器特性強化的數字（delta）**：同 id 兩件加總 1＋0.5 後捨去，仍 +1，所以斧、錘各自最多 +1（第 3 件 1.75 也是 +1）；要更高需要不同 id 的詞條。
9. **武器特性強化在建立單位時套用**：戰鬥中換武器（目前沒有）、或召喚物（沒有裝備）不受影響。
10. **武器特性說明文字**：預覽浮動卡（`preview.py`）讀單位實際的武器，所以強化後的數字會反映；但英雄面板與開局頁（`api/routes/content.py`、`run_presenter.py`）的 `weapon_traits_zh` 讀的是資料檔的原始武器，尚未反映裝備強化。這屬於 G4（顯示來源）的範圍，G2 沒有改 API 型別。
