"""選變體畫面（FL-1b）的開發頁與 vitest 夾具：``client/src/dev/fixtures/flashChoice.json``。

用法::

    uv run python scripts/export_flash_choice_fixture.py

點燃斬（白板 ``kindle``，使用者截圖那組：AP 2、耐力 2、冷卻 2、射程 4、燃燒 5 回合）第 1 次閃現
的幾組選項，
``changes``、``headline_zh``、``say_zh``、``terms`` 都是伺服器同一套函式算的（不是手寫）：

- ``base``：使用者截圖那四個（射程 +1、蓄力、積水、撞擊加碼）；
- ``rows``：雙槍連射（列數多的一組：輕巧一升一降、多打一下、換形狀、蓄力）；
- ``transform``：第 3 次大變化，轉成反應且被動欄滿了（卸下選單的三招是示意：主角夾具裡的招）；
- ``stance``：轉成姿態、姿態欄已有一招（自動換下，不出選單）。

主角（``hero``）沿用 ``client/src/run/fixtures/run_campfire.json``，第一招換成點燃斬。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from trpg.api.flash_changes import base_stats, flash_changes
from trpg.api.flash_text import (
    FlashTextContext,
    base_terms,
    flash_terms,
    option_headline,
    option_say,
    option_tag_term,
    term_ids,
)
from trpg.api.run_schemas import FlashOptionOut, PendingFlashOut
from trpg.api.skill_cards import skill_card
from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef
from trpg.narrative.skills import CardOwner
from trpg.skillgen.flash_derive import derive_skill
from trpg.skillgen.flash_state import Variation, acquire, with_flash
from trpg.skillgen.whiteboard import compose_whiteboard

ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / "client" / "src" / "run" / "fixtures" / "run_campfire.json"
OUT = ROOT / "client" / "src" / "dev" / "fixtures" / "flashChoice.json"
SEED = 12345
ATTR = 10

SETS: dict[str, list[tuple[str, str, str, str | None]]] = {
    "base": [
        ("minor", "range_plus", "area", None),
        ("minor", "cost_charge", "cost", None),
        ("minor", "keyword_imbue", "element", "wet"),
        ("minor", "keyword_exploit", "element", "collision"),
    ],
    "rows": [
        ("minor", "cost_light", "cost", None),
        ("minor", "multi_hit", "combo", None),
        ("minor", "reshape_shape", "area", None),
        ("minor", "cost_charge", "cost", None),
    ],
    "transform": [
        ("minor", "cost_light", "cost", None),
        ("minor", "range_plus", "area", None),
        ("minor", "keyword_imbue", "element", "wet"),
        ("transform", "to_reaction_melee", "transform", None),
    ],
    "stance": [
        ("minor", "cost_light", "cost", None),
        ("minor", "range_plus", "area", None),
        ("minor", "keyword_imbue", "element", "wet"),
        ("transform", "to_stance", "transform", None),
    ],
}
BASES = {"rows": "skill_akimbo_burst"}
"""其他組用點燃斬。"""


def _card(library: ContentLibrary, skill: SkillDef) -> dict[str, Any]:
    weapon = library.weapons.get("one_handed_sword")
    owner = CardOwner(weapon=weapon, attr_get=lambda _a: ATTR)
    return skill_card(library, skill, owner=owner).model_dump(mode="json")


def _pending(
    library: ContentLibrary, base: SkillDef, picks: list[tuple[str, str, str, str | None]], nth: int
) -> tuple[dict[str, Any], list[SkillDef]]:
    ctx = FlashTextContext(weapon=library.weapons.get("one_handed_sword"), attr=lambda _a: ATTR)
    terms = base_terms(base, skill_card(library, base))
    stats = base_stats(library, base)
    terms += [s.term for s in stats if s.term is not None]
    options = []
    afters = []
    for index, (source, template, category, keyword) in enumerate(picks):
        variation = Variation(source=source, template=template, category=category, keyword=keyword)  # type: ignore[arg-type]
        state = with_flash(acquire(base.id), variation)
        after = derive_skill(library, base, state, SEED + index, tier=1)
        afters.append(after)
        changes = flash_changes(library, base, after, keyword=keyword)
        headline = option_headline(library, variation, after, changes)
        say = option_say(library, variation, after, changes)
        tag = option_tag_term(library, variation)
        terms += [*term_ids(headline), *term_ids(say), *([] if tag is None else [tag])]
        for row in changes:
            terms += [*term_ids(row.before_zh), *term_ids(row.after_zh)]
            terms += [] if row.term is None else [row.term]
        summary = template
        found = library.flash.minor_template(template) or library.flash.transform_template(template)
        if found is not None:
            summary = found.summary_zh
        category_zh = "轉型" if source == "transform" else library.flash.category(category).name_zh
        options.append(
            FlashOptionOut.model_validate(
                {
                    "index": index,
                    "source": source,
                    "category": category,
                    "category_zh": category_zh,
                    "template": template,
                    "summary_zh": summary,
                    "transform": source == "transform",
                    "card": _card(library, after),
                    "changes": [c.model_dump() for c in changes],
                    "headline_zh": headline,
                    "say_zh": say,
                    "tag_term": tag,
                }
            )
        )
    pending = PendingFlashOut(
        skill_id=base.id,
        nth=nth,
        slot=None,
        category=None,
        major=nth == library.flash.rules.major_flash,
        cost=1,
        options=tuple(options),
        base_stats=stats,
        terms=flash_terms(library, base, terms, ctx),
    )
    return pending.model_dump(mode="json"), afters


def main() -> int:
    library = load_library()
    base = compose_whiteboard(75, recipe_id="kindle", weapon_class="melee", tier=1, library=library)
    hero = json.loads(HERO.read_text(encoding="utf-8"))["hero"]
    hero["skills"] = [_card(library, base), *hero["skills"][1:]]
    hero["insight"] = 3
    out: dict[str, Any] = {"hero": hero, "sets": {}}
    for key, picks in SETS.items():
        skill = base if key not in BASES else library.skills[BASES[key]]
        pending, _ = _pending(library, skill, picks, 3 if key in ("transform", "stance") else 1)
        out["sets"][key] = pending
    out["bases"] = {key: _card(library, library.skills[sid]) for key, sid in BASES.items()}
    passives = [s["id"] for s in hero["skills"] if s["kind_id"] == "passive"]
    others = [s["id"] for s in hero["skills"][1:] if s["kind_id"] == "active"][:2]
    for key, slot, ids in (
        ("transform", "reaction", [*passives, *others][:3]),
        ("stance", "stance", others[:1]),
    ):
        for option in out["sets"][key]["options"]:
            if option["transform"]:
                option["unequip_candidates"] = ids  # 示意：被動欄滿了／姿態欄只有 1 格（自動換下）
                option["unequip_slot"] = slot
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"已寫入 {OUT.relative_to(ROOT).as_posix()}", file=sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
