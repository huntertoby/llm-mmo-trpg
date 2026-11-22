# Phase E4b 報告｜觸發圖示移植（格擋時、你讓別人位移時）＋倒地說明框懸掛縮排

> 規格 `docs/phases/PhaseE4b計畫.md`；美術移植需求 `docs/art/E4-觸發圖示-美術.md` 第 6、7 節；美術 E4 驗收 `docs/art/E4驗收.md` 小修 1。基準 main `07b58f4c4`。只改前端（`client/`）、截圖與本報告；`src/`、`content/`、`config/`、`docs/design/` 都沒動。

## 1. Commit

| 項目 | Commit |
|---|---|
| 1 兩個觸發圖示（`parts.ts`） | `35a655481` |
| 2 測試（3 個既有檔＋新的 `arE4Trig.test.ts`） | `d7b14ad23` |
| 3 倒地說明框懸掛縮排 | `d8bc83bc9` |
| 4 截圖＋開發頁 | `452b910d0` |
| 報告 | （本檔） |

## 2. 做了什麼

### 2.1 觸發圖示（美術 6.1 第 1～3 項）
- `client/src/render/qIcon/parts.ts`：`TRIG` 在 `on_ap_spent_all` 後面加 `on_block`（格擋時）、`on_displace`（你讓別人位移時），前面順序不動；`zh`、`topic` 照 `e4Triggers.js` 的 `TRIG` 原字。
- 畫法 `blockArt`、`displaceArt` 從 `e4Triggers.js` 逐行搬：盾用 `QS.ACT.shield.d(q, o, QS.ACT.shield.def as Tint)`（同 `shieldAt` 寫法，不縮不移）、`PI * 2` 換成 `TAU`；`at`、`bust`、`burstStar`、`bladeSword`、`halo`、`ci`、`f`、`rr`、`CREAM`、`ENEMY`、`OUT` 都用檔內既有的同名同值。沒有新色。
- `TRIG_ALIAS` 拿掉 `on_displace: "on_collision"`、`on_block: "hit_by_melee"`，行尾註解改成「E4：格擋時、你讓別人位移時換成專屬圖樣（TRIG 最後），拿掉暫借」。

### 2.2 測試（美術 6.1 第 4～6 項）
- `qIconSkills.test.ts`：部件計數觸發 26 → 28、暫代 9 → 7（it 標題與註解一起改）；`TRIG_ALIAS` 長度 9 → 7。
- `qIconQi2d.test.ts`：`ADDED_PARTS` 加 `trigger:on_block`、`trigger:on_displace`；其他部件基準雜湊沒重錄。
- `arAp2Borrow.test.ts`：原「TRIG 最後一個是 `on_ap_spent_all`」改成驗 TRIG 最後三個依序是 `on_ap_spent_all`、`on_block`、`on_displace`。
- 新增 `client/src/render/arE4Trig.test.ts`（照 6.1 第 6 項的第二種寫法另加）：`TRIG_ALIAS` 沒有這兩個、`zh` 和名詞表 `name_zh` 一樣、格擋時 tiny 沒有劍（沒有劍柄色）、位移 tiny 和一般的呼叫紀錄不同，兩個都和舊的暫借圖不同。

### 2.3 倒地說明框懸掛縮排（E4 驗收小修 1）
- `TipPart` 加選填的 `bullet`；`entryTipParts` 對只列規則的項目（倒地）回傳 `bullet: true`。
- `PartTip` 對 `bullet` 的段落加 class `part-tip-bullet`；`float-card.css` 加 `.part-tip-text.part-tip-bullet { padding-left: 1em; text-indent: -1em; }`，和 E2 小修 2 的加註換行同一種做法（「・」是全形、1em）。
- 6 行字沒改。`tipPartsE4.test.ts` 加一則：倒地每段都是 bullet、燃燒沒有，class 與 CSS 都在。
- 沒有新的彈出卡片；倒地說明框是原本的 `PartTip`（共用浮動卡 `FloatCard`）。

