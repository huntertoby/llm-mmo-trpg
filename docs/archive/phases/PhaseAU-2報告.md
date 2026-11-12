# Phase AU-2 報告：合成音庫與介面音

分支 `worktree-agent-a72d1f391f3faa679`，基於 main `70a6268d`（AU-1 合併）。規格見 `docs/art/音效與音樂方案.md` 第 2.1、2.2、4 節，再加上美術 PM 驗收 AU-1 時追加的 3 項（專案 PM 轉達）。

使用者的決定（專案 PM 轉達）：音樂選純西式奇幻管弦；外部下載「先不要」。這一段沒有用任何外部素材，也沒有新增套件，`package.json`、`pnpm-lock.yaml`、`pyproject.toml` 都沒動。沒有碰 `client/src/render/`、`client/src/battle/`、`screens/battle/`；只從 `render/inkStyle`、`render/attackVariants` 匯入 `seedOf`、`lcg`、`fmix32`，沒有修改它們。

## 做了什麼

| # | 項目 | 做法 | commit |
|---|---|---|---|
| 1 | 合成積木 `client/src/audio/synth.ts` | 用 JS 直接算出取樣，寫進 `AudioBuffer` 再播放，不靠 OscillatorNode 排程。積木共 6 種：濾波雜訊、振盪器（可掃頻、加顫音、加低通；鋸齒波和方波用 polyBLEP 去混疊）、FM 鐘與金屬、和弦鐘（`stagger` 就是琶音）、短脈衝序列（雜訊喀聲，或冒泡的正弦啵聲）、劈啪。包絡是 `[起音, 衰減到 −40 dB, 保持]`，結尾有 4 ms 淡出 | d9f6a25e |
| 2 | 確定性 | 種子是 `sfxSeed(id, 變體鍵) = fmix32(seedOf("id#變體鍵"))`；每一層再用 `fmix32` 分出自己的 LCG。雜訊、劈啪的時間、脈衝抖動、`vary` 的音高微調都從種子來，沒有用 `Math.random`，也不讀時鐘 | d9f6a25e |
| 3 | 參數表 `content/audio/sfx.yaml` | 共 79 筆：介面音 20 個、戰鬥音效 58 個、環境點綴 1 個（遠雷）。格式照方案第 4 節，檔案最上層多包一層 `sfx:`。每筆的欄位：`zh`、`cat`、`use`、`track`、`synth`（○＝full、△＝temp）、`harsh`、`gain`、`vary`、`layers` | d9f6a25e |
| 4 | 前端讀參數表 | 沿用 dev 頁讀 `content/` 的做法：build 時用 `?raw` 匯入，再用專案已有的 `yaml` 解析（`sfxLibrary.ts`）。前端也做一次結構檢查，壞掉的那筆略過不出聲。`main.tsx` 呼叫 `registerSfxLibrary(audio)` | d9f6a25e、cffbec37 |
| 5 | Python schema | `src/trpg/content/audio.py`（`SfxTable`）：用 callable discriminator 依種類鍵分派到 6 種 model；檢查頻率範圍 20～20000 Hz、時間、dB、包絡格式、`harsh` 必須是嚴格的布林值、`cat: ambient` 必須放在 ambient 軌。已登記在 `KNOWN_CONTENT_FILES`，`trpg content check` 會顯示「audio/sfx.yaml：79 個音效（介面音 20 個、合成暫代 7 個）」。純前端資料，不進引擎 | aca9d7f5 |
| 6 | 介面音接上介面 | **點擊**：在 `audio/uiSounds.ts` 用一個委派的 click 監聽，依元素挑音（規則見下方「介面音清單」）。**事件**：由元件呼叫 `uiSound(id)`。觸發點有 `usePopupMenu` 開關、`ErrorBanner`、說書人字幕、擲骰（翻滾與停下）、`RunLevelUp`，以及大世界依前後兩次畫面的差判斷：升級、任務完成、任務更新、拿到物品、金幣。另外，等伺服器超過 0.7 秒會放墨痕聲，之後每 1.6 秒一次。同一次點擊只放一聲：已經有事件音，就不再疊輕觸 | cffbec37 |
| 7 | dev 頁 `client/audio-gallery.html` | 在 AU-1 的頁上擴充：分類分頁加 79 個音效鈕，點了就播；選一個會顯示波形、長度和峰值；每層的數字欄位可以即時調；也可以直接改 YAML 再按「套用」；可以換變體鍵、試聽柔和版、還原；可以複製這一筆或整張參數表，瀏覽器不讓複製時會改顯示文字框。AU-1 的測試音放在最下面 | ada64581 |
| 追加 1 | 大世界齒輪鈕 | 原本按了會顯示「設定：尚未開放」，現在會打開 `AudioSettingsPanel`，目前只有聲音一區。和戰鬥「版面」面板裡的聲音區是同一個元件、同一份設定。面板用 `usePopupMenu`，齒輪鈕有標 `aria-expanded`，說明卡在面板開著時不顯示；類別是 `.top-popup .popup-menu`。拿掉了 `onSettings` prop | cffbec37、ada64581 |
| 追加 2 | 減少刺耳音效只作用在音效與環境 | 主音量不再降。**音效軌**：音量 ×0.501（−6 dB）；高低頻 shelf 只接在音效軌上（軌 → high → low → 主）；而且改放柔和版，所有頻率夾在 70～3500 Hz，鋸齒波和方波改成三角波，白雜訊和高通改成低通或帶通，FM 調變指數減半，鐘不加泛音。**環境軌**：`harsh: true` 的音效不出聲（回傳 `silent`）。**音樂**：不動。主輸出的限幅固定在 −1 dB | d9f6a25e |
| 追加 3 | 預設關閉 | `DEFAULT_AUDIO_SETTINGS.reduceHarsh === false`，已加測試，壞資料也會退回 false | d9f6a25e |

