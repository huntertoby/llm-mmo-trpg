# X10-3d 報告：×10 顯示的剩餘地方

依據：`docs/phases/PhaseX10-3d計畫.md`、`PhaseX10-3b計畫.md`（骰子顯示定案）、`PhaseX10-3b報告.md`（含開發 PM 裁定）、`docs/art/X10-3b驗收.md`。
基準：開工時 `git merge main`（`9a7897f11`）；途中照協調者通知再 merge 一次 main（HC-1 併入後，merge commit `eda4681c4`，沒有衝突）。分支 `worktree-agent-a67f86577577b3f6d`，沒 push。
沒改 `docs/design/`、`config/`、HC-1 的 `scripts/hardcoded/`、`tests/test_hardcoded_scan.py`、`docs/phases/寫死數值-*`。沒跑全量、沒用 `-m ""`、沒試數值。

## 1. 交付與 commit

| # | 項目 | commit |
|---|---|---|
| 1 | 狀態、地形、主角面板普攻、閃現變化列表的骰子改範圍；docstring「回 2d6 HP」 | `4729a61b7` |
| 2 | 走路預覽 `pathPreview.ts` 改用「–」 | `507268782` |
| 3 | `flashChoice.json` 匯出腳本修好、屬性換新單位、重產 | `7a1eecdec` |
| 4 | 回復藥說明加「另加體質加成」 | `fb40d590a` |
| 5 | 美術驗收：截圖（含走路預覽的開發頁） | `a656cad41` |
| — | merge main（HC-1） | `eda4681c4` |
| — | 報告 | （本檔所在的 commit） |

## 2. 交付項目 1：四處骰子改範圍

規則照 X10-3b：骰面 × `quantity_scale`，再疊固定值；只寫範圍、連接號「–」；範圍下面多一行「擲 NdM，每點 ×10」（`trpg.shared.range_text.dice_note`）。不知道的倍率（狀態強度 `magnitude_permille`、潮濕治療減半等）不乘進範圍（X10-3b 裁定 1、2）。

- **狀態說明**（`src/trpg/narrative/status_info.py`）：
  - 持續傷害「回合開始時受到 1d6 火焰傷害」→「回合開始時受到 10–60 火焰傷害」＋下一行「擲 1d6，每點 ×10」；持續治療同樣。
  - 層數的超載反噬「受到 2d6 雷電傷害（不致命）」→「20–120」，骰子行接在超載那一行之後。
  - 這些行經過 `/api/glossary` 的 `rules_zh`，戰鬥中滑過狀態圖示、層數說明都會看到。
- **地形說明**（`src/trpg/narrative/tile_info.py`）：
  - 表面的回合開始傷害、治療（毒、聖光…）：「1d4」→「10–40」＋骰子行。
  - 物件爆炸：「爆炸範圍 3×3，2d6 火焰傷害」→「爆炸範圍 3×3，20–120 火焰傷害」＋骰子行；`flat` 疊進範圍（不再寫「+N」）。
- **主角面板的普攻**（`src/trpg/content/battle.py` `attack_formula_zh`／`rule_lines_zh`）：
  - 「普攻：1d6＋智力 × 0.3（目前 +48）」→「普攻：10–60＋智力 × 0.3（目前 +48）」；武器的 `flat` 疊進範圍。
  - 屬性加成照舊另寫「＋智力 × 0.3（目前 +N）」，不疊進範圍（保守：這行原本就是在講算法）。
  - `rule_lines_zh` 第二行是「擲 1d6，每點 ×10」，握法、背刺往後挪一行。這組行用在一輪的主角面板、戰鬥中的單位卡（`engine/view.py`）、開局武器說明（`/api/runs` 選武器、`/api/content`）。
- **閃現變化列表**（`src/trpg/api/flash_changes.py`）：
  - 骰子那一列的 `before_zh`／`after_zh`：「1d12 → 1d4」→「10–120 → 10–40」（沒有持有者，只疊固定值，同 X10-3b 的泛稱卡）。資料欄位 `before`／`after` 照舊是「1d12」。
  - 整個效果新加或拿掉的那句（`_phrase`）：「1d6 冰霜傷害」→「10–60 冰霜傷害」。
  - 變化列表沒有長說明的位置，沒加骰子行（套用後的卡片本身滑過有「擲 NdM」，X10-3b）。見待決 3。
