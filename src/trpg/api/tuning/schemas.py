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


type TuningValue = int | str | list[str] | None
"""欄位的值：整數、骰子字串（``2d6``）、技能 ID 清單；``None``＝沒寫。"""

type TuningCategory = Literal["boss", "enemy", "skill"]


class TuningSkillFacets(_Model):
    """技能清單的篩選欄位（NW-2a A6）。"""

    tier: int
    category: str
    """``weapon``（武器技）、``spell``（法術）…"""
    weapon_req: str
    ap_cost: int | None
    kind: str
    """``active``／``passive``／``reaction``／``stance``／``modifier``。"""
    enemy_only: bool
    has_condition: bool
    """技能或任一效果帶條件。"""
    shape: str
    ranged: bool
    """遠程：武器需求是 ``ranged``，或固定射程 ≥ 2。"""
    tags: list[str]
    budget_ratio_permille: int | None = None
    """預算比例（‰，四捨五入；算不出來或伺服器沒載入內容庫時是 ``None``）。"""


class TuningSkillUser(_Model):
    """裝了某招的單位或模擬用 build。"""

    kind: Literal["unit", "build"]
    id: str
    name_zh: str
    where_zh: list[str]
    """單位：「開場」「第 2 階段」…；build 是空的。"""
    tier: int | None = None
    """實戰時用的階級（大世界敵人依等級升階；``None``＝不確定或 1 階）。R2 提示用。"""


class TuningObjectSummary(_Model):
    kind: str
    id: str
    name_zh: str
    category: TuningCategory
    """``boss``＝頭目（``tags`` 含 ``boss``）、``enemy`` 一般敵人、``skill`` 技能。"""
    file: str
    """相對 ``content/`` 的路徑。"""
    skill: TuningSkillFacets | None = None
    """技能的篩選欄位（只有技能有）。"""


class TuningFieldView(_Model):
    path: str
    """具體路徑（例 ``phases[1].trigger.permille``、``effects[0].dice``）：改動單的 ``path``。"""
    pattern: str
    """白名單的路徑（例 ``phases[*].trigger.permille``）。"""
    label_zh: str
    kind: Literal["int", "permille", "dice", "range", "skill_ids"]
    value: TuningValue
    """磁碟上的現值；``None``＝沒寫（用預設值）。``range`` 的值可能是 ``weapon``（唯讀）。"""
    default_zh: str | None = None
    """沒寫時的預設值說明（例「沒寫＝5」）。"""
    hint_min: int | None = None
    hint_max: int | None = None
    """建議範圍：只作提示、不擋。"""
    limit_min: int | None = None
    limit_max: int | None = None
    """原語或形狀表上的範圍（會擋；只顯示，實際由驗證擋）。"""
    readonly_zh: str | None = None
    """唯讀的原因（例：射程是「武器射程」）；``None``＝可改。"""
    note_zh: str


class TuningObjectDetail(_Model):
    kind: str
    id: str
    name_zh: str
    category: TuningCategory
    file: str
    fields: list[TuningFieldView]
    notes_zh: list[str] = Field(default_factory=list)
    """唯讀提示（例：實戰時另有遭遇護甲調整、等級成長、技能升階重算）。"""
    skill: TuningSkillFacets | None = None
    used_by: list[TuningSkillUser] = Field(default_factory=list)
    """技能：裝了這招的單位與 build。"""


# ---------------------------------------------------------------------------
# 草稿、驗證、差異
# ---------------------------------------------------------------------------


class TuningChangeIn(_Model):
    file: str
    path: str
    old: TuningValue
    """改前的值（畫面拿到的現值；``None``＝沒寫）；寫回前和磁碟現值比對。"""
    new: TuningValue
    """新值：整數、骰子、ID 清單或使用者打的文字（依欄位種類轉型，轉不了就是欄位錯誤；ID 清單可打
    逗號分隔的文字）；``None``＝改回沒寫。"""


class TuningDraftIn(_Model):
    changes: list[TuningChangeIn] = Field(default_factory=list, max_length=500)


class TuningChangeView(_Model):
    file: str
    path: str
    old: TuningValue
    new: TuningValue
    object_id: str
    label_zh: str


