# BAL-12a 完成報告｜build 與資源（只量＋建議）

規格：`docs/phases/PhaseBAL計畫.md` 第 7 節「BAL-12a」。**沒有改任何 content 檔與既有行為**；覆寫只在腳本的 library 副本（記憶體內）。

## 1. 交付

| 項目 | 位置 |
|---|---|
| 診斷與覆寫工具 | `scripts/skill_diagnosis.py`（`matrix`／`diag`／`trial`／`mana`；覆寫語法見檔頭） |
| 排名與統計輔助 | `scripts/matrix_ranks.py`（各類型第 7 名門檻、build 平均統計） |
| 新基線（地圖＋矩陣＋資源） | `docs/phases/BAL-12/12a_baseline.md`、`12a_baseline.csv`（檔內標題沿用「BAL-3」字樣，是腳本固定標題） |
| 診斷／試驗原始輸出 | `12a_diag.md`、`12a_diag2.md`、`12a_matrix_stats.txt`、`12a_matrix_ranks.txt`、`12a_trial1`～`6.md`、`12a_mana.md` |

規模：地圖 10 張×30 場；矩陣 23 build×10 圖×10 場；資源 5 build×3 情境×40 場（`--jobs 4`，約 9 分鐘）。重新排名用的參考矩陣只有 5 場（`12a_matrix.json`），試驗每組 10 場（單 build 約 ±5 個百分點雜訊）。

**注意兩個量測限制**：（1）每格只有 10 場、名次以「勝率、同分比英雄 DPR」排，前段判定雜訊很大（同一批 build 在 5 場參考矩陣與 10 場基線的「無前段」名單不同）；（2）法術技的 `multiplier_permille` 不影響傷害（引擎只用骰子＋屬性），法術技覆寫改用技能層級 `damage_permille`；趟 1、2 的法術傷害覆寫因此無效，已以趟 3 重做，下表只用有效的趟。

## 2. 新基線 vs BAL-3

| 指標 | BAL-3 | 新基線 |
|---|---|---|
| 地圖平均勝率／平均輪數 | 78.0%／4.31 | 61.7%／4.37 |
| 勝率在 35–65% 的地圖 | 2／10 | 5／10（另 lava_crossing、swamp 66.7%，ruined_fort 33.3%） |
| 矩陣 build 勝率 > 65% | 17／23 | 6／23（storm 85、fire 79、healer 76、summoner 74、telekinesis 73、detonator 70） |
| 矩陣 build 勝率 < 35% | 0 | 1（assassin 34） |
| 標準 1（全類型前段）| 0 | 1（storm） |
| 標準 2（無前段類型）| 5 | 8（push、assassin、striker、gambler、seer、bomber、winged、runeweaver） |
| fire Boss 法力不足 | 59.4% | 25.1% |
| summoner Boss 法力不足 | 47.4% | 19.4% |
| fire 長戰單體法力不足 | 38.3% | 5.3% |

難度與法力旋鈕（BAL-4 起）讓整體勝率下降、法力短缺大減；但「無前段」名單從 5 個變 8 個，且與 BAL-3 的名單只部分重疊（support、charger 這次有前段；push、striker、bomber、winged、runeweaver 沒有）。名單的變動主要是整體勝率下降後各 build 擠在同一區間、前段判定靠少量場次的排序，**不代表那些 build 突然變弱**。

## 3. 沒有前段類型的 build（assassin、support、charger、gambler、seer）

各 build 的平均統計（`12a_matrix_stats.txt`）與技能使用（`12a_diag.md`）：

