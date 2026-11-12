# Phase PNL-1a 報告：資訊面板共用元件＋隊伍與影子

依據：`docs/art/資訊面板-移植需求.md`（美術 PM 第九任，使用者「照建議」）表 6 的 PNL-1a 列。起點 main `19b0213d`。PNL-1b／2／3／4 沒做。

## 1. 做了什麼

| 項目 | 檔案 |
|---|---|
| 分頁規則純函式：`pickTab`（第一頁整頁鎖住時改開金底數字的、再沒有就第一個沒鎖的）、`fitLevel`／`fitClass`（四級縮）、`tabHintText`、`badgeShowsValue`、`TabBadgeSpec` | `client/src/ui/panelTabRules.ts` |
| `PanelTabs`（固定區＋分頁列＋分頁內容；只有一頁時不畫分頁列）、`TabBar`（`ResizeObserver` 量分頁列寬加 `fit1`～`fit3`；字寬照粗體預留 `data-t`＋`::after`）、`TabBadge`（五種記號）、`paneVariants`；面板高度＝最高那一頁（每個摺疊打開各量一次），打開與面板寬度改變時量，鎖成 `min-height`，資料變多不重量 | `client/src/ui/PanelTabs.tsx` |
| `Callout`（警告／鎖住／資訊三級＋`sub`＋`end`）、`InfoTip`（(i)＝事件卡 `info`＋`<Hint>`）、`Chip`（0 灰）、`Tag`（open／live／mine／dim／info／lock／warn／細框）、`PanelHead`（襯線標題＋回到地點圖）、`TabLine`、`EmptyNote`、`FoldGroup`／`Fold`（`<details name>` 互斥＋`closeSiblings` 後備）、圖示 `HudBare`／`EventBare`／`EventRing`／`PartBare`／`LockGlyph`／`ClockGlyph`／`WarnGlyph`／`InfoGlyph`／`TokenGlyph` | `client/src/ui/PanelKit.tsx` |
| 事件卡圖樣本身（`QE.bareGlyph`）、事件卡圓環圖示、第④批部件圖樣（金鎖、鐘）的畫布快取（QI-6 裁定 6：快取在本段加；回畫布，沒做圖片網址） | `client/src/render/panelIcon.ts` |
| 樣式：樣張 `ip-*` → `pnl-*` 併進 `world-hud.css`（文字三級、提示三級、籌碼、標籤、摺疊、區塊標頭、清單列、欄名列、空狀態、分頁列、記號、隊友卡、影子數值格）；容器查詢 `.world-hud-panel { container: world-panel / inline-size }`＋`@container world-panel (max-width: 559px)` | `client/src/styles/world-hud.css` |
| `LimitNote` → `Callout tone="lock"`（提示句照舊由伺服器給，`data-testid` 不變）；舊 `.world-limit-note`／`.world-limit-banner` 樣式拿掉 | `client/src/world/limits.tsx`、`client/src/styles/range-ob.css` |
| 「隊伍與影子」面板：標題改字、回到地點圖、分頁「隊伍」（旗 `t_orders`、細框「3／3」、滑過「隊伍 3／3（含主角）」）｜「我的影子」（`bar_Y`、短名「影子」、還沒存＝琥珀三角）；成員卡（頭像 44、名字＋亮金「Lv N」、身分、「打法 …」不斷行、OB-8 來歷行；主角金框、劇情夥伴綠框＋綠底「劇情夥伴」）；面板 < 560 兩欄＋第 3 張撐滿；劇情夥伴說明、獨行＝資訊，賽季頭目限制、換隊友＝鎖住；影子分頁：琥珀「還沒存」＋一行小字、兩格數值、戰報或虛線空狀態 | `client/src/world/PartyShadowPanel.tsx`、`client/src/world/partyShadow.ts`、`client/src/world/HudPanels.tsx`（`HudShadowPanel` 改用新面板、多 `onClose`）、`client/src/screens/WorldScreen.tsx`（傳 `closeHud`） |
| 開發頁 `panel-gallery.html`：`#bar`（四級）、`#switch`（切分頁前後量邊緣）、`#kit`（提示、籌碼、標籤、摺疊）、`#party`（固定資料的面板） | `client/dev/panel-gallery.html`、`client/src/dev/panelGallery.tsx` |
| 測試 26 項 | `client/src/ui/pnl1aPanelKit.test.ts` |
| 上手筆記第一節加一列、第四節第 79～84 點、第五節加一列 | `docs/dev/上手-前端戰鬥畫面與動畫.md` |

