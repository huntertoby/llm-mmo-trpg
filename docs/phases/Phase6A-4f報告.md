# Phase 6A-4f 報告：6A-4c／6B-5 驗收收尾

實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6A-4f 列。依據：`docs/art/6B-5與6B-6與6A-4c檢查.md` 第 4、5 節、`docs/art/HUD功能列圖示.md`、`docs/art/sample/hudIcons.js`。

開工先合併 `main` 與 `origin/claude/art-pm-8f4e6d`（只有 docs/），沒有衝突。沒有新增相依，沒有改既有結算（`LOG_FORMAT` 不變）。

## 1. 交付

| 項目 | 內容 |
|---|---|
| 後端 | `engine/path_preview.py`：`SlipRun` 與 `PathPreview.slip_runs`；`api/path_schemas.py`：`SlipRunOut`、`PathPreviewOut.slip_runs`；OpenAPI 與 `schema.d.ts` 重產 |
| 前端：小牌 | `battle/pathPreview.ts`（合併小牌、虛線段）、`render/pathArt.ts`（只改一行：虛線改看 `seg.dashed`） |
| 前端：HUD | 新增 `world/HudBarIcons.tsx`（8 個定稿圖示）；`world/WorldHud.tsx`（功能列、影子鈕、地圖鈕換圖示，加按鈕狀態與說明卡）；`world/hud.ts`（`buttonState`、`hudButtonCard`）；`ui/Hint.tsx`（加選用的 `rich` 內容）；`styles/world-hud.css` |
| 測試 | `tests/engine/test_path_preview.py`、`tests/api/test_path_preview_api.py`、`client/src/battle/pathPreview.test.ts`、`client/src/world/hud.test.ts` |
| 截圖 | `docs/art/6a4f_ice_trap.jpg`、`docs/art/6a4f_hud_bar.jpg` |

## 2. 做法

**path-preview 的連續冰面段（`slip_runs`）**
- 把路徑上連續有滑倒檢定（`slip_check`）的格子合成一段，依路徑順序列出。
- 每段給：`start`／`end`（index）、`start_pos`／`end_pos`、`tiles`、`chance_permille`、`fail_stops`、`status_id`。
- `chance` 是整段「至少滑倒一次」的機率：各格不滑倒的機率連乘，用 `Fraction` 精確計算；API 換成 ‰ 四捨五入。
- 各格的機率取自原本的模擬事件，不另外擲骰，也不改狀態與 `rng_state`。
- `fail_stops` 是段內滑倒時可能停的格子，依路徑順序、不重複。倒在其他單位的格子上時，是滑回去的最近空格（規則同 `battle._slide_back_if_stacked`）。
- 只加欄位，原有欄位的意思不變。

**測試**
- 兩格冰：窮舉兩次 d20 共 400 種組合實際走一遍，滑倒的比例等於 `chance`，實際停點的集合等於 `fail_stops`。
- 第二格冰上站著友軍時也測一次：停點只剩第一格。
- 另外測：段會在一般地面斷開、冰後面的陷阱格是 `possible`、沒有冰時沒有段、預覽前後狀態與亂數不變。
- API：開闊平原放兩格冰，回應的段與引擎的精確值一致。

**小牌**
- 每段冰只出一張小牌，掛在第一格冰上。
  - 兩格以上：「冰 N 格・滑倒 xx%・失敗停在那格」。
  - 只有一格：照 6A-4c 已通過的寫法「滑倒 xx%・失敗停在這格」。
  - 有百分比的小牌都不加「（可能）」。
- 陷阱格在某段冰的第一格之後時：
  - 小牌的「陷阱」和陷阱造成的狀態不加「（可能）」；
  - 走進那格的紅線改成紅色虛線（`PathSeg.dashed`）。
- 小牌實際畫的位置照 6A-4c 的避讓（`placeTags`），會為了不重疊而稍微移開。

**HUD 功能列**
- `hudIcons.js` 的 8 個圖示照同一套畫法移植成 48×48 的 SVG：
  - 外形先依名字當種子抖動，再用二次曲線圓滑；
  - 墨線畫兩層，暗面斜線只畫在填色區塊裡；
  - K 的寶石、M 的藍點有光暈。
- 功能列 7 顆鈕用 I K G J Y N R；左上的影子鈕用 Y，右上的地圖鈕用 M。舊的靴子圖示不再用在功能列。
- 按鈕狀態：
  - 滑過：亮一點的邊加光暈；
  - 開著：金底、亮金邊；
  - 停用（沒有資料開不了，例如還沒存影子）：圖示變灰、半透明；
  - 未讀的數字與點沿用 6B-5。
