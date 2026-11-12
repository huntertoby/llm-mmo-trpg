# Phase QI-4a 報告：⑤b 關鍵字小圓章搬畫法（點版）＋開發頁、`statusTile` 其餘 86 種換 Q 版

> 實作者（Opus 5.5），2026-11-12。規格：`docs/phases/PhaseQI-4計畫.md`（第 0.0 節定稿與美術 PM 書面答覆、第 0 節表、QI-4a 各節；4c 已拿掉）。起點：main `190f7bd7`（含 `1e64f3a5` QI-4 規格與美術答覆）。未 push。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| A3 `statusTile` 86 種 | `render/skillParts.ts` 的 `QP.hooks.status` 改成：`qIcon/status.ts` 的 `entry(id)` 認得就畫 `e.d(c, o)`；不認得（名詞表以外）照 QI-2c 的現行圖樣（`statusGlyph`＋`statusColor`）原樣退回。檔頭、`KNOWN_PARTS` 註解、`skillIcon.ts` 的 `statusTile` 與工坊狀態選項註解跟著改（只改註解）。色環照舊 `FAINT_RING`（美術 PM 答覆 (1)） | `c5702347` |
| A4 基準重錄 | `render/fixtures/qi3bStatusBaseline.json` 逐筆重錄（只有 86 個 `head|<id>` 變）；`qi2dBaseline.json` 不變（名單為空，第 3 節） | `c5702347` |
| A1 `qIcon/keywords.ts` | 由 `docs/art/sample/qIconsKeywords.js`（`07d85471` 之後）逐行搬：`LIST`（12）、`KEYS`、`glyph`、`RATIO`／`MARGIN`、`sizeOf`、`bgOf`、`chip`、`known`、`at`、`KEY_CORNER`（樣張原表）、`isDiag`、`cornersOf`、`MORE_DIR`（只有 `edge`）、`MORE_DIR_KIND`、`MORE_DIR_DIAG`、`moreDirOf`、`moreSize`、`moreBox`、`more`（只有點版）、`paint`、`chipCanvas`、撞擊簡化形 `collision`。只有點版、只畫一個圓章 | `ead95db7` |
| A5 測試 | 新 `render/qIcon/qIconKeywords.test.ts`（T-A1～T-A7、T-A9，18 項）、`render/qi4aStatusTile.test.ts`（T-A8，6 項）；改寫 `render/qi3bWiring.test.ts` 1 項、`render/qi2cStatusUnchanged.test.ts` 1 項（第 3 節） | `ead95db7`、`c5702347` |
| A2 開發頁 | 新 `client/dev/keyword-gallery.html`＋`client/src/dev/keywordGallery.ts`：`?px=`、`&res=`、`&zoom=`、`&rarity=`、`&set=bag|all|chips|dots|corner|count|legacy|compare`、`&from=&n=`、`&label=0`、`&sample=`；`window.__qiKwDev`；款式清單用 `gearAppearance.json` 的 `kinds`（和另兩頁同來源）。`dev/statusGallery.ts` 的 `set=tile` 收 `?px=`／`&res=` 清單、標籤改「Q 版（hooks）」、`&old=1` 並排 4a 以前的掛鉤圖樣 | `cf52e223` |
| A6 樣張對照 | 第 4 節 | — |
| A7 截圖 | `docs/art/shots/qi4/4a-*.png` 10 張 | `d805c8a0` |
| A7 報告、上手筆記 | 本報告；`docs/dev/上手-前端戰鬥畫面與動畫.md` | 本 commit |

