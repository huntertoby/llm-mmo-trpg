# BAL-19f 報告：白板形狀與觸發（玩法決定 #110，缺口 5）＋追加

規格：`docs/phases/PhaseBAL計畫.md` 第 12 節 BAL-19f 與「BAL-19f 追加」；設計 `docs/design/06-技能.md` 6.34.1、6.34.9、6.27.4、6.10。另含開發 PM 轉來的玩法 PM 追加兩點（感知／意志白板姿態、撤步護體的改法）。

## 1. 新增白板配方（`content/skill_composer.yaml`）

| 類 | 配方 | 關鍵字 | 內容 | 階級 |
|---|---|---|---|---|
| 形狀 | flame_lance 炎流 | 點燃 | 直線火焰傷害 | 1～3（長 6 的直線 3 階） |
| 形狀 | thunder_lance 雷槍 | 帶電 | 直線雷電傷害 | 1～3 |
| 形狀 | frost_breath 寒息 | 冰凍 | 錐形冰霜傷害 | 1～3 |
| 形狀 | venom_mist 毒霧 | 中毒 | 錐形施加中毒 | 1（max_tier 1） |
| 形狀 | whirl_slash 迴旋斬 | 通用 | 環形物理傷害（武器技） | 1～3 |
| 形狀 | shadow_ring 暗影環 | 隱蔽 | 環形暗影傷害 | 1～3 |
| 形狀 | chain_lightning 連鎖閃電 | 帶電 | 連鎖雷電傷害 | 3（6.34.9 連鎖 3 階） |
| 號令 | command_strike 號令突擊 | 召喚物 | 近戰武器攻擊＋自己得「號令」 | 1～3，力量 |
| 號令 | command_shot 號令箭 | 召喚物 | 遠程武器攻擊＋自己得「號令」 | 1～3，敏捷 |
| 姿態 | dawn_stance 晨光架勢／dawn_stance_hi 聖曜架勢 | 通用 | 聖光架勢 1／3 級（感知） | 2／3 |
| 姿態 | dusk_stance 暮影架勢／dusk_stance_hi 夜影架勢 | 通用 | 暗影架勢 1／3 級（意志） | 2／3 |
| 被動 | kill_mend 戰後回氣 | 通用 | 擊倒時回血 | 1～3 |
| 被動 | pain_spark 逆電 | 帶電 | 受傷時電擊來源 | 1～3 |
| 被動 | crash_ward 撞勢護身 | 撞擊 | 造成撞擊後自己得護盾 | 1～3 |
| 被動 | crit_frost 寒芒／crit_ward 乘勝護身 | 冰凍／通用 | 暴擊時冰傷害／護盾 | 2～3 |
| 被動 | stride_ward 行進護盾／stride_mend 步步回春／stride_veil 潛行步 | 通用／通用／隱蔽 | 移動後護盾／回血／隱蔽 | 1～3／1～3／2～3 |
| 被動 | dusk_mend 歇息／dusk_mark 收勢標記 | 通用／標記 | 回合結束回血／標記 3 格內最近敵人 | 1～3 |
| 被動 | fuel_fire 火上加油／venom_feast 毒噬 | 點燃／中毒 | 施加燃燒／中毒後追加傷害 | 1～3 |
| 被動 | undertow 暗流／fire_sea 火海灼燒 | 潮濕／點燃 | 敵人進入你的水／火時受傷 | 1～3 |
| 反應 | spell_spark 逆流電光 | 帶電 | 被法術擊中時電擊施法者 | 1～3 |
| 反應 | frost_greet 迎面寒霜 | 冰凍 | 敵人靠近時冰傷害 | 1～3 |
| 反應 | parting_cut 送別一擊 | 通用 | 敵人離開時傷害 | 1～3 |
| 反應 | watch_mark 護衛標記／watch_spark 護衛電擊 | 標記／帶電 | 隊友被瞄準時標記／電擊攻擊者 | 1～2／1～3 |

- 白板定義：`simple_shapes` 加 `line, cone, ring, chain`；號令型「傷害＋對自己施加號令狀態」列為允許的兩個效果（`command_statuses: [commanding]`，與位移的小補強同一種例外，`whiteboard_check._rider_ok`）。
- 每個配方在它開放的階級、四種武器大類下都過驗證、白板定義、預算 70～100%、關鍵字對得上（`test_whiteboard_3w4b.py` 對全部配方檢查）。`min_tier`／`max_tier` 只用在「那一階做不出來」的配方（暴擊係數 250‰，1 階骰子最小仍超預算；點數固定的狀態 2 階起湊不到下限）。

## 2. 號令型白板（追加 1）

