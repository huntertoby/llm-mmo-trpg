"""Phase 3J-4c：解除形態原語（``leave_form``）與解形爆發（Phase3J計畫.md 4.14、06-技能.md 6.30）。

- 不在形態中不能施放；在形態中施放時先解除形態（照常冷卻），之後的傷害＝卡片數字；
- 解除形態算代價（預算折抵）、在 70～100% 之內；
- 驗證器（位置、數量、只限主動技能）、關鍵字（形態利用者）、AI（不在形態中不選）。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from tests.engine.skill_helpers import U1, U2, of
from tests.engine.test_forms_3j4 import BEAR, arena, into_bear, use
from tests.engine.test_passive_triggers import always
from trpg.content.skills import SkillDef, skill_problems
from trpg.engine import UseSkill, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import DamageDealt, FormLeft
from trpg.engine.rules.forms import form_problem
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.skills.targeting import skill_problem
from trpg.narrative.skills import skill_card
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.keywords import keyword_pools

BURST = "skill_form_release_burst"
CAT = "skill_form_cat"
COST_LABEL = "解除形態（先離開目前的形態）"


def test_the_burst_cannot_be_cast_outside_a_form() -> None:
    state = arena([BURST, BEAR])
    skill = library().ruleset.skill_def(BURST)
    assert skill_problem(state, state.units[U1], skill) == "只能在形態中使用：解形爆發"
    with pytest.raises(IllegalActionError, match="只能在形態中使用"):
        resolve(state, UseSkill(unit_id=U1, skill_id=BURST))
    in_bear = into_bear(state)
    assert skill_problem(in_bear, in_bear.units[U1], skill) is None


def test_the_burst_releases_the_form_with_the_usual_cooldown_then_hits_for_the_card_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=15, die=1)
    lib = library()
    skill = lib.ruleset.skill_def(BURST)
    state = into_bear(arena([BURST, BEAR, CAT], foes=((4, 3), (6, 3))))
    unit = state.units[U1]
    assert unit.form is not None
    natural = unit.weapon
    result = use(state, BURST)
    left = of(result, FormLeft)  # type: ignore[arg-type]
    assert [(e.form_id, e.reason, e.cooldown) for e in left] == [("bear", "released", 2)]
    after = result.state  # type: ignore[attr-defined]
    me = after.units[U1]
    assert me.form is None and me.form_cooldowns == {"bear": 2}
    assert me.weapon != natural  # 換回手上的武器
    assert me.ap == 8 - (skill.ap_cost or 0)
    assert form_problem(me, "bear") == "形態冷卻中：還要 2 回合"  # 同一個形態冷卻中
    assert form_problem(me, "cat") is None  # 別的形態不受影響
    # 事件順序：先解除形態，再造成傷害；只打周圍 1 格的敵人
    events = result.events  # type: ignore[attr-defined]
    left_at = next(i for i, e in enumerate(events) if isinstance(e, FormLeft))
    hit_at = next(i for i, e in enumerate(events) if isinstance(e, DamageDealt))
    assert left_at < hit_at
    (hit,) = of(result, DamageDealt)  # type: ignore[arg-type]
    assert hit.target_id == U2 and hit.rolls == (1, 1, 1)
    con = effective_attribute(lib.ruleset, me, Attribute.CON)
    assert hit.multiplier_permille == 1000
    assert hit.amount == (3 * 1000 + con * 500) // 1000  # 卡片：3d6＋體質加成
    assert "3d6" in "".join(skill_card(lib, skill).effects)
    # 之後不在形態中，不能再施放
    me.ap = 8
    assert skill_problem(after, me, skill) is not None


def test_the_card_tells_the_requirement_and_the_cost() -> None:
    lib = library()
    text = "".join(skill_card(lib, lib.ruleset.skill_def(BURST)).effects)
    assert "只能在形態中施放" in text and "照常進入冷卻" in text


def test_releasing_the_form_counts_as_a_cost_inside_the_budget() -> None:
    lib = library()
    skill = lib.ruleset.skill_def(BURST)
    report = skill_budget(skill, lib)
    assert report.ok and 0.7 <= float(report.ratio) <= 1.0
    extra = dict(report.allowance_parts)[COST_LABEL]
    assert extra == lib.budget.allowance.leave_form_permille == 200
    # 把 leave_form 拿掉（其餘不變），可用預算少了這一項折抵
    data = skill.model_dump(mode="json")
    data["effects"] = data["effects"][1:]
    plain = SkillDef.model_validate(data)
    assert skill_budget(plain, lib).allowance_permille == report.allowance_permille - extra


def test_the_validator_wants_leave_form_first_alone_and_on_active_skills() -> None:
    rules = library().ruleset
    base = rules.skill_def(BURST).model_dump(mode="json")
    leave, damage = base["effects"]

    def build(**patch: object) -> SkillDef:
        return SkillDef.model_validate({**base, **patch})

    for effects, message in (
        ([damage, leave], "第一個效果"),
        ([leave, leave, damage], "第一個效果|最多"),
    ):
        with pytest.raises(ValueError, match=message):
            build(effects=effects)
    assert (
        skill_problems(
            build(),
            rules.shapes.by_id(),
            rules.primitives.by_id(),
            status_ids={s.id for s in rules.statuses.statuses},
            object_ids={o.id for o in rules.objects.objects},
            conditions=rules.conditions.by_id(),
        )
        == []
    )
    # 只限主動技能：技能層級的檢查（姿態）拒絕
    with pytest.raises(ValueError, match=r"主動|姿態|stance"):
        build(kind="stance", shape={"type": "self"})


def test_the_burst_makes_a_form_exploiter_and_joins_the_form_pool() -> None:
    lib = library()
    assert BURST in keyword_pools(lib, exclusive_only=True)["form"]
    # 2 階：不當起始技能（開局只給 1 階化身）
    assert BURST not in keyword_pools(lib, starter_only=True, exclusive_only=True)["form"]


def test_the_ai_only_offers_the_burst_inside_a_form() -> None:
    ai = UtilityAI(library().ai_profiles)
    plain = arena([BURST, BEAR])
    plain_ids = {s.action.skill_id for s in ai.rank(plain) if isinstance(s.action, UseSkill)}
    assert BURST not in plain_ids
    inside = into_bear(arena([BURST, BEAR], foes=((4, 3),)))
    inside_ids = {s.action.skill_id for s in ai.rank(inside) if isinstance(s.action, UseSkill)}
    assert BURST in inside_ids
