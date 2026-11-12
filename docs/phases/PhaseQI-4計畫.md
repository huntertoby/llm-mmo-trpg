# Phase QI-4 計畫：Q 版小圖示移植第 4 段（⑤b 裝備關鍵字小圓章、`statusTile` 其餘 86 種、頭頂狀態列擁擠時留第一個圖示、QI-2c 補拍）

> 草稿（開發 PM 的規格助手依據本機 main `f7104d51` 起草，2026-11-12；含美術分支 `f2ebee5d`）。待開發 PM 定稿。
> 美術依據：`docs/art/Q版小圖示-關鍵字移植需求.md`（以下簡稱「需求」，引用寫「需求 x.y」）；樣張以 `07d85471` 之後的 `docs/art/sample/qIconsKeywords.js`、`q-icons-keywords.html` 為準（畫法 `965ca2e8`、點版預設 `07d85471`）；紀錄 `docs/art/Q版小圖示-第5b批關鍵字.md` 第 9 節、13.9、13.12（**有出入時以需求第 3 節為準**）；審查 `docs/art/Q版小圖示-第5b批關鍵字-審查.md`「第 3 版：通過」「C 版複審」「C 版點版對照」。
> 另兩件的依據：美術驗收 `docs/art/QI-2c-2d-3a-3b驗收.md`（以下簡稱「驗收」）4.2、4.3、4.4、第 6 節第 1、4、5 點；`docs/phases/PhaseQI-3b報告.md` 待決第 2、5 點；上手筆記 `docs/dev/上手-前端戰鬥畫面與動畫.md` 第四節第 40、45～47 點。
> 前幾段照樣適用：`PhaseQI-1計畫.md` 0.0（畫布＝顯示尺寸 × 固定 `ICON_RES` 2、圖樣貼整數裝置像素、材質色用 `material.ts`、截圖規則）；`PhaseQI-3計畫.md` 0.0（`qIcon/` 已搬的部件不重搬、`core.ts`／`weapons.ts` 不改畫法、快照不整批重產）。
> **建議切三段**：QI-4a 搬關鍵字畫法＋開發頁＋`statusTile` 換 Q 版 → QI-4b 裝備圖示接線＋說明框列關鍵字＋實機與 QI-2c 補拍 → QI-4c 頭頂狀態列擁擠時留第一個圖示（**等第 0 節第 7、8 列確認後才派**）。理由見第 4 節。

## 0.0 已定（使用者與派工）

- **⑤b 只畫一個圓章，旁邊加記號表示「還有一個」**（使用者 2026-11-12 選 C，原話「C」）。
- **記號用 B 點版**（使用者 2026-11-12，原話「B」，專案 PM 轉達）：牌裡是第二個關鍵字顏色的點。**只做點版**，不搬「＋」那一支、不留樣式切換常數（需求 3.4 第 6 點）；樣張裡試做的 `dot`／`plus`／`stack`／`pill` 與第 3 版「>36px 斜放單把畫兩個圓章」（`opt.v3`、`TWO_DIAG`、`areas` 的多圓章分支）都不搬。
- **撞擊的簡化形先放關鍵字檔、不動 `parts.ts`**（需求第 4 節第 2 點，美術建議；派工照收）：技能組裝列 18px 的撞擊部件圓片與 QI-2d 基準都不變。
- **說明框要列出全部關鍵字**（需求 1.3 第 3 點）；現況查證見第 0 節第 1 列與附錄第 1 點。
- **`statusTile` 其餘 86 種換 Q 版**（驗收 4.3、4.4、第 6 節第 1 點；美術 PM 第八任）：`skillParts.ts` 掛的 `QP.hooks.status` 改指向 `qIcon/status.ts` 的狀態卡形圖樣；圓片只放圖樣、不放狀態框；圖樣＝直徑 78%（`QP.chip` 現行的 `r × 1.56`）；不用 `HEAD_TINT` 的頭頂簡化形；不需要 `fitK`。
- **頭頂狀態列擁擠時至少留排序第一的圖示**（驗收 4.2、第 6 節第 4 點，開發 PM 定優先度）：本段寫改法；和既有美術決定的衝突見第 0 節第 7、8 列。
- **QI-2c 補拍併進本段截圖配額**（驗收第 6 節第 5 點）：工坊 56 卡片預覽（1600、800）、800 工坊 96／40／28、背包身上裝備格左上角對齊（1600@1 真 1 倍 ×6）。
- **舊存檔不必相容**（使用者原話：「存檔都可以刪除」）。本段不動存檔格式。
- **快照與呼叫紀錄基準不得整批重產**：每項變動要證明來自本段（拿掉本段改動回到舊值）。
- **截圖**：每段 ≤ 10 張；jpg 品質 80；真 1 倍／最近鄰放大特寫可用 PNG，單張 ≤ 300 KB；存 `docs/art/shots/qi4/`，檔名前綴 `4a-`、`4b-`、`4c-`。
- **開發 PM 第七任定稿（2026-11-12）**：第 0 節第 1～6、10～12 點**照建議**。第 9 點（色環）與第 7、8 點（擁擠規則與既有美術決定 6F-13／6F-19／6F-20 衝突）已問美術 PM，答覆前：4a 的色環照現行 `FAINT_RING` 不動、只換圖樣（美術若要 `statusColor` 再追加）；**4c 不派**。派工順序 4a → 4b；4c 等美術書面改寫（若牽涉使用者看過的 6F-20 (a)，回使用者）。
- **美術 PM（第八任）書面答覆（2026-11-12）**：(1) `statusTile` 圓片維持現行 `FAINT_RING`（白 30%），只換圖樣；驗收檔「照 `statusColor`」是筆誤、作廢。(2)(3) 撤回「頭頂擁擠至少留第一個圖示」：6F-13、6F-19、6F-20 舊決定全部維持（800／1040 照舊只留「+N」，有灌注徽章也只留「+N」），不用回使用者。**4c 從本段拿掉，QI-4 只做 4a、4b。** 說明框從後端匯出關鍵字名稱、中文名以內容為準（高處、召喚物）同意。

## 0. 待開發 PM 確認

「建議」是規格目前寫進去的做法（最保守）；確認後改掉對應列或移進 0.0。

