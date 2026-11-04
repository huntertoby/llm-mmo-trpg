"""Phase 6L-1：技能名稱與描述照取得地點的區域（#126）、全域語氣中性（C1）、古風詞檢查（C5）、
命名帶武器（12B 對照）、分區評估的自動驗收（C9）。"""

from __future__ import annotations

import json

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef
from trpg.content.world import load_style_eval, load_world_style
from trpg.llm import MockLLMClient
from trpg.llm.candidate_source import held_weapon_text
from trpg.llm.naming import NamingText, check_naming, name_skill, weapon_text
from trpg.llm.prompts.proposal import build_proposal_prompt
from trpg.llm.skill_eval import region_items
from trpg.llm.style_eval import DialogueRow, NameRow, archaic_hits, report_lines, style_report
from trpg.skillgen.proposal_subset import ProposalRequest

WORLD = load_world_style()
RULES = WORLD.naming


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


@pytest.fixture(scope="module")
def skill(library: ContentLibrary) -> SkillDef:
    return library.skills["skill_fire_arrow"]


def _text(name: str, concept: str = "火焰凝成箭矢。", flavor: str = "火光一閃。") -> NamingText:
    return NamingText(name_zh=name, concept=concept, cast_flavor=flavor)


def _codes(text: NamingText, *, archaic_ok: bool = False) -> list[str]:
    return [e.code for e in check_naming(text, RULES, archaic_ok=archaic_ok)]


# -- 資料 ---------------------------------------------------------------------


def test_global_tone_is_neutral() -> None:
    assert "中性奇幻" in WORLD.tone_zh and "施主" in WORLD.tone_zh  # C1：列出不用的詞


def test_style_payload_by_region() -> None:
    assert WORLD.style_payload(None) == {"region": "無（中性）", "style_zh": WORLD.neutral_style_zh}
    assert WORLD.style_payload("cloud_ridge")["region"] == "雲嶺"
    assert WORLD.style_payload("nowhere")["region"] == "無（中性）"  # 沒列出的區＝中性
    assert WORLD.archaic_ok("cloud_ridge")
    assert not WORLD.archaic_ok("ashen_waste") and not WORLD.archaic_ok("capital")
    assert not WORLD.archaic_ok(None)


def test_styles_cover_eval_regions_and_regions_yaml(library: ContentLibrary) -> None:
    styles = {s.region for s in WORLD.skill_styles}
    assert library.regions is not None
    assert {r.id for r in library.regions.regions} | {"capital"} == styles
    assert set(load_style_eval().eval_regions) <= styles


# -- 古風詞（C5） -------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "neutral", "eastern"),
    [
        ("餘燼之箭", [], []),
        ("風雷訣", ["name_zh.archaic"], []),  # 「某某訣」：雲嶺可以
        ("真氣斬", ["name_zh.archaic"], []),
        ("施主止步", ["name_zh.archaic"], ["name_zh.archaic"]),  # 「施主」：哪一區都不行
    ],
)
def test_archaic_names(name: str, neutral: list[str], eastern: list[str]) -> None:
    assert [c for c in _codes(_text(name)) if c.endswith("archaic")] == neutral
    assert [c for c in _codes(_text(name), archaic_ok=True) if c.endswith("archaic")] == eastern


def test_archaic_text_fields() -> None:
    codes = _codes(_text("餘燼之箭", concept="氣沉丹田，凝成火箭。"))
    assert "concept.archaic" in codes
    assert "concept.archaic" not in _codes(_text("餘燼之箭", concept="氣沉丹田。"), archaic_ok=True)


# -- prompt ---------------------------------------------------------------


def _request_block(library: ContentLibrary, region: str | None) -> dict[str, object]:
    request = ProposalRequest(1, "common", region=region)
    user = build_proposal_prompt(library, request).messages[1]["content"]
    body = user.split("<request>\n", 1)[1].split("\n</request>", 1)[0]
    return json.loads(body)


def test_proposal_request_carries_region_style(library: ContentLibrary) -> None:
    assert _request_block(library, None)["style"] == WORLD.style_payload(None)
    assert _request_block(library, "ashen_waste")["style"] == WORLD.style_payload("ashen_waste")


