# Phase BAL-20 報告：AI 估值表補燃燒（餘燼啃咬施放率）

依 `docs/phases/PhaseBAL-20計畫.md`（D1～D4，#149）。只改 `content/ai_profiles.yaml` 的一筆估值，引擎、技能資料都沒動。

**結論先講**：幼蜥的啃咬 0% → 59.3%，其他 4 種單位變動 ≤ 2 個百分點，和調查的試算逐字相同。**D4 ② 通過；D4 ① 用嚴格讀法不通過**（主量測 1020 場三組都在 ±3 個百分點內，但熔岩獸場景那組「灰燼瑪菈隨隊」+7.7 個百分點，另有兩格是單場翻轉造成 −3.3／−3.8）。照規格，**先不要合併**，交開發 PM 回玩法 PM 決定（見第 4 節與第 8 節）。

## 1. 交付與 commit

| commit | 內容 |
|---|---|
| `27717975` balance(bal20) | `content/ai_profiles.yaml` `status_values` 加 `burning: 3`（放在 `poison` 後面）；註解補 BAL-20 的理由，並把「沒列出的狀態（燃燒、倒地……）」改成「（倒地……）」 |
| `822a578e` test(bal20) | 新測試 `tests/engine/test_ai_burning_value_bal20.py`（行為一致測試，3 項） |
| `5d268584` test(bal20) | 既有測試的種子與全表比對（第 5 節） |
| （本報告的 commit） | 本報告；`docs/dev/上手-內容資料與模擬.md` 新增「AI 估值表」小節 |

### 行為一致測試（`tests/engine/test_ai_burning_value_bal20.py`）

場地：7×7 平地，我方戰士（HP 200，一擊打不倒、沒有反應）緊貼 T1 餘燼蜥（`ember_lizard`，莽夫），輪到餘燼蜥。實際呼叫 `score_action`（`engine/ai/utility/scoring.py`）。

1. `test_the_table_reads_burning_from_the_content_file`：用 `yaml.safe_load` 讀 `content/ai_profiles.yaml` 的 `status_values.burning`（不寫死數字），斷言是正整數、等於 `library().ai_profiles.status_values["burning"]`，而且每個行為模式拿到的都是同一個值。
2. `test_t1_ember_bite_outscores_a_plain_attack_on_the_same_target`：啃咬與普攻都合法，啃咬分數 > 同目標普攻分數。
3. `test_without_the_burning_entry_the_bite_loses_by_its_cost`（對照組）：把 `burning` 從行為模式的表拿掉，普攻 − 啃咬 ＝ 技能代價（耐力 10 × 500‰ ＋ 冷卻 1 × 1 ＝ 6 分，從技能資料與權重算，不寫死）。

改前（內容還沒改時）實跑：第 1、2 項失敗（啃咬 1129/9 ≈ 125.4 對普攻 1183/9 ≈ 131.4，低 6 分），第 3 項通過；改後 3 項全過。

## 2. 五種單位的啃咬每回合施放率（208 場，同種子配對）

做法照調查筆記（`bite_sim.py`：焦土外圍 0～5、焦油坑 0～3、焦油坑＋蜥群擴散 0～5、角魔祭壇 0～5、熔心坑 0～3，× 8 個底稿 build；程序池改 6）。改前數字與調查筆記的基準逐字相同，改後與筆記的做法 A 逐字相同。

| 單位（招式階級） | 改前 每回合施放率 | 改後 每回合施放率 | 改前 含灌注 | 改後 含灌注 |
|---|---|---|---|---|
| 餘燼蜥 `ember_lizard`（T2） | 64.5%（385/597） | 66.2%（423/639） | — | — |
| 殼縫餘燼蜥 `heart_ember_lizard`（T3） | 74.9%（158/211） | 75.3%（162/215） | — | — |
| 熔晶魅 `molten_wraith`（T2） | 24.9%（42/169） | 24.7%（42/170） | — | — |
| 熔爐母獸 `furnace_matriarch`（T2） | 5.7%（17/297） | 6.0%（15/249） | 36.4%（灌注 91 回合） | 40.2%（灌注 85 回合） |
| 餘燼幼蜥 `summon_ember_whelp`（T1） | **0.0%（0/435）** | **59.3%（253/427）** | — | — |