**音量平衡**：寫了一個暫用腳本，算每個音效在 48 kHz 下的峰值和 RMS，再用各筆的 `gain` 拉齊，腳本已刪。拉齊後的峰值：介面音約 −14～−6 dB，墨痕約 −21 dB；出招約 −9 dB；命中約 −3～−8 dB；腳步約 −14 dB；爆炸、暴擊、Boss 大招約 −2.5 dB。全部不超過 ±1，只是起點，等美術 PM 聽過再調。

## 檔案清單

新增：
- `client/src/audio/synth.ts`、`sfxLibrary.ts`、`uiSounds.ts`、`synth.test.ts`、`uiSounds.test.ts`
- `client/src/world/useWorldSounds.ts`
- `content/audio/sfx.yaml`
- `src/trpg/content/audio.py`、`tests/content/test_audio_sfx.py`
- `docs/art/shots/au2/au2_gallery.jpg`、`au2_gallery_narrow.jpg`、`au2_world_settings_1600.jpg`、`au2_world_settings_800.jpg`
- 本報告

修改：
- `client/src/audio/types.ts`：加 `AudioBufferLike`、`sampleRate`、`createBuffer`，`SoundSource` 加 `harsh` 與 `StartFlags`
- `client/src/audio/engine.ts`、`mix.ts`、`fakeAudio.ts`、`audio.test.ts`：減少刺耳音效的新規則；AU-1 那條減少刺耳的測試改成新規則
- `client/src/audio/AudioSettingsPanel.tsx`：說明文字
- `client/src/main.tsx`
- `client/src/dev/audioGallery.tsx`、`client/audio-gallery.html`
- `client/src/ui/usePopupMenu.ts`、`client/src/ui/ErrorBanner.tsx`
- `client/src/world/StoryParts.tsx`、`client/src/world/WorldHud.tsx`、`client/src/world/hud.test.ts`
- `client/src/screens/WorldScreen.tsx`、`client/src/screens/RunLevelUp.tsx`
- `client/src/styles/world-hud.css`
- `src/trpg/content/registry.py`

## 測試

