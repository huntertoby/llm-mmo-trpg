"""Q-style skill icons (batch 4): export the data the sample page q-icons-parts.html reads.

Writes docs/art/sample/qPartsData.js with two things, both produced by the backend's own code
(read-only): the glossary (names of effects / conditions / triggers / statuses, same payload as
/api/glossary) and every skill's icon data (trpg.narrative.skill_icon.skill_icon, the payload
the client's render/skillIcon.ts paints from). Art sample tooling only; nothing imports this.

Usage (from the repo root):
    uv run python docs/art/sample/tools/qparts_export.py
"""

from __future__ import annotations

import json
from pathlib import Path

from trpg.api.glossary import build_glossary
from trpg.content.library import load_library
from trpg.narrative.skill_icon import skill_icon

OUT = Path(__file__).resolve().parents[1] / "qPartsData.js"


def main() -> int:
    library = load_library()
    glossary = json.loads(build_glossary(library).model_dump_json())
    icons = {
        skill_id: json.loads(skill_icon(skill).model_dump_json())
        for skill_id, skill in sorted(library.skills.items())
    }
    head = "// 由 tools/qparts_export.py 匯出（Q 版小圖示第 4 批樣張用；不要手改）\n"
    body = (
        f"window.QPARTS_GLOSSARY = {json.dumps(glossary, ensure_ascii=False)};\n"
        f"window.QPARTS_ICONS = {json.dumps(icons, ensure_ascii=False)};\n"
    )
    OUT.write_text(head + body, encoding="utf-8")
    print(f"{len(icons)} skills -> {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
