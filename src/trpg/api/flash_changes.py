"""閃現選項的「前 → 後」差異清單（FL-1a；``docs/phases/閃現蓄力調查.md`` 5.1）。

比對閃現前的技能與選項套用後的技能 **卡片上的數字**（:func:`~trpg.api.skill_cards.card_stats`：AP、
冷卻、射程、半徑、大小、各項代價、每個效果的骰子／倍率／回合（格數、層數）），另加狀態強度
（``magnitude_permille``）與接續段的效果。每一列是一個欄位的「前值、後值、方向」：

- ``better``／``worse``：強度欄位變強／變弱（數字大＝強；骰子比平均）；
- ``cost``：代價欄位（AP、冷卻、法力、耐力……）變貴（新加、整項拿掉也算這一類，前端看後值）；
  變便宜的代價照 ``better``（FL-1g）；
- ``new``：新加的效果或欄位（前值為 ``None``）。拿掉的效果記 ``worse``（後值為 ``None``）。

只列有變的欄位；順序固定（種類 → 技能層級 → 代價 → 效果 → 接續段）。前端畫「前 → 後」用，不進規則。

**畫面用的欄位名與單位對照只在這裡**（FL-1b，``docs/art/靈感閃現選擇-移植需求.md`` 8.1、
9.1 #3～#5；開發 PM 第 12 節決定 1）：每列另帶 ``name_zh``（射程、冷卻、AP、燃燒、範圍、地面、
額外傷害、接續、第二元素、效果、種類）、帶單位的 ``before_zh``／``after_zh``（「4 格」「2 回合」
「3 成武器傷害」）、欄位小圖 ``icon`` 與說明卡 ``term``。前端只畫樣式。顯示字可帶術語標記
``[[術語|字]]``、圖示標記 ``{{kw:<id>}}``（見 :mod:`trpg.api.flash_text`）。
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from fractions import Fraction
from typing import Literal

from trpg.api.run_schemas import ChangeIconOut, FlashBaseStatOut, StatChangeOut
from trpg.api.skill_cards import CostStat, EffectStat, card_stats, effect_stat
from trpg.content.battle import StatusDef
from trpg.content.library import ContentLibrary
from trpg.content.skills import EffectSpec, SkillDef, condition_text
from trpg.shared.types import Element, Surface

__all__ = [
    "base_stats",
    "flash_changes",
    "magnitude_zh",
    "ratio_zh",
    "status_magnitude_suffix",
]

Direction = Literal["better", "worse", "cost", "new"]

_CATEGORY_ZH = {
    "damage": "傷害",
    "heal": "治療",
    "shield": "護盾",
    "move": "位移",
    "status": "狀態",
    "surface": "表面",
    "summon": "召喚",
    "stack": "層數",
    "other": "效果",
}
_COST_ZH = {
    "ap": "AP",
    "mana": "法力",
    "stamina": "耐力",
    "hp_percent": "HP 代價",
    "self_status": "施放後狀態",
    "overdraft": "透支",
    "upkeep": "維持費",
    "cooldown": "冷卻",
    "uses_per_battle": "每場次數",
    "source": "源力",
    "backlash": "失手反噬",
}
_AMOUNT_ZH = {"回合": "回合", "格": "距離", "輪": "持續", "層": "層數"}
_BUFF_ROUNDS_ZH = {
    "grant_skill": "獲得技能回合",
    "zone": "區域回合",
    "shield": "護盾回合",
    "cheat_death": "不死回合",
    "redirect_damage": "轉移傷害回合",
}
"""卡片數字沒有回合、但蓄力與輕巧會調回合的增益原語（06 6.34「費用方向」第 6 點；FL-1c 暫時給技能、
區域，FL-1d 護盾、不死、轉移傷害）的列名。"""
_SHIELD_DEFAULT_DURATION = 2
"""護盾省略 ``duration`` 時的回合（``skill_primitives.yaml`` 的 shield：省略＝2）。"""
_NEUTRAL_MAGNITUDE = 1000
_MAGNITUDE_TYPES = frozenset({"apply_status", "create_surface", "enter_form"})


def _row(
    field: str,
    label_zh: str,
    before: object,
    after: object,
    direction: Direction,
    *,
    effect_index: int | None = None,
) -> StatChangeOut:
    return StatChangeOut(
        field=field,
        label_zh=label_zh,
        effect_index=effect_index,
        before=None if before is None else str(before),
        after=None if after is None else str(after),
        direction=direction,
    )


def _compare(old: Fraction | int, new: Fraction | int) -> Direction:
    return "better" if new > old else "worse"


def _shape_rows(
    before: SkillDef, after: SkillDef, library: ContentLibrary
) -> Iterator[StatChangeOut]:
    old, new = card_stats(library, before), card_stats(library, after)
    for field, label in (("range", "射程"), ("radius", "半徑"), ("size", "大小")):
        a, b = getattr(old, field), getattr(new, field)
        if a == b:
            continue
        if a is None:
            yield _row(field, label, a, b, "new")
        elif b is None:
            yield _row(field, label, a, b, "worse")
        else:
            yield _row(field, label, a, b, _compare(a, b))


def _cost_label(cost: CostStat | None) -> str | None:
    if cost is None:
        return None
    return cost.label or (None if cost.value is None else str(cost.value)) or "有"


def _cost_rows(
    before: SkillDef, after: SkillDef, library: ContentLibrary
) -> Iterator[StatChangeOut]:
    old = {c.kind: c for c in card_stats(library, before).costs}
    new = {c.kind: c for c in card_stats(library, after).costs}
    order = list(dict.fromkeys([*old, *new]))
    for kind in order:
        a, b = old.get(kind), new.get(kind)
        if a is not None and b is not None and (a.value, a.label) == (b.value, b.label):
            continue
        name = _COST_ZH.get(kind, kind)
        yield _row(f"cost.{kind}", name, _cost_label(a), _cost_label(b), _cost_way(a, b))


_MORE_IS_BETTER_COSTS = frozenset({"uses_per_battle"})
"""代價欄位裡數字越大越好的（每場次數）；其他（AP、冷卻、法力、耐力……）數字越大越貴。"""


def _cost_way(a: CostStat | None, b: CostStat | None) -> Direction:
    """代價欄位的方向（FL-1g，FL-1b 驗收必修 1）：只有變貴才是 ``cost``；變便宜照 ``better``。

    整項拿掉（``b`` 是 ``None``）照舊給 ``cost``，前端寫「不用花」並畫成變好；新加的代價、
    沒有數值可比的（失手反噬、只換字）也照舊是 ``cost``。
    """
    if a is None or b is None or a.value is None or b.value is None or a.value == b.value:
        return "cost"
    cheaper = b.value > a.value if a.kind in _MORE_IS_BETTER_COSTS else b.value < a.value
    return "better" if cheaper else "cost"


def _times(permille: int | None) -> str | None:
    return None if permille is None else f"×{permille / 1000:g}"


def _dice_mean(spec: EffectSpec) -> Fraction:
    if spec.dice is None:
        return Fraction(0)
    return Fraction(spec.dice.count * (spec.dice.sides + 1), 2) + (spec.flat_bonus or 0)


def _same_effect(a: EffectSpec, b: EffectSpec) -> bool:
    return (a.type, a.status, a.surface, a.stack, a.form, a.unit) == (
        b.type,
        b.status,
        b.surface,
        b.stack,
        b.form,
        b.unit,
    )


def _name(stat: EffectStat) -> str:
    return stat.name_zh or _CATEGORY_ZH[stat.category]


def _magnitude(spec: EffectSpec) -> int | None:
    if spec.type not in _MAGNITUDE_TYPES:
        return None
    return spec.magnitude_permille or _NEUTRAL_MAGNITUDE


def _buff_rounds(spec: EffectSpec) -> int | None:
    if spec.duration is not None:
        return spec.duration
    return _SHIELD_DEFAULT_DURATION if spec.type == "shield" else None


def _nested_rows(
    library: ContentLibrary, prefix: str, index: int, old_spec: EffectSpec, new_spec: EffectSpec
) -> Iterator[StatChangeOut]:
    """只對友方的區域裡巢狀的狀態（FL-1d：跟直接施加的狀態一樣算回合與強度）。"""
    if old_spec.type != "zone" or old_spec.affects != "allies" or new_spec.affects != "allies":
        return
    statuses = library.ruleset.statuses.by_id()
    pairs = zip(old_spec.effects or (), new_spec.effects or (), strict=False)
    for sub, (a, b) in enumerate(pairs):
        if a.type != "apply_status" or b.type != "apply_status" or a.status != b.status:
            continue
        status = statuses.get(str(a.status))
        name = str(a.status) if status is None else status.name_zh
        default = None if status is None else status.duration
        where = f"{prefix}[{index}].effects[{sub}]"
        a_rounds, b_rounds = a.duration or default, b.duration or default
        if a_rounds is not None and b_rounds is not None and a_rounds != b_rounds:
            yield _row(
                f"{where}.amount",
                f"{name}回合",
                a_rounds,
                b_rounds,
                _compare(a_rounds, b_rounds),
                effect_index=index,
            )
        a_mag, b_mag = _magnitude(a), _magnitude(b)
        if a_mag is not None and b_mag is not None and a_mag != b_mag:
            yield _row(
                f"{where}.magnitude_permille",
                f"{name}強度",
                f"{a_mag}‰",
                f"{b_mag}‰",
                _compare(a_mag, b_mag),
                effect_index=index,
            )


def _pair_rows(
    prefix: str,
    index: int,
    pair: tuple[tuple[EffectSpec, EffectStat], tuple[EffectSpec, EffectStat]],
) -> Iterator[StatChangeOut]:
    (old_spec, old), (new_spec, new) = pair
    where = f"{prefix}[{index}]"
    name = _name(new)
    if old.dice != new.dice and old.dice is not None and new.dice is not None:
        direction = _compare(_dice_mean(old_spec), _dice_mean(new_spec))
        yield _row(
            f"{where}.dice", f"{name}骰子", old.dice, new.dice, direction, effect_index=index
        )
    if old.multiplier_permille != new.multiplier_permille:
        a, b = old.multiplier_permille, new.multiplier_permille
        direction = "new" if a is None else ("worse" if b is None else _compare(a, b))
        yield _row(
            f"{where}.multiplier_permille",
            f"{name}倍率",
            _times(a),
            _times(b),
            direction,
            effect_index=index,
        )
    if old.amount != new.amount:
        a, b = old.amount, new.amount
        what = _AMOUNT_ZH.get(new.unit or old.unit or "", "數值")
        direction = "new" if a is None else ("worse" if b is None else _compare(a, b))
        yield _row(f"{where}.amount", f"{name}{what}", a, b, direction, effect_index=index)
    buff = _BUFF_ROUNDS_ZH.get(new_spec.type)
    a_rounds, b_rounds = _buff_rounds(old_spec), _buff_rounds(new_spec)
    if (
        buff is not None
        and old.amount is None
        and new.amount is None
        and a_rounds is not None
        and b_rounds is not None
        and a_rounds != b_rounds
    ):
        # 第 6 點：增益回合（給技能、區域、護盾、不死、轉移傷害）卡片數字不列，但蓄力、輕巧會調它
        direction = _compare(a_rounds, b_rounds)
        yield _row(f"{where}.amount", buff, a_rounds, b_rounds, direction, effect_index=index)
    a_mag, b_mag = _magnitude(old_spec), _magnitude(new_spec)
    if a_mag is not None and b_mag is not None and a_mag != b_mag:
        yield _row(
            f"{where}.magnitude_permille",
            f"{name}強度",
            f"{a_mag}‰",
            f"{b_mag}‰",
            _compare(a_mag, b_mag),
            effect_index=index,
        )


def _effect_rows(
    library: ContentLibrary,
    prefix: str,
    old: Sequence[tuple[EffectSpec, EffectStat]],
    new: Sequence[tuple[EffectSpec, EffectStat]],
) -> Iterator[StatChangeOut]:
    for index in range(max(len(old), len(new))):
        a = old[index] if index < len(old) else None
        b = new[index] if index < len(new) else None
        if a is not None and b is not None and _same_effect(a[0], b[0]):
            yield from _pair_rows(prefix, index, (a, b))
            yield from _nested_rows(library, prefix, index, a[0], b[0])
            continue
        if a is not None:
            label = a[1].label or _name(a[1])
            yield _row(f"{prefix}[{index}]", _name(a[1]), label, None, "worse", effect_index=index)
        if b is not None:
            label = b[1].label or _name(b[1])
            yield _row(f"{prefix}[{index}]", _name(b[1]), None, label, "new", effect_index=index)


def _effects(
    library: ContentLibrary, skill: SkillDef, specs: Sequence[EffectSpec]
) -> list[tuple[EffectSpec, EffectStat]]:
    return [(spec, effect_stat(library, skill, i, spec)) for i, spec in enumerate(specs)]


_KIND_ZH = {
    "active": "主動",
    "passive": "被動",
    "reaction": "反應",
    "stance": "姿態",
    "modifier": "修正型被動",
}


def _kind_of(skill: SkillDef) -> str:
    return "modifier" if skill.is_modifier else skill.kind


def _kind_rows(before: SkillDef, after: SkillDef) -> Iterator[StatChangeOut]:
    """轉型換了種類（FL-1b 9.1 #4「種類」；前面有值的換掉照 ``better``，不掛「新」）。"""
    a, b = _kind_of(before), _kind_of(after)
    if a != b:
        yield _row("kind", "種類", _KIND_ZH.get(a, a), _KIND_ZH.get(b, b), "better")