- vitest 新增 19 個：`synth.test.ts` 15 個、`uiSounds.test.ts` 4 個。
  - 參數表：79 筆全部解析成功；介面音剛好 20 個；6 種積木都有音效在用；每筆都算得出聲音，峰值 > 0.01 且不超過 1，沒有 NaN；錯誤範例會被抓到並略過。
  - 確定性：同參數、同種子、同取樣率逐點相同；變體鍵改變時，雜訊、劈啪、脈衝抖動跟著改變；把 `Math.random` 換成會丟例外的函式後，79 筆照樣算得出來；經過引擎時，寫進 AudioBuffer 的取樣等於 `renderSfx` 的結果，而且同一個變體只算一次。
  - 減少刺耳音效：預設關閉；柔和版沒有超過 3500 Hz 或低於 70 Hz 的頻率設定，也沒有鋸齒波、方波、白雜訊、高通；也檢查原表確實有超過門檻的設定，確認測試不是空轉；只作用在音效軌，主音量、音樂、環境的 gain 不變；音效軌放柔和版；環境軌的 harsh 音效不出聲，其他環境音照常；柔和版的長度不變。
  - 介面音：點擊挑音的規則；同一下點擊只放一聲；大世界事件音的優先順序；換角色與花錢時不出聲。
- `audio.test.ts` 的減少刺耳測試改成新規則：shelf 只接在音效軌，主音量與限幅不變。
- Python `tests/content/test_audio_sfx.py` 共 19 個：真實檔案載入、6 種積木都有用到、harsh 標記、登記在 content check；錯誤範例 13 種層級錯誤（兩個種類鍵、沒有種類鍵、缺 dur、未知波形、超出可聽範圍、掃頻終點太低、帶通沒有 freq、fm 缺參數、pulses 缺 every、空和弦、包絡格式錯誤、太長、拼錯欄位），加上項目層級錯誤（id 格式、未知分類、空 layers、harsh 不是布林、ambient 分類放錯軌），以及壞檔案回報 `ContentError`。
- 交件前跑的檢查：

  | 檢查 | 結果 |
  |---|---|
  | client 全部 vitest | **214 個檔案、2338 個測試全過** |
  | `corepack pnpm -C client build` | 結束碼 0 |
  | Python `tests/content` | **2603 passed** |
  | `ruff check`、`ruff format --check`、`mypy src`（513 個檔）、`lint-imports`（13 個 kept） | 全過 |
  | `trpg content check` | 通過 |

  Python 用的是主資料夾的 `.venv` 加 `PYTHONPATH=<worktree>/src`，沒有在 worktree 跑 `uv sync`。中途 `uv run` 在 worktree 自動建了空的 `.venv`，已刪除。

## 音效清單（79 個）

積木代號：N＝濾波雜訊、T＝振盪器／掃頻、F＝FM 鐘／金屬、C＝和弦鐘、P＝短脈衝序列、K＝劈啪。△＝合成暫代（`synth: temp`），⚡＝`harsh: true`。

**介面音（2.2，20 個）**

觸發方式：委派點擊（▲）或元件事件（●）。

| id | 用途與觸發 | 積木 |
|---|---|---|
| ui_tap | 一般按鈕（▲，預設） | N＋T |
| ui_confirm | 送出、`.primary` 按鈕（▲） | C |
| ui_cancel | 取消、關閉、返回、×（▲） | T＋N |
| ui_error | `ErrorBanner` 出現（●）；按 `aria-disabled` 或停用狀態的 HUD 鈕（▲） | T＋T |
| ui_toggle | 勾選框、單選、分頁、`aria-pressed` 按鈕（▲） | P |
| ui_select | `role=option`（▲） | F |
| ui_panel_open／ui_panel_close | `usePopupMenu` 開、關（●；戰鬥頂端面板、大世界齒輪等） | N |
| ui_page | 上一頁、下一頁、翻頁鈕（▲） | N＋P |
| ui_item | 大世界拿到物品（●） | C |
| ui_coin | 大世界金幣增加（●） | F＋F |
| ui_levelup | 大世界升級、roguelite 升級畫面（●） | C＋T |
| ui_learn | 文字以「學會／學習」開頭的按鈕（▲） | C＋N |
| ui_quest_update／ui_quest_done | 大世界任務新增、進度、完成（●） | N＋F／C |
| ui_dice_roll／ui_dice_success／ui_dice_fail | 擲骰開始、停下（成功與勉強放成功聲、失敗放失敗聲）（●） | P＋N／C／T＋T |
| ui_narrator | 說書人字幕出現（●） | N＋C |
| ui_ink_wait | 等伺服器超過 0.7 秒，之後每 1.6 秒一次（●） | N |

另外：`data-sfx="<id>"` 可以指定任何按鈕的音效，`data-sfx="none"` 不出聲。

