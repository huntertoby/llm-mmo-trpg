"""大世界 LLM 入口的背景預先生成（Phase 6L-2；06 6.34.7「預先生成」，使用者：「要（推薦）」、
沒趕上時「等，超過 10 秒改給組合器版（推薦）」）。

三個入口（:mod:`trpg.world.generated`）：閃現與重閃的變化、主線劇情技能的元素與文字、機遇的完整技能
三選一。這一層：

- **預測**（:func:`predicted_requests`，每個世界動作之後、角色第一次讀進來時）：
  - 閃現：沒有待選的閃現與遭遇時，裝備中可以閃的技能（不指定類別、最多 :data:`FLASH_LIMIT` 招，
    依技能列順序）。6L-2b 起不看地點：戰鬥結束、那招可以閃了就開始，走回城鎮的路上也在生成；
  - 劇情技能：進行中任務還沒做的步驟有劇情技能時（6L-2b 起接到任務就開始，不只下一步；現在與做到
    那一步的等級各一份，最多 :data:`STORY_LIMIT`）；
  - 機遇：每份三選一最多 :data:`OPPORTUNITY_LLM_CARDS` 張請 LLM（6L-2b），其餘用組合器；
    ``pending_event`` 有可用的機遇解法時（最多 :data:`OPPORTUNITY_LIMIT`）。
- **單一佇列**：一條背景執行緒依序做，同一時間只有一個 LLM 請求。暫存區全服最多
  :data:`QUEUE_LIMIT` 筆，超過時丟掉最舊、還沒開始的。
- **只放記憶體**：結果不寫日誌也不寫存檔；預測換了（角色狀態變了）就丟掉這個角色沒用到的。
- **閃現的暫存鍵不含用法統計**（6L-2c，玩法 PM 決定）：每打完一場統計都會變，放進鍵就會一直重做。
  統計只在開始生成時讀一次（那次請求的輸入）；同一招同一次出題只有一筆，已經在生成或做好的不重開。
  玩家按下時給出去的那一筆，鍵改成按下那一刻的請求鍵，引擎照樣驗證，日誌記下的就是這一份。
- **玩家真的打開時**（引擎向供應者要，:meth:`WorldPregen.supplier`）：好了就給；還沒好就等，**最多
  10 秒**（:data:`WAIT_SECONDS`，從第一次等待算起；劇情技能最多 2 秒，:data:`STORY_WAIT_SECONDS`，
  6L-2b），超過就回 ``None``（引擎改給組合器、模板或內容版）。給出去的那一筆從暫存區拿掉；
  引擎把最後給出的版本記進日誌。
- **等待提示**（:meth:`WorldPregen.wait`，``POST .../pregen/wait``）：前端按閃現、選機遇解法之前
  先問；會等到好了或 10 秒，期間前端顯示等待提示，可以取消（取消＝不送那個動作）。
- 模型關閉（世界的 LLM 開關關掉、健康檢查說不可用）：不預測、不等，一律降級。

計時只在這一層（``clock`` 可注入假時鐘），世界引擎不讀時間（守則 1）。
"""

from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict

from trpg.api.llm_source import LlmProvider
from trpg.content.library import ContentLibrary
from trpg.llm.flash_propose import LlmFlashSource
from trpg.llm.story_skill import StorySkillRequest
from trpg.roguelite.flashes import problem_of
from trpg.roguelite.llm_hook import use_proposer
from trpg.roguelite.offers import make_offer, offer_key
from trpg.roguelite.state import FlashChoice, FlashLlmRecord
from trpg.world.common import rules_of
from trpg.world.generated import (
    FlashGen,
    FlashGenRequest,
    GenRequest,
    OfferGen,
    OfferGenRequest,
    StoryGen,
    StoryGenRequest,
    Supplier,
    flash_pregen_key,
)
from trpg.world.growth import (
    as_run,
    at_service,
    char_library,
    flash_blocked_zh,
    gain_xp,
    skill_region,
    skill_seed,
    world_flash_request,
    world_library,
)
from trpg.world.quests import quest_def
from trpg.world.situations import opportunity_available
from trpg.world.solutions import opportunity_tier_bonus
from trpg.world.state import CharacterState, WorldState
from trpg.world.story_gen import opportunity_request, story_base, story_request

