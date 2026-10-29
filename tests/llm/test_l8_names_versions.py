"""Phase 4-L8（PM 追加）：提議 schema 不含技能名稱（由命名步驟或組合式名稱決定）、提議與命名的
prompt 版本號寫進 run 紀錄。全部用 Mock，不需網路。"""

from __future__ import annotations

import json

from tests.engine.helpers import library
from trpg.llm import MockLLMClient
from trpg.llm.candidate_source import mock_proposer
from trpg.llm.naming import fallback_naming
from trpg.llm.prompts.builder import PROMPT_VERSION
from trpg.llm.prompts.naming import NAMING_PROMPT_VERSION
from trpg.llm.propose import propose_skill
from trpg.roguelite import RunSave, dumps_save, loads_save, new_run
from trpg.roguelite.state import LlmRecord
from trpg.skillgen.proposal import (
    ProposalContext,
    build_proposal_models,
    combined_skill_name,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_subset import ProposalRequest

LIB = library()


def _top_level_properties(schema: dict) -> set[str]:  # type: ignore[type-arg]
    found: set[str] = set()
    for name, node in schema.get("$defs", {}).items():
        if name.startswith("SkillProposal"):
            found |= set(node.get("properties", {}))
    found |= set(schema.get("properties", {}))
    return found


def test_proposal_schema_has_no_skill_name() -> None:
    schema = build_proposal_models(LIB).json_schema()
    props = _top_level_properties(schema)
    assert "skeleton" in props and "name_zh" not in props
    assert "name_zh" not in proposal_from_skill(LIB.skills["skill_cleave"], LIB)


def test_a_proposed_name_is_rejected() -> None:
    data = {**proposal_from_skill(LIB.skills["skill_cleave"], LIB), "name_zh": "自創名稱"}
    result = evaluate_proposal(data, build_proposal_models(LIB), LIB, ProposalContext(1, "rare"))
    assert any(e.path == "name_zh" and e.code == "extra_forbidden" for e in result.errors)


def test_without_naming_the_skill_gets_the_combined_name() -> None:
    text = json.dumps(proposal_from_skill(LIB.skills["skill_cleave"], LIB), ensure_ascii=False)
    request = ProposalRequest(1, "rare", skeleton="area")
    outcome = propose_skill(MockLLMClient([text]), LIB, request, ProposalContext(1, "rare"), seed=1)
    assert outcome.source == "llm", outcome.reason
    assert outcome.skill.name_zh == combined_skill_name(LIB, outcome.skill)
    assert outcome.skill.name_zh == fallback_naming(LIB, outcome.skill).name_zh


def test_mock_proposer_records_prompt_versions() -> None:
    proposer = mock_proposer(LIB, naming=True)
    attempt = proposer(ProposalRequest(1, "rare", skeleton="strike"), ProposalContext(1, "rare"), 3)
    assert attempt.attempts >= 1
    assert attempt.prompt_version == PROMPT_VERSION
    if attempt.skill is not None:
        assert attempt.naming_prompt_version == NAMING_PROMPT_VERSION
    else:
        assert attempt.naming_prompt_version is None


def test_versions_survive_the_save_and_old_saves_load() -> None:
    record = LlmRecord(
        attempts=1,
        ok=True,
        prompt_version=PROMPT_VERSION,
        naming_prompt_version=NAMING_PROMPT_VERSION,
    )
    run = new_run(LIB, "build_push", 1)
    run = run.model_copy(update={"llm_log": (record,)})
    back = loads_save(dumps_save(RunSave(run_id="v", run=run)))
    assert back.format == "trpg-run/10"
    assert back.run.llm_log[0].prompt_version == PROMPT_VERSION
    assert back.run.llm_log[0].naming_prompt_version == NAMING_PROMPT_VERSION
    raw = json.loads(dumps_save(RunSave(run_id="v9", run=new_run(LIB, "build_push", 1))))
    raw["format"] = "trpg-run/9"
    assert loads_save(json.dumps(raw)).format == "trpg-run/10"
