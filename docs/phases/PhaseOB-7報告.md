# Phase OB-7 報告：遭遇大小（#155）與預設隊友的出場（#154，後端＋內容）

> 實作者：OB-7 實作 agent（Opus 5.5）。前端台詞／對話框／隊伍面板是 OB-8，這段不做。
> 依據：09 9.6.6「遭遇大小」、9.6「系統傭兵」與「預設隊友的出場」、18 18.7.1、決定 #154、#155；歸類表 `docs/phases/PhaseOB-7遭遇歸類.md`（開發 PM 確認、玩法 PM 回覆 Q1～Q6 照建議，設計文件 05a0e8fa）。

## 1. 交付與 commit

| commit | 內容 |
|---|---|
| da6330e2、b148dd81 | 歸類表與 PM 結論 |
| 18a90e35 | #155：兩區遭遇表改隻數；`tests/world/test_next_battle.py` 兩項改用滿 4 名的遭遇變化 |
| a7b7ec38 | #154：開局只帶賽倫、阿岳第 1 步打完才入隊、`escort_parted` 旗標、`WorldView.party_intro`、`PartyMemberView.backstory_zh`、API 型別重產 |
| （本報告） | 報告與上手筆記 |

## 2. 歸類表結果（#155）

照確認後的歸類表改了 25 組（雲嶺 16、荒原 9）：路邊（實地地圖上有 `patrol` 的巡邏隊）一律 2 名；地點戰 4 名的改 3 名；精英巢穴、懸賞、Boss 不改。新手第 1 步渡口 `bandit_raiders`＝`bandit_rookie`＋`bandit_archer_rookie`（1 近戰＋1 弓手）。Q1 吊橋 `sword_array`＝弟子 ×2＋陣眼石靈、劍冢 `tomb_array`＝弟子 ×3。schema 不動（`MIN_GROUP_SIZE` 2）。只改 `content/`，世界日誌的規則鍵因 digest 變而自動標成不能重播；沒有改單位數值。

## 3. #154 逐條

| 設計 | 做法 |
|---|---|
| 開局只帶賽倫 | `content/world/mercenaries.yaml` 的 `default_party: [merc_tiebi]` |
| 賽倫在「確定出發」後、傳送前加入，守印人與賽倫各一句 | 台詞放 `mercenaries.yaml` 的 `escort.intro`；`WorldView.party_intro` 在 `opening.stage` 不是 `pick_class` 時給（＝按了確定出發 `opening_class` 之後）。賽倫**實際上從建角就在隊上**（選大類階段沒有任何戰鬥與隊伍面板入口，玩家感受不到；見待決 1） |
| 阿岳在渡口石階打完後說一句再入隊，坐第 2 個隊友位 | 任務新欄位 `companion_after`（`starter_ferry` 填 `ferry_bandits`）：那一步完成才算該在隊（`trpg.world.companions._joined_yet`）。隊伍只有賽倫，所以直接坐第 2 位、不替換人。台詞 `companions[].join_lines` |
| 阿岳離隊後第 2 位留空，正式選定後才能在城鎮雇用 | 沒有替換紀錄（`companion_bench` 空），離隊後不還原任何人＝留空；入門期雇用本來就被開局閘門擋（`_STARTER_BLOCKED` 的 `HireAction`，21.5 第 9 點），沒改 |
| 隊伍面板名字下面一行來歷 | `PartyMemberView.backstory_zh`：賽倫＝`escort.backstory_zh`、阿岳＝`CompanionDef.backstory_zh` |
| 賽倫的來歷只給開局帶來的那一位 | `hire` 之後賽倫不在新隊伍時記劇情旗標 `escort_parted`（`trpg.world.party.ESCORT_PARTED`）；之後再雇回來不顯示來歷（`party.is_escort`）。留著賽倫只多雇別人不記 |
| 舊角色不補播台詞，來歷照樣顯示 | `party_intro` 在 `opening is None` 時一律 `None`；來歷不看 `opening` |

規則改動：`companion_after` 與 `escort_parted` 會讓同一份世界日誌重播結果不同 → `WORLD_RULES_VERSION` 26 → 27（`save.py` 說明加一條）。`CHAR_FORMAT`、`trpg-wlog`、`LOG_FORMAT`、`SAVE_FORMAT` 不變。舊存檔：不做轉換（使用者原話「存檔都可以刪除」）；舊角色讀得進來，但已在隊上的回春不會被拿掉、舊日誌標成不能重播；沒刪任何存檔檔案。

## 4. 給 OB-8 的接口

