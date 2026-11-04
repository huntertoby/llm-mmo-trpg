"""等待動畫的短句（``content/ui/narration_wait.yaml``，Phase RT-3）。

設計見 ``docs/art/等待動畫.md`` 第 3 節。純前端資料：``client/src/ui/waitNarration.ts``
在 build 時匯入同一份檔，四個等待場合各一組短句輪替；不呼叫 LLM、不進引擎結算。
Python 端只驗證 schema（``trpg content check``）。
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, model_validator

from trpg.content.schemas import ContentModel

__all__ = ["ARCHAIC_WORDS", "WAIT_SCENES", "WaitNarration", "WaitSceneLines"]

WAIT_SCENES: tuple[str, ...] = ("skill", "judge", "npc", "retell")
"""四個等待場合（與前端 ``WAIT_SCENES`` 相同）。"""

ARCHAIC_WORDS: tuple[str, ...] = ("墨滴", "宣紙", "毛筆", "蘸墨")
"""C 羽毛筆羊皮紙定稿後不用的古風用詞（等待動畫.md 第 3 節）。"""

Line = Annotated[str, Field(min_length=1, max_length=30)]


class WaitSceneLines(ContentModel):
    """一個場合的短句：輪替的句子與等太久的提示句。"""

    lines: tuple[Line, ...] = Field(min_length=1, max_length=8)
    long: Line


class WaitNarration(ContentModel):
    """``content/ui/narration_wait.yaml``：四個場合的短句、失敗句與輪替時間。"""

    rotate_ms: Annotated[int, Field(ge=1000, le=20000)]
    long_ms: Annotated[int, Field(ge=1000, le=60000)]
    fail: Line
    scenes: dict[str, WaitSceneLines]

    @model_validator(mode="after")
    def _check(self) -> WaitNarration:
        names = sorted(self.scenes)
        if names != sorted(WAIT_SCENES):
            raise ValueError(f"場合必須剛好是 {', '.join(WAIT_SCENES)}，現在是 {', '.join(names)}")
        texts = [self.fail]
        for scene in WAIT_SCENES:
            s = self.scenes[scene]
            texts.extend([*s.lines, s.long])
        for text in texts:
            plain = text.replace("羽毛筆", "")  # 「羽毛筆」裡的「毛筆」不算
            bad = [w for w in ARCHAIC_WORDS if w in plain]
            if bad:
                raise ValueError(f"短句不用古風詞（{'、'.join(bad)}）：{text}")
        for scene in WAIT_SCENES:
            if scene == "npc":
                continue
            s = self.scenes[scene]
            if any("{name}" in t for t in (*s.lines, s.long)):
                raise ValueError(f"只有 npc 的短句可以用 {{name}}：{scene}")
        if self.long_ms < self.rotate_ms:
            raise ValueError("long_ms 不能比 rotate_ms 短")
        return self

    def summary(self) -> str:
        n = sum(len(s.lines) + 1 for s in self.scenes.values())
        return f"等待短句 {len(self.scenes)} 個場合、{n} 句"
