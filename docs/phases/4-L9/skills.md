# 技能生成評估（swift（http://localhost:8001/v1））

種子 0；每題最多 3 次

## 升級候選

- 牆鐘時間 203 秒（平行 8）
- 題目 50（失敗丟例外 0）
- 一次通過 5（10.0%）；重試後通過 9（累計 28.0%）；退回 36（72.0%）　**⚠ 超過 20% 提醒線**
- 退回來源：workshop 4、composer 31、pool 1
- 平均嘗試 2.70
- 每題耗時（含命名）：平均 21.9 秒、p50 18.8、p90 30.1、最大 97.8
- 每次呼叫耗時：p50 6.7、p90 10.6 秒
- 引擎修補：exclusion.no_cooldown_big_area 18、budget.weak 2
- 呼叫 135 次；prompt token 平均 2003、最大 3541；輸出 token 平均 249、最大 2048
- HTTP 狀態：200 ×135
- 被接受的 schema 寫法：response_format ×135
- 結束原因：stop ×132、length ×3
- 第一次 prompt 的真實 token ÷ 估算（`estimate_tokens`）：平均 0.76、最小 0.75、最大 0.78
- 命名：14 個，llm 14；平均呼叫 1.00 次、平均 2.5 秒

| 錯誤代碼 | 次數 | 題數 | 這些題的平均嘗試 |
|---|---:|---:|---:|
| `value_error` | 34 | 24 | 2.83 |
| `budget.weak` | 25 | 17 | 2.94 |
| `reference` | 24 | 14 | 3.00 |
| `keyword.required` | 10 | 7 | 3.00 |
| `skeleton.secondary_share` | 10 | 6 | 3.00 |
| `skeleton.core_beneficial` | 6 | 4 | 3.00 |
| `exclusion.terrain_needs_earth` | 4 | 3 | 3.00 |
| `skeleton.forbidden_affects` | 4 | 3 | 3.00 |
| `json_invalid` | 3 | 2 | 3.00 |
| `on_kill.beneficial` | 3 | 2 | 3.00 |
| `variant.v1.budget.weak` | 3 | 2 | 3.00 |
| `cap.revive_cost` | 2 | 1 | 3.00 |
| `exclusion.stun_single_long_cooldown` | 2 | 2 | 3.00 |
| `variant.variant_breach.skeleton.forbidden_affects` | 2 | 1 | 3.00 |
| `variant.variant_breach.skeleton.secondary_count` | 2 | 1 | 3.00 |
| `exclusion.self_shape_no_enemy_effect` | 1 | 1 | 3.00 |
| `skeleton.core` | 1 | 1 | 3.00 |
| `skeleton.secondary_count` | 1 | 1 | 3.00 |
| `tier.element` | 1 | 1 | 3.00 |
| `variant.high_ground.budget.over` | 1 | 1 | 3.00 |
| `variant.high_ground.exclusion.terrain_needs_earth` | 1 | 1 | 3.00 |
| `variant.shatter.budget.weak` | 1 | 1 | 3.00 |
| `variant.shatter.skeleton.secondary_share` | 1 | 1 | 3.00 |
| `variant.v1.budget.over` | 1 | 1 | 3.00 |
| `variant.v1.exclusion.terrain_needs_earth` | 1 | 1 | 3.00 |
| `variant.variant_1.skeleton.secondary_count` | 1 | 1 | 3.00 |
| `variant.variant_breach.budget.over` | 1 | 1 | 3.00 |
| `variant.variant_breach.budget.weak` | 1 | 1 | 3.00 |

### 主題一致性抽樣

