# Phase 3-12 報告｜技能特效

> 規格：`docs/phases/Phase3計畫.md` 15.1、15.2。只動前端繪圖；引擎、API、事件 schema、內容都沒改。
> 分支：`worktree-agent-afb133cbca1f2aebd`（從 main `0ef0614` 開出）。

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| `eac94b7` feat(client): derive skill VFX from events and skill cards | `battle/vfx.ts`（推導純函式）、`battle/vfxPalette.ts`（元素對照表與粒子軌跡）、`playback.ts` 加入 `vfx` 步驟、`vfx.test.ts`、20 個隨機技能 fixture 與產生腳本 `scripts/make_vfx_fixture.py` |
| `be8aefc` feat(client): draw skill VFX with PixiJS and add shake toggle | `render/vfxEffects.ts`（PixiJS 繪圖）、`BattleRenderer.playVfx`、`BattleScreen` 串接、「版面」面板的震動開關（`battle/vfxPrefs.ts`） |
| （本報告與截圖） | `docs/phases/Phase3-12報告.md`、`docs/phases/img/3-12-*.png` |

### 做法摘要

- **推導（`battle/vfx.ts`，純函式）**：`vfxFor(events, view, cards) → StepVfx { casts, hits, shake, leadMs }`。一步的事件切成「段」：`skill_used`、`skill_followup`（複合技能第二段，從 `origin` 出發）、不屬於目前技能的 `attack_rolled`（一般攻擊、反擊）。每段得到一個 `VfxCast { kind, element, from, to, tiles, path, ranged, intensity, crit, charge, startMs, impactMs }`；多段依序排開。
  - **形狀**：技能卡 `shape` 文字開頭的中文形狀名（`SHAPE_NAMES` 對照 `skill_shapes.yaml` 的 `name_zh`）。卡片缺少、形狀不認得、或與實際 `tiles` 不符（修正規則轉換形狀）時，改由 `tiles` 幾何推斷（全在自己格 → 自身；一格 → 單體；施放者正方向連續 → 直線；其他 → 範圍）。骨架 `aura`／`stance` 且形狀不認得時當光環。
  - **遠程／近戰**：施放者到目標的切比雪夫距離 > 1 為遠程（不看武器文字，以實際距離為準）。
  - **元素**：該段施放者造成的第一筆 `damage_dealt.element` → 其次 `element_touched.element` → 有治療或護盾為 `support`（綠色）→ 一般攻擊為 `physical` → 其他為 `default`（奧術紫）。
  - **暴擊**：該段有 `crit` → `intensity = 1.6`（粒子、爆發大小）、受擊閃白加金色外環、強震動。
  - **時間**：蓄力 160ms ＋ 飛行（飛行物 90＋45×距離，上限 360）或光束／扇形／範圍／光環的固定時間；命中後爆發 520ms。`playback.ts` 依播放速度（慢 ×2、正常 ×1、快 ×0.5）縮放，略過時沒有 `vfx` 步驟。
- **播放順序**：標示行動者 → 位移動畫 → **`vfx`（蓄力與飛行，等到命中）** → 畫 `view` → 地圖回饋（浮動數字）→ 紀錄 → 停頓。浮動數字因此在命中瞬間才出現。
- **繪圖（`render/vfxEffects.ts`）**：每個效果一個 `Graphics`，每幀 `clear()` 重畫；粒子位置由 `vfxPalette.particleAt`（純函式）算出。效果結束時由既有的效果迴圈 `destroy`；震動效果的 `end()` 把場景位移歸零；沒有效果時移除 ticker 回呼。沒有新增任何相依或外部素材。
- **震動開關**：「版面」面板新增「技能特效的畫面震動」勾選框，存在 `localStorage` 的 `trpg.vfxShake`（獨立於版面的「重設為預設」）。

### 元素 × 形狀 對照表

形狀 → 特效種類（`vfx.ts` 的 `SHAPE_KIND`）：

