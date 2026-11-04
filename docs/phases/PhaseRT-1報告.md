# Phase RT-1＋UI-E2 報告：區域主題點綴、HUD 與彈窗統一

實作者，2026-11-04。分支 `worktree-agent-aa2dc2876fcc5e56d`（從 main `71eb8352` 開始），沒有 push、沒有合併。只換外觀，規則、伺服器欄位、版面、字型、按鈕都沒有動。

## 1. 做了什麼

### 1.1 RT-1 區域主題點綴

- **資料**：`content/ui/region_themes.yaml`。
  - 七個主題：`hub`、`capital`、`cloud_ridge`、`ashen_waste`、`crystal_crown`、`arcane_hub`、`frost_tide`。
  - 每個主題的欄位：`accent`、`corner`、`plaque`、`portrait_ring`、`ink`、`seal`、`wait_fx`。另有 `plaques:` 表，存標題牌材質的兩色漸層。
  - `ink`、`seal`、`wait_fx` 留給 RT-3 的等待動畫讀。`wait_fx` 的值：荒原 `ember`、主城和 hub `crystal`、其他 `none`。
- **Python**：
  - `src/trpg/content/ui_themes.py`：`RegionThemeTable` 的 pydantic schema，檢查以下幾點：
    - 顏色是 `#rrggbb`；
    - 飾件只能是六種之一；
    - 標題牌必須在 `plaques` 表裡；
    - 一定要有 `hub`；
    - `extra="forbid"`。
  - 另有 `theme_for()`：拿不到區域時用 hub。
  - 已登記進 `registry.py`，`trpg content check` 會顯示「7 個區域主題（6 種四角飾件、6 種標題牌）」。
- **前端讀取**（照 AU-2 的 `sfx.yaml` 做）：`client/src/ui/regionTheme.ts` 在 build 時用 `?raw` 匯入 yaml，再自己做一次結構檢查；壞掉的那筆略過，退回 hub。
- **目前區域**：不新增伺服器欄位。
  - 大世界讀 `field.region`（主城與室內是 `capital`），沒有就用 `map.region`；
  - 戰鬥讀 `BattleView.region`；
  - 都拿不到時用 hub。
  - 畫面用堆疊管理：在大世界裡開戰鬥時用戰鬥的區域，戰鬥結束退回大世界，全部離開退回 hub。
- **CSS 變數**：`--rt-accent`、`--rt-ring`、`--rt-ink`、`--rt-seal`、`--rt-plaque-top`、`--rt-plaque-bottom`、`--rt-corners`，寫在 `<html>` 上。
- **換區淡入**：換區域時點綴淡入 0.3 秒（`data-rt-swap` 依 a／b 交替，0.4 秒後拿掉）。減少動態時直接換。
- **四角飾件**：`client/src/ui/regionCorners.ts`。
  - 六種，每種 18×18 的 SVG，照樣張 `region-themes.html` 的 `corner()` 畫，另外三角用鏡射。
  - 疊在 `.rt-frame::after` 上，`z-index: -1` 加 `isolation`：飾件在底色之上、文字之下，不接滑鼠、不佔版面。
- **套用的位置**：
  - 四角飾件：主角卡、小地圖、任務追蹤、功能列、所有共用彈窗。
  - 標題牌：地名條換成區域漸層，內框加一道區域色細線。
  - 強調色：功能列鈕滑過與選取時的細光。
  - 頭像框：主角頭像框換成區域的 `portrait_ring`。
- **開發頁**：`client/theme-gallery.html`。七區並排，後三區的飾件也看得到（`rt1_11_theme_gallery.jpg`）。

### 1.2 UI-E2 HUD 與彈窗統一

- **#4 顏色變數**：新檔 `client/src/styles/theme.css`，定義 `--ui-navy` `#1e2236`、`--ui-panel`、`--ui-panel-solid`、`--ui-gold` 等變數。
  - 大世界的 `--hud-panel` 和戰鬥的 `--hud-bg` 都改成接這組變數。
  - 舊的炭黑 `rgba(24,20,16,…)` 全部移除，有測試鎖住。
  - 首頁和建角頁不套用這些 class（UI-E1 沒動）。
