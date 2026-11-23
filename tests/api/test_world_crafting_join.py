"""鐵匠裝備說明用「；」接詞條時不出現「。；」（QF-7 (al)；``docs/art/E6-b2驗收.md`` 小修 1）。

現有詞條的玩家文字沒有「。」結尾，所以整合測試把測試內容庫的詞條文字都補上「。」再打造。
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from tests.api.test_world_api import START, _client
from tests.api.test_world_crafting_api import COARSE, SMITHY, _act, _ok
from trpg.api.world_crafting_view import join_clauses
from trpg.content.library import ContentLibrary


def test_join_clauses_drops_trailing_period() -> None:
    assert join_clauses(["不會滑倒。", "防禦值 +1%"]) == "不會滑倒；防禦值 +1%"
    assert join_clauses(["結 1 回合冰。。", "敏捷 +3。"]) == "結 1 回合冰；敏捷 +3"
    # 沒有「。」結尾時和原本的 join 逐字相同；句中的「。」不動
    assert join_clauses(["敏捷 +3", "閃避 +3%"]) == "；".join(["敏捷 +3", "閃避 +3%"])
    assert join_clauses(["先滑。再結冰", "敏捷 +3"]) == "先滑。再結冰；敏捷 +3"
    assert join_clauses([]) == ""


def test_crafted_gear_description_has_no_period_semicolon(
    library: ContentLibrary, tmp_path: Path
) -> None:
    economy = library.world_economy
    assert economy.rules is not None
    rules = economy.rules.model_copy(update={"start_gold": 1000})
    affixes = {
        k: a.model_copy(update={"name_zh": f"{a.name_zh}。"}) for k, a in library.affixes.items()
    }
    lib = dataclasses.replace(
        library, affixes=affixes, world_economy=dataclasses.replace(economy, rules=rules)
    )
    with _client(lib, tmp_path / "saves") as client:
        view = _ok(client.post("/api/world/characters", json=START), 201)
        cid = view["character"]["character_id"]
        # 主手的部位預算大，稀有就有兩條以上的詞條（才有「；」）
        slot = next(s for s in view["crafting"]["slots"] if s["slot_type"] == "weapon")
        for _ in range(4):
            _act(client, cid, kind="buy", shop="shop_liu", item=COARSE, count=1)
        craft = {"kind": "craft", "station": SMITHY, "slot_type": "weapon", "rarity": "rare"}
        view = _act(client, cid, **craft, affix=slot["affixes"][0]["id"], grade=COARSE)
    text = view["crafting"]["gear"][0]["description_zh"]
    assert "；" in text, text  # 至少兩條詞條，才有接起來的地方
    assert "。；" not in text and not text.endswith("。"), text
