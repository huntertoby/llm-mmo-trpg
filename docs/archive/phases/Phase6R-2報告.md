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

---

## 6R-2b：驗收後的修正與補拍

> 實作者：worktree `dev/6r2b`（從 main `78647b0d` 開）。沒有 push、沒有 rebase。來源：玩法 PM、美術 PM、專案 PM 11-06 的決定。

### 1. 完成表

| # | 做什麼 | 結果 | commit |
|---|---|---|---|
| 1 | 稱謂補三區 | `address.yaml` 加 `crystal_crown: 閣下`、`arcane_hub: 這位訪客`、`frost_tide: 外地來的`，檔頭註解改寫（三區還沒有大世界地圖，先放稱呼）。測試：查表三區、沒寫到的區叫名字、模型關閉時降級模板用該區稱呼 | `ce846dfd` |
| 2 | 玩家名字包進 `<player_input>` | `<player>` 區塊改成「`<player_input>名字</player_input>`＋`{"address":…}`」（`trpg.llm.prompts.escape.player_block`，名字跳脫、截到 12 字＝建角上限，測試檢查兩者一致）。稱謂若就是名字（叫名字），資料區寫 `{name}`，`<npcs>` 的 `address` 同樣處理，名字不出 `<player_input>`。系統指令同步：稱謂句改成「<player> 裡 <player_input> 的文字」「{name} 代表叫名字」；安全規則寫明每一段 `<player_input>` 都是資料（<player> 裡的是名字、最後一段是玩家說的話）；聊天任務、情境判定的「玩家的回答」改稱「最後一段 <player_input>」。版號 `storyteller/5`、`situation-check/4`（快照雜湊已登記）。新測試：名字（含注入字串、超長）只出現在 `<player_input>` 內、被跳脫截斷 | `064c2cf1` |
| 3 | 真模型煙霧測試 | `tests/llm/test_neutral_address_real_model.py`（`-m llm`）：說書人 event 2、chat 2（渡婆婆叫名字、青崖道長「施主」）、情境判定 2，主角「青禾」。判斷法寫在檔頭：要是模型輸出（不是降級）；有稱呼到主角（名字、該 NPC／區域稱謂，或對玩家說話的「你」）；「他／她」先去掉「其他、他人、他們…」，剩下的若和主角名字／稱謂同一句就算指稱主角。**順手修的程式問題**：說書人 schema 的 `uniqueItems` 讓 LM Studio（MLX）整個請求 HTTP 400（模型生成到陣列時才報錯，所以時好時壞）、退到 `guided_json` 後約束失效，情境判定跟著出現不在列舉內的值；改成不送 `uniqueItems`（不重複本來就由 pydantic `StoryText` 擋），加測試 | `6c333824` |
| 4 | 800 寬看得到外觀預覽 | 建角頁：外觀選單捲進畫面上半部（IntersectionObserver）時表單加 `entry-look-step`，窄版（< 1040）預覽改成固定在畫面上方、預覽框 120px（隱藏「預覽」標題、名字與摘要，底色不透明），選單在下面捲；捲離外觀步驟恢復原版面（實測捲到武器步驟：class 拿掉、`position: relative`、預覽框回 140px）。主城「成長」→「外觀與種族」窄版：預覽與 4 個方向鈕 `sticky` 在這一區上方（不透明底），選單在下面捲。1600 寬不受影響 | `7a81bb63` |
| 5 | 獸躍補拍（崖台 ▲2） | 鶴歸崖（`crane_cliff`，戰場「懸崖前哨」）用開發入口「頭目戰（開發）」`?boss=crane_cliff&bosslv=6` 開打，獸耳族主角青禾從平地 (2, 4) 高 0 跳上 (4, 4) ▲2；起跳、空中、落地 3 張＋同一幀 zoom，滑鼠移到右側空白處，提示框沒有蓋到崖台。平地 3 格的弧沒改 | `44a8bfe4` |
| 6 | 介面英文「Boss」→「頭目」 | 前端：佈告欄「賽季頭目」、編年史「賽季頭目評分榜」、名片「賽季頭目評分」、開發標題列「頭目戰（開發）」、開新一輪「5 場戰鬥加頭目」、首頁說明、路線按鈕「開始頭目戰／繼續頭目戰」（拿掉原本英文前的空格）、工坊「（頭目地圖）」、傳送落點提示、技能展示頁。伺服器：預覽／目標檢查「X 是頭目」、說明卡（推進致命地形、硬控轉換、勝利條件「頭目戰：…」）、技能說明、佈告「── 賽季頭目 ──」、首殺公告、季末編年史「打倒頭目…」、賽季階段名、NPC 人設卡、音效名、`world_presenter`「頭目據點」、賽季頭目的錯誤訊息、季末重置清單、CLI（`trpg run` 的「頭目・」與「頭目戰」、`--bonus` 說明）。程式識別字、資料欄位、內容 id 沒動；前端 fixtures 重匯出（`glossary.json`）；CLI 快照沒變 | `62b57de8` |

