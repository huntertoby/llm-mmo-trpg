# Phase 6E-2 報告：#123 冰面滑倒並滑行

規格：`docs/phases/Phase6計畫.md` 第 1 節 6E-2 列；設計 `docs/design/05-戰鬥.md` 表面規則「冰面：滑倒並滑行」與 5.10。
開工時 `git merge main`：已是最新（含玩法 PM 的 eba626f2、008301e5），沒有衝突。沒有新增相依；沒有碰 `src/trpg/world`、世界端點、伺服器日誌讀取、`client/src/world/`。

## 1. 引擎（`src/trpg/engine/ice_slide.py`，新檔）

- **內容即資料**：表面檢定新增 `slide_max`（`SurfaceCheck`，預設 0＝舊行為）；`content/surfaces.yaml` 的冰面設 3。
- **檢定**：自己走（`Move` 的 `walk` 步）進一段冰的第一格時，在那一步的反應、陷阱結算之後擲一次敏捷 DC 12（`check_rolled` 新欄位 `slide: true`）。「同一段」＝ 路徑上前一格是同一種表面；同一次移動離開冰面再走進另一段冰會再擲。`enter_surface` 在自己走進／滑行進來時跳過會滑行的檢定，被推、拉、表面出現在腳下照舊（檢定、觸發表套用倒地、不滑）。
- **失敗**：沿走進來的方向一格一格滑（每格 `unit_moved`，新 `mode: slide`），最多 3 格：
  - 下一格是地圖邊緣（`edge`）、其他存活單位（`unit`，敵我都算）、致命地形（`deadly`）、不可站立的地形（`wall`）或擋路物件（`object`）、高度差 ≥ 1（`height`，上下坡都算）時停在目前這一格；
  - 滑到冰面外的第一格停下（`off_ice`）；滑滿 3 格仍在冰上（`max_tiles`）；
  - 滑過的格子照「走進那一格」：陷阱照樣觸發（定身、暈眩、被推離、倒下、撤離 → `interrupted`，停在那格），火、毒等表面照樣生效（`arrive` 的一般流程）。
  - 停下後發新事件 `unit_slid`（`path` 含起點與停點、`stop_reason`），**之後**才倒地（`status_applied`），`move_points` 歸零（這次移動剩下的點數作廢），路徑剩下的步數不走。
- **不變**：矮人、鱗族（`slip_immune`）與會飛的單位不擲、不滑；被推、拉進冰面維持舊規則；衝鋒（`dash`）與跳躍落點照舊（見待決 3）。
- **`_slide_back_if_stacked` 保留**：滑行停點已排除單位格，但「第一格冰上就站著友軍（走路可穿過友軍）且下一格就擋住、一格都沒滑」時仍會倒在友軍格上；被反應擊倒在友軍格上也一樣。docstring 寫明了這兩種情況。
- **確定性**：只用 `ctx.check_d20()`；同一段冰的亂數取用從「每格一次」變成「一次」。預覽另有內部的強制分支 `Ctx.slide_fail_at`（第 N 次滑行檢定失敗，其餘照最少後果；正式結算不用）。
- **敘事**：`unit_slid` 一行，例如「戰士 在冰上滑倒，滑行 2 格：(3, 3)→(4, 3)→(5, 3)（前方有人）」；`slide` 的 `unit_moved` 不另寫。
- **戰鬥紀錄**：`LOG_FORMAT` `/111` → `/112`，`docs/phases/戰鬥紀錄格式變更.md` 加了一條（`/111` 的紀錄無法重播）；測試裡的字面值一併更新（`tests/cli/*` 6 個、`test_gear_g2/g3a`、`test_24c`、`test_self_costs`、`test_wind_54a`）。
- **CLI 快照**：只有 `battle_frozen_lake_push_3` 變了（冰湖地圖的冰面結算改變，預期內），用 `UPDATE_CLI_SNAPSHOTS=1` 只重產這一鍵；其他 23 鍵不變。沒有其他重播 fixture 受影響（`git grep battle-log/111` 只剩 `Phase6計畫.md` 的開工基準描述，沒動）。

