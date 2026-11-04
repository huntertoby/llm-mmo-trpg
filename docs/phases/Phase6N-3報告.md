# Phase 6N-3 報告：動畫第二批③　原語片段（下）

實作者，2026-11-04。

規格依據：
- `docs/phases/Phase6計畫.md` 6N-3 列；
- `docs/art/動畫移植需求第二批.md` 第 0 節（原則）、第 3 節（6N-3 的原語清單、共用組、檢查清單）；
- `docs/art/動畫方案.md` 2.3 (1) 的原語表；
- `docs/phases/Phase6N-1報告.md` 第 4 節（留給 6N-3 的 34 個原語）；
- 開發 PM 中途補充（依美術 PM 的 6N-1 驗收 `docs/art/6B-ART1與6C-ART2與6N-1檢查.md` 第 3 節）：
  - 附一場真實戰鬥的截圖，裡面要有多原語技能；
  - 貼圖快取加 LRU，上限 600 張，加測試，再量一次 FPS 和貼圖數；
  - 敵方回合照正常速度播、斧錘大劍匕首歸「劍、刀」：維持現狀。

開工前 `git merge main`，沒有衝突，含 6N-1 的檔案。只改了 `client/`，另外加了截圖和這份報告。沒碰 6N-9、6N-10、6D-ART2 的檔（statusAnim、surfaceAnim、townArt 一類）；沒有新增相依；沒有新增伺服器欄位。

## 交付

| 項目 | 檔案 |
|---|---|
| 下半原語的片段與播法 | `client/src/render/skillClips.ts`：`PRIMITIVE_CLIPS` 加 29 個片段，`PRIMITIVE_PLAYS` 加 34 個原語；`PrimitivePlay.icon`；`FxKind` 加 22 種、`FxWhere` 加 `head`、`linkOut` |
| 下半原語的特效 | `client/src/render/skillFxLower.ts`（新）；`skillFx.ts` 的 `cueEffect` 不認得的種類交給它，多一個 `icon` 參數 |
| 串接器 | `client/src/battle/skillSequence.ts`：事件 → 原語的下半對照；沒有身體動作的片段（`still`）；共用片段帶圖示；符文引爆留在段落裡 |
| 播放 | `client/src/render/BattleRenderer.ts`：`still` 的列不套姿勢，只播特效；`head`、`linkOut` 兩個位置；圖示傳給特效 |
| 貼圖快取 LRU | `client/src/render/textureLru.ts`（新）、`artTextures.ts` 改用它 |
| 測試 | `skillClips.test.ts`（改＋5 項）、`skillSequence.test.ts`（＋8 項）、`textureLru.test.ts`（新，5 項） |
| dev 頁 | `client/src/dev/skillGallery.ts`：`#lower`（`?group=world`／`?group=rules`）；`#perf` 加 `?secs=`、`?lower=1`、貼圖數峰值；`?freeze=` 停格後不再放下一輪 |
| 截圖 | `docs/art/6n3_world.jpg`、`docs/art/6n3_rules.jpg`、`docs/art/6n3_still.jpg`；實戰：`docs/art/6n3_battle.jpg`（三格連拍）、`docs/art/6n3_battle_full.jpg`（全畫面） |

## 1. 下半原語的片段

都是「出招後」播（`role: post`），照卡上部件的順序接在出招後面。時間 280～460 毫秒，每個 2～5 個關鍵姿勢。

