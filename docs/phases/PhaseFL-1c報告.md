# Phase FL-1c 報告：閃現費用方向第 5～7 點（FL-1a 後補）

> 規格：`docs/design/06-技能.md` 6.34「費用方向」第 5、6、7 點（玩法 PM 822106148，2026-11-13）；背景 `docs/phases/PhaseFL-1a報告.md`。開工時 `git merge --ff-only main`（`e6ebcbb8d`）。

## 1. 三點怎麼做

**第 5 點：少付以卡片實付值為準**（`src/trpg/skillgen/flash_ops.py`）

- `_light_cost_drafts(skill, fields, library)`：AP 已是 1 時依 `cost_fields`（冷卻 → 法力 → 耐力）找第一個能減的項目；減 1 前後的 **實付值**（`_paid`：法力照 `core.mana_cost`，×0.8 四捨五入；其他照資料值）相同就 **停下**：這一項不出草稿，也不改試後面的項目。前面已經排進來的草稿照舊（原本就是依序試）。
- 結果：FL-1a 報告列的 7 招（飛行、咒印飛彈、霜寒之觸、收割靈魂、靜電掌、燼咒、雷咒）**全部不再出輕巧**（法力 3 → 2 實付都是 2）。這 7 招都還有別的閃現選項（見第 2 節）。

**第 6 點：增益也算狀態**（`src/trpg/skillgen/flash_cost.py`）

- 新增 `_has_rounds(effect)`：「狀態回合」＝ `apply_status`（增減益本來就都算）＋ `grant_skill`（暫時給技能，原語定義只能給自己或友方）＋ `affects: allies` 的 `zone`（只對友方的持續區域）。蓄力的 `_duration_step`（+1、累計原招 +2）、輕巧的降回合（最少 1）、原招回合表 `origin_durations` 都改用它。
- 調整順序（傷害 → 狀態強度 → 狀態回合）、一次一項、強度只在回合加不上時才調、蓄力可一升一降、輕巧不准任何一項變強：都沒動。
- 「狀態強度」的增益：頂層 `apply_status` 的增益本來就照 `scales_with_magnitude` 調；區域裡的巢狀狀態不在退路裡（見待決 2）。
- 差異清單（FL-1a 的 `changes`）：`grant_skill`、`zone` 的回合卡片數字沒有，`src/trpg/api/flash_changes.py` 另列 `effects[i].amount`（「獲得技能回合」「區域回合」），否則展翼輕巧在前端只看到 AP 變便宜、看不到變弱。
- 結果：戰歌蓄力＝冷卻 3 → 5、區域 3 → 4 回合；展翼、賜予羽翼輕巧＝AP 2 → 1、飛行回合變少。

**第 7 點：沒有選項的招面板不給按**

- 後端 `src/trpg/skillgen/flash_offer.py::has_options(library, request)`：不指定類別出題會不會至少有 1 個選項。用 **出題同一套** `_builder`／`UsageSource`／`skill_before`：這一次可出的類別 ∪ 補位用的小變化類別（同 `_fill_up`），任一類有一個套得上就停；大變化另看轉型保底。不算 LLM 提議（只會多不會少）。結果快取在 `ContentLibrary.flash_option_cache`（鍵＝請求內容 JSON 的 SHA-256，不用 `hash()`／`id()`；512 筆清空，同 `retier_cache` 不參與相等比較）。
- `src/trpg/roguelite/flashes.py::flash_available`；`src/trpg/api/run_presenter.py::_flash_out` 在 `problem_of` 為 `None`（其他條件都符合）時才算；沒有選項 → `can_flash=False`、`flash_problem_zh="這招目前沒有可以閃的變化"`（`NO_OPTIONS_ZH`）、新欄位 `SkillFlashOut.flash_available=False`。大世界的 `hero_panel` 共用同一個函式，所以兩處面板都有。
- 驗證：1 階主動 277 招 × 第 1～3 次閃現共 809 筆，`has_options` 與 `make_offer(...).options` 非空 **全部一致**（暫存區 `fl1c/equiv.py`）。效能：第一次呼叫中位 1.6ms、p90 12.9ms、最慢 82ms（277 招合計 1.4 秒），快取命中 0.06ms。
- `open_flash` 按下去仍保留「沒有合法的變化」的退路（防呆，不扣點）；面板已經不給按，正常路徑不會走到。
- 前端（`client/src/run/flash.ts` `noFlashOptions`／`NO_FLASH_OPTIONS_TEXT`、`run/FlashSection.tsx`、`world/WorldGrowth.tsx`、`styles/flash.css`）：照 LW-2 標灰（移植需求 3.7 第 1 條）——整列灰紫虛線框、大世界的技能圖示褪灰、字不淡；名稱下一行灰字「這招目前沒有可以閃的變化」；閃現鈕停用（滑過說明同一句）；不再顯示「可以閃現了」。
- OpenAPI 重產：`client/openapi.json`、`client/src/api/schema.d.ts` 各 +5 行（`flash_available`）。

