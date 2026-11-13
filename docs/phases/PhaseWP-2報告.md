# Phase WP-2 報告｜許願池的 API、面板資料與等待（含插隊）

> 實作 agent，2026-11-13。規格 `docs/phases/PhaseWP計畫.md` 第 4 節；WP-1 報告最後的開發 PM 裁定（待決 3：許願在 pregen 佇列插隊排最前面）。依據 main `7f244f21`（TF-1、WP-1 已合併）。
> 使用者核可：「都按照建議」（專案 PM 轉達）。`docs/design/` 沒動。
> commit：`1b735475`（API、面板、等待、插隊、測試）、`85674148`（OpenAPI 與前端型別、主城物件在 WP-3 前照舊開說明卡）、本報告與上手筆記一筆。

## 1. 做了什麼

| 規格第 4 節 | 做法 | 檔案 |
|---|---|---|
| 1. 請求 | `WorldActionRequest` 加 `WishAction` | `api/world_schemas.py` |
| 2. 面板資料 | `WorldView.wish: WishView \| None`（人在主城才有）：`cost`、`refund`、`coins`、`left`、`per_week`、`available`／`blocked_zh`、`llm`、`text_max_chars`、`max_keywords`、`menu`（`id`、`name_zh`、`description_zh`）、`title_zh`、守池人 `speaker`＋`line_zh` | `api/world_wish_schemas.py`、`api/world_wish_view.py`（新）、`api/world_presenter.py`、`api/routes/world.py::_view` |
| 3. 等待 | `PregenWaitRequest.kind` 加 `"wish"`、`text`、`keywords`；`wish_wait_request` 組和動作同一把鍵的請求 | `api/world_pregen.py`、`api/routes/world.py::post_pregen_wait` |
| 3＋裁定 | **許願插隊**：排在所有還沒開始的預測前面、許願之間照先後、正在跑的不打斷 | `api/world_pregen.py`（`URGENT_KINDS`、`_urgent`／`_normal`、`_take`、`_next`） |
| 4. 主城入口 | `wishing_pool`、`pool_keeper` 加 `panel: wish`；`ObjectPanel` 多 `wish`；說明句換掉「還沒開放」（暫定字） | `content/world/fields/capital/capital.yaml`、`content/fields.py` |
| 給 WP-3 | `PendingOfferView.source`（`quest`／`opportunity`／`wish`）、`refund`（「都不拿（退 N 任務幣）」用） | `api/world_story_schemas.py`、`api/world_story_view.py` |
| 重產 | `scripts/export_openapi.py`、`pnpm -C client gen:api` | `client/openapi.json`、`client/src/api/schema.d.ts` |

小改：`world/wish.py` 多 `wish_refund(library)`（退款數，`apply_wish` 與面板共用）；`api/world_range.py` 的 `_capital_figure` 改公開成 `capital_figure`（守池人頭像共用）。

**前端只動一行**：`client/src/world/atlasModel.ts::objectHud` 略過 `panel === "wish"`（照舊開說明卡）。不改的話 `ObjectPanel` 多了 `wish` 而 `HudPanel` 沒有，`tsc` 會失敗；同 PR-2a 對 `workshop` 的前例。`atlas.test.ts` 加一行鎖住。閃現的檔（`RunFlashPending.tsx`、`flash.ts`、`PopupFrame.tsx`、`flash.css`、`api/flash_changes.py`、`api/flash_text.py`）沒碰。

### 1.1 能不能許（`wish_block`，畫面與等待共用）

依序：戰鬥中（「戰鬥進行中，先打完這場」）→ 待選的閃現 → 待選的三選一（這兩句和 `world_step` 先擋的字相同）→ `wish_problem`（主城、入門期、遭遇、本週次數、任務幣）。所以畫面上的 `blocked_zh` 和送出被拒的字一致（測試 `test_refusal_matches_view`）。

### 1.2 `llm` 欄位

`store.pregen is not None and store.pregen.enabled()`：文字許願只經預先生成的供應者，所以這就是「送文字會不會真的問 LLM」。世界 LLM 關掉或健康檢查說不可用＝`False`，前端只顯示選單。

### 1.3 等待（`kind: "wish"`）

- `text` 先 `strip`，和 `apply_wish` 組同一把鍵（`wish_request`），所以等待排好的那一筆在送出時直接拿（測試：送出時 `pregen.calls` 不增加）。
- 回 `none`：只給 `keywords`（選單許願不呼叫 LLM）、願望空白、超過字數、`wish_block` 不過（例：任務幣不足；不白打 LLM）。
- 逾時照舊 `timeout`（10 秒從第一次等待算起；送出時不再多等，會被拒、不扣錢）。

### 1.4 插隊的做法

`WorldPregen._submit` 不再把 `_run` 直接丟進單一執行緒池；改成每筆 `_Entry` 帶自己的 `Future` 與內容庫視圖，放進 `_urgent`（`kind ∈ URGENT_KINDS = {"wish"}`）或 `_normal` 兩條 deque，再丟一個 `_next` 工作進池子。`_next` 先拿 `_urgent` 再拿 `_normal`，`set_running_or_notify_cancel()` 失敗（已取消：預測換了、`forget`、`_trim`）就略過拿下一筆。仍然只有一條背景執行緒，同一時間一個 LLM 請求；`drain`、`_trim`（看 `future.running()`）、`shutdown`（清兩條 deque）照舊可用。

