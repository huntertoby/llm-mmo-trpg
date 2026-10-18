"""示範地圖的批次模擬：``trpg sim maps`` 的薄包裝（Phase 2C-1 3.2）。

用法::

    uv run python scripts/sim_demo_maps.py [--seeds 20] [--maps bridge_chasm,oil_depot]

與 ``uv run trpg sim maps`` 完全相同（參數也一樣：``--seed-start``、``--jobs``、``--json``）。
批次模擬、指標與技能使用統計在 ``trpg.sim``（``batch.py``、``metrics.py``）。
"""

from __future__ import annotations

import sys

from trpg.cli.main import main

if __name__ == "__main__":
    sys.exit(main(["sim", "maps", *sys.argv[1:]]))
