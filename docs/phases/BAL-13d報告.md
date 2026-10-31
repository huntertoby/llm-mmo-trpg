# BAL-13d 報告：弱 build 修正＋BAL-13c 收尾

依 `docs/phases/PhaseBAL計畫.md` 第 8 節「BAL-13d」1～6 項與「BAL-13d 併入 BAL-13c 收尾」7～9 項（06 6.5「BAL-13c 定」）。產出放 `docs/phases/BAL-13/13d_*`。

## 1. 各項做了什麼

**1. seer 行為模式**（`497e5eaf`）
- `content/ai_profiles.yaml` 新增行為模式 `seer`（權重與 `cunning` 相同），只覆寫 `rewrite: {mana_points: 0, cooldown_points: 1}`；`build_seer` 改用它。表格層級的 `rewrite` 不動。
- `AiProfileTable` 的合併改成逐欄合併：行為模式自己寫的 `rewrite:`（以及 `trap`、`gamble` 等同類表）只蓋掉寫到的欄位，其他欄位沿用表格層級的值。原本會整張換掉，沒寫的欄位會退回程式預設值。現有行為模式都沒寫這些表，所以沒有影響。

**2. 狂怒姿態 AI**（`src/trpg/engine/ai/stance.py`；數值在 `ai_profiles.yaml` 的 `stance:`）
- 只套用在 `risky_statuses: [stance_fury]`。其他姿態維持原狀，AI 一樣不主動取消。
- 進入條件：有敵人在「2 回合可達範圍」內（曼哈頓距離 ≤ 2 × 速度 ＋ 普攻射程），而且當下不符合取消條件。
- 取消條件：HP < 40%，而且 6 格內有敵人（「附近」沿用 `self_cost` 的 6 格）。符合時回合一開始就 `EndStance`，不花 AP。

**3. 孤注一擲／捨身突刺**
- `gamble.cautious` 的範圍擴大：有任何失手反噬的技能都算，不再只限反噬會造成傷害的。孤注一擲失手是倒地，現在 HP < 30% 時也會照既有的 `low_hp_permille`（100‰）壓低分數。
- 捨身突刺的自損估值：原本自身易傷借用了「對敵人施加易傷」的價值 6，等於把 1 回合有效易傷當成自損約 15 HP。實際估算如下：BAL-13b 量到 gambler 每輪受到約 13 傷害，×25% ≈ 3.3 HP；照 `hp_cost` 的慣例用 `friendly_fire` 權重 4 計 ≈ 13 分，相當於 damage 權重 10 × 1.3。判定是高估，改成 `self_status_values: {stun: 5, vulnerable: 1}`。只有捨身突刺用到自身易傷。修正後捨身突刺的使用從每場 0.03 次升到 0.69 次，每 AP 傷害 5.6，是 gambler 最高的一招。

**4. 預算 6.5：瞬步與背刺條件**（`80562066`）
- 新欄位 `ConditionDef.budget_permille`：填了就取代 harshness 對應的條件倍率。`from_behind` 的 harshness 仍是 `common`，所以武器親和判斷不受影響。
- 試值用 `scripts/bal13d_backstab.py`。每組係數下，背後加成都取預算上限內的最大值，再實測 assassin 300 場（10 圖 × 種子 0～29）。完整表在 `13d_backstab_measure.md`：

| 瞬步點數 s | 背刺條件 c | 背後加成 | 預算比例 | 每 AP 傷害（普攻） | 倍數 |
|---|---|---|---|---|---|
| 4（原） | 850（原） | 500（原） | 85.0% | 2.35（3.38） | 0.69 |
| 4 | 850 | 900 | 99.4% | 3.44（3.39） | 1.01 |
| 3 | 750 | 1200 | 99.1% | 3.74（3.36） | 1.12 |
| **3** | **700** | **1300** | **99.5%** | **4.09（3.39）** | **1.21** |
| 3 | 650 | 1400 | 99.5% | 4.16（3.29） | 1.26 |
| 2 | 700 | 1500 | 99.4% | 4.31（3.21） | 1.34 |
| 3 | 550 | 1650 | 99.4% | 4.43（3.24） | 1.37 |

