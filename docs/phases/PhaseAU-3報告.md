# Phase AU-3 報告：接上戰鬥與探索

實作者，2026-11-04。分支 `worktree-agent-a0b8205a897824fa9`，開工時 `git merge --ff-only 72848d18`（含 AU-2、6H-1、6R-F、RT-2）。
規格：`docs/art/音效與音樂方案.md` 2.1、2.3、4 節；`docs/art/AU-2檢查.md` 的美術 PM 指示；派工六點。

只改了 `client/` 與 `content/audio/sfx.yaml`（加 6 筆環境音、燃燒改成可循環的 3 秒版）。沒有改 Python、API、數值、規則；沒有新增相依；沒有外部素材；沒有 `Math.random`、不讀時鐘決定聲音內容；沒有原生 `title=`。
**`WorldHud.tsx`、`WorldScreen.tsx` 沒有改**：環境音掛在 AU-2 已經掛在 WorldScreen 的 `useWorldSounds` 裡面。`content/llm` 沒碰。

## 做了什麼

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 戰鬥音效掛 6N 時間軸 | `audio/battleSfx.ts`（純函式）：在 `playbackPlan` 裡和 `skillTimeline`／`withSpecials`／`withImpact` 同時算出這一步的音效，跟著播放速度縮放，放在 `Frame.sfx`（跟著 `playVfx`）與 `Frame.viewSfx`（畫面更新那一刻）。`usePlayback` 在 `playVfx` 同一刻交給排程 | e2362a4b |
| | 停頓、最後一擊放慢對齊 | `cueRealMs`：效果時鐘 → 實際時間，加上命中前的停頓、放慢範圍用 6H-1 的 `slowRealMs` 拉長；命中聲在停住那一刻響。測試拿繪製器的 `advanceClock` 逐毫秒模擬比對（誤差 ≤ 2 ms）。減少動態時不停頓、不放慢，聲音也不等 | e2362a4b |
| | 2 倍速不變調 | `audio/sfxScheduler.ts` 的 `CueScheduler`：只提前 120 ms 交給引擎，其餘留在清單裡由計時器補上；按住空白鍵時 `setBoost(2)`，已交給引擎還沒響的取消、照新倍率重排。**不碰 playbackRate** | e2362a4b |
| | 跳過不補放 | 「略過」的播放計畫沒有音效；播放中按跳過 → `cancelAll()`：清單清空，已交給引擎、還沒開始的用新的 `engine.cancelPending("battle")` 斷開 | e2362a4b |
| | 打 5 人不爆音 | 同一刻同一個音效在推導時就合併成一筆（`count`），引擎再照 AU-1 的合併規則略增音量（最多 1.45 倍）；加上每個 id 3 個、總數 16 個的上限與限幅 | e2362a4b |
| 2 | 腳步聲依地表 | `audio/footsteps.ts`：表面（水、油、冰）→ 室內地板（木板、石板，照 6B-ART1 的房間配色）→ 地形（草、石、土；荒原的土＝沙）。戰鬥：`walkCues` 每一格開始踏一步，地表停頓放滑倒、陷阱、冒火。探索：`world/fieldSteps.ts`，`WorldField.tsx` 每走一格呼叫一次 | 90d55c0a |
| 3 | 環境音 | `audio/ambience.ts`：`ambienceFor`（純函式）＋ `AmbienceDirector`（戰鬥優先、結束回到大世界）＋ `audio/loops.ts` 的 `LoopDeck`（循環槽，解鎖後才開始、減少刺耳音效切換時重開）。底聲 6 秒、前端交叉淡化 0.5 秒接成無縫循環（`makeLoopable`）；點綴的間隔照雜湊。地點只讀現有畫面資料 | 90d55c0a |
| 4a | 取消、翻頁、學會一律 `data-sfx` | 24 顆按鈕加上明確的 `data-sfx`（見下方清單），文字判斷只剩退路 | 82bde444 |
| 4b | 戰鬥按鈕 | 點擊音保留；滑過技能列本來就不出聲（全站只有 click 監聽，沒有 hover 音）。「結束回合」加 `data-sfx="ui_confirm"` | 82bde444 |
| 4c | 勝利短樂句 | `EndPanel` 出現且 `winner === "ally"` 時放 `res_victory` | 82bde444 |
| 4d | 燃燒循環全場一條 | `useBurnLoop`：畫面上有任何人燃燒（倒下的不算）就開一條 `status_burn` 循環（音效軌，×0.55），沒有就淡出；一個槽，不會疊 | 90d55c0a |
| 5 | 戰鬥中的 ducking | **沒有接**：戰鬥畫面沒有說書人字幕或對話元件（WorldScreen 在戰鬥時直接換成 BattleScreen，大世界的 `NarratorSubtitle`／`StoryDialog` 不在畫面上）。之後戰鬥加了字幕，在元件裡呼叫 `useDuck(true)` 即可 | — |
| 6 | dev 頁 | `audio-gallery.html` 加「AU-3 戰鬥時間軸試聽」（12 招可選；速度、按住 2 倍速、減少動態、播放整段、跳過）與「AU-3 環境音試聽」（7 個場景） | bfe724ab |
| 追加 | `?mute=1` 強制靜音 | 協調者轉達使用者「測試聲音我會聽到」後加的：任何頁面網址帶 `?mute=1`，主 gain 固定 0、不寫進設定；節點與排程照常，可以用數值驗證。dev 頁狀態欄會顯示「強制靜音」 | fe64f9d1 |

