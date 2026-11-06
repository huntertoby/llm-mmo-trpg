# Phase RT-5 報告：主城開場四格分鏡

實作者，2026-11-05。分支 `worktree-agent-a7365caab4495379f`（從 main `c05315f2` 開始），沒有 push、沒有合併。

**依據**：`docs/art/區域主題移植需求.md` 第 5 節（含檢查清單、文案定稿、浮橋斷在雲上、免費傳送條件）；樣張 `docs/art/shots/misc/capital-opening.png`、`docs/art/sample/capital-opening.html`；設計 09 9.6.9、21 21.5（#125）。

**範圍**：
- 沒碰戰鬥畫面的 `rowLayout.ts`、`badgeLayout.ts`、`heightMark.ts`、`unitSprite.ts`、`BattleRenderer.ts`。
- 沒改紙娃娃部件與頭像繪製；主角直接用現有紙娃娃（`resolveDoll` ＋ `drawFigure`）。
- 沒有新增相依套件、原生 `title=`、`Math.random`。

**先講結論**
- 四格都做了，新角色實際跑 ①→④：1600×900 全程 25.1 秒、800×600 24.4 秒，沒有戰鬥、沒有遭遇。
- 檢查清單 5 項全過。
- 免費傳送規則伺服器本來就有（6F-2 的 `free_first_teleport`），沒有改規則。
  - 只在大世界圖的回應加了一個顯示用欄位 `AtlasRegionView.free`，並補了 API 測試。
  - 存檔與世界規則都沒動，所以不升版號、不重產快照。

---

## 1. 每格做了什麼

### ① 醒來（`awaken` 插圖＋說書人卡）

- **插圖**：新檔 `client/src/render/eventArtAwaken.ts`，由 `eventArt.ts` 匯出。8×4 格，比一般事件插圖的 7×3 大一圈。
  - 地面：RT-2 的主城背景（白石板、源晶燈、遠處藍頂白牆）。
  - 傳送陣：`capitalArt` 的光圈與晶柱，晶柱多一層光。光圈照大世界圖已開放的區上色，和實地圖同一套規則。
  - 五面區旗：`drawBanner`，圍著傳送陣的後半圈；左右兩面在主角前面。
  - 主角：玩家自己的紙娃娃（`heroDoll(field.hero)`：範本、外觀、武器、種族、裝備）。
    - 兩格動作：先仰躺（0.9 秒），再上身往後仰約 40° 半坐起。
    - 減少動態時直接畫半坐起。
    - `?anim=` 放慢時照倍率拉長。
  - 四周暗角，左上角地名小牌（實地圖名「樞島」）。
- **不進 `EVENT_ART_IDS`**：`awaken` 不是伺服器事件骨架的場景，而且主角外觀每個人不同，所以不走事件插圖的圖片快取，直接畫在畫布上。伺服器那份清單不用改。
- **卡片**：`OpeningDialog.tsx` 新增 `AwakenDialog`。
  - 沿用 `DialogFrame`，也就是共用彈窗。
  - 說書人頭像框用 `hub` 主題（`FALLBACK_THEME`）。
  - 只有一個動作按鈕「站起來」。
  - 文字是內容檔 `content/world/newcomer.yaml` 的 `opening`，經由伺服器的 `guide.opening` 帶來。畫面裡沒有寫死文案。
- **哪句放哪裡**：`world/opening.ts` 的 `splitOpening`。
  - 說話的人名字和地圖上站著的人（情境物件的 `figure`）相同，那句就給那個人，也就是 ② 的守印人。
  - 其他句子放插圖卡。
  - 地圖上沒有那個人時，全部放插圖卡，不會漏句子。
  - 沒有實地地圖時，照舊用原本的 `OpeningDialog`。
- 截圖：
  - `rt5_1_awaken_1600.png`、`rt5_1_awaken_1600_zoom.png`
  - `rt5_1_awaken_800.png`、`rt5_1_awaken_800_zoom.png`

### ② 廣場與浮橋＋守印人「！」