- **採用達到 1.2 倍的最小改動**：`shadowstep.base_points` 4 → 3，`from_behind.budget_permille` 850 → 700，`skill_shadow_backstab` 的背後加成 500 → 1300‰（背後命中時總倍率 1.5 → 2.3）。
- **其他預算比例改變的技能**（內建 301 招中只有這三招）：`skill_shadow_backstab` 85.0 → 99.5%，`skill_shadow_ambush` 86.3 → 79.6%，`skill_crossing_slash` 86.7 → 79.7%。**沒有技能掉出 70～100%。**
- 每 AP 傷害的口徑：英雄這招造成的傷害 ÷ 施放次數 ÷ AP，含未命中。普攻是英雄普攻傷害 ÷ 擲骰數。`13d_skills.md` 的批次報表也有每 AP 傷害一欄（瞬步背刺 3.1），但那是另一種口徑，不能和上表直接比。

**5. 沒有價值的技能**：只量測，見第 3 節。

**7. 連鎖的非威力效果點數維持舊倍率**（`fa0fac40`）
- `ShapeBudget` 新增 `non_power_by_value_permille` 與 `power_primitives` 兩個欄位。連鎖形狀上，`power_primitives` 以外的效果維持舊倍率（1250／1500／1750）。`power_primitives` 是引擎會乘連鎖衰減的原語：damage、heal、shield、hurl_object、charge_through，再加上加在傷害上的 consume_stack。
- 內建技能沒有帶狀態的連鎖技，行為快照不受影響。

**8. 被每輪一次擋下的擴散寫入紀錄**
- 新事件 `conduct_blocked`（`unit_id`、`source_id`）。戰鬥紀錄寫一行「⚡ X 已受過本輪擴散（每輪最多一次），這次的擴散沒有傷害」，數值不變。
- 互動表產生擴散時，不再先濾掉本輪已受過擴散的單位，改成結算時擋下並發出這個事件。

**9. 技能卡形狀行**：連鎖形狀行後面加「每跳 −25%」，數值從 `core.yaml` 讀，例：「連鎖（跳躍距離 3，跳躍 2，射程 5，每跳 −25%）」。

**紀錄格式**：`LOG_FORMAT` /93 → **/94**（新事件種類）。測試字面值 11 處、roguelite 夾具 1 處一起改；`runner.py` 文件字串與 `戰鬥紀錄格式變更.md` 也補上這一版。

## 2. 重量：全矩陣（23 build × 10 圖 × 30 場、新判定）

分兩批跑（`scripts/bal13d_matrix.py run`，各 527 秒／405 秒），再用 `bal13c_matrix.py merge` 合併：以 12d 為底，所有格子都換成本次結果。產出在 `13d_matrix_a.json`、`13d_matrix_b.json`、`13d_merge.txt`。

| build | 12d／13c | 本段 | 存活 | DPR |
|---|---|---|---|---|
| seer | 49.0 | **60.0（+11.0）** | 30 → 37% | 9.3 → 12.2 |
| gambler | 44.3 | **41.0（−3.3）** | 22 → 19% | 7.9 → 7.9 |
| assassin | 39.0 | **40.0（+1.0）** | 24 → 24% | 5.4 → 6.6 |
| storm | 73.0（13c） | **73.0** | 53% | 23.2 |
| winged（全表最低） | 39.7 | 39.7 | — | — |

- 其他 build 都和 12d／13c 相同。runeweaver 46.3、push 60.3，和 13c 一樣。
- **gambler 不是全表最低**：最低是 winged 39.7，其次是 assassin 40.0，gambler 41.0 排倒數第三。但 gambler 比之前低了 3.3 點，大約是 1.2 個標準誤：
  - 狂怒姿態雖然加了條件，拿掉它仍然 **+5.0**（41.0 → 46.0）。
  - 捨身突刺的使用變多（每場 0.69 次），自身易傷讓英雄更容易被打。存活率從 22% 降到 19%。
