"""共用候選產生器：加深、橋接、新方向（Phase 3-24b2，``docs/design/06-技能.md`` 6.27.4）。

所有技能來源（升級三選一〔測試原型〕、之後的任務、機遇、許願池）共用這個 **純函式**：

- 輸入（:class:`CandidateRequest`）：玩家持有技能的 **關鍵字分布**、目前 **武器大類**、**行為紀錄**
  （用過的動作類型與次數）、**種子**、候選技能的 **階級**、要排除的技能 ID。
- 輸出：最多三個 :class:`Candidate`，依序是

  | 種類 | 定義 |
  |---|---|
  | ``deepen`` 加深 | 帶玩家持有最多的關鍵字 |
  | ``bridge`` 橋接 | 同時帶玩家已持有的兩個關鍵字 |
  | ``new`` 新方向 | 帶玩家還沒有的關鍵字 |

- 來源：關鍵字技能池（內容庫的手寫技能，階級相符、非傳說、與武器相容）或隨機組合器（指定關鍵字）。
  每個候選以 ``composer_share_permille`` 決定先找哪個來源，找不到再換另一個。

**只看專屬規則**（PM 決定，3-24b1 待決 #2）：關鍵字分布與「技能帶某關鍵字」都以
``derive_keywords(..., exclusive_only=True)`` 判斷；通用規則只影響卡片顯示。

**通用池**（Phase 3-51，玩法決定 #55）：沒有任何關鍵字的手寫技能是基礎技能；「新方向」那一格有
``general_share_permille`` 的機率從通用池抽（候選的 ``keywords`` 為空）。

**退回**（定義做不到時，``Candidate.fallback`` 為真）：

- 持有 0 個關鍵字：加深與橋接都退回新方向（各自帶一個不同的、還沒有的關鍵字）。
- 持有 1 個關鍵字：橋接退回「持有的關鍵字 ＋ 一個還沒有的關鍵字」（向外橋接）；仍找不到就只帶持有的
  關鍵字。
- 加深找不到持有最多的關鍵字的技能時，依持有數往下找；新方向找不到時換另一個還沒有的關鍵字。
- 全部來源都找不到時少給（極少發生）。

**行為紀錄**：關鍵字的 ``actions``（``skill_keywords.yaml``，例如攀跳 → 高處）與玩家用過的動作次數
相乘當權重：加深在持有數並列時偏向行為相符的關鍵字；新方向抽關鍵字時，行為相符的權重較高。

**同路線找法**（BAL-19g，06 6.27.4，玩法決定 #110）：加深、橋接依序找 ① 帶同關鍵字、縮放屬性跟
主路線的技能（武器技看武器）→ ② 帶同關鍵字的雙屬性技能（第二縮放屬性跟上主路線，6.10）→ ③ 放寬
關鍵字（換下一個關鍵字，再照 ①②）→ ④ 最後才給不跟主屬性的技能（三選一標偏離）。判定見
:func:`route_rank`，三選一的 ``off_route`` 用同一個判定（:func:`follows_attr`）。

**跟主屬性**（Phase 3H-3，07 7.2）：``CandidateRequest.hero_attributes`` 有值時，加深與橋接優先取
縮放屬性＝主角最高屬性的技能（技能池只看 ``scaling_attr``；隨機組合器的技能縮放屬性直接跟著最高
屬性，限在 ``skill_scaling.yaml`` 允許範圍內），**新方向保留給不同屬性**（組合器取允許範圍內次高
的）；偏好湊不到時放寬（取同來源的備選），所以候選數量不變。最高屬性同分依六屬性順序
（:func:`trpg.shared.types.top_attribute`）。

**橋接搜尋上限**（PERF-3，玩法 PM 2026-11-03）：橋接的多關鍵字選項共用
``bridge_variant_cap`` 個組合器種子變體；用完還沒找到就跳過剩下的多關鍵字選項，照 ③ 放寬關鍵字
（單一關鍵字，``fallback`` 為真）。指定關鍵字的組合不抽傳說
（:mod:`trpg.skillgen.random_composer`）。

**指定關鍵字**（Phase 5B-4d，07 7.6 機遇「關鍵字由觸發情境決定」）：
``CandidateRequest.pinned_keyword``
有值時三張都帶它——加深＝只帶它；橋接＝它＋另一個持有的關鍵字；新方向＝它＋一個還沒有的關鍵字
（區域偏向排前）；多關鍵字找不到時退回只帶它（``fallback``）。橋接、新方向的多關鍵字選項各自受
``bridge_variant_cap`` 管；不從通用池抽。``None`` ＝ 原行為（逐字不變）。
橋接的「另一個持有的關鍵字」也是區域偏向排前（TXT-2，許願池兩個關鍵字：``region_keywords`` 的
第 2 個已持有時，橋接先試「第 1＋第 2」，還沒有時新方向先試，所以組合器做得到時有一張同時帶兩個；
其他呼叫端的 ``region_keywords`` 只有指定關鍵字本身，順序不變）。

**LLM 來源**（Phase 4-L6，``docs/phases/Phase4計畫.md`` 3F 節）：呼叫端傳入 ``llm``
（:data:`~trpg.skillgen.proposal_topic.LlmProposer`）時，每個候選種類先以
``llm_share_permille`` 的機率
請 LLM 提議（題目由 :func:`~trpg.skillgen.proposal_topic.make_topic` 決定：核心原語依種子與
``llm_uses`` 配額加權抽出、輪替選單、主題詞）；每種候選最多呼叫一次，失敗（含 3 次重試後退回）就照
上面的退回順序走組合器與技能池，所以候選仍湊滿。沒有傳 ``llm`` 時行為與之前逐字相同（擲骰用獨立的
``fork``，不消耗其他亂數）。``Candidate.llm`` 記錄這次嘗試（成功或失敗），供 run 紀錄與退回率統計。

確定性：亂數只來自 ``Rng(request.seed).fork(<種類>)``；同樣的輸入必得同樣的候選。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from itertools import combinations
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.player_pool import in_region_pool, player_skills
from trpg.content.skills import SkillDef, weapon_problem
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, top_attribute
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.proposal_topic import LlmProposer, TopicRequest, make_topic
from trpg.skillgen.random_composer import (
    KEYWORD_TRIES,
    ComposeError,
    KeywordExhaustedError,
    compose_with_stats,
)
from trpg.skillgen.validate import minimum_tier

__all__ = [
    "BRIDGE_VARIANT_CAP",
    "CANDIDATE_KINDS",
    "ROUTE_DUAL",
    "ROUTE_MAIN",
    "ROUTE_OFF",
    "Candidate",
    "CandidateKind",
    "CandidateRequest",
    "CandidateRules",
    "LlmTrace",
    "behavior_weights",
    "follows_attr",
    "generate_candidates",
    "keyword_distribution",
    "new_direction_keywords",
    "region_first",
    "route_rank",
    "skill_has_keywords",
]

type AttrWant = Literal["same", "other"]
"""候選對縮放屬性的偏好（Phase 3H-3）：``same`` ＝ 主角最高的屬性（加深、橋接），``other`` ＝ 不同的
屬性（新方向）。"""

type CandidateKind = Literal["deepen", "bridge", "new"]
type _Graded = list[SkillDef | None]
"""依好壞（:meth:`_Search._grade`）分的三格：完全符合、雙屬性、備選；各格最多一招。"""
CANDIDATE_KINDS: tuple[CandidateKind, ...] = ("deepen", "bridge", "new")


BRIDGE_VARIANT_CAP = 400
"""橋接搜尋的種子變體數上限（PERF-3，玩法 PM 2026-11-03：照「最壞約 3 秒」定；見
``docs/phases/PERF-3報告.md``）。橋接的多關鍵字選項（兩個持有的關鍵字、往外一步）共用這個上限；
到上限還沒找到就照 06 6.27.4 ③ 放寬關鍵字（改試單一關鍵字），所以候選不會少。0 ＝ 不設上限。"""


@dataclass(frozen=True, slots=True)
class CandidateRules:
    """產生器的參數（roguelite 取自 ``roguelite.yaml`` 的 ``candidates``）。"""

    composer_share_permille: int = 500
    composer_tries: int = 8
    general_share_permille: int = 100
    """「新方向」那一格從通用池（基礎技能）抽的機率（‰；Phase 3-51，玩法決定 #55）。"""
    llm_share_permille: int = 0
    """有傳 ``llm`` 時，每個候選先請 LLM 提議的機率（‰；Phase 4-L6）。"""
    llm_theme_permille: int = 0
    """LLM 題目帶主題詞的機率（‰；Phase 4-L6）。"""
    llm_reaction_permille: int = 0
    """LLM 題目出反應技的機率（‰；Phase 4-L8b）；0 ＝ 一律主動技能。"""
    bridge_variant_cap: int = BRIDGE_VARIANT_CAP
    """橋接多關鍵字搜尋的組合器變體數上限（PERF-3，:data:`BRIDGE_VARIANT_CAP`）；0 ＝ 不設。"""
    llm_max_calls: int = 0
    """一份候選最多請 LLM 幾次（6L-2b：大世界機遇每份最多 1 張）；0 ＝ 不設（每種候選各一次，
    roguelite 照舊）。擲到請 LLM 的種類依「加深 → 橋接 → 新方向」的順序先到先用，其餘走組合器。"""


