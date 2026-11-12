# Phase HID-1 報告：隱蔽中的敵人只藏資訊（玩法決定 #144）

> 依據：`docs/design/05-戰鬥.md` 5.1.2「隱蔽中的敵人只藏資訊」6 條（使用者：「B 只藏資訊」）。worktree `dev/hid1`（從 main `15ab0903` 開），沒有 push、沒有 rebase。

## 1. 完成表

| 規格條 | 做法 | 位置 |
|---|---|---|
| 1 位置、外觀、名稱照畫；HP、護盾、狀態「？」 | 伺服器：`UnitView.hp`、`shield` 改成 `int \| None`，新增 `hidden_info: Literal[True] \| None`；看不到時 `hp`／`shield` 為 `None`、`statuses`／`stacks` 為空、`hidden_info` 為 `True`。前端：Pixi HP 條黑框灰色整條＋「?」徽章（掛 HUD 層、地圖縮小時反向放大），不畫護盾條與狀態列；單位卡與滑過資訊卡（`UnitInfo`）寫「HP ？ / 最大」、護盾「？」、狀態一格「？」（共用 `PartTip`，說明卡寫原因）；行動順序列的 HP 條灰色整條、說明寫「HP ？」 | `src/trpg/api/hidden_info.py`、`src/trpg/engine/view.py`、`client/src/battle/hiddenInfo.ts`、`client/src/render/unitSprite.ts`、`client/src/ui/statusCard.ts`、`UnitInfo.tsx`、`TurnBar.tsx` |
| 2 揭露／隱蔽解除／上下左右相鄰時完整，條件消失回「？」 | `hidden_unit_ids(state, team)`：不是觀看者陣營、在場（未倒下、未撤離、召喚物未消失）、`is_concealed`（`concealed` 狀態、黑暗表面、草叢；被揭露 `prevents_concealment` 不算），而且沒有和觀看者陣營任一在場單位（含召喚物）曼哈頓距離 1。每次組回應都重算（純函式），所以條件消失就回「？」 | `hidden_info.py` |
| 3 規則不變 | 引擎、合法動作、命中劣勢都沒動；只在 API 組回應時遮 | — |
| 4 自己的傷害數字照常；紀錄不寫剩餘 HP、護盾、狀態 | 事件 JSON：`damage_dealt`／`healed`／`gear_hp_lost`／`damage_redirected` 的 `hp_before`、`hp_after`，`shield_gained.total`、`shield_absorbed.remaining`，`form_entered`／`form_left`／`unit_revived`／`boss_phase_changed` 的 `hp` 改成 `null`（`amount` 照給，傷害數字照畫）。紀錄文字：`describe_event(..., hidden)` 不寫「HP a → b」「剩餘 N」「共 N」。狀態類事件：`status_applied`、`stacks_changed`、`status_save_rolled` 只有來源是觀看者陣營時才給（＝自己動作的結果），`status_removed` 與到期的 `shield_ended` 不給（被打破的照給）。預覽：`min_events`／`max_events` 同樣遮，`certain`／`possible` 去掉看不到資訊的單位的「downed」「shield」 | `hidden_info.py`、`presenter.py`、`src/trpg/narrative/events.py` |
| 5 對稱；AI 不變 | `hidden_unit_ids` 以觀看者陣營判斷（測試含敵方視角）；AI 與 LLM 指揮官都不讀 `project_for`／presenter，沒有改 | — |
| 6 伺服器過濾、重播與存檔完整 | 只在 `trpg.api.presenter`（`traits_view`、`team_events_out`、`preview_response`）遮；引擎 `project_for` 一律完整、`hidden_info` 為 `None`；`/log` 匯出、存檔、重播、CLI（全知視角）不變 | — |

前端另外：所有「HP > 0 才算站著」的判斷改成 `hp` 為 `null` 也算站著（`standing()`；`battleSfx`、`impact`、`specials`、`world/battleHints.ts`）。

## 2. commit

- `5f70fa3c` feat(api): hide concealed enemies' HP, shield and statuses per viewer team (HID-1)
- `a2a64680` fix(api): make UnitView.hidden_info optional (true or null) in OpenAPI
- `45300c57` feat(client): show ? for concealed enemies' HP, shield and statuses (HID-1)
- 本報告 commit：HP 條「?」改成黑底圓徽章（選取時的紅框蓋住 HP 條也讀得到）、截圖、報告

## 3. 測試

- Python `tests/api/test_hidden_info.py`（9 項）：隱蔽未揭露時 HP／護盾／狀態未知、位置名稱照給；相鄰（主角、其他我方；斜角不算）完整；揭露後與隱蔽解除後完整；條件消失回未知、倒下的不遮；敵方視角對稱；自己的傷害數字照給、`hp_before`／`hp_after`／護盾剩餘為 `null`、文字不含 HP（全知描述照寫）；狀態事件只給自己來源的；存檔往返與引擎投影完整；預覽結果去掉 downed／shield。
- 前端 `client/src/battle/hiddenInfo.test.ts`（6 項）：小工具、畫法資料、Pixi HUD（「?」節點在 `HUD_LABELS`、`unitMarksOf`）、單位卡／滑過資訊卡、完整資訊時沒有「？」、行動順序列。
- `client/src/ui/hiddenUnitHud.test.ts` 的「伺服器的 UnitView 沒有『看不見』的欄位」改成鎖住新形狀：有 `hidden_info?: true | null`、`hp`／`shield` 可為 null，仍沒有「整個看不見」的欄位（選項 B 身體一直看得到）。`statusBadges.test.ts`、`summonBadges.test.ts` 的接線字串跟著改。

