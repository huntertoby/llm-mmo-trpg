"""大世界的狀態：世界快照（``trpg-world/2``）與角色（``trpg-char/4``）（Phase 5A-2）。

``docs/phases/Phase5計畫.md`` 2.4、2.5、6.4。所有集合型欄位都以排序後的 tuple 存放（守則 2），
同樣的動作序列一定得到逐字相同的 JSON。角色欄位盡量和 :class:`trpg.roguelite.state.RunState`
同名同型別（2.2；``hero``、``origin``、``level``、``xp``、``hp``、``mana``、``stamina``）。

Phase 5A-6 加上成長欄位（靈感點、閃現狀態、生成技能、用法統計、技能階級、配點、精英首殺、誓約），
和 ``RunState`` 同名同型別，讓 :mod:`trpg.world.growth` 轉成 ``RunState`` 呼叫 roguelite 的成長
函式。
全部有預設值，``trpg-char/1`` 不升版號。

Phase 6B-2 加上實地地圖上的位置（:class:`FieldPos`）與解鎖的傳送石，角色格式升成 ``trpg-char/2``；
``trpg-char/1`` 的舊存檔照讀（``field`` 是 ``None``，第一次需要座標時放到地點的 ``entry``，
:mod:`trpg.world.field`）。

Phase 6C-1 加上看得見的敵人（:class:`FieldVisit`、:class:`FieldContact`），角色格式升成
``trpg-char/3``；``/1``、``/2`` 照讀（只多了選填欄位）。

Phase 6C-2 加上遭遇接觸位置（``enemy_at``）、Phase 6C-6 加上去過的地點
（``visited_locations``，區域圖的戰爭迷霧），角色格式升成
``trpg-char/4``；``/1``～``/3`` 照讀（只多了選填欄位）。

Phase 6C-5 加上地圖上的「！」（:class:`FieldEventMark`）、潛行、情境物件的使用紀錄
（:class:`ObjectUse`），角色格式升成 ``trpg-char/5``；``/1``～``/4`` 照讀（只多了選填欄位）。

Phase 6D-R2 加上這一趟進圖時的重生世代（``FieldVisit.generations``），角色格式升成
``trpg-char/6``；``/1``～``/5`` 照讀（只多了選填欄位）。

Phase 6F-4（6F-2b）加上提示與教學的紀錄（``hints_seen``、``hints_off``：出過的戰鬥短提示、開場、
教學；「不再顯示提示」）與看過的升級畫面（``level_seen``），改記在角色身上、不用本機儲存；角色格式
升成 ``trpg-char/7``；``/1``～``/6`` 照讀（舊存檔的 ``level_seen`` 補成目前等級，不會跳出舊的
升級畫面）。

Phase 6L-2 加上學到的技能的取得地點界域（``skill_regions``，#126：閃現的變化名照原技能的界域）與
三選一的取得區域（``PendingOffer.region``），角色格式升成 ``trpg-char/8``；``/1``～``/7`` 照讀
（只多了選填欄位；舊技能沒有紀錄＝中性）。

Phase 6T-1a 加上交易共同前置與郵寄（08 8.16、#136）：裝備的來歷與綁定（:class:`GearOrigin`，
``gear_origin``）、信箱（:class:`MailLetter`，``mailbox``）；角色格式升成 ``trpg-char/9``，``/1``～
``/8`` 照讀（舊存檔已有的裝備不知道穿過沒有，一律當作穿過＝綁定，來源記「舊存檔」）。世界格式升成
``trpg-world/4``（交易帳 ``trades``、主手大類比例 ``weapon_mix``、上線紀錄的 ``characters``；
``/1``～``/3`` 照讀）。

Phase 6R-1（#138）加上這一季用過免費換種族沒有（``free_race_change_used``），角色格式升成
``trpg-char/10``；``/1``～``/9`` 照讀（只多了選填欄位；舊角色＝還沒用過）。

Phase 6R-2（#137）主角紙娃娃多了玩家自己選的外觀（``hero.doll.custom``），角色格式升成
``trpg-char/11``；``/1``～``/10`` 照讀（沒有＝種族預設）。

Phase TR-1（#134）加上「未完成開局（在主城工坊靶場）」（``opening``：起始技能的種子），角色格式升成
``trpg-char/12``；``/1``～``/11`` 照讀（沒有＝已完成開局：舊角色建角時就選了武器與關鍵字）。

Phase WP-1（許願池，07 7.6、#88）加上本週許願的次數（``wish_week``）、待選三選一的來源多一種
``wish`` 與都不拿時的退款（``PendingOffer.refund``），角色格式升成 ``trpg-char/14``；``/1``～``/13``
照讀（沒有＝本週還沒許過願）。

Phase RG-2（精英單挑，#162）加上遭遇的單挑狀態（``EncounterResult.duel``，沒有時不輸出），角色格式
升成 ``trpg-char/15``；``/1``～``/14`` 照讀（沒有＝沒有提出單挑）。
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trpg.content.battle import ID_PATTERN, UnitTemplate
from trpg.content.equipment import ItemDef
from trpg.content.skills import SkillDef
from trpg.content.slots import SlotType
from trpg.content.world_newcomer import RangeClass
from trpg.content.world_oaths import OathDifficulty
from trpg.roguelite.state import PendingFlash, SkillOffer
from trpg.shared.rng import MASK64
from trpg.shared.types import Attribute
from trpg.skillgen.flash_state import SkillFlash
from trpg.skillgen.usage import SkillUsage
from trpg.world.clock import DayPhase

__all__ = [
    "CHAR_FORMAT",
    "LEGACY_CHAR_FORMATS",
    "LEGACY_WORLD_FORMATS",
    "WORLD_FORMAT",
    "BossAttempt",
    "BossClear",
    "BountyClaim",
    "CharacterState",
    "ClearedLocation",
    "CompanionAffinity",
    "CompanionBench",
    "CraftRecipe",
    "DailyActivity",
    "DailyGoalProgress",
    "DefeatedSpawn",
    "EncounterResult",
    "EventTrigger",
    "FieldContact",
    "FieldEventMark",
    "FieldPos",
    "FieldVisit",
    "GearBound",
    "GearMod",
    "GearOrigin",
    "GearSource",
    "LastBattle",
    "LeagueEntry",
    "LocationRef",
    "LootSummary",
    "MailLetter",
    "NextBattleMod",
    "OathState",
    "ObjectUse",
    "OpeningState",
    "PendingLoot",
    "PendingOffer",
    "PerceptionMark",
    "QuestState",
    "RecipeRecord",
    "RecipeStep",
    "ShadowRecord",
    "ShadowReport",
    "ShadowSnapshot",
    "ShopPurchase",
    "TargetAdjustment",
    "ThreadState",
    "TimedFlag",
    "TradeRecord",
    "WeaponMix",
    "WishWeek",
    "WorldEventState",
    "WorldState",
]

WORLD_FORMAT: Final = "trpg-world/4"
LEGACY_WORLD_FORMATS: Final = frozenset({"trpg-world/1", "trpg-world/2", "trpg-world/3"})
"""照讀、讀進來就升成 :data:`WORLD_FORMAT` 的舊世界格式（6C-1b：只多了 ``defeated_spawns``；
6C-R2：只多了 ``defeated_spawns`` 的 ``wins``，舊資料當作打贏過 1 次；6T-1a：只多了 ``trades``、
``weapon_mix``、``DailyActivity.characters``）。"""
_ORIGIN_FORMATS: Final = frozenset({"trpg-char/9", "trpg-char/10"})
"""已經有裝備來歷（``gear_origin``）的舊角色格式（6T-1a 起），讀進來不重算來歷。"""
CHAR_FORMAT: Final = "trpg-char/15"
LEGACY_CHAR_FORMATS: Final = frozenset(
    {
        "trpg-char/1",
        "trpg-char/2",
        "trpg-char/3",
        "trpg-char/4",
        "trpg-char/5",
        "trpg-char/6",
        "trpg-char/7",
        "trpg-char/8",
        "trpg-char/9",
        "trpg-char/10",
        "trpg-char/11",
        "trpg-char/12",
        "trpg-char/13",
        "trpg-char/14",
    }
)
"""照讀、讀進來就升成 :data:`CHAR_FORMAT` 的舊角色格式（6B-2～6R-1：只多了選填欄位；6T-1a 另把
``/8`` 以前存檔的裝備標成綁定，見 :meth:`CharacterState._upgrade_format`）。"""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocationRef(_Model):
    """某區的某個地點。"""

    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)

    def key(self) -> tuple[str, str]:
        return (self.region, self.location)


class ClearedLocation(_Model):
    """所有人看到「已清空」的地點（09 9.6.7 #15）；``respawn_at``（UTC 秒）起敵人重生。"""

    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    respawn_at: int = Field(ge=0)


class DefeatedSpawn(_Model):
    """實地地圖上被打贏的一隊（6C-1b，21.10 第 9 條）：所有人看得到它消失，``respawn_at``（UTC 秒）
    起重生。``spawn`` 是地點室外圖 ``spawns`` 的索引。"""

    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    spawn: int = Field(ge=0)
    respawn_at: int = Field(ge=0)
    wins: int = Field(default=1, ge=1)
    """這一隊被打贏過幾次（Phase 6C-R2）＝現在這一隊的重生世代（陣容種子用，
    :func:`trpg.world.rng.spawn_seed`）。``personal`` 的隊伍、不共享清空的地點打贏時也記
    （``respawn_at`` 寫當下，不會讓它對任何人消失），讓下一次碰到的陣容換一批、所有人看到的一樣。"""

    def key(self) -> tuple[str, str, int]:
        return (self.region, self.location, self.spawn)


class PerceptionMark(_Model):
    """角色最後一次對某個隱藏地點做感知判定的日子（``refresh_day``；#112 每天 1 次）。"""

    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    day: int = Field(ge=0)


type Facing = Literal["n", "e", "s", "w"]
"""朝向（地圖上 y 向下：``n``＝往 y 減少）。"""


class FieldPos(_Model):
    """實地地圖上的位置（Phase 6B-2）：``map`` 是實地地圖或室內圖的 ID。"""

    map: str = Field(pattern=ID_PATTERN)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    facing: Facing = "s"


