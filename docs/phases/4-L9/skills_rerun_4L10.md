# 技能生成評估（swift（http://localhost:8001/v1））

種子 0；每題最多 3 次

## 升級候選

- 牆鐘時間 105 秒（平行 8）
- 題目 50（失敗丟例外 0）
- 一次通過 13（26.0%）；重試後通過 18（累計 62.0%）；退回 19（38.0%）　**⚠ 超過 20% 提醒線**
- 退回來源：workshop 4、composer 14、pool 1
- 平均嘗試 2.20
- 每題耗時（含命名）：平均 15.0 秒、p50 14.8、p90 21.4、最大 23.8
- 每次呼叫耗時：p50 6.0、p90 8.3 秒
- 引擎修補：budget.weak 19、exclusion.no_cooldown_big_area 11、exclusion.stun_single_long_cooldown 3、cap.rule_rewrite_cost 2、cap.revive_cost 1、skeleton.secondary_share 1
- 呼叫 110 次；prompt token 平均 1938、最大 3517；輸出 token 平均 169、最大 311
- HTTP 狀態：200 ×110
- 被接受的 schema 寫法：response_format ×110
- 結束原因：stop ×110
- 第一次 prompt 的真實 token ÷ 估算（`estimate_tokens`）：平均 0.76、最小 0.75、最大 0.78
- 命名：31 個，llm 31；平均呼叫 1.03 次、平均 2.5 秒

| 錯誤代碼 | 次數 | 題數 | 這些題的平均嘗試 |
|---|---:|---:|---:|
| `budget.weak` | 28 | 17 | 2.76 |
| `keyword.required` | 20 | 14 | 2.79 |
| `value_error` | 8 | 5 | 2.80 |
| `exclusion.stun_single_long_cooldown` | 5 | 4 | 2.50 |
| `skeleton.core_beneficial` | 5 | 3 | 3.00 |
| `skeleton.forbidden_affects` | 5 | 3 | 3.00 |
| `exclusion.self_shape_no_enemy_effect` | 4 | 2 | 3.00 |
| `reference` | 3 | 3 | 3.00 |
| `skeleton.secondary_share` | 3 | 2 | 3.00 |
| `shield.status` | 2 | 2 | 2.00 |
| `skeleton.core` | 2 | 1 | 3.00 |
| `variant.variant_1.skeleton.core_beneficial` | 2 | 1 | 3.00 |
| `exclusion.terrain_needs_earth` | 1 | 1 | 3.00 |
| `on_kill.beneficial` | 1 | 1 | 2.00 |
| `skeleton.core_share` | 1 | 1 | 2.00 |
| `variant.summon_echo.budget.over` | 1 | 1 | 3.00 |

### 主題一致性抽樣

