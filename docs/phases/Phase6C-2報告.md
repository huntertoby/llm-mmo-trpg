# Phase 6C-2 完成報告：就地開打：從實地地圖切 12×12 戰場

> 實作者 agent，2026-11-04。依據：`docs/phases/Phase6計畫.md` 第 1 節 6C-2 列、0.4 Q8；`docs/design/21-探索地圖與城鎮.md` 21.4、21.9 第 6 條、21.10；`docs/design/05-戰鬥.md` 5.10；`Phase6C-1報告.md`、`Phase6C-1b報告.md`（待決 5）、`Phase6B-6報告.md`、`Phase6C-3報告.md`／`Phase6C-4報告.md`（測試輔助 `cut_battlefield`）。
> 開工時 `git merge main`：已是最新（含 6C-1／6C-1b、6B-6）。**沒有改引擎**（`src/trpg/engine/`）；沒有動 `client/src/render/`、HUD 版面、功能列圖示、NPC 與朋友。

## 1. 交付內容

| 項目 | 檔案 |
|---|---|
| 切 12×12、起始區、合法性、退回模板 | 新檔 `src/trpg/world/battlefield.py`（`cut_origin`、`cut_battlefield`、`contact_battlefield`、`UnitCounts`、`Battlefield`、`FALLBACK_ZH`） |
| 接上開戰 | `src/trpg/world/battle.py`：`prepare_battle` 先組好雙方單位再選地圖（`_battlefield`）；`PreparedBattle.field_cut`、`cut_fallback`；`BattleStartedEvent` 帶出；`_battle_setup` 的骨架照模板地圖 ID 建（切出來的地圖不在內容庫） |
| 事件 | `src/trpg/world/actions.py`：`BattlefieldCut`（實地地圖 ID、左上角、大小）、`CutFallback`（退回原因）；`BattleStartedEvent.field_cut`、`.cut_fallback` |
| 接觸資料 | `src/trpg/world/state.py`：`FieldContact.enemy_at`（接觸時那一隊站的格子）；`field_enemies._contact_model` 寫入 |
| 存檔格式 | `trpg-char/3` → `/4`（只多了選填欄位，照讀升版）；`trpg-wlog/4` → `/5`（`/4` 照讀、標成「規則已變、不能重播」，同 6B-2 的做法） |
| `SHARED_CLEAR_KINDS` | 拿掉常數，`shared_clear` 改讀 `content/world/rules.yaml` 的 `battle.clear_kinds`，該檔改成 `[camp, elite_lair, ruin, altar]` |
| API | `src/trpg/api/world_schemas.py`：`BattlefieldRectView`、`EncounterView.battlefield`、`.battlefield_fallback_zh`；`world_presenter.py` 填值；`client/openapi.json`、`client/src/api/schema.d.ts` 重產 |
| 前端 | 新檔 `client/src/world/battlefield.ts`（`battleFrame`、`battlefieldLine`）＋測試；`screens/WorldScreen.tsx` 只把 `hud.frame` 接上 `battleFrame(v)`；`world/WorldPanel.tsx` 遭遇卡多一行戰場說明 |
| 測試 | 新檔 `tests/world/test_battlefield.py`（29 項）、`tests/api/test_world_battlefield_view.py`（2 項）、`client/src/world/battlefield.test.ts`（5 項）；既有測試調整見第 5 節 |
| 截圖 | `docs/art/6c2_cut_battle.jpg`（切出的戰場，戰鬥畫面）、`docs/art/6c2_fallback_template.jpg`（退回模板）、另附 `docs/art/6c2_cut_framed.jpg`（遭遇時鏡頭框住戰場） |

## 2. 規則怎麼落實

