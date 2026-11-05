# Phase 6T-1a 報告：交易共同前置＋郵寄（伺服器端）＋#135 主手掉落比例

實作者，2026-11-05。規格：開發 PM 派工 prompt（6T-1a）；規則真相來源 `docs/design/08-裝備.md` 8.13、8.15、8.16，
玩法 PM 交接 3.5 的郵寄代決，共用筆記「玩法PM-郵差內容文字.md」。只做伺服器、引擎、內容與 API；沒碰 `client/`
（只重產 `client/openapi.json`、`client/src/api/schema.d.ts`）。

## 1. 每項做了什麼

### 1.1 交易共同前置（`src/trpg/world/trade.py`、`content/world/trade.yaml`）

- **來歷與綁定**：角色多 `gear_origin`（物品 ID → `GearOrigin`：原主 ID／名字、來源 `drop|craft|trade|other|legacy`、
  來源句、時間、`worn`、`bound`）。`world_step` 每個動作之後呼叫 `stamp_gear`：
  - 新拿到的（背包、穿戴中、等著決定的戰利品）補紀錄；來源句依動作：戰鬥／戰後結算＝「〈地點〉的戰利品」、
    打造＝「〈地點〉打造」、其他＝「〈地點〉取得」。
  - 穿戴中的標 `worn`（**穿上就綁定**，換下來也還是綁定）。
  - **取得就綁定**：獨特（隱藏配方 `GearCraftedEvent.hidden`，或掛了 `item_gen.unique_affixes` 的詞條）→ `unique`；
    首殺物品（這一步有精英首殺 `InsightGainedEvent(source="elite:…")` 時掉進背包的裝備）→ `first_kill`。
  - 不在身上的紀錄刪掉；沒有變化時回傳同一物件（不影響 `world_step` 的快速路徑）。
- 卡片資料（`api/gear_trade.py`）：「最初得自：〈原主〉（〈來源〉）」、「目前持有：〈角色名〉」、綁定標籤
  （穿過／獨特／首殺）、能不能交易。
- **能交易**：背包裡 `trade.tradable_kinds`（材料、消耗品）、金幣、沒穿過也沒綁定的裝備。染料、補給、任務幣、
  靈感點、經驗、好感度、技能不在附件範圍內，寄不了。
- **門檻**（`send_quote`）：寄件人、收件人都要 3 級；收到的裝備物品等級 ≤ 收件人等級 +2；同帳號不能互寄
  （也不能寄給自己）；收件人背包放得下、信箱沒滿；附件最多 3 格、留言 40 字、金幣夠。全部通過才寫。
- **兩角色同一筆日誌**：`WorldLogEntry` 多 `counterpart`、`counterpart_actor`；`world_step(..., other=, other_actor=)`
  回傳 `StepResult.other`；`replay` 兩個角色一起更新；`WorldStore._apply` 用 `counterpart_of` 找另一個角色、兩邊一起寫回。
  純函式：不合法拋 `WorldActionError`、狀態不變＝兩邊一起成功或一起不變。
- **交易帳**：`WorldState.trades`（每封信一筆 `TradeRecord`：雙方角色與帳號、物品 ID、裝備 ID、金幣、稅、估值、
  狀態 sent/claimed/refused/reclaimed）。估值＝材料消耗品照買價、裝備照回收價、金幣照面額（稅前）。
- **稽核報表**（`src/trpg/world/trade_audit.py`）：短時間大量（同帳號 1 小時 ≥5 封）、大額（一封 ≥500）、
  估值懸殊（單向累計 ≥800 且反方向 <20%）。只出報表，不擋交易。門檻在 `trade.yaml` 的 `audit`。
- 交易不重新命名、不呼叫 LLM（名稱與描述本來就在 `ItemDef` 上，原封不動；`gear_mods`、`gear_origin` 跟著物品走）。

### 1.2 郵寄（伺服器）

