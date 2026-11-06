# Phase RT-3 報告：等待動畫（C 羽毛筆羊皮紙）

實作者，2026-11-05。分支 `worktree-agent-a78e97016bd372c16`（從 main `14a2a3f7` 開始，含 RT-1、UI-E1b、6L-2、6F-6），沒有 push、沒有合併。
依據：`docs/archive/art/等待動畫.md` 第 1、3、4、5、6 節，`docs/art/區域主題移植需求.md` 第 3 節，`docs/art/AU-2檢查.md` 待決 3，UI-E1b 待決 10，以及專案 PM 追加的「下緣漸隱再加深加高」。

## 1. 逐項做了什麼

### 1.1 四個場合各一種畫法（`client/src/render/waitArt.ts`）

同一套道具：羊皮紙、羽毛筆、墨、封蠟、金邊。四個場合的構圖、大小、節奏都不同。

| 場合 | 大小 | 一輪 | 畫法 | 完成 | 失敗 |
|---|---|---|---|---|---|
| `skill` 技能生成 | 120×120 | 3.2 秒 | 羊皮紙由上往下展開 → 羽毛筆沿卡框描一圈 → 畫中間的圖樣（淡淡上色）＋兩行小字線 → 區域色封蠟由大壓小 → 卡框內鑲金邊。還沒好就換一張紙重畫，換一個圖樣（5 種：螺旋、五芒星、符文三角、火焰波、新月）。圖樣照請求編號雜湊挑，下一輪一定不同 | 卡面淡入 0.3 秒：深藍底、金框、圖樣轉金色、封蠟 | 停住、變灰 |
| `judge` 事件判定 | 80×80 | 1.4 秒 | 羊皮紙小卡上的沙漏：先翻轉半圈，再讓區域色（`seal`）的沙流下，有一道沙流和往下掉的沙粒 | 沙漏停住（成功時事件卡換成判定結果卡，接 6C-ART3 的擲骰） | 停住、變灰、加重試鈕 |
| `npc` NPC 聊天 | 64×30 | 0.9 秒 | 羊皮紙泡泡，尾巴指向頭像。羽毛筆依序點出三個墨點「……」 | 回覆一到直接換成文字（泡泡拿掉） | 停住、變灰、加重試鈕 |
| `retell` 多講一點 | 104×64 | 2.6 秒 | 皮面書翻開，左頁寫滿；羽毛筆沿右頁一行行寫，寫滿就翻頁；區域色書籤 | 闔書：右頁往左蓋上，剩封面金框加封蠟 | 停住、變灰 |

- 墨色、封蠟、點綴讀 RT-1 的 `region_themes`（`ink`、`seal`、`wait_fx`），經 `waitPalette()` 轉成調色盤，畫法裡沒有寫死區域。
  - 荒原的 `ember`：飄起的火星；主城的 `crystal`：紫晶光閃爍；雲嶺 `none`：沒有點綴。
  - 拿不到區域（`null`、空字串、不認得的區域）時用 hub。
- 程式繪製（canvas），不用外部素材。
- 確定性：畫面只由「時間 t、種子、狀態」決定。種子是 `fmix32(seedOf("wait#請求編號"))`，點綴位置用 `lcg`。不用 `Math.random`，畫法裡也不讀時鐘。

### 1.2 元件（`client/src/ui/WaitScene.tsx`、`waitScene.css`）

- 用 canvas 加 requestAnimationFrame，元件卸載就停。畫布依 `devicePixelRatio` 放大，最多 3 倍。
- 時間只拿來算相位。開發用的 `?anim=0.1` 會放慢動畫，倍率用 playback 的 `devAnimFactor`；句子照真實時間輪替。
- 區域：`region` 沒傳時用目前畫面的主題（`useCurrentTheme`）。事件判定傳 `event.region`，NPC 聊天傳 `field.region`。
- 屬性 `data-scene`、`data-status`、`data-region` 給測試和截圖腳本讀。

