# Phase 5F-1b 完成報告：5F-1 收尾（門檻下限、霧影分身、每天第一場懸賞、「你不在的時候」）

範圍：`docs/phases/Phase5計畫.md` 第 1 節 5F-1b 列；背景 `Phase5F-1報告.md` 待 PM 決定 1、3、4、7。依玩法 PM 2026-11-03 代決（09 9.6.10 #103 已寫入、18.7.4 已寫入）。

## 交付

| # | 項目 | 位置 |
|---|---|---|
| 1 | 世界事件門檻：前一天沒有上線紀錄（含第 1 天、舊存檔）用原門檻；有紀錄照比例調，最少保留原門檻 `min_target_permille`（250‰＝1/4，無條件進位，30 → 8） | `content/world/season.yaml`、`content/world_season.py`（`WorldEventDef.min_target`／`target_for`）、`world/season_board.py` |
| 2 | 霧中劍客「霧影分身」：不改引擎。新單位 `sect_mist_swordsman`（持劍弟子的數值與招式＋召喚技能）、新召喚技能 `skill_summon_mist_shade`（技能層級條件 `first_round`＝只在第 1 輪能用、射程 2、持續 3 輪）、新召喚物 `summon_mist_shade`（範本 HP 6、單手劍＋先發制人）；懸賞精英改用新單位（詞綴仍是霧隱的）；外觀表加一列（沿用殘影畫法） | `content/units/`、`content/units/summons/`、`content/skills/`、`content/summon_looks.yaml`、`content/world/season.yaml` |
| 3 | 懸賞遭遇：每個角色每天在該地點的**第一場**遭遇是懸賞陣容（已被別人搶下也一樣），開打時記進 `CharacterState.bounty_days`（懸賞 → 刷新日），之後照一般遭遇；6 點換日重算。先打倒的人拿大獎（任務幣 3＋經驗補到懸賞份數，照舊），其他人打倒拿小獎 `consolation_coins`（任務幣 1，`bounty_missed` 加 `coins`，來源 `bounty_consolation:<id>`）；公告板的「已被 X 搶下」補小獎提示 | `world/season_board.py`、`world/solutions.py`、`world/state.py`、`world/season_events.py`、`api/season_view.py` |
| 4 | 「你不在的時候」：`GET /api/world/characters/{id}/absence`（`since`、`as_of`、`items`：世界事件成敗、懸賞被誰搶下、新開放的區域；隱藏地點用提示語；自己搶的不列；換日後的世界、只讀）；新世界動作 `news_seen`（`until`＝`as_of`，寫 `CharacterState.news_seen_at`，只往後、不超過現在）；新角色建立時 `news_seen_at`＝建立當下；`WorldEventState.resolved_at`（成敗的時刻）；前端進入角色時讀一次，有消息就用 `DialogFrame` 跳 `AbsenceDialog`，按「知道了」送 `news_seen` | `api/absence_view.py`、`api/routes/world.py`、`world/actions.py`、`world/step.py`、`client/src/world/AbsenceDialog.tsx`、`absence.ts`、`screens/WorldScreen.tsx` |
| 5 | 季末政策表：`bounty_days`、`news_seen_at` 標數值類 | `server/season_policy.py` |
| 6 | 修正：往灰燼荒原的渡口 `unlock_flag` 由 `mist_tide_success`（沒有任何事件會設）改成世界事件寫的 `ashen_waste_open`（19.9：成功或失敗都開放） | `content/world/maps/cloud_ridge.yaml` |

存檔：新欄位都有預設值，`trpg-world/1`、`trpg-char/1`、`trpg-wlog/1` 不升版；`LOG_FORMAT` 不變（引擎沒動）。

## 檢查

- `ruff check`、`ruff format --check`、`mypy`（1191 檔）、`lint-imports`（13 契約）通過。
- `tests/world tests/api tests/content tests/server tests/test_architecture.py`（`-n 8`）：3206 通過（合併 main 後）。
- slow：`tests/content/test_con_hp.py`、`tests/engine/test_source.py`、`tests/narrative/test_skill_icon.py` 通過（`test_con_hp` 加兩個範本；技能圖示快照重產）。
- vitest 139 檔 1279 通過；`npm run build` 通過；OpenAPI 與 `schema.d.ts` 重產。
- swamp 種子 7 重播：88 個動作、313 個事件，最終狀態一致。
- 瀏覽器實測（8200 埠，暫存存檔、開賽日調到 5 天前）：進入角色跳出「你不在的時候」（霧潮入侵失敗、渡口開放），按「知道了」後重新整理不再跳。
- 新測試：`tests/world/test_mist_shade.py`（2）、`tests/api/test_world_absence.py`（6）、`tests/world/test_season_board.py`（+3）、`client/src/world/absence.test.ts`（3）；受影響的內容計數測試照慣例更新（召喚物、外觀表 20、技能 378、雲嶺新敵人 20、懸賞精英算進「有出場」）。

## 代決（最保守）

- 門檻下限四捨五入方式：無條件進位（30 × 1/4 ＝ 7.5 → 8，照 PM 例子）；上線人數多於 `base_players` 時照舊放大（下限只管下面）。
- 霧影「開場召喚」：效用 AI 在第 1 輪決定要不要召（技能只在第 1 輪合法，所以每場最多一隻）；3 個種子實測至少 2 場第 1 輪就召出，不保證每場都召（第 1 輪就能直接砍到人時 AI 可能先砍）。要保證就得改引擎（開場動作），本段不做。霧影 HP 約為本體的 1/6（範本 6，召喚物近戰係數 ×2.2 後約 13）。
- 「第一場」以**開打**（`battle_started` 帶懸賞）為準：遇到後撤退不算用掉；打輸也算用掉。
- 小獎：任務幣 1，不補經驗（content `consolation_coins`）。
- 「看過」記在角色狀態（`news_seen` 世界動作，進日誌、可重播、換裝置也不再跳），不記在帳號 session；送 `news_seen` 也算當天上線（記進上線紀錄）。
- 舊存檔角色（`news_seen_at` 為空）從開賽算起跳一次；新角色從建立當下算起。
- 「新開放的區域」＝世界事件成敗效果的旗標打開了哪些地點的 `unlock_flag`（目前只有渡口）。

## 待 PM 決定

1. 小獎的數值（任務幣 1、不補經驗）與「打輸也算用掉今天第一場」。
2. 霧影要不要保證每場第 1 輪召出（需要引擎的開場動作，屬引擎變更）。
3. 渡口旗標的修正（`mist_tide_success` → `ashen_waste_open`）：Phase5 計畫 5A-2 表格寫的是 `mist_tide_success`，19.9 失敗也開放，因此改成事件實際設的旗標；如要分成功／失敗兩種開放方式請告知。
4. 霧影外觀沿用殘影畫法（`summon_looks.yaml`），請美術 PM 確認。