| # | 題目（關鍵字／主題／核心） | 名稱 | 結構 | 概念 |
|---:|---|---|---|---|
| 4 | marked／nature／sacrifice_summon | 殘響・孤祭 | 獻祭／單體／獻祭召喚物（毒素）＋獻祭召喚物（大地）＋獻祭召喚物（風）＋獻祭召喚物（毒素） | 以召喚物的殘魂為引，將標記刻入單體敵人的靈魂深處，換取一瞬的寂靜。 |
| 6 | poisoned／—／consume_status | 蝕毒・斷鏈 | 消耗狀態／單體／消耗狀態（毒素） | 將單體目標累積的中毒狀態轉化為純粹的消耗，徹底剝離其生命韌性。 |
| 7 | collision／—／teleport_target | 碎界・撞落 | 位移／單位與落點／傳送他人 | 以殘破的源晶頻率為錨，將目標連同其所在的空間一併撞向指定的落點。 |
| 10 | collision／—／damage | 磐石・震盪 | 反應技／單體／傷害（大地）＋推擊 | 以堅實的反震之力，將敵人撞開並造成傷害。 |
| 13 | wet／—／grant_skill | 濕痕・暫息 | 光環／單體／暫時獲得技能 | 潮氣凝結為單體光環，短暫繼承異界技能的殘餘頻率。 |
| 14 | frozen／—／create_surface | 凝霜・封鎖 | 控場／單體／產生表面（冰霜）＋施加狀態（冰凍） | 將源晶的低頻震盪凝結為實體冰層，瞬間凍結目標並剝奪其行動能力。 |
| 18 | marked／—／topple | 斷脊・重壓 | 位移／單體／推倒＋傷害（物理）＋施加狀態（標記） | 以源晶的低頻震動壓垮敵手，使其倒地並留下無法擺脫的標記。 |
| 21 | marked／nature／topple | 裂紋・標記 | 位移／單體／推倒＋施加狀態（定身）＋施加狀態（標記） | 以源晶頻率撕開空間裂隙，將敵手釘在殘破的界域邊緣，使其失去平衡。 |
| 24 | —／nature／restore_resource | 餘溫・環抱 | 光環／範圍光環／回復資源 | 在崩裂的虛空邊緣，以源晶殘留的頻率編織一圈溫暖的光暉，讓同行者在冷寂中重新凝聚氣力。 |
| 25 | prone／—／zone | 燃域・方陣 | 控場／方陣／持續區域（火焰） | 以源晶頻率點燃地面，形成持續灼燒的方陣區域，令敵人在火光中倒地。 |

## 強制測試

- 牆鐘時間 199 秒（平行 8）
- 題目 132（失敗丟例外 0）
- 一次通過 54（40.9%）；重試後通過 48（累計 77.3%）；退回 30（22.7%）　**⚠ 超過 20% 提醒線**
- 退回來源：composer 30
- 平均嘗試 1.92
- 每題耗時（含命名）：平均 11.4 秒、p50 10.8、p90 17.5、最大 36.8
- 每次呼叫耗時：p50 5.8、p90 7.7 秒
- 引擎修補：budget.weak 54、exclusion.no_cooldown_big_area 43、cap.rule_rewrite_cost 33、exclusion.stun_single_long_cooldown 6、cap.revive_cost 3、skeleton.secondary_share 2、budget.over 1、skeleton.core_share 1
- 呼叫 254 次；prompt token 平均 2060、最大 3082；輸出 token 平均 153、最大 1024
- HTTP 狀態：200 ×254
- 被接受的 schema 寫法：response_format ×254
- 結束原因：stop ×253、length ×1
- 第一次 prompt 的真實 token ÷ 估算（`estimate_tokens`）：平均 0.76、最小 0.75、最大 0.78

| 錯誤代碼 | 次數 | 題數 | 這些題的平均嘗試 |
|---|---:|---:|---:|
| `budget.weak` | 96 | 59 | 2.56 |
| `skeleton.secondary_share` | 20 | 14 | 2.86 |
| `value_error` | 19 | 12 | 2.83 |
| `exclusion.terrain_needs_earth` | 17 | 9 | 2.56 |
| `on_kill.beneficial` | 5 | 2 | 3.00 |
| `skeleton.forbidden_affects` | 5 | 2 | 3.00 |
| `exclusion.self_shape_no_enemy_effect` | 3 | 2 | 3.00 |
| `shield.status` | 3 | 2 | 3.00 |
| `cap.rule_rewrite` | 2 | 2 | 3.00 |
| `variant.variant_1.shield.status` | 2 | 1 | 3.00 |
| `variant.variant_1.skeleton.forbidden_affects` | 2 | 1 | 3.00 |
| `variant.variant_2.shield.status` | 2 | 1 | 3.00 |
| `variant.variant_2.skeleton.forbidden_affects` | 2 | 1 | 3.00 |
| `combo.max_per_skill` | 1 | 1 | 2.00 |
| `json_invalid` | 1 | 1 | 2.00 |
| `reference` | 1 | 1 | 3.00 |
| `skeleton.secondary` | 1 | 1 | 2.00 |
| `variant.swift.budget.over` | 1 | 1 | 3.00 |
| `variant.swift.cap.rule_rewrite_cost` | 1 | 1 | 3.00 |
| `variant.v1.budget.weak` | 1 | 1 | 3.00 |
| `variant.v1.skeleton.forbidden_affects` | 1 | 1 | 3.00 |
| `variant.v1.skeleton.secondary_count` | 1 | 1 | 3.00 |
| `variant.v1.skeleton.secondary_share` | 1 | 1 | 3.00 |

