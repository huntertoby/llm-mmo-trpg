# Phase KD-1 報告｜倒地改版（扶起、站穩、對抗變難）

> 規格 `docs/phases/PhaseKD-1計畫.md`；規則以 `docs/design/05-戰鬥.md` 5.13（#176）與 5.2.2（#177，基本動作上限 11）為準。基準 main `3581730ab`（含 E1、E2、E5），中途併入 `e9be9c6b6`（E5 驗收）、`07520b732`（#177）。

## 1. Commit

| 項目 | commit |
|---|---|
| 1 倒地的效果（不能反應、少 1 AP 只扣一次、單格頭目不扣；`prone_ap_due`；`LOG_FORMAT` `/137`） | `3e51e66c5` |
| 2 基本動作「扶起」（合法動作、AI、名詞表、前端「更多動作」） | `a4ec90318` |
| 3 站穩（站起或被扶起；擋下所有倒地來源，冰面照滑；前端退回畫法） | `ad5ea5d73` |
| #177 扶起算基本動作、上限 11（`BASIC_ACTION_LIMIT`） | `3fda34d36` |
| 3、#177 的測試補件（預算表、beneficial 清單、`test_vault` 上限） | `a5778c769` |
| 4 擊倒對抗守方 +3、平手算守方贏（含預覽） | `f32a8ff6d` |
| 5 震波、推倒壓到、藤蔓改成擲對抗 | `e3c84edab` |
| 6 冰面 DC 12 → 10 | `1ed8df99e` |
| 7 工坊欄位、AI 倒地估值、反應欄「倒地中，不能反應」、狀態與技能卡文字 | `1e190a8d1` |
| 8 E1 小修 1：技能列副標題只寫裝備名 | `78590aa8e` |
| 8 E1 小修 2：金框貼在卡片上 | `d4d092550` |
| 8 E5 小修 1：說明卡上方幾條底色不透明 | `e0401e9d2` |
| 8 E5 小修 2：金框、虛線框、卡片接成一張 | `95d11d24c` |
| 8 E5 補 1：被彈射擋下的那招，說明卡最後加灰字 | `e679af026` |
| 8 E5 補 2（8.29 E5 第 7 點）：一招只套一種變形，沒生效的變形加灰字 | `5ccfff69d` |
| 8 E2 小修 1：完全沒效果的加註改灰 | `e264652aa` |
| 8 E2 小修 2：加註懸掛縮排 | `f96d7cde1` |
| 8「擊中時」統一成「命中時」 | `cffc09270` |
| 戰鬥紀錄格式文件、上手筆記 | `e8853fe77` |
| 截圖 | `c32ae4be1` |
| 合併 main（HC-8、CR-1 計畫與設計文件，只有文件） | `f901ddbe1` |
| 全量檢查後的修正：AI 倒地估值 6 → 3、固定種子測試換種子、內容數量快照 | `d604c05d9` |
| CLI 快照、閃現一輪的種子 | `d683d317e` |
| 報告 | 最後一個 commit |

## 2. 倒地來源一覽（施工前 grep，第 4 項要求）

