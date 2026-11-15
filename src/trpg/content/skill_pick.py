"""技能生成「挑選模式」的打分權重與候選池大小（Phase PK-1；資料檔 ``content/skill_pick.yaml``）。

提案 ``docs/phases/技能生成-挑選模式提案.md`` 第 4 節、第 7.2 節：程式先用組合器多種子抽出合法候選、
依設計去重，再依「適不適合這位玩家」打分（**不比強弱**），取前 K 個交給 LLM 挑一個並命名。這張表只放
數字（全部是整數），由使用者在數值工坊調（第 6 節第 5 題 A）；看哪些項目由程式決定。

不嵌入規則包（不影響戰鬥結算與重播）；它在 ``library.files`` 裡，所以改了 ``ruleset_hash`` 與
``content_digest`` 會變（同 ``skill_icon_art.yaml``）。
"""

from __future__ import annotations

from pydantic import Field, model_validator

from trpg.content.schemas import ContentModel

__all__ = ["PickPoolRules", "PickWeights", "SkillPickRules"]


class PickPoolRules(ContentModel):
    """候選池：組合器抽幾個種子、湊到幾個不同設計就停、送幾個給 LLM。"""

    seeds: int = Field(default=60, ge=1, le=400)
    """組合器最多抽幾個種子（每個種子一招；同一個設計只留第一個）。"""
    designs: int = Field(default=16, ge=1, le=100)
    """湊到這麼多個不同設計就停止抽樣（省 CPU 時間；打分前的候選上限）。"""
    top_k: int = Field(default=5, ge=1, le=8)
    """送給 LLM 的候選數（提案第 6 節第 2 題 A：每格 4～6 個）。"""
    min_for_llm: int = Field(default=2, ge=1, le=8)
    """候選少於這個數就不呼叫 LLM，直接用第一名（提案 7.6）。"""
    handwritten_max: int = Field(default=0, ge=0, le=1)
    """PK-1b：送給 LLM 的候選裡最多幾個手寫技能（技能池）；0＝完全不放（只在候選池是空的時候照現行
    退回技能池）。玩家手上已有的技能不論這裡設多少都不會進候選。"""
    element_seeds: int = Field(default=12, ge=0, le=400)
    """PK-1b：玩家手上有元素技能、而候選池裡同元素的設計少於 ``element_designs`` 個時，另外用獨立的
    亂數串流再抽最多這麼多個種子，只收和玩家同元素的新設計；0＝不補抽。"""
    element_designs: int = Field(default=2, ge=0, le=40)
    """PK-1b：候選池裡和玩家同元素的設計至少要有幾個（不夠才補抽，補到這個數就停）。"""
    slot_seeds: int = Field(default=16, ge=0, le=200)
    """PK-2 三選一的每一格（加深／橋接／新方向）：照這一格的出題條件（關鍵字、種類、屬性路線）另外
    最多抽這麼多個種子當候選（獨立亂數串流；湊到 ``top_k`` 個不同設計就停）；0＝每格只有原本
    出題的那一張。白板三選一用這個。"""
    complete_slot_seeds: int = Field(default=8, ge=0, le=200)
    """PK-2 完整技能三選一的每一格另外抽幾個種子（組合器整招指定關鍵字，每個種子約 0.05～0.2 秒，
    所以比白板少）。"""
    nondamage_seeds: int = Field(default=10, ge=0, le=200)
    """PK-2 非傷害保底（#142）：保底格只留非傷害的候選，不到 ``top_k`` 個時（或三格都沒有非傷害的
    候選時，依新方向 → 橋接 → 加深）用另一條亂數串流最多補抽這麼多個種子，只收非傷害的；
    0＝不補抽。"""

    @model_validator(mode="after")
    def _check(self) -> PickPoolRules:
        if self.min_for_llm > self.top_k:
            raise ValueError("min_for_llm 不能大於 top_k")
        return self


