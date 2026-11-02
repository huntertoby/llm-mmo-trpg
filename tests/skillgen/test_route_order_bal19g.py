"""BAL-19g：同路線找法（06 6.27.4，玩法決定 #110）。

候選找同路線依序 ① 同關鍵字、跟主路線（武器技看武器）→ ② 雙屬性技能 → ③ 放寬關鍵字 → ④ 才給偏離；
完整版、白板版與三選一的偏離標示（``off_route``）用同一個判定（:func:`route_rank`）。
"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.roguelite import new_keyword_run
from trpg.roguelite.offers import make_offer, weapon_scaling_attrs
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute as A
from trpg.shared.types import top_attribute
from trpg.skillgen import whiteboard_candidates as wbc
from trpg.skillgen.candidates import (
    ROUTE_DUAL,
    ROUTE_MAIN,
    ROUTE_OFF,
    CandidateRequest,
    CandidateRules,
    _first,
    _Search,
    follows_attr,
    route_rank,
)

LIB = library()
SWORD = (A.STR,)


def _spell(skill_id: str, attr: A, second: A | None = None) -> SkillDef:
    base = LIB.skills["skill_fire_bolt"]
    return base.model_copy(
        update={"id": skill_id, "scaling_attr": attr, "secondary_scaling_attr": second}
    )


def _weapon_skill(skill_id: str, second: A | None = None) -> SkillDef:
    base = next(
        s for s in sorted(LIB.skills.values(), key=lambda s: s.id) if s.category == "weapon"
    )
    return base.model_copy(update={"id": skill_id, "secondary_scaling_attr": second})


def _attrs(top: A) -> dict[A, int]:
    return {a: 14 if a is top else 10 for a in A}


# ---------------------------------------------------------------------------
# 判定
# ---------------------------------------------------------------------------


def test_weapon_skill_follows_the_weapon_and_its_mind_second_attr_is_dual() -> None:
    plain = _weapon_skill("t_plain")
    dual = _weapon_skill("t_dual", A.INT)
    assert route_rank(plain, A.STR, SWORD) == ROUTE_MAIN  # 武器技看武器（不看技能自己的）
    assert route_rank(dual, A.STR, SWORD) == ROUTE_MAIN
    assert route_rank(dual, A.INT, SWORD) == ROUTE_DUAL  # 智力最高：靠心智第二屬性跟上
    assert route_rank(plain, A.INT, SWORD) == ROUTE_OFF


def test_dual_attribute_spell_follows_through_its_second_attr() -> None:
    curse = _spell("t_curse", A.WIL, A.INT)
    assert route_rank(curse, A.WIL) == ROUTE_MAIN
    assert route_rank(curse, A.INT) == ROUTE_DUAL
    assert follows_attr(curse, A.INT)  # 雙屬性不算偏離
    assert route_rank(curse, A.STR, SWORD) == ROUTE_OFF
    assert route_rank(_spell("t_fire", A.INT), A.STR, SWORD) == ROUTE_OFF


def test_dual_weapon_rule_from_bal17_is_kept() -> None:
    arcane = (A.STR, A.INT)
    assert route_rank(_spell("t_fire", A.INT), A.STR, arcane) == ROUTE_MAIN
    assert route_rank(_spell("t_wil_int", A.WIL, A.INT), A.STR, arcane) == ROUTE_DUAL
    assert route_rank(_spell("t_wil", A.WIL), A.STR, arcane) == ROUTE_OFF


# ---------------------------------------------------------------------------
# 完整版的找法順序
# ---------------------------------------------------------------------------


def _search(pool: list[tuple[SkillDef, tuple[str, ...]]], top: A) -> _Search:
    request = CandidateRequest(
        keyword_counts={},
        weapon_class="focus",
        seed=7,
        tier=1,
        hero_attributes=_attrs(top),
    )
    rules = CandidateRules(composer_share_permille=0, composer_tries=0)  # 只看技能池
    return _Search(LIB, request, rules, tuple(pool), set())


def test_full_search_prefers_main_route_then_dual_within_a_keyword() -> None:
    main = _spell("t_main", A.INT)
    dual = _spell("t_dual", A.WIL, A.INT)
    off = _spell("t_off", A.WIL)
    search = _search([(off, ("ignite",)), (dual, ("ignite",)), (main, ("ignite",))], A.INT)
    hit = _first(search, Rng(1), [("ignite",)], "same")
    assert hit is not None and hit[1].id == "t_main"
    search = _search([(off, ("ignite",)), (dual, ("ignite",))], A.INT)
    hit = _first(search, Rng(1), [("ignite",)], "same")
    assert hit is not None and hit[1].id == "t_dual"


def test_full_search_takes_dual_before_relaxing_the_keyword() -> None:
    """② 在 ③ 之前：第一個關鍵字只有雙屬性技能時就取它，不換到第二個關鍵字的主路線技能。"""
    dual = _spell("t_dual", A.WIL, A.INT)
    other_kw = _spell("t_other_kw", A.INT)
    search = _search([(dual, ("ignite",)), (other_kw, ("charged",))], A.INT)
    hit = _first(search, Rng(1), [("ignite",), ("charged",)], "same")
    assert hit is not None and hit[0] == ("ignite",) and hit[1].id == "t_dual"


def test_full_search_relaxes_the_keyword_before_going_off_route() -> None:
    """③ 在 ④ 之前：第一個關鍵字只有偏離的，就換關鍵字找同路線的。"""
    off = _spell("t_off", A.WIL)
    other_kw = _spell("t_other_kw", A.INT)
    search = _search([(off, ("ignite",)), (other_kw, ("charged",))], A.INT)
    hit = _first(search, Rng(1), [("ignite",), ("charged",)], "same")
    assert hit is not None and hit[0] == ("charged",) and hit[1].id == "t_other_kw"
    search = _search([(off, ("ignite",))], A.INT)
    hit = _first(search, Rng(1), [("ignite",), ("charged",)], "same")
    assert hit is not None and hit[1].id == "t_off"  # ④ 都沒有才給偏離


def test_new_direction_still_wants_off_route() -> None:
    dual = _spell("t_dual", A.WIL, A.INT)
    off = _spell("t_off", A.WIL)
    search = _search([(dual, ("ignite",)), (off, ("ignite",))], A.INT)
    hit = _first(search, Rng(1), [("ignite",)], "other")
    assert hit is not None and hit[1].id == "t_off"  # 雙屬性不算偏離，新方向不取它


# ---------------------------------------------------------------------------
# 白板版的找法順序
# ---------------------------------------------------------------------------


class _FakeMaker(wbc._Maker):
    """每個關鍵字固定回傳一招（測試 ``_first`` 的順序）。"""

    def __init__(self, made: dict[str, SkillDef], top: A) -> None:
        request = CandidateRequest(
            keyword_counts={}, weapon_class="focus", seed=1, tier=1, hero_attributes=_attrs(top)
        )
        super().__init__(LIB, request, 1)
        self.made = made

    def make(self, rng, kind, keyword, want):  # type: ignore[no-untyped-def]
        skill = self.made.get(keyword)
        return None if skill is None else (skill, "composer")


def test_whiteboard_order_matches_full_version() -> None:
    dual = _spell("t_dual", A.WIL, A.INT)
    main = _spell("t_main", A.INT)
    off = _spell("t_off", A.WIL)
    maker = _FakeMaker({"ignite": dual, "charged": main}, A.INT)
    hit = wbc._first(maker, Rng(1), "deepen", ["ignite", "charged"])
    assert hit is not None and hit[1].id == "t_dual"  # ② 在 ③ 之前
    maker = _FakeMaker({"ignite": off, "charged": main}, A.INT)
    hit = wbc._first(maker, Rng(1), "deepen", ["ignite", "charged"])
    assert hit is not None and hit[1].id == "t_main"  # ③ 在 ④ 之前
    maker = _FakeMaker({"ignite": off}, A.INT)
    hit = wbc._first(maker, Rng(1), "deepen", ["ignite", "charged"])
    assert hit is not None and hit[1].id == "t_off"  # ④


def test_whiteboard_grade_ranks_main_dual_off() -> None:
    maker = _FakeMaker({}, A.INT)
    assert maker.grade(_spell("a", A.INT), "same") == 0
    assert maker.grade(_spell("b", A.WIL, A.INT), "same") == 1
    assert maker.grade(_spell("c", A.WIL), "same") == 2
    assert maker.grade(_spell("c", A.WIL), "other") == 0
    assert maker.grade(_spell("b", A.WIL, A.INT), "other") == 2


# ---------------------------------------------------------------------------
# 三選一的偏離標示用同一個判定
# ---------------------------------------------------------------------------


def test_offer_off_route_uses_route_rank() -> None:
    for weapon, keywords, alloc in (
        ("totem_staff", ("summon", "ignite"), {A.WIL: 4}),
        ("one_handed_sword", ("prone", "collision"), {A.STR: 4}),
    ):
        run = new_keyword_run(LIB, weapon, keywords, 3, alloc)
        offer = make_offer(LIB, run, "level_up")
        top = top_attribute(run.hero.attributes)
        attrs = weapon_scaling_attrs(LIB.weapons[weapon])
        expected = tuple(
            i for i, s in enumerate(offer.candidates) if route_rank(s, top, attrs) == ROUTE_OFF
        )
        assert offer.off_route == expected