def flash_changes(
    library: ContentLibrary,
    before: SkillDef,
    after: SkillDef,
    *,
    keyword: str | None = None,
) -> tuple[StatChangeOut, ...]:
    """``before``（閃現前）到 ``after``（選項套用後）卡片數字的差異清單（見模組說明）。

    ``keyword``：選項帶的關鍵字（``Variation.keyword``）；新加的表面效果「後」寫
    「會造成 {關鍵字}」用。"""
    rows = [
        *_kind_rows(before, after),
        *_shape_rows(before, after, library),
        *_cost_rows(before, after, library),
        *_effect_rows(
            library,
            "effects",
            _effects(library, before, before.effects),
            _effects(library, after, after.effects),
        ),
        *_effect_rows(
            library,
            "followup",
            _effects(library, before, before.followup.effects if before.followup else ()),
            _effects(library, after, after.followup.effects if after.followup else ()),
        ),
    ]
    view = _View(library, before, after, keyword)
    merged = _merge_moved(library, before, after, _drop_shifted(rows))
    return _name_segments([view.dress(row) for row in merged])


def _drop_shifted(rows: list[StatChangeOut]) -> list[StatChangeOut]:
    """同一個效果只是換了位置（例：多打一下插進一段傷害，後面的造水往後挪一格）：「拿掉」與「新加」
    兩列的欄位名與值都一樣時兩列都不列（FL-1b：畫面不出現「積水 → 沒有」又「沒有 → 積水」）。"""
    removed = [r for r in rows if r.after is None and r.before is not None and "." not in r.field]
    added = [r for r in rows if r.before is None and r.after is not None and "." not in r.field]
    drop: set[int] = set()
    for old in removed:
        prefix = old.field.split("[", 1)[0]
        match = next(
            (
                new
                for new in added
                if id(new) not in drop
                and new.field.split("[", 1)[0] == prefix
                and (new.label_zh, new.after) == (old.label_zh, old.before)
            ),
            None,
        )
        if match is not None:
            drop |= {id(old), id(match)}
    return [r for r in rows if id(r) not in drop]


