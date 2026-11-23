# Phase WM-1 報告：大世界走路不黏腳

依據：`docs/phases/PhaseWM-1計畫.md`、`docs/phases/WM-1調查.md`。起點 main `7465ee738`。
沒碰 `content/`、`src/trpg/engine/`、`content/equipment.py`、`config/`、`docs/design/`、CLAUDE.md。不改規則、不改數值；存檔照舊同步寫入。

## 1. 做了什麼（每項一個 commit）

| # | 項目 | commit | 檔案 |
|---|---|---|---|
| 1 | **按住連走**：`keydown`（濾掉 `e.repeat`）／`keyup`／`blur`／`visibilitychange` 記住「正在按哪個方向」（最後按的優先，點一下也走一格）；走路迴圈每播完一格才問一次還有沒有按著。拿掉作業系統重複＋`KEY_QUEUE_MAX = 3` 的排隊。 | `09f24d368` | `client/src/world/heldKeys.ts`（新）、`WorldField.tsx`、`heldKeys.test.ts`（新） |
| 2 | **前端先走**：方向鍵走路改由 `WalkAhead` 跑——主角用 `canStep` 先滑，請求在背景照順序送（同時一個）；最多領先 2 格，看得到敵人（伺服器已過濾的 `field.enemies` 有人）最多 1 格。回應對得上就套用整份畫面（主角畫在畫面上站的格子），對不上（遇敵、位置不同、換地圖、請求失敗）就停送、主角**滑回**伺服器的格子（沿原路倒退，不在路上就直接滑過去；`forced` 位移、不轉身）、再套用伺服器畫面。出口、門、傳送石不先走：前面都確認了才照舊流程送。套用畫面用 `flushSync` 同步重畫，下一格動畫才找得到小人。 | `2e7562068` | `client/src/world/walkAhead.ts`（新）、`walkAhead.config.json`（新）、`WorldField.tsx`、`heldKeys.ts`、`walkAhead.test.ts`（新） |
| 3 | **伺服器加速**：`hero_panel` 照「內容庫視圖（同一個物件）＋整份 `as_run` 的 `RunState` JSON＋角色裝備 JSON」快取（LRU 64 份、加鎖；回傳模型是凍結的）。技能、等級、屬性、閃現、待選閃現、技能種子都在 `RunState` 裡，任何一樣變了就是新鍵。 | `24612f4b3` | `src/trpg/api/world_growth_view.py`、`tests/api/test_wm1_walk.py`（新） |
| 4 | **地點事件先回畫面**：`walk` 而且世界 LLM 會真的呼叫時（`client` 不是 `None`），`act_with_story` 不在同一個請求裡寫旁白；`EventView.story_pending` 為真，前端畫占位「說書人正在構思這段故事……」並另外送新的 `POST /api/world/characters/{id}/event_story`（照舊 `narrate_event` → `event_story` → 寫一個 `narrate` 動作進日誌）。回來只換畫面的 `event` 一塊。LLM 關著時照舊同一個請求寫模板旁白（`story_pending` 為假）。 | `c3079f76f` | `src/trpg/api/world_flow.py`、`routes/world.py`、`world_story_schemas.py`、`world_story_view.py`、`client/openapi.json`、`client/src/api/schema.d.ts`、`api/client.ts`、`screens/WorldScreen.tsx`、`world/EventCard.tsx`、`world/eventStory.ts`（新）、`styles/world.css`、`eventStory.test.ts`（新）、`tests/api/test_wm1_walk.py`；四個前端假資料補 `story_pending: false` |

### 領先上限的設定放哪

放**前端設定檔** `client/src/world/walkAhead.config.json`（`lead_max: 2`、`lead_max_enemy_seen: 1`），由 `walkAhead.ts` 匯入。理由：這是前端演出的參數，不是規則；放伺服器要動 `content/world/rules.yaml`（規則資料）、schema 與 OpenAPI，改動比較大。

### 開發用慢動作（為了拍連續截圖新增）

`?dev=1&walkms=N`：方向鍵先走與拉回每格 N 毫秒（只在開發模式生效，正式畫面照 `STEP_MS = 120`）。

## 2. 測試

- 前端（vitest，node 環境沒有元件測試，所以把走路迴圈抽成 `WalkAhead`、用假伺服器與假時鐘測）：
  - 按住連走第 1、2 步之間不停頓（每 120 ms 一格：0／120／240／360）、請求同時只有一個；
  - 放開後最多只走完正在播的那一格；點一下只走一格；
  - 伺服器慢時最多領先 2 格；看得到敵人時最多 1 格；
  - 對不上：遇敵時不送第 2 格、沿原路滑回、套用伺服器畫面、方向鍵放開；位置不同時直接滑過去；請求失敗時滑回最後確認的格子並重畫；
  - 視窗失焦（`clear`）時停止；出口要等前面確認才送；
  - `HeldKeys`：`e.repeat` 不算按下、多鍵優先順序、`WorldField` 有聽 `keyup`／`blur`／`visibilitychange`；
  - 旁白：占位與補上的事件卡、要不要送、補上之後只換 `event`（不把走路已更新的位置蓋掉）。
