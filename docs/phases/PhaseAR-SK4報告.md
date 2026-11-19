# Phase AR-SK4 報告：前端小修（AR-SK3、SK-3b、SK-3c、WC-2b 的待決）

> 2026-11-19，實作者。規格 `docs/phases/PhaseAR-SK4計畫.md`。
> 分支 `worktree-agent-afacf6d372339edba`（worktree 原本停在 `c44b528f3`，先 fast-forward 到 main `e3e242222` 才有規格）。不 push。
> 只改前端（`client/`）與截圖；沒有改 `docs/design/`、`config/`、後端 Python、`src/trpg/skillgen`、`content/`、`scripts/wish_coverage.py`。

## 結果（一兩句）

第 1～3 項做完並有實機截圖。第 4 項重產後**不是全部都是 SK-3c 以前的變動**，而且新夾具會讓 5 個 vitest 失敗（重閃的重現案例不見了），所以**沒有 commit 新夾具**，差異與來源寫在第 4 節，交 PM 決定。

## 交付項目

| # | 項目 | 狀態 | commit |
|---|---|---|---|
| 1 | 佈置說明卡改字、不寫顏色 | 完成 | `40263d03f` |
| 2 | 佈置時滑過可放格不出格子資訊卡＋實機截圖 | 完成 | `df1881c9c` |
| 3 | 許願元素面板當場擋第二個非物理元素 | 完成 | `4ab2bee08` |
| 4 | `flashChoice.json` 重產與逐項核對 | 核對完成；**新夾具沒 commit**（見 4 節、待決 1） | 本報告 |

## 1. 各項做法

### 1.1 佈置說明卡（第 1 項）
- 左上技能說明卡的字由 `ui/ActionPanel.tsx::modeHint` 出。選目標模式的 key 是 `prep:` 開頭時（`battle/prep.ts::isPrepModeKey`），改回 `prepModeHint(N)`：「點框起來的起始區裡的一格放下（可選 N 格）。Esc／右鍵取消。」N＝這一招可放的格數（`mode.targets.tiles.size`）。
- 其他選目標模式照舊。說明句的「前 3 次」次數仍算在 `target` 那一種（同一般選目標），見待決 3。

### 1.2 佈置時的格子資訊卡（第 2 項）
- `battle/prep.ts::prepHidesTileCard(mode, tile)`：佈置選格模式、而且這一格在可放的格子裡 → true。
- `screens/battle/useTileInteraction.ts`：資訊卡控制器的 `hasContent` 先看它，是 true 就當作這格沒有內容（不出卡，釘住也不出）。滑過其他格子照舊。

### 1.3 許願元素面板（第 3 項）
- 伺服器給的元素 `max` 已經多給物理 1 格（WC-2b `menu_limits`：1 階 2、2 階起 3）。前端照這個算：物理以外的元素最多 `max − 1` 個，物理不佔名額。
- `world/wish.ts`：`physicalSlot(group, items)`（元素類、清單裡有 `physical` 才套用）、`tagRoom`（還能不能點）、`toggleTag` 多一個 `physical` 參數。沒有物理的類別照舊用總數。
- `world/WishPanel.tsx`：按鈕的 `locked` 改看 `tagRoom`；元素類旁的字改成「最多 N 個（物理另外算）」，N＝物理以外的上限（同伺服器檢查字串的「（物理另外算）」）。這句字是規格沒寫的，見待決 2。
- 2 階起照伺服器的 `max`，前端不寫死階級。

## 2. 截圖（`docs/art/shots/ar-sk4/`，10 張）

做法：
- 無頭 Chrome `--headless=new --mute-audio --remote-debugging-address=127.0.0.1 --force-device-scale-factor=1`，除錯埠 9766；量到 `devicePixelRatio = 1`，網址帶 `mute=1`。視窗用 CDP `Browser.setWindowBounds` 調成視口 1600×900 與 800×600。
- 伺服器：暫存區的啟動腳本，照 `trpg serve` 的方式 `create_app(static_dir=client/dist)`，埠 8766，存檔在暫存區。開之前兩個埠都沒人聽；結束時只停了自己起的伺服器與 Chrome，兩個埠都已關閉。
- 戰鬥：開發模式「一鍵開局」，頁面的 `window.fetch` 包一層，把建立戰鬥的請求換成 `open_plain` 種子 3、`build_skill_archer`（帶捕獸夾）。
- **地圖右緣的那張**：現有地圖的我方起始區全在左邊，實機做不出「可放格在地圖右緣」。啟動腳本在記憶體裡多加一張 `open_plain_mirror`（`open_plain` 的我方、敵方起始區對調，其他不變），可放格變成 (9, 3)。沒有改任何檔案。
- 許願：開發模式建一個角色，啟動腳本多一條暫存路由把任務幣設成 20、把入門期當作已選定（`opening=None`），才能在主城打開許願池面板。只為了截圖，沒有 commit。
- 最近鄰放大：暫存區的 `zoom.html`（canvas `imageSmoothingEnabled = false`、CSS `image-rendering: pixelated`）在同一個無頭 Chrome 畫，是真的最近鄰。