沒有改 Python、`content/`、數值工坊相關檔、需求與計畫檔。

## 2. 第 5 節「要開發 PM 決定的事」本段怎麼做（一律照美術建議）

| # | 做法 |
|---|---|
| 4 | 併進 `world-hud.css`，前綴 `pnl-`（CSS 變數 `--pnl-*`） |
| 5 | 元件放 `client/src/ui/`（`PanelTabs.tsx`、`PanelKit.tsx`、`panelTabRules.ts`） |
| 6 | 原生 `<details name>`；`onToggle` 補一行 JS（`closeSiblings`）關掉同組其他的，不另寫元件 |
| 8 | 開著時不重量；面板寬度改變（視窗縮放）才重量；超過 `maxHeight` 在捲動區捲 |
| 9 | 本段沒有線頭；`TabBadge` 支援 warn，門檻留給 PNL-3 |
| 1、2、3、7、10、11 | 屬於 PNL-1b／2／3／4，本段沒碰 |

## 3. 既有測試的改動

無（舊 → 新：沒有）。`world/partyIntro.test.ts` 仍測 `PartyPanel`（雇用面板與舊側欄還在用的精簡清單，本段沒改）；`world/limits.test.ts` 原樣通過（`data-testid`、字不變）。沒有重產任何雜湊或快照。

## 4. 實測、量值、結束碼

**結束碼**（交件前各跑一次）：`corepack pnpm -C client typecheck` 0；`corepack pnpm -C client test --run` 0（319 檔、4139 passed）；`corepack pnpm -C client build` 0（只有既有的 chunk 大小警告）。第一次全量有 1 項失敗：開發頁 `SwitchGroup` 的 prop 叫 `title`，被 `floatCardRule` 當原生 tooltip，改名 `caption` 後全過。沒改 Python。

**實機做法**：自己的 `trpg serve --port 8765`（`TRPG_SAVE_DIR` 在暫存區、`TRPG_DEV_ROUTES=1`）、`vite --port 5199`（開發頁）、無頭 Chrome `--mute-audio`，網址帶 `?mute=1`；Node 24 內建 WebSocket 走 CDP。開發建角 `POST /api/world/characters {"name":"PNL","weapon":"one_handed_sword","keywords":["ignite","wet"]}`，localStorage `trpg.world.character` 寫角色 → 首頁「進入大世界（測試）」→「站起來」→ 按 Y。新角色只有主角＋賽倫；三人（劇情夥伴阿岳）用 `Page.addScriptToEvaluateOnNewDocument` 包 `window.fetch`，在 `party.members` 補一名 `companion`、補 `companion_zh`（程式與後端不動）。成長面板的鎖住提示同法補 `view.limits`（字＝`opening_limits` 的 flash／dissolve／oath）。結束後已用自己的 task／PID 關掉 serve、vite、Chrome，8765／5199／9333 都沒在聽。

**(a) 量到的固定區與面板高**（隊伍與影子；固定區＝標題列＋分頁列）

| 視窗 | 面板（寬×高） | maxHeight | 固定區 | 分頁區鎖高（最高那一頁） | 捲不捲 |
|---|---|---|---|---|---|
| 1600×900 | 720×316 | 632 | 74 | 190（隊伍頁） | 不用捲 |
| 800×600 | 493.3×381.8 | 381.8 | 74 | 272（隊伍頁，2＋1） | 隊伍頁要捲 48px（內容 386／可視 338）；影子頁不用 |

切分頁前後：兩個分頁按鈕的位置、面板外框（x、y、寬、高）在兩種寬度都完全相同（1600：隊伍 [456,234.5,113.3,34]、影子 [571.3,234.5,117,34]）。800 的實機面板是 493 寬、382 高，不是需求表的 514×477：開發入口上方有 60px 標題列（上手筆記第 84 點）。