### 每個核心原語

| 原語 | 中文 | 題數 | 一次通過 | 重試通過 | 退回 | 錯誤代碼 |
|---|---|---:|---:|---:|---:|---|
| `damage` | 傷害 | 3 | 1 | 2 | 0 | `json_invalid`×1、`skeleton.secondary`×1 |
| `heal` | 治療 | 3 | 1 | 0 | 2 | `value_error`×6 |
| `shield` | 護盾 | 3 | 2 | 1 | 0 | `shield.status`×2、`variant.variant_1.shield.status`×2、`variant.variant_1.skeleton.forbidden_affects`×2、`variant.variant_2.shield.status`×2、`variant.variant_2.skeleton.forbidden_affects`×2 |
| `cleanse` | 淨化 | 3 | 0 | 1 | 2 | `budget.weak`×3、`skeleton.forbidden_affects`×3、`variant.swift.budget.over`×1、`variant.swift.cap.rule_rewrite_cost`×1 |
| `push` | 推擊 | 3 | 1 | 2 | 0 | `budget.weak`×2 |
| `pull` | 拉扯 | 3 | 1 | 0 | 2 | `value_error`×3、`budget.weak`×3 |
| `knock_prone` | 擊倒 | 3 | 0 | 3 | 0 | `budget.weak`×3、`skeleton.secondary_share`×1 |
| `shockwave` | 震波 | 3 | 0 | 2 | 1 | `exclusion.terrain_needs_earth`×6、`budget.weak`×1 |
| `teleport` | 傳送 | 3 | 1 | 2 | 0 | `budget.weak`×2 |
| `charge_through` | 直線衝撞 | 3 | 3 | 0 | 0 | — |
| `shadowstep` | 瞬步 | 3 | 3 | 0 | 0 | — |
| `leap` | 跳躍 | 3 | 0 | 3 | 0 | `budget.weak`×4 |
| `swap` | 交換位置 | 3 | 0 | 2 | 1 | `on_kill.beneficial`×3、`budget.weak`×2 |
| `teleport_target` | 傳送他人 | 3 | 3 | 0 | 0 | — |
| `swap_any` | 任意兩者互換 | 3 | 3 | 0 | 0 | — |
| `apply_status` | 施加狀態 | 3 | 1 | 2 | 0 | `budget.weak`×2、`exclusion.self_shape_no_enemy_effect`×1 |
| `create_surface` | 產生表面 | 3 | 0 | 2 | 1 | `budget.weak`×5、`skeleton.secondary_share`×2 |
| `create_obstacle` | 產生障礙 | 3 | 0 | 1 | 2 | `budget.weak`×8、`skeleton.secondary_share`×5 |
| `raise_terrain` | 隆起地形 | 3 | 0 | 1 | 2 | `exclusion.terrain_needs_earth`×7 |
| `lower_terrain` | 下陷地形 | 3 | 0 | 2 | 1 | `exclusion.terrain_needs_earth`×4、`value_error`×1、`budget.weak`×1 |
| `intercept` | 替隊友擋攻擊 | 3 | 0 | 2 | 1 | `budget.weak`×3、`value_error`×2、`exclusion.self_shape_no_enemy_effect`×2 |
| `consume_status` | 消耗狀態 | 3 | 3 | 0 | 0 | — |
| `grant_ap` | 給予 AP | 3 | 2 | 0 | 1 | `budget.weak`×2、`cap.rule_rewrite`×1 |
| `reset_cooldown` | 重置冷卻 | 3 | 0 | 2 | 1 | `budget.weak`×3、`value_error`×2、`shield.status`×1 |
| `cheat_death` | 免死 | 3 | 1 | 0 | 2 | `budget.weak`×6、`skeleton.forbidden_affects`×2 |
| `redirect_damage` | 分擔傷害 | 3 | 1 | 1 | 1 | `budget.weak`×4、`cap.rule_rewrite`×1、`variant.v1.skeleton.forbidden_affects`×1、`variant.v1.budget.weak`×1 |
| `copy_skill` | 複製技能 | 3 | 2 | 0 | 1 | `budget.weak`×2、`value_error`×1 |
| `extra_reaction` | 額外反應 | 3 | 2 | 1 | 0 | `budget.weak`×1 |
| `hurl_object` | 投擲物件 | 3 | 2 | 1 | 0 | `on_kill.beneficial`×2 |
| `topple` | 推倒 | 3 | 2 | 1 | 0 | `budget.weak`×1 |
| `restore_resource` | 回復資源 | 3 | 1 | 2 | 0 | `budget.weak`×2、`value_error`×1 |
| `steal_buff` | 奪取增益 | 3 | 0 | 2 | 1 | `budget.weak`×4、`variant.v1.skeleton.secondary_count`×1、`variant.v1.skeleton.secondary_share`×1 |
| `dispel` | 驅散 | 3 | 0 | 1 | 2 | `budget.weak`×8、`skeleton.secondary_share`×4 |
| `reveal` | 揭露 | 3 | 2 | 1 | 0 | `skeleton.secondary_share`×1、`budget.weak`×1 |
| `revive` | 復活 | 3 | 2 | 1 | 0 | `combo.max_per_skill`×1 |
| `delayed_damage` | 定時炸彈 | 3 | 3 | 0 | 0 | — |
| `summon` | 召喚 | 3 | 2 | 1 | 0 | `value_error`×1 |
| `zone` | 持續區域 | 3 | 0 | 1 | 2 | `budget.weak`×5、`reference`×1、`value_error`×1 |
| `grant_skill` | 暫時獲得技能 | 3 | 3 | 0 | 0 | — |
| `inscribe` | 刻印 | 3 | 1 | 2 | 0 | `budget.weak`×3 |
| `detonate_runes` | 引爆符文 | 3 | 2 | 1 | 0 | `value_error`×1 |
| `sacrifice_summon` | 獻祭召喚物 | 3 | 3 | 0 | 0 | — |
| `blow_surface` | 吹送 | 3 | 0 | 1 | 2 | `budget.weak`×8、`skeleton.secondary_share`×4 |
| `clear_surface` | 清除表面 | 3 | 0 | 1 | 2 | `budget.weak`×7、`skeleton.secondary_share`×3 |

