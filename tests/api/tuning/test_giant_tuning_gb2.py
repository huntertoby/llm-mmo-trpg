"""GB-2（docs/phases/PhaseGB計畫.md 6.4）：數值工坊開放限時封招的回合數與階段生長表面的排數。

- T-A1：白名單對得到 schema、展開規則（``on_break[*].rounds`` 只展開已寫 ``rounds`` 的封招；
  ``grow_surface.max_rows`` 只展開已寫的階段）、標籤、擋的範圍；``footprint``、``tiles`` 不開放。
- T-A2：YAML 字面替換只動那一個數字。

數值一律讀 ``content/`` 現值（使用者寫回後不必收編）；寫死的只有結構（核心是第 3 個部位、第 2 個
破壞效果是限時封住熔心吸氣；第 3 階段有生長表面）。
"""

from __future__ import annotations

from typing import Any

from trpg.api.tuning.objects import concrete_fields, read_data
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import MISSING, lookup, patch_text
from trpg.content.loader import bundled_content_dir, parse_yaml
from trpg.content.tuning_fields import load_tuning_fields, parse_path

CONTENT = bundled_content_dir()
HEART = "units/ashen_heart.yaml"
MIST = "units/sect_mist_lock_master.yaml"
CORE_ROUNDS = "parts[2].on_break[1].rounds"
GROW_ROWS = "phases[2].grow_surface.max_rows"


def _now(path: str) -> Any:
    found = lookup(read_data(CONTENT / HEART), parse_path(path))
    return None if found is MISSING else found


def _unit_fields() -> Any:
    unit = load_tuning_fields(CONTENT).target("unit")
    assert unit is not None
    return unit


# ---------------------------------------------------------------------------
# T-A1：白名單
# ---------------------------------------------------------------------------


def test_rounds_and_grow_rows_are_whitelisted_existing_only() -> None:
    unit = _unit_fields()
    for pattern in ("parts[*].on_break[*].rounds", "phases[*].grow_surface.max_rows"):
        field = unit.field_for(pattern.replace("*", "0"))
        assert field is not None and field.path == pattern, pattern
        assert field.kind == "int" and field.existing_only
        assert field.note_zh and field.hint_min is not None and field.hint_max is not None
    paths = {f.path for f in unit.all_fields()}
    assert not [p for p in paths if "footprint" in p or "tiles" in p]  # 結構，不開放


def test_ashen_heart_expands_only_the_timed_seal_and_the_growing_phase() -> None:
    unit = _unit_fields()
    data = read_data(CONTENT / HEART)
    got = {path: label for _f, path, label in concrete_fields(data, unit)}
    rounds = sorted(p for p in got if p.endswith(".rounds"))
    assert rounds == [CORE_ROUNDS]  # 噴口的封招是永久的（沒寫 rounds）
    assert got[CORE_ROUNDS] == "部位「核心」破掉後第 2 個效果：封住「skill_heart_inhale」的回合數"
    assert not [p for p in got if p.endswith(".amount")]  # 沒有能力下降
    grow = sorted(p for p in got if "grow_surface" in p)
    assert grow == [GROW_ROWS]
    assert got[GROW_ROWS] == "第 3 階段「熔毀」表面生長排數"
    for path in got:
        assert unit.field_for(path) is not None


def test_units_without_these_fields_do_not_expand_them() -> None:
    unit = _unit_fields()
    data = read_data(CONTENT / MIST)
    paths = [p for _f, p, _l in concrete_fields(data, unit)]
    assert not [p for p in paths if p.endswith(".rounds") or "grow_surface" in p]


def test_detail_shows_values_and_limits(read_service: TuningService) -> None:
    detail = read_service.object("unit", "ashen_heart")
    rows = {f.path: f for f in detail.fields}
    core = rows[CORE_ROUNDS]
    assert (core.value, core.limit_min, core.limit_max) == (_now(CORE_ROUNDS), 1, None)
    assert core.group_zh == "部位 3「核心」"
    # GB-2b：畫面上的標籤換成技能中文名（concrete_fields 沒有內容庫，仍是 ID）
    assert core.label_zh == "部位「核心」破掉後第 2 個效果：封住「熔心吸氣」的回合數"
    grow = rows[GROW_ROWS]
    assert (grow.value, grow.limit_min, grow.limit_max) == (_now(GROW_ROWS), 1, 9)


# ---------------------------------------------------------------------------
# T-A2：YAML 字面替換
# ---------------------------------------------------------------------------


def _changed_lines(before: str, after: str) -> list[tuple[str, str]]:
    old, new = before.splitlines(), after.splitlines()
    assert len(old) == len(new)
    return [(a, b) for a, b in zip(old, new, strict=True) if a != b]


def test_patch_changes_only_the_rounds_and_the_rows() -> None:
    text = (CONTENT / HEART).read_bytes().decode("utf-8")
    for path in (CORE_ROUNDS, GROW_ROWS):
        old = _now(path)
        new = patch_text(text, [(parse_path(path), old + 1)])
        [(was, now)] = _changed_lines(text, new)
        leaf = path.rsplit(".", 1)[-1]
        assert now == was.replace(f"{leaf}: {old}", f"{leaf}: {old + 1}")
        expected = parse_yaml(text)
        node = expected
        parts = parse_path(path)
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = old + 1
        assert parse_yaml(new) == expected
