"""頭目戰量測的核心（NW-1a，從 ``scripts/cb2e_sim.py`` 搬來；腳本與數值工坊共用）。

走大世界的真實路徑：``new_character`` 建角 → build 底稿拉到地點建議等級、帶系統傭兵
（:data:`PROBE_PARTY`）→ 組 ``EncounterResult`` → ``prepare_battle`` →
``run_battle``，雙方都由效用 AI 操作（上手-內容 第二節「量頭目施放率的做法」）。

- :class:`BossWatch` 只看頭目本體的事件（``template_id`` 等於頭目）：``TurnStarted`` 是分母、
  ``SkillUsed`` 是分子（技能 ID 去掉 ``_t<階>``）；頭目回合中途轉階段而該回合還沒放招時，回合改歸
  新階段。另記我方開場在場的單位與其中倒下過的（數值工坊的倒下率；不進 :func:`boss_tally`）。
- :func:`boss_tally` 的鍵與 ``scripts/cb2e_sim.py bosses`` 的 JSON 完全相同（腳本輸出逐字不變）。
- 平行：:func:`probe_task` 是頂層函式，``context`` 是內容資料夾（``None``＝專案內建）；每個工作
  行程依資料夾快取一份內容庫（:func:`library_for`），程序池可以跨工作保留。

確定性：同一份內容、同一組 :class:`ProbeJob` 結果相同（戰鬥種子來自 ``EncounterResult`` 的
``battle_seed``，不讀時間）。
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.actions import Step
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import BossPhaseChanged, RoundStarted, TurnStarted
from trpg.engine.events.combat import ReactionTriggered, UnitDowned
from trpg.engine.events.skills import SkillUsed
from trpg.engine.results import ResolveResult
from trpg.engine.runner import run_battle
from trpg.shared.types import Team
from trpg.sim.parallel import run_tasks
from trpg.world.battle import grow_enemy, prepare_battle
from trpg.world.clock import WEATHER_PERIOD_SECONDS, day_phase
from trpg.world.state import CharacterState, EncounterResult
from trpg.world.step import new_character

__all__ = [
    "BOSSES",
    "BOSS_NAMES",
    "BUILDS",
    "NIGHT",
    "NOON",
    "BossBattle",
    "BossWatch",
    "ProbeJob",
    "base_skill",
    "boss_jobs",
    "boss_tally",
    "character",
    "library_for",
    "phase_skills",
    "probe_battle",
    "probe_task",
    "run_boss_probe",
]

NOON = 1_793_592_000
NIGHT = NOON + WEATHER_PERIOD_SECONDS
TIER_SUFFIX = re.compile(r"_t\d+$")
BUILDS = (
    "build_striker",
    "build_fire",
    "build_storm",
    "build_ranged",
    "build_tank",
    "build_guardian",
    "build_healer",
    "build_trapper",
)
"""``content/sim/builds.yaml`` 裡量頭目用的 8 個 build（順序＝報表順序）。"""
PARTIES = {
    "build_tank": ("merc_chiyan", "merc_huichun"),
    "build_guardian": ("merc_chiyan", "merc_huichun"),
    "build_healer": ("merc_chiyan", "merc_chuanyun"),
}
PROBE_PARTY = ("merc_tiebi", "merc_huichun")
"""其他 build 帶的傭兵（賽倫＋回春）：頭目依「主角＋2 名傭兵」設計（9.6.8）。OB-7（#154）起新角色的
``default_party`` 只帶賽倫，量測照舊帶 2 名，結果不變。"""
SEASON_BOSS_LEVEL = 10
BOSSES: dict[str, tuple[str, str, str, int]] = {
    "mist": ("sect_mist_lock_master", "cloud_ridge", "cloud_summit", 6),
    "ashen": ("ashen_heart", "ashen_waste", "molten_heart_pit", 9),
    "rift": ("rift_shard_lord", "cloud_ridge", "", SEASON_BOSS_LEVEL),
}
"""情境鍵 → (頭目單位, 區域, 地點, 等級)；``rift`` 是賽季頭目（地圖取 ``world_season``）。"""
BOSS_NAMES = {"mist": "霧鎖真人", "ashen": "灰燼之心", "rift": "碎晶之主"}


@dataclass(frozen=True)
class ProbeJob:
    """一場量測戰鬥（腳本的 ``Job``；``boss`` 為 ``None`` 的是隱蔽對照用）。"""

    group: str
    region: str
    location: str
    battle_map: str | None
    level: int
    build: str
    seed: int
    bounty: str | None = None
    season: str | None = None
    night: bool = False
    world_flags: tuple[str, ...] = ()
    story_flags: tuple[str, ...] = ()
    boss: str | None = None


def base_skill(skill_id: str) -> str:
    return TIER_SUFFIX.sub("", skill_id)


def character(library: ContentLibrary, job: ProbeJob) -> CharacterState:
    """build 底稿拉到 ``job.level``、帶系統傭兵、身上掛好這場遭遇的角色。"""
    base = next(b.hero for b in library.builds.builds if b.id == job.build)
    grown, skills = grow_enemy(library, base, job.level)
    hero = grown.model_copy(update={"max_hp": base.max_hp, "level": 1})
    at = NIGHT if job.night else NOON
    encounter = EncounterResult(
        region=job.region,
        location=job.location,
        level=job.level,
        battle_map=job.battle_map,
        battle_seed=job.seed,
        weather="clear",
        day_phase=day_phase(at),
        at=at,
        bounty=job.bounty,
        season_boss=job.season,
        world_flags=job.world_flags,
    )
    update: dict[str, Any] = {
        "level": job.level,
        "mercenaries": PARTIES.get(job.build, PROBE_PARTY),
        "generated_skills": skills,
        "pending_encounter": encounter,
        "story_flags": job.story_flags,
    }
    if job.season is None:
        update["location"] = job.location
    return new_character(library, "sim", hero, region=job.region).model_copy(update=update)


type _BossEvent = BossPhaseChanged | SkillUsed | ReactionTriggered | TurnStarted


class BossWatch:
    """只看頭目本體的事件：階段、行動回合、施放（另記我方開場單位與倒下過的）。"""

    def __init__(self, boss: str) -> None:
        self.boss = boss
        self.tally: Counter[str] = Counter()
        self.phase = 1
        self.round = 0
        self.turn_phase: int | None = None
        self.turn_cast = False
        self.allies: frozenset[str] | None = None
        self.downed: set[str] = set()

    def __call__(self, _step: Step | None, result: ResolveResult) -> None:
        units = result.state.units
        if self.allies is None:  # 開場：我方在場的單位（之後召喚出來的不算）
            self.allies = frozenset(k for k, u in units.items() if u.team is Team.ALLY)
        for event in result.events:
            if isinstance(event, RoundStarted):
                self.round = event.round
                continue
            if isinstance(event, UnitDowned):
                if event.unit_id in self.allies:
                    self.downed.add(event.unit_id)
                continue
            if not isinstance(
                event, BossPhaseChanged | SkillUsed | ReactionTriggered | TurnStarted
            ):
                continue
            unit = units.get(event.unit_id)
            if unit is None or unit.template_id != self.boss:
                if isinstance(event, TurnStarted):  # 別人的回合：頭目的回合已經結束，不再改歸屬
                    self.turn_phase = None
                continue
            self._boss_event(event)

    def _boss_event(self, event: _BossEvent) -> None:
        tally = self.tally
        if isinstance(event, BossPhaseChanged):
            if self.turn_phase is not None and not self.turn_cast:
                tally[f"turn|{self.turn_phase}"] -= 1
                tally[f"turn|{event.phase}"] += 1
                self.turn_phase = event.phase
            self.phase = event.phase
            tally[f"reach|{event.phase}"] += 1
            tally[f"reach_round|{event.phase}"] += self.round
        elif isinstance(event, SkillUsed):
            tally[f"cast|{self.phase}|{base_skill(event.skill_id)}"] += 1
            self.turn_cast = True
        elif isinstance(event, ReactionTriggered):
            tally[f"rx|{self.phase}|{event.reaction}"] += 1
        else:
            tally[f"turn|{self.phase}"] += 1
            self.turn_phase = self.phase
            self.turn_cast = False


@dataclass(frozen=True)
class BossBattle:
    """一場頭目戰的結果（:func:`probe_battle`）。``tally`` 是 :class:`BossWatch` 的計數。"""

    boss: str
    build: str
    seed: int
    won: bool
    rounds: int
    allies: int
    downed: int
    tally: dict[str, int] = field(default_factory=dict)


def probe_battle(library: ContentLibrary, job: ProbeJob) -> BossBattle:
    assert job.boss is not None
    watch = BossWatch(BOSSES[job.boss][0])
    prepared = prepare_battle(library, character(library, job))
    run = run_battle(prepared.setup, prepared.seed, UtilityAI(library.ai_profiles), on_step=watch)
    return BossBattle(
        boss=job.boss,
        build=job.build,
        seed=job.seed,
        won=run.state.winner is Team.ALLY,
        rounds=run.state.round,
        allies=len(watch.allies or ()),
        downed=len(watch.downed),
        tally=dict(watch.tally),
    )


def boss_tally(battle: BossBattle) -> dict[str, int]:
    """一場的計數，鍵同 ``scripts/cb2e_sim.py bosses`` 的 JSON（相加即彙總）。"""
    tally = Counter(battle.tally)
    won = int(battle.won)
    tally["n"] = 1
    tally["win"] = won
    tally["rounds"] = battle.rounds
    tally[f"n|{battle.build}"] = 1
    tally[f"win|{battle.build}"] = won
    tally[f"rounds|{battle.build}"] = battle.rounds
    return dict(tally)


def boss_jobs(
    library: ContentLibrary, which: str, seeds: int, builds: Sequence[str] = BUILDS
) -> list[ProbeJob]:
    """一個頭目 × ``builds`` × 種子 ``0..seeds-1``（build 在外層，同腳本的順序）。"""
    _unit, region, location, level = BOSSES[which]
    if which == "rift":
        season = library.world_season
        assert season is not None and season.season_boss is not None
        battle_map: str | None = season.season_boss.battle_map
        season_id: str | None = BOSSES[which][0]
    else:
        battle_map, season_id = location, None
    return [
        ProbeJob(
            which, region, location, battle_map, level, build, seed, season=season_id, boss=which
        )
        for build in builds
        for seed in range(seeds)
    ]


def phase_skills(library: ContentLibrary, which: str) -> list[tuple[int, tuple[str, ...]]]:
    """頭目各階段（從 1 起算）的招式組；沒換招的階段沿用前一階段。"""
    unit = library.unit(BOSSES[which][0])
    current = tuple(unit.skills)
    phases: list[tuple[int, tuple[str, ...]]] = []
    for index, phase in enumerate(unit.phases, start=1):  # 第一筆就是開場階段
        current = tuple(phase.skills) if phase.skills is not None else current
        phases.append((index, current))
    return phases


_LIBRARIES: dict[str | None, ContentLibrary] = {}
_KEEP_LIBRARIES = 2


def library_for(root: str | None) -> ContentLibrary:
    """工作行程內依內容資料夾快取的內容庫（最多留 :data:`_KEEP_LIBRARIES` 份，先進先出）。"""
    cached = _LIBRARIES.get(root)
    if cached is not None:
        return cached
    library = load_library(None if root is None else Path(root))
    while len(_LIBRARIES) >= _KEEP_LIBRARIES:
        del _LIBRARIES[next(iter(_LIBRARIES))]
    _LIBRARIES[root] = library
    return library


def probe_task(root: str | None, job: ProbeJob) -> BossBattle:
    """平行用的頂層函式：``root`` 的內容庫跑一場。"""
    return probe_battle(library_for(root), job)


def run_boss_probe(
    library: ContentLibrary,
    root: str | None,
    which: Iterable[str],
    seeds: int,
    *,
    jobs: int,
    builds: Sequence[str] = BUILDS,
) -> dict[str, dict[str, int]]:
    """``which`` 每個頭目 × ``builds``（預設 8 個）× ``seeds`` 個種子的彙總計數（腳本 ``bosses``）。

    ``library`` 只用來列出工作（應與 ``root`` 是同一份內容）；戰鬥在 ``root`` 的內容庫上跑。"""
    order = list(which)
    _LIBRARIES.setdefault(root, library)  # jobs == 1 時在本行程跑，不必再載一次
    tasks = [job for w in order for job in boss_jobs(library, w, seeds, builds)]
    totals: dict[str, Counter[str]] = {w: Counter() for w in order}
    for battle in run_tasks(probe_task, root, tasks, jobs=jobs):
        totals[battle.boss].update(boss_tally(battle))
    return {w: dict(t) for w, t in totals.items()}
