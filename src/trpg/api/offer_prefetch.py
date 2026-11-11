"""大世界三選一的背景預先計算（PERF-3，玩法 PM 2026-11-03）。

完整技能三選一要算 1～3 秒。世界引擎（純函式）在玩家選機遇解法、或完成帶三選一的劇情步驟時才呼叫
:func:`~trpg.roguelite.offers.make_offer`；這一層在**機遇與劇情步驟一出現**（每個世界動作之後、
角色第一次從存檔讀進來時）就預測那一次呼叫的參數，丟到背景執行緒先算，結果放進
:class:`~trpg.roguelite.offers.OfferCache`。

- 世界引擎的呼叫包在 :func:`~trpg.roguelite.offers.using_offer_cache` 裡：快取的鍵是候選產生器的
  **完整輸入**（角色技能、屬性、裝備、行為、階級、種子、第幾組、區域偏向、高 1 階…，
  :func:`~trpg.roguelite.offers.offer_key`），所以命中的結果一定和同步計算逐字相同；預測錯了
  （例如玩家中間換了裝備）只是沒命中，照舊同步算。
- 背景還在算同一把鍵時，同步呼叫等它算完（比同時再算一次快；結果相同）。
- 預測：
  - 機遇：``pending_event`` 的骨架有可用的機遇解法（條件成立、這季還沒拿過）→ 照
    ``solutions._opportunity`` 的參數（``requires_keyword`` 當區域偏向與指定關鍵字〔5B-4d〕、
    ``opportunity_tier_bonus``）。
  - 劇情步驟：每個進行中任務的下一步有 ``reward.offer`` → 照 ``quests._offer`` 的參數；另外再算
    一份「加上這一步經驗之後」的角色（升級可能換階級；鍵相同時只算一次）。
- 只在 API 層；世界引擎、roguelite 與候選產生器都不知道背景執行緒的存在。
"""

from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.roguelite.offers import OfferCache, make_offer, offer_key, using_offer_cache
from trpg.roguelite.state import RunState, SkillOffer
from trpg.world.common import rules_of
from trpg.world.growth import as_run, gain_xp, skill_seed, world_library
from trpg.world.quests import defers_offer, offer_bias, quest_def
from trpg.world.situations import opportunity_available
from trpg.world.solutions import opportunity_tier_bonus
from trpg.world.state import CharacterState, WorldState

__all__ = ["OfferJob", "OfferPrefetcher", "predicted_offers"]


@dataclass(frozen=True, slots=True)
class OfferJob:
    """一次預測的 :func:`make_offer` 呼叫（參數與世界引擎的呼叫相同）。"""

    run: RunState
    reason: Literal["level_up", "complete"]
    region_keywords: tuple[str, ...] = ()
    mix: tuple[int, int, int] | None = None
    min_passive: int = 0
    tier_bonus: int = 0
    pinned_keyword: str | None = None
    region: str | None = None

    def key(self, view: ContentLibrary) -> str | None:
        return offer_key(
            view,
            self.run,
            self.reason,
            region_keywords=self.region_keywords,
            mix=self.mix,
            min_passive=self.min_passive,
            tier_bonus=self.tier_bonus,
            pinned_keyword=self.pinned_keyword,
            region=self.region,
        )

    def make(self, view: ContentLibrary) -> SkillOffer:
        return make_offer(
            view,
            self.run,
            self.reason,
            region_keywords=self.region_keywords,
            mix=self.mix,
            min_passive=self.min_passive,
            tier_bonus=self.tier_bonus,
            pinned_keyword=self.pinned_keyword,
            region=self.region,
        )


def _run_of(world: WorldState, char: CharacterState) -> RunState:
    """世界引擎給三選一用的 ``RunState``（``solutions._opportunity``、``quests._offer`` 同一個
    寫法）。"""
    return as_run(char, seed=skill_seed(world, char)).model_copy(
        update={"offers_made": char.offers_made}
    )


