# Phase 5F-ART1 完成報告：大十字圖示＋霧影外觀

實作者 agent，2026-11-03。範圍：`Phase5計畫.md` 第 1 節 5F-ART1 列；需求文件 `docs/archive/art/大十字圖示.md`、`docs/archive/art/霧影外觀.md`。

## 併入美術 PM 的 commit

- 753c517d（大十字需求）、bc168013（霧影需求）：cherry-pick 進來（a6f20629、e49f3df4）。
- 4df27344（熔核）：cherry-pick 後是空的，因為 main 早就有這個內容（`敵人外觀.md` 熔核蛞蝓、熔爐母獸已加 `core`），所以跳過。這個 commit 只改美術文件和樣張，content 裡也還沒有熔岩區的敵人，沒有東西要移植。

## 大十字圖示

- 後端：`IconSegment` 加上 `arm: int | None = None`，照 `range` 的方式從形狀帶出（只接受整數、不接受 bool），其他情況給 `None`。技能卡片透過 `icon.segments[].arm` 帶出，`SkillCard.shape` 文字不用改。OpenAPI、`schema.d.ts`、`skill_icons.json` 都重產了。
- 前端 `skillGlyphs.ts`：
  - 新增 `normalizeArm()`：不是 ≥ 1 的整數一律當 1，包括缺欄位、0、負數、非整數、NaN 和字串。
  - 新增 `gridLayout()`：十字且 arm ≥ 2 時畫 5×5，cs 11、gap 2、總寬 63，亮中心列和中心行共 9 格；其他情況維持 3×3（cs 19、gap 3）。
  - 5×5 的圓角是 2；星形半徑改成 5.6／11.9，元素符號縮成 0.63 倍（都是原本的 0.7 倍）。
  - `MotifSpec.arm` 是選填欄位，由 `drawMotif` 傳到 `grid()`。
- `skillIcon.ts`：`partsOf` 會把 arm 帶進 motif。`shapeTile` 的 id 結尾加上 `|arm`。arm ≥ 2 的十字，說明文字改成「技能的作用範圍，臂長 2」。
- 戰場預告：格子本來就是用伺服器給的實際格子畫，程式沒改，瀏覽器確認是 9 格（見下方）。
- 方陣、環，以及 arm 1 的十字（leap_slam 等）完全沒變，由測試鎖住。

## 霧影外觀

- `summonArt.ts`：
  - 人形款式加上 `mist_shade`。
  - 新增 `copiesOwner()`，afterimage 和 mist_shade 都會複製召喚者。`summonKey`、`artTextures.ts`、`drawModel.ts` 的 `copyTarget` 都改用它。
  - `humanoidSpec` 的 mist_shade 分支：用召喚者的紙娃娃，並去掉 `rarity`，所以頭目的外光不會跟著複製過來。
  - `HUMANOID_STYLE.mist_shade = { alpha: 0.55, tint: "#dfe4e2", fade: 14, ground: false }`，不設 glow。
  - 合成完後用 `destination-in` 疊一條直向漸層：腳底（`DOLL_FOOT_Y`）是 0，往上 14 單位變成 1。
- `paperdoll.ts`：`renderFigureCanvas`、`drawFigurePose` 加上選填參數 `ground = true`。霧影傳 false，就不畫紙娃娃自己的地面影子。其他呼叫端不受影響。
- 內容：`content/summon_looks.yaml` 的 `mist_shade` 列改成 `variant: mist_shade`。`variant` 本來就是任意 ID，schema 不用改。前端遇到不認得的款式會退回骷髏，有測試。
- 金環、金菱形、詞綴粒子：前端目前沒有任何程式在畫這些精英記號，`copyOf` 也只帶紙娃娃欄位，所以霧影本來就不會帶到。
- 玩家自己的殘影：`afterimage` 的樣式沒動（藍色調、藍色外光、有影子），有測試鎖住。

## 測試

- `skillIcon.test.ts` 新增「大十字圖示」5 項：
  - 5×5 的版面、亮 9 格、總寬 63；
  - 其他形狀不受 arm 影響；
  - 不合法的 arm 當 1，roundRect 畫 9 格或 25 格；
  - 霧鎖千山第二段是 arm 2、畫 25 格，leap_slam 仍是 9 格；
  - shapeTile 的 id 和說明文字。
- `summonArt.test.ts` 新增 3 項：
  - 款式解析、`copiesOwner`、快取鍵帶召喚者、去掉 rarity；
  - 樣式值；
  - 用假的 document 驗貼圖：霧影有 `destination-in`、漸層座標是腳底到往上 14 單位、alpha 0.55、色調 `#dfe4e288`、沒有 shadowBlur、沒有影子筆觸；殘影仍有藍色外光和影子。

