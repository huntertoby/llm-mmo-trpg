"""世界畫面的實地地圖（Phase 6B-2；``docs/phases/Phase6計畫.md`` 3.5）。

格式照戰鬥畫面的 ``TileView``／``ObjectView`` 的欄位名稱（``x``、``y``、``height``、``terrain``、
``surface``、``kind``），6B-3 可以直接組成 ``DrawModel``。隱藏的門（還沒發現）不給。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from trpg.content.battle import DollLook
from trpg.content.fields import FieldFigure, ObjectPanel
from trpg.content.races import RaceLook
from trpg.content.world_events import NpcPortrait
from trpg.content.world_rules import FieldRules
from trpg.engine.view import AppearanceView

__all__ = [
    "FieldBuildingView",
    "FieldDoorView",
    "FieldEnemyUnitView",
    "FieldEnemyView",
    "FieldEventMarkView",
    "FieldExitView",
    "FieldFacilityView",
    "FieldFootprintView",
    "FieldFriendView",
    "FieldGearLookView",
    "FieldHeroView",
    "FieldNoteStoneView",
    "FieldNpcView",
    "FieldObjectView",
    "FieldPositionView",
    "FieldSituationObjectView",
    "FieldSpotView",
    "FieldStoneTargetView",
    "FieldStoneView",
    "FieldTileView",
    "FieldTilesView",
    "FieldView",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FieldTileView(_ApiModel):
    x: int
    y: int
    height: int
    terrain: str
    surface: str = "none"
    """初始表面（``water``、``fire``…；沒有＝``none``）。"""
    walkable: bool = True
    """角色站得上去（6B-3 前端算路徑用；同 ``field_grid``：地形、物件、NPC、隱藏門）。靜態地形
    （:class:`FieldTilesView`，6C-R3）把「發現才出現」的隱藏門一律畫成牆（不可站，6D-R1），這個角色
    已發現的放在 ``FieldView.open_cells``。"""


class FieldTilesView(_ApiModel):
    """一張實地地圖的靜態地形（6C-R3；``GET /api/world/characters/{id}/fields/{map_id}``）：只看
    內容，前端依
    ``hash`` 快取。"""

    map_id: str
    hash: str
    """地形內容的雜湊（排序鍵 JSON 的 SHA-256 前 16 碼；內容一樣就一樣）。"""
    width: int
    height: int
    tiles: tuple[FieldTileView, ...]
    """逐列（y 由上到下、x 由左到右）。"""


class FieldObjectView(_ApiModel):
    id: str
    """``o<x>_<y>``（一格最多一個物件）。"""
    kind: str
    x: int
    y: int
    look: str | None = None
    """只畫的家具外觀（6B-ART1：``barrel``、``bar``…）；規則照 ``kind``，沒有＝照 ``kind`` 畫。"""


class FieldBuildingView(_ApiModel):
    """只畫的建築外觀（6B-ART1）：疊在既有的牆格上，不影響走路、視線與戰鬥。"""

    kind: str
    """``tavern``、``smithy``、``hall``、``house``、``scrap_house``、``forge_house``，主城的
    ``stone_hall``、``mentor_hall``、``tent``、``fountain``（6D-ART2）；前端不認得的畫成
    ``house``。"""
    x: int
    y: int
    """左上角。"""
    width: int
    height: int
    sign: Literal["jar", "anvil", "scroll"] | None = None
    """招牌圖示（6D-ART2）：照建築範圍內的門通往的室內設施決定（導師＝書卷，鐵匠或附魔＝鐵砧，
    酒館＝酒罈；同 ``interiorArt`` 的室內種類順序）。沒有門、或門通往的不是這幾種室內＝``None``。"""


class FieldExitView(_ApiModel):
    id: str
    cells: tuple[tuple[int, int], ...]
    to: str
    to_name_zh: str
    """目的地點的名稱（室內圖的出口＝所屬地點）。"""
    blocked_zh: str | None = None
    """主線還沒推進到、走不過去時的提示（6E-1 霧牆，#122）；開著＝``None``。"""


class FieldDoorView(_ApiModel):
    id: str
    x: int
    y: int
    to: str
    to_name_zh: str
    """室內圖的名稱，或隱藏地點的名稱。"""


class FieldStoneView(_ApiModel):
    id: str
    x: int
    y: int
    unlocked: bool


class FieldStoneTargetView(_ApiModel):
    """站在傳送石上時可以傳去的另一顆（已解鎖；6B-3 的「傳送」按鈕用）。"""

    id: str
    name_zh: str
    """傳送石所在地點的名稱。"""