def _named(
    library: ContentLibrary, skill: SkillDef, replies: list[str], **kwargs: object
) -> tuple[MockLLMClient, str]:
    client = MockLLMClient(replies)
    outcome = name_skill(client, library, skill, **kwargs)  # type: ignore[arg-type]
    return client, outcome.text.name_zh


def _reply(name: str, concept: str = "火焰凝成箭矢射向目標。") -> str:
    return json.dumps(
        {"name_zh": name, "concept": concept, "cast_flavor": "火光一閃。"}, ensure_ascii=False
    )


def test_naming_prompt_has_region_style_and_weapon(
    library: ContentLibrary, skill: SkillDef
) -> None:
    client, _ = _named(library, skill, [_reply("餘燼之箭")], region="cloud_ridge", weapon="匕首")
    system, user = client.calls[0][0]["content"], client.calls[0][1]["content"]
    assert "X之Y" in system and "不要都用『X・Y』" in system and "施主" in system
    payload = json.loads(user.split("<skill>\n", 1)[1].split("\n</skill>", 1)[0])
    assert payload["style"] == WORLD.style_payload("cloud_ridge")
    assert payload["weapon"].startswith("匕首（")


def test_neutral_region_retries_archaic_name(library: ContentLibrary, skill: SkillDef) -> None:
    client, name = _named(
        library, skill, [_reply("烈焰訣"), _reply("餘燼之箭")], region="ashen_waste"
    )
    assert name == "餘燼之箭" and len(client.calls) == 2
    assert "name_zh.archaic" in client.calls[1][1]["content"]
    _, eastern = _named(library, skill, [_reply("烈焰訣")], region="cloud_ridge")
    assert eastern == "烈焰訣"


def test_weapon_text(library: ContentLibrary, skill: SkillDef) -> None:
    assert weapon_text(skill, "匕首").startswith("匕首（")
    spell = library.skills["skill_thunder_clap"]  # 法術：不靠武器
    assert "法術" in weapon_text(spell) and weapon_text(spell).startswith("任何武器")
    assert held_weapon_text({"dagger": "匕首", "buckler": "小圓盾"}) == "小圓盾、匕首"
    assert held_weapon_text(None) is None and held_weapon_text({}) is None


# -- 分區評估（C9） ------------------------------------------------------------


def test_region_items_repeat_same_question(library: ContentLibrary) -> None:
    regions = load_style_eval().eval_regions
    items = region_items(library, 2, regions, seed=0)
    assert [i.request.region for i in items] == [r for r in regions for _ in range(2)]
    first = [i for i in items if i.request.region == regions[0]]
    other = [i for i in items if i.request.region == regions[1]]
    assert [(i.request.tier, i.request.rarity, i.seed) for i in first] == [
        (i.request.tier, i.request.rarity, i.seed) for i in other
    ]


def test_style_report_passes_and_fails() -> None:
    rules, archaic = load_style_eval(), RULES.archaic
    good = [
        NameRow("ashen_waste", "焦土重擊"),
        NameRow("capital", "晨光之盾"),
        NameRow("cloud_ridge", "霧隱・竹影"),
        NameRow("capital", "火焰・爆裂", "fallback"),  # 退回的組合式名稱不算
    ]
    talks = [
        DialogueRow("cloud_ridge", "daoist_qingya", "施主，莫要亂撿。"),
        DialogueRow("cloud_ridge", "hunter_ayue", "霧裡有狼，別往深處走。"),
    ]
    report = style_report(good, talks, rules, archaic)
    assert report.passed and report.dot_names == 1 and report.llm_names == 3
    bad = [
        NameRow("ashen_waste", "焚天訣"),
        NameRow("capital", "火・光"),
        NameRow("capital", "冰・霜"),
    ]
    leak = [DialogueRow("cloud_ridge", "scarface", "這位施主，留下買路錢。")]
    report = style_report(bad, leak, rules, archaic)
    assert not report.archaic_ok and not report.honorific_ok and not report.dot_ok
    text = "\n".join(report_lines(report))
    assert "焚天訣" in text and "scarface" in text
    assert archaic_hits("焚天訣", archaic) == ["…訣"]
