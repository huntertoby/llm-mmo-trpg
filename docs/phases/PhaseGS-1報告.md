# Phase GS-1 報告：護主不獨佔（#171）、「形態」只出在主動題（#172）

依據：`docs/phases/PhaseGS-1計畫.md`；`docs/玩法決定紀錄.md` #171、#172；`docs/design/06-技能.md` 6.34.5；`docs/技能空格清單.md`。
基準：main `7ce40274b`。分支 `worktree-agent-aed2cb5d957dfbb21`，沒 push。
沒動 `docs/design/`、`config/`、`llm.toml`、`CLAUDE.md`、`.claude/`，沒改 content 數值（只在 `skill_keywords.yaml` 的形態加了一個旗標，見 3）。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 #171 護主每題只擲一次 | `f5b196882` | `random_composer.guardian_gate`；盤點腳本多記每格的護主數；測試 `tests/skillgen/test_guardian_gate_gs1.py` |
| 2 #172 形態不出在被動、反應題 | `bb5a50b33` | `KeywordDef.active_only`（形態 `true`）＋`KeywordTable.topic_allows`；出題檢查、三選一與許願擲到的種類、白板被動保底；測試 `tests/skillgen/test_form_topic_gs1.py` |
| 3 盤點結果 | `398894a38` | `docs/phases/盤點-2026-11-21/census-gs1-*`（改前、改後、對照表） |
| 報告 | 本 commit | |

規格的第 3 項（測試）分在第 1、2 項的 commit 裡，和各自的實作一起進。

## 2. 受影響的既有功能（開工盤點）

- **出反應技、指定關鍵字的地方**：組合器（`compose_with_stats`／`compose_random_skill` 帶 `keyword`）是唯一的入口。退回路徑 `proposal_fallback._from_composer`、三選一的組合器候選 `candidates.from_composer`、挑選模式 `skill_pick._Composer`／`pick_offer._complete`、許願 `wish_pick._compose`、工坊與測試模式都經 `_compose_with_keyword`，所以 #171 只改這一處就全部適用。白板（`whiteboard.py`）不做護主；閃現轉型的護主（`to_reaction_guardian`）不是出題，不在範圍內。
- **「反應題」的判定**：`_compose_with_keyword` 收到的骨架是 `reaction`（呼叫端傳 `kinds=("reaction",)` 時由 `_kind_skeleton` 轉成同名骨架，或明確指定骨架）。所有遊戲路徑都照這個傳。
- **出題抽關鍵字的地方（#172）**：
  - `proposal_topic.make_topic`（LLM 出題）：形態本來就因 `composable: false` 不出題。
  - `proposal_subset.select_subset`：原本不看 composable，(被動／反應, 形態) 會通過；盤點的「會出題」與 CLI `trpg llm` 都用它。**改這裡。**
  - `candidates.from_composer`、`wish_pick._draw`：種類是擲的（主動 70／被動 20／反應 10），關鍵字另外給；形態在組合器那一步會 `ComposeError` 被跳過。**改成擲到被動、反應時改出主動**（結果不變，只是不再白擲）。
  - `whiteboard_candidates._ensure_passive`：被動保底會試持有、沒持有的關鍵字（可含形態）。**改成跳過形態。**
  - `skill_pick`、`pick_offer`：種類與關鍵字取自原候選；形態的手寫技都是姿態，屬主動那一族，不用改。
  - 許願的玩家指定標籤（`tags.kinds`）照舊：那是玩家選的，不是出題抽的。
- **快照與夾具的預測**：組合器輸出只在「指定關鍵字（非召喚）的反應題」會變。CLI 快照沒有這種指令、parity 夾具（完整技能、升階、閃現）不走這條路、前端夾具不含關鍵字旗標，所以預測**都不變**；規則包多了 `keywords[*].active_only`，預測 78 場戰鬥的內嵌規則包與 `ruleset_hash` 會變、事件不變。實測見 5。

## 3. 做法

### 3.1 #171 護主（`src/trpg/skillgen/random_composer.py`）

- `guardian_gate(seed, keyword, lib, skeleton)`：關鍵字不是 `summon`、骨架是 `reaction` 時，用**題目的種子**、獨立串流 `Rng(seed).fork("composer.guardian")` 以 `recipes.reaction_permille`（250‰）擲一次；其他題回傳 `None`（照舊）。主串流、各變體的串流都沒動。
- `_compose_with_keyword` 在變體迴圈外呼叫一次，把結果（`Guardian = bool | None`）往下傳：`_compose_plain` → `_special_result` → `_compose_special` → `_compose_reaction_recipe`。
- `_compose_reaction_recipe`：
  - `None`：和改前逐字相同。
  - `True`：先用護主配方組（每個變體都先試；組不出來，這個變體再照一般做法，抽配方時不含護主）。
  - `False`：所有變體抽配方時都不含護主（其他配方的 250‰ 照舊）。