| # | 題目（關鍵字／主題／核心） | 名稱 | 結構 | 概念 |
|---:|---|---|---|---|
| 10 | collision／—／damage | 碎晶反震 | 反應技／單體／傷害（物理）＋推擊 | 以源晶頻率抵禦撞擊，將衝擊力轉化為向外的推擊。 |
| 18 | marked／—／topple | 碎晶壓頂 | 位移／單體／推倒＋傷害（物理）＋施加狀態（標記） | 引動源晶高頻震動，將單體目標狠狠推倒並施加標記。 |
| 32 | poisoned／—／heal | 晶韻淨化環 | 光環／範圍光環／治療 | 散發源晶低頻震動，在範圍內持續抵禦毒素侵蝕並修復受創之軀體。 |
| 41 | frozen／—／hurl_object | 霜潮・裂界之鑰 | 位移／物件與落點／投擲物件＋傷害（冰霜） | 擲出凝結的源晶碎片，在落點激起冰凍的衝擊波，將敵軍封於寒霜之中。 |
| 43 | high_ground／—／heal | 巔峰・源晶垂露 | 反應技／單體／治療 | 於高處凝結源晶頻率，化作垂落的治療之光，撫平單體創傷。 |
| 1 | —／—／revive | 晶頻回響 | 光環／單體／復活＋回復資源 | 以源晶的純粹頻率震動界域，使破碎的生命重新凝聚。 |
| 2 | —／—／heal | 晶頻迴響 | 反應技／自己／治療 | 在受傷瞬間，以自身源晶頻率共振，修復界域碎片的裂痕。 |
| 23 | —／—／heal | 晶頻・愈息疊層 | 反應技／單體／治療＋累積層數 | 以源晶低頻共振修復創傷，隨時間累積層數，讓生命如碎晶般重新生長。 |
| 26 | —／—／cleanse | 晶頻護環 | 光環／範圍光環／淨化＋護盾 | 以源晶的穩定頻率展開光環，淨化周遭的腐蝕並凝聚防禦。 |
| 29 | —／—／shield | 晶頻護環 | 光環／單體／護盾（護盾） | 以源晶低頻震動凝結光環，為受者築起抵禦崩碎力量的結界。 |

## 強制測試

- 牆鐘時間 379 秒（平行 8）
- 題目 132（失敗丟例外 0）
- 一次通過 8（6.1%）；重試後通過 25（累計 25.0%）；退回 99（75.0%）　**⚠ 超過 20% 提醒線**
- 退回來源：composer 99
- 平均嘗試 2.77
- 每題耗時（含命名）：平均 21.1 秒、p50 19.7、p90 28.6、最大 68.9
- 每次呼叫耗時：p50 7.1、p90 10.8 秒
- 引擎修補：exclusion.no_cooldown_big_area 25、exclusion.stun_single_long_cooldown 7、budget.weak 5、skeleton.secondary_share 2
- 呼叫 365 次；prompt token 平均 2133、最大 3179；輸出 token 平均 238、最大 2048
- HTTP 狀態：200 ×365
- 被接受的 schema 寫法：response_format ×365
- 結束原因：length ×2、stop ×363
- 第一次 prompt 的真實 token ÷ 估算（`estimate_tokens`）：平均 0.76、最小 0.75、最大 0.78