- **`WorldView.party_intro: PartyIntroView | None`**（`src/trpg/api/world_party_intro.py`）：一次一段還沒播的加入台詞，賽倫優先、夥伴依加入順序；戰鬥中為 `None`。欄位 `seen_id`（`intro:merc_tiebi`、`intro:companion_ayue`）、`member`、`name_zh`、`lines[{speaker_zh, text_zh}]`。
  - 賽倫：選完大類（`opening_class` 的回應）就出現；前端可以接在 `RangeDoneDialog`（守印人的 `range.done`）之後播，再傳送。
  - 阿岳：渡口石階固定戰打完、回到地圖的那個回應就出現。
  - 播完送既有動作 `hint_seen {ids: [seen_id]}`（沒有新動作；`hints_reset` 清掉後會再播一次）。
- **`PartyMemberView.backstory_zh: str | None`**：放在隊伍面板名字那一列下面。
- 型別已重產（`client/openapi.json`、`client/src/api/schema.d.ts`）；前端沒改程式。
- 文字全部讀 `content/world/mercenaries.yaml`（`escort`、`companions[].backstory_zh`／`join_lines`），前端不寫死。

## 5. 新手模擬報表（`scripts/ob6_newbie_sim.py run --candidates current --per-cell 80 --jobs 4`）

改前＝b148dd81 的 `content/`（`TRPG_CONTENT_DIR` 指過去，渡口 3 隻、預設賽倫＋回春、阿岳接任務就入隊＝第 1 步是主角＋賽倫＋阿岳）；改後＝本段（渡口 2 隻、第 1 步只有主角＋賽倫）。程式同一份。只出表、沒調任何敵人數值。

**第 1、2 步（入門配備）：勝率／主角倒下率**

| 大類 | 步 | 改前勝率 | 改後勝率 | 改前倒下 | 改後倒下 | 平均輪數 前→後 |
|---|---|---|---|---|---|---|
| 近戰 | 1 渡口 | 160/163（98%） | 161/166（97%） | 16/163（10%） | 22/166（13%） | 3.3 → 3.7 |
| 近戰 | 2 竹林 | 160/160（100%） | 160/161（99%） | 33/160（21%） | 42/161（26%） | 2.5 → 2.6 |
| 遠程 | 1 渡口 | 81/81（100%） | 82/82（100%） | 2/81（2%） | 2/82（2%） | 2.7 → 3.4 |
| 遠程 | 2 竹林 | 80/81（99%） | 80/82（98%） | 9/81（11%） | 13/82（16%） | 2.5 → 2.6 |
| 法器 | 1 渡口 | 80/80（100%） | 83/85（98%） | 10/80（12%） | 14/85（16%） | 2.3 → 2.5 |
| 法器 | 2 竹林 | 80/80（100%） | 80/83（96%） | 19/80（24%） | 25/83（30%） | 2.1 → 2.3 |

**第 3 步路上（正式配備；分母＝走到第 3 步的 80 人）**

| 格 | 改前倒下 | 改後倒下 | 改前固定戰勝率 | 改後固定戰勝率 |
|---|---|---|---|---|
| 火焰法杖 點燃＋帶電 | 2/80（2%） | 0/80（0%） | 80/80 | 80/80 |
| 匕首 冰凍＋隱蔽 | 1/80（1%） | 0/80（0%） | 80/80 | 80/80 |
| 巨劍 倒地＋撞擊 | 6/80（8%） | 6/80（8%） | 80/80 | 80/80 |
| 弓 標記＋高處 | 0/80（0%） | 0/80（0%） | 80/80 | 80/80 |

讀法：渡口少 1 隻盜賊，但我方也少了阿岳（3 人 → 2 人），模擬裡第 1 步倒下率反而略升（近戰 10→13%、法器 12→16%），回合變長；第 2 步因為帶著第 1 步剩的 HP（兩步之間不休息）一起略升。第 3 步前回城補滿，幾乎不變。模擬只用效用 AI 代打，不代表真人手感（使用者回報的「第一站頭破血流」是實際操作）。數值由使用者在數值工坊調。

## 6. 改到的測試（舊 → 新）