### 1.3 短句（`content/ui/narration_wait.yaml`、`client/src/ui/waitNarration.ts`）

- 內容照第 3 節：每個場合一組，加一句失敗句；`rotate_ms: 4000`、`long_ms: 8000`。
- 第一句照請求編號挑（確定性），之後每 4 秒換下一句。
- 等超過 8 秒後，提示句（`long`）和一般句子交替出現：第 8 秒提示句、第 12 秒一般句、第 16 秒提示句……見待決 2。
- `{name}` 換成 NPC 的名字。失敗時一律顯示「說書人停下了筆，再試一次？」。
- 不呼叫 LLM。前端在 build 時用 `?raw` 匯入，壞掉的欄位退回內建句子。
- Python schema `src/trpg/content/ui_wait.py`（`WaitNarration`）已登記進 `registry.py`，由 `trpg content check` 驗證。檢查內容：
  - 四個場合剛好齊全；
  - 不用古風詞（墨滴、宣紙、毛筆、蘸墨；「羽毛筆」不算）；
  - 只有 npc 能用 `{name}`；
  - `long_ms` 不比 `rotate_ms` 短；
  - 不接受拼錯的欄位。
- 檔案位置：規格寫 `content/narration_wait.yaml`，派工說「必要時改 content/ui」，所以放在 `content/ui/`（見待決 1）。

### 1.4 減少動態（各場合分開）

- 每個場合固定畫自己那一刻的靜態版（`STATIC_T`），不跑 rAF。
  - 技能生成：畫好的羊皮紙圖樣，含封蠟、金邊；完成時直接出卡，不淡入。
  - 事件判定：停住的沙漏，上下各一半沙，沒有沙流。
  - NPC 聊天：三個墨點並排，羽毛筆不動。
  - 多講一點：寫了一半的書頁，羽毛筆停在行中。
- 點綴停在固定一刻，不動。
- 句子照常換，但不淡入淡出（`.wait-scene.still`、`:root[data-reduced-motion="true"]`）。
- 實機：`localStorage trpg.reducedMotion=on` 時，預先生成的等待彈窗顯示靜態版（`rt3_live_capitalreduced_*`）。

### 1.5 接上現有的等待點

| 場合 | 等待點 | 做法 |
|---|---|---|
| 技能生成 | 6L-2 的預先生成等待提示（閃現、重閃、機遇的 `event_solve`） | `PregenWaitDialog` 的 `DialogFrame` 文字換成 `<WaitScene scene="skill">`。等 400ms 才出現、可以取消、取消＝不送動作，這些都沒變。好了的時候，如果動畫有出現過，先收成卡框、卡面淡入 0.3 秒再送出；減少動態時直接送出。完成時取消鈕停用 |
| 事件判定 | 情境判定的「擲骰」（`/situation/answer`） | `SituationForm` 按下擲骰後，在說書人對話框下方靠右放沙漏。成功時事件卡換成判定結果卡；請求失敗、卡片還在時進入失敗狀態，重試鈕＝再送一次 |
| NPC 聊天 | 聊天的「說」（`/chat`） | `NpcPanel` 的對話紀錄最後一列：NPC 頭像加羊皮紙泡泡。回覆一到就拿掉、換成文字；失敗時變灰，重試鈕＝用同一句話再送一次 |
| 多講一點 | **找不到等待點** | 「多講一點」是前端直接展開後端已經給的 `more_zh`（`StoryDialog`、`NarratorSubtitle`、`StoryBlock`），不會等伺服器。所以這個場合只有畫法、短句、聲音和開發頁，沒有接進正式畫面（待決 3） |

- 按鈕照舊不能點：送出中 `busy` 的停用規則沒變。

### 1.6 等待聲（AU-2 檢查待決 3）

