# Phase 6C-ART2 完成報告：事件插圖 10 種

實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6C-ART2 列；`docs/art/Phase6剩餘美術移植需求.md` 第 3 節；`docs/art/事件插圖.md` 第 1～3 節；樣張 `docs/art/events.png`（`sample/events.html`、`sample/events.js`）。開工前已 `git merge main`（無衝突，含 `docs/art/Phase6剩餘美術移植需求.md`）。

> 只換外觀、不改規則：沒碰引擎、`src/trpg/world`、走路、地圖地形與物件。伺服器只加欄位。沒碰 6N-1（`render` 人物動畫、`battle` 播放）、6P-2（`src/trpg/world`、走路 schema）、6B-ART1（`render` 地形物件建築、`content/world/fields`、`content/fields.py`）的檔案；`render/` 只新增檔案，既有的荒原地形與物件畫法、紙娃娃、異形只匯入不改。

## 1. 做了什麼

| 項目 | 檔案 |
|---|---|
| 骨架欄位 | `src/trpg/content/world_events.py`：`EventArtId`（10 種場景的 `Literal`）、`EVENT_ART_IDS`、`EventSkeletonDef.art`（選填，`None`＝不寫）。只接受已知 ID，其他值載入時就驗證失敗 |
| 內容 | `content/world/events/cloud_ridge.yaml` 22 個、`ashen_waste.yaml` 16 個骨架都填了 `art`（對照表見第 3 節） |
| API（只加欄位） | `EventView.art`（骨架的 `art`）、`EventView.region`（角色所在區域，背景用）。`client/openapi.json`、`client/src/api/schema.d.ts` 已重產 |
| 畫法 | 新檔 `client/src/render/eventArt.ts`（10 種場景、挑場景、背景、小牌、暗角、金邊、快取）、`client/src/render/eventArtParts.ts`（`events.js` 用到的地面、地物、小圖示，從 `explore.js`、`cloudTiles.js`、`ashenTiles.js`、`realms.js`、`hud.js` 移植）。荒原的焦土、岩漿、枯木、枯草、破木箱直接用遊戲已有的 `ASHEN_TERRAIN`、`ASHEN_OBJECTS`；人物用 `drawFigure`（C 畫風紙娃娃）；霧狼、灰燼犬用 `resolveCreature`＋`drawCreature` |
| 事件卡 | `client/src/world/EventCard.tsx`：拿掉 6C-7 的 `SCENES`、`sceneIndex` 色塊和中央大圖示；`art_url` 有值時照舊用圖片，否則畫事件插圖。`story.css`：`.world-event-art.drawn` 用 364:156 等比縮放到卡寬（原本固定 84px 高） |
| 開發用頁面 | `client/event-art-gallery.html`＋`src/dev/eventArtGallery.tsx`（`?mode=cards` 正式事件卡；`?mode=raw` 插圖 1:1，和 `events.png` 對照；`&only=ambush,chest` 只看幾種） |
| 測試 | 後端：新檔 `tests/content/test_world_event_art.py`（19 個）、`tests/api/test_world_story.py` 加 1 個。前端：新檔 `client/src/render/eventArt.test.ts`（14 個） |
| 截圖 | `docs/art/6cart2_cards.jpg`（14 張事件卡：雲嶺 10 種＋荒原 4 種）、`docs/art/6cart2_raw.jpg`（插圖 1:1，排法同 `events.png`）、`docs/art/6cart2_event_card.jpg`（完整事件卡：插圖＋對話框＋選項＋情境判定） |

## 2. 畫法細節

- 每張是 7×3 格（52 虛擬格，364×156），依（場景、背景、解析度 2）離屏畫好、轉成圖片網址快取；事件卡上當背景圖，照卡寬等比縮放。
- 場景擺法、顏色、小牌文字與圖示都照 `events.js` 逐行移植；沒有亂數（`Math.random` 測試確認沒被呼叫），需要變化的地方用座標當種子（照樣張的兩套種子：`explore.js` 的 xorshift、`realms.js` 的 mulberry32）。
- **挑場景**（`eventArtScene`）：`art` 是已知 ID 就用它；不認得的值退回 `stele`；沒寫 `art` 時照第一個不是放棄的選項的圖示查表（戰鬥、潛行＝`ambush`；說服＝`villager`；調查＝`stele`；硬闖＝`trap`；機遇＝`altar`；交涉＝`caravan`；只剩放棄＝`camp`）。選項圖示沿用 6C-7 的 `solutionIcon`。
- **背景**（`eventArtBg`）：`region` 是 `ashen_waste` 用荒原背景（焦土＋右上兩格岩漿、枯木林、角魔祭壇、紅光、熔岩材質的灰燼犬）；其他區與沒有區域用雲嶺背景。

