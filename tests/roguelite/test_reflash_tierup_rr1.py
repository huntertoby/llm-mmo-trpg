"""RR-1：升階後照新階級套不上的那一筆，照存檔裡的定義保留（06 6.34.9「重推套不上的那一筆」）。

重現案例（FL-1g 報告第 2 節）：第一個開發起始包、種子 2 的一輪打到營火。「灼燃・燃燒爆」的第 2 次
（``keyword_imbue`` 潮濕）是角色 1 階時選的，升到 2 階後照新階級套不上；以前重閃第 1、3 格整份歷程
重推失敗，一個選項都出不了。現在升階時把那一筆升階前的定義記進 ``FlashRecord.kept``，之後重推到
這一筆就照它保留，所以重閃第 3 格出得了題；真的出不了題的格子（第 1 格：被換掉的蓄力強度下限太
高）照 6.34「費用方向」第 7 點標灰、不扣點。
"""

from __future__ import annotations

import pytest

from tests.world.helpers import make_world
from trpg.api.run_presenter import _flash_out
from trpg.content.library import ContentLibrary
from trpg.roguelite import auto_play
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.flashes import base_def, flash_request, open_flash, pick_flash
from trpg.roguelite.retier import sync_skill_tier
from trpg.roguelite.start import new_dev_run
from trpg.roguelite.state import FlashChoice, FlashPickChoice, RunState
from trpg.skillgen.flash_derive import (
    FlashStepError,
    derive_chain,
    derive_skill,
    flashed_identity,
    keep_failed,
)
from trpg.skillgen.flash_offer import NO_REFLASH_OPTIONS_ZH, has_options
from trpg.skillgen.flash_state import with_reflash
from trpg.world import growth
from trpg.world.growth import as_run, from_run, sync_tier
from trpg.world.step import new_character

SEED = 2
IMBUE_NTH = 2


@pytest.fixture(scope="module")
def tier_up(library: ContentLibrary) -> tuple[RunState, RunState, RunState]:
    """（升階前一刻、升階後一刻、打到營火）的三個一輪狀態。"""
    pack = library.dev_starters.packs[0].id
    pairs: list[tuple[RunState, RunState]] = []

    def watch(before: RunState, after: RunState) -> None:
        if not pairs and before.skill_tier != after.skill_tier:
            pairs.append((before, after))

    run = new_dev_run(library, pack, SEED)
    run, _ = auto_play(library, run, stop=lambda r, _b: r.node.kind == "campfire", on_node=watch)
    assert pairs, "這一輪到營火前應該升過階"
    before, after = pairs[0]
    return before, after, run


def _imbued(run: RunState) -> str:
    """歷程第 2 次是 keyword_imbue 的那一招（重現案例的「灼燃・燃燒爆」）。"""
    found = [
        skill_id
        for skill_id, state in sorted(run.flash.items())
        if (r := state.record(IMBUE_NTH)) is not None and r.variation.template == "keyword_imbue"
    ]
    assert len(found) == 1
    return found[0]


def test_tier_up_keeps_the_saved_definition(
    library: ContentLibrary, tier_up: tuple[RunState, RunState, RunState]
) -> None:
    before, after, _ = tier_up
    skill_id = _imbued(after)
    state = after.flash[skill_id]
    old = before.flash[skill_id]
    base = base_def(library, after, skill_id)
    # 升階前的歷程照舊（1 階）推得出來，照新階級（2 階）第 2 筆套不上
    saved = derive_chain(library, base, old, SEED, before.skill_tier)
    with pytest.raises(FlashStepError) as exc:
        derive_chain(library, base, old, SEED, after.skill_tier)
    assert exc.value.nth == IMBUE_NTH
    # 那一筆記下升階前的定義；其他筆沒有
    kept = {r.nth: r.kept for r in state.records}
    assert kept[IMBUE_NTH] == saved[IMBUE_NTH - 1]
    assert all(v is None for n, v in kept.items() if n != IMBUE_NTH)
    # 技能 ID 不變（保留的定義不進雜湊），卡片就是照新階級重推、套不上那一筆照保留的結果
    assert flashed_identity(library, base, state) == flashed_identity(library, base, old)
    assert skill_id == flashed_identity(library, base, old)[0]
    derived = derive_skill(library, base, state, SEED, after.skill_tier)
    assert derived.id == skill_id
    assert derived.tier == after.skill_tier