**切法**（21.4）
- 中心＝「我方接觸點」與「那一隊所在格」的中點（捨去小數），同 6C-3／6C-4 的測試輔助。左上角 `x0 = clamp(cx − 6, 0, 寬 − 12)`，`y0` 同；靠邊往內平移、不超出地圖。
- 地形、高低差、物件、表面（含持續輪數）照實地地圖切出；圖例只留用到的符號。
- `region` 不寫，交給 `reskin(…, encounter.region)`（換成該區的預設外觀，照舊）。
- `archetype`、`tags`、`weather` 照地點原本的戰鬥地圖模板（`encounter_map` 選的那張；見待決 3）；勝利條件一律全滅，沒有地圖事件、源泉。
- 地圖 ID `cut_<實地地圖>_<x0>_<y0>`、名稱＝地點名稱。

**起始區**（依接觸方向與先手）
- 我方從接觸點、敵方從那一隊所在格起算，只取「從自己起點走得到」的格子。排序：自己這一側優先（離自己起點比離對方近 → 等距 → 比較近對方）、離自己起點的曼哈頓距離、y、x。所以主角站在接觸點、敵方帶頭的站在地圖上看到的位置，其他人往各自後方排開。
- 格數：至少敵方 4、我方 3；單位比較多時照單位數（傭兵、影子、劇情夥伴、增援都算）。第三方不畫起始區（引擎排在敵方附近），但要留得出位置。
- 先手的那一方先挑（同一格接觸時那一格歸先手方）；沒有先手（側面相鄰）照敵方先挑。

**不合法就退回模板**（記在 `BattleStartedEvent.cut_fallback` 與遭遇畫面）
| 原因 | 代碼 | 畫面文字 |
|---|---|---|
| 實地地圖不到 12×12 | `too_small` | 地圖不到 12×12 |
| 起點不可站、走得到的格子放不下起始區或第三方 | `zones` | 站位放不下 |
| `check_map` 沒過（例如雙方隔著深淵走不到對方） | `check_map` | 切出來的戰場不合法 |
| 模板是 Boss 地圖 | `boss` | Boss 戰用專屬地圖 |
| 遭遇指定了撤離／守點而模板有這個條件 | `objective` | 這場的勝利條件只有原本的戰場有 |
| 接觸資料沒有敵人位置（6C-2 以前的存檔） | `no_enemy_at` | 舊存檔的遭遇沒有敵人位置 |
| 找不到實地地圖 | `no_field` | 找不到實地地圖 |

不是地圖上碰到的遭遇（沒有地圖的地點、事件的戰鬥解法、賽季 Boss）照舊用模板，`cut_fallback` 是 `None`。

**確定性**：切法只看內容與遭遇資料，不耗亂數；模板照舊先用 `"{battle_seed}:map"` 選（切不切都一樣，亂數消耗不變）；所有集合排序後才取。

**戰後回到哪**（Q8，21.10 第 7 條）：6C-1 已實作，這段加測試確認切出來的戰場也一樣——打贏站在接觸點；撤退回這一趟進地圖時站的格子（入口）；全滅照現行回小鎮。

**戰鬥紀錄與重播**
- 戰鬥設定（`BattleSetup.map`）就是切出來的 `MapDef`，所以 API 的戰鬥工作階段、`fight` 回寫、掉落都用同一份；設定序列化再讀回來地圖不變（測試鎖住）。
- 世界日誌只存動作，重播時 `prepare_battle` 從內容與 `pending_encounter`（含 `enemy_at`）重算出同一張圖。`trpg-wlog/4` 的 `fight` 步驟是照模板地圖記的，所以升 `/5`、`/4` 標成不能重播。

## 3. 正式內容的接觸點（只報告）

- 相鄰接觸：每張室外圖的每一隊，在駐守點（巡邏的每個轉折點）四方向相鄰、站得上去的格子，共 **267 個接觸點**（涵蓋全部 spawns），陣容照遭遇表、我方 3 人。**退回模板 0 個**（測試 `test_every_content_spawn_cuts` 鎖住「每隊都有涵蓋、清單是空的」）。
- 另用暫存腳本擴大到每一隊巡邏路線每一格、四個朝向的整個視野扇形（實際可能的所有接觸點），共 **9073 個**，退回模板也是 **0 個**。
- 所以正式內容目前不會出現退回模板；退回只會發生在舊存檔（`no_enemy_at`）或之後新畫的窄圖。