- 新狀態 `commanding`（號令，`content/statuses.yaml`）：持續到你的下回合開始（召喚物緊接在召喚者之後行動，剛好涵蓋一輪召喚物的行動），你的召喚物造成的攻擊傷害 ×1250‰（初值），預算 3 點，最低稀有（照狀態表規則）。
- 為此加一個狀態欄位 `summon_damage_dealt_permille`（`StatusDef`）與引擎一處乘算（`engine/effects/handlers._dealt_permille`：攻擊者是召喚物時再乘召喚者身上的號令；`engine/rules/statuses.summon_damage_dealt_permille`）。沒有現成原語能「讓你的召喚物這回合變強」，這是最小改動；選「傷害提高」而不是「額外行動」。
- 關鍵字：`skill_keywords.yaml` 召喚物的 uses 加 `{effect: apply_status, status: commanding}`（專屬）。
- 吃武器屬性：配方指定 `weapon_req`，近戰固定力量、遠程固定敏捷（`_attempt_active` 讀配方的 `weapon_req`）；本身不召喚。
- 創角選「召喚物」仍給召喚白板：配方新欄位 `starter: false`，號令型只出在三選一。
- 完整模式組合器不抽 `commanding`（`_status_candidates` 排除），既有種子輸出不變。

## 3. 觸發時機前後（白板配方數）

| 時機 | 前 | 後 |
|---|---|---|
| on_hit | 7 | 7 |
| on_turn_start | 2 | 2 |
| on_kill | 1 | 2 |
| on_damaged | 1 | 2 |
| on_collision | 1 | 2 |
| on_crit | 0 | 2 |
| on_move | 0 | 3 |
| on_turn_end | 0 | 2 |
| on_status_applied | 0 | 2 |
| on_enter_surface | 0 | 2 |
| hit_by_melee | 4 | 4 |
| hit_by_attack | 3 | 3 |
| hit_by_spell | 1 | 2 |
| enemy_enters_adjacent | 1 | 2 |
| enemy_leaves_adjacent | 1 | 2 |
| ally_targeted | 0 | 2 |
| **種類** | **10** | **16（每種 ≥ 2）** |

- 技能的反應事件沒有「敵人在射程內移動」（`SKILL_REACTION_EVENTS`），第 16 種用 `ally_targeted`。
- 暴擊的觸發係數 250‰，1 階最小的骰子也超預算，暴擊白板 2 階起（1 階沒有）；原本試的 1 階燃燒版（爆燃）升階重配時比例跳 14%、閃現也沒有選項，拿掉。潛行步 2 階起。「每種 ≥ 2」以配方總數算，不是每一階。

## 4. 形狀前後（`scripts/skill_balance_audit.py --sections 3`，白板可達）

抽樣：每個配方 × 武器大類 × 最高屬性 8 個種子，去重後的結果（前 158 → 後 214 種）。

| 形狀 | 前 | 後 |
|---|---|---|
| line 直線 | 0 | 6 (3%) |
| cone 錐形 | 0 | 6 (3%) |
| ring 環形 | 0 | 5 (2%) |
| chain 連鎖 | 0 | 3 (1%) |
| single 單體 | 68 (43%) | 88 (41%) |
| self 自身 | 43 (27%) | 59 (28%) |
| cross 十字 | 26 (16%) | 26 (12%) |
| ground_tile 地面格 | 21 (13%) | 21 (10%) |

同一份報表的觸發時機：白板可達的被動／反應事件 10 種 → 16 種（新增 on_crit 3（含已拿掉的爆燃）、on_move 3、on_turn_end 2、on_status_applied 2、on_enter_surface 2、ally_targeted 6；hit_by_spell 3 → 6、enemy_enters_adjacent 1 → 4、enemy_leaves_adjacent 3 → 6、on_collision 3 → 4、on_damaged 2 → 3、on_kill 1 → 2；數字是去重後的結果數，不是配方數）。

## 5. 火杖召喚法術（追加 2，`content/skills/skill_fsum_*.yaml`）

| ID | 名稱 | 召喚物（輪） | 附帶元素（自己） | 費用 | 預算 | 最低角色階級 |
|---|---|---|---|---|---|---|
| skill_fsum_ember_herald | 燼火喚靈 | 元素之靈（3） | 火焰附魔 3 回合 | AP 2、法力 10、冷卻 4 | 82.3% | 1 |
| skill_fsum_cinder_pact | 焰契火靈 | 火靈（3） | 火焰附魔 3 回合 | AP 2、法力 12、冷卻 4 | 89.8% | 2 |
| skill_fsum_storm_pact | 雷契喚靈 | 雷靈（2） | 帶電護盾 1d6 | AP 2、法力 12、冷卻 4 | 78.8% | 2 |

