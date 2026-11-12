# Phase QI-2d 報告：Q 版技能圖示補圖（部件補圖＋7 個新道具＋19 招 `icon_prop`）

> 實作者（Opus 5.5），2026-11-12。規格：`docs/phases/PhaseQI-2d計畫.md`（第 0.0 節開發 PM 定稿）。起點 main `493965a8`（含 QI-2c 合併 `ecbf8964`、QI-3a 合併 `e03b8d76`）。未 push。
> 平行邊界：`statusIcon.ts`、`statusFrame.ts`、`qIcon/status.ts`、`skillIcon.ts`、`unitSprite.ts`、`ui/statusCard.ts`、`ui/StatusCardParts.tsx`、`dev/statusGallery.ts` **都沒動**（`git diff --stat 493965a8..HEAD` 確認）；`skillParts.ts` 只改 `modifierTargetPart` 的回傳（加 `q`）與檔頭一行註解，`hooks.status` 掛法沒動。`qIcon/core.ts`、`weapons.ts`、`content/skill_icon_art.yaml` 沒動。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| F1 主圖 | `qIcon/skills.ts`：照 `git diff 20a6fd39~1 379812dd -- docs/art/sample/qIconsSkills.js` 逐行搬 `LIQUID`、`hornPt`／`hornSide`、`THINGS` 7 個（瓶、煙霧彈、吼聲、靴、肩撞、獠牙、黏液，第 2 版）、`MOTION.shot` 的 `noTail`、`dashV`（`ACT.dash` 改呼叫它）、`TIP_KINDS`／`HEAD_KINDS` 新成員、`propOf` 的 `thing` 分支（排在飛刃與武器解析之前）、`ramDash` 擺位與 V 換色、黏液配右上記號的擺位與 `markK` 0.92、瓶配地面效果換液體色、`info()` 的 `!P.thing` 與 `noTail`、`list()` 的 7 列（放最後）、export `THINGS`。靴的 `M.leather` 用 `core.ts` 的 `M`（＝`material.ts`）。檔頭「和樣張不同」補型別調整 | `7fa9deec` |
| F2 部件 | `qIcon/parts.ts`：照 `git show 7b6db8dc -- docs/art/sample/qIconsParts.js` 逐行搬 `minus`、`soulRings`（export）、`EFFECT.redirect_damage`（雙環）、`CHANGE.summon_limit_delta`（讀 `opt.value`，負＝減號；沒有值當 +1）、`CHANGE.form_upkeep_permille`（`up()`＋右下沙漏）、`bowArrow`、`cardFan`、`TARGET` 13、`TARGET_TAG`、`targetOf`、`CATS`／`CAT_ZH`／`RING` 加 `target`（放最後）。`TARGET.tag_shout` 呼叫 `QS.THINGS.roar`。`status.ts` 不動 | `7fa9deec` |
| F3 改造對象接線 | `skillParts.ts::modifierTargetPart` 回傳多 `q: { cat: "target", id: QP.targetOf(applies) }`——和 2c 接其他部件同一條路：`drawChip` 給 `unitPx` 時走 `QP.chip`（圓底、色環照呼叫端給的 `CORE_RING` 白 `#ffffff`、圖樣＝直徑 78%、`blit` 對齊）。`label`、`note`、`color`、`cat`、`key` 一字不改（T-D7）。舊 `draw` 留著（見第 8 節第 1 點） | `8c208228` |
| B1 允許清單 | `content/skill_icon_props.yaml` 在 `w:kunai` 後加 17.7 的 7 列；檔頭 57 → 64、分節註解「（2＋11-12 補 7）」 | `1104e1f6` |
| B2 19 招 | 8 招 `icon_prop: "w:fist"` 改值、11 招在 `weapon_req` 下一行插入（腳本做，只動那一行）。`trpg content check`：660 個檔、402 個技能通過 | `1104e1f6` |
| B3 快照 | 重產 `skill_icons.json`、`skillCards.json`；`export_openapi.py`＋`gen:api` 0 差異（第 4 節） | `1104e1f6` |
| B4 後端測試 | 新 `tests/content/test_icon_prop_qi2d.py`（T-D1～T-D3、T-D9、T-D10，69 項）＋既有 3 檔改寫（第 3 節） | `1104e1f6` |
| F5 前端測試 | 新 `render/qIcon/qIconQi2d.test.ts`（T-D4～T-D8、T-D11＋開工前基準，16 項）、基準檔 `render/fixtures/qi2dBaseline.json`；`qIconSkills.test.ts` 改寫（第 3 節） | `7fa9deec`、`2cebda7c` |
| F4 開發頁 | `dev/skillIconGallery.ts`：`set=target`（13 個 Q 版＋現行對照）、`set=qi2d`（19 招、`&before=1` 2c 後的道具、改過的部件與狀態卡「靈魂連結」對照，`&ppx=`）；`__qiSkillDev` 加 `oldTarget`、`statusCard`、`before`；檔頭參數說明同步 | `f94167b9`、`d69e5c31` |
| F6 比對與截圖 | 第 5 節；`docs/art/shots/qi2/2d-*` 8 張 | `20698ff1` |
| R1／R2 | 本報告、兩份上手筆記 | 本 commit |

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| 8.1-1 | 第 7 節測試 | 過。後端 `tests/content/test_icon_prop_qi2d.py` 69 項：T-D1 `test_allow_list_has_the_seven_new_neutral_props`；T-D2 `test_nineteen_skills_have_the_new_values`（19）、`test_counts_of_fist_and_new_values`（`w:fist` 恰好 5 招、新 7 值恰好 19 招）；T-D3 `test_new_props_are_not_bound_to_a_weapon_class`（7 值 × melee／ranged／focus／any 各配一招實際技能，28）；T-D9 `test_derivation_only_swaps_the_prop`（19：`prop` 換新值，換回舊值重算的 motion／act／tint／spark／elements 與改後相同且等於第 6 節「改前」欄）；T-D10 `test_battle_replay_parametrization_covers_the_new_eleven`（`test_icon_prop_battle_ip1.py` 參數化 36 → 47、新填 11 招都在）。前端 `qIconQi2d.test.ts` 16 項：基準 2 項（全部部件除分擔傷害、形態維持消耗外呼叫紀錄＝開工前；402 招主圖只有 19 招變）；T-D4（`EFFECT.redirect_damage.d === QP.soulRings`，與 `status.ts` `NEW.soul_link` 在 tiny／small × 有無外框 4 種 `QOpts` 下全域呼叫紀錄逐筆相同）；T-D5 三項（+1／沒有 value 的呼叫紀錄雜湊＝開工前；−1 只有橫槓；`form_upkeep_permille` −500 `scale(1,-1)`＋`#6ae0ff`、+500 `#ffb23a`、兩者都有 `translate(6.4,6.6)` 的沙漏 `#8ab8f0`；精英召喚 −1、群召 +1、化形專精 −500 照實際值）；T-D6 兩項（13 代碼合成＋`weapon_skills: true`→`default`；fixture 全部 18 招修正技＝本段前分支；重踏 `tag_push`、震懾餘波 `tag_shout`、召喚兩招 `tag_summon`）；T-D7 兩項（18 招修正技的五欄＝開工前錄的基準；組裝列 `drawChip`（unitPx 0.3／0.18 × res）呼叫紀錄＝`QP.chip("target", targetOf(…))`、白環）；T-D8 四項（7 個 `THINGS`、`thing` 分支、`list()` 的中性 7 列；瓶／元素道具射出有彗尾、弓沒有、黏液沒有；瓶配地面效果記號＝琥珀 `#f0b030`、靴不換；肩撞配衝刺 `markK` 0.72、V 用 dim／soft、靴照舊 `#ffe9a8`）；T-D11 兩項（19 招 × main 24／28／40、mid 48／56、full 96 × res 1、2，13 改造對象＋4 部件（含正負）× 18／30 × res 1、2：每個貼圖不縮放、左上角在整數裝置像素；畫兩次相同） |
| 8.1-2 | 後端 | `trpg content check` **0**（660 個檔、402 個技能）；`ruff check .` **0**、`ruff format --check .` **0**、`mypy` **0**（1456 檔）、`lint-imports` **0**（14 kept）；`trpg battle --map open_plain --seed 7 --log-json …` **0**＋`trpg battle replay` **0**（91 個動作、383 個事件，最終狀態一致） |
| 8.1-3 | 合併前 slow | 見第 2.1 節 |
| 8.1-4 | 前端三個結束碼、快照 | 見第 2.1 節 |
| 8.1-5 | `git diff --stat 493965a8..HEAD` | 只有：`client/src/render/qIcon/skills.ts`、`parts.ts`、`render/skillParts.ts`、`dev/skillIconGallery.ts`、`render/fixtures/skill_icons.json`、`ui/fixtures/skillCards.json`、新 `render/fixtures/qi2dBaseline.json`、新 `render/qIcon/qIconQi2d.test.ts`、`render/qIcon/qIconSkills.test.ts`、`content/`（20 個檔）、`tests/content/test_icon_prop_qi2d.py`（新）、`test_icon_prop_ip1.py`、`test_icon_prop_d4_qi2a.py`、`tests/narrative/test_skill_icon_art_qi2a.py`、`docs/art/shots/qi2/2d-*`（8 張新檔）、本報告、兩份上手筆記。`core.ts`、`weapons.ts`、`status.ts`、`skill_icon_art.yaml` 沒動 |

