# Phase 6V-1 報告：主城功能型 NPC 外觀

實作者，2026-11-04。依據：美術 PM 偷懶自查 G7（`docs/art/偷懶自查.md`，在 `claude/art-pm-8f4e6d` 分支，main 上還沒有）、`docs/art/sample/capital-opening.html` 第 2 格（守印人：兜帽長袍、晶杖）、RT-4 的頭像做法。

## 1. 做了什麼

1. **內容資料**：
   - 4 位 NPC 的外觀放在原本情境物件的新欄位 `figure`：守印人、守池人、工坊師傅、書記。
   - `figure` 有 4 個欄位：
     - `portrait`：寫法同 NPC 人設卡（6C-7），頭像和地圖紙娃娃共用這一份；
     - `held`：主手拿的東西，例如晶杖、錘子；
     - `work`：待機動作，`smith`、`keeper` 或 `town`；
     - `facing`：朝向。
   - 檔案：`content/world/fields/capital/capital.yaml`、`interiors/capital_mentor_hall.yaml`。
2. **Schema**：
   - `src/trpg/content/fields.py` 新增 `FieldFigure`，以 pydantic 驗證，`portrait` 直接用 `NpcPortrait`。
   - 營火點、事件點填了 `figure` 會報錯，只有情境物件可以填。
3. **API**：
   - `FieldSituationObjectView` 新增 `figure`。
   - 已重新產生 `client/openapi.json` 和 `schema.d.ts`。
4. **地圖紙娃娃**：
   - 寫在 `fieldModel.ts` 和 `npcLook.figureFieldLook`。有 `figure` 的物件，在原本的格子上多畫一個我方紙娃娃，單位 ID 是 `figure_<id>`。
   - 不畫血條，種族外觀照頭像換算，朝向照內容。
   - 主手用紙娃娃的 `main_kind`、`main_material` 覆寫，沒拿東西時主手空著。原因見待決第 3 點。
5. **待機動作**：
   - 寫在 `fieldAmbient.ts`，身分照 `figure.work` 設定。
   - 工坊師傅是 `smith`，套 6N-10 的鐵匠打鐵動作，朝東面向靶場。
   - 其他三位是 `town`，用一般小動作。
6. **頭像**：
   - 寫在 `FieldThings.tsx`。情境物件說明卡的名稱前加一張 48px 頭像，和對話框同大小。
   - 框色：主城不在區域表裡，所以退回傭兵金。這和 hub 的金色主題一致。
7. **互動、規則不變**：
   - 這 4 位沒有改成 `npcs`。
   - 點了照舊開原本的東西：守印人開公告板，書記開技能，守池人、工坊師傅開說明卡。
   - 格子仍然可以走，沒有擋路。

四位的外觀：

| NPC | 外觀 |
|---|---|
| 守印人 | 照樣張：兜帽、深紫長袍金邊、白長髮、白鬍、晶杖，面向西 |
| 守池人 | 水色長袍、銀髮髻配青色髮帶、耳環、皺紋，副手拿一顆晶珠，面向池子 |
| 工坊師傅 | 皮衣、皮手套、壯碩、鬍子；頭像上有推到額頭的護目鏡和煤灰；拿錘子，待機打鐵 |
| 書記 | 深藍長袍金邊、短髮，副手捧魔導書 |

守印人以外的三位，樣張沒有畫，是我照「只換外觀」的原則自己配的。

## 2. 檔案清單

| 類別 | 檔案 |
|---|---|
| 內容 | `content/world/fields/capital/capital.yaml`、`content/world/fields/capital/interiors/capital_mentor_hall.yaml` |
| Python | `src/trpg/content/fields.py`、`src/trpg/api/world_field_schemas.py`、`src/trpg/api/world_field_things.py` |
| 前端 | `client/src/world/npcLook.ts`、`client/src/world/fieldModel.ts`、`client/src/world/fieldAmbient.ts`、`client/src/world/FieldThings.tsx`、`client/src/world/fieldThings.css`、`client/src/api/types.ts`、`client/openapi.json`、`client/src/api/schema.d.ts` |
| 測試 | `tests/world/test_capital_figures_6v1.py`（新檔，9 項）、`tests/content/test_field_buildings.py`（規則雜湊排除 `figure`）、`client/src/world/figures6v1.test.ts`（新檔，9 項） |
| 截圖 | `docs/art/6v1_01`～`6v1_08` |

## 3. 測試

- **Python**：
  - `trpg content check` 通過。
  - `tests/content`、`tests/world` 加上相關的 api 測試（`test_world_field_things`、`test_openapi_snapshot`、`test_newcomer_api_6f2`），共 3605 項。
  - 第一次跑有 5 項 `test_rule_content_unchanged` 失敗。原因是每個情境物件多了 `figure: null`，地圖的雜湊跟著變。
  - 修法：雜湊計算排除 `figure`，和排除物件 `look` 是同一個理由（只是外觀）。排除後主城和其他地圖的雜湊都和原本一致，表示規則內容沒變。
  - 修完重跑該檔，32 項全部通過。
  - ruff check、ruff format --check、mypy src（515 檔）、lint-imports（13 條）全部乾淨。
