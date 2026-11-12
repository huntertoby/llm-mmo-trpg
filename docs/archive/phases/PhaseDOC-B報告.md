# Phase DOC-B 報告：文件瘦身第二批（開發 PM 交接文件與 README 重寫）

> 依 `docs/phases/整理提案-程式.md` 第 1 節執行 M1～M4、S3，M5 只列不改（使用者原話「瘦身都照建議」）。2026-11-06。只改 `docs/開發PM交接.md`、`README.md`、新檔 `docs/archive/交接歷史-開發PM.md`、本報告；純文件，沒跑測試，只用 `grep`／`ls`／`git ls-files` 核對連結。

## 1. 做了什麼

| 項 | 內容 | 大小 | commit |
|---|---|---|---|
| M1 | `docs/開發PM交接.md` 第 3 節的 3.00000（10-31）、3.0000（10-29）、3.000（10-28）、3.00（10-23）、3.0（10-22）、3.0.1～3.0.3 八個小節原文整段搬到新檔 `docs/archive/交接歷史-開發PM.md`（檔頭一句指回現況，由新到舊）；留下的三節改編號 **3.1（11-06）、3.2（11-05）、3.3（11-02）**，標題拿掉「優先於下面各節」，3.1 開頭加「3.1 最新；3.2、3.3 是前兩次交接，只為了查脈絡」；全文的 `3.00000000`／`3.0000000`／`3.00000 第 4 點` 引用改成新編號或指到 archive | 交接 87,559 → 55,817 B | `e1686ae1` |
| M2 | 原 3.1「使用者已同意的方向（10-18）」：內容就是 `docs/專案計畫.md` 第 14 節 v0.2.1 的調換說明＋ 2D／2E 已完成表，整段歸檔。原 3.1.2「加快階段速度」：五條都已在 `CLAUDE.md` 守則 11（只跑相關測試、全量只在交件前、大型模擬不放實作段）與本檔 §6.2 第 1、5 點（一段上限「一套規則＋其測試」、大型模擬由 PM 背景跑），沒有別處沒有的守則，**沒有另立「仍有效的經驗」小節**，整段歸檔。原 3.3「延後到平衡階段的累積待辦」逐列對 `PhaseBAL計畫.md`（第 2 節末、第 3～12 節）與 `docs/archive/phases/BAL-*報告.md` 核對（第 2 節處置表）：已做的刪、未做或拿不準的搬進 3.1 第 4 點「來自原 3.3」（四條：規則類、未單獨量測的初值、AI、小項），原 3.3 整節從交接文件刪除；**原文另保留在 `交接歷史-開發PM.md` 末段「原 3.1、3.1.2、3.3」**（保守做法，之後要刪由 PM 決定）。原 3.4 改編號 3.4 | 交接 55,817 → 40,287 B；archive 檔 32,057 → 49,838 B | `0901aa7f` |
| M3 | §2「專案現況」重寫成一張 11 列表（Phase 0～1、2A～2H、3＋3C～3W＋C 畫風、4（4-L11 小待辦）、5A～5F、BAL-1～19g、Phase 6 已結案系列、Phase 6 進行中系列（6T／6R／UI-E 三段標「等 Windows push」）、MAC-1／2 ✅、DOC-A／B ✅、LLM-1 進行中），測試數改成 2026-11-06 全量 pytest 15217、vitest 3045，版號照 3.2（`LOG_FORMAT` /112 等）；內容數改成現在的數字（`content/skills/` 約 390 檔、`content/maps/` 17 張、實地地圖 44 張）；主要指令改 Mac 寫法（`uv run trpg …`、`pnpm -C client …`、`llm ping`）；刪掉「一輪的平衡現況：AI 代打 2 勝」（一輪勝率目標 10-31 已取消）。§6.1 重寫成 macOS 版（uv 在 `~/.local/bin`、`export PATH`、Node 26 無 corepack 用 `pnpm -C client`、`pnpm_command()` 在 `src/trpg/cli/frontend.py`、8000／8001 不用、LM Studio 與 `config/llm.local.toml`、模型載著時不跑全量、只關自己的 PID、CI 手動、`.claude/settings.json`、vitest 兩個快照回 Windows 要再跑），Windows 縮成一行指到 archive；拿掉 Windows 時期的「雲端模式（remote-devices）」段。§6.2 的 `corepack pnpm -C client build` → `pnpm -C client build`；§6.4 範本的「Windows 商店空殼」改成 Mac 優先寫法、`F:\WSL` 改成 `config/llm.local.toml`、`taskkill` 例子加 `pkill`／`killall`。3.2 的 `C:\Users\tobby\…` 共用筆記改成「由專案 PM 開場訊息給（Mac：`~/Library/Application Support/Claude/side-session-notes/<專案 PM id>/`）」；3.2、3.3 的舊 PM id 整行換成「當時的 PM id 已失效，現行 id 見 3.1」（舊 id 只留在 archive）。懸空引用：`docs/phases/工坊盤點-2026-10-24.md` → `docs/archive/phases/…`、`docs/art/*檢查.md` 註明已結案的在 `docs/archive/art/`、`PhaseUI-E3b報告`／`Phase6R-2報告` 註明「在 Windows 分支，尚未 push」；3.1 第 3 點 MAC-2 由「進行中」改 ✅（`c6b43e26`、`0898b086`，報告已在 `docs/phases/`），檔頭「現況一句話」同步 | 交接 40,287 → 41,486 B | `3caabc43` |
| M4 | `README.md` 重寫：標題＋原本那句簡介；「目前進度」3 行（原型與 BAL 完成、Phase 5 上線、Phase 6 收尾中、測試數）；「安裝與執行」macOS 6 行、Windows 5 行（uv 安裝、`uv sync`、`check.py`、pnpm／corepack 前端、`trpg serve`），細節指 `docs/部署說明.md`；保留仍能跑的 CLI 試用指令（`map list` 核對過 `oil_depot`、`swamp`、`test_heights_8x8` 都在）；文件索引改成一句「見 `CLAUDE.md`」，刪掉說「`docs/專案計畫.md` 唯一的設計真相來源」的舊表 | README 2,837 → 2,348 B | `22736eb0` |
| S3 | §6.5.2「交件截圖規則」：存 `docs/art/shots/<段>/`（段名小寫）、每段 ≤ 10 張、jpg 80、單張 ≤ 300 KB；美術通過後 1600 寬與 800 寬各留 1 張，其餘工作區 `git rm`（歷史仍在）；舊截圖已依前綴搬進 `shots/`（DOC-A），找圖用 `git ls-files`；§6.4 派工範本加一句「截圖照 6.5.2」 | 交接 41,486 → 42,269 B | `1f4c3e4a` |

