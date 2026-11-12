"""實地地圖（``content/world/fields/<region>/<location>.yaml``；室內放
``<region>/interiors/<id>.yaml``；Phase 6B-1）。

每個地點一張可以走動的 2D 格子地圖，城鎮的重點建築另有室內圖（``docs/design/21-探索地圖與城鎮.md``
21.2、21.3、21.5、21.6、21.10）。地形、高低差、物件、表面的寫法與戰鬥地圖
:class:`~trpg.content.maps.MapDef` 相同，並共用 :mod:`trpg.content.maps` 的驗證工具，之後可以
直接切出 12×12 戰場（21.4、6C-2）。

銜接（21.2）：

- **出口** ``exits``：邊緣上的一段格子；``to`` 是相鄰地點（``region`` 省略＝本區），``arrive``
  是對面地圖上「回來的那個出口」的 ID。一條地點連線＝一對互指的出口。
- **門與洞口** ``doors``：通往本地點的室內圖，或相鄰的隱藏地點（``hidden_until: reveal``，21.6）。
  隱藏地點那一側用出口回來，出口的 ``arrive`` 指向這扇門。
- **傳送石** ``teleport_stones``：每區 2～3 個、每個城鎮 1 個（不符是錯誤，6D-R1；那一區的地點
  還沒畫完時先記成待補）。

跨區（往灰燼荒原的渡口，21.10 第 1 條；Phase 6 計畫 Q2）兩種寫法都支援：

- **渡口是一張路徑圖**（預設）：傳送點地點（``kind: gate``）自己有實地地圖，其中一個出口寫
  ``region: <gate_to>``，走到尾端就進入另一區。
- **渡口只是出口**：傳送點地點沒有實地地圖，與它相連的地圖直接放一個 ``region: <gate_to>`` 的出口，
  這個出口同時算作「往傳送點的那條連線」。

主城（21.1、21.5；6D-4）：``region: capital``、``location: capital``（室內圖寫
``interior_of: capital``），
放在 ``capital/``。主城不在任何區域的地點圖裡、沒有走路的出口，只能傳送抵達；它是安全區，沒有敵人
（``spawns``）與營火（``campfires``），傳送石恰好 1 個；功能型 NPC 沒有人設卡，用 ``facilities`` 或
``situation_objects`` 表示，不用 ``npcs``。抵達方式與安全區規則是 6D-5 的事，這裡只檢查地圖。

驗證分兩層：單檔（:class:`FieldMapDef` 的 validator：網格、座標、出口在邊緣、ID 不重複）與跨檔案
（:func:`field_map_report`：地點與連線、出口配對、地形與物件 ID、走得到、尺寸、傳送石、NPC、
出口 gate 的任務與步驟）。還沒畫的地圖不算錯：對面還沒畫的出口列為「待補」。

確定性：所有清單依 ID 或座標排序，不依賴 ``set``／``dict`` 的迭代順序（守則 2）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, get_args

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, TerrainDef
from trpg.content.environment import ObjectDef
from trpg.content.maps import (
    MapObjectPlacement,
    MapSurfacePlacement,
    Passable,
    grid_rows,
    grid_shape_problems,
    passable_grid,
    placement_problems,
    reachable_from,
)
from trpg.content.rules import CoreRules
from trpg.content.schemas import ContentModel, duplicates
from trpg.content.world_events import NpcPortrait, NpcPortraitGear
from trpg.content.world_map import LocationDef, LocationMapDef

__all__ = [
    "BUILDING_KINDS",
    "CAPITAL_LOCATION",
    "CAPITAL_NAME_ZH",
    "CAPITAL_REGION",
    "CHASM_STYLES",
    "FACILITY_KINDS",
    "LAYOUT_SIZES",
    "OBJECT_LOOKS",
    "ChasmStyle",
    "ExitGate",
    "FacilityKind",
    "FieldBuilding",
    "FieldDoor",
    "FieldExit",
    "FieldFacility",
    "FieldLayout",
    "FieldLook",
    "FieldMapDef",
    "FieldMapReport",
    "FieldNpc",
    "FieldObjectPlacement",
    "FieldSpawn",
    "FieldSpot",
    "ObjectLook",
    "RegionProgress",
    "TeleportStone",
    "field_map_problems",
    "field_map_report",
    "field_progress",
]

type XY = tuple[int, int]

_MIN_SIZE = 4
_MAX_SIZE = 64

type FieldLayout = Literal["path", "site", "lair", "boss", "town", "capital", "interior"]
"""地圖種類（21.3 的大小表）：路徑類、營地／遺跡／祭壇／村落、精英巢穴／秘境、Boss 前廳、小鎮、
主城、室內。省略時依地點種類推定（:meth:`FieldMapDef.layout_for`）。"""

LAYOUT_SIZES: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {
    # 種類: ((長邊下限, 長邊上限), (短邊下限, 短邊上限))；21.3 寫「約」，前後各放寬幾格
    "path": ((16, 24), (8, 14)),  # 約 20×12，狹長
    "site": ((20, 28), (14, 22)),  # 約 24×18
    "lair": ((12, 20), (10, 18)),  # 約 16×14
    "boss": ((10, 14), (6, 10)),  # Boss 地圖前的前廳，約 12×8（Boss 地圖本身照 20.6）
    "town": ((20, 28), (14, 22)),  # 約 24×18
    "capital": ((28, 36), (20, 28)),  # 約 32×24
    "interior": ((8, 12), (6, 10)),  # 約 10×8
}
"""21.3 的尺寸範圍（數值類：超出只警告）。橫放、直放都可以，所以比的是長邊與短邊。"""

_KIND_LAYOUT: dict[str, str] = {
    "town": "town",
    "gate": "path",
    "secret": "lair",
    "elite_lair": "lair",
    "boss": "boss",
}
"""地點種類 → 預設地圖種類；其他種類（營地、遺跡、祭壇、村落、異象、商隊）是 ``site``。"""

type FacilityKind = Literal[
    "shop", "smithy", "tavern", "mentor", "notice_board", "hire", "enchanter", "post"
]
"""現有的設施種類（21.5；商店、鐵匠、酒館、導師、公告板、雇用、附魔台；``post`` 郵寄是 6T-1b：郵筒與
郵差站的格子，點了開郵寄面板）。"""

FACILITY_KINDS: tuple[str, ...] = (
    "shop",
    "smithy",
    "tavern",
    "mentor",
    "notice_board",
    "hire",
    "enchanter",
    "post",
)

CAPITAL_REGION = "capital"
"""主城的 ``region``（不是碎界五區之一，沒有地點圖；6D-4）。"""
CAPITAL_LOCATION = "capital"
"""主城室外圖的 ``location``（室內圖的 ``interior_of``）。"""
CAPITAL_NAME_ZH = "主城"
"""``content check`` 進度列的名稱（主城的正式名稱待使用者決定，草稿待確認 1）。"""

STONES_PER_REGION = (2, 3)
"""每區野外的傳送石數（21.2「每區 2～3 個，城鎮各 1 個」：城鎮那顆不算在內）；不在範圍內是錯誤
（6D-R1；那一區的地點還沒全部畫完時先記成待補，畫完才判）。"""


class ExitGate(ContentModel):
    """主線推進前擋住的出口（#122，21.10 第 18 條；例：源晶裂痕往雲頂觀的霧牆）。

    角色 **自己的** 任務 ``quest`` 的 ``step`` 這一步完成（或整個任務完成）、或角色有劇情旗標
    ``open_flag`` 時打開；之前走上出口格不換圖、不移動、不算一步，畫面顯示 :meth:`notice_zh`。
    ``spot`` 是這張圖上對應的情境物件：關著時說明卡用 :meth:`notice_zh`、打開後用 ``open_zh``
    （省略＝照物件原本的 ``note_zh``）。"""

    quest: str = Field(pattern=ID_PATTERN)
    step: str = Field(pattern=ID_PATTERN)
    open_flag: str | None = Field(default=None, pattern=ID_PATTERN)
    spot: str | None = Field(default=None, pattern=ID_PATTERN)
    blocked_zh: str = Field(min_length=1)
    hint_zh: str = ""
    open_zh: str = ""

    def notice_zh(self) -> str:
        """擋住時的提示（說明卡、畫面提示共用）。"""
        return f"{self.blocked_zh}。{self.hint_zh}" if self.hint_zh else self.blocked_zh


class FieldExit(ContentModel):
    """邊緣出口（21.2）：佔一段邊緣格（路口寬 2～3 格）。"""

    id: str = Field(pattern=ID_PATTERN)
    at: tuple[XY, ...] = Field(min_length=1)
    to: str = Field(pattern=ID_PATTERN)
    """相鄰地點的 ID；室內圖寫所屬的地點。"""
    arrive: str = Field(pattern=ID_PATTERN)
    """對面地圖上的出口（或門）ID：走過去就從那裡出現。"""
    region: str | None = Field(default=None, pattern=ID_PATTERN)
    """``to`` 所在的區域；省略＝本區。只有跨區的渡口才寫（見模組說明）。"""
    gate: ExitGate | None = None
    """主線推進前擋住（#122）；省略＝一直開著。"""