class FieldContact(_Model):
    """碰到實地地圖上看得見的敵人（Phase 6C-1，:mod:`trpg.world.field_enemies`）：哪一隊、陣容的
    種子、接觸點與先手（21.10 第 4 條）、撤退回哪一格（21.10 第 7 條）。"""

    map: str = Field(pattern=ID_PATTERN)
    spawn: int = Field(ge=0)
    """``FieldMapDef.spawns`` 的索引。"""
    group: str = Field(pattern=ID_PATTERN)
    """陣容 ID（``spawns`` 的 ``group``；遭遇變化、懸賞照舊優先）。"""
    lineup_seed: int = Field(ge=0, le=0xFFFFFFFF)
    """陣容用的種子（取代 ``battle_seed`` 的 ``":lineup"``；地圖上顯示的陣容＝開戰的陣容）。"""
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    """接觸點（自己站的格子；打贏回到這裡）。"""
    first: Literal["ally", "enemy"] | None = None
    """``ally``＝從背後、在敵人視野外接觸；``enemy``＝被敵人看到；``None``＝照現行先攻。"""
    retreat_to: FieldPos
    """撤退回到的格子（進這張地圖時站的格子）。"""
    came_from: tuple[int, int] | None = None
    """走到接觸點的前一格（6E-3：就地開打時主角沿走來的方向往回退，21.10 第 26 條）；6E-3 以前的
    資料沒有，改在符合距離的格子裡挑最靠近接觸點的。"""
    enemy_facing: Facing | None = None
    """接觸時這一隊帶頭的朝向（6E-3b 寫入，原本用來讓主角不擺在背後半邊；6E-3c 撤回該限制，照舊
    記錄但不再用於擺位）；6E-3b 以前的資料沒有。"""
    enemy_at: tuple[int, int] | None = None
    """接觸時這一隊站的格子（Phase 6C-2：就地切 12×12 戰場用）；6C-2 以前的資料沒有，開戰時改用
    地點原本的戰鬥地圖模板。"""


class FieldVisit(_Model):
    """這一趟待在某個地點的實地地圖（Phase 6C-1）：換地點時重來。

    ``seed`` 由角色的 ``field`` 串流衍生（:mod:`trpg.world.rng`），決定每隊的陣容、巡邏起點與駐守
    朝向；``ticks``＝這一趟在室外圖走了幾格（巡邏你走一格它走一格）；``defeated``＝這一趟打贏的
    隊伍裡只對自己算的（``personal``、不共享清空的地點；離開這個地點前不再出現，6C-1b）。"""

    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    seed: int = Field(ge=0, le=0xFFFFFFFF)
    ticks: int = Field(default=0, ge=0)
    defeated: tuple[int, ...] = ()
    arrived: FieldPos
    """進這張地圖時站的格子（撤退回這裡）。"""
    generations: tuple[int, ...] = ()
    """進圖時每隊（``spawns`` 的索引）的重生世代（6D-R2）：這一趟的陣容固定用它，別人打贏造成的
    世代 +1 下一趟才生效。空（``trpg-char/5`` 以前的存檔）或索引超出＝照世界現在的世代。"""

    def generation(self, index: int) -> int | None:
        """第 ``index`` 隊這一趟固定的重生世代；沒記＝``None``。"""
        return self.generations[index] if index < len(self.generations) else None

    @field_validator("defeated")
    @classmethod
    def _sorted_defeated(cls, ids: tuple[int, ...]) -> tuple[int, ...]:
        if list(ids) != sorted(set(ids)):
            raise ValueError("defeated 必須排序且不重複")
        return ids


class ObjectUse(_Model):
    """角色最後一次用某個情境物件開事件的日子（Phase 6C-5；每天 6 點刷新後才能再開）。"""

    map: str = Field(pattern=ID_PATTERN)
    object: str = Field(pattern=ID_PATTERN)
    day: int = Field(ge=0)


class EncounterResult(_Model):
    """遇敵的結果（只是資料，不開戰；開戰在 5A-4，敵人陣容在 5A-3）。"""

    region: str
    location: str
    """遇敵的地點（移動的目的地）。"""
    level: int = Field(ge=1)
    """該地點的建議等級（``level_max``）。"""
    battle_map: str | None
    """從目的地 ``battle_maps`` 抽的地圖；目的地沒有戰鬥地圖時為 ``None``
    （5A-4 從區域地圖池挑）。"""
    battle_seed: int = Field(ge=0, le=0xFFFFFFFF)
    weather: str
    day_phase: DayPhase
    at: int = Field(ge=0)
    """遇敵的時間（UTC 秒）。"""
    from_location: str | None = None
    """出發地點（撤退回這裡，5A-4）；5A-4 以前的資料沒有，撤退時回本區小鎮。"""
    objective: Literal["escape", "defend"] | None = None
    """戰鬥解法指定的勝利條件（Phase 5B-4c；地圖支援時用它，否則全滅）；``None``＝地圖預設。"""
    world_flags: tuple[str, ...] = ()
    """遇敵當下有效的世界旗標（排序；Phase 5B-4c 世界級線頭到期結局的遭遇加人）。"""
    level_bonus: int = Field(default=0, ge=0)
    """遇敵當下該區的建議等級加成（Phase 5F-1，世界事件失敗 +1；敵人等級與經驗照加成後）。"""
    bounty: str | None = Field(default=None, pattern=ID_PATTERN)
    """遇敵當下這個地點貼出、還沒被搶的懸賞（Phase 5F-1；陣容照懸賞）。"""
    season_boss: str | None = Field(default=None, pattern=ID_PATTERN)
    """賽季 Boss 的挑戰（Phase 5F-3；Boss ID）：陣容、地圖、等級照 ``season_boss`` 資料，戰後照
    賽季 Boss 的規則回寫。"""
    contact: FieldContact | None = None
    """碰到實地地圖上看得見的敵人（Phase 6C-1）；``None``＝移動遇敵、戰鬥解法等。"""
    duel: Literal["offered", "accepted", "declined"] | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    """精英單挑（RG-2，#162，09 9.6.6）：``offered``＝陣容排最前的精英提出一對一（遇敵時判定），
    ``duel_choice`` 改成 ``accepted``／``declined``；還沒選就開打＝拒絕。``None``＝不提
    （不輸出）。"""


class EventTrigger(_Model):
    """觸發的事件（Phase 5B-1；只是「哪個骨架」的資料，解法與結果在 5B-2～5B-4）。

    ``skeleton`` 是引擎挑的預設骨架；``candidates`` 是當下所有合格的骨架（依 ID 排序），說書人
    （5B-3）只能從這裡換，不能自己多生事件（09 9.6.7 #6）。
    """

    region: str
    location: str
    skeleton: str
    candidates: tuple[str, ...]
    follows_thread: str | None = None
    """被接上的有效線頭（骨架的 ``follows`` 命中時）。"""
    weather: str
    day_phase: DayPhase
    at: int = Field(ge=0)
    narrated: bool = False
    """說書人已經敘述過這個事件（Phase 5B-3；每個事件只能敘述、換骨架 1 次）。"""
    combat_solution: int | None = Field(default=None, ge=0)
    """選了戰鬥解法（Phase 5B-4b）：骨架 ``solutions`` 的索引；遭遇結束時結算事件。"""
    guaranteed: bool = False
    """機遇保底觸發的（Phase 5B-4d，07 7.6「第 7 天前保底 1 次」：不看天氣、時段與機率）。"""

    @field_validator("candidates")
    @classmethod
    def _candidates_sorted(cls, candidates: tuple[str, ...]) -> tuple[str, ...]:
        if list(candidates) != sorted(set(candidates)):
            raise ValueError("candidates 必須排序且不重複")
        return candidates


class FieldEventMark(_Model):
    """地圖上的「！」（Phase 6C-5；21.6、21.9 第 9 條）：進入地圖時擲出的事件先放在事件點上，走過去
    碰到（站上或四方向相鄰）才變成 ``pending_event`` 開事件卡；同一趟只開一次，離開地點就消失。"""

    trigger: EventTrigger
    map: str = Field(pattern=ID_PATTERN)
    """事件點所在的實地地圖或室內圖。"""
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    spot: str = Field(pattern=ID_PATTERN)
    """事件點的 ID（``event_spots`` 的 ``id``）。"""


class NextBattleMod(_Model):
    """下一場戰鬥帶的修正（Phase 5B-2：情境判定的短期 buff、debuff、敵人增援；09 9.6.4）。

    只記錄；之後的戰鬥接線開戰時套用並清掉。``source`` 是產生它的情境模板。
    """

    kind: Literal["buff", "debuff", "reinforce"]
    status: str | None = None
    """buff／debuff 的狀態（``statuses.yaml``）；增援為 ``None``。"""
    source: str = Field(pattern=ID_PATTERN)


class OathState(_Model):
    """目前的誓約（Phase 5A-6 接點；06 6.26、09 9.6.10 #106）：一直有效到自己解除。加成與違反判定在
    5C-3。"""

    template: str = Field(pattern=ID_PATTERN)
    params: dict[str, str | int] = Field(default_factory=dict)
    difficulty: OathDifficulty
    sworn_at: int = Field(ge=0)

    @field_validator("params")
    @classmethod
    def _sorted_params(cls, params: dict[str, str | int]) -> dict[str, str | int]:
        return dict(sorted(params.items()))


class LootSummary(_Model):
    """一場戰鬥撿到的東西（Phase 5D-2；``LastBattle.loot``）。"""

    materials: dict[str, int] = Field(default_factory=dict)
    """撿到的材料（物品 → 個數，依 ID 排序）。"""
    gear: tuple[str, ...] = ()
    """撿到的裝備名稱（依掉落順序）。"""
    lost_materials: dict[str, int] = Field(default_factory=dict)
    """背包滿了沒撿到的材料（代決 5D2-6）。"""
    lost_gear: tuple[str, ...] = ()
    """背包滿了沒撿到的裝備名稱。"""

    @field_validator("materials", "lost_materials")
    @classmethod
    def _sorted(cls, counts: dict[str, int]) -> dict[str, int]:
        return dict(sorted(counts.items()))

    @property
    def empty(self) -> bool:
        return not (self.materials or self.gear or self.lost_materials or self.lost_gear)


class PendingLoot(_Model):
    """背包放不下、等玩家在戰後結算選要丟哪件的戰利品（Phase 5D-2b；20.2，玩法 PM 2026-11-03 代決：
    不做暫存區）。只留最近一場：下一場打贏、結算掉落前還沒決定的就留在原地（``LootAbandonedEvent``）。"""

    materials: dict[str, int] = Field(default_factory=dict)
    """放不下的材料（物品 → 個數，依 ID 排序）。"""
    gear: tuple[ItemDef, ...] = ()
    """放不下的裝備（依掉落順序）。"""

    @field_validator("materials")
    @classmethod
    def _sorted(cls, counts: dict[str, int]) -> dict[str, int]:
        return dict(sorted(counts.items()))

    @property
    def empty(self) -> bool:
        return not self.materials and not self.gear


type OpeningStage = Literal["pick_class", "starter", "chosen"]
"""開局的階段（#150，21 21.5）：選大類中／用入門配備打新手第 1、2 步／正式選定後到 4 級前。"""


