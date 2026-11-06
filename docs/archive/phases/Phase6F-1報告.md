# Phase 6F-1 報告：前 10 分鐘的文字與 bug 修正

> 實作者：implementer agent（2026-11-04）。基準 main `70a6268d`，分支 `worktree-agent-a4dfdbdba645e930d`（沒有 push、沒有合併）。
> 範圍：玩法 PM 筆記第 1.3 節 U5～U10、U16，第 1.2 節 C4、C5；中途追加實機巡檢 bug 1、bug 4（`docs/phases/Phase6實機巡檢.md`）與美術 PM 的頂列三項。
> 前圖用體驗檢查的 `docs/art/first10_*`，後圖是本段的 `docs/art/6f1_*`（無頭 Chrome 1280×800，自己的伺服器 8366）。

## 1. 逐項

| # | 項目 | 做了什麼 | 前 → 後 |
|---|---|---|---|
| 1 | 原始 ID 外露（U6） | 靈感 toast 的來源 `quest:<id>` 改成任務名稱，句尾加「可以在成長面板（G）讓技能閃現」；不認得的來源不再原樣印出。HUD 燈泡改成「靈感點 N：在成長面板（G）讓技能閃現」。全站掃描（首頁、建角、大世界、J／G／I／K／Y／N／R／M 各面板，用正規式找 `snake_case` 與 `kind:id`）另抓到「還有任務給的技能三選一沒有選（offer_pick）」「（flash_pick）」兩句，改成「……沒有選：先選一招或跳過／先選一個」 | `first10_41` → `6f1_08_result`（結算面板第 6 行） |
| 2 | 開發指令外露（U5） | 結束面板的「紀錄可用 uv run trpg battle replay……」只在 `?dev=1` 顯示 | `first10_37` → `6f1_08_result` |
| 3 | 結算畫面（U5） | 大世界戰鬥播完時先同步一次世界（伺服器原本就在這時回寫），用回來的資料組結算：這次的事件句子（經驗、金幣、掉落、任務步驟、靈感、好感度）、「經驗 400／950（Lv 1）」、沒掉落時「戰利品：這場沒有掉落」、事件裡沒有任務句子時補追蹤中的任務進度；打贏時另一行「HP 1／40：HP 要到城鎮或營火才會回。」（在捲動區外，一定看得到）。回到地點圖時沿用這份畫面，toast 不會少。**沒有新 API 欄位**，所以沒跑 export_openapi／gen:api | `first10_37` → `6f1_08_result`、`6f1_09_after_battle` |
| 4 | 同名（C4、C5） | 白板配方加選填欄位 `weapon_name_zh`，武器技版本用它；`frost_shard` 武器版叫「冰錐刺」。`bow_guard` 改名「護衛弓」，並加武器欄位 `enemy_only: true`，開局選單（`/api/runs/start-options`：開始畫面、建角、開新一輪）不列出；隨機開局 `start_weapons()` 與掉落照舊，種子對應不變 | `first10_04` → `6f1_12_create_weapons`（只剩一顆「弓」） |
| 5 | 霜咒卡面（C6 的文字部分） | 元素不改；短描述改成「暗影傷害＋冰凍 1 回合：冰冷的詛咒從腳底爬上來，連逃跑的念頭都凍住」 | `first10_39` |
| 6 | 戰敗回鎮法力（U7） | 見第 3 節。全滅回鎮改成 HP、法力都回滿；事件句改「被抬回霧渡鎮，HP、法力回滿；……」 | — |
| 7 | 白板標籤（U8） | 原因：新手鏈「被動保底」把新方向卡換成被動時，只要換了關鍵字就標成退回，即使換上的是還沒有的關鍵字。改成新方向卡只有在換上「已持有的關鍵字」時才算退回。退回文字也改成「還沒有的關鍵字找不到技能：改給持有最少的」（原本「所有關鍵字都有了」在找不到技能時也會出現，不準） | `first10_38` → `6f1_09_after_battle` |
| 8 | 日夜不一致（U9＋巡檢 bug 4） | HUD 的時段字改成一律照伺服器 `day_phase`（白天：早／午；夜晚：晚／夜），不再自己用時刻算（17 點、05:12 的錯）。「夜晚」天氣（晚上沒雨霧）在天氣欄改寫「晴」配夜晚圖示，遇敵卡與地點列寫「晴朗・夜晚」，不再「夜晚・夜晚」 | `first10_19` → `6f1_07_encounter`（「濃霧・夜晚」） |
| 9 | 正式入口（U10＋美術 PM 頂列） | 沒有 `?dev=1`：首頁只有「開始」→ 建立角色；建角頁標題「建立角色」，不顯示「開發模式（不用登入）」字樣（還沒登入時只留「登入帳號」鈕）與季末重置；大世界頂列標題改成區域名（「雲嶺 Lv 1～6」），本機模型勾選框只在開發模式，「換角色／回首頁」改「切換角色／回到首頁」（沒動齒輪）。`?dev=1` 時照舊：原本的首頁（roguelite、地圖清單、單場戰鬥、技能工坊）、「大世界（測試）」、勾選框、季末重置（管理者）都在 | `first10_01`、`first10_02` → `6f1_01_home`、`6f1_02_create`、`6f1_03_world_first`；開發模式 `6f1_10_dev_home`、`6f1_11_dev_world` |
| 10 | U16 | **Esc**：重現到了——滑鼠停在對話框的按鈕上（例如「接任務」），按鈕說明卡會在 document 上吃掉 Esc，對話框就關不掉。大世界的 Esc 改在捕獲階段處理；有**釘住**的浮動卡時照舊先關卡片。**出口格**：右上整組（地名、小地圖、時間天氣、錢包）不再因出口變半透明，「出」格不會透過小地圖畫出來；其他塊照舊 | `first10_12` → `6f1_04_npc_dialog`、`6f1_05_npc_esc_closed`；`first10_12`（右上「出」）→ `6f1_06_exit_hud_opaque` |

