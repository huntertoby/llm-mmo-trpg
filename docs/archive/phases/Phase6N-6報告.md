# Phase 6N-6 報告：動畫第二批⑥　近戰攻擊變體（＋6N-5 驗收的兩項回饋）

實作者，2026-11-04。

規格依據：
- `docs/phases/Phase6計畫.md` 6N-6 列；
- `docs/art/動畫移植需求第二批.md` 第 0 節（共同原則，尤其第 3、5、6 點）、第 6 節；
- `docs/art/動畫方案.md` 2.10 第 5 點的變體數表，以及樣張 `sample/anim.js`／`anim.html` 第 6 區。
- 追加（開發 PM 轉美術 PM 6N-5 驗收回饋）：目標不能動時沒打中寫「失手」、不播閃避；「暴擊 −N」縮小。

開工時 worktree 落後 main，先 `git merge --ff-only 6910a359`；追加兩項前再 merge 一次 main（b3fb56a2，只多了 docs）。只改了 `client/`，另外加了截圖和這份報告。沒有改數值、規則、Python 引擎或 API；沒有新增相依；沒有新增伺服器欄位。

## 交付

| 項目 | 檔案 |
|---|---|
| 變體表、片段、弧光、挑法（純函式） | `client/src/render/attackVariants.ts`（新）：`ATTACK_FAMILIES`、`VARIANT_COUNT`、`ATTACK_VARIANTS`、`VARIANT_CLIPS`、`attackFamilyOf`、`ArcSpec`／`arcStrokes`／`arcTravel`／`arcMirror`、`battleVariantKey`／`exploreVariantKey`、`pickVariant`／`variantIndex` |
| 片段查表 | `client/src/render/skillClips.ts`：`ClipId` 加上變體片段，`clipDef` 也查 `VARIANT_CLIPS` |
| 串接器 | `client/src/battle/skillSequence.ts`：`SkillSegment.variant`（`VariantPick`）、`AttackOf`、`variantFor`；段落記開段事件的 `seq`；近身普攻的蓄力、出招換成變體的片段；挑到的弧光寫進 `VfxCast.arc` |
| 型別 | `client/src/battle/vfx.ts`：`VfxCast.arc?` |
| 弧光 | `client/src/render/vfxEffects.ts`：`variantSlash`（由下往上、橫掃、突刺、交叉、迴旋；朝西左右鏡像；暴擊同樣加粗、金色） |
| 繪製器、播放 | `client/src/render/BattleRenderer.ts`：`attackFamilyOf(unitId)`；`battle/playback.ts`、`screens/battle/usePlayback.ts`：把 `attackOf` 傳進串接器 |
| 追加①：不能動時「失手」 | `client/src/battle/feedback.ts`：`IMMOBILE_STATUSES`、`immobileIn`、`WORD_MISS`；`battle/vfx.ts`：`reactOf` 不能動的人沒被打中不產生 `dodge` 反應（6N-5 的閃避強化跟著沒有） |
| 追加②：「暴擊 −N」縮小 | `client/src/render/uiAnim.ts`：`FLOAT_FONT`、`BIG_RATIO`、`BIG_MAX_CELLS`、`BIG_REST`、`floatFontSize`、`floatFit`；`BattleRenderer.makeEffect` 照它算字級與再縮的倍率 |
| dev 頁 | `client/src/dev/skillGallery.ts`：`skill-gallery.html#variants` |
| 測試 | `render/attackVariants.test.ts`（新，26）、`battle/missImmobile.test.ts`（新，9）、`battle/skillSequence.test.ts`（改 1） |

## 1. 變體表（方案 2.10 第 5 點）

| 列（`AttackFamily`） | 武器（紙娃娃主手） | 數量 | 變體（第一個 ＝ 6N-6 以前的普攻） |
|---|---|---|---|
| 劍 `sword` | 劍（非彎刀、非魔導）、匕首（非彎匕） | 5 | 由上往下、由下往上、橫掃、突刺、小跳斬 |
| 刀 `saber` | 彎刀（劍 `curved`）、彎匕（匕首 `kris`） | 5 | 由上往下、由下往上、橫掃、拔刀斬、迴身斬 |
| 魔導劍 `arcane` | 劍 `arcane` | 4 | 由上往下、橫掃、突刺、劍上符文一亮再斬 |
| 斧錘雙手 `heavy` | 斧、錘、大劍（含斬馬刀） | 3 | 劈、橫掃、掄一圈 |
| 成對 `pair` | 主副手同種的劍、匕首 | 4 | 交叉斬、連刺、迴旋、反手刺 |
| 槍 `spear` | 矛 | 4 | 直刺、下段刺、橫掃、跳刺 |
| 鐮 `scythe` | 鐮 | 3 | 橫掃、上挑、迴旋 |
| 鞭 `whip` | 鞭 | 3 | 上甩、側甩、纏繞拉扯 |

