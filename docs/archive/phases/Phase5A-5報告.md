# Phase 5A-5 完成報告：API 與前端地點圖畫面

> 實作者：implementer agent（2026-11-02～03）。規格：`docs/phases/Phase5計畫.md` 第 11 節（先寫入規格、commit `85d1ec2e`，當時是第 10 節；合併 main 的 5B-2 後 5B-2 是第 10 節、本段改為第 11 節，「之後各段規格」改為第 12 節）。
> 動到的檔案：`src/trpg/api/`（新 `world.py`、`world_schemas.py`、`world_presenter.py`、`routes/world.py`；`app.py`、`state.py` 小改）、`src/trpg/world/` 小改（`state.py` 加 `generated_skills`、`battle.py`、`town.py` 各 2～3 行）、`tests/api/test_world_api.py`、`tests/world/test_generated_skills.py`、`client/`（新畫面、首頁入口、型別、`openapi.json`、`schema.d.ts`）。沒有動引擎、roguelite、`trpg-run` 與戰鬥紀錄格式。

## 1. 交付

| # | 項目 | 檔案 | commit |
|---|---|---|---|
| 1 | 5A-5 詳細規格 | `docs/phases/Phase5計畫.md` 第 11 節 | `85d1ec2e` |
| 2 | 世界角色帶生成技能（創角的組合器技能進戰鬥、換技能認得） | `src/trpg/world/{state,battle,town}.py`、`tests/world/test_generated_skills.py` | `a2b02ec4` |
| 3 | 大世界 API、本機存檔、OpenAPI 重產 | `src/trpg/api/world*.py`、`routes/world.py`、`app.py`、`state.py`、`tests/api/test_world_api.py`、`client/openapi.json`、`client/src/api/schema.d.ts` | `8ef1efca` |
| 4 | 前端：角色畫面、地點圖、右側面板、首頁入口、換技能元件共用 | `client/src/screens/WorldScreen.tsx`、`client/src/world/*`、`client/src/styles/world.css`、`App.tsx`、`StartScreen.tsx`、`run/loadout.ts`、`run/LoadoutEditor.tsx` | `d5b492dc`、`c46c92dd` |
| 5 | 合併 main（5B-2）、解計畫衝突 | `docs/phases/Phase5計畫.md` | `e7662bd8` |
| 6 | 本報告 | `docs/phases/Phase5A-5報告.md` | 最後一筆 |

## 2. API 清單（`/api/world`）

| 方法與路徑 | 內容 |
|---|---|
| `GET /api/world/characters` | 角色列表（ID、名稱、等級、區域、所在地點） |
| `POST /api/world/characters` | 建立角色（201）：`name`（1～12 字）、`weapon`、`keywords`（2 個）、`race`、`origin`、`seed`（選填）。和一輪開局同一套函式（`new_keyword_run`＋`with_race`／`with_origin`），站在雲嶺霧渡鎮 |
| `GET /api/world/characters/{id}` | `WorldView`（先同步已結束的戰鬥：把步驟送 `fight` 回寫） |
| `POST /api/world/characters/{id}/actions` | `travel`（`to`、`hasten`）、`camp`、`retreat`、`rest`、`loadout`（`skills`）、`teleport`（`region`）；`fight` 不收（422） |
| `POST /api/world/characters/{id}/battle` | 開戰或接續：`{world, battle}`；之後用既有 `/api/battles/{id}/…` |

錯誤：角色不存在 404；動作或內容不合法 422（`WorldActionError` 的中文訊息）；戰鬥中做其他動作、沒有遭遇卻開戰 409。

`WorldView`：`character`（等級、經驗與下一級門檻、HP／法力／補給與上限、疲憊、未分配屬性點、武器與種族名、裝備與備用技能卡、欄位上限）、`map`（地點：種類、建議等級、說明、座標、目前、相鄰、不能走的原因、已清空；連線——**未發現的隱藏地點與它的連線不送**）、`here`（能不能休息／換技能、紮營問題、傳送選項、趕路與紮營花費）、`encounter`（敵人等級、戰場、天氣、日夜、陣容含精英與詞綴、撤退回哪、開場 HP、是否已開戰）、`clock`（遊戲時刻、日夜、本區天氣）、`events`（這次請求的事件句子）、`battle_id`。

**存檔**：`<存檔資料夾>/world/` 底下 `world.json`（`trpg-world/1`）、`chars/<id>.json`（`trpg-char/1`）、`log.jsonl`（`trpg-wlog/1`）。存檔資料夾＝一輪的存檔資料夾（`TRPG_SAVE_DIR` 或 `saves/`）。一把鎖＝單一寫入佇列；每個成功動作取下一個 `seq` 寫日誌，再寫角色與世界。`test_battle_writes_back_to_world` 驗證「初始快照＋日誌重播」＝存檔的角色。

