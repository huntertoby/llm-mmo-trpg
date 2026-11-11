# Phase CB-2e｜#149：頭目每階段 3 招的施放率補強

> 來源：`docs/玩法決定紀錄.md` #149 的 2026-11-11 各條（玩法 PM 裁定，main `29495847`、`5b1972d3`、`c2af7393`）、`docs/design/18-雲嶺內容.md` 18.2、`docs/design/19-*` 19.4、19.7。前置：`docs/phases/PhaseCB-2d報告.md`。
> 調查與數字（只讀模擬的結果）：共用筆記資料夾 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_c2d54362-e4f7-4f75-b1dd-07933f64c2aa\` 的 `候選-霧鎖真人換execute.md`、`量測-頭目每回合施放率.md`、`調查-AI隱蔽分數與碎晶之主兩招.md`。草稿與模擬腳本在 `C:\Users\tobby\AppData\Local\Temp\claude\9f1b79de9b6f77a5\a9ed9ff7-f0fd-4dbe-868c-139ab4e352c7\scratchpad\cb2e\`、`cb2f\`、`cb2g\`（`drafts\mist_rend.diff`、`skill_mist_rend.yaml`、`K2_ai_concealed.diff`、`R_clap.diff`、`sim2.py`、`sim3.py`、`enc.py`）；資料夾若不在，照筆記內容重寫。

## PM 決定（不要再問）

| 項目 | 決定 |
|---|---|
| 標準 | 進到該階段後，頭目每個行動回合的施放率（施放次數 ÷ 頭目在該階段的行動回合數）：≥ 20% 達標；10～20% 可接受、不動；< 10% 要處理 |
| 霧鎖真人第 3 階段 | `skill_execute` 換成新招 **收霧斬 `skill_mist_rend`**（放血斬的敵人版：1 AP 近戰 700‰＋流血 2 回合、冷卻 2、`enemy_only`）|
| 霧鎖真人 `mist_shift` | `content/ai_profiles.yaml` 的 `ally_status_values` 加 **`concealed: 2`**（只能是 2）。不換招 |
| 碎晶之主第 1 階段 | `cluster_bolt` 換成現有的 **`skill_thunder_clap`** |
| 碎晶之主第 3 階段 `skill_blink` | **本段不動**（併進平衡段和 trapper 一起調） |
| 其餘 10～20% 的招、歸一門檻、任何數值 | 不動 |

## 範圍外

- 不調任何其他數值、門檻、AI 權重；不新增其他招；不改 `src/trpg/`（若非改不可，停下來回報）。
- 前端動畫不用新畫（調查判斷收霧斬、震波都有現成片段）；若實際發現缺片段，寫進報告，不要自己畫。

## 交付項目

1. **內容修改**：上表三項。新招收霧斬要補齊所有登記處：技能圖示 fixture、`tests/skillgen`（`test_enemy_only` 等固定名單）、`tests/narrative`（圖示 fixture）、技能預算（`trpg skills budget`；超出預算時回報，不自行改數值）。
2. **合併前必須先量的三項**（玩法 PM 的條件：加 `concealed: 2` 前後，玩家勝率變動不超過 3 個百分點；**有任何一項超過就不要合，停下來回報**）：叛徒戰（青霧執事，霧隱）、夜間霧魅增援、帶 `skill_blink` 的我方 build（我方 AI 也讀同一張表）。每組至少 60 場、同種子前後對照。
3. **模擬**（內容都完成後跑一次，輸出摘要表；沿用調查的 `sim2.py`／`sim3.py` 做法，可複製進 `scripts/` 成為 `scripts/cb2e_sim.py` 並修掉 `cb2a_sim.py` 把源晶柱 `surge` 算進第 1 階段的問題）：三個頭目各階段各招的每回合施放率（80 場，8 build × 10 種子）、勝率、輪數；碎晶之主分 build 勝率（每個 build 30 場，列出 < 40% 的）；調查量過的四組會隱蔽的敵人（懸賞霧中劍客、營地霧隱精英、裂痕霧魅、角魔祭壇熔晶魅）前後勝率。

## 受影響的既有功能

| 項目 | 影響 | 處理 |
|---|---|---|
| CLI 快照、固定種子測試 | AI 評分與頭目招式變了，數字會變 | 重產前逐類說明原因；確定性與重播比對不可放寬 |
| `tests/skillgen`、`tests/narrative`、`tests/roguelite` | 固定名單、fixture、固定種子 | **這三個目錄要跑** |
| 前端 fixture（`client/src/render/fixtures/`、圖示） | 新招要登記 | 跑相關 vitest 檔與 `typecheck` |
| 世界日誌 | 內容 digest 會變 | `WORLD_RULES_VERSION` 不加一 |

## 行為一致測試

- 表格測試，**實際跑引擎**：霧鎖真人第 3 階段 3 招都能施放、AI 會選到收霧斬；第 2 階段 AI 會選到 `mist_shift`；碎晶之主第 1 階段 AI 會選到 `skill_thunder_clap`。
- 資料測試：第一季敵人招數仍達 18.2 表格；頭目每階段 3 招。

## 驗收條件

- `ruff check`、`ruff format --check`、`uv run mypy`、`lint-imports` 通過。
- `tests/content`、`tests/engine`、`tests/sim`、`tests/world`、`tests/api`、`tests/cli`、`tests/skillgen`、`tests/narrative`、`tests/roguelite`、`tests/test_architecture.py` 通過（CLI 快照帶 `TRPG_FULL=1 -m "not llm"`）。`tests/skillgen/test_player_text.py::test_player_check_texts_have_no_english_identifiers` 單獨要約 5 分鐘，分批跑、不要和其他目錄擠在同一個 `-n 8`；`tests/api/test_world_dev_boss.py::test_dev_boss_rehearses_to_the_boss_charge` 已知不穩定，失敗時單獨重跑確認，不要改它。
- 前端：`corepack pnpm -C client typecheck`、有改到 fixture 的 vitest 檔與 `src/render/inkDollSnapshot.test.ts` 通過。
- 至少 3 張地圖 `--log-json` ＋ `replay` 通過。

## 報告

`docs/phases/PhaseCB-2e報告.md`：逐條驗收、三項補量的前後對照、三個頭目的施放率表（標出 < 10% 與 10～20% 的）、碎晶之主分 build 勝率、快照變動說明、待 PM 決定。
