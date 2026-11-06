# Phase 3C-6a 報告：收尾（累積的小修正、顯示、被近戰攻擊後轉身）

## 1. commit

| commit | 內容 |
|---|---|
| 5867df6 | 被近戰攻擊後轉身（8.2B）：`reactions.py`、`interpreter.py`、`tests/engine/test_turn_on_melee_hit.py`（8 個）、`scripts/backstab_counts.py` |
| b5b768c | 8.2A 小修正與其餘後端：紀錄文字、穿透、奪取順序、環境預告、AI、示範技能「聚雷」、技能卡片時機、複製暫停預覽（API）、`sim maps` 召喚次數、`LOG_FORMAT` `/33`、OpenAPI／`schema.d.ts`、CLI 快照重錄、`tests/engine/test_polish_3c6a.py`（14 個） |
| a5843ae | 網頁：源泉格、源力圖示、技能卡片種類與稀有度顏色、複製暫停（方向鈕、Esc、懸停預覽）、環境預告不重複、殘影分身剩餘輪數、被揭露陷阱標記、`polish3c6a.test.ts`（11 個） |
| （本報告） | 報告 |

開發期間沒有 stash、reset、amend、切換分支，也沒有 push。

## 2. 8.2B 被近戰攻擊後轉身

- **規則**：近戰攻擊（普攻、近戰武器技、藉機攻擊與反應普攻；`weapon.is_melee`，與背刺同一個判斷）擲過命中判定之後，不論命中與否，目標在 **該次攻擊或施放結算完** 才轉向攻擊者擲骰當時的位置（`after_attack(..., turns=...)`）。遠程、法術不轉；推、拉、傳送、交換不轉；攻擊物件不轉；已倒下的目標不轉；守護者替隊友擋下時，轉身的是被瞄準的原目標（見待決 #3）。
- **擲骰當下的朝向**：背刺判定與 `from_behind` 效果條件都在轉身之前，所以「瞬步背刺」的第二段傷害（條件 `from_behind`）照舊成立，施放完目標才轉向（測試 `test_a_backstab_cast_keeps_its_bonus_damage_then_the_target_turns`）。多段攻擊（連續兩次普攻）第二下目標已轉身：`test_the_second_melee_attack_is_no_longer_a_backstab`。
- **團隊連招**：`test_the_tank_turns_the_enemy_and_the_teammate_backstabs`（敵人面向北，坦克從西邊砍，敵人轉向西，東邊的盜賊站在背後，背刺 +2；沒有先砍時同一格只是側面）。
- **預覽與 AI**：預覽讀的是出手當下的朝向，不需要改；AI 的 `backstab`（站到相鄰敵人的背後格）本來就讀敵人的實際朝向，`back_exposed`（以「面向最近的敵人」近似自己的朝向）沒有改。AI 權重沒有調整（建議見待決 #1）。
- **重播**：`test_ai_battle_with_backstabs_replays`（`dark_forest` 種子 3、`build_assassin`）與整批 `test_cli_output_matches_the_recorded_snapshot` 通過；`LOG_FORMAT` 升為 `/33`（AI 選擇與事件順序改變，舊紀錄不能重播）。

### 驗收測試（`tests/engine/test_turn_on_melee_hit.py`）

| 項目 | 測試 |
|---|---|
| 命中也轉身 | `test_a_melee_hit_turns_the_target_toward_the_attacker` |
| 未命中也轉身 | `test_a_melee_miss_also_turns_the_target`、`test_a_melee_skill_turns_the_target_hit_or_miss` |
| 遠程不轉 | `test_ranged_attacks_do_not_turn_the_target` |
| 強制位移不轉 | `test_forced_displacement_does_not_turn_the_target` |
| 第二下不再背刺 | `test_the_second_melee_attack_is_no_longer_a_backstab` |
| 團隊連招、同一次施放內仍背刺 | 上列兩個測試 |
| 重播一致 | `test_ai_battle_with_backstabs_replays`（既有）、CLI 快照 |

### 背刺次數改前／改後

10 張地圖 × 5 種子 ＝ 50 場；`uv run python scripts/backstab_counts.py --seeds 5`。「改前」是在 `git archive HEAD` 匯出的 3b61a1b 舊程式上跑同一支腳本。

