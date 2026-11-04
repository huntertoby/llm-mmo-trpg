# Phase 6N-1 報告：動畫延伸①　串接器、起手對照表、按住加速＋原語片段（上）

實作者，2026-11-04。

規格依據：
- `docs/phases/Phase6計畫.md` 6N-1 列；
- 開發 PM 中途補充：照 `docs/art/動畫移植需求第二批.md`（main `700c3340`）對齊範圍，這段做美術編號的 **6N-1**（串接器、起手對照表、按住空白鍵 2 倍速）和 **6N-2**（原語片段的上半）；下半是 6N-3，沒做；
- `docs/art/動畫方案.md` 2.3（原語表、(1-1) 起手對照表、(2) 串接規則、(3) 特效）、第 3 節的選項；
- 樣張 `docs/art/sample/anim.js` 的 `CLIP`。

開工前 `git merge main` 兩次（開工時一次、收到補充後一次），都沒有衝突。只改了 `client/`，另外加了截圖和這份報告。沒碰 terrainArt、objectArt、world、伺服器；沒有新增相依；沒有新增伺服器欄位（OpenAPI 不用重產）。

## 交付

| 項目 | 檔案 |
|---|---|
| 片段資料與求值（純函式） | `client/src/render/skillClips.ts`（新）：<br>• `OPENER_CLIPS`：起手片段（關鍵姿勢＋`hitAt`＋起點＋位移＋特效提示）<br>• `OPENER_TABLE`：13 種武器 × 4 種施放方式；`openerFor`（表上沒有 → 空手列）<br>• `weaponClassOf`：紙娃娃主手、副手 → 武器種類<br>• `PRIMITIVE_CLIPS`、`PRIMITIVE_PLAYS`、`primitivePlay`：上半原語的片段與播法（出招前、出招、出招後、位移途中）<br>• `clipFrame`、`recoverFrame`：時間 → 量化姿勢；`anchorPoint`：姿勢 → 特效起點 |
| 串接器（純函式） | `client/src/battle/skillSequence.ts`（新）：`castMode`、`eventPrimitive`、`primitivesOf`、`skillTimeline`、`scaleRows`、`placeMotions`、`castFromBefore` |
| 片段的特效 | `client/src/render/skillFx.ts`（新）：發光、符陣、腳下法陣、槍口火光、罩子、往上收的光環、光點（上、下、收進身體）、碎片、連線、倒數記號、光柱、風線、黑煙、震波 |
| 接上播放 | `battle/playback.ts`：`playbackPlan(..., weaponOf)`；`Frame.skill`、`Frame.after`；`vfx` 操作帶 `skill`<br>`battle/animation.ts`：`MoveAnim.clip`<br>`render/BattleRenderer.ts`：`playSkill`、`weaponClassOf`、`setBoost`、`clipMove`、`poseClip`；`playVfx(..., origins)`<br>`render/unitSprite.ts`：`gripOf`<br>`screens/battle/usePlayback.ts`：先播身體片段再播特效；按住空白鍵 2 倍速 |
| 測試（新） | `render/skillClips.test.ts`（26 項）、`battle/skillSequence.test.ts`（21 項） |
| dev 頁 | `client/skill-gallery.html`、`src/dev/skillGallery.ts`（新）：`#openers`（`?mode=`、`?dir=west`）、`#prims`、`#order`（`?only=`）、`#moves`、`#perf`；`?anim=0.1` 慢動作、`?freeze=毫秒` 停格、`?cell=` 格子大小 |
| 截圖 | `docs/art/6n1_openers_east.jpg`、`docs/art/6n1_openers_west.jpg`、`docs/art/6n1_primitives.jpg`、`docs/art/6n1_order.jpg`<br>附加：`docs/art/6n1_moves.jpg` |

## 做法

### 1. 串接器（`skillSequence.ts`）

**輸入**：
- 一步的事件；
- 技能卡上部件的順序：`icon.segments[n].effects`，舊資料用 `effect_ids`；
- 這一步原本的特效時間軸 `vfxFor`；
- 施放者的武器種類（由繪製器 `weaponClassOf` 提供）。

