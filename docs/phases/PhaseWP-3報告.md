# Phase WP-3 報告｜許願池前端

> 實作 agent，2026-11-13。規格 `docs/phases/PhaseWP計畫.md` 第 5 節；WP-2 報告最後的開發 PM 裁定（拿掉 `objectHud` 略過 `wish`、文字許願帶 `keywords: []`）；美術 PM 的六條版面方向（專案 PM 轉達）。
> 使用者核可：「都按照建議」（專案 PM 轉達）。`docs/design/`、後端、`src/trpg/skillgen/`、重閃與閃現歷程的程式都沒動。
> commit：`f9c1c8e9`（面板、等待、三選一標題與退款鈕、測試）、`fb1a2560`（守池人與池子開面板的測試）、`254003b4`（下固定區不跳、許願專用的等待說明、回到地點圖不折行）、`1311323b`（截圖）、`b5e054d7`（merge main：RR-1）、本報告與上手筆記一筆。

## 1. 做了什麼

| 規格 | 做法 | 檔案 |
|---|---|---|
| 主城點池子或守池人開面板 | `objectHud` 不再略過 `wish`；`HudPanel` 多 `wish`，`panelAvailable`＝`view.wish != null`；`hudPanelContent` 的 `case "wish"` | `world/atlasModel.ts`、`world/hud.ts`、`screens/WorldScreen.tsx` |
| 面板讀 `WorldView.wish` | `WishPanel`：上固定區（標題＋守池人＋不能許的原因＋籌碼＋分頁列）、中間分頁內容、下固定區（前 → 後＋許願鈕） | `world/WishPanel.tsx`、`styles/world-panel-wish.css` |
| 文字許願與選單許願 | 兩個分頁：「說出願望」（輸入框、`maxLength`＝`text_max_chars`、字數）、「從選單挑」（1～`max_keywords` 個，照點的順序標「第 1 個／第 2 個」）；LLM 關著（`llm` false）只有選單、不畫分頁列 | `world/WishPanel.tsx`、`world/wish.ts` |
| 送出 | `wishAction`：文字＝`{kind:"wish", text, keywords: []}`、選單＝`{kind:"wish", keywords}`；`WorldAction` 型別多 `WishAction` | `world/wish.ts`、`api/types.ts` |
| 等待提示 | 文字許願先 `pregen/wait`（`kind: "wish"`、帶願望），等待元件同閃現（`PregenWaitDialog`）；說明行改許願專用（逾時改開選單）；`waitPregen` 回 `go`／`cancel`／`timeout` | `world/pregen.ts`、`world/PregenWaitDialog.tsx`、`screens/WorldScreen.tsx` |
| 逾時自動切到選單並說明 | `timeout`＝不送動作；伺服器退回（沒聽懂等）＝不扣錢。兩種都讓面板重開在「從選單挑」，第一行琥珀提示（逾時是前端字，退回是伺服器的原因句） | `screens/WorldScreen.tsx`（`wish`、`WishFallback`）、`world/WishPanel.tsx` |
| 三選一的標題與跳過鈕 | `source == "wish"`：標題＝伺服器的 `quest_name_zh`（「許願池」）、副標＝`step_zh`（不再接成「許願池：許願：…」）、跳過鈕「都不拿（退 N 任務幣）」（`refund`）；任務與機遇照舊 | `world/QuestLog.tsx`、`world/wish.ts` |
| 不能許時灰掉並顯示原因 | 第一行 `NowOffNote`「現在不能用：{`blocked_zh`}」（3.7 的寫法）；輸入框與選單灰階變暗、許願鈕停用 | `world/WishPanel.tsx`、`styles/world-panel-wish.css` |

共用元件只加一個選填參數：`PanelTabs` 的 `onTab`（切分頁時通知呼叫端；下固定區的許願鈕要知道現在是哪一種許法）。沒傳的面板行為不變。

### 1.1 美術 PM 六條的對照

