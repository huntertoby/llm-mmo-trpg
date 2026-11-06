# LLM-MMO-TRPG

由 LLM 擔任說書人的開放世界 MMO-TRPG：LLM 為每位玩家長出獨一無二、有主題、有協同的 build，多樣的格子戰場讓每個 build 都有發光的時刻。

## 目前進度（2026-11-06）

- 單人 roguelite 原型（Phase 0～4）與平衡階段（BAL）已完成；大世界第一版（Phase 5：地點、事件、組隊、經濟、Discord、賽季）已上線。
- **Phase 6「可走動的大世界」收尾中**（交易、種族、介面與美術打磨），之後是程式整理與 Phase 7。
- 測試：pytest 15217、vitest 3045（2026-11-06 全量）。各階段規格在 `docs/phases/`，已結案報告在 `docs/archive/phases/`。

## 安裝與執行

### macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # 安裝 uv（裝在 ~/.local/bin）
export PATH="$HOME/.local/bin:$PATH"
uv sync                                                   # 依 .python-version 準備 Python 3.12 與相依
uv run python scripts/check.py                            # ruff、格式、mypy、import-linter、pytest
npm install -g pnpm && pnpm -C client install && pnpm -C client build   # 前端（Node 沒有 corepack 時）
uv run trpg serve                                         # 本機伺服器（預設 8000 埠）
```

### Windows（PowerShell）

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # 安裝 uv，之後重開終端機
uv sync
uv run python scripts/check.py
corepack enable; corepack pnpm -C client install; corepack pnpm -C client build
uv run trpg serve
```

Git Bash 裡直接打 `python` 是 Windows Store 空殼，一律用 `uv run python`。對外開服、Tunnel、Discord Bot、備份與季末重置見 `docs/部署說明.md`。

### 試用 CLI

```bash
uv run trpg --help
uv run trpg content check
uv run trpg map show oil_depot
uv run trpg battle --map oil_depot --seed 42
uv run trpg battle --map swamp --seed 42 --weather fog --deploy "0,6;1,7"
uv run trpg battle --map test_heights_8x8 --seed 42 --log-json battle.json
uv run trpg battle replay battle.json
uv run trpg rng --seed 42 --count 5 --sides 20
```

## 文件索引

見 `CLAUDE.md` 的文件索引（總覽 `docs/專案計畫.md`、設計細節 `docs/design/`、各 PM 交接文件、階段規格 `docs/phases/`、歸檔 `docs/archive/`）。
