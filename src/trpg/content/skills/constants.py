"""技能內容的常數、列舉值與原語／機制識別字（純資料，不依賴任何模型類別）。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Literal

from trpg.content.modifier_changes import bundled_modifier_changes
from trpg.content.yaml_sources import (
    mechanic_status,
    primitive_status,
    shape_role,
    split_heal_skeletons,
)
from trpg.shared.types import Element

SKILL_ID_PATTERN = r"^skill_[a-z0-9_]+$"


SKELETON_IDS: tuple[str, ...] = (
    "strike",
    "area",
    "control",
    "displace",
    "builder_finisher",
    "combo",
    "trap",
    "aura",
    "summon",
    "reaction",
    "stance",
    "passive",
    "modifier",
    "consume_status",
    "rune",
    "sacrifice",
)
"""``docs/design/06-技能.md`` 6.9 的 12 種骨架，加上 Phase 3C-2 的 ``modifier``（修正規則：改造型與
修正型被動，6.14.1）、3C-3b 的 ``consume_status``（6.14.2 管道 1）與 3-23 的 ``rune``（6.25 刻印）。
結構驗證見 ``skillgen``。"""


WEAPON_CLASSES: tuple[str, ...] = ("melee", "ranged", "focus")


REQUIRED_SHAPES: tuple[str, ...] = (
    "self",
    "single",
    "line",
    "cone",
    "cross",
    "square3",
    "ring",
    "ground_tile",
    "chain",
    "allies_in_radius",
    "object_then_tile",
    "unit_then_tile",
    "unit_pair",
)
"""引擎實作的 13 種形狀（``trpg.engine.skills.shapes``），資料檔必須全部定義。