**輸出**：
- 時間軸，每列是 {單位、片段、開始、長度、`hitMs`、特效起點 `anchor`、第幾段、是不是出招、目標格、元素}；
- 對齊後的特效；
- 每段的描述（施放方式、起手、原語）。

段落的切法和 `vfx.ts` 相同，所以段落和 `casts` 一一對應；對不起來時回傳 `null`，照舊只播特效。

**規則**（需求 2.1）：

| 規則 | 做法 |
|---|---|
| 1. 照卡上部件的順序 | 片段順序：起手 → 出招前的原語（`damage_multiplier` 加力）→ 出招 → 出招後的原語（照卡上的順序，相鄰的同一個片段合併）→ 收勢 160 ms<br>位移類原語照卡上的位置分到出招前或出招後：排在第一個 `damage` 之後的放到出招後。所以「砍＋跳」先砍再跳，「跳＋砍」先跳再砍<br>出招後才位移時，特效從位移前的格子發出 |
| 2. 方向、距離讀事件 | 位移片段只給姿勢，起點和終點照 `unit_moved` 的落點；施放者出招前轉向目標格 |
| 3. 同時發生的結果並排 | 同一段的所有命中都在那一段的命中點；施放者同時只有一個片段（後一段開始時，截掉前一段的收尾） |
| 4. 連鎖、反應前停頓 | 複合技能的後段、換人施放的段落，前面加 0.15 秒（`CHAIN_GAP_MS`） |
| 5. 起手只播一次 | 每個施放者在這一步只有第一段播蓄力；後段直接出招 |
| 6. 沒有身體動作的原語不佔時間 | 片段資料有 `still` 欄位；上半原語都有身體動作，所以這段沒用到（6N-3 的規則類用） |

**命中點對齊**：
- 近身（揮砍弧、範圍、光環等）：出招的 `hitAt` 那一刻＝特效命中；
- 遠程（飛行物、光束、扇形）：出招的 `hitAt` 那一刻＝特效的蓄力結束、飛行物離手，再飛到目標；
- 做法是把原本的特效時間整段往後移，命中、符文爆發一起移，所以受擊閃白、震動、傷害數字都跟著對齊。

**蓄力、延遲**：卡片的 `timing` 是 `delayed`、`activation`，或有 `activation_id` 時，起手的蓄力加長 1.5 倍。

**1.8 秒上限**：
- 第一段（不含連鎖與反擊）從起手到命中，超過 1.8 秒時，蓄力和加力等比壓縮，最多壓到 3 成；
- 命中點之後不壓；
- 測試用「蓄力技能＋加力＋射程 9」驗過。

**速度**：
- 時間軸是正常速度，`scaleRows` 和 `scaleVfx` 乘上 `playback.ts` 的速度；`?anim=` 照舊生效；
- 「略過」時沒有時間軸；
- **按住空白鍵**時，畫布 ticker 2 倍速（`setBoost`，片段、特效、走路一起快），播放中的等待照剩下的時間重算；放開、視窗失焦時恢復；輸入框裡按空白不算。

**事件 → 原語對照**（卡片沒有部件資料時，用它推出原語的順序；卡片有部件時以卡為準）：

| 事件 | 原語 |
|---|---|
| `damage_dealt` | `damage` |
| `healed` | `heal` |
| `shield_gained` | `shield` |
| `unit_revived` | `revive` |
| `resource_restored` | `restore_resource` |
| `unit_dashed`；`unit_moved` 的 `dash` | `dash` |
| `unit_charged` | `charge_through` |
| `status_removed` 的 `cleansed`／`dispelled`／`stolen` | `cleanse`／`dispel`／`steal_buff` |
| `status_applied` 的 `time_bomb`／`prone`／其他 | `delayed_damage`／`knock_prone`／`apply_status` |
| `unit_moved` 的 `leap`／`teleport`／`shadowstep`／`swap`／`teleported` | `leap`／`teleport`／`shadowstep`／`swap`／`teleport_target` |
| 其他事件 | 對不到 → 照現在的特效播，不加身體動作 |

