# Phase BS-2 完成報告｜連續背刺與雙牙的前端＋獨狼與 BS-1 條件的正式 Q 版圖示

> 規格：沒有另寫計畫檔。依派工 prompt 與：`docs/phases/PhaseBS-1報告.md`（含第 9 節與開發 PM 裁定）、`PhaseLW-2報告.md`、`PhaseLW-2b報告.md`、`docs/art/LW-2驗收.md`、`docs/art/資訊面板-移植需求.md` 3.7、`docs/art/Q版小圖示-第4批徽章與部件.md` 14.5 與 15.5（開發 PM 中途追加）、`docs/design/06-技能.md` 6.21.1、`docs/design/08-裝備.md` 8.11。
> 基準：開工時 `git merge --ff-only main` 到 `bfb0aa6f`（含 BS-1、LW-2、LW-2b）；中途依開發 PM 指示 `git merge main`（帶進 15.5 移植說明與 BS-1 兩個圖的樣張），沒有衝突。
> 不改引擎規則、沒做平衡量測、沒重產任何雜湊或快照、沒跑 `scripts/check.py`。

## 1. 做了什麼

| 項目 | 做法 | 完成 |
|---|---|---|
| 1. 預覽與戰鬥紀錄顯示「不會轉身」 | `client/src/battle/noTurn.ts`（字、說明卡、`noTurnRows`、`isNoTurnNote`、`stripNoTurnBracket`）。預覽：`previewLines` 照 `no_turn`／`no_turn_reason`／`backstab` 畫「背刺・無聲（不會轉身）：A 盜賊」，伺服器 `notes` 裡同一句濾掉不重複；`ActionPanel` 把那幾列畫成紫色標籤＋說明卡（`NoTurnLine`）。紀錄：`log.ts` 對 `attack_rolled.no_turn` 設 `LogLine.noTurn`、精簡行拿掉行尾「［…（不會轉身）］」；`BattleLog` 精簡行與浮動提示畫 `ui/NoTurnTag.tsx`（紀錄掛說明卡、浮動提示不掛）；完整文字照伺服器。隱蔽＝「隱蔽出手」、無聲＝「無聲」，各自的說明卡字。 | 是 |
| 2. 「要拿匕首類」標灰 | 後端 `src/trpg/api/condition_off.py`：新表 `WEAPON_NEEDS`（`silent_strike` → 引擎 `SILENT_WEAPONS`；`all_strikes_hit` → `AFFINITY_BY_CONDITION` 的雙匕首）＋`OFF_REASON_ZH` 兩筆（「要拿匕首類（匕首或雙匕首），無聲本場不成立」「要拿雙匕首，「兩下都中」本場不成立」）。看 `held_weapon(unit)`（形態中看進入前的武器）。無聲步（每條規則都是無聲、沒有效果）＝整招；影纏給無聲那段、雙牙上毒那段＝部分。前端照 LW-2 機制不必改（見待決 1）。 | 是 |
| 3. LW-2 可修 2：卡片上帶條件的效果數字 | `SkillOffOut.effects`（選用，預設空）＝不會發動的第一段效果在 `skill.effects` 的位置（＝技能卡 `stats.effects[].index`），獨狼與武器條件都給。前端 `ConditionOffMark.effects` → `SkillCardView` 的 `offEffects` → `effectLine(card, off)`；`.skill-eff.cond-off`＝灰紫虛線框＋圖示灰階、字不淡（3.7 第 1 條）。標灰與沒標灰的連打不合併（孤狼撲擊的兩段 ×1 分開）。 | 是 |
| 4. 數值工坊前端 | `TuningScreen` 另讀 `rules`、`budget`，清單多一組「規則與預算（全體共用）」（`FieldForm.tsx` 的 `GROUPS`）；表單照後端 `fields` 產生（背刺命中加成、背刺暴擊範圍、潛行偷襲命中加成；無聲被動價值、主動每回合價值）。AI 表白名單開 `facing.silent_behind`（`content/tuning_fields.yaml`，中文名「無聲留背的加分」、建議 0～10、附說明）；AI 表頂端提示同步。沒改任何數值。 | 是 |
| 5. 獨狼兩條件正式圖（14.5） | `qIcon/parts.ts` 搬 `WOLF: Pt[]`、`loneWolf`、`selfLacks`；`COND.lone_wolf`／`self_lacks_status` 改呼叫，`zh`、`topic` 照樣張；註解與兩個測試檔的「暫代」清掉。 | 是 |
| 追加：BS-1 兩個圖（15.5） | 搬 `BULL_RED`／`BULL_D`／`BULL_W`、`stuckDagger`、`allStrikesHit`（迴圈陣列 `as const`）、`FEATHER: Pt[]`、`feather`、`silentStrike`；`COND.all_strikes_hit`、`CHANGE.silent_strike` 改呼叫，`zh`「每一下都命中」「無聲（目標不轉身）」。「暫代」字樣以內容為準清掉（`parts.ts` 只剩觸發 `TRIG_ALIAS` 的舊暫代，不在範圍）。 | 是 |
| 順手修 | 組裝算式的修正內容 `silent_strike` 沒有中文名，顯示「silent_…」：`skillParts.ts::modifierChangePart` 加一筆「無聲」（組裝列字欄窄，「無聲（目標不轉身）」會被截）。 | 是 |
| 上手筆記 | `上手-前端戰鬥畫面與動畫.md` 第四節 133～138、第五節測試表；`上手-內容資料與模擬.md` 第 31 點（工坊前端已接）。 | 是 |