- **守印人**：按「站起來」之後（伺服器記下 `opening` 看過了）才出現，一直留到角色到過霧渡鎮（伺服器不再給開場）。
  - 頭上出現「！」，任務標記和 NPC 的「！」同一套樣式。
  - 旁邊是整句對話泡泡：名字一行，加「新來的？雲嶺那邊缺人手。站上傳送陣，去霧渡鎮找渡婆婆。」
  - 泡泡放在守印人左邊、和「！」同高。守印人站在地圖北緣附近，放頭頂會被畫面上緣切掉。
  - 點「！」等於點守印人，照舊開公告板。
  - `fieldPeople.headMarks` 多一種 `figure`（新參數 `guides`）。
- **800×600 看不到守印人時**：鏡頭跟著傳送陣，守印人在畫面外北邊。
  - 這時「！」和泡泡夾到畫面邊上的 HUD 安全區（不壓主角卡、小地圖），名字旁加往那人方向的箭頭「↗」。
  - 判斷用整個可視區：1600×900 看得到守印人，就照原位不夾。
  - 對應 `opening.guideAnchor`。
- **任務欄**：照舊顯示「到霧渡鎮找渡婆婆／走到中央廣場的傳送陣，或按 M 選雲嶺的霧渡鎮」。800 寬時照 6F-3 的規則收合成圖示。
- **橋頭石碑的小牌**：`FieldHeads.tsx` 的 `FieldSteleTags`，資料來自 `opening.steleTags`。
  - 照大世界圖的 `atlas.regions` 開放狀態畫，沒有新增欄位。
  - 已開放：只寫區名，細框用該區顏色。
  - 有地點圖但還沒開放（荒原）：灰色加鎖，第二行「尚未開放」。
  - 這一季沒有地點圖（其他三區）：灰色加鎖，第二行「之後的賽季」。
  - 小牌只畫、不接滑鼠，點石碑照舊開那一區的傳送選單。
- **浮橋斷在雲上**：`capitalArt.drawSkyBridge` 改成：
  - 前 4 塊木板相連，之後缺 1 塊，再一塊歪掉的鬆木板，最外端缺 1 塊（`BRIDGE_PLANKS`）。
  - 繩欄在斷口斷開（`BRIDGE_BREAK_Y`），斷繩往外垂，最後一根繩柱留在斷口前。
  - 格子外側約 1/3 只剩雲，木板不鋪到地圖邊。
- 截圖：
  - 守印人：`rt5_2_plaza_1600.png`／`_zoom`、`rt5_2_plaza_800.png`／`_zoom`（800 是夾到邊上的那種）。
  - 石碑小牌三種狀態的 zoom：
    - 已開放：`rt5_2_stele_open_zoom.png`（整張是 `rt5_2_steles_west_1600.png`）
    - 尚未開放：`rt5_2_stele_locked_zoom.png`（整張是 `rt5_2_steles_south_1600.png`）
    - 之後的賽季：`rt5_2_stele_later_zoom.png`（同上）
  - 浮橋：`rt5_2_bridge_east_zoom.png`（取自 `rt5_2_plaza_1600`）、`rt5_2_bridge_west_zoom.png`（取自 `rt5_2_steles_west_1600`）。
- 拍廣場時開場對話框已經關掉（按過「站起來」）。

### ③ 第一次打開大世界圖

- **五座島依序從雲裡浮起**：
  - 每座 0.3 秒，照 `regions.yaml` 的順序，第 i 座在 i×0.3 秒開始，主城不動。
  - 浮起時從下方 70px 上來並淡入，先快後慢。
  - 島下的雲層與前景雲照舊蓋在島前面，所以看起來是從雲裡浮上來。
  - 畫法：`worldMapPainter.riseAt`、`paintOverlay` 的 `rise` 選項，只平移已快取的貼圖、不重畫。
- **只播一次**：
  - 前端在本機記住這個角色播過了（`opening.takeAtlasRise`，localStorage 鍵 `trpg.atlasRise`，讀寫都包 try/catch）。
  - 第二次打開不播（`data-rise="0"`）。
- **減少動態時**：
  - 不播，直接顯示。
  - 這時也不記成播過，之後關掉減少動態，第一次打開還會看到一次。
- **雲嶺「免費」**：
  - 伺服器在 `AtlasRegionView` 加了 `free`，照 `free_first_teleport`（角色在主城、還沒到過新手區的小鎮）。
  - 傳送鈕寫「傳送到霧渡鎮（免費）」，改成金框，外面一圈較強的金光。
  - 點擊區跟著變寬；浮島說明卡多「（第一次免費）」。
  - 到過之後 `free` 是 false，「免費」就不見了。
