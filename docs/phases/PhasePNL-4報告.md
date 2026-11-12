# Phase PNL-4 報告：事件卡選項列 A＋OB-8 NPC 頭像＋改字表剩下的部分（＋排進來的美術待辦）

> 依據：`docs/art/資訊面板-移植需求.md` 第 6 節 PNL-4 列（3.4、3.5、4.2；後端 `PartyIntroLine` 頭像），驗收第 7 節 #16～#18；需求第 5 節「要開發 PM 決定」一律照美術建議。
> 加做：`SolutionTile`（2.2）、800×600 判定列（`docs/art/QI-6驗收.md` 觀察）、覺醒插圖照顯示寬出圖（`PhaseQI-6報告.md` 待決 2）、阿岳頭像（`PNL-1a驗收.md` 可修 3）、刪 `dev/eventLegacy.ts`、事件卡說明字套 `KeepNum`。
> 開發 PM 追加（中途）：PNL-3／QI-7 美術驗收可修（已完成任務摺疊、KeepNum 套公告板與成長、任務類別細框、刪 `dev/itemLegacy.tsx`、截圖用語）、灰燼荒原「異象」說明卡定稿字、HUD 追蹤列線頭改「剩 …」。
> 分支：`worktree-agent-a2ebcf5b23f55148a`（開工時 ff 到 main `ce997e53`）。沒有 push。

## 1. 做了什麼

| 項目 | 檔 |
|---|---|
| **後端 OB-8 頭像**：`PartyIntroLine` 加 `portrait`、`region`（選填）。伺服器照說話者名字對：這段的成員本人（傭兵＝名冊頭像＋出身區；劇情夥伴＝人設卡頭像＋卡所在的區）、主城守印人（新的 `world_range.keeper_speaker`，同公告板／靶場那張）；對不到為 `None`。前端不用名字查。 | `src/trpg/api/world_party_schemas.py`、`world_party_intro.py`、`world_range.py` |
| **後端劇情夥伴頭像**：`PartyMemberView.portrait`／`region`（只給劇情夥伴；`world_party_view.companion_face`：依區域 ID 排序找第一張人設卡，阿岳＝雲嶺）。 | `src/trpg/api/world_party_view.py` |
| `client/openapi.json`、`client/src/api/schema.d.ts` 重產（只多上面四個選填欄位）。 | |
| **`SolutionTile`／`SolutionGrid`**（選項列 A）：兩欄等寬、剩一格撐滿（`:last-child:nth-child(odd)`）、同列等高；每格 `SolutionGlyph` 24＋主字（粗體、兩行「…」、`keep-all`＋`anywhere`、詞間 `<wbr>`）＋次行（「情境判定・屬性圖 14＋名」、兩屬性用「／」；「交涉 −N 補給」；戰鬥、放棄不重複）；放棄＝右下小鈕（圖示 18）；「用〔…〕抵」＝同一格次行右邊的小鈕；說明卡照現行 `solutionLabel`＋`solutionHint`，內文過 `KeepNum`。 | `client/src/world/SolutionTile.tsx`（新）、`solutionGrid.ts`（新，純函式）、`EventCard.tsx`、`world/story.css`、`styles/world.css` |
| **800×600 判定列**：說明字 `flex-basis` 8em→3em（DC、屬性、說明、線索同一行）；打開情境判定時把「判定列～擲骰」捲進事件卡（新 `scrollReveal.revealBottomInScroller`：放不下時先對齊下緣；`ResizeObserver` 在 1.2 秒內跟著版面再捲，玩家自己捲就停）。 | `EventCard.tsx`、`ui/scrollReveal.ts`（只新增匯出） |
| 事件卡其他說明卡（線索鈕、每筆引用）也過 `KeepNum`（`HintBody`）。 | `EventCard.tsx` |
| **OB-8 對話框**：每句改成開場 `AwakenDialog` 的 `world-dialog` 排法（頭像 48＋粗體名字＋台詞），同一人連續兩句也各一個頭像。 | `world/PartyIntroDialog.tsx`、`styles/world-hud.css` |
| **阿岳頭像**：隊伍面板隊友卡、HUD 隊友小卡改用伺服器的 `portrait`／`region`（傭兵照舊用名冊）。 | `world/PartyShadowPanel.tsx`、`world/hud.ts` |
| **覺醒插圖照顯示寬出圖**：`AwakenArt` 用 `ResizeObserver` 量畫布寬，`awakenArtScale`（和 `eventArtScale` 共用算法），量到前退回舊的 ×4。 | `world/OpeningDialog.tsx`、`render/eventArt.ts` |
| **刪 `dev/eventLegacy.ts`**，開發頁 `event-gallery` 拿掉「現行｜Q」對照（小牌、泡泡只畫 Q 版；指紋 `set=hash` 不受影響）。 | `client/src/dev/eventGallery.ts` |
| （追加）**任務日誌已完成摺疊**：進行中在前，已完成收進最後的「已完成（N）」摺疊、預設摺起、卡片淡化保留、卡上不掛「已完成」；0 個不畫；有已完成時 `folds` 讓量高度含打開的樣子。 | `world/QuestLog.tsx`、`world/questPanel.ts` |
| （追加）**任務類別標籤細框中性**（`<Tag>`，不帶色調）。 | `world/QuestLog.tsx` |
| （追加）**KeepNum 套公告板與成長的 L2／L3 說明**：公告板＝階段說明、「下一個」天數、頭目說明、首殺、挑戰原因、挑戰規則；成長＝警告、閃現鎖住、入門配點資訊、已閃次數、屬性點空狀態、種族次行、重閃說明（`reflashNoteText`，一輪營火共用，字不變）。 | `world/BoardPanes.tsx`、`WorldGrowth.tsx`、`GrowthLookRows.tsx`、`run/CampfireSkillCare.tsx` |
| （追加）**刪 `dev/itemLegacy.tsx`**，`item-gallery` 拿掉「現行」欄。 | `client/src/dev/itemGallery.tsx` |
| （追加）**灰燼荒原「異象」說明卡**：`與火溝通；角魔主角 +1` → `向聖火求指引，角魔主角判定 +1`（玩法 PM 定稿）。 | `content/world/events/ashen_waste.yaml` 第 68 行 |
| （追加）**HUD 追蹤列線頭到期改「剩 …」**：`trackedQuests` 的線頭行改用 `left_zh`（`threadLeftText`，沒有時退回 `expires_zh`），說明卡 `trackHint` 跟著是同一行。 | `world/hud.ts` |
| 測試（新）：前端 `world/pnl4EventTiles.test.ts`（23）、`world/pnl4Followups.test.ts`（11）；後端 `tests/api/test_party_faces_pnl4.py`（4）、`tests/content/test_event_hint_pnl4.py`（1）。 | |
| 上手筆記第四節第 113～120 點、第一節開發頁列、第五節加一列。 | `docs/dev/上手-前端戰鬥畫面與動畫.md` |