| # | 問題 | 出處 | 建議（暫採） |
|---|---|---|---|
| 1 | **說明框的關鍵字名稱從哪裡來**：現行說明框**沒有任何地方列關鍵字**（附錄第 1 點）；前端也**沒有關鍵字中文名的資料**——名詞表 `/api/glossary` 不含關鍵字，`gearAppearance.json` 只有 id，技能那邊的 `KeywordRef.name_zh` 只跟著技能卡來。守則 4、上手筆記第三節第 9 點不准在元件寫死名稱 | 需求 1.3 第 3 點、第 4 節末（「後端不用動」）；`content/skill_keywords.yaml`（`ignite: 點燃`…`form: 形態`）；`scripts/export_appearance.py`、`trpg.content.appearance.appearance_export` | **擴充前端內容快照，不動 API**：`appearance_export` 多一個鍵 `keywordNames`（id → `skill_keywords.yaml` 的 `name_zh`，照 `keywords` 的順序），`export_appearance.py` 重產 `client/src/render/gearAppearance.json`；`tests/content/test_appearance.py` 的「JSON 沒有過期」照舊擋。這會動到一支 Python 匯出函式（和需求「後端不用動」字面不同，但不碰引擎、API、存檔）。另案：`AppearanceView` 加 `keywords_zh`（要重產 OpenAPI 與型別，較重）；前端寫死 12 個名稱（違反守則，不採） |
| 2 | **說明框列「全部」是哪些** | 需求 1.3 第 3 點；`derive_keywords(…, limit=2)`（`content/appearance.py` 138 行）；前端 `resolveGear` 另把武器表 `element` 換成的元素關鍵字排第一再截 2 個 | **列圖示代表的那幾個**：`resolveGear(look, slot).keywords`（認得的、最多 2 個、元素關鍵字在前），和圓章、點用的是同一份。寫成一行「關鍵字：點燃、潮濕」（`、` 連接，名稱用第 1 列的 `keywordNames`，沒有名稱時寫 id）；沒有關鍵字時不加這一行。物品若有第 3 個會產生關鍵字的詞條，後端已截掉、前端看不到（詞條行本身仍列出）——寫進報告，不在本段改後端 |
| 3 | **哪些說明框要加** | 附錄第 1 點的清單 | **所有「滑過裝備圖示會開的說明卡」與裝備卡本體**：`run/gearOffer.ts` 的 `itemTipLines`（背包身上裝備格、跑團主角面板、裝備卡「目前的」比較）、`gear/affixStatus.ts` 的 `tipLines` 呼叫處（`HeroGearPanel`、`UnitInfo`：改呼叫端多傳 `appearance`，不改 `tipLines` 簽名）、`GearCardView` 本體的詞條清單（放在詞條行之後、`gear-card-lines` 裡多一個 `li`）。**不加**：背包格 42 的 `<Hint>`（`bagGrid.cellHint`＝「名稱・種類」一行，點下去就開 `GearCardView`，那裡有）、郵件與獲得動畫的 32（沒有說明框）、靶場選大類的起始武器 40（不是物品，元素關鍵字來自武器表） |
| 4 | **畫圓章的尺寸門檻與 `small` 參數** | 需求 1.3 第 1 點、3.1 第 1 點；`gearIcon.ts` 的 `SMALL_ICON_MAX_PX = 36`、`drawGear(ctx, look, small, …)`、`gearIconKey` 倒數第 3 欄 `s`／`l` | **門檻改 `px >= 32`**：新常數 `KEYWORD_CHIP_MIN_PX = 32`（`gearIcon.ts`），刪 `SMALL_ICON_MAX_PX`；`drawGear` 第 3 參數改名 `chips`（畫不畫關鍵字層，預設 `true`），`gearIconCanvas` 傳 `px >= KEYWORD_CHIP_MIN_PX`；快取鍵**拿掉 `s`／`l` 那一欄**（鍵裡已有 `px`，需求第 4 節第 4 點）。現行呼叫的尺寸是 32、40、42、48、64 與 `fit`（1600 寬 48、800 寬 39；更窄時可能 < 32 → 不畫，照美術建議） |
| 5 | **檔放哪、怎麼切** | 需求第 4 節第 1 點 | **新檔 `client/src/render/qIcon/keywords.ts`**：`LIST`、`KEY_CORNER`、`MORE_DIR`、`MORE_DIR_KIND`、`isDiag`、`cornersOf`、`sizeOf`、`glyph`、`chip`、`moreSize`、`moreBox`、`more`（只有 `kwdot` 一種）、`paint(ctx, keywords, px, res, { def, kind, form })`、`chipCanvas`、撞擊簡化形 `collision`；`gearIcon.ts` 只呼叫 `paint`。關鍵字色一律 import `palette.ts` 的 `KEYWORD_COLOR`，不搬樣張的 `KC`（測試斷言兩表逐筆相同） |
| 6 | **舊 `motif()`／`motifs()` 的去留** | 需求第 4 節第 3 點；`grep` 結果：`motif()` 只在 `gearIcon.ts` 內部被 `motifs()` 呼叫，別處沒有 import（`skillIcon.ts` 的 `motif` 是技能拆解的欄位名，不相干） | **刪**（4b，接線後沒有呼叫處）；`qIcon/weapons.ts`、`armor.ts` 定義裡的 `meta.spots` 不動（`weapons.ts` 不改，檔頭註解提到 `motif()` 的那句也不改，報告列出）；開發頁需要「現行」對照時用樣張的 `legacy()` 原樣抄進開發頁（同 QI-3b 的 `legacyPaint` 做法） |
| 7 | **頭頂狀態列擁擠時留第一個圖示，和既有美術決定衝突** | 美術 `6F-19檢查.md`（`docs/archive/art/`）第 2 節決定 X：「1 個圖示＋『+1』」**只限 2 個狀態**、有徽章又放不下兩個圖示；`docs/art/6F-20檢查.md` 第 2 節第 1 題選 **(a) 維持現狀**：「1040、800 寬照舊只留『+2』」「不放寬『超出格子 ≤ 6』和『隔 3px』」；`6F-17檢查.md` 第 5 項（1600 寬 3 個狀態＋蓄力只留「+N」照收）；6F-13 精簡列有灌注徽章一律只留「+N」（`badgeLayout.chooseRowLayout` 的 `infused`）。都是美術 PM 的決定，**沒有寫進 `docs/design/`**，也沒找到使用者原話 | **QI-4c 照第八任美術的新建議改，但底線不放寬**：「1 個圖示＋『+(N−1)』」擴到 3 個狀態以上、排在「只留 +N」之前（改法見第 6 節 C1）；「超出格子 ≤ 6」「數字隔 3px」照舊，放不下仍只留「+N」。請美術 PM 在 `docs/art/6F-20檢查.md` 或新檢查檔寫明「決定 X 擴到 3 個以上、取代 6F-17 第 5 項與 6F-20 (a) 的範圍」再派 4c。**可能要回使用者**：若開發 PM 或美術 PM 認為 6F-20 (a) 是給使用者看過的定案，照 CLAUDE.md 角色分工回使用者 |
| 8 | **擁擠時幾何上可能仍放不下** | `Phase6F-20報告.md`「X 的結果」：「1 個圖示＋膠囊」寬約 26.4（本地座標），比 2 個圖示相貼的 22 還寬，6F-20 的 9 種裡只有 1600 朝北放得下；精簡列（縮放 ≤ 85%，800 寬）原本的排法就已經是 1 個圖示＋膠囊 | **4c 先量、不保證做到**：精簡列的新排法只是把「1 個圖示＋膠囊」移到中間／靠右／靠左並避開朝向三角形，800 寬的 3b-04 那一格不一定放得下。4c 要交「改前／改後顯示方式」表（第 7.3 節 T-C3）；若 3b-04 那一格改後仍只留「+N」，**不放寬底線**，停在報告的待決，交美術 PM 決定（例：精簡列「+N」膠囊再縮、允許超出更多、把徽章往外推） |
| 9 | **色環「照 `statusColor`」和現況不同** | 驗收 4.3「外框（色環）：照現行 `statusColor` 的淡色環，和第④批 32 種一致」；實際：`skillIcon.ts` 的 `statusTile` 與工坊狀態選項都是 `qChip("status", id, r, FAINT_RING)`（白 30%），第④批 32 種也是這個環；組裝列效果圓片的環由呼叫端給 | **環一律不動，只換圓片裡的圖樣**：「和 32 種一致」本來就成立；改成 `statusColor` 色環會連 32 種一起變、超出「換 86 種圖樣」。報告附一張並排請美術看；美術若要改環另排 |
| 10 | **`hooks.status` 換掉後，32 種以外「不認得」的狀態畫什麼** | `qIcon/status.ts` 的 `entry(id)` 對不認得的回 `null`；`skillParts.ts` 現行 hook 畫 `statusGlyph`（`GLYPH` 或名稱第一個字，色 `statusColor`） | **認得的（名詞表 118 個全部）畫 `status.ts` 的 `entry(id).d`；不認得的照現行 hook 畫**（`statusGlyph`＋`statusColor`，原樣保留成退回分支）。不另畫 |
| 11 | **開發頁**：擴充 `gear-gallery.html`，還是另開一頁 | 需求第 5 節前言（「照 QI-1 的裝備開發頁加 `?px=`、`&res=`、`&zoom=`、`&set=`」）；`gear-gallery.html` 只有防具＋飾品 44 款，武器 61 款在 `weaponicon-gallery.html` | **另開 `client/dev/keyword-gallery.html`＋`src/dev/keywordGallery.ts`**，參數名照 QI-1 兩頁（`?px=`、`&res=1\|2`、`&zoom=`、`&set=`、`&from=&n=`、`&label=0`、`&rarity=`），款式清單從兩頁共用的來源 import（不複製清單）；4b 加 `&live=1`（走遊戲端 `gearIconCanvas`）。理由：105 款跨兩頁，塞進任一頁都要改另一頁的清單 |
| 12 | **`statusTile` 換圖的呼叫紀錄基準** | 上手筆記第四節第 40、48 點；`render/fixtures/qi3bStatusBaseline.json`（`head|<id>`＝`statusTile` 24）、`qi2dBaseline.json`（全部部件 18／30 × res 1、2，含效果 `status:*`、條件 `target_has_status`、`card:status`） | **重錄兩份基準，逐筆證明**：`qi3bStatusBaseline.json` 只有 86 個 `head|<id>` 變（32 個 `head|` 與 118 個 `card|` 不變）；`qi2dBaseline.json` 只有「圖樣經 `hooks.status` 的那幾筆」變（實作者先列出名單再重錄）；其他一筆都不准變。`qi2cStatusBaseline.json` 不動，「236 組都和舊基準不同」照舊 |