| 來源 | 程式位置 | 改版後 |
|---|---|---|
| 基本動作「絆倒」 | `battle._do_trip` | 敏捷對抗＋擊倒加值 |
| 技能原語 `knock_prone`（含反應招、修正規則命中後效果） | `primitives/displacement.knock_prone` → `Cast.knock_down` | 縮放屬性對抗＋擊倒加值 |
| 衝鋒命中時擊倒（`charge_through` 的 `on_hit`） | `primitives/displacement`（第二處 `cast.knock_down`） | 同上 |
| 擲物擊倒（`hurl_object.knock_prone`） | `primitives/displacement`（`knock_prone(cast, …)`） | 同上 |
| 「每第 3 次命中：倒地」詞條（`affix_trig_every3_prone`） | 詞條效果走 `knock_prone` 原語 → `Cast.knock_down` | 同上 |
| 召喚物灌注「倒地」 | `weapon_traits._try_trip` | 敏捷對抗＋擊倒加值 |
| 震波 | `primitives/displacement.shockwave` | **新**：命中後 `Cast.knock_down(kind="shockwave")`；友方對象也擲（PM 確認） |
| 推倒物件壓到 | `triggers._topple_damage` | **新**：照舊受傷；每人 `_crushed_prone`（推倒者力量對抗） |
| 土牆倒下壓到 | `triggers._wall_topple_damage` | **新**：同上 |
| 藤蔓纏住 | `summons/core`（snare 觸發） | **新**：`_snare_knocks`（召喚者那一招的縮放屬性） |
| 冰面滑倒（走進、被推拉進、衝鋒與跳躍落點） | `ice_slide.slide_check`、`effects/surface_entry` | DC 讀 `surfaces.yaml`（12 → 10） |
| 孤注一擲失手自己倒地 | 賭注代價（`apply_status` self） | 照舊不擲；站穩期間也擋（5.13 第 3 點「任何來源」） |

所有倒地最後都經過 `effects/handlers.apply_status`，站穩、巨型免疫、穩若磐石在 `_status_blocked` 一處擋。

## 3. 各項做法

### 3.1 倒地的效果（第 1 項）

- 不能反應：`reactions._react` 開頭擋（格擋、藉機攻擊、監視射擊、反擊、反應技、同門相護、裝備轉移全部經過它），重擲在 `rerolls._reroll_skill` 另擋。不詢問、不發事件。視圖 `reaction_available` 為假，另有 `UnitView.reaction_blocked_zh`。「守護」動作的轉移不是反應，沒擋（見待決）。
- 少 AP：倒地**新施加**（不是刷新）而且沒有 `boss` 標籤時設 `UnitState.prone_ap_due`；回合開始的 `ap_penalty` 加上 `prone_ap_loss`，補完 AP 後清掉。被扶起、自己站起都不影響這個旗標，所以照扣。AP 列的紅斜線（`ap_lost`、`ap_next_loss`）跟著算。
- 巨型頭目照舊在 `_status_blocked` 免疫；精英照一般單位。
- `LOG_FORMAT` `/137`（`docs/phases/戰鬥紀錄格式變更.md` 加一條，涵蓋整段）。

### 3.2 扶起（第 2 項、#177）

- 動作 `HelpUp`（`type: help_up`），**算基本動作**：放進 `BASIC_ACTION_TYPES`，基本動作上限 `BASIC_ACTION_LIMIT = 11`（05 5.2.2，#177）。上限只有測試讀（引擎不依它結算），所以不搬進 content，`classes.yaml` 歸 `const` 並寫明理由；前端 `BASIC_ACTION_LIMIT` 同步 11。
- 條件（`basics.help_up_problem`）：AP ≥ `help_up_ap_cost`；自己沒倒地、沒被定身、沒有跳過回合的狀態；對象是相鄰、同陣營（含召喚物）、高度差 ≤ `melee_height_limit`、倒地中。
- 結算：移除倒地（原因 `helped_up`）、發 `unit_stood_up`（`helper_id`、`cost: 0`），再給站穩。不移動、不花對象的移動點數，所以沒有藉機攻擊。
- AI：不另寫規則。扶起照「淨化」的算法計分（`support` × 倒地在 `status_values` 的價值）。
- 前端：「更多動作」選單第 6 項（換位後面），名詞表有說明卡。

### 3.3 站穩（第 3 項）

- 新狀態 `steady`（`mechanic_only`，中性、有益、`turn_end` 倒數）。`basics.stand_steady`：持續 `steady_rounds` 個自己回合；在自己回合中站起時這個回合不算（持續 `steady_rounds + 1`）。
- `_status_blocked` 對站穩回 `steady`（`effect_fizzled`），所有倒地來源都擋；冰面照樣滑（滑行在施加倒地之前），只是滑完不倒。
- 前端圖示用退回畫法（名稱第一個字「站」），列在 `qIcon/status.ts` 的 `AWAITING_ART_STATUSES`；狀態圖示的計數測試都排除它，美術補圖後從清單拿掉即可。`wl1bFallbackList.json`（美術待畫清單）多了 `steady`。