class DeferredOffer(_Model):
    """入門期先保留、不出題的三選一（#150 第 2 點）：新手任務與步驟（出題在 OB-2）。"""

    quest: str = Field(pattern=ID_PATTERN)
    step: int = Field(ge=0)


class OpeningState(_Model):
    """開局還沒結束（TR-1 #134；OB-1 #150）。``seed`` 是起始技能的種子（建角時決定，確定出發與靶場
    的預覽、試打都用它，同一組選擇給同樣的招）。``opening`` 非 ``None`` 的角色才受開局閘門管（已完成
    開局的舊角色不受影響，:func:`trpg.world.opening.opening_gate`）。"""

    seed: int = Field(ge=0, le=2**64 - 1)
    stage: OpeningStage = "pick_class"
    weapon_class: RangeClass | None = None
    """選定的大類（``pick_class`` 階段為 ``None``）。"""
    deferred_offers: tuple[DeferredOffer, ...] = ()
    """第 1、2 步延後的三選一，依序（OB-2 寫入）。"""
    weapon: str | None = Field(default=None, pattern=ID_PATTERN)
    """正式選定的武器（``chosen`` 階段；OB-2 寫入）。"""
    keywords: tuple[str, ...] = ()
    """正式選定的 2 個關鍵字（``chosen`` 階段；OB-2 寫入）。"""
    reselect_used: bool = False
    """4 級前的免費重選用過沒（OB-3）。"""
    granted_skills: tuple[str, ...] = ()
    """重選時要收回的招：起始 2 招＋第 1、2 步三選一拿到的（OB-2 寫入；入門招不算）。"""

    @model_validator(mode="after")
    def _class_matches_stage(self) -> OpeningState:
        if (self.stage == "pick_class") != (self.weapon_class is None):
            raise ValueError("只有 pick_class 階段沒有大類，其他階段一定要有")
        return self


class LastBattle(_Model):
    """最近一次戰鬥的結果（Phase 5A-7；5A-5 待決 1）：``fight`` 結算時寫入（勝負都算），讓重新整理的
    畫面仍看得到輸贏。由日誌決定，可重播。"""

    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    won: bool
    end_reason: str | None = None
    rounds: int = Field(ge=0)
    xp_gained: int = Field(ge=0)
    level_before: int = Field(ge=1)
    level: int = Field(ge=1)
    at: int = Field(ge=0)
    oath: str | None = None
    """這場帶的誓約模板（5C-3；``None``＝沒有誓約）。"""
    oath_broken: bool = False
    """這場違反了誓約（戰鬥中或戰鬥結束時判定，5C-3）。"""
    loot: LootSummary | None = None
    """這場撿到的東西（Phase 5D-2；打贏才有，沒有掉落為 ``None``）。"""


class CompanionBench(_Model):
    """劇情夥伴加入時替下的隊伍成員（5C-3；任務結束時還原）：傭兵 ID 或影子複本，與它的打法。"""

    mercenary: str | None = Field(default=None, pattern=ID_PATTERN)
    shadow: ShadowSnapshot | None = None
    ai: str | None = Field(default=None, pattern=ID_PATTERN)
    position: int = Field(default=1, ge=0)
    """原本在隊伍出場順序的第幾名（0 起算；5C-3 替掉第 2 名＝1）。"""

    @property
    def member_id(self) -> str:
        if self.mercenary is not None:
            return self.mercenary
        assert self.shadow is not None
        return self.shadow.owner


class CompanionAffinity(_Model):
    """劇情夥伴今天已經因為「帶他打贏」加了多少好感度（18.7.6：阿岳每天最多 +6）。"""

    day: int = Field(ge=0)
    gained: int = Field(ge=0)


class ThreadState(_Model):
    """一條進行中的線頭（09 9.6.7 #6；``expires_at``（UTC 秒）起到期）。"""

    thread: str = Field(pattern=ID_PATTERN)
    """線頭 ID（事件骨架 ``threads`` 裡的 ``id``）。"""
    skeleton: str = Field(pattern=ID_PATTERN)
    """留下這條線頭的事件骨架。"""
    region: str = Field(pattern=ID_PATTERN)
    created_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)

    def key(self) -> tuple[int, str]:
        return (self.created_at, self.thread)


class QuestState(_Model):
    """一個接過的任務（Phase 5B-4）：完成了幾步、是否已完成。"""

    quest: str = Field(pattern=ID_PATTERN)
    steps_done: int = Field(default=0, ge=0)
    done: bool = False
    started_at: int = Field(ge=0)
    completed_at: int | None = Field(default=None, ge=0)


class PendingOffer(_Model):
    """任務給的技能三選一，還沒選（Phase 5B-4；07 7.6）。候選已經產生好，選的時候不重抽。

    ``source``（Phase 5B-4c）：``quest``＝任務（``quest``、``step`` 是任務與步驟）；
    ``opportunity``＝事件的機遇解法（``quest``＝骨架 ID、``step``＝``opportunity``）；
    ``wish``＝主城的許願池（WP-1；``quest``＝``wish``、``step``＝``w<週>_<第幾次>``）。

    ``guaranteed``（Phase 5D-2b）：機遇是保底觸發的那次（標題用骨架的保底「誰」）；預設 ``False``，
    舊存檔照讀。"""

    quest: str = Field(pattern=ID_PATTERN)
    step: str = Field(pattern=ID_PATTERN)
    offer: SkillOffer
    source: Literal["quest", "opportunity", "wish"] = "quest"
    guaranteed: bool = False
    region: str | None = None
    """取得地點的區域（6L-2，#126：選到的技能記進 ``CharacterState.skill_regions``）；``None``＝
    舊存檔，選的時候用角色當下的區域。"""
    refund: int = Field(default=0, ge=0, exclude_if=lambda v: v == 0)
    """都不拿時退還的任務幣（WP-1 許願池，#88 2b；照許願當時的費用算）；0 不輸出。"""


class WishWeek(_Model):
    """本週許願的次數（Phase WP-1；``week`` 是 :func:`~trpg.world.season.week_of`，換週＝0 次）。"""

    week: int = Field(ge=0)
    used: int = Field(ge=0)


def _check_threads(threads: tuple[ThreadState, ...]) -> tuple[ThreadState, ...]:
    keys = [t.key() for t in threads]
    ids = [t.thread for t in threads]
    if keys != sorted(keys) or len(set(ids)) != len(ids):
        raise ValueError("threads 必須依建立時間、ID 排序且同一線頭不重複")
    return threads


class CraftRecipe(_Model):
    """打造的配方（Phase 5D-3，08 8.20）：部位＋物品等級＋稀有度＋指定的 build 詞條＋材料組合。

    ``weapon_class`` 只有武器（主角武器的大類）；``affix`` 是 ``None``＝隱藏配方（獨特詞條由配方
    決定）；``grade`` 是 1 種通用料；``materials`` 是特色材料（排序、不重複）。"""

    slot_type: SlotType
    weapon_class: Literal["melee", "ranged", "focus"] | None = None
    rarity: Literal["rare", "epic"]
    item_level: int = Field(ge=1, le=99)
    affix: str | None = Field(default=None, pattern=ID_PATTERN)
    grade: str = Field(pattern=ID_PATTERN)
    materials: tuple[str, ...] = ()

    @field_validator("materials")
    @classmethod
    def _sorted_materials(cls, ids: tuple[str, ...]) -> tuple[str, ...]:
        if list(ids) != sorted(set(ids)):
            raise ValueError("materials 必須排序且不重複")
        return ids


class RecipeStep(_Model):
    """配方的一步改動（Phase 5D-3b，8.20「配方＝基礎配方＋重骰序列」）：``affix`` 是 ``None``＝重骰
    第 ``index`` 條（亂數由「指紋＋位置＋n」決定）；否則＝用精華把第 ``index`` 條
    指定成 ``affix``。"""

    index: int = Field(ge=0, le=7)
    affix: str | None = Field(default=None, pattern=ID_PATTERN)


class GearMod(_Model):
    """一件裝備被打造、強化、重骰、指定的紀錄（Phase 5D-3，8.20）。

    ``fingerprint``：打造品是配方指紋；掉落品是第一次改動時物品 JSON 的 SHA-256（沒有配方碼）。
    ``rerolls``：依序重骰過的詞條位置（第 n 次重骰某位置的亂數由「指紋＋位置＋n」決定）。"""

    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    recipe: str | None = Field(default=None, pattern=r"^[0-9a-f]{10}$")
    enhance: int = Field(default=0, ge=0, le=10)
    rerolls: tuple[int, ...] = ()
    imbues: int = Field(default=0, ge=0)
    steps: tuple[RecipeStep, ...] = ()
    """依序的重骰與指定（5D-3b；配方的一部分）。5D-3 的舊紀錄沒有這欄：``len(steps) != changes``
    ＝序列不完整，這件不能再產生配方碼（見 :attr:`traceable`）。"""
    variant: str | None = Field(default=None, pattern=r"^[0-9a-f]{10}$")
    """帶重骰序列的配方碼（5D-3b）；沒改過或不能追溯時為 ``None``（顯示 ``recipe``）。"""

    @property
    def changes(self) -> int:
        """重骰與指定合計幾次（費用越改越貴，8.14）。"""
        return len(self.rerolls) + self.imbues

    @property
    def traceable(self) -> bool:
        """是打造品，且每一次重骰與指定都記在 ``steps``（能併進配方碼）。"""
        return self.recipe is not None and len(self.steps) == self.changes

    @property
    def code(self) -> str | None:
        """這件裝備目前的配方碼（帶序列的優先）；掉落品為 ``None``。"""
        return self.variant or self.recipe


type GearSource = Literal["drop", "craft", "trade", "other", "legacy"]
"""裝備最初怎麼來的（6T-1a）：掉落、打造、交易收到（沒有來歷的物品）、其他、舊存檔。"""
type GearBound = Literal["unique", "first_kill", "legacy"]
"""取得就綁定的原因（08 8.16）：獨特裝備、首殺物品、舊存檔（不知道穿過沒有，當作穿過）。"""


class GearOrigin(_Model):
    """一件裝備的來歷與綁定（Phase 6T-1a，08 8.16、#136）。跟著物品走：交易時原封不動轉到收件人。

    卡片寫「最初得自：〈``owner_name``〉（〈``source_zh``〉）」；目前持有者＝這筆紀錄所在的角色。"""

    owner: str = Field(pattern=ID_PATTERN)
    """最初得到它的角色 ID。"""
    owner_name: str
    source: GearSource
    source_zh: str
    """來源的一句話（例「霧渡鎮的戰利品」「石師傅鐵鋪打造」）。"""
    at: int = Field(ge=0)
    worn: bool = False
    """穿過（穿上就綁定）。"""
    bound: GearBound | None = None
    """取得就綁定的原因；``None``＝沒有。"""

    @property
    def tradable(self) -> bool:
        return not self.worn and self.bound is None


