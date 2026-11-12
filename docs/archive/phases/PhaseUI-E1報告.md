# Phase UI-E1 報告：入口畫面換皮，加上美術 PM 驗收 RT-1＋UI-E2 的 14 項追加

實作者，2026-11-05。分支 `worktree-agent-ac227a44c00b76db8`，從 main `b8207d6e` 開始，沒有 push，也沒有合併。

這一段只換外觀。流程、API、規則都沒動，伺服器欄位、`WORLD_RULES_VERSION`、`LOG_FORMAT` 也都沒變。

## 1. 做了什麼

### 1.1 遊戲名稱只放在一處

- 名稱和標語放在新的內容檔 `content/ui/game.yaml`，目前是 `title_zh: （遊戲名稱）` 和 `tagline_zh: 碎界之上，說書人替你寫下第一頁`。
- Python 端用 `src/trpg/content/ui_game.py` 的 `GameInfo` schema 驗證，已登記進 `registry.py`。`trpg content check` 會顯示：`ui/game.yaml：遊戲名稱「（遊戲名稱）」`。
- 前端由 `client/src/ui/gameInfo.ts` 在 build 時用 `?raw` 匯入，自己再檢查一次，壞掉時退回空位。
- 讀這個名稱的地方：首頁標題牌、開發選單標題牌、瀏覽器分頁標題（`main.tsx` 寫 `document.title`）。
- `index.html` 的固定標題改成「載入中」。舊的「LLM-MMO-TRPG 戰鬥原型」已經全部拿掉。
- 名稱定案後只要改 yaml。

### 1.2 入口五個畫面

五個畫面共用一個外殼 `EntryShell`：
- 背景：`EntryBackdrop`，用大世界圖第 2 版的 `AtlasPainter` 畫，加了 `bare` 選項，只貼天空、浮島、浮橋、雲。浮島 ±3px 漂浮，減少動態時不動。
- 標題牌：`EntryPlaque`。
- 框：共用彈窗 `PopupFrame` 的 inline 樣式，深藍底、金框、RT-1 四角飾件。
- 樣式都在 `styles/entry.css`，選擇器全部限定在 `.entry-skin` 底下，不影響大世界和戰鬥。

| 畫面 | 做法 |
|---|---|
| 首頁（正式） | 照 `home-v2.png`：標題牌在中上方，選單在右側，不擋島；窄視窗時置中。選單只有「開始」（6F-1），下面一行說明。 |
| 開發選單（`?dev=1`） | 換成同一套背景、標題牌和框。內容照舊：一輪、大世界、單場戰鬥、起始包、工坊。 |
| 角色列表 | 「我的角色」每列加上現行的 `HudPortrait` 頭像（金框）。帳號列也收進框裡。 |
| 建角頁 | 左邊是「預覽」框。人物要等 Q 版，所以**只留位置、不畫人物**；下面寫名字和「種族・出身・武器」。右邊是編號步驟：1 名字 → 2 種族 → 3 出身 → 4 起始武器 → 5 兩個關鍵字，編號用 CSS counter 自動產生。種族與出身拆成兩個步驟標題。武器鈕前面加現成的 `WeaponIcon`。按鈕改成「**建立並在主城醒來**」（#125），送出的資料不變。 |
| 開新一輪 | 換成同一套背景、標題牌和框。步驟標題編號，內容照舊。 |
| 一輪路線圖 | 6 場改成節點加連線，直排，所以 800 寬也放得下。已完成的節點是金框，目前這場是亮藍，Boss 用金色角冠的頭目紋章。一輪畫面的其他面板也套上同一套框。 |

**排版煙霧檢查**：`layoutSmoke.ts` 有兩處新增。
- `runScreens` 多一個階段：「角色列表與建角」加上種族卡說明。
- 新的 `window.__layoutSmoke.runEntry()`：正式入口不用 `?dev=1`。它量首頁和角色列表、建角頁，並檢查「首頁選單只有開始」。

### 1.3 美術 PM 的 14 項追加