``object_then_tile``（Phase 3C-5a）：投擲物件，先選射程內的物件、再選落點格。
``unit_then_tile``（Phase 3D-2b）：傳送他人，先選射程內的單位、再選落點格。
``unit_pair``（Phase 3D-2b）：任意兩者互換，選射程內的兩個單位。"""


REQUIRED_CONDITIONS: tuple[str, ...] = (
    "target_hp_below",
    "self_hp_below",
    "height_advantage",
    "target_on_surface",
    "target_has_status",
    "moved_this_turn",
    "adjacent_ally",
    "target_isolated",
    "first_round",
    "cast_tag_this_turn",
    "flanked",
    "from_behind",
    "self_concealed",
    "on_own_rune",
    "target_collided",
    "wielding_weapon",
    "in_form",
)
"""引擎實作的 17 種條件（``trpg.engine.skills.conditions``），資料檔必須全部定義。"""


type Targeting = Literal[
    "self", "unit", "tile", "direction", "none", "object_tile", "unit_tile", "unit_pair"
]


type Affects = Literal["enemies", "allies", "all", "self", "tiles"]


type SkillKind = Literal["active", "reaction", "passive", "stance", "modifier"]


type ReactionEvent = Literal[
    "hit_by_melee",
    "hit_by_attack",
    "ally_hit_adjacent",
    "enemy_leaves_adjacent",
    "hit_by_spell",
    "ally_downed",
    "enemy_enters_adjacent",
    "ally_targeted",
]


type SkillRarity = Literal["common", "rare", "epic", "legendary"]


type SkillCategory = Literal["weapon", "spell"]


type WeaponReq = Literal["melee", "ranged", "focus", "any"]


type Origin = Literal["builtin", "level_up", "drop", "crafted", "taught", "tome", "workshop"]
"""技能的來源；``workshop``：技能工坊（Phase 3F-1，開發工具）做的技能。"""


AFFECTS_VALUES: tuple[str, ...] = ("enemies", "allies", "all", "self", "tiles")


RARITY_ORDER: tuple[str, ...] = ("common", "rare", "epic", "legendary")
"""稀有度由低到高。"""


def rarity_rank(rarity: str) -> int:
    """稀有度的高低（普通 0 … 傳說 3）。"""
    return RARITY_ORDER.index(rarity)


MAX_EFFECTS = 4
"""一個技能（複合技能兩段合計）最多幾個效果原語；內容驗證、提議與預算檢查共用這個值。"""


_MAX_DISPLACE = 2


_MAX_COOLDOWN = 6


_MAX_AP_COST = 3


_PERMILLE = 1000


_MAX_MULTIPLIER_PERMILLE = 10_000


def _unique(ids: Iterable[str], what: str) -> None:
    dup = sorted(i for i, n in Counter(ids).items() if n > 1)
    if dup:
        raise ValueError(f"重複的{what} ID：{', '.join(dup)}")


SHAPE_ROLES: tuple[str, ...] = (
    "followup",
    "on_kill_second",
    "pierce",
    "shape_to",
    "zone_caster",
    "zone_moving",
)
"""``skill_shapes.yaml`` 的 ``shape_roles`` 必須有的用途。"""


SHAPE_TO_VALUES: tuple[str, ...] = shape_role("shape_to")
"""修正規則 ``shape_to`` 可以轉成的形狀（Phase 3D-3；組合見 ``skill_shapes.yaml``）。"""


type KnobLadder = Literal[
    "dice",
    "multipliers",
    "push_pull_distances",
    "blow_distances",
    "status_duration",
    "surface_duration",
    "stack_amount",
    "per_stack",
    "param_range",
]
"""強度旋鈕的階梯來源（Phase 3T-1；實作在 :data:`trpg.skillgen.composer_parts.KNOB_LADDERS`）。"""


type KnobWeight = Literal["caller", "core", "other", "status", "surface"] | int
"""旋鈕被抽中的權重：``caller`` 由呼叫端依核心／附帶傳入、``core``／``other`` 為
``skill_composer.yaml`` 的 ``structure.knob_weight_core``／``knob_weight_other``、``status``／
``surface`` 為 ``duration.status_weight``／``surface_weight``，或直接寫整數。"""


FORM_CATEGORY_TEXT: dict[str, str] = {"physical": "物理", "mental": "心智"}
"""形態類別的中文（``in_form`` 條件句；3J-3）。"""


_PLAIN_CONDITION_TEXT = {
    "moved_this_turn": "本回合移動過",
    "adjacent_ally": "身旁有友方",
    "target_isolated": "目標身邊沒有友方",
    "flanked": "夾擊（目標的對面有友方）",
    "from_behind": "背刺（站在目標背後）",
    "self_concealed": "潛行偷襲（自身隱蔽中）",
    "first_round": "第一輪",
    "target_collided": "目標本回合受過撞擊",
    "in_form": "你在形態中",
}
"""沒有參數的條件的一句話（Phase 3D-1）。"""


type ScaleBy = Literal[
    "missing_hp_10pct", "distance", "enemies_adjacent_target", "enemies_adjacent_self"
]


SCALE_BY_VALUES: tuple[str, ...] = (
    "missing_hp_10pct",
    "distance",
    "enemies_adjacent_target",
    "enemies_adjacent_self",
)
"""依情況縮放（Phase 3D-7b，6.17 E、6.18 G）的依據：施放者每少 10% 最大 HP、與目標的距離（格）、
目標相鄰的敵方數、施放者相鄰的敵方數。"""


MIN_SKILL_CRIT_RANGE = 15
"""技能 ``crit_range`` 的下限（Phase 3D-7b，6.17 B）。"""


ON_MISS_MIN_RARITY = "rare"
"""``cost.on_miss`` 失手反噬的最低稀有度（Phase 3D-7b，3D-7a 驗收決定）。"""


YAML_RANGED_FIELDS = frozenset(
    {
        "lifesteal_permille",
        "max_hp_permille",
        "multiplier_permille",
        "power_permille",
        "radius",
        "rounds",
        "splash",
    }
)
"""``EffectSpec`` 中只宣告型別、範圍完全取自 ``skill_primitives.yaml`` 的整數欄位（建構時就檢查）。
其餘整數欄位仍有較寬的 schema 範圍（健全性檢查）或只在跨檔案驗證時檢查細緻範圍。"""


EFFECT_NON_PARAM_FIELDS = frozenset({"type", "affects", "condition"})
"""``EffectSpec`` 中不是原語參數的欄位（其餘欄位一律視為參數，新增欄位不必另外登記）。"""


ON_CAST_TAG = "on_cast_tag"


ON_STATUS_APPLIED = "on_status_applied"


ON_SUMMON_DOWNED = "on_summon_downed"
"""召喚物倒下時（Phase 3-33f2）：只給裝備詞條用的觸發時機，效果是以倒下的召喚物為中心的爆炸或治療
（``sacrifice_summon`` 效果）。"""


ON_COLLISION = "on_collision"


ON_ENTER_SURFACE = "on_enter_surface"
"""帶參數或需要特別處理的觸發時機 ID（Phase 3C-3a；其餘見 ``content/skill_triggers.yaml``）。"""


SKILL_REACTION_EVENTS: tuple[str, ...] = (
    "hit_by_melee",
    "hit_by_attack",
    "ally_hit_adjacent",
    "enemy_leaves_adjacent",
    "hit_by_spell",
    "ally_downed",
    "enemy_enters_adjacent",
    "ally_targeted",
)
"""反應技（``kind: reaction``）的觸發事件（Phase 2E-2 4.1；後四個是 Phase 3D-3 新增）。"""


LEGACY_REACTION_EVENTS: tuple[str, ...] = SKILL_REACTION_EVENTS[:4]
"""Phase 2E-2 的四個觸發事件。隨機組合器只從這些抽（3D-3 的新事件只給手寫技能，組合器的亂數
串流與既有種子的結果因此不變）。"""


INTERCEPT = "intercept"
"""替隊友擋攻擊的原語 ID（只能出現在 ``event: ally_hit_adjacent`` 的反應技）。"""


ADD_STACK = "add_stack"


CONSUME_STACK = "consume_stack"


CONSUME_STATUS = "consume_status"


CONSUME_THEN_TYPES = ("damage", "heal", "shield", "apply_status")
"""``consume_status`` 的 ``then`` 可用的原語（Phase 3C-3b）。"""


PLACE_TRAP = "place_trap"
"""Phase 2E-3 的原語 ID：累積層數、消耗層數、放置陷阱。"""


GRANT_AP = "grant_ap"


RESET_COOLDOWN = "reset_cooldown"


CHEAT_DEATH = "cheat_death"
"""Phase 3C-4a 的改寫規則型原語 ID（6.3；規則見 ``content/skill_primitives.yaml``）。"""


CHEAT_DEATH_STATUS = primitive_status("cheat_death")
"""``cheat_death`` 施加的狀態（``statuses.yaml``，``prevents_death``）。"""


REDIRECT_DAMAGE = "redirect_damage"


COPY_SKILL = "copy_skill"


EXTRA_REACTION = "extra_reaction"
"""Phase 3C-4b 的改寫規則型原語 ID。"""


RESTORE_RESOURCE = "restore_resource"


STEAL_BUFF = "steal_buff"
"""Phase 3D-1 的資源互動原語 ID（6.16 H）。"""


DISPEL = "dispel"


REVEAL = "reveal"
"""Phase 3D-8a 的原語 ID（6.18 J、I）：驅散敵方增益、揭露隱蔽與陷阱。"""


GRANT_SKILL = "grant_skill"


MAX_GRANT_DURATION = 4
"""Phase 3D-8c 的暫時獲得技能原語 ID（6.20）：目標的技能列暫時多出 ``skill``，``duration`` 輪後
（在目標自己的回合結束時倒數）消失。持續輪數上限。"""


REVIVE = "revive"


DELAYED_DAMAGE = "delayed_damage"


TIME_BOMB = primitive_status("delayed_damage")
"""Phase 3D-8b 的原語 ID（6.18 C、H）：復活倒下的友方、在目標身上附加定時炸彈（狀態 ``time_bomb``，
``statuses.yaml``；倒數與爆炸見 ``trpg.engine.bombs``）。"""


REFUND_AP = "refund_ap"


REFUND_COOLDOWN = "refund_cooldown"


ON_KILL_TYPES: tuple[str, ...] = (REFUND_AP, REFUND_COOLDOWN, "heal", "shield", "apply_status")
"""技能內的擊殺時效果（``on_kill``，Phase 3D-8b，6.18 F）可用的效果類型：``refund_ap``（返還 AP）與
``refund_cooldown``（本技能冷卻歸零）是只能放在 ``on_kill`` 裡的專用效果（不是
``skill_primitives.yaml`` 的原語，也不屬於改寫規則型）；其餘依一般原語結算，對象一律是施放者。"""


MAX_ON_KILL_EFFECTS = 2


MAX_REFUND_AP = 2
"""``on_kill`` 的效果個數上限，與 ``refund_ap`` 一次最多返還的 AP。"""


SPLIT_SKELETONS: tuple[str, ...] = split_heal_skeletons()
"""``split_heal``（聖光雙效）可以使用的骨架。"""


DASH = "dash"


LEAP = "leap"


SWAP = "swap"
"""Phase 3D-2 的自身位移原語 ID（6.16 A）。"""


SHADOWSTEP = "shadowstep"
"""Phase 3D-8d 的瞬步原語 ID（6.21）：以敵方單位為目標，瞬間出現在他相鄰的格子；``landing:
choose`` 搭配形狀 ``unit_then_tile``、``landing: behind`` 搭配形狀 ``single``。"""


SHADOWSTEP_SHAPES: dict[str, str] = {"choose": "unit_then_tile", "behind": "single"}


TELEPORT_TARGET = "teleport_target"


SWAP_ANY = "swap_any"
"""Phase 3D-2b 的位移他人原語 ID（6.19）：傳送他人（形狀 ``unit_then_tile``）、任意兩者互換
（形狀 ``unit_pair``）。"""


PAIR_MOVES: tuple[str, ...] = (TELEPORT_TARGET, SWAP_ANY)


PAIR_SHAPES: dict[str, str] = {TELEPORT_TARGET: "unit_then_tile", SWAP_ANY: "unit_pair"}


SHAPE_REQUIRED_PRIMITIVES: dict[str, tuple[str, ...]] = {
    "unit_then_tile": (TELEPORT_TARGET, SHADOWSTEP),
    "unit_pair": (SWAP_ANY,),
    "object_then_tile": ("hurl_object",),
}
"""形狀這一側的組合規則（Phase 4-L5b 整理；驗證見 ``SkillDef._check_pair_moves``、
``_check_hurl_object``）：這些形狀必須搭配其中一個原語（``shadowstep`` 要 ``landing: choose``）。
LLM 提議模型的一般型態不開放這些形狀。"""


CHARGE_THROUGH = "charge_through"
"""Phase 3D-2c 的直線衝撞原語 ID（6.22）：形狀 ``ground_tile`` 選終點格，沿直線衝過去。"""


ENTER_FORM = "enter_form"
"""Phase 3J-1a 的進入形態原語 ID（6.30）：姿態（``kind: stance``）唯一的效果，參數 ``form``。"""


LEAVE_FORM = "leave_form"
"""Phase 3J-4c 的解除形態原語 ID（6.30 解形爆發）：主動技能的第一個效果，施放者先解除目前的形態
（照常冷卻），之後的效果照一般順序結算；不在形態中不能施放。"""


SUMMON = "summon"


MAX_SUMMON_COUNT = 2
"""一次召喚的數量上限（Phase 3-33f2，數量型分歧進化：2 隻各 ``power_permille``）。"""
"""Phase 3D-4a 的召喚原語 ID（6.16 B）：在 ``ground_tile`` 選的空格召喚 ``unit`` 範本。"""


RULE_CHANGE = "rule_change"
"""規則改變（Phase 3D-6）：引用 ``content/rule_changes.yaml`` 的一條規則，以 ``activation``
啟動。"""


INSCRIBE = "inscribe"
"""Phase 3-23 的刻印原語 ID（6.25）：在影響格留下施放者專屬的符文（``element`` 或 ``tag``）。"""


DETONATE_RUNES = "detonate_runes"
"""Phase 3-23 的消耗型原語 ID（6.25）：引爆影響格內施放者自己的符文，每格對該格單位一次小傷害。"""


RUNE_BOTH_MESSAGE = "不能同時刻下符文又引爆符文（要靠兩件東西搭配，不是單一被動或單一裝備自己完成）"


BLOW_SURFACE = "blow_surface"
"""Phase 3-54a 的吹送原語 ID（06 6.33，#56）：把影響格上的表面整片往風向平移 ``distance`` 格。"""