**戰鬥音效（2.1 的 ○ 與 △）**：這段只做音色和參數表，還沒有掛上時間軸，AU-3 要接。

| 類別 | id（積木） |
|---|---|
| 起手 | windup_charge 蓄力（T＋T）、windup_chant 詠唱（C）、windup_sigil 劍指畫符（N＋F）、windup_bow_draw 拉弓△（P＋T）、windup_reload 上膛△（F＋F＋N） |
| 出招 | swing_slash 揮砍（N）、swing_thrust 突刺（N）、swing_punch 拳（N）、release_bow 弓放箭△（T＋N）、release_crossbow 弩△（F＋N）、release_gun 火槍△⚡（N＋T＋N） |
| 命中 | hit_blunt 鈍擊（T＋N）、hit_magic 魔法命中（F＋N） |
| 元素 | elem_fire 火（N＋K）、elem_ice 冰（P＋F）、elem_lightning 雷（T＋N＋K）、elem_water 水（N＋P）、elem_poison 毒（P＋N）、elem_holy 聖光（C＋N）、elem_dark 黑暗（T＋N，慢起音、急收）、elem_mist 霧（N） |
| 結果 | res_crit 暴擊（T＋N＋F）、res_block 格擋（F＋N）、res_dodge 閃避（N）、res_miss 失手（N）、res_kill 擊殺（T＋N）、res_down 倒下（N＋T）、res_revive 復活（C＋T）、res_victory 勝利短樂句△（C） |
| 原語 | prim_heal 治療（C＋N）、prim_shield 護盾（T＋T＋F）、prim_dash 衝刺（N）、prim_land 跳躍落地（N＋T）、prim_teleport 傳送（T＋T）、prim_summon 召喚（T＋N＋K）、prim_rune_carve 符文刻下（N＋P＋F）、prim_rune_burst 符文引爆（F＋N＋T）、prim_transform 變身（T＋C＋N） |
| 狀態 | status_burn 燃燒（K＋N）、status_freeze 冰凍（P＋N）、status_poison 中毒（P）、status_stun 暈眩（C，小鈴轉圈）、status_shock 帶電（K＋T） |
| 地表 | surface_slip 冰面滑倒（N＋T）、surface_trap 陷阱夾住（F＋T＋N）、surface_fire_spread 火蔓延（N＋K） |
| 爆炸 | explosion 爆炸△⚡（N＋T＋N＋K） |
| 腳步 | step_grass、step_stone、step_dirt、step_wood、step_water、step_ice、step_sand（N，石、木、冰另加 T 或 F；水用 P＋N；全部加 `vary`） |
| 系統 | sys_round_start 回合開始（F）、sys_my_turn 輪到我方（C）、sys_boss_warn Boss 預告（T＋F＋F）、sys_boss_ult Boss 大招⚡（T＋N＋T） |
| 環境點綴 | amb_thunder 遠雷⚡（ambient 軌；N＋K＋T） |

2.1 標 × 的（刀劍砍肉、穿刺的真實質感）照方案沒有做，先用揮砍的咻加鈍擊代替。

## 實機

我自己啟動了兩個伺服器：前端 5379（5377 已被其他程序占用，所以改用 5379）、後端 8377。後端存檔目錄設在 scratchpad，沒有碰 `saves/` 和 `tmp_x`。驗證用的 vite 設定沒有 commit，已刪除；兩個伺服器都用 TaskStop 和自己的 PID 結束了。瀏覽器借用了 AU-1 留下的 tab-13（原本的 5344 伺服器已經沒了），結束時已用 desktop preset 還原大小。

**dev 頁**：
- 79 個鈕都有顯示；在真的 AudioContext 上點擊播放，回傳 `played`，console 沒有錯誤。
- 調參數（爆炸的 gain 改成 −6）後，YAML、波形、「已改」標記都跟著更新。
- 試聽柔和版時，峰值從約 −2.5 dB 降到 −6.7 dB，並顯示「頻率 ≤ 3500 Hz」。
- 用程式觸發「複製」時，瀏覽器不給剪貼簿權限，頁面改顯示文字框（降級正常）。由使用者手勢點擊時應該可以直接寫進剪貼簿，這點沒有實測。

**大世界齒輪面板（浮動卡規則 6.5.1）**：這是點擊式面板，用 `usePopupMenu`，不是滑過才出現的說明卡。