class MailLetter(_Model):
    """一封信（Phase 6T-1a 郵寄，08 8.16）：在收件人的信箱裡；被拒收時回到寄件人的信箱
    （``returned``）。附件連同改動紀錄與來歷一起寄。

    過期（``expires_at`` 起還沒領）的信 **自動退回寄件人**（6T-1b）：資料留在收件人的信箱、但收件人
    看不到也領不了，寄件人的退件分頁直接列出，和被拒收的一樣用 ``mail_claim`` 領（那一筆同時從收件人
    身上拿掉）。"""

    id: str = Field(pattern=r"^mail_[0-9]{6,}$")
    sender: str = Field(pattern=ID_PATTERN)
    sender_name: str
    recipient: str = Field(pattern=ID_PATTERN)
    recipient_name: str
    from_region: str = Field(pattern=ID_PATTERN)
    from_location: str = Field(pattern=ID_PATTERN)
    sent_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)
    note: str = ""
    items: dict[str, int] = Field(default_factory=dict)
    gear: tuple[ItemDef, ...] = ()
    gear_mods: dict[str, GearMod] = Field(default_factory=dict)
    gear_origin: dict[str, GearOrigin] = Field(default_factory=dict)
    gold: int = Field(default=0, ge=0)
    """對方實收的金幣（已扣稅）。"""
    tax: int = Field(default=0, ge=0)
    """寄件時扣的跑腿費（退件不退）。"""
    returned: Literal["refused", "expired"] | None = None
    """退回寄件人的原因（在寄件人的信箱裡）；``None``＝寄給收件人的信。"""

    @field_validator("items")
    @classmethod
    def _sorted_items(cls, counts: dict[str, int]) -> dict[str, int]:
        return _check_counts(counts)

    @field_validator("gear_mods")
    @classmethod
    def _sorted_mods(cls, rows: dict[str, GearMod]) -> dict[str, GearMod]:
        return dict(sorted(rows.items()))

    @field_validator("gear_origin")
    @classmethod
    def _sorted_origins(cls, rows: dict[str, GearOrigin]) -> dict[str, GearOrigin]:
        return dict(sorted(rows.items()))

    def overdue(self, now: int) -> bool:
        """寄出的信過期了（還沒領、``returned`` 是 ``None``）。"""
        return self.returned is None and now >= self.expires_at


class TradeRecord(_Model):
    """交易帳的一筆（Phase 6T-1a，08 8.16「記雙方帳號、物品 ID、估值」）：每封信一筆，寄出時寫入，
    領取、拒收、取回時更新 ``status``。稽核報表（:mod:`trpg.world.trade_audit`）只讀這裡。"""

    id: str = Field(pattern=r"^mail_[0-9]{6,}$")
    kind: Literal["mail"] = "mail"
    at: int = Field(ge=0)
    sender: str = Field(pattern=ID_PATTERN)
    sender_account: str = Field(min_length=1)
    recipient: str = Field(pattern=ID_PATTERN)
    recipient_account: str = Field(min_length=1)
    items: dict[str, int] = Field(default_factory=dict)
    gear: tuple[str, ...] = ()
    """附件裝備的物品 ID（寄出時的）。"""
    gold: int = Field(default=0, ge=0)
    """寄出的金幣（稅前）。"""
    tax: int = Field(default=0, ge=0)
    value: int = Field(default=0, ge=0)
    """估值（金幣）：材料與消耗品照買價、裝備照回收價、金幣照面額（稅前）。"""
    expires_at: int = Field(ge=0)
    status: Literal["sent", "claimed", "refused", "reclaimed"] = "sent"
    """``reclaimed``＝過期自動退回、寄件人領回（6T-1b 起沒有另外的取回動作；值沿用 6T-1a 的）。"""
    closed_at: int | None = Field(default=None, ge=0)


class WeaponMix(_Model):
    """全服在線角色的武器大類人數（Phase 6T-1a，#135）：每天 6 點換日時用前一天有動作的角色算一次，
    主手掉別大類時照它分。"""

    day: int
    """算的那個刷新日（用的是 ``day - 1`` 的上線紀錄）。"""
    counts: dict[str, int] = Field(default_factory=dict)
    """武器大類 → 角色數（依鍵排序；0 不寫）。"""

    @field_validator("counts")
    @classmethod
    def _sorted_counts(cls, counts: dict[str, int]) -> dict[str, int]:
        return _check_counts(counts)


class RecipeRecord(_Model):
    """世界記得的配方（Phase 5D-3，M6）：配方碼、配方、第一次打出的名稱與首位發現者。"""

    code: str = Field(pattern=r"^[0-9a-f]{10}$")
    recipe: CraftRecipe
    name_zh: str
    discoverer: str = Field(pattern=ID_PATTERN)
    discoverer_name: str
    discovered_at: int = Field(ge=0)
    hidden: str | None = Field(default=None, pattern=ID_PATTERN)
    """隱藏配方的 ID（M7）；一般配方為 ``None``。"""
    base: str | None = Field(default=None, pattern=r"^[0-9a-f]{10}$")
    """帶重骰序列的配方（5D-3b）：基礎配方的配方碼；基礎配方本身為 ``None``。"""
    steps: tuple[RecipeStep, ...] = ()
    """重骰序列（5D-3b，8.20）：照順序在基礎配方打出的裝備上重骰或指定。"""
    listed: bool = True
    """列在配方表上（5D-4，玩法 PM 2026-11-03 代決：每件裝備只列最新一筆）。裝備改出新碼時舊碼
    改成 ``False``、有人用這個碼打出新裝備時改回 ``True``；不列的碼照樣能打（可能已經分享出去）。"""
    season_id: str = Field(pattern=ID_PATTERN)
    """發現時的賽季（Phase 5D-R2；首位發現者是紀念類，見 ``trpg.server.season_policy``）。
    舊存檔沒有這個欄位時，:class:`WorldState` 讀入時補成世界當季（``WorldState.season_id``）。"""


class ShopPurchase(_Model):
    """本週在某家店買過的限量商品個數（Phase 5D-1；8.26.1 區域特產每週限量）。"""

    shop: str = Field(pattern=ID_PATTERN)
    item: str = Field(pattern=ID_PATTERN)
    week: int = Field(ge=0)
    bought: int = Field(ge=1)


def _check_counts(counts: dict[str, int]) -> dict[str, int]:
    if any(v < 1 for v in counts.values()):
        raise ValueError("物品個數必須至少 1（用完就拿掉）")
    return dict(sorted(counts.items()))


def _raw_ids(value: object) -> list[str]:
    """存檔原文裡物品（``{"id": …}``）的 ID；格式不對的略過（交給欄位驗證報錯）。"""
    if isinstance(value, dict):
        rows: list[object] | tuple[object, ...] = list(value.values())
    else:
        rows = value if isinstance(value, list | tuple) else []
    return [r["id"] for r in rows if isinstance(r, dict) and isinstance(r.get("id"), str)]


def _legacy_origins(data: dict[str, object]) -> dict[str, dict[str, object]]:
    """6T-1a 以前的存檔：身上的裝備一律記成「舊存檔」來源、綁定（不知道穿過沒有，保守）。"""
    owner = data.get("character_id")
    hero = data.get("hero")
    name = hero.get("name_zh") if isinstance(hero, dict) else None
    if not isinstance(owner, str):
        return {}
    pending = data.get("pending_loot")
    ids = [
        *_raw_ids(data.get("gear", ())),
        *_raw_ids(data.get("equipment", {})),
        *(_raw_ids(pending.get("gear", ())) if isinstance(pending, dict) else []),
    ]
    origin = {
        "owner": owner,
        "owner_name": name if isinstance(name, str) else owner,
        "source": "legacy",
        "source_zh": "舊存檔",
        "at": 0,
        "bound": "legacy",
    }
    return {item: dict(origin) for item in sorted(set(ids))}


class TimedFlag(_Model):
    """限時的世界旗標（Phase 5B-4c）：``until``（UTC 秒）以前有效。"""

    flag: str = Field(pattern=ID_PATTERN)
    until: int = Field(ge=0)


class ShadowSnapshot(_Model):
    """一個角色最後一次在城鎮整備時存下的影子（Phase 5C-2；09 9.6.10 #102）。

    借用時整份複製進招募者的角色（:attr:`CharacterState.shadows`），開戰時再照招募者壓強度上限
    （:mod:`trpg.world.shadows`，#87）。"""

    owner: str = Field(pattern=ID_PATTERN)
    """影子主人的角色 ID。"""
    hero: UnitTemplate
    """主角範本：名稱、屬性、武器、裝備中的技能與反應規則、基礎 HP。"""
    level: int = Field(ge=1)
    skill_tier: int | None = Field(default=None, ge=1)
    attribute_points: int = Field(default=0, ge=0)
    """還沒分配的屬性點（強度上限先扣這些）。"""
    attribute_spent: dict[Attribute, int] = Field(default_factory=dict)
    skills: tuple[SkillDef, ...] = ()
    """裝備中、不在內容庫的技能定義（依 ID 排序）。"""
    ai_profile: str | None = Field(default=None, pattern=ID_PATTERN)
    """主人設定的預設打法（#102）；``None``＝範本的 ``ai_profile``。"""
    equipment: dict[str, ItemDef] = Field(default_factory=dict)
    """存影子時穿的裝備（欄位 → 物品；Phase 5D-2，20.5）。借用時物品等級超過招募者等級的不穿。"""
    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    saved_at: int = Field(ge=0)

    @model_validator(mode="before")
    @classmethod
    def _drop_legacy_gear(cls, data: object) -> object:
        """舊存檔的 ``gear``（5C-2 預留的裝備欄位，5D-2 起改用 ``equipment``、從沒寫過值）讀入時
        忽略（5D-R1 刪掉這個死欄位）。"""
        if isinstance(data, dict) and "gear" in data:
            return {k: v for k, v in data.items() if k != "gear"}
        return data

    @field_validator("attribute_spent")
    @classmethod
    def _sorted_spent(cls, spent: dict[Attribute, int]) -> dict[Attribute, int]:
        return dict(sorted(spent.items()))


class ShadowReport(_Model):
    """影子被借用的戰報（#102；每天第一次）。"""

    day: int = Field(ge=0)
    at: int = Field(ge=0)
    borrower: str = Field(pattern=ID_PATTERN)
    borrower_name: str
    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    won: bool
    foes: tuple[str, ...] = ()
    """敵方單位（範本或變體 ID，依陣容順序）。"""
    coins: int = Field(default=0, ge=0)


