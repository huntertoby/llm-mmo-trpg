# X10-3b 報告：×10 的骰子顯示與位數

依據：`docs/phases/PhaseX10-3b計畫.md`、`PhaseX10-3a報告.md`（含開發 PM 裁定）、`docs/design/05-戰鬥.md` 5.4.1。
基準：開工時 `git merge main`（`ca9429fac`）；交件前再 merge 一次 main（X10-3c 併入後的 `0d1716186`，merge commit `068e5755b`，沒有衝突）。分支 `worktree-agent-a5aeb9075fc12f599`，沒 push。
沒改 `docs/design/`、`config/`；沒碰 X10-3c 的 `src/trpg/skillgen/flash_*.py`、`content/flash_templates.yaml`、parity 夾具、docstring 與 YAML 註解。沒跑全量、沒用 `-m ""`、沒試數值。

## 1. 交付與 commit

| # | 項目 | commit |
|---|---|---|
| 1 | 卡片和技能列只寫範圍 | `e31efe616` |
| 2 | 長說明多一行「擲 2d8，每點 ×10」 | `5b67e6a57` |
| 3 | d20 判定照舊 | 沒有改動（只有截圖 5） |
| 4 | 連接號一律「–」 | `274913121`（測試；伺服器端的同一條檢查在 `e31efe616`） |
| 5 | 位數變寬 | `d01b8f6f5`（測試；排版本來就會換行，沒改 CSS） |
| 6 | 工坊的換算提示 | `16d9a39ab` |
| 7 | X10-3a 留下的舊字 | `0f8524baf` |
| 補 | 免死的戰鬥敘事與卡片句「HP 留在 1」→ 照倍率（開發 PM 途中補充） | `1af2fab39` |
| — | merge main（X10-3c） | `068e5755b` |
| — | 報告與截圖 | （本檔所在的 commit） |

第 3 項沒有程式要改，所以沒有 commit；第 4、5 項的程式本來就符合，只補了回歸測試。

## 2. 範圍在哪一層算（交付項目 1）

範圍在**後端**算，前端照收到的字顯示。新的共用小工具 `src/trpg/shared/range_text.py`：
- `span(count, sides, scale, extra)`：最小 `count × scale + extra`、最大 `count × sides × scale + extra`。
- `range_text(low, high)`：「20–160」；兩端相同只寫一個數。
- 連接號常數 `RANGE_DASH = "–"`（U+2013）。

### 數字（`stats.effects[].label`，卡片與技能列的那一行）
`src/trpg/api/skill_cards.py`：
- 傷害、治療、護盾原本寫「3d6」，改成範圍：骰面 × `quantity_scale`，再疊效果的固定值（`flat_bonus`）。
- **有持有者時**（一輪主角、戰鬥中的主角卡 `hero-cards`、工坊）：法術傷害、治療、護盾再疊**目前的屬性加成**。算法和卡片「傷害算法（目前 +N）」一樣：縮放屬性 × 倍率‰（法術傷害有 `attr_permille` 時用它），捨去後加上。骰值與固定值都是整數，所以和引擎「合計後才捨去」結果相同。
- 沒有持有者（三選一的泛稱卡、`/api/skills/{id}`）：只疊固定值，句子照舊寫「＋智力加成」。
- 武器傷害照舊寫倍率「×0.4」（骰子來自手上的武器，不是這張卡的骰子）。
- 結構化欄位 `dice` 照舊是「3d6」（資料原樣，畫面不顯示）。
- `card_stats`、`effect_stat` 多一個選填參數 `owner`。

### 句子（卡片的效果行、詳細、說明卡）
- `src/trpg/narrative/skills.py`：所有效果句的骰子都改成範圍。例：「2d6＋智力加成的火焰傷害」→「20–120＋智力加成的火焰傷害」。
  - 包含撞擊傷害、推倒石柱、超載反噬、直線衝撞、投擲、獻祭、引爆符文、定時炸彈。
  - 句子不帶持有者，所以不疊屬性，「＋X加成」照留。
