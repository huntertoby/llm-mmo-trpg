"""主題合併（R2）。

原 ``test_retier_3w9.py``：

Phase 3W-9：一輪裡的角色升階重算、手寫技能換 ID、候選照角色階級、舊存檔（``/10``）轉換。

原 ``test_truth_3wr1.py``：

Phase 3W-R1：升階後同一招只有一個真相來源、歷程重推失敗的退路、重配快取掛在內容庫上。

夾具 ``fixtures/flash_history_3wr1.json``：``build_fire`` 種子 6，AI 代打到第一個營火（等級 3、角色
階級 2；``skill_fire_bolt`` 閃過 3 次：第 1 次 ``keyword_exploit``、第 2 次 ``range_plus``、第 3 次
大變化）。重產：``uv run python -m tests.roguelite.test_retier``（:func:`_generate`）。
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from functools import cache
from pathlib import Path

import pytest

from tests.roguelite.helpers import library
from trpg.api.run_presenter import flash_preview
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite import (
    SAVE_FORMAT,
    RunSave,
    RunState,
    apply_choice,
    auto_play,
    dumps_save,
    loads_save,
    new_dev_run,
    new_keyword_run,
    new_run,
    next_node,
    upgrade_save,
)
from trpg.roguelite.battle import SavedBattle
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.flashes import (
    base_def,
    flash_request,
    inherit_problem,
    owned_skills,
    state_of,
)
from trpg.roguelite.offers import at_run_tier, candidate_request, library_base, skill_defs
from trpg.roguelite.retier import run_tier, sync_skill_tier
from trpg.roguelite.state import (
    CampfireNode,
    FlashChoice,
    FlashPickChoice,
    InheritChoice,
    LevelUpNode,
)
from trpg.skillgen import skill_tier
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_derive import (
    FlashHistoryError,
    FlashStepError,
    derive_chain,
    derive_skill,
    history_error,
)
from trpg.skillgen.flash_offer import _builder, history_problem, skill_before
from trpg.skillgen.flash_state import acquire
from trpg.skillgen.skill_tier import character_tier, retier
from trpg.skillgen.validate import validate_skill

# --- 原 test_retier_3w9.py ---

LIB = library()
HANDWRITTEN = "skill_fire_bolt"


def _run() -> RunState:
    return new_keyword_run(LIB, "fire_staff", ("ignite", "charged"), 3)


def _owned(run: RunState) -> list[SkillDef]:
    return skill_defs(LIB, run, (*run.hero.skills, *run.bench))


def _level_to(run: RunState, level: int) -> RunState:
    """升到 ``level`` 的前一級，留一次升級給 ``next_node``。"""
    return run.model_copy(update={"level": level - 1, "levels_pending": 1})


def test_a_new_run_starts_at_character_tier_one() -> None:
    run = _run()
    assert run.skill_tier == character_tier(LIB, 1) == 1
    assert all(s.tier == 1 for s in _owned(run))


def test_crossing_a_tier_retunes_every_skill_between_battles() -> None:
    run = _run()
    second = next(lv for lv in range(2, 10) if character_tier(LIB, lv) == 2)
    before = {s.id: budget_power(s, LIB) for s in _owned(run)}
    after = next_node(LIB, _level_to(run, second))
    assert isinstance(after.node, LevelUpNode)
    assert after.skill_tier == 2 and run_tier(LIB, after) == 2
    assert after.node.offer.tier == 2
    for skill in _owned(after):
        assert skill.tier == 2
        assert budget_power(skill, LIB) >= before[skill.id]  # 不低於升階前
        assert validate_skill(skill, LIB) == []
    for candidate in after.node.offer.candidates:
        assert candidate.tier == 2


def test_a_level_up_without_a_tier_change_keeps_the_skills() -> None:
    run = _run()
    after = next_node(LIB, run.model_copy(update={"levels_pending": 1}))
    if character_tier(LIB, 2) == 1:
        assert after.generated_skills == run.generated_skills
        assert after.hero.skills == run.hero.skills


def test_handwritten_skills_become_tier_copies_and_keep_their_flash_state() -> None:
    run = _run()
    hero = run.hero.model_copy(update={"skills": (*run.hero.skills, HANDWRITTEN)})
    run = run.model_copy(
        update={
            "hero": hero,
            "flash": {HANDWRITTEN: acquire(HANDWRITTEN).model_copy(update={"used": True})},
            "level": 3,
            "skill_tier": 1,
        }
    )
    synced = sync_skill_tier(LIB, run)
    copy_id = f"{HANDWRITTEN}_t{character_tier(LIB, 3)}"
    assert copy_id in synced.hero.skills and HANDWRITTEN not in synced.hero.skills
    assert set(synced.flash) == {copy_id} and synced.flash[copy_id].used
    copy = synced.generated(copy_id)
    assert copy is not None and copy.tier == character_tier(LIB, 3)
    assert library_base(LIB, copy_id) == HANDWRITTEN
    assert HANDWRITTEN in candidate_request(LIB, synced).exclude  # 候選不再出原本那招
    assert budget_power(copy, LIB) >= budget_power(LIB.skills[HANDWRITTEN], LIB)
    again = sync_skill_tier(LIB, synced.model_copy(update={"level": 5, "skill_tier": 2}))
    assert f"{HANDWRITTEN}_t3" in again.hero.skills  # 再升階換成新階級的後綴


def test_pool_candidates_are_retuned_to_the_character_tier() -> None:
    """手寫池退回的候選（原本的階級）照角色階級重配，卡片上的數字就是拿到後的數字（3W-4 #8）。"""
    skill = LIB.skills[HANDWRITTEN]
    moved = at_run_tier(LIB, skill, 3)
    assert moved.id == f"{HANDWRITTEN}_t3" and moved.tier == 3
    assert validate_skill(moved, LIB) == []
    assert at_run_tier(LIB, skill, skill.tier) is skill