**`parts.ts`、`skills.ts` 沒有加任何 export**（`entry`、`BOX`、`ELEMENT`、`ACT` 本來就匯出）。`core.ts`、`weapons.ts`、`armor.ts`、`parts.ts`、`skills.ts`、`gearIcon.ts`、`ui/GearIcon.tsx` 的 diff 都是空的（`git diff --stat 190f7bd7..HEAD -- <這些檔>` 無輸出）。

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| T-A1 | 12 個圖樣、同序、色、來源 | 過：`KEYS`＝`gearAppearance.json` 的 `keywords`；`KEYWORD_COLOR`＝樣張 `KC` 逐筆；`k` 照需求 3.3；12 個的呼叫紀錄（含 halo 另建畫布）和直接呼叫該部件逐筆相同（`small`／`tiny` 各組）；`glyph` 的 1.8 倍與 ≤14px 不包外框 |
| T-A2 | 圓章大小與位置 | 過：32／42／48／64 × res 1、2 的 `D`、`far`、`near`；真 1 倍 13／18／20／27；外圓 `#16121a` → 內圓 `mix(色, #191b22, 0.72)`（半徑 D/2 − 1 裝置像素）；外層沒有 `stroke` |
| T-A3 | 角 | 過：`KEY_CORNER` 逐列鎖住；105 款照「kind/form → kind → 右下」，沒有右上；表上每一列都對到實際的款（`def` 與 `{kind, form}` 兩種傳法結果相同） |
| T-A4 | 只畫一個圓章 | 過：105 款 × 32／48 × 1／2／3 個關鍵字：`drawImage` 一次、底色＝第一個；1 個沒有記號；2、3 個紀錄相同、點色＝第二個 |
| T-A5 | 記號 | 過：邊長 7／7／7／11、11／15／17／23；方向（手套右、卷軸匣與寬簷帽左、右下斜放左、其餘照角）105 款逐款；位置公式與夾邊 105 × 4 × 2；畫法逐筆（真 1 倍 3×3 方點）、不認得 `#f2e6c8`、G>4 畫圓 |
| T-A6 | 撞擊簡化形 | 過：tiny 畫牆＋七角星（座標字串）、和 `on_collision` 不同；非 tiny 和 `on_collision` 逐筆相同；13、18 簡化、27 不簡化（res 1、2）。`parts.ts` 的 `on_collision` 沒改：`qIconQi2d.test.ts`（部件基準含 `trigger:on_collision`）不改一字通過 |
| T-A7 | 對齊、不丟例外 | 過：105 × 兩個關鍵字 × 4 尺寸 × 2 res，`blit` 左上 × res 為整數、`drawImage` 只有 5 個參數；不認得、空陣列、null、undefined 不畫不丟例外；`chipCanvas` 沒有畫布回 null |
| T-A8 | `statusTile` 86 種 | 過（`qi4aStatusTile.test.ts`）：118 個 `status.ts` 都認得；86 種呼叫紀錄＝「掛鉤直接畫 `entry(id).d`」且≠舊圖樣；32 種換掉掛鉤紀錄不變；`brand_new_status` 照舊畫第一個字（有 `fillText`）；環 `rgba(255,255,255,0.3)`、半徑 42；全部部件 × 18／30 × res 1、2 沒有一筆經掛鉤 |
| T-A9 | 遊戲裡的裝備圖示不變 | 過：`gearIcon.ts`、`GearIcon.tsx` 不在 diff 裡、原始碼不含 `qIcon/keywords`；`gearIcon.test.ts`、`qIconArmor.test.ts`、`qIconWeapons.test.ts` 不改一字通過 |
| 8.1-2 | 三個結束碼 | `corepack pnpm -C client typecheck` **0**；`corepack pnpm -C client test` **0**（301 檔、3839 項）；`corepack pnpm -C client build` **0**（只有既有的 chunk 大小警告） |
| 8.1-2 | 快照 | `inkDollSnapshot.test.ts`、`creaturePose.test.ts` 在整包通過；`render/__snapshots__/` 沒有變動 |
| 8.1-3 | slow 測試 | `UV_NO_SYNC=1 uv run pytest -q tests/api/test_client_fixtures.py`：4 passed；沒有動 Python、`content/` |
| 8.1-4 | 4a 範圍 | 見第 1 節末（`core.ts`、`weapons.ts`、`armor.ts` 不改；`parts.ts`／`skills.ts` 也沒加 export） |
| 8.1-7 | 截圖 | 10 張 PNG（最近鄰），單張 139～288 KB；無頭 Chrome `--force-device-scale-factor=1`、`--mute-audio`、`--disable-gpu`，網址 `?mute=1` |
| — | 相關測試 | `vitest run src/render/qIcon/ src/render/qi3bWiring.test.ts src/render/qi2cStatusUnchanged.test.ts src/render/qi4aStatusTile.test.ts src/render/skillIcon.test.ts src/render/statusIcon.test.ts src/render/gearIcon.test.ts src/test/importCycles.test.ts`：13 檔 206 項過 |