- 幼蜥另外收到母獸灌注後施放：53 → 55 次。
- 母獸自己放仍 < 10%，依 D2 算灌注（約 40%），不另處理。
- 這組 208 場的場景勝率：外圍 62→60%、焦油坑 44→47%、蜥群擴散 50→46%、熔心坑 81→81%、祭壇 100→100%。

## 3. D4 ②：三頭目每招每回合施放率（`cb2e_sim.py bosses --seeds 10`，240 場，同種子）

用 10 個種子（調查用 5 個）；分子／分母照實列。

| 頭目・階段 | 招 | 改前 | 改後 | 判定 |
|---|---|---|---|---|
| 霧鎖真人 P1 | `cluster_bolt`／`mist_shift`／`guardian_aegis` | 40%（200/499）／53%／89% | 40%（201/500）／53%／89% | — |
| 霧鎖真人 P2 | `mist_shift`／`mist_lock_peaks`／`cluster_bolt` | 24%（38/161）／38%／37% | 23%（37/162）／38%／36% | — |
| 霧鎖真人 P3 | `charged_cleave`／`first_strike`／`mist_rend` | 58%／40%／49% | 58%／39%／50% | — |
| 灰燼之心 P1 | `lava_spout` | **8.5%（51/603）** | **8.3%（49/593）** | 改前就 < 10%（不是這次跌破的） |
| 灰燼之心 P1 | `fire_bolt`／`ashen_oath` | 132%／10.4%（63/603） | 133%／10.3%（61/593） | `ashen_oath` 仍 ≥ 10%，餘裕極小 |
| 灰燼之心 P2 | `heart_inhale` | 15.3%（17/111） | **10.7%（12/112）** | 仍 ≥ 10%，掉 4.6 個百分點 |
| 灰燼之心 P2 | `heart_exhale`／`fire_bolt` | 31%／66% | 29%／70% | — |
| 灰燼之心 P3 | `heart_meltdown`／`heart_exhale`／`fire_bolt` | 17%／17%／33% | 19%／17%／36% | — |
| 碎晶之主 P1 | `thunder_clap`／`shard_erosion`／`spark_chain` | 25%／72%／89% | 26%／74%／92% | — |
| 碎晶之主 P2 | `rift_tremor`／`shard_erosion`／`cluster_bolt` | 23%／58%／19%（53/286） | 24%／56%／18%（51/278） | — |
| 碎晶之主 P3 | `rift_shatter`／`skill_blink`／`rift_tremor` | 21%／**0%**／68% | 23%／**0%**／68% | `skill_blink` 0% 是已知缺口，改前就是 |
| 碎晶之主 P4 | `rift_shatter`／`skill_blink`／`rift_tremor` | 26%／**0%**／53%（18/34） | 26%／**0%**／63%（22/35） | 同上 |

頭目勝率：霧鎖真人 95%→95%、灰燼之心 74%→72%、碎晶之主 74%→72%。

**D4 ② 判定：通過**——沒有一招是因為這次變更從 ≥ 10% 掉到 < 10%。但要注意：
- `heart_inhale` 掉到 10.7%（12/112），距 10% 只差 1 次；調查用 5 個種子量到 21→16%，樣本小，數字會跳。
- `lava_spout` 在 10 個種子的基準就是 8.5%（調查 5 個種子是 12%；CB-2e 也記過 40 場 12%、80 場 8%），是既有問題，不是這次造成的。

## 4. D4 ①：我方 fire build 與帶燃燒招的我方 AI 隊友勝率

「帶燃燒招的我方 AI 隊友」＝系統傭兵**灰燼瑪菈 `merc_chiyan`**（`build_fire`）；底稿 build 中只有 tank、guardian、healer 的隊伍帶她（`cb2e_sim.py` 的換隊，`default_party` 是盾衛＋醫者）。另列主角帶燃燒招的 striker（`skill_ember_brand`）。我方主角與傭兵都由效用 AI 操作，讀的是同一張估值表。

