# Phase KW-3 完成報告｜層數關鍵字的前端與美術移植（#161）

> 實作 agent，2026-11-13。依據：`docs/phases/PhaseKW計畫.md` KW-3 段；美術 `docs/art/KW樣張.md`（第 2 版，第 6 節移植、第 7 節指紋、第 9 節決定）、
> 審查 `docs/art/KW樣張-審查.md`。開工時 worktree 已快轉到 main `12d410797`。
> 五項都用 A 案；開發 PM 的兩個決定（創角 15px、HUD 0 層規則）照做。

## 1. 做了什麼

| 項目 | 檔案 | 內容 |
|---|---|---|
| 關鍵字色 | `client/src/render/palette.ts` | `KEYWORD_COLOR` 末尾加四筆：連擊 `#ff3d8b`、怒氣 `#df2046`、專注 `#476deb`、氣 `#29e0bc`；新增 `STACK_KEYWORDS`（這四個） |
| 圓章 ×4 | `client/src/render/qIcon/keywords.ts` | `LIST` 末尾加四筆（`comboSlashes` 直斬線 k 0.96、`furyEyes` 怒目 k 0.84、`focusFrame` 對焦框 k 0.8、`kiTaiji` 太極 k 0.92；≤14px 的簡化形照第 2 版：連擊兩道、氣沒有勾玉眼＋深半邊 `#0e7f6a`），三階色 `KW_TONE`；照 `docs/art/sample/qIconsKW.js` 逐行搬，只搬 A 案 |
| 裝備不帶 | `render/gearResolve.ts`、`render/qIcon/core.ts`（`gemAccent`）、`render/qIcon/keywords.ts`（`known`） | 三處都跳過 `STACK_KEYWORDS`：加進 `KEYWORD_COLOR` 後，裝備圓章、寶石色、說明框「關鍵字」行不會因為這四個變 |
| 創角圖示 ×4 | `client/src/ui/CreateIcons.tsx` | `KEYWORD_ICON_IDS` 16 個；`KEYWORD_ICON_COLOR` 加四筆（怒氣亮一階 `#ff4a62`，其他三個和圓章同色）；`keywordGlyph` 加四個 case（照 `CREATE[kw].a` 逐字抄，連擊的三條 path 由樣張的 `comboCreate` 算出）。尺寸照現行 15px（開發 PM 決定 1） |
| HUD 層數計量 | 新檔 `render/qIcon/stackGauge.ts`、`ui/StackPips.tsx`；`ui/statusCard.ts`（`hudStacks`）、`ui/Hud.tsx`、`styles/status-card.css` | 照樣張 ④ A 案逐行搬（格 6×10、步距 7、右內距 5；含膠囊連擊 60、怒氣 53、專注與氣 46；怒氣亮格 `#ff4a62`；滿層外暈＋關鍵字色框＋圓章外圈）。膠囊與外暈畫在畫布裡，畫布四邊多 4px、CSS 負邊距收回。四種層數在主角 HUD 改畫 `StackPips`（拿掉右下角數字，滑過說明照舊 `StackTip`），其他層數照舊 `StackBadge` |
| HUD 0 層 | `ui/statusCard.ts` 的 `hudStacks(unit, cards)` | 開發 PM 決定 2：四種計量在 0 層時，主角有會累積或消耗它的技能（技能卡 `stacks` 的 `makes`／`uses`）才顯示空格，否則整條不顯示 |
| 條件部件 | `client/src/render/qIcon/parts.ts` | `COND.self_stack_at_least` 換成 `condPips`（三個金格＋右下米白小人形，整體縮 0.9），取代 KW-1 暫代的「第一輪」 |
| 開發頁 | `client/src/dev/keywordGallery.ts` | `set=chips` 16 個；新增 `set=hud`、`set=cond`、`set=hash`；`dots`、`compare` 只用裝備外觀的 12 個；`__qiKwDev` 加 `gauge`、`hash` |
| 測試 | 新檔 `client/src/render/qIcon/qIconKW3.test.ts`（14 個）；改 `qIconKeywords.test.ts` T-A1、`ui/entryScreen.test.ts`、`tests/content/test_appearance.py` | 見第 2、3 節 |