- 後端（`tests/api/test_wm1_walk.py`）：
  - 快取熱著與清空重算時 `GET` 畫面**逐位元組相同**；連走 4 步 `hero_out` 只算 1 次；
  - 換技能（改名）、換裝備、升級都重算，且和不用快取的結果相同；
  - 守則 14：走路回應的 `field` 等於依這個角色過濾的 `field_view`；
  - LLM 開著（Mock）：走到事件「！」旁那一步沒呼叫 LLM、`story` 為空、`story_pending` 為真；`event_story` 才呼叫、補上旁白；再送不重寫；重新載入看得到；日誌是 `walk`、`narrate`；從日誌重播＝存檔；
  - LLM 關著：同一個請求裡寫好旁白（沒有占位）。
- 既有測試沒有改斷言；只在 4 個前端假資料（`dev/eventArtGallery.tsx`、`dev/storyGallery.tsx`、`render/eventArt.test.ts`、`world/storyDialog.test.ts`）補新欄位 `story_pending: false`（型別要求）。

## 3. 量測（改之前 → 改之後）

### 3.1 一步的伺服器時間

方法同調查 2.1：`TestClient`、正式內容、LLM 關、主城、來回走 60 步取第 3 步起的中位數（腳本 `measure_step.py` 在暫存區）。同一台機器、同一段時間交替跑「每步清快取（＝改之前）」與「有快取」：

| | 整個請求 | world_view | hero_panel | 回應 |
|---|---|---|---|---|
| 改之前（開工時實測，未改程式） | 36.1 ms | 24.6 ms | 16.0 ms | 68.8 KB |
| 不用快取（交替第 1、3 次） | 34.7／37.7 ms | 23.2／24.0 ms | 15.2／15.6 ms | 68.8 KB |
| **有快取**（交替第 2、4 次） | **19.6／21.3 ms** | **8.5／8.6 ms** | **0.25 ms** | 68.8 KB |

這台機器比調查時慢（調查是 20.8 ms），比例上一步少了約 45%。回應大小不變（這段不做走路專用回應）。

### 3.2 前端（內建瀏覽器、本機 8765 埠伺服器、主城酒館、模擬按住：按下後停 500 ms，再每 33 ms 送一次 repeat）

| | 第 1、2 步間隔 | 按住時每兩步間隔 | 放開後多走 | 單次來回 |
|---|---|---|---|---|
| 改之前 | **508 ms**（2 次都是） | 119～145 ms（多數 133） | **2 步** | 23～31 ms |
| 改之後 | **134～138 ms**（5 次） | 129～150 ms（多數 133～135） | **0 步** | 20～29 ms |
| 改之後＋每個走路回應多延遲 150 ms（模擬 Tunnel） | 171～188 ms | 170～193 ms（≈ 來回時間；主角領先 2 格，不再「滑 120 ms＋站著等來回」） | 0 步 | 170～192 ms |

- 注意：量測時瀏覽器窗格是隱藏的，rAF 只有約 15 fps（67 ms 一幀），偶爾停住，動畫時間只能看相對值。有幾輪出現每步約 425 ms 的情形：同一段時間量到 rAF 停擺、改由渲染器 420 ms 的備用計時結束動畫，屬環境（窗格隱藏）而非程式；窗格恢復 15～30 fps 後回到約 133 ms。
- 改之前沒有在加延遲的情況下量（舊版前端沒有另外建置保存）；照舊流程推算是「來回＋播一格」約 300 ms。Tunnel 沒有實測。

## 4. 截圖（`docs/art/shots/wm-1/`，交美術 PM）

| 檔案 | 內容 |
|---|---|
| `pullback-1-ahead.jpg` | 拉回前：主角先走到第 2 格中途（伺服器還在起點） |
| `pullback-2-sliding.jpg` | 拉回中：伺服器回報停在起點，主角面向不變往回滑 |
| `pullback-3-server-cell.jpg` | 拉回後：停在伺服器給的格子 |
| `story-1-pending.jpg` | 事件卡旁白占位「說書人正在構思這段故事……」 |
| `story-2-filled.jpg` | 旁白補上之後 |

拍法：`?dev=1&walkms=6000` 放慢；用頁面裡包 `window.fetch` 的方式讓第一個走路回應延遲 7 秒、位置往回一格（模擬伺服器不同意）。旁白兩張也是包 `fetch`：`GET` 畫面塞一張假事件（`story_pending: true`），`event_story` 延遲 15 秒回假旁白（文字標了「WM-1 截圖用假資料」）——實機要 LLM 開著又踩到事件「！」才到得了，這次沒有開本機 LLM。聲音設定全靜音。伺服器 8765 與瀏覽器分頁交件前都用自己的 PID／分頁關掉。

## 5. 結束碼

