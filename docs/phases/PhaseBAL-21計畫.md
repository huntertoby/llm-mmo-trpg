# Phase BAL-21 計畫｜頭目與新手戰平衡（延遲段落在選定格、灰燼之心、碎晶之主、霧鎖真人、雨中梯田、1 階技能）

> 開發 PM 的規格助手起草（2026-11-12）；**範圍與定稿以第 0.0 節為準**。
> 實作者先讀 `docs/dev/上手-引擎戰鬥結算.md`（21a）或 `docs/dev/上手-內容資料與模擬.md`（21b 起；第二節「量頭目施放率」「量新手任務」「AI 估值表」與第四節）。
> 平衡目標與數值調整屬玩法決定：本規格只列「現況、建議、技術做法」，數值以玩法 PM 的答覆為準，不在實作中自行定案。

## 0.0 使用者決定與開發 PM 定稿（2026-11-12；優先於本檔其他各節）

使用者原話（專案 PM 轉達）：「1.數值的調整不要再給你做 反而給我一個數值工仿 讓我可在裡面改各種數值 就不用你們慢慢調了　2. 新引擎能力都oK」

- **範圍改為**：
  - **21a 引擎能力（兩項）**：(i) 延遲段落在選定格（第 4 節）；(ii) 「進入新階段回復法力」——`BossPhase` 加選填欄位（例 `mana_restore`），**預設不回復**，沒填就不輸出、規則包雜湊不變；本段不幫任何頭目填值（數值由使用者之後在數值工坊調）。
  - **21b 灰燼之心**：P1 `lava_spout` 換熔岩濺落（內容＋AI 接線），數值用第 2 節 Q1 建議預設；Q2 照建議（`molten_lord` 不換）。**不做** Q3 的 `max_mana` 三檔量測。
  - **21c 碎晶之主**：先只讀查陷阱流（trapper）掉場原因，再加 `skill_rift_flicker`（內容＋AI）；**不做**頭目數值候選試調，掉場原因與建議寫進報告。
  - **21e 1 階技能比值報表**：只讀＋新腳本。
  - **不做 21d**（霧鎖真人、雨中梯田）：數值改由使用者在數值工坊自己調。
- **之後的平衡段一律**：PM 與 agent 不反覆試數值，只出報表與建議，數值由使用者決定。第 2 節各題中屬「目標數值」的部分作廢，不再交玩法 PM 定。
- 第 10 節技術點 T1～T7 **全部照建議**；T7（動畫片段）在派 21b、21c 前問美術 PM。
- 依賴：21a → 21b；21b 與 21c 依序；21e 可平行。
- **T7 美術 PM（第八任）答覆（2026-11-12，不用新樣張）**：
  - 21b 熔岩濺落：施放回合播 `spout`（在 `bossAttackClip` 補一行，不再退到 `firebolt`），自身護盾照現有護盾表現；落下回合頭目不播片段，目標 3×3 用現有火屬性範圍命中特效＋火地表面，預告格沿用現有畫法。截圖：`spout` 中段一張、落下命中＋火地一張（讀不出「落下」美術再出樣張）。
  - 21c 瞬步：補 `blink` 片段接現有 `LordState.blink`，不畫新部件；時間軸照 `docs/art/sample/bosses.html` 第 81 行（約 600 ms，blink 1 → 0 線性）；在目的格播；殘影照現有寫法身後兩層（16 px 間距、透明度 0.35／0.55），東西向隨鏡像、南北向照預設；`swing` 不再當位移的退回片段。截圖：P3 瞬步開頭（殘影最濃）、中段各一張。

## 0. 待排項目與現況（數字都附出處）