| 陣容 | 我方背刺 前→後 | 敵方背刺 前→後 | 我方偷襲 前→後 |
|---|---|---|---|
| 預設陣容 | 53 → 27 | 77 → 27 | 12 → 12 |
| `build_assassin`（`--ally-build`） | 150 → 89 | 122 → 58 | 21 → 20 |

各地圖（背刺，前→後）：

| 地圖 | 預設 我方 | 預設 敵方 | 刺客 我方 | 刺客 敵方 |
|---|---|---|---|---|
| bridge_chasm | 2→1 | 4→1 | 4→3 | 5→2 |
| cliff_outpost | 3→3 | 12→4 | 14→10 | 6→2 |
| dark_forest | 7→3 | 11→3 | 16→11 | 22→2 |
| frozen_lake | 3→2 | 8→3 | 8→6 | 13→4 |
| lava_crossing | 5→3 | 0→0 | 17→8 | 2→4 |
| narrow_halls | 3→2 | 2→1 | 26→14 | 7→6 |
| oil_depot | 3→2 | 12→7 | 15→9 | 30→16 |
| open_plain | 4→2 | 2→0 | 15→9 | 5→11 |
| ruined_fort | 7→3 | 3→2 | 11→9 | 6→1 |
| swamp | 16→6 | 23→6 | 24→10 | 26→10 |

背刺次數大約減半，敵方（過去背刺很常見）降幅更大；刺客仍有每場約 1.8 次我方背刺。權重不調整，建議見待決 #1。

## 3. 8.2 顯示：盤點結果

| 項目 | 盤點 | 本段處理 |
|---|---|---|
| HUD 源力 | 原本只有文字「源力 2/3」 | 改為三格菱形圖示（亮的是目前的源力，滑過有說明） |
| 源泉格在地圖上 | **CLI 已有（`$`）；網頁沒有** | 網頁畫紫色菱形加「源」字（`WellDraw`、`BattleRenderer.drawWells`） |
| 技能卡片的「改造／修正」類別與描述 | 描述（`修正：…`）已有；種類字樣沒有 | 標題加種類「主動／被動／反應／修正（改造／修正）」 |
| 傳說的源力成本 | 代價文字已含「源力 N」 | 另列一行「傳說代價：源力 2 ●●○」 |
| 稀有度顏色 | 沒有 | 稀有藍、史詩紫、傳說金色邊框與標題（`.rarity-*`） |
| 戰鬥紀錄文字（源力、免死、轉移傷害、複製、觸發） | **已全部有**（`SourceChanged`、`DeathCheated`、`DamageRedirected`、`SkillCopied`、`SkillTriggered` 等 handler 都在 `trpg/narrative/events.py`） | 不用改 |

## 4. 8.2A 逐條處理結果

