# Phase WP-3b 報告｜許願池美術驗收修正、三個許願池圖示、「都不拿」統一

> 實作 agent，2026-11-13（Opus 5.5）。依據：`docs/art/WP-3驗收.md`（必修 1、可修 1～6）、`docs/art/Q版小圖示-第7批HUD.md` 13.7（三個圖都用候選 A）、`docs/art/Q版小圖示-許願池-審查.md`；追加：玩法 PM 定案「一輪和世界日誌也統一用『都不拿』」（專案 PM 轉達）。
> 沒動：`src/trpg/skillgen/`、重閃相關 api、`client/src/run/CampfireSkillCare.tsx`、`client/src/screens/RunFlashPending.tsx`（RR-2 在改）；兩個檔裡都沒有「跳過」鈕，不用停下來。
> commit：`2d61da343`（都不拿）、`f98c70669`（三個圖示）、`8be352fcb`（選單乙案與可修 1～6）、`b067b4f1f`（分頁圖對齊、下固定區同高、截圖）、本報告與上手筆記一筆。

## 1. 逐條對照（`docs/art/WP-3驗收.md`）

| 條 | 做法 | 檔案 | 截圖 |
|---|---|---|---|
| **必修 1**（乙案，所有寬度一樣） | 選單格只放圓章 20＋名字（挑中再加實心「第 N 個」），說明改用 `<Hint text={k.description_zh}>` 浮動卡；格子改 `aria-disabled`（不用 `disabled`），挑滿兩個、不能許時滑過照樣打得開說明卡（點了不動）。**最後挑中的那一個**的說明放在下固定區最上面（`PickedNote`：「第 N 個」＋16 圓章＋名字：說明；拿掉後退回前一個，`wish.ts` 的 `pickedFocus`）。這塊兩個分頁都預留兩行高（沒有時空白），切分頁、挑關鍵字時外框與下固定區都不跳（實量 800 下固定區 124.8 不變）。欄數看面板寬：寬版 4 欄×3 列、窄版 3 欄×4 列 | `world/WishPanel.tsx`、`world/wish.ts`、`styles/world-panel-wish.css` | `a1600-menu-picked.jpg`、`a800-menu-picked.jpg`、`a800-menu-bottom.jpg`、`a1600-hint.jpg`、`a1600-hint-full.jpg`（挑滿時滑過不能點的格）、`a800-hint.jpg`、`a800-picked-poisoned.jpg`（最長的說明在 800 兩行放得下） |
| 可修 1 | `.ui-popup-hud > .ui-popup-body { scrollbar-gutter: stable }`（共用，大世界所有 HUD 彈窗面板一起）。實量「回到地點圖」：改前 1600 1023 → 1008、800 509.6 → 494.6；改後兩個分頁都是 1008／494.6 | `styles/theme.css` | `wp3b-fix1-tabswitch.png` |
| 可修 2 | 視窗高 ≤ 820（捲動區可視高 < 約 450）時守池人對話泡收成標題旁一行（同 800）。1040×624 實量：輸入框底 395.4 < 捲動區底 414.1，整個看得到；分頁內容 168.8／可視 147.9（只剩退款說明要捲） | `styles/world-panel-wish.css` | `b1040-text.jpg`、`a1040-text.jpg`、`wp3b-fixes-before-after.png` |
| 可修 3 | `run.css` 的 `.run-offer-card.off-route` 拿掉虛線，改成 1px 紫色細框（`box-shadow: inset`，不佔位；選中時換成選中框），「偏離路線」標籤照舊。一輪與任務三選一共用 | `styles/run.css` | `b1600-result.jpg`、`a1600-result.jpg`、`wp3b-fixes-before-after.png` |
| 可修 4 | `.wish-lead`、`.wish-picked-desc` 加 `text-wrap: pretty`（格子裡的說明已經搬走，原本「…或被引／爆。」的情況不會再出現在格子裡）。這次的環境 800 點數不夠時說明句一行放得下，沒有重現「一。」 | `styles/world-panel-wish.css` | `wp3b-fixes-before-after.png`（改前「爆。」）、`a800-picked-ignite.jpg` |
| 可修 5 | `.wish-kw` 加 `align-content: start`（乙案後每格只有一行，本來就不會被拉開，規則照加） | 同上 | `wp3b-fixes-before-after.png` |
| 可修 6 | 不能許時下固定區「得到 → 新 技能三選一」那列灰階＋0.55（`DiffRows` 是 5 格一列的格線，「得到」固定是最後一列，用 `:nth-last-child(-n + 5)`；共用的 `FlashChoiceParts` 沒改）；任務幣「不夠」照舊琥珀 | 同上 | `poor-b800-text.jpg`、`poor-a800-text.jpg`、`wp3b-fixes-before-after.png` |

