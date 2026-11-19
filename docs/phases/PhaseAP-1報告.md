# 階段 AP-1 報告：#168 AP 改版（引擎＋AP 列）

> 2026-11-19，實作者。依據：`docs/phases/PhaseAP-1計畫.md`、05 5.2「⚠ AP 改版」與 5.2.1、`docs/phases/AP探討.md`、`docs/art/AP-1-AP列畫法.md`。
> 分支 `worktree-agent-a801430320efaf81e`（開工先 `git merge main`，快轉到 `1ed3c79f8`）。不 push。
> 第 2 項「預支」照派工不做；第 4 項「耗費結構不動」沒有程式要改，所以沒有 commit。數值都是初值、都在工坊白名單；沒有試數值、沒有跑平衡量測（不變比對除外）。沒有改 `docs/design/`、`config/`。

## 1. 做了什麼

| 項目 | commit | 內容 |
|---|---|---|
| 1 每回合 AP | `c2ac0d11f` | `UnitState.ap_per_turn`（建立單位時決定）：玩家方 `party_ap_per_turn` 4、召喚物 `ap_per_turn` 3（照現行）、敵人照範本新欄位 `UnitTemplate.ap_per_turn`，沒寫時標籤 `elite`／`boss` 用 `elite_ap_per_turn` 4、其他 3。本回合上限＝單位每回合 AP＋`ap_carry_max`（玩家方 5）。`LOG_FORMAT` `/133 → /134` |
| 3 失手返還 | `b5f1f7d61` | 實際花了 ≥ `miss_refund_min_cost`（2）AP 的施放，所有敵方目標都沒命中 → 返還 `miss_refund_ap`（1）AP；每單位每回合 1 次（`UnitState.miss_refunded`）；事件 `ap_refunded.on_miss`、紀錄文字「全部落空，返還了 1 AP（失手返還…）」；AI 的擊殺返還估值不算它 |
| 6 API | `fc3a6b4eb` | `UnitView` 多 `ap_per_turn`、`ap_max`、`ap_carried_in`（這回合帶進來的保留）、`ap_lost`（這回合開始被扣的）、`ap_next_loss`（下回合會少的）；OpenAPI、`schema.d.ts` 重產 |
| 5 AP 列 | `14e521aea` | 主角狀態卡 AP 圓點：一般金點、保留那格的米白環、紅斜線（這回合已扣的接在一般 AP 後；下回合會少的在分隔線右邊）、每顆自己的說明卡、滑過「結束回合」時會被保留的那顆閃米白環（CSS `body:has(.end-turn-button:hover)`，0.6 秒 ×2）。沒有預支按鈕、橘色菱形 |
| 報告 | （本 commit） | 本報告、`戰鬥紀錄格式變更.md`、`上手-引擎戰鬥結算.md` 第 57 點 |

「沒命中」的判定（`refunds.all_targets_missed`，看這次施放的事件）：一個敵方目標擲了命中而每一下都失手；或命中（或不擲命中）之後，對它的抵抗判定（狀態抵抗、互換／傳送／擊倒的對抗）全被擋下、也沒受到這次施放的傷害。不擲命中又沒有抵抗判定的目標算命中；範圍內沒有敵方目標時不返還。

工坊白名單（`content/tuning_fields.yaml`）：核心規則加 `party_ap_per_turn`、`ap_per_turn`、`elite_ap_per_turn`、`ap_carry_max`、`miss_refund_ap`、`miss_refund_min_cost`；敵人與頭目加 `ap_per_turn`。**沒有放在檔尾**：白名單 schema 規定 `targets` 的 `kind` 不能重複，所以加在既有的 `rules`、`unit` 兩段裡（各有 `# AP-1` 註解）。SK-5 改的是組合器、觸發的條目，合併時這兩段應該不會撞。

## 2. 檢查（結束碼）

最後一次（第 6 項、第 5 項 commit 前）：

| 指令 | 結束碼 |
|---|---|
| `ruff check .`／`ruff format --check .` | 0／0 |
| `mypy`（1718 檔） | 0 |
| `lint-imports`（14 kept） | 0 |
| `trpg content check` | 0 |
| 前端 `tsc --noEmit`、`pnpm -C client build` | 0、0 |
| vitest `src/ui`（51 檔 695）；全部 vitest（第 6 項前跑過一次，385 檔 4758） | 0 |
| pytest 分目錄一次一組（`-n 8`）：engine 5091、api 1325（1 skip）、cli 148、`-m slow tests/cli` 44 | 0 |
| 同上，第 3 項 commit 前：world 1328、roguelite 279、sim 180、content＋narrative＋shared＋llm＋bot＋架構等 4294 | 0 |
| 重播：`trpg battle --map open_plain --seed 10` ＋ `battle replay`（有 2 次保留 AP、1 次失手返還：盜賊隊長「全部落空，返還了 1 AP」） | 0（「重播驗證通過：71 個動作、311 個事件」） |

