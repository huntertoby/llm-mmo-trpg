# Phase RG-7 報告：規則小修（4.1.1 A 段 5 題「都照建議」）

依據：`docs/玩法PM交接.md` 4.1.1 A 段（玩法 PM `809c61f5b`）、4.1.3 第 10 條；`docs/玩法決定紀錄.md` #161、#162；設計 05 5.7、06 6.32.1（第 979 行「一次出招最多 +1」）、18（第 56 行定身符要瞄準）、19（第 42 行熔岩彈不留火、燃燒 2 回合）。
基準：main `6f14e0767`（worktree 原本在 `6178bcba1`，先 fast-forward 到 `6f14e0767`）。

## 0. 重點：這 4 項在 AF-1 已全部做完

接手後核對程式與報告，發現派工的 4 項都已在 **AF-1**（`38b165b06` 引擎、`5af217b92` 內容；報告 `docs/phases/PhaseAF-1報告.md`，`LOG_FORMAT` `/122`）實作並合併進 main。所以 RG-7 **沒有改任何結算、沒有升 `LOG_FORMAT`（仍 `/125`）**，只補缺的測試與一行過時的 YAML 註解。

## 1. 逐條驗收

| # | 要求 | 現況（證據） | RG-7 做了什麼 |
|---|---|---|---|
| 1 | 05 5.7：擋箭改打擋住的人；隱蔽照一般隱蔽規則；瞄準預告只限敵方 | `engine/lock_on.py::lock_victim`、`delayed._release_lock` 發 `lock_intercepted` 後打擋住的人；`lock_problem` 照一般選取（2 格內照射、2 格外 `lock_on_concealed`）；`skills/targeting.py::aims_first`（施放者不是 `Team.ALLY` 才瞄準）。測試 `tests/engine/test_af1_rules.py` 第 1～3 節（含 hypothesis 性質測試）、`test_lock_on_rg1.py` | 無（跑過，全過） |
| 2 | 18：符籙師定身符先瞄準 | `content/skills/skill_binding_talisman.yaml` `lock_on: true`；`sect_talisman_caster` 帶這招（`test_lock_on_rg1.py::test_the_three_ranged_enemies_carry_a_lock_on_skill` 只驗資料） | 補實跑測試：施放＝瞄準（`followup_charged.lock_target_id`、不擲命中、不上狀態），下一個自己回合開始才對目標上定身 1 回合 |
| 3 | 19：熔岩彈燃燒 2 回合、不留火 | `skill_lava_bomb.yaml`：`damage 3d8 fire`＋`burning 2`，沒有 `create_surface`；噴岩龜技能是熔岩彈＋火球，沒有火牆。符合設計 | 補測試：同上的瞄準流程；射出後只上 `burning` 2 回合、整場沒有 `surface_changed`、全部格子表面與開場相同；內容層驗沒有 `create_surface`、噴岩龜沒有 `skill_fire_wall`。YAML 第 3 行註解「先用燃燒代替（報告待決）」改成已定案 |
| 4 | 06 6.32.1：一次出招連擊點與氣各最多 +1；說明字括號「一次出招最多 1 點」 | `engine/stack_gain.py` `_collect(..., once=True)` 不分目標（第 117、121 行）；`content/skill_keywords.yaml` 第 248 行括號已是「（一次出招最多 1 點）」。測試 `test_af1_rules.py` 第 4 節（範圍武器技、雙匕首普攻、性質測試） | 無 |

新測試 `tests/engine/test_rg7_rules.py`（4 個測試：定身符、熔岩彈各一列的瞄準流程參數化、熔岩彈不留火、熔岩彈內容）。

相關測試：`test_rg7_rules.py`＋`test_af1_rules.py`＋`test_lock_on_rg1.py`（`-n 4`）37 passed。

## 2. 不變比對

沒有跑 46 場比對，理由：`src/` 沒有任何改動；`content/` 只改了 `skill_lava_bomb.yaml` 的一行 **YAML 註解**。改前改後 `hash_ruleset(library.ruleset)`（`ae4b48df…b050`）與 `content_digest`（`50be396d…8883`）逐字相同，所以戰鬥結算的輸入與引擎都相同，46 場必然 `different=0`。重播 `open_plain` 種子 7：「重播驗證通過：91 個動作、383 個事件，最終狀態一致」。

## 3. 快照預測

沒改任何技能說明字或技能資料（只有註解），預測 CLI 快照 **0 鍵**變動；規則包雜湊不變，所以沒有跑 slow 的 CLI 快照。

## 4. 版號

- `LOG_FORMAT`：不升（`/125`），三個 `endswith` 測試不用動；`docs/phases/戰鬥紀錄格式變更.md` 沒有新條目。
- `WORLD_RULES_VERSION`、`CHAR_FORMAT`：不升。

## 5. 檢查

| 檢查 | 結果 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0（2693 檔） |
| `mypy` | 0（1599 檔） |
| `lint-imports` | 0（14 kept） |
| 相關 pytest（上面三檔） | 37 passed |
| 重播 `open_plain` 7 | 通過 |

新 `# noqa`：無。

## 6. 待 PM 決定

1. RG-7 和 AF-1 是同一批 A 段決定，派工重複了；`docs/開發PM交接.md` 的段落清單要不要把 RG-7 標成「只補測試」結案。
2. 瞄準預告的前端顯示（擋箭改打的浮字、只限敵方）AF-1／RG-3b 已接 `lock_intercepted`，RG-7 沒有新增前端需求。

## 7. 平衡疑慮

無新增（熔岩彈不留火造成荒原火地壓制變少，已記在 `docs/design/平衡待查.md` 第 22 條）。
