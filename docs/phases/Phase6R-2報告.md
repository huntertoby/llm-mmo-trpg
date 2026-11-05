# Phase 6R-2 報告（中途收尾，WIP）

> 實作者：worktree 分支 `worktree-agent-aae0ccf14bc44eab2`（從 `2457e3f2` 開始）。使用者要重開電腦，依專案 PM 指示中途收尾。沒有 push、沒有合併。

## 1. 做到哪裡

只做完閱讀與盤點，**還沒有改任何程式或內容檔**。盤點結果（給下一位實作者）：

- **玩家外觀的資料流**：角色存檔 `CharacterState.hero`（`UnitTemplate`）的 `doll`（`DollLook`，`src/trpg/content/battle.py`）→ 戰鬥單位 `unit.doll` → `UnitView.doll_look`；前端 `client/src/render/appearance.ts` 的 `resolveDoll` 先用 `doll_look`，再用 `UnitView.race.look`（種族預設，`inkRace.ts` 的 `raceLookToLook`）蓋掉膚色、髮型、髮色、眼色、鬍子、體型。所以玩家的選擇必須在種族外觀**之後**套上。
- **建議做法**：在 `content/battle.py` 加 `LookChoice`（face、eye_style、lashes、eyes、hair〔含 bob／ponytail／twin／spiky〕、hair_color、skin、beard〔none／stubble／mustache／goatee／full〕、frame、beast_ears，全部選填），`DollLook` 加選填 `custom: LookChoice | None`；`races.py` 的 `RaceDef` 加 `look_options`（沒有時由 `look` 推出預設），載入時驗證種族預設值在清單內；前端 `resolveDoll` 在種族外觀之後套 `custom`。
- **限制表色票**：`docs/art/sample/appearance-vary.html` 第 87～96 行的 `RULE`（各族膚色、髮型、髮色、鬍子）、第 66～67 行 `HAIRC`／`EYEC`、第 79 行快速組合 `PRESET`。注意人類預設髮色 `#6a3d1e` 不在 `HAIRC` 裡，要補進人類清單。
- **建角畫面**：`client/src/world/WorldCharacterPicker.tsx`＋`client/src/run/RaceOriginPicker.tsx`；預覽框目前不畫人物（UI-E1 留給 Q 版）。外觀步驟要看得到效果，建議用現有 `paperdoll.ts` 的 `drawFigurePose`＋`resolveDoll` 畫在預覽框（現有部件，待 PM 確認）。
- **主城改外觀**：照 6R-1 的 `change_race`（`src/trpg/world/race_change.py`、`world/actions.py`、`client/src/world/RaceChange.tsx`）加 `change_look` 動作。換種族時的外觀保留規則在 `src/trpg/server/chronicle.py` 的 `legacy_doll`（5F-3c 代決，要改成看 `look_options`）。
- **一般敵人**：內容裡的敵人範本都沒有 `race`，且 `doll` 都寫滿了膚色與髮型；頭目可用 `tags: boss`、`doll.rarity` 判斷。建議前端只在敵方、非召喚、非異形、非頭目時以 id 的 FNV-1a 雜湊在人類範圍挑（髮髻、光頭當成身分特徵保留），待 PM 確認。
- **「他／她」掃描（草稿腳本在 scratchpad，未 commit）**：排除「其他」「他人」後，`content/world/**`、`content/llm/*`、`races.yaml` 與 `src/trpg` 的非 docstring 字串共 59 處。大多指 NPC（事件骨架、聊天內容、郵差台詞「這件他還拿不動」指收件人＝玩家角色，**要改**）、技能說明指目標單位（`action_info.py`、`rule_changes.py`、`option_params.py`）。narration／戰報／編年史／公告板模板本身沒有看到寫死的玩家「他／她」，但郵差 `trade.yaml` 三句與事件文字要逐條判斷。

## 2. 還沒做的項目

全部交付項目都還沒做：#137 外觀 1～4、中性稱謂 5～7（`address.yaml`、`{name}`／`{address}` 佔位符、掃描測試與白名單、LLM 系統指令與 `player: {name, address}`、升提示詞版號、離線評估）、版號 8、快照 9、6R-1 補拍 10～11、所有截圖、6.5.1 浮動卡實測、交件檢查。

## 3. 下一步

照第 1 節的建議做法從資料層開始：`LookChoice`／`look_options`＋驗證測試 → 建角 API 收 `look` → `change_look` 動作 → 前端外觀步驟 → 稱謂與 LLM → 版號與快照 → 截圖。

## 4. 版號與快照

- `WORLD_RULES_VERSION` 仍是 20、`CHAR_FORMAT` 仍是 `trpg-char/10`，**都沒升**。
- 快照、`client/openapi.json`、`schema.d.ts` **都沒重產**。

## 5. 程序

沒有啟動任何伺服器或背景程序（只在 worktree 跑過一次 `uv sync` 建 `.venv`，已結束）。
