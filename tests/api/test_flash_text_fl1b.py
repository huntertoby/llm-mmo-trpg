"""FL-1b：選變體畫面的字（欄位名與單位、大標、下固定區的一句話、說明卡）。

依據 ``docs/art/靈感閃現選擇-移植需求.md`` 8、9；說明卡的數字照資料填（不寫死）。
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.engine.helpers import library as _load_library
from trpg.api.flash_changes import base_stats, flash_changes, ratio_zh
from trpg.api.flash_text import (
    FlashTextContext,
    flash_terms,
    option_headline,
    option_say,
    option_tag_term,
    say_from_changes,
    term_ids,
)
from trpg.api.llm_source import MockLlmProvider
from trpg.api.run_schemas import StatChangeOut
from trpg.api.runs import RunStore
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite import auto_play
from trpg.roguelite.state import GearOfferNode
from trpg.shared.types import Surface
from trpg.skillgen.flash_derive import derive_skill
from trpg.skillgen.flash_state import Variation, acquire, with_flash
from trpg.skillgen.whiteboard import compose_whiteboard

LIB = _load_library()
SEED = 12345
KINDLE = compose_whiteboard(75, recipe_id="kindle", weapon_class="melee", tier=1, library=LIB)
"""點燃斬（使用者截圖那組：射程 4、冷卻 2、燃燒 5 回合）。"""


def _option(template: str, category: str, keyword: str | None = None) -> tuple[Variation, SkillDef]:
    variation = Variation(source="minor", template=template, category=category, keyword=keyword)
    state = with_flash(acquire(KINDLE.id), variation)
    return variation, derive_skill(LIB, KINDLE, state, SEED, tier=1)


def _rows(template: str, category: str, keyword: str | None = None) -> list[StatChangeOut]:
    _, after = _option(template, category, keyword)
    return list(flash_changes(LIB, KINDLE, after, keyword=keyword))


def _view(row: StatChangeOut) -> tuple[str, str | None, str | None, str]:
    return (row.name_zh, row.before_zh, row.after_zh, row.direction)


def test_ratio_wording() -> None:
    """9.1 #3：整成寫「3 成」、不整寫「35%」、1 以上寫「1.35 倍」。"""
    assert ratio_zh(300) == "3 成"
    assert ratio_zh(350) == "35%"
    assert ratio_zh(1350) == "1.35 倍"
    assert ratio_zh(1000) == "1 倍"


def test_the_four_user_options_read_like_the_spec() -> None:
    """9.3 的四個選項：欄位名、單位、方向照資料。"""
    assert [_view(r) for r in _rows("range_plus", "area")] == [("射程", "4 格", "5 格", "better")]
    assert [_view(r) for r in _rows("cost_charge", "cost")] == [
        ("冷卻", "2 回合", "4 回合", "cost"),
        ("燃燒", "5 回合", "6 回合", "better"),
    ]
    water = _rows("keyword_imbue", "element", "wet")
    assert [_view(r) for r in water] == [
        ("地面", None, "[[surface:water|積水]]，[[makes|會造成]] {{kw:wet}}[[kw:wet|潮濕]]", "new")
    ]
    bump = _rows("keyword_exploit", "element", "collision")
    assert [_view(r) for r in bump] == [
        (
            "額外傷害",
            None,
            "3 成[[weapon_damage:300|武器傷害]]（目標這回合被[[kw:collision|撞過]]才有）",
            "new",
        )
    ]


def test_icons_and_terms_of_rows() -> None:
    charge = _rows("cost_charge", "cost")
    assert [(r.icon and (r.icon.kind, r.icon.cat, r.icon.id)) for r in charge] == [
        ("part", "card", "cooldown"),
        ("status", None, "burning"),
    ]
    assert [r.term for r in charge] == ["cooldown", "status:burning"]


def test_light_has_one_up_one_down() -> None:
    """11 #4：輕巧 AP 2 → 1、燃燒 5 → 2（一升一降）。"""
    rows = {r.name_zh: _view(r) for r in _rows("cost_light", "cost")}
    assert rows["AP"] == ("AP", "2", "1", "cost")
    assert rows["燃燒"][3] == "worse"


def test_removed_effect_reads_none_and_worse() -> None:
    """12 決定 5：拿掉的效果「後」為 None（畫面寫「沒有」），照 worse。"""
    _, grown = _option("keyword_imbue", "element", "wet")
    rows = flash_changes(LIB, grown, KINDLE)
    assert [_view(r) for r in rows] == [("地面", "[[surface:water|積水]]", None, "worse")]