- 截圖：
  - `rt5_3_atlas_1600.png`／`_zoom`、`rt5_3_atlas_800.png`／`_zoom`：浮起播完之後。
  - `rt5_3_rise_mid_1600.png`：浮起中的一格（打開後約 0.7 秒，前 3 座已經上來）。
  - `rt5_3_atlas_reduced_1600.png`／`_zoom`：減少動態時打開後 0.15 秒就全部到位，`data-rise="0"`。
  - `rt5_3_atlas_again_1600.png`、`rt5_3_atlas_again_800.png`：第二次打開，沒有動畫，`data-rise="0"`。

### ④ 抵達霧渡鎮

- 沿用 RT-1：`field.region` 換成 `cloud_ridge`，主題淡入 0.3 秒（`--rt-accent` 變成 `#6aa84a`），四角換雲紋，地名牌換成玉色。
- 渡婆婆頭上「！」：伺服器原本的任務標記，說明卡是「渡婆婆・好感：中立・有任務可以接」。
- 任務欄更新成「找頭上有「！」的渡婆婆說話」。
- 截圖：`rt5_4_ferry_1600.png`／`_zoom`、`rt5_4_ferry_800.png`／`_zoom`。

## 2. 伺服器

- 規則本來就有：`trpg.world.atlas.free_first_teleport`、`can_teleport_to`、`town.teleport`。
  - 條件是「角色在主城、還沒到過新手區的小鎮」（`visited_towns` 沒有它），和需求寫的「角色還沒到過霧渡鎮」一致。
  - 沒有另外加旗標。
- 改動只有一個顯示用欄位：`AtlasRegionView.free: bool = False`（`world_schemas.py`、`world_atlas_view.py`）。
  - 重產了 `client/openapi.json` 與 `client/src/api/schema.d.ts`。
- 存檔、世界規則都沒動。所以：
  - 不升 `WORLD_RULES_VERSION`；
  - 不重產 3wr2 與 CLI 快照；
  - `tests/test_architecture.py` 的 season_policy 欄位清單不受影響。
- 新測試 `tests/api/test_opening_rt5.py`，3 項：
  - `test_free_label_only_before_first_visit`：新角色只有雲嶺 `free`；傳過去之後、再回主城都沒有。
  - `test_stele_plaques_follow_atlas_status`：雲嶺 open、荒原 locked、其他三區 later；五座石碑對五區。
  - `test_opening_to_ferry_without_battle`：開場兩句照內容檔；守印人站在主城；傳到霧渡鎮沒有遭遇，渡婆婆的標記是 `quest`。

## 3. 檢查清單

| 項目 | 結果 | 證據 |
|---|---|---|
| 新角色第一次進遊戲照 ①→④ 播，全程不超過 2 分鐘、沒有戰鬥 | ✓ | 見下方說明 |
| 浮橋石碑的小牌和開放狀態一致 | ✓ | 見下方說明 |
| 大世界的浮起動畫只播一次，減少動態時不播 | ✓ | 見下方說明 |
| 免費傳送只有第一次 | ✓ | 見下方說明 |
| 到霧渡鎮後主題換成雲嶺 | ✓ | 見下方說明 |

- **①→④、不超過 2 分鐘、沒有戰鬥**
  - 實測從按「建立並在主城醒來」到站上霧渡鎮：1600×900 是 25.1 秒，800×600 是 24.4 秒。
    - 這段時間含模擬看字的停頓：醒來 5 秒、廣場 4 秒、大世界圖約 5 秒。
    - 建角頁到醒來卡約 4.4 秒。
  - 全程沒有戰鬥畫面，也沒有遭遇卡。
  - 腳本與紀錄：`scratchpad/rt5/flow.mjs`、`flow_1600.json`、`flow_800.json`。
- **石碑小牌和開放狀態一致**
  - 實機讀到 `cloud_ridge:open:雲嶺`、`ashen_waste:locked:灰燼荒原 尚未開放`，其他三區是「之後的賽季」。
  - 測試：`test_stele_plaques_follow_atlas_status`；vitest「小牌照大世界圖的開放狀態」「小牌畫出來」。