| # | 項目 | 現況 | 目標（出處） | 出處 |
|---|---|---|---|---|
| A | 灰燼之心 P1 `lava_spout` 施放率 | **8.5%（51/603）**，BAL-20 改後 8.3%（49/593）；240 場（3 頭目 × 8 build × 10 種子） | 每回合 ≥ 10%（#149 三級標準：< 10% 要處理） | `PhaseBAL-20報告.md` 第 3 節；`玩法決定紀錄.md` #149 |
| A' | 原因 | 延遲段是「身邊一圈」，回合開頭有人貼身只有 21%（124/603）；列入候選的 65 回合有 51 回合會放，不是評分問題 | — | 共用筆記 `調查-灰燼之心lava_spout.md` |
| A'' | 已定做法 | 玩法 PM 2026-11-11 採 B 案新招「熔岩濺落」`skill_lava_splash`（4 格內 3×3、1d6 火＋火地 2 回合），**但要保留提前一輪預告**；同日裁定：要先擴充引擎「延遲招記住施放時選的格子、下一輪在那格落下」，延後到平衡段一起做 | 施放率 ≥ 10%、勝率 70～80%、fire build ≥ 40% 就採用 | `玩法決定紀錄.md` #149「`lava_spout` 裁定」「後續（同日）」 |
| B | 灰燼之心法力見底 | 法力 67、不回復，火焰箭一回合最多 3 發，約第 6～8 輪見底；回合開頭法力 < 6 的比例 P1 18%、P2 52%、P3 58%。`heart_inhale` 15.3%（17/111）→ BAL-20 後 **10.7%（12/112）**；`heart_meltdown` 19%、`heart_exhale` P3 17% | #149：≥ 20% 達標、10～20% 可接受 | `調查-灰燼之心lava_spout.md`；`PhaseBAL-20報告.md` 第 3 節與 PM 裁定 |
| B' | 灰燼之心整體 | 勝率 72%（BAL-20 改後，80 場）、平均 10.8 輪（調查基準） | 勝率 70～80%、**6～10 輪**（19 第 62 行 5F-5a 代決） | 同上；`docs/design/19-灰燼荒原與賽季主線.md` |
| C | 碎晶之主 P3 瞬步 | `skill_blink` **0%**（P3、P4 皆 0；240 場） | #149 每階段 3 招；19.7「本體每回合結束移動到浮台另一側」 | `PhaseBAL-20報告.md` 第 3 節 |
| C' | trapper | CB-2d 37%（11/30）不算通過；P1 換震波後 12/30＝40%（沒有餘裕）；**P3 只要會瞬步，trapper 就掉到 5～6/30**（冷卻 1～3、兩種新招都一樣），其他 build 不變；機制沒查 | 整體 60～70%、10～15 輪、**每個 build ≥ 40%**（19 第 178～180 行；#87 調 Boss 不調 build） | `調查-AI隱蔽分數與碎晶之主兩招.md` 任務 2；`玩法決定紀錄.md` #149 |
| C'' | 已定做法 | 「P3 瞬步招現在不加，併進平衡段和 trapper 一起做；到時**優先用 `skill_rift_flicker`**（先打再閃走，冷卻 3，37%，不擠掉界碎）」 | 同上 | `玩法決定紀錄.md` #149「調查結果與裁定」 |
| D | 霧鎖真人「95%」 | **玩家勝率**（8 build × 10 種子＝80 場，底稿 build＋系統傭兵）：CB-2e 前 91% → 補 `concealed: 2` 後 95%／10.1 輪；BAL-20 前後 95%→95%。trapper 以外 7 個 build 幾乎全勝（trapper 7/10）。第 3 階段太短（頭目平均只行動 1.06 回合） | **70%**（5F-2b 量到 70%／6.4 輪；19 第 62 行「目標與霧鎖真人一致：70～80%、6～10 輪」） | `PhaseCB-2e報告.md` 第 53 行起與待決 3；`玩法PM交接.md` 第 69 行；`候選-霧鎖真人換execute.md`「要到 1 次以上」 |
| E | 雨中梯田「42%」 | 42% 是 **CB-2d 舊流程的主角倒下率**（火焰 33/78、巨劍 41%）。#150 新流程（OB-6b，每格 80 人）：第 3 步路上倒下 **0～8%**，固定戰 **320/320 全勝、平均 2.0～2.5 輪** | 倒下率 ≤ 40%（已達）；玩法 PM 2026-11-12：「雨中梯田固定戰平均 2～2.5 輪，新流程下偏輕」，盜賊 HP −10% 維持；設計 18 第 67 行「保留較簡單」 | `PhaseOB-6b報告.md` 4.3 節與待決 1；`玩法決定紀錄.md` #150「OB-6b 小模擬審核」 |
| F | 1 階技能偏弱（遠程優先） | 對單一木樁、每 AP 傷害 ÷ 普攻：遠程 1 階武器技 45 招**沒有一招直接傷害贏過普攻**（淬毒箭 0.58～0.61、燧石飛刃 0.83～0.86；含持續傷害才 1.29～1.97）；另記：雙匕首上 2 AP 單擊招只有 0.5～0.7 | 沒有定量目標 | `玩法決定紀錄.md` #148（2026-11-11 修訂）；共用筆記 `核對-148示範招B案.md` |

