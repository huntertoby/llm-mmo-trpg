# Phase 5A-7 完成報告：新世界動作的 API 與前端

> 實作者：implementer agent（2026-11-03）。規格：`docs/phases/Phase5計畫.md` 第 13 節（先寫入規格、commit `8675068f`，再實作；「之後各段規格」改為第 14 節）。
> 動到的檔案：`src/trpg/api/`（新 `world_growth_view.py`；`world_schemas.py`、`world_presenter.py`、`routes/world.py`、`world.py`；`run_presenter.py` 只公開兩個既有函式）、`src/trpg/world/`（`state.py` 加 `LastBattle`／`last_battle`、`battle.py` 打完寫入）、`tests/api/test_world_growth_api.py`、`tests/world/test_last_battle.py`、`client/`（大世界畫面、一輪元件加選填參數、`BattleScreen` 開場說明、API 型別、`openapi.json`）。沒有動引擎、roguelite、戰鬥紀錄格式（`LOG_FORMAT` 不變）。

## 1. 交付

| # | 項目 | 檔案 | commit |
|---|---|---|---|
| 1 | 5A-7 詳細規格 | `docs/phases/Phase5計畫.md` 第 13 節 | `8675068f` |
| 2 | 最近一次戰鬥結果留在角色上（5A-5 待決 1） | `src/trpg/world/{state,battle}.py`、`tests/world/test_last_battle.py` | `ea55c345`（`region` 欄位在 `72e55781`） |
| 3 | API：新世界動作、閃現／配點預覽、`WorldView` 的成長、誓約、下一場修正、開場說明、最近一次戰鬥、新事件句子；OpenAPI 重產 | `src/trpg/api/*`、`tests/api/test_world_growth_api.py`、`client/openapi.json`、`client/src/api/schema.d.ts` | `72e55781` |
| 4 | 前端：「成長與技能」畫面（重用一輪元件）、閃現待選、誓約區、狀態與限制說明、戰鬥開場說明 | `client/src/world/{WorldGrowth.tsx,growth.ts,growth.test.ts,WorldPanel.tsx}`、`client/src/screens/{WorldScreen,BattleScreen,RunFlashPending}.tsx`、`client/src/run/{FlashChooser,FlashSection,CampfireSkillCare,AttributeRespecSection}.tsx`、`allocationPreview.ts`、CSS | `2998c810` |
| 5 | 閃現後同名技能的句子 | `world_growth_view.py` | `734eba0b` |
| 6 | 合併 main（5A-SIM） | — | `ed347672` |
| 7 | 本報告 | `docs/phases/Phase5A-7報告.md` | 最後一筆 |

## 2. API 變動

| 方法與路徑 | 變動 |
|---|---|
| `POST /api/world/characters/{id}/actions` | `WorldActionRequest` 加 `allocate`、`respec`、`flash`、`flash_pick`、`dissolve`、`inherit`、`swear_oath`、`release_oath`（欄位同 `trpg.world.actions`）。`swear_oath` 只收 `source: "menu"` 且沒有 `prompt_version`，否則 422（代決 5A7-4）。 |
| `POST /api/world/characters/{id}/flash-preview`（新） | `{skill, slot}` → `FlashPreviewOut`（大世界內容庫視圖＋角色技能種子；不扣點、不寫日誌） |
| `POST /api/world/characters/{id}/allocation-preview`（新） | `{attributes}` → `AllocationPreviewOut` |

`WorldView` 新增：`hero`（一輪的 `HeroOut`）、`pending_flash`（一輪的 `PendingFlashOut`）、`growth`（靈感、角色階級、`at_service`、`service_zh`、`can_allocate`、`can_spend`、`blocked_zh`、`pending`）、`oath`（`available`、`unavailable_zh`＝「尚未開放」、`current`、冷卻、`can_swear`／`swear_problem_zh`、`can_release`、`templates`）、`next_battle_zh`、`last_battle_zh`。`character` 加 `insight`、`skill_tier`；`encounter` 加 `reinforcements`、`first_team`、`hero_statuses`（名稱、說明、回合＝min(預設, 2)）、`opening_zh`。閃現待選時：相鄰地點 `blocked_zh`＝「先選完閃現的變化」、休息／換技能／傳送關閉。

新事件句子：開戰（先手、開場狀態、增援）、升級（屬性點、靈感、角色階級）、升階重配、精英首殺靈感、配點、重配、閃現出題、選閃現、溶掉、傳承、立誓、解除誓約。

`trpg.world`：`CharacterState.last_battle: LastBattle | None`（`region`、`location`、`won`、`end_reason`、`rounds`、`xp_gained`、`level_before`、`level`、`at`），`fight` 結算寫入、其他動作不清；有預設值，`trpg-char/1` 不升版號，舊檔照讀，重播相同（測試）。

## 3. 畫面流程