- 說明卡沿用 `Hint`（加了選用的 `rich` 內容），內容依序是：
  - 標題列：圖示、名稱、快捷鍵方塊；
  - 黃字的目前狀態；
  - 說明一句；
  - 觸控小字。
  - 樣式是深底、金邊、圓角 10、寬約 250。

## 3. 測試結果

- `pytest tests/engine/test_path_preview.py tests/api/test_path_preview_api.py tests/api/test_openapi_snapshot.py`：27 項通過。
- `ruff check .`、`ruff format --check .`、`lint-imports`（13 kept）都通過。
- `mypy`：我改的檔沒有錯誤。有 1 個錯誤在 `tests/world/test_field.py:92`，是 main 上 6C-1 帶進來的，我沒有動那個檔。
- vitest：
  - `src/battle/pathPreview.test.ts`、`src/world/hud.test.ts`：96 項通過；
  - 加上 `src/world` 全部與 `src/ui/Hint.test.ts`：228 項通過、1 項失敗。
  - 失敗的是 `floatCardRule.test.ts` 的「`role=dialog` 的面板都在白名單」，原因是 `WorldHud.tsx` 本來就有 `role="dialog"`（6B-5 的面板），這段之前就會失敗，不是這段造成的。
- `tsc --noEmit`、`pnpm build` 都通過（只有原本就有的 chunk 大小警告）。
- swamp 種子 7 重播通過：88 個動作、313 個事件。

**截圖做法**
- 用 scratchpad 裡的腳本開本機伺服器（不進版控），埠 8300，存檔放暫存資料夾。
- 腳本照常 `create_app`，每場開局後在主角東邊放兩格冰，冰後一格放一個已揭露的敵方陷阱。
- 路徑預覽照樣由引擎算。
- 用完已停掉伺服器；沒有碰 `saves/`、`tmp_x`。

**截圖內容**
- `6a4f_ice_trap.jpg`（800×600）：
  - 一張小牌「冰 2 格・滑倒 80%・失敗停在那格」；
  - 冰後的陷阱段是紅色虛線，陷阱小牌是「陷阱 −6」。
- `6a4f_hud_bar.jpg`：
  - 1100×720 的畫面縮到 800 寬輸出；
  - 霧渡鎮的功能列是定稿圖示，滑過背包時出現說明卡「0 / 30 格・金幣 0」。

## 4. 待 PM 決定（都已照最保守的做法做完）

1. **冰後陷阱的傷害範圍與定身拿不到**：
   - 伺服器只做兩次模擬。「最多後果」那次在第一格冰就滑倒停下，走不到陷阱；「最少後果」那次會走到陷阱，但傷害骰取最小、抵抗成功。
   - 所以冰後的陷阱只有最小傷害，也沒有定身。目前畫面照伺服器給的寫「陷阱 −6」，不寫「−6～14・定身」。
   - 要照樣張寫完整，引擎得多做一次「冰面檢定有利、其他骰子不利」的模擬，要改 `battle.simulate_preview`，超出這段的範圍，所以先不做。
2. **單格冰的寫法**：照 6A-4c 通過的「滑倒 xx%・失敗停在這格」；兩格以上才寫「冰 N 格・……那格」。
3. **「冰後面」的範圍**：陷阱在某段冰的第一格之後（包含陷阱就在第二格冰上）都算。只拿掉陷阱本身和陷阱狀態的「（可能）」；藉機攻擊等其他小牌照舊。
4. **整段機率不算其他打斷**：例如冰前先被藉機攻擊擊倒的情況不計入（引擎註解有寫）。
5. **潛行鈕（R）**：潛行還沒開放（6C-5），按鈕用一般狀態，說明卡狀態行寫「尚未開放」；「開關開著」的樣式等功能做好再接。
6. **說明卡的狀態行**：只用現有資料。
   - 背包：格數・金幣；
   - 技能：角色階級；
   - 成長：可花的點；
   - 任務：進行中幾條；
   - 影子：新戰報幾則，或「還沒存影子」；
   - 留言：所在地點名。
   - 「新技能」數字、留言未讀數一樣沒有資料。
7. **暗面斜線**：照樣張在 SVG 裡用 clipPath 畫；在 46px 的鈕上幾乎看不出來。
8. **地圖鈕、影子鈕**：也換成定稿的 M、Y（樣張列了 8 個圖示）。其他地方（任務追蹤、浮動提示）的小圖示沒換。

## 5. Commit

- `d2bd8323` feat(engine): path preview merges consecutive ice into slip runs (6A-4f)
- `77de19cc` feat(client): merge consecutive ice into one path tag, dashed trap after ice (6A-4f)
- `72504f4b` feat(client): final HUD bar icons, button states and hover cards (6A-4f)
- `c8251e76` style(client): HUD bar hover card frame; 6A-4f screenshots
