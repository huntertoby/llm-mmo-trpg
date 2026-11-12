# Phase VFX-1 完成報告｜「只給自己」的支援特效改畫在施放者身上

> 依據：美術 PM `docs/art/QI-4b與BAL-21b驗收.md` 2.2 (a)、2.3 可修 1；`docs/phases/PhaseBAL-21b報告.md` 第 9 節第 4 點。基準 `9b90f7f7`（`git merge --ff-only main`，含 `a057ca27`）。
> 只動前端 `client/src/battle/`；後端、`content/` 沒動。

## 1. 做了什麼（`29f4204a`）

**規則（`client/src/battle/vfx.ts`）**：某一段（技能第一段或複合技能的第二段）下面三條**全部成立**時，特效改成施放者身上的光環（`kind: "aura"`、`from`＝`to`＝施放者這一步結束時的位置、`tiles`＝[施放者]、`path`＝[施放者, 施放者]、`ranged: false`）；顏色、蓄力、傳說蓄力、開始與命中時間全部照改之前：

- (a) **沒有碰到施放者以外的任何東西**（`noteReach`）：這一段裡有 `damage_dealt` 或 `attack_rolled`（沒打中也算）→ 不成立；其他事件的欄位裡出現施放者以外的單位 ID、或施放者所在格以外的格子（`pos`、`tiles`、`cells`…，例：造表面、建區域、物件、位移）→ 不成立。唯一例外是 `followup_charged`（延遲段的預告，落點屬於下一段）。
- (b) **治療、護盾、狀態只落在施放者身上**：`healed`／`status_applied` 看 `target_id`、`shield_gained` 看 `unit_id`；至少一個是施放者、而且沒有任何一個是別人。沒有任何增益落地時不成立。
- (c) **施放者不在這一段的格子裡**（`skill_used`／`skill_followup` 的 `tiles`；格子是空的時不成立）。形狀本來就是自身、或範圍包含施放者的（`war_hymn`）都因此照舊。
- 一般攻擊一律不套用。

**身體不變（`client/src/battle/skillSequence.ts`）**：`VfxCast` 加選填欄位 `aim`（只有改畫的那一段才有＝改之前的 `to`），新函式 `aimOf(cast)`＝`aim ?? to`。`skillTimeline` 原本用 `cast.to` 的三處（片段列的 `target`、`describe`／`withCreature` 的目標、`eggTo`）改用 `aimOf`，所以頭目照舊朝選的格子、異形動作類型、片段自帶特效的轉向（`fxTurn`）都和改之前逐字相同（`vfx1SelfOnly.test.ts` 第 3 項：整個 `rows` 和「用改之前的特效描述」排出來的相同；把 `aimOf` 改回 `to` 時這項會紅，實測過）。沒有 `aim` 的段落行為完全不變。

**測試（新檔 `client/src/battle/vfx1SelfOnly.test.ts`，14 項）**

| 組 | 內容 |
|---|---|
| 三條都成立 | 熔岩濺落施放回合（引擎實際的事件順序：施放 → 冷卻 → 自己的護盾 → `followup_charged`）→ 頭目身上支援色光環、`aim`＝選的格子；時間、蓄力、配色和改之前相同；身體片段列和改之前逐字相同 |
| 任一不成立 → 照舊 | (a) 有傷害、有命中判定（沒打中）、有造表面；(b) 護盾給別人、自己護盾＋別人狀態、沒有增益；(c) 施放者站在 3×3 裡；形狀本來是自身；一般攻擊 |
| 區域型不受影響 | `fire_wall`（錐形、`zone_created` 帶 `cells`＋造火地）照舊 `cone`；`war_hymn`（範圍光環、只有自己在範圍裡）照舊 `aura`＋原本 13 格、沒有 `aim`。事件照引擎實際輸出抄 |

## 2. 受影響的招（全技能掃描）

**內容（`content/skills/` 403 招）裡只有 1 招：`skill_lava_splash`（熔岩濺落）的施放回合（第一段）**——選的 3×3 不含頭目時改成頭目身上的光環；3×3 含頭目時照舊。落下回合（第二段，有傷害與火地）不變。

掃描方法（腳本在暫存區，沒有 commit，見待決 5）：

1. **引擎實際施放**：每一招裝給施放者（法器、單手劍、弓、雷杖依序試到合法為止），在 11×11 平地上從合法動作中平均取最多 24 個目標各施放一次（`answered` 回答暫停），記下事件、步後單位位置與 `/api/skills/{id}` 的技能卡（`trpg.api.skill_cards.skill_card`）。兩種場地：
   - 近場（友方、5 個敵人、木箱、油桶都在附近）：336 招、2745 次施放；
   - 遠場（友方、敵人都在角落，用來抓「範圍裡沒人」的情況）：176 招、2021 次施放。
   - 放不出來的 67 招：非主動 49（修正 17、反應 16、被動 16）＋有條件的主動 18（處決、復活等，全是單體／自身，環形只有 `skill_form_release_burst`）；這些用第 2 點的靜態檢查補。
