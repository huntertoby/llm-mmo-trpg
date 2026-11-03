# Phase 5F-2b 完成報告：5F-2 收尾（霧鎖千山大十字、Boss HP、陣眼標籤中文）

規格：`docs/phases/Phase5計畫.md` 第 1 節 5F-2b 列（玩法 PM 2026-11-03 代決）；背景 `docs/phases/Phase5F-2報告.md`、第 34 節。

## 交付

| 項目 | 檔案 |
|---|---|
| 形狀的「內容專用參數」`ShapeDef.content_params`（選填、必須有 `default`）；`ParamDef.default`；`all_params()`、`with_defaults()`、`param_or_default()` | `src/trpg/content/skills/shapes.py` |
| `ShapeSpec.arm`（十字臂長；沒填時不序列化，舊技能的 JSON／雜湊不變） | `src/trpg/content/skills/effects.py` |
| 驗證器認得 `content_params`（範圍、不接受的參數） | `src/trpg/content/skills/skill.py` |
| 預算、格數套預設值（`zone_cell_count`、形狀倍率、閃現的格數） | `src/trpg/skillgen/budget.py`、`src/trpg/skillgen/flash_ops.py` |
| 引擎幾何：`cross_tiles(state, center, arm=1)`（每臂遇牆或地圖邊緣就停）；`center_tiles(..., arm=)` 讀技能形狀 | `src/trpg/engine/skills/shapes.py`、`src/trpg/engine/skills/targeting.py` |
| 敘述：形狀參數「臂長」 | `src/trpg/narrative/skills.py`、`src/trpg/skillgen/player_text.py` |
| 十字：`content_params.arm`（1–2，預設 1）、格數 `{1: 5, 2: 9}`、預算 `{1: 1800, 2: 2000}‰` | `content/skill_shapes.yaml` |
| 霧鎖千山延遲段 `arm: 2`（9 格）、定身 1 回合不變 | `content/skills/skill_mist_lock_peaks.yaml` |
| 霧鎖真人 HP 90 → 120、陣眼石靈 30 → 40 | `content/units/sect_mist_lock_master.yaml`、`content/units/sect_summit_array_stone.yaml` |
| 同門標籤中文名 `kin_name_zh`（陣法、護陣、分傷三種都可選填；只能和 `kin_tag` 一起寫）；鎖霧大陣填「霧鎖真人」 | `src/trpg/content/battle.py`、`src/trpg/narrative/status_info.py`、`content/statuses.yaml` |
| 模擬腳本加 `--sweep 真人HP:石靈HP,...`（只跑有階段、不改 content） | `scripts/boss_phase_sim.py` |
| 產生檔 | `client/src/battle/fixtures/glossary.json`（鎖霧大陣的規則句） |
| 測試 | `tests/engine/test_shape_cell_counts.py`（臂長格數、遇牆停）、`tests/engine/test_boss_phases.py`（預告 9 格；整場重播種子 1 → 3）、`tests/content/test_skills_content.py`（臂長範圍、其他形狀不接受）、`tests/narrative/test_unit_traits.py`（石靈卡顯示中文、`kin_name_zh` 要有 `kin_tag`）、`tests/content/test_con_hp.py`、`tests/engine/test_earth_54b.py`（改用 `with_defaults`） |
| 夾具 | `tests/skillgen/fixtures/refactor_3wr2.json`：只改 `skill_mist_lock_peaks` 的 complete／retier 兩筆（形狀真的變了）；`tests/cli/snapshots/cli_output_hashes.json`：`skills_list`、`skills_show_all/06` |

## 做法摘要

