"""「他／她」掃描（Phase 6R-2，#137；09 9.6.10：稱謂一律中性）。

玩家角色不分性別：說書人對玩家說「你」，第三人稱用名字。這裡掃大世界的文字資料與伺服器端的字串常數
（不含 docstring 與註解），每個檔案的「他／她」個數要和白名單相同：白名單裡的都是指 **NPC**（人設、
事件骨架、情境、聊天內容）或 **技能目標單位**，不是玩家角色。新加的文字出現「他／她」時測試會失敗——
指玩家的請改成「你」或 ``{name}``；確定指 NPC 才更新白名單並寫理由。

不算的字：「其他」「他人」，以及規則本身寫的「『他』『她』」。技能文字（``content/skills``、原語說明、
工坊說明）指技能目標單位，不在掃描範圍（6R-2 待 PM 決定）。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Final

ROOT = Path(__file__).resolve().parents[2]
_PRONOUN = re.compile(r"(?<!其)[他她](?!人)")
_QUOTED = re.compile(r"「[他她]」")

YAML_SCOPES: Final = ("content/world", "content/llm", "content/ui")
YAML_FILES: Final = ("content/races.yaml", "content/origins.yaml")
PY_SCOPES: Final = (
    "src/trpg/world",
    "src/trpg/api",
    "src/trpg/narrative",
    "src/trpg/llm",
    "src/trpg/server",
)

WHITELIST: Final[dict[str, int]] = {
    # 事件骨架的誰、想要、阻礙、賭注：指事件裡的 NPC
    "content/world/events/ashen_waste.yaml": 4,
    "content/world/events/cloud_ridge.yaml": 12,
    # 人設卡（主線轉折）
    "content/world/npcs/ashen_waste.yaml": 1,
    # 情境模板與事實：指事件裡的 NPC
    "content/world/situations/ashen_waste.yaml": 3,
    "content/world/situations/cloud_ridge.yaml": 8,
    # NPC 聊天內容（傳聞、祕密）：指說話的 NPC
    "content/world/social/ashen_waste.yaml": 13,
    "content/world/social/cloud_ridge.yaml": 17,
    # 守護動作的說明：指被守護的隊友（技能目標單位）
    "src/trpg/narrative/action_info.py": 4,
}


def _count(text: str) -> int:
    return len(_PRONOUN.findall(_QUOTED.sub("", text)))


def _yaml_counts() -> dict[str, int]:
    paths = [p for s in YAML_SCOPES for p in sorted((ROOT / s).rglob("*.yaml"))]
    paths += [ROOT / f for f in YAML_FILES]
    out: dict[str, int] = {}
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        body = "\n".join(
            line.split(" #", 1)[0] for line in lines if not line.lstrip().startswith("#")
        )
        n = _count(body)
        if n:
            out[path.relative_to(ROOT).as_posix()] = n
    return out


def _docstrings(tree: ast.AST) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            found.add(id(node.value))
    return found


def _py_counts() -> dict[str, int]:
    out: dict[str, int] = {}
    for scope in PY_SCOPES:
        for path in sorted((ROOT / scope).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            docs = _docstrings(tree)
            n = sum(
                _count(node.value)
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docs
            )
            if n:
                out[path.relative_to(ROOT).as_posix()] = n
    return out


def test_he_she_only_where_whitelisted() -> None:
    found = {**_yaml_counts(), **_py_counts()}
    assert found == WHITELIST, (
        "「他／她」個數和白名單不同：指玩家角色的改成「你」或 {name}（#137），"
        "確定指 NPC 才更新 tests/content/test_pronoun_scan.py 的白名單"
    )


def test_scan_catches_pronoun() -> None:
    assert _count("這件他還拿不動。") == 1
    assert _count("其他人、他人與「他」「她」") == 0