### 3.4 擊倒對抗（第 4 項）

- `maneuvers.contest(..., knockdown=True)`：守方 +`prone_contest_bonus`（記在 `maneuver_rolled.resist_bonus`），門檻 `hit_target + 1`（平手算守方贏）。自然 1、自然 20 照舊（PM 確認）。
- 預覽 `_maneuver_chance`（絆倒）、`_knock_chance`（技能擊倒、衝鋒、震波）用同一個 `knock_terms`。

### 3.5 原本不擲的來源（第 5 項）

- 震波：命中後 `Cast.knock_down(kind="shockwave")`，用技能的縮放屬性；友方對象（`affects: all`／`allies`）也擲（PM 確認）。
- 推倒物件、土牆壓到：照舊受傷；每人在觸發當下擲一次（推倒者的力量）。找不到推倒者時不倒地（見待決）。
- 藤蔓：召喚時記 `UnitState.summon_skill_id`，纏住時用召喚者那一招的縮放屬性；沒記到（測試直接放的藤蔓）用藤蔓自己的意志。
- 孤注一擲自己倒地照舊不擲。

### 3.6 冰面（第 6 項）

- `surfaces.yaml` 冰的 `check.dc` 12 → 10。走進、被推拉進、衝鋒與跳躍落點都讀同一個值（原本就是），不必改程式。

### 3.7 工坊、AI、預覽、文字（第 7 項）

- 工坊（`tuning_fields.yaml`）：核心戰鬥規則表多「倒地」一組——倒地少的 AP、站起消耗的移動（‰）、扶起的 AP、站穩的輪數、擊倒對抗的守方加值、壓到的傷害骰；新對象種類 `surface`（`surfaces.yaml`，清單名「地面表面（全體共用）」）開冰面滑倒 DC。每欄有中文名與調高、調低的影響。前端數值工坊多抓 `surface`。
- AI：`status_values` 加 `prone: 3`（初值，和燃燒、透支同一級；未經模擬）。第一次全量時用 6，AI 在好幾個情境改成絆倒而不普攻（嘲諷、第三方、召喚物集火的測試都翻），降成 3。技能擊倒的收益改用這個值（以前是各行為模式的 `status` 權重，莽夫等是 0），目標已倒地或站穩時不加分。
- 反應欄：主角倒地時技能列的反應區第一行寫「倒地中，不能反應」，反應技圓鈕標灰；狀態列的反應圖示說明也換成這句。
- 文字：倒地的狀態說明與規則句（扶起、不能反應、少 AP、站穩）、絆倒的名詞表（對方 +3、門檻、平手算對方贏）、技能卡（擊倒、衝鋒、擲物、震波、推倒）、召喚物說明（絆倒、藤蔓）。

### 3.8 小修（第 8 項）

