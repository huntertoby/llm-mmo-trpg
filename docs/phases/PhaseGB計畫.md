# Phase GB 計畫｜部位系統段 2：不動巨型頭目（3×3）＋灰燼之心

> 開發 PM 的規格助手起草（2026-11-14，依據 main `c2469ea8e`；行號以它為準）。**範圍與定稿以第 0 節為準**；第 0.2 節的規則類待決要先經專案 PM 問使用者（附原話），答覆前對應的段不派工。
> 設計依據（以設計文件為準，本檔不放寬、不重新解釋）：`docs/design/05-戰鬥.md` 5.12（尤其 5.12.2、5.12.4 九條、5.12.6、5.12.8）、`docs/design/19-灰燼荒原與賽季主線.md` 19.2.3「不動巨型頭目與部位」、`docs/玩法決定紀錄.md` #152、`docs/phases/頭目部位與巨型頭目-工作量估算.md` 附錄 B1（本檔第 3 節查證並修正）。
> 段 1 的做法照搬：`docs/phases/PhasePB-1計畫.md`（部位模型、事件、版號、不變比對）、`PhasePB-1a／1b／1b2／1c／1d／1n報告.md`；BAL-21a 的 `FollowupSpec.anchor`（`docs/dev/上手-引擎戰鬥結算.md` 第一節 `delayed.py` 一列）。
> 實作者先讀：GB-1x、GB-2、GB-3 讀 `docs/dev/上手-引擎戰鬥結算.md`（全文）；GB-2 加讀 `docs/dev/上手-內容資料與模擬.md` 第二、七節；GB-4x 讀 `docs/dev/上手-前端戰鬥畫面與動畫.md` 第一～三節與 `docs/開發PM交接.md` 6.5.1、6.5.2。
> **不排任何平衡量測或模擬報表**（使用者 2026-11-13：「都不用再量數值了 寫個可能有問題記在.md上就好了 平衡 之後再說  先做遊戲」）。數值一律占位、由使用者在數值工坊調；疑慮寫在各段報告的「平衡疑慮」一節，本檔第 8 節先列已知的。

## 0. 決定與待決

### 0.1 已定、不要再問（都附出處）

| # | 規則 | 出處 |
|---|---|---|
| D1 | 段 2＝不動巨型頭目（3×3）＋灰燼之心。**不做**：定點飛行（龍，5.12.5）、碎晶之主部位（段 3）、大型精英部位、會移動的多格單位 | 05 5.12.8；#152 決定 1 |
| D2 | 用欄位標出這類單位（例 `footprint: [3, 3]`）加現有 `immovable` 標籤 | 05 5.12.4 開頭 |
| D3 | 佔滿 3×3；這些格子不能走，也不能放物件、表面或召喚物 | 05 5.12.4 第 1 點 |
| D4 | 和任何一格相鄰就算相鄰；距離量到最近的那一格；頭目自己出招也從離目標最近的那一格算 | 05 5.12.4 第 2 點 |
| D5 | 點頭目的某一格，格子對應到部位；沒標部位的格子＝本體 | 05 5.12.4 第 3 點 |
| D6 | 範圍技一次蓋到好幾格也只打一次；連鎖、彈跳只算一次本體 | 05 5.12.4 第 4 點；5.12.2 第 9 點 |
| D7 | 身體擋住它後面的視線（同石柱），但不擋打它自己的格子 | 05 5.12.4 第 5 點 |
| D8 | 推、拉、換位、傳送、擊退、倒地一律免疫；它自己的拉人招往最近的那一格拉；暈眩、沉默、定身照頭目現行規則 | 05 5.12.4 第 6 點 |
| D9 | 朝向固定，由地圖資料定哪一面是正面；部位或側面可以標「算從背後」 | 05 5.12.4 第 7 點 |
| D10 | 佔的格子高度一致；腳下的致命地形對它無效 | 05 5.12.4 第 8 點 |
| D11 | 只用在專屬頭目地圖；一般地圖與隨機遭遇不出現多格單位 | 05 5.12.4 第 9 點 |
| D12 | 巨型頭目的部位另要「那一格打得到」：近戰要和那一格相鄰，遠程要射程夠、看得到那一格；選哪個部位由目標格推出，欄位設計由開發定 | 05 5.12.2 第 8、10 點 |
| D13 | 巨型頭目 AI 只加一條：部位快破時多給「打站在那一面的人」一點分數；隊友與影子照破壞價值挑部位（同段 1） | 05 5.12.2 第 11 點 |
| D14 | 灰燼之心 3×3，靠熔心坑北側中段，背後（北）是岩漿；坑底維持 8×8；2 道矮牆往南移；4 個冷卻井改成兩側殼縫旁各 1、南邊 2；南邊入口兩側各加 1 格高台（高 1）；我方起始區不變；殼縫餘燼蜥從東、西兩側出來（座標由開發定） | 19 19.2.3「佔格」「熔心坑改圖」 |
| D15 | 部位綁格：北排 3 格＝熔岩噴口；中排東西 2 格＝殼縫（共用一條血）；中心＝核心；南排 3 格＝前殼（本體，沒有部位血條） | 19 19.2.3「部位綁格」圖與表 |
| D16 | 殼縫：站在兩側的近戰、遠程看得到也能打；破＝外殼高護甲提前消失（和水冰冷卻並存）；**打殼縫算「從背後」、吃背刺加成** | 19 19.2.3 表；#152 決定 4 |
| D17 | 熔岩噴口：只有遠程或長距離的招（北邊是岩漿站不了人）；破＝封住熔岩噴發（「噴口破了，這招就沒了」） | 19 19.2.3 表、「壓制站遠的人」1 |
| D18 | 核心：第 2 階段「呼吸」起才露出；近戰貼著任何一面都打得到、遠程看得到也能打；破＝打斷熔心爆的蓄力、吸氣 2 回合內失效 | 19 19.2.3 表 |
| D19 | 熔岩噴發改用「延遲招落在選定格」，預告一輪後落在離它最遠的敵人那一帶；高台也是它的第一目標 | 19 19.2.3「壓制站遠的人」1、5 |
| D20 | 第 2 階段吸氣改成 4 格內、往頭目拉 1 格，下一回合接吐息 | 同上 2 |
| D21 | 殼縫餘燼蜥優先追離頭目最遠的敵人 | 同上 3 |
| D22 | 第 3 階段的火地從頭目南緣往南長 | 同上 4 |
| D23 | 頭目不轉身；兩側殼縫算從背後（側邊靠近火地、餘燼蜥從兩側出來，要冒險才拿得到） | 19 19.2.3「背刺流的舞台」 |
| D24 | 19.2.3 這段和上面（5F-5a／5b 的階段描述）衝突時以這段為準 | 19 19.2.3「不動巨型頭目與部位」首句 |
| D25 | 部位共用系統、事件、版號、不變比對照段 1（PB-1a）；部位血量預設每個 200‰、加總 ≤ 600‰；數值由使用者在數值工坊調 | 05 5.12.2；#152「數值」；PB-1 計畫 D17 |
| D26 | 不再排平衡量測或模擬報表；仍要做確定性與不變比對 | 使用者 2026-11-13（`docs/開發PM交接.md` 3.0000 第 5 點） |
| D27 | 舊存檔、舊戰鬥紀錄不必相容（照實寫影響，不寫遷移） | `PhaseBAL-21計畫.md` 第 1 節（使用者 2026-11-12「存檔都可以刪除」） |

### 0.2 規則類待決（必須問使用者；附建議與理由）