## 1. PM 決定

| # | 決定 | 出處 |
|---|---|---|
| D1 | ⑤b 只畫一個圓章（`keywords[0]`），第二個以上只用點版記號提示；第 3 版「斜放單把兩個圓章」拿掉 | 使用者「C」「B」；需求 1.3 第 2 點、3.4 |
| D2 | 撞擊簡化形放關鍵字檔，`parts.ts` 不動 | 需求第 4 節第 2 點 |
| D3 | `statusTile` 86 種換 Q 版狀態卡形圖樣；圓片只放圖樣、不放框；78%；不用頭頂簡化形 | 驗收 4.3、4.4 |
| D4 | 頭頂擁擠時「1 個圖示＋『+N』」先於「只留 +N」；底線（超出 ≤ 6、隔 3px）不放寬 | 驗收 4.2；第 0 節第 7、8 列（待確認） |
| D5 | 截圖：每段 ≤ 10 張；真 1 倍／最近鄰特寫可 PNG ≤ 300 KB，其他 jpg 80 | `docs/開發PM交接.md` 6.5.2；QI-2 D7 |

## 2. 目標與範圍外

**目標**：
1. 裝備圖示（`gearIcon.ts`）的關鍵字層從「器物上兩處細線小圖樣（> 36px 才畫）」換成「**角落一個 Q 版關鍵字小圓章（≥ 32px 就畫）＋第二個關鍵字的點版記號**」；12 個圖樣全部呼叫已移植的 `qIcon/skills.ts`、`parts.ts`，只有撞擊 ≤ 14px 的簡化形在新檔裡（需求第 1～3 節）。
2. 說明框列出關鍵字（第 0 節第 1～3 列）。
3. 部件圓片 `statusTile`（戰場定時炸彈／蓄力徽章 24、組裝列效果與條件圓片 18／30、工坊狀態選項 26）裡 32 種以外的 86 種狀態改畫 Q 版圖樣。
4. 頭頂狀態列擁擠時至少留排序第一的圖示（4c，待確認）。
5. QI-2c 缺的三張實機截圖。

**範圍外**：框（`frame()`）、稀有度色塊、Q 版主圖、寶石色、元素混色、`KEYWORD_COLOR` 的值、`resolveGear` 的關鍵字規則（需求 1.2）；`qSummon.ts` 召喚物頭上的元素小圖（需求 1.2 末點）；撞擊簡化形共用到 `parts.ts`（D2）；`statusTile` 的色環（第 0 節第 9 列）；`statusIconTile`／`statusIconCanvas`（狀態框，QI-3b 已換）；頭頂 11px 照螢幕實際尺寸出圖（驗收 4.4：維持現狀）；後端 API、存檔、引擎；需求第 6 節的已知事項（42 點偏弱、點色只分大類、橘綠色盲、關鍵字色與圖樣不一致、同題材不同形）；`qIcon/core.ts`、`weapons.ts`、`armor.ts` 的畫法。

## 3. 工作環境

- Windows、Git Bash。前端 `corepack pnpm -C client …`；Python 一律 `uv run python`（`UV_NO_SYNC=1`）。
- 新 worktree 第一次：`uv sync --frozen`、`corepack pnpm -C client install --frozen-lockfile --offline`。
- 預覽埠（不用 8000、8001）：vite **5305～5309**（4a 5305～5306、4b 5307～5308、4c 5309）；`trpg serve`／靜態伺服器（載樣張比對）**8151～8153**（4a 8151、4b 8152、4c 8153）。vite 的 `/api` 寫死轉 8000，要接自己的 `trpg serve` 另寫暫存設定檔、用完刪掉，不改 `vite.config.ts`（上手筆記第四節第 13 點）。
- 瀏覽器網址一律加 `?mute=1`；無頭 Chrome 加 `--mute-audio`，截圖 `--force-device-scale-factor=1`；和樣張逐像素比用 `--disable-gpu`、剛載入的頁面、兩邊交錯畫（上手筆記第四節第 23、37 點）。腳本、`--user-data-dir`、存檔目錄放暫存區自己的子資料夾（第 26 點）。
- 結束前用自己記下的 PID 關掉 vite、`trpg serve`、靜態伺服器與無頭 Chrome，確認沒有殘留；不用 `taskkill /IM`、`pkill`。
- 等背景程序用完成通知，不寫 `until`／`while` 輪詢迴圈。
- agent 與子 agent 一律 Opus 5.5（Agent 工具 `model: "opus"`），prompt 寫明往下也一樣。
- 只跑相關測試（第 9 節）；不跑 `scripts/check.py`、不跑模擬。不要 push。每完成一個交付項目就 commit（第一行英文，例 `feat(qi4a): port Q keyword chips to TS`），結尾帶 Co-Authored-By。
- 要讀的：`CLAUDE.md`；需求全文；`docs/dev/上手-前端戰鬥畫面與動畫.md`（第一、二節全文、第三節、第四節第 19～21、23、33～50 點）；`docs/art/上手-畫法.md` 2.1、2.5、2.8、2.9；紀錄第 9 節、13.9、13.12；4a 另讀驗收 4.3 與 `PhaseQI-3b報告.md` 待決第 2 點；4c 另讀 `Phase6F-20報告.md`「X 的結果」、`docs/art/6F-20檢查.md`。

