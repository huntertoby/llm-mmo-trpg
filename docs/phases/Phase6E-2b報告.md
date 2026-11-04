# Phase 6E-2b 報告：路徑預覽涵蓋冰面滑倒與其他分歧點的組合

## 問題

全量時 hypothesis 抽到：

```
surfaces=[(2, 1, 'ice')], moves=[(1, 0), (1, 0), (0, 1)], seed=0, trap=True
→ 實走停在 (2, 2)，但預覽 stop = worst_stop = (2, 1)
```

## 原因

路徑預覽只跑兩次模擬：「最少後果」（所有檢定、抵抗對移動者有利）與「最多後果」（全部不利），只涵蓋
「全部有利／全部不利」兩個極端。冰面滑倒是另一個獨立的分歧點，與陷阱抵抗等組合時會漏掉中間情況：

- 這個反例：陷阱就在冰面最後一格 (2, 1)。最少後果＝陷阱抵抗成功＋冰面通過 → (2, 1)；最多後果＝陷阱
  定身成功 → 被定身後不擲冰面檢定 → (2, 1)。實走的「陷阱抵抗成功＋冰面失敗」滑到冰外 (2, 2)，兩次模擬
  都沒有。`slip_runs` 的小牌（「這段失敗、其餘最少後果」的模擬）其實算對了 (2, 2)，但沒有進 `worst_stop`。
- 同類的漏洞（本機確認實走會發生）：冰在陷阱前 → 「過了冰＋陷阱定身」停在陷阱格，最少（走到底）、
  最多（冰上就滑倒）都不是；兩段冰 → 「第一段過、第二段失敗」的停點也不在兩個欄位裡。

後兩種會有 **三種以上** 的實走停點，`stop`／`worst_stop` 兩個欄位在原理上放不下，所以「實際停點必在
`stop` 或 `worst_stop` 之一」對多段冰、冰＋陷阱在一般情況下無法成立（見待決 1）。

## 修法（只動 `src/trpg/engine/path_preview.py`；引擎結算、`LOG_FORMAT` 不變）

1. **冰面分支模擬**：最少後果擲了 N 次滑行檢定時另跑
   - 全部通過 × 其餘最多後果（抓「過了冰＋陷阱定身」）；
   - 第 k 次失敗（之前的通過）× 其餘最少後果（原有的 `simulate_slide_failure`，小牌共用，依 k 快取）；
   - 第 k 次失敗 × 其餘最多後果。

   共 2N＋1 次額外模擬；沒有冰面檢定（或預覽本來就確定）時不跑。「其餘最多後果、冰面照指定」用
   path_preview 內的 `_SlidePassCtx`（`Ctx` 子類別，覆寫 `check_d20`：`slide_checks` 剛增加的呼叫就是
   滑行檢定，回傳 20 通過；被推進冰面的檢定照 max）。這依賴 `ice_slide._roll` 的呼叫順序，docstring 有寫
   明；因為限制只能動 path_preview，沒有在引擎加正式參數（見待決 2）。
2. **`PathPreview.stops`**（新欄位，預設 `()`）：所有分支的停點，不重複，`stop` 在前。
3. **`worst_stop`**：仍是最多後果的停點；它與 `stop` 相同但其他分支停在別處時，改取 `stops` 中第一個
   不同的停點（反例因此變成 `worst_stop = (2, 2)`）。只有兩種停點時，實走必在 `stop`／`worst_stop` 之一。
4. **`stop_certain`**：`stop == worst_stop` 且 `stops` 只有一個。
5. **每格事件與 `reach`**：分支的事件併入每一格（`_merge_all`／`_fold`）——不在所有分支出現的改「可能」，
   只在分支出現的加在後面（「可能」，傷害沒有最小值）；同一件事的傷害範圍取聯集。`reach` 改看所有
   分支走了幾步。`certain`（整體）仍是「最少後果沒經過分歧點」，與實走一致的保證不變。

API（`api/path_schemas.py`）沒有改：`stops` 目前只在引擎層；前端沒有用到 `worst_stop`／`stop_certain`
（只在 vitest 的假資料裡出現），小牌畫法依 `slip_runs`，不受影響，所以沒有動 client、沒有跑 vitest。

## 回歸測試（`tests/engine/test_path_preview.py`）

- hypothesis 性質測試加兩個 `@example`：題目的反例，以及「冰在陷阱前」的三停點案例。
- 新表格 `test_ice_branches_cover_every_walked_stop`（`trap_on_last_ice`、`ice_then_trap`、`ice_trap_ice`）：
  檢查 `stops` 與 `worst_stop` 的值，並用 120 個種子實走，實走停點集合 **等於** `set(stops)`。
- `_assert_matches_walk` 加強：`stops[0] == stop`、`worst_stop ∈ stops`、實走停點 `∈ stops`；`stops` 只有
  兩個以下時實走必在 `stop`／`worst_stop` 之一；`stop_certain ⇔ len(stops) == 1`；確定時 `stops == (stop,)`。
- 預設 `max_examples` 維持 40。

## 驗證

- 相關測試：`tests/engine/test_path_preview.py tests/engine/test_ice_slide.py tests/api/test_path_preview_api.py`
  52 通過。
- 大例數（只在本機，scratchpad 的臨時測試，不進 repo）：原性質測試的策略 `max_examples=2000` 通過；另一組
  冰面加重（表面 3/5 是冰、最多 10 格）的 `max_examples=2000` 也通過，沒有其他反例。
- `ruff check`、`ruff format --check`、`mypy src`、`lint-imports`（13 kept）通過。
- 重播：swamp 種子 7（88 動作、313 事件）、frozen_lake 種子 7（91 動作、378 事件）一致。

## 待 PM 決定

1. **兩個欄位放不下所有停點**：多段冰、冰＋陷阱時實走可能有三種以上停點，題目要求的「必在 `stop` 或
   `worst_stop` 之一」只在兩種停點時成立；一般情況的保證改為「必在 `stops` 之中」。要不要把 `stops`
   加進 API（`PathPreviewOut`，需重產 `openapi.json`／`schema.d.ts`）、前端要不要畫第三個以上的可能停點，
   請 PM 決定；目前保守地只放引擎層。
2. **`_SlidePassCtx` 依賴 `ice_slide._roll` 的呼叫順序**：較乾淨的做法是在 `Ctx`／`ice_slide`／`battle` 加
   「其他滑行檢定一律通過」的正式預覽參數（純預覽，不影響結算），但超出這段允許的檔案範圍。若要改，
   建議下段順手做。
3. **仍不涵蓋的組合**（設計上兩次極端模擬本來就有的限制，非這段新增）：看不見的陷阱；多個互相獨立的
   非冰面分歧點（例如兩個陷阱各自抵抗、藉機攻擊命中＋陷阱抵抗）的混合結果。hypothesis 測試只有一個
   陷阱，所以沒有抽到。
4. 效能：有 N 次冰面檢定的路徑多 2N＋1 次模擬（原本 N 次）；路徑短，預期可接受，沒有量測。