最終：`docs/開發PM交接.md` **42,269 B**（目標 ≤ 50 KB；原 87,559 B）、`README.md` 2,348 B、`docs/archive/交接歷史-開發PM.md` 49,838 B。交接文件現在的結構：§1 角色、§2 現況表、§3.1～3.3 三次交接＋3.4 技術細節、§4～5 設計決定、§6 流程（6.1 Mac 環境、6.2 流程、6.3 模型、6.4 範本、6.5／6.5.1／6.5.2、6.6 坑）、§7 token。

## 2. 原 3.3 逐列處置表

依據欄的「§N」指 `docs/phases/PhaseBAL計畫.md` 的節；報告指 `docs/archive/phases/BAL-*報告.md`。

| 原列 | 處置 | 依據 |
|---|---|---|
| B-3W 靈感總量（一季尺度兩種玩家模擬） | **搬**（規則類） | 原型每勝 2 點已定（§2 BAL-1b）；一季尺度模擬沒做；使用者 10-31 取消一輪勝率目標後沒再提 |
| B-3W-2 輔助 → 被動轉型 | **搬**（規則類） | §1「規則類（回使用者）」列著；BAL-3報告第 6 項說只在需要時回使用者，之後沒排 |
| B-3W-3 姿態等級表、維持費換算、轉型後姿態扣法力 | **搬**（拿不準） | §1 列在技能數值批，但 §7 BAL-12 只做 B-3W-4／5；維持費不打折已定（§2 BAL-4b、§10 #67），等級表與扣法力問題沒單獨量 |
| B-3W-4 升階持續上限、層數參數 | 刪 | §7 BAL-12e 玩法決定 #76：上限 6、升階改加強度（層數改用強度取代） |
| B-3W-5 完整技能 +150‰ 超標、幅度階梯 | 刪 | §7 BAL-12c：超過 +200‰ 停 +120‰ 以下、修正幅度 5‰ 細階梯；50 → 23 招 |
| B-3W-6 ①靈感與閃現次數 ②修正／觸發 0 次 ③其他 | 刪（①②③）；「一季尺度模擬未做」併進 B-3W 列 | §2 BAL-1／1b、BAL-2／2b～2d；全指定集中由三種 AI 保留處理 |
| 使用者 2026-10-23「平衡延後」段落 | 刪（歷史） | 平衡階段已做完；原文留在 archive |
| B1 普攻流範圍技選用率 | 刪 | §2 BAL-5：46 → 78%、清場輪數比 1.17、Boss 擊殺輪數比 0.96 |
| B2 召喚流對照 | 刪 | §9 BAL-14a／14b（含長戰 10 輪情境） |
| B3 召喚物存活門檻 | 刪 | §9 BAL-14a／14b（鷹隼 70 → 44%） |
| B4 召喚持續輪數與預算 | 刪 | §9 BAL-14b：召喚預算 800 與各召喚持續「不改」（玩法 PM 定） |
| B5 召喚物 AI | 刪 | §2 BAL-5（灌注 1300、不帶遠程上高台）＋ §9 BAL-14a |
| B6 刃刻降階 | **搬**（拿不準） | 計畫與 48 份 BAL 報告都沒有「刃刻」 |
| B7 Boss 公平性 | 刪 | §2 BAL-8／9（`boss_approach`、頭目 HP 700‰、普攻流不是唯一解）、§11 BAL-16a 護衛撤退 |
| B8 戰場變奏初值 | **搬**（拿不準） | 只在 §1 分組列過，沒有量測紀錄 |
| B9 法力續航 | 刪 | §10：規則定為營火回滿；BAL-15a Boss 戰短缺 18.3% ≤ 20% |
| B10 普攻屬性倍率 | **搬**（拿不準） | 只在 §1 分組列過 |
| B11 法力、耐力係數 | 刪 | §10 BAL-15a：`mana_cap_permille` 1400 維持 |
| B12 心智三分後的流派 | 刪 | BAL-3 全面基線與 §7／§8 的 build 矩陣（summoner、seer 都量過） |
| B13 屬性常駐係數 | **搬**（拿不準） | 只在 §1 分組列過 |
| B14 敵我同一套資源公式 | 刪 | §10 BAL-15b 玩法決定 #80 |
| B15 法力回復 | 刪 | 使用者 10-24「只在營火回滿」；§10 |
| B16 新武器傷害骰（拳套、鐮刀、鞭） | 刪 | BAL-8報告：114%／106%／94% 都在區間 |
| B17 圓盾格擋強化 | **搬**（拿不準） | BAL-3報告寫明「未量」，之後沒排 |
| B18 雙匕首偏強 | **搬**（拿不準） | BAL-8 131% ⚠ → BAL-9 對照未改 123.9%；沒看到玩法 PM 結案句 |
| B19 霰彈槍偏弱 | 刪 | §2 BAL-5：位置價值修好 32 → 48%，BAL-8 DPR 81% ✓ |
| B20 代價技 AI 條件 | 刪 | BAL-8 量測、BAL-8b 套用（`overdrawn` 8 → 3、`self_status_values.stun` 5） |
| B21 魔劍斬改武器技 | **搬**（拿不準） | BAL-3報告「未量」；BAL-13c 只當矩陣的一列 |
| B22 物品產生器初值 | **搬**（拿不準） | BAL-3報告「未量」；Phase 5 掉落後沒重量 |
| B23 親和出現率 | **搬**（拿不準） | 沒有量測；BAL-13d 只提到背刺條件不影響親和判斷 |
| B24 防具基礎防禦 | **搬**（拿不準） | BAL-3報告「未量」 |
| B25 風的初值 | **搬**（拿不準） | BAL-3報告「未量」；BAL-12e 的「吹送」是表面強度，不是這項 |
| 召喚物（玩法 PM 10-23） | 刪 | 同 B2～B5 |
| 普攻流（3-32d） | 刪 | 同 B1 |
| 勝率 70–95%、`oil_depot` 偏難 | 刪 | §2 BAL-4／4b／6：難度倍率後一般戰 56%、oil_depot 換頭目 |
| build 矩陣（2C-3 tank／assassin） | 刪 | §7 BAL-12a／12d 前段判定重做、§8 BAL-13 |
| AI 很少用控場、位移、場地技；控制回合接近 0 | **搬**（拿不準） | §1 列在 AI 行為批，BAL-5 只修範圍技、霰彈槍、灌注 |
| `skill_fire_bolt` DPR 超 P95 | 刪 | §7 BAL-12a／12d fire 系費用、§8 BAL-13a |
| 結構型原語點數偏低（2B-3） | **搬**（拿不準） | 沒有紀錄；可能已被 BAL-11 預算旋鈕查修涵蓋 |
| 冰面滑倒對 AI、`bridge_chasm` 集火反升 | **搬**（拿不準） | 沒有紀錄（BAL 報告裡的 bridge_chasm 只是矩陣地圖） |
| 代價折抵上限 +500‰、組合器權重在 content | 刪 | 事實陳述，不是待辦 |
| 2D 後 tank／healer 0 前段 | 刪 | 同 build 矩陣列 |
| 2E-2 guardian 偏強、反應技 fuzz 少觸發 | 刪 | BAL-3 基線涵蓋全部 build；§10 BAL-15c 量過還擊觸發 |
| 2E-3 tank／striker 無前段；trapper 擺位 | tank／striker 刪；**trapper 擺位搬** | 前段判定 §7；陷阱擺位沒有紀錄 |
| 2H 新數值未模擬、`arcane_blade` 在 build_push | **搬**（拿不準） | 沒有單獨量測紀錄 |
| 2G 驗收數字（completion／matrix） | 刪 | 歷史數字 |
| 2G-2 示範技能只為過預算；AI 把築高台當攻擊技；敵方無被動／反應／姿態 | 示範技能刪（§8 BAL-13e 天賜好運）；敵方反應刪（§10 BAL-15c 敵人帶反應技）；**築高台搬** | 築高台沒有紀錄 |
| 2G-1 build_tank 法力 20 | 刪 | §10 BAL-15b 資源改公式 |
| `CONTROL_STATUSES` 只算三種 | **搬**（小項） | 沒有紀錄 |
| 3C／3D／3F 後：storm／detonator／fire 偏強、弱 build | 刪 | §7、§8 |
| 撞擊流不如預期、合併 build 建議 | **搬**（拿不準） | 未決定 |
| roguelite 一輪只贏 3 輪、Boss 30% | 刪 | 一輪勝率目標 10-31 取消 |
| 新原語預算係數與 AI 權重初值未模擬 | 刪 | BAL-3 全面基線、BAL-11 旋鈕查修 |
| 背刺次數與權重 | 刪 | §8 BAL-13d（瞬步背刺 1.21 倍） |
| 召喚物很快被打倒；AI 隊友走進火牆；定時炸彈炸隊友 | 召喚刪（§9）；**火牆／炸彈搬** | 沒有紀錄 |
| 修正型被動「打法差異」低，Phase 4 避免大量產生 | **搬**（拿不準） | 4-L 報告沒看到處理 |
| `dread_gaze`／`hush` 貼下限、`hex_bolt` 1 回合、AI 重複施放 | 刪 | §7 BAL-12c／12d（hex_bolt +50% 後卡預算不動） |
| 3-5～3-17：一輪 2 勝、Boss 不動平手、HP 取整、玩家配體質未測 | 一輪與 Boss 刪（§2 BAL-9 `boss_approach`、目標取消）；HP 取整刪（事實）；**配體質搬** | 配體質沒有紀錄 |
| 3-7 體質抵抗後 matrix 未重跑 | 刪 | BAL-3 全面基線重跑 |
| 3-11 暫時障礙係數、冰牆／荊棘牆、煙霧彈 | **搬**（拿不準） | 沒有紀錄 |

