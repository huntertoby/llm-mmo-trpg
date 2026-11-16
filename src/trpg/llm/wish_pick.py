"""許願池「願望驅動」的第二步：從照標籤排好的候選挑 3 張並命名、回應願望（Phase PK-4；07 7.6
「許願池：願望驅動」第 4 點，06 6.7 挑選模式）。

:func:`make_wish_picker` 回傳 :data:`~trpg.skillgen.wish_pick.WishPicker`：一次呼叫回答 3 張
（:mod:`trpg.llm.prompts.wish_pick`，``wish-pick/1``）。

1. 回應先過 JSON 與 pydantic（:class:`WishCardText`，多餘欄位拒絕）。
2. 每張：``pick`` 在範圍內、和其他張不重複；名稱與兩段文字同挑選模式的命名檢查
   （:func:`~trpg.llm.naming.check_naming`、加嚴的 :func:`~trpg.llm.naming.check_consistency`）；
   ``wish_zh``（回應願望）：字數、字元、只能提到這張有的效果（加嚴詞組也看）。
3. 不合格的那幾張帶 ``<errors>`` 重問（合格的留著），最多 ``max_attempts`` 次、一份
   ``budget_s`` 秒內。最後仍不合格：名稱不合格的那張不收（由程式依排序補）；只有回應願望那句
   不合格就不留那句（``wish.reply_dropped``）。
4. 連不上模型、格式壞掉用完次數＝一張都不給（程式依排序取前 3 名、組合式名稱）。

LLM 不能改候選：結果只換名稱與敘事（``apply_naming``；程式再比一次結構）。
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from trpg.content.effect_words import EffectWords, load_effect_words
from trpg.content.library import ContentLibrary
from trpg.content.world import WorldStyle, load_world_style
from trpg.llm.candidate_source import mock_naming_client
from trpg.llm.client import LLMClient, MockLLMClient
from trpg.llm.consistency import NameCheck, check_mentions, strict_facts
from trpg.llm.errors import LLMBadResponse, LLMTimeout, LLMUnavailable
from trpg.llm.naming import NamingText, apply_naming, check_consistency, check_naming
from trpg.llm.pick import candidate_card, fit_notes
from trpg.llm.prompts.wish_pick import (
    WISH_PICK_PROMPT_VERSION,
    WISH_REPLY_MAX_CHARS,
    build_wish_pick_messages,
    wish_pick_schema,
)
from trpg.llm.response import clean_response
from trpg.skillgen.candidates import LlmTrace
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.player_text import plain_name
from trpg.skillgen.wish_pick import (
    WISH_CARDS,
    WishCard,
    WishPick,
    WishPicker,
    tag_hits,
    tag_labels,
)

__all__ = [
    "WISH_PICK_BUDGET_S",
    "WishCardText",
    "make_wish_picker",
    "mock_wish_pick_client",
    "mock_wish_picker",
]

WISH_PICK_BUDGET_S = 10.0
"""一次許願請 LLM 挑選的時間上限（秒；06 6.34.7「超過 10 秒改給組合器版」）：用完就不再重問。"""
_REPLY_CHARS = re.compile(r"^[一-鿿　-〿＀-￯・—…‘-”、。，；：！？（）「」『』《》]+$")
_ENGLISH = re.compile(r"[A-Za-z_0-9]")


class WishCardText(BaseModel):
    """回應裡一張的格式（多餘欄位拒絕）。``wish_zh`` 可省（Mock 不寫）。"""

    model_config = ConfigDict(extra="forbid")

    pick: int
    name_zh: str
    concept: str
    cast_flavor: str
    wish_zh: str | None = None

    def naming(self) -> NamingText:
        return NamingText(name_zh=self.name_zh, concept=self.concept, cast_flavor=self.cast_flavor)


class _Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cards: list[WishCardText]


@dataclass(slots=True)
class _Card:
    """一張目前的答案。"""

    position: int | None = None
    naming: NamingText | None = None
    reply: str | None = None
    settled: bool = False
    codes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _Loop:
    client: LLMClient
    library: ContentLibrary
    ask: WishPick
    messages: Callable[[str | None, str | None], list[Any]]
    schema: dict[str, Any]
    style: WorldStyle
    words: EffectWords
    taken: set[str]
    cards: list[_Card]
    codes: list[str] = field(default_factory=list)
    attempts: int = 0
    previous: str | None = None
    feedback: str | None = None
    reason: str | None = None

    def attempt(self, number: int, limit: int) -> bool:
        """做一次呼叫；回傳要不要再問。"""
        self.attempts = number
        try:
            raw = self.client.complete(
                self.messages(self.previous, self.feedback), json_schema=self.schema
            )
        except LLMUnavailable as exc:
            self.codes.append("llm.unavailable")
            self.reason = f"llm.unavailable：{exc}"
            return False
        except (LLMTimeout, LLMBadResponse) as exc:
            self.codes.append("llm.timeout" if isinstance(exc, LLMTimeout) else "llm.bad_response")
            return True
        try:
            answer = _Answer.model_validate(json.loads(clean_response(raw)))
        except (json.JSONDecodeError, ValidationError):
            errors = [NameCheck("response.invalid", "回應必須是只含 cards（3 張）的 JSON。")]
        else:
            errors = self._take(answer.cards, final=number >= limit)
        self.codes.extend(e.code for e in errors)
        if all(c.settled for c in self.cards):
            return False
        self.previous = raw
        self.feedback = json.dumps(
            {
                "attempt": number,
                "max_attempts": limit,
                "errors": [{"code": e.code, "message": e.message} for e in errors],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return True

    def _take(self, answers: Sequence[WishCardText], *, final: bool) -> list[NameCheck]:
        errors: list[NameCheck] = []
        if len(answers) != WISH_CARDS:
            errors.append(NameCheck("cards.count", f"cards 要剛好 {WISH_CARDS} 張。"))
        for i, (card, text) in enumerate(zip(self.cards, answers, strict=False)):
            if card.settled:
                continue
            errors += [
                NameCheck(e.code, f"cards[{i}]：{e.message}")
                for e in self._card(i, text, final=final)
            ]
        return errors

    def _card(self, i: int, text: WishCardText, *, final: bool) -> list[NameCheck]:
        ranked = self.ask.slate.ranked
        card = self.cards[i]
        others = {c.position for j, c in enumerate(self.cards) if j != i and c.settled}
        if not 0 <= text.pick < len(ranked):
            return [NameCheck("pick.out_of_range", f"pick 要是 0～{len(ranked) - 1}。")]
        if text.pick in others:
            return [NameCheck("pick.duplicate", "3 張的 pick 不可重複。")]
        skill = ranked[text.pick].skill
        naming = text.naming()
        facts = strict_facts(self.library, skill)
        used = self.taken | {
            c.naming.name_zh for c in self.cards if c.naming is not None and c.settled
        }
        problems = check_naming(naming, self.style.naming, used, archaic_ok=False)
        problems += check_consistency(naming, facts, self.words, strict=True)
        if problems:
            return problems
        reply, reply_problems = self._reply(text.wish_zh, facts)
        card.position, card.naming = text.pick, naming
        if reply_problems and not final:
            return reply_problems
        if reply_problems:
            card.codes.append("wish.reply_dropped")
        card.reply, card.settled = reply, True
        return []

    def _reply(self, text: str | None, facts: frozenset[str]) -> tuple[str | None, list[NameCheck]]:
        if text is None:
            return None, []
        body = text.strip()
        if not body or len(body) > WISH_REPLY_MAX_CHARS:
            return None, [
                NameCheck("wish_zh.length", f"wish_zh 要 1～{WISH_REPLY_MAX_CHARS} 個字。")
            ]
        if _ENGLISH.search(body) or not _REPLY_CHARS.match(body):
            return None, [
                NameCheck("wish_zh.charset", "wish_zh 只能用全形中文與全形標點，不可有英文或數字。")
            ]
        problems = check_mentions("wish_zh", body, facts, self.words, strict=True)
        return (None, problems) if problems else (body, [])


def _payload(library: ContentLibrary, ask: WishPick, player: PickPlayer) -> dict[str, Any]:
    return {
        "style": "主城（中性奇幻）",
        "weapon": ask.weapon_zh or "依技能需求",
        "tier": ask.tier,
        "wish_tags": list(tag_labels(library, ask.tags)),
    }


def _cards(library: ContentLibrary, ask: WishPick, player: PickPlayer) -> list[dict[str, Any]]:
    out = []
    for i, c in enumerate(ask.slate.ranked):
        card = candidate_card(library, c.skill, i, fit=fit_notes(library, c.skill, player))
        hit, miss = tag_hits(library, c.skill, ask.tags)
        if hit:
            card["hits"] = list(hit)
        if miss:
            card["misses"] = list(miss)
        out.append(card)
    return out


def _player(library: ContentLibrary, player: PickPlayer) -> dict[str, Any]:
    """玩家手上的技能（名稱與關鍵字；同挑選模式的 ``<player>``）。"""
    skills = []
    for s in sorted(player.held_skills, key=lambda s: s.id):
        found = derive_keywords(s, library.keywords, exclusive_only=True).all()
        skills.append({"name": s.name_zh, "keywords": [plain_name(k, library) for k in found]})
    return {"skills": skills}


def _trace(ask: WishPick, card: _Card, loop: _Loop) -> LlmTrace:
    return LlmTrace(
        keywords=ask.tags.keywords,
        rarity=ask.slate.ranked[card.position or 0].skill.rarity,
        core_primitive=None,
        menu_seed=None,
        theme=None,
        attempts=loop.attempts,
        ok=True,
        codes=tuple(dict.fromkeys([*loop.codes, *card.codes])),
        name_source="llm",
        name_attempts=loop.attempts,
        prompt_version=WISH_PICK_PROMPT_VERSION,
        pick_seeds=ask.slate.seeds,
        pick_designs=ask.slate.designs,
        pick_index=card.position,
    )


def make_wish_picker(
    client: LLMClient,
    library: ContentLibrary,
    wish: str,
    *,
    max_attempts: int = 3,
    budget_s: float = WISH_PICK_BUDGET_S,
    clock: Callable[[], float] = time.monotonic,
    world: WorldStyle | None = None,
    words: EffectWords | None = None,
    taken: Collection[str] = (),
) -> WishPicker:
    """願望 ``wish``（只進 ``<player_input>``）的挑選器（見模組說明）。"""
    style = world if world is not None else load_world_style()
    vocab = words if words is not None else load_effect_words()

    def pick(ask: WishPick, player: PickPlayer) -> list[WishCard]:
        used = set(taken) | {s.name_zh for s in player.held_skills}
        used |= {s.name_zh for s in library.skills.values()}
        payload = _payload(library, ask, player)
        who = _player(library, player)
        cards = _cards(library, ask, player)

        def messages(previous: str | None, errors: str | None) -> list[Any]:
            return build_wish_pick_messages(
                payload,
                who,
                cards,
                sorted(set(taken)),
                wish,
                previous=previous,
                errors=errors,
                world=style,
            )

        loop = _Loop(
            client,
            library,
            ask,
            messages,
            wish_pick_schema(len(ask.slate.ranked), style),
            style,
            vocab,
            used,
            [_Card() for _ in range(WISH_CARDS)],
        )
        start = clock()
        for number in range(1, max_attempts + 1):
            if not loop.attempt(number, max_attempts) or clock() - start >= budget_s:
                break
        out: list[WishCard] = []
        for card in loop.cards:
            if not card.settled or card.position is None or card.naming is None:
                continue
            chosen = ask.slate.ranked[card.position].skill
            out.append(
                WishCard(
                    card.position,
                    apply_naming(chosen, card.naming),
                    card.reply,
                    _trace(ask, card, loop),
                    llm=True,
                )
            )
        return out

    return pick


def mock_wish_pick_client(
    library: ContentLibrary, ask: WishPick, *, picks: Sequence[int] = (0, 1, 2), attempts: int = 3
) -> MockLLMClient:
    """Mock 挑選（不需網路與金鑰）：挑 ``picks``（超出範圍照填，用來測退回），名稱與兩段文字照 Mock
    命名（依種子挑詞），不寫回應願望的那一句（同 Mock 不寫描述）。"""
    cards = []
    for n, index in enumerate(picks):
        target = ask.slate.ranked[index].skill if 0 <= index < len(ask.slate.ranked) else None
        if target is None and ask.slate.ranked:
            target = ask.slate.ranked[0].skill
        if target is None:
            continue
        text = json.loads(
            mock_naming_client(library, target, ask.seed + n).complete([], json_schema=None)
        )
        cards.append({"pick": index, **text})
    return MockLLMClient([json.dumps({"cards": cards}, ensure_ascii=False)] * attempts)


def mock_wish_picker(library: ContentLibrary, *, picks: Sequence[int] = (0, 1, 2)) -> WishPicker:
    """Mock 挑選器：每次許願都挑 ``picks``（:func:`mock_wish_pick_client`），不限時。"""

    def pick(ask: WishPick, player: PickPlayer) -> Sequence[WishCard]:
        client = mock_wish_pick_client(library, ask, picks=picks)
        inner = make_wish_picker(client, library, "（Mock）", budget_s=float("inf"))
        return inner(ask, player)

    return pick
