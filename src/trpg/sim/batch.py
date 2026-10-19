"""批次模擬器（Phase 2C-1 3.2–3.4）：同一個戰鬥設定跑多個種子，彙總成 :class:`BatchReport`。

- :class:`BatchSpec` 描述一批戰鬥；:func:`run_batch`／:func:`run_batches` 執行（可用多行程），
  結果 **依種子排序後才彙總**，所以報表與 ``jobs`` 無關。
- 每場戰鬥的例外被捕捉並記為異常（``exception``／``max_actions``），不中斷整批。
- :class:`BatchReport` 可序列化成 JSON（pydantic），也能以 :func:`format_report` 格式化成文字表格。
  報表不含任何時間資訊，相同的輸入必得逐字相同的輸出（執行時間由 CLI 印在標準錯誤）。

``jobs > 1`` 時 ``BatchSpec`` 會傳給工作行程（``fork`` 以外的啟動方式需要它可 pickle：
``policy_factory`` 請用模組層級的可呼叫物件，例如 :class:`UtilityPolicyFactory`，不要用 lambda）。
"""

from __future__ import annotations

import multiprocessing
import statistics
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from pydantic import BaseModel, ConfigDict, TypeAdapter

from trpg.content.environment import AiProfileTable
from trpg.content.library import ContentLibrary
from trpg.engine.ai import Policy
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import DEFAULT_MAX_ACTIONS
from trpg.engine.setup import BattleSetup, build_setup
from trpg.shared.types import Team
from trpg.sim.commanders import CommandedPolicyFactory
from trpg.sim.metrics import (
    CONTROL_STATUSES,
    LONG_BATTLE_ROUNDS,
    BattleMetrics,
    MaxActionsExceeded,
    battle_metrics,
    run_tracked,
)

__all__ = [
    "ANOMALY_KINDS",
    "DEFAULT_MAX_ROUNDS",
    "ONE_SHOT_SEED_LIMIT",
    "REPORT_LIST_ADAPTER",
    "Anomaly",
    "BatchReport",
    "BatchSpec",
    "BattleOutcome",
    "ControlRow",
    "SkillRow",
    "TeamSummary",
    "TemplateRow",
    "UtilityPolicyFactory",
    "build_report",
    "format_report",
    "map_spec",
    "run_batch",
    "run_batches",
]

DEFAULT_MAX_ROUNDS = 30
ONE_SHOT_SEED_LIMIT = 5
"""``one_shot`` 只列出前幾個種子。"""
SEED_LIST_LIMIT = 40
"""文字報表的種子清單上限（JSON 一律完整）。"""
ANOMALY_KINDS: Final = (
    "exception",
    "max_actions",
    "draw",
    "long_battle",
    "chain_limit",
    "boss_burst",
    "one_shot",
    "trigger_limit",
)

_TEAM_LABEL = {"ally": "我方", "enemy": "敵方", "environment": "環境"}


# ---------------------------------------------------------------------------
# 規格與執行
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UtilityPolicyFactory:
    """每場戰鬥新建一個 :class:`~trpg.engine.ai.utility.UtilityAI`（可 pickle）。"""

    profiles: AiProfileTable

    def __call__(self) -> Policy:
        return UtilityAI(self.profiles)


@dataclass(frozen=True)
class BatchSpec:
    """一批戰鬥：同一個設定、多個種子。"""

    name: str
    """報表標題，例如 ``"swamp"``。"""
    setup: BattleSetup
    seeds: tuple[int, ...]
    policy_factory: Callable[[], Policy]
    """每場戰鬥新建一個 policy（避免跨場狀態）。"""
    max_actions: int = DEFAULT_MAX_ACTIONS