| 檢查 | 結束碼 |
|---|---|
| `uv run ruff check src tests/api/test_wm1_walk.py` | 0 |
| `uv run ruff format --check src tests` | 0 |
| `uv run mypy src tests/api/test_wm1_walk.py` | 0 |
| `uv run lint-imports` | 0（14 kept） |
| `uv run pytest -n 8 tests/api tests/test_architecture.py` | 0（1477 passed、1 skipped） |
| `corepack pnpm -C client exec tsc --noEmit` | 0 |
| `corepack pnpm -C client exec vitest run src/world src/render/eventArt.test.ts src/api` | 0（72 檔、886 passed） |
| `corepack pnpm -C client build` | 0（只有既有的 chunk 大小警告） |
| `scripts/check.py --all` | 0（見第 7 節） |

## 6. 待 PM 決定（已裁定）

開發 PM 裁定（2026-11-23）：

- 第 1～7、10、11 件：接受。
- 第 8 件：接受。日誌少的是那個事件的**開場旁白紀錄**：一筆 `narrate` 動作（`scene: "event"`，裡面是說書人的 `story`）。走路的 `walk` 動作與事件本身（觸發、放「！」、開卡）照舊記在 `walk` 的結果裡，重播不受影響。
- 第 9 件：主角面板沒看身上裝備是既有行為，這段不改；開發 PM 記進 E6-b2。

原本列的 11 件：

1. **領先上限放前端設定檔**（`client/src/world/walkAhead.config.json`），沒有放伺服器規則。
2. **前端先走只用在方向鍵**。點格子走路照舊：整條路一次送、等回應才播（第一格仍會等一次來回）。要不要也改成先走，留給下一段。
3. **對不上時方向鍵全部放開**，要再按一次才走（最保守）；遇敵本來就會停。若希望「位置不同但沒遇敵」時按住的鍵繼續走，要再定。
4. **拉回的演出**：沿原路倒退、每格 120 ms、`forced` 滑動不轉身；伺服器的格子不在先走的路上時直接滑過去一格的距離（不播走路片段）。
5. **出口、門、傳送石不先走**：要等前面的格子都確認了，照舊流程送（換地圖仍等伺服器）。
6. **旁白後補只在 `walk` 而且 LLM 真的會呼叫時**（世界 LLM 開著、健康檢查沒說不可用）；LLM 關著時模板旁白照舊在同一個請求寫。其他動作（`travel` 等）照舊同步。
7. **補旁白回來只換 `event`**：旁白寫進日誌時順帶記下的人名、地名、線頭，要等下一個動作的整份畫面才出現。補旁白請求失敗時留著占位，重新載入畫面才會再送。
8. **事件被走掉時旁白就不寫**：如果補旁白的請求到之前事件已經不在（例如離開地點），`narrate_event` 照舊什麼都不寫，日誌就沒有那筆 `narrate`（重播語意不變，只是少一段敘述）。
9. **快取鍵多放了角色裝備**：`as_run` 目前沒有帶 `CharacterState.equipment`，所以主角面板（含暴擊倍率）其實是照主角範本的裝備算、不看角色穿的裝備。這段為了「換裝備就失效」保守把裝備放進鍵；面板該不該看角色裝備是既有行為，沒改，請開發 PM 看要不要排（可能和 E6 有關）。
10. **開發用慢動作參數** `?dev=1&walkms=N` 是為了拍截圖新加的（只在開發模式）。
11. 量測在隱藏窗格（約 15 fps）做的；Tunnel 沒實測；改之前沒有量「加 150 ms 延遲」的對照。

## 7. 全量檢查

開發 PM 說「可以跑」後，先 `git merge --no-edit main`（含 E6-c1，`3a7d5f7bf`），沒有衝突。

- 第一次 `check.py --all`：結束碼 1。`tests/test_hardcoded_scan.py` 抓到 `devWalkMs` 的上限 `10000` 沒有歸類。開發用參數不需要上限，拿掉之後重跑（`1b7f0c98a`）。
- 第二次 `uv run python scripts/check.py --all`：**結束碼 0**。
  - ruff、format、mypy、lint-imports、pytest（18903 passed、8 skipped）、client install、typecheck、client test（425 檔、5012 passed）、situation coverage 全部通過。
  - 已寫下通過戳記。
- `corepack pnpm -C client build`：**結束碼 0**。

## 開發 PM 驗收（2026-11-23）

**通過**，已合併進 main。`check.py --all` 第 2 次 0（第 1 次擋在寫死數字掃描，拿掉開發參數上限修好）；build 0。量測：第 1、2 步間隔 508 → 約 136 ms、放開後多走 2 → 0 步、伺服器一步約 36 → 20 ms；Tunnel 未實測，模擬 150 ms 延遲時每步 170～190 ms。

- 11 件待決照裁定（報告第 6 節）。第 9 件主角面板沒看身上裝備，記進 E6-b2。
- 截圖交美術 PM（拉回 3 張、旁白 2 張）。