## 4. 切段

| 段 | 內容 | 改的檔（主要） | 前置 |
|---|---|---|---|
| **QI-4a** 關鍵字畫法＋開發頁＋`statusTile` | 新 `qIcon/keywords.ts`（樣張逐行搬，只有點版）；開發頁 `keyword-gallery.html`；和樣張逐像素比對；`hooks.status` 改指向 `status.ts`；重錄兩份基準；需求第 5 節第 1～6 項截圖、`statusTile` 截圖 | 新 `client/src/render/qIcon/keywords.ts`、新 `client/dev/keyword-gallery.html`、新 `src/dev/keywordGallery.ts`、`render/skillParts.ts`（只改 `QP.hooks.status` 那一段）、`dev/statusGallery.ts`（`set=tile` 收 `px` 清單）、`render/fixtures/qi3bStatusBaseline.json`、`qi2dBaseline.json`、相關測試 | 無（`gearIcon.ts` 不動，**遊戲裡的裝備圖示不變**；`statusTile` 會變） |
| **QI-4b** 裝備圖示接線＋說明框＋補拍 | `gearIcon.ts` 換關鍵字層、門檻與快取鍵、刪 `motif()`；`keywordNames` 匯出；說明框加一行；開發頁 `&live=1`；實機截圖（需求第 5 節第 7 項）；QI-2c 補拍 3 張；`__layoutSmoke` | `render/gearIcon.ts`、`trpg/content/appearance.py`（`appearance_export`）、`scripts/export_appearance.py`（若簽名要改）、`client/src/render/gearAppearance.json`（重產）、`run/gearOffer.ts`、`gear/affixStatus.ts` 的呼叫端（`ui/gear/HeroGearPanel.tsx`、`ui/UnitInfo.tsx`）、`ui/gear/GearCardView.tsx`、`dev/keywordGallery.ts`、既有測試改寫 | **QI-4a 合併後**（要 import `keywords.ts`） |
| **QI-4c** 頭頂擁擠留第一個圖示 | `chooseRowLayout` 的順序與 `oneAllowed` 放寬到 3 個以上；改前／改後表；實機截圖 | `render/badgeLayout.ts`、`render/unitSprite.ts`（`statusRow` 的 `oneAllowed`、`oneVariants`、`rowControls`）、`ui/badgeCapsule.test.ts`、`ui/statusBadges.test.ts` 等 | **第 0 節第 7、8 列確認後才派**；檔案和 4a、4b 不重疊，可和 4b 平行 |

理由：① 樣張 `qIconsKeywords.js` 30 KB（含 4 種試做樣式與第 3 版分支），只搬點版仍要逐行搬、做 105 款 × 4 尺寸 × 2 種 `res` 的逐像素比對與開發頁 7 種 `set`，接近一段上限；`statusTile` 只改一個 hook，但要重錄兩份基準並逐筆證明，放在 4a 是因為它和關鍵字檔不重疊、截圖也走開發頁，合計 4a 約 9 張。② 4b 動到 Python 匯出與 React 說明框，還要實機（背包、裝備格、裝備卡）與 QI-2c 補拍，和搬畫法放一起會超過 25 萬 token。③ 4c 改的是 6F 系列反覆調過的排版規則（`chooseRowLayout` 有 6F-13～6F-20 七層退路），測試多、要量多種寬度與方向，又卡在美術決定，獨立一段才不擋 4a、4b。若 4a 超量，`statusTile` 可移到 4b 開頭。

## 5. 受影響的既有功能

| 區塊 | 受影響的 | 改／不改 | 理由 |
|---|---|---|---|
| 裝備圖示（全部 `GearIcon`、`gearIconCanvas`） | 關鍵字層換掉；32～36px 從不畫改成畫一個圓章（需求 1.3 第 1 點）；快取鍵少 `s`／`l` 一欄 | 改（4b） | 需求 1.1、1.3 |
| 框、稀有度、主圖、寶石色、元素混色 | 無 | 不改 | 需求 1.2 |
| `resolveGear`、`KEYWORD_COLOR`、`gearAppearance.json` 的既有鍵 | `gearAppearance.json` 只多 `keywordNames` | 加鍵（4b） | 第 0 節第 1 列 |
| 說明框 | `itemTipLines`、`tipLines` 呼叫端、`GearCardView` 多一行「關鍵字：…」 | 改（4b） | 第 0 節第 2、3 列 |
| 背包格 42 的 `<Hint>`、郵件、獲得動畫、靶場起始武器 | 圖示會多圓章；說明不加 | 只換圖 | 第 0 節第 3 列 |
| 人物身上的裝備（`dollGear.ts`） | 只 import `resolveGear`／`gearKinds` | 不改 | — |
| `statusTile`（定時炸彈／蓄力徽章 24、組裝列效果／條件圓片 18／30、工坊狀態選項 26） | 86 種的圖樣換 Q 版；環、底、半徑不動 | 改（4a） | D3；第 0 節第 9、10 列 |
| `statusIconTile`／`statusIconCanvas`、`statusColor`、`glyphColor`、`GLYPH`、`drawGlyph` | 無（`statusGlyph` 留給不認得的退回與 `conditionPart` 的舊畫法） | 不改 | QI-3 第 0 節第 6 列 |
| 頭頂狀態列 | 擁擠時的顯示方式順序；圖示本身、排序、`ROW_MAX_ICONS`（2）、膠囊大小、`minMark` 不動 | 改（4c） | D4 |
| 呼叫紀錄基準 | `qi3bStatusBaseline.json`、`qi2dBaseline.json` 重錄（4a） | 逐筆證明 | 第 0 節第 12 列 |
| 快照 `render/__snapshots__/`（`creaturePose`、`inkDollSnapshot`） | 與本段無關，預期不變 | 不改 | 有變就停下回報 |
| 排版煙霧檢查 | `icons()` 照舊量裝備圖示畫布；4c 的三尺寸 `runCase` | 照跑 | 6.2 第 5 點 |

## 6. 交付項目

### QI-4a 關鍵字畫法＋開發頁＋`statusTile`

