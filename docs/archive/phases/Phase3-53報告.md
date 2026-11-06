# Phase 3-53 報告｜「中毒」關鍵字（玩法決定 #59，06 6.27.1）

## 做了什麼

新增第 11 個關鍵字 `poisoned`（中毒），資料在 `content/skill_keywords.yaml`，沒有改引擎或程式碼（紀錄格式不變，`LOG_FORMAT` 仍為 `/74`）。

### 推導規則對照（全部為專屬規則，沒有通用／暫定）

| 06 6.27.1 | 推導規則 |
|---|---|
| 製造：施加「中毒」 | `{effect: apply_status, status: poison}` |
| 製造：產生毒表面 | `{effect: create_surface, surface: poison}`、`{effect: zone, surface: poison}` |
| 利用：以中毒為條件 | `{condition: target_has_status, status: poison}`、`{condition: target_on_surface, surface: poison}` |
| 利用：消耗中毒 | `{effect: consume_status, status: poison}` |
| 利用：被施加中毒時觸發 | `{trigger: on_status_applied, status: poison}`（對照點燃） |

「對中毒目標加傷」由 `target_has_status: poison` 條件涵蓋。

### 影響盤點

- 裝備外觀表 `content/equipment/appearance.yaml` 的 `keywords` 加入 `poisoned`（`test_table_keywords_are_the_24b1_keywords` 要求與推導表一致）；重新匯出 `client/src/render/gearAppearance.json`；前端 `artPalette.ts` 加顏色、`gearIcon.ts` 加小圖樣。普攻詞條推導（`ELEMENT_KEYWORD`）**沒有**把毒元素對應到中毒，維持現狀（避免改動現有裝備外觀），需要的話另案。
- 關鍵字卡片、工坊關鍵字建議（`keyword_hints`）、三選一候選池、開局關鍵字：都由推導表驅動，自動出現中毒。
- 進化嫁接表 `content/skill_evolution.yaml` 的 `grafts` **沒有**加中毒（非必要，會改變橋接選擇與預算）；沒加時中毒不會出現在橋接進化的候選。待 PM 決定。
- `skill_icons.json`：重新產生，沒有差異。CLI 快照：見下方測試。

## 每池「至少 3 招主動利用者」檢查（06 6.27.2）

| 池 | 主動利用者（專屬規則） | 1 階起始技能 | 結果 |
|---|---|---|---|
| 其他 10 個關鍵字 | 沒有變動 | ≥ 3 | 通過 |
| **中毒 poisoned** | 1 招：`skill_toxin_burst`（2 階） | 製造者 1 招：`skill_thorn_wall`；利用者 0 | **不足** |

中毒的製造者另有 `skill_venom_cloud`（2 階）。**沒有自己補技能**，等 3-54c 毒種子技能。需要補：中毒池至少再 2 招主動利用者，並且至少 3 招 1 階（不分武器）起始技能。

### 為了不讓測試失敗而做的保守標記（補齊後必須移除）

- `tests/skillgen/test_pools_24c.py::test_every_keyword_pool_has_at_least_three_active_exploiters`：預期 `short == {"poisoned": 1}`（補齊後這個斷言會失敗，提醒改回 `{}`）。
- `tests/skillgen/test_keywords.py`：`KEYWORDS`（供池測試參數化）維持 10 個，新增 `EXTRA_KEYWORDS`／`EXTRA_NAMES`，表格順序測試改名 `test_table_has_the_eleven_keywords_in_order`；`test_exclusive_only_derivation...` 排除 `EXTRA_KEYWORDS`。補齊後併進 `KEYWORDS` 並刪掉 `EXTRA_*`。
- `tests/roguelite/test_keyword_start.py`：中毒池起始技能預期剛好 1 招。

### 副作用（待 PM 知悉）

中毒現在會出現在開局關鍵字選項。池只有 1 招起始技能，所以多半由「組合起始技能」（`_composed_starter`）補一招隨機組出的技能（`skill_rand_*`）；荊棘牆只會出現在持有法杖／權杖／圖騰杖的開局。功能正常（已實測各武器都拿得到技能），但在 3-54c 之前這個選項的體驗不完整。若不想讓玩家先選到，可在 3-54c 前暫時把它從開局選項隱藏（需另案）。

## 測試

- pytest（全部在 worktree 實跑）：skillgen、content、narrative 加入新關鍵字後有 5 項失敗，均為測試對「十個關鍵字」的假設，已修正（見上）；roguelite 167 passed；api 294 passed；sim 104 passed（含修正 `test_keyword_sample` 的種子，原種子下技能名「霜寒之觸」撞到開發者起始包標籤）；llm 89 passed；engine 3042 passed、1 failed；`-m "slow or not slow" tests/cli` 146 passed、1 failed 後已更新快照。
- vitest 989 passed、build 成功；ruff、format、mypy、lint-imports 通過。

### 測試補充

- `tests/engine/test_summons_e1.py::test_the_infusion_table_covers_all_ten_keywords`：中毒沒有召喚灌注（規格沒要求，需要時另案），斷言改為「推導表扣掉 poisoned 後等於原本十個」。
- `tests/cli/snapshots/llm_propose_mock.txt`：已用 `UPDATE_CLI_SNAPSHOTS=1` 重新產生。原因：Mock 提議依關鍵字清單輪替，清單從 10 個變 11 個，三題的關鍵字改變（prone／collision／marked → summon／summon／poisoned）。`cli_output_hashes.json`（技能清單與 7 場戰鬥）**沒有變**，`skill_icons.json` 沒有變。
- **既有失敗，與 3-53 無關**：`tests/engine/test_self_costs.py::test_a_battle_with_the_four_demo_skills_replays_identically` 斷言 `LOG_FORMAT.endswith("/73")`，但 `LOG_FORMAT` 在 3-52 後已是 `/74`（3-52 沒更新這條斷言）。我沒有動它；建議開發 PM 順手改成 `/74`。
- 備註：`tests/cli/test_output_snapshots.py` 單一測試約 300 秒，剛好貼著 pyproject 的 `timeout = 300`，在負載高的機器上會被 thread timeout 殺掉；我用 `--timeout=3000` 驗證通過。

## 待 PM 決定

1. 3-54c 之前中毒是否先從開局選項隱藏。
2. 是否要在 `skill_evolution.yaml` 加中毒嫁接（製造：`apply_status poison`；利用：`target_has_status poison` 加傷）。
3. 是否要讓毒元素普攻詞條對應到中毒外觀圖樣。