- **臂長資料化**：十字多一個選填參數 `arm`，放在新的 `content_params`，不放在 `params`。原因：技能生成器（組合器、LLM 提議模型、工作坊選項、閃現）都會掃 `params` 抽參數，放進去會改變亂數流與所有生成結果。`content_params` 只給內建內容寫；驗證器、預算、格數、敘述與引擎都認得，省略就用 `default: 1`，行為和以前一樣。
- **其他十字技能不變**：leap_slam、holy_water 等都沒寫 `arm`，幾何、預算、敘述、序列化都一樣。`refactor_3wr2` 只有霧鎖千山的 2 筆改變，其餘 900 多筆沒變。CLI 快照只有 2 個改變，都是因為霧鎖千山的形狀文字變成「十字（臂長 2，射程 0）」。
- **前端範圍預覽**：前端的影響格（`affected_tiles`）和蓄力預告（`charge_tiles`）都由引擎算好再傳給前端，前端不用改。這兩處都會顯示 9 格。技能圖示（`skillGlyphs`）仍用固定的十字小圖。
- **陣眼標籤中文**：狀態定義新增 `kin_name_zh` 欄位。有填時規則句寫「12 格內的友方「霧鎖真人」（不含自己）」，沒填時照舊寫「帶「sect」標籤的友方」，所以其他單位卡的文字不變。
- **LOG_FORMAT 不遞增**：戰鬥紀錄格式沒變。新欄位都是選填，沒填時不輸出，`exclude_if`。
- **第 4 項確認維持現狀**：「歸一」仍在回合開始時回血（`mist_return` 的 `on_turn_start_heal`，沒改）。一次跌破多個門檻時仍依序全部觸發（`boss_phases._enter` 沒改，`test_threshold_table` 照舊通過）。

## 模擬（`uv run python scripts/boss_phase_sim.py --seeds 40`，方法同 5F-2）

雲頂觀 Boss 地圖，原型三人，雙方都用效用 AI，`max_rounds` 30。現值是真人 120、石靈 40、霧鎖千山 9 格：

| 條件 | 場數 | 勝率 | 平均輪數 | 敗場真人剩餘 HP | 到第 2 階段 | 到第 3 階段 |
|---|---|---|---|---|---|---|
| 1 級・沒有階段 | 40 | 82% | 8.1 | 66% | 0% | 0% |
| 1 級・有階段 | 40 | 25% | 7.8 | 40% | 90% | 47% |
| 6 級・沒有階段 | 40 | 97% | 5.8 | 15% | 0% | 0% |
| 6 級・有階段 | 40 | **62%** | **6.7** | 29% | 100% | 85% |

- 輪數 6.7，有達到 6～10 輪的目標（5F-2 是 5.5）。6 級勝率 62%，**沒達到** 70～80%。
- 1 級勝率 25%，比 5F-2 的 42% 更難。1 級只是原型參考，建議等級是 6。

**候選值掃描**（`--sweep`，都是有階段、6 級、霧鎖千山 9 格；先各跑 40 場，接近目標的再各跑 80 場）：

| 真人／石靈 HP | 40 場勝率 | 40 場輪數 | 80 場勝率 | 80 場輪數 | 1 級勝率（40 場） |
|---|---|---|---|---|---|
| 90／30 | 75% | 5.8 | — | — | 40% |
| 90／40 | 72% | 5.8 | — | — | 40% |
| 100／30 | 85% | 5.9 | — | — | 37% |
| 100／40 | 77% | 6.0 | **72%** | **6.2** | 32% |
| 110／30 | 77% | 6.1 | 68% | 6.1 | 32% |
| 110／40 | 70% | 6.2 | 66% | 6.3 | 30% |
| 120／30 | 72% | 6.4 | **70%** | **6.4** | 27% |
| 120／40（現值） | 62% | 6.7 | 60% | 7.0 | 25% |

- 兩個目標同時達到的只有 **120／30**（70%、6.4 輪）和 **100／40**（72%、6.2 輪），兩者都剛好在目標邊緣。40 場的誤差大約 ±7%。
- 建議值：**真人 120、石靈 30**。理由是保留代決的真人 HP，只把石靈改回 30。另一個選擇是 100／40。content 維持代決值 120／40，請 PM 決定。
- 如果要輪數更接近 6～10 輪的中間：只靠 HP 很難兼顧勝率（HP 越高，輪數越長，勝率也越低）。需要另外動輸出或第 3 階段的回血，本段沒有試。

