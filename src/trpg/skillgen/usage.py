"""技能的用法統計（Phase 3-26b，``docs/design/06-技能.md`` 6.28「分歧進化的選項怎麼產生」第 1 點）。

從一場戰鬥的 **初始設定 ＋ 種子 ＋ 步驟** 重播出事件（確定性），統計某個單位每招技能的用法：

- ``uses``：使用次數（``skill_used`` 事件）；
- ``targets``／``distance``：目標數與施放距離的總和（平均 ＝ 總和 ÷ 次數；
  目標 ＝ 施放當下站在影響格上的
  其他單位；距離 ＝ 施放者到最遠影響格的曼哈頓距離）；
- ``kills``：施放後倒下的目標數；
- ``target_keywords``：目標身上的關鍵字狀態（施放當下的狀態與腳下的表面，
  依關鍵字推導表「利用」規則的
  ``target_has_status``／``target_on_surface``，只看專屬規則）；
- ``terrain``：施放時施放者所在格的地形；
- ``partner_makes``／``partner_uses``：這招前後（同一場、
  同一個單位的上一招與下一招）搭配的技能製造與
  利用的關鍵字（專屬規則）。

全部是整數計數、依鍵排序，所以序列化確定。roguelite（``RunState.skill_usage``）與之後的大世界共用。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.keyword_derive import derive_keywords
from trpg.content.skill_keywords import KeywordTable
from trpg.content.skills import SkillDef
from trpg.engine.actions import Step
from trpg.engine.battle import begin_battle
from trpg.engine.events import SkillUsed
from trpg.engine.rules.geometry import manhattan
from trpg.engine.runner import apply_step
from trpg.engine.setup import BattleSetup
from trpg.engine.state import BattleState
from trpg.shared.types import UnitId

__all__ = ["SkillUsage", "collect_usage", "merge_usage", "target_keyword_lookup"]


def _sorted(counts: Mapping[str, int]) -> dict[str, int]:
    return {k: counts[k] for k in sorted(counts) if counts[k] > 0}


class SkillUsage(BaseModel):
    """一招技能累積的用法統計（見模組說明）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    uses: int = Field(default=0, ge=0)
    targets: int = Field(default=0, ge=0)
    distance: int = Field(default=0, ge=0)
    kills: int = Field(default=0, ge=0)
    target_keywords: dict[str, int] = Field(default_factory=dict)
    terrain: dict[str, int] = Field(default_factory=dict)
    partner_makes: dict[str, int] = Field(default_factory=dict)
    partner_uses: dict[str, int] = Field(default_factory=dict)

    def average_permille(self, total: int) -> int:
        """``total`` ÷ 使用次數（‰，無條件捨去；沒用過為 0）。"""
        return total * 1000 // self.uses if self.uses else 0

    @property
    def avg_targets_permille(self) -> int:
        return self.average_permille(self.targets)

    @property
    def avg_distance_permille(self) -> int:
        return self.average_permille(self.distance)

    def partners(self) -> dict[str, int]:
        """前後搭配的關鍵字（製造＋利用的次數）。"""
        return _sorted(Counter(self.partner_makes) + Counter(self.partner_uses))

    def merged(self, other: SkillUsage) -> SkillUsage:
        def add(a: Mapping[str, int], b: Mapping[str, int]) -> dict[str, int]:
            return _sorted(Counter(a) + Counter(b))

        return SkillUsage(
            uses=self.uses + other.uses,
            targets=self.targets + other.targets,
            distance=self.distance + other.distance,
            kills=self.kills + other.kills,
            target_keywords=add(self.target_keywords, other.target_keywords),
            terrain=add(self.terrain, other.terrain),
            partner_makes=add(self.partner_makes, other.partner_makes),
            partner_uses=add(self.partner_uses, other.partner_uses),
        )


def merge_usage(
    base: Mapping[str, SkillUsage], extra: Mapping[str, SkillUsage]
) -> dict[str, SkillUsage]:
    """兩份統計相加（依技能 ID 排序）。"""
    out = dict(base)
    for skill_id, usage in extra.items():
        out[skill_id] = out[skill_id].merged(usage) if skill_id in out else usage
    return {k: out[k] for k in sorted(out)}


@dataclass(frozen=True, slots=True)
class _Lookup:
    statuses: dict[str, tuple[str, ...]]
    surfaces: dict[str, tuple[str, ...]]