_SEGMENT_ZH = "{name}（第 {n} 段）"
_FOLLOWUP_SEGMENT_ZH = "{name}（接續）"
"""同一張卡兩列以上同名（例：雙槍連射兩段都叫「傷害」）時加的段名（FL-1g，FL-1b 驗收可修 3）；
「傷害（第 1 段）」「傷害（接續）」玩法 PM 11-13 定稿（TXT-2）。"""


def _name_segments(rows: list[StatChangeOut]) -> tuple[StatChangeOut, ...]:
    """不同效果的列同名時加段名：本體有兩段以上同名時照出現順序「（第 N 段）」，
    接續段「（接續）」。"""
    owners: dict[str, list[tuple[str, int]]] = {}
    for row in rows:
        match = _FIELD_RE.match(row.field)
        if match is None or not row.name_zh:
            continue
        key = (match.group(1), int(match.group(2)))
        seen = owners.setdefault(row.name_zh, [])
        if key not in seen:
            seen.append(key)
    out: list[StatChangeOut] = []
    for row in rows:
        match = _FIELD_RE.match(row.field)
        keys = owners.get(row.name_zh, [])
        if match is None or len(keys) < 2:  # noqa: PLR2004
            out.append(row)
            continue
        prefix, index = match.group(1), int(match.group(2))
        mine = sorted(i for p, i in keys if p == "effects")
        if prefix == "followup":
            label = _FOLLOWUP_SEGMENT_ZH.format(name=row.name_zh)
        elif len(mine) < 2:  # noqa: PLR2004
            label = row.name_zh
        else:
            label = _SEGMENT_ZH.format(name=row.name_zh, n=mine.index(index) + 1)
        out.append(row.model_copy(update={"name_zh": label}))
    return tuple(out)


