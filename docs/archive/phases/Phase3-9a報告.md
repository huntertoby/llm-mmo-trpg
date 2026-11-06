# Phase 3-9a 報告｜地圖上的戰鬥回饋

分支：`worktree-agent-a7a9e5860c62e055e`（從 main `448a988` 開出）。只改前端，後端與事件 schema 都沒動。

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| `a4ac285` | `battle/feedback.ts`（事件 → 回饋項目的純函式）、`animation.ts` 位移表現與倍率、`playback.ts` 回饋 op ＋ 速度倍率，附 vitest |
| `123c47f` | `BattleRenderer` 新增效果圖層（浮動數字、字樣、連線、狀態彈出）與淡出淡入位移；`BattleScreen` 接上 `feedback` op |
| 最後一個 tweak commit | 連線加粗並停留較久、同格多個文字上下錯開（22 px）；加入 4 張截圖 |
| 本報告 commit | `docs/phases/Phase3-9a報告.md` |

設計重點：

- `feedbackFor(events, view)`：一步的事件 ＋ 該步的 `view`（取單位所在格）→ `FeedbackItem[]`（`float`、`line`、`status` 三種）。畫布只畫。事件型別 → 字樣的對照表 `EVENT_WORDS` 放在 `feedback.ts` 一處。
- 浮動數字：傷害紅「−N」（暴擊放大並彈一下）、治療綠「＋N」、護盾「＋N盾」「吸收 N」淺藍；另含轉移傷害、場景物件受傷。
- 字樣：失手、背刺！、伏擊！、格擋（`reaction_triggered` 的 `block`）、撞擊！、墜落、致命地形、抵抗（`status_resisted`、`push_resisted`、失敗的 `maneuver_rolled`）、擊倒、復活、死裡逃生、無法行動、攔截。
- 行動連線：`attack_rolled` 攻擊者 → 目標；`skill_used` 範圍技能 → 範圍中心格（各格平均後取最近的一格），終點與自己同格不畫；同一步重複的連線只畫一條。
- 狀態：`status_applied` 在單位上閃光環並浮出「＋狀態名」。
- 位移：`MoveAnim` 新增 `style`。推（`forced`）、拉、衝鋒（`dash`）、跳躍（`leap`）、步行用滑動；傳送（`teleport`、`teleported`）、交換（`swap`）、瞬步（`shadowstep`）用原地淡出、新格淡入。
- 播放速度：`SPEED_SCALE`（正常 1、快 0.5、略過 0）。移動動畫時間與回饋時間（`FEEDBACK_MS` 1000）都乘上倍率；略過時 `feedback` 為空，`movePlan` 倍率 0，沿用單一格直接到結果。回饋是不阻塞的（畫在獨立圖層、場景重畫不會清掉），所以不會拉長播放；播放鎖與 `skipNow` 照舊。

## 2. 驗收條件逐條

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | 事件 → 回饋項目的純函式有 vitest，列出覆蓋事件 | 通過 | `client/src/battle/feedback.test.ts`（11 項）。覆蓋事件：`damage_dealt`（含暴擊、0 傷害）、`damage_redirected`、`healed`、`shield_gained`、`shield_absorbed`、`object_damaged`、`attack_rolled`（失手、背刺、伏擊）、`reaction_triggered`（block 與其他）、`collided`、`unit_fell`、`entered_deadly_terrain`、`status_resisted`、`push_resisted`、`maneuver_rolled`（失敗與成功）、`unit_downed`、`unit_revived`、`status_applied`、`skill_used`（範圍連線）、無回饋事件與找不到單位。另 `log.test.ts` 新增位移樣式與倍率、`playback.test.ts` 新增回饋與速度。 |
| 2 | 播放速度三種都正確 | 通過 | vitest：`playback.test.ts`「gives feedback…full time normally, half when fast, none when skipping」「shortens move animations by speed」。瀏覽器同種子（1369752957）開場播放到可操作的總時間：正常 6.1 s、快 4.0 s、略過 0.04 s（含伺服器回應與固定的「戰鬥開始」橫幅時間）。 |
| 3 | 瀏覽器實測、附截圖 | 通過 | 見第 6 節截圖 |
| 4 | `pnpm build`、`check.py` 全過 | 通過 | `corepack pnpm -C client build` exit 0；`uv run python scripts/check.py` 全部通過（vitest 293）。 |

規格 12.1 逐項：浮動數字、字樣、連線、狀態、位移（滑動／淡出淡入）、三種速度、動畫期間不能操作（沿用播放鎖）皆已做。

## 3. 複雜度 noqa

沒有新增或移除。`textFor` 的事件分派用 `switch` ＋ 查表，未超過 C901 15。

## 4. 修改既有測試期望值

`client/src/battle/log.test.ts` 的 `movePlan` 兩個測試：

- 傳送原本期望 `durationMs` 為 0（直接出現），現在傳送改成淡出淡入、時間 260 ms，所以改成檢查 `style` 為 `fade` 且時間大於 0。
- 交換原本只檢查時間大於 0，現在檢查 `style`（衝鋒、跳躍為 `slide`，交換為 `fade`）。

另新增「倍率」測試。

## 5. 待 PM 決定

1. 交換位置改成淡出淡入（依規格），兩個單位依序淡出淡入、不是同時；原本是同時滑動。要不要改回滑動？
2. 回饋不阻塞播放（每步停頓照舊，浮動文字約 1 秒），快速連續的行動文字會疊在一起；若覺得太亂，可改成每步等回饋結束，代價是整體變慢。
3. 同一格同一步有多個文字時只上下錯開，沒有合併（例如「－5」「－3」不加總）；位於地圖最上排的單位，文字會被畫布上緣裁掉一部分。
4. 暴擊只放大「−N」數字，沒有另加「暴擊！」字樣。
5. 沒做陣營區分的數字顏色（我方受傷與敵方受傷同色紅）。
6. 儲存讀檔或重新整理後不會補播回饋（只看最後狀態）。
7. 行動連線只畫攻擊與技能（`attack_rolled`、`skill_used`）；投擲、推倒等場景互動沒有連線，目前靠位移與數字表現。
8. 狀態只在「新增」時彈出，續期、轉換（`status_converted`）、解除沒有回饋。
9. 瀏覽器內建窗格與另一位實作者共用，實測時分頁與視窗大小曾被切換；最後調整的文字間距（22 px）只有單元測試涵蓋，未再拍截圖。

## 6. 代表性輸出節錄

截圖（內建瀏覽器擷取，800×514 縮圖）在 `docs/phases/img/`：

- `3-9a-normal-line-miss-status.png`：正常速度。弓手攻擊的黃色連線、「失手」、「＋防禦」狀態彈出。
- `3-9a-normal-stacked-numbers.png`：正常速度。同一格多個文字（防禦、擊倒、致命地形、格擋、傷害數字）重疊；這張是調整間距之前的版本，用來決定把錯開距離從 14 px 改成 22 px。
- `3-9a-fast-status-popup.png`：快速。同樣的回饋，時間縮短一半。
- `3-9a-skip-no-animation.png`：略過。整輪敵方行動直接到結果，地圖上沒有任何動畫或文字，紀錄完整。