### 1.1 可視高與內容高（實機 DPR 1，「從選單挑」分頁、挑了兩個）

| | 1600×900 改前 | 1600×900 改後 | 800×600 改前 | 800×600 改後 |
|---|---|---|---|---|
| 外框 | 720×632 | 720×502.3 | 493.3×413.8 | 493.3×413.8 |
| 上固定區 | 156.8 | 156.8 | 104 | 104 |
| 下固定區 | 94 | 137.5 | 86 | 124.8 |
| 分頁內容可視高 | 357.3 | 184 | 199.8 | 158.5～161 |
| 「從選單挑」內容高 | 503.8（1.41 屏） | **175.8（一屏）** | 798.8（4.0 屏） | **193.8（1.2 屏，要捲 33）** |
| 「說出願望」內容高 | 168.8 | 168.8 | 168.8 | 168.8 |

- 1600：12 個一屏放完，外框從 632 降到 502（面板高照最高的那一頁）。
- 800：從 4.0 屏降到 1.2 屏，一次看得到 3 列（9 個），第 4 列要捲 33px。差的這一截是下固定區多了「挑中的說明」兩行（約 39px）。窄版已經把格子上下內距 5 → 4、說明字 12px／行高 1.45；要真的一屏放完的做法見第 5 節待決 1。

## 2. 三個許願池圖示（13.7，都是候選 A）

- `client/src/render/qIcon/hud.ts`：照樣張另開一張表 `WISH`（`wish_text` 16、`wish_menu` 16、`wish_left` 15，`grp: "gen"`），連同 `wishStar`、`speech`、`SKY`；**不進 `ICON`／`list()`**，`entryOf` 改成 `ICON[id] ?? WISH[id]`。`_b`、`_c` 沒搬。
- 接線：分頁「說出願望」「從選單挑」的 `icon` 是 `<HudBare id="wish_text|wish_menu" px={16} />`（圖在字前、間距 6、左緣 +11）；**上緣**置中是 +9.5，`.wish-panel .pnl-tab > .pnl-ico { position: relative; top: 0.5px }` 取整成 +10（圖與分頁的小數部分相同，畫出來永遠差整 10px）。籌碼「本週還能許」`icon={<HudBare id="wish_left" px={15} />}`，照任務幣籌碼（左 +6、上 +5.5、圖字間距 5，實量籌碼寬 129.3）。標題列沒畫圖。
- **指紋**（同一個無頭 Chrome `--disable-gpu --mute-audio`、同一個 FNV 與行格式）：開發頁 `hud-gallery.html?set=wishhash`（新增；`set=wish` 是實際底色上 ×1／×4 的對照）輸出
  ```
  wish_text | 16:f948c249/0dda48e6
  wish_menu | 16:6be283c1/b3fced1d
  wish_left | 15:f29350f0/b0d1dbef
  ```
  和 13.7、`qicons_shots.py --hash wish` 推薦三行逐字相同。
- **第⑦批其他圖不變**：樣張 `qicons_shots.py --hash hud` 55 行（樣張沒改）；遊戲端 `hud-gallery.html?set=hash` 53 行和樣張 55 行扣掉沒搬的 `pin_b`、`pinbadge_b` 逐字相同（`diff --strip-trailing-cr` 結束碼 0）。注意：沒加 `--disable-gpu` 時遊戲端和樣張的指紋全部對不上（GPU 光柵化不同），比對一定要加。
- 截圖：`wp3b-icons-true1x-x4.png`（實機 1600 的分頁列兩種選中、籌碼 9 與 2，真 1 倍 ×4）、`wp3b-tabs-narrow-x4.png`（只剩圖示＝第 2 級、短名＝第 1 級 ×4，800 的籌碼＋分頁列 ×2）、`a1600-text.jpg`、`a800-text.jpg`。窄版只剩圖示是在實機頁面裡把分頁列寬設成 90px（第 1 級用 150px）讓 `PanelTabs` 自己重量出來的，實際面板寬碰不到。

## 3. 「都不拿」統一（玩法 PM 定案，專案 PM 轉達）

改了的玩家看得到的字（程式識別字、事件名 `skipped` 等都沒改）：

