"""物品產生器（Phase 3K-1，``docs/design/08-裝備.md`` 8.22.1）。

給 3K-2 戰後裝備三選一，之後的掉落與打造沿用。:func:`generate_item` 是純函式：只用傳入的
:class:`~trpg.shared.rng.Rng`，相同種子與參數必得相同物品。

1. **底材**：主手從 ``weapons.yaml``（不含召喚物專用，可限定武器大類）；副手從 ``offhands.yaml``
   （外觀與標籤沿用 ``items.yaml`` 裡沒有詞條的副手本體）；其他部位從外觀清單的造型
   （``equipment/appearance.yaml``；防具目前沒有基礎數值資料，只有詞條）。
2. **詞條**：依稀有度（``item_gen.yaml`` 的 ``rarities``）決定條數與可用類別；稀有起第 1 條是
   build 詞條（``required_picks``）。每一步從「放得進剩餘預算、且替後面每條留下至少 2 點」的詞條
   中抽：同一族（六屬性、8 種普攻附加元素、8 種武器元素）先算一個候選，抽中再選成員；武器上的
   屬性依縮放屬性偏好。數值取放得進的最大值（8.22.1 第 4 點）。點數不到預算 70% 時重抽（最多
   ``max_attempts`` 次），再不行用「每步挑點數最高」的確定性方法；普通物品沒有詞條時，詞條部分
   換成基礎加成。
3. **名稱**：程式產生「稀有度＋底材名」（#44 原則；LLM 命名留給 Phase 4 之後）；詞條文字照白名單
   模板。
4. **傳說**：不產生；從現有傳說物品挑同部位（主手還要同武器大類）的，沒有就降為史詩
   （8.22.1 第 7 點）。

輸出一律通過 :func:`~trpg.content.item_budget.item_budget_problems` 與
:func:`~trpg.content.equipment.item_problems`（產生後自我檢查，不通過就拋出
:class:`ItemGenError`）。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Literal

from trpg.content.battle import OffhandDef, WeaponDef
from trpg.content.equipment import (
    AffixDef,
    AffixRoll,
    AttackAffix,
    ItemDef,
    StatAffix,
    TriggerAffix,
    affix_slot_problems,
    affix_strength,
    item_problems,
)
from trpg.content.item_budget import (
    RARITY_ZH,
    ItemGenRules,
    Rarity,
    RarityRule,
    affix_budget,
    affix_points,
    base_bonus_points,
    item_budget_problems,
)
from trpg.content.library import ContentLibrary
from trpg.content.slots import SLOT_TYPE_OF, SlotType
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute

__all__ = ["ItemGenError", "generate_item", "roll_rarity"]

type WeaponClass = Literal["melee", "ranged", "focus"]
_PERMILLE = 1000


class ItemGenError(ValueError):
    """產生器無法產生合規物品（資料或參數有問題）。"""


@dataclass(frozen=True, slots=True)
class _Base:
    """底材：物品除了詞條以外的欄位。"""

    slot_type: SlotType
    name_zh: str
    weapon: WeaponDef | None = None
    offhand: OffhandDef | None = None
    paired: bool = False
    tags: tuple[str, ...] = ()
    kind: str | None = None
    form: str | None = None
    material: str | None = None


@dataclass(frozen=True, slots=True)
class _Pick:
    affix: AffixDef
    value: int | None
    points: Fraction


def _rules(library: ContentLibrary) -> ItemGenRules:
    if library.item_gen is None:
        raise ItemGenError("內容庫沒有 item_gen.yaml")
    return library.item_gen


def roll_rarity(library: ContentLibrary, rng: Rng) -> Rarity:
    """依 ``rarity_weights`` 抽一個稀有度（權重 0 的不會抽到）。"""
    weights = _rules(library).rarity_weights
    order: list[Rarity] = ["common", "uncommon", "rare", "epic", "legendary"]
    pool = [(r, weights.get(r, 0)) for r in order if weights.get(r, 0) > 0]
    return _weighted(rng, pool)


def _weighted[T](rng: Rng, pool: Sequence[tuple[T, int]]) -> T:
    total = sum(w for _, w in pool)
    roll = rng.randint(0, total - 1)
    for value, weight in pool:
        if roll < weight:
            return value
        roll -= weight
    raise AssertionError("unreachable")


# ---------------------------------------------------------------------------
# 底材
# ---------------------------------------------------------------------------


def _weapon_base(library: ContentLibrary, rng: Rng, weapon_class: WeaponClass | None) -> _Base:
    pool = sorted(
        (
            w
            for w in library.weapons.values()
            if not w.summon_only and (weapon_class is None or w.weapon_class == weapon_class)
        ),
        key=lambda w: w.id,
    )
    if not pool:
        raise ItemGenError(f"沒有武器大類 {weapon_class} 的武器可以當底材")
    weapon = rng.choice(pool)
    look = weapon.look
    return _Base(
        slot_type="weapon",
        name_zh=weapon.name_zh,
        weapon=weapon,
        paired=weapon.paired,
        kind=None if look is None else look.kind,
        form=None if look is None else look.form,
        material=None if look is None else look.material,
    )


def _offhand_base(library: ContentLibrary, rng: Rng) -> _Base:
    pool = sorted(library.offhands.values(), key=lambda o: o.id)
    if not pool:
        raise ItemGenError("沒有副手可以當底材")
    offhand = rng.choice(pool)
    body = next(
        (
            i
            for i in sorted(library.items.values(), key=lambda i: i.id)
            if i.offhand == offhand.id and not i.affixes
        ),
        None,
    )
    return _Base(
        slot_type="offhand",
        name_zh=offhand.name_zh,
        offhand=offhand,
        tags=() if body is None else body.tags,
        kind=None if body is None else body.kind,
        form=None if body is None else body.form,
        material=None if body is None else body.material,
    )


def _look_base(library: ContentLibrary, rng: Rng, slot_type: SlotType) -> _Base:
    table = library.appearance
    kinds = [] if table is None else [k for k in table.kinds if k.slot_type == slot_type]
    if not kinds:
        return _Base(slot_type=slot_type, name_zh=_SLOT_NAME[slot_type])
    kind = rng.choice(kinds)
    form = rng.choice(kind.forms)
    return _Base(
        slot_type=slot_type,
        name_zh=kind.name_zh,
        kind=kind.id,
        form=form.id,
        material=kind.form_default(form),
    )


_SLOT_NAME: dict[str, str] = {
    "head": "頭盔",
    "body": "護甲",
    "hands": "手套",
    "feet": "鞋",
    "neck": "項鍊",
    "ring": "戒指",
}


def _base(
    library: ContentLibrary, rng: Rng, slot_type: SlotType, weapon_class: WeaponClass | None
) -> _Base:
    if slot_type == "weapon":
        return _weapon_base(library, rng, weapon_class)
    if slot_type == "offhand":
        return _offhand_base(library, rng)
    return _look_base(library, rng, slot_type)


def _probe(base: _Base) -> ItemDef:
    """檢查詞條能不能掛時用的物品（只有底材欄位）。"""
    return ItemDef(
        id="item_gen_probe",
        name_zh=base.name_zh,
        slot_type=base.slot_type,
        weapon=None if base.weapon is None else base.weapon.id,
        offhand=None if base.offhand is None else base.offhand.id,
        offhand_def=base.offhand,
        paired=base.paired,
        tags=base.tags,
    )


# ---------------------------------------------------------------------------
# 詞條
# ---------------------------------------------------------------------------


def _family(affix: AffixDef) -> str:
    """同一族的詞條只算一個候選（避免 8 種元素、6 種屬性擠掉其他詞條）。"""
    if isinstance(affix, StatAffix) and affix.stat == "attribute":
        return "family:attribute"
    if isinstance(affix, AttackAffix) and affix.add_element is not None:
        return "family:attack_element"
    if isinstance(affix, AttackAffix) and affix.weapon_element is not None:
        return "family:weapon_element"
    return affix.id


def _best_value(
    rules: ItemGenRules, affix: AffixDef, allowance: Fraction
) -> tuple[int | None, Fraction] | None:
    """放得進 ``allowance`` 的最強數值與點數；放不進（或少於每條最低點數）時為 ``None``。"""
    floor = rules.min_affix_points
    if affix.value is None:
        points = affix_points(rules, affix, None)
        return (None, points) if floor <= points <= allowance else None
    lo, hi = affix.value.min, affix.value.max
    fixed = affix_points(rules, affix, lo) == affix_points(rules, affix, hi)
    if fixed:  # 點數和數值無關：取最強的數值
        value = max((lo, hi), key=lambda v: affix_strength(affix, v))
        points = affix_points(rules, affix, value)
        return (value, points) if floor <= points <= allowance else None
    for value in range(hi, lo - 1, -1):
        points = affix_points(rules, affix, value)
        if points <= allowance:
            return (value, points) if points >= floor else None
    return None


_ONE_PER_ITEM = frozenset({"family:attack_element", "family:weapon_element"})


def _compatible(affix: AffixDef, chosen: Sequence[_Pick]) -> bool:
    """同一件裝備的組合限制：不重複、觸發最多 1 條、武器元素與普攻附加元素各最多 1 條、符文的
    「刻」與「引爆」不同時出現。"""
    family = _family(affix)
    for pick in chosen:
        other = pick.affix
        if other.id == affix.id:
            return False
        if family in _ONE_PER_ITEM and _family(other) == family:
            return False
        if isinstance(affix, TriggerAffix) and isinstance(other, TriggerAffix):
            return False
        if (
            isinstance(affix, AttackAffix)
            and isinstance(other, AttackAffix)
            and {affix.rune, other.rune} == {"inscribe", "detonate"}
        ):
            return False
    return True


@dataclass(frozen=True, slots=True)
class _Context:
    rules: ItemGenRules
    base: _Base
    pool: tuple[AffixDef, ...]
    """這件物品能掛、稀有度允許的詞條（依 id）。"""
    required: tuple[AffixDef, ...]
    """build 詞條的候選（稀有起；沒有時為空）。"""


def _context(library: ContentLibrary, base: _Base, rule: RarityRule) -> _Context:
    rules = _rules(library)
    probe = _probe(base)
    fits = [
        a
        for _, a in sorted(library.affixes.items())
        if not a.legendary_only and not affix_slot_problems(probe, a, base.weapon, library.weapons)
    ]
    pick = rules.required_picks.get(base.slot_type) if rule.required else None
    required = tuple(a for a in fits if pick is not None and pick.allows(a))
    pool = tuple(a for a in fits if a.category in rule.categories)
    return _Context(rules=rules, base=base, pool=pool, required=required)


def _attribute_weight(rules: ItemGenRules, base: _Base, attribute: Attribute | None) -> int:
    weapon = base.weapon
    if weapon is None or attribute is None:
        return _PERMILLE
    preferred = {weapon.scaling_attr}
    if weapon.secondary_scaling_attr is not None:
        preferred.add(weapon.secondary_scaling_attr)
    share = rules.weapon_attribute_preference_permille
    others = len(Attribute) - len(preferred)
    if attribute in preferred:
        return share * others  # 縮放屬性平分 share；乘上 others／len(preferred) 的公倍數以免小數
    return (_PERMILLE - share) * len(preferred)


def _choose_member(ctx: _Context, rng: Rng, members: Sequence[AffixDef]) -> AffixDef:
    if len(members) == 1:
        return members[0]
    if all(isinstance(a, StatAffix) and a.stat == "attribute" for a in members):
        pool = [
            (a, _attribute_weight(ctx.rules, ctx.base, a.attribute))  # type: ignore[union-attr]
            for a in members
        ]
        return _weighted(rng, pool)
    return rng.choice(members)


def _fill(
    ctx: _Context,
    count: int,
    choose: Callable[
        [list[tuple[AffixDef, int | None, Fraction]]], tuple[AffixDef, int | None, Fraction]
    ],
    budget: int,
) -> list[_Pick]:
    """依序挑 ``count`` 條詞條，每一步替後面每條留下最低點數。放不下時先減少條數（照「每條至少
    2 點」下修，08 8.22）；第 1 條 build 詞條在只剩 1 條也放不下時，改從一般候選挑。"""
    chosen: list[_Pick] = []
    remaining = Fraction(budget)
    floor = ctx.rules.min_affix_points
    while len(chosen) < count:
        index = len(chosen)
        allowance = remaining - floor * (count - index - 1)
        want_required = index == 0 and bool(ctx.required)
        options = _options(ctx, ctx.required if want_required else ctx.pool, chosen, allowance)
        if not options and count > index + 1:
            count -= 1
            continue
        if not options and want_required:
            options = _options(ctx, ctx.pool, chosen, allowance)
        if not options:
            break
        affix, value, points = choose(options)
        chosen.append(_Pick(affix, value, points))
        remaining -= points
    return chosen


def _options(
    ctx: _Context, source: Sequence[AffixDef], chosen: Sequence[_Pick], allowance: Fraction
) -> list[tuple[AffixDef, int | None, Fraction]]:
    found: list[tuple[AffixDef, int | None, Fraction]] = []
    for affix in source:
        if not _compatible(affix, chosen):
            continue
        best = _best_value(ctx.rules, affix, allowance)
        if best is not None:
            found.append((affix, best[0], best[1]))
    return found


def _random_chooser(
    ctx: _Context, rng: Rng
) -> Callable[[list[tuple[AffixDef, int | None, Fraction]]], tuple[AffixDef, int | None, Fraction]]:
    def choose(
        options: list[tuple[AffixDef, int | None, Fraction]],
    ) -> tuple[AffixDef, int | None, Fraction]:
        families: dict[str, list[tuple[AffixDef, int | None, Fraction]]] = {}
        for option in options:
            families.setdefault(_family(option[0]), []).append(option)
        family = families[rng.choice(sorted(families))]
        member = _choose_member(ctx, rng, [o[0] for o in family])
        return next(o for o in family if o[0] is member)

    return choose


def _greedy(
    options: list[tuple[AffixDef, int | None, Fraction]],
) -> tuple[AffixDef, int | None, Fraction]:
    """點數最高、同點數依 id（確定性的後備方法）。"""
    return max(options, key=lambda o: o[2])  # options 依 id 排序，同點數取第一個


def _enough(ctx: _Context, picks: Sequence[_Pick], budget: int) -> bool:
    total = sum((p.points for p in picks), Fraction(0))
    return total * _PERMILLE >= budget * ctx.rules.min_fill_permille and total <= budget


def _roll_affixes(
    ctx: _Context, rng: Rng, rule: RarityRule, budget: int, *, common: bool
) -> tuple[list[_Pick], int]:
    """詞條與（普通物品的）基礎加成（‰）。"""
    rules = ctx.rules
    for _ in range(rules.max_attempts):
        count = rng.randint(rule.min_affixes, rule.max_affixes)
        picks = _fill(ctx, count, _random_chooser(ctx, rng), budget)
        if picks and _enough(ctx, picks, budget):
            return picks, 0
        if not picks and common:
            bonus = _base_bonus(rules, budget)
            if bonus is not None:
                return [], bonus
    # 後備：每步挑點數最高；build 詞條放進去就到不了 70% 時（小部位），改成不強制 build 詞條
    for fallback in (ctx, replace(ctx, required=())):
        for count in range(rule.max_affixes, 0, -1):
            picks = _fill(fallback, count, _greedy, budget)
            if picks and _enough(fallback, picks, budget):
                return picks, 0
    if common:
        bonus = _base_bonus(rules, budget)
        if bonus is not None:
            return [], bonus
    raise ItemGenError(f"無法在詞條預算 {budget} 內產生合規的詞條（{ctx.base.name_zh}）")


def _base_bonus(rules: ItemGenRules, budget: int) -> int | None:
    """詞條部分換成基礎加成（無條件捨去）；達不到 70% 時為 ``None``。"""
    permille = budget // rules.base_bonus.points * rules.base_bonus.permille
    points = base_bonus_points(rules, permille)
    if points * _PERMILLE < budget * rules.min_fill_permille:
        return None
    return permille


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def _legendary(
    library: ContentLibrary, rng: Rng, slot_type: SlotType, weapon_class: WeaponClass | None
) -> ItemDef | None:
    pool = [
        i
        for _, i in sorted(library.items.items())
        if (i.legendary or i.rarity == "legendary")
        and i.slot_type == slot_type
        and (
            weapon_class is None
            or i.weapon is None
            or library.weapons[i.weapon].weapon_class == weapon_class
        )
    ]
    return rng.choice(pool) if pool else None


def _slot_type(slot: str) -> SlotType:
    if slot in SLOT_TYPE_OF:
        return SLOT_TYPE_OF[slot]
    if slot in SLOT_TYPE_OF.values():
        return slot  # type: ignore[return-value]
    raise ItemGenError(f"未知的部位：{slot}")


def generate_item(
    library: ContentLibrary,
    rng: Rng,
    slot: str,
    rarity: Rarity,
    item_level: int,
    *,
    weapon_class: WeaponClass | None = None,
) -> ItemDef:
    """產生一件物品（確定性：相同 ``rng`` 狀態與參數必得相同物品）。

    ``slot`` 可以是欄位（``main_hand``、``ring_1``……）或物品種類（``weapon``、``ring``……）；
    ``weapon_class`` 只對主手有效（主手只出同大類的武器，07 7.1）。傳說從現有傳說物品挑，沒有同部位
    的就降為史詩。"""
    if item_level < 1:
        raise ItemGenError(f"物品等級至少 1（收到 {item_level}）")
    slot_type = _slot_type(slot)
    if rarity == "legendary":
        found = _legendary(library, rng, slot_type, weapon_class)
        if found is not None:
            return found
        rarity = "epic"
    rules = _rules(library)
    rule = rules.rarity(rarity)
    base = _base(library, rng, slot_type, weapon_class)
    ctx = _context(library, base, rule)
    budget = affix_budget(rules, item_level, slot_type)
    picks, bonus = _roll_affixes(ctx, rng, rule, budget, common=rarity == "common")
    item = ItemDef(
        id=f"item_gen_{slot_type}_{rng.randint(0, 0xFFFFFFFF):08x}",
        name_zh=f"{RARITY_ZH[rarity]}{base.name_zh}",
        slot_type=slot_type,
        weapon=None if base.weapon is None else base.weapon.id,
        offhand=None if base.offhand is None else base.offhand.id,
        offhand_def=base.offhand,
        paired=base.paired,
        tags=base.tags,
        affixes=tuple(AffixRoll(affix=p.affix.id, value=p.value) for p in picks),
        kind=base.kind,
        form=base.form,
        material=base.material,
        rarity=rarity,
        item_level=item_level,
        base_bonus_permille=bonus,
    )
    problems = item_problems(
        item, library.affixes, library.weapons, library.ruleset.equipment, library.offhands
    )
    problems += item_budget_problems(rules, item, library.affixes)
    if problems:
        raise ItemGenError("；".join(problems))
    return item