巡檢 bug 1 的重現方式（打開任一開局畫面看起始武器）已確認：改完後開始畫面、建角、開新一輪共用的 start-options 只有一顆「弓」（API 測試也檢查選單沒有同名武器）。

## 2. 新名字（請玩法 PM 確認）

| 原本 | 新名字 | 備註 |
|---|---|---|
| `frost_shard` 武器技版「冰錐」 | **冰錐刺** | 法術版仍叫「冰錐」 |
| `bow_guard`「弓」 | **護衛弓** | 另標 `enemy_only`，開局選單不列 |
| 霜咒短描述 | 「暗影傷害＋冰凍 1 回合：……」 | 只改 `narrative.concept` |

## 3. WORLD_RULES_VERSION：**升了，6 → 7**

- 全滅回鎮法力回滿（`trpg.world.battle._lost`）會讓同一份世界日誌重播出不同的角色狀態。
- 白板 `fallback` 旗標存進角色狀態，新手鏈被動保底的改動也會讓重播不同；兩項記在同一個版號（`save.py` 文件字串已補第 7 條）。
- 依據：`docs/design/09-世界與敘事.md` #98 只寫「HP 回滿」，沒寫法力；9.6.7 第 2 條「只有城鎮與營火能完全回復」。原本「法力照戰後」來自 `Phase5計畫.md` 的開發規格（代決 5A4-8 一帶），不是設計文件。照 prompt 的保守做法回滿，列為待決。

## 4. 檔案

