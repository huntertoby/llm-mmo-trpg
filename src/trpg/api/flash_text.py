"""選變體畫面的字（FL-1b，``docs/art/靈感閃現選擇-移植需求.md`` 6、8.2、9）。

- **大標** ``headline_zh``：「模板 × 關鍵字」表（``flash_templates.yaml`` 的 ``headlines``）→
  模板自己的 ``headline_zh`` → ``None``（畫面退回 ``summary_zh``）。不用 LLM。
- **一句話** ``say_zh``：同上的 ``say_zh``；都沒有時照差異清單組（「用過之後要等 4 回合才能
  再用（原本 2），燃燒多 1 回合。」，玩法 PM 2026-11-13 定的句型）。
- **說明卡**：畫面上的字用術語標記 ``[[術語ID|顯示字]]``，圖示標記 ``{{kw:<關鍵字>}}``。
  :func:`flash_terms` 把用到的術語查成說明卡：``flash_templates.yaml`` 的 ``terms`` 優先，
  其次照內容原句（``status:``／``kw:``／``shape:`` 讀 ``description_zh``）；數字由資料填
  （AP、積水回合、武器骰與目前的屬性加成），不寫死。查不到的術語不給，畫面就不畫底線。
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from trpg.api.flash_changes import ratio_zh
from trpg.api.run_schemas import FlashTermOut, StatChangeOut
from trpg.api.skill_cards import SkillCard
from trpg.content.battle import WeaponDef
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.bonus_text import bonus_text, plain_text
from trpg.shared.types import Attribute, Element, Surface
from trpg.skillgen.flash_ops import cell_count
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.flash_text import clean_name, clean_note

__all__ = [
    "FlashTextContext",
    "NameSource",
    "base_terms",
    "flash_terms",
    "option_headline",
    "option_llm_text",
    "option_say",
    "option_tag_term",
    "term_ids",
]

_TERM_RE = re.compile(r"\[\[([^|\]]+)(?:\|[^\]]*)?\]\]")
_PERMILLE = 1000
_DEFAULT_STEP = 1
"""模板沒寫 ``delta`` 時 ``{n}`` 填的數：這些模板的改法一次都是 ±1（``flash_ops``：觸發範圍
``delta or 1``、維持費 ±1、延長、觸發次數、作用範圍、持續回合各 +1；FL-1f）。"""
_ELEMENTS = frozenset(e.value for e in Element)
_VARIANT_WHERE = {
    "wet": "站在水中",
    "icy": "站在冰上",
    "high": "站在高處",
    "wall": "背靠牆壁",
    "oil": "目標站在油上",
    "puddle": "目標站在水窪裡",
}
"""戰場變奏 ``{terrain}``：變奏條件（``skill_composer.yaml`` 的 ``variant.conditions`` ID）→
完整的動作片語（FL-1f 第二輪，填答第十節第 3 點）。查不到時寫 :data:`_VARIANT_SOMEWHERE`。"""
_VARIANT_SOMEWHERE = "在特定地形"
_INTENSIFY_NEW = "專精{keyword}：這招開始會造成{keyword}"
"""``major_intensify`` 原本不會造成該關鍵字、引擎補上製造效果時的大標（第十節第 5 點）；
原本就會造成時用模板的 ``headline_zh``（更持久）。"""
_TAG_TERMS = {"charge": "power_up", "light": "power_down"}
"""選項卡類別標籤的說明卡（9.2：威力提高／降低只在說明卡）：模板的 ``op`` → 術語。"""


@dataclass(frozen=True, slots=True)
class FlashTextContext:
    """填說明卡數字用的主角資料：手上武器與有效屬性（武器傷害的骰子、目前加成）。"""

    weapon: WeaponDef | None
    attr: Callable[[Attribute], int]


def term_ids(text: str | None) -> list[str]:
    """一段字裡用到的術語 ID（照出現順序）。"""
    return [] if text is None else _TERM_RE.findall(text)


def _template_text(
    library: ContentLibrary, variation: Variation, field: str
) -> tuple[str | None, int | None]:
    """模板自己的 ``headline_zh``／``say_zh`` 與 ``delta``（填 ``{n}``）。"""
    table = library.flash
    if variation.source == "minor":
        minor = table.minor_template(variation.template)
        if minor is None:
            return None, None
        return getattr(minor, field), minor.delta
    if variation.source == "transform":
        found = table.transform_template(variation.template)
        return (None if found is None else getattr(found, field)), None
    extra = table.extra_template(variation.template)
    if extra is not None:
        return getattr(extra, field), None
    major = table.major_template(variation.template)
    return (None if major is None else getattr(major, field)), None


def _pick(
    library: ContentLibrary, variation: Variation, field: str
) -> tuple[str | None, int | None]:
    line = library.flash.headline(variation.template, variation.keyword or variation.element)
    text, delta = _template_text(library, variation, field)
    special = None if line is None else getattr(line, field)
    return (special or text), delta


def _fill(text: str, values: dict[str, str]) -> str:
    """``{名}`` 換成值；沒有的變數原樣留著（內容寫錯時看得出來，不會拋錯）。"""
    return re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), m.group(0)), text)


def _values(
    library: ContentLibrary,
    variation: Variation,
    after: SkillDef,
    changes: Sequence[StatChangeOut],
    delta: int | None,
) -> dict[str, str]:
    shape = library.ruleset.shapes.by_id().get(after.shape.type)
    cells = cell_count(after.shape, library)
    extra = next(
        (c.after_zh for c in changes if c.direction == "new" and c.after_zh is not None), None
    )
    values = {
        "n": str(abs(delta if delta is not None else _DEFAULT_STEP)),
        "shape": "" if shape is None else f"[[shape:{shape.id}|{shape.name_zh}範圍]]",
        "cells": "" if cells is None else str(cells),
        "range": "" if not isinstance(after.shape.range, int) else str(after.shape.range),
        "extra": (extra or "").split("（")[0],  # 條件「（……才有）」說明句另寫
        "keyword": _keyword_zh(library, variation),
        "terrain": _variant_where(library, after),
    }
    return values


def _variant_where(library: ContentLibrary, after: SkillDef) -> str:
    """戰場變奏加上去的那個（``variants`` 最後一個，``evolution._variant`` 往後接）的條件片語。"""
    if not after.variants:
        return _VARIANT_SOMEWHERE
    variant_id = after.variants[-1].id
    for condition in library.composer.variant.conditions:
        if variant_id.startswith(f"{condition.id}_") and condition.id in _VARIANT_WHERE:
            return _VARIANT_WHERE[condition.id]
    return _VARIANT_SOMEWHERE


def _keyword_zh(library: ContentLibrary, variation: Variation) -> str:
    """``{keyword}``：關鍵字的中文名；第二元素的模板（``element_second``…）是元素的中文名。"""
    keyword = library.keywords.by_id().get(variation.keyword or "")
    if keyword is not None:
        return keyword.name_zh
    if variation.element in _ELEMENTS:
        return Element(variation.element).display_name
    return ""


def option_headline(
    library: ContentLibrary,
    variation: Variation,
    after: SkillDef,
    changes: Sequence[StatChangeOut],
) -> str | None:
    """白話大標；還沒填的模板為 ``None``（畫面退回 ``summary_zh``）。"""
    text, delta = _pick(library, variation, "headline_zh")
    if text is None:
        return None
    if variation.template == "major_intensify" and any(
        c.direction == "new" and c.before is None for c in changes
    ):
        text = _INTENSIFY_NEW  # 原本不會造成，引擎補上製造效果（不是更持久）
    return _fill(text, _values(library, variation, after, changes, delta))


def option_say(
    library: ContentLibrary,
    variation: Variation,
    after: SkillDef,
    changes: Sequence[StatChangeOut],
) -> str:
    """選中時下固定區的一句話：模板（或模板 × 關鍵字）有寫照寫的，沒有照差異清單組。"""
    text, delta = _pick(library, variation, "say_zh")
    if text is not None:
        return _fill(text, _values(library, variation, after, changes, delta))
    return say_from_changes(changes)


def option_tag_term(library: ContentLibrary, variation: Variation) -> str | None:
    """選項卡類別標籤的說明卡（蓄力「威力提高」、輕巧「威力降低」）。"""
    if variation.source != "minor":
        return None
    minor = library.flash.minor_template(variation.template)
    return None if minor is None else _TAG_TERMS.get(minor.op)


NameSource = Literal["llm", "template"]


def option_llm_text(variation: Variation, after: SkillDef) -> tuple[str | None, NameSource]:
    """LLM 的一句話描述與名稱來源（LF-3）。變化上的文字出題時已經 ``clean_text`` 過，這裡照樣再
    檢查一次（守則 3）：描述不合格當作沒有；名稱只有大變化、轉型帶了合格的名稱、而且技能真的用了它
    才算 ``llm``。"""
    note = clean_note(variation.note_zh)
    name = None if variation.source == "minor" else clean_name(variation.name_zh)
    source: NameSource = "llm" if name is not None and after.name_zh == name else "template"
    return note, source


# ---------------------------------------------------------------------------
# 照差異清單組一句話（9.3 第 2 個的句型）
# ---------------------------------------------------------------------------


def _int(value: str | None) -> int | None:
    try:
        return None if value is None else int(value)
    except ValueError:
        return None


def _clause(row: StatChangeOut) -> str:
    name, before, after = row.name_zh or row.label_zh, row.before_zh, row.after_zh
    if row.field == "cost.cooldown" and row.before is not None and row.after is not None:
        return f"用過之後要等 {row.after} 回合才能再用（原本 {row.before}）"
    if row.field == "cost.ap" and row.before is not None and row.after is not None:
        lead = "只要" if (_int(row.after) or 0) < (_int(row.before) or 0) else "要花"
        return f"{lead} {row.after} AP（原本 {row.before}）"
    if after is None:
        return f"不用花{name}" if row.field.startswith("cost.") else f"拿掉{name}"
    if before is None:
        return f"多了{name}：{after}"
    a, b = _int(row.before), _int(row.after)
    unit = "回合" if (after or "").endswith(" 回合") else ""
    if unit and a is not None and b is not None:
        return f"{name}多 {b - a} 回合" if b > a else f"{name}少 {a - b} 回合"
    return f"{name}從 {before} 變成 {after}"


def say_from_changes(changes: Sequence[StatChangeOut]) -> str:
    """差異清單的每一列一個短句，用「，」接起來（玩法 PM 2026-11-13：蓄力那句照這個句型）。"""
    clauses = [_clause(row) for row in changes]
    return "" if not clauses else "，".join(clauses) + "。"


# ---------------------------------------------------------------------------
# 說明卡
# ---------------------------------------------------------------------------


def base_terms(skill: SkillDef, card: SkillCard) -> list[str]:
    """原技能列與「完整說明」用到的說明卡（9.2）。"""
    ids = ["ap", "cooldown", "range", "assembly", "scaling", "makes", "uses"]
    ids += [f"skeleton:{skill.skeleton}", f"category:{skill.category}", f"shape:{skill.shape.type}"]
    if skill.cost.stamina:
        ids.append("stamina")
    if card.element_id is not None:
        ids.append(f"element:{card.element_id}")
    ids += [f"status:{e.status}" for e in skill.effects if e.status is not None]
    ids += [f"kw:{k.id}" for k in (*card.keywords.makes, *card.keywords.uses)]
    return ids


def _numbers(library: ContentLibrary) -> dict[str, str]:
    core = library.ruleset.core
    water = library.ruleset.surface_def(Surface.WATER).duration
    return {
        "ap_per_turn": str(core.ap_per_turn),
        "ap_carry_max": str(core.ap_carry_max),
        "water_rounds": "" if water is None else str(water),
        "wet_heal_percent": f"{(core.wet_heal_permille - _PERMILLE) / 10:g}",
    }


def _weapon_numbers(
    library: ContentLibrary, skill: SkillDef, permille: int, ctx: FlashTextContext
) -> dict[str, str]:
    weapon = ctx.weapon
    core = library.ruleset.core
    if weapon is None:
        dice, attrs = "", "武器屬性"
    else:
        dice = str(weapon.dice) + (f"＋{weapon.flat}" if weapon.flat else "")
        attrs = weapon.skill_scaling_names_zh(skill.secondary_scaling_attr)
    value = skill.scaling_value(ctx.attr, weapon)
    return {
        "dice": dice,
        "attrs": attrs,
        "times": f"{permille / _PERMILLE:g}",
        "bonus": plain_text(bonus_text(value, core.basic_attack_attr_multiplier_permille)),
        "ratio": ratio_zh(permille),
    }


def _content_term(library: ContentLibrary, term_id: str) -> FlashTermOut | None:
    kind, _, arg = term_id.partition(":")
    if kind == "status":
        status = library.ruleset.statuses.by_id().get(arg)
        if status is not None:
            return FlashTermOut(title_zh=status.name_zh, text_zh=status.description_zh)
    if kind == "kw":
        keyword = library.keywords.by_id().get(arg)
        if keyword is not None:
            return FlashTermOut(
                title_zh=f"{keyword.name_zh}（關鍵字）", text_zh=keyword.description_zh
            )
    if kind == "shape":
        shape = library.ruleset.shapes.by_id().get(arg)
        if shape is not None:
            return FlashTermOut(title_zh=f"{shape.name_zh}範圍", text_zh=shape.description_zh)
    return None


def flash_terms(
    library: ContentLibrary, skill: SkillDef, ids: Iterable[str], ctx: FlashTextContext
) -> dict[str, FlashTermOut]:
    """用到的術語 → 說明卡（照 ID 排序；查不到的不給）。``skill``：武器傷害看的技能。"""
    numbers = _numbers(library)
    out: dict[str, FlashTermOut] = {}
    for term_id in sorted(set(ids)):
        base, _, arg = term_id.partition(":")
        if base == "weapon_damage" and arg.isdigit():
            template = library.flash.term("weapon_damage")
            if template is not None:
                values = numbers | _weapon_numbers(library, skill, int(arg), ctx)
                out[term_id] = FlashTermOut(
                    title_zh=_fill(template.title_zh, values),
                    text_zh=_fill(template.text_zh, values),
                )
            continue
        found = library.flash.term(term_id)
        if found is not None:
            out[term_id] = FlashTermOut(
                title_zh=_fill(found.title_zh, numbers), text_zh=_fill(found.text_zh, numbers)
            )
            continue
        content = _content_term(library, term_id)
        if content is not None:
            out[term_id] = content
    return out