### 4a. 主量測：兩區一般營地（1020 場，`wr_sim.py`，同種子配對）

雲嶺 9 個地點、灰燼荒原 8 個（所有有戰鬥地圖、不是頭目的地點），每地點 × 5 個 build × 種子 0～11。

| 組 | 場數 | 勝率 改前 | 勝率 改後 | 變動 | 翻轉（輸→贏／贏→輸） |
|---|---|---|---|---|---|
| **fire 主角** | 204 | 78.4%（160） | 80.4%（164） | **+2.0 pp** | 4／0 |
| **灰燼瑪菈隨隊**（tank/guardian/healer） | 612 | 86.9%（532） | 88.6%（542） | **+1.6 pp** | 12／2 |
| striker 主角（烙印） | 204 | 82.8%（169） | 83.8%（171） | +1.0 pp | 3／1 |
| 　其中 tank／guardian／healer | 各 204 | 81.9／91.2／87.7% | 84.3／92.2／89.2% | +2.5／+1.0／+1.5 pp | 5/0、4/2、3/0 |

分區：雲嶺 540 場 97.6%→97.8%、灰燼荒原 480 場 69.6%→72.7%；1020 場中 922 場勝負與輪數完全相同。翻轉集中在焦油坑（8 輸→贏、1 贏→輸）。

### 4b. 熔岩獸場景（第 2 節那 208 場的勝負）

| 組 | 場數 | 改前 | 改後 | 變動 | 翻轉 |
|---|---|---|---|---|---|
| fire 主角 | 26 | 53.8%（14） | 50.0%（13） | **−3.8 pp** | 0／1（蜥群擴散 種子 2） |
| **灰燼瑪菈隨隊** | 78 | 69.2%（54） | 76.9%（60） | **+7.7 pp** | 8／2 |
| striker | 26 | 61.5%（16） | 57.7%（15） | −3.8 pp | 1／2 |
| 其他（storm/ranged/trapper） | 78 | 74.4%（58） | 66.7%（52） | −7.7 pp | 0／6 |

20 場翻轉中 14 場在「焦油坑＋蜥群擴散」（有母獸與幼蜥那組，調查也記過 48 場 14 場互換），其餘在焦油坑 5 場、外圍 1 場。這組的勝負主要受**敵方幼蜥行為改變**影響（幼蜥從推擊、走位改成啃咬），不是我方燃燒 AI 本身；但規格的條件只看「我方 fire build 與帶燃燒招的隊友」的勝率，沒有區分原因。

### 4c. 頭目戰（第 3 節那 240 場）

| 組 | 場數 | 改前 | 改後 | 變動 | 翻轉的格 |
|---|---|---|---|---|---|
| fire 主角 | 30 | 23 | 22 | **−3.3 pp** | 碎晶之主 fire 7→6 |
| 灰燼瑪菈隨隊 | 90 | 83 | 82 | −1.1 pp | 灰燼之心 healer 9→8、碎晶之主 guardian 10→8、tank 8→9、healer 9→10 |
| striker | 30 | 21 | 21 | 0 | — |

### 4d. 合計與判定

三組量測合計（1468 場）：fire 主角 197/260 → 199/260（**+0.8 pp**）；灰燼瑪菈隨隊 669/780 → 684/780（**+1.9 pp**）。

**D4 ① 判定：嚴格讀法不通過。**
- 主量測（1020 場）與合計都在 ±3 個百分點內。
- 但分開看有三格超過 3 個百分點：熔岩獸場景「灰燼瑪菈隨隊」**+7.7**（78 場，8／2 翻轉）；熔岩獸場景 fire −3.8（26 場、1 場翻轉）；頭目戰 fire −3.3（30 場、1 場翻轉）。後兩格是單場翻轉、樣本太小造成；第一格方向是我方變強，翻轉集中在蜥群擴散那組。
- 規格沒寫要用哪一張表、多少場判定，我照最保守的讀法判不通過，**沒有為了過關去改其他數值或換場景**。要用哪個口徑，由開發 PM 回玩法 PM 決定（第 8 節第 1 點）。

