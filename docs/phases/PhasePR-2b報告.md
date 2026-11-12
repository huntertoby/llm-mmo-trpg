# Phase PR-2b 報告｜靶場測試模式前端（工坊師傅選單、測試模式 HUD、入口與離開）

> 規格：`docs/phases/PhasePR-2計畫.md`（PR-2b 一節；「第 1～10 點已定」）。字串：`台詞-OB5與PR2定稿.md`「PR-2 字串」「工坊師傅（PR-2）」「測試模式戰鬥（PR-2）」三表（逐字）。
> 基底：本機 main `9163c2e6`（PR-2a），中途合併本機 main `3dd40196`（PR-2c）。未 push。

## 1. Commit

| commit | 內容 | 對應 |
|---|---|---|
| `1d442874` | `tests/content/test_field_buildings.py` 的 `RULE_HASHES["capital"]` 更新（PR-2a 改 `capital.yaml` 的遺留；開發 PM 追加） | 追加 |
| `fb3527ae` | 測試模式戰鬥 HUD：全部以 `view.practice` 分支 | 交付 3、4 |
| `a290702d` | 工坊師傅選單、靶場試玩的入口與離開、`DELETE` 試打、拿掉 `atlasModel.objectHud` 的過渡判斷 | 交付 1、2 |
| `e4fa6f9e` | 行為一致測試 B 組（`client/src/battle/pr2bPractice.test.ts`）、`range.test.ts` 掃描清單加 `WorkshopPanel.tsx` | 交付 5 |
| `81a1dea2` | 合併本機 main（PR-2c） | — |
| `d0e04316` | 師傅面板寬 520（蓋過共用彈窗 inline 寬度）、手機寬貼齊畫面 | 交付 1 |
| `b69e86b6` | vitest：戰鬥 HUD 對木樁不畫長相（開發 PM 追加「HUD 上的木樁頭像」） | 追加 |
| （本報告的 commit） | 本報告、截圖 5 張、`docs/dev/上手-前端戰鬥畫面與動畫.md` | 交付 6、7 |

## 2. 做了什麼

1. **工坊師傅選單**（`client/src/world/WorkshopPanel.tsx`、`styles/range-ob.css`）：`HudPanel` 加 `workshop`（`panelAvailable`＝`view.workshop != null`）；`objectHud` 的 `panel: "workshop"` 開面板（PR-2a 的過渡判斷已拿掉）；`WorldScreen` 另記師傅的物件 ID，選單上方照舊放 OB-6 的「重選」鈕（和說明卡共用 `ReselectEntry`）。版面：`world-hud-panel` 寬 520（手機寬貼齊畫面、左右留 8）、`mail-head`（頭像 56＋「工坊師傅」＋`title_zh`）、台詞一行、兩列選單（一般／滑過／停用三態；第 2 列永遠停用、只寫一次 `rework_note_zh`）、「新」小牌（`practice_new` 且本機還沒點過）、面板下 `footer_zh`。第 1 列不能按時 `aria-disabled` 並用 `<Hint>` 說 `practice_blocked_zh`。可以正式選定時點師傅照 OB-5 開選定整頁（`interactHud` 開頭的 `opensChoose` 沒動）。選單小圖：木樁＝內嵌 SVG（照樣張 `dummy()` 的座標）、改造技能＝`WeaponIcon` 的 `hammer`（米色圓章）。
2. **開「靶場試玩」**（`WorldScreen.openPractice`）：`practice_new` 時先送 `hint_seen {ids: [seen_id]}`，再 `POST …/range/practice`（`api.worldRangePractice`），進戰鬥：地名 `rangeFightPlace("practice", view)`＝「{`WorkshopView.capital_zh`}・工坊靶場」、離開鈕「離開靶場」、開場訊息＝[標題, `SANDBOX_NOTE`]；面板先關。離開（`backToMap`）時兩種靶場戰鬥都先呼叫 `DELETE …/range/trial`（`api.worldRangeTrialClose`，失敗不擋），靶場試玩回主城實地圖（面板關著），開局試打照舊回靶場整頁。`rangeFight` 從布林改成 `"trial" | "practice" | null`；靶場試玩的主角卡頭像用角色的出身框（開局試打照舊）。
3. **測試模式戰鬥版面**（`view.practice` 為真時；實戰分支輸出不變）：
   - 上方中央 `PracticeBar`（`TestModeBadge` 原樣重用＋「每次出手後自動過一輪，資源立刻補滿，木樁不會倒」），不放 `TurnBar`。
   - `TurnControls` 不放「結束回合」、不補按鈕（格子自然收合、靠底，沒改）。
   - `BattleStatusBox`：勝利條件換成「沙盒・不算勝負」小牌；輪數照舊。
   - `PreviewBox`：總覽行「命中」「暴擊」「傷害」三段各自 `white-space: nowrap`、命中率綠色粗體；有命中率時多一行淡金色「靶場木樁必中，實戰會有失手」。數字照引擎（實機 100%）。
   - `SkillBar.costParts(b, practice)`：測試模式拿掉「冷卻 N 回合」那段（冷卻中的「冷卻 N」也不出）。
   - 提示句：`practiceWording(text, practice)`（「敵人」→「木樁」）套在技能列上方那行（`actionHintText`／`modeBarHint` 的結果）與選取面板的 `OpHint`（一般模式、兩段選取、複合技能、隊友指令）。
   - 紀錄：`practiceRoundLines`（`battle/logGroups.ts`）在輪數 +1 時插「第 {n} 輪結束：木樁補滿」，`BattleScreen` 先過它再交給 `BattleLogDock`（浮動提示與完整清單都看得到；`BattleLogDock`／`BattleLog` 沒改）。