def map_spec(
    library: ContentLibrary,
    map_id: str,
    seeds: Sequence[int],
    *,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    ally_commander: str | None = None,
    enemy_commander: str | None = None,
    allies: Sequence[str] | None = None,
) -> BatchSpec:
    """地圖預設陣容（``encounter``）、效用 AI 的 :class:`BatchSpec`。

    ``allies`` 給定時取代 ``encounter`` 的我方（``trpg sim maps --ally-build``；範本須已在
    ``library`` 內，見 :func:`trpg.sim.lineup.build_allies`）。

    指定 ``ally_commander``／``enemy_commander``（:data:`~trpg.sim.commanders.COMMANDER_IDS`）
    時，該陣營由腳本指揮官下戰術指令（Phase 2C-2）。"""
    encounter = library.map(map_id).encounter
    if encounter is None:
        raise ValueError(f"{map_id} 沒有預設陣容（encounter）")
    team = encounter.allies if allies is None else list(allies)
    setup = build_setup(library, map_id, team, encounter.enemies, max_rounds=max_rounds)
    factory: Callable[[], Policy] = UtilityPolicyFactory(library.ai_profiles)
    if ally_commander is not None or enemy_commander is not None:
        factory = CommandedPolicyFactory(library.ai_profiles, ally_commander, enemy_commander)
    return BatchSpec(name=map_id, setup=setup, seeds=tuple(seeds), policy_factory=factory)


@dataclass(frozen=True)
class BattleOutcome:
    """一場戰鬥的結果：指標，或錯誤（``exception``／``max_actions``）。"""

    seed: int
    metrics: BattleMetrics | None = None
    error_kind: str | None = None
    error_text: str = ""


def _last_line(exc: BaseException) -> str:
    lines = str(exc).strip().splitlines()
    return f"{type(exc).__name__}: {lines[-1] if lines else ''}"


def run_one(spec: BatchSpec, seed: int) -> BattleOutcome:
    """跑一場戰鬥並算出指標；任何例外都轉成錯誤結果。"""
    try:
        run = run_tracked(spec.setup, seed, spec.policy_factory(), max_actions=spec.max_actions)
        return BattleOutcome(seed, metrics=battle_metrics(run))
    except MaxActionsExceeded as exc:
        return BattleOutcome(seed, error_kind="max_actions", error_text=_last_line(exc))
    except Exception as exc:
        return BattleOutcome(seed, error_kind="exception", error_text=_last_line(exc))


_WORKER_SPECS: tuple[BatchSpec, ...] = ()


def _worker_init(specs: tuple[BatchSpec, ...]) -> None:
    global _WORKER_SPECS  # noqa: PLW0603 - 行程初始化：每個工作行程只收一次規格
    _WORKER_SPECS = specs


def _worker(task: tuple[int, int]) -> tuple[int, BattleOutcome]:
    index, seed = task
    return index, run_one(_WORKER_SPECS[index], seed)


def run_batches(specs: Sequence[BatchSpec], *, jobs: int = 1) -> list[BatchReport]:
    """執行多批戰鬥（共用同一組工作行程）；回傳與 ``specs`` 同順序的報表。

    報表只依種子排序後的結果彙總，與 ``jobs`` 無關。
    """
    if jobs < 1:
        raise ValueError("jobs 必須 >= 1")
    spec_list = tuple(specs)
    tasks = [(i, seed) for i, spec in enumerate(spec_list) for seed in spec.seeds]
    results: list[tuple[int, BattleOutcome]]
    if jobs == 1 or len(tasks) <= 1:
        results = [(i, run_one(spec_list[i], seed)) for i, seed in tasks]
    else:
        with multiprocessing.get_context("spawn").Pool(
            min(jobs, len(tasks)), initializer=_worker_init, initargs=(spec_list,)
        ) as pool:
            results = pool.map(_worker, tasks, chunksize=1)
    grouped: dict[int, list[BattleOutcome]] = {i: [] for i in range(len(spec_list))}
    for index, outcome in results:
        grouped[index].append(outcome)
    return [
        build_report(
            spec.name,
            sorted(grouped[i], key=lambda o: o.seed),
            equipped=_equipped_skills(spec.setup),
            max_rounds=spec.setup.max_rounds,
        )
        for i, spec in enumerate(spec_list)
    ]


