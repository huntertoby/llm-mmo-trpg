# Phase 6 實機巡檢

> 2026-11-04，實機巡檢員（agent）。只新增截圖和這份報告，沒有改程式或內容檔。
> 截圖都在 `docs/art/tour_*.jpg`，視窗 1280×800。

## 0. 環境與做法

- **版本**：前半段在 `80d674c1` 上走（建角、霧渡鎮、雲嶺、一般戰、冰面與陷阱、復活、大世界圖、主城、聖光爆發 3 次）。
  中途發現 6N-8 技能變體還沒進 `80d674c1`，就把 worktree `--ff-only` 到 main `70a6268d`（含 6N-8、6R-P、AU-1），重 build 後走後半段：火焰箭 3 次、灰燼荒原、roguelite、戰鬥「版面」設定面板。下面每張截圖都標了版本（舊＝`80d674c1`、新＝`70a6268d`）。
- **伺服器**：自己起的 `uv run trpg serve`，埠 8388（主要）和 8389（荒原用）。
  - 存檔放 scratchpad：`…/scratchpad/tour/saves`、`saves2`。
  - `TRPG_DEV_ROUTES=1`，`TRPG_LLM_GENERATE=false`。
  - `TRPG_LLM_BASE_URL` 指向不存在的 `127.0.0.1:9`，不碰 8001。
- **瀏覽器**：自己啟的無頭 Chrome，CDP 9388，用 GPU（ANGLE D3D11，RTX 5090）。
  - 內建瀏覽器只借了一個已經沒有伺服器的舊分頁，因為分頁數到上限。
  - 結束時大小已還原成 desktop；那個分頁原本就不是我開的，所以沒有關。
- **加速方式**（畫面一律是正式遊戲）：
  - 移動：腳本用正式的 `walk` 動作走路，避開敵人視野，再重新載入正式畫面；城鎮內、遇敵、互動都是真的點擊和按鍵。
  - 冰湖陷阱戰、復活與聖光爆發、火焰箭 3 次：走開始畫面的正式「開始戰鬥」流程，只把送出的 `POST /api/battles` 換成開發用欄位 `hero_build`（`build_trapper`、`build_healer`、`build_fire`）。
  - roguelite：用 `dev-advance` 讓 AI 代打。
- **結束**：伺服器、Chrome、CDP 程序都用自己的 PID 結束。`saves/`、`tmp_x` 都沒碰。

## 1. 路線逐段

