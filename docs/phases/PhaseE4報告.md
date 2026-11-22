# Phase E4 報告｜觸發篩選與新時機（element、attack_kind、source；on_block、on_displace）

> 規格 `docs/phases/PhaseE4計畫.md`；規則以 `docs/design/08-裝備.md` 8.29 E4（#175）為準，施工草案 `docs/phases/E2-E5草案.md` 的 E4 節。基準 main `c9acff0d7`（含 E1、E2、E5、KD-1、HC-8）。E3 的檔案（`unit_rules.py`、`_do_move`、`movement.py`、`turns.py`、`position.py`）沒動；`effects/world.py` 只改 `_push_unit`，沒碰 `set_surface`。

## 1. Commit

| 項目 | commit |
|---|---|
| 1 篩選欄位（`TriggerSpec`、`TriggerAffix` 的 `element`、`attack_kind`、`source`、`reaction`；能搭哪些時機的檢查） | `343b165da` |
| 2 篩選的結算（`Ctx.attack_info`、元素延到結算時對照、近戰同格擋） | `4c4da4303` |
| 3 新時機 `on_displace` | `ea0a2eb93` |
| 7 「站穩」圖示移植 | `bca3c421c` |
| 4 新時機 `on_block` | `9c55ace2d` |
| 5 卡片句子（篩選寫在觸發時機那一行）、時機數改從 `REQUIRED_TRIGGERS` 推 | `9ad091a8c` |
| 6 KD-1 驗收的兩件用字（倒地 6 行、彈射卡同名加次數） | `7a934eb78` |
| 8 收尾（`classify.py --check`、上手筆記、截圖） | `fe06b0c50` |
| 合併 main（含 E3 `967569588`）：`skills/cast.py` 的匯入兩邊都留（E3 的 `leave_trail`、E4 的 `AttackInfo`）；`寫死數值-清單.md` 取 main 再重產；`set_surface` 的 `surface_trail=None` 保留 | `ae42be782` |
| 報告 | 最後一個 commit |

第 7 項比第 4 項先 commit（前端檔案和第 3、4 項分開，順序不影響內容）。

## 2. 各項做法

### 2.1 篩選欄位（第 1 項）

- `content/skills/constants.py`：`ON_BLOCK`、`ON_DISPLACE`、`AttackKind`（`melee`／`ranged`／`spell`）、`AttackSource`（`attack`／`skill`／`reaction`）、`TRIGGER_FILTER_TIMINGS`、`trigger_filter_problem`。
- 能搭配的時機（保守）：
  - `element`：`on_hit`、`on_crit`、`on_damaged`。
  - `attack_kind`、`source`、`reaction`：上面三個再加 `on_block`（看被擋下的那次攻擊）。
  - `on_kill`、`every_n_hits`、`on_natural_20` 都不開。
- `reaction` 一定要搭 `source: reaction`。裝備詞條的反應 ID 在 `gear_checks` 對照 `reactions.yaml`；被動技的反應 ID 沒有做存在檢查（查不到就永遠不觸發）。
- 四欄預設 `None`，用 `exclude_if` 不輸出。既有技能、詞條序列化不變，規則包的技能部分不變。
- `melee_only` 不動。
- `TRIGGER_PARAM_NAMES` 和 `skill_triggers.yaml` 的 `params` 都沒加新篩選。所以 LLM 提議與組合器不會產生篩選；只有手寫內容與裝備詞條能用。

### 2.2 篩選的結算（第 2 項）