| 原語 | 施放者片段 | 特效 | 共用 |
|---|---|---|---|
| `summon` | `summon_press`：雙手往下按、屈膝 | 目標格法陣＋往上飄的光點 | — |
| `sacrifice_summon` | `sacrifice_grip`：手朝召喚物一握 | 光球從目標飛回施放者 | — |
| `create_surface` | `scatter`：揮手灑出去 | 地表從中心擴散 | — |
| `zone` | `zone_stamp`：武器頓地 | 範圍線慢慢亮起 | — |
| `blow_surface` | `blow_sleeve`：揮袖 | 風線往一邊吹 | — |
| `clear_surface` | `press_clear`：單手往下壓 | 地表從邊緣收縮 | — |
| `create_obstacle` | `raise_both`：舉起雙手 | 障礙物從地面升起 | — |
| `raise_terrain` | `stomp_raise`：跺地 | 沿用現有的升降補間（`terrain_changed`），片段不另帶特效 | **特效共用** |
| `lower_terrain` | `press_lower`：雙手往下壓、蹲低 | 同上 | **特效共用** |
| `topple` | `shoulder_ram`：肩膀往前撞 | 目標格揚塵 | — |
| `hurl_object` | `lift_throw`：舉起、丟出 | 物件走拋物線到目標 | — |
| `place_trap` | `crouch_place`：蹲下放置 | 陷阱齒出現 | — |
| `inscribe` | `air_write`：在空中畫符 | 手上符陣，符文落到地上 | — |
| `detonate_runes` | `fist_clench`：握拳 | 目標格爆開 | — |
| `destroy_object` | `smash_down`：武器往下砸 | 目標碎片 | — |
| `enter_form` | `form_gather`：雙手上舉再收到胸前 | 一圈光收進身體 | — |
| `leave_form` | `form_release`：從胸前往外散開 | 光從身體散開 | — |
| `intercept`、`redirect_damage` | `side_guard`：側身擋到隊友前面 | 隊友 → 自己的雙線保護線 | **共用** |
| `cheat_death` | `rally_up`：半跪撐住、站起 | 金光一閃 | — |
| `reveal` | `shade_look`：手搭額頭 | 一圈光往外掃 | — |
| `copy_skill` | `snatch`：手朝目標一抓 | 技能圖示從目標飛過來 | — |
| `grant_skill`、`grant_ap`、`extra_reaction` | `shoulder_tap`：往隊友一拍 | 圖示從自己飛到隊友（方卡／菱形／半圓盾） | **共用**（靠圖示分辨） |
| `refund_ap`、`refund_cooldown`、`reset_cooldown` | `rewind_still`：**沒有身體動作** | 頭上圖示倒轉一圈（菱形／沙漏／雙線） | **共用** |
| `add_stack`、`consume_stack`、`consume_status` | `stack_still`：**沒有身體動作** | 頭上「＋」或「－」往上飄 | **共用** |
| `gamble` | `coin_flip`：拋硬幣 | 頭上硬幣翻轉 | — |
| `rule_change` | `finger_snap`：打響指 | 頭上一個小星 | — |
| `self_damage_of_hit` | `clutch_wound`：按住傷口、身體一彎 | 胸口紅光（傷害數字照舊由 `damage_dealt` 顯示） | — |

**共用的只有表上那幾組**（測試鎖住）：
- `swap`／`swap_any`（6N-2）；
- `intercept`／`redirect_damage`；
- `grant_skill`／`grant_ap`／`extra_reaction`；
- `refund_ap`／`refund_cooldown`／`reset_cooldown`；
- `add_stack`／`consume_stack`／`consume_status`；
- 升降地形：動作是兩個片段，特效共用現有的升降補間。

共用片段靠 `PrimitivePlay.icon` 分辨：給予類 `skill`／`ap`／`reaction`，退還類 `ap`／`cooldown`／`reset`，層數類 `+1`／`-1`。相鄰兩個共用片段圖示不同時不合併（例如「給技能＋給 AP」播兩次拍肩）。

**沒有身體動作的片段**（6N-1 規則 6：不佔時間，和前一個片段同時播）：
- 只有退還、層數兩組（`still: true`）；
- 開始時間 ＝ 前一個有動作的片段的開始時間（緊接在出招後面時就是出招那一刻）；
- 不推後面的片段、不改收勢，繪製器不套姿勢、不鎖待機，只播頭上的圖示；
- 測試：「砍＋退 AP＋加層＋治療＋減層」的總長和「砍＋治療」一樣。

**異形、形態、召喚物**：沿用 6N-1 的做法，沒有骨架的單位不換姿勢，特效照播。`enter_form` 之後施放者變成形態時，`form_gather` 只剩特效。

### 事件 → 原語（卡片沒有部件資料時才用）

