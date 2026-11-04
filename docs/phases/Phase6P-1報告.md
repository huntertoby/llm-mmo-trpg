# Phase 6P-1 報告：收尾小項①（路徑預覽）

處理 6A-4f 待決 1（冰後陷阱的傷害範圍與定身）與 6E-2b 待決 2（`_SlidePassCtx` 依賴呼叫順序）。
引擎正式結算、`LOG_FORMAT`、API 欄位都沒有改。

## 1. 冰後陷阱的傷害範圍與定身

- 檢查結果：6E-2b 加的「全部冰面通過 × 其餘最多後果」分支，已經讓冰後陷阱拿到最大傷害與定身；
  最少後果（冰面本來就通過、陷阱取最小）給最小傷害。`_widen` 把兩者合成 `amount_min`～`amount_max`，
  定身只在最多後果那支出現，所以是「可能」（`certain: false`）。
  - 例：冰 (1,0) → 陷阱 (2,1)：陷阱 `damage 6～14`、`root` 可能（6A-4f 寫的是只有 −6、沒有定身）。
- 不需要再多跑模擬；預覽仍不擲骰、不改狀態與 `rng_state`（測試有檢查）。
- API：`PathEventOut` 原本就有 `amount_min`／`amount_max`／`certain`，**沒有加欄位，OpenAPI 不用重產**。
- 前端：`pathPreview.ts` 本來就照 6A-4f 規格寫「陷阱 −min～max・定身」（冰後不加「（可能）」），
  `pathPreview.test.ts` 已有對應夾具（「陷阱 −6～14・定身」），**沒有改 client**。
  worktree 沒有 `node_modules`，所以沒跑 vitest／tsc。

## 2. `SlideOverride`：冰面檢定結果的正式預覽參數

- `engine/context.py`：新增 `SlideOverride(outcomes: tuple[bool, ...], rest: bool | None)`（frozen dataclass）。
  - 第 i 次滑行檢定照 `outcomes[i]`（通過／失敗）；超出時照 `rest`（`None`＝照預覽模式）。
  - `SlideOverride.fail_at(k, rest=...)`：第 k 次失敗、之前的通過。
  - `Ctx(..., slide_override=...)`：取代原本的 `slide_fail_at` 屬性。正式結算（`preview=None`）傳入時拋 `ValueError`。
- `engine/ice_slide.py` `_roll`：有覆寫且指定了這次結果時，通過回 20、失敗回 1（標記分歧點）；
  其他照 `ctx.check_d20()`。只作用在自己走進冰面的滑行檢定；被推進冰面的檢定（`effects.handlers`）不受影響。
  正式結算的路徑與原本一樣（覆寫為 `None` 時直接 `check_d20()`）。
- `engine/battle.py`：`simulate_slide_failure(base, move, index)` 改成 `simulate_slide_branch(base, move, override, preview="min")`
  （只有 path_preview 在用）。
- `engine/path_preview.py`：刪掉 `_SlidePassCtx` 與 `_simulate_slide_max`，各分支改用 `simulate_slide_branch`：
  - 全部通過 × max：`SlideOverride(rest=True)`；
  - 第 k 次失敗 × min：`SlideOverride.fail_at(k)`；
  - 第 k 次失敗 × max：`SlideOverride.fail_at(k, rest=True)`。

  和舊作法的結果相同（6E-2b 的測試都照舊通過），但不再靠呼叫順序分辨冰面檢定。

## 3. 測試

新增測試：

- `tests/engine/test_path_preview.py`
  - `test_trap_after_ice_damage_range_matches_the_walk`：三個案例（`ice_then_trap`、`ice_trap_ice`、6A-4f 的 `two_ice_then_trap`）。
    - 實走種子 0～299，取「陷阱觸發前沒有滑倒」的實走，陷阱傷害的最小／最大＝預覽的 `amount_min`／`amount_max`（6～14）。
    - 定身在實走中有有無兩種，預覽是「可能」。
    - 預覽前後狀態與 `rng_state` 不變。
  - `test_slide_override_outcomes`：測 `outcome`／`fail_at` 的語意。
  - `test_slide_override_is_preview_only`：正式結算傳覆寫會被拒絕，預設是 `None`。
  - `test_formal_resolve_ignores_previews`：種子 0～19 先做預覽再正式結算，事件與最終狀態跟沒做預覽時完全相同。
  - `test_slide_override_only_forces_slide_checks`：
    - 全部通過 × min 的結果＝最少後果；
    - 全部通過 × max 不會滑倒，被陷阱定身在陷阱格。
- `tests/api/test_path_preview_api.py` `test_path_preview_gives_trap_range_after_ice`：API 回應的冰後陷阱有傷害範圍
  （最小 < 最大、與引擎一致），定身 `certain: false`。

結果：

- `pytest tests/engine tests/api/test_path_preview_api.py tests/api/test_openapi_snapshot.py -n 8`：4163 通過
- hypothesis `test_preview_never_changes_state_and_matches_when_certain`：在本機暫時改成 `max_examples=1000` 跑過一次，通過；已改回 40，沒有 commit。
- ruff、ruff format --check、mypy src、lint-imports：通過。
- 重播：swamp 種子 7（88 動作、313 事件）、frozen_lake 種子 7（91 動作、378 事件）一致。

## 4. 待 PM 決定

1. **6A-4f 待決 1 其實已在 6E-2b 解決**：這段只補上「範圍＝窮舉實走」的驗證與 API 測試，引擎與前端沒有為此改行為。
2. **仍不涵蓋的情況**：「全部通過 × 最多後果」在走到冰後陷阱之前，可能先被別的最多後果打斷，例如：
   - 前面另一個陷阱定身；
   - 藉機攻擊把人擊倒。

   這時後面那個陷阱只有最小傷害。這屬於 6E-2b 待決 3「多個互相獨立的非冰面分歧點」，這段沒有處理。
3. 沒跑 vitest／tsc：client 沒有改，而且 worktree 沒有 `node_modules`。
