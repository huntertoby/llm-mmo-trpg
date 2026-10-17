# LLM-MMO-TRPG

由 LLM 擔任說書人的開放世界 MMO-TRPG：LLM 為每位玩家長出獨一無二、有主題、有協同的 build，多樣的格子戰場讓每個 build 都有發光的時刻。

## 目前進度

**Phase 1C：掩護系統與牆壁**（三層視線：全掩護／半掩護／隱蔽、牆壁地形、矮牆與倒木、掩護感知的效用 AI 與 AI 效能最佳化；4 張示範地圖，含 `ruined_fort`）。
Phase 1B 已完成環境與戰術（物件與表面、元素 × 標籤互動表、推擊／絆倒／互動、環境回合與預告、地圖事件、天氣、反應規則與暫停點、撤離與守點、部署、預覽、效用 AI）。
Phase 1A 已完成戰鬥核心（確定性規則引擎：狀態模型、地圖、先攻、AP、移動、判定、傷害、效果佇列、勝負）。
Phase 0 已完成基礎建設（專案骨架、程式品質工具、可種子化亂數產生器、共用型別、內容資料載入、CLI、CI）。
第一里程碑是單人 roguelite 原型（Phase 0–4），各階段內容見 `docs/專案計畫.md` 第 14 節。

## 在 Windows 上安裝與執行

1. 安裝 [uv](https://docs.astral.sh/uv/)（在 PowerShell 執行官方安裝指令）：

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   安裝後重新開啟終端機，確認 `uv --version` 可以執行。

2. 取得原始碼後，在專案根目錄安裝相依（uv 會依 `.python-version` 自動準備 Python 3.12）：

   ```powershell
   uv sync
   ```

3. 執行完整檢查（ruff、格式、mypy、import-linter、pytest）：

   ```powershell
   uv run python scripts/check.py
   ```

4. 試用 CLI：

   ```powershell
   uv run trpg rng --seed 42 --count 5
   uv run trpg rng --seed 42 --count 5 --sides 20
   uv run trpg content check
   uv run trpg map show test_heights_8x8
   uv run trpg battle --map test_heights_8x8 --seed 42
   uv run trpg map show oil_depot
   uv run trpg battle --map oil_depot --seed 42
   uv run trpg battle --map bridge_chasm --seed 42
   uv run trpg battle --map swamp --seed 42 --weather fog --deploy "0,6;1,7"
   uv run trpg battle --map test_heights_8x8 --seed 42 --log-json battle.json
   uv run trpg battle replay battle.json
   uv run trpg --version
   ```

macOS／Linux 的步驟相同，只有第 1 步改用 `curl -LsSf https://astral.sh/uv/install.sh | sh`。

## 文件索引

| 文件 | 用途 |
|---|---|
| `CLAUDE.md` | 實作守則、技術選型、專案結構、常用指令 |
| `docs/專案計畫.md` | 完整設計與開發階段（唯一的設計真相來源） |
| `docs/phases/` | 各階段的實作規格（`PhaseN計畫.md`）與完成報告（`PhaseN報告.md`） |
| `docs/archive/` | 舊版計畫，只供參考 |
| `content/README.md` | 內容資料夾的用途與規劃 |
