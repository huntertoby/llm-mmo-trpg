# Phase TF-1 報告：召喚與輔助技的 1 階轉型（伴生、護主、庇佑、援手）

規格：`docs/phases/PhaseTF-1計畫.md`。依據 06 6.34.5（玩法 PM d71642970）、#159；使用者「都按照建議」。

## 1. 做了什麼

| 轉型 | 模板 | 結果 |
|---|---|---|
| 伴生 | `to_passive_companion`（`source: summon`） | 被動，時機 `on_battle_start`；效果 `summon_beside`（縮小版、`companion_duration` 輪） |
| 護主 | `to_reaction_guardian`（`source: summon`） | 反應 `hit_by_melee`、形狀 single 射程 2；`summon_beside`＋`strike_other`，存在 `guardian_duration`（1）輪 |
| 庇佑 | `to_passive_blessing`（`source: support`） | 被動 `on_turn_start`，`target: weakest_ally`、`max_distance: 1`；帶原招的治療／護盾／有益狀態（作用在友方，強度照被動預算重調） |
| 援手 | `to_reaction_aid`（`source: support`） | 反應 `ally_targeted`＋`aid`（護盾、增益：命中判定前）；原招只有治療時改 `ally_hit_near`＋`aid`（受擊後） |

- 大標 `headline_zh` 照玩法 PM 定的四句；`say_zh` 照 06 6.34.5 各轉型的說明寫。既有模板的 `headline_zh`／`say_zh` 沒動。
- 對敵不傷害的招（減速等）照原本的餘波／反擊，沒改。

### 引擎與內容新增的能力（守則 4）

1. 被動時機 `on_battle_start`（`skill_triggers.yaml`，係數 300‰，`random_composer: false`）：`begin_battle` 在 `RoundStarted` 後、第一位行動前收集並結算；沒有持有者時不建索引。
2. 被動對象 `weakest_ally`（`TriggerSpec`，必填 `max_distance`）：同陣營、存活、不含自己（召喚物、護送 NPC 都算），生命比例交叉相乘比，同比例取 ID 小的。
3. 反應 `aid`（`ReactionSpec`）與事件 `ally_hit_near`（必須 `aid`）：援手的射程、條件與效果都以被瞄準／受擊的友方為對象。
4. 原語 `summon_beside`：只用在被動、反應、唯一效果；滿了不召喚（`effect_fizzled` 原因 `summon_limit`，不擠掉舊的）；`strike_other` 時出現在攻擊者旁邊離你最近的空格並立刻反咬一次（方格只有上下左右相鄰，站你旁邊咬不到攻擊者）。預算沿用 `summon` 算法，反咬另計一次每輪價值。組合器、LLM 題目都不用它。
5. 數值工坊：`skill_budget.yaml` 的 `flash_transform`（伴生／護主各一組強度‰與輪數）開進 `kind: budget`。

### 其他配套

- 卡片文字（`narrative/skills.py`）、反應時機文字、工坊參數名與玩家說明（`workshop_text.yaml` 兩筆）、AI 對照、預覽對照。
- 前端：`qIcon/parts.ts` 加 3 個暫代（`summon_beside`→召喚、`on_battle_start`→回合開始、`ally_hit_near`→身旁隊友受擊）、`skillClips.ts` 讓 `summon_beside` 借召喚的動作；`glossary.json` 重產（只多 3 筆）。**沒碰 LF-3 的 5 個檔案。**

## 2. 驗收

（第 4 節填各檢查的結束碼）

- 1 階角色：召喚技 31 招中 28 招有伴生或護主（伴生 28、護主 11；伴生的強度落在 500～900‰，護主 700～1000‰）；`is_support_skill` 的 28 招中 15 招有庇佑或援手，其餘 13 招裡 11 招接續段有傷害（照舊走餘波／反擊），只剩護衛換位、淨化兩招沒有任何新轉型。四種都出現得了（`test_most_summon_and_support_skills_get_a_tier_one_transform`）。
- 既有能轉的招：`_fits` 只拿掉本來就做不出來的模板，新模板排在既有之後，沒有新模板適用的招轉型結果不變。
- 引擎：`tests/engine/test_tf1_transform_engine.py`（開場召出、上限不出現、每場一次、獨狼不受影響、重播相同；護主召出 1 回合並反咬；庇佑挑最虛弱、沒友方不觸發；援手護盾在命中前、治療在受擊後）。

## 3. 快照與夾具

- parity（`tests/skillgen/fixtures/refactor_3wr2.json`）：預測「夾具裡技能是召喚技或輔助技的 flash 鍵」12 個，實際變 10 個（都在預測內；`frost_armor_seal@5@2`、`summon_war_wolf@5@2` 沒變），而且只有第 3 段（大變化那次）的雜湊變。只重寫這 10 個鍵。
  - 第一次預測我誤用了現在的 `_flash_ids()`（取樣點已和夾具不同），列出的鍵和實際不符；改用夾具自己的鍵重新預測後吻合。已寫進上手筆記。
