# Phase 3-33a 報告｜召喚物現況模擬

> 規格：`docs/phases/Phase3計畫.md` 36.1；背景：`docs/design/06-技能.md` 6.29.1、6.29.7。**只加統計與腳本，沒有改任何戰鬥規則、數值、內容資料或事件格式。**

## 1. 交付

- **統計**（`src/trpg/sim/metrics.py`）：`BattleMetrics` 新增 `summons: tuple[SummonRecord, ...]`（每隻召喚物的 `owner_id`、`template_id`、`team`、`spawn_round`、`end`、`end_round`；`end` 為 `expired`／`owner_gone`／`limit`／`sacrificed`／`downed`／`survived`）與 `summon_damage(team)`（召喚物傷害，歸到施放者陣營、另列，仍包含在 `team_damage`）。全部由現有事件（`unit_summoned`、`summon_expired`、`unit_downed`、`damage_dealt`）推導；單隻召喚物的傷害、行動回合與存活輪數沿用 `UnitMetrics`（`damage_dealt`、`turns`、`alive_rounds`）。事件與紀錄格式沒有變。
- **批次**（`src/trpg/sim/batch.py`）：把 `run_batches` 的執行部分抽成 `run_outcomes`（回傳每批的 `BattleOutcome`），`run_batches` 行為不變。
- **模擬**（`src/trpg/sim/summon_report.py`）＋**腳本** `scripts/sim_summons.py`：開發者起始包 × 地圖 × 種子各一場；我方為該包主角（`new_dev_run`，Lv1）＋標準隊友，敵方為地圖預設陣容，效用 AI。
- **測試**：`tests/sim/test_metrics.py::test_summon_records_and_damage`（手工事件序列）、`tests/sim/test_summon_report.py`（同種子兩次結果完全相同、統計與 `summon_events` 對得上、無召喚包為 0）。

## 2. 重跑指令

```bash
uv run python scripts/sim_summons.py --jobs 4        # 預設：4 包 × 5 圖 × 4 種子 = 80 場（約 40 秒）
uv run python scripts/sim_summons.py --packs dev_spirit,dev_frost --maps swamp --seeds 8
```

預設包：`dev_spirit`（喚靈）、`dev_bulwark`（鐵壁，單手劍，普攻為主）、`dev_blaze`（烈焰，火焰法杖，技能為主）、`dev_hawkeye`（鷹眼，弓，遠程）。預設地圖：`open_plain`、`dark_forest`、`ruined_fort`、`swamp`、`narrow_halls`。種子 0–3。結果與 `--jobs` 無關。

## 3. 摘要表（4 包 × 5 圖 × 4 種子，每包 20 場）

| 起始包 | 勝率 | 平均輪數 | 主角 DPR | 我方傷害/場 | 召喚物傷害/場 | 召喚物占比 | 召喚次數/場 | 有召喚場數 | 平均存活輪數 | 平均行動回合 | 首召輪 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 喚靈 dev_spirit | 60% | 5.0 | 7.9 | 120 | 2 | 1.4% | 0.60 | 9/20 | 0.8 | 1.1 | 1.7 |
| 鐵壁 dev_bulwark | 50% | 5.7 | 5.7 | 121 | 0 | 0% | 0 | 0 | — | — | — |
| 烈焰 dev_blaze | 55% | 4.4 | 8.5 | 104 | 0 | 0% | 0 | 0 | — | — | — |
| 鷹眼 dev_hawkeye | 60% | 4.8 | 10.2 | 119 | 0 | 0% | 0 | 0 | — | — | — |

喚靈共召喚 12 隻，結束原因：被打倒 4、持續到期 3、戰鬥結束時還在 5。未完成（例外或動作上限）：0 場。

名詞：主角 DPR ＝ 主角自己造成的傷害 ÷ 存活輪數（不含召喚物）；存活輪數 ＝ 召喚物出現後經過的輪數（與 `UnitMetrics.alive_rounds` 同義）；首召輪 ＝ 有召喚的戰鬥中第一隻出現的輪。

## 4. 觀察

1. **目前的喚靈包幾乎沒有召喚物貢獻**：召喚物只占我方傷害 1.4%（每場約 2 點，每隻平均約 3 點）。喚靈的勝率與輪數和其他包同級，靠的是主角與隊友，不是召喚物。
2. **起始技能抽到什麼很關鍵**：種子 0、1、2 的喚靈主角起始技能含「喚起骷髏」（每種子約 4 場有召喚），種子 3 抽到「靈祭」＋火焰箭，**20 場中 0 次召喚**。也就是 4 個種子裡有 1 個根本沒有召喚技能（喚靈包兩個池只保證「召喚」關鍵字池抽一招，不保證是召喚技）。樣本只有 4 個不同主角，結論有限。
3. **召喚物很短命**：已結束的 7 隻中，4 隻在出現後 1～2 輪內被打倒，3 隻撐到期（3 輪）；平均只行動約 1.1 個回合、存活 0.8 輪。目前固定 HP 12～14 在 5 張圖的預設陣容下撐不到 2 輪。
4. **AI 召喚的時機**：首召平均在第 1.7 輪，幾乎都是第 1 輪開場就召喚（9 場有召喚的戰鬥裡，多數在第 1 輪）；第二隻通常等到第 4～5 輪（冷卻後），這時戰鬥常已接近結束，所以「戰鬥結束時還在」有 5 隻（占 12 隻的 4 成），這些幾乎沒有時間行動。換句話說同時 2 隻的上限在實戰中很少用到。
5. **按地圖**：召喚較多出現在 `dark_forest`、`ruined_fort`、`narrow_halls`；`open_plain`、`swamp` 的 4 個種子沒有任何召喚（原因多半是 2 的抽技能問題而非地圖，沒有再細分）。
6. 對照包的勝率差距（50%～60%）在 20 場樣本下屬雜訊範圍，不宜解讀成強弱。

## 5. 待 PM 決定

1. **樣本要不要放大**：4 種子只有 4 個不同的主角，而且其中 1 個沒有召喚技能。3-33g（召喚流對照）前，建議用「強制起始技能含召喚技」的專用對照包（`dev_starters.yaml` 的 `skills` 可直接指定），並把種子加到 8 以上；或確認要不要讓喚靈包的起始技能保證含召喚技。我沒有改 `dev_starters.yaml`。
2. **對照基準**：「長戰輸出不超過技能流與普攻流」的基準，建議以 3-33b 之前的本表為「召喚物 ≈ 0 貢獻」基線；3-33b 完成後同指令重跑即可比較。
3. **統計定義**：存活輪數目前取 `UnitMetrics.alive_rounds`（出現後經過的 `round_started`，同輪出現又消失為 0）。若 PM 想改成「出現到結束的輪數差 ＋ 1」，`SummonRecord` 已有 `spawn_round`／`end_round` 可直接算，不需改引擎。
4. **介面**：只做了腳本（`scripts/sim_summons.py`），沒有加 `trpg sim summons` 子命令（避免與同時進行的段在 `cli/main.py` 衝突）。要的話之後一小段即可補。
5. **Boss 戰與召喚物**：本次只跑一般預設陣容，沒有 Boss 地圖（規格也未要求）；3-33b 的 Boss ×2 傷害驗證需另外跑。