沒有改 `content/skills`、詞條、技能驗證、LLM schema、數值工坊、`src/trpg/sim/skill_ratio.py`。共用元件只做新增（`scrollReveal` 新增兩個匯出、`Hint` 用既有的 `rich`）。

## 2. 第 5 節「要開發 PM 決定的事」（PNL-4 相關）

| # | 做法 |
|---|---|
| 3 | 已由 TXT-1 做成內容檔 `hint_zh`；本段只把說明卡內文過 `KeepNum`。 |
| 5 | `SolutionTile` 放 `client/src/world/`（不是 `ui/`）：它依賴 `world/narration`、`StoryIcons`、`story.ts`，只有事件卡用；`ui/` 匯入 `world/` 會讓共用層反向依賴。見待決 1。 |
| 10 | 不合併：同一人連續兩句也每句一個頭像。 |

## 3. 4.2 內容字與 content digest

- TXT-1 已改的四處不動；本段只改 `ashen_waste.yaml` 第 68 行「異象」的 `hint_zh`（開發 PM 追加，玩法 PM 定稿）。`content/` 裡玩家看得到的「#數字」：`tests/content/test_no_design_numbers_txt1.py` 照樣通過（沒有新增）。
- **雜湊**：改了事件檔，`ruleset_hash`、`content_digest` 會變（`library.files`）；事件不在規則包，`hash_ruleset` 不變，舊戰鬥紀錄照樣重播。使用者重開伺服器後進行中的一輪從頭開始、世界日誌標成不能重播（同 TXT-1 報告第 5 節）。沒有重產任何雜湊或快照；`tests/content tests/api tests/world` 結果見第 6 節。

## 4. 既有測試的改動（舊 → 新、理由）