## 1. 已定、不要再問的規則

- 過關判法（玩法 PM，BAL-20 報告末節）：**每組 ≥ 100 場的表與合計判定，不到 100 場只看不判**。
- #149 每回合施放率三級：≥ 20% 達標、10～20% 可接受、< 10% 要處理。施放率＝施放次數 ÷ 頭目在該階段的行動回合數；只認頭目本體；回合中途轉階段且還沒放招歸新階段（`scripts/cb2e_sim.py`）。
- 頭目平衡照 #87 調 Boss、不調 build。
- 雨中梯田：盜賊 HP −10% 維持；「敵方至少 2 名」是已確認的代決，不減人（#149 CB-2a 審核）。
- 舊存檔不必相容（使用者 2026-11-12：「存檔都可以刪除」）：報告照實寫「舊存檔／舊紀錄會受影響」即可，不寫遷移；實際刪存檔檔案不要做。

## 2. 待玩法 PM 確認（附建議；答覆前對應的段不派工）

| # | 問題 | 建議 |
|---|---|---|
| Q1 | 熔岩濺落帶預告版的初值：施放時「選格＋預告」、下一個自己的回合開始在該格 3×3 落下 1d6 火＋火地 2 回合；法力 6、冷卻 2、2 AP；第一段要不要保留 `lava_spout` 的自身護盾 1d4 | 照調查草稿的數值；第一段保留自身護盾 1d4（第一段一定要有效果，護盾也延續「殼」的主題）。施放後到落下之間頭目若被暈眩／冰凍照現有規則取消 |
| Q2 | `molten_lord`（`content/units/molten_lord.yaml`）也用 `lava_spout`：一起換還是保留 | 保留，只換灰燼之心 P1（調查的 A、B、C 案都只改灰燼之心） |
| Q3 | 灰燼之心法力見底的目標與手段：目標是「P2、P3 每招 ≥ 10%」還是 ≥ 20%；手段選 (a) 純內容：`ashen_heart.yaml` 加 `max_mana`（現由屬性推算 67）；(b) 引擎：頭目階段加「進階段回復法力」欄位（`BossPhase` 目前沒有，`src/trpg/content/battle.py:1544`）；(c) 火焰箭改冷卻／調費用 | (a) 先量：上限 67 → 90／110／130 三檔，看 P2、P3 各招與勝率、輪數。(b) 要動引擎，留給 (a) 達不到時。注意勝率與輪數同時會往「更難、更短」走，現況 10.8 輪已超過 6～10 輪上限 |
| Q4 | 碎晶之主 P3：照已定的 `skill_rift_flicker`（冷卻 3）加入；trapper 掉場要用什麼補（#87 調 Boss） | 21c 第一步先只讀查 trapper 掉場的機制（陷阱被閃走浪費？），再提 2～3 個只動 Boss 的候選（例：P3 本體傷害倍率、界碎冷卻、`rift_flicker` 落點限制），由玩法 PM 選 |
| Q5 | 碎晶之主「每個 build ≥ 40%」的判法：照 ≥ 100 場的規則，每個 build 要 100 場（8 build × 100 種子＝800 場／方案） | 同意 800 場／方案（BAL-20 的 240 場頭目量測程序池 6 約 1～1.3 分鐘，800 場估 4～5 分鐘）；只量碎晶之主（`--only rift`） |
| Q6 | 霧鎖真人目標：70% 還是 70～80%；手段 | 目標照 19 第 62 行「70～80%、6～10 輪」。先做二維小表：真人 HP 120 → 140／160 × 歸一門檻 30% → 40%（調查：門檻 40% 配收霧斬 92%／9.9 輪）。不動 `concealed: 2`（已定） |
| Q7 | 雨中梯田「偏輕」的目標：固定戰的平均輪數、我方倒下率要到多少；能動哪些（盜賊 HP −10% 與「不減人」已定） | 建議目標「固定戰平均 3～4 輪、第 3 步路上倒下率仍 ≤ 40%」。候選只動 `terrace_clash` 的修士方（設計是「盜賊＋修士衝突」）：修士 HP／傷害或多 1 名修士。若玩法 PM 認為「保留較簡單」（18 第 67 行）已經涵蓋，就不調、結案 |
| Q8 | 1 階技能的目標與範圍：遠程先做；目標比值（每 AP 直接傷害 ÷ 普攻）多少；用 `skill_scaling.yaml` 全域倍率還是逐招改 | 本次只做報表（21e）：全部 1 階武器技 × 每把武器的比值表，遠程排前面；目標比值與調法等報表出來再定。建議討論起點「無條件的單體招 ≥ 0.9、帶條件且條件成立時 ≥ 1.1」 |