class TuningBudgetFlag(_Model):
    """草稿裡預算超出合格區間的招（寫回要勾「我確定」；NW-2a D3）。"""

    skill_id: str
    name_zh: str
    ratio_permille: int
    ratio_text: str
    """顯示用（同 ``trpg skills budget``，例 ``112.4%``）。"""
    verdict: Literal["over", "weak"]
    message_zh: str


class TuningSideChange(_Model):
    """寫回時由後端產生的附帶改動（使用者不能直接改；NW-2a T5）。"""

    file: str
    action: Literal["exception_add", "exception_remove"]
    skill_id: str
    text_zh: str


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
    needs_confirm_budget: list[TuningBudgetFlag] = Field(default_factory=list)
    """預算超出合格區間的招：``ok`` 為真也要勾「我確定」才能寫回（apply 的 ``confirm_budget``）。
    整包檢查已假設這幾招會登記成例外。"""
    side_changes: list[TuningSideChange] = Field(default_factory=list)
    """寫回時會一起改的（例外清單加入／移除）。"""


class TuningDiffRow(_Model):
    object_id: str
    object_name_zh: str
    file: str
    path: str
    label_zh: str
    old: TuningValue
    new: TuningValue


class TuningDiff(_Model):
    rows: list[TuningDiffRow]
    text: str
    """``git diff`` 風格的文字（只含改到的行，含附帶改動）；改動單套不上時是空字串，原因在
    ``errors``。"""
    errors: list[TuningFieldError] = Field(default_factory=list)
    side_changes: list[TuningSideChange] = Field(default_factory=list)


class TuningApplyIn(_Model):
    """寫回時的確認（NW-2a）：要恰好等於驗證回的 ``needs_confirm_budget`` 的招。"""

    confirm_budget: list[str] = Field(default_factory=list, max_length=200)


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
    maps: list[TuningSimMap] = Field(default_factory=list)
    """地圖戰情境可選的地圖（NW-2a；有預設遭遇、不含 ``test_*``、``training_range``）。"""
    map_default_seeds: int = 24
    map_seconds_per_battle: float = 0.8
    """地圖戰的每場秒數（另記，不和頭目戰共用）。"""


class TuningSimMap(_Model):
    id: str
    name_zh: str


class TuningSimInject(_Model):
    """「裝到 build」（NW-2a T9）：只在模擬的內容庫裡把這招裝到該 build 英雄身上，不寫檔。"""

    build: str
    skill: str


class TuningSimRequest(_Model):
    draft: str = Field(default=DEFAULT_DRAFT, pattern=DRAFT_NAME_PATTERN)
    scenario: Literal["boss", "map"] = "boss"
    """``boss``＝頭目戰（NW-1）；``map``＝地圖戰（NW-2a）。"""
    boss: str | None = None
    """頭目戰必填。"""
    builds: list[str] | None = None
    """頭目戰：省略＝全部 8 個。"""
    seeds: int = Field(default=3, ge=1, le=160)
    """頭目戰：每個 build 的種子數；地圖戰：每張圖的種子數。"""
    maps: list[str] | None = None
    """地圖戰必填（1～3 張）。"""
    allies: list[str] | None = None
    """地圖戰：我方換成這些 build（同 ``--ally-build``，標準隊友補滿）；省略＝地圖預設陣容。"""
    probe: list[str] = Field(default_factory=list, max_length=20)
    """地圖戰：受測招（基礎 ID）；空＝草稿改到的招。"""
    inject: list[TuningSimInject] = Field(default_factory=list, max_length=8)
    """地圖戰：把受測招裝到 build 上（該 build 要在 ``allies`` 裡才有作用）。"""


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
    """頭目戰的結果。"""
    map_result: TuningMapSimResult | None = None
    """地圖戰的結果（NW-2a）。"""


# ---------------------------------------------------------------------------
# 地圖戰（NW-2a 5.6）
# ---------------------------------------------------------------------------


class TuningSkillRate(_Model):
    """單招施放率：分子＝施放次數，分母＝裝了這招的單位的行動回合數（T10）。"""

    skill: str
    team: Literal["ally", "enemy"]
    casts: int
    turns: int
    battles: int
    """場數（每場平均次數＝casts ÷ battles）。"""
    small: bool
    """分母小於 30。"""


class TuningMapSide(_Model):
    n: int
    wins: int
    rounds: int
    allies: int
    downed: int
    small: bool
    skills: list[TuningSkillRate]
    maps: list[TuningSimBuildResult]
    """逐張地圖的場數與勝場（``build`` 欄放地圖 ID）。"""


