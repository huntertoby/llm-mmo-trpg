# X10-1 報告：×10 換算工具（還不改內容）

依據：`docs/phases/PhaseX10-1計畫.md`、`docs/phases/X10-影響盤點.md`（關鍵做法照做）、`docs/design/05-戰鬥.md` 5.4.1。
基準 `de10a8035`（開工前已 `git merge main`）。**沒有改任何遊戲數字**：`content/` 一個檔都沒動，只跑了 dry-run。
沒碰 `src/trpg/api/tuning/`、`content/sim/builds.yaml`（只列進清單）、`docs/design/`、`config/`。

## 1. 交付與 commit

| # | 項目 | commit | 檔 |
|---|---|---|---|
| 1 | 欄位清單＋涵蓋測試 | `eeb4fd343` | `scripts/x10/fields.yaml`、`scripts/x10/rescale.py`（掃描與分類）、`tests/test_x10_fields.py` |
| 2 | 換算腳本＋dry-run 預覽 | `38eb39076` | `scripts/x10/rescale.py`（改寫、驗證、防重跑、CSV）、`tests/test_x10_rescale.py`、`docs/phases/X10-換算預覽.csv` |
| 3 | 放寬上限 | `e74cb61d2` | `src/trpg/content/` 8 個檔、`tests/content/test_x10_caps.py` |
| 4 | 工坊調過的欄位 | `b812f0816` | `rescale.py --tuned-md`、`docs/phases/X10-工坊調過的欄位.md` |

### 腳本用法

```
uv run python scripts/x10/rescale.py --check          # 清單有沒有漏、衝突、過時（有問題時結束碼 1）
uv run python scripts/x10/rescale.py --stats
uv run python scripts/x10/rescale.py --dry-run --csv docs/phases/X10-換算預覽.csv
uv run python scripts/x10/rescale.py                  # X10-2 才跑：真的改 content/
uv run python scripts/x10/rescale.py --tuned-md docs/phases/X10-工坊調過的欄位.md
```

- 改寫用 `yaml.compose` 的位置只換數字那段文字（和工坊 `yaml_patch` 同一招；專案沒有 ruamel，也沒加相依）。註解、縮排、CRLF、BOM 都保留；改完重新 parse，必須等於「原資料只把那幾個值 ×10」，不對就整批不寫。
- 只換沒加引號的十進位整數；浮點、十六進位、加引號的會擋下。
- YAML 錨點（`&a`／`*a`）共用的數字只改一次；如果同一個錨點同時被 scale 和 keep 的路徑引用，整批拒絕（`skill_composer.yaml` 的白板 `vary` 有用錨點，已驗證）。
- **防止跑兩次**：改過的檔第一行加註解 `# x10: 量類已 ×10（scripts/x10/rescale.py，#169 題 10）`；`content/` 任何一個檔有這行就整批拒絕、一個檔都不寫（測試 `test_second_run_is_refused`）。
- 清單有任何問題（沒列到的數字欄位、同一欄位落在兩類、樣式或 group 沒對到東西）時，換算也拒絕執行。

## 2. 清單統計

`content/` 共 699 個檔，有數字欄位的 678 個，清單分 51 個 group。

| 類別 | 樣式（路徑）條數 | 數值個數 | 分布檔數 |
|---|---|---|---|
| scale（×10） | 98 | 1,839 | 516 |
| keep（不變） | 608 | 11,826 | 677 |
| pending（待定，先不 ×10） | 32 | 349 | 2（`ai_profiles.yaml`、`tuning_fields.yaml`） |
| unit_change（X10-2 手動改單位） | 2 | 2 | 1（`skill_budget.yaml`） |

- 數值個數以「YAML 節點」計（錨點共用的算一個；照路徑算是 scale 1,875）。
- 盤點標「未核對」的 `items.yaml`、`item_gen.yaml`、`world/loot.yaml`、`world/crafting.yaml`、`world/situations/*.yaml`、`flash_templates.yaml` 都逐筆看過：
  - `items.yaml`、`world/resonance.yaml`：只有屬性與最大 HP 詞條的 `value` ×10（依 `affix` ID 篩），抗性、條件 ‰ 不變。
  - `item_gen.yaml`：`stat_prices.attribute.per`、`stat_prices.max_hp.per`、`cost_prices.turn_start_hp_loss.per` ×10（點數不變＝「屬性 +10 ＝ 3 點」），其餘 ‰、點數、權重不變。
  - `flash_templates.yaml`：`rules.trigger_flat_bonus`（固定值 +1～+n）、`minor[stance_channel].rider` 回復法力的 `amount` ×10；其餘不變。
  - `world/loot.yaml`、`world/crafting.yaml`、`world/situations/*.yaml`：金幣、件數、等級、DC、‰，全部不變。