| 錯誤代碼 | 次數 | 題數 | 這些題的平均嘗試 |
|---|---:|---:|---:|
| `value_error` | 165 | 87 | 2.89 |
| `budget.weak` | 82 | 58 | 2.93 |
| `skeleton.secondary_share` | 38 | 23 | 3.00 |
| `reference` | 32 | 21 | 3.00 |
| `exclusion.terrain_needs_earth` | 18 | 8 | 3.00 |
| `cap.rule_rewrite_cost` | 15 | 11 | 3.00 |
| `on_kill.beneficial` | 4 | 4 | 3.00 |
| `variant.v1.skeleton.secondary_share` | 4 | 3 | 3.00 |
| `combo.max_per_skill` | 3 | 1 | 3.00 |
| `exclusion.self_shape_no_enemy_effect` | 3 | 3 | 3.00 |
| `shield.status` | 3 | 3 | 3.00 |
| `skeleton.core_share` | 3 | 3 | 3.00 |
| `variant.v1.budget.over` | 3 | 3 | 3.00 |
| `variant.variant_1.skeleton.secondary_share` | 3 | 2 | 3.00 |
| `cap.revive_cost` | 2 | 2 | 3.00 |
| `cap.rule_rewrite` | 2 | 2 | 3.00 |
| `exclusion.stun_single_long_cooldown` | 2 | 2 | 2.50 |
| `json_invalid` | 2 | 2 | 3.00 |
| `skeleton.core_beneficial` | 2 | 1 | 3.00 |
| `variant.crystalline_burst.skeleton.secondary_count` | 2 | 1 | 3.00 |
| `variant.crystalline_burst.skeleton.secondary_share` | 2 | 1 | 3.00 |
| `variant.height_advantage.budget.over` | 2 | 1 | 3.00 |
| `variant.self_hp_below.skeleton.forbidden_affects` | 2 | 1 | 3.00 |
| `variant.v1.shield.status` | 2 | 1 | 3.00 |
| `variant.v1.skeleton.secondary_count` | 2 | 2 | 3.00 |
| `variant.v2.shield.status` | 2 | 1 | 3.00 |
| `variant.variant_1.budget.over` | 2 | 2 | 3.00 |
| `variant.variant_1.budget.weak` | 2 | 2 | 3.00 |
| `variant.variant_1.skeleton.secondary_count` | 2 | 1 | 3.00 |
| `skeleton.forbidden_affects` | 1 | 1 | 3.00 |
| `skeleton.secondary` | 1 | 1 | 3.00 |
| `tier.terrain_area` | 1 | 1 | 3.00 |
| `variant.crystalline_burst.budget.over` | 1 | 1 | 3.00 |
| `variant.height_advantage.skeleton.secondary_share` | 1 | 1 | 3.00 |
| `variant.self_hp_below.budget.weak` | 1 | 1 | 3.00 |
| `variant.self_hp_below.cap.rule_rewrite_cost` | 1 | 1 | 3.00 |
| `variant.self_hp_below.exclusion.self_shape_no_enemy_effect` | 1 | 1 | 3.00 |
| `variant.self_hp_below.skeleton.secondary_count` | 1 | 1 | 3.00 |
| `variant.v1.budget.weak` | 1 | 1 | 3.00 |
| `variant.v1.cap.rule_rewrite` | 1 | 1 | 3.00 |
| `variant.v1.exclusion.stun_single_long_cooldown` | 1 | 1 | 3.00 |
| `variant.v2.budget.over` | 1 | 1 | 3.00 |
| `variant.v2.cap.rule_rewrite` | 1 | 1 | 3.00 |
| `variant.variant_1.exclusion.stun_single_long_cooldown` | 1 | 1 | 3.00 |
| `variant.variant_1.exclusion.terrain_needs_earth` | 1 | 1 | 3.00 |
| `variant.variant_1.skeleton.core_share` | 1 | 1 | 3.00 |
| `variant.variant_2.budget.over` | 1 | 1 | 3.00 |
| `variant.variant_2.exclusion.no_cooldown_big_area` | 1 | 1 | 3.00 |
| `variant.variant_2.skeleton.secondary_share` | 1 | 1 | 3.00 |

### 每個核心原語

