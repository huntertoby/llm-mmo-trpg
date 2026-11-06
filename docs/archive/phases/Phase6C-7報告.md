# Phase 6C-7 完成報告：文字減量與去文字化⑤（字幕、對話泡泡、事件卡、骰子動畫；NPC 紙娃娃照頭像）

實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6C-7 列。依據：21.7；`docs/archive/art/HUD版面.md` 5.7；`docs/archive/art/去文字化移植需求.md` 第 6 節；`docs/art/NPC頭像.md`（全文，第 4 節第 5 項）；6B-4、6C-5 報告。開工前已 `git merge main`、`git merge origin/claude/art-pm-8f4e6d`（後者已是最新，無衝突）。

> 沒有改引擎、`src/trpg/world` 的規則、`RegionMap`、HUD 地圖鈕、`WorldScreen.tsx`（6D-5 在改的檔都沒碰）。伺服器只加欄位，沒改任何既有欄位的意思。

## 1. 做了什麼

| 項目 | 檔案 |
|---|---|
| 頭像資料（伺服器原本沒有） | `content/world_events.py`：`NpcPortraitLook`、`NpcPortraitGear`、`NpcPortrait`，`NpcCardDef.portrait`（選填）。`content/world/npcs/cloud_ridge.yaml`、`ashen_waste.yaml` 15 位照 `docs/art/sample/portraits.js` 的表填（駝峰改底線） |
| API（只加欄位） | `FieldNpcView.portrait`、`NpcHereView.portrait`（人設卡的 `portrait` 原樣給）、`EventView.art_url`（插圖網址，目前一律 `null`）。OpenAPI 與 `schema.d.ts` 已重產；`api/types.ts` 加 `NpcPortrait` |
| 頭像畫法 | 新檔 `client/src/render/portrait.ts`：用 C 畫風紙娃娃正面頭部放大（`resolveDoll`＋`drawFigure`，不畫主手副手）＋頭像專用配件 15 種＋區域色框；白狐另畫狐臉；沒有資料畫通用剪影；說書人用兜帽長袍的固定頭像。離屏畫好依（外觀、區域、大小）快取成圖片網址 |
| 地圖紙娃娃照頭像 | 新檔 `client/src/world/npcLook.ts`（`npcFieldLook`、`portraitDollLook`、`portraitGear`、`portraitRaceLook`）；`fieldModel.ts` 的 NPC 單位與種族外觀改用它 |
| 字幕、對話框、骰子 | 新檔 `world/narration.ts`（純函式：切句、分段、字幕淡出時間、選項圖示、屬性鍵、骰子每格的樣子）、`world/StoryParts.tsx`（`NarratorSubtitle`、`StoryDialog`、`DiceRoll`、`FallbackMark`）、`world/StoryIcons.tsx`（選項、六屬性、d20、線索、模型關閉、說書人、資訊圖示；`Portrait` 元件）、`world/story.css` |
| 事件卡與情境判定 | `world/EventCard.tsx` 改寫（見第 2 節）；`StoryBlock` 保留匯出（舊測試與其他地方可用） |
| NPC 對話時的頭像 | `FieldPanels.tsx` 的 `HudNpcPanel`：頭像 48（角落疊好感表情）；`NpcPanel.tsx`：NPC 說的每一行前面一個 28 的頭像 |
| 開發用頁面 | `client/story-gallery.html`＋`src/dev/storyGallery.tsx`（`?mode=subtitle｜event｜roll`，`&t=` 指定骰子動畫已過的毫秒）。用正式元件與樣式、假資料；NPC 外觀直接讀內容檔 |
| 測試 | `tests/api/test_world_field_people.py` 加 2 個；新檔 `client/src/world/story6c7.test.ts`（36 個） |
| 截圖 | `docs/art/6c7_subtitle.jpg`、`docs/art/6c7_event_card.jpg`、`docs/art/6c7_situation_roll.jpg` |

## 2. 畫面怎麼改

