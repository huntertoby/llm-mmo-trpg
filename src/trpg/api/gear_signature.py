"""招牌效果的顯示資料（E6-b2，``docs/design/08-裝備.md`` 8.27、8.30 第 4 點）：裝備卡第一行的招牌
框、誰生效、標灰的原因、角色面板的勾選清單。

- **種類**（:func:`signature_kind`）：標了 ``signature`` 的照它；沒標的改寫規則（第 11 類）也是改寫
  規則（全身同時 1 條，角色面板一樣可以選）。
- **類型牌**（:func:`signature_label_zh`）：「招牌・新動作」；傳說的獨特效果、獨特裝備的招牌寫
  「獨特效果・新動作」。
- **標灰的原因**：裝備卡、比較、撿到時用長版（:data:`~trpg.engine.view.SIGNATURE_LIMITED_ZH`），
  角色面板用短版（:data:`SIGNATURE_SHORT_ZH`）；改寫規則衝突照 8.27
  （:data:`~trpg.engine.view.RULE_LIMITED_ZH`）。
- **誰生效**照開戰時的算法（:func:`trpg.roguelite.gear.limited_gear`），所以顯示和戰鬥一致。

只看主角自己的裝備（守則 14：角色面板與勾選只給玩家自己的角色；其他單位照戰鬥的單位資訊顯示）。
"""

from __future__ import annotations

from trpg.api.gear_schemas import SignaturePanelOut, SignatureRowOut
from trpg.content.equipment import (
    SIGNATURE_KIND_ZH,
    ActionAffix,
    AffixDef,
    ItemDef,
    affix_text,
    chosen_key,
)
from trpg.content.item_budget import is_legendary, legendary_unique
from trpg.content.library import ContentLibrary
from trpg.content.slots import SLOT_ZH
from trpg.engine.gear.limits import whole_no_effect
from trpg.engine.gear.state import GearAffix, GearState
from trpg.engine.view import limit_off_zh
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.gear import equip, limited_gear, may_overflow, run_loadout
from trpg.roguelite.state import RunState

__all__ = [
    "SIGNATURE_FULL_ZH",
    "SIGNATURE_SHORT_ZH",
    "candidate_off",
    "signature_kind",
    "signature_label_zh",
    "signature_name_zh",
    "signature_panel",
    "worn_off",
]

SIGNATURE_SHORT_ZH = "已經有 {n} 個生效，這個沒有效果"
"""角色面板裡、超過名額的灰字（短版，08 8.30 第 4 點用字；``n`` 是 ``caps.signature_active``）。"""

SIGNATURE_FULL_ZH = "已經有 {n} 個生效，先取消勾選一個，再勾這個。"
"""已滿時按沒勾的那列的提示（08 8.30 第 4 點用字，美術移植需求第 3 節標「暫定」）。"""

_DUPLICATE_ZH = "和{slot}的這條重複，沒有效果"


def signature_kind(affix: AffixDef) -> str | None:
    """招牌框的種類：標了招牌的照它，沒標的改寫規則算改寫規則；其他 ``None``。"""
    if affix.signature is not None:
        return affix.signature
    return "rule" if affix.category == "rule" else None


def _unique(library: ContentLibrary, item: ItemDef, affix: AffixDef) -> bool:
    """傳說的獨特效果，或獨特裝備的招牌（8.30 第 9 點：獨特效果就是那件的招牌）。"""
    if is_legendary(item) and legendary_unique(affix):
        return True
    rules = library.item_gen
    return rules is not None and affix.id in rules.unique_affixes


def signature_label_zh(library: ContentLibrary, item: ItemDef, affix: AffixDef) -> str | None:
    """類型牌的字（「招牌・新動作」「獨特效果・改寫規則」）；不是招牌 ``None``。"""
    kind = signature_kind(affix)
    if kind is None:
        return None
    head = "獨特效果" if _unique(library, item, affix) else "招牌"
    return f"{head}・{SIGNATURE_KIND_ZH[kind]}"


def signature_name_zh(library: ContentLibrary, affix: AffixDef) -> str | None:
    """招牌框的名字：授予技能的詞條（新動作、行為改寫等）是那一招的名字；其他 ``None``。"""
    if not isinstance(affix, ActionAffix):
        return None
    skill = library.skills.get(affix.skill)
    return None if skill is None else skill.name_zh


def _offs(library: ContentLibrary, gear: GearState) -> dict[tuple[str, str], str]:
    found: dict[tuple[str, str], str] = {}
    for a in gear.affixes:
        text = limit_off_zh(library.ruleset, gear, a)
        if text is not None:
            found.setdefault((a.slot, a.affix.id), text)
    return found


