"""NW-2a：技能預算端點（T-A3）、分組預覽（T-A5）、非法值（T-A6）、digest（T-A9）。

讀專案內建 ``content/`` 的服務一律 ``git = None``（不可能寫回）。"""

from __future__ import annotations

import io
import re
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.api.tuning.check import prepare
from trpg.api.tuning.drafts import Change
from trpg.api.tuning.schemas import (
    TuningChangeIn,
    TuningGroupFilter,
    TuningGroupIn,
    TuningGroupOp,
)
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.skills import (
    GROUP_PRESETS,
    MAX_GROUP,
    GroupError,
    _apply_int,
    _ladder_step,
    _round_div,
)
from trpg.cli.budget import print_skill_budget
from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import bundled_content_dir
from trpg.engine.ruleset_hash import hash_ruleset
from trpg.roguelite.save import ruleset_hash
from trpg.world.save import content_digest

CONTENT = bundled_content_dir()
FIRE = "skills/skill_fire_arrow.yaml"
PINPOINT = "skills/skill_pinpoint_shot.yaml"
BOLT = "skills/skill_fire_bolt.yaml"
HEART = "units/ashen_heart.yaml"
_RATIO = re.compile(r"比例 ＝ total ÷ 可用預算 ＝ (\d+\.\d%)（合格區間 (\S+)–(\S+)）→ (\S+)")
_FORM = re.compile(r"＝ (\d+\.\d%) → (\S+)$")


def _sample(library: ContentLibrary) -> list[str]:
    """20 招：變奏、複合、被動、姿態、陷阱各至少一招，其餘是一般主動技。"""
    skills = sorted(
        (s for s in library.skills.values() if not s.id.startswith("skill_gear_")),
        key=lambda s: s.id,
    )
    picks: list[str] = []
    for test, n in (
        (lambda s: bool(s.variants), 4),
        (lambda s: s.followup is not None, 4),
        (lambda s: s.kind == "passive", 3),
        (lambda s: s.kind == "stance", 2),
        (lambda s: s.trap is not None, 2),
        (lambda s: s.kind == "active", 20),
    ):
        picks += [s.id for s in skills if test(s) and s.id not in picks][:n]
    return picks[:20]


def test_budget_numbers_match_the_cli(read_service: TuningService) -> None:
    library = read_service.library
    assert library is not None
    sample = _sample(library)
    assert len(sample) == 20
    verdicts = {"合格": "ok", "超出預算": "over", "過弱": "weak"}
    for skill_id in sample:
        out = io.StringIO()
        print_skill_budget(library, library.skills[skill_id], out)
        text = out.getvalue()
        result = read_service.budget(skill_id)
        found = _RATIO.search(text)
        assert found is not None, skill_id
        assert result.ratio_text == found.group(1), skill_id
        assert verdicts[found.group(4)] == result.verdict, skill_id
        forms = [m for line in text.splitlines() if (m := _FORM.search(line))]
        assert [(v.ratio_text, v.verdict) for v in result.variants] == [
            (m.group(1), verdicts[m.group(2)]) for m in forms
        ], skill_id
        assert len(result.segments) in (0, 2)
        assert ("驗證：通過" in text) == (not result.violations), skill_id


def test_budget_follows_the_change_direction(read_service: TuningService) -> None:
    base = read_service.budget("skill_fire_arrow")
    assert base.ratio_text == "78.8%" and base.verdict == "ok"
    up = read_service.budget(
        "skill_fire_arrow",
        [TuningChangeIn(file=FIRE, path="effects[0].multiplier_permille", old=800, new=900)],
    )
    down = read_service.budget(
        "skill_fire_arrow",
        [TuningChangeIn(file=FIRE, path="effects[0].multiplier_permille", old=800, new=700)],
    )
    assert base.ratio_permille is not None
    assert up.ratio_permille is not None and up.ratio_permille > base.ratio_permille
    assert down.ratio_permille is not None and down.ratio_permille < base.ratio_permille
    over = read_service.budget(
        "skill_fire_arrow",
        [TuningChangeIn(file=FIRE, path="effects[0].multiplier_permille", old=800, new=1300)],
    )
    assert over.verdict == "over" and any(v.rule == "budget.over" for v in over.violations)
    bad = read_service.budget(
        "skill_fire_arrow",
        [TuningChangeIn(file=FIRE, path="effects[0].multiplier_permille", old=800, new="x")],
    )
    assert bad.verdict == "error" and bad.field_errors


