"""修正規則：``ModifierTarget``、``ModifierChange``、``ModifierSpec``。"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills.conditions import ConditionSpec
from trpg.content.skills.constants import (
    _MAX_DISPLACE,
    _MAX_ON_HIT_EFFECTS,
    CHANGE_TARGETS,
    DETONATE_RUNES,
    INSCRIBE,
    MODIFIER_CHANGES,
    NONZERO_CHANGES,
    ON_HIT_PRIMITIVES,
    PER_TURN_LIMIT_CHANGES,
    RUNE_BOTH_MESSAGE,
    SELF_CONDITIONS,
    SELF_ONLY_CHANGES,
    TRUE_ONLY_CHANGES,
    BasicAction,
)
from trpg.content.skills.effects import EffectSpec
from trpg.shared.types import Element


class ModifierTarget(ContentModel):
    """修正規則的套用對象（``applies_to``；至少一項，多項為「或」）。

    - ``actions``：基本動作（``attack`` 普攻、``shove`` 推擊、``trip`` 絆倒、``interact`` 互動）。
    - ``skill_tags``：帶這些標籤（含其他修正規則用 ``add_tags`` 加上的）的技能。
    - ``all_attacks``：你的所有攻擊——普攻與「有對敵方傷害效果」的技能（修正型被動）。
    - ``all_skills``：你施放的所有技能（主動、姿態與反應技）。
    - ``weapon_skills``（3J-3，化形專精）：你的武器技（``category: weapon`` 的技能；不含普攻）；
      只有 ``damage_permille`` 可以用。

    被動觸發與陷阱觸發的效果不是「你的動作」，不受修正規則影響。
    """

    actions: tuple[BasicAction, ...] = ()
    skill_tags: tuple[str, ...] = ()
    all_attacks: bool = False
    all_skills: bool = False
    weapon_skills: bool = False

    @model_validator(mode="after")
    def _check(self) -> ModifierTarget:
        if not (
            self.actions
            or self.skill_tags
            or self.all_attacks
            or self.all_skills
            or self.weapon_skills
        ):
            raise ValueError(
                "applies_to 至少要有一項（actions、skill_tags、all_attacks、all_skills、"
                "weapon_skills）"
            )
        if len(set(self.actions)) != len(self.actions):
            raise ValueError("applies_to.actions 不可重複")
        bad = [t for t in self.skill_tags if re.match(ID_PATTERN, t) is None]
        if bad:
            raise ValueError(f"applies_to.skill_tags 必須是小寫 snake_case：{', '.join(bad)}")
        if len(set(self.skill_tags)) != len(self.skill_tags):
            raise ValueError("applies_to.skill_tags 不可重複")
        return self

    def keys(self) -> frozenset[str]:
        """對象的代碼集合：基本動作、``all_attacks``、``all_skills``、``skill_tags``。"""
        keys: set[str] = set(self.actions)
        if self.all_attacks:
            keys.add("all_attacks")
        if self.all_skills:
            keys.add("all_skills")
        if self.weapon_skills:
            keys.add("weapon_skills")
        if self.skill_tags:
            keys.add("skill_tags")
        return frozenset(keys)


class ModifierChange(ContentModel):
    """修正規則的改變（恰好一種，正交；``docs/phases/Phase3C計畫.md`` 4.1）。

    - ``damage_permille``：傷害 ±‰（−500～＋1000，不可為 0；多條規則加總後套用一次）。
    - ``hit_bonus``：命中 ±（−3～＋3）。
    - ``cooldown_delta``：命中後該技能剩餘冷卻 −1 或 −2（下限 0）。
    - ``push_distance_delta``：推擊與拉扯距離 +1 或 +2（結果截斷在 ``max_displace_distance``）。
    - ``ap_delta``：AP 成本 ±1（結果至少 1）。
    - ``range_delta``：射程 −1～＋2（不可為 0；結果至少 1；只改有射程的形狀與普攻）。
    - ``add_element``：傷害獲得元素（只改物理傷害，已有元素的不覆寫）。
    - ``add_tags``：技能獲得標籤（1～3 個）。
    - ``on_hit_effects``：命中後附加效果（1～2 個，原語見 :data:`ON_HIT_PRIMITIVES`）。
    - ``grant_pierce``：技能獲得穿透（只能是 ``true``；只對遠程單體與直線的技能有效，
      Phase 3C-5b）。
    - ``area_delta``（3D-3）：範圍型形狀大小 +1（直線與錐形的 ``size``、環形與範圍光環的
      ``radius``；不超過 ``skill_shapes.yaml`` 的最大值，``cross``、``square3`` 的大小固定）。
    - ``shape_to``（3D-3）：形狀轉換，只有 ``skill_shapes.yaml`` 的 ``conversions`` 表列的組合：
      ``single → line``、``single → chain``、``line → cone``；技能的效果原語必須允許新形狀，
      否則不轉。
    - ``allow_self_target``（3D-3，只能是 ``true``）：治療、護盾、增益類技能（有對友方生效的效果）
      的影響範圍也包含施放者自己（單體形狀本來就能選自己；直線、錐形等形狀的範圍不含施放者，
      這條規則把他算進去）。
    - ``heal_permille``（3-24b1，8.21.4.2）：你的治療量 ±‰（技能的治療與聖光雙效的治療；
      −500～＋1000，不可為 0；多條規則加總後套用一次，結果下限 0）。
    - ``summon_hp_permille``（3-24b1）：你召喚出來的召喚物最大 HP +n‰（1～1000；召喚時結算）。
    - ``summon_attack_dice``（3-24b1）：你召喚出來的召喚物攻擊傷害骰多 +n 顆（只能是 1；召喚時
      結算）。
    - ``summon_limit_delta``（3-33f1，6.29.4）：你同時存在的召喚物上限 ±1（只能是 +1 或 −1；
      結果不低於 1、不超過 ``core.summon_hard_cap``）。
    - ``summon_duration_delta``（3-33f1）：你召喚出來的召喚物持續輪數 +n（1～2；加在
      ``summon_max_duration`` 之後）。
    - ``summon_damage_permille``（3-33f1）：你召喚出來的召喚物傷害加成 +n‰（1～1000；召喚時快照，
      與成長加成一樣計入全身 +50% 上限）。
    - ``form_upkeep_permille``（3J-3，化形專精）：你的形態維持費 −n‰（−1000～−1；−500＝減半，
      無條件捨去）。
    - ``form_entry_permille``（3J-3，化形專精）：你的形態進入獎勵的數值 +n‰（1～1000；+500＝×1.5，
      無條件捨去；每次進入結算時套用）。
    """

    damage_permille: int | None = Field(default=None, ge=-500, le=1000)
    hit_bonus: int | None = Field(default=None, ge=-3, le=3)
    cooldown_delta: int | None = Field(default=None, ge=-2, le=-1)
    push_distance_delta: int | None = Field(default=None, ge=1, le=2)
    ap_delta: int | None = Field(default=None, ge=-1, le=1)
    range_delta: int | None = Field(default=None, ge=-1, le=2)
    add_element: Element | None = None
    add_tags: tuple[str, ...] | None = None
    on_hit_effects: tuple[EffectSpec, ...] | None = None
    grant_pierce: bool | None = None
    area_delta: int | None = Field(default=None, ge=1, le=1)
    shape_to: Literal["line", "chain", "cone"] | None = None
    allow_self_target: bool | None = None
    heal_permille: int | None = Field(default=None, ge=-500, le=1000)
    summon_hp_permille: int | None = Field(default=None, ge=1, le=1000)
    summon_attack_dice: int | None = Field(default=None, ge=1, le=1)
    summon_limit_delta: int | None = Field(default=None, ge=-1, le=1)
    summon_duration_delta: int | None = Field(default=None, ge=1, le=2)
    summon_damage_permille: int | None = Field(default=None, ge=1, le=1000)
    form_upkeep_permille: int | None = Field(default=None, ge=-1000, le=-1)
    form_entry_permille: int | None = Field(default=None, ge=1, le=1000)

    @model_validator(mode="after")
    def _check(self) -> ModifierChange:
        given = [name for name in MODIFIER_CHANGES if getattr(self, name) is not None]
        if len(given) != 1:
            got = "、".join(given) if given else "沒有"
            raise ValueError(f"change 必須恰好一種（{'、'.join(MODIFIER_CHANGES)}），收到 {got}")
        kind = given[0]
        value = getattr(self, kind)
        if kind in NONZERO_CHANGES and value == 0:
            raise ValueError(f"change.{kind} 不可為 0")
        if kind == "add_element" and value is Element.PHYSICAL:
            raise ValueError("change.add_element 不可是物理（physical）")
        if kind in TRUE_ONLY_CHANGES and value is not True:
            raise ValueError(f"change.{kind} 只能是 true")
        if kind == "add_tags":
            self._check_tags(value)
        if kind == "on_hit_effects":
            self._check_on_hit(value)
        return self

    @staticmethod
    def _check_tags(tags: tuple[str, ...]) -> None:
        if not 1 <= len(tags) <= 3:  # noqa: PLR2004 - 規格的 1～3 個
            raise ValueError(f"change.add_tags 必須有 1 到 3 個標籤，收到 {len(tags)} 個")
        bad = [t for t in tags if re.match(ID_PATTERN, t) is None]
        if bad:
            raise ValueError(f"change.add_tags 必須是小寫 snake_case：{', '.join(bad)}")
        if len(set(tags)) != len(tags):
            raise ValueError("change.add_tags 不可重複")

    @staticmethod
    def _check_on_hit(effects: tuple[EffectSpec, ...]) -> None:
        if not 1 <= len(effects) <= _MAX_ON_HIT_EFFECTS:
            raise ValueError(
                f"change.on_hit_effects 必須有 1 到 {_MAX_ON_HIT_EFFECTS} 個效果，"
                f"收到 {len(effects)} 個"
            )
        for index, effect in enumerate(effects):
            if effect.type not in ON_HIT_PRIMITIVES:
                raise ValueError(
                    f"change.on_hit_effects[{index}]：{effect.type} 不能當命中後效果"
                    f"（可用：{'、'.join(ON_HIT_PRIMITIVES)}）"
                )
            if effect.type in ("push", "pull") and (
                effect.distance is None or not 1 <= effect.distance <= _MAX_DISPLACE
            ):
                raise ValueError(
                    f"change.on_hit_effects[{index}]：推擊與拉扯的距離必須是 1 到 "
                    f"{_MAX_DISPLACE} 格，收到 {effect.distance}"
                )
            ModifierChange._check_on_hit_rune(index, effect)
        types = {e.type for e in effects}
        if INSCRIBE in types and DETONATE_RUNES in types:
            raise ValueError(RUNE_BOTH_MESSAGE)

    @staticmethod
    def _check_on_hit_rune(index: int, effect: EffectSpec) -> None:
        where = f"change.on_hit_effects[{index}]（{effect.type}）"
        if effect.type == DETONATE_RUNES and effect.scope != "target_cell":
            raise ValueError(f"{where}：命中後引爆必須填 scope: target_cell（只引爆目標那 1 格）")
        if effect.type != DETONATE_RUNES and effect.scope is not None:
            raise ValueError(f"{where}：只有 detonate_runes 使用 scope")
        if effect.type == INSCRIBE and (effect.element is None) == (effect.tag is None):
            raise ValueError(f"{where}：必須恰好填 element 或 tag 其中一個")
        if effect.type == INSCRIBE and effect.dice is not None:
            raise ValueError(f"{where}：符文本身沒有效果，不可填 dice")

    @property
    def kind(self) -> str:
        """這條改變的種類（:data:`MODIFIER_CHANGES` 之一）。"""
        return next(name for name in MODIFIER_CHANGES if getattr(self, name) is not None)


class ModifierSpec(ContentModel):
    """一條修正規則：套用對象、條件（可省略，沿用 ``skill_conditions.yaml``）與改變。

    條件的判斷對象：``self_hp_below`` 看持有者；其他條件看這次動作的目標（傷害、命中、推擊距離
    看該目標；冷卻看「被命中的敵人中至少一個」；命中後效果看被命中的目標）。:data:`SELF_ONLY_CHANGES`
    在選目標之前就要決定，所以條件只能是 ``self_hp_below``。
    """

    applies_to: ModifierTarget
    condition: ConditionSpec | None = None
    change: ModifierChange
    per_turn_limit: Literal[1] | None = None
    """每回合最多生效幾次（Phase 3-31；只能是 1）。次數存在持有者的戰鬥狀態內（自己回合開始時
    清除）；只有 ``damage_permille``（且只套用在普攻）與 ``on_hit_effects`` 可以填。"""
    empty_slots_cap: int | None = Field(default=None, ge=1, le=6)
    """傷害加成依空欄位數計算（Phase 3-32a，普攻精通）：``damage_permille`` 變成「主動技能欄每空
    1 格加這麼多‰」，最多算這麼多格；空格數在每次普攻結算當下由引擎從單位裝備的主動技能數量算出
    （``core.skill_slots.active`` 減去裝備的主動技能數）。只能搭配 ``damage_permille`` 且只套用在
    普攻（``applies_to.actions``），不可與 ``per_turn_limit`` 並用。"""

    @model_validator(mode="after")
    def _check(self) -> ModifierSpec:
        kind = self.change.kind
        self._check_per_turn(kind)
        self._check_empty_slots(kind)
        allowed = CHANGE_TARGETS[kind]
        extra = sorted(self.applies_to.keys() - allowed)
        if extra:
            raise ValueError(
                f"change.{kind} 不能套用在 {'、'.join(extra)}（可用：{'、'.join(sorted(allowed))}）"
            )
        condition = self.condition
        if (
            kind in SELF_ONLY_CHANGES
            and condition is not None
            and any(part.type not in SELF_CONDITIONS for part in condition.alternatives())
        ):
            raise ValueError(
                f"change.{kind} 在選目標之前就決定，條件只能是 self_hp_below，收到 {condition.type}"
            )
        return self

    def _check_per_turn(self, kind: str) -> None:
        if self.per_turn_limit is None:
            return
        if kind not in PER_TURN_LIMIT_CHANGES:
            names = "、".join(sorted(PER_TURN_LIMIT_CHANGES))
            raise ValueError(f"per_turn_limit 只能用在 {names}，收到 change.{kind}")
        target = self.applies_to
        if kind == "damage_permille" and (
            target.skill_tags or target.all_attacks or target.all_skills
        ):
            raise ValueError("傷害加成的 per_turn_limit 只能套用在普攻（applies_to.actions）")

    def _check_empty_slots(self, kind: str) -> None:
        if self.empty_slots_cap is None:
            return
        target = self.applies_to
        if kind != "damage_permille" or (self.change.damage_permille or 0) <= 0:
            raise ValueError("empty_slots_cap 只能搭配正的 change.damage_permille")
        if target.skill_tags or target.all_attacks or target.all_skills:
            raise ValueError("empty_slots_cap 只能套用在普攻（applies_to.actions）")
        if self.per_turn_limit is not None:
            raise ValueError("empty_slots_cap 不可與 per_turn_limit 並用")
