# BAL-12d 完成報告｜套用 BAL-12a、前段判定改新量測方式

規格：`docs/phases/PhaseBAL計畫.md`「BAL-12d」。產出：`docs/phases/BAL-12/12d_matrix.json`（全矩陣，每格 30 場）、`12d_matrix_stats.txt`、`12d_matrix_ranks.txt`。

## 1. content 四項數值

| 項目 | 規格 | 實際套用 | 原因 |
|---|---|---|---|
| fire 主動技法力 ×0.9 | 逐招取整 | `fire_bolt` 6→5、`cinder_burst` 8→7、`ashen_oath` 12→11、`shatter_blast` 6→5、`detonate_burning` 6→5、`gravity_burst` 7→6 | 照規格。`fire_bolt`／`shatter_blast`／`detonate_burning` 是共用技能，連帶影響用到它們的其他 build |
| `hex_bolt` +50% | | **未套用（維持 1d8）** | 技能預算上限 100%：`hex_bolt` 現為 96.1%，1d10 就 110.8%，2d8 為 162.6%；`trpg content check` 與 `tests/content` 會失敗 |
| gambler 攻擊技 +30% | | `blood_sacrifice` 1200→1560、`all_in` 1800→2340、`first_strike` 1000→1300／1200→1560 照 +30%；`wild_blade` 2000→2560（+28%）、`berserker_rage` 1600→2020（+26%）、`reckless_lunge` 2800→3270（+17%） | 這三招 +30% 會超過預算上限（100.5%、102.5%、110.6%），取不超過 100% 的最大值 |
| `chain_lightning` −30% | | **未套用（維持原樣）** | 預算下限 70%：現為 75.0%，−30% 會變 52.5%（過弱）；下限內最多只能減約 6%（`damage_permille: 940`），而技能多了頂層 `damage_permille` 會讓提案來回測試（round-trip）少一個技能（265 < 下限 266），所以不套用這個無實質效果的小幅度 |

兩項（`hex_bolt`、`chain_lightning`）與預算規則衝突，見「待決」。測試：`test_gamble_schema`（預算期望值改讀 content 的倍率）、`test_skills_content`（`ashen_oath` 法力不寫死）、`test_budget_cli`、`test_skills_cli` 改讀 content。

## 2. assassin AI 保命與 HP

新增 AI 模式 `assassin`（`content/ai_profiles.yaml`；build_assassin 改用，原 `flanker`）：延用夾擊者權重，加 `keep_distance`（2 格內敵人扣分，使打完會退出敵人堆）、`shadowstep` 6／`shadowstep_behind` 3、`backstab` 6／`back_exposed` 6。以 20 場×10 圖量英雄存活率：

| keep_distance | 勝率 | 英雄存活 | DPR |
|---|---|---|---|
| flanker（原） | 34% | 10% | 7.5 |
| 3 | 40.5% | 6% | 7.3 |
| 12 | 37% | 11% | 6.5 |
| **30（採用）** | 37% | **20%** | 5.4 |
| 60 | 28% | 15% | 3.7 |

AI 保命後存活率最高 20%，仍 < 30%，所以照規格 **英雄 HP 44→53（+20%）**；HP 加上去後同樣 20 場量到存活 20%、勝率 36%，30 場全矩陣為存活 **24%**、勝率 39.0%（之前 34%）。匕首未動。存活率仍低，assassin 仍是最弱的 build（見待決）。

## 3. 前段判定新量測（06 6.8）