| # | 問題（出處） | 建議 | 理由 |
|---|---|---|---|
| R1 | **範圍技打到巨型頭目時打本體還是部位**：5.12.2 第 9 點「範圍技、連鎖、彈跳只打本體；對巨型頭目也只打一次」，但 5.12.4 第 4 點又寫「打哪個部位照離範圍中心最近的那一格決定，同距離照座標排序」，兩條互相矛盾 | **只打本體、只打一次**。「離範圍中心最近的那一格」只拿來當「打中的那一格」：事件的 `pos`、演出落點、命中判定用的掩護與高度都以這一格算；距離用曼哈頓，同距離照 (y, x) 小的 | #152 決定 3 原話是「範圍技、持續傷害只打本體」；5.12.6 表「範圍、召喚、持續傷害流：打本體」；5.12.2 第 9 點自己就指向 5.12.4 第 4 點講「只打一次」。讓範圍技也能破部位會讓爆發流以外的 build 也能破核心，和 5.12.6 的分工不合 |
| R2 | **巨型頭目「以自己為中心」的招怎麼量**（5.12.4 第 2 點只寫「從離目標最近的那一格算」，沒寫環形、方陣、十字、錐形這種以自己為中心的形狀）：吐息（環形 2）、吸氣（改 4 格內）與它的後段方陣、熔心爆（十字臂長 2）、灰燼誓約（錐形 3） | **整個 3×3 當中心向外量**：一格算進範圍＝它到最近佔格的距離符合形狀（環形＝切比雪夫距離恰為 r；範圍光環＝曼哈頓 ≤ r；方陣＝切比雪夫 ≤ 1；十字＝佔格的 3 欄與 3 列各往外延伸臂長）；錐形與直線從朝向那一面的中間格起算。佔格本身永遠不在範圍內 | 照 5.12.4 第 2 點「從最近那一格算」最直接的延伸；只從中心格量的話，吐息環形 2 只會蓋到緊貼身邊那圈、方陣只蓋到自己。代價：範圍會比 1 格時大（例：十字臂長 2 從 9 格變 24 格、吐息環形 2 從 16 格變 24 格），列進平衡疑慮，數值交使用者調 |
| R3 | **噴口的「遠程或長距離的招」怎麼判**（19.2.3 表）：坑底 8 寬、頭目佔 x 4～6 時，(3, 2)、(7, 2) 是能站人的地板、而且和噴口角落相鄰；矛（`spear`，近戰、射程 2）算不算「長距離」 | 噴口標新條件 `ranged`：**這次攻擊不是近戰**（同背刺用的 `profile.melee` 判斷）才能選；所以站在 (3, 2) 的近戰、拿矛的也不能打噴口；遠程照 D12 要射程夠、看得到那一格 | 照表的字面「只有遠程或長距離的招」；用既有的近戰判斷不另造「長距離」的定義。不改地圖（坑底維持 8×8，D14） |
| R4 | **遠程打殼縫算不算背刺**（D16「打殼縫算從背後，吃背刺加成」；5.1 背刺只算近戰） | **只有近戰打殼縫算從背後**（背刺加成、條件「目標背後」、無聲不轉向等所有「背後」判斷都成立）；遠程打殼縫照一般部位，沒有背刺加成 | 5.1 背刺本來就只算近戰；19.2.3 寫「背刺流的舞台……要冒險才拿得到」，是給近戰的 |
| R5 | **熔岩噴發「落在離它最遠的敵人那一帶」的選格規則**（D19；現行 `skill_lava_splash` 是 4 格內由 AI 挑最多人的格） | 新錨點 `followup.anchor: farthest_enemy`：施放時由**引擎**選格（不靠 AI 評分）——離頭目最近佔格曼哈頓距離最遠的存活敵人，看不見的隱蔽敵人不算（照一般隱蔽規則），同距離照 (y, x) 小的；**不限射程、不需視線**；落點是那名敵人當下的格子，3×3 落下照舊；第一段的自我護盾照舊；找不到敵人就不能施放 | 「最遠的敵人」用規則定下來最確定，AI 只決定放不放；限射程或要視線的話站最遠的人反而打不到，和「壓制站遠的人」相反 |
| R6 | **第 3 階段「火地從頭目南緣往南長」是一次放好還是每回合長**（D22；19.2.3 原文第 3 階段「場上所有火地每回合擴散 1 格（只往空地）」，現行用進入階段時一次放 8 格近似） | **A 每回合長**：進第 3 階段時在南緣外那一排（3 格）放火地；之後每輪結束往南長 1 排（只長到可站、沒有單位、沒有物件的格子；遇岩漿、牆、矮牆、水就停），最多長到 N 排（占位 4，工坊可調）。B 案（較省）：進階段時一次放南緣往南 2 排共 6 格，不長 | 「長」與 19.2.3 原文「每回合擴散」都指會隨時間變大；A 要新做「階段的生長表面」機制（約 GB-1c 的一小項），B 只改內容。使用者選 B 也可以，GB-1c 刪掉那一項 |
| R7 | **吸氣「下一回合接吐息」要不要強制**（D20；現行吸氣有立即的後段「方陣 1d10」，吐息由 AI 自己挑） | **不強制**：只改範圍（4 格內，照 R2 量）與拉的方向（往最近佔格），後段 1d10 照舊；吐息照現在由 AI 挑（冷卻 1，下一回合本來就能放） | 19.2.3 原文第 2 階段就寫「吸氣、下一回合吐氣」，5F-5a 一直用 AI 挑來近似；改成強制連段要新機制並改變現有節奏，原話也沒說要拿掉後段傷害 |

### 0.3 技術類待決（開發 PM 可定；沒回覆就照建議）

