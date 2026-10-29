"""``trpg map show``、``trpg battle``、``trpg battle replay`` 的實作。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO

from pydantic import ValidationError

from trpg.cli.render import (
    BattleStats,
    render_battle_grid,
    render_legend,
    render_map,
    render_telegraph,
    render_unit_table,
)
from trpg.content.library import ContentLibrary
from trpg.engine.actions import Move, Step
from trpg.engine.ai import Policy
from trpg.engine.ai.orders import (
    FocusTarget,
    HoldPosition,
    OrderRecord,
    OrderSet,
    Protect,
    RetreatTo,
    TacticalOrder,
    UseEnvironment,
)
from trpg.engine.ai.simple import choose_action
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.environment import telegraph
from trpg.engine.events import EVENT_LIST_ADAPTER, EventBase, RoundStarted, UnitMoved
from trpg.engine.results import ResolveResult
from trpg.engine.runner import (
    BattleLog,
    log_format_problem,
    log_replay_problem,
    replay,
    run_battle,
)
from trpg.engine.setup import BattleSetupError, assign_races, build_setup, deploy_allies
from trpg.engine.state import BattleState, state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.types import Team, UnitId
from trpg.sim.commanders import build_commanded_ai
from trpg.sim.lineup import (
    DEFAULT_ALLIES,
    DEFAULT_ENEMIES,
    UnknownBuildError,
    build_allies,
    default_lineup,
)

__all__ = [
    "DEFAULT_ALLIES",
    "DEFAULT_ENEMIES",
    "cmd_battle",
    "cmd_map_show",
    "cmd_replay",
    "default_lineup",
    "describe_order",
    "describe_order_record",
]


def cmd_map_show(library: ContentLibrary, map_id: str, out: TextIO) -> int:
    map_def = library.map(map_id)
    print(render_map(map_def, library.ruleset), file=out)
    return 0


def cmd_map_list(library: ContentLibrary, out: TextIO) -> int:
    """``trpg map list``：每張地圖的 ID、類型、大小、名稱，以及是否有預設遭遇。"""
    print("| 地圖 | 類型 | 大小 | 名稱 | 遭遇 |", file=out)
    print("|---|---|---|---|---|", file=out)
    for map_id, map_def in sorted(library.maps.items()):
        encounter = "有" if map_def.encounter is not None else "—"
        print(
            f"| {map_id} | {map_def.archetype} | {map_def.width}×{map_def.height} "
            f"| {map_def.name_zh} | {encounter} |",
            file=out,
        )
    return 0


def _walk_summary(action: Step, events: list[EventBase], state: BattleState) -> str | None:
    if not isinstance(action, Move):
        return None
    steps = [e for e in events if isinstance(e, UnitMoved) and e.mode == "walk"]
    if not steps:
        return None
    unit = state.units[action.unit_id]
    cost = sum(e.cost for e in steps)
    start, end = steps[0].from_pos, steps[-1].to_pos
    return (
        f"  {unit.name_zh} 從 ({start.x}, {start.y}) 移動到 ({end.x}, {end.y})（消耗 {cost} 移動）"
    )


def describe_order(order: TacticalOrder, state: BattleState) -> str:
    """一條戰術指令的繁體中文說明（單位以名稱顯示）。"""

    def name(uid: UnitId) -> str:
        unit = state.units.get(uid)
        return uid if unit is None else unit.name_zh

    match order:
        case FocusTarget(target=target):
            return f"集火 {name(target)}"
        case HoldPosition(at=at, radius=radius):
            return f"守住 ({at[0]}, {at[1]}) 半徑 {radius}"
        case RetreatTo(at=at):
            return f"撤往 ({at[0]}, {at[1]})"
        case Protect(ward=ward):
            return f"保護 {name(ward)}"
        case UseEnvironment():
            return "利用環境"
    raise AssertionError(order)  # pragma: no cover


def describe_order_record(record: OrderRecord, state: BattleState) -> list[str]:
    """指揮官下達的指令（新指令一行；被忽略的指令另起一行附原因）。"""
    parts = [describe_order(o, state) for o in record.orders.team_orders]
    for uid in sorted(record.orders.unit_orders):
        unit = state.units.get(uid)
        label = uid if unit is None else unit.name_zh
        orders = record.orders.unit_orders[uid]
        text = "、".join(describe_order(o, state) for o in orders) or "無"
        parts.append(f"{label}：{text}")
    lines = [f"{record.team.display_name}指令：{'；'.join(parts) if parts else '（無）'}"]
    lines.extend(
        f"  （忽略：{describe_order(i.order, state)}，{i.reason}）" for i in record.ignored
    )
    return lines


class _Printer:
    """依事件順序印出戰鬥紀錄；每輪開始時印出戰場網格與單位狀態。"""

    def __init__(self, out: TextIO) -> None:
        self.out = out

    def __call__(self, action: Step | None, result: ResolveResult) -> None:
        state = result.state
        walk_printed = False
        for event in result.events:
            if isinstance(event, RoundStarted):
                print(f"\n=== 第 {event.round} 輪 ===", file=self.out)
                print(render_battle_grid(state), file=self.out)
                legend = render_legend(state)
                if legend:
                    print(legend, file=self.out)
                print(render_unit_table(state), file=self.out)
                forecast = render_telegraph(state, telegraph(state))
                if forecast:
                    print(forecast, file=self.out)
                print("", file=self.out)
                continue
            if isinstance(event, UnitMoved) and event.mode == "walk":
                if not walk_printed and action is not None:
                    line = _walk_summary(action, result.events, state)
                    if line:
                        print(line, file=self.out)
                    walk_printed = True
                continue
            text = describe_event(event, state)
            if text is not None:
                print(text, file=self.out)


def cmd_battle(
    library: ContentLibrary,
    *,
    map_id: str,
    seed: int,
    rounds_max: int,
    allies: list[str] | None,
    enemies: list[str] | None,
    log_json: Path | None,
    out: TextIO,
    ally_builds: list[str] | None = None,
    ai: str = "utility",
    weather: str | None = None,
    objective: str | None = None,
    deploy: list[tuple[int, int]] | None = None,
    ally_commander: str | None = None,
    enemy_commander: str | None = None,
    ally_races: list[str] | None = None,
    enemy_races: list[str] | None = None,
) -> int:
    default_allies, default_enemies = default_lineup(library, map_id)
    if ally_builds:
        try:
            library, allies = build_allies(library, ally_builds)
        except UnknownBuildError as exc:
            print(f"錯誤：{exc}", file=sys.stderr)
            return 2
    try:
        chosen = None if objective is None else library.map(map_id).objective_for(objective)
    except ValueError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2
    setup = build_setup(
        library,
        map_id,
        allies or default_allies,
        enemies or default_enemies,
        max_rounds=rounds_max,
        weather=weather,
        objective=chosen,
    )
    try:
        setup = assign_races(setup, Team.ALLY, ally_races or [])  # 種族（Phase 3R-2）
        setup = assign_races(setup, Team.ENEMY, enemy_races or [])
        if deploy:
            setup = deploy_allies(setup, deploy)
    except BattleSetupError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2
    policy: Policy = UtilityAI(library.ai_profiles) if ai == "utility" else choose_action
    if ally_commander is not None or enemy_commander is not None:
        if ai != "utility":
            print("錯誤：指揮官只能搭配效用 AI（--ai utility）", file=sys.stderr)
            return 2

        shown: dict[Team, OrderSet] = {}

        def show(record: OrderRecord, state: BattleState) -> None:
            """只印出與該陣營上一次不同的指令（紀錄 ``BattleLog.orders`` 仍保留每一次）。"""
            if shown.get(record.team) == record.orders and not record.ignored:
                return
            shown[record.team] = record.orders
            for line in describe_order_record(record, state):
                print(line, file=out)

        policy = build_commanded_ai(
            library.ai_profiles, ally=ally_commander, enemy=enemy_commander, on_order=show
        )
    run = run_battle(setup, seed, policy, on_step=_Printer(out))
    state = run.state
    print("\n=== 結算 ===", file=out)
    print(render_battle_grid(state), file=out)
    winner = state.winner.display_name + "勝利" if state.winner is not None else "平手"
    print(
        f"勝方：{winner}（第 {state.round} 輪結束，{len(run.actions)} 個動作，"
        f"{len(run.events)} 個事件）",
        file=out,
    )
    print(BattleStats.from_events(run.events, state).render(state), file=out)
    if log_json is not None:
        log_json.write_text(run.to_log().model_dump_json(indent=1), encoding="utf-8")
        print(f"\n已寫入戰鬥紀錄：{log_json}", file=out)
    return 0


def _old_format(text: str) -> str | None:
    """紀錄 JSON 的 ``format`` 不是目前版本時的說明；不是 JSON 物件時交給後面的解析報錯。"""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict) or "format" not in raw:
        return None
    return log_format_problem(raw["format"])


def cmd_replay(path: Path, out: TextIO) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {path}", file=sys.stderr)
        return 1
    old = _old_format(text)
    if old is not None:  # 舊版紀錄先說明版本（結構可能已經解析不了，3W-5b）
        print(f"錯誤：{path}：{old}", file=sys.stderr)
        return 1
    try:
        log = BattleLog.model_validate_json(text)
    except ValidationError as exc:
        print(f"錯誤：{path} 不是有效的戰鬥紀錄：\n{exc}", file=sys.stderr)
        return 1
    problem = log_replay_problem(log)
    if problem is not None:
        print(f"錯誤：{path}：{problem}", file=sys.stderr)
        return 1
    run = replay(log.setup, log.seed, log.actions)
    same_state = state_to_json(run.state) == state_to_json(log.final_state)
    recorded = EVENT_LIST_ADAPTER.dump_json(log.events)
    replayed = EVENT_LIST_ADAPTER.dump_json(run.events)  # type: ignore[arg-type]
    same_events = recorded == replayed
    if same_state and same_events:
        print(
            f"重播驗證通過：{len(log.actions)} 個動作、{len(log.events)} 個事件，"
            f"最終狀態一致（{log.final_state.map_id}，種子 {log.seed}）。",
            file=out,
        )
        return 0
    problems = []
    if not same_state:
        problems.append("最終狀態不一致")
    if not same_events:
        first = next(
            (i for i, (a, b) in enumerate(zip(log.events, run.events, strict=False)) if a != b),
            min(len(log.events), len(run.events)),
        )
        problems.append(f"事件不一致（第 {first} 個事件開始不同）")
    print("重播驗證失敗：" + "；".join(problems), file=sys.stderr)
    return 1
