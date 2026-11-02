"""誓約在大世界戰鬥裡的接線（Phase 5C-3；06 6.26、#106；``docs/phases/Phase5計畫.md`` 24.7）。

- :func:`oath_setup`：角色有誓約時的引擎設定（主角＝``units[0]``、模板的判定填好參數、難度 →
  加成狀態、破誓狀態與回合數）；``prepare_battle`` 放進 ``BattleSetup.oath``。
- :func:`oath_events`：從這場戰鬥的引擎事件（``oath_broken``）產生世界事件——違反（戰鬥中或戰鬥結束
  時）或守住。誓約本身不因違反而解除（06 6.26「下一場恢復」）。

立誓、解除、冷卻與被動欄位在 :mod:`trpg.world.growth`。純函式、不擲骰。
"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.content.library import ContentLibrary
from trpg.content.world_oaths import OathTemplateDef, resolve_check
from trpg.engine.events import EventBase, OathBroken
from trpg.engine.oaths import OathSetup
from trpg.world.actions import OathBrokenEvent, OathKeptEvent, WorldEvent
from trpg.world.state import CharacterState

__all__ = ["oath_events", "oath_setup", "oath_template"]


def oath_template(library: ContentLibrary, char: CharacterState) -> OathTemplateDef | None:
    """角色目前誓約的模板（沒有誓約、或內容庫已經沒有這個模板時為 ``None``）。"""
    table = library.world_oaths
    if char.oath is None or table is None:
        return None
    return table.template_by_id().get(char.oath.template)


def oath_setup(library: ContentLibrary, char: CharacterState) -> OathSetup | None:
    """角色有誓約時的引擎設定；沒有誓約或模板沒有判定時為 ``None``（不帶加成、不判定）。"""
    template = oath_template(library, char)
    table = library.world_oaths
    if template is None or table is None or char.oath is None:
        return None
    check = resolve_check(template, char.oath.params)
    if check is None:
        return None
    return OathSetup(
        unit=0,
        template=template.id,
        check=check,
        bonus_status=table.bonuses.get(char.oath.difficulty),
        penalty_status=table.penalty_status,
        penalty_rounds=table.penalty_rounds,
    )


def oath_events(
    setup: OathSetup | None, battle_events: Sequence[EventBase]
) -> tuple[list[WorldEvent], bool]:
    """這場的誓約結果：世界事件（違反或守住）與「有沒有違反」。沒有誓約時是空的。"""
    if setup is None:
        return [], False
    broken = [e for e in battle_events if isinstance(e, OathBroken)]
    if broken:
        first = broken[0]
        event = OathBrokenEvent(template=setup.template, check=first.check, at_end=first.at_end)
        return [event], True
    return [OathKeptEvent(template=setup.template)], False
