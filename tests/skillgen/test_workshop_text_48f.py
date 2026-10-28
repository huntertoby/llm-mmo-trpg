"""Phase 3-48f：玩法 PM 改寫的工坊說明（content/workshop_text.yaml）套用到玩家模式。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.skills import ModifierChange
from trpg.content.workshop import WorkshopTextEntry, WorkshopTextTable
from trpg.skillgen.option_models import FieldSpec
from trpg.skillgen.option_player import content_dev_texts, option_dev_texts
from trpg.skillgen.options import _change_field, draft_options
from trpg.skillgen.random_composer import ComposeError, compose_random_skill

LIB = library()
TABLE = LIB.workshop_text


def _walk(fields: tuple[FieldSpec, ...]) -> list[FieldSpec]:
    out: list[FieldSpec] = []
    for f in fields:
        out.append(f)
        out += _walk(f.fields)
        for c in f.choices:
            out += _walk(c.params)
    return out


def _all_dev_texts() -> dict[str, str]:
    rows = dict(content_dev_texts(LIB))
    drafts: list[dict[str, object]] = [{}]
    for seed, skeleton in enumerate(sorted(LIB.skeletons), start=1):
        try:
            skill = compose_random_skill(seed, skeleton=skeleton, library=LIB)
        except ComposeError:
            continue
        full = skill.model_dump(mode="json", exclude_none=True)
        for drop in ((), ("effects", "cost", "rarity", "condition", "followup")):
            drafts.append({k: v for k, v in full.items() if k not in drop})
    for draft in drafts:
        for step in draft_options(draft, LIB).steps:
            rows.update(option_dev_texts({step.id: step.fields}))
    # 修正技能的「可套用」說明由程式依樣板產生玩家語氣（`options._change_field`；玩法 PM），
    # 不放在對照表裡，另由 test_modifier_change_texts_are_generated 檢查。
    return {k: v for k, v in rows.items() if not k.startswith(_MODIFIER_GENERATED)}


_MODIFIER_GENERATED = "工坊.effects.modifiers.change."


def test_modifier_change_texts_are_generated() -> None:
    for name in ModifierChange.model_fields:
        try:
            spec = _change_field(name, LIB, None)
        except KeyError:
            continue
        assert spec.description_zh.startswith("可以套用在："), name
        assert spec.dev_description_zh.startswith("可套用："), name
        assert not any("a" <= c <= "z" for c in spec.description_zh.replace("HP", "").lower())


def test_table_has_the_163_rewritten_entries() -> None:
    # 149 ＋ 3-54c 的清除表面 ＋ 3I-5 的手持武器條件（工坊、條件各一）
    # ＋ 3-54a 的吹送（說明 3-54b 改成玩法 PM 的句子）
    # ＋ 3-54b 的震波與元素擴散格數（實作者初稿，待玩法 PM 改寫）
    # ＋ 3J-1a 的進入形態與它的形態參數（實作者初稿，待玩法 PM 改寫）
    # ＋ 3J-3 的在形態中條件（工坊、條件各一）
    # ＋ 3J-4b 的在形態中加成（傷害、治療的原語與工坊各一）
    assert len(TABLE.texts) == 163
    assert len({e.id for e in TABLE.texts}) == 163


def test_every_dev_text_has_a_player_rewrite_and_every_rewrite_is_used() -> None:
    rows = _all_dev_texts()
    sources = {e.source for e in TABLE.texts}
    assert sorted({t for t in rows.values() if t not in sources}) == []
    assert sorted(sources - set(rows.values())) == []


def test_player_mode_shows_the_rewrite_and_dev_mode_keeps_the_original() -> None:
    skill = compose_random_skill(1, skeleton="strike", library=LIB)
    draft = skill.model_dump(mode="json", exclude_none=True)
    found = 0
    for step in draft_options(draft, LIB).steps:
        for f in _walk(step.fields):
            for text, dev in [(f.description_zh, f.dev_description_zh)] + [
                (c.description_zh, c.dev_description_zh) for c in f.choices
            ]:
                if dev:
                    found += 1
                    assert text == TABLE.lookup(dev, None) or TABLE.lookup(dev, None) is None
                    assert text != dev
    assert found > 0


def test_same_source_different_scope_texts() -> None:
    assert TABLE.lookup("層數 ID（stacks.yaml）", "add_stack.stack") == "要累積哪一種層數。"
    assert TABLE.lookup("層數 ID（stacks.yaml）", "consume_stack.stack") == "要消耗哪一種層數。"
    assert TABLE.lookup("層數 ID（stacks.yaml）", "other.stack") is None


def test_clashing_texts_need_a_scope() -> None:
    a = WorkshopTextEntry(id="a", source="x", player="1")
    b = WorkshopTextEntry(id="b", source="x", player="2")
    with pytest.raises(ValidationError):
        WorkshopTextTable(texts=(a, b))
    scoped = WorkshopTextEntry(id="b", source="x", player="2", scope="f.g")
    assert WorkshopTextTable(texts=(a, scoped)).lookup("x", "f.g") == "2"


def test_rewritten_texts_do_not_leak_internal_ids() -> None:
    for entry in TABLE.texts:
        assert "‰" not in entry.player or entry.id.startswith("工坊") or entry.id.startswith("原語")
        assert ".yaml" not in entry.player