- 篩選需要的資訊放在 `Ctx`，不加事件欄位：
  - **攻擊種類** `Ctx.attack_info`（`trigger_types.AttackInfo`：攻擊者、`kind`、`source`、`reaction`）。由 `skill_triggers.attacking(ctx, info)` 括號設定，巢狀時（例如攻擊中途反擊）結束後還原外層。
    - 普攻、反應攻擊：`reactions.perform_unit_attack` 多一個 `reaction_id` 參數。反擊、監視射擊、藉機攻擊的三個呼叫點都帶 `picked.id`；召喚物反咬沒有 ID。
    - 施放：`Cast.run` 包住整個施放，`Cast.attack_info()` 提供種類。
  - **近戰**和格擋同一套：普攻看 `is_melee_attack`（武器射程），技能看 `profile.height_limited`（傳給 `block_multiplier` 的同一個值）。不是近戰時，法術技算 `spell`，其他算 `ranged`。
  - **來源**：反應技（`kind: reaction`）算 `reaction`，反應 ID 是技能 ID；其他施放（主動、被動、陷阱、裝備）都算 `skill`。
  - 有種類、來源篩選，但這次傷害不屬於任何攻擊（燃燒、表面等）時：不觸發。
- **元素**（8.29 E4 第 4、5 點）：
  - `on_damaged`：直接看 `DamageDealt.element`，所以燃燒、毒表面都算。裝備觸發照舊每回合最多 1 次。
  - `on_hit`／`on_crit`：命中判定時還沒有傷害。所以收集時把要求的元素記在 `Fired.element`；`settle` 每一批再對照 `Ctx.dealt_elements`（這一批裡，攻擊者對目標 `cause: attack`、傷害大於 0 的元素，也就是轉換以後的元素）。同一個持有者、同一條被動或詞條、同一個另一方只留第一筆，所以多段、多下的攻擊只觸發 1 次。
  - `dealt_elements` 只在有人帶這類篩選時才記（`PassiveIndex.element_hits`），每批清空；沒有觸發的批次也清。
- 沒有篩選的觸發原樣保留，順序不變。

### 2.3 on_displace（第 3 項）

- `skill_triggers.collect_displace(ctx, source_id, moved_id)`：持有者是推的人，另一方是被推的人；自己位移自己不算。沒有持有者時直接返回。
- 呼叫點：
  - `effects/world._push_unit`：推、拉、擊退都走這裡。第一格真的移動之後記 1 次；第一格就被擋住只有撞擊。推進致命地形、墜落也算，因為已經移動了。
  - `effects/handlers._move_unit`：`mode: teleported`，傳送別人，位置真的改變時。
  - `effects/handlers._swap_units`：互換的兩個人各記 1 次，`source_id` 自己不算。包含「換位」基本動作與 `swap_any`。
- 冰上滑行：被推、拉進冰面照舊不滑（`ice_slide` 的既有規則）；自己走的滑行沒有 `source`，所以不會另外算。
- 預算係數 250‰（保守，比撞擊的 300 低），`random_composer: false`。工坊沿用 `triggers[*].budget_coefficient_permille` 白名單，自動開放。

### 2.4 on_block（第 4 項）

- `reactions.block_multiplier`：格擋類反應（`reduce_damage`）真的用了（`_react` 回傳定義）之後呼叫 `collect_block(ctx, blocker, attacker)`。
  - 一般格擋、規則改成 `targeted_by_attack` 的遠程格擋、提示裡選「格擋」都經過這裡。
  - 替隊友擋（`intercept`）、替隊友承受（`redirect_damage`）、盾兵掩護都不經過這裡。
  - 倒地時 `_react` 開頭就擋下，所以不會觸發。
- 另一方是攻擊者；`attack_kind`、`source` 篩選看被擋下的那次攻擊（`Ctx.attack_info`）。
- 預算係數 250‰（保守），`random_composer: false`。

### 2.5 時機清單與文字（第 5 項）

- `REQUIRED_TRIGGERS`、`skill_triggers.yaml` 各加 2 筆（`name_zh`、`llm_hint`、`description_zh`）。
- 工坊文字 `workshop_text.yaml` 加 2 筆，都是實作者初稿，待玩法 PM 改寫。
- 卡片句子：`narrative/skills.trigger_filter_text`。觸發時機那一行在有篩選時加「（只算火焰傷害、近戰、反應：藉機攻擊）」；沒有篩選時字不變。
- 測試的時機數：`test_skill_triggers_content` 本來就對照 `REQUIRED_TRIGGERS`，只把名稱裡的「twelve」拿掉；數量快照 `tests/content_counts.json` 重產（17 → 19）。
- 前端：
  - 新時機先借圖，加在 `TRIG_ALIAS`：`on_block` → 「被近戰命中時」（劍砍向盾），`on_displace` → 「造成撞擊後」。正式圖交美術 PM。
  - 名詞表 `glossary.json` 重產。