## 3. 連結核對

- `grep -n "docs/phases/\|docs/art/" docs/開發PM交接.md README.md`：逐條用 `ls`／`git ls-files` 對過。存在的：`4-L9/`、`PhaseBAL計畫`、`PhaseDOC-A報告`、`PhaseMAC-1報告`、`PhaseMAC-2報告`、`Phase6F-19報告`、`Phase6報告`、`整理提案-程式`、`docs/archive/phases/工坊盤點-2026-10-24.md`、`docs/art/shots/`、`docs/art/*檢查.md`（進行中的 8 份）。不存在但已註明的：`PhaseUI-E3b報告`、`Phase6R-2報告`（Windows 分支，尚未 push）、`PhaseLLM-1報告`（待寫）、`PhaseDOC-B報告`（本檔，commit 後存在）、範本裡的 `PhaseX計畫／報告`、`Phase<段>報告`（佔位）。
- 交接文件裡不帶路徑的檔名（`Phase0計畫.md` 等 12 個）都在 `docs/phases/`。

## 4. CLAUDE.md 建議改行（M5，交專案 PM 改；原文 → 建議）

1. 文件索引表 `| docs/phases/PhaseN報告.md | 第 N 階段的完成報告（由實作者撰寫） |` → `| docs/phases/PhaseN報告.md | 進行中階段的完成報告（由實作者撰寫）；已結案的在 docs/archive/phases/ |`
2. 文件索引表 `| docs/archive/ | 舊版計畫，只供參考 |` → `| docs/archive/ | 歸檔：phases/（已結案報告，索引 phases/README.md）、art/（已結案美術檢查）、交接歷史-開發PM.md 與舊版計畫、玩法決定紀錄 1～138；只供查脈絡 |`
3. 文件索引表新增一列（放 `docs/phases/PhaseN報告.md` 之後）：`| docs/部署說明.md | 開服、Tunnel、Discord Bot、備份與季末重置（macOS 與 Windows） |`
4. 文件索引表新增一列：`| docs/phases/整理提案-程式.md | 文件與程式整理提案（第 1 節文件已做完 DOC-A／DOC-B；第 2 節程式 I1～I8、R1～R6 待排）；整理完後刪這列 |`
5. 常用指令區塊：在 `uv sync` 前加一行 `export PATH="$HOME/.local/bin:$PATH"   # macOS：uv 在 ~/.local/bin`，並加一行 `pnpm -C client build             # 前端（Windows 用 corepack pnpm -C client build）`。
6. 專案結構表 `docs/       計畫、階段規格與報告` → `docs/       計畫、階段規格與報告（archive/ 是歸檔）`。
7. （順手）守則 11「同時進行的 agent 最多 4 個」與交接 §6.2 第 5 點「開發 PM 自己最多 3 個、留 1 個給美術 PM」一致，不用改；守則 13 的例子可補 `pkill`／`killall`（Mac）。