### 其他小改

- `engine.ts`：`play` 多一個 `group` 選項、`cancelPending(group)`、`startLoop(id, opts)`、`setForcedMute`；`voices.ts` 記錄 `at` 與 `group`。
- `sfxLibrary.ts`：音源加 `loop()`；循環與一次性的波形分開快取。
- `skillSequence.ts`：`SkillSegment` 多一個 `seq`（音效的變體鍵要用）。
- `synth.test.ts`：長度上限改成「環境音 6 秒、其他 3 秒」。

## 檔案清單

新增：`client/src/audio/battleSfx.ts`、`sfxScheduler.ts`、`footsteps.ts`、`ambience.ts`、`loops.ts`、`scene.ts`、`au3.test.ts`；`client/src/world/fieldSteps.ts`；`client/src/dev/audioTimeline.tsx`；`docs/art/au3_timeline_final.jpg`、`au3_timeline_sweep.jpg`；本報告。

修改：`client/src/audio/types.ts`、`engine.ts`、`voices.ts`、`index.ts`、`fakeAudio.ts`、`sfxLibrary.ts`、`synth.test.ts`；`client/src/battle/playback.ts`、`skillSequence.ts`；`client/src/screens/battle/usePlayback.ts`、`screens/BattleScreen.tsx`（兩行 hook）；`client/src/ui/EndPanel.tsx`、`TurnControls.tsx`、`BattleTopBar.tsx`；`client/src/world/useWorldSounds.ts`、`WorldField.tsx`；`data-sfx` 的 20 個元件檔；`client/src/dev/audioGallery.tsx`、`client/audio-gallery.html`；`content/audio/sfx.yaml`。

`data-sfx` 清單：
- `ui_cancel`：營火技能照料的兩個「取消」、登入／大世界入口／角色選擇的「返回首頁」、新一輪「返回」、工坊「取消」×3、取消選取、取消施放、取消指令、取消選取（隊友指令）、取消指揮、取消灌注、取消報名、成長面板「取消」、錯誤／通知橫幅與區域圖／大世界圖的 ×、戰鬥頂端的返回鈕、完成獎勵選「跳過」時；
- `ui_page`：聯賽上一頁、下一頁；
- `ui_learn`：任務獎勵「學這招」、閃現「確定」、完成獎勵與升級畫面選了技能時的「確定」（沒選技能時是取消／確認）；
- `ui_confirm`：結束回合。
- **沒加的**：`WorldHud.tsx` 第 474 行的 ×（這個檔不能碰），照舊靠 aria-label／文字退路判斷成取消音。

## 掛點對照表（事件 → 音效 → 時間點）

時間都是效果時鐘（相對 `playVfx`），再由 `cueRealMs` 換成實際時間。

