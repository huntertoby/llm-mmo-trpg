"""Phase 3W-R1：升階後同一招只有一個真相來源、歷程重推失敗的退路、重配快取掛在內容庫上。

夾具 ``fixtures/flash_history_3wr1.json``：``build_fire`` 種子 6，AI 代打到第一個營火（等級 3、角色
階級 2；``skill_fire_bolt`` 閃過 3 次：第 1 次 ``keyword_exploit``、第 2 次 ``range_plus``、第 3 次
大變化）。重產：``uv run python -m tests.roguelite.test_truth_3wr1``（:func:`_generate`）。
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from functools import cache
from pathlib import Path

import pytest

from tests.roguelite.helpers import library
from trpg.api.run_presenter import flash_preview
from trpg.content.library import ContentLibrary
from trpg.roguelite import (
    RunSave,
    RunState,
    apply_choice,
    auto_play,
    dumps_save,
    loads_save,
    new_run,
)
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.flashes import (
    base_def,
    flash_request,
    inherit_problem,
    owned_skills,
    state_of,
)
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.retier import sync_skill_tier
from trpg.roguelite.state import CampfireNode, FlashChoice, FlashPickChoice, InheritChoice
from trpg.skillgen import skill_tier
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash import (
    FlashHistoryError,
    FlashStepError,
    _builder,
    derive_chain,
    derive_skill,
    history_error,
    history_problem,
    skill_before,
)
from trpg.skillgen.skill_tier import character_tier, retier

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
    assert builder.floor_permille == math.ceil(budget_power(card, lib) * 1000)  # type: ignore[arg-type]
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