## 3. 切段

| 段 | 內容 | 前置 | 可否平行 |
|---|---|---|---|
| **BAL-21a** | 引擎能力：延遲段落在施放時選定的格子＋測試（不改任何現有內容） | 無（技術點 T1～T4 由開發 PM 定） | 可與 21c 第一步、21e 平行 |
| **BAL-21b** | 灰燼之心：熔岩濺落（帶預告）取代 P1 `lava_spout`＋法力見底 | 21a 合併；Q1～Q3 | 不可與 21c 同時（都會加技能、改同一批登記處與 CLI 快照） |
| **BAL-21c** | 碎晶之主：P3 `skill_rift_flicker`＋trapper 補償 | Q4、Q5（第一步只讀調查不需要） | 不可與 21b 同時 |
| **BAL-21d** | 霧鎖真人勝率＋雨中梯田固定戰 | Q6、Q7 | 可與 21a、21e 平行（只動雲嶺單位與遭遇）；與 21b／21c 都會動 CLI 快照時要錯開合併 |
| **BAL-21e** | 1 階技能比值報表（只讀＋新腳本，不改內容） | 無 | 可與任何段平行 |

同時進行的 agent 最多 3 個（開發名額）；21b 與 21c 依序。

## 4. BAL-21a｜引擎：延遲段落在選定格

### 4.1 現在怎麼決定落點（查證，main `b3b96fa6`）

- 延遲段只能以施放者**當下**的位置為中心：`src/trpg/engine/delayed.py:81-95` `delayed_selection` 把 `target_pos` 設成 `caster.xy`（第 88-89 行）。蓄力時（`charge`，第 102-125 行）、釋放時（`_release`，第 177-185 行）、預告（`charge_infos`，第 228-249 行）都呼叫它，所以施放者移動時範圍跟著移動。
- 蓄力狀態 `StatusInstance`（`src/trpg/engine/state.py:66-93`）只有 `skill_id`、`direction`（定向蓄力用），沒有存格子。
- 內容檢查：`src/trpg/content/skills/followup.py:113-122` `_check_delayed` 要求第二段形狀在 `DELAYED_SHAPES`（`src/trpg/content/skills/constants.py:611`：`cross`、`square3`、`ring`），`_second_shape`（第 46-54 行）要求以原點為中心的形狀 `range: 0`。`FollowupSpec` 在 `src/trpg/content/skills/specs.py:64-83`。
- 第二段結算：`src/trpg/engine/skills/interpreter.py:259-281` `run_delayed`，`SkillFollowup.origin` 寫死施放者位置（第 273 行附近）；施放時從 `_resolve_cast`（第 160-161 行）呼叫 `charge`。
- 事件：`FollowupCharged`（`src/trpg/engine/events/skills.py:55-68`）的 `pos`／`tiles` 是以施放者位置推算的預計範圍。
- AI：`src/trpg/engine/ai/composite.py:61-63` 的便宜估計與 `src/trpg/engine/ai/utility/scoring.py:317-337` `_delayed_points` 都看 `delayed_selection`／`FollowupCharged.tiles`——這就是「身邊一圈沒人就不列入候選」的來源。
- 其他讀預告的地方：`src/trpg/engine/view.py:643`（狀態上的 `charge_tiles`）、`src/trpg/engine/environment.py:430`（`telegraph.charges`）、`src/trpg/engine/preview.py:872`、`:1150`。前端只畫後端給的格子（`client/src/battle/followup.ts:75-80`），但說明文字寫死「以自己為中心」（`followup.ts:65`）。
- 現有 11 招延遲段：`charged_cleave`、`heart_meltdown`、`lava_spout`、`magma_breach`、`mist_lock_peaks`、`nine_turns_revival`、`parry_riposte`、`rift_pulse_fire／mist／thunder`、`rift_shatter`（界碎設計是「提前一輪標出 2 排直線」，現在也是以自己為中心近似，這個能力日後可沿用，本段不改它）。