SACRIFICE_SUMMON = "sacrifice_summon"
"""Phase 3-24c 的獻祭召喚物原語 ID（6.27.2）：移除自己的一個召喚物，在它的位置爆炸或治療。"""


ZONE = "zone"
"""Phase 3D-5 的持續區域原語 ID（6.16 G）：在格子上建立持續 ``duration`` 輪的區域。"""


ZONE_EFFECT_TYPES: tuple[str, ...] = ("damage", "heal", "shield", "apply_status")
"""``zone`` 的 ``effects`` 可用的原語（Phase 3D-5；與 ``consume_status`` 的 ``then`` 相同）。"""


ZONE_MOVING_SHAPES: tuple[str, ...] = shape_role("zone_moving")
"""``anchor: moving`` 可用的形狀（選方向的形狀；區域沿施放方向前進）。"""


ZONE_CASTER_SHAPES: tuple[str, ...] = shape_role("zone_caster")
"""``anchor: caster`` 可用的形狀（以施放者為中心、不需要選取的形狀；跟著施放者重新展開）。"""


_ZONE_ONLY_FIELDS = ("anchor", "when", "speed", "effects")


GAMBLE = "gamble"


GAMBLE_TAG = "gamble"
"""帶賭博機制的技能自動加上的標籤。"""