### 2.1 交件前的結束碼

在 `20698ff1`（程式最後一個 commit；之後只加文件）上依序跑：
- 合併前 slow：`UV_NO_SYNC=1 uv run pytest -q -n 8 -m "not llm" tests/skillgen/ tests/narrative/ tests/content/ tests/api/`（`-m "not llm"` 蓋掉預設的 `not slow`，含 slow）→ **0**（9295 passed、15 skipped，4 分 24 秒）。沒有既有失敗，不用在起點對照。
- `UV_NO_SYNC=1 uv run pytest -q tests/cli/test_output_snapshots.py -m slow` → **0**（24 passed、1 deselected）；CLI 快照沒有重產。
- `corepack pnpm -C client typecheck` → **0**
- `corepack pnpm -C client test` → **0**（296 檔、3694 項；含 `inkDollSnapshot`、`creaturePose`、`qi2cStatusUnchanged`）
- `corepack pnpm -C client build` → **0**（只有既有的 chunk 大小警告）
- `export_openapi.py` → `gen:api` → `git status` 沒有變動；跑完全部後 `render/__snapshots__/`、fixtures 都沒被改。
- 開發中跑的相關後端測試（規格第 9 節清單＋新檔）：15 檔 284 項＋69 項過。
- 自己啟動的 vite（5295）、靜態伺服器（8144）、`trpg serve`（8146）、無頭 Chrome（CDP 5299，`--user-data-dir` 在暫存區 `qi2d/chrome-profile`）都用自己的工作 ID／PID 關掉，四個埠都沒在聽。

