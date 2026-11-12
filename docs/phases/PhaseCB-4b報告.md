# Phase CB-4b 報告｜灰燼之心東西向衝撞星爆內收到目標格

> 實作者 2026-11-12。依據美術驗收 `docs/art/QI-2c-2d-3a-3b驗收.md` 第 5.3 節（決定點 3b）；前段 `docs/phases/PhaseCB-4計畫.md`、`PhaseCB-4報告.md`。起點 main `f07a0e19`（`git merge --ff-only main` 成功）。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 1 錨點修正 | `client/src/render/qBoss.ts`：新增 `bossSameRowFx(who, clip, fx)` 與 `BOSS_EW_TARGET_X`（＝52 ／（`DOLL_SCALE` × `BOSS_FIELD_SCALE`）≈ 30.66 單位＝戰場上 48 px，東西向相鄰目標格中心）；`BossActOpt.sameRow`；`drawBossFrame` 沒有轉向（東西向）時傳 `sameRow: true`，`bossAct` 畫進身體貼圖前先過 `bossSameRowFx`。只改灰燼之心 `ram`：星爆 x → 目標格中心（水平偏移 0、y／r 不動）；塵土 x → 目標格中心 ＋（原 x − 52）＝往施放者側 8 單位（12.52 px）。`bossPlan`（命中對齊、轉向的 `bossPoseFx`）沒改，所以南北、斜向、命中時間都不變 | `dbdd25f1` |
| 2 測試 | `client/src/render/cb4FxAnchor.test.ts`：新 describe「CB-4b 灰燼之心東西向衝撞」5 項；改 1 條既有斷言（第 3 節） | `dbdd25f1` |
| 3 開發頁 | `client/src/dev/skillGallery.ts` 加案例 `ahRamW`（東西向、目標在西，和 `ahRamE` 成對）＋檔頭說明 | `41b61a1a` |
| 截圖 | `docs/art/shots/cb4/cb4b-1`～`cb4b-4`（4 張） | `41b61a1a` |
| 4 報告、上手筆記 | 本檔；`docs/dev/上手-前端戰鬥畫面與動畫.md` 第二節「特效落點」、開發入口（`ahRamW`）、第四節第 3 點、第五節測試表 | 本檔的 commit |

### 數值（戰場、相對目標格中心，負＝往施放者）

| | 修改前（東西向） | 修改後（東西向） | 正南北（CB-4） | 斜向（CB-4） |
|---|---|---|---|---|
| 星爆水平 | +30.3（離施放者 78.3 px，超出格邊約 6 px） | **0.0** | 0 | −3.1 |
| 星爆高度 | −24 單位（−37.6 px） | **不變** | 同 | 同 |
| 塵土水平 | +20.9（離施放者 68.9 px） | **−12.5** | 0（縱向 −7.4） | −12.5 |

## 2. 驗收逐條

1. **星爆水平 0～−3 px、高度不動（東、西各一）**：`CB-4b … 目標在東／目標在西`——灰燼之心第 1 階段 `ram` 逐格（12 格，出手 3 格有星爆、塵土），用戰場的 `creatureOffsetPx`（含鏡射）換成 px：星爆相對目標格中心 −3 ≤ Δ ≤ 0（上限寫 1e-9，只容浮點誤差；實際 Δ ＝ 0）；y 與 r 和 `bossPlan` 原值 `toBe` 相同；塵土 −13 ≤ Δ ≤ −12（實際 −12.52）。**通過**。
2. **四個方向一致**：`四個方向一致`——東西向塵土水平＝斜向塵土（剪切）的水平（`toBeCloseTo` 9 位）；東西向星爆水平＝正南北的（0），且大於斜向的（−3.13）；星爆 y ＝ −24。**通過**。
3. **錨點不變**：`目標格中心換算`——`BOSS_EW_TARGET_X` 單位＝48 px；「相鄰目標」點仍在 81.41 px。CB-4 錨點表（東西向 32 列＝修改前）沒動、照過。**通過**。
4. **其他頭目／異形東西向畫面不變**（證據）：`其他頭目片段的東西向畫面與修改前逐筆相同`——`drawBossFrame`（沒有轉向）對兩個頭目全部片段 × 全部階段 × 12 格的假畫布紀錄取 FNV 雜湊，和修改前（`f07a0e19`，同一段程式在改動前跑出來的值）比：除灰燼之心 `ram` 出手 3 格（f6～f8）外**全部相同**（碎晶之主 `swing` 的白弧也相同）；`ram` 的其他 9 格相同、f6～f8 不同。一般異形不經過 `qBoss`（`inkCreature.drawCreature` 非頭目路徑沒改，`git diff` 只動 `qBoss.ts`）。另外 `creaturePose.test.ts`、`inkDollSnapshot.test.ts` 的雜湊快照沒有變（`__snapshots__` 沒有改動，沒有重產）。**通過**。
5. **範圍外不動**：碎晶之主白弧、硫煙獸斜向星爆、頭目擋住後排目標都沒改（`bossSameRowFx` 對 `sl` 與其他片段原樣回傳同一個陣列，測試鎖住；轉向路徑 `bossPoseFx` 沒改）。**通過**。
6. **交件前三個結束碼**（分開記）：`corepack pnpm -C client typecheck` → **0**；`corepack pnpm -C client test` → **0**（`Test Files 299 passed (299)`、`Tests 3815 passed (3815)`，比 CB-4 多 5 項）；`corepack pnpm -C client build` → **0**（只有既有的 chunk 大小警告）。
7. 開發中跑的相關測試：`cb4FxAnchor`、`cb3cFxTurn`、`qBoss`、`qBoss4b`、`qk9Boss`、`creaturePose`、`inkDollSnapshot`、`art5`、`test/importCycles` → 9 檔 194 項全過（`qBoss.ts` 新匯入 `paperdoll` 沒有造成循環）。
8. 截圖：第 4 節，東、西各一張（另附各一張 2 倍特寫）。