- **storm 仍是全類型前段**：8 類名次為 1／7／6／5／5／4／5／3。照規格標出，交玩法 PM 決定 `twin_strike`。
- 全類型前段只有 storm。無前段 8 個：assassin、striker、charger、banisher、gambler、winged、wallburn、runeweaver。seer 離開了無前段名單，在 bridge_chasm 拿到第 7 名、算前段。

## 3. 沒有價值的技能（只量測，不改）

使用率與每次效果取自全矩陣的批次報表（`13d_skills.md`，每個 build 英雄的每一招）。拿掉後的勝率用同種子 300 場量（`13d_ablate.md`），雜訊約 ±2.8 點。

| 技能（build） | 每場施放 | 每次效果 | 拿掉後勝率差 | 判定 |
|---|---|---|---|---|
| 竊取祝福（seer） | 0.79 | 傷害 2.2，只剝得到 `defending` | −0.7 | 沒有價值 |
| 竊取祝福（warlock） | 0.45 | 傷害 4.4 | +1.3 | 沒有價值 |
| 破魔（seer） | 0.48 | 傷害 2.5 | +1.0 | 沒有價值 |
| 照明彈（seer） | 0.21 | 13b 量到揭露 0 次 | −1.7 | 沒有價值 |
| 疾時之潮（seer） | 0.16 | 只對自己回復 | −0.3 | 沒有價值 |
| 專注湧流（seer） | 0.00 | seer 模式下不再使用 | — | 沒有價值 |
| 孤注一擲（gambler） | 0.30 | 每 AP 1.8（普攻約 3.4） | −0.3 | 沒有價值 |
| 狂怒姿態（gambler） | 0.85 | — | **+5.0** | 負價值 |
| 狂怒姿態（assassin） | 0.78 | — | +0.3 | 沒有價值 |
| 灼傷之痕 `searing_scar`（fire，修正型） | — | — | −1.3 | 雜訊內 |
| 颶風踢 `gale_kick`（push） | 0.68 | 傷害 1.3 | −1.3 | 雜訊內 |
| 盾擊（wallburn） | 1.10 | 傷害 1.8 | +1.0 | 沒有價值 |
| 挑釁怒吼 `taunting_roar`（tank） | 0.80 | — | −2.0 | 雜訊邊緣 |
| **餘燼護體**（fire） | 3.63 | 護盾 | **−18.0** | **有價值**（點名查的，但不在名單內） |
| **餘燼護體**（telekinesis） | 2.51 | 護盾 | **−14.0** | **有價值** |

- 幾乎沒被用到的（每場 ≤ 0.05 次，拿掉等於沒拿，所以沒有做拿掉對照）：
  - support：重振號令 `rallying_cry` 0.00
  - warlock：噤聲 0.00
  - banisher：反咒 0.00
  - striker：雷霆終結 0.01
  - wallburn：撕裂傷口 `rupture` 0.01
  - assassin：前後夾擊 0.02
  - tank：破甲擊 0.02
  - gambler：先發制人 0.03、血祭重擊 0.05
  - bomber：不滅誓約 0.05
  - push：震地推倒 0.05
  - detonator：毒血迸發 0.05
- 修正型技能（例：餘燼循環、慈悲光束、重踏、穿木箭術）不會出現在施放次數裡。本段只量了灼傷之痕一招，其他沒量。
- 量測範圍只限各 build 英雄帶的技能。沒有被任何 build 帶到的內建技能，矩陣裡沒有資料。

## 4. 快照與夾具

- 行為快照 `refactor_3wr2.json` 重產，5 筆變動：
  - 完整技能 2／301：shadow_ambush、shadow_backstab。
  - 升階重配 3／301：crossing_slash、shadow_ambush、shadow_backstab。
  - 閃現 0／129。
- CLI 輸出快照 2 筆變動：`skills_list`、`skills_show_all`（瞬步背刺的倍率、連鎖形狀行）。戰鬥快照都沒變。
- client fixture：glossary、unitDolls、raceLooks、skill_icons 重產後內容都沒變。

