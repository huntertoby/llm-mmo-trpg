# Phase RG-6 完成報告（單挑插圖支援非劍的主手；RG-4 驗收 K2）

依據：`docs/art/RG樣張.md` 9.9.5 第 1～7 條、9.9.10 量表、9.9.8 第 3、4 條（劍不套整組移）；`RG樣張-審查.md` 末三節（非劍武器審查、第 2 版複審、第 3 版複審）；截圖對照 `docs/art/shots/rg-units/duel-weapons-*-v3.png`；背景 `docs/phases/PhaseRG-4報告.md`。

## 1. 做了什麼

### 1.1 畫法（`client/src/render/duelArt.ts`）
- 分組表照樣張 `rgUnits.js` 第 3b 節的同名常數搬：`SIL_GROUP`／`silGroup`（bow、aim、staff，其他＝held）、`CROSS_GROUP`／`crossGroup`（head、gun、open、block，其他＝blade）、`PROP`、`GROUP_POSE`、`FACE`、`FACE_KIND`。數值和 9.9.2、9.9.3 逐一相同。
- `DuelSpec.hero.main`（`DuelMain`：kind，加上 form、material、element）決定剪影組和交叉組。沒給時照劍。
- 架式：沒給 `pose` 時用 `GROUP_POSE[剪影組] ?? HERO_POSE`（9.9.5 第 6 條）。
- 道具剪影（`propSilhouette`，對應樣張同名函式）：
  - 主手換成拳套載體；弓手沒有背部裝備時掛箭袋。
  - 身體照現行侵蝕 1.0。
  - 道具用 `render(def, d, 1, {})` 貼在手心，二值化 >128，不侵蝕。
  - 縫是道具外擴 0.7 再扣掉道具本身，只留落在身體上的部分。雙手槍畫兩把，遠側那把多偏 (+1.5, +4.5)。
- 手心 `handOf`：座標系和剪影畫布相同，依序 `scale(R) → translate(lx, ly) → scale(k)`，再 `drawQ` 加 `probe`，取第一筆 `gauntlet` 的 `(e, f)`。**取不到就丟錯**，不退回預設（9.9.5 第 5 條）。`DuelArt.tsx` 原本就有 try/catch，出錯時插圖留空、不會當掉。
- 道具圖示 `propOf`：預設用中間交叉的那個 def。雙手槍改成 `{kind: "pistol", form, material, element}`，先經 `resolveGear`，再經 `qResolve` 和 `qWeaponDef`。中間沒有圖示時照主手解析；解析不出來就丟錯。
- 交叉 `crossed`：
  - `FACE_KIND` 優先於 `FACE[組]`。
  - `heroW` 或 `eliteW` 是 `null` 時照現行。
  - 對異形套 `groupFit`（9.9.5 第 7 條；`drawDuel` 多傳 `es`、`hs`）。對人形照表錯開。
  - 劍那組和表外 kind 一律走原本的程式。
  - `putWeapon` 多了 dx、dy 參數，預設 0。
- `DuelSpec.onFit`：開發頁用來取得整組移動量。

### 1.2 資料接線
- `world/duelArtPlan.ts`：新增純函式 `mainKindOf(DuelWeaponPlan)`，從 `mainWeaponOf` 的結果取 kind、form、material、element；獸爪回傳 null。
- `world/DuelArt.tsx`：`duelSpecOf` 帶 `hero.main`。

### 1.3 開發頁 `/dev/duel-gallery.html`
- `?mode=fp`：劍版指紋，16 個，分兩條路。
  - dev：diff 模式的 spec。
  - game：dialog 的假 WorldView 經 `duelPlan → duelSpecOf`。
  - 用 FNV-1a，同樣張 `fnv`。
- `?mode=weapons`：和樣張比對，內容如下。
  - 主角剪影 20 種，比 alpha。
  - 道具剪影的歸因：身體、圖示、手心 probe 分開比。
  - 五種主手 × 狼王、疤面的整張插圖，DPR 1 和 2。
  - 九種主手 × 狼王、熔核、熊、蛇的整組移動量，res 1 和 2。
- `?mode=sheet&part=cmp|x4|small|all|sil|contact|silcmp`：拼圖的 PNG 寫在 `#out`。
- `?mode=dialog&hw=<kind>`：主角換主手。不給 `hw` 時照舊拿單手劍，fp 也走這條。

### 1.4 測試
新增 `world/rg6DuelWeapons.test.ts`（6 個測試）：
- 兩張分組表。
- 每個道具組的 kind 都在 `PROP` 裡。
- 劍沒有 FACE 列，`HERO_POSE` 不變。
- 鞭沒有人形列。
- `mainKindOf`。
- 雙手槍的道具圖示。

## 2. 指紋與比對

### 2.1 劍版指紋：改前改後逐字相同
無頭 Chrome 加 `--disable-gpu`。改前是 commit `3dedc3fb7`，改後是 `59dd4404e` 和 `4acb8a814`，兩次比對都逐字相同：