@dataclass(frozen=True, slots=True)
class CandidateRequest:
    """產生器的輸入。``keyword_counts``：關鍵字 ID → 持有幾招帶該關鍵字的技能（見
    :func:`keyword_distribution`）；``behavior``：動作類型 → 用過的次數；``weapon_class``：
    ``melee``／``ranged``／``focus``。"""

    keyword_counts: Mapping[str, int]
    weapon_class: str
    seed: int
    tier: int
    behavior: Mapping[str, int] = field(default_factory=dict)
    exclude: frozenset[str] = frozenset()
    """不能出現的技能 ID（玩家已持有的）。"""
    hero_attributes: Mapping[Attribute, int] = field(default_factory=dict)
    """主角目前的六屬性（Phase 3H-3，07 7.2）。有值時：加深與橋接的候選優先取縮放屬性＝最高屬性的
    技能（同分依六屬性順序），新方向優先取不同屬性的技能；找不到再放寬。隨機組合器產生的技能
    縮放屬性直接跟著最高屬性（:func:`trpg.skillgen.scaling.retarget_scaling`）。空 ＝ 不看屬性
    （與 3H-3 之前完全相同）。"""
    weapon_attrs: tuple[Attribute, ...] = ()
    """主角手上武器的縮放屬性（含第二縮放屬性；Phase 3H-7）。武器技看手上武器（3H-6），所以比對
    屬性偏好時武器技用這個，不用技能自己的 ``scaling_attr``（只是顯示提示）；空 ＝ 退回技能的。"""
    llm_uses: Mapping[str, int] = field(default_factory=dict)
    """run 內配額（Phase 4-L6）：原語 → 已出現在這一輪候選中的次數（核心原語抽籤的權重折減）。"""
    held: Mapping[str, str] = field(default_factory=dict)
    """主角手上的主手武器與副手（ID → 中文名；Phase 3I-5）：限定武器的招牌技只在拿著那種武器時
    才會出現在候選裡；隨機組合器的武器親和條件也只挑拿著的那一種。空 ＝ 不給限定武器的技能。"""
    region_keywords: tuple[str, ...] = ()
    """區域偏向（Phase 5B-4b，07 7.6「區域任務鏈偏向該區的關鍵字」）：「新方向」挑關鍵字時，玩家
    還沒有的區域關鍵字排在前面（:func:`region_first`）。空 ＝ 不偏向（原型 roguelite）。"""
    region: str | None = None
    """技能取得地點的區域（#126，06 6.34.7）：只進 LLM 題目的 prompt（名稱與描述照該區風格），
    不影響候選與數值。``None``＝中性（創角、許願池、測試原型）。"""
    mix: tuple[int, int, int] = (1, 1, 1)
    """白板三選一的組成（加深、橋接、新方向各幾張；Phase 5B-4b，07 7.6 新手鏈 1／0／2）。只有白板版
    產生器（:mod:`trpg.skillgen.whiteboard_candidates`）看；預設 1／1／1 ＝ 原行為。"""
    min_passive: int = 0
    """白板三選一至少幾張被動（Phase 5B-4b，07 7.6 新手鏈「至少 1 招被動」）。0 ＝ 原行為。"""
    pinned_keyword: str | None = None
    """指定關鍵字（Phase 5B-4d，07 7.6 機遇「關鍵字由觸發情境決定」）：三張候選都帶它（見模組
    說明）。只有完整版產生器看；``None`` ＝ 原行為。"""


