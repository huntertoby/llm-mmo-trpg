# FL-1b 報告：靈感閃現「選變體」畫面改版（直向版）

依據：`docs/art/靈感閃現選擇-移植需求.md`（全文；橫向排法第 11 節不做）＋開發 PM 對第 12 節的 7 個決定＋規則面 `docs/design/06-技能.md` 6.34「費用方向」。
三句字（9.2 威力提高、威力降低、9.3 蓄力下固定區句型）**依玩法 PM 2026-11-13 確認**（專案 PM 轉達），已直接用定案字。

## 1. 做了什麼

| 項目 | 位置 |
|---|---|
| 「前 → 後」的畫面欄位：`StatChangeOut` 加 `name_zh`（9.1 #4 欄位名）、帶單位的 `before_zh`／`after_zh`（「4 格」「2 回合」「3 成武器傷害」、倍率照 #3）、`icon`（欄位小圖：第④批卡片小圖／部件、第⑤批狀態、第⑤b 批關鍵字）、`term`（說明卡）。新加的整個效果寫白話（「積水，會造成 潮濕」「3 成武器傷害（目標這回合被撞過才有）」）；拿掉的效果「後」＝`None`（畫面寫「沒有」、變弱樣式；決定 5）。轉型多一列「種類 主動 → 被動」。**對照表只在後端一處**（決定 1） | `src/trpg/api/flash_changes.py`（`_View`、`ratio_zh`、`base_stats`） |
| 只換位置的效果不重複列（多打一下插進一段後，造水往後挪一格：原本會列「積水 → 沒有」又「沒有 → 積水」） | `flash_changes.py` 的 `_drop_shifted` |
| `FlashOptionOut` 加 `headline_zh`（沒填＝`None`，畫面退回 `summary_zh`）、`say_zh`（下固定區一句話）、`tag_term`（蓄力／輕巧的類別標籤帶「威力提高／降低」說明卡）、`unequip_slot`（卸下選單的欄位名；姿態欄自動換下）；`PendingFlashOut` 加 `base_stats`（原技能列數字）與 `terms`（這次用到的說明卡，數字已照資料填） | `src/trpg/api/run_schemas.py`、`src/trpg/api/run_presenter.py`、`src/trpg/api/flash_text.py` |
| 大標、模板 × 關鍵字表、說明卡字、條件白話：`headline_zh`／`say_zh`（模板欄位）、`headlines`（模板 × 關鍵字）、`terms`、`condition_zh` | `content/flash_templates.yaml`、`src/trpg/content/flash_templates.py` |
| 畫面三段：上固定區（標頭、說明行、原技能列）＋選項清單（單選、白話大標、類別標籤、前 → 後四種記號）＋下固定區（選中的大標與一句話、卸下選單、確定）。點整張卡選中、再點不取消、方向鍵切換、選中自動捲進來 | `client/src/screens/RunFlashPending.tsx`、`client/src/run/FlashChoiceParts.tsx`、`client/src/run/flashChoice.ts`、`client/src/styles/flash-choice.css` |
| `PopupFrame` 加 `foot`（照 `head`，放在 `ui-popup-body` 後面、不捲；決定 2）＋`slots`（框的 `ui-popup-head`／`ui-popup-foot` 插槽，空著不顯示；`usePopupSlots`）。大世界面板開 `slots`，選變體元件把標頭與確定列 portal 進去（`PopupSlot`），狀態不用往上提 | `client/src/ui/PopupFrame.tsx`、`client/src/ui/PopupSlot.tsx`、`client/src/world/WorldHud.tsx` |
| 一輪：三段照排，下固定區 `position: sticky; bottom: 0`（決定 3） | `flash-choice.css` 的 `.fc-run` |
| 大世界鎖住提示：寬版第 2 行下一行 L3、窄版收進 (i)（決定 4）；不畫 × | `client/src/world/WorldGrowth.tsx` |
| 示意圖（射程格、積水格）不做（決定 6） | — |
| `cardDiff` 整句比對、`pendingTitle` 拿掉（改讀伺服器 `changes`） | `client/src/run/flash.ts` |
| 開發頁＋夾具：`client/dev/flash-choice.html?set=base｜rows｜transform｜stance&mode=world｜run&pick=0～3`；夾具由伺服器同一套函式產生 | `client/src/dev/flashChoiceGallery.tsx`、`client/src/dev/fixtures/flashChoice.json`、`scripts/export_flash_choice_fixture.py` |
| 測試 | `tests/api/test_flash_text_fl1b.py`（16 條）、`tests/api/test_flash_changes_fl1a.py`（欄位集合）、`client/src/run/fl1bFlashChoice.test.ts`（14 條）、`client/src/ui/floatCardRule.test.ts`（portal 例外：`ui/PopupSlot.tsx`） |
| OpenAPI 與前端型別重產 | `client/openapi.json`、`client/src/api/schema.d.ts`、`client/src/api/types.ts`（`StatChange`、`ChangeIcon`、`FlashTerm`、`FlashBaseStat`） |