1. **版面**：上固定區＝`PanelTabs` 的 sticky `.pnl-fixed`（不捲、捲下去下緣 18px 漸隱，PNL-1a 的那條）；中間捲；下固定區＝框的 `ui-popup-foot` 插槽（FL-1b 的做法）。高度：`PanelTabs` 量兩個分頁取最高（鎖高上限照 `cappedLock`），切分頁外框不跳；下固定區那行「為什麼按不下去」一律佔一行，挑關鍵字、切分頁時下固定區高度不變（實量 1600：94px、800：86px，兩個分頁相同）。窄版用容器查詢 559px（守池人收成標題旁 28px＋一行、選單一欄）。
2. **標籤**：「第 N 個」＝實心（狀態）；選單每格白 4% 淡底不描框，挑中的才描金框（狀態）；沒用虛線（挑滿 2 個時其他格只變暗 0.7）；「現在不能用」照 3.7（琥珀實線框、四個字琥珀粗體）放第一行；逾時提示（警告）放選單分頁第一行；退款說明（資訊、L3）放分頁內容最後。
3. **圖示**：只用已定案的：任務幣＝第⑦批 HUD `token`；選單關鍵字＝第⑤b 批關鍵字圓章（12 個都有）；「現在不能用」、前 → 後的警告三角＝第⑦批。沒有對應圖的留字（見第 5 節「缺的圖」）。
4. **前 → 後**：直接用 FL-1b 的 `DiffRows`：任務幣 9 → 5、本週次數 剩 2 次 → 剩 1 次＝代價（細框＋警告三角）；得到 沒有 → 新 技能三選一＝新（綠「新」）。付不起「不夠」、沒次數「沒有了」照代價畫。
5. **字**：伺服器有的全用伺服器的暫定字；前端自寫的字集中在 `world/wish.ts` 的 `WISH_ZH`，清單在第 4 節。
6. **截圖**：四個狀態 × 兩個尺寸都拍了（第 3 節）。

## 2. 測試

新檔 `client/src/world/wp3Wish.test.ts`（13 項）：兩種許法、關鍵字順序與上限、送出鈕的原因、動作形狀（`keywords: []`）、前 → 後的四種記號、三選一標題副標與「都不拿（退 N 任務幣）」、`objectHud`／`panelAvailable`、`pregenWaitBody`／`pregenWaitText`／`pregenWaitNote`／`pregenRequestId`、面板四種輸出（可以許、不能許、LLM 關、逾時退回選單）。

改的既有測試：
- `world/atlas.test.ts`：`objectHud({ panel: "wish" })` 改成開 `wish` 面板。
- `world/capitalFigures.test.ts`（專案 PM 轉達的 main 上 2 條失敗）：守池人的 `panel` 期望 `"wish"`；說明卡期望 WP-2 的暫定台詞「說出你想要的力量」；另加一條鎖住「點守池人、許願池都開許願池面板」（從 `capital.yaml` 讀物件 → `objectHud`）。

## 3. 實機截圖（`docs/art/shots/WP-3/`，DPR 1，`?mute=1`，無頭 Chrome `--mute-audio`）

做法：`localhost:8001` 沒回應，改用 LM Studio `100.87.188.89:1234`（`swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp`，`reasoning_effort = "none"`；設定在 worktree 的 `config/llm.local.toml`，gitignored、沒 commit，`config/llm.toml` 沒改）。自己的 `trpg serve --port 8796`（`TRPG_SAVE_DIR` 暫存區、`TRPG_LLM_CONFIG`、`TRPG_DEV_ROUTES=1`）、建置好的前端、`POST /api/world/llm {enabled:true}`。存檔用暫存區腳本寫三個入門期已過的主城角色（alice、carol 任務幣 9；bob 任務幣 2），站在守池人正下方朝北；首頁「繼續」→ 按 E 開面板。無頭 Chrome 除錯埠 9571（`--remote-debugging-address=127.0.0.1`，開之前 `netstat` 確認 8796、9571 沒人用）。交件前用自己記下的 PID 關掉伺服器（57108）與 Chrome（48148，含子程序），兩個埠都沒在聽。