@dataclass(frozen=True, slots=True)
class Candidate:
    """一個候選：種類、它要帶的關鍵字、技能、來源；``fallback`` 表示定義做不到而退回。"""

    kind: CandidateKind
    keywords: tuple[str, ...]
    skill: SkillDef
    source: Literal["pool", "composer", "llm"]
    fallback: bool = False
    llm: LlmTrace | None = None
    """這個種類請過 LLM 時的紀錄（成功 ``ok``，或失敗後改走組合器／技能池）。"""


@dataclass(frozen=True, slots=True)
class LlmTrace:
    """一次 LLM 提議的紀錄（Phase 4-L6）：題目（關鍵字、稀有度、核心原語、選單種子、主題）、
    嘗試次數、
    錯誤代碼、是否成功（``ok``）與失敗原因。寫進 run（``OfferTag``），重播與讀檔不再呼叫 LLM。"""

    keywords: tuple[str, ...]
    rarity: str
    core_primitive: str | None
    menu_seed: int | None
    theme: str | None
    attempts: int
    ok: bool
    codes: tuple[str, ...] = ()
    reason: str | None = None
    name_source: Literal["llm", "fallback"] | None = None
    name_attempts: int = 0
    name_codes: tuple[str, ...] = ()
    prompt_version: str | None = None
    naming_prompt_version: str | None = None


