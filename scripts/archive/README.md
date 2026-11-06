# scripts/archive：已結案的一次性量測腳本

CODE-1 I1（2026-11-06）從 `scripts/` 搬來：不被任何程式、測試、`check.py`、交接或部署文件引用，只在 `docs/phases/`、`docs/archive/` 的報告裡提到。
- 仍在 ruff／mypy 範圍內（本目錄的 `ruff.toml` 只放寬 E501，並把本目錄加進 `src` 讓同目錄互相匯入的腳本排序不變）。
- 用法說明的路徑已改成 `scripts/archive/…`；舊報告裡的 `scripts/<檔名>` 指的就是這裡的同名檔。
- 互相匯入的腳本一起搬（例如 `bal9_sweep`／`bal9b_boss`、`bal8_measure`、`f4_newbie_sim`、`season_boss_sim`、`skill_diagnosis`、`weak_build_audit`、`bal13c_matrix`、`bal15a_resources`），直接 `uv run python scripts/archive/<檔名>` 即可執行。

| 檔名 | 用途 | 對應段 |
|---|---|---|
| `ashen_waste_sim.py` | 灰燼荒原的小模擬（Phase 5F-5a；5F-5b 加候選內容、敵人高 2 級與灰燼瑪菈主角）。 | 5F-5a、5F-5b、RT-4 |
| `attrition_sweep.py` | 一輪消耗量測（BAL-6）：守點戰輪數／格子、第 3 場人數的模擬覆寫（不改 content）。 | BAL-6 |
| `backstab_counts.py` | 背刺次數對照表（Phase 3C-6a 8.2B）：10 張地圖 × N 種子，預設陣容與 ``build_assassin``。 | 3C-6a、3C-6b |
| `bal13c_matrix.py` | BAL-13c：重量用 chain／雷的 build，與其他 build 的既有全矩陣合併後重算前段判定。 | BAL-13c、BAL-13d |
| `bal13d_backstab.py` | BAL-13d 第 4 項：找「瞬步背刺每 AP 傷害 ≥ 普攻 1.2 倍」所需的最小預算係數改動（只在記憶體內覆寫）。 | BAL-13d |
| `bal13d_matrix.py` | BAL-13d：全矩陣重量（第 6、9 項）與「沒有價值的技能」量測（第 5 項，只量不改）。 | BAL-13d |
| `bal14a_summons.py` | BAL-14a：召喚批（B2～B5、summoner 74%、Boss 有召喚輪數）只量＋建議；覆寫只在記憶體內的 library 副本。 | BAL-14a、BAL-14b |
| `bal15a_pool.py` | BAL-15a：資源消耗與上限（B11 法力換耐力是否合理）——讀 ``bal15a_resources.py measure`` 的輸出。 | BAL-15a |
| `bal15a_resources.py` | BAL-15a：資源（法力）批只量＋建議；覆寫只在記憶體內的 library 副本，不改 content。 | BAL-15a、BAL-15b |
| `bal15a_table.py` | BAL-15a：把 ``bal15a_resources.py measure`` 的多個輸出併成「build × 覆寫」對照表。 | BAL-15a |
| `bal16_block_riposte.py` | BAL-16 追加量測：近戰 build 的格擋 vs 還擊（玩法 PM 2026-11-02，BAL-15c 驗收）。 | BAL-16 |
| `bal16a_boss.py` | BAL-16a：Boss 戰「頭目倒下、護衛撤退」（#86）前後對照（只量不調；頭目 HP 維持 content 的 700‰）。 | BAL-16 |
| `bal16b_heal.py` | BAL-16b：潮濕 × 治療（#93）前後對照——有治療技能的 build 勝率（只量不調）。 | BAL-16 |
| `bal8_measure.py` | 武器與 Boss 公平性量測（BAL-8）：只在記憶體內覆寫，不改 content 預設。 | BAL-8 |
| `bal8b_measure.py` | BAL-8b 套用後的複測（武器勝率／DPR、代價技使用率）；沿用 ``bal8_measure`` 的函式。 | BAL-8b |
| `bal8b_melee_boss.py` | 近戰能否摸到 Boss（BAL-8b；只量不調）。 | BAL-8b、BAL-9 |
| `bal9_sweep.py` | BAL-9 掃描：近戰朝 Boss 靠近權重（boss_approach）與 Boss 輪數旋鈕（只在模擬覆寫）。 | BAL-9 |
| `bal9b_analyze.py` | BAL-9b：分析 ``bal9b_boss.py --dump`` 的逐場記錄（輸場死因、援軍時機、AI 目標）。 | BAL-9b |
| `bal9b_boss.py` | BAL-9b：Boss 戰頭目 HP 倍率對照與輸場追蹤（只量不調；頭目 HP 只在模擬覆寫）。 | BAL-9b |
| `bal9b_pierce.py` | BAL-9b：弩穿透數（pierce_line）對勝率與 DPR 的影響（白板弩 vs 單手劍；10 圖 × 種子）。 | BAL-9b |
| `bal9b_targets.py` | BAL-9b：無召喚 Boss 戰的火力分配（我方打誰、誰打我方、各敵人何時倒下）。 | BAL-9b |
| `bal9c_boss.py` | BAL-9c：Boss 戰頭目 HP 700‰ 下，只調弱弓手護衛傷害（弓手護衛專用弓的骰面降階；只在模擬覆寫）。 | BAL-9c |
| `bal9c_pierce.py` | BAL-9c：弩穿透後方折扣（pierce_permille，pierce_line=5）對勝率與 DPR 的影響（10 圖 × 種子）。 | BAL-9c、DOC-A |
| `boss_phase_sim.py` | 雲頂觀 Boss 階段的小模擬（Phase 5F-2；``docs/phases/Phase5計畫.md`` 34.8）。 | 5F-2、5F-2b |
| `boss_support_sweep.py` | Boss 戰護衛與援軍量測（BAL-7）：只在模擬覆寫，不改 content。 | BAL-7 |
| `composer_rejects.py` | 組合器「驗證失敗退回」統計（Phase 2F-2 4.1）。 | 2F-2 |
| `consistency_offline_check.py` | 離線檢查（4-L11b）：用樣本 md 與被擋原句，比較舊／新一致性詞表與規則（不連模型）。 | 4-L11b |
| `difficulty_sweep.py` | 難度與法力旋鈕掃描（BAL-4）：只量不調。 | BAL-4 |
| `f4_newbie_sim.py` | 6F-4 C1／#128：新手任務鏈 3 場固定戰的自動打摘要（渡口石階、竹林小徑、雨中梯田）。 | 6F-4、6F-4b、6F-4c、6Q-A、MAC-1 |
| `f4b_starter_links.py` | 6F-4b：起始兩招的觸發關係（#129）前後對照。 | 6F-4b |
| `f4c_starter_links.py` | 6F-4c：起始兩招的觸發關係（#129）。 | 6F-4c、6F-4d |
| `f4c_terrace_sweep.py` | 6F-4c 第 6 項：雨中梯田巡邏的陣容掃描（新手第 3 步一路走過去）。 | 6F-4c、6F-4d、MAC-1 |
| `f4d_terrace_sweep.py` | 6F-4d 第 4 項：雨中梯田固定戰 ``terrace_clash`` 的陣容掃描（新手第 3 步一路走過去）。 | 6F-4d、MAC-1 |
| `f4d_witness_compare.py` | 6F-4d 第 6 項：witness 的兩條件建構（6F-4c ``condition_proposals``）前後對照，只用靜態建構。 | 6F-4d |
| `f4e_starter_links.py` | 6F-4e／6F-4f：起始兩招的觸發關係（#129）與第 1 招的分布。 | 6F-4e、6F-4f、6F-4g、6F-4h |
| `flash_converge_measure.py` | BAL-10d 收束的量測（只量不調；不改任何模板與規則）。 | BAL-10d |
| `flash_reclaim_measure.py` | BAL-10e 收回家族的量測（只量不調；不改任何模板與規則）。 | BAL-10e |
| `ice_slide_sim.py` | Phase 6E-2：冰面滑倒並滑行（#123）前後對照——冰湖地圖與冰系 build 的勝率（只量不調）。 | 6E-2 |
| `league_balance.py` | 5F-4b：影子循環賽的平衡候選（玩法 PM 2026-11-03 代決；只量不改 content）。 | 5F-4b |
| `leap_shortcuts.py` | 獸躍捷徑檢查（Phase 6R-1 驗收 C，#138）：每張戰鬥地圖與實地地圖輸出摘要表。 | 6R-1 |
| `make_vfx_fixture.py` | 產生前端技能特效測試用的資料（Phase 3-12）：隨機組合器的 20 個技能，各自在試玩場施放一次。 | 3-12 |
| `map_push_check.py` | 地圖卡路檢查（Phase 3C-1）：可推動物件會不會擋住我方到敵方的通路。 | 3-5b、3C-1、3C-5a、3C-5b、3D-3、3F-1 |
| `matrix_ranks.py` | BAL-12a：讀 ``skill_diagnosis.py matrix`` 存的 JSON，列各類型第 7 名門檻與指定 build 的差距。 | BAL-12a |
| `migrate_con_hp.py` | 一次性遷移（Phase 3-7）：引擎改為「最大 HP ＝ 範本基礎 HP ＋（體質 − 10）× 3」後的 content 遷移。 | 3-7 |
| `perf_complete_offer.py` | PERF-2：量完整技能三選一（``make_offer(..., "complete")``）的時間，並可用 cProfile 找熱點。 | PERF-2、PERF-3 |
| `race_matrix.py` | 種族勝率矩陣（Phase 6R-1 B，#138；玩法 PM「種族讓任務過易盤點」第 5 節 B）。只量不調。 | 6R-1、MAC-1 |
| `season_boss_diagnose.py` | 碎晶之主的敗因分析（Phase 5F-3b；``docs/archive/phases/Phase5F-3b報告.md``）。 | 5F-3b、5F-3c |
| `season_boss_sim.py` | 賽季 Boss「碎晶之主」的小模擬（Phase 5F-3；``docs/phases/Phase5計畫.md`` 37.9、19.7 #87）。 | 5F-3、5F-3b、RT-4 |
| `sim_objectives.py` | 勝利條件輪替的模擬摘要表（Phase 3-22，``docs/phases/Phase3計畫.md`` 24.1 第 5 項）。 | 3-22 |
| `sim_race_138.py` | #138 種族勝率比較（只量不調）：人類 ／ 舊狐族（現行規則）／ 新獸耳族（近似）。 | 6Q-A、MAC-1 |
| `sim_summons.py` | 召喚物現況模擬（Phase 3-33a）：開發者起始包 × 地圖 × 種子，輸出召喚物統計摘要表。 | 3-33a、3-33b、3-33e1、3-33e2a、3-33e2b、3-33f1 |
| `skill_balance_audit.py` | 技能模板不均衡分析（BAL-18，只讀、只量測；不改任何內容、程式與測試）。 | BAL-18、BAL-19a、BAL-19b、BAL-19c、BAL-19d、BAL-19e、BAL-19f、BAL-19g |
| `skill_diagnosis.py` | BAL-12a：build 與資源的診斷與記憶體內覆寫試驗（只量不調，不改任何 content）。 | BAL-12a |
| `synergy_audit.py` | BAL-13a：元素協同查修（只量不調，不改任何 content；覆寫只在記憶體內的 library 副本）。 | BAL-13a |
| `weak_build_audit.py` | BAL-13b：弱 build（gambler、seer、assassin）診斷（只量不調，不改任何 content、AI 與引擎）。 | BAL-13b |
| `world_leveling_sim.py` | 5A-SIM：練等手感與經驗曲線（代決初值；只量不改 content）。 | 5A-SIM |
| `verify_sandbox.sh` | 只給 Claude 雲端工作區用的驗證腳本（無法連 PyPI、無法 uv sync 的環境）。 | Phase 0 |