### 2.6 KD-1 驗收的兩件用字（第 6 項）

- 倒地：`narrative/status_info._prone_lines` 改成玩法 PM 定的 6 行。
  - 「1 AP」取自 `prone_ap_loss`。「一半」取自 `prone_stand_up_move_permille`：剛好 500‰ 寫「一半」，其他值寫「30% 的」。
  - 照目前的值組出來，和規格的字一字不差（`tests/narrative/test_kd1_wording_e4.py`）。
  - `prone_ap_loss`、`steady_rounds` 是 0 時，那一行照舊不寫。
- 名詞表 `GlossaryEntry.rules_only`：只有倒地是 `true`，其他是 `None`，不輸出。
  - 前端 `entryTipParts`：`rules_only` 時一條規則一段、前面加「・」，不接狀態說明。
  - `statusTile` 的 tip 用換行連接。
  - OpenAPI 與 `schema.d.ts` 重產。
- 彈射卡：`attack_shapes.skill_note_zh` 的招名清單，同名的只寫一次並加次數（「鉤爪 ×2」），照第一次出現的順序。

### 2.7 「站穩」圖示移植（第 7 項）

- `qIcon/status.ts` 的 `NEW` 最後照移植需求原樣加 `steady`；`AWAITING_ART_STATUSES` 變成空陣列。
- `statusFit.json` 用開發頁 `?set=fitgen` 重產：無頭 Chrome，加 `--disable-gpu`。
  - 只多 `steady|16.80|0.00: 0.74`、`steady|9.00|0.00: 0.7`，和樣張量到的相同；其他鍵沒變。
- 測試：
  - 規格列的 5 個測試照做。
  - 實際還有 3 個也靠 `AWAITING_ART_STATUSES` 過濾，一起更新：`statusIcon.test.ts`、`ui/qi3bStatusCorner.test.ts`、`wl1bFallbackList` 的快照（待畫清單的 `steady` 拿掉）。
  - 基準 `qi3bStatusBaseline.json` 只多 `head|steady`、`card|steady` 兩個鍵，既有的鍵沒重錄；`AFTER_QI3B` 加 `steady`。
- `statusIcon.test.ts` 要求每個狀態都有舊式線條圖樣 `GLYPH`（部件圓片以外、召喚物頭頂的退回）。這次補了一個站穩的線條圖，畫法同倒地但站直。美術沒有指定這個，見待決。
- 技能組裝列的部件圓片不收 steady（美術 PM 第 7 節裁定）：`skillIcon.test.ts` 的部件庫檢查把 steady 排除，註明原因。
- 逐像素比對：
  - 遊戲端 `tileCanvas(statusIconTile("steady"))`／`statusIconCanvas("steady")` 對 `steady-2-true1x.png` 的 B 欄。狀態卡 20 用 ×6、頭頂 11 用 ×8，DPR 2 的對照格各用 ×3、×4。
  - 真 1 倍 400／400、121／121 像素相同；DPR 2 1600／1600、484／484 相同。透明處合成到樣張底色比，容差 ±2。

### 2.8 收尾（第 8 項）

- `classify.py --check`：新的 `_half_text` 用了 `× 2`，判斷是不是剛好「一半」。歸 `const`，規則 `py-narrative-status-info-half-e4`，附理由；清單文件重產。
- 上手筆記 `docs/dev/上手-引擎戰鬥結算.md` 第 60 點。

## 3. 新規則的測試

