"""BAL-4c：戰鬥外給玩家看的費用（技能卡、工坊）是我方實際會扣的法力；技能資料、CLI 內容瀏覽、
敵方單位的卡片維持原始費用。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.engine.helpers import caster_template, library, make_map, make_state, spawn
from tests.engine.skill_helpers import FLAT7
from trpg.api.hero_cards import hero_cards
from trpg.narrative.skills import cost_summary, skill_card
from trpg.shared.types import Team, UnitId

FIRE_BOLT = "skill_fire_bolt"
"""法力 6；我方 ×0.8 ＝ 4.8 → 5。"""


def _raw_and_ally() -> tuple[int, int]:
    lib = library()
    raw = lib.skills[FIRE_BOLT].cost.mana
    return raw, lib.ruleset.core.ally_mana(raw)


def test_fixture_skill_has_a_visible_discount() -> None:
    assert _raw_and_ally() == (6, 5)


def test_skill_card_shows_the_ally_cost_and_cli_summary_the_raw_cost() -> None:
    lib = library()
    raw, ally = _raw_and_ally()
    skill = lib.skills[FIRE_BOLT]
    assert f"法力 {ally}" in skill_card(lib, skill).cost
    assert f"法力 {raw}" in skill_card(lib, skill, ally=False).cost
    assert f"法力 {raw}" in cost_summary(lib, skill)  # CLI 內容瀏覽：原始費用
    assert skill.cost.mana == raw  # 技能資料不變（預算以它計算）


def test_skill_endpoint_shows_the_ally_cost(client: TestClient) -> None:
    _raw, ally = _raw_and_ally()
    body = client.get(f"/api/skills/{FIRE_BOLT}").json()
    assert f"法力 {ally}" in body["cost"]


def test_workshop_check_reports_battle_mana_and_keeps_raw_skill(client: TestClient) -> None:
    raw, ally = _raw_and_ally()
    draft = library().skills[FIRE_BOLT].model_dump(mode="json", exclude_none=True)
    draft["id"] = "skill_custom_bal4c"
    body = client.post("/api/workshop/check", json={"skill": draft}).json()
    assert body["card"] is not None, body["problems"]
    assert body["battle_mana"] == ally
    assert body["skill"]["cost"]["mana"] == raw
    assert f"法力 {ally}" in body["card"]["cost"]


def test_hero_cards_follow_the_units_team() -> None:
    """戰鬥中的卡片（有算式的才會列出）：我方單位打折、敵方單位原價。"""
    lib = library()
    raw, ally = _raw_and_ally()
    m = make_map(FLAT7, ally=[(1, 3)], enemy=[(5, 3)])
    spawns = [
        spawn(Team.ALLY, (1, 3), caster_template([FIRE_BOLT])),
        spawn(Team.ENEMY, (5, 3), caster_template([FIRE_BOLT])),
    ]
    state = make_state(m, spawns)
    ally_cards = hero_cards(state, lib, UnitId("unit_0001")).cards
    enemy_cards = hero_cards(state, lib, UnitId("unit_0002")).cards
    assert FIRE_BOLT in ally_cards and FIRE_BOLT in enemy_cards
    assert f"法力 {ally}" in ally_cards[FIRE_BOLT].cost
    assert f"法力 {raw}" in enemy_cards[FIRE_BOLT].cost