- 0.7 秒的規則保留，聲音依場合不同。由 `useWaitSound` 掛在 `WaitScene` 上，動畫還在等的時候才放；完成、失敗、卸載就停。

  | 場合 | 音效 id | 間隔 |
  |---|---|---|
  | 技能生成 | `ui_wait_quill` 羽毛筆刮紙：帶通粉紅雜訊往下掃，加 5 個細喀聲，0.3 秒後再刮第二筆 | 1.6 秒 |
  | 事件判定 | `ui_wait_sand` 沙漏細沙：每秒 60 個 4.2 kHz 的劈啪，加很輕的帶通雜訊，1.1 秒 | 1.4 秒（和一輪同長） |
  | NPC 聊天 | 不出聲 | — |
  | 多講一點 | `ui_wait_page` 說書人翻頁：比 `ui_page` 長一點、低一點 | 2.6 秒 |

- 參數表：`content/audio/sfx.yaml` 的 `ui_ink_wait` 改成這三筆。介面音從 20 個變成 22 個。合成照 AU-2 的確定性積木。
- 舊的全域墨痕聲 `useInkWaitSound(busy)`（任何伺服器等待超過 0.7 秒都會放）已經拿掉。走路、傳送這類一般等待不再出聲（待決 4）。
- 預先生成的彈窗晚 400ms 才出現，所以聲音延遲傳 `700 − 400`，仍然是從開始等算起 0.7 秒。
- **一律靜音驗證**：無頭 Chrome 加 `--mute-audio`，網址加 `?mute=1`，沒有用系統指令放音檔。開發頁不初始化音效。聲音只用參數和波形驗證（vitest：三筆都算得出波形、峰值在 0.005～1 之間、同種子逐點相同、三筆長度不同）。

### 1.7 順手修：捲動區上下緣漸隱

- **上緣（新）**：捲動內容最前面加一塊 sticky 色塊（`::before`），用負的下邊距，不佔版面。
  - 還沒捲時 `opacity: 0`，不蓋第一行。
  - 捲下去後，`PopupFrame` 在 `.ui-popup-body` 標 `data-scrolled="1"`（`onScroll`，直接寫 dataset，不重繪），色塊才顯示。
- **下緣（專案 PM 追加：加深加高）**：16px → 32px，漸層從 45% 起是實色底色（原本是線性漸到底色）。
- 上下兩邊用同一個漸層。實測 800×600 設定面板：
  - `rt3_fade_800_mid`（捲到一半）：上緣切半的「音效」那一行完全淡掉，「音樂」那一行清楚；下緣切半的「提示」也看不到被切的字。
  - `rt3_fade_800_top0`（沒捲）：上緣不蓋第一行，下緣切半的「跟系統／開／關」那一行完全淡掉（加深前還隱約看得到）。
  - `rt3_fade_800_end`（捲到底）：最後一行照常清楚。
- 套用範圍和 UI-E1b 一樣：`hud` 面板（含設定）與詢問視窗（`dialog`）。

### 1.8 開發頁（`client/wait-gallery.html`、`src/dev/waitGallery.tsx`）

- 四個場合 × 三區（主城、雲嶺、灰燼荒原）並排，每格標出墨色、封蠟、點綴。
- 網址參數：
  - `scene=` 只看一個場合（放大 2 倍）；
  - `region=` 只看一區（也可以選 hub）；
  - `reduced=1` 減少動態；
  - `status=done|fail` 完成、失敗；
  - `t=` 固定畫某一刻、`line=` 固定句子的時間（逐格截圖用）；
  - `anim=0.1` 放慢 10 倍。
- 頁面上有連結可以切換。

## 2. 截圖（`docs/art/rt3_*`）

**開發頁（四個場合 × 三區、減少動態、完成、失敗、短句）**

