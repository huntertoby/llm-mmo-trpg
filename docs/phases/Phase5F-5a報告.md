# Phase 5F-5a 完成報告：灰燼荒原內容接入

規格：`docs/phases/Phase5計畫.md` 第 39 節（含決策影響盤點 39.2；佔位節順延成 40）。依據：第 1 節 5F-5a 列；19 19.1～19.9；20 20.1（餘燼集欄）、20.2、20.4、20.6；18（雲嶺 content 的寫法）；8.26.1（每鎮鐵匠＋附魔台）；#87；19.9 #1 失敗荒原 +1（5F-1 已接）；`Phase5F-1b報告.md`、`Phase5D-3b報告.md`、`Phase5F-2報告.md`／`5F-2b`、`Phase5F-3報告.md`。

## 交付

| 項目 | 檔案 |
|---|---|
| 規格 39 節（決策影響盤點：渡口、世界事件、懸賞、封印鑰匙、商店、鐵匠、提示、掉落、遭遇、快照） | `docs/phases/Phase5計畫.md` |
| 地點圖：18 個地點（19.3 扣掉裂界門）、17 條連線、黑曜谷隱藏（感知／任務線索）、熔心坑 `unlock_flag: heart_pit_open`、灰渡口 `gate_to: cloud_ridge` | `content/world/maps/ashen_waste.yaml` |
| Boss 地圖「熔心坑」（12×12；外圈岩漿、南側 2 條通路、4 個冷卻井＝預放水表面、灰燼之心在中央） | `content/maps/molten_heart_pit.yaml` |
| 熔岩獸群 9 種＋精英熔核領主＋寒燼蜥＋熔晶魅；召喚物餘燼幼蜥（外觀表一列） | `content/units/*.yaml`、`content/units/summons/summon_ember_whelp.yaml`、`content/summon_looks.yaml` |
| 變體 5（雷殼甲蟲、焦石背熊、斷崖幫火槍手、熔爐督工「鍛疤」、角魔狂信者）、詞綴 2（熾熱的、硬殼的） | `content/world/enemies.yaml` |
| 區域 Boss 灰燼之心：3 階段（殼／呼吸／熔毀，`hp_below` 600／300）、開場「熔殼」、第 2 階段召喚 2 隻餘燼蜥、第 3 階段 8 格火地 | `content/units/ashen_heart.yaml` |
| 新技能 8 招（只給敵人）：熔岩噴發、熔心吸氣、熔心吐息、熔心爆、熔流潰堤、產下幼蜥、硫煙吐息、餘燼啃咬 | `content/skills/skill_*.yaml` |
| 新狀態 4 個：熔核爆裂（死後留火 2 回合）、寒燼爆裂（死後留冰）、熔殼、硬殼 | `content/statuses.yaml` |
| 遭遇表：16 個地點、32 種陣容（含三方「獸群襲擊運輸隊」「赫琳的背叛」）；三村落 `objective: defend`；熔心坑 `armor_mods`；線頭到期變化「擴散的蜥群」 | `content/world/encounters/ashen_waste.yaml` |
| 事件骨架 16 個（19.4 的 15＋角魔古祭壇的機遇）、情境模板 16 個 | `content/world/events/ashen_waste.yaml`、`content/world/situations/ashen_waste.yaml` |
| NPC 人設卡 6 張（爐叔由 pending 搬來；刪 `world/pending/`） | `content/world/npcs/ashen_waste.yaml` |
| 任務：主線第 2 章「灰燼之心」5 步（第 3 步給劇情技能「冷鋒」、第 2 步記 `ashen_convoy_stopped`、阿岳同行）、區域鏈「鐵娘的委託」3 步、隱藏任務「黑曜谷的寒燼」；雲嶺主線最後一步加旗標 `mist_rift_done`（第 2 章從這裡接） | `content/world/quests/ashen_waste.yaml`、`content/world/quests/cloud_ridge.yaml` |
| 社交：聊天 12 條、事件好感度 4 條、酒館傳聞 6 條（含 20.4「霧與火相遇之處」）、爐叔聊天「冰與火在同一隻蜥蜴身上」、機遇提示 | `content/world/social/ashen_waste.yaml` |
| 商店「鐵娘的廢鐵攤」（20.1 餘燼集欄）；鐵匠「爐叔鐵鋪」、附魔台；新材料餘燼羽、硫磺結晶、黑曜片（特產每週 5）；荒原材料標區域；新材料的傾向 | `content/world/shops/ashen_waste.yaml`、`content/world/crafting.yaml`、`content/world/items.yaml` |
| 掉落：`regions.ashen_waste`（點燃、倒地、中毒）、家族材料、`bosses.ashen_heart`（熔心晶＋史詩） | `content/world/loot.yaml` |
| 賽季：荒原懸賞 3 張（第 4 天起）、世界事件 #2 熔岩潰堤、鑰匙來源「打倒熔心坑的灰燼之心」 | `content/world/season.yaml` |
| 說書語氣 | `content/world/narration.yaml` |
| 世界端三個資料欄位（39.4）：`GoalSpec.locations`；`LocationEncounters.objective`（`make_encounter` 沒指定時用）；`LocationEncounters.armor_mods`（`ArmorMods`／`ArmorMod`，`prepare_battle` 經 `armored()` 套用） | `src/trpg/content/world_season.py`、`world_encounters.py`、`src/trpg/world/season_board.py`、`solutions.py`、`battle.py` |
| 隱藏配方提示接到傳聞：有地點圖且有聊天與骨架的區域，提示文字要出現在該區的酒館傳聞、聊天或線頭文字裡（載入檢查） | `src/trpg/content/world_crafting.py`、`library.py` |
| 前端：4 個新狀態的圖示 | `client/src/render/statusIcon.ts`、`statusIcon.test.ts` |
| 產生檔 | `client/src/battle/fixtures/glossary.json`、`client/src/render/fixtures/skill_icons.json`、`tests/skillgen/fixtures/refactor_3wr2.json`、`tests/cli/snapshots/` |
| 模擬腳本 | `scripts/ashen_waste_sim.py`（新） |
| 測試（新） | `tests/world/test_ashen_waste.py`（10）、`tests/content/test_ashen_waste_content.py`（5）、`tests/content/test_world_crafting.py`（+3） |

