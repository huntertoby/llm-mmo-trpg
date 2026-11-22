"""HC-3：前端不寫死的規則數字改由 API 帶（glossary 的 rules、主角的 flash_rules）。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.engine.helpers import library
from trpg.api.glossary import build_glossary
from trpg.api.run_schemas import HeroOut


def test_glossary_rules_come_from_content() -> None:
    lib = library()
    rules = build_glossary(lib).rules
    core = lib.ruleset.core
    assert rules.source_max == core.source_max
    assert rules.skill_slots.model_dump() == core.skill_slots.model_dump(exclude={"rule_change"})
    assert rules.start_keywords == lib.roguelite.start.keywords
    assert rules.complete_budget_permille == lib.flash.rules.complete.budget_permille


def test_glossary_endpoint_has_rules(client: TestClient) -> None:
    reply = client.get("/api/glossary")
    assert reply.status_code == 200
    rules = reply.json()["rules"]
    # HC-6b 加了說明文字組字用的欄位；HC-3 的四個照舊在
    assert {"source_max", "skill_slots", "start_keywords", "complete_budget_permille"} <= set(rules)
    assert set(rules["skill_slots"]) == {"active", "passive", "reaction", "stance"}


def test_run_hero_flash_rules_is_required() -> None:
    """前端拿掉了閃現規則的備用值，所以回應一定要帶 ``flash_rules``。"""
    assert HeroOut.model_fields["flash_rules"].is_required()
