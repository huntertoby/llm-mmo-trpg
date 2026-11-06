# Phase 3R-3c 報告｜種族外觀：體型、臉部紋路、鬍子、獠牙、龍裔（C 畫風）

規格：`docs/phases/Phase3R計畫.md` 4.5 節的 3R-3c。畫法對照 `docs/art/sample/storyDoll.js` 的 `face`（鱗片、刺青、晶路、獠牙、鬍子、豎瞳）與龍裔部件；龍裔用 `種族與側面移植需求.md` ① 的定案版（甲＋乙＋丙＋戊）。另併入美術 PM 驗收 3R-3b 的兩個必修（`docs/art/3R-3b檢查.md`）。

## 1. 交付

| 項目 | 位置 |
|---|---|
| 體型接上資料來源 | `inkRace.ts` `raceLookToLook` 帶出 `build`（stout／tall）；`inkDoll.ts` 既有 `buildScale` 縮放（矮壯 ×(1.12, 0.88)、高瘦 ×(0.96, 1.1)）；沒有新的後端欄位（`RaceLook.build` 在 3R-1 已有） |
| 頭頂狀態列跟體型 | `inkDoll.ts` `buildRowRise`、`unitSprite.ts` `statusRow`：高瘦（精靈）頭頂升高 10%，狀態列同步上移約 4px；矮壯維持原位（頭變低，不會蓋到） |
| 臉部紋路 | `inkRace.ts` `drawRaceFace`：`scales` 鱗片、`marks` 刺青（`mark_color`）、`circuit` 晶路、`dragonscale` 龍鱗（多一排、線較粗、用 `scale_color`）；正面與側面各有位置，背面不畫 |
| 鬍子、獠牙 | `drawRaceFace`：鬍子（髮色，有鬍子時不畫嘴）、獠牙（正面兩顆、側面一顆）；畫在頭髮與頭部裝備之前，頭盔會蓋住該蓋的部分 |
| 豎瞳 | `drawEye`（`inkDoll.ts` 的 `drawFace` 呼叫）：金色眼白＋黑色細縫 |
| 龍裔 | 大龍角、粗龍尾＋尾上背刺（3R-3b 已有）；新增：龍鱗紋路、豎瞳、鱗脊（`drawRidge`，鼻樑到額頭三個小尖，畫在頭髮之後）、肩後背刺（`drawBackSpines`：正面只露尖端、背面畫在披風之上、側面在背後）、鱗色三色（資料 `scale_color`，影響龍鱗、鱗脊、背刺、尾巴） |
| 美術 PM 必修 1 | `content/races.yaml` 角魔 `horn_color` 改 `#bfb0a4`，`raceLooks.json` 夾具重產 |
| 美術 PM 必修 2 | `inkDoll.ts` `drawHair`：有種族角、帽子被抬高（巫師帽、寬帽）時，頭髮照「沒有遮頭頂」畫，帽緣下面是頭髮 |
| 開發頁 | `doll-gallery` ⑫ 補：龍裔三色四方向、矮人鬍子＋頭部裝備、獸人獠牙＋頭部裝備、晶能義體人晶路、海民刺青、鱗族鱗片（標題前綴沿用「3R-3b・衝突」） |
| 測試 | `inkRace.test.ts` 新增 6 項（欄位對照與亂值、體型縮放與狀態列、各部件各視角、龍裔多鱗色×四方向與其他種族×全部頭部裝備全組合確定性與不用 `Math.random`、豎瞳、角魔巫師帽留頭髮） |

沒有動 Python 程式與 API；只改 `content/races.yaml` 一個色碼與重產的夾具。

## 2. 驗收

