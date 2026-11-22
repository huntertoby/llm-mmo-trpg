# Phase HC-6c 報告：介面文字收尾（7 個介面項目＋前端剩下的 text）

依據：`docs/phases/PhaseHC-6c計畫.md`。基準：main `29b6c7b01`。分支 `worktree-agent-a4345a205839e6ffe`，沒 push。
沒改數值、沒動 `docs/design/`、`config/`、`CLAUDE.md`、計畫檔。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1.1 `base_points` 說明用字（HC-B 裁定 6） | `f23121c08` | 7 個原語的 `description_zh`（含一個參數說明）與 `workshop_text.yaml` 的對照原文改寫成 `primitive_points.<原語>` |
| 1.2 沒有招用到的形狀基礎值（HC-W2 裁定 1） | `1d0ff9449` | 新模組 `api/tuning/shape_usage.py`，由資料算；工坊說明接「目前沒有招用到，改了暫時沒效果。」 |
| 1.3 祝禱的骰子字（X10-3d 裁定 6） | `c0510b9c1` | `WeaponDef.trait_lines_zh(core, …)`：祝禱有骰子時寫範圍＋骰子行 |
| 1.6 詞彙表的骰子欄（AR-X10 待決 5） | `253789950` | `GlossaryEntry.rules_dice`（預設 `()`）；前端 `tipParts` 改讀欄位、不再比對句型 |
| 1.4 地面提示的骰子行（AR-X10 待決 4） | `870fb65a2` | `SurfaceBadge` 分段；開發頁 `client/dev/hc6c-gallery.html` |
| 1.5 組裝列說明的骰子行（AR-X10 待決 4） | `2d4b32dbc` | `statusTile`／`surfaceTile` 帶 `parts`，`SkillIconView` 四處 `PartTip` 都傳 |
| 1.7 路徑預覽的「要多擲」（AR-X10 補件裁定） | `84bbd726d` | 引擎路徑事件、`PathEventOut` 多 `save_roll`；`trapText` 照它分 |
| 2 前端剩下的 22 筆 text | `4cb700d8d` | 9 處改組字（`GameRulesOut` 多 5 欄＋既有欄位）、新增 2 條 const 規則；text 22 → 2 |
| 3 營火「重閃」懸掛縮排 | `3abe1b85a` | 「重閃」與內文分兩欄 |
| 4 收尾 | `5dffe6978` | `--md` 重產清單（沒有變 0 筆要刪的規則，`--unused` 沒有輸出） |
| 截圖 | `1f9fce5f5` | `docs/art/shots/hc-6c/` 12 張 |
| 報告 | 本 commit | |

規格的順序是 4、5、6，實作時先做 6（結構化欄位），4、5 直接用它，避免先寫一次句型比對再改掉。

## 2. 七個介面項目：出處與處理

### 2.1 `base_points` 的說明用字（HC-B 裁定 6「要改，併進 HC-6」）

只有開發者模式（`?dev=1`）看得到（技能工坊的效果原文；玩家模式顯示 `workshop_text.yaml` 的 `player`，沒動）。`reveal_base_points`、`revive_base_points` 是 `skill_budget.yaml` 現有的鍵名，不改。

| 原語 | 改前 | 改後 |
|---|---|---|
| shockwave | 預算：固定 base_points（形狀倍率另算；初值，未經模擬）。 | 預算：固定點數 primitive_points.shockwave（skill_budget.yaml；形狀倍率另算；初值，未經模擬）。 |
| leave_form | 不另計點數（base_points 0）， | 不另計點數（skill_budget.yaml 的 primitive_points.leave_form）， |
| inscribe | 預算：base_points × inscribe_duration_permille（依 duration；… | 預算：primitive_points.inscribe × inscribe_duration_permille（skill_budget.yaml；依 duration；… |
| blow_surface | 預算：base_points × 距離。 | 預算：primitive_points.blow_surface（skill_budget.yaml）× 距離。 |
| clear_surface | 預算：base_points 3（形狀與對象倍率照一般效果）。 | 預算：primitive_points.clear_surface（skill_budget.yaml；形狀與對象倍率照一般效果）。 |
| enter_form | 預算：base_points 11（照姿態計，skill_budget.yaml 的 form_coefficient_permille）。 | 預算：primitive_points.enter_form（照姿態計，skill_budget.yaml 的 form_coefficient_permille）。 |
| enter_form.magnitude_permille | 預算 base_points × 幅度 | 預算 primitive_points.enter_form × 幅度 |
| absorb_surface | 層數＝add_stack 的 base_points × amount | 層數＝primitive_points.add_stack × amount |

