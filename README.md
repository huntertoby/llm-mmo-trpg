# LLM-MMO-TRPG

由 LLM 擔任說書人的開放世界 MMO-TRPG：LLM 為每位玩家長出獨一無二、有主題、有協同的 build，多樣的格子戰場讓每個 build 都有發光的時刻。

## 目前進度

**Phase 0：基礎建設**（專案骨架、程式品質工具、可種子化亂數產生器、共用型別、內容資料載入、最小 CLI、CI）。
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