## 3. 改寫的既有測試、基準與快照

**改寫的既有測試**

1. `render/qi3bWiring.test.ts`「第④批 STATUS 32 種畫 Q 版圖樣；其餘經 QP.hooks.status」：舊＝掛鉤收到 86 個（現行圖樣）→ 新＝掛鉤收到 86 個，**而且每個 `QT.entry(id)` 都不是 null**（全部走 `status.ts`）。其他斷言不動。
2. `render/qi2cStatusUnchanged.test.ts`「基準裡相同的雜湊只有元素架勢同元素的各級」：舊＝同雜湊只有 `card|stance_*`、部件圓片 118 個兩兩不同 → 新＝同雜湊是 `card|` 或 `head|` 的同元素 5 級（不跨卡與圓片）、部件圓片 **82 種**（118 − 9 元素 × 4）。理由：部件圓片的元素架勢改走 `status.ts`，各級同圖（規格第 8.2 節「元素架勢 45 個會是 9 組同圖」）。檔頭加 QI-4a 的說明。其他兩項（＝基準且 236 組都≠QI-2c 舊基準；換成什麼）不改。

**`qi3bStatusBaseline.json`（重錄，用 `qi2cStatusUnchanged.test.ts` 同一段 `record()`，鍵順序與格式不變）**：236 筆中**只有 86 筆變**，全部是 `head|<id>`，名單＝名詞表 118 個裡不在第④批 `QP.STATUS` 的 86 個（測試由資料算出，不手寫）：

armor_broken、array_ward、charging、commanding、crystal_surge、crystal_surge_2、entangled、frost_ember_burst、hard_shell、heart_ember_burst、heart_link、league_truce、mist_return、molten_burst、molten_shell、oath_bonus_easy、oath_bonus_hard、oath_bonus_medium、oath_broken、overdrawn、race_adapt、race_stonewall、rallied、revealed、rift_channel、rift_collapse、rift_resonance、shard_burst、shielded、shielded_marking、shielded_mending、shielded_thorns、shielded_wet、soul_link、stance_bastion、stance_blaze、stance_earth_1～5、stance_fire_1～5、stance_flame、stance_frost、stance_glacier、stance_holy_2～5、stance_ice_1～5、stance_lightning_1～5、stance_physical_1～5、stance_poison_1～5、stance_shadow_2～5、stance_wind_1～5、summit_array_ward、sword_formation、time_bomb、undying。

32 個 `head|`（第④批）與 118 個 `card|` 一筆都沒變（`git diff c5702347~1 c5702347 -- client/src/render/fixtures/qi3bStatusBaseline.json`：86 增 86 刪，沒有 `card|`）。

**`qi2dBaseline.json`：名單為空、檔案不動。** 改動前先用同一套迴圈（全部 `QP.CATS` × 18／30 × res 1、2 的 `chipCanvas`／`cardCanvas`）把 `hooks.status` 包一層記錄：**沒有任何一筆經過掛鉤**（`CATS.status` 只有第④批 32 種、效果 `status:*` 與條件 `target_has_status:*` 不是 `CATS` 的鍵）。改動後 `qIconQi2d.test.ts` 不改一字通過；`qi4aStatusTile.test.ts` 最後一項把「沒有一筆經掛鉤」鎖住。

**「拿掉本段改動回到舊值」的證明**：把 `skillParts.ts` 換回 `190f7bd7` 版（其他不動）→ 新的 `qi2cStatusUnchanged.test.ts` 第 1 項與 `qi4aStatusTile.test.ts`「86 種＝entry(id).d」失敗；再把 `qi3bStatusBaseline.json`、`qi2cStatusUnchanged.test.ts`、`qi3bWiring.test.ts` 也換回 `190f7bd7` 版 → `qi2cStatusUnchanged`、`qIconQi2d`、`qi3bWiring` 三檔 32 項**全過**（舊基準 236 筆全同）。換回本段的檔後全過。

