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

    @model_validator(mode="after")
    def _check(self) -> PickPoolRules:
        if self.min_for_llm > self.top_k:
            raise ValueError("min_for_llm 不能大於 top_k")
        return self


class PickWeights(ContentModel):
    """打分權重（分數＝各項的加權和；全部是整數點數）。"""

    synergy_per_link: int = Field(default=300, ge=0)
    """協同：候選製造的關鍵字有一招手上的技能利用（或反過來），每一條連線加這麼多。"""
    synergy_max_links: int = Field(default=3, ge=0)
    """協同最多算幾條連線。"""
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

    pool: PickPoolRules = Field(default_factory=PickPoolRules)
    weights: PickWeights = Field(default_factory=PickWeights)
