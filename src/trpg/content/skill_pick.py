"""技能生成「挑選模式」的打分權重與候選池大小（Phase PK-1；資料檔 ``content/skill_pick.yaml``）。

提案 ``docs/phases/技能生成-挑選模式提案.md`` 第 4 節、第 7.2 節：程式先用組合器多種子抽出合法候選、
依設計去重，再依「適不適合這位玩家」打分（**不比強弱**），取前 K 個交給 LLM 挑一個並命名。這張表只放
數字（全部是整數），由使用者在數值工坊調（第 6 節第 5 題 A）；看哪些項目由程式決定。

不嵌入規則包（不影響戰鬥結算與重播）；它在 ``library.files`` 裡，所以改了 ``ruleset_hash`` 與
``content_digest`` 會變（同 ``skill_icon_art.yaml``）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from trpg.content.schemas import ContentModel

__all__ = [
    "WISH_TAG_GROUPS",
    "PickPoolRules",
    "PickWeights",
    "SkillPickRules",
    "WishEffectTag",
    "WishShapeTag",
    "WishTagItem",
    "WishTagRules",
    "WishTags",
]


class PickPoolRules(ContentModel):
    """候選池：組合器抽幾個種子、湊到幾個不同設計就停、送幾個給 LLM。"""

    seeds: int = Field(ge=1, le=400)
    """組合器最多抽幾個種子（每個種子一招；同一個設計只留第一個）。"""
    designs: int = Field(ge=1, le=100)
    """湊到這麼多個不同設計就停止抽樣（省 CPU 時間；打分前的候選上限）。"""
    top_k: int = Field(ge=1, le=8)
    """送給 LLM 的候選數（提案第 6 節第 2 題 A：每格 4～6 個）。"""
    min_for_llm: int = Field(ge=1, le=8)
    """候選少於這個數就不呼叫 LLM，直接用第一名（提案 7.6）。"""
    handwritten_max: int = Field(ge=0, le=1)
    """PK-1b：送給 LLM 的候選裡最多幾個手寫技能（技能池）；0＝完全不放（只在候選池是空的時候照現行
    退回技能池）。玩家手上已有的技能不論這裡設多少都不會進候選。"""
    element_seeds: int = Field(ge=0, le=400)
    """PK-1b：玩家手上有元素技能、而候選池裡同元素的設計少於 ``element_designs`` 個時，另外用獨立的
    亂數串流再抽最多這麼多個種子，只收和玩家同元素的新設計；0＝不補抽。"""
    element_designs: int = Field(ge=0, le=40)
    """PK-1b：候選池裡和玩家同元素的設計至少要有幾個（不夠才補抽，補到這個數就停）。"""
    slot_seeds: int = Field(ge=0, le=200)
    """PK-2 三選一的每一格（加深／橋接／新方向）：照這一格的出題條件（關鍵字、種類、屬性路線）另外
    最多抽這麼多個種子當候選（獨立亂數串流；湊到 ``top_k`` 個不同設計就停）；0＝每格只有原本
    出題的那一張。白板三選一用這個。"""
    complete_slot_seeds: int = Field(ge=0, le=200)
    """PK-2 完整技能三選一的每一格另外抽幾個種子（組合器整招指定關鍵字，每個種子約 0.05～0.2 秒，
    所以比白板少）。"""
    nondamage_seeds: int = Field(ge=0, le=200)
    """PK-2 非傷害保底（#142）：保底格只留非傷害的候選，不到 ``top_k`` 個時（或三格都沒有非傷害的
    候選時，依新方向 → 橋接 → 加深）用另一條亂數串流最多補抽這麼多個種子，只收非傷害的；
    0＝不補抽。"""
    relax_until: int = Field(ge=1, le=8)
    """PK-3（06 6.7「候選怎麼篩」，使用者題 1「B 放寬」）：三選一每一格先只收「全部關鍵字＋路線符合
    這一格」的候選；不到這麼多個時，照 #110 的找法依序放寬補上——同路線但只帶這一格部分關鍵字（橋接
    之類的多關鍵字格）→ 不跟路線（偏離）的。放寬的候選另外扣分
    （``weights.keyword_relaxed_penalty``、``weights.route_off_penalty``），排在後面。"""
    flash_top_k: int = Field(ge=1, le=8)
    """PK-3 閃現挑選模式：每個選項格給本機模型幾個候選（格子的類別由程式決定，候選依用法統計排序；
    第一個就是原本出題的那一個）。越多 prompt 越長。"""
    wish_candidates: int = Field(ge=3, le=30)
    """PK-4 許願池「候選量」（07 7.6「許願池：願望驅動」第 2 點，初值：一般每格 4～6 個，許願 15～20
    個）：照願望標籤用組合器做這麼多個不同設計，打分後全部交給本機模型挑 3 張。越多越慢（每個種子約
    0.05～0.2 秒）。"""

    @model_validator(mode="after")
    def _check(self) -> PickPoolRules:
        if self.min_for_llm > self.top_k:
            raise ValueError("min_for_llm 不能大於 top_k")
        return self


class PickWeights(ContentModel):
    """打分權重（分數＝各項的加權和；全部是整數點數）。"""

    synergy_per_link: int = Field(ge=0)
    """協同：候選製造的關鍵字有一招手上的技能利用（或反過來），每一條連線（手上技能 × 關鍵字 ×
    方向）加這麼多（PK-1b 起 300 → 150、上限 3 → 5，讓條數拉開差距）。"""
    synergy_max_links: int = Field(ge=0)
    """協同最多算幾條連線。"""
    keyword_make: int = Field(ge=0)
    """PK-1b 關鍵字貼合：題目要的關鍵字，候選是「製造」它的，每個加這麼多。"""
    keyword_use: int = Field(ge=0)
    """PK-1b 關鍵字貼合：題目要的關鍵字，候選是「利用」它的，每個加這麼多（兩者都有就兩項都加）。"""
    keyword_extra_penalty: int = Field(ge=0)
    """PK-1b 關鍵字貼合：候選另外帶的關鍵字既不是題目要的、玩家手上也沒有，每個扣這麼多
    （主題分散）。"""
    theme_per_keyword: int = Field(ge=0)
    """PK-1b 主題相合：候選帶的關鍵字（題目要的以外）玩家手上的技能也有，每個加這麼多。"""
    theme_max_keywords: int = Field(ge=0)
    """PK-1b 主題相合最多算幾個關鍵字。"""
    element_match: int = Field(ge=0)
    """PK-1b 元素相合：玩家手上每有一招和候選同元素的技能，加這麼多。"""
    element_match_max: int = Field(ge=0)
    """PK-1b 元素相合最多算幾招手上的技能。"""
    element_any: int = Field(ge=0)
    """PK-1b：候選有元素（不是物理）就加這麼多（有元素的招，名稱與描述比較有主題感）。"""
    odd_condition_penalty: int = Field(ge=0)
    """PK-1b：候選帶「怪條件」（第一輪才生效的非傷害效果、有條件的刻紋等；
    ``trpg.skillgen.skill_pick.odd_conditions``），每一處扣這麼多。只影響挑選的排序，不改合法判定。"""
    thin_penalty: int = Field(ge=0)
    """PK-2「這招有沒有料」：候選單薄（``trpg.skillgen.skill_pick.thin_reasons``：只有沒效果的刻紋、
    標記或揭露；只有條件式的非傷害效果；史詩以上有作用的效果太少），每一項扣這麼多。只影響排序。"""
    thin_epic_min_effects: int = Field(ge=1, le=6)
    """PK-2：史詩以上的候選至少要有幾個「有作用的效果」（刻紋、標記、揭露不算），少於就算單薄。"""
    behavior_per_point: int = Field(ge=0)
    """打法：候選帶的關鍵字與玩家用過的動作相符，每 1 次加這麼多（``skill_keywords.yaml`` 的
    ``actions``）。"""
    behavior_cap: int = Field(ge=0)
    """打法分數的上限。"""
    route_main: int = Field(ge=0)
    """縮放屬性跟主屬性（同路線找法 ①）。"""
    route_dual: int = Field(ge=0)
    """雙屬性技能靠第二屬性跟上主屬性（同路線找法 ②）。"""
    pool_bonus: int = Field(ge=0)
    """手寫技能（技能池）的加分；0＝和組合器的候選一視同仁。"""
    same_skeleton_penalty: int = Field(ge=0)
    """多樣性：和已選進前 K 的候選同骨架，每一個扣這麼多。"""
    same_shape_penalty: int = Field(ge=0)
    """多樣性：同形狀，每一個扣這麼多。"""
    same_effects_penalty: int = Field(ge=0)
    """多樣性：效果種類完全相同（只差元素或數字），每一個扣這麼多。"""
    same_element_penalty: int = Field(ge=0)
    """多樣性：元素標籤相同，每一個扣這麼多。"""
    route_off_penalty: int = Field(ge=0)
    """PK-3（06 6.7，題 1 B）：「跟主路線」改成扣分——候選不符合這一格的路線（加深、橋接要跟主路線；
    新方向要不同屬性），扣這麼多。只有這一格符合路線的候選不夠 ``pool.relax_until`` 個時才會
    放進來。"""
    keyword_relaxed_penalty: int = Field(ge=0)
    """PK-3（同上）：多關鍵字的格子（橋接）放寬成只帶其中一部分關鍵字的候選，扣這麼多。"""
    wish_match: int = Field(ge=0)
    """PK-4 許願池「願望相合」（07 7.6「許願池：願望驅動」第 3 點：打分以願望相合為最大權重，高過和
    手上技能的協同）：候選每命中一個願望標籤（關鍵字、元素、效果類型、形狀、種類）加這麼多。只有
    許願池用。"""


WISH_TAG_GROUPS: tuple[str, ...] = ("keywords", "elements", "effects", "shapes", "kinds")
"""願望標籤的五類（07 7.6「許願池：願望驅動」第 1 點；依這個順序顯示與檢查）。"""


class WishTagItem(ContentModel):
    """願望標籤清單的一個值：代碼與中文名。"""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name_zh: str = Field(min_length=1)


class WishEffectTag(WishTagItem):
    """效果類型標籤：技能（含接續段、分支）裡出現這些原語、狀態就算命中。``control_statuses``＝
    有控制類別（``control_group``）的狀態也算；``beneficial_statuses``＝增益狀態（``polarity:
    buff``）也算，但已經寫在其他效果類型 ``statuses`` 裡的不算（例：護盾）。"""

    primitives: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    params: tuple[str, ...] = ()
    """效果上有這些參數（有值）也算（WC-2，#167：吸血 ``lifesteal_permille``、聖光雙效
    ``split_heal`` 算「治療」；06 6.18 A、B）。"""
    control_statuses: bool = False
    beneficial_statuses: bool = False


class WishShapeTag(WishTagItem):
    """形狀標籤：技能（第一段）的形狀是這些之一就算命中。"""

    shapes: tuple[str, ...] = Field(min_length=1)


class WishTagRules(ContentModel):
    """PK-4 願望標籤的固定清單（07 7.6「許願池：願望驅動」第 1 點）。關鍵字用內容庫的 16 個
    （06 6.27.1），這裡只放每類最多幾個。HC-4b2：「關鍵字、效果最多 2 個，元素 2 階起最多 2 個」
    是 07 7.6 的規則，數字只寫在 ``skill_pick.yaml``（schema 不再另外寫死上限）。"""

    max_keywords: int = Field(ge=0)
    max_elements: int = Field(ge=0, le=1)
    max_elements_dual: int = Field(ge=0)
    """角色到第二元素的階級（``skill_budget.yaml`` 的 ``min_character_tier.second_element``，初值
    2 階）起元素最多幾個（WC-2，#167；07 7.6 第 1 點、06 6.34.9 第二元素 2 階開放）。"""
    max_effects: int = Field(ge=0)
    max_shapes: int = Field(ge=0, le=1)
    max_kinds: int = Field(ge=0, le=1)
    elements: tuple[WishTagItem, ...] = ()
    effects: tuple[WishEffectTag, ...] = ()
    shapes: tuple[WishShapeTag, ...] = ()
    kinds: tuple[WishTagItem, ...] = ()

    def limit(self, group: str, *, dual: bool = False) -> int:
        """某一類最多選幾個。``dual``＝角色已到第二元素的階級（元素改用 ``max_elements_dual``）。"""
        return {
            "keywords": self.max_keywords,
            "elements": self.max_elements_dual if dual else self.max_elements,
            "effects": self.max_effects,
            "shapes": self.max_shapes,
            "kinds": self.max_kinds,
        }[group]

    def items(self, group: str) -> tuple[WishTagItem, ...]:
        """某一類的清單（關鍵字不在這裡，回傳空）。"""
        found: dict[str, tuple[WishTagItem, ...]] = {
            "elements": self.elements,
            "effects": self.effects,
            "shapes": self.shapes,
            "kinds": self.kinds,
        }
        return found.get(group, ())

    @model_validator(mode="after")
    def _check(self) -> WishTagRules:
        for group in WISH_TAG_GROUPS[1:]:
            ids = [i.id for i in self.items(group)]
            if len(set(ids)) != len(ids):
                raise ValueError(f"wish_tags.{group} 有重複的代碼")
        if any(k.id not in ("active", "passive", "reaction") for k in self.kinds):
            raise ValueError("wish_tags.kinds 只能是 active、passive、reaction")
        return self