- **A1 `qIcon/keywords.ts`**：由 `qIconsKeywords.js`（`07d85471` 之後）逐行搬，只做型別調整，檔頭寫「和樣張不同」：
  - 依賴：元素道具 `ELEMENT`、記號 `ACT` 從 `qIcon/skills.ts`；`entry`（`trigger.on_collision`、`condition.height_advantage`、`status.concealed`、`status.poison`、`effect.enter_form`）、`BOX` 從 `qIcon/parts.ts`；`render`、`blit`、`outlinePx`、`blank`、`H`（`rr`、`f`、`poly`、`starPts`）從 `qIcon/core.ts`；顏色 `KEYWORD_COLOR` 從 `palette.ts`、`mix` 從 `color.ts`。`parts.ts`／`skills.ts` 缺 `export` 時只加 `export`（列進報告），不改畫法。
  - 圓章（需求 3.1）：`D = round(px × 0.42 × res) / res`；`m = px × 3.6 / 64`；`far`／`near` 對齊裝置像素；外圓 `#16121a`、內圓（半徑 D/2 − 1 裝置像素）`mix(KEYWORD_COLOR[kw], "#191b22", 0.72)`；沒有環。
  - 圖樣（需求 3.1 第 5 點、3.3）：`cpx = (D − 2/res) × k`、圖樣格 `cpx × 4/3`、中心對準圓心、`blit` 貼整數裝置像素；`cpx ≤ 14` 不包外框。元素 4 個照 `from48`（縮 0.47、平移 −24、`small: true`）；其他 ±10 單位 × 1.8 移到 (24, 24)；`o.tiny`／`o.small` 照圖樣大小（≤14、≤24）。撞擊 `cpx ≤ 14` 畫簡化形（需求 3.3 第 5 點，D2），其他呼叫 `parts.ts` 的 `on_collision`。
  - 角（需求 3.2）：`KEY_CORNER` 照樣張原表搬（查 `kind/form` → `kind` → 預設右下；右上永遠不放）。
  - 記號（需求 3.4，只有 `kwdot`）：條件 `keywords.length > 1`；`s`、`w`、方向（`MORE_DIR_KIND` → 右下且 `isDiag` → 照角）、位置（`r = D/2 + w/2 − 2/res`、`snap`、夾在 `[snap(m), snap(px − m) − w]`）、畫法（外框 `#16121a` 圓 → 內縮 1 裝置像素 `#191b22` → 點用 `KEYWORD_COLOR[keywords[1]]` 原色；不認得用 `#f2e6c8`；`G ≤ 4` 畫方點、否則圓）。畫在圓章之後。
  - 出口：`paint(ctx, keywords, px, res, { kind, form, diag })`（ctx 是 CSS px 座標、每單位 `res` 個裝置像素；`keywords` 由呼叫端先過 `resolveGear`）；`chipCanvas(kw, px, res)`（開發頁用）；`LIST`、`KEYS`、`KEY_CORNER`、`cornersOf`、`isDiag`、`moreSize`（測試用）。不認得的關鍵字不畫、不丟例外。
  - **不搬**：`KC`、`legacy`／`paintLegacy`（開發頁另抄，第 0 節第 6 列）、`areas`、`coverOf`、`ONE_MAX_PX`、`TWO_DIAG`、`MORE_STYLES`／`MARK`／`setMark` 與非 `kwdot` 的分支、`geom` 的 `ring`。
- **A2 開發頁** `client/dev/keyword-gallery.html`＋`src/dev/keywordGallery.ts`（第 0 節第 11 列）：`?px=`（可逗號多個）、`&res=1|2`、`&zoom=`（最近鄰）、`&rarity=`、`&set=bag|all|chips|dots|corner|count|legacy`（逗號接多段）、`&from=&n=`、`&label=0`。`bag`＝背包模擬 16 件（每件兩個關鍵字、五種稀有度輪流，照樣張 `?part=bag` 的清單）；`all`＝105 款總表每款兩個關鍵字（`?part=c`）；`chips`＝12 個圓章 13／18／20／27（`?part=true1x`）；`dots`＝點色 12 × 五稀有度（`?part=dots`）；`corner`＝需求第 5 節第 5 項的例外表各款（32、48）；`count`＝一個關鍵字與三個關鍵字（第 6 項）；`legacy`＝現行 `motif()` 對照（頁內抄樣張 `legacy()`）。4a 的圖示＝`gearIconCanvas` 的框與主圖＋`keywords.paint`（遊戲端還沒接，頁內組合）。掛 `window.__qiKwDev`（`paint`、`chip`、`list`），畫好後 `body.dataset.ready="1"`；檔頭寫參數說明。
- **A3 `statusTile` 86 種**：`render/skillParts.ts` 的 `QP.hooks.status` 改成：`const e = QStatus.entry(id); if (e) e.d(c, o); else { 現行 statusGlyph＋statusColor 那一段 }`（第 0 節第 10 列；`QStatus` ＝ `qIcon/status.ts`）。檔頭第 7 行與 `statusTile` 的註解跟著改。確認不產生循環匯入（`status.ts` 不 import `skillParts.ts`）。`dev/statusGallery.ts` 的 `set=tile` 收 `?px=` 清單（18、24、26、30），「現行」標籤改「Q 版（hooks）」；保留 `&old=1` 對照。
- **A4 基準重錄**（第 0 節第 12 列）：先在改動前用同一套 `grab` 列出 `qi2dBaseline.json` 裡圖樣經 `hooks.status` 的鍵（實作者自己算、寫進報告），改動後重錄，斷言只有那些鍵與 `qi3bStatusBaseline.json` 的 86 個 `head|` 變。
- **A5 測試**：第 7.1 節 T-A1～T-A8。
- **A6 和樣張逐像素對照**：開發頁同一頁載入靜態伺服器上的樣張（`qIcons.js`、`qIconsWeapons.js`、`qIconsArmor.js`、`qIconsSkills.js`、`qIconsParts.js`、`qIconsStatus.js`、`qIconsKeywords.js`；樣張 `M`／`MAT` 先換成 `material.ts` 的色，上手筆記第四節第 20、35 點），105 款 × 兩個關鍵字 × 32／42／48／64 × `res` 1、2 比「只有關鍵字層」的畫布（同一個 `def`、同一組角）；另 12 圓章 × 13／18／20／27 × `res` 1、2。需求 2 末段的樣張端指紋 `uv run python docs/art/sample/tools/qicons_shots.py --hash keywords` 結果附在報告。只允許 `color.ts` 的 `mix` 四捨五入差異，其他差異先停下回報。
- **A7 截圖、報告與上手筆記**（第 8.2、10 節）。

### QI-4b 裝備圖示接線＋說明框＋補拍

- **B1 `gearIcon.ts`**：`drawQ` 最後一行 `if (!small) motifs(…)` 換成 `if (chips) keywords.paint(ctx 換成 CSS px 座標, r.keywords, px, res, { kind: r.kind, form: r.form, diag })`（座標換算同上一行 `blit` 的 `ctx.scale(64 / px, 64 / px)`）；`KEYWORD_CHIP_MIN_PX = 32`、刪 `SMALL_ICON_MAX_PX`；`drawGear` 第 3 參數改 `chips`；`gearIconKey` 拿掉 `s`／`l`；刪 `motif()`、`motifs()`（第 0 節第 4、6 列）。檔頭與 `drawGear` 的註解改寫。`isDiag` 需要的「造型的 `diag`」從 `gearQDef` 的定義讀（樣張怎麼取就怎麼取）。
- **B2 `keywordNames`**（第 0 節第 1 列）：`appearance_export` 多 `keywordNames`（照 `keywords` 順序；名稱來源 `skill_keywords.yaml`，載入方式照 `trpg.content` 既有讀法）；重產 `gearAppearance.json`；Python 測試加一條「12 個都有名稱、和 `skill_keywords.yaml` 相同」。
- **B3 說明框**（第 0 節第 2、3 列）：新純函式 `gearKeywordLine(look, slot): string | null`（放 `run/gearOffer.ts` 或 `gear/` 下，回「關鍵字：點燃、潮濕」或 `null`）；`itemTipLines(item, slot?)` 在詞條行之後加這一行（`{ text, note: null }`；沒有詞條但有關鍵字時照寫「（沒有詞條）」再接這一行）；`HeroGearPanel`、`UnitInfo` 的 `tipLines(e.affixes)` 在呼叫端接上這一行；`GearCardView` 的 `gear-card-lines` 多一個 `li`（`data-testid="gear-card-keywords"`）。「沒有詞條」那一列的判斷不受影響。
- **B4 開發頁**：`keyword-gallery.html` 加 `&live=1`：圖示改走遊戲端 `gearIconCanvas`；斷言 `live=0`／`live=1` 每款逐像素相同（寫進報告）。
- **B5 測試**：第 7.2 節 T-B1～T-B7；既有測試改寫逐條寫「舊斷言 → 新斷言」。
- **B6 實機截圖、`__layoutSmoke`、浮動卡實測、補拍、報告與上手筆記**（第 8.1、8.2、10 節）。

