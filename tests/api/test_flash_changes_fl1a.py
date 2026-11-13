"""FL-1a：閃現選項的「前 → 後」差異清單（``FlashOptionOut.changes``）。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.engine.helpers import library as _load_library
from trpg.api.flash_changes import flash_changes
from trpg.api.llm_source import MockLlmProvider
from trpg.api.runs import RunStore
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite import auto_play
from trpg.roguelite.state import GearOfferNode
from trpg.skillgen.flash_derive import derive_skill
from trpg.skillgen.flash_state import Variation, acquire, with_flash
from trpg.skillgen.whiteboard import compose_whiteboard

LIB = _load_library()
SEED = 12345


def _flash(base: SkillDef, template: str, category: str = "cost") -> SkillDef:
    state = with_flash(
        acquire(base.id), Variation(source="minor", template=template, category=category)
    )
    return derive_skill(LIB, base, state, SEED, tier=1)


def _named(name: str) -> SkillDef:
    return next(
        s for s in LIB.skills.values() if s.name_zh == name and s.tier == 1 and not s.enemy_only
    )


def _rows(before: SkillDef, after: SkillDef) -> dict[str, tuple[str | None, str | None, str]]:
    return {c.field: (c.before, c.after, c.direction) for c in flash_changes(LIB, before, after)}


def test_kindle_charge_lists_cooldown_and_rounds() -> None:
    base = compose_whiteboard(75, recipe_id="kindle", weapon_class="melee", tier=1, library=LIB)
    rows = _rows(base, _flash(base, "cost_charge"))
    assert rows == {
        "cost.cooldown": ("2", "4", "cost"),
        "effects[0].amount": ("5", "6", "better"),
    }
    labels = {c.field: c.label_zh for c in flash_changes(LIB, base, _flash(base, "cost_charge"))}
    assert labels == {"cost.cooldown": "冷卻", "effects[0].amount": "燃燒回合"}


def test_light_lists_cheaper_cost_and_a_weaker_effect() -> None:
    """FL-1a 原本用霜寒之觸（法力 3 → 2、1d8 → 1d6）；FL-1c 第 5 點起法力實付沒變就不出輕巧，
    改用 1 階的雷鳴箭以外、仍出輕巧的展翼（FL-1c 第 6 點：飛行回合算增益的狀態回合）。"""
    base = _named("展翼")
    after = _flash(base, "cost_light")
    rows = _rows(base, after)
    assert rows["cost.ap"] == ("2", "1", "cost")
    assert rows["effects[0].amount"] == ("3", str(after.effects[0].duration), "worse")
    assert all(d != "better" for *_, d in rows.values())


def test_war_hymn_charge_lists_the_aura_rounds() -> None:
    """FL-1c 第 6 點：只對友方的持續區域，回合算增益的狀態回合；卡片數字沒有，差異清單另外列。"""
    base = _named("戰歌")
    rows = _rows(base, _flash(base, "cost_charge"))
    assert rows["effects[0].amount"] == ("3", "4", "better")
    labels = {c.field: c.label_zh for c in flash_changes(LIB, base, _flash(base, "cost_charge"))}
    assert labels["effects[0].amount"] == "區域回合"


def test_cost_rows_follow_the_card() -> None:
    base = _named("霜寒之觸")
    cheaper = base.model_copy(update={"cost": base.cost.model_copy(update={"mana": 1})})
    assert _rows(base, cheaper) == {"cost.mana": ("2", "1", "cost")}


def test_one_up_one_down_is_expressed() -> None:
    """調查 3.4：蓄力有 38 招是一升一降（例：雙槍連射）。"""
    base = _named("雙槍連射")
    rows = _rows(base, _flash(base, "cost_charge"))
    directions = {d for *_, d in rows.values()}
    assert {"better", "worse", "cost"} <= directions


def test_new_and_removed_effects() -> None:
    base = _named("霜寒之觸")
    extra = base.effects[1]
    grown = base.model_copy(update={"effects": (*base.effects, extra)})
    added = _rows(base, grown)
    assert added == {"effects[2]": (None, "1", "new")}
    removed = _rows(grown, base)
    assert removed == {"effects[2]": ("1", None, "worse")}


def test_no_changes_for_the_same_skill() -> None:
    base = _named("霜寒之觸")
    assert flash_changes(LIB, base, base) == ()


def test_magnitude_and_range_rows() -> None:
    base = compose_whiteboard(75, recipe_id="kindle", weapon_class="melee", tier=1, library=LIB)
    effect = base.effects[0].model_copy(update={"magnitude_permille": 1050})
    assert isinstance(base.shape.range, int)
    shape = base.shape.model_copy(update={"range": base.shape.range + 1})
    after = base.model_copy(update={"effects": (effect,), "shape": shape})
    rows = _rows(base, after)
    assert rows["effects[0].magnitude_permille"] == ("1000‰", "1050‰", "better")
    assert rows["range"][2] == "better"


# ---------------------------------------------------------------------------
# API：pending_flash 的每個選項都帶 changes
# ---------------------------------------------------------------------------


@pytest.fixture
def client(library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    return make_client(library, llm=MockLlmProvider())


def _ok(reply: Any) -> dict[str, Any]:
    assert reply.status_code in (200, 201), reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_pending_flash_options_carry_changes(client: TestClient) -> None:
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
    options = opened["pending_flash"]["options"]
    assert options
    for option in options:
        assert option["changes"], option["template"]
        for row in option["changes"]:
            assert set(row) == {
                "field",
                "label_zh",
                "effect_index",
                "before",
                "after",
                "direction",
                *("name_zh", "term", "before_zh", "after_zh", "icon"),  # FL-1b 畫面字
            }
            assert row["direction"] in ("better", "worse", "cost", "new")
            assert row["before"] != row["after"]