`Hud.tsx` 只改了層數那一段（`activeStacks`＋`StackBadge` → `hudStacks`＋`StackPips`／`StackBadge`）與 import；沒有碰紙娃娃、塔盾、戰場瞄準標記、單挑插圖（RG-4 的範圍）。
`gearResolve.ts` 只動一行關鍵字過濾（見第 6 節第 2 點）。

## 2. 裝備不帶這四個關鍵字（鎖住）

- 前端 `qIconKW3.test.ts` 第 2 節：`resolveGear` 丟掉四個層數關鍵字（`["combo_point","ignite","fury","marked"]` → `["ignite","marked"]`）；`gemAccent([kw])` 金 `#e04060`、晶石 `#b8a8ff`，`[kw, "prone"]` 取倒地色；
  `gearKeywordLine` 回 `null`；`keywords.known` 跳過；`keywords.paint` 一筆都不畫；`gearAppearance.json` 的 `keywords` 沒有它們。
- 後端 `tests/content/test_appearance.py::test_gear_never_carries_stack_keywords`：層數關鍵字（關鍵字 id ＝ 它 `add_stack` 的層數 id）正好是這四個；外觀表沒有它們；
  79 個詞條逐一 `derive_keywords` 都推不出它們（裝備關鍵字全部由詞條推導）。

## 3. ART_PENDING 恢復前後的檢查數

| 測試 | KW-2（有 ART_PENDING） | KW-3 |
|---|---|---|
| `client/src/ui/entryScreen.test.ts`（創角圖示） | 「沒有圖示的關鍵字 ＝ ART_PENDING 4 個」；只檢查 **12** 個開局可選的關鍵字有專屬圖示、12 個圖示彼此不同 | 「沒有圖示的關鍵字 ＝ 0 個」；檢查 **16** 個開局可選的關鍵字（新增 `toHaveLength(16)`）都有專屬圖示、16 個彼此不同 |
| `tests/content/test_appearance.py`（裝備外觀） | 「全部關鍵字 − 外觀關鍵字 ＝ ART_PENDING 4 個」（當成美術待補） | 照設計：外觀關鍵字（12）＝全部關鍵字（16）− 層數關鍵字（4）；另加 `test_gear_never_carries_stack_keywords`（4 個層數關鍵字 × 外觀表＋79 個詞條） |

兩處 `ART_PENDING` 都拿掉了（程式裡只剩 `entryScreen.test.ts` 一行說明「已拿掉」的註解）。

## 4. 指紋

**新圖（`docs/art/KW樣張.md` 第 7 節）：9／9 行逐字相同。** 自己的 vite（127.0.0.1:5297）開 `/dev/keyword-gallery.html?set=hash&mute=1`，
無頭 Chrome `--headless=new --disable-gpu --mute-audio --force-device-scale-factor=1 --dump-dom`，抓 `#hash` 和第 7 節的程式碼區塊逐行比（腳本比，不是目測）：

```
chip combo_point a 4e7f4444 6e0d01c6 cdc4e277 e9f629d8 80b28f83 ab1a19b3 fed5b254 b569e608
chip fury a 048a19ad 252c0a17 af87d04d 965677d5 735cf2cf fd0c7e9d bdd1a41c 8c26486c
chip focus a e887cb0c 1642dad0 31d68dbe e2ca9824 56e5ec13 68248623 d3573e5e fb20635a
chip ki a 120c8e01 31eb60c3 abfd8a46 5b6a7363 98a21a51 801e140f c801039a bf2cae36
cond a 519471a4 f7d16d90 708a817b 90fc5715 b86b2464 8eb25b27
hud combo_point a 81c6f9ae b29d873e 5faba426 d33333ee c4a4cfae a0ac9de6
hud fury a 2135ae05 22ba0712 45643181 1227a45e 6a11bd81
hud focus a 7218316b 553ee020 1a7e222b 8e9435ef
hud ki a d06b0513 52bae7b5 a6625a87 d8f5779a
```

