# Phase HC-2 計畫：量類寫死值跟著 quantity_scale

> 來源：`docs/phases/寫死數值-清單.md` 的 HC-2 節；`docs/phases/PhaseHC-1報告.md` 的開發 PM 裁定（第 3 點）；`docs/design/05-*.md` 5.4.1。
> 原則：**結果和現在等價**。這段只換寫法，不換數值：遊戲裡實際用到的數字不能變。
> 接在 X10-3d 合併之後。

## 範圍
1. **專查「量類預設 1」**：
   - 掃 `src/trpg/` 裡名稱帶 hp、mana、stamina、damage、heal、shield、armor、attr、flat 等字的欄位和參數，找出預設值是 1（或其他小整數）的。
   - 這些在 HC-1 因為「不列 1」而漏掉。
   - 逐筆判斷：是量類就列進 `classes.yaml` 的 scale todo，和下面一起改。
2. **content 的量類預設值與上下限**（清單 HC-2 a）：
   - 範圍：`rules.py`、`forms.py`、`battle.py`、`roguelite.py`。
   - YAML 有寫的欄位，拿掉程式預設值，改成必填。
   - 上下限改成 × `quantity_scale`，或交給 YAML 驗證。
3. **生成器和零星位置**（清單 HC-2 b、c）：
   - 生成器寫死的法力代價改乘 scale：`skillgen/flash_major.py`、`composer_recipes.py`。如果 X10-2b 已經改成 `scaled_cost`，就確認一下，再把歸類標成 done。
   - 零星位置：`engine/gear/core.py` 的 `_MAX_ATTR`、`engine/rules/statuses.py` 的 `DEFAULT_DEFENSE_BREAK`、`world/situation_coverage.py`、前端 `AttributeAllocator` 的 `?? 10`。

每處改完，把 `classes.yaml` 對應的項目從 todo 改成 done。

## 驗收
- **不變比對 different=0**：78 場戰鬥。另外跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`，夾具不應該變。
- 加一個測試：把 `quantity_scale` 設成 1 時，這些位置算出來的值要剛好是 10 時的 1/10，證明它們確實跟著倍率走。
- ruff、format、mypy、lint-imports、`trpg content check`、`classify.py --check` 都要是 0。
- 交件前所有目錄的非 slow 測試各跑一輪；前端有改的話，跑 tsc 和相關 vitest。
- 每項一個 commit。報告寫在 `docs/phases/PhaseHC-2報告.md`，列出每處改了什麼、todo 剩幾筆。