def test_headlines_of_the_five_first_filled_ones() -> None:
    """8.2：FL-1b 先填的 5 條（FL-1f 其他模板也填了，見 ``test_flash_text_fl1f.py``）。"""
    cases = {
        ("range_plus", "area", None): "射程變遠 1 格",
        ("cost_charge", "cost", None): "多等幾回合再用，換這招變強",
        ("cost_light", "cost", None): "省一點代價，這招弱一點",
        ("keyword_imbue", "element", "wet"): "打中的格子還會積水",
        ("keyword_exploit", "element", "collision"): "敵人剛被撞過，這招多傷一截",
    }
    for (template, category, keyword), want in cases.items():
        variation = Variation(source="minor", template=template, category=category, keyword=keyword)
        assert option_headline(LIB, variation, KINDLE, ()) == want, template


def test_say_lines() -> None:
    """9.3 下固定區：第 1、3、4 個照模板；第 2 個（蓄力）照差異清單組（玩法 PM 11-13 原句）。"""
    expect = {
        ("range_plus", "area", None): "[[shape:cross|十字範圍]]照舊，中心最遠可以放到 5 格外。",
        ("cost_charge", "cost", None): "用過之後要等 4 回合才能再用（原本 2），燃燒多 1 回合。",
        ("keyword_imbue", "element", "wet"): (
            "打中時，[[shape:cross|十字範圍]]的 5 格地上會[[surface:water|積水]]；"
            "站在水上的敵人之後被雷電打會傳導、被冰霜打會結凍。"
        ),
        ("keyword_exploit", "element", "collision"): (
            "目標這回合被推去[[kw:collision|撞過]]牆或別人時，"
            "這招對它多 3 成[[weapon_damage:300|武器傷害]]。"
        ),
    }
    for (template, category, keyword), want in expect.items():
        variation, after = _option(template, category, keyword)
        changes = flash_changes(LIB, KINDLE, after, keyword=keyword)
        assert option_say(LIB, variation, after, changes) == want, template


def test_say_from_changes_light() -> None:
    assert say_from_changes(_rows("cost_light", "cost")) == (
        "只要 1 AP（原本 2），用過之後要等 1 回合才能再用（原本 2），燃燒少 3 回合。"
    )


def test_tag_terms_for_charge_and_light() -> None:
    charge = Variation(source="minor", template="cost_charge", category="cost")
    light = Variation(source="minor", template="cost_light", category="cost")
    other = Variation(source="minor", template="range_plus", category="area")
    assert option_tag_term(LIB, charge) == "power_up"
    assert option_tag_term(LIB, light) == "power_down"
    assert option_tag_term(LIB, other) is None


def test_terms_fill_numbers_from_data() -> None:
    """9.2：說明卡的數字照資料填（AP 每回合、積水回合、治療加成、武器骰與目前的屬性加成）。"""
    weapon = LIB.weapons["one_handed_sword"]
    ctx = FlashTextContext(weapon=weapon, attr=lambda _a: 14)
    ids = ["ap", "surface:water", "weapon_damage:300", "status:burning", "kw:wet", "nope"]
    terms = flash_terms(LIB, KINDLE, ids, ctx)
    assert "nope" not in terms
    core = LIB.ruleset.core
    assert f"每回合 {core.ap_per_turn} 點" in terms["ap"].text_zh
    assert f"最多留 {core.ap_carry_max} 點" in terms["ap"].text_zh
    water = LIB.ruleset.surface_def(Surface.WATER).duration
    assert f"預設留 {water} 回合" in terms["surface:water"].text_zh
    assert "+20%" in terms["surface:water"].text_zh
    damage = terms["weapon_damage:300"].text_zh
    assert f"武器骰 {weapon.dice}" in damage
    assert "× 0.3" in damage
    bonus = KINDLE.scaling_value(lambda _a: 14, weapon) * core.basic_attack_attr_multiplier_permille
    assert f"屬性加成目前 +{bonus // 1000}" in damage
    statuses = LIB.ruleset.statuses.by_id()
    assert terms["status:burning"].text_zh == statuses["burning"].description_zh
    assert terms["kw:wet"].text_zh == LIB.keywords.by_id()["wet"].description_zh