通過率低於 2/3 的原語：`heal`、`cleanse`、`pull`、`create_obstacle`、`raise_terrain`、`cheat_death`、`dispel`、`zone`、`blow_surface`、`clear_surface`

## 自由測試

- 牆鐘時間 438 秒（平行 8）
- 題目 300（失敗丟例外 0）
- 一次通過 219（73.0%）；重試後通過 61（累計 93.3%）；退回 20（6.7%）
- 退回來源：composer 20
- 平均嘗試 1.38
- 每題耗時（含命名）：平均 10.7 秒、p50 7.9、p90 18.3、最大 44.4
- 每次呼叫耗時：p50 7.5、p90 10.2 秒
- 引擎修補：skeleton.core_share 14、budget.weak 11、exclusion.no_cooldown_big_area 11、exclusion.stun_single_long_cooldown 2、skeleton.secondary_share 1、cap.rule_rewrite_cost 1
- 呼叫 414 次；prompt token 平均 3335、最大 5985；輸出 token 平均 182、最大 1024
- HTTP 狀態：200 ×414
- 被接受的 schema 寫法：response_format ×414
- 結束原因：stop ×410、length ×4
- 第一次 prompt 的真實 token ÷ 估算（`estimate_tokens`）：平均 0.75、最小 0.74、最大 0.78

