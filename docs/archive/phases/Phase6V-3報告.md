# Phase 6V-3／6V-4 報告：場景小修與主城廣場（只換外觀）

> 2026-11-04，實作者（agent）。worktree 分支，沒 push、沒合併。基準 main `664f7339`（含 6V-1、6V-2）。
> 規格來源：`docs/archive/art/Fable審查.md` 第 2 節 B、C；`docs/archive/art/6V-1與6H-1b檢查.md` 待決 1、3、4；`RT-2與RT-4與6H-1與AU-3檢查.md` RT-2 待決 2。
> **沒改任何人物畫法**（inkDoll、inkStyle、inkGear、inkWeapons、inkOffhand、portrait 都沒動），沒新增人物部件；工坊師傅護目鏡照指示不做。
> 沒碰世界 HUD／彈窗／鏡頭、`src/trpg/llm`、`content/llm`、霧渡鎮導師堂／葛蘭／新手任務。數值、規則、格子都沒改；沒有新增相依。

## 1. 逐項

| # | 項目 | 做了什麼 | 檔案 |
|---|---|---|---|
| 1 | 火地表 | 火苗改成彎曲的火舌：圓底、尖端往一側彎、兩側各一條小火舌、三層色（暗紅橘／橘／黃芯），每格 2～3 簇。底下加黑色焦痕：不規則的焦斑、煙燻暈、幾點還在燒的灰燼。全部照格子座標雜湊。原本的火光閃動（`surfaceShimmer`）沒改，減少動態時照舊不登記、畫面靜止。共用的 `artDraw.flame` 沒動（狀態圖示還在用） | `render/terrainArt.ts` |
| 2 | 室內後牆掛件 | 新增 `wallHangings`：在擺設和緊貼後牆的物件都沒佔的欄掛東西，相鄰兩欄只掛一個。依室內種類輪流：酒館是小窗、掛燈、鍋具；鐵匠鋪是工具板（鐵鉗、錘子、馬蹄鐵）、掛燈、小窗；導師殿是小窗、掛燈、紫底金邊晶石掛旗。荒原室內的小窗外是暗紅黃昏。後牆快取鍵加上掛件；沒有掛件時鍵和原本一樣 | `render/interiorArt.ts`、`render/sceneryModel.ts`、`render/sceneryLayer.ts`、`world/fieldScenery.ts` |
| 3 | 附魔台發光環 | 靜態貼圖：外圈暈染、一道粗亮環（線寬 3、紫色光暈 12）、一道內細環。環境動態層另外疊一圈 8 個符文：從正上方畫成圓，再壓扁成透視，慢慢轉（12 秒一圈），亮度輕微呼吸。減少動態或關掉時停在第 0 毫秒 | `render/interiorArt.ts`、`render/ambientAnim.ts`、`render/ambientLayer.ts` |
| 4 | 荒原祭壇 | 事件插圖「祭壇・機遇」的荒原版：祭壇前三格的青石板換成黑曜岩石板。石板近黑，石塊左上有一道玻璃光澤；每格一道暗紅發光裂紋，畫法同荒原焦土地的裂縫：先畫黑縫，再疊模糊的暗紅光。雲嶺版照舊是青石板 | `render/eventArtParts.ts`（`obsidianSlab`）、`render/eventArt.ts` |
| 5 | 公告板頭像列 | 公告板面板標題下加一列「頭像＋名字＋一句話」，版面照 NPC 面板（`world-npc-portrait`）。頭像直接呼叫現有的 `Portrait`，資料用 6V-1 的 `figure.portrait`。人選：這張圖上 `panel: board`、有 `figure` 的情境物件，依 ID 排第一個，主城就是守印人；其他城鎮的公告板沒有這列。一句話放內容檔的 `figure.line_zh`（新欄位，見第 3 節） | `world/BoardPanel.tsx`、`content/.../capital.yaml`、`src/trpg/content/fields.py` |
| 6 | NPC 空手 | `npcFieldLook`（照頭像換算的地圖外觀）把主手設成 `FIGURE_EMPTY_HAND`，跟 6V-1 情境物件上的人同一個做法。紙娃娃不認得這個造型，所以不畫主手，空手的武器 id 不會再退回預設的劍。頭像有寫 `gear.main_hand` 的、白狐的，都照舊。**只改了資料解讀，沒改紙娃娃的退路邏輯和畫法** | `world/npcLook.ts` |
| 7 | 5 位 NPC 外觀 | 在設施格填 `figure`（見第 4 節），做法跟 6V-1 情境物件的 `figure` 一樣：在原格多畫一個不畫血條的紙娃娃，點那一格照舊是設施，不擋路，不是 npcs。站位都用原本設施的格子，**沒新增格子** | 內容 3 張室內圖＋主城；`fields.py`（`FieldFacility.figure`）、`api/world_field_schemas.py`、`api/world_field_view.py`、`client/openapi.json`、`api/schema.d.ts`、`world/fieldModel.ts`（`facilityFigures`、`figureSpots`）、`world/fieldAmbient.ts`、`world/npcLook.ts`（`facilityFigureId`） |
| 8 | 工坊師傅護目鏡 | **沒做**（照指示，等 Q 版換皮段） | — |
| 9 | 主城 decor | 新增 `render/plazaDecor.ts`：花壇 6、攤布 3、晾衣繩 1（3 格寬）、堆箱 4。中央廣場另有放射狀鋪法：範圍是四盞源晶燈圍起來的 11～20 × 9～14，圓心在傳送石，由一圈深一圈淺的環帶、同心接縫、每圈錯半塊的放射接縫和一道淡金嵌線組成。地面的裝飾（花壇、攤布、鋪法）放裝飾層，立著的（晾衣繩、堆箱）放物件層 | `render/plazaDecor.ts`、`render/sceneryModel.ts`、`render/sceneryLayer.ts`、`world/fieldScenery.ts`（`plazaDecorOf`、`pavingOf`） |
| 10 | 許願池 | 改成圓形石緣水池：透視成 0.62 的橢圓，有前緣立面、14 塊石的接縫、漸層池水、兩圈漣漪、兩層石座和金色噴口。底下墊一塊方形石板台，蓋住 2×2 的水表面，圓池不會浮在藍色方格上。噴水是確定性動畫：左右兩道拋物線水弧各 7 顆水珠，加中央一道短水柱，1.4 秒一輪，都在環境動態層，減少動態時停在第 0 毫秒 | `render/capitalArt.ts`（`fountainGeom`）、`render/ambientAnim.ts`（`fountainSpray`）、`render/ambientLayer.ts`（`fountainSpout`） |
| 11 | 不擋路 | decor 只是 `FieldScenery.plaza` 的外觀資料，地形、物件、格子、規則都沒動。每件 decor 每次都照 FieldView 檢查，要放在空的石地、草地或泥地上；格子被物件、人、設施、情境物件、門、傳送石、建築範圍或表面佔住，那件就整件不畫。從傳送石到三扇門的直線留空 | 同上 |