- `src/trpg/content/skills/skill.py` 傷害算法的武器骰：「武器骰 1d8＋20」→「武器骰 30–100」（固定傷害疊進範圍）。
- `src/trpg/narrative/summon_info.py`（召喚物資訊：普攻、灌注、脈動、自爆）、`src/trpg/content/form_text.py`（形態的天生武器、進入時的範圍傷害與相鄰治療）也改成範圍。這兩處也在卡片上。
  - `form_text` 的天生武器句也是戰鬥中形態面板（`engine/view.py`）用的，那裡跟著變成範圍。
- 新測試 `test_no_card_text_writes_dice`：全部 434 個技能的卡片（`stats`、`icon` 以外）都找不到「NdM」。

例（截圖 2、3，戰鬥中主角卡，智力 160 → 加成 +80）：
- 餘燼爆發：1d8 → 「90–160」、4d6 → 「120–320」。
- 第 1 段沒有持有者時是「10–80」。

## 3. 長說明（交付項目 2）
- `EffectStat` 多一個欄位 `dice_note`：「擲 3d6，每點 ×10」（倍率 1 時只寫「擲 3d6」）。
  - 武器傷害在知道持有者的武器時寫武器骰（「擲 1d8，每點 ×10」），不知道時為 `null`。
  - 沒有骰子的效果為 `null`。
- 前端：
  - 滑過效果數字的說明卡：效果句的下一行（`skillCardLines.ts` 的 `effectHint`）。
  - 展開「詳細」：每條效果句下面一行小字（`SkillCardView.tsx`，`data-testid="skill-dice-note"`）。連打的「第 N 擊：同上」那行不重複寫。
- OpenAPI 有變（多一個欄位），已重產 `client/openapi.json` 與 `client/src/api/schema.d.ts`。

## 4. d20、連接號、位數（交付項目 3～5）
- **d20**：沒有改。量類骰只在 `roll_quantity` 乘倍率，d20 檢定不經過那裡（X10-2a）。截圖 5 是事件卡的 d20 圖示＋DC 13。
- **連接號**：卡片、技能列、戰鬥預覽 `damageText` 都是「–」（U+2013）。
  - Python `tests/shared/test_range_text.py` 直接讀 `previewText.ts` 比對。
  - vitest `client/src/ui/x10RangeDash.test.ts` 檢查全部卡片夾具的範圍和預覽同一個字，而且不寫骰子。
- **位數**：
  - 效果那一行本來就是 `flex-wrap: wrap`，數字和標籤都沒有 `overflow: hidden`、`text-overflow`。字級：數字 14 px、標籤 11 px。
  - 放不下時整格往下換行，不會出現「…」，所以沒改 CSS。`client/src/ui/x10RangeWidth.test.ts` 把這幾條釘住。
  - 傷害範圍前面是傷害圖示（✦，`EffectGlyph` 的 `damage`），不是骰子。
  - 800 寬實測（截圖 3）：卡片 380 px；「90–160」95 px、「120–320」103 px，一行放得下，沒有左右捲軸。
  - HP 文字（「HP 400 / 400」）、飄字（「−86」）在截圖裡都沒有擠到。

## 5. 工坊提示（交付項目 6）
- `client/src/tuning/ScaleNotice.tsx`：數值工坊頁面的頂端（錯誤列下面）一行「數值已整體放大 10 倍（2026-11-20）；舊的 5 現在是 50。」，旁邊「知道了」。
  - 「知道了」是這個畫面原本資訊列就用的按鈕字，沒有新增別的字。
- 關掉後 `localStorage["trpg.tuning.x10Notice"] = "1"`，以後不再出現。讀寫都包 try/catch：私密視窗、封鎖儲存時照樣顯示，關掉也不會丟錯（只是下次還會出現）。
- 實測：關掉後記下 `"1"`，重新整理再進工坊不再出現。

## 6. 舊字（交付項目 7）
- `content/world/items.yaml`：
  - 小回復藥「戰鬥中回 2d6 HP」→「戰鬥中回 20–120 HP」；
  - 中回復藥「4d6」→「40–240」。
  - `tests/test_x10_texts.py` 加一條：從道具的 `dice` 算出範圍來比對。
