# Phase E3b 報告｜E3 後續顯示（霜行預覽與說明、種族被蓋過的用字、分點懸掛縮排）

> 規格 `docs/phases/PhaseE3b計畫.md`；用字照 `docs/design/08-裝備.md` 8.29 E3「顯示」與規格第 3 項（玩法 PM 11-22）；美術 `docs/art/E3驗收.md` 小修 1～3、「請開發確認」，`docs/art/E4驗收.md` 末節。基準 main `d64dc3168`。沒有改規則、數值、`docs/design/`、`config/`，也沒碰 TS-2 的檔案。

## 1. Commit

| 項目 | commit |
|---|---|
| 1 走路預覽畫出會留冰的格子＋預覽牌一行 | `00f7f1273` |
| 2 霜行冰的名詞說明 | `114ea84dc` |
| 3 種族被動加註改寫（灰色只套沒作用的段、`text-wrap: pretty`） | `8f4c8b4dc` |
| 4 台階「▲N」畫在路徑線上面 | `e5c14f4fa` |
| 5 環境預告 (1,3) 出現兩次 | `3521d662f` |
| 6 所有「・」分點的說明框懸掛縮排 | `7a0cdfa71` |
| 截圖 | `21c1f0ec6` |
| 合併 main（只有文件） | `0918d3830` |
| 報告 | 最後一個 commit |

## 2. 各項做法

1. **走路預覽的留冰格子**
   - 後端 `engine/path_preview.py`：`PathPreview.trail`（`TrailPreview`：`tiles`、`surface`、`duration`）。取最少後果那次模擬（停點＝`stop`）裡 `cause="trail"` 的 `surface_changed`，所以已有表面、有其他單位站著、會飛、那一步倒下等不留的情況，和實走用同一套判斷（`engine/trail.py`），沒有另寫一份規則。
   - API `path_schemas.TrailOut`、`PathPreviewOut.trail`（沒有時 `null`）；OpenAPI、`schema.d.ts` 重產。
   - 前端 `battle/pathPreview.ts`：`PathDraw.trail`（框線格子）、`trailTag`（預覽牌放在停點）、`trailText`「沿路留下冰 N 格（M 回合後消失）」，表面名稱取名詞表（火是「火焰」）。
   - 畫法 `render/pathArt.ts` `drawTrailCell`：格子內縮 8、短虛線圓角框、**不填色**，冰用淡冰藍 `0xbfeaff`、火 `0xffa060`、水 `0x8cc8ff`、其他白色。和地圖上已有冰的「實線外框＋淡填色」分得開，也不是冰的樣子（美術意見）。待美術 PM 驗收。
2. **霜行冰的名詞說明**
   - `TileView.surface_trail`（留下的人的 ID；沒有時不輸出，既有格子 JSON 逐字不變）。
   - 前端 `battle/tileInfo.ts`：霜行的表面那段標題只寫表面名，第一行「〇〇沿路留下的冰：剩 N 回合，到期直接消失，不會變成水。〇〇自己踩不會滑倒，其他人照一般冰檢定。」；表面不是冰時沒有「滑倒」那句，後面接該表面原本的說明。原本的「由技能產生時持續 N 回合，之後變成水」那行不列（不適用），其他原本的規則行（元素、檢定 DC、互動）照列。一般的冰照舊。
   - 名詞說明是格子資訊卡（`tileSections`），不是 `narrative/tile_info.surface_rules`：後者是名詞表的靜態文字，不分哪一格，所以沒改。