class ShadowRecord(_Model):
    """世界上一個角色的影子與被借用的紀錄（5C-2）。"""

    snapshot: ShadowSnapshot
    coins: int = Field(default=0, ge=0)
    """被借用累計的任務幣（5D 任務幣做好後轉入主人角色）。"""
    reward_day: int | None = Field(default=None, ge=0)
    """最後一次給獎的日子（``refresh_day``）。"""
    reports: tuple[ShadowReport, ...] = ()
    """最近的戰報（新的在後）。"""
    coins_claimed: int = Field(default=0, ge=0)
    """已轉進主人角色的任務幣（Phase 5D-1；``coins`` 保留為累計）。"""


class LeagueEntry(_Model):
    """影子循環賽的一筆報名（Phase 5F-4；09 9.7、#100 每個帳號 1 個角色）。快照是報名當下的 build
    （:func:`~trpg.world.shadows.shadow_snapshot`），對戰時再拉到等級上限（:mod:`trpg.world.league`）。"""

    account: str = Field(min_length=1, max_length=80)
    """報名的帳號（世界日誌的 ``actor``；沒有帳號時＝角色 ID）。"""
    character_id: str = Field(pattern=ID_PATTERN)
    name: str
    """報名時的角色名。"""
    snapshot: ShadowSnapshot
    ai: str | None = Field(default=None, pattern=ID_PATTERN)
    """報名的 AI 打法（``None``＝快照的預設打法）。"""
    allocation: dict[Attribute, int] | None = None
    """（5F-4b，#32）報名時的屬性點重新分配（拉到上限後全部可配的點；``None``＝照自動配點）。"""
    entered_at: int = Field(ge=0)
    """第一次報名的 UTC 秒（更新不改；排名同分時報名較早的在前）。"""


class DailyActivity(_Model):
    """某個刷新日有成功世界動作的帳號（Phase 5F-1，Q15；世界事件門檻依前一天的人數調整）。"""

    day: int
    actors: tuple[str, ...] = ()
    """帳號 ID（沒有帳號時用角色 ID；排序、不重複）。"""
    characters: dict[str, str] = Field(default_factory=dict)
    """有動作的角色 ID → 武器大類（Phase 6T-1a，#135：隔天 6 點算主手大類比例；依 ID 排序）。"""

    @field_validator("characters")
    @classmethod
    def _sorted_characters(cls, rows: dict[str, str]) -> dict[str, str]:
        return dict(sorted(rows.items()))

    @field_validator("actors")
    @classmethod
    def _sorted_actors(cls, actors: tuple[str, ...]) -> tuple[str, ...]:
        if list(actors) != sorted(set(actors)):
            raise ValueError("actors 必須排序且不重複")
        return actors


class TargetAdjustment(_Model):
    """世界事件門檻的一次調整（#103、Q14；可查證：依前一天的上線人數）。"""

    day: int
    """哪個刷新日調的。"""
    players: int | None = Field(ge=0)
    """前一天的上線帳號數；``None``＝沒有前一天的資料（用原門檻）。"""
    target: int = Field(ge=1)


class WorldEventState(_Model):
    """一個世界事件的全服進度（Phase 5F-1，#103）。"""

    id: str = Field(pattern=ID_PATTERN)
    status: Literal["active", "succeeded", "failed"] = "active"
    progress: int = Field(default=0, ge=0)
    target: int = Field(ge=1)
    adjustments: tuple[TargetAdjustment, ...] = ()
    """門檻的調整紀錄（依日期）。"""
    resolved_day: int | None = None
    """成功或失敗的刷新日。"""
    resolved_at: int | None = None
    """成功或失敗的 UTC 秒數（換日時判定的＝該刷新日開始；5F-1b「你不在的時候」用；舊存檔
    ``None``＝用 ``resolved_day`` 的開始）。"""


class BountyClaim(_Model):
    """某天某張懸賞被誰搶下（Phase 5F-1；09 9.7「先搶先贏」）。"""

    day: int
    bounty: str = Field(pattern=ID_PATTERN)
    character_id: str = Field(pattern=ID_PATTERN)
    name: str
    """搶下的角色名（顯示用）。"""
    at: int = Field(ge=0)


class BossAttempt(_Model):
    """某個帳號在某個刷新日挑戰賽季 Boss 的次數（Phase 5F-3；#100 算帳號）。"""

    day: int
    actor: str = Field(min_length=1)
    """帳號 ID（沒有帳號時＝角色 ID，同 Q15）。"""
    count: int = Field(ge=1)


class BossClear(_Model):
    """一次打倒賽季 Boss（Phase 5F-3；依日誌順序）。第一筆就是本季首殺（#101）。"""

    character_id: str = Field(pattern=ID_PATTERN)
    name: str
    """當下的角色名（顯示用）。"""
    at: int = Field(ge=0)
    score: int = Field(ge=0)
    rounds: int = Field(ge=0)


class DailyGoalProgress(_Model):
    """角色今天的今日目標進度（Phase 5F-1，#99；跨日歸零）。"""

    day: int
    progress: dict[str, int] = Field(default_factory=dict)
    """目標 ID → 次數（依鍵排序）。"""
    done: tuple[str, ...] = ()
    """已完成、已給任務幣的目標（排序）。"""

    @field_validator("progress")
    @classmethod
    def _sorted_progress(cls, progress: dict[str, int]) -> dict[str, int]:
        return dict(sorted(progress.items()))

    @field_validator("done")
    @classmethod
    def _sorted_done(cls, done: tuple[str, ...]) -> tuple[str, ...]:
        if list(done) != sorted(set(done)):
            raise ValueError("done 必須排序且不重複")
        return done


