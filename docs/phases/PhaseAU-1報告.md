# Phase AU-1 報告：音訊核心

分支 `worktree-agent-a0cc6f6e69a196bbb`，基於 main `4dffd028`。只改了 `client/`，沒有動 `src/`、`client/src/render/`、`client/src/battle/`。規格見 `docs/art/音效與音樂方案.md` 第 3、4 節。

使用者的決定（專案 PM 轉達）：音樂選純西式奇幻管弦；外部下載「先不要」；預設音量主 70、音效 80、音樂 50、環境 60。

## 做了什麼

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 原生 Web Audio，不加套件 | 新目錄 `client/src/audio/`。`package.json` 沒有改 | 6254f7b3 |
| 2 | 四軌混音 | 節點串法：每一聲 gain → 軌 gain（音效／音樂／環境）→ 主 gain → highshelf → lowshelf → 限幅 compressor → 輸出。實際音量 = 主 × 軌（`mix.ts` 的 `effectiveGain`） | 6254f7b3 |
| 3 | 設定面板、靜音、`Shift+M`、localStorage | 戰鬥「版面」面板最下面加「聲音」區：四條滑桿、各自的靜音鈕、減少刺耳音效、切到其他分頁時靜音。`Shift+M` 切換全部靜音。設定存在 `trpg.audio.v1`，讀寫都包 try/catch，壞資料改用預設值 | 6254f7b3、484933fb |
| 4 | 自動播放解鎖 | 使用者第一次 pointerdown、keydown 或 touchend 時才建立 AudioContext。在那之前呼叫 `play` 直接丟掉，不建立任何節點。AudioContext 真的進入 running 才拿掉監聽，因為單按 Shift 這種按鍵不算使用者手勢 | 6254f7b3 |
| 5 | ducking | `audio.duck()` 回傳釋放函式；可以重疊呼叫，全部釋放才回復。音樂和環境壓到 ×0.7（−30%），音效不變。React 用 `useDuck(active)`。已經接上 `NarratorSubtitle`（字幕淡出前）和 `StoryDialog`（對話框在畫面上時） | 6254f7b3 |
| 6 | 同時播放上限 | 同一個 id 最多 3 個，全部最多 16 個，超過就不放新的（`dropped`）。同一個 id 在同一個 `at`（取到毫秒）只放一聲，之後每多一次音量 +15%，最多 1.45 倍 | 6254f7b3 |
| 7 | 背景分頁靜音 | 用 `visibilitychange` 把主 gain 壓到 0。設定裡可以關掉 | 6254f7b3 |
| 8 | 減少刺耳音效 | 開啟後：最大音量 −6 dB（主 gain ×0.501）；highshelf 5 kHz −12 dB；lowshelf 120 Hz −9 dB；限幅門檻從 −1 dB 降到 −12 dB。關閉時兩個 shelf 是平的，只留 −1 dB 的防爆音限幅 | 6254f7b3 |
| 9 | 延遲載入架構 | `manifest.ts`：依區域的清單 `AUDIO_MANIFEST`（現在是空的）。`pickFormat` 用 `canPlayType` 挑格式，probably 優於 maybe，同級時 ogg/Opus 優於 m4a/AAC。`RegionLoader.load(region)` 先下載，解鎖後才解碼。失敗一律吞掉，那個 id 就不出聲；同一個區域不會重複載入 | 6254f7b3 |
| 10 | 播放 API | `play(id, { at, variantKey, track })` 回傳 `"played" \| "merged" \| "dropped" \| "silent"`。id 對不到音源時回傳 `silent`。AU-2 用 `audio.registerSound(id, SoundSource)` 掛音源，`SoundSource.start(ctx, out, at, variantKey)` 回傳長度（秒） | 6254f7b3 |
| 11 | dev 頁 | `client/audio-gallery.html`：上方是正式的設定元件；下方是 OscillatorNode 測試音（單音、連放 6 次、同一時間點 5 次、全部各 5 次、3200 Hz 鋸齒波、55 Hz 方波、音樂軌、環境軌、不存在的 id、模擬 ducking），還有即時的節點數值和播放結果紀錄 | 4a7ed11c |