## 3. 改寫的既有測試（舊 → 新，不放寬）

- `tests/content/test_icon_prop_ip1.py`
  - `test_allow_list_has_the_57_values_of_the_art_list` → `test_allow_list_has_the_64_values_of_the_art_list`：`len == 57`、`neutral: 2` → `len == 64`、`neutral: 9`（docstring 補第③批紀錄 17.7 的 7 個）；其他群組數量不變。模組 docstring 57 → 64。
  - `test_every_filled_skill_is_in_the_list_and_matches_its_weapon_class`：`len(filled) == 36` → `== 47`（註明 #151 補充新填 11 招）；其餘斷言不變。
- `tests/narrative/test_skill_icon_art_qi2a.py`
  - 全量比對 `filled == 36` → `== 47`。
  - `PROP_ROWS` 的 `("skill_lingering_roar", "3", "w:tome/book")`：它填了 `w:roar` 後走 2b 列，第 3 列「其餘」沒有別的實際技能 → 改成合成 `("lingering_roar_no_prop", "3", "w:tome/book")`（`SYNTH` 加 `_copy("skill_lingering_roar", icon_prop=None)`，標「合成」），另加一列 `("skill_lingering_roar", "2b", "w:roar")`。T-A5「改變出手的恰好 6 招」不改，照樣通過（19 招出手不變）。
  - 用 grep 確認：這個檔裡 19 招只出現在上面那一列（其他 T-A1 實例都不是 19 招）。
