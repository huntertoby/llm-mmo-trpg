# `docs/art/sample/` 樣張檔一覽

> 2026-11-06 自 `docs/美術PM交接.md` 附錄 10 搬出。樣張頁是「畫法真相」，不接進遊戲；畫法改了就更新這張表。被 Q 版取代的舊頁已搬到 `docs/archive/art/sample/`（載入路徑已改成 `../../../art/sample/`）。

| 檔案 | 內容 |
|---|---|
| `qDoll.js`、`style-compare-3.html` | **Q 版人物（現行方向）**：見第 7 節 |
| `key-poses.html`、`parts-4dir.html`、`parts-extra.js` | Q 版關鍵姿勢與部件四方向特寫 |
| `idleWeapons.js`、`idle-weapons.html` | 武器待機 15 種 |
| `appearance-vary.html` | 外觀變化（#137、#138） |
| `dragon-compare.html` | 龍裔重做比較 |
| `storyDoll.js` | C 墨線畫法，**已被 Q 版取代**；Q 版頁仍載入它（`anim.js`、頭像等共用），不能刪。`storyDollSkin.js`、`flat-rig.html`、`style-compare.html`、`style-compare-2.html`、`restyle.*` 已搬到 `docs/archive/art/sample/` |
| ~~`scene.js`、`procedural.js`、`compare.html`、`legacy.js`、`kenney/`~~ | 第一次風格比較（色塊、Kenney、程式繪製），已搬到 `docs/archive/art/sample/` |
| `paperdoll.js`、`dolls.html` | 紙娃娃（已含 9 格新部件、新武器） |
| `skillIcons.js`、`parts.js`、`assembled.js`、`assembled.html` | 組裝式技能圖示 |
| `declutter.html` | 技能卡減雜三方向 |
| `downed.html`、`height.html`、`height2.html`、`lowwall.html` | 倒地、高度、矮牆 |
| `gearArt.js` | 裝備圖示產生器（含 `resolve()`、`dollItem()`；`legacy` 標記的造型不要用） |
| `gear-all.html`、`gear-sizes.html` | 裝備總覽＋全組合自測、尺寸檢查 |
| `gear2～5.html` | 裝備範例、風格包＋槍、#34 武器、數值卡 |
| `summonArt.js`、`summons.html` | 召喚物 17 種 |
| `fx.js`、`battlefield-fx.html`、`status-icons.html` | 戰場效果、狀態圖示提案（10-23） |
| `realms.js`、`realms.html` | 碎界五區比較（＋霓虹另案） |
| `regions4.js`、`regions4.html` | 其他四區地形與物件換皮（`../shots/misc/regions4.png`） |
| `explore.js`、`explore.html` | 可走動的城鎮（霧渡鎮）與野外（渡口石階）畫面示意，畫面地圖靠路口銜接（`../shots/misc/explore.png`；11-04 專案 PM 要的示意，非定案） |
| `hud.js`、`hud.html` | 網遊式 HUD 三種版面（`../shots/misc/hud.png`、`../../archive/art/HUD版面.md`；11-04，等使用者選，未代決） |
| `textless.html` | 介面去文字化改前／改後對照：技能卡、單位資訊、主角狀態卡（`../shots/misc/textless.png`；盤點在 `../../archive/art/HUD版面.md` 第二部分） |
| `battle.js`、`battle.html` | 戰鬥畫面現行格子版 vs D 版（待機、選移動、選範圍、路徑經過冰面和陷阱；`../shots/misc/battle-d.png`、`../../archive/art/戰鬥D版樣張.md`；2.5D 使用者不要，函式 `iso()` 留在檔案裡但不再顯示） |
| `bossArt.js`、`bosses.html` | 灰燼之心、碎晶之主的專屬造型與各階段（`../shots/misc/bosses.png`、`頭目造型.md`；11-04 樣張，待使用者看） |
| `cyborg.html` | 晶能義體人辨識記號三方案（`../shots/misc/cyborg.png`、`晶能義體人記號.md`；11-04 樣張，推薦 C） |
| `cloudTiles.js`、`cloud-tiles.html` | 雲嶺實地地圖地磚與地物圖庫＋示範圖「青霧觀山門」（`../shots/misc/cloud-tiles.png`、`雲嶺實地圖庫.md`；11-04 樣張，待使用者看） |
| `ashenTiles.js`、`ashen-tiles.html` | 灰燼荒原實地地圖圖庫＋示範圖「赤沙村」（`../shots/misc/ashen-tiles.png`、`灰燼實地圖庫.md`；11-04 樣張） |
| `townTiles.js`、`town-tiles.html` | 主城、霧渡鎮的城鎮圖庫與酒館、鐵匠鋪、導師殿室內，疊 HUD A（`../shots/misc/town-tiles.png`、`城鎮與室內圖庫.md`；11-04 樣張） |
| `worldmap.js`、`worldmap.html` | 大世界圖（漂浮界域、灰色未解鎖）與雲嶺區域圖（戰爭迷霧三態）（`../shots/misc/worldmap.png`、`../../archive/art/大世界圖與區域圖.md`；11-04 樣張） |
| `portraits.js`、`portraits.html` | NPC 頭像 24 位（雲嶺 9、荒原 6、傭兵 9）＋好感度表情（`../shots/misc/portraits.png`、`NPC頭像.md`；11-04 樣張） |
| `events.js`、`events.html` | 事件插圖 10 種（雲嶺背景＋荒原換背景）（`../shots/misc/events.png`、`事件插圖.md`；11-04 樣張） |
| `itemIcons.js`、`items.html` | 物品圖示 42 個：藥水、投擲瓶、補給、材料、染料、貨幣、任務物品（`../shots/misc/items.png`、`物品圖示.md`；11-04 樣張） |
| `hudIcons.js`、`hud-icons.html` | HUD 功能列 8 個圖示定稿（R＝潛行）、按鈕狀態、滑過說明卡（`../shots/misc/hud-icons.png`、`HUD功能列圖示.md`；11-04 樣張） |
| `story-icons.html` | 事件卡墨線圖示：選項 8 種、d20、線索、模型關閉、說書人、說明（`../shots/misc/story-icons.png`；11-04，6C-ART3） |
| `attr-icons.html` | 六種縮放屬性圖示（6A-1 技能卡用；`../shots/misc/attr-icons.png`） |
| `vfx.js`、`vfx.html` | 技能特效細部：火冰雷水霧毒 6 元素的飛行物、爆發、地表擴散與變體（`../shots/misc/vfx.png`、`技能特效細部.md`；11-04 樣張） |
| `regionArt.js`、`ashenRegionArt.js`、`region-map.html` | 區域插畫：雲嶺、荒原（`../shots/region/region-painted.png`、`../shots/region/region-ashen.png`；`雲嶺區域插畫.md`）。**使用者 11-04 選 B 俯視彩繪**（「這個不錯」）；`scroll` 分支是沒選上的 A 案 |
| `worldPaintedArt.js`、`world-painted.html` | 大世界圖 B 風格（`../shots/misc/world-painted.png`；取代 `worldmap.js` 的浮島畫法） |
| `mapMarks.js`、`map-marks.html` | 實地地圖標記：事件「！」、營火、腳印、石碑、物件提示、視野併塊、潛行（`../shots/misc/map-marks.png`、`地圖標記.md`；11-04 樣張） |
| `anim.js`、`anim.html` | 動畫樣張：骨架紙娃娃走路四方向、上樓、受擊、三種技能、同片段不同順序（`../shots/anim/anim.gif`、`../shots/anim/anim-strip.png`、`動畫方案.md`；11-04 示意，不代決） |
| `arcane-blade.html` | 魔導劍（#46，sword 的 form: arcane） |
| `forms.html` | 形態（變身，#48）：bear、cat、demon（summonArt.js 新 variant） |
| `raceArt.js`、`races.html`、`dragonkin.html` | 可玩種族部件與衝突規則 |
| `sideArt.js`、`side-views.html`、`races-side.html` | 真側面畫法（可調轉向） |
| `formArt.js`、`forms10.html` | 形態 10 種（定稿） |
| `enemyArt.js`、`enemies.html` | 敵人外觀：修士（含 storyDoll.js 新部件）、異形（身形 × 材質 × 元素 × 大小 × 特徵）、精英詞綴、頭目外光；頁首全組合自測 |
| `tools/enemy-dolls.html` | 盜賊三套配色（原版、斷崖幫、荒原）用正式紙娃娃畫法拍（經 5183） |
| `current.js` | 遊戲現況畫法的打包（client/src/render → IIFE），樣張「現況」欄用；重打包方法：用 main 的 vite 以 lib 模式打包 terrainArt／objectArt／skillIcon |