| 原語 | 中文 | 題數 | 一次通過 | 重試通過 | 退回 | 錯誤代碼 |
|---|---|---:|---:|---:|---:|---|
| `damage` | 傷害 | 3 | 1 | 1 | 1 | `value_error`×2、`json_invalid`×1、`cap.rule_rewrite_cost`×1、`exclusion.self_shape_no_enemy_effect`×1 |
| `heal` | 治療 | 3 | 0 | 1 | 2 | `value_error`×8 |
| `shield` | 護盾 | 3 | 1 | 1 | 1 | `reference`×5、`value_error`×3、`variant.v1.shield.status`×2、`variant.v2.shield.status`×2、`shield.status`×1、`variant.v1.budget.over`×1、`variant.v2.budget.over`×1 |
| `cleanse` | 淨化 | 3 | 1 | 1 | 1 | `value_error`×4、`budget.weak`×1 |
| `push` | 推擊 | 3 | 0 | 0 | 3 | `value_error`×9 |
| `pull` | 拉扯 | 3 | 0 | 0 | 3 | `value_error`×7、`exclusion.stun_single_long_cooldown`×1、`exclusion.self_shape_no_enemy_effect`×1、`budget.weak`×1 |
| `knock_prone` | 擊倒 | 3 | 0 | 0 | 3 | `value_error`×3、`skeleton.secondary_share`×2、`variant.height_advantage.budget.over`×2、`budget.weak`×2、`variant.height_advantage.skeleton.secondary_share`×1、`reference`×1 |
| `shockwave` | 震波 | 3 | 0 | 0 | 3 | `exclusion.terrain_needs_earth`×8、`skeleton.secondary_share`×5、`budget.weak`×3、`reference`×1 |
| `teleport` | 傳送 | 3 | 0 | 0 | 3 | `value_error`×6、`budget.weak`×3 |
| `charge_through` | 直線衝撞 | 3 | 0 | 3 | 0 | `value_error`×3 |
| `shadowstep` | 瞬步 | 3 | 0 | 2 | 1 | `value_error`×4、`skeleton.secondary_share`×1、`on_kill.beneficial`×1、`budget.weak`×1 |
| `leap` | 跳躍 | 3 | 0 | 0 | 3 | `budget.weak`×4、`value_error`×3、`reference`×1、`on_kill.beneficial`×1 |
| `swap` | 交換位置 | 3 | 0 | 0 | 3 | `budget.weak`×5、`value_error`×4、`on_kill.beneficial`×1 |
| `teleport_target` | 傳送他人 | 3 | 0 | 1 | 2 | `budget.weak`×4、`value_error`×2、`reference`×1 |
| `swap_any` | 任意兩者互換 | 3 | 0 | 1 | 2 | `budget.weak`×4、`value_error`×3 |
| `apply_status` | 施加狀態 | 3 | 0 | 2 | 1 | `budget.weak`×3、`value_error`×1、`skeleton.secondary_share`×1、`variant.v1.exclusion.stun_single_long_cooldown`×1、`variant.v1.skeleton.secondary_share`×1、`variant.v1.budget.over`×1 |
| `create_surface` | 產生表面 | 3 | 0 | 0 | 3 | `skeleton.secondary_share`×3、`budget.weak`×3、`value_error`×2、`shield.status`×1、`skeleton.secondary`×1 |
| `create_obstacle` | 產生障礙 | 3 | 0 | 0 | 3 | `skeleton.secondary_share`×4、`value_error`×3、`reference`×2、`budget.weak`×1、`variant.variant_1.skeleton.secondary_share`×1、`variant.variant_1.budget.over`×1、`variant.variant_2.exclusion.no_cooldown_big_area`×1、`variant.variant_2.skeleton.secondary_share`×1、`variant.variant_2.budget.over`×1 |
| `raise_terrain` | 隆起地形 | 3 | 0 | 1 | 2 | `exclusion.terrain_needs_earth`×6、`budget.weak`×6、`variant.variant_1.skeleton.secondary_count`×2、`variant.variant_1.skeleton.secondary_share`×2、`variant.variant_1.exclusion.terrain_needs_earth`×1、`variant.variant_1.budget.weak`×1、`variant.variant_1.budget.over`×1 |
| `lower_terrain` | 下陷地形 | 3 | 0 | 0 | 3 | `value_error`×5、`exclusion.terrain_needs_earth`×4、`budget.weak`×3、`tier.terrain_area`×1 |
| `intercept` | 替隊友擋攻擊 | 3 | 0 | 0 | 3 | `value_error`×8、`budget.weak`×1 |
| `consume_status` | 消耗狀態 | 3 | 0 | 0 | 3 | `value_error`×5、`budget.weak`×4、`skeleton.core_share`×3、`variant.variant_1.exclusion.stun_single_long_cooldown`×1、`variant.variant_1.skeleton.core_share`×1、`variant.variant_1.budget.weak`×1 |
| `grant_ap` | 給予 AP | 3 | 0 | 0 | 3 | `value_error`×4、`reference`×2、`budget.weak`×2、`cap.rule_rewrite_cost`×2、`variant.v1.cap.rule_rewrite`×1、`variant.v1.budget.over`×1、`variant.v2.cap.rule_rewrite`×1 |
| `reset_cooldown` | 重置冷卻 | 3 | 0 | 0 | 3 | `value_error`×7、`cap.rule_rewrite_cost`×1、`shield.status`×1、`reference`×1 |
| `cheat_death` | 免死 | 3 | 0 | 0 | 3 | `value_error`×5、`cap.rule_rewrite_cost`×2、`budget.weak`×2、`reference`×2、`variant.self_hp_below.skeleton.forbidden_affects`×2、`cap.rule_rewrite`×1、`exclusion.self_shape_no_enemy_effect`×1、`skeleton.forbidden_affects`×1、`variant.self_hp_below.cap.rule_rewrite_cost`×1、`variant.self_hp_below.exclusion.self_shape_no_enemy_effect`×1、`variant.self_hp_below.skeleton.secondary_count`×1、`variant.self_hp_below.budget.weak`×1 |
| `redirect_damage` | 分擔傷害 | 3 | 0 | 0 | 3 | `value_error`×5、`budget.weak`×4、`cap.rule_rewrite_cost`×3 |
| `copy_skill` | 複製技能 | 3 | 0 | 0 | 3 | `value_error`×7、`budget.weak`×2、`cap.rule_rewrite_cost`×1 |
| `extra_reaction` | 額外反應 | 3 | 0 | 1 | 2 | `cap.rule_rewrite_cost`×3、`budget.weak`×3、`value_error`×2、`reference`×1、`cap.rule_rewrite`×1 |
| `hurl_object` | 投擲物件 | 3 | 1 | 2 | 0 | `value_error`×1、`exclusion.stun_single_long_cooldown`×1 |
| `topple` | 推倒 | 3 | 0 | 0 | 3 | `reference`×3、`budget.weak`×3、`value_error`×3、`on_kill.beneficial`×1 |
| `restore_resource` | 回復資源 | 3 | 0 | 2 | 1 | `budget.weak`×5、`cap.rule_rewrite_cost`×2 |
| `steal_buff` | 奪取增益 | 3 | 0 | 0 | 3 | `value_error`×4、`skeleton.secondary_share`×3、`budget.weak`×2 |
| `dispel` | 驅散 | 3 | 0 | 0 | 3 | `skeleton.secondary_share`×5、`value_error`×3、`variant.crystalline_burst.skeleton.secondary_count`×2、`variant.crystalline_burst.skeleton.secondary_share`×2、`reference`×1、`variant.crystalline_burst.budget.over`×1 |
| `reveal` | 揭露 | 3 | 0 | 1 | 2 | `skeleton.secondary_share`×3、`value_error`×3、`budget.weak`×2 |
| `revive` | 復活 | 3 | 0 | 0 | 3 | `combo.max_per_skill`×3、`value_error`×2、`cap.revive_cost`×2、`skeleton.core_beneficial`×2、`budget.weak`×2、`reference`×1 |
| `delayed_damage` | 定時炸彈 | 3 | 2 | 1 | 0 | `value_error`×1 |
| `summon` | 召喚 | 3 | 1 | 0 | 2 | `value_error`×4、`budget.weak`×2 |
| `zone` | 持續區域 | 3 | 0 | 0 | 3 | `value_error`×9 |
| `grant_skill` | 暫時獲得技能 | 3 | 0 | 0 | 3 | `reference`×7、`value_error`×2 |
| `inscribe` | 刻印 | 3 | 0 | 0 | 3 | `value_error`×7、`budget.weak`×1、`reference`×1 |
| `detonate_runes` | 引爆符文 | 3 | 0 | 3 | 0 | `value_error`×4、`reference`×1 |
| `sacrifice_summon` | 獻祭召喚物 | 3 | 1 | 1 | 1 | `value_error`×4、`json_invalid`×1 |
| `blow_surface` | 吹送 | 3 | 0 | 0 | 3 | `skeleton.secondary_share`×7、`variant.v1.skeleton.secondary_share`×2、`reference`×1、`budget.weak`×1、`variant.v1.budget.weak`×1、`variant.v1.skeleton.secondary_count`×1 |
| `clear_surface` | 清除表面 | 3 | 0 | 0 | 3 | `skeleton.secondary_share`×4、`value_error`×3、`budget.weak`×2、`variant.v1.skeleton.secondary_count`×1、`variant.v1.skeleton.secondary_share`×1 |

