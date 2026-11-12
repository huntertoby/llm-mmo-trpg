# OB-7 遭遇歸類表（#155，待開發 PM 確認後才改 YAML）

> 依據：09 9.6.6「遭遇大小」（路邊 1～2、地點戰 2～3、精英巢穴／頭目／賽季 Boss 照原設計；只算敵方，第三方與戰鬥中召喚不算）、18 18.7.1（渡口 2 隻＝1 近戰＋1 弓手）、#155。
> 歸類方法：看陣容在實地地圖 `content/world/fields/<區>/*.yaml` 的 `spawns` 怎麼用——**有 `patrol` 的巡邏隊＝路邊**；**站著不動的駐守、新手與主線固定戰（`win_battle`）、守點戰、線頭到期變化＝地點戰**；**精英巢穴（`elite_lair` 的固定精英）、懸賞（`world/season.yaml`）、懸賞型變化（疤面）、Boss 地點＝精英／頭目**。
> 選人規則：保留不同種類（混族）、遠程不超過地點上限（雲嶺 2、雲海吊橋 1、荒原 2）；路邊一律先改成 2 隻（1～2 的上限，最保守、不動 schema 的 `MIN_GROUP_SIZE = 2`）。
> 「R」＝遠程、「E」＝精英範本。

## 雲嶺（`content/world/encounters/cloud_ridge.yaml`）

| 陣容 | 用在哪 | 歸類 | 現在 | 改成 | 改法 |
|---|---|---|---|---|---|
| bandit_raiders | 渡口石階駐守，新手第 1 步固定戰 | 地點戰（新手） | 3 | **2** | 拿掉 1 名 `bandit_rookie` → `bandit_rookie`＋`bandit_archer_rookie`(R)（18.7.1 明寫） |
| bandit_shield_line | 渡口石階夜間巡邏 | 路邊 | 3 | **2** | 拿掉 1 名 `bandit` → `bandit`＋`bandit_shieldbearer` |
| mist_wolf_pack | 竹林駐守，新手第 2 步固定戰 | 地點戰（新手） | 3 | 3 | 不改 |
| bandit_wolf_handler | 竹林巡邏 | 路邊 | 3 | **2** | 拿掉 1 名 `mist_wolf` → `bandit`＋`mist_wolf` |
| sect_patrol | 沒有地點引用（6F-4c 起不用） | — | 4 | 4 | 不改（疑問 Q5） |
| terrace_patrol | 梯田田埂巡邏 | 路邊 | 2 | 2 | 不改 |
| terrace_clash | 梯田駐守，新手第 3 步固定戰（三方） | 地點戰（新手） | 2＋第三方 1 | 2＋1 | 不改 |
| temple_gate_guard | 青霧觀山門駐守 | 地點戰 | 3 | 3 | 不改 |
| hunter_beasts | 獵戶小屋巡邏 | 路邊 | 3 | **2** | 拿掉 1 名 `mist_wolf` → `mist_wolf`＋`mountain_leopard` |
| cliff_gang_core | 斷崖幫寨駐守 | 地點戰 | 4 | **3** | 拿掉 `bandit` → `bandit_shieldbearer`＋`bandit_archer`(R)＋`bandit_captain`(E) |
| cliff_gang_hounds | 斷崖幫寨木棧道巡邏 | 路邊 | 4 | **2** | 留 `bandit_archer`(R)＋`mist_wolf`（和竹林巡邏的盜賊＋狼區隔） |
| altar_wardens | 古松祭壇駐守 | 地點戰 | 3 | 3 | 不改 |
| sword_array | 雲海吊橋北橋頭駐守 | 地點戰 | 4 | **3** | 拿掉 1 名劍陣弟子 → `sect_array_disciple`×2＋`sect_array_stone`（疑問 Q1） |
| bridge_patrol | 雲海吊橋巡邏（遠程上限 1） | 路邊 | 3 | **2** | 拿掉 `sect_acolyte` → `sect_swordsman`＋`sect_crane_archer`(R) |
| valley_keepers | 藥師谷駐守 | 地點戰 | 3 | 3 | 不改 |
| valley_beasts | 藥師谷谷口巡邏 | 路邊 | 3 | **2** | 拿掉 1 名 `mountain_leopard` → `mountain_leopard`＋`stoneback_bear` |
| furnace_steward | 丹爐洞駐守 | 地點戰（含精英執事） | 4 | **3** | 拿掉 `sect_acolyte` → `sect_steward`(E)＋`sect_swordsman`＋`sect_warrior_monk` |
| furnace_tide | 丹爐洞南水房駐守 | 地點戰 | 4 | **3** | 拿掉 1 名 `sect_swordsman` → `water_alchemist`＋`sect_swordsman`＋`sect_mist_walker` |
| north_slope_pack | 北坡獵場（精英巢穴，加狂暴霧狼） | 精英巢穴 | 2＋精英 | 不改 | 照原設計 |
| north_wolf_king_pack | 懸賞「北坡狼王」 | 懸賞 | 3＋精英 | 不改 | 照原設計 |
| lake_hunters | 冬湖東岸駐守 | 地點戰 | 3 | 3 | 不改 |
| lake_bears | 冬湖湖心駐守（三方） | 地點戰 | 2＋第三方 2 | 不改 | 只算敵方 2 |
| tomb_array | 劍冢劍陣石台駐守 | 地點戰 | 4 | **3** | 拿掉 `sect_mist_walker` → `sect_array_disciple`×3（疑問 Q1） |
| tomb_swordsmen | 劍冢外圍巡邏 | 路邊 | 4 | **2** | 留 `sect_mist_walker`＋`thunder_talisman_caster`(R) |
| mist_swordsman_band | 懸賞「霧中劍客」 | 懸賞 | 2＋精英 | 不改 | 照原設計 |
| rift_wraiths | 源晶裂痕北側駐守（三方） | 地點戰 | 3＋第三方 2 | 不改 | 只算敵方 3 |
| rift_scavengers | 源晶裂痕南側駐守（三方） | 地點戰 | 4＋第三方 2 | **3** | 拿掉 `mist_wraith` → `bandit`＋`bandit_archer`(R)＋`shard_golem`（霧魅留給北側那隊） |
| crane_nest | 鶴歸崖崖頂駐守（三方） | 地點戰 | 2＋第三方 3 | 不改 | 只算敵方 2 |
| crane_cliff_bear | 鶴歸崖下層駐守（三方） | 地點戰 | 2＋第三方 1 | 不改 | |
| summit_patrol | 沒有地點引用（5F-2 起保留不用） | — | 4 | 4 | 不改（疑問 Q5） |
| mist_lock_court | 雲頂觀 Boss 戰 | 頭目 | 4 | 不改 | 照原設計 |
| scarface_risen | 斷崖幫寨線頭到期變化（疤面＝懸賞精英，連心的） | 精英（懸賞型） | 3＋精英 | 不改 | 照原設計（疑問 Q3） |
| temple_traitor | 山門線頭到期變化＝主線第 1 章叛徒戰（`win_battle`） | 地點戰（主線固定戰，含精英執事） | 3＋精英＝4 | **2＋精英＝3** | 拿掉 1 名 `bandit` → 精英 `sect_steward`＋`bandit`＋`sect_swordsman`（疑問 Q3） |