_MOVABLE = frozenset({"apply_status", "create_surface"})


def _specs(skill: SkillDef, prefix: str) -> Sequence[EffectSpec]:
    if prefix == "effects":
        return skill.effects
    return skill.followup.effects if skill.followup else ()


def _merge_moved(
    library: ContentLibrary, before: SkillDef, after: SkillDef, rows: list[StatChangeOut]
) -> list[StatChangeOut]:
    """同一個狀態或表面挪了位置、數字也變了（FL-1g，FL-1b 驗收可修 4：「燃燒 2 回合 → 沒有」＋
    「沒有 → 燃燒 3 回合」）：拿掉與新加兩列併成新位置上的一般差異列（「燃燒 2 回合 → 3 回合」）。
    只換位置、數字沒變的已由 :func:`_drop_shifted` 拿掉。"""
    removed = [r for r in rows if r.after is None and r.before is not None and "." not in r.field]
    added = [r for r in rows if r.before is None and r.after is not None and "." not in r.field]
    replace: dict[int, list[StatChangeOut]] = {}
    used: set[int] = set()
    for old in removed:
        match = _FIELD_RE.match(old.field)
        if match is None:
            continue
        prefix, index = match.group(1), int(match.group(2))
        old_spec = _specs(before, prefix)[index]
        if old_spec.type not in _MOVABLE:
            continue
        for new in added:
            found = _FIELD_RE.match(new.field)
            if id(new) in used or found is None or found.group(1) != prefix:
                continue
            at = int(found.group(2))
            new_spec = _specs(after, prefix)[at]
            if not _same_effect(old_spec, new_spec):
                continue
            pair = (
                (old_spec, effect_stat(library, before, index, old_spec)),
                (new_spec, effect_stat(library, after, at, new_spec)),
            )
            replace[id(new)] = list(_pair_rows(prefix, at, pair))
            replace[id(old)] = []
            used.add(id(new))
            break
    out: list[StatChangeOut] = []
    for row in rows:
        out.extend(replace.get(id(row), [row]))
    return out