- `src/trpg/api/world_economy_schemas.py` docstring 的例子「回 2d6 HP」→「回 20–120 HP」（OpenAPI 不含這段 docstring，重產後沒有差異）。
- 前端夾具 `client/src/battle/fixtures/glossary.json` 重產（`scripts/export_client_fixtures.py`；其他三個夾具沒變）。
- 新測試 `tests/narrative/test_x10_3d_ranges.py`：全部狀態、層數、表面、物件的規則句，除了「擲 NdM，每點 ×10」那行，都找不到「NdM」；每把武器的普攻行是範圍、第二行是骰子行；閃現骰子列的前後顯示字是範圍。
- 既有測試改斷言（只改斷言）：`tests/narrative/test_rule_texts.py`（燃燒的句子、普攻行開頭）、`tests/engine/test_weapons_ranged.py`、`test_weapons_dual_dagger_firearm.py`（握法從 `[1]` 挪到 `[2]`）。

## 3. 交付項目 2：走路預覽
- `client/src/battle/pathPreview.ts` `damageText`：「−6～9」→「−6–9」（減號 U+2212 接數字，範圍用 U+2013）。`pathPreview.test.ts` 4 處跟著改。

## 4. 交付項目 3：`flashChoice.json` 匯出腳本

**報錯原因**：點燃斬白板（`compose_whiteboard(75, recipe_id="kindle", …)`）在 ×10 之後組出的是「耐力 40、冷卻 1」（原本「耐力 2、冷卻 2」），預算已經填滿。`keyword_exploit` 要加一段「目標被撞過時才有」的武器傷害，連最小的 ×0.3 都超預算（106.3%，上限 100%），所以每份草稿都重調失敗、`derive_chain` 拋 `FlashStepError`。不是引擎的錯：正式出題（`make_offer`）本來就不會出套用不了的變化，只有這支腳本是手指定變化。

**修法**（只改腳本）：
- 白板種子 75 → 107（`WHITEBOARD_SEED`）：107 組出「AP 2、耐力 20、冷卻 2、射程 4、燃燒 5 回合」，就是使用者截圖那組數字的新單位；`base`、`transform`、`stance` 三組的 12 個變化都套得上。我掃過種子 0～399，同時符合這組數字、四組都套得上的只有 107、115、313；107 的 `llm` 組最接近原本（見待決 1）。
- 卡片屬性 `ATTR = 10` → `100`（新單位）。
- 技能 ID 跟著變（`skill_rand_75` → `skill_rand_107`）；前端沒有地方寫死這個 ID。

**重產 diff 摘要**（`client/src/dev/fixtures/flashChoice.json`，+515／−393）：
- 主角第一招：耐力「2」→「20」（其他代價、燃燒 5 回合不變）。`transform`、`stance` 組的「耐力 2 → 沒有」跟著變「20」。
- `base`、`rows`、`transform`、`stance` 的大標全部不變；`base` 的四個選項照舊（射程 +1、蓄力、積水、撞擊加碼 3 成武器傷害）。
- `reflash`、`reflash_major`：所有骰子變成範圍（「傷害從 1d12 變成 1d4」→「傷害從 10–120 變成 10–40」、「4d4 火焰傷害」→「40–160 火焰傷害」）；法力也變新單位（「3 → 5」→「64 → 48」）。`reflash_major` 兩個橋接選項的順序對調（冰凍在前、被標記在後），內容和 X10-3c 之後的出題一致。
- `llm` 組：第 3 個的額外傷害 3 成 → 4 成；第 4 個（轉型）從「轉成姿態」變成「轉成召喚」（見待決 1）。
- 整份夾具的「NdM」從 112 個減到 66 個；剩下的是結構化欄位 `dice`（「3d6」原樣保留）與主角夾具裡沿用的舊招（見待決 2）。

**連帶修的前端斷行**（`client/src/run/flashChoice.ts`）：重產後 vitest `fl1jFlashWrap` 抓到「10–120 火焰」被切成「從 10」「–」「120 變成」：數字＋單位不斷行的規則認得「1d4」但不認得範圍。`NUM_UNIT_RE` 多認「10–120」，前後沒黏字的範圍也整段不斷行（瀏覽器會在「–」後面斷）。測試加一條；1600 那張重閃卡的斷言改成「10–120 火焰」「10–40 火焰」。這也是項目 1 上線後實機會遇到的斷行，一起修。

## 5. 交付項目 4：回復藥

- 算不準：說明（商店、背包的 `description_zh`）不知道是誰喝，體質加成沒辦法算進去。戰鬥中的道具卡在 X10-3b 已經照持有者疊了加成。
- 照保守的做法：範圍維持骰子的「20–120」「40–240」，後面加一句「另加體質加成」：
  - 小回復藥：「戰鬥中回 20–120 HP，另加體質加成；野外喝一瓶回 20% HP。」
  - 中回復藥：「戰鬥中回 40–240 HP，另加體質加成；野外喝一瓶回 35% HP。柳掌櫃好感度中立以上才賣。」