### 2. 截圖（共 10 張，jpg 80，皆 ≤ 300 KB）

- `docs/art/shots/6r2b/6r2b_create_look_800.jpg`：建角 800×600，外觀步驟（獸耳族、雙馬尾、灰髮、貓耳剛點完），預覽固定在上方、看得到換好的灰髮雙馬尾，選單在下面。
- `docs/art/shots/6r2b/6r2b_create_look_1600.jpg`：同樣的選擇 1600×900 對照（原版面，左側預覽）。
- `docs/art/shots/6r2b/6r2b_town_look_800.jpg`：主城「成長」→「外觀與種族」800×600，選單捲到髮色、剛點金棕色，預覽與方向鈕固定在上方。
- `docs/art/shots/6r2b/6r2b_town_look_1600.jpg`：1600×900 對照（原版面）。
- `docs/art/shots/6r1/6r1_leap_cliff_1_takeoff_1600.jpg`＋`_zoom.jpg`、`6r1_leap_cliff_2_air_1600.jpg`＋`_zoom.jpg`、`6r1_leap_cliff_3_landed_1600.jpg`＋`_zoom.jpg`：鶴歸崖平地跳上 ▲2（`?anim=0.1`＋「極慢」連拍，`_zoom` 是同一幀裁切放大 2 倍）。

截圖方式：worktree 內 `TRPG_DEV_ROUTES=1 trpg serve --port 8130`、無頭 Chrome（CDP 9341，視窗 1600×900／800×600），都用自己的 PID 結束。

### 3. 真模型結果（E4B `gemma-4-small`，LM Studio MLX）

指令：`TRPG_LLM_CONFIG=config/llm.local.toml uv run pytest -q tests/llm -m llm -n 0 --timeout=900`（含舊的 3 個）。修好 `uniqueItems` 後：**9 過、2 失敗，共 83 秒**；只跑新檔再一次：6 過、2 失敗，50 秒，失敗的是同樣兩題。

| 題目 | 秒數 | 結果 |
|---|---|---|
| 舊：`test_real_model_ping`／`propose_one`／`one_upgrade_item` | 1.7／20.2／28.8 | 過 |
| event：迷路道童（霧、白天） | 8.1 | **失敗**：沒有稱呼到主角（「濃霧籠罩著雨中梯田。一位道童站在面前…」只寫場景與 NPC） |
| event：盜賊收過路費（雨、夜） | 6.1 | 過 |
| chat：渡婆婆（叫名字） | 4.2 | **失敗**：沒有稱呼到主角（「霧渡鎮的霧氣較重。」） |
| chat：青崖道長（施主） | 4.0 | 過 |
| 情境判定 ×2 | 4.2／2.9 | 過（通過 pydantic 與靜態檢查） |

- **沒有任何一題用「他」「她」指稱主角**；失敗的兩題都是「整段沒提到主角」（模型品質，不是程式問題），照指示不改 prompt 規則。
- 修正前（`uniqueItems` 還在）同一組跑出 3 題失敗：event 1 題整個請求被拒（HTTP 400）、情境判定 2 題輸出 `care.item` 不在列舉內（client 退到 `guided_json` 後約束失效）。這兩類是程式問題，已修。
- 跑的過程中 LM Studio 兩次把模型卸載（另有人在用同一台 LM Studio？），照 `docs/部署說明.md` 的 `lms load` 指令載回後重跑。

### 4. 驗收

| 項目 | 結果 |
|---|---|
| `ruff check`、`ruff format --check`、`mypy src tests`、`lint-imports` | 全過（14 contracts kept） |
| pytest `tests/world tests/api tests/content tests/llm tests/narrative tests/cli tests/server tests/roguelite`（`-n 4`） | 5606 過、1 跳過；唯一失敗（`test_displace_others` 斷言「Boss」）已改，`tests/engine` 4222 過 |
| `tests/skillgen tests/sim tests/test_architecture.py` | 4127 過、14 跳過 |
| CLI 快照（`UPDATE_CLI_SNAPSHOTS=1`） | 沒有變化 |
| `trpg battle --map bandit_lair --seed 7 --log-json` → `replay` | 通過（109 動作、390 事件） |
| vitest 全量、`tsc --noEmit`、`pnpm build` | 3094 過；typecheck、build 過 |
| 排版煙霧檢查（1600×900、1040×624、800×600） | 三個情況全 PASS |
| 6.5.1 浮動卡 | 本段沒有新增浮動卡（外觀預覽是固定區塊，不是彈出卡） |
| `openapi.json`／`schema.d.ts` | API 沒變，重產沒有差異 |
| 版號 | `storyteller/5`、`situation-check/4`；`WORLD_RULES_VERSION` 沒升（只改文字與前端） |