沒有升 LOG_FORMAT；沒有後端快照或夾具受影響（預測只有 `test_pending_flash_options_carry_changes` 的欄位集合會變，實際也只有它）。

### 沒有選項的招（1.3 第 6 條）
FL-1c 已做，本段驗收：成長「靈感閃現」分頁與一輪營火那列加 `flash-none`、灰紫虛線、灰字「這招目前沒有可以閃的變化」、閃現鈕停用（伺服器 `can_flash=false`，按不下去就不會扣點）。開發頁量到：成長分頁 `pnl-row pnl-skill flash-none`、鈕 `disabled`；營火 `flash-skill-row flash-none`、鈕 `disabled`。沒有缺的，未補。

## 2. 驗收截圖（`docs/art/shots/FL-1b/`，10 張）

實機＝自己的 `trpg serve --port 8794`（`TRPG_DEV_ROUTES=1`、存檔在暫存區）＋建置好的前端；無頭 Chrome `--mute-audio`、除錯埠 9473、DPR 1、網址 `?mute=1`；800×600 從首頁「繼續」進入。開發頁＝自己的 vite 5294。開發角色：`POST /api/world/characters`（單手劍、點燃＋潮濕），停伺服器後把兩招標成「上場用過」、靈感點補到 6（腳本在暫存區），在主城閃現「水彈射」第 1 次（不指定，真資料四個選項：多打一下、蓄力、射程 +1、延長）。

| # | 檔案 | 內容 | 來源 |
|---|---|---|---|
| 1 | `fl1b_01_none_1600.jpg` | 大世界都沒選：上固定區（燈泡＋標題、第 1 次閃現＋已扣 1 點＋說明行、鎖住提示 L3）、原技能列（名字＋原本的樣子＋AP、耐力、冷卻、射程＋完整說明）、四張卡、下固定區「先點一個變化…」與灰的確定、沒有 × | 1600 實機 |
| 1、10 | `fl1b_10_width_1040_800.jpg` | 左：1040×624 面板 677＝寬版；右：800×600（首頁「繼續」）面板 493＝窄版（一行標頭＋(i)、「原本」「說明」）＝第 1 項的 800 | 實機 |
| 2 | `fl1b_02_picks_1600.jpg` | 四個各自選中：金框、單選圈、大標亮金、下固定區換字；分隔線都在 y=729 | 1600 實機 |
| 2、5 | `fl1b_02_picks_800.jpg` | 同上（分隔線都在 y=481）；第 4 張＝選中最後一張，選項區捲到底（`data-end=1`），卡下框離捲動區底 8px，上下固定區不動 | 800 實機 |
| 3、4 | `fl1b_03_marks_updown_800_x4.png` | 最近鄰 ×4：實機「多打一下」＝變弱 ▼＋新（一張卡同時有升有降）、實機「蓄力」＝代價（琥珀框＋⚠）＋變好；開發頁點燃斬蓄力「冷卻 2 回合 → ⚠ 4 回合、燃燒 5 回合 → 6 回合」；開發頁雙槍連射輕巧（AP、冷卻代價＋傷害 ▼）；開發頁積水「新」＋關鍵字小圓章 | 實機＋開發頁（標實機未看） |
| 6 | `fl1b_06_transform_800.png` | 左：轉型（轉成反應）＋「被動欄滿了，選一招卸下」＋技能圖示鈕，沒選前確定灰；右：轉成姿態，姿態欄自動換下、不出選單、確定可按 | 開發頁（實機未看：要第 3 次閃現；主動欄一例實機到不了——主動欄 6 格，召喚、陷阱轉型要 2 階） |
| 7 | `fl1b_07_tips.jpg` | 說明卡浮在面板外：積水、武器傷害、威力提高（蓄力），1600 一排、800 一排 | 實機 |
| 8 | `fl1b_08_base_800_x2.png` | 「說明」說明卡（類型、組成＝組裝圓片、花費、範圍、效果、會造成、威力看），最近鄰 ×2 | 800 實機 |
| 9 | `fl1b_09_run_1600.jpg` | 一輪營火（重閃第 2 次）：左＝頁面頂，下固定區 sticky 在視窗下緣；右＝選中後捲到頁底，確定一直看得到 | 1600 實機（種子 2 的開發一輪，`dev-advance?to=campfire`） |
| 11 | `fl1b_11_noflash_1600.jpg` | 沒有選項的招：成長分頁、一輪營火那列灰掉、鈕停用、灰字 | 開發頁（實機未看，同 FL-1c） |