## 3. 畫面流程

```
首頁「進入大世界（測試）」
  └ 角色畫面：我的角色（進入）／建立新角色（名稱、種族與出身、起始武器、2 個關鍵字——沿用一輪開局元件）
      └ 地點圖畫面（左：地點圖；右：遇敵面板、角色狀態、目前地點服務、最近事件）
          ├ 點發亮的相鄰地點 → 移動（勾「趕路」花補給、遇敵機率減半）
          ├ 遇敵 → 右側最上方陣容面板 →「開戰」→ 戰鬥畫面（沿用）→「回到地點圖」→ 勝負已回寫
          │                          └「撤退」→ 回出發地點
          ├ 小鎮：休息、換技能（沿用營火換裝元件）、傳送（去過的其他區）
          └ 野外：紮營（村落、遺跡、已清空的營地…）→ 營火中可換技能
```

- 地點圖：程式繪製（HTML 按鈕＋SVG 連線，座標＝內容的 `pos`）；種類用顏色與形狀（小鎮方塊、傳送點菱形、營地紅、精英巢穴橘＋金框、Boss 大紅、秘境綠）；目前位置白框、可走的相鄰地點金色光暈、其他變淡；已清空在小字標「已清空」；連到目前位置的連線變實線。
- 地點的說明卡用共用 `Hint`（6.5.1）：名稱、種類、建議等級、說明、能不能走（原因）。地點按鈕的左鍵是「移動」動作，所以照按鈕規則只滑過顯示、不點擊釘住。
- 遇敵陣容是一般面板（不是浮動卡），有遭遇時地點圖不能點。

## 4. 瀏覽器驗證紀錄（Claude_Browser，後端＋前端都在 8030）

`corepack pnpm -C client build` 後用 `TRPG_SAVE_DIR=<worktree>/.scratch_5a5/saves uv run trpg serve --port 8030`（`trpg serve` 直接提供 `client/dist`），預覽視窗 1600×900。

1. 首頁出現「大世界（測試）」區塊，點「進入大世界（測試）」→ 角色畫面（沒有角色）。
2. 建立：名稱「阿霧」、人類、晶冠城邦出身、火焰法杖、點燃＋標記 → 進入地點圖。右側：「阿霧　火焰法杖・人類／Lv 1・經驗 0／100・HP 40／40・法力 67／67・補給 5／10／技能：火球、烙印／雲嶺・06:31（白天）・濃霧／霧渡鎮　小鎮／休息　換技能」。地點圖 16 個地點，鶴歸崖、丹爐洞（隱藏）沒有出現；截圖確認版面（地圖、連線、霧渡鎮方塊、相鄰的渡口石階與獵戶小屋發亮）。
3. 滑過渡口石階 → 說明卡「渡口石階（營地・Lv 1）／新手任務 1（盜賊搶渡船）／點一下走過去（路上可能遇敵）」。
4. 點渡口石階 → 竹林小徑 → 雨中梯田：第三步遇敵。陣容面板：「遇敵！雨中梯田／敵人等級 2・戰場 沼澤・濃霧・白天／盜賊、盜賊、持劍弟子、青霧道童／我方：主角（開場 HP 40）＋ 2 名標準隊友／開戰　撤退」。紀錄：「走到雨中梯田。」「在雨中梯田遇到敵人！」。
5. 點「開戰」→ 戰鬥畫面（第 1／30 輪、全滅、沼澤・濃霧、先攻列出 7 名單位，右上「← 回到地點圖」）。為了節省時間，戰鬥的主角動作用頁面內 `fetch` 直接送 `/api/battles/{id}/actions`（優先用技能、其次攻擊）打到結束——戰鬥畫面本身是既有的，不是本段改的。
6. 點「← 回到地點圖」→ 這場輸了：角色回到霧渡鎮、HP 40／40、法力 52／67（照戰後）、名字旁出現「疲憊」標籤（#98）。（戰鬥結果的事件句子這次被第 5 步的偵錯 `fetch` 先同步掉了，所以紀錄沒顯示「戰鬥失敗」；正常從畫面回來會顯示，API 測試有涵蓋。）
7. 點「休息」→「在霧渡鎮休息：HP、法力回滿，補給 5。」法力 67／67。
8. 存檔資料夾的 `log.jsonl`：`travel`×3、`fight`（含整場步驟）、`rest`，`seq` 1～5。伺服器紀錄沒有錯誤。
9. **浮動卡 6.5.1**（800×600）：版面變單欄、沒有水平捲動（`scrollWidth` 785 < 800）；滑過最上方的雲頂觀 → 說明卡「雲頂觀（Boss 據點・Lv 6）／霧鎖真人／不相鄰：先走到旁邊的地點」貼齊上方、完全在視窗內（x 471～636、y 34～102）；Esc 關閉。說明卡只有一行字、不會長到要捲動，沒有「捲到底」可測；地點按鈕的左鍵是移動，照 `Hint` 的按鈕規則滑鼠不釘住（觸控點一下開關）。1600×900 同樣滑過貼齊。
10. 「換技能」（小鎮）→ 展開換裝元件：「主動 2/6・被動（含修正） 0/3・反應 0/1・姿態 0/1／火球 卸下／烙印 卸下／套用換裝」。
11. 結束時只停了自己開的 8030 伺服器。