## 檢查結果

已合併 main（`6d06b3dc`，5F-1 等），合併後跑：

- `ruff check .`、`ruff format --check .`、`mypy`（strict，1180 檔）、`lint-imports`（13 kept）：全部通過。
- `pytest -n 8 tests/engine tests/content tests/narrative tests/world tests/api`：7520 通過。
- `pytest -n 8 tests/skillgen`：3732 通過、14 略過。`-m "slow or not slow"` 跑 `test_budget`、`test_refactor_3wr2`、`tests/sim/test_push_check.py`：910 通過。
- CLI 快照（`-m "slow or not slow"`）：25 通過。`skills_list`、`skills_show_all/06` 已用 `UPDATE_CLI_SNAPSHOTS=1` 重產，原因是霧鎖千山的形狀文字。
- vitest：1272 通過（137 檔）。`pnpm build`：通過。前端原始碼沒有改，只重產了 `glossary.json`。
- 重播：swamp 種子 7 通過（88 動作、313 事件）。雲頂觀種子 3 通過（163 動作、638 事件，兩次階段轉換，三個階段都出現）。
- 沒跑全量、matrix、completion。沒有新增 `# noqa`。

## 代決（照最保守的預設實作）

| # | 事項 | 實作 |
|---|---|---|
| 5F2b-1 | 臂長參數放哪裡 | 新的 `content_params`，生成器、LLM、玩家選項都不提供；`arm` 範圍 1–2，預設 1 |
| 5F2b-2 | 臂長 2 的預算倍率 | 2000‰，和方陣 9 格相同。試過 2200‰，霧鎖千山會頂到預算上限（0.997），閃現「接續段強化」就沒有空間，`test_flash_bal10b` 會失敗 |
| 5F2b-3 | 臂長 2 遇牆 | 每一臂遇到牆壁或地圖邊緣就停在它之前，牆後的格子不算。臂長 1 和以前相同 |
| 5F2b-4 | 驗證器是否限制只有內建技能能寫 `arm` | 不限制來源。生成器本來就產生不出 `arm`，內建技能的閃現或升階衍生版會沿用 `arm` |
| 5F2b-5 | 中文標籤名放哪裡 | 每個同門規格各自寫選填的 `kin_name_zh`，不另開標籤名表；只填鎖霧大陣，`sect`、`sword_array` 照舊顯示 ID |
| 5F2b-6 | 重播測試種子 | `test_summit_battle_runs_all_phases_and_replays` 改用種子 3、4。HP 加高後，種子 1 只打到第 2 階段 |
| 5F2b-7 | 未達標時的數值 | content 維持 120／40，建議值寫在下面 |

## 待 PM 決定

1. **Boss 數值**：現值 6 級勝率 62%、6.7 輪，勝率沒達標。建議**真人 120、石靈 30**（80 場：70%、6.4 輪）；另一個選擇是 100／40（72%、6.2 輪）。只要改 content 的 `max_hp`，`tests/content/test_con_hp.py` 也要跟著改。
2. **臂長 2 的預算倍率 2000‰**（5F2b-2）是初值。如果認為大十字應該比方陣貴，要同時處理霧鎖千山頂到上限的問題，例如降傷害骰。
3. **玩家技能能不能有大十字**：現在只有內建內容能寫 `arm`。要開放給生成器或 LLM 的話，把 `arm` 從 `content_params` 移到 `params`，但所有生成結果都會改變，夾具與快照要重產。
4. **其他同門標籤**（`sect`、`sword_array`）在卡片上仍顯示英文 ID。要中文的話，在 `content/statuses.yaml` 補 `kin_name_zh` 即可，例如「同門」「劍陣弟子」。名稱由玩法 PM 決定。
5. **1 級勝率 25%**：雲頂觀建議等級是 6，1 級只是參考。如果 1 級也要能打，需要另外處理。
6. **技能圖示**：霧鎖千山的圖示仍是一般十字小圖，要不要畫大十字是美術的事。