def _old_text(run: RunState, battle: SavedBattle | None = None) -> str:
    raw = json.loads(dumps_save(RunSave(run_id="old", run=run, battle=battle)))
    raw["format"] = "trpg-run/10"
    del raw["run"]["skill_tier"]
    return json.dumps(raw)


def test_old_saves_are_upgraded_between_battles() -> None:
    run = new_dev_run(LIB, next(iter(LIB.dev_starters.by_id())), 2)
    old = run.model_copy(update={"level": 5})
    loaded = loads_save(_old_text(old))
    assert loaded.format == SAVE_FORMAT == "trpg-run/13"
    assert loaded.run.skill_tier is None
    upgraded = upgrade_save(LIB, loaded)
    tier = character_tier(LIB, 5)
    assert upgraded.run.skill_tier == tier
    assert all(s.tier == tier for s in _owned(upgraded.run))
    assert upgrade_save(LIB, upgraded) == upgraded  # 已是新格式：不變
    back = loads_save(dumps_save(upgraded))
    assert back.run == upgraded.run


def test_old_saves_in_battle_wait_for_the_next_node() -> None:
    run = _run().model_copy(update={"level": 5})
    battle = SavedBattle(index=1, seed=run.plan_of(1).seed, steps=[], orders=[])
    loaded = loads_save(_old_text(run, battle))
    assert upgrade_save(LIB, loaded) == loaded  # 戰鬥中：技能不動（重播用存檔當時的技能）
    synced = sync_skill_tier(LIB, loaded.run)
    assert synced.skill_tier == character_tier(LIB, 5)


# --- 原 test_truth_3wr1.py ---

FIXTURE = Path(__file__).parent / "fixtures" / "flash_history_3wr1.json"
FLASHED = "skill_fire_bolt"
STALE = "range_plus"
"""夾具裡那一招第 2 次的小變化；「內容改版」用拿掉它的內容庫模擬。"""


@cache
def _saved() -> RunState:
    return loads_save(FIXTURE.read_text(encoding="utf-8")).run


def _flashed(run: RunState) -> str:
    return next(s for s in owned_skills(run) if state_of(run, s).base_id == FLASHED)


def _card(run: RunState, skill_id: str) -> object:
    return skill_defs(library(), run, [skill_id])[0]


