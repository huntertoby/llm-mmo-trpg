"""讓 ``python -m trpg`` 等同 ``trpg`` 指令。"""

import sys

from trpg.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
