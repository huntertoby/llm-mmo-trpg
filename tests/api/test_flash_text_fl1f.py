"""FL-1f：玩法 PM 填完的大標、下固定區句子、‰ 強度的白話（FL-1b 報告附錄 A 的填答）。

鎖幾條代表性的字；完整的字在 ``content/flash_templates.yaml``。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library as _load_library
from trpg.api.flash_changes import flash_changes, magnitude_zh, status_magnitude_suffix
from trpg.api.flash_text import option_headline, option_say
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.whiteboard import compose_whiteboard

LIB = _load_library()
KINDLE = compose_whiteboard(75, recipe_id="kindle", weapon_class="melee", tier=1, library=LIB)


def _headline(
    template: str,
    category: str,
    *,
    source: str = "minor",
    keyword: str | None = None,
    element: str | None = None,
) -> str | None:
    variation = Variation(
        source=source,  # type: ignore[arg-type]
        template=template,
        category=category,
        keyword=keyword,
        element=element,
    )
    return option_headline(LIB, variation, KINDLE, ())


def test_every_template_has_a_headline() -> None:
    """86 個模板都有大標；support_keyword 只有兩個關鍵字，寫在「模板 × 關鍵字」表。"""
    flash = LIB.flash
    templates = [*flash.minor, *flash.major, *flash.extra_major, *flash.transforms]
    assert len(templates) == 86
    missing = [t.id for t in templates if t.headline_zh is None]
    assert missing == ["support_keyword"]
    for keyword in ("wet", "concealed"):
        assert flash.headline("support_keyword", keyword) is not None


@pytest.mark.parametrize(
    ("template", "category", "source", "keyword", "element", "want"),
    [
        ("area_plus", "area", "minor", None, None, "範圍變大 1 格"),
        ("support_area_wide", "support", "minor", None, None, "光環範圍變大 2 格"),
        ("stance_cost_light", "cost", "minor", None, None, "維持費少 1，姿態效果弱一點"),
        ("multi_hit", "combo", "minor", None, None, "同一個敵人多挨一段"),
        ("element_second", "element", "minor", None, "ice", "多帶一段冰霜傷害"),
        ("keyword_imbue", "element", "minor", "ignite", None, "打中時還會點燃敵人"),
        # 隱蔽的製造是在打中的格子造煙霧，不是自己躲：用模板的通用句（填答第五節「對照引擎的規則」）
        ("keyword_imbue", "element", "minor", "concealed", None, "打中時還會造成隱蔽"),
        # 帶電的加碼條件是「這回合放過雷電技能」，不是敵人帶電：用模板的通用句
        ("keyword_exploit", "element", "minor", "charged", None, "敵人身上有帶電時，這招多傷一截"),
        ("keyword_exploit", "element", "minor", "wet", None, "敵人站在水上時，這招多傷一截"),
        ("support_keyword", "support", "minor", "wet", None, "施放時目標腳下積水"),
        ("major_intensify", "deepen", "major", "ignite", None, "專精點燃：造成的點燃更持久"),
        ("major_bridge_imbue", "bridge", "major", "wet", None, "打中的格子還會積水"),
        ("shield_wet", "bridge", "major", "wet", None, "護盾破掉時，腳下積一灘水"),
        ("summon_bridge", "bridge", "major", "frozen", None, "召喚物的攻擊帶上冰凍"),
        ("to_stance", "transform", "transform", None, None, "變成姿態：進入後一直生效，直到你取消"),
    ],
)
def test_headlines(
    template: str,
    category: str,
    source: str,
    keyword: str | None,
    element: str | None,
    want: str,
) -> None:
    got = _headline(template, category, source=source, keyword=keyword, element=element)
    assert got == want


def test_say_lines_from_the_answer_sheet() -> None:
    """填答第七節：前 → 後看不出怎麼運作的模板才寫 say_zh。"""
    cases = {
        ("minor", "kill_refund", "extend"): "這招打倒敵人時，馬上拿回 1 AP，可以接著行動。",
        ("major", "major_battle_variant", "deepen"): (
            "站在特定地形上施放時，這招自動換成另一種打法。"
        ),
        ("major", "shield_charged", "bridge"): "護盾被打破時，電一下打破它的敵人。",
        ("transform", "to_trap", "transform"): ("這招變成陷阱：先布在地上，敵人踩上去時才發動。"),
    }
    for (source, template, category), want in cases.items():
        variation = Variation(source=source, template=template, category=category)  # type: ignore[arg-type]
        assert option_say(LIB, variation, KINDLE, ()) == want, template


def test_magnitude_wording() -> None:
    """填答第六節：寫「倍」；前值 1000‰ 寫「原本」；小數最多兩位。"""
    assert magnitude_zh("1000‰", before=True) == "原本"
    assert magnitude_zh("1250‰", before=False) == "1.25 倍"
    assert magnitude_zh("1200‰", before=True) == "1.2 倍"
    assert magnitude_zh("1500‰", before=False) == "1.5 倍"
    assert magnitude_zh("800‰", before=False) == "0.8 倍"
    assert magnitude_zh("2000‰", before=False) == "2 倍"
    assert magnitude_zh("1025‰", before=False) == "1.03 倍"


def test_magnitude_names_follow_what_the_status_changes() -> None:
    """欄位名照狀態實際被強度放大的欄位分類（資料為準）。"""
    statuses = LIB.ruleset.statuses.by_id()
    expect = {
        "burning": "傷害",
        "regenerating": "回復量",
        "weaken": "幅度",
        "vulnerable": "幅度",
        "guarded": "減傷",
        "stoneskin": "減傷",
        "empowered": "加成",
        "hasted": "加成",
        "mist_return": "回復量",  # 填答估「其他」；資料是每回合回復
        "stance_guard": "減傷",  # 姿態只放大有利的一邊（移動變慢不算）
        "stance_earth_1": "強度",  # 同時少受物理傷害又加元素傷害
    }
    for status_id, suffix in expect.items():
        assert status_magnitude_suffix(statuses[status_id]) == suffix, status_id


def test_burning_magnitude_row_reads_plain() -> None:
    """燃燒傷害 原本 → 1.25 倍（填答第六節的例子）。"""
    effect = KINDLE.effects[0].model_copy(update={"magnitude_permille": 1250})
    after = KINDLE.model_copy(update={"effects": (effect,)})
    rows = [r for r in flash_changes(LIB, KINDLE, after) if r.field.endswith("magnitude_permille")]
    assert [(r.name_zh, r.before_zh, r.after_zh) for r in rows] == [("燃燒傷害", "原本", "1.25 倍")]