| 段 | 截圖 | 觀察 |
|---|---|---|
| 1 建角 | `tour_01_create_top.jpg`、`tour_01_create.jpg`（舊） | 種族、出身、武器、關鍵字、起始技能卡都正常。**武器列有兩顆「弓 遠程」**（bug 1）。 |
| 2 霧渡鎮 | `tour_02_mist_ferry.jpg`、`tour_02_mist_ferry_idle60.jpg`（待機 60 秒後）、`tour_02_smithy.jpg`（舊） | 雨天、燈籠、NPC 頭上的「！」都正常。待機 60 秒，主控台沒有錯誤。 |
| 2 NPC 職業動作 | `tour_02_npc_smith_work.jpg`（舊） | **補到**：石記鐵鋪的石師傅轉側面，對鐵砧搥打。約 45 張連拍中有 3 張是側面，比例符合「偶爾做一次」。 |
| 3 雲嶺 | `tour_03_cloud_ridge.jpg`（渡口石階）、`tour_03_hunter_hut.jpg`、`tour_03_crystal_rift.jpg`（舊／新） | 敵群視野、巡邏、營火都正常。**重新載入後主角常被底部快捷列蓋住**（bug 3）。 |
| 4 一般戰 | `tour_04_battle_start.jpg`、`tour_04_fist_attack.jpg`、`tour_04_battle_end.jpg`（舊） | 遇敵卡 → 就地開打 → 12 輪全滅勝利。 |
| 4 空手攻擊 | `tour_04_fist_attack.jpg`（舊） | **補到**：拳套普攻，主角朝右揮出黃色弧光，對手頭上冒「閃避」。 |
| 4 勝利 | `tour_04_battle_end.jpg`（舊） | 勝利面板對玩家顯示 `uv run trpg battle replay` 開發說明（bug 7）。 |
| 5 冰面與陷阱 | `tour_05_winter_lake.jpg`、`tour_05_ice_battle_start.jpg`、`tour_05_ice_battle.jpg`、`tour_05_ice_defeat.jpg`、`tour_05_after_defeat.jpg`（舊） | 在冬湖碰到 Lv4 冰鶴使群，就地開打。Lv1 打不過，被抬回霧渡鎮並帶「疲憊」，這段流程正常。 |
| 5 冰面滑倒 | `tour_05_ice_slip_1_enter.jpg` → `tour_05_ice_slip_2_slide.jpg` → `tour_05_ice_slip_3_down.jpg`，另有 `tour_05_ice_slip_fall.jpg`（舊） | **補到「先滑再倒」**：標準隊友（弓手）踏上冰面，一路滑 3 格帶冰屑，最後倒地並冒「＋倒地」。 |
| 5 陷阱夾住 | `tour_05_trap_clamp.jpg`、`tour_05_trap_kill.jpg`（舊） | **補到**：盜賊1 踩中 (4,3) 的捕獸夾，鐵夾合在腳下，接著扣血、白閃、擊倒。 |
| 6 Boss 戰 | `tour_06_boss_map_refused.jpg`、`tour_06_run_map.jpg`、`tour_06_campfire.jpg`（新） | **沒拍到**，原因見第 4 節。 |
| 6 復活 | `tour_06_revive_a.jpg`、`tour_06_revive_b.jpg`（舊） | **補到**：開闊平原，治療英雄對倒地的標準隊友（弓手）放返魂術。人物從倒地站起，冒「復活」，腳下有綠光。 |
| 7 大世界圖 | `tour_07_world_map.jpg`、`tour_07_world_map_float_b.jpg`、`tour_07_world_map_hover.jpg`（舊） | 彩繪浮島、吊橋、雲、鎖頭都正常。 |
| 7 浮島漂浮 | `tour_07_island_float_a.jpg`、`tour_07_island_float_b.jpg`（舊） | **補到**：同一塊雲嶺島，相隔約 1.8 秒的裁切，島身上下差約 5 px。名牌不跟著飄，請美術 PM 確認是不是刻意的。 |
| 7 點島進區域圖 | `tour_07_world_map_hover.jpg` → `tour_07_island_to_region.jpg`；區域圖本身是 `tour_07_region_map.jpg`（舊） | **補到**：滑過雲嶺島會亮起並出現說明；點下去進雲嶺區域圖，迷霧和傳送石都正常。 |
| 8 灰燼荒原 | `tour_08_ashen_waste.jpg`（灰渡口）、`tour_08_ember_market.jpg`、`tour_08_ashen_region_map.jpg`、`tour_08_world_map_ashen_lit.jpg`、`tour_08_island_click_ashen.jpg`（新） | 要等世界事件 #1 結束才能過渡口（見第 4 節），所以另開一個 `TRPG_SEASON_START=2026-10-25` 的世界。荒原大世界圖會亮。 |
| 9 主城 | `tour_09_capital.jpg`、`tour_09_capital_tavern.jpg`（舊） | 從大世界圖「傳送到樞島」。廣場和酒館都沒有 NPC（bug 12）。 |
| 技能 3 次 | 見第 6 節 | 同一招連放 3 次。 |

## 2. Bug 清單

嚴重度：高＝擋流程或明顯錯誤；中＝玩家看得出的錯；低＝小瑕疵或待確認。