- `tests/content/test_icon_prop_d4_qi2a.py`：docstring「36 招有填」→「47 招有填」，斷言不變。
- `client/src/render/qIcon/qIconSkills.test.ts`
  - T-B1：`w:` 道具若是 `THINGS` 的 7 個 → 斷言 `def(...).meta.prop.thing === true`（不再要求是第 1 批武器）；其餘照舊。
  - T-B2：數量陣列多一項 `TARGET` 13（出處第④批紀錄 13.1）。
  - T-B5：有箭頭的鍵 9 → 10（加 `form_upkeep_permille`，第④批紀錄 13.1 E）；`summon_limit_delta` 不是箭頭，正負改在 T-D5 測（加號／減號）。
- `client/src/render/skillIcon.test.ts` 112 行附近的 `modifierTargetPart({ mystery: true })`：只斷言 `draw` 不丟例外與標籤不空（`draw` 仍是舊畫法、還在），**不用改**。

## 4. 快照與雜湊（每項證明來自本段）

**快照**（腳本 `fixture_proof.py`：HEAD 版與重產版逐鍵比）
- `client/src/render/fixtures/skill_icons.json`：變動 38 個值，恰好是第 6 節 19 招的 `icon_prop`（8 招 `w:fist` → 新值、11 招新增）與 `art.prop`（舊值逐招等於第 6 節「改前」欄）；`motion`／`act`／`tint`／`spark` 沒有任何一筆變。把這 19 招的兩欄換回舊值（11 招拿掉 `icon_prop` 鍵）後和 HEAD 版**完全相同**；`random` 50、`workshop` 示範逐筆不變。
- `client/src/ui/fixtures/skillCards.json`：只有 `skill_gale_kick.icon.icon_prop` 與 `icon.art.prop`（`w:fist` → `w:boot`）；換回後和 HEAD 版完全相同。
- `unitDolls.json`、`raceLooks.json`、`glossary.json`：重產後 `git status` 沒變。
- `client/openapi.json`、`client/src/api/schema.d.ts`：`export_openapi.py` → `gen:api` 後 `git status` 沒變。
- CLI 快照：沒有重產（slow 結果見 2.1）。

**雜湊**（腳本 `hash_proof.py`；起點＝`git archive 493965a8 src content` 匯出）

| 組合 | `hash_ruleset(library.ruleset)` | `ruleset_hash(library)` | `content_digest(library)` |
|---|---|---|---|
| A 起點 `src`＋起點 `content`（`PYTHONPATH` 指匯出的 `src`） | `21d09310ae4fd46d…` | `57420f4cbee82d8c…` | `8a884ff8f3c9c3a9…` |
| B 本段 `src`＋起點 `content` | `21d09310ae4fd46d…`（＝A） | `57420f4cbee82d8c…`（＝A） | `8a884ff8f3c9c3a9…`（＝A） |
| C 本段 `src`＋本段 `content`（改後） | `163ec72f2f15a7e7…` | `75ea2de332a01e16…` | `356b34e13d36021d…` |
| D＝C 把 19 招 `icon_prop` 換回起點值（`model_copy`，重建 `SkillTable`）、`library.files` 的 19 個技能檔換回、允許清單換成起點那一份 | `21d09310ae4fd46d…`（＝A） | `57420f4cbee82d8c…`（＝A） | `8a884ff8f3c9c3a9…`（＝A） |

B＝A 證明程式沒動雜湊；D＝A 證明三個雜湊的變動全部來自 19 招與允許清單。`git diff --stat 493965a8..HEAD -- content/` 恰好 20 個檔（19 技能＋`skill_icon_props.yaml`）。版號（`LOG_FORMAT`、`WORLD_RULES_VERSION`、`CHAR_FORMAT`）沒動。