4. **排版煙霧檢查**：`layoutSmoke.ts` 的上方中央選擇器改成 `ORDER_SELECTOR`（`.turn-bar` 或 `.practice-bar`），`HUD_SELECTORS`／`MAP_COVER_SELECTORS` 共用。
5. **測試**：見第 3 節 B 組。
6. **截圖**：第 6 節。
7. **上手筆記**：`docs/dev/上手-前端戰鬥畫面與動畫.md` 更新第一節（檔案表加 3 列：測試模式 HUD 分支、`practiceWording`／`practiceRoundLines`、`WorkshopPanel`）、第二節（「從點擊到畫面」加第 8、9 點）、第四節（新坑 24～27）、第五節（測試表加 PR-2b 一列）。

**開發 PM 追加三項**
- 開局試打標題「靶場試打：{武器}＋{招 1}、{招 2}」：標題是**前端**接的（伺服器 `title_zh` 只到武器，前端原本就接 `skills_zh`），抽成 `range.rangeFightNotes("trial", res)` 並加測試鎖字（看示範比照）；後端沒改。靶場試玩照舊只寫「靶場試玩：{武器}」。
- `RULE_HASHES["capital"]` → `5bb6634881af56be`（註解「PR-2a：靶場說明卡定稿句、工坊師傅 panel」），`tests/content` 2790 passed；`ruff check`／`ruff format --check` 該檔通過。
- HUD 上的木樁頭像：**實際查過，戰鬥 HUD 沒有任何地方畫單位長相**——行動順序列是字母章（`turn-chip-marker`）、資訊卡（滑過與釘選小卡）是字母章＋名字；前端畫長相的只有主角頭像（`ui/heroFace.tsx`，只給主角）與大世界的敵人縮圖（`world/enemyThumb.tsx`，木樁不會出現在野外）。所以沒有「舊的人形頭像」可換，`render/` 沒改。用 vitest 鎖住（`pr2bPractice.test.ts`「木樁在 HUD 上的樣子」三項：`TurnBar` 與 `UnitInfo`（含精簡版）對兩種木樁沒有 `<img>`／`<canvas>`／portrait、戰鬥 HUD 元件不匯入任何畫長相的函式），截圖見第 6 節第 5 張右三分之一（以 `practice=false` 改寫回應呈現 3F 那種有行動順序列的 HUD，戰場上是 PR-2c 的新木樁）。

## 3. 逐條驗收

