"""前端測試用的技能圖示資料（Phase 3-17）：內容庫的每個技能、隨機組合器的種子、工坊示範的每一步。

重產：``uv run python -m tests.narrative.icon_fixture``（寫到 ``client/src/render/fixtures/skill_icons.json``）；
``tests/narrative/test_skill_icon.py`` 檢查檔案是最新的。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.engine.helpers import library
from tests.skillgen.workshop_walks import DISPLACE, MODIFIER, STRIKE, walk_draft
from trpg.narrative.skill_icon import icon_of, skill_icon
from trpg.skillgen.random_composer import compose_random_skill

__all__ = ["FIXTURE_PATH", "build_fixture", "render"]

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "client"
    / "src"
    / "render"
    / "fixtures"
    / "skill_icons.json"
)
RANDOM_SEEDS = range(50)


def build_fixture() -> dict[str, Any]:
    lib = library()
    skills = {s.id: skill_icon(s).model_dump(mode="json") for s in lib.skills.values()}
    random = [
        skill_icon(compose_random_skill(seed, library=lib)).model_dump(mode="json")
        for seed in RANDOM_SEEDS
    ]
    workshop: dict[str, list[dict[str, Any]]] = {}
    for name, walk in (("strike", STRIKE), ("displace", DISPLACE), ("modifier", MODIFIER)):
        draft: dict[str, Any] = {}
        steps: list[dict[str, Any]] = []
        for _step, picks in walk:
            draft.update(picks)
            steps.append(icon_of(draft).model_dump(mode="json"))
        workshop[name] = steps
        assert walk_draft(walk) == draft
    return {"skills": skills, "random": random, "workshop": workshop}


def render() -> str:
    return (
        json.dumps(build_fixture(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )


if __name__ == "__main__":
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(render(), encoding="utf-8", newline="\n")
    print(f"wrote {FIXTURE_PATH}")