| 檔 | 舊 | 新 | 理由 |
|---|---|---|---|
| `tests/api/test_ob7_party_intro.py` `test_seren_intro_after_departure_then_seen` | `intro == {…, "lines": _lines(...)}` | `{**intro, "lines": _texts(intro["lines"])} == {…}`（只比說話者與台詞） | 每句多了 `portrait`／`region`；頭像另在 `test_party_faces_pnl4.py` 鎖 |
| 同檔 `test_ayue_intro_when_he_joins` | `[x.model_dump() for x in intro.lines] == _lines(...)` | `_texts([...]) == _lines(...)` | 同上 |
| `client/src/world/partyIntro.test.ts` | `"<b>乙</b>：第一句。"` | `'<b>乙</b></div><p class="world-awaken-text">第一句。'` | 排法改成頭像＋名字＋台詞（需求 3.5） |
| `client/src/world/pnl3Quest.test.ts` | `'<span class="pnl-tag open">新手</span>'` | `'<span class="pnl-tag">新手</span>'` | 類別改細框中性（PNL-3 驗收可修 1） |
| 同檔 | 完成卡 `toContain('<span class="pnl-tag mine">已完成</span>')` | `not.toContain("已完成")` | 已完成收進摺疊，卡上不掛標籤（可修 2） |
| `client/src/ui/summonBadges.test.ts` | `'<Tag tone="open">{quest.kind_zh}</Tag>'` | `"<Tag>{quest.kind_zh}</Tag>"` | 同類別細框 |

舊句「與火溝通；角魔主角 +1」沒有任何測試斷言（`tests/`、`client/src` 都 grep 過），新增 `test_event_hint_pnl4.py` 鎖新字。

## 5. 實機量測與截圖

**做法**：`vite build` 後自己的 `trpg serve --port 8794`（`TRPG_SAVE_DIR`＝`scratchpad/pnl4/saves`、`TRPG_DEV_ROUTES=1`）、無頭 Chrome `--headless=new --mute-audio`（除錯埠 9784、profile 在 `scratchpad/pnl4/chrome`），網址都帶 `?mute=1`，裝置像素比 1。開發角色 `POST /api/world/characters`（單手劍），localStorage 寫角色後**首頁「繼續」**進入。事件、隊友加入台詞、阿岳成員、任務、線頭用 `Page.addScriptToEvaluateOnNewDocument` 包 `window.fetch` 注入（上手筆記第 119 點）：事件解法字照 `content/world/events/*.yaml`（說書人用模板句）；賽倫／阿岳的台詞與頭像用伺服器同一個函式 `_view`／`companion_face` 從正式內容算出；#17 的長主字是樣張 OPT8 的示意字（非正式內容，正式內容沒有長到兩行的主字）。程式與後端不動。結束後用 TaskStop 關掉 serve 與 Chrome，8794／9784 都沒在聽。

**事件卡（卡寬實量：1600＝575 CSS px〔460×外層縮放 1.25〕，800×600＝339.7）**

| 事件 | 1600 卡高／格子 | 800 卡高／格子 |
|---|---|---|
| 1 個（疤面的報仇） | 383／531×46 | 293／295.7×46 |
| 1 個＋放棄（鐵匠） | 414／531×48（放棄小鈕距右緣 22） | 324／295.7×48 |
| 2 個（獸耳族旅人） | 385／262.5×48 ×2 | 295／144.8×48 ×2（次行一行） |
| 3 個（斷崖幫哨兵） | 439／262.5×48 ×2＋531×48 | 349／144.8×48 ×2＋295.7×48 |
| 1＋放棄・兩屬性（崖上的靈芝） | 414 | 324（「情境判定・力量／敏捷」一行） |
| 長主字＋線頭抵（示意） | 472，四格都一行 | 414（捲 64）；格寬 137.3，主字兩行，第 2 格截斷「…」 |

都不用捲（長主字示意除外）。

**800×600 判定列（QI-6 那張，前後）**：改前判定列折兩行、線索膠囊被下緣切半、文字框與擲骰要自己捲。改後判定列一行（高 24，線索同一行）；打開時自動捲 220（到底），擲骰列底 526＝捲動區底；1600 捲 17 到底，擲骰同樣看得到。

**OB-8**：1600、800 的對話框都是 480 寬；賽倫那段兩個頭像 48（守印人主城框、賽倫晶冠出身框），阿岳那段一個（雲嶺綠框）；800 不另縮。隊伍面板 800：阿岳卡、HUD 隊友小卡都有臉。

**覺醒插圖**：1600、800 都量到畫布 444×222＝顯示 444×222（實機 DPR 1；改前是 ×4 的畫布再被 CSS 縮小）。

**任務日誌**：1600 面板 720×616、800 面板 493×414；「已完成（2）」預設摺起、打開後外框高不變（量高度含打開的樣子）；類別三個都是 `pnl-tag`（細框）。

