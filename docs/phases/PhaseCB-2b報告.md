# Phase CB-2b 報告｜異形招式動畫挑選

基準 main 08c72991。不改 `content/`、`src/trpg/engine/`；不畫新片段；動畫雜湊快照未重產。

## 改了什麼

- `client/src/battle/creatureAction.ts`（新）：`creatureActionOf` 照美術 PM 第 1 節的順序挑動作類型（summon → 位移 → dash／charge_through／leap → 錐形＝吐息 → 指定招小表 → 其餘照現行 `creatureAttackTypeOf`）；普攻不走前五層。指定招小表 `CREATURE_CHARGE_SKILLS`（`skill_battering_ram`、`skill_plunging_strike`）放前端，技能資料與 LLM 都沒有多欄位。
- `skillSequence.ts`：段落帶 `shape`、`casterMove`、`creature`；`SkillRow.creature = { action, inPlace? }`；`StrikeOf` 收動作類型（不再收人形片段與距離）。
- `viewGrip.creatureStrikeInView(id, view, action)`；回傳 `blink: true` 僅在片段真的是閃現（退回普攻的身形不算）。
- `skillLayer`：出招列用 `r.creature.action`；`inPlace` 把 root dx 歸零；**命中時重畫會把朝向換回規則的朝向**（見待決 1），所以片段播完前維持面向東西向的目標，片段結束轉回規則朝向（只有異形）。
- `motionLayer.creatureBlinkMove` ＋ `MoveAnim.creatureBlink`：閃現片段直接播在傳送上（長度＝片段、照速度縮放），中段（完全透明時）換格；出招列不再播，落地不再多閃一次。減少動態照舊走原本的淡出淡入。
- `creaturePose.inPlace`、快取鍵含 `inplace`；`inkCreature.partPoseOf` 套用。
- 開發頁 `client/dev/skill-gallery.html#cb2b?case=…`（9 個案例，走正式 `playbackPlan → frameOps`）。

## 驗收條件

| 條件 | 結果 | 證據 |
|---|---|---|
| typecheck | PASS，exit 0 | `npx tsc --noEmit` |
| 相關 vitest | PASS，exit 0 | `npx vitest run src/battle src/render src/dev src/audio src/test --reporter=dot`（含 `inkDollSnapshot`、`creaturePose`、`qCreatureAnim`、`creatureStrike`、`importCycles` 等；168 檔 1918 項全 PASS） |
| `npx vite build` | PASS，exit 0 | 建置輸出 |
| 排版煙霧 1600×900 | **全 PASS（12 項）** | `window.__layoutSmoke.runCase("1600x900")`；`/?dev=1&anim=0.1`，localStorage 先清 |
| 動畫雜湊快照 | 未變、未重產 | `inkDollSnapshot.test.ts`、`creaturePose.test.ts` 原樣通過；`inPlace` 只在帶旗標時改快取鍵 |
| 人形既有動畫測試 | 原樣通過 | `skillSequence.test.ts`、`impactFeel.test.ts`、`hitReactions.test.ts` |
| 6 個片段實機連拍 | PASS（**開發頁**） | 見下 |
| 第 1 節檢查項 | 全部列於下 | |

## 表格測試範圍（`client/src/battle/creatureAction.test.ts`）

資料讀實際的 `content/skills/*.yaml`、`content/units/*.yaml`（異形種類取 `doll.creature`）：

- 六層各有實招（`CB-2b 異形招式動畫挑選 > %s %s…`，14 列）：產下幼蜥、魅閃現 ×2、山豹撲擊、火牆、硫煙吐息（相鄰與 3 格）、破城衝撞 ×2、俯衝斬、靜電掌、油瓶、雙牙、餘燼咬。
- `每一個實際的技能 YAML（含後段）都照順序`：全部技能 × 距離 0／1／3，涵蓋層與層的先後。
- `現有異形的招：不屬於前五層的，和改前一樣；普攻不看原語`：逐招比對改前的 `creatureAttackTypeOf`（行為一致）。
- 片段接線：山豹 `inPlace` 與位移排序、甲蟲推開在 after 且命中點對齊、魅閃現無出招列且傳送帶片段長度、蜥蜴召喚 leadMs 不早於出手格、`inPlace` 進快取鍵。
- CB-2a 合併後新增招會自動進「每一個實際的技能 YAML」與「現有異形的招」兩條；若要新增列只要在 `TABLE` 加一行。