## 3. 檢查

| 檢查 | 結束碼 |
|---|---|
| `pnpm -C client exec tsc --noEmit`（每個 commit 前） | 0 |
| vitest 相關檔（`src/render`、`src/ui`、`rg3Marks`、`statusCard`、`panelIcons`） | 0 |
| `uv run python scripts/check.py --all` | 0（開發 PM 回「可以跑」後跑；全部通過，已寫通過戳記） |
| 前端 build（`pnpm -C client build`） | 0 |

## 4. 截圖（`docs/art/shots/e4b/`，交美術 PM）

開發頁 `client/dev/e4b-gallery.html`（`client/src/dev/e4bGallery.tsx`，網址加 `?mute=1`）用正式元件畫：技能卡是 `SkillCardView`（左＝技能列浮動卡的緊湊版、右＝一般版，都展開詳細），倒地是正式的主角卡 `Hud → StatusBadge → PartTip`，點一下狀態圖示釘住。無頭 Chrome（`--mute-audio`、DPR 1）拍；jpg 品質 80，PNG 只用在真 1 倍與最近鄰。

| 檔 | 內容 |
|---|---|
| `docs/art/shots/e4b/e4b_on_block_card_1600x900.jpg` | 被動「格擋時（只算近戰）」的技能卡：組裝列第一格換成新圖（大盾＋撞擊星＋彈開的劍），「觸發時機：格擋時（只算近戰）」 |
| `docs/art/shots/e4b/e4b_on_displace_card_1600x900.jpg` | 被動「你讓別人位移時」的技能卡：組裝列第一格換成新圖（紅人形＋影子圈＋速度線） |
| `docs/art/shots/e4b/e4b_trig_row_true1x_800x600.png` | 組裝列圓片 30／26／18 真 1 倍（`QP.chipCanvas` res 1）；每組左＝移植前暫借、右＝新 |
| `docs/art/shots/e4b/e4b_trig_row_x6_800x1000.png` | 同上 ×6 最近鄰（畫布 `imageSmoothingEnabled=false`；抽查 4 個圓片，每個 6×6 區塊都是純色，比例 100%） |
| `docs/art/shots/e4b/e4b_prone_tip_800x600.jpg` | 倒地的說明框：分點換行後第二行對齊「・」後面的字（「反擊）。」「劣勢。」「隊友扶起。」等） |

## 5. 待 PM 決定

1. **技能卡截圖用開發頁拍，不是實機**：E4 的實機截圖要靠起 `trpg serve`、用頁面腳本換掉 `POST /api/battles` 加工坊的測試被動。這次只換了圖示，所以改成在開發頁用正式的 `SkillCardView` 畫兩張假卡（名稱「盾後蓄勢」「推後護身」、效果是護盾，只給截圖用）。卡上的組裝列和實機同一個元件。要實機的話請另外指示。
2. **倒地說明框也是開發頁**（正式的 `Hud` 元件，主角身上加倒地狀態），同 AR-X10 的開發頁做法。
3. **多加一個測試檔 `arE4Trig.test.ts`**：規格寫「改 3 個測試檔」，美術 6.1 第 6 項說可以另加一個 E4 的測試檔，我兩個都做了（既有檔改寫＋新檔）。
4. **懸掛縮排只套在「只列規則」的項目（目前只有倒地）**：`actionInfo.ts`、`stackInfo.ts` 等其他用「・」的說明是另一種說明卡（`Hint`），沒動。

## 開發 PM 裁定（2026-11-22）

**驗收通過**，合併為 `dc0086a21`。tsc、vitest、`check.py --all`、build 都是 0。

- 第 1、2 點：在開發頁用正式元件拍，接受（同 AR-X10 做法）。美術 PM 要實機截圖時再補。
- 第 3 點：多加的 `arE4Trig.test.ts` 接受。
- 第 4 點：懸掛縮排只套倒地，接受。其他用「・」的說明要不要跟進，轉美術 PM 看。
