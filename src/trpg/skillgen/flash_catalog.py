"""閃現變化的「目錄」（Phase 3W-7）：這一次可以提議哪些模板、每個模板可帶哪些參數。

LLM 提議只能在目錄裡挑（守則 3）：目錄由資料來源
（:class:`~trpg.skillgen.flash_offer.UsageSource`，與一般
出題同一套候選）展開，所以提議的變化一定是「資料本來就可能出的變化」，只是由模型挑哪幾個。目錄同時
是 prompt 的選單、JSON schema 的列舉與提議的驗證表（:meth:`FlashCatalog.resolve`）。純函式、確定性。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen.flash_category import allowed_categories
from trpg.skillgen.flash_offer import FlashOptionSource, FlashRequest, UsageSource
from trpg.shared.rng import Rng
from trpg.skillgen.flash_state import Variation

__all__ = ["CatalogEntry", "FlashCatalog", "build_catalog"]


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """目錄裡的一個模板：類別、給 LLM 看的說明，以及可帶的參數選單（空 ＝ 不需要這個參數）。"""

    template: str
    source: str
    category: str
    hint: str
    keywords: tuple[str, ...] = ()
    elements: tuple[str, ...] = ()
    shapes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FlashCatalog:
    """一次出題可提議的全部變化（依類別、模板分組）。"""

    categories: tuple[str, ...]
    entries: tuple[CatalogEntry, ...]
    pool: dict[str, Variation] = field(default_factory=dict)
    """所有可提議的變化（以 :meth:`Variation.key` 為鍵）。"""

    def shuffled(self, seed: int, label: str) -> FlashCatalog:
        """呈現順序依種子打亂的目錄（BAL-10c；同 4-L6 的輪替選單，``menu_order``）：類別、模板與每個
        模板的參數選單各自打亂，避免模型偏好排在前面的選項（第一個提議 83% 取自選單前三分之一）。
        只影響呈現（prompt 的 ``<catalog>`` 與 schema 列舉）；``pool``、:meth:`resolve` 與驗證不變。
        先排序再打亂，所以結果只取決於種子與目錄內容；同種子同順序。"""
        rng = Rng(seed).fork(f"menu/flash/{label}")
        entries = [
            replace(
                e,
                keywords=tuple(rng.shuffled(sorted(e.keywords))),
                elements=tuple(rng.shuffled(sorted(e.elements))),
                shapes=tuple(rng.shuffled(sorted(e.shapes))),
            )
            for e in sorted(self.entries, key=lambda e: e.template)
        ]
        return FlashCatalog(
            tuple(rng.shuffled(sorted(self.categories))),
            tuple(rng.shuffled(entries)),
            self.pool,
        )

    def entry(self, template: str) -> CatalogEntry | None:
        return next((e for e in self.entries if e.template == template), None)

    def templates(self) -> tuple[str, ...]:
        return tuple(e.template for e in self.entries)

    def resolve(
        self,
        template: str,
        keyword: str | None = None,
        element: str | None = None,
        shape: str | None = None,
    ) -> Variation | None:
        """依模板與參數找目錄裡對應的變化；沒有（參數不在選單內、該給沒給）回傳 ``None``。"""
        for variation in self.pool.values():
            if (
                variation.template == template
                and variation.keyword == keyword
                and variation.element == element
                and (variation.shape.type if variation.shape is not None else None) == shape
            ):
                return variation
        return None


def _hint(library: ContentLibrary, variation: Variation) -> str:
    table = library.flash
    text = ""
    if variation.source == "minor":
        template = table.minor_template(variation.template)
        text = "" if template is None else template.llm_hint or template.summary_zh
    else:
        major = table.major_template(variation.template)
        extra = table.extra_template(variation.template)
        if major is not None:
            evolution = next(
                (t for t in library.evolution.templates if t.id == major.evolution), None
            )
            text = major.llm_hint or ("" if evolution is None else str(evolution.summary_zh))
        elif extra is not None:
            text = extra.llm_hint or extra.summary_zh
    return text.replace("{keyword}", "指定的關鍵字")


def _unique(values: Sequence[str | None]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(v for v in values if v is not None))


def build_catalog(
    library: ContentLibrary,
    request: FlashRequest,
    before: SkillDef,
    *,
    major: bool,
    source: FlashOptionSource | None = None,
    applicable: Callable[[Variation], bool] | None = None,
) -> FlashCatalog:
    """這一次（``major``：是不是第 3 次大變化）可以提議的變化目錄。轉型不在目錄內（由資料保底）。
    指定類別時只含該類。

    ``applicable``（Phase 4-L10a F1／F2）：只收這招套得上的變化（LLM 提議用引擎真的套一次的
    檢查，與 ``flash.not_applicable`` 同一個判斷）；模板的參數選單只留套得上的值，沒有任何套得上
    變化的模板與類別不列入。"""
    source = source or UsageSource()
    table = library.flash
    categories = allowed_categories(table, before, major=major)
    if request.category is not None:
        categories = tuple(c for c in categories if c == request.category)
    pool: dict[str, Variation] = {}
    order: dict[str, list[Variation]] = {}
    for category in categories:
        for variation in source.ranked(library, request, category, before):
            if variation.key() in pool or (applicable is not None and not applicable(variation)):
                continue
            pool[variation.key()] = variation
            order.setdefault(variation.template, []).append(variation)
    entries = tuple(
        CatalogEntry(
            template=template,
            source=variations[0].source,
            category=variations[0].category,
            hint=_hint(library, variations[0]),
            keywords=_unique([v.keyword for v in variations]),
            elements=_unique([v.element for v in variations]),
            shapes=_unique([v.shape.type if v.shape is not None else None for v in variations]),
        )
        for template, variations in order.items()
    )
    if applicable is not None:
        categories = tuple(c for c in categories if any(e.category == c for e in entries))
    return FlashCatalog(categories, entries, pool)