## 5. 改動的既有測試（都是 AI 軌跡的固定種子，斷言沒有放寬）

| 測試 | 改了什麼 | 原因 |
|---|---|---|
| `tests/engine/test_status_ai.py::test_status_values_are_defined_for_every_new_status` | 全表比對補一筆 `"burning",  # BAL-20` | 估值表多一筆，是這次變更本身（同 CB-2e 補 `concealed`） |
| `tests/engine/test_boss_phases.py::test_summit_battle_runs_all_phases_and_replays` | 種子 `[1, 3]` → `[1, 5]` | 我方法師（`hero_mage`：火焰箭、燼爆）重視燃燒後軌跡變了，種子 3 只打到第 2 階段（第 5 輪我方輸）。掃 0～12，仍到第 3 階段的是 1、5、8、11、12，取 5 |
| `tests/engine/test_displace_ai.py::test_an_ai_battle_with_a_void_swap_replays` | `open_plain` 種子 11 → 32 | 放逐流主角帶火焰箭，軌跡改變後種子 11 不再放虛空互換。掃 0～119，命中 32、119 |
| `tests/engine/test_scene_ai.py::test_an_ai_battle_with_a_topple_replays` | `lava_crossing` 種子 13 → 0 | 種子 13 不再推倒石柱。掃 0～119，命中 0、23、32 |
| `tests/cli/test_basic_actions_cli.py::test_open_plain_battle_uses_swap_and_aim_and_replays` | `open_plain` 種子 730 → 17 | 隊友法師軌跡改變後，種子 730 不再同時出現換位與瞄準。掃 0～1499，前 3 個命中是 17、95、129 |

全部是「某個種子會發生某事」的測試：換種子後斷言與重播比對完全不動。topple 那場沒有明顯帶燃燒招的我方單位（敵方是盜賊盾衛與弓手），沒有追是哪個單位的評分變了，只確認是軌跡改變、不是行為錯誤（第 8 節第 7 點）。

## 6. 驗收條件逐條

1. **交付 2 的測試過；AI 評分、內容與引擎相關測試檔過**：通過。跑的是 `tests/engine`、`tests/content`、`tests/world`、`tests/roguelite`、`tests/sim`（預設不含 slow）、`tests/cli`（不含 slow 的 `test_output_snapshots.py`）、`tests/test_architecture.py`、`tests/test_sim_scripts.py`、`tests/api/test_full_battle.py`、`tests/api/test_season_boss_api.py`（`-n 8`）：先跑一次 `-x` 抓到 `test_boss_phases.py`（換種子），再跑全部：8961 過、4 失敗（第 5 節其餘 4 項）；改種子後重跑這 6 個檔 65 項全過。`uv run trpg content check` 通過。
2. **靜態檢查與重播**：`ruff check .`、`ruff format --check .`、`mypy`（1441 檔無問題）、`lint-imports`（14 kept, 0 broken）結束碼 0；`trpg battle --map open_plain --seed 7 --log-json` ＋ `battle replay`：「重播驗證通過：91 個動作、383 個事件」。
3. **三張表齊全；D4 兩條逐條寫明**：第 2、3、4 節；D4 ② 通過、D4 ① 嚴格讀法不通過。
4. **沒有其他變動**：`git diff 91b323bd --stat` 只有 `content/ai_profiles.yaml`、新測試檔、第 5 節 5 個測試檔、本報告與上手筆記。量測腳本放在 worktree 的 `.scratch_bal20/`（gitignore），結束前刪除。

沒跑：CLI 輸出快照（`test_output_snapshots.py`，slow）與 `tests/api` 其他檔、`tests/bot`、`tests/server`。CLI 快照裡如果有固定種子的戰鬥用到法師或燃燒招，可能要重產對應的鍵，留給 PM 的全量。

## 7. 重現指令與耗時