__all__ = [
    "FLASH_LIMIT",
    "OPPORTUNITY_LIMIT",
    "OPPORTUNITY_LLM_CARDS",
    "QUEUE_LIMIT",
    "STORY_LIMIT",
    "STORY_WAIT_SECONDS",
    "WAIT_SECONDS",
    "Generators",
    "PregenWaitOut",
    "PregenWaitRequest",
    "WorldPregen",
    "flash_wait_request",
    "opportunity_wait_request",
    "predicted_requests",
    "provider_generators",
]

_LOG = logging.getLogger(__name__)

WAIT_SECONDS: Final = 10.0
"""沒趕上時最多等多久（秒，使用者決定）；超過改給組合器、模板或內容版。"""
STORY_WAIT_SECONDS: Final = 2.0
"""劇情技能（破霧）沒趕上時最多靜默等多久（6L-2b，玩法 PM 照 #132）：完成那一步的動作沒有等待提示，
不讓玩家沒有提示地卡 10 秒；超過就給內容版。"""
FLASH_LIMIT: Final = 3
"""每個角色一次最多預先生成幾招的閃現（保守上限）。"""
STORY_LIMIT: Final = 2
"""每個角色最多幾份劇情技能（同一步完成前後的等級各一份）。"""
OPPORTUNITY_LIMIT: Final = 1
"""每個角色最多幾份機遇的三選一（同一個事件通常只有一個機遇解法）。"""
OPPORTUNITY_LLM_CARDS: Final = 1
"""機遇的完整技能三選一每份最多幾張請 LLM（6L-2b，玩法 PM 照 #132）；其餘用組合器與技能池。
roguelite 照舊（每種候選各擲一次）。"""
QUEUE_LIMIT: Final = 12
"""全服暫存區（含排隊中與做好的）最多幾筆；超過丟掉最舊、還沒開始的。"""
_POLL_SECONDS: Final = 0.05

type Kind = Literal["flash", "story_skill", "complete_offer"]


@dataclass(frozen=True, slots=True)
class Generators:
    """三個入口的生成函式（內容庫是世界引擎用的同一個視圖）；``None``＝這個入口不生成。"""

    flash: Callable[[ContentLibrary, FlashGenRequest], FlashGen] | None = None
    story: Callable[[ContentLibrary, StoryGenRequest], StoryGen] | None = None
    offer: Callable[[ContentLibrary, OfferGenRequest], OfferGen] | None = None


def provider_generators(provider: LlmProvider) -> Generators:
    """用 :class:`~trpg.api.llm_source.LlmProvider` 建三個生成函式（設定壞掉的入口回降級紀錄）。"""

    def flash(library: ContentLibrary, request: FlashGenRequest) -> FlashGen:
        factory = provider.flash_source(library)
        records: list[BaseModel] = []
        source = None if factory is None else factory(records.append)
        if isinstance(source, LlmFlashSource):
            skill = request.request.current or request.request.base
            source.proposed(library, request.request, skill)
        if not records:
            return FlashGen(key=request.key, record=FlashLlmRecord(tag=request.key))
        record = FlashLlmRecord.model_validate(records[-1].model_dump(mode="json"))
        return FlashGen(key=request.key, record=record)

    def story(library: ContentLibrary, request: StoryGenRequest) -> StoryGen:
        proposer = provider.story_proposer(library)
        base = StoryGen(key=request.key, skill=request.skill.id)
        if proposer is None:
            return base
        made = proposer(
            StorySkillRequest(
                skill=request.skill,
                elements=request.elements,
                keywords=request.keywords,
                region=request.region,
                weapon=request.weapon_zh,
            )
        )
        if made.source != "llm":
            return base
        return base.model_copy(
            update={
                "source": "llm",
                "element": made.element,
                "name_zh": made.name_zh,
                "concept": made.concept,
                "cast_flavor": made.cast_flavor,
                "prompt_version": made.prompt_version,
            }
        )

    def offer(library: ContentLibrary, request: OfferGenRequest) -> OfferGen:
        proposer = provider.proposer(library)
        if proposer is None:
            return OfferGen(key=request.key)
        with use_proposer(proposer):
            made = make_offer(
                library,
                request.run.model_copy(update={"llm": True}),
                "complete",
                region_keywords=request.region_keywords,
                tier_bonus=request.tier_bonus,
                pinned_keyword=request.pinned_keyword,
                region=request.region,
                llm_max_calls=OPPORTUNITY_LLM_CARDS,  # 6L-2b：每份最多 1 張請 LLM
            )
        if not any(t.source == "llm" for t in made.tags):
            return OfferGen(key=request.key)
        return OfferGen(key=request.key, source="llm", offer=made)

    return Generators(flash=flash, story=story, offer=offer)