## 2. 路徑預覽（`engine/path_preview.py`、`api/path_schemas.py`）

- `SlipRun` 每段冰一筆：`start`（擲檢定的格）、`end`（這段冰在路徑上的最後一格）、`chance`（第一格的失敗率，精確 `Fraction`）、**單一停點** `fail_stop`、`slide_path`（含起點）、`stop_reason`、`status_id`；另有 `immune`（矮人、鱗族：「冰 N 格・不會滑倒」）、`stop_trap`（停點上有看得見的敵方陷阱）、`stop_surface`（停點上冰與無以外的表面）。原本的 `fail_stops`（多停點）移除。
- 停點不是靜態推算：對每一段另跑一次同一套引擎的模擬（`battle.simulate_slide_failure`：只有這段的檢定失敗、其餘照最少後果），所以撞牆、撞單位、高度差、致命地形、滑過陷阱、倒在友軍格滑回空格都與實走一致。預覽不改狀態、不動 `rng_state`（原有的 hypothesis 性質測試照過）。
- API `SlipRunOut` 同步（`fail_stop`、`slide_path`、`stop_reason`、`immune`、`stop_trap`、`stop_surface`；`chance_permille` 改為第一格的機率），`client/openapi.json`、`schema.d.ts` 重產。

## 3. 前端

- **小牌**（`battle/pathPreview.ts`）：`冰 N 格・滑倒 xx%・失敗滑到 ◆ 倒地`；一格都沒滑時「失敗就地倒地」；停點有陷阱／表面時加「（滑到陷阱）」「（滑到火焰）」；不會滑倒的種族「冰 N 格・不會滑倒」。滑行的每一格（`displaced: slide`）不另出小牌。
- **◆**：`PathDraw.slipStops`，`render/pathArt.ts` 在停點格中心畫藍色菱形（白邊），和驚嘆號一起畫在最上層；就地倒地、不會滑倒的段不畫。
- **動畫**（`battle/walkAnim.ts`、`render/BattleRenderer.ts`、`render/motionClips.ts`、`render/walkFx.ts`）：
  - 第一格檢定失敗（`check_rolled` 的 `slide: true`）→ 新停頓 `stumble`（220ms，冰花＋滑痕，左右晃兩下 `stumbleTilt`）；
  - 每個 `slide` 的 `unit_moved` → 新片段 `skid`（每格 70ms，比走路的 120ms 快；敵方回合一樣 2 倍速；等速、不踏步，`skidBody`：往後仰 0.22、雙手張開的固定姿勢）；
  - `unit_slid` → 停點的 `slip` 停頓：接 6M-3 的倒地姿勢（`proneBody`，從滑行姿勢倒下），之後倒地狀態照舊躺著；一格都沒滑時踉蹌與倒下合成一個倒下；滑過陷阱時在陷阱格照常停頓；之後倒在友軍格的 `teleport` 照舊改成短短滑回。
  - `MoveMode` 加 `slide`（`api/types.ts`、`battle/animation.ts`：滑動 70ms）。

## 4. 敵人 AI（`engine/ai/utility.py`）

- `ice_slip_cost`：路徑上每次滑行檢定（依序；前面都通過才會擲到）× 失敗率 ×（`ice_slip_points` ＋ 終點與滑行停點的位置價值差〔下限 0〕）。停點用 `ice_slide.static_slide` 靜態推算（只看地形、物件、單位，不看陷阱），失敗率是精確分數，全程 `Fraction`、確定性。
- 套在移動的兩處：虛擬分數排序（決定哪些移動進入完整預覽）與完整預覽後的分數。其他動作、其他權重不變。
- 新權重 `basic.ice_slip_points`（`BasicActionAiRules`，content 8，初值保守、未調）。
- 測試：冰面擋在兩條等價路線之一時，AI 走乾的那條（兩個方向都測）；沒有冰時代價為 0；排序結果重跑相同。