快照 `render/__snapshots__/` 沒有變動；沒有整批重產任何 fixture。

## 4. 需求第 5 節末 (a)、截圖、實機未看

**(a) 和樣張逐像素對照**：自己的 vite（5305）開 `keyword-gallery.html?set=compare&sample=http://127.0.0.1:8151/`，同一頁從自己的 CORS 靜態伺服器（8151，根目錄 `docs/art/sample/`）抓 `qIcons.js`、`qIconsWeapons.js`、`qIconsArmor.js`、`qIconsSkills.js`、`qIconsParts.js`、`qIconsStatus.js`、`qIconsKeywords.js`，載入前把 `M`／`MAT` 鐵鋼銅換成遊戲端的色（同 QI-3a）。兩邊交錯著畫、`getImageData` 逐像素比；無頭 Chrome `--disable-gpu`、剛載入的頁面。

| 比對 | 組數 | 0 像素不同 |
|---|---|---|
| 只有關鍵字層：105 款 × 兩個關鍵字（樣張 `PAIRS` 6 組輪流）× 32／42／48／64 × res 1、2（每款用各自的 `def`：遊戲端 `gearQDef`、樣張 `QW.def(look, true)`／`QA.def`） | 840 | 840 |
| 12 個圓章 × 13／18／20／27 × res 1、2（`chipCanvas`） | 96 | 96 |
| 105 款的角（`cornersOf(def)[0]`，遊戲端 vs 樣張） | 105 | 105 |

沒有 ±1 雜訊，也沒有 `mix` 四捨五入差異。另外確認比對不是空跑：105 款的關鍵字層畫布都有 >50 個不透明像素。

**樣張端指紋** `uv run python docs/art/sample/tools/qicons_shots.py --hash keywords`（結束碼 0，119 列）：12 列 `chip <kw> | …`（13／18／20／27 × 真 1 倍、2 倍）和遊戲端用同一個 FNV 算法算 `chipCanvas` 的結果 **96 個逐字相同**。其餘 107 列是樣張的整格裝備（框＋主圖用樣張自己的材質色），和遊戲端主圖的材質色本來就不同（QI-1 0.0），不拿來比；關鍵字層已在上表比過。

**截圖**（`docs/art/shots/qi4/`，全部 PNG、最近鄰、裝置像素比 1）

| 檔 | 對到 8.2 | 內容 |
|---|---|---|
| `docs/art/shots/qi4/4a-01-bag-32-42-true1x-x3.png` | 第 1 項 | 背包模擬 16 件，32、42 真 1 倍 ×3（對照 `closeup/qicons/keywords/bag32-dot.png`、`bag42-dot.png`） |
| `docs/art/shots/qi4/4a-02-all32-true1x-dpr2-x2-1.png` | 第 2 項 | 105 款總表第 1～35 款，32 真 1 倍與 DPR 2（各一段）×2；標籤寫角 |
| `docs/art/shots/qi4/4a-03-all32-true1x-dpr2-x2-2.png` | 第 2 項 | 同上第 36～70 款 |
| `docs/art/shots/qi4/4a-04-all32-true1x-dpr2-x2-3.png` | 第 2 項 | 同上第 71～105 款 |
| `docs/art/shots/qi4/4a-05-chips-13-18-20-27-true1x-dpr2-x6.png` | 第 3 項 | 12 個圓章 13／18／20／27，真 1 倍與 DPR 2 ×6 |
| `docs/art/shots/qi4/4a-06-dots-true1x-x4.png` | 第 4 項 | 點色 12 × 五稀有度，真 1 倍 ×4 |
| `docs/art/shots/qi4/4a-07-corner-32-48-true1x-x2.png` | 第 5 項 | 例外表 40 款（KEY_CORNER 與記號方向例外表列到的），32、48 真 1 倍 ×2；標籤寫角／記號方向 |
| `docs/art/shots/qi4/4a-08-count-32-48-true1x-x3.png` | 第 6 項 | 一個／兩個／三個關鍵字 × 6 款，32、48 真 1 倍 ×3 |
| `docs/art/shots/qi4/4a-09-statustile-18-24-26-true1x-x3.png` | `statusTile` | 部件圓片 18、24、26 真 1 倍 ×3（名詞表 118 個） |
| `docs/art/shots/qi4/4a-10-statustile-24-dpr2-x2.png` | `statusTile` | 部件圓片 24 DPR 2 ×2（裝置像素 1:1） |

