# Phase 3-32b 報告｜重複詞條標灰、浮動卡自動檢查、召喚物模式不被自動結束回合吃掉

分支：`worktree-agent-a18dd6fdc71d3620f`（基於 `e64bbfa`）。依 `Phase3計畫.md` 第 35.2 節三項。

## 1. 交付

| 項目 | 內容 | 主要檔案 |
|---|---|---|
| 1 重複詞條標灰 | 角色面板（`UnitInfo`、裝備測試的英雄面板）的裝備說明卡：沒生效的詞條標灰、劃線，後面註明「和〇〇重複，沒有效果」（資料來自 3-32a 的 `active`／`duplicate_of`；數值類遞減到 0 權重但沒有 `duplicate_of` 時註明「同種詞條疊太多條，這條沒有效果」）。裝備比較（裝備測試的物品清單）：每一列顯示「換上後沒效果：…（和〇〇的「…」重複）」與「換上後恢復生效：…（〇〇的這條原本和〇〇的重複，換下後恢復生效）」 | `client/src/gear/affixStatus.ts`、`ui/PartTip.tsx`（新增 `lines`）、`ui/gear/ItemList.tsx`、`ui/gear/HeroGearPanel.tsx`、`ui/UnitInfo.tsx` |
| 2 浮動卡自動檢查 | `ui/floatCardRule.test.ts`（vitest，用 `import.meta.glob` 掃 `client/src/**/*.tsx` 與 `styles.css`）。新增共用元件 `ui/Hint.tsx`（取代原生 `title=`），並把所有違規改過去（見第 3 節） | `client/src/ui/Hint.tsx`、`ui/floatCardRule.test.ts` |
| 3 召喚物模式不被自動結束吃掉 | 網頁工作階段 `BattleSession.awaits_player`：主角只剩 `EndTurn` 但還有可操控（非圖騰）的召喚物時，不自動結束，停下來等玩家按「結束回合」；前端技能列提示文字改為「行動點數用完了，但還能調整召喚物的模式（0 AP）；準備好後按「結束回合」。」 | `src/trpg/api/sessions.py`、`client/src/battle/summons.ts`（`hasControllableSummon`）、`battle/skillTray.ts`、`screens/BattleScreen.tsx` |

附帶修正：3-30b 的共用浮動卡（`useFloatCard` 的 `FloatCard`，技能卡與部件說明框）原本沒有最大高度與卡內捲動（只有格子資訊卡 `HoverFloat` 有），違反 6.5.1 第 7 條；`styles.css` 補上 `max-height: calc(100vh - 8px)`、`.float-card-body` 內捲動（`overflow-y: auto; overscroll-behavior: contain`）。另外技能卡在「現在不能用」時，卡片最上方多一行「現在不能用：〇〇」（取代原本 `.skill-slot` 的原生 `title`）。

## 2. 自動結束回合的處理方式（第 3 項）

- 自動結束發生在 **API 工作階段** 的 `awaits_player`（用 `has_only_end_turn` 判斷），不是前端。所以這項不是「只動前端」：後端改一個條件，**只影響網頁工作階段**；引擎的 `has_only_end_turn`、CLI、模擬、`replay` 都不變（`LOG_FORMAT` 不變、紀錄與重播不受影響）。
- 條件：輪到主角、只剩 `EndTurn`，且主角在場上有 `summon_problem(...) is None` 的召喚物（排除圖騰與已倒下的）。這時 `awaiting` 維持 `"action"`，`legal_actions` 只有 `end_turn`；玩家仍可送 `set_summon_mode`，再按結束回合。
- 保守取捨：有召喚物時，主角每個回合都會在 AP／移動用完後停下來等玩家按「結束回合」（多按一下），不管玩家是否真的想切模式。這是「提示、不自動」的做法；若嫌煩，可改成「只在召喚物模式有可能需要切換時才停」，需玩法 PM 定義（見待決定 #1）。

## 3. 浮動卡 grep 盤點（第 2 項）

盤點範圍：`client/src` 所有 `title=`、`createPortal`、內聯 `position: fixed|absolute`、`role="tooltip"`／`role="dialog"`、`styles.css` 中 `position: fixed` 規則。