- **盤點沒列、這次找到的量類**：`skill_scaling.yaml` 的 `dual_max_gap`（主角第一、第二高屬性的差）、`core.yaml` 的 `attribute_perks.base`／`step` 與撞擊兩條 `per_tier`、`summon_traits.sturdy.armor_bonus`、`world/encounters/ashen_waste.yaml` 的 `armor_mods`（灰燼之心護甲 ±1）、`world/rules.yaml` 的 `enemy_growth.attribute_points_per_level`、`world/items.yaml` 法力藥水的回復量、`world/quests/*.yaml` 劇情技的法力費用、`units/*.yaml` 反應的 `self_stamina_below`、`interactions.yaml` 導電的 `min_damage`、`races.yaml` 機人的 `restore_choice`、狀態的 `shield_end_heal`／`shield_reflect`／`shield_break_lightning`、`tuning_fields.yaml` 中量類欄位的 `hint_min`／`hint_max`。
- `core.yaml` 逐項：`ability_mod_base/divisor`、`initiative_attr_base/divisor`、`hp_con_base`、`resources.base`、`resources.class_base.*`、`attribute_perks.base/step` ×10；`hp_per_con_point`、`resources.*.per_point` 不變（屬性差與上限一起 ×10，每點不變）；`summon_growth.hp_per_attr_mod` ×10（M 是屬性修正，本身不變，乘出 HP）。

## 3. dry-run

`docs/phases/X10-換算預覽.csv`：**1,839 筆，516 個檔**（欄位：`file,path,old,new`；路徑裡清單項有 `id` 就寫 `[id=…]`）。其中 134 筆是 0 → 0（例如武器 `flat: 0`、單位 `stamina: 0`），照列。

| 範圍 | 筆數 |
|---|---|
| `units/`（含 `summons/`） | 793 |
| `skills/` | 397 |
| `sim/builds.yaml` | 384 |
| `weapons.yaml` | 67 |
| `tuning_fields.yaml` | 30 |
| `world/` | 29 |
| `skill_composer.yaml` | 28 |
| `rules/core.yaml` | 24 |
| 其他 15 個檔 | 87 |

## 4. 預算要改單位的係數（給 X10-2）

**內容檔（清單的 `unit_change`，腳本不動，要手改）**

| 欄位 | 現在 | X10-2 要變成 | 說明 |
|---|---|---|---|
| `skill_budget.yaml` `allowance.mana_per_point` | 每 1 法力 5‰ | 每 10 法力 5‰ | 0.5 放不進整數，欄位格式要改（例如加 `mana_per`），`budget.py` 1338、1341，`flash_ops.py` 1466、1468，`options.py` 1312 的說明文字一起改 |
| `skill_budget.yaml` `restore_mana_point_permille` | 每點 700‰ | 每點 70‰（或每 10 點 700‰） | `budget.py` 469；現有回復量都是 10 的倍數，改 70 剛好等價 |

**內容檔（清單的 `scale`，腳本會 ×10，點數單位因此不變）**：`item_gen.yaml` `stat_prices.attribute.per`（1→10）、`stat_prices.max_hp.per`（4→40）、`cost_prices.turn_start_hp_loss.per`（1→10）。

**確認過不用改**：`allowance.stamina_per_mana`（耐力、法力一起 ×10，比例不變）、`allowance.stance_upkeep_per_point`（見待決 3）、`allowance.hp_per_permille`、`allowance.mana_cap`（‰）、`revive_hp_point_permille`（乘的是 `hp_permille`）、`collision_die_points`（骰子不變）、`summon_trait_*`（都乘骰子平均或 ‰）、`budget_reference_weapon_damage`、`tier_budget`。

**程式裡吃固定值的點數（X10-2 要 ÷10 再計）**

| 位置 | 吃的量 |
|---|---|
| `skillgen/budget.py` 406–407 | `effect.flat_bonus`（傷害、治療、護盾） |
| `skillgen/budget.py` 896–899 | 召喚物脈動 `pulse.heal_flat` |
| `skillgen/budget.py` 909 | 召喚物自爆 `blast.flat` |
| `skillgen/budget.py` 1338–1342 | `cost.mana`、`cost.stamina` × `mana_per_point`（見上表） |
| `skillgen/budget.py` 469 | 回復法力 `amount`（見上表） |
| `skillgen/flash_ops.py` 1466–1471 | 閃現代價換算的法力、耐力 |
| `skillgen/proposal_numbers.py` 263–278 | 補 `cost=1` 改 10（盤點第 4 節） |

## 5. 放寬的上限（交付項目 3）

