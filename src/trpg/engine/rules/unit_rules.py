"""單位身上所有規則來源的查詢（E2，``docs/design/08-裝備.md`` 8.29，#175）。

來源依固定順序：**種族的環境被動**，再依欄位固定順序（``main_hand`` → ``ring_2``）看裝備生效中的
第 12 類「地形規則」詞條（:class:`~trpg.content.equipment.TerrainAffix`）。

**同一種規則不疊加**（8.29 E2 第 1 點；開發 PM 與玩法 PM 2026-11-22 補定判法）。每條規則有一組
「鍵」——它作用的表面、天氣、地形或地圖標籤（:func:`rule_keys`；沒有這類參數的規則只有一個鍵）：

- 每個鍵由**第一個**給它的來源決定（開關型就是「有」；數值型取那個來源的數值）。後面的來源在這個鍵
  上沒有效果，不疊加。
- 一個來源的鍵**全部**被前面的來源給過 → 這條完全重複，標灰（:attr:`SourceOverlap.full`）。
- 只有**部分**鍵被給過 → 這條照樣生效，重疊的鍵只算一份，卡片註明重疊的部分。

判斷集中在 :func:`classify_sources`；戰鬥中的查詢 :func:`first_source` 用同一個規則（第一個給這個鍵
的來源），兩者一致。

裝備地形規則給的移動加成計入「裝備的移動加成合計」上限（8.21.5.3，``caps.move_bonus``）：
:func:`gear_move_room`。

查詢只讀規則包與單位狀態，是確定性的純函式。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from trpg.content.equipment import TerrainAffix, affix_text
from trpg.content.library import Ruleset
from trpg.content.slots import SLOT_INDEX, SLOT_ZH
from trpg.content.unit_rules import UnitRule
from trpg.engine.gear.state import GearAffix
from trpg.engine.state import UnitState
from trpg.shared.types import Surface

__all__ = [
    "ANY_KEY",
    "RuleSource",
    "SourceOverlap",
    "TerrainNote",
    "classify_sources",
    "first_source",
    "gear_move_room",
    "rule_keys",
    "rule_sources",
    "terrain_notes",
]

ANY_KEY = "*"
"""沒有表面、天氣、地形、地圖標籤參數的規則（例如輕身）唯一的鍵。"""

_KEY_FIELD: dict[str, str] = {
    "sight_penalty_reduction": "weathers",
    "sight_bonus_on_map_tag": "map_tags",
    "damage_taken_permille": "element",
    "slip_immunity": "surfaces",
    "conduction_immunity": "surfaces",
    "knockback_reduction_at_hazard": "terrain",
    "burn_immunity_on": "surfaces",
    "surface_move_bonus": "surfaces",
    "weather_move_bonus": "weathers",
    "surface_damage_immunity": "surfaces",
}
"""規則 → 決定「作用在哪裡」的參數欄位（沒列出的規則只有 :data:`ANY_KEY`）。"""


@dataclass(frozen=True, slots=True)
class RuleSource:
    """單位身上的一條規則。``gear`` 為 ``None`` 時是種族的環境被動。"""

    rule: UnitRule
    gear: GearAffix | None = None

    @property
    def from_race(self) -> bool:
        return self.gear is None


@dataclass(frozen=True, slots=True)
class SourceOverlap:
    """一條規則和前面來源的重疊：``covered`` 是被前面的來源給過的鍵（鍵 → 給它的那個來源），
    依鍵在本規則中的順序。"""

    source: RuleSource
    covered: tuple[tuple[str, RuleSource], ...]

    @property
    def full(self) -> bool:
        """所有鍵都被前面給過：完全重複（標灰、沒有效果）。"""
        return len(self.covered) == len(rule_keys(self.source.rule))


def rule_keys(rule: UnitRule) -> tuple[str, ...]:
    """規則作用的鍵（表面、天氣、地形、地圖標籤或元素的 ID，依資料順序、不重複）。"""
    field = _KEY_FIELD.get(rule.rule)
    if field is None:
        return (ANY_KEY,)
    value = getattr(rule, field)
    if value is None:
        return ()
    items = value if isinstance(value, tuple) else (value,)
    return tuple(dict.fromkeys(str(getattr(v, "value", v)) for v in items))


def rule_sources(rules: Ruleset, unit: UnitState) -> tuple[RuleSource, ...]:
    """單位身上所有的規則來源：種族先，再依欄位固定順序（同欄位依詞條 ID）看生效中的地形規則。
    種族 ID 不存在時拋 ``KeyError``（載入時已驗證）。"""
    found: list[RuleSource] = []
    if unit.race is not None:
        found.append(RuleSource(rules.race_def(unit.race).passive))
    terrain = unit.gear.active_affixes("terrain") if unit.gear.affixes else ()
    if terrain:
        ordered = sorted(terrain, key=lambda g: (SLOT_INDEX[g.slot], g.affix.id))
        found += [RuleSource(g.affix, g) for g in ordered if isinstance(g.affix, TerrainAffix)]
    return tuple(found)


def first_source(
    rules: Ruleset, unit: UnitState, rule: str, keys: Iterable[str] = (ANY_KEY,)
) -> RuleSource | None:
    """第一個在 ``keys`` 的任一個鍵上給了規則 ``rule`` 的來源（就是那個鍵上生效的來源）；沒有時
    ``None``。"""
    wanted = set(keys)
    for source in rule_sources(rules, unit):
        if source.rule.rule == rule and wanted.intersection(rule_keys(source.rule)):
            return source
    return None


def classify_sources(sources: Iterable[RuleSource]) -> tuple[SourceOverlap, ...]:
    """每個來源和前面來源的重疊（依來源順序；判斷規則見模組說明）。"""
    given: dict[tuple[str, str], RuleSource] = {}
    result: list[SourceOverlap] = []
    for source in sources:
        kind = source.rule.rule
        keys = rule_keys(source.rule)
        covered = tuple((k, given[kind, k]) for k in keys if (kind, k) in given)
        result.append(SourceOverlap(source, covered))
        for key in keys:
            given.setdefault((kind, key), source)
    return tuple(result)


def gear_move_room(rules: Ruleset, unit: UnitState) -> int:
    """裝備的移動加成合計上限（``caps.move_bonus``）扣掉裝備數值詞條已經給的移動之後，地形規則還
    能加多少（最少 0）。數值詞條的移動是上限之前的合計，先截到上限；塔盾的移動 −N 在上限之後，
    不算進來（同 :func:`trpg.engine.gear.core.build_gear`）。"""
    cap = rules.equipment.caps.move_bonus
    static = min(dict(unit.gear.uncapped).get("move", 0), cap)
    return max(0, cap - static)


# ---------------------------------------------------------------------------
# 顯示：裝備地形規則的標灰與重疊說明
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TerrainNote:
    """一條裝備地形規則的顯示說明：``duplicate_of`` 不為 ``None`` ＝ 完全重複（標灰；內容是重複的
    那個來源，前端寫成「和〇〇重複，沒有效果」）；``overlap_zh`` 是部分重疊的說明（例「冰的部分
    和種族重複」）。"""

    duplicate_of: str | None = None
    overlap_zh: str | None = None


def _source_label(rules: Ruleset, unit: UnitState, source: RuleSource) -> str:
    """完全重複時的來源名稱：種族「種族被動「炎膚」」；裝備「部位的詞條文字」。"""
    if source.gear is None:
        assert unit.race is not None
        return f"種族被動「{rules.race_def(unit.race).passive.name_zh}」"
    return f"{SLOT_ZH[source.gear.slot]}的{affix_text(source.gear.affix, source.gear.value)}"


def _source_short(source: RuleSource) -> str:
    """部分重疊時的來源簡稱：「種族」或「部位的「詞條文字」」。"""
    if source.gear is None:
        return "種族"
    text = affix_text(source.gear.affix, source.gear.value)
    return f"{SLOT_ZH[source.gear.slot]}的「{text}」"


def _key_name(rules: Ruleset, rule: UnitRule, key: str, names: Mapping[str, str]) -> str:
    """鍵的中文名（表面、地形查規則包；天氣、地圖標籤查 ``names``，沒有時用 ID）。"""
    field = _KEY_FIELD.get(rule.rule)
    if field == "surfaces":
        return rules.surface_def(Surface(key)).name_zh
    if field == "terrain":
        return rules.terrain_def(key).name_zh
    return names.get(key, key)


def terrain_notes(
    rules: Ruleset, unit: UnitState, names: Mapping[str, str] | None = None
) -> dict[tuple[str, str], TerrainNote]:
    """裝備地形規則（欄位, 詞條 ID）→ 顯示說明（只列有重複或重疊的）。``names``：天氣、地圖標籤的
    中文名。"""
    names = names or {}
    notes: dict[tuple[str, str], TerrainNote] = {}
    for overlap in classify_sources(rule_sources(rules, unit)):
        gear = overlap.source.gear
        if gear is None or not overlap.covered:
            continue
        key = (gear.slot, gear.affix.id)
        if overlap.full:
            notes[key] = TerrainNote(duplicate_of=_source_label(rules, unit, overlap.covered[0][1]))
            continue
        groups: dict[int, tuple[RuleSource, list[str]]] = {}
        for k, source in overlap.covered:
            groups.setdefault(id(source), (source, []))[1].append(
                _key_name(rules, overlap.source.rule, k, names)
            )
        parts = [
            f"{'、'.join(keys)}的部分和{_source_short(source)}重複"
            for source, keys in groups.values()
        ]
        notes[key] = TerrainNote(overlap_zh="；".join(parts))
    return notes