| 事件 | 原語 |
|---|---|
| `unit_summoned` | `summon` |
| `summon_expired`（`sacrificed`） | `sacrifice_summon` |
| `surface_changed`（`cause: effect` 且有表面）／（`cause: clear`） | `create_surface`／`clear_surface` |
| `surface_blown` | `blow_surface` |
| `zone_created` | `zone` |
| `object_created` | `create_obstacle` |
| `terrain_changed`（變高／變低） | `raise_terrain`／`lower_terrain` |
| `object_toppled`、`wall_toppled` | `topple` |
| `object_hurled` | `hurl_object` |
| `trap_placed` | `place_trap` |
| `rune_inscribed` | `inscribe` |
| `rune_removed`（`detonated`） | `detonate_runes` |
| `object_destroyed`（`cause: effect`） | `destroy_object` |
| `form_entered`／`form_left` | `enter_form`／`leave_form` |
| `attack_intercepted`／`damage_redirected` | `intercept`／`redirect_damage` |
| `death_cheated` | `cheat_death` |
| `trap_revealed`；`status_removed`（`revealed`） | `reveal` |
| `skill_copied`／`skill_granted`／`ap_granted`／`reactions_granted`／`ap_refunded` | `copy_skill`／`grant_skill`／`grant_ap`／`extra_reaction`／`refund_ap` |
| `stacks_changed`（`gained`／`consumed`） | `add_stack`／`consume_stack` |
| `status_removed`（`consumed`） | `consume_status` |
| `gamble_rolled`／`rule_change_triggered` | `gamble`／`rule_change` |
| `damage_dealt`（`cause: backlash` 且打自己） | `self_damage_of_hit` |

- `skill_cooldown_changed` **不對**：使用技能時本來就會設冷卻，分不出退還還是重置（見待決 3）。
- 符文引爆（`rune_removed`／`detonated`）照 6N-1 不開新段，但現在留在這一段的事件裡，推得出 `detonate_runes`。

## 2. 斧、錘、大劍、匕首（6N-1 待決 2）

需求文件的起手對照表沒有這幾列；美術 PM 的 6N-1 驗收寫「同意」，開發 PM 也說維持。所以照舊歸「劍、刀」列（`KIND_CLASS`），沒改。6N-6 的變體表另有「斧、錘、雙手武器」3 種，到時再分。

## 3. 貼圖快取 LRU（上限 600）

- `textureLru.ts`：Map 插入順序當作「最久沒用」的順序；取用時移到最後；超過上限時從最前面淘汰並 `destroy(true)`。
- **不會銷毀畫面上正在用的貼圖**：
  - `ArtTextures` 在 `beginFrame`～`endFrame`（重畫場景）之間要的貼圖都「釘住」，到下一次重畫才解除；地形、物件、站著的小人都在這裡；
  - 剛放進去的那一張不淘汰；
  - 全部釘住時暫時超過上限，不硬砍。
- 只淘汰重畫之間動畫臨時要的姿勢貼圖（走路、技能片段、待機）。淘汰後再要同一個鍵會重畫一張新的。
- 原本 `endFrame` 清掉這一輪沒用到的貼圖，照舊。
- 測試（`textureLru.test.ts`）：預設上限 600；淘汰最久沒用的並銷毀；釘住的和剛放的不淘汰；淘汰後再要是新的、快取裡沒有已銷毀的；`clear` 全部銷毀。

## 4. 效能

量法同 6N-1：`skill-gallery.html#perf`，12×12 戰場、8 人輪流放技能，和靜止 3 秒比；無頭 Chrome（用 CDP 讀結果，沒有用虛擬時間）、dpr 1。

| 情境 | 靜止 FPS／p95 | 8 人放技能 FPS／p95 | 超過 50 ms 的幀 | 貼圖數：開始 → 結束（峰值） |
|---|---|---|---|---|
| 52 px，6 秒，只有砍 | 60.0／16.8 ms | 60.0／16.8 ms | 0 | 153 → 471（471） |
| 88 px，6 秒，只有砍 | 60.0／16.8 ms | 60.0／16.8 ms | 0 | 153 → 470（470） |
| 52 px，20 秒，砍＋輪流接 34 種下半原語（`?lower=1&secs=20`） | 60.0／16.8 ms | 60.0／16.8 ms | 0 | 153 → 600（**600**，上限生效） |