class FieldDoor(ContentModel):
    """門與洞口（21.2）：通往本地點的室內圖或相鄰的隱藏地點。"""

    id: str = Field(pattern=ID_PATTERN)
    at: XY
    to: str = Field(pattern=ID_PATTERN)
    """室內圖 ID，或相鄰隱藏地點的地點 ID。"""
    hidden_until: Literal["reveal"] | None = None
    """``reveal``＝平時被遮住，發現隱藏地點後才出現（21.6）；通往隱藏地點的門必填。"""


BUILDING_KINDS: tuple[str, ...] = (
    "tavern",
    "smithy",
    "hall",
    "house",
    "scrap_house",
    "forge_house",
    "stone_hall",
    "mentor_hall",
    "tent",
    "fountain",
)
"""``buildings`` 認得的外觀（6B-ART1；``docs/archive/art/Phase6剩餘美術移植需求.md`` 1.1）。主城的
``stone_hall``、``mentor_hall``、``tent``、``fountain`` 是 6D-ART2（需求第 2 節）；不認得的 ``kind``
前端退回 ``house``（``content check`` 列為警告）。"""

WATER_BUILDINGS: frozenset[str] = frozenset({"fountain"})
"""可以蓋在水表面上的建築外觀（6D-ART2：許願池的噴水池）：範圍內每一格是牆、門或水表面。"""

type ObjectLook = Literal[
    "barrel",
    "table",
    "bar",
    "counter",
    "anvil",
    "forge",
    "candle",
    "crystal_statue",
    "shelf",
    "crystal_lamp",
    "stele",
    "sky_bridge",
    "postbox",
]
"""物件的家具外觀（6B-ART1，需求 1.3）：只換畫法，規則照原本的 ``kind``。``crystal_lamp``
（源晶燈）、``stele``（橋頭石碑；紋章照同一格情境物件的 ``stele_region``）、``sky_bridge``（主城的
浮橋）是 6D-ART2；``postbox``（郵筒，材質照區域；規則用 ``low_wall``）是 6T-1b。"""

OBJECT_LOOKS: tuple[str, ...] = get_args(ObjectLook.__value__)
""":data:`ObjectLook` 的值（由型別取出，不另寫一份；6R-P）。"""


type ChasmStyle = Literal["default", "deep_water"]
"""深淵（``chasm``）的畫法（6V-2b，``docs/archive/art/6V-2檢查.md`` 2.2）：``deep_water``
畫成深灰藍的深水（灰渡口的灰河）。**只換畫法**：地形仍是 ``chasm``，致命判定、路徑預覽都照舊。"""

CHASM_STYLES: tuple[str, ...] = get_args(ChasmStyle.__value__)
""":data:`ChasmStyle` 的值（由型別取出）。"""


type DecorKind = Literal["flower_bed", "stall_cloth", "clothesline", "crate_stack", "radial_paving"]
"""只畫的地面裝飾種類（6V-4b，``docs/art/6V-3與6V-4檢查.md`` 2 第 3、4 點）：花壇、攤布、晾衣繩、
堆箱、放射狀鋪法。"""

DECOR_KINDS: tuple[str, ...] = get_args(DecorKind.__value__)
""":data:`DecorKind` 的值（由型別取出）。"""

type DecorLayer = Literal["ground", "standing"]
"""裝飾畫在哪一層：``ground``＝地面（畫在人物下面）；``standing``＝站著的（和人物一起照 y 排序：
人站在它後面〔北邊〕時被擋住，站在前面時蓋住它）。"""

DECOR_LAYERS: Mapping[str, DecorLayer] = {
    "flower_bed": "ground",
    "stall_cloth": "ground",
    "clothesline": "standing",
    "crate_stack": "standing",
    "radial_paving": "ground",
}
"""每種裝飾的圖層（站立／地面）。"""

DECOR_FIXED_SIZE: Mapping[str, XY] = {
    "flower_bed": (1, 1),
    "stall_cloth": (1, 1),
    "clothesline": (3, 1),
    "crate_stack": (1, 1),
}
"""固定尺寸的裝飾（寬、高，格）；``size`` 省略＝這個尺寸，填了必須相同。``radial_paving`` 不在這裡
（範圍必填）。"""


class FieldDecor(ContentModel):
    """一件只畫的裝飾（6V-4b）：不佔格、不擋路、不進規則（放在地圖的 ``look.decor``，規則雜湊
    排除整個 ``look``）。

    - ``at``：左上格；``size``：寬高（格）。固定尺寸的種類可省略 ``size``
      （見 :data:`DECOR_FIXED_SIZE`）。
    - ``radial_paving``（放射狀鋪法）：``size`` 是鋪的範圍，``center`` 是圓心那一格
      （畫在格子中心），
      都必填，``center`` 要在範圍內。其他種類不可填 ``center``。

    前端每次照地圖檢查格子是不是空的地面，被佔的那件整件不畫。"""

    kind: DecorKind
    at: XY
    size: XY | None = None
    center: XY | None = None

    @model_validator(mode="after")
    def _shape(self) -> FieldDecor:
        if self.kind == "radial_paving":
            if self.size is None or self.center is None:
                raise ValueError("radial_paving 必須填 size（範圍）與 center（圓心）")
            w, h = self.size
            if w < 1 or h < 1:
                raise ValueError(f"radial_paving 的 size 必須至少 1×1，收到 {list(self.size)}")
            cx, cy = self.center
            x0, y0 = self.at
            if not (x0 <= cx < x0 + w and y0 <= cy < y0 + h):
                raise ValueError(f"radial_paving 的 center {list(self.center)} 不在範圍內")
            return self
        if self.center is not None:
            raise ValueError(f"{self.kind} 不可填 center（只有 radial_paving 可以）")
        fixed = DECOR_FIXED_SIZE[self.kind]
        if self.size is not None and self.size != fixed:
            raise ValueError(f"{self.kind} 的 size 固定是 {list(fixed)}，收到 {list(self.size)}")
        return self

    @property
    def footprint(self) -> XY:
        """寬、高（格）。"""
        return self.size if self.size is not None else DECOR_FIXED_SIZE[self.kind]

    @property
    def layer(self) -> DecorLayer:
        return DECOR_LAYERS[self.kind]

    def cells(self) -> list[XY]:
        """範圍內的格子（逐列、由左到右）。"""
        x0, y0 = self.at
        w, h = self.footprint
        return [(x, y) for y in range(y0, y0 + h) for x in range(x0, x0 + w)]