- 原文裡寫死的「3」「11」「0」一起拿掉：點數已搬到可在工坊調的 `primitive_points`，留著現值會過時（待決 1）。
- 改的是規則包的 `description_zh`，所以 `ruleset_hash` 會變（待決 2）。

### 2.2 沒有招用到的形狀（HC-W2 裁定 1）

- 判斷由資料算（`unused_shape_bases`）：只看有查表的形狀（錐形、十字、環形、連鎖），把 `base_permille` +1 後重算內容庫全部技能（含道具技能）的預算，全部不變＝沒有招用到。依內容庫快取，一次約 0.1 秒。
- 現在的結果：錐形、環形、連鎖沒有招用到；十字有（陷阱的十字範圍）。和 HC-W2 報告一致。
- `tuning_fields.yaml` 三格的說明拿掉寫死的「目前的…招都會填…，所以改這格通常沒有效果」，改成程式接的句子：

| 欄位 | 改前 | 改後（`note_zh`，現在的資料） |
|---|---|---|
| `shape_budget.cone.base_permille` | 「錐形」沒填長度 size 時用的倍率。目前的錐形招都會填長度、改查上面三格，所以改這格通常沒有效果；調錐形請改上面依長度的三格。 | 「錐形」沒填長度 size 時用的倍率；填了長度的錐形招改查上面三格，調錐形請改那三格。目前沒有招用到，改了暫時沒效果。 |
| `shape_budget.ring.base_permille` | 「環形」沒填半徑…所以改這格通常沒有效果；調環形請改上面依半徑的兩格。 | 「環形」沒填半徑 radius 時用的倍率；填了半徑的環形招改查上面兩格，調環形請改那兩格。目前沒有招用到，改了暫時沒效果。 |
| `shape_budget.chain.base_permille` | 「連鎖」沒填跳數…所以改這格通常沒有效果；調連鎖請改上面依跳數的幾格。 | 「連鎖」沒填跳數 jumps 時用的倍率；填了跳數的連鎖招改查上面幾格，調連鎖請改那幾格。目前沒有招用到，改了暫時沒效果。 |

- 有一招不填錐形長度時，那句就不再出現（`tests/api/tuning/test_shape_usage_hc6c.py`）。
- 沒有查表的形狀（自身、單體…）、`by_value` 各格不加這句（待決 3）。

### 2.3 祝禱的骰子字（X10-3d 裁定 6）

- 現在唯一有祝禱的權杖是 `blessing: {flat: 30}`，沒有骰子，畫面字不變（「祝禱：普攻命中時，最近的隊友回復 30 HP」）。
- 有骰子時：「祝禱：普攻命中時，最近的隊友回復 10–60 HP」，長說明下一行「擲 1d6，每點 ×10」；固定值疊進範圍（同 X10-3d 的普攻）。戰鬥預覽的備註（`on_hit_only`）只寫範圍、不加骰子行（待決 4）。
- `trait_lines_zh` 多一個 `core` 參數（選填；祝禱有骰子卻沒給時報錯）。呼叫的五處（`routes/content.py`、`routes/runs.py`、`run_presenter.py`、`engine/view.py`、`engine/preview.py`）都改傳。
- 沒有截圖：現有資料畫面不變。測試 `tests/content/test_blessing_range_hc6c.py`。

### 2.4 地面提示（`SurfaceBadge`）與 2.5 組裝列說明（AR-X10 待決 4）