## 灰燼荒原（`content/world/encounters/ashen_waste.yaml`）

| 陣容 | 用在哪 | 歸類 | 現在 | 改成 | 改法 |
|---|---|---|---|---|---|
| lizard_swarm | 焦土外圍駐守 | 地點戰 | 3 | 3 | 不改 |
| hound_pack | 焦土外圍南邊巡邏 | 路邊 | 3 | **2** | 拿掉 1 名 `ash_hound` → `ash_hound`＋`ember_lizard` |
| lizard_brood | 焦油坑南側巡邏 | 路邊 | 4 | **2** | 留 `furnace_matriarch`＋`ember_lizard` |
| beetle_line | 熔岩洞窟主通道巡邏 | 路邊 | 3 | **2** | 拿掉 `ash_hound` → `lava_beetle`＋`lava_tortoise` |
| colossus_smoke | 枯木林小路巡邏 | 路邊 | 3 | **2** | 拿掉 `fire_dust_bat` → `scorched_colossus`＋`sulfur_beast` |
| deadwood_sulfur | 枯木林駐守 | 地點戰 | 3 | 3 | 不改 |
| mire_slugs | 灰泥沼駐守 | 地點戰 | 3 | 3 | 不改 |
| mire_mix | 灰泥沼小路巡邏 | 路邊 | 3 | **2** | 拿掉 `sulfur_beast` → `magma_slug`＋`fire_dust_bat` |
| well_guardians | 冷卻井駐守 | 地點戰 | 3 | 3 | 不改 |
| tar_tortoises | 焦油坑岩台駐守 | 地點戰 | 3 | 3 | 不改 |
| tar_brood | 焦油坑母獸巢駐守 | 地點戰 | 3 | 3 | 不改 |
| cave_beetles | 熔岩洞窟洞口駐守 | 地點戰 | 3 | 3 | 不改 |
| cave_lord | 熔岩洞窟深處駐守（熔核領主精英，一般營地） | 地點戰（含精英） | 3 | 3 | 不改 |
| obsidian_frost | 黑曜谷谷底駐守 | 地點戰 | 3 | 3 | 不改 |
| obsidian_mix | 黑曜谷岩棚駐守 | 地點戰 | 3 | 3 | 不改 |
| fortress_beasts | 廢墟要塞東牆外巡邏 | 路邊 | 3 | **2** | 拿掉 `fire_dust_bat` → `scorched_colossus`＋`lava_beetle` |
| scavenger_beasts | 舊鐵哨站外圍巡邏 | 路邊 | 3 | **2** | 拿掉 1 名 `ash_hound` → `ash_hound`＋`scorched_stoneback` |
| convoy_guard | 運輸道路中央駐守 | 地點戰 | 4 | **3** | 拿掉 1 名 `bandit` → `bandit`＋`bandit_shieldbearer`＋`ashen_gunner`(R) |
| convoy_raid | 運輸道東段駐守（三方） | 地點戰 | 3＋第三方 2 | 不改 | |
| overseer_crew | 熔爐督工營（精英巢穴，加 forge_scar） | 精英巢穴 | 3＋精英 | 不改 | 照原設計 |
| overseer_guard | 同上 | 精英巢穴 | 3＋精英 | 不改 | 照原設計 |
| fortress_bandits | 廢墟要塞內庭駐守 | 地點戰 | 3 | 3 | 不改 |
| altar_wraiths | 角魔古祭壇駐守 | 地點戰 | 3 | 3 | 不改 |
| altar_betrayal | 角魔古祭壇的抽籤陣容（主線第 2 章「赫琳的背叛」，三方；不在實地地圖） | 地點戰 | 3＋第三方 3 | 不改 | |
| village_raid_light／mid／heavy | 三村落守點戰（個人駐守） | 地點戰 | 3 | 3 | 不改 |
| forge_scar_band、molten_lord_band、frost_king_band | 懸賞 | 懸賞 | 3／3／2＋精英 | 不改 | 照原設計 |
| brood_spread | 焦油坑線頭到期變化（「多一隻餘燼蜥」） | 地點戰 | 4 | **3** | 拿掉 1 名 `ember_lizard` → `furnace_matriarch`＋`ember_lizard`×2（疑問 Q3） |
| ashen_heart_court | 熔心坑 Boss 戰 | 頭目 | 3 | 不改 | 照原設計 |