## 5. 模擬（守則 8）

`scripts/ice_slide_sim.py`（新）：「舊」＝ 同一份程式把冰面的 `slide_max` 覆寫成 0（等於 #123 之前：每格檢定、失敗停在那格；AI 也不估滑行代價），「新」＝ content 現況。地圖冰湖（`frozen_lake`，原本就有冰）與沼澤（`swamp`，冰系技能把水凍成冰）；build 冰系三個（`build_storm`、`build_support`、`build_healer`）＋對照兩個（`build_tank`、`build_fire`）。新舊同一批種子，安靜模式，只跑這個量，沒跑全量 matrix。

指令：`uv run python scripts/ice_slide_sim.py --seeds 60 --jobs 8 --out <檔>`（1200 場）。

地圖 frozen_lake、swamp；build build_storm、build_support、build_healer、build_tank、build_fire；每格 60 種子（種子 1000～1059，新舊同一批）；例外 0 場

| 地圖・規則 | 勝率 | 輪數 | 冰面檢定／場 | 我方滑倒／場 | 敵方滑倒／場 | 滑行格數／場 |
|---|---|---|---|---|---|---|
| frozen_lake 舊（每格檢定、不滑） | 79.7%（n=300） | 6.24 | 34.36 | 7.77 | 8.32 | 0.00 |
| frozen_lake 新（滑倒並滑行） | 80.3%（n=300） | 5.09 | 8.00 | 1.68 | 2.09 | 5.89 |
| swamp 舊（每格檢定、不滑） | 56.0%（n=300） | 6.09 | 1.12 | 0.06 | 0.49 | 0.00 |
| swamp 新（滑倒並滑行） | 56.0%（n=300） | 6.11 | 0.73 | 0.02 | 0.36 | 0.04 |

| build | frozen_lake 舊／新 | swamp 舊／新 |
|---|---|---|
| build_storm | 86.7%／96.7% | 63.3%／63.3% |
| build_support | 80.0%／81.7% | 36.7%／38.3% |
| build_healer | 90.0%／75.0% | 75.0%／73.3% |
| build_tank | 68.3%／55.0% | 48.3%／48.3% |
| build_fire | 73.3%／93.3% | 56.7%／56.7% |

結論（只量不調）：

- **冰湖**：冰面檢定從每場 34.4 次降到 8.0 次，滑倒從每場約 16 次（我方 7.8、敵方 8.3）降到約 3.8 次，平均每場滑行 5.9 格；戰鬥從 6.24 輪縮短到 5.09 輪。**整體勝率幾乎不變**（79.7% → 80.3%）。
- **沼澤**（冰是技能凍出來的、面積小）：檢定與滑倒本來就少，勝率不變（56.0% → 56.0%），只有極少數滑行。
- **各 build 在冰湖的差異大**（每格 n=60，標準誤約 5～6 個百分點）：輸出型的 `build_fire` +20.0、`build_storm` +10.0；續戰型的 `build_healer` −15.0、`build_tank` −13.3；`build_support` 持平。推測是「少滑倒、戰鬥變短」讓先打出傷害的一方更有利，持久型的優勢變小；敵人 AI 避冰也改變了接敵路線。這次沒有把「規則改變」和「AI 避冰」拆開量（要的話可以用 `ice_slip_points: 0` 再跑一次新規則）。
- 建議：沒有需要立刻調的數值；`build_healer`／`build_tank` 在冰湖的下降請 PM 判斷是否列入下一輪平衡觀察。

## 6. 測試