- 三位郵差放在 `content/world/trade.yaml`（`mail.postmen`）：白鷺（主城 `capital`）、阿信（霧渡鎮 `mist_ferry`）、
  灰鴿（餘燼集 `ember_market`），各有人設卡（`NpcCardDef`，含頭像外觀：制服同一套、照區域換色＋皮帽）與七種情境台詞
  （打開、有信、寄件成功、等級不到、寄給自己帳號、對方等級太低、退件）。載入時檢查郵差站在城鎮。
- 動作（`trade_actions.py`）：`mail_send`（兩角色）、`mail_claim`（自己）、`mail_refuse`（兩角色）、`mail_reclaim`（兩角色）。
  全部要站在郵差的地點、沒有遭遇。
- 寄：附件從寄件人拿掉、信（`MailLetter`）放進收件人的 `mailbox`；金幣稅 10% **無條件進位**，信上記實收與稅。
- 領：收件人進城在郵差處領；背包放不下 → 明確錯誤「背包放不下（還差 N 格），先整理背包再來領」。
  撞到身上已有的裝備 ID 時加序號（改動紀錄、來歷一起改名）。
- 退件與過期：`expires_at = 寄出 + 3 天`（現實天數，用日誌的 `now`）。過期後收件人看不到也領不了，
  算寄件人的退件，寄件人在郵差處 `mail_reclaim` 取回（直接進背包）。收件人主動「退回」→ 信回到寄件人信箱
  （`returned: refused`），寄件人再領。稅都不退。
- 信箱上限 20（只算能領的、沒過期的）；滿了寄件人看到「對方信箱滿了」。
- 季末：角色整個清掉（季末重置政策表 `mailbox`、`gear_origin`、`trades`、`weapon_mix` 都標數值類）；季末前 3 天
  （`season_warning_days`）寄件時 `MailSentEvent.season_warning`、API 的 `season_warning_zh`。
- 時間判定只用日誌時間（守則 1）。

### 1.3 #135 主手掉落比例（`src/trpg/world/weapon_mix.py`、`content/world/loot.yaml` 的 `gear.main_hand`）

- 上線紀錄 `DailyActivity` 多 `characters`（角色 ID → 武器大類），每個動作之後記。
- 換日（`roll_season`，6 點）用前一天的上線紀錄算 `WorldState.weapon_mix`（大類 → 人數），存進世界狀態，重播同結果。
- 掉主手時：野外一般 500‰ 同大類、精英 750‰；其餘依另外兩類人數比例分，兩類合計 <3 人（`min_sample`）平均分。
  懸賞（`encounter.bounty`）、區域 Boss（Boss 地點或陣容有 `loot.yaml` 的 `bosses`）一律同大類。打造、任務本來就同大類；
  roguelite（`trpg.roguelite.gear`）沒動。大類亂數用裝備亂數的 `fork("main_hand")`，不推進原串流（其他掉落不變）。
- 卡片：別大類主手 `cross_class_zh`＝「別大類：可交易・可分解・可賣」、`cross_class_lost_zh`＝「換上後不能用：〈招名〉」
  （目前裝的招裡 `weapon_req` 是原大類的）；換裝的 `equip_problem_zh` 寫「主手只能換成同一大類的武器」。
- 修掉的連帶問題：背包裡有別大類主手時，`gear_candidate`（roguelite 卡片比較）會丟 `ChoiceError` 讓整個世界畫面 422；
  改成接住、把原因放進 `notes_zh`。