### 4.2 建議做法（技術點 T1～T4 由開發 PM 定）

1. **內容**：`FollowupSpec` 加選填欄位 `anchor`（建議值只有 `cast_tile`；`None`＝照舊以施放者為中心）。`anchor: cast_tile` 時：
   - 只允許 `when: delayed`；技能本身（第一段）的形狀要是 `tile` 型（例 `ground_tile`、`square3` 帶 `range`），選的格子就是落點；第二段仍在 `DELAYED_SHAPES` 內、`range: 0`。
   - 新增檢查與錯誤訊息（`followup.py::_check_delayed`），並在 `skill.py` 的結構檢查擋住其他 `when` 帶 `anchor`。
   - 序列化：比照 IP-1 的 `icon_prop`，`None` 不輸出（`exclude_if=lambda v: v is None`），讓沒填的 11 招規則包序列化不變。
2. **狀態**：`StatusInstance` 加 `anchor: Pos | None = None`（或 `XY`；只有 `charging` 用），同步 `clone()` 與序列化（`docs/dev/上手-引擎戰鬥結算.md` 第三節第 4 點）。`charge` 在 `anchor: cast_tile` 時把 `action.target_pos` 存進去（`charge` 要多收 `action`，呼叫點 `interpreter.py:161`）。
3. **選取**：`delayed_selection` 看到狀態有 `anchor` 時，以 `anchor` 為原點算範圍：沿用 `targeting.py:1216` `_at`（假設施放者站在原點的複本）的做法，**釋放時不重驗射程與視線**（施放時已驗），只驗地圖範圍與技能條件。`charge`、`_release`、`charge_infos` 都改傳狀態（或 anchor）。蓄力當下還沒有狀態時（`charge` 內），用 `action.target_pos`。
4. **結算**：`run_delayed` 的 `SkillFollowup.origin` 用實際原點（anchor 或施放者位置）。命中、抵抗等仍以真正的施放者計（只有範圍用 anchor）。
5. **事件**：`FollowupCharged.pos` 改為原點（anchor 或施放者位置），`tiles` 不再隨施放者移動；建議另加 `anchored: bool = False`，讓前端分辨「固定在地上」與「跟著施放者」。
6. **AI**：`composite_estimate`（`composite.py:61`）與 `_delayed_points` 對 `anchor` 招改用該動作的 `target_pos` 推算範圍；`legal_actions` 的候選由第一段的 `tile` 型形狀照常列舉（`targeting.py:1163-1185` `selections` → `_candidates`），不必新增列舉。
7. **前端**：`followup.ts:65` 的說明文字依 `anchored` 改成「落在指定位置」；`gen:api` 重產型別。不新增畫面元件；預告格的畫法沿用。動畫片段（灰燼之心打遠處格會歸成施法播 `firebolt`，要播殼頂熔岩柱 `spout` 得在片段對應補一行，`client/src/render/qBoss.ts`）**不在 21a**，留到 21b 先問美術 PM。

### 4.3 確定性與重播

