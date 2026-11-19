"""許願覆蓋表（WC-1；WC-2 起照 #167 的新配方）：許願池的每個標籤、每一對標籤，組合器在各階級、各
稀有度做不做得出來。

標籤清單＝``content/skill_pick.yaml`` 的 ``wish_tags``（PK-4；關鍵字＝內容庫的 16 個）。做法照
``trpg.skillgen.wish_pick.wish_pool`` 的出題條件：

- **桶子**＝（指定關鍵字或不指定, 種類, 階級, 稀有度）；每桶用種子 0～N-1 各呼叫一次組合器
  （``compose_with_stats``，參數同 ``wish_pick._compose``：``keyword_tries=SLOT_KEYWORD_TRIES``、
  ``skip_legendary``、``kinds``；另外指定稀有度——遊戲裡由組合器自己擲）。
- **合法**＝組合器不丟 ``ComposeError``、``validate_skill`` 無違規、不是傳說、種類在要的那一族
  （主動＝主動＋姿態），同 ``wish_pick._Filter``（不看武器、不看手上的技能）。
- 每個合法技能記下它的標籤（``wish_pick.skill_tag_ids``，關鍵字只看專屬規則）。
- **一組標籤在一格的成功率**＝照許願池出題：有關鍵字標籤的用那個關鍵字的桶（兩個關鍵字＝兩桶各半，
  同 ``wish_pool`` 輪流指定）；有種類標籤的用那個種類的桶，沒有時照 ``kind_permille``（主動 70／
  被動 20／反應 10）加權三個種類的桶。成功＝合法而且標籤全部帶到。

WC-2（#167）另外照許願池的新出題量：

- **換主題元素**（``composer_retheme.retheme``）：每個合法技能另記下換成其他元素的版本（``R``）；
  願望有元素標籤時算數。
- **雙元素**（``composer_dual.add_second_element``）：2 階起，帶一個元素的技能另記下加第二元素的版本
  （``D``）；物理（武器傷害沒有元素）的技能每一階都記下「物理＋元素」的版本（WC-2b，#167 補：物理
  不佔元素名額）。願望有兩個元素標籤（含物理）時算數。
- **召喚**：效果標籤有召喚時，主動那一族另外用「指定召喚骨架」的桶（``…/summon``，同許願池的標籤
  補抽）；兩個桶取較高的。
- **形態**（關鍵字）：候選另外放進同關鍵字的手寫技能（``wish_pick.handwritten_pool``）；有一招帶到
  全部標籤就算 100%（手寫技能一定在候選裡）。
- **吸血**（SK-5）：吸血配方做得到的合法技能（``composer_lifesteal.lifesteal_ready``：打擊、範圍
  骨架的主動技）另記下吸血版本（``L``，``composer_lifesteal.add_lifesteal``）；願望的效果同時有傷害和治療時
  算數（同許願池的 ``_lifesteal_draws``；許願池另有指定骨架的補抽，這裡不另跑桶）。

做不到（每一格都是 0）與極低（最好的一格也低於 :data:`LOW_PERMILLE`）的組合分三類：(a) 引擎有原語、
組合器缺配方；(b) 規則禁止（附設計文件出處）；(c) 連原語都沒有；判斷不了的標「需人工」。

只讀：不改 ``content/``、不呼叫 LLM、不跑戰鬥。``run`` 寫 ``docs/phases/WC-2資料/buckets.json``
（計時以外的欄位只由內容與參數決定）；``report`` 讀它寫 ``docs/phases/許願覆蓋表-WC2.md``，並和舊表
（WC-1，``docs/phases/許願覆蓋表.md``）的做不到清單對照。

用法::

    uv run python scripts/wish_coverage.py run --seeds 40 --workers 8
    uv run python scripts/wish_coverage.py report

**資料不進版控**（SK-4）：``buckets.json``（WC-2 起 8 MB 以上；WC-1 的
``docs/phases/WC-1資料/buckets.json`` 同樣）列在 ``.gitignore``，repo 裡只留覆蓋表 md。要重出表或
改 ``report`` 時，先在本機用上面的 ``run`` 重產（同一份內容、同樣參數，計時以外的欄位逐字相同；
8 個行程約 15 分鐘），再跑 ``report``。``report`` 找不到資料檔時會提示先跑 ``run``。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from typing import Any

from trpg.content.library import ContentLibrary, load_library
from trpg.content.skill_pick import WISH_TAG_GROUPS
from trpg.content.skills import SkillDef, damage_elements
from trpg.content.skills.constants import SkillRarity
from trpg.shared.rng import Rng
from trpg.skillgen.composer_dual import add_second_element, second_element_tier
from trpg.skillgen.composer_lifesteal import add_lifesteal, lifesteal_ready
from trpg.skillgen.composer_parts import _HAND_WRITTEN_PRIMITIVES
from trpg.skillgen.composer_retheme import retheme
from trpg.skillgen.pick_offer import SLOT_KEYWORD_TRIES
from trpg.skillgen.random_composer import _STACK_SKELETON, ComposeError, compose_with_stats
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.wish_pick import (
    LIFESTEAL_TAGS,
    SUMMON_HINT,
    handwritten_keywords,
    handwritten_pool,
    skill_tag_ids,
    tag_label,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "docs" / "phases" / "WC-2資料"
REPORT = ROOT / "docs" / "phases" / "許願覆蓋表-WC2.md"
OLD_REPORT = ROOT / "docs" / "phases" / "許願覆蓋表.md"
FORMAT = "wish-coverage/3"
HINT_SEP = "/"
DERIVED_SEP = "#"
"""一個種子的結果字串：``基本簽名#R換元素簽名;…#D雙元素簽名;…#L吸血簽名``（沒有衍生版本時只有基本
簽名；SK-5 起多 ``L``，格式 /3）。"""
NO_KEYWORD = "-"
KINDS: tuple[str, ...] = ("active", "passive", "reaction")
KIND_FAMILY: dict[str, tuple[str, ...]] = {
    "active": ("active", "stance"),
    "passive": ("passive",),
    "reaction": ("reaction",),
}
RARITIES: tuple[SkillRarity, ...] = ("common", "rare", "epic")
MAX_WORKERS = 8
DEFAULT_SEEDS = 60
LOW_PERMILLE = 20
"""極低：最好的一格成功率低於這個千分比（許願池一次只抽約 27＋9 個種子，2% 大多抽不到）。"""

PAIR = 2
PER_PERCENT = 10
"""千分比換百分比。"""

type Tag = tuple[str, str]
"""（類別, 值），類別是 ``WISH_TAG_GROUPS`` 之一。"""


def tag_code(tag: Tag) -> str:
    return f"{tag[0]}:{tag[1]}"


def all_tags(lib: ContentLibrary) -> list[Tag]:
    """許願池的固定標籤清單（依類別順序）：關鍵字（內容庫）、元素、效果類型、形狀、種類。"""
    out: list[Tag] = [("keywords", k.id) for k in lib.keywords.keywords]
    rules = lib.skill_pick.wish_tags
    for group in WISH_TAG_GROUPS[1:]:
        out.extend((group, item.id) for item in rules.items(group))
    return out


# ---------------------------------------------------------------------------
# 量測：桶子
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Bucket:
    keyword: str  # NO_KEYWORD ＝ 不指定
    kind: str
    tier: int
    rarity: SkillRarity
    hint: str = ""
    """指定給組合器的骨架（WC-2：效果標籤有召喚時的 ``summon``）；空＝不指定。"""

    def key(self) -> str:
        base = f"{self.keyword}/{self.kind}/{self.tier}/{self.rarity}"
        return f"{base}{HINT_SEP}{self.hint}" if self.hint else base


_LIBRARY: ContentLibrary | None = None


def _library() -> ContentLibrary:
    global _LIBRARY  # noqa: PLW0603 — 每個行程只載入一次內容庫
    if _LIBRARY is None:
        _LIBRARY = load_library()
    return _LIBRARY


def skill_signature(lib: ContentLibrary, skill: SkillDef) -> str:
    """技能帶的全部標籤（排序後以 ``|`` 連接的 ``類別:值``）。"""
    tags = skill_tag_ids(lib, skill)
    codes = sorted(f"{g}:{v}" for g in WISH_TAG_GROUPS for v in tags.group(g))
    return "|".join(codes)


_PHYSICAL = "physical"


def derived(lib: ContentLibrary, skill: SkillDef, tier: int, seed: int) -> str:
    """WC-2：換主題元素（每個別的元素）與 2 階起加第二元素的版本的簽名（見模組說明）；沒有時
    空字串。"""
    elements = [i.id for i in lib.skill_pick.wish_tags.elements if i.id != _PHYSICAL]
    have = {e.value for e in damage_elements(skill)}
    swapped = []
    for element in elements:
        made = retheme(lib, skill, element)
        if made is not None:
            swapped.append(skill_signature(lib, made))
    dual = []
    physical = not have and _PHYSICAL in skill_tag_ids(lib, skill).elements
    if (len(have) == 1 and tier >= second_element_tier(lib)) or physical:
        # WC-2b：物理（武器傷害沒有元素）的技能加一段元素＝「物理＋元素」，1 階起
        rng = Rng(seed).fork("wish-coverage.dual")
        for element in elements:
            made = add_second_element(lib, skill, element, rng.fork(element))
            if made is not None:
                dual.append(skill_signature(lib, made))
    drained = []
    if lifesteal_ready(lib, skill):  # SK-5：吸血版本
        made = add_lifesteal(lib, skill, Rng(seed).fork("wish-coverage.lifesteal"))
        if made is not None:
            drained.append(skill_signature(lib, made))
    if not swapped and not dual and not drained:
        return ""
    out = f"{DERIVED_SEP}R{';'.join(swapped)}{DERIVED_SEP}D{';'.join(dual)}"
    return out + (f"{DERIVED_SEP}L{';'.join(drained)}" if drained else "")


def attempt(lib: ContentLibrary, bucket: Bucket, seed: int) -> tuple[str, str]:
    """一個種子：回傳（結果, 標籤簽名＋衍生版本）；結果 ``ok`` 或失敗原因。"""
    family = KIND_FAMILY[bucket.kind]
    try:
        skill = compose_with_stats(
            seed,
            tier=bucket.tier,
            rarity=bucket.rarity,
            skeleton=bucket.hint or None,
            library=lib,
            keyword=None if bucket.keyword == NO_KEYWORD else bucket.keyword,
            keyword_tries=SLOT_KEYWORD_TRIES,
            skip_legendary=True,
            kinds=family,
        ).skill
    except ComposeError:
        return "compose_error", ""
    if skill.rarity == "legendary":
        return "legendary", ""
    if skill.kind not in family:
        return "other_kind", ""
    if validate_skill(skill, lib):
        return "invalid", ""
    return "ok", skill_signature(lib, skill) + derived(lib, skill, bucket.tier, seed)


def run_bucket(bucket: Bucket, seeds: int) -> dict[str, Any]:
    lib = _library()
    started = time.perf_counter()
    reasons: Counter[str] = Counter()
    sigs: Counter[str] = Counter()
    for seed in range(seeds):
        result, sig = attempt(lib, bucket, seed)
        reasons[result] += 1
        if result == "ok":
            sigs[sig] += 1
    return {
        "key": bucket.key(),
        "seeds": seeds,
        "legal": reasons["ok"],
        "reasons": dict(sorted(reasons.items())),
        "signatures": dict(sorted(sigs.items())),
        "seconds": round(time.perf_counter() - started, 2),
    }


def _run_one(job: tuple[Bucket, int]) -> dict[str, Any]:
    return run_bucket(*job)


def player_tiers(lib: ContentLibrary) -> list[int]:
    """玩家拿得到的技能階級（同 ``scripts/recipe_census.py``）。"""
    world = lib.world_rules
    tiers = set(lib.roguelite.offer_tier_by_level)
    if world is not None:
        tiers |= set(world.hero_growth.skill_tier_by_level)
        if world.opportunity.tier_up_permille > 0:
            tiers.add(max(tiers) + 1)
    return sorted(t for t in tiers if t in lib.ruleset.core.tier_budget)


def build_buckets(lib: ContentLibrary, tiers: Sequence[int]) -> list[Bucket]:
    """一般桶（關鍵字或不指定 × 種類 × 階 × 稀有度），加上 WC-2 的召喚桶（主動、指定召喚骨架）。
    手寫技能才有的關鍵字（形態）不跑組合器（組合器做不出來，候選另外從手寫技能放）。"""
    manual = handwritten_keywords(lib)
    rows = [NO_KEYWORD, *(k.id for k in lib.keywords.keywords if k.id not in manual)]
    plain = [Bucket(k, kind, t, r) for k in rows for kind in KINDS for t in tiers for r in RARITIES]
    hinted = [Bucket(k, "active", t, r, SUMMON_HINT) for k in rows for t in tiers for r in RARITIES]
    return plain + hinted


def measure(buckets: Sequence[Bucket], seeds: int, workers: int) -> list[dict[str, Any]]:
    """每桶的結果（順序同 ``buckets``）。平行時慢的桶（反應＋指定關鍵字，每個種子要試 30 個變體）
    先送，免得最後只剩一兩個行程在跑。"""
    jobs = [(b, seeds) for b in buckets]
    if workers <= 1:
        return [_run_one(j) for j in jobs]
    order = sorted(
        jobs, key=lambda j: (j[0].kind != "reaction", j[0].keyword == NO_KEYWORD, j[0].hint)
    )
    with ProcessPoolExecutor(max_workers=min(workers, MAX_WORKERS)) as pool:
        done = {r["key"]: r for r in pool.map(_run_one, order, chunksize=1)}
    return [done[b.key()] for b in buckets]


# ---------------------------------------------------------------------------
# 彙整：成功率
# ---------------------------------------------------------------------------


type Sig = frozenset[str]
_LIFESTEAL_NEED: Sig = frozenset(f"effects:{t}" for t in LIFESTEAL_TAGS)


def _sig(text: str) -> Sig:
    return frozenset(text.split("|")) if text else frozenset()


@dataclass(frozen=True, slots=True)
class Group:
    """一個種子的結果：基本技能的標籤、換主題元素的版本、加第二元素的版本、吸血版本（SK-5）。"""

    base: Sig
    swapped: tuple[Sig, ...] = ()
    dual: tuple[Sig, ...] = ()
    drained: tuple[Sig, ...] = ()

    @classmethod
    def parse(cls, text: str) -> Group:
        parts = text.split(DERIVED_SEP)
        found = {p[0]: tuple(_sig(x) for x in p[1:].split(";") if x) for p in parts[1:] if p}
        return cls(_sig(parts[0]), found.get("R", ()), found.get("D", ()), found.get("L", ()))

    def hits(self, need: Sig, elements: int) -> bool:
        """``need`` 全帶到：基本技能；願望有元素時換元素的版本；有兩個元素時加第二元素的版本；效果
        同時有傷害和治療時吸血版本（SK-5）。"""
        if need <= self.base:
            return True
        if elements >= 1 and any(need <= s for s in self.swapped):
            return True
        if need >= _LIFESTEAL_NEED and any(need <= s for s in self.drained):
            return True
        return elements >= PAIR and any(need <= s for s in self.dual)


@dataclass(frozen=True, slots=True)
class Measured:
    """量測結果：每桶的種子數與（種子結果, 次數）；手寫技能池（形態）的簽名。"""

    seeds: dict[str, int]
    sigs: dict[str, tuple[tuple[Group, int], ...]]
    tiers: tuple[int, ...]
    kind_permille: dict[str, int]
    handwritten: dict[tuple[str, str, int], tuple[Sig, ...]] = field(default_factory=dict)
    """（關鍵字, 種類, 階）→ 手寫技能池的簽名（WC-2 形態）。"""

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
        kind_permille: Mapping[str, int],
        handwritten: Mapping[tuple[str, str, int], tuple[Sig, ...]] | None = None,
    ) -> Measured:
        seeds: dict[str, int] = {}
        sigs: dict[str, tuple[tuple[Group, int], ...]] = {}
        for row in payload["buckets"]:
            seeds[row["key"]] = int(row["seeds"])
            sigs[row["key"]] = tuple(
                (Group.parse(s), int(n)) for s, n in sorted(row["signatures"].items())
            )
        return cls(
            seeds,
            sigs,
            tuple(payload["params"]["tiers"]),
            {k: int(v) for k, v in kind_permille.items()},
            dict(handwritten or {}),
        )

    def bucket_rate(self, key: str, need: Sig, elements: int = 0) -> Fraction:
        total = self.seeds.get(key, 0)
        if total == 0:
            return Fraction(0)
        hits = sum(n for group, n in self.sigs[key] if group.hits(need, elements))
        return Fraction(hits, total)

    def _cell(self, bucket: Bucket, need: Sig, elements: int) -> Fraction:
        """一個（關鍵字, 種類）在一格的成功率：組合器的桶；效果有召喚時再看召喚桶；手寫技能池有一招
        全帶到就是 1。"""
        rate = self.bucket_rate(bucket.key(), need, elements)
        if bucket.kind == "active" and f"effects:{SUMMON_HINT}" in need:
            hinted = Bucket(bucket.keyword, bucket.kind, bucket.tier, bucket.rarity, SUMMON_HINT)
            rate = max(rate, self.bucket_rate(hinted.key(), need, elements))
        pool = self.handwritten.get((bucket.keyword, bucket.kind, bucket.tier), ())
        if any(need <= s for s in pool):
            rate = Fraction(1)
        return rate

    def rate(self, tags: Sequence[Tag], tier: int, rarity: str) -> Fraction:
        """模組說明的「一組標籤在一格的成功率」。"""
        keywords = [v for g, v in tags if g == "keywords"] or [NO_KEYWORD]
        kinds = [v for g, v in tags if g == "kinds"]
        weights = {kinds[0]: 1} if kinds else self.kind_permille
        need = frozenset(tag_code(t) for t in tags)
        elements = sum(1 for g, _ in tags if g == "elements")
        total = Fraction(0)
        for keyword in keywords:
            for kind, weight in sorted(weights.items()):
                bucket = Bucket(keyword, kind, tier, rarity)  # type: ignore[arg-type]
                total += weight * self._cell(bucket, need, elements)
        return total / (len(keywords) * sum(weights.values()))

    def cells(self) -> list[tuple[int, str]]:
        return [(t, r) for t in self.tiers for r in RARITIES]

    def row(self, tags: Sequence[Tag]) -> list[Fraction]:
        return [self.rate(tags, t, r) for t, r in self.cells()]


def permille(value: Fraction) -> int:
    return int(value * 1000)


# ---------------------------------------------------------------------------
# 分類：做不到的原因
# ---------------------------------------------------------------------------

_ONE_PER_SKILL: dict[str, tuple[str, str]] = {
    "shapes": (
        "一招只有一個目標形狀",
        "06 6.1（技能＝目標形狀＋效果原語…）；07 7.6 第 1 點（形狀最多 1 個）",
    ),
    "kinds": (
        "一招只有一個種類（主動／被動／反應）",
        "06 6.34.1（主動 70／被動 20／反應 10）；07 7.6 第 1 點（種類最多 1 個）",
    ),
}


@dataclass(frozen=True, slots=True)
class Verdict:
    category: str  # a／b／c／需人工
    reason: str
    source: str


def _effect_ways(lib: ContentLibrary, value: str) -> tuple[list[str], list[str]]:
    """效果類型標籤的原語與狀態（只列內容庫裡存在的；不存在的另外回報）。"""
    tag = next(t for t in lib.skill_pick.wish_tags.effects if t.id == value)
    return list(tag.primitives), list(tag.statuses)


def missing_parts(lib: ContentLibrary, tag: Tag) -> list[str]:
    """標籤對應的原語、狀態、形狀、關鍵字在內容庫裡找不到的（(c) 的判斷）。"""
    group, value = tag
    prims = {p.id for p in lib.ruleset.primitives.primitives}
    if group == "keywords":
        return [] if value in {k.id for k in lib.keywords.keywords} else [value]
    if group == "effects":
        names, statuses = _effect_ways(lib, value)
        known = {s.id for s in lib.ruleset.statuses.statuses}
        found = [n for n in names if n in prims] + [s for s in statuses if s in known]
        return [] if found else [*names, *statuses]
    if group == "shapes":
        shapes = next(t.shapes for t in lib.skill_pick.wish_tags.shapes if t.id == value)
        known_shapes = {s.id for s in lib.ruleset.shapes.shapes}
        return [] if set(shapes) & known_shapes else list(shapes)
    return []


def handwritten_example(lib: ContentLibrary, tags: Sequence[Tag]) -> str | None:
    """手寫技能裡同時帶這些標籤的一招（ID 最小的；證明引擎做得到）。"""
    need = frozenset(tag_code(t) for t in tags)
    for skill_id in sorted(lib.skills):
        skill = lib.skills[skill_id]
        if skill.rarity == "legendary":
            continue
        if need <= frozenset(skill_signature(lib, skill).split("|")):
            return skill_id
    return None


def _keyword_composable(lib: ContentLibrary, keyword: str) -> bool:
    found = next((k for k in lib.keywords.keywords if k.id == keyword), None)
    return found is None or found.composable


def kind_shapes(lib: ContentLibrary, kind: str) -> set[str]:
    """這個種類（一族）用得到的形狀：啟用的骨架裡 ``kinds`` 有它的，形狀聯集（驗證器
    ``skeleton.shape`` 擋其他形狀）。"""
    family = set(KIND_FAMILY[kind])
    out: set[str] = set()
    for skeleton in lib.skeletons.values():
        if skeleton.enabled and family & set(skeleton.kinds):
            out |= set(skeleton.shapes)
    if kind == "passive" and "self" in out:
        out.add("single")  # WC-2（#167）：被動作用在觸發的那個人算「單體」
    return out


def _kind_shape_block(lib: ContentLibrary, tags: Sequence[Tag]) -> Verdict | None:
    groups = {g: v for g, v in tags}
    if len(tags) != PAIR or "kinds" not in groups or "shapes" not in groups:
        return None
    kind, shape = groups["kinds"], groups["shapes"]
    wanted = next(t.shapes for t in lib.skill_pick.wish_tags.shapes if t.id == shape)
    allowed = kind_shapes(lib, kind)
    if set(wanted) & allowed:
        return None
    files = sorted(
        s.id for s in lib.skeletons.values() if s.enabled and set(KIND_FAMILY[kind]) & set(s.kinds)
    )
    return Verdict(
        "b",
        f"{tag_label(lib, 'kinds', kind)}技能的骨架形狀只有 {'、'.join(sorted(allowed))}"
        f"（驗證器 skeleton.shape）",
        f"06 6.9 技能骨架；content/skeletons/{'、'.join(files)}.yaml 的 shapes",
    )


def rule_verdict(lib: ContentLibrary, tags: Sequence[Tag]) -> Verdict | None:
    """(b) 規則禁止、(c) 沒有原語；都不是＝``None``。"""
    if len(tags) == PAIR and tags[0][0] == tags[1][0] and tags[0][0] in _ONE_PER_SKILL:
        reason, source = _ONE_PER_SKILL[tags[0][0]]
        return Verdict("b", reason, source)
    blocked = _kind_shape_block(lib, tags)
    if blocked is not None:
        return blocked
    missing = [m for t in tags for m in missing_parts(lib, t)]
    if missing:
        return Verdict("c", f"內容庫沒有這些原語／狀態／形狀：{'、'.join(missing)}", "—")
    return None


def _stack_keywords(lib: ContentLibrary) -> set[str]:
    """組合器會抽的層數關鍵字（同 ``random_composer._is_stack_keyword``）。"""
    return {s.id for s in lib.ruleset.stacks.stacks if s.composer}


def _composer_recipe(lib: ContentLibrary, tags: Sequence[Tag], example: str | None) -> str | None:
    """看得出是組合器配方造成的（a）：回傳理由；看不出＝``None``。"""
    has = f"手寫技能 `{example}` 有；" if example is not None else ""
    off = [v for g, v in tags if g == "keywords" and not _keyword_composable(lib, v)]
    if off:
        return (
            f"{has}關鍵字 {'、'.join(off)} 組合器不做（composable: false）；WC-2 起候選另外"
            "放進同關鍵字的手寫技能，但手寫技能沒有一招同時帶到這些標籤"
        )
    stacks = [v for g, v in tags if g == "keywords" and v in _stack_keywords(lib)]
    if stacks:
        return (
            f"{has}層數關鍵字（{'、'.join(stacks)}）：組合器用蓄力骨架 `{_STACK_SKELETON}`，或"
            "WC-2 的附帶配方（主動技多累積或消耗一種層數，限範圍、控場、位移、連段、召喚等允許的"
            "骨架）都沒做出來"
        )
    for group, value in tags:
        if group != "effects":
            continue
        names, statuses = _effect_ways(lib, value)
        if not statuses and set(names) <= _HAND_WRITTEN_PRIMITIVES:
            return (
                f"{has}{tag_label(lib, group, value)}的原語（{'、'.join(names)}）組合器不抽"
                "（手寫／閃現轉型專用），只在少數骨架的特殊路徑出現"
            )
    return None


_EXCLUSION_HINTS: dict[frozenset[str], str] = {
    frozenset({"effects:damage", "effects:heal"}): "no_damage_with_ally_heal",
}
"""部分被互斥規則擋下的組合（``content/skill_exclusions.yaml``）：擋掉一部分寫法，剩下的寫法規則
允許，所以程式判斷不了是 (a) 還是 (b)。"""


def classify(lib: ContentLibrary, tags: Sequence[Tag], singles: Mapping[Tag, int]) -> Verdict:
    """做不到（或極低）的組合的分類。``singles``＝每個標籤單獨的最佳一格（‰）。"""
    ruled = rule_verdict(lib, tags)
    if ruled is not None:
        return ruled
    example = handwritten_example(lib, tags)
    recipe = _composer_recipe(lib, tags, example)
    if recipe is not None:
        return Verdict("a", recipe, "—")
    weak = [t for t in tags if singles.get(t, 0) == 0]
    if weak and len(tags) == PAIR:
        names = "、".join(tag_label(lib, g, v) for g, v in weak)
        return Verdict("a", f"{names}單獨就做不到（見單一標籤的分類）；組合跟著做不到", "—")
    labels = "＋".join(tag_label(lib, g, v) for g, v in tags)
    if example is not None:
        return Verdict(
            "a", f"手寫技能 `{example}` 同時帶{labels}：引擎做得到，組合器沒有這個配方", "—"
        )
    rule = _EXCLUSION_HINTS.get(frozenset(tag_code(t) for t in tags))
    if rule is not None:
        found = next(r for r in lib.exclusions.rules if r.id == rule)
        return Verdict(
            "需人工",
            f"互斥規則 `{rule}` 擋掉一部分寫法（{found.message_zh}）；剩下的寫法規則允許但組合器"
            "沒做，手寫技能也沒有例子",
            "content/skill_exclusions.yaml；06 6.6 互斥規則表、6.18 A、B（吸血與聖光雙效放寬）",
        )
    return Verdict(
        "需人工",
        "原語都在、沒有找到禁止的規則，但手寫技能也沒有同時帶的例子：可能是缺配方 (a)，"
        "也可能有沒寫成資料的限制",
        "—",
    )


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Coverage:
    """彙整好的結果：單一標籤與每一對的各格成功率（‰），做不到與極低的分類。"""

    tags: tuple[Tag, ...]
    cells: tuple[tuple[int, str], ...]
    singles: dict[Tag, list[int]]
    pairs: dict[tuple[Tag, Tag], list[int]]
    misses: list[tuple[tuple[Tag, ...], str, Verdict]]
    """（組合, ``none``＝每一格都 0／``low``＝最好的一格低於 :data:`LOW_PERMILLE`, 分類）"""


def build_coverage(lib: ContentLibrary, measured: Measured) -> Coverage:
    tags = tuple(all_tags(lib))
    singles = {t: [permille(v) for v in measured.row((t,))] for t in tags}
    pairs = {(a, b): [permille(v) for v in measured.row((a, b))] for a, b in combinations(tags, 2)}
    best = {t: max(row) for t, row in singles.items()}
    misses: list[tuple[tuple[Tag, ...], str, Verdict]] = []
    rows: Iterable[tuple[tuple[Tag, ...], list[int]]] = [
        *(((t,), r) for t, r in singles.items()),
        *(((a, b), r) for (a, b), r in pairs.items()),
    ]
    for combo, row in rows:
        top = max(row)
        if top >= LOW_PERMILLE:
            continue
        misses.append((combo, "none" if top == 0 else "low", classify(lib, combo, best)))
    return Coverage(tags, tuple(measured.cells()), singles, pairs, misses)


def _pct(value: int) -> str:
    """千分比 → 百分比文字（0 寫「0」，不到 1% 寫「<1」）。"""
    if value == 0:
        return "0"
    if value < PER_PERCENT:
        return "<1"
    return str(round(value / PER_PERCENT))


def _label(lib: ContentLibrary, tag: Tag) -> str:
    return tag_label(lib, *tag)


_GROUP_ZH = {
    "keywords": "關鍵字",
    "elements": "元素",
    "effects": "效果",
    "shapes": "形狀",
    "kinds": "種類",
}
_RARITY_ZH = {"common": "普", "rare": "稀", "epic": "史"}


def _single_table(lib: ContentLibrary, cov: Coverage) -> list[str]:
    head = (
        "| 類別 | 標籤 | "
        + " | ".join(f"{t}{_RARITY_ZH[r]}" for t, r in cov.cells)
        + " | 最佳 | 平均 |"
    )
    lines = [head, "|" + "---|" * (len(cov.cells) + 4)]
    for tag in cov.tags:
        row = cov.singles[tag]
        mean = sum(row) // len(row)
        cells = " | ".join(_pct(v) for v in row)
        lines.append(
            f"| {_GROUP_ZH[tag[0]]} | {_label(lib, tag)} | {cells} "
            f"| {_pct(max(row))} | {_pct(mean)} |"
        )
    return lines


def _pair_matrix(lib: ContentLibrary, cov: Coverage) -> list[str]:
    """配對矩陣：每一格＝那一對在 12 格裡最好的一格（%）；「·」＝0。"""
    index = {t: i for i, t in enumerate(cov.tags)}
    head = "| | " + " | ".join(str(i + 1) for i in range(len(cov.tags))) + " |"
    lines = [head, "|" + "---|" * (len(cov.tags) + 1)]
    for a in cov.tags:
        cells = []
        for b in cov.tags:
            if a == b:
                cells.append("—")
                continue
            pair = (a, b) if index[a] < index[b] else (b, a)
            top = max(cov.pairs[pair])
            cells.append("·" if top == 0 else _pct(top))
        lines.append(f"| {index[a] + 1} {_label(lib, a)} | " + " | ".join(cells) + " |")
    return lines


def _miss_table(lib: ContentLibrary, cov: Coverage, status: str) -> list[str]:
    lines = ["| 組合 | 最佳格 | 類別 | 理由 | 出處 |", "|---|---|---|---|---|"]
    for combo, found, verdict in cov.misses:
        if found != status:
            continue
        name = "＋".join(f"{_label(lib, t)}（{_GROUP_ZH[t[0]]}）" for t in combo)
        row = cov.singles[combo[0]] if len(combo) == 1 else cov.pairs[(combo[0], combo[1])]
        lines.append(
            f"| {name} | {_pct(max(row))}% | {verdict.category} | {verdict.reason} "
            f"| {verdict.source} |"
        )
    return lines


def category_counts(cov: Coverage) -> dict[str, Counter[str]]:
    out: dict[str, Counter[str]] = {"none": Counter(), "low": Counter()}
    for _combo, found, verdict in cov.misses:
        out[found][verdict.category] += 1
    return out


def render(lib: ContentLibrary, cov: Coverage, payload: Mapping[str, Any]) -> str:
    params = payload["params"]
    counts = category_counts(cov)
    n_pairs = len(cov.pairs)

    def summary(status: str) -> str:
        found = counts[status]
        parts = "、".join(f"{c} {found[c]}" for c in ("a", "b", "c", "需人工"))
        return f"{sum(found.values())} 項（{parts}）"

    keywords = sum(1 for t in cov.tags if t[0] == "keywords")
    lines = [
        "# 許願覆蓋表",
        "",
        "由 `scripts/wish_coverage.py report` 從 `docs/phases/WC-2資料/buckets.json` 產生"
        f"（格式 `{FORMAT}`），不要手改。資料檔不進版控，重產照 `scripts/wish_coverage.py` "
        "開頭的說明（先 `run` 再 `report`）。"
        "舊表（WC-1）留在 `docs/phases/許願覆蓋表.md` 對照。",
        "",
        f"- 標籤：許願池固定清單 {len(cov.tags)} 個（`content/skill_pick.yaml` 的 `wish_tags`；"
        f"關鍵字＝內容庫的 {keywords} 個），配對 {n_pairs} 組。",
        f"- 每格：階級 {params['tiers']} × 稀有度 普通／稀有／史詩；每個"
        "（關鍵字或不指定, 種類, 階級, 稀有度）桶"
        f"用種子 0～{params['seeds'] - 1} 各跑一次組合器（{len(payload['buckets'])} 桶）。",
        "- 成功＝做出合法的完整技能，而且這些標籤全部帶到（判定同許願池的 `tag_hits`，"
        "關鍵字只看專屬規則）。有關鍵字或種類標籤時照許願池指定給組合器；"
        "沒有種類標籤時照主動 70／被動 20／反應 10 加權。",
        "- 被動的骨架至少史詩、反應至少稀有（06 6.12「目前實作」），"
        "所以「被動」「反應」在較低稀有度一定是 0。",
        "- WC-2（#167）：願望有元素時另算組合器「換主題元素」的版本，有兩個元素時另算「加第二元素」"
        "（2 階起；物理＋元素 1 階起，WC-2b）；效果有召喚時主動另看指定召喚骨架的桶；"
        "形態的候選另外放進手寫形態技"
        "（有一招全帶到＝100%，每個稀有度欄都一樣）。",
        "- SK-5：效果同時有傷害和治療時，另算打擊、範圍骨架的主動技加上吸血的版本。",
        f"- 做不到＝每一格都 0；極低＝最好的一格也不到 {LOW_PERMILLE / 10:g}%。",
        "",
        "## 摘要",
        "",
        f"- 做不到：{summary('none')}",
        f"- 極低：{summary('low')}",
        "- 類別：a＝引擎有原語、組合器缺配方；b＝規則禁止；c＝連原語都沒有；需人工＝程式判斷不了。",
        "",
        "## 單一標籤（成功率 %，欄＝階級＋稀有度：普＝普通、稀＝稀有、史＝史詩）",
        "",
        *_single_table(lib, cov),
        "",
        "## 配對（最好的一格，%；「·」＝每一格都 0）",
        "",
        "列與欄的編號相同（第 1 列＝第 1 欄）。",
        "",
        *_pair_matrix(lib, cov),
        "",
        "## 做不到清單（每一格都 0）",
        "",
        *_miss_table(lib, cov, "none"),
        "",
        f"## 極低清單（最好的一格不到 {LOW_PERMILLE / 10:g}%）",
        "",
        *_miss_table(lib, cov, "low"),
        "",
        "## 玩家常許但不在標籤清單的願望（玩法 PM 補）",
        "",
        "| 願望原話 | 最接近的標籤 | 缺的是什麼 | 備註 |",
        "|---|---|---|---|",
        "",
    ]
    return "\n".join(lines)


def handwritten_sigs(
    lib: ContentLibrary, tiers: Sequence[int]
) -> dict[tuple[str, str, int], tuple[Sig, ...]]:
    """手寫技能池（WC-2 形態）每個（關鍵字, 種類, 階）的簽名（同
    ``wish_pick.handwritten_pool``）。"""
    out: dict[tuple[str, str, int], tuple[Sig, ...]] = {}
    for keyword in sorted(handwritten_keywords(lib)):
        for kind in KINDS:
            for tier in tiers:
                skills = handwritten_pool(lib, keyword, tier, KIND_FAMILY[kind])
                out[(keyword, kind, tier)] = tuple(_sig(skill_signature(lib, s)) for s in skills)
    return out


def load_measured(lib: ContentLibrary, path: Path) -> tuple[Measured, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != FORMAT:
        raise SystemExit(f"{path} 不是 {FORMAT}")
    weights = {str(k): int(v) for k, v in lib.composer.whiteboard.kind_permille.items()}
    tiers = tuple(int(t) for t in payload["params"]["tiers"])
    measured = Measured.from_payload(payload, weights, handwritten_sigs(lib, tiers))
    return measured, payload


def _miss_names(text: str, title: str) -> list[str]:
    """覆蓋表某一節（做不到清單／極低清單）的組合名稱（表格第一欄，依原順序）。"""
    names: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith(f"## {title}")
            continue
        if inside and line.startswith("| ") and not line.startswith("| 組合"):
            names.append(line.split(" | ")[0].removeprefix("| ").strip())
    return names


def compare_lines(old_text: str, new_text: str) -> list[str]:
    """和舊表（WC-1）對照：做不到 → 做得到、做不到 → 極低、還剩做不到（新出現的另列）。"""
    old_none = _miss_names(old_text, "做不到清單")
    new_none = set(_miss_names(new_text, "做不到清單"))
    new_low = set(_miss_names(new_text, "極低清單"))
    fixed = [n for n in old_none if n not in new_none and n not in new_low]
    low = [n for n in old_none if n in new_low]
    still = [n for n in old_none if n in new_none]
    added = sorted(new_none - set(old_none))

    def block(title: str, names: Sequence[str]) -> list[str]:
        return [f"### {title}（{len(names)}）", "", *(f"- {n}" for n in names), ""]

    return [
        "## 和 WC-1 舊表對照（`docs/phases/許願覆蓋表.md` 的做不到清單）",
        "",
        f"舊表做不到 {len(old_none)} 組 → 新表做不到 {len(new_none)} 組、極低 {len(new_low)} 組。",
        "",
        *block("做不到 → 做得到（最好的一格 ≥ 2%）", fixed),
        *block("做不到 → 極低（最好的一格 < 2%）", low),
        *block("還是做不到", still),
        *block("新出現的做不到（舊表沒有）", added),
    ]


def cmd_report(args: argparse.Namespace) -> int:
    if not args.data.exists():  # SK-4：資料不進版控，要先在本機重產
        print(
            f"找不到 {args.data}（不進版控）：先跑 "
            "uv run python scripts/wish_coverage.py run --seeds 40 --workers 8",
            file=sys.stderr,
        )
        return 2
    lib = load_library()
    measured, payload = load_measured(lib, args.data)
    cov = build_coverage(lib, measured)
    text = render(lib, cov, payload)
    if args.old.exists():
        old = args.old.read_text(encoding="utf-8")
        text = text.rstrip("\n") + "\n\n" + "\n".join(compare_lines(old, text)) + "\n"
    args.out.write_text(text, encoding="utf-8", newline="\n")
    counts = category_counts(cov)
    print(f"{args.out}：做不到 {dict(counts['none'])}、極低 {dict(counts['low'])}")
    return 0


# ---------------------------------------------------------------------------
# 命令列
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    lib = load_library()
    tiers = [int(t) for t in args.tiers.split(",")] if args.tiers else player_tiers(lib)
    buckets = build_buckets(lib, tiers)
    if args.keywords:
        wanted = set(args.keywords.split(","))
        buckets = [b for b in buckets if b.keyword in wanted]
    started = time.perf_counter()
    results = measure(buckets, args.seeds, args.workers)
    elapsed = round(time.perf_counter() - started, 1)
    payload = {
        "format": FORMAT,
        "params": {
            "seeds": args.seeds,
            "tiers": tiers,
            "rarities": list(RARITIES),
            "kinds": list(KINDS),
            "workers": args.workers,
        },
        "elapsed_s": elapsed,
        "buckets": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(results)} 桶 × {args.seeds} 種子（{elapsed} 秒）→ {args.out}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="許願覆蓋表（WC-1）")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="量測：每桶跑組合器，寫 JSON")
    run.add_argument("--seeds", type=int, default=DEFAULT_SEEDS, help="每桶種子數（0～N-1）")
    run.add_argument("--workers", type=int, default=1, help=f"平行行程數（最多 {MAX_WORKERS}）")
    run.add_argument("--tiers", help="逗號分隔；預設＝玩家拿得到的所有階級")
    run.add_argument("--keywords", help=f"只跑這些關鍵字桶（逗號分隔；{NO_KEYWORD}＝不指定）")
    run.add_argument("--out", type=Path, default=DATA_DIR / "buckets.json")
    report = sub.add_parser("report", help="讀 JSON 寫覆蓋表")
    report.add_argument("--data", type=Path, default=DATA_DIR / "buckets.json")
    report.add_argument("--out", type=Path, default=REPORT)
    report.add_argument("--old", type=Path, default=OLD_REPORT, help="對照的舊表（WC-1）")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    return cmd_report(args)


if __name__ == "__main__":
    sys.exit(main())