| # | 來源 | 項目 | 做法 |
|---|---|---|---|
| 1 | 第一則 1 | 戰鬥反應詢問改成危險類 | `DialogFrame` 加 `tone`，反應詢問傳 `tone="danger"`，上緣加紅帶和「！」。紅帶在 `.decision-card` 裡左右貼齊。 |
| 2 | 第一則 2 | `DialogFrame` 避開 HUD | 新的 `DialogHudBox` context，加上 `hud.ts` 的 `dialogBox()`：沿用 6F-3 的 `popupBox`，再加上舞台上緣在視窗裡的位置（`useHudStage` 多回傳 `top`）。大世界的開場、配點教學、升級、「你不在的時候」都走 hud 位置，這時不顯示「移到下方」。戰鬥照舊。800×600 實測：視窗上緣 132，主角卡下緣 121。 |
| 3 | 第一則 3 | 遇敵標題 | 「遇敵！霧渡鎮」改成「遇敵：霧渡鎮」，紅帶上的「！」保留。開發頁的主題對照也一起改。 |
| 4 | 第一則 4＋複查 2 | 小框飾件 | 新的 `ui/smallFrames.ts`：一個 ResizeObserver 量每個 `.rt-frame` 的高度，64px 以下就標 `data-rt-small`，飾件換成 70%（`--rt-corners-small`，12.6px）。左右內距改成「原本＋6px，且至少 16px」：70% 飾件到內緣只佔 14.6px，所以四個角都讓開靠邊的按鈕和頭尾的字。任務框和戰鬥主角卡內容多時會超過 64px，另外標成 `data-rt-compact`，一律照小框處理（任務框的「－」和「▸ 詳細」）。標上之後要高過 88px 才拿掉，避免加了內距後折行又來回切換。 |
| 5 | 第一則 5 | 頭像框色淡入 | `HudPortrait` 的外圈加 class，框色寫在 style 裡，CSS `transition: stroke 0.3s`，減少動態時直接換。畫法沒改。 |
| 6 | 複查 1 | 重拍 rt1 截圖 | 01、04、06、07 用同一個角色重拍前後對照。11 拍整頁，七區都在。見第 4 節。 |
| 7 | 複查 3 | 設定面板 | 改用 `PopupFrame` 的 hud 位置，照 6F-3 避開四角 HUD。加標題列「設定」和 × 鈕，拿掉頂端那條空的分隔線，底部停在功能列上方 8px。`usePopupMenu` 多一個 `panelRef`，面板不在齒輪的外層裡時，點面板不算「點外面」。1600 實測：面板 610～990、173～727；金錢列、任務框都在 1362 以右，功能列從 815 開始，都沒蓋到。 |
| 8 | 複查 4 | 地點面板、背包面板不透明 | `.ui-popup.world-hud-panel` 底色改成 `--ui-navy`（不透明）。原本是 0.97。 |
| 9 | 複查 5 | 事件卡內框 | 說書人框 `.world-dialog` 和輸入框 `.world-answer` 改成 `--ui-navy-deep` 加金色細框。 |
| 10 | 複查 6 | 「瞄準」框收進面板 | 那是「更多動作」選單 `.more-list`。原本固定 220px、靠右，800 寬時往左超出 18px。改成和按鈕同寬。實測：選單 561～763，面板 561～763。 |
| 11 | 複查 7 | 捲動區讓出飾件 | 大世界浮動面板的捲動區上下各留 18px，詢問視窗的捲動區下緣多留 6px，捲動後的字不會跑到四角飾件底下。 |
| 12 | 複查 8 | 腰包標題 | 改成和「其他物品」一樣的 `section-title`，數字前面加全形空格，數字用小字。 |
| 13 | 複查 9 | 開發頁事件卡的場景 | `storyGallery` 的事件加上 `region: "cloud_ridge"`，背景從主城換成雲嶺，對上「霧渡鎮・斷橋」。 |
| 14 | — | 順手修 | `DialogFrame` 在大世界加的 class，原本取名 `world-dialog`，和事件卡說書人框的 class 撞名，已改成 `world-hud-dialog`。 |

## 2. 檔案清單

**新增**

- 內容與 Python：`content/ui/game.yaml`、`src/trpg/content/ui_game.py`、`tests/content/test_game_info.py`
- 前端：`client/src/ui/gameInfo.ts`、`EntryShell.tsx`、`EntryBackdrop.tsx`、`smallFrames.ts`、`client/src/render/entryScene.ts`、`client/src/styles/entry.css`
- 測試：`client/src/ui/uiE1.test.ts`
- 截圖：`docs/art/ue1_*`，共 46 張

**修改**

- Python：`src/trpg/content/registry.py`
- 入口畫面：
  - `client/index.html`、`client/src/main.tsx`
  - `screens/HomeScreen.tsx`、`StartScreen.tsx`、`RunNewScreen.tsx`、`RunScreen.tsx`
  - `world/WorldCharacterPicker.tsx`、`run/RaceOriginPicker.tsx`、`run/StartPicker.tsx`（加武器圖示）