規格估 8～9 張，實拍 10 張：105 款總表在 300 KB 內只放得下 35 款一張（分三張），`statusTile` 的 DPR 2 只拍 24（戰場定時炸彈／蓄力徽章的尺寸；18、26 DPR 2 沒拍，見待決 6）。

**實機未看**：本段不接遊戲的裝備圖示，關鍵字全部用開發頁畫（第 7 項實機是 4b）。`statusTile` 有接到遊戲（組裝列、工坊狀態選項、戰場定時炸彈／蓄力徽章），本段只用開發頁 `status-gallery.html?set=tile` 畫，**實機未看**（4b 的實機巡檢可順便看戰場的定時炸彈徽章）。

## 5. 和樣張不同的地方、長函式

- 依賴改 import：`ELEMENT`、`ACT` 從 `./skills`；`entry`、`BOX` 從 `./parts`；`render`、`blit`、`outlinePx`、`blank`、`ctxOf`、`rr`／`f`／`poly`／`starPts`、`OUT`、`TAU`、`mix` 從 `./core`。
- `KEYWORD_COLOR` 取代樣張 `KC`（值相同，T-A1 鎖住）。
- `LIST` 的元素道具與記號改成畫的時候才查 `QS.ELEMENT[id]`／`QS.ACT[id]`（樣張在載入時取 `.d`）：`skills.ts` import `gearIcon.ts`，4b 由 `gearIcon.ts` import 這個檔時，載入時取值會撞到還沒初始化的表。呼叫順序與參數不變（逐像素 0 差異）。
- 沒搬：`KC`、`ELEMENT_KW`、`coverOf`／`coverMemo`／`CORNERS`、`areas`、`geom` 的環、`bgOf` 的 `opt.tint`、`chip` 的 `opt.ring`／`opt.bg`／`opt.gk`、`glyph` 的 `opt.ow`、`ONE_MAX_PX`、`TWO_DIAG`／`twoDiagOf`／`count`、`MORE_STYLES`／`MORE_STYLE`／`MARK`／`setMark`／`styleOf` 與 `dot`／`plus`／`stack`／`pill` 分支、`MORE_DIR` 的 `side`／`diag` 與 `opt.moreDir`、`paint` 的 `opt.one`／`v3`／`cs`／`maxKw`／`min`／`ratio`、`legacy`／`paintLegacy`（開發頁另抄）。`paint` 一律只畫一個圓章（樣張預設也是）。
- `paint`／`cornersOf`／`moreDirOf`／`isDiag` 收 `{ def }` 或 `{ kind, form, diag }`（給 4b 直接傳 `resolveGear` 的結果）；有 `def` 以 `def` 為準。兩者都沒給時和樣張「沒給 def」相同。
- `chipCanvas(kw, px, res)`（樣張 `(kw, px, zoom, o)`）；沒有畫布回 null。`chip` 遇到 `glyph` 回 null 時不貼。
- `LIST.zh` 照樣張（「高地」「召喚」），只給開發頁當標籤；說明框以內容為準（4b）。
- 超過 80 行的函式：**沒有**。

## 6. 待 PM 決定