## 做法摘要

- **只寫資料、引擎不動**：熔岩獸的「熔核爆裂」用 5A-M1 的 `on_death_surface`（火、半徑 0、2 回合）；Boss 三階段用 5F-2 的 `hp_below`；熔心爆、熔流潰堤用 5F-2b 的十字臂長 2。`LOG_FORMAT` 不升版（新內容只加技能、狀態、單位、地圖，舊內容結算不變）。
- **世界端三個小欄位**都是資料驅動、有預設值、不耗亂數：`GoalSpec.locations`（熔岩潰堤只算三村落）；`LocationEncounters.objective`（村落遇敵是守點；骨架的戰鬥解法照舊優先）；`LocationEncounters.armor_mods`（灰燼之心護甲：世界旗標 `ashen_heart_hardened` +1、劇情旗標 `ashen_convoy_stopped` −1、線頭 `convoy_intercepted` −1，夾在 −3～+1）。世界狀態沒有新欄位，存檔不升版。
- **世界事件**：#2 熔岩潰堤（第 4～7 天，門檻 24 照上線人數調整，下限 1/4）成功給 `heart_pit_open`＋全服封印鑰匙 +5（5F-3 的 `seal_keys` 效果第一次有資料）；失敗也給 `heart_pit_open`（事件結束才開）＋荒原建議等級 +1。#3 封印共鳴不改，新增鑰匙來源「打倒熔心坑的灰燼之心」；荒原 3 張懸賞第一次搶下照 `bounty_claimed` 自動給鑰匙。
- **渡口**：雲嶺渡口（`ashen_waste_open`）傳送到餘燼集、灰渡口傳回霧渡鎮，都走既有 `teleport`；荒原第一次有地點圖，所以 5F-1b 的旗標修正從這段起真正有作用。
- **提示接口**：`CraftingRules.hints_at` 的兩個荒原提示寫成酒館傳聞與爐叔的聊天傳聞；載入時加一條檢查（有地點圖、且有聊天與骨架的區域，提示文字要出現在該區的傳聞、聊天或線頭文字裡；雲嶺的「雷雨夜的霧最濃」在骨架 4 的線頭裡，照樣通過）。
- **手寫被動「餘燼烙印」不放到單位身上**（`tests/content/test_skill_triggers_content.py` 的規則），所以「啃咬點燃」另做敵人技能「餘燼啃咬」。