```
地點圖畫面
  右側狀態：Lv・經驗・HP…／角色階級・靈感點・未分配屬性點／誓約／下一場修正（每筆一句）／最近一次戰鬥
  目前地點：服務按鈕＋「這裡可以（不能）閃現、重閃、溶掉、傳承、重配屬性、立誓（只在城鎮與營火）」
            「成長與技能（屬性點 N・靈感 N）」→ 左欄切換
  遇敵陣容：多了開場說明（我方／敵方先手：第 1 輪全部先動…、開場狀態〔中毒〕2 回合（不擲抵抗）、增援 N 名）
左欄「成長與技能」（重用一輪元件）
  地點限制說明（不在城鎮或營火時橘字：「現在不行：這裡不是城鎮或營火」）
  屬性點：配點（含 HP／法力／耐力預覽，任何沒有遭遇的時候）、免費重配（只在城鎮與營火）
  靈感閃現（FlashSection）→ 出題前畫面（FlashChooser，預覽走大世界端點）
  重閃／溶掉或傳承（CampfireSkillCare，標題「只在城鎮與營火」）
  誓約：沒有 world/oaths.yaml →「立誓（尚未開放）」停用；有內容 → 模板選單＋參數＋誓言 → 立誓；已有誓約 → 解除（先確認）
閃現待選：左欄固定顯示選項畫面（一輪的 FlashPendingPanel）＋「先選完閃現的變化」，地點圖收起、切換按鈕停用、服務關閉
戰鬥畫面：開場橫幅下顯示開場說明，並留一則可關的提示（15 秒）
```

一輪元件只加選填參數（預覽來源、停用原因、地點文字），一輪的行為不變（vitest 全過）。

## 4. 瀏覽器驗證紀錄（Claude_Browser；後端＋前端 `trpg serve --port 8040`，`TRPG_SAVE_DIR=.scratch_5a7/saves`；1600×900）

1. 首頁 →「進入大世界（測試）」→ 建角「驗收七」：人類、雲嶺出身、雙手劍、倒地（絆擊）＋撞擊（頂撞）→ 進入。右側：「Lv 1・經驗 0／100・HP 60／60…／角色階級 1・靈感點 0」，霧渡鎮服務下方「這裡可以閃現、重閃、溶掉、傳承、重配屬性、立誓。」與「成長與技能」按鈕。
2. 在地點圖點渡口石階 → 竹林小徑 → 渡口石階 → 竹林小徑：遇敵「竹林小徑／敵人等級 1・戰場 竹林／霧狼 ×3」。
3. **在戰鬥畫面上手動打完並打贏**：點「開戰」→ 第 1 回合點「結束回合」；第 2 回合點「移動」→ 點格子移到 (3,2)，點技能「絆擊」→ 點紅框的霧狼施放（失手，但技能算用過）→ 結束回合；第 3 回合結束回合；第 4 輪隊友擊倒最後一隻 → 畫面右下「勝利！（全滅）・第 4 輪」→ 點「回到地點圖」（截圖記錄於本次對話）。
4. 回到地點圖：「Lv 2・經驗 100／200・HP 63／63」「角色階級 1・靈感點 2・未分配屬性點 2」「最近一次戰鬥（竹林小徑）：打贏了（4 輪），獲得 100 經驗，升到 2 級。」；紀錄：「打贏了（4 輪），獲得 100 經驗。」「升到 2 級！（未分配屬性點 2、靈感點 2、角色階級 1）」「竹林小徑已清空…」。
5. **重新整理頁面**再進入：事件紀錄是空的，但「最近一次戰鬥（竹林小徑）：打贏了…升到 2 級。」仍在（5A-5 待決 1 解決）。
6. 在竹林小徑（野外）開「成長與技能」：橘字「現在不行：這裡不是城鎮或營火。」；閃現、選這招都停用、配點可用。**配點**：力量 ＋ → 預覽「配點後：耐力 ＋2」→「確認分配屬性點」→「分配屬性點：力量 ＋1（剩 1 點）」，再一次 →「（剩 0 點）」。（自動化連點兩下 ＋ 只記到 1 點，是一輪配點元件既有的連點行為，正常操作不受影響。）
7. 走回霧渡鎮 → 服務說明變「這裡可以…」→「成長與技能（靈感 2）」→ 絆擊顯示「可以閃現了」、頂撞（沒用過）停用。點「閃現」→ 出題前畫面（大世界預覽端點）：「閃現「絆擊」第 1 次／不指定 1 點・4 選 1／指定類別：範圍（1）連段（1）元素與關鍵字（3）費用（1）延長與收割（1）」→「確定，扣 1 點並出題」。
8. **待選**：左欄只剩「先選完閃現的變化：選之前不能移動、開戰或使用其他服務。」＋4 個選項；地點圖收起、「回到地點圖」切換按鈕停用、休息與換技能消失；頁面內直接送 `travel` → 422「還有閃現的選項沒有選（flash_pick）」。紀錄：「閃現「絆擊」：花 1 點靈感，出 4 個變化（剩 1 點），一定要選一個。」
9. 選第 1 個（連段：多打一下）→「確定」→ 待選消失、靈感點 1、「絆擊 已閃 1／5 次」、休息與換技能恢復；紀錄「選好變化…」（句子在此之後改成同名時「「絆擊」換上新的變化。」，`734eba0b`）。
10. 誓約區顯示「立誓（尚未開放）」停用（沒有 `world/oaths.yaml`）。
11. 浮動卡 6.5.1 抽查：「休息」滑過 → 說明卡貼齊、在視窗內（x 945、y 273、240×52）。800×600：成長畫面單欄、沒有水平捲動（`scrollWidth` 785 < 800）。本段沒有新增浮動卡元件，只沿用 `Hint`。
12. 結束時只停了自己開的 8040 伺服器（確認埠已釋放）。