def test_reflash_after_tier_up_has_options_again(
    library: ContentLibrary, tier_up: tuple[RunState, RunState, RunState]
) -> None:
    *_, run = tier_up
    run = run.model_copy(update={"insight": 8})
    skill_id = _imbued(run)
    major = library.flash.rules.major_flash
    # 重現案例：重閃第 3 格（大變化）出得了題，入口的轉型提示也回來了
    request = flash_request(library, run, skill_id, slot=major)
    assert has_options(library, request)
    out = _flash_out(library, run, skill_id)
    assert out.reflash_transform_hint
    slots = {s.slot: s for s in out.reflash_slots}
    assert slots[major].available and slots[major].problem_zh is None
    opened = open_flash(library, run, FlashChoice(skill=skill_id, slot=major))
    assert opened.pending_flash is not None and opened.pending_flash.offer.options
    assert opened.insight < run.insight
    picked = pick_flash(library, opened, FlashPickChoice(pick=0))
    assert picked.pending_flash is None


def test_every_reflash_slot_marks_availability_truthfully(
    library: ContentLibrary, tier_up: tuple[RunState, RunState, RunState]
) -> None:
    """每一格的 ``available`` 和實際按下去出不出得了題一致；出不了題的不扣點、灰字是固定句。"""
    *_, run = tier_up
    run = run.model_copy(update={"insight": 8})
    checked = 0
    for skill_id in sorted(run.flash):
        for slot in _flash_out(library, run, skill_id).reflash_slots:
            try:
                open_flash(library, run, FlashChoice(skill=skill_id, slot=slot.slot))
                opens = True
            except ChoiceError:
                opens = False
            assert slot.available == opens
            assert slot.problem_zh == (None if opens else NO_REFLASH_OPTIONS_ZH)
            checked += 1
    assert checked >= 3


def test_reflash_clears_kept_after_the_replaced_slot(
    tier_up: tuple[RunState, RunState, RunState],
) -> None:
    """換掉更前面的一筆時，後面保留的定義含舊的那一筆，要清掉；換掉後面的不動前面的。"""
    *_, run = tier_up
    state = run.flash[_imbued(run)]
    first, second, third = state.records
    assert second.kept is not None
    earlier = with_reflash(state, first.nth, first.variation)
    assert earlier.records[1].kept is None
    later = with_reflash(state, third.nth, third.variation)
    assert later.records[1].kept == second.kept


def test_keep_failed_is_a_no_op_when_everything_fits(
    library: ContentLibrary, tier_up: tuple[RunState, RunState, RunState]
) -> None:
    *_, run = tier_up
    for skill_id, state in sorted(run.flash.items()):
        base = base_def(library, run, skill_id)
        for tier in (3, 4):
            # 3、4 階整條都套得上（FL-1g 報告），不記任何東西
            records = tuple(r.model_copy(update={"kept": None}) for r in state.records)
            stripped = state.model_copy(update={"records": records})
            assert keep_failed(library, base, stripped, SEED, old_tier=2, tier=tier) == stripped


def test_sync_is_idempotent_and_replays_the_same(
    library: ContentLibrary, tier_up: tuple[RunState, RunState, RunState]
) -> None:
    before, after, _ = tier_up
    leveled = before.model_copy(update={"level": after.level})
    assert sync_skill_tier(library, leveled).flash == after.flash
    assert sync_skill_tier(library, after) == after


def test_world_tier_up_keeps_the_saved_definition(
    library: ContentLibrary,
    tier_up: tuple[RunState, RunState, RunState],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """大世界（城鎮的重閃）走同一條升階重配（``sync_tier`` → ``sync_skill_tier``）。"""
    before, after, _ = tier_up
    monkeypatch.setattr(growth, "skill_seed", lambda _world, _char: SEED)
    char = new_character(library, "rr1", before.hero, region="cloud_ridge")
    level = next(n for n in range(1, 30) if growth.hero_tier(library, n) == after.skill_tier)
    char = from_run(char, before.model_copy(update={"level": level}))
    synced, events = sync_tier(library, make_world(), char)
    assert events
    assert synced.flash == after.flash
    skill_id = _imbued(after)
    major = library.flash.rules.major_flash
    run = as_run(synced, seed=SEED)
    assert synced.flash[skill_id].record(IMBUE_NTH).kept is not None  # type: ignore[union-attr]
    # 升階時第 3 次還沒閃；照保留的定義，下一次閃現從那一筆接著推
    assert major not in {r.nth for r in synced.flash[skill_id].records}
    assert has_options(library, flash_request(library, run, skill_id))