class TuningMapSimResult(_Model):
    maps: list[str]
    battles: int
    before: TuningMapSide
    after: TuningMapSide
    flips: TuningSimFlips
    before_cached: bool


# ---------------------------------------------------------------------------
# 技能預算與分組改（NW-2a 5.3、5.4）
# ---------------------------------------------------------------------------


class TuningBudgetIn(_Model):
    changes: list[TuningChangeIn] = Field(default_factory=list, max_length=200)
    """這招的改動（只取這招的檔；省略＝現值）。"""


class TuningBudgetVariant(_Model):
    id: str
    name_zh: str
    ratio_permille: int
    ratio_text: str
    verdict: Literal["ok", "over", "weak"]


class TuningBudgetSegment(_Model):
    label: str
    points: str
    """兩段各自的點數（顯示用，小數兩位）。"""


class TuningViolation(_Model):
    rule: str
    message_zh: str


class TuningBudgetResult(_Model):
    skill_id: str
    ratio_permille: int | None
    """total ÷ 可用預算（‰，四捨五入）；算不出來時是 ``None``（原因在 ``error_zh``）。"""
    ratio_text: str
    """同 ``trpg skills budget`` 的寫法（例 ``93.6%``）。"""
    min_ratio_permille: int
    max_ratio_permille: int
    verdict: Literal["ok", "over", "weak", "error"]
    verdict_zh: str
    variants: list[TuningBudgetVariant] = Field(default_factory=list)
    segments: list[TuningBudgetSegment] = Field(default_factory=list)
    violations: list[TuningViolation] = Field(default_factory=list)
    """``validate_skill`` 的違規（含預算範圍以外的錯誤）。"""
    known_exception: bool
    """目前在 ``known_budget_exceptions`` 裡。"""
    field_errors: list[TuningFieldError] = Field(default_factory=list)
    """改動本身的錯誤（轉型、單檔 schema）；有錯時不算預算。"""
    error_zh: str | None = None


class TuningGroupFilter(_Model):
    """分組改的篩選（全部條件都要符合；空的條件不篩）。"""

    tier: list[int] = Field(default_factory=list)
    category: list[str] = Field(default_factory=list)
    weapon_req: list[str] = Field(default_factory=list)
    ap_cost: list[int] = Field(default_factory=list)
    kind: list[str] = Field(default_factory=list)
    enemy_only: bool | None = None
    has_condition: bool | None = None
    ranged: bool | None = None
    shape: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    """要全部包含。"""
    single_damage: bool | None = None
    """單體傷害（形狀 ``single`` 且有傷害效果）。"""

    def empty(self) -> bool:
        return self == TuningGroupFilter()


class TuningGroupOp(_Model):
    kind: Literal["set", "add", "scale_permille", "ladder"]
    value: int
    """``set``：新值；``add``：±N；``scale_permille``：‰ 倍率（1100＝×1.1）；``ladder``：±級數。"""


type TuningGroupTarget = Literal[
    "ap_cost",
    "cost.stamina",
    "cost.mana",
    "cost.cooldown",
    "shape.range",
    "damage_all",
    "damage_base",
    "damage_conditional",
]


class TuningGroupIn(_Model):
    skills: list[str] = Field(default_factory=list)
    """手動勾的招（和篩選取聯集）。"""
    filter: TuningGroupFilter | None = None
    target: TuningGroupTarget
    """``damage_all``＝所有傷害效果、``damage_base``＝沒有條件的、``damage_conditional``＝帶條件的；
    ``ladder``／``scale_permille`` 依效果是武器倍率或骰子自動選。"""
    op: TuningGroupOp


class TuningGroupRow(_Model):
    skill_id: str
    name_zh: str
    changes: list[TuningChangeIn]
    """放進草稿用的改動（``old`` 是磁碟現值）。"""
    before_ratio_permille: int | None
    after_ratio_permille: int | None
    verdict: Literal["ok", "over", "weak", "error", "skipped"]
    skipped_reason_zh: str | None = None


class TuningGroupPreview(_Model):
    rows: list[TuningGroupRow]
    """依技能 ID 排序。"""
    count: int
    max_skills: int


class TuningGroupPreset(_Model):
    key: str
    label_zh: str
    filter: TuningGroupFilter
