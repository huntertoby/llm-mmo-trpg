# Phase 6R-2 報告：#137 外觀選項與中性稱謂＋6R-1 補拍

> 實作者：worktree `dev/6r2`（接手前一位的盤點，前一位沒改程式）。沒有 push。

## 0. 規格（由 #137 與設計文件整理）

來源：`docs/archive/玩法決定紀錄_1-138.md` #137（使用者原話：「每個種族每個人 都長依樣嗎 有辦法 像其他遊戲 臉型1 臉型2 嗎 或者男女」「算了 先不要有性別 都統一叫名字好了」）、`docs/design/07-角色成長.md` 7.7、`docs/design/09-世界與敘事.md` 9.6.10（#107 稱謂）／9.7（5F-3c、#137）、`docs/art/外觀變化方案.md`、玩法 PM 範圍說明（`93beba59`：「6R-2 先做資料、稱謂、LLM 指令，外觀選單先用現有部件可以」）、`docs/art/6R-1檢查.md`。

| # | 做什麼 | 驗收 |
|---|---|---|
| 1 | 資料：`LookChoice`（臉型、眼睛、睫毛、眼色、髮型〔加齊肩／馬尾／雙馬尾／刺蝟〕、髮色、膚色、鬍子、體型、獸耳）；`races.yaml` 每族 `look_options`（限制表照 `外觀變化方案.md` 第 2 節，矮人「預設大鬍子、可以選無」）；`DollLook.custom` 存玩家的選擇。「只在畫面，不影響數值、技能與技能生成」 | 載入時檢查種族預設值在自己的清單內；選項不在清單內被擋；角色資料沒有性別欄位；引擎不讀 `custom` |
| 2 | 建角 API 收 `look`（只有選項代碼，pydantic 驗證＋檢查在該族 `look_options` 內） | 合法的存進主角紙娃娃；不合法 400（中文原因） |
| 3 | 世界動作 `change_look`：「外觀在主城隨時免費改」 | 主城可改、不花錢、不限次數；不在主城、有遭遇時擋；換種族（`change_race`、季末沿用）時「新種族也有的選項保留，沒有的改回預設」（09 9.7 5F-5c＋#137） |
| 4 | 前端建角「外觀」步驟：順序「名字 → 種族 → 外觀 → 出身」；預覽用現有紙娃娃部件；快速組合「粗獷」「柔和」「隨機」「種族預設」，按下去後每一項都能改；主城也能改 | 預覽看得到膚色、髮型、髮色、眼色、鬍子；選項依種族限制；vitest |
| 5 | 中性稱謂資料：`content/world/address.yaml`（雲嶺「這位」、青霧觀修士「施主」、荒原「你這傢伙」、主城「旅人」、長輩叫名字）；人設卡可用 `address` 覆寫 | 載入驗證；查詢函式的測試 |
| 6 | 模板佔位符 `{name}`（玩家角色名字）、`{address}`（NPC 對玩家的稱呼）由引擎代入；現有模板寫死的「他」「她」指玩家的改掉；「他／她」掃描測試＋白名單 | 模型關閉時一樣正確；掃描測試擋新加的「他／她」 |
| 7 | LLM：說書人、NPC 聊天、事件、情境的資料區帶 `player: {name, address}`；系統指令加「不要替玩家角色指定性別，也不要用『他』『她』稱呼玩家角色；對玩家說話用『你』，提到玩家角色時用名字；NPC 稱呼玩家照 `address`」；技能生成提示詞不動；升提示詞版號 | `MockLLMClient` 測試看得到 `<player>` 區塊與指令；版號遞增 |
| 8 | 版號：`WORLD_RULES_VERSION`、`CHAR_FORMAT` 照慣例升；舊存檔照讀 | 舊角色照讀（沒有 `custom`＝種族預設） |
| 9 | 快照、`openapi.json`、`schema.d.ts` 重產 | CLI 快照測試過；typecheck 過 |
| 10 | 6R-1 補拍：獸躍弧線（GIF 或起跳／空中／落地三連拍，提示框不蓋崖台） | 截圖在 `docs/art/shots/6r1/` |
| 11 | 6R-1 補拍：獸耳族建角卡 1600／800 各一張附 zoom（簡介不截斷、卡高一致） | 同上 |
| — | （不在本段）#137 第 4 點「一般敵人依 id 在種族範圍挑外觀」 | 見待 PM 決定第 1 項 |