def run_batch(spec: BatchSpec, *, jobs: int = 1) -> BatchReport:
    """執行一批戰鬥並彙總成報表。"""
    return run_batches([spec], jobs=jobs)[0]


def _equipped_skills(setup: BattleSetup) -> tuple[str, ...]:
    return tuple(sorted({s for spawn in setup.units for s in spawn.template.skills}))


# ---------------------------------------------------------------------------
# 報表模型
# ---------------------------------------------------------------------------


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Anomaly(_Model):
    """一種異常：次數與種子（可用 ``trpg battle --map … --seed …`` 重現）。"""

    kind: str
    count: int
    seeds: tuple[int, ...]
    details: dict[int, str]
    """種子 → 說明（例外訊息、Boss 爆發原因、連鎖上限次數……）。"""


class TemplateRow(_Model):
    """一個單位範本（同範本的所有單位實例彙總）。"""

    template_id: str
    team: Team
    instances: int
    dpr: float
    """每個實例的 DPR 的平均。"""
    damage_taken: float
    healing: float
    kills: float
    survival: float
    """戰鬥結束時未倒下的比例。"""
    ap_per_turn: float | None
    """平均每回合花掉的 AP（總 AP ÷ 總回合數）。"""
    shield_provided: float = 0.0
    """每個實例施放的護盾所吸收的傷害（Phase 2D-2 保護指標）。"""
    teammate_survival: float | None = None
    """我方實例：戰鬥結束時隊友（同陣營其他單位）存活人數 ÷ 隊友人數，各實例平均；
    沒有隊友或敵方為 ``None``（Phase 2D-2 保護指標）。"""


class TeamSummary(_Model):
    team: Team
    dpr_direct: float
    """陣營每輪的直接傷害（每場戰鬥的 ``傷害 ÷ 輪數``，再對各場平均）。"""
    dpr_indirect: float
    damage_friendly: float
    """每場平均的友軍誤傷。"""
    environment_damage_taken: float
    """每場平均受到的環境傷害（追溯不到來源）。"""
    shield_absorbed: float = 0.0
    """每場平均被己方護盾吸收的傷害（Phase 2D-1；不計入 DPR 與承受傷害）。"""

    @property
    def dpr(self) -> float:
        return self.dpr_direct + self.dpr_indirect


class ControlRow(_Model):
    """施加者（``ally``／``enemy``／``environment``）每場平均的控制回合。"""

    source: str
    turns: dict[str, float]
    """狀態（stun／frozen／root／slow）→ 每場平均。"""


class SkillRow(_Model):
    skill_id: str
    teams: tuple[str, ...]
    uses_per_battle: float
    hit_rate: float | None
    avg_damage: float | None
    """每次使用造成的直接傷害（只計敵方）。"""
    avg_healed: float | None


class BatchReport(_Model):
    """一批戰鬥的彙總報表。"""

    name: str
    max_rounds: int | None
    battles: int
    completed: int
    ally_wins: int
    enemy_wins: int
    draws: int
    ally_win_rate: float
    enemy_win_rate: float
    draw_rate: float
    rounds_mean: float
    rounds_median: float
    rounds_min: int
    rounds_max: int
    actions_mean: float
    """每場平均的總動作數（含自動結束回合）。"""
    teams: tuple[TeamSummary, ...]
    templates: tuple[TemplateRow, ...]
    control: tuple[ControlRow, ...]
    skills: tuple[SkillRow, ...]
    unused_skills: tuple[str, ...]
    """裝備在某個單位身上、但整批戰鬥從未被使用的技能。"""
    anomalies: tuple[Anomaly, ...]
    scene_events: dict[str, int] = {}
    """場景物件事件的總次數（Phase 3C-5b）：``hurled`` 投擲、``toppled`` 推倒、``pierced`` 穿透。"""

    def anomaly(self, kind: str) -> Anomaly | None:
        return next((a for a in self.anomalies if a.kind == kind), None)

    def team(self, team: Team) -> TeamSummary:
        return next(t for t in self.teams if t.team is team)