| 條件 | 結果 | 證據 |
|---|---|---|
| `stout`／`tall` 接上種族資料 | 通過 | 矮人矮壯、精靈高瘦；`inkRace.test.ts`；`img/3R-3c-races-south-north.jpg`、`-races-east-west.jpg` |
| 頭頂狀態列跟體型確認 | 通過（有調整） | 高瘦上移；`buildRowRise` 測試 |
| 臉部紋路（鱗片、刺青、晶路）、鬍子、獠牙、豎瞳 | 通過 | `img/3R-3c-dwarf-beard-orc-tusks.jpg`、`-cyborg-seafolk-faces.jpg`、`-dragonkin-south-zoom.jpg` |
| 龍裔定案版（大龍角、龍鱗、豎瞳、鱗脊、粗龍尾、背刺、鱗色可換） | 通過 | `img/3R-3c-dragonkin-south-zoom.jpg`（豎瞳、鱗脊、龍鱗、紅鱗尾）；紅／藍／金三色四方向在 `doll-gallery` ⑫ 可看 |
| 10 族四方向含體型與臉部 | 通過 | `img/3R-3c-races-south-north.jpg`、`-races-east-west.jpg` |
| 美術 PM 必修 1、2 | 通過 | `img/3R-3c-fiend-hats-overview.jpg`（角魔＋各種帽子，巫師帽下有頭髮、角為骨灰色） |
| 檢查清單「種族」：全組合自測、龍裔定案版、衝突規則 | 通過 | 全組合自測在 `inkRace.test.ts` |
| 實戰看得到 | 通過 | `img/3R-3c-battle-dragonkin-hero.jpg`（`dev_blaze` 種子 7、`race: dragonkin`，戰場縮圖下只看得出角與尾，臉部紋路太小） |
| tsc、vitest（`src/render`、`src/battle`、`src/dev` 82 檔 827 項）、build | 通過 | |
| ruff、format、pytest（`tests/api/test_client_fixtures.py`、`tests/content`、`tests/engine/test_race_skills.py`） | 通過 | 沒動 Python 程式，未跑 mypy |
| 排版煙霧檢查（1600×900、800×600、1600×900 shortBottom） | 全 PASS | 同 3R-3b 的作法：先手動開始戰鬥再呼叫 `runCase`；800×600 要重新載入頁面（視窗縮放不會重建窄螢幕版面） |

未跑完整 `scripts/check.py`（守則 11）。沒有新增 `noqa`。

## 3. 待 PM 決定

1. **正面背刺幾乎看不到**：肩後背刺在正面被肩甲與手臂蓋住（符合「背刺被盔甲蓋住大半」），目前正面只在沒穿甲時才露尖端；背面（披風之上）與側面看得到。要不要正面也強制露出？
2. **鱗脊位置**：畫在頭髮之後的額頭三個小尖（避開瀏海被蓋住），戴頭盔、帽子時被蓋住；沒有畫到鼻樑兩眼之間（會和眼睛重疊）。
3. **戰場實際大小看不出臉部紋路**：縮圖下只有角、尾、鬍子、膚色分得出來，豎瞳、紋路要放大才看到（與樣張的評估一致，沒有為了縮圖加粗）。
4. **獸人的獠牙、龍裔鱗片在側面只有一側**，位置照 `storyDoll.js` 的側面座標。
5. **晶路**：照樣張只畫一小段發光線與兩個點，沒有畫「半邊臉金屬片」（`raceArt.js` 的舊版）；如要更明顯需要美術 PM 再提樣張。
6. **狀態列**：只有高瘦體型上移；矮壯維持原位，沒有下移（避免遮到其他單位的血條）。
7. **鬍子顏色用髮色**（`hair_color`）；矮人戴頭盔時鬍子仍畫在頭盔之前（下巴露出），兜帽下也露出鬍子。
8. **帽子抬高時頭髮**：巫師帽與寬帽在有角時一律照「沒蓋頭頂」畫頭髮；沒有角的人戴巫師帽仍蓋住頭髮（維持舊行為）。
9. **開發頁標題前綴**：3R-3c 新增的衝突組沿用 `conflict()` 的「3R-3b・衝突」前綴，只是顯示名稱。
10. **工作紀錄**：環境的 `python` 是 Windows 商店佔位程式，腳本編輯一度沒套用（用 `uv run python` 重做）；已確認所有檔案最終內容與 commit 一致。