- **浮起只播一次、減少動態不播**
  - 實機：第一次 `data-rise=1`，第二次 0；減少動態第一次就是 0，而且沒有寫進本機紀錄。
  - vitest：「每座 0.3 秒、照順序」「浮起中還沒輪到的島不貼」「前端記住播過了」。
- **免費傳送只有第一次**
  - 實機：第一次傳送鈕寫「傳送到霧渡鎮（免費）」，`data-free=1`。
  - pytest：`test_free_label_only_before_first_visit`（含回主城後）；原本的 `tests/world/test_newcomer_6f2.py`（規則）。
- **到霧渡鎮後主題換成雲嶺**
  - 實機：`--rt-accent` 是 `#6aa84a`，地圖是 `mist_ferry`。
  - 截圖：`rt5_4_ferry_*`。

## 4. 驗證與結束碼

**截圖方式**
- 無頭 Chrome（`--mute-audio`），網址加 `?mute=1`。
- 用 `Emulation.setDeviceMetricsOverride` 把視窗真的設成檔名上的尺寸（device scale 1）。
- 全圖與 `_zoom` 是同一幀：只拍一次全畫面 PNG，zoom 從同一張裁出、最近鄰放大。
- 交件前用 `file` 核對：全圖都是 1600×900 或 800×600，和檔名一致。共 30 張 `docs/art/rt5_*`。

**排版煙霧檢查**
- 網址 `/?dev=1&anim=0.1&mute=1`，先 `localStorage.clear()` 再重新載入，跑 `__layoutSmoke.runCase`。
- 1600×900、1040×624、800×600 都是「全 PASS」，各 12 列。
- 結束碼 0（`scratchpad/rt5/smoke.log`）。

**6.5.1 浮動卡實測**（大世界圖上雲嶺浮島的說明卡，RT-5 在這張卡加了「第一次免費」）

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過 → 卡片出現 | ✓ | ✓ |
| 分 6 步滑進卡片後不關 | ✓ | ✓ |
| 卡內捲動後不關 | ✓（卡片 36px 高，沒有可捲的內容，只確認不關） | ✓ |
| 點一下釘住 → 滑出去不關 | ✓ | ✓ |
| Esc 先關卡片，大世界圖還開著 | ✓ | ✓ |

截圖：`rt5_float_1600_pinned.png`、`rt5_float_800_pinned.png`。

**每次 commit 前**
- `ruff check`：0。
- `ruff format --check`：0（2191 files already formatted）。
- `mypy src`：Success（531 source files）。
- `lint-imports`：13 kept、0 broken。
- 重播：`trpg battle --map swamp --seed 7 --log-json` 結束碼 0；`trpg battle replay` 通過（88 個動作、313 個事件）。

**相關 pytest**（`-n 8`）：59 passed，結束碼 0。
- `tests/api/test_opening_rt5.py`
- `tests/api/test_newcomer_api_6f2.py`
- `tests/api/test_openapi_snapshot.py`
- `tests/world/test_capital.py`
- `tests/world/test_capital_hub.py`
- `tests/world/test_newcomer_6f2.py`

**相關 vitest**：13 個檔、281 項全過。
- RT-5 新測試：`client/src/world/rt5.test.ts`，15 項。
- 原本的相關測試：atlas、worldMapArt、capitalArt、eventArt、fieldPeople、story、tracker6f2、floatCardRule、regionMapArt、uiE1、uiE1b、hud。

**交件前**
- client 全部 vitest：257 個檔、2949 項全過，結束碼 0。
- `corepack pnpm -C client build`：結束碼 0（只有原本就有的 chunk 大小提醒）。

## 5. 檔案清單

**新增**
- `client/src/render/eventArtAwaken.ts`：`awaken` 插圖。
- `client/src/world/opening.ts`：句子分配、開場階段、石碑小牌、泡泡夾邊、浮起只播一次。
- `client/src/world/rt5.test.ts`
- `tests/api/test_opening_rt5.py`
- 截圖 `docs/art/rt5_*`（30 張）、本報告。

**修改**
- 伺服器：`src/trpg/api/world_schemas.py`、`src/trpg/api/world_atlas_view.py`。
- API 型別：
  - `client/openapi.json`、`client/src/api/schema.d.ts`（重產）
  - `client/src/api/types.ts`（`WorldOpeningLine`）