def keyword_distribution(skills: Iterable[SkillDef], library: ContentLibrary) -> dict[str, int]:
    """持有技能的關鍵字分布（只看專屬規則；一招技能對每個關鍵字最多算 1）。依推導表順序，只列
    出現過的關鍵字。"""
    counts: Counter[str] = Counter()
    for skill in skills:
        counts.update(derive_keywords(skill, library.keywords, exclusive_only=True).all())
    return {k: counts[k] for k in library.keywords.ids() if counts[k] > 0}


def new_direction_keywords(library: ContentLibrary, held: Sequence[str]) -> list[str]:
    """還沒有、可以當「新方向」出題的關鍵字（推導表順序）：排除 ``start_hidden``（KW-1：池子補齊
    前不主動出題；持有這種關鍵字的技能時，加深、橋接照常）。"""
    offered = set(library.keywords.start_ids())
    return [k for k in library.keywords.ids() if k not in held and k in offered]


def behavior_weights(library: ContentLibrary, behavior: Mapping[str, int]) -> dict[str, int]:
    """關鍵字 → 行為分數（玩家用過的、與該關鍵字相符的動作次數總和）。"""
    return {
        k.id: sum(behavior.get(action, 0) for action in k.actions)
        for k in library.keywords.keywords
    }


ROUTE_MAIN = 0
"""同路線找法 ①：縮放屬性跟主路線（武器技看手上武器；BAL-19g，06 6.27.4）。"""
ROUTE_DUAL = 1
"""同路線找法 ②：雙屬性技能，靠第二縮放屬性跟上主路線（6.10，武器屬性＋心智屬性）。"""
ROUTE_OFF = 2
"""偏離：不跟主屬性（④，三選一標偏離）。"""


def route_rank(skill: SkillDef, attr: Attribute, weapon_attrs: Sequence[Attribute] = ()) -> int:
    """技能對主路線 ``attr`` 的等級（BAL-19g，06 6.27.4 同路線找法）：:data:`ROUTE_MAIN`、
    :data:`ROUTE_DUAL` 或 :data:`ROUTE_OFF`。

    - 武器技看手上武器的縮放屬性（``weapon_attrs``，含第二屬性；3H-6、3H-7）；武器屬性不合、但
      技能的心智第二屬性是 ``attr``（3I-3）算雙屬性。
    - 法術技看技能的 ``scaling_attr``；第二縮放屬性是 ``attr`` 的雙屬性法術算雙屬性。
    - BAL-17：手上是雙屬性武器（``weapon_attrs`` 有兩個）、且 ``attr`` 是其中之一時，武器的兩個
      屬性都算主路線，法術也一樣（魔導劍：力量最高時，吃力量或智力的技能都算同路線）。"""
    weapon_set = set(weapon_attrs)
    if len(weapon_set) > 1 and attr in weapon_set and skill.category != "weapon":
        if skill.scaling_attr in weapon_set:
            return ROUTE_MAIN
        return ROUTE_DUAL if skill.secondary_scaling_attr in weapon_set else ROUTE_OFF
    if skill.category == "weapon" and weapon_attrs:
        if attr in weapon_set:
            return ROUTE_MAIN
    elif skill.scaling_attr == attr:
        return ROUTE_MAIN
    return ROUTE_DUAL if skill.secondary_scaling_attr == attr else ROUTE_OFF


def follows_attr(skill: SkillDef, attr: Attribute, weapon_attrs: Sequence[Attribute] = ()) -> bool:
    """技能跟主路線 ``attr``（:func:`route_rank` 不是偏離；主路線或雙屬性都算）。候選產生器
    （完整版、白板版）與三選一的偏離標示（``roguelite.offers`` 的 ``off_route``）共用。"""
    return route_rank(skill, attr, weapon_attrs) != ROUTE_OFF


def skill_has_keywords(skill: SkillDef, keywords: Sequence[str], library: ContentLibrary) -> bool:
    """技能（依專屬規則）同時製造或利用 ``keywords`` 的每一個。"""
    found = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    return all(k in found for k in keywords)