- E1-1：技能列裝備技能的副標題只寫裝備名，CSS 截掉尾巴、不加「…」（`gearSkillItem`）。完整的「來自裝備・欄位：物品名」留在說明卡上方與 aria-label。
- E1-2、E5-2：說明卡上方的金框、虛線框、卡片接成一張：不留縫、上下重疊一條線、只有最上面那條有圓角、條不另外投影。
- E5-1：那幾條的底色改成卡片同色 `#14141c`、不透明，底色畫到框線下。
- E5 補 1：裝備變形只擋下一部分招式時，被擋的那招說明卡內文最後加灰字「彈射不會套用到這招」（`UnitView.skill_notes_zh`；整個擋下時修正技本身已標灰，不另外寫）。
- E5 補 2（8.29 E5 第 7 點）：一招已有一個裝備變形生效時，其他會套到這招的裝備變形加灰字「已有其他變形，〇〇的△△不會套用」。判定照 `reshape_gate.gated_rules`（依技能鍵排序第一個通過閘門的生效）。
- E2-1：完全重複（和種族、和另一件裝備）的加註改成灰色；部分重疊維持金色。
- E2-2：加註換行懸掛縮排（`padding-left: 1em; text-indent: -1em`）。
- E2 附註：部位字「腳」實測 `font-size` 10 px（1600 寬與 800 寬都是，行高 13.5 px），沒有低於 10 px，沒有改（見待決）。
- 「擊中時」→「命中時」：反應觸發「被近戰命中時」「被法術命中時」（含反咒觸發格的 Q 版部件名）、閃現兩條標題，共 6 處（加名詞表快照與一條前端測試）。

## 4. 檢查（全部 commit、合併 main 之後）