| # | 技術點 | 建議 |
|---|---|---|
| T1 | 位置的表示 | `UnitState.pos` **維持一格＝佔格的中心格**（只允許奇數正方形，第一版只收 `[3, 3]`）；新欄位 `UnitState.footprint: int = 1`（邊長；`exclude_if` 等於 1 不輸出）；所有「這個單位佔哪些格」一律走新檔 `engine/rules/footprint.py::tiles_of(unit)`（依 (y, x) 排序）。中心格當 `pos` 的好處：頭目永不移動，大部分「讀 `pos`」的地方（自己的狀態、事件、敘事、視圖）不必改 |
| T2 | 共用查詢（新檔 `engine/rules/footprint.py`，只依賴 `state.py`、`geometry.py`） | `tiles_of(unit)`、`occupies(unit, xy)`、`nearest_tile(unit, xy)`（曼哈頓最近，同距離 (y, x) 小）、`dist_to(unit, xy)`、`unit_dist(a, b)`（兩邊都取最近格）、`adjacent(a, b)`（`unit_dist == 1`）、`is_giant(unit)`。1 格單位時每個函式都**退化成原本的 `manhattan(unit.xy, …)`、不多取亂數**，這是不變比對成立的前提 |
| T3 | 佔格與阻擋 | `BattleState.unit_at` 與 `occupancy()` 認佔格（`occupancy` 對 9 格都回同一個單位）；`rules/movement.py::path_map`、`rules/landing.py::landing_problem`／`nearest_free`、`targeting.summon_site_problem`、放物件（含陷阱、符文）與造表面（`effects/world.py`）的檢查都經過它。表面：效果要在佔格上造表面時**跳過那格、不發事件**；佔格上原有的表面在開場時清掉（內容檢查擋，見 T13） |
| T4 | 視線 | `geometry.has_line_of_sight` 多收選填 `ignore_unit`：巨型單位的佔格（除了 `ignore_unit` 自己）當成 `blocks_sight` 的牆；打巨型頭目（任何一格）時傳入它自己。1 格單位不受影響（現行一般單位不擋視線） |
| T5 | 範圍去重與「打中的那一格」 | `skills/targeting.py::_tiles_to_units` 改成依單位 ID 去重（現在是 `[unit_at(xy) for xy in tiles]` 沒去重，3×3 會被收好幾次）；`Cast` 另記 `hit_tile[unit_id]`＝範圍內離中心最近的佔格（R1）。連鎖（`shapes.chain_units`）把巨型頭目當一個節點，距離用 `dist_to`，從它跳出時以 `nearest_tile` 為起點 |
| T6 | 位移免疫 | **只對 `footprint > 1` 的單位**補齊：`_swap_units`（換位）、`MoveUnitEffect` 的 `teleport`、`knock_prone`、`ice_slide`、推拉（現行 `push_distance` 已擋 `immovable`）。理由：`immovable` 現在也用在源晶柱、碎晶之主、陣眼石等 7 個範本，改 `immovable` 本身會讓 `rift_gate`、`cloud_summit` 的戰鬥變。免疫時照現行發 `MoveBlocked(reason="immovable")`；倒地免疫發既有的「抵抗」事件（實作者查現行 `race_stonewall` 擋倒地的寫法照抄） |
| T7 | 頭目的拉人方向 | `primitives/displacement.py::_displace` 在施放者是巨型單位時，方向＝被拉者到 `nearest_tile(caster, 被拉者)` 的主軸；斜向同距離時取 x 軸（寫進報告）；已相鄰的不拉 |
| T8 | 朝向 | 地圖 `start_zones` 之外新增選填 `giant_facing: {<範本 ID>: <方向>}`（熔心坑 `ashen_heart: south`）；巨型單位整場不轉向（`face_toward`、被近戰轉身、`after_attack(turns=…)` 都跳過）。「背後」的幾何：攻擊者和背面那一排相鄰而且站在背面之外（灰燼之心背面是岩漿，實際不會成立）；部位旗標 `counts_as_behind: true`（R4，殼縫用） |
| T9 | 出招起點 | 巨型單位施放時，`caster.xy` 換成 `nearest_tile(caster, 目標格或目標單位)`：射程、視線、`center_problem`、方向判斷都以它算；以自己為中心的形狀照 R2（`shapes.py` 多一組「以佔格為中心」的函式，1 格時退化成原函式） |
| T10 | 致命地形與高度 | 巨型單位不觸發 `EnteredDeadlyTerrain`、表面進入效果；`state.tile(*unit.xy).height` 對巨型單位等於任一佔格（內容檢查保證一致） |
| T11 | 部位綁格（內容） | `BossPart` 新增選填 `tiles: tuple[tuple[int, int], ...] = ()`（相對中心格的偏移，`exclude_if` 空）；`reach` 加 `ranged`（R3）；`counts_as_behind: bool = False`（R4）；`melee_from: Literal["tile", "any_face"] = "tile"`（核心「近戰貼著任何一面」用 `any_face`）。檢查：巨型單位的部位必有 `tiles`、不重疊、在佔格內；1 格頭目的部位不能有 `tiles` |
| T12 | 動作欄位 | **沿用 `target_part`**（段 1 的欄位），不新增 `target_pos`：前端由「點的那一格」查 `PartView.tiles` 推出 `target_part` 再送出；引擎用 `part_targets` 驗（D12 的相鄰、射程、視線以部位的格子算）。點到前殼、已破部位的格、還沒露出的部位的格＝本體（不送 `target_part`）。理由：重播只需要記選了哪個部位，不必另一套欄位 |
| T13 | 內容檢查（`trpg content check`） | 只有帶 `boss` 標籤的範本能有 `footprint > 1`；佔格必須是奇數正方形 3；只能出現在 `archetype: boss` 的地圖的遭遇裡（掃 `encounters`、`world/`、`roguelite` 的遭遇表；隨機遭遇與一般地圖擋下）；開場位置的 9 格都在地圖內、可站、同高度、沒有物件與表面；`giant_facing` 的範本 ID 存在 |
| T14 | 新的破壞效果：限時封招 | `seal_skill` 加選填 `rounds: int | None = None`（`None`＝永久，同段 1）；有值時存進新欄位 `UnitState.sealed_until: dict[str, int]`（技能 → 解封的輪數，`exclude_if` 空），`skill_problem` 一併擋。「2 回合內失效」＝從破壞那一輪起算 2 輪，第 (破壞輪 + 2) 輪開始解封（報告寫明）。不用冷卻，因為換階段會覆寫冷卻 |
| T15 | 熔岩噴發的錨點 | `DelayedAnchor` 加 `farthest_enemy`（R5）；`ANCHOR_FIRST_SHAPES` 照舊；施放時 `delayed.anchor_of` 由引擎選格存進 `StatusInstance.anchor`，之後預告、釋放、打斷全部沿用 BAL-21a。`UseSkill` 對這種招不收 `target_pos`（送了就 `IllegalActionError`）；`legal_actions` 只列一個不帶格子的動作 |
| T16 | 火地生長（R6 選 A 時） | `BossPhase` 新增選填 `grow_surface: {surface, rows_from: south_edge, max_rows, every: round_end}`，在 `_end_round` 結算；只往「可站、沒有單位、沒有物件、沒有其他表面」的格子長；事件用既有的表面事件。R6 選 B 時這項不做 |
| T17 | 殼縫餘燼蜥追最遠的人 | 行為模式加 `prefer_far_from_leader`（AI 價值表 `content/ai_profiles.yaml` 新的權重，占位 3，工坊 NW-3 開放後可調）：目標離頭目最近佔格越遠分數越高；只給 `heart_ember_lizard`。軟偏好、不強制 |
| T18 | 巨型頭目護部位（D13） | `ai/parts.py` 加 `guard_face_bonus`：有部位剩血 ≤ `near_break_permille` 時，攻擊「和那個部位的格子相鄰」的敵人多加分（占位 3，同 `guard_back_bonus` 的寫法填進 `weights`） |
| T19 | `LOG_FORMAT` | GB-1a、GB-1b、GB-1c 各升一號（預期 `/125` → `/126`、`/127`、`/128`；合併時已有別段先升就順延），各在 `docs/phases/戰鬥紀錄格式變更.md` 寫一條。GB-2（只改內容）、GB-3（AI）不升 |
| T20 | 佔格中心與地圖座標 | 灰燼之心中心 (5, 3)、佔 x 4～6、y 2～4（北邊 y 1 是岩漿，D14）；8 寬的坑放不到正中，取和現在一樣的 x＝5。其餘座標見 GB-2（6.2），開發 PM 可改 |

## 1. 範圍

**做**：多格單位的資料、佔格、距離與相鄰、範圍去重、連鎖、視線、位移免疫、固定朝向、出招起點、致命地形；部位綁格與巨型頭目的可打條件；限時封招、`farthest_enemy` 錨點、（R6 A）火地生長；熔心坑改圖與灰燼之心內容；AI（隊友挑格、站位、頭目護面、餘燼蜥追遠）；API 與前端（點格選部位、3×3 繪製、範圍與預告、部位格標示占位）；數值工坊白名單的新欄位；美術需求（第 7 節）。

**不做**：定點飛行（龍）、落點預告與推開；碎晶之主部位（段 3）；大型精英；會移動的多格單位（路徑、推開、多格位移事件）；偶數邊長或非正方形；任何數值調整、平衡量測、模擬報表；改 `immovable` 標籤本身的語意（T6）；剪影外框（OCL）規則（只做 3×3 的必要相容）。

## 2. 現況查證（只讀，`c2469ea8e`）

- **位置**：`engine/state.py:379` `UnitState.pos: Pos`（`shared/types.py:49`），`xy` 是 property（`:566`）。`BattleState.unit_at`（`:855`，線性掃描、假設一格一人）、`occupancy()`（`:869`，`{u.xy: u}`）。沒有任何佔格欄位或函式。
- **距離**：`rules/geometry.py::manhattan` 收兩個 XY；169 處呼叫（52 檔），其中 136 處傳的是單位的 `.xy`；另有約 12 處單位距離是行內 `abs()` 算（`api/skill_reasons.py:29`、`oath_tracking.py:221`、`traps.py:108／127`、`summons/core.py:460`、`skills/mobility.py:105`、`rules/combat.py:380`、`weapon_traits.py:328`、`basics.py:289`、`battle.py:581`、`sim/skill_ratio.py:491` 等）。
- **範圍收人**：`skills/targeting.py::_tiles_to_units`（`:662`）沒有去重；`anchored_area`（`:1042`）也用它。
- **視線**：`geometry.has_line_of_sight`（雙向 Bresenham、端點不算）；`_sight_walls`（`:90`）已支援「帶 `blocks_sight` 標籤的單位擋視線」，但只擋它那一格。
- **位移**：`immovable` 只在 `effects/handlers.py:834`（`forced`／`teleported` 的 `move_unit`）、`effects/world.py::push_distance`（`:623`，推與拉）、`battle.py::shove_problem`（`:702`）檢查；**換位 `_swap_units`（`:983`）、`teleport` 模式、`knock_prone`（`primitives/displacement.py:155`）、`ice_slide.py:153` 都沒擋**。`immovable` 範本 7 個：`ashen_heart`、`rift_pillar_*` 3 個、`rift_shard_lord`、`sect_array_stone`、`sect_summit_array_stone`。
- **錨點**：`content/skills/constants.py:650` `DelayedAnchor = Literal["cast_tile"]`；AI 挑 `target_pos` 是在射程內每格預覽、`_delayed_points` 取最多人，**沒有「以最遠敵人為中心」的寫法**（附錄 B1 的疑問：BAL-21a 表達不了，要 T15）。
- **形狀**：`shapes.ring_tiles` 是切比雪夫距離恰為 r；`radius_tiles` 曼哈頓 ≤ r；`square3_tiles`、`cross_tiles`、`cone_tiles` 都以單一格為中心。
- **頭目階段召喚**：`PhaseSpawn.at` 已存在（`content/battle.py:1546`，省略＝頭目位置再找最近安全格），所以「從東西兩側出來」只要填座標。
- **火地**：沒有「火地擴散到空地」的程式；`environment.py::_spread_fire`（`:171`）只燒可燃表面與物件。第 3 階段現在是 `tiles` 一次放 8 格。
- **灰燼之心**：`content/units/ashen_heart.yaml`：HP 160、`speed: 0`、標籤含 `immovable`、開場 `molten_shell`；階段 `shell`（`skill_lava_splash`、`skill_fire_bolt`、`skill_ashen_oath`）→ `breath`（≤ 600‰；`skill_heart_inhale`、`skill_heart_exhale`、`skill_fire_bolt`；移除熔殼；召喚 2 隻 `heart_ember_lizard`）→ `meltdown`（≤ 300‰；`skill_heart_meltdown`、吐息、火球；`cunning`；8 格火地）。吸氣：環形 2、拉 1、後段方陣 1d10；吐息：環形 2、1d6＋燃燒；熔心爆：延遲十字臂長 2、3d8；熔岩濺落：方陣射程 4、自我護盾、延遲 `anchor: cast_tile` 方陣 1d6＋火地 2 回合。
- **熔心坑**：`content/maps/molten_heart_pit.yaml` 12×12、全高 0；坑底石地 x 2～9、y 2～9；外圈岩漿、南側通路 (3, 10)、(8, 10)；矮牆 (4, 8)、(7, 8)；水表面 (3, 3)、(8, 3)、(3, 8)、(8, 8)；我方起始 y 11；敵方起始 (5, 5)、(3, 5)、(7, 5)、(5, 3)。另有同 ID 的世界實地（前廳 12×8，`content/world/fields/ashen_waste/molten_heart_pit.yaml`），本段不動。
- **CLI 快照**：`tests/cli/snapshots/cli_output_hashes.json` 24 鍵＝7 個戰鬥鍵（都不是頭目圖）＋`skills_list`＋`skills_show_all/00～15`（429 招、每片 27 招）。灰燼之心的 5 招（吐息、吸氣、熔心爆、熔岩濺落；灰燼誓約在 01）中前四招都落在 **`skills_show_all/05`**。
- **前端**：`UnitView.pos` 一格（`api/schema.d.ts:12179`），`PartView` 沒有格子欄位；`battle/drawModel.ts:286` 把 `pos` 攤成 `UnitDraw {x, y}`；z 順序靠 `rows.row(u.y)`（`render/battle/unitLayer.ts:85`）；OCL「大型前排」是貼圖面積門檻（`render/battle/outlineLayer.ts:130` `canBeBig`），不是旗標；頭目的放大 `render/unitSprite.ts::ringScale`／`bossHudGeom`（`"ah"` 灰燼之心、`"sl"` 碎晶之主）。部位 UI：`battle/partMenu.ts`、`ui/PartMenu.tsx`（錨在被點的那一格 `tileBox`）、`ui/PartBar.tsx`、`render/qIcon/bossParts.ts`（只有拂塵、氣海）。
- **美術（已確認，不是假設）**：`docs/art/` 與 `docs/美術PM交接.md` **沒有**灰燼之心 3×3 立繪、灰燼之心部位小圖、部位格標示、改圖後熔心坑的樣張或需求；`docs/art/頭目部位*.md` 與 `bossParts.ts` 只有霧鎖真人；`docs/art/頭目造型.md` 是 1 格版灰燼之心造型。PB-1e（頭頂部位小格、霧鎖真人）11-14 已派、正在跑，會動 `render/`。