- 法力藥是 `restore_resource` 固定 100，不吃屬性，沒改。
- `tests/test_x10_texts.py` 加斷言：道具技能是 `spell`／`con`，說明含「HP，另加體質加成；」。

## 6. 交付項目 5：美術驗收
- 工坊的建議範圍維持全形「～」，沒改。
- 4 位數範圍：目前內容沒有。掃過全部技能卡（不帶持有者）最長「40–320」、名詞表最長「20–120」、武器普攻最長「20–120」。所以沒有 4 位數的 800 截圖；800 真 1 倍另外交了兩張（閃現變化列表、走路預覽）。

## 7. 截圖（`docs/art/shots/x10-3d/`）

做法：無頭 Chrome `--headless=new --mute-audio --force-device-scale-factor=1`，除錯埠 9767，網址都帶 `mute=1`，視口用 CDP 設 1600×900／800×900、`deviceScaleFactor` 1。伺服器是暫存區的啟動腳本：`create_app(static_dir=client/dist, tuning=True)`、埠 8767、存檔在暫存區、LLM 用 mock、`TRPG_DEV_ROUTES=1`。開發頁用 vite dev server（埠 5181）。結束時三個程序都停了，三個埠都已關閉。

| 檔案 | 內容 | 來源 |
|---|---|---|
| `1-status-burning-1600.jpg` | 滑過燃燒圖示：「回合開始時受到 10–60 火焰傷害」「擲 1d6，每點 ×10」 | 實機：單場戰鬥油庫，引火彈點燃站在油上的盜賊弓手，釘選單位卡後滑過狀態圖示 |
| `2a-terrain-object-1600.jpg` | 滑過油桶：「爆炸範圍 3×3，20–120 火焰傷害」「擲 2d6，每點 ×10」 | 實機：同一場 |
| `3-hero-attack-1600.jpg` | 一輪主角面板：「普攻：10–60＋智力 × 0.3（目前 +48）」「擲 1d6，每點 ×10」 | 實機：`?dev=1&screen=flash` |
| `4-flash-changes-1600.jpg` | 閃現「踏焰炎擊」第 1 次的四個選項：「傷害 10–120 → 10–80」「額外傷害 沒有 → 新 10–60 火焰傷害」 | 實機：同上，按閃現出題 |
| `4b-flash-changes-800-1x.png` | 同上，800 寬真 1 倍 PNG | 實機 |
| `5-path-preview-1600.jpg` | 走路預覽小牌「陷阱 −60–140・定身（可能）」 | 開發頁 `client/dev/x10-3d-path.html` |
| `5b-path-preview-800-1x.png` | 同上，800 寬（地圖縮放 0.531）真 1 倍 | 開發頁 |
| `6-flash-fixture-reflash-1600.jpg` | 重產後的夾具 `reflash_major`：前 → 後都是範圍、「10–120 火焰傷害」不斷行 | 開發頁 `flash-choice.html?set=reflash_major` |
| `6b-flash-fixture-base-1600.jpg` | 重產後的夾具 `base`：點燃斬「AP 2、耐力 20、冷卻 2、射程 4、燃燒 5 回合」與原本四個選項 | 開發頁 `flash-choice.html?set=base` |

- **走路預覽用開發頁**：實機走不出帶範圍的小牌。範圍只出現在「最少後果」和「最多後果」都有傷害的事件，也就是踩看得見的陷阱；目前內容沒有任何敵人會放陷阱（`content/units` 沒有陷阱技能），藉機攻擊在最少後果是落空、只寫最大值。開發頁 `client/src/dev/x10PathGallery.ts` 用手寫的路徑預覽（和 `pathPreview.test.ts` 的陷阱同形狀），經過真的 `pathDraw` ＋ `BattleRenderer.setHighlights` 畫在戰場上。開發頁有 commit（`a656cad41`），不在正式 build。
- **回復藥沒有截圖**：說明只出現在大世界的商店與背包。新角色背包沒有藥；霧渡鎮柳掌櫃只能說話、聊天，沒有開店的按鈕（應該要先接渡婆婆的任務），開發路由也沒有給道具的入口。改字有 `tests/test_x10_texts.py` 斷言。見待決 4。

## 8. 快照與夾具