| 驗收 | 結果 | 證據 |
|---|---|---|
| `corepack pnpm -C client typecheck` | 結束碼 **0** | `tsc --noEmit` 無輸出（合併 PR-2c 後重跑） |
| `corepack pnpm -C client test` | 結束碼 **0** | `Test Files 289 passed (289)`、`Tests 3589 passed (3589)`（合併 PR-2c 後重跑） |
| `corepack pnpm -C client build`（`vite build`） | 結束碼 **0** | 只有既有的 chunk 大小警告 |
| 行為一致 B 組 | 全過 | 下表 |
| 移植需求第 4 節第 7、8、10、11 項 | 有截圖 | 第 6 節 |
| 浮動卡實測 | 通過 | 第 4 節 |
| `__layoutSmoke` 三個尺寸 | 全 PASS | 第 5 節 |
| 實戰畫面不變 | 是 | B1～B5 的實戰列逐字比對改前；實機 `/?dev=1` 單場戰鬥：提示句「點選紅框敵人攻擊」、有行動順序列、有「結束回合」、右上 ⚔、技能「・冷卻 1 回合」（`pr2b_10_compare.jpg` 左半） |
| Python（只動了一個測試檔） | 通過 | `tests/content -n 8` 2790 passed；ruff 兩項通過 |

**B 組對照**（`client/src/battle/pr2bPractice.test.ts`，27 項）

| # | 測試 | 斷言重點 |
|---|---|---|
| B1 | 「B1 提示句…」4 項（含 `it.each` 6 列） | `actionHintText` 六種狀態的實戰輸出＝改前原字（寫在表裡）；測試模式移動句＝定稿原字「…點選紅框木樁攻擊…」；寫「目標」的句子不變；`BattleBottomBar`／`ActionPanel` 原始碼確實經過 `practiceWording` |
| B2 | 「B2 costParts」2 項 | 實戰有「冷卻 2 回合」／冷卻中「冷卻 2」；測試模式兩者都沒有，其餘代價相同 |
| B3 | 「B3 回合操作」 | 實戰有 `end-turn-button`；測試模式沒有，其餘按鈕清單＝實戰去掉「結束回合」；`practice=false` 的輸出和不給一樣 |
| B4 | 「B4 狀態盒與上方中央」3 項 | 實戰有勝利條件、沒有小牌；測試模式有「沙盒・不算勝負」、沒有勝利條件、輪數照舊；提示條＝徽章＋定稿句；`BattleScreen` 依 `practice` 二選一；預覽拆段與必中句 |
| B5 | 「B5 戰鬥紀錄」2 項 | 實戰原樣回傳同一陣列；測試模式插在新一輪前、`seq` 不重複、`groupLog` 後順序正確 |
| B6 | 「B6 工坊師傅選單」5 項 | 「新」小牌條件；字照伺服器；停用列 `aria-disabled`＋原因＋沒有「›」；第 2 列永遠停用、「之後開放」只一次；`objectHud`／`panelAvailable`／`WorldScreen` 接線 |
| B7 | 「B7 地名、離開鈕、開場訊息」3 項 | `rangeFightPlace` 吃 `WorkshopView.capital_zh`／`RangeView.capital_zh`；「離開靶場」／「回到靶場」；開局試打標題接招名、靶場試玩不接；新檔不寫死「主城」與技能 ID（`world/range.test.ts` 兩個掃描清單加了 `WorkshopPanel.tsx`） |
| 追加 | 「木樁在 HUD 上的樣子」3 項 | 見第 2 節追加第 3 點 |

**更動的既有測試**：`world/range.test.ts`「接線」那項原本找 `'"回到靶場"'` 字面（字搬到 `range.ts` 的 `TRIAL_EXIT_LABEL`），改成找 `rangeExitLabel(rangeFight)`，字本身由 B7 鎖；兩個掃描清單各加 `WorkshopPanel.tsx`。其他斷言沒放寬。

