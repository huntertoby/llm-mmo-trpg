# Phase 3F-2 報告：技能工坊網頁

## 1. commit

| commit | 內容 |
|---|---|
| fdeaaa4 | 工坊編輯邏輯（`client/src/workshop/`：草稿路徑與選項寫入 `draft.ts`、步驟與檢查顯示與暫存 `state.ts`、試玩請求 `tryout.ts`、YAML 轉換 `yamlEdit.ts`）、API 客戶端與型別（`api/client.ts`、`api/types.ts`）、新增相依 `yaml@2.8.1`、真實回應 fixtures、`workshop.test.ts`（28 個測試） |
| 0fc8ca8 | 頁面：`screens/WorkshopScreen.tsx`、`ui/workshop/`（步驟列與欄位編輯器、檢查面板、試玩面板、隨機／匯出／YAML 面板）、首頁入口、戰鬥畫面的「回到技能工坊」按鈕、樣式 |
| （本報告） | 報告 |

沒有 stash、reset、amend、切換分支，沒有 push。**後端完全沒改。** 其中 `ui/useSkillCards.ts` 新增 `primeSkillCard`（見 3.3）。

## 2. 交付項目

- **入口**：首頁表單下方「技能工坊」區塊，按鈕「進入技能工坊」。App 記得是從工坊進的戰鬥，離開或結束後回工坊。
- **一步步組**（`StepView`）：最上面的步驟列（骨架、基本設定、形狀、效果、條件、代價、稀有度），填完的打 ✓，前面步驟沒填完的灰掉；每一步有標題、說明、該步的限制清單（`notes_zh`）與欄位；「← 上一步」「下一步 →」和步驟列都能回頭修改。欄位全部依後端 `FieldSpec` 畫（單選卡片附說明與「核心／附帶／稀有以上」標籤、數字框顯示範圍、勾選、多選、骰子、標籤、物件、效果列表可新增／移除／上下移、修正規則列表），必填欄位標 `*`。
- **即時檢查面板**（`CheckPanel`）：改動後 250 毫秒呼叫 `check`；顯示一句話結論（還沒組完／合法／不合法 N 項）、預算條（百分比、合格區間的兩條刻度線、綠＝合格、黃＝過弱、紅＝過強，下方一句「太弱／太強該怎麼調」）、技能點數與可用預算、可展開的逐項點數明細、違反的規則（規則代碼＋中文）、最低稀有度與原因、技能卡片預覽（沿用戰鬥用的 `SkillCardView`）。
- **隨機一個**：階級、稀有度、骨架、種子 → `random`，結果帶進編輯器（已有內容時先確認；拿掉 `skill_rand_N` 的 ID，之後由內容雜湊重算）。
- **裝上試玩**（`TryoutPanel`）：主角 build、要換掉哪一個技能（顯示中文名；不換＝加在空格）、地圖（預設靶場）、對手（只有靶場才出現，木樁／會反擊，含說明）、種子。技能未組完或不合法時按鈕停用並說明原因；檢查更新中也停用。成功後直接進入既有戰鬥頁。
- **匯出**：「下載 YAML」呼叫 `export`，以 Blob 下載 `skill_ws_xxxx.yaml`；不合法也能匯出，頁面提示「目前不合法」與原因。
- **暫存**：草稿、目前步驟、試玩選項存在 `localStorage`（鍵 `trpg.workshop.v1`），重新整理、進戰鬥再回來都在；存取失敗（無痕視窗等）時悄悄略過。另有「清空重來」（有內容時確認）。
- **進階：直接編輯 YAML**：可摺疊文字區，內容與草稿雙向同步；打字即時解析，格式有誤時顯示中文錯誤（含行欄）且不套用、保留上一個有效內容；JSON 也能貼。修改後同樣即時檢查。巢狀效果（`type: effects` 但沒有選項）在欄位位置顯示說明「請用進階 YAML」並顯示現有內容的 JSON。
- **法力提醒**（0.1 #9）：技能有法力代價時，試玩面板常駐一句「每次施放要 N 點法力」；建立戰鬥後比對主角 `max_mana`，不夠時先停在面板上顯示「法力上限只有 X，這個技能需要 Y 點法力」，讓使用者選「仍然進入戰鬥」或「回去調整」。
- 戰鬥頁：從工坊進入時，回合列下方多一顆「← 回到技能工坊」（隨時可離開，沒有手動結束，3F-1 待決定 #7），戰鬥結束面板的主按鈕也改成「回到技能工坊」。

## 3. 設計說明

### 3.1 選項如何寫進草稿（`draft.ts`，無規則）