## 3. 影響面（查證後修正附錄 B1）

### 3.1 Python（`src/trpg/`）

| 項目 | 附錄 B1 粗估 | 查證 | 說明 |
|---|---|---|---|
| 讀單位位置的地方 | 約 218 處 | **約 750～800 處**（以單位為接收者的 `.pos`／`.xy`／`unit_at(` 共 855 處，扣掉約 64 處其實是事件的 `e.pos`） | 全部 `.pos`／`.xy`／`unit_at(` 1066 處（含物件、陷阱、符文） |
| 其中**真的要改**的 | — | **約 100～150 處**（估） | T1 讓 `pos`＝中心格、頭目不動，「單位自己的位置」那一大半不必改；要改的是「別人和巨型單位之間」的距離、相鄰、佔格、視線 |

依類別（數字是查到的呼叫點；「集中」＝改一個函式就涵蓋）：

| 類別 | 主要位置 | 呼叫點 | 性質 |
|---|---|---|---|
| 佔格與阻擋 | `state.unit_at`（51）、`occupancy`（4）、`movement.path_map`、`landing.landing_problem`（20）／`nearest_free`（6）、`effects/handlers._move_unit`、`effects/world.unit_push_block`、`battle._place_units`／`_zone_of`、`boss_phases`（召喚）、`targeting.summon_site_problem`；`.xy ==`／`in` 比較 43 | 約 120 | 大多集中 |
| 距離、相鄰、射程 | `manhattan` 169（AI 65、引擎頂層 36、skills 22、rules 11）；相鄰 `== 1`／`<= 1` 18；`reactions.py:448`（近戰相鄰）、`:663`（敵人走進相鄰）、`:957`（藉機攻擊）；`combat.reach_problem`、`attack_problem`、`sees_hidden`、`advantage_sources`；`basics.adjacent_allies` | 約 190 | 分散；`manhattan` 收 XY，要逐處換成 T2 的單位版 |
| 範圍收人、連鎖 | `targeting._tiles_to_units`、`Cast.targets`／`tiles`／`tile_holds`、`shapes.chain_units`、`ai/utility/scoring._delayed_points` | 約 30 | 集中（`_tiles_to_units` 一處） |
| 視線 | `has_line_of_sight` 16 處、`combat.cover_object_between`、`guard_between` | 約 20 | 集中 |
| 位移 | `_swap_units`、`teleport`、`knock_prone`、`ice_slide`（缺口）；`push_distance`、`shove_problem`（已擋） | 約 8 | 集中 |
| 朝向、背刺 | `facing.back_xy`、`is_behind`（7）、`face_toward`（7）、`combat.positional_bonus`、`conditions`、`parts._part_reason` | 約 20 | 集中 |
| 出招起點 | `targeting.shape_reach`、`_reach_problem`、`compute_area`、`_tile_candidates`、`shapes.center_candidates`、`delayed.py`（`:126／144／259`）；`caster.xy` 約 108 | 約 110 | 每個函式取一次，分散 |
| 腳下地形與高度 | `state.tile(*X.xy)` 46 處（`.height` 30）、`is_deadly` 30、`is_standable` 25、`surface_entry` | 約 100 | 分散；巨型單位不動，只需在「對它判斷」的幾處處理 |
| AI 站位 | `ai/utility/position.py` 32（`_steps_to`、`_approach_distance`、`_boss_distance`、`_facing_terms`、`_flanked_count`、`_covered_from`）、`moves.py`、`skill_estimate.py`、`scoring.py`、`ai/summon.py` 18、`ai/race.py` 12、`ai/displace.py` | 約 180 | 分散；靠近巨型頭目要改成「走到任一佔格旁」 |
| 視圖、API、敘事 | `engine/view.py:940`、`api` 14、`narrative` 30（多為事件位置） | 約 45 | 每個序列化器一處 |

### 3.2 前端（`client/src/`）

| 項目 | 附錄 B1 粗估 | 查證 |
|---|---|---|
| 讀位置的正式檔 | 約 66 檔 | 提到位置的正式檔 **67 檔、341 行**（另測試 26 檔、開發頁 4 檔）；其中 `world/*` 7 檔是大地圖、物件與預告也算在內，**真正讀單位格子的約 35～40 檔** |

主要集中點：點擊找單位至少 5 份各自寫的「`samePos(u.pos, tile)`」（`screens/battle/useTileInteraction.ts::unitAt`、`battle/tileClick.ts`、`battle/actions.ts:172`、`battle/targeting.ts:527／655-669`、`battle/composite.ts:79`、`screens/battle/useHighlights.ts:102`）；「單位 ID → 位置」至少 4 份（`battle/vfx.ts:689`、`battle/skillSequence.ts:280／680`、`battle/feedback.ts:267`、`battle/scenePreview.ts:60`）與一份反查（`render/battle/vfxLayer.ts::creatureAt／dollAt`）；繪製 `render/battle/unitLayer.ts`（`rows.row(u.y)`、`place`）、`render/rowLayers.ts`、`render/unitSprite.ts`（`hpBar`、`unitTopY`、`bossHudGeom`、`ringScale`、`bossRingFront`）、OCL `render/battle/outlineLayer.ts`（`rowOf`、`FRONT_ROWS`、`canBeBig`）、`occlusionLayer.ts`；卡片錨點 `battle/stageLayout.ts::tileBox／cardPlacement`、`ui/PartMenu.tsx:175`。路徑與合法目標由伺服器算（`pathPreview.ts` 只畫），前端不用改尋路。

### 3.3 段數

| | 附錄 B1 | 本計畫 |
|---|---|---|
| 規則規格 | 中（1） | 本檔（已做） |
| 引擎 | 大 2～3 段 | **3 段**（GB-1a 佔格與基礎、GB-1b 距離與出招、GB-1c 部位綁格與新機制）；GB-1b 若超過約 40 萬 token 可拆 1b／1b2（AI 站位分出去） |
| 內容 | 中 | 1 段（GB-2，含 NW 白名單小項） |
| AI | 中 | 1 段（GB-3） |
| 前端 | 大約 2 段 | **3 段**（GB-4a 邏輯、GB-4b 繪製占位、GB-4c 美術移植） |
| 模擬 | 小 | **0**（使用者 11-13 不量） |
| 合計 | 7～10 段（含模擬） | **8 段（可能 9）**；和原估同量級，但 Python 讀位置的地方是原估的約 3.5 倍（750～800 對 218），靠 T1「`pos`＝中心格」把實際要改的壓到約 100～150 處 |

