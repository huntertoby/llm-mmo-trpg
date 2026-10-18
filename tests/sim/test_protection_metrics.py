"""Phase 2D-2 4.6-4：保護指標（治療量、護盾吸收量、承受傷害、隊友存活率）與保護矩陣。"""

from __future__ import annotations

from tests.engine.helpers import library
from tests.sim.test_metrics import A1, A2, E1, UNITS, Stream
from trpg.engine.events import RoundStarted, ShieldAbsorbed, ShieldGained
from trpg.shared.types import Team
from trpg.sim.batch import run_batch
from trpg.sim.matrix import format_matrix, matrix_specs, run_matrix
from trpg.sim.metrics import metrics_from_events


def test_shield_absorption_is_credited_to_the_caster_of_the_shield() -> None:
    s = Stream()
    s.add(RoundStarted)
    s.add(ShieldGained, unit_id=A2, source_id=A1, amount=10, total=10)
    s.add(ShieldAbsorbed, unit_id=A2, absorbed=6, remaining=4)
    s.damage(A2, E1, 40, 40)  # 名目傷害被護盾完全吸收，沒有實際扣血
    s.add(ShieldAbsorbed, unit_id=A2, absorbed=4, remaining=0)
    m = metrics_from_events(
        seed=1,
        units=UNITS,
        events=s.events,
        bounds=None,
        ap_spent={},
        winner=None,
        rounds=1,
        actions=1,
    )
    by_id = {u.unit_id: u for u in m.units}
    assert by_id[A1].shield_provided == 10  # 施放者 A1 的護盾共吸收 10
    assert by_id[A2].shield_provided == 0 and by_id[A2].damage_taken == 0


def test_teammate_survival_counts_downed_allies_per_instance() -> None:
    lib = library()
    spec = matrix_specs(lib, ["build_tank"], ["open_plain"], [0, 1])[0][2]
    report = run_batch(spec)
    hero = next(t for t in report.templates if t.template_id == "build_tank")
    assert hero.teammate_survival is not None and 0.0 <= hero.teammate_survival <= 1.0
    enemy_rows = [t for t in report.templates if t.team is Team.ENEMY]
    assert enemy_rows and all(t.teammate_survival is None for t in enemy_rows)


def test_matrix_report_has_a_protection_section() -> None:
    report = run_matrix(library(), ["build_tank", "build_healer"], ["open_plain"], [0, 1])
    text = format_matrix(report)
    assert "## 保護矩陣" in text
    healer = report.archetype_cell("build_healer", "open_plain")
    assert healer.hero_healing >= 0.0 and 0.0 <= healer.teammate_survival <= 1.0
    assert report.cell("build_healer", "open_plain").hero_taken >= 0.0
    assert report.standards.top_count >= 1  # 保護矩陣不影響排名與標準