| 地方 | 改前 | 改後 |
|---|---|---|
| 一輪完整技能三選一的鈕 `screens/RunCompleteOffer.tsx` | 跳過 | 都不拿 |
| 一輪完整技能說明 `run/flash.ts` `COMPLETE_INTRO` 第 3 句 | 三張都不想要可以跳過，技能不變。 | 三張都不想要可以都不拿，技能不變。 |
| 同上 `completeSkipText()` | 目前：跳過（技能不變）。 | 目前：都不拿（技能不變）。 |
| 升級的標題 `screens/RunLevelUp.tsx` | 選一張新技能（可跳過） | 選一張新技能（可以都不拿） |
| 升級的鈕 | 確定（跳過技能） | 確定（技能都不拿） |
| 戰後裝備三選一說明 `screens/RunGearOffer.tsx` | …；不想換就跳過。選完之後才是升級。 | …；不想換就都不拿。選完之後才是升級。 |
| 戰後裝備三選一的鈕 | 跳過（不換裝備） | 都不拿（不換裝備） |
| 世界日誌：給三選一 `api/world_story_view.py` | {來源}給了技能三選一：先選一招（或跳過）。 | {來源}給了技能三選一：先選一招（或都不拿）。 |
| 世界日誌：都不拿（非許願池） | 跳過了{來源}給的技能{，退還 N 任務幣}。 | {來源}給的三招都沒拿{，退回 N 任務幣}。 |
| 世界動作被拒 `world/step.py` | 還有任務給的技能三選一沒有選：先選一招或跳過 | 還有任務給的技能三選一沒有選：先選一招，或都不拿（和許願池 `blocked_zh` 同一句） |

- 許願池自己的鈕（`都不拿（退回 N 任務幣）`）與日誌（`許願池給的三招都沒拿，退回 N 任務幣（次數照扣）。`）是 TXT-2 的定稿字，沒動。
- 裝備三選一（戰利品）也照「一律」改了；如果玩法 PM 的意思只限技能三選一，改回兩個字串即可（待決 3）。
- 預測會變的測試：只有 `tests/api/test_wish_pregen.py` 的「先選一招（或跳過）」一行；實際也只有它（`grep` 全部 `tests/`、`client/src` 沒有其他斷言或快照用到這幾句）。另外補了非許願池來源都不拿的兩句斷言、`wp3bWish.test.ts` 鎖住一輪三個畫面不再有「跳過」。

## 4. 檢查（交件前）

