"""情境覆蓋表（Phase 6Q-A）：計數、DC 分布、兩種標記、最好情況成功率與引擎結算一致。"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.content.world_situations import (
    CareClaim,
    SituationProposal,
    SituationRules,
    SituationTemplateDef,
)
from trpg.shared.types import Attribute
from trpg.world.actions import SituationAction, SituationCheckEvent
from trpg.world.situation_coverage import (
    DICE_PAIRS,
    CoverageInputs,
    best_case,
    build_coverage,
    format_report,
    inputs_from_library,
    skeleton_gated,
    success_hits,
)
from trpg.world.situations import situation_rules, situation_template
from trpg.world.state import CharacterState, EventTrigger, ThreadState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
ROOT = Path(__file__).resolve().parents[2]


def fake_rules() -> SituationRules:
    return SituationRules.model_validate(
        {
            "methods": [
                {"id": "lore", "name_zh": "學識", "attributes": ["int"]},
                {"id": "notice", "name_zh": "察覺", "attributes": ["wis"]},
                {"id": "force", "name_zh": "力取", "attributes": ["str"]},
            ],
            "race_methods": {"human": "lore", "elf": "notice", "orc": "force"},
            "check": {"dc_shift_max": 2, "partial_margin": 5, "care_max": 2, "race_bonus": 1},
            "budget": {
                "xp_battle_permille": 500,
                "supplies_max": 2,
                "threads_max": 2,
                "buffs_max": 1,
                "reveals_max": 1,
            },
            "dangers": [
                {"level": 1, "penalties": [], "hurt_max_permille": 0},
                {"level": 2, "penalties": [], "hurt_max_permille": 0},
                {"level": 3, "penalties": [], "hurt_max_permille": 0},
            ],
            "exchange_supplies": 1,
        }
    )


def tpl(
    tid: str, methods: list[str], attributes: list[str], dc: int, **extra: Any
) -> SituationTemplateDef:
    data: dict[str, Any] = {
        "id": tid,
        "skeleton": extra.pop("skeleton", f"sk_{tid}"),
        "solution": 0,
        "note_zh": "測試",
        "methods": methods,
        "attributes": attributes,
        "base_dc": dc,
        "danger": 1,
        "success": {},
        "partial": {},
        "failure": {},
        **extra,
    }
    return SituationTemplateDef.model_validate(data)


def fake_inputs() -> CoverageInputs:
    templates = (
        tpl("a", ["lore", "notice"], ["int", "wis"], 8, skeleton="secret"),  # 有門檻
        tpl("b", ["lore"], ["int", "wis"], 9),  # DC ≤ 10 沒有門檻
        tpl("c", ["lore", "notice"], ["int", "wis"], 13),
        tpl("d", ["notice"], ["wis", "int"], 15, advantage_threads=["door"]),
        # 允許 force、但模板屬性沒有 str：提議不合法，獸人不算
        tpl("e", ["force", "lore"], ["int", "wis"], 12),
    )
    return CoverageInputs(
        rules=fake_rules(),
        templates={"r1": templates},
        gated_skeletons={"r1": frozenset({"secret"})},
        template_levels={("r1", t.id): 3 for t in templates},
        races=("human", "elf", "orc", "nomethod"),
        race_names={"human": "人類"},
    )


def test_counts_dc_distribution_and_flags() -> None:
    report = build_coverage(fake_inputs())
    rows = {r.race: r for r in report.rows}
    assert rows["human"].count == 4  # a b c e
    assert rows["human"].dc_distribution() == ((8, 1), (9, 1), (12, 1), (13, 1))
    assert rows["elf"].count == 3  # a c d
    assert rows["elf"].dc_distribution() == ((8, 1), (13, 1), (15, 1))
    assert rows["orc"].count == 0
    assert rows["nomethod"].count == 0 and rows["nomethod"].method is None
    assert {r.race for r in report.few()} == {"orc", "nomethod"}
    assert [(f.template, f.base_dc) for f in report.low_dc] == [("b", 9)]
    assert report.template_counts == {"r1": 5}


def test_best_case_numbers() -> None:
    inputs = fake_inputs()
    templates = {t.id: t for t in inputs.templates["r1"]}
    # 等級 3：屬性 10 ＋ 2×2 ＝ 14，修正 +2；用心 +2；種族 +1 → +5
    case = best_case(inputs, "r1", templates["c"], "human")
    assert (case.attribute_value, case.bonus, case.advantage) == (14, 5, False)
    assert case.hits_base == 20 * 13  # 需要 8 以上：13 面
    assert case.hits_best == 20 * 15  # DC 11：需要 6 以上
    adv = best_case(inputs, "r1", templates["d"], "elf")
    assert adv.advantage and adv.hits_base == DICE_PAIRS - 9 * 9  # 需要 10：兩顆都 ≤ 9 才失敗


def test_success_hits_edges() -> None:
    assert success_hits(1, advantage=False) == DICE_PAIRS
    assert success_hits(-5, advantage=True) == DICE_PAIRS
    assert success_hits(21, advantage=True) == 0
    assert success_hits(11, advantage=False) == 200
    assert success_hits(11, advantage=True) == DICE_PAIRS - 100


def test_quiet_report_only_summary_and_flags() -> None:
    report = build_coverage(fake_inputs())
    quiet = format_report(report, quiet=True)
    assert "| 區域 |" not in quiet
    assert "orc" in quiet and "b（骨架 sk_b）：DC 9" in quiet
    full = format_report(report)
    assert "| r1 | 人類（human） | lore | 4 | 8×1 9×1 12×1 13×1 |" in full


# ---------------------------------------------------------------------------
# 和引擎的結算對照（實際模板）
# ---------------------------------------------------------------------------


def _thread(thread_id: str) -> ThreadState:
    return ThreadState(
        thread=thread_id,
        skeleton="wounded_peddler",
        region="cloud_ridge",
        created_at=NOON - 10,
        expires_at=NOON + 259200,
    )


@pytest.mark.parametrize(
    "spec",
    [
        ("granny_parley", "mist_ferry", "human", "lore", Attribute.INT),
        ("convoy_steal", "sword_tomb", "cyborg", "finesse", Attribute.DEX),  # 有優勢線頭
    ],
)
def test_best_case_matches_engine(
    library: ContentLibrary,
    make_char: MakeChar,
    spec: tuple[str, str, str, str, Attribute],
) -> None:
    template_id, location, race, method, attribute = spec
    inputs = inputs_from_library(library)
    template = situation_template(library, "cloud_ridge", template_id)
    case = best_case(inputs, "cloud_ridge", template, race)
    rules = situation_rules(library)
    assert case.advantage == bool(template.advantage_threads)
    threads = (_thread("peddler_owes_you"), *(_thread(t) for t in template.advantage_threads))
    base = make_char(threads=threads, supplies=3)
    attributes = {**base.hero.attributes, attribute: case.attribute_value}
    hero = base.hero.model_copy(update={"race": race, "attributes": attributes})
    trigger = EventTrigger(
        region="cloud_ridge",
        location=location,
        skeleton=template.skeleton,
        candidates=(template.skeleton,),
        weather="fog",
        day_phase="day",
        at=NOON,
    )
    char = base.model_copy(update={"hero": hero, "location": location, "pending_event": trigger})
    care = (
        CareClaim(item="clue", fact="thread:peddler_owes_you"),
        CareClaim(item="exchange", fact="supplies"),
    )
    for shift, hits in ((0, case.hits_base), (-rules.check.dc_shift_max, case.hits_best)):
        proposal = SituationProposal(attribute=attribute, method=method, dc_shift=shift, care=care)
        action = SituationAction(
            template=template_id,
            player_text="商人欠你人情，我拿補給跟你換",
            proposal=proposal,
            source="llm",
        )
        need = template.base_dc + shift - case.bonus
        assert success_hits(need, advantage=case.advantage) == hits
        for seed in range(30):
            result = world_step(library, make_world(season_seed=seed), char, action, NOON)
            check = next(e for e in result.events if isinstance(e, SituationCheckEvent))
            assert check.care_bonus == rules.check.care_max
            assert check.race_bonus == rules.check.race_bonus
            assert check.mode == ("advantage" if case.advantage else "normal")
            assert check.total == check.roll + case.bonus
            assert (check.outcome == "success") == (check.roll >= need)


def test_shifted_low_dc_is_info_only() -> None:
    """6Q-B 口徑 2：DC − 2 ≤ 10 另列資訊，不進警告；DC ≤ 10 照舊比基準 DC。"""
    report = build_coverage(fake_inputs())
    # e：DC 12 → 10，沒有門檻；c：DC 13 → 11 不列；a：DC 8 有門檻；b：DC 9 已是警告
    assert [(f.template, f.base_dc) for f in report.shifted_low_dc] == [("e", 12)]
    assert [f.template for f in report.low_dc] == ["b"]
    full = format_report(report)
    assert "資訊（不警告）：DC − 2 ≤ 10" in full and "e（骨架 sk_e）：DC 12→10" in full
    assert "資訊 1 個 DC − 2 ≤ 10" in full
    quiet = format_report(report, quiet=True)
    assert "sk_e" not in quiet  # quiet（check.py）只印警告


def test_gate_counts_only_unlock_only(library: ContentLibrary) -> None:
    """6Q-B 口徑 3（後更正）：只有 unlock_only 算門檻；follows 在引擎裡不擋骨架出現，和時段、天氣、
    once 一樣不算。"""
    skeletons = library.world_event_content.events["cloud_ridge"].skeleton_by_id()
    plain = skeletons["wounded_peddler"].model_copy(
        update={
            "unlock_only": False,
            "follows": (),
            "day_phase": None,
            "weather": (),
            "once": False,
        }
    )
    assert not skeleton_gated(plain)
    assert skeleton_gated(plain.model_copy(update={"unlock_only": True}))
    for update in (
        {"follows": ("peddler_owes_you",)},
        {"day_phase": "night"},
        {"weather": ("fog",)},
        {"once": True},
    ):
        assert not skeleton_gated(plain.model_copy(update=update))
    gated = inputs_from_library(library).gated_skeletons
    unlock = {s.id for s in skeletons.values() if s.unlock_only}
    assert gated["cloud_ridge"] == unlock


def test_town_location_uses_region_level_min(library: ContentLibrary) -> None:
    """6Q-B 口徑 1：城鎮地點沒有建議等級時用該區的等級下限，不照 1 級算。"""
    inputs = inputs_from_library(library)
    region_map = library.location_map("ashen_waste")
    assert region_map is not None and region_map.level_min > 1
    # veteran_listen 的骨架只在灰燼市集（town，沒有 level_min）
    skeleton = library.world_event_content.events["ashen_waste"].skeleton_by_id()["tavern_veteran"]
    locations = region_map.location_by_id()
    assert all(locations[loc].level_min is None for loc in skeleton.locations)
    assert inputs.template_levels[("ashen_waste", "veteran_listen")] == region_map.level_min


def test_real_content_gates(library: ContentLibrary) -> None:
    """渡婆婆的兩個 DC 8 模板屬於 unlock_only 骨架，不被標出。"""
    inputs = inputs_from_library(library)
    assert "granny_past" in inputs.gated_skeletons["cloud_ridge"]
    flagged = {f.template for f in build_coverage(inputs).low_dc}
    assert not flagged & {"granny_parley", "granny_notice"}


# ---------------------------------------------------------------------------
# scripts/check.py：只出警告
# ---------------------------------------------------------------------------


def _check_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_script", ROOT / "scripts" / "check.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("check_script", module)  # dataclass 需要模組在 sys.modules
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(("code", "expected"), [(0, "通過"), (3, "警告"), (1, "警告")])
def test_check_step_is_warning_only(
    monkeypatch: pytest.MonkeyPatch, code: int, expected: str
) -> None:
    check = _check_script()
    step = next(s for s in check.STEPS if s.title == "situation coverage")
    assert step.warn_only and step.script == "scripts/situation_coverage.py"
    assert "--quiet" in step.args
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, code)

    monkeypatch.setattr(check.subprocess, "run", fake_run)
    assert check.run_step(step) == expected
    assert calls[0][1].endswith("situation_coverage.py")
