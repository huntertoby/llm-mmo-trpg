# Phase RG-8（美術 RG-5／RG-6 驗收可修＋RG 第二批核對）完成報告

依據：開發 PM 交接 (e3l)、(e3m)；`docs/art/RG-5驗收.md`、`docs/art/RG-6驗收.md` 末節「美術 PM 裁定」；`docs/玩法PM交接.md` 4.1.5、4.1.7 第 2 點；`docs/design/08-裝備.md` 8.11。
段名：派工時叫「RG-4」，因為 `PhaseRG-4報告.md`、`docs/art/shots/RG-4/` 已存在，開發 PM 更正為 **RG-8**；RG-4 的檔案一個都沒動。

## 0. 先說結論

派工的第 1、2 項（美術 RG 第二批、RG-3b）**在 main 上已經做完並驗收**（`PhaseRG-4報告.md`，commit `ddd326657`～`a6e4baaf9`，開發 PM 已接受；美術 `RG-4驗收.md` 已結案）。這段 worktree 開出來時停在 `6178bcba1`（落後 main），先快轉到 `6f14e0767` 才看到 RG-5／RG-6 驗收。所以這段實際做的是第 3、4、5 項；第 1、2 項只核對、不重做。

## 1. 逐條驗收

| # | 項目 | 結果 | 證據 |
|---|---|---|---|
| 1 | 美術 RG 第二批（碑盾、立殼、暮色對峙、`enemy_only`、`isTowerLike`、`emblem`、單挑按鈕、鍛疤、異形交叉） | **已在 main**，核對過 | `FormDef.enemy_only`（`src/trpg/content/appearance.py:74`）、`isTowerLike(` 10 處呼叫、`QItem.emblem`（`qCore.ts:25`）、`render/duelArt.ts`。**注意**：「大盾不開放給玩家」已被 RG-5（玩法 PM 4.1.5、#163）改成「開放、只配塔盾」，`appearance.yaml` 兩款帶 `offhands: [tower_shield]`；這段照 main 現況，沒有改回 |
| 2 | RG-3b「被擋下」讀 `lock_intercepted` | **已在 main**，核對過 | `client/src/battle/feedback.ts` 的 `interceptSpots`（RG-4 報告第 1 節） |
| 3 | K-1：玩家看得到「雲紋碑盾」「熔殼塔盾」 | **過** | 名稱定案位置：`docs/玩法PM交接.md` 4.1.5 第 1 點（定字）、4.1.7 第 2 點（「維持物品名『塔盾』，『雲紋碑盾』『熔殼塔盾』當外觀形制名（圖示說明、物品卡副標）」）、`08-裝備.md` 8.11。名字本來就在 content（`content/equipment/appearance.yaml` 的 `name_zh` → `gearAppearance.json` 的 `zh`），**content 不用改**。前端：`gearResolve.signatureFormZh`（只有帶 `offhands` 的形制回名字）；物品卡副標 `itemSubtitle` 用形制名取代副手種類（「副手・稀有・Lv5・熔殼塔盾」，照美術建議）；背包格說明 `cellHint`（也是 `aria-label`）「稀有塔盾（5 級）・熔殼塔盾・裝備」；穿戴欄浮動卡標題吃 `itemSubtitle`，自動變成「稀有塔盾（稀有・Lv5・雲紋碑盾）」。物品名不動。截圖 01～05（實機） |
| 4 | 開發頁北坡狼王照實機外觀 | **過** | `dev/duelGallery.tsx`：`WOLF` 預設＝`unitDolls.json` 的 `mist_wolf.creature`（沒有 `size: large`、`scar`），`&wolf=sample` 退回樣張大狼。遊戲資料沒改。截圖 06～09 |
| 5 | 同節其他美術裁定 | **核對過，不用改程式** | RG-5 待決 2「鋼＋冰凍盾邊同鋼」：遊戲 `sectPalOf` 早就用混元素前的本色判斷，開發頁 `rg5-shield-gallery?mode=pal` 實跑 `sect_great steel+frozen rim:#626e7c`＝`steel rim:#626e7c`，`rg5PlayerShield.test.ts` 第 73 行也鎖了（截圖 10）；文件那格美術 PM 已改。待決 1（混色 45%／40% 照現行）、4（墨線畫風之後補 `inkOffhand`）、5（圓章 20 殼縫）、6（K3 舊剪影之後跟 OCL 一起改）、RG-6 待決 2（雙匕首剪影）：都是「接受、不做」或「之後再做」，不需要程式 |
| — | 浮動卡流程實測 | **過** | 實機 1600×900、800×600：背包格 `Hint`、穿戴欄 `PartTip`（共用浮動卡）都完整在視窗內、不被面板裁掉（截圖 01～03、05） |