**請使用者重開伺服器檢查的重點**（要重新 build；使用者已說存檔可以刪）
1. **內容有變**：重開後進行中的一輪會從頭開始、舊世界日誌標成不能重播（舊戰鬥紀錄內嵌規則包，照樣能重播）。
2. 技能列、技能卡的 19 招換新道具：踩踏、踢翻、颶風踢、躍擊震地、追印絆擊、重踏＝靴；破城衝撞、蠻牛衝陣、衝鋒撞擊、震地推倒＝肩撞；燈油瓶、潑水瓶＝瓶；兩招煙霧彈＝煙霧彈；震懾餘波、挑釁怒吼、野性怒吼＝號角；毒牙頂撞＝獠牙；黏液＝黏液。
3. 修正技卡片（與工坊）組裝算式第一格「改造對象」換 Q 版（標籤文字不變）。
4. 魂結（`skill_soul_bond`）效果列的「分擔傷害」是兩個交扣的淡紫圓環（和狀態「靈魂連結」同圖）。
5. 精英召喚的「召喚物上限 −1」畫減號；化形專精的「形態維持消耗 −500‰」右上是朝下青色箭頭、沙漏移到右下。

## 5. 逐像素比對、截圖、實機未看

**和樣張逐像素比對**（`PhaseQI-2b報告.md` 第 4 節做法：自己的 vite 5295 開 `skillicon-gallery.html?set=none`；靜態伺服器 8144（CORS）供 `docs/art/sample` 原始碼，載入前把 `qIcons.js` 的 `M`、`qIconsWeapons.js` 的 `MAT` 換成 `material.ts` 的色，`window.AssembledIcon = { framePath }`；無頭 Chrome `--disable-gpu --mute-audio --force-device-scale-factor=1`；每一類一頁剛載入的頁面；錘照 2c，技能主圖暗柄和樣張相同，不另處理）

| 比對 | 組數 | 0 像素差 | 不同 | 最少不透明像素（不是空圖） |
|---|---|---|---|---|
| 19 招主圖（fixture 的 `art`）× 24／28／40 × res 1、2 | 114 | 114 | 0 | 424 |
| 19 招組裝 mid 56、mid 48、full 96 × res 1、2 | 114 | 114 | 0 | 1746 |
| 改造對象 13＋分擔傷害＋形態維持 ±500＋召喚物上限 ±1 × 18 r1／18 r2／30 r2（`chipCanvas`） | 54 | 54 | 0 | 216 |
| 精英召喚、群召、化形專精、魂結 full 96 × res 1、2 | 8 | 8 | 0 | 6980 |
| **回歸** 主圖 402 招 × 24／28／40 × res 1、2 | 2412 | 2412 | 0 | 400 |
| **回歸** 組裝 402 招 × mid 56／48、full 96 × res 1、2 | 2412 | 2412 | 0 | 1637 |
| **回歸** 部件 201 個（12 類扣卡片、扣新的 target）× 18 r1／18 r2／30 r2 | 603 | 603 | 0 | 182 |
| **回歸** 卡片小圖 22＋圖釘未釘 × 16／18／13 × res 1、2 | 138 | 138 | 0 | 52 |

回歸共 5565 組，不同的組數 0＝和 QI-2c 報告的基準（4824 組全 0、部件與卡片小圖全 0）相同，本段沒有新增不同的組。沒有看到 ±1 雜訊。

**截圖**（`docs/art/shots/qi2/`；裝置像素比 1 拍；「DPR 2」＝res 2 的畫布照裝置像素原大顯示，「真 1 倍 ×k」＝res 1 的畫布最近鄰放大）

