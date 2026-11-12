"""地圖戰小模擬與單招施放率（數值工坊 NW-2a，``docs/phases/PhaseNW-2計畫.md`` 5.6、T9、T10）。

- 陣容：地圖的預設 ``encounter``（:func:`~trpg.sim.batch.map_spec`）；``allies`` 給 build ID
  時我方換成 build 英雄 ＋ 標準隊友（同 ``--ally-build``，
  :func:`~trpg.sim.lineup.build_allies`）。雙方都由效用 AI 操作。
- 「裝到 build」（T9，``inject``）：只在記憶體裡的內容庫副本改 build 英雄的技能欄，不寫檔、
  不動傳入的內容庫（規則見 :func:`inject_skills`）。
- 施放率（T10）：分子＝這招的 ``SkillUsed``（技能 ID 去掉 ``_t<階>``），分母＝「裝了這招的
  單位」的行動回合數（``TurnStarted``）；陣營分開（鍵見 :class:`SkillWatch`）。
- 平行：:func:`probe_task` 是頂層函式，內容庫用 :func:`trpg.sim.boss_probe.library_for`
  依資料夾快取。

確定性：同一份內容、同一組 :class:`SkillProbeJob` 結果相同（不讀時間、不用 ``random``）。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace

from trpg.content.library import ContentLibrary
from trpg.engine.actions import Step
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import TurnStarted
from trpg.engine.events.combat import UnitDowned
from trpg.engine.events.skills import SkillUsed
from trpg.engine.results import ResolveResult
from trpg.engine.runner import run_battle
from trpg.shared.types import Team
from trpg.sim.batch import map_spec
from trpg.sim.boss_probe import base_skill, library_for
from trpg.sim.lineup import build_allies

__all__ = [
    "EXCLUDED_MAPS",
    "MapBattle",
    "SkillProbeJob",
    "SkillWatch",
    "inject_skills",
    "map_jobs",
    "probe_battle",
    "probe_maps",
    "probe_task",
    "skill_tally",
]

EXCLUDED_MAPS = ("training_range",)
"""不列入情境選單的地圖（另外 ``test_*`` 一律不列）。"""


@dataclass(frozen=True)
class SkillProbeJob:
    """一場地圖戰。

    - ``allies``：我方的 build ID（補標準隊友到 3 人）；``None``＝地圖預設陣容。
    - ``inject``：``(build_id, skill_id)``，把這招裝到該 build 英雄身上
      （見 :func:`inject_skills`）。
    - ``probe``：受測招的基礎 ID；空＝場上所有單位裝的所有招都計。
    """

    map_id: str
    seed: int
    allies: tuple[str, ...] | None = None
    inject: tuple[tuple[str, str], ...] = ()
    probe: tuple[str, ...] = ()


@dataclass(frozen=True)
class MapBattle:
    """一場地圖戰的結果。``allies``／``downed`` 是我方開場人數與其中倒下過的；``tally`` 見
    :class:`SkillWatch`。"""

    map_id: str
    seed: int
    won: bool
    rounds: int
    allies: int
    downed: int
    tally: dict[str, int] = field(default_factory=dict)


def _equip(library: ContentLibrary, skills: tuple[str, ...], skill_id: str) -> tuple[str, ...]:
    if any(base_skill(s) == base_skill(skill_id) for s in skills):
        return skills
    defs = library.skills
    kind = defs[skill_id].slot_kind
    slots = library.ruleset.core.skill_slots
    limit = {
        "active": slots.active,
        "passive": slots.passive,
        "reaction": slots.reaction,
        "stance": slots.stance,
    }[kind]
    same = [i for i, s in enumerate(skills) if s in defs and defs[s].slot_kind == kind]
    if len(same) < limit:
        return (*skills, skill_id)
    if not same:  # 這類欄位上限為 0：裝不上
        raise ValueError(f"{skill_id} 的欄位（{kind}）上限為 0，無法裝備")
    last = same[-1]
    return (*skills[:last], skill_id, *skills[last + 1 :])


def inject_skills(library: ContentLibrary, inject: Iterable[tuple[str, str]]) -> ContentLibrary:
    """回傳把技能裝到 build 英雄身上的內容庫**副本**（不改 ``library``、不寫檔）。

    規則（依 ``inject`` 的順序逐筆套用）：

    1. 該 build 已裝這招的任何一階（基礎 ID 相同）：不變。
    2. 這招佔的欄位類別（``slot_kind``：主動／被動含修正／反應／姿態）還有空位：加在技能清單最後。
    3. 該類欄位已滿：替換該 build 同類欄位的**最後一招**（位置不變）。

    未知的 build 或技能拋出 :class:`ValueError`；武器不相容等裝備問題由開戰時的引擎檢查拋出。
    """
    pairs = list(inject)
    if not pairs:
        return library
    builds = library.builds.by_id()
    for build_id, skill_id in pairs:
        if build_id not in builds:
            raise ValueError(f"未知的 build：{build_id}")
        if skill_id not in library.skills:
            raise ValueError(f"未知的技能：{skill_id}")
        hero = builds[build_id].hero
        hero = hero.model_copy(update={"skills": _equip(library, hero.skills, skill_id)})
        builds[build_id] = builds[build_id].model_copy(update={"hero": hero})
    table = library.builds.model_copy(
        update={"builds": tuple(builds[b.id] for b in library.builds.builds)}
    )
    return replace(library, builds=table)


class SkillWatch:
    """``run_battle`` 的 ``on_step``：數施放與裝備者的行動回合，另記我方開場單位與倒下過的。

    ``tally`` 的鍵（``team`` 為 ``ally``／``enemy``，``skill`` 為基礎 ID）：

    - ``cast|{team}|{skill}``：該陣營單位施放這招的 ``SkillUsed`` 次數。
    - ``turns|{team}|{skill}``：該陣營中「當下技能清單（含暫時獲得的）有這招任何一階」的單位的
      ``TurnStarted`` 次數。

    ``probe`` 非空時只計其中的招；空時計所有招。
    """

    def __init__(self, probe: Iterable[str] = ()) -> None:
        self.probe = frozenset(base_skill(s) for s in probe)
        self.tally: Counter[str] = Counter()
        self.allies: frozenset[str] | None = None
        self.downed: set[str] = set()

    def _counted(self, skill: str) -> bool:
        return not self.probe or skill in self.probe

    def __call__(self, _step: Step | None, result: ResolveResult) -> None:
        units = result.state.units
        if self.allies is None:  # 開場：我方在場的單位（之後召喚出來的不算）
            self.allies = frozenset(k for k, u in units.items() if u.team is Team.ALLY)
        for event in result.events:
            if isinstance(event, UnitDowned):
                if event.unit_id in self.allies:
                    self.downed.add(event.unit_id)
                continue
            if not isinstance(event, SkillUsed | TurnStarted):
                continue
            unit = units.get(event.unit_id)
            if unit is None:
                continue
            team = unit.team.value
            if isinstance(event, SkillUsed):
                skill = base_skill(event.skill_id)
                if self._counted(skill):
                    self.tally[f"cast|{team}|{skill}"] += 1
                continue
            for skill in sorted({base_skill(s) for s in unit.all_skills}):
                if self._counted(skill):
                    self.tally[f"turns|{team}|{skill}"] += 1


def _battle_library(
    library: ContentLibrary, job: SkillProbeJob
) -> tuple[ContentLibrary, list[str] | None]:
    """``inject`` 只改 build 英雄：預設陣容（``allies`` 為 ``None``）沒有 build 英雄時不起作用。"""
    lib = inject_skills(library, job.inject)
    if job.allies is None:
        return lib, None
    return build_allies(lib, job.allies)


def probe_battle(library: ContentLibrary, job: SkillProbeJob) -> MapBattle:
    """跑一場地圖戰（效用 AI 對效用 AI），回傳勝負、輪數、我方倒下與計數。"""
    lib, allies = _battle_library(library, job)
    spec = map_spec(lib, job.map_id, (job.seed,), allies=allies)
    watch = SkillWatch(job.probe)
    run = run_battle(
        spec.setup,
        job.seed,
        UtilityAI(lib.ai_profiles),
        on_step=watch,
        max_actions=spec.max_actions,
    )
    return MapBattle(
        map_id=job.map_id,
        seed=job.seed,
        won=run.state.winner is Team.ALLY,
        rounds=run.state.round,
        allies=len(watch.allies or ()),
        downed=len(watch.downed),
        tally=dict(sorted(watch.tally.items())),
    )


def probe_task(root: str | None, job: SkillProbeJob) -> MapBattle:
    """平行用的頂層函式：``root`` 的內容庫（``None``＝專案內建）跑一場。"""
    return probe_battle(library_for(root), job)


def skill_tally(battles: Iterable[MapBattle]) -> dict[str, int]:
    """逐場 ``tally`` 相加（鍵排序）。"""
    total: Counter[str] = Counter()
    for battle in battles:
        total.update(battle.tally)
    return dict(sorted(total.items()))


def map_jobs(
    map_ids: Sequence[str],
    seeds: int,
    allies: Sequence[str] | None = None,
    inject: Iterable[tuple[str, str]] = (),
    probe: Iterable[str] = (),
) -> list[SkillProbeJob]:
    """每張地圖 × 種子 ``0..seeds-1``（地圖在外層、種子在內層）。"""
    ally_ids = None if allies is None else tuple(allies)
    injected = tuple(inject)
    probed = tuple(probe)
    return [
        SkillProbeJob(map_id, seed, ally_ids, injected, probed)
        for map_id in map_ids
        for seed in range(seeds)
    ]


def probe_maps(library: ContentLibrary) -> list[str]:
    """情境選單可用的地圖：有 ``encounter``、不是 ``test_*`` 與 :data:`EXCLUDED_MAPS`
    （依 ID 排序）。"""
    return sorted(
        map_id
        for map_id, map_def in library.maps.items()
        if map_def.encounter is not None
        and not map_id.startswith("test_")
        and map_id not in EXCLUDED_MAPS
    )