### (a) 量到的高度（實機，都沒選）

| 視窗 | 面板 | 上固定區 | 選項區 可視／內容 | 下固定區 |
|---|---|---|---|---|
| 1600×900 | 720×632 | 157 | 391／426 | 74 |
| 1040×624 | 677×413 | 157 | 173／426 | 74 |
| 800×600 | 493×414 | 88 | 259／376 | 57 |
| 一輪 1600（營火右欄，376 寬＝窄版） | 376×598，頁面高 1034 | — | 頁面捲 | sticky 在視窗下緣 |

轉型＋卸下選單（開發頁）：下固定區 800 為 86、1600 為 100（見第 4 節第 3 條）；選卸下選單那張前後分隔線不動（800：458 → 458；1600：711 → 711）。上固定區 800 的 88 在 11.4 第 2 條的 165 以內。

### (b) 欄位名與單位對照放在哪
後端 `src/trpg/api/flash_changes.py` 一處（`_COST_ICON`、`_COST_TERM`、`_COST_UNIT`、`_SHAPE_ROWS`、`_SURFACE_ZH`、`_AMOUNT_UNITS`、`_CARD_ICON`、`_whole_name`、`ratio_zh`、`_View.dress`）。前端只畫樣式（`flashChoice.nowStyle`）。

### (c) `headline_zh`
已填 5 條（8.2 表）：`range_plus`「射程變遠 {n} 格」、`cost_charge`、`cost_light`、`keyword_imbue`×潮濕、`keyword_exploit`×撞擊。其他全部退回 `summary_zh`；完整清單見附錄 A，交玩法 PM 一次填完（填 `content/flash_templates.yaml`：模板加 `headline_zh`，依關鍵字的加進 `headlines`；可用 `{n}`、`{keyword}`）。

### (d) 第 10.2 節三個數

1. **技能產生的水幾回合**：`create_surface` 沒寫 `duration` 時用 `surfaces.yaml` water 的 `duration: 3`；技能自己寫了就照技能（例：水彈射寫 1 回合）；另外施放者智力的常駐加成每一階 +1（`core.yaml` `attribute_perks` 的 `surface_duration`）。說明卡照資料寫「預設留 {water_rounds} 回合」（＝3）；選項卡上的「積水 1 回合 → 2 回合」照技能本身。
2. **「目前 +3」是什麼**：只是**屬性加成**＝縮放屬性 × 普攻倍率 0.3（`basic_attack_attr_multiplier_permille`），不是整段。引擎算法：（武器骰＋武器固定值＋屬性 × 0.3）× 效果倍率（`engine/skills/targeting.py` `damage_parameters`）。所以 9.2「（武器骰 1d8 ＋ …加成）× 0.3。屬性加成目前 +3。」的結構是對的：× 後面是這一列的倍率（3 成＝0.3），「目前 +N」是屬性加成。說明卡照資料填：骰子＝主角手上武器、屬性名＝武器的縮放屬性（單手劍只有「力量」，不是樣張的「力量、智力的平均」）、倍率＝這一列、目前加成照卡片算法句（屬性 12 時 3.6 捨去成「目前 +3」）。
3. **‰ 強度會出現哪些種類**（`flash_changes._MAGNITUDE_TYPES`）：施加狀態的強度（會隨強度變的 25 種：燃燒、虛弱、易傷、流血、中毒、護衛、石膚、激昂、戰意、加速、再生、灌注源晶、晶能湧動、晶能狂湧、界崩、歸一、誓約之力 易／中／難、破誓、熔核爆裂、殼縫熔核、寒燼爆裂、熔殼、硬殼）、表面的強度（`create_surface`，BAL-12e 數值型表面）、形態幅度（`enter_form`，BAL-2c）、只對友方的區域裡巢狀的狀態強度（戰歌的激昂這類，FL-1d）。白話寫法待玩法 PM；**現在暫寫成百分比**（「1025‰」→「102.5%」），欄位名照 `label_zh`（「燃燒強度」）。