| 形狀（卡片文字） | 種類 | 表現 |
|---|---|---|
| 單體（遠程，距離 > 1） | `projectile` | 蓄力 → 飛行物（拖尾 3 顆；雷另有鋸齒軌跡）→ 目標爆發 |
| 單體（近戰，相鄰） | `slash` | 蓄力 → 在目標身上掃過一道弧 → 小爆發 |
| 單體（目標是自己） | `burst` | 原地爆發 |
| 直線 | `beam` | 光束沿路延伸到最遠格（雷為鋸齒）→ 各格依距離錯開爆發 |
| 連鎖 | `beam` | 光束依序連過命中的單位 |
| 錐形 | `cone` | 扇形從施放者擴散 → 各格依距離錯開爆發 |
| 十字、方陣、環形、指定格 | `area` | 範圍格逐格閃色 ＋ 爆發（依與中心的距離錯開） |
| 物件與落點、單位與落點、兩個單位 | `area` | 同上（影響的格子） |
| 自身、範圍光環 | `aura` | 從施放者向外擴散的兩道環；命中的單位身上另有爆發 |
| 不認得的形狀 | 依 `tiles` 推斷 | 見上 |
| 一般攻擊（`attack_rolled`） | `slash`／`projectile` | 依距離；不蓄力，元素取傷害事件（多為物理） |

元素 → 配色與粒子（`vfxPalette.ts` 的 `ELEMENT_VFX`；任何元素 × 任何形狀都自動組合）：

| 元素 | 主色／副色 | 粒子行為 | 特別 |
|---|---|---|---|
| 物理 physical | 白／灰藍 | 火花（向外短線） | |
| 火焰 fire | 橘／金 | 火星上飄 | |
| 冰霜 ice | 冰藍／白 | 碎晶向外飛後下墜 | |
| 雷電 lightning | 黃／淡藍 | 鋸齒閃電 | 光束與飛行軌跡為鋸齒 |
| 毒素 poison | 綠／深綠 | 綠泡緩慢上升變大 | |
| 風 wind | 淡青／青綠 | 弧線旋出 | |
| 大地 earth | 土褐／深褐 | 碎石拋出落下 | |
| 神聖 holy | 淡金／金 | 光點上升 | 命中處多一道光柱 |
| 暗影 shadow | 紫／深紫 | 煙霧擴大淡出 | |
| （水 water，非元素） | 藍／淡藍 | 水花拋物線 | 保留，內容若加入水元素可直接用 |
| 支援 support | 綠／淡綠 | 閃光 | 無傷害的治療、護盾技能 |
| 預設 default | 奧術紫／白 | 閃光 | 不認得的元素、無傷害也無元素的技能 |

## 2. 驗收條件逐條（15.2）

1. **推導函式的 vitest；20 個隨機技能都推導得到特效** — ✅
   - `client/src/battle/vfx.test.ts`（67 個測試）：每種形狀 × 遠程／近戰（18 組案例：單體遠程、單體武器射程穿透、近戰正向與斜向、直線兩種、錐形、十字兩種、方陣、環形、指定格、自身、範圍光環、連鎖、單位與落點、兩個單位、物件與落點）、每個元素（9 個）、暴擊、未知元素與未知形狀的預設、卡片缺少時的幾何推斷、形狀轉換時以格子為準、一般攻擊與反擊、複合技能第二段、環境傷害、速度縮放與 `frameOps` 順序。
   - 20 個隨機技能：`scripts/make_vfx_fixture.py` 以工坊隨機組合器（與 `trpg skills random` 同一個函式，種子 1–20）組技能，在訓練場以 API 真的施放一次，記錄技能卡、施放那一步的事件與單位位置 → `client/src/battle/fixtures/vfx_random_skills.json`（17 個有施放紀錄；3 個沒施放成功——被動、條件不符——以施放者旁一格代替）。測試 `20 random workshop skills` 逐一確認每個都推導出合法種類的特效、形狀都認得。
2. **瀏覽器實測與截圖** — ✅（方法見下方附註）
   - 火遠程：`docs/phases/img/3-12-fire-ranged-charge.png`（蓄力光與剛出手的火球）、`3-12-fire-ranged-impact.png`（命中閃白、浮動數字與燃燒）— 實際施放「火焰箭」。
   - AI 一般攻擊（遠程物理飛行物）：`3-12-ai-basic-ranged.png` — 實際 AI 回合。
   - 冰範圍：`3-12-ice-area.png`（方陣逐格碎晶）。
   - 雷直線：`3-12-lightning-line.png`（鋸齒光束延伸中）、`3-12-lightning-impact.png`（命中兩個敵人閃白、震動中）。
   - 近戰揮砍：`3-12-melee-slash.png`。
   - 暴擊：`3-12-crit.png`（金色外環、加大的揮砍與火花、強震動）。
   - 震動開關：`3-12-shake-toggle.png`（「版面」面板）。
   - **附註**：內建內容沒有「冰範圍」「雷直線」技能，近戰與暴擊也難在固定時間點遇到，所以這四張是在真實戰鬥畫面上，對畫布的 `BattleRenderer.playVfx` 直接送特效描述（與 `vfxFor` 的輸出同格式）拍的；火遠程與 AI 一般攻擊是完整實際流程。截圖時以注入的時間放慢（`requestAnimationFrame`／`setTimeout` 時間縮放）凍結中間畫面，未修改程式。
