# Phase 3-53b 報告｜中毒關鍵字小修

紀錄格式、存檔格式沒有改（`LOG_FORMAT` 不變）。

## 做了什麼

1. **開局隱藏中毒（資料旗標）**：`KeywordDef.start_hidden`（預設 `false`）；`content/skill_keywords.yaml` 的 `poisoned` 設 `start_hidden: true`（3-54c 補完毒種子技能後刪掉這行）。`KeywordTable.start_ids()` 回傳可在開局選的關鍵字，用在 `GET /api/runs/start-options`、`POST /api/runs/start-preview`、`default_start`（`run auto`／模擬抽樣）。三選一、工坊、關鍵字推導、`new_keyword_run` 的驗證都不看旗標（中毒仍是合法關鍵字，開發者／測試仍可直接指定）。
2. **橋接嫁接**：`content/skill_evolution.yaml` 的 `grafts.poisoned`：前綴「劇毒」、製造＝`apply_status poison` 2 回合、利用＝`target_has_status poison` 加傷（照 6.28 與另外 10 個關鍵字一致；召喚走自己的路徑不需要）。
3. **毒元素普攻詞條外觀**：`ELEMENT_KEYWORD` 加 `Element.POISON → poisoned`（`affix_attack_poison`、`affix_weapon_poison` 現在帶中毒圖樣）。`gearAppearance.json` 重產後**沒有差異**（該檔只含外觀表，詞條對應是執行期推導，`poisoned` 在 3-53 已在表中）。

## 測試

- 新增：開局選單沒有中毒但 `ids()` 仍有（api）、`default_start` 40 個種子都不含中毒（roguelite）、橋接可嫁接中毒且嫁接表涵蓋全部關鍵字（除召喚）（skillgen）、毒詞條推導出 `poisoned`（content）。
- pytest：content、skillgen、roguelite、narrative、api 共 4040 passed、1 skipped；`-m "slow or not slow" tests/cli --timeout=3000` 見下方「CLI」。
- vitest 990 passed、build 成功、ruff、format、mypy、lint-imports 通過。

## 待 PM 知悉

- `run auto` 的種子：中毒隱藏後，`default_start` 的候選回到 10 個（與 3-53 前相同），所以 3-53 後才改變的開局抽樣會回到原狀；CLI 快照結果見下。
- 3-54c 補齊毒種子技能後：刪 `start_hidden`、拿掉 3-53 留下的保守測試標記（`EXTRA_KEYWORDS`、`short == {"poisoned": 1}` 等）。
