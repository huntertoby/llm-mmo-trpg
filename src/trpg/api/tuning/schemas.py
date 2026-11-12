"""數值工坊 API 的請求與回應（NW-1a；前端 NW-1b 由 OpenAPI 產生型別）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.api.tuning.drafts import DEFAULT_DRAFT, DRAFT_NAME_PATTERN

__all__ = [
    "SMALL_SAMPLE",
    "TuningApplyResult",
    "TuningChangeIn",
    "TuningChangeView",
    "TuningCheckResult",
    "TuningDiff",
    "TuningDiffRow",
    "TuningDraftIn",
    "TuningDraftView",
    "TuningFieldError",
    "TuningFieldView",
    "TuningHistoryEntry",
    "TuningObjectDetail",
    "TuningObjectSummary",
    "TuningSimBoss",
    "TuningSimBuild",
    "TuningSimBuildResult",
    "TuningSimFlips",
    "TuningSimJob",
    "TuningSimOptions",
    "TuningSimPhase",
    "TuningSimRequest",
    "TuningSimResult",
    "TuningSimSide",
    "TuningSimSkill",
    "TuningStatus",
]

SMALL_SAMPLE = 30
"""分母小於這個數時標「樣本小」（規格 5.4）。"""


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# 對象與欄位
# ---------------------------------------------------------------------------


class TuningObjectSummary(_Model):
    kind: str
    id: str
    name_zh: str
    category: Literal["boss", "enemy"]
    """``boss``＝頭目（``tags`` 含 ``boss``），其餘是一般敵人。"""
    file: str
    """相對 ``content/`` 的路徑。"""


class TuningFieldView(_Model):
    path: str
    """具體路徑（例 ``phases[1].trigger.permille``）：改動單的 ``path``。"""
    pattern: str
    """白名單的路徑（例 ``phases[*].trigger.permille``）。"""
    label_zh: str
    kind: Literal["int", "permille"]
    value: int | None
    """磁碟上的現值；``None``＝沒寫（用預設值）。"""
    default_zh: str | None = None
    """沒寫時的預設值說明（例「沒寫＝5」）。"""
    hint_min: int | None = None
    hint_max: int | None = None
    """建議範圍：只作提示、不擋。"""
    note_zh: str


class TuningObjectDetail(_Model):
    kind: str
    id: str
    name_zh: str
    category: Literal["boss", "enemy"]
    file: str
    fields: list[TuningFieldView]
    notes_zh: list[str] = Field(default_factory=list)
    """唯讀提示（例：實戰時另有遭遇護甲調整、等級成長）。"""


# ---------------------------------------------------------------------------
# 草稿、驗證、差異
# ---------------------------------------------------------------------------


class TuningChangeIn(_Model):
    file: str
    path: str
    old: int | None
    """改前的值（畫面拿到的現值；``None``＝沒寫）；寫回前和磁碟現值比對。"""
    new: int | str | None
    """新值：整數或使用者打的文字（驗證時轉型，轉不了就是欄位錯誤）；``None``＝改回沒寫。"""


class TuningDraftIn(_Model):
    changes: list[TuningChangeIn] = Field(default_factory=list, max_length=500)


class TuningChangeView(_Model):
    file: str
    path: str
    old: int | None
    new: int | None
    object_id: str
    label_zh: str


class TuningDraftView(_Model):
    name: str = Field(pattern=DRAFT_NAME_PATTERN)
    changes: list[TuningChangeView]


class TuningFieldError(_Model):
    file: str
    path: str
    message_zh: str


class TuningCheckResult(_Model):
    ok: bool
    superseded: bool = False
    """後到的驗證取代了這一次（規格 5.5）：這次的結果作廢，看最新那次。"""
    field_errors: list[TuningFieldError] = Field(default_factory=list)
    page_errors: list[str] = Field(default_factory=list)
    """對不到欄位的錯誤（跨檔檢查、技能預算等）。"""
    seconds: float = 0.0


class TuningDiffRow(_Model):
    object_id: str
    object_name_zh: str
    file: str
    path: str
    label_zh: str
    old: int | None
    new: int | None


class TuningDiff(_Model):
    rows: list[TuningDiffRow]
    text: str
    """``git diff`` 風格的文字（只含改到的行）；改動單套不上時是空字串，原因在 ``errors``。"""
    errors: list[TuningFieldError] = Field(default_factory=list)


class TuningApplyResult(_Model):
    commit: str
    message: str
    files: list[str]
    backup: str
    """備份資料夾（``<save_dir>/tuning/backups/<時間>``）。"""
    restart_note_zh: str


class TuningHistoryEntry(_Model):
    commit: str
    summary: str
    date: str


class TuningStatus(_Model):
    can_write: bool
    reason_zh: str | None = None
    """不能寫回的原因（例：開發 PM 正在合併）。"""
    restart_needed: bool
    """這次開伺服器以來寫回過：遊戲要重開伺服器才用新數值。"""
    restart_note_zh: str
    draft_default: str = DEFAULT_DRAFT
    drafts: list[str]
    sim_running: str | None = None
    """跑中的模擬工作 ID。"""


# ---------------------------------------------------------------------------
# 模擬
# ---------------------------------------------------------------------------


class TuningSimBoss(_Model):
    key: str
    name_zh: str
    unit_id: str


class TuningSimBuild(_Model):
    id: str
    name_zh: str


class TuningSimOptions(_Model):
    bosses: list[TuningSimBoss]
    builds: list[TuningSimBuild]
    default_seeds: int
    max_battles: int
    workers: int
    seconds_per_battle: float
    """上一次實測的每場秒數（沒跑過時是估計值）；預估秒數＝場數 × 這個 ÷ ``workers``。"""


class TuningSimRequest(_Model):
    draft: str = Field(default=DEFAULT_DRAFT, pattern=DRAFT_NAME_PATTERN)
    boss: str
    builds: list[str] | None = None
    """省略＝全部 8 個。"""
    seeds: int = Field(default=3, ge=1, le=40)


class TuningSimSkill(_Model):
    skill: str
    casts: int
    turns: int
    """分母：頭目在該階段的行動回合數（每回合施放率＝casts ÷ turns）。"""
    small: bool


class TuningSimPhase(_Model):
    phase: int
    name_zh: str
    reached: int
    """到達這個階段的場數（第 1 階段＝全部場數）。"""
    turns: int
    skills: list[TuningSimSkill]


class TuningSimBuildResult(_Model):
    build: str
    n: int
    wins: int


class TuningSimSide(_Model):
    n: int
    wins: int
    rounds: int
    """所有場的輪數總和（平均＝rounds ÷ n）。"""
    allies: int
    """所有場我方開場人數總和。"""
    downed: int
    """所有場我方倒下過的人數總和（倒下率＝downed ÷ allies）。"""
    small: bool
    phases: list[TuningSimPhase]
    builds: list[TuningSimBuildResult]


class TuningSimFlips(_Model):
    won_to_lost: int
    lost_to_won: int


class TuningSimResult(_Model):
    boss: str
    battles: int
    before: TuningSimSide
    after: TuningSimSide
    flips: TuningSimFlips
    """同種子配對的勝負翻轉場數（改前贏改後輸、改前輸改後贏）。"""
    before_cached: bool


class TuningSimJob(_Model):
    job_id: str
    state: Literal["running", "done", "failed", "cancelled"]
    done: int
    total: int
    """這次要跑的場數（改前有快取時只算改後）。"""
    estimate_s: float
    elapsed_s: float
    error_zh: str | None = None
    result: TuningSimResult | None = None