class FieldNpcView(_ApiModel):
    id: str
    name_zh: str
    x: int
    y: int
    rank: Literal["hostile", "cold", "neutral", "friendly", "trusted"] = "neutral"
    """好感度級別（6B-4：頭上的表情圖示；21.5、21.7）。"""
    rank_zh: str = ""
    """級別名稱（例「中立」）。"""
    alert: Literal["quest", "rumor"] | None = None
    """頭上的「！」（6B-4）：``quest``＝有可接的任務（或聊得出任務入口）、``rumor``＝今天還沒聊、
    有傳聞可聽；都沒有＝``None``。"""
    alert_zh: str | None = None
    """「！」的說明（例「有任務可以接」）。"""
    look: FieldHeroView | None = None
    """紙娃娃外觀；人設卡沒有外觀資料時為 ``None``（前端用預設外觀，6B-4）。"""
    portrait: NpcPortrait | None = None
    """頭像外觀（人設卡的 ``portrait``，6C-7）；``look`` 為 ``None`` 時前端照它換算地圖紙娃娃
    （``docs/art/NPC頭像.md`` 第 4 節第 5 項）。沒寫為 ``None``（前端用通用剪影）。"""


class FieldFacilityView(_ApiModel):
    kind: str
    """``shop``、``smithy``、``tavern``、``mentor``、``notice_board``、``hire``、``enchanter``。"""
    x: int
    y: int
    figure: FieldFigure | None = None
    """站在設施格上的人（6V-3，內容的 ``figure``）：主城功能型 NPC 的紙娃娃與頭像，只畫；
    ``None``＝沒有人。"""


class FieldEnemyUnitView(_ApiModel):
    """敵群裡的一名（6C-1 陣容摘要）。"""

    unit: str
    name_zh: str
    affix: str | None = None
    """精英詞綴（沒有＝``None``）。"""
    elite: bool = False
    """精英範本或套了精英詞綴。"""
    third: bool = False
    """三方混戰的第三方（和我方、敵方都敵對）。"""


class FieldEnemyView(_ApiModel):
    """地圖上看得見的一隊敵人（Phase 6C-1）：位置、朝向、陣容摘要、視野格。"""

    id: str
    """``e<spawns 的索引>``。"""
    x: int
    y: int
    facing: Literal["n", "e", "s", "w"]
    patrol: bool
    """巡邏（你走一格它走一格）；``False``＝駐守不動。"""
    group: str
    name_zh: str
    """陣容名稱。"""
    elite: bool
    """陣容裡有精英。"""
    units: tuple[FieldEnemyUnitView, ...] = ()
    sight: tuple[tuple[int, int], ...] = ()
    """看得到的格子（前方扇形 4 格、被牆與擋視線物遮住；走進去就開打、敵方先手）。"""
    look: FieldHeroView | None = None
    """帶頭單位（陣容第一名，沒有敵方時第三方第一名）的外觀（6C-R3；欄位同戰鬥 ``UnitView``：
    ``doll_look`` 含異形的 ``creature``）；沒有陣容＝``None``。"""


class FieldPositionView(_ApiModel):
    x: int
    y: int
    facing: Literal["n", "e", "s", "w"]


class FieldGearLookView(_ApiModel):
    slot: str
    appearance: AppearanceView = AppearanceView()


class FieldHeroView(_ApiModel):
    """主角的紙娃娃外觀（6B-3；欄位同戰鬥的 ``UnitView``，純顯示）。"""

    template_id: str
    doll_look: DollLook | None = None
    weapon_id: str
    weapon_class: str
    race_look: RaceLook | None = None
    equipment: tuple[FieldGearLookView, ...] = ()


class FieldFriendView(_ApiModel):
    """站在城裡的朋友（其他角色的影子，6B-4；21.5）：位置依角色 ID 雜湊決定（確定性），
    點了看名片。"""

    owner: str
    """影子主人的角色 ID（對 ``PartyView.shadows`` 的 ``owner``）。"""
    name_zh: str
    level: int
    x: int
    y: int
    facing: Literal["n", "e", "s", "w"] = "s"
    look: FieldHeroView
    """紙娃娃外觀（存影子時的主角範本與裝備）。"""


class FieldSpotView(_ApiModel):
    """營火點（6C-5）：站在上面可以紮營。"""

    id: str
    x: int
    y: int


class FieldEventMarkView(_ApiModel):
    """地圖上的事件「！」（6C-5，21.6）：走過去碰到（站上或相鄰）才開事件卡。不給骨架。"""

    x: int
    y: int