- 照 AR-X10 狀態提示的排法：骰子行自己一段、次要字色、不加分隔符號。
- 地面提示：`surfaceTipParts(id)` → `PartTip parts`。
- 組裝列：`AssemblyTile` 多選填 `parts`，`statusTile`、`surfaceTile`（以及沿用它們的 `statusIconTile`、工坊選項 `optionTile`）都帶；`SkillIconView` 的 `TipGlyph`、組裝算式 `TileView`、算式附帶部件、`OptionGlyph` 四處 `PartTip` 都傳 `parts`。`tip` 字串不變（標題、`tileTitle` 照舊）。
- 層數說明（`StackTip`）本來就是逐行，沒動。

### 2.6 詞彙表的骰子欄（AR-X10 待決 5）

- `GlossaryEntry.rules_dice: tuple[RuleDiceOut, ...] = ()`，`RuleDiceOut {line, count, sides, scale}`：`rules_zh[line]` 是骰子行。
- 後端：`trpg.shared.range_text.dice_note` 回傳 `DiceNote`（`str` 的子類，多帶 `dice_count`／`dice_sides`／`dice_scale`），名詞表照型別標出骰子行，不比對句型。現在有 10 行（毒、聖光×2、燃燒、霧歸、流血、中毒、再生、油桶、超載）。
- 前端：`tipParts(lines, dice)` 第二個參數是骰子行的索引；新 `entryTipParts(entry, fallback)`。`DICE_NOTE_RE` 刪掉。
- 測試：後端 `tests/api/test_glossary_dice_hc6c.py`（欄位標的行＝舊句型抓到的行，逐項相同）；前端 `ui/hc6cDiceField.test.ts`（照欄位分段和 AR-X10 的句型比對結果逐項相同；欄位說了算）。

### 2.7 路徑預覽的「要多擲」（出處：`PhaseAR-X10報告.md` 補件的開發 PM 裁定）

- grep `docs/art/`、`docs/phases/` 的「要多擲／重擲／路徑預覽」：唯一相關的是 AR-X10 補件 8.5 待決 1 與裁定「後端的狀態事件得多帶一個欄位，標明觸發後還要不要另外擲；排進佇列，和 HC-6 的 glossary 結構化欄位一起做」，玩法 PM 的用字已定（還要擲的加「可能」，觸發就一定附上的不加）。
- 引擎 `path_preview.py`：一次模擬裡，移動者先有 `status_save_rolled`、之後得到同一個狀態，這個路徑事件就標 `save_roll`；合併分支時任一分支擲過就是真。API `PathEventOut.save_roll`（預設 `false`）。
- 前端 `trapText`：陷阱不確定時，`save_roll` 為假的狀態不加「可能」；陷阱確定時照舊看 `certain`。
- 現有三個陷阱（捕獸夾的定身有 `save_attr`；毒池、灰燼地雷是表面）實機字不變，所以沒有截圖；vitest 兩條（真實伺服器的 `certain=false` 兩種 `save_roll`）＋ pytest（捕獸夾的定身 `save_roll` 為真、合併規則）。
- 只是預覽的資訊欄位，不影響結算（78 場 different=0），不升 `LOG_FORMAT`。

## 3. 前端剩下的 text（22 → 2）

### 3.1 改組字（目前的值組出來逐字相同，`client/src/ui/hc6cRuleText.test.ts`）

| 位置 | 原本寫死 | 改讀 |
|---|---|---|
| `battle/summonControl.ts` 守護我「待在你 2 格內」 | 2 | `rules.summon_guard_radius`（新，`ai_profiles.yaml` 的 `summon.guard_radius`）；`MODE_HINTS` → `modeHints()` |
| `ui/SummonPanel.tsx` 操控說明「指揮要花 1 AP」「灌注要花 1 AP」 | 1、1 | 戰鬥畫面既有的 `summon_command_ap_cost`、`summon_infuse_ap_cost`；`TIP_TEXT` → `summonTipText(view)` |
| `screens/StartScreen.tsx`「標準隊友補到 3 人」 | 3 | `rules.battle_team_size`（新，`trpg.sim.lineup.TEAM_SIZE`）；`battleAlliesText()` |
| `ui/statusCard.ts` 源力「每場至少 1 點」 | 1 | `rules.source_min_at_start`（新，`core.yaml`）；`sourceRuleText()` |
| `world/BagScreen.tsx`、`EconomyPanel.tsx`「戰鬥中 1 AP 使用」 | 1 | `rules.item_skill_ap_cost`（新，`world/items.yaml`；HC-7 b 搬的值）；`bagView.pouchUseText()` |
| `world/EventCard.tsx` 線索「最多 +2」（兩處） | 2 | `rules.situation_care_max`（新，`world/situation_rules.yaml` 的 `check.care_max`） |
| `world/range.ts` 重選「2 個關鍵字」 | 2 | 既有的 `rules.start_keywords`（重選走 `new_keyword_run`，和開局同一個 `start.keywords`） |
| `world/WorldPanel.tsx` 雇用「0～2 名隊友」 | 2 | 隊伍既有的 `PartyView.max_hired`；`PartyPanel.hireHintText()` |