| 檔案 | 狀態 |
|---|---|
| `wp3_01_empty_1600.jpg`、`wp3_01_empty_800.jpg` | 沒許願：剛打開，「說出願望」分頁、空的輸入框，下固定區「先寫下你的願望」、許願鈕停用 |
| `wp3_02_menu_1600.jpg`、`wp3_02_menu_800.jpg` | 可以許（選單許願）：挑了冰凍（第 1 個）、撞擊（第 2 個），其他格變暗、許願鈕可按 |
| `wp3_03_wait_1600.jpg`、`wp3_03_wait_800.jpg` | 文字許願等待中（「想把敵人凍住，再一錘敲碎」）：等待元件同閃現，說明行是許願專用 |
| `wp3_04_result_1600.jpg` | 結果（**本機 LLM**）：標題「許願池」、副標「許願：都不拿可退 2 任務幣（次數照扣）。」，第一張是 LLM 提議的「寒核凝結」（掛「源晶推演」） |
| `wp3_04_result_800.jpg` | 結果（本機 LLM，carol）捲到底：跳過鈕「都不拿（退 2 任務幣）」；按下後提示「跳過了許願池給的技能，退還 2 任務幣。」 |
| `wp3_05_poor_1600.jpg`、`wp3_05_poor_800.jpg` | 點數不夠（bob 任務幣 2）：第一行「現在不能用：任務幣不足，許願要 4 任務幣」，表單灰掉，前 → 後「任務幣 2 → 不夠」 |

實測到的延遲（不是量測，只是順手記下）：文字許願 alice 5.5 秒、carol 8.2 秒都在 10 秒內；前一輪（重拍前）一次 10.6 秒逾時 → 面板自動切到「從選單挑」、第一行出逾時提示（看過，沒放進 10 張的額度）；背景那一筆照跑完，同一句再送一次直接拿到。

浮動卡實測（800×600，守池人那一行的 `Hint`）：滑過開卡 → 滑進卡片仍開著 → 點一下釘住 → 滑走仍在 → Esc 關（面板沒關）。卡只有一行，沒有「卡內捲到底」可測。1600 寬版守池人是對話泡，沒有說明卡。

## 4. 玩家看得到的字（交玩法 PM 確認）

**伺服器的暫定字**（WP-1／WP-2，前端照用）：標題「許願池」、守池人「「說出你想要的力量，池子會回應你。」」、選單 12 個關鍵字的名稱與說明（`skill_keywords.yaml`）、不能許的原因（`wish_problem`／`wish_block`：「只有在主城能許願」「入門期還不能許願，找葛蘭選定武器後再來」「還有沒處理的遭遇，不能許願」「這週已經許了 2 次願，下週再來」「任務幣不足，許願要 4 任務幣」「戰鬥進行中，先打完這場」「還有閃現的選項沒有選：先選一個」「還有任務給的技能三選一沒有選：先選一招或跳過」）、沒聽懂「許願池這次沒聽懂你的願望，改從選單挑關鍵字吧（沒有扣任務幣）。」、三選一副標「許願：都不拿可退 N 任務幣（次數照扣）。」、提示「跳過了許願池給的技能，退還 N 任務幣。」。

**前端自寫的暫定字**（全在 `client/src/world/wish.ts` 的 `WISH_ZH`，玩法 PM 定稿後只換字）：

| 位置 | 字 |
|---|---|
| 分頁（全名／窄版短名） | 說出願望／願望、從選單挑／選單 |
| 籌碼 | 任務幣、本週還能許 N／M |
| 說出願望分頁 | 用一句話說出想要的力量；說書人會對到 1～2 個關鍵字，再給你一份技能三選一。 |
| 輸入框提示 | 例：想把敵人凍住，再一錘敲碎 |
| 從選單挑分頁 | 挑 1～2 個關鍵字：三招都會帶第 1 個，第 2 個優先出現在其中一招。 |
| 選中標記 | 第 1 個、第 2 個 |
| 前 → 後 | 任務幣、本週次數（剩 N 次）、得到（技能三選一）、不夠、沒有了 |
| 退款說明 | 三選一都不拿也算一次，退 N 任務幣。 |
| 送出 | 許願；按不下去時：先寫下你的願望、先挑 1 個關鍵字 |
| 等待提示 | 許願池正在聽你的願望……（無障礙標籤）；最多等 10 秒；來不及就改從選單挑關鍵字（不扣任務幣）。 |
| 逾時 | 說書人這次來不及想好（等了 10 秒），改從選單挑關鍵字吧（沒有扣任務幣）。 |
| 三選一跳過鈕 | 都不拿（退 N 任務幣） |
| 共用 | 現在不能用（3.7 既有字）、回到地點圖（既有） |

