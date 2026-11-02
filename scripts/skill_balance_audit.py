"""技能模板不均衡分析（BAL-18，只讀、只量測；不改任何內容、程式與測試）。

統計五件事，輸出 Markdown 摘要表到標準輸出（相同參數必得逐字相同）：

1. 手寫技能、種子技能（完整組合器抽樣）、技能模板（白板配方實際組出的結果、閃現模板）依縮放屬性 ×
   技能種類（武器技、法術技、被動、反應、姿態、召喚）的分布。
2. 12 個關鍵字 × 縮放屬性 × 類別（武器技／法術技）、元素 × 縮放屬性 × 類別的交叉表；列出空格與少於
   3 招的組合。少於 3 招的清單與 BAL-19 的達標（2t）以 **關鍵字表** 為準（BAL-19g，玩法 PM 定）；元素欄
   只算傷害元素，僅供參考。
3. 稀有度、觸發時機、形狀的分布。
4. 依武器大類（近戰、遠程、法器、雙屬性）看每類能拿到各關鍵字技能的數量（含「同路線」）。
5. 實際候選偏離率：12 種開局 × 數十個種子的白板三選一（第 1、2 次升級）偏離張數分布。

「模板」的縮放屬性不是固定的：白板會把縮放屬性改成主角最高屬性（限在允許範圍內，武器技看武器），所以
用 ``compose_whiteboard`` 在不同武器與最高屬性下抽樣，記錄實際組得出的結果。

用法::

    uv run python scripts/skill_balance_audit.py --seeds 50 --jobs 6 --out-dir docs/phases/BAL-18
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, skill_elements, weapon_problem
from trpg.roguelite import new_keyword_run
from trpg.roguelite.offers import make_offer, weapon_scaling_attrs
from trpg.shared.types import Attribute as A
from trpg.sim.parallel import run_tasks
from trpg.skillgen.candidates import follows_attr
from trpg.skillgen.flash_category import template_kinds
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.random_composer import ComposeError, compose_random_skill, default_library
from trpg.skillgen.validate import minimum_tier
from trpg.skillgen.whiteboard import compose_whiteboard

ATTRS: tuple[A, ...] = tuple(A)
CLASSES = ("武器技", "法術技", "被動", "反應", "姿態", "召喚")
GENERIC = "generic"
SHAPE_GROUP = {
    "single": "單體",
    "self": "自身",
    "ground_tile": "地面格",
    "line": "範圍",
    "cone": "範圍",
    "cross": "範圍",
    "square3": "範圍",
    "ring": "範圍",
    "allies_in_radius": "範圍",
    "chain": "連鎖",
    "object_then_tile": "兩段",
    "unit_then_tile": "兩段",
    "unit_pair": "兩段",
}
FEW = 3  # 少於這個招數算「少」
MAX_RECIPE_TIER = 2  # 第 1、2 次升級用的角色階級上限
MAX_JOBS = 6
RARITIES = ("common", "rare", "epic", "legendary")


# ---------------------------------------------------------------------------
# 技能紀錄
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Rec:
    """一筆技能的統計用摘要。"""

    ref: str
    cls: str
    attr: str
    second: str
    category: str
    rarity: str
    trigger: str
    shape: str
    keywords: tuple[str, ...]
    elements: tuple[str, ...]
    req: str


def kind_class(skill: SkillDef) -> str:
    """技能種類：召喚、姿態、被動（含修正型）、反應、武器技、法術技。"""
    if any(e.type in ("summon", "sacrifice_summon") for e in skill.effects):
        return "召喚"
    if skill.kind == "stance":
        return "姿態"
    if skill.kind in ("passive", "modifier"):
        return "被動"
    if skill.kind == "reaction":
        return "反應"
    return "武器技" if skill.category == "weapon" else "法術技"


def trigger_of(skill: SkillDef) -> str:
    if skill.trigger is not None:
        return skill.trigger.event
    if skill.reaction is not None:
        return skill.reaction.event
    return {"stance": "(姿態)", "modifier": "(修正)"}.get(skill.kind, "(主動)")


def element_set(skill: SkillDef) -> tuple[str, ...]:
    found = {e.value for e in skill_elements(skill)}
    found |= {
        str(e.element.value)
        for e in skill.effects
        if e.type == "damage" and e.element is not None and e.element.value != "physical"
    }
    return tuple(sorted(found))


def make_rec(lib: ContentLibrary, skill: SkillDef, ref: str | None = None) -> Rec:
    kws = tuple(sorted(derive_keywords(skill, lib.keywords, exclusive_only=True).all()))
    return Rec(
        ref=ref or skill.id,
        cls=kind_class(skill),
        attr=skill.scaling_attr.value,
        second=skill.secondary_scaling_attr.value if skill.secondary_scaling_attr else "",
        category=skill.category,
        rarity=skill.rarity,
        trigger=trigger_of(skill),
        shape=skill.shape.type,
        keywords=kws or (GENERIC,),
        elements=element_set(skill),
        req=skill.weapon_req,
    )


def handwritten(lib: ContentLibrary) -> list[Rec]:
    return [make_rec(lib, lib.skills[i]) for i in sorted(lib.skills)]


def composer_sample(lib: ContentLibrary, count: int) -> tuple[list[Rec], int]:
    """完整組合器抽樣（種子 0～count-1，階級輪流 1～3）。"""
    out: list[Rec] = []
    failed = 0
    for seed in range(count):
        try:
            skill = compose_random_skill(seed, tier=1 + seed % 3, library=lib)
        except ComposeError:
            failed += 1
            continue
        out.append(make_rec(lib, skill, f"seed{seed}"))
    return out, failed


# ---------------------------------------------------------------------------
# 白板模板可達結果
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Profile:
    label: str
    group: str  # 近戰／遠程／法器／雙屬性
    weapon: str
    top: A


PROFILES: tuple[Profile, ...] = (
    Profile("劍 力量", "近戰", "one_handed_sword", A.STR),
    Profile("匕首 敏捷", "近戰", "dagger", A.DEX),
    Profile("弓 敏捷", "遠程", "bow", A.DEX),
    Profile("火杖 智力", "法器", "fire_staff", A.INT),
    Profile("權杖 感知", "法器", "scepter", A.WIS),
    Profile("圖騰杖 意志", "法器", "totem_staff", A.WIL),
    Profile("魔導劍 力量", "雙屬性", "arcane_blade", A.STR),
    Profile("魔導劍 智力", "雙屬性", "arcane_blade", A.INT),
    Profile("鐮刀 意志", "雙屬性", "scythe", A.WIL),
)
WEAPON_CLASSES = ("melee", "ranged", "focus")


@dataclass(frozen=True, slots=True)
class Draw:
    """白板配方在某個武器與最高屬性下的一次抽樣結果。"""

    recipe: str
    kind: str
    keyword: str
    species: str
    min_tier: int
    rec: Rec
    on_route: bool


def hero_attrs(top: A) -> dict[A, int]:
    return {a: 14 if a is top else 10 for a in ATTRS}


def sample_recipe(  # noqa: PLR0917 - 量測腳本，參數照配方與開局展開
    lib: ContentLibrary,
    recipe_id: str,
    kind: str,
    keyword: str,
    species: str,
    min_tier: int,
    weapon_class: str,
    top: A,
    weapon_attrs: Sequence[A],
    seeds: int,
) -> list[Draw]:
    out: list[Draw] = []
    for seed in range(seeds):
        try:
            skill = compose_whiteboard(
                seed * 7919 + 13,
                kind=kind,
                keyword=keyword,
                weapon_class=weapon_class,
                tier=max(min_tier, 1),
                library=lib,
                hero_attributes=hero_attrs(top),
                recipe_id=recipe_id,
            )
        except ComposeError:
            continue
        rec = make_rec(lib, skill, f"{recipe_id}#{seed}")
        out.append(
            Draw(
                recipe_id,
                kind,
                keyword,
                species,
                min_tier,
                rec,
                follows_attr(skill, top, tuple(weapon_attrs)),
            )
        )
    return out


def all_recipes(lib: ContentLibrary) -> list[tuple[str, str]]:
    rules = lib.composer.whiteboard
    return [(kind, r.id) for kind in ("active", "passive", "reaction") for r in rules.recipes(kind)]


def recipe_def(lib: ContentLibrary, kind: str, recipe_id: str) -> tuple[str, str, int]:
    for r in lib.composer.whiteboard.recipes(kind):
        if r.id == recipe_id:
            return r.keyword, r.species, r.min_tier
    raise KeyError(recipe_id)


def reach_draws(lib: ContentLibrary, seeds: int) -> list[Draw]:
    """可達性：3 種武器大類 × 6 種最高屬性，每個配方各抽 ``seeds`` 次。"""
    out: list[Draw] = []
    weapon_of = {"melee": "one_handed_sword", "ranged": "bow", "focus": "fire_staff"}
    for kind, rid in all_recipes(lib):
        keyword, species, min_tier = recipe_def(lib, kind, rid)
        for wc in WEAPON_CLASSES:
            attrs = weapon_scaling_attrs(lib.weapons[weapon_of[wc]])
            for top in ATTRS:
                out += sample_recipe(
                    lib, rid, kind, keyword, species, min_tier, wc, top, attrs, seeds
                )
    return out


def profile_draws(lib: ContentLibrary, seeds: int) -> dict[str, list[Draw]]:
    out: dict[str, list[Draw]] = {p.label: [] for p in PROFILES}
    for kind, rid in all_recipes(lib):
        keyword, species, min_tier = recipe_def(lib, kind, rid)
        for p in PROFILES:
            weapon = lib.weapons[p.weapon]
            out[p.label] += sample_recipe(
                lib, rid, kind, keyword, species, min_tier, weapon.weapon_class, p.top,
                weapon_scaling_attrs(weapon), seeds,
            )  # fmt: skip
    return out


# ---------------------------------------------------------------------------
# Markdown 工具
# ---------------------------------------------------------------------------


def table(header: Sequence[str], rows: Iterable[Sequence[object]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return [*lines, ""]


def attr_zh(a: str) -> str:
    return A(a).display_name


def uniq_outcomes(draws: Iterable[Draw]) -> dict[tuple[str, str, str], Rec]:
    """（配方, 種類, 縮放屬性）→ 代表紀錄；不同武器與最高屬性下重複的算一個。"""
    found: dict[tuple[str, str, str], Rec] = {}
    for d in draws:
        found.setdefault((d.recipe, d.rec.cls, d.rec.attr), d.rec)
    return found


# ---------------------------------------------------------------------------
# 1. 屬性 × 種類
# ---------------------------------------------------------------------------


def attr_by_class(recs: Iterable[Rec]) -> list[list[object]]:
    count: Counter[tuple[str, str]] = Counter((r.attr, r.cls) for r in recs)
    rows: list[list[object]] = []
    for a in ATTRS:
        cells = [count[(a.value, c)] for c in CLASSES]
        rows.append([a.display_name, *cells, sum(cells)])
    totals = [sum(count[(a.value, c)] for a in ATTRS) for c in CLASSES]
    rows.append(["合計", *totals, sum(totals)])
    return rows


def flash_template_table(lib: ContentLibrary) -> list[str]:
    table_ = lib.flash
    kinds = ("active", "passive", "reaction", "stance", "modifier")
    count: dict[tuple[str, str], int] = defaultdict(int)
    for t in table_.minor:
        for k in template_kinds(table_, t):
            count[(t.category, k)] += 1
    rows = []
    for c in table_.categories:
        if c.stage != "minor":
            continue
        rows.append([f"{c.name_zh}({c.id})", *[count[(c.id, k)] for k in kinds]])
    rows.append(["小變化合計(不重複模板)", *[
        sum(1 for t in table_.minor if k in template_kinds(table_, t)) for k in kinds
    ]])  # fmt: skip
    out = table(["小變化類別", "主動", "被動", "反應", "姿態", "修正型"], rows)
    out.append(
        f"大變化：加深／橋接共 {len(table_.major)} 個模板，額外大變化 {len(table_.extra_major)}，"
        f"轉型 {len(table_.transforms)}。"
    )
    out.append("")
    return out


def section1(lib: ContentLibrary, hand: list[Rec], comp: list[Rec], reach: list[Draw]) -> list[str]:
    head = ["縮放屬性", *CLASSES, "合計"]
    out = ["## 1. 縮放屬性 × 技能種類", ""]
    out += [f"### 1a. 手寫技能（content/skills 全部 {len(hand)} 招，含傳說）", ""]
    out += table(head, attr_by_class(hand))
    out += [f"### 1b. 種子技能（完整組合器抽樣 {len(comp)} 招，階級 1～3 輪流）", ""]
    out += table(head, attr_by_class(comp))
    uniq = uniq_outcomes(reach)
    out += [
        f"### 1c. 白板模板（{len(all_recipes(lib))} 個配方 × 3 種武器大類 × 6 種最高屬性實際組得出的"  # noqa: E501
        f"（配方, 種類, 屬性）組合共 {len(uniq)} 種）",
        "",
    ]
    out += table(head, attr_by_class(uniq.values()))
    out += ["### 1d. 閃現小變化模板 × 適用技能種類（可出這類變化的模板數）", ""]
    out += flash_template_table(lib)
    out += ["### 1e. 白板配方：種類 × 型態 × 最低階級", ""]
    count: Counter[tuple[str, str, int]] = Counter()
    for kind, rid in all_recipes(lib):
        _, species, min_tier = recipe_def(lib, kind, rid)
        count[(kind, species, min_tier)] += 1
    rows = [[k, s, t, n] for (k, s, t), n in sorted(count.items())]
    out += table(["種類", "型態", "最低階", "配方數"], rows)
    return out


# ---------------------------------------------------------------------------
# 2. 關鍵字 × 元素 × 屬性
# ---------------------------------------------------------------------------

MAIN_CELLS = {"武器技": (A.STR, A.DEX), "法術技": (A.INT, A.WIS, A.WIL)}


def cell_counts(
    hand: list[Rec], reach: list[Draw], key: str
) -> tuple[Counter[tuple[str, str, str]], Counter[tuple[str, str, str]]]:
    """（維度, 屬性, 類別）→ 手寫招數／模板配方數；維度為關鍵字或元素。"""
    h: Counter[tuple[str, str, str]] = Counter()
    t: Counter[tuple[str, str, str]] = Counter()
    for r in hand:
        if r.cls not in MAIN_CELLS:
            continue
        for dim in r.keywords if key == "keyword" else r.elements:
            h[(dim, r.attr, r.cls)] += 1
    seen: set[tuple[str, str, str, str]] = set()
    for d in reach:
        if d.rec.cls not in MAIN_CELLS:
            continue
        for dim in d.rec.keywords if key == "keyword" else d.rec.elements:
            token = (dim, d.rec.attr, d.rec.cls, d.recipe)
            if token not in seen:
                seen.add(token)
                t[(dim, d.rec.attr, d.rec.cls)] += 1
    return h, t


def cross_table(
    dims: Sequence[str], hand: list[Rec], reach: list[Draw], key: str, cls: str
) -> tuple[list[str], list[str]]:
    h, t = cell_counts(hand, reach, key)
    cols = MAIN_CELLS[cls]
    rows: list[list[object]] = []
    gaps: list[str] = []
    for dim in dims:
        cells: list[object] = []
        for a in cols:
            hh, tt = h[(dim, a.value, cls)], t[(dim, a.value, cls)]
            total = hh + tt
            mark = "**0**" if total == 0 else (f"{total}*" if total < FEW else str(total))
            cells.append(f"{mark} ({hh}+{tt})")
            if total < FEW:
                gaps.append(f"{dim} × {a.display_name} × {cls}：{total} 招（手寫 {hh}＋模板 {tt}）")
        rows.append([dim, *cells])
    header = [("關鍵字" if key == "keyword" else "元素"), *[a.display_name for a in cols]]
    return table(header, rows), gaps


def section2(
    lib: ContentLibrary, hand: list[Rec], reach: list[Draw]
) -> tuple[list[str], list[str], list[str]]:
    keywords = [*lib.keywords.ids(), GENERIC]
    elements = sorted(
        {e for r in hand for e in r.elements} | {e for d in reach for e in d.rec.elements}
    )
    out = [
        "## 2. 關鍵字／元素 × 縮放屬性（主動武器技與法術技）",
        "",
        "格子內：合計（手寫＋模板配方數）；`*` ＝ 少於 3 招，`**0**` ＝ 空格。模板配方數＝不重複的配方"  # noqa: E501
        "（在任一武器大類與最高屬性下組得出該屬性）。武器技的屬性只會是力量（近戰）或敏捷（遠程）；"
        "法術技看主題（智力＝元素、感知＝輔助、意志＝召喚暗影）。",
        "",
    ]
    keyword_gaps: list[str] = []
    element_gaps: list[str] = []
    for key, dims in (("keyword", keywords), ("element", elements)):
        label = "關鍵字" if key == "keyword" else "元素"
        for cls in ("武器技", "法術技"):
            out += [f"### 2 {label} × 屬性：{cls}", ""]
            tbl, gaps = cross_table(dims, hand, reach, key, cls)
            out += tbl
            (keyword_gaps if key == "keyword" else element_gaps).extend(
                f"[{label}] {g}" for g in gaps
            )
    out += ["### 2g. 非武器／法術的種類（被動、反應、姿態、召喚）× 關鍵字（手寫招數）", ""]
    cnt: Counter[tuple[str, str]] = Counter()
    for r in hand:
        for k in r.keywords:
            cnt[(k, r.cls)] += 1
    out += table(
        ["關鍵字", *CLASSES],
        [[k, *[cnt[(k, c)] for c in CLASSES]] for k in keywords],
    )
    return out, keyword_gaps, element_gaps


# BAL-19 的補內容目標（06 6.27.4，#110）：達標以關鍵字表為準（BAL-19g，玩法 PM 定；元素欄只算
# 傷害元素，施加燃燒、冰凍、中毒這類狀態不會算進火、冰、毒）。
TARGETS: tuple[tuple[str, str, tuple[A, ...]], ...] = (
    *(
        (k, "法術技", (a,))
        for a in (A.WIS, A.WIL)
        for k in ("ignite", "charged", "frozen", "poisoned", "prone", "collision")
    ),
    *((k, "武器技", (A.DEX,)) for k in ("prone", "high_ground", "charged", "poisoned")),
)
# 元素武器技的目標以近戰＋遠程合計算（風、聖各 3 招，#110「近戰、遠程都有」），列為已知、不算殘留。
ELEMENT_TARGETS: tuple[str, ...] = ("wind", "holy")
KNOWN_ZERO = (
    "summon × 感知 × 法術技：權杖召喚 0 招（召喚維持意志，6.10；玩法 PM 接受 0，靠創角提示）",
)


def target_rows(hand: list[Rec], reach: list[Draw]) -> tuple[list[list[object]], list[str]]:
    """BAL-19 目標格子的達標表（關鍵字表）與殘留（少於 3 招）的清單。"""
    h, t = cell_counts(hand, reach, "keyword")
    rows: list[list[object]] = []
    residual: list[str] = []
    for keyword, cls, attrs in TARGETS:
        for a in attrs:
            hh, tt = h[(keyword, a.value, cls)], t[(keyword, a.value, cls)]
            ok = hh + tt >= FEW
            rows.append([keyword, a.display_name, cls, f"{hh}+{tt}", "達標" if ok else "**未達**"])
            if not ok:
                residual.append(
                    f"{keyword} × {a.display_name} × {cls}：{hh + tt} 招（手寫 {hh}＋模板 {tt}）"
                )
    return rows, residual


def element_weapon_rows(hand: list[Rec], reach: list[Draw]) -> list[list[object]]:
    """風、聖元素武器技（近戰力量＋遠程敏捷合計）。"""
    h, t = cell_counts(hand, reach, "element")
    rows: list[list[object]] = []
    for e in ELEMENT_TARGETS:
        parts = [(h[(e, a.value, "武器技")], t[(e, a.value, "武器技")]) for a in (A.STR, A.DEX)]
        total = sum(x + y for x, y in parts)
        detail = "、".join(
            f"{a.display_name} {x}+{y}" for a, (x, y) in zip((A.STR, A.DEX), parts, strict=True)
        )
        rows.append([e, detail, total, "達標（已知）" if total >= FEW else "**未達**"])
    return rows


def section_targets(hand: list[Rec], reach: list[Draw]) -> tuple[list[str], list[str]]:
    rows, residual = target_rows(hand, reach)
    out = [
        "## 2t. BAL-19 補內容目標（關鍵字表；06 6.27.4，#110）",
        "",
        "格子：手寫＋模板配方數，達標線 3。達標以**關鍵字表**為準（元素欄只算傷害元素）。",
        "",
    ]
    out += table(["關鍵字", "屬性", "類別", "手寫+模板", "結果"], rows)
    out += ["風、聖元素武器技（近戰＋遠程合計 3 招；列為已知）：", ""]
    out += table(["元素", "力量／敏捷", "合計", "結果"], element_weapon_rows(hand, reach))
    out += ["已知：", "", *[f"- {k}" for k in KNOWN_ZERO], ""]
    out += ["殘留（目標格子少於 3 招）：", ""]
    out += [f"- {r}" for r in residual] if residual else ["- 無"]
    out.append("")
    return out, residual


# ---------------------------------------------------------------------------
# 3. 稀有度、觸發、形狀
# ---------------------------------------------------------------------------


def dist_rows(
    counters: Sequence[Counter[str]], order: Sequence[str] | None = None
) -> list[list[object]]:
    keys = list(order) if order else sorted({k for c in counters for k in c})
    rows: list[list[object]] = []
    totals = [sum(c.values()) or 1 for c in counters]
    for k in keys:
        rows.append(
            [k, *[f"{c[k]} ({100 * c[k] / t:.0f}%)" for c, t in zip(counters, totals, strict=True)]]
        )
    return rows


def section3(hand: list[Rec], comp: list[Rec], reach: list[Draw]) -> list[str]:
    uniq = list(uniq_outcomes(reach).values())
    sets = (hand, comp, uniq)
    head = ["", f"手寫 {len(hand)}", f"組合器抽樣 {len(comp)}", f"白板可達 {len(uniq)}"]
    out = ["## 3. 稀有度、觸發時機、形狀", "", "### 3a. 稀有度", ""]
    out += table(head, dist_rows([Counter(r.rarity for r in s) for s in sets], RARITIES))
    out += ["### 3b. 觸發時機", ""]
    out += table(head, dist_rows([Counter(r.trigger for r in s) for s in sets]))
    out += ["### 3c. 形狀（歸類）", ""]
    out += table(
        head, dist_rows([Counter(SHAPE_GROUP.get(r.shape, r.shape) for r in s) for s in sets])
    )
    out += ["### 3d. 形狀（原始）", ""]
    out += table(head, dist_rows([Counter(r.shape for r in s) for s in sets]))
    return out


# ---------------------------------------------------------------------------
# 4. 武器大類 × 關鍵字
# ---------------------------------------------------------------------------


def hand_usable(
    lib: ContentLibrary, p: Profile, hand_skills: list[SkillDef]
) -> dict[str, list[SkillDef]]:
    weapon = lib.weapons[p.weapon]
    held = {weapon.id: weapon.name_zh}
    out: dict[str, list[SkillDef]] = defaultdict(list)
    for s in hand_skills:
        if s.tier != 1 or s.rarity == "legendary" or s.form_id is not None:
            continue
        if (
            minimum_tier(s, lib) > MAX_RECIPE_TIER
            or weapon_problem(s, weapon.weapon_class, held) is not None
        ):
            continue
        for k in derive_keywords(s, lib.keywords, exclusive_only=True).all() or (GENERIC,):
            out[k].append(s)
    return out


def section4(
    lib: ContentLibrary, pdraws: dict[str, list[Draw]]
) -> tuple[list[str], dict[str, dict[str, float]]]:
    skills = [lib.skills[i] for i in sorted(lib.skills)]
    keywords = [*lib.keywords.ids(), GENERIC]
    out = [
        "## 4. 武器大類 × 關鍵字：能拿到的技能數",
        "",
        "格子：`手寫 同路線／可用` ＋ `模板 同路線期望／配方數`。手寫＝1 階、非傳說、角色 2 階以內可用、武器相容；"  # noqa: E501
        "同路線＝`follows_attr`（BAL-17 之後的判定）。模板＝最低階 ≤ 2 的白板配方，同路線期望＝每個配方"  # noqa: E501
        "抽樣中同路線的比例加總（含該武器抽不到的配方不計）。",
        "",
    ]
    summary: dict[str, dict[str, float]] = {}
    for group in ("近戰", "遠程", "法器", "雙屬性"):
        profs = [p for p in PROFILES if p.group == group]
        out += [f"### 4 {group}（{'、'.join(p.label for p in profs)}）", ""]
        rows: list[list[object]] = []
        for k in keywords:
            row: list[object] = [k]
            for p in profs:
                weapon = lib.weapons[p.weapon]
                attrs = weapon_scaling_attrs(weapon)
                pool = hand_usable(lib, p, skills)[k]
                same = sum(1 for s in pool if follows_attr(s, p.top, attrs))
                per: dict[str, list[bool]] = defaultdict(list)
                for d in pdraws[p.label]:
                    if d.keyword == k and d.min_tier <= MAX_RECIPE_TIER:
                        per[d.recipe].append(d.on_route)
                expect = sum(sum(v) / len(v) for v in per.values())
                total_same = same + expect
                summary.setdefault(p.label, {})[k] = total_same
                mark = (
                    "**0**"
                    if total_same == 0
                    else (f"{total_same:.1f}*" if total_same < FEW else f"{total_same:.1f}")
                )
                row.append(f"{mark} = {same}/{len(pool)} + {expect:.1f}/{len(per)}")
            rows.append(row)
        out += table(["關鍵字", *[p.label for p in profs]], rows)
    return out, summary


# ---------------------------------------------------------------------------
# 5. 偏離率
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Start:
    label: str
    weapon: str
    keywords: tuple[str, str]
    allocation: dict[A, int] | None


STARTS: tuple[Start, ...] = (
    Start("劍 力量 prone+collision", "one_handed_sword", ("prone", "collision"), {A.STR: 4}),
    Start("匕首 敏捷 concealed+prone", "dagger", ("concealed", "prone"), {A.DEX: 4}),
    Start("戰錘 體質 collision+prone", "hammer", ("collision", "prone"), {A.CON: 4}),
    Start("弓 敏捷 high_ground+marked", "bow", ("high_ground", "marked"), {A.DEX: 4}),
    Start("弩 敏捷 ignite+collision", "crossbow", ("ignite", "collision"), {A.DEX: 4}),
    Start("火杖 智力 ignite+marked", "fire_staff", ("ignite", "marked"), {A.INT: 4}),
    Start("雷杖 智力 wet+charged", "lightning_staff", ("wet", "charged"), {A.INT: 4}),
    Start("權杖 感知 wet+marked", "scepter", ("wet", "marked"), {A.WIS: 4}),
    Start("圖騰杖 意志 summon+ignite", "totem_staff", ("summon", "ignite"), {A.WIL: 4}),
    Start("魔導劍 力量14 charged+concealed", "arcane_blade", ("charged", "concealed"), {A.STR: 4}),
    Start("魔導劍 預設配點 ignite+frozen", "arcane_blade", ("ignite", "frozen"), None),
    Start("鐮刀 預設配點 concealed+poisoned", "scythe", ("concealed", "poisoned"), None),
)
# 兩種量法：lv1＝BAL-17 的做法（等級 1，兩次都 1 階）；real＝實際第 1、2 次升級（等級 2、3＝1、2 階）  # noqa: E501
MODES = (("lv1", ((1, 0), (1, 1))), ("real", ((2, 0), (3, 1))))


@dataclass(frozen=True, slots=True)
class OfferRow:
    start: int
    mode: str
    seed: int
    index: int
    off: tuple[int, ...]  # 偏離的候選索引
    kinds: tuple[str, ...]
    sources: tuple[str, ...]
    desc: tuple[str, ...]  # 每張候選：種類/屬性/關鍵字


def offers_task(_ctx: None, task: tuple[int, int]) -> list[OfferRow] | None:
    start_i, seed = task
    lib = default_library()
    s = STARTS[start_i]
    try:
        run = new_keyword_run(lib, s.weapon, s.keywords, seed, s.allocation)
    except Exception:  # 這個種子開不出這種開局（ChoiceError）：略過，計入失敗數
        return None
    rows: list[OfferRow] = []
    for mode, steps in MODES:
        for level, made in steps:
            r = run.model_copy(update={"level": level, "offers_made": made})
            offer = make_offer(lib, r, "level_up")
            rows.append(
                OfferRow(
                    start_i,
                    mode,
                    seed,
                    made,
                    offer.off_route,
                    tuple(t.kind for t in offer.tags),
                    tuple(t.source for t in offer.tags),
                    tuple(
                        f"{kind_class(c)}/{c.scaling_attr.value}/{'+'.join(t.keywords) or GENERIC}"
                        for c, t in zip(offer.candidates, offer.tags, strict=True)
                    ),
                )
            )
    return rows


def section5(seeds: int, jobs: int) -> list[str]:
    tasks = [(i, seed) for i in range(len(STARTS)) for seed in range(seeds)]
    results = run_tasks(offers_task, None, tasks, jobs=jobs)
    rows: list[OfferRow] = []
    failed: Counter[int] = Counter()
    for task, res in zip(tasks, results, strict=True):
        if res is None:
            failed[task[0]] += 1
        else:
            rows += res
    out = [
        "## 5. 實際候選偏離率（白板三選一，第 1、2 次升級）",
        "",
        f"12 種開局 × 種子 0～{seeds - 1}（白板模式；完整技能模式一組要數秒到數十秒，不在本量測內）。"  # noqa: E501
        "`lv1`＝BAL-17 的做法（等級 1，兩次都用 1 階）；`real`＝實際升級（等級 2、3＝第 1、2 次升級，"  # noqa: E501
        "階級 1、2）。偏離張數＝`SkillOffer.off_route` 的長度（縮放屬性不在主角最高屬性 ／ 雙屬性武器"  # noqa: E501
        "的兩個屬性內，且不是靠第二屬性跟上的雙屬性技能；BAL-19g `route_rank`）。",
        "",
    ]
    for mode, _ in MODES:
        sub = [r for r in rows if r.mode == mode]
        out += [f"### 5 {mode}", ""]
        body: list[list[object]] = []
        for i, s in enumerate(STARTS):
            mine = [r.off for r in sub if r.start == i]
            if not mine:
                body.append([s.label, "開不出", "", "", "", "", ""])
                continue
            dist = Counter(len(o) for o in mine)
            mean = sum(len(o) for o in mine) / len(mine)
            body.append([
                s.label,
                len(mine),
                f"{mean:.2f}",
                max(dist),
                *[f"{100 * dist[n] / len(mine):.0f}%" for n in (0, 1, 2, 3)],
            ])  # fmt: skip
        out += table(["開局", "組數", "平均偏離", "最多", "0 張", "1 張", "2 張", "3 張"], body)
        allc = Counter(len(r.off) for r in sub)
        n = sum(allc.values())
        out.append(
            f"全部 {n} 組：平均 {sum(k * v for k, v in allc.items()) / n:.2f}；"
            + "、".join(f"{k} 張 {100 * v / n:.0f}%" for k, v in sorted(allc.items()))
        )
        out.append("")
        slot_off: Counter[str] = Counter()
        slot_all: Counter[str] = Counter()
        for r in sub:
            for j, kind in enumerate(r.kinds):
                slot_all[kind] += 1
                slot_off[kind] += j in r.off
        out += table(
            ["候選位置", "出現", "偏離", "偏離率"],
            [
                [k, slot_all[k], slot_off[k], f"{100 * slot_off[k] / slot_all[k]:.0f}%"]
                for k in slot_all
            ],
        )
        why: Counter[str] = Counter()
        for r in sub:
            for j in r.off:
                why[f"{r.sources[j]} {r.desc[j]}"] += 1
        out += ["偏離候選最常見的來源／種類／屬性／關鍵字：", ""]
        out += table(["來源 種類/屬性/關鍵字", "次數"], [[k, v] for k, v in why.most_common(10)])
    if failed:
        out.append(
            "開局開不出的種子：" + "、".join(f"{STARTS[i].label} {n}" for i, n in failed.items())
        )
        out.append("")
    return out


# ---------------------------------------------------------------------------
# 主程式
# ---------------------------------------------------------------------------


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def keyword_element_attr_csv(path: Path, hand: list[Rec], reach: list[Draw]) -> None:
    """完整的 關鍵字 × 元素 × 屬性 × 類別 表（手寫招數與模板配方數）。"""
    h: Counter[tuple[str, str, str, str]] = Counter()
    t: Counter[tuple[str, str, str, str]] = Counter()
    for r in hand:
        for k in r.keywords:
            for e in r.elements or ("none",):
                h[(k, e, r.attr, r.cls)] += 1
    seen: set[tuple[str, str, str, str, str]] = set()
    for d in reach:
        for k in d.rec.keywords:
            for e in d.rec.elements or ("none",):
                token = (k, e, d.rec.attr, d.rec.cls, d.recipe)
                if token not in seen:
                    seen.add(token)
                    t[(k, e, d.rec.attr, d.rec.cls)] += 1
    keys = sorted(set(h) | set(t))
    write_csv(path, ["keyword", "element", "attr", "class", "handwritten", "template_recipes"],
              [[*k, h[k], t[k]] for k in keys])  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=50, help="第 5 節每種開局的種子數")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--composer-samples", type=int, default=600)
    ap.add_argument("--reach-seeds", type=int, default=8, help="可達性：每個配方×武器×屬性的抽樣數")
    ap.add_argument("--profile-seeds", type=int, default=24, help="第 4 節：每個配方×開局的抽樣數")
    ap.add_argument("--sections", default="1,2,3,4,5")
    ap.add_argument("--out-dir", type=Path, default=None, help="另存 CSV 的資料夾")
    args = ap.parse_args()
    if args.jobs < 1 or args.jobs > MAX_JOBS:
        raise SystemExit("--jobs 必須在 1～6")
    want = set(args.sections.split(","))
    lib = default_library()
    hand = handwritten(lib)
    out: list[str] = ["# 技能模板不均衡分析（BAL-18）", ""]
    need_reach = want & {"1", "2", "3"}
    comp, comp_failed = composer_sample(lib, args.composer_samples) if need_reach else ([], 0)
    reach = reach_draws(lib, args.reach_seeds) if need_reach else []
    if "1" in want:
        out += section1(lib, hand, comp, reach)
        out.append(f"（組合器抽樣 {args.composer_samples} 個種子，失敗 {comp_failed}。）")
        out.append("")
    if "2" in want:
        lines, gaps, element_gaps = section2(lib, hand, reach)
        out += lines
        out += [
            "### 2h. 少於 3 招的組合（關鍵字表；主要格：武器技＝力量／敏捷，法術技＝智力／感知／"
            "意志）",
            "",
        ]
        out += [f"- {g}" for g in gaps] + [""]
        out += [
            "### 2h'. 元素欄少於 3 招（只算傷害元素，僅供參考，不算達標）",
            "",
        ]
        out += [f"- {g}" for g in element_gaps] + [""]
        out += section_targets(hand, reach)[0]
    if "3" in want:
        out += section3(hand, comp, reach)
    if "4" in want:
        lines, _ = section4(lib, profile_draws(lib, args.profile_seeds))
        out += lines
    if "5" in want:
        out += section5(args.seeds, args.jobs)
    if args.out_dir is not None and need_reach:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        keyword_element_attr_csv(args.out_dir / "keyword_element_attr.csv", hand, reach)
    print("\n".join(out))


if __name__ == "__main__":
    main()