## 3. 檢查（交件前）

| 檢查 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1555 檔） |
| `uv run lint-imports` | 0（14 kept） |
| `uv run trpg content check` | 通過 |
| `pytest -n 8`：`tests/api/test_flash_text_fl1b.py`、`test_flash_changes_fl1a.py`、`test_flash_api.py`、`test_world_growth_api.py`、`test_openapi_snapshot.py`、`test_client_fixtures.py`、`test_opening_flash.py`、`tests/world/test_flash_world.py`、`tests/content`、`tests/skillgen/test_flash.py`、`tests/roguelite/test_flash_run.py`、`tests/test_architecture.py` | 0（3142 passed） |
| `vitest run src/run src/ui src/world src/screens src/test src/dev` | 0（125 檔、1613 條） |
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client build` | 0 |

沒跑全量 `check.py`、沒做平衡量測或模擬。伺服器、vite、Chrome 都是自己開的，交件前已關（8794／5294／9473 沒在聽）。

## 4. 待 PM 決定

1. **蓄力／輕巧的「威力提高／降低」說明卡掛在哪**：9.2 有說明卡、選項卡上不寫；我掛在選項卡的類別標籤（「費用」帶青色點線，滑過出現「威力提高（蓄力）」）。要換位置（例如掛在下固定區一句話末尾）只改 `RunFlashPending.tsx`。
2. **‰ 強度暫寫百分比**（見 (d) 3），等玩法 PM 給白話。
3. **下固定區最小高度**：需求寫有卸下選單時窄版約 83、寬版約 91；照真字量到 85／99（兩行說明＋卸下選單＋確定），改成 86／100 才不跳。沒有卸下選單的 57／74 照需求。
4. **下固定區的一句話最多兩行**（`line-clamp: 2`，超出以「…」收）：沒填 `say_zh` 的模板照差異清單組句，轉型這類列數多時會很長；完整的變化看卡上的前 → 後。大標也照需求最多兩行（沒填 `headline_zh` 的長 `summary_zh` 會被截成兩行＋「…」）。
5. **代價整項不用付了**（轉型後不花 AP、耐力）：「後」寫「不用花」、照變好樣式（照樣張轉型那張「AP 2 → 不用花」）；需求只定了「拿掉的效果寫沒有、變弱樣式」。
6. **完整說明說明卡**：欄位照需求（類型、組成、花費、範圍、效果、會造成、元素、威力看），內容用技能卡現有的字（例：效果「武器傷害 ×0.9（物理）（敵方）」），沒有逐句改白話；卡裡的術語不再畫點線（浮動卡裡再套浮動卡不穩）。說明卡寬照共用浮動卡（240），不是樣張的 330。
7. **窄版標頭放不下**（招名長、重閃）：只截招名（「「灼燃・燃燒爆」重…」那種截法改成只截「」裡的名字），「重閃第 2 次」「已扣」「(i)」一定留在框內。
8. **一輪的面板寬**：營火的選變體在右欄（1600 時 376 寬），所以是窄版。
9. **示意圖不做**（決定 6）：9.1 #27 的三個字沒用到。
10. **轉型的卸下選單**：反應填「被動欄」（照 9.1 #28 字面）；伺服器另給 `unequip_slot`，前端照它決定字與姿態自動換下。
11. 第 9.3 第 1、3、4 個的下固定區句子照提案寫進 `say_zh`（`range_plus`、`keyword_imbue`×潮濕、`keyword_exploit`×撞擊）；`{shape}` 會帶十字範圍的說明卡。其他模板沒有 `say_zh`，一併請玩法 PM 決定要不要逐條寫（附錄 A 同一張表）。

## 5. 平衡疑慮

無（沒有動數值；`_drop_shifted` 與欄位名只影響畫面）。

## 附錄 A：大標（`headline_zh`）待填清單（交玩法 PM 一次填完）

說明：`{n}`＝模板的增量（`delta`），`{keyword}`＝選項帶的關鍵字中文名。模板 × 關鍵字的組合寫進 `headlines`（`template`、`keyword`、`headline_zh`，可另加 `say_zh`）；表裡沒有的退回模板自己的 `headline_zh`，再退回 `summary_zh`。

### A. 小變化（minor）
| 模板 | 類別 | 現行 summary_zh | headline_zh |
|---|---|---|---|
| `area_plus` | area | 範圍 +1（傷害依預算調整） | （待填） |
| `range_plus` | area | 距離 +1（傷害依預算調整） | 射程變遠 {n} 格 |
| `reshape_shape` | area | 換形狀（直線 3、錐形 2、十字）：一次打到更多目標（傷害依預算調整） | （待填） |
| `reshape_square3` | area | 換成 3×3（傷害依預算調整） | （待填） |
| `reshape_line6` | area | 換成整排直線（長度 6，傷害依預算調整） | （待填） |
| `reshape_chain` | area | 換成連鎖跳躍（再跳 2 次，傷害依預算調整） | （待填） |
| `followup_area` | area | 接續段範圍 +1（傷害依預算調整） | （待填） |
| `followup_range` | area | 接續段距離 +1（傷害依預算調整） | （待填） |
| `terrain_mid` | area | 地形變化：升降地形的影響範圍擴大到 4～6 格（十字），必要時附帶少量落石傷害（強度由預算補） | （待填） |
| `terrain_wide` | area | 地形變化：升降地形的影響範圍擴大到 7 格以上（3×3 或更大），必要時附帶少量落石傷害（強度由預算補） | （待填） |
| `fuse` | area | 合體：召喚隻數 −1，省下的預算全部換成召喚物的生命（一隻時恢復完整強度） | （待填） |
| `converge_single` | area | 收成單體：範圍收成一個目標，省下的預算全部換成威力（以自己為中心的改成射程 1） | （待填） |
| `converge_step` | area | 縮小一級：直線、錐形長度 −1，或 3×3 改十字，省下的預算全部換成威力 | （待填） |
| `multi_hit` | combo | 多打一下：同一個目標多一段命中（每段傷害依預算調整） | （待填） |
| `followup_hit` | combo | 接續段：命中後再接一小段傷害（6.23 複合技，傷害依預算調整） | （待填） |
| `followup_potency` | combo | 接續段強化：接續段的傷害提高（依預算） | （待填） |
| `refine_merge` | combo | 多段併一段：同一目標的幾段傷害併成一段單發（總量不變，依預算換成威力） | （待填） |
| `element_second` | element | 加第二元素：多一段別種元素的傷害（傷害依預算調整） | （待填） |
| `followup_element` | element | 接續段加第二元素：接續段多一段別種元素的傷害（傷害依預算調整） | （待填） |
| `dual_scaling` | element | 雙屬性縮放：加第二縮放屬性（命中與傷害取兩個屬性的平均） | （待填） |
| `keyword_imbue` | element | 加第二個關鍵字：命中時額外製造該關鍵字 | （待填） |
| `keyword_exploit` | element | 加第二個關鍵字：目標帶有該關鍵字時加碼 | （待填） |
| `refine` | element | 精煉：拿掉一個附帶效果（附帶狀態、第二元素、第二關鍵字或接續段），省下的預算全部換成主要效果的威力 | （待填） |
| `extend_duration` | extend | 延長：這招的狀態、表面與區域多持續 1 回合（效果依預算調整） | （待填） |
| `summon_toughen` | extend | 強壯：召喚物的最大生命再多一截（召喚技能的小變化，強度固定所以靠這個補） | （待填） |
| `kill_refund` | extend | 擊殺返還 1 AP | （待填） |
| `cost_charge` | cost | 蓄力：冷卻 +2（最多 5 回合），威力提高 | 多等幾回合再用，換這招變強 |
| `cost_light` | cost | 輕巧：AP −1（最少 1）、冷卻縮短，威力降低；AP 已是 1 時改成冷卻或資源 −1（每項最少留 1） | 省一點代價，這招弱一點 |
| `stance_cost_light` | cost | 輕巧：姿態維持費 −1，效果降低一級 | （待填） |
| `stance_cost_heavy` | cost | 蓄力：姿態維持費 +1，效果提高 | （待填） |
| `stance_enter_light` | cost | 進入代價 −1：進入姿態的冷卻、法力或耐力 −1（最少留 1；維持費不變，效果不變） | （待填） |
| `stance_enter_heavy` | cost | 進入代價 +1：進入姿態的法力或耐力 +1，姿態效果提高一級（維持費不變） | （待填） |
| `support_potency` | support | 效果 +（治療、護盾、增益依預算提高） | （待填） |
| `support_area` | support | 範圍 +1（效果依預算調整） | （待填） |
| `support_area_wide` | support | 範圍 +2（光環類，效果依預算調整） | （待填） |
| `support_keyword` | support | 附帶第二個關鍵字（例：治療時造水＝潮濕） | （待填） |
| `trigger_range` | trigger | 觸發範圍 +1（效果依預算調整） | （待填） |
| `trigger_range_wide` | trigger | 觸發範圍 +2（效果依預算調整） | （待填） |
| `trigger_potency` | trigger | 效果 +（依預算提高） | （待填） |
| `trigger_cap` | trigger | 每回合觸發次數上限 +1（效果依預算調整，不超過 6.6） | （待填） |
| `reaction_ward` | trigger | 附帶護盾：反應觸發時，自己也得到一層護盾（強度依預算重新分配） | （待填） |
| `reaction_refocus` | trigger | 附帶回氣：反應觸發時，自己所有技能的冷卻 −1（強度依預算重新分配） | （待填） |
| `focus_range` | trigger | 專注：觸發範圍收回一級，省下的預算全部換成觸發效果（依預算） | （待填） |
| `focus_condition` | trigger | 專注：觸發條件收緊一級（例：被攻擊時 → 被近戰攻擊時；沒有條件 → 目標血量低於 50%），換成觸發效果（依預算） | （待填） |
| `mod_potency` | modifier | 修正幅度 +（依預算提高） | （待填） |
| `mod_range` | modifier | 作用範圍 +1（多一條光環半徑 +1 的規則，或射程 +1，幅度依預算調整） | （待填） |
| `mod_keyword` | modifier | 加第二個關鍵字：條件變成「原條件，或另一個關鍵字的條件」（幅度依預算調整） | （待填） |
| `stance_potency` | modifier | 姿態效果 +（元素傷害加成與小特色提高一級，維持費不變） | （待填） |
| `stance_ward` | modifier | 姿態附帶護盾：進入姿態時得到一層護盾（護盾量依預算） | （待填） |
| `stance_mend` | modifier | 姿態附帶治療：進入姿態時回復生命（治療量依預算） | （待填） |
| `stance_refocus` | modifier | 姿態附帶回氣：進入姿態時自己所有技能的冷卻 −1（必要時姿態效果降一級） | （待填） |
| `stance_channel` | modifier | 姿態附帶回魔：進入姿態時回復法力（回復量依預算） | （待填） |
| `stance_cleanse` | modifier | 姿態附帶淨化：進入姿態時移除自己身上的減益（必要時姿態效果降一級） | （待填） |
| `mod_relax` | modifier | 條件放寬一級：血量門檻放寬，或多一個「或」分支（幅度依預算調整） | （待填） |
| `mod_duration` | modifier | 持續回合 +1：命中後附帶的狀態、符文，或召喚物多持續 1 回合（幅度依預算調整） | （待填） |
| `mod_stack` | modifier | 計數上限 +1：依空欄位計算的加成多算 1 格（幅度依預算調整） | （待填） |
| `mod_cooldown` | modifier | 冷卻：命中後冷卻 −1 加深成 −2（幅度依預算調整） | （待填） |
| `mod_cost` | modifier | 代價減輕：附帶的代價（傷害降低、命中降低……）減輕一級，不會變成沒有代價（其他幅度依預算調整） | （待填） |
| `focus_mod_range` | modifier | 專注：作用範圍收回一級（範圍、射程 −1），省下的預算全部換成修正幅度 | （待填） |
| `focus_mod_condition` | modifier | 專注：條件收緊一級（沒有條件 → 目標血量低於 50%；血量門檻收緊；「或」拿掉一支），換成修正幅度 | （待填） |

### A. 大變化（major，引用進化模板）
| 模板 | 類別 | 進化模板 | headline_zh |
|---|---|---|---|
| `major_intensify` | deepen | `intensify` | （待填） |
| `major_reshape` | deepen | `reshape` | （待填） |
| `major_extend` | deepen | `extend` | （待填） |
| `major_delayed_burst` | deepen | `delayed_burst` | （待填） |
| `major_kill_chain` | deepen | `kill_chain` | （待填） |
| `major_battle_variant` | deepen | `battle_variant` | （待填） |
| `major_bridge_exploit` | bridge | `bridge_exploit` | （待填） |
| `major_bridge_imbue` | bridge | `bridge_imbue` | （待填） |

### A. 大變化補充（extra_major：輔助、護盾、召喚）
| 模板 | 類別 | 適用 | 現行 summary_zh | headline_zh |
|---|---|---|---|---|
| `support_wide` | deepen | support | 加深：影響範圍擴大 1 格，多照顧一個人（效果依預算調整） | （待填） |
| `support_ease` | deepen | support | 加深：冷卻縮短 1 回合，能更常使用（效果依預算調整） | （待填） |
| `support_imbue` | bridge | support | 橋接{keyword}：施放時在目標腳下留下{keyword}的場地 | （待填） |
| `shield_potency` | deepen | shield | 加深：護盾量提高（依預算） | （待填） |
| `shield_thorns` | deepen | shield | 加深：護盾附反傷（吸收近戰攻擊時，對攻擊者反彈物理傷害） | （待填） |
| `shield_mending` | deepen | shield | 加深：護盾結束時（打破或到期）回復少量生命 | （待填） |
| `shield_wet` | bridge | shield | 橋接潮濕：護盾被打破時，在自己腳下造出一灘水 | （待填） |
| `shield_marking` | bridge | shield | 橋接標記：護盾被打破時，對打破它的攻擊者施加標記 | （待填） |
| `shield_charged` | bridge | shield | 橋接帶電：護盾被打破時，對打破它的攻擊者造成小量雷電傷害 | （待填） |
| `summon_deepen` | deepen | summon | 加深：召喚物更強壯，並多一個小特性 | （待填） |
| `summon_count` | deepen | summon | 加深：一次召喚 2 隻較弱的召喚物 | （待填） |
| `summon_bridge` | bridge | summon | 橋接{keyword}：召喚物多帶一個{keyword}灌注 | （待填） |

### A. 轉型（transforms）
| 模板 | 轉成 | 現行 summary_zh | headline_zh |
|---|---|---|---|
| `to_passive_on_hit` | passive | 轉成被動：你的攻擊命中時，自動對被打中的敵人補上縮小版的這招 | （待填） |
| `to_reaction_melee` | reaction | 轉成反應：被近戰攻擊時，對攻擊者施放縮小版的這招 | （待填） |
| `to_summon` | summon | 轉成召喚：召喚一隻幫你出手的召喚物（依這招的元素） | （待填） |
| `to_trap` | trap | 轉成陷阱：在地上布下陷阱，敵人踩上去時才發動這招的效果 | （待填） |
| `to_stance` | stance | 轉成姿態：進入一個持續到取消的姿態（原招有傷害給同元素的元素姿態、沒有傷害給防守向） | （待填） |
| `to_modifier` | modifier | 轉成修正型被動：你的同元素技能命中時，帶上這招的效果（沒有可帶的效果時改為傷害提高） | （待填） |

### A. 模板 × 關鍵字／元素
| 模板 | 參數 | 會出現的值 | 已填 |
|---|---|---|---|
| `element_second` | 元素 | fire、ice、lightning、poison、wind、earth、holy、shadow | — |
| `followup_element` | 元素 | fire、ice、lightning、poison、wind、earth、holy、shadow | — |
| `keyword_imbue` | 關鍵字 | 帶電（charged）、撞擊（collision）、隱蔽（concealed）、形態（form）、冰凍（frozen）、高處（high_ground）、點燃（ignite）、標記（marked）、中毒（poisoned）、倒地（prone）、潮濕（wet） | wet |
| `keyword_exploit` | 關鍵字 | 帶電（charged）、撞擊（collision）、隱蔽（concealed）、形態（form）、冰凍（frozen）、高處（high_ground）、點燃（ignite）、標記（marked）、中毒（poisoned）、倒地（prone）、潮濕（wet） | collision |
| `support_keyword` | 關鍵字 | 潮濕（wet）、隱蔽（concealed） | — |
| `mod_keyword` | 關鍵字 | 帶電（charged）、撞擊（collision）、隱蔽（concealed）、形態（form）、冰凍（frozen）、高處（high_ground）、點燃（ignite）、標記（marked）、中毒（poisoned）、倒地（prone）、潮濕（wet） | — |
| `major_bridge_exploit` | 關鍵字（橋接） | 帶電（charged）、撞擊（collision）、隱蔽（concealed）、形態（form）、冰凍（frozen）、高處（high_ground）、點燃（ignite）、標記（marked）、中毒（poisoned）、倒地（prone）、潮濕（wet） | — |
| `major_bridge_imbue` | 關鍵字（橋接） | 帶電（charged）、撞擊（collision）、隱蔽（concealed）、形態（form）、冰凍（frozen）、高處（high_ground）、點燃（ignite）、標記（marked）、中毒（poisoned）、倒地（prone）、潮濕（wet） | — |
| `support_imbue` | 關鍵字（橋接） | 帶電（charged）、撞擊（collision）、隱蔽（concealed）、形態（form）、冰凍（frozen）、高處（high_ground）、點燃（ignite）、標記（marked）、中毒（poisoned）、倒地（prone）、潮濕（wet） | — |
| `summon_bridge` | 關鍵字（橋接） | 帶電（charged）、撞擊（collision）、隱蔽（concealed）、形態（form）、冰凍（frozen）、高處（high_ground）、點燃（ignite）、標記（marked）、中毒（poisoned）、倒地（prone）、潮濕（wet） | — |

「會出現的值」是上限（嫁接表 `skill_evolution.yaml` grafts 的 11 個）：實際還受模板的 `keywords` 限制與出題條件影響（例：`support_imbue` 只出「製造場地」的關鍵字、`summon_bridge` 只出灌注表有的）。`element_second`、`followup_element` 依元素不同，`headlines` 的 `keyword` 欄填元素 ID 即可（例：`ice`）。

## 開發 PM 裁定

- 接受，已合併。第 12 節 7 項照派工決定做（第 6 項的示意圖不做）。玩法 PM 2026-11-13 確認的三句字已併入。
- 待 PM 決定 1～11 全部照 agent 的做法維持，其中：
  - 第 2 點「‰ 強度暫寫百分比」、第 11 點「其他模板的 say_zh」：併入附錄 A，和 headline_zh 一起交玩法 PM 一次填完。
  - 第 6 點：完整說明卡沿用技能卡的字，不另改白話。美術驗收若要改，另開小修。
- **檢查放寬（push 前已回報專案 PM）**：floatCardRule 測試新增 portal 例外，只放 `ui/PopupSlot.tsx`；PopupFrame 本身照舊不用 portal。
- changes 去掉「只換位置」的成對兩列：視為正確性修正，接受。
- 截圖 10 張存在 `docs/art/shots/FL-1b/`，待美術 PM 照第 11 節驗收。實機未看的有 #3／#4 的一部分、#6、#11（開發頁）；主動欄卸下選單實機到不了。