def target_keyword_lookup(table: KeywordTable) -> _Lookup:
    """狀態／表面 → 關鍵字（推導表「利用」規則的 ``target_has_status``、``target_on_surface``，
    只看專屬規則；依推導表順序）。"""
    statuses: dict[str, list[str]] = {}
    surfaces: dict[str, list[str]] = {}
    for keyword in table.keywords:
        for rule in keyword.uses:
            if rule.grade != "exclusive":
                continue
            if rule.condition == "target_has_status" and rule.status is not None:
                statuses.setdefault(rule.status, []).append(keyword.id)
            if rule.condition == "target_on_surface" and rule.surface is not None:
                surfaces.setdefault(rule.surface.value, []).append(keyword.id)
    return _Lookup(
        {k: tuple(dict.fromkeys(v)) for k, v in statuses.items()},
        {k: tuple(dict.fromkeys(v)) for k, v in surfaces.items()},
    )


@dataclass(slots=True)
class _Cast:
    skill_id: str
    targets: int
    distance: int
    kills: int
    keywords: Counter[str]
    terrain: str


def _cast(before: BattleState, after: BattleState, event: SkillUsed, lookup: _Lookup) -> _Cast:
    caster = before.unit(event.unit_id)
    tiles = [(p.x, p.y) for p in event.tiles]
    hit = [
        u
        for xy in tiles
        if (u := before.unit_at(*xy)) is not None and u.id != caster.id and u.alive
    ]
    keywords: Counter[str] = Counter()
    for unit in hit:
        found = [k for s in unit.statuses for k in lookup.statuses.get(s.status_id, ())]
        found += lookup.surfaces.get(before.tile(*unit.xy).surface.value, ())
        keywords.update(dict.fromkeys(found, 1))  # 一個目標每個關鍵字算 1
    return _Cast(
        skill_id=event.skill_id,
        targets=len(hit),
        distance=max((manhattan(caster.xy, xy) for xy in tiles), default=0),
        kills=sum(1 for u in hit if not after.unit(u.id).alive),
        keywords=keywords,
        terrain=before.tile(*caster.xy).terrain,
    )


def _replay_casts(
    setup: BattleSetup, seed: int, steps: Sequence[Step], unit_id: UnitId, lookup: _Lookup
) -> list[_Cast]:
    state = begin_battle(setup, seed).state
    casts: list[_Cast] = []
    for step in steps:
        result = apply_step(state, step)
        casts += [
            _cast(state, result.state, e, lookup)
            for e in result.events
            if isinstance(e, SkillUsed) and e.unit_id == unit_id
        ]
        state = result.state
    return casts


def collect_usage(
    setup: BattleSetup,
    seed: int,
    steps: Sequence[Step],
    unit_id: UnitId,
    table: KeywordTable,
    *,
    only: Sequence[str] | None = None,
) -> dict[str, SkillUsage]:
    """重播一場戰鬥，統計 ``unit_id`` 每招技能的用法（``only`` 限定技能 ID）。純函式、確定性。"""
    casts = _replay_casts(setup, seed, steps, unit_id, target_keyword_lookup(table))
    skills: dict[str, SkillDef] = setup.ruleset.skills.by_id()
    derived = {
        c.skill_id: derive_keywords(skills[c.skill_id], table, exclusive_only=True)
        for c in casts
        if c.skill_id in skills
    }
    usage: dict[str, SkillUsage] = {}
    for i, cast in enumerate(casts):
        if only is not None and cast.skill_id not in only:
            continue
        makes: Counter[str] = Counter()
        uses: Counter[str] = Counter()
        for j in (i - 1, i + 1):
            if not 0 <= j < len(casts) or casts[j].skill_id == cast.skill_id:
                continue
            partner = derived.get(casts[j].skill_id)
            if partner is not None:
                makes.update(partner.makes)
                uses.update(partner.uses)
        one = SkillUsage(
            uses=1,
            targets=cast.targets,
            distance=cast.distance,
            kills=cast.kills,
            target_keywords=_sorted(cast.keywords),
            terrain={cast.terrain: 1},
            partner_makes=_sorted(makes),
            partner_uses=_sorted(uses),
        )
        usage = merge_usage(usage, {cast.skill_id: one})
    return usage