## 2. 指紋比對（14.4、15 的驗收）

無頭 Chrome `--disable-gpu`（同美術 `qicons_shots.py`），遊戲端用開發頁 `/dev/skillicon-gallery.html` 的 `__qiSkillDev.chip(cat, id, px, 2)`（＝樣張 `qTile`，30／26／18）：

```
condition:lone_wolf | 650bd98d 7cf6c677 35bdf95f
condition:self_lacks_status | 750631be 36150083 7dfe081f
condition:all_strikes_hit | a0a90d63 9e384b71 0c2d0171
change:silent_strike | 2bb45e37 93accfb6 2c2bc85b
```

四行和文件記的**全同**；同一個 Chrome 跑樣張頁 `q-icons-parts.html?part=hash` 也逐行相同。註：第一次沒加 `--disable-gpu` 時遊戲端與樣張彼此相同、但和文件記的全部不同（GPU 點陣化差異），寫進上手筆記第 137 點。

## 3. 測試

新增：
- `tests/api/test_condition_off_bs2.py`（4）：雙匕首不標；匕首只標雙牙上毒（`effects=(1,)`）；單手劍標影纏（部分）、無聲步（整招）、雙牙；帶隊友＋拿劍時獨狼與武器各列在自己的技能上。
- `client/src/battle/bs2SilentStrike.test.ts`（11）：字與說明卡；預覽列不重複、沒有 `no_turn` 時照舊；預覽列 HTML；紀錄 `noTurn`、精簡行拿掉括號、完整文字不動；標籤 HTML 與 CSS；`conditionOffMap` 帶／不帶 `effects`；`effectLine` 的 `off` 與不合併；卡片只多 `cond-off`（其餘逐字同）、CSS、`SkillBar` 兩處傳 `offEffects`；組裝算式「無聲」；工坊清單分組與讀 `rules`／`budget`。

改到的既有測試（舊 → 新）：

| 檔 | 改動 | 理由 |
|---|---|---|
| `tests/api/test_condition_off_lw2.py` | 無人掩護的期望加 `effects=(1, 2)`、孤狼撲擊加 `effects=(1,)` | 新欄位；斷言變嚴 |
| `tests/api/tuning/test_parts_pb1n.py` | `AI_PATHS` 加 `facing.silent_behind` | 白名單多一欄（登記處） |
| `client/src/battle/lw2ConditionOff.test.ts` | 固定資料 `SkillOff` 加 `effects: []` | 重產的型別裡 `effects` 是必填（回應一定帶） |
| `client/src/render/qIcon/qIconSkills.test.ts`、`qIconQi2d.test.ts` | 只改註解（「暫代」拿掉、修正 21 → 22 的說明）；數字 20、22 與 `ADDED_PARTS` 四個 id 不變 | 14.5、15.5 指定 |