# ---------------------------------------------------------------------------
# 來源
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Search:
    library: ContentLibrary
    request: CandidateRequest
    rules: CandidateRules
    pool: tuple[tuple[SkillDef, tuple[str, ...]], ...]
    """可用的手寫技能與它（專屬規則）帶的關鍵字。"""
    taken: set[str]
    llm: LlmProposer | None = None
    kind: CandidateKind = "deepen"
    """目前正在找的候選種類（LLM 來源每種最多請一次）。"""
    llm_done: set[str] = field(default_factory=set)
    traces: dict[str, LlmTrace] = field(default_factory=dict)
    bridge_used: int = 0
    """橋接多關鍵字搜尋已用掉的組合器變體數（PERF-3）。"""
    pinned_new_used: int = 0
    """指定關鍵字模式（5B-4d）新方向的多關鍵字搜尋已用掉的組合器變體數（和橋接各自計）。"""

    def capped(self, keywords: Sequence[str]) -> bool:
        """這次搜尋受變體上限管（PERF-3）：兩個以上的關鍵字、有設上限，而且是橋接（或指定關鍵字
        模式的新方向，5B-4d）。"""
        if len(keywords) <= 1 or self.rules.bridge_variant_cap <= 0:
            return False
        return self.kind == "bridge" or (
            self.kind == "new" and self.request.pinned_keyword is not None
        )

    def used(self) -> int:
        return self.bridge_used if self.kind == "bridge" else self.pinned_new_used

    def spend(self, variants: int) -> None:
        if self.kind == "bridge":
            self.bridge_used += variants
        else:
            self.pinned_new_used += variants

    def exhausted(self, keywords: Sequence[str]) -> bool:
        """變體上限已用完（PERF-3）：剩下的多關鍵字選項跳過，照 6.27.4 ③ 放寬關鍵字。"""
        return self.capped(keywords) and self.used() >= self.rules.bridge_variant_cap

    def from_llm(
        self, keywords: Sequence[str], want: AttrWant | None
    ) -> tuple[SkillDef, Literal["llm"]] | None:
        """請 LLM 提議（每種候選最多一次；擲骰與出題用獨立的 ``fork``，不影響其他亂數）。失敗回傳
        ``None``（呼叫端走組合器與技能池）。"""
        if self.llm is None or self.kind in self.llm_done:
            return None
        cap = self.rules.llm_max_calls
        if cap > 0 and len(self.llm_done) >= cap:  # 6L-2b：這份已經請滿
            return None
        rng = Rng(self.request.seed).fork(f"llm/{self.kind}")
        if not rng.chance_permille(self.rules.llm_share_permille):
            return None
        self.llm_done.add(self.kind)
        attrs = None if want == "other" else (self.request.hero_attributes or None)
        made = make_topic(
            self.library,
            TopicRequest(
                tier=self.request.tier,
                keywords=tuple(keywords),
                seed=rng.next_u32(),
                uses=self.request.llm_uses,
                hero_attributes=attrs,
                held=self.request.held or None,
                theme_permille=self.rules.llm_theme_permille,
                reaction_permille=self.rules.llm_reaction_permille,
                weapon_class=self.request.weapon_class,
                region=self.request.region,
            ),
        )
        if made is None:
            return None
        topic, ctx, seed = made
        result = self.llm(topic, ctx, seed)
        skill = result.skill
        ok = skill is not None and self.usable(skill)
        self.traces[self.kind] = LlmTrace(
            keywords=topic.keywords,
            rarity=topic.rarity,
            core_primitive=topic.core_primitive,
            menu_seed=topic.menu_seed,
            theme=topic.theme,
            attempts=result.attempts,
            ok=ok,
            codes=result.codes,
            reason=result.reason if skill is None else (None if ok else "技能不適用目前的武器"),
            name_source=result.name_source,
            name_attempts=result.name_attempts,
            name_codes=result.name_codes,
            prompt_version=result.prompt_version,
            naming_prompt_version=result.naming_prompt_version,
        )
        if not ok or skill is None:
            return None
        self.taken.add(skill.id)
        return skill, "llm"

    def usable(self, skill: SkillDef) -> bool:
        return (
            skill.rarity != "legendary"  # 傳說技能不當候選（組合器的隨機結果也一樣）
            and skill.id not in self.taken
            and skill.id not in self.request.exclude
            and weapon_problem(skill, self.request.weapon_class, self.request.held) is None
        )

    def _want_ok(self, skill: SkillDef, want: AttrWant | None) -> bool:
        return self._grade(skill, want) == 0

    def _grade(self, skill: SkillDef, want: AttrWant | None) -> int:
        """候選的好壞（小者優先）：0 ＝ 完全符合偏好、1 ＝ 雙屬性技能靠第二屬性跟上主路線（只在
        ``same``；BAL-19g 同路線找法 ②，仍算符合）、2 ＝ 不符合（備選）。"""
        if want is None:
            return 0
        top = top_attribute(self.request.hero_attributes)
        rank = route_rank(skill, top, self.request.weapon_attrs)
        if want == "other":
            return 0 if rank == ROUTE_OFF else 2
        return rank

    def from_pool(self, rng: Rng, keywords: Sequence[str], want: AttrWant | None) -> _Graded:
        """依好壞分組：有完全符合的就從中抽（不再看其他組），否則抽雙屬性的，再否則抽備選。"""
        options = [
            s for s, found in self.pool if all(k in found for k in keywords) and self.usable(s)
        ]
        graded: _Graded = [None, None, None]
        for grade in range(3):
            group = [s for s in options if self._grade(s, want) == grade]
            if group:
                graded[grade] = rng.choice(group)
                break
        return graded

    def from_composer(self, rng: Rng, keywords: Sequence[str], want: AttrWant | None) -> _Graded:
        graded: _Graded = [None, None, None]
        if not keywords:
            return graded
        hint = "spell" if self.request.weapon_class == "focus" else None
        attrs = self.request.hero_attributes or None
        avoid = top_attribute(self.request.hero_attributes) if want == "other" else None
        capped = self.capped(keywords)
        for _ in range(self.rules.composer_tries):
            if self.exhausted(keywords):  # PERF-3：橋接上限用完
                break
            seed = rng.next_u32()
            left = self.rules.bridge_variant_cap - self.used() if capped else KEYWORD_TRIES
            try:
                found = compose_with_stats(
                    seed,
                    tier=self.request.tier,
                    category=hint,
                    library=self.library,
                    keyword=keywords[0],
                    hero_attributes=attrs,
                    avoid_attr=avoid,
                    held=self.request.held or None,
                    keyword_tries=left,
                    skip_legendary=True,  # PERF-3：指定關鍵字的組合不抽傳說（傳說不當候選）
                )
            except KeywordExhaustedError as exc:
                self.spend(exc.variants if capped else 0)
                continue
            except ComposeError:
                continue
            self.spend(found.variants if capped else 0)
            skill = found.skill
            if self.usable(skill) and skill_has_keywords(skill, keywords, self.library):
                grade = self._grade(skill, want)
                if grade == 0:
                    graded[0] = skill
                    return graded
                if graded[grade] is None:
                    graded[grade] = skill
        return graded

    def find(
        self, rng: Rng, keywords: Sequence[str], want: AttrWant | None = None
    ) -> tuple[SkillDef, Literal["pool", "composer", "llm"], bool] | None:
        """（技能, 來源, 是否符合屬性偏好）；不符合偏好的是備選，呼叫端決定要不要用（BAL-17：先換
        關鍵字找符合的，都沒有才用第一個備選）。BAL-19g：同一組關鍵字先找主路線（①），兩個來源
        都沒有才取雙屬性技能（②，仍算符合）。找到的技能由呼叫端 :meth:`accept` 登記（LLM 來源
        已登記）。"""
        want = want if self.request.hero_attributes else None
        from_llm = self.from_llm(keywords, want)
        if from_llm is not None:
            return from_llm[0], from_llm[1], True
        composer_first = rng.chance_permille(self.rules.composer_share_permille)
        order: tuple[Literal["pool", "composer"], ...] = (
            ("composer", "pool") if composer_first else ("pool", "composer")
        )
        seconds: list[tuple[SkillDef, Literal["pool", "composer", "llm"], bool]] = []
        spares: list[tuple[SkillDef, Literal["pool", "composer", "llm"], bool]] = []
        for source in order:
            best, dual, spare = (
                self.from_composer(rng, keywords, want)
                if source == "composer"
                else self.from_pool(rng, keywords, want)
            )
            if best is not None:
                return best, source, True
            if dual is not None:
                seconds.append((dual, source, True))
            if spare is not None:
                spares.append((spare, source, False))
        if seconds:  # ② 雙屬性技能
            return seconds[0]
        return spares[0] if spares else None  # 偏好的屬性湊不到：備選取第一個來源的

    def accept(self, skill: SkillDef) -> None:
        self.taken.add(skill.id)


