# Phase 5B-4 完成報告：任務狀態機與好感度

> 實作者：implementer agent（2026-11-03）。規格：`docs/phases/Phase5計畫.md` 第 16 節（本段先寫規格、commit 後實作）。
> 玩法 PM 2026-11-03（照 #85 2a）：聊天只換資訊；人設卡 `hooks_zh` 依好感度過濾——中立給一般傳聞、友善給隱藏任務入口、信賴才說祕密（例：渡婆婆說出暗門）。已照做並標「玩法 PM 定」。

## 1. 交付

| 項目 | 檔案 |
|---|---|
| 規格 | `docs/phases/Phase5計畫.md` 第 16 節（原「之後各段規格」改為第 17 節） |
| schema 與載入 | `src/trpg/content/world_quests.py`（新）；`src/trpg/content/library.py` 加 `world_quests` 欄位、一個載入呼叫、劇情技能檢查函式 |
| 雲嶺內容 | `content/world/quests/cloud_ridge.yaml`（5 個任務、14 步、劇情技能「破霧」）、`content/world/social/cloud_ridge.yaml`（17 條聊天內容、6 條事件好感度、6 條酒館傳聞）、`content/world/affinity.yaml`（#116 級距） |
| 引擎 | `src/trpg/world/quests.py`（接任務、每個動作後推進、三選一、劇情技能）、`affinity.py`（好感度、`talk_entries`）、`social.py`（聊天、酒館）；`state.py`、`actions.py`、`step.py`、`narration.py` 小改 |
| 外層 | `src/trpg/api/world_story.py`：給說書人的人設卡 `hooks_zh` 換成依好感度能給的內容 |
| 測試 | `tests/content/test_world_quests.py`、`tests/world/test_quests.py`、`tests/world/test_affinity.py`、`tests/world/test_quest_replay.py`、`tests/api/test_world_story.py`（加 3 例）；`tests/content/test_world_events.py` 一處（拿掉事件資料時一併拿掉任務資料） |

`trpg content check` 多三行摘要（任務、聊天、好感度規則）；CLI 快照沒有列這些檔案，不用重產。

## 2. 任務資料格式（`content/world/quests/<region>.yaml`）

```yaml
quests:
  - id: main_mist_rift
    kind: main              # starter／main／chain／hidden
    giver: granny_du        # 接任務要在他所在的地點，且他不敵視你
    start: [...]            # 接任務的條件（只能用狀態型條件）
    steps:
      - id: enter_temple
        when:               # 全部成立才完成這一步
          - {kind: at_location, location: mist_temple_gate}
          - kind: any_of    # 任一成立（不可巢狀）
            conditions:
              - {kind: affinity, npc: acolyte_xiaolian, rank: friendly}
              - {kind: hold_thread, thread: temple_pass}
        reward: {xp_source: main_step, xp_level: 2, story_skill: skill_mist_breaker}
story_skills: [ ...SkillDef... ]   # 劇情技能，不進技能池
```

- **條件**：狀態型 `at_location`、`hold_thread`（有效線頭，個人或世界）、`affinity`（級別 ≥）、`quest_step`（已完成 ≥ n 步）；事件型 `win_battle`（這個動作在該地點打贏）、`situation`（骨架、可選模板、結果）、`talk`（和 NPC 說話）；`any_of`。
- **獎勵**：`xp_source`＋`xp_level`（照 `world/rules.yaml` 的份數：任務鏈一步 3 份、主線一步 5 份、隱藏地點 2 份）、`insight`、`offer`（`whiteboard`／`complete` 三選一）、`story_skill`、`affinity`、`flags`。
- **聊天與傳聞**（`content/world/social/<region>.yaml`）：`talk`（NPC、級別、`rumor`／`quest_entry`／`secret`、文字；級別限制在 schema 檢查：傳聞 ≥ 中立、入口 ≥ 友善、祕密＝信賴）、`event_affinity`（骨架＋結果 → NPC ± 值）、`rumors`（酒館傳聞池，指向地點或骨架，只是文字）。
- 跨檔案檢查：地點、NPC、線頭、骨架與模板、任務步數、劇情技能、關鍵字、經驗來源、入口指向本區隱藏任務且 giver 相符；劇情技能過與 `content/skills/` 同一套引用與費用檢查，並另有測試確認通過預算驗證（`validate_skill` 無違規）。

### 2.1 狀態機