class FieldSituationObjectView(_ApiModel):
    """情境物件（6C-5；21.6「走到旁邊點了就開」）。"""

    id: str
    name_zh: str
    x: int
    y: int
    use: Literal["note", "event", "encounter"]
    """``note``＝只看說明卡（不送動作）；``event``／``encounter``＝站在旁邊送
    ``use_field_object``。"""
    usable: bool
    """現在能送 ``use_field_object``（``use`` 不是 ``note``、沒有 ``problem_zh``）。"""
    note_zh: str = ""
    problem_zh: str | None = None
    """``use`` 是 ``event``／``encounter`` 但現在不能用的原因。"""
    panel: ObjectPanel | None = None
    """點了直接開的既有面板（主城的功能型物件；6D-R2，內容的 ``panel``）；``None``＝照 ``use``。"""
    stele_region: str | None = None
    """橋頭石碑對應的區域：點了開那一區的傳送選單（6D-R2，內容的 ``stele_region``）。"""
    figure: FieldFigure | None = None
    """站在這格的人（6V-1，內容的 ``figure``）：主城功能型 NPC 的紙娃娃與頭像，只畫；
    ``None``＝沒有人。"""


class FieldFootprintView(_ApiModel):
    """朋友走過的腳印（6C-5；21.6、21.9 第 14 條）：其他角色去過這個地點時，沿兩個出入口之間的一條
    路畫幾個腳印（位置依地圖與角色 ID 的雜湊決定，不是真的走過的路）。"""

    owner: str
    name_zh: str
    x: int
    y: int
    facing: Literal["n", "e", "s", "w"] = "s"


class FieldNoteStoneView(_ApiModel):
    """這個地點有留言時，入口旁畫一塊留言石碑（6C-5；點了開留言板，N）。"""

    x: int
    y: int
    count: int


class FieldView(_ApiModel):
    map_id: str
    name_zh: str
    region: str
    location: str
    interior: bool
    width: int
    height: int
    tiles: tuple[FieldTileView, ...] = ()
    """逐列（y 由上到下、x 由左到右）。6C-R3 起世界畫面不帶（空），前端用 ``tiles_hash`` 向
    ``GET /api/world/characters/{id}/fields/{map_id}?h=…`` 取靜態地形並快取，再套上
    ``open_cells``。"""
    tiles_hash: str = ""
    """靜態地形的雜湊（:class:`FieldTilesView` 的 ``hash``；6C-R3）。"""
    open_cells: tuple[FieldTileView, ...] = ()
    """這個角色看到的地形和靜態地形不同的格子（已發現的隱藏門：靜態地形畫成牆，這裡是真地形；6C-R3，
    6D-R1 改成整格），前端蓋在靜態地形上。"""
    objects: tuple[FieldObjectView, ...]
    exits: tuple[FieldExitView, ...]
    doors: tuple[FieldDoorView, ...]
    stones: tuple[FieldStoneView, ...]
    npcs: tuple[FieldNpcView, ...]
    facilities: tuple[FieldFacilityView, ...]
    me: FieldPositionView
    """自己的位置與朝向。"""
    max_climb: int = 1
    """一步最多往上爬幾層（``core.max_climb_height``；6B-3 前端算路徑用）。"""
    walk_max_steps: int = FieldRules().walk_max_steps
    """一次 ``walk`` 最多幾格（規則 ``field.walk_max_steps``；6P-2，前端照這個分段送）。預設值取
    :class:`~trpg.content.world_rules.FieldRules` 的（單一來源，6R-P）。"""
    hero: FieldHeroView | None = None
    """主角外觀（6B-3）。"""
    stone_targets: tuple[FieldStoneTargetView, ...] = ()
    """站在傳送石上時：其他已解鎖的傳送石（依 ID 排序；沒站在傳送石上＝空）。"""
    enemies: tuple[FieldEnemyView, ...] = ()
    """看得見的敵人（6C-1；依 ``spawns`` 順序；室內、已清空、打贏的不給）。"""
    friends: tuple[FieldFriendView, ...] = ()
    """站在城裡的朋友（6B-4；只在城鎮的主地圖、不含自己；依主人 ID，最多 8 位）。"""
    campfires: tuple[FieldSpotView, ...] = ()
    """營火點（6C-5）。"""
    event_mark: FieldEventMarkView | None = None
    """這張圖上還沒碰到的事件「！」（6C-5）。"""
    situation_objects: tuple[FieldSituationObjectView, ...] = ()
    """情境物件（6C-5；要線頭才顯示的，沒持有時不給）。"""
    sneaking: bool = False
    """潛行中（6C-5，Q7：到進入下一張地圖為止，敵人視野減半）。"""
    sneak_cost: int = 1
    sneak_problem_zh: str | None = None
    """不能潛行的原因（HUD 的 R 鈕）；可以時為 ``None``。"""
    footprints: tuple[FieldFootprintView, ...] = ()
    """朋友的腳印（6C-5；室外圖，最多 3 位朋友）。"""
    note_stone: FieldNoteStoneView | None = None
    """留言石碑（6C-5；這個地點有留言時）。"""
    buildings: tuple[FieldBuildingView, ...] = ()
    """建築外觀（6B-ART1；只畫，依內容順序）。"""


FieldNpcView.model_rebuild()
FieldEnemyView.model_rebuild()
