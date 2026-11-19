"""X10-2a：程式認得 ``quantity_scale``（``docs/phases/PhaseX10-2a計畫.md``）。

內容的 ``quantity_scale`` 是 1，所有結果都不變；這裡把它換成 10 檢查各處的倍率。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.rules import CoreRules


def test_content_scale_is_one(library: ContentLibrary) -> None:
    assert library.ruleset.core.quantity_scale == 1


@pytest.mark.parametrize("value", [0, 2, 5, 100])
def test_scale_accepts_only_one_or_ten(library: ContentLibrary, value: int) -> None:
    data = library.ruleset.core.model_dump()
    assert CoreRules.model_validate({**data, "quantity_scale": 10}).quantity_scale == 10
    with pytest.raises(ValidationError):
        CoreRules.model_validate({**data, "quantity_scale": value})