REPORT_LIST_ADAPTER: TypeAdapter[list[BatchReport]] = TypeAdapter(list[BatchReport])


# ---------------------------------------------------------------------------
# 彙總
# ---------------------------------------------------------------------------


def _ratio(numerator: int | Fraction, denominator: int | Fraction) -> float:
    return float(Fraction(numerator) / Fraction(denominator)) if denominator else 0.0


def _anomalies(outcomes: Sequence[BattleOutcome]) -> tuple[Anomaly, ...]:
    seeds: dict[str, list[int]] = {k: [] for k in ANOMALY_KINDS}
    details: dict[str, dict[int, str]] = {k: {} for k in ANOMALY_KINDS}
    counts: Counter[str] = Counter()
    for outcome in outcomes:
        if outcome.error_kind is not None:
            kind = outcome.error_kind
            seeds[kind].append(outcome.seed)
            details[kind][outcome.seed] = outcome.error_text
            counts[kind] += 1
            continue
        m = outcome.metrics
        assert m is not None
        if m.result == "draw":
            seeds["draw"].append(m.seed)
            counts["draw"] += 1
        if m.rounds > LONG_BATTLE_ROUNDS:
            seeds["long_battle"].append(m.seed)
            details["long_battle"][m.seed] = f"{m.rounds} 輪"
            counts["long_battle"] += 1
        if m.chain_limit_count:
            seeds["chain_limit"].append(m.seed)
            details["chain_limit"][m.seed] = f"{m.chain_limit_count} 次"
            counts["chain_limit"] += m.chain_limit_count
        if m.trigger_limit_count:
            seeds["trigger_limit"].append(m.seed)
            details["trigger_limit"][m.seed] = f"{m.trigger_limit_count} 次"
            counts["trigger_limit"] += m.trigger_limit_count
        if m.boss_burst is not None:
            seeds["boss_burst"].append(m.seed)
            details["boss_burst"][m.seed] = m.boss_burst
            counts["boss_burst"] += 1
        if m.one_shot_count:
            seeds["one_shot"].append(m.seed)
            details["one_shot"][m.seed] = f"{m.one_shot_count} 次"
            counts["one_shot"] += m.one_shot_count
    out: list[Anomaly] = []
    for kind in ANOMALY_KINDS:
        if not counts[kind]:
            continue
        listed = seeds[kind][:ONE_SHOT_SEED_LIMIT] if kind == "one_shot" else seeds[kind]
        out.append(
            Anomaly(
                kind=kind,
                count=counts[kind],
                seeds=tuple(listed),
                details={s: details[kind][s] for s in listed if s in details[kind]},
            )
        )
    return tuple(out)


def _team_summaries(done: Sequence[BattleMetrics]) -> tuple[TeamSummary, ...]:
    n = len(done)
    out: list[TeamSummary] = []
    for team in (Team.ALLY, Team.ENEMY):
        direct = sum(
            (Fraction(m.team_damage(team, direct=True), max(1, m.rounds)) for m in done),
            Fraction(0),
        )
        indirect = sum(
            (Fraction(m.team_damage(team, direct=False), max(1, m.rounds)) for m in done),
            Fraction(0),
        )
        friendly = sum(u.damage_friendly for m in done for u in m.units if u.team is team)
        env = sum(m.environment_damage.get(team.value, 0) for m in done)
        out.append(
            TeamSummary(
                team=team,
                dpr_direct=_ratio(direct, n),
                dpr_indirect=_ratio(indirect, n),
                damage_friendly=_ratio(friendly, n),
                environment_damage_taken=_ratio(env, n),
                shield_absorbed=_ratio(
                    sum(u.shield_absorbed for m in done for u in m.units if u.team is team), n
                ),
            )
        )
    return tuple(out)