通過率低於 2/3 的原語：`heal`、`push`、`pull`、`knock_prone`、`shockwave`、`teleport`、`leap`、`swap`、`teleport_target`、`swap_any`、`create_surface`、`create_obstacle`、`raise_terrain`、`lower_terrain`、`intercept`、`consume_status`、`grant_ap`、`reset_cooldown`、`cheat_death`、`redirect_damage`、`copy_skill`、`extra_reaction`、`topple`、`steal_buff`、`dispel`、`reveal`、`revive`、`summon`、`zone`、`grant_skill`、`inscribe`、`blow_surface`、`clear_surface`

## 自由測試

- 牆鐘時間 771 秒（平行 8）
- 題目 300（失敗丟例外 0）
- 一次通過 127（42.3%）；重試後通過 98（累計 75.0%）；退回 75（25.0%）　**⚠ 超過 20% 提醒線**
- 退回來源：composer 75
- 平均嘗試 1.95
- 每題耗時（含命名）：平均 19.2 秒、p50 15.6、p90 34.7、最大 188.0
- 每次呼叫耗時：p50 8.9、p90 13.5 秒
- 引擎修補：exclusion.no_cooldown_big_area 14、exclusion.stun_single_long_cooldown 10、budget.weak 6、skeleton.core_share 6、skeleton.secondary_share 4
- 呼叫 586 次；prompt token 平均 3784、最大 6183；輸出 token 平均 246、最大 2048
- HTTP 狀態：200 ×586
- 被接受的 schema 寫法：response_format ×586
- 結束原因：stop ×580、length ×6
- 第一次 prompt 的真實 token ÷ 估算（`estimate_tokens`）：平均 0.75、最小 0.74、最大 0.78