| `obSamples.js`、`obSamples.css` | #150／#147 三項介面樣張的共用畫法與新增排版（`ob-*`）。框、按鈕、字級直接載入現行的 `client/src/styles/index.css`（只讀）；人物 `QDoll`／`QNpc`、頭像 `QPortrait`、選大類卡上的武器 `GearArt`、技能 `SkillIcon`、戰場地磚 `CUR.drawTile`、城鎮 `TownTiles`、水池水面 `Explore.ground`；木樁、滑軌、水池石緣、武器架照 `range.html`；武器架小圖示用 `tools/obLiveIcons.js`，關鍵字小圖示取自 `client/src/ui/CreateIcons.tsx` |
| `ob-range-class.html` | 靶場「選大類」畫面（#150 第 1 點）：三張大類卡、未選／滑過／已選、「試其他武器」的武器架、確定出發。`?state=none｜hover｜selected`、`?rack=closed｜open`；手機寬 390 與桌機寬 1280 同一頁（`../shots/ob/class-*.png`、`OB與PR樣張.md`；11-11 第 3 版：文字照玩法 PM 定稿、入門招照 #148 新名單） |
| `ob-range-entry.html` | 出發後的靶場入口：`?part=master` 主城工坊師傅的選單（`state=normal｜hover`）；`?part=gran` 霧渡鎮葛蘭開的「正式選定」畫面（整頁，照現行靶場）與試打入口，`sel=mix｜one`、`hover=try｜demo`、`off=try｜kw`（`../shots/ob/entry-*.png`；第 3 版加工坊師傅的台詞，「拿起試打」帶該大類的 2 招示範招） |
| `practice-battle.html` | 測試模式戰鬥版面（#147）：`?mode=practice｜current`、`?act=attack｜move`、`?view=compare` 和現行版面並排；390 寬只是提案；第 3 版測試模式的提示句把「敵人」寫成「木樁」，移動模式的藍格只是示意（`../shots/ob/practice-*.png`） |
| `tools/ob-frame.html`、`tools/ob_shots.py` | 上面三頁的截圖外框（用 iframe 給準確的版面寬、放大拍特寫、只拍某個元件）與整批重拍的腳本（張數與參數都在腳本的 `SHOTS`）；用法在 `OB與PR樣張.md` 第 6 節 |
| `tools/obLiveIcons.js` | 自動產生：現行武器小圖示（`client/src/render/weaponIcon.ts`）打包成 IIFE，給上面兩頁的武器架用；不要手改 |
| `tools/hand-gap-compare.html` | 第 17 版 B 批待決題：parts 空手「不變寬 ea 0.09」vs「留縫 ea 0.5」的並排圖（`../shots/misc/hand-gap-compare.png`） |
| `qIcons.js`、`q-icons.html`、`tools/qicons_shots.py` | 小圖示改 Q 版的風格樣張（11-11，第一階段第 2 版，照獨立審查改過，待使用者確認方向）：武器 8、技能 8、物品 6、狀態 6、HUD 6、事件卡 4，現行在左、Q 版在右，各有實際尺寸與 4 倍放大；第 7～9 節是給使用者做決定的對照（狀態的控制類別色、技能右下的核心效果圓片、防具飾品 4 個）；最後一段是放進現行版面的情境圖。`?part=weapon｜skill｜item｜status｜hud｜event｜ctrl｜core｜gear｜scene` 只畫一類，`?part=audit` 印規則自查表，`?part=inspect` 是 1 倍圖放大 6 倍的檢查頁。現行畫法只讀（`OBLive`、`GearArt`、`AssembledIcon`、`ItemIcons`、`FX.statusIcon`、`HudIcons`；事件卡四個是 `story-icons.html` 的原樣程式）。重拍：`uv run python docs/art/sample/tools/qicons_shots.py`（`--audit` 印自查表）。圖：`../shots/qicons/`、`../closeup/qicons/`；盤點與規則：`Q版小圖示樣張.md` |
| `qIconsWeapons.js`、`q-icons-weapons.html` | 小圖示改 Q 版第 1 批：武器 17 種 53 款＋副手 4 種 8 款，一張圖放米色圓章與裝備格（`QIconsWeapons.def／paint／canvas`）；`?part=a｜b｜c｜var｜scene｜close&kind=…｜audit｜review`（`../shots/qicons/weapons-*.png`、`../closeup/qicons/weapons/`、`Q版小圖示-第1批武器.md`） |
| `tools/qicons_shots.py` | 上面兩頁與第 2 批（`q-icons-armor.html`）的重拍腳本（無頭 Chrome、靜音、`file://`）：不帶參數拍全部，`weapons` 只拍第 1 批，`armor` 只拍第 2 批，`--audit`／`--audit weapons` 印自查表，`--page … --query … --out …` 拍單張 |
| `qIconsArmor.js`、`q-icons-armor.html` | Q 版小圖示第 2 批：防具 18 種 37 款＋飾品 3 種 7 款，只放裝備格（`../Q版小圖示-第2批防具飾品.md`） |
