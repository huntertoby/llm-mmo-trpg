"""大世界的生成內容（Phase 6L-2；06 6.34.7「預先生成」、07 7.6）。

三個入口本來就會請 LLM 提議：**閃現與重閃**的變化、主線**劇情技能**的元素與文字、**機遇**的完整技能
三選一；WP-1 加上第四個：**許願池**（願望對到的關鍵字＋完整技能三選一，:class:`WishGenRequest`）。
世界引擎（純函式）不呼叫 LLM，也不知道背景執行緒：

- 引擎需要生成內容時組一個 **請求**（:class:`FlashGenRequest`、:class:`StoryGenRequest`、
  :class:`OfferGenRequest`），交給目前裝上的 **供應者**（:func:`using_generated`；API 層裝上背景
  預先生成的暫存區，會等、會降級）。供應者回傳一筆 **紀錄**（:data:`Generated`），或 ``None``＝
  沒有（模型關閉、沒趕上、驗證失敗）。
- 不論有沒有拿到，引擎都把 **最後給出的版本** 記成一筆紀錄（來源 ``llm``／``partial``／
  ``template``／``composer``／``content``），收進這次動作的清單；API 層把清單寫進日誌那一筆
  （``WorldLogEntry.generated``）。
- **重播只讀日誌**：:func:`~trpg.world.replay.replay` 用日誌那一筆的紀錄當供應者
  （:func:`recorded`），完全不呼叫 LLM，結果和當時逐字相同。舊日誌沒有紀錄＝全部用組合器、
  模板與內容版（與 6L-2 以前相同）。
- 引擎照樣驗證紀錄（守則 3）：閃現的變化由 :func:`~trpg.skillgen.flash_offer.make_offer` 一一套用，
  套不上的用模板補；劇情技能的元素要在選單內、換完預算不變（:func:`~trpg.skillgen.story_theme.retheme`），
  文字要通過長度與字元檢查；機遇的三選一要是同種類、同階級的完整技能。

紀錄的鍵（``key``）由請求的完整輸入算出（:func:`input_key`），預測錯了只是沒命中，不會拿到別人的。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.skills import SkillDef
from trpg.roguelite.state import FlashLlmRecord, RunState, SkillOffer
from trpg.skillgen.flash_offer import FlashRequest

__all__ = [
    "FlashGen",
    "FlashGenRequest",
    "GenRequest",
    "Generated",
    "OfferGen",
    "OfferGenRequest",
    "Record",
    "StoryGen",
    "StoryGenRequest",
    "Supplier",
    "WishGen",
    "WishGenRequest",
    "flash_key",
    "flash_pregen_key",
    "input_key",
    "recorded",
    "supply",
    "using_generated",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FlashGen(_Model):
    """閃現（或重閃）出題時用的變化提議（``record.source``：``llm``／``partial``／``template``）。"""

    kind: Literal["flash"] = "flash"
    key: str
    record: FlashLlmRecord


class StoryGen(_Model):
    """劇情技能的元素與文字（``source``：``llm``＝LLM 換過；``content``＝內容版原樣）。"""

    kind: Literal["story_skill"] = "story_skill"
    key: str
    skill: str
    source: Literal["llm", "content"] = "content"
    element: str | None = None
    name_zh: str | None = None
    concept: str | None = None
    cast_flavor: str | None = None
    prompt_version: str = ""


class OfferGen(_Model):
    """機遇給的完整技能三選一（``source``：``llm``＝至少一張是 LLM 提議的；``composer``＝組合器與
    技能池，``offer`` 為 ``None``，引擎照常同步算）。"""

    kind: Literal["complete_offer"] = "complete_offer"
    key: str
    source: Literal["llm", "composer"] = "composer"
    offer: SkillOffer | None = None


class WishGen(_Model):
    """許願池（WP-1）：LLM 從選單對到的關鍵字與完整技能三選一。``source``：``llm``＝關鍵字＋至少
    一張 LLM 提議的技能；``partial``＝只有關鍵字（``offer`` 為 ``None``，引擎用同樣的關鍵字照常算
    組合器版）；``none``＝沒對上（模型關閉、逾時、驗證不過），引擎拒絕這次許願。願望文字不在這裡
    （在動作裡），紀錄只有 LLM 給出的結構。"""

    kind: Literal["wish"] = "wish"
    key: str
    source: Literal["llm", "partial", "none"] = "none"
    keywords: tuple[str, ...] = ()
    offer: SkillOffer | None = None
    attempts: int = Field(default=0, ge=0)
    """對關鍵字那一步呼叫了幾次 LLM（提議技能的次數在 ``offer`` 的標示裡）。"""
    codes: tuple[str, ...] = ()
    """對關鍵字那一步的錯誤碼（每次嘗試依序）。"""
    prompt_version: str = ""


type Generated = Annotated[FlashGen | StoryGen | OfferGen | WishGen, Field(discriminator="kind")]


@dataclass(frozen=True, slots=True)
class FlashGenRequest:
    """閃現出題的提議請求（``request`` 已帶原技能取得地點的區域）。"""

    character_id: str
    key: str
    request: FlashRequest
    kind: Literal["flash"] = "flash"


@dataclass(frozen=True, slots=True)
class StoryGenRequest:
    """劇情技能的請求：``skill`` 是照角色階級、完整技能強度做好的內容版；``elements`` 是可以換的
    元素（:func:`~trpg.skillgen.story_theme.story_elements`）；``keywords`` 是玩家持有的關鍵字分布；
    ``region`` 是取得地點的區域（#126 名稱與描述的風格）。"""

    character_id: str
    key: str
    skill: SkillDef
    elements: tuple[str, ...]
    keywords: tuple[tuple[str, int], ...]
    region: str | None
    weapon_zh: str | None = None
    kind: Literal["story_skill"] = "story_skill"