- 組配方的部分抽成 `_build_reaction_recipe`（串流 `composer.reaction.recipe.build` 不變）。
- `scripts/recipe_census.py`：`CellResult.guardian`（合法結果裡效果有 `summon_beside` 的反應技個數），「全部格子」表多一欄「護主」。

### 3.2 #172 形態

- `content/skill_keywords.yaml` 形態加 `active_only: true`；`KeywordDef.active_only`（預設 `false`）、`KeywordTable.topic_allows(keyword, kind)`（被動、反應題不收 `active_only` 的關鍵字；未知 ID 回 `True` 交給原本的檢查）。
- `select_subset`：種類是被動、反應而關鍵字有形態時丟 `SubsetError`（LLM 出題退回主動題、盤點標成「不會出題」）。
- `candidates.topic_kinds`：擲到的種類遇到形態時改成主動那一族（`from_composer`、`wish_pick._draw` 沒指定種類時用）。
- `_ensure_passive`：被動保底跳過形態。
- 組合器照舊不做形態（`composable: false` 不變）。

## 4. 盤點（`scripts/recipe_census.py --seeds 200 --workers 4`）

改前用 `git archive 7ce40274b` 的 `src/`、`content/`，加上新版的盤點腳本（只多記護主數）；改後是本分支。兩次都只開 4 個 worker，沒和 `check.py` 或其他盤點同時跑。

- 反應技整列：`--kinds reaction --rarities rare,epic`，17 列 × 4 階 × 2 稀有度＝136 格。
- 帶電被動 1 階史詩：`--kinds passive --keywords charged --tiers 1 --rarities epic`。
- 檔案：`docs/phases/盤點-2026-11-21/census-gs1-reaction(.json/.md)`、`-before`、`census-gs1-reaction-對照.md`（逐格表）、`census-gs1-charged-passive(-before)`。

### 4.1 護主占比摘要（每格 200 種子；稀有、史詩兩格數字相同，合併列）

| 關鍵字 | 階 | 改前 護主／合法 | 改前 占比 | 改後 護主／合法 | 改後 占比 | 設計數 改前 → 改後 |
|---|---|---|---|---|---|---|
| 點燃 ignite | 2 | 185／200 | 92.5% | 58／200 | 29.0% | 12 → 47 |
| 點燃 ignite | 3 | 187／200 | 93.5% | 58／200 | 29.0% | 9 → 42 |
| 潮濕 wet | 2 | 97／200 | 48.5% | 58／200 | 29.0% | 50 → 58 |
| 潮濕 wet | 3 | 97／200 | 48.5% | 58／200 | 29.0% | 38 → 45 |
| 帶電 charged | 2 | 191／200 | 95.5% | 58／192 | 30.2% | 4 → 13 |
| 帶電 charged | 3 | 190／200 | 95.0% | 58／196 | 29.6% | 5 → 13 |
| 帶電 charged | 4 | 191／200 | 95.5% | 58／195 | 29.7% | 4 → 12 |
| 冰凍 frozen | 2 | 186／200 | 93.0% | 58／200 | 29.0% | 8 → 46 |
| 冰凍 frozen | 3 | 186／200 | 93.0% | 58／200 | 29.0% | 8 → 33 |
| 冰凍 frozen | 4 | 184／200 | 92.0% | 58／200 | 29.0% | 7 → 27 |
| 倒地 prone | 1 | 168／200 | 84.0% | 58／200 | 29.0% | 25 → 52 |
| 倒地 prone | 2 | 178／200 | 89.0% | 58／200 | 29.0% | 20 → 62 |
| 倒地 prone | 3 | 188／200 | 94.0% | 58／200 | 29.0% | 11 → 45 |
| 倒地 prone | 4 | 189／200 | 94.5% | 58／200 | 29.0% | 10 → 31 |
| 撞擊 collision | 2 | 149／200 | 74.5% | 58／200 | 29.0% | 40 → 97 |
| 撞擊 collision | 3 | 159／200 | 79.5% | 58／200 | 29.0% | 30 → 81 |
| 撞擊 collision | 4 | 164／200 | 82.0% | 58／200 | 29.0% | 27 → 69 |
| 標記 marked | 2 | 191／200 | 95.5% | 58／199 | 29.1% | 9 → 45 |
| 高處 high_ground | 2 | 97／200 | 48.5% | 58／200 | 29.0% | 65 → 85 |
| 隱蔽 concealed | 2 | 192／200 | 96.0% | 58／198 | 29.3% | 5 → 14 |
| 隱蔽 concealed | 3 | 190／200 | 95.0% | 58／199 | 29.1% | 6 → 16 |
| **召喚 summon** | 1～4 | 200／200 | 100% | 200／200 | 100% | 1 → 1（照舊） |

