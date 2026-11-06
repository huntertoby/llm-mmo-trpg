# Phase 5A-ART5 完成報告：5A-ART 收尾

規格：`docs/phases/Phase5計畫.md` 第 1 節表格 5A-ART5 列；細節：`docs/archive/art/5A-ART檢查.md`（第 1 節、第 5 節第 1 列）。**引擎沒有改。**

## 交付

| 項目 | 內容 | 主要檔案 |
|---|---|---|
| 戰場最小大小 | 新增 `FIELD_SIZES`（tiny 0.8、small 0.9，medium 以上不變）。`resolveCreature` 多一個 `field` 選項，戰場（`creatureOf`）才會開；樣張頁和其他畫面還是用 `SIZES`。精英 ×1.15 照乘，頭目不乘。幼蜥 0.8，仍比餘燼蜥的 0.9 小 | `client/src/render/inkCreature.ts`、`unitSprite.ts` |
| 狀態列移到身體上方 | `statusRowY(cr, fieldScale)`：非浮空的異形，畫出來的高度（`-top × 大小 × 戰場縮放`）不到人形頭頂 `DOLL_HEAD_TOP`（53）的 90% 時，圖示中心 ＝ 身體最高點 − 圖示/2 − 1。<br>位置不比原位 `ROW_Y_FEET` 低；往上不超過 `UNIT_HEADROOM`，也不蓋到上一排的 HP 條，兩個上限取比較低的那個。<br>人形、浮空的（晶靈、霧魅、飛禽）、傀儡維持原位。HP 條、代號圓、召喚徽章都沒有動 | `unitSprite.ts`、`inkDoll.ts`（匯出 `DOLL_HEAD_TOP`）、`inkCreature.ts`（`bodyTop`） |
| 道童 | `DollLook` 新增兩個欄位：`main_glow`（杖頭光色，hex）、`scale`（人形在戰場上的大小，0.5～1.5）。<br>青霧道童設成 `main_glow: '#b6f0a0'`（樣張的色）、`scale: 0.9`。<br>前端：`GearItem.glow`；圖騰杖與一般杖都畫同心光暈，並用這個色畫杖頭圓珠；附魔元素仍然優先。紙娃娃和人形詞綴特效都乘上 `scale`，精英倍率照乘 | `src/trpg/content/battle.py`、`content/units/sect_acolyte.yaml`、`client/src/render/appearance.ts`、`inkGear.ts`、`inkWeapons.ts`、`unitSprite.ts`；已重產 OpenAPI、`schema.d.ts`、`unitDolls.json` |
| 測試 | vitest `art5.test.ts`（9 項）：最小大小、精英照乘、狀態列（矮異形公式與熔核不被蓋住、人形、浮空與傀儡原位、碰到上限的高異形、扁平異形不會往下掉）、道童資料與綠光有畫出來。另外把 `inkCreature.test.ts` 的幼蜥戰場大小改成 0.8 | `client/src/render/art5.test.ts` |

異形資料照舊放在 `doll.creature`，格式沒有改。

## 檢查（已合併 main，含 5F-3c）

| 項目 | 結果 |
|---|---|
| ruff check、ruff format --check、mypy（1220 檔）、lint-imports（13 契約） | 全過 |
| pytest `tests/content tests/api tests/narrative`（-n 8） | 2995 通過 |
| vitest | 145 檔、1344 項全過 |
| `pnpm build` | 通過 |
| swamp 種子 7 重播 | 通過（88 動作、313 事件） |

## 瀏覽器驗證

- 伺服器用 8280 埠，是我自己啟動的，驗完已停。用自己的分頁 tab-21，驗完已關分頁，視窗大小也還原了。開局前先 `localStorage.clear()`。
- 內容用 scratchpad 的副本，repo 的 content 沒有動。副本裡把 `open_plain` 的敵人換成熔爐母獸、`test_whelp`（餘燼蜥改成 tiny，模擬幼蜥）、青霧道童、餘燼蜥。母獸開戰後真的召喚出一隻餘燼幼蜥，召喚物也一起看到了。
- 800×600（地圖放大到 300% 看細節）：
  - 熔爐母獸：腹部熔核露出來，狀態圖示浮在背上。
  - 餘燼幼蜥（召喚物，有回合數徽章）和 tiny 的測試幼蜥：都看得出是蜥蜴，狀態圖示在背上。
  - 道童：圖騰杖頭有綠色圓珠和淡綠光暈，身形比其他人形小一號。
- 1600×900 也看了一次（自動縮放和「填滿」各一次）。
- `__layoutSmoke.scan()`：800×600 和 1600×900 都回 `[]`。

## 待 PM 決定

1. **「比人形矮」的門檻**：檢查文件寫「傀儡這類和人一樣高的，維持原位」，但傀儡最高點 49 比人形頭頂 53 還矮。所以我把門檻定成「不到人形頭頂的 90%」，差 10% 以內都當作一樣高（傀儡是 92%）。浮空的身形（晶靈、霧魅、飛禽）一律維持原位。
2. **多加了一個上限：不蓋到上一排的 HP 條**：只用 `UNIT_HEADROOM` 的話，犬狼、熊、晶塔、蛇這類中等高度的異形，狀態圖示會壓到上一排單位的 HP 條，違反檢查第 1 節的驗收項目。所以我多加了這個上限，和頭頂預留一起取比較低的位置。結果是這幾種異形的圖示落在身體上半部，比原位高、比頭頂低。這個上限是照同高的格子算的；上一排格子比較高時沒有特別處理。
3. **道童還是畫圖騰杖**：樣張畫的是一般短杖。但道童的武器是 `totem_staff`，武器外觀本來就是圖騰杖，所以我沒有改形制，只加了綠光和光暈。要改成短杖的話，得再加一個 `main_form` 欄位。
4. **新欄位 `DollLook.main_glow`、`DollLook.scale`**：都是有預設值的純顯示資料，`LOG_FORMAT` 沒有升（理由和 5A-ART 報告的待決第 2 項相同）。`scale` 是浮點數（0.5～1.5），只用在前端顯示。
5. **`+N` 角標**：狀態列有 3 個以上的狀態時，第 2 個圖示右上角的「+N」圓會比圖示上緣再高約 2.5px。上限只算了圖示本身，沒有把它算進去。