## 3. 對照表（事件骨架 → 場景）

**雲嶺（22）**

| 骨架 | 內容 | 場景 |
|---|---|---|
| wounded_peddler | 受傷的行商、霧狼群 | villager |
| lost_acolyte | 迷路的道童 | villager |
| gang_toll | 斷崖幫哨兵收過路費 | ambush |
| pine_elder_go | 古松下的老人下棋 | villager |
| cliff_lingzhi | 崖上的靈芝 | chest |
| monks_dispute | 兩名修士爭論源晶 | villager |
| gang_deserter | 盜賊逃兵、擋追兵 | ambush |
| possessed_hunter | 被霧魅附身的獵人 | anomaly |
| broken_ferry | 被砸的渡船 | villager |
| bear_den | 石背熊母子 | ambush |
| crane_envoy | 雲鶴使盤查 | villager |
| storm_altar | 雷雨中的古松祭壇 | altar |
| tomb_sword | 劍冢的殘劍 | stele |
| shard_convoy | 盜賊押送隊 | caravan |
| poison_spring | 藥師谷的毒泉 | trap |
| tavern_storyteller | 酒館的說書人 | camp |
| lantern_patrol | 夜裡的燈籠隊、霧行者 | ambush |
| fox_traveler | 狐族旅人換補給 | caravan |
| ayue_request | 阿岳打山豹 | ambush |
| runaway_furnace | 失控的丹爐、毒霧 | trap |
| frost_chime_riddle | 白狐霜音的謎 | stele |
| granny_past | 渡婆婆的舊帳 | villager |

**灰燼荒原（16）**

| 骨架 | 內容 | 場景 |
|---|---|---|
| laotie_dig | 拾荒者挖舊機械 | chest |
| water_caravan | 迷路的運水隊 | caravan |
| ashen_deserter | 斷崖幫逃兵 | ambush |
| horned_pilgrim | 角魔巡禮者、古祭壇 | altar |
| burned_bandit | 燒傷的盜賊 | villager |
| cooling_well_relic | 冷卻井（遺跡） | stele |
| furnace_brood | 熔爐母獸 | ambush |
| forge_smith | 鐵爐村的鐵匠要黑曜片 | caravan |
| sandstorm | 沙暴（天氣異象） | anomaly |
| scarface_revenge | 疤面報仇 | ambush |
| fortress_stele | 廢墟要塞的石碑 | stele |
| lost_pup | 赤沙村的孩子找幼犬 | villager |
| ashen_convoy | 盜賊運輸隊 | caravan |
| molten_lord_pool | 熔核領主 | ambush |
| tavern_veteran | 酒館的老兵 | camp |
| noon_altar | 正午的角魔古祭壇 | altar |

統計：ambush 9、villager 9、caravan 5、stele 4、altar 3、trap 2、camp 2、chest 2、anomaly 2、friend 0（共 38）（`friend` 留給之後的朋友足跡，目前沒有對應的骨架）。

## 4. 測試與檢查