| # | 項目 | 處理 |
|---|---|---|
| 1 | 3C 0.10：複製暫停時面板方向鈕無反應 | **修正**：暫停時面板只留被複製技能的方向鈕且可按（`onAction` 改送 `decideCopy`），提示改為「請為複製的技能選擇目標…」 |
| 2 | 3C 0.10：複製暫停的懸停預覽、Esc 放棄 | **修正**：Esc ＝ 放棄施放；`/preview` 在複製暫停時收被複製技能的選取，預覽「暫停前狀態＋該選取」整個施放（`BattleSession._preview_copy`；測試 `test_the_preview_during_the_pause_matches_the_real_cast`、`test_a_non_skill_preview_during_the_pause_is_rejected`） |
| 3 | 3C 0.12：穿透失手不顯示「後方只受 70%」 | **修正**：`shot_pierced.behind` 只列命中的後方單位（`test_a_missed_pierced_shot_does_not_claim_the_back_discount`；物件受傷與否照舊） |
| 4 | 3C 0.12：CLI 穿透折扣與格擋分開顯示 | **修正**：`damage_dealt.pierce_permille`，紀錄顯示「（格擋/加成 ×1.4）（穿透後方 ×0.7）」，不再是「×0.98」（`test_a_hit_pierced_shot_still_reports_the_back_discount_separately_from_block`、`test_a_pierce_discount_alone_is_not_shown_as_a_block`）；`LOG_FORMAT` 升 `/33` |
| 5 | 3C 0.8 #7：貼牆推擊以「撞上牆壁」為主 | **修正**：推擊被擋下的 `move_blocked` 標 `forced`，紀錄不再顯示「無法移動到…」，只留「撞上了…」（`test_a_shove_into_a_pillar_logs_the_collision_not_a_blocked_move`）；步行被擋的 `move_blocked` 照舊 |
| 6 | 3D 0.4 #8：奪取增益的顯示順序 | **修正**：先「被奪走」再「獲得」（`steal_buff` 先 `execute` 移除再回傳施加；`test_steal_buff_logs_the_loss_before_the_gain`） |
| 7 | 3D 0.8 #10：技能卡片補反應時機一行 | **修正**：`SkillCard.timing`——反應技「反應時機：被法術命中時（傷害結算之前）」、被動「觸發時機：命中時」；網頁卡片顯示（`test_reaction_and_passive_cards_show_their_timing`，並檢查 8 個反應事件都有文字） |
| 8 | 3D 0.10 #10：`sim maps` 加召喚次數 | **修正**：報表多一行「召喚物（整批合計）：我方召喚 N 次」，JSON 有 `summon_events`（`test_sim_maps_reports_the_summon_count`） |
| 9 | 3D 0.12 #7：殘影分身剩餘輪數多算 1 輪 | **修正（網頁）**：召喚者已倒下的分身，本輪先攻位置已過時不把本輪算進去（`remainingRounds`；vitest 3 個）。CLI 只印到期輪，沒有「剩 N 輪」，不受影響 |
| 10 | 3D 0.13 #10：單體武器技 `legal_actions` 多一筆 `target_id: null` | **證明無害並記錄，不改引擎**：目前版本找不到這筆動作。逐一檢查 `legal_actions`（所有主動技能 × 3 種武器的決鬥場景共 48 組、另有 5 個 build × 2 種子的 AI 戰鬥中每一步的合法動作），單位選取型形狀都不會列出沒有目標的動作；就算送出，`checked_area` 也拒絕（`IllegalActionError`）。測試 `test_unit_targeted_skills_never_list_a_selection_less_action`、`test_a_selection_less_cast_of_a_single_skill_is_rejected` 鎖住此行為。3D-7a 看到的動作可能是自身／環形等無選取形狀（它們本來就是無目標動作，例如嘲諷怒吼、狂戰士之怒） |
| 11 | 3D 0.14 #6：AI 低血量規則也套用到會超載的技能 | **修正**：`ai/gamble.py` 新增 `overloads()`——這次施放會把超載層數推到門檻（且反噬含傷害）時，`cautious` 同樣把正分乘 `low_hp_permille`（`test_a_low_hp_caster_avoids_the_cast_that_would_overload_it`、`test_overloads_is_true_only_when_the_cast_reaches_the_threshold`） |
| 12 | 3D 0.14 #10：補 `enemies_adjacent_target` 示範技能 | **完成**：「聚雷」`skill_cluster_bolt`（common、法術、單體射程 4、3d6 雷電、目標每有 1 名（對施放者而言的）敵人相鄰 +15%、上限 +45%；預算 81.7%），裝進 `build_striker`（主動欄位 4→5；`test_the_cluster_bolt_scales_with_the_enemies_around_the_target`） |
| 13 | 3D 0.17：「飛行」附帶的 2 回合隱蔽是否保留 | **保留，不改**：拿掉隱蔽後 `trpg skills budget skill_flight` 為 56.3%（下限 70%），過弱。AP 已是 1（最小）、射程對 `teleport` 不計價，無法用 AP／射程補到預算。若要拿掉需 PM 決定改 `teleport` 的點數或下限（待決 #4） |
| 14 | 3D 0.16：環境預告中同一顆炸彈那一行重複 | **修正**：下一次環境回合就爆炸的炸彈，變化裡已有「將在…爆炸」一行，不再另列炸彈那行（CLI `render_telegraph`、網頁側欄與格子說明；`test_the_telegraph_lists_a_bomb_once`、vitest `telegraph bombs`）。還有 2 次以上倒數的炸彈仍列倒數那行 |
| 15 | 3D 0.15 #4：被揭露的敵方陷阱網頁與 CLI 用不同標記 | **修正**：CLI 用 `x`（圖例「x 被揭露的敵方陷阱」），我方陷阱仍是 `^`；網頁用紅色「×」，我方陷阱仍是黃色「^」（`test_a_revealed_enemy_trap_uses_its_own_glyph_in_the_grid_and_legend`、vitest `marks an enemy trap that was revealed differently`） |
| 16 | 組合器能產生新原語、條件、賭博型 | **屬 3C-6b，不做** |