| 檔名 | 內容 |
|---|---|
| `rt3_skill_3regions`、`rt3_judge_3regions`、`rt3_npc_3regions`、`rt3_retell_3regions` | 每個場合 × 主城、雲嶺、荒原（放大 2 倍）：墨色藍黑、黑褐、紅褐；封蠟紫、朱紅、橘；主城紫晶光、荒原火星 |
| `rt3_skill_t150`～`t3000`（6 張） | 技能生成一輪：展開 → 描框 → 圖樣 → 封蠟 → 金邊 |
| `rt3_judge_t100`～`t1300`（4 張） | 沙漏翻轉中 → 沙往下流 |
| `rt3_npc_t100`～`t800`（4 張） | 一點、兩點、三點、羽毛筆抬起 |
| `rt3_retell_t500`～`t2400`（4 張） | 一行行寫 → 翻頁 |
| `rt3_reduced_all` | 減少動態：四個場合各自的靜態版 × 三區 |
| `rt3_done_all` | 完成：卡面淡入後、沙漏停住、闔書 |
| `rt3_fail_all` | 失敗：變灰、失敗句、重試鈕 |
| `rt3_line2_all`、`rt3_long_line_all` | 第 4 秒換下一句；超過 8 秒的提示句（金色） |
| `rt3_anim01_retell_a／b` | `?anim=0.1`：真實時間過了約 5 秒、10 秒，動畫才走到第一、二行（沒放慢時已經過好幾輪）；句子照真實時間換到提示句 |

**實機**（API 8355、vite 5355，用自己的存檔目錄 `scratchpad/rt3/saves`）

- 固定狀態的做法：用 `scratchpad/rt3/inject.js` 在頁面載入前包住 `fetch`。
  - 世界畫面塞一個有情境判定的事件（storyGallery 的假資料），以及一位「這裡的人」；
  - `/api/world/llm` 回 `enabled: true`；
  - `/pregen/wait`、`/situation/answer`、`/chat` 先延遲再送出。
- 伺服器沒有這個事件、NPC，所以判定和聊天最後會回錯誤，剛好拍到失敗狀態。畫面和元件都是正式的 `WorldScreen`。

| 檔名 | 內容 |
|---|---|
| `rt3_live_capital1600_*`、`rt3_live_capital800_*` | 主城（1600、800）：`event_card` 事件卡；`skill_wait_a／b` 預先生成等待彈窗（技能生成，1.4 秒、2.6 秒）；`skill_cancelled` 取消後彈窗關閉；`judge_wait`／`judge_fail` 事件判定的沙漏與失敗；`npc_wait`／`npc_fail` 聊天泡泡與失敗 |
| `rt3_live_cloud1600_*` | 雲嶺（實際傳送過去）：同上，墨色、封蠟換成雲嶺的 |
| `rt3_live_ashenfixed1600_*` | 荒原：固定狀態，把 `field.region` 改成 `ashen_waste`。還沒去過荒原的小鎮，不能傳送，所以地圖仍是雲嶺，HUD 主題和等待動畫是荒原的 |
| `rt3_live_capitalreduced_*` | 減少動態開著的實機：彈窗裡是靜態版（畫好的圖樣） |
| `rt3_fade_800_top0`、`rt3_fade_800_mid`、`rt3_fade_800_end` | 800 寬設定面板：下緣遮罩、上下緣遮罩、捲到底 |
| `rt3_float_1600_pinned`、`rt3_float_800_pinned` | 6.5.1 浮動卡實測，釘住的狀態 |

拍主城、雲嶺之前都先關掉開場對話框（`close.js`）。

## 3. 驗證

- **排版煙霧檢查**：`/?dev=1&anim=0.1`，先 `localStorage.clear()`，再跑 `__layoutSmoke.runCase('RT-3')`。伺服器帶 `TRPG_DEV_ROUTES=1`。
  - 1600×900、1040×624、800×600 三個尺寸都是「全 PASS」，每個尺寸 10 項。
  - console 有一則 BattleScreen 的 `flushSync` 警告，原本就有，不是這段造成的。