## 2. 掃描統計（FL-1a 方法：1 階主動、內容檔＋白板配方 × 三種武器 × 種子 0～7，種子 12345）

腳本：暫存區 `fl1c/scan.py`（同 FL-1a）、`fl1c/options.py`（有沒有選項；`old` 參數用猴子補丁模擬改前）。

| | FL-1c 前 | FL-1c 後 |
|---|---|---|
| 蓄力・內容檔：套得上 | 163 | 164（+戰歌） |
| 　**沒變** | 0 | **0** |
| 蓄力・白板：套得上 | 611 | 611 |
| 　**沒變** | 0 | **0** |
| 輕巧・內容檔：套得上 | 126 | 121（−7 法力實付不變，+展翼、賜予羽翼） |
| 　**沒變弱**（不變／變強） | 0 | **0** |
| 輕巧・白板：套得上 | 512 | 512 |
| 　**沒變弱** | 0 | **0** |
| 1 階主動技沒有任何閃現選項 | 9 | **7** |

逐筆變動（只有內容檔，白板 0 筆）：

- 輕巧 套得上 → 不出：咒印飛彈、收割靈魂、燼咒、雷咒、霜寒之觸、靜電掌、飛行（第 5 點，7 招全中）。
- 輕巧 不出 → 套得上：展翼、賜予羽翼（`grant_skill` 回合變少）。
- 蓄力 不出 → 套得上：戰歌（區域回合 3 → 4）。

**補完後仍然沒有閃現選項的招（7 招）**：殘影之誓、血痕疾行、慈焰誓約、移山之力（規則改變，唯一效果）、鏡像施法（複製技能）、吹送（吹送表面，只有距離）、挑釁怒吼（嘲諷、標記各 1 回合：回合 +1 預算 123%／135% 超出上限，冷卻已多 2 也不夠）。

重新有選項的：戰歌（蓄力）、展翼（輕巧）。展翼的蓄力仍不出（飛行 3 → 4 回合預算 121% 超出上限）；戰歌的輕巧仍不出（AP 2 → 1 後區域 2 回合 118%、1 回合 59%，跨過合格區間）——這兩項是一格的粒度問題，屬數值。

## 3. 快照與夾具

**parity 夾具（`tests/skillgen/fixtures/refactor_3wr2.json`）**

- 預測（暫存區 `fl1c/predict.py`）：用猴子補丁回到改前（`_paid` 照資料值、`_has_rounds` 只認 `apply_status`）重跑 126 條 flash 條目，**126 條全部等於夾具**（模擬正確）；記下每次蓄力／輕巧嘗試：「輕巧 AP 1、第一個可減的是法力且實付不變、改前套得上」＝會變；「技能有增益回合」＝可能變。結果 **會變 0、可能變 0**（parity 的閃現條目沒有碰到這 10 招）。`complete`、`retier` 不走 `apply_variation`，不變。
- 實際（slow 跑 `test_refactor_parity.py`）：**0 條失敗**。一致，夾具沒動。

**Mock 提議快照（`test_proposal_l8.py`、`test_proposal.py`）**：預測不變（手寫技能往返提議管線不經過閃現）；實際 0 失敗。

**CLI 快照（`tests/cli`，含輸出快照、`test_run_cli.py` 固定種子一輪、`test_llm_propose_cli.py`）**：預測不變（技能清單與戰鬥不經過閃現；白板配方掃描 0 筆變動，`run auto` 的固定種子只有選到這 10 招的蓄力／輕巧才會變，預測沒選到；沒有逐筆追蹤）；實際 0 失敗，沒有重產。

**改動的既有測試**

| 測試 | 原因 | 處理 |
|---|---|---|
| `tests/skillgen/test_flash_cost_fl1a.py::test_frost_touch_light_is_strictly_weaker` | 霜寒之觸是第 5 點的 7 招之一，輕巧不再出 | 改名 `test_frost_touch_light_is_not_offered`，斷言 `FlashError` |
| `tests/api/test_flash_changes_fl1a.py::test_frost_touch_light_lists_mana_and_a_weaker_die` | 同上，沒有輕巧可以比 | 改用展翼輕巧（AP 2 → 1、獲得技能回合 `worse`、沒有 `better`），另加戰歌蓄力列「區域回合 3 → 4」 |

FL-1a 換掉的那批測試（戰歌 → 寒鎖、`_flashable`）沒有改回去；戰歌現在有蓄力，但它們的斷言照樣成立。