| 檔案 | 預測 | 實際 |
|---|---|---|
| CLI `skills_list`、`skills_show_all/00～15` | 不變（技能清單不印狀態、地形、普攻、閃現差異） | 不變 |
| CLI 7 個 `battle_*` | 不變（戰鬥輸出不印單位卡的武器行） | 不變 |
| `client/src/battle/fixtures/glossary.json` | 會變（狀態、表面、物件、層數的規則句） | 變，已重產（項目 1） |
| `skillCards.json`、`unitDolls.json`、`raceLooks.json` | 不變 | 不變 |
| `client/src/dev/fixtures/flashChoice.json` | 會變（項目 3 重產） | 變，見第 4 節 |
| OpenAPI／`schema.d.ts` | 不變（沒有新欄位） | 重產後沒有差異 |

CLI 快照沒有鍵要重產；`-m slow tests/cli/test_output_snapshots.py` 在項目 1 之後跑過一次 24 個全過，交件前的 `-m slow tests/cli` 也包含它。

## 9. 檢查

以下都在 merge HC-1 之後、最後一個 commit 的樹上跑。

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（全專案） | 0 |
| `lint-imports` | 0 |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類：0） |
| `pytest tests/test_hardcoded_scan.py` | 0（22 passed） |
| 分目錄 `pytest -n 8`（預設標記） | 全部 0：api 1340（1 skipped）、bot 67、cli 148、content 3166、engine 5120、llm 495、narrative 479、roguelite 279、server 77、shared 76、sim 180、skillgen 4637（7 skipped）、world 1328、頂層 224 |
| `pytest -n 8 -m slow tests/skillgen/test_refactor_parity.py tests/cli` | 0（979 passed） |
| 前端 `tsc --noEmit` | 0 |
| 前端 `vitest run`（全部） | 0（390 檔、4800 passed） |
| 前端 `build` | 0 |
| OpenAPI 重產比對 | 沒有差異 |

**HC-1 涵蓋測試**：merge 後跑 `classify.py --check` 與 `tests/test_hardcoded_scan.py` 都過，這段新增的字串與數字都已被既有規則涵蓋，**沒有在 `scripts/hardcoded/classes.yaml` 補規則**。

## 10. 待 PM 決定

1. **`flashChoice.json` 的 `llm` 組第 4 個選項變成召喚，文字還是姿態的**：
   - 種子換成 107 後，第 3 次大變化真的出題時第 4 個是 `to_summon`（原本 `to_stance`）。
   - `LLM_TEXTS` 照出題順序掛文字，所以召喚選項掛著「赤焰立姿／以長劍為引…進入燃燒的架勢」（LF-1 報告本機模型給姿態的字）。
   - 測試只看名稱來源（`llm`／`template`），全過；但開發頁上看起來是「姿態的名字配召喚」。
   - 要不要換一段召喚的字（我沒有本機模型的召喚輸出可用，不自己編），或改成照模板掛字，請定。
2. **主角夾具 `client/src/run/fixtures/run_campfire.json` 還是舊單位**：`flashChoice.json` 的 `hero` 第一招以外都照抄它（X10-3b 待決 6 提過）。這段範圍只寫了 `flashChoice` 的腳本，沒動它。要重產的話是另一支流程。
3. **閃現變化列表沒有骰子行**：列表一列只有「前 → 後」兩格，沒有長說明的位置；套用後的卡片滑過時已有「擲 NdM，每點 ×10」（X10-3b）。要不要在列表加說明卡（例如欄位名的術語 `term`），請定。
4. **回復藥沒有截圖**：見第 7 節。要實機截，需要能開柳掌櫃商店的存檔，或開發路由給道具。
5. **狀態圖示的滑過說明把規則行用空白接起來**：截圖 1 是「…刷新持續時間。 回合開始時受到 10–60 火焰傷害 擲 1d6，每點 ×10」。名詞表其他地方是一行一條；這張提示卡是既有的接法（不是這段改的），骰子行接在句尾讀起來像同一句。要不要改成換行或「；」，請美術 PM 看。
6. **武器特性「祝禱」的骰子**（`WeaponDef.trait_lines_zh`：「祝禱：普攻命中時，最近的隊友回復 1d6 HP」）也在主角面板，但計畫只點名「普攻」，沒改。要改的話 `trait_lines_zh` 要多帶 `core`（也用在引擎預覽的備註）。
7. **普攻行不疊屬性**：範圍只疊骰子與武器固定傷害，屬性加成照舊寫「＋智力 × 0.3（目前 +48）」。若要和戰鬥中技能卡一樣把「目前加成」疊進範圍，請定。

## 11. 平衡疑慮
- 沒有。這段只改顯示字與開發夾具，沒有改引擎與數值；CLI 戰鬥快照沒變。