第 1、3 項各自 commit 前也跑了 engine、cli、`-m slow tests/cli` 與改到的其他測試檔，都是 0。全量 `scripts/check.py` 沒跑（PM 跑）。

## 3. 不變比對

腳本在 scratchpad（未 commit）：改前＝`git archive 1ed3c79f8` 的 `src content config`、`PYTHONPATH` 指向舊 `src`（印出載入的 `trpg` 路徑確認）；改後＝目前程式＋把 `content/` 複製出來只改 `rules/core.yaml` 的工坊值。地圖預設陣容、效用 AI、`max_rounds=30`；10 張一般圖 × 種子 1、2 ＋ 4 張頭目圖 × 種子 3～12（同 SK-3c）。比整份事件、步驟、最終狀態（去掉 `ruleset`、`ruleset_hash`、`format` 與新欄位 `ap_per_turn`、`miss_refunded`、`ap_carried_in`、`ap_lost`）。最終程式（第 6 項之後）：

| 工坊值（玩家方／精英頭目／失手返還） | 結果 |
|---|---|
| 3／3／0（關回舊行為） | `battles=60 events=23897 different=0`（events 和 SK-3d 的基準相同） |
| 4／3／0（只開玩家方 4 AP） | different=60 |
| 3／4／0（只開敵人 AP 欄位：精英、頭目 4） | different=48 |
| 3／3／1（只開失手返還） | different=49 |
| 4／4／1（初值） | different=60 |

第 3 項做完時（第 6 項之前）也跑過 3／3／0：different=0。

## 4. 快照、夾具（先預測再逐鍵核對）

| 東西 | 預測 | 結果 |
|---|---|---|
| CLI 快照（24 鍵） | 第 1 項：7 個 `battle_*` 全變（我方都是 4 AP）；`skills_list`、`skills_show_all/*` 不變（技能卡不寫每回合 AP） | 對：只有 7 個 `battle_*` 變，`-k battle_` 不加 `-n` 重產 |
| 同上，第 3 項 | 有失手返還的戰鬥變 | 7 個裡 5 個變（`battle_*` 另外 2 場沒有返還） |
| `glossary.json` | 結束回合的說明「每回合 3 AP」→ 4 | 只有那一行 |
| `test_field_ctx_replay` 的凍結雜湊 | 不該變 | 一開始變了：`UnitTemplate.ap_per_turn` 是 `None` 時也輸出，角色存檔 JSON 多一個鍵。改成 `None` 不輸出（`exclude_if`），雜湊回到原值、沒改常數 |
| OpenAPI | `UnitView` 多 5 個欄位 | 只有這 5 個 |

## 5. 為新規則改的測試（種子、條件）

都是「某個種子剛好出現某件事」的測試；每個新種子都在失手返還開、關兩種下確認過（第 1 項 commit 是關的狀態，第 3 項之後是開的）。

- 換種子：`test_displace_ai` 32→4、`test_hurl_object` 27→35、`test_scene_ai` 推倒 0→3、穿甲 3→2、`test_boss_phases` 雲頂 [1,5]→[2,3]、`test_gamble` [17,37]→[0,6]、`test_rewrite_primitives` 守護轉移 0→1、複製 0→1、`test_rule_changes` 化身 0→1、`test_self_moves` 廢墟 3→1、`test_summon_ai` 5→7、`test_status_determinism` (9,10)→(4,9)、`test_oaths` [0,6]→[2,6]、`test_grant_skill` 飛行 7→11、`test_world_dev_boss` 角色 ID `c_0000b055`→`b056`、`test_reflash_hint_fl1g` 2→4、`test_elite_duel_rg2` (0,1)→(0,11)、CLI：守護 18→27、換位＋瞄準 17→237（0～299 只有 237、247、258）、其他圖吊橋 0→1、示範圖吊橋 4→169、雷霆終結 46→20、`run auto` [4,6]→[11,13]。
- 改條件：`test_economy_battle` 的主角帶傷（滿血的三分之一）上陣——4 AP 後滿血打渡口 40 個種子都用不到藥水；`test_flash_economy` 的種子 `range(8)`→`[0,4,6,7]`（失手返還後種子 5 一輪要 2 分多鐘，平行跑會超過單測 300 秒上限）。
- 鎖回舊行動經濟（`tests/engine/helpers.with_pre_ap1_turns`，同 `without_sk1_flash` 的做法）：`tests/roguelite` 的重閃重現案例 3 檔（rr1、rr2、fl1h：種子 2 打到營火的閃現歷程換了）、`tests/sim/test_skill_fuzz` 的 100 種子（兩個「擊殺時」被動在試打中都輪不到施放者擊殺）。
- `RARELY_CHOSEN` 加 `fire_dust_bat`／`skill_cinder_dive`：兩隻火塵蝠在空地圖 1～2 輪就倒，每次都先放火球術。
- 版號字面值 `/133`→`/134`（8 檔＋4 個 `endswith`）；`test_turns`、`test_rewrites`、`test_practice_mode`、`test_on_kill` 改成照單位的每回合 AP。
- 新測試：`test_ap_per_turn_ap1.py`（陣營、精英、頭目、範本覆寫、大世界精英標籤、召喚物、保留上限、工坊值關回 3）、`test_miss_refund_ap1.py`（單體失手、範圍中 1 個、範圍全空、豁免擋下、命中有傷害但狀態被擋、不擲命中的互換被擋／成功、每回合 1 次與下回合再拿、1 AP 不返還、敵人也拿、工坊值 0 關閉、紀錄文字、確定性）、`test_ap_view_ap1.py`、前端 `apRow.test.ts`。

