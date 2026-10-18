"""隨機技能的執行驗收（``docs/phases/Phase2B計畫.md`` 5.2）。

對每個種子 ``compose_random_skill`` 組出技能，然後在 ``test_flat_6x6`` 上：

1. 建立戰鬥：施放者（依 ``weapon_req`` 配相容武器、法力充足）、1 名友方、2 名敵方；嘗試 3 種站位
   （敵人相鄰、距離 3、距離 5），直到技能出現在 ``legal_actions``。有條件的技能先把場面布置成
   條件成立（目標 HP 低、帶有狀態、站在表面上、施放者較高或 HP 低）。
2. 對每個合法選取（最多 8 個，平均抽樣）在 ``clone`` 上 ``resolve``（另外 ``preview``），
   不得拋出例外。
3. 每 10 個技能挑 1 個，讓施放者裝備它，用 ``UtilityAI`` 打完一場戰鬥（上限 20 輪），
   不得拋出例外。

:func:`run_fuzz` 回傳 :class:`FuzzReport`，:func:`format_report` 印出摘要。摘要不含時間，
同樣的參數必得完全相同的文字（確定性）。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from fractions import Fraction

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary, Ruleset
from trpg.content.skills import SkillDef, SkillTable
from trpg.engine import (
    BattleSetup,
    BattleState,
    UnitSpawn,
    UseSkill,
    legal_actions,
    preview,
    resolve,
    start_battle,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import run_battle
from trpg.engine.state import StatusInstance, Tile
from trpg.shared.types import Surface, Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.random_composer import compose_with_stats
from trpg.skillgen.skill_yaml import skill_to_yaml
from trpg.skillgen.validate import validate_skill

__all__ = [
    "BATTLE_EVERY",
    "FuzzReport",
    "SkillOutcome",
    "battle_setup",
    "caster_base",
    "check_skill",
    "format_report",
    "run_fuzz",
]

BATTLE_EVERY = 10
MAX_SELECTIONS = 8
MAX_ROUNDS = 20
ARENA_MAP = "test_flat_6x6"
_CASTER_POS = (0, 3)
_ALLY_POS = (0, 4)
_DISTANCES = (1, 3, 5)
_BASE_UNIT = {
    "melee": "hero_fighter",
    "ranged": "hero_archer",
    "focus": "hero_mage",
    "any": "hero_mage",
}
_BINS = 10
_BIN_LOW = Fraction(70, 100)
_BIN_HIGH = Fraction(1)
_MANA = 99
_STATUS_TURNS = 3
_MIN_TIER, _MAX_TIER = 1, 5


@dataclass(slots=True)
class SkillOutcome:
    """一個技能的執行結果。``error`` 為例外的最後一行（型別與訊息）。"""

    seed: int
    skill: SkillDef
    attempts: int
    violations: int = 0
    castable: bool = False
    selections: int = 0
    error: str | None = None
    battle_ran: bool = False
    battle_winner: str | None = None
    ratio: Fraction = Fraction(0)


@dataclass(slots=True)
class FuzzReport:
    """全部技能的結果。"""

    seed_start: int
    outcomes: list[SkillOutcome] = field(default_factory=list)
    compose_errors: list[tuple[int, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 戰場
# ---------------------------------------------------------------------------


def _unit_template(
    library: ContentLibrary, base: str, *, skills: tuple[str, ...], reactions: bool, mana: int
) -> UnitTemplate:
    data = library.unit(base).model_dump()
    data.update(skills=list(skills), max_mana=mana)
    if not reactions:
        data["reactions"] = []
    return UnitTemplate.model_validate(data)


def _ruleset_with(library: ContentLibrary, skill: SkillDef) -> Ruleset:
    if skill.id in library.skills:  # 內容庫裡的技能（示範技能）已在規則包內
        return library.ruleset
    rules = library.ruleset.model_copy(
        update={"skills": SkillTable(skills=(*library.ruleset.skills.skills, skill))}
    )
    rules.model_post_init(None)
    return rules


def _spawn(
    library: ContentLibrary, template: UnitTemplate, team: Team, pos: tuple[int, int] | None
) -> UnitSpawn:
    return UnitSpawn(template=template, weapon=library.weapon_of(template), team=team, position=pos)


def _enemy_positions(distance: int) -> list[tuple[int, int]]:
    first = (_CASTER_POS[0] + distance, _CASTER_POS[1])
    second = (first[0] + 1, first[1]) if first[0] + 1 <= _MAX_X else (first[0], first[1] - 1)
    return [first, second]


_MAX_X = 5


def _arena_state(library: ContentLibrary, skill: SkillDef, distance: int) -> BattleState:
    """施放者拿到回合與滿 AP 的戰場：施放者、1 名友方、2 名敵方。"""
    caster = _unit_template(
        library, _BASE_UNIT[skill.weapon_req], skills=(skill.id,), reactions=False, mana=_MANA
    )
    ally = _unit_template(library, "hero_archer", skills=(), reactions=False, mana=0)
    foe = _unit_template(library, "bandit", skills=(), reactions=False, mana=0)
    foes = _enemy_positions(distance)
    base = library.map(ARENA_MAP)
    arena = base.model_copy(
        update={
            "start_zones": {
                Team.ALLY: (_CASTER_POS, _ALLY_POS),
                Team.ENEMY: tuple(foes),
            }
        }
    )
    units = (
        _spawn(library, caster, Team.ALLY, _CASTER_POS),
        _spawn(library, ally, Team.ALLY, _ALLY_POS),
        _spawn(library, foe, Team.ENEMY, foes[0]),
        _spawn(library, foe, Team.ENEMY, foes[1]),
    )
    setup = BattleSetup(
        map=arena, ruleset=_ruleset_with(library, skill), units=units, max_rounds=MAX_ROUNDS
    )
    return _give_turn(start_battle(setup, 0), _caster_id(units))


def _caster_id(units: Sequence[UnitSpawn]) -> UnitId:
    assert units[0].template.skills
    return UnitId("unit_0001")


def _give_turn(state: BattleState, unit_id: UnitId) -> BattleState:
    """複本：行動者換成 ``unit_id``，並給滿 AP 與移動點數。"""
    s = state.clone()
    s.active_unit = unit_id
    s.turn_pos = s.turn_order.index(unit_id)
    unit = s.units[unit_id]
    unit.ap = s.ruleset.core.ap_per_turn
    unit.move_points = unit.speed
    return s


def _conditions(skill: SkillDef) -> list[tuple[str, int | None, str | None]]:
    """技能與效果上的條件：``(類型, permille, 狀態或表面)``。"""
    found = [skill.condition] if skill.condition is not None else []
    found += [e.condition for e in skill.effects if e.condition is not None]
    return [
        (c.type, c.permille, c.status or (c.surface.value if c.surface is not None else None))
        for c in found
    ]


def _prepare(state: BattleState, skill: SkillDef) -> None:
    """把場面布置成技能的條件成立（直接修改 ``state``）。"""
    caster = state.units[UnitId("unit_0001")]
    others = [u for u in state.units.values() if u.id != caster.id]
    for kind, _, name in _conditions(skill):
        if kind == "target_hp_below":
            for unit in others:
                unit.hp = 1
        elif kind == "self_hp_below":
            caster.hp = 1
        elif kind == "target_has_status" and name is not None:
            for unit in others:
                unit.statuses.append(StatusInstance(name, _STATUS_TURNS))
        elif kind == "target_on_surface" and name is not None:
            for unit in others:
                x, y = unit.xy
                state.set_tile(x, y, _with_surface(state.tile(x, y), Surface(name)))
        elif kind == "height_advantage":
            x, y = caster.xy
            tile = state.tile(x, y)
            state.set_tile(
                x,
                y,
                Tile(
                    tile.height + 1,
                    tile.terrain,
                    tile.surface,
                    tile.surface_remaining,
                    tile.surface_team,
                    tile.object_id,
                ),
            )


def _with_surface(tile: Tile, surface: Surface) -> Tile:
    return Tile(tile.height, tile.terrain, surface, None, None, tile.object_id)


def _skill_actions(state: BattleState, skill: SkillDef) -> list[UseSkill]:
    return [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == skill.id]


def _sample(items: list[UseSkill], limit: int) -> list[UseSkill]:
    if len(items) <= limit:
        return items
    return [items[i * len(items) // limit] for i in range(limit)]


def _last_line(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}"
    return text.strip().splitlines()[-1] if text.strip() else type(exc).__name__


def _try_cast(library: ContentLibrary, outcome: SkillOutcome) -> None:
    """3 種站位直到技能合法；對每個合法選取 ``resolve``（與 ``preview``）。"""
    skill = outcome.skill
    for distance in _DISTANCES:
        state = _arena_state(library, skill, distance)
        _prepare(state, skill)
        actions = _skill_actions(state, skill)
        if not actions:
            continue
        outcome.castable = True
        for action in _sample(actions, MAX_SELECTIONS):
            preview(state.clone(), action)
            resolve(state.clone(), action)
            outcome.selections += 1
        return


def caster_base(skill: SkillDef) -> str:
    """施放者的範本 ID（依技能的 ``weapon_req`` 配相容武器的英雄）。"""
    return _BASE_UNIT[skill.weapon_req]


def battle_setup(
    library: ContentLibrary,
    skill: SkillDef,
    *,
    ally: str = "hero_archer",
    enemies: Sequence[str] = ("bandit", "bandit_archer"),
) -> BattleSetup:
    """AI 對戰用的設定：施放者（只裝備這個技能）＋一名友方 對 ``enemies``，``test_flat_6x6``。

    預設是友方弓手對盜賊與盜賊弓手（隨機技能驗收用）；``trpg sim skills`` 改用沒有技能的標準隊友
    與同階標準敵人。
    """
    caster = _unit_template(
        library, _BASE_UNIT[skill.weapon_req], skills=(skill.id,), reactions=True, mana=_MANA
    )
    friend = library.unit(ally)
    foes = tuple(library.unit(e) for e in enemies)
    units = [_spawn(library, caster, Team.ALLY, None), _spawn(library, friend, Team.ALLY, None)]
    units += [_spawn(library, f, Team.ENEMY, None) for f in foes]
    return BattleSetup(
        map=library.map(ARENA_MAP),
        ruleset=_ruleset_with(library, skill),
        units=tuple(units),
        max_rounds=MAX_ROUNDS,
    )


def _try_battle(library: ContentLibrary, outcome: SkillOutcome) -> None:
    run = run_battle(
        battle_setup(library, outcome.skill), outcome.seed, UtilityAI(library.ai_profiles)
    )
    outcome.battle_ran = True
    winner = run.state.winner
    outcome.battle_winner = "平手" if winner is None else winner.display_name


def check_skill(
    library: ContentLibrary, seed: int, *, with_battle: bool, attempts: int, skill: SkillDef
) -> SkillOutcome:
    """驗證與執行一個技能；例外記在 ``error``（不往外拋）。"""
    outcome = SkillOutcome(seed=seed, skill=skill, attempts=attempts)
    outcome.violations = len(validate_skill(skill, library))
    outcome.ratio = skill_budget(skill, library).ratio
    steps: list[Callable[[ContentLibrary, SkillOutcome], None]] = [_try_cast]
    if with_battle:
        steps.append(_try_battle)
    for step in steps:
        try:
            step(library, outcome)
        except Exception as exc:
            outcome.error = f"{step.__name__.removeprefix('_try_')}：{_last_line(exc)}"
            break
    return outcome


def run_fuzz(
    library: ContentLibrary,
    *,
    count: int,
    seed_start: int = 0,
    progress: Callable[[int], None] | None = None,
) -> FuzzReport:
    """組出並驗收 ``seed_start … seed_start + count − 1`` 的隨機技能。"""
    report = FuzzReport(seed_start)
    for index in range(count):
        seed = seed_start + index
        try:
            composed = compose_with_stats(seed, library=library)
        except Exception as exc:
            report.compose_errors.append((seed, _last_line(exc)))
            continue
        report.outcomes.append(
            check_skill(
                library,
                seed,
                with_battle=index % BATTLE_EVERY == 0,
                attempts=composed.attempts,
                skill=composed.skill,
            )
        )
        if progress is not None:
            progress(index + 1)
    return report


# ---------------------------------------------------------------------------
# 摘要
# ---------------------------------------------------------------------------


def _distribution(
    title: str, counter: Counter[str], total: int, order: Sequence[str] = ()
) -> list[str]:
    keys = [k for k in order if k in counter] + sorted(k for k in counter if k not in order)
    lines = [f"{title}："]
    for key in keys:
        share = counter[key] / total * 100 if total else 0
        lines.append(f"  {key:<18}{counter[key]:>5}  {share:5.1f}%")
    return lines


def _histogram(ratios: list[Fraction]) -> list[str]:
    width = (_BIN_HIGH - _BIN_LOW) / _BINS
    bins = [0] * _BINS
    for r in ratios:
        bins[min(max(int((r - _BIN_LOW) / width), 0), _BINS - 1)] += 1
    peak = max(bins) or 1
    lines = ["預算比例分佈（total ÷ 可用預算，10 個區間）："]
    for i, n in enumerate(bins):
        low, high = _BIN_LOW + width * i, _BIN_LOW + width * (i + 1)
        bar = "#" * (n * 30 // peak)
        lines.append(f"  {float(low) * 100:4.0f}%–{float(high) * 100:3.0f}%  {n:>5}  {bar}")
    return lines


def format_report(report: FuzzReport) -> str:
    """摘要文字（不含時間；同樣的參數必得完全相同的結果）。"""
    outcomes = report.outcomes
    total = len(outcomes) + len(report.compose_errors)
    skills = [o.skill for o in outcomes]
    valid = sum(1 for o in outcomes if o.violations == 0)
    castable = sum(1 for o in outcomes if o.castable)
    errors = [o for o in outcomes if o.error is not None]
    battles = [o for o in outcomes if o.battle_ran]
    last = report.seed_start + total - 1
    lines = [f"隨機技能驗收：種子 {report.seed_start}–{last}，共 {total} 個"]
    lines.append(f"  組合成功 {len(outcomes)}/{total}；通過驗證 {valid}/{len(outcomes)}")
    rate = castable / len(outcomes) * 100 if outcomes else 0
    selections = sum(o.selections for o in outcomes)
    lines.append(
        f"  可施放 {castable}/{len(outcomes)}（{rate:.1f}%）；合法選取共執行 {selections} 次"
    )
    winners = Counter(o.battle_winner for o in battles)
    lines.append(
        f"  AI 對戰 {len(battles)} 場"
        f"（我方勝 {winners['我方']}、敵方勝 {winners['敵方']}、平手 {winners['平手']}）"
    )
    lines.append(f"  例外 {len(errors) + len(report.compose_errors)} 個")
    attempts = [o.attempts for o in outcomes]
    mean = Fraction(sum(attempts), len(attempts)) if attempts else Fraction(0)
    most = max(attempts, default=1) - 1
    lines.append(f"  平均重抽次數 {float(mean - 1):.3f}（最多 {most} 次；0 表示第一次就成功）")
    lines.append("")
    lines += _distribution("骨架", Counter(s.skeleton for s in skills), len(skills))
    lines += _distribution(
        "稀有度",
        Counter(s.rarity for s in skills),
        len(skills),
        ("common", "rare", "epic", "legendary"),
    )
    lines += _distribution("階級", Counter(f"T{s.tier}" for s in skills), len(skills))
    lines += _distribution("形狀", Counter(s.shape.type for s in skills), len(skills))
    lines += _distribution("AP", Counter(f"AP {s.ap_cost}" for s in skills), len(skills))
    lines += _distribution("分類", Counter(s.category for s in skills), len(skills))
    lines.append("")
    lines += _histogram([o.ratio for o in outcomes])
    lines += _problem_lines(report, errors)
    return "\n".join(lines) + "\n"


def _problem_lines(report: FuzzReport, errors: list[SkillOutcome]) -> list[str]:
    lines: list[str] = []
    bad = [o for o in report.outcomes if o.violations or not o.castable]
    for seed, message in report.compose_errors:
        lines += ["", f"組合失敗：種子 {seed}：{message}"]
    for outcome in errors + [o for o in bad if o.error is None]:
        why = outcome.error or ("未通過驗證" if outcome.violations else "沒有合法的選取")
        lines += ["", f"問題：種子 {outcome.seed}：{why}", skill_to_yaml(outcome.skill).rstrip()]
    return lines
