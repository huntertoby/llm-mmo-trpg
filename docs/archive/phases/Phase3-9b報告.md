# Phase 3-9b 報告｜戰鬥紀錄改版

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| `3de806e` | 紀錄依行動分組、輪／回合分隔、陣營色與符號、擲骰細節收起、滑過高亮；`logGroups.ts`、`logGroups.test.ts` |
| （本報告 commit） | 截圖 `docs/phases/img/3-9b-*.png`、`docs/phases/Phase3-9b報告.md` |

只改前端，沒有動後端、事件 schema、`LOG_FORMAT`。沒有碰 `render/`、`animation.ts`、`playback.ts`。

### 設計重點

- **`battle/log.ts`**：`LogLine` 新增 `type`、`action`、`summary`、`tone`、`team`、`unitIds`、`tiles`（`text` 仍是完整文字）。
  - 行動開始事件（`action: true`）：`skill_used`、`unit_dashed`、`unit_charged`、沒有 `skill_id` 的 `attack_rolled`（普攻）、合併後的步行。
  - `summarize(type, text)`：擲骰類（`attack_rolled`、`status_save_rolled`、`check_rolled`、`maneuver_rolled`）精簡成「主詞 → 結果」；`initiative_rolled` 精簡成「先攻：誰 總值」；`damage_dealt`、`healed` 拿掉「［骰…］」「（天氣、格擋…）」。精簡版只在能拿掉細節時才有（`summary`），沒有則不顯示「詳」。
  - `team`：傷害、治療、狀態以「被作用的單位」為準，其他以行動者為準；`unitIds`／`tiles` 取自事件的 `*_id` 欄位與 `pos`、`from_pos`、`to_pos`、`tiles`。
  - `UnitNames` 新增 `team(id)`（`battle/units.ts`）。
- **`battle/logGroups.ts`（純函式 `groupLog`）**：`round` 改變插入「第 N 輪」；`turn_started`、`environment_started` 插入回合分隔（依行動單位陣營上色，去掉開頭的「—」）；行動開始事件開新組，其後的結果掛在組內，直到下一個行動、回合分隔或 `turn_ended`；沒有標題可掛的行各自成一組。因為是對整個 `lines` 重算，跨播放格（frame）的行動也會正確合在同一組；重新整理後還原的歷史（`logLines(h.steps…)`）走同一條路徑，自然也分組。
- **`ui/BattleLog.tsx`**：我方藍、敵方紅（行與回合分隔）；結果前的符號：傷害「−」紅、治療「＋」綠、護盾「◇」青、狀態「◆」黃、倒下「✕」灰、命中「●」、失手「○」。擲骰與修正細節預設收起，行尾「詳」展開該行完整文字，標題列右上「擲骰細節」開關全部展開。
- **滑過高亮**：`BattleLog` 新增 `onHover` prop，`BattleScreen` 只新增 `logHover` state 與一個包在原 `highlights` 外面的 `useMemo`：把該組牽涉單位目前所在格（依播放中的 `shown` 視圖）與事件指出的格子併進 `preview`（橘色）。原本的高亮邏輯（改名為 `baseHighlights`）一行未改，離開紀錄就清除。

## 2. 驗收條件逐條

| # | 結果 | 證據 |
|---|---|---|
| 1 | 通過 | `client/src/battle/logGroups.test.ts`：`summarize`（`attack_rolled`、`status_save_rolled`、`initiative_rolled`、`damage_dealt`、`healed`、`unit_downed`）、`logLines` 欄位（`skill_used`、`attack_rolled` 技能／普攻、`damage_dealt`、`unit_downed`、`unit_moved` 合併步行）、`groupLog`（`turn_started`、`turn_ended`、`environment_started`、`status_applied`、`surface_changed`、輪與回合分隔、陣營色、空輸入、歷史還原）。既有 `log.test.ts`、`historyLog.test.ts`、`playback.test.ts` 不改即過。 |
| 2 | 通過（滑過高亮） | 瀏覽器實測：滑過「盜賊頭目 施放橫掃劈砍」那組，頭目與被打的我方格子變橘；滑過展開細節按鈕所在的撞擊那組，涉及的兩個單位與落點格變橘；移開後消失。播放速度屬 3-9a。 |
| 3 | 通過 | 截圖：`docs/phases/img/3-9b-hover.png`（分組、陣營色、符號、滑過高亮）、`3-9b-expanded-detail.png`（單行展開「詳」並滑過）、`3-9b-all-details.png`（全部展開）。 |
| 4 | 通過 | `corepack pnpm -C client build` 成功；`uv run python scripts/check.py` 全部通過（ruff、format、mypy、lint-imports、pytest、client typecheck、vitest）。 |

## 3. 複雜度 noqa

沒有新增、沒有移除（前後相同）。

## 4. 修改既有測試期望值

無。

## 5. 待 PM 決定

1. 普攻每一次命中判定各自成一組（弓手連續三次攻擊是三組），沒有合併成「攻擊 ×3」。
2. 戰鬥開始、先攻、行動順序等開場行掛在「第 1 輪」分隔下、各自一組（先攻擲骰預設收成「先攻：誰 總值」）。
3. 「結束回合」「回合開始時的狀態傷害」沒有行動標題，各自成一行；沒做整組收起／展開（只做擲骰細節的收起）。
4. 步行合併行是一個行動標題（沒有子行）；被推、傳送等位移行掛在觸發它的行動底下。
5. 重新整理後還原的歷史只認得開局時就在場的單位；之後才召喚的單位那幾行沒有陣營色與高亮（文字完整）。
6. 滑過高亮借用橘色「預覽範圍」，沒有新增專用的色彩層；與 3-9a 合併時若它也改高亮層，需確認 `preview` 疊加仍成立。
7. 沒有在瀏覽器實測重新整理還原（分組走同一個函式，以 vitest 覆蓋）。

## 6. 代表性輸出節錄

紀錄結構（一組）：

```
第 2 輪
盜賊頭目 的回合（AP 4・移動 5・法力 14/14）
  盜賊頭目 施放「橫掃劈砍」（AP 2，法力 4，冷卻 2 回合）→ 影響 4 格
    ○ 盜賊頭目 以「橫掃劈砍」攻擊 標準隊友 → 失手      [詳]
    − 倒木 受到 20 點物理傷害，HP 20 → 0
```