def _tier_up(lib: ContentLibrary, run: RunState) -> RunState:
    level = next(lv for lv in range(run.level, 20) if character_tier(lib, lv) > run.skill_tier)  # type: ignore[operator]
    return sync_skill_tier(lib, run.model_copy(update={"level": level}))


@cache
def _stale_library() -> ContentLibrary:
    lib = library()
    minor = tuple(t for t in lib.flash.minor if t.id != STALE)
    return replace(lib, flash=lib.flash.model_copy(update={"minor": minor}))


def test_the_fixture_has_a_skill_flashed_with_the_stale_template() -> None:
    run = _saved()
    state = state_of(run, _flashed(run))
    assert [r.variation.template for r in state.records][1] == STALE
    assert run.skill_tier == character_tier(library(), run.level) == 2


# ---------------------------------------------------------------------------
# ① 升階後同一招只有一個真相來源
# ---------------------------------------------------------------------------


def test_a_tier_up_rederives_flashed_skills_from_their_history() -> None:
    lib = library()
    run = _saved()
    skill_id = _flashed(run)
    before = {s.id: budget_power(s, lib) for s in skill_defs(lib, run, owned_skills(run))}
    up = _tier_up(lib, run)
    tier = up.skill_tier
    assert tier == 3
    stored = up.generated(skill_id)
    expected = derive_skill(lib, base_def(lib, up, skill_id), state_of(up, skill_id), up.seed, tier)
    assert stored == expected  # 卡片的定義 ＝ 從原技能照新階級重推整條歷程
    assert stored is not None and stored.tier == tier and stored.id == skill_id  # ID 由歷程決定
    # 3W-9b：升階後預算分數不低於升階前
    for skill in skill_defs(lib, up, owned_skills(up)):
        stem = skill.id.removesuffix(f"_t{tier}")
        old = before.get(skill.id, before.get(stem, before.get(f"{stem}_t2")))
        assert old is not None, skill.id
        assert budget_power(skill, lib) >= old


def test_unflashed_skills_still_use_retier() -> None:
    lib = library()
    run = _saved()
    plain = next(
        s
        for s in run.hero.skills
        if not state_of(run, s).records and run.generated(s) is not None and "_t" not in s
    )
    up = _tier_up(lib, run)
    assert up.generated(plain) == retier(lib, run.generated(plain), up.skill_tier)  # type: ignore[arg-type]


def test_a_flash_right_after_a_tier_up_starts_from_the_card() -> None:
    lib = library()
    up = _tier_up(lib, _saved())
    skill_id = _flashed(up)
    card = up.generated(skill_id)
    # 閃現：「套用前」＝ 卡片
    assert skill_before(lib, flash_request(lib, up, skill_id)) == card
    # 重閃最後一筆：強度下限 ＝ 卡片的預算分數（被換掉的就是卡片現在的樣子）
    last = state_of(up, skill_id).records[-1].nth
    builder = _builder(lib, flash_request(lib, up, skill_id, slot=last))
    assert builder.broken is None
    assert builder.floor_permille == math.ceil(budget_power(card, lib) * 1000)
    # 重閃第 1 筆：強度下限 ＝ 同一條歷程（照新階級重推）第 1 筆的預算分數
    first = flash_request(lib, up, skill_id, slot=1)
    chain = derive_chain(lib, first.base, first.state, up.seed, up.skill_tier)
    assert _builder(lib, first).floor_permille == math.ceil(budget_power(chain[0], lib) * 1000)


# ---------------------------------------------------------------------------
# ② 歷程重推失敗與「變化不合法」分開
# ---------------------------------------------------------------------------


def test_a_stale_history_is_reported_separately() -> None:
    lib = _stale_library()
    run = _saved()
    skill_id = _flashed(run)
    request = flash_request(lib, run, skill_id)
    found = history_error(lib, request.base, request.state, run.seed, request.tier)
    assert isinstance(found, FlashHistoryError) and isinstance(found.step, FlashStepError)
    assert found.step.nth == 2 and found.step.template == STALE
    problem = history_problem(lib, request)
    assert problem is not None and "第 2 次" in problem and "存檔裡的數值" in problem
    assert history_problem(library(), flash_request(library(), run, skill_id)) is None
    # API：預覽帶出原因
    preview = flash_preview(lib, run, skill_id, None)
    assert preview.history_note_zh == problem


