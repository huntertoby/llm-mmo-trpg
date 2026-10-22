"""依陣營過濾的戰場視圖（Phase 3-1）：把 :class:`~trpg.engine.state.BattleState` 轉成可以交給
某一方玩家的 pydantic 模型，之後直接當 API 回應。

- **不包含**：``rng_state``、``seed``、暫停結算的內部欄位（``base_state_json``、``action_json``、
  ``decisions``、``events_emitted``）、其他陣營的陷阱、``ruleset`` 本體。
- 陷阱一律經過 :func:`trpg.engine.traps.visible_traps`（唯一的陷阱可見性邏輯）。
- 確定性：相同狀態與陣營 → 相同 JSON（單位、物件、陷阱、層數、冷卻都排序；先攻順序保留原順序）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from trpg.content.battle import ReactionRule
from trpg.content.equipment import (
    AFFIX_CATEGORY_NUMBER,
    AFFIX_CATEGORY_ZH,
    ActionAffix,
    ChargeAffix,
    ReactionAffix,
    affix_text,
)
from trpg.content.maps import Objective
from trpg.content.skills import CHARGING, TIME_BOMB
from trpg.content.slots import SLOT_ZH
from trpg.engine.bombs import bomb_spec
from trpg.engine.delayed import charge_infos
from trpg.engine.gear_state import GearAffix, GearState
from trpg.engine.gear_view import GearTotalView, gear_totals
from trpg.engine.skills.revive import revivable
from trpg.engine.state import (
    Activation,
    BattleState,
    Facing,
    PendingResolution,
    StatusInstance,
    UnitState,
    reaction_limit,
)
from trpg.engine.summons import totem_of
from trpg.engine.traps import visible_traps
from trpg.engine.zones import next_zone_cells, zone_cells, zone_is_harmful, zone_spec
from trpg.shared.types import Element, Pos, Surface, Team, UnitId, rune_name

__all__ = [
    "REACTION_TRIGGER_TEXT",
    "ActivationView",
    "AffixLineView",
    "AppearanceView",
    "BattleView",
    "ChargeView",
    "EquipmentSlotView",
    "GearSkillView",
    "GearTotalView",
    "GrantedSkillView",
    "ObjectView",
    "PendingView",
    "ReactionRuleView",
    "RuneView",
    "StatusView",
    "TileView",
    "TrapView",
    "UnitView",
    "ZoneView",
    "project_for",
]


class _ViewModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TileView(_ViewModel):
    x: int
    y: int
    height: int
    terrain: str
    surface: Surface
    surface_remaining: int | None
    surface_team: Team | None
    object_id: str | None
    surface_creator: UnitId | None


class ObjectView(_ViewModel):
    id: str
    kind: str
    pos: Pos
    hp: int | None
    max_hp: int | None
    burning: int | None
    expires_in: int | None = None
    """暫時障礙（Phase 3-11）還剩幾次環境回合；永久為 ``None``。"""


class StatusView(_ViewModel):
    status_id: str
    remaining: int | None
    source_id: UnitId | None
    amount: int | None
    blast_radius: int | None = None
    """定時炸彈（``time_bomb``，Phase 3D-8b）的爆炸半徑（曼哈頓距離）；其他狀態為 ``None``。"""
    skill_id: str | None = None
    """延遲段（``charging``，Phase 3F-4b）的技能；其他狀態為 ``None``。"""
    release: str | None = None
    """延遲段的釋放時機（``next_turn``／``attacked``）；其他狀態為 ``None``。"""
    charge_tiles: tuple[Pos, ...] = ()
    """延遲段以帶有者目前位置推算的預計範圍；其他狀態為空。"""


REACTION_TRIGGER_TEXT: dict[str, str] = {
    "targeted_by_melee": "被近戰攻擊命中時",
    "targeted_by_attack": "被攻擊命中時",
    "enemy_leaves_adjacent": "敵人離開相鄰格時",
    "hit_by_melee": "被近戰攻擊命中後",
    "hit_by_attack": "被攻擊命中後",
    "ally_hit_adjacent": "相鄰友方被攻擊命中時",
    "hit_by_spell": "被法術命中時（傷害之前）",
    "ally_downed": "視野內的友方倒下後",
    "enemy_enters_adjacent": "敵人進入相鄰格後",
    "enemy_moves_in_range": "敵人在射程與視線內移動一步後",
    "ally_hit_in_range": "範圍內的友方被攻擊命中時（傷害之前）",
    "ally_targeted": "相鄰友方被敵人瞄準時（命中之前）",
}
"""反應規則觸發事件的中文說明（``ReactionWhen.event`` → 文字）。"""


class ReactionRuleView(_ViewModel):
    """單位身上的一條反應規則（玩家可以用 ``set_reaction_mode`` 切換 ``mode``）。"""

    reaction: str
    name_zh: str
    description_zh: str
    event: str
    trigger_zh: str
    mode: Literal["auto", "prompt", "off"]
    unless_stamina_below: int | None
    stamina_cost: int
    mana_cost: int
    hp_cost_permille: int
    gear_source_zh: str = ""
    """來自裝備的說明（Phase 3G-G3b）：授予或擴充這條反應的物品與詞條（「物品名：詞條文字」，多條用
    「；」分隔）；不是裝備來的為空字串。"""


class ActivationView(_ViewModel):
    """生效中的常駐類傳說（Phase 3D-6；雙方都看得到）。

    ``expires_round``：限時型在持有者第 ``expires_round`` 輪的回合開始時結束（剩餘輪數 ＝
    ``expires_round − round``）；整場型為 ``None``。``rule_name_zh``：規則改變的名稱（修正型為
    ``None``）。"""

    skill_id: str
    name_zh: str
    activation: Literal["timed", "battle"]
    expires_round: int | None
    rule_name_zh: str | None


class GrantedSkillView(_ViewModel):
    """暫時獲得的技能（Phase 3D-8c，``grant_skill``）：技能與剩餘輪數（在持有者每個回合結束時 −1，
    歸零消失）。只有自己陣營的單位會列出。"""

    skill_id: str
    name_zh: str
    remaining: int


class GearSkillView(_ViewModel):
    """裝備授予的常駐技能（Phase 3G-G3b，第 9 類；唯讀）：技能來自哪個欄位的哪件物品與詞條。
    技能本身也在 ``UnitView.skills`` 裡，卸下裝備（戰鬥開始前不穿那件物品）就沒有。"""

    skill_id: str
    name_zh: str
    affix_id: str
    slot: str
    slot_zh: str
    item_name_zh: str


class AffixLineView(_ViewModel):
    """裝備上的一條詞條（Phase 3G-G1，唯讀）。``active``：遞減後仍生效（非數值類同 id 只生效 1 條；
    數值類第 4 條起權重 0）；``weight_permille``：遞減權重（1000／500／250／0）。

    ``duplicate_of``（Phase 3-32a）：這條 **沒有生效** 的重複詞條，是和哪一條重複（生效的那條的
    「部位＋詞條文字」，例如「主手的每第 2 次普攻命中：…」）；生效中的詞條為 ``None``。"""

    affix_id: str
    category: str
    category_zh: str
    text_zh: str
    active: bool
    weight_permille: int
    duplicate_of: str | None = None


class AppearanceView(_ViewModel):
    """物品外觀（Phase 3G-G5a，只給圖示用）：欄位同 ``content/equipment/appearance.yaml``；
    物品沒寫的欄位為 ``None``（前端依欄位退回預設）；``keywords`` 由詞條推導（前 2 個）；
    ``rarity`` 沒寫時傳說物品為 ``legendary``、其餘 ``common``。"""

    kind: str | None = None
    form: str | None = None
    material: str | None = None
    dye: str | None = None
    style: str | None = None
    rarity: str = "common"
    keywords: tuple[str, ...] = ()


class EquipmentSlotView(_ViewModel):
    """一個裝備欄位（Phase 3G-G1，唯讀）：欄位、物品名與詞條文字。"""

    slot: str
    slot_zh: str
    item_id: str
    name_zh: str
    affixes: tuple[AffixLineView, ...] = ()
    appearance: AppearanceView = AppearanceView()


class ChargeView(_ViewModel):
    """裝備上的一條充能詞條（Phase 3G-G3a，唯讀）：層數、啟動需求與目前能不能啟動。

    ``stacks``／``max_stacks``：目前層數與裝備版上限；``cost_stacks``／``cost_ap``：啟動花費；
    ``needs_target``：啟動要選一個敵方目標（否則作用在自己）；``ready``：層數足夠（AP 與目標
    另外看 ``legal_actions``）。
    """

    affix_id: str
    name_zh: str
    stack_id: str
    stack_name_zh: str
    stacks: int
    max_stacks: int
    cost_stacks: int
    cost_ap: int
    needs_target: bool
    ready: bool


class UnitView(_ViewModel):
    id: UnitId
    template_id: str
    name_zh: str
    team: Team
    pos: Pos
    hp: int
    max_hp: int
    shield: int
    """護盾的剩餘吸收量（所有吸收傷害的狀態加總）。"""
    mana: int
    max_mana: int
    stamina: int
    max_stamina: int
    ap: int
    move_points: int
    speed: int
    initiative: int
    weapon_name_zh: str
    weapon_id: str = ""
    """武器 ID（Phase 3-16b，紙娃娃主手外觀用）；未知武器由前端退回預設。"""
    weapon_class: str = ""
    """武器大類（Phase 3-18b）：melee、ranged、focus；不認得 weapon_id 時前端依此退回。"""
    weapon_traits_zh: tuple[str, ...] = ()
    """武器小特性的說明，每個特性一行（Phase 3-24a1；取自武器資料的參數）。"""
    ammo: int = 0
    """彈匣裡的子彈數（Phase 3-24a2；HUD 顯示用，沒有彈匣的武器為 0）。"""
    magazine: int = 0
    """彈匣容量（武器的 ``magazine``；0 ＝ 沒有彈匣，不顯示）。"""
    tags: tuple[str, ...]
    skills: tuple[str, ...]
    """裝備的技能 ID；只有自己陣營的單位會列出（其他陣營的單位為空，避免洩漏陷阱技能）。"""
    skill_levels: dict[str, int] = {}
    """技能等級（Phase 3-26a；只列出 2 級以上的，技能列顯示「Lv.N」；只有自己陣營的單位會列出）。"""
    statuses: tuple[StatusView, ...]
    stacks: dict[str, int]
    cooldowns: dict[str, int]
    """冷卻中的技能；其他陣營單位的陷阱技能冷卻不列出。"""
    reaction_available: bool
    """還有反應次數，且身上有（未關閉的）反應規則。"""
    reaction_rules: tuple[ReactionRuleView, ...]
    """反應規則與目前模式；只有自己陣營的單位會列出（其他陣營的單位為空）。"""
    ap_carry: int
    """結束回合時保留、下回合開始時加上的 AP（自己的回合中為 0，已併入 ``ap``）。"""
    source: int
    """源力（Phase 3C-4a；傳說技能的代價，敵人一律 0）。"""
    source_max: int
    """源力上限（``core.yaml`` 的 ``source_max``）。"""
    downed: bool
    revivable: bool = False
    """倒下而且可以被復活（Phase 3D-8b）：不是撤離或消失、不是召喚物、本場還沒被復活過。"""
    escaped: bool
    owner_id: UnitId | None
    """召喚物的召喚者（Phase 3D-4a）；一般單位為 ``None``。"""
    summon_expires_round: int | None
    """召喚物在召喚者這一輪的回合結束時消失（Phase 3D-4a）；一般單位為 ``None``。"""
    dismissed: bool
    """召喚物已消失（Phase 3D-4a）：不在戰場上，保留在清單中讓紀錄能查名字。"""
    totem_radius: int | None
    """圖騰（Phase 3D-4b）：光環半徑（回合開始時給範圍內友方狀態）；不是圖騰為 ``None``。"""
    activations: tuple[ActivationView, ...] = ()
    """生效中的常駐類傳說（Phase 3D-6），依啟動順序。"""
    granted_skills: tuple[GrantedSkillView, ...] = ()
    """暫時獲得的技能與剩餘輪數（Phase 3D-8c；不佔 ``skills`` 的欄位，依獲得順序；只有自己陣營的
    單位會列出）。"""
    facing: Facing = "east"
    """朝向（Phase 3D-8d；north／east／south／west）。背後格 ＝ 位置 ＋ 朝向的反方向；站在那裡的
    近戰攻擊者有背刺加成。"""
    equipment: tuple[EquipmentSlotView, ...] = ()
    """裝備摘要（Phase 3G-G1，唯讀；依欄位固定順序，沒有裝備時為空）。"""
    gear_totals: tuple[GearTotalView, ...] = ()
    """裝備加成的來源（Phase 3G-G4，唯讀）：實際值（遞減、截斷後）與每條詞條的貢獻。"""
    gear_skills: tuple[GearSkillView, ...] = ()
    """裝備授予的常駐技能（Phase 3G-G3b，唯讀；只有自己陣營的單位會列出，依欄位固定順序）。"""
    charges: tuple[ChargeView, ...] = ()
    """裝備的充能詞條（Phase 3G-G3a，唯讀；依詞條 ID，沒有時為空）：層數與啟動需求。"""


class TrapView(_ViewModel):
    owner_id: UnitId
    team: Team
    pos: Pos
    skill_id: str
    remaining: int


class ZoneView(_ViewModel):
    """持續區域（Phase 3D-5；雙方都看得到）。

    - ``cells``：目前的格子（跟隨型以施放者目前的位置展開）。
    - ``next_cells``：移動型區域在本輪環境回合之後的格子（只看幾何的預告；不移動或在那之前就
      消失的區域為 ``None``，空串列表示全部會撞上牆壁而消失）。
    - ``expires_round``：施放者在這一輪的回合結束時區域消失。
    - ``harmful``：效果含傷害或有害狀態（網頁用來決定顏色）。
    """

    id: int
    owner_id: UnitId
    team: Team
    skill_id: str
    name_zh: str
    anchor: Literal["tile", "caster", "moving"]
    affects: Literal["enemies", "allies", "all"]
    when: Literal["enter", "turn_start", "both"]
    cells: tuple[Pos, ...]
    direction: str | None
    """移動型區域的方向（``north``／``east``／``south``／``west``）。"""
    speed: int
    expires_round: int
    harmful: bool
    next_cells: tuple[Pos, ...] | None


class RuneView(_ViewModel):
    """格子上的符文（Phase 3-23 ``inscribe``；雙方都看得到，但只有 ``owner_id`` 自己讀得到）。

    ``element``／``tag``：恰好一個；``name_zh`` 例如「雷紋」；``remaining``：剩餘的環境回合數。
    """

    id: int
    owner_id: UnitId
    team: Team
    pos: Pos
    element: Element | None
    tag: str | None
    name_zh: str
    remaining: int


class PendingView(_ViewModel):
    """目前的反應詢問（只有公開欄位；內部的重播資料不外流）。"""

    kind: str
    unit_id: UnitId
    reaction: str
    trigger_unit_id: UnitId | None
    skill_id: str | None
    copy_skill_id: str | None
    trigger_event_seq: int | None
    stamina_cost: int
    mana_cost: int
    hp_cost_permille: int


class BattleView(_ViewModel):
    """``team`` 視角的戰場。"""

    team: Team
    map_id: str
    map_name_zh: str
    width: int
    height: int
    tiles: tuple[TileView, ...]
    """列優先（先 y 後 x）。"""
    objects: tuple[ObjectView, ...]
    units: tuple[UnitView, ...]
    traps: tuple[TrapView, ...]
    """只有 ``team`` 看得見的陷阱（自己陣營放置的）。"""
    turn_order: tuple[UnitId, ...]
    active_unit: UnitId | None
    round: int
    max_rounds: int | None
    weather_id: str | None
    weather_name_zh: str | None
    objective: Objective
    ended: bool
    winner: Team | None
    end_reason: str | None
    pending: PendingView | None
    source_wells: tuple[Pos, ...]
    """尚未被取用的源泉格（Phase 3C-4a；我方單位進入時 +1 源力，之後消失；雙方都看得到）。"""
    zones: tuple[ZoneView, ...] = ()
    """持續區域（Phase 3D-5），依編號排序；雙方都看得到。"""
    runes: tuple[RuneView, ...] = ()
    """格子上的符文（Phase 3-23），依編號排序；雙方都看得到。"""


def _pos(cells: tuple[tuple[int, int], ...]) -> tuple[Pos, ...]:
    return tuple(Pos(x=x, y=y) for x, y in cells)


def _zone_views(state: BattleState) -> tuple[ZoneView, ...]:
    views: list[ZoneView] = []
    for zone in state.zones:
        spec = zone_spec(state, zone)
        assert spec.affects in ("enemies", "allies", "all") and spec.when is not None
        upcoming = next_zone_cells(state, zone)
        views.append(
            ZoneView(
                id=zone.id,
                owner_id=zone.owner_id,
                team=zone.team,
                skill_id=zone.skill_id,
                name_zh=state.ruleset.skill_def(zone.skill_id).name_zh,
                anchor=zone.anchor,
                affects=spec.affects,
                when=spec.when,
                cells=_pos(zone_cells(state, zone)),
                direction=zone.direction,
                speed=zone.speed,
                expires_round=zone.expires_round,
                harmful=zone_is_harmful(state, spec),
                next_cells=None if upcoming is None else _pos(upcoming),
            )
        )
    return tuple(views)


def _rune_views(state: BattleState) -> tuple[RuneView, ...]:
    return tuple(
        RuneView(
            id=r.id,
            owner_id=r.owner_id,
            team=r.team,
            pos=r.pos,
            element=r.element,
            tag=r.tag,
            name_zh=rune_name(r.element, r.tag),
            remaining=r.remaining,
        )
        for r in state.runes
    )


def _status_view(state: BattleState, unit: UnitState, status: StatusInstance) -> StatusView:
    radius = None
    if status.status_id == TIME_BOMB and status.skill_id is not None:
        radius = bomb_spec(state, status.skill_id).radius
    charge = None
    if status.status_id == CHARGING:
        charge = next((c for c in charge_infos(state) if c.unit_id == unit.id), None)
    return StatusView(
        status_id=status.status_id,
        remaining=status.remaining,
        source_id=status.source_id,
        amount=status.amount,
        blast_radius=radius,
        skill_id=None if charge is None else charge.skill_id,
        release=None if charge is None else charge.release,
        charge_tiles=() if charge is None else charge.tiles,
    )


def _visible_cooldowns(state: BattleState, unit: UnitState, team: Team) -> dict[str, int]:
    """冷卻中的技能；其他陣營看不到陷阱技能的冷卻（否則會洩漏「剛放過陷阱」）。"""
    cooldowns = sorted(unit.cooldowns.items())
    if unit.team is not team:
        cooldowns = [(s, n) for s, n in cooldowns if state.ruleset.skill_def(s).trap is None]
    return dict(cooldowns)


def _rule_view(state: BattleState, unit: UnitState, rule: ReactionRule) -> ReactionRuleView:
    rules = state.ruleset
    if rule.reaction in unit.skills:  # 反應技：規則的 reaction 是技能 ID
        skill = rules.skill_def(rule.reaction)
        name, description = skill.name_zh, skill.narrative.concept
        stamina, mana, hp = 0, skill.cost.mana, skill.cost.hp_percent or 0
    else:
        definition = rules.reaction_def(rule.reaction)
        name, description = definition.name_zh, definition.description_zh
        stamina, mana, hp = definition.stamina_cost, 0, 0
    return ReactionRuleView(
        reaction=rule.reaction,
        name_zh=name,
        description_zh=description,
        event=rule.when.event,
        trigger_zh=REACTION_TRIGGER_TEXT[rule.when.event],
        mode=rule.mode,
        unless_stamina_below=None if rule.unless is None else rule.unless.self_stamina_below,
        stamina_cost=stamina,
        mana_cost=mana,
        hp_cost_permille=hp,
        gear_source_zh=_reaction_gear_source(unit, rule.reaction),
    )


def _duplicate_of(gear: GearState, entry: GearAffix) -> str | None:
    """沒有生效的重複詞條所重複的那一條（同 id、排第一的詞條）：「部位＋詞條文字」；生效中的詞條
    與找不到時 ``None``。"""
    if entry.active:
        return None
    winner = next((g for g in gear.affixes if g.affix.id == entry.affix.id and g.rank == 0), None)
    if winner is None or winner is entry:
        return None
    return f"{SLOT_ZH[winner.slot]}的{affix_text(winner.affix, winner.value)}"


def _equipment_view(unit: UnitState) -> tuple[EquipmentSlotView, ...]:
    """裝備摘要：每個欄位的物品與詞條（詞條依類別、id 排序）。"""
    gear = unit.gear
    if not gear.items:
        return ()
    views: list[EquipmentSlotView] = []
    for item in gear.items:
        lines = sorted(
            (a for a in gear.affixes if a.slot == item.slot),
            key=lambda a: (AFFIX_CATEGORY_NUMBER[a.affix.category], a.affix.id),
        )
        views.append(
            EquipmentSlotView(
                slot=item.slot,
                slot_zh=SLOT_ZH[item.slot],
                item_id=item.item_id,
                name_zh=item.name_zh,
                appearance=AppearanceView(
                    kind=item.kind or None,
                    form=item.form or None,
                    material=item.material or None,
                    dye=item.dye or None,
                    style=item.style or None,
                    rarity=item.rarity or "common",
                    keywords=item.keywords,
                ),
                affixes=tuple(
                    AffixLineView(
                        affix_id=a.affix.id,
                        category=a.affix.category,
                        category_zh=AFFIX_CATEGORY_ZH[a.affix.category],
                        text_zh=affix_text(a.affix, a.value),
                        active=a.active,
                        weight_permille=a.weight_permille,
                        duplicate_of=_duplicate_of(gear, a),
                    )
                    for a in lines
                ),
            )
        )
    return tuple(views)


def _gear_totals(state: BattleState, unit: UnitState) -> tuple[GearTotalView, ...]:
    caps = state.ruleset.equipment.caps
    return gear_totals(unit, damage_cap=caps.damage_bonus_permille, move_cap=caps.move_bonus)


def _charge_views(state: BattleState, unit: UnitState) -> tuple[ChargeView, ...]:
    """裝備的充能詞條摘要（生效中的，詞條 ID 排序）。"""
    views: list[ChargeView] = []
    for gear in unit.gear.active_affixes("charge"):
        affix = gear.affix
        assert isinstance(affix, ChargeAffix)
        stacks = unit.stacks.get(affix.stack, 0)
        views.append(
            ChargeView(
                affix_id=affix.id,
                name_zh=affix.name_zh,
                stack_id=affix.stack,
                stack_name_zh=state.ruleset.stack_def(affix.stack).name_zh,
                stacks=stacks,
                max_stacks=affix.max_stacks,
                cost_stacks=affix.cost_stacks,
                cost_ap=affix.cost_ap,
                needs_target=affix.effect_target == "target",
                ready=stacks >= affix.cost_stacks,
            )
        )
    return tuple(views)


def _gear_skill_views(state: BattleState, unit: UnitState) -> tuple[GearSkillView, ...]:
    """裝備授予的常駐技能（第 9 類，生效的詞條）：來源欄位與物品。"""
    names = {item.slot: item.name_zh for item in unit.gear.items}
    views: list[GearSkillView] = []
    for gear in unit.gear.active_affixes("action"):
        affix = gear.affix
        assert isinstance(affix, ActionAffix)
        views.append(
            GearSkillView(
                skill_id=affix.skill,
                name_zh=state.ruleset.skill_def(affix.skill).name_zh,
                affix_id=affix.id,
                slot=gear.slot,
                slot_zh=SLOT_ZH[gear.slot],
                item_name_zh=names.get(gear.slot, ""),
            )
        )
    return tuple(views)


def _reaction_gear_source(unit: UnitState, reaction: str) -> str:
    """授予或擴充 ``reaction`` 的裝備詞條（第 10 類）：「物品名：詞條文字」，多條用「；」分隔。"""
    names = {item.slot: item.name_zh for item in unit.gear.items}
    return "；".join(
        f"{names.get(gear.slot, '')}：{affix_text(gear.affix, gear.value)}"
        for gear in unit.gear.active_affixes("reaction")
        if isinstance(gear.affix, ReactionAffix) and gear.affix.reaction == reaction
    )


def _unit_view(state: BattleState, unit: UnitState, team: Team) -> UnitView:
    return UnitView(
        id=unit.id,
        template_id=unit.template_id,
        name_zh=unit.name_zh,
        team=unit.team,
        pos=unit.pos,
        hp=unit.hp,
        max_hp=unit.max_hp,
        shield=sum(s.amount for s in unit.statuses if s.amount is not None),
        mana=unit.mana,
        max_mana=unit.max_mana,
        stamina=unit.stamina,
        max_stamina=unit.max_stamina,
        ap=unit.ap,
        move_points=unit.move_points,
        speed=unit.speed,
        initiative=unit.initiative,
        weapon_name_zh=unit.weapon.name_zh,
        weapon_id=unit.weapon.id,
        weapon_class=unit.weapon.weapon_class,
        weapon_traits_zh=unit.weapon.trait_lines_zh(),
        ammo=unit.ammo,
        magazine=unit.weapon.magazine,
        tags=unit.tags,
        skills=unit.skills if unit.team is team else (),
        skill_levels=dict(sorted(unit.skill_levels.items())) if unit.team is team else {},
        statuses=tuple(_status_view(state, unit, s) for s in unit.statuses),
        stacks=dict(sorted(unit.stacks.items())),
        cooldowns=_visible_cooldowns(state, unit, team),
        reaction_available=unit.alive
        and any(r.mode != "off" for r in unit.reactions)
        and unit.reactions_used < reaction_limit(state.ruleset.core, unit),
        reaction_rules=(
            tuple(_rule_view(state, unit, r) for r in unit.reactions) if unit.team is team else ()
        ),
        ap_carry=unit.ap_carry,
        source=unit.source,
        source_max=state.ruleset.core.source_max,
        downed=unit.downed,
        revivable=revivable(unit),
        escaped=unit.escaped,
        owner_id=unit.owner_id,
        summon_expires_round=unit.summon_expires_round,
        dismissed=unit.dismissed,
        totem_radius=None if (totem := totem_of(state, unit)) is None else totem.radius,
        activations=tuple(_activation_view(state, a) for a in unit.activations),
        facing=unit.facing,
        equipment=_equipment_view(unit),
        gear_totals=_gear_totals(state, unit),
        charges=_charge_views(state, unit),
        gear_skills=_gear_skill_views(state, unit) if unit.team is team else (),
        granted_skills=(
            tuple(
                GrantedSkillView(
                    skill_id=g.skill_id,
                    name_zh=state.ruleset.skill_def(g.skill_id).name_zh,
                    remaining=g.remaining,
                )
                for g in unit.granted_skills
            )
            if unit.team is team
            else ()
        ),
    )


def _activation_view(state: BattleState, activation: Activation) -> ActivationView:
    skill = state.ruleset.skill_def(activation.skill_id)
    rule_id = skill.rule_change_id
    return ActivationView(
        skill_id=skill.id,
        name_zh=skill.name_zh,
        activation=skill.activation or "battle",
        expires_round=activation.expires_round,
        rule_name_zh=None if rule_id is None else state.ruleset.rule_change_def(rule_id).name_zh,
    )


def _pending_view(pending: PendingResolution) -> PendingView:
    return PendingView(
        kind=pending.kind,
        unit_id=pending.unit_id,
        reaction=pending.reaction,
        trigger_unit_id=pending.trigger_unit_id,
        skill_id=pending.skill_id,
        copy_skill_id=pending.copy_skill_id,
        trigger_event_seq=pending.trigger_event_seq,
        stamina_cost=pending.stamina_cost,
        mana_cost=pending.mana_cost,
        hp_cost_permille=pending.hp_cost_permille,
    )


def project_for(state: BattleState, team: Team) -> BattleView:
    """``team`` 看得到的戰場。純函式；暫停中的狀態也可以。"""
    tiles = tuple(
        TileView(
            x=x,
            y=y,
            height=t.height,
            terrain=t.terrain,
            surface=t.surface,
            surface_remaining=t.surface_remaining,
            surface_team=t.surface_team,
            object_id=t.object_id,
            surface_creator=t.surface_creator,
        )
        for y in range(state.height)
        for x in range(state.width)
        for t in (state.tile(x, y),)
    )
    return BattleView(
        team=team,
        map_id=state.map_id,
        map_name_zh=state.map_name_zh,
        width=state.width,
        height=state.height,
        tiles=tiles,
        objects=tuple(
            ObjectView(
                id=o.id,
                kind=o.kind,
                pos=o.pos,
                hp=o.hp,
                max_hp=o.max_hp,
                burning=o.burning,
                expires_in=o.expires_in,
            )
            for o in state.objects_sorted()
        ),
        units=tuple(_unit_view(state, u, team) for u in state.units_sorted()),
        traps=tuple(
            TrapView(
                owner_id=t.owner_id,
                team=t.team,
                pos=t.pos,
                skill_id=t.skill_id,
                remaining=t.remaining,
            )
            for t in sorted(visible_traps(state, team), key=lambda t: (t.pos.y, t.pos.x))
        ),
        turn_order=tuple(state.turn_order),
        active_unit=state.active_unit,
        round=state.round,
        max_rounds=state.max_rounds,
        weather_id=None if state.weather is None else state.weather.id,
        weather_name_zh=None if state.weather is None else state.weather.name_zh,
        objective=state.objective,
        ended=state.ended,
        winner=state.winner,
        end_reason=state.end_reason,
        pending=None if state.pending is None else _pending_view(state.pending),
        source_wells=tuple(Pos(x=x, y=y) for x, y in state.source_wells),
        zones=_zone_views(state),
        runes=_rune_views(state),
    )
