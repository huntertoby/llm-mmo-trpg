# Phase OCL-1c 報告｜被遮擋外框：美術定案兩項小修＋實機補拍

> 實作 agent（Opus 5.5），2026-11-12。依據 `docs/art/OCL-1驗收.md`（第 2、3 節定案、第 4 節 R1～R9）、`docs/phases/PhaseOCL-1b報告.md`。
> 基準：本機 main（含 `1e987c86`）ff 進 worktree 後的 `5499d9be`。後端、`content/`、API 沒動。

## 1. 改動

| 項目 | 內容 | commit |
|---|---|---|
| 1b 待決 4（旋轉） | `render/battle/occlusionLayer.ts`：新常數 `OUTLINE_MAX_ROTATION = 0.35`；`tickOutlines` 每格把外框 `rotation` 設成身體節點的 `rotation`（外框與身體同一個錨點：腳底，`anchor (0.5, foot/h)`），`abs(rotation) > 0.35` 才藏。倒下（`hideOutline`）、移動中照舊藏。 | `49825619` |
| 1b 待決 3（異形重擊峰值） | `render/reactClips.ts`：新常數 `CREATURE_HEAVY_FLASH`＝`quantizeCreaturePose({ flash: min(1, 0.9 × 1.1) }).flash`（＝1.0，照實際片段量化後的值算，不寫死）；`creatureReactFlashPeak("heavy")` 回它。 | `49825619` |
| 需求文件 | `docs/art/被遮擋剪影外框-移植需求.md` 第 33 行表格：「異形重擊 0.99」→「1.0（照實際片段量化後的值；OCL-1c 依美術驗收 `OCL-1驗收.md` 第 3 節，原寫 0.99）」，只改這一格。 | `49825619` |
| 截圖 | `docs/art/shots/ocl1/1c-*.jpg` 8 張 | `5cd395f7` |
| 報告、上手筆記 | 本檔；`docs/dev/上手-前端戰鬥畫面與動畫.md` 第二節「受擊閃白 k」改 1.0、「播放」改「跟著轉」，第四節加第 62 點 | 最後一個 commit |

其他行為不變（`occlusionUnits` 的 `tilted` 判定、片段中沿用、移動、閃白 k 的算法都沒動）。

## 2. 改到的既有測試（`client/src/render/ocl1Playback.test.ts`，逐項）

| # | 舊 | 新 | 為什麼 |
|---|---|---|---|
| 1 | 「身體有旋轉（空翻、倒下、側彎）：藏起來」：`rotation 0.3` → 藏；0 → 出現 | 「身體轉 10°（受擊側彎）外框看得到、跟著轉；轉 0.5 rad 藏；轉回 0 再出現」：±10°（0.1745）→ 可見且外框 `rotation` 相同；`OUTLINE_MAX_ROTATION` ＝ 0.35；0.5 → 藏；0 → 可見、`rotation` 0 | 驗收第 2 節定案（外框跟著轉，> 0.35 rad 才藏）；舊測試的 0.3 現在是「看得到」 |
| 2 | 第 11 項 ROWS「異形反應 heavy」容許差 0.0101（峰值 0.99、實際 1.0） | 容許差 0（完全相等） | 驗收第 3 節定案（峰值照實際） |
| 3 | ROWS 上方註解寫「照需求表傳 0.99…k 夾在 1」 | 改寫成 OCL-1c 照實際 1.0、完全相等 | 同上 |
| 4 | 「峰值表」`creatureReactFlashPeak("heavy")` `toBeCloseTo(0.99, 9)` | `toBe(1)`（標題的 0.99 改 1.0） | 同上 |
| 5 | reactEffects「異形受擊：峰值 0.9、重擊 0.99」 | 「重擊 1.0（OCL-1c）」，期望值 `1` | 同上（假 `ReactHost` 收到的峰值） |

沒有整批重產任何快照；雜湊快照（`creaturePose`、`inkDollSnapshot`、`__snapshots__`）沒變。

## 3. 結束碼

在 `5cd395f7`（程式最後一個 commit 之後只有文件與截圖）各跑一次：

- `corepack pnpm -C client typecheck` → **0**
- `corepack pnpm -C client test` → **0**（308 檔、3976 項全過）
- `corepack pnpm -C client build` → **0**（只有既有的 chunk 大小警告）
- 相關 vitest（`ocl1Playback`、`ocl1Outline`、`reactClips`、`bodyAnim`、`reducedMotion`）→ **0**（5 檔、110 項）

## 4. 實機補拍（R1～R9）

**怎麼打到這些擺位**：自己的 `uv run trpg serve --port 8170`（`TRPG_DEV_ROUTES=1`、存檔在 scratchpad）＋無頭 Chrome（`--mute-audio`、網址 `?dev=1&mute=1&anim=0.1`）。頭目地圖只有「工坊試玩」（帶自訂技能）才開得了，所以佈局用正式 API：`POST /api/battles {map_id: molten_heart_pit／rift_gate, seed: 1, hero_build: build_charger, custom_skills: [內建 skill_bull_rush 換 id], replace_skills: [skill_bull_rush]}`（標準隊友 AI），腳本照 BFS 走主角（`move`）＋`end_turn`，停在要拍的那一刻。頁面從開發選單「單場戰鬥 → 開始戰鬥」進，用 CDP `Fetch` 把那一次 `POST /api/battles` 的回應換成這場已佈好局的 `GET /api/battles/{id}`；**之後的動作（結束回合、點格子走路）都是頁面自己送到真伺服器、照正式 `playbackPlan` 播**。種子固定，所以同一個佈局可以重開好幾次（每次一場新戰鬥）。截圖是連拍（每 50～90 ms 一張），合圖在無頭 Chrome 的 canvas 裡裁切放大、jpg 0.8。時間標示＝牆鐘 ÷ 10（`anim=0.1`）＝遊戲內毫秒，誤差約 ±5 ms。