```
dev  res1  d457db52 82490307 5b3b977a c1bcc021   (wolf scar lord forge)
dev  res2  58791a6a 37135beb 325d5858 465c85c6
game res1  2467ef9e af5ee84f f655ace2 b73ab191
game res2  101518ec e7f17e15 c567ceb0 81ad3816
```

`?mode=diff`（RG-4 的四場和樣張逐像素比）改前改後整份輸出也一字不差：DUEL TOTAL 7151、獸爪 0。

### 2.2 非劍和樣張比（`?mode=weapons`）
- **主角剪影 20 種，比 alpha**：道具三組（弓、弩、火槍、霰彈槍、手槍、雙手槍、三種杖）在 res 1、2 都是 cv 0、縫 0。
  - RGBA 有差，因為道具那塊保留了圖示本色，遊戲端材質色暗一階（QI-1a）。剪影用的時候都會染色，所以不影響。
  - 歸因：身體 0、圖示二值化後 0、手心 probe 兩邊同一點。
  - 雙匕首（held 路）差 30／54：這是 RG-4 原本就有的樣張和遊戲 qDoll 的差，這次沒碰。
- **整張五種 × 兩場**：每格「扣掉交叉武器與精英剪影」後都是 0，所以主角剪影、背景、框都相同。剩下的差來自武器圖示顏色和人形精英，和 RG-4 的歸因一樣。法杖 × 狼王兩種 DPR 都是差異 0。
- **整組移動量，9 種 × 4 場 × res 1、2，共 72 格**：全部和樣張相同。
  - res 1 和 9.9.10 的表逐格相同：狼王錯開組全是「左 1 上 4」，熔核「左 1 上 3」，熔核的鞭「×0.98」，熊、蛇也對得上。
  - res 2 和複審 R-4 的值相同：狼王「左 0.5 上 4」，熔核「左 1.5 上 4」，鞭「左 1 上 4 ×0.98」。

## 3. 截圖（`docs/art/shots/RG-6/`，DPR 1、`?mute=1`、無頭 Chrome `--disable-gpu --mute-audio`）

全部用開發頁拍。**實機未看**：要開伺服器、湊出拿非劍主手的主角並遇到單挑精英，這次沒做。

| 檔 | 內容 | 對照 |
|---|---|---|
| `01-devpage-cmp.png` | 樣張 vs 遊戲，劍、弓、斧、法杖、雙手槍 × 狼王、疤面，真 1 倍 | `duel-weapons-3-duel-v3` |
| `02-devpage-x4.png` | 遊戲端同上 10 張，最近鄰 ×4 | `duel-weapons-4-duel-x4-v3` |
| `03-devpage-small.png` | 800 寬：縮成 259×97，真 1 倍與 ×3 | `duel-weapons-5-small-259-v3` |
| `04-devpage-all.png` | 主手 20 種 × 狼王、疤面，真 1 倍 | `duel-weapons-2-cross-v3`／`-1-sil` |
| `05-devpage-sil.png` | 主角剪影 20 種，左半與 ×2 | `duel-weapons-1-sil` |
| `06-devpage-contact.png` | 會單挑的四場 × 九種，中間 130×84，1 倍與 ×2，標出整組移動量 | `duel-weapons-6-contact-v3` |
| `07`～`14-dialog-*` | 正式的遇敵卡（開發頁假資料），1600 與 800：狼王 × 弓、熔核 × 雙手槍、疤面 × 法杖、鍛疤暫代 × 弩 | — |

我看到的：
- 弓 × 狼王：持弓的人、弓對爪、狼。弓的開口裡沒有爪痕。
- 斧、法杖：斧頭、杖頭在爪痕右上，整個露出來。
- 雙手槍：兩把手槍的 X 在左、爪痕在右。剪影手前是一小團，和樣張一樣（9.9.7 第 1 條已接受）。
- 人形：弓、弩、匕首、手槍、雙手槍錯開；斧、鞭、霰彈槍照劍交叉。
- 800 寬的弓、斧、法杖仍認得出來。

## 4. 檢查（結束碼）
- `tsc --noEmit`（typecheck）：0
- `vite build`（client build）：0
- vitest `rg6DuelWeapons.test.ts`、`rg4DuelArt.test.ts`、`rg3Duel.test.ts`：0（21 個測試全過）
- 沒改 Python，所以沒跑 ruff 和 mypy。依規定也沒跑全量 check.py。

## 5. 待 PM 決定
1. **probe 取不到時丟錯**：照 9.9.5 第 5 條不默默退回。正式遊戲裡錯誤被 `DuelArt` 的 try/catch 接住，結果是插圖留空。需要的話可以改成在畫面上標紅，或回報到 log。目前 20 種主手都取得到。
2. **雙匕首剪影和樣張差 30／54 px**（held 路，RG-4 就有）：這是兩邊 qDoll 的 `dual_dagger` 畫法小差。正式遊戲的主角走 `pairedPart` 換成單把，和開發頁比的不是同一條路，這次沒處理。
3. **道具組 kind 解析不出圖示時丟錯**（不退回 held）：目前 20 種都有圖示，這條只防以後新增的 kind。
