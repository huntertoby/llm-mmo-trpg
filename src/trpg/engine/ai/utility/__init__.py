"""效用評分 AI（``docs/專案計畫.md`` 5.9）：對每個合法動作跑 ``preview`` 評分，取最高分。

分數 ＝ 預覽收益 ＋ 命中率 × Σ 權重 × (動作後的位置價值 − 動作前的位置價值)，權重來自
``content/ai_profiles.yaml`` 的行為模式（莽夫、弓手、狡猾、守衛）。分數為正的動作中取最高者，
平手依 ``legal_actions`` 的順序；沒有正分的動作時結束回合。全部以 :class:`~fractions.Fraction`
計算，完全確定。

收益的估計：攻擊主要目標的傷害用預覽的精確期望值；其他傷害（爆炸、擴散……）取最少與最多後果
的平均再乘上命中率；「確定」的連鎖乘上命中率，「只是可能」的擊倒再除以 4。這些是啟發式，
供 Phase 2 以模擬調整。

掩護（Phase 1C）：位置價值的 ``cover`` 為「看得到、且從其位置看過來我受到半掩護」的敵人數；
收益的 ``expose`` 為動作讓幾名敵人離開掩護（被推離或掩護物被摧毀），``cover_damage`` 為對
「緊鄰敵人的掩護物」造成的每點傷害。

接近（Phase 2C-4）：位置價值的 ``approach`` 用「走路的步數」（繞過牆、深淵、岩漿，不看單位）而不是
曼哈頓距離。否則隔著河的雙方，在橋被燒斷、只剩一條繞遠的陸路時，任何一步繞路都會讓距離變大而
沒有正分，永遠不會接近（``lava_crossing`` 的平手）。走路步數每次決策只算一次（:class:`_Walk`）。

效能（Phase 1C 決定 #1）：每次決策只算一次「動作前」的位置價值；``Move`` 先以「直接把行動者放到
目的地」的位置價值（不跑引擎）排序，只保留前 ``move_candidates`` 個（``ai_profiles.yaml``）；
其中有風險的移動（可能被藉機攻擊、踩上有進入效果的表面、墜落、撤離、倒地站起）才跑完整
``preview``。沒有風險的移動結果是確定的（只有位置改變），其分數與完整預覽算出的分數相同。
``preview`` 本身在最少後果的模擬沒有經過分歧點時也只模擬一次。

技能（Phase 2A）：每個技能的選取先以便宜的估計（:func:`skill_estimate`）篩選與排序，每種技能只保留
前 ``skill_candidates`` 個跑完整 ``preview``；分數＝預覽收益（每個目標各自的命中率與期望傷害、治療
實際補到的量、友方誤傷與讓友方站上有害表面的扣分、擊倒對抗的成功率）＋位置價值的變化 −
法力與冷卻的機會成本（``mana``、``cooldown`` 權重）。場地型技能（煙幕、石牆、隱匿）沒有敵人在範圍
內也是候選：只要它可能改變自己的處境（涵蓋自己的格子、或擋在敵人與自己之間），由位置價值的差決定
值不值得。

子模組（Phase R1c 自單一檔案拆出，內容未改；外部一律從本套件匯入）：

- :mod:`~trpg.engine.ai.utility.position`：戰術指令、場面快照、走路步數與位置價值。
- :mod:`~trpg.engine.ai.utility.gains`：預覽事件換算的收益項。
- :mod:`~trpg.engine.ai.utility.scoring`：動作評分、改寫類技能分數、技能成本、防禦／撤離／翻越分數。
- :mod:`~trpg.engine.ai.utility.skill_estimate`：技能的便宜估計。
- :mod:`~trpg.engine.ai.utility.moves`：攻擊物件篩選、移動的虛擬分數與風險判定。
- :mod:`~trpg.engine.ai.utility.policy`：:class:`UtilityAI` 本體。
"""

from __future__ import annotations

from trpg.engine.ai.utility.gains import (
    effective_skill as effective_skill,
)
from trpg.engine.ai.utility.moves import (
    ice_slip_cost as ice_slip_cost,
)
from trpg.engine.ai.utility.moves import (
    is_risky_move as is_risky_move,
)
from trpg.engine.ai.utility.moves import (
    reactive_enemies as reactive_enemies,
)
from trpg.engine.ai.utility.moves import (
    virtual_move_score as virtual_move_score,
)
from trpg.engine.ai.utility.moves import (
    worth_previewing as worth_previewing,
)
from trpg.engine.ai.utility.policy import (
    UtilityAI as UtilityAI,
)
from trpg.engine.ai.utility.position import (
    ActionScore as ActionScore,
)
from trpg.engine.ai.utility.position import (
    OrderContext as OrderContext,
)
from trpg.engine.ai.utility.position import (
    OrdersSource as OrdersSource,
)
from trpg.engine.ai.utility.position import (
    _facing_terms as _facing_terms,
)
from trpg.engine.ai.utility.position import (
    _harmful as _harmful,
)
from trpg.engine.ai.utility.position import (
    _knock_collides as _knock_collides,
)
from trpg.engine.ai.utility.position import (
    _scene as _scene,
)
from trpg.engine.ai.utility.position import (
    _unit_position_value as _unit_position_value,
)
from trpg.engine.ai.utility.position import (
    _weapon_terms as _weapon_terms,
)
from trpg.engine.ai.utility.position import (
    position_value as position_value,
)
from trpg.engine.ai.utility.position import (
    resolve_orders as resolve_orders,
)
from trpg.engine.ai.utility.scoring import (
    defend_score as defend_score,
)
from trpg.engine.ai.utility.scoring import (
    extra_targets as extra_targets,
)
from trpg.engine.ai.utility.scoring import (
    run_score as run_score,
)
from trpg.engine.ai.utility.scoring import (
    score_action as score_action,
)
from trpg.engine.ai.utility.scoring import (
    skill_cost as skill_cost,
)
from trpg.engine.ai.utility.scoring import (
    vault_score as vault_score,
)
from trpg.engine.ai.utility.skill_estimate import (
    _charge_estimate as _charge_estimate,
)
from trpg.engine.ai.utility.skill_estimate import (
    _supports as _supports,
)
from trpg.engine.ai.utility.skill_estimate import (
    skill_estimate as skill_estimate,
)

__all__ = [
    "ActionScore",
    "OrderContext",
    "OrdersSource",
    "UtilityAI",
    "defend_score",
    "ice_slip_cost",
    "is_risky_move",
    "position_value",
    "reactive_enemies",
    "resolve_orders",
    "score_action",
    "virtual_move_score",
    "worth_previewing",
]
