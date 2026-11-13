# Phase RG-3 報告（第一批：#162 戰場標記前端）

> 實作者，2026-11-13。依據 `docs/phases/PhaseRG計畫.md` 第 3 節、`docs/art/RG樣張.md` 第 2、3、5、6、8 節（第 2 版，只搬 A 強招紫）。
> 第二批（持盾弟子、熔殼甲兵外觀、單挑插圖）不在這段；RG-1 的暫代外觀照舊。半掩護小圖示不做（美術 PM 決定 5）。

## 1. 做了什麼

| # | 項目 | 做法 | 主要檔案 |
|---|---|---|---|
| 1 | 被瞄準標記（準星） | 強招紫 `#b06bff`；空心圓＋三刻度＋朝下三角，亮 520／收 380 ms（收＝縮 0.86、沒有亮弧）；同一目標只畫一個，每一條都被擋才灰 `#b0b8c4`、不閃；減少動態固定亮。位置＝含頭飾的頭頂往上 4＋13.6k。目標格的「蓄」預計範圍拿掉，「蓄 N」改標在弓手格（RG-1 的 `ChargeOut.pos` 是目標格） | `battle/rgMarks.ts`、`render/rgArt.ts`、`render/battle/rgMarkLayer.ts`、`battle/telegraph.ts` |
| 2 | 瞄準線 | 胸口往目標 0.4 格起（在蓄力徽章圓裡就往前推出去）、到準星前 11k 止；2 px 虛線 `[4, 7]`、每段自己包外框色、每秒往目標 24 px；被擋：擋的人前 0.22 格斷開、垂直短槓（最多放大 1.3）、空 4 後灰點線不流動、外框 60%。照所在的排切段，放每排新的 `aims` 層（紅框之上、單位之下） | 同上、`render/rowLayers.ts` |
| 3 | 落空／被擋下／被打斷 | 沿用傷害浮字、tone `good` 黃。「落空」「被打斷」在弓手頭上，「被擋下」在擋住的隊友頭上（找不到時退回弓手），從不放在目標頭上；線與準星在同一步拿掉（播放中本來就不畫） | `battle/feedback.ts` |
| 4 | 盾兵擋住提示 | 選目標、預覽的 `cover.kind == shield_guard` 時：被保護者頭上 14×14 鳶形小盾（沒有人頭）＋盾兵到小盾側邊的米白點線（二次曲線、不穿過身體）；盾兵在正北時小盾放頭的右上（第 8 節第 2 條） | `battle/rgMarks.ts`、`rgMarkLayer.ts`、`screens/battle/useHighlights.ts` |
| 5 | 可疑痕跡 | 讀 `BattleView.trap_traces`（null／空＝不畫）→ `DrawModel.traces`；土堆＋挖坑＋細線木樁＋右上「？」（反向放大 9 px），每排 `traps` 層 | `battle/drawModel.ts`、`rgArt.ts`、`rgMarkLayer.ts` |
| 6 | 看一眼 | `trap_glance` → 回饋項目 `glance`；放置者頭頂（含頭飾）上方的米色泡泡、兩隻眼往那一格看，0～90 彈出、60～150 瞳孔、150～240 視線、480～600 淡出；和浮字同一層；減少動態不彈直接顯示 | `battle/feedback.ts`、`render/battle/feedbackLayer.ts` |
| — | 單挑對話框 | `EncounterView.duel == offered`：遇敵卡裡多一段「{精英}要求一對一」＋伺服器 `duel_zh`（寫明兩邊獎勵一樣）＋接受／拒絕兩顆等寬按鈕（送 `duel_choice`）；已選時只顯示 `duel_zh` 一行。**無插圖版本**（插圖美術還沒出）。不選直接開戰＝拒絕（RG-2 規則） | `world/WorldPanel.tsx`、`styles/world.css`、`api/types.ts`（`WorldAction` 加 `DuelChoiceAction`） |

頭頂（含頭飾）照第 8 節：量身體貼圖（`bareBodyOf`＋`ArtTextures.alphaMask`，解析度 2）中心左右 ±9 模型 px 的第一列不透明像素，照身體鍵（外觀＋朝向）記住；頭目用 `unitMarkTopY`；量不到退 `unitTopY`。只給準星、小盾、看一眼用，浮字照舊 `unitTopY`。

### 必要的 API 欄位（只動 `src/trpg/api/`，引擎與 `LOG_FORMAT` 不變）

- `ChargeOut.lock_blocker_id`：現在射出會被誰擋（`lock_on.lock_blocker`；看不到資訊的不送）。
- 落空事件（`effect_fizzled` 的 `lock_on_*`）JSON 加 `lock_caster_id`（這一步最後一個 `turn_started` 的單位）與 `lock_blocker_id`（`lock_on_blocked` 時，以這一步之後的戰場判斷）。
- `CoverOut.unit_id`（盾兵）。
- 重產 `client/openapi.json`、`client/src/api/schema.d.ts`；測試 `tests/api/test_rg3_api.py`（6 項）。

## 2. 檢查（結束碼）