@dataclass(frozen=True, slots=True)
class OfferGenRequest:
    """機遇完整技能三選一的請求（``make_offer`` 的參數，同 ``solutions._opportunity``）。"""

    character_id: str
    key: str
    run: RunState
    region_keywords: tuple[str, ...]
    tier_bonus: int
    pinned_keyword: str | None
    region: str | None
    kind: Literal["complete_offer"] = "complete_offer"


@dataclass(frozen=True, slots=True)
class WishGenRequest:
    """許願池的請求（WP-1）：``text`` 是玩家的願望（生成函式只放進 prompt 的 ``<player_input>``）；
    ``menu`` 是可以對到的關鍵字；``run`` 是出題用的角色（``offers_made`` 已對上）；
    ``max_keywords``、
    ``llm_cards`` 照世界規則。"""

    character_id: str
    key: str
    text: str
    menu: tuple[str, ...]
    run: RunState
    max_keywords: int
    llm_cards: int
    kind: Literal["wish"] = "wish"


type GenRequest = FlashGenRequest | StoryGenRequest | OfferGenRequest | WishGenRequest
type Record = FlashGen | StoryGen | OfferGen | WishGen
type Supplier = Callable[[GenRequest], Record | None]
"""請求 → 紀錄（或 ``None``）。API 層的實作可以等背景工作（最多 10 秒）；引擎只當它是資料來源。"""


@dataclass(slots=True)
class _Context:
    supplier: Supplier | None
    used: list[Record]


_CONTEXT: ContextVar[_Context | None] = ContextVar("trpg_world_generated", default=None)


@contextmanager
def using_generated(
    supplier: Supplier | None,
) -> Iterator[list[Record]]:
    """在 ``with`` 區塊內裝上供應者；``as`` 拿到的清單收集這段期間引擎最後給出的紀錄（依發生順序）。
    ``supplier`` 為 ``None``＝一律降級（照樣收集降級的紀錄）。"""
    context = _Context(supplier, [])
    token = _CONTEXT.set(context)
    try:
        yield context.used
    finally:
        _CONTEXT.reset(token)


def supply[R: (FlashGen, StoryGen, OfferGen, WishGen)](
    request: GenRequest, expect: type[R], fallback: R, accept: Callable[[R], R | None]
) -> R:
    """引擎拿生成內容：問目前的供應者，種類或鍵不對、``accept``（引擎的驗證）不收時用 ``fallback``；
    最後給出的那一筆記進收集清單。沒裝供應者（例如模擬、測試直接呼叫引擎）時直接用 ``fallback``、
    不收集。"""
    context = _CONTEXT.get()
    if context is None:
        return fallback
    found = None if context.supplier is None else context.supplier(request)
    chosen: R = fallback
    if isinstance(found, expect) and found.key == request.key:
        checked = accept(found)
        if checked is not None:
            chosen = checked
    context.used.append(chosen)
    return chosen


def recorded(records: Iterable[Record]) -> Supplier:
    """重播用的供應者：依（種類, 鍵）取日誌裡的紀錄，不呼叫 LLM。"""
    by_key: dict[tuple[str, str], Record] = {(r.kind, r.key): r for r in records}

    def lookup(request: GenRequest) -> Record | None:
        return by_key.get((request.kind, request.key))

    return lookup


def input_key(prefix: str, data: Any) -> str:
    """``{prefix}:{輸入的雜湊}``：排序鍵 JSON 的 blake2b（不用內建 ``hash()``）。"""
    text = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=12).hexdigest()
    return f"{prefix}:{digest}"


def _flash_data(character_id: str, request: FlashRequest) -> dict[str, Any]:
    """閃現請求的輸入（不含用法統計；:func:`flash_key` 另外加上）。"""
    return {
        "char": character_id,
        "base": request.base.model_dump(mode="json"),
        "state": request.state.model_dump(mode="json"),
        "seed": request.seed,
        "slot": request.slot,
        "category": request.category,
        "held": dict(sorted(request.held_keywords.items())),
        "tier": request.tier,
        "current": None if request.current is None else request.current.model_dump(mode="json"),
        "region": request.region,
        "weapon": request.weapon_zh,
    }


def _flash_tag(request: FlashRequest) -> str:
    return f"{request.state.base_id}/{request.nth}/{request.reflashes}/{request.category}"


def flash_key(character_id: str, request: FlashRequest) -> str:
    """閃現請求的鍵（日誌紀錄的鍵，重播依它查）：角色＋種子標籤欄位＋出題的完整輸入（含用法統計）。"""
    data = {**_flash_data(character_id, request), "usage": request.usage.model_dump(mode="json")}
    return input_key(f"flash/{_flash_tag(request)}", data)


def flash_pregen_key(character_id: str, request: FlashRequest) -> str:
    """預先生成暫存區的閃現鍵（6L-2c，玩法 PM 決定）：同 :func:`flash_key` 但**不含用法統計**——
    每打完一場用法統計都會變，放進鍵就會一直重做。統計只在開始生成時讀一次（那次請求的輸入）；
    玩家按下時用這把鍵找，給出去時鍵改成按下那一刻的 :func:`flash_key`（日誌照舊依它重播）。"""
    return input_key(f"flash-pregen/{_flash_tag(request)}", _flash_data(character_id, request))
