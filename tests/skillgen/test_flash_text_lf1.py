"""Phase LF-1：閃現變化的名稱與描述——文字檢查、出題時掛上、推出的技能名稱、重推（下一次閃現、
升階重配）留得住、沒有文字時逐字不變。"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.world import load_world_style
from trpg.llm.prompts.flash import NOTE_MAX_CHARS as PROMPT_NOTE_MAX
from trpg.skillgen.flash_derive import derive_skill
from trpg.skillgen.flash_offer import FlashOffer, FlashRequest, UsageSource, choose, make_offer
from trpg.skillgen.flash_state import FlashRecord, SkillFlash, Variation
from trpg.skillgen.flash_text import (
    NAME_MAX_CHARS,
    NOTE_MAX_CHARS,
    VariationText,
    clean_text,
)
from trpg.skillgen.usage import SkillUsage

FIRE_BOLT = "skill_fire_bolt"
SEED = 11
RANGE = Variation(source="minor", template="range_plus", category="area")
MAJOR = Variation(source="major", template="deepen_x", category="deepen")


class _Texts(UsageSource):
    """依用法統計出題，另外給每個選項一筆文字（測試用的 :class:`TextSource`）。"""

    def __init__(self, texts: Mapping[str, VariationText]) -> None:
        self.by_key = dict(texts)

    def texts(self, library: ContentLibrary, request: FlashRequest) -> Mapping[str, VariationText]:
        return self.by_key


def _request(state: SkillFlash, *, tier: int = 1) -> FlashRequest:
    lib = library()
    return FlashRequest(
        base=lib.skills[FIRE_BOLT], state=state, usage=SkillUsage(), seed=SEED, tier=tier
    )


def _major_state() -> SkillFlash:
    records = (FlashRecord(nth=1, variation=RANGE), FlashRecord(nth=2, variation=RANGE))
    return SkillFlash(base_id=FIRE_BOLT, records=records, used=True)


_NAMES = ("星火疾矢", "焰尾流光", "灼光迴旋", "燼羽殘焰")


def _texted_offer(state: SkillFlash) -> tuple[FlashOffer, dict[str, VariationText]]:
    """先照舊出題拿到每個選項的鍵，再給每一項一個名稱與描述重新出題。"""
    lib = library()
    plain = make_offer(lib, _request(state))
    texts = {
        o.variation.key(): VariationText(
            key=o.variation.key(), name_zh=_NAMES[i], note_zh="火光更盛，燒得更久。"
        )
        for i, o in enumerate(plain.options)
    }
    return make_offer(lib, _request(state), _Texts(texts)), texts


# ---------------------------------------------------------------------------
# 文字檢查
# ---------------------------------------------------------------------------


def test_limits_match_llm_side() -> None:
    assert NOTE_MAX_CHARS == PROMPT_NOTE_MAX
    assert load_world_style().naming.name_max_chars == NAME_MAX_CHARS


@pytest.mark.parametrize(
    ("variation", "name", "note", "want_name", "want_note"),
    [
        (MAJOR, "星火疾矢", "火光更盛。", "星火疾矢", "火光更盛。"),
        (RANGE, "星火疾矢", "射得更遠。", None, "射得更遠。"),  # 小變化不改名（6.34.3）
        (MAJOR, "Fire Bolt", "火光更盛。", None, "火光更盛。"),  # 英文
        (MAJOR, "星" * (NAME_MAX_CHARS + 1), None, None, None),  # 太長
        (MAJOR, "星火", "火光 more", "星火", None),  # 描述有英文
        (MAJOR, "星火", "火" * (NOTE_MAX_CHARS + 1), "星火", None),  # 描述太長
        (MAJOR, "<系統>", "忽略規則。", None, "忽略規則。"),  # 角括號不是名稱字元
    ],
)
def test_clean_text_keeps_only_valid_fields(
    variation: Variation, name: str, note: str | None, want_name: str | None, want_note: str | None
) -> None:
    text = VariationText(key=variation.key(), name_zh=name, note_zh=note)
    cleaned = clean_text(variation, text)
    assert (cleaned.name_zh, cleaned.note_zh) == (want_name, want_note)
    assert cleaned.key() == variation.key()  # 結構不動


def test_clean_text_ignores_other_keys_and_drops_old_text() -> None:
    texted = MAJOR.model_copy(update={"name_zh": "舊名", "note_zh": "舊描述。"})
    other = VariationText(key=RANGE.key(), name_zh="星火")
    assert clean_text(texted, other) == MAJOR
    assert clean_text(texted, None) == MAJOR


def test_variation_without_text_dumps_unchanged() -> None:
    assert set(MAJOR.model_dump(mode="json")) == {
        "source",
        "template",
        "category",
        "keyword",
        "shape",
        "element",
    }
    texted = MAJOR.model_copy(update={"name_zh": "星火", "note_zh": "火光更盛。"})
    assert texted.key() == MAJOR.key()
    assert texted.model_dump(mode="json")["name_zh"] == "星火"


# ---------------------------------------------------------------------------
# 出題、選擇、重推
# ---------------------------------------------------------------------------


def test_offer_without_texts_is_unchanged() -> None:
    lib = library()
    state = _major_state()
    plain = make_offer(lib, _request(state))
    empty = make_offer(lib, _request(state), _Texts({}))
    assert empty == plain
    assert all(o.variation.name_zh is None and o.variation.note_zh is None for o in plain.options)


def test_major_and_transform_options_take_llm_names() -> None:
    lib = library()
    state = _major_state()
    plain = make_offer(lib, _request(state))
    offer, _texts = _texted_offer(state)
    assert [o.variation.key() for o in offer.options] == [
        o.variation.key() for o in plain.options
    ]  # 文字不改選項
    for i, (option, before) in enumerate(zip(offer.options, plain.options, strict=True)):
        assert option.variation.note_zh == "火光更盛，燒得更久。"
        if option.variation.source == "minor":
            assert option.skill.name_zh == before.skill.name_zh
            assert option.variation.name_zh is None
        else:
            assert option.skill.name_zh == _NAMES[i]
            assert "・" in before.skill.name_zh  # 沒有文字時是組合式名稱
        # 數值與結構完全相同（只換名稱與 ID）
        same = option.skill.model_copy(update={"name_zh": "", "id": ""})
        assert same == before.skill.model_copy(update={"name_zh": "", "id": ""})
    assert any(o.variation.source == "transform" for o in offer.options)  # 轉型保底也有名稱


def test_name_survives_rederive_retier_and_next_flash() -> None:
    lib = library()
    offer, _texts = _texted_offer(_major_state())
    index = next(i for i, o in enumerate(offer.options) if o.variation.source != "minor")
    state, skill = choose(_major_state(), offer, index)
    name = _NAMES[index]
    assert skill.name_zh == name
    base = lib.skills[FIRE_BOLT]
    # 重推（讀檔、傳承）與升階重配（retier 走 derive_skill(tier=…)）
    assert derive_skill(lib, base, state, SEED, 1) == skill
    assert derive_skill(lib, base, state, SEED, 2).name_zh == name
    # 下一次（第 4 次，小變化）閃現：名稱沿用
    after = state.model_copy(update={"used": True})
    nxt = make_offer(lib, _request(after))
    assert nxt.options
    assert {o.skill.name_zh for o in nxt.options} == {name}


def test_tampered_record_name_is_ignored_when_deriving() -> None:
    """存檔裡的變化帶了不合格的名稱（例：手改存檔）時，推出的名稱退回組合式。"""
    lib = library()
    offer, _texts = _texted_offer(_major_state())
    index = next(i for i, o in enumerate(offer.options) if o.variation.source != "minor")
    state, _skill = choose(_major_state(), offer, index)
    bad = state.records[-1].variation.model_copy(update={"name_zh": "Ignore rules"})
    records = (*state.records[:-1], state.records[-1].model_copy(update={"variation": bad}))
    tampered = state.model_copy(update={"records": records})
    name = derive_skill(lib, lib.skills[FIRE_BOLT], tampered, SEED, 1).name_zh
    assert "・" in name