# ---------------------------------------------------------------------------
# 預測
# ---------------------------------------------------------------------------


def flash_wait_request(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    choice: FlashChoice,
    *,
    anywhere: bool = False,
) -> FlashGenRequest | None:
    """這一次閃現（或重閃）出題會用的生成請求；出題本身不合法（不在城鎮營火、點數不足、不能閃）
    時 ``None``（同 ``growth._flash_source`` 的判斷）。``anywhere``（6L-2b 預測用）：不看地點——
    戰鬥結束、那招可以閃了就開始，走回城鎮的路上也在生成（出題的輸入不含地點，鍵相同）。"""
    busy = char.pending_flash is not None or char.pending_encounter is not None
    # OB-3（#150 第 6 點）：開局還沒結束的角色 4 級前不能閃現，預先生成也跳過（不白打 LLM）
    if busy or flash_blocked_zh(char) is not None:
        return None
    if not anywhere and not at_service(library, char):
        return None
    lib = char_library(library, char)
    run = as_run(char, seed=skill_seed(world, char))
    if run.insight < lib.flash.pricing.rule(choice.category is not None).cost:
        return None
    if choice.skill not in (*run.hero.skills, *run.bench):
        return None
    if problem_of(lib, run, choice.skill, choice.slot) is not None:
        return None
    return world_flash_request(lib, char, run, choice, skill_region(char, choice.skill))


