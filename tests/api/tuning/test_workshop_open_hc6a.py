"""HC-6a：許願張數 ``pool.wish_cards`` 開進工坊（HC-5b 裁定 4），以及說明文字照資料組字。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

from pathlib import Path

from trpg.api.tuning.objects import note_text, object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import lookup
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import parse_path
from trpg.llm.prompts.wish_pick import build_wish_pick_messages, wish_pick_schema

CONTENT = bundled_content_dir()
PATH = "pool.wish_cards"


def _now(path: str) -> int:
    value = lookup(read_data(CONTENT / "skill_pick.yaml"), parse_path(path))
    assert isinstance(value, int)
    return value


def test_wish_cards_is_open_with_chinese_note(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "pick", "skill_pick")
    by_path = {f.path: f for f in detail.fields}
    field = by_path[PATH]
    assert field.value == _now(PATH)
    assert field.label_zh and not field.label_zh.isascii()
    assert "調高" in field.note_zh and "調低" in field.note_zh
    low, high = field.hint_min, field.hint_max
    assert low is not None and high is not None
    assert low <= _now(PATH) <= high
    paths = [f.path for f in detail.fields]
    assert paths.index(PATH) == paths.index("pool.wish_candidates") + 1  # 和候選量相鄰


def test_wish_cards_within_candidates_validates(read_service: TuningService) -> None:
    now = _now(PATH)
    item = TuningChangeIn(file="skill_pick.yaml", path=PATH, old=now, new=now + 1)
    result = read_service.check("hc6a-wish-cards", [item])
    assert result.ok, (result.field_errors, result.page_errors)


def test_wish_cards_over_candidates_is_refused(read_service: TuningService) -> None:
    now = _now(PATH)
    item = TuningChangeIn(
        file="skill_pick.yaml", path=PATH, old=now, new=_now("pool.wish_candidates") + 1
    )
    result = read_service.check("hc6a-wish-cards-over", [item])
    assert not result.ok


def test_wish_prompt_follows_the_card_count() -> None:
    """提示詞與 schema 的張數照 ``card_count``／``cards`` 寫（現值 3 時和以前逐字相同）。"""
    system = build_wish_pick_messages({}, {}, [], [], "x", card_count=4)[0]["content"]
    assert "從裡面挑 4 張不同的給玩家選" in system
    assert '{"cards": [四張]}' in system
    assert "3 張" not in system
    schema = wish_pick_schema(6, cards=4)
    cards = schema["properties"]["cards"]
    assert cards["minItems"] == cards["maxItems"] == 4


def test_neighbour_notes_follow_wish_cards(read_service: TuningService, tmp_path: Path) -> None:
    """HC-6b 第 4 項（HC-6a 裁定 1）：「候選量」「都不拿時退回」的說明照 ``wish_cards`` 組字。"""
    detail = object_detail(CONTENT, read_service.table, "pick", "skill_pick")
    notes = {f.path: f.note_zh for f in detail.fields}
    assert "打分後全部交給本機模型挑 3 張。" in notes["pool.wish_candidates"]
    world = object_detail(CONTENT, read_service.table, "world_rules", "rules")
    refund = next(f.note_zh for f in world.fields if f.path == "wish.refund_permille")
    assert refund.startswith("許願的三選一都不拿時，退還任務幣的這麼多千分比")
    text = (CONTENT / "skill_pick.yaml").read_text(encoding="utf-8")
    for cards, zh in ((2, "二"), (5, "五")):
        (tmp_path / "skill_pick.yaml").write_text(
            text.replace("wish_cards: 3 ", f"wish_cards: {cards} "), encoding="utf-8"
        )
        assert note_text("挑 {wish_cards} 張", tmp_path) == f"挑 {cards} 張"
        assert note_text("許願的{wish_cards_zh}選一", tmp_path) == f"許願的{zh}選一"