def test_budget_route(read_service: TuningService) -> None:
    app = create_app(tuning=True)
    app.state.tuning = read_service
    with TestClient(app) as client:
        ok = client.post("/api/tuning/skills/skill_fire_arrow/budget")
        assert ok.status_code == 200 and ok.json()["ratio_text"] == "78.8%"
        assert client.post("/api/tuning/skills/skill_nope/budget").status_code == 404
        presets = client.get("/api/tuning/skills/presets").json()
        assert [p["key"] for p in presets] == [p.key for p in GROUP_PRESETS]
        none = client.post(
            "/api/tuning/skills/group-preview",
            json={"target": "ap_cost", "op": {"kind": "add", "value": 1}},
        )
        assert none.status_code == 422 and "篩選" in none.json()["detail"]


# ---------------------------------------------------------------------------
# 分組改（T-A5）
# ---------------------------------------------------------------------------


def test_rounding_and_ladders_are_integer_and_deterministic() -> None:
    assert _apply_int(850, "scale_permille", 1100) == 935
    assert _round_div(1005 * 500, 1000) == 503  # 502.5 → 503（.5 進位）
    assert _round_div(1003 * 500, 1000) == 502  # 501.5 → 502
    assert _round_div(-5, 2) == -3
    ladder = (500, 600, 700, 800, 1000)
    assert _ladder_step(ladder, 800, 1) == 1000
    assert _ladder_step(ladder, 750, 1) == 800 and _ladder_step(ladder, 750, -1) == 700
    assert _ladder_step(ladder, 1000, 1) is None and _ladder_step(ladder, 500, -1) is None


def _preview(service: TuningService, **kwargs: object) -> dict[str, object]:
    request = TuningGroupIn.model_validate(kwargs)
    return {r.skill_id: r for r in service.group_preview(request).rows}


def test_damage_selectors_touch_only_the_right_effects(read_service: TuningService) -> None:
    op = {"kind": "scale_permille", "value": 1100}
    base = _preview(read_service, skills=["skill_pinpoint_shot"], target="damage_base", op=op)
    row = base["skill_pinpoint_shot"]
    assert [(c.path, c.old, c.new) for c in row.changes] == [  # type: ignore[attr-defined]
        ("effects[0].multiplier_permille", 1000, 1100)
    ]
    cond = _preview(
        read_service, skills=["skill_pinpoint_shot"], target="damage_conditional", op=op
    )
    assert [(c.path, c.new) for c in cond["skill_pinpoint_shot"].changes] == [  # type: ignore[attr-defined]
        ("effects[1].multiplier_permille", 1430)
    ]
    every = _preview(read_service, skills=["skill_pinpoint_shot"], target="damage_all", op=op)
    assert len(every["skill_pinpoint_shot"].changes) == 2  # type: ignore[attr-defined]
    dice = _preview(read_service, skills=["skill_fire_bolt"], target="damage_all", op=op)
    assert dice["skill_fire_bolt"].verdict == "skipped"  # type: ignore[attr-defined]
    assert "±級" in (dice["skill_fire_bolt"].skipped_reason_zh or "")  # type: ignore[attr-defined]
    up = _preview(
        read_service,
        skills=["skill_fire_bolt"],
        target="damage_all",
        op={"kind": "ladder", "value": 1},
    )
    change = up["skill_fire_bolt"].changes[0]  # type: ignore[attr-defined]
    assert change.path == "effects[0].dice" and change.old == "1d8" and change.new == "2d4"


def test_ladder_top_is_skipped_and_scalar_fields_clamp(read_service: TuningService) -> None:
    top = _preview(
        read_service,
        skills=["skill_fire_arrow"],
        target="damage_all",
        op={"kind": "ladder", "value": 999},
    )
    assert top["skill_fire_arrow"].verdict == "skipped"  # type: ignore[attr-defined]
    ap = _preview(
        read_service, skills=["skill_fire_arrow"], target="ap_cost", op={"kind": "add", "value": 9}
    )
    assert [(c.old, c.new) for c in ap["skill_fire_arrow"].changes] == [(1, 3)]  # type: ignore[attr-defined]
    cd = _preview(
        read_service,
        skills=["skill_fire_arrow"],
        target="cost.cooldown",
        op={"kind": "add", "value": 1},
    )
    assert cd["skill_fire_arrow"].verdict == "skipped"  # type: ignore[attr-defined] # 沒有冷卻
    weapon = _preview(
        read_service,
        skills=["skill_fire_arrow"],
        target="shape.range",
        op={"kind": "add", "value": 1},
    )
    assert "武器射程" in (weapon["skill_fire_arrow"].skipped_reason_zh or "")  # type: ignore[attr-defined]


