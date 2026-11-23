"""QF-6（佇列 (i)）：副手與元素的中文名改讀資料（原本 ``_OFFHAND_ZH``、``_ELEMENT_ZH`` 寫死），
顯示文字不變。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.api.tuning.objects import _with_element, element_names
from trpg.content.equipment import AffixRoll, item_problems

# 拿掉前寫死的兩張表（對照用：資料讀出來的名字要和這裡一字不差）
OLD_OFFHAND_ZH = {"tower_shield": "塔盾", "round_shield": "圓盾", "tome": "法書", "orb": "法器珠"}
OLD_ELEMENT_ZH = {
    "physical": "物理",
    "fire": "火焰",
    "ice": "冰霜",
    "lightning": "雷電",
    "poison": "毒素",
    "wind": "風",
    "earth": "大地",
    "holy": "神聖",
    "shadow": "暗影",
    "chosen": "所選元素",
}


def test_data_names_match_the_old_tables() -> None:
    lib = library()
    assert {o: d.name_zh for o, d in lib.offhands.items()} == OLD_OFFHAND_ZH
    names = element_names(lib.root)
    assert names == {k: v for k, v in OLD_ELEMENT_ZH.items() if k != "chosen"}


def test_element_label_reads_data_and_keeps_chosen() -> None:
    names = element_names(library().root)
    for key, zh in OLD_ELEMENT_ZH.items():
        data = {"forms": [{"element": key}]}
        label = _with_element("受到{element}傷害", data, ("forms", 0, "x"), names)
        assert label == f"受到{zh}傷害"


def test_offhand_restricted_affix_message_uses_data_names() -> None:
    lib = library()
    affix = next(a for _, a in sorted(lib.affixes.items()) if a.offhands and "offhand" in a.slots)
    item = next(
        i
        for _, i in sorted(lib.items.items())
        if i.slot_type == "offhand" and i.offhand is not None and i.offhand not in affix.offhands
    )
    rolled = item.model_copy(update={"affixes": (AffixRoll(affix=affix.id),)})
    problems = item_problems(rolled, lib.affixes, lib.weapons, lib.ruleset.equipment, lib.offhands)
    names = "、".join(OLD_OFFHAND_ZH[o] for o in affix.offhands)
    assert any(f"只能出現在{names}上" in p for p in problems), problems