注：預覽視窗在背景時截圖常逾時，第 3 步以後的驗證多用 `get_page_text`／DOM 查詢記錄文字。

## 5. 使用者怎麼開來玩

```bash
corepack pnpm -C client build   # 第一次或前端有改時
uv run trpg serve               # 開 http://127.0.0.1:8000 → 首頁「進入大世界（測試）」
```

角色與世界存在 `saves/world/`（刪掉這個資料夾＝重新開始世界）。

## 6. 代決（開發 PM 定，最保守預設）

| # | 事項 | 代決 |
|---|---|---|
| 5A5-1 | 帳號還沒做 | 不登入；角色用伺服器產生的 ID（`c`＋8 位十六進位），可以多個；前端用 `localStorage` 記最後一個；5E-1 改依帳號存取 |
| 5A5-2 | 世界與賽季的建立 | 第一次用到時自動建立 `s1`、伺服器亂數種子、開始時間＝當下 |
| 5A5-3 | 創角配點與名稱 | 配點照一輪開局預設（全點起始技能最常用的屬性）；名稱存在主角範本的 `name_zh`（1～12 字，只顯示用）；起始區域固定雲嶺 |
| 5A5-4 | 日誌寫法 | 讀全部＋新行原子重寫（5～10 人量足夠） |
| 5A5-5 | 戰鬥中途的進度 | 不存檔；伺服器重啟後遭遇還在，重新開戰從頭打（同種子） |
| 5A5-6 | 戰鬥畫面 | 沿用現有戰鬥畫面與 API；回到地點圖（或任何讀取該角色的請求）時才把步驟送 `fight` 回寫 |
| 5A5-7 | 地點圖畫法 | HTML 按鈕＋SVG 連線、內容的 `pos`；種類用顏色與形狀；不加新美術 |
| 5A5-8 | 生成技能 | `CharacterState.generated_skills`（同 `RunState`，舊檔照讀、格式字串不變） |
| 5A5-9 | 遇敵陣容的呈現 | 右側一般面板（不是浮動卡／對話框），避開 6.5.1 的彈出層規則 |

## 7. 待 PM 決定

1. **戰鬥結果的事件句子只給第一個同步的請求**：結算是「讀取時同步」，事件只回在觸發同步的那個回應裡；重新整理頁面剛好碰到同步時會看不到「打贏／失敗」那句（狀態本身正確）。要不要在角色上留「最近一次戰鬥結果」給畫面顯示？
2. **戰鬥中途存檔**：目前伺服器重啟會丟掉打到一半的戰鬥（遭遇還在、從頭打）；要不要照一輪的方式存步驟？
3. **屬性點分配、閃現等成長服務**（5A-4 待決 2）：畫面只顯示「未分配屬性點 N（之後的段開放）」，交 5A-6。
4. **事件（5B-1 的 `pending_event`）與情境判定（5B-2）**：地點圖目前不顯示事件卡，交 5B-5。
5. **遇敵機率不顯示**：地點說明卡沒有列遇敵機率（9.6.7 #9 只說越危險越高）；要不要顯示「危險度」？
6. 一帳號 2～3 角色的上限（#100）目前沒有限制，5E-1 做。

## 8. 檢查結果

### 8.1 交件前檢查

合併 main（5B-2，`e7662bd8`）之後：

| 檢查 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | 通過（1551 檔） |
| `mypy`（strict，1004 檔） | 通過 |
| `lint-imports` | 9 條契約全部 KEPT |
| `pytest tests/api tests/world tests/test_architecture.py -n 8` | 556 passed |
| `pytest tests/cli -m "slow or not slow" -n 8 --timeout=3000` | 180 passed |
| `npx vitest run` | 123 檔、1190 passed（含新的 `world/mapView.test.ts`、浮動卡規則檢查） |
| `corepack pnpm -C client build` | 通過 |
| OpenAPI 快照 | 重產（`scripts/export_openapi.py`＋`gen:api`），`test_openapi_snapshot` 通過 |

`C901` 沒有超標、沒有新增 `# noqa`。