## 2. 測試

- **新的 vitest**（共 23 項）：
  - `render/scene6v3.test.ts`（13 項）：
    - 火：確定性；有焦痕；火舌是貝茲曲線、三層色、尖端往偏的那一側；閃動是時間 → 相位。
    - 掛件：避開擺設與物件，相鄰兩欄不同時掛；照種類輪流；確定性；快取鍵；四種掛件都畫得出來，荒原窗色另外驗。
    - 附魔環：亮環的線寬與光暈；8 個符文；12 秒一圈；環心和靜態貼圖對齊。
    - 黑曜岩：荒原 3 格、沒有青石色；雲嶺照舊；確定性。
    - 許願池：確定性；立面、池水、接縫；噴口在池心；水珠從噴口出發、落在池水內；確定性。
    - 減少動態或關掉時，環境動態層的時鐘不前進。
    - 來源掃描：10 個畫法檔沒有 `Math.random(`。
  - `world/figures6v3.test.ts`（5 項）：
    - 剛好 5 個設施有 `figure`，用的都是現有部件。
    - 地圖上的單位站在原格、沒有血條，點那一格還是設施。
    - 鐵匠拿錘子、待機打鐵；殿主拿晶杖、戴晶冠。
    - 公告板的頭像列：主城有，其他城鎮沒有。
    - NPC 空手：伺服器有給外觀的照舊。
  - `world/plaza6v4.test.ts`（5 項）：
    - 14 件裝飾都放得下。
    - 不疊在物件、設施、門、建築、水上；主要的路留空。
    - 格子被佔就不畫；室內和其他地圖沒有裝飾。
    - 鋪法的範圍、圓心、60 格。
    - 畫法確定。