同一台機器先跑了樣張 `kw_shots.py --hash`，圓章與計量 8 行也和第 7 節相同（確認環境一致）。

**既有圖不變：**
- 裝備關鍵字層與 12 個圓章：`set=compare&sample=<樣張>`（樣張資料夾開帶 CORS 的靜態伺服器 127.0.0.1:5298）逐像素比——105 款 × 兩個關鍵字 × 32／42／48／64 × res 1、2 **840／840 相同**；12 圓章 × 13／18／20／27 × res 1、2 **96／96 相同**；角 105／105。
- 技能組裝列部件：`qIconQi2d.test.ts`（開工前錄的呼叫紀錄基準）通過，`self_stack_at_least` 本來就在 `ADDED_PARTS`（KW-1 加的、沒有基準），其他部件的紀錄不變。
- 既有 12 個創角圖示與顏色沒動（`KEYWORD_ICON_COLOR` 前 12 筆、`keywordGlyph` 前 12 個 case 未改）。
- 樣張畫法檔一個都沒改。

## 5. 截圖（`docs/art/shots/KW-3/`）

實機：自己的 `trpg serve`（127.0.0.1:5299，`TRPG_DEV_ROUTES=1`，存檔在暫存區）＋自己的無頭 Chrome（CDP 127.0.0.1:9641，`--remote-debugging-address=127.0.0.1 --disable-gpu --mute-audio`，DPR 1，網址 `?dev=1&anim=0.1&mute=1`）。
開發首頁單場戰鬥：武器匕首、關鍵字連擊＋怒氣（起始技能連刺／穿影、怒衝斬／盛怒擊）。

| 檔 | 內容 | 實機／開發頁 |
|---|---|---|
| `create-1600.png`、`create-1600-list.png`、`create-800.png`、`create-800-list.png` | 創角圖示：開局選單（`StartPickerView`，roguelite 新一輪與開發首頁共用）16 個關鍵字，四個新圖示在最後兩列，連擊、怒氣選中 | 實機 |
| `hud-1600-0.png`、`hud-1600-0-card.png`、`hud-800-0.png`、`hud-800-0-card.png` | HUD 0 層：連擊、怒氣兩條空格（主角有連擊、怒氣的技能）；專注、氣不顯示（沒有相關技能） | 實機（真資料） |
| `hud-1600-mid*.png`、`hud-800-mid*.png` | 中間：連擊 3／5、怒氣 2／4、專注 1／3、氣 2／3 | 實機，層數是包 fetch 造的（見下） |
| `hud-1600-full*.png`、`hud-800-full*.png` | 滿層：四條全亮、外暈、圓章外圈 | 實機，層數是包 fetch 造的 |
| `dev-chips-x4.png` | 16 個圓章 × 13／18／20／27，**真 1 倍 × 4 最近鄰**（四個新圓章在最後一列） | 開發頁（圓章單獨大小**實機未看**：遊戲裡只出現在 HUD 計量的 14px） |
| `dev-hud-x4.png` | 四種計量 × 0～滿層，**真 1 倍 × 4** | 開發頁（實機另見 `hud-*`） |
| `dev-cond-x4.png` | 條件部件「層數達 N」30／26／18／16，**真 1 倍 × 4**，和累積層數、消耗層數、第一輪並排 | 開發頁，**實機未看**（開局的起始技能沒有用這個條件的招；斷喉等要後續學到） |
| `dev-chips-dpr2.png`、`dev-hud-dpr2.png` | 同上、res 2（遊戲用的解析度） | 開發頁 |

