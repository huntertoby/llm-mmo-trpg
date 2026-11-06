# Phase 3T-5 報告｜AI 施放純地形技能

實作者：implementer（sonnet）。規格：`docs/phases/Phase3T計畫.md` 3.6。起因：3-54e 待決 5（效用 AI 對純地形技能沒有評分）。

## 做了什麼

- **新模組 `src/trpg/engine/ai/terrain.py`**：
  - `is_terrain_only(skill)`：效果全是 `raise_terrain`／`lower_terrain`。
  - `terrain_estimate(...)`（候選估計，不跑引擎）：範圍內「有收益的對象」才納入候選，否則回傳 `None`。對象：敵人站在可下陷的格子（+3）、友方站在可隆起的格子（+2）、自己站在可隆起的格子且行為模式有 `height` 權重（+1）、坑旁有高出墜落門檻的敵人且我方有推擊技能（每名 +2）。高度 0 的格子降不下去、頂高的升不上去，這些格子不算。
  - `terrain_gains(...)`（預覽收益）：依預覽事件的 `terrain_changed`：站在該格的敵人被降低（或友方被抬高）每層 `height_points`、反過來扣；下陷造出的坑旁邊（施放後的高度）每名高出 `fall_damage_min_drop` 的敵人加 `pit_points`（我方有未冷卻的推擊／拉扯技能才算）。結果 × 行為模式的 `damage` 權重。施放者自己站的格子由位置價值既有的 `height` 權重處理，不重複計算。
- **接線**：`utility.py` 的 `_gains` 加一項（僅 `UseSkill`、非集火加成）；`_special_estimate` 對純地形技能呼叫 `terrain_estimate`。`coverage.py` 兩個原語的說明更新。
- **權重**：`content/ai_profiles.yaml` 新增表格層級 `terrain: {height_points: 4, pit_points: 6}`（`TerrainAiRules`，與 `form`、`rune` 同樣填入每個行為模式；`AiProfile`／`AiProfileTable` 都有欄位）。初值未經模擬。
- **不濫用**：沒有任何單位（或只有「錯的一方」）在範圍內、地面動不了、只有友方被降低、只有敵人被抬高，皆不是候選或分數 ≤ 0（技能的法力與冷卻成本照扣）。

## 測試

`tests/engine/test_terrain_ai.py`（12 個）：
- 表格：隆起／下陷 × 有收益（敵人被降低、友方被抬高）／無收益（範圍無人、只有友方被降低、只有敵人被抬高），同時驗候選與分數；友方在爆炸範圍內分數較低；高度 0 的地面無收益。
- 坑：敵人高 3、坑 1（十字一起降，落差 2）有推擊技能的分數高於沒有；落差只有 1 時有無推擊技能分數相同。
- 真實內容：`skill_earth_collapse` 在附近有敵人時是正分候選；一場含大地崩陷的 AI 對戰（施放者偏好大地崩陷）重播後事件、亂數狀態完全一致。

## 驗收

- `ruff check`、`ruff format --check`、`mypy`（783 檔）、`lint-imports`（7 kept）全過。
- pytest：`tests/engine` ＋ `tests/sim` ＋ `tests/content`＋架構測試 5386 passed；`-m "slow or not slow" tests/cli --timeout=3000` 154 passed。
- **戰鬥快照沒有變**（沒有使用 `UPDATE_CLI_SNAPSHOTS`）：預設陣容沒有純地形技能，行為不變。
- 沒有新增任何複雜度類 noqa（`_special_estimate` 差一個 return 超標，改成先判斷 `not is_terrain_only` 提早回傳 `_UNHANDLED` 避免）。

## 小樣本量測（不調數值）

腳本在 scratchpad（`terrain_sim.py`）：英雄法師（`hero_mage`，去掉最後幾個預設技能換上 build）對 2 個 bandit，6 張地圖（open_plain、cliff_outpost、ruined_fort、bridge_chasm、test_heights_8x8、narrow_halls）× 種子 1–8，共 48 場，最多 12 輪。「修改前」以把 `terrain` 權重設 0 模擬（等同沒有評分）。

| build | 版本 | 大地崩陷施放次數 | 被改變的格子 | 我方勝場 |
|---|---|---|---|---|
| 崩陷 | 修改前 | 0 | 0 | 22/48 |
| 崩陷 | 修改後 | 6 | 27 | 25/48 |
| 崩陷＋颶風推擊 | 修改前 | 0 | 0 | 23/48 |
| 崩陷＋颶風推擊 | 修改後 | 6 | 27 | 25/48 |

施放集中在有高低差的地圖（平地高度 0 降不下去）。勝場差異在樣本誤差內，不做結論。

## 待 PM 決定

1. 規格列的四個加分項中，「在敵人與我方之間造成高低差阻擋近戰」**沒有實作**（需要路徑與近戰判斷，收益不明；規格寫「例如」，選了保守的三項：降敵、抬友、坑旁推擊）。要不要補另開。
2. 隆起「讓我方遠程站高處」只透過位置價值的 `height` 權重（目前只有 archer 有）處理；施放者自己的格子不重複加分。若要讓隊友遠程單位也算，目前走 `height_points`（友方被抬高每層 4 × damage 權重）。
3. 友方被降低／敵人被抬高的懲罰與獎勵對稱（同一個 `height_points`），沒有分開調。
4. 「坑」的判定用「我方有未冷卻的推擊／拉扯技能」（不看射程、AP、推擊方向），是粗估；也沒有計算友方站在坑旁會被敵人推下去的風險。
5. 純地形技能以外的混合技能（含傷害又含地形）只套 `terrain_gains` 的收益，不走 `terrain_estimate`（它們本來就靠傷害進候選）。
6. 在高度 0 的平地，大地崩陷永遠不會被 AI 施放（降不下去、沒有 `terrain_changed`）；這是預期行為，但代表敵方要有高低差的地圖才看得到。
7. 勝率量測樣本小（48 場），權重 4／6 是初值，需要時由平衡階段調。
