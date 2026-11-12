# Phase PR-2d 報告｜靶場測試模式收尾

> 規格：派工 prompt（PR-2d，2026-11-12）；依據 `PhasePR-2計畫.md`「第 1～10 點已定」、`PhasePR-2b報告.md`、`PhasePR-2c報告.md` 第 9 節、`docs/art/PR-2檢查.md`（2c 第 6 點）、`docs/art/OB與PR樣張.md`（藍格貼水池內縮 9）、玩法 PM 共用筆記「PR-2 字串（2026-11-12）」。
> 實作者：Opus 5.5（2026-11-12）。worktree 從 origin/main 開，先 `git merge --ff-only main`（含 `f4ffd6ce`）。

## 1. Commit

| commit | 內容 |
|---|---|
| `34df277c` | `feat(client)`：五項交付＋D 組測試 |
| `4e1b2c6a` | `fix(client)`：實戰紅框那一行維持原字（`hid1bLayers.test.ts` 鎖著原句）；4 張截圖 |
| `4a464fec` | `docs`：本報告、上手筆記 |

沒有 push。

## 2. 做了什麼（全部以 `view.practice`／`DrawModel.practice` 分支，實戰輸出逐字不變）

1. **藍格貼水池內縮**（美術必做，`PR-2檢查.md` 2c 第 6 點）：`render/practiceRange.ts` 新 `poolInsets(scene, w, h, T)`——石條落在哪一格上，那一格朝石條的那一邊縮一個石條寬（`slabWidth(T)`＝9×48/52）：池外貼水池的那一邊、池格貼地圖邊緣（石條畫在水面裡）的那一邊；斜對角外伸的角不算（同樣張）。`render/pathArt.ts` 的 `drawSoftCells` 多一個選填 `insetOf`（方塊與外緣亮線一起縮；省略時每筆畫筆呼叫和改前相同）；`render/battle/highlightLayer.ts` 的可走、範圍、預覽與攻擊紅框都套用（`poolInset()`：`model.practice` 不存在時回 `undefined`，紅框走改前那一行）。
2. **工坊選單的木樁小圖**：`render/trainingDummy.ts` 新 `drawTrainingDummyIcon(ctx, px, res)`（呼叫同一個 `drawTrainingDummy`，取景照原 SVG 的 viewBox `-31 -55 62 62`）；`world/WorkshopPanel.tsx` 的 `DummyGlyph` 改成 32×32 CSS px、畫布 64×64 的 `<canvas>`（CSS 不縮放），刪掉內嵌 SVG。「改造技能」照舊 `WeaponIcon` 的 `hammer`。
3. **靶場「測試模式」徽章說明卡**：`TestModeBadge` 加選填 `hint`（預設＝原字 `TEST_MODE_BADGE_HINT_ZH`）；只有 `PracticeBar` 傳 `PRACTICE_BADGE_HINT_ZH`（定稿句）。一輪測試模式的三處（`RunEnded`、`RunScreen`、`StartScreen`）不傳，原字不動。徽章外觀的 HTML 兩邊相同。
4. **開場橫幅**：抽出 `ui/BattleBanner.tsx`。實戰照舊（「戰鬥開始」＋勝利條件＋開場訊息，DOM 和改前相同）；測試模式只有一行 `PRACTICE_BANNER_ZH`「靶場：打木樁試招，按右上的離開鈕結束」（20px 粗體，同原勝利條件那行的樣式），開場訊息（「靶場試玩：{武器}」、沙盒說明）照舊接在下面（見待決 1）。
5. **指揮召喚物面板**：`ui/SummonPanel.tsx` 前端自寫的字過 `practiceWording(…, view.practice)`：面板說明卡（`TIP_TEXT`）、四個模式的說明（`MODE_HINTS`）、「選一個敵人集火（0 AP）：」、指揮框的兩句（`CommandBox` 多一個 `practice` 參數，並匯出給測試）。伺服器給的字不經過。

## 3. 逐條驗收

| 項目 | 結果 |
|---|---|
| `corepack pnpm -C client typecheck` | **0** |
| `corepack pnpm -C client test` | **0**（290 檔、3606 項全過） |
| `corepack pnpm -C client build` | **0**（只有既有的 chunk 大小警告） |
| D 組測試（新檔 `client/src/battle/pr2dPractice.test.ts`，17 項） | 全過 |
| 既有：`pr2bPractice`、`pr2cPractice`、`world/range`、`floatCardRule`、`hid1bLayers`、`importCycles` | 全過 |
| 浮動卡實測（徽章說明卡） | 通過（第 5 節） |
| `__layoutSmoke` 三個尺寸 | 全 PASS（第 6 節） |
| 截圖 4 張、≤ 300 KB | 是（第 4 節） |

D 組測試名（`describe › it`）：

- `D1 高亮格貼水池往內縮一個石條寬` › 實戰、技能工坊與沒有水池的地圖不給內縮／training_range 各格的內縮值（含 L 形內角、池格貼下緣）／縮過的可走格不壓到這一格上的石條（拿 `poolGeometry` 的石條逐格比）／沒給內縮與內縮回 null 時每筆畫筆呼叫和改前相同（改前數字寫在表裡）／測試模式方塊與外緣線讓出石條／接線（高亮層四處都經過 `poolInsets`）
- `D2 工坊師傅選單` › 木樁畫布原尺寸 ×2、沒有 SVG、錘子不變／`drawTrainingDummyIcon` 取景與縮放
- `D3 徽章說明卡` › 定稿原字／不帶參數是改前原字、提示條帶定稿句、外觀 HTML 相同／一輪測試模式三處不傳 hint
- `D4 開場橫幅` › 實戰和改前逐字相同（含開場訊息）／測試模式只有定稿那一行／接線
- `D5 指揮召喚物面板` › 實戰改前原字／測試模式寫木樁、其餘相同／接線