DAMAGE_MULTIPLIER = "damage_multiplier"


SELF_DAMAGE_OF_HIT = "self_damage_of_hit"
"""Phase 3D-7a 的賭博型原語（6.17 A）：``gamble``（賭注：成敗兩個分支）；``damage_multiplier``
（本次傷害 × 倍率）與 ``self_damage_of_hit``（施放者受本次傷害的 n‰）只能出現在賭注的分支裡，
不是 ``skill_primitives.yaml`` 的原語。"""


GAMBLE_BRANCH_TYPES: tuple[str, ...] = (
    "damage",
    "heal",
    "shield",
    "apply_status",
    DAMAGE_MULTIPLIER,
    SELF_DAMAGE_OF_HIT,
)
"""賭注分支（``win``／``lose``）可用的效果類型。"""


BACKLASH_TYPES: tuple[str, ...] = ("damage", "apply_status")
"""失手反噬（``cost.on_miss``）可用的效果類型。"""


_MAX_BRANCH_EFFECTS = 2


_GAMBLE_ONLY_FIELDS = ("chance_permille", "win", "lose")


_MAX_ZONE_EFFECTS = 2


SELF_MOVES: tuple[str, ...] = (DASH, LEAP, SWAP, CHARGE_THROUGH, SHADOWSTEP, "teleport")
"""改變施放者位置的原語；一個技能最多一個。"""