### 5. 待 PM 決定

1. **真模型 2 題「沒稱呼到主角」**：E4B 的事件開場、渡婆婆短回話常常只寫場景，不提主角。測試照規格要求「用名字或稱謂（或對玩家說的『你』）」，所以會失敗；規則沒改。要不要放寬（例如只檢查「不用他／她」），或改用 12B 再跑，請決定。
2. **獸躍弧線**：懸崖前哨的 ▲2 是中央階梯的第二階（前一格 ▲1），不是北坡那種實地崖台——北坡、鶴歸崖的實地戰場要從實地地圖接觸敵人才切得出來，開發入口只開地點的戰鬥模板。拍到的弧：人物從高 0 一路往上到 ▲2，**沒有高過落點的最高點**（看起來像斜坡滑上去，空中主要靠放大）；另外空中經過 ▲1 那格時，格子的「▲1」高度標籤畫在人物上面（見 `6r1_leap_cliff_2_air_zoom.jpg`）。要不要加大弧度、讓高度標籤在人物移動時讓開，請美術 PM 看圖決定。
3. **建角「在外觀步驟」的判斷**：外觀選單捲進畫面上半部（下緣留 40%）才算；900～1039 寬原本是左右兩欄（左欄預覽本來就 sticky），進外觀步驟時也一起切成單欄＋上方小預覽，與 < 900 一致。
4. **稱謂是名字以外的組合模板**（例如將來寫「{name}大哥」）：目前只在稱謂「等於名字」時改寫成 `{name}`；組合模板會把名字帶出 `<player_input>`。現在內容裡沒有這種稱謂，加的時候要一起改 `address_token`。
5. **「Boss」沒改的地方**：程式註解、docstring、伺服器 log、內容載入檢查的錯誤訊息（開發者看的）、模擬報表（`trpg.sim`）、`server/season_policy.py` 的欄位說明表、`engine/preview.py` 的欄位說明表；OpenAPI 的欄位標題（`Boss`、`Season Boss Zh`）是 pydantic 由欄位名自動產生的，不是介面文字。
6. 說書人 schema 拿掉 `uniqueItems` 沒升提示詞版號（schema 不在 prompt 快照內、不影響重播）。

### 6. 程序

伺服器（8130）、無頭 Chrome（9341）都是自己啟動，已用自己的 PID 結束。`config/llm.local.toml` 從主資料夾複製（gitignored，沒 commit）。

## 6R-1c：跳躍弧度與高度標籤（獸躍驗收退回）

> 實作者：worktree `dev/leap`（從 main `58dc6889` 開）。沒有 push、沒有 rebase。依據：`docs/art/6R-2檢查.md` 第 5 節（美術 PM 11-06 決定）。

### 1. 完成表

| # | 做什麼 | 結果 | commit |
|---|---|---|---|
| 1 | 弧度從較高的一端往上量 | `render/motionClips.ts`：新增 `jumpRise`（＝ 14＋級差×6，往下 ×0.7）、`jumpPeakAir`（＝ rise ＋ 級差的一半；中點的底線在兩端中間，補半個級差，最高點才量在較高的一端上面）。高低差走路的跳躍（`legFrame`，差 2 級以上）改用它。技能跳躍 `leap_air`（獸躍、技能的跳躍原語）新增 `leapAirScale`：起訖有高低差時離地高度取「片段原本的 18 虛擬像素」和 `jumpPeakAir` 的大者，同高時倍率 1（平地的弧不變；高弧、空翻的倍率照舊乘上去）。例：▲0 → ▲2 最高點 ＝ 12＋26 ＝ 38（世界座標，原本 21），▲2 → ▲0 ＝ 12＋18.2 | `f5cd55f7` |
| 2 | 高度標籤在人物底下 | `render/rowLayers.ts`：每排圖層改成「地面、裝飾、under、物件、陷阱、**▲N**、單位、徽章（marks）、上層霧」（原本 ▲N 在單位之上，6F-10）。有人站的格子 6F-18 起本來就不畫 ▲N；這次是飛過、倒地時人物蓋過標籤。單位身上的炸彈、蓄力、灌注徽章照舊在 ▲N 與單位之上 | `f5cd55f7` |
| 3 | **找到的程式問題：獸躍根本沒有弧** | 種族技「獸躍」沒有技能卡的特效，播放計畫不經過 `placeMotions`，位移動畫沒有 `leap_air` 片段，於是走「平移」：人物從起點直線滑到落點、完全不離地（這才是 6R-2b 截圖看起來像滑上階梯的原因，弧度公式其實沒用到）。改成 `moveAnimOf` 遇到 `mode: "leap"` 一律帶 `clip: "leap_air"`（技能的跳躍由 `placeMotions` 換成同一個片段，不受影響） | `1ece0b82` |
| 4 | 補拍 | 見下 | `67c6b4d0` |