`apply_status` 的增益、減益：這一段施放者施加的第一個狀態，目標和施放者同陣營是增益，否則是減益。

### 2. 起手對照表（`OPENER_TABLE`）

**施放方式**照形狀和射程判斷，不新增欄位：

| 施放方式 | 形狀 |
|---|---|
| 自身 | `self`、`allies_in_radius`、`ring` |
| 地面 | `ground_tile`、`square3` |
| 其他 | 射程 1 → 近身；2 以上 → 遠程 |

射程讀 `icon.segments[n].range`，第一段再退回 `stats.range`，都沒有時用施放者到目標的距離。一般攻擊照距離判斷。

**武器種類**（`weaponClassOf`，讀紙娃娃已解析的主手、副手）：

| 武器種類 | 判斷 |
|---|---|
| 魔導劍 | `sword` 加上 `arcane` 形制 |
| 劍、刀 | 其他 `sword`，以及大劍、匕首、斧、錘（見待決 2） |
| 成對 | 主手、副手同種的刃類 |
| 其他列 | 槍、鐮、鞭、拳套、法杖、弓、弩各自一列；長槍、手槍、霰彈槍歸火槍 |
| 法球 | 只有主手不是表上的武器、副手是法球時（見待決 3） |
| 空手 | 拂塵、符紙、傀儡線、沒有主手 |

沒有骨架的單位（異形、形態、召喚物）當空手。

**對照表**（片段名稱；照方案 2.3 (1-1)，13 列 × 4 欄全有）：

| 武器 | 近身 | 遠程 | 自身 | 地面 |
|---|---|---|---|---|
| 劍、刀 | windup→slash | point→palm_release | raise→aura_pulse | tip_down_in→tip_down |
| 魔導劍 | arcane_windup→slash | **sigil→sigil_cast（選項 A）** | raise_glow→aura_pulse | stab_ground_in→stab_ground |
| 成對 | x_windup→twin_slash | cross_point→palm_release | cross_chest→aura_pulse | cross_point→pair_down |
| 槍 | thrust_in→thrust | tip_point→tip_shot | plant→aura_pulse | butt_stamp |
| 鐮 | windup→sweep | sweep_in→scythe_flick | raise→aura_pulse | sweep_in→scythe_drag |
| 鞭 | whip_in→whip_lash | whip_in→whip_lash | whip_circle→aura_pulse | whip_in→whip_ground |
| 拳套 | fist_in→punch | fist_in→fist_shot | fist_clash→aura_pulse | fist_in→ground_punch |
| 法杖 | staff_raise→staff_tap | channel→cast | raise→aura_pulse | staff_stamp |
| 法球 | orb_in→orb_push | orb_channel→orb_cast | orb_raise→aura_pulse | orb_raise→orb_press |
| 弓 | bash_in→bash | aim→release | raise→aura_pulse | lob_aim→lob |
| 弩 | bash_in→bash | aim_gun→fire | raise→aura_pulse | aim_down→fire_down |
| 火槍 | bash_in→bash | aim_gun→fire（槍口火光） | raise→aura_pulse | aim_down→fire_down |
| 空手 | fist_in→punch | mudra→bare_release | palms_together→aura_pulse | palm_ground |

- 起手不看物理或法術；元素只換特效顏色。
- 每個片段 3～4 個關鍵姿勢，段間緩入緩出（細緻度 B 標準），長度 180～520 毫秒，姿勢照樣張 `anim.js` 的 `CLIP`。
- 正面、背面只吃 `armL`／`armR`：`frontize` 把主手、另一隻手往前上抬的量換成手臂往上移。

**特效起點**：
- 由當下姿勢算出武器作用端的位置（`anchorPoint`）：髖為軸前傾 → 肩 → 手肘 → 手 → 作用端。作用端的長度用 `inkWeaponFrame.weaponFrame(...).len`。
- 法球、法掌用另一隻手；空手用手掌。
- 飛行物、光束、扇形從出招那一刻的起點發出，蓄力光也在那裡；揮砍弧、範圍、光環照舊（揮砍弧的方向屬於 6N-6）。

### 3. 原語片段（上半，`PRIMITIVE_PLAYS`）