**實機驗證（第 11 項；自己啟動的 `trpg serve --port 8112`，存檔在暫存區，開發入口沒用）**：`POST /api/world/characters`（舊流程建角＝開局已結束、弓＋點燃／充能，出生在主城）→ 送 `hint_seen ["opening"]` 跳過醒來那張卡 → 方向鍵走到 (23, 18) 朝東按 E → 師傅選單（「新」小牌在）→ 點「靶場試玩」→ 戰鬥（標題「靶場試玩：弓」、`view.practice=true`）→ 放「引火射」打木樁（第 1 → 2 輪）→ 普攻（→ 第 3 輪）→ 紀錄有「第 1 輪結束：木樁補滿」「第 2 輪結束：木樁補滿」→ 右上離開鈕（`aria-label`「離開靶場」）→ 回主城實地圖、面板關著 → `GET /api/battles/{那場}` **404**（DELETE 生效）→ 再按 E：「新」小牌**不見**；重新整理頁面再開：仍不見；`WorldView.workshop.practice_new == false`。

## 4. 浮動卡實測（6.5.1；無頭 Chrome、`--mute-audio`、`?mute=1`）

| 情況 | 1600×900 | 800×600 |
|---|---|---|
| 測試模式戰鬥：技能列「引火射」的技能卡 | 滑過 → 開；滑進卡片 600ms 仍開；卡內容放得下、沒有捲軸（不用捲）；點卡片 → `.pinned`；滑出 700ms 仍開；Esc → 關 | 同左 |
| 師傅選單第 1 列停用時的 `<Hint>`（卡片字「先處理眼前的事，再來打木樁」） | 同上全過；點停用列不會開戰鬥 | 同左 |

- **「卡內捲到底」沒有實測到**：測試模式戰鬥裡逐一滑過所有可滑進的卡（技能 2 張、種族技、測試模式徽章、地名、輪數），800×600 最高 124px，都放得下、沒有捲軸。
- **停用列的狀態在主城實機到不了**（戰鬥中、遭遇、待選閃現／三選一時不會在主城開著這個面板），實測時在頁內改寫 `/api/world/characters/…` 的回應（`practice_available=false`）造出來；列在第 7 節「實機未看」。

## 5. `window.__layoutSmoke.runCase("PR-2b")`（`localStorage.clear()` → `/?dev=1&anim=0.1&mute=1`）

| 尺寸 | 結果 |
|---|---|
| 1600×900 | **全 PASS**（12 項：結束回合寬度 232/232、播放列、HUD 互不重疊 7 塊、資訊卡提示列、更多動作選單、說明卡不外包 0 個、浮動卡底色、文字溢出 0 項、地圖不被蓋 6 塊、四角飾件、選取技能時地圖不被蓋） |
| 1040×624 | **全 PASS**（同 12 項；結束回合 202/202、地圖 [347,68,721,474]） |
| 800×600 | **全 PASS**（同 12 項；結束回合 202/202、地圖 [254,90,566,428]、選取面板 [8,162,238,280]） |

`runCase` 只量實戰；測試模式的新元件（提示條）靠 `ORDER_SELECTOR` 一起量，沒有另加測試模式的 case（入口要走大世界，`runCase` 的單場戰鬥進不去）。

## 6. 截圖（`docs/art/shots/pr2/`，本段 5 張；和 2c 的 5 張合計 10 張；jpg 80）

| 檔名 | 大小 | 對應移植需求第 4 節 |
|---|---|---|
| `docs/art/shots/pr2/pr2b_7_master_1280.jpg` | 82 KB | 第 7 項：1280 一般｜滑過（裁切 720×400，含右下的工坊師傅：護目鏡、鬍子、皮圍裙、平頭鎚）；「新」小牌 |
| `docs/art/shots/pr2/pr2b_7_master_390.jpg` | 102 KB | 第 7 項：390×844 一般｜滑過（面板貼齊畫面；這個寬度師傅被面板蓋住，看不到） |
| `docs/art/shots/pr2/pr2b_8_practice_1280.jpg` | 136 KB | 第 8 項：1280×720 移動狀態（藍格、提示句寫木樁）｜普攻狀態（預覽命中 100%、必中句；三段不拆）；兩張都沒有回合列、沒有結束回合、技能不寫冷卻 |
| `docs/art/shots/pr2/pr2b_10_compare.jpg` | 126 KB | 第 10 項：左＝實戰（`/?dev=1` 單場戰鬥，版面不變）｜右＝測試模式 |
| `docs/art/shots/pr2/pr2b_11_live_hud.jpg` | 187 KB | 第 11 項：實機放招＋普攻後（紀錄展開，有「木樁補滿」）｜按「離開靶場」回樞島｜（追加）不帶測試模式的 HUD：行動順序列與資訊卡的木樁＝字母章 |