| 欄位 | 舊 → 新 | 盤點有列 |
|---|---|---|
| `StatusDef.attack_bonus` | ≤10 → ≤100 | 有（battle.py 931） |
| `StatusDef.shield_reflect` | ≤5 → ≤50 | 沒有 |
| `StatusDef.shield_end_heal` | ≤10 → ≤100 | 沒有 |
| `StatusDef.shield_break_lightning` | ≤10 → ≤100 | 沒有 |
| `SummonDetonate.flat` | ≤20 → ≤200 | 有（1431） |
| `SummonPulse.heal_flat`、`shield_flat` | ≤10 → ≤100 | 有（1450、1452） |
| `ReactionDef.shield_flat` | ≤20 → ≤200 | 有（environment.py 565） |
| `FlashRules.trigger_flat_bonus` | ≤10 → ≤100 | 有（flash_templates.py 187） |
| `FormTable.upkeep_stamina`、`upkeep_mana` | ≤20 → ≤200 | 有（forms.py 253–259） |
| `FormTable.stance_upkeep_stamina`、`stance_upkeep_mana` | ≤10 → ≤100 | 有 |
| `SummonGrowth.hp_per_level`、`hp_per_attr_mod` | ≤20 → ≤200 | 沒有 |
| `SummonGrowth.flat_per_level_permille`、`flat_per_attr_mod_permille` | ≤5000 → ≤50000 | 沒有 |
| `SummonTrait.armor_bonus` | ≤3 → ≤30 | 沒有 |
| `ArmorMod.amount` | ±5 → ±50 | 沒有 |
| `ArmorMods.min_total`／`max_total` | −10～10 → −100～100 | 沒有 |
| `skills/constants.py` `_MAX_FLAT_BONUS` | 10 → 100 | 沒有（盤點列的是 yaml，見待決 1） |
| `RaceEffect.amount` | ≤10 → ≤100，但只有 `restore_choice` 能超過 10（新加檢查，其他效果仍 ≤10） | 沒有 |

只放寬上限、沒改預設值與內容。OpenAPI 與前端快照不含這些欄位，沒有快照變動。

## 6. 不變比對

- 放寬上限前後各跑 38 場 AI 對戰（15 張正式地圖 × 種子 1、7，再加 `open_plain` 種子 3 × 8 個 build），比對 `--log-json` 整份（動作、事件、最終狀態）與文字輸出：**different=0**（文字輸出只有「寫入路徑」那行不同，已排除）。
- 交付項目 1、2、4 只新增 `scripts/`、`tests/`、`docs/`，不影響戰鬥。
- 沒有快照、夾具變動。

## 7. 檢查（交件前，最後一個 commit）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（全專案，1732 檔） | 0 |
| `lint-imports` | 0 |
| `trpg content check` | 0（696 檔、434 技能通過） |
| `pytest tests/test_x10_fields.py tests/test_x10_rescale.py tests/content/test_x10_caps.py` | 0（53 passed） |
| `pytest tests/api/test_openapi_snapshot.py` | 0（2 passed） |
| `pytest -n 8 tests/content` | 0（3166 passed） |
| `pytest -n 8 tests/world -k "encounter or armor or race"` | 0（69 passed） |
| `pytest -n 8 tests/skillgen -k "flat or race or form or stance or summon"` | 0（562 passed） |
| `rescale.py --check` | 0 |
| `rescale.py --dry-run` | 0 |

沒跑全量 `check.py`、沒用 `-m ""`、沒做平衡量測。

## 8. 待 PM 決定