def test_group_limits_and_determinism(read_service: TuningService) -> None:
    with pytest.raises(GroupError, match="篩選"):
        read_service.group_preview(
            TuningGroupIn(target="ap_cost", op=TuningGroupOp(kind="add", value=1))
        )
    with pytest.raises(GroupError, match=str(MAX_GROUP)):
        read_service.group_preview(
            TuningGroupIn(
                filter=TuningGroupFilter(kind=["active"]),
                target="ap_cost",
                op=TuningGroupOp(kind="add", value=1),
            )
        )
    request = TuningGroupIn(
        filter=GROUP_PRESETS[0].filter,
        target="damage_base",
        op=TuningGroupOp(kind="ladder", value=1),
    )
    first = read_service.group_preview(request)
    assert first == read_service.group_preview(request)
    ids = [r.skill_id for r in first.rows]
    assert ids == sorted(ids) and 0 < len(ids) <= MAX_GROUP
    assert first.rows[0].changes and first.rows[0].changes[0].file.startswith("skills/")


# ---------------------------------------------------------------------------
# 非法值（T-A6）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        (FIRE, "ap_cost", 1, 0, "1 到 3"),
        (FIRE, "cost.cooldown", None, 7, "不能大於 6"),
        (BOLT, "effects[0].dice", "1d8", "2x6", "NdM"),
        (FIRE, "effects[0].multiplier_permille", 800, 0, "1–10000"),
        (BOLT, "shape.range", 5, 99, "range"),
        (FIRE, "shape.range", "weapon", 4, "武器射程"),
        (
            HEART,
            "skills",
            ["skill_lava_splash", "skill_fire_bolt", "skill_ashen_oath"],
            ["skill_nope_nope"],
            "沒有這招",
        ),
        (
            HEART,
            "skills",
            ["skill_lava_splash", "skill_fire_bolt", "skill_ashen_oath"],
            ["skill_fire_bolt", "skill_fire_bolt"],
            "兩次",
        ),
        (
            HEART,
            "skills",
            ["skill_lava_splash", "skill_fire_bolt", "skill_ashen_oath"],
            ["skill_fire_bolt", "skill_cleave"],
            "近戰武器",
        ),
    ],
)
def test_illegal_values_carry_reasons_and_paths(
    read_service: TuningService, case: tuple[str, str, object, object, str]
) -> None:
    file, path, old, new, why = case
    result = read_service.check(
        "x",
        [TuningChangeIn(file=file, path=path, old=old, new=new)],  # type: ignore[arg-type]
    )
    assert not result.ok
    mine = [e for e in result.field_errors if e.file == file and e.path == path]
    assert mine, result
    assert any(why in e.message_zh for e in mine), mine


def test_player_side_unit_cannot_take_an_enemy_only_move(
    tmp_path: Path, content_library: ContentLibrary
) -> None:
    """玩家這一邊（build 的隊友）裝敵人專用招：載入檢查擋，錯誤對到欄位（D6；用假白名單打開
    ``sim_companion_fighter``）。"""
    content = tmp_path / "content"
    shutil.copytree(CONTENT, content)
    whitelist = content / "tuning_fields.yaml"
    whitelist.write_text(
        whitelist.read_text(encoding="utf-8").replace("      - sim_*\n", "", 1), encoding="utf-8"
    )
    service = TuningService(content, tmp_path / "saves", content_library)
    service.git = None
    companion = "units/sim_companion_fighter.yaml"
    old = list(content_library.units["sim_companion_fighter"].skills)
    assert old == []  # 標準隊友沒寫技能欄：插入一行
    result = service.check(
        "x",
        [TuningChangeIn(file=companion, path="skills", old=None, new=["skill_mist_rend"])],
    )
    errors = [e for e in result.field_errors if e.file == companion and e.path == "skills"]
    assert errors and "enemy_only" in errors[0].message_zh


# ---------------------------------------------------------------------------
# digest（T-A9）
# ---------------------------------------------------------------------------


def test_changing_a_skill_changes_all_three_digests(read_service: TuningService) -> None:
    original = load_library(CONTENT)
    prepared = prepare(
        CONTENT,
        read_service.table,
        [Change(file=FIRE, path="effects[0].multiplier_permille", old=800, new=850)],
    )
    draft = load_library(read_service.workspace.draft(prepared.texts))
    assert hash_ruleset(draft.ruleset) != hash_ruleset(original.ruleset)  # 技能在規則包裡
    assert ruleset_hash(draft) != ruleset_hash(original)
    assert content_digest(draft) != content_digest(original)
    same = load_library(read_service.workspace.draft({}))
    assert hash_ruleset(same.ruleset) == hash_ruleset(original.ruleset)
    assert ruleset_hash(same) == ruleset_hash(original)
    assert content_digest(same) == content_digest(original)