**1. 說書人字幕**（21.7）
- 判定結果的敘述改成上方一行字幕：只顯示第一句（最多 40 字），**6 秒後用 0.8 秒淡出**，淡完就不畫。
- 一行講不完或有補充（`more_zh`）時有「多講一點」：點了展開完整旁白＋補充，展開時不淡出；再點「收起」。
- 字幕放在判定結果卡的上面（HUD 中央區塊的最上方，就是畫面上方），不用動 `WorldScreen`。字幕淡掉以後，結果卡左下的「說書人」小按鈕可以把完整敘述用對話框再看一次。
- 換地圖只跳一行地名：6B-3 已有（`world-place-banner`），沒有重複做。

**2. NPC 說話**
- 頭上的泡泡沿用 6B-4（`npcBubbles`：這次請求 NPC 說的第一句、1～2 句、最多 40 字），泡泡與聊天紀錄都從同一份 `view.dialog` 來，沒有另開來源。
- 對話時顯示頭像：NPC 浮動面板的頭像從好感表情換成紙娃娃頭像（48，表情疊在右下角）；聊天紀錄裡 NPC 的每一行前面一個 28 的頭像。

**3. 事件卡**
- 上方一張插圖：有 `art_url` 就用圖；沒有時畫場景色塊（依骨架 ID 的 FNV-1a 雜湊挑 5 組之一，確定性）＋大圖示（第一個不是「放棄」的選項的圖示），下緣一行地名。原本的「人物：動機」收進地名的說明卡，「接著線頭」是一個小圖示，`leave_zh` 收進資訊圖示。
- 說書人敘事改成對話框：說書人頭像＋名字＋一段字。一段＝1～2 句、不超過 48 字；有下一段時右下有閃爍的「▼」，點文字播下一段；最後一段有補充時出現「多講一點」，點了接上補充的段落。情境判定的旁白也是同樣的對話框。
- 選項：前面一個圖示，文字只留一行（情境判定與交涉用說明 `note_zh`，戰鬥、放棄、機遇用種類名），原本的整句（種類、屬性、付出）＋原本的說明收進說明卡。交涉的付出改成「−2 補給」小字；「用〔線頭〕抵」按鈕照舊。
- 圖示對照：戰鬥＝雙劍、交涉＝錢幣、機遇＝星、放棄＝出門。情境判定看說明的關鍵字：潛／躲／繞／偷…＝潛行、說服／勸／談／騙…＝說服、查／找／看／辨…＝調查、撞／推／爬／闖…＝硬闖；都沒有時看第一個屬性（力量、體質＝硬闖；敏捷＝潛行；智力、感知＝調查；意志＝說服）。

**4. 情境判定**
- 標題一行：方法圖示＋說明、d20 圖示＋基準 DC 數字、可用屬性的圖示（說明卡寫屬性名）、資訊圖示（方法）。
- 引用的事實收進「線索」圖示（右上，數字是可引用的筆數／已引用筆數），點開才列出可點的事實，點法與插字照舊。
- 送出鈕改成「d20 擲骰」，「送出後就定案，不能重來」收進說明卡。
- 判定結果：兩顆 d20 的動畫（0.9 秒，每 70 毫秒換一次面，照固定序列換、不用亂數），結束時用的那一顆塗結果色並發光，另一顆變淡；結果字（成功／勉強／失敗）、卡片框都是結果色（綠 `#5ad06a`、黃 `#e8bb48`、紅 `#e04a3a`）。
- 下面一行：屬性圖示＋總和 vs d20＋DC。算式、「兩顆骰：6、14（優勢）」、屬性與方法收進這行的說明卡。用心的明細收進「線索」圖示（數字＝算到的／引用的）。
- 「（模型關閉：照預設提議）」改成右上角的小圖示（說明卡寫原本的字）；「（模板文字）」在字幕與對話框裡也改成同一個小圖示。

**5. 地圖上的 NPC 紙娃娃**（NPC頭像.md 第 4 節第 5 項）
- 伺服器的 `FieldNpcView.look` 仍是 `null`；前端 `npcFieldLook`：有 `look` 用 `look`，沒有時照 `portrait` 換算，都沒有用預設外觀。
- `look` 的膚色、髮型、髮色、髮帶、鬍子、體型照搬；`ears`、`horns`、`horn_color`、`pattern`、`mark_color` 走種族外觀（紙娃娃本來就支援）。
- `gear` 照搬，沒寫材質的補預設（皮甲＝皮、板甲鎖甲頭盔＝鋼、布帽斗笠＝皮、其他＝布）。
- 配件照表：`cap`、`wide_hat` 換成同名帽子，`bandana` 換頭巾 `#a83a2a`，`headband` 換頭巾 `#b8432f`；其他配件不畫。`gear.head` 已經有值的以它為準。
- 霜音：異形「犬」骨架（`creature: {body: hound, material: fur, tint: #f4f0e8}`），頭上的表情圖示照樣有。