## 模擬（`scripts/ashen_waste_sim.py`，大世界真實路徑 `prepare_battle`；主角＋2 名系統傭兵，8 種 build 輪流，效用 AI）

| 場景 | 場數 | 勝率 | 平均輪數 | 備註 |
|---|---|---|---|---|
| 荒原一般遭遇（10 個營地、村落、遺跡輪流；主角＝地點建議等級；村落守點） | 40 | 97%（39/40） | 4.6 | 唯一敗場：鐵爐村（8 級守點）healer |
| 灰燼之心（9 級、HP 160 現值、護甲不調整） | 40 | 92%（37/40） | 9.6 | 到第 2 階段 100%、第 3 階段 92%；敗場 Boss 剩 45% |
| 灰燼之心 HP 200（候選；熔岩噴發改成身邊一圈之前量的） | 40 | 87% | 10.9 | 敗場 Boss 剩 17% |
| 灰燼之心 HP 240（同上） | 40 | 85% | 11.2 | 敗場 Boss 剩 32% |

- 加 HP 幾乎不降勝率、只拉長輪數（超過 5F-2b 的 6～10 輪），所以維持 160；勝率高於雲嶺 Boss 的目標 70～80%，見待 PM 決定 1。

## 檢查

（交件前填）

## 代決（最保守預設；規格 39.6 之外的實作細節）