- 新 `tests/engine/test_ice_slide.py`（24）：13 種停止條件的表格（滑出冰面、滑滿 3 格、牆、物件、敵人、友軍、地圖邊緣、上坡、下坡、深淵、岩漿、滑進火焰、縱向），每一格都比對事件（`unit_slid` 路徑與原因、`slide` 的 `unit_moved`、倒地在滑行之後、移動點數歸零）＋預覽的停點與滑行路徑＝實走；滑進火焰會燃燒；同一段只擲一次、成功照常走、成功可停在冰上、兩段冰擲兩次、從冰上出發不擲、剩下的路徑作廢、滑過陷阱觸發（定身時停在陷阱格）、被推進冰面檢定但不滑、確定性；預覽的 `immune` 與停點陷阱／表面。
- 新 `tests/engine/test_ai_ice_slide.py`（4）：代價公式、冰面移動分數變低、AI 走乾的路線（兩個方向）、確定性。
- 改：`test_path_preview.py`（冰面表格兩格改成新規則；連續冰面改成窮舉實走「只擲一次、單一停點」）、`test_move_stacking.py`（改成第一格冰上有友軍、下一格是牆的情境，仍滑回空格）、`tests/api/test_path_preview_api.py`（新欄位）。
- 前端：`pathPreview.test.ts`（小牌文字、◆、滑到陷阱／火焰、不會滑倒、滑行格不出小牌、◆ 的畫法）、`walkAnim.test.ts`（踉蹌→滑行→倒下的片段與時間軸、一格沒滑、滑過陷阱、敵方 2 倍速）、`motionClips.test.ts`（滑行姿勢、踉蹌）。

跑過的檢查：`ruff check`、`ruff format --check`、`mypy src`（512 檔）、`lint-imports`（13 kept）；`pytest tests/engine tests/cli tests/sim tests/narrative tests/content tests/api/test_path_preview_api.py tests/api/test_client_fixtures.py -n 8`：7293 通過（第一次跑出 3 個 `LOG_FORMAT.endswith("/111")` 的字面值，已改）；CLI 快照（slow）24 鍵；前端 `tsc`、相關 vitest 9 檔 130 通過、`pnpm build` 通過；`trpg battle --map swamp --seed 7` 與 `--map frozen_lake --seed 7` 的 `--log-json` ＋ `replay` 都通過（冰湖這場有 4 次滑行）。沒跑全量。

## 7. 待 PM 決定

規則類（照最保守／字面的做法先做了）：

1. **從冰上出發**：這次移動起點就在冰上、接著走的冰算同一段，不擲（字面：「走進一段連續冰面的第一格」）。若要「站在冰上開始走也要擲一次」，改 `slide_check_due` 一行。
2. **剩下的點數作廢**＝本回合的移動點數歸零。之後還能用 AP 衝刺（`run` +3 移動）再站起來走；要不要也禁止，需要決定。
3. **衝鋒（`dash`）與跳躍落點進冰**：維持舊規則（每格檢定、失敗倒地、不滑），只有一般走路會滑。
4. **滑行不觸發藉機攻擊與「敵人靠近」類反應**（比照強制位移）；陷阱、表面、源泉、撤離出口照常。
5. **檢定時機**：在那一步的反應、陷阱結算之後才擲；那一步已被陷阱定身／暈眩／推離／擊倒時不擲（舊規則是一進格就擲）。

原型數值與解讀類（照預設做完，PM 確認後順手改）：

6. AI 的 `ice_slip_points` 初值 8；停點的位置損失下限 0。
7. 小牌的停點附註：陷阱寫「（滑到陷阱）」，表面寫「（滑到〈表面名〉）」，只列冰與無以外的表面（水也會寫）；會飛的單位不出冰面小牌（不受地表影響），只有矮人、鱗族寫「不會滑倒」。
8. 預覽的停點在「滑過的陷阱」上照最少後果算（抵抗成功就照常滑過去）；抵抗失敗時實際會停在陷阱格，小牌的 ◆ 在更遠的那格。
9. 動畫時間：踉蹌 220ms、每格滑行 70ms（敵方回合 35ms）、倒下沿用 450ms；`dev/walkGallery` 沒有加滑行的示範。