**分頁列四級（開發頁 `#bar`）**：內寬 696＝第 0 級全名、486＝第 1 級短名、400／320＝第 2 級圖示、250＝第 3 級折兩列（高 69）；每一級 4 個記號都在。和需求 3.2 第 7 條的實測一致。**切分頁前後（`#switch`）**：公告板五頁、486（第 1 級）與 320（第 2 級）各換 5 種目前分頁，每個分頁左右上下緣最大差 0.0 px。

**摺疊**（`#kit`）：預設開「重閃」，點「溶掉或傳承」後 reflash:false、dissolve:true、oath:false（原生互斥）。

**浮動卡（6.5.1）**：觸發元素＝分頁「隊伍」（說明卡「隊伍 2／3（含主角）」）。1600×900 與 800×600 都是：滑過約 400 ms 卡片出現（上方）→ 分 8 步滑進卡片，卡片還在 → 卡內滾輪：卡片內容短（scrollHeight 36＝clientHeight 36），已經到底、沒有被關 → 點一下釘住（`.float-card.pinned`）→ 滑鼠移到畫面角落後仍在 → Esc 關掉卡片，面板仍開著。本段的說明卡都是一行，沒有長到要捲的卡。

**截圖**（`docs/art/shots/pnl1a/`，10 張，全部 ≤ 300 KB；PNG 只用在開發頁量測圖與最近鄰特寫）

| # | 檔 | 對應驗收 | 來源 |
|---|---|---|---|
| 1 | `docs/art/shots/pnl1a/pnl1a_01_party_1600.jpg` | 1：隊伍分頁、回到地點圖、「3／3」細框、影子琥珀三角 | 實機 1600×900（阿岳為注入資料） |
| 2 | `docs/art/shots/pnl1a/pnl1a_02_shadow_1600.jpg` | 1：我的影子分頁 | 實機 1600×900 |
| 3 | `docs/art/shots/pnl1a/pnl1a_03_tabbar_widths.png` | 3：分頁列四級＋每級記號 | 開發頁（實機未看） |
| 4 | `docs/art/shots/pnl1a/pnl1a_04_tab_switch.png` | 4：切分頁前後（486 第①級、320 第②級），最大差 0.0 px | 開發頁（實機未看） |
| 5 | `docs/art/shots/pnl1a/pnl1a_05_kit_1600.jpg` | 5：提示三級、籌碼、標籤、摺疊（打開第二個、第一個收起） | 開發頁（實機未看） |
| 6 | `docs/art/shots/pnl1a/pnl1a_06_party_800.jpg` | 1、2：800×600 隊伍（2＋1） | 實機 800×600 |
| 7 | `docs/art/shots/pnl1a/pnl1a_07_shadow_800.jpg` | 1：800×600 我的影子 | 實機 800×600 |
| 8 | `docs/art/shots/pnl1a/pnl1a_08_party_514_closeup.png` | 2：隊友卡 2＋1、「打法 預設（守衛）」不斷行（最近鄰 2 倍） | 實機 800×600（面板 493） |
| 9 | `docs/art/shots/pnl1a/pnl1a_09_limitnote_growth_1600.jpg` | `LimitNote` → 鎖住級提示（成長面板現行版面，只換了這三行） | 實機 1600×900（limits 為注入資料） |
| 10 | `docs/art/shots/pnl1a/pnl1a_10_tab_hint_800.jpg` | 記號滑過說明（浮動卡） | 實機 800×600 |

**實機未看**：分頁列第 1～3 級（隊伍與影子只有兩頁，任何寬度都是全名）、切分頁前後量測、摺疊（本段面板沒有摺疊）——都用開發頁畫。

## 5. 和樣張不同的地方