class PickWeights(ContentModel):
    """打分權重（分數＝各項的加權和；全部是整數點數）。"""

    synergy_per_link: int = Field(default=150, ge=0)
    """協同：候選製造的關鍵字有一招手上的技能利用（或反過來），每一條連線（手上技能 × 關鍵字 ×
    方向）加這麼多（PK-1b 起 300 → 150、上限 3 → 5，讓條數拉開差距）。"""
    synergy_max_links: int = Field(default=5, ge=0)
    """協同最多算幾條連線。"""
    keyword_make: int = Field(default=80, ge=0)
    """PK-1b 關鍵字貼合：題目要的關鍵字，候選是「製造」它的，每個加這麼多。"""
    keyword_use: int = Field(default=40, ge=0)
    """PK-1b 關鍵字貼合：題目要的關鍵字，候選是「利用」它的，每個加這麼多（兩者都有就兩項都加）。"""
    keyword_extra_penalty: int = Field(default=30, ge=0)
    """PK-1b 關鍵字貼合：候選另外帶的關鍵字既不是題目要的、玩家手上也沒有，每個扣這麼多
    （主題分散）。"""
    theme_per_keyword: int = Field(default=60, ge=0)
    """PK-1b 主題相合：候選帶的關鍵字（題目要的以外）玩家手上的技能也有，每個加這麼多。"""
    theme_max_keywords: int = Field(default=3, ge=0)
    """PK-1b 主題相合最多算幾個關鍵字。"""
    element_match: int = Field(default=150, ge=0)
    """PK-1b 元素相合：玩家手上每有一招和候選同元素的技能，加這麼多。"""
    element_match_max: int = Field(default=2, ge=0)
    """PK-1b 元素相合最多算幾招手上的技能。"""
    element_any: int = Field(default=40, ge=0)
    """PK-1b：候選有元素（不是物理）就加這麼多（有元素的招，名稱與描述比較有主題感）。"""
    odd_condition_penalty: int = Field(default=200, ge=0)
    """PK-1b：候選帶「怪條件」（第一輪才生效的非傷害效果、有條件的刻紋等；
    ``trpg.skillgen.skill_pick.odd_conditions``），每一處扣這麼多。只影響挑選的排序，不改合法判定。"""
    thin_penalty: int = Field(default=250, ge=0)
    """PK-2「這招有沒有料」：候選單薄（``trpg.skillgen.skill_pick.thin_reasons``：只有沒效果的刻紋、
    標記或揭露；只有條件式的非傷害效果；史詩以上有作用的效果太少），每一項扣這麼多。只影響排序。"""
    thin_epic_min_effects: int = Field(default=2, ge=1, le=6)
    """PK-2：史詩以上的候選至少要有幾個「有作用的效果」（刻紋、標記、揭露不算），少於就算單薄。"""
    behavior_per_point: int = Field(default=20, ge=0)
    """打法：候選帶的關鍵字與玩家用過的動作相符，每 1 次加這麼多（``skill_keywords.yaml`` 的
    ``actions``）。"""
    behavior_cap: int = Field(default=400, ge=0)
    """打法分數的上限。"""
    route_main: int = Field(default=200, ge=0)
    """縮放屬性跟主屬性（同路線找法 ①）。"""
    route_dual: int = Field(default=100, ge=0)
    """雙屬性技能靠第二屬性跟上主屬性（同路線找法 ②）。"""
    pool_bonus: int = Field(default=0, ge=0)
    """手寫技能（技能池）的加分；0＝和組合器的候選一視同仁。"""
    same_skeleton_penalty: int = Field(default=150, ge=0)
    """多樣性：和已選進前 K 的候選同骨架，每一個扣這麼多。"""
    same_shape_penalty: int = Field(default=100, ge=0)
    """多樣性：同形狀，每一個扣這麼多。"""
    same_effects_penalty: int = Field(default=250, ge=0)
    """多樣性：效果種類完全相同（只差元素或數字），每一個扣這麼多。"""
    same_element_penalty: int = Field(default=60, ge=0)
    """多樣性：元素標籤相同，每一個扣這麼多。"""


class SkillPickRules(ContentModel):
    """``content/skill_pick.yaml``。"""

    enabled: bool = True
    """PK-2 開關（06 6.7 #165）：真＝原型的升級三選一（含白板格）與完整技能三選一（原型特殊時刻、
    大世界機遇）走挑選模式（``trpg.skillgen.pick_offer``）；假＝完全回到 PK-2 前的出題流程。"""
    pool: PickPoolRules = Field(default_factory=PickPoolRules)
    weights: PickWeights = Field(default_factory=PickWeights)