| # | 事項 | 代決 |
|---|---|---|
| 5F5a-1～10 | 見規格 39.6 | 裂界門不放地點圖、熔心坑的開放時機、村落沒有商店可關、村落一律守點、攔截「批」的近似、護甲整場套、引擎做不到的機制近似、熔岩洞窟借地圖、冷卻井等只留線頭、阿岳與碎晶之主的卡 |
| 5F5a-11 | 「怕水」 | 引擎的元素沒有水（水只是表面），所以弱點只做冰（+50%）；水由地圖的水表面、冷卻井（熔心坑 4 格預放水）與玩家的水瓶發揮。熔殼只會被冰打碎 |
| 5F5a-12 | 「站在火上回血」「受火回血」 | 用火抗（−50%；焦岩巨像、灰燼之心 −75%）近似 |
| 5F5a-13 | 熾熱的（相鄰敵人每回合小火傷） | 非召喚物沒有光環，用加技能「餘燼啃咬」（近戰點燃）近似；只能套近戰 |
| 5F5a-14 | 硬殼的（前 2 次受擊減半） | 開場 2 回合受到的骰值傷害減半 |
| 5F5a-15 | 熔核蛞蝓「爬過的格子留火地」 | 用燈油瓶（造油面，遇火燃燒）近似 |
| 5F5a-16 | 熔爐母獸「每 2 回合產 1 隻」 | 召喚原語，冷卻 2、幼蜥持續 2 回合（預算上限）；召喚物沒有開場狀態，幼蜥倒下不留火 |
| 5F5a-17 | 雷殼甲蟲「硬殼帶電反傷」 | 翻滾撞擊換成雷掌，沒有反傷 |
| 5F5a-18 | 寒燼蜥 | 變體換不了元素修正與開場狀態，做成獨立範本（怕火、死後留冰面，帶批註寒霜） |
| 5F5a-19 | 三方混戰 | 引擎只有一個第三方：「赫琳的背叛」的熔岩獸與盜賊同一邊、祭司護衛是敵方；第 4 步放在角魔古祭壇（熔心坑的戰鬥＝Boss 戰） |
| 5F5a-20 | 主線第 2 章的前置 | 任務條件不能跨區指任務，所以雲嶺主線最後一步加劇情旗標 `mist_rift_done`，第 2 章以它為 start |
| 5F5a-21 | 主線第 1 步 | 和鐵娘說話或持有「運輸隊的時刻表」任一 |
| 5F5a-22 | 荒原懸賞 | 第 4 天起貼出；19.8 只寫寒燼蜥王的詞綴（再生的），熔爐督工、熔核領主用荒原詞綴「硬殼的」；熔爐督工＝盜賊隊長的變體「鍛疤」（鞭），也是熔爐督工營的固定精英 |
| 5F5a-23 | 熔岩潰堤門檻 | 24（約每人 3 場），照上線人數調整、下限 1/4 |
| 5F5a-24 | 店名、鐵鋪名、附魔台名、商店好感度 | 鐵娘的廢鐵攤（消費一次 +2、每天最多 +4，同柳記）、爐叔鐵鋪、餘燼附魔台 |
| 5F5a-25 | 新材料 | 餘燼羽（火塵蝠）、硫磺結晶（硫煙獸）、黑曜片（只在商店每週 5，沒有採集點機制）；傾向用最接近的現成詞條 |
| 5F5a-26 | 冷鋒 | 3×3 範圍：清表面→造冰面→1d4 冰傷；「對火屬性敵人加傷」靠熔岩獸的冰弱點，不另寫條件 |
| 5F5a-27 | 事件骨架 10「疤面」 | 只放熔爐督工營（精英巢穴一定有精英＝「戰鬥（精英）」）；follows 雲嶺線頭「二當家記恨你」 |
| 5F5a-28 | 說書語氣 | 「粗獷：短句、口語，常用廢鐵、灰燼與火的比喻」 |
| 5F5a-29 | 火塵蝠、噴岩龜的遠程 | 拿火杖（focus），算遠程；熔核蛞蝓、硫煙獸用近戰武器，所以一場遠程上限 2 只會是蝠、龜、火槍手 |

## 需要標 `enemy_only` 的技能（5F-3b 還沒進 main）

`skill_lava_spout`、`skill_heart_inhale`、`skill_heart_exhale`、`skill_heart_meltdown`、`skill_magma_breach`、`skill_summon_ember_whelp`、`skill_sulfur_breath`、`skill_ember_bite`（共 8 招；劇情技能「冷鋒」是玩家技能，不標）。

## 待 PM 決定

1. **灰燼之心偏簡單**：40 場 92%、9.6 輪（雲嶺 Boss 目標 70～80%、6～10 輪）。加 HP 只拉長輪數；若要降勝率，建議調傷害（例如熔心爆 3d8 → 3d10、吐息加燃燒 2 回合）或熔殼的減傷，請 PM 定方向再量。一般遭遇 97% 也偏高（3 人隊＋系統傭兵）。
2. 規格 39.6 的代決 1～10 與上表 11～29，特別是：裂界門不進地點圖、熔心坑失敗時第 8 天才開、村落沒有商店可關、怕水只做冰、「批」的近似。
3. 「失守的村落商店關閉」若要做，需要村落商店與「哪一村失守」的分村進度（每村一條進度或每村一個世界事件），屬規則變更。
4. 新的 4 個狀態圖示、餘燼幼蜥借戰狼畫法、熔岩獸外觀（目前用預設），請美術 PM 看。
5. `tests/skillgen/test_budget.py` 在 main 上少了 5F-4b 的 `league_truce`（slow 測試會失敗），本段一併補上。
