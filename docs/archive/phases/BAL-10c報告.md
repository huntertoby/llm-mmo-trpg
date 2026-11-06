# BAL-10c 報告：BAL-10b 三個修正＋閃現目錄依種子打亂

玩法 PM 2026-10-31 決定（見 `docs/design/06-技能.md` 6.34.4 的 BAL-10b 定）＋開發 PM 技術決定。沒有連真模型。

## 做了什麼
1. **變身姿態只出修正類（回到 BAL-2c）**：`stance_cost_light`／`stance_cost_heavy` 的 `cost_fields` 清空、summary 拿掉「變身姿態：進入冷卻 ±1」；`flash_templates.yaml` 註解寫明玩法 PM 2026-10-31 的理由（姿態進入後一直持續，進入冷卻幾乎不是代價）。程式（`_form_cost_drafts`）不動：`cost_fields` 空就不出。測試改成斷言變身姿態不出費用類（`test_flash_bal10b.py`、`test_flash_form_bal2c.py`、`test_flash_stance_all_bal2b.py`）；卡片＝引擎冷卻的測試改用有進入冷卻的熊形態夾具＋`stance_potency`。
2. **`stance_enter_light` 也能減進入時的法力、耐力**：`cost_fields: [ap_cost, cooldown, mana, stamina]`；`_entry_cost` 對法力、耐力減到 0 ＝ 代價消失，所以最少留 1（冷卻仍可減到 0，維持原有行為）；維持費不動。新測試 `test_enter_light_cuts_mana_or_stamina_but_keeps_one`（mana／stamina 各一）：只減 1、剩 1 就不出、預算窗與強度下限（`_sound`）、效果與維持費不變、卡片費用＝實戰數字。
3. **`mod_cost` 不讓代價消失**：拿掉整條移除的 `_DROP_DRAWBACKS`（AP +1、召喚上限 −1、射程 −1）；傷害、治療、命中減了就歸 0 的也不出。測試：重踏、精英召喚三個階級都不出 `mod_cost`；2 格以上（傷害 −2 級距、命中 −2）照出且最少留 1、規則條數不變；只剩 1 格的不出。`test_mod_cost_lightens_a_drawback...` 的代價計算同步簡化（`done >= 1`：目前內建只有一招還出得來）。
4. **閃現目錄依種子打亂**：新增 `FlashCatalog.shuffled(seed, label)`（`trpg.skillgen.flash_catalog`）：類別、模板、每個模板的 keyword／element／shape 選單各自「先排序再依 `Rng(seed).fork("menu/flash/<tag>")` 打亂」，做法同 4-L6 的 `menu_order`。`propose_variations` 在確認目錄非空後用這一題的 `request.seed` 與 `seed_tag` 打亂，`<catalog>` 區塊與 JSON schema 列舉共用同一個順序；`pool` 與 `resolve` 不變，所以驗證、模板補位（`make_offer`）、模擬 client 與確定性都不變。**prompt 文字結構沒改，不升版本（仍 `flash-variation/2`）。** 測試（`tests/llm/test_flash_propose.py` 末四個）：同種子同順序、不同種子／不同題目標籤不同順序、打亂只改呈現（pool、可解析的變化、參數集合、schema 與 catalog 同序）、各種子下同一個回覆收下同一組合格的變化。
5. **行為快照** `tests/skillgen/fixtures/refactor_3wr2.json` 重產：**只有 3 筆變**，都是 `skill_form_demon`（種子 3、11 的 tier 1、種子 5 的 tier 2）閃現出題——變身姿態不再出費用類，選項少了。其他 BAL-10b 的 13 筆不變（複合技、修正型被動的變化還在）；完整技能強度、升階重配不變；LLM 目錄打亂不影響快照（快照走模板補位）。

## 姿態列前後（`scripts/flash_minor_coverage.py --jobs 8`，同 BAL-10b 參數）
產物：`docs/phases/BAL-10/minor_coverage_bal10c.md`／`.csv`（「之前」是 `minor_coverage_bal10b.*`）。列＝(技能, 角色階級)，數字是「第 1 次／第 2 次選項數 < 2 的列數」。

| 類別 | 列數 | 第 1 次 <2 | 第 2 次 <2 | 最低階 第 1 次 <2 | 最低階 第 2 次 <2 |
|---|---|---|---|---|---|
| 姿態（內建 12 招） | 30 | 0 → **24** | 4 → **24** | 0 → **10** | 4 → **10** |
| 姿態（白板） | 3 | 2 → **1** | 3 → 3 | 1 → **0** | 2 → 2 |
| 修正型被動（內建） | 53 | 34 → 36 | 48 → 49 | 12 → 12 | 17 → 17 |
| 全部（972 列） | 972 | 126 → 151 | 237 → 258 | 37 → 46 | 100 → 106 |

- 內建姿態的 24 列（8 個形態 × tier，加上其他）退回 BAL-2c／10a 的狀況：變身姿態只剩「強效（形態幅度）」一個選項，第 1 次 1 個、第 2 次 0～1 個。這是玩法 PM 決定的代價，預期內。
- 白板姿態（3 列）：`stance_enter_light` 加入法力／耐力後，白板 flame／ironwall（進入代價是法力）多一個選項，第 1 次不足的列 2 → 1；但白板裡的變身姿態同樣失去費用類，`skill_rand_2` 3 階 4/4 → 2/1、`skill_rand_3` 3 階 3/1 → 1/0（逐列見 csv）。
- 修正型被動 +2、+1 列：`mod_cost` 不再拿掉一級代價（重踏、精英召喚等）；預期內。

## 待 PM 決定
1. **【數值】變身姿態閃現選項太少**：8 個形態在各階級第 1 次只剩「強效」一個選項（24 列 < 2）。要補救只能新增「不是費用」的形態旋鈕（例如形態的某個副效果、持續時間），或接受（形態本來就是一次性的大招，靠大變化成長）。
2. **【數值】修正型被動 `mod_cost` 的出現率**：只剩傷害／命中有 2 格以上代價的才出；內建目前只有 1 招在 tier 3 還出得來。若要讓它有存在感，需要內建修正型被動多一些「多格代價」的設計（玩法決定）。
3. 目錄打亂只影響真模型，本段沒連模型，**實際位置偏好是否下降要等下一次真模型評估**（`scripts` 的閃現多樣性評估）才能確認；打亂範圍包含 keyword／element／shape 選單，若想只打亂模板順序，改 `FlashCatalog.shuffled` 一處即可。

## 複雜度與例外
無新增 `noqa`。

## 驗證
- ruff check、ruff format --check、mypy（902 檔）、lint-imports（7 kept）通過。
- pytest（`-m "(slow or not slow) and not llm" --timeout=1800 -n 8`）：tests/skillgen、tests/llm、tests/content、tests/roguelite、tests/narrative，結果 **6251 passed、14 skipped**（353 秒）。