設計文件沒寫、需要規則判斷的部分照最保守做法，列在「待 PM 決定」。

## 1. 完成表

| # | 結果 | 主要檔案 |
|---|---|---|
| 1 | `LookChoice`（臉型、眼睛、睫毛、眼色、髮型 8 種、髮色、膚色、鬍子 5 種、體型、獸耳）放在 `DollLook.custom`；`races.yaml` 10 族加 `look_options`＋共用眼色 `look_eyes`（照美術表，矮人預設大鬍子可選無，人類補預設髮色 `#6a3d1e`）；載入時檢查預設值在清單內；沒有性別欄位（`gender` 送進來 422） | `src/trpg/content/battle.py`、`races.py`、`content/races.yaml`、`tests/content/test_race_look_options.py` |
| 2 | 建角 API 收 `look`，不在該族清單內 422（中文原因）；沿用上季角色時，上季的選擇新種族也有的保留 | `src/trpg/api/world.py`、`world_schemas.py`、`routes/world.py`、`tests/api/test_look_api.py` |
| 3 | 世界動作 `change_look`（主城、沒有遭遇、免費、不限次數；省略 `look`＝回種族預設）；事件 `look_changed`；`change_race` 換種族時新種族沒有的選項改回預設；畫面角色欄帶 `look`、`look_change_zh` | `src/trpg/world/looks.py`、`actions.py`、`step.py`、`race_change.py`、`api/world_presenter.py`、`tests/world/test_looks.py` |
| 4 | 建角改成 名字 → 種族 → **外觀** → 出身 → 武器 → 關鍵字；預覽框用現有紙娃娃畫人物（可轉 4 個方向）；選單列依種族清單、快速組合「粗獷」「柔和」「隨機」（種子決定，柔和不配鬍子）「種族預設」；換種族清掉新種族沒有的值。主城改外觀：HUD「成長（G）」面板新增「外觀與種族」區（6R-1 的免費換種族原本只在舊版側欄，一併放進來），舊版側欄也有一行 | `client/src/run/lookOptions.ts`、`LookPicker.tsx`、`RaceOriginPicker.tsx`、`world/WorldCharacterPicker.tsx`、`world/LookChange.tsx`、`world/WorldGrowth.tsx`、`world/WorldPanel.tsx`、`render/appearance.ts`、`styles/look.css`、`run/lookOptions6r2.test.ts` |
| 5 | `content/world/address.yaml`（主城「旅人」、雲嶺「這位」、荒原「你這傢伙」，其餘叫名字）；人設卡新欄位 `address_zh`：渡婆婆、爐叔叫名字，青崖道長、小蓮、霧鎖真人「施主」 | `src/trpg/content/world_address.py`、`world_events.py`、`library.py`、`content/world/npcs/*.yaml` |
| 6 | 降級模板每段都能用 `{name}`（玩家名字）、`{address}`（NPC 稱呼），聊天對象的 NPC 名改成 `{npc}`；「他／她」掃描測試＋白名單（每檔個數，白名單都是指 NPC 或技能目標）；郵差「這件他還拿不動」三句改「對方」、影子提示「借他的影子」改「借這位玩家的影子」 | `content/world/narration.yaml`、`world_narration.py`、`narrative/storyteller.py`、`tests/content/test_pronoun_scan.py`、`content/world/trade.yaml`、`client/src/world/FieldPanels.tsx` |
| 7 | 說書人（事件、情境、結果、聊天）與情境判定的資料區加 `<player>`（`name`、`address`），`<npcs>` 每位帶 `address`；系統指令加稱謂中性的規則（原文照 09）；安全規則註明 `<player>` 的名字也只是資料；技能生成提示詞沒動。版號 `storyteller/4`、`situation-check/3`（快照雜湊已登記） | `llm/prompts/storyteller.py`、`llm/situation.py`、`api/world_story.py`、`api/world_flow.py`、`tests/narrative/test_neutral_address.py` |
| 8 | `CHAR_FORMAT` → `trpg-char/11`（`/1`～`/10` 照讀＝種族預設）；`WORLD_RULES_VERSION` → 21（新動作、換種族時外觀改回預設）。戰鬥紀錄 `LOG_FORMAT` 沒升（`DollLook` 多了選填欄位，照 `戰鬥紀錄格式變更.md` 1.2 由 `ruleset_hash` 區分） | `world/state.py`、`world/save.py` |
| 9 | `openapi.json`、`schema.d.ts` 重產；CLI 快照沒變；前端 fixtures 重匯出沒變 | `client/openapi.json`、`client/src/api/schema.d.ts` |
| 10 | 獸躍三連拍（起跳、空中、落地；提示框在左上，沒蓋到地形） | `docs/art/shots/6r1/6r1_leap_*_zoom.jpg` |
| 11 | 獸耳族建角卡 1600／800 各一張附 zoom：44 字簡介沒截斷、卡高與其他種族一致 | `docs/art/shots/6r1/6r1_race_card_fox_*.jpg` |