- 值是物件的單選欄位只有 `shape`、`condition`（寫成 `{type, ...參數}`），效果列表的每一項也是 `{type, ...}`；其他單選寫純量，選項專屬的參數（`ap_cost`、`weapon_req`、觸發時機的 `n`……）寫在同一層。這個區分是前端寫死的欄位名單（`OBJECT_CHOICE_FIELDS`），後端 `FieldSpec` 沒有標記。
- 換選項時清掉其他選項專屬、而且不適用新選項的參數（例如武器技換法術技，近戰武器需求會被清掉）。
- 新增形狀、效果、選項時，**必填的整數**自動補成預設或範圍最小值（例如擊退距離 1、射程 1），選填的不替使用者決定；必填且只有一個選項的單選（例如「主動技」、被動技的形狀「自己」）自動選好。
- 換骨架會清掉除名稱外的所有欄位（先確認）。

### 3.2 步驟狀態（`state.ts` 的 reducer）

動作：`edit`、`replace`（隨機／清空／載入，忘掉舊選項與檢查）、`goto`、`back`、`next`、`options`、`check`。目前步驟為 `null` 時取第一個沒填完的步驟（全部填完看最後一步）；已選的步驟若因為編輯消失（例如換骨架）就退回預設。

### 3.3 戰鬥頁認得自訂技能名稱

戰鬥頁以 `/api/skills/{id}` 取技能名稱，自訂技能不在內容庫，會顯示成 `skill_ws_…`。解法（純前端）：試玩建立戰鬥時把 `check.card`（技能卡片，id 與技能 ID 相同）放進卡片快取（`primeSkillCard`），戰鬥頁就顯示中文名與消耗。

## 4. 驗收條件（2.1）

1. **vitest 涵蓋編輯流程的狀態（選項、回上一步、檢查結果顯示）** — 通過。`client/src/workshop/workshop.test.ts`：
   - 選項→草稿：`building a skill step by step from the real options > walks 衝鋒＋傷害＋擊退 from an empty draft using only the offered choices`（用後端真實 `options` 回應，只用提供的選項，從空草稿一路組到與 `charge_full.json` 相同）、`only offers rarities and effects that the options contain`、`choosing options writes the draft`（`switching category drops…`、`switching the shape replaces…`、`removes and reorders effects, and enforces the effect limit`、`clearing a dotted field…`、`changing the skeleton keeps only the name`、`selects the only offered choice by itself`）。
   - 步驟與回上一步：`editor state: steps, going back, check results > opens on the first unfinished step…`、`goes back to earlier steps and forward again`、`keeps the step you are on while editing, and falls back when it disappears`、`a finished skill is viewed from its last step…`、`replacing the draft … forgets the old options and check`。
   - 檢查結果顯示：`shows the check result in plain Chinese`、`lists unfinished steps without nagging about the optional ones`、`budget display > shows 70.7% as an acceptable skill…`、`marks weak and over-budget skills with a hint…`、`explains the rarity rule in the check result`。
   - 另有：暫存（`browser storage` 2 個）、試玩請求與法力提醒（`try it out` 4 個）、YAML（`advanced YAML editing` 4 個，含匯出檔讀回、錯誤中文訊息、巢狀效果原樣通過）。
2. **PM 用瀏覽器：從零組衝鋒＋傷害＋擊退、看到預算百分比、裝上試玩施放一次、匯出 YAML** — 實作者已用瀏覽器窗格走過：開頁、依下列步驟組出「衝鋒擊退」，檢查面板顯示 **70.7%・合格**（與 3F-1 報告一致）、技能卡片正確；裝上試玩進入靶場戰鬥，技能列顯示「衝鋒擊退　AP 2・冷卻 2 回合」；「← 回到技能工坊」回到工坊且草稿還在；隨機一個與 YAML 編輯（含壞 YAML 錯誤訊息）正常。**尚未由實作者實際在戰鬥畫面中施放，也未實際點下載按鈕**（施放的後端路徑已由 3F-1 的 `test_try_out_a_custom_skill_cast_it_and_replay_the_log` 驗證）；請 PM 依第 6 節驗收。
3. **check.py 全過** — 通過（ruff、format、mypy、lint-imports、pytest、client install／typecheck／test 全部通過；後端沒改）。另 `corepack pnpm -C client build` 成功。

## 5. 修改既有檔案的原因

沒有修改既有測試。既有檔案改動：`App.tsx`（畫面切換加入工坊）、`StartScreen.tsx`（`onWorkshop` 入口）、`BattleScreen.tsx` 與 `EndPanel.tsx`（可選的 `exitLabel`／`restartLabel`，不傳時與原本完全相同）、`useSkillCards.ts`（`primeSkillCard`）、`styles.css`（附加 `ws-*` 樣式）。`client/package.json`／`pnpm-lock.yaml` 新增相依 `yaml@2.8.1`（進階 YAML 編輯解析用；沒有它就只能收 JSON）。

## 6. PM 瀏覽器驗收步驟