為了總張數 ≤ 10，規格寫的「一般、滑過各一張」「普攻、移動各一張」都併成左右並排的一張（每格原尺寸或縮成 960×540）。

## 7. 實機未看

- 師傅選單第 1 列**停用**（主城實機到不了，見第 4 節；外觀只有 vitest 與改寫回應的實測，沒有截圖）。
- 第 5 張右三分之一的「不帶測試模式的 HUD」：是同一場靶場試玩把回應改寫成 `practice=false` 畫的（技能工坊 3F 的試玩要先通過工坊檢查，腳本沒走那條路）。
- 手機寬（390）的戰鬥版面：規格不做。

## 8. 暫定字串

本段沒有新的暫定字串：師傅選單、提示條、沙盒小牌、必中句、「離開靶場」、「第 {n} 輪結束：木樁補滿」、移動模式提示句都是定稿原字；「新」小牌的字「新」照定稿補定 3。前端自寫的「試打結束」（結束面板標題，原本開局試打就用）沿用到靶場試玩。

## 9. 和規格不同的地方

1. **「只改」清單外改了**：`client/src/world/atlasModel.ts`（拿掉 PR-2a 的過渡判斷，PR-2a 報告要求）、`client/src/world/range.test.ts`（掃描清單與一個斷言）、`client/src/battle/pr2bPractice.test.ts`（新）、`tests/content/test_field_buildings.py`（開發 PM 追加）。`BattleLogDock.tsx`／`BattleLog.tsx`／`WorldHud.tsx`／`api/types.ts` 沒改（紀錄行在 `BattleScreen` 插、面板寬度用 CSS、型別用 `NonNullable<WorldView["workshop"]>`）。
2. **面板寬度用 `!important`**：共用彈窗把寬度寫在 inline style（720），要 520 只能蓋過去（`range-ob.css` 已有同類先例）。
3. **截圖併張**（第 6 節）。
4. **選單小圖的木樁**是 `WorkshopPanel.tsx` 內嵌 SVG（座標照樣張 `dummy()`），沒有重用 PR-2c 的 `drawTrainingDummy`（那是 canvas 畫法、2b 寫面板時 2c 還沒合併；要統一可在之後改成畫布）。

## 10. 待 PM 決定

1. **`TestModeBadge` 的說明卡字**是 3-39 的「測試模式：戰後回滿，不計入任何統計」，放在靶場提示條上意思不完全對（靶場是每次出手補滿）。規格寫「只重用」，沒改；要不要給靶場另一句。
2. **回合操作靠底**照樣張（拿掉「結束回合」後四顆常駐鈕比實戰下移，移植需求說約 54px；並排見 `pr2b_10_compare.jpg`）；要改靠上先問美術 PM。
3. **戰鬥開始的橫幅**（「戰鬥開始」＋勝利條件一句）在測試模式照舊出現；規格沒寫，沒改。
4. **`SummonPanel`（指揮召喚物）裡的「敵人」**（「選一個敵人集火」等）沒換成「木樁」：檔案不在只改清單，而且靶場只有主角、召喚技能才會出現；要不要一起換。
5. **師傅選單停用列在主城實機到不了**（第 7 節）：目前的擋法（戰鬥中、遭遇、待選）都會讓玩家不在這個面板上；`practice_blocked_zh` 實際上只會在直接打端點時看到。
6. **手機寬（≤ 560）師傅面板蓋過左右的 HUD 欄**（照樣張貼齊畫面）；其他 HUD 面板在這個寬度仍是中間一窄條。
7. **戰鬥 HUD 沒有單位長相**（第 2 節追加第 3 點）：開發 PM 說的「木樁小頭像仍是人形」查不到出處；若是指別的畫面（例：3F 的試玩面板、某張截圖），請指明位置。
8. **「改造技能」小圖**用 `WeaponIcon` 的 `hammer`（武器 ID 寫在元件裡）；Q 版小圖示批次換圖後會跟著變。