### QI-4c 頭頂擁擠留第一個圖示（第 0 節第 7、8 列確認後）

- **C1 規則**（`render/badgeLayout.ts` 的 `chooseRowLayout`、`render/unitSprite.ts` 的 `statusRow`）：
  1. `oneAllowed` 從 `ids.length === 2 && plusW > 0` 放寬成 `ids.length >= 2 && plusW > 0`；膠囊的數字＝`ids.length − 1`（就是現行 `plusN`／`compactPlusCount`）。
  2. 凡是會選到「只留 +N」（`plus-c|r|l`）的地方，先試同方向的「1 個圖示＋膠囊」（`one-c|r|l`）：(a) 精簡列 `order` 裡 `plusOrder` 之前插 `oneOrder`；(b) 精簡列有灌注徽章時的 `order` 也先 `oneOrder` 再 `PLUS_ONLY_MODES`（**這條改到 6F-13「灌注一律只留 +N」，列進第 0 節第 7 列一起確認**）；(c) `rescue`（非精簡列 3 個以上）先給 `oneVariants()` 再 `plusVariants()`，迴圈先試 one；(d) `lastResort`、`lastOverflow` 照 6F-20（已含 one）。
  3. 接受條件和現行一樣（strict＝每顆徽章第 0 層；退路＝`!placedPoorly`／`firm`）；`withinOverflow`（超出 ≤ `ROW_PLUS_OVERFLOW_MAX`）、數字隔 3px、不碰朝向三角形、不超出地圖邊**都不放寬**。
  4. 留下的圖示照 `sortStatuses` 排第一的（控制 > 持續傷害 > 其他減益 > 增益）；`ROW_MAX_ICONS`、膠囊大小、`minMark` 都不動。
  5. 註解寫明出處（驗收 4.2、本計畫 C1）與被取代的舊規則（6F-17 第 5 項、6F-20 (a) 的範圍）。
- **C2 量表**：第 7.3 節 T-C3 的改前／改後表。
- **C3 測試、截圖、`__layoutSmoke`、報告**。

## 7. 行為一致測試

資料用名詞表快照 `client/src/battle/fixtures/glossary.json`、`render/gearAppearance.json`、`qIcon/weapons.ts`／`armor.ts` 的款式清單，不手寫清單；數字寫在斷言旁並註明出處。vitest 假畫布 `test/fakeCanvas.ts`（`setQCanvasFactory`），結束換回 `null` 並清快取。

### 7.1 QI-4a（vitest）

| # | 測什麼 |
|---|---|
| T-A1 | **12 個都有圖樣、和 `gearAppearance.json` 的 `keywords` 同序**；`LIST` 的色＝`KEYWORD_COLOR` 逐筆（不另存一份）；元素 4 個呼叫 `skills.ts` 的 `ELEMENT`、其他 8 個呼叫需求 3.3 表的那個部件（比假畫布呼叫紀錄和直接呼叫該部件相同，含 `k`）|
| T-A2 | **圓章大小與位置**：`px` 32／42／48／64 × `res` 1、2 的 `D`、`far`、`near` 照需求 3.1 第 3 點；真 1 倍 32→13、42→18、48→20、64→27；內圓色＝`mix(KEYWORD_COLOR[kw], "#191b22", 0.72)`、沒有 `stroke` |
| T-A3 | **角**：`KEY_CORNER` 逐列鎖住（需求 3.2 表＋樣張原表）；沒列的預設右下；105 款沒有任何一款放右上 |
| T-A4 | **只畫一個圓章**：每款 × 1／2／3 個關鍵字，圓章只有一個、用 `keywords[0]`；1 個沒有記號；2、3 個記號相同（點色＝`keywords[1]`） |
| T-A5 | **記號**：`s`（真 1 倍 32／42／48→7、64→11；2 倍 32→11、42→15、48→17、64→23）、方向（手套 3 種右、`tome/scroll`、`hat/wide` 左、右下且斜放左、其餘照角）、夾邊、點色原色、不認得 `#f2e6c8`、`G ≤ 4` 方點 3×3（真 1 倍） |
| T-A6 | **撞擊簡化形**：`cpx ≤ 14`（圓章 13、18）畫需求 3.3 第 5 點的牆與七角星（比座標字串）、不呼叫 `on_collision`；`cpx > 14` 呼叫 `on_collision`；`parts.ts` 的 `on_collision` 呼叫紀錄和開工前相同（D2） |
| T-A7 | **貼圖對齊整數裝置像素、不丟例外**：所有 `blit` 左上 × `res` 是整數、沒有 4 個以上參數的縮放 `drawImage`；不認得的關鍵字、空陣列、`null` 不丟例外、不畫 |
| T-A8 | **`statusTile` 86 種**：名詞表 118 個的 `tileCanvas(statusTile(id), 24)` 都不再呼叫 `statusGlyph`（`GLYPH` 的筆畫）；32 種呼叫紀錄和開工前相同；86 種等於「Q 版圓片＋`status.ts` 的 `entry(id).d`」；`brand_new_status` 仍畫現行第一個字；圓片的環仍是 `FAINT_RING`（第 0 節第 9 列）；`qi3bWiring.test.ts` 的「其餘經 `hooks.status`」那條改寫（舊：hook 收到 86 個 → 新：hook 收到 86 個且全部走 `status.ts`）；A4 的兩份基準只變名單內的鍵 |
| T-A9 | **遊戲裡的裝備圖示不變**：`gearIcon.ts`、`GearIcon.tsx` 不在 `git diff` 裡；`gearIcon.test.ts`、`qIconArmor.test.ts`、`qIconWeapons.test.ts` 不改一字通過 |

### 7.2 QI-4b（vitest＋pytest）