## 4. 分段與平行

| 段 | 內容 | 前置 | 會動的主要檔 | 平行 |
|---|---|---|---|---|
| **GB-1a** 佔格與基礎 | 5.1 | R2 以外的規則類不擋；T1～T4、T6、T8、T10、T13、T19 | `engine/state.py`、新 `engine/rules/footprint.py`、`rules/geometry.py`、`rules/movement.py`、`rules/landing.py`、`rules/facing.py`、`effects/handlers.py`、`effects/world.py`、`skills/primitives/displacement.py`、`ice_slide.py`、`battle.py`（開場放置）、`boss_phases.py`（召喚落點）、`content/battle.py`、`content/maps.py`、`runner.py` | 不和任何改 `state.py`、`effects/`、升 `LOG_FORMAT` 的段平行 |
| **GB-1b** 距離、範圍、出招起點 | 5.2 | 1a 合併；R1、R2；T5、T7、T9 | `skills/targeting.py`、`skills/shapes.py`、`skills/cast.py`、`skills/mobility.py`、`rules/combat.py`、`reactions.py`、`basics.py`、`delayed.py`、`preview.py`、`ai/`（距離部分）、其他 `manhattan` 呼叫點 | 不和改 `skills/`、`ai/`、`rules/combat.py` 的段平行 |
| **GB-1c** 部位綁格與新機制 | 5.3 | 1b 合併；R3～R6；T11、T12、T14～T16 | `engine/parts.py`、`part_breaks.py`、`delayed.py`、`boss_phases.py`、`environment.py`（R6 A）、`content/parts.py`、`content/skills/constants.py`、`content/skills/followup.py`、`content/battle.py`、`narrative/` | 同上 |
| **GB-2** 內容＋改圖＋工坊白名單 | 第 6 節 | 1c 合併；R5～R7；T17、T20 | `content/units/ashen_heart.yaml`、`heart_ember_lizard.yaml`（只限必要）、`content/maps/molten_heart_pit.yaml`、`content/skills/skill_lava_splash.yaml`、`skill_heart_inhale.yaml`、`content/tuning_fields.yaml`、`src/trpg/content/tuning_fields.py`、`src/trpg/api/tuning/objects.py`、被固定答案打到的測試 | 可和 GB-4a 平行（檔案不重疊）；不可和 NW 白名單段同時 |
| **GB-3** AI | 第 7 節 | GB-2 合併；T17、T18 | `engine/ai/`（`parts.py`、`utility/position.py`、`utility/policy.py`）、`content/ai_profiles.yaml`、`src/trpg/content/environment.py` | 可和 GB-4a、GB-4b 平行 |
| **GB-4a** API＋前端邏輯 | 8.1 | GB-2 合併（瀏覽器實測要正式內容）；T12 | `src/trpg/api/`（視圖、合法動作、OpenAPI）、`client/src/battle/`（`tileClick.ts`、`targeting.ts`、`actions.ts`、`composite.ts`、`telegraph.ts`、`vfx.ts`、`skillSequence.ts`、`feedback.ts`、`scenePreview.ts`、`partMenu.ts`、`stageLayout.ts`）、`screens/battle/`、`ui/PartMenu.tsx`、新 `battle/footprint.ts` | 可和 GB-3 平行；**不動 `render/`** |
| **GB-4b** 繪製（占位） | 8.2 | GB-4a 合併、**PB-1e 合併**（同在 `render/`） | `render/battle/unitLayer.ts`、`rendererBase.ts`、`rowLayers.ts`、`outlineLayer.ts`、`occlusionLayer.ts`、`highlightLayer.ts`、`vfxLayer.ts`、`render/unitSprite.ts`、新 `render/battle/partTileMarks.ts`、`dev/oclGallery.ts` | 不和任何動 `render/` 的段平行 |
| **GB-4c** 美術移植 | 8.3 | GB-4b 合併＋**美術 PM 交第 9 節的移植需求** | 只動 GB-4b 標成占位的檔 | 同上 |

同時進行的 agent 最多 3 個（開發名額）。順序：**1a → 1b → 1c → 2 →（3 ∥ 4a）→ 4b →（美術到了）4c**。只有 GB-4c 要等美術；GB-4b 等的是 PB-1e 合併。

## 5. 引擎

### 5.1 GB-1a｜佔格與基礎（T1～T4、T6、T8、T10、T13、T19）

1. **資料**：`UnitTemplate.footprint: int = 1`（`exclude_if` 等於 1；只收 1 或 3）；`UnitState.footprint`（開場從範本複製）；地圖 `giant_facing`（T8）。三處同步（dataclass、`clone()`、序列化；上手第三節第 4 點）。
2. **`engine/rules/footprint.py`**（T2）全部函式＋單元測試：1 格時與 `manhattan(unit.xy, xy)` 逐值相同的 hypothesis 性質測試。
3. **佔格**（T3）：`unit_at`、`occupancy`、`path_map`、`landing_problem`、`nearest_free`、`summon_site_problem`、放物件／陷阱／符文、造表面都認佔格。開場放置：巨型單位放在遭遇的起始格（＝中心格），其餘單位排除它的 9 格。
4. **視線**（T4）：佔格當牆、`ignore_unit` 例外。
5. **位移免疫**（T6）：只對 `footprint > 1`；5 種缺口各一列測試。
6. **朝向**（T8）：固定朝向、不轉身；`counts_as_behind` 的讀點留到 GB-1c。
7. **地形**（T10）。
8. **內容檢查**（T13），錯誤訊息中文、指出範本／地圖／遭遇 ID。
9. **測試用合成巨人**：放在測試裡（`tests/engine/helpers.py` 加 `spawn_giant`），不進 `content/`；本段 `content/` 一個字都不改。
10. `LOG_FORMAT` 升一號（T19）。

### 5.2 GB-1b｜距離、範圍、出招起點（R1、R2、T5、T7、T9）

1. 把 3.1「距離、相鄰、射程」與「出招起點」兩類的呼叫點換成 T2 的單位版（`dist_to`／`unit_dist`／`adjacent`／`nearest_tile`），含行內 `abs()` 的那約 12 處。只換「另一邊可能是巨型單位」的地方；逐檔列進報告（換了幾處、刻意不換的理由）。
2. 範圍去重與「打中的那一格」（R1、T5）；連鎖、彈跳只算一次。
3. 以自己為中心的形狀（R2）：`shapes.py` 新增以佔格為中心的版本；1 格時呼叫原函式。
4. 出招起點（T9）、拉人方向（T7）。
5. 藉機攻擊、「敵人走進相鄰」、仇恨、光環「N 格內」、`ZoneState` 的範圍判定都用單位版距離；巨型單位在一個區域裡只算一次。
6. AI 的距離（`ai/utility/position.py` 的 `_steps_to`、`_approach_distance`、`_boss_distance` 等）：靠近巨型頭目＝走到任一佔格旁；**只換距離，不加新評分**（評分在 GB-3）。
7. 預覽（`preview.py`）照新距離；不能有副作用。
8. `LOG_FORMAT` 升一號。

### 5.3 GB-1c｜部位綁格與新機制（R3～R6、T11、T12、T14～T16）

1. **部位綁格**（T11）：`BossPart.tiles`、`reach: ranged`、`counts_as_behind`、`melee_from`；內容檢查。
2. **可打條件**（D12、T12）：`parts.part_targets` 對巨型頭目逐部位判斷——
   - 部位的格子：近戰要和其中一格相鄰（`melee_from: any_face` 時和任一佔格相鄰即可）；遠程要到其中一格的距離 ≤ 射程、而且看得到那一格（T4 `ignore_unit`＝頭目自己）。
   - 再疊段 1 的條件（`exposed_in`、`broken`、`disabled`）與新的 `ranged`（R3）。
   - 原因代碼新增 `not_adjacent_to_tile`、`no_sight_to_tile`、`out_of_range_to_tile`、`melee_cannot_reach`（中文在 `PART_REASON_ZH`：「要貼著那一格才打得到」「看不到那一格」「那一格超出射程」「只有遠程才打得到」）。
3. **從背後**（R4）：近戰打 `counts_as_behind` 的部位時，`positional_bonus`、條件「目標背後」、無聲不轉向（`quiet_strikes`）都當成在背後；遠程照舊。
4. **限時封招**（T14）；**`farthest_enemy` 錨點**（R5、T15）；**火地生長**（R6 A、T16）。
5. **敘事**：新原因、限時封招（「熔心吸氣被封住 2 回合」）、錨點落點（「熔岩噴向最遠的 X」）的中文；說書人只描述。
6. `LOG_FORMAT` 升一號。