開場說明（先手、開場狀態、增援）沒有在瀏覽器實際遇到（需要情境判定給的下一場修正或暗門線頭）；由 `test_next_battle_and_opening_lines` 驗證後端句子，前端只是顯示 `opening_zh`。

## 5. 代決（開發 PM 定，最保守預設）

| # | 事項 | 代決 |
|---|---|---|
| 5A7-1 | 最近一次戰鬥結果放哪 | `CharacterState.last_battle`（`fight` 寫入、可重播）；畫面一句話 |
| 5A7-2 | 成長畫面位置 | 左欄切換（地點圖 ↔ 成長）；閃現待選時固定顯示選項 |
| 5A7-3 | 重用一輪元件 | `WorldView.hero` 用 `HeroOut`；元件加選填參數，一輪行為不變 |
| 5A7-4 | 立誓的來源 | API 只收 `menu`；LLM 轉換之後再接 |
| 5A7-5 | 解除誓約的地點 | 照 5A-6：有誓約就能解除（不限地點），畫面先確認 |
| 5A7-6 | 開場說明文字 | 先手「第 1 輪〔我方／敵方〕全部先動，第 2 輪起照先攻」；開場狀態「狀態名＋回合（不擲抵抗）＋說明」；增援「增援 N 名（已在陣容裡）」 |
| 5A7-7 | 閃現待選時的城鎮畫面 | 後端把休息、換技能、傳送、紮營關掉（紮營原因「先選完閃現的變化」）；前端只照 `WorldView` 顯示（實作補） |
| 5A7-8 | 誓約參數的顯示 | 參數用 ID 與原值（例「element＝fire」）；18.6 的中文參數名在 5C-3 寫模板時一起補（實作補） |

## 6. 待 PM 決定

1. **停用按鈕的說明卡不會出現**：`Hint` 包住 `disabled` 按鈕時瀏覽器不送滑鼠事件，所以「立誓（尚未開放）」「閃現（靈感點不足／不在城鎮）」的說明卡滑過不顯示（一輪的閃現區原本就這樣）。原因另有文字顯示在畫面上；要不要改 `Hint`（例如外包一層可接事件的元素）需排介面段，6.5.1 有 CSS 注意事項。
2. **一輪配點元件的連點**：快速連點兩下「＋」只加 1 點（`adjustAllocation` 用同一個舊狀態），一輪也一樣；正常速度操作沒問題。
3. **事件卡與情境判定畫面**（5B-5）：`next_battle` 目前只有情境判定會給，畫面還不能做情境判定，所以下一場修正與開場說明在實際遊玩中暫時看不到。
4. **誓約參數中文名**：`OathParamDef` 沒有 `name_zh`；5C-3 寫 18.6 模板時建議加。

## 7. 檢查結果（合併 main `ed347672` 之後）

| 檢查 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | 通過（1566 檔） |
| `mypy`（strict） | 通過（1015 檔） |
| `lint-imports` | 9 條契約 KEPT |
| `pytest tests/api tests/world tests/test_architecture.py -n 8` | 605 passed |
| `pytest tests/cli -m "slow or not slow" -n 8 --timeout=3000` | 180 passed |
| `npx vitest run` | 124 檔、1198 passed |
| `corepack pnpm -C client build` | 通過 |
| OpenAPI 快照 | 重產（`export_openapi.py` ＋ `gen:api`），合併後再產沒有差異 |

`C901` 沒有超標、沒有新增 `# noqa`。沒有跑全量 `scripts/check.py`（PM 合併時跑）。

### 7.1 pytest

- `pytest tests/api tests/world tests/test_architecture.py -n 8 --timeout=3000`：605 passed
- `pytest tests/cli -m "slow or not slow" -n 8 --timeout=3000`：180 passed（快照沒變）