| 檔 | 格式／大小 | 對到 8.4 | 內容 |
|---|---|---|---|
| `F:\PythonProject\LLM-MMO-TRPG\.claude\worktrees\agent-a2616041cd6083fb0\docs\art\shots\qi2\2d-01-props7-40-28-24.jpg` | jpg 94 KB | 01 | 7 個新道具（每個道具第一招）40／28／24 DPR 2：遊戲端｜樣張同圖 |
| `…\docs\art\shots\qi2\2d-02-skills19-dpr2.jpg` | jpg 243 KB | 02 | 19 招 40／28／24 DPR 2，每格上排 2c 後（舊道具）｜下排 2d，標道具值 |
| `…\docs\art\shots\qi2\2d-03-skills19-true1x-x4.png` | PNG 81 KB | 03 | 19 招 24、28 真 1 倍 ×4 |
| `…\docs\art\shots\qi2\2d-04-target13-30-18.png` | PNG 85 KB | 04 | 改造對象 13 個：左現行（2c 後）30 DPR 2、18 真 1 倍 ×6｜右 QI-2d 同兩種 |
| `…\docs\art\shots\qi2\2d-05-redirect-sign-x6.png` | PNG 38 KB | 05 | 分擔傷害雙環（旁邊狀態卡「靈魂連結」20：DPR 2＋真 1 倍 ×6）、形態維持 ±500、召喚物上限 ±1：30 DPR 2、18 真 1 倍 ×6 |
| `…\docs\art\shots\qi2\2d-06-full96-modifiers.jpg` | jpg 75 KB | 06 | 精英召喚、群召、化形專精、魂結 full 96 DPR 2（標實際 changes） |
| `…\docs\art\shots\qi2\2d-07-game-1600-galekick-card.jpg` | jpg 66 KB | 07 | **實機 1600×900**（自己的 `trpg serve` 8146、正式 build）：技能列 40（颶風踢 靴、破城衝撞 肩撞、燈油瓶 瓶）＋颶風踢技能卡 48 mid（展開詳細） |
| `…\docs\art\shots\qi2\2d-07-game-1600-workshop-modifier.jpg` | jpg 12 KB | 07 | **實機 1600×900 工坊**：骨架＝修正「隨機一個」的預覽 96／40／28＋組裝算式第一格 Q 版改造對象（所有攻擊＝交叉雙劍） |

實機的做法：戰鬥用 CDP `Fetch.enable` 攔「一鍵開局」的 `POST /api/battles`，body 換成 `{map_id, seed, hero_build: "build_wallburn"}`（`content/sim/builds.yaml` 的開發 build，正好有 3 個新道具招）；工坊照 2c 的腳本。兩處 `__layoutSmoke.icons()` 都全 PASS（技能卡 25 個畫布、工坊 37 個畫布）。

**實機未看**（開發頁畫了或只靠測試）：內容修正技（例 重踏 `tag_push`、震懾餘波 `tag_shout`、精英召喚 `tag_summon`）的**技能卡**組裝算式——修正技不在戰鬥技能列上，工坊實機只拍到隨機草稿的「所有攻擊」；魂結效果列的雙環、精英召喚的減號、化形專精的朝下箭頭在遊戲畫面（只有開發頁 2d-05、2d-06，畫法和遊戲同一條 `paintSkillIcon`／`QP.chip`）；其餘 16 招新道具在技能列、配招、隊伍等處（2d-02、2d-03 用遊戲端 `paint`）；800×600 尺寸。

## 6. 和樣張不同的地方（值都沒改；也寫在 `skills.ts`、`parts.ts` 檔頭）

- `skills.ts`：`ThingArt` 介面（`tint` 選填）；`LIQUID` 標成可缺的表（查不到退水，同樣張 `?? LIQUID.water`）；`hornPt` 控制點與 `for … of` 字面表加 `as const`；號角 `map` 的回傳標 `Pt`、沒用到的 `i` 改 `_i`；獠牙 `X` 的參數型別；`propOf` 的 `id` 用 `id ?? ""`；`MotionPos` 多 `noTail`、`PropInfo` 多 `thing`、`list()` 的道具列多選填 `note`。
- `parts.ts`：`summon_limit_delta` 的 `(opt?.value ?? 1) < 0` 寫成 `Number(opt?.value ?? 1) < 0`（數字、字串、布林的結果和 JS `<` 的轉型相同）；`targetOf` 的 `applies` 型別標成任意物件、`skill_tags[0]` 加 `as string`；`cardFan` 沒用到的 `o` 改 `_o`（noUnusedParameters）。

## 7. 長函式、複雜度

前端逐行搬的函式不拆；本段沒有新增超過 80 行的函式（`skills.ts` 的 `def()` 由 63 行變 69 行，和樣張同）。Python 只改測試，沒有新增 `noqa`。

## 8. 待 PM 決定