## 5. 待 PM 決定（照最保守的做法做了）

1. **版面沒有樣張**：美術 PM 沒出移植需求，照資訊面板通用規則與 FL-1b 的上下固定區做；面板寬沿用 HUD 面板的 720（工坊師傅是 520，許願池內容多、照資訊面板）。請美術 PM 驗收時看。
2. **缺的圖（交美術排畫，現在留字）**：兩個分頁的 16px 圖示（說出願望、從選單挑）、「本週還能許」籌碼的圖示、標題列的許願池小圖。分頁沒圖示：分頁列縮到第 ② 級（只剩圖示）時會沒有字；兩個分頁的短名在 250px 以上都放得下，實際碰不到。
3. **1600 選單要捲**：12 個關鍵字兩欄、每格兩行說明，比鎖高（捲動區可視高）高，中間要捲一點；800 一欄捲比較多。要一屏放完得把說明收成一行或拿掉（字量交美術 PM 看）。
4. **「說出願望」分頁的空白**：面板高度照最高的「從選單挑」鎖，說出願望那頁下面留白（1600 約 250px）。照規則「外框不跳」做的結果。
5. **三選一畫面的「不選任何一張就是跳過（技能不變）。目前：跳過。」**是共用 `OfferPicker` 的字，許願池這裡和跳過鈕「都不拿（退 N 任務幣）」用詞不一致；沒改共用元件（任務、機遇共用），請玩法 PM 一起定。
6. **逾時與被退回都切到選單**：規格只寫逾時；伺服器退回（沒聽懂、不能許）也同樣切過去並把伺服器的原因放第一行，選單許願被退回則照舊走全域錯誤訊息。
7. **退款說明放在分頁內容最後**（資訊放內容後面），不放下固定區：800 下固定區放不下兩欄字（會撐高到 124px、中間只剩約 140px）。
8. **`layoutSmoke` 沒加許願池的量測**：面板沿用 `world-hud-panel`，既有量測照樣涵蓋外框；沒跑三尺寸 `runTown`（規格沒要求）。

## 6. 檢查（交件前，merge main `RR-1` 之後）

| 檢查 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client build` | 0 |
| 直接相關 vitest（`world/wp3Wish`、`atlas`、`pregen`、`capitalFigures`、`hud`、`pnl3Quest`、`story`、`pnl1bBoard`、`ui/pnl1aPanelKit`、`floatCardRule`、`sharedPopup`、`waitScene`、`eventCardScroll`、`test/importCycles`、`sourceScan`、`render/qIcon/qIconArmor`、`run/`、`dev/layoutSmoke`；33 檔 477 項） | **1**：476 過、1 失敗＝`ui/floatCardRule.test.ts`「沒有原生 title=」抓到 `run/CampfireSkillCare.tsx:110 <button title=…>` |

那 1 條失敗（和另一條 `ui/summonBadges.test.ts` 的「行首全形空白」`run/CampfireSkillCare.tsx:119`）都是 merge 進來的 RR-1（`983a7ed1` 重閃欄位標灰）在 `CampfireSkillCare.tsx` 的改動，不是這段的檔；那塊是重閃的程式（派工說不要碰），沒修，請 PM 轉給 RR-1。merge 前跑過的直接相關 vitest（含 `floatCardRule`）都過。

沒改 Python，沒跑 ruff、mypy、lint-imports、pytest；沒跑全量 `check.py`、整包 vitest、數值量測。快照沒有要重產的（OpenAPI 沒變）。

## 7. 需要使用者決定

沒有新的。
