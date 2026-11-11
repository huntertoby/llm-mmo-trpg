# Phase PR-2｜#147 靶場測試模式：接線（PR-2a 後端、PR-2b 前端、PR-2c 木樁與場景畫法）

> 來源：`docs/design/21-探索地圖與城鎮.md` 21.5「工坊靶場」與「測試模式」6 點、#150 第 9 點「靶場入口」（**規則以它為準**）；`docs/玩法決定紀錄.md` #147。
> 畫面：`docs/art/OB與PR移植需求.md` 第 2 節 PR-2、第 3 節、第 4 節第 7～11 項（**畫面以它與 `docs/art/OB與PR樣張.md` 第 2.1、3、4、6 節為準**）；木樁、滑軌、水池見 `docs/art/靶場移植需求.md` 第 2 節。
> 文字：玩法 PM 定稿 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_c2d54362-e4f7-4f75-b1dd-07933f64c2aa\台詞-OB5與PR2定稿.md`（「補定」與「OB-5b 後補定」兩節優先，其次「工坊師傅（PR-2）」「測試模式戰鬥（PR-2）」兩表）。
> 前置（都已在 main）：`docs/phases/PhasePR-1報告.md`（第 7 節是給本段的介面）、`PhasePR-1b報告.md`。盤點：`...\local_1dc515fa-6fa4-4841-956e-bdff26ae2844\盤點-150與147.md` 第 3.2 節。
> 上手筆記：2a 先讀 `docs/dev/上手-roguelite開局與入門期.md`；2b、2c 先讀 `docs/dev/上手-前端戰鬥畫面與動畫.md`。

## 第 1～10 點已定（2026-11-12；本節取代下表的預設）

規則以 `docs/design/21-探索地圖與城鎮.md` 21.5 第 9 點「PR-2 補充」與測試模式第 7 點為準；字串以共用筆記 `台詞-OB5與PR2定稿.md`「PR-2 字串」表為準（逐字照用）。

- **第 1 點（開發 PM）**：切三段 2a／2b／2c。順序：2a → 2b、2c（2b 與 2c 可平行）；**PR-2 整體排在 OB-6a 合併之後**（共用 `world_range.py`、`newcomer.yaml`、`WorldScreen.tsx`）。
- **P2（玩法，照預設）**：入門期也能用靶場試玩；選大類階段不行。
- **P3（玩法，照預設）**：能正式選定時點工坊師傅開選定整頁，其他時候開師傅選單。
- **P4（玩法，改字）**：主城「靶場」物件說明卡換成定稿句；點了照舊開說明卡。
- **P5（玩法，照預設）**：「重新顯示提示」清旗標後「新」小牌再出現，可以。
- **P6（玩法，照預設要擋）**：戰鬥中或有遭遇、待選閃現或三選一、選大類階段都擋，原因句三句見定稿表。
- **P7（玩法）**：戰鬥標題「靶場試玩：{武器}」；離開鈕「離開靶場」只用在師傅入口，開局試打維持原字。
- **第 8 點（美術，照預設）**：木樁新外觀與閃白在技能工坊（3F）一起換。
- **第 9 點（美術、玩法，照預設）**：不改地圖，照現行 `training_range.yaml`（12×10、L 形水面）畫；水面方角、填滿到石緣（L 形內角也方角），滑軌照樣張畫法畫在現有位置。美術驗收看畫法一致，不看格數。
- **第 10 點**：模型一律 Opus 5.5 並往下傳；PR-1 待決 4～9、PR-1b 待決 1～6 全部照實作（玩法 PM 補寫於 21.5 測試模式第 7 點）。

## 待開發 PM 確認（原表；已由上一節取代，保留供查出處）

| # | 問題 | 出處 | 預設（最保守） |
|---|---|---|---|
| 1 | 是否接受切成 **三段**（多一段 PR-2c 木樁與場景畫法）。理由：木樁在戰鬥畫面還是預設人形（`PhaseTR-1報告.md` 待決 5），滑軌、方角水池、閃白都要改 `client/src/render/`，和 2b 的 HUD 檔不重疊；併進 2b 會超過一段的量 | 移植需求第 2 節 PR-2 第 2 點、第 4 節第 9 項；本規格「切段」 | 切三段；不接受時 2c 的交付併進 2b，2b 的量會超標 |
| 2 | 入門期（`stage=starter`）在主城能不能用工坊師傅的「靶場試玩」（試入門武器＋入門招）。21.5 寫「出發後在主城工坊師傅加一項」，「出發」＝確定出發，但「之後回靶場試的是自己的技能與裝備」又像指開局完成後 | 21.5 第 9 點「靶場入口」、工坊靶場段倒數第 2 條 | 開放（`starter`、`chosen`、開局已結束都可；`pick_class` 不可） |
| 3 | 工坊師傅同時是 `range.choose_objects`（OB-5：可以正式選定時點它＝開正式選定整頁）。可以正式選定時點師傅，開選定整頁還是師傅選單 | `content/world/newcomer.yaml` `choose_objects`；`client/src/screens/WorldScreen.tsx` `interactHud`；定稿沒寫 | 照 OB-5：可以正式選定時開選定整頁，其餘時候開師傅選單 |
| 4 | 主城「靶場」物件（`training_range`）的說明卡仍寫「靶場試玩與改造技能還沒開放」。要不要改成也開師傅選單、或改字（定稿沒有這句的新字） | `content/world/fields/capital/capital.yaml` | 不動，寫進報告的暫定字串清單 |
| 5 | 「新」小牌的旗標記在 `hints_seen`，設定裡的「重新顯示提示」（`hints_reset`）會清掉它，小牌會再出現 | `src/trpg/world/step.py::_hints_reset`；定稿補定第 3 點 | 接受（不另加例外；OB-5b「重新顯示提示」那一點在 OB-6 一起看） |
| 6 | 開「靶場試玩」要不要擋：有待選的閃現或三選一、身上有未打的遭遇 | 盤點 3.2「出發後回靶場」建議擋；21.5 沒寫 | 擋（戰鬥中、有遭遇、有待選閃現、有待選三選一），原因句列進暫定字串 |
| 7 | 定稿沒有的字：工坊師傅入口那場的戰鬥標題（樣張的「靶場試打：弓＋…」不能照抄，移植需求第 3 節）、離開鈕的字（美術答覆第 16 項寫「離開靶場」）、不能開的原因句 | 定稿「測試模式戰鬥」表、移植需求第 1 節表第 16 項 | 標題「靶場試玩」、離開鈕「離開靶場」（只用在工坊師傅入口；開局試打維持「回到靶場」）；原因句暫定並列表 |
| 8 | 木樁的新外觀也會出現在技能工坊（3F）的試玩，因為兩邊用同一個單位範本 `training_dummy` | `content/workshop.yaml`；`content/units/training_dummy*.yaml` | 照畫（不分兩種），報告註明 |
| 9 | 樣張的靶場是 12×8、上排磚牆、2×2 水池、上方滑軌；現行 `content/maps/training_range.yaml` 是 12×10、水面 3 格（L 形），而且和技能工坊共用（`tests/content/test_training_range.py` 鎖著） | 移植需求第 2 節 PR-2 第 2 點；`靶場移植需求.md` 第 2 節 | 2c **不改地圖與內容**：水池畫法只對測試模式戰鬥的水面生效，滑軌畫在會動木樁那一排；要改地圖先回報 |
| 10 | 前段待決：PR-1 待決 4～9、PR-1b 待決 1～6（補血與充能不發事件、免死先於不倒下、跑步累加、反應次數不補…）未見 PM 回覆；另交接 3.000 第 2 點寫 agent 一律 Fable 5.2、本規格依派工指示寫 Opus 5.5；PR-1 計畫寫「PR-2 排在 OB-6 之後」、交接 3.000 第 3 點把 PR-2 排在 OB-6 前（兩者共用 `world_range.py`、`newcomer.yaml`、`WorldScreen.tsx`，不可平行） | 兩份報告第 8／5 節；交接 3.000 | 引擎行為不動；模型照本規格；PR-2 與 OB-6 不平行 |

## PM 決定（不要再問）

| 項目 | 決定 | 出處 |
|---|---|---|
| 地名 | 標示所在地點的牌子（地名牌、頁首、標題牌、戰鬥右上「{主城地名}・工坊靶場」、師傅身分行「{主城地名}工坊・靶場與改造」）讀內容檔的主城地名（`trpg.world.common.capital_name`，目前「樞島」）。`CAPITAL_NAME_ZH` 不改；「主城」當通稱的句子不改 | 定稿「補定」1、「OB-5b 後補定」第 1 列（玩法 PM 回覆 OB-5b 第 (a) 點） |
| 師傅台詞 | 守印人「出發後回靶場」那句不用；用工坊師傅的「木樁隨你打，打壞了我再釘。試試你現在的本事。」 | 定稿七項第 5、「工坊師傅（PR-2）」表 |
| 提示句 | 測試模式把「敵人」寫成「木樁」，寫「目標」的不動；實戰不變 | 定稿七項第 7、「測試模式戰鬥」表 |
| 「新」小牌 | 該角色第一次點開「靶場試玩」後消失；旗標記在 `hints_seen`（不加存檔欄位） | 定稿補定 3；上手筆記「提示旗標」 |
| 手機寬戰鬥版面 | 不做（`practice-390*.png` 只是提案） | 移植需求第 1 節使用者第 4 點 |
| 回合操作靠底／靠上 | 照樣張靠底；要改成靠上，**先問美術 PM**，不自行決定 | 移植需求第 3 節第 2 點 |
| 測試模式畫面 | 輪數留、不寫冷卻、拿掉「結束回合」後回合操作自然收合不留空格、離開只用右上既有離開鈕 | 移植需求第 1 節表第 14～16 項 |
| 引擎規則 | 21.5 測試模式第 6 點已涵蓋 PR-1 待決 1～3、9（AP 補到 4、灌注／充能／指揮算放招、主角進致命地形回位、裝備充能補滿），PR-1b 已做完；本段**不改引擎規則** | 21.5；`PhasePR-1b報告.md` |
| 範圍說明 | OB-5b 其餘三點（雇用句、「重新顯示提示」、配點教學句）放 OB-6，不在本規格 | 交接 3.000 第 3 點第 3 項 |

## 目標

1. 工坊靶場的每一場試打（選大類、葛蘭／主城的正式選定與重選畫面、工坊師傅的「靶場試玩」）都用 #147 測試模式開（`practice=PracticeRules()`、`max_rounds=None`），畫面知道自己在測試模式。
2. 主城工坊師傅有選單，「靶場試玩」用角色**自己的技能與裝備**打木樁；不回寫世界、不耗資源。
3. 測試模式的戰鬥版面照樣張；實戰畫面一個像素都不變。

## 範圍外

- 引擎規則（`src/trpg/engine/` 除了 `view.py` 加一個欄位以外都不動）、`LOG_FORMAT`。
- 手機寬戰鬥版面；回合操作改靠上（要改先問美術 PM）。
- 「改造技能」（選單第 2 項只顯示停用「之後開放」）。
- 靶場試打的戰鬥在重新整理後接回（現行試打也不接回；關掉頁面就丟）。
- `BattleSession.history()` 每次從頭重播的效能（只做「一角色一場、離開就刪」，見 2a 第 4 項；長時間單場的耗時量測寫進報告）。
- OB-6 的項目（重選確認彈窗、任務欄小牌、入門武器卡片文字、小模擬）與 OB-5b 其餘三點。
- 技能工坊（3F，`/api/battles` 帶 `training_range` 地圖）**不帶**測試模式旗標，行為不變。

## 工作環境（三段共用）

- Windows；Python 一律 `uv run python`（直接打 `python` 是商店空殼）；前端 `corepack pnpm -C client …`。新 worktree 第一次先 `uv sync --frozen` 與 `corepack pnpm -C client install --frozen-lockfile --offline`，之後指令加 `UV_NO_SYNC=1`。
- 預覽埠：2a 不需要；**2b 用 5230～5234、8111～8113；2c 用 5235～5239、8114～8115**。不用 8000、8001、5195。vite 的 `/api` 寫死轉 8000：要接自己的 `trpg serve` 就另寫暫存 vite 設定檔，不改 `client/vite.config.ts`。存檔目錄 `TRPG_SAVE_DIR` 指到暫存區。
- 瀏覽器測試網址一律加 `?mute=1`；無頭 Chrome 加 `--mute-audio`。交件前用**自己記下的 PID** 關掉伺服器、vite 與所有無頭 Chrome，確認沒有殘留；不用 `taskkill /IM`、`pkill`。
- 等背景程序靠完成通知，**不寫 until／while 輪詢迴圈**。
- 再開子 agent 一律指定 Opus 5.5（`model: "opus"`），並在 prompt 寫明往下也一樣。
- 不跑 `scripts/check.py`、不跑模擬；pytest 平行最多 `-n 8`；每個交付項目一個 commit；不 push。

## 切段與順序

| 段 | 內容 | 依賴 | 可平行 |
|---|---|---|---|
| **PR-2a 後端接線** | `world/`、`api/`、`engine/view.py` 一個欄位、內容檔、API 測試、`gen:api` | 無 | 可和 2c 的「看圖準備」平行，但 2c 要用 2a 的型別，建議 2a 合併後再開 2b、2c |
| **PR-2b 前端 HUD 與入口** | 工坊師傅選單、測試模式戰鬥版面、提示句換字、離開與回靶場 | 2a 的 `schema.d.ts` | 和 2c 平行（檔案不重疊，見各段「只改」） |
| **PR-2c 木樁與場景畫法** | 木樁外觀與閃白、滑軌、測試模式的方角水池 | 2a 的 `BattleView.practice` | 和 2b 平行 |

切段理由：盤點確認 `src/trpg/world/`、`src/trpg/api/`、`client/src` 目前**沒有任何地方傳 `practice=` 或讀 `practice`**，`BattleView`（`src/trpg/engine/view.py:546`）也沒有對應欄位（2026-11-12 以 Grep 確認）；前端兩段都要 2a 重產的型別。

## 受影響的既有功能（第 0 步盤點）

| 區域 | 位置 | 改／不改 | 理由 |
|---|---|---|---|
| 引擎規則 | `src/trpg/engine/practice.py`、`turns.py`、`battle.py` 等 | 不改 | PR-1／1b 已完成；接線只傳 `BattleSetup(..., practice=PracticeRules(), max_rounds=None)` |
| 引擎畫面資料 | `src/trpg/engine/view.py` `BattleView` | **改（2a）**：加 `practice: bool = False`（`state.practice is not None`） | PR-1 報告第 7 節；前端靠它切版面。不進 `BattleLog`、不動規則包雜湊 |
| 開局試打 | `src/trpg/world/opening.py::range_trial` | **改（2a）**：帶 `practice`、`max_rounds=None` | 21.5：測試模式只限工坊靶場（開局試打與之後回靶場）；葛蘭與主城的正式選定、重選畫面的「拿起試打」「看示範」走同一個函式，一起變測試模式 |
| 自己的技能與裝備 | `src/trpg/world/battle.py::_hero_spawn` | **改（2a）**：改成公開函式（行為不變）或抽共用部分 | 「靶場試玩」的主角要和實戰同一套技能列（含生成技能、武器混用規則）與裝備（含共鳴） |
| 世界日誌、重播 | `world/step.py`、`save.py` | 不改 | 試打不經過 `world_step`、不寫日誌；「新」小牌用既有的 `hint_seen` 動作。**`WORLD_RULES_VERSION` 不加**（若實作時發現必須改 `world_step` 路徑上的判斷，就照交接 6.6 加一並寫說明） |
| 角色存檔 | `world/state.py` `CharacterState` | 不改 | 旗標放 `hints_seen`；**`CHAR_FORMAT` 不加一**（沒有新欄位、沒有結構變動），`server/season_policy.py` 不用登記 |
| 一輪存檔、`LOG_FORMAT`、`WLOG_FORMAT` | `roguelite/save.py`、`engine/runner.py`、`world/save.py` | 不改 | 都沒碰到 |
| 戰鬥工作階段表 | `src/trpg/api/sessions.py` `SessionStore` | **改（2a）**：加刪除一場的方法 | 沒有輪數上限後，沒刪的沙盒會一直佔記憶體（盤點 3.2「長時間沙盒的隱患」） |
| 世界 API | `api/world_range.py::open_range_trial`、`api/world.py` `WorldStore`、`api/routes/world.py` | **改（2a）**：開新試打先關同角色的舊試打；新端點「靶場試玩」與「離開」 | 一角色一場 |
| 世界畫面資料 | `api/world_schemas.py` `WorldView`、`api/world_range_schemas.py` | **改（2a）**：加工坊師傅選單資料 | 選單三態、「新」小牌、原因句、主城地名都由伺服器給（畫面與規則同一個函式） |
| 主城情境物件 | `content/world/fields/capital/capital.yaml` `workshop_master`、`src/trpg/content/fields.py` `ObjectPanel` | **改（2a）**：`panel: workshop` | 點師傅開面板（沿用 6D-R2 的 `panel` 機制，前端 `objectHud`） |
| 新手內容 | `content/world/newcomer.yaml` `range`、`src/trpg/content/world_newcomer.py` | **改（2a）**：加工坊師傅選單的字（台詞、兩列、面板下說明、身分行）；`range.max_rounds` 保留不用（註明測試模式不用） | 文字讀內容檔 |
| 技能工坊（3F） | `content/workshop.yaml`、`SessionStore.create`、`client/src/ui/workshop/TryoutPanel.tsx` | 不改規則；**外觀會變（2c）** | 不帶旗標，引擎行為不變；木樁畫法共用（待確認第 8 點） |
| 實戰、循環賽重播、賽季 Boss、roguelite 一輪、開發用 Boss 排演 | `world/battle.py::prepare_battle`、`league.py`、`routes/runs.py`、`world_dev.py` | 不改 | 不帶旗標；行為一致測試鎖住 `BattleView.practice == False` |
| 正式選定、重選、選大類流程 | `world/opening_choice.py`、`opening_reselect.py`、`client/src/world/RangeScreen.tsx` | 不改流程 | 只是試打變測試模式；`RangeScreen` 的試打入口不動 |
| 戰鬥短提示 | `api/world_newcomer_view.py::battle_hints`、`WorldScreen` 傳給 `BattleScreen` 的 `hints` | 不改 | 試打（`replay` 模式）本來就不帶短提示 |
| 前端戰鬥 HUD | `ui/BattleTopBar.tsx`、`TurnBar.tsx`、`TurnControls.tsx`、`SkillBar.tsx` `costParts`、`ActionPanel.tsx` `PreviewBox`、`BattleStatusBox.tsx`、`battle/skillTray.ts`、`battle/logGroups.ts`、`screens/BattleScreen.tsx`、`screens/battle/BattleBottomBar.tsx` | **改（2b）**：全部以 `view.practice` 分支 | 實戰分支的輸出要和改前逐字相同（行為一致測試） |
| 世界畫面 | `screens/WorldScreen.tsx`、`world/hud.ts` `HudPanel`、`world/range.ts`、新 `world/WorkshopPanel.tsx` | **改（2b）** | 師傅選單、開「靶場試玩」、離開回主城 |
| 戰場繪製 | `render/unitSprite.ts`、`render/battle/terrainLayer.ts`、`render/battle/vfxLayer.ts`（閃白）、`battle/drawModel.ts` | **改（2c）** | 木樁外觀、滑軌、方角水池只在對應條件下畫 |
| 排版煙霧檢查 | `client/src/dev/layoutSmoke.ts` | 2b 視需要加量測 | 實戰三個情況要照舊 PASS |
| 原始碼掃描 | `client/src/world/range.test.ts`（不准寫死技能 ID、「主城」） | 2b 的新檔加進掃描清單 | 文字讀伺服器 |
| LLM、skillgen、sim、narrative | — | 不改 | 沒有關聯 |
| OpenAPI | `client/openapi.json`、`client/src/api/schema.d.ts` | **重產（2a）** | `tests/api/test_openapi_snapshot.py` 會擋 |

---

## PR-2a｜後端接線

**只改**：`src/trpg/world/opening.py`、`src/trpg/world/battle.py`（只公開主角出場函式）、`src/trpg/engine/view.py`（只加欄位與賦值）、`src/trpg/api/`（`sessions.py`、`world.py`、`world_range.py`、`world_range_schemas.py`、`world_schemas.py`、`world_presenter.py`、`routes/world.py`）、`src/trpg/content/fields.py`、`src/trpg/content/world_newcomer.py`、`content/world/newcomer.yaml`、`content/world/fields/capital/capital.yaml`、`client/openapi.json`、`client/src/api/schema.d.ts`、`tests/`、`docs/dev/上手-roguelite開局與入門期.md`。**不改**其他前端檔。

### 交付項目

1. **`BattleView.practice`**（`src/trpg/engine/view.py`）：`practice: bool = False`，組 view 時填 `state.practice is not None`。跑 `tests/engine` 裡和 view 相關的測試與 `tests/cli/test_output_snapshots.py`；快照若變了，停下來回報（預期不變）。
2. **開局試打帶測試模式**（`world/opening.py::range_trial`）：`BattleSetup(..., practice=PracticeRules(), max_rounds=None)`；`range.max_rounds` 留在內容檔與 schema，說明改成「測試模式不用」。
3. **自己的技能與裝備的試玩**：
   - `world/opening.py` 加 `practice_problem(library, char, *, in_battle: bool, pending_encounter: bool) -> str | None`（或等效簽名；**畫面與端點共用**）：不在主城、`pick_class`、戰鬥中、有遭遇、有待選閃現或三選一 → 中文原因；其他 `None`（待確認第 2、6 點的預設）。
   - `world/opening.py` 加 `own_practice(library, char) -> RangeTrial`：主角用 `world/battle.py` 公開後的出場函式組（技能列含生成技能、`ruleset.with_skills(char.generated_skills)`、裝備含共鳴）；**HP、法力、耐力給滿；不帶腰包道具、不帶誓約、不帶 `next_battle` 狀態**（21.5 測試模式第 6 點）；隊友不上場（只有主角，和開局試打一樣）；木樁照 `range.dummies`；種子只由角色 ID 衍生（和開局種子無關）（`fnv1a64(f"practice|{char.character_id}".encode())`，同一角色每次一樣）；`practice=PracticeRules()`、`max_rounds=None`。
4. **工作階段表與端點**：
   - `SessionStore.discard(battle_id)`（不存在時不報錯）。
   - `WorldStore` 記「角色 → 目前的試打 battle_id」（只在記憶體）。`open_range_trial` 與新的試玩端點開新場前先 `discard` 同角色的舊場。
   - 新端點 `POST /api/world/characters/{id}/range/practice`（無 body）→ `RangeTrialResponse`（`title_zh` 照待確認第 7 點、`demo=False`、`skills_zh`＝主角技能名）；不能開時 422，原因＝`practice_problem` 的字。
   - 新端點 `DELETE /api/world/characters/{id}/range/trial`：刪掉該角色目前的試打（沒有也回 204）。兩個端點都檢查擁有者（照既有 `owner`）。
5. **工坊師傅選單資料**：
   - `content/world/newcomer.yaml` `range.workshop`（schema 在 `world_newcomer.py`）：`title_zh: 工坊・靶場與改造`（伺服器前面加主城地名）、`line`（說話者「工坊師傅」＋定稿那句）、`practice_zh`／`practice_note_zh`（「靶場試玩」／「用你現在的技能與裝備打木樁，不耗任何資源」）、`rework_zh`／`rework_note_zh`（「改造技能」／「之後開放」）、`footer_zh`（「靶場裡技能沒有冷卻，每次出手後自動過一輪，資源立刻補滿。」）。字逐字照定稿。
   - `content/fields.py` `ObjectPanel` 加 `"workshop"`；`capital.yaml` 的 `workshop_master` 加 `panel: workshop`（`note_zh` 保留）。
   - `WorldView.workshop: WorkshopView | None`（在主城且有靶場內容時才有）：`title_zh`、`capital_zh`、`speaker`（頭像取 `workshop_master` 情境物件的 `figure.portrait`，比照 `_keeper`）、`line`、兩列文字、`footer_zh`、`practice_available`、`practice_blocked_zh`、`practice_new`、`seen_id`。
   - 「新」小牌：常數 `PRACTICE_SEEN = "range:practice"`（放 `api/world_newcomer_view.py` 旁，比照 `LESSON_SEEN_PREFIX`）；`practice_new = PRACTICE_SEEN not in char.hints_seen`。前端點「靶場試玩」時送既有的 `hint_seen {ids: [seen_id]}`（2b 做），**後端不加新動作**。
6. **測試**：下面「行為一致測試」的 A 組全部；更新受影響的既有測試（預期：`tests/world/test_opening.py` 的 `range_trial` 相關、`tests/api/test_range_api.py`；斷言只改「多了 `practice`」的部分，不放寬其他斷言，每個改動在報告列出）。
7. **重產型別**：`uv run python scripts/export_openapi.py`、`corepack pnpm -C client gen:api`，兩檔一起 commit；`corepack pnpm -C client typecheck` 要過（前端還沒用新欄位，只確認沒壞）。
8. **上手筆記**：更新 `docs/dev/上手-roguelite開局與入門期.md` 第二節「測試模式（#147）目前的接線狀態」、檔案表（新端點、`WorkshopView`）、提示旗標的 ID 慣例（`range:practice`）。

### 驗收（2a）

- `ruff check`、`ruff format --check`、`uv run mypy`、`lint-imports` 通過；沒有新增複雜度 noqa（有就逐一寫理由）。
- `UV_NO_SYNC=1 uv run pytest -q tests/world/test_opening.py tests/world/test_opening_stages.py tests/api/test_range_api.py tests/api/test_capital_opening_api.py tests/api/test_openapi_snapshot.py tests/api/test_world_api.py tests/test_architecture.py <新測試檔> -n 8` 通過；`tests/engine/test_practice_mode.py` 與 view 相關測試通過；`tests/cli/test_output_snapshots.py` 通過且快照沒變。
- 行為一致測試 A 組全過（測試名寫進報告）。
- 一場重播：`trpg battle --map open_plain --seed 7 --log-json <暫存>/b.json` ＋ `trpg battle replay`；另把一場測試模式試打的 `BattleSession.to_log()` 寫成 JSON 用 `trpg battle replay` 重播一致。
- `WORLD_RULES_VERSION`、`CHAR_FORMAT`、`LOG_FORMAT` 都沒變（`tests/world/test_opening_stages.py::test_versions` 字面值不動）；若有變，報告寫理由。
- `trpg content check` 通過。

---

## PR-2b｜前端 HUD 與入口（依賴 2a）

**只改**：`client/src/screens/WorldScreen.tsx`、`client/src/world/hud.ts`、`client/src/world/range.ts`、新 `client/src/world/WorkshopPanel.tsx`（與其樣式）、`client/src/screens/BattleScreen.tsx`、`client/src/screens/battle/BattleBottomBar.tsx`、`client/src/ui/BattleTopBar.tsx`、`TurnBar.tsx`、`TurnControls.tsx`、`SkillBar.tsx`、`ActionPanel.tsx`、`BattleStatusBox.tsx`、`TestModeBadge.tsx`（只重用，必要時加 class）、`client/src/battle/skillTray.ts`、`client/src/battle/logGroups.ts`、`client/src/api/client.ts`、`client/src/styles/*.css`、`client/src/dev/layoutSmoke.ts`、對應的 `*.test.ts`、`docs/art/shots/pr2/`、`docs/dev/上手-前端戰鬥畫面與動畫.md`。**不改** `client/src/render/`、`battle/drawModel.ts`（2c 的檔）與任何後端檔。

### 交付項目

1. **工坊師傅選單**（樣張第 2.1 節、第 6 節表「工坊師傅選單」列）：`objectHud` 的 `panel: "workshop"` 開新面板（`world-hud-panel` 寬 520；標頭 `mail-head` 寫 `WorkshopView.title_zh`；標頭下一行師傅台詞與頭像；兩列選單一般／滑過／停用三態，停用列只寫一次「之後開放」；第 1 列 `practice_new` 時掛「新」小牌；面板下一行 `footer_zh`）。不能開時第 1 列停用並用 `<Hint>` 說原因（`practice_blocked_zh`）。待確認第 3 點：可以正式選定時點師傅照 OB-5 開選定整頁。
2. **開「靶場試玩」**：先送 `hint_seen {ids: [seen_id]}`（`practice_new` 時），再呼叫 `POST …/range/practice`，用 `rangeFight` 同一套進戰鬥：`placeName`＝「{`WorkshopView.capital_zh`}・工坊靶場」（`rangePlaceName` 改成吃這個值；開局試打照舊吃 `opening.capital_zh`）、`exitLabel`＝「離開靶場」、開場訊息＝標題＋`SANDBOX_NOTE`。離開時呼叫 `DELETE …/range/trial` 再回主城實地圖（師傅選單關著）。開局試打的「回到靶場」也在離開時呼叫 `DELETE`。
3. **測試模式戰鬥版面**（`view.practice` 為真時；樣張第 3 節、第 6 節表「測試模式」列）：
   - 上方中央不放 `TurnBar`，改放提示條（`TestModeBadge`＋「每次出手後自動過一輪，資源立刻補滿，木樁不會倒」）。
   - `TurnControls` 不放「結束回合」，也不補別的按鈕；回合操作那塊自然收合、**靠底**（要改靠上先問美術 PM）。
   - `BattleStatusBox`：勝利條件換成「沙盒・不算勝負」小牌；輪數照舊顯示（沒有上限）。
   - `PreviewBox`：照引擎給的 100%；多一行淡金色「靶場木樁必中，實戰會有失手」；「命中」「暴擊」「傷害」三段各自 `white-space: nowrap`（「傷害 3–10」不拆開）。
   - `SkillBar` `costParts`：測試模式不寫冷卻。
   - 提示句：`battle/skillTray.ts` 等前端自寫的操作提示句，測試模式把「敵人」寫成「木樁」、「目標」不動（例：「點選藍色格子移動（{n} 格），點選紅框木樁攻擊（{m} 個）；右鍵或 Esc 取消選取。」）。做法：加純函式（例 `practiceWording(text, practice)`）或在產生句子的函式多一個參數，**實戰分支的輸出逐字不變**。範圍只限操作提示句（技能列上方那行、選了模式的提示、指揮召喚物等前端自寫的提示）；伺服器給的技能說明不改。
   - 戰鬥紀錄：每輪結束多一行「第 {n} 輪結束：木樁補滿」（`battle/logGroups.ts`，只在測試模式）。
4. **排版煙霧檢查**：實戰的 `runCase` 三個情況（1600×900、1040×624、800×600）全 PASS；若測試模式版面有新元件（提示條、小牌），把量測加進 `layoutSmoke.ts` 的 `HUD_SELECTORS`。
5. **測試**：行為一致測試 B 組；`client/src/world/range.test.ts` 的原始碼掃描清單加進 `WorkshopPanel.tsx`。
6. **截圖**（`docs/art/shots/pr2/`，與 2c 合計 ≤ 10 張、jpg 品質 80、單張 ≤ 300 KB）：本段最多 8 張，對應移植需求第 4 節第 7、8、10、11 項（見下方驗收）。
7. **上手筆記**：更新 `docs/dev/上手-前端戰鬥畫面與動畫.md`（測試模式的分支點、`view.practice`、工坊師傅面板）。

### 驗收（2b）

- `corepack pnpm -C client typecheck`、`corepack pnpm -C client test`、在 `client` 內 `npx vite build`，**三個結束碼分開記進報告，全部 0**。
- 行為一致測試 B 組全過。
- 移植需求第 4 節（每項都要截圖；只有 vitest 的不算通過）：
  - **第 7 項**：工坊師傅選單 1280 與 390 寬，一般、滑過各一張（4 張）；場景裡師傅的護目鏡、鬍子、皮圍裙、平頭鎚看得到；「新」小牌出現；檔名 `pr2b_7_master_1280_normal.jpg` 這類。另用文字記錄：點過一次「靶場試玩」、回來後小牌消失（重新整理後仍消失）。
  - **第 8 項**：測試模式 1280×720 普攻狀態一張、移動狀態（有藍格）一張；看得到「沒有回合列、沒有結束回合、提示句寫木樁、預覽 100%」。
  - **第 10 項**：和現行戰鬥版面並排一張（同一張圖左右兩半；左邊是一般實戰，證明實戰沒被改到）。
  - **第 11 項**：實機一張以上：用自己啟動的伺服器建角，走到主城工坊師傅 → 靶場試玩 → 放招、普攻 → 離開靶場回主城（可用開發入口加速，報告寫明怎麼到的）。
- 浮動卡實測（6.5.1）：在測試模式戰鬥裡挑一張可滑進的卡（例技能列的技能卡）做「從觸發元素滑進卡片 → 卡內捲到底 → 釘住 → 關閉」，**1600×900 與 800×600** 各一次，結果寫進報告；師傅選單第 1 列停用時的 `<Hint>` 也照做一次。
- `window.__layoutSmoke`：`localStorage.clear()` → `/?dev=1&anim=0.1&mute=1` → `await window.__layoutSmoke.runCase("PR-2b")`，**1600×900、1040×624、800×600 三個情況全 PASS**，表格貼進報告。
- 截圖前自己看一遍（字溢出、壓線、和 `docs/art/shots/ob/practice-1280*.png`、`entry-master-*.png` 並排對得上）；實機到不了的用開發頁畫並在報告列「實機未看」。

---

## PR-2c｜木樁與場景畫法（依賴 2a 的 `BattleView.practice`；和 2b 平行）

**只改**：`client/src/render/unitSprite.ts`（與需要的新檔，例 `render/trainingDummy.ts`）、`client/src/render/battle/terrainLayer.ts`、`client/src/render/battle/vfxLayer.ts`（或受擊所在的層）、`client/src/battle/drawModel.ts`、`client/src/dev/` 下一個開發頁（可新增 `practice-gallery`）、對應測試、`docs/art/shots/pr2/`、`docs/dev/上手-前端戰鬥畫面與動畫.md`。**不改** 2b 列的檔、後端、`content/`。

### 交付項目

1. **木樁外觀**：模板 `training_dummy`／`training_dummy_moving`（`UnitView.template_id`）畫成底座、木樁、橫臂、麻布身、布頭；不畫血條；照 `docs/art/OB與PR樣張.md` 第 4 節與 `靶場移植需求.md` 第 2 節。被打中閃白 0.1 秒（減少動態時改成不閃或一格）。
2. **滑軌**：會動的木樁那一排畫兩條墨線鐵軌加枕木（只是外觀，不影響規則；只在 `view.practice` 時畫）。
3. **水池**：`view.practice` 時水面畫成方角、整片填滿到石緣、外圈方角石條，格縫十字線不畫；**實戰與技能工坊的水面畫法不變**。
4. 地圖與內容不改（待確認第 9 點）；若不改地圖做不出樣張的效果，停下來回報。
5. **測試**：行為一致測試 C 組；`render/__snapshots__` 若變了在報告逐項說明。
6. **截圖**：本段最多 2 張（第 9 項：三種木樁的特寫合成一張、被打閃白一張），放 `docs/art/shots/pr2/`。

### 驗收（2c）

- `typecheck`、`test`、`npx vite build` 三個結束碼都 0（分開記）；雜湊快照測試（`render/creaturePose.test.ts`、`render/inkDollSnapshot.test.ts`）照舊通過。
- 移植需求第 4 節**第 9 項**截圖齊全；和 `docs/art/closeup/ob/practice-board-dummies-3x.png`、`practice-pool-4x.png` 並排對得上。
- 實戰一場（`/?dev=1` 單場戰鬥）截一張確認水面與單位畫法沒變（可和 2b 第 10 項共用，不另算張數時在報告註明）。

---

## 行為一致測試（實際打 API 或跑引擎的表格測試；不只測資料）

**A 組（2a，pytest；用固定世界種子與角色 ID，不依賴 `secrets`）**

| # | 情境 | 怎麼跑 | 斷言 |
|---|---|---|---|
| A1 | 試打不回寫世界 | 三種入口（選大類 `range/trial`、正式選定畫面 `range/trial`、`range/practice`）各開一場，透過 `/api/battles/{id}/actions` 放招、普攻、走路共 5 個動作 | 角色存檔（`dumps_char`）、世界快照、`log.jsonl` 行數、經驗、背包、`next_battle` 全部和開打前相同；`GET …/characters/{id}` 的 `battle_id` 為 `None` |
| A2 | 只有靶場是測試模式 | 參數化：三種靶場入口 vs 世界遭遇戰（`POST …/battle`）、技能工坊（`POST /api/battles` 帶 `training_range`）、roguelite 一輪的戰鬥、循環賽重播 | 靶場三種 `view.practice is True`、`view.max_rounds is None`；其他全部 `False` 且 `max_rounds` 照原值 |
| A3 | 測試模式規則真的經過 API 生效 | 在 `range/practice` 那場：放一招有冷卻的技能；普攻一次；走路一次；對木樁 `POST …/preview` | 放招後冷卻為 0、主角 HP／AP／法力為滿；普攻後 `view.round` +1、回應裡沒有 `end_turn` 步驟；走路後輪數不變；預覽命中 100% |
| A4 | 自己的技能與裝備 | 帶生成技能、穿裝備、腰包有道具、有誓約、`next_battle` 有狀態的角色開 `range/practice` | 主角技能列＝實戰出場函式的技能列（不含腰包道具）；裝備＝`hero_loadout`；沒有誓約、沒有 `next_battle` 狀態；開完後角色的 `next_battle` 沒被消耗 |
| A5 | 能不能開（畫面與端點同一個函式） | 參數化：開局已結束在主城、`starter` 在主城、`chosen` 在主城、`pick_class`、在霧渡鎮、戰鬥中、有遭遇、有待選閃現、有待選三選一 | `WorldView.workshop.practice_available` 與端點成功／422 一致；422 的字＝`practice_blocked_zh`；不在主城時 `workshop is None` |
| A6 | 「新」小牌 | 新角色 → 送 `hint_seen {ids: [seen_id]}` → 送 `hints_reset` | `practice_new` 依序為 `True`、`False`、`True`；送 `hint_seen` 前後世界日誌多一筆（既有動作），`WORLD_RULES_VERSION` 不變 |
| A7 | 一角色一場 | 同角色連開兩次試打；再 `DELETE …/range/trial` | 第一場 `GET /api/battles/{id}` 變 404；刪除後第二場也 404；`len(store.battles)` 不增加；別的角色的試打不受影響；別人的帳號刪不到 |
| A8 | 技能工坊不受影響 | `POST /api/battles` 開 `training_range`，放一招 | 冷卻照常、需要 `end_turn` 才換輪（和改前相同） |
| A9 | 重播 | 測試模式試打 5 個動作後 `to_log()` → JSON → `replay` | 事件與最終狀態逐筆相同 |
| A10 | 地名與文字 | 讀 `WorldView.workshop` | `title_zh == f"{capital_name(library)}工坊・靶場與改造"`；台詞、兩列、面板下說明和定稿逐字相同（測試裡寫定稿原字） |

**B 組（2b，vitest；純函式表格測試）**

| # | 函式 | 斷言 |
|---|---|---|
| B1 | 提示句（`actionHintText`、`modeBarHint` 等前端自寫的句子） | 每一種提示：`practice=false` 的輸出和改前**逐字相同**（把改前的句子寫進測試表）；`practice=true` 時「敵人」→「木樁」、「目標」不變 |
| B2 | `costParts` | 有冷卻的技能：實戰有「冷卻 N 回合」、測試模式沒有；其他代價兩邊相同 |
| B3 | 回合操作 | 實戰有「結束回合」，測試模式沒有、也沒有補上別的按鈕 |
| B4 | 狀態盒、頂部 | 測試模式顯示「沙盒・不算勝負」與提示條、不顯示 `TurnBar`；實戰相反 |
| B5 | 戰鬥紀錄 | 測試模式輪數 +1 時多一行「第 {n} 輪結束：木樁補滿」；實戰沒有 |
| B6 | 師傅選單 | `practice_new` 時有「新」小牌；停用時第 1 列停用並帶原因；第 2 列永遠停用、只寫一次「之後開放」 |
| B7 | 地名 | `rangePlaceName` 吃 `WorkshopView.capital_zh`；新檔原始碼不出現「主城」字面與技能 ID（`range.test.ts` 掃描） |

**C 組（2c，vitest）**

| # | 函式 | 斷言 |
|---|---|---|
| C1 | 單位畫法的選擇 | `template_id` 是兩種木樁 → 木樁畫法、沒有血條；其他模板照舊 |
| C2 | 水池與滑軌 | `practice=false` 的 `DrawModel`（或畫法描述）和改前相同；`practice=true` 才有方角水池與滑軌 |
| C3 | 閃白 | 木樁受擊產生 0.1 秒閃白；減少動態時照第 1 項的規則 |

## 報告格式

- 檔名：`docs/phases/PhasePR-2a報告.md`、`docs/phases/PhasePR-2b報告.md`、`docs/phases/PhasePR-2c報告.md`（若待確認第 1 點不切 2c，2c 的內容寫進 2b 報告）。
- 內容：做了什麼（對應交付編號）、逐條驗收（測試名稱或指令輸出為證）、和規格不同的地方與理由、更動的既有測試清單（2a）、版號是否變動與理由（2a：`WORLD_RULES_VERSION`、`CHAR_FORMAT`、`LOG_FORMAT`）、新增的複雜度 noqa 與理由、截圖檔名對照表（完整路徑 `docs/art/shots/pr2/<檔名>`）、浮動卡與 `__layoutSmoke` 結果（2b）、「實機未看」清單、暫定字串清單（位置、現在的字、出現時機）。
- **「待 PM 決定」最多 10 點**。
- **改到的區域順手更新對應上手筆記**（2a：`docs/dev/上手-roguelite開局與入門期.md`；2b、2c：`docs/dev/上手-前端戰鬥畫面與動畫.md`），在報告寫更新了哪幾節。
- 每段以一個實作 agent 約 30 分鐘、25 萬 token 做得完為上限；做不完時先 commit 已完成的交付項目，報告寫明停在哪。