伺服器端沒有弧度參數（事件只有 `unit_moved` 的 `mode: "leap"`），沒動 Python。

### 2. 截圖（6 張，jpg 80，最大 188 KB）

鶴歸崖（戰場「懸崖前哨」）開發入口 `?dev=1&boss=crane_cliff&bosslv=6`（請求加 `region=cloud_ridge`），獸耳族主角青禾先走到 (1, 4) 高 0，再獸躍到 (4, 4) ▲2，途中飛過 (2, 4) 的敵人與 (3, 4) ▲1。「極慢」連拍，`_zoom` 是同一幀裁切放大 2 倍。

- `docs/art/shots/6r1/6r1_leap_cliff_v2_1_takeoff_1600.jpg`＋`docs/art/shots/6r1/6r1_leap_cliff_v2_1_takeoff_zoom.jpg`：起跳，身體已離開底圈。
- `docs/art/shots/6r1/6r1_leap_cliff_v2_2_apex_1600.jpg`＋`docs/art/shots/6r1/6r1_leap_cliff_v2_2_apex_zoom.jpg`：最高點在 ▲1 那格上空，腳底明顯高過 ▲2 的地面；「▲1」標籤在護盾泡泡與底圈之下（泡泡的外框畫過標籤）。
- `docs/art/shots/6r1/6r1_leap_cliff_v2_3_landed_1600.jpg`＋`docs/art/shots/6r1/6r1_leap_cliff_v2_3_landed_zoom.jpg`：落在 ▲2。

### 3. 驗收

| 項目 | 結果 |
|---|---|
| vitest 相關（`motionClips`、`animation`、`summonBadges`、`statusBadges`、`src/battle`） | 全過 |
| vitest 全量 | 247 檔、3112 項全過（含 6F-21b） |
| `tsc --noEmit`、`pnpm build` | 過（只有原本的 chunk 大小提醒） |
| 排版煙霧檢查 1600×900、1040×624、800×600 | 三個都 13 PASS、0 FAIL |
| 新測試 | 上跳、下跳各級差：整段最高點 ≥ max(起點, 落點)＋14（逐點掃 200 格）、中點 ＝ 較高一端＋rise；下跳 ＝ 上跳的 0.7 倍；獸躍 `leapAirScale` 同高為 1、跳上 ▲1～▲3 最高點 ≥ 落點＋14、跳下 0.7 倍；`moveAnimOf` 的 leap 帶 `leap_air`；圖層順序 物件、陷阱 < ▲N < 單位 < 徽章、上層霧 |

### 4. 待 PM 決定

1. **沒有骨架的單位（形態、召喚物）獸躍／跳躍仍是平移**：`clipMove` 只對紙娃娃人形換姿勢與離地；現在只有獸耳族主角會獸躍，不影響這次驗收。
2. **弧變高**：▲0 → ▲2 最高點 38（約 0.8 格），照「從較高一端往上 14＋級差×6」；平地獸躍不變（15.3）。若看起來太高，可改成只保證「≥ 較高一端＋14」（▲0 → ▲2 會是 26）。
3. **6F-10 的決定被這次取代**：6F-10 把 ▲N 移到單位之上是為了「站在高台上的人不蓋住 ▲N」；6F-18 起有人站的格子不畫 ▲N，所以這次改回單位之下只影響飛過、倒地的情況。

### 5. 程序

伺服器 `uv run trpg serve --port 8132`（`TRPG_DEV_ROUTES=1`）、無頭 Chrome（CDP 9351、9352）都是自己啟動，已用自己的 PID 結束並確認埠沒有在聽。測試角色「青禾」建在本機開發世界資料（不在 repo）。
