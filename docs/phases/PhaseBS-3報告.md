# Phase BS-3 報告：照 06 §6.21.1「BS-1 後的細節」調整

> 規格：`docs/design/06-技能.md` 6.21.1「BS-1 後的細節」（玩法 PM 2026-11-13 定，第 539～544 行）；`docs/phases/PhaseBS-1報告.md` 待決 1、3 與第 9 節。開工時 `git merge --ff-only main`（`810ec27e3`）。

## 1. 五點對照

| 細節 | 本段 |
|---|---|
| 1. 「接下來 N 回合」＝施放那回合剩下＋之後 N 個自己的回合 | **改**：影纏資料持續值 2 → 3；卡片與預覽仍顯示「2 回合」（見第 2 節） |
| 2. 技能要帶隱蔽，可以同時帶別的關鍵字 | **改**：放寬 `silent_strike_problems`（見第 3 節） |
| 3. 看實際出手的武器、化形的天生武器不算 | BS-1 已照做（`modifiers.silent_strike` 看 `unit.weapon`；`test_quiet_strikes_bs1.py` 有形態測試），確認不改 |
| 4. 只對普攻、武器技、反應攻擊 | BS-1 已照做（`quiet_strikes.no_turn_reason` 只算普攻與 `category: weapon`；B 不分類別），確認不改 |
| 5. 守護者攔下時也不轉 | BS-1 已照做（`test_a_guardian_who_takes_a_silent_strike_does_not_turn`），確認不改 |

## 2. 影纏「2 個完整的自己回合」

- `content/skills/skill_shadow_bind.yaml`：`grant_skill` 的 `duration: 2 → 3`（`grant_skill` 在持有者回合結束時倒數，給自己時施放那回合就先扣 1）。檔頭註解寫明。
- 顯示：`trpg.content.skills.silent_rounds_shown(granted, duration, *, to_self)`（`queries.py`）——**只有「給自己的無聲」**（`is_silent_grant` 而且對象是自己）回傳資料 − 1，其他回 `None` 照資料顯示。
  - 卡片（`narrative/skills.py::_grant_skill`，`affects: self` 時）：「接下來 2 回合獲得「無聲步」（施放這回合剩下的部分，再加上之後 2 個自己的回合；不佔技能欄位，重新施放只刷新回合數）」。
  - 預覽（`engine/preview.py::_grant_infos` 多傳行動者，獲得者就是行動者時）：`grants[].duration` 為 2。
  - 飛行（`skill_wing_spread` 等）照舊「持續 3 輪」（有測試鎖）。
- 沒改（照資料值 3）：預算、戰鬥紀錄文字「（3 輪，在 X 的回合結束時倒數）」、HUD「剩 N 輪」、數值工坊的 `effects[1].duration`（見待決）。
- **預算**：`trpg skills budget skill_shadow_bind` 71.2% → **74.5%**（給無聲 3 回合 × 0.6 = 1.8，條件 ×0.85 → 1.53），仍合格，**倍率 1450 不必調**，沒動。
- `trpg content check`：通過（409 個技能）。

## 3. 無聲的來源放寬

`src/trpg/content/silent_strike.py::silent_strike_problems`：無聲本身（`silent_strike` 修正規則、給無聲技能的 `grant_skill`）在 `skill_keywords.yaml` 推導成隱蔽，所以先用 `_without_silence` 拿掉這兩種事實，再推導其餘部分的專屬關鍵字：

- 沒有任何專屬關鍵字（技能的主題只有無聲：無聲步、影纏）→ 通過；
- 有而且含 `concealed`（毒＋暗影傷害、火＋上隱蔽）→ 通過；
- 有但不含隱蔽（只有毒、只有火）→ 擋，訊息列出中文關鍵字名（「……除了無聲以外的專屬關鍵字是：中毒，沒有隱蔽」）。

三處驗證：內容載入（`skill_checks`）與 `validate_skill`（`silent_strike.source`，LLM 提議、工坊、白板共用）都呼叫這個函式，改一處兩邊生效；詞條授予（`gear_checks._action_problems`）仍用 `carries_silent`，**給出的技能就算是隱蔽主題也一律擋**（設計：不做成詞條）。武器特性是固定清單，結構上放不進去（同 BS-1）。

## 4. 測試