- 追加項目：
  - `ui/DialogFrame.tsx`、`DecisionDialog.tsx`、`PopupFrame.tsx`（`frameRef`）、`usePopupMenu.ts`（`panelRef`）、`HeroCard.tsx`、`regionCorners.ts`、`regionTheme.ts`
  - `world/WorldHud.tsx`、`WorldPanel.tsx`、`HudIcons.tsx`、`EconomyPanel.tsx`、`hud.ts`、`useHudStage.ts`
  - `screens/WorldScreen.tsx`、`dev/storyGallery.tsx`、`dev/themeGallery.tsx`
- 繪製：`render/worldMapPainter.ts`，只多了 `bare` 選項，畫法不變。
- 樣式：`styles/index.css`、`theme.css`、`world-hud.css`、`world.css`、`skill-bar.css`、`world/story.css`
- 開發工具與測試：`dev/layoutSmoke.ts`、`ui/floatCardRule.test.ts`（`DialogFrame` 的 className 改成樣板字串，正規式跟著放寬）

**沒碰**

- 人物繪製：inkDoll、inkStyle、`portrait.ts` 的畫法。建角預覽只留位置。
- `src/trpg/llm`、`content/llm`。
- 世界 HUD 各塊的內部排版：只改了框的內距和飾件，以及設定面板的位置。

## 3. 測試

- **vitest**：新增 `uiE1.test.ts`，30 個。
  - 遊戲名稱：等於內容檔的值；只有 `gameInfo.ts` 匯入 yaml；`.tsx` 裡沒有寫死的名稱；檔案壞掉時退回空位。
  - 入口畫面：首頁選單只有「開始」；五個畫面都用 `EntryShell`；`entry.css` 的選擇器都在 `.entry-` 範圍內；建角按鈕的文字；預覽沒有呼叫任何人物繪製；步驟會編號；路線圖有 Boss 紋章。
  - 背景：場景是確定的；cover 的像素計算；`bare` 只貼本體與前景（貼圖次數）；sticky 不會被 `overflow: hidden` 打斷。
  - 14 項追加各有對應的測試。其中詢問視窗在三個尺寸 × 隊友 0／2 人下，都不碰任何 HUD 塊。
- **6.5.1 規則**：`floatCardRule.test.ts` 全過，包括「禁用原生 `title=`」。`EntryPlaque` 的 prop 因此取名 `heading`，不叫 `title`。
- **Python**：`tests/content/test_game_info.py` 共 7 個，包括「client 的 .tsx 沒有寫死名稱」。
- **交件前的檢查**：
  - client 全部 vitest：237 個檔、2636 個全過（結束碼 0）；
  - `corepack pnpm -C client build` 結束碼 0（含 `tsc --noEmit`）；
  - Python `tests/content` 加 `tests/cli/test_cli.py` 共 2674 個全過；
  - `ruff check`、`ruff format --check`、`mypy`（新檔與 registry）、`lint-imports`（13 個契約）全過；
  - `trpg content check` 通過。

## 4. 實機驗證

設定：API 8355，加 `TRPG_DEV_ROUTES=1`，存檔與帳號放在 `scratchpad/e1/`。新版 vite 用 5355，舊版對照（main `b8207d6e`）用 5356。無頭 Chrome 加 `--mute-audio`，網址加 `?mute=1`。

### 4.1 排版煙霧檢查

先 `localStorage.clear()` 再重新載入，三個尺寸（1600×900、1040×624、800×600）各跑三項，**9 項都是全 PASS**，0 個 FAIL：

- `runEntry`：正式入口，`/?mute=1`；
- `runScreens`：全站，`/?dev=1&anim=0.1`，已含新的「角色列表與建角」階段；
- `runCase`：戰鬥，`/?dev=1&anim=0.1`。

### 4.2 6.5.1 浮動卡實測

實測對象是建角頁「矮人」種族卡的說明卡（這一段換皮的畫面）。

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過觸發元素 → 卡片出現，貼齊卡片上方 | ✓（卡 301～425，觸發 425～474） | ✓（151～275，觸發 275～324；右緣 796，被推回畫面內） |
| 從觸發元素滑進卡片 → 不關 | ✓ | ✓ |
| 在卡片內捲到底 → 不關 | ✓（卡片 116px，沒有可捲的內容，只確認不關） | ✓（同左） |
| 點一下釘住 → 滑出去不關 | ✓（pinned） | ✓ |
| Esc → 關閉 | ✓ | ✓ |

截圖：`ue1_float_1600_pinned.jpg`、`ue1_float_800_pinned.jpg`。