- 第三列的貼圖數停在 600，證明 LRU 有作用；畫廊主控台沒有錯誤，畫面沒有破圖。
- 同一頁在 Claude 的瀏覽器面板（面板隱藏，背景頁節流）只有約 28 FPS，那是節流，不採用。
- 實機 GPU 沒有量。

## 5. 截圖

| 檔案 | 內容 |
|---|---|
| `docs/art/6n3_world.jpg` | `#lower?group=world&freeze=760&cell=80`：召喚、地表、地形、物件、符文 15 種（劍＋射程 2 起手，接原語片段）。看得到召喚法陣、範圍線、肩撞前傾、蹲下放陷阱、畫符 |
| `docs/art/6n3_rules.jpg` | `#lower?group=rules&freeze=780&cell=66`：形態、防護、給予、退還、層數、規則類 16 種＋兩組多原語（「砍＋刻符＋引爆」「召喚＋層數＋退還」）。看得到形態散開、金光、往外掃的光圈、硬幣、響指 |
| `docs/art/6n3_still.jpg` | 同頁 `freeze=470`：沒有身體動作的退還、層數圖示在出招那一刻同時出現在頭上（倒轉圈、＋） |
| `docs/art/6n3_battle.jpg` | **實戰**：本機伺服器（`trpg serve --port 8327`，`TRPG_SAVE_DIR` 指到暫存區）開練習戰（開闊平原、單手劍、關鍵字「倒地」「高處」），第 2 輪對盜賊隊長放「絆擊」（`damage`＋`knock_prone`，兩個原語），極慢速連拍三格：站好 → 蓄力 → 揮砍命中（目標白閃） |
| `docs/art/6n3_battle_full.jpg` | 同一刻的全畫面 |

實戰紀錄：「冒險者 從背後以「絆擊」攻擊 盜賊隊長 → 命中」「冒險者 對 盜賊隊長 使出擊倒 → 失敗」。擊倒失敗所以目標沒有倒下，但卡上有 `knock_prone`，施放者照卡在揮砍後播 `sweep_low`（掃腿）；這一格沒拍到（見待決 5）。同場第 1 輪也放了「隆地」（`raise_terrain`），跺地加上現有的升降補間。

伺服器、vite（5324）、無頭 Chrome 都只停自己啟動的程序；瀏覽器面板的分頁大小已還原。

## 6. 測試結果

- `tsc --noEmit` 通過；`vite build` 成功（只有原本就有的 chunk 大小提示）。
- `vitest run`，相關的 17 個檔案、258 項全部通過。範圍：`skillClips`、`skillSequence`、`textureLru`、`artTextures`、`playback`、`vfx`（3 個檔）、`animation`、`walkAnim`、`unitSprite`、`inkDollSnapshot`、`motionClips`、`art`、`src/dev`。
- 新增、改動的測試：
  - **全原語覆蓋**：`skill_primitives.yaml` 每個原語都有片段（原本的「沒有片段的必須等於 6N-3 名單」改成「必須是空的」）；34 個下半原語都是出招後、長度 200～520 ms、至少 2 個關鍵姿勢；
  - **共用只有表上那幾組**（5 組）；共用片段的圖示互不相同；升降地形兩個片段、都不帶特效；
  - **只有退還、層數是 `still`**；
  - **片段時間軸**：34 個片段在 0、0.3、0.77、1 的姿勢確定、收勢回到站好；
  - **串接順序**：「砍＋召喚＋範圍＋刻符」照卡上順序、首尾相接不重疊；「刻符＋引爆」與「引爆＋刻符」順序相反；`still` 不佔時間、和前一個片段同時開始、收勢接在最後一個有動作的片段；相鄰共用片段圖示不同不合併；
  - **確定性**：34 個原語各建兩次時間軸結果相同，出招命中點不超過 1.8 秒；
  - **事件 → 原語**：上表全部、`skill_cooldown_changed` 不對、符文引爆留在段落裡；
  - **退回**：不存在的原語照舊退回「起手＋現有特效」；
  - **LRU**：見第 3 節。