COMPOSITE_MOVES: tuple[str, ...] = ("teleport", LEAP, DASH, CHARGE_THROUGH, SHADOWSTEP)
"""複合技能（Phase 3F-3a，6.23 基本型「位移 → 動作」）的位移段可用的施放者自身位移原語。"""


FOLLOWUP_SHAPES: tuple[str, ...] = shape_role("followup")
"""複合技能動作段可用的形狀（Phase 3F-3a）：以落點為原點；``cross``、``square3`` 必須 ``range: 0``
（以落點為中心）。"""


FOLLOWUP_CENTERED: tuple[str, ...] = ("cross", "square3")


FOLLOWUP_FORBIDDEN: tuple[str, ...] = (
    *SELF_MOVES,
    TELEPORT_TARGET,
    SWAP_ANY,
    SUMMON,
    ZONE,
    PLACE_TRAP,
    COPY_SKILL,
    RULE_CHANGE,
    GAMBLE,
    "hurl_object",
)
"""動作段不能用的原語（Phase 3F-3a）：位移（不套娃）、召喚、持續區域、陷阱，以及需要另外選取或改變
整個施放流程的原語（複製技能、規則改變、賭注、投擲物件；保守做法）。"""


type FollowupWhen = Literal[
    "after_move", "after_action", "after_gather", "on_kill", "on_hit", "delayed"
]
"""第二段的時機（6.23）：``after_move`` 位移 → 動作（3F-3a）；``after_action`` 動作 → 位移
（打帶跑）、``after_gather`` 聚集 → 範圍打擊、``on_kill`` 擊殺 → 接下一段、``on_hit`` 命中 →
加碼段（3F-4a）；``delayed`` 延遲段（3F-4b）。"""


type DelayedRelease = Literal["next_turn", "attacked"]
"""延遲段的釋放時機（Phase 3F-4b）：``next_turn`` 施放者下回合開始時；``attacked`` 到施放者下回合
開始之前被敵人攻擊（擲命中，不論是否命中）時——沒被攻擊就在下回合開始時失效。"""


FOLLOWUP_WHEN_VALUES: tuple[str, ...] = (
    "after_move",
    "after_action",
    "after_gather",
    "on_kill",
    "on_hit",
    "delayed",
)


DELAYED_RELEASE_VALUES: tuple[str, ...] = ("next_turn", "attacked")


DELAYED_SHAPES: tuple[str, ...] = ("cross", "square3", "ring")
"""延遲段的形狀（Phase 3F-4b）：以施放者釋放當下的位置為中心（十字、方陣 ``range: 0``）。"""