- **#5 主角卡**：新的共用元件 `client/src/ui/HeroCard.tsx`，左邊頭像、右邊三條。
  - 戰鬥：多了頭像（44px），名字仍在條的上方。窄螢幕的 compact 版只有三條和圖示。
  - 探索：多一條細的耐力條（5px），條的順序是 HP、法力、耐力、經驗。
  - 頭像用現有的 `HudPortrait`，畫法沒改。
- **#6 共用彈窗元件**：`client/src/ui/PopupFrame.tsx`。
  - 位置有三種：
    - `hud`：沿用 6F-3 的 `popupBox`，上緣在主角卡下方、讓出左右兩欄、下緣停在功能列上方；
    - `dialog`：沿用 `.decision-card`，靠上或靠下；
    - `inline`：中上方欄裡的卡片。
  - 外觀：深藍底、金框、四角飾件、單層。內容在 `.ui-popup-body` 裡捲，捲動時飾件不會跟著跑。
  - 危險類（遇敵卡）只在上緣加一條紅帶和「！」。
  - 已經改用這個元件的：大世界的浮動面板（背包、技能、NPC、地點…）、遇敵卡、事件卡、`DialogFrame`。
  - 因為改了 `DialogFrame`，戰鬥的反應詢問、複製、灌注、誓約，以及大世界的開場、配點教學（6F-4）、升級、你不在的時候，都一起收進共用元件。
- **#12 拿掉內框**：彈窗裡的 `.panel` 不再畫第二層框，區塊之間改用細分隔線（`rt1_05_npc_panel_after`、`rt1_06_bag_after`）。
- **設定面板**：新元件 `client/src/ui/SettingsHead.tsx`，分成聲音（喇叭）、減少動態（動態圓點）、提示（燈泡）三區，每區有標題和小圖示，區與區之間有細分隔線。戰鬥「版面」面板和大世界齒輪面板共用同一份。
- **隊友小卡**：改用 `StoryIcons.Portrait`，也就是 `portrait.ts` 的頭像，畫法沒改。
  - `mateCards` 依傭兵 id 到 `party.mercenaries` 取 `portrait` 與 `origin`，框色照出身區。
  - 影子、同伴、舊存檔找不到傭兵資料時，顯示剪影加金框。

## 2. 檔案清單

**新增**

- 內容與 Python：`content/ui/region_themes.yaml`、`src/trpg/content/ui_themes.py`、`tests/content/test_region_themes.py`
- 前端元件：`client/src/ui/regionTheme.ts`、`regionCorners.ts`、`PopupFrame.tsx`、`HeroCard.tsx`、`SettingsHead.tsx`
- 樣式：`client/src/styles/theme.css`
- 開發頁：`client/src/dev/themeGallery.tsx`、`client/theme-gallery.html`
- 前端測試：`client/src/ui/regionTheme.test.ts`、`client/src/ui/uiE2.test.ts`

**修改**

- Python：`src/trpg/content/registry.py`
- 前端畫面與元件：
  - `client/src/ui/DialogFrame.tsx`、`Hud.tsx`、`MotionSettingsSection.tsx`
  - `client/src/audio/AudioSettingsPanel.tsx`、`client/src/world/HintsSettingsSection.tsx`
  - `client/src/world/WorldHud.tsx`、`hud.ts`（`mateCards`）、`WorldPanel.tsx`（遇敵卡）、`EventCard.tsx`
  - `client/src/screens/WorldScreen.tsx`、`BattleScreen.tsx`（`useRegionTheme`）
- 樣式：`client/src/styles/index.css`、`world-hud.css`、`world.css`、`battle-hud.css`、`battle-panels.css`
- 前端測試：`client/src/world/hud.test.ts`（多 4 個）、`client/src/ui/floatCardRule.test.ts`

**沒碰**

- 人物繪製：inkDoll、inkStyle、inkGear、`portrait.ts` 的畫法；
- `src/trpg/llm`、`content/llm`；
- 主城廣場的 decor 與噴水；
- 首頁、建角頁。

## 3. 測試