- `client/src/workshop/fixtures/arena.json`：木樁「HP 300」→「HP 3000」。
- `options_charge_effects.json`（1 處）、`options_charge_full.json`（2 處）：免死「HP 留在 1，」→「HP 留在 10，」。
- `client/src/dev/fixtures/flashChoice.json`：輕巧的舊說明 ×3 換成 `flash_templates.yaml` 目前的 `cost_light.summary_zh`。
  - **這份是改字，不是重產**：見待決 6。

## 6.5 途中補充：免死的「HP 留在 1」（`1af2fab39`）
開發 PM 轉來兩處，實際留下的是 1 × `quantity_scale`（現在 10）：
- `src/trpg/narrative/events.py` 戰鬥敘事「…擋下了致命傷害，HP 留在 {倍率}」：讀 `v.state.ruleset.core.quantity_scale`。
- `src/trpg/narrative/skills.py` 免死效果句「受到致命傷害時 HP 留在 {倍率}」：讀 `lib.ruleset.core.quantity_scale`。
- 都不寫死，倍率 1 的內容會寫 1。`tests/narrative/test_events_text.py` 改成照倍率算，並確認正式內容是 10。
- 快照：預測 `skills_list` 與裝著 `skill_undying_oath` 的那一片會變、7 個戰鬥鍵不變（這些戰鬥沒有免死事件）。實際變的是 `skills_list`、`skills_show_all/13`，和預測一致，用 `-k "skills_list or skills_show_all/13"` 重產。

## 7. 快照與夾具

| 檔案 | 預測 | 實際 |
|---|---|---|
| CLI `skills_list` | 會變（清單帶效果句） | 變，已重產 |
| CLI `skills_show_all/00`～`/15` | 會變（幾乎每片都有帶骰子的技能） | 16 片全變，已重產 |
| CLI 7 個 `battle_*` | 不變（戰鬥輸出沒有卡片句子） | 不變 |
| 補充（免死）：`skills_list`、`skills_show_all/13` | 會變 | 變，已重產（見 6.5） |
| `client/src/ui/fixtures/skillCards.json` | 會變 | 第 1、2 項各重產一次 |
| `glossary.json`、`unitDolls.json`、`raceLooks.json` | 不變 | 不變 |
| OpenAPI／`schema.d.ts` | 第 2 項會變（新欄位） | 變，已重產 |
| `tests/cli/snapshots/llm_propose_mock.txt`、`llm` prompt 快照 | 可能變 | 不變，測試全過 |
| parity 夾具 | 不碰（X10-3c） | 沒動 |

CLI 快照照規矩用 `-k "skills_list or skills_show_all"` 只重產那 17 個鍵，重產後 `-m slow tests/cli/test_output_snapshots.py` 24 個全過。

既有測試裡寫死骰子的斷言改成範圍（只改斷言，沒改測的東西）：
- `tests/engine/helpers.py` 多一個 `card_dice(dice, flat)`，給「卡片上的骰子＝技能資料」那類測試用。
- 改到的檔：
  - `tests/engine/`：`test_charge_through`、`test_earth_element`、`test_element_seeds`、`test_form_pools`、`test_form_release`、`test_forms`、`test_variance_preview`
  - `tests/narrative/`：`test_rule_texts`、`test_skills_text`、`test_form_cards`
  - `tests/skillgen/`：`test_flash_bal10b`、`test_flash_bal12c`、`test_flash_major`、`test_flash_transform_followup`、`test_flash_transform_physical`、`test_proposal_l10b`、`test_skill_tier`
  - `tests/cli/test_skills_cli`、`tests/api/test_skill_card_stats`
  - vitest `client/src/ui/skillCard.test.ts`

## 8. 截圖（`docs/art/shots/x10-3b/`）

做法：
- 無頭 Chrome `--headless=new --mute-audio --force-device-scale-factor=1`，除錯埠 9766；網址帶 `mute=1`。視口用 CDP 設成 1600×900 與 800×600，`deviceScaleFactor` 1。
- 伺服器：暫存區的啟動腳本 `create_app(static_dir=client/dist, tuning=True)`，埠 8766，存檔在暫存區，LLM 用 mock，`TRPG_DEV_ROUTES=1`。
- 戰鬥：開發模式單場戰鬥，頁面的 `window.fetch` 包一層，把建立戰鬥的請求換成 `hero_build: build_fire`（技能列有餘燼爆發）；按「不佈置，直接開戰」；播放按「跳到結尾」直到輪到主角。
- d20：正式畫面要在大世界遇到情境判定，這裡改用開發頁 `client/dev/story-gallery.html?mode=event`（暫時開 vite dev server，埠 5179），畫的是真正的 `EventCard`。
- 結束時停掉自己起的伺服器、vite、Chrome，三個埠都已關閉。