class FieldLook(ContentModel):
    """實地地圖只影響畫法的外觀欄位（6V-2b）；不進規則（規則雜湊排除整個 ``look``）。"""

    chasm_style: ChasmStyle = "default"
    decor: tuple[FieldDecor, ...] = ()
    """只畫的裝飾（6V-4b，見 :class:`FieldDecor`）；依內容順序。"""


class FieldBuilding(ContentModel):
    """建築外觀（6B-ART1；只畫）：疊在既有的牆格上，牆照舊寫在 ``terrain``，規則完全不變。

    ``at`` 是左上角、``size`` 是寬高（格）；範圍內每一格都要是 ``wall`` 地形或門的格子
    （``fountain`` 也可以是水表面），
    不可蓋到出口（不採用代決 #34 的「載入時展開成牆」）。"""

    kind: str = Field(pattern=ID_PATTERN)
    at: XY
    size: tuple[int, int]

    @model_validator(mode="after")
    def _size_positive(self) -> FieldBuilding:
        if self.size[0] < 1 or self.size[1] < 1:
            raise ValueError(f"建築 {self.kind} 的 size 必須至少 1×1，收到 {list(self.size)}")
        return self

    def cells(self) -> list[XY]:
        """範圍內的格子（逐列、由左到右）。"""
        x0, y0 = self.at
        w, h = self.size
        return [(x, y) for y in range(y0, y0 + h) for x in range(x0, x0 + w)]


class FieldObjectPlacement(MapObjectPlacement):
    """實地地圖上的物件；``look`` 是只畫的家具外觀（6B-ART1），省略＝照 ``kind`` 的畫法。"""

    look: ObjectLook | None = None


class TeleportStone(ContentModel):
    """傳送石（21.2）。``id`` 全部實地地圖內不重複。"""

    id: str = Field(pattern=ID_PATTERN)
    at: XY


class FieldNpc(ContentModel):
    """站在地圖上的 NPC（21.5）；``id`` 是 ``world/npcs/<region>.yaml`` 的人設卡。"""

    at: XY
    id: str = Field(pattern=ID_PATTERN)


class FieldFacility(ContentModel):
    """設施（21.5）：走到旁邊就開原本的面板。``at`` 可以是建築的牆或櫃檯（旁邊要走得到）。"""

    at: XY
    id: FacilityKind
    figure: FieldFigure | None = None
    """站在設施格上的人的外觀（6V-3，同情境物件的 ``figure``；只畫）：主城的殿主、酒館老闆、鐵匠、
    附魔師、傭兵管事。不影響規則、互動與通行（點了照舊開設施的面板）。"""
    postman: bool = False
    """站在這格的是這區的郵差（只用在 ``post``，6T-1b）：畫面用 ``world/trade.yaml`` 郵差人設卡的
    頭像與名字（不另寫 ``figure``）；郵筒那格寫 ``false``。"""

    @model_validator(mode="after")
    def _postman_is_post(self) -> FieldFacility:
        if self.postman and self.id != "post":
            raise ValueError("postman 只能用在 post 設施")
        if self.postman and self.figure is not None:
            raise ValueError("郵差的外觀照 world/trade.yaml 的人設卡，不另寫 figure")
        return self


class FieldSpawn(ContentModel):
    """看得見的敵人（6C-1；``personal``、``day_phase`` 是 6C-1b）。"""

    at: XY
    group: str = Field(pattern=ID_PATTERN)
    patrol: tuple[XY, ...] = ()
    """巡邏路線（沿固定路線來回，21.10 第 3 條）；省略＝站著不動。"""
    personal: bool = False
    """個人的駐守（21.10 第 9 條）：打贏只對自己消失（記在角色的這一趟）、不算進共享的「已清空」，
    下一趟回來（離開這個地點再進來）再出現。用在新手任務的固定戰與三村落的守點戰。"""
    day_phase: Literal["day", "night"] | None = None
    """只在這個時段出現（21.10 第 11 條，寫法同事件骨架的 ``day_phase``）；省略＝全天。"""
    until_quest: str | None = Field(default=None, pattern=ID_PATTERN)
    """這個任務完成後就不再出現（21.10 第 9 條，6C-5）；省略＝一直出現。"""
    until_step: str | None = Field(default=None, pattern=ID_PATTERN)
    """``until_quest`` 的這一步完成後就不再出現（21.10 第 9 條 6C-5 改：「那一步完成後就不再出現」，
    6C-5b）；省略＝整個任務完成才不出現。要和 ``until_quest`` 一起寫。"""

    @model_validator(mode="after")
    def _step_needs_quest(self) -> FieldSpawn:
        if self.until_step is not None and self.until_quest is None:
            raise ValueError("until_step 要和 until_quest 一起寫")
        return self


type SpotUse = Literal["note", "event", "encounter"]
"""情境物件點了做什麼（6C-5）：``note``＝只開說明卡；``event``＝開這個地點的事件骨架（情境判定照
骨架的模板）；``encounter``＝這個地點的遭遇（Boss 門）。"""

type ObjectPanel = Literal["board", "league", "pavilion", "skills", "workshop"]
"""主城情境物件點了開的既有面板（6D-R2）：``board``＝公告板（封印、賽季 Boss）、``league``＝影子
循環賽、``pavilion``＝整備亭、``skills``＝技能（魔導書）、``workshop``＝工坊師傅選單（PR-2a，
``WorldView.workshop``）。"""


type FigureWork = Literal["smith", "keeper", "town"]
"""站在物件上的人的待機小動作（同前端 6N-10 的 NPC 身分）：``smith``＝打鐵、``keeper``＝擦櫃檯、
``town``＝一般。"""

type FigureFacing = Literal["n", "e", "s", "w"]


class FieldFigure(ContentModel):
    """站在情境物件上的人（6V-1，``docs/archive/art/偷懶自查.md`` G7）：主城的功能型 NPC
    （守印人、守池人、工坊師傅、書記）沒有人設卡、不放 ``npcs``，只在原本的格子上畫一個紙娃娃。
    純顯示：不影響規則、互動與通行（點了照舊開物件的 ``panel`` 或說明卡）。"""

    portrait: NpcPortrait
    """頭像與地圖紙娃娃的外觀（寫法同 NPC 人設卡的 ``portrait``，6C-7）。"""
    held: NpcPortraitGear | None = None
    """主手拿的東西（只畫在地圖紙娃娃上；``kind`` 用紙娃娃主手的造型，例：``staff``、
    ``hammer``）。"""
    work: FigureWork = "town"
    facing: FigureFacing = "s"
    line_zh: str = Field(default="", max_length=40)
    """頭像旁的一句話（6V-3）：主城公告板上緣「頭像＋一句話」用（守印人）；省略＝只顯示名字。只顯示，
    不給說書人。"""