1. 固定區放在捲動區頂端 `position: sticky`，不是 `PopupFrame` 的 head（見待決 1）；「×」用 CSS `:has(.pnl-fixed)` 擺到外框右上，和「回到地點圖」同一列。
2. 捲下去後原本的上緣漸隱被固定區蓋住，所以固定區下緣補一條 10px 漸隱（只在 `data-scrolled="1"`）。
3. 分頁、記號的滑過說明用共用 `<Hint>`，一個分頁一張卡：只剩圖示時寫「名字　記號說明」，全名時只寫記號說明（樣張是原生 title 分兩個）。
4. 影子已存的狀態樣張沒畫：第一行寫伺服器的 `saved_zh`（例「霧渡鎮・Lv 3」），分頁不掛記號（純資訊）。
5. 劇情夥伴的頭像：成員資料沒有頭像，照 HUD 隊友小卡（`mateCards`）的做法用通用剪影＋傭兵金框；賽倫用傭兵名單的頭像與出身區。主角＝`HeroFace`（HUD 主角卡同一張）。
6. 劇情夥伴卡上不再寫 `note_zh`（「劇情夥伴：任務結束後離隊」），由綠底標籤＋下方 `companion_zh` 帶到（#31）；其他成員有 `note_zh` 照舊寫 L3。

## 6. 待 PM 決定

1. **固定區用 sticky 而不是 `PopupFrame` 的 head**：面板內容拿不到 `WorldHud` 的 head，用 portal 會被 `floatCardRule` 的「沒有自製 portal」擋（要進白名單）。sticky 的行為相同（不捲、切分頁不動），差別只在瀏覽器捲軸從固定區旁邊就開始。若要改成 head，需要在 `WorldHud` 加一個面板標頭插槽並放寬 `floatCardRule`。
2. **2.2 的 `SeasonTimeline`、`StepTimeline`、`SolutionTile` 本段沒做**：它們只用在公告板、任務、事件卡，資料（後端新欄位）也在 PNL-1b／3／4，先做會變成沒人用的元件。表 6 的 PNL-1b 列本來就寫了 `SeasonTimeline`；建議 `StepTimeline` 併 PNL-3、`SolutionTile`＋`wordBreaks` 併 PNL-4。
3. **800×600 實機面板是 493×382**（開發入口的 60px 標題列），隊伍頁在三人＋賽倫來歷三行＋兩條提示時要捲 48px。需求表的 514×477 是整個視窗當舞台；要不要讓隊伍頁在 800 也一屏放下（例：來歷行改兩行截斷）交美術 PM 看圖決定。
4. **`LimitNote` 改成鎖住級提示後也影響鐵匠面板**（「入門期的打造、強化、重骰、指定詞條只限防具」），本段只拍了成長面板。
5. **分頁內容在量高度時會多掛載一次**：本段的隊伍、影子沒有副作用；之後放進分頁的元件若在掛載時打 API（例如公告板的 `api.worldBoard`），要把讀資料放在 `PanelTabs` 外面（上手筆記第 82 點）。
6. **`bareGlyph` 只做了畫布快取、沒做圖片網址**：面板用 `<canvas>`（同 HUD 圖示的 `IconCanvas`），用不到網址。
7. **舊 `PartyPanel`、`MyShadowPanel` 還在**：雇用面板（`HudHirePanel`）與 `WorldPanel` 舊側欄還用前者的精簡清單，後者只剩 `WorldPanel` 用；要不要統一成新卡片另排。

## 開發 PM 裁定（2026-11-12，第八任開發 PM）

已驗收並以 --no-ff 合入 main（上手筆記 §4 編號改為 83～88）。合併後前端 typecheck 0、vitest 320 檔 4149 passed、build 0。

1. 固定區用捲動區頂端 sticky：接受，行為相同；交美術 PM 驗收時一併看。
2. SeasonTimeline、StepTimeline、SolutionTile 分別併進 PNL-1b、PNL-3、PNL-4。
3. 800×600 實量 493×382、三人隊伍要捲 48px：交美術 PM 判斷。
4. LimitNote 改鎖住級後鐵匠面板也變：交美術 PM 驗收時看。
5. PanelTabs 會多掛載一次：PNL-1b（公告板）派工時寫明注意。
6. bareGlyph 只做畫布快取：接受。
7. 舊 PartyPanel／MyShadowPanel 統一：記入待排，PNL 系列做完後再看。