| build | 勝率 | 英雄 DPR | 英雄存活 | 主要原因 |
|---|---|---|---|---|
| assassin | 34% | 7.2 | 10% | 英雄幾乎都死（承傷 48.6）；匕首 1d4 讓每招每次平均只有 2–4 傷害；`pincer_strike` 從不被用（夾擊條件 AI 湊不到）；其餘技能都有被用 |
| gambler | 48% | 6.0 | 22% | 存活 22%、承傷 57.6；招式強但傷害變異大；`blood_sacrifice` 命中只有 40% |
| seer | 38–47% | 8.0 | 24% | 六招中只有 `hex_bolt` 打傷害（每場 4.5 次×4.1）；其餘為偵測／補給類，輔助價值不被勝率反映 |
| support | 60% | 6.2 | 58% | 勝率正常；沒有前段是排名同分時比英雄 DPR（輔助 DPR 天生低）造成；這次基線 1 類、重排 2–3 類，屬雜訊邊緣 |
| charger | 47–52% | 7.1 | 32% | 位移技多（6 個主動技中 2 個完全不造成傷害，其餘每次只有 3–5）；前段在 0～1 類之間擺盪，屬邊緣 |

**覆寫試驗**（10 場／組；詳見 `12a_trial1/2/3.md`）：

| build | 覆寫 | 勝率 | 前段類型 |
|---|---|---|---|
| assassin | 基線 | 34% | 0 |
| assassin | 5 個攻擊技傷害 +30% | 35% | 0 |
| assassin | 傷害 +60% | 33% | 0 |
| assassin | 傷害 ×2（探測） | 24% | 0 |
| assassin | 所有技能冷卻 −1 | 31% | 0 |
| charger | 4 個攻擊技傷害 +30%／+60%／×2 | 48%／46%／44%（基線 47%） | 1／1／0 |
| gambler | 6 個攻擊技傷害 +30% | **55%**（基線 44%） | 0→1 |
| gambler | 傷害 +60% | 56% | 0→1 |
| support | `life_drain` 傷害 +50%（法術技，有效） | 67%（基線 60%） | 2→3 |
| support | 傷害 ×2 | 68% | 2→3 |
| seer | `hex_bolt`／`dispel_magic`／`blessing_thief` 傷害 +50% | **55%**（基線 47%） | 0→1 |
| seer | 傷害 ×2 | **66%** | 0→2 |

結論：
- **gambler、seer 是「招太弱」**：技能傷害 +30%（gambler）、+50%～×2（seer）就有明顯效果，建議採用。
- **assassin 不是技能傷害的問題**：傷害加到 ×2 也不升勝率，冷卻 −1 也無效；是英雄生存（存活 10%）與匕首基礎傷害（1d4）。需要改 build 組成（HP／護甲／武器）或讓 AI 保命，超出「技能數值」範圍。
- **support、charger 不需改技能**：前段判定本來就在邊緣。support 的結構性問題是量測規則（同分比英雄 DPR）。

## 4. 偏強的 build

| build | 勝率 | 主因 | 覆寫結果 |
|---|---|---|---|
| fire | 79% | 英雄傷害不是主因：六招傷害降 15%／30%／50% 勝率為 79%／71%／70%（DPR 14.6→9.9 還是 70%）。與 `oil_depot`、森林等地形／燃燒協同有關 | 無法用單一技能數值壓到 65% 以下 |
| summoner | 74% | **召喚物本身**：禁止施放三個召喚技（探測）勝率降到 54%（−20 點）；召喚持續 −1、召喚冷卻 +1／+2 都沒有效果（74%→72%／70%／74%），因為一場只施放約 1 次，冷卻與持續不是約束；`fire_wall` 傷害 −40% 也無效（75%） | 要動召喚物範本（HP、武器）或每場可召喚的數量，本段未試（需 PM 決定） |
| storm | 85%（標準 1：全類型前段） | `chain_lightning` 每次傷害 21.3，約為其他 build 技能的 2 倍；−30% 與 −50% 勝率都降到 75% | `chain_lightning` 傷害 −30%：85%→75%（前段 7→5） |
| healer | 76% | 英雄 DPR 2.9、治療 87／場、承傷 55；勝率來自治療與復活，不是傷害；未做覆寫（需要治療量覆寫的語法，本段未做） | 未試 |
| telekinesis、detonator | 73%、70% | 未試（detonator 英雄 DPR 21.2，僅次於 storm） | 未試 |