CHARGING = mechanic_status("charging")
"""延遲段等待期間施放者身上的狀態（Phase 3F-4b；``StatusInstance.skill_id`` 是技能、
``remaining`` 是還要幾回合釋放）。"""


FOLLOWUP_CHOICE_WHENS: tuple[str, ...] = ("after_action", "on_kill")
"""第二段要施放者自己選目標的種類（3F-4a）：結算到第二段時以 ``pending``（``kind: followup``）
詢問；AI 與重播直接在 ``UseSkill.followup_target`` 帶選取。"""


FOLLOWUP_AUTO_WHENS: tuple[str, ...] = ("after_gather", "on_hit")
"""第二段的選取由引擎決定的種類（3F-4a）：聚集點、命中的同一個目標；不能帶 ``followup_target``。"""


COMPOSITE_KIND_ZH: dict[str, str] = {
    "after_move": "位移 → 動作",
    "after_action": "動作 → 位移",
    "after_gather": "聚集 → 範圍打擊",
    "on_kill": "擊殺 → 接下一段",
    "on_hit": "命中 → 加碼段",
    "delayed": "延遲段",
}
"""複合技能種類的中文名稱（6.23）。"""


GATHER_SHAPES: tuple[str, ...] = ("cross", "square3", "ring")
"""聚集段（``after_gather`` 的第一段）的形狀：十字、方陣以選的中心格為聚集點，環形以施放者
為聚集點。"""


ON_KILL_SECOND_SHAPES: tuple[str, ...] = shape_role("on_kill_second")
"""``on_kill`` 第二段的形狀：動作段的形狀，加上跳躍、傳送用的指定格。"""


_MAX_COOLDOWN_RESTORE = 2
"""``restore_resource`` 的 ``resource: cooldown`` 一次最多縮短的回合（Phase 3D-1）。"""


HURL_OBJECT = "hurl_object"


TOPPLE = "topple"
"""Phase 3C-5a 的物件原語 ID（6.15）：投擲物件、推倒。"""


PIERCE_SHAPES: tuple[str, ...] = shape_role("pierce")
"""可以穿透（``pierce``，Phase 3C-5b）的形狀：遠程單體與直線。"""


REDIRECT_STATUS = primitive_status("redirect_damage")
"""``redirect_damage`` 施加的狀態（``statuses.yaml``，``redirects_damage``）：
``StatusInstance.amount`` 存轉移的千分比、``source_id`` 是承受轉移的施放者。"""


# ---------------------------------------------------------------------------
# 修正規則（Phase 3C-2：修正型被動與改造型技能，``docs/design/06-技能.md`` 6.14.1、6.14.3）
# ---------------------------------------------------------------------------

type BasicAction = Literal["attack", "shove", "trip", "interact"]
"""可以被修正的基本動作：普攻（含藉機攻擊）、推擊、絆倒、互動（推或撥開物件）。"""


BASIC_ACTIONS: tuple[str, ...] = ("attack", "shove", "trip", "interact")


_CHANGES = bundled_modifier_changes()
"""修正規則的改變種類（``content/modifier_changes.yaml``，Phase 3T-1；唯一來源）。"""


MODIFIER_CHANGES: tuple[str, ...] = _CHANGES.ids
"""``change`` 的種類（每條規則恰好一種；依 YAML 順序）。"""


SHAPE_CHANGES: frozenset[str] = frozenset(c.id for c in _CHANGES.changes if c.reshapes)
"""讓技能變形的修正（Phase 3D-3；YAML 的 ``reshapes``）：選目標之前就決定，只套用在主動技能；
引擎以 :func:`trpg.engine.modifiers.shaped_skill` 產生變形後的技能。"""


CHANGE_TARGETS: dict[str, frozenset[str]] = {
    c.id: frozenset(c.applies_to) for c in _CHANGES.changes
}
"""每種 ``change`` 可以套用的對象（YAML 的 ``applies_to``；``applies_to`` 的每一項都必須在內）：
推擊、絆倒、互動沒有傷害與命中骰，基本動作沒有冷卻與標籤。"""


SELF_ONLY_CHANGES: frozenset[str] = frozenset(c.id for c in _CHANGES.changes if c.self_only)
"""在選目標之前就要決定的修正（YAML 的 ``self_only``）：條件只能看持有者自己
（``self_hp_below``）或省略。"""