1. **4b 會撞到執行期 import 環**：`qIcon/skills.ts` import `gearIcon.ts`（`resolveGear`），4b 讓 `gearIcon.ts` import `keywords.ts`（→ `skills.ts`、`parts.ts`）就成了 `gearIcon → keywords → skills → gearIcon`，`test/importCycles.test.ts` 會擋。建議 4b 開頭先把 `resolveGear`（與 `KINDS`、`NO_FORM`、`KEYWORD_OF_ELEMENT` 等）搬到不 import Q 版圖樣的小模組（例 `render/gearResolve.ts`，`gearIcon.ts` re-export），`skills.ts` 改從那裡 import。4a 沒動（不在範圍；`keywords.ts` 已做成載入時不取表的值，搬完即可接）。（出處：上手筆記第四節新第 51 點）
2. **撞擊簡化形在 48 真 1 倍也會用到**：門檻是圖樣 `cpx ≤ 14`，48 真 1 倍圓章 20 的 `cpx` 是 13.68，所以也畫牆＋星（樣張同樣，逐像素相同）；需求寫「圓章 13、18」。照樣張做，`4a-05` 截圖可看。若美術要 48 一律完整形，要改門檻（樣張也要改）。
3. **`paint` 多收 `{ kind, form, diag }`**（規格第 0 節第 5 列寫 `{ def, kind, form }`、A1 寫 `{ kind, form, diag }`）：兩種都收，`def` 優先；4b 可任選一種，建議傳 `gearQDef` 的 `def`（`diag` 由造型定義決定，和樣張同一個來源）。
4. **`qi2dBaseline.json` 不重錄**：A4 要「列名單再重錄」，實測名單為空（沒有部件經 `hooks.status`），重錄的結果和現檔完全相同，所以不動檔案；改用 `qi4aStatusTile.test.ts` 鎖住「沒有一筆經掛鉤」。
5. **部件圓片的元素架勢從此同元素 5 級同圖**（9 組各 5 個，含聖輝／暗影的 2～5 級借壹級圖）：照 `status.ts` 的畫法（各級同一個圖），所以 `qi2cStatusUnchanged` 的「部件圓片 118 個兩兩不同」改成 82 種。組裝列與戰場徽章看不出級數（狀態卡有角落級數，部件圓片沒有）。
6. **截圖 10 張、DPR 2 部件圓片只拍 24**：18、26 的 DPR 2 沒拍（300 KB 上限下放不進），真 1 倍三種都有；要補可開 `status-gallery.html?mute=1&set=tile&scene=0&label=0&px=18,26&res=2&zoom=2` 分張拍。
7. **`statusTile` 實機未看**：組裝列、工坊狀態選項、戰場定時炸彈／蓄力徽章本段只用開發頁畫；建議 4b 實機巡檢時順便拍一張戰場定時炸彈徽章。
8. **開發頁 `set=all` 的兩個關鍵字固定點燃＋標記**（同樣張 `?part=c`）；`compare` 才用 `PAIRS` 6 組輪流。`set=bag` 照樣張清單（樣張用 `material` 欄；遊戲端 `resolveGear` 認得的材質才用）。
9. **新增一個空的 `.venv` 不影響**：worktree 第一次 `uv run` 時建立（已 `uv sync --frozen --offline`），在 `.gitignore` 內。

## 7. 上手筆記更新

`docs/dev/上手-前端戰鬥畫面與動畫.md`：檔頭加 QI-4 的位置；第一節表加 `qIcon/keywords.ts` 一列、改 `skillIcon.ts`／`skillParts.ts` 列（`hooks.status` 改 Q 版、色環照舊）；開發入口表加 `keyword-gallery.html`、改 `status-gallery.html` 的 `set=tile`；第四節第 40 點（`qi3bStatusBaseline` 4a 重錄過、`head|` 82 種）、第 47 點改寫（86 種走掛鉤＝Q 版、測試換掛鉤要換回、`qi2dBaseline` 不經掛鉤）、新增第 51 點（4b 的 import 環）、第 52 點（撞擊簡化形的門檻）、第 53 點（截圖 PNG 大小）；第五節測試表加兩列。`gearIcon.ts` 那一列本段不改（4b 接線時改）。

## 8. 請使用者重開伺服器檢查的重點

遊戲裡的**裝備圖示不變**（4b 才接）。**會變的是部件圓片 `statusTile`**：技能組裝列的狀態效果／條件圓片、技能工坊的狀態選項、戰場上的定時炸彈與蓄力徽章，32 種以外的狀態從單色線條改成 Q 版彩色圖樣（環不變）。要看關鍵字圓章：自己的 vite 開 `/dev/keyword-gallery.html?mute=1&set=bag&px=32,42&res=1&zoom=3`（參數見 `dev/keywordGallery.ts` 檔頭）。