- **變體只改關節角度和弧光**：同一列的蓄力片段一樣長、出招片段一樣長、`hitAt` 一樣（劍刀魔導斧錘 220 ms／0.62、成對 280／0.45、槍 200／0.7、鐮 240／0.6、鞭 240／0.7；蓄力照各列原本的 260／280／220／240）。所以串接器排出來的時間軸完全相同，命中點、傷害數字、受擊、特效、6N-5 的停頓都不動（測試：60 個不同 seq 的命中點、特效命中、結束時間各只有一個值）。
- 每個蓄力片段的最後一格 ＝ 出招的第一格（測試鎖住，不會跳一下）。
- **只有近身普攻挑變體**：技能（6N-8 做技能變體）、遠程普攻、沒有變體表的武器（弓、弩、火槍、法杖、法球、拳套、空手；6N-7）照起手對照表。
- **異形**：沒有骨架的單位 `attackFamilyOf` 回傳 `null`，出招照舊播 `creaturePose` 的通用「撲」；形態、召喚物同（測試鎖住 `null` 時是原本的 `slash`、沒有 `arc`）。
- **走路、跑步不做變體**（沒動）。
- **6N-7 怎麼接**：在 `AttackFamily`／`ATTACK_FAMILIES`／`VARIANT_COUNT`／`ATTACK_VARIANTS` 加列、在 `VARIANT_CLIPS` 加片段、在 `attackFamilyOf` 加對照，串接器與弧光不用改。遠程的「弧光」可改成飛行物軌跡，`ArcSpec` 是聯集型別，可加一種。受擊、閃避的變體在 `reactClips.ts`，挑法可直接用 `variantIndex` 的同一套鍵。

## 2. 挑法（第 0 節第 3 點）

- 鍵：`戰鬥鍵:事件 seq:施放者 ID:attack_<列>`（例：`bamboo_grove:12:u_hero:attack_sword`）。戰鬥鍵沿用 6N-4 起的 `view.map_id`；`seq` 是開這一段的 `attack_rolled` 的 `seq`。
- `inkStyle.seedOf`（FNV-1a）÷ 變體數取餘數。同一個鍵永遠同一個變體，重播、觀戰、重新整理都一樣（測試：同鍵兩次、`structuredClone` 過的事件重排一次，時間軸與特效完全相同）。
- 探索中的鍵 `exploreVariantKey(地圖 ID, 單位 ID, 動作序號)` 已備好，但目前探索沒有攻擊動畫，沒有呼叫端（見待決 3）。
- 不用 `Math.random()`、不讀時鐘。

## 3. 弧光

- `ArcSpec`：`arc`（從 `from` 掃 `sweep`，`squash` 壓扁＝橫掃）、`line`（突刺）、`cross`（交叉斬兩道，先後各一半時間）、`ring`（迴旋一圈）。本地座標朝東、y 往下；往西打（水平分量為主）左右鏡像；往南、往北打照朝東畫（上下不變）。
- 沒有 `arc`（技能、舊呼叫端）時照 6N-5 以前的弧（由上往下），一筆都沒改。
- 暴擊：每一種形狀都用 6N-5 的金色（`CRIT_GOLD`）＋加粗。
- 測試「弧光方向和揮的方向一致」：每個變體用 `anchorPoint` 算武器作用端從出招第一格到 `hitAt` 的位移，和弧光頭尾的方向比：由上往下＝兩者都往下；由下往上＝都往上；橫掃＝都往前、弧光扁；突刺＝都往前、弧光是直線；迴旋＝弧光是一圈、武器到命中前轉過至少 π。

## 4. 追加①：目標不能動時沒打中

- 不能動 ＝ 畫面資料（這一步的 `view`）裡目標身上有 `frozen`、`stun`、`prone`、`root`（`statuses.yaml` 的 ID）。
- 這時：不產生閃避反應（不播閃避片段、6N-5 的閃避殘影強化也跟著沒有），地圖浮動字寫「失手」；其他人沒打中照舊「閃避」。
- 戰鬥紀錄的文字來自伺服器的事件 `text`，前端沒改（測試鎖住紀錄仍是「失手」、沒有「閃避」）。

## 5. 追加②：「暴擊 −N」縮小

- 放大字停住時 ＝ 一般傷害字（20）的 **1.3 倍**：字級 `20 × 1.3 ÷ 1.15`（1.15 是 6N-10 彈完停住的倍率，沒改），停住時 26。
- 整串字寬（停住時）不超過**格寬的 1.8 倍**，超過就整串再縮（`floatFit`）。背刺、伏擊、撞擊這類同樣是放大字，一起套用。
- 52px 格截圖：`6n6_crit_float_52px.png`（「暴擊 −18」約 1.77 格寬）。