- **Python**：`tests/content/test_region_themes.py` 共 23 個。
  - 內容：載入、登記、五區加 capital 加 hub 都有、六種飾件都用到、六區各自的挑選、拿不到區域退回 hub、RT-3 欄位。
  - 錯誤範例：飾件、顏色、標題牌、`wait_fx`、拼錯欄位、缺欄位、缺 hub、標題牌顏色不對。
- **vitest**：新增 46 個。
  - `regionTheme.test.ts`：前端結構檢查與錯誤範例、各區挑選、退回 hub、六種飾件與鏡射、CSS 變數、畫面堆疊。
  - `uiE2.test.ts`：
    - 共用彈窗的位置規則：1600×900、1040×624、800×600 三個尺寸 × 隊友 0／2 人 × 面板與中上方卡，都不蓋 HUD，元件真的把樣式寫到外框上；
    - 單層框、危險紅帶、`DialogFrame` 的結構；
    - CSS 變數只有一組；
    - 主角卡在探索和戰鬥共用（實際輸出加原始碼掃描）；
    - 設定面板的分區標題。
  - `hud.test.ts` 多 4 個：主角卡、隊友小卡用 portrait 頭像、面板用共用彈窗、標題牌與飾件。
  - `floatCardRule.test.ts`：
    - `NON_HOVER_POPUPS` 加上 `ui/PopupFrame.tsx`；
    - 新增一條「彈窗外框一律用 PopupFrame」，同時檢查舊的自製外框不再出現；
    - 原本的「`.decision-card` 可捲動」改成檢查 `.ui-popup-dialog > .ui-popup-body` 有 `overflow-y: auto`；
    - 「禁用原生 `title=`」那條照舊全過。
- **交件前的完整檢查**：
  - client 全部 vitest：235 個檔、2598 個全過；
  - `tsc --noEmit` 結束碼 0；
  - `corepack pnpm -C client build` 結束碼 0；
  - Python `tests/content` 共 2637 個全過；`ruff`、`mypy`、`lint-imports`（13 個契約）全過。

## 4. 實機驗證（API 8355、vite 5355，舊版對照 vite 5356；無頭 Chrome 加 `--mute-audio`，網址加 `?mute=1`）

### 4.1 6.5.1 浮動卡實測（功能列「技能」鈕的說明卡）

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過觸發元素 → 卡片出現（貼齊鈕的上方） | ✓（top 707／bottom 821） | ✓（436／550） |
| 從鈕滑進卡片 → 不關 | ✓ | ✓ |
| 在卡片內捲到底 → 不關 | ✓（卡片 106px 沒有可捲的內容，只確認不關） | ✓（同左） |
| 點一下釘住 → 滑出去不關 | ✓（pinned） | ✓ |
| Esc → 關閉 | ✓ | ✓ |

- 截圖：`rt1_13_float_1600_pinned.jpg`、`rt1_14_float_800_pinned.jpg`。
- **另外量了共用彈窗**（800×600 的背包面板）：外框 126～540，主角卡下緣 120，功能列上緣 546，沒有蓋到。內容 507／410，用滾輪捲到底（97），四角飾件留在原位，按 Esc 關閉（`rt1_12_bag_800_scrolled.jpg`）。

### 4.2 排版煙霧檢查

- 在 `/?dev=1&anim=0.1` 先 `localStorage.clear()`，再跑 `__layoutSmoke.runCase`。
- 1600×900、1040×624、800×600 三個尺寸都是「全 PASS」。

### 4.3 截圖（`docs/art/rt1_*`；有 `_before` 的是 main `71eb8352`，`_after` 是這一段）

