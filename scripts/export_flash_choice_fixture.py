"""選變體畫面（FL-1b）的開發頁與 vitest 夾具：``client/src/dev/fixtures/flashChoice.json``。

用法::

    uv run python scripts/export_flash_choice_fixture.py

點燃斬（白板 ``kindle``，使用者截圖那組：AP 2、耐力 2、冷卻 2、射程 4、燃燒 5 回合）第 1 次閃現
的幾組選項，
``changes``、``headline_zh``、``say_zh``、``terms`` 都是伺服器同一套函式算的（不是手寫）：

- ``base``：使用者截圖那四個（射程 +1、蓄力、積水、撞擊加碼）；
- ``rows``：雙槍連射（列數多的一組：輕巧一升一降、多打一下、換形狀、蓄力）；
- ``transform``：第 3 次大變化，轉成反應且被動欄滿了（卸下選單的三招是示意：主角夾具裡的招）；
- ``stance``：轉成姿態、姿態欄已有一招（自動換下，不出選單）；
- ``llm``（LF-3）：點燃斬閃過兩次（射程 +1、蓄力）後的第 3 次大變化，**真的出題**
  （``make_offer``，2 階），變化帶 LLM 的名稱與一句話描述（字照 LF-1 報告第 3 節本機模型的
  輸出改寫成這招的效果）；第 3 個只有描述、名稱退回組合式（命名不合格時的樣子）。

主角（``hero``）沿用 ``client/src/run/fixtures/run_campfire.json``，第一招換成點燃斬。
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from trpg.api.flash_changes import base_stats, flash_changes
from trpg.api.flash_text import (
    FlashTextContext,
    base_terms,
    flash_terms,
    option_headline,
    option_llm_text,
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
from trpg.skillgen.flash_offer import (
    DataOrderSource,
    FlashRequest,
    make_offer,
    skill_before,
)
from trpg.skillgen.flash_state import Variation, acquire, with_flash
from trpg.skillgen.flash_text import VariationText
from trpg.skillgen.usage import SkillUsage
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

LLM_PRIOR = (
    Variation(source="minor", template="range_plus", category="area"),
    Variation(source="minor", template="cost_charge", category="cost"),
)
"""``llm`` 組之前閃過的兩次（大變化在第 3 次）。"""
LLM_TEXTS: tuple[tuple[str | None, str | None], ...] = (
    ("雲嶺燎原", "霧水沾身的敵人，火勢趁隙燒得更深。"),
    ("竹影焚心", "山霧鎖住熱氣，點燃的火更難熄滅。"),
    (None, "雲氣匯聚，帶電的敵人挨這一斬格外吃痛。"),
    ("赤焰立姿", "以長劍為引，將火焰凝於自身，進入燃燒的架勢。"),
)
"""``llm`` 組依出題順序的（名稱，描述）；``None`` ＝ 沒有（名稱退回組合式）。"""


class _TextedSource(DataOrderSource):
    """資料順序出題，另外給文字（LF-1 的 ``TextSource``）。"""

    def __init__(self, texts: Mapping[str, VariationText]) -> None:
        self._texts = texts

    def texts(self, library: ContentLibrary, request: FlashRequest) -> Mapping[str, VariationText]:
        del library, request
        return self._texts


def _card(library: ContentLibrary, skill: SkillDef) -> dict[str, Any]:
    weapon = library.weapons.get("one_handed_sword")
    owner = CardOwner(weapon=weapon, attr_get=lambda _a: ATTR)
    return skill_card(library, skill, owner=owner).model_dump(mode="json")


def _pending_out(
    library: ContentLibrary,
    skill_id: str,
    before: SkillDef,
    items: Sequence[tuple[Variation, SkillDef, str]],
    nth: int,
) -> dict[str, Any]:
    """（變化，套用後的技能，``summary_zh``）→ ``PendingFlashOut``（伺服器同一套函式）。"""
    ctx = FlashTextContext(weapon=library.weapons.get("one_handed_sword"), attr=lambda _a: ATTR)
    terms = base_terms(before, skill_card(library, before))
    stats = base_stats(library, before)
    terms += [s.term for s in stats if s.term is not None]
    options = []
    for index, (variation, after, summary) in enumerate(items):
        changes = flash_changes(library, before, after, keyword=variation.keyword)
        headline = option_headline(library, variation, after, changes)
        say = option_say(library, variation, after, changes)
        tag = option_tag_term(library, variation)
        note, name_source = option_llm_text(variation, after)
        terms += [*term_ids(headline), *term_ids(say), *([] if tag is None else [tag])]
        for row in changes:
            terms += [*term_ids(row.before_zh), *term_ids(row.after_zh)]
            terms += [] if row.term is None else [row.term]
        source = variation.source
        category_zh = (
            "轉型" if source == "transform" else library.flash.category(variation.category).name_zh
        )
        options.append(
            FlashOptionOut.model_validate(
                {
                    "index": index,
                    "source": source,
                    "category": variation.category,
                    "category_zh": category_zh,
                    "template": variation.template,
                    "summary_zh": summary,
                    "transform": source == "transform",
                    "card": _card(library, after),
                    "changes": [c.model_dump() for c in changes],
                    "headline_zh": headline,
                    "say_zh": say,
                    "tag_term": tag,
                    "note_zh": note,
                    "name_source": name_source,
                }
            )
        )
    pending = PendingFlashOut(
        skill_id=skill_id,
        nth=nth,
        slot=None,
        category=None,
        major=nth == library.flash.rules.major_flash,
        cost=1,
        options=tuple(options),
        base_stats=stats,
        terms=flash_terms(library, before, terms, ctx),
    )
    return pending.model_dump(mode="json")


def _pending(
    library: ContentLibrary, base: SkillDef, picks: list[tuple[str, str, str, str | None]], nth: int
) -> dict[str, Any]:
    items = []
    for index, (source, template, category, keyword) in enumerate(picks):
        variation = Variation(source=source, template=template, category=category, keyword=keyword)  # type: ignore[arg-type]
        state = with_flash(acquire(base.id), variation)
        after = derive_skill(library, base, state, SEED + index, tier=1)
        summary = template
        found = library.flash.minor_template(template) or library.flash.transform_template(template)
        if found is not None:
            summary = found.summary_zh
        items.append((variation, after, summary))
    return _pending_out(library, base.id, base, items, nth)


def _llm_pending(library: ContentLibrary, base: SkillDef) -> dict[str, Any]:
    """第 3 次大變化真的出題，文字照 :data:`LLM_TEXTS` 依出題順序掛上（引擎 ``clean_text``）。"""
    state = acquire(base.id)
    for variation in LLM_PRIOR:
        state = with_flash(state, variation)
    state = state.model_copy(update={"used": True})
    request = FlashRequest(base=base, state=state, usage=SkillUsage(), seed=SEED, tier=2)
    plain = make_offer(library, request)
    texts = {
        o.variation.key(): VariationText(key=o.variation.key(), name_zh=name, note_zh=note)
        for o, (name, note) in zip(plain.options, LLM_TEXTS, strict=False)
    }
    offer = make_offer(library, request, _TextedSource(texts))
    items = [(o.variation, o.skill, o.summary_zh) for o in offer.options]
    return _pending_out(library, base.id, skill_before(library, request), items, offer.nth)


def main() -> int:
    library = load_library()
    base = compose_whiteboard(75, recipe_id="kindle", weapon_class="melee", tier=1, library=library)
    hero = json.loads(HERO.read_text(encoding="utf-8"))["hero"]
    hero["skills"] = [_card(library, base), *hero["skills"][1:]]
    hero["insight"] = 3
    out: dict[str, Any] = {"hero": hero, "sets": {}}
    for key, picks in SETS.items():
        skill = base if key not in BASES else library.skills[BASES[key]]
        out["sets"][key] = _pending(
            library, skill, picks, 3 if key in ("transform", "stance") else 1
        )
    out["sets"]["llm"] = _llm_pending(library, base)
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