## 6. 截圖（`docs/art/shots/ap-1/`）

無頭 Chrome（`--headless=new --mute-audio`，DPR 1，1600×900）＋網址 `?dev=1&mute=1`；自己的 `trpg serve`（埠 8766）＋暫存 vite 設定（埠 5294，`/api` 轉 8766，用完刪掉）＋ CDP 除錯埠 9737。戰鬥先用 API 推到要拍的那一刻（`open_plain`，鐵壁起始包＋工坊版竭力一擊〔透支 1〕），頁面按「一鍵開局」時把那一次建立戰鬥的回應換成 `GET /api/battles/<id>`。結束時三個程序都停了、埠都關了，瀏覽器分頁也關了。每張另附 `*_ap_x4.png`（AP 那一格用 4 倍解析度重新算繪，不是最近鄰放大）。

| 第 6 節 | 檔名 | 畫面 |
|---|---|---|
| 1 | `1_kept.jpg` | 上回合保留 1 格：5 顆金，最後一顆有米白環 |
| 3 | `3_overdraft_next_turn.jpg` | 透支後的下一回合：3 顆金＋1 顆紅斜線在最後 |
| 4 | `4_end_turn_hover.jpg` | 滑過「結束回合」：會被保留的第 4 顆閃米白環（拍在亮的那一刻） |
| 6 | `6_next_turn_minus2.jpg` | 下回合 −2：分隔線右邊兩顆紅斜線（見待決 7：這張的 −2 是改回應資料畫的） |

## 7. 待 PM 決定

1. **工坊條目沒放檔尾**：`targets` 的 `kind` 不能重複，加在既有的 `rules`、`unit` 兩段裡（見第 1 節）。
2. **精英、頭目的 AP 用標籤推**：範本有 `ap_per_turn` 欄位（可覆寫），沒寫時標籤 `elite`／`boss` → `elite_ap_per_turn`。這樣大世界加精英詞條的一般敵人也是 4 AP（詞條會加 `elite` 標籤）。如果要每個範本都寫死，再補資料。敵人範本當隊友（傭兵）時一律照玩家方。
3. **失手返還不算進裝備的每回合 AP 回復上限**（`ap_gain_turn`），所以同一回合還能吃到「擊殺時回 1 AP」詞條。
4. **失手返還只看一般施放**：陷阱、瞄準預告（射出時另外結算）、延遲段的釋放、反應技不返還；一個敵人都沒有的施放也不返還。
5. **「被豁免擋下」的解讀**：命中後對目標的抵抗判定全被擋、也沒受到傷害才算沒命中；有傷害、只是狀態被擋的算命中（範例測試有一列）。
6. **AP 列幾處畫法文件沒寫的地方**：(a) 回合開始已經扣掉那格的說明字用「透支：這回合少 N AP」（第 5 節只有「下回合少」的字）；(b) 不是自己的回合時，畫每回合 AP 顆空心點（以前是 1 顆空心），保留寫在說明裡「（下回合保留 +N）」照舊；(c) 被給、被返還多出來的 AP 接在一般 AP 後面；(d) 超過 9 顆改寫數字。
7. **第 6 張（−2）實機做不出來**：透支固定 1、同一個狀態不疊加，AP-1 沒有預支，所以真畫面最多 −1。這張是真的遊戲畫面（施放竭力一擊的那一回合，真的有 1 顆紅斜線），頁面把回應裡主角的 `ap_next_loss` 加 1 再畫。預支技能那段（AP-2）可以重拍真的。
8. **測試改種子、鎖回舊行動經濟、改條件**都列在第 5 節；其中 `test_flash_economy` 種子 5 一輪 138 秒（其他 1～55 秒），平行跑會逾時，原因沒查（沒跑量測）。
9. **`tests/engine/helpers.give_turn` 仍給 `core.ap_per_turn`（3）**，沒改成單位的每回合 AP，避免大量既有測試變動；新測試直接跑回合流程。
10. **第 4 項**（耗費結構不動）沒有程式改動，所以沒有 commit；SK-5 若也升 `LOG_FORMAT`，合併時要再往上排一號。
