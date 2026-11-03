"""裝備共鳴（Phase 5D-3；08 8.9、8.26.3 M3；``docs/phases/Phase5計畫.md`` 30.4）。

物品的共鳴關鍵字＝技能強化詞條的關鍵字＋``resonance_<關鍵字>`` 標籤（打造時特色材料帶的）。主角開戰
時，穿戴中帶同一關鍵字的裝備 ≥ ``pieces`` 件（第一季 2 件）→ 加上那個共鳴的詞條：依序挑第一條
「掛得上帶該關鍵字的某件物品（依欄位順序）、那件沒有同 ID、穿戴驗證通過」的詞條（代決 5D3-8：
只算主角）。

純函式：只改開戰用的裝備快照，不改角色存檔。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from trpg.content.battle import WeaponDef
from trpg.content.equipment import (
    AffixRoll,
    EquippedAffix,
    EquippedItem,
    ItemDef,
    KeywordAffix,
    Loadout,
    affix_text,
    loadout_problems,
)
from trpg.content.library import ContentLibrary
from trpg.content.world_crafting import ResonanceDef

__all__ = [
    "ActiveResonance",
    "active_resonances",
    "apply_resonance",
    "item_keywords",
]

_TAG = "resonance_"


def item_keywords(library: ContentLibrary, item: ItemDef) -> tuple[str, ...]:
    """這件物品的共鳴關鍵字（排序、不重複）。"""
    found: set[str] = {t.removeprefix(_TAG) for t in item.tags if t.startswith(_TAG)}
    for roll in item.affixes:
        affix = library.affixes.get(roll.affix)
        if isinstance(affix, KeywordAffix):
            found.add(affix.keyword)
    return tuple(sorted(found))


@dataclass(frozen=True)
class ActiveResonance:
    """觸發的一個共鳴：關鍵字、件數、加上的詞條（掛不上時 ``slot`` 為 ``None``）。"""

    resonance: ResonanceDef
    pieces: int
    slot: str | None
    affix: str | None
    value: int | None

    def text_zh(self, library: ContentLibrary) -> str:
        keyword = library.keywords.by_id().get(self.resonance.keyword)
        name = self.resonance.keyword if keyword is None else keyword.name_zh
        head = f"{self.resonance.name_zh}（{name} {self.pieces} 件）"
        if self.affix is None:
            return f"{head}：這身裝備掛不上共鳴的效果"
        return f"{head}：{affix_text(library.affixes[self.affix], self.value)}"


def _counts(library: ContentLibrary, entries: Iterable[EquippedItem]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for i, entry in enumerate(entries):
        for keyword in item_keywords(library, entry.item):
            found.setdefault(keyword, []).append(i)
    return found


def _attach(
    library: ContentLibrary,
    loadout: Loadout,
    weapon: WeaponDef,
    res: ResonanceDef,
    carriers: list[int],
) -> tuple[Loadout, ActiveResonance] | None:
    for entry_def in res.affixes:
        affix = library.affixes[entry_def.affix]
        for index in carriers:
            entry = loadout.items[index]
            if any(e.affix.id == affix.id for e in entry.affixes):
                continue
            item = entry.item.model_copy(
                update={
                    "affixes": (
                        *entry.item.affixes,
                        AffixRoll(affix=entry_def.affix, value=entry_def.value),
                    )
                }
            )
            new_entry = entry.model_copy(
                update={
                    "item": item,
                    "affixes": (*entry.affixes, EquippedAffix(affix=affix, value=entry_def.value)),
                }
            )
            items = list(loadout.items)
            items[index] = new_entry
            candidate = Loadout(items=tuple(items))
            if not loadout_problems(candidate, weapon, library.ruleset.equipment):
                active = ActiveResonance(
                    res, len(carriers), entry.slot, entry_def.affix, entry_def.value
                )
                return candidate, active
    return None


def apply_resonance(
    library: ContentLibrary, loadout: Loadout, weapon: WeaponDef
) -> tuple[Loadout, tuple[ActiveResonance, ...]]:
    """加上共鳴詞條後的裝備快照與觸發的共鳴（依關鍵字排序）。沒有共鳴規則時原樣回傳。"""
    rules = library.world_resonance
    if rules is None or not loadout.items:
        return loadout, ()
    active: list[ActiveResonance] = []
    for keyword, carriers in sorted(_counts(library, loadout.items).items()):
        res = rules.of(keyword)
        if res is None or len(carriers) < rules.pieces:
            continue
        done = _attach(library, loadout, weapon, res, carriers)
        if done is None:
            active.append(ActiveResonance(res, len(carriers), None, None, None))
            continue
        loadout, found = done
        active.append(found)
    return loadout, tuple(active)


def active_resonances(
    library: ContentLibrary, loadout: Loadout, weapon: WeaponDef
) -> tuple[ActiveResonance, ...]:
    """目前觸發的共鳴（給畫面顯示）。"""
    return apply_resonance(library, loadout, weapon)[1]