| # | 測什麼 |
|---|---|
| T-B1 | **接線**：`drawGear(…, chips = true, slot, px, res)` 的關鍵字層呼叫紀錄＝直接呼叫 `keywords.paint`（105 款 × 32／40／42／48／64 × `res` 1、2）；`px < 32`（例 20、31）不畫；`chips = false` 不畫 |
| T-B2 | **快取鍵**：`gearIconKey` 少一欄、含 `px`；32 與 36 不同鍵；同輸入同字串（既有「屬性順序無關」照過） |
| T-B3 | **舊畫法拿掉**：`gearIcon.ts` 沒有 `motif`／`motifs`／`SMALL_ICON_MAX_PX`；原始碼掃描（`test/sourceScan.ts`）全專案沒有 import 它們 |
| T-B4 | **`keywordNames`**：`gearAppearance.json` 12 個都有名稱（`ignite` → 點燃 … `high_ground` → 高處、`summon` → 召喚物；注意樣張 `LIST.zh` 寫「高地」「召喚」，以內容為準）；pytest `tests/content/test_appearance.py` 檢查和 `skill_keywords.yaml` 一致、JSON 沒有過期 |
| T-B5 | **說明框**：`gearKeywordLine` 對 0／1／2 個、含不認得、含元素關鍵字（`element: "fire"`）的外觀回對的字串；`itemTipLines` 在詞條行之後多這一行、沒有關鍵字時和改前逐字相同；`GearCardView` 有 `gear-card-keywords`（純函式抽出來測）；`HeroGearPanel`、`UnitInfo` 的說明卡行含這一行 |
| T-B6 | **既有測試改寫**（逐條「舊 → 新」，不放寬）：`gearIcon.test.ts`「快取鍵包含是否小圖；36px 以下為小圖」→「32px 以上畫圓章；鍵含 px」；「小圖仍保留元素混色」照留（`chips = false`）；`qIconArmor.test.ts` 207、222、230 行傳 `px <= 36` 的地方 → 改傳 `px >= 32` 的語意並說明；`qIconWeapons.test.ts` 201 行；`gear/gearPreview.test.ts` |
| T-B7 | **不動的確認**：框、稀有度色塊、主圖、寶石色的呼叫紀錄和開工前相同（同一套 `grab`，只比關鍵字層以外的部分）；`render/__snapshots__/` 不變 |

### 7.3 QI-4c（vitest）

| # | 測什麼 |
|---|---|
| T-C1 | **3 個以上會留第一個圖示**：構造「精簡列＋徽章、`normal`／`shift` 放不下、`one-r` 放得下」的情況 → 選 `one-r`、留下的是 `sortStatuses` 第一個、膠囊數字 N − 1；`one-*` 全放不下 → 照舊 `plus-*` |
| T-C2 | **底線不放寬**：`one-*` 超出格子 > `ROW_PLUS_OVERFLOW_MAX` 或數字隔 < 3px 時不選；不碰朝向三角形、不超出地圖邊 |
| T-C3 | **改前／改後表**（寫進報告，測試鎖住改後）：1600／1040／800 × 朝東南西北 × 狀態 2／3／4 個 × 有蓄力徽章／有灌注徽章／相鄰單位的臉，每格寫改前、改後的顯示方式；**3b-04 第一列右那一格**（800、暈眩＋燃燒＋1）單獨一列；6F-20 的 9 種照舊（1600 朝北仍 `one`） |
| T-C4 | **既有測試**：`ui/badgeCapsule.test.ts`、`ui/statusBadges.test.ts`、`render/rowLayout` 相關、`ui/narrowMapLayout.test.ts`、`ui/summonBadges.test.ts`：因規則改變而改的斷言逐條寫「舊 → 新」並說明對到 C1 哪一點；其他不改一字通過 |

## 8. 驗收條件

### 8.1 共通

1. 本段第 7 節的測試全過；改寫的既有測試在報告逐條說明。
2. `corepack pnpm -C client typecheck`、`corepack pnpm -C client test`、`corepack pnpm -C client build` 三個結束碼都是 0（分開記）。`render/inkDollSnapshot.test.ts`、`render/creaturePose.test.ts` 通過且快照沒有變。
3. **合併前的 slow 測試**：4a、4c 不動 Python 與 `content/`——`UV_NO_SYNC=1 uv run pytest -q tests/api/test_client_fixtures.py`（`glossary.json` 仍是最新）。4b 另跑 `UV_NO_SYNC=1 uv run pytest -q tests/content/test_appearance.py tests/api/test_openapi_snapshot.py` 與 `uv run ruff check`、`uv run ruff format --check`、`uv run mypy`、`uv run lint-imports`（守則 11）。動到 `content/` 的資料檔就停下回報。
4. **4a**：遊戲裡的裝備圖示不變（T-A9）；`core.ts`、`weapons.ts`、`armor.ts` 不改；`parts.ts`／`skills.ts` 只多 `export`（`git diff` 為證）。
5. **4b、4c `window.__layoutSmoke`**：`corepack pnpm -C client build` 後啟動自己的 `trpg serve`（存檔放暫存區），1600×900、1040×624、800×600 各 `localStorage.clear()` → `/?dev=1&anim=0.1&mute=1` → `runCase("標題")` 全 PASS；4b 另 `runTown` 打開背包後 `icons()` 全 PASS（裝備圖示畫布＝顯示 × 2、`gear-fit` 左上角對齊）。
6. **4b 浮動卡實測**（6.5.1）：1600×900 與 800×600 各做一次「滑過背包身上裝備格的圖示 → 滑進說明卡 → 卡內捲到底 → 釘住 → 關閉」，確認「關鍵字：…」那一行在卡上。結果寫進報告。
7. 截圖存 `docs/art/shots/qi4/`（D5）；`--force-device-scale-factor=1` 拍；放大用最近鄰。實機到不了的用開發頁畫並在報告「實機未看」逐項列出。報告寫完整路徑。
8. 需求第 5 節末 (a)～(c) 寫進報告：(a) 和樣張逐像素比對（4a）；(b) 舊 `motif()` 的去留（4b）；(c) 說明框有沒有列出全部關鍵字（4b，連同第 0 節第 2 列「全部」的定義）。

### 8.2 截圖分配

「真 1 倍」＝開發頁 `res=1`；「DPR 2」＝`res=2`；兩種都最近鄰放大、裝置像素比 1 拍。張數不夠時把真 1 倍與 DPR 2 拼在同一張。

| 項目 | 段 | 內容 | 張數估計 |
|---|---|---|---|
| 需求第 5 節第 1 項 背包模擬 16 件 | 4a | `set=bag`：32、42 真 1 倍 ×4，對照 `closeup/qicons/keywords/bag32-dot.png`、`bag42-dot.png` | 1（PNG） |
| 第 2 項 105 款總表 | 4a | `set=all`：32 真 1 倍＋DPR 2，分兩張（`from`／`n`） | 2（PNG） |
| 第 3 項 12 個圓章（含撞擊 13／18） | 4a | `set=chips`：13、18、20、27 真 1 倍＋DPR 2 ×6 | 1（PNG） |
| 第 4 項 點色 12 × 五稀有度 | 4a | `set=dots`：32 真 1 倍 ×4 | 1（PNG） |
| 第 5 項 例外表的款 | 4a | `set=corner`：32、48 | 1（PNG） |
| 第 6 項 一個／三個關鍵字 | 4a | `set=count`：32、48（可併進第 5 項那張） | 0～1（PNG） |
| `statusTile` 86 種（驗收 4.3 驗收欄） | 4a | `status-gallery.html?set=tile&px=18,24,26`：真 1 倍＋DPR 2 ×6，和 `qi3/3b-06` 同排；元素架勢 45 個會是 9 組同圖 | 1～2（PNG） |
| 第 7 項 實機：背包 42、身上裝備格（`fit`，1600 寬 48／800 寬 39）、32（主角面板或單位資訊）、裝備卡或說明框（含「關鍵字：…」） | 4b | 1600 與 800 各一張（jpg），說明框裁切合成 | 2（jpg） |
| QI-2c 補拍：工坊 56 卡片預覽 | 4b | 1600、800 各一，裁切合成一張（驗收 1 節第 8 項） | 1（jpg） |
| QI-2c 補拍：800 工坊 96／40／28 | 4b | 800×600 工坊（驗收 1 節第 9 項） | 1（jpg） |
| QI-2c 補拍：背包身上裝備格左上對齊 | 4b | 1600@1 真 1 倍 ×6 最近鄰（驗收 1 節第 12 項） | 1（PNG） |
| 頭頂擁擠 | 4c | 3b-04 那一格改後（800）＋1040 一格，×6 最近鄰拼一張；800 實機全景一張 | 2（PNG＋jpg） |