| # | 嚴重度 | 位置 | 重現步驟 | 現象 | 截圖 |
|---|---|---|---|---|---|
| 1 | 中 | 開始畫面、建角、開新一輪的「起始武器」 | 打開任一開局畫面 | 有兩顆「弓 遠程」。第二顆應該是敵人專用的 `bow_guard`（`content/weapons.yaml` 註明「只有 bandit_archer_guard 使用」），玩家選得到。 | `tour_ui_01_opening.jpg` |
| 2 | 中 | 渡口石階打完一群 | 建角 → 渡口石階 → 打贏「盜賊盾衛」那群 | 提示「渡口石階已清空」，區域圖也打勾「已清空」，但精英群「搶渡船的盜賊」還站在地圖上。 | `tour_07_region_map.jpg`、當時的畫面 |
| 3 | 中 | 大世界野外與城鎮，重新載入或剛進圖時 | 在獵戶小屋、冬湖重新整理 | 鏡頭沒有把主角放進可見區：主角在畫面最下面，被快捷列蓋住（快捷列變半透明）。右側「任務」面板也會蓋到出口格和敵人。 | `tour_03_hunter_hut.jpg`、`tour_05_winter_lake.jpg`、`tour_02_mist_ferry.jpg`（右側出口） |
| 4 | 中 | 天氣欄（右上第二顆） | 雲嶺晚上 | 天氣顯示「夜」。伺服器 `weather_zh` 也是「夜晚」，遇敵卡寫成「夜晚・夜晚」。早上 05:12 時時段欄顯示「早」，伺服器 `day_phase` 卻是 night，兩邊不一致。 | `tour_ui_18_popup_encounter.jpg`、`tour_05_winter_lake.jpg` |
| 5 | 中 | 大世界圖「你在哪裡」 | 荒原世界站在灰渡口時打開大世界圖 | 島下的名牌寫「你在餘燼集」，實際在灰渡口，看起來是固定寫該區的城鎮。 | `tour_08_world_map_ashen_lit.jpg` |
| 6 | 中 | 彈出面板位置（背包、技能、NPC 面板） | 按 I、K，或和 NPC 說話 | 面板左上角蓋住左上 HUD 的血條和法力條。 | `tour_ui_13_bag.jpg`、`tour_ui_14_skills_panel.jpg`、`tour_ui_16_event_dialog.jpg` |
| 7 | 低 | 大世界戰鬥勝利面板 | 任一場大世界戰鬥打贏 | 面板對玩家顯示「紀錄可用 uv run trpg battle replay 檔案 重播驗證」，這是開發用說明。 | `tour_04_battle_end.jpg` |
| 8 | 低 | 浮動字重疊 | 一步內有多個結果（暴擊＋擊倒＋倒地；回血＋閃避） | 字疊在一起，例如「擊倒／暴擊 −9／倒地！」三行壓在一起、「＋11 盾」和「閃避」重疊，讀不清。 | `tour_05_trap_clamp.jpg`、`tour_skill3x_firebolt_compare.jpg` |
| 9 | 低 | 戰鬥紀錄與浮動字用語不一致 | 拳套普攻打不中 | 浮動字是「閃避」，紀錄寫「→ 失手」或「自然 1，失手」。 | `tour_04_fist_attack.jpg` |
| 10 | 低 | 戰鬥重新載入 | 戰鬥中重新整理後按「繼續戰鬥」 | 已經第 2 輪以上，仍跳出「敵方先手：第 1 輪敵人全部先動…」提示。 | 巡檢當時的畫面（第 3 輪） |
| 11 | 低 | 技能列文字截斷與跳位 | 6 招以上的 build（陷阱流、治療） | 「AP 2・法力 6・冷卻 3 …」被截斷。技能進入冷卻時按鈕變窄，後面的按鈕往前跳。 | `tour_05_trap_clamp.jpg` |
| 12 | 低／待確認 | 主城樞島 | 傳送到樞島，進樞島酒館 | 廣場和酒館都沒有 NPC。酒館小地圖有一個橘點，畫面上沒有人。 | `tour_09_capital.jpg`、`tour_09_capital_tavern.jpg` |
| 13 | 低／待確認 | 範圍技畫到地圖外 | 聖光爆發的目標在地圖邊緣 | 光柱畫在地圖外的深色邊和頂列 HUD 下方。 | `tour_skill3x_2.jpg`（左上） |
| 14 | 低／待確認 | 倒地的敵人也有綠色「可復活」愛心 | 敵人倒地後 | 敵方屍體頭上也有綠色＋愛心，玩家可能以為能救。 | `tour_04_battle_end.jpg`、`tour_06_revive_b.jpg` |
| 15 | 低 | 「設定」齒輪 | 大世界右上齒輪 | 新舊版都只顯示「設定：尚未開放」。新版的聲音設定只在戰鬥「版面」面板裡（AU-1 待決 1）。 | `tour_ui_11_settings_locked.jpg`、`tour_ui_12_settings_battle_panel.jpg` |
| 16 | 低 | 鐵匠舖 | 走到石師傅旁邊 | 主角走到鐵砧下一格時，頭被鐵砧圖蓋住（前後遮擋）。按 E 只開對話，沒有打造面板。 | `tour_ui_17_popup_npc_panel.jpg` |
| 17 | 低／內容 | 餘燼集鐵娘的傳聞 | 荒原和鐵娘說話 | 傳聞寫「斷崖幫的運輸隊…」，斷崖幫是雲嶺的幫派。 | `tour_ui_16_event_dialog.jpg` |
| 18 | 低 | 大世界圖說明框 | 滑過荒原島 | 「點了看區域圖」斷成「點了看區／域圖」。 | `tour_08_world_map_ashen_lit.jpg` |

- **主控台**：整趟只有兩種訊息，沒有 JS 例外，也沒有 React 錯誤：
  - `favicon.ico` 404；
  - 巡檢員自己用單場戰鬥請求 Boss 地圖時的 422。
