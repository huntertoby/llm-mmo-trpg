# Phase 3-10 報告｜試玩回饋：慢速、版面大小設定、推不動的原因

## 1. 完成項目與 commit

| 項目 | 內容 |
|---|---|
| 慢速 | `PlaySpeed` 加 `slow`；`SLOW_FACTOR = 2` 一處常數，動畫、地圖回饋、AI／主角停頓都套用；順序「慢／正常／快／略過」 |
| 推不動的原因 | 新增 `battle/pushReasons.ts`：依 `interact_options` 補「推動物件」。全不合法時按鈕灰色（滑過顯示 title、點擊在 `NoticeBanner` 顯示原因）；有合法時，選取模式中點到推不動的相鄰物件也顯示原因 |
| 版面可調 | 新增 `battle/layoutPrefs.ts`（數值、上下限、`localStorage`）、`ui/ResizeHandle.tsx`（拖曳分隔線）、`ui/LayoutPanel.tsx`（頂端列「版面」面板）；地圖縮放（＋／－／填滿、Ctrl＋滾輪、捲軸與滑鼠中鍵拖曳平移） |
| 後端小修 | `interact_options.to_pos` 改為可為 `null`（見 5.1）；重新產生 `openapi.json`／`schema.d.ts` |

Commit（由舊到新）：
1. `feat: add slow playback speed (2x normal time)`
2. `feat: show why a push is blocked (greyed push button and tile hint)`
3. `feat: adjustable battle layout (drag handles, map zoom, layout panel)`
4. `fix: interact_options to_pos is null when an object would leave the map (was HTTP 500)`
5. 本報告與截圖

## 2. 驗收條件逐條

1. 四種播放速度，慢速為正常的 2 倍：通過。`playback.test.ts`「has four speeds in order, and slow takes twice the normal time」（順序、移動動畫總時間 2 倍、停頓總和剛好 2 倍、地圖回饋 2 倍）。
2. 拖曳分隔線、縮放（含平移後點格）、設定面板與重設、重新整理後保留：通過。
   - vitest：`layoutPrefs.test.ts`（上下限不讓地圖小於一半、拖曳方向與夾限、視窗縮小時收回、縮放步進、放大且平移後 `clientToTile` 正確、縮小時正確、`localStorage` 往返／壞資料／不可用）。
   - 瀏覽器實測（1400×800，狹窄長廊）：拖曳右欄 300→402、底部列 166→204、主角卡 300→366；＋放大到 266% 出現捲軸、捲動後滑過油桶格高亮正確；重新整理後版面與縮放仍在。截圖見第 6 節。
3. 推不動時按鈕灰色並顯示原因：通過。`pushReasons.test.ts`（全不合法加灰色按鈕與原因、補前綴、合法時附 `blockedObjects` 且點格得原因、順序）。瀏覽器實測：狹窄長廊 seed 1，把木箱推到左緣後主角站在它右邊，「推動物件」灰色，點擊顯示「推不動：木箱會被推出地圖」。
4. `pnpm build`、`check.py` 全過：通過（`scripts/check.py` 全部通過，vitest 314 項；`corepack pnpm -C client build` 成功）。

## 3. 複雜度 noqa

無新增、無移除。

## 4. 修改既有測試期望值

無。新增：`playback.test.ts` 一項、`pushReasons.test.ts`、`layoutPrefs.test.ts`、`tests/api/test_shove_aside.py` 一項（地圖邊緣）。

## 5. 待 PM 決定

1. 【後端，超出「只改前端」】實測發現：物件貼著地圖左／上緣、主角在其內側時，推的目的格座標為負，`presenter._offset` 建立 `Pos` 失敗，`GET/POST /battles/...` 整個回 HTTP 500（戰鬥卡死、前端顯示「伺服器錯誤」）。這很可能就是「推不動」回饋的真正來源之一。我採最小修法：`InteractOptionOut.to_pos` 改 `Pos | None`（出界為 `null`，原註解本來就寫「可能在地圖外」），前端撥開箭頭在 `null` 時不顯示箭頭。請 PM 確認；右／下緣出界仍給合法 `Pos`（座標超出地圖寬高但不為負），行為不變。
2. 使用者說「面向右邊、箱子在下面推不動」：推動不需面向（方向是主角到物件），所以那次多半是被擋原因（含上面的 500）；現在原因會直接顯示。若 PM 認為仍有「面向」的預期，需另議。
3. 窄螢幕（< 1100px）版面是固定版型：窄欄收合、底部列高與主角卡寬不可調（面板內三個滑桿灰掉並註明）；只有地圖縮放有效。
4. 上限採「窄欄寬 ≤ 視窗寬一半 − 22px、底部列高 ≤ 視窗高一半 − 56px」（頂端列與間距為估計值）；下限 200／120／主角卡 200–520。視窗縮小時以夾限後的值顯示（儲存值不變）。
5. 手動縮放範圍 40%–300%，每次 ×1.25；「自動填滿」維持原本 50%–200% 夾限。縮放時以捲動區中心為錨，不是以滑鼠為中心。
6. 平移：捲軸與滾輪捲動，另支援滑鼠中鍵拖曳（右鍵已是取消選取）；沒做觸控拖曳。
7. 分隔線雙擊還原該項預設；方向鍵每次 16px。
8. 慢速的「戰鬥開始」橫幅時間（`BANNER_MS`）維持 1 秒，未加倍。
9. 推動物件灰色時，面板（`AsideHelp`）不變；撥開物件按鈕與推動物件是兩個獨立按鈕，行為不變。
10. 截圖為瀏覽器窗格截圖（縮放後 800 像素寬），非全解析度。

## 6. 代表性輸出

截圖（`docs/phases/img/`）：`3-10-push-blocked.png`（灰色按鈕與原因提示）、`3-10-layout-panel.png`（版面面板）、`3-10-resized-columns.png`（拖曳後的欄寬）、`3-10-zoom-in.png`（266% 與捲軸）、`3-10-persist-after-reload.png`（重新整理後保留）。

`localStorage["trpg.battleLayout"]` 範例：`{"sideWidth":402,"bottomHeight":204,"heroWidth":366,"zoom":2.66}`
