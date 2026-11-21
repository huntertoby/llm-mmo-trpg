"""HC-6b：API 說明文字裡的規則數字改從資料組字；目前的值組出來要和改前的字逐字相同。"""

from __future__ import annotations

from trpg.api import world_economy_view, world_growth_view
from trpg.api.tuning import objects
from trpg.api.tuning.objects import ai_notes, retier_note_zh, table_notes
from trpg.api.tuning.skills import _BORROW_SAME_ZH, GROUP_PRESETS
from trpg.content.library import ContentLibrary
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import load_tuning_fields
from trpg.world.actions import OathBrokenEvent


def test_tuning_defaults_follow_schema_defaults() -> None:
    defaults = objects._DEFAULTS_ZH
    assert defaults["armor_bonus"] == "沒寫＝0"
    assert defaults["level"] == "沒寫＝1"
    assert defaults["cost.stamina"] == "沒寫＝0"
    assert defaults["cost.mana"] == "沒寫＝0"
    assert defaults["stance_upkeep"] == "沒寫＝0"


def test_retier_note_reads_the_budget_window(content_library: ContentLibrary) -> None:
    budget = content_library.budget
    assert retier_note_zh(budget) == (
        "這招在 2 階以上會依預算比例重算（夾在 70～100%），超出的部分只在 1 階有效"
    )
    moved = budget.model_copy(update={"min_ratio_permille": 650, "max_ratio_permille": 1000})
    assert "（夾在 65～100%）" in retier_note_zh(moved)


def test_table_notes_count_the_whitelist() -> None:
    table = load_tuning_fields(bundled_content_dir())
    ai = table.target("ai")
    triggers = table.target("skill_triggers")
    assert ai is not None and triggers is not None
    assert ai_notes(ai)[1] == (
        "目前開放頭目部位（parts）的 11 個值（含巨型頭目的護面與站位，GB-3）、「無聲留背」"
        "（facing.silent_behind，BS-2）與殼縫蟲群的「追離頭目遠的人」（GB-3），全部是占位；"
        "其他行為模式權重還沒開。"
    )
    assert len(ai_notes(ai)) == len(objects.AI_NOTES_ZH) + 1
    assert table_notes("skill_triggers", triggers)[-1] == (
        "只開放係數（SK-5）；「每命中 n 次」依 n 查的係數 HC-B 起也開了（n＝2、3 各一格）。"
    )


def test_group_preset_labels_follow_their_filters() -> None:
    labels = [p.label_zh for p in GROUP_PRESETS[:4]]
    assert labels == [
        "1 階遠程武器技",
        "1 階近戰武器技",
        "1 AP 箭類（1 階、遠程、AP 1、單體傷害）",
        "2 AP 條件型（1 階武器技，帶條件段）",
    ]
    assert _BORROW_SAME_ZH == "預支技能的 AP 固定是 0，不能改"


def test_oath_slot_and_penalty_rounds(content_library: ContentLibrary) -> None:
    assert world_growth_view.slot_zh(content_library) == (
        "誓約佔 1 格被動欄位（立誓後被動技能最多裝 2 招）"
    )
    table = content_library.world_oaths
    assert table is not None
    template = table.templates[0]
    line = world_growth_view._oath_line(
        content_library, OathBrokenEvent(template=template.id, check="x", at_end=True), {}
    )
    assert line == (
        f"戰鬥結束：沒有守住誓約「{template.name_zh}」，"
        "破誓 2 回合帶到下一場開場（下一場的誓約加成照常）。"
    )


def test_pouch_item_line_reads_the_item_skill(content_library: ContentLibrary) -> None:
    items = [i for i in content_library.world_economy.items.values() if i.skill is not None]
    assert items
    for item in items:
        assert world_economy_view._battle_zh(item) == (
            "放進腰包：戰鬥中花 1 AP 使用，每個用一次（不佔技能欄位）"
        )