3. **種族被動加註**
   - 前端 `battle/race.ts` `passiveSegments`／`passiveLabel`：「被動「流線身形」・有作用」「・水的部分被身體的「〇〇」蓋過，其他有作用」「・被腳的「〇〇」蓋過，沒有作用」，不用括號。
   - 全部或部分被蓋過要看後端：新增 `RaceView.passive_overridden_full`（`unit_rules.race_overridden_fully`；沒被蓋過時不輸出）。兩件裝備各蓋一部分、合起來整條被蓋過時也算「全部」。
   - 新元件 `ui/RacePassive.tsx`（`RacePassive`、`RaceDetail`），HUD「▸ 詳細」的種族那行和角色面板「▸ 詳細」的種族列共用；`race-off`（`var(--muted)`）只套沒作用的那段。
   - HUD 那行原本整行是 `muted`，灰色看不出來；改成「・潮息剩 1／1 次・」維持 `muted`，被動那段用本文色，沒作用的段灰色。
   - 角色面板種族列改成「鱗族・種族技「潮息」・被動「流線身形」・……」（原本是括號套括號）。
   - `passiveLine`（種族名的說明卡、技能列）也改成同一套字：「被動「〇〇」：說明・有作用」。
   - `.hud-race { text-wrap: pretty; }`。
4. **台階「▲N」在路徑線上面**：高度標記節點記在 `heightBadgeAt`（依格子）。畫路徑時，在 `marks` 裡路徑線後面放一個 Pixi `RenderLayer`（`pathBadgeTop`），把路徑線經過的格子（`pathLineCells`：每段兩端）的「▲N」接上去，節點仍在原本那排、位置與縮放不變；路徑線本身不改。清高亮前先放回；重畫地形後（`draw`）再接一次。
5. **環境預告 (1,3) 出現兩次：是同一件事**。最上面金色那行是滑過格子時 `marksTextAt` 取出那一格的預告字，就是下面清單裡同一筆 `surface_changed` 的同一句字（`telegraph.ts` 的標記由 `t.changes` 產生）。改成：滑過的格子在清單已有的項目直接標金色（`.telegraph-list .telegraph-hot`），不另外多一行；清單沒有的（持續區域的說明 `zoneLinesAt`）才照舊放最上面。`splitHoverTexts` 是純函式、有測試。
6. **懸掛縮排**：新 `ui/bulletText.ts`（`bulletLines`）。`float-card.css` 那一條規則選擇器從 `.part-tip-text.part-tip-bullet` 放寬成 `.part-tip-bullet`（還是唯一一條）。改到的說明框：
   - `Hint` 的預設內容（`hintBody`）：「・」開頭的行各自一塊、套 `part-tip-bullet`。涵蓋 `actionInfo.ts` 的動作說明（移動、普攻、跑步、守護、結束回合、「更多動作」選單項目，`TurnControls.tsx`）、狀態列晶片與條的說明（`statusCard.ts` 接 `actionCardText`，例：移動、耐力），以及其他經 `Hint` 而有「・」分點的說明。
   - `PartTip` 的 `tip` 字串（`tipBody`）：`stackInfo.ts` 的層數說明（`StackTip`）與其他傳 `tip` 的部件說明。
   - E4b 的倒地（`parts` 的 `bullet`）照舊。
   - 沒有「・」分點的說明照舊整段，不多包元素。

## 3. 測試

| 檔 | 內容 |
|---|---|
| `tests/engine/test_trail_preview_e3b.py`（8） | 起點與途經、停點不留，和實走一樣；沒規則 `None`；略過：已有表面、有其他單位站著、會飛、那一步倒下（看得見的捕獸夾，HP 1）；非冰表面與持續；API 輸出 |
| `tests/engine/test_trail_view_e3b.py`（1） | `TileView.surface_trail`：有時帶 ID、沒有時不輸出 |
| `tests/engine/test_race_note_e3b.py`（3） | `passive_overridden_full`：部分 false、全部 true、沒被蓋過不輸出 |
| `client/src/battle/trailPreview.test.ts`（5） | 預覽牌那行：冰、非冰（火焰）；沒有霜行；框線格子與預覽牌位置；框線是內縮虛線、不填色、顏色依表面 |
| `client/src/battle/tileInfoTrail.test.ts`（4） | 霜行冰的說明：冰、非冰；一般的冰照舊；找不到持有者、沒有剩餘回合 |
| `client/src/battle/race.test.ts`（改寫＋4） | 三種加註、灰色套在哪一段（`off`）、被動沒作用時、兩件合起來整條被蓋過；不用括號；HUD／面板用 `RacePassive`；CSS |
| `client/src/render/pathBadgeLift.test.ts`（2） | 路徑線經過的格子；`RenderLayer` 在線後面、小牌前面、清除前放回、重畫後再接 |
| `client/src/battle/telegraph.test.ts`（＋2） | 同一句字標金色不重列、持續區域照舊放上面；面板與 CSS |
| `client/src/ui/bulletText.test.ts`（3）、`tipPartsE4.test.ts`（改一行） | 切行；`hintBody` 套 class 的行數；套到的說明框（動作、層數、倒地）；CSS 只有一條規則 |