def _pool(
    library: ContentLibrary, tier: int, region: str | None = None
) -> tuple[tuple[SkillDef, tuple[str, ...]], ...]:
    """手寫技能池；``region``（6F-4c）：區域技能池只在那一區出（:func:`in_region_pool`）。"""
    found: list[tuple[SkillDef, tuple[str, ...]]] = []
    for skill in player_skills(library).values():
        if skill.tier != tier or skill.rarity == "legendary" or minimum_tier(skill, library) > tier:
            continue
        if not in_region_pool(skill, region):
            continue
        keywords = derive_keywords(skill, library.keywords, exclusive_only=True).all()
        if keywords:
            found.append((skill, keywords))
    return tuple(found)


# ---------------------------------------------------------------------------
# 三種候選
# ---------------------------------------------------------------------------


def _ranked_held(
    counts: Mapping[str, int], order: Sequence[str], behavior: Mapping[str, int]
) -> list[str]:
    """持有的關鍵字，依持有數（多→少）、行為分數（高→低）、推導表順序排列。"""
    held = [k for k in order if counts.get(k, 0) > 0]
    return sorted(held, key=lambda k: (-counts[k], -behavior.get(k, 0), order.index(k)))


def _weighted_order(rng: Rng, keywords: Sequence[str], behavior: Mapping[str, int]) -> list[str]:
    """依權重（1 ＋ 行為分數）不放回抽出的順序（確定性）。"""
    remaining = list(keywords)
    result: list[str] = []
    while remaining:
        weights = [1 + behavior.get(k, 0) for k in remaining]
        roll = rng.randint(1, sum(weights))
        for keyword, weight in zip(remaining, weights, strict=True):
            roll -= weight
            if roll <= 0:
                result.append(keyword)
                remaining.remove(keyword)
                break
    return result