- **新的 Python 測試**：
  - 4 位都有外觀與頭像；
  - 格子、面板、`use` 和原本一樣；
  - 全遊戲只有這 4 個物件有 `figure`；
  - 不是 npcs，也不是設施；
  - 格子仍然可以走；
  - 錘子、晶杖、兜帽照資料；
  - 營火點填 `figure` 會被拒；
  - API 有把 `figure` 帶給前端。
- **前端**：
  - client 全部 vitest：225 個檔、2442 項通過。
  - `corepack pnpm -C client build` 結束碼 0。
- **新的 vitest**：
  - yaml 剛好 4 位，位置和面板照舊；
  - 頭像配件都畫得出來，框色是金色，畫法確定，4 張頭像彼此不同；
  - 地圖單位站在原格、沒有血條、朝向正確；
  - 主手是晶杖或錘子；守池人和書記主手空著，副手是晶珠或魔導書；
  - 工坊師傅的待機動作會出現打鐵；
  - 點那一格還是情境物件，提示文字照舊；
  - 說明卡有頭像，沒有人的物件（許願池）沒有頭像。

## 4. 截圖

在真的遊戲裡拍：

- 伺服器開在 8388 埠，存檔放 `scratchpad/v1/saves`；
- 無頭 Chrome 加 `--mute-audio`，CDP 埠 9388；
- 頁面網址加 `?mute=1`。

| 檔案 | 內容 |
|---|---|
| `6v1_01_capital_seal_pool` | 主城全景：守印人站在封印台旁、守池人站在許願池旁 |
| `6v1_02_pool_keeper_card` | 按 E 開守池人的說明卡，名稱前有頭像 |
| `6v1_03_workshop_master_card` | 工坊師傅的說明卡加頭像，地圖上可以看到他 |
| `6v1_04_scribe`、`6v1_04_scribe_zoom` | 技能導師殿裡的書記，捧著魔導書 |
| `6v1_05_seal_keeper_zoom` | 守印人放大：兜帽長袍、晶杖、白鬍 |
| `6v1_06_workshop_master_zoom` | 工坊師傅放大：舉錘子打鐵 |
| `6v1_07_pool_keeper_zoom` | 守池人放大：手拿晶珠，面向池子 |
| `6v1_08_portraits` | 4 位的頭像，96px 和 48px |

`6v1_08` 不是在遊戲裡拍的：用自己的 vite（5391 埠）直接呼叫 `drawPortrait` 畫出來，資料讀 yaml。原因是守印人、書記的頭像在遊戲裡沒有地方出現，見待決第 1 點。

拍完後，伺服器、vite、Chrome 都用自己的工作 ID 或 PID 結束了。

另外有一件事要說明：原本想把 vite 開在 5388，但那個埠已經有別人在用。我的截圖腳本誤連了一次那個頁面，只開啟、截圖，沒有任何操作。之後改用 5391。

## 5. noqa

沒有新增。

## 6. 待 PM 決定

1. **守印人和書記的頭像，遊戲裡看不到**：
   - 他們點了開的是共用的公告板、技能面板，面板上沒有「誰」的位置。
   - 開場對話（`OpeningDialog`）有守印人的台詞，但那是彈窗，6F-3 正在改，這段沒碰。
   - 建議 6F-3 之後在開場對話、公告板標題加頭像，資料可以直接用 `situation_objects[].figure.portrait`。
2. **人站的格子可以走**：
   - 情境物件格本來就可以站，主角走過時會和這 4 位疊在一起。
   - NPC 格會擋路，但擋路是規則變動，這段照規格不改。
   - 要擋的話，屬於規則段。
3. **既有 NPC 地圖上拿著劍（順手發現，沒改）**：
   - `npcFieldLook` 給 NPC 的武器 id 是 `unarmed`，紙娃娃查不到外觀，就退回近戰預設的劍。所以渡婆婆、柳掌櫃等人手上都有一把劍。
   - 這 4 位改用 `main_kind` 覆寫，沒拿東西時設 `none`，主手就空著。
   - 要不要讓既有 NPC 也這樣改，請美術 PM 決定，改法是一行。
4. **工坊師傅的護目鏡只在頭像上**：
   - `goggles_up` 沒有對應的紙娃娃頭部裝備，照 6C-7 的表，地圖上不畫。
   - 錘子用預設造型，因為 `held` 沒有 `form` 欄位。
5. **其他功能型 NPC 也沒有人**：
   - 殿主、酒館老闆、鐵匠、附魔師、傭兵管事是 facilities，地圖上也沒有人，例如導師殿截圖裡殿主那格是空的。
   - 這段照任務只做 4 位。G7 原文只列 4 位，這幾位要不要補，請美術 PM 決定。
6. **配色**：守池人、工坊師傅、書記樣張沒有畫，是我照 hub 主題配的。請美術 PM 看 `6v1_08` 確認。
7. **G8 不在這段範圍**：封印台、木人樁、整備亭仍是石柱和木箱。
