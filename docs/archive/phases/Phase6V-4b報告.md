# Phase 6V-4b 報告：主城裝飾搬進地圖檔（只換外觀）

> 2026-11-04，實作者（agent）。worktree 分支，沒有 push，也沒有合併。基準是 main `71eb8352`。
> 規格來源：`docs/art/6V-3與6V-4檢查.md` 第 2 節的第 3、4、5、7 點。
> **規則沒動**：地形、格子、通行、物件都沒改。10 張圖的規則雜湊和原本一樣。
> 沒碰人物繪製（inkDoll、inkStyle、portrait 等）、`src/trpg/llm`、`content/llm`，也沒碰世界 HUD 和彈窗。沒有新增相依套件。

## 1. 逐項

| # | 項目 | 做了什麼 | 檔案 |
|---|---|---|---|
| 1 | decor 搬進地圖檔 | 實地地圖的 `look` 加了 `decor:` 清單，比照 6V-2b 的 `look.chasm_style`。規則雜湊本來就排除整個 `look`，所以雜湊不受影響。<br>schema 是 `FieldDecor`，欄位有 `kind`、`at`、`size`、`center`。種類有 5 種：`flower_bed`、`stall_cloth`、`clothesline`、`crate_stack`、`radial_paving`。<br>固定尺寸的種類可以省略 `size`；有寫的話必須和固定尺寸相同。晾衣繩是 3×1，其他都是 1×1。<br>鋪法的範圍和圓心都必填，而且圓心要落在範圍內。<br>地圖層也會檢查：每件都要整件在地圖內；鋪法以外的裝飾不能疊在同一格。<br>主城的 14 件裝飾加 1 件鋪法照原本的位置寫進 `capital.yaml`。鋪法本來是用四盞源晶燈推算範圍，現在改成在資料裡直接寫範圍和圓心。<br>API 新增 `FieldView.decor`（`FieldDecorView`：kind、layer、x、y、width、height、center_x、center_y），並重跑了 `export_openapi` 和 `gen:api`。<br>前端的 `plazaDecor.ts` 拿掉寫死的 `CAPITAL_DECOR`、`DECOR_LAYOUTS` 和 `DECOR_LAYER`，只留下畫法。`fieldScenery` 改成讀 `field.decor`，照舊會檢查格子是不是空著；前端不認得的種類就不畫。<br>`FieldScenery` 的 `paving`、`decor` 從 `plaza` 底下移到頂層，任何地圖都可以照資料放。主城的畫的順序和原本相同：先鋪法，再裝飾，最後傳送陣。 | `src/trpg/content/fields.py`、`src/trpg/api/world_field_schemas.py`、`src/trpg/api/world_field_view.py`、`content/world/fields/capital/capital.yaml`、`client/openapi.json`、`client/src/api/schema.d.ts`、`client/src/render/plazaDecor.ts`、`client/src/render/sceneryModel.ts`、`client/src/render/sceneryLayer.ts`、`client/src/world/fieldScenery.ts` |
| 2 | 噴水調大 | `SPRAY_RISE` 從 10 改成 14（加 40%）。水珠直徑 `SPRAY_DROP` 從 8 改成 12，等於半徑 ×1.5；貼圖的漸層和亮點也跟著等比放大，貼圖快取鍵改成 `amb\|drop12`。 | `client/src/render/ambientAnim.ts`、`client/src/render/ambientLayer.ts` |
| 3 | 站著的裝飾照 y 排序 | 圖層改成看資料的 `layer`，種類表 `DECOR_LAYERS` 在 Python 那邊：堆箱、晾衣繩是 standing；花壇、攤布、鋪法是 ground。<br>standing 的裝飾放在所在排（最下一列）的物件層，畫布往上多 1 格。結果是：站在北邊一排的人先畫，所以被擋住；站在同一排或南邊的人後畫，所以蓋住它。ground 的裝飾放在裝飾層，畫在人物下面。<br>**說明**：6V-3 其實已經把立著的裝飾放在物件層，所以實機的效果本來就對，前後截圖逐像素相同（第 3 節）。這段做的是讓圖層由資料決定，另外加了 `decorLayerOf`，並用測試鎖住順序。 | 同第 1 項 |
| 4 | 後牆掛件 | 6V-3 沒有數量上限：霧渡鎮鐵匠鋪會掛 3 個（工具板、掛燈、小窗），**不符合**。現在加了 `MAX_HANGINGS = 2`。<br>「不疊在擺設上方」6V-3 本來就有做到：掛件會避開擺設的欄，也會避開緊貼後牆的物件。<br>7 間室內的掛件數量如下：<br>- 霧渡鎮鐵匠鋪：3 → 2，少了 x=7 的小窗；<br>- 主城導師殿：1（照舊）；<br>- 其他 5 間：2（照舊）。 | `client/src/render/interiorArt.ts` |

## 2. 測試

**Python**：新的 `tests/content/test_field_decor_6v4b.py`，共 14 項，涵蓋：

- 種類表和站立／地面的標示；
- 正確的 schema；
- 8 個錯誤範例：不認得的種類、尺寸不符、非鋪法填了圓心、鋪法缺圓心、鋪法缺範圍、圓心不在範圍內、範圍是 0、未知欄位；
- 地圖層的檢查：超出地圖、兩件疊在一起、鋪法底下可以放花壇；
- 主城的版面和 6V-4 前端版面逐件相同；
- 只有主城有 decor；
- API 帶 decor 和 layer。