**改用共用元件的（原生 `title=` → `Hint`，約 40 處，分布 20 餘個檔案）**：`run/LoadoutEditor`、`run/SkillGrowthPanel`、`run/StartPicker`（武器特性、關鍵字說明）、`screens/BattleScreen`（縮放四個）、`ui/ActionPanel`（兩處方向鈕）、`ui/BattleLog`（兩處）、`ui/ChargeChips`、`ui/DialogFrame`（移動視窗鈕）、`ui/GearTotals`、`ui/Hud`（AP、移動、彈匣、源力、反應、精簡列）、`ui/ResizeHandle`、`ui/SidePanel`（展開鈕）、`ui/SkillBar`（基本動作鈕）、`ui/TurnBar`（目標與先攻晶片）、`ui/TurnControls`（移動、普攻、跑步、守護、更多動作）、`ui/workshop/CheckPanel`（合格上下限、圖示尺寸）、`ui/workshop/FieldEditor`（必填、選項說明）、`ui/workshop/StepView`。
`Hint` 是共用浮動卡（`useFloatCard`）：滑過 150ms 延遲、離開寬限與橋接區、可滑進卡片、Esc／點外面關閉、同時只開一張、貼齊觸發元素並翻轉／夾進視窗、超高卡內捲動、portal 到 body、鍵盤焦點與觸控。外框用 `display: contents`，不影響版面；停用的按鈕也能顯示（瀏覽器實測：停用的「守護」鈕）。

**直接移除（不改成 Hint）的 `title=`**，逐項理由：
- `run/OfferPicker` 的 `offer-kind-tag`：`title` 與緊鄰的可見文字（`offerTagHint`）完全相同，純重複。
- `ui/SkillBar` 的 `skill-slot`（`title={disabledReason}`）：這個元素本來就有技能卡浮動卡；原因改顯示在技能卡最上方一行。
- `ui/SkillBar` 的 `MiniSlot` 按鈕（`title="名稱（花費）"`）：同樣已有技能卡浮動卡，卡片內有名稱與花費；按鈕仍保留 `aria-label`。
- `ui/SkillIconView`、`ui/GearIcon` 的 canvas `title`：移除原生屬性，保留 `aria-label`；元件的 `title` prop 改名 `label`（純無障礙名稱，註解註明要說明請用 `Hint`／`PartTip`）。技能卡／變奏清單的圖示旁邊已有可見名稱；工坊檢查面板的「技能列大小／小圖示大小」改用 `Hint` 包住。

**白名單（測試內列出，並寫明理由）**：
- `<DialogFrame title=…>`：`title` 是對話框標題 prop，不是 DOM tooltip 屬性（共 4 個呼叫端）。
- `ui/DialogFrame.tsx`、`ui/BattleTopBar.tsx` 的 `role="dialog"`：點按鈕開關的互動對話框／頂端設定與圖例面板，不是滑過說明卡。
- 共用元件本身（`useFloatCard`、`HoverFloat`、`Hint`、`PartTip`）可使用 portal 與 `position: fixed`。
- CSS：`position: fixed` 只允許 `.float-card`、`.unit-float`、`.modal-backdrop`、`.decision-card`。
- 盤點到但**不屬於彈出卡片**、測試不管的：`.board-toasts`、`.battle-banner`（戰場提示橫幅，非說明卡）、`.more-list`／`.fallback-list`（點擊展開的選單）、`.mode-panel`、`.summon-panel`（行動面板內的 inline 面板）、`.top-popup`（BattleTopBar 的點擊面板，已在 `role=dialog` 白名單）、`.turn-chip-left`／`.ws-bar-mark`／`.zoom-controls`／`.resize-handle`（定位用的 `absolute`，不是彈出層）。

測試內容（`floatCardRule.test.ts` 6 條）：沒有原生 `title=`（`DialogFrame` 例外）；沒有 `createPortal`（共用元件例外）；沒有內聯 `position: fixed|absolute`；`role="tooltip"` 只在共用元件與用到 `FloatCard` 的檔案；`role="dialog"` 在白名單；`styles.css` 的 `position: fixed` 規則只屬白名單選擇器。

## 4. 驗收證據