def worn_off(library: ContentLibrary, run: RunState) -> dict[tuple[str, str], str]:
    """穿戴中、被名額標灰的詞條：（欄位, 詞條 ID）→ 原因（長版）。不可能超過名額時不算。"""
    if not may_overflow(library, run_loadout(library, run)):
        return {}
    return _offs(library, limited_gear(library, run))


def candidate_off(
    library: ContentLibrary, run: RunState, item: ItemDef, slot: str, *, cross_class: bool = False
) -> dict[str, str]:
    """把 ``item`` 換進 ``slot`` 之後，它身上被名額標灰的詞條：詞條 ID → 原因（長版）。換上時照
    「保留原本生效的」寫勾選（:func:`~trpg.roguelite.gear.keep_active_chosen`），所以是新的這件被標灰。
    換不上時為空。"""
    if not any(signature_kind(a) for a in _affixes(library, item)):
        return {}
    try:
        after = equip(library, run, item, slot, cross_class=cross_class)
    except ChoiceError:  # 換不上的候選卡片照樣列（gear_candidate 另外寫原因）
        return {}
    return {i: text for (s, i), text in worn_off(library, after).items() if s == slot}


def _affixes(library: ContentLibrary, item: ItemDef) -> list[AffixDef]:
    return [library.affixes[r.affix] for r in item.affixes if r.affix in library.affixes]


def _row_off(library: ContentLibrary, gear: GearState, entry: GearAffix) -> str | None:
    """角色面板一列的灰字：招牌名額用短版，改寫規則照 8.27，其他沒生效的寫重複。"""
    if entry.active:
        return None
    if entry.limited_by == "signature":
        return SIGNATURE_SHORT_ZH.format(n=library.ruleset.equipment.caps.signature_active)
    limited = limit_off_zh(library.ruleset, gear, entry)
    if limited is not None:
        return limited
    winner = next((g for g in gear.affixes if g.affix.id == entry.affix.id and g.rank == 0), None)
    slot = "其他裝備" if winner is None or winner is entry else SLOT_ZH[winner.slot]
    return _DUPLICATE_ZH.format(slot=slot)


def signature_panel(
    library: ContentLibrary, run: RunState, *, problem: str | None = None
) -> SignaturePanelOut | None:
    """角色面板的「招牌效果」一節；身上沒有招牌也沒有改寫規則時 ``None``。``problem``：現在不能改
    勾選的原因（大世界不在城鎮或營火）。"""
    loadout = run_loadout(library, run)
    worn = [(e, a) for e in loadout.items for a in e.affixes if signature_kind(a.affix)]
    if not worn:
        return None
    gear = limited_gear(library, run)
    free = whole_no_effect(library.ruleset, gear, run.hero.race, library.weapons[run.hero.weapon])
    index: dict[tuple[str, str], int] = {}
    for i, g in enumerate(gear.affixes):
        index.setdefault((g.slot, g.affix.id), i)
    caps = library.ruleset.equipment.caps
    rows: list[SignatureRowOut] = []
    counted_alive = 0
    rules_alive: set[str] = set()
    for equipped, rolled in worn:
        affix = rolled.affix
        at = index.get((equipped.slot, affix.id))
        if at is None:
            continue
        entry = gear.affixes[at]
        kind = signature_kind(affix) or "rule"
        counted = affix.signature is not None
        if entry.active and counted and at not in free:
            counted_alive += 1
        if entry.active and affix.category == "rule":
            rules_alive.add(affix.id)
        item = equipped.item
        rows.append(
            SignatureRowOut(
                key=chosen_key(equipped.slot, affix.id),
                slot=equipped.slot,
                slot_zh=SLOT_ZH[equipped.slot],
                item_name_zh=item.name_zh,
                rarity=item.rarity or ("legendary" if item.legendary else "common"),
                affix_id=affix.id,
                kind=kind,
                kind_zh=SIGNATURE_KIND_ZH[kind],
                name_zh=signature_name_zh(library, affix) or affix_text(affix, rolled.value),
                text_zh=affix_text(affix, rolled.value),
                counted=counted,
                rule=affix.category == "rule",
                active=entry.active,
                off_zh=_row_off(library, gear, entry),
            )
        )
    has_rule = any(r.rule for r in rows)
    count = f"生效 {counted_alive}／{caps.signature_active}"
    if has_rule:
        count += f"・改寫規則 {len(rules_alive)}／{caps.rule_affixes}"
    return SignaturePanelOut(
        rows=tuple(rows),
        active=counted_alive,
        cap=caps.signature_active,
        rules=len(rules_alive),
        rule_cap=caps.rule_affixes,
        has_rule=has_rule,
        count_zh=count,
        full_zh=SIGNATURE_FULL_ZH.format(n=caps.signature_active),
        chosen=run.gear_chosen,
        problem_zh=problem,
    )