## 4. 驗收

（第 4 節的全量檢查結果在合併 main 之後跑，見下表最後幾列。）

| 檢查 | 結果 |
|---|---|
| ruff check、ruff format --check、mypy、lint-imports（每個 commit 前） | 0 |
| tsc（每個 commit 前） | 0 |
| vitest 相關檔（`src/render`、`src/ui`、`src/battle` 相關檔） | 0 |
| pytest 相關檔（`tests/engine/test_trail*`、`test_path_preview`、`test_race_note_e3b`、`test_stronger_rule_e3`、`tests/api`） | 開發中一次 `tests/api/test_wish_pregen.py::test_text_wish_is_logged_and_replayed_without_llm` 在 `-n 8` 下失敗一次（`WorldActionError：池子這次沒聽懂你的願望`），單獨重跑 6 passed；和這段的改動無關（許願流程，不經過路徑預覽、格子視圖、種族視圖） |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（後端 config 36、text 0；前端 text 0；沒歸類 0） |
| 442 招逐招預算（`budget442.py`，基準 `git archive d64dc3168`） | `cmp` 0（逐位相同） |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`） | `cells=204 different=0 whole_equal=True` |
| 78 場（`compare78.py`，a 段那組，基準 `git archive d64dc3168`） | `battles=78 events=26741 different=0`；內嵌規則包差異 0 條（`format` 也比，沒有去掉） |
| CLI 快照 | 這段只在視圖多兩個選填欄位（沒有值時不輸出）、API 多一個選填欄位，CLI 文字沒改；結果見 slow cli 那列 |
| `uv run python scripts/check.py --all` | 結束碼 0（開發 PM 回「可以跑」後，merge main 已是最新）：pytest 18689 passed、8 skipped；vitest 4934；ruff、format、mypy、lint-imports、client typecheck、situation coverage 通過；已寫通過戳記 |
| slow parity、cli（`-m slow tests/skillgen/test_refactor_parity.py tests/cli`） | 結束碼 0（995 passed）；CLI 快照、parity 都沒變，不用重產 |
| 前端 build | 結束碼 0（全量後重跑） |

不寫死 `LOG_FORMAT` 版號：這段沒有改戰鬥紀錄格式，也沒有新增比對版號的測試。

## 5. 截圖（`docs/art/shots/e3b/`，交美術 PM）

實機：`trpg serve`（埠 8787）＋暫存的內容複本（E3 那三條測試詞條；治療英雄改鱗族；地圖懸崖前哨），頁面腳本換掉「一鍵開局」的開戰內容（同 E3）。無頭 Chrome `--mute-audio`、DPR 1；jpg 品質 80，PNG 只用在真 1 倍；都在 300 KB 以下，共 9 張。

| 檔 | 內容 |
|---|---|
| `docs/art/shots/e3b/e3b_frost_preview_1600x900.jpg`、`docs/art/shots/e3b/e3b_frost_preview_800x600.jpg` | 坦克穿「霜行攀岩靴」還沒走，滑到 (2,4)：起點與途經三格畫內縮虛線框（停點不畫），預覽牌「沿路留下冰 3 格（1 回合後消失）」 |
| `docs/art/shots/e3b/e3b_frost_ice_info_1600x900.jpg` | 走過之後 Shift＋點 (1,3) 釘住資訊卡：「坦克英雄沿路留下的冰：剩 1 回合，到期直接消失，不會變成水。坦克英雄自己踩不會滑倒，其他人照一般冰檢定。」；右上環境預告的 (1,3) 只有一行、標金色（第 5 項） |
| `docs/art/shots/e3b/e3b_race_note_hud_800x600.jpg` | HUD「▸ 詳細」種族那行：「被動「流線身形」・水的部分被身體的「站在水上，移動 +2」蓋過，其他有作用」，灰色只在「水的部分…蓋過」 |
| `docs/art/shots/e3b/e3b_race_note_panel_1600x900.jpg` | 角色面板「▸ 詳細」的種族列：「鱗族・種族技「潮息」・被動「流線身形」・……」，同一套字與灰色 |
| `docs/art/shots/e3b/e3b_climb_preview_800x600.png` | 攀岩預覽 800 寬真 1 倍：路徑線經過的「▲1」「▲2」畫在線上面 |
| `docs/art/shots/e3b/e3b_bullet_run_800x600.jpg`、`docs/art/shots/e3b/e3b_bullet_defend_800x600.jpg`、`docs/art/shots/e3b/e3b_bullet_move_chip_800x600.jpg` | 懸掛縮排：跑步、守護按鈕的說明，HUD 移動晶片的說明；分點換行後對齊「・」後面的字 |

浮動卡：這段沒有新增彈出卡片；預覽牌是地圖上的小牌，資訊卡、說明卡都是原本的共用元件（`TileCardController`、`Hint`、`PartTip`），行為沒改，所以沒另做「滑進、捲到底、釘住、關閉」的實測（資訊卡的釘住在第 2 張截圖用到）。

## 6. 對外資料（守則 14）

- `TileView.surface_trail` 會寫出霜行表面持有者的 ID，前端用它寫出名字。這片表面在地圖上看得到，和既有的 `surface_creator`（同一格、同一個人）是同一級資訊，不多洩漏。
- `RaceView.passive_overridden_full` 只是既有 `passive_overridden_zh` 的一個旗標，敵方單位也一樣（E3 已記：多人階段排「每個視圖帶觀看者」時一併確認敵方裝備是否該被看見）。
- `PathPreviewOut.trail` 只給移動者自己（路徑預覽只能預覽主角）。

## 7. 待 PM 決定

1. **預覽取最少後果那次模擬**：路徑上有別人的冰或陷阱、結果看骰子時，框線照「骰子都有利」那次畫（停點＝預覽的 `stop`）；最多後果可能少留幾格，畫面不另外標「可能」。
2. **框線樣式**（內縮 8、短虛線、不填色、冰用淡冰藍）是我定的，交美術 PM 驗收。
3. **預覽牌放在停點**，和其他小牌一起排（`placeTags` 不重疊）；放不下時往上疊。
4. **非冰表面也寫「不會變成水」**：照規格的句子只換「滑倒」那句，所以留火也寫「到期直接消失，不會變成水」。要不要改成「到期直接消失」就好，請玩法 PM 定。
5. **霜行冰的說明後面照列原本的規則行**（元素、檢定 DC、和火的互動），只拿掉「持續 N 回合，之後變成水」那行。
6. **被動此刻沒作用時**（例如天氣型沒下雨）：沒被蓋過就不加註（同原本）；部分被蓋過時不寫「其他有作用」；全部被蓋過照寫「沒有作用」。
7. **HUD 種族那行的顏色**：原本整行 `muted`，改成被動那段用本文色、沒作用的段灰色，「・潮息剩 1／1 次・」仍是 `muted`。
8. **角色面板種族列改成「鱗族・種族技「潮息」・被動「流線身形」・……」**，種族名的說明卡與技能列的 `passiveLine` 也換成同一套字「被動「〇〇」：說明・有作用」。
9. **`text-wrap: pretty` 在 800 寬仍留兩個字**：HUD 那行最後一行是「作用」（原本是「過）」）。Chrome 的 pretty 只保證不留單一個詞；要完全避開需要另外調字或寬度，請美術 PM 看截圖決定。
10. **懸掛縮排的 CSS 選擇器放寬成 `.part-tip-bullet`**（原本要同時有 `.part-tip-text`），讓 `Hint` 的說明也能用同一條規則；`tipPartsE4.test.ts` 的比對跟著改一行。