# ---------------------------------------------------------------------------
# 畫面用的欄位名、單位、小圖與說明卡（FL-1b）
# ---------------------------------------------------------------------------

_FIELD_RE = re.compile(r"^(effects|followup)\[(\d+)\](?:\.effects\[(\d+)\])?(?:\.([a-z_]+))?$")
_COST_ICON = {
    "ap": "ap",
    "mana": "mana",
    "stamina": "stamina",
    "hp_percent": "hp",
    "cooldown": "cooldown",
    "uses_per_battle": "uses",
    "source": "source",
}
_COST_TERM = {"ap": "ap", "stamina": "stamina", "cooldown": "cooldown"}
_COST_UNIT = {"cooldown": "回合", "uses_per_battle": "次"}
_SHAPE_ROWS = {"range": ("射程", "格"), "radius": ("範圍", "格"), "size": ("範圍", "格")}
_SURFACE_ZH = {"water": "積水"}
"""表面在選變體畫面的叫法（9.2「積水（水表面）」）；沒列的用表面的 ``name_zh``。"""
_AMOUNT_UNITS = (("回合", "回合"), ("距離", "格"), ("層數", "層"), ("持續", "輪"))
"""``label_zh`` 的字尾 → 單位（「燃燒回合」→ 名「燃燒」、值「5 回合」）。"""
_PERMILLE = 1000
_TENTH = 100
_CARD_ICON = {
    "damage": "damage",
    "delayed_damage": "damage",
    "heal": "heal",
    "shield": "shield",
    "apply_status": "status",
    "create_surface": "surface",
    "summon": "summon",
    "push": "move",
    "pull": "move",
    "teleport": "move",
}


def ratio_zh(permille: int) -> str:
    """倍率的白話（9.1 #3）：整成寫「3 成」、不整寫「35%」、1 以上寫「1.35 倍」。"""
    if permille >= _PERMILLE:
        return f"{permille / _PERMILLE:g} 倍"
    if permille % _TENTH == 0:
        return f"{permille // _TENTH} 成"
    return f"{permille / 10:g}%"


def _unit(value: str | None, unit: str | None) -> str | None:
    if value is None or not unit:
        return value
    return f"{value} {unit}"