其他說明：
- **確定性**：沒有用 `Math.random`，也沒有讀牆上時鐘。排程只看 `AudioContext.currentTime`，聲音結束的判斷也用這個時間。
- **地圖鍵衝突**：`world/hud.ts` 的 `hudKey` 原本把 `Shift+M` 轉小寫，會當成 `M` 打開地圖。現在 `Shift+M` 回傳 null，`hud.test.ts` 加了一條測試。
- **實測時順手修的兩個問題**（484933fb）：
  - 焦點在滑桿或勾選框上時，`Shift+M` 原本被當成「正在打字」而失效。現在只有文字輸入框才算打字。
  - 在 800×600，「版面」面板加了聲音區後會超出視窗底部，也會被底部操作列和縮放鈕蓋住。原因是 `.bhud-right` 的 z-index 13 低於底部的 14，而且 `max-height: calc(100vh - 80px)` 沒有扣掉面板頂端的 109px。改法：在 `styles/battle-hud.css` 把 hud-a 的 `.top-popup` 設成 `max-height: calc(100vh - 120px)`；面板打開時用 `.bhud-right:has(.top-popup)` 把 z-index 提到 20。

## 檔案清單

新增：
- `client/src/audio/types.ts`：最小 Web Audio 介面、`SoundSource`、`PlayOpts`
- `client/src/audio/settings.ts`：設定、預設值、正規化、localStorage 存讀
- `client/src/audio/mix.ts`：混音純函式（主 × 軌、ducking、減少刺耳）
- `client/src/audio/voices.ts`：同時播放上限、同一時間點合併
- `client/src/audio/engine.ts`：`AudioEngine`
- `client/src/audio/manifest.ts`：區域清單、`pickFormat`、`RegionLoader`
- `client/src/audio/index.ts`：全站共用的 `audio`、`play`、`installAudio`、`isMuteShortcut`
- `client/src/audio/useAudio.ts`：`useAudioSettings`、`useDuck`
- `client/src/audio/AudioSettingsPanel.tsx`、`client/src/audio/audio.css`：設定面板的「聲音」區
- `client/src/audio/fakeAudio.ts`：測試用的假 AudioContext 和 Storage
- `client/src/audio/audio.test.ts`
- `client/audio-gallery.html`、`client/src/dev/audioGallery.tsx`

修改：
- `client/src/main.tsx`：呼叫 `installAudio(window, document)`
- `client/src/ui/LayoutPanel.tsx`：加上 `<AudioSettingsPanel />`
- `client/src/world/StoryParts.tsx`：字幕和對話框呼叫 `useDuck`
- `client/src/world/hud.ts`、`hud.test.ts`：`Shift+M` 不開地圖
- `client/src/styles/battle-hud.css`：面板高度與疊放順序

## 測試

- `src/audio/audio.test.ts` 共 21 個測試：
  - 四軌乘法（預設值、引擎節點、音量夾在 0～100）
  - 靜音（全部靜音、單軌靜音、`Shift+M` 判斷、背景分頁）
  - 解鎖前不出聲（不建立 context 和節點、`installAudio` 第一次手勢才解鎖並移除監聽、未知 id）
  - 每個 id 的上限、總上限
  - 同一 hitAt 合併（含毫秒取整）
  - 減少刺耳的上限與濾波
  - ducking
  - 設定存讀（含讀寫失敗、資料損壞）
  - 延遲載入（格式選擇、失敗降級、不重載、空清單）
- `hud.test.ts` 多一條斷言。
- 交件前跑過一次 client 全部 vitest：**212 個檔案、2319 個測試全過**；`corepack pnpm -C client build` 結束碼 0；`tsc --noEmit` 沒有錯誤。

## 實機（preview，前端 5344、後端 8344）