def _flash_requests(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> list[GenRequest]:
    out: list[GenRequest] = []
    for skill in char.hero.skills:
        if len(out) >= FLASH_LIMIT:
            break
        request = flash_wait_request(library, world, char, FlashChoice(skill=skill), anywhere=True)
        if request is not None:
            out.append(request)
    return out


def _story_requests(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> list[GenRequest]:
    out: list[GenRequest] = []
    owned = {*char.hero.skills, *char.bench}
    table = library.world_quests.quests.get(char.region)
    for state in char.quests:
        quest = None if state.done else quest_def(library, char.region, state.quest)
        if quest is None or table is None:
            continue
        # 6L-2b：接到任務就開始——找還沒做的步驟裡第一個給劇情技能的（不只下一步）
        ahead = quest.steps[state.steps_done :]
        at = next((i for i, s in enumerate(ahead) if s.reward.story_skill is not None), None)
        if at is None:
            continue
        skill_id = ahead[at].reward.story_skill
        if skill_id is None or skill_id in owned:
            continue
        base = table.story_skill_by_id().get(skill_id)
        if base is None:
            continue
        xp = sum(  # 做到那一步為止各步的經驗（可能升級、換階級）
            rules_of(library).xp.xp_for(s.reward.xp_source, s.reward.xp_level)
            for s in ahead[: at + 1]
            if s.reward.xp_source is not None
        )
        chars = [char]
        if xp > 0:
            chars.append(gain_xp(library, world, char, xp)[0])
        keys: set[str] = set()
        for who in chars:
            request = story_request(library, who, story_base(library, who, base), who.region)
            if request.key not in keys and len(out) < STORY_LIMIT:
                keys.add(request.key)
                out.append(request)
    return out


def opportunity_wait_request(
    library: ContentLibrary, world: WorldState, char: CharacterState, index: int
) -> OfferGenRequest | None:
    """選第 ``index`` 個解法會用的機遇生成請求；不是可用的機遇解法時 ``None``（同
    ``solutions._check`` 與 ``solutions._opportunity_offer``）。"""
    trigger = char.pending_event
    if trigger is None or trigger.skeleton in char.opportunities:
        return None
    if char.pending_encounter is not None:
        return None
    table = library.world_event_content.events.get(trigger.region)
    skeleton = None if table is None else table.skeleton_by_id().get(trigger.skeleton)
    if skeleton is None or not 0 <= index < len(skeleton.solutions):
        return None
    solution = skeleton.solutions[index]
    if solution.kind != "opportunity" or not opportunity_available(library, char, solution):
        return None
    keyword = solution.requires_keyword
    bonus = opportunity_tier_bonus(library, world, char, trigger.skeleton)
    run = as_run(char, seed=skill_seed(world, char)).model_copy(
        update={"offers_made": char.offers_made}
    )
    key = offer_key(
        world_library(library),
        run,
        "complete",
        region_keywords=() if keyword is None else (keyword,),
        tier_bonus=bonus,
        pinned_keyword=keyword,
        region=trigger.region,
    )
    if key is None:
        return None
    return opportunity_request(
        char, run, key, keyword=keyword, tier_bonus=bonus, region=trigger.region
    )


def _opportunity_requests(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> list[GenRequest]:
    trigger = char.pending_event
    table = None if trigger is None else library.world_event_content.events.get(trigger.region)
    skeleton = (
        None if table is None or trigger is None else table.skeleton_by_id().get(trigger.skeleton)
    )
    out: list[GenRequest] = []
    for index in range(0 if skeleton is None else len(skeleton.solutions)):
        if len(out) >= OPPORTUNITY_LIMIT:
            break
        request = opportunity_wait_request(library, world, char, index)
        if request is not None and all(r.key != request.key for r in out):
            out.append(request)
    return out


def predicted_requests(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> list[GenRequest]:
    """角色目前看得到、之後可能會打開的生成請求（見模組說明；各入口有上限）。"""
    return [
        *_flash_requests(library, world, char),
        *_story_requests(library, world, char),
        *_opportunity_requests(library, world, char),
    ]


# ---------------------------------------------------------------------------
# 暫存區與單一佇列
# ---------------------------------------------------------------------------


def _slot(request: GenRequest) -> str:
    """暫存區的鍵（6L-2c）：閃現不含用法統計（:func:`~trpg.world.generated.flash_pregen_key`），
    同一招同一次出題只會有一筆——打完一場統計變了也不重開；其他入口就是請求的鍵。"""
    if isinstance(request, FlashGenRequest):
        return flash_pregen_key(request.character_id, request.request)
    return request.key


@dataclass(slots=True)
class _Entry:
    request: GenRequest
    target: str | None
    """閃現的技能 ID（等待提示用）；其他入口為 ``None``。"""
    future: Future[FlashGen | StoryGen | OfferGen | None]
    deadline: float | None = None
    order: int = 0


class PregenWaitRequest(BaseModel):
    """``POST .../pregen/wait``：``kind`` 是要打開的入口；閃現另給技能、重閃欄位與指定類別。"""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["flash", "opportunity"]
    skill: str | None = None
    slot: int | None = None
    category: str | None = None
    solution: int | None = None
    """機遇：事件的第幾個解法（同 ``event_solve`` 的 ``solution``）；不是機遇解法＝不用等。"""


class PregenWaitOut(BaseModel):
    """``status``：``ready``＝好了；``timeout``＝等滿 10 秒還沒好（會改給組合器或模板版）；
    ``none``＝沒有要等的（沒有預先生成，或這次不會呼叫 LLM）；``off``＝模型關閉。"""

    status: Literal["ready", "timeout", "none", "off"]
    waited_s: float = 0.0


@dataclass
class WorldPregen:
    """背景預先生成與暫存區（見模組說明）。``enabled`` 每次都問（世界的 LLM 開關與健康檢查）。"""

    generators: Generators
    enabled: Callable[[], bool]
    clock: Callable[[], float] = time.monotonic
    wait_seconds: float = WAIT_SECONDS
    story_wait_seconds: float = STORY_WAIT_SECONDS
    poll_seconds: float = _POLL_SECONDS
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _entries: dict[tuple[str, str], _Entry] = field(default_factory=dict)
    _pool: ThreadPoolExecutor | None = None
    _order: int = 0
    _closed: bool = False
    calls: int = 0
    """實際送出的生成次數（測試與統計用）。"""

    # -- 預測與排隊 -----------------------------------------------------------

    def prefetch(self, library: ContentLibrary, world: WorldState, char: CharacterState) -> None:
        """依目前狀態預測並排隊；這個角色沒有再被預測到的舊結果丟掉。模型關閉時全部丟掉。"""
        cid = char.character_id
        if self._closed or not self.enabled():
            self.forget(cid)
            return
        try:
            requests = predicted_requests(library, world, char)
        except Exception:  # 預測只是加速；出錯就不預先生成
            _LOG.exception("預先生成的預測失敗（%s）", cid)
            return
        view = world_library(library)
        wanted = {_slot(r) for r in requests}
        with self._lock:
            for key in [k for k in self._entries if k[0] == cid and k[1] not in wanted]:
                self._entries.pop(key).future.cancel()
            for request in requests:
                if (cid, _slot(request)) not in self._entries:
                    self._submit(view, request)
            self._trim()

    def forget(self, character_id: str) -> None:
        """丟掉這個角色全部的暫存（沒開始的取消；做到一半的結果之後丟掉）。"""
        with self._lock:
            for key in [k for k in self._entries if k[0] == character_id]:
                self._entries.pop(key).future.cancel()

    def _target(self, request: GenRequest) -> str | None:
        if isinstance(request, FlashGenRequest):
            return request.request.current.id if request.request.current else None
        return None

    def _submit(self, view: ContentLibrary, request: GenRequest) -> _Entry:
        """（持鎖）排進單一佇列。"""
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trpg-pregen")
        future = self._pool.submit(self._run, view, request)
        self._order += 1
        entry = _Entry(request, self._target(request), future, order=self._order)
        self._entries[(request.character_id, _slot(request))] = entry
        return entry

    def _trim(self) -> None:
        """（持鎖）超過上限時丟掉最舊、還沒開始的。"""
        while len(self._entries) > QUEUE_LIMIT:
            idle = sorted((e.order, k) for k, e in self._entries.items() if not e.future.running())
            if not idle:
                return
            self._entries.pop(idle[0][1]).future.cancel()

    def _run(
        self, view: ContentLibrary, request: GenRequest
    ) -> FlashGen | StoryGen | OfferGen | None:
        """背景執行緒：真正呼叫 LLM（單一佇列，一次一個）。出錯＝``None``（降級）。"""
        if not self.enabled():
            return None
        self.calls += 1
        try:
            if isinstance(request, FlashGenRequest) and self.generators.flash is not None:
                return self.generators.flash(view, request)
            if isinstance(request, StoryGenRequest) and self.generators.story is not None:
                return self.generators.story(view, request)
            if isinstance(request, OfferGenRequest) and self.generators.offer is not None:
                return self.generators.offer(view, request)
        except Exception:
            _LOG.exception("預先生成失敗（%s），改用組合器、模板或內容版", request.key)
        return None

    # -- 等待 -----------------------------------------------------------------

    def _await(self, entry: _Entry) -> tuple[FlashGen | StoryGen | OfferGen | None, bool]:
        """等這一筆（不持鎖）：回傳（結果, 有沒有逾時）。``deadline`` 從第一次等待算起。"""
        with self._lock:
            if entry.deadline is None:
                limit = (
                    self.story_wait_seconds
                    if entry.request.kind == "story_skill"
                    else self.wait_seconds
                )
                entry.deadline = self.clock() + limit
            deadline = entry.deadline
        while not entry.future.done():
            if self.clock() >= deadline:
                return None, True
            concurrent.futures.wait([entry.future], timeout=self.poll_seconds)
        if entry.future.cancelled():
            return None, False
        try:
            return entry.future.result(), False
        except Exception:
            return None, False

    def supplier(self, library: ContentLibrary) -> Supplier:
        """給世界引擎的供應者（:func:`trpg.world.generated.using_generated`）：好了就給、沒好就等
        （最多 10 秒），給出去的那一筆從暫存區拿掉。沒預測到的請求當場排進佇列再等。"""

        def supply(request: GenRequest) -> FlashGen | StoryGen | OfferGen | None:
            if self._closed or not self.enabled():
                return None
            key = (request.character_id, _slot(request))
            with self._lock:
                entry = self._entries.get(key)
                if entry is None:
                    entry = self._submit(world_library(library), request)
            result, _late = self._await(entry)
            with self._lock:
                if self._entries.get(key) is entry:
                    del self._entries[key]
            if isinstance(result, FlashGen) and result.key != request.key:
                # 6L-2c：暫存區的鍵不含用法統計；給出去時改成按下那一刻的鍵（引擎比對鍵、日誌依它
                # 重播）。內容是開始生成時那份統計做的，引擎照樣逐一驗證、套不上的用模板補。
                result = result.model_copy(update={"key": request.key})
            return result

        return supply

    def wait(
        self,
        character_id: str,
        kind: Kind,
        request: GenRequest | None = None,
        *,
        library: ContentLibrary | None = None,
    ) -> PregenWaitOut:
        """等待提示用（不持世界的鎖）：等這個角色 ``kind`` 的那一筆好了或逾時。``request`` 給了就
        找同一把鍵（沒有時排進佇列）；沒給就找這個角色這一種的任一筆。"""
        if self._closed or not self.enabled():
            return PregenWaitOut(status="off")
        start = self.clock()
        with self._lock:
            entry: _Entry | None = None
            if request is not None:
                entry = self._entries.get((character_id, _slot(request)))
                if entry is None and library is not None:
                    entry = self._submit(world_library(library), request)
            else:
                found = sorted(
                    (e.order, k)
                    for k, e in self._entries.items()
                    if k[0] == character_id and e.request.kind == kind
                )
                entry = self._entries[found[0][1]] if found else None
        if entry is None:
            return PregenWaitOut(status="none")
        result, late = self._await(entry)
        waited = round(max(0.0, self.clock() - start), 3)
        if late:
            return PregenWaitOut(status="timeout", waited_s=waited)
        return PregenWaitOut(status="ready" if result is not None else "none", waited_s=waited)

    def pending(self, character_id: str) -> int:
        """這個角色暫存區裡還沒好的筆數。"""
        with self._lock:
            return sum(
                1 for k, e in self._entries.items() if k[0] == character_id and not e.future.done()
            )

    def drain(self, timeout: float | None = None) -> None:
        """等目前排隊的工作做完（測試用）。"""
        with self._lock:
            futures = [e.future for e in self._entries.values()]
        concurrent.futures.wait(futures, timeout=timeout)

    def shutdown(self) -> None:
        """不再接新工作，排隊中的取消（伺服器關閉時）。"""
        with self._lock:
            pool, self._pool = self._pool, None
            self._closed = True
            for entry in self._entries.values():
                entry.future.cancel()
            self._entries.clear()
        if pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)