3. **播放速度四種都正確；震動可關閉** — ✅
   - 測試：`scaleVfx and playback` 確認慢＝2 倍、快＝一半、略過沒有特效步驟，`vfx` 步驟在移動之後、`view` 之前。
   - 瀏覽器：略過速度下連續 3 回合 `effectList` 最大值 0；正常速度 AI 回合有 15–22 個效果。震動關閉時一整個 AI 回合場景位移最大值 0；開啟時 6.48 px（一次實際暴擊）。效果全部結束後 `effects` 圖層子物件 0、場景位移歸零、ticker 回呼已移除（不洩漏）。
   - 效能：極端壓力（5 個 49 格暴擊範圍同時、745 個效果）每幀更新＋渲染約 30 ms；一般單次技能約數十個效果，估計 1–2 ms。內建瀏覽器的分頁在背景被節流（rAF 約 1 次／秒），所以無法在此量實際 FPS，改量每幀成本。
4. **`check.py` 全過、`pnpm build` 成功** — ✅ `uv run python scripts/check.py`：全部檢查通過（pytest 3255 passed；client 35 檔 381 個 vitest 通過）。`corepack pnpm -C client build` 成功（「chunk 大於 500 kB」為既有警告）。

## 3. 複雜度 noqa

無新增或移除（前端沒有複雜度 lint；新 Python 腳本無 noqa）。noqa 總數不變。

## 4. 修改既有測試期望值

無。既有 `playback.test.ts` 全部照舊通過（`vfx` 步驟只插在有特效的格子、位於 `view` 之前）。

## 5. 待 PM 決定

1. **規格的 9 元素清單含「水」，但引擎元素是 物理／火／冰／雷／毒／風／大地／神聖／暗影（水只是表面）**：依「以既有型別為準」做了物理（火花），另保留一組「水花」給之後若加入水元素；要不要讓「生成水表面」的技能也用水花配色？
2. **形狀由技能卡的中文字串對照**（API 沒有形狀 id）：內容改了形狀的 `name_zh` 會退回幾何推斷（仍有合理特效）。建議之後在 `SkillCard` 加 `shape_id`（API 變更，本段未做）。
3. **無傷害技能的配色**：治療／護盾用綠色「支援」，其他（增益、控制、位移）用奧術紫預設。是否要改依狀態或標籤上色？
4. **一般攻擊也有特效**（近戰揮砍／遠程飛行物、物理火花），規格只寫技能；若覺得太吵可關。
5. **震動開關放在「版面」面板，且不受「重設為預設」影響**；是否要再加「關閉全部特效」的選項？
6. **暗影突襲、閃現等位移技能**仍以位移動畫為主，特效只在影響格做範圍爆發；是否要為傳送類另做「消散／出現」表現？
7. **連鎖技能的光束依命中順序連線**；沒有命中時只連到第一格。
8. **截圖解析度**：內建瀏覽器面板較小（截圖 643×402），粒子細節不明顯；3-13 原型美術後可重拍。
9. **蓄力時間固定 160ms（正常速度）**，不依技能 AP 或稀有度變化；是否要讓傳說技能有較長、較華麗的蓄力？

## 6. 代表性輸出節錄

`vfxFor` 對「方陣（射程 2）、冰霜傷害、一筆暴擊」的輸出（正常速度）：

```ts
{
  casts: [{ kind: "area", element: "ice", from: {x:2,y:2}, to: {x:4,y:4}, tiles: [/* 9 格 */],
            path: [{x:2,y:2},{x:4,y:4}], ranged: true, intensity: 1.6, crit: true, charge: true,
            startMs: 0, impactMs: 300 }],
  hits: [{ pos: {x:4,y:4}, element: "ice", crit: true, atMs: 300 }],
  shake: 2,
  leadMs: 300,
}
```

`uv run python scripts/make_vfx_fixture.py`：

```
20 個技能，17 個有施放紀錄 → client/src/battle/fixtures/vfx_random_skills.json
```