def _mate_survival(team: Team, values: Sequence[Fraction | None]) -> float | None:
    known = [v for v in values if v is not None]
    if team is not Team.ALLY or not known:
        return None
    return _ratio(sum(known, Fraction(0)), len(known))


@dataclass(frozen=True)
class _Instance:
    """一個單位在一場戰鬥中的數字（彙總成範本列之前的中間資料）。"""

    dpr: Fraction
    damage_taken: int
    healing_done: int
    kills: int
    downed: bool
    ap_spent: int
    turns: int
    shield_provided: int
    teammate_alive: Fraction | None


def _template_rows(done: Sequence[BattleMetrics]) -> tuple[TemplateRow, ...]:
    groups: dict[tuple[Team, str], list[_Instance]] = {}
    for m in done:
        for u in m.units:
            mates = [o for o in m.units if o.team is u.team and o.unit_id != u.unit_id]
            alive = Fraction(sum(1 for o in mates if not o.downed), len(mates)) if mates else None
            groups.setdefault((u.team, u.template_id), []).append(
                _Instance(
                    u.dpr,
                    u.damage_taken,
                    u.healing_done,
                    u.kills,
                    u.downed,
                    u.ap_spent,
                    u.turns,
                    u.shield_provided,
                    alive,
                )
            )
    rows: list[TemplateRow] = []
    for (team, template_id), items in sorted(
        groups.items(), key=lambda kv: (kv[0][0] is Team.ENEMY, kv[0][1])
    ):
        n = len(items)
        turns = sum(i.turns for i in items)
        rows.append(
            TemplateRow(
                template_id=template_id,
                team=team,
                instances=n,
                dpr=_ratio(sum((i.dpr for i in items), Fraction(0)), n),
                damage_taken=_ratio(sum(i.damage_taken for i in items), n),
                healing=_ratio(sum(i.healing_done for i in items), n),
                kills=_ratio(sum(i.kills for i in items), n),
                survival=_ratio(sum(1 for i in items if not i.downed), n),
                ap_per_turn=_ratio(sum(i.ap_spent for i in items), turns) if turns else None,
                shield_provided=_ratio(sum(i.shield_provided for i in items), n),
                teammate_survival=_mate_survival(team, [i.teammate_alive for i in items]),
            )
        )
    return tuple(rows)


def _control_rows(done: Sequence[BattleMetrics]) -> tuple[ControlRow, ...]:
    n = len(done)
    totals: dict[str, Counter[str]] = {
        "ally": Counter(),
        "enemy": Counter(),
        "environment": Counter(),
    }
    for m in done:
        for u in m.units:
            totals[u.team.value].update(u.control_inflicted)
        totals["environment"].update(m.environment_control)
    return tuple(
        ControlRow(
            source=source,
            turns={status: _ratio(totals[source][status], n) for status in CONTROL_STATUSES},
        )
        for source in ("ally", "enemy", "environment")
    )


def _skill_rows(done: Sequence[BattleMetrics]) -> tuple[SkillRow, ...]:
    n = len(done)
    uses: Counter[str] = Counter()
    rolls: Counter[str] = Counter()
    hits: Counter[str] = Counter()
    damage: Counter[str] = Counter()
    healed: Counter[str] = Counter()
    teams: dict[str, set[str]] = {}
    for m in done:
        for skill_id, s in m.skills.items():
            uses[skill_id] += s.uses
            rolls[skill_id] += s.rolls
            hits[skill_id] += s.hits
            damage[skill_id] += s.damage
            healed[skill_id] += s.healed
        for skill_id, users in m.skill_users.items():
            teams.setdefault(skill_id, set()).update(users)
    rows = [
        SkillRow(
            skill_id=skill_id,
            teams=tuple(sorted(teams.get(skill_id, ()))),
            uses_per_battle=_ratio(uses[skill_id], n),
            hit_rate=_ratio(hits[skill_id], rolls[skill_id]) if rolls[skill_id] else None,
            avg_damage=_ratio(damage[skill_id], uses[skill_id]) if uses[skill_id] else None,
            avg_healed=_ratio(healed[skill_id], uses[skill_id]) if healed[skill_id] else None,
        )
        for skill_id in uses
    ]
    return tuple(sorted(rows, key=lambda r: (-r.uses_per_battle, r.skill_id)))