## 6. 測試結果

- `tsc --noEmit` 通過；`corepack pnpm -C client build` 成功（只有原本就有的 chunk 大小提示）。
- client 全部 vitest：**209 個檔案、2260 項全部通過**（交件前跑一次）。
- 新增 35 項、改 1 項：
  - **變體數照表**（8 列與方案的數字逐一比）、ID 不重複、每個片段都在、所有變體片段都有用到；
  - **同一列的蓄力、出招一樣長、`hitAt` 一樣**；第一個變體和起手對照表原本的長度一樣；蓄力尾＝出招頭；
  - **連續 8 次普攻至少 3 種**：dev 頁（`skill_gallery`、seq 1～8，兩個施放者）與樣張第 6 區（`battle_7f3a`、`unit_0001`）的鍵，8 列全部 ≥ 3；另外 6 張地圖 × 6 個單位 × 2 個起點的統計：每列 ≥ 80% 的 8 連擊有 3 種以上、每個變體都出現過（見待決 1）；
  - **同一個鍵一定挑到同一個**；
  - **弧光方向和揮的方向一致**（8 列各一項，見第 3 節）；朝西鏡像只換左右；
  - **所有變體命中點相同**（串接器實排）；只有近身普攻挑變體（技能、遠程、異形不挑）；暴擊旗標在每個變體上都保留；
  - 追加①：四種不能動狀態各一項（「失手」、沒有閃避反應、沒有閃避強化）、能動時照舊「閃避」、戰鬥紀錄不變；
  - 追加②：放大字停住 ＝ 1.3 倍、整串 ≤ 1.8 格、短字不縮。
- 改的 1 項：`skillSequence.test.ts` 的「basic melee」現在比對挑到的變體片段，`attackOf` 回傳 `null` 時仍是原本的 `windup → slash`。

## 7. noqa

沒有新增 eslint／ruff 例外。

## 8. dev 頁

`client/skill-gallery.html#variants`：
- 上面 8 排 ＝ 8 列，每格固定一個變體（照正式雜湊找出會挑到那一個的 seq，再走正式的 `vfxFor → skillTimeline → playSkill／playVfx`），格上寫名稱；
- 最後兩排每種武器一人，連續 8 次普攻（seq 1～8），格上寫「第 n 次：變體名」；頁面下方列出每種武器 8 次挑到的全部結果；
- `?anim=0.1` 慢動作、`?cell=88` 放大、`?dir=west` 朝西、`?crit=1` 全部暴擊（閃白只給第一個，不然四十幾個同時閃會整片白）、`?freeze=毫秒` 停格、`?floatAt=毫秒` 浮動字出現後停格。

## 9. 截圖（`docs/art/`）

| 檔案 | 內容 |
|---|---|
| `6n6_gallery_variants.jpg` | dev 頁 `#variants`，80px、`?anim=0.25&freeze=1640`（命中那一刻）：由上往下、由下往上、橫掃（扁弧）、突刺（直線）、交叉斬（X）、迴旋（一圈）、反手刺（斜線）各自的弧光 |
| `6n6_gallery_8picks.jpg` | 同頁下半：每種武器連續 8 次的那兩排，以及頁面下方 8 列各 8 次挑到的變體（每列 ≥ 3 種） |
| `6n6_crit_float_52px.png` | `?crit=1&cell=52&floatAt=500`：52px 格上的「暴擊 −18」（停住時 1.3 倍、約 1.77 格寬） |
| `6n6_battle_heavy_cleave.jpg` | **實戰**（雲海吊橋，種子 500328441）：盜賊頭目（大劍＝斧錘雙手）普攻主角，seq 206「劈」——由上往下的弧 |
| `6n6_battle_heavy_whirl.jpg` | 同一場，同一個頭目 seq 211「掄一圈」——一整圈的弧 |
| `6n6_battle_sword_thrust.jpg` | **實戰**（開闊平原）：盜賊隊長（單手劍）seq 166「突刺」——往北打照朝東畫的直線 |
| `6n6_battle_sword_hop.jpg` | 同一場：盜賊2（匕首＝劍列）seq 172「小跳斬」 |
| `6n6_battle_sword_up.jpg` | 同一場：盜賊2 seq 174「由下往上」 |