## 4. 前端與「不換畫面」

- 遭遇出現時（`encounter.battlefield` 在目前這張實地地圖上），`WorldField` 的 `hud.frame` 接上 `battleFrame(view)`，鏡頭用 6B-6 的 `frameCamera` 框住 12×12（四周各半格，最多 1 倍、最少 0.5 倍），平移 300ms。遭遇結束（打完、撤退）`battlefield` 消失，鏡頭回到跟隨主角。退回模板時不框。
- 遭遇卡多一行：「就地開打（12×12，地形照剛剛看到的）」或「改用這裡原本的戰場：〈原因〉」。
- 實測（API 8302、vite 5305、存檔在 scratchpad 暫存資料夾；用完已停掉、暫存 vite 設定已刪）：渡口石階，駐守 (9, 6) 西邊接觸；遭遇卡出現、鏡頭改成框住戰場；按「開戰」後戰鬥畫面的地形就是石階那一塊（`6c2_cut_battle.jpg`）。另一個角色把接觸的 `enemy_at` 拿掉模擬舊存檔，遭遇卡顯示退回原因、戰場是模板「懸崖前哨」、鏡頭照舊跟隨（`6c2_fallback_template.jpg`）。

**完全「不換畫面」還差什麼**（現行流程是換成 `BattleScreen` 元件）：
1. 開戰仍切到 `BattleScreen`（另一個畫布、另一套 HUD）。要不換畫面，需要讓 `WorldField` 的畫布直接當戰場：戰鬥單位疊在實地地圖上（12×12 以外的格子變暗或鎖住）、戰鬥 UI（行動列、技能卡、回合順序）改成疊在 HUD 版面上。
2. 戰鬥座標是切出來的局部座標，畫在實地地圖上要加 `(x0, y0)` 位移（`BattlefieldRectView` 已給）。
3. 戰鬥結束要把畫面上的單位收回成實地地圖的狀態（敵人消失、主角站回接觸點），目前是「回到地點圖」重新載入。
4. 05 5.10 的「平常不畫格線、選移動與選範圍才浮出」是戰鬥畫面本身的呈現（6A-4 系列），和上面三點可分開做。
5. 外觀：實地地圖的室外圖與戰鬥用同一套繪製器，但戰鬥畫面自動填滿縮放（`fitScale`），格子大小和實地地圖不同（6B-6 待決 1）。

## 5. 既有測試的調整

- 版號字串：`trpg-char/3` → `/4`、`trpg-wlog/4` → `/5`（`test_save.py`、`test_field.py`、`test_world_field_api.py`、`test_opportunity_hints.py`）。
- `test_field_enemies.py::test_replay_sneak_and_clear`、`test_field_enemies_6c1b.py::test_replay_arrival_and_per_group_clear`：改成就地開打後，1 級支援主角＋2 傭兵貼著 3 名盜賊開打會輸（原本在模板地圖上分開站會贏）。這兩個測的是清空與重播，所以主角改成 3 級，測試的意思不變（見待決 1）。
- `test_field_enemies_6c1b.py::test_shared_kinds_constant` → `test_shared_kinds_from_rules`（讀規則檔；規則拿掉遺跡就不共享）。

## 6. 測試與檢查結果

