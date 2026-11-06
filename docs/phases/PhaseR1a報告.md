# Phase R1a 報告：`engine/events.py` 按領域拆成子模組

依據：`docs/phases/整理提案-程式.md` 2.2 節 R1（使用者已同意）。分支 `dev/r1a`。

## 結果

`src/trpg/engine/events.py`（2,091 行）→ `src/trpg/engine/events/` 套件（共 2,506 行，多出的是各檔的 docstring 與 import）：

| 檔案 | 行數 | 內容 |
|---|---|---|
| `__init__.py` | 327 | 原模組 docstring＋子模組說明、re-export、原樣的 `__all__` |
| `base.py` | 52 | `EventBase`；跨領域型別別名 `AdvantageState`、`DamageCause`、`ObjectDestroyCause`、`MoveMode`、`SlideStopReason` |
| `flow.py` | 104 | 戰鬥流程（開戰、先攻、輪／回合、`EndReason`、結束） |
| `movement.py` | 184 | 移動、碰撞、墜落、致命地形 |
| `combat.py` | 342 | 命中、傷害、治療、護盾、狀態；技巧動作、推擊、反應 |
| `objects.py` | 279 | 物件、表面、地形；陷阱 |
| `skills.py` | 265 | 技能使用／追擊／觸發／堆疊／裝備；常駐傳說啟動、技能授予、賭博型 |
| `rules.py` | 264 | 源力與改寫規則型原語；形態、架勢、規則改寫、誓約 |
| `environment.py` | 84 | 環境回合、地圖事件、出現／撤離；Boss 階段、天氣 |
| `summons.py` | 198 | 召喚物、灌注、圖騰、引爆、推倒牆 |
| `zones.py` | 116 | 持續區域、符文 |
| `union.py` | 291 | `Event` discriminated union（成員順序與原檔相同）、`EVENT_ADAPTER`、`EVENT_LIST_ADAPTER` |

每檔 < 700 行。

## 做法

- 純搬移：用腳本依原檔行號切段，類別、型別別名、欄位、docstring、註解逐字保留（以 AST 比對：原檔 166 個頂層敘述除了被拆開的 import 外全部原樣出現在新檔）。只在沒有原段落標題的接合處補了段落標題註解。
- 每個子模組保留 `from __future__ import annotations`，執行期 import 用到的型別（pydantic 依模組全域解析註解）。子模組只依賴 `base`，`union` 依賴其他全部；沒有循環匯入、沒有新增 `noqa`。
- re-export：全專案 303 個引用檔實際從 `trpg.engine.events` 匯入 147 個名稱；原 `__all__` 148 個名稱全部 re-export。唯一不在 `__all__` 卻被匯入的 `InfusionFizzleReason` 用 `import X as X` 明確 re-export（`__all__` 不變）。共 re-export 149 個名稱（148＋1）。
- 呼叫端 import 一行都沒改；import-linter 契約沒動。

## 驗收

- `ruff check`、`ruff format --check`、`mypy`（1369 檔）、`lint-imports`（14 條契約 KEPT）：全過。
- `pytest -q tests/engine tests/cli/test_output_snapshots.py tests/world tests/narrative tests/api/test_openapi_snapshot.py -x -n 4`：5651 passed（CLI 快照與 `frozen_replay` 未重產）。
- 重播：`trpg battle --map swamp --seed 7` → `battle replay` 通過（88 個動作、313 個事件）。
- `scripts/export_openapi.py` 後 `client/openapi.json` 無差異（byte 相同）。

## 待 PM 決定

- `src/trpg/engine/forms.py` 等 docstring 用 `:data:\`~trpg.engine.events.FormLeaveReason\`` 這類路徑引用，透過 re-export 仍可解析，沒改。
- 子模組名稱（`rules`、`objects`）是依原檔段落命名的保守選擇；R3 抽葉模組時若要改名再一起處理。