## 4. 截圖（`docs/art/shots/pr2/`，前綴 `d-`，4 張）

| 檔案（完整路徑） | 內容 | 大小 |
|---|---|---|
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\pr2\d-pool-inset-3x.png` | 實機測試模式移動模式（3 倍）：池外 (5,8) 右緣、(6,7)／(7,7) 下緣停在石條外；池格 (6,9) 下緣停在內側石條上方、(7,8) 右緣停在石條內；木樁紅框 | 126 KB |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\pr2\d-workshop-menu-2x.jpg` | 實機主城工坊師傅選單（2 倍）：「靶場試玩」列的木樁＝戰場木樁畫法；「改造技能」錘子不變 | 64 KB |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\pr2\d-banner-badge-1600.jpg` | 實機進場 0.6 秒內（1600×900）：開場橫幅只有定稿那一行（下接「靶場試玩：弓」與沙盒說明）；滑過徽章的說明卡是定稿句 | 119 KB |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\pr2\d-summon-panel-2x.jpg` | 實機召喚後（2 倍）：「選一個木樁集火（0 AP）」、模式說明卡「優先打威脅你的木樁」 | 68 KB |

（worktree 內的路徑：`<worktree>/docs/art/shots/pr2/…`；合併後即上表路徑。）

另：選「喚出元素火花」時的攻擊紅框貼水池也內縮（實機看過，過程截圖在暫存區、沒有放進交件，張數上限）。

怎麼拍：`corepack pnpm -C client build` → `TRPG_SAVE_DIR=<暫存>\pr2d\saves TRPG_DEV_ROUTES=1 uv run trpg serve --port 8111`；`POST /api/world/characters`（開發欄位：弓＋召喚物／潮濕，出生主城）→ `POST …/actions {kind: "walk"}` 走到 (23, 18)、`hint_seen ["opening"]` → 無頭 Chrome（`--mute-audio`、CDP 8112、`?mute=1`）按「繼續」→ 方向鍵右＋E 開師傅選單 → 點「靶場試玩」→ 走到 (4, 6) → 移動模式截圖 → 放「喚出元素火花」→ 點「集火」。結束後用自己記下的 PID 關掉 uv（43400，含 trpg／python 子程序）與 Chrome（12736 與 8 個子程序），8111、8112 都沒有在聽，沒有殘留。

## 5. 浮動卡實測（徽章說明卡，`<Hint>`）

| 尺寸 | 150 ms 前不開 | 滑過開 | 卡片位置 | 滑進卡片仍開 | 卡內捲動 | 釘住 | Esc 關 | 點外面關 |
|---|---|---|---|---|---|---|---|---|
| 1600×900 | 是 | 是（portal 到 body、`position: fixed`） | 徽章下方（上方放不下翻轉），在畫面內 | 是 | 卡高 69 px，不需捲（scrollHeight＝clientHeight） | 觸控點一下釘住（1.2 秒後仍在）；滑鼠點不釘（`<Hint>` 的設計，3-32b） | 是 | 是（滑鼠與觸控都是） |
| 800×600 | 是 | 是 | 同上，在畫面內 | 是 | 不需捲 | 同上 | 是 | 是 |

## 6. `window.__layoutSmoke.runCase("PR-2d")`

`localStorage.clear()` → `/?dev=1&anim=0.1&mute=1`，自己的 build＋`trpg serve`（8111）：

| 尺寸 | 結果 |
|---|---|
| 1600×900 | **全 PASS** |
| 1040×624 | **全 PASS** |
| 800×600 | **全 PASS** |

## 7. 和規格不同的地方

1. **多改 `render/pathArt.ts`**（`drawSoftCells` 加選填參數）：高亮格的畫法在這裡，高亮層只負責呼叫。省略參數時輸出不變（D1 第 4 項）。
2. **攻擊紅框也內縮**：規格寫「可行動格／範圍等高亮格」，紅框貼水池同樣會壓石條，一起縮（實戰那一行原字保留，`hid1bLayers.test.ts` 照舊通過）。

## 8. 實機未看

- 指揮框（`CommandBox`）的兩句（「再選要打的木樁」「原地沒有打得到的木樁」）：只有 vitest（D5）；實機截圖拍的是集火清單與模式說明。
- 開場訊息的 `NoticeBanner`（上方那條，15 秒自動關）在截圖上被徽章說明卡蓋住一半，那條沒改。

## 9. 待 PM 決定

1. **橫幅下面的開場訊息**：定稿說「改成一行」，我只拿掉「戰鬥開始＋勝利條件」，「靶場試玩：{武器}」與沙盒說明兩行照舊接在下面（它們不是被要求拿掉的東西，且同一句另有上方提示條）。要只留一行請說。
2. **斜對角的外角**：石條外角往斜對角格多伸出的一小塊（約 8×8 px）不讓，藍格的角被石條蓋住一小角（同樣張 `practice-move-board-2x.png`）。
3. **水池格本身也是可走格**（引擎判定）：池格上的藍格只讓開貼地圖邊緣那一邊的內側石條；池內相鄰水面之間不縮。
4. **選單木樁小圖的大小**照原 SVG（32 px、取景相同）；木樁在深色底上偏暗、只佔中間一條，要放大或加底色請美術 PM 定。
5. **路徑提示、滑過白框、致命淡紅**等其他疊在格子上的標記沒有內縮（只做規格寫的高亮格＋紅框）。