| 檔案 | 內容 |
|---|---|
| `tests/content/test_trigger_filters_e4.py` | 預設 `None` 不輸出、既有內容沒有篩選、能搭的時機、`reaction` 要 `source: reaction`、不合法的值、`melee_only` 照舊 |
| `tests/engine/test_trigger_filters_e4.py` | 轉換後的元素才算；多下對同一目標只 1 次；多段任一段符合（冰＋物理）；燃燒、毒表面算；近戰普攻、近戰武器技算近戰、法術技是法術、弓是遠程；來源（普攻／技能／反應）；藉機攻擊的 `reaction` 篩選與「近戰反應攻擊」；裝備的元素與種類篩選；舊 `melee_only` 的結果不變；重播確定性 |
| `tests/engine/test_displace_trigger_e4.py` | 推 2 格只 1 次、另一方是被推的人；拉；第一格被擋＝只有撞擊；推 1 格後被擋仍算 1 次；傳送別人；和施放者互換只算對方；兩人互換各 1 次；推上冰面只 1 次；「換位」1 AP 觸發、同回合換位兩次裝備只觸發 1 次（8.21.5.3）、被動照每輪次數（1 次／2 次）；確定性 |
| `tests/engine/test_block_trigger_e4.py` | 真的格擋才算、另一方是攻擊者；預設規則下遠程不格擋就不算；遠程也能格擋時算，`attack_kind` 看被擋的攻擊；提示裡選格擋算、拒絕不算；倒地時不觸發；替隊友擋不算 |
| `tests/narrative/test_trigger_filter_text_e4.py` | 新時機的名稱、`llm_hint`、工坊文字、係數 250、`random_composer: false`；卡片句子 |
| `tests/narrative/test_kd1_wording_e4.py` | 倒地 6 行一字不差、跟著工坊值走、名詞表 `rules_only`；同名招加次數 |
| `client/src/ui/tipPartsE4.test.ts` | 倒地的說明卡一條一行、其他狀態照舊、部件圓片 tip |

被動技每輪次數照現有規則：`max_per_round: 1` 的被動，同一輪換位兩次只觸發第 1 次；`max_per_round: 2` 時兩次都觸發。裝備詞條照 8.21.5.3，每回合（`limit: per_turn`）或每輪最多 1 次。

## 4. 驗收

基準 `c9acff0d7`，用 `git archive` 取出 `src`、`content`、`scripts`、`config` 到暫存區；執行時確認載入的 `trpg` 來自基準那份。腳本放在暫存區，沒進 repo（同 E5 的 `compare78.py`、`budget.py`、`census_cmp.py`）。