| # | 檔案（`F:/PythonProject/LLM-MMO-TRPG/docs/art/shots/ocl1/`） | 實機／開發頁 | 看到的 |
|---|---|---|---|
| R1 | `1c-r1-ah-north-live.jpg` | **實機**（熔心坑第 3 輪；主角走到灰燼之心正北 (5,4)，結束回合後熔岩濺落落在主角身上） | 同一回合移動前 (4,6) 沒被擋的主角；命中前淡藍外框（帶黑邊）；+0、+30、+94 白；+150 回淡藍並跟著身體側彎；頭目整回合結束後淡藍。外框頂端的兩個凸起：左邊是頭、右邊高起的一塊和沒被擋時主角舉起的手臂（持劍那隻手的位置）對得上，**不是耳朵**；但遊戲端外框不含武器，所以只看得到手、沒有劍。注意：命中那一刻熔岩濺落有全畫面的亮閃，+0～+94 的外框「白」和全畫面變亮疊在一起。 |
| R2 | `1c-r2-lord-north-live.jpg` | **實機**（裂界門第 2 輪；碎晶之主 (6,4) 在主角 (6,3) 正南） | 淡紫晶胸口上看得到主角的外框（淡藍偏灰＋黑邊），黑邊比色線醒目，同驗收第 1 節所述；施放火花連鎖時外框沿用。 |
| R3 | `1c-r3-enemy-behind-core-live.jpg` | **實機**（同 R1 的佈局但主角站 (5,3)；第 2 階段殼裂爬出的餘燼蜥直接落在 (5,4)） | 敵方的粉紅外框（帶黑邊）畫在灰燼之心核心上半；換到主角回合時那一格有紅框（可攻擊）。頭目這時是第 2 階段的核心形（較矮），外框照樣成立。 |
| R4 | `1c-r4-window-1600.jpg` | **實機** 1600×900 整個視窗（R1 命中前那一格） | 外框在頭目上半，和主角卡、行動順序列、右上環境預告、底部技能列、`結束回合` 說明卡都沒有疊到。這張地圖的頭目沒有獨立的頭目 HUD 欄（頭目血條在頭頂），外框和頭目頭頂的狀態圖示、血條沒有疊在一起。 |
| R5 | `1c-r5-window-800.jpg` | **實機** 800×600 整個視窗（同一刻，自動 50%） | 外框小但找得到（頭目頭頂下方一圈淡藍）；和 HUD 沒疊到。 |
| R6 | `1c-r6-walk-north-live.jpg` | **實機**（主角從 (4,6) 經 (4,5)(4,4) 走到 (5,4)，頁面上點格子走） | 移動中沒有外框；停下後約 +10～+50 ms **兩種剪影都沒有**（1b 待決 6 的空檔），約 +65 ms 外框出現。正常速度下這個空檔約 50 ms，`anim=0.1` 慢 10 倍才看得出來；實際遊玩時肉眼看不出。 |
| R7 | `1c-r7-hit-lean-live.jpg` | **實機**（R1 那一下受擊，OCL-1c 改後） | +0、+30 外框全白；+116 起外框跟著身體往側邊歪（舊規則下這段會藏起來），閃白結束回淡藍。 |
| R8 | `1c-r8-r9-gallery.jpg` 左 | **開發頁**（`ocl-gallery.html?scene=collide` 第 2 列）；**實機未看** | 矮異形在高 3 主角後：只有 6F-22 虛線剪影、沒有新外框。實機沒排：正式地圖的開局（`cliff_outpost`、`ruined_fort` 種子 1）沒有「高台上的人南北相鄰擋人」的擺位，要特意走位，這次沒做。 |
| R9 | `1c-r8-r9-gallery.jpg` 右 | **開發頁**（`scene=concealed`）；**實機未看** | 左：隱匿中的敵人在頭目後不畫；右：沒隱匿的對照有外框。實機試過「主角在頭目正北被打倒」（熔心坑再多打一輪）：灰燼之心那一輪先進第 2 階段變成較矮的核心，主角不再被擋到 55%，看不出「倒下才不畫」，所以不算；隱匿中的敵人沒有現成的擺位。 |

## 5. 自己啟動的程序

`trpg serve`（埠 8170，PID 40828）、vite（埠 8171，PID 38616，只為 R8／R9 開發頁）、無頭 Chrome（CDP 9231，`--mute-audio`，`--user-data-dir` 在 scratchpad `ocl1c/chrome-ud`）。Chrome 用 CDP `Browser.close` 關；伺服器與 vite 用 `taskkill /PID <自己的 PID> /T`；三個埠都已沒有監聽。

## 待 PM 決定

1. R8、R9 是開發頁（實機未看）：要實機補，得另外排走位（高台擋人）或造一個隱匿敵人的局；要不要再排。
2. R6 實機看得到 1b 待決 6 的空檔（停下到外框出現約 50 ms，兩種剪影都沒有）；慢 10 倍才看得出，正常速度看不出，照現狀沒改。
3. R1 的「兩個凸起」：實機對照看起來是頭＋舉起的手臂（外框不含武器，所以沒有劍）。要不要讓外框也包手持物（樣張含手持物、面積多 25～33%），請美術判斷；本段沒改。
4. 佈局方式：頭目地圖只能經「工坊試玩」開，所以實機截圖是「開發選單單場戰鬥」＋CDP 換掉開戰回應（之後的動作都是真的）。如果美術要求「從城鎮挑戰頭目」的正式入口，這次沒走。