- **伺服器 log**：沒有 Traceback 或 ERROR。
- **彈出卡（6.5.1）**：格子資訊卡、技能卡、設定說明卡都用共用浮動卡（釘住時圖釘變金色，資訊卡可停到右側）。沒看到違規的原生 `title` 或自製彈出層。

## 3. FPS 和延遲

- 環境：無頭 Chrome 156，GPU 是 ANGLE D3D11 / RTX 5090，1280×800。玩家電腦的數字會比這裡低。
- 量法：`requestAnimationFrame` 連量 5 秒。

| 場景 | 平均 FPS | 最低（1 秒窗格） | 最長一格 |
|---|---|---|---|
| 霧渡鎮（城鎮，雨） | 59.9 | 60 | 16.8 ms |
| 雲嶺野外（源晶裂痕，雨） | 59.9 | 60 | 16.9 ms |
| 大世界圖（浮島漂浮中） | 59.9 | 59 | 16.9 ms |
| 主城樞島 | 60.0 | 60 | 16.9 ms |
| 灰燼荒原・灰渡口（霧） | 59.9 | 59 | 16.9 ms |
| 灰燼荒原・餘燼集 | 59.9 | 59 | 17.0 ms |
| 戰鬥待機（冰湖） | 59.9 | 60 | 17.1 ms |
| 戰鬥中，敵方回合播放（冰湖） | 59.9 | 60 | 16.8 ms |

**最低的場景**是大世界圖、灰渡口、餘燼集，三個並列，最低都是 59。全部都在 60 fps 附近，看不出卡頓。

**戰鬥每步延遲**（從送出動作到又能下指令，含輪詢誤差約 30 ms，播放速度「正常」）：

| 動作 | 延遲 |
|---|---|
| 主角拳套普攻（命中、格擋各一次） | 636 ms、543～655 ms（4 次） |
| 主角普攻（失手、移動一併） | 347～1144 ms |
| 結束回合 → 我方、敵方 5 人行動完 → 再輪到主角 | 9.1 s |
| 同上，`?anim=0.25` | 21.4 s |

**城鎮待機**：霧渡鎮放 60 秒，主控台沒有新的錯誤，JS heap 約 17 MB。

## 4. 拍不到的項目和原因

1. **Boss 戰、Boss 大招（四周變暗）**：都沒拍到。
   - **大世界 Boss**：雲頂觀「霧鎖真人」。腳本一路走到源晶裂痕的山門 (20,1)，出口被擋：「霧太濃，還過不去。主線：先查清源晶裂痕」（`tour_03_crystal_rift.jpg` 的霧牆）。要推進主線才開，沒有開發欄位能跳過。荒原的熔心之主一樣要等主線。
   - **單場戰鬥**：開始畫面不能選 Boss 地圖。換成 `cloud_summit` 會回 422「未知的地圖」（`tour_06_boss_map_refused.jpg`）。
   - **roguelite 的 Boss**：用 `dev-advance` 讓 AI 代打。第一輪在前 3 場就全滅；第二輪（`dev_bulwark`）到第一個營火（`tour_06_campfire.jpg`），之後第 4 場又全滅，到不了 Boss。另外 roguelite 的頭目 `bandit_warlord` 只有 `skill_cleave`、`skill_gale_kick`，沒有蓄力招。6N-5 的「Boss＋蓄力」條件本來就不會觸發，所以就算打到 Boss 也拍不到大招。
   - **要補拍的話**：
     - 給 PM 一個推進主線旗標的開發欄位；
     - 或讓單場戰鬥在 dev 模式可選 Boss 地圖。
2. **事件卡（地圖上的「！」事件）**：雲嶺、荒原走過的地圖剛好都沒有抽到事件點（`event_mark` 都是 null）。改拍 NPC 對話面板（頭像、傳聞、可接任務）當作事件與對話類的彈窗（`tour_ui_16_event_dialog.jpg`、`tour_ui_22_npc_quests.jpg`）。
3. **6N-8 技能變體「看出三次不一樣」**：拍了，但在實戰的畫面大小下看不太出差別，見第 6 節。

## 5. 一致性巡檢截圖清單（tour_ui_）