**HUD 追蹤列**：線頭行「剩 2 天 23 小時」，說明卡「線頭：商人欠你人情・剩 2 天 23 小時（點了打開任務面板）」。

**浮動卡（6.5.1）**：觸發元素＝事件卡選項格（第 2 格，長主字），1600×900 與 800×600 都是：100 ms 時沒有卡、600 ms 出現（上方）→ 分 8 步沿直線滑進卡片，卡片還在 → 卡內滾輪：卡片內容短（scrollHeight 85＝clientHeight 85），已經到底、沒有被關 → 點一下釘住（`.float-card.pinned`）→ 滑鼠移到畫面角落仍在 → Esc 關掉卡片，事件卡仍在。

**截圖**（`docs/art/shots/pnl4/`，10 張；PNG 只用在最近鄰特寫；單張最大 233 KB）

| 檔 | 驗收 | 內容 |
|---|---|---|
| `docs/art/shots/pnl4/pnl4_01_events_1600.jpg` | #16 | 實機 1600：1 個、1＋放棄、2 個、3 個 |
| `docs/art/shots/pnl4/pnl4_02_events_800.jpg` | #16 | 實機 800×600：同上＋崖上的靈芝（兩屬性） |
| `docs/art/shots/pnl4/pnl4_03_tiles_340_closeup.png` | #17 | 實機 800×600、DPR 1，最近鄰 ×2：長主字兩行「…」＋說明卡全文、「用〔…〕抵」小鈕、兩屬性次行 |
| `docs/art/shots/pnl4/pnl4_04_judge_before_after.jpg` | 加做 2 | 判定列：改前（QI-6 截圖 7）｜改後 800｜改後 1600 |
| `docs/art/shots/pnl4/pnl4_05_intro_1600.jpg` | #18 | 實機 1600：賽倫那段、阿岳那段 |
| `docs/art/shots/pnl4/pnl4_06_intro_800_party.jpg` | #18、加做 4 | 實機 800：兩段對話框＋隊伍面板與 HUD 隊友小卡的阿岳頭像 |
| `docs/art/shots/pnl4/pnl4_07_awaken_x3.png` | 加做 3 | 覺醒插圖左上小牌，實機 DPR 1、最近鄰 ×3（1600、800）＋1600 整張 |
| `docs/art/shots/pnl4/pnl4_08_quest_done_fold.jpg` | 追加 1、3 | 任務日誌：已完成摺起｜打開（1600）｜800 |
| `docs/art/shots/pnl4/pnl4_09_track_left.png` | 追加（追蹤列） | 實機 1600、DPR 1，×2：追蹤列「剩 …」＋說明卡 |
| `docs/art/shots/pnl4/pnl4_10_float_800.jpg` | 浮動卡 | 實機 800×600：選項格說明卡 |

**實機未看**：KeepNum 套到公告板與成長的那幾處（字面沒有斷行差異，由 `pnl4Followups.test.ts` 掃原始碼與 `glueNumbers` 鎖）；開發頁 `event-gallery`／`item-gallery` 拿掉對照後的樣子（typecheck、build 過）；實機 DPR 2。

## 6. 檢查（結束碼）

| 指令 | 結束碼 | 摘要 |
|---|---|---|
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run mypy` | 0 | 1527 個檔沒有問題 |
| `uv run lint-imports` | 0 | 14 kept、0 broken |
| `uv run trpg content check` | 0 | 662 個檔、404 個技能 |
| `uv run pytest -q tests/api/test_openapi_snapshot.py` | 0 | 2 passed（重產後） |
| `uv run pytest -q -n 8 tests/content tests/api tests/world` | 0 | 5434 passed、1 skipped（含 test_no_design_numbers_txt1、test_event_hint_pnl4、test_party_faces_pnl4、test_ob7_party_intro）；沒有測試寫死 content digest 而變紅 |
| `corepack pnpm -C client typecheck` | 0 | |
| `corepack pnpm -C client test --run` | 0 | 328 個檔、4272 項通過 |
| `corepack pnpm -C client build` | 0 | 只有既有的 chunk 大於 500 kB 警告 |

沒有跑完整的 `scripts/check.py`。

## 7. 和樣張不同的地方

1. **斷詞**：樣張「有標點就整句不插斷點」；800×600 的格子只有 137～145 寬，「亮出商隊旗號，」比一行長時 `overflow-wrap: anywhere` 把「，」斷到行首。改成有標點也照詞切（收尾標點黏前一個詞、開頭標點黏下一個詞），每個詞的「最後一字＋收尾標點」不斷開。
2. **格子內距與間距**：圖示與字的間距 8→6、內距 6/8/6/6→6/6/6/5（左），次行屬性圖示與字 2→1；145 寬時「情境判定・意志」才放得下一行。分隔號和後面的屬性包成一段不斷行。
3. **次行字色**：照樣張 L2（`#bdb5a2`）11.5px、分隔號 L3；需求 3.4 第 2 點寫「次行 L3」，我理解為 L3 的字級（見待決 3）。
4. **「用〔…〕抵」的位置**：樣張沒畫；做成同一格次行右邊的小鈕（金字、細金框、深底），次行先讓出同字的寬度。
5. 放棄小鈕、說明卡內容照樣張 `solGrid(…, { splitLeave: true })`。