- 法器、稀有、提示屬性智力。召喚原語的其餘效果只能作用在施放者自己，所以附帶元素是自身附魔或帶電護盾；主題推導抓不到這種元素，`skill_scaling.yaml` 逐招加 override `[int, wil]`（元素＋意志組合主題）。
- AP 1 時預算 141%，改 AP 2。`trpg content check`：373 個技能通過。內建技能數 370 → 373。

## 6. 撤步護體（step_back）查證

- **確認失效**：反應技 `shape: self` 的施放區域原點就是持有者自己，`_displace_direction` 算不出方向（`axis_direction(0, 0)` 為 None）就跳過，推擊不結算；實測被近戰打中後只有護盾、持有者沒動。
- **修法**（玩法 PM 追加 7：優先「推開攻擊者」）：效果改成把攻擊者推開 1 格（`shape: single`，目標固定是觸發者，方向是持有者 → 攻擊者），護盾照舊；名稱改「推身護體」。仍是撞擊關鍵字、位移類例外。測試 `test_step_back_pushes_the_melee_attacker_away_and_shields_the_owner`。
- 反推（shove_off）已是同類效果（推攻擊者＋傷害），兩者差在附帶護盾或傷害。

## 7. 快照與 fixture

- `tests/skillgen/fixtures/refactor_3wr2.json`：重產。complete／retier 只新增 3 招（fsum），既有條目不變；flash 抽樣依技能排序，換了 90 筆（同 19c，既有同 key 的值不變）。
- `client/src/render/fixtures/skill_icons.json`：重產，只新增條目。
- CLI 雜湊：合併 main（534e741e，修 5 個失敗測試）後重產（不加 -n），只有 `skills_list`、`skills_show_all/04～15` 改變。
- 計數：`_BAL19_PREFIXES` 加 `skill_fsum_`；`tests/content/test_skill_scaling.py` 370 → 373；`test_coverage.py` 的 `_UNCOVERED` 加 `commanding`。
- 既有測試隨規格更新：`test_rule_lists_3wr2`（白板形狀清單）、`test_whiteboard_3w4`（主動白板形狀集合、「形狀必須簡單」改用 allies_in_radius）。

## 8. 檢查

- 合併 main（534e741e 修 5 個失敗測試）後：`uv run pytest -n 8 --timeout=3000 -m "slow or not slow" tests/content tests/skillgen tests/narrative tests/roguelite tests/api/test_client_fixtures.py tests/engine/test_reaction_skills.py tests/engine/test_summons.py`：6796 passed、14 skipped。
- `tests/cli`（`-m "slow or not slow"`、`-n 8`）：CLI 雜湊重產後 178 passed，Mock 提議快照與 run 種子 2 個隨後修正並單獨重跑通過。
- 再合併 main（82501cb9，世界地圖，不碰技能）後：`trpg content check` 373 個技能通過；`ruff check`、`ruff format --check`、`mypy`（947 檔）、`lint-imports`（7 契約）通過。
- 重播：`trpg battle --map swamp --seed 7` → `battle replay`：88 個動作、313 個事件，一致。
- 稽核：`scripts/skill_balance_audit.py --sections 3 --composer-samples 60`（前後見第 3、4 節）。

## 9. 待 PM 決定

1. **號令只做「傷害提高」**：+25%、持續到你的下回合開始、預算 3 點都是初值；「額外行動」沒做（要新的引擎機制）。號令加了一個狀態欄位與引擎一處乘算（必要的最小改動）。
2. **撤步護體改名「推身護體」並改成推開攻擊者**：06 6.34.1「反應補位移類：被近戰攻擊後，往後退 1 格」的字面要改，請玩法 PM 決定是否同步設計文件。
3. **火杖召喚的縮放屬性靠 override**：三招都逐招列 `[int, wil]`。若想改成規則（例如把附魔狀態 `infused_*`、帶電護盾算進元素主題），會影響既有技能的允許範圍，沒有動。雷契喚靈的元素是雷（不是火），若火杖只要火可以拿掉。
4. **觸發「每種 ≥ 2」以配方總數算**：暴擊白板 1 階 0 個（2 階起 2 個）；watch_mark 只到 2 階；毒霧只有 1 階（錐形狀態在高階湊不到下限）。
5. **形狀上限**：錐形深度 2～4（最多 16 格）、環形半徑 1～2 照組合器既有範圍出，沒有另外限「小範圍」；預算會把傷害壓低。
6. 新增配方、號令、火杖召喚的數值都是初值，沒有跑模擬。