## 第 1 節檢查項（美術 PM）

連拍在 `docs/art/shots/cb2b/`（9 張，jpg 80，每張約 120 KB；時間標籤是遊戲內毫秒）。全部由開發頁 `#cb2b`＋`?anim=0.1` 無頭 Chrome（`--mute-audio`）連拍：**真實戰鬥中要讓 AI 剛好放這些招不容易，這裡走的是和戰鬥相同的播放器與事件格式，事件由人手依引擎事件形狀寫成，不是戰鬥實錄**。

| 片段 | 要看什麼 | 結果 | 截圖 |
|---|---|---|---|
| 山豹撲擊 | 前衝不和 dash 疊加、不先退回原地 | PASS：跑到相鄰格後原地騰撲（root dx 歸零），身體沒有超出落點、也沒有回起點 | `1-leopard-pounce.jpg` |
| 甲蟲衝撞 | 不移動的招，前衝後回原位；被撞者推開時間對齊 | PASS：463 ms 前衝命中，697 ms 目標已推開、身體回到原位 | `2-beetle-ram.jpg` |
| 鷹俯衝 | 俯衝落點對準目標，結束後回飛行高度 | PASS：俯衝落在目標前方；片段結束回到 dy＝0（飛行高度，935 ms）。**之後的待機是既有的落地待機（dy＋9），爪擊同樣如此** | `3-hawk-dive.jpg` |
| 噴岩龜、硫煙獸噴吐 | 噴口朝向目標，朝東、朝西都對 | PASS：東、西各一組；西向案例開場故意朝東，施放轉身後噴口朝西。**修掉一個 bug**：命中重畫會把身體翻回規則朝向（見待決 1） | `4a` `4b` `5a` `5b` |
| 蜥蜴產卵 | 幼蜥在片段產出時間點出現，不提早 | PASS：855 ms 還沒有幼蜥，孵化（約 1000 ms）時才出現。蛋與幼蜥位置見待決 2 | `6-lizard-summon.jpg` |
| 魅閃現 | 淡出、淡入和傳送事件對齊，不在原地多閃 | PASS：原地淡出、中段換格、新格淡入；落地後無第二次閃爍（1369 ms 起的淡影是隱身狀態） | `7-wraith-blink.jpg` |
| 減少動態 | 照 QK-4 規則 | 程式路徑沿用：攻擊片段的減少動態照舊；閃現走原本的淡出淡入。**沒有另外截圖** | — |

硫煙吐息貼身放（`5a`、`5b` 相鄰）：播吐息，不再退回獠牙撞。

## 待 PM 決定

1. **朝向**：引擎的 `face_toward` 只在攻擊結算、瞬步等處呼叫，沒有攻擊結算的招（如火牆）施放後朝向不變（我只讀了呼叫點，沒有逐招跑引擎確認）。前端已讓異形在出招片段播完前維持面向東西向的目標，片段結束轉回規則朝向。人形同樣的現象未動（範圍外）；若要規則上也轉身，屬引擎決定。目標在正南、正北時片段仍是側面播（沿用現況）。
2. **蛋落點**：`atk:summon` 的蛋固定落在身前約 0.65 格；幼蜥實際出現在指定格（射程 2）時，位置對不上。只能改片段或讓片段讀目標距離，本段不動，請美術 PM 判斷要不要調。
3. **鷹待機**：`qCreatureAnim` 的鷹待機是落地姿勢，所以所有鷹的招（含俯衝斬）結束後會從飛行高度落回地面（既有行為）。檢查項「回到飛行高度」以片段結束那一格判定；若要改成持續飛著，要動待機。
4. **普攻**：文件寫「普攻一律是普攻片段」，保守解讀為「普攻不走前五層，遠程普攻照現行播遠程片段」（維持改前）。
5. **頭目**：`creatureStrikeInView` 與 `drawCreature` 的頭目路徑共用同一套動作類型；現有頭目的招都落在第 6 層，結果和改前相同。`inPlace` 對頭目無效（目前沒有頭目有 dash）。
6. **連拍來源**：全部是開發頁（真實播放器＋人寫事件），沒有戰鬥實錄。

## 其他

- `qBoss4b.test.ts` 的 `creatureStrikeInView` 呼叫改成新簽名（`"cast"`），測的內容不變。
- 伺服器與無頭 Chrome 都用自己的 PID 關掉（vite 44520、chrome 37776、serve 20968），5197／9477／8093 埠確認沒有殘留。