| 檢查 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client build` | 0 |
| vitest：`battle/rg3Marks.test.ts`（20）、`world/rg3Duel.test.ts`（4）、`telegraph`、`feedback`、`drawModel`、`playback`、`src/test`、`floatCardRule`；開發中另跑過 `src/render` 全部（108 檔、1508 項） | 0 |
| `ruff check .`、`ruff format --check .`、`mypy`、`lint-imports` | 0、0、0、0 |
| pytest：`tests/api/test_rg3_api.py`、`test_openapi_snapshot.py`、`test_hidden_info.py`、`test_parts_api.py`、`test_delayed_api.py`、`tests/engine/test_lock_on_rg1.py` | 0 |

沒跑全量 `check.py`、沒重產快照（預測沒有會變的：引擎、內容、CLI 輸出都沒動）。

## 3. 截圖（`docs/art/shots/RG-3/`，DPR 1、`?mute=1`、無頭 Chrome `--mute-audio`）

| 檔 | 內容 | 項目 |
|---|---|---|
| `1-aim-1600.jpg` | 1600×900 實機整張（地圖 121%） | 1、2、5 |
| `2-aim-zoom-1600.jpg` | ×2：準星亮／收、瞄準線流動、被擋（斷點短槓＋灰點線＋灰準星）、可疑痕跡 | 1、2、5 |
| `3-guard-1600.jpg` | ×3：盾兵在南、盾兵在正北（小盾右上）＋同時的預覽文字 | 4 |
| `4-floats-glance-1600.jpg` | 被擋下、被打斷、落空＋看一眼 8 張連拍（×2） | 3、6 |
| `5-aim-800.jpg` | 800×600 實機整張（地圖 63%） | 1、2、5 |
| `6-aim-zoom-800.jpg` | ×3：800 的準星（反向放大）、線、斷點、「？」 | 1、2、5 |
| `7-guard-800.jpg` | ×4：800 的小盾與點線（南、正北）＋預覽 | 4 |
| `8-floats-glance-800.jpg` | 800 的三個浮字＋看一眼連拍 | 3、6 |
| `9-duel-1600.jpg`、`10-duel-800.jpg` | 大世界遇敵卡的單挑段（無插圖） | 單挑 |

**資料注入（註明）**：第一季實戰幾乎碰不到這些情境（沒有會放陷阱的敵人；瞄準要特定遭遇＋居高），全部 6 項都是**實機畫面＋包 `window.fetch` 注入資料**：單場戰鬥（開闊平原、鷹眼包、種子 7，主角先走到 (3, 4) 當擋箭的人）的回應加 `telegraph.charges`（`lock_target_id`／`lock_blocker_id`，弓手身上補 `charging` 狀態畫徽章）、`view.trap_traces`、選目標預覽加 `cover`（`shield_guard`＋`unit_id`），按「結束回合」那次回應的第一步加 `effect_fizzled`（`lock_on_blocked`、`lock_on_concealed`）、`followup_cancelled`（`interrupted`）、`trap_glance`。畫法與真資料相同（前端只讀這些欄位）。截圖用 `?anim=0.25` 放慢連拍。單挑是大世界開發角色的世界回應注入一個 `duel: offered` 的遇敵（敵人小頭像因為假資料沒有 `look` 是空圈）。所以「真的敵人 AI 瞄準、真的盾兵站位、真的放陷阱」的情境**實機未看**，畫法同上。

收尾：自己開的伺服器（9612，PID 36532）、無頭 Chrome（9613，PID 2368 整棵）都已關，兩個埠沒在聽。

## 4. 待 PM 決定

1. **單挑沒有用 `DialogFrame`**：大世界遇敵卡本身是中上方彈窗，`DialogFrame` 實機會疊在卡裡、蓋住敵人清單、多出「移到下方」，又在 1600 出捲軸。改成遇敵卡裡一段有金框的小對話框（`role="group"`）。標題「{精英}要求一對一」由前端用第一個精英名組字（伺服器 `duel_line` 用排最前的敵人；目前一致）。要真的獨立對話框請美術 PM 定位置。
2. **盾兵正北時小盾的位置**：第 8 節只寫「頭的右上側」，取頭頂往右 14k、中心比頭頂低 4（`NORTH_CHIP_DX`／`NORTH_CHIP_DY`）。實機（`3-guard-1600.jpg` 中間）小盾貼著頭的右上、點線很短；請美術 PM 看。
3. **瞄準線在「蓄」框的那一排**：線照所在的排放進每排新的 `aims` 層（和紅框同一級，在紅框之上），不是直接放 `frames`（`frames` 每次重設高亮會整層清掉）。畫的順序一樣是單位之下。
4. **目標看不到時不畫**：弓手或目標不在畫面資料裡（隱蔽看不到、倒下）時準星與線都不畫（保守，不洩漏位置）。被擋的人看不到時伺服器不送 `lock_blocker_id`，線就畫成沒被擋。
5. **落空浮字的弓手與擋的人由 API 推算**（不改引擎事件）：射出者＝這一步最後一個 `turn_started`，擋的人以這一步之後的戰場算。要更準得讓引擎事件自帶欄位（升 `LOG_FORMAT`）。
6. **看一眼的時間**固定 0.6 秒（不跟播放速度縮放，只跟開發用的 `?anim` 放慢）。
7. 可疑痕跡在 800（一格約 30 px）翻土只剩一小塊，主要靠「？」，同樣張的「仍不好認」第 2 條。

## 5. Commit

| hash | 內容 |
|---|---|
| `e63911a6d` | API：`lock_blocker_id`、落空事件的射出者與擋的人、`CoverOut.unit_id`＋測試＋重產型別 |
| `b9f3791c8` | 前端：準星、瞄準線、三個浮字、小盾與連結、可疑痕跡、看一眼 |
| `820e6f377` | 前端：單挑對話框（無插圖） |
| `e1bf237fe` | 單挑改成遇敵卡內一段；截圖 |
| （本報告） | 報告、上手筆記 |
