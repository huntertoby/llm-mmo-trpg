# Phase QK-4 報告（暫停）

2026-11-07，實作 agent。專案 PM 通知暫停：美術 PM 盤點後確認異形 17 種與頭目 2 種還沒有 Q 版樣張，使用者看過補的樣張後會重寫需求。

## 做到哪

- 只讀了規格與樣張，**還沒改任何程式**（`client/` 沒有變動，沒啟動伺服器、沒拍截圖）。

## 發現

- `docs/art/sample/enemyArt.js`、`bossArt.js` 都是 C 手繪墨線（檔頭寫明沿用 `storyDoll.js` 的畫法層 `StoryDoll.H`：抖動墨線、水彩填色、暗面斜排線）。
- `docs/art/Q版回歸評估.md` 第 3 節說「舊版 `enemyArt.js` 有 Q 版的 17 種身形（`shots/misc/enemies.png` 下半那套）」，但 git 歷史裡 `enemyArt.js` 只有 3 個 commit（165ec238 起），從第一版就是 C 墨線；`enemies.png` 下半也是同一份 C 程式在小倍率下的渲染，只是小圖看不出排線。**沒有 Q 版的異形點列可搬。**
- 身形數：`enemyArt.js` 的 `BODIES` 是 14 種（飛禽分鳥／蝠、爬蟲分甲蟲／蜘蛛，共 16 款），規格寫 17 種，差 1 種待美術 PM 對清單。
- `summonArt.js` 的非人形召喚物也走同一套異形畫法（`enemyArt.js`）或紙娃娃，沒有獨立的 Q 版樣張。
- client 端現況：`client/src/render/inkCreature.ts` 已逐點移植 `enemyArt.js`（點列、材質、特徵、詞綴、精英、頭目外光都在）；頭目沒有專屬畫法檔，`bossArt.js` 尚未移植。

## 之後可以沿用

- 若 Q 版異形沿用現有點列（只換畫法），改法很小：`inkCreature.ts` 的 `mass`／`limb` 改成無抖動純色填色、去掉暗面排線，整隻再用 `qDoll.js` `stamp` 的圓盤膨脹剪影外框（`OUT #16121a`、半徑 1.3 單位）；`creaturePose.ts`、`resolveCreature`、`creatureKey`、精英金環、詞綴、外光、白閃流程都不用動。
- 頭目照 `bossArt.js` 的「部件＋掛點」結構移植時，殼片／浮晶的雜湊相位寫法可直接搬（已確定性）。

## 待 PM 決定

1. Q 版異形是「現有點列＋Q 畫法」，還是美術 PM 重畫身形？
2. 材質表面（熔岩裂縫、源晶切面、青石刻符、木紋）在「材質改純色」下要不要保留成平塗線條。
3. 「17 種」的第 17 種是哪一個。