## 8. 待 PM 決定

1. **`SolutionTile` 放 `client/src/world/`** 而不是需求第 5 節第 5 點建議的 `ui/`：它依賴 `world/` 的事件卡字與圖示，只有事件卡用；放 `ui/` 會讓共用層匯入 `world/`。
2. **賽倫頭像框用出身區（晶冠）**，不是需求 3.5 寫的「傭兵金」：隊伍面板與 HUD 隊友小卡已經用出身區（PNL-1a、RT-4），同一個人兩處框色一致比較保守；要改傭兵金就把伺服器的 `region` 換成 `None`。
3. 次行字色照樣張 L2，需求 3.4 第 2 點寫「L3」（第 7 節第 3 點）。
4. **斷詞與格子間距和樣張不同**（第 7 節第 1、2 點），交美術 PM 看截圖 3。
5. **打開情境判定時自動捲**：放不下時先對齊下緣（擲骰那一列），判定列上面的選項格會被捲上去；版面穩定前 1.2 秒內跟著再捲。玩家剛好在這 1.2 秒內自己捲會停止自動捲。
6. **說話者頭像由伺服器用說話者名字對**（內容的 `PartyLine` 只有 `speaker_zh`）。沒有改內容 schema；之後若有同名不同人，要在 `mercenaries.yaml` 的台詞加說話者 ID。
7. **#17 的長主字是樣張示意字**：正式內容目前沒有在 340 寬會到兩行的主字，實機的「…」截斷只能用注入的示意字看。
8. 開發 PM 中途追加的「實機 DPR 1」用語：本報告與截圖標題都照改；舊段報告未回改。
9. `dev/eventLegacy.ts` 的刪除被一起放進第一個 commit（`a586f69e`，`git rm` 先暫存了），內容不受影響。

## 9. Commit

- `a586f69e` feat(api): speaker portraits for party intro and companion faces (PNL-4)
- `86f6b21a` feat(client): event card solution tiles, intro portraits, awaken art scale (PNL-4)
- `cefbf569` feat(client): quest done fold, neutral kind tag, KeepNum on board/growth (PNL-4)
- `07e0d805` content(events): ashen vision hint wording per gameplay PM (PNL-4)
- `c6c60f94` feat(client): tile word breaks, judge row reveal, HUD thread left text (PNL-4)
- `5ae0a26d` docs(art): PNL-4 screenshots
- 最後一個：docs(dev): PNL-4 report and notes（本報告與上手筆記）

## 開發 PM 裁定（2026-11-13，第八任開發 PM）

已驗收並以 --no-ff 合入 main（無衝突，已含 LW-1）。合併後 ruff、mypy、trpg content check 0；openapi 快照＋ob7＋設計編號測試 13 passed；前端 typecheck 0、vitest 4272 passed、build 0。

1. SolutionTile 放 world/：接受（避免共用層反向依賴）。
2. 賽倫頭像框用出身區晶冠：交美術 PM。
3. 次行字色 L2：交美術 PM。
4. 斷詞與間距：交美術 PM 看截圖 3。
5. 判定列放不下時先對齊下緣：接受。
6. 頭像依說話者名字對應：接受；同名不同人時再加說話者 ID。
7. eventLegacy 刪除併在第一個 commit：接受。

### 美術驗收結果（2026-11-13，docs/art/PNL-4驗收.md）

有條件通過。必修 1：800×600 格寬 137～145 時「用〔…〕抵」小鈕壓到圖示、貼邊框；可修 1：收尾標點黏整個詞。兩件派 PNL-4b（交格寬 137、145、262 三張特寫）。賽倫頭像框用出身區晶冠正確（需求已更正）、次行 L2 與格子縮 2px 接受。