**新增測試**：`tests/skillgen/test_flash_cost_fl1c.py`（7 招不出輕巧、實付不變就停不改試耐力、戰歌蓄力、展翼與賜予羽翼輕巧、火牆不算增益、7 招事先判斷沒選項、4 招有、快取；slow：277 招 `has_options` 與 `make_offer` 一致、沒選項的正好 7 招）、`tests/api/test_flash_available_fl1c.py`（面板資料：沒選項→灰、有選項照舊、其他原因不算）、`client/src/world/fl1cFlashNone.test.ts`（兩處面板的灰列、灰字、停用、樣式）。

## 4. 截圖（注入資料）

`docs/art/shots/fl1c/`。實機要找一個 1 階、沒有選項的招、已用過、在城鎮或營火，太繞；改用開發頁注入：`panel-gallery.html?case=lv4&tab=flash&flashnone=1#growth`（大世界成長面板）、`?flashnone=1#campfire`（一輪營火），把 fixture 第 3 招（烈焰爆）標成伺服器回傳的 `flash_available: false`。開發頁的參數已加進 `client/src/dev/panelGallery.tsx`。

- `growth_800x600.jpg`：大世界成長面板 800×600。
- `growth_1600x900.jpg`：同上 1600×900（內建預覽縮成 800×450 存）。
- `campfire_800x600.jpg`：一輪營火 800×600（灼痕可以閃、烈焰爆灰掉對照）。

## 5. 檢查（結束碼）

| 檢查 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .`、`mypy`、`lint-imports`、`trpg content check` | 全部 0 |
| `pytest tests/skillgen tests/api tests/roguelite tests/world tests/llm -n 8` | 0（7147 passed、15 skipped；含 `test_openapi_snapshot.py`） |
| slow：`test_refactor_parity.py`、`test_proposal_l8.py`、`test_proposal.py`、`test_flash_cost_fl1a.py`、`test_flash_cost_fl1c.py`、`tests/cli`（`-m "slow or not slow" -n 4`） | 0（1205 passed） |
| 前端 `corepack pnpm -C client typecheck` | 0 |
| 前端 `corepack pnpm -C client test --run` | 0（335 檔、4323 項） |
| 前端 `corepack pnpm -C client build` | 0 |

沒跑 `scripts/check.py`、沒跑平衡量測。

## 6. 待 PM 決定

1. **「不改試別的項目」的解讀**：實付不變的那一項之後的項目（例：法力之後的耐力）也不試；它之前已排進來的項目（冷卻）照舊依序試。目前 1 階內容檔沒有同時有法力與耐力可減的招，實際沒有差別。
2. **增益的範圍**：只算 `apply_status`、`grant_skill`、`affects: allies` 的 `zone`。`cheat_death`、`redirect_damage` 的 `duration`、護盾的 `duration`、`grant_ap`／`extra_reaction` 的數量沒有算（規格舉例只有戰歌、展翼）；區域裡巢狀的增益狀態（戰歌的激昂）不調——激昂沒有 `scales_with_magnitude`，「加值」（屬性 +2）沒有可調的旋鈕。要擴大再定。
3. **只對友方的區域才算**：對敵或全體的 `zone`（火牆）回合不在退路裡（它不是增益；規格第 6 點只講增益）。
4. **沒有選項只在「其他條件都符合」時才算**：還沒用過、閃滿、完整技能時照原本的原因，`flash_available` 照 `True`；用過之後才會看到灰字。大世界 4 級前的鎖照舊蓋掉原因字，但列的灰框照 `flash_available`。
5. **事先判斷不算 LLM 提議**：LLM 只會多出選項，所以確定性的部分沒有時才標灰；理論上 LLM 能替沒選項的招提出合法變化，但不給按（保守）。
6. **差異清單補列增益回合**（`flash_changes` 的「獲得技能回合」「區域回合」）：規格沒寫，為了讓輕巧的變弱看得到而加。
7. **仍沒有選項的 7 招**：照規格先接受（誓約、純位移類）；展翼蓄力、戰歌輕巧、挑釁怒吼的回合一格就跨出合格區間，屬數值粒度，交使用者在工坊看。

## 7. 請使用者重開伺服器檢查的重點

- 內容檔沒改，content digest 不變；規則程式改了，進行中的一輪照常。
- 靈感閃現面板：殘影之誓、挑釁怒吼等 7 招用過之後整列灰色虛線框、灰字「這招目前沒有可以閃的變化」，按不下去。
- 戰歌蓄力選項看得到「區域回合 3 → 4」；展翼輕巧看得到 AP 2 → 1 與「獲得技能回合」變少；霜寒之觸、飛行等不再出現「輕巧」。