| 順序 | 內容 | 檔案（沿用的寫對應檔名） |
|---|---|---|
| 1 | 開場 | `tour_ui_01_opening.jpg`（舊） |
| 2 | 建角 | 沿用 `tour_01_create.jpg`、`tour_01_create_top.jpg` |
| 3 | 霧渡鎮 | 沿用 `tour_02_mist_ferry.jpg` |
| 4 | 雲嶺野外 | 沿用 `tour_03_cloud_ridge.jpg`、`tour_03_hunter_hut.jpg` |
| 5 | 一般戰鬥 | 沿用 `tour_04_battle_start.jpg`、`tour_04_battle_end.jpg` |
| 6 | Boss 戰 | 沒拍到（第 4 節）；roguelite 路線圖 `tour_06_run_map.jpg`、營火 `tour_06_campfire.jpg` |
| 7 | 大世界圖 | 沿用 `tour_07_world_map.jpg`、`tour_08_world_map_ashen_lit.jpg` |
| 8 | 區域圖 | 沿用 `tour_07_region_map.jpg`、`tour_08_ashen_region_map.jpg` |
| 9 | 荒原 | 沿用 `tour_08_ashen_waste.jpg`、`tour_08_ember_market.jpg` |
| 10 | 主城 | 沿用 `tour_09_capital.jpg`、`tour_09_capital_tavern.jpg` |
| 11 | 設定（大世界齒輪） | `tour_ui_11_settings_locked.jpg`（舊，「尚未開放」） |
| 12 | 設定（戰鬥版面＋聲音） | `tour_ui_12_settings_battle_panel.jpg`（新） |
| 13 | 背包 | `tour_ui_13_bag.jpg`（舊） |
| 14 | 技能面板（K） | `tour_ui_14_skills_panel.jpg`（舊） |
| 15 | 技能卡（戰鬥中滑過） | `tour_ui_15_skillcard.jpg`（舊） |
| 16 | 事件與對話卡 | `tour_ui_16_event_dialog.jpg`（新） |
| 17 | 彈窗：NPC 面板 | `tour_ui_17_popup_npc_panel.jpg`（舊） |
| 18 | 彈窗：遇敵卡 | `tour_ui_18_popup_encounter.jpg`、`tour_ui_23_encounter_lake.jpg`（舊） |
| 19 | 彈窗：格子資訊卡 | `tour_ui_19_tilecard.jpg`（舊） |
| 20 | 角色列表 | `tour_ui_20_character_list.jpg`（新） |
| 21 | roguelite 開新一輪 | `tour_ui_21_run_new.jpg`（新） |
| 22 | NPC 可接任務 | `tour_ui_22_npc_quests.jpg`（新） |

## 6. 同一招連放 3 次（tour_skill3x_）

| 組 | 版本 | 檔案 | 說明 |
|---|---|---|---|
| A 聖光爆發 | 舊（還沒有 6N-8） | `tour_skill3x_1.jpg`、`tour_skill3x_2.jpg`、`tour_skill3x_3.jpg`、`tour_skill3x_compare.jpg` | 同一場戰鬥第 1、5、8 輪各放一次（冷卻 3）。三次一樣，符合舊版沒有變體。只當對照。 |
| B 火焰箭 | 新（6N-8） | `tour_skill3x_firebolt_1.jpg`、`_2.jpg`、`_3.jpg`、`tour_skill3x_firebolt_compare.jpg` | 同一回合連放 3 次（AP 1、沒有冷卻），播放速度「慢」，每 50 ms 一張。對比圖是三次各取出招後第 9～14 張（3 列 × 5 欄）。 |

**觀察**：

- 第 1、2 次的起手弧光方向和亮點位置略有不同；第 3 次多了「＋燃燒」。
- 但目標就在隔壁格，飛行距離只有 1 格，又是實戰的格子大小，**三次的軌跡和爆發在截圖上幾乎分不出來**。
- 起手（詠唱）在出招前約 100 ms 就結束，50 ms 連拍只抓到 1～2 張。
- 開始畫面的隨機「火球」（AP 2，沒有冷卻）也試過，但目標一直在射程外，只放成一次，所以改用 `build_fire` 的火焰箭。

**建議**：

- 補一組「目標相距 4～5 格、播放速度極慢、放大 150%」的實戰截圖；
- 或在 dev 頁 `#skillvar` 上，用和實戰同一套串接器的放大圖對照。

## 7. 給 PM 的待決

1. 第 2 節的 bug 1～6 是玩家看得出的問題，建議排一小段修。bug 4（天氣顯示「夜」）和 bug 2（已清空的判斷）要先確認是規則還是顯示的問題。
2. Boss 大招和大世界 Boss 戰要另外想補拍的方法（第 4 節第 1 點）。
3. 6N-8 的技能變體在實戰的可讀性要再看一次（第 6 節）。