| 檔名 | 內容 |
|---|---|
| `rt1_01_capital_hud_*` | 主城 HUD：紫晶捲紋飾件、水晶標題牌、紫色頭像框；隊友小卡改成傭兵頭像（賽倫、回春） |
| `rt1_02_cloud_hud_*` | 雲嶺 HUD：雲紋加朱紅點、玉色標題牌、綠色頭像框 |
| `rt1_03_ashen_hud_*` | 荒原 HUD：鐵角鉚釘、鐵色標題牌、橘色頭像框 |
| `rt1_04_dialog_*` | 開場對話框（`DialogFrame`）：原本是洋紅框，改成共用彈窗 |
| `rt1_05_npc_panel_*` | 地點面板（這裡的人／NPC）：拿掉內框，改用分隔線 |
| `rt1_06_bag_*` | 背包面板：單層 |
| `rt1_07_settings_*` | 設定面板：三區標題加小圖示 |
| `rt1_08_battle_card_*` | 荒原戰鬥的主角卡：頭像＋三條＋鉚釘飾件 |
| `rt1_09_event_card_*` | 事件卡（開發頁 `story-gallery.html?mode=event`） |
| `rt1_10_cloud_battle_800` | 雲嶺戰鬥（煙霧檢查的雲海吊橋）800×600 的主角卡 |
| `rt1_11_theme_gallery` | 開發頁：七區的飾件、標題牌、頭像框、事件卡、遇敵紅帶、RT-3 的墨色與封蠟 |
| `rt1_12_bag_800_scrolled` | 800×600 背包面板捲到底，飾件留在原位 |
| `rt1_13`、`rt1_14` | 6.5.1 實測：說明卡釘住 |

## 5. 待 PM 決定

以下都照最保守的做法先做完了：

1. **探索的耐力條**：大世界沒有耐力資料，而且這段不新增欄位，所以畫成滿格的細條。說明卡寫「戰鬥中的行動要花，每場開戰都是滿的」。如果要顯示真實數值，要另開段加伺服器欄位。
2. **探索主角卡不寫名字**：250×74 的卡放不下名字，名字放在頭像的說明卡裡。戰鬥卡照舊寫名字（用同一個 `hero-card-name` 樣式）。
3. **後三區標題牌的顏色是我擬的**：`marble`、`brass`、`sea` 樣張沒有給色。`wait_fx` 這個欄位也是我加的，給 RT-3 用，值是 `none`、`ember`、`crystal`。這兩項請美術 PM 確認。
4. **詢問視窗的位置**：`DialogFrame` 收進共用元件後，位置照舊（固定在上方 58px 置中，可以移到下方），沒有改成 6F-3 避開 HUD 的規則。大世界的開場、配點教學在 800×600 時可能碰到主角卡右緣。要不要改用 `hud` 位置？
5. **戰鬥詢問視窗的框色**：原本是醒目的洋紅框，統一後改成金框加區域飾件。反應詢問因此不再那麼搶眼。要不要讓反應詢問走危險紅帶？
6. **戰鬥 HUD 的其他塊**：右上的戰況、工具鈕、環境預告、技能列，只換了深藍底色，沒有加四角飾件。規格的表只列了「主角卡、功能列、任務、小地圖」。
7. **戰鬥主角卡改成外框不捲**：這樣四角飾件不會跟著內容跑。「▸ 詳細」打開時，改成在詳細區塊裡捲（最高 30vh）；原本是整張卡最高 40vh、整張捲。
8. **遇敵卡的「！」重複**：上緣紅帶的「！」和原本的標題「遇敵！…」重複了。標題文字沒改，要不要去掉？
9. **小框的飾件**：任務追蹤（寬 170）等小框，1600 寬時飾件放大到約 27px，會碰到第一、二行字的邊（飾件在文字底下，不會蓋字）。要不要把小框的飾件縮小？
10. **開發頁 `story-gallery.html` 的事件卡沒有四角飾件**：那一頁沒有載入主題模組。正式畫面有飾件（`rt1_11` 是主題開發頁）。
11. **雲嶺實戰的截圖**：開發用 Boss 入口在雲嶺被主線限制擋下，所以雲嶺戰鬥的主角卡用煙霧檢查的雲海吊橋那場代替（`rt1_10`）。
12. **頭像框色淡入**：主角頭像（`HudPortrait`）的框色換區時是直接換，沒有淡入。四角飾件有 0.3 秒淡入。

## 6. 備註

- 暫存檔都在 `scratchpad/rt1/`，沒有 commit：截圖原檔、CDP 腳本、測試存檔、舊版對照用的 client。
- `client/vite.rt1.config.mts` 是實機驗證用的暫時設定，同樣沒有 commit。
- 自己啟動的 API、vite、Chrome 都只用 PID 結束。
