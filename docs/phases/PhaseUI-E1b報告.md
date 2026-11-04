# Phase UI-E1b 報告：美術 PM 驗收 UI-E1 的 9 條修正＋UI-E1 待決 2 條定案

實作者，2026-11-05。分支 `worktree-agent-a7b637f269120a32a`，從 main `302d83eb` 開始，沒有 push，也沒有合併。

這一段只換外觀。流程、API、規則都沒動：送出的資料、伺服器欄位、`WORLD_RULES_VERSION`、`LOG_FORMAT` 都沒變。人物繪製（inkDoll、inkStyle、`portrait.ts`）沒碰，種族頭像、人物預覽照舊只留位置。

## 1. 逐項對照

截圖都在 `docs/art/ue1b_*`，共 41 張。

| # | 項目 | 做法 | 截圖 |
|---|---|---|---|
| 1 | 建角頁照 create-v2 | **種族**：改成 5 欄格子卡，每張卡有「頭像位置（空框，等 Q 版）＋名字＋發源：區名」，外框是發源區的區域色（`region_themes.yaml` 的 accent）。<br>**右側展開欄**：選中種族後，在格子右邊列出名字、發源、一句簡介、種族技（每場次數、AP、不佔技能欄）、環境被動，最下面是膠囊「判定加值：交涉 +1」，滑過顯示「情境判定用這類方法時 +1」。判定加值讀 `situation_rules.yaml` 的 `race_methods`、`methods` 名稱與 `check.race_bonus`。<br>**出身**：五張紋章卡，每張是六角金框紋章（晶冠王冠、雲嶺雙峰、樞市齒輪、荒原火焰、霜潮浪紋，配區域色）＋區名＋短描述。下面一行是選中出身的長說明（`description_zh`）。<br>**關鍵字**：每顆鈕名字前加 12 種程式繪製的小圖示。<br>**內容**：`races.yaml` 加 `blurb_zh`、`origins.yaml` 加 `tagline_zh`，文字照玩法 PM 定稿。pydantic 欄位必填、不可空，上限分別是 40 與 16 字。前端照遊戲名稱的做法，build 時用 `?raw` 匯入同一份 yaml，**不新增 API 欄位**。 | `01_create_1600`、`01_create_races_800`、`01_create_origins_800`、`01_create_go_1600／800`（建立並在主城醒來） |
| 2 | 武器圖示 | `.weapon-icon` 墊淺色圓底（`#f6eed8`→`#d6c7a2`）加金色細框，畫法不變。 | `02_weapons_keywords_1600／800`（含關鍵字小圖示） |
| 3 | 飾件不能壓到內容 | **主角卡**：頭像從 left 7 移到 18（直徑 62 的圓不再伸進左上、左下飾件），三條改成 86～227（讓出右上），階級鈕從 left 2 移到 23（原本壓在左下飾件上），等級、補給、靈感跟著右移。<br>**遇敵卡**（危險類通用）：紅帶改成絕對定位、左右各從 22px 起，讓出四角；「！」往右 4px，內容上內距 20px。遇敵卡左右內距 12→20px（見待決 3）。<br>**通用**：所有 inline 彈窗（事件卡等）、入口畫面的框、入口畫面裡的舊 `.panel` 左右內距改 20px；HUD 面板捲動區上下 18→20px。<br>**自動量測**：新增 `ui/cornerClear.ts`（純函式：四角正方形、重疊判定、圓形內容照內切圓、捲出可見範圍不算）。`layoutSmoke` 每個階段多一列「四角飾件沒有壓到內容」（`runEntry`、`runScreens`、`runCase` 都量），量所有畫飾件的框（`.rt-frame` 與入口畫面的 `.panel`）裡的文字（逐行）、按鈕、輸入框、圖示、資源條。HUD 有縮放時，飾件尺寸跟著乘倍數。`window.__layoutSmoke.corners()` 可單獨跑；開發頁（主題對照、劇情頁）有 `window.__corners()`。 | `03_hero_card_1600／800`、`03_capital_hud_1600／800`、`09_cloud_hero_card_1600`、`09_encounter_1600／800`、`03_theme_gallery` |
| 4 | 事件卡內框線 | 說書人框、輸入框的框線改成新變數 `--ui-gold-faint`（亮金 45%）。 | `04_event_card` |
| 5 | 設定面板切半的字 | hud 面板（含設定）與詢問視窗的捲動區，最後面加一塊 sticky 漸層（16px，透明漸到底色）。內容超出時黏在捲動區底部；捲到底時落在內容後面的空白處，最後一行照常清楚。 | `05_settings_scrolled_800`（捲到一半）、`05_settings_1600` |
| 6 | 浮動說明卡 | `float-panel`、部件說明框、一句話說明都改成深藍底（`--ui-navy`）金框。釘住時框線換亮金，右上角加一個金色圖釘圓記號。格子資訊卡原本就有圖釘，不動。6.5.1 實測見第 3 節。 | `06_float_1600_pinned`、`06_float_800_pinned` |
| 7 | 路線圖 | 連線 2px、35% 暗金，改成 3px、亮金 70%，加一圈暗邊；打完的段是實心亮金。「存檔／回首頁」改用新的入口按鈕樣式 `.entry-btn`，和首頁選單的次要鈕同一套（上半亮、下半暗的深藍、淺色細框，滑過換金框）。 | `07_route_map_1600`、`07_route_map_800`（已捲到節點區） |
| 8 | 鎖頭徽章 | `bare` 模式（入口背景）不畫未開放島的鎖頭徽章：`islandBody` 多一個 `badge` 參數，離屏圖的快取鍵也帶上它。大世界圖照舊畫。 | `10_home_*`、`07_route_map_1600`（背景都沒有鎖頭） |
| 9 | 補拍與重拍 | 800 寬路線圖（捲到節點區）；建角送出鈕；雲嶺 HUD；反應詢問紅帶；「遇敵：地點」標題；升級、營火、三選一（裝備三選一、完整技能三選一），1600 與 800 各一張。<br>**反應詢問與遇敵卡**：實機要等敵人行動或在實地地圖上碰到敵人才出現，所以在開發頁 `story-gallery.html` 加 `#encounter`、`#reaction` 兩個場景。用的是正式元件（`EncounterPanel`、`DecisionDialog`）加固定資料，真的畫出來。 | `07_route_map_800`、`01_create_go_*`、`09_cloud_hud_1600／800`、`09_reaction_1600／800`、`09_encounter_1600／800`、`09_level_up_*`、`09_campfire_*`、`09_gear_offer_*`、`09_complete_offer_*` |
| 10 | 首頁四顆鈕 | 繼續、建立新角色、roguelite 一輪、設定。<br>**繼續**：第二行寫最近的角色，例如「霜月 Lv 1・雲嶺・霧渡鎮」。優先用瀏覽器記住的角色，沒有就用列表第一個；沒有角色時停用，寫「還沒有角色」。<br>**讀角色列表**：用現有的 `GET /world/characters`，改成背景請求，收到 401 不導到登入畫面；沒登入、也不是開發模式時直接不讀。<br>**建立新角色**：清掉記住的角色，進大世界的角色畫面。<br>**roguelite 一輪**：進開新一輪。<br>**設定**：在同一個選單框裡展開聲音、減少動態，按「返回」收回，不另開彈窗。<br>開發選單照舊在 `?dev=1`。 | `10_home_no_char_1600／800`（停用，固定狀態）、`10_home_continue_1600／800`、`10_home_settings_1600` |
| 11 | 同時只開一個彈窗 | 新增純函式 `hud.ts` 的 `popupsToClose`。`WorldHud` 的規則：按齒輪先關掉面板與地圖再開設定；面板（點圖示或快捷鍵）或地圖打開時，關掉設定。面板之間本來就只開一個。鎖住的面板（閃現、三選一待選）不能關，設定照常可以開在上面。 | `11_bag_closes_settings_1600`（開著設定按 I）、`11_settings_closes_bag_1600`（開著背包按齒輪）；實測狀態 `{settings:false, panel:"bag"}` → `{settings:true, panel:null}` |

