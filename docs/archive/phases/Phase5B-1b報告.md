# Phase 5B-1b 完成報告：follows、世界級線頭、新骨架 19～21

> 實作者：implementer agent（2026-11-03）。只改 `content/world/events/cloud_ridge.yaml`、`content/world/situations/cloud_ridge.yaml` 與測試；沒有動 `src/`、schema。資料來源：`docs/design/18-雲嶺內容.md` 18.4 末段兩次「補充」。

## 1. 改了什麼

1. **12 個骨架的 `follows`**：3、6、7、8、9、10、12、14、15、17、19、21，照補充的對照表（骨架 6 三條、14 三條、21 兩條）。
2. **世界級線頭**：`wraiths_from_rift`（霧魅從裂痕湧出）、`shards_to_ashen`（碎片被送往灰燼荒原）設 `scope: world`；其餘維持 `personal`。
3. **新骨架 19／20／21**（21 個骨架、19 種線頭）：
   - 19 `ayue_request`：獵戶小屋、白天、NPC `hunter_ayue`；解法 戰鬥／情境（感知，追蹤）；線頭 `ayue_father_relic`。
   - 20 `runaway_furnace`：丹爐洞；解法 情境（體質，耐力）／情境（智力，學識）；無線頭。
   - 21 `frost_chime_riddle`：鶴歸崖、NPC `frost_chime`；解法 情境（意志，異象）／情境（智力，學識）；線頭 `frost_chime_we`。
4. **新情境模板 5 個（共 28 個）**：`ayue_track_leopard`（感知／敏捷 DC 12）、`furnace_hold_breath`、`furnace_shut_down`（DC 13，體質／智力）、`chime_riddle_uncanny`、`chime_riddle_lore`（DC 13，意志／智力）。獎懲用預設（危險度 19、20 為 2，21 為 1，額度在預算內）。
5. **既有模板補屬性**：`ferry_repair`（骨架 9）加敏捷（方法加 `finesse`）；`acolyte_find_way`（骨架 2）、`hunter_awaken`（骨架 8）加體質（方法加 `endurance`）。骨架 10 `bear_slip_away`、13 `sword_array`、17 `patrol_track` 原本就有補充要的屬性（敏捷、敏捷、體質），沒有再動。
6. **骨架 15 `spring_hold_breath`**：加 `advantage_threads: [alchemist_owes_you]`（補充：「耐力」得到優勢，5B-2 報告建議的寫法）。

屬性覆蓋（28 個模板）：感知 12、智力 12、意志 10、體質 9、力量 8、敏捷 8（測試上下限 5～16）。

## 2. 測試

- 新增 `tests/world/test_events.py::test_cloud_ridge_follows_picks_following_skeleton`（4 組，用雲嶺真實資料）：持有 `scarface_grudge`／`temple_traitor`／`shards_under_den` 時在源晶裂痕一定選中骨架 14；持有 `wolves_driven_down` 時在雨中梯田選中骨架 3；各跑 8 個亂數計數；`follows_thread` 正確、候選仍有 ≥ 2 個（證明是「優先」而非唯一）。
- 更新計數：`test_world_events.py`（21 骨架、19 線頭、世界級線頭恰兩條）、`test_world_situations.py`（28 模板）。
- 因新資料而調整兩個既有測試：`test_no_candidates_no_event` 改用雲頂觀（獵戶小屋白天現在有骨架 19）；`test_follows_thread_preferred` 的合成骨架改接 `wolves_driven_down`（`peddler_owes_you` 現在被骨架 9、19 真正接上）。
- 結果見第 4 節。

## 3. 待決

- **骨架 9「用人情代替青竹節」**：補充寫「交涉時給青竹節改成可用人情代替」。資料層只有 `follows` 能表達「接得上」；「給青竹節」是 `parley` 解法，沒有結算模板，人情如何抵用屬於交涉流程（5B-3／5B-4），本段沒有做。
- **「斷崖幫寨的暗門」戰鬥先手**：補充「在斷崖幫寨的戰鬥我方先手」屬戰鬥接線，延續 5B-2 的待辦，本段沒有做（骨架 14 偷走的優勢已有）。
- **骨架 20／21 的屬性配對**：補充只寫「20 體質／智力、21 意志／智力」，沒有分到各個解法；採「每個解法第 1 屬性＝骨架解法的屬性，第 2 屬性從方法表補」：耐力 體質＋力量、學識 智力＋感知、異象 意志＋感知、學識 智力＋意志。要改只動 content。
- **骨架 20 沒有線頭**（照補充「—」）；失敗懲罰為受傷＋中毒，成功補給 2（丹砂以補給表示，沒有新獎勵種類）。
- **世界級線頭的實際行為**：`scope: world` 的結算（放進 `WorldState.threads`、上限 5）5B-2 已實作，本段只改資料；5A-6 若讓世界級線頭影響其他系統，要另外確認。

## 4. 檢查紀錄

- `uv run pytest -q tests/content/test_world_events.py tests/content/test_world_situations.py tests/world -n 8 --timeout=1800`：全數通過（含新增 4 個）。
- `uv run trpg content check`：「21 個事件骨架、19 種線頭」「28 個情境模板（21 個骨架）」。
- `tests/cli`、ruff、format、mypy、lint-imports：見交件回覆。