- 新世界動作：`accept_quest`、`offer_pick`、`talk`、`tavern`。
- `world_step` **每個動作之後** 呼叫 `advance_quests`：① 這個動作的情境判定對到 `event_affinity` → 調好感度；② 每個進行中任務（依 ID）目前步驟的條件成立 → 完成並發獎勵（`quest_step_done` → `leveled_up`… → `insight_gained` → `affinity_changed` → `story_skill_granted` → `skill_offered`；最後一步 `quest_completed`）。同一動作可連續完成多步，但事件型條件只認一次。沒有任務、也沒對到好感度表的角色完全不多任何事件（既有測試全部照過）。
- 三選一：角色轉 `RunState`，用 `world_library`（07 7.6 角色階級）呼叫 roguelite `make_offer`，種子＝角色技能種子＋`offers_made`；候選存在 `pending_offers`，有待選時其他動作被拒（閃現的待選優先）。`offer_pick`：城鎮與營火照 `take_candidate` 裝上（裝不下又沒指定替換就放備用），野外一律放備用、不准替換；跳過可。
- 劇情技能：照角色階級（`at_run_tier`）→ 完整技能強度（`as_complete`）→ 放備用、`with_acquired(complete=True)`（不能再閃）；已擁有不重給。
- 新角色欄位（全有預設、`trpg-char/1` 不升版號）：`quests`、`affinity`、`pending_offers`、`offers_made`、`story_flags`。

## 3. 好感度規則

- 值 −100～100、沒有＝0；級別照 #116（≤ −50 敵視、−49～−10 冷淡、−9～19 中立、20～59 友善、≥ 60 信賴），寫在 `content/world/affinity.yaml`（沒有檔案時程式用同一張表）。
- 變化只來自資料：事件結果表（道童、哨兵、兩名修士、狐族旅人、阿岳的請託）與任務步驟獎勵。聊天本身不加減。不影響任何數值（9.6.7 #5）。
- **聊天給什麼（玩法 PM 定）**：`talk` 動作的 `talked` 事件列出依目前級別能給的內容 ID 與可接的隱藏任務；說書人的 `hooks_zh` 換成同一份內容的文字（`talk_entries`，引擎與外層同一個函式）；**信賴級 NPC 的祕密不再是禁止文字**，其他 NPC 的祕密仍禁止。LLM 只能包裝，給什麼由引擎依好感度與資料決定。
- **酒館**：本週傳聞＝傳聞池依 ID 排序後用 `{season_seed}:{region}:rumors:{week}` 的種子洗牌取 3 條；同一週所有人相同、不耗角色亂數串流。

## 4. 可重播

- 新動作都進 `WorldAction` 聯集、寫進 `trpg-wlog/1`；任務進度、好感度、候選、傳聞只由「日誌＋內容庫＋賽季種子」決定，不讀時間、不呼叫 LLM、不用 `random`／`uuid4`／`hash()`。
- `tests/world/test_quest_replay.py`：接任務（線頭已持有 → 接了立刻完成主線第 1 步）→ 聊天 → 接隱藏任務 → 酒館 → 移動遇敵 → 打（勝負照實際）→ 三選一，日誌寫出讀回後重播兩次，角色與世界快照逐字相同、事件相同；新欄位存檔往返；舊角色沒有新欄位照讀。

## 5. 用了 18 的哪些內容

- 18.7.1 新手任務鏈三步（渡口石階、竹林小徑、雨中梯田）；「教學」與阿岳入隊沒做。
- 18.7.2 主線第 1 章五步（事件 17 線頭 → 進山門〔好感度或通行令〕→ 事件 6 → 源晶裂痕 → 雲頂觀）、劇情技能「破霧」。
- 18.7.3 區域任務鏈「青霧觀的分裂」（送信、查私通者、夜襲；中段與結尾三選一、解鎖導師任務鏈的旗標）。
- 18.4 骨架 2、3、6、18、19 的賭注（好感度）、骨架 12、13、10、15 與地點（酒館傳聞）；18.5 每位 NPC 的「和線頭／任務的關係」與祕密（聊天內容）。
- 18.7.4 懸賞沒做（5F-1）。

## 6. 代決（照規格 16.10）