class WorldState(_Model):
    """共享的世界快照（``trpg-world/4``；``/1``～``/3`` 照讀）。世界的變化由世界動作日誌重播得到，
    快照只是快取。"""

    format: Literal["trpg-world/4"] = WORLD_FORMAT

    @model_validator(mode="before")
    @classmethod
    def _upgrade_world(cls, data: object) -> object:
        """``trpg-world/1``～``/3`` → ``trpg-world/4``：只多了選填欄位（6C-1b、6C-R2、6T-1a），
        直接換版號。"""
        if isinstance(data, dict) and data.get("format") in LEGACY_WORLD_FORMATS:
            return {**data, "format": WORLD_FORMAT}
        return data

    season_id: str = Field(pattern=ID_PATTERN)
    season_seed: int = Field(ge=0, le=MASK64)
    season_start: int = Field(ge=0)
    """賽季開始的 UTC 秒數（5F-1 的日程用；本段只存）。"""
    flags: tuple[str, ...] = ()
    """世界旗標（排序、不重複）；地點的 ``unlock_flag`` 成立與否看這裡。"""
    cleared: tuple[ClearedLocation, ...] = ()
    """已清空的地點（依區域、地點排序；每個地點最多一筆）。寫入在 5A-4／5F-1。"""
    defeated_spawns: tuple[DefeatedSpawn, ...] = ()
    """實地地圖上被打贏的隊伍（6C-1b，21.10 第 9 條；所有人看得到；依區域、地點、索引排序、
    不重複）。"""
    threads: tuple[ThreadState, ...] = ()
    """世界級線頭（所有人的世界都看得到；5B-1 起）。"""
    timed_flags: tuple[TimedFlag, ...] = ()
    """限時的世界旗標（依旗標排序、不重複；Phase 5B-4c 世界級線頭的到期結局，例：之後 2 天）。"""
    shadows: tuple[ShadowRecord, ...] = ()
    """每個角色的影子（依主人 ID 排序、每人一筆；Phase 5C-2）。"""
    recipes: tuple[RecipeRecord, ...] = ()
    """打造過的配方與首位發現者（依配方碼排序、不重複；Phase 5D-3，M6）。"""

    # --- 5F-1 賽季日程（邏輯在 trpg.world.season_board） ---
    rolled_day: int | None = None
    """換日處理到的刷新日（``None``＝還沒處理過，從開賽日補）。"""
    activity: tuple[DailyActivity, ...] = ()
    """今天與昨天有動作的帳號（依日期排序）。"""
    world_events: tuple[WorldEventState, ...] = ()
    """開始過的世界事件（依 ID 排序）。"""
    bounty_claims: tuple[BountyClaim, ...] = ()
    """懸賞被搶下的紀錄（依日期、懸賞排序；每天每張最多一筆）。"""
    level_bonus: dict[str, int] = Field(default_factory=dict)
    """區域 → 建議等級加成（世界事件失敗，9.6.7 #15；依鍵排序）。"""
    shop_price: dict[str, int] = Field(default_factory=dict)
    """商店 → 買價加成‰（世界事件失敗，Phase 5F-5b；19.9 #2「餘燼集商店價格 +20% 到季末」；
    依鍵排序，季末重置清掉）。"""

    # --- 5F-3 賽季 Boss（邏輯在 trpg.world.season_boss） ---
    seal_keys: int = Field(default=0, ge=0)
    """全服累積的封印鑰匙（19.6.2）。"""
    seal_full_at: int | None = Field(default=None, ge=0)
    """封印鑰匙集滿（解鎖旗標第一次出現）的 UTC 秒；``None``＝還沒集滿。"""
    boss_attempts: tuple[BossAttempt, ...] = ()
    """今天各帳號挑戰賽季 Boss 的次數（依帳號排序；換日後的第一次挑戰清掉舊的）。"""
    boss_clears: tuple[BossClear, ...] = ()
    """這一季打倒賽季 Boss 的紀錄（依日誌順序；第一筆＝首殺）。"""

    def boss_attempts_of(self, day: int, actor: str) -> int:
        """``actor`` 在刷新日 ``day`` 已挑戰的次數。"""
        found = next((a for a in self.boss_attempts if a.day == day and a.actor == actor), None)
        return 0 if found is None else found.count

    # --- 5F-4 影子循環賽（邏輯在 trpg.world.league） ---
    league_entries: tuple[LeagueEntry, ...] = ()
    """循環賽的報名（依帳號排序；帳號、角色都不重複）。"""

    # --- 6T-1a 交易與主手大類（邏輯在 trpg.world.trade、trpg.world.weapon_mix） ---
    trades: tuple[TradeRecord, ...] = ()
    """這一季的交易帳（依寄出順序；信件 ID 不重複）。"""
    weapon_mix: WeaponMix | None = None
    """今天的主手大類比例（每天 6 點算一次，#135）；``None``＝還沒算過（平均分）。"""

    @field_validator("trades")
    @classmethod
    def _trades_unique(cls, trades: tuple[TradeRecord, ...]) -> tuple[TradeRecord, ...]:
        if len({t.id for t in trades}) != len(trades):
            raise ValueError("trades 的信件 ID 重複")
        return trades

    def trade(self, letter: str) -> TradeRecord | None:
        return next((t for t in self.trades if t.id == letter), None)

    @field_validator("league_entries")
    @classmethod
    def _league_sorted(cls, entries: tuple[LeagueEntry, ...]) -> tuple[LeagueEntry, ...]:
        accounts = [e.account for e in entries]
        if accounts != sorted(set(accounts)):
            raise ValueError("league_entries 必須依帳號排序且不重複")
        if len({e.character_id for e in entries}) != len(entries):
            raise ValueError("league_entries 的角色重複")
        return entries

    @field_validator("level_bonus", "shop_price")
    @classmethod
    def _sorted_bonus(cls, bonus: dict[str, int]) -> dict[str, int]:
        return dict(sorted(bonus.items()))

    @field_validator("bounty_claims")
    @classmethod
    def _claims_sorted(cls, claims: tuple[BountyClaim, ...]) -> tuple[BountyClaim, ...]:
        keys = [(c.day, c.bounty) for c in claims]
        if keys != sorted(set(keys)):
            raise ValueError("bounty_claims 必須依日期、懸賞排序且不重複")
        return claims

    @field_validator("world_events")
    @classmethod
    def _events_sorted(cls, events: tuple[WorldEventState, ...]) -> tuple[WorldEventState, ...]:
        ids = [e.id for e in events]
        if ids != sorted(set(ids)):
            raise ValueError("world_events 必須依 ID 排序且不重複")
        return events

    def claim_of(self, day: int, bounty: str) -> BountyClaim | None:
        return next((c for c in self.bounty_claims if c.day == day and c.bounty == bounty), None)

    def world_event(self, event_id: str) -> WorldEventState | None:
        return next((e for e in self.world_events if e.id == event_id), None)

    @model_validator(mode="before")
    @classmethod
    def _recipes_default_season(cls, data: object) -> object:
        """舊存檔的配方沒有 ``season_id``：補成世界當季（Phase 5D-R2）。"""
        if not isinstance(data, dict):
            return data
        season = data.get("season_id")
        recipes = data.get("recipes")
        if not isinstance(season, str) or not isinstance(recipes, list | tuple):
            return data
        filled = [
            {**r, "season_id": season} if isinstance(r, dict) and "season_id" not in r else r
            for r in recipes
        ]
        return {**data, "recipes": filled}

    @field_validator("recipes")
    @classmethod
    def _recipes_sorted(cls, recipes: tuple[RecipeRecord, ...]) -> tuple[RecipeRecord, ...]:
        codes = [r.code for r in recipes]
        if codes != sorted(set(codes)):
            raise ValueError("recipes 必須依配方碼排序且不重複")
        return recipes

    def recipe_of(self, code: str) -> RecipeRecord | None:
        return next((r for r in self.recipes if r.code == code), None)

    @field_validator("shadows")
    @classmethod
    def _shadows_sorted(cls, shadows: tuple[ShadowRecord, ...]) -> tuple[ShadowRecord, ...]:
        owners = [s.snapshot.owner for s in shadows]
        if owners != sorted(set(owners)):
            raise ValueError("shadows 必須依主人 ID 排序且每人一筆")
        return shadows

    def shadow_of(self, owner: str) -> ShadowRecord | None:
        return next((s for s in self.shadows if s.snapshot.owner == owner), None)

    @field_validator("timed_flags")
    @classmethod
    def _timed_sorted(cls, flags: tuple[TimedFlag, ...]) -> tuple[TimedFlag, ...]:
        names = [f.flag for f in flags]
        if names != sorted(set(names)):
            raise ValueError("timed_flags 必須依旗標排序且不重複")
        return flags

    def active_flags(self, now: int) -> tuple[str, ...]:
        """``now`` 有效的世界旗標：``flags`` 加上還沒過期的 ``timed_flags``（排序）。"""
        timed = (f.flag for f in self.timed_flags if f.until > now)
        return tuple(sorted({*self.flags, *timed}))

    @field_validator("flags")
    @classmethod
    def _flags_sorted(cls, flags: tuple[str, ...]) -> tuple[str, ...]:
        if list(flags) != sorted(set(flags)):
            raise ValueError("flags 必須排序且不重複")
        return flags

    @field_validator("cleared")
    @classmethod
    def _cleared_sorted(cls, cleared: tuple[ClearedLocation, ...]) -> tuple[ClearedLocation, ...]:
        keys = [(c.region, c.location) for c in cleared]
        if keys != sorted(set(keys)):
            raise ValueError("cleared 必須依區域、地點排序且不重複")
        return cleared

    @field_validator("defeated_spawns")
    @classmethod
    def _spawns_sorted(cls, spawns: tuple[DefeatedSpawn, ...]) -> tuple[DefeatedSpawn, ...]:
        keys = [s.key() for s in spawns]
        if keys != sorted(set(keys)):
            raise ValueError("defeated_spawns 必須依區域、地點、索引排序且不重複")
        return spawns

    @field_validator("threads")
    @classmethod
    def _world_threads(cls, threads: tuple[ThreadState, ...]) -> tuple[ThreadState, ...]:
        return _check_threads(threads)

    def has_flag(self, flag: str) -> bool:
        return flag in self.flags

    def is_cleared(self, region: str, location: str, now: int) -> bool:
        """``location`` 現在是否「已清空」（還沒到重生時間）。"""
        return any(
            c.region == region and c.location == location and now < c.respawn_at
            for c in self.cleared
        )

    def spawn_generation(self, region: str, location: str, spawn: int) -> int:
        """實地地圖上第 ``spawn`` 隊的重生世代（被打贏過幾次；沒打贏過＝0；6C-R2）。"""
        return next(
            (s.wins for s in self.defeated_spawns if s.key() == (region, location, spawn)), 0
        )

    def spawn_defeated(self, region: str, location: str, spawn: int, now: int) -> bool:
        """實地地圖上的第 ``spawn`` 隊現在是否被打贏、還沒重生（6C-1b）。"""
        return any(
            s.key() == (region, location, spawn) and now < s.respawn_at
            for s in self.defeated_spawns
        )