### 3.2 改判 const（`classes.yaml` 兩條新規則，note 附理由）

- `ts-hc6c-engine-text`（引擎寫死、沒有資料欄位）：
  - 源泉格 +1（`legend.ts`、`statusCard.ts`；`engine/source.py` 一格一點、取走就消失）；
  - 戰前佈置「免費放 1 個」「每場 1 個」（`prep.ts`；一次的窗口，放了或跳過就關）；
  - 召喚物「每隻每輪 1 次」「每隻每輪最多指揮 1 次」（`summonControl.ts` 3 筆、`SummonPanel.tsx` 2 筆；每輪一個旗標）；
  - 「開火一次用掉 1 發」（`statusCard.ts`）。
- `ts-hc6c-structure-text`（結構）：
  - 線索「核對得到才 +1」（`EventCard.tsx` 2 筆；用心清單一筆一點）；
  - 鍛造「指定部位＋1 條詞條」「每種用 1 個」（`SmithyPanel.tsx`）；
  - 誓約「同時 1 個」（`WorldGrowth.tsx`；`OathView.current` 單一欄位，同 HC-6b 的 `ts-hc6b-single-text`；規則包沒有這個值）；
  - 雇用「免費帶 0～」的 0（不帶＝獨行）。

### 3.3 留 text（2 筆，見待決 5）

- `world/growthPanel.ts`「升級時每級 +2」、`world/OpeningDialog.tsx` 配點範例（開局 4 點、智力 12…）。資料是 `attribute_points_per_level` 20（×10 量尺），顯示怎麼換算 HC-6b 起就沒定案，照規格「出處沒定案的不做」。`ts-ui-text` 的 note 與檔案清單已更新。

## 4. API 新欄位與夾具

| 型別 | 欄位 | 備註 |
|---|---|---|
| `GlossaryEntry` | `rules_dice: RuleDiceOut[]` | 預設 `()`（規格要求有預設值） |
| `RuleDiceOut`（新） | `line`、`count`、`sides`、`scale` | |
| `GameRulesOut` | `source_min_at_start`、`summon_guard_radius`、`battle_team_size`、`item_skill_ap_cost`、`situation_care_max` | 必填（同 HC-7 b：伺服器一律由內容庫填）；缺 `world/items.yaml`、`world/situation_rules.yaml` 時名詞表報錯 |
| `PathEventOut` | `save_roll: bool` | 預設 `false` |

- `WorldEconomy` 多 `item_skill_ap_cost`（載入 `world/items.yaml` 時記下）。
- `client/openapi.json`、`schema.d.ts`、`battle/fixtures/glossary.json` 重產（每項多 `rules_dice`、`rules` 多 5 鍵）；其他夾具不變。
- 前端手寫的 `GlossaryEntry`／`PathEvent` 物件補新欄位：`render/glossaryNames.test.ts`、`render/statusIcon.test.ts`、`battle/pathPreview.test.ts`、開發頁 `dev/x10PathGallery.ts`。

## 5. 營火「重閃」按鈕（`docs/art/HC-3看圖.md`）

- 按鈕內容拆成 `.reflash-word`（「重閃」，不換行、不縮）和 `.reflash-body`（內文、轉型藍字、變弱提醒、沒有選項的說明）；按鈕 `display: flex; align-items: baseline; gap: 1em`。原本的全形空白拿掉，改用 `gap`。
- 結果：三個鈕都是「重閃」在左、內文在右換行對齊（截圖 5、6）。
- 測試 `run/hc6cReflashIndent.test.ts`。