沒有放寬斷言；沒有重產雜湊、快照、夾具。`client/openapi.json`、`schema.d.ts` 因 `SkillOffOut.effects` 重產（`scripts/export_openapi.py`、`gen:api`），`tests/api/test_openapi_snapshot.py` 通過。

## 4. 截圖（`docs/art/shots/bs2/`，10 張，最大 194 KB）

伺服器 `trpg serve --port 9163`（正式 build、`TRPG_TUNING=1`、存檔在暫存區）、vite 9164（開發頁）、樣張 `http.server` 9166、無頭 Chrome `--disable-gpu --mute-audio`（9165，DPR 1）、網址帶 `?mute=1`。拍完已用自己的 PID 關掉四個程序，埠都沒在聽。

| 檔 | 內容 | 來源 |
|---|---|---|
| `bs2_cond16_t1x4.png` | 條件 16 真 1 倍（最近鄰 ×4）：目標帶有狀態｜目標落單｜手持武器｜**獨狼**｜**自身沒有狀態**｜**每一下都命中** | 開發頁 |
| `bs2_cond18_t1x4.png` | 同上 18 | 開發頁 |
| `bs2_silent30_x3.png` | 修正內容「無聲」30：真 1 倍與 2 倍並排（×3） | 開發頁 |
| `bs2_cards_lw_1600.png` | 技能卡特寫（詳細展開）：無人掩護（「×0.6」「2 回合・隱蔽」標灰）、孤狼撲擊（第二段 ×1 標灰、條件：獨狼圖）、界隙閃擊（條件：自身沒有狀態圖） | 實機（注入技能） |
| `bs2_cards_bs_1600.png` | 雙牙（「3 回合・中毒」標灰、條件：每一下都命中圖）、無聲步（整招不成立、組裝算式「無聲」圖） | 實機（注入技能） |
| `bs2_battle_sword_1600.jpg` | 單手劍＋帶隊友：孤狼撲擊、影纏、雙牙、無聲步都標灰；雙牙說明卡兩條狀態行＋效果數字標灰 | 實機（注入技能） |
| `bs2_fangcard_800.jpg` | 800×600 雙牙說明卡（詳細展開） | 實機（注入技能） |
| `bs2_preview_silent_1600.jpg` | 匕首＋無聲步普攻預覽：「無聲（不會轉身）：c 盜賊2」標籤列 | 實機（注入技能、地圖換開闊平原） |
| `bs2_log_silent_1600.jpg` | 出手後紀錄浮動提示「冒險者 攻擊 盜賊2 … ［無聲（不會轉身）］」標籤 | 實機 |
| `bs2_tuning_rules_1600.jpg` | 數值工坊：清單「規則與預算（全體共用）（2）」、核心戰鬥規則三欄 | 實機 |

「注入技能」＝包 `window.fetch`，在 `POST /api/battles` 加 `custom_skills`（內容 YAML 原樣轉 JSON）；伺服器真的回 `skills_off`／`no_turn`，畫面沒有假資料。

浮動卡「滑進 → 捲到底 → 釘住 → 關閉」（實機，兩個觸發：雙牙主動鈕、無聲步被動小圖示；詳細展開後量）：

| 尺寸 | 觸發 | 滑進後仍開 | 捲到底 | 釘住（離開仍開） | Esc 關閉 |
|---|---|---|---|---|---|
| 1600×900 | 雙牙 | 是 | 內容 427＝可視 427，不需捲 | 是 | 是 |
| 1600×900 | 無聲步 | 是 | 309＝309 | 是 | 是 |
| 800×600 | 雙牙 | 是 | 427＝427（卡 y 110～536，放得下） | 是 | 是 |
| 800×600 | 無聲步 | 是 | 309＝309 | 是 | 是 |

沒拍：隱蔽出手（`concealed`）的實機預覽與紀錄（要先進隱蔽再近戰出手；字與說明卡由測試保證）；預覽標籤的說明卡打開的樣子；數值工坊的寫回（worktree 分支本來就擋寫回）。