NONZERO_CHANGES: frozenset[str] = frozenset(c.id for c in _CHANGES.changes if c.nonzero)
"""數值不可為 0 的 ``change`` 種類（YAML 的 ``nonzero``）。"""


TRUE_ONLY_CHANGES: frozenset[str] = frozenset(c.id for c in _CHANGES.changes if c.true_only)
"""只能是 ``true`` 的 ``change`` 種類（YAML 的 ``true_only``）。"""


WIELDING_WEAPON = "wielding_weapon"
"""武器親和條件（Phase 3I-5）。"""


WIELDING_EFFECT_ONLY = (
    "「手持某種武器時」只能寫在效果上（沒拿那種武器時技能照常可用，只是少那個加成）；"
    "想限定武器才能用，請改用限定武器"
)
"""``wielding_weapon`` 寫在技能條件上時的訊息（schema 與工坊事前停用共用）。"""


SELF_CONDITIONS: frozenset[str] = frozenset({"self_hp_below"})


CASTER_CONDITIONS: frozenset[str] = frozenset(
    {
        "self_hp_below",
        "moved_this_turn",
        "adjacent_ally",
        "first_round",
        "cast_tag_this_turn",
        "self_concealed",
        "wielding_weapon",
        "in_form",
    }
)
"""只看施放者的條件（Phase 3D-1；``wielding_weapon`` 為 3I-5）：技能層級的判斷不需要影響範圍內
有對象。選目標之前就要決定的修正規則改變（:data:`SELF_ONLY_CHANGES`）仍只允許
:data:`SELF_CONDITIONS`（``self_hp_below``）。"""


ON_HIT_PRIMITIVES: tuple[str, ...] = (
    "damage",
    "apply_status",
    "push",
    "pull",
    "knock_prone",
    "create_surface",
    "detonate_runes",
    "inscribe",
)
"""``on_hit_effects`` 可用的原語（作用在被命中的目標或其所在格，自動命中）。``detonate_runes``、
``inscribe``（Phase 3-31 普攻與符文）只作用在目標所在的那 1 格。"""


PER_TURN_LIMIT_CHANGES: frozenset[str] = frozenset(
    c.id for c in _CHANGES.changes if c.per_turn_limit
)
"""可以帶 ``per_turn_limit`` 的 ``change`` 種類（Phase 3-31；YAML 的 ``per_turn_limit``）。"""


_MAX_MODIFIERS = 2


_MAX_MASTERY_MODIFIERS = 4
"""專精（帶 ``exclusive_group`` 的修正型被動，3-33f1）可以有的規則數：效果與代價各幾條。"""


MAX_MODIFIERS = _MAX_MODIFIERS
"""修正技能的修正規則條數上限（Phase 3F-1 公開給技能工坊的選項推導）。"""


_MAX_CONSUME_THEN = 2


_MAX_ON_HIT_EFFECTS = 2


# ---------------------------------------------------------------------------
# 戰場變奏（Phase 3-25a，06 6.24）
# ---------------------------------------------------------------------------

MAX_VARIANTS = 2
"""一招技能最多的變奏數（實際上限再依稀有度，見 ``core.yaml`` 的 ``variant_max_by_rarity``）。"""


VARIANT_CONDITIONS: tuple[str, ...] = (
    "caster_surface",
    "caster_high_ground",
    "caster_adjacent_blocker",
    "target_surface",
)
"""變奏條件的四種（PM 決定 #2）。"""


VARIANT_TARGET_CONDITIONS: tuple[str, ...] = ("caster_high_ground", "target_surface")
"""依賴目標點的條件：同一招對不同的目標點可能選出不同的型態（PM 決定 #4）。"""


_MAX_VARIANT_REPLACEMENTS = 2


_VARIANT_REPLACEMENTS = ("shape", "range_delta", "element", "add_effect", "replace_effect")


type Activation = Literal["timed", "battle"]
"""常駐類傳說的啟動方式（Phase 3D-6，6.14.4）：``timed`` 持續 ``legendary_timed_rounds`` 輪、
``battle`` 本場剩餘時間有效（預算較低）。"""


type Mastery = Literal["range", "duration"]
"""專精加成的種類（Phase 2H-2）。"""


_ELEMENT_VALUES = frozenset(e.value for e in Element)


_REQ_NAMES = {"melee": "近戰武器", "ranged": "遠程武器", "focus": "法器", "any": "任何武器"}


_GROUP_NAMES = {"mastery": "專精（普攻精通、群召、精英召喚、化形專精）"}