## 5. 待 PM 決定

1. **LLM-1 是什麼**：派工說「LLM-1 進行中」，但 `docs/`、共用筆記資料夾（目前是空的）都找不到它的規格或報告；§2 寫成「本機 LLM 接線，專案 PM 2026-11-06 派，報告待寫」，內容請專案 PM 確認。
2. **MAC-2 標 ✅**：派工說「MAC-1／MAC-2 ✅」，`docs/archive/phases/PhaseMAC-2報告.md` 與 `0898b086` 都在 main，但 `docs/專案PM交接.md` 第 82 行仍寫「MAC-2 真模型驗收 → 全量 → push 進行中」。本檔 §2 與 3.1 第 3 點照派工標 ✅；若真模型驗收還沒做，請改回。
3. **原 3.3 的原文**：派工說「原 3.3 整節刪除」，我從交接文件刪了，但原文另存在 `docs/archive/交接歷史-開發PM.md` 末段（連同原 3.1、3.1.2）。要徹底刪請說。
4. **拿不準清單**（第 2 節標「搬」的 24 列，已寫進 3.1 第 4 點）：B-3W、B-3W-2（規則類）、B-3W-3、B6、B8、B10、B13、B17、B18、B21～B25、3-11 暫時障礙係數、2H 數值、結構型原語點數、AI 控場／位移使用率、trapper 擺位、築高台、火牆／定時炸彈、冰面與 bridge_chasm、`CONTROL_STATUSES`、build 合併建議、修正型被動生成、玩家配體質。多數是 Phase 2～3 時期的初值，大世界平衡時再決定要不要量；可整批交玩法 PM 砍。
5. `docs/phases/PhaseBAL計畫.md` 第 6、7、9、10 節標題寫「交接 3.00000 第 N 點」，現在指的是 `docs/archive/交接歷史-開發PM.md` 的 3.00000；不是我的檔，沒改。
6. §6.1 拿掉的 Windows「雲端模式（remote-devices）」說明：Mac 上 Remote Control 開不了 session（記憶筆記），且 Mac 的做法不同；要保留請從 archive（3.00、原 6.1 在 `21d25fe6` 之前的版本）撈。
7. `docs/archive/phases/README.md` 的索引沒有列 `docs/archive/交接歷史-開發PM.md`（那是 DOC-A 的檔，不在我的範圍）；CLAUDE.md 第 2 條建議已涵蓋。