- 實戰的變體名稱是用伺服器回應裡的 `attack_rolled`（seq、攻擊者、武器）照同一套雜湊算的，再和畫面對照。劍列那三張的弧被「−N」字樣擋住一部分，看得出形狀但不如 dev 頁清楚。
- 實戰的方法：自己啟動的伺服器（8366，存檔在 scratchpad）、build 版、無頭 Chrome（自己的設定檔、CDP 9366，由腳本 spawn、結束時只關它自己），`?anim=0.35`，主角一直按「結束回合」讓 AI 打，連拍後挑。dev 頁用內建瀏覽器借用 6N-5 留下的分頁 tab-22（原本的伺服器已關），大小已還原成 desktop；vite（5366）與伺服器都只用自己的 PID／工作停掉。沒碰 tmp_x、saves/，沒用 8000／8001／8010。
- **不能動時「失手」沒在實戰拍到**（要剛好打冰凍、暈眩的人又沒打中）；只有測試。

## 10. 檢查清單（需求第二批第 6 節，6N-6 部分）

- [x] 每種武器的變體數照表（劍 5、刀 5、魔導劍 4、斧錘雙手 3、成對 4、槍 4、鐮 3、鞭 3）。
- [x] 連續 8 次普攻至少出現 3 種：dev 頁與樣張的鍵都 ≥ 3；但純雜湊不能保證每一段 8 連擊都 ≥ 3（見待決 1）。
- [x] 重播時挑到的變體不變。
- [x] 弧光方向和揮的方向一致。
- [x] 所有變體 `hitAt` 相同；走路、跑步不做變體；異形退回通用片段；暴擊金色加粗套在每個變體上。

## 11. 待 PM 決定（都已照最保守的做法做完）

1. **「連續 8 次至少 3 種」只能統計上成立**：照規格是「雜湊 ÷ 變體數取餘數」，3 種變體的武器（斧錘、鐮、鞭）任選 8 次，約 12% 的機率只出現 2 種（隨機本來就會這樣）。測試鎖的是 dev 頁與樣張的鍵（都 ≥ 3）加上統計（≥ 80%）。若要每一段都保證，要改成「和同一人上一次不同」之類的規則，需要知道同一人上一次的變體（跨回應要從紀錄推），先不做。
   - 另外：FNV-1a 的低位元混合得差，變體數是 2 的冪（4 種：魔導劍、成對、槍）時，連續 seq 會很規律地輪（0,1,2,3,0,1…）。看起來仍是「每次不同」，但不像隨機。要更像隨機可以在取餘數前多做一次混合（例如 murmur 的 fmix32），但那就不是規格寫的「`seedOf` ÷ 變體數」；先照規格。6N-5 的閃避方向（÷2）也有同樣的情形。
2. **武器歸列**（表上沒寫的）：匕首歸「劍」、彎匕（`kris`）歸「刀」；大劍（含斬馬刀）歸「斧錘雙手」；主副手同種的劍、匕首歸「成對」。內容裡目前沒有「刀」的武器 ID，彎刀只會出現在裝備外觀 `form: curved`（dev 頁用裝備外觀放）。要改只改 `attackFamilyOf`。
3. **探索中的鍵**：`exploreVariantKey` 已寫好，但探索目前沒有攻擊動畫，沒有呼叫端。
4. **技能的近身出招不挑變體**：照分段，技能變體是 6N-8；現在技能照起手對照表、弧光照舊。
5. **鐮的預設普攻換了蓄力**：6N-6 以前鐮的普攻是「舉高蓄力（windup）→ 橫掃」，兩段之間會跳一下；現在「橫掃」的蓄力改成側收（`scythe_side_in`，同樣 260 ms），接得上。時間軸沒變。
6. **不能動的判斷用這一步結束時的 `view`**（浮動字與特效本來就用它）：如果這一步內狀態剛好被解除（例如被打醒），就會照「閃避」播。要更準要用這一步開始前的畫面。
7. **原型數值**：各變體的關節角度、弧光角度（由上往下 ±0.45π、橫掃壓扁 0.42、突刺直線長 2.2 倍半徑、迴旋壓扁 0.5）、小跳斬離地 7、跳刺 8、拔刀斬前衝 9。都在 `attackVariants.ts`，美術 PM 看 dev 頁再調。
8. **放大字一起縮**：背刺、伏擊、撞擊和暴擊同樣是放大字，這次一起變成 1.3 倍並受 1.8 格限制。只要暴擊縮的話，要在 `FloatItem` 加一個種類。

## Commit

- `b4769096` feat(client): melee attack variants picked by deterministic hash, arcs follow the swing (6N-6)
- `675a8e08` merge main（docs）
- `84e2a7f0` feat(client): immobile targets miss without a dodge (失手); crit float 1.3x and at most 1.8 cells wide
- `870bda54` feat(client): skill gallery #variants page for 6N-6 (all melee variants, 8 picks in a row, crit size)
- 報告與實戰截圖：最後一個 commit