- **改到的既有 vitest**：`render/regionArt4.test.ts` 鎖住的預設畫法雜湊 `6aa45e1d` → `870425f3`。只有火表面換了畫法，是刻意更新，註解有寫。
- **client 全部 vitest**：231 檔、2517 項通過（結束碼 0）。`corepack pnpm -C client build`（tsc ＋ vite）結束碼 0。
- **新的 Python 測試**：`tests/world/test_capital_figures_6v3.py`，共 10 項：
  - 5 位的站位和外觀，全遊戲只有這 5 個設施有 `figure`；
  - 用現有部件；
  - 通行表和拿掉 `figure` 的地圖一樣；
  - 守印人的 `line_zh`，而且 `note_zh` 沒動；
  - API 把設施的 `figure` 帶給前端。
- **規則雜湊**：`tests/content/test_field_buildings.py` 照 6V-1 的做法，雜湊計算再多排除設施的 `figure`。10 張圖的雜湊**和原本一樣**（主城 `73a7cad0ebf4dfb6`、三間主城室內都沒變），表示規則內容沒變。一句話放在 `figure.line_zh`、不放 `note_zh`，就是為了不動規則雜湊。
- **其他 Python 檢查**：
  - `trpg content check` 通過。
  - ruff check、ruff format --check、mypy src（516 檔）、lint-imports（13 條）全部乾淨。
  - 另外跑了 `tests/world` 全部、`tests/api` 的 world_field 6 檔、`test_openapi_snapshot`、`test_newcomer_api_6f2`，全部通過。
- **API**：重跑了 `scripts/export_openapi.py` 和 `gen:api`。
- **noqa**：沒有新增。

## 3. 新增的資料欄位（都只畫）

- `FieldFacility.figure`：寫法同 6V-1 情境物件的 `figure`，API 是 `FieldFacilityView.figure`。
- `FieldFigure.line_zh`：頭像旁的一句話，上限 40 字，省略＝空。只顯示，不給說書人。

## 4. 填了哪些 NPC 資料、缺哪些部件

| NPC | 地圖、格子（原設施站位） | 填的資料 | 缺的部件（用什麼代替） |
|---|---|---|---|
| 殿主 | 導師殿 [6, 2]（mentor） | 晶冠（`head: crown`，晶紫色）、白袍晶紫邊（`robe`）、晶杖（`held: staff/crystal`）、白長髮白鬍、皺紋，面向南 | 無 |
| 酒館老闆 | 樞島酒館 [6, 1]（tavern，櫃檯後） | 米白襯衫（`shirt`）、壯碩、鬍子、八字鬍，待機擦櫃檯（`work: keeper`），面向南 | **圍裙**：紙娃娃和頭像都沒有圍裙部件（`apron_cross` 是醫者紅十字，不是圍裙），先用米白襯衫 |
| 鐵匠 | 樞島鐵匠鋪 [4, 2]（smithy） | 深色皮衣（`leather`）、皮手套、鎚子（`held: hammer/iron`）、壯碩、鬍子、煤灰，待機打鐵（`work: smith`），面向西邊的鐵砧 | **皮圍裙**：同上，先用深色皮衣 |
| 附魔師 | 樞島鐵匠鋪 [7, 3]（enchanter） | 紫袍淡紫邊（`robe`）、黑長髮、耳環，面向北邊的附魔台 | 無 |
| 傭兵管事 | 主城 [14, 18]（hire） | 舊鎖甲（`mail`，暗灰褐）、灰短髮、鬍子、刀疤、皺紋，面向南 | 無（「舊」只靠暗色表現，沒有磨損或破洞部件） |

依暫停清單，這 5 位**還沒拍驗收用的頭像或紙娃娃圖**。`6v3_08`（鐵匠鋪）、`6v3_10`（酒館）裡看得到鐵匠、附魔師、酒館老闆站在原位，但這兩張是用來看室內後牆和附魔台的，人物等換皮後再重拍。

## 5. 截圖（`docs/art/`，1280×800 或放大，全部靜音：無頭 Chrome `--mute-audio`、網址 `?mute=1`）