### 5.4 不變比對（GB-1a、1b、1c 每段都做；比照 `PhasePB-1計畫.md` 4.10）

- **場次**：8 張地圖 × 種子 1、2（`molten_heart_pit`、`rift_gate`、`cloud_summit`、`open_plain`、`bandit_lair`、`oil_depot`、`lava_crossing`、`swamp`）＋ 3 張頭目圖（`molten_heart_pit`、`rift_gate`、`cloud_summit`）× 種子 3～12，共 46 場；地圖預設陣容、效用 AI、`max_rounds=30`。
- **比對**：完整事件 JSON、步驟、輪數、勝方、最終 `rng_state`、最終狀態 JSON（拿掉 `final_state.ruleset`；剝掉「值等於預設」的新鍵並列在報告）。改前用 `git archive` 解開舊引擎跑（上手第四節第 21 點），腳本放 scratchpad、不 commit。
- **預期**：GB-1a、1b、1c 時 `content/` 裡還沒有巨型單位，**46 場全部 `different=0`**（含熔心坑）。`hash_ruleset`、一輪存檔 `ruleset_hash`、世界日誌 `content_digest` 改前＝改後（附值）。對不上就停下回報，不放寬。
- **CLI 快照預測**：24 鍵**全部不變**（戰鬥鍵都是一般地圖；技能卡沒改）。

### 5.5 行為一致測試（實際跑引擎；新檔 `tests/engine/test_giant_gb1a.py`、`test_giant_gb1b.py`、`test_giant_parts_gb1c.py`，合成巨人）

每列一條規則句（D 編號或 R／T 編號寫在列名）：

1. 佔格：9 格都走不進、路徑繞開；不能在佔格放物件、陷阱、造表面（跳過、不發事件）、召喚、傳送落點、復活落點、`nearest_free` 不選佔格。
2. 相鄰與距離：站在 12 個外圍相鄰格任一格都算相鄰；斜角不算；射程量到最近格（射程 5 的火球從 (5, 9) 打中心 (5, 3) 的頭目＝距離 5，不是 6）；藉機攻擊、走進相鄰的觸發以佔格計。
3. 範圍（R1）：方陣蓋到 4 格只扣一次 HP、只一筆 `damage_dealt`；`hit_tile` 是離中心最近、同距離 (y, x) 小的那格；不帶 `part_id`；連鎖只打一次、跳出點正確。
4. 自身為中心（R2）：環形 2、範圍光環 4、方陣、十字臂長 2、錐形 3 的格子數與座標逐一列出（表格寫在測試裡）。
5. 出招起點（T9）：頭目打南邊的人從南排算、打東邊的人從東欄算；視線也從那格起。
6. 視線（D7）：佔格擋住後面；打它自己任一格不擋（含遠程打北排從南邊射）。
7. 位移（D8、T6）：推、拉、換位、傳送、擊退、倒地、滑冰 7 種各一列，全部不動、事件照 T6；**1 格的 `immovable` 單位（源晶柱）被換位、倒地照現行**（證明 T6 沒擴大）。拉人往最近格（T7）。
8. 朝向（D9、T8）：被近戰打不轉身；`face_toward` 不改。
9. 地形（D10）：開場在致命地形上（合成）不觸發。
10. 部位（GB-1c）：每個部位 × 近戰／遠程 × 位置的可不可選與原因代碼表；殼縫近戰有背刺加成、遠程沒有（R4）；噴口近戰（含矛、站 (3, 2)）不可選（R3）；核心未露出不可選、露出後近戰貼任一面可選；點已破部位的格＝本體。
11. 限時封招（T14）：第 N 輪破、第 N＋1 輪不能放、第 N＋2 輪可以；換階段不清。
12. `farthest_enemy`（R5）：選到最遠、同距離 (y, x) 小、隱蔽不算、超過原射程仍可、`target_pos` 送了就拒絕；預告格跟著那時的格子、敵人走開格子不動（BAL-21a）。
13. 火地生長（R6 A）：每輪結束長一排、遇單位、物件、岩漿、水、牆停；最多 N 排。
14. 確定性：同種子兩次相同；暫停點（`prompt` 反應）中途 `resume` 與一次跑完相同；`BattleLog` JSON 往返後 `replay` 一致；`clone()` 保留新欄位。

### 5.6 交付與驗收（每段）

1. 程式＋測試分 commit；報告 `docs/phases/PhaseGB-1a報告.md`（1b、1c 同）；更新 `docs/dev/上手-引擎戰鬥結算.md`（第一節加 `rules/footprint.py`、第二節加「巨型單位」一段、第四節加「距離一律走單位版」一條）、`docs/phases/戰鬥紀錄格式變更.md`。
2. `ruff check`、`ruff format --check`、`mypy`、`lint-imports` 結束碼 0。
3. 相關測試（不帶 `-m`；多檔 `-n 8`）：5.5 新檔、`test_determinism.py`、`test_skill_determinism.py`、`test_status_determinism.py`、`test_state_clone.py`、`test_pending_serialization.py`、`test_combat.py`、`test_effects.py`、`test_skill_shapes.py`、`test_skill_primitives.py`、`test_reactions.py`、`test_preview.py`、`test_boss_parts_pb1.py`、`test_parts_ai_pb1.py`、`test_delayed_anchor_bal21.py`、`test_lava_splash_bal21b.py`、`test_runner_advance.py`、`test_ruleset_hash.py`、`tests/content/` 的單位與地圖 schema 檔、`tests/test_architecture.py`、版號字面值所在的測試（`grep -rn 'trpg-battle-log/' tests`、`grep -rn 'endswith("/1' tests`）。
4. 一場紀錄＋重播：`molten_heart_pit` 2、`oil_depot` 13、`swamp` 21，「重播驗證通過」。
5. 5.4 的 `different=0` 與三個雜湊。
6. 交件前一次：`tests/cli/test_output_snapshots.py -m slow`（預期 0 鍵）、`tests/narrative/`。
7. 複雜度：新增 `# noqa` 逐一寫理由。

## 6. GB-2｜內容＋改圖＋工坊白名單

### 6.1 灰燼之心（`content/units/ashen_heart.yaml`；檔頭註解寫 #152、19 19.2.3、占位值）

- `footprint: 3`；部位（全部 `hp_permille: 200` 占位、加總 600‰；護甲、抗性都不寫）：

| id | name_zh | tiles（相對中心） | reach | 其他 | exposed_in | on_break |
|---|---|---|---|---|---|---|
| `shell_seam` | 殼縫 | (−1, 0)、(1, 0) | `any` | `counts_as_behind: true` | （全程） | `stop_mechanic: molten_shell` |
| `vent` | 熔岩噴口 | (−1, −1)、(0, −1)、(1, −1) | `ranged` | — | （全程） | `seal_skill: skill_lava_splash` |
| `core` | 核心 | (0, 0) | `any` | `melee_from: any_face` | `[breath, meltdown]` | `interrupt_charge`＋`seal_skill: skill_heart_inhale, rounds: 2` |

  南排 3 格不列＝前殼（本體）。
- 第 2 階段 `spawns`：`at` 填東、西兩側（T20：(3, 3)、(7, 3)；被佔就照現行找最近安全格）。
- 第 3 階段（R6）：A 時拿掉現有 8 格 `tiles`，改 `tiles` 南緣外一排 (4, 5)、(5, 5)、(6, 5)＋`grow_surface`（`max_rows` 占位 4）；B 時只改 `tiles` 為南緣往南 2 排 6 格。
- 不新增、不刪除技能 ID（否則 CLI 快照 16 片全部位移）。

### 6.2 熔心坑（`content/maps/molten_heart_pit.yaml`；座標開發 PM 可改）

- 坑底 8×8、外圈岩漿、我方起始區 y 11、南側通路不變（D14）。
- 敵方起始改成 `[(5, 3), (2, 4), (8, 4), (5, 6)]`：灰燼之心在第一格＝中心（T20）；開場兩隻餘燼蜥 (2, 4)、(8, 4)（原 (3, 5)、(7, 5)，跟著頭目往北、避開下面的井）；第 4 格備用。`giant_facing: {ashen_heart: south}`。
- 矮牆 (4, 8)、(7, 8) → (4, 9)、(7, 9)（「往南移」；不擋 (3, 9)、(8, 9) 的通路）。
- 冷卻井（水表面）(3, 3)、(8, 3)、(3, 8)、(8, 8) → 殼縫旁 (3, 4)、(7, 4)（殼縫攻擊位 (3, 3)、(7, 3) 的南邊一格，不佔攻擊位）＋南邊 (3, 8)、(8, 8)。
- 高台：入口兩側 (2, 9)、(9, 9) 高度 1（`heights` 改兩格）。
- 檔頭註解改成新配置並寫 #152、19.2.3。