- `glossary.json`：只新增 3 筆（原語、觸發、反應事件）。`skill_icons.json`、`skillCards.json` 不變（新欄位預設值不輸出）。
- 沒有升 LOG_FORMAT。

## 4. 檢查結束碼

| 檢查 | 結束碼／結果 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy src/trpg` | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0 |
| 重播 `open_plain` 種子 7 | 通過（91 動作、383 事件） |
| `tests/content`、`tests/skillgen`、`tests/llm`、`tests/narrative`、`tests/test_primitive_coverage.py`、反應／被動／召喚的引擎測試 | 修完後相關檔全過 |
| slow：`test_refactor_parity.py`、`test_proposal_l8.py`、`test_proposal.py`、`tests/cli -m slow` | 全過（parity 照第 3 節只改 10 鍵） |
| `tests/api`、`tests/roguelite` | 1430 passed、1 skipped |
| 引擎核心（決定性、複製、反應、回合、暫停序列化、獨狼、原語、架構、規則雜湊） | 104 passed |
| 前端 `vitest run`（全部）、`tsc --noEmit` | 全部跑一次只有 `skillClips.test.ts` 1 項失敗（新原語沒有動作）；補上後該檔 29 項全過，`tsc` 0 |

沒跑全量 `scripts/check.py`、沒跑模擬（守則 11）。

## 5. 待 PM 決定

1. **`on_battle_start` 的預算係數 300‰**：新時機沒有前例，照「每場一次」比回合開始（500‰）低一截先定；係數 1000‰ 時半強度 2 輪的伴生只到預算 20～45%，進不了窗。
2. **護主的強度**：照設計「縮小版、存在 1 回合」用設定值 500‰ 進不了反應的預算窗（70% 下限），`_power_tries` 往上找到 700～1000‰ 才合格；也就是護主實際上多半不是縮小版。保守做法是讓設定值只當起點，記在這裡。
3. **護主的位置**：設計寫「在你身邊召出」，但方格只有上下左右相鄰，站你旁邊一定咬不到貼身的攻擊者；改成「攻擊者旁邊離你最近的空格」。都沒空格時退回你旁邊（咬不到就不咬）。
4. **援手的觸發距離**：反應技形狀 single 射程 1（友方要在你身邊 1 格）。`ally_targeted` 原本就要求相鄰。
5. **伴生的費用**：先試沒有費用，再試法力 2、4；不付費會不會太強由預算窗把關。
6. **哪些算「輔助技」**：沿用 `is_support_skill`，另外要求整招含接續段都沒有傷害（例：充能劈砍頂層只有護盾、接續段有傷害，不給庇佑／援手，照舊餘波／反擊）。
7. **2 階以上的召喚技**：轉型種類由種子在做得出來的種類間挑（被動、反應、姿態……），所以 2 階召喚技不一定拿到伴生或護主。
8. **`summon_beside` 的最低角色階級**：沒列（1 階）。召喚技本身 2 階才有，實際不會在 1 階出現。

## 6. 平衡疑慮（不改設計文件）

- 護主：反應預算窗對「1 回合的縮小召喚物」太嚴，設定值 500‰ 幾乎都被推到 900～1000‰。
- 圖騰類（種樹圖騰、高台圖騰、吸引圖騰）、護衛換位、淨化沒有任何新轉型能進預算窗。
- 伴生：開場就有召喚物、不佔行動，係數 300‰ 是起點，沒量過。

## 7. 需要使用者決定的事

- 上面第 1、2 點：`on_battle_start` 係數與護主的強度要不要放寬（例如護主改成存在 2 回合，或反應的預算窗對召喚另算）。請使用者在數值工坊試 `flash_transform` 的四個值後再定。

## 8. 請使用者重開伺服器檢查的重點

- 內容改了（新原語、觸發、反應事件、四個轉型），伺服器要重開；進行中的戰鬥會從頭開始。
- 召喚技、輔助技第 3 次閃現時看得到「伴生／護主／庇佑／援手」其中一個轉型選項與大標。
- 選伴生後下一場開打，身邊就有一隻縮小版召喚物；數值工坊「技能預算表」多四個 `flash_transform` 欄位。

## 開發 PM 裁定

- 接受，已合併，沒有衝突。上手筆記的編號和 LF-1 撞號，已重新編號：LF 是第 43 點，TF-1 是第 44 點。
- 待 PM 決定 1、2、5 是數值：`on_battle_start` 係數 300‰、護主的預算窗、伴生的費用。照使用者規定，全部交數值工坊（`flash_transform` 已開放），由使用者自己調，不另派量測。
- 待 PM 決定 3、4、6、7、8 是規則解讀：召喚物改成出現在攻擊者旁邊、援手射程 1 格、輔助技要整招含接續段都沒有傷害、2 階以上不一定拿到伴生或護主、`summon_beside` 沒有階級下限。照保守做法維持，轉交玩法 PM 確認；要改再開小段。
- 「需要使用者決定」的護主放寬與係數，經專案 PM 轉給使用者，建議先在數值工坊試。
