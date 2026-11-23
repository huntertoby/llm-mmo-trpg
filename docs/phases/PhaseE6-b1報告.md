# Phase E6-b1 報告｜招牌同時 3 個、改寫規則 1 個（引擎與內容層）

> 規格 `docs/phases/PhaseE6-b1計畫.md`；規則以 `docs/design/08-裝備.md` 8.27、8.28、8.29 E2 第 1 點、8.30 第 4、5、10 點（#180）為準。基準 `34bb21fa9`；交件前已合併 main（`e3bd9e8d6`，E6-a2）。`LOG_FORMAT` 升 `/139`。

## 1. Commit

| 項目 | commit |
|---|---|
| 3 `Loadout.chosen`、`LOG_FORMAT` `/139`（含 `戰鬥紀錄格式變更.md` 條目） | `ba413e1a5` |
| 1 改寫規則超過 1 條改成標灰 | `d6bd3c11c` |
| 2 招牌同時 3 個 | `d39155ae8` |
| 4 檢視層寫出標灰的原因 | `1a1061bb3` |
| 合併 main（E6-a2） | `2818a854d` |
| 報告 | 最後一個 commit |

## 2. 各項做法

### 2.1 `Loadout.chosen`（第 3 項）

- `Loadout.chosen: tuple[str, ...]`，每個是 `"<欄位>:<詞條 ID>"`（`equipment.chosen_key`），預設空、空的時候不輸出。
- 檢查：格式要是「合法欄位:非空 id」、不能重複；指到身上沒有的詞條（換裝後留下的舊勾選）不算錯誤，計算時忽略。
- `LOG_FORMAT` 升 `trpg-battle-log/139`；`docs/phases/戰鬥紀錄格式變更.md` 第 2 節加 `/139`。測試從常數推（`test_loadout_chosen_e6b1.py`），沒有寫死舊字面值（全庫沒有 `battle-log/138` 字面值）。

### 2.2 改寫規則同時 1 個（第 1 項）

- `loadout_problems` 拿掉「改變規則類詞條全身最多 1 個」的穿戴錯誤；前端測試模式、一輪與世界穿戴、內容檢查都不再擋。
- 新模組 `engine/gear/limits.py`，在 `make_unit` 的 `build_gear` 之後套用（`limit_gear`）：生效中的第 11 類詞條依 id 分組，超過 `caps.rule_affixes`（1）的標灰——`weight_permille` 設 0、`GearAffix.limited_by="rule"`（新欄位，`None` 不輸出，狀態序列化不變）。
- 誰留下：勾選的優先，其次欄位固定順序（主手 → 戒指 2），再依詞條 id（`limit_priority`）。沒勾過時照欄位順序（待決 1，PM 已裁定由 E6-b2 換裝時寫 `chosen`）。
- 標灰只把權重設 0，所以授予的技能、反應、規則改變都自然不生效；`_gear_rule_change` 只看生效的，標灰的那條不擋傳說啟動（測試鎖住）。
- `content/rules/equipment.yaml` 與 `tuning_fields.yaml` 只改說明文字（「超過時穿戴驗證失敗」→「超過的標灰」）。

### 2.3 招牌同時 3 個（第 2 項）

- `EquipmentCaps.signature_active`（必填），`content/rules/equipment.yaml` 填 3，開進工坊（「硬上限」組，提示 1～5）。
- 算名額（`limits._limit_signatures`）：
  - 只算標了 `signature` 的生效詞條（待決 2）。
  - 裝備給的技能（第 9 類）遞減時每份都生效，所以同 id 每份各佔 1 個（8.28、8.30 第 5 點）。地形規則、改寫規則、第 10 類反應同 id 第 2 條起權重 0，只佔 1 個。
  - 整條完全沒效果的不佔（`whole_no_effect`）：和種族或其他裝備完全重複的地形規則（`unit_rules.classify_sources` 的 `full`；名額在知道種族之後算）；普攻變形拿著不能套用的武器、或過不了預算閘門。被改寫規則名額標灰的也不佔。只對部分技能沒效果的照佔。
  - 一次標灰 1 條（排最後的那條）、重算到不超過名額：蓋過別條地形規則的那條被標灰後，被蓋過的那條有效果了，要重新算名額（測試鎖住）。
- 玩家照 `chosen`；玩家以外的單位沒有勾選，就是照欄位順序。
- `unit_rules` 多 `gear_rule_sources(rules, race, gear)`、`gear_strength(rules, gear)`（建立單位前用），原本的 `rule_sources`、`effective_strength`、`gear_move_room` 改成呼叫它們，行為不變。
- 沒有內容標招牌、也沒有標招牌的詞條時，`_limit_signatures` 第一個判斷就返回，不做重複計算。

### 2.4 檢視層（第 4 項）

- 標灰原因放在現有的 `AffixLineView.off_zh`（前端 `affixStatus.ts` 的 `inactiveNote` 會直接顯示），API schema、`client/` 不用改（待決 4）。
  - 改寫規則：「和{部位}的改寫規則衝突，沒有效果」（`RULE_LIMITED_ZH`，8.27 原文；部位是生效那條的）。
  - 招牌：「身上已經有 3 個招牌效果生效，這個沒有效果，可以在角色面板換選」（`SIGNATURE_LIMITED_ZH`，8.30 第 4 點原文；3 從 `caps` 帶入）。