## 2. 檔案清單

**新增**

- 前端：
  - `client/src/run/createTexts.ts`（種族簡介、出身短描述、判定加值，從 yaml 讀）
  - `client/src/ui/CreateIcons.tsx`（五區紋章、關鍵字小圖示）
  - `client/src/ui/cornerClear.ts`（飾件量測的純函式）
- 測試：
  - `client/src/ui/uiE1b.test.ts`（27 個）
  - `tests/content/test_create_texts.py`（9 個）
- 截圖：`docs/art/ue1b_*`，41 張

**修改**

- 內容與 Python：`content/races.yaml`、`content/origins.yaml`、`src/trpg/content/races.py`
- 前端：
  - 入口：`App.tsx`、`api/client.ts`（`worldCharactersQuiet`）、`screens/HomeScreen.tsx`、`screens/RunScreen.tsx`、`run/RaceOriginPicker.tsx`、`run/StartPicker.tsx`
  - 大世界：`screens/WorldScreen.tsx`、`world/WorldHud.tsx`、`world/hud.ts`
  - 繪製：`render/worldIslandArt.ts`、`render/worldMapPainter.ts`（只多了「bare 不畫徽章」）
  - 開發工具：`dev/layoutSmoke.ts`、`dev/storyGallery.tsx`、`dev/themeGallery.tsx`
  - 樣式：`styles/entry.css`、`styles/theme.css`、`styles/float-card.css`、`styles/world-hud.css`、`styles/world.css`、`world/story.css`
  - 既有測試跟著改：
    - `ui/uiE1.test.ts`：首頁四顆鈕、紅帶的新寫法、捲動區 20px
    - `ui/floatCardRule.test.ts`：float-panel 的底色允許 `var(--ui-navy)`