- 不新增亂數取用；`anchor` 是施放時的選取，存在狀態裡，「初始狀態＋動作列表」仍可完整重播。
- `BattleState` 的欄位（`StatusInstance.anchor`）與事件欄位改變 → **`LOG_FORMAT` 113 → 114**（`docs/phases/戰鬥紀錄格式變更.md` 第 1 節；更新寫死版號的測試，Grep `trpg-battle-log/`）。舊戰鬥紀錄與戰鬥中存檔讀不了，已接受（舊存檔不必相容）。
- **證明現有內容不變**：改動前後各跑 8 張地圖 × 2 個種子（含灰燼之心、碎晶之主、霧鎖真人三張頭目圖，因為 11 招延遲段多在頭目身上），比對事件 JSON、步驟、輪數、勝方、最終 `rng_state`，`different=0` 寫進報告（PR-1 的做法；比對時忽略 `LOG_FORMAT` 字串與 `FollowupCharged` 新增的預設欄位）。`hash_ruleset` 對現有內容應不變（`anchor` 沒填不輸出），報告附前後值。

### 4.4 交付與驗收

1. 內容 schema、狀態、選取、結算、事件、AI、前端文字的改動（一個或數個 commit）。
2. **行為一致測試**（實際跑引擎，新檔 `tests/engine/test_delayed_anchor_bal21.py`）：用測試專用技能（放 `tests/` 夾具或測試內建構，不加進 `content/skills/`）：
   - 施放時選格 → `FollowupCharged.tiles` 是該格的 3×3、`pos` 是該格；
   - 施放者移動（或被推開）後，`charge_infos` 與釋放範圍仍在原格；
   - 下一個自己的回合開始在原格結算傷害與表面，施放者身上 `charging` 移除；
   - 暈眩、倒下、被取代時照舊取消；
   - 選格超出第一段射程時 `IllegalActionError`；
   - 沒填 `anchor` 的現有延遲段（例 `lava_spout`）範圍仍跟著施放者；
   - AI：一個貼身沒人、但 4 格內有 2 名敵人的場面，`anchor` 招的候選分數 > 0（對照：同數值不帶 anchor 的招 = 不列入）；
   - `clone()` 與 JSON 往返保留 `anchor`（`tests/engine/test_state_clone.py` 會擋漏）。
3. 內容檢查測試：`anchor` 用在非延遲段、第一段不是 `tile` 型時載入失敗（`tests/content/test_skills_content.py` 或新檔）。
4. 驗收：`ruff check`、`ruff format --check`、`mypy`、`lint-imports` 結束碼 0；相關測試檔（`tests/engine/test_delayed*.py`、`test_state_clone.py`、`test_boss_phases.py`、`tests/content/test_skills_content.py`、`tests/test_architecture.py`、`tests/api` 中 telegraph／charges 相關檔、前端 `client/src/battle/followup.test.ts`、`charges.test.ts`、`telegraph.test.ts`）過；一場 `trpg battle --log-json` ＋ `replay`「重播驗證通過」；4.3 的 `different=0`。
5. 合併前跑相關 slow：`tests/cli/test_output_snapshots.py -m slow`（`LOG_FORMAT` 字串可能出現在快照，**只重產受影響的鍵**，逐鍵說明）、`tests/skillgen/` 含 slow（`SkillDef`／`FollowupSpec` schema 變了：`test_refactor_parity.py` 的雜湊必須不變——`anchor` 沒填不輸出；**不得重產 parity 夾具**，對不上就停下回報）、`tests/narrative/`。
6. 報告 `docs/phases/PhaseBAL-21a報告.md`；順手更新 `docs/dev/上手-引擎戰鬥結算.md`（延遲段一條）與 `docs/phases/戰鬥紀錄格式變更.md`。

## 5. BAL-21b｜灰燼之心（Q1～Q3 答覆後）