- Python：`src/trpg/api/world_growth_view.py`、`src/trpg/api/world_presenter.py`、`src/trpg/api/routes/runs.py`、`src/trpg/content/battle.py`、`src/trpg/content/composer_rules.py`、`src/trpg/skillgen/whiteboard.py`、`src/trpg/skillgen/whiteboard_candidates.py`、`src/trpg/world/battle.py`、`src/trpg/world/save.py`、`src/trpg/world/step.py`、`src/trpg/roguelite/flashes.py`
- 內容：`content/weapons.yaml`、`content/skill_composer.yaml`、`content/skills/skill_wil_frost_hex.yaml`
- 前端：`client/src/App.tsx`、`client/src/screens/HomeScreen.tsx`（新）、`client/src/screens/WorldScreen.tsx`、`client/src/screens/BattleScreen.tsx`、`client/src/screens/battle/BattleBottomBar.tsx`（只加一個 prop 傳下去）、`client/src/ui/EndPanel.tsx`、`client/src/styles/battle-panels.css`、`client/src/world/battleSummary.ts`（新）、`client/src/world/WorldCharacterPicker.tsx`、`client/src/world/WorldHud.tsx`、`client/src/world/WorldPanel.tsx`、`client/src/world/hud.ts`、`client/src/run/startFlow.ts`、`client/src/dev/layoutSmoke.ts`
- 沒碰 `client/src/render/`、`client/src/battle/`。
- 測試：新增 `tests/api/test_first10_text_6f1.py`、`tests/skillgen/test_passive_fallback_6f1.py`、`client/src/world/battleSummary.test.ts`；修改 `tests/world/test_fight.py`（法力回滿）、`tests/api/test_run_start_api.py`、`tests/skillgen/test_whiteboard_3w4b.py`、`tests/world/test_flash_world.py`、`tests/world/test_quests.py`、`client/src/world/hud.test.ts`、`client/src/world/camera.test.ts`
- 截圖：`docs/art/6f1_01`～`6f1_12`

## 5. 測試

- client：vitest 全部 **213 檔、2325 個通過**；`corepack pnpm -C client build` 通過。
- Python：`tests/api tests/world tests/content tests/roguelite` 加兩個 skillgen 檔，**4887 通過、2 失敗 → 修正後重跑通過**（失敗是兩個測試用 `match="offer_pick"／"flash_pick"` 比對我改掉的錯誤文字）。另跑過 `tests/skillgen/test_refactor_3wr2.py`（霜咒改描述後夾具仍過）。
- 每次 commit 前：ruff check、ruff format --check、mypy src、lint-imports、swamp 種子 7 重播（88 動作、313 事件，一致）。
- 浮動卡：本段沒有新增彈出層或 `title=`；6.5.1 的滑進／捲動／釘住流程沒有變動，沒另外量。

## 6. noqa

無。

## 7. 待 PM 決定

1. **全滅回鎮的法力**：照保守做法改成回滿（設計文件 #98 只寫 HP）。請玩法 PM 確認；若要維持「法力照戰後」，改回 `_lost` 並再升一次 `WORLD_RULES_VERSION`。
2. **新名字**：冰錐刺、護衛弓（第 2 節）。另外其他「法術、武器都能出」的白板配方（火球、雷擊、暗影彈等）武器版也和法術版同名；這段只照 C4 改了冰錐，要不要全部補 `weapon_name_zh`、以及要不要加內容檢查「同名不同技能」，請玩法 PM 決定。
3. **排版煙霧檢查要在開發模式跑**：正式首頁只剩「開始」，`window.__layoutSmoke.runCase／runScreens` 改成沒有 `?dev=1` 時直接回 FAIL 說明。`docs/開發PM交接.md` 6.2 第 5 點的網址要從 `/?anim=0.1` 改成 `/?dev=1&anim=0.1`（我沒改交接文件）。
4. **管理者的季末重置**也收進 `?dev=1`：管理者帳號要從開發模式網址進才看得到（權限仍由伺服器檢查）。
5. **「夜晚」天氣的顯示**：天氣欄寫「晴」配夜晚圖示、文字寫「晴朗・夜晚」，是顯示上的解讀（夜晚天氣＝晚上沒有雨霧，規則上仍有隱蔽加強）。如果要把「夜晚」從天氣表拿掉、改成純時段，是規則題。
6. **出口淡化**：右上整組不再淡化；出口剛好在那一角時，只能從小地圖看到出口位置。
7. 世界錯誤訊息裡還有一些帶英文代碼的句子（多半是內容檢查或開發用，例如「升級選擇（level_up）」在一輪），這段只改了玩家在大世界會碰到的兩句。