2. **靜態檢查**：403 招的每一段（主段＋`followup`），形狀不是自身、而且效果全部 `affects: self` 的只有 `skill_lava_splash` 主段。
3. **改前改後比對**：同一份事件分別給改前（`HEAD~1` 的 `vfx.ts`）與改後的 `vfxFor`，整份 `StepVfx` 序列化逐字比（改後拿掉 `aim` 再比）。

| 資料 | 施放次數 | 改了的 | 哪幾招 |
|---|---|---|---|
| 近場掃描 | 2745 | 18 | 全是 `skill_lava_splash`（24 個目標中 3×3 不含頭目的 18 個；含頭目的 6 個照舊） |
| 遠場掃描 | 2021 | 18 | 同上 |
| `client/src/battle/fixtures/oil_depot_seed3.json` 每一步 | 全部 | 0 | — |
| `client/src/battle/fixtures/vfx_random_skills.json`（Phase 3-12 錄的 20 個隨機組合技） | 20 | 1 | `skill_rand_10`（環形半徑 1、標記敵人；當時錄到範圍裡沒人、只有施放者自己被上緩速）→ 光環在施放者身上。這是舊錄的隨機技能，不是內容招；現行測試照樣通過（見待決 1） |

名單以外逐字不變的證明就是上表（改前改後 `vfxFor` 輸出逐字相同）。前端沒有特效描述的雜湊快照；整包 vitest 307 檔 3971 項全過，沒有重產任何快照或 fixture。

## 3. 結束碼

| 指令 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test`（307 檔、3971 項） | 0 |
| `corepack pnpm -C client build` | 0 |
| 相關 vitest：`vfx1SelfOnly`、`vfx`、`skillSequence`、`playback`、`specials`、`impactFeel`、`bal21bLavaSplash`、`realResponse`（8 檔 189 項） | 0 |

沒跑 `scripts/check.py`、沒跑模擬、沒 push。

## 4. 給美術的截圖（`docs/art/shots/vfx1/`，jpg 80，2 張）

開發頁 `client/dev/skill-gallery.html?mute=1&step=cast&cell=72&rows=1&freeze=780#bal21b`（和 BAL-21b 的 `1-cast-spout-mid.jpg` 同一刻），無頭 Chrome（`--headless=new --mute-audio --disable-gpu`）、CDP 用 Node 內建 WebSocket；「改前」是把 `vfx.ts`、`skillSequence.ts` 暫時換回 `HEAD~1` 拍的，拍完還原。

| 檔 | 內容 |
|---|---|
| `docs/art/shots/vfx1/1-cast-before.jpg` | 改前：玩家 A、B 所在的 3×3 每格綠色閃光（像在幫玩家補盾） |
| `docs/art/shots/vfx1/2-cast-after.jpg` | 改後：3×3 沒有特效，綠色光環在頭目腳下；頭目的 `spout` 熔岩柱、朝向、蓄力徽章和改前相同 |

**實機未看**：沒在正式戰鬥（熔心坑）打到熔岩濺落；開發頁走的是正式 `playbackPlan` → `frameOps`。

## 5. 待 PM 決定

1. **(b) 照「實際落地」判，不看技能設計**：範圍型的招如果這一次一個人都沒打到、只有施放者自己被上狀態（例：代價狀態），也會改成施放者身上的光環。現行內容沒有這種招（兩種場地掃描都沒抓到），但工坊／LLM 生成的技能可能有——`vfx_random_skills.json` 的 `skill_rand_10` 就是（環形沒打到人、自己被上緩速）。技能卡沒有結構化的「作用對象」欄位，前端分不出「本來就只給自己」和「本來要打人但沒打到」；若要只限前者需要後端在 `icon.segments[].effects` 加 `affects`。
2. **(a) 照最保守解讀**：除了命中，碰到別的單位或別的格子（造表面、建區域、物件、位移）的段都不改；只把 `followup_charged`（延遲段預告）當成不算。
3. **身體不跟著改**：美術建議 `to = from`，特效照做；但頭目朝向、異形動作、片段自帶特效的轉向仍照選的格子（`aim`），和改前逐字相同。若美術要頭目施放時不轉向選的格子，再說。
4. **時間照改前**：命中時間仍是範圍的 140 ms（光環本來是 120 ms），沒有讓後面的時間軸位移。光環半徑因為 `tiles` 只有施放者，是最小的 0.8 格。
5. **掃描腳本沒 commit**（`scan_skills.py` 引擎施放＋暫用 vitest 比對，放在暫存區）：之後改 `vfx.ts` 通用規則時若要重跑名單，要不要收進 `scripts/archive/`？
6. 美術追蹤 1（正式戰鬥補拍施放、預告、落下）沿用，本段沒做。