## 5. 檢查與結束碼

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0（14 kept） |
| `uv run trpg content check` | 0（409 招） |
| `uv run pytest -q -n 8 tests/api tests/world/test_lone_wolf_party_lw2.py tests/content/test_no_design_numbers_txt1.py tests/content/test_tuning_fields_nw2a.py`（含 `test_openapi_snapshot.py`、`tests/api/tuning`） | 0（1188 passed、1 skipped） |
| `trpg battle --map open_plain --seed 7 --log-json` ＋ `battle replay` | 0／0（91 動作、383 事件） |
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test --run` | 0（333 檔、4308 項） |
| `corepack pnpm -C client build` | 0 |

## 6. 待 PM 決定

1. **「要拿匕首類」沒有加進 `STICKY_CONDITIONS`，另開 `WEAPON_NEEDS`**：無聲是修正規則（不是條件），「兩下都中」條件本身會隨戰況變，都不能用 `condition_met` 判斷整場不成立；把 `wielding_weapon` 加進 `STICKY_CONDITIONS` 又會把所有武器親和技（例「拿雙手劍時…」）一起標灰，超出範圍。還是「兩張表各一筆」的精神（種類表＋原因表），前端不必改。要不要把其他武器親和條件也標灰，請玩法 PM 定。
2. **原因字是新字**：「要拿匕首類（匕首或雙匕首），無聲本場不成立」「要拿雙匕首，「兩下都中」本場不成立」；說明卡字 `NO_TURN_HINT_ZH` 兩句也是新字（照 06 6.21.1 改寫）。請玩法／美術 PM 看字。
3. **隱蔽的字統一成「隱蔽出手」**：伺服器預覽 `notes` 寫「從隱蔽中出手（不會轉身）」、紀錄寫「［隱蔽出手（不會轉身）］」；前端兩處都畫「隱蔽出手」（伺服器那句濾掉）。若要「從隱蔽中出手」，改 `NO_TURN_ZH` 一處。
4. **「不會轉身」標籤用紫（隱蔽系，同潛行偷襲兜帽）**，隱蔽出手用虛線框、無聲用實線框，實作者暫定，請美術 PM 驗收。浮動提示一行放不下時主字先省略（「…」），標籤保留。
5. **影纏的標灰看不到效果數字**：給無聲的 `grant_skill` 不在技能卡第 3 行（`category: other`），所以只有上方那條「本場不成立」說明。
6. **標灰看手上武器、形態中不看天生武器**：化形時無聲實際不成立，但不標灰（不然變身就閃爍，LW-2 的原則）。
7. **組裝算式的修正內容名取「無聲」**（Q 版圖 `zh` 是「無聲（目標不轉身）」，組裝列字欄窄會被截）。
8. **AI 表 `facing.silent_behind` 建議範圍 0～10**（現值 4 占位，疊在背刺 4 上）；背刺、背對扣分沒開（照 NW-3）。
9. **06 6.21.1「BS-1 後的細節」第 1、2 點（影纏持續 +1、毒＋隱蔽可帶無聲）是規則／內容改動**，不在本段範圍、沒做。

## 7. 新增的複雜度類 noqa

無。

## 8. commit

- `848a0152` feat(client): lone wolf and self-lacks-status condition icons
- `4654e5b0` feat(api): grey silent and twin-fang skills without the needed dagger
- `f0f0e19c` feat(tuning): open facing.silent_behind in the AI table
- `75cd935d` feat(client): show "no turn" (silent / concealed strike) in preview and log
- `f3a59af1` feat(client): grey the condition-off effect numbers on the skill card
- `8d021bd7` Merge branch 'main'（15.5 移植說明）
- `07d0b599` feat(client): all-strikes-hit condition and silent strike change icons
- `b6933bef` feat(client): tuning workshop lists the shared rules and budget tables
- `c9c0200e` test(client): BS-2 no-turn wording, greyed effect numbers, tuning tables
- `20fda9cb` fix(client): Chinese label for the silent strike change in the assembly row
- `fdafb392` docs(bs2): screenshots
- （本報告與上手筆記）docs(bs2): report and onboarding notes