| 檔案 | 內容 |
|---|---|
| `1-prep-hover-1600.png` | 1600×900 實機：選了捕獸夾、滑過可放格 (0, 6)：金框＋預覽＋「放在這裡」，**沒有格子資訊卡**；左上說明卡是新字（可選 1 格） |
| `1b-prep-hover-800-true1x.png` | 同上，800×600 真 1 倍（地圖自動 63%） |
| `1c-prep-hover-800-nearest-x6.png` | 上圖可放格那一塊 120×45 × 6 最近鄰 |
| `2-prep-flip-left-1600.png` | 1600×900 實機（`open_plain_mirror`）：可放格在地圖右緣 (9, 3)，「放在這裡」翻到格子左邊，沒有資訊卡 |
| `2b-prep-flip-left-800-true1x.png` | 同上，800×600 真 1 倍 |
| `2c-prep-flip-left-800-nearest-x6.png` | 上圖那一塊 125×45 × 6 最近鄰 |
| `3-prep-other-tile-card-1600.jpg` | 對照：佈置模式滑過不能放的格子，資訊卡照舊（「草地・高度 0・可通行」） |
| `4-wish-fire-locks-others-1600.png` | 1 階許願池：點了火焰後，其他非物理元素當場變灰；物理沒變灰；「最多 1 個（物理另外算）」 |
| `5-wish-fire-plus-physical-1600.png` | 再點冰霜（沒反應）、再點物理：已選「火焰、物理」 |
| `6-wish-fire-locks-others-800-true1x.png` | 同 4，800×600 真 1 倍 |

`2-prep-flip-left-1600.png` 的左上說明卡收成「?」：是既有的「每種說明句只完整出現前 3 次」（`opHints`），那時已經出現過 3 次。

## 3. 測試與檢查

| 檢查 | 結束碼 |
|---|---|
| `npx tsc --noEmit -p client`（每個 commit 前、交件前） | 0 |
| vitest 相關（交件前：`src/battle src/ui src/world src/screens src/run src/render/prepTipSide.test.ts`，237 檔、2818 個） | 0 |
| `corepack pnpm -C client build`（每個 commit 前、交件前） | 0 |

新增測試：
- `battle/arSk4Prep.test.ts`（5）：說明卡定案字與 N、不寫顏色、只有 `prep:` 換字；可放格不出卡、其他格與非佈置模式照舊、控制器 `visible`。
- `world/arSk4Wish.test.ts`（6）：只有元素類有物理時套用；1 階擋第二個非物理、物理還能點、拿掉後能換；先點物理不佔名額；2 階（max 3）兩個非物理＋物理；沒有物理規則照舊；面板字。

沒有改既有測試。沒有改 Python，沒跑 ruff、mypy、pytest。

## 4. `flashChoice.json` 重產（第 4 項）

`uv run python scripts/export_flash_choice_fixture.py`（結束碼 0）。重產後 68 行加、951 行刪。結構比對（每個欄位逐一比）共 83 處，**全部在兩組「真的出題」的重閃**；其他組（base、rows、transform、stance、llm）、主角、`bases` 都一樣。

### 4.1 差在哪裡
- **`reflash`（RR-2 重現案例：第一個開發起始包、種子 2 打到營火，「灼燃・燃燒爆」重閃第 1 格）**：
  - 選項 4 → 1。舊的是 3 張「比原本弱」＋1 張整招等於現在（#160 例外格）；新的只剩 1 張「每場一次」（`cost_once`：冷卻改成每場 1 次、傷害 2d6 → 2d8，比原本強）。
  - 跟著不見的：`weaker_foot_zh`、每張的 `weaker_tag_zh`、`terms.power_up`。
- **`reflash_major`（同一招重閃第 3 格）的第 4 張**：橋接關鍵字「帶電」→「冰凍」，名稱「雷鳴・燃燒爆」→「霜結・燃燒爆」，條件「本回合已施放過雷電技能」→「目標帶有冰凍」，傷害 1d12 → 1d4、額外傷害 1d4 → 3d4；卡片 id 跟著變。

### 4.2 從哪裡來（照每一版的產生腳本重產比對）
做法：`git archive <commit>` 把那一版的 `src`、`content`、`scripts`、夾具匯出到暫存區，用那一版的腳本重產（只讀 repo）。