### 6.3 技能

- `skill_lava_splash.yaml`：`followup.anchor: farthest_enemy`（R5）；第一段的 `shape` 改成實作者在 GB-1c 定的「不需選格」寫法；`name_zh` 照舊「熔岩濺落」（19.2.3 寫「熔岩噴發」是設計用語，改名會動 `skills_list`，不改；報告寫明）。
- `skill_heart_inhale.yaml`：`shape` 改範圍光環 4（R2 量法下＝離最近佔格 ≤ 4）、拉 1（R7）；後段照舊。
- 其他招不改。

### 6.4 數值工坊白名單（小項）

`content/tuning_fields.yaml` 加：`parts[*].on_break[*].rounds`（int，說明「破掉後封住幾輪」）、（R6 A）`phases[*].grow_surface.max_rows`（int）；`api/tuning/objects.py` 的中文標籤；`footprint`、`tiles` **不開放**（結構，不是數值）。測試照 PB-1n 的 T-A1／T-A2 各加一列。

### 6.5 驗收

1. `trpg content check` 過；`tests/content/`、`tests/world/test_ashen_waste.py`、`tests/engine/test_lava_splash_bal21b.py`、`tests/engine/test_enemy_skills_149.py`、`tests/world/test_enemy_ai_moves_149.py`、`tests/content/test_ashen_waste_content.py`、`tests/content/test_con_hp.py`、`tests/api/tuning/` 的部位與白名單檔。被打到的固定答案逐項說明（「拿掉本段改動就回到舊值」），斷言不放寬；固定種子不再成立的照上手第四節第 6 點掃種子換。
2. 不變比對（5.4 的 46 場）：**除 `molten_heart_pit` 的 12 場外 `different=0`**；熔心坑列出每場勝方、輪數改前改後（只列，不評）。`hash_ruleset` 會變（技能在規則包內）：把兩個技能檔換回舊版重算＝舊值，證明只來自這兩個檔；`ruleset_hash`、`content_digest` 同法。
3. **CLI 快照逐鍵預測**：只有 **`skills_show_all/05`** 變（`skill_heart_inhale`、`skill_lava_splash` 的技能卡）；`skills_list` 不變（列的骨架、AP、法力、冷卻都沒改）；7 個戰鬥鍵不變。其他鍵變了就停下查。用 `UPDATE_CLI_SNAPSHOTS=1 … -k skills_show_all/05` 只重產那一鍵。
4. 前端夾具：`unitDolls.json` 等只有在 `doll` 改了才會變（本段不改 `doll`）。
5. 一場紀錄＋重播：`molten_heart_pit` 種子 2、7。
6. 報告 `docs/phases/PhaseGB-2報告.md`，含「平衡疑慮」一節。

## 7. GB-3｜AI（T17、T18；不量勝率）

1. **隊友挑部位**：PB-1b 的 `_with_parts` 已用 `part_targets` 展開，GB-1c 之後自然包含綁格條件；本段確認並補測：能打斷熔心爆時打核心、噴口能一擊破而熔岩噴發快好時打噴口、近戰在殼縫攻擊位時打殼縫。
2. **站位**：`ai/parts.py` 加 `giant_part_spot_extra`（同 PB-1b2 `circle_back_extra` 的寫法）：近戰站在「能打到某個未破、已露出部位的格子旁」、遠程站在「看得到、打得到噴口」的格子時加分（占位，填進 `weights`）；高台不另加分（高度既有的位置價值已算）。
3. **頭目護面**（D13、T18）；**餘燼蜥追遠**（D21、T17）。
4. **測試**（新檔 `tests/engine/test_giant_ai_gb3.py`）：每條一個固定場面比分數（不比機率）；確定性；**沒有巨型單位的場面 `rank` 逐字不變**。
5. **不變比對**：46 場除熔心坑外 `different=0`；熔心坑列出變了幾場、平均事件差，寫「預期：隊友開始走去殼縫與高台、打部位」。
6. **CLI 快照預測**：0 鍵。
7. 報告 `docs/phases/PhaseGB-3報告.md`；上手筆記第二節「AI 怎麼選招」加一點。

## 8. 前端

### 8.1 GB-4a｜API＋前端邏輯（不動 `render/`）

1. **API**：`UnitView.footprint: int | None = None`、`UnitView.tiles: list[Pos] | None = None`（只有巨型單位輸出）；`PartView.tiles: list[Pos] | None = None`；`part_options` 的原因吃新代碼的中文。選填一律 `X | None = None`（上手-引擎第四節第 13 點）。`export_openapi.py` → `gen:api`。
2. **共用 helper** 新檔 `battle/footprint.ts`：`unitTiles(u)`、`unitAtTile(units, tile)`、`partAtTile(u, tile)`；把 3.2 列的 5 份點擊找單位、4 份 ID → 位置改成用它（演出落點取 `hit_tile` 或離來源最近的佔格）。
3. **點格選部位**（D5、T12）：點巨型頭目任一格 → 由 `partAtTile` 推出部位，**不跳選單**，直接預覽；打不到的部位格滑過時顯示原因（灰掉，原因同 `reason_zh`）；點前殼、已破、未露出的格＝本體。人形頭目（1 格）照段 1 的選單不變（`pb1cPartClick.test.ts` 原表不改）。
4. **範圍與高亮**：目標高亮蓋整個 3×3；範圍預覽、延遲落點預告（`telegraph.ts`、`followup.ts`）照伺服器給的格子；以頭目為中心的預告（熔心爆）照伺服器的格子，不用 `unit.pos` 自己推。
5. **卡片錨點**：滑過卡、部位卡錨在被點的那一格（`tileBox`），不錨中心。
6. **測試**（vitest）：`battle/gb4aGiantClick.test.ts`（9 格 × 選取模式的點擊表、部位推出、灰掉原因）、`footprint.test.ts`、事件窄化；後端 `tests/api/test_giant_api.py`、`test_openapi_snapshot.py`。
7. **瀏覽器實測**（6.5.1；`?dev=1&boss=` 進熔心坑，1600×900 與 800×600）：點每一種部位格、看預覽行、灰掉原因、熔岩噴發預告落在最遠的人。網址加 `?mute=1`、無頭 Chrome 加 `--mute-audio`；埠避開 8000／8001；目標瀏覽器照 `docs/開發PM交接.md` 3.0000 的派工規定。截圖 ≤ 8 張到 `docs/art/shots/gb4a/`。
8. `corepack pnpm -C client test`、`build`、`typecheck` 結束碼分開記，全部 0。報告 `docs/phases/PhaseGB-4a報告.md`；更新 `docs/dev/上手-前端戰鬥畫面與動畫.md`。

### 8.2 GB-4b｜繪製（占位）

1. **錨點與大小**：巨型單位的貼圖寬＝3 格、底邊對齊南排的南緣、水平置中於中心欄；沿用現有灰燼之心造型放大（`ringScale`／`creatureFieldScale` 改成以佔格寬算），標「占位，待美術」。
2. **z 順序**：放在**南排那一列**（`rows.row(中心 y + 1)`）、同列最前（現行 `index 0` 的頭目規則保留）；北排、中排的同列單位畫在它前面（實際上北排外是岩漿）。
3. **OCL**：`outlineLayer.ts` 的 `rowOf` 對巨型單位回南排；`canBeBig` 照面積算不改；確認被它擋住的單位照樣畫外框（`oclGallery.ts?scene=boss` 加一個 3×3 場面）。
4. **HP 條、蓄力徽章、選取圈**：放在 3×3 上方中間；選取圈改成 3×3 的框。
5. **部位格標示（占位）**：新檔 `render/battle/partTileMarks.ts`：殼縫、噴口、核心的格子畫細框＋部位小圖（沒有灰燼之心的部位小圖前用文字縮寫「縫」「口」「核」）；破掉打叉；未露出不畫；打不到時暗。全部集中在這一個檔，GB-4c 只換這裡。
6. **演出起點**：施放、受擊、浮動字落在 `hit_tile` 或面向目標的那一格（`vfxLayer`、`feedbackLayer`）。
7. 測試、截圖（`docs/art/shots/gb4b/`，≤ 10 張：三個階段各一、OCL 一、部位格標示一、800 寬一）、三個結束碼。報告列「占位，待美術移植」的清單。

### 8.3 GB-4c｜美術移植（等第 9 節交件）