## 4. 驗收

| 項目 | 結果 |
|---|---|
| `ruff check`、`ruff format --check`、`mypy`（584 檔）、`lint-imports`（14 kept） | 過 |
| `pytest tests/api tests/engine tests/world tests/narrative tests/test_architecture.py -n 4` | 6482 passed、1 skipped（第一次和 CLI 快照同時跑、加 `-x` 時有 1 項失敗，之後兩次重跑全過，判斷為負載下的時間性測試；見「待 PM 決定」） |
| CLI 輸出快照（含 slow，25 項） | 過，沒有重產（CLI 是全知視角，`describe_event` 預設不遮） |
| 重播 swamp 種子 7 | 通過：88 個動作、313 個事件，最終狀態一致 |
| `client/openapi.json`、`schema.d.ts` | 重產，`test_openapi_snapshot` 過 |
| vitest 全量 | 273 檔、3281 項全過（全量時 `badgeCapsule.test.ts` 的效能測試曾在負載下失敗一次，單獨重跑過） |
| `tsc --noEmit`、`pnpm build` | 過 |
| 排版煙霧 1600×900、1040×624、800×600 | 三個都 11 PASS、1 FAIL；FAIL 是既有的「戰鬥：四角飾件沒有壓到內容」（主角卡左下 × 技能晶片），6F-22b 已記錄 main 上同樣 FAIL，與本段無關 |
| 6.5.1 實測（狀態「？」的說明卡） | 1600×900、800×600：Shift＋點釘住格子資訊卡 → 滑過「？」出現說明卡（在觸發元素上方、無空隙）→ 經橋接區滑進卡片 → 捲動（卡片沒超出，沒有捲軸）不關 → 點卡片釘住（`pinned`）→ 滑鼠離開仍在 → Esc 關閉。都過。800×600 時滑到右上角目標徽章（另一個浮動卡觸發元素）會換成那張卡，是共用元件「同時只開一張」的既有行為 |

## 5. 截圖（`docs/art/shots/hid1/`，5 張，jpg 80，最大 127 KB）

以排版煙霧檢查的種子開局（雲海吊橋），用 headless Chrome（CDP，`--mute-audio`）在 1600×900 拍。**伺服器的遮法由測試保證；截圖時在瀏覽器攔下戰鬥回應，把「盜賊2」移到 (2, 3)，照伺服器的格式改寫成 `hidden_info: true`、`hp`／`shield` 為 null、狀態空**（同一開局沒有天然的隱蔽敵人）。

- `docs/art/shots/hid1/hid1_hidden_1600.jpg`＋`docs/art/shots/hid1/hid1_hidden_1600_zoom.jpg`：隱蔽敵人離主角 2 格，身體半透明照畫，HP 條灰色＋「?」徽章，沒有護盾條與狀態列。
- `docs/art/shots/hid1/hid1_adjacent_1600.jpg`＋`docs/art/shots/hid1/hid1_adjacent_1600_zoom.jpg`：同一個敵人站到主角旁邊（相鄰）＝完整：HP 條、護盾條、狀態列（隱蔽、護盾、燃燒）。
- `docs/art/shots/hid1/hid1_hovercard_1600.jpg`：滑過資訊卡寫「HP ？ / 35」、護盾「？」、狀態一格「？」；位置、名稱、武器照寫。

## 6. 待 PM 決定

1. **只遮 HP、護盾、狀態（照字面）**：法力、耐力、AP、移動、速度、武器、裝備、最大 HP、Boss 階段（含下一階段的 HP 門檻 ‰）照給；層數 `stacks` 因為畫在狀態列一起遮。若要連法力、耐力一起遮請玩法 PM 決定。
2. **狐族「靈覺」（`sees_hidden`）**：規則上隱蔽對有靈覺的觀看者無效，但規格只列「揭露、解除、相鄰」，這段沒有把靈覺算成看得到（保守照字面）。
3. **相鄰的我方只算在場的人**：倒下、撤離、消失的召喚物不算；倒下的敵人也不遮（倒地已經看得到）。
4. **環境預告（`telegraph`）沒有遮**：隱蔽敵人身上的定時炸彈、蓄力倒數與預告的傷害仍會出現在預告裡（屬危險預警）；戰場上他的炸彈／蓄力徽章因狀態被遮而不畫。要不要連預告一起遮請決定。
5. **「何時算看不到」以每一步結束後的狀態判斷**：同一步中途相鄰、結束時離開的事件仍會遮。
6. **自己動作的狀態結果照給**：例如我方對隱蔽敵人施加燃燒的 `status_applied` 照給（「自己動作的結果」），敵方自己上的增益不給；被打破的護盾 `shield_ended` 照給、到期的不給。
7. **黑暗格的霧（`veil`）畫在 HUD 之上**（既有圖層），站在黑暗裡的隱蔽敵人「?」徽章會被霧蓋暗；選取「移動」時攻擊目標的紅框也會蓋住 HP 條下緣（所有敵人都一樣）。「?」改成黑底圓徽章已比較讀得到，最終畫法請美術 PM 看截圖決定。
8. 改到 `client/src/world/battleHints.ts` 一行（`alive()` 讓 HP 為 null 算站著，型別變了不改會編譯失敗）；RT-6b 同時在 `client/src/world/` 工作，合併時留意。
9. 測試時負載下各有一項時間性測試失敗一次（Python 那項未定位，單獨重跑全過；vitest `badgeCapsule` 效能測試），與本段無關但記錄。