| 類別 | 觸發 | 音效 | 時間點 |
|---|---|---|---|
| 起手 | 技能的起手片段（第一個不是原語的片段） | 近身＝`windup_charge`；法杖／法球／空手／魔導劍的遠程、自身、地面＝`windup_chant`；魔導劍遠程＝`windup_sigil` | 起手片段開始 |
| 起手 | 弓的遠程／地面（普攻也有） | `windup_bow_draw` | 起手片段開始 |
| 起手 | 弩、火槍的遠程／地面（普攻也有） | `windup_reload` | 起手片段開始 |
| 出招 | 近身：劍、刀、斧、鐮、鞭、魔導劍 | `swing_slash` | 出招片段的 hitAt − 60 ms |
| 出招 | 近身：槍 | `swing_thrust` | hitAt − 60 ms |
| 出招 | 近身：拳套、空手、弓弩槍的槍托 | `swing_punch` | hitAt − 60 ms |
| 出招 | 遠程：弓／弩／火槍 | `release_bow`／`release_crossbow`／`release_gun` | 出招片段的 hitAt（放出那一刻） |
| 命中 | 受擊反應 `hit`／`heavy`／`down`，依元素：物理、土＝`hit_blunt`；火、冰、雷、水、毒、聖、暗、風＝`elem_*`（風用霧）；其他＝`hit_magic` | 同左 | 受擊反應的時間（＝命中點） |
| 結果 | 格擋、閃避、倒下、復活（受擊反應） | `res_block`、`res_dodge`、`res_down`、`res_revive` | 命中點 |
| 結果 | 6N-5 特殊結果：暴擊、擊殺 | `res_crit`、`res_kill` | 命中點（停住那一刻） |
| 結果 | Boss 大招（6N-5） | `sys_boss_ult` | 出招開始 |
| 結果 | 我方勝利 | `res_victory` | 結算畫面出現 |
| 原語 | 卡上的部件：治療、護盾、召喚、刻符文、變身、放陷阱 | `prim_heal`、`prim_shield`、`prim_summon`、`prim_rune_carve`、`prim_transform`、`prim_rune_carve` | 那一段的命中點 |
| 原語 | 位移：衝刺／跳躍／傳送、暗影步、交換 | `prim_dash`／`prim_land`／`prim_teleport` | 位移開始；跳躍在落地（位移結束） |
| 原語 | 符文引爆（blasts） | `prim_rune_burst` | 引爆的時間 |
| 狀態 | `status_applied`：冰凍、中毒、暈眩、帶電 | `status_freeze`、`status_poison`、`status_stun`、`status_shock` | 目標的受擊時間 |
| 狀態 | 燃燒（畫面上有人在燒） | `status_burn` 循環，全場一條 | 持續 |
| 地表 | `surface_changed`（`cause: effect`）出現火、冰、水、油、毒、聖、暗、煙 | `elem_*` | 命中點 |
| 地表 | `surface_changed` 其他原因變成火（蔓延） | `surface_fire_spread` | 命中點 |
| 地表 | 走路時的地表停頓：踉蹌／滑倒、陷阱、冒火、油 | `surface_slip`、`surface_trap`、`elem_fire`、`elem_water` | 停頓開始 |
| 爆炸 | `object_exploded`、`bomb_exploded`、符文引爆的 impact | `explosion` | 命中點 |
| 腳步 | 走路的每一格 | `step_*`（依地表） | 每一格開始 |
| 系統 | `round_started` | `sys_round_start` | 畫面更新 |
| 系統 | Boss 的 `followup_charged` | `sys_boss_warn` | 畫面更新 |
| 系統 | AI 行動完、輪回我方 | `sys_my_turn` | 播放結束 |

變體鍵：出招類用 `skillVariant.key`／`battleVariantKey`／`skillVariantKey`，受擊類用 `reactVariantKey`，和動畫同一把；腳步用「地圖:x,y:第幾步」。

## 環境音對照表

| 地點 | 底聲（循環，環境軌） | 點綴 |
|---|---|---|
| 雲嶺室外 | 風 `amb_wind` | — |
| 荒原室外 | 熱風 `amb_wind_hot`＋火 `amb_fire` ×0.5 | — |
| 霜潮室外（之後） | 風 | — |
| 主城室外 | — | 遠處鐘聲 `amb_bell`，約每 24±6 秒 |
| 室外街上有鐵匠鋪 | — | 打鐵 `amb_forge`（遠），約每 7±2 秒 |
| 戰場有岩漿 | 火 ×0.5 | — |
| 雨天（室外） | ＋雨 `amb_rain` | ＋遠雷 `amb_thunder`，約每 22±8 秒 |
| 室內：鐵匠鋪、附魔台 | 爐火 ×0.8 | 打鐵，約每 3.6±0.9 秒 |
| 室內：酒館 | 爐火 ×0.55 | — |
| 室內：其他（導師殿、一般屋子） | 安靜 | — |

- 資料來源：大世界＝`view.field` 的 `region`、`interior`、`facilities`，加上 `clock.weather_zh` 含「雨」；戰鬥＝`BattleView.region`、`weather_id === "rain"`、有沒有 `lava` 地形。沒有新增伺服器欄位。
- 減少刺耳音效開啟時，`harsh` 的遠雷、打鐵不出聲（引擎擋）；底聲照常。

## 測試

- 新增 `src/audio/au3.test.ts` 共 29 項：
  - 時間點對齊：近身咻＝hitAt − 60、命中＝hitAt；起手；弓；起手音對照；停頓與放慢和 `advanceClock` 一致；快速播放縮放；
  - 跳過時不放音；
  - 2 倍速時排程減半、playbackRate 都是 1，中途加速重排；
  - 同一個鍵同一個變體；
  - 打 5 人合併、不超過上限；
  - 腳步依地表、戰鬥走路的時間；
  - 環境音依區域、天氣、室內挑選；導演的優先順序；
  - 減少刺耳音效時 `harsh` 不放；
  - `?mute=1`；循環槽、燃燒、接縫連續；事件 → 音效。