- **6.5.1 浮動卡實測**（功能列「技能」鈕的說明卡）：

  | 步驟 | 1600×900 | 800×600 |
  |---|---|---|
  | 滑過觸發元素 → 卡片出現（貼齊鈕的上方） | ✓（707～821） | ✓（436～550） |
  | 從鈕滑進卡片 → 不關 | ✓ | ✓ |
  | 在卡片內捲動 → 不關 | ✓（卡片 106px，沒有可捲的內容，只確認不關） | ✓ |
  | 點一下釘住 → 滑出去不關 | ✓ pinned | ✓ pinned |
  | Esc → 關閉 | ✓ | ✓ |

- **交件前的完整檢查**：
  - client 全部 vitest：243 個檔、**2718 個全過**，結束碼 0；
  - `tsc --noEmit` 結束碼 0；
  - `corepack pnpm -C client build` 結束碼 0；
  - Python `tests/content` 加 `tests/test_architecture.py`：**2702 passed**；
  - 改到的 Python 檔：`ruff check`、`ruff format --check`、`mypy` 都通過。
- Python 用主資料夾的 `.venv` 從 worktree 執行（pytest 的 `pythonpath = ["src"]` 會優先讀 worktree 的 `src`）。中途 `uv run` 在 worktree 自動建了空的 `.venv`，已刪除。
- `corepack pnpm exec` 第一次跑時，從本機快取裝了 `client/node_modules`（downloaded 0），沒有新增相依。

## 4. 檔案清單

**新增**

- 內容：`content/ui/narration_wait.yaml`
- Python：`src/trpg/content/ui_wait.py`、`tests/content/test_wait_narration.py`
- 前端：
  - `client/src/render/waitArt.ts`
  - `client/src/ui/WaitScene.tsx`、`waitScene.css`、`waitNarration.ts`
  - `client/src/audio/waitSounds.ts`
- 開發頁：`client/src/dev/waitGallery.tsx`、`client/wait-gallery.html`
- 測試：`client/src/ui/waitScene.test.ts`
- 截圖：`docs/art/rt3_*`
- 本報告

**修改**

- 內容與 Python：
  - `content/audio/sfx.yaml`：`ui_ink_wait` 改成 `ui_wait_quill`、`ui_wait_sand`、`ui_wait_page`
  - `src/trpg/content/registry.py`：登記 `ui/narration_wait.yaml`
  - `tests/content/test_audio_sfx.py`：介面音 20 → 22
- 前端：
  - `client/src/audio/uiSounds.ts`：介面音清單
  - `client/src/world/useWorldSounds.ts`：拿掉 `useInkWaitSound`
  - `client/src/screens/WorldScreen.tsx`：預先生成的完成收尾；拿掉全域墨痕聲
  - `client/src/world/PregenWaitDialog.tsx`、`pregen.ts`（`pregenRequestId`）
  - `client/src/world/EventCard.tsx`：事件判定
  - `client/src/world/NpcPanel.tsx`：NPC 聊天
  - `client/src/ui/PopupFrame.tsx`：`data-scrolled`
  - `client/src/styles/theme.css`：上下緣漸隱
- 前端測試：`client/src/audio/uiSounds.test.ts`、`synth.test.ts`（介面音 22 個）；`client/src/ui/uiE1b.test.ts`（下緣 32px）

**沒碰**

- 人物繪製（inkDoll、inkStyle 只匯入 `seedOf`、`lcg`；portrait）；
- `src/trpg/llm`、`content/llm`；
- 白板、新手任務內容；
- 伺服器欄位與 API。

**沒有 commit**

- `scratchpad/rt3/`：CDP 腳本、注入腳本、測試存檔、截圖原檔；
- `client/vite.rt3.config.mts`：實機驗證用的暫時設定。

## 5. 測試數

- vitest 新增 `waitScene.test.ts`，共 **27 個**：
  - 四個場合的挑選、大小與節奏；
  - 預先生成彈窗用技能生成；事件判定、NPC 聊天接到正確的元件；
  - 墨色依區域，三區都不同；拿不到區域退回 hub；失敗時變灰；
  - 確定性：同輸入相同、不同時間不同、`Math.random` 換成會丟例外的函式也畫得出來、圖樣下一輪一定換；
  - 減少動態：任何時間畫面都一樣、四個靜態版各自不同、完成直接出卡、CSS 不淡入；
  - 短句：內容、第一句確定性、4 秒輪替、8 秒提示句、`{name}`、失敗句、壞檔退回；
  - 等待聲：對應表、NPC 不出聲、0.7 秒規則、三筆波形；
  - 上下緣遮罩；
  - RT-3 的檔案不用 `Math.random`、不用原生 `title=`。