def _scene_events(done: Sequence[BattleMetrics]) -> dict[str, int]:
    total: Counter[str] = Counter()
    for m in done:
        total.update(m.scene_events)
    return dict(sorted(total.items()))


def build_report(
    name: str,
    outcomes: Sequence[BattleOutcome],
    *,
    equipped: Sequence[str] = (),
    max_rounds: int | None = None,
) -> BatchReport:
    """把（依種子排序的）戰鬥結果彙總成報表；純函式。"""
    ordered = sorted(outcomes, key=lambda o: o.seed)
    done = [o.metrics for o in ordered if o.metrics is not None]
    n = len(done)
    wins = Counter(m.result for m in done)
    rounds = [m.rounds for m in done]
    skills = _skill_rows(done)
    used = {r.skill_id for r in skills if r.uses_per_battle > 0}
    return BatchReport(
        name=name,
        max_rounds=max_rounds,
        battles=len(ordered),
        completed=n,
        ally_wins=wins["ally"],
        enemy_wins=wins["enemy"],
        draws=wins["draw"],
        ally_win_rate=_ratio(wins["ally"], n),
        enemy_win_rate=_ratio(wins["enemy"], n),
        draw_rate=_ratio(wins["draw"], n),
        rounds_mean=_ratio(sum(rounds), n),
        rounds_median=float(statistics.median(rounds)) if rounds else 0.0,
        rounds_min=min(rounds, default=0),
        rounds_max=max(rounds, default=0),
        actions_mean=_ratio(sum(m.actions for m in done), n),
        teams=_team_summaries(done),
        templates=_template_rows(done),
        control=_control_rows(done),
        skills=skills,
        unused_skills=tuple(sorted(set(equipped) - used)),
        anomalies=_anomalies(ordered),
        scene_events=_scene_events(done),
    )


# ---------------------------------------------------------------------------
# 文字報表
# ---------------------------------------------------------------------------


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def _seed_list_text(items: Sequence[str], total: int) -> str:
    shown = ", ".join(items[:SEED_LIST_LIMIT])
    extra = total - SEED_LIST_LIMIT
    return shown + (f" …（共 {total} 個，完整清單見 --json）" if extra > 0 else "")


def _seed_list(seeds: Sequence[int]) -> str:
    return _seed_list_text([str(s) for s in seeds], len(seeds))


_DETAIL_LINES = frozenset({"exception", "max_actions", "boss_burst"})


