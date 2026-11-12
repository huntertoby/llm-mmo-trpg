"""內容庫 :class:`ContentLibrary`（載入結果的容器）與技能名稱檢查。"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path

from trpg.content.appearance import AppearanceTable
from trpg.content.battle import OffhandDef, UnitTemplate, WeaponDef
from trpg.content.composer_rules import ComposerRules, WhiteboardRules
from trpg.content.dev_starters import DevStarterTable
from trpg.content.environment import AiProfileTable, WeatherDef
from trpg.content.equipment import AffixDef, ItemDef, Loadout, resolve_loadout
from trpg.content.fields import FieldMapDef
from trpg.content.flash_templates import FlashTable
from trpg.content.item_budget import ItemGenRules
from trpg.content.library.ruleset import Ruleset
from trpg.content.library.world import _enemy_catalog
from trpg.content.maps import MapDef
from trpg.content.modifier_changes import ModifierChangeTable, bundled_modifier_changes
from trpg.content.races import OriginTable, RaceTable
from trpg.content.regions import RegionTable
from trpg.content.roguelite import RunRules
from trpg.content.schemas import ContentModel, ElementTable
from trpg.content.sim_builds import BuildTable
from trpg.content.skill_evolution import EvolutionTable
from trpg.content.skill_icon_art import IconArtTable
from trpg.content.skill_icon_props import IconPropTable
from trpg.content.skill_keywords import KeywordTable
from trpg.content.skill_rules import BudgetRules, ExclusionTable, SkeletonDef, SynergyTable
from trpg.content.skill_scaling import ScalingBasis, ScalingFacts, SkillScalingRules
from trpg.content.skills import SkillDef
from trpg.content.workshop import WorkshopRules, WorkshopTextTable
from trpg.content.world_address import AddressRules
from trpg.content.world_crafting import CraftingRules, ResonanceRules
from trpg.content.world_economy import WorldEconomy
from trpg.content.world_encounters import EncounterTable
from trpg.content.world_enemies import EnemyCatalog, WorldEnemies
from trpg.content.world_events import WorldEventContent
from trpg.content.world_loot import LootRules
from trpg.content.world_map import LocationMapDef
from trpg.content.world_mercenaries import MercenaryTable
from trpg.content.world_newcomer import NewcomerContent
from trpg.content.world_oaths import OathTable
from trpg.content.world_quests import WorldQuestContent
from trpg.content.world_rules import WorldRules
from trpg.content.world_season import SeasonContent
from trpg.content.world_trade import TradeRules
from trpg.shared.types import Attribute


@dataclass(frozen=True)
class ContentLibrary:
    """``content/`` 下全部已驗證的戰鬥內容。"""

    root: Path
    elements: ElementTable
    ruleset: Ruleset
    weapons: dict[str, WeaponDef]
    skills: dict[str, SkillDef]
    units: dict[str, UnitTemplate]
    maps: dict[str, MapDef]
    weather: dict[str, WeatherDef]
    ai_profiles: AiProfileTable
    budget: BudgetRules
    composer: ComposerRules
    builds: BuildTable
    synergies: SynergyTable
    keywords: KeywordTable
    """關鍵字推導表（``skill_keywords.yaml``，Phase 3-24b1）。"""
    exclusions: ExclusionTable
    skeletons: dict[str, SkeletonDef]
    roguelite: RunRules
    """roguelite 一輪的參數（``roguelite.yaml``，Phase 3-5a）。"""
    workshop: WorkshopRules
    """技能工坊「裝上試玩」的設定（``workshop.yaml``，Phase 3F-1）。"""
    skill_scaling: SkillScalingRules
    """技能縮放屬性的允許範圍（``skill_scaling.yaml``，Phase 3H-1；武器技看武器、法術技依主題）。
    必填（Phase 3T-2）：沒有縮放規則的內容庫無法驗證技能。"""
    affixes: dict[str, AffixDef] = field(default_factory=dict)
    """詞條白名單（``affixes.yaml``，Phase 3G-G1）。"""
    offhands: dict[str, OffhandDef] = field(default_factory=dict)
    """副手定義（``offhands.yaml``，Phase 3I-2）；物品的 ``offhand_def`` 由這裡嵌入。"""
    items: dict[str, ItemDef] = field(default_factory=dict)
    """物品（``items.yaml``，Phase 3G-G1；目前只有測試用物品）。"""
    appearance: AppearanceTable | None = None
    """裝備外觀清單（``equipment/appearance.yaml``，Phase 3G-G5a）。"""
    item_gen: ItemGenRules | None = None
    """物品產生器與物品預算的係數（``item_gen.yaml``，Phase 3K-1）。"""
    dev_starters: DevStarterTable = field(default_factory=DevStarterTable)
    """開發者起始包（``dev_starters.yaml``，Phase 3-24b2；不是設計規則，玩家介面不顯示）。"""
    evolution: EvolutionTable = field(default_factory=EvolutionTable)
    """3 級分歧進化的模板（``skill_evolution.yaml``，Phase 3-26b）。"""
    flash: FlashTable = field(default_factory=FlashTable)
    """閃現（靈光一閃）的規則與模板（``flash_templates.yaml``，Phase 3W-1）；不嵌入規則包。"""
    workshop_text: WorkshopTextTable = field(default_factory=WorkshopTextTable)
    """工坊說明的玩家語氣對照表（``workshop_text.yaml``，Phase 3-48f）；不屬於規則。"""
    regions: RegionTable | None = None
    """區域主題表（``regions.yaml``，Phase 3-37a；純顯示資料）。"""
    races: RaceTable | None = None
    """可玩種族（``races.yaml``，Phase 3R-1；已通過防最佳解驗證）。"""
    origins: OriginTable | None = None
    """出身（``origins.yaml``，Phase 3R-1；不影響戰鬥）。"""
    modifier_changes: ModifierChangeTable = field(default_factory=bundled_modifier_changes)
    """修正規則的改變種類（``modifier_changes.yaml``，Phase 3T-1）；不嵌入規則包（引擎只用
    :mod:`trpg.content.skills` 由內建資料推導的常數）。"""
    map_warnings: tuple[str, ...] = ()
    """地圖 ``region``／``look`` 的未知值警告（已丟棄、退回預設畫法；不是錯誤）。"""
    world_maps: dict[str, LocationMapDef] = field(default_factory=dict)
    """大世界地點圖（``world/maps/*.yaml``，Phase 5A-1）；鍵＝區域 ID。沒有資料夾時為空。不含主城
    （在 ``hub_maps``）；查某區的地點圖一律用 :meth:`location_map`。"""
    hub_maps: dict[str, LocationMapDef] = field(default_factory=dict)
    """不屬於任何區的樞紐地點圖（``hub: true``，目前只有主城；6D-R2）；鍵＝``region``。"""
    world_rules: WorldRules | None = None
    """大世界規則的數值（``world/rules.yaml``，Phase 5A-2）；沒有檔案時為 ``None``。"""
    world_enemies: WorldEnemies | None = None
    """大世界敵人的元素變體與精英詞綴（``world/enemies.yaml``，Phase 5A-3）；沒有檔案時為
    ``None``。"""
    world_encounters: dict[str, EncounterTable] = field(default_factory=dict)
    """大世界遭遇表（``world/encounters/*.yaml``，Phase 5A-3）；鍵＝區域 ID。沒有資料夾時為空。"""
    world_event_content: WorldEventContent = field(default_factory=WorldEventContent)
    """事件骨架、NPC 人設卡、事件規則（``world/events/``、``world/npcs/``、
    ``world/event_rules.yaml``，Phase 5B-1）；沒有資料時為空。"""
    world_quests: WorldQuestContent = field(default_factory=WorldQuestContent)
    """任務、聊天內容、事件好感度、酒館傳聞與好感度規則（``world/quests/``、``world/social/``、
    ``world/affinity.yaml``，Phase 5B-4）；沒有資料時為空。"""
    world_oaths: OathTable | None = None
    """誓約模板（``world/oaths.yaml``，Phase 5A-6 接點；內容在 5C-3）；沒有檔案時為 ``None``。"""
    world_mercenaries: MercenaryTable | None = None
    """系統傭兵名單（``world/mercenaries.yaml``，Phase 5C-1）；沒有檔案時為 ``None``（開戰用標準
    隊友）。"""
    world_economy: WorldEconomy = field(default_factory=WorldEconomy)
    """貨幣規則、物品與商店（Phase 5D-1；沒有 ``world/economy.yaml`` 時經濟功能關閉）。"""
    world_loot: LootRules | None = None
    """掉落規則（``world/loot.yaml``，Phase 5D-2）；沒有檔案時為 ``None``（掉落關閉）。"""
    world_address: AddressRules | None = None
    """NPC 怎麼稱呼玩家（``world/address.yaml``，Phase 6R-2，#137）；沒有檔案時為 ``None``
    （一律叫名字）。"""
    world_trade: TradeRules | None = None
    """交易共同前置與郵寄（``world/trade.yaml``，Phase 6T-1a）；沒有檔案時為 ``None``
    （交易關閉）。"""
    world_crafting: CraftingRules | None = None
    """鐵匠與附魔台（``world/crafting.yaml``，Phase 5D-3）；沒有檔案時為 ``None``（關閉）。"""
    world_newcomer: NewcomerContent | None = None
    """新手引導（``world/newcomer.yaml``，Phase 6F-2：開局在主城、戰鬥短提示）；沒有檔案時為
    ``None``（新角色照舊站在起始區的小鎮、沒有第一次免費傳送）。"""
    world_season: SeasonContent | None = None
    """賽季日程、今日目標、懸賞、世界事件（``world/season.yaml``，Phase 5F-1）；沒有檔案時為
    ``None``（這些功能關閉）。"""
    world_resonance: ResonanceRules | None = None
    """裝備共鳴（``world/resonance.yaml``，Phase 5D-3）；沒有檔案時為 ``None``（沒有共鳴）。"""
    field_maps: dict[str, FieldMapDef] = field(default_factory=dict)
    """實地地圖與室內圖（``world/fields/<region>/``，Phase 6B-1）；鍵＝地圖 ID；沒有資料夾＝空。"""
    field_warnings: tuple[str, ...] = ()
    """實地地圖的數值類警告（尺寸、傳送石數；不影響通過）。"""
    field_pending: tuple[str, ...] = ()
    """對面還沒畫的出口與門（配對待補；不是錯誤）。"""
    icon_props: IconPropTable = field(default_factory=IconPropTable)
    """技能圖示道具的允許清單（``skill_icon_props.yaml``，Phase IP-1）；圖示推導執行期也對它（QI-2a
    D3：清單外的 ``icon_prop`` 退回推導）。不嵌入規則包。"""
    icon_art: IconArtTable | None = None
    """Q 版技能圖示的推導表（``skill_icon_art.yaml``，Phase QI-2a）；只影響圖示，不嵌入規則包。
    ``None`` 時圖示推導讀預設內容資料夾的表（``trpg.narrative.skill_icon_art.icon_art_rules``）。"""
    files: list[tuple[Path, ContentModel]] = field(default_factory=list)
    retier_cache: dict[str, SkillDef] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    """技能照角色階級重配的快取（:func:`trpg.skillgen.skill_tier.retier`，3W-R1）：掛在內容庫上、隨它
    回收；鍵是「技能內容的 SHA-256 ＋ 階級」。不是建構參數，``dataclasses.replace`` 換內容後是新的空
    快取；不參與相等比較。"""
    mercenary_gear_cache: dict[tuple[str, int], dict[str, ItemDef]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    """傭兵系統裝備的快取（:func:`trpg.world.gear.mercenary_equipment`，5D-R1）：掛在內容庫上、隨它
    回收；鍵是「傭兵 ID ＋ 物品等級」，滿了就清空（上限在 ``trpg.world.gear``）。同 ``retier_cache``
    不是建構參數、不參與相等比較。"""
    outdoor_index: dict[str, dict[tuple[str, str], FieldMapDef]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    """:meth:`outdoor_map` 的索引（Phase 6C-R2：``"maps"`` → (區域, 地點) → 室外圖；第一次查時建）。
    同 ``retier_cache`` 不是建構參數，``dataclasses.replace`` 換了 ``field_maps`` 後是新的空
    索引。"""
    season_views: dict[str, ContentLibrary] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    """:meth:`for_season` 的快取（季 ID → 套上覆寫的內容庫；Phase 5F-R2）。"""
    season_base: ContentLibrary | None = field(default=None, init=False, repr=False, compare=False)
    """:meth:`for_season` 產生的內容庫指回原本的內容庫（原本的＝``None``）。"""

    def for_season(self, season_id: str) -> ContentLibrary:
        """``season_id`` 這一季的內容庫（Phase 5F-R2）：``world_season`` 換成套上
        ``seasons.<季 ID>`` 覆寫的內容，其他不變。那一季沒有覆寫時回傳原本的內容庫（第一季的行為
        完全不變）。結果有快取，同一季拿到同一個物件。"""
        base = self.season_base or self
        season = base.world_season
        if season is None or season_id not in season.seasons:
            return base
        view = base.season_views.get(season_id)
        if view is None:
            view = replace(base, world_season=season.for_season(season_id))
            object.__setattr__(view, "season_base", base)
            base.season_views[season_id] = view
        return view

    def outdoor_map(self, region: str, location: str) -> FieldMapDef | None:
        """地點的實地地圖（室外圖；還沒畫＝``None``）。同一個地點有好幾張時取地圖 ID 最小的
        （和原本依 ID 排序掃描的結果一樣）。"""
        index = self.outdoor_index.get("maps")
        if index is None:
            index = {}
            for map_id in sorted(self.field_maps):
                found = self.field_maps[map_id]
                if found.location is not None:
                    index.setdefault((found.region, found.location), found)
            self.outdoor_index["maps"] = index
        return index.get((region, location))

    def loadout_of(self, template: UnitTemplate) -> Loadout:
        """單位範本的裝備快照（``equipment`` 解析成內嵌定義的 :class:`Loadout`；沒有裝備時
        為空）。"""
        if not template.equipment:
            return Loadout()
        return resolve_loadout(template.equipment, self.items, self.affixes)

    def location_map(self, region: str) -> LocationMapDef | None:
        """``region`` 的地點圖：區域的，或主城這類樞紐的（6D-R2）；沒有＝``None``。"""
        found = self.world_maps.get(region)
        return found if found is not None else self.hub_maps.get(region)

    def enemy_catalog(self) -> EnemyCatalog:
        """解析大世界敵人名字（範本或變體）與套用精英詞綴（Phase 5A-3）。"""
        return _enemy_catalog(
            self.units, self.world_enemies, self.weapons, self.skills, self.ruleset
        )

    def unit(self, template_id: str) -> UnitTemplate:
        try:
            return self.units[template_id]
        except KeyError:
            known = ", ".join(sorted(self.units))
            raise KeyError(f"未知的單位範本：{template_id}（可用：{known}）") from None

    def map(self, map_id: str) -> MapDef:
        try:
            return self.maps[map_id]
        except KeyError:
            known = ", ".join(sorted(self.maps))
            raise KeyError(f"未知的地圖：{map_id}（可用：{known}）") from None

    def weapon_of(self, template: UnitTemplate) -> WeaponDef:
        return self.weapons[template.weapon]

    def scaling_basis(self, skill: SkillDef | ScalingFacts) -> ScalingBasis:
        """技能（或工坊草稿）的縮放屬性允許範圍與由來（``skill_scaling.yaml``，Phase 3H-7）。"""
        return self.skill_scaling.basis(skill, self.weapons)

    def scaling_range(self, skill: SkillDef | ScalingFacts) -> tuple[Attribute, ...]:
        """允許的縮放屬性（有順序；沒有主角屬性時取第一個）。"""
        return self.scaling_basis(skill).attrs

    def secondary_range(self, skill: SkillDef | ScalingFacts) -> tuple[Attribute, ...]:
        """允許的第二縮放屬性（3I-3，#46；武器技只能是心智屬性、身體類法術沒有；不含主屬性要
        呼叫者自己排除）。"""
        return self.skill_scaling.secondary_range(skill, self.weapons)

    def weather_def(self, weather_id: str) -> WeatherDef:
        try:
            return self.weather[weather_id]
        except KeyError:
            known = ", ".join(sorted(self.weather))
            raise KeyError(f"未知的天氣：{weather_id}（可用：{known}）") from None


def skill_name_problems(skills: Mapping[str, SkillDef], whiteboard: WhiteboardRules) -> list[str]:
    """顯示名相同、技能內容不同（6L-1，玩法 PM）：手寫技能（``skills/``）不可同名；白板配方的武器版
    名稱（``weapon_name_zh``）不可和手寫技能同名。配方之間的同名由
    :func:`~trpg.content.composer_rules.whiteboard_name_problems` 檢查。"""
    by_name: dict[str, list[SkillDef]] = {}
    for skill_id in sorted(skills):
        by_name.setdefault(skills[skill_id].name_zh, []).append(skills[skill_id])
    problems: list[str] = []
    for name, group in sorted(by_name.items()):
        bodies = {
            json.dumps(s.model_dump(mode="json", exclude={"id"}), sort_keys=True) for s in group
        }
        if len(group) > 1 and len(bodies) > 1:
            problems.append(f"技能同名但內容不同：{name}（{'、'.join(s.id for s in group)}）")
    for recipe in (*whiteboard.active, *whiteboard.passive, *whiteboard.reaction):
        if recipe.weapon_name_zh is not None and recipe.weapon_name_zh in by_name:
            problems.append(
                f"白板配方 {recipe.id} 的 weapon_name_zh 和手寫技能同名：{recipe.weapon_name_zh}"
            )
    return problems