- 驗證用的設定是 `client/vite.au1verify.config.ts`，沒有 commit，已刪除。
- 後端存檔目錄設在 scratchpad，沒有碰 `saves/` 和 `tmp_x`。
- 兩個伺服器都是我自己啟動的，已用 TaskStop 和自己的 PID 結束。

dev 頁實測結果：
- 解鎖前狀態欄顯示「否」，點一下之後變成 running。
- 連放 6 次：`played×3、dropped×3`。
- 同一時間點 5 次：`played、merged×4`。
- 全部各 5 次：總數停在 16。
- 不存在的 id：`silent`。
- ducking：音樂 0.350、環境 0.420。
- `Shift+M` 切換後存進 localStorage，重新整理後還是靜音。
- 打開減少刺耳：主 gain 0.351（= 0.7 × 0.501）、highshelf −12 dB、lowshelf −9 dB、限幅門檻 −12 dB。

浮動卡規則（6.5.1）：這個面板是現有的頂端列點擊式面板（`usePopupMenu`），不是滑過才出現的浮動卡。所以「滑進」測的是滑鼠移進面板後面板不關；「釘住」對應點開後在面板內操作也不關。
- **1600×900**：點開 → 滑鼠移進面板 → 捲動 → 在面板內點擊，面板都還開著 → Esc 關閉 ✔。
- **800×600**：修正前面板底部在 622px，超出 600 的視窗，而且被底部操作列蓋住 ✘。修正後底部在 588px，內容高 505、可見 478，可以在卡片內捲到底；面板蓋在操作列上面；在面板內點靜音鈕不關閉，`Shift+M` 有效且存得住，Esc 關閉 ✔。

截圖：
- `docs/art/au1_gallery.jpg`：dev 頁，減少刺耳已打開
- `docs/art/au1_settings_1600.jpg`、`docs/art/au1_settings_panel.png`：戰鬥中的「版面」面板，1600×900
- `docs/art/au1_settings_800.jpg`：800×600，修正後

借用的分頁 tab-13（原本的 8303 已經沒有伺服器）已用 desktop preset 還原大小；8388、8399、8355 都沒有碰。分頁停在 5344 的網址，那個伺服器已經關了；工具不接受 `about:blank`，所以沒有導回空白頁。

## noqa

沒有新增 noqa（前端沒有 ruff）。

## 待 PM 決定

1. **大世界沒有設定面板**：`WorldHud` 的齒輪鈕目前顯示「設定：尚未開放」。我照最保守的做法，只把聲音區放進戰鬥「版面」面板；`Shift+M` 全站都能用。要不要把大世界的齒輪接到同一個 `AudioSettingsPanel`？
2. **ducking 的觸發點**：已接上大世界的字幕和對話框。戰鬥中沒有說書人字幕元件，所以沒接。方案寫的「戰鬥中音樂壓低 30%」我理解成要 AU-3 在戰鬥畫面掛上 `useDuck(true)`；音樂軌第一階段本來就沒有音源。**接戰鬥要改 `screens/BattleScreen.tsx`，6R-F 正在改那附近，所以留給 AU-3。**
3. **減少刺耳的 −6 dB 套在主音量**：方案寫「所有音效上限 −6 dB」。我套在主 gain，所以音樂和環境也一起降，這是比較安靜的做法。要不要改成只降音效軌？
4. **超過上限時不放新的**：沒有搶掉最舊的那一聲，這樣結果可預期。總上限 16 和合併時每次 +15%（最多 1.45 倍）都是原型數值。
5. **沒有給 `at` 的 `play`**：會用 `currentTime` 當 `at`。同一個 render quantum 內連續呼叫兩次，也會被當成同一時間點合併。實測時曾經因為點得很快看到一次合併。我認為這樣合理（本來就是同時），但先記下來。
6. **共用 CSS 的修改**：`.bhud-right:has(.top-popup)` 的 z-index 和 `.top-popup` 的 max-height 是共用的頂端列面板樣式，反應設定、隊友指令、圖例也一起受影響（都只會變好）。請 6R-F 合併時留意 `styles/battle-hud.css` 會不會衝突。
