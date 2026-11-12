# Phase R1e 報告：`client/src/render/BattleRenderer.ts` 按職責拆成子模組

依據：`docs/phases/整理提案-程式.md` 2.2 節 R1（BattleRenderer）。分支 `dev/r1e`。做法照 R1a～R1d 的精神：純搬移、呼叫端 import 不改、以既有測試與實機畫面守行為。

## 做法：同一個類別拆成一條繼承鏈

`BattleRenderer` 的方法幾乎都讀寫同一批私有狀態（圖層、`unitSprites`／`unitDrawOf`、效果時鐘、`idle`、`art`…），改成「自由函式 ＋ host 物件」等於重寫介面。所以改用**繼承鏈**：每一層是一個 `abstract class`，方法本文逐字不動，只把被其他層用到的成員由 `private` 改成 `protected`。

```
RendererBase → TerrainLayer → HighlightLayer → UnitLayer → FeedbackLayer → MotionLayer → SkillLayer → VfxLayer → BattleRenderer
```

呼叫方向只往上（子類別呼叫父類別），不需要任何 `abstract` 方法宣告；沒有循環匯入（`render/battle/*` 不匯入 `BattleRenderer.ts`）。

## 行數表

原檔 2,683 行 → 9 檔共 2,797 行（多出的是各檔 import、檔頭說明與 `const T = TILE_SIZE;`）。

| 檔案 | 行數 | 內容 |
|---|---|---|
| `render/BattleRenderer.ts` | 277 | 類別本體 `BattleRenderer extends VfxLayer`：建構子、`init`、`destroy`、壞掉重建（`safeRender`、WebGL context 遺失／恢復）、`setScale`／`applySize`、整場重畫 `draw`、`setBoost`、`setIdle`／`setIdleClock`、減少動態、`nextDraw`、`textureCount`；`liveRenderers`／`releaseIfLast` 等模組狀態；re-export `Highlights`、`DirectionMark`、`HEIGHT_BADGE_FONT`、`FLAME_DIM` |
| `render/battle/rendererBase.ts` | 221 | 全部欄位（原順序）、`guard`／`fail`、標記最小尺寸（`scaleMark(s)`、`scaleUnitMarks`）、抬高座標（`heightOf`、`origin`、`center`、`place`）、效果迴圈（`effectLayer`、`launch`、`ensureEffectTick`）；`DOLL_PX`、`LiftState` |
| `render/battle/terrainLayer.ts` | 392 | 地形格與崖面、區域、陷阱、符文、源泉、目標格、出口路牌、薄霧、擋視線的霧、高度徽章「▲N」、物件與可燃標記、`setFlameEmphasis`、升降續播；`surfaceHost`／`ambientHost`／`sceneryHost`；`HEIGHT_BADGE_FONT`、`FLAME_DIM` |
| `render/battle/highlightLayer.ts` | 381 | `setHighlights` 與其下：移動格、範圍、預覽、目標框、方向、攀跳、環境預告、場景物件預覽（`OVERLAY_COLORS`）、路徑提示、致命淡紅、焦點與滑過框、出口滑過、實地標記（腳印、「！」、眼睛、`tickBobs`）；`Highlights`、`DirectionMark` 型別 |
| `render/battle/unitLayer.ts` | 218 | 畫單位與剪影、HUD 掛載（`hudLayerOf`→`hudTop`、朝南三角形 `southArrowTop`）、連心虛線、換姿勢（`poseBody`／`restBody`／`poseClip`／`spinBody`）、待機、`turn`、`holdBody` |
| `render/battle/feedbackLayer.ts` | 250 | `playFeedback`、浮動字（`FloatStack` 錯開、`placeFloat` 夾在戰場內、狀態光環）、行動連線 |
| `render/battle/motionLayer.ts` | 517 | `animate`／位移片段（`clipMove`、殘影）、逐格走路 `animateWalk`／`stepLeg`／`playBeat`、進出門（`playLeave`／`playDoor`／`playArrive`）、鏡頭跟隨 `follow`、`during`／`tween` |
| `render/battle/skillLayer.ts` | 223 | `playSkill`、`weaponClassOf`、`attackFamilyOf`、作用端位置（`anchorWorld`、`creatureMouthWorld`）、時間軸片段（`rowEffect`、`rowCues`、Q 版關鍵幀） |
| `render/battle/vfxLayer.ts` | 318 | `playVfx`、受擊（異形／人形／疊白剪影）、減少動態的白閃、`reactHost`／`resultHost`、`playVictory`、`playLift` |

每檔 < 800 行。

## 純搬移的檢查