| 錯誤代碼 | 次數 | 題數 | 這些題的平均嘗試 |
|---|---:|---:|---:|
| `value_error` | 219 | 120 | 2.75 |
| `reference` | 78 | 46 | 2.67 |
| `on_kill.beneficial` | 27 | 23 | 2.70 |
| `skeleton.secondary_share` | 18 | 12 | 3.00 |
| `budget.weak` | 14 | 13 | 2.85 |
| `variant.v1.skeleton.secondary_count` | 14 | 8 | 3.00 |
| `json_invalid` | 6 | 4 | 3.00 |
| `exclusion.self_shape_no_enemy_effect` | 3 | 3 | 2.33 |
| `exclusion.stun_single_long_cooldown` | 3 | 3 | 2.00 |
| `variant.v1.skeleton.secondary_share` | 3 | 2 | 3.00 |
| `variant.v1.budget.over` | 2 | 2 | 3.00 |
| `variant.v1.skeleton.core_share` | 2 | 1 | 3.00 |
| `variant.v1.skeleton.secondary` | 2 | 2 | 3.00 |
| `variant.v_fire.budget.weak` | 2 | 1 | 3.00 |
| `variant.variant_frost.budget.weak` | 2 | 1 | 3.00 |
| `variant.variant_frostbite.budget.over` | 2 | 1 | 3.00 |
| `budget.over` | 1 | 1 | 2.00 |
| `followup.skeleton.core` | 1 | 1 | 3.00 |
| `followup.skeleton.core_share` | 1 | 1 | 3.00 |
| `followup.skeleton.secondary` | 1 | 1 | 3.00 |
| `followup.skeleton.secondary_count` | 1 | 1 | 3.00 |
| `skeleton.core` | 1 | 1 | 3.00 |
| `skeleton.core_share` | 1 | 1 | 2.00 |
| `skeleton.secondary_count` | 1 | 1 | 3.00 |
| `skeleton.shape` | 1 | 1 | 3.00 |
| `variant.frost_shatter.budget.over` | 1 | 1 | 3.00 |
| `variant.frostbite.budget.over` | 1 | 1 | 2.00 |
| `variant.frostbite.exclusion.stun_single_long_cooldown` | 1 | 1 | 2.00 |
| `variant.shatter.budget.weak` | 1 | 1 | 3.00 |
| `variant.shatter.skeleton.secondary_count` | 1 | 1 | 3.00 |
| `variant.shatter.skeleton.secondary_share` | 1 | 1 | 3.00 |
| `variant.v1.exclusion.no_repeated_control_group` | 1 | 1 | 3.00 |
| `variant.v2.skeleton.secondary_count` | 1 | 1 | 3.00 |
| `variant.variant_1.skeleton.secondary_count` | 1 | 1 | 2.00 |
| `variant.variant_ashen.skeleton.secondary_count` | 1 | 1 | 3.00 |
| `variant.variant_frost.skeleton.secondary_share` | 1 | 1 | 3.00 |
| `variant.variant_heavy.budget.weak` | 1 | 1 | 3.00 |

### 選單與選中率（對照隨機組合器）