## 交件前檢查（已 `git merge main`，合併到 ce9776fd 5F-4b）

| 項目 | 結果 |
|---|---|
| ruff check、ruff format --check | 通過 |
| mypy（1202 檔） | 通過 |
| lint-imports | 13 kept、0 broken |
| pytest `tests/api tests/content tests/narrative`（-n 8） | 2902 通過、2 失敗，都是 main 本身的問題，見待 PM 決定 1 |
| vitest | 140 檔、1294 項全部通過 |
| `pnpm build` | 通過 |
| 重播 swamp 種子 7 | 通過（88 動作、313 事件） |
| OpenAPI／`schema.d.ts`／`skill_icons.json` | 合併 main 後重產，`skill_icons.json` 因 main 的新技能又變了 1 行，已另外 commit |

## 瀏覽器驗證（8220 埠、自己的分頁 tab-17，驗完已關分頁、停伺服器）

做法：開單場戰鬥。在頁面裡暫時包一層 `fetch`（只用來檢查，不改原始碼），讓 `POST /api/battles` 的地圖換成雲頂觀，並用 `custom_skills` 把霧鎖千山和霧影分身裝到主角身上。開局前先 `localStorage.clear()`。霧中劍客只會出現在世界懸賞遭遇裡，所以這次的霧影是主角召出來的，複製的是主角的紙娃娃。

截圖描述：

1. **技能卡（1600×900、800×600）**：滑過霧鎖千山出現技能卡，組裝算式的第二段是「範圍＋十字＋傷害＋定身」。把十字小格放大來看，是 5×5，亮中心十字 9 格，其餘 16 格是空心框，中心的小星形沒有蓋到旁邊的亮格。滑到十字小格，說明文字是「技能的作用範圍，臂長 2」。800×600 時卡片完整顯示在技能列上方。
2. **戰場預告**：
   - 施放前的預覽寫「目前預計影響 9 格（紫色）」。主角在地圖邊緣時會寫 8 格，因為下臂超出地圖。
   - 施放後，地圖上的紫框加「蓄」字是一個臂長 2 的十字，中心 1 格加四臂各 2 格，共 9 格。
   - 右側的環境預告寫「冒險者 正在蓄力「霧鎖千山」：下回合開始時釋放，以自己為中心影響 9 格」。
3. **霧影（800×600 放大到 300%）**：
   - 霧影就在主角旁邊，是主角紙娃娃的月白色半透明版本，偏灰白，和殘影的藍色分得開。
   - 沒有外光；小腿以下漸漸淡掉，看不到腳和地面影子。
   - 腳下只有召喚物原本就有的陣營底圈和剩餘輪數徽章。
   - 主角本體的腳是實的，有影子。
   - 1600×900 時內建瀏覽器的面板會縮小畫面，霧影只看得出淡色人形，細節以 800×600 的放大圖為準。
4. `__layoutSmoke.scan()`：800×600 下做了兩次（召喚後、施放後），1600×900 下也做了兩次（技能卡開著、放大地圖後），四次都回 `[]`。

## 待 PM 決定

1. **main 本身有 2 個測試失敗，不是這段造成的**，兩個都來自 5F-3 的 77dc4093：
   - `tests/narrative/test_card_text_scan.py::test_every_skill_tag_has_a_chinese_name`：技能標籤 `dot` 沒有中文名。
   - `tests/narrative/test_rule_texts_41c.py::test_status_descriptions_hold_no_hard_coded_numbers`：狀態 `rift_collapse` 的說明裡有「加倍」。
   - 我沒有修，因為不在這段範圍內。建議由開發 PM 另外處理。
2. **形狀小格的說明文字**：規格只寫要寫出臂長 2。我用「技能的作用範圍，臂長 2」，只用在 arm ≥ 2 的十字；arm 1 的十字維持「技能的作用範圍」。用逗號而不是括號，是因為外層 `tileTitle` 已經會加一層括號。
3. **霧影的「霧隱的」透明度**：規格說本體的 75% 不透明不要疊上去。目前本體的透明度本來就不會經 `copyOf` 帶到霧影，所以沒有另外處理。但如果之後霧影自己被施加隱匿狀態，`applyLook` 仍會照一般規則乘上隱匿的透明度。我採保守做法，不另外排除。
4. **倒下的霧影**：照規格沿用召喚物現有的處理。倒下時用的是範本 `summon_mist_shade` 的紙娃娃，不是召喚者的外觀，和殘影倒下時一樣。

## Commit

a6f20629、e49f3df4（美術需求）→ 3ee68c66（大十字）→ 8ab942b6（霧影）→ 49e3bd85（merge main）→ 重產夾具 → 文字換行 → 本報告。沒有 push。