## 6. 筆數（`classify.py`）

| | config | scale | const | text | layout | guard | 合計 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 後端開工 | 28 | 18 | 9280 | 0 | 0 | 486 | 9812 |
| 後端交件 | 28 | 18 | 9294 | 0 | 0 | 486 | 9826 |
| 前端開工 | 0 | 0 | 5491 | **22** | 54763 | 0 | 60276 |
| 前端交件 | 0 | 0 | 5515 | **2** | 54763 | 0 | 60280 |

- 沒歸類 0；`--unused` 沒有輸出；`--md` 重產 `docs/phases/寫死數值-清單.md`。
- const 增加的是新程式的字（測試、`shape_usage.py`、`DiceNote` 等，都被既有規則涵蓋）與改判的 16 筆。
- 這段沒有搬完變 0 筆的規則（`ts-ui-text` 還有 2 筆，留著）。

## 7. 截圖（`docs/art/shots/hc-6c/`，jpg 80，單張 ≤ 40 KB，共 12 張）

- 做法：無頭 Chrome（`--headless=new --mute-audio --force-device-scale-factor=1`，除錯埠 9793），網址帶 `mute=1`；vite 開發頁用埠 5243；工坊用建置後的前端＋`TRPG_TUNING=1 trpg serve --port 8127`（存檔放 scratch）。改前在開工時、改程式之前拍。拍完 vite、伺服器、Chrome 都用 PID 關掉，三個埠都已關。

| 檔案 | 內容 |
|---|---|
| `1-ws-dev-text-before.jpg`／`-after.jpg` | 技能工坊 `?dev=1`、效果「清除表面」的原文：「預算：base_points 3」→「預算：primitive_points.clear_surface（skill_budget.yaml；…）」 |
| `2-tuning-cone-note-before.jpg`／`-after.jpg` | 數值工坊預算表「形狀倍率：錐形（沒填長度時）」的說明卡（第 2.2 節的字） |
| `3-surface-tip-before.jpg`／`-after.jpg` | 主角卡腳下毒表面的說明卡：骰子行從句尾改成自己一行、次要字色（開發頁 `hc6c-gallery.html`，正式的 `Hud`） |
| `4-part-tip-status-before.jpg`／`-after.jpg` | 工坊組裝列的狀態部件「燃燒」說明框（正式的 `OptionGlyph`） |
| `5-reflash-1600-before.jpg`／`-after.jpg` | 營火重閃（`panel-gallery.html#campfire`），1600×900 |
| `6-reflash-800-before.jpg`／`-after.jpg` | 同上，800×600（開發頁的營火框最寬 760，所以和 1600 的畫面相同） |

### 浮動卡實測（1600×900、800×600）

| 卡 | 滑進卡片 | 捲到底 | 釘住 | 關閉 |
|---|---|---|---|---|
| 腳下表面（`SurfaceBadge`） | 1600 ✓ | 內容不超高，不用捲（`scrollTop` 0／可捲 0），捲輪後卡片仍開 | 點卡片釘住，滑鼠離開仍開（`aria-expanded=true`）；800 同 | Esc 關閉 ✓；800 卡片四邊都在視窗內 |
| 組裝列部件（`OptionGlyph`） | 照現行設計不能滑進（`pin={false}`、`no-bridge`，只在滑過時顯示；不是這段改的） | — | 不能釘（同上） | 離開即關 ✓；800 卡片四邊都在視窗內 |

## 8. 一致性比對（基準 `git archive 29b6c7b01 src content`）

| 比對 | 結果 |
|---|---|
| 逐招預算＋驗證 442 招（`hc7b_dump.py`） | `same=442 different=0` |
| 每張地圖 3 種子 | `battles=51 different=0` |
| 78 場（`compare78.py`，同 a 段那組） | `battles=78 events=26206 different=0`；內嵌規則包只差 8 個原語說明（第 2.1 節） |

## 9. 檢查