平均選中率 3.2%；低於 1.1%（平均的 1/3）或 0 次標 ⚠。

| 原語 | 中文 | 選單次數 | 被選次數 | 選中率 | 被選占比 | 組合器占比 | 標記 |
|---|---|---:|---:|---:|---:|---:|---|
| `apply_status` | 施加狀態 | 300 | 171 | 57.0% | 38.3% | 24.2% |  |
| `damage` | 傷害 | 300 | 214 | 71.3% | 47.9% | 30.8% |  |
| `heal` | 治療 | 300 | 2 | 0.7% | 0.4% | 6.2% | ⚠ |
| `shield` | 護盾 | 300 | 4 | 1.3% | 0.9% | 8.3% |  |
| `cleanse` | 淨化 | 276 | 0 | 0.0% | 0.0% | 2.1% | ⚠ |
| `pull` | 拉扯 | 190 | 2 | 1.1% | 0.4% | 3.2% |  |
| `push` | 推擊 | 190 | 1 | 0.5% | 0.2% | 3.2% | ⚠ |
| `intercept` | 替隊友擋攻擊 | 179 | 3 | 1.7% | 0.7% | 0.9% |  |
| `raise_terrain` | 隆起地形 | 171 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `reveal` | 揭露 | 171 | 0 | 0.0% | 0.0% | 1.1% | ⚠ |
| `consume_status` | 消耗狀態 | 168 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `lower_terrain` | 下陷地形 | 167 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `dispel` | 驅散 | 166 | 0 | 0.0% | 0.0% | 0.9% | ⚠ |
| `add_stack` | 累積層數 | 165 | 2 | 1.2% | 0.4% | 1.7% |  |
| `consume_stack` | 消耗層數 | 165 | 0 | 0.0% | 0.0% | 0.4% | ⚠ |
| `create_obstacle` | 產生障礙 | 165 | 0 | 0.0% | 0.0% | 0.8% | ⚠ |
| `steal_buff` | 奪取增益 | 165 | 0 | 0.0% | 0.0% | 0.6% | ⚠ |
| `topple` | 推倒 | 165 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `create_surface` | 產生表面 | 164 | 36 | 22.0% | 8.1% | 6.2% |  |
| `knock_prone` | 擊倒 | 163 | 9 | 5.5% | 2.0% | 3.2% |  |
| `restore_resource` | 回復資源 | 162 | 2 | 1.2% | 0.4% | 0.6% |  |
| `blow_surface` | 吹送 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `clear_surface` | 清除表面 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `delayed_damage` | 定時炸彈 | 155 | 0 | 0.0% | 0.0% | 0.8% | ⚠ |
| `destroy_object` | 摧毀物件 | 155 | 0 | 0.0% | 0.0% | 0.8% | ⚠ |
| `detonate_runes` | 引爆符文 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `grant_skill` | 暫時獲得技能 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `hurl_object` | 投擲物件 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `inscribe` | 刻印 | 155 | 1 | 0.6% | 0.2% | 1.1% | ⚠ |
| `revive` | 復活 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `shockwave` | 震波 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `teleport_target` | 傳送他人 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `zone` | 持續區域 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `enter_form` | 進入形態 | 150 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `leave_form` | 解除形態 | 142 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `gamble` | 賭注 | 139 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `charge_through` | 直線衝撞 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `leap` | 跳躍 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `sacrifice_summon` | 獻祭召喚物 | 99 | 0 | 0.0% | 0.0% | 0.9% | ⚠ |
| `shadowstep` | 瞬步 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `summon` | 召喚 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `swap` | 交換位置 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `swap_any` | 任意兩者互換 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `teleport` | 傳送 | 99 | 0 | 0.0% | 0.0% | 0.6% | ⚠ |
| `place_trap` | 放置陷阱 | 89 | 0 | 0.0% | 0.0% | 1.1% | ⚠ |
| `dash` | 衝鋒 | 80 | 0 | 0.0% | 0.0% | 0.2% | ⚠ |
| `grant_ap` | 給予 AP | 58 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `cheat_death` | 免死 | 56 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `extra_reaction` | 額外反應 | 56 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `redirect_damage` | 分擔傷害 | 56 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `reset_cooldown` | 重置冷卻 | 54 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `copy_skill` | 複製技能 | 53 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