| 錯誤代碼 | 次數 | 題數 | 這些題的平均嘗試 |
|---|---:|---:|---:|
| `value_error` | 48 | 32 | 2.62 |
| `variant.v1.budget.over` | 15 | 7 | 3.00 |
| `reference` | 14 | 14 | 2.29 |
| `budget.weak` | 12 | 12 | 2.42 |
| `on_kill.beneficial` | 10 | 9 | 2.11 |
| `variant.v1.skeleton.secondary_count` | 9 | 4 | 3.00 |
| `shield.status` | 8 | 7 | 2.57 |
| `variant.v1.skeleton.core_share` | 6 | 3 | 3.00 |
| `json_invalid` | 4 | 4 | 2.25 |
| `exclusion.self_shape_no_enemy_effect` | 3 | 3 | 2.67 |
| `skeleton.core_share` | 3 | 3 | 2.00 |
| `skeleton.secondary_share` | 3 | 3 | 2.00 |
| `variant.v1.exclusion.no_repeated_control_group` | 3 | 2 | 3.00 |
| `variant.variant_ash.budget.over` | 3 | 1 | 3.00 |
| `exclusion.terrain_needs_earth` | 2 | 2 | 2.50 |
| `variant.lightning_bolt.skeleton.secondary_count` | 2 | 1 | 3.00 |
| `variant.v1.skeleton.secondary` | 2 | 2 | 3.00 |
| `variant.v1.tier.element` | 2 | 2 | 3.00 |
| `variant.v2.skeleton.secondary_count` | 2 | 1 | 3.00 |
| `variant.variant_ash.skeleton.secondary_count` | 2 | 1 | 3.00 |
| `skeleton.core` | 1 | 1 | 3.00 |
| `skeleton.secondary_count` | 1 | 1 | 3.00 |
| `variant.lightning_bolt.skeleton.secondary` | 1 | 1 | 3.00 |
| `variant.shatter.budget.weak` | 1 | 1 | 3.00 |
| `variant.v1.skeleton.shape` | 1 | 1 | 3.00 |
| `variant.v2.skeleton.secondary` | 1 | 1 | 3.00 |
| `variant.v_earth_shatter.budget.weak` | 1 | 1 | 3.00 |
| `variant.v_earth_shatter.skeleton.secondary` | 1 | 1 | 3.00 |
| `variant.v_shock.exclusion.stun_single_long_cooldown` | 1 | 1 | 3.00 |
| `variant.v_shock.skeleton.core_share` | 1 | 1 | 3.00 |
| `variant.variant_1.exclusion.stun_single_long_cooldown` | 1 | 1 | 2.00 |
| `variant.variant_fire.skeleton.secondary` | 1 | 1 | 2.00 |
| `variant.variant_fire.skeleton.secondary_count` | 1 | 1 | 2.00 |
| `variant.variant_shard.budget.over` | 1 | 1 | 2.00 |
| `variant.variant_shard.skeleton.core_share` | 1 | 1 | 2.00 |
| `variant.variant_shard.skeleton.secondary` | 1 | 1 | 2.00 |
| `variant.variant_shard.skeleton.secondary_count` | 1 | 1 | 2.00 |

### 選單與選中率（對照隨機組合器）

平均選中率 3.8%；低於 1.3%（平均的 1/3）或 0 次標 ⚠。