## 7. 檢查清單（需求第二批第 3 節）

- [x] 每個原語在測試頁都有片段，和方案表上的描述一致：`#prims`（6N-2）、`#moves`（6N-2）、`#lower?group=world|rules`（6N-3），截圖 `6n3_world.jpg`、`6n3_rules.jpg`、`6n3_still.jpg`。
- [x] 共用的只有上列幾組：測試鎖住。
- [~] 拿一個 LLM 生成的技能（多原語）實戰播一次，順序照卡：實戰播的是內建的「絆擊」（兩個原語），見待決 5。LLM 生成的技能走同一條路（只讀 `icon.segments[].effects`）。
- [x] 沒有片段的原語不會壞：測試。

## 8. 待 PM 決定（都已照最保守的做法做完）

1. **`destroy_object`**：方案表上沒有，給了「武器往下砸＋碎片」（`smash_down`），沒有和其他原語共用。
2. **退還、層數的開始時間**：照「和前一個片段同時播」，前一個是出招時就在出招一開始出現；要改成對齊命中點的話，只改 `lay()` 裡 `lastStart`。
3. **`skill_cooldown_changed` 不推原語**：使用技能本來就會設冷卻，沒有部件資料的卡片無法分辨退還或重置，所以不推（卡上有 `refund_cooldown`／`reset_cooldown` 時照卡播）。
4. **`self_damage_of_hit` 從事件推**：只認 `damage_dealt` 的 `cause: backlash` 且打自己；`cost.on_miss` 的失手反噬也是同樣的事件，沒部件資料時會被當成這個原語（只多一個按住傷口的片段）。
5. **實戰截圖的範圍**：
   - 練習戰的起始技能裡，多原語而且有下半原語的組合不好湊（起始技能多半是單一效果），所以實戰用的是「絆擊」（`damage`＋`knock_prone`）；下半原語只有單原語的「隆地」在實戰播過；
   - 下半原語的多原語組合（「砍＋刻符＋引爆」「召喚＋層數＋退還」）是在畫廊頁看的；
   - 面板隱藏時截圖只能連拍，拍到站好、蓄力、命中三格，沒拍到命中後的掃腿；
   - 要更完整的實戰（例如工坊組一招多原語技能裝上去打）可以排在 6N-4 一起看。
6. **圖示是形狀不是字**：退還、給予、層數的圖示用簡單形狀（菱形＝AP、沙漏＝冷卻、雙線＝重置、方卡＝技能、半圓盾＝反應、＋／－），照去文字化原則，之後有正式圖示可換。
7. **LRU 的釘選範圍**：只釘「重畫場景那一輪」要的貼圖。重畫之間某個小人一直停在一個很久沒再要過的姿勢，同時別人又要了 600 張以上的新姿勢時，理論上那張會被淘汰；實測 20 秒、8 人、34 種原語沒有發生（峰值剛好 600，畫面正常）。要更保險可以讓繪製器把每個小人目前的貼圖也釘住。
8. **時間數值**：下半片段長度 280～460 ms、退還圖示 420 ms、層數圖示 360 ms，都是原型值。

沒有新增 eslint 例外，也沒有新增相依套件。

## Commit

- `f3654103` feat(client): primitive clips for the lower half (summon, surface, terrain, objects, runes, forms, rules) (6N-3)
- `8fb8d1c4` feat(client): LRU cap of 600 for the art texture cache; scene textures stay pinned (6N-3)
- `0b28ac86` feat(client): skill gallery page for the lower-half primitive clips (6N-3)
- `c628907c` feat(client): gallery freeze stops new rounds; perf page can run longer with lower-half primitives; 6N-3 screenshots
- `58d7cfe6` docs(art): 6N-3 real battle screenshots (trip strike: damage + knock_prone)
- 報告：最後一個 commit