| 檢查 | 結果 |
|---|---|
| `uv run python scripts/check.py`（第 1 次） | 結束碼 1：pytest 21 個失敗（AI 倒地估值 6 讓 AI 改絆倒 9 個；固定種子 11 個；內容數量快照 1 個）。修正後 `d604c05d9` |
| `uv run python scripts/check.py`（第 2 次） | 結束碼 0：18399 passed、8 skipped；vitest 4900 passed；ruff、format、mypy、lint-imports、situation coverage 都通過；寫入通過戳記 |
| `uv run pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli`（第 1 次） | 結束碼 1：parity 全過；CLI 快照 17 鍵、`test_run_cli` 閃現一輪 1 個種子 |
| 同上（修正後，`d683d317e`） | 結束碼 0：995 passed（`d683d317e` 只改 slow 的 CLI 測試與快照，`check.py` 沒重跑） |
| 前端 build（`corepack pnpm -C client build`） | 結束碼 0 |
| 靜態檢查 `ruff`、`format`、`mypy`、`lint-imports`、`classify.py --check`、`trpg content check`、`tsc`、`vitest` | 全部結束碼 0（`classify.py` 沒歸類 0；content check 442 招通過） |
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill` 違規） | `same=442 different=0` |
| 78 場（`compare78.py`，同 a 段那組） | 見第 5 節 |

### CLI 快照與 parity

- parity（`test_refactor_parity.py`）沒有變。
- `skills_list`、`skills_show_all` 16 片：只因技能卡的擊倒字多了「，對方 +3」（擊倒、衝鋒、擲物、震波、推倒）。拿基準 `3581730ab` 逐行比對：`skills list` 27 行、442 招的 `skills show` 28 行不同，全部是這個字。
- `battle_frozen_lake_push_3`：冰面檢定的門檻 12 → 10（第一個差異就是 `需 ≥ 10`）。
- `battle_default_flat_42`：戰士改放「碎骨重擊」（擊倒技）而不是「放血斬」——AI 的擊倒估值改用 `status_values.prone`。
- 其他 5 場戰鬥快照沒有變。
- `test_run_cli.py` 大閃現一輪：種子 20 不再重閃完整技能，換 21（重掃 11～30 有 9 個符合）。

### 換種子的測試（斷言都沒放寬）

| 測試 | 改前 → 改後 |
|---|---|
| `tests/engine/test_gamble.py` 賭徒失手反噬 | open_plain 0、6 → narrow_halls 1、ruined_fort 4（open_plain 0～199 都沒有失手反噬：孤注一擲很少放、放了都命中） |
| `tests/cli/test_basic_actions_cli.py` 換位＋瞄準 | 237 → 120 |
| `tests/engine/test_status_determinism.py` 新狀態 | 4、9 → 7、12 |
| `tests/engine/test_self_moves.py` 衝鋒流三種位移 | open_plain 5 → 4 |
| `tests/roguelite/test_attribute_respec.py`、`tests/api/test_attribute_text_api.py` 營火 | 3 → 4 |
| `tests/content/test_bandit_lair.py` 援軍 | 6 → 5 |
| `tests/api/test_full_battle.py` 反應詢問交替 | 多加一場 ruined_fort 7 |
| `tests/cli/test_run_cli.py` 大閃現一輪 | 20 → 21 |

## 5. 78 場比對

`compare78.py`（同 a 段那組；去掉 `ruleset_hash`、內嵌規則包）。因為 `format` `/136` → `/137`，78 場全部不同；另外去掉 `format` 再比（`c78_analyze.py`）：**73 場不同、5 場相同**（`boss_bandit_lair_4`、`boss_bandit_lair_8`、`lava_crossing_1`、`lava_crossing_7`、`oil_depot_1`）。內嵌規則包的差異只有新欄位（`prone_ap_loss`、`help_up_ap_cost`、`steady_rounds`、`prone_contest_bonus`）、新狀態 `steady`（狀態表的索引往後移一格）、冰的 DC、AI 表的 `prone`。

勝負：我方勝 49 → 47、敵方勝 29 → 31。動作：絆倒 2 → 49、扶起 0 → 5、碎骨重擊 83 → 92、放血斬 145 → 138。28 次擊倒對抗是因為 +3 或平手才失敗。

抽 3 場：
1. **`open_plain_3_tank`**（第 47 個事件起分岔）：標準隊友（戰士）原本普攻盜賊命中；改後 AI 選絆倒（倒地估值變高），擲 9＋修正 −1＋熟練 2 = 10，扣掉對方 +3 是 7，門檻 9 → **對抗失敗**。之後的戰鬥從 238 個事件變成 200 個。
2. **`frozen_lake_1`**（第 15 個事件）：盜賊走進冰面，檢定 13 對 **DC 10**（原本 12），兩邊都成功，但之後別的冰面檢定結果翻轉，戰鬥路徑分岔（209 → 218 個事件，勝方不變）。
3. **`boss_bandit_lair_5`**（第 26 個事件）：英雄第一手從「放血斬」改成「碎骨重擊」（擊倒技的估值改用倒地的價值）；之後被擊倒的頭目護衛**少 1 AP、不能反應**，整場從我方敗變成**我方勝**（282 → 330 個事件）。同類的「放血斬改碎骨重擊」也出現在 `bandit_lair_1`、`swamp_7`。

## 6. 截圖（`docs/art/shots/kd-1/`，交美術 PM）

實機（`trpg serve`＋暫存的內容複本：開場倒地／站穩、只給截圖用的彈射詞條（對所有技能）、E2 的三條地形規則詞條、坦克改矮人）；jpg 品質 80，美術清單指定的 800 寬用真 1 倍 PNG；單張都在 300 KB 以下。

| 檔 | 內容 |
|---|---|
| `kd1_prone_reaction_1600x900.jpg`、`kd1_prone_reaction_800x600.jpg` | 主角倒地：反應欄「倒地中，不能反應」、反應技圓鈕標灰、AP 列少一格（紅斜線）、倒地的狀態說明 |
| `kd1_help_up_1600x900.jpg`、`kd1_help_up_800x600.jpg` | 隊友倒地：「更多動作」選單的「扶起」與它的說明卡 |
| `kd1_steady_1600x900.jpg` | 主角起身後的「站穩」圖示（退回畫法「站」）與說明 |
| `e5_bounce_card_1600x900.jpg` | 彈射的說明卡：金框、虛線框、卡片接成一張（E1 小修 2、E5 小修 1、2 的補拍；同時是 E1「說明卡 1600 寬」那張） |
| `e5_blocked_skill_1600x900.jpg` | 被彈射擋下的「颶風踢」滑過時的說明卡，最後一行灰字 |
| `e5_blocked_skill_e1_skillbar_800x600.png` | 同上 800 寬真 1 倍；技能列兩格「鉤爪」副標題只寫裝備名「鉤索圓盾」「鉤爪護手」（E1 小修 1 的補拍） |
| `e2_gear_card_1600x900.jpg`、`e2_gear_card_800x600.png` | 同一張裝備卡：完全重複的兩條加註灰色、部分重疊金色、換行懸掛縮排 |

共 10 張（6.5.2 上限）。站穩只拍 1600（張數上限；圖示要等美術出圖）。

## 7. 待 PM 決定

1. **扶起算基本動作、上限 11**（#177）：已照改。上限常數 `BASIC_ACTION_LIMIT` 只有測試讀，歸 `const` 沒搬 content；要搬再說。
2. **震波的友方對象也擲對抗**、**擊倒對抗的自然 1／20 照舊、平手＝總和等於門檻時守方贏**：照 PM 指示做了。
3. **AI 倒地估值 `prone: 3`**（原規格「照新懲罰重新給初值」，6 太高會讓 AI 一直絆倒）。另外擊倒技的估值改用這個值後，碎骨重擊用得比放血斬多一點。要不要開進工坊、值多少，請使用者自己調（數值疑慮，沒寫進 `平衡待查.md`：這段不改 `docs/design/`）。
4. **推倒壓到找不到推倒者（`source_id` 是空的）時不倒地**（保守：倒地變難的方向）。目前內容沒有沒有來源的推倒。
5. **「守護」動作的轉移不是反應，倒地的守護者照樣能替隊友承受**（5.13 只列反應）。
6. **站穩的持續**：自己回合中站起時，這個回合不算（持續到下一個自己回合結束）；被別人扶起時就是下一個自己回合結束。工坊值 0＝不給站穩。
7. **扶起的條件「不能行動」**：照跳過回合的狀態（暈眩等）判斷；冰凍、沉默不算。
8. **E5 灰字的用字**（「彈射不會套用到這招」「已有其他變形，〇〇的△△不會套用」）等玩法 PM 定。整個擋下時（修正技本身已標灰）被擋的招不另外寫。
9. **一招只套一種變形的「第一個」**：照 `gated_rules`（依技能鍵排序第一個通過閘門的）。
10. **E2 部位字**：實測 `font-size` 10 px（1600、800 寬都一樣），沒有低於 10 px，沒改；字形本身看起來 7～8 px 是 10 px 中文字的正常墨跡。要放大請美術 PM 定。
11. **站穩圖示**：先用退回畫法（`AWAITING_ART_STATUSES`），交美術 PM 出圖。
12. 「擊中時」實際找到 6 處（規格寫約 7 處）。

## 8. 數值疑慮（不跑模擬、不量平衡）

- 倒地變重又變難：絆倒、技能擊倒的成功率約少 15～20 個百分點，但擊倒一旦成功，對方少 1 AP、不能反應。擊倒技的預算點數（`knock_prone` 3、`prone` 狀態點數）沒有動，預算 442 招逐位相同；擊倒技相對變弱還是變強要靠使用者在工坊看。
- 冰面 DC 10：敏捷 +0 的滑倒率從 55% 降到 45%。

## 開發 PM 裁定（2026-11-22）

合併為 81f9cbb49 推上 main，push hook 的完整檢查通過。截圖交美術 PM 驗收。這段本來就會改戰鬥結果：78 場裡有 73 場不同；442 招逐位相同。

1、2：接受，已照 #177 與 PM 指示做。
3. AI 倒地估值 3：接受，當初值。AI 權重表要能在工坊調。如果 `prone` 這格還沒開進工坊，排進佇列，下一段碰到 AI 時開。
4～7、9：接受，都照保守做。第 6、7 點轉給玩法 PM，補進 5.13。
8. 灰字的用字，玩法 PM 已定 A，就是現在的字。
10. 部位字實測是 10 px，不改。
11. 站穩圖示：交美術 PM 出圖。
12. 接受。
第 8 節的兩條數值疑慮，轉給玩法 PM 記進平衡待查。