- `src/trpg/sim/matrix.py`：名次改為依勝場，勝場差 ≤ 1（與組內最高者比，不連鎖）視為同分，同分比「我方隊伍剩餘 HP 比例（含隊友、不含召喚物）」，再同分依檔案順序；類型層級用各地圖勝場合計；不再比英雄 DPR。
- 資料來源：`UnitMetrics.max_hp／final_hp`（不進序列化）→ `BatchReport.ally_hp_ratio` → `RawCell.team_hp_ratio`；`MatrixCell／ArchetypeCell` 新增 `team_hp_ratio`、`ArchetypeCell.ally_wins`。
- `trpg sim matrix --seeds` 預設 30、`BaselineSizes.matrix_seeds` 預設 30（`MIN_SEEDS_PER_CELL`）。
- 測試：`tests/sim/test_matrix.py` 改為「勝場、隊伍 HP」並新增勝場差 1／2 的案例。

## 4. 全矩陣重量（每格 30 場，23 build×10 圖，1118 秒）

| 項目 | BAL-12a 基線（10 場，舊判定） | 本次（30 場，新判定） |
|---|---|---|
| 勝率 > 65% | storm 85、fire 79、healer 76、summoner 74、telekinesis 73、detonator 70 | storm 79.7、fire 79.0、summoner 74.3、healer 73.3、detonator 71.3、warlock 69.0、telekinesis 69.0（support 64.3 邊緣） |
| 勝率 < 35% | assassin 34 | 無（最低 assassin 39.0、winged 39.7） |
| 無前段類型 | 8 個（舊判定、10 場） | 9 個：assassin、striker、charger、banisher、gambler、seer、winged、wallburn、runeweaver |
| 全類型前段 | storm | storm（1 個） |

（註：這次全矩陣量測時 `chain_lightning` 帶 `damage_permille: 940`，之後還原；對 storm 無實質影響。）

**fire 仍 79.0% > 75%**（法力費用降低後勝率沒有變低）；依規格標出，**另開一段查燃燒與地形協同**。gambler 44.3%（存活 22%）、seer 49.0%（存活 30%）、assassin 39.0% 都仍在「無前段」名單：新判定對勝場排序很嚴（30 場、差 ≤ 1 場才同分），弱勢 build 距第 7 名門檻通常 15–35 個百分點，本段調的數值不足以讓它們進前段。

## 5. 行為快照

BAL-12c 已合併（含 `flat_bonus`，不算本段）。重產 `tests/skillgen/fixtures/refactor_3wr2.json`，BAL-12d 造成 **28 筆變動**：
- 技能內容雜湊 11 筆：`all_in`、`ashen_oath`、`berserker_rage`、`blood_sacrifice`、`cinder_burst`、`fire_bolt`、`first_strike`、`gravity_burst`、`reckless_lunge`、`shatter_blast`、`wild_blade`。
- 閃現出題 5 筆：`blood_sacrifice@3@1`、`blood_sacrifice@5@2`、`fire_bolt@11@1`、`fire_bolt@3@1`、`fire_bolt@5@2`。
- 完整技能與升階重配 12 筆：上列各招加 `detonate_burning`（共 12 招，不含 `chain_lightning`）。

## 6. 待決

1. **（原型數值）`hex_bolt` +50% 與 `chain_lightning` −30% 與技能預算區間（70–100%）衝突**，目前取區間內的最大改動（兩者都不動）。若仍要這兩個幅度，需先決定是否調整預算區間或同時改該技能的代價（例如 `hex_bolt` 加冷卻、`chain_lightning` 降費用換取預算空間）。
2. **（原型數值）gambler 三招未達 +30%**（`wild_blade` +28%、`berserker_rage` +26%、`reckless_lunge` +17%）；gambler 全矩陣勝率 44.3%，未見 BAL-12a 試驗的 +11 點。
3. **（原型數值）assassin** 存活 24%、勝率 39%，仍最弱；AI 與 HP +20% 效果有限，下一步應考慮護甲、武器或其他保命技能。
4. **（原型數值）fire 79%** > 75%，另開段查燃燒與地形協同；summoner 不動（74.3%）。
5. 弱勢 build 的「無前段」在新判定下反而增為 9 個（舊 8 個、不同場數，不能直接比）；是否需要再放寬前段條件（例如前段名次、同分容許場數）請玩法 PM 判斷。
