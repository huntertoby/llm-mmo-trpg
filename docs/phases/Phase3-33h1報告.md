# Phase 3-33h1 報告：召喚物外觀渲染器

規格：`docs/phases/Phase3計畫.md` 36.4；美術：`docs/art/召喚物外觀.md`「定案」以下、`docs/art/sample/summonArt.js`、`docs/art/summons.png`。

## 做了什麼

1. **資料（後端）**
   - `UnitTemplate` 新增選填欄位 `look`（`SummonLook`：`body`、`variant`、`element`、`size`、`trait`；`body` 限六種、`size` 限三種，其餘為 snake_case 字串）。只有召喚物（`summon: true`）可以填。
   - 現有 4 個召喚物範本（骷髏戰士、元素之靈、戰意圖騰、殘影分身）照美術表填好。
   - `content/summon_looks.yaml`：17 種的完整外觀表（含尚未存在、3-33e1／e2 才新增的 13 種），附 `SummonLookTable`／`load_summon_looks` 與 pydantic 驗證；新增召喚物時照填即可。
   - `UnitView.summon_look`（`SummonLookView`）：`element` 已套用灌注（有灌注關鍵字用該關鍵字，否則用範本預設）。OpenAPI 與 `schema.d.ts` 已重產。
2. **渲染（前端 `client/src/render/summonArt.ts`）**
   - 五種新體型（漂浮靈、構造體三款、野獸兩款、植物、圖騰三款）移植自樣張，畫到離屏後加 8 方向深色外框，與紙娃娃同尺寸、同腳底位置，所以整格抬高、遮擋剪影、陣營底圈、剩餘輪數徽章、血條、狀態徽章都沿用原本流程。
   - 人形四款（骷髏、影魅、殘影、守護靈）用紙娃娃，依款式合成透明度、色調、外光；殘影複製召喚者外觀（`UnitDraw.copyOf`，找不到召喚者時用預設戰士）。
   - `resolveSummonLook`：不認得的體型退回人形骷髏；不認得的款式退回該體型的預設款；不認得的元素用預設灰白；不認得的大小用 medium；不丟例外。
   - 元素色票沿用樣張，ID 換成 `skill_keywords.yaml` 的正式 ID（`charged`、`frozen`、`collision`、`marked`、`high_ground`、`concealed`…）。
   - `ArtTextures.summon()`：貼圖快取鍵 ＝ 外觀＋朝向（殘影另加召喚者外觀鍵）。
   - 土牆（`wall`）不畫陣營底圈與朝向尖角。倒地的人形召喚物沿用紙娃娃躺下姿勢；其他體型不躺下。
   - 沒有 `summon_look` 的召喚物（舊資料）走原本的畫法，行為不變。
3. **開發用一覽頁**：`client/summon-gallery.html`＋`client/src/dev/summonGallery.ts`（用真正的 `BattleRenderer` 畫：17 種 × 4 朝向、整格抬高與遮擋剪影、不認得的值；網址 `#south／north／east／west／height／unknown` 只顯示該段）。不屬於正式 build。

## 測試

- vitest：`render/summonArt.test.ts`（約 2 萬組全組合含不認得的輸入不丟例外、退回骷髏與各層退回、四元素靈畫法不同、背面不畫眼睛、野獸朝向鏡像、鷹隼抬高、土牆無底圈、快取鍵、人形款式、無 DOM 回傳 null）、`battle/summonLook.test.ts`（繪製模型帶出外觀與殘影複製對象）。
- pytest：`tests/content/test_summon_looks.py`（17 種載入、現有範本與外觀表一致、元素都是正式關鍵字、不認得的體型被拒、非召喚物不能填 `look`）、`tests/api/test_summon_api.py`（視圖帶出 `summon_look`）。
- 驗收指令結果：見下方「驗收」。

## 美術檢查清單對照

截圖都在 `docs/phases/img/`（因截圖工具輸出 PNG，副檔名為 `.png`）：`3-33h1-south.png`、`-north.png`、`-east.png`、`-west.png`（17 種 × 四朝向，含戰士對照）、`-height.png`（整格抬高與遮擋）、`-unknown.png`（不認得的值）。