只換 GB-4b 標成占位的貼圖、錨點數字、部位格標示畫法與破壞演出；驗收照美術 PM 的移植需求檢查清單，每項附截圖（記憶「美術驗收要每項都有截圖」）。

## 9. 給美術 PM 的需求（現在都還沒有，GB-4c 等這些）

| # | 項目 | 內容 | 前端誰在等 |
|---|---|---|---|
| A1 | 灰燼之心 3×3 立繪 | 佔 3 格寬的正面（朝南）造型；三個階段（殼、呼吸、熔毀）與熔殼在／不在的差分（沿用 `docs/art/頭目造型.md` 的設定與 `status_traits`）；**錨點**：底邊對齊南排南緣、高度上限（建議 ≤ 4 格高，北邊是岩漿可以往上長，見 19.2.3「從地圖面解決遮擋」）；800 寬與 1600 寬的實際像素 | GB-4c（GB-4b 先用放大的現有造型占位） |
| A2 | 部位格標示 | 殼縫、噴口、核心在格子上的標示（和霧鎖真人 PB-1e 的頭頂小格同一套語言）：一般、滑過亮起、打不到（暗＋原因）、破掉（打叉）、未露出（核心第 1 階段）；殼縫要讓人看出「算從背後」 | GB-4c（GB-4b 用 `partTileMarks.ts` 占位） |
| A3 | 部位小圖（Q 版） | 殼縫、噴口、核心三個圖示（給 `PartMenu`、`PartBar`、部位格標示；照 `docs/art/頭目部位-移植需求.md` 的尺寸與規則 9） | GB-4c（PartBar 先用文字） |
| A4 | 破壞演出 | 噴口封住（熔岩噴發沒了）、殼縫破（熔殼掉落）、核心破（蓄力打斷）三種；可沿用段 1 的白閃＋微震＋浮字，另加各自一個特效 | GB-4c |
| A5 | 改圖後熔心坑 | 用 GB-2 的新配置（高台 2 格、矮牆、4 口井、頭目在北）出一張戰場樣張，確認高台與北邊岩漿在現有灰燼地形畫法下看得出來、3×3 立繪不擋南邊的人；需要新地形貼圖再列 | GB-4c；**不擋 GB-2**（地形用現有畫法） |
| A6 | 熔岩噴發落點 | BAL-21b 的延遲落格預告可沿用（`QI-4b與BAL-21b驗收.md` 已過）；只要確認「落在最遠的人」時，預告和頭目之間要不要畫一條線（目前沒有連線） | 可選，不擋 |

建議美術 PM 在 GB-2 合併後開始（那時座標定了），GB-4b 合併後用開發頁（`oclGallery.ts?scene=boss`）對照。PB-1e 的頭頂部位小格畫法先定，A2、A3 照它延伸。

## 10. 平衡疑慮（不量，只記；PM 轉玩法 PM 記進 `docs/design/平衡待查.md`）

1. **近戰更好貼**：3×3 外圍有 12 格相鄰（1 格只有 4 格），近戰同時打它的人數與頻率上升；HP 160 與 5F-5b 量到的勝率 75％ 不再適用。
2. **R2 讓它自己的招範圍變大**：吐息環形 2 從 16 格變 24 格、熔心爆十字從 9 格變 24 格、吸氣 4 格內幾乎蓋到半個坑。
3. **範圍技只打一次**：範圍流打它和 1 格時一樣，但它變大後更容易被範圍蓋到，影響不大；連鎖流少一個跳點。
4. **熔岩噴發一定打最遠的人**：遠程與站高台的人每 2 回合必挨一次（1d6＋火地 2 回合），可能讓遠程主角特別吃虧。
5. **部位破壞的連鎖**：殼縫在第 1 階段就破＝熔殼（−40％ 傷害）提前沒了，第 1 階段可能變很短；核心破封吸氣 2 回合。
6. **火地生長（R6 A）**：每輪長一排、最多 4 排，可能把南半坑整片封住、我方無處可站。
7. **餘燼蜥追最遠的人**：遠程與高台同時被熔岩噴發與蜥蜴針對。
8. 赤焰（fire build）打火抗 −75％ 的頭目原本就慢（5F-5b 平均 14.7 輪），加上上面幾條可能更久。

## 11. 共通規矩（每段派工 prompt 都要寫）

- 實作者遇到規格沒寫到、或和設計文件衝突的地方，照最保守做法做並寫進報告「待 PM 決定」（最多 10 點）；**不自己定規則**，已寫入設計文件的決定不放寬。原型數值與解讀類照最保守的預設直接做完、寫進報告。
- 快照、雜湊、夾具不得整批重產；每一項先證明變動來自本段（拿掉改動回到舊值），對不上就停下回報；CLI 快照用 `-k` 只重產受影響的鍵。
- 開發中只跑直接相關的測試（不帶 `-m`，多檔最多 `-n 8`）；不跑 `scripts/check.py`、`trpg sim completion`／`matrix`；不跑任何平衡量測或模擬報表；PM 跑全量期間不跑大測試。
- Windows：`uv run python`；新 worktree 先 `uv sync --frozen`，之後 `UV_NO_SYNC=1`；前端 `corepack pnpm -C client …`，新 worktree 先 `install --frozen-lockfile --prefer-offline`。
- shell 指令的字串裡不放反引號（含反引號的文字用檔案工具或 `<<'EOF'`）；用 Python 改檔指定 `newline="\n"`。
- 等待用完成通知，不寫 until／while／sleep 輪詢；不結束不是自己啟動的程序，只用自己記下的 PID；預覽埠不用 8000、8001；瀏覽器測試一律靜音。
- 判斷版號是否已 push 前先 `git fetch`。
- 子 agent 一律 Opus 5.5（`model: "opus"`），並往下傳同樣規矩。
- 不要 push；依交付分 commit，第一行英文，結尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## 12. 報告格式

做了什麼（交付表＋commit）、逐條驗收（測試名或指令輸出為證、結束碼分開記）、現況確認（對照第 2 節，有出入就寫）、改了哪些呼叫點（檔案 × 處數，刻意不改的理由）、不變比對（場數、事件數、`different`、三個雜湊前後值、剝掉的預設鍵）、快照與既有測試變動逐條說明（含換種子的清單）、新增 `# noqa` 與理由、規格沒寫到而採保守做法的地方、影響（舊紀錄不能重播、戰鬥中存檔讀不回）、平衡疑慮、「待 PM 決定」最多 10 點。

## 開發 PM 裁定（2026-11-14）

- 規格採用（起草：開發 PM 派的 Opus 起草 agent；開發 PM 已對原文核對 R1：05 5.12.2 第 9 點與 5.12.4 第 4 點確實互相矛盾）。
- **技術類 T1～T20 照建議**。
- **規則類 R1～R7 經專案 PM 問使用者**（附建議，見 0.2；`docs/開發PM交接.md` 3.0001）。GB-1a 不受 R1～R7 影響，先派；GB-1b 等 R1、R2，GB-1c 等 R3～R6，GB-2 等 R5～R7。
- 第 9 節美術需求 A1～A6 轉美術 PM；只有 GB-4c 要等。第 10 節平衡疑慮轉玩法 PM 記平衡待查。
- **2026-11-14 使用者回 R1～R7**（專案 PM 轉，原話）：「都照建議」；R6 選 **A**（每輪往南長一排，最多 4 排，占位）。玩法 PM 寫入設計中（`docs/玩法PM交接.md` 4.1.9）。GB-1b、1c、2 照 0.2 建議做；T16 要做。
- **2026-11-14 玩法 PM 寫入設計 #164**（commit 1e527b1f5；`docs/玩法PM交接.md` 4.1.10）：05 5.12.4 第 2 點（R2）、第 4 點（R1，筆誤已更正）；19 19.2.3「巨型頭目段 GB 補定的細節」（R3～R7，與舊條衝突時以它為準）。**比 0.2 多一條**：R1「打中的那一格」就算落在部位格，防禦也照本體，不套部位自己的護甲、抗性。0.1 的 D6、D17、D19、D20、D22 出處改指 #164，規則不變。派 GB-1b、1c 時照這條。
- **2026-11-14 美術 GB 移植需求**（`docs/art/GB巨型頭目-移植需求.md`，A1～A4、A6 過審；A5 熔心坑樣張等 GB-2 合併，GB-4c 不等它）。第 7 節 8 條開發 PM 裁定：**全部照美術建議**；第 2 條「頭頂部位條」**要加**（噴口｜殼縫｜核心三條，照 `頭目部位-移植需求.md` 2.3 排法與 800 最小尺寸，和 PB-1e 一致）；第 6 條火星不收（照不擋），試玩覺得雜再收到佔格外 0.5 格內；第 8 條檔案位置照建議。GB-4b、4c 派工照此。