## 2. API 清單（`src/trpg/api/routes/mail.py`）

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/api/world/characters/{id}/mail` | 郵寄面板 `MailView` |
| GET | `/api/world/characters/{id}/mail/recipients` | 寄給誰（別帳號的角色）`MailRecipientView[]` |
| POST | `/api/world/characters/{id}/mail/quote` | 寄件前檢查（body＝`MailSendAction`）`MailQuoteView`，不寫日誌 |
| POST | `/api/world/characters/{id}/mail/send` | 寄 → `MailActionResponse` |
| POST | `/api/world/characters/{id}/mail/{letter}/claim` | 領（收件匣或退件）|
| POST | `/api/world/characters/{id}/mail/{letter}/refuse` | 退回寄件人 |
| POST | `/api/world/characters/{id}/mail/{letter}/reclaim` | 取回過期的信 |
| GET | `/api/world/trades/audit` | 稽核報表（管理者，`require_trade_admin`）`TradeAuditView` |

另外：`WorldView.mail`（`MailBadgeView`，郵差頭上「✉」）；`BagItemView` 多 `tradable`、`bound_zh`、`origin_zh`、
`holder_zh`、`cross_class_zh`、`cross_class_lost_zh`。錯誤碼沿用：不合法 422、角色不存在 404、戰鬥中 409。

## 3. 版號

| 項目 | 舊 → 新 | 舊檔 |
|---|---|---|
| 世界日誌 | `trpg-wlog/8` → `/9`（`counterpart`、`counterpart_actor`，空時不寫） | `/7`、`/8` 照讀 |
| 角色 | `trpg-char/8` → `/9`（`gear_origin`、`mailbox`） | `/1`～`/8` 照讀；舊存檔身上的裝備記成 `bound: legacy`（當作穿過） |
| 世界 | `trpg-world/3` → `/4`（`trades`、`weapon_mix`、`DailyActivity.characters`） | `/1`～`/3` 照讀 |
| `WORLD_RULES_VERSION` | 17 → 18 | 舊日誌標成規則已變、不能重播（既有機制） |

docstring：`world/save.py`（模組說明與 18 的說明）、`world/state.py`、`world/replay.py`、`world/step.py`、`api/world.py`、
`world/__init__.py`。季末政策表 `server/season_policy.py` 補 4 個欄位；`tests/test_architecture.py` 通過。

## 4. 快照變動

- `uv run python -m tests.skillgen.test_refactor_3wr2`：重產後內容**沒有變**（git 只看到 Windows 換行差異，已還原）。
- `UPDATE_CLI_SNAPSHOTS=1 uv run pytest -m "slow or not slow" tests/cli/test_output_snapshots.py`：25 passed，快照檔**沒有變**
  （CLI 快照不含大世界）。`test_run_cli` 不用重篩種子。
- `client/openapi.json`、`client/src/api/schema.d.ts` 重產（只多了郵寄的格式與 `WorldView.mail`、`BagItemView` 的交易欄位；
  `schema.d.ts` 只有新增、沒有刪除）。`schema.d.ts` 用主資料夾 `client/node_modules` 的 openapi-typescript 7.13.0 產生
  （worktree 沒有 node_modules）。
- 測試裡寫死版號的地方改成新版號；`test_field_ctx_replay` 的凍結雜湊照舊（新欄位加進 `DROPPED`），`SEASON_BOOKKEEPING`
  多 `weapon_mix`。

## 5. 各結束碼（交件前，最後一個 commit 之前）

| 指令 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy src` | 0（540 檔） |
| `lint-imports` | 0（13 kept） |
| `trpg content check` | 0（`world/trade.yaml：交易：3 級起、郵差 3 位（白鷺、阿信、灰鴿）`） |
| `trpg battle --map swamp --seed 7 --log-json …` ＋ `trpg battle replay …` | 0、0（88 個動作、313 個事件一致） |
| `pytest -n 8 tests/world tests/roguelite tests/server tests/test_architecture.py` | 0（1380 passed） |
| `pytest -n 8 tests/api` | 0（774 passed、1 skipped） |
| `pytest -n 8 tests/content tests/test_architecture.py tests/api/test_world_mail_api.py` | 0（2717 passed） |
| `python -m tests.skillgen.test_refactor_3wr2` | 0 |
| CLI 快照（含 slow，UPDATE） | 0（25 passed） |

新測試：`tests/world/test_trade.py`（17）、`tests/world/test_weapon_mix.py`（6）、`tests/api/test_world_mail_api.py`（5）。
沒跑完整 `scripts/check.py`（照守則 11 交給 PM）。

## 6. 給 6T-1b 前端的資料介面

- **✉ 泡泡**：`WorldView.mail`：`postman`（NPC ID）、`region`、`location`、`here`（站在郵差那裡）、`unread`、`returned`、
  `bubble`（有信時「✉」，否則 `null`）。所在區域沒有郵差為 `null`。
