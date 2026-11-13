"""FL-1g（FL-1b 驗收可修 6）：營火「可以重閃第 3 格轉型」只在重閃第 3 格真的出得了題時才給。

種子 2 的開發一輪（第一個開發起始包）打到營火時，「灼燃・燃燒爆」閃滿 3 次（第 3 次是大變化、不是
轉型），但第 2 次的變化（``keyword_imbue``）是角色 1 階時選的，升到 2 階後歷程重推不了（3W-R1；
重閃沒有退路），所以重閃任何一格都是「沒有合法的變化」。以前入口照樣寫「可以重閃第 3 格轉型」。
"""

from __future__ import annotations

from trpg.api.run_presenter import _flash_out
from trpg.content.library import ContentLibrary
from trpg.roguelite import auto_play
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.flashes import open_flash
from trpg.roguelite.start import new_dev_run
from trpg.roguelite.state import FlashChoice


def test_transform_hint_only_when_the_slot_has_options(library: ContentLibrary) -> None:
    pack = library.dev_starters.packs[0].id
    run = new_dev_run(library, pack, 2)
    run, _ = auto_play(library, run, stop=lambda r, _b: r.node.kind == "campfire")
    run = run.model_copy(update={"insight": 8})
    major = library.flash.rules.major_flash
    checked = 0
    for skill_id, state in sorted(run.flash.items()):
        record = state.record(major)
        if state.complete or record is None or record.variation.source == "transform":
            continue
        out = _flash_out(library, run, skill_id)
        hinted = [s.slot for s in out.reflash_slots if s.transform_hint]
        try:
            open_flash(library, run, FlashChoice(skill=skill_id, slot=major))
            opens = True
        except ChoiceError:
            opens = False
        assert out.reflash_transform_hint == opens
        assert hinted == ([major] if opens else [])
        checked += 1
    assert checked >= 1