## 3. 改寫的既有斷言（舊 → 新）

| # | 位置 | 舊 | 新 | 理由／舊程式下 |
|---|---|---|---|---|
| 1 | `cb4FxAnchor.test.ts`「CB-4 頭目身體貼圖」，沒轉向那一份的期望紀錄 | 沒轉向＝身體＋`drawCreatureFx(bossPlan(...).fx)`＋restore | 沒轉向＝身體＋`drawCreatureFx(bossSameRowFx(who, clip, bossPlan(...).fx))`＋restore；另加：碎晶之主 `bossSameRowFx` 回傳**同一個陣列**（`toBe`），灰燼之心 `ram` 有特效的格 `not.toEqual` 原值 | 本段有意改變東西向的特效位置；碎晶之主的期望值實質不變（同一個陣列），身體那幾筆、「有轉向＝少了特效」的比對一字未改，沒有放寬。舊程式下 `ashen_heart ram` 這項**失敗** |

沒有刪除斷言、沒有放寬容差、沒有重產快照。

## 4. 新斷言在舊程式下會失敗

把 `qBoss.ts` 換回 `f07a0e19`（另補兩行只為了讓測試載得進來：`BOSS_EW_TARGET_X` 常數與「原樣回傳」的 `bossSameRowFx`，等於舊行為），跑 `cb4FxAnchor.test.ts`：**5 失敗、97 通過**，跑完換回新檔（`git diff` 確認）。

| 測試 | 舊程式下 |
|---|---|
| CB-4b 目標在東 | fail（星爆 +30.3、塵土 +20.9） |
| CB-4b 目標在西 | fail（同上，鏡射） |
| CB-4b 四個方向一致 | fail |
| CB-4b 其他頭目片段不變／`ram` 出手 3 格改變 | fail（`ram` f6～f8 和修改前相同） |
| CB-4 頭目身體貼圖 `ashen_heart ram`（改寫的第 1 條） | fail |
| CB-4b 目標格中心換算 | pass（定義與「錨點不變」斷言，本來就該過） |

## 5. 截圖（`docs/art/shots/cb4/`，4 張、最大 88 KB）

開發頁 `http://127.0.0.1:5300/dev/skill-gallery.html?mute=1&sheet=1&rows=1&case=<案例>&at=…&crop=…#cb2b`（正式 `playbackPlan → frameOps → BattleRenderer`），t＝出招片段開始後的毫秒；無頭 Chrome `--mute-audio`，CDP `toDataURL('image/jpeg', 0.8)`。

| 檔 | 內容 |
|---|---|
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\cb4b-1-ah-ram-east.jpg` | 重拍截圖 8：`ahRamE`（目標在東），417／500／583／667 ms：星爆在目標頭上、目標格內；塵土在目標腳邊靠頭目側 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\cb4b-2-ah-ram-west.jpg` | `ahRamW`（目標在西），同上四格 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\cb4b-3-ah-ram-east-closeup.jpg` | 東向 2 倍格（`&cell=104`），417／500／583 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\cb4b-4-ah-ram-west-closeup.jpg` | 西向 2 倍格，417／500／583 |

對照修改前：`docs/art/shots/cb4/8-ah-ram-east.jpg`（星爆在目標背後、超出格邊）。

## 6. 實機未看

- 實戰沒有直接拍：灰燼之心第 1 階段貼身東西向普攻改用開發頁畫（同正式播放路徑）。
- 減少動態沒拍：`reduce` 時 `bossPlan` 仍給同樣的特效，內收照樣套用（路徑沒分岔）。

## 7. 自己啟動的程序

| 程序 | PID | 結束 |
|---|---|---|
| vite（埠 5300，`--strictPort --host 127.0.0.1`） | node 44156 | `taskkill /PID 44156 /T /F` |
| 無頭 Chrome（CDP 8148，`--mute-audio`，`--user-data-dir` 在 scratchpad） | 17824（含子程序 7 個） | `taskkill /PID 17824 /T /F` |

結束後 `netstat` 查 5300、8148 都沒有在聽。沒有啟動 `trpg serve`。沒有新增複雜度 noqa／eslint-disable。

## 8. 待 PM 決定

1. **星爆水平取 0（不取 −3.1）**：規格容許 0～−3 px。若照斜向的剪切（「相鄰目標」點對到目標格中心、橫向距離照舊），星爆會在 −3.13 px，超出 3 px 上限 0.13；所以星爆（接觸點）水平直接放在目標格中心（＝正南北的 0），塵土照剪切（−12.5，＝斜向）。兩者間距因此從原本 6 單位（9.4 px）變成 8 單位（12.5 px）。要改成 −3 也只是改 `bossSameRowFx` 一行，請美術 PM 看截圖 `cb4b-1`～`4` 判斷。
2. **只動東西向的身體貼圖路徑**：沒有改 `bossPlan` 的原始數值（改了會連帶動到南北、斜向的轉向結果與樣張頁 `creature-gallery`）；樣張頁（`bossAct` 直接呼叫、沒有 `sameRow`）照舊畫在 x ＝ 50。
3. **隔一格（射程 ＞ 1）的東西向衝撞**：內收的目標是「相鄰格中心」，和 CB-4 Q6（隔一格的近戰錨點仍放相鄰格）一致；第 1 階段衝撞目前只有貼身的情況。
