"""內容數量快照沒過期（Phase WL-1，``tests/content_counts.py``）。"""

from __future__ import annotations

from tests.content_counts import COUNTERS, COUNTS, compute
from trpg.content.library import ContentLibrary


def test_the_snapshot_matches_the_bundled_content(content_library: ContentLibrary) -> None:
    computed = compute(content_library)
    assert computed == COUNTS, (
        "內容數量變了：跑 uv run python -m tests.content_counts 重產快照、看 diff"
    )


def test_every_counter_has_a_snapshot_entry() -> None:
    assert sorted(COUNTS) == sorted(COUNTERS)
