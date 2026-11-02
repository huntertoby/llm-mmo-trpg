# Phase 5C-1 報告：隊伍與系統傭兵

> 實作者：implementer agent（2026-11-03）。依 `docs/phases/Phase5計畫.md` 第 22 節（本段新增的詳細規格，`9d50a4ae`）。
> 依據：09 9.6.9 #97（3 人隊伍、傭兵免費、出城前選好、野外不能換）、9.6.8 #87（固定 build、強度同主角、AI 同隊友）、9.6.11 #117（9 名傭兵暫名與底稿）、5A-SIM2（隊友照主角等級成長）。

## 1. 交付

| 項目 | 內容 |
|---|---|
| 規格 | `Phase5計畫.md` 第 22 節「5C-1 詳細規格」（合併 main 後，5B-4c 佔第 21 節；「之後各段規格」改為第 23 節） |
| 內容 | `content/world/mercenaries.yaml`（9 名＋`max_hired: 2`）；schema `src/trpg/content/world_mercenaries.py`（ID 不重複、四種定位各 ≥ 2）；`library.py` 載入 `world_mercenaries`，檢查底稿存在且不是白板／對照組；沒有檔案時為 `None` |
| 世界 | `src/trpg/world/party.py`（新）：`hire`、`hire_problem`、`party_spawns`；`CharacterState.mercenaries`（預設空、依出場順序）；動作 `hire`（整組替換）、事件 `party_changed`；`battle_started.mercenaries`；`prepare_battle` 有傭兵時用傭兵取代標準隊友，同一個 `grow_allies` 照主角等級成長。存檔版號不變 |
| API | `WorldView.party`（`PartyView`：成員、`max_hired`、`can_hire`、`hire_problem_zh`、名單含定位／主題／技能概要／已雇用）；`EncounterView.allies_zh`；`WorldActionRequest` 加 `hire`；`party_changed` 事件句子。新檔 `world_party_schemas.py`、`world_party_view.py`；OpenAPI 與 `schema.d.ts` 已重產 |
| 前端 | 小鎮選單「雇用傭兵」（`aria-expanded`，面板內展開；依定位分組、勾選上限 2、勾選順序＝出場順序、主題說明用共用 `<Hint>`、技能概要一行）；右側「隊伍」面板；遇敵面板的我方改用 `allies_zh`；角色建立畫面的隊友說明改字。`client/src/world/party.ts`、`PartyPanel.tsx`、`styles/world.css` |
| 測試 | `tests/world/test_party.py`（16）、`tests/content/test_world_mercenaries.py`（3）、`tests/api/test_world_party_api.py`（3）、vitest `client/src/world/party.test.ts`（5） |

## 2. 傭兵名單摘要（9.6.11 #117；ID 開發 PM 取）

| ID | 暫名 | 稱號 | 定位 | 底稿 | 武器／AI |
|---|---|---|---|---|---|
| `merc_qingfeng` | 青鋒 | 近戰劍客 | 輸出 | `build_striker` | 雷電法杖／cunning |
| `merc_chuanyun` | 穿雲 | 弓手 | 輸出 | `build_ranged` | 弓／預設 |
| `merc_chiyan` | 赤焰 | 火術士 | 輸出 | `build_fire` | 火焰法杖／cunning |
| `merc_tiebi` | 鐵壁 | 盾衛 | 守護 | `build_tank` | 單手劍／guard |
| `merc_panshi` | 磐石 | 守護者 | 守護 | `build_guardian` | 單手劍／guard |
| `merc_huichun` | 回春 | 醫者 | 輔助 | `build_healer` | 冰霜法杖／support |
| `merc_qingyin` | 清音 | 祝禱師 | 輔助 | `build_support` | 冰霜法杖／support |
| `merc_jinglei` | 驚雷 | 雷水術士 | 控制 | `build_storm` | 雷電法杖／cunning |
| `merc_fuying` | 伏影 | 陷阱師 | 控制 | `build_trapper` | 火焰法杖／archer |

注意：「青鋒（近戰劍客）」的底稿 `build_striker` 實際是雷電法杖的蓄力流法系 build，名稱與打法不符（暫名照設計文件，見待 PM 決定 1）。

## 3. 瀏覽器驗證紀錄（Claude_Browser；`.scratch_5c1/serve.py` 在 8070 提供 API＋`client/dist`，存檔 `.scratch_5c1/saves`；`TRPG_LLM_BASE_URL=http://127.0.0.1:9/v1`、`TRPG_LLM_GENERATE=false` 降級）