**沒碰**

- 人物繪製：inkDoll、inkStyle、portrait。
- `src/trpg/llm`、`content/llm`、world 的閃現與劇情技能。
- skill_composer、新手任務內容。
- 戰鬥的浮動字、技能列、範圍技。

## 3. 測試與實機驗證

### 3.1 自動測試

- **client 全部 vitest**：238 個檔、2663 個全過（結束碼 0）。其中新的 `uiE1b.test.ts` 27 個，11 條每條都有。
- **`corepack pnpm -C client build`**：結束碼 0，含 `tsc --noEmit`。
- **6.5.1 規則**：`floatCardRule.test.ts` 全過，包括「禁用原生 `title=`」。這段沒有新增 `Math.random`。
- **Python**：`tests/content` 加 `tests/test_architecture.py`，`UV_NO_SYNC=1`、`-n 6`，共 2689 個全過。
  - 其中 `test_create_texts.py`：定稿文字、十族判定加值、必填、不可空、長度上限。
  - `trpg content check` 通過。
  - `ruff check`、`ruff format --check`、`mypy`（改到的檔）、`lint-imports`（13 個契約）全過。

### 3.2 排版煙霧檢查

設定：API 8355，加 `TRPG_DEV_ROUTES=1`，cwd 是 `scratchpad/e1b/`；vite 5355；無頭 Chrome 加 `--mute-audio`，網址加 `?mute=1`。每項都先 `localStorage.clear()` 再重新載入。

| 尺寸 | `runEntry`（`/?mute=1`） | `runScreens`（`/?dev=1&anim=0.1`） | `runCase` |
|---|---|---|---|
| 1600×900 | 全 PASS（13 列，其中飾件 4 列） | 全 PASS（126 列，飾件 42 列） | 全 PASS（10 列，飾件 1 列） |
| 1040×624 | 全 PASS（13） | 全 PASS（126） | 全 PASS（10） |
| 800×600 | 全 PASS（13） | 全 PASS（126） | 全 PASS（10） |