- **自動檢查**：`uv run python scripts/check.py` 全過（ruff、format、mypy、lint-imports、pytest、client typecheck、vitest 71 檔 744 測試）；`corepack pnpm -C client build` 成功。另有一個全量 pytest 與其他 agent 同時跑，沒有卡住。
- **pytest**：`tests/api/test_summon_control_api.py::test_a_summoner_with_no_ap_left_is_not_auto_ended`（召喚後主角花光 AP／移動，仍是主角的回合、`awaiting == "action"`、`legal_actions` 只剩 `end_turn`、可再切換模式、結束回合後換人）。
- **vitest**：`gear/affixStatus.test.ts`（標灰與註明文字、重複／恢復生效預測、數值類不預測、同詞條換同詞條不列恢復）；`ui/floatCardRule.test.ts`；`battle/skillTray.test.ts`（`summonIdle` 提示）；`battle/summons.test.ts`（`hasControllableSummon`，圖騰不算）。
- **瀏覽器實測**（內建瀏覽器，埠 8032 自己的伺服器，結束後已停止；沒動使用者的 8000 埠）：
  - 從觸發元素滑進卡片 → 卡片內捲到最底 → 釘住 → 關閉：
    - 1600×900：移動鈕的 `Hint`：滑過 150ms 後出現、貼齊在按鈕上方、滑進卡片仍開著、點卡片釘住（黃框）、滑開仍在、點外面關閉。`3-32b-hint-pinned-1600x900.jpg`。
    - 800×600：技能卡（火焰箭）：滑過出現（含「現在不能用：AP 不足」行）、滑進卡片仍開、點卡片釘住並滑開仍在、Esc 關閉（DOM 確認卡片移除）。`3-32b-skillcard-pinned-800x600.jpg`。
    - 800×150（刻意縮矮，讓卡片超出視窗；800×600 下技能卡高度 180px 不會超出）：卡片最大高度 142px，滾輪捲到最底（`scrollTop + clientHeight = scrollHeight`）、卡片未關閉、頁面沒有跟著捲。`3-32b-skillcard-scrolled-bottom-800x150.jpg`。
  - 停用的按鈕（AP 用完的「守護」）滑過也會出現 `Hint`。
  - 裝備比較標灰：兩枚同樣「擊殺時回 1 AP」的戒指，英雄面板戒指 2 的說明卡顯示灰色劃線詞條與「和戒指 1 的…重複，沒有效果」；物品清單各列顯示「換上後沒效果／換上後恢復生效」。`3-32b-gear-duplicate-gray-1600x900.jpg`。
  - 有召喚物時 AP 用完不自動結束：dev 起始包「喚靈（骷髏）」，召喚骷髏後花光 AP 與移動，仍是「行動中：A 冒險者」，技能列提示顯示「行動點數用完了，但還能調整召喚物的模式…」，點「待命」切換成功（0 AP），再按結束回合才換人。`3-32b-summon-no-auto-end-800x600.jpg`。
  - 版面：所有 `Hint` 外框為 `display: contents`，戰鬥畫面、起始頁、裝備頁目視無版面位移。

## 5. 待 PM 決定

1. **自動結束的範圍**：目前「有任何可操控的召喚物，就在 AP 用完時停下來等玩家按結束回合」，不管需不需要切模式。若想更少打擾（例如只在召喚物剛被召喚或有敵人進入某範圍時停），要玩法 PM 定義規則；也可加一個「略過」設定。
2. **自動結束只改網頁工作階段**：CLI、模擬與我方 AI 代打仍照舊（引擎不變）。若希望「自動代打」也考慮切模式，是 3-33c #3 的範圍，這裡沒動。
3. **`Hint` 不做「點一下釘住」**（`pinOn: "never"`）：因為多數 `Hint` 包的是有動作的按鈕，點擊要執行動作，沿用 `PartTip pin={false}` 的先例。其餘規則（延遲、橋接、可滑進、Esc、單開、翻轉、捲動、鍵盤）都有。若 PM 要求所有卡片都能釘住，需決定按鈕類的釘住手勢（例如長按或右鍵）。
4. **比較預測只看非數值類（同 id 只生效 1 條）**：數值類的遞減（100／50／25／0%）與「誰比較強」由伺服器裁決，前端不預測，所以預測只說「會重複」，不說哪一條有效；已穿上後的實際結果以英雄面板（伺服器的 `active`／`duplicate_of`）為準。若要精準預測，需要後端提供「假設換上」的試算端點。目前沒有獨立的「裝備比較」畫面（物品清單即比較處），也沒有跨戰鬥的背包比較。
5. **`FloatCard` 補上最大高度與卡內捲動**是規格 6.5.1 第 7 條要求、但 3-30 只在格子資訊卡做到；本段順手補，改動全站共用卡片的外框 CSS（`display: flex; max-height: calc(100vh - 8px)`）。卡片比視窗還高時仍會蓋住觸發元素（沒有「選上方或下方較大的一側再限高」），保守起見沒做；實際內容（技能卡約 180–400px）在 800×600 不會遇到。
6. **白名單內的 `role="dialog"` 面板**（`DialogFrame`、`BattleTopBar`）與 `.top-popup`、`.more-list` 等點擊選單沒有改成共用浮動卡：它們是互動式面板而非說明卡。若 PM 的 6.5.1 意圖包含這些（例如要 Esc／點外面關閉的統一行為），需另排一段整理。