**實機的中間與滿層層數是造的**：真打要連續幾回合才累積得到，所以在自己的無頭 Chrome 用 `Page.addScriptToEvaluateOnNewDocument` 包 `window.fetch`，
把回應裡 `team: "ally"` 且有 `skills` 的單位 `stacks` 蓋掉，再按「結束回合」＋「跳到結尾」讓下一份回應進來（伺服器與程式都不動）。
四條計量的膠囊（60／53／46／46 都和 `gaugeOuter` 一致，DOM 量到 60×22、53×22、46×22、46×22）。

Chrome、vite、靜態伺服器、`trpg serve` 都用自己記下的 PID 關掉了（5297、5298、5299、9641 交件前確認沒有在聽）。

## 6. 檢查與結束碼

| 檢查 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client build` | 0 |
| vitest（直接相關 34 檔：`render/qIcon/*`、`gearIcon`、`qi4bGearKeywords`、`dollGear`、`qi3bWiring`、`ui/entryScreen`、`statusCard`、`battleHud`、`hiddenUnitHud`、`occludedHud`、`costStatus`、`statusBadges`、`badgeCapsule`、`legacyLayout`、`narrowSkillLayout`、`floatCardRule`、`containerNameRule`、`sharedPopup`、`world/hud`、`world/panelIcons`、`battle/pr2bPractice`、`test/*`） | 0（641 個測試全過） |
| `uv run ruff check`／`ruff format --check`／`mypy`（`tests/content/test_appearance.py`） | 0／0／0 |
| `uv run pytest -q tests/content/test_appearance.py` | 0（23 passed） |

沒有改 `src/` 的 Python，沒跑 `lint-imports`；沒跑全量 `check.py` 與全量 vitest（照派工單）。

## 7. 待 PM 決定

1. **條件部件「層數達 N」實機未看**：開局起始技能沒有帶 `self_stack_at_least` 的招，只拍了開發頁。要實機看得等學到斷喉／貫心箭（或照 RG-3 的做法包 fetch 換技能卡）。
2. **`gearResolve.ts` 動了一行**（關鍵字過濾加 `!STACK_KEYWORDS.has(k)`）：派工單說 RG-4 在改紙娃娃與塔盾，這個檔是裝備外觀的驗證＋補預設、紙娃娃也會用到。改動只有一行，合併時如果 RG-4 也動到這個檔，要留意這一行。
3. **單位資訊卡（`UnitInfo.tsx`，點單位開的卡）的層數還是 `StackBadge`**：規格只寫 HUD；要不要也換計量、0 層規則要不要套（單位卡看的是別人，「你的技能」不適用）——待 PM。
4. **四種層數同時出現時 HUD 圖示列多一到兩列**：主角卡寬度固定，圖示列自動換行（1600 與 800 都是，`hud-1600-full-card.png`、`hud-800-mid.png`）。實際玩家同時有四種層數的機會不大（起始兩個關鍵字），保守不動版面。
5. **層數計量的滿層呼吸動畫**：美術第 4 節「建議但沒畫」，這次沒做（減少動態設定也就不用處理）。
6. 美術第 9 節第 8 條（說明行「條件：自身『連擊點』達 5 層」與「連擊／連擊點」兩個名稱並存）是玩法 PM 的事，前端沒動字。

## 8. commit

| commit | 內容 |
|---|---|
| `dcad6ab78` | 圓章、色、創角圖示、條件部件、裝備不帶、拿掉兩處 ART_PENDING |
| `25012c74f` | HUD 計量（`stackGauge.ts`、`StackPips.tsx`、`hudStacks`）、開發頁 hud／cond／hash、`qIconKW3.test.ts` |
| `9a5c47915` | 截圖 `docs/art/shots/KW-3/` |
| （本報告與上手筆記） | `docs/phases/PhaseKW-3報告.md`、`docs/dev/上手-前端戰鬥畫面與動畫.md` 第 154～156 點、檔案表與測試表 |
