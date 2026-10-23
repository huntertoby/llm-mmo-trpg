"""格子資訊卡的靜態說明（Phase 3-15）：由內容資料自動產生地形、表面、物件的中文「會怎樣」。

純函式、確定性；不讀時間、不用亂數。每種標籤、欄位、互動到中文短句的對照表都在本檔
（``OBJECT_TAG_TEXT``、``OUTCOME_TEXT``、``TERM_*``）。新增內容只要使用既有標籤、欄位與互動，
就自動有說明；未知標籤顯示原名（不出錯），並由 :func:`unknown_terms` 列出，測試中視為警告。

動態部分（剩餘回合、目前 HP、持續區域、預告、陷阱）不在這裡：前端從戰鬥視圖組合。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from trpg.content.battle import StatusTable, TerrainDef
from trpg.content.environment import (
    InteractionOutcome,
    InteractionRule,
    ObjectDef,
    SurfaceDef,
)
from trpg.content.library import ContentLibrary, Ruleset
from trpg.shared.types import Surface

__all__ = [
    "OBJECT_TAG_TEXT",
    "TERM_BLOCKS_MOVE",
    "TERM_BLOCKS_SIGHT",
    "TERM_DEADLY",
    "TERM_HALF_COVER",
    "object_rules",
    "surface_rules",
    "terrain_rules",
    "unknown_terms",
]

# ---------------------------------------------------------------------------
# 共用用語（前端圖例與資訊卡一致；測試比對 client/src/battle/legend.ts）
# ---------------------------------------------------------------------------

TERM_DEADLY = "致命地形"
TERM_BLOCKS_MOVE = "不可通行"
TERM_BLOCKS_SIGHT = "擋視線"
TERM_HALF_COVER = "半掩護"

# 物件標籤 → 中文短句。固定順序（顯示時依此排序）。``{radius}`` 等由 _tag_text 補上。
OBJECT_TAG_TEXT: Mapping[str, str] = {
    "blocks_move": TERM_BLOCKS_MOVE,
    "blocks_sight": f"{TERM_BLOCKS_SIGHT}（全掩護）",
    "half_cover": f"{TERM_HALF_COVER}（遠程攻擊其後的目標，命中 −{{penalty}}）",
    "conceal": "站在同一格的單位隱蔽（這是物件的效果，同名的地面不會隱蔽）",
    "over_chasm": "架在致命地形上，可以走；被打破後格上的單位會落下",
    "pushable": "可推動",
    "topplable": "可推倒（往推的方向倒下，壓住後面 {topple} 格）",
    "breakable": "可被破壞",
    "penetrable": "穿透型攻擊可以穿過",
    "flammable": "可燃",
    "explosive": "碰火爆炸",
    "conductive": "導電",
    "freezable": "可結冰",
    "meltable": "遇火融化",
    "extinguish": "可熄滅火焰",
}

# 互動結果 → 中文短句。ops 需要參數的用函式。
_OutcomeText = Callable[[InteractionOutcome, "_Names"], str]


class _Names:
    """ID → 中文名（表面、狀態、元素、地形）。"""

    def __init__(self, library: ContentLibrary) -> None:
        rules = library.ruleset
        self.surface = {s.id.value: s.name_zh for s in rules.surfaces.surfaces}
        self.terrain = {t.id: t.name_zh for t in rules.terrain.terrain}
        self.status = {s.id: s.name_zh for s in rules.statuses.statuses}
        self.element = {e.id.value: e.name_zh for e in library.elements.elements}

    def of(self, table: Mapping[str, str], key: str | None) -> str:
        if key is None:
            return "?"
        return table.get(key, key)


_UNIT_TAG_TEXT: Mapping[str, str] = {"undead": "不死系"}


def _set_surface(o: InteractionOutcome, n: _Names) -> str:
    if o.surface is None or o.surface is Surface.NONE:
        return "消失"
    return f"變成{n.of(n.surface, o.surface.value)}"


def _apply_status(o: InteractionOutcome, n: _Names) -> str:
    name = n.of(n.status, o.status)
    turns = "" if o.duration is None else f" {o.duration} 回合"
    return f"獲得{name}{turns}"


OUTCOME_TEXT: Mapping[str, _OutcomeText] = {
    "set_surface": _set_surface,
    "ignite_object": lambda o, n: "被點燃（燃燒後摧毀，並產生火焰）",
    "explode": lambda o, n: "爆炸",
    "conduct": lambda o, n: "沿相連的水與導電物傳導，波及其上的其他單位",
    "push": lambda o, n: "被推動",
    "spread_surface": lambda o, n: (
        f"沿方向蔓延到下一格（{n.of(n.surface, o.surface.value if o.surface else None)}）"
    ),
    "fill_chasm": lambda o, n: f"被填平，格子變成{n.of(n.terrain, o.terrain)}",
    "destroy_object": lambda o, n: "被摧毀",
    "apply_status": _apply_status,
    "keep": lambda o, n: "維持原狀",
}


def _outcome_text(rule: InteractionRule, names: _Names) -> str:
    parts = []
    for outcome in rule.then:
        fn = OUTCOME_TEXT.get(outcome.op)
        text = fn(outcome, names) if fn is not None else outcome.op
        if outcome.op == "push" and rule.object_tag == "topplable":
            text = "被推倒"
        elif outcome.op == "destroy_object" and rule.object_tag == "meltable":
            text = "融化消失"
        parts.append(text)
    return "，".join(parts)


def _trigger_text(rule: InteractionRule, names: _Names) -> str:
    if rule.trigger == "element":
        return names.of(names.element, rule.element.value if rule.element else None)
    created = names.of(names.surface, rule.surface_created.value if rule.surface_created else None)
    return f"在上面產生{created}"


def _interaction_line(rule: InteractionRule, names: _Names) -> str:
    only_keep = all(o.op == "keep" for o in rule.then)
    if only_keep and rule.trigger != "element":  # 「在上面產生火焰：維持原狀」→ 說清楚是產生不了
        created = names.of(
            names.surface, rule.surface_created.value if rule.surface_created else None
        )
        return f"{created}無法在上面形成"
    return f"{_trigger_text(rule, names)}：{_outcome_text(rule, names)}"


# ---------------------------------------------------------------------------
# 地形
# ---------------------------------------------------------------------------


def terrain_rules(terrain: TerrainDef, ruleset: Ruleset) -> tuple[str, ...]:
    lines: list[str] = []
    if terrain.deadly:
        pct = ruleset.core.deadly_terrain_elite_permille // 10
        lines.append(TERM_BLOCKS_MOVE)
        lines.append(f"{TERM_DEADLY}：被推進去的單位死亡（精英與 Boss 改受 {pct}% 最大 HP 傷害）")
    elif terrain.walkable:
        lines.append("可通行")
    else:
        lines.append(TERM_BLOCKS_MOVE)
    if terrain.blocks_sight:
        lines.append(f"{TERM_BLOCKS_SIGHT}（全掩護）；一般攻擊無法破壞")
    return tuple(lines)


# ---------------------------------------------------------------------------
# 表面
# ---------------------------------------------------------------------------


def _surface_property_lines(s: SurfaceDef, names: _Names, statuses: StatusTable) -> list[str]:
    lines: list[str] = []
    if s.duration is not None:
        after = (
            ""
            if s.expires_to is Surface.NONE
            else f"，之後變成{names.of(names.surface, s.expires_to.value)}"
        )
        lines.append(f"由技能產生時持續 {s.duration} 回合{after}")
    if s.element is not None:
        lines.append(
            f"帶有{names.of(names.element, s.element.value)}元素（產生時會觸及格上的物件）"
        )
    if s.flammable:
        lines.append("可燃：火勢會蔓延過來")
    if s.blocks_sight:
        lines.append(TERM_BLOCKS_SIGHT)
    if s.conceal:
        lines.append("站在上面的單位隱蔽")
    if s.beneficial:
        lines.append("對站在上面的友方有益")
    lines.extend(_surface_effect_lines(s, names))
    return lines


def _surface_effect_lines(s: SurfaceDef, names: _Names) -> list[str]:
    lines: list[str] = []
    if s.on_enter is not None:
        if s.on_enter.check is not None:
            c = s.on_enter.check
            fail = names.of(names.status, c.fail_status)
            lines.append(f"進入時 {c.attr.display_name}檢定 DC {c.dc}，失敗會{fail}（滑倒判定）")
        if s.on_enter.apply_status is not None:
            lines.append(f"進入時獲得{names.of(names.status, s.on_enter.apply_status)}")
    if s.on_turn_start is not None:
        t = s.on_turn_start
        if t.damage is not None:
            tag = t.damage.only_tag
            who = "" if tag is None else f"（只傷害{_UNIT_TAG_TEXT.get(tag, tag)}）"
            elem = names.of(names.element, t.damage.element.value)
            lines.append(f"回合開始時站在上面的單位受 {t.damage.dice} {elem}傷害{who}")
        if t.heal is not None:
            lines.append(f"回合開始時治療站在上面的友方 {t.heal.dice}")
        if t.apply_status is not None:
            lines.append(f"回合開始時獲得{names.of(names.status, t.apply_status)}")
    return lines


def _surface_interactions(
    surface: Surface, rules: tuple[InteractionRule, ...], names: _Names
) -> list[str]:
    lines: list[str] = []
    for r in rules:
        if r.target == "surface" and r.surface is surface:
            lines.append(_interaction_line(r, names))
        elif r.target == "unit" and r.unit_surface is surface:
            lines.append(f"{_trigger_text(r, names)}：站在上面的單位{_outcome_text(r, names)}")
    return lines


def surface_rules(surface: SurfaceDef, library: ContentLibrary) -> tuple[str, ...]:
    names = _Names(library)
    ruleset = library.ruleset
    lines = _surface_property_lines(surface, names, ruleset.statuses)
    lines.extend(_surface_interactions(surface.id, ruleset.interactions.rules, names))
    return tuple(lines)


# ---------------------------------------------------------------------------
# 物件
# ---------------------------------------------------------------------------


def _tag_text(tag: str, ruleset: Ruleset) -> str:
    text = OBJECT_TAG_TEXT.get(tag)
    if text is None:
        return tag
    return text.format(
        penalty=ruleset.core.half_cover_hit_penalty, topple=ruleset.core.topple_length
    )


def object_rules(obj: ObjectDef, library: ContentLibrary) -> tuple[str, ...]:
    names = _Names(library)
    ruleset = library.ruleset
    order = list(OBJECT_TAG_TEXT)
    tags = sorted(obj.tags, key=lambda t: (order.index(t) if t in order else len(order), t))
    lines = [_tag_text(t, ruleset) for t in tags]
    if obj.max_hp is not None and "breakable" in obj.tags:  # 可被破壞的物件寫出 HP（6.4）
        at = tags.index("breakable")
        lines[at] = f"{lines[at]}（HP {obj.max_hp}）"
    if obj.explosion is not None:
        e = obj.explosion
        side = 2 * e.radius + 1
        elem = names.of(names.element, e.element.value)
        flat = f"+{e.flat}" if e.flat else ""
        lines.append(f"爆炸範圍 {side}×{side}，{e.dice}{flat} {elem}傷害")
    if obj.spill is not None:
        spill = names.of(names.surface, obj.spill.surface.value)
        lines.append(f"被傷害打破或摔破時（非被火引爆）漏出{spill}")
    seen: set[tuple[str, str]] = set()
    for r in ruleset.interactions.rules:
        if r.target != "object" or r.object_tag not in obj.tags:
            continue
        key = (r.trigger, _trigger_text(r, names))
        if key in seen:  # 同一次觸及只套用第一條符合的規則（依檔案順序）
            continue
        seen.add(key)
        lines.append(_interaction_line(r, names))
    return tuple(lines)


# ---------------------------------------------------------------------------
# 未知項目（測試列為警告）
# ---------------------------------------------------------------------------


def unknown_terms(library: ContentLibrary) -> tuple[str, ...]:
    """內容用到、但本檔沒有中文對照的標籤與互動結果（排序）。"""
    found: set[str] = set()
    for o in library.ruleset.objects.objects:
        found.update(f"object_tag:{t}" for t in o.tags if t not in OBJECT_TAG_TEXT)
    for r in library.ruleset.interactions.rules:
        found.update(f"outcome:{x.op}" for x in r.then if x.op not in OUTCOME_TEXT)
        if r.object_tag is not None and r.object_tag not in OBJECT_TAG_TEXT:
            found.add(f"object_tag:{r.object_tag}")
    return tuple(sorted(found))