1. 新增 `content/skills/skill_lava_splash.yaml`（`enemy_only`，`followup.when: delayed`、`anchor: cast_tile`，數值照 Q1）；草稿在 `C:\Users\tobby\AppData\Local\Temp\claude\9f1b79de9b6f77a5\a9ed9ff7-f0fd-4dbe-868c-139ab4e352c7\scratchpad\cb2h\drafts\skill_lava_splash.yaml`（無預告版，要改寫成兩段）。`uv run trpg skills budget` 落在 70～100%。
2. `content/units/ashen_heart.yaml` 第 20 行 P1 `skills` 把 `skill_lava_spout` 換成新招；`molten_lord` 依 Q2。
3. 法力見底依 Q3 的手段與檔位（數值以腳本跑出摘要表，不手試）。
4. 加一招的四個登記處：技能圖示快照（`uv run python -m tests.narrative.icon_fixture`）、`tests/skillgen/test_enemy_only.py` 名單、`tests/content/test_skill_scaling.py` 招數、CLI 快照的 `skills_list`／`skills_show_all` 鍵（只重產這兩個）。
5. 動畫：派工前開發 PM 先問美術 PM 熔岩濺落要播 `spout` 還是 `firebolt`；要改就在 `qBoss.ts` 片段對應補一行，交件附截圖。
6. **量測**（同種子配對，現況 vs 改後；程序池 ≤ 6）：
   - 灰燼之心每招每回合施放率：`cb2e_sim.py bosses --only ashen`，**8 build × 13 種子＝104 場以上**（判法用合計）；
   - 勝率、平均輪數（目標 70～80%、6～10 輪），fire build 單獨 ≥ 40%：fire 要判就要 ≥ 100 場（`--builds fire --seeds 100`；若腳本沒有 `--builds` 就在腳本加，並補一次小規模實跑）；
   - 三個頭目其他招沒有因此跌破 10%（只有灰燼之心內容變，另兩個應逐項相同，附一行確認）。
7. 過關（已定）：`lava_splash` ≥ 10%、勝率 70～80%、fire ≥ 40%；法力的部分照 Q3 的目標。不過就照實寫報告、不合併，回玩法 PM。

## 6. BAL-21c｜碎晶之主（Q4、Q5 答覆後；第 1 步可先做）

1. **只讀調查**（不改 repo）：P3 會瞬步時 trapper 掉場的機制（陷阱放置與觸發、被閃走的次數、輪數），結論與 2～3 個只動 Boss 的候選寫進共用筆記或報告草稿，交玩法 PM 選。
2. 實作：新增 `content/skills/skill_rift_flicker.yaml`（草稿在同一 scratchpad 的 `cb2g\drafts\skill_rift_flicker.yaml`；冷卻 3）；`content/units/rift_shard_lord.yaml` 第 38 行 P3 `skills` 的 `skill_blink` 換成它（P4 同列表是否一併換，依 Q4 一起問）；加上 Q4 選定的補償。四個登記處同 21b 第 4 點。
3. 動畫：位移類會退回 `swing`（揮擊刀光），殘影 `LordState.blink` 已在 `qBoss.ts` 但沒有片段用到——派工前問美術 PM，補一個 blink 片段接上（不畫新部件）。
4. **量測**：`cb2e_sim.py bosses --only rift`，8 build × 100 種子＝800 場／方案（Q5），同種子配對；表列 P3、P4 每招施放率、整體勝率與輪數、每個 build 勝率。
5. 過關：`rift_flicker` ≥ 10%（建議看 ≥ 20%）、整體 60～70%、10～15 輪、每個 build ≥ 40%（各 100 場）。

## 7. BAL-21d｜霧鎖真人與雨中梯田（Q6、Q7 答覆後）

1. 霧鎖真人：依 Q6 的檔位寫一個掃描腳本（例 `scripts/bal21_sweep.py`：在記憶體換內容、`cb2e_sim.py` 的建角與歸屬規則、每格 8 build × 13 種子），輸出「勝率／輪數／各招施放率」摘要表；建議值寫報告由玩法 PM 定，定了才改 `content/units/sect_mist_lock_master.yaml`。改後各招仍不得跌破 10%。
2. 雨中梯田：Q7 若要調，用 `scripts/ob6_newbie_sim.py`（第 3 步每格 80 人、4 格合計 320 人）加候選（`CANDIDATES` 結構），只換 `terrace_clash` 的對象；表列固定戰勝率、平均輪數、第 3 步路上倒下率。若 Q7 定為不調，本項結案、只在報告記錄。
3. 判法：霧鎖真人每格 104 場、合計判；梯田每格 80 人只看不判，4 格合計 320 人判（照 ≥ 100 場規則）。

## 8. BAL-21e｜1 階技能比值報表（只讀＋新腳本）