1. 1600×900：在霧渡鎮建角（經 API）→ 進入 → 右側「隊伍」顯示主角＋2 名標準隊友 → 小鎮選單「雇用傭兵」展開 9 名（輸出／守護／輔助／控制分組、技能概要）→ 勾鐵壁、回春（其餘 7 個勾選框停用，順序標「第 1／2 位」）→「確定雇用：鐵壁、回春」→ 紀錄「隊伍：雇用鐵壁、回春（免費）。」、隊伍面板「鐵壁 盾衛・守護・1 級／回春 醫者・輔助・1 級」。
2. 出城到渡口石階：「雇用傭兵」按鈕消失，隊伍面板顯示「換傭兵：出城前在城鎮選好，野外不能換」。來回走到竹林小徑遇敵（霧狼 ×3）：遇敵面板「我方：主角（開場 HP 40）＋鐵壁、回春」。
3. 開戰：戰鬥畫面先攻與行動順序出現「阿霧、鐵壁、回春」與 3 隻霧狼，傭兵由 AI 操作（截圖確認單位在場）。戰鬥沒有打完（不在驗收範圍）；勝負回寫由 `tests/world/test_party.py`、`tests/api/test_world_party_api.py` 涵蓋。
4. 浮動卡（傭兵名的主題 `<Hint>`）：1600×900 滑過 → 卡片貼齊上方（底緣＝觸發元素頂緣）→ 滑進卡片不關 → 內容不需捲動（`scrollHeight == clientHeight`、`max-height` 892px）→ 點一下釘住、滑鼠離開仍在 → Esc 關閉。800×600：最後一名（伏影）的卡片往內推到 x=4、貼齊上方，同樣釘住與 Esc 正常；文件沒有水平捲動。
5. 結束時只停了自己開的伺服器（`TaskStop`，8070 已無回應），關閉自己開的分頁。

## 4. 代決（開發 PM 定，最保守預設；規格 22.11）

| # | 事項 | 代決 |
|---|---|---|
| 5C1-1 | 隊伍上限放哪 | `mercenaries.yaml` 的 `max_hired: 2` |
| 5C1-2 | 沒雇傭兵時的隊友 | 照舊 2 名標準隊友；雇 1 名時只帶那 1 名（#97「可以少帶人」），不補標準隊友 |
| 5C1-3 | 能雇用的地點 | 任何 `town` 種類地點；每個城鎮名單相同 |
| 5C1-4 | 傭兵 AI | 效用 AI＋戰鬥中的隊友指令（同標準隊友）；保留底稿 `ai_profile` |
| 5C1-5 | 開場狀態 | 每場滿 HP／法力／耐力，不追蹤傭兵的傷 |
| 5C1-6 | 戰鬥單位名稱 | 範本 `id`＝傭兵 ID、`name_zh`＝暫名，其他照底稿 |
| 5C1-7 | 技能依階級對照 | 走 `grow_allies`（`at_run_tier` 重配到主角等級對應階級），不另寫對照表 |
| 5C1-8 | 雇用時機 | 城鎮且沒有遭遇；戰鬥中 API 回 409（既有規則）、檢視顯示「戰鬥中」 |
| 5C1-9 | 出場順序 | `hire` 清單順序 |

## 5. 待 PM 決定

1. **青鋒的底稿不合稱號**：9.6.11 寫「青鋒（近戰劍客）＝`build_striker`」，但 `build_striker` 是雷電法杖的法系蓄力流；要改底稿（例如 `build_push`／`build_charger` 等近戰 build）或改稱號，需玩法 PM 決定（只動 `mercenaries.yaml`）。
2. **裝備預算**（9.6.8「裝備預算和主角相同」）：底稿沒有裝備，傭兵目前不帶裝備；等 5D 物品等級做好後再接。
3. **底稿技能數**：底稿 build 帶 7～9 招（模擬用，沒有照主角欄位上限）；傭兵強度可能高於同等級主角。正式上線前（5F 賽季 Boss 模擬）建議量一次，或改為照欄位上限挑技能。
4. **「雇 0 名」的意義**：目前 0 名＝帶 2 名標準隊友。若設計上要允許真正的單人或 2 人（主角＋0），需另加選項。
5. **戰鬥外的隊友 AI 預設**：設計說「可以設定 AI 行為」；目前沿用戰鬥中的「隊友指令」，沒有在城鎮存預設的設定。

## 6. 檢查

- `ruff check .`、`ruff format --check .`、`mypy`（1063 檔）、`lint-imports`（9 契約）通過。
- `pytest tests/world tests/api tests/content tests/test_architecture.py -n 8`：2720 passed。
- `pytest tests/cli -m "slow or not slow" --timeout=3000`：180 passed。
- `npx vitest run`：128 檔、1219 passed；`npm run build`：通過。
- 交件前 `git merge main`（只有文件變動，無衝突）。