| # | 事項 | 代決 | 誰定 |
|---|---|---|---|
| 5B4-1 | 聊天給什麼 | 中立傳聞、友善隱藏任務入口、信賴祕密；`hooks_zh` 依好感度過濾 | **玩法 PM 定** |
| 5B4-2 | 好感度級距與初值 | #116；初值 0 | 玩法 PM（級距）／開發 PM（初值） |
| 5B4-3 | 好感度怎麼變 | 事件結果表＋任務步驟；聊天不加減；數值 ±5～20 | 開發 PM |
| 5B4-4 | 祕密與線頭 | 祕密只是文字（暗門不給線頭）；信賴級 NPC 的祕密不算禁止文字 | 開發 PM |
| 5B4-5 | 任務怎麼開始 | 一律 `accept_quest`，不自動接 | 開發 PM |
| 5B4-6 | 經驗份數 | 新手鏈與區域鏈每步 3 份、主線 5 份、隱藏 2 份；地點等級寫在步驟 | 5A-SIM2／開發 PM |
| 5B4-7 | 任務鏈段落的靈感 | 新手鏈與區域鏈每步 +1；主線、隱藏不給 | 開發 PM |
| 5B4-8 | 主線第 4 步三方混戰 | 源晶裂痕的一般戰鬥替代 | 開發 PM（PM 指示） |
| 5B4-9 | 劇情技能 | 主線第 2 步給；完整技能、照角色階級、放備用；名稱與元素固定 | 開發 PM |
| 5B4-10 | 三選一 | 新手鏈每步、區域鏈中段與結尾，白板；野外放備用 | 07 7.6／開發 PM |
| 5B4-11 | 「拒絕外人」的情境判定入口 | 沒有模板，只做好感度與通行令 | 開發 PM |
| 5B4-12 | 隱藏任務 | 用 18 的內容組 2 個（丹爐之謎、霜音的謎） | 開發 PM |
| 5B4-13 | 酒館傳聞 | 每週 3 條、賽季種子決定、所有人相同、只是文字 | 開發 PM |
| 5B4-14 | 撤離勝利條件 | 先用一般勝利 | 開發 PM |

另外實作時定的：
- 劇情技能「破霧」的數值（實作者定，過預算驗證）：控場骨架、法術、任何武器、感知縮放、3×3 射程 3、AP 2、法力 6、冷卻 4；揭露 1 回合、清除表面（煙霧、毒）、1d4 神聖傷害。原本想用風元素，但「元素傷害只能看智力」，又不想讓劇情技能綁死智力，改用神聖（感知可縮放）；揭露 2 回合會超出預算，改 1 回合。
- 「治療」不是關鍵字表裡的關鍵字，區域鏈的偏向只記了「帶電、隱蔽」。

## 7. 待 PM 決定

1. **三選一的關鍵字偏向**（18.7.3「偏向治療、帶電、隱蔽」、7.6「偏向該區的關鍵字」）：候選產生器沒有關鍵字偏向的輸入，資料先記錄、不影響候選；要做需要改 `trpg.skillgen`（另排一段）。「治療」也沒有對應關鍵字。
2. **新手鏈的保底**（7.6「至少 1 招被動」「加深／橋接／新方向 1／0／2」）：目前照一般白板三選一的比例，沒有強制。
3. **劇情技能的 LLM 換名稱與元素**（7.6）：還沒接；「破霧」數值請玩法 PM 看一下（第 6 節）。
4. **聊天給線頭**：渡婆婆的暗門目前只是文字。若要讓信賴級的祕密也給「斷崖幫寨的暗門」線頭（帶來優勢與先手），和 9.6.7 #6「線頭只能由事件結果產生」衝突，需要使用者或玩法 PM 決定。
5. **放棄／交涉／戰鬥解法的結算與線頭到期結局**（5B-2 留下的）：不在 5B-4 列，還沒做；主線「叛徒戰」、二當家坐大也等它。
6. **導師任務鏈**（青崖道長，#95）：只留了旗標 `mentor_qingya`，內容待玩法 PM。
7. **隱藏任務 2 個與事件好感度數值、聊天文字**是我用 18 的內容組的，請玩法 PM 確認。
8. 主線第 5 步（雲頂觀 Boss）目前就是雲頂觀的一般遭遇勝利；Boss 階段在 5F-2。

## 8. 檢查

- 已 `git merge main`（含 5A-M1b，`fc0db05a`），合併後重跑。
- `uv run pytest -q tests/world tests/content tests/api/test_world_story.py tests/test_architecture.py -n 8 --timeout=1800`：2253 passed（`tests/content/test_world_situations.py` 一個「拿掉情境模板」的測試補上一併拿掉任務與聊天資料，因為任務條件引用模板）。
- `uv run pytest -q tests/cli tests/test_architecture.py -m "slow or not slow" -n 8 --timeout=3000`：187 passed。
- `ruff check .`、`ruff format --check .`、`mypy`（1039 檔）、`lint-imports`（9 kept）全部通過。
- 新增的 `# noqa`：`quests._leaf_holds` 的 `PLR0911`（每種條件一個分支）、`step._dispatch` 的 `PLR0911`（動作分派，每類動作一個出口）。
