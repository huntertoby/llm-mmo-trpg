"""NPC 怎麼稱呼玩家（``content/world/address.yaml``，Phase 6R-2，#137；09 9.6.10 #107 稱謂）。

稱謂一律中性：不做性別，NPC 稱呼玩家照區域（雲嶺「這位」、荒原「你這傢伙」、主城「旅人」），
人設卡可用 ``address_zh`` 覆寫（青霧觀修士「施主」、長輩口吻叫名字）。值是模板，只能用 ``{name}``
（玩家角色的名字）。查詢：:func:`address_for`。
"""

from __future__ import annotations

import re
import string
from pathlib import Path
from typing import Final

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel

__all__ = [
    "ADDRESS_FIELDS",
    "ADDRESS_FILE",
    "AddressRules",
    "address_for",
    "address_problems",
    "load_world_address",
]

ADDRESS_FILE: Final = "world/address.yaml"
ADDRESS_FIELDS: Final = frozenset({"name"})
"""稱謂模板能用的佔位符：``{name}``＝玩家角色的名字。"""
_DEFAULT: Final = "{name}"


def address_problems(text: str) -> list[str]:
    """稱謂模板的問題（空白、格式錯、不認得的佔位符）。"""
    if not text.strip():
        return ["稱謂不可空白"]
    try:
        names = [n for _, n, _, _ in string.Formatter().parse(text) if n is not None]
    except ValueError as exc:
        return [f"稱謂格式錯誤：{text!r}（{exc}）"]
    unknown = sorted(set(names) - ADDRESS_FIELDS)
    return [f"稱謂 {text!r} 有不認得的佔位符：{'、'.join(unknown)}"] if unknown else []


class AddressRules(ContentModel):
    """``content/world/address.yaml``。"""

    default_zh: str = Field(default=_DEFAULT, min_length=1)
    """沒有寫到的區域（預設叫名字）。"""
    regions: dict[str, str] = Field(default_factory=dict)
    """區域 ID → 那一區一般 NPC 對玩家的稱呼。"""

    @model_validator(mode="after")
    def _check(self) -> AddressRules:
        problems = address_problems(self.default_zh)
        for region, text in sorted(self.regions.items()):
            if not re.fullmatch(ID_PATTERN, region):
                problems.append(f"區域 ID 格式不正確：{region!r}")
            problems += [f"{region}：{p}" for p in address_problems(text)]
        if problems:
            raise ValueError("；".join(problems))
        return self

    def summary(self) -> str:
        return f"NPC 稱謂（{len(self.regions)} 區）"


def _fill(text: str, name: str) -> str:
    return text.replace("{name}", name)


def address_for(rules: AddressRules | None, region: str, card_address: str, name: str) -> str:
    """NPC 在 ``region`` 怎麼稱呼名叫 ``name`` 的玩家角色：人設卡的 ``address_zh``
    （``card_address``，一般人或沒寫＝空字串）→ 區域 → 預設（叫名字）。沒有 ``address.yaml`` 時
    一律叫名字。"""
    if card_address:
        return _fill(card_address, name)
    if rules is None:
        return _fill(_DEFAULT, name)
    return _fill(rules.regions.get(region, rules.default_zh), name)


def load_world_address(path: Path) -> AddressRules | None:
    """讀 ``address.yaml``；不存在＝``None``（一律叫名字）。"""
    if not path.is_file():
        return None
    return load_content_file(path, AddressRules)