| 指令 | 結束碼 |
|---|---|
| `corepack pnpm -C client exec vitest run`（wp3bWish、wp3Wish、qIconHud、containerNameRule、floatCardRule、panelTabsMeasure、pnl1aPanelKit、sharedPopup、run/flash、narrowSkillLayout、imeEnterRule，11 檔 168 項；開發中另跑過 21 檔 388 項的 CSS 掃描與一輪相關） | 0 |
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client build` | 0 |
| `uv run ruff check src tests/api/test_wish_pregen.py`、`ruff format --check`（改到的 3 檔） | 0、0 |
| `uv run mypy src/trpg/api/world_story_view.py src/trpg/world/step.py` | 0 |
| `uv run lint-imports` | 0 |
| `uv run pytest -q -n 4 tests/api/test_wish_pregen.py tests/api/test_wish_api_wp2.py tests/world/test_opening_choice.py tests/api/test_world_events_api.py`（60 項） | 0 |

沒跑全量 `scripts/check.py`。

### 4.1 瀏覽器相容（MDN／caniuse）

- `scrollbar-gutter: stable`：Chrome、Edge 94+、Firefox 97+ 支援；Safari 18.2 起支援，更舊的 Safari 忽略（切分頁時「回到地點圖」照舊會移 15px，不影響操作）。macOS 預設的浮動捲軸本來就不佔寬，有沒有這條都一樣。
- `text-wrap: pretty`：Chrome、Edge 117+ 支援；Safari 26 起支援；**Firefox 不支援**，照一般折行（最後一行可能只剩一兩個字，字不會被切）。

## 5. 待 PM 決定（照最保守的做法做了）

1. **800 的選單還要捲 33px**（1.2 屏）。原因是「挑中的說明」放進下固定區後多了兩行。可以的做法：(a) 接受；(b) 窄版 4 欄，「第 N 個」改成格子角上的小數字章（要美術 PM 給樣子）；(c) 窄版挑中的說明改放在選單下面（捲動區裡），下固定區不預留。現在是 (a)。
2. **「說出願望」分頁的下固定區也預留兩行空白**（沒有挑中的說明可寫）。不留的話切到「從選單挑」時外框會長高 39px（1600 選單一屏放得下，面板高跟著內容）。要不要在這兩行放一句說明（例如文字許願時關鍵字由池子聽出來）是字，交玩法 PM。
3. 「都不拿」連**戰後裝備三選一**也改了（「一律」）；若只限技能三選一，改回兩個字串。
4. 下固定區只寫**最後挑中的那一個**的說明（規格寫「挑中的那一個」）；兩個都挑時，第 1 個的說明要滑過格子看。1600 其實放得下兩個各一行（最長的「中毒」在 1600 要兩行），要不要兩個都寫請美術 PM 定。
5. 可修 1 的 `scrollbar-gutter` 加在共用的 `.ui-popup-hud > .ui-popup-body`：大世界所有 HUD 彈窗面板（公告板、任務、成長、隊伍、選變體等）沒捲軸時右邊也會多留 15px。只想許願池用的話改成 `:has(.wish-panel)`。

## 6. 實機截圖（`docs/art/shots/WP-3b/`，全部實機 DPR 1，網址 `?mute=1`，無頭 Chrome `--mute-audio --disable-gpu`）

做法：暫存區的小啟動檔 `create_app(llm=MockLlmProvider(), static_dir=…)`，存檔在暫存區，一個入門期已過的主城角色站在守池人正下方朝北（任務幣 9；點數不夠的另一份 2）；頁面裡 `POST /api/world/llm {enabled:true}`，首頁「繼續」→ 按 E。**改前**是同一個 worktree 把 5 個檔暫時換回 `f1629b431` 建的前端（`dist-before`，伺服器相同），建完立刻換回。埠：8793～8796（伺服器）、5194（vite 開發頁）、9573（Chrome，只綁 127.0.0.1），開之前 `netstat -ano` 確認都沒人用；交件前用自己記的 PID（14876、28800、59396、20892、33528、63300）關掉，六個埠都沒在聽。整張截圖是 JPG 80，放大與拼圖是 PNG（最近鄰）。結果畫面是 Mock 提議器的技能。

| 檔 | 內容 |
|---|---|
| `a1600-menu-picked.jpg`、`a800-menu-picked.jpg` | **必修 1 乙案**：挑了冰凍（第 1 個）、撞擊（第 2 個），下固定區寫撞擊的說明 |
| `a1600-menu-empty.jpg`、`a800-menu-bottom.jpg` | 1600 沒挑；800 捲到底（第 4 列＋退款說明） |
| `a1600-hint.jpg`、`a1600-hint-full.jpg`、`a800-hint.jpg` | 滑過格子出說明卡；挑滿兩個時滑過不能點的格也有 |
| `a800-picked-poisoned.jpg`、`a800-picked-ignite.jpg` | 最長的說明（中毒）在 800 兩行；點燃 |
| `a1600-text.jpg`、`a800-text.jpg` | 分頁列與籌碼（說出願望選中，三個新圖示） |
| `wp3b-icons-true1x-x4.png` | 圖示真 1 倍 ×4（分頁兩種選中、籌碼 9／2） |
| `wp3b-tabs-narrow-x4.png` | 只剩圖示（第 2 級）、短名（第 1 級）×4；800 籌碼＋分頁列 ×2 |
| `a1600-iconsonly.jpg`、`a1600-iconsonly-fit.jpg` | 上面那張的整張（分頁列寬手動設 90／150） |
| `wp3b-fix1-tabswitch.png` | 可修 1 改前／改後：切分頁時標頭 |
| `wp3b-fixes-before-after.png` | 可修 2、3、5、6 改前／改後拼圖（可修 4 的改前「爆。」在可修 5 的改前格） |
| `b1600-text.jpg`、`b1600-menu-picked.jpg`、`b800-text.jpg`、`b800-menu-picked.jpg` | 改前（舊選單 1.41／4.0 屏） |
| `a1040-text.jpg`、`b1040-text.jpg` | 可修 2 改後／改前 |
| `a1600-result.jpg`、`b1600-result.jpg`、`a800-result.jpg` | 可修 3 改後／改前（結果三選一）；800 結果 |
| `a800-after-skip.jpg` | 按「都不拿（退回 2 任務幣）」後重開面板，左下日誌「許願池給的三招都沒拿，退回 2 任…」 |
| `poor-a800-text.jpg`、`poor-b800-text.jpg`、`poor-a1600-text.jpg`、`poor-b1600-text.jpg`、`poor-a800-menu.jpg`、`poor-b800-menu.jpg` | 點數不夠（可修 6 改後／改前） |