def _first(
    search: _Search, rng: Rng, options: Iterable[tuple[str, ...]], want: AttrWant | None = None
) -> tuple[tuple[str, ...], SkillDef, Literal["pool", "composer", "llm"]] | None:
    """依序試 ``options``：第一個符合屬性偏好的；都沒有才放寬屬性，取第一個備選（BAL-17：先放寬
    關鍵字、再放寬屬性）。"""
    spare: tuple[tuple[str, ...], SkillDef, Literal["pool", "composer", "llm"]] | None = None
    for keywords in options:
        if search.exhausted(keywords):  # PERF-3：橋接上限用完，跳到單一關鍵字（6.27.4 ③）
            continue
        found = search.find(rng, keywords, want)
        if found is None:
            continue
        if found[2]:
            search.accept(found[0])
            return keywords, found[0], found[1]
        spare = spare if spare is not None else (keywords, found[0], found[1])
    if spare is not None:
        search.accept(spare[1])
    return spare


def _deepen(
    search: _Search, held: list[str], unheld: list[str], behavior: Mapping[str, int]
) -> Candidate | None:
    rng = Rng(search.request.seed).fork("deepen")
    search.kind = "deepen"
    # BAL-17：持有的關鍵字與還沒有的關鍵字合成一串，先換關鍵字找同路線的，都沒有才放寬屬性
    options = [*((k,) for k in held), *((k,) for k in _weighted_order(rng, unheld, behavior))]
    hit = _first(search, rng, options, "same")
    if hit is None:
        return None
    return Candidate("deepen", hit[0], hit[1], hit[2], fallback=not held or hit[0][0] != held[0])


def _bridge(
    search: _Search, held: list[str], unheld: list[str], behavior: Mapping[str, int]
) -> Candidate | None:
    rng = Rng(search.request.seed).fork("bridge")
    search.kind = "bridge"
    pairs = [tuple(sorted(p, key=held.index)) for p in combinations(held, 2)]
    shuffled = rng.shuffled(pairs)
    weighted = _weighted_order(rng, unheld, behavior)
    if held:
        outward = [(k, n) for k in held for n in weighted]
        rest: list[tuple[str, ...]] = [*outward, *((k,) for k in held)]
    else:
        rest = [(k,) for k in weighted]
    # BAL-17：配對、往外一步、單一關鍵字合成一串，先換關鍵字找同路線的，都沒有才放寬屬性
    hit = _first(search, rng, [*shuffled, *rest], "same")
    if hit is None:
        return None
    return Candidate("bridge", hit[0], hit[1], hit[2], fallback=hit[0] not in pairs)


def region_first(keywords: Sequence[str], region: Sequence[str]) -> list[str]:
    """區域偏向（Phase 5B-4b）：``keywords`` 裡屬於 ``region`` 的排前面，其餘照原順序在後。"""
    wanted = set(region)
    return [k for k in keywords if k in wanted] + [k for k in keywords if k not in wanted]


def _new(
    search: _Search, unheld: list[str], held: list[str], behavior: Mapping[str, int]
) -> Candidate | None:
    rng = Rng(search.request.seed).fork("new")
    search.kind = "new"
    order = region_first(_weighted_order(rng, unheld, behavior), search.request.region_keywords)
    fresh = [(k,) for k in order]
    # 每個關鍵字都有了（或還沒有的都找不到技能）：退回持有最少的關鍵字（BAL-17：合成一串，先換
    # 關鍵字找偏離路線的，都沒有才放寬屬性）
    hit = _first(search, rng, [*fresh, *((k,) for k in reversed(held))], "other")
    if hit is None:
        return None
    return Candidate("new", hit[0], hit[1], hit[2], fallback=hit[0] not in fresh)


def _pinned(
    search: _Search, held: list[str], unheld: list[str], behavior: Mapping[str, int]
) -> list[Candidate | None]:
    """指定關鍵字模式（Phase 5B-4d，見模組說明）：三張都帶 ``pinned_keyword``。亂數照一般模式各
    種類一條 ``fork``。"""
    pin = search.request.pinned_keyword
    assert pin is not None
    # TXT-2：區域偏向（許願的第 2 個關鍵字）排前，組合器做得到時橋接那張同時帶兩個
    others = region_first([k for k in held if k != pin], search.request.region_keywords)
    fresh = [k for k in unheld if k != pin]
    seed = search.request.seed

    search.kind = "deepen"
    hit = _first(search, Rng(seed).fork("deepen"), [(pin,)], "same")
    deepen = None if hit is None else Candidate("deepen", *hit, fallback=pin not in held)

    search.kind = "bridge"
    pairs: list[tuple[str, ...]] = [(pin, k) for k in others]
    hit = _first(search, Rng(seed).fork("bridge"), [*pairs, (pin,)], "same")
    bridge = None if hit is None else Candidate("bridge", *hit, fallback=hit[0] not in pairs)

    search.kind = "new"
    rng = Rng(seed).fork("new")
    order = region_first(_weighted_order(rng, fresh, behavior), search.request.region_keywords)
    outward: list[tuple[str, ...]] = [(pin, k) for k in order]
    hit = _first(search, rng, [*outward, (pin,)], "other")
    new = None if hit is None else Candidate("new", *hit, fallback=hit[0] not in outward)
    return [deepen, bridge, new]