- 因為名額標灰的不是重複：`duplicate_of` 為 `None`（同 id 的第 2 份授予技能被名額擋下時，不會誤寫成「和主手的…重複」）。
- 守則 14：裝備欄照現有規則，敵我看到同樣的詞條行（測試鎖住）。

### 2.5 `build_gear` 的其他呼叫端（PM 交辦的待決 7）

- `roguelite/progress.py` `hero_effective_attributes`：只取 `geared_template(...).attributes`（角色面板的常駐數值階數）。
- `world/league.py` `league_unit`：只取 `geared_template` 之後的最大 HP 算循環賽倍率。
- 名額只會把第 9～12 類（動作、反應、改寫規則、地形規則）的詞條標灰，這些都不是數值類，不進 `merged`；`geared_template` 只讀 `merged`。所以兩處算出的屬性與最大 HP 和套不套名額完全相同，**不改**。真正的戰鬥一律經 `make_unit`，已套名額。

### 2.6 其他

- 沒有新增 `# noqa`。`scripts/hardcoded/classify.py --check` 0（`signature_active` 放進 yaml 後沒有寫死的數字）。
- `config/`、`docs/design/`、`client/`、`CLAUDE.md` 都沒動。

## 3. 驗收

| 檢查 | 結果 |
|---|---|
| `uv run python scripts/check.py --all`（全部 commit、合併 main 之後） | 0（pytest 18848 passed、8 skipped；vitest 422 檔 4987；ruff、format、mypy、lint-imports、client typecheck、situation coverage 通過；已寫通過戳記） |
| `uv run python scripts/run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（995 passed；CLI 快照沒變） |
| 78 場（E5 的 `compare78.py`，去掉 `ruleset_hash`、內嵌規則包、`format`；基準 `34bb21fa9` 的 `git archive`） | 0；`battles=78 events=26741 different=0` |
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill` 違規） | 0；檔案逐位相同（`cmp` 0），`same=442 different=0` |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看 timing） | 0；`cells=204 different=0` |
| `ruff check`、`ruff format --check`、`mypy`、`lint-imports` | 0、0、0、0 |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0 |

**另外列出的紀錄差異**

- `LOG_FORMAT` 升版：78 場的 `format` 全部是 `trpg-battle-log/138` → `trpg-battle-log/139`，只有這個版本字串。
- 不是升版造成的：內嵌規則包只多 `equipment.caps.signature_active: 3`（missing → 3），所以 `ruleset_hash` 也不同。`setup`（含 `Loadout`，`chosen` 空不輸出）、事件、步驟、`final_state`（`limited_by` 空不輸出）逐位相同。

**新測試**

- `tests/content/test_loadout_chosen_e6b1.py`：預設空不輸出、往返、格式錯誤與重複被擋、舊勾選不算錯、`LOG_FORMAT` 從常數推。
- `tests/engine/test_signature_limits_e6b1.py`：改寫規則 2 條、3 條時只留 1 條（照欄位順序不照 id）；勾選的那條生效；舊勾選退回欄位順序；同 id 兩件不算衝突；`limited_by` 序列化往返、空時不輸出。
- `tests/engine/test_signature_cap_e6b1.py`：招牌 4 個標灰最後一個；3 個都生效；沒標招牌的不佔；勾選優先、勾 3 個就是那 3 個；戰鬥中標灰的新動作不在技能列、敵方單位照欄位順序；同 id 授予技能疊加、各佔名額；同 id 地形規則只算 1 個；和種族完全重複的不佔、部分重疊的照佔；蓋過的那條被標灰後重算；普攻變形拿弓或過不了閘門不佔；被改寫規則名額標灰的不佔；確定性。
- `tests/engine/test_signature_view_e6b1.py`：兩種灰字用字、標灰的不寫成重複、敵我看到一樣、沒有名額問題時沒有原因。
- `tests/engine/test_gear_g3b.py`：兩個「兩條改寫規則被擋下」的舊測試改成「通過穿戴檢查、只留 1 條」。

## 4. 待 PM 決定

PM 已裁定待決 1～7（2026-11-23）：1 由 E6-b2 換裝時寫 `chosen`；2～6 接受；7 查明後不改（第 2.5 節）。沒有新的待決。

已裁定的內容（留紀錄）：

1. 沒勾過時照欄位順序（引擎沒有穿戴先後）。
2. 只有標了 `signature` 的詞條佔名額。
3. 技能變形「全部招式被閘門擋下」會隨戰場條件變，不算整條沒效果，照佔名額。
4. 標灰原因沿用 `off_zh`；給前端畫框的 `signature` 欄位留 E6-b2。
5. `signature_active: 3` 放進 `equipment.yaml` 並開進工坊（規則包雜湊因此變）。
6. 邊界情況：被 3 個名額標灰的剛好是生效的改寫規則時，另一條改寫規則不補上；改寫規則名額調成 0 時灰字寫「和其他裝備的改寫規則衝突，沒有效果」。

## 5. 平衡疑慮

沒有。這段沒有試數值。