**規則雜湊**：`tests/content/test_field_buildings.py` 照舊通過，10 張圖的雜湊都沒變（主城是 `73a7cad0ebf4dfb6`）。

**其他 Python 檢查**：
- ruff check、ruff format --check、mypy src（517 檔）、lint-imports（13 條）全部乾淨；
- `trpg content check` 通過；
- 相關測試共 111 項通過：decor、buildings、6v2b look、6V-3 figures、openapi snapshot，以及 `tests/api/test_world_field*`。

**vitest**：新的 `client/src/world/decor6v4b.test.ts`，共 9 項：

- **讀資料後畫出來的結果和搬家前相同**：14 件的種類、位置、圖層、畫布高和全部畫法呼叫，加上鋪法的範圍、圓心、格子和每一列的畫法，做成 FNV 雜湊（`1f9081ed`、`92eb21cb`）。這兩個雜湊是開工前在 `71eb8352` 上用舊版 `CAPITAL_DECOR` 算的。
- 伺服器沒給 decor，或給了不認得的種類，就不畫；其他地圖也可以照資料放。
- **y 排序**：
  - standing 的裝飾在物件層、ground 的在裝飾層；
  - 用真的 `RowStack` 和 `SceneryLayer` 驗畫的順序：北邊一排的人比堆箱先畫，南邊或同一排的人比堆箱後畫；晾衣繩同理；花壇在同一排的人下面。
- **噴水參數**：`SPRAY_RISE` 14、`SPRAY_DROP` 12、貼圖的漸層半徑，以及水弧頂點高度照 `SPRAY_RISE`。
- **減少動態時靜止**：時鐘停在 0，噴水停在第 0 毫秒的樣子。
- **掛件**：各種室內、寬度 6～16、各種被佔的欄位，都最多 2 個，而且不在被佔的欄。

**改到的既有測試**：
- `plaza6v4.test.ts` 改用資料，種類名改成 `stall_cloth`、`crate_stack`；
- 7 個測試的 FieldView 夾具加上 `decor: []`；
- 新增共用夾具 `client/src/test/capitalField.ts`，照地圖檔組出主城的 FieldView。

**交件前的全量**：client 全部 vitest **234 檔、2560 項通過**（結束碼 0）；`corepack pnpm -C client build` 結束碼 0。

**noqa**：沒有新增。

## 3. 截圖（`docs/art/`，全部靜音：無頭 Chrome `--mute-audio`、網址 `?mute=1`）

| 檔案 | 內容 |
|---|---|
| `6v4b_01_plaza_before.jpg`／`6v4b_02_plaza_after.jpg` | 主城廣場。開了減少動態，逐像素比對**地圖完全相同**。唯一的差異是右上的時段字（晚→夜），因為兩張拍攝之間真實時間過了，和裝飾無關 |
| `6v4b_03_behind_crate_after.jpg` | 人物站在堆箱 [24, 9] 北邊的 [24, 8]，腳和身體下半被堆箱擋住。和 before 逐像素相同 |
| `6v4b_04_front_crate_after.jpg` | 人物站在堆箱南邊的 [24, 10]，蓋住堆箱。和 before 逐像素相同 |
| `6v4b_05_spray_zoom_before.jpg`／`6v4b_06_spray_zoom_after.jpg` | 許願池放大 3 倍，第 0 毫秒的靜止畫面。after 的水珠比較大、水弧比較高。逐像素比對時，差異只在噴水那一塊（234～276, 337～372） |

**拍法**：
- 伺服器是自己起的 `trpg serve --port 8388`，存檔和帳號放在 `scratchpad/v4b/`，設 `TRPG_LLM_GENERATE=false`、`TRPG_DEV_ROUTES=1`。
- 角色用 API 建立，用 walk 動作走到各位置。
- before 用 `71eb8352` 的 client 建置，after 用這段的建置，兩個輪流放進 `client/dist`，在同一個位置各拍一張。
- 比對時，在無頭 Chrome 的 canvas 裡逐像素比，沒有裝任何套件。
- 拍完後伺服器用工作 ID 結束，Chrome 都是自己 spawn 的程序。
- 沒用 8000、8001、8010、8333、5333 這幾個埠，也沒碰 `tmp_x`、`saves/`。

## 4. 待 PM 決定

1. **y 排序本來就對**：實機前後畫面相同，這段只做了「由資料決定」和測試。如果美術 PM 看到的「疊在上面」指的是人物**走到**堆箱那一格（裝飾不擋路，人物會畫在它上面），那就要改成擋路，屬於規則變動，不在這段範圍。
2. **霧渡鎮鐵匠鋪少了一扇小窗**（3 → 2）。這間沒有截圖；要看的話可以順手補拍。
3. **`look.decor` 目前只有主城在用**。其他城鎮要不要加裝飾，是內容的工作（改 yaml 就可以，不用改程式）。
4. **前端測試的種類表**：`client/src/test/capitalField.ts` 裡抄了一份 Python 的 `DECOR_LAYERS` 和 `DECOR_FIXED_SIZE`，只在測試裡用。執行時一律用伺服器給的 `layer`、`width`、`height`。
5. **原型數值**，照指示做完：`SPRAY_RISE` 14、水珠直徑 12、掛件上限 2。

## 5. commit（worktree 分支）

- `df2541b2` Python：`look.decor` schema、主城版面、API、OpenAPI
- `b1b5207a` client：讀資料、y 排序圖層、噴水、掛件上限、測試
- 最後一個 commit：截圖與這份報告
