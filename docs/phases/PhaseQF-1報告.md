# Phase QF-1 報告：兩件小修

> 規格：`docs/phases/PhaseQF-1計畫.md`。基準 `de10a8035`（開工時 `git merge main`）。分支 `worktree-agent-adb5ca72f767045b7`，沒有 push。
> 沒有試數值；沒有改 `docs/design/`、`config/`、`content/`（含 schema、`skill_primitives.yaml`）、`scripts/x10/`。

## 1. 做了什麼

| 項目 | commit | 內容 |
|---|---|---|
| 1 批次改 `ap_cost` 放行預支 | `1e7ce18c5` | `src/trpg/api/tuning/skills.py` `_scalar_edit`：目標是 `ap_cost`、技能的 `effects` 帶 `borrow_ap` 時，範圍改成 `_BORROW_AP_LIMITS = (0, 0)`（只放行 0）；改完跟原值相同時跳過，原因寫「預支技能的 AP 固定是 0，不能改」。不帶預支的照舊 `(1, 3)`。回歸測試在 `tests/api/tuning/test_skills_nw2a.py`：`test_group_ap_cost_keeps_borrow_skills_at_zero`（設定 2、+1、−1、×2 四種，搶拍都跳過，不會再夾成 1）與 `test_group_ap_cost_non_borrow_skills_still_floor_at_one`（火箭設定 0 → 夾成 1 → 跳過）。 |
| 2 形態 build 報錯 | `b00a91274` | `src/trpg/narrative/events.py`：命中骰描述 `_attack` 改用 `_skill_name`；`_skill_name` 找不到技能、而且 ID 是 `skill_form_breath_<形態>` 時，回傳該形態天生武器的名稱（龍是「吐息」）。回歸測試 `tests/engine/test_directed_charge.py::test_narrative_line_for_the_released_breath_attack`（改前確認會失敗）。 |

### 第 2 項的原因（程式錯，不是資料或 build 設定錯）

- 報錯不是在開場，是在龍形態吐息**蓄力釋放後的命中骰**。
- 吐息技能 `skill_form_breath_<形態>` 由 `content/form_breath.py` 臨時組出，**故意不登錄在規則包**（引擎的 `stack_gain._event_skill` 已經有特判）。
- 引擎結算正常，但 CLI 印戰鬥經過時，`narrative/events.py` 的 `_attack` 直接呼叫 `ruleset.skill_def(e.skill_id)`，拋出 `KeyError`。`cli/main.py` 的 `_with_library` 把它接住，印成「錯誤：skill_form_breath_dragon」、結束碼 1。
- 兩個 build 都有 `skill_form_dragon`，所以只有它們踩到。其他形態沒有蓄力武器。
- 不用改技能資料或規則；只改描述層。

## 2. 檢查（結束碼）

| 指令 | 第 1 項 | 第 2 項 |
|---|---|---|
| `ruff check` | 0（第一次 1：E501 兩行、`_scalar_edit` PLR0911 7 個 return；改成共用跳過原因後 0，沒加 noqa） | 0 |
| `ruff format --check` | 0 | 0 |
| `mypy` | 0 | 0 |
| `lint-imports` | 0（14 kept） | 0（narrative 匯入 `trpg.content.form_breath`，合規） |
| `trpg content check` | 0 | 0 |
| 相關測試 | `tests/api/tuning`：0（203 passed） | `tests/engine/test_directed_charge.py`：0（29）；`tests/narrative`：0（475）；`tests/cli`：0（148） |

重播：`trpg battle --map open_plain --seed 3 --ally-build build_form_mastery --log-json` ＋ `battle replay`：0、0（96 個動作、298 個事件）。
兩個 build 在 `open_plain` 種子 1、2、3 用 `trpg battle --ally-build` 都是 0（改前都是 1）。

## 3. 戰鬥不變比對

腳本在 scratchpad（未 commit）：改前＝`git archive de10a8035` 的 `src content config`，`PYTHONPATH` 指向舊 `src`（印出 `trpg.__file__` 確認路徑不同）；同 AP-2b 的組合：17 張地圖 × 種子 1、2 預設陣容 ＋ `open_plain` 種子 3 × 48 個 `--ally-build`；比整份 `--log-json`（去掉 `ruleset`、`ruleset_hash`、`format`）。

| 比對 | 結果 |
|---|---|
| 全部 82 場 | 80 場相同；不同的 2 場是 `build_form_mastery`、`build_form_tester_2`：改前結束碼 1（沒有紀錄），改後 0 |
| 那 2 場另外比：把 CLI 的逐步印出關掉（`_Printer.__call__` 改成什麼都不做），兩個 build × 種子 1、2、3 | 6 場相同，different=0 |

結論：引擎結果沒有變；那 2 場改前只是在印出時當掉，戰鬥本身不受影響。第 1 項只改數值工坊，不碰戰鬥。

## 4. 待 PM 決定（1 件）

1. **「只放行 0」的解讀**：我照字面做成「帶預支的技能，批次改 AP 時只能是 0」。因為 schema 規定預支技能必須 0 AP，所以批次改 AP 時搶拍一律跳過、附原因，不會再夾成 1 然後驗證失敗。如果原意是把下限放到 0、上限照舊 3，例如設定 2 會改成 2，那 schema 會擋，所以我沒這樣做。

## 5. 其他觀察（沒改）

- `narrative/events.py` 施放描述的變奏名稱（約 687 行）也直接查 `skill_def`。吐息沒有變奏，所以不會踩到，沒動。
- 數值工坊單欄位的 AP 提示（`content/tuning_fields.yaml` 的 `hint_min: 1`）沒改：規格只說批次改，而且 X10-1 正在動 `content/`。

## 開發 PM 裁定（2026-11-20）

合併：`Merge QF-1`（--no-ff）。第 2 項查到的原因是程式錯：組出來的吐息技能沒登錄在規則包，描述命中骰時查不到就拋錯。只改描述層就修好了，引擎結果不變，這樣做對。

待決 1 件：接受。帶預支的技能批次改 AP 時只能是 0，和規則一致。