| 版本 | 結果 |
|---|---|
| main `2c261d5aa`（SK-3c 合併前） | `reflash` 已經是 1 個選項；`reflash_major` 第 4 張還是「雷鳴」 |
| main `5f1b0562c`（WC-2 合併前，含 SK-3c、SK-3d） | 和上一列完全相同 |
| WC-2 `fa36aa56c`（第 2 項） | 同上 |
| WC-2 `69335a213`（第 4 項） | 和現在完全相同 |
| main `2fb1f09d9`（WC-2b 合併前） | 和現在完全相同 |

- `reflash` 的 4 → 1：**SK-3c 以前**就有（同 SK-3c 報告待決 4），來自 SK-1 合併（4.3）。
- `reflash_major` 第 4 張：**不是 SK-3c 以前**，是 WC-2 的 `f71c3c8df`（第 3 項：被動的自身周圍、被動觸發算單體）造成的。SK-3c、SK-3d、WC-2b 都沒影響。

### 4.3 `reflash` 4 → 1 的來源
在 main 第一父鏈（FL-1h 夾具 `d2811c3da` 之後到 `2c261d5aa`，258 個）上二分，只看 `reflash` 的選項數：
- 最後一個還是 4：`03bfa4027`（docs，4.1.28）。
- 第一個變成 1：`c492b7fec` **Merge SK-1**（距離條件、移動折扣、閃現側向變化與新的小變化模板、先製造的評分、施放順序變化，#166）。
- 新的那張是 `cost_once`（每場一次）模板，符合 SK-1 的 `44621a8b7`「flash side variations and new minor templates」。SK-1 合併後同一個種子打到營火時的重閃選項就不一樣了，屬於 SK-1 的預期變動（沒有再往 SK-1 分支內二分）。

### 4.4 為什麼沒 commit
- 新夾具讓 5 個 vitest 失敗：`run/fl1hFlashWords.test.ts` 4 個（較弱重閃的 `weaker_foot_zh`、3 張 ▼「比原本弱」、#160「和現在一樣」那張、找不到現在的卡）、`run/fl1jFlashWrap.test.ts` 1 個（「1d4 火焰」斷行，現在是 3d4）。
- 前 4 個測的正是「重現案例」：種子 2 現在打出來的重閃已經不是 #160 那種情況，夾具換掉就沒有東西可以測。要改測試或換種子，都不是照產生腳本重產能做完的事，規格也沒寫，所以照最保守的做法：**夾具維持原樣**（仍是 FL-1h 那一版，開發頁與 vitest 都照舊），重產的檔案留在暫存區沒 commit。見待決 1。

## 5. 新增 `# noqa`
沒有（沒改 Python）。

## 待 PM 決定（規格沒寫到、我先採保守做法的地方）

| # | 事項 | 我的做法 | 其他選項 |
|---|---|---|---|
| 1 | `flashChoice.json` 重產後重閃的重現案例不見了、5 個 vitest 失敗；而且 `reflash_major` 那張的差異來自 WC-2（不是 SK-3c 以前） | 夾具不換，只寫核對結果 | 甲：換新夾具並改那 5 個測試（#160 那幾個要改成別的情況或拿掉）；乙：產生腳本換一個種子或起始包，找回「3 弱＋1 一樣」的重閃再重產（後端腳本，`scripts/` 不在這段範圍） |
| 2 | 許願元素旁的上限字 | 改成「最多 N 個（物理另外算）」，N＝物理以外的上限（沿用伺服器檢查字串） | 照舊寫伺服器的 `max`（1 階會寫「最多 2 個」，但第 2 個非物理點不下去） |
| 3 | 佈置說明句的「前 3 次」 | 算在一般選目標（`target`）那一種：玩家選過 3 次目標後，佈置的說明句也收成「?」 | 佈置另開一種說明句次數（`OpHintKind` 加一種） |
| 4 | 右緣翻邊截圖用的地圖 | 現有地圖做不出可放格在右緣，用記憶體裡對調起始區的 `open_plain` 拍（沒改檔） | 之後有起始區在右邊的地圖時重拍 |

## 開發 PM 裁定（2026-11-19）

合併：main（--no-ff）。第 1～3 項接受；截圖交美術 PM 驗收。

1. 重閃夾具：選第二種。讓產生腳本換種子或起始包，把 #160 的重閃案例找回來再重產，5 個測試照原本的意思保留。交回本段 agent 補做。
2. 「最多 N 個（物理另外算）」：先照這樣做，用字請美術 PM 和玩法 PM 確認。
3. 佈置說明和選目標共用「前 3 次」計數：照現狀，請美術 PM 看要不要分開計次。
4. 起始區在右邊的真地圖出現後再重拍：接受。