| 原語 | 中文 | 選單次數 | 被選次數 | 選中率 | 被選占比 | 組合器占比 | 標記 |
|---|---|---:|---:|---:|---:|---:|---|
| `apply_status` | 施加狀態 | 300 | 150 | 50.0% | 29.9% | 24.2% |  |
| `damage` | 傷害 | 300 | 239 | 79.7% | 47.6% | 30.8% |  |
| `heal` | 治療 | 300 | 8 | 2.7% | 1.6% | 6.2% |  |
| `shield` | 護盾 | 300 | 20 | 6.7% | 4.0% | 8.3% |  |
| `cleanse` | 淨化 | 278 | 0 | 0.0% | 0.0% | 2.1% | ⚠ |
| `intercept` | 替隊友擋攻擊 | 190 | 4 | 2.1% | 0.8% | 0.9% |  |
| `pull` | 拉扯 | 190 | 0 | 0.0% | 0.0% | 3.2% | ⚠ |
| `push` | 推擊 | 190 | 1 | 0.5% | 0.2% | 3.2% | ⚠ |
| `topple` | 推倒 | 172 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `knock_prone` | 擊倒 | 171 | 7 | 4.1% | 1.4% | 3.2% |  |
| `restore_resource` | 回復資源 | 170 | 0 | 0.0% | 0.0% | 0.6% | ⚠ |
| `create_obstacle` | 產生障礙 | 169 | 0 | 0.0% | 0.0% | 0.8% | ⚠ |
| `add_stack` | 累積層數 | 167 | 3 | 1.8% | 0.6% | 1.7% |  |
| `dispel` | 驅散 | 167 | 0 | 0.0% | 0.0% | 0.9% | ⚠ |
| `steal_buff` | 奪取增益 | 167 | 0 | 0.0% | 0.0% | 0.6% | ⚠ |
| `lower_terrain` | 下陷地形 | 166 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `reveal` | 揭露 | 166 | 0 | 0.0% | 0.0% | 1.1% | ⚠ |
| `consume_status` | 消耗狀態 | 164 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `destroy_object` | 摧毀物件 | 164 | 0 | 0.0% | 0.0% | 0.8% | ⚠ |
| `raise_terrain` | 隆起地形 | 163 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `consume_stack` | 消耗層數 | 162 | 0 | 0.0% | 0.0% | 0.4% | ⚠ |
| `create_surface` | 產生表面 | 162 | 63 | 38.9% | 12.5% | 6.2% |  |
| `blow_surface` | 吹送 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `clear_surface` | 清除表面 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `delayed_damage` | 定時炸彈 | 155 | 0 | 0.0% | 0.0% | 0.8% | ⚠ |
| `detonate_runes` | 引爆符文 | 155 | 1 | 0.6% | 0.2% | 0.0% | ⚠ |
| `gamble` | 賭注 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `grant_skill` | 暫時獲得技能 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `hurl_object` | 投擲物件 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `inscribe` | 刻印 | 155 | 5 | 3.2% | 1.0% | 1.1% |  |
| `revive` | 復活 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `shockwave` | 震波 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `teleport_target` | 傳送他人 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `zone` | 持續區域 | 155 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `charge_through` | 直線衝撞 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `dash` | 衝鋒 | 99 | 0 | 0.0% | 0.0% | 0.2% | ⚠ |
| `leap` | 跳躍 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `place_trap` | 放置陷阱 | 99 | 0 | 0.0% | 0.0% | 1.1% | ⚠ |
| `sacrifice_summon` | 獻祭召喚物 | 99 | 0 | 0.0% | 0.0% | 0.9% | ⚠ |
| `shadowstep` | 瞬步 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `summon` | 召喚 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `swap` | 交換位置 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `swap_any` | 任意兩者互換 | 99 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `teleport` | 傳送 | 99 | 0 | 0.0% | 0.0% | 0.6% | ⚠ |
| `redirect_damage` | 分擔傷害 | 58 | 1 | 1.7% | 0.2% | 0.0% |  |
| `reset_cooldown` | 重置冷卻 | 58 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `extra_reaction` | 額外反應 | 56 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `grant_ap` | 給予 AP | 56 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `cheat_death` | 免死 | 53 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
| `copy_skill` | 複製技能 | 53 | 0 | 0.0% | 0.0% | 0.0% | ⚠ |
