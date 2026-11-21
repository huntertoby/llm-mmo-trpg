"""HC-4c：搬進 ``ai_profiles.yaml`` 的 AI 規則數值開進工坊（AI 估值表，分組顯示）。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

from trpg.api.tuning.objects import object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import lookup
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import parse_path

CONTENT = bundled_content_dir()
AI = "ai_profiles.yaml"
OPENED = (
    "rewrite.ap_points",
    "rewrite.ally_ap_permille",
    "rewrite.source_points",
    "rewrite.undying_points",
    "rewrite.revive_points",
    "rewrite.priority_kill_points",
    "rewrite.interrupt_points",
    "summon.hit_permille",
    "summon.totem_ally_points",
    "summon.infuse_value_permille",
    "summon.infuse_threat_damage",
    "trap_likelihood_permille",
    "trap.max_active",
    "zone.likelihood_permille",
    "rune.inscribe_points",
    "terrain.height_points",
    "stance.cancel_hp_below_permille",
    "form.enter_value",
    "self_cost.stun_hp_below_permille",
    "gamble.hp_floor_permille",
    "orders.focus_permille",
    "orders.hold_weight",
    "orders.environment_permille",
    "run.pursue_points",
    "run.retreat_hp_permille",
    "basic.guard_points",
    "basic.swap_points",
    "basic.aim_hit_permille",
    "heuristics.race.conceal_near",
    "heuristics.race.leap_rise_points",
    "heuristics.race.restore_min_deficit",
    "heuristics.scoring.unlisted_status_value",
    "heuristics.scoring.defend_radius",
    "heuristics.scoring.surface_friend_harm",
    "heuristics.scoring.hurt_hp_permille",
)
"""這段新開的欄位（HC-4c 拿掉程式預設值、工坊改得動的 AI 規則數值；有分組）。"""


def _now(path: str) -> object:
    return lookup(read_data(CONTENT / AI), parse_path(path))


def test_ai_rule_numbers_are_open_with_groups_and_notes(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "ai", "ai_profiles")
    grouped = {f.path: f for f in detail.fields if f.group_zh is not None}
    assert sorted(grouped) == sorted(OPENED)
    for path in OPENED:
        field = grouped[path]
        assert field.value == _now(path), path
        assert field.label_zh and not field.label_zh.isascii(), path
        assert "調高" in field.note_zh and "調低" in field.note_zh, path
        assert field.hint_min is not None and field.hint_max is not None, path
        assert field.hint_min <= field.value <= field.hint_max, path  # type: ignore[operator]
    assert any("HC-4c" in n for n in detail.notes_zh)


def test_an_ai_rule_draft_validates(read_service: TuningService) -> None:
    path = "heuristics.scoring.defend_radius"
    now = _now(path)
    assert isinstance(now, int)
    item = TuningChangeIn(file=AI, path=path, old=now, new=now + 1)
    result = read_service.check("hc4c-defend", [item])
    assert result.ok, (result.field_errors, result.page_errors)


def test_a_permille_over_the_schema_cap_is_refused(read_service: TuningService) -> None:
    path = "basic.aim_hit_permille"
    now = _now(path)
    assert isinstance(now, int)
    item = TuningChangeIn(file=AI, path=path, old=now, new=1001)
    result = read_service.check("hc4c-aim", [item])
    assert not result.ok