| 尺寸 | 結果 |
|---|---|
| 1600×900 | 點齒輪打開 → 滑鼠移進面板 → 捲動 → 在面板內點「音效靜音」，面板都沒關，`trackMuted.sfx` 有存進 localStorage → Esc 關閉 ✔。第一次實測時，下方的「任務追蹤」區塊蓋在面板上；已修正：用 `.world-hud-block:has(.world-settings-popup)` 把齒輪所在區塊的 z-index 提到 20 |
| 800×600 | 面板範圍 x 477～772、y 193～412，在視窗內，內容不需要捲動 → 在面板內勾「減少刺耳音效」，面板沒關且有存起來 → 點外面關閉 ✔ |

截圖：
- `docs/art/shots/au2/au2_gallery.jpg`：dev 頁，1600 寬，選了爆炸並開柔和版
- `docs/art/shots/au2/au2_gallery_narrow.jpg`：dev 頁，800 寬，單欄
- `docs/art/shots/au2/au2_world_settings_1600.jpg`、`docs/art/shots/au2/au2_world_settings_800.jpg`：大世界齒輪面板

**大世界的介面音沒有逐個用耳朵確認**，只確認了 dev 頁會出聲、單元測試通過。正式畫面裡的觸發時機由美術 PM 實聽驗收。

## noqa

沒有新增 noqa。寫測試時加過兩個 `# noqa: ANN401`，ruff 回報未使用（RUF100），已經拿掉。

## 待 PM 決定

1. **參數表最上層多一層 `sfx:`**：方案第 4 節的範例是直接寫 `swing_light: {...}`。我多包一層，是為了讓 pydantic model 有欄位可以掛驗證，也留空間給之後的共用設定。這樣可以嗎？
2. **戰鬥畫面沒有接任何音效**：照指示，戰鬥時間軸留給 AU-3。不過全站的委派點擊監聽也會在戰鬥畫面的按鈕上放輕觸、確認、取消，像技能列、結束回合這些按鈕。我沒有改 `screens/battle/` 或 `client/src/battle/` 的任何檔案。如果戰鬥按鈕要用別的音，或不出聲，AU-3 可以在按鈕上加 `data-sfx`。
3. **勝利短樂句**：`res_victory` 是合成暫代，還沒接到 6F-1 的結算畫面，因為那邊正在改；留給 AU-3。
4. **點擊挑音用文字啟發**：取消、翻頁、學會這三種是靠按鈕文字或 aria-label 判斷（例如「取消」「關閉」「下一頁」「學會…」），主要按鈕靠 `.primary` 類別。這樣不用改一堆元件，但有可能誤判；誤判的按鈕可以加 `data-sfx` 修正。這樣可以嗎？
5. **一次更新只放一聲**：大世界同時升級又拿到物品時，只放優先度最高的一聲（升級 → 任務完成 → 任務更新 → 物品 → 金幣）。同一個事件處理中，第二個事件音也會被略過，例如按「關閉」時，取消聲和面板收起聲只留先到的那一聲。這是比較安靜的做法。
6. **柔和版的門檻**：3500 Hz 和 70 Hz 都是原型數值，搭配音效軌上 5 kHz −12 dB、120 Hz −9 dB 的 shelf。另外，FM 的邊頻在調變指數減半後仍可能稍微超過 3500 Hz；測試只檢查「設定值」，沒有做頻譜分析。
7. **狀態音不循環**：燃燒「全場一條、循環」這部分屬於播放邏輯，留給 AU-3。現在 `status_burn` 是一段 1.2 秒的音，可以接成循環。
8. **墨痕等待聲接在 `WorldScreen` 的 `busy`**：前端目前沒有墨痕等待動畫的元件（美術 PM 的 v2 方案還只在文件裡）。所以我用「等伺服器超過 0.7 秒」當觸發點。之後做了動畫元件，要不要改接到動畫上？
9. **`harsh` 的意思**：只影響環境軌，減少刺耳時不出聲。放在音效軌的 harsh 音效（爆炸、火槍、Boss 大招）照常放柔和版。方案第 3 節寫的「減少動態時，Boss 大招、爆炸改成柔和版」我理解成 AU-3 的事，這段沒有做。