class WishTags(ContentModel):
    """玩家的願望翻成的需求標籤（PK-4；07 7.6「許願池：願望驅動」第 1 點）：每一類都可以不選，值是
    清單的代碼（關鍵字是內容庫的關鍵字 ID）。合不合清單由
    :func:`trpg.skillgen.wish_pick.wish_tags_problem` 檢查（這裡只管格式）。"""

    keywords: tuple[str, ...] = ()
    elements: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()
    shapes: tuple[str, ...] = ()
    kinds: tuple[Literal["active", "passive", "reaction"], ...] = ()

    def group(self, name: str) -> tuple[str, ...]:
        """某一類選了哪些。"""
        return tuple(getattr(self, name))

    def empty(self) -> bool:
        """一個標籤都沒有。"""
        return not any(self.group(g) for g in WISH_TAG_GROUPS)


class SkillPickRules(ContentModel):
    """``content/skill_pick.yaml``。"""

    enabled: bool = True
    """PK-2 開關（06 6.7 #165）：真＝原型的升級三選一（含白板格）與完整技能三選一（原型特殊時刻、
    大世界機遇）走挑選模式（``trpg.skillgen.pick_offer``）；假＝完全回到 PK-2 前的出題流程。"""
    flash_enabled: bool = True
    """PK-3 閃現開關（06 6.7、6.34.7 #165）：真＝閃現與重閃走挑選模式
    （``trpg.skillgen.flash_pick``：程式照原本出題決定每一格的類別與轉型保底，每格依用法統計給幾個
    合法候選，LLM 只挑與取名）；假＝回到 PK-3 前的流程（LF-2：LLM 從目錄提議）。和 ``enabled``
    （三選一）分開。"""
    wish_enabled: bool = True
    """PK-4 許願池開關（07 7.6「許願池：願望驅動」）：真＝許願改走願望驅動（願望翻成需求標籤、照標籤
    做大池候選、以願望相合打分、LLM 挑 3 張並回應願望、做不到時照實寫）；假＝回到 PK-4 前的許願
    流程（對關鍵字＋自由設計）。"""
    pool: PickPoolRules
    weights: PickWeights
    wish_tags: WishTagRules
    """PK-4 願望標籤的固定清單（07 7.6「許願池：願望驅動」第 1 點）。"""