提示：許多技能被多個 build 共用（`hex_bolt` 4 個 build、`fire_bolt` 3、`shatter_blast` 3、`summon_spirit` 3、`raise_skeleton` 4）。**調這些技能會連帶改動其他 build**，本試驗只量被指定的 build，套用前需要重量全矩陣。

## 5. 火系法力費用（Boss 戰短缺目標 ≤ 20%）

`mana` 指令，Boss 戰，各 60 場（`12a_mana.md`；覆寫只改 build 英雄裝備的主動技）：

| 覆寫 | fire 法力不足 | fire 勝率 | summoner 法力不足 | summoner 勝率 |
|---|---|---|---|---|
| 基線 | 26.0% | 68.3% | 13.7% | 65.0% |
| 法力費用 ×0.9 | **18.5%** | 65.0% | 12.1% | 68.3% |
| 法力費用 ×0.8 | 15.8% | 66.7% | 10.2% | 70.0% |
| 個別：`fire_bolt` −1、`ashen_oath` −2、`gravity_burst` −1 | 20.5% | 66.7% | 12.6%（`summon_spirit` −2） | 66.7% |

×0.9 即達標，勝率沒有再升（68→65%，在雜訊內）。×0.9 四捨五入後實際是每個火系主動技約 −1（`fire_bolt` 6→5、`cinder_burst` 8→7、`ashen_oath` 12→11、`shatter_blast` 6→5、`detonate_burning` 6→5、`gravity_burst` 7→6）。

## 6. 建議值（皆為原型數值，由玩法 PM 決定）

1. fire 的主動技法力費用 ×0.9（等於各 −1）；Boss 短缺 26%→18.5%，勝率不升。
2. seer：`hex_bolt` 傷害 +50%（若不想動共用的 `hex_bolt`，改調只有 seer 用的 `dispel_magic`、並考慮替 seer 換專屬傷害技）；+50% 勝率 47→55%、前段 0→1 類；×2 勝率 66%。
3. gambler：六個攻擊技傷害 +30%，勝率 44→55%、前段 0→1 類。
4. storm：`chain_lightning` 傷害 −30%，勝率 85→75%。
5. support、charger：不改技能。assassin：不是技能數值問題（見下）。
6. summoner、fire、healer：沒有找到可只靠技能數值壓到 65% 的單一旋鈕，暫不建議動。

## 7. 待 PM 決定

1. **（原型數值）** 上面第 6 節建議值要不要採用；共用技能（`hex_bolt` 等）的連帶影響要先重量矩陣。
2. **（原型數值）** assassin：英雄生存 10%、匕首 1d4。要不要調 assassin 的 HP／護甲／AI 保命，或改拿雙匕首以外的武器；本段的技能傷害與冷卻覆寫都無效。
3. **（原型數值）** summoner 74%：召喚物本身撐 20 點勝率。要不要動召喚物範本 HP、武器，或限制一場的召喚數量；本段沒有試範本層級的覆寫。
4. **（規則）** 「前段」判定（6.8 標準）：每格只有 10 場、同分比英雄 DPR，雜訊大且對輔助／治療類不公平（support DPR 低而被排後）。是否改成較多場數、或同分改比團隊指標（隊友存活、治療／護盾量），屬量測規則，請玩法 PM 判斷；在此之前「標準 2」名單每次重量都會變。
5. **（原型數值）** fire 79% 沒有可用的單一技能旋鈕；若仍要壓，需要探究燃燒狀態／表面協同（超出本段）。
6. 趟 1 的最後一組（`@build:build_assassin,:cd=-1`）語法錯誤中止，趟 2 已用正確語法重做；趟 1、2 的法術傷害覆寫因引擎不套用 `multiplier_permille` 而無效，以趟 3 取代（紀錄保留供對照）。

## 8. 驗收

- `ruff check`、`ruff format --check`、`mypy`（兩支新腳本）、`lint-imports`：見提交紀錄最後一行檢查。
- 沒有改 content、`src/`、`flash_*`、`flash_templates.yaml`；沒有跑全量 pytest（沒有新增程式碼進入 `src/`）。