- **面板** `GET …/mail`：`postman`（名字、種族、所在城鎮、`portrait` 同 NPC 頭像格式）、`line_zh`（郵差這次說的話）、
  `here`／`here_problem_zh`、三個分頁 `inbox`／`returned`／`outgoing`（`LetterView`：寄件人、寄自 `from_zh`、`days_left`、
  `note`、`items`、`gear`（卡片含「最初得自」）、`gold`（已扣稅）、`status_zh`、`action`＝`claim|reclaim|null`、`can_act`、
  `problem_zh`（背包滿等）、`can_refuse`）、`sendable`（背包縮圖列；`tradable` 假的灰掉，`bound_zh` 是「穿過／獨特／首殺」）、
  上限 `mailbox_count/mailbox_max/max_attachments/note_max/tax_permille/min_level/level_ok/return_days`、
  `season_warning_zh`、`footer_zh`。
- **寄出前檢查** `POST …/mail/quote`：`ok`、`tax_zh`（「跑腿費 10%：−N　對方實收 M」）、`problems[{code,text_zh}]`、
  `line_zh`（等級不到／同帳號／對方拿不動時郵差的話）。`ok` 才亮「寄出」。code：`not_here low_level recipient_low_level
  self same_account no_recipient empty too_many note count not_tradable not_enough no_gear duplicate bound gold gold_small
  too_strong mailbox_full bag_full`。
- 動作回應 `MailActionResponse`：`mail`（新的面板）、`events`（中文句子）、`line_zh`（寄件成功、退件的台詞）。
  金幣與背包請重抓 `GET …/characters/{id}`（回應不含整份世界畫面）。
- 朋友名單：目前沒有「朋友」系統，`recipients` 列出所有別帳號的角色（名字、等級、所在地、`can_receive`）。

## 7. 待 PM 決定

1. **收件人也要 3 級**：8.16 寫「角色 3 級起能交易」，我保守解讀成寄件人、收件人都要（收件人不到時郵差說「對方等級太低」那句）。
2. **首殺物品**：沒有現成的「首殺物品」定義，採「這一場有精英首殺（個人第一次打倒某種精英）時掉的裝備」取得就綁定；
   全服首殺不在引擎內，沒算。
3. **舊存檔的裝備一律綁定**（不知道穿過沒有，記 `legacy`，卡片標「穿過」）。測試季重置後就沒有舊裝備。
4. **金幣稅捨入**：無條件進位（寄 1～9 金幣也收 1），實收要 ≥1。
5. **別大類主手仍然不能換上**（照現有換裝規則「主手只換同大類」）；卡片的「換上後不能用：〈招名〉」只當資訊。
   如果 #135 的本意是可以換上（然後那些招不能用），要改換裝規則，需要使用者決定。
6. **過期的信**留在收件人信箱（收件人看不到），由寄件人取回才進背包，不另寫系統日誌；寄件人背包滿時要先整理。
   被拒收的信則直接回寄件人信箱（不受 20 封上限）。
7. **所有郵寄動作都要站在郵差的地點**（城鎮地點就算，沒檢查實地地圖上的格子距離，同商店）；郵差的地圖站位、郵筒物件、
   `post` 設施種類留給 6T-1b。
8. **稽核門檻**是我的初值（1 小時 5 封、一封 500、單向 800 且反向 <20%），只出報表。
9. **在線角色**＝前一個刷新日有世界動作的角色；比例存人數，另兩類合計 <3 人平均分（`min_sample: 3`）。
10. 精英的 25% 別大類，兩類之間也照同一份在線比例分（規格只寫 75/25）。

## 8. 複雜度 noqa

沒有新增 C901／PLR0911／PLR0912／PLR0915。新增 `PLR0917`（位置參數 6 個）三處：`trade._mail_send`、`_mail_refuse`、
`_mail_reclaim`——和 `PairHandler` 分派表同簽名；另 `step._pair`（兩角色兩帳號）。`api/app.py` 的 `create_app` 因多掛一個
router 超過 50 行，拆出 `_include_routers`。