1. **改造對象的接法**（第 0 節第 2 列、F3）：規格寫「只換 `draw`」，實作用 2c 接其他部件的同一條路——加 `q`，`drawChip` 給 `unitPx` 時畫 Q 版；舊 `draw` 保留（`swordGlyph`、`rangedGlyph`、`TAG_TARGET` 因此都還在用，沒刪）。遊戲畫面都有給 `unitPx`，所以全部是 Q 版；沒給 `unitPx` 的只有開發頁 `&old=1`／`oldTarget`。T-D7 照這個解讀寫（組裝列方塊的呼叫紀錄＝`QP.chip("target", …)`）。若要連 `draw` 也換，需要給 `draw` 一個不帶 `unitPx` 的 Q 版畫法，另排。
2. **`tag_summon` 的標籤仍是「summon技能」**（第 0 節第 3 列）：`TAG_NAMES` 沒有 `summon`，本段不改；要改只需加 `summon: "召喚"`。
3. **`status.ts` 94 行 `soul_link` 的註解過時、雙環有兩份**（第 0 節第 4、5 列）：`parts.ts` 另存 `soulRings`，兩份逐筆相同由 T-D4 鎖住；共用與註解留給 QI-3b 或整理段。
4. **美術清單 1.3 的文字仍是第 1 版**（第 0 節第 6 列）：煙霧彈、黏液、肩撞的描述與第 3 節「等 YAML 加了值才算進清單」請轉美術 PM 更新（開發不改 `docs/art/`）。
5. **新基準檔 `render/fixtures/qi2dBaseline.json`**（81 KB）：鎖住開工前全部部件與 402 招主圖的假畫布呼叫紀錄雜湊，之後動部件或主圖的段都要在報告說明並重錄。若嫌負擔，可只留 `sld`／`target` 兩段。
6. **實機截圖的取法**：戰鬥用 CDP 攔請求換成開發 build `build_wallburn`（不是正常玩家流程）；修正技的技能卡實機沒拍到（第 5 節實機未看）。要的話可排一個「開發選單選 build 開戰」的小功能，或在工坊用「從現有技能開始」。
7. **截圖 8 張、07 拆兩張**：戰鬥技能卡與工坊組裝算式各一張（規格寫 1～2 張）。

## 9. 交使用者時要講明（照抄審查第 2 版的清單；註明哪幾條已在實機看到）

1. 肩撞 24px 只看得出「人往前衝」，肩甲要 28 以上才看得出。（實機：技能列 40 看得到肩甲；24 只在開發頁 2d-02／03）
2. 黏液是洋紅色（不是綠），刻意和毒分開。（開發頁）
3. 煙霧彈和其他炸彈同剪影，靠右下的煙雲記號分。（開發頁）
4. 改造對象 `tag_summon` 改畫小靈（現行畫傷害閃光）。（開發頁 2d-04）
5. 改造對象 `attack`／`actions` 同一把劍、`tag_other`／`default` 同一顆四芒閃光（判斷順序照現行，圖相同）。（開發頁 2d-04）
6. 分擔傷害的雙環和被動 ∞ 剪影相近。（開發頁 2d-05、2d-06）
7. 化形專精兩顆掌印靠箭頭分（維持消耗另有右下沙漏）。（開發頁 2d-06）
8. 樣張的組裝圖不讀 `icon_prop`；遊戲端主圖一律用後端 `art`（含 `icon_prop`），兩邊同一份 `look` 時逐像素相同。（實機：颶風踢技能卡 mid 是靴）
9. 審查的「可修」各點（黏液換色、重踏齒輪位置、維持消耗沙漏放大、號角 18px、肩撞 24px 的 V 再退）本段不做，使用者看圖要改時美術改樣張後另排小段。

## 10. 上手筆記更新

- `docs/dev/上手-內容資料與模擬.md`：第一節表 57 → 64 個值；第二節第 8 點補「7 個中性道具不限大類、前後端要同一段上、快照逐招比對、目前 47 招有填」。
- `docs/dev/上手-前端戰鬥畫面與動畫.md`：第一節 `skills.ts`／`parts.ts` 列補 `THINGS`、`TARGET`／`targetOf`、`soulRings`；`skillParts.ts` 列補改造對象的 `q`；第二節開發頁參數 `set=target`、`set=qi2d`、`&before`、`&ppx`、`__qiSkillDev` 新欄位；第四節加第 45～47 點（部件呼叫紀錄基準、假畫布筆數因外框算兩遍、修正技實機要走工坊／CDP 換 build）；第五節測試表加一列。
