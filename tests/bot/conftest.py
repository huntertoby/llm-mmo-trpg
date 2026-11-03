"""``tests/bot`` 共用的 fixture（不需網路）。"""

from __future__ import annotations

import pytest

from trpg.content.library import ContentLibrary, load_library


@pytest.fixture(scope="session")
def library() -> ContentLibrary:
    return load_library()
