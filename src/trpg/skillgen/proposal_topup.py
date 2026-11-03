"""LLM 提議的結構補強（Phase 6S-2）：數值補值器修不好的 ``budget.weak``、``keyword.required``。

升級候選的退回大多是兩種「結構」問題（4-L10b 起數值補值器已把旋鈕、巢狀效果、AP 都調過了）：

- ``budget.weak``：提議只有一個沒有數值的核心效果（位移、淨化、地形、傳送…），旋鈕全開、AP 降到 1
  仍只有預算的 10～40%。
- ``keyword.required``：題目要求的關鍵字沒有帶到（例：題目是「召喚物」，提議只有淨化）。

這裡產生 **候選補強**：在提議的 ``effects`` 末尾加一個效果（關鍵字的專屬效果、或傷害／治療／護盾／
有害狀態附帶效果），或替已有效果補上 LLM 沒填的參數（例：沒指定元素的 ``damage`` 補 ``element:
lightning`` 讓它帶到「帶電」）。只加題目選單（提議模型）開放的原語，也就是 LLM 本來就能選的。
補強後的提議 **照原樣走完整的驗證**（提議模型、數值補值、``validate_skill``、題目要求），第一個
合格的才採用；驗證規則、預算數值與上下限都不變。

附帶效果的順序（Phase 6S-2c）：不再固定 ``damage → heal → shield``。先試骨架偏好的一組
（:data:`FILLER_PREFERENCE`：攻擊骨架傷害、支援骨架治療／護盾、控制骨架有害狀態、位移骨架傷害與
有害狀態），再試其餘；
兩組各自依「題目種子＋提議內容」的雜湊輪替起點（:func:`filler_order`）。

確定性：候選的順序只取決於提議、種子與內容庫（YAML 順序）；雜湊用
:func:`trpg.shared.rng.fnv1a64`（不用內建 ``hash()``），沒有亂數。純函式：不修改輸入。
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping, Sequence
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from trpg.content.keyword_derive import derive_from_facts
from trpg.content.library import ContentLibrary
from trpg.content.skill_keywords import KeywordRule
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skills import SkillRarity, rarity_rank
from trpg.shared.rng import fnv1a64
from trpg.skillgen.keywords import draft_facts
from trpg.skillgen.proposal import budget_statuses, rarity_statuses

if TYPE_CHECKING:
    from trpg.skillgen.proposal_subset import ProposalSubset

__all__ = [
    "FILLER_EFFECTS",
    "FILLER_PREFERENCE",
    "FILLER_STATUS_MAX",
    "TOPUP_CODES",
    "TOPUP_GROUP_MAX",
    "TOPUP_MAX",
    "TOPUP_PREFIX",
    "filler_order",
    "keyword_effect_rules",
    "keyword_way_texts",
    "keywords_reachable",
    "missing_keywords",
    "topup_candidates",
]

TOPUP_CODES = frozenset({"budget.weak", "keyword.required"})
"""補強處理的錯誤代碼：數值修補之後只剩這些（規則層）才試補強。"""
TOPUP_PREFIX = "topup."
"""補強修好的代碼在 ``RepairedEvaluation.repaired`` 的前綴（報表與數值修補分開計）。"""
TOPUP_MAX = 24
"""每份提議最多試幾個候選（每個候選要跑一次完整驗證）。"""
TOPUP_GROUP_MAX = 10
"""每一組候選（關鍵字、附帶效果、關鍵字＋附帶效果）最多幾個，讓三組都有機會被試到。"""
FILLER_EFFECTS: tuple[str, ...] = ("damage", "heal", "shield", "apply_status")
"""過弱時補的附帶效果（試的順序由 :func:`filler_order` 決定）：數值由預算器補；對象依效果性質
（傷害與有害狀態只打敵方、治療與護盾只給友方），不合骨架的由驗證擋下。"""
FILLER_PREFERENCE: dict[str, tuple[str, ...]] = {
    # 攻擊骨架：核心是傷害，先試傷害
    "strike": ("damage",),
    "area": ("damage",),
    "combo": ("damage",),
    "builder_finisher": ("damage",),
    "rune": ("damage",),
    "consume_status": ("damage",),
    "trap": ("damage",),
    # 支援骨架：先試治療、護盾
    "aura": ("heal", "shield"),
    # 控制骨架：先試非傷害的有害狀態；位移骨架：傷害與有害狀態輪替
    "control": ("apply_status",),
    "displace": ("damage", "apply_status"),
}
"""骨架偏好的附帶效果（6S-2c，原型值）。表外的骨架依核心效果的對象：對友方／自己的先試治療與
護盾，其他先試傷害與有害狀態。偏好只決定試的先後，每個候選照樣走完整驗證。"""
FILLER_STATUS_MAX = 3
"""附帶效果 ``apply_status`` 每份提議最多試幾種有害狀態（依雜湊輪替起點選）。"""
_AFFECTS_ORDER: tuple[str, ...] = ("enemies", "allies", "self")
_SKIP_PARAMS = frozenset({"infusion", "unit", "on_hit", "rule", "skill"})
"""推導規則裡這些參數對應的是手寫內容（附魔召喚、指定召喚物、規則改寫、授予指定技能），
補強不產生、prompt 也不列。"""


def keyword_effect_rules(library: ContentLibrary, keyword: str) -> tuple[KeywordRule, ...]:
    """``keyword`` 的專屬「效果」推導規則（製造在前、利用在後；YAML 順序），排除
    :data:`_SKIP_PARAMS` 的規則。未知的關鍵字為空。"""
    found = library.keywords.by_id().get(keyword)
    if found is None:
        return ()
    return tuple(
        rule
        for rule in (*found.makes, *found.uses)
        if rule.grade == "exclusive"
        and rule.source == "effect"
        and not (_SKIP_PARAMS & set(rule.params()))
    )


def _rule_text(rule: KeywordRule) -> str:
    params = rule.params()
    inner = "，".join(f"{k}＝{v}" for k, v in sorted(params.items()))
    return f"{rule.source_id}（{inner}）" if inner else rule.source_id


def keyword_way_texts(
    library: ContentLibrary,
    keyword: str,
    *,
    primitives: Iterable[str],
    conditions: Iterable[str] = (),
    triggers: Iterable[str] = (),
    shapes: Iterable[str] = (),
    limit: int = 6,
) -> list[str]:
    """題目選單裡能帶到 ``keyword`` 的寫法（給 prompt 的短字串，最多 ``limit`` 個）：專屬規則中
    原語／條件／觸發／形狀在選單內的。例：``apply_status（status＝commanding）``、
    ``條件 target_has_status（status＝poison）``。"""
    found = library.keywords.by_id().get(keyword)
    if found is None:
        return []
    allowed = {
        "effect": set(primitives),
        "condition": set(conditions),
        "trigger": set(triggers),
        "shape": set(shapes),
    }
    label = {"effect": "", "condition": "條件 ", "trigger": "觸發 ", "shape": "形狀 "}
    out: list[str] = []
    for rule in (*found.makes, *found.uses):
        if rule.grade != "exclusive" or rule.source not in allowed:
            continue
        if _SKIP_PARAMS & set(rule.params()) or rule.source_id not in allowed[rule.source]:
            continue
        text = label[rule.source] + _rule_text(rule)
        if text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _status_ok(library: ContentLibrary, status: str | None, rarity: SkillRarity) -> bool | None:
    """狀態在這個稀有度能用嗎；回傳 ``None`` ＝ 沒有指定狀態。"""
    if status is None:
        return None
    found = library.ruleset.statuses.by_id().get(status)
    return found is not None and rarity_rank(found.min_rarity) <= rarity_rank(rarity)


def _hostile(library: ContentLibrary, rule: KeywordRule) -> bool:
    status = rule.params().get("status")
    if rule.source_id == "apply_status" and status is not None:
        found = library.ruleset.statuses.by_id().get(status)
        return found is not None and not found.beneficial
    primitive = library.ruleset.primitives.by_id().get(rule.source_id)
    return primitive is not None and primitive.harmful


def _slot_ok(
    library: ContentLibrary, skeleton: SkeletonDef, primitive: str, *, core: str | None
) -> bool:
    """``primitive`` 能放進 ``skeleton``：當核心（沒指定核心或就是指定的核心）或附帶效果。"""
    if primitive in skeleton.core.primitives and core in (None, primitive):
        return True
    rules = skeleton.secondary
    if rules.max_count <= 0 or (rules.primitives is not None and primitive not in rules.primitives):
        return False
    found = library.ruleset.primitives.by_id().get(primitive)
    return not rules.harmful_only or (found is not None and found.harmful)


def _effect_rule_reachable(
    library: ContentLibrary, rule: KeywordRule, subset: ProposalSubset, core: str | None
) -> bool:
    if rule.source_id not in subset.primitives or subset.rarity is None:
        return False
    if _status_ok(library, rule.params().get("status"), subset.rarity) is False:
        return False
    hostile = _hostile(library, rule)
    for skeleton_id in subset.skeletons:
        skeleton = library.skeletons.get(skeleton_id)
        if skeleton is None or not _slot_ok(library, skeleton, rule.source_id, core=core):
            continue
        if hostile and "enemies" in skeleton.forbid_affects:
            continue
        return True
    return False


def keywords_reachable(
    library: ContentLibrary, subset: ProposalSubset, *, core: str | None = None
) -> bool:
    """題目的每個關鍵字在這份選單裡 **至少有一種寫法可能成立**（必要條件，不保證一定過驗證）：
    專屬規則的原語在選單裡、放得進某個骨架（指定核心時只能當附帶效果，除非就是核心）、狀態的
    稀有度夠、有害效果不在禁止對敵的骨架上；或條件／觸發／形狀在選單裡。

    出題用（Phase 6S-2）：選單裡根本帶不到關鍵字的題目（例：普通稀有度的淨化光環配「召喚物」，
    號令要稀有）每次都會 ``keyword.required`` 退回，不出這種題目。"""
    table = library.keywords.by_id()
    allowed = {
        "condition": set(subset.conditions),
        "trigger": set(subset.triggers),
        "shape": set(subset.shapes),
    }
    for keyword in subset.keywords:
        found = table.get(keyword)
        if found is None:
            return False
        rules = [r for r in (*found.makes, *found.uses) if r.grade == "exclusive"]
        if not any(
            _effect_rule_reachable(library, rule, subset, core)
            if rule.source == "effect"
            else rule.source_id in allowed.get(rule.source, ())
            for rule in rules
        ):
            return False
    return True


def missing_keywords(
    library: ContentLibrary, data: Mapping[str, Any], keywords: Sequence[str]
) -> tuple[str, ...]:
    """提議（草稿 JSON）依專屬規則還沒帶到的題目關鍵字（依題目順序）。"""
    if not keywords:
        return ()
    found = derive_from_facts(draft_facts(data), library.keywords, exclusive_only=True).all()
    return tuple(k for k in keywords if k not in found)


_FRIENDLY = ("allies", "self")
_HOSTILE = ("enemies",)
_FILLER_AFFECTS: dict[str, tuple[str, ...]] = {
    "damage": _HOSTILE,
    "heal": _FRIENDLY,
    "shield": _FRIENDLY,
    "apply_status": _HOSTILE,
}
"""附帶效果的對象：傷害與有害狀態只打敵方、治療與護盾只給友方（不產生「治療敵人」這類怪招）。"""
DEFAULT_ELEMENT = "physical"
"""補的傷害沒有可沿用的元素時用物理（法術技的傷害必須指定元素）。"""


def _core_affects(effects: Sequence[Any]) -> tuple[str, ...]:
    first = effects[0] if effects and isinstance(effects[0], Mapping) else {}
    preferred = first.get("affects")
    order = [preferred] if isinstance(preferred, str) and preferred in _AFFECTS_ORDER else []
    return tuple(dict.fromkeys([*order, *_AFFECTS_ORDER]))


def _element_of(effects: Sequence[Any]) -> str:
    """提議裡第一個寫了元素的效果的元素（補的傷害沿用它）；沒有時 :data:`DEFAULT_ELEMENT`。"""
    for effect in effects:
        if isinstance(effect, Mapping) and isinstance(effect.get("element"), str):
            return str(effect["element"])
    return DEFAULT_ELEMENT


def _appended(data: Mapping[str, Any], effect: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(dict(data))
    out["effects"] = [*out["effects"], effect]
    return out


def _rule_affects(library: ContentLibrary, rule: KeywordRule, core: Sequence[str]) -> list[str]:
    """關鍵字效果的對象：施加有益狀態只給友方、有害狀態只給敵方；有害的原語（``harmful``，例：
    擊倒、推擊）只打敵方；其他依核心效果的對象排序。"""
    status = rule.params().get("status")
    if rule.source_id == "apply_status" and status is not None:
        found = library.ruleset.statuses.by_id().get(status)
        if found is not None:
            return list(_FRIENDLY if found.beneficial else _HOSTILE)
    primitive = library.ruleset.primitives.by_id().get(rule.source_id)
    if primitive is not None and primitive.harmful:
        return list(_HOSTILE)
    return list(core)


def _rule_effects(
    library: ContentLibrary, rule: KeywordRule, core: Sequence[str]
) -> Iterator[dict[str, Any]]:
    params = dict(sorted(rule.params().items()))
    if rule.source_id == "damage":
        params.setdefault("element", DEFAULT_ELEMENT)
    for target in _rule_affects(library, rule, core):
        yield {"type": rule.source_id, "affects": target, **params}
    yield {"type": rule.source_id, **params}  # 不吃 affects 的原語（例：地形）


def _param_fills(data: Mapping[str, Any], rule: KeywordRule) -> Iterator[dict[str, Any]]:
    """已有同原語、但 LLM 沒填規則要的參數的效果：補上那個參數（不改 LLM 已填的值）。"""
    params = rule.params()
    for index, effect in enumerate(data["effects"]):
        if not isinstance(effect, Mapping) or effect.get("type") != rule.source_id:
            continue
        if any(name in effect for name in params):
            continue
        out = deepcopy(dict(data))
        out["effects"][index] = {**effect, **params}
        yield out


def _keyword_candidates(
    library: ContentLibrary,
    data: Mapping[str, Any],
    keyword: str,
    allowed: frozenset[str] | None,
) -> Iterator[dict[str, Any]]:
    affects = _core_affects(data["effects"])
    rules = [
        rule
        for rule in keyword_effect_rules(library, keyword)
        if allowed is None or rule.source_id in allowed
    ]
    for rule in rules:
        if rule.params():
            yield from _param_fills(data, rule)
    for rule in rules:
        for effect in _rule_effects(library, rule, affects):
            yield _appended(data, effect)


def _rotated[T](items: Sequence[T], start: int) -> list[T]:
    if not items:
        return []
    k = start % len(items)
    return [*items[k:], *items[:k]]


def _order_key(data: Mapping[str, Any], seed: int) -> int:
    """「題目種子＋提議內容」的穩定雜湊（排序鍵的 JSON 再 FNV-1a；不用內建 ``hash()``）。"""
    text = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return fnv1a64(f"{seed}|{text}".encode())


def _preferred(data: Mapping[str, Any]) -> tuple[str, ...]:
    skeleton = data.get("skeleton")
    if isinstance(skeleton, str) and skeleton in FILLER_PREFERENCE:
        return FILLER_PREFERENCE[skeleton]
    if _core_affects(data["effects"])[0] in _FRIENDLY:
        return ("heal", "shield")
    return ("damage", "apply_status")


def filler_order(data: Mapping[str, Any], *, seed: int = 0) -> tuple[str, ...]:
    """附帶效果原語要試的順序（6S-2c）：骨架偏好的一組在前、其餘在後，兩組各自依「題目種子＋
    提議內容」的雜湊輪替起點。``data`` 需有非空的 ``effects`` 清單。"""
    key = _order_key(data, seed)
    preferred = [p for p in FILLER_EFFECTS if p in _preferred(data)]
    rest = [p for p in FILLER_EFFECTS if p not in preferred]
    return (*_rotated(preferred, key), *_rotated(rest, key >> 16))


def _hostile_statuses(library: ContentLibrary, rarity: SkillRarity | None, key: int) -> list[str]:
    """附帶效果可試的有害狀態：非有益、有預算點數、（有給稀有度時）稀有度夠——與提議模型的
    ``apply_status`` 狀態選單條件相同；依 ``key`` 輪替起點取 :data:`FILLER_STATUS_MAX` 個。"""
    usable = set(budget_statuses(library))
    if rarity is not None:
        usable &= set(rarity_statuses(library, rarity))
    pool = [s.id for s in library.ruleset.statuses.statuses if not s.beneficial and s.id in usable]
    return _rotated(pool, key >> 32)[:FILLER_STATUS_MAX]


def _filler_candidates(
    data: Mapping[str, Any],
    allowed: frozenset[str] | None,
    *,
    order: Sequence[str],
    statuses: Sequence[str],
) -> Iterator[dict[str, Any]]:
    affects = _core_affects(data["effects"])
    element = _element_of(data["effects"])
    for primitive in order:
        if allowed is not None and primitive not in allowed:
            continue
        for target in (a for a in affects if a in _FILLER_AFFECTS[primitive]):
            if primitive == "apply_status":
                for status in statuses:
                    yield _appended(data, {"type": primitive, "affects": target, "status": status})
                continue
            effect: dict[str, Any] = {"type": primitive, "affects": target}
            if primitive == "damage":
                effect["element"] = element
            yield _appended(data, effect)


def topup_candidates(
    library: ContentLibrary,
    data: Mapping[str, Any],
    *,
    keywords: Sequence[str] = (),
    weak: bool = False,
    primitives: Iterable[str] | None = None,
    seed: int = 0,
    rarity: SkillRarity | None = None,
) -> list[dict[str, Any]]:
    """依序要試的補強提議（最多 :data:`TOPUP_MAX` 個，去重；``data`` 不變）。

    1. 題目關鍵字沒帶到：先補參數、再加該關鍵字的專屬效果（只補第一個缺的關鍵字）；
    2. ``weak``：加一個 :data:`FILLER_EFFECTS` 附帶效果（順序見 :func:`filler_order`，依 ``seed``
       與提議內容輪替；``rarity`` 有給時只試這個稀有度能用的有害狀態）；
    3. 兩者都有：關鍵字效果 ＋ 附帶效果。

    ``primitives``：題目選單（提議模型）開放的原語；給了就只加選單內的效果。每組最多
    :data:`TOPUP_GROUP_MAX` 個。``data`` 沒有 ``effects`` 清單時為空。"""
    if not isinstance(data.get("effects"), list) or not data["effects"]:
        return []
    allowed = None if primitives is None else frozenset(primitives)
    lacking = missing_keywords(library, data, keywords)
    order = filler_order(data, seed=seed)
    statuses = _hostile_statuses(library, rarity, _order_key(data, seed))

    def fillers(base: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        return _filler_candidates(base, allowed, order=order, statuses=statuses)

    groups: list[Iterable[dict[str, Any]]] = []
    if lacking:
        groups.append(_keyword_candidates(library, data, lacking[0], allowed))
    if weak:
        groups.append(fillers(data))
    if lacking and weak:
        groups.append(
            filled
            for base in _keyword_candidates(library, data, lacking[0], allowed)
            for filled in fillers(base)
        )
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        taken = 0
        for candidate in group:
            key = repr(candidate)
            if key in seen:
                continue
            seen.add(key)
            out.append(candidate)
            taken += 1
            if len(out) >= TOPUP_MAX:
                return out
            if taken >= TOPUP_GROUP_MAX:
                break
    return out