| 位置 | 之前 | 之後 |
|---|---|---|
| 主城廣場 | `6v3_01_plaza_before.jpg` | `6v3_02_plaza_after.jpg`：放射狀鋪法加金色嵌線，源晶燈內側的花壇，西側、東南的攤布，鐵匠鋪旁的堆箱 |
| 許願池（全景） | `6v3_03_pool_before.jpg` | `6v3_04_pool_after.jpg`：圓形石緣水池，晾衣繩在酒館屋後 |
| 許願池（放大 2×） | `6v3_05_pool_zoom_before.jpg`：橢圓石邊浮在藍色方格上 | `6v3_06_pool_zoom_after.jpg`：石板台、圓池、噴水 |
| 室內：鐵匠鋪（放大 2×） | `6v3_07_smithy_before.jpg` | `6v3_08_smithy_after.jpg`：工具板、掛燈；附魔台是明顯的發光環 |
| 室內：酒館（放大 2×） | `6v3_09_tavern_before.jpg` | `6v3_10_tavern_after.jpg`：小窗、掛燈 |
| 火地表（區域圖庫，放大 3×） | `6v3_11_fire_before.jpg`：水滴形火苗 | `6v3_12_fire_after.jpg`：彎曲火舌、兩側小火舌、黑底焦痕 |
| 荒原祭壇（事件插圖 1:1，雲嶺／荒原／主城並排） | `6v3_13_altar_before.jpg`：中間是青石板 | `6v3_14_altar_after.jpg`：荒原中間是黑曜岩加暗紅裂紋 |
| 公告板 | `6v3_15_board_before.jpg` | `6v3_16_board_after.jpg`：標題下有守印人頭像和一句話 |

拍法：

- **遊戲畫面**：
  - 自己的伺服器 `trpg serve --port 8388`，存檔放 `scratchpad/v34/saves`，設 `TRPG_LLM_GENERATE=false`、`TRPG_DEV_ROUTES=1`。
  - 「之前」用 `664f7339` 的 client 建置，「之後」用這段的建置，兩個輪流放進 `client/dist`，在同一個位置各拍一張。
  - 角色用 API 建立，用 walk 動作走到各位置。
- **火和祭壇**：用自己的 vite（之後 5391、之前 5392）開 `region-gallery.html`、`event-art-gallery.html?mode=raw&only=altar`。
- **結束**：伺服器用工作 ID 結束，兩個 vite 用自己的 PID（45604、26620）結束。
- **沒碰**：`tmp_x`、`saves/`；沒用 8000、8001、8010、8366、8344、5388。

## 6. 待 PM 決定

1. **給玩法 PM 確認：公告板的一句話**。守印人：「封印和懸賞的消息，都貼在板上了。」
   - 照最保守的寫法，只講公告板上有什麼，沒有新設定。
   - 寫在 `capital.yaml` 守印人的 `figure.line_zh`。
2. **圍裙部件**：酒館老闆的圍裙、鐵匠的皮圍裙，現有部件都沒有，先用襯衫和皮衣代替。要不要在 Q 版換皮段加 `apron` 部件（身體疊層），請美術 PM 決定。
3. **裝飾版面寫在前端**：主城的 decor 位置寫在 `render/plazaDecor.ts` 的 `CAPITAL_DECOR`。
   - 原因：實地地圖沒有地圖層的 `look`，也沒有 decor 欄位。
   - 每次都照 FieldView 檢查格子空著才畫，內容改了也不會疊到人或物件上。
   - 要完全照「內容即資料」做，可以另開一段：在地圖檔加 `decor:` 清單（只畫，規則雜湊排除），由開發 PM 決定。
4. **裝飾畫在可走的格子上**：花壇、攤布、堆箱、晾衣繩都在可走的空格。主角走過去會和它們疊在一起，這是只畫、不擋路的直接結果。要真的擋路就是規則變動，不在這段。
5. **掛件數量**：鐵匠鋪、酒館的後牆被鍛爐、酒架、壁爐佔掉不少，只掛得下 2 個（工具板加掛燈、小窗加掛燈），酒館的鍋具沒有位置。要更多就得把掛件疊在擺設上方，請美術 PM 看 `6v3_08`、`6v3_10` 決定。
6. **原型數值**，照最保守的預設做完，都是常數：
   - 附魔環 12 秒一圈；
   - 噴水一輪 1.4 秒、每道水弧 7 顆、拱高 10；
   - 鋪法 6 圈（半徑 1.7～5.7 格）；
   - 火苗每格 2～3 簇、焦斑 2～3 塊。
7. **噴水在畫面上偏小**（`6v3_06`）：水珠是 8 單位的小點。美術 PM 覺得不明顯的話，可以把 `SPRAY_RISE` 或水珠大小調大。

## 7. commit（worktree 分支）

- `1a865fdd` 火地表
- `7696795d` 荒原祭壇黑曜岩
- `fbc64f2e` 室內掛件、附魔環、圓形許願池與噴水
- `45511865` 設施格上的人、公告板頭像列、NPC 空手（含 Python、內容、OpenAPI）
- `b9fc256c` 主城廣場裝飾與放射狀鋪法
- 最後一個 commit：許願池石板台、截圖、這份報告