- 後端：`UV_NO_SYNC=1 uv run pytest -q tests/content tests/api -n 8`：3277 過、1 略過（既有的開發模式略過）。`ruff check`、`ruff format --check`、`mypy src/trpg/content/world_events.py src/trpg/api`、`lint-imports`（13 個契約）通過；`uv run trpg content check` 通過。
- 前端：`vitest run src/world src/render/eventArt.test.ts src/render/inkDoll.test.ts src/render/inkCreature.test.ts src/dev`：32 檔 383 個全過；`tsc --noEmit`、`pnpm build` 通過。
- 新測試涵蓋：欄位只接受 10 種 ID（未知、大小寫不同、空字串、數字都拒絕）、不寫是 `None`、兩區每個骨架都有 `art`、`EventView` 帶 `art` 與 `region`；挑場景（已知、未知退回古碑、沒寫照選項圖示的每一列）、背景依區域；10 種 × 2 背景各畫兩次指令完全相同且不呼叫 `Math.random`、10 種彼此不同、荒原與雲嶺不同；快取（同場景同背景只畫一次）；事件卡沒有 `art` 時照選項圖示挑場景且不再出現色塊漸層、有 `art` 與區域時照它畫、`art_url` 優先。
- 沒跑全量。
- 實測：自己開的 vite（埠 5322，沒開伺服器）。內建瀏覽器的分頁已滿（都是別人的分頁，沒有關），改用 Edge 無頭模式截圖。`?mode=raw` 和 `events.png` 逐張比對：擺法、顏色、小牌都一致；荒原換成焦土、熔岩、枯木與熔岩材質的犬。

## 5. 檢查清單（需求第 3 節第 7 點）

- [x] 10 種場景和 `events.png` 一致，荒原換背景（`docs/art/6cart2_raw.jpg`；荒原 4 種排在後面，和樣張第 2 節同一組）
- [x] 同一事件每次畫出來都一樣（沒有亂數；測試逐指令比對；依場景、背景快取）
- [x] 對照表合理（第 3 節；請美術 PM 驗收時一起看）
- [x] 沒寫 `art` 的事件照第 4 點挑場景（`ICON_ART` 表；不認得的值退回 `stele`）

## 6. 待 PM 決定

1. **沒寫 `art` 時的退路（規格互相衝突，照需求文件做）**：派工訊息寫「沒有 art 的骨架照現行色塊」，但 `Phase6剩餘美術移植需求.md` 第 3 節第 4、6 點寫「照第一個不是放棄的選項的圖示挑」、「拿掉 6C-7 的色塊佔位（`SCENES`、`sceneIndex`）」，檢查清單也要求照第 4 點挑。我照需求文件做（色塊已拿掉）。目前 38 個骨架都有 `art`，這條退路只影響之後新增、沒寫 `art` 的骨架。若要恢復色塊，改 `EventCard.tsx` 的 `EventArt` 一處即可。
2. **`EventView.region` 是新加的欄位**：插圖背景要依區域換，事件卡原本拿不到區域（只有 `skeleton`），所以伺服器多給 `region`（角色所在區）。只畫。
3. **對照表**是我依骨架內容挑的（第 3 節），比較主觀的幾個：`pine_elder_go`、`monks_dispute`、`crane_envoy` 用 `villager`（以人物為主）；`lantern_patrol` 用 `ambush`（霧行者）而不是 `friend`；`runaway_furnace`、`poison_spring` 用 `trap`（危險地形）；`sandstorm` 用 `anomaly`。`friend` 目前沒有骨架用。
4. **插圖變高了**：照需求「照卡寬等比縮放」，插圖高度從 6C-7 固定的 84px 變成卡寬 × 156/364（卡寬 320 時約 137px）。事件卡在 HUD 中央會比以前高一些。
5. **小牌圖示「古碑」（問號）與「村民求助」（驚嘆號）是黑色，在深色小牌上幾乎看不到**：樣張就是這樣（`events.png` 一樣看不清），照樣張移植沒改；若要改，請美術 PM 給顏色。
6. **照樣張的小地方**：雲嶺的陷阱草叢、村民求助與商隊的木箱，樣張用的是荒原的枯草、破木箱畫法，照搬；小牌字型改成遊戲字型清單（`Noto Sans TC` 優先，樣張是微軟正黑體）。
7. **同一種事件的 2～3 種擺法**（`事件插圖.md` 第 1 節「之後再做」）沒做。
8. **截圖是開發用頁面**（正式事件卡元件、假資料），不是實際走路碰到事件；`6cart2_event_card.jpg` 用 6C-7 的 `story-gallery.html?mode=event`（假事件沒有 `art`，所以照第一個選項「查看」挑到古碑，順便示範退路）。

## 7. 複雜度例外

沒有新增 `# noqa`。