| 測試 | 為什麼變 | 改法 |
|---|---|---|
| `tests/world/test_next_battle.py::test_full_lineup_turns_into_enemy_first`、`test_door_and_full_reinforcement_cancel` | 斷崖幫寨一般陣容不再有 4 名，「滿員再增援 → 敵方先手」碰不到 | 角色帶劇情旗標 `scarface_rises`（遭遇變化「二當家坐大」3＋精英＝4 名）；斷言不動，另補「確實是 4 名」 |
| `tests/world/test_opening_stages.py::test_versions`、`tests/api/test_pr2a_range_practice.py`（最後一行） | 版號 26 → 27 | 字面值改 27 |
| `tests/world/test_companions.py`（全檔） | 阿岳改成第 1 步完成才入隊；預設只帶賽倫 | 新增 `test_ayue_joins_after_first_step_into_second_slot`；其餘改用 `_with_ayue`（接任務＋第 1 步完成＋同步），替換與還原的測試用自己雇滿的 2 名（`TWO`）；重播那項的「接任務後阿岳在隊」改成「還沒入隊」（規則改了） |
| `tests/world/test_quests.py::test_accept_starter_in_town` | 接新手任務不再出 `CompanionJoinedEvent` | 事件只剩任務開始，補 `companions == ()` |
| `tests/world/test_battle_setup.py::test_setup_units_weather_and_seed` | 預設隊伍 | 我方隊友 `["merc_tiebi"]` |
| `tests/world/test_party.py::test_hire_in_town` | 換下賽倫會記 `escort_parted` | 斷言旗標，其他欄位照舊相同；新增 `test_keeping_escort_records_nothing` |
| `tests/world/test_field_ctx_replay.py` | 凍結重播的雜湊含角色的傭兵；傭兵名單不在凍結內容裡 | `run()` 寫死凍結當時的預設 `FROZEN_PARTY`（賽倫＋回春）；**雜湊 `BEFORE_6CR2` 不變** |
| `tests/api/test_world_dev_boss.py::test_dev_boss_rehearses_to_the_boss_charge` | 固定種子（世界種子＋角色 ID）是在 2 名傭兵下挑的；只帶賽倫時 AI 代打等不到蓄力（另掃了 24 個角色 ID 都等不到） | 不換種子，開打前雇回挑種子時的隊伍 `CHARGE_PARTY`（賽倫＋回春）；斷言不動 |
| `tests/api/test_world_party_api.py`（2 項） | 預設隊伍；接新手任務不再帶阿岳 | 面板成員改 2 列；夥伴那項先雇滿 2 名，接新手任務確認阿岳沒入隊，再接主線第 1 章（`main_mist_rift`，接任務就入隊）測替下回春與說明 |
| `tests/content/test_world_mercenaries.py` | 預設隊伍 | 改 `("merc_tiebi",)`；新增台詞與來歷照設計、escort 必須在預設隊伍、`companion_after` 驗證 |
| 新增 `tests/api/test_ob7_party_intro.py` | — | 只帶賽倫、賽倫台詞出現時機與看過、阿岳台詞、舊角色不補播、來歷三種情況 |

另：`src/trpg/sim/boss_probe.py`（數值工坊與 `cb2e_sim.py` 共用）原本沒指定隊伍的 build 用 `default_party`，改成固定 `PROBE_PARTY`（賽倫＋回春），頭目量測結果不因 #154 改變；`scripts/cb2a_sim.py`（歷史腳本）同樣寫死。CLI 快照沒有變動（`-m slow` 24 項全過，沒重產）。

## 7. 檢查結束碼

| 項目 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | 0、0 |
| `mypy` | 0（1512 檔） |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0 |
| `pytest tests/api tests/world tests/test_architecture.py -n 8`（全部改完後） | 0（2360 passed、1 skipped） |
| `pytest tests/roguelite tests/sim tests/content -n 6` | 0（3399 passed） |
| `pytest tests/cli/test_output_snapshots.py -m slow` | 0（24 passed） |
| `trpg battle --map open_plain --seed 7`＋`replay` | 0、0（91 動作、383 事件一致） |
| `corepack pnpm -C client typecheck`／`test`／`build` | 0／0／0 |

## 8. 待 PM 決定

1. 賽倫實際上從建角就在隊上（選大類階段沒有戰鬥、看不到隊伍），只有台詞等確定出發後才給；若要嚴格「確定出發才入隊」是規則改動（`opening_class` 時才加 `default_party`），要再排。
2. 「之後在城鎮雇用的傭兵不顯示來歷」解讀成：`hire` 後賽倫不在新隊伍就記 `escort_parted`，之後再雇回來不顯示；留著賽倫只加人仍顯示。用劇情旗標存，沒加存檔欄位。
3. 隊友台詞看過記在 `hints_seen`（`intro:<ID>`），「重新顯示提示」清掉後入門期內會再播一次（同 PR-2a 的 `range:practice` 慣例）。
4. 阿岳主線第 1 章（`main_mist_rift`）仍是接任務就入隊（設計只改新手第 1 步）。
5. 模擬裡第 1、2 步主角倒下率改後略升（我方少阿岳），數值由使用者在工坊判斷。
6. 開發用 Boss 排演（`dev-boss`）帶角色當下的隊伍；新角色只帶賽倫時，原本的固定種子等不到霧鎖真人蓄力。測試改成先雇回 2 名；實機排演 Boss 前建議先雇滿。
7. `PROBE_PARTY` 固定賽倫＋回春：頭目量測沿用「主角＋2 名傭兵」的設計前提（9.6.8）。