class FieldSpot(ContentModel):
    """營火點、事件點、情境物件（6C-5）。

    - 營火點、事件點只用 ``at``、``id``（事件點的 ``id`` 是事件骨架 ID，6C-3 報告第 9 點）。
    - 情境物件另外可寫 ``name_zh``、``use``、``event``、``note_zh``、``requires_*``、
      ``locked_zh``。"""

    at: XY
    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = ""
    """顯示名稱（情境物件；省略＝畫面用「物件」）。"""
    use: SpotUse = "note"
    event: str | None = Field(default=None, pattern=ID_PATTERN)
    """``use: event`` 的事件骨架；省略＝和 ``id`` 同名。"""
    note_zh: str = ""
    """說明卡的文字（每種 ``use`` 都可以有）。"""
    requires_thread: str | None = Field(default=None, pattern=ID_PATTERN)
    """持有這個線頭才顯示（例：斷崖幫寨的暗門）。"""
    requires_flag: str | None = Field(default=None, pattern=ID_PATTERN)
    """世界旗標沒開時只開說明卡、顯示 ``locked_zh``（例：熔心坑的熔岩封口）。"""
    locked_zh: str = ""
    """``requires_flag`` 沒開時的說明。"""
    panel: ObjectPanel | None = None
    """點了開哪個既有面板（6D-R2，原本前端寫死）；只有主城的情境物件可填，``use`` 必須是 note。"""
    stele_region: str | None = Field(default=None, pattern=ID_PATTERN)
    """橋頭石碑對應的區域（``regions.yaml`` 的 ID）：點了開那一區的傳送選單（6D-5；6D-R2 改成資料，
    原本靠 ``stele_`` 前綴）。只有主城的情境物件可填，``use`` 必須是 ``note``。"""
    figure: FieldFigure | None = None
    """站在這格的人的外觀（6V-1，只畫）；只有情境物件可填。"""

    @model_validator(mode="after")
    def _panel_or_stele(self) -> FieldSpot:
        if self.panel is not None and self.stele_region is not None:
            raise ValueError(f"情境物件 {self.id}：panel 與 stele_region 只能填一個")
        if (self.panel is not None or self.stele_region is not None) and self.use != "note":
            raise ValueError(f"情境物件 {self.id}：填了 panel／stele_region 的 use 必須是 note")
        return self


def _is_edge(cell: XY, size: XY) -> bool:
    x, y = cell
    return x == 0 or y == 0 or x == size[0] - 1 or y == size[1] - 1