1. **`skill_primitives.yaml` 的量類上限沒在這段放寬**（盤點第 3 節列了 `flat_bonus` max 10、`restore_resource` amount max 10）。這兩個範圍會進 LLM 提示詞，`restore_resource` 的 amount 還是組合器的取值階梯：現在放寬，舊單位下組合器與 LLM 就會出 11～100 的數字，生成結果會變。改成在清單列為 scale，由 X10-2 和內容一起 ×10（`flat_bonus.max`、`restore_resource.amount.max` 10→100，min 留 1）。Python 端的硬上限 `_MAX_FLAT_BONUS` 已放寬。要改成這段就放寬的話告訴我。
2. **AI 的評分點數列為 pending**（`ai_profiles.yaml` 32 條、349 個值，連帶 `tuning_fields.yaml` ai 那組的 `hint_*`）。AI 分數＝預估傷害（HP）× 權重＋固定點數（`status_values`、`*_points`、`weights.*`…）。傷害 ×10 後兩條路：(a) 所有固定點數 ×10；(b) 引擎在 AI 評分時把傷害／HP ÷10，內容不動。建議 (b)（點數是「分數」不是量類，工坊調的值也不用換）。`summon.infuse_threat_damage`（和召喚物 HP 直接相加）已列 scale；若選 (b) 要改回 keep。
3. **姿態維持費**：`forms.yaml` 的 `stance_upkeep_stamina`／`mana`（每點維持費的耐力、法力數）×10，技能自己的 `stance_upkeep`（點數，≤2）不變。所以 `skill_budget.yaml` 的 `allowance.stance_upkeep_per_point` 不用改單位（盤點寫要改）。
4. **`summon_growth.flat_per_level_permille`／`flat_per_attr_mod_permille` 列 scale**（250→2500）：名字是 ‰，實際是「固定傷害 × 1000」。÷1000 捨去，新單位尾數更細（例：等級 2 舊 0、新 2），不是精確 ×10。
5. **組合器的法力範圍 ×10 會讓取值變細**：`skill_composer.yaml` 的 `spell_mana_per_ap` 2～4 → 20～40 等，組合器在範圍內抽整數，可選值從 3 個變 21 個，生成的技能會變（X10-2 預期內）。若要生成分布不變，改成「範圍不動、程式乘 10」。
6. **Python 預設值也是量類**（內容沒寫時用）：例 `FormTable.upkeep_stamina=5`、`upkeep_mana=3`、`stance_upkeep_*=2/1`、`SummonGrowth` 四個、`rules.py` `stamina_regen=5`、`environment.py` `infuse_threat_damage=4`、`world_encounters` `min_total=-5`／`max_total=5`。腳本只改 `content/`，X10-2 要一起改這些預設。
7. **標記註解加在每個改過的檔第一行**（516 個檔）。若不想動這麼多檔頭，可改成單一戳記檔（例如 `scripts/x10/applied.txt`），但檔被還原時擋不住。
8. **涵蓋測試會擋新欄位**：之後任何人（包括正在改 `builds.yaml` 的那段）新增數字欄位，`tests/test_x10_fields.py` 會失敗，要先在 `fields.yaml` 歸類。這是規格要的行為，合併時請注意。
9. **部位破壞的 `stat_down`**：`stat: armor` 時 `amount` 是護甲點數（量類），目前內容只有 `stat: damage_dealt`（‰），清單只列了後者；以後有人加 armor 版會被測試擋下。工坊 `parts[*].on_break[*].amount` 的建議範圍（1～999）不分 stat，先不變。
10. **工坊建議範圍**：量類欄位的 `hint_min`／`hint_max` 一起 ×10（例：最大 HP 1～999 → 10～9990、屬性 1～30 → 10～300）。

## 9. 平衡疑慮

- 換算不是處處精確 ×10：凡是「量 × ‰ ÷ 1000 捨去」的地方（升級 HP、召喚物成長、傷害倍率），新單位的捨去誤差相對變小，數值會比舊值 ×10 略高一點點。X10-2 回歸時勝率可能有極小差異，不是錯。

## 10. 工坊調過的欄位

`git log`（HEAD 的歷史）裡**沒有任何數值工坊寫回的 commit**（標題 `tune(` ＋ 結尾 `Tuned-by: number-workshop`），所以清單是空的。唯一長得像的 `dcd94d4ae tune(ai): close_range weight 40`（BAL-5）是手動 commit、沒有 `Tuned-by`，不算；那個欄位（`weapon_ai.close_range`）也在待決 2 的 pending 裡。X10-2／X10-3 開工前重跑 `--tuned-md` 即可更新。

## 開發 PM 裁定（2026-11-20）

合併：`Merge X10-1`（--no-ff）。合併後 ruff、mypy、x10 欄位涵蓋測試都是 0。

待決 10 件：
1. 接受。`skill_primitives.yaml` 的範圍列進 ×10，由 X10-2 跟內容一起換。
2. **選 (b)**：引擎評分時把量類（傷害、HP、護盾等）除以 `quantity_scale`，`ai_profiles.yaml` 和工坊裡 AI 那組的數字都不動。`infuse_threat_damage` 改回不變。
   - 理由：AI 的點數是抽象權重，逐項歸類容易錯；統一除掉，AI 的決策就和換算前一樣。
   - 待定的 349 個值全部改列「不變」。
3. 接受。
4. 接受。尾數變細，是 5.4.1 想要的效果。
5. **範圍 ×10，取值步距 10**：例如 2～4 變成 20～40，只取 20、30、40。生成的分布不變，內容檔也用新單位。步距用 `quantity_scale`。
6. 接受。Python 預設值由 X10-2 一起改。
7. **改成單一標記**：`content/rules/core.yaml` 加 `quantity_scale`。腳本看到它已經是 10 就拒絕再跑。516 個檔不加首行註解，單一檔被還原的情況靠 git 和涵蓋測試處理。
8. 知道了。QF-1 沒有新增數字欄位。
9. 接受。
10. 接受。