合計 4a 約 8～9 張、4b 約 5 張、4c 約 2 張。

## 9. 開發中跑的測試

- **QI-4a**：`corepack pnpm -C client exec vitest run src/render/qIcon/ src/render/qi3bWiring.test.ts src/render/qi2cStatusUnchanged.test.ts src/render/skillIcon.test.ts src/render/statusIcon.test.ts src/render/gearIcon.test.ts src/test/importCycles.test.ts <新測試檔>`。
- **QI-4b**：`corepack pnpm -C client exec vitest run src/render/gearIcon.test.ts src/render/qIcon/qIconArmor.test.ts src/render/qIcon/qIconWeapons.test.ts src/render/qIcon/ src/gear/ src/run/ src/ui/gear/ src/world/bagScreen.test.ts src/ui/floatCardRule.test.ts src/dev/layoutSmoke.test.ts src/test/importCycles.test.ts src/test/sourceScan.test.ts <新測試檔>`；`UV_NO_SYNC=1 uv run pytest -q tests/content/test_appearance.py -x`。
- **QI-4c**：`corepack pnpm -C client exec vitest run src/ui/badgeCapsule.test.ts src/ui/statusBadges.test.ts src/ui/narrowMapLayout.test.ts src/ui/summonBadges.test.ts src/render/ src/dev/layoutSmoke.test.ts <新測試檔>`（`src/render/` 太大時改列與 `badgeLayout`／`rowLayout`／`unitSprite` 相關的檔）。
- 每次 commit 前 `corepack pnpm -C client typecheck`；交件前跑第 8.1 節第 2、3 點（結束碼分開記，全部 0 才交）。

## 10. 報告格式

各段寫 `docs/phases/PhaseQI-4a報告.md`、`PhaseQI-4b報告.md`、`PhaseQI-4c報告.md`：

1. 做了什麼（交付項目逐條，附 commit）。
2. 驗收逐條（測試名稱或指令輸出為證；結束碼分開記）。
3. 改寫的既有測試（舊斷言 → 新斷言）；基準與快照變動（4a 兩份基準逐筆名單與「拿掉改動回到舊值」的證明；其他預期沒有，有就先停下回報）。
4. 需求第 5 節末 (a)～(c) 中本段負責的；截圖清單（完整路徑、對到第 8.2 節哪一項、真 1 倍或 DPR 2）；「實機未看」清單。
5. 4a：和樣張不同的地方（依賴改 import、`KEYWORD_COLOR` 取代 `KC`、沒搬的分支）逐條；`parts.ts` 等加的 export；超過 80 行的函式（逐行搬的長函式不拆）。
6. 4b：說明框加在哪幾處（檔名＋截圖）；請使用者重開伺服器檢查的重點（背包 42、身上裝備格、主角面板 32 的圓章與點；說明卡的「關鍵字」行；戰場定時炸彈／蓄力徽章的新圖）；需求第 6 節「交使用者時要講明」6 點原樣轉列。
7. 4c：T-C3 的改前／改後表；3b-04 那一格的結果；仍只留「+N」的情況與原因。
8. **待 PM 決定**：最多 10 點，每點附出處；原型數值與解讀類照最保守做完再列。
9. 順手更新 `docs/dev/上手-前端戰鬥畫面與動畫.md`：第一節表加 `qIcon/keywords.ts` 一列、改 `gearIcon.ts` 列（`motif()` 拿掉、門檻 32）、`skillIcon.ts`／`skillParts.ts` 列（`hooks.status` 改 Q 版）；開發入口表加 `keyword-gallery.html`、改 `status-gallery.html` 的 `set=tile`；第四節第 40、47 點改寫、加踩到的坑；第五節測試表加列。

## 附：起草時查到的疑點（給開發 PM／美術 PM）

1. **說明框現在沒有列關鍵字（需求 1.3 第 3 點「待查證」的結果）**：
   - 裝備的說明卡只有詞條文字：`run/gearOffer.ts` 的 `itemLines`／`itemTipLines`（基礎加成、副手特性、詞條 `text_zh`）用在 `GearCardView`（卡本體與「目前的」比較）、`BagScreen.wornTipLines`（背包身上裝備格）、`RunHeroPanel`；`HeroGearPanel`、`UnitInfo` 用 `gear/affixStatus.ts` 的 `tipLines(e.affixes)`。
   - 背包格 42 的 `<Hint>` 是 `bagGrid.cellHint`＝「名稱・種類」；郵件 32、獲得動畫 32 沒有說明框；靶場起始武器 40 的關鍵字來自武器表 `element`。
   - 詞條文字有時含關鍵字名（例「利用點燃的技能傷害 +{n}」），但不是一對一：「普攻帶雷電」對到的是「帶電」，「你施加的{status} +N 回合」看不出關鍵字；前端另加的元素關鍵字完全沒出現在說明裡。
   - 前端沒有關鍵字中文名的資料（第 0 節第 1 列）。所以「補上」要新資料來源，不只是改元件。
2. **需求 3.1 第 1 點「`GearIcon` 只收 32／48／64（背包 42 是 48 經 CSS 縮小）」不是現況**：QI-1b 起 `GearIcon` 收任何整數、CSS 不准縮放；實際呼叫 32（`HeroGearPanel`、`UnitInfo`、`RunHeroPanel`、`GearCardView` 比較列、`MailPanel`、`GainEffects`）、40（`RangeClassPick`）、42（背包格）、48（`ItemList`）、64（`GearCardView`、`SlotGrid`、`CustomItemForm`）與 `fit`。沒有固定 < 32 的呼叫處；`fit` 在比 800 更窄的寬度可能 < 32，照美術建議不畫。
3. **需求第 5 節第 7 項「身上裝備格（32）」**：背包的身上裝備格是 `fit`（1600 寬 48、800 寬 39，上手筆記第四節第 28 點）；32 是主角面板與單位資訊。截圖分配已改成兩種都拍。
4. **「三個關鍵字」在遊戲裡不會出現**：後端 `max_keywords: 2`、`derive_keywords(limit=2)`，前端 `resolveGear` 也截 2 個；需求第 5 節第 6 項只能在開發頁畫。
5. **關鍵字中文名兩處不同**：樣張 `LIST.zh` 寫「高地」「召喚」，內容 `skill_keywords.yaml` 是「高處」「召喚物」；說明框以內容為準（T-B4）。樣張檔頭的註解仍是第 2 版（「≤36px 一個，>36px 斜放兩個」），以需求為準。
6. **色環**：驗收 4.3 說「照現行 `statusColor` 的淡色環」，現行 `statusTile` 其實是白 30% 的 `FAINT_RING`（第 0 節第 9 列）。
7. **頭頂擁擠的改法和美術自己的兩個舊決定衝突**（6F-19 決定 X 限 2 個狀態、6F-20 (a) 800／1040 維持「+2」），而且 6F-20 報告算過「1 個圖示＋膠囊」比兩個圖示還寬，800 寬多半仍放不下（第 0 節第 7、8 列）。這兩個決定只在 `docs/art/`，沒寫進 `docs/design/`。