- 畫法：
  - `client/src/render/capitalArt.ts`（斷橋）
  - `eventArt.ts`（匯出 awaken）
  - `worldMapArt.ts`（免費鈕）
  - `worldMapPainter.ts`（浮起）
- 畫面：
  - `client/src/screens/WorldScreen.tsx`
  - `client/src/world/OpeningDialog.tsx`、`WorldField.tsx`、`FieldHeads.tsx`、`fieldPeople.ts`
  - `client/src/world/AtlasMap.tsx`、`atlasModel.ts`、`atlasScene.ts`
- 樣式：`client/src/world/fieldPeople.css`、`client/src/styles/world-hud.css`。
- 測試資料補 `free: false`：`client/src/dev/mapGallery.tsx`、`render/regionMapArt.test.ts`、`render/worldMapArt.test.ts`、`world/atlas.test.ts`。

複雜度：沒有新增 `noqa`。

## 6. 待 PM 決定

1. **守印人離傳送陣有 10 格**：守印人在封印廣場 (25,3)，樣張畫在傳送陣旁邊。
   - 我沒有改內容檔的站位，因為那是玩法 PM 的主城草稿。
   - 800×600 看不到他，改成把「！」和泡泡夾到畫面邊上、加方向箭頭。
   - 要不要把守印人移到廣場邊，或開場時讓他站到傳送陣旁，請玩法 PM 決定。
2. **泡泡停留多久**：守印人的泡泡從按「站起來」一直留到角色到過霧渡鎮，一般 NPC 的泡泡是 6 秒。
   - 選這個做法是因為它就是第一個指示。
   - 如果覺得太久，可以改成幾秒後收成只剩「！」。
3. **小牌的「尚未開放」「之後的賽季」是畫面標籤**（`STELE_SUB_ZH`），沒有放進內容檔。
   - 區名和開放狀態照伺服器。
   - 荒原的解鎖條件「世界事件：霧潮入侵」只放在大世界圖上，石碑小牌照需求寫「尚未開放」。
4. **小牌一直顯示**：不只開場期間；主城的石碑之後也一直有小牌，荒原開放後就只寫區名。
5. **插圖卡的地名小牌寫「樞島」**（實地圖名），樣張是「樞島・中央廣場」。
   - 「中央廣場」目前沒有資料欄位，所以沒有寫死在畫面裡。
   - 要的話請在內容檔加一個欄位。
6. **半坐起的畫法**：不改紙娃娃部件，只把整個人往後轉約 40°，所以腿也跟著斜。
   - 等 Q 版定案後，可以換成真正的坐姿。
7. **浮起時的浮橋**：大世界圖上主城到雲嶺的木板吊橋畫在前景層，浮起的前 0.3 秒，雲嶺還沒上來時吊橋已經在。
   - 這段很短，我沒有另外處理。
8. **大世界圖的浮起記在本機**：換電腦或清掉瀏覽器資料會再播一次。需求寫「前端記住已播過即可」，所以沒放進角色存檔。
9. **主城地圖的浮橋只有邊緣一格**：浮橋的斷口畫在那一格的外側 1/3。鏡頭夾在地圖邊，所以浮橋在畫面上偏小。
   - 要更明顯的話，需要地圖多留一兩格雲，這要改內容檔的地圖。

## 7. 程序

- 自己啟動的程序：
  - API 8475：`scratchpad/rt5/serve.py`，用 worktree 的 `.venv` 與 `client/dist`，存檔在 `scratchpad/rt5/saves`。
    - 背景工作 `bvhou6bzn`，python PID 69812。
  - CDP 9475 的無頭 Chrome（`--mute-audio`）：PID 58136。
- 結束時只用這些 PID 或背景工作 ID 關掉。
- 沒碰 8000、8001、8010、`tmp_x`、`saves/`。
- 暫存都在 `scratchpad/rt5/`，沒有 commit。
- worktree 裡跑了 `uv sync --frozen` 和 `corepack pnpm -C client install --frozen-lockfile`，這兩個是 worktree 的環境，不 commit。

**client 全部 vitest**（最後一個程式 commit `942ddb45` 之後跑的）：257 個檔、2949 項全過，結束碼 0。