## 5. 驗收條件逐條（8.5 第 0 條）

- 8.2A 每項都有處理結果：見第 4 節（16 項：修正或完成 13 項、證明無害或說明不改 2 項〔#10、#13〕、屬 3C-6b 1 項〔#16〕）。
- 8.2B：見第 2 節。
- 網頁顯示：由 PM 用瀏覽器驗收，重現步驟見第 7 節。
- `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（**2860**）、client typecheck、vitest（**163**）全部通過。

## 6. 修改既有測試

| 測試 | 原因 |
|---|---|
| `test_attacking_and_casting_on_a_unit_face_the_target` | 規則改變：被攻擊的一方現在會轉向攻擊者（期望值 `west` → `north`） |
| `test_a_unit_with_riposte_hits_back_in_an_ai_battle`（`test_guardian_battle.py`） | AI 戰局因轉身改變，種子 2 不再出現還擊；改用種子 0 |
| `test_the_new_builds_have_the_specified_skills`（striker 技能數 5 → 6） | 新增「聚雷」 |
| `test_budget_cli.py` 兩處 134 → 135 | 技能數 +1 |
| `test_battle_cli.py`、`test_skills_cli.py` | `LOG_FORMAT` `/32` → `/33` |
| `tests/cli/snapshots/cli_output_hashes.json` | 9 場戰鬥雜湊重錄：被近戰攻擊後轉身使 AI 走位、背刺與後續戰局改變，加上 `build_striker` 多一個技能 |
| `test_striker_battle_accumulates_and_consumes_static_charge_and_replays` | 開發中曾因轉身改成種子 6，加入「聚雷」後種子 1 又成立，最後仍是原本的種子 1（沒有淨改變） |

## 7. 網頁驗收重現步驟（PM 用瀏覽器）

`uv run python scripts/play.py`（`client/dist` 已 `corepack pnpm -C client build`；我只跑了 vitest 與型別檢查，沒有用瀏覽器實機操作）。

1. **源力圖示、技能卡片**：選 `build_charger`（衝鋒流）、`open_plain`、種子 0。HUD 的「源力」是三格菱形（亮 1 格）。滑過「戰神降臨」：標題金色、卡片金色邊框，標題行有「傳說・修正…」字樣，另有「傳說代價：源力 1 ●○○」一行。滑過任何反應技（例如 `build_banisher` 的「反咒」）：多一行「反應時機：被法術命中時（傷害結算之前）」。
2. **源泉格**：選有源泉格的地圖（`grep source_wells content/maps/*.yaml` 可找；CLI 圖上的 `$`），地圖上該格有紫色菱形「源」；我方單位走上去後消失、源力 +1。
3. **複製暫停**：`oil_depot`、種子 4、`build_support`，打到主角回合，施放「鏡像施法」，出現「複製技能：選擇目標」。(a) 右側面板的方向鈕可以按（直接送出）；(b) 滑過高亮格子，右側顯示整個施放的預覽（命中率、傷害）；(c) 按 Esc 放棄施放，AP 與源力不變。
4. **被近戰攻擊後轉身**：`narrow_halls`、種子 1、`build_assassin`：觀察單位圖示的朝向小箭頭——被近戰命中或打空後，被攻擊者的箭頭轉向攻擊者；紀錄第二下近戰不再有「背刺 +2」。
5. **環境預告炸彈**：`open_plain`、種子 2、`build_bomber` 對敵人貼定時炸彈，預告側欄中，倒數剩 1 次時只出現「…將在 (x, y) 爆炸」一行，不再多一行「身上的定時炸彈下一次環境回合就會爆炸」。
6. **被揭露的敵方陷阱**：用 `build_seer` 的「揭露」照到敵方陷阱：格子上是紅色「×」，我方陷阱仍是黃色「^」。
7. **殘影分身**：`build_trapper` 啟動「殘影之誓」後倒下，HUD 的分身剩餘輪數不把已過的本輪算進去。

## 8. 新增的複雜度 noqa

無（C901、PLR0911／0912／0915 都沒有新增）。測試與腳本中新增的 `noqa` 只有 `PLC0415`（函式內匯入，4 處）與腳本的 `SIM115`（1 處：暫存檔開啟後在 `finally` 關閉）。

## 9. `LOG_FORMAT`

`/32` → `/33`（理由見 `runner.py` 的說明：轉身改變 AI 選擇與事件順序、`damage_dealt.pierce_permille`、`move_blocked.forced`、`shot_pierced.behind` 只列命中者、`steal_buff` 事件順序）。OpenAPI 只多了 `SkillCard.timing`。

## 10. 待 PM 決定

1. **背刺權重**：轉身後背刺次數約減半（預設陣容 53/77 → 27/27，刺客 150/122 → 89/58），敵我已接近對等；刺客仍每場約 1.8 次。是否維持現有 AI 權重（`backstab: 4`、`back_exposed: 3`）？建議維持，等 3C-6b 的 `sim matrix` 看刺客勝率再說。
2. **`back_exposed` 近似**：它仍假設單位「面向最近的敵人」，沒有考慮「被近戰打到會轉向」。建議不改，除非 matrix 顯示 AI 不會避免露背。
3. **守護者攔截**：替隊友擋下近戰攻擊時，轉身的是被瞄準的原目標，不是承受傷害的守護者。若希望守護者也轉向攻擊者，是一行改動。
4. **「飛行」的隱蔽**：拿掉會過弱（56.3%）。要拿掉需調整 `teleport` 的基礎點數或預算下限；建議保留現狀，視為技能設計的一部分（落地後短暫隱蔽）。
5. **聚雷放在 `build_striker`**：該 build 只有 4 個主動，是唯一有空位的法杖 build。3C-6b 整理 build 時可再搬。
6. **`legal_actions` 無目標動作**：目前找不到，已加測試鎖住。若 PM 在網頁／API 回應中實際看到 `target_id: null` 的單體技，請給重現（技能、地圖、種子）。
7. **複製暫停的預覽**：`/preview` 在暫停時改為收「被複製技能的選取」，語意與平常的 `/preview`（收主角動作）不同；若之後想有專屬路由可再拆。
8. **面板提示**：複製暫停時面板內「Esc／右鍵取消」的說明文字沿用一般模式（右鍵在暫停時只是清除選取，不會放棄；Esc 才是放棄）。

## 11. 代表性的 CLI 輸出節錄

`uv run trpg battle --map narrow_halls --seed 1 --ally-build build_assassin`（連續的一段：戰士推擊讓盜賊盾衛撞上盜賊，只有「撞上了」，沒有「無法移動」；接著刺客「瞬步背刺」第一刀吃到背刺 +2，同一回合第二下普攻就沒有背刺了）：

```
— 標準隊友（戰士） 的回合（AP 3，移動 5）
  標準隊友（戰士） 從 (5, 5) 移動到 (8, 4)（消耗 4 移動）
  標準隊友（戰士） 對 盜賊盾衛 使出推擊：d20=5 修正 +1 熟練 +2 = 8（目標 11）→ 失敗
  標準隊友（戰士） 對 盜賊盾衛 使出推擊：d20=5 修正 +1 熟練 +2 = 8（目標 11）→ 失敗
  標準隊友（戰士） 對 盜賊盾衛 使出推擊：d20=12 修正 +1 熟練 +2 = 15（目標 11）→ 成功
  盜賊盾衛 撞上了盜賊！少走 1 格，受到 1 次撞擊
    盜賊盾衛 受到 5 點撞擊物理傷害［骰 6］（元素修正 ×0.9），HP 32 → 27
    盜賊 受到 3 點撞擊物理傷害［骰 3］，HP 30 → 27
  標準隊友（戰士） 結束回合
— 刺殺英雄 的回合（AP 3，移動 5，法力 15/20）
  刺殺英雄 的「迎頭痛擊」冷卻結束
  刺殺英雄 的「防禦」結束了
  刺殺英雄 施放「瞬步背刺」（AP 2，法力 5，冷卻 3 回合）→ 影響 1 格
  刺殺英雄 瞬步到 (9, 2)
  刺殺英雄 從背後以「瞬步背刺」攻擊 盜賊：d20=5 修正 +0 熟練 +2 背刺 +2 = 9（目標 11）→ 失手
  刺殺英雄 攻擊 盜賊：d20=8 修正 +0 熟練 +2 = 10（目標 11）→ 失手
  刺殺英雄 結束回合
```