def _general_pool(
    library: ContentLibrary, tier: int, region: str | None = None
) -> tuple[SkillDef, ...]:
    """通用池：階級相符、非傳說、**沒有任何關鍵字**（含通用歸類）的手寫技能＝基礎技能（06 6.27.1，
    玩法 PM 2026-10-24 選 B：通用池與「基礎技能」同一個範圍）。``region``：同 :func:`_pool`。"""
    found: list[SkillDef] = []
    for skill in player_skills(library).values():
        if skill.tier != tier or skill.rarity == "legendary" or minimum_tier(skill, library) > tier:
            continue
        if not in_region_pool(skill, region):
            continue
        if skill.form_id is not None:  # 形態技能（3J-1a 只為測試）：身分與技能池在 3J-3
            continue
        if not derive_keywords(skill, library.keywords).all():
            found.append(skill)
    return tuple(found)


def _general(search: _Search) -> Candidate | None:
    """「新方向」有 ``general_share_permille`` 的機率從通用池抽（Phase 3-51，玩法決定 #55）。
    擲骰用獨立的 ``fork("new_general")``，沒中時不影響其他候選的亂數；池空時回傳 ``None``。"""
    rng = Rng(search.request.seed).fork("new_general")
    if not rng.chance_permille(search.rules.general_share_permille):
        return None
    options = [
        s
        for s in _general_pool(search.library, search.request.tier, search.request.region)
        if search.usable(s)
    ]
    if not options:
        return None
    if search.request.hero_attributes:  # 新方向盡量取不同屬性；湊不到就放寬
        options = [s for s in options if search._want_ok(s, "other")] or options
    skill = rng.choice(options)
    search.taken.add(skill.id)
    return Candidate("new", (), skill, "pool")


def generate_candidates(
    library: ContentLibrary,
    request: CandidateRequest,
    rules: CandidateRules | None = None,
    llm: LlmProposer | None = None,
) -> tuple[Candidate, ...]:
    """加深、橋接、新方向各一個候選（依序；找不到的種類略過）。見模組說明；``llm`` 為 LLM 來源
    （省略 ＝ 不使用，行為與 Phase 4 之前相同）。"""
    rules = rules if rules is not None else CandidateRules()
    order = library.keywords.ids()
    unknown = sorted(set(request.keyword_counts) - set(order))
    if unknown:
        raise ValueError(f"未知的關鍵字：{', '.join(unknown)}")
    behavior = behavior_weights(library, request.behavior)
    held = _ranked_held(request.keyword_counts, order, behavior)
    if request.pinned_keyword is not None and request.pinned_keyword not in order:
        raise ValueError(f"未知的指定關鍵字：{request.pinned_keyword}")
    search = _Search(
        library, request, rules, _pool(library, request.tier, request.region), set(), llm
    )
    found: list[Candidate | None] = []
    # 依「加深 → 橋接 → 新方向」的順序產生；退回到「還沒有的關鍵字」的候選用掉的關鍵字，不再給
    # 下一個候選（盡量讓三個候選不同），已被前一個候選用掉的技能也不會重複。
    unheld = new_direction_keywords(library, held)
    if request.pinned_keyword is not None:  # 指定關鍵字（5B-4d）
        found = _pinned(search, held, unheld, behavior)
    else:
        deepen = _deepen(search, held, unheld, behavior)
        found.append(deepen)
        bridge = _bridge(search, held, _without(unheld, deepen), behavior)
        found.append(bridge)
        new = _general(search) or _new(
            search, _without(_without(unheld, deepen), bridge), held, behavior
        )
        found.append(new)
    return tuple(
        replace(c, llm=search.traces.get(c.kind)) if c.kind in search.traces else c
        for c in found
        if c is not None
    )


def _without(keywords: list[str], candidate: Candidate | None) -> list[str]:
    """退回到新方向的候選用掉的關鍵字，不再給下一個候選當「新方向」（盡量讓三個候選不同）。"""
    if candidate is None or not candidate.fallback:
        return keywords
    remaining = [k for k in keywords if k not in candidate.keywords]
    return remaining or keywords