- 以腳本依原檔的類別成員切段（含前置註解），逐字搬到所屬檔；import 由原檔的 import 區塊複製、只留用到的名稱、路徑加一層 `../`。
- 比對：原檔 174 個類別成員（欄位、方法、箭頭函式欄位）把 `protected` 換回 `private` 後**全部原樣、各出現一次**在新檔；類別外的常數、介面、函式逐行都在。
- 唯二的非搬移改動：① `BattleRenderer` 建構子多一行 `super();`（衍生類別必要）；② 被其他層用到的成員 `private` → `protected`。
- 欄位初始化順序：全部一般欄位仍在 `RendererBase` 照原順序；原本就排在欄位之後的 `onContextLost`／`onContextRestored`、`reactHost`／`resultHost`、`surfaceHost`、`strides` 現在在各自的子類別初始化，仍在所有一般欄位之後，且都沒有初始化時的副作用（`reactHost` 讀的 `this.art` 已建好）。
- 公開 API 不變：`new BattleRenderer()`、所有公開方法與 `motion`、`onBroken` 欄位、匯出的 `Highlights`、`DirectionMark`、`HEIGHT_BADGE_FONT`、`FLAME_DIM`（re-export）；呼叫端 import 一行都沒改。

## 測試的改動

10 個「掃原始碼」的測試原本直接讀 `render/BattleRenderer.ts` 檢查接線字串（例如 `this.rows.attachHud(` 出現 2 次）。改法：`client/src/test/sourceScan.ts` 新增 `BATTLE_RENDERER_FILES`（9 檔，依繼承順序）與 `battleRendererSource(sources)`（各檔串成一段，缺檔丟例外）；測試裡的 `sources["render/BattleRenderer.ts"]` 改成 `battleRendererSource(sources)`，「這次動到的檔案不用 Math.random／title=」清單改成 `...BATTLE_RENDERER_FILES`。斷言內容一字未改。涉及：`ui/badgeCapsule`、`badgeFacing`、`hiddenUnitHud`、`narrowMapLayout`、`narrowSkillLayout`、`occludedHud`、`southArrow`、`statusBadges`、`summonBadges`、`render/hazardTiles` 的 `.test.ts`。

## 留在原檔的與原因

- `draw`（整場重畫的順序：地形 → 地表動畫 → 實地外觀 → 光環 → 區域 → 符文 → … → 單位 → 霧 → 環境動態）：它是各層的編排，圖層順序就寫在這裡，放在類別本體最好讀，也避免拆到某一層後要往下呼叫。
- 生命週期（`init` 的 ticker 註冊與圖層掛載順序、`destroy`、壞掉重建）與模組狀態 `liveRenderers`：和建構子同一檔才能共用模組變數，不必另外匯出可變計數。
- 沒有任何段落因為「和私有狀態糾纏太深」而留下；全部成員都已依職責歸到某一層。

## 驗收

| 項目 | 結果 |
|---|---|
| typecheck（`tsc --noEmit`） | 通過 |
| 全量 vitest（不重產快照） | 273 檔、3,293 個測試；拆前 3,293 全過。拆後 3,292 過，1 個失敗見下 |
| 快照 | `render/__snapshots__/` 的 2 個 `.snap` 沒有任何變動（`git status` 乾淨） |
| build 主 chunk | `index-*.js` 2,237,898 → 2,238,248 bytes（+350 B，類別鏈的宣告） |
| 排版煙霧檢查（正式 build、`?dev=1&anim=0.1`） | 1600×900、1040×624、800×600：各 11 PASS／1 FAIL；FAIL 都是「戰鬥：四角飾件沒有壓到內容」（主角卡左下 × 技能圖示），main 既有，拆前 1600×900 同樣 FAIL，未修 |
| 實機前後對照 | 同一種子：取消選取 → 主角從 (0,3) 走到 (2,3) → 普攻上方的敵人。拆前、拆後同一時點截圖，地圖區平均像素差 0.7～1.0（待機呼吸與 JPEG 雜訊），畫面相同：`docs/art/shots/r1e/r1e_compare_end_800.jpg`（攻擊結束）、`docs/art/shots/r1e/r1e_compare_attack_800.jpg`（攻擊飛行中） |

全量 vitest 的那 1 個失敗：`ui/badgeCapsule.test.ts`「效能：最擠的情況一個單位不到 0.5 秒」。它只量 `unitSprite.buildUnitSprite`，不載入 `BattleRenderer` 或 `render/battle/*`；單獨跑那一項通過，整檔跑時失敗，當時機器負載 11～14（10 核，另一個 agent 同時在跑）。屬計時測試受負載影響，與本段無關。

## 待 PM 決定

- `badgeCapsule.test.ts` 的 0.5 秒計時測試在機器高負載時會失敗（與本段無關）；要不要放寬門檻或標成 slow，請 PM 決定。
- 子類別的成員可見度：被其他層用到的 `private` 改成 `protected`（tsc 檢查出的最小集合），只在本層用的仍是 `private`。若想讓各層之間的介面更窄（例如只開放 `poseBody`／`restBody` 給技能層），可在之後的段再收斂；本段為純搬移未做。
