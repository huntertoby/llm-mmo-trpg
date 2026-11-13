"""許願池（Phase WP-1；``docs/design/07-角色成長.md`` 7.6、#88；
``docs/phases/PhaseWP計畫.md`` 第 2 節）。

- **在哪裡、誰能許**（:func:`wish_problem`，畫面與送出共用）：人在主城、不在入門期、沒有待處理的
  遭遇、本週還有次數（每週 ``per_week`` 次，週＝:func:`~trpg.world.season.week_of`）、任務幣夠。
- **兩種許法**（:class:`~trpg.world.actions.WishAction`）：
  - **願望文字**：向生成內容的供應者要 :class:`~trpg.world.generated.WishGen`（API 層請 LLM 從
    選單對到 1～2 個關鍵字、再提議完整技能；願望文字只進 prompt 的 ``<player_input>``）。引擎驗證：
    關鍵字在選單內、不重複、數量對；三選一是完整技能、階級相同、每張都帶第 1 個關鍵字
    （:func:`~trpg.world.story_gen.checked_offer`）。三選一不合格只丟三選一（照關鍵字算組合器版）；
    關鍵字不合格或沒拿到（模型關閉、逾時、對不上）→ 拒絕這次許願、不扣錢不算次數（請玩家改用選單）。
  - **選單**：玩家自己挑 1～2 個關鍵字，不呼叫 LLM。
- **出題**：完整技能三選一、角色目前的階級；第 1 個關鍵字釘住（三張都帶）、全部關鍵字當偏向；
  「任何池」＝不限區域技能池（``region=None``，名稱與描述用中性奇幻，#126）。
- **扣款與次數**：先扣 ``cost_quest_coins`` 任務幣、本週次數 +1；三選一存進 ``pending_offers``
  （``source="wish"``），都不拿時退 ``refund_permille``（:func:`~trpg.world.quests.take_offer`，
  #88 2b「次數照扣、任務幣退一半」）。

純函式：不讀時間（``now`` 由呼叫者傳入）、不呼叫 LLM；
生成內容只經 :func:`~trpg.world.generated.supply`
拿資料，日誌記下最後給出的版本，重播只讀日誌。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final, Literal

from trpg.content.fields import CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.content.world_rules import WishRules
from trpg.roguelite.offers import make_offer
from trpg.roguelite.state import RunState, SkillOffer
from trpg.skillgen.skill_tier import character_tier
from trpg.world.actions import WishAction, WishMadeEvent, WorldEvent
from trpg.world.common import rules_of
from trpg.world.errors import WorldActionError
from trpg.world.generated import WishGen, WishGenRequest, input_key, supply
from trpg.world.growth import as_run, skill_seed, world_library
from trpg.world.opening_limits import in_starter_period
from trpg.world.quests import store_offer
from trpg.world.season import week_of
from trpg.world.state import CharacterState, WishWeek, WorldState
from trpg.world.story_gen import checked_offer

__all__ = [
    "WISH_NO_MATCH_ZH",
    "WISH_QUEST",
    "apply_wish",
    "wish_keywords_problem",
    "wish_menu",
    "wish_offer_ok",
    "wish_problem",
    "wish_refund",
    "wish_request",
    "wish_rules",
    "wishes_left",
    "wishes_used",
]

WISH_QUEST: Final = "wish"
"""許願池三選一的 ``PendingOffer.quest``（步驟是 ``w<週>_<第幾次>``）。"""
WISH_NO_MATCH_ZH: Final = "許願池這次沒聽懂你的願望，改從選單挑關鍵字吧（沒有扣任務幣）。"
"""願望文字沒對上關鍵字（模型關閉、逾時、驗證不過）時的原因句（暫定字）。"""


def wish_rules(library: ContentLibrary) -> WishRules:
    """世界規則的許願池數值。"""
    return rules_of(library).wish


def wish_refund(library: ContentLibrary) -> int:
    """三選一都不拿時退還的任務幣（費用 × ``refund_permille``，捨去）。"""
    rules = wish_rules(library)
    return rules.cost_quest_coins * rules.refund_permille // 1000


def wish_menu(library: ContentLibrary) -> tuple[str, ...]:
    """可以許的關鍵字（內容庫順序；扣掉開局隱藏的，PhaseWP計畫 待決 4）。"""
    return tuple(k.id for k in library.keywords.keywords if not k.start_hidden)


def wishes_used(library: ContentLibrary, world: WorldState, char: CharacterState, now: int) -> int:
    """本週已經許了幾次（換週＝0）。"""
    row = char.wish_week
    if row is None or row.week != week_of(library, world, now):
        return 0
    return row.used


def wishes_left(library: ContentLibrary, world: WorldState, char: CharacterState, now: int) -> int:
    """本週還能許幾次。"""
    return max(0, wish_rules(library).per_week - wishes_used(library, world, char, now))


def wish_problem(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> str | None:
    """現在不能許願的原因（繁體中文）；可以時 ``None``。畫面與送出共用。"""
    rules = wish_rules(library)
    if char.region != CAPITAL_REGION:
        return "只有在主城能許願"
    if in_starter_period(char):
        return "入門期還不能許願，找葛蘭選定武器後再來"
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇，不能許願"
    if wishes_left(library, world, char, now) <= 0:
        return f"這週已經許了 {rules.per_week} 次願，下週再來"
    if char.quest_coins < rules.cost_quest_coins:
        return f"任務幣不足，許願要 {rules.cost_quest_coins} 任務幣"
    return None


def wish_keywords_problem(
    library: ContentLibrary, keywords: tuple[str, ...], *, menu: tuple[str, ...] | None = None
) -> str | None:
    """關鍵字不合格的原因：1～``max_keywords`` 個、不重複、在選單內；合格時 ``None``。"""
    limit = wish_rules(library).max_keywords
    menu = wish_menu(library) if menu is None else menu
    if not 1 <= len(keywords) <= limit:
        return f"要挑 1～{limit} 個關鍵字"
    if len(set(keywords)) != len(keywords):
        return "關鍵字不能重複"
    unknown = [k for k in keywords if k not in menu]
    if unknown:
        return f"許願池沒有這個關鍵字：{'、'.join(unknown)}"
    return None


def _wish_run(world: WorldState, char: CharacterState) -> RunState:
    return as_run(char, seed=skill_seed(world, char)).model_copy(
        update={"offers_made": char.offers_made}
    )


def wish_request(
    library: ContentLibrary, world: WorldState, char: CharacterState, text: str
) -> WishGenRequest:
    """願望文字的生成請求；鍵由完整輸入算出（願望、選單、出題用的角色狀態）。"""
    rules = wish_rules(library)
    menu = wish_menu(library)
    run = _wish_run(world, char)
    data = {
        "char": char.character_id,
        "text": text,
        "menu": menu,
        "seed": run.seed,
        "level": run.level,
        "offers_made": run.offers_made,
        "skills": run.hero.skills,
        "bench": run.bench,
        "weapon": run.hero.weapon,
        "generated": [s.id for s in run.generated_skills],
        "max": rules.max_keywords,
        "cards": rules.llm_cards,
    }
    return WishGenRequest(
        character_id=char.character_id,
        key=input_key(f"wish/{char.character_id}/{char.offers_made}", data),
        text=text,
        menu=menu,
        run=run,
        max_keywords=rules.max_keywords,
        llm_cards=rules.llm_cards,
    )


def wish_offer_ok(offer: SkillOffer | None, tier: int, pinned: str) -> SkillOffer | None:
    """LLM 版的三選一合不合格：:func:`checked_offer`（完整技能、階級相同、候選與標示一一對應），而且
    每張都帶第 1 個關鍵字。"""
    checked = checked_offer(offer, tier)
    if checked is None or any(pinned not in t.keywords for t in checked.tags):
        return None
    return checked


def _acceptor(
    library: ContentLibrary, menu: tuple[str, ...], tier: int
) -> Callable[[WishGen], WishGen | None]:
    """引擎對 :class:`WishGen` 的驗證（守則 3）。"""

    def accept(gen: WishGen) -> WishGen | None:
        if gen.source == "none" or wish_keywords_problem(library, gen.keywords, menu=menu):
            return None
        if gen.source == "llm" and wish_offer_ok(gen.offer, tier, gen.keywords[0]) is not None:
            return gen
        # 三選一不合格（或只有關鍵字）：只丟三選一，引擎照關鍵字算組合器版
        return gen.model_copy(update={"source": "partial", "offer": None})

    return accept


def _text_keywords(
    library: ContentLibrary, world: WorldState, char: CharacterState, text: str, tier: int
) -> WishGen:
    rules = wish_rules(library)
    cleaned = text.strip()
    if not cleaned:
        raise WorldActionError("願望不能是空白")
    if len(cleaned) > rules.text_max_chars:
        raise WorldActionError(f"願望最多 {rules.text_max_chars} 個字")
    request = wish_request(library, world, char, cleaned)
    gen = supply(request, WishGen, WishGen(key=request.key), _acceptor(library, request.menu, tier))
    if gen.source == "none":
        raise WorldActionError(WISH_NO_MATCH_ZH)
    return gen


def apply_wish(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: WishAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """許願（見模組說明）。全部檢查完才動狀態；不合法拋 :class:`WorldActionError`。"""
    problem = wish_problem(library, world, char, now)
    if problem is not None:
        raise WorldActionError(problem)
    rules = wish_rules(library)
    view = world_library(library)
    run = _wish_run(world, char)
    tier = character_tier(view, run.level)
    via: Literal["text", "menu"]
    if action.text is not None:
        gen = _text_keywords(library, world, char, action.text, tier)
        keywords, via = gen.keywords, "text"
        llm_offer = gen.offer if gen.source == "llm" else None
    else:
        problem = wish_keywords_problem(library, action.keywords)
        if problem is not None:
            raise WorldActionError(problem)
        keywords, via, llm_offer = action.keywords, "menu", None
    made_by: Literal["llm", "composer"] = "llm" if llm_offer is not None else "composer"
    offer = llm_offer or make_offer(
        view,
        run,
        "complete",
        region_keywords=keywords,
        pinned_keyword=keywords[0],  # 三張都帶第 1 個關鍵字（待決 5）
        region=None,  # 「任何池」、中性奇幻（#126）
    )
    week = week_of(library, world, now)
    used = wishes_used(library, world, char, now) + 1
    cost = rules.cost_quest_coins
    refund = wish_refund(library)
    char = char.model_copy(
        update={
            "quest_coins": char.quest_coins - cost,
            "wish_week": WishWeek(week=week, used=used),
        }
    )
    char, offered = store_offer(
        char,
        WISH_QUEST,
        f"w{week}_{used}",
        offer,
        source="wish",
        region=char.region,
        made_by=made_by,
        refund=refund,
    )
    made = WishMadeEvent(
        via=via, keywords=keywords, made_by=made_by, coins_spent=cost, used=used, refund=refund
    )
    return char, (made, offered)