## 5. 測試與檢查

- **新增測試**：
  - `tests/engine/test_ai_bal13d.py`：seer 模式合併、狂怒進入與取消、無代價姿態不受限、孤注一擲 30% 門檻、捨身突刺的自身易傷估值。
  - `tests/skillgen/test_backstab_budget_bal13d.py`。
  - `tests/narrative/test_chain_card_bal13d.py`。
  - 擴充 `test_chain_falloff_budget.py`（非威力效果用舊倍率）與 `test_chain_conduct_bal13c.py`（`conduct_blocked`）。
- **重挑種子**（斷言不改）：
  - `test_gamble.py`：種子 7 → 4。
  - `test_combo_resources.py`：seer 兩例在種子 0～79 都不再對自己回復，所以這個測試在戰鬥中讓 seer 改用 `cunning` 模式，種子 5 照舊。這個測試要驗的是「AI 會用回復技」，不是驗 seer 的行為模式。
- **結果**：
  - ruff check、ruff format --check、mypy（926 檔）、lint-imports（7 kept）通過。
  - pytest：engine＋narrative 4218 通過；skillgen＋content＋narrative（含 slow）5834 通過，重產快照前只有快照那 5 筆失敗；api＋cli＋roguelite＋sim＋架構 833 通過；CLI 輸出快照（slow）重產後通過。
  - 重播 `swamp` 種子 7 一致（100 個動作、303 個事件）。
- **模擬總時間約 33 分鐘**：背刺試值 8 分、全矩陣 15.5 分、拿掉對照 9.5 分。

## 6. 待 PM 決定

1. **（原型數值）gambler 41.0%（−3.3）**：狂怒姿態加了 AI 條件後，拿掉它仍然 +5.0。捨身突刺的估值修正後用得多，但存活率反而降了。要決定：自身易傷估值要不要折衷（例如 2～3）、HP +6、或改狂怒姿態本身（不改受傷 ×1.2 是本段的前提）。gambler 不是全表最低（winged 39.7 才是），所以照規格沒有標成「最低」。
2. **（原型數值）storm 73.0% 仍是全類型前段**：交玩法 PM 決定 `twin_strike`。
3. **（AI）「2 回合可達範圍」與「附近」的定義**：規格沒寫，我取最保守的做法。可達範圍是自己的速度 × 2 ＋ 普攻射程（曼哈頓距離，不算路徑）；附近是 6 格（沿用自暈條件）。另外補了一條：符合取消條件時也不進入，避免取消後又馬上重開。
4. **（AI）孤注一擲的「不賭」沿用既有的 `low_hp_permille` 100‰（壓低分數，不是完全禁用）**。要完全禁用的話，把 `gamble.low_hp_permille` 改成 0，但這會連帶影響血祭重擊與超載。
5. **（預算）背刺條件改用新欄位 `budget_permille: 700`，`harshness` 仍是 common**。另一個做法是直接把 harshness 改成 harsh（600），但那會改變武器親和的判斷。1.21 倍離門檻很近；要多一點餘裕可以改用 s=3、c=650、加成 1400（1.26 倍）。
6. **（範圍）連鎖的 `power_primitives` 清單是我列的**：damage、heal、shield、hurl_object、charge_through、consume_stack。detonate_runes、delayed_damage 這類不經過連鎖衰減的原語，算成非威力效果、用舊倍率。
7. **（量測）沒有價值的技能**：拿掉對照只做了 14 組（時間預算）。每場 ≤ 0.05 次的技能直接列名、沒做對照。修正型技能只量了灼傷之痕。餘燼護體拿掉 −18／−14，看起來很有價值。破魔、竊取祝福、照明彈三招在標準地圖組裡確實沒有作用（拿掉 ±1.7 內）。
8. **（文字）**：`conduct_blocked` 的紀錄句、技能卡的「每跳 −25%」都是實作者初稿；瞬步背刺的說明文字改成「多 130% 傷害」。