| 原語 | 播法 | 施放者片段 | 特效 |
|---|---|---|---|
| `damage` | 出招 | 起手決定的出招（不另外佔時間） | 照形狀（3-12） |
| `damage_multiplier` | 出招前 | `empower`：握緊、身體一沉 | 作用端發光 |
| `delayed_damage` | 出招後 | `mark_recover`：收勢 | 目標頭上倒數記號 |
| `heal` | 出招後 | `palm_heal`：另一隻手手掌朝前 | 掌心光、目標往上飄光點 |
| `shield` | 出招後 | `arm_guard`：雙臂往前一擋 | 目標身上罩子 |
| `cleanse` | 出招後 | `sweep_down`：手往下拂 | 目標身上光點往下掉 |
| `revive` | 出招後 | `kneel_lift`：單膝跪下、雙手上托 | 目標光柱 |
| `restore_resource` | 出招後 | `fist_chest`：握拳收到胸前 | 光點收進身體 |
| `apply_status`（增益） | 出招後 | `raise_hand`：舉手 | 目標腳下光環往上收 |
| `apply_status`（減益） | 出招後 | `point_at`：手指目標 | 目標身上一道光 |
| `dispel` | 出招後 | `palm_push`：手掌往外推 | 目標碎片 |
| `steal_buff` | 出招後 | `grab_back`：手往回抓 | 目標 → 自己的連線 |
| `dash` | 位移途中 | `dash_lean`：前傾 | 風線 |
| `charge_through` | 位移途中 | `shoulder_charge`：肩膀前頂 | 風線 |
| `leap` | 位移途中 | `leap_air`：縮腿、離地 18（只抬小人） | — |
| `teleport` | 位移途中 | `warp_pose` | 起點、終點扭曲圈（現有） |
| `shadowstep` | 位移途中 | `smoke_step`：蹲低前傾 | 黑煙 |
| `swap`、`swap_any` | 位移途中 | `swap_pose`（**共用**，表上標明） | 兩格之間的連線 |
| `teleport_target` | 出招後 | `point_tap`：手指一點 | 目標的扭曲圈（現有） |
| `push` | 出招後 | `palm_shove`：推掌 | 目標播「被推」 |
| `pull` | 出招後 | `yank`：手往回拉 | 目標播「被拉」 |
| `knock_prone` | 出招後 | `sweep_low`：掃腿 | 目標播「被撞倒」 |
| `shockwave` | 出招後 | `stomp`：跺地 | 腳下震波 |

**目標片段**（6N-4 會用到）：
- `pushed`：後仰、拖腳；
- `pulled`：前傾、拖腳；
- `knocked_down`：照 6M-3 的 `proneBody` 倒下，結束時標記倒地，接上重畫後的躺著；異形改播 `fall`。

被推、被拉、被傳送的人一律在出招後才移動（原本在特效之前）。

**異形、形態、召喚物**：
- 異形的出招播 6M-2 的「撲」，其他片段不播；
- 形態、召喚物不換姿勢，照舊只有特效。

**沒有片段的原語**：
- 回傳 `null`，播法是「起手＋現有特效」，不會壞；
- 測試讀 `content/skill_primitives.yaml` 全部原語，沒有片段的必須和下表完全相同。之後新增原語而沒有片段時，測試會失敗，提醒加進清單。

### 4. 留給 6N-3 的原語（34 個）

| 類別 | 原語 |
|---|---|
| 召喚 | `summon`、`sacrifice_summon` |
| 地表、地形 | `create_surface`、`zone`、`blow_surface`、`clear_surface`、`create_obstacle`、`raise_terrain`、`lower_terrain` |
| 物件、符文 | `topple`、`hurl_object`、`place_trap`、`inscribe`、`detonate_runes`、`destroy_object` |
| 形態 | `enter_form`、`leave_form` |
| 防護與其他 | `intercept`、`redirect_damage`、`cheat_death`、`reveal`、`copy_skill` |
| 給予、退還、層數 | `grant_skill`、`grant_ap`、`extra_reaction`、`refund_ap`、`refund_cooldown`、`reset_cooldown`、`add_stack`、`consume_stack`、`consume_status` |
| 規則類 | `gamble`、`rule_change`、`self_damage_of_hit` |