| # | 項目 | 結果 |
|---|---|---|
| 1 | 17 種在 52px 格子裡可辨認；四種元素靈一眼分得出元素 | 達成（south 圖：火靈火焰、冰靈冰晶、雷靈閃電、水精水滴與腳下水窪；17 種各自成形）。是否與 `summons.png` 逐項一致請美術 PM 目驗 |
| 2 | 四個朝向正確，背面沒有眼睛 | 達成（north 圖：漂浮靈、石像、傀儡、圖騰、狼、鷹隼皆無眼睛；west 圖狼與鷹隼左右鏡像；南北沿用東側側面）。另有 vitest 檢查 |
| 3 | 鷹隼影子在地上、身體抬高；藤蔓貼地；土牆沒有底圈 | 達成（south／height 圖；土牆格沒有底圈與朝向尖角） |
| 4 | 半透明、外光（影魅、殘影、守護靈）不影響陣營底圈與徽章清晰度 | 達成（透明度只套在小人貼圖，底圈、徽章、血條另層，截圖中仍清楚） |
| 5 | 不認得的體型、元素、大小都退回預設，不壞 | 達成（unknown 圖：未知體型、空體型 → 骷髏；未知款式 → 狼；未知元素 → 灰白靈；未知大小 → medium；沒有外觀欄位 → 骷髏） |
| 6 | 與整格抬高（3-19）、遮擋剪影相容 | 達成（height 圖：高台上的召喚物一起抬高、上排被擋住時畫虛線剪影）。截圖用一覽頁的真實 `BattleRenderer` 畫面，沒有用實戰（目前實戰只有 4 種召喚物，其餘 13 種要等 3-33e1／e2） |

未達成：無。限制：「殘影複製召喚者外觀」在一覽頁用的是沒有裝備的 `hero_fighter` 範本（半透明淡藍的戰士），未在真實戰鬥中截圖（殘影需要規則改變「殘影」觸發才會出現）。

## 驗收

- `uv run ruff check .`、`ruff format --check`、`mypy`、import-linter：通過。
- `corepack pnpm -C client build`：成功（只有既有的 chunk 大小警告）。
- vitest：全過（68 檔 715 測試）。
- 全量 pytest：4375 通過（`check.py` 第一次跑時有 1 個失敗，是新驗證器順序蓋住了圖騰的錯誤訊息，已修正；修正後 ruff／mypy／vitest／build 與全量 pytest 重跑通過，因此 `check.py` 是分段跑完而非單次全過）。

## 待 PM 決定

1. **`element` 欄位的語意**：實際顯示以灌注關鍵字為先、沒有灌注才用範本預設。元素之靈（通用的靈）沒有預設元素，所以沒灌注時是灰白色；若要它依施放者持有關鍵字上色，是 3-33e1 新增 4 種元素靈時一併處理。
2. **外觀表與範本的重複**：17 種外觀放在 `content/summon_looks.yaml`，現有 4 個範本也各帶 `look`；兩者由 pytest 比對一致。3-33e1／e2 新增召喚物時要兩邊都填，或之後改成範本引用表（建議 3-33h2 一併決定）。
3. **特徵 `trait` 的合法值未列舉**：後端只驗格式，前端認得 `puddle`、`shield`、`fuse`、`flying`、`aura`（會影響畫法）與 `translucent`、`glow`、`no_ring`、`ground`（目前只作標記；透明度與外光依款式固定，`no_ring` 實際以款式 `wall` 判斷）。新增 `trait` 值前請先確認前端。
4. **圖騰舊畫法**：有 `look` 的圖騰改用新畫法；`totem: true` 但沒有 `look` 的仍是舊的通用圖騰柱。
5. **畫在 64×64 貼圖內**：新體型最高約 47px（高台圖騰、戰意圖騰旗），與紙娃娃（約 46px）相當；第 0 排的高個子頂端靠近畫面上緣（與既有單位同樣處理）。若美術 PM 覺得擠，需要調整預留。
6. **剩餘輪數徽章**遮住漂浮靈的上緣（徽章位置照舊在右上角）；是否移位交美術 PM 判斷。
7. **預覽伺服器**：`preview_start` 只認得主專案的 `.claude/launch.json` 且會重用使用者的伺服器，所以截圖改用本 worktree 自己啟動的 vite（埠 5199），截完已關閉；沒有動使用者的 8000／8001／8765。
