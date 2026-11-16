"""許願池面板的 API 模型（Phase WP-2；組法在 :mod:`trpg.api.world_wish_view`）。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from trpg.api.world_range_schemas import RangeSpeakerView

__all__ = ["WishMenuItemView", "WishTagGroupView", "WishView"]


class _ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WishMenuItemView(_ApiModel):
    """選單的一個關鍵字（「改用選單」挑 1～2 個）。"""

    id: str
    name_zh: str
    description_zh: str
    """一句說明（內容庫 ``skill_keywords.yaml`` 的 ``description_zh``）。"""


class WishTagGroupView(_ApiModel):
    """PK-4 願望驅動：標籤清單的一類（沒有 LLM 時玩家從這份清單點選；07 7.6「許願池：願望驅動」
    第 1 點）。``id`` 是 ``keywords``／``elements``／``effects``／``shapes``／``kinds``（送出
    ``wish`` 動作的 ``tags`` 用同名欄位）。"""

    id: str
    label_zh: str
    """類別名稱（關鍵字、元素、效果類型、形狀、種類）。"""
    max: int
    """這一類最多選幾個（每一類都可以不選；全部加起來至少 1 個）。"""
    items: tuple[WishMenuItemView, ...]
    """可以選的值（``description_zh`` 只有關鍵字有，其他是空字串）。"""


class WishView(_ApiModel):
    """``WorldView.wish``（WP-2；07 7.6、#88）：主城許願池的面板資料。人在主城才有，其他 ``None``。
    能不能許與原因和 ``wish`` 動作用同一個函式（:func:`trpg.world.wish.wish_problem`），所以畫面的
    原因句和送出被拒的那一句相同。"""

    title_zh: str
    """面板標頭（主城地圖上許願池物件的名字）。"""
    speaker: RangeSpeakerView | None = None
    """守池人的頭像（主城實地地圖上的 ``pool_keeper`` 情境物件）。"""
    line_zh: str | None = None
    """標頭下守池人說的一句（同一個物件的 ``note_zh``）。"""
    cost: int
    """每次許願的任務幣。"""
    refund: int
    """三選一都不拿時退還的任務幣（次數照扣）。"""
    coins: int
    """角色現有的任務幣。"""
    left: int
    """本週還能許幾次。"""
    per_week: int
    """每週幾次。"""
    available: bool
    """現在可以許願（``wish`` 動作的資格檢查會過；文字許願另看 LLM 有沒有對到關鍵字）。"""
    blocked_zh: str | None = None
    """不能許的原因（和動作被拒的字相同）；可以時 ``None``。"""
    llm: bool
    """世界的 LLM 開著而且健康檢查沒說不可用：可以用願望文字；``False``＝只顯示選單。"""
    text_max_chars: int
    """願望文字最多幾個字。"""
    max_keywords: int
    """選單一次最多挑幾個關鍵字（最少 1 個、不重複）。"""
    menu: tuple[WishMenuItemView, ...]
    """可以許的關鍵字（內容庫順序；扣掉開局隱藏的）。"""
    tag_groups: tuple[WishTagGroupView, ...] = ()
    """PK-4 願望驅動（``skill_pick.yaml`` 的 ``wish_enabled``）：「從清單挑」改成點選需求標籤
    （五類）；
    空＝舊流程（照 ``menu`` 挑 1～``max_keywords`` 個關鍵字）。"""