| 檔案 | 內容 |
|---|---|
| `tests/skillgen/test_silent_strike_bs3.py`（新，6） | 毒＋隱蔽（暗影傷害＋上毒＋給無聲）通過、`validate_skill` 不報 `silent_strike.source`；只有毒帶無聲 → 擋（訊息含「中毒」、規則碼）；火＋上隱蔽通過、只有火擋；無聲步加「帶火」修正仍擋；兩招示範通過；詞條授予影纏仍擋 |
| `tests/engine/test_shadow_bind_rounds_bs3.py`（新，4） | 施放後剩 3；施放那回合結束後兩個自己的回合都有無聲（剩 2、1，背後普攻 `no_turn: silent`），第二個回合結束後消失、普攻不再無聲；期滿事件；卡片「接下來 2 回合獲得「無聲步」」、預覽 `grants` 為 2；飛行卡片仍「持續 3 輪」 |
| `tests/engine/test_quiet_strikes_bs1.py` | `SkillGranted.duration` 斷言 2 → 3（資料值） |

BS-1 的 `test_silent_strike_bs1.py`（火焰版影纏、無聲步帶火被擋）不改仍通過。

## 5. 不變比對

腳本在 scratchpad（`bs3/invariance.py`，不進 repo）：`sim.batch.map_spec`＋`run_battle`，存整份紀錄去掉 `format`、`ruleset_hash`、`setup.ruleset`、`final_state.ruleset`；改前用 `git archive HEAD src content`（`810ec27e3`）、`PYTHONPATH` 指過去。8 張圖（`molten_heart_pit`、`rift_gate`、`cloud_summit`、`open_plain`、`bandit_lair`、`oil_depot`、`lava_crossing`、`swamp`）× 種子 1、2 ＋ 3 張頭目圖 × 種子 3～12。

**`battles=46 events=20499 different=0`**。46 場都沒有影纏（紀錄裡沒有 `skill_shadow_bind`），全部逐字相同。

## 6. 快照與 parity

先預測：影纏的卡片文字變 → `skills_list` 與含影纏的 `skills show` 分片（409 招每片 26 招，影纏在第 10 片）；parity 夾具 `refactor_3wr2.json` 影纏的 `complete` 與 `retier` 兩筆（雜湊含持續值）；戰鬥快照、`llm_propose_mock.txt` 不變。

實際失敗恰好是這 4 個：`skills_list`、`skills_show_all/10`、`test_complete_strength_unchanged[skill_shadow_bind]`、`test_retier_unchanged[skill_shadow_bind]`。只重產這幾個（CLI 用 `UPDATE_CLI_SNAPSHOTS=1` 只跑那兩個鍵；parity 手改那兩筆雜湊）。差異內容核對過：`skills list`／`show` 只有影纏那一行的文字從「讓目標暫時獲得技能「無聲步」，持續 2 輪……」變成「接下來 2 回合獲得「無聲步」……」。

前端夾具（`skill_icons.json`、`skillCards.json`、`glossary.json`）不變（`tests/api/test_client_fixtures.py`、`tests/content/test_icon_prop_qi2d.py` 通過），前端沒改，不跑前端檢查。戰鬥紀錄格式沒變（`trpg-battle-log/119`，`git fetch` 後 origin/main 也是 119），不 bump。

## 7. 檢查結束碼

| 檢查 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0（14 kept） |
| `uv run trpg content check` | 0 |
| `pytest tests/content tests/skillgen tests/engine tests/api -n 8` | 0（12815 passed、15 skipped） |
| `pytest tests/cli/test_output_snapshots.py tests/skillgen/test_refactor_parity.py tests/cli/test_llm_propose_cli.py tests/narrative -m "slow or not slow" -n 8`（重產後） | 0（1405 passed）；重產前 4 failed，即第 6 節預測的 4 個 |

## 8. 待 PM 決定

1. **「沒有其他專屬關鍵字」算隱蔽技能**：無聲本身推導成隱蔽，所以「主題只有無聲」的技能（無聲步、影纏：無元素傷害＋給無聲）照舊通過；有其他主題時才要求另有隱蔽來源。這是讓兩招示範維持合格的最保守讀法。
2. **「2 回合」只在「給自己的無聲」顯示成資料 − 1**：飛行等其他 `grant_skill`、給隊友的無聲照資料顯示。設計第 1 點的「接下來 N 回合」若要推廣到所有給自己的暫時技能（例：展翼 `duration: 3` 會變成顯示 2），要另定。
3. **照資料值（3）沒改顯示的地方**：戰鬥紀錄「（3 輪……）」、施放後 HUD「剩 3 輪」、數值工坊 `effects[1].duration` 顯示 3、預算按 3 回合計（74.5%）。若預算要只算完整回合（2 × 0.6），需改 `_grant_skill_points`。
4. **影纏倍率**：預算升到 74.5% 仍合格，沒調；若要取最低合格值，1350 約 70.0%（未改，交數值工坊）。

## 9. 複雜度例外

無。