測試（`tests/api/test_wish_api_wp2.py`）：

- `test_wish_jumps_the_queue`：閃現第一筆卡在 gate（正在跑）、後面排著閃現與機遇；兩個許願用 `wait_seconds=0` 的等待排進去 → 放行後呼叫順序是「第一筆、許願 1、許願 2、其餘預測」，同時進行數最多 1。
- `test_cancelled_wish_is_skipped`：排隊中的許願被 `forget` → 背景執行緒略過，下一個許願照做。

## 2. 測試

新檔 `tests/api/test_wish_api_wp2.py`（12 個，全用 Mock）：插隊 2 個；面板（主城才有、數字、選單扣掉開局隱藏、守池人、`llm` 開關）；選單許願 → 三選一 `source="wish"`、`refund=2`、本週剩 1、任務幣 6，都不拿 → 任務幣 8、次數照扣；任務幣不足時畫面原因＝被拒的字、狀態不變；同週 2 次後 `left=0` 與原因；文字許願先等待（`ready`）再送出（Mock 點燃，至少一張 LLM 卡、沒有再呼叫）；等待的 `none` 情況；對不上被拒不扣錢；`text` 與 `keywords` 同時給被拒。

改的既有測試：`tests/world/test_capital.py`（`panel` 表多兩個 `wish`）、`tests/world/test_capital_figures.py`（守池人的 `panel`）、`client/src/world/atlas.test.ts`（多一行）。

快照：預測會變的只有 OpenAPI（`client/openapi.json`、`schema.d.ts`，已重產，`test_openapi_snapshot` 過）。實際也只有它。版號都沒升（`CHAR_FORMAT`、`WORLD_RULES_VERSION`、`WLOG_FORMAT`、`LOG_FORMAT` 不變：沒改規則與存檔，`ObjectPanel` 多一個值是內容 schema）。

## 3. 檢查（交件前）

| 檢查 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1575 個檔） |
| `uv run lint-imports` | 0（14 kept） |
| `trpg battle --map open_plain --seed 7 --log-json` ＋ `battle replay` | 0／0（91 動作、383 事件一致） |
| `trpg content check` | 0 |
| `pnpm -C client typecheck` | 0 |
| `vitest run src/world/atlas.test.ts src/world/pregen.test.ts` | 0（16 passed） |
| 直接相關 pytest（見下） | 0 |

pytest（`-n 8`，分兩批；`tests/api` 和 `tests/world` 混在同一次跑時 `tests/api/test_pr2a_range_practice.py` 會找不到 `make_client` fixture（只定義在 `tests/api/conftest.py`，這段沒動 conftest；沒在 main 上另外驗證），分開跑全過）：`tests/api/test_wish_api_wp2.py`、`test_wish_pregen.py`、`test_world_pregen.py`、`test_world_pregen_schedule.py`、`test_offer_prefetch.py`、`test_world_story.py`、`test_opportunity_offer_view.py`、`test_pr2a_range_practice.py`、`test_ob5_screen_data.py`、`test_world_api.py`、`test_world_field_api.py`、`test_flash_api.py`、`test_openapi_snapshot.py`；`tests/world/test_capital.py`、`test_capital_figures.py`、`test_wish.py`、`tests/content/test_capital_field.py`、`tests/test_architecture.py`。沒跑全量 `check.py`、沒做數值量測、沒用本機 LLM。

## 4. 待 PM 決定（照最保守的做法做了）

1. **說明卡與守池人的台詞是暫定字**（規格「玩法 PM 給字」，還沒給）：許願池「花任務幣向池子說一句願望，換一份技能三選一；每週次數有限。」、守池人「「說出你想要的力量，池子會回應你。」」。守池人的 `note_zh` 同時當面板標頭下那一句（`WishView.line_zh`），沒另開內容欄位；要分開再加。請玩法 PM 給定稿句。
2. **面板在戰鬥中也給**（`available=False`、原因「戰鬥進行中，先打完這場」），同工坊師傅選單的做法；不在主城才是 `None`。
3. **等待端點不看戰鬥中**：要看得先 `sync`（有副作用）；戰鬥中送動作本來就 409，最多白打一次 LLM。
4. **前端在 WP-3 前點池子照舊開說明卡**（`objectHud` 略過 `wish`），避免型別擋住建置；WP-3 接面板時拿掉這個判斷。
5. **TS 型別的 `WishAction.keywords` 是必填**（pydantic 預設 `()` 在輸出 schema 算必填）：WP-3 送文字許願時帶 `keywords: []`。`PregenWaitRequest.keywords` 改成 `None` 預設，所以既有的閃現、機遇等待呼叫不用改。
6. **許願之間照先後**、只有許願插隊；機遇、閃現、劇情技能的順序不變。

## 5. 需要使用者決定

沒有新的。（價格 4 幣、退 2 已交數值工坊；一次 1 張 LLM 卡開發 PM 已裁定在範圍內。）
