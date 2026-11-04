"""遊戲名稱與標語（``content/ui/game.yaml``，Phase UI-E1）。

純前端資料：``client/src/ui/gameInfo.ts`` 在 build 時匯入同一份檔，首頁標題牌、開發選單、
瀏覽器分頁標題都從這裡讀；名稱定案後只改這一處。Python 端只驗證 schema（``trpg content check``）。
"""

from __future__ import annotations

from pydantic import Field

from trpg.content.schemas import ContentModel

__all__ = ["GameInfo"]


class GameInfo(ContentModel):
    """``content/ui/game.yaml``：遊戲名稱與標語。"""

    title_zh: str = Field(min_length=1, max_length=24)
    tagline_zh: str = Field(min_length=1, max_length=40)

    def summary(self) -> str:
        return f"遊戲名稱「{self.title_zh}」"