### 4.3 截圖（`docs/art/`）

`_before` 是 main `b8207d6e`，`_after` 是這一段。

| 檔名 | 內容 |
|---|---|
| `ue1_01_home_*` | 正式首頁 |
| `ue1_02_char_list_*` | 角色列表（建角頁上半） |
| `ue1_05_create_*` | 建角頁步驟區，已選人類與第一個出身 |
| `ue1_03_run_new_*` | 開新一輪 |
| `ue1_04_route_map_*`（另有 `_800`） | 一輪路線圖 |
| `ue1_fix_dialog_*_1600／_800` | 追加 2：開場對話框避開主角卡（before 在 800 時蓋到主角卡右半） |
| `ue1_fix_hud_*` | 追加 4、5：任務框的小框飾件與內距、頭像框 |
| `ue1_fix_settings_*` | 複查 3：設定面板 |
| `ue1_fix_bag_*` | 複查 4、7、8：背包不透明、捲動區、腰包標題 |
| `ue1_fix_more_*_800` | 複查 6：「更多動作」選單收進面板 |
| `ue1_fix_event_*` | 複查 5、9：事件卡內框改深藍、場景改成雲嶺 |
| `ue1_rt1_01_capital_hud_*`、`ue1_rt1_04_dialog_*`、`ue1_rt1_06_bag_*`、`ue1_rt1_07_settings_*` | 重拍 rt1 的 01、04、06、07。before 和 after 是同一畫面、同一種新角色 |
| `ue1_rt1_11_theme_gallery_*` | 重拍 rt1 的 11：整頁，七區都在 |

**沒有截圖、只用 vitest 鎖住的項目**：
- 追加 1：反應詢問的紅帶。要有敵人行動觸發的時機，固定種子的煙霧戰鬥裡沒碰到。
- 追加 3：遇敵標題。capital 沒有遇敵。

## 5. noqa

無。

## 6. 待 PM 決定

以下都照最保守的做法先做完了：

1. **首頁選單**：`home-v2.png` 畫的是「繼續／建立新角色／roguelite 一輪／設定」，但任務單寫「正式入口只有開始」（6F-1），所以正式首頁只放「開始」，下面加一行說明。要不要改成樣張的四顆（「繼續」寫最近的角色），請 PM 決定。「繼續」需要讀角色列表，不用新 API。
2. **建角預覽**：只留位置，框裡寫「Q 版人物完成後顯示在這裡」，下面寫名字和「種族・出身・武器」。種族卡也照舊是文字卡，等 Q 版再換頭像。
3. **建角頁的流程**：照「不改流程」，武器和關鍵字還在建角頁。4.3（#134）把它們移到工坊靶場，那要另開一段。
4. **遇敵標題的寫法**：「遇敵！霧渡鎮」如果只拿掉「！」會變成「遇敵霧渡鎮」，所以改成「**遇敵：**霧渡鎮」。如果要別的分隔方式（例如「遇敵・」），請美術 PM 指定。
5. **小框的範圍**：
   - 用高度 64px 判斷，加上兩個點名的資訊塊（任務框、戰鬥主角卡）一律算小框。
   - 探索主角卡（74px）不算小框，雲嶺朱紅點壓到 HP 條右端的問題這段沒處理，要不要也標成小框？
   - 小框的內距是「原本＋6，且至少 16px」，比只加 6px 多一點，任務框每行的字因此少約 10px 寬。
6. **設定面板的位置**：改到中央（照 HUD 規則），不再貼著齒輪。背包等面板和設定面板同時打開時，設定面板蓋在上面。
7. **一輪畫面整頁套用入口外觀**：除了路線圖，一輪畫面的其他面板（升級、營火、戰後三選一）也一起換成深藍金框和新按鈕樣式。煙霧檢查全過，但升級、營火、三選一畫面沒有另外拍截圖給美術 PM 看。
8. **瀏覽器分頁標題**：現在是「（遊戲名稱）」，開發模式加「（開發模式）」。名稱定案前分頁上會顯示括號字樣。
9. **詢問視窗在大世界不能「移到下方」**：位置改由 HUD 規則決定。戰鬥裡照舊可以移。

## 7. 備註

- 暫存檔都在 `scratchpad/e1/`，沒有 commit：CDP 腳本、測試存檔與帳號、舊版對照的 client、煙霧檢查原始輸出。`client/vite.ue1.config.mts` 是實機驗證用的暫時設定，同樣沒有 commit。
- 自己啟動的 API（8355）、vite（5355、5356）、Chrome 都只用 PID 結束。