### 1.1 開發頁指紋（無頭 Chrome `--disable-gpu`，`/dev/duel-gallery.html`）

| 查詢 | 結果 |
|---|---|
| `?mode=fp&wolf=sample` | 16 個指紋和 RG-6 驗收第 6 條**逐字相同**（`d457db52 82490307 5b3b977a c1bcc021 / 58791a6a 37135beb 325d5858 465c85c6 / 2467ef9e af5ee84f f655ace2 b73ab191 / 101518ec e7f17e15 c567ceb0 81ad3816`） |
| `?mode=fp`（預設＝實機狼） | 只有狼王 4 個變：dev `5ba210c5`／`74b40347`、game `b8a30341`／`c8c34ddd`（res 1／2）；其他 12 個不變 |
| `?mode=diff` | 狼王 dpr1 210、dpr2 582，`unexplained=0`；`DUEL TOTAL 7151`、`BEASTCLAW TOTAL 0`（和 RG-4／RG-6 相同，差都在交叉武器的已知顏色差） |
| `?mode=weapons` 整組移量表 | 實機狼 res 1、2 都 `same=9/9`（遊戲＝樣張），9 種主手全部「不動」；熊、蛇、熔核領主的列和改前相同。這就是美術說的「實機照小狼由 `groupFit` 自算」 |

## 2. 改了什麼

| 檔 | 內容 |
|---|---|
| `client/src/render/gearResolve.ts` | `signatureFormZh(look)`；`KindEntry.forms` 型別加 `offhands?` |
| `client/src/run/gearOffer.ts` | `itemSubtitle`：副手有形制名時用形制名 |
| `client/src/world/bagGrid.ts`、`BagScreen.tsx` | `cellHint(row, formZh)`；背包格的 `Hint` 與 `aria-label` 帶形制名 |
| `client/src/dev/duelGallery.tsx` | 狼王照實機、`&wolf=sample` |
| 測試 | `gearOffer.test.ts`（副標 5 種形制）、`panelIcons.test.ts`（格說明）、`rg5PlayerShield.test.ts`（`signatureFormZh`：只有兩款大盾有名字、不認得的回 null） |
| `docs/dev/上手-前端戰鬥畫面與動畫.md` | 第 162 點 |

沒有動：API、OpenAPI、content、`src/trpg/`、閃現與重閃面板、RG-4 的報告與截圖。

## 3. 檢查