**合計要改**：雲嶺 16 組（路邊 8、地點戰 8）、荒原 9 組（路邊 7、地點戰 2）。schema 不動（`MIN_GROUP_SIZE` 2、`MAX_GROUP_SIZE` 4 照舊；精英巢穴、懸賞、頭目仍可到 4）。

## 疑問（請開發 PM 確認，必要時轉玩法 PM）

- **Q1 劍陣**：18.2.1 劍陣弟子「三人一組」、陣容例「劍陣弟子 ×3＋陣眼石靈」共 4 隻。改 3 隻時：吊橋 `sword_array` 我提「弟子 ×2＋陣眼石靈」（陣眼石靈不行動，保留陣眼主題）、劍冢 `tomb_array` 提「弟子 ×3」（保留三人一組）。或兩處都「弟子 ×2＋石靈」／都「弟子 ×3」？另：不行動的陣眼石靈算不算一隻？（我照字面算一隻。）
- **Q2 路邊 1 隻**：目前路邊全改 2 隻（1～2 的上限）。要不要有任何路邊改 1 隻（例：單隻野獸）？改 1 隻要動 schema `MIN_GROUP_SIZE`（2→1），屬規則類，我沒做。
- **Q3 線頭到期變化**：`temple_traitor`（主線叛徒戰）與 `brood_spread`（焦油坑擴散）我歸「地點戰」並減到 3；`scarface_risen`（疤面＝懸賞精英）歸「精英」不改。對嗎？
- **Q4 會讓隻數超過的機制（只列出、不改程式）**：① 世界旗標 `wraiths_surge` 夜晚雲嶺營地遭遇 +1 名霧魅（路邊 2→3、地點戰 3→4）；② 情境判定失敗的「增援」（`reinforce_lineup`，最多加到 4 名）；③ 精英巢穴的固定精英是「加 1 名」不是替換。這三項算不算「照原設計」的例外，或要另排規則段？
- **Q5 沒有地點引用的陣容**：`sect_patrol`（4）、`summit_patrol`（4）沒有任何地點或地圖使用，照原樣保留（不影響遊戲）。要不要也改成 3 或刪掉？
- **Q6 新手第 2 步**：竹林 `mist_wolf_pack` 3 隻維持（2～3 之內）；18.7.1「難度一步一步往上加」——第 1 步 2 隻、第 2 步 3 隻、第 3 步 2＋第三方 1。第 3 步是否要加到 3 隻由 PM／使用者定，我不動。