腳本（未 commit，量完已刪）：`bite_sim.py`（調查筆記原檔，程序池 8 → 6）、`cb2e_sim.py`（`scripts/` 的副本，`JOBS = 8` → 6，內容不變）、`wr_sim.py`（新寫：匯入 `bite_sim` 的建角，把兩區 17 個地點加進場景，逐場存 `{勝負, 輪數}`，`compare` 子命令出配對表）。

```bash
export UV_NO_SYNC=1 PYTHONIOENCODING=utf-8
uv run python bite_sim.py run --out base_bite.json            # 208 場
uv run python cb2e_sim.py bosses --seeds 10 --out base_boss.json   # 240 場
uv run python wr_sim.py run --seeds 12 --out base_wr.json     # 1020 場
# 改 content 後同指令輸出 after_*.json
uv run python wr_sim.py compare base_wr.json after_wr.json
```

耗時（程序池 6）：改前 46＋58＋113 ＝ 217 秒；改後 38＋76＋143 ＝ 257 秒；冒煙（各 1 個種子）約 47 秒；換種子掃描約 3 分鐘。合計約 13 分鐘，在 30 分鐘內。

## 8. 待 PM 決定

1. **D4 ① 的判定口徑**：主量測 1020 場與合計都在 ±3 個百分點內；熔岩獸場景 78 場的「灰燼瑪菈隨隊」+7.7（我方變強，翻轉集中在蜥群擴散），另兩格是 26～30 場的單場翻轉。要用哪張表、多少場判定，請回玩法 PM；在這之前照規格不合併。
2. **`heart_inhale` 只剩 10.7%（12/112）**：這次掉 4.6 個百分點，距 10% 只差 1 次。要不要用更大的樣本（例 `--only ashen --seeds 30`）再確認。
3. **`lava_spout` 在 10 個種子的基準是 8.5%**（和 BAL-20 無關，改前就低於 10%），調查用 5 個種子量到 12%。CB-2e 待決 1 的老問題，建議另開。
4. **`ashen_oath` 10.3%（61/593）** 也貼著 10% 線，和第 2、3 點一起看。
5. `wr_sim.py`（兩區一般營地、指定 build 的勝率前後配對）**值得留在 `scripts/`**：AI 表的全域變更以後都要量「我方相關 build 的勝率」，`cb2e_sim.py conceal` 只涵蓋會隱蔽的單位。需要的話把它整理成 `cb2e_sim.py` 的子命令（`winrate --builds … --seeds N`）並補小規模實跑，另排一段。
6. `bite_sim.py`（啃咬施放率與不放原因的診斷）同理，可泛化成「某招每回合施放率＋原因」的通用腳本；目前只在 scratchpad。
7. topple 那場（`lava_crossing` 種子 13、`build_push`）軌跡改變的來源沒追；雙方都看不出帶燃燒招的單位。要確認的話用逐決策分數追一次。
8. CLI 輸出快照（slow）沒跑，PM 全量時若有戰鬥鍵變了，照慣例只重產受影響的鍵。

## 9. 沒驗證

- 只用底稿 build 與系統傭兵量，不代表真人玩家的勝率。
- 熔岩獸場景每 build 只有 26 場、頭目每格 10 場，分 build 的變動在誤差內。
- `blazing`（熾熱的）精英詞綴也帶這招，三組量測都沒有特別抽到。
- 帶 `status` 權重的模式（狡猾、輔助等）原本給燃燒 `status` 權重的分，現在改成 `damage × 3`；這部分沒有單獨量。

## PM 裁定（2026-11-12，玩法 PM；決定紀錄 #149）

- **BAL-20 通過，可以合併。**
- D4 ① 以**每組 ≥ 100 場的表與三組合計**判定：一般營地 fire +2.0、瑪菈 +1.6；合計 fire +0.8、瑪菈 +1.9，都在 ±3 內。不到 100 場的格子（熔岩獸 26／78 場、頭目戰 30 場）只看不判；超標的三格各只翻 1 場或方向是我方變強，不構成問題。**之後同類條件都照這個判法。**
- `heart_inhale` 10.7% 達標，不另加量；貼線主因是灰燼之心法力見底，併進那條平衡待辦。