| 檢查 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client build` | 0 |
| vitest：`rg5PlayerShield`、`gearOffer`、`panelIcons`、`qSectShield`、`floatCardRule`、`rg3Duel`、`bagScreen`、`rg4DuelArt`、`rg6DuelWeapons`、`gearIcon`、`importCycles` | 0（11 檔 128 passed） |
| Python | 沒有改 Python 與 content，沒跑（照守則 11 只跑相關） |

全量 `scripts/check.py` 未跑（照守則）。

## 4. 截圖（`docs/art/shots/RG-8/`，DPR 1、`?mute=1`、無頭 Chrome `--disable-gpu --mute-audio`，CDP 除錯埠只綁 127.0.0.1）

| 檔 | 內容 | 來源 |
|---|---|---|
| `01-bag-hint-detail-1600.jpg` | 背包選熔殼塔盾：格說明「稀有塔盾（5 級）・熔殼塔盾・裝備」、詳情副標「副手・稀有・Lv5・熔殼塔盾」、目前裝備「稀有・Lv5・雲紋碑盾」 | 實機 |
| `02-worn-tip-1600.jpg` | 穿戴欄副手浮動卡「稀有塔盾（稀有・Lv5・雲紋碑盾）」＋塔盾、盾陣兩行 | 實機 |
| `03-bag-hint-800.jpg` | 800 格說明 | 實機 |
| `04-bag-detail-800.jpg` | 800 詳情副標 | 實機 |
| `05-worn-tip-800.jpg` | 800 穿戴欄浮動卡（完整在視窗內） | 實機 |
| `06-duel-wolf-live-1600.jpg`、`07-duel-wolf-live-800.jpg` | 遇敵卡單挑插圖，實機外觀的狼王 | 開發頁 `?mode=dialog&e=wolf` |
| `08-duel-wolf-live-x3.png`、`09-duel-wolf-sample-x3.png` | 插圖 ×3：實機狼（預設）對樣張大狼（`&wolf=sample`）；CDP clip scale 3（瀏覽器放大，不是最近鄰） | 開發頁 |
| `10-shield-rim-pal-devpage.jpg` | `rg5-shield-gallery?mode=pal`：鋼＋冰凍的盾邊 `#626e7c`＝鋼 | 開發頁 |

實機做法：`TRPG_DEV_ROUTES=1`、`TRPG_SAVE_DIR`（暫存區）、`trpg serve --port 9537`；開發模式建角（單手劍）→ 停伺服器 → 腳本用伺服器的 `generate_item(lib, Rng(seed), "offhand", "rare", 5)` 找兩件塔盾，`with_affix(…, "affix_trait_tower_formation")` 後 `model_copy(form=sect_great／molten_shell)`，寫進 `CharacterState.gear` → 重開 → `POST …/actions {kind: "equip"}` 換上碑盾。實機未看：單挑插圖的實機狼（開發頁照實機外觀畫，RG-6 驗收已實機拍過同一隻）。收尾：vite（9390）、伺服器（9537）、Chrome（9472）都用自己記的 PID 關掉，三個埠都沒在聽。

## 5. Commit

| hash | 內容 |
|---|---|
| `308549392` | K-1：物品卡副標、背包格說明顯示大盾形制名 |
| `4edccb5db` | 開發頁狼王照實機外觀 |
| （本報告的 commit） | 報告、截圖、上手筆記第 162 點 |

## 6. 待 PM 決定

1. **形制名的範圍**：只有「限定副手特性」的形制（目前就雲紋碑盾、熔殼塔盾）在副標與格說明顯示形制名；其他形制（例如鳶盾、包鐵圓盾）照原本寫副手種類或不寫。若要所有裝備都顯示形制名，是另一個 UI 決定。
2. **格說明的順序**：寫成「稀有塔盾（5 級）・熔殼塔盾・裝備」（形制名接在名字後、種類前）。玩法 PM 只說「圖示說明」，位置是我選的。
3. **詳情的特性行**仍寫「塔盾：縮放屬性…」（那是規則上的副手種類，不是外觀），沒有換成形制名。
4. **派工第 1 項「大盾這段不開放」與 main 現況不同**：RG-5 已照玩法 PM 4.1.5 開放給玩家（只配塔盾）。這段照 main，沒有改回；派工文字可能是 RG-4 時的舊稿。
5. **開發頁指紋基準換了**：之後比劍版指紋要加 `&wolf=sample`，或改記預設（實機狼）的 4 個新值；上手筆記已寫明。

## 開發 PM 裁定（2026-11-13）

- 接受。第 1、2 項（RG 第二批、RG-3b）已在 RG-4 做完並驗收，派工條目過時；只核對不重做是對的。
- 待決 1～3：照目前做法（形制名只在兩款盾兵大盾顯示；背包格說明放在名字後、種類前；特性行維持「塔盾：…」）。要不要全部裝備都顯示形制名，等美術或玩法提出再排。
- 待決 4：照 main 現況（RG-5 已依玩法 PM 決定開放玩家大盾）；派工那句是舊稿，以 main 為準。
- 待決 5：開發頁劍版指紋的新基準照上手筆記 162 點。
- 請美術 PM 複驗 `docs/art/shots/RG-8/`。