- 改過的 vitest：`uiSounds.test.ts`、`synth.test.ts`、`uiE1b.test.ts` 各 1 個。
- 浮動卡規則（`floatCardRule.test.ts`）照舊全過：新元件沒有新的彈出層，也沒有 `title=`。
- Python 新增 `test_wait_narration.py`，共 13 個：載入、登記、正確範例，以及 10 種錯誤範例。`test_audio_sfx.py` 改 1 個。

## 6. 待 PM 決定

以下都照最保守的做法先做完了：

1. **短句檔的位置**：規格寫 `content/narration_wait.yaml`，派工說「必要時改 content/ui」，所以放在 `content/ui/narration_wait.yaml`。另外照守則 4（內容要有 pydantic schema）加了 `src/trpg/content/ui_wait.py` 和登記一行，這超出「只改 client/」的範圍。要不要搬回頂層？
2. **超過 8 秒後的輪替**：規格只寫「超過 8 秒換提示句」。我的做法是提示句和一般句交替（第 8、16、24 秒提示句，第 12、20 秒一般句），不是一直停在提示句。
3. **「多講一點」沒有等待點**：它展開的是後端已經給的 `more_zh`，不等伺服器。畫法、短句、聲音都做好了，在開發頁看得到。要接進正式畫面，需要另開段，例如讓「多講一點」改成向 LLM 要補充。
4. **一般等待不再出聲**：舊的全域墨痕聲（任何伺服器等待超過 0.7 秒）照 AU-2 檢查待決 3「改成接在等待動畫上」拿掉了。走路、傳送、商店這類沒有等待動畫的等待，現在都不出聲。
5. **事件判定的位置**：規格寫「說書人對話框右邊」。判定卡的說書人框佔滿整列寬，所以沙漏放在說書人框**下方、靠右**，在輸入框上方。要不要改成和說書人框同一列（框變窄）？
6. **技能生成的完成收尾會延後 0.3 秒送出**：預先生成好了的時候，如果動畫有出現過，先等卡面淡入 0.3 秒才送出動作；減少動態時不等。只出現過不到 400ms、動畫沒露面的情況不等。
7. **技能圖樣的元素色**：規格寫「照技能的元素色淡淡上色」，但等待提示的請求（`PregenWaitRequest`）只有技能 ID，沒有元素，而且這段不新增伺服器欄位。所以元件留了 `tint` 參數，目前用區域墨色淡淡上色。要接元素色，可以從畫面上已有的技能卡讀。
8. **失敗狀態的觸發**：預先生成的等待本來就是失敗時降級（`catch → null`，照常送出），所以技能生成在正式畫面不會出現失敗狀態，只有開發頁看得到。事件判定和聊天在請求出錯時進入失敗狀態，重試＝再送一次。情境判定是「第一次送出即定案」，請求出錯時伺服器有沒有定案，由伺服器決定，前端只是重送。
9. **沙漏翻轉時略超出羊皮紙卡**：翻到 90 度時，木框對角會碰到卡的左右緣，約 2px（`rt3_judge_t100`）。
10. **三個等待聲的音量**是原型值（gain 10／10／8，和舊的墨痕聲同一級），等使用者試聽。
11. **荒原的實機截圖用固定狀態**：測試角色還沒去過荒原的小鎮，不能傳送，所以 `rt3_live_ashenfixed1600_*` 是把畫面資料裡的 `field.region` 改成荒原，地圖仍是雲嶺。荒原真正的墨色、封蠟在開發頁三區並排的截圖裡。