開發中每個 commit 前跑 ruff check、ruff format --check、mypy、lint-imports、`classify.py --check`、tsc 與相關測試（經看門狗），都 0。

**交件前全量**（全部 commit 後 `git merge --no-edit main`：Already up to date，main 仍是 `29b6c7b01`）：

| 檢查 | 結束碼 |
|---|---|
| `scripts/check.py`（ruff、format、mypy、lint-imports、pytest、前端 install／typecheck／vitest、situation coverage） | 0（pytest 18247 passed、8 skipped；vitest 4866 passed）；已寫下通過戳記 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（995 passed） |
| `corepack pnpm -C client build` | 0 |
| `trpg content check` | 0（704 檔、442 技能） |
| `classify.py --check` | 0（沒歸類 0；`--unused` 沒有輸出） |

跑完之後沒有改程式；本報告是唯一之後加的檔（只有 `.md`）。

## 10. 複雜度與 noqa

沒有新加 `# noqa`。

## 11. 待 PM 決定（都照最保守的做了）

1. **原語原文拿掉寫死的點數**（2.1）：「base_points 3／11／0」改成指到 `primitive_points.<原語>` 的鍵名，不再寫數字（數字已可在工坊調，寫死會過時）。要留數字得改成組字。
2. **改原語說明會讓 `ruleset_hash` 變**（2.1）：`description_zh` 在規則包裡，舊戰鬥紀錄照 1.2 被拒（給 HC-7 b 的中文說明）。結算、事件都沒變，不升 `LOG_FORMAT`。
3. **「目前沒有招用到」只看有查表的形狀的基礎值**（2.2）：沒有查表的形狀（例如 `unit_pair`）、查表的各格即使內容庫沒有招用到，生成的招一用就有效，不加這句。
4. **祝禱的戰鬥預覽備註只寫範圍**（2.3）：長說明（武器卡、單位卡）才加「擲 NdM」那行；預覽備註是一行一條的短句，沒加。
5. **屬性點兩筆留 text**（3.3）：「每級 +2」與配點範例要等「屬性點顯示換算」定案（資料是 20）。
6. **`GameRulesOut` 新 5 欄必填**（4）：照 HC-7 b 的做法不給預設值；`battle_team_size` 讀的是程式常數 `TEAM_SIZE`（`sim/lineup.py`，const），不是內容。
7. **誓約「同時 1 個」改判 const**（3.2）：規格說「規則包裡有值就改讀」；查過沒有這個值（`OathView.current` 是單一欄位），照 HC-6b 前例改判。
8. **`OptionGlyph` 的說明框不能滑進、不能釘**（7）：是現行設計（工坊選項鈕裡、點擊是選這個選項），這段只改內容排法，沒改行為。
9. **營火 800 截圖和 1600 相同**（7）：開發頁的營火框限寬 760。要看一輪實機窄寬的鈕得另拍。
10. **`tipParts` 的句型比對刪掉**（2.6）：骰子行只認名詞表的 `rules_dice`；之後別處（例如技能卡）若自己組「擲 NdM」字串，要自己標次要行。

## 開發 PM 裁定（2026-11-22）

合併為 68854a87c 推上 main。推送時 hook 的完整檢查有 1 筆失敗：`tests/infra/test_xdist_loadgroup.py::test_loadgroup_finishes_after_a_worker_crash`。它的 4 個子測試都通過，只是在負載下 240 秒內沒有結束，跟這段的改動無關。單獨重跑 3 passed，再推一次就過了。這筆列進不穩測試的佇列，和 `wish_pregen` 那筆一起看。

1. 接受。原語說明本來就寫滿鍵名，改成鍵名一致，也不會過時。
2. 接受。照 `戰鬥紀錄格式變更.md` 1.2 處理，`LOG_FORMAT` 不升。
3. 接受。
4. 接受。
5. 接受。等「屬性點顯示換算」定案後再處理。
6. 接受。
7. 接受。
8. 接受。這段不改行為。
9. 接受。窄寬實機的截圖等下一次動到營火時補拍。
10. 接受。往後若有別處自己組「擲 NdM」，記得標次要行；這條寫進上手筆記的佇列。