| 檔案 | 內容 |
|---|---|
| `1-cards-1600.jpg` | 一輪升級選技（開發畫面 `level_up`）的兩張卡：「80–130」「80–190」（主角智力 140，已疊加成） |
| `2-skillbar-1600.jpg` | 戰鬥技能列滑過餘燼爆發：「90–160 火焰」「120–320 火焰」 |
| `3-skillbar-800-longest-1x.png` | 同上，800×600、真 1 倍 PNG。「120–320」是戰鬥中卡片最長的範圍：五個 build 開戰後的主角卡都量過，這個最長 |
| `4a-long-hover-1600.jpg` | 滑過「120–320」：效果句、「擲 4d6，每點 ×10」、傷害算法 |
| `4b-long-detail-1600.jpg` | 展開「詳細」：兩條效果句下面各一行「擲 1d8／4d6，每點 ×10」 |
| `5-d20-dc-1600.jpg` | 事件卡情境判定：d20 圖示＋DC 13，照舊 |
| `6-tuning-notice-1600.jpg` | 數值工坊頂端的換算提示 |

## 9. 檢查

最後一個程式 commit 是 `1af2fab39`，之後是 merge main（`068e5755b`）與這份報告、截圖。以下都是在 merge 之後的樹上跑的。

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（全專案，1737 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0 |
| `-m slow tests/skillgen/test_refactor_parity.py`（merge 後，開發 PM 指定） | 0（935 passed） |
| 分目錄 `pytest -n 8`（預設標記） | 全部 0：api 1340（1 skipped）、bot 67、cli 148、content 3166、engine 5120、llm 495、narrative 475、roguelite 279、server 77、shared 76、sim 180、skillgen 4634（7 skipped）、world 1328、頂層 200 |
| `pytest -n 8 -m slow tests/cli` | 0（44 passed） |
| 前端 `tsc --noEmit` | 0 |
| 前端 `vitest run`（全部） | 0（390 檔、4800 passed） |
| 前端 `build` | 0 |
| OpenAPI 重產比對（merge 後） | 沒有差異 |

註：
- 機器同時有其他 agent 在跑，負載 100%。
- cli 第一次 `-n 8` 時，xdist 主程序在測試全部跑完（100%）後很久沒結束，被我停掉。改用單程序重跑 `tests/cli`：148 passed，結束碼 0。
- roguelite 第一次也是同樣情形被我提早停掉；加 `--timeout=900` 重跑：279 passed，結束碼 0。其餘目錄都一次通過。

worktree 裡原本沒有 `client/node_modules`，先跑了 `corepack pnpm -C client install --frozen-lockfile`（node_modules 在 .gitignore 內，沒有進 commit）。

## 10. 待 PM 決定

1. **範圍疊不疊屬性**（照最保守的做法）：
   - 只有「法術傷害、治療、護盾」在有持有者時疊屬性加成，和卡片「傷害／治療／護盾算法」同一組。
   - 投擲、獻祭、引爆符文、定時炸彈、直線衝撞、撞擊、推倒石柱：只寫骰子＋固定值。這些效果的屬性規則各不相同，沒有逐一對照引擎。
   - 沒有持有者的卡（三選一泛稱卡、`/api/skills/{id}`）只寫骰子＋固定值，句子照舊寫「＋智力加成」。
2. **範圍沒有乘的倍率**：
   - 高變異技能的基礎傷害折扣（句子另寫「（基礎傷害 ×0.75）」）、形態加成、修正規則、元素與天氣都沒乘進範圍。
   - 爆骰的上限照一般骰子寫。
   - 要不要乘，請 PM 定。