- `UV_NO_SYNC=1 uv run pytest -q tests/world tests/api tests/content tests/server tests/test_architecture.py -n 8 -x`：4032 通過、1 skip（5 分 15 秒；server 與 architecture 因為改了存檔格式一起跑）。
- 新測試 `tests/world/test_battlefield.py` 29 項：切的左上角（中間、四角、非正方形、剛好 12×12）、地形高低差物件照抄且 `check_map` 通過、起始區方向表格（東西南北、相鄰與視野距離、靠邊）、先手搶同一格（我方／敵方／沒有）、人數多時起始區變大、退回模板表格（太窄兩種、站位放不下、隔深淵 `check_map` 失敗）、確定性、`contact_battlefield` 各種退回（不是接觸、沒有敵人位置、Boss、勝利條件、沒有實地地圖）、`prepare_battle` 用切出來的圖（主角在接觸點、駐守在原地）、舊存檔退回模板、**重播兩場（就地開打、退回模板）：戰鬥重播逐位元一致＋世界日誌重播兩次角色與世界一致＋打贏回接觸點**、撤退回入口、正式內容 267 個接觸點。
- `tests/api/test_world_battlefield_view.py` 2 項：遭遇畫面帶出戰場範圍／退回原因。
- 前端：`vitest run src/world src/screens src/ui` 35 檔 350 項，349 通過、1 項失敗＝`src/ui/floatCardRule.test.ts` 抓到 `world/WorldHud.tsx` 的 `role="dialog"`，是 main 上 6B-5 就有的（6B-6 報告待決 3），這段沒碰。`tsc --noEmit`、`pnpm build` 通過（只有原本的 chunk 大小警告）。
- `ruff check .`、`ruff format --check .`、`mypy src`（506 檔）、`lint-imports`（13 kept）通過。
- swamp 種子 7 重播：通過，88 個動作、313 個事件，最終狀態一致。
- 沒有跑全量。沒有新增 `# noqa`（除了測試的 pytest 參數化 `PLR0917`，同既有寫法）。

## 7. 待 PM 決定（都已照最保守的做法做完）

**規則類**

1. **貼著敵人開打很兇**：主角站在接觸點、敵方帶頭的站在原位，相鄰接觸時第 1 輪就是近身戰。測試裡 1 級支援主角＋2 傭兵對渡口石階 3 名盜賊，模板上會贏、就地開打會輸（3 級才贏）。21.4「開場站位照誰先發現誰」照字面做；若想在接觸點和敵人之間至少留幾格（例如起始區離對方起點 ≥ 3），要訂規則。建議 PM 之後安排一次模擬比較兩種站位的勝率。
2. **`clear_kinds` 加了精英巢穴、遺跡、祭壇之後的副作用**：地圖上碰到的隊伍行為不變；但**不是**從地圖上碰到的戰鬥（事件的戰鬥解法）在這三種地點打贏，現在也會把整個地點寫「已清空」（以前只有營地會）。正式內容裡這三種地點都有實地地圖與敵人，所以只影響事件開的戰。若要維持只有營地，需要另一個欄位（或把非接觸的清空限制寫進規則）。
3. **切出來的戰場的地圖類型、標籤、天氣照模板**：`tags`（例如 `forest`，精靈的「林間視野」看它）、`archetype` 取該地點原本的戰鬥地圖；若要依實地地圖的地形判斷是不是森林，要訂規則或在實地地圖加標籤。
4. **撤離／守點的戰鬥解法**：遭遇指定了撤離或守點、而模板有這個條件時退回模板（切出來的戰場沒有出口格與守點格）。正式內容裡地圖上碰到的遭遇沒有指定勝利條件，目前不會發生。
5. **中心取中點**：「以接觸點為中心」照 6C-3／6C-4 的測試輔助取「我方接觸點與敵方所在格的中點」；視野接觸最遠差 4 格，兩種取法的差別最多 2 格。

**數值／解讀類**

6. 起始區排序（自己這一側 → 距離 → y → x）、沒有先手時敵方先挑、單位比較多時照單位數擴大起始區。
7. 第三方不畫起始區（照引擎的自動排法），只檢查留得出位置。
8. 6C-2 以前存的遭遇（沒有 `enemy_at`）開戰時退回模板，不另外補算敵人位置。

## 8. 測試結果（交件前）

- 相關 pytest（world、api、content、server、architecture）：4032 通過、1 skip。
- vitest `src/world src/screens src/ui`：349／350（唯一失敗是 main 上既有的 `floatCardRule.test.ts`）；`tsc`、`build` 通過。
- ruff、format、mypy、lint-imports、swamp 種子 7 重播：全部通過。
- 沒有跑全量（守則 11）。
