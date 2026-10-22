"""3 級分歧進化的模板（``content/skill_evolution.yaml``；Phase 3-26b，
``docs/design/06-技能.md`` 6.28）。

進化模板只描述「怎麼改一招技能」（換形狀、加第二元素、延遲大範圍、擊殺接續……）；強度不寫在這裡：
套用模板之後由 :mod:`trpg.skillgen.evolution` 依 **同階預算** 重新調整骰子與倍率，再交給驗證器，
不合格
的模板不出現。挑選規則（加深／橋接）也在 :mod:`trpg.skillgen.evolution`。

跨檔案檢查（``grafts`` 的關鍵字存在、``skeletons`` 存在）在 :mod:`trpg.content.library` 載入時。
"""

from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills import EffectSpec, ShapeSpec

__all__ = [
    "EvolutionOp",
    "EvolutionShape",
    "EvolutionTable",
    "EvolutionTemplate",
    "KeywordGraft",
]

type EvolutionOp = Literal[
    "reshape", "intensify", "extend", "delay", "on_kill", "graft_uses", "graft_makes"
]
"""模板的改法：

- ``reshape``：換形狀（``shapes`` 依序嘗試；跳過和原本相同種類的形狀）。
- ``intensify``：加深這招自己的關鍵字——已經有同一個「製造」效果時持續 +1 回合，否則加上該關鍵字的
  製造效果（``grafts.<關鍵字>.makes``）。
- ``extend``：這招的狀態、表面與區域各多持續 1 回合（硬控狀態不延長）。
- ``delay``：第一個傷害效果改成延遲爆炸（``delayed_damage``，``delay_rounds``、``delay_radius``）。
- ``on_kill``：第一個傷害效果加上擊殺時效果（``on_kill``）。
- ``graft_uses``：加上「利用」橋接關鍵字的加碼效果（``grafts.<關鍵字>.uses``；條件成立時加傷）。
- ``graft_makes``：加上「製造」橋接關鍵字的效果（``grafts.<關鍵字>.makes``）。
"""

_BRIDGE_OPS = ("graft_uses", "graft_makes")


class EvolutionShape(ContentModel):
    """``reshape`` 的一個形狀選項。``reach``：``far`` 是遠距離用（平均距離 ≥ ``far_distance`` 時
    先試）、``near`` 是近距離用，``any`` 不分。"""

    shape: ShapeSpec
    reach: Literal["near", "far", "any"] = "any"


class EvolutionTemplate(ContentModel):
    """一個進化模板。``branch`` 決定它是「加深」還是「橋接」用的模板。"""

    id: str = Field(pattern=ID_PATTERN)
    branch: Literal["deepen", "bridge"]
    op: EvolutionOp
    prefix_zh: str | None = None
    """組合式名稱的前綴（「{前綴}・{原名}」）；省略時用關鍵字的 ``prefix_zh``（``intensify`` 與
    橋接模板）。"""
    summary_zh: str = Field(min_length=1)
    """技能卡比較畫面上的一句話；``{keyword}`` 會換成關鍵字名稱。"""
    shapes: tuple[EvolutionShape, ...] = ()
    delay_rounds: int | None = Field(default=None, ge=1, le=3)
    delay_radius: int | None = Field(default=None, ge=0, le=2)
    on_kill: tuple[EffectSpec, ...] = ()
    skeletons: tuple[str, ...] = ()
    """原本的骨架不合格時，依序改試的骨架（例如加上條件加碼後改成 ``combo``）。"""

    @model_validator(mode="after")
    def _check(self) -> EvolutionTemplate:
        bridge = self.op in _BRIDGE_OPS
        if bridge != (self.branch == "bridge"):
            raise ValueError(f"模板 {self.id}：{self.op} 只能用在 {'橋接' if bridge else '加深'}")
        if self.op == "reshape" and not self.shapes:
            raise ValueError(f"模板 {self.id}：reshape 必須列出 shapes")
        if self.op == "delay" and (self.delay_rounds is None or self.delay_radius is None):
            raise ValueError(f"模板 {self.id}：delay 必須填 delay_rounds 與 delay_radius")
        if self.op == "on_kill" and not self.on_kill:
            raise ValueError(f"模板 {self.id}：on_kill 必須列出 on_kill 效果")
        if self.op in ("reshape", "extend", "delay", "on_kill") and self.prefix_zh is None:
            raise ValueError(f"模板 {self.id}：{self.op} 必須填 prefix_zh")
        return self


class KeywordGraft(ContentModel):
    """一個關鍵字的嫁接效果。``makes`` 是製造該關鍵字的效果（數值固定）；``uses`` 是利用它的加碼
    效果（必須有 ``condition``，強度由預算調整：法術技調骰子、武器技調倍率）。"""

    prefix_zh: str = Field(min_length=1)
    makes: EffectSpec | None = None
    uses: EffectSpec | None = None

    @model_validator(mode="after")
    def _check(self) -> KeywordGraft:
        if self.uses is not None and self.uses.condition is None:
            raise ValueError("uses 的加碼效果必須有 condition")
        return self


class EvolutionTable(ContentModel):
    """``content/skill_evolution.yaml``。"""

    far_distance: int = Field(default=3, ge=1)
    """平均施放距離 ≥ 它時，``reshape`` 先試 ``far`` 的形狀，否則先試 ``near``。"""
    spread_targets_permille: int = Field(default=1500, ge=1000)
    """平均目標數（‰）低於它時，視為「單體用法」：加深的模板優先換形狀。"""
    bridge_keyword_tries: int = Field(default=3, ge=1)
    """橋接最多嘗試幾個關鍵字（依統計排序）。"""
    templates: tuple[EvolutionTemplate, ...] = ()
    grafts: dict[str, KeywordGraft] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _unique(self) -> EvolutionTable:
        dup = sorted(i for i, n in Counter(t.id for t in self.templates).items() if n > 1)
        if dup:
            raise ValueError(f"進化模板 ID 重複：{', '.join(dup)}")
        return self

    def branch(self, branch: Literal["deepen", "bridge"]) -> tuple[EvolutionTemplate, ...]:
        return tuple(t for t in self.templates if t.branch == branch)

    def summary(self) -> str:
        return f"{len(self.templates)} 個進化模板、{len(self.grafts)} 個關鍵字嫁接"