3. **武器技的數字照舊寫倍率「×0.4」**，沒有改成範圍（骰子來自武器）。
   - 傷害算法那一行的武器骰已改成「武器骰 30–100」。
   - 長說明的骰子行只在知道持有者的武器時才有。
4. **卡片以外還有骰子寫法**（這段範圍外，沒改）：
   - 狀態說明：`content/statuses.yaml` 的「回合開始時恢復 1d4 HP」等，以及 `narrative/status_info.py` 的持續傷害、回復。
   - 地形說明：`narrative/tile_info.py`（表面、爆炸）。
   - 主角面板的普攻與武器特性：`content/battle.py` `attack_formula_zh`「普攻：1d6＋智力 × 0.3」，截圖 1 左上看得到。
   - 閃現變化列表：`api/flash_changes.py` 的「骰子 2d6 → 3d6」與 837 行的傷害字。
   - 技能工坊的骰子選單：那是編輯用的輸入，應該保留骰子寫法。
   - 預算說明（開發用）。
   - 要不要一起改成範圍？
5. **走路預覽的範圍用「～」**：`client/src/battle/pathPreview.ts` 的 `damageText` 寫「−6～9」。
   - 計畫第 4 項點名的「預覽」是 `previewText.ts`（已是「–」），這裡沒改。
   - 改成「−6–9」減號和連接號會連在一起，要不要改請定。
6. **`flashChoice.json` 只改字、沒有重產**：
   - `scripts/export_flash_choice_fixture.py` 在目前的 main 就跑不動：`FlashStepError: skill_rand_75 第 1 次的變化 keyword_exploit 套用不了`，不是這段造成的。
   - 腳本的 `ATTR = 10` 也還是舊單位。
   - 夾具裡卡片的數字因此還是舊的「NdM」；主角夾具 `client/src/run/fixtures/run_campfire.json` 也是舊單位。
   - X10-3c 改閃現程式後若要重產，需要先修這支腳本。
7. **回復藥說明照計畫寫「回 20–120 HP」**。實際治療會再加體質 × 0.5（道具技能是法術治療），所以實際回得比說明多。要不要在說明裡提到加成？
8. **4 位數沒有實機案例**：目前內容沒有任何卡片範圍到 4 位數（不帶持有者最長 50–300，戰鬥中最長 120–320）。
   - 寬度靠 CSS 本來就換行、加上測試確認。
   - 頭目 HP 有 4 位數（3800），這次沒有截到頭目戰的 HP 文字。
9. **和 X10-3c**：交件前已 merge main（含 X10-3c），沒有衝突；`-m slow tests/skillgen/test_refactor_parity.py` 935 passed（結束碼 0）。
   - 這段改過 `tests/skillgen/test_flash_*.py` 的斷言（骰子 → 範圍）、`flashChoice.json` 3 處字；X10-3c 的姿態「進入代價」新字和 `flashChoice.json` 裡的不衝突（夾具裡沒有那條）。
10. `src/trpg/api/world_economy_schemas.py` 48 行 docstring 的例子「回 2d6 HP」：docstring 歸 X10-3c，沒動。

## 11. 平衡疑慮
- 沒有。這段只改顯示字，沒有改引擎與數值。CLI 戰鬥快照 7 個鍵都沒變。

## 開發 PM 裁定（2026-11-20）

合併：`Merge X10-3b`（--no-ff）。截圖已轉美術 PM 驗收。

待決 10 件：
1、2、3. 接受，照保守的做法。範圍只疊「確定會加」的部分；不確定的折扣、爆骰不放進範圍。
4. 排進 X10-3d：狀態說明、地形說明、主角面板的普攻、閃現變化列表裡的骰子寫法，照同一套規則改成範圍。
5. 排進 X10-3d：`pathPreview.ts` 改用「–」，和其他三處統一。
6. 排進 X10-3d：修好 `flashChoice.json` 匯出腳本的錯誤（`FlashStepError keyword_exploit`），屬性值換成新單位，再重產一次。
7. 排進 X10-3d：回復藥的範圍要把體質加成算進去，或者在長說明寫明「另加體質加成」，照最保守的那種做。
8. 接受。
9. 接受。
10. 排進 X10-3d。