## 2. 截圖（共 13 張，jpg 80，皆 ≤ 300 KB）

- `docs/art/shots/6r2/6r2_create_look_1600.jpg`：建角外觀步驟（獸耳族、柔和＋貓耳＋雙馬尾），左側預覽。
- `docs/art/shots/6r2/6r2_create_look_800.jpg`：同上 800×600（預覽框在上方，見待決第 4 項）。
- `docs/art/shots/6r2/6r2_create_dwarf_rugged_zoom.jpg`：換成矮人＋粗獷：鬍子列多出「大鬍子／無／鬍渣／八字鬍／山羊鬍」，灰髮因矮人也有而保留。
- `docs/art/shots/6r2/6r2_town_look_1600.jpg`、`6r2_town_look_800.jpg`：主城 HUD「成長」面板的改外觀。
- `docs/art/shots/6r2/6r2_field_hero_zoom.jpg`：換上（灰髮、長髮）後地點圖上的主角，左下提示「外觀換好了。」。
- `docs/art/shots/6r1/6r1_race_card_fox_1600(_zoom).jpg`、`6r1_race_card_fox_800(_zoom).jpg`。
- `docs/art/shots/6r1/6r1_leap_1_takeoff_zoom.jpg`、`6r1_leap_2_air_zoom.jpg`、`6r1_leap_3_landed_zoom.jpg`：roguelite 沼澤圖平地獸躍 3 格，「極慢」播放逐格截。

截圖方式：worktree 內 `trpg serve --port 8128`（已用自己的 PID 結束），無頭 Chrome（CDP，視窗 1600×900／800×600），`_zoom` 是同一幀裁切放大。

## 3. 驗收