`destroy_object` 不在方案 2.3 的原語表上，先歸「物件」類（見待決 6）。

### 5. 效能

量測方式：
- `skill-gallery.html#perf`：12×12 戰場，8 人（劍、杖、弓、火槍、槍、魔導劍、鞭、拳套）輪流放技能，持續 6 秒；
- 和靜止 3 秒比較；
- 無頭 Chrome，dpr 1。

| 格子 | 靜止 FPS／p95 | 8 人放技能 FPS／p95 | 超過 50 ms 的幀 | 貼圖數：開始 → 6 秒後 |
|---|---|---|---|---|
| 52 px | 60.0／16.8 ms | 60.0／16.8 ms | 0 | 153 → 470 |
| 88 px | 60.0／16.8 ms | 60.0／16.8 ms | 0 | 153 → 470 |

- 姿勢先把時間量化成每片段 16 格，再用 6M-3 的 `quantizePose`／`poseKey` 進貼圖快取。所以同一個片段、同一套外觀、同一個朝向，最多 17 張貼圖。
- 實機 GPU 沒有量。

## 測試結果

- `vitest run`，相關的 18 個檔案、258 項全部通過。範圍：
  - 新增的 `skillClips`、`skillSequence`；
  - `playback`、`vfx`（3 個檔）、`animation`、`walkAnim`、`walkGait`、`bodyAnim`、`dollHit`、`motionClips`、`inkWeaponFrame`、`unitSprite`、`inkDollSnapshot`、`src/dev`。
- 新增 47 項：
  - 對照表：13×4 都有、出招有 `hitAt`、蓄力沒有；退回空手列；武器種類對應；
  - 片段時間軸：量化、確定性、收勢回到站好；
  - 作用端：13 種武器遠程出招時，朝東在身前、朝西左右對稱；
  - 原語：全部原語有片段或列在 6N-3 名單；只有 `swap`／`swap_any` 共用；
  - 串接：
    - 一般近身的命中點對齊；杖的飛行物在放出時離手；
    - 13 種武器 × 4 種施放方式都能串；
    - 加力在出招前、治療在出招後；增益、減益；
    - 3 人同時受擊；後段不重播蓄力、前面停頓 0.15 秒，施放者片段不重疊；
    - 蓄力遠程不超過 1.8 秒；沒有片段的原語退回；
    - 撞倒的目標在命中點倒下；
    - 確定性；段落對不起來時回傳 `null`；
  - 位移順序：跳＋砍、砍＋跳、被推、被拉、肩撞；
  - 接上 `playbackPlan`：砍＋跳的特效從跳之前的格子發出；速度縮放、跳過、沒給 `weaponOf` 時和原本相同。
- `inkDollSnapshot` 快照沒有變（沒設姿勢的畫法沒動）。
- `tsc --noEmit` 通過。`vite build` 成功，只有原本就有的 chunk 大小提示。
- 畫廊頁的主控台沒有錯誤。vite 用 5320 埠，用完已停掉（只停自己啟動的程序）。

## 檢查清單（需求第二批第 2.3、3 節）

**6N-1**
- [x] 樣張第 5 區的三組（砍＋跳、跳＋砍、衝刺＋砍）重現，順序和落點對：`#order` 頁走正式的 `playbackPlan → frameOps`，截圖 `6n1_order.jpg`。**沒在真的伺服器戰鬥裡實測**，見待決 8。
- [x] 起手 13 種武器 × 4 種施放方式都有，作用端位置對：測試，加上 `6n1_openers_east.jpg`、`6n1_openers_west.jpg`。
- [x] 火球從杖頭、劍尖、槍口、弓弦射出，不從格子中心：同上兩張截圖。
- [x] 一次打 3 人時 3 人同時受擊；連鎖前有停頓：測試。
- [x] 按住空白鍵 2 倍速；跳過直接出結果；一招最長 1.8 秒：空白鍵只在程式裡接上，沒有自動測試（見待決 7）；其餘兩項有測試。
- [x] 同一場戰鬥重播，畫面一樣：時間軸是純函式，有確定性測試；沒有用亂數，也沒有變體（變體屬於 6N-6～6N-8）。

