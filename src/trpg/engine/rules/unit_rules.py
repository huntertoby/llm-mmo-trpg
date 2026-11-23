"""單位身上所有規則來源的查詢（E2，``docs/design/08-裝備.md`` 8.29，#175）。

來源依固定順序：**種族的環境被動**，再依欄位固定順序（``main_hand`` → ``ring_2``）看裝備生效中的
第 12 類「地形規則」詞條（:class:`~trpg.content.equipment.TerrainAffix`）。

**同一種規則不疊加**（8.29 E2 第 1 點；開發 PM 與玩法 PM 2026-11-22 補定判法）。每條規則有一組
「鍵」——它作用的表面、天氣、地形或地圖標籤（:func:`rule_keys`；沒有這類參數的規則只有一個鍵）：

- 每個鍵只有**一個**來源生效（開關型就是「有」；數值型取那個來源的數值），不疊加。
- 誰生效：開關型是**第一個**給它的來源。數值型（``amount``、``permille``、``radius``、``duration``）
  取**較強**的那條（E3，08 8.29 E2 補充；開發 PM 2026-11-22 補定）：比的是實際值——裝備給的移動加成
  先截到裝備移動合計上限（:func:`gear_move_room`）再比；一樣強時排在前面的生效（種族先）。只有其他
  參數也相同時才比強弱（例 ``trail_surface`` 的表面不同時，排在前面的生效）。
- 一個來源的鍵**全部**由別的來源生效 → 這條沒有效果（:attr:`SourceOverlap.full`）：裝備標灰；種族
  那條在角色面板註明被蓋過（:func:`race_override_zh`）。
- 只有**部分**鍵由別的來源生效 → 這條照樣生效，重疊的鍵只算一份，卡片註明重疊的部分。

判斷集中在 :func:`classify_sources`；戰鬥中的查詢 :func:`first_source` 用同一個規則（那個鍵上生效的
來源），兩者一致。

裝備地形規則給的移動加成計入「裝備的移動加成合計」上限（8.21.5.3，``caps.move_bonus``）：
:func:`gear_move_room`。

查詢只讀規則包與單位狀態，是確定性的純函式。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

from trpg.content.equipment import TerrainAffix, affix_text
from trpg.content.library import Ruleset
from trpg.content.slots import SLOT_INDEX, SLOT_ZH
from trpg.content.unit_rules import UNIT_RULE_SPECS, UnitRule
from trpg.engine.gear.state import GearAffix, GearState
from trpg.engine.state import UnitState
from trpg.shared.types import Surface

__all__ = [
    "ANY_KEY",
    "RuleSource",
    "SourceOverlap",
    "Strength",
    "TerrainNote",
    "classify_sources",
    "effective_strength",
    "first_source",
    "gear_move_room",
    "gear_rule_sources",
    "gear_strength",
    "race_overridden_fully",
    "race_override_zh",
    "raw_strength",
    "rule_keys",
    "rule_sources",
    "terrain_notes",
    "winners",
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
    """一條規則和其他來源的重疊：``covered`` 是由別的來源生效的鍵（鍵 → 生效的那個來源），依鍵在
    本規則中的順序。"""

    source: RuleSource
    covered: tuple[tuple[str, RuleSource], ...]

    @property
    def full(self) -> bool:
        """所有鍵都由別的來源生效：完全重複（沒有效果）。"""
        return len(self.covered) == len(rule_keys(self.source.rule))


type Strength = Callable[[RuleSource], int]
"""一個來源的強弱（越大越強；:func:`raw_strength`、:func:`effective_strength`）。"""

_NUMERIC_FIELDS = ("amount", "permille", "radius", "duration")
_MOVE_RULES = frozenset({"surface_move_bonus", "weather_move_bonus"})


def raw_strength(source: RuleSource) -> int:
    """規則的數值（越大越強；元素減傷 ``permille`` 是負數，取絕對值）；開關型為 0。"""
    rule = source.rule
    for name in _NUMERIC_FIELDS:
        value: int | None = getattr(rule, name)
        if value is not None:
            return abs(value) if rule.rule == "damage_taken_permille" else value
    return 0


def effective_strength(rules: Ruleset, unit: UnitState) -> Strength:
    """實際的強弱：裝備給的移動加成先截到裝備移動合計上限（:func:`gear_move_room`；開發 PM
    2026-11-22），其他同 :func:`raw_strength`。"""
    return gear_strength(rules, unit.gear)


def gear_strength(rules: Ruleset, gear: GearState) -> Strength:
    """:func:`effective_strength`，但直接看裝備狀態（建立單位之前用；E6-b1 名額）。"""
    room = _move_room(rules, gear)

    def strength(source: RuleSource) -> int:
        value = raw_strength(source)
        if source.gear is not None and source.rule.rule in _MOVE_RULES:
            return min(value, room)
        return value

    return strength


def _signature(rule: UnitRule) -> tuple[object, ...]:
    """比強弱前要相同的其他參數（不含鍵與數值；例 ``trail_surface`` 的表面）。"""
    key_field = _KEY_FIELD.get(rule.rule)
    spec = UNIT_RULE_SPECS[rule.rule]
    return tuple(
        getattr(rule, name)
        for name in spec.required
        if name != key_field and name not in _NUMERIC_FIELDS
    )


def winners(
    sources: Sequence[RuleSource], strength: Strength = raw_strength
) -> dict[tuple[str, str], RuleSource]:
    """每個（規則種類, 鍵）上生效的來源（規則見模組說明）：依來源順序走，較強而且其他參數相同時
    取代。"""
    won: dict[tuple[str, str], RuleSource] = {}
    for source in sources:
        kind = source.rule.rule
        for key in rule_keys(source.rule):
            current = won.get((kind, key))
            if current is None or (
                strength(source) > strength(current)
                and _signature(source.rule) == _signature(current.rule)
            ):
                won[kind, key] = source
    return won


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
    return gear_rule_sources(rules, unit.race, unit.gear)


def gear_rule_sources(rules: Ruleset, race: str | None, gear: GearState) -> tuple[RuleSource, ...]:
    """:func:`rule_sources`，但直接看種族與裝備狀態（建立單位之前用；E6-b1 名額）。"""
    found: list[RuleSource] = []
    if race is not None:
        found.append(RuleSource(rules.race_def(race).passive))
    terrain = gear.active_affixes("terrain") if gear.affixes else ()
    if terrain:
        ordered = sorted(terrain, key=lambda g: (SLOT_INDEX[g.slot], g.affix.id))
        found += [RuleSource(g.affix, g) for g in ordered if isinstance(g.affix, TerrainAffix)]
    return tuple(found)


def first_source(
    rules: Ruleset, unit: UnitState, rule: str, keys: Iterable[str] = (ANY_KEY,)
) -> RuleSource | None:
    """``keys`` 的鍵上生效的規則 ``rule`` 的來源（:func:`winners`）；好幾個鍵各有不同的來源時取
    最強的、一樣強時取排在前面的。沒有時 ``None``。"""
    sources = tuple(s for s in rule_sources(rules, unit) if s.rule.rule == rule)
    if not sources:
        return None
    strength = effective_strength(rules, unit)
    won = winners(sources, strength)
    found = [won[rule, k] for k in keys if (rule, k) in won]
    if not found:
        return None
    order = {id(s): i for i, s in enumerate(sources)}
    return max(found, key=lambda s: (strength(s), -order[id(s)]))


def classify_sources(
    sources: Iterable[RuleSource], strength: Strength = raw_strength
) -> tuple[SourceOverlap, ...]:
    """每個來源和其他來源的重疊（依來源順序；判斷規則見模組說明）。``strength``：比強弱用的值
    （戰鬥與顯示用 :func:`effective_strength`）。"""
    ordered = tuple(sources)
    won = winners(ordered, strength)
    result: list[SourceOverlap] = []
    for source in ordered:
        kind = source.rule.rule
        covered = tuple(
            (k, won[kind, k]) for k in rule_keys(source.rule) if won[kind, k] is not source
        )
        result.append(SourceOverlap(source, covered))
    return tuple(result)


def gear_move_room(rules: Ruleset, unit: UnitState) -> int:
    """裝備的移動加成合計上限（``caps.move_bonus``）扣掉裝備數值詞條已經給的移動之後，地形規則還
    能加多少（最少 0）。數值詞條的移動是上限之前的合計，先截到上限；塔盾的移動 −N 在上限之後，
    不算進來（同 :func:`trpg.engine.gear.core.build_gear`）。"""
    return _move_room(rules, unit.gear)


def _move_room(rules: Ruleset, gear: GearState) -> int:
    cap = rules.equipment.caps.move_bonus
    static = min(dict(gear.uncapped).get("move", 0), cap)
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
    for overlap in classify_sources(rule_sources(rules, unit), effective_strength(rules, unit)):
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


def race_overridden_fully(rules: Ruleset, unit: UnitState) -> bool:
    """種族的環境被動整條都被裝備蓋過（E3b 顯示「…蓋過，沒有作用」）；部分蓋過或沒被蓋過為假。"""
    if unit.race is None:
        return False
    overlaps = classify_sources(rule_sources(rules, unit), effective_strength(rules, unit))
    race = next((o for o in overlaps if o.source.gear is None), None)
    return race is not None and bool(race.covered) and race.full


def race_override_zh(
    rules: Ruleset, unit: UnitState, names: Mapping[str, str] | None = None
) -> str | None:
    """種族的環境被動被裝備較強的同種規則蓋過時的說明（E3，08 8.29 E2 補充）：完全蓋過「被腳的
    「水上移動 +2」蓋過」；部分「水的部分被腳的「……」蓋過」。沒有被蓋過時 ``None``。"""
    if unit.race is None:
        return None
    names = names or {}
    overlaps = classify_sources(rule_sources(rules, unit), effective_strength(rules, unit))
    race = next((o for o in overlaps if o.source.gear is None), None)
    if race is None or not race.covered:
        return None
    if race.full and len({id(s) for _, s in race.covered}) == 1:
        return f"被{_source_short(race.covered[0][1])}蓋過"
    groups: dict[int, tuple[RuleSource, list[str]]] = {}
    for k, source in race.covered:
        groups.setdefault(id(source), (source, []))[1].append(
            _key_name(rules, race.source.rule, k, names)
        )
    return "；".join(
        f"{'、'.join(keys)}的部分被{_source_short(source)}蓋過" for source, keys in groups.values()
    )