| 項目 | 結果 |
|---|---|
| `ruff check`、`ruff format --check`、`mypy src tests`、`lint-imports` | 全過（14 contracts kept） |
| pytest `tests/world tests/api tests/content tests/llm tests/narrative tests/server`＋`tests/cli/test_output_snapshots.py`（`-n 4`） | 5381 passed、1 skipped（開發模式不檢查的那項） |
| `trpg battle --map bandit_lair --seed 7 --log-json` → `trpg battle replay` | 通過（109 動作、390 事件） |
| vitest 全量、`tsc --noEmit`、`pnpm build` | 全過 |
| 排版煙霧檢查（`__layoutSmoke.runCase`，1600×900、1040×624、800×600） | 三個情況全 PASS |
| 6.5.1 浮動卡實測（建角種族卡：滑進卡片 → 捲到底 → 點擊釘住 → Esc 關閉；1600、800） | 兩個寬度都正常；建角頁 800 寬沒有水平捲動。本段沒有新增浮動卡（外觀選單是按鈕列，「改外觀」按鈕有 `aria-expanded`） |
| 離線評估 | 沒有可用的真 LLM；以 `MockLLMClient` 測試確認 `<player>` 區塊、NPC `address` 與稱謂規則都在送出的訊息裡，模型關閉時降級模板正確代入 `{name}`／`{address}` |

## 4. 待 PM 決定

1. **一般敵人依 id 挑外觀（#137 第 4 點）沒做**：現有部件只能變膚色、髮色與 4 種髮型，且敵人範本都沒有 `race`、`doll` 已寫滿；改了會動到所有戰鬥快照。建議併進 QK-6（Q 版畫好臉型、新髮型、鬍子之後再一起做）。
2. **畫面先用現有部件**（玩法 PM「外觀選單先用現有部件可以」）：臉型、眼睛、睫毛、體型、獸耳花色（貓／狼／兔）都照存但還畫不出來；新髮型先畫最接近的（齊肩、馬尾、雙馬尾 → 長髮，刺蝟 → 短髮）；鬍子只有「大鬍子」畫得出來（鬍渣、八字鬍、山羊鬍先不畫）。選單下方有一行說明。QK-6 照 `DollLook.custom` 補畫即可，資料不用再改。
3. **稱謂的「或叫名字」**：09 寫「雲嶺一般人『這位』或叫名字」等；表裡只放區域稱呼，「或叫名字」交給說書人（資料區同時有名字與稱謂）。晶冠、樞市、海境設計文件沒寫，先叫名字；傭兵與其他具名 NPC 沒有覆寫的照區域稱呼。
4. **建角 800 寬**：預覽框疊在步驟上方（原本版面），外觀選單在下面，點選時看不到預覽。要不要讓預覽在窄版跟著捲動，請美術 PM 看截圖決定。
5. **模板佔位符 `{name}` 換了意思**：`narration.yaml` 原本 `{name}`＝聊天的 NPC，照 09 改成玩家名字、NPC 改 `{npc}`。`content/ui/narration_wait.yaml`（等待中的字）與 `season.yaml` 編年史的 `{name}` 仍是各自原本的意思（不是玩家），沒動。
6. **「他／她」掃描範圍**：大世界文字（`content/world`、`content/llm`、`content/ui`、`races.yaml`、`origins.yaml`）與伺服器端字串。技能文字（`content/skills`、原語、工坊說明、戰鬥 UI 的「替他承受」）指技能目標單位，不在範圍、沒改。
7. **玩家名字進 LLM**：名字是玩家輸入，放在 `<player>`（跳脫、建角時限長），不是 `<player_input>`；系統指令已寫明它只是資料。若要求一律包在 `<player_input>` 請告知。
8. **真模型評估**：這台沒有 LLM，`storyteller/4`、`situation-check/3` 要在有本機模型時重跑一次評估（`eval_style.py` 的對白檢查）。
9. **獸躍弧線**：平地 3 格的低弧起伏不大（沿用 6N-8 的跳躍弧度，不是高低差攀跳那種大弧）；要看明顯的弧要拍跳上崖台的情況。
10. **6R-1 的免費換種族在 HUD 版面原本找不到**（只在舊版側欄）：本段順手放進「成長」面板的「外觀與種族」區，請確認位置可以。

## 5. 程序

伺服器（8128）與無頭 Chrome（9333～9338）都是自己啟動，已用自己的 PID 結束。沒有 push、沒有 rebase。