- 交件前跑一次 client 全部 vitest：**223 個檔案、2450 項，2448 過、2 項逾時**（`cleanup6rf.test.ts` 掃整個原始碼、`inkCreature.test.ts` 全組合自測，都超過 5 秒）。這兩個檔單獨用 `--testTimeout 60000` 重跑：22 項全過，4.6 秒。兩個檔和這段無關，逾時是因為機器負載。
- `corepack pnpm -C client build`：結束碼 0。
- Python `tests/content/test_audio_sfx.py`：19 passed（新的 6 筆環境音通過 schema）。

## 實機

- 自己的伺服器：vite 5381（5377 已被別的程序占用）、後端 8377（`TRPG_SAVE_DIR` 在 scratchpad），沒碰 `saves/`、`tmp_x`。自己的無頭 Chrome（CDP 9381，自己的設定檔）。全部用 TaskStop 和自己的 PID 結束。
- 驗證方式：在無頭 Chrome 注入一段只記錄 `AudioBufferSourceNode.start` 的腳本（不改遊戲程式），看時間、長度、loop 與 playbackRate：
  - 實戰（一鍵開局，雲海吊橋）：風的循環 1 條（5.5 秒）、回合開始鐘、揮砍、命中、石地腳步都有排上；提前量 0～120 ms；**playbackRate 全部是 1**；沒有錯誤；
  - 大世界（霧渡鎮）：風的循環 1 條；走路每格一聲石地腳步。
- **聲音外洩**：前半段實測用的無頭 Chrome 沒有加 `--mute-audio`，使用者聽到了測試聲音。收到通知後立刻用自己的 PID 停掉，之後改成 `--mute-audio` 加網址 `?mute=1` 重開，截圖時已經不出聲。
- 截圖（`?mute=1`）：
  - `docs/art/au3_timeline_final.jpg`：最後一擊，可以看到停頓、放慢範圍，以及效果時鐘和實際時間的對照；
  - `docs/art/au3_timeline_sweep.jpg`：橫掃 5 人，鈍擊 ×5 合併，按住 2 倍速；環境音試聽「雲嶺下雨」。
- 我手誤在 `F:/tmp_au3_edit.cjs` 建了一個空檔（0 bytes）。刪除指令被安全檢查擋下，請使用者自己刪。

## noqa

沒有新增（前端沒有 ruff）。

## 待 PM 決定（都已照最保守的做法做完）

1. **6H-1 的 `impacts` 沒有跟著技能時間軸移動（找到的既有問題，沒有修）**：`skillSequence.retime` 會移動 casts、hits、reactions、blasts，但沒有移動 `impacts`。所以有技能時間軸時，分級停頓與重擊微震落在「還沒對齊的命中點」，比受擊早。例如試聽頁的劍：停頓在 270 ms，命中在 396 ms。聲音照實際的停頓排，所以和畫面一致，但畫面本身的停頓早了。建議排一小段修 `retime`（把 `impacts` 照 `shift` 移），屬於動畫範圍。
2. **直線、錐形這類近身技能**：咻照出招片段的 hitAt − 60；命中照特效真的打到的時間（光束飛過去），所以兩者會差超過 60 ms（試聽頁橫掃：336 和 546）。我照「命中聲跟著畫面」做。
3. **近身普攻沒有起手音**：只有咻＋命中，免得每下普攻都嗡一聲；遠程武器的拉弓、上膛普攻照放。
4. **擊殺同時放 `res_kill` 和 `res_down`**：擊殺是低頻落下，倒下是悶響，同一刻疊兩聲。要不要只留一個？
5. **勝利短樂句放在結算畫面出現時**，不在 6N-5 的勝利動畫開始時；略過播放時結算畫面照樣會放（它屬於結算畫面，不是補放）。
6. **打鐵標成 `harsh`**：金屬聲偏尖，所以減少刺耳音效開啟時不出聲，只剩爐火。
7. **室內聽不到雨**；主城室外沒有風，只有鐘聲。
8. **燃燒循環音量 ×0.55**，放在音效軌（會被減少刺耳音效改成柔和版）。`status_burn` 改成 3 秒、不衰減的版本，不再當一次性音效使用。
9. **環境音的數值都是原型**：鐘每 24±6 秒、打鐵每 3.6±0.9 秒（街上 7±2）、遠雷每 22±8 秒；底聲音量 0.5～1。
10. **輪到我方的提示音**：條件是「這次回應開始時不是主角、結束時輪到主角」，主角自己行動後不會響。
11. **`?mute=1`** 對所有頁面都有效（正式遊戲也可以用），不寫進設定、不存檔。之後的預覽、截圖、自動化驗證請一律加上，無頭 Chrome 加 `--mute-audio`。
12. **戰鬥中的 ducking 沒有接**（理由見上方第 5 項）。音樂軌第一階段也沒有音源。
