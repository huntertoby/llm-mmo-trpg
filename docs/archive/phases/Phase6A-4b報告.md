# Phase 6A-4b 報告：戰鬥 D 版②——伺服器的路徑預覽

依據：`docs/phases/Phase6計畫.md` 第 1 節 6A-4b 列；`docs/design/05-戰鬥.md` 5.10（#121）；`docs/archive/art/戰鬥D版樣張.md` 第 3、6 節。

## 1. 交付內容

| 項目 | 檔案 |
|---|---|
| 引擎唯讀路徑預覽 `preview_path(state, unit_id, *, path=…, dest=…) -> PathPreview` | `src/trpg/engine/path_preview.py`（新檔） |
| API `POST /api/battles/{id}/path-preview`（走 `owned_battle` → `check_owner`） | `src/trpg/api/routes/battles.py`、`src/trpg/api/sessions.py`（`BattleSession.preview_path`）、`src/trpg/api/path_schemas.py`（新檔） |
| OpenAPI 重產、前端型別 | `client/openapi.json`、`client/src/api/schema.d.ts`（只有產生的型別，`tsc --noEmit` 通過） |
| 測試 | `tests/engine/test_path_preview.py`（新）、`tests/api/test_path_preview_api.py`（新）、`tests/api/test_owner_guard.py`（擁有者檢查表加一列） |

**既有的引擎檔案一個都沒改**（只新增 `path_preview.py`），結算行為與 `LOG_FORMAT` 不變。

## 2. 做法

- 與現有預覽（`engine/preview.py`）相同：在狀態複本上用 `simulate_preview` 跑「最少後果」（`min`：檢定通過、藉機攻擊落空、傷害骰最小）與「最多後果」（`max`：檢定失敗、命中、傷害骰最大、prompt 反應使用）兩次。`FixedRng` 不消耗亂數，**不擲骰**；傳入的狀態與 `rng_state` 不變（hypothesis 驗證）。
- 兩次模擬都有的事件＝`certain`，只有一邊的＝`possible`（傷害只在 `max` 出現時 `amount_min` 為 `null`）。整次預覽沒經過任何分歧點時 `certain: true`，保證與實走完全一致。
- 事件記在「當時所在的格子」：離開一格引發的藉機攻擊記在離開的那一格；之後的表面、陷阱、反應記在走進的那一格。
- 路徑不合法時，用 `plan_move`（與實際結算同一套檢查）找**最長的合法前段**模擬，之後的格子 `reach: "unreachable"`，`reason` 是完整路徑不合法的原因（中文）。只給 `dest` 時：本回合走得到取最短路徑；走不到取不限成本的最短路徑（前段標得出走到哪）；完全沒有路時回傳「起點＋終點」，終點標到不了。
- 隱藏陷阱：先 `strip_hidden_traps`（與一般預覽同），看不見的陷阱不出現在預覽，避免洩漏。

### 回應欄位（`PathPreviewOut`）

- `path`、`legal_length`、`reachable`、`reason`、`move_cost`
- `stop`（骰子有利時的停點）、`worst_stop`（骰子不利時）、`stop_certain`、`certain`
- `steps[]`：`pos`、`index`、`surface`（冰／火／油／水＝潮濕／毒……，畫分段顏色用）、`trap`（看得見的敵方陷阱）、`reach`（`certain`／`possible`／`interrupted`／`unreachable`）、`events[]`
- `events[]`：`kind`（`stood_up`、`surface`、`slip_check`、`trap`、`damage`、`status`、`reaction`、`displaced`、`surface_changed`、`fell`、`deadly`、`downed`、`escaped`、`stopped`）、`certain`、`other_id`、`status_id`、`surface`、`pos`、`amount_min／max`、`chance_permille`（滑倒失敗機率，精確窮舉 d20）、`detail`
- 請求：`{path}` 或 `{dest}` 恰好一個（否則 422）；`unit_id` 省略為主角，不是主角 400；不是自己的戰鬥 404；不在等主角動作 409。

小牌文字（「滑 1 格」「陷阱 −8・定身」「點燃」「潮濕」）由 6A-4c 依這些欄位組；規則判斷都在伺服器。

## 3. 測試與檢查

- `tests/engine/test_path_preview.py`：18 通過。表格「預覽＝實走」9 例：一般地面、冰面（通過／滑倒）、冰面在友軍格滑倒滑回空格、冰面後撞牆（到不了）、被敵人擋住、移動點數不足、已發現陷阱（傷害範圍、定身可能）、火→油→水（點燃確定、潮濕看表面）、離開相鄰敵人（藉機攻擊可能）。另有 d20 兩個極端與實走的停點一致、滑倒機率＝窮舉實走、隱藏陷阱不洩漏、`dest` 模式、錯誤輸入；hypothesis（40 例，本機另跑 400 例通過）：隨機表面／陷阱／路徑，預覽前後 `state_to_json` 與 `rng_state` 完全相同，且確定時與實走逐格一致。
- `tests/api/test_path_preview_api.py` 3 通過；`test_owner_guard.py`、`test_openapi_snapshot.py` 通過（相關合計 160 passed、1 skipped）。
- `ruff check`、`ruff format --check`、`mypy src`（498 檔）、`lint-imports`（13 kept）通過；`corepack pnpm -C client typecheck` 通過。
- swamp 種子 7 重播：通過（88 個動作、313 個事件，最終狀態一致）。
- 複雜度：`_convert_own`（單純的事件型別分派）加了 `# noqa: PLR0911`，其餘沒有 noqa。
- 為了跑 `gen:api`，在這個 worktree 執行了 `corepack pnpm -C client install --frozen-lockfile --prefer-offline`（照 lockfile 安裝，沒有新增相依；`node_modules` 不進版控）。

## 4. 待 PM 決定

1. **規則沒有「冰上滑行多格」**：現行冰面是進入時的敏捷檢定（DC 12），失敗倒地並停在冰上；只有倒在友軍格時會滑回最近的空格（`_slide_back_if_stacked`）。所以預覽回報「滑倒機率＋失敗時停點」，沒有「滑幾格」；規格與樣張的「滑 N 格」「撞牆／撞單位停下」在現行規則下不存在（設計 5.10 也寫明規則不改）。表格測試以「冰後撞牆＝到不了」「冰在友軍格＝滑回」代替。若要真的滑行，是規則變更，需回到使用者。
2. **陷阱定身的抵抗**：陷阱狀態照常擲抵抗，預覽把定身標成「可能」，不附機率（目前只給滑倒的 `chance_permille`）。若小牌要顯示定身機率，可以下一段加（`preview.status_save_chance` 可重用）。
3. **藉機攻擊的傷害**只在最多後果出現，`amount_min` 為 `null`、`amount_max` 為最大骰；不給命中率。保守做法，需要時再加。
4. 只能預覽**主角**（與 `/preview` 一致）；預覽隊友或召喚物的路徑要另開。
5. 「到不了」的完整路徑只給第一個不合法原因（例如「移動點數不足：需要 6，剩餘 5」）。