class CharacterState(_Model):
    """一個角色在大世界的狀態（``trpg-char/15``；``trpg-char/1``～``/14`` 照讀）。"""

    format: Literal["trpg-char/15"] = CHAR_FORMAT

    @model_validator(mode="before")
    @classmethod
    def _upgrade_format(cls, data: object) -> object:
        """``trpg-char/1``～``/14`` → ``trpg-char/15``：只多了選填欄位（6B-2、6C-1、6C-2、6C-6、
        6C-5、6D-R2 的 ``field_visit.generations``、6F-4 的提示紀錄、6L-2 的 ``skill_regions``、
        6T-1a 的 ``gear_origin``、``mailbox``、6R-1 的 ``free_race_change_used``、6R-2 的
        ``hero.doll.custom``、TR-1 的 ``opening``：沒有＝已完成開局；OB-1 的 ``opening`` 新欄位：
        ``/12`` 靶場中的角色取預設 ``stage="pick_class"``，走 #150 新流程；WP-1 的 ``wish_week``、
        ``PendingOffer.refund``：沒有＝本週沒許過願；RG-2 的 ``EncounterResult.duel``：沒有＝沒有
        提出單挑），直接換版號；
        ``/6`` 以前的存檔沒有 ``level_seen``，補成目前等級（舊角色不跳升級畫面）。6T-1a：``/8``
        以前的存檔已有的裝備（背包、穿戴中、等著決定的戰利品）不知道穿過沒有，保守起見一律記成
        綁定（``bound: legacy``），不能交易（``/9`` 起已經有來歷，不重算）。"""
        if isinstance(data, dict) and data.get("format") in LEGACY_CHAR_FORMATS:
            old = data.get("format")
            upgraded = {**data, "format": CHAR_FORMAT}
            if "level_seen" not in upgraded and isinstance(upgraded.get("level"), int):
                upgraded["level_seen"] = upgraded["level"]
            if "gear_origin" not in upgraded and old not in _ORIGIN_FORMATS:
                upgraded["gear_origin"] = _legacy_origins(upgraded)
            return upgraded
        return data

    character_id: str = Field(pattern=ID_PATTERN)
    hero: UnitTemplate
    origin: str | None = None
    level: int = Field(ge=1)
    xp: int = Field(ge=0)
    hp: int = Field(ge=0)
    mana: int = Field(ge=0)
    stamina: int | None = Field(default=None, ge=0)
    """目前耐力；``None``＝滿（同 ``RunState``）。"""
    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    supplies: int = Field(ge=0)
    revealed: tuple[LocationRef, ...] = ()
    """這個角色發現的隱藏地點（依區域、地點排序、不重複）。"""
    perception_marks: tuple[PerceptionMark, ...] = ()
    """每個隱藏地點最後一次感知判定的日子（依區域、地點排序、每地點一筆）。"""
    rng_counters: dict[str, int] = Field(default_factory=dict)
    """亂數串流 → 已用次數（依鍵排序；2.4 的 ``counter``）。"""
    pending_encounter: EncounterResult | None = None
    """還沒處理的遭遇；有它時不能移動或紮營（5A-4 開戰後清掉）。"""
    camped_at: LocationRef | None = None
    """目前紮營中的地點（營火；移動就清掉）。"""
    bench: tuple[str, ...] = ()
    """備用技能（學會但沒裝上的，排序；同 ``RunState.bench``）。換技能在城鎮與營火（5A-4）。"""
    fatigued: bool = False
    """疲憊（9.6.9 #98）：全滅後的下一場開場 HP 打折，打完一場就消失（5A-4）。"""
    attribute_points: int = Field(default=0, ge=0)
    """升級給的、還沒分配的屬性點（5A-4 只累積；分配之後再做）。"""
    visited_towns: tuple[str, ...] = ()
    """到過小鎮的區域 ID（排序、不重複）；城鎮之間的傳送只能去這些區（5A-4）。"""

    @field_validator("bench", "visited_towns")
    @classmethod
    def _sorted_ids(cls, ids: tuple[str, ...]) -> tuple[str, ...]:
        if list(ids) != sorted(set(ids)):
            raise ValueError("bench／visited_towns 必須排序且不重複")
        return ids

    event_steps: int = Field(default=0, ge=0)
    """距離上次事件走了幾步（事件出現機率用；5B-1）。"""
    pending_event: EventTrigger | None = None
    """觸發了、還沒處理的事件（5B-1；不擋移動，離開地點就作罷）。"""
    threads: tuple[ThreadState, ...] = ()
    """個人線頭（只屬於自己；5B-1 起）。"""
    next_battle: tuple[NextBattleMod, ...] = ()
    """下一場戰鬥帶的修正（情境判定的獎懲，5B-2 起；依產生順序）。5A-6 起開戰時套用，打完一場
    （勝負都算）清空。"""

    # --- 5A-6 成長（和 RunState 同名同型別；邏輯在 trpg.world.growth） ---
    insight: int = Field(default=0, ge=0)
    """還沒花掉的靈感點（06 6.34.2 大世界：每升 1 級、每種精英首殺…；一般戰鬥不給）。"""
    flash: dict[str, SkillFlash] = Field(default_factory=dict)
    """每招學會的技能的閃現狀態（目前的技能 ID → 狀態；依 ID 排序）。"""
    flash_bases: tuple[SkillDef, ...] = ()
    """閃現過的生成技能的原本定義（依 ID 排序）。"""
    pending_flash: PendingFlash | None = None
    """已付點、還沒選的閃現選項；有它時只能送 ``flash_pick``。"""
    skill_usage: dict[str, SkillUsage] = Field(default_factory=dict)
    """每招技能的用法統計（閃現選項依它排序；依 ID 排序）。"""
    skill_tier: int | None = Field(default=None, ge=1)
    """主角技能目前照哪一階的預算配數值（07 7.6 的角色階級；``None`` ＝ 5A-6 以前的角色，下次升級時
    照角色階級重配一次）。"""
    attribute_spent: dict[Attribute, int] = Field(default_factory=dict)
    """分配出去（重配時退回）的屬性點（同 ``RunState``；新角色開局的點數不在內）。"""
    elite_kills: tuple[str, ...] = ()
    """首殺過的精英種類（排序、不重複；06 6.34.2「每種精英的首殺各 1 點」）。"""
    oath: OathState | None = None
    """目前的誓約（同時 1 個，#106）。"""
    oath_broken_next: bool = False
    """上一場戰鬥結束才判出的違反（每場擊殺／施加狀態沒達到）：破誓 2 回合帶到下一場開場（5C-3b；
    下一場的誓約加成照常）。下一場打完（勝負都算）重新判定，解除或換誓約也清掉。"""
    oath_cooldown_until: int = Field(default=0, ge=0)
    """解除誓約後，這個時間（UTC 秒）以前不能再立（#106「現實 1 天」）。"""
    last_battle: LastBattle | None = None
    """最近一次戰鬥的結果（Phase 5A-7；``fight`` 寫入，其他動作不清除）。"""

    # --- 5B-4 任務與好感度（邏輯在 trpg.world.quests、trpg.world.affinity） ---
    quests: tuple[QuestState, ...] = ()
    """接過的任務（依任務 ID 排序、不重複）。"""
    affinity: dict[str, int] = Field(default_factory=dict)
    """NPC → 好感度（依 NPC 排序；沒有的 NPC＝0，9.6.11 #116）。"""
    pending_offers: tuple[PendingOffer, ...] = ()
    """任務給的、還沒選的技能三選一（依產生順序）；有它時只能送 ``offer_pick``。"""
    offers_made: int = Field(default=0, ge=0)
    """產生過幾組技能候選（候選種子的計數，同 ``RunState.offers_made``）。"""
    story_flags: tuple[str, ...] = ()
    """劇情旗標（排序、不重複；例：解鎖導師任務鏈）。"""

    # --- 5B-4b 好感度取得、祕密事件 ---
    talk_days: dict[str, int] = Field(default_factory=dict)
    """NPC → 最後一次 ``talk`` 的日子（``refresh_day``；每天第一次聊天加好感度，18.7.6）。"""
    unlocked_skeletons: tuple[str, ...] = ()
    """解鎖的 ``unlock_only`` 事件骨架（排序、不重複；信賴的 NPC 說出祕密時，18.7.7）。"""

    # --- 5B-4c 機遇、只出一次的骨架 ---
    opportunities: tuple[str, ...] = ()
    """拿過機遇技能的骨架（排序、不重複；同一個機遇每個角色只能拿一次，代決 5B4c-5）。"""
    opportunity_tier_ups: int = Field(default=0, ge=0)
    """機遇給過幾次高 1 階的三選一（07 7.6：每人每季最多 1 次；角色一季一份）。"""
    finished_skeletons: tuple[str, ...] = ()
    """解決過的 ``once`` 骨架（排序、不重複；18.4 補充「骨架 22 每個角色只出現到解決為止」）。"""

    # --- 5B-4d 骨架 22 失敗可再試、機遇保底 ---
    failed_skeletons: dict[str, int] = Field(default_factory=dict)
    """判定失敗的 ``once`` 骨架 → 失敗那天（``refresh_day``；依骨架排序）。當天不再出現，隔天
    （6 點刷新後）可以再試（18.7.6「失敗隔天可再試」）。"""
    met_opportunities: tuple[str, ...] = ()
    """觸發過的機遇骨架（有 ``opportunity`` 解法的骨架；排序、不重複；07 7.6 第 7 天前保底）。"""

    # --- 5B-4f 機遇提示一天一次 ---
    opportunity_hint_day: int | None = None
    """最後一次聽到機遇提示的日子（``refresh_day``；``None``＝沒聽過）。同一天（6 點刷新為界）
    不再提（玩法 PM 2026-11-03 代決）。"""

    # --- 5C-1 隊伍（邏輯在 trpg.world.party） ---
    mercenaries: tuple[str, ...] = ()
    """隊伍裡的系統傭兵（依選擇順序＝出場順序、不重複）。5C-2 起沒有隊友＝獨行（玩法 PM 定 ③）。"""

    # --- 5C-2 影子與打法（邏輯在 trpg.world.party、trpg.world.shadows） ---
    shadows: tuple[ShadowSnapshot, ...] = ()
    """隊伍裡借來的影子（借用當下的複本，依選擇順序；排在傭兵之後出場）。"""
    party_ai: dict[str, str] = Field(default_factory=dict)
    """隊伍成員（傭兵 ID 或影子主人 ID）→ 選的 AI 打法（依鍵排序；沒有＝預設）。"""
    shadow_ai: str | None = Field(default=None, pattern=ID_PATTERN)
    """自己影子的預設打法（#102；``None``＝範本的）。"""

    # --- 5C-3 劇情夥伴（邏輯在 trpg.world.companions） ---
    companions: tuple[str, ...] = ()
    """隊伍裡的劇情夥伴（只在對應任務裡跟著，佔一個隊友位；#97）。依加入順序，排在傭兵、影子之後出場。"""
    companion_bench: tuple[CompanionBench, ...] = ()
    """夥伴加入時替下的成員（任務結束時還原；玩家自己 ``hire`` 就清掉）。"""
    companion_affinity: dict[str, CompanionAffinity] = Field(default_factory=dict)
    """夥伴 → 今天「帶他打贏」加過的好感度（每天上限，18.7.6）。"""

    # --- 5D-1 貨幣、背包、腰包、商店（邏輯在 trpg.world.economy） ---
    gold: int = Field(default=0, ge=0)
    """金幣（08 8.15：戰鬥、出售物品 → 買消耗品…）。"""
    quest_coins: int = Field(default=0, ge=0)
    """任務幣（8.15：任務、懸賞、世界事件；影子被借用的任務幣也轉進來）。"""
    bag: dict[str, int] = Field(default_factory=dict)
    """背包：物品 → 個數（依 ID 排序；30 格照每種物品的疊數算，8.17）。"""
    pouch: dict[str, int] = Field(default_factory=dict)
    """腰包：消耗品 → 個數（依 ID 排序；合計最多 3 個，戰鬥中當道具用，8.17）。"""
    shop_week: tuple[ShopPurchase, ...] = ()
    """本週買過的限量商品（依店、物品排序）。"""
    shop_affinity: dict[str, CompanionAffinity] = Field(default_factory=dict)
    """店主 NPC → 今天在店裡消費加過的好感度（18.7.6：柳掌櫃每天最多 +4）。"""

    # --- 5D-2 掉落與裝備（邏輯在 trpg.world.loot、trpg.world.gear） ---
    gear: tuple[ItemDef, ...] = ()
    """背包裡的裝備（依取得順序；每件佔背包 1 格，8.17）。"""
    equipment: dict[str, ItemDef] = Field(default_factory=dict)
    """穿戴中的裝備（欄位 → 物品；空＝主角範本的裝備，同 ``RunState.equipment``）。"""
    pending_loot: PendingLoot | None = None
    """背包滿了、等戰後結算選要丟哪件的戰利品（5D-2b；``None``＝沒有）。舊存檔沒有這個欄位照讀。"""

    # --- 5D-3 鐵匠與附魔台（邏輯在 trpg.world.crafting） ---
    gear_mods: dict[str, GearMod] = Field(default_factory=dict)
    """打造、強化、重骰、指定過的裝備（物品 ID → 紀錄；依 ID 排序）。"""
    crafts: int = Field(default=0, ge=0)
    """打造過幾件（打造品 ID 的流水號，同配方打兩件不撞 ID）。"""

    # --- 5F-1 今日目標（邏輯在 trpg.world.season_board） ---
    daily_goals: DailyGoalProgress | None = None
    """今天的今日目標進度（``None``＝還沒有；跨日歸零）。"""
    bounty_days: dict[str, int] = Field(default_factory=dict)
    """懸賞 → 最後一次打懸賞陣容的刷新日（5F-1b：每個角色每天在該地點的第一場遭遇才是懸賞陣容）。"""
    news_seen_at: int | None = None
    """「你不在的時候」摘要看到哪個時刻為止（UTC 秒；``news_seen`` 動作寫入，5F-1b）。新角色＝建立
    當下；``None``＝舊存檔（從開賽算起）。"""

    # --- 5F-3 封印鑰匙、區域 Boss 的保底掉落 ---
    seal_key_sources: tuple[str, ...] = ()
    """已拿過封印鑰匙的來源（排序、不重複；個人鑰匙數＝長度，19.6.2）。"""
    boss_drop_days: dict[str, int] = Field(default_factory=dict)
    """區域 Boss（單位 ID）→ 最後一次拿保底掉落的刷新日（每角色每刷新日一次，代決 5F3-15；
    依鍵排序）。"""

    # --- 6B-2 實地地圖上的位置（邏輯在 trpg.world.field） ---
    field: FieldPos | None = None
    """實地地圖上的位置；一定屬於 ``location`` 的實地地圖或它的室內圖。``None``＝舊存檔，或所在
    地點沒有實地地圖（照舊用 ``travel`` 移動）。"""
    teleport_stones: tuple[str, ...] = ()
    """走到過、已解鎖的傳送石 ID（排序、不重複；21.2）。"""
    # --- 6C-1 看得見的敵人（邏輯在 trpg.world.field_enemies） ---
    field_visit: FieldVisit | None = None
    """這一趟待在所在地點的實地地圖（巡邏進度、陣容種子、打贏的隊伍）；所在地點沒有實地地圖＝
    ``None``。"""
    # --- 6C-6 區域圖的戰爭迷霧（21.1） ---
    visited_locations: tuple[LocationRef, ...] = ()
    """走進過的地點（依區域、地點排序、不重複）。每個動作之後把所在地點記進來
    （:func:`trpg.world.town.with_visited_location`）；舊存檔是空的，畫面另外把目前位置與到過的
    小鎮當作去過。"""
    # --- 6C-5 地圖上的東西（邏輯在 trpg.world.field_things） ---
    field_event: FieldEventMark | None = None
    """地圖上還沒碰到的事件「！」；屬於所在地點，換地點就消失。"""
    sneaking: bool = False
    """潛行中（Q7：花補給開啟，持續到進入下一張地圖；敵人視野減半）。"""
    object_uses: tuple[ObjectUse, ...] = ()
    """用情境物件開事件的紀錄（依地圖、物件排序；每個物件每天一次）。"""

    # ---- 提示與教學的紀錄（Phase 6F-4，6F-2b；記在角色身上，不用本機儲存） ----
    hints_seen: tuple[str, ...] = ()
    """出過的提示 ID（排序、不重複）：戰鬥短提示的 ID、``opening``（開場）、``lesson:<種類>``
    （教學：``allocate``、``flash``、``reflash``）。「重新顯示提示」清空。"""
    hints_off: bool = False
    """「不再顯示提示」：戰鬥短提示全部不出。「重新顯示提示」清掉。"""
    level_seen: int = Field(default=1, ge=1)
    """看過升級畫面的等級（升級畫面在 ``level > level_seen`` 時出）。"""

    # ---- 技能的取得地點（Phase 6L-2，#126） ----
    skill_regions: dict[str, str] = Field(default_factory=dict)
    """學到的技能（取得時的技能 ID）→ 取得地點的區域。閃現的變化名照原技能的界域
    （:func:`trpg.world.growth.skill_region`）；沒有紀錄（創角、舊存檔）＝中性。"""

    # ---- 交易共同前置與郵寄（Phase 6T-1a，08 8.16、#136；邏輯在 trpg.world.trade） ----
    gear_origin: dict[str, GearOrigin] = Field(default_factory=dict)
    """持有的裝備（背包、穿戴中、等著決定的戰利品；物品 ID）→ 來歷與綁定（依 ID 排序）。每個動作
    之後補上新拿到的、標上穿過的、刪掉不在身上的（:func:`trpg.world.trade.stamp_gear`）。"""
    mailbox: tuple[MailLetter, ...] = ()
    """信箱：寄給自己的信與被拒收退回來的信（依信件 ID 排序、不重複）。"""

    # ---- 換種族（Phase 6R-1，#138；邏輯在 trpg.world.race_change） ----
    free_race_change_used: bool = False
    """這一季用過免費換種族（#138：舊狐族改成獸耳族，本季開放一次，不佔 #108 那一次）。"""

    # ---- 開局在主城工坊靶場（Phase TR-1，#134；邏輯在 trpg.world.opening） ----
    opening: OpeningState | None = None
    """未完成開局（在主城工坊靶場，還沒按「確定出發」）；``None``＝已完成（舊角色一律是）。這段期間
    主角拿的是佔位武器、沒有技能，只能做 ``opening_confirm`` 與只記畫面紀錄的動作。"""

    # ---- 許願池（Phase WP-1，07 7.6、#88；邏輯在 trpg.world.wish） ----
    wish_week: WishWeek | None = Field(default=None, exclude_if=lambda v: v is None)
    """最近一次許願那週的次數（每週 2 次；``None``＝沒許過願）。"""

    @field_validator("gear_origin")
    @classmethod
    def _sorted_gear_origin(cls, rows: dict[str, GearOrigin]) -> dict[str, GearOrigin]:
        return dict(sorted(rows.items()))

    @field_validator("mailbox")
    @classmethod
    def _sorted_mailbox(cls, letters: tuple[MailLetter, ...]) -> tuple[MailLetter, ...]:
        ids = [m.id for m in letters]
        if ids != sorted(set(ids)):
            raise ValueError("mailbox 必須依信件 ID 排序且不重複")
        return letters

    @field_validator("hints_seen")
    @classmethod
    def _hints_sorted(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if list(value) != sorted(set(value)):
            raise ValueError("hints_seen 要排序且不重複")
        return value

    @field_validator("object_uses")
    @classmethod
    def _sorted_object_uses(cls, uses: tuple[ObjectUse, ...]) -> tuple[ObjectUse, ...]:
        keys = [(u.map, u.object) for u in uses]
        if keys != sorted(set(keys)):
            raise ValueError("object_uses 必須依地圖、物件排序且不重複")
        return uses

    @field_validator("teleport_stones")
    @classmethod
    def _sorted_stones(cls, ids: tuple[str, ...]) -> tuple[str, ...]:
        if list(ids) != sorted(set(ids)):
            raise ValueError("teleport_stones 必須排序且不重複")
        return ids

    @field_validator("seal_key_sources")
    @classmethod
    def _sorted_key_sources(cls, sources: tuple[str, ...]) -> tuple[str, ...]:
        if list(sources) != sorted(set(sources)):
            raise ValueError("seal_key_sources 必須排序且不重複")
        return sources

    @field_validator("boss_drop_days")
    @classmethod
    def _sorted_drop_days(cls, days: dict[str, int]) -> dict[str, int]:
        return dict(sorted(days.items()))

    @field_validator("gear_mods")
    @classmethod
    def _sorted_gear_mods(cls, mods: dict[str, GearMod]) -> dict[str, GearMod]:
        return dict(sorted(mods.items()))

    @field_validator("bag", "pouch")
    @classmethod
    def _sorted_counts(cls, counts: dict[str, int]) -> dict[str, int]:
        return _check_counts(counts)

    @field_validator("shop_week")
    @classmethod
    def _sorted_shop_week(cls, rows: tuple[ShopPurchase, ...]) -> tuple[ShopPurchase, ...]:
        keys = [(r.shop, r.item) for r in rows]
        if keys != sorted(set(keys)):
            raise ValueError("shop_week 必須依店、物品排序且不重複")
        return rows

    @field_validator("shop_affinity")
    @classmethod
    def _sorted_shop_affinity(
        cls, rows: dict[str, CompanionAffinity]
    ) -> dict[str, CompanionAffinity]:
        return dict(sorted(rows.items()))

    @field_validator("party_ai")
    @classmethod
    def _sorted_party_ai(cls, ai: dict[str, str]) -> dict[str, str]:
        return dict(sorted(ai.items()))

    @field_validator("talk_days", "failed_skeletons", "bounty_days")
    @classmethod
    def _sorted_talk_days(cls, days: dict[str, int]) -> dict[str, int]:
        return dict(sorted(days.items()))

    @field_validator(
        "unlocked_skeletons", "opportunities", "finished_skeletons", "met_opportunities"
    )
    @classmethod
    def _sorted_unlocked(cls, ids: tuple[str, ...]) -> tuple[str, ...]:
        if list(ids) != sorted(set(ids)):
            raise ValueError("骨架清單必須排序且不重複")
        return ids

    @field_validator("quests")
    @classmethod
    def _sorted_quests(cls, quests: tuple[QuestState, ...]) -> tuple[QuestState, ...]:
        ids = [q.quest for q in quests]
        if ids != sorted(set(ids)):
            raise ValueError("quests 必須依任務 ID 排序且不重複")
        return quests

    @field_validator("affinity")
    @classmethod
    def _sorted_affinity(cls, affinity: dict[str, int]) -> dict[str, int]:
        return dict(sorted(affinity.items()))

    @field_validator("story_flags")
    @classmethod
    def _sorted_flags(cls, flags: tuple[str, ...]) -> tuple[str, ...]:
        if list(flags) != sorted(set(flags)):
            raise ValueError("story_flags 必須排序且不重複")
        return flags

    def quest_state(self, quest: str) -> QuestState | None:
        return next((q for q in self.quests if q.quest == quest), None)

    @field_validator("elite_kills")
    @classmethod
    def _sorted_kills(cls, kills: tuple[str, ...]) -> tuple[str, ...]:
        if list(kills) != sorted(set(kills)):
            raise ValueError("elite_kills 必須排序且不重複")
        return kills

    @field_validator("revealed", "visited_locations")
    @classmethod
    def _revealed_sorted(cls, refs: tuple[LocationRef, ...]) -> tuple[LocationRef, ...]:
        keys = [r.key() for r in refs]
        if keys != sorted(set(keys)):
            raise ValueError("revealed／visited_locations 必須依區域、地點排序且不重複")
        return refs

    @field_validator("perception_marks")
    @classmethod
    def _marks_sorted(cls, marks: tuple[PerceptionMark, ...]) -> tuple[PerceptionMark, ...]:
        keys = [(m.region, m.location) for m in marks]
        if keys != sorted(set(keys)):
            raise ValueError("perception_marks 必須依區域、地點排序且每地點一筆")
        return marks

    @field_validator("rng_counters")
    @classmethod
    def _counters(cls, counters: dict[str, int]) -> dict[str, int]:
        if any(v < 0 for v in counters.values()):
            raise ValueError("rng_counters 不可為負")
        return dict(sorted(counters.items()))

    generated_skills: tuple[SkillDef, ...] = ()
    """不在內容庫的技能（創角的組合器起始技能等；依 ID 排序，同 ``RunState.generated_skills``；
    5A-5；5A-6 起也含閃現、升階重配後的技能）。開戰時併進該場規則包、換技能認得它們。"""

    @field_validator("generated_skills")
    @classmethod
    def _generated_sorted(cls, skills: tuple[SkillDef, ...]) -> tuple[SkillDef, ...]:
        ids = [s.id for s in skills]
        if ids != sorted(set(ids)):
            raise ValueError("generated_skills 必須依 ID 排序且不重複")
        return skills

    @field_validator("threads")
    @classmethod
    def _char_threads(cls, threads: tuple[ThreadState, ...]) -> tuple[ThreadState, ...]:
        return _check_threads(threads)

    def has_revealed(self, region: str, location: str) -> bool:
        return any(r.region == region and r.location == location for r in self.revealed)

    def has_visited(self, region: str, location: str) -> bool:
        return any(r.region == region and r.location == location for r in self.visited_locations)

    def perception_day(self, region: str, location: str) -> int | None:
        for mark in self.perception_marks:
            if mark.region == region and mark.location == location:
                return mark.day
        return None