## 3. 測試與檢查

- 前端：`vitest run src/world src/render/inkDoll.test.ts src/dev`：28 檔 331 個全過（新的 `story6c7.test.ts` 36 個：字幕淡出與「多講一點」、對話框分段與「多講一點」接續、選項圖示表、事件卡輸出、骰子動畫中與結束狀態、三種結果色、結果卡收合、外觀映射表、霜音、`fieldDrawModel` 的 NPC 外觀）。`tsc --noEmit`、`pnpm build` 通過。
- 後端：`tests/api/test_world_field_people.py`、`test_openapi_snapshot.py`、`test_world_story.py`、`test_world_events_api.py`、`tests/content -k npc/world_event`、`tests/world/test_replay.py` 全過；`ruff check`、`ruff format --check`、`mypy src/trpg/content/world_events.py src/trpg/api`、`lint-imports` 通過。沒跑全量。
- 實測：自己開的 vite（埠 5313，沒開伺服器）開 `story-gallery.html`，1040×720：字幕 6 秒後淡掉、展開後 8 秒還在；對話框點一下換段、最後一段出現「多講一點」；線索圖示點開列出事實；骰子動畫播完停在真的點數。截圖是內建瀏覽器縮到約 800×554 輸出的。主控台只有 HMR 重新掛載的警告。

## 4. 待 PM 決定

1. **截圖是開發用頁面，不是實際遊戲**：事件與判定要走路碰到「！」才開，沒有開發用的捷徑；用正式元件與樣式、假資料拍。實際遊戲裡的 HUD 中央區塊位置照舊（`world-hud-center`），建議驗收時在遊戲裡再看一次。
2. **字幕放哪些旁白**（保守解讀）：只有判定結果的敘述改成字幕；事件與情境的開場旁白照 HUD版面.md 5.7 改成對話框；NPC 說話是泡泡＋聊天紀錄。字幕放在結果卡上面（中央區塊頂端），不另外在 `WorldScreen` 加一層（避開 6D-5 的檔）。
3. **字幕時間**：6 秒開始淡出、0.8 秒淡完；一行最多 40 字。對話框一段最多 2 句、48 字。都是原型值。
4. **傭兵頭像沒做**：規格只要地圖與對話的 NPC；`mercenaries.yaml` 的 9 位沒加 `portrait`（雇用清單目前不畫頭像）。NPC頭像.md 第 4 節第 3 項留給之後。
5. **事件卡的頭像用說書人**：事件的 `actor_zh` 多半不是 NPC（「困住的商隊」），對話框一律用說書人的頭像（兜帽長袍、傭兵金框）。之後若事件帶 NPC ID，可以換成那位 NPC 的頭像。
6. **NPC 的頭像框色**：用 `field.region`（雲嶺綠、荒原橘）；不在實地地圖時（舊的面板版面）用傭兵金。
7. **頭像資料缺時**：通用剪影（深色頭肩＋「?」），地圖上照舊用預設外觀。目前兩區 15 位都有資料。
8. **選項圖示的關鍵字表**是我定的（見 2.3），沒命中時看第一個屬性；技能、方法的正式圖示等美術 PM 給。
9. **插圖**：`EventView.art_url` 欄位已留，伺服器一律給 `null`；場景色塊 5 組是暫定。
10. **判定結果的「說書人」小按鈕**：字幕淡掉後重看完整敘述用（規格沒寫，保守加上，免得淡掉就看不到）。
11. **骰子、DC、選項與屬性圖示用 SVG 自畫**，沒有用美術樣張的 C 畫風墨線（屬性圖示是 `attr-icons.html` 的簡化版）；若要照樣張的墨線版，需要另一段移植。頭像本身照 `portraits.js` 移植。

## 5. 複雜度例外

沒有新增 `# noqa`。