1. 新腳本 `scripts/t1_skill_ratio.py`：照 `核對-148示範招B案.md` 的量法（靶場 `training_range`、`range_trial` 配點、普通木樁、每把武器 250 個種子含失手），對全部 1 階、非 `enemy_only` 的武器技，輸出「每 AP 直接傷害 ÷ 普攻每 AP」與「含持續傷害」兩欄，依大類（遠程、近戰、法器）× 武器分組；條件類（背後、第 1 輪、油面）另標成立／不成立兩種。先用 #148 記過的 4 招對數字（瞬步背刺 1.26～1.34、淬毒箭 0.58～0.61…），對得上才跑全表。
2. 子命令分「跑」與「重印」，結果存 JSON（暫存區，不進 repo），報告只貼摘要表（遠程在前）與「低於 0.9 的招清單」。
3. 不改任何內容；調整等 Q8 定了另開段。

## 9. 共通規矩（每段派工 prompt 都要寫）

- 數值調整不要反覆手試：寫腳本輸出摘要表，建議值寫報告由玩法 PM 定。
- 大型模擬（`trpg sim completion`、不限縮的 `matrix`、`balance_baseline.py`）不跑；量測只在最後各跑一次完整版，前面只做冒煙（1～2 個種子）；PM 跑全量 `check.py` 期間不跑模擬。
- **快照／雜湊不得整批重產**：每一項先證明變動來自本段（拿掉該改動回到舊值），對不上的不更新、先回報；CLI 快照用 `-k` 只重產受影響的鍵。
- 每段合併前跑相關 slow：動 AI 估值或戰鬥結算 → `tests/cli/test_output_snapshots.py -m slow`；動技能內容或 schema → `tests/skillgen/`（含 slow）、`tests/narrative/`；動 AI 軌跡導致的固定種子測試，照 BAL-20 第 5 節的做法換種子、斷言不放寬，逐項列出。
- 舊存檔不必相容，報告照實寫影響；不刪存檔檔案。
- Windows：`uv run python`；新 worktree 先 `uv sync --frozen`，之後 `UV_NO_SYNC=1`；pytest 平行最多 `-n 8`；不跑完整 `scripts/check.py`。
- 不開伺服器（21a、21b、21c 的前端截圖除外，埠避開 8000／8001，用自己記下的 PID 關）；不結束不是自己啟動的程序；等待用完成通知，不寫 until／while 輪詢。
- 子 agent 一律 Opus 5.5（`model: "opus"`），往下傳同樣規矩。不要 push；commit 結尾帶 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- 報告「待 PM 決定」最多 10 點；改到的區域順手更新上手筆記。

## 10. 待開發 PM 確認的技術點（附建議）

| # | 技術點 | 建議 |
|---|---|---|
| T1 | 新欄位放哪、叫什麼：`FollowupSpec.anchor`（`cast_tile`）vs 讓 `UseSkill.followup_target.target_pos` 也能用在延遲段 | `FollowupSpec.anchor`＋第一段 `tile` 型形狀：選取沿用現有列舉，不必像 `_composite_selections` 做兩段相乘；`followup_target` 那條要改驗證與 AI 列舉，面積大 |
| T2 | 釋放時要不要重驗射程、視線、格子是否可站 | 不重驗射程與視線（施放時已驗、玩家看得到預告）；只驗格子在地圖內與技能條件；有單位站上去照常吃傷害 |
| T3 | `LOG_FORMAT` 113 → 114 | 要加（`BattleState` 欄位與事件欄位變了）；`FollowupCharged` 加 `anchored`，`pos` 改為實際原點 |
| T4 | `hash_ruleset` 與 parity 雜湊 | `anchor` 沒填不輸出，現有 402 招序列化不變；21a 合併前用 slow 的 `test_refactor_parity.py` 證明 |
| T5 | 21b、21c 依序 | 兩段都加一招、改同一批登記處與 CLI 快照；21d、21e 可平行 |
| T6 | 量測腳本留不留 | BAL-20 的 `wr_sim.py`、`bite_sim.py` 已刪；建議 21b 起把「指定 build、指定種子數、只跑某頭目」補進 `scripts/cb2e_sim.py`（`--builds`），21d 的掃描腳本與 21e 的比值腳本留在 `scripts/`，結案再決定搬 `scripts/archive/` |
| T7 | 動畫 | 21b（熔岩濺落播哪個片段）、21c（blink 片段）派工前先問美術 PM；交件要截圖（`docs/開發PM交接.md` 6.5.2） |
