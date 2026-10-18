"""``trpg map show``、``trpg battle``、``trpg battle replay`` 的實作。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO

from pydantic import ValidationError

from trpg.cli.render import (
    BattleStats,
    describe_event,
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
from trpg.engine.runner import LOG_FORMAT, BattleLog, replay, run_battle
from trpg.engine.setup import BattleSetupError, build_setup, deploy_allies
from trpg.engine.state import BattleState, state_to_json
from trpg.shared.types import Team, UnitId
from trpg.sim.commanders import build_commanded_ai

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

DEFAULT_ALLIES = ("hero_fighter", "hero_archer", "hero_mage")
DEFAULT_ENEMIES = ("bandit", "bandit_archer", "bandit_boss")


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


def default_lineup(library: ContentLibrary, map_id: str) -> tuple[list[str], list[str]]:
    """地圖的預設陣容（``encounter``）。

    沒有時使用 :data:`DEFAULT_ALLIES`／:data:`DEFAULT_ENEMIES`。
    """
    encounter = library.map(map_id).encounter
    if encounter is None:
        return list(DEFAULT_ALLIES), list(DEFAULT_ENEMIES)
    return list(encounter.allies), list(encounter.enemies)


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
    ai: str = "utility",
    weather: str | None = None,
    deploy: list[tuple[int, int]] | None = None,
    ally_commander: str | None = None,
    enemy_commander: str | None = None,
) -> int:
    default_allies, default_enemies = default_lineup(library, map_id)
    setup = build_setup(
        library,
        map_id,
        allies or default_allies,
        enemies or default_enemies,
        max_rounds=rounds_max,
        weather=weather,
    )
    if deploy:
        try:
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


def cmd_replay(path: Path, out: TextIO) -> int:
    try:
        log = BattleLog.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {path}", file=sys.stderr)
        return 1
    except ValidationError as exc:
        print(f"錯誤：{path} 不是有效的戰鬥紀錄：\n{exc}", file=sys.stderr)
        return 1
    if log.format != LOG_FORMAT:
        print(f"錯誤：不支援的紀錄格式 {log.format!r}（預期 {LOG_FORMAT!r}）", file=sys.stderr)
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