def test_power_terms_use_confirmed_wording() -> None:
    """9.2 兩張威力說明卡：玩法 PM 2026-11-13 確認的字。"""
    ctx = FlashTextContext(weapon=None, attr=lambda _a: 10)
    terms = flash_terms(LIB, KINDLE, ["power_up", "power_down"], ctx)
    assert terms["power_up"].text_zh.startswith("威力提高：多付代價（冷卻變長、AP 或資源變多）")
    assert terms["power_down"].text_zh.startswith("威力降低：代價少付一點")
    assert "待玩法 PM" not in terms["power_down"].text_zh


def test_term_ids_parse_markup() -> None:
    text = "打中時，[[shape:cross|十字範圍]]會[[surface:water|積水]]，{{kw:wet}}[[kw:wet|潮濕]]"
    assert term_ids(text) == ["shape:cross", "surface:water", "kw:wet"]
    assert term_ids(None) == []


# ---------------------------------------------------------------------------
# API：pending_flash 帶大標、一句話、說明卡
# ---------------------------------------------------------------------------


@pytest.fixture
def client(library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    return make_client(library, llm=MockLlmProvider())


def _ok(reply: Any) -> dict[str, Any]:
    assert reply.status_code in (200, 201), reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_pending_flash_carries_text_and_terms(client: TestClient) -> None:
    run_id = _ok(client.post("/api/runs", json={"build": "build_fire", "seed": 6}))["run_id"]
    store = client.app.state.runs  # type: ignore[attr-defined]
    assert isinstance(store, RunStore)
    session = store.get(run_id)
    session.run, _ = auto_play(
        store.library, session.run, stop=lambda r, _b: isinstance(r.node, GearOfferNode)
    )
    body = _ok(client.get(f"/api/runs/{run_id}"))
    skill = next(f["skill_id"] for f in body["hero"]["flash"] if f["can_flash"])
    opened = _ok(client.post(f"/api/runs/{run_id}/choice", json={"kind": "flash", "skill": skill}))
    pending = opened["pending_flash"]
    terms = pending["terms"]
    assert {"ap", "cooldown", "range"} <= set(terms)
    for option in pending["options"]:
        assert option["say_zh"]
        assert "headline_zh" in option
        used = term_ids(option["say_zh"]) + term_ids(option["headline_zh"])
        for row in option["changes"]:
            assert row["name_zh"]
            used += term_ids(row["before_zh"]) + term_ids(row["after_zh"])
            if row["term"] is not None:
                used.append(row["term"])
        # 用到的術語：查得到的都在表裡（查不到的畫面不畫底線，不要求）
        resolvable = flash_terms(
            LIB, KINDLE, used, FlashTextContext(weapon=None, attr=lambda _a: 10)
        )
        assert set(resolvable) <= set(terms)


def test_base_strip_of_kindle() -> None:
    """2.1 原技能列：AP、耐力、冷卻、射程、燃燒回合五個數字（照資料）。"""
    stats = [(s.name_zh, s.value_zh, s.term) for s in base_stats(LIB, KINDLE)]
    assert stats == [
        ("AP", "2", "ap"),
        ("耐力", "2", "stamina"),
        ("冷卻", "2", "cooldown"),
        ("射程", "4", "range"),
        ("燃燒", "5 回合", "status:burning"),
    ]


def test_shifted_effect_is_not_listed_twice() -> None:
    """效果只是換了位置（多打一下插進一段，造水往後挪）：不列「積水 → 沒有」又「沒有 → 積水」。"""
    _, wet = _option("keyword_imbue", "element", "wet")
    burn, water = wet.effects
    _, bump = _option("keyword_exploit", "element", "collision")
    extra = bump.effects[1]
    after = wet.model_copy(update={"effects": (burn, extra, water)})
    rows = flash_changes(LIB, wet, after)
    assert [(r.name_zh, r.direction) for r in rows] == [("額外傷害", "new")]


def test_surface_rounds_read_as_puddle() -> None:
    _, wet = _option("keyword_imbue", "element", "wet")
    burn, water = wet.effects
    longer = wet.model_copy(update={"effects": (burn, water.model_copy(update={"duration": 4}))})
    shorter = wet.model_copy(update={"effects": (burn, water.model_copy(update={"duration": 2}))})
    rows = flash_changes(LIB, shorter, longer)
    assert [_view(r) for r in rows] == [("積水", "2 回合", "4 回合", "better")]
    assert rows[0].term == "surface:water"