先 `uv run trpg serve`（可用 `corepack pnpm -C client build` 後直接開 http://127.0.0.1:8000/，或另開 `corepack pnpm -C client dev` 開 http://127.0.0.1:5173/）。**若 8000 埠被舊的 serve 佔用，工坊會顯示 Method Not Allowed／Not Found（舊程序沒有工坊 API），請先關掉舊的再啟動。**

組「衝鋒＋傷害＋擊退」（和 3F-1 報告的範例相同，預期 70.7% 合格）：

1. 首頁按「進入技能工坊」。
2. **骨架**：點卡片「位移」→ 按「下一步」。
3. **基本設定**：技能名稱填「衝鋒擊退」；種類「主動技」已自動選好，AP 填 2；類別點「武器技」，出現的武器需求點「近戰武器」；縮放屬性點「力量」；階級填 2 → 「下一步」。
4. **形狀**：點「單體」，射程填 4 → 「下一步」。
5. **效果**：在「新增一個效果」依序點「衝鋒」、「傷害」、「推擊」（三個效果依序出現，推擊的距離填 2；傷害不填倍率就是武器傷害 ×1）→ 「下一步」。
6. **條件**：不用選 → 「下一步」。
7. **代價**：「冷卻」填 2 → 「下一步」。
8. **稀有度**：點「稀有」。
9. 右側「即時檢查」應顯示「合法」、`70.7%・合格`、技能點數 14／可用預算 19.8、最低稀有度「稀有」，下方有技能卡片預覽。想看過弱／過強：把稀有度改「普通」會出現 3 項違規；把推擊距離調成其他值或加冷卻看預算條變化。回上一步：點步驟列任一已完成的步驟，或「← 上一步」。
10. **裝上試玩**（右側第二個面板）：主角 build 選「位移流」（預設第一個）、「要換掉哪一個技能」選「颶風踢」（不換會加在空格；位移流主動技已滿 6 個時會被拒絕並顯示原因）、地圖維持「靶場」、對手「木樁」→ 按「裝上試玩」。
11. 進入戰鬥後技能列第一格是「衝鋒擊退」；走到木樁前 4 格內，點技能再點木樁施放。戰鬥記錄應出現衝鋒、命中、推開。想離開按左上「← 回到技能工坊」，回來草稿還在。
12. **匯出**：右側最下面「下載 YAML」，瀏覽器會下載 `skill_ws_e9737f7780.yaml`（內容與 3F-1 報告範例相同，`provenance.origin: workshop`）。
13. 其他：「隨機一個」、重新整理頁面（草稿還在）、頁面最下方「進階：直接編輯 YAML」打字即時檢查。

## 7. 待 PM 決定

1. **JSON 還是 YAML 才算「直接編輯」**：為了解析 YAML 新增相依 `yaml@2.8.1`（體積小、無相依）。若不想加相依，可改只收 JSON（文字區仍可顯示 YAML 但只接受 JSON 貼回）。
2. **「單選值是物件」的欄位名單寫死在前端**（`shape`、`condition`）。後端 `FieldSpec` 沒有標記；新增這類欄位時前端要同步改，建議 Phase 4 前讓後端在 `FieldSpec` 加一個旗標。
3. **選填整數不預設**：傷害倍率不填＝武器傷害 ×1（後端預設）。必填的整數才補範圍最小值。若希望傷害預設就填 1000 之類的「建議值」需要後端提供。
4. **換骨架會清空其他欄位**（保留名稱，有確認）；沒有「復原」。
5. **試玩時主角的法力上限無法事前得知**（`BuildSummary` 沒有法力欄位）：先建立戰鬥再比對，不夠時在面板停住讓使用者選擇；被放棄的戰鬥留在伺服器記憶體。若要事前提示，需後端在 `builds` 回傳法力上限。
6. **自訂技能名稱顯示靠前端快取**（`primeSkillCard`）：重新整理戰鬥頁後（目前戰鬥本來就不支援重新整理續玩）名稱會退回技能 ID；若之後要支援續玩，後端的 `/api/skills/{id}` 需能查到戰鬥內的自訂技能。
7. **重新整理一律回首頁**：草稿保留，但畫面不記得你在工坊（避免把人困在工坊）。可改成記住畫面。
8. **匯出不要求合法、試玩要求完全合法**（沿用 3F-1 決定 #4）；網頁沿用，沒有「略過預算檢查也試玩」的選項。
9. **選項名稱顯示的是後端中文名**；技能卡片預覽、點數明細表的欄位名（基礎、形狀×、對象×、條件×）為前端自訂。
10. **未做瀏覽器自動化測試**：前端測試環境是 node（沒有 jsdom 與 React 測試函式庫），元件以純函式（reducer、草稿操作、顯示邏輯）測試覆蓋，畫面互動靠 PM 瀏覽器驗收。