def _opportunity_jobs(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> list[OfferJob]:
    trigger = char.pending_event
    if trigger is None or trigger.skeleton in char.opportunities:
        return []
    table = library.world_event_content.events.get(trigger.region)
    skeleton = None if table is None else table.skeleton_by_id().get(trigger.skeleton)
    if skeleton is None:
        return []
    jobs: list[OfferJob] = []
    for solution in skeleton.solutions:
        if solution.kind != "opportunity" or not opportunity_available(library, char, solution):
            continue
        keyword = solution.requires_keyword
        jobs.append(
            OfferJob(
                _run_of(world, char),
                "complete",
                region_keywords=() if keyword is None else (keyword,),
                tier_bonus=opportunity_tier_bonus(library, world, char, trigger.skeleton),
                pinned_keyword=keyword,
                region=trigger.region,
            )
        )
    return jobs


def _quest_jobs(library: ContentLibrary, world: WorldState, char: CharacterState) -> list[OfferJob]:
    jobs: list[OfferJob] = []
    for state in char.quests:
        quest = None if state.done else quest_def(library, char.region, state.quest)
        if quest is None or state.steps_done >= len(quest.steps):
            continue
        reward = quest.steps[state.steps_done].reward
        offer = reward.offer
        if offer is None or defers_offer(char, quest):  # OB-2：入門期的新手三選一不當場出題
            continue
        chars = [char]
        if reward.xp_source is not None:  # 完成這一步先加經驗（可能升級、換階級）
            xp = rules_of(library).xp.xp_for(reward.xp_source, reward.xp_level)
            chars.append(gain_xp(library, world, char, xp)[0])
        for who in chars:
            jobs.append(
                OfferJob(
                    _run_of(world, who),
                    "complete" if offer.kind == "complete" else "level_up",
                    region_keywords=offer_bias(library, char.region, quest, offer),
                    mix=None if offer.mix is None else offer.mix.as_tuple(),
                    min_passive=offer.min_passive,
                    region=char.region,
                )
            )
    return jobs


def predicted_offers(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> list[OfferJob]:
    """角色目前看得到的機遇與劇情步驟，之後會呼叫的三選一（見模組說明）。"""
    return [*_opportunity_jobs(library, world, char), *_quest_jobs(library, world, char)]


class OfferPrefetcher:
    """背景預先計算（一條背景執行緒；見模組說明）。``enabled`` 為假時只提供快取、不在背景算。"""

    def __init__(self, library: ContentLibrary, *, enabled: bool = True, limit: int = 64) -> None:
        self.library = library
        self.enabled = enabled
        self.cache = OfferCache(limit)
        self._lock = threading.Lock()
        self._pool: ThreadPoolExecutor | None = None
        self._futures: list[Future[None]] = []

    @property
    def view(self) -> ContentLibrary:
        """世界引擎呼叫 ``make_offer`` 用的內容庫視圖（同一個物件，快取靠物件身分對應）。"""
        return world_library(self.library)

    def prefetch(self, world: WorldState, char: CharacterState) -> list[Future[None]]:
        """把預測到、快取裡還沒有的三選一丟到背景算；回傳這次丟出去的工作。預測本身出錯時不丟
        （之後照舊同步算，錯誤會在那裡照常回報）。"""
        if not self.enabled:
            return []
        view = self.view
        try:
            jobs = predicted_offers(self.library, world, char)
        except Exception:  # 預測只是加速；出錯就不預先算
            return []
        submitted: list[Future[None]] = []
        seen: set[str] = set()
        for job in jobs:
            key = job.key(view)
            if key is None or key in seen or self.cache.has(view, key):
                continue
            seen.add(key)
            submitted.append(self._submit(view, job))
        return submitted

    def _submit(self, view: ContentLibrary, job: OfferJob) -> Future[None]:
        with self._lock:
            if self._pool is None:
                self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trpg-offer")
            future = self._pool.submit(self._compute, view, job)
            self._futures = [f for f in self._futures if not f.done()] + [future]
            return future

    def _compute(self, view: ContentLibrary, job: OfferJob) -> None:
        with using_offer_cache(self.cache):
            job.make(view)

    def wait(self, timeout: float | None = None) -> None:
        """等目前丟出去的背景工作做完（測試用）。"""
        with self._lock:
            pending = list(self._futures)
        for future in pending:
            future.exception(timeout=timeout)

    def shutdown(self) -> None:
        """不再接新工作，排隊中的取消（伺服器關閉時）。"""
        with self._lock:
            pool, self._pool = self._pool, None
            self.enabled = False
        if pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)