- 其他格（不指定、中毒、形態、連擊／怒氣／專注／氣，以及上表沒列的階）改前改後護主都是 0，合法數與設計數相同（逐格見對照表）；高處 3～4 階、潮濕 4 階設計數 +1～6 是因為那幾格改前也會抽到護主配方、只是組不出來，現在不擲護主時抽到別的配方。
- **召喚以外最高 30.2%（帶電 2 階），0 格超過 35%**。召喚反應 1～4 階稀有、史詩都是 200／200。
- 會出題的薄格：改前 34 → 改後 10（帶電反應 1 階 ×2，原因是缺「造帶電」的反應配方，空格清單 2.2；召喚 ×8，盤點把召喚物算成同一種設計的假象，空格清單第 3 節）。
- 形態反應 8 格：改前「會出題的空」，改後出題檢查不通過（`reachable: false`），不再算會出題的空格。
- 帶電被動 1 階史詩：改前改後都是 200 合法、15 種設計（正常；#171 不管被動）。

## 5. 其他比對

| 比對 | 結果 |
|---|---|
| 主動列小樣本 `recipe_census.py --seeds 4 --kinds active --workers 4`（204 格，改前程式 vs 改後） | `cells=204 same=204 different=0` |
| 434 招逐招預算（`skill_budget` 全部 dump） | 檔案逐位元組相同 |
| 78 場戰鬥（沿用 HC-2 的 78 場；去掉 `ruleset_hash` 與內嵌規則包） | `battles=78 events=26206 different=0`；內嵌規則包只差 16 筆 `keywords.keywords[i].active_only`（形態 `true`、其他 `false`），原因是規則包內含關鍵字表 |
| parity 夾具（`-m slow tests/skillgen/test_refactor_parity.py`） | 935 passed，不用重產 |
| CLI 快照（`tests/cli`，非 slow） | 通過，不用重產 |
| 前端夾具（`scripts/export_client_fixtures.py`） | 重產後 0 差異 |

快照預測（2 節）與實測一致，沒有重產任何快照或夾具。

## 6. 檢查（全部 commit 後）

| 檢查 | 結束碼 |
|---|---|
| `ruff check`、`ruff format --check`（改到的檔） | 0 |
| `mypy`（改到的檔） | 0 |
| `lint-imports` | 0 |
| `trpg content check` | 0（696 檔、434 技能） |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| 看門狗 `tests/skillgen tests/llm tests/content -n 8` | 0（8636 passed） |
| 看門狗 `tests/cli` 等 4 處 `-n 8` | 0（160 passed） |
| 看門狗 `tests/skillgen/test_guardian_gate_gs1.py`、`test_form_topic_gs1.py` | 0 |
| `scripts/check.py`、slow 測試 | 見 7 |

前端沒改，沒跑 tsc、vitest、build。

## 7. 交件前的完整檢查

照派工：全部 commit 後問開發 PM，依回覆決定（結果補在下方）。

## 8. 待 PM 決定

1. **護主的擲骰只看種子，不看關鍵字**（解讀類，照最保守做）：串流是 `composer.guardian`，同一個種子不論題目是點燃還是冰凍，擲中與否都一樣（所以盤點每格都是 58 個）。遊戲裡每題的種子本來就不同，不影響比例；若想讓不同關鍵字的同種子各自擲，可改成 `composer.guardian/<關鍵字>`。
2. **擲中時「先試護主」是每個種子變體都先試**：組不出合格的護主（或帶不到關鍵字）時，那個變體才走一般做法。實測擲中的題幾乎都交出護主，比例約 25～30%。
3. **少數格合法數小降**：帶電 2～4 階 200 → 192～196、標記 2 階 → 199、隱蔽 2～3 階 → 198～199。沒擲中護主的題要靠其他做法，`search.keyword_tries` 內偶爾做不出來（`keyword_exhausted`）；遊戲裡這時三選一改出主動、退回路徑換下一個種子。要不要補配方（例如空格清單 2.2 的「造帶電」反應配方）另排。
4. **形態旗標放在關鍵字表**（`KeywordDef.active_only`）：因為規則包含關鍵字表，戰鬥紀錄的內嵌規則包和 `ruleset_hash` 會變（事件不變）。若希望規則包不動，可改放 `skill_composer.yaml`（例如 `llm_topic` 底下的清單）。
5. **「反應題」只認骨架 `reaction`**：呼叫端不指定種類（`kinds=None`）時，組合器偶爾也會組出反應技，那種題不算反應題，護主照舊和其他配方一起抽。遊戲路徑都有指定種類，影響只在 CLI `skills random --keyword` 這類工具。
6. 第 1 項的盤點腳本改動（護主欄）和 #171 放在同一個 commit。