def test_a_stale_history_flashes_from_the_saved_definition() -> None:
    lib = _stale_library()
    run = _saved()
    skill_id = _flashed(run)
    state = state_of(run, skill_id).model_copy(update={"used": True})
    ready = run.model_copy(update={"flash": {**run.flash, skill_id: state}, "insight": 3})
    card = ready.generated(skill_id)
    assert card is not None
    request = flash_request(lib, ready, skill_id)
    assert skill_before(lib, request) == card  # 退路：起點是存檔裡的定義，不是原技能
    opened = apply_choice(lib, ready, FlashChoice(skill=skill_id))
    offer = opened.pending_flash.offer  # type: ignore[union-attr]
    assert offer.options, "重推失敗不能被當成「沒有合法變化」"
    for option in offer.options:
        assert option.skill.id.startswith(f"{FLASHED}_fl_")
        if option.variation.template == "cost_light":
            continue  # FL-1a：輕巧一定要變弱（少付的代價扣回），不受「不低於閃現前」的下限
        assert budget_power(option.skill, lib) >= budget_power(card, lib)  # 強度下限照存檔的定義
    again = apply_choice(lib, ready, FlashChoice(skill=skill_id))
    assert again == opened  # 確定性
    picked = apply_choice(lib, opened, FlashPickChoice(pick=0))
    assert len(state_of(picked, offer.options[0].skill.id).records) == 4


def test_a_stale_history_keeps_the_reflash_floor() -> None:
    lib = _stale_library()
    run = _saved()
    skill_id = _flashed(run)
    card = run.generated(skill_id)
    for slot in (1, 3):
        builder = _builder(lib, flash_request(lib, run, skill_id, slot=slot))
        assert builder.broken is not None
        assert builder.floor_permille == math.ceil(budget_power(card, lib) * 1000) > 0  # type: ignore[arg-type]


def test_a_stale_history_survives_a_tier_up() -> None:
    lib = _stale_library()
    run = _saved()
    skill_id = _flashed(run)
    up = _tier_up(lib, run)
    stored = up.generated(skill_id)
    assert stored is not None and stored.tier == up.skill_tier
    assert stored == retier(lib, run.generated(skill_id), up.skill_tier)  # type: ignore[arg-type]
    # 之後的閃現也以它為起點
    assert skill_before(lib, flash_request(lib, up, skill_id)) == stored


def test_inherit_names_a_stale_variation_instead_of_failing() -> None:
    lib = _stale_library()
    run = _saved()
    source = _flashed(run)
    target = next(s for s in owned_skills(run) if s != source and not state_of(run, s).records)
    problem = inherit_problem(lib, run, target, source, (2,))
    assert problem is not None and "內容版本已經沒有" in problem and STALE in problem
    with pytest.raises(ChoiceError, match="內容版本已經沒有"):
        apply_choice(lib, run, InheritChoice(skill=target, source=source, records=(2,)))


# ---------------------------------------------------------------------------
# ⑨ 重配快取掛在內容庫上
# ---------------------------------------------------------------------------


def test_the_retier_cache_lives_on_the_library() -> None:
    lib = library()
    assert not hasattr(skill_tier, "_CACHE")
    skill = lib.skills[FLASHED]
    done = retier(lib, skill, 3)
    digest = hashlib.sha256(skill.model_dump_json().encode("utf-8")).hexdigest()
    assert lib.retier_cache[f"{digest}/3"] == done
    assert retier(lib, skill, 3) is done
    other = replace(lib)
    assert other.retier_cache == {} and other == lib  # 換內容是新的空快取；不參與相等比較


def _generate() -> None:
    """重產夾具：AI 代打 ``build_fire`` 種子 6 到第一個營火，寫成存檔。"""
    lib = library()
    run, _ = auto_play(
        lib, new_run(lib, "build_fire", 6), stop=lambda r, _b: isinstance(r.node, CampfireNode)
    )
    text = dumps_save(RunSave(run_id="fixture3wr1", run=run))
    FIXTURE.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    _generate()