def magnitude_zh(value: str | None, *, before: bool) -> str | None:
    """強度 ‰ 的白話（FL-1f，玩法 PM 填答第六節）：寫「倍」不寫百分比；前值是 1000‰ 寫「原本」，
    其他寫「N 倍」（小數最多兩位，四捨五入；小於 1 也寫「0.8 倍」）。「1250‰」→「1.25 倍」。"""
    if value is None:
        return None
    permille = int(value.removesuffix("‰"))
    if before and permille == _PERMILLE:
        return "原本"
    whole, hundredths = divmod((permille + 5) // 10, 100)
    text = str(whole) if hundredths == 0 else f"{whole}.{hundredths:02d}".rstrip("0")
    return f"{text} 倍"


_FAVORABLE_PERMILLES = (
    ("damage_dealt_permille", "加成", "幅度"),
    ("damage_taken_permille", "幅度", "減傷"),
    ("physical_taken_permille", "幅度", "減傷"),
    ("element_dealt_permille", "加成", "強度"),
    ("element_dealt_wet_permille", "加成", "強度"),
    ("move_permille", "加成", "強度"),
    ("healing_received_permille", "加成", "強度"),
)
"""狀態倍率欄位 → （大於 1000 時、小於 1000 時）這個欄位改的是什麼（第六節的欄位名字尾）。
第一個字尾給 ``> 1000``、第二個給 ``< 1000``；「強度」＝看不出是哪一種。"""
_DRAWBACKS = {
    ("damage_dealt_permille", "幅度"),
    ("damage_taken_permille", "幅度"),
    ("physical_taken_permille", "幅度"),
    ("move_permille", "強度"),
    ("healing_received_permille", "強度"),
}
"""對持有者不利的一邊；姿態的幅度只放大有利的那一邊（``engine/state.py`` 的
``magnitude_permille``），所以姿態不看這些。"""


def status_magnitude_suffix(status: StatusDef) -> str:
    """狀態強度那一列的欄位名字尾（FL-1f，第六節表）：照狀態實際會被強度放大的欄位分類，
    每回合傷害「傷害」、每回合回復「回復量」、降低輸出或讓對方多受傷「幅度」、少受傷「減傷」、
    自己的加值「加成」；同時改好幾種、或看不出來的寫「強度」。"""
    if status.on_turn_start_damage is not None:
        return "傷害"
    if status.on_turn_start_heal is not None:
        return "回復量"
    kinds: set[str] = set()
    for field, up, down in _FAVORABLE_PERMILLES:
        value: int = getattr(status, field)
        if value == _PERMILLE:
            continue
        kind = up if value > _PERMILLE else down
        if status.stance and (field, kind) in _DRAWBACKS:
            continue
        kinds.add(kind)
    if any(v > 0 for v in status.attr_bonus.values()) or status.attack_bonus > 0:
        kinds.add("加成")
    if any(v < 0 for v in status.attr_bonus.values()) or status.attack_bonus < 0:
        kinds.add("強度")
    return kinds.pop() if len(kinds) == 1 else "強度"


def _card_icon(spec: EffectSpec) -> str:
    return _CARD_ICON.get(spec.type, "status")


def _icon(spec: EffectSpec) -> ChangeIconOut:
    if spec.type == "apply_status" and spec.status is not None:
        return ChangeIconOut(kind="status", id=str(spec.status))
    if spec.type == "create_surface" and spec.surface is not None:
        return ChangeIconOut(kind="part", cat="surface", id=spec.surface.value)
    return ChangeIconOut(kind="part", cat="card", id=_card_icon(spec))


def _card(icon: str) -> ChangeIconOut:
    return ChangeIconOut(kind="part", cat="card", id=icon)


_WEAPON_DAMAGE_ZH = "武器傷害"
_ELEMENT_WEAPON_DAMAGE_ZH = "{element}武器傷害"
"""帶元素的武器傷害（FL-1g，FL-1b 驗收必修 2）：元素名插在「武器傷害」前（「3 成雷電武器傷害」），
每種元素同一個句型；物理不寫元素（「3 成武器傷害」）。玩法 PM 11-13 定稿（TXT-2）。"""


def _ratio(times: str | None, weapon: bool, element: Element | None = None) -> str | None:
    """「×0.3」→「3 成武器傷害」（武器技帶說明卡 ``weapon_damage:<‰>``）；
    帶元素時「3 成雷電武器傷害」。"""
    if times is None:
        return None
    permille = round(float(times.removeprefix("×")) * _PERMILLE)
    text = ratio_zh(permille)
    if not weapon:
        return text
    label = _WEAPON_DAMAGE_ZH
    if element is not None and element is not Element.PHYSICAL:
        label = _ELEMENT_WEAPON_DAMAGE_ZH.format(element=element.display_name)
    return f"{text}[[weapon_damage:{permille}|{label}]]"


def _plain(row: StatChangeOut, name: str, unit: str | None, term: str | None) -> dict[str, object]:
    return {
        "name_zh": name,
        "term": term,
        "before_zh": _unit(row.before, unit),
        "after_zh": _unit(row.after, unit),
    }


def _whole_name(prefix: str, skill: SkillDef, spec: EffectSpec) -> str:
    """整個效果新加或拿掉的欄位名（9.1 #4）。"""
    if prefix == "followup":
        return "接續"
    if spec.type == "create_surface":
        return "地面"
    if spec.type != "damage":
        return "效果"
    if spec.condition is None:
        first = next((e for e in skill.effects if e.type == "damage"), None)
        if first is not None and first is not spec and spec.element != first.element:
            return "第二元素"
    return "額外傷害"


class _View:
    """把一列差異換成畫面字（欄位名、帶單位的前後值、小圖、說明卡）。"""

    def __init__(
        self, library: ContentLibrary, before: SkillDef, after: SkillDef, keyword: str | None
    ) -> None:
        self.library = library
        self.before = before
        self.after = after
        self.keyword = keyword
        self.statuses = library.ruleset.statuses.by_id()

    def dress(self, row: StatChangeOut) -> StatChangeOut:
        field = row.field
        if field == "kind":
            kind = _kind_of(self.after)
            update = _plain(row, row.label_zh, None, None)
            update["icon"] = ChangeIconOut(kind="part", cat="skeleton", id=kind)
            if kind == "passive":
                update["after_zh"] = f"[[kind:passive|{row.after}]]"
            return row.model_copy(update=update)
        if field in _SHAPE_ROWS:
            name, unit = _SHAPE_ROWS[field]
            update = _plain(row, name, unit, "range" if field == "range" else None)
            update["icon"] = _card("range")
            return row.model_copy(update=update)
        if field.startswith("cost."):
            kind = field.removeprefix("cost.")
            update = _plain(row, row.label_zh, _COST_UNIT.get(kind), _COST_TERM.get(kind))
            icon = _COST_ICON.get(kind)
            update["icon"] = None if icon is None else _card(icon)
            return row.model_copy(update=update)
        match = _FIELD_RE.match(field)
        if match is None:
            return row.model_copy(update=_plain(row, row.label_zh, None, None))
        prefix, index, sub, attr = match.groups()
        update = self._effect(row, prefix, int(index), None if sub is None else int(sub), attr)
        return row.model_copy(update=update)

    def _spec(self, skill: SkillDef, prefix: str, index: int, sub: int | None) -> EffectSpec | None:
        if prefix == "effects":
            specs: Sequence[EffectSpec] = skill.effects
        else:
            specs = skill.followup.effects if skill.followup else ()
        if index >= len(specs):
            return None
        if sub is None:
            return specs[index]
        nested = specs[index].effects or ()
        return nested[sub] if sub < len(nested) else None

    def _effect(
        self, row: StatChangeOut, prefix: str, index: int, sub: int | None, attr: str | None
    ) -> dict[str, object]:
        new_spec = self._spec(self.after, prefix, index, sub)
        old_spec = self._spec(self.before, prefix, index, sub)
        if attr is None:  # 整個效果新加或拿掉
            return self._whole(row, prefix, index, old_spec, new_spec)
        spec = new_spec or old_spec
        assert spec is not None
        if attr == "amount":
            return self._amount(row, spec)
        if attr == "multiplier_permille":
            skill = self.after if new_spec is not None else self.before
            weapon = effect_stat(self.library, skill, index, spec).weapon
            return {
                "name_zh": "傷害",
                "term": None,
                "before_zh": _ratio(row.before, weapon),
                "after_zh": _ratio(row.after, weapon),
                "icon": _card("damage"),
            }
        if attr == "magnitude_permille":
            update = _plain(row, self._magnitude_name(row, spec), None, None)
            update.update(
                before_zh=magnitude_zh(row.before, before=True),
                after_zh=magnitude_zh(row.after, before=False),
            )
            update["icon"] = _icon(spec)
            return update
        update = _plain(row, row.label_zh.removesuffix("骰子") or row.label_zh, None, None)
        update["icon"] = _card(_card_icon(spec))  # 骰子
        return update

    def _magnitude_name(self, row: StatChangeOut, spec: EffectSpec) -> str:
        """強度那一列的欄位名（FL-1f，玩法 PM 填答第六節）：寫「這個東西變的是什麼」。"""
        if spec.type == "enter_form":
            return "形態加成"
        if spec.type == "create_surface" and spec.surface is not None:
            ruleset = self.library.ruleset
            definition = ruleset.surface_def(spec.surface)
            name = _SURFACE_ZH.get(spec.surface.value) or definition.name_zh
            return name + ("傷害" if self._surface_hurts(spec.surface) else "效果")
        if spec.type == "apply_status" and spec.status is not None:
            status = self.statuses.get(str(spec.status))
            if status is not None:
                return status.name_zh + status_magnitude_suffix(status)
        return row.label_zh

    def _surface_hurts(self, surface: Surface) -> bool:
        """表面會不會造成傷害：回合開始的傷害，或進入、回合開始時施加每回合傷害的狀態（火焰的燃燒）。"""
        ruleset = self.library.ruleset
        definition = ruleset.surface_def(surface)
        start, enter = definition.on_turn_start, definition.on_enter
        if start is not None and start.damage is not None:
            return True
        applied = [
            s
            for s in (
                None if start is None else start.apply_status,
                None if enter is None else enter.apply_status,
            )
            if s is not None
        ]
        return any(ruleset.status_def(s).on_turn_start_damage is not None for s in applied)

    def _amount(self, row: StatChangeOut, spec: EffectSpec) -> dict[str, object]:
        if spec.type == "apply_status" and spec.status is not None:
            status = self.statuses.get(str(spec.status))
            name = str(spec.status) if status is None else status.name_zh
            update = _plain(row, name, "回合", f"status:{spec.status}")
            update["icon"] = ChangeIconOut(kind="status", id=str(spec.status))
            return update
        if (
            spec.type == "create_surface"
            and spec.surface is not None
            and row.label_zh.endswith("回合")
        ):
            surface = spec.surface.value
            name = _SURFACE_ZH.get(surface) or row.label_zh.removesuffix("回合")
            update = _plain(row, name, "回合", f"surface:{surface}")
            update["icon"] = _icon(spec)
            return update
        label, unit = row.label_zh, None
        for suffix, found in _AMOUNT_UNITS:
            if label.endswith(suffix) and label != suffix:
                label, unit = label.removesuffix(suffix), found
                break
        update = _plain(row, label, unit, None)
        update["icon"] = _icon(spec)
        return update

    def _whole(
        self,
        row: StatChangeOut,
        prefix: str,
        index: int,
        old_spec: EffectSpec | None,
        new_spec: EffectSpec | None,
    ) -> dict[str, object]:
        adding = row.before is None
        spec = new_spec if adding else old_spec
        skill = self.after if adding else self.before
        assert spec is not None
        phrase = self._phrase(skill, index, spec, makes=self.keyword if adding else None)
        return {
            "name_zh": _whole_name(prefix, skill, spec),
            "term": None,
            "before_zh": None if adding else phrase,
            "after_zh": phrase if adding else None,
            "icon": _icon(spec),
        }

    def _phrase(self, skill: SkillDef, index: int, spec: EffectSpec, *, makes: str | None) -> str:
        """整個效果的白話（9.3：「積水，會造成 潮濕」「3 成武器傷害（目標這回合被撞過才有）」）。"""
        if spec.type == "create_surface" and spec.surface is not None:
            surface = spec.surface.value
            name = _SURFACE_ZH.get(surface)
            if name is None:
                name = self.library.ruleset.surface_def(spec.surface).name_zh
            text = f"[[surface:{surface}|{name}]]"
            keyword = self._keyword_name(makes)
            if makes is not None and keyword is not None:
                text += f"，[[makes|會造成]] {{{{kw:{makes}}}}}[[kw:{makes}|{keyword}]]"
            return text
        if spec.type == "apply_status" and spec.status is not None:
            status = self.statuses.get(str(spec.status))
            name = str(spec.status) if status is None else status.name_zh
            rounds = spec.duration or (None if status is None else status.duration)
            tail = "" if rounds is None else f" {rounds} 回合"
            return f"[[status:{spec.status}|{name}]]{tail}"
        stat = effect_stat(self.library, skill, index, spec)
        if spec.type != "damage":
            return stat.label or _name(stat)
        if stat.weapon:
            times = _times(stat.multiplier_permille or _PERMILLE)
            text = _ratio(times, weapon=True, element=spec.element) or ""
        else:
            text = f"{stat.dice or ''} {stat.element_zh or ''}傷害".strip()
        if spec.condition is not None:
            text += f"（{self._condition(spec)}）"
        return text

    def _condition(self, spec: EffectSpec) -> str:
        assert spec.condition is not None
        custom = self.library.flash.condition_zh.get(spec.condition.type)
        if custom is not None:
            return custom
        ruleset = self.library.ruleset
        weapons = self.library.weapons
        text = condition_text(
            spec.condition,
            status_name=lambda s: self.statuses[s].name_zh if s in self.statuses else s,
            surface_name=lambda s: ruleset.surface_def(s).name_zh,
            tag_name=ruleset.skill_tags.name,  # FL-1g：沒帶時退回「特定」（FL-1b 驗收可修 2）
            tag_runes=ruleset.skill_tags.rune_names(),
            weapon_name=lambda w: weapons[w].name_zh if w in weapons else w,
        )
        return f"{text}才有" if text.endswith("時") else f"{text}時才有"

    def _keyword_name(self, keyword: str | None) -> str | None:
        found = None if keyword is None else self.library.keywords.by_id().get(keyword)
        return None if found is None else found.name_zh


def base_stats(library: ContentLibrary, skill: SkillDef) -> tuple[FlashBaseStatOut, ...]:
    """原技能列的數字（FL-1b 2.1）：代價（照卡片順序：AP、耐力、冷卻…）、射程、狀態回合。"""
    stats = card_stats(library, skill)
    out: list[FlashBaseStatOut] = []
    for cost in stats.costs:
        icon = _COST_ICON.get(cost.kind)
        out.append(
            FlashBaseStatOut(
                name_zh=_COST_ZH.get(cost.kind, cost.kind),
                value_zh=_cost_label(cost) or "",
                term=_COST_TERM.get(cost.kind),
                icon=None if icon is None else _card(icon),
            )
        )
    if stats.range is not None:
        out.append(
            FlashBaseStatOut(
                name_zh="射程", value_zh=str(stats.range), term="range", icon=_card("range")
            )
        )
    statuses = library.ruleset.statuses.by_id()
    for spec, stat in zip(skill.effects, stats.effects, strict=False):
        if spec.type != "apply_status" or spec.status is None or stat.amount is None:
            continue
        status = statuses.get(str(spec.status))
        out.append(
            FlashBaseStatOut(
                name_zh=str(spec.status) if status is None else status.name_zh,
                value_zh=f"{stat.amount} {stat.unit or '回合'}",
                term=f"status:{spec.status}",
                icon=ChangeIconOut(kind="status", id=str(spec.status)),
            )
        )
    return tuple(out)