class FieldMapDef(ContentModel):
    """一張實地地圖（一個地點一張；室內圖另外一張）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = ""
    """顯示名稱；省略時畫面用地點名稱（室內圖建議填，例「霧渡鎮酒館」）。"""
    region: str = Field(pattern=ID_PATTERN)
    location: str | None = Field(default=None, pattern=ID_PATTERN)
    """地點圖上的地點 ID（室外圖必填）。"""
    interior_of: str | None = Field(default=None, pattern=ID_PATTERN)
    """室內圖必填：所屬的地點 ID。``location`` 與 ``interior_of`` 恰好填一個。"""
    layout: FieldLayout | None = None
    """地圖種類（尺寸檢查用）；省略時依地點種類推定。"""
    size: tuple[int, int]
    heights: str
    terrain: str
    legend: dict[str, str]
    objects: tuple[FieldObjectPlacement, ...] = ()
    surfaces: tuple[MapSurfacePlacement, ...] = ()
    entry: XY
    """預設入口格：舊存檔、傳送、全滅回城都放這裡。"""
    exits: tuple[FieldExit, ...] = ()
    doors: tuple[FieldDoor, ...] = ()
    teleport_stones: tuple[TeleportStone, ...] = ()
    npcs: tuple[FieldNpc, ...] = ()
    facilities: tuple[FieldFacility, ...] = ()
    spawns: tuple[FieldSpawn, ...] = ()
    campfires: tuple[FieldSpot, ...] = ()
    event_spots: tuple[FieldSpot, ...] = ()
    situation_objects: tuple[FieldSpot, ...] = ()
    buildings: tuple[FieldBuilding, ...] = ()
    """建築外觀（6B-ART1；只畫，見 :class:`FieldBuilding`）。"""
    look: FieldLook = Field(default_factory=FieldLook)
    """只影響畫法的外觀（6V-2b，見 :class:`FieldLook`）。"""

    # ---- 網格（與 MapDef 相同） ----

    @property
    def width(self) -> int:
        return self.size[0]

    @property
    def height(self) -> int:
        return self.size[1]

    @property
    def is_interior(self) -> bool:
        return self.interior_of is not None

    @property
    def is_capital(self) -> bool:
        """主城的室外圖或室內圖（6D-4）。"""
        return self.region == CAPITAL_REGION

    @property
    def place(self) -> str:
        """所屬的地點 ID（室外圖＝``location``，室內圖＝``interior_of``）。"""
        place = self.location if self.location is not None else self.interior_of
        assert place is not None  # validator 保證恰好填一個
        return place

    def height_rows(self) -> list[str]:
        return grid_rows(self.heights)

    def terrain_rows(self) -> list[str]:
        return grid_rows(self.terrain)

    def grid(self) -> list[list[tuple[int, str]]]:
        """``grid()[y][x] == (高度, 地形 ID)``。"""
        hs, ts = self.height_rows(), self.terrain_rows()
        return [
            [(int(hs[y][x]), self.legend[ts[y][x]]) for x in range(self.width)]
            for y in range(self.height)
        ]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    # ---- 查詢 ----

    def portal(self, portal_id: str) -> FieldExit | FieldDoor | None:
        """ID 為 ``portal_id`` 的出口或門；沒有時回傳 ``None``。"""
        for exit_ in self.exits:
            if exit_.id == portal_id:
                return exit_
        for door in self.doors:
            if door.id == portal_id:
                return door
        return None

    def layout_for(self, location: LocationDef | None) -> str:
        """尺寸檢查用的地圖種類：``layout`` 欄位優先，其次依地點種類推定。"""
        if self.layout is not None:
            return self.layout
        if self.is_interior:
            return "interior"
        if self.is_capital:
            return "capital"
        if location is None:
            return "site"
        return _KIND_LAYOUT.get(location.kind, "site")

    def summary(self) -> str:
        name = self.name_zh or self.place
        return (
            f"{name}（{self.width}×{self.height}）：出口 {len(self.exits)}、門 {len(self.doors)}、"
            f"傳送石 {len(self.teleport_stones)}"
        )

    # ---- 單檔驗證 ----

    @model_validator(mode="after")
    def _check(self) -> FieldMapDef:
        w, h = self.size
        if not (_MIN_SIZE <= w <= _MAX_SIZE and _MIN_SIZE <= h <= _MAX_SIZE):
            raise ValueError(f"size 必須在 {_MIN_SIZE}–{_MAX_SIZE} 之間，收到 {list(self.size)}")
        problems = self._kind_problems()
        problems += grid_shape_problems(self.size, self.heights, self.terrain, self.legend)
        problems += self._id_problems()
        problems += self._panel_problems()
        problems += self._bounds_problems()
        problems += self._decor_problems()
        if not problems:
            problems += self._edge_problems()
            problems += self._overlap_problems()
            problems += self._building_problems()
        if problems:
            raise ValueError(f"實地地圖 {self.id}：{'；'.join(problems)}")
        return self

    def _panel_problems(self) -> list[str]:
        """``panel``／``stele_region`` 只有主城的情境物件可填（6D-R2）；``figure`` 只有情境物件
        可填（6V-1）。"""
        out = [
            f"{name} {s.id} 不可填 panel／stele_region（只有情境物件可以）"
            for name, spots in (("campfires", self.campfires), ("event_spots", self.event_spots))
            for s in spots
            if s.panel is not None or s.stele_region is not None
        ]
        out += [
            f"{name} {s.id} 不可填 figure（只有情境物件可以）"
            for name, spots in (("campfires", self.campfires), ("event_spots", self.event_spots))
            for s in spots
            if s.figure is not None
        ]
        if not self.is_capital:
            out += [
                f"情境物件 {s.id} 的 panel／stele_region 只有主城可以用"
                for s in self.situation_objects
                if s.panel is not None or s.stele_region is not None
            ]
        return out

    def _kind_problems(self) -> list[str]:
        if (self.location is None) == (self.interior_of is None):
            return ["location 與 interior_of 必須恰好填一個"]
        if not self.is_interior:
            if self.layout == "interior":
                return ["室外圖的 layout 不可是 interior"]
            return []
        out: list[str] = []
        if self.layout not in (None, "interior"):
            out.append("室內圖的 layout 只能是 interior")
        if self.doors or self.teleport_stones:
            out.append("室內圖不可有門或傳送石")
        if not self.exits:
            out.append("室內圖至少要有 1 個出口")
        return out

    def _id_problems(self) -> list[str]:
        out: list[str] = []
        portal_ids = [e.id for e in self.exits] + [d.id for d in self.doors]
        portal_ids += [s.id for s in self.teleport_stones]
        out += [f"出口、門、傳送石的 ID {i} 重複" for i in duplicates(portal_ids)]
        out += [f"NPC {i} 重複" for i in duplicates(n.id for n in self.npcs)]
        targets = [f"{e.region or self.region}/{e.to}" for e in self.exits]
        out += [f"往 {t} 的出口重複（一條連線＝一對出口）" for t in duplicates(targets)]
        spots = {o.id for o in self.situation_objects}
        for exit_ in self.exits:
            cells = [f"{x},{y}" for x, y in exit_.at]
            if duplicates(cells):
                out.append(f"出口 {exit_.id} 的格子重複")
            gate = exit_.gate
            if gate is not None and gate.spot is not None and gate.spot not in spots:
                out.append(f"出口 {exit_.id} 的 gate.spot {gate.spot} 不是這張圖的情境物件")
        return out

    def _placed(self) -> list[tuple[str, XY]]:
        placed: list[tuple[str, XY]] = [("entry", self.entry)]
        placed += [(f"出口 {e.id}", c) for e in self.exits for c in e.at]
        placed += [(f"門 {d.id}", d.at) for d in self.doors]
        placed += [(f"傳送石 {s.id}", s.at) for s in self.teleport_stones]
        placed += [(f"NPC {n.id}", n.at) for n in self.npcs]
        placed += [(f"設施 {f.id}", f.at) for f in self.facilities]
        placed += [("objects", o.at) for o in self.objects]
        placed += [("surfaces", s.at) for s in self.surfaces]
        for spawn in self.spawns:
            placed.append((f"spawns {spawn.group}", spawn.at))
            placed += [(f"spawns {spawn.group} 的巡邏點", p) for p in spawn.patrol]
        for name, spots in (
            ("campfires", self.campfires),
            ("event_spots", self.event_spots),
            ("situation_objects", self.situation_objects),
        ):
            placed += [(f"{name} {s.id}", s.at) for s in spots]
        return placed

    def _decor_problems(self) -> list[str]:
        """裝飾（``look.decor``，6V-4b）整件要在地圖內；除了鋪法以外，兩件裝飾不可疊在同一格。"""
        out: list[str] = []
        seen: dict[XY, str] = {}
        for d in self.look.decor:
            cells = d.cells()
            if not all(self.in_bounds(*c) for c in cells):
                out.append(f"裝飾 {d.kind} {list(d.at)} 超出地圖範圍")
                continue
            if d.kind == "radial_paving":
                continue
            for c in cells:
                if c in seen:
                    out.append(f"裝飾 {d.kind} {list(d.at)} 和 {seen[c]} 疊在 {list(c)}")
                    break
                seen[c] = f"{d.kind} {list(d.at)}"
        return out

    def _bounds_problems(self) -> list[str]:
        return [
            f"{what} 的 {list(at)} 超出地圖範圍"
            for what, at in self._placed()
            if not self.in_bounds(*at)
        ]

    def _edge_problems(self) -> list[str]:
        return [
            f"出口 {e.id} 的 {list(c)} 不在地圖邊緣"
            for e in self.exits
            for c in e.at
            if not _is_edge(c, self.size)
        ]

    def _overlap_problems(self) -> list[str]:
        """出口、門、傳送石、入口、NPC 彼此不重疊；物件、表面每格最多一個。"""
        owners: dict[XY, str] = {}
        out: list[str] = []
        for what, at in self._placed():
            if what in ("objects", "surfaces") or what.startswith(("設施", "spawns")):
                continue
            if what.startswith(("campfires", "event_spots", "situation_objects")):
                continue
            if at in owners:
                out.append(f"{what} 與 {owners[at]} 都在 {list(at)}")
            else:
                owners[at] = what
        for what, spots in (
            ("objects", [o.at for o in self.objects]),
            ("surfaces", [s.at for s in self.surfaces]),
        ):
            dup = sorted({c for c in spots if spots.count(c) > 1})
            out += [f"{what} 的 {list(c)} 重複（每格最多一個）" for c in dup]
        return out

    def _building_problems(self) -> list[str]:
        """建築（只畫）只能疊在牆格或門格上，不可超出地圖、蓋到出口或彼此重疊（6B-ART1）。"""
        if not self.buildings:
            return []
        terrain = [[t for _h, t in row] for row in self.grid()]
        doors = {d.at for d in self.doors}
        exits = {c for e in self.exits for c in e.at}
        water = {s.at for s in self.surfaces if s.surface == "water"}
        owner: dict[XY, int] = {}
        out: list[str] = []
        for i, b in enumerate(self.buildings):
            name = f"建築 {b.kind} {list(b.at)}"
            cells = b.cells()
            if any(not self.in_bounds(*c) for c in cells):
                out.append(f"{name} 超出地圖範圍")
                continue
            out += [f"{name} 蓋到出口的 {list(c)}" for c in cells if c in exits]
            allowed = doors | (water if b.kind in WATER_BUILDINGS else set())
            out += [
                f"{name} 的 {list(c)} 不是牆也不是門"
                for c in cells
                if c not in exits and c not in allowed and terrain[c[1]][c[0]] != "wall"
            ]
            for c in cells:
                if c in owner:
                    out.append(f"{name} 與第 {owner[c] + 1} 棟建築在 {list(c)} 重疊")
                    break
                owner[c] = i
        return out


# ---------------------------------------------------------------------------
# 跨檔案檢查
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldMapReport:
    """:func:`field_map_report` 的結果：錯誤（載入失敗）、警告（數值類，不影響通過）、待補（對面的
    地圖還沒畫，配對之後再檢查）。三者都已排序。"""

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    pending: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegionProgress:
    """一區的實地地圖進度（``content check`` 印「雲嶺 x／18」）。"""

    region: str
    name_zh: str
    done: int
    total: int


@dataclass
class _Ctx:
    world_maps: Mapping[str, LocationMapDef]
    outdoor: dict[tuple[str, str], FieldMapDef]
    interiors: dict[tuple[str, str], FieldMapDef]
    errors: list[str]
    warnings: list[str]
    pending: list[str]

    def loc(self, region: str, location: str) -> LocationDef | None:
        world_map = self.world_maps.get(region)
        if world_map is None:
            return None
        return world_map.location_by_id().get(location)


def field_map_problems(
    fields: Mapping[str, FieldMapDef],
    *,
    world_maps: Mapping[str, LocationMapDef],
    terrain: dict[str, TerrainDef],
    objects: dict[str, ObjectDef],
    core: CoreRules,
    npcs: Mapping[str, Mapping[str, str]] | None = None,
    quest_steps: Mapping[str, Mapping[str, Sequence[str]]] | None = None,
) -> list[str]:
    """:func:`field_map_report` 的錯誤清單（空＝通過）。"""
    report = field_map_report(
        fields,
        world_maps=world_maps,
        terrain=terrain,
        objects=objects,
        core=core,
        npcs=npcs,
        quest_steps=quest_steps,
    )
    return list(report.errors)


def field_map_report(
    fields: Mapping[str, FieldMapDef],
    *,
    world_maps: Mapping[str, LocationMapDef],
    terrain: dict[str, TerrainDef],
    objects: dict[str, ObjectDef],
    core: CoreRules,
    npcs: Mapping[str, Mapping[str, str]] | None = None,
    quest_steps: Mapping[str, Mapping[str, Sequence[str]]] | None = None,
) -> FieldMapReport:
    """實地地圖的跨檔案檢查（Phase 6 計畫 2.3）。

    ``fields`` 的鍵是地圖 ID；``npcs`` 是「區域 → NPC ID → 人設卡的地點」（``None``＝不檢查 NPC；
    沒有該區的鍵＝那一區不檢查）。``quest_steps`` 是「區域 → 任務 ID → 步驟 ID（依序）」
    （``world_quests``；``None``＝不檢查出口 gate）：出口的 ``gate.quest`` 必須是地圖 **同區** 的
    任務（:func:`trpg.world.field.exit_open` 用地圖的區域找任務）、``gate.step`` 必須是它的步驟；
    沒有該區的鍵＝那一區沒有任務，有 gate 就是錯誤。
    """
    ctx = _Ctx(world_maps, {}, {}, [], [], [])
    for map_id in sorted(fields):
        _index(ctx, fields[map_id])
    for map_id in sorted(fields):
        field = fields[map_id]
        _tile_problems(ctx, field, terrain, objects, core)
        if npcs is not None:
            _npc_problems(ctx, field, npcs)
        if quest_steps is not None:
            _gate_problems(ctx, field, quest_steps.get(field.region, {}))
    for key in sorted(ctx.outdoor):
        if key[0] == CAPITAL_REGION:
            _capital_links(ctx, ctx.outdoor[key])
        else:
            _outdoor_links(ctx, ctx.outdoor[key])
    for key in sorted(ctx.interiors):
        _interior_links(ctx, ctx.interiors[key])
    for map_id in sorted(fields):
        if fields[map_id].is_capital:
            _safe_zone_problems(ctx, fields[map_id])
    _size_warnings(ctx, fields)
    _building_warnings(ctx, fields)
    _stone_checks(ctx)
    return FieldMapReport(
        errors=tuple(sorted(ctx.errors)),
        warnings=tuple(sorted(ctx.warnings)),
        pending=tuple(sorted(ctx.pending)),
    )


def field_progress(
    world_maps: Mapping[str, LocationMapDef], fields: Mapping[str, FieldMapDef]
) -> list[RegionProgress]:
    """每區有實地地圖的地點數／地點總數（室內圖不算）；依區域等級、ID 排序，最後是主城（1 張，
    6D-4）。"""
    done: dict[str, set[str]] = {}
    for field in fields.values():
        if field.location is not None:
            done.setdefault(field.region, set()).add(field.location)
    ordered = sorted(world_maps.values(), key=lambda m: (m.level_min, m.region))
    regions = [
        RegionProgress(
            region=m.region,
            name_zh=m.name_zh,
            done=len(done.get(m.region, set()) & {loc.id for loc in m.locations}),
            total=len(m.locations),
        )
        for m in ordered
    ]
    capital = RegionProgress(
        region=CAPITAL_REGION,
        name_zh=CAPITAL_NAME_ZH,
        done=len(done.get(CAPITAL_REGION, set()) & {CAPITAL_LOCATION}),
        total=1,
    )
    return [*regions, capital]


def _index(ctx: _Ctx, field: FieldMapDef) -> None:
    prefix = f"實地地圖 {field.id}"
    if field.is_capital:
        if field.place != CAPITAL_LOCATION:
            what = "interior_of" if field.is_interior else "location"
            ctx.errors.append(f"{prefix}：主城的 {what} 必須是 {CAPITAL_LOCATION}")
            return
    elif field.region not in ctx.world_maps:
        ctx.errors.append(f"{prefix}：未知的區域 {field.region}（沒有地點圖）")
        return
    elif ctx.loc(field.region, field.place) is None:
        ctx.errors.append(f"{prefix}：區域 {field.region} 沒有地點 {field.place}")
        return
    if field.is_interior:
        ctx.interiors[(field.region, field.id)] = field
        return
    key = (field.region, field.place)
    if key in ctx.outdoor:
        other = ctx.outdoor[key].id
        ctx.errors.append(f"{prefix}：地點 {field.place} 已有實地地圖 {other}")
        return
    ctx.outdoor[key] = field


# ---- 地形、物件、走得到 ----


def _tile_problems(
    ctx: _Ctx,
    field: FieldMapDef,
    terrain: dict[str, TerrainDef],
    objects: dict[str, ObjectDef],
    core: CoreRules,
) -> None:
    prefix = f"實地地圖 {field.id}"
    unknown = sorted({tid for tid in field.legend.values() if tid not in terrain})
    if unknown:
        ctx.errors.append(f"{prefix}：legend 使用了未知的地形：{', '.join(unknown)}")
        return
    unknown_objects = sorted({o.kind for o in field.objects if o.kind not in objects})
    if unknown_objects:
        ctx.errors.append(f"{prefix}：objects 使用了未知的物件：{', '.join(unknown_objects)}")
        return
    grid = field.grid()
    problems = placement_problems(grid, field.objects, field.surfaces, terrain)
    passable = passable_grid(field, terrain, objects)
    problems += _standing_problems(field, passable)
    if not problems:
        problems += _reach_problems(field, grid, passable, core)
    ctx.errors += [f"{prefix}：{p}" for p in problems]


def _standing_problems(field: FieldMapDef, passable: Passable) -> list[str]:
    """要站上去的格子（入口、出口、門、傳送石、NPC、敵人與巡邏點）必須可站立。"""
    cells: list[tuple[str, XY]] = [("entry", field.entry)]
    cells += [(f"出口 {e.id}", c) for e in field.exits for c in e.at]
    cells += [(f"門 {d.id}", d.at) for d in field.doors]
    cells += [(f"傳送石 {s.id}", s.at) for s in field.teleport_stones]
    cells += [(f"NPC {n.id}", n.at) for n in field.npcs]
    for spawn in field.spawns:
        cells.append((f"spawns {spawn.group}", spawn.at))
        cells += [(f"spawns {spawn.group} 的巡邏點", p) for p in spawn.patrol]
    return [
        f"{what} 的 {list(at)} 位於不可站立的格子"
        for what, at in cells
        if not passable[at[1]][at[0]]
    ]


def _neighbors(cell: XY) -> list[XY]:
    x, y = cell
    return [(x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)]


def _reach_problems(
    field: FieldMapDef, grid: list[list[tuple[int, str]]], passable: Passable, core: CoreRules
) -> list[str]:
    """從 ``entry`` 走得到每個出口格、門、傳送石，以及 NPC 與設施的旁邊（Phase 6 計畫 2.3
    第 4 條）。"""
    reach = reachable_from(field.entry, grid, passable, core)
    out = [
        f"從 entry 走不到出口 {e.id} 的 {list(c)}"
        for e in field.exits
        for c in e.at
        if c not in reach
    ]
    out += [f"從 entry 走不到門 {d.id}" for d in field.doors if d.at not in reach]
    out += [f"從 entry 走不到傳送石 {s.id}" for s in field.teleport_stones if s.at not in reach]
    out += [
        f"從 entry 走不到 NPC {n.id} 的旁邊"
        for n in field.npcs
        if not any(c in reach for c in _neighbors(n.at))
    ]
    out += [
        f"從 entry 走不到設施 {f.id} 的旁邊"
        for f in field.facilities
        if f.at not in reach and not any(c in reach for c in _neighbors(f.at))
    ]
    return out


def _gate_problems(ctx: _Ctx, field: FieldMapDef, quests: Mapping[str, Sequence[str]]) -> None:
    """出口 gate 的任務與步驟要存在（6R-P）：寫錯的話出口永遠打不開（只剩 ``open_flag``）。"""
    for exit_ in field.exits:
        gate = exit_.gate
        if gate is None:
            continue
        prefix = f"實地地圖 {field.id}：出口 {exit_.id} 的 gate"
        steps = quests.get(gate.quest)
        if steps is None:
            ctx.errors.append(f"{prefix}.quest {gate.quest} 不是 {field.region} 的任務")
        elif gate.step not in steps:
            ctx.errors.append(f"{prefix}.step {gate.step} 不是任務 {gate.quest} 的步驟")


def _npc_problems(ctx: _Ctx, field: FieldMapDef, npcs: Mapping[str, Mapping[str, str]]) -> None:
    if field.is_capital:
        ctx.errors += [
            f"實地地圖 {field.id}：NPC {n.id} 沒有人設卡（主城的功能型 NPC 用 facilities 或 "
            "situation_objects，草稿待確認 2）"
            for n in field.npcs
        ]
        return
    cards = npcs.get(field.region)
    if cards is None:
        return  # 這區沒有 NPC 人設卡檔（內容庫允許省略 world/npcs/），無從比對
    for npc in field.npcs:
        home = cards.get(npc.id)
        if home is None:
            ctx.errors.append(f"實地地圖 {field.id}：NPC {npc.id} 不是 {field.region} 的人設卡")
        elif home != field.place:
            ctx.errors.append(
                f"實地地圖 {field.id}：NPC {npc.id} 的人設卡在 {home}，不在 {field.place}"
            )


# ---- 出口與門的配對 ----


def _outdoor_links(ctx: _Ctx, field: FieldMapDef) -> None:
    for exit_ in field.exits:
        _check_exit(ctx, field, exit_)
    for door in field.doors:
        _check_door(ctx, field, door)
    _edge_coverage(ctx, field)


def _check_exit(ctx: _Ctx, field: FieldMapDef, exit_: FieldExit) -> None:
    prefix = f"實地地圖 {field.id} 的出口 {exit_.id}"
    region = exit_.region or field.region
    target = ctx.loc(region, exit_.to)
    if target is None:
        ctx.errors.append(f"{prefix}：區域 {region} 沒有地點 {exit_.to}")
        return
    if region == field.region:
        problem = _same_region_exit_problem(ctx, field, exit_, target)
    else:
        problem = _cross_region_exit_problem(ctx, field, region)
    if problem:
        ctx.errors.append(f"{prefix}：{problem}")
        return
    far = ctx.outdoor.get((region, exit_.to))
    if far is None:
        ctx.pending.append(f"{prefix} → {region}/{exit_.to}：對面還沒有實地地圖，配對待補")
        return
    problem = _arrive_problem(field, exit_, far)
    if problem:
        ctx.errors.append(f"{prefix}：{problem}")


def _same_region_exit_problem(
    ctx: _Ctx, field: FieldMapDef, exit_: FieldExit, target: LocationDef
) -> str:
    world_map = ctx.world_maps[field.region]
    if exit_.to not in world_map.neighbors(field.place):
        return f"地點圖上沒有 {field.place}–{exit_.to} 的連線（沒有連線的出口算錯）"
    here = ctx.loc(field.region, field.place)
    if target.hidden and here is not None and not here.hidden:
        return f"{exit_.to} 是隱藏地點，入口要用 doors（hidden_until: reveal），不用出口"
    return ""


def _cross_region_exit_problem(ctx: _Ctx, field: FieldMapDef, region: str) -> str:
    """跨區出口只有兩種情形合法：本地點是通往 ``region`` 的傳送點（渡口是路徑圖）；或本地點與通往
    ``region`` 的傳送點相連、而那個傳送點沒有實地地圖（渡口只是出口）。"""
    here = ctx.loc(field.region, field.place)
    if here is not None and here.kind == "gate" and here.gate_to == region:
        return ""
    if _gates_as_exit(ctx, field, region):
        return ""
    return f"只有通往 {region} 的渡口（傳送點）可以放跨區出口"


def _gates_as_exit(ctx: _Ctx, field: FieldMapDef, region: str) -> list[str]:
    """與本地點相連、通往 ``region``、而且沒有實地地圖的傳送點（「渡口只是出口」寫法）。"""
    world_map = ctx.world_maps[field.region]
    out: list[str] = []
    for neighbor in world_map.neighbors(field.place):
        loc = ctx.loc(field.region, neighbor)
        if loc is None or loc.kind != "gate" or loc.gate_to != region:
            continue
        if (field.region, neighbor) not in ctx.outdoor:
            out.append(neighbor)
    return out


def _arrive_problem(field: FieldMapDef, exit_: FieldExit, far: FieldMapDef) -> str:
    """``exit_`` 與對面地圖 ``far`` 上的 ``arrive`` 是否互指。"""
    back = far.portal(exit_.arrive)
    if back is None:
        return f"arrive {exit_.arrive} 不是 {far.id} 的出口或門"
    if back.to != field.place:
        return f"{far.id} 的 {back.id} 通往 {back.to}，不是 {field.place}（arrive 不互指）"
    if isinstance(back, FieldDoor):
        return ""  # 從隱藏地點回到相鄰地圖的門（門沒有 arrive）
    if (back.region or far.region) != field.region:
        return f"{far.id} 的 {back.id} 通往區域 {back.region}，不是 {field.region}（arrive 不互指）"
    if back.arrive != exit_.id:
        return f"{far.id} 的 {back.id} 的 arrive 是 {back.arrive}，不是 {exit_.id}（arrive 不互指）"
    return ""


def _check_door(ctx: _Ctx, field: FieldMapDef, door: FieldDoor) -> None:
    prefix = f"實地地圖 {field.id} 的門 {door.id}"
    interior = ctx.interiors.get((field.region, door.to))
    if interior is not None:
        if interior.interior_of != field.place:
            ctx.errors.append(
                f"{prefix}：室內圖 {door.to} 屬於 {interior.interior_of}，不是 {field.place}"
            )
        elif not any(e.arrive == door.id for e in interior.exits):
            ctx.errors.append(f"{prefix}：室內圖 {door.to} 沒有 arrive 指向這扇門的出口")
        return
    target = ctx.loc(field.region, door.to)
    if target is None:
        ctx.errors.append(f"{prefix}：{door.to} 不是本地點的室內圖，也不是本區的地點")
        return
    problem = _hidden_door_problem(ctx, field, door, target)
    if problem:
        ctx.errors.append(f"{prefix}：{problem}")
        return
    far = ctx.outdoor.get((field.region, door.to))
    if far is None:
        ctx.pending.append(f"{prefix} → {field.region}/{door.to}：對面還沒有實地地圖，配對待補")
        return
    if not any(e.to == field.place and e.arrive == door.id for e in far.exits):
        ctx.errors.append(f"{prefix}：{far.id} 沒有回到 {field.place}、arrive 指向這扇門的出口")


def _hidden_door_problem(
    ctx: _Ctx, field: FieldMapDef, door: FieldDoor, target: LocationDef
) -> str:
    if not target.hidden:
        return f"{door.to} 不是隱藏地點；一般連線要用出口"
    if door.to not in ctx.world_maps[field.region].neighbors(field.place):
        return f"地點圖上沒有 {field.place}–{door.to} 的連線"
    if door.hidden_until != "reveal":
        return f"通往隱藏地點 {door.to} 的入口要寫 hidden_until: reveal"
    return ""


def _edge_coverage(ctx: _Ctx, field: FieldMapDef) -> None:
    """地點圖上這個地點的每條連線都有出口（或隱藏地點的門）；渡口路徑圖要有跨區出口。"""
    prefix = f"實地地圖 {field.id}"
    here = ctx.loc(field.region, field.place)
    assert here is not None
    exits_to = {e.to for e in field.exits if (e.region or field.region) == field.region}
    doors_to = {d.to for d in field.doors}
    cross = {e.region for e in field.exits if e.region not in (None, field.region)}
    for neighbor in ctx.world_maps[field.region].neighbors(field.place):
        loc = ctx.loc(field.region, neighbor)
        assert loc is not None
        if loc.hidden and not here.hidden:
            if neighbor not in doors_to:
                ctx.errors.append(
                    f"{prefix}：缺少往隱藏地點 {neighbor} 的門（hidden_until: reveal）"
                )
            continue
        if neighbor in exits_to:
            continue
        as_exit = loc.kind == "gate" and loc.gate_to in cross
        if as_exit and (field.region, neighbor) not in ctx.outdoor:
            continue  # 「渡口只是出口」：跨區出口就是這條連線
        ctx.errors.append(f"{prefix}：缺少往 {neighbor} 的出口（一條連線＝一對出口）")
    if here.kind == "gate" and here.gate_to not in cross:
        ctx.errors.append(
            f"{prefix}：渡口圖要有通往區域 {here.gate_to} 的出口（region: {here.gate_to}）"
        )


def _capital_links(ctx: _Ctx, field: FieldMapDef) -> None:
    """主城：沒有走路的出口（只能傳送抵達，21.1）；門只通往主城的室內圖。"""
    prefix = f"實地地圖 {field.id}"
    ctx.errors += [
        f"{prefix} 的出口 {e.id}：主城沒有走路的出口（只能傳送抵達；浮橋用 situation_objects）"
        for e in field.exits
    ]
    for door in field.doors:
        if (CAPITAL_REGION, door.to) not in ctx.interiors:
            ctx.errors.append(f"{prefix} 的門 {door.id}：{door.to} 不是主城的室內圖")
        else:
            _check_door(ctx, field, door)


def _safe_zone_problems(ctx: _Ctx, field: FieldMapDef) -> None:
    """主城（含室內）是安全區：沒有敵人、沒有營火（草稿第 4 節：不能紮營，直接休息）。"""
    prefix = f"實地地圖 {field.id}"
    if field.spawns:
        ctx.errors.append(f"{prefix}：主城是安全區，不可有 spawns")
    if field.campfires:
        ctx.errors.append(f"{prefix}：主城不能紮營，不可有 campfires")


def _interior_links(ctx: _Ctx, field: FieldMapDef) -> None:
    prefix = f"室內圖 {field.id}"
    parent = ctx.outdoor.get((field.region, field.place))
    if parent is None:
        ctx.errors.append(f"{prefix}：所屬的地點 {field.place} 還沒有實地地圖")
        return
    for exit_ in field.exits:
        if exit_.region not in (None, field.region) or exit_.to != field.place:
            ctx.errors.append(f"{prefix} 的出口 {exit_.id}：室內圖的出口只能回到 {field.place}")
            continue
        door = parent.portal(exit_.arrive)
        if not isinstance(door, FieldDoor) or door.to != field.id:
            ctx.errors.append(
                f"{prefix} 的出口 {exit_.id}：arrive {exit_.arrive} 不是 {parent.id} 上通往這裡的門"
            )


# ---- 數值類：尺寸、傳送石 ----


def _building_warnings(ctx: _Ctx, fields: Mapping[str, FieldMapDef]) -> None:
    """不認得的建築外觀（前端退回 ``house``；6B-ART1）。"""
    for map_id in sorted(fields):
        for b in fields[map_id].buildings:
            if b.kind not in BUILDING_KINDS:
                ctx.warnings.append(f"實地地圖 {map_id}：建築外觀 {b.kind} 不認得（畫成 house）")


def _size_warnings(ctx: _Ctx, fields: Mapping[str, FieldMapDef]) -> None:
    for map_id in sorted(fields):
        field = fields[map_id]
        layout = field.layout_for(ctx.loc(field.region, field.place))
        (long_lo, long_hi), (short_lo, short_hi) = LAYOUT_SIZES[layout]
        long_side, short_side = max(field.size), min(field.size)
        if long_lo <= long_side <= long_hi and short_lo <= short_side <= short_hi:
            continue
        ctx.warnings.append(
            f"實地地圖 {field.id}：{field.width}×{field.height} 不在 {layout} 的建議範圍"
            f"（長邊 {long_lo}～{long_hi}、短邊 {short_lo}～{short_hi}，21.3）"
        )


def _stone_checks(ctx: _Ctx) -> None:
    by_region: dict[str, list[str]] = {}
    seen: dict[str, str] = {}
    fields = [ctx.outdoor[k] for k in sorted(ctx.outdoor)] + [
        ctx.interiors[k] for k in sorted(ctx.interiors)
    ]
    for field in fields:
        for stone in field.teleport_stones:
            if stone.id in seen:
                ctx.errors.append(f"傳送石 ID {stone.id} 重複（{seen[stone.id]}、{field.id}）")
            seen[stone.id] = field.id
            loc = ctx.loc(field.region, field.place)
            if field.is_capital:
                continue  # 主城的 1 個另外算（_map_stone_checks），不屬於任何區
            if loc is None or loc.kind != "town":  # 城鎮的 1 個另外算（_map_stone_checks）
                by_region.setdefault(field.region, []).append(stone.id)
        _map_stone_checks(ctx, field)
    lo, hi = STONES_PER_REGION
    for region in sorted({f.region for f in fields if not f.is_capital}):
        count = len(by_region.get(region, []))
        if lo <= count <= hi:
            continue
        text = f"區域 {region}：傳送石 {count} 個，應為 {lo}～{hi} 個"
        if _region_drawn(ctx, region):
            ctx.errors.append(text)
        else:  # 地點還沒畫完：之後補上的地圖可能有傳送石（6D-R1）
            ctx.pending.append(f"{text}（地點還沒畫完，畫完再判）")


def _region_drawn(ctx: _Ctx, region: str) -> bool:
    """這一區地點圖上的每個地點都有室外圖了（6D-R1：傳送石數畫完才判）。"""
    world_map = ctx.world_maps.get(region)
    if world_map is None:
        return False
    return all((region, loc.id) in ctx.outdoor for loc in world_map.locations)


def _map_stone_checks(ctx: _Ctx, field: FieldMapDef) -> None:
    if field.is_capital and not field.is_interior:
        count = len(field.teleport_stones)
        if count != 1:
            ctx.errors.append(f"實地地圖 {field.id}：主城要有 1 個傳送石，目前 {count} 個")
        return
    loc = ctx.loc(field.region, field.place)
    if loc is None:
        return
    if loc.kind == "boss" and field.campfires:
        # 21.10 第 24 條：打贏 Boss 不寫「已清空」，Boss 地點（含前廳與室內圖，6D-R1）的營火點永遠
        # 用不到；室內圖照所屬地點（``place``）判斷
        ctx.errors.append(f"實地地圖 {field.id}：Boss 地點 {loc.id} 不可放營火點")
    if field.is_interior:
        return
    count = len(field.teleport_stones)
    if loc.kind == "boss" and count:
        # 雲頂觀只從源晶裂痕進入（18.3、21.2）：Boss 地點不能有傳送石
        ctx.errors.append(
            f"實地地圖 {field.id}：Boss 地點 {loc.id} 只能從相連的地點走進去，不可有傳送石"
        )
    if loc.kind == "town" and count != 1:
        ctx.errors.append(f"實地地圖 {field.id}：城鎮應有 1 個傳送石，目前 {count} 個")
