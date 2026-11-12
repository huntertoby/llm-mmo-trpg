"""NW-1a T-A8：頭目量測核心 :mod:`trpg.sim.boss_probe`（從 ``scripts/cb2e_sim.py`` 搬來）。

腳本輸出逐字不變的證明在 ``docs/phases/PhaseNW-1a報告.md`` 第 3 節（``bosses --only mist --seeds 1``
搬家前後 JSON 與 stdout 的 SHA-256）；這裡鎖確定性與彙總的鍵。"""

from __future__ import annotations

from collections import Counter

from trpg.content.library import ContentLibrary
from trpg.sim import boss_probe
from trpg.sim.boss_probe import (
    BOSSES,
    BUILDS,
    boss_jobs,
    boss_tally,
    phase_skills,
    probe_battle,
    run_boss_probe,
)


def test_jobs_are_build_major_and_cover_every_boss(content_library: ContentLibrary) -> None:
    jobs = boss_jobs(content_library, "mist", 2)
    assert [(j.build, j.seed) for j in jobs[:3]] == [
        ("build_striker", 0),
        ("build_striker", 1),
        ("build_fire", 0),
    ]
    assert len(jobs) == len(BUILDS) * 2
    for which in BOSSES:
        assert boss_jobs(content_library, which, 1, builds=("build_fire",))
        assert len(phase_skills(content_library, which)) >= 2
    rift = boss_jobs(content_library, "rift", 1)[0]
    assert rift.season == "rift_shard_lord" and rift.battle_map


def test_probe_battle_is_deterministic(content_library: ContentLibrary) -> None:
    job = boss_jobs(content_library, "mist", 1, builds=("build_tank",))[0]
    first = probe_battle(content_library, job)
    second = probe_battle(content_library, job)
    assert first == second
    assert first.allies >= 1 and 0 <= first.downed <= first.allies
    assert first.tally["turn|1"] > 0


def test_boss_tally_keys_match_the_script(content_library: ContentLibrary) -> None:
    job = boss_jobs(content_library, "mist", 1, builds=("build_tank",))[0]
    battle = probe_battle(content_library, job)
    tally = boss_tally(battle)
    assert tally["n"] == 1 and tally["n|build_tank"] == 1
    assert tally["win"] == int(battle.won) == tally["win|build_tank"]
    assert tally["rounds"] == battle.rounds == tally["rounds|build_tank"]
    assert not any(k.startswith(("allies", "downed")) for k in tally)  # 倒下率不進腳本的 JSON


def test_run_boss_probe_in_process_sums_battles(content_library: ContentLibrary) -> None:
    boss_probe._LIBRARIES.clear()
    builds = ("build_tank", "build_fire")
    data = run_boss_probe(content_library, None, ["mist"], 1, jobs=1, builds=builds)
    assert data["mist"]["n"] == len(builds)
    by_hand: Counter[str] = Counter()
    for job in boss_jobs(content_library, "mist", 1, builds):
        by_hand.update(boss_tally(probe_battle(content_library, job)))
    assert data["mist"] == dict(by_hand)
    assert boss_probe.library_for(None) is content_library  # 本行程跑時沿用傳入的內容庫
    boss_probe._LIBRARIES.clear()