def format_report(report: BatchReport) -> str:
    """報表的文字格式（繁體中文；每張地圖一節）。"""
    r = report
    out: list[str] = []
    cap = f"，max_rounds={r.max_rounds}" if r.max_rounds is not None else ""
    out.append(f"## {r.name}（{r.battles} 場，完成 {r.completed} 場{cap}）")
    out.append("")
    out.append(
        f"勝負：我方 {r.ally_wins}（{_pct(r.ally_win_rate)}）／敵方 {r.enemy_wins}"
        f"（{_pct(r.enemy_win_rate)}）／平手 {r.draws}（{_pct(r.draw_rate)}）"
    )
    out.append(
        f"輪數：平均 {r.rounds_mean:.2f}、中位數 {r.rounds_median:g}、"
        f"最小 {r.rounds_min}、最大 {r.rounds_max}"
    )
    out.append(f"動作數：每場平均 {r.actions_mean:.1f}")
    out.append("")
    out.append("陣營 DPR（每輪傷害，每場平均）與環境：")
    out += _table(
        ["陣營", "DPR", "直接", "間接", "友軍誤傷／場", "受環境傷害／場", "護盾吸收／場"],
        [
            [
                _TEAM_LABEL[t.team.value],
                f"{t.dpr:.2f}",
                f"{t.dpr_direct:.2f}",
                f"{t.dpr_indirect:.2f}",
                f"{t.damage_friendly:.2f}",
                f"{t.environment_damage_taken:.2f}",
                f"{t.shield_absorbed:.2f}",
            ]
            for t in r.teams
        ],
    )
    out.append("")
    out.append("單位範本（每個實例的平均）：")
    out += _table(
        [
            "範本",
            "陣營",
            "實例",
            "DPR",
            "承受傷害",
            "治療量",
            "護盾提供",
            "擊倒",
            "存活率",
            "隊友存活率",
            "AP／回合",
        ],
        [
            [
                t.template_id,
                _TEAM_LABEL[t.team.value],
                str(t.instances),
                f"{t.dpr:.2f}",
                f"{t.damage_taken:.1f}",
                f"{t.healing:.1f}",
                f"{t.shield_provided:.1f}",
                f"{t.kills:.2f}",
                _pct(t.survival),
                "—" if t.teammate_survival is None else _pct(t.teammate_survival),
                "—" if t.ap_per_turn is None else f"{t.ap_per_turn:.2f}",
            ]
            for t in r.templates
        ],
    )
    out.append("")
    out.append("控制回合（施加者 → 目標在自己回合開始時帶著該狀態；每場平均）：")
    out += _table(
        ["施加者", *CONTROL_STATUSES],
        [
            [_TEAM_LABEL[c.source], *(f"{c.turns[s]:.2f}" for s in CONTROL_STATUSES)]
            for c in r.control
        ],
    )
    out.append("")
    out.append("技能使用：")
    if r.skills:
        out += _table(
            ["技能", "陣營", "次／場", "命中率", "平均傷害／次", "平均治療／次"],
            [
                [
                    s.skill_id,
                    "、".join(_TEAM_LABEL[t] for t in s.teams) or "—",
                    f"{s.uses_per_battle:.2f}",
                    "—" if s.hit_rate is None else _pct(s.hit_rate),
                    "—" if s.avg_damage is None else f"{s.avg_damage:.1f}",
                    "—" if s.avg_healed is None else f"{s.avg_healed:.1f}",
                ]
                for s in r.skills
            ],
        )
    else:
        out.append("（沒有技能被使用）")
    out.append("")
    out.append("從未使用的技能：" + ("、".join(r.unused_skills) if r.unused_skills else "無"))
    if r.scene_events:
        labels = {"hurled": "投擲物件", "toppled": "推倒", "pierced": "穿透"}
        counts = "、".join(f"{labels[k]} {v} 次" for k, v in r.scene_events.items())
        out.append(f"場景物件（整批合計）：{counts}")
    out.append("")
    if not r.anomalies:
        out.append("異常：無")
    else:
        out.append("異常：")
        for a in r.anomalies:
            if a.kind in _DETAIL_LINES:
                out.append(f"- {a.kind} ×{a.count}：種子 {_seed_list(a.seeds)}")
                for seed, text in list(a.details.items())[:SEED_LIST_LIMIT]:
                    out.append(f"    種子 {seed}：{text}")
                continue
            labeled = [f"{s}（{a.details[s]}）" if s in a.details else str(s) for s in a.seeds]
            out.append(f"- {a.kind} ×{a.count}：種子 {_seed_list_text(labeled, len(a.seeds))}")
    return "\n".join(out)