**飾件量測找到並修掉的問題**（量測是這一段新加的）：
- 入口畫面各框左上的標題、左下的字、建角送出鈕；
- 開新一輪表單左下的字；
- 事件卡左下的「0／500」；
- 主題對照頁的事件卡；
- 主角卡的 HP 條、階級鈕、頭像；
- 任務框（量法修正：被省略號裁掉的字不算）；
- 設定面板捲動區下緣。

大世界 HUD（主城、雲嶺，1600、800）、設定面板、開發頁（遇敵、反應、事件、主題對照），以及升級、營火、兩種三選一，也都另外跑了 `corners()`，全部回空。

### 3.3 6.5.1 浮動卡實測

實測對象：建角頁「矮人」種族卡的說明卡。

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過觸發元素 → 卡片出現，貼齊上方 | ✓（卡 274～398，觸發 398～503） | ✓（124～248，觸發 248～353；右緣 768，在畫面內） |
| 從觸發元素滑進卡片 → 不關 | ✓ | ✓ |
| 在卡片內捲到底 → 不關 | ✓（卡片 116px，沒有可捲的內容，只確認不關） | ✓（同左） |
| 點一下釘住 → 滑出去不關 | ✓（pinned，右上角出現圖釘記號） | ✓ |
| Esc → 關閉 | ✓ | ✓ |

## 4. noqa

無。

## 5. 待 PM 決定

以下都照最保守的做法先做完了：

1. **判定加值的顯示**：只寫「判定加值：交涉 +1」一個膠囊，說明放在滑過（照玩法 PM 文字）。樣張另有一個小標「判定加值」和膠囊右邊的說明字，這兩樣沒有放。
2. **出身卡的標題**：照樣張寫區名（「雲嶺」），不寫「雲嶺出身」。展開說明那一行寫完整的「雲嶺出身：……」。
3. **遇敵卡左右內距**：美術 PM 要求加 6px（12→18）。但飾件佔外框 2＋2＋18＝22px，加 6 時第一個字離外緣 20px，仍會壓到飾件 2px，所以改成加 8（20px）。這條同時套到所有 inline 彈窗、入口畫面的框與 `.panel`，內容寬度每邊少 4～8px。
4. **鎖頭徽章**：選了「bare 模式不畫」。首頁與路線圖背景上，未開放的島只剩去色與纏雲，沒有鎖頭。
5. **首頁「繼續」接哪個角色**：瀏覽器記住的（上次進過的）優先，否則列表第一個。伺服器的角色列表沒有時間欄位，所以不是嚴格的「最近」。正式模式沒登入時一律停用，不先跳登入畫面。
6. **首頁「設定」**：在選單框裡展開聲音與減少動態，沒有「重新顯示提示」那一區（那一區要有角色）。
7. **同時只開一個彈窗的例外**：閃現、三選一待選時面板鎖住、不能關，這時按齒輪，設定會疊在鎖住的面板上面。
8. **反應詢問、遇敵卡的截圖用開發頁**：`story-gallery.html#reaction`、`#encounter`，正式元件加固定資料。實機沒有拍到這兩個時機。
9. **說明卡換色的範圍**：深藍金框套到全站的 float-panel、部件說明框、一句話說明，戰鬥畫面的說明卡也一起換了。技能卡浮動卡、格子資訊卡沒動。
10. **捲動區漸隱只做下緣**：上緣捲動後也會切到字（例如 800 寬設定面板的「音樂」那一行），這段沒有處理。

## 6. 備註

- 暫存檔都在 `scratchpad/e1b/`，沒有 commit：CDP 腳本、測試存檔與帳號、煙霧檢查的原始輸出。`client/vite.ue1b.config.mts` 是實機驗證用的暫時設定，同樣沒有 commit。
- 自己啟動的 API（8355）、vite（5355）、Chrome 都只用 PID 結束。
- 內容檔多了 `blurb_zh`、`tagline_zh`，所以內容雜湊 `content_digest` 會變。舊的大世界日誌會照既有機制標成「規則或內容改了，不能重播」，任何內容改動都一樣。