| 檢查 | 結果 |
|---|---|
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill` 違規） | `cmp` 0，逐位相同（442 筆） |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時） | `cells=204 different=0`（整份相同） |
| 78 場戰鬥（`compare78.py`，同 a 段那組；去掉 `ruleset_hash`、內嵌規則包，`format` 也比） | 第 2、3、4 項各跑一次，都是 `battles=78 events=26741 different=0`。內嵌規則包只差 `skill_triggers.triggers` 的長度（17 → 18 → 19，新加的兩個時機） |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| ruff、format、mypy、lint-imports | 0 |
| tsc、vitest、build | tsc 0；build 0；vitest 0（4909 passed） |
| `uv run python scripts/check.py` | FULL_RESULT |
| `uv run pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli` | SLOW_RESULT |

`LOG_FORMAT` 不升版（合併 E3 後是 `/138`，E4 沒有改紀錄格式）：沒有新事件、動作、狀態欄位。`Ctx.attack_info`、`Ctx.dealt_elements`、`Fired.element` 都不在戰鬥狀態裡。

## 5. 截圖（`docs/art/shots/e4/`，交美術 PM）

實機（`trpg serve`）：從開發選單「一鍵開局」進入，用頁面腳本換掉 `POST /api/battles` 的內容，改成靶場＋工坊試玩的兩個測試被動。倒地、站穩是在回應裡替主角加上狀態（只改畫面資料）。jpg 品質 80，單張都在 300 KB 以下。

| 檔 | 內容 |
|---|---|
| `e4_on_block_card_1600x900.jpg`、`e4_on_block_card_800x600.jpg` | 被動「格擋時（只算近戰）」的技能卡：組裝列的時機圖（暫借「被近戰命中時」）、「觸發時機：格擋時（只算近戰）」 |
| `e4_on_displace_card_1600x900.jpg` | 被動「你讓別人位移時」的技能卡（時機圖暫借「造成撞擊後」） |
| `e4_kd1_prone_tip_1600x900.jpg`、`e4_kd1_prone_tip_800x600.jpg` | 倒地的說明框：6 行，每行前面「・」，沒有摘要句（KD-1 驗收小修 1） |
| `e4_kd1_steady_1600x900.jpg` | 主角身上的「站穩」：HUD 狀態列、頭頂、說明框（KD-1 驗收最後一節的補拍） |
| `e4_steady_closeup_x6.png` | 站穩的狀態卡 20、頭頂 11，真 1 倍與 DPR 2，各 ×6 最近鄰（遊戲端畫法；和樣張 B 欄逐像素相同，見 2.7） |
| `e4_bounce_card_x2_1600x900.jpg` | 彈射的說明卡：「這招不能套用：鉤爪 ×2、守護之盾」（KD-1 驗收用字第 2 件）。暫存內容複本多一招只給截圖用、對所有技能的彈射（同 KD-1 的做法）＋坦克主角、兩件授予「鉤爪」的自訂裝備（鉤索圓盾、鉤爪護手） |


## 6. 待 PM 決定

1. **（開發 PM 已同意，請玩法 PM 確認）讓另外兩人互換位置時，兩人各觸發 1 次**。8.29「一次位移只觸發 1 次」我解讀成「每個被位移的人各算 1 次」。「換位」基本動作也算互換。
2. **（開發 PM 已同意）反應技的來源算 `reaction`**，反應 ID 用技能 ID；內建反應攻擊用 `reactions.yaml` 的 ID；召喚物反咬沒有 ID。
3. **（開發 PM 已同意）`attack_kind` 的分法**：近戰照格擋；不是近戰時，法術技算 `spell`，其他算 `ranged`。
4. **（開發 PM 已同意）命中時、暴擊時的元素篩選只看這次攻擊造成的傷害**：條件是 `cause: attack`，而且傷害大於 0。被擋到 0 點的不算；撞擊、爆炸這類附帶傷害也不算。`on_damaged` 每一筆傷害都看。
5. **（開發 PM 已同意）篩選能搭的時機**：`on_kill`、`every_n_hits`、`on_natural_20` 不開；`on_block` 不開元素篩選，因為還沒有傷害。
6. **舊 `melee_only` 的實際行為和草案寫的不同**：草案說「技能傷害不算」，實際是「`cause: attack`，而且距離在近戰範圍內」，貼身的法術技也算（`test_gear_on_damaged_kind_filter_differs_from_melee_only` 有測）。照規格不改，現有結果不變。
7. **新時機的預算係數**：`on_block`、`on_displace` 都先給 250‰（保守），已開放在工坊（既有白名單）。依守則 8，這是數值疑慮，該記進 `docs/design/平衡待查.md`；但這段不改 `docs/design/`，所以只寫在這裡，請 PM 轉記。
8. **LLM 與組合器不會產生篩選**：`TRIGGER_PARAM_NAMES` 和 `params` 都沒加，因為加了就要改 LLM 的提議 schema，也會動到快照。要開放請另排。被動技的 `reaction` ID 也沒做存在檢查，填錯的話不會觸發。
9. ~~彈射卡「鉤爪 ×2」的實機補拍~~：已補（`e4_bounce_card_x2_1600x900.jpg`，開發 PM 指示）。
10. **站穩的舊式線條圖樣 `GLYPH`**（部件圓片以外的退回、召喚物頭頂）：`statusIcon.test.ts` 要求每個狀態都要有，美術沒有指定，我照倒地的畫法改成站直的小人。要換的話請美術 PM 給。
11. **倒地、站穩的實機截圖是在畫面資料裡加狀態**：所以技能列沒有「起身」鈕，反應欄也沒灰（伺服器端的狀態沒變）。這兩張只拍說明框與圖示。
12. **工坊文字兩筆是實作者初稿**（`觸發.on_block`、`觸發.on_displace` 的 `player`），待玩法 PM 改寫。
