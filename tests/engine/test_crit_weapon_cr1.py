"""每種武器的暴擊傷害倍率（CR-1，``docs/design/05-戰鬥.md`` 5.4.2 第 2、5 點）：武器、天生武器、
單位檔的欄位；普攻看攻擊用的武器、武器技看手上的武器、法術技照基礎；全身上下限；重播確定性。"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, of
from trpg.content.battle import UnitTemplate, WeaponDef
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, resolve
from trpg.engine.crit_damage import crit_damage_permille
from trpg.engine.events import AttackRolled, DamageDealt
from trpg.shared.rng import Rng


def _skill(category: str = "spell") -> SkillDef:
    effect: dict[str, object] = {"type": "damage", "dice": "1d6", "element": "fire"}
    if category == "weapon":
        effect = {"type": "damage", "multiplier_permille": 1000}
    return make_skill(SID, {"type": "single", "range": 1}, [effect], category=category)


def _duel(permille: int | None, base: str = "hero_mage") -> BattleState:
    state = battle(_skill(), [(4, 3)], base=base)
    unit = state.units[U1]
    unit.weapon = unit.weapon.model_copy(update={"crit_permille": permille})
    return state


def test_weapons_have_no_multiplier_by_default(library: ContentLibrary) -> None:
    """初值全部沒寫＝核心規則的 200%；序列化不輸出這個欄位（既有存檔、紀錄不變）。"""
    assert library.ruleset.core.crit_damage.base_permille == 2000
    for weapon in library.weapons.values():
        assert weapon.crit_permille is None, weapon.id
        assert "crit_permille" not in weapon.model_dump(mode="json")


@pytest.mark.parametrize(
    ("permille", "expected"),
    [(None, 2000), (2500, 2500), (1800, 1800), (3600, 3000), (1100, 1500)],
)
def test_the_attack_weapon_sets_the_base_and_the_body_caps_apply(
    permille: int | None, expected: int
) -> None:
    state = _duel(permille)
    assert crit_damage_permille(state, state.units[U1]) == expected


def test_a_weapon_skill_uses_the_held_weapon_and_a_spell_uses_the_base() -> None:
    state = _duel(2500)
    unit = state.units[U1]
    assert crit_damage_permille(state, unit, skill=_skill("weapon")) == 2500
    assert crit_damage_permille(state, unit, skill=_skill("spell")) == 2000


def test_the_caps_come_from_the_core_rules() -> None:
    state = _duel(2800)
    rules = state.ruleset.core.crit_damage
    state.ruleset = state.ruleset.model_copy(
        update={
            "core": state.ruleset.core.model_copy(
                update={"crit_damage": rules.model_copy(update={"max_permille": 2600})}
            )
        }
    )
    assert crit_damage_permille(state, state.units[U1]) == 2600


def test_a_unit_file_overrides_its_weapon(library: ContentLibrary) -> None:
    template = library.units["hero_fighter"]
    plain = library.weapon_of(template)
    assert plain.crit_permille is None
    heavy = template.model_copy(update={"crit_permille": 3000})
    assert library.weapon_of(heavy).crit_permille == 3000
    assert library.weapon_of(heavy).model_copy(update={"crit_permille": None}) == plain
    assert "crit_permille" not in template.model_dump(mode="json")


def test_a_natural_weapon_carries_its_multiplier(library: ContentLibrary) -> None:
    form = library.ruleset.forms.forms[0]
    natural = form.natural_weapon.model_copy(update={"crit_permille": 2400})
    weapon = natural.weapon_def(form.id, None)
    assert isinstance(weapon, WeaponDef) and weapon.crit_permille == 2400
    assert form.natural_weapon.weapon_def(form.id, None).crit_permille is None


def _script(monkeypatch: pytest.MonkeyPatch, values: Sequence[int]) -> None:
    queue = list(values)

    def randint(self: Rng, lo: int, hi: int) -> int:
        assert queue, "骰值用完了"
        return queue.pop(0)

    monkeypatch.setattr(Rng, "randint", randint)


def _crit_attack(monkeypatch: pytest.MonkeyPatch, permille: int | None) -> DamageDealt:
    state = _duel(permille)
    _script(monkeypatch, [20, *([5] * 40)])  # 自然 20，之後每顆骰都擲 5
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (rolled,) = of(result, AttackRolled)
    assert rolled.crit
    return of(result, DamageDealt)[0]


def test_a_basic_attack_crit_uses_the_weapon_multiplier(monkeypatch: pytest.MonkeyPatch) -> None:
    """普攻自然 20：骰值照擲出的記，傷害隨武器倍率變（200% 和沒填一樣）。"""
    amounts = {p: _crit_attack(monkeypatch, p) for p in (None, 1500, 2000, 2500)}
    assert len({hit.rolls for hit in amounts.values()}) == 1
    assert amounts[None].amount == amounts[2000].amount
    assert amounts[1500].amount < amounts[2000].amount < amounts[2500].amount


@pytest.mark.parametrize("seed", range(6))
def test_the_replay_is_deterministic_with_a_custom_multiplier(seed: int) -> None:
    """同一個初始狀態與動作，倍率 250% 時兩次結算的事件與亂數狀態完全相同。"""

    def run() -> tuple[object, ...]:
        state = _duel(2500)
        state.rng_state = Rng(seed).get_state()
        result = resolve(state, Attack(unit_id=U1, target_id=U2))
        return (tuple(e.model_dump(mode="json") for e in result.events), result.state.rng_state)

    assert run() == run()


def test_unit_template_field_is_validated() -> None:
    with pytest.raises(ValueError, match="crit_permille"):
        UnitTemplate.model_validate(
            {
                "id": "x",
                "name_zh": "x",
                "attributes": {},
                "max_hp": 1,
                "speed": 1,
                "weapon": "dagger",
                "crit_permille": 500,
            }
        )