**6N-2**
- [x] 每個原語在測試頁都有片段，和方案表上的描述一致：`#prims`（17 種）、`#moves`（位移 6 種＋被推、被拉），截圖 `6n1_primitives.jpg`、`6n1_moves.jpg`。
- [x] 共用的只有表上那幾組：這段只有 `swap`／`swap_any`，有測試鎖住。
- [ ] 拿一個 LLM 生成的技能（多原語）實戰播一次，順序照卡：**沒做**，這段沒開伺服器。串接只讀卡上的 `icon.segments[].effects`，手做、工坊、LLM 生成的技能都走同一條路；多原語的順序有單元測試。
- [x] 沒有片段的原語不會壞：測試（`summon`、`zone`，以及不存在的原語都退回「起手＋現有特效」）。

## 待 PM 決定（都已照最保守的做法做完）

1. **敵方回合**：6A-4d 只讓敵方的走路 2 倍速，停頓與其他動畫不縮短，所以技能片段照正常速度播，沒有另外快轉。如果要敵方的技能也快轉，`playbackPlan` 裡加一個倍率就好。
2. **斧、錘、大劍、匕首**：對照表沒有這幾列。照規則應該退回空手，但拿著斧頭出拳看起來不對，所以先歸「劍、刀」那一列（揮砍）。要改的話，只改 `skillClips.ts` 的 `KIND_CLASS`。
3. **法球列**：正式資料裡主手一定有武器（沒有時畫劍），所以只有主手不是表上的武器（例如符紙）、副手是法球時，才走法球列。劍＋法球走劍、杖＋法球走杖。
4. **空手列**：同上理由，戰鬥中實際會走到空手列的只有拂塵、符紙、傀儡線，以及沒有骨架的單位。
5. **揮砍的 3 種變體**：方案的表寫「蓄力→揮砍（3 種變體）」，但變體屬於 6N-6，這段每種只有一個樣子，也還沒用 `seedOf` 和戰鬥鍵挑變體。
6. **`destroy_object`**：不在方案 2.3 的原語表上，先放進 6N-3 的名單（物件類）。
7. **按住空白鍵**：
   - 做法是畫布 ticker 2 倍速，所以待機呼吸也一起變快；
   - 播放中的等待照剩下的時間重算；
   - 空白鍵沒有和其他戰鬥快捷鍵衝突（戰鬥目前只用 Esc）；
   - 沒有自動測試（屬於 hook 與鍵盤事件），在畫廊用 `setBoost` 確認過畫布會加速。
8. **實戰驗收**：截圖都是 dev 畫廊的假事件。播放走的是正式的 `playbackPlan`／`frameOps`／`BattleRenderer`，但沒開伺服器打一場真的戰鬥。
9. **位移順序的範圍**：
   - 只看第一段施放者自己的位移和卡上第一個 `damage` 的相對位置；
   - 走路照舊在前面；
   - 被推、被拉、被傳送的人一律在出招後才移動（原本在特效之前）。
10. **貼圖快取沒有上限**：沿用 6M-3 的作法，6 秒從 153 張長到 470 張。一場長戰鬥裡武器、技能種類多時會再長，要不要加上限（LRU）請 PM 決定。
11. **時間數值**：片段長度、收勢 160 ms、蓄力加長 1.5 倍、壓縮下限 3 成、跳躍離地 18，都是原型值。

沒有新增 eslint 例外，也沒有新增相依套件。

## Commit

- `cd2c76c1` feat(client): skill opener table, primitive clips and skill sequencer (6N-1)
- `8b279ea5` feat(client): play skill clips in battle, fx from weapon tip, hold space to speed up (6N-1)
- `4925ef5a` test(client): opener table, clip timeline, sequencer order and fallback (6N-1)
- `b825159f` feat(client): skill clip gallery (openers, primitives, order, perf) and 6N-1 screenshots
- `c09ab455` feat(client): gallery page for displacement clips (6N-2)
- 報告：最後一個 commit
