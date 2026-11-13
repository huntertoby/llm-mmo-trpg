"""roguelite 一輪的 API 格式（Phase 3-5a；``/api/runs``）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trpg.api.gear_schemas import GearItemInfo
from trpg.api.schemas import BattleResponse
from trpg.api.skill_cards import SkillCard
from trpg.content.maps import Objective
from trpg.narrative.skills import KeywordRef
from trpg.roguelite.save import RUN_ID_PATTERN
from trpg.roguelite.state import BattleRecord
from trpg.shared.rng import MASK64
from trpg.shared.types import Attribute

__all__ = [
    "AllocationPreviewOut",
    "AllocationPreviewRequest",
    "AttributeAffectsOut",
    "AttributeSuggestionOut",
    "BattlePlanOut",
    "CreateRunRequest",
    "DevPackOut",
    "FlashCategoryOut",
    "FlashOptionOut",
    "FlashPreviewOut",
    "FlashPreviewRequest",
    "FlashRecordOut",
    "FlashRulesOut",
    "GearCandidateOut",
    "GearOfferOut",
    "HeroGearSlotOut",
    "HeroOut",
    "LoadRunRequest",
    "NodeOut",
    "OfferOut",
    "OfferTagOut",
    "OriginOption",
    "PendingFlashOut",
    "RaceOption",
    "RunBattleResponse",
    "RunResponse",
    "RunRules",
    "SaveOut",
    "SaveSummary",
    "SkillFlashOut",
    "StartKeywordOption",
    "StartLinkOut",
    "StartOptions",
    "StartPreview",
    "StartPreviewRequest",
    "StartResourcesOut",
    "StartResourcesRequest",
    "StartWeaponOption",
    "StatChangeOut",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CreateRunRequest(_ApiModel):
    """開新一輪（Phase 3-24b2）：``weapon`` ＋ ``keywords``（一般開局），或 ``dev_pack``（開發者
    起始包），或 ``build``（回歸範本，開發與測試用）——三者擇一；種子；開局配點（省略時全部點在
    武器的縮放屬性，以 build 開局時為技能最常用的縮放屬性）。"""

    build: str | None = None
    seed: int = Field(ge=0, le=MASK64)
    attributes: dict[Attribute, int] | None = None
    weapon: str | None = None
    """起始武器（Phase 3-24b2）。"""
    keywords: tuple[str, ...] | None = None
    """選的關鍵字（Phase 3-24b2；``roguelite.yaml`` 的 ``start.keywords`` 個）。"""
    dev_pack: str | None = None
    """開發者起始包 ID（Phase 3-24b2，開發用）。"""
    test_mode: bool = False
    """測試模式（Phase 3-39）：戰後回滿，可挑裝備；只能用 ``weapon`` ＋ ``keywords`` 開局。"""
    race: str | None = None
    """主角的種族（Phase 3R-2，``races.yaml`` 的 ID）；省略＝無種族；未知的種族回 422。"""
    origin: str | None = None
    """出身（Phase 3R-3a，``origins.yaml`` 的 ID，不影響戰鬥）；省略＝無出身；未知的出身回 422。"""
    test_equipment: dict[str, str] = Field(default_factory=dict)
    """測試模式挑的裝備（欄位 → 物品 ID，Phase 3-39）；只有 ``test_mode`` 時可非空。"""
    llm: bool = False
    """LLM 生成開關（Phase 4-L6b）：升級技能候選請本機模型提議。連不到模型時不報錯，這一輪自動當作
    關閉，回應的 ``llm_notice`` 帶提示。預設關。"""

    @model_validator(mode="after")
    def _one_start(self) -> CreateRunRequest:
        if (self.test_mode or self.test_equipment) and self.weapon is None:
            raise ValueError("測試模式只能用 weapon＋keywords 開局")
        if self.test_equipment and not self.test_mode:
            raise ValueError("挑選裝備只能在測試模式使用")
        given = [
            self.build is not None,
            self.dev_pack is not None,
            self.weapon is not None or self.keywords is not None,
        ]
        if sum(given) != 1:
            raise ValueError("開局必須擇一：weapon＋keywords、dev_pack 或 build")
        if (self.weapon is None) != (self.keywords is None):
            raise ValueError("weapon 與 keywords 必須一起給")
        return self

    def dev_fields(self) -> list[str]:
        """有填的開發用欄位（6S-1：開發模式關時路由回 403）。"""
        used = {
            "build": self.build is not None,
            "dev_pack": self.dev_pack is not None,
            "test_mode": self.test_mode,
            "test_equipment": bool(self.test_equipment),
        }
        return [name for name, on in used.items() if on]


class StartWeaponOption(_ApiModel):
    """開局可選的武器（Phase 3-24b2）。"""

    id: str
    name_zh: str
    weapon_class: str
    traits_zh: tuple[str, ...] = ()
    hp: int
    """選這把武器時主角的最大 HP（未配點）。"""
    mana: int


class StartResourcesRequest(_ApiModel):
    """開局資源預覽（3-41c）：武器與目前的配點（不必配滿；省略的屬性為 0 點）。"""

    weapon: str
    attributes: dict[Attribute, int] = Field(default_factory=dict)


class StartResourcesOut(_ApiModel):
    """開局的 1 級主角最大 HP、法力、耐力（含配點加成；和開新一輪建立出的主角同一個函式）。"""

    hp: int
    mana: int
    stamina: int


class AllocationPreviewRequest(_ApiModel):
    """升級配點與營火重配的資源預覽（3H-5）：目前的配點（不必配滿；省略的屬性為 0 點）。"""

    attributes: dict[Attribute, int] = Field(default_factory=dict)


class AllocationPreviewOut(_ApiModel):
    """配點後主角的最大 HP、法力、耐力（不含裝備；和一輪面板同一個函式）與一句話的變化
    （例「最大 HP ＋6、耐力 ＋4」，沒變時為空字串）。"""

    hp: int
    mana: int
    stamina: int
    summary_zh: str


class RaceOption(_ApiModel):
    """開局可選的種族（Phase 3R-3a）：種族技與環境被動的說明（都不給數值，7.7）。"""

    id: str
    name_zh: str
    home_realm: str
    home_realm_name_zh: str
    skill_name_zh: str
    skill_description_zh: str
    skill_ap: int
    skill_uses: int
    """每場限用次數。"""
    passive_name_zh: str
    passive_description_zh: str


class OriginOption(_ApiModel):
    """開局可選的出身（Phase 3R-3a）：界域與簡介；出身不影響戰鬥。"""

    id: str
    name_zh: str
    realm: str
    realm_name_zh: str
    description_zh: str


class StartOptions(_ApiModel):
    """開局選項（Phase 3-24b2）：全部武器、全部關鍵字、要選幾個關鍵字；3R-3a 起另有種族與出身。"""

    weapons: tuple[StartWeaponOption, ...]
    keywords: tuple[KeywordRef, ...]
    keyword_count: int
    races: tuple[RaceOption, ...] = ()
    origins: tuple[OriginOption, ...] = ()


class StartPreviewRequest(_ApiModel):
    """開局預覽：武器、種子與目前已選的關鍵字（依選擇順序）。"""

    weapon: str
    seed: int = Field(ge=0, le=MASK64)
    keywords: tuple[str, ...] = ()


class StartKeywordOption(_ApiModel):
    """一個關鍵字的起始技能預覽：``skill`` 為 ``None`` 表示這把武器湊不到（不可選）。已選的關鍵字
    是實際會拿到的技能；沒選的是「下一個選它」時會拿到的技能。"""

    keyword: KeywordRef
    selected: bool
    skill: SkillCard | None


class AttributeAffectsOut(_ApiModel):
    """一個屬性影響的東西（Phase 3H-3）：武器的普攻、縮放這個屬性的技能名；由程式依技能
    與武器的縮放屬性產生。"""

    attr: Attribute
    lines_zh: tuple[str, ...]
    """影響的項目（沒有時為空）。"""


class AttributeSuggestionOut(_ApiModel):
    """開局建議的主屬性（Phase 3H-3）：起始技能最常用的縮放屬性（和自動配點同一個規則）。"""

    attr: Attribute
    reason_zh: str


class RouteHintOut(_ApiModel):
    """關鍵字與屬性不搭的提示（BAL-19g，06 6.27.3，#110）：配點後的最高屬性不在 ``fits`` 時，
    前端顯示 ``text_zh``（只提示、不擋）。``lean``：選的關鍵字前期的技能多半是法術（``spell``）或
    武器技（``weapon``）。"""

    lean: Literal["spell", "weapon"]
    fits: tuple[Attribute, ...]
    text_zh: str


class StartLinkOut(_ApiModel):
    """起始兩招的觸發關係（#129，6F-4）：「火球製造點燃 → 電爆利用點燃」。"""

    maker_zh: str
    """製造的那招。"""
    user_zh: str
    """利用的那招。"""
    keyword: KeywordRef
    text_zh: str


class StartPreview(_ApiModel):
    weapon: str
    seed: int
    options: tuple[StartKeywordOption, ...]
    suggestion: AttributeSuggestionOut | None = None
    """建議的主屬性（Phase 3H-3；依武器＋已選的關鍵字給的起始技能）。"""
    attribute_affects: tuple[AttributeAffectsOut, ...] = ()
    """每個屬性影響你的哪些招（Phase 3H-3；起始技能與武器）。"""
    route_hint: RouteHintOut | None = None
    """關鍵字與屬性不搭的提示（BAL-19g；依武器＋已選的關鍵字）。"""
    links: tuple[StartLinkOut, ...] = ()
    """已選兩招之間的觸發關係（#129；選滿兩個關鍵字才有，沒有互相觸發時空）。"""
    recommended: dict[Attribute, int] = Field(default_factory=dict)
    """推薦配法（07 7.2，#133）：開局 4 點怎麼配（同屬性全給、不同各半）；大世界建角照這個自動
    配好。"""
    recommended_zh: str = ""
    """推薦配法的文字，例「智力 +2、力量 +2」。"""


class DevPackOut(_ApiModel):
    """開發者起始包（Phase 3-24b2，開發用；只在開發者選單顯示）。"""

    id: str
    label_zh: str
    weapon: str
    weapon_name_zh: str
    keywords: tuple[KeywordRef, ...]


class LoadRunRequest(_ApiModel):
    run_id: str = Field(pattern=RUN_ID_PATTERN)


class RunRules(_ApiModel):
    """開局規則（``content/roguelite.yaml``）。"""

    start_points: int
    """開局的自由配點數。"""
    base_attribute: int
    """開局六項屬性的基礎值。"""
    hp_per_con_point: int
    """每點體質的最大 HP（``core.yaml``；配點預覽用）。"""


class FlashRulesOut(_ApiModel):
    """閃現的規則（Phase 3W-5，``content/flash_templates.yaml``）：前端不寫死數值。"""

    open_cost: int
    """不指定類別的價格（點）。"""
    open_options: int
    """不指定類別出幾個選項。"""
    focused_cost: int
    """指定類別的價格（點）。"""
    focused_options: int
    """指定類別出幾個選項（該類不足時少出）。"""
    allow_focus: bool
    max_flashes: int
    """每招最多閃幾次。"""
    major_flash: int
    """第幾次是大變化（加深、橋接、轉型）。"""
    insight_per_win: int
    """每打贏一場得到的靈感點。"""
    max_carry: int
    """傳承時最多帶走幾個小變化（第 3 次是大變化，所以是 ``major_flash`` − 1；3W-R2）。"""


class FlashRecordOut(_ApiModel):
    """技能變化歷程的一筆（第幾次、哪一類、一句話說明）。"""

    nth: int
    """第幾次閃現（完整技能的調整欄為 0）。"""
    source: Literal["minor", "major", "transform"]
    category: str
    category_zh: str
    template: str
    summary_zh: str
    reflashes: int
    """這一欄被重閃過幾次。"""


class ReflashSlotOut(_ApiModel):
    """可以重閃的一欄（3W-R2：前端不自己推規則）。"""

    slot: int
    """第幾次（完整技能的調整欄為 0）。"""
    transform_hint: bool = False
    """這一欄是第 3 次大變化但還不是轉型（升階後建議重閃）。"""
    available: bool = True
    """重閃這一欄有沒有任何合法選項（RR-1，比照 FL-1c 的 ``flash_available``，06 6.34「費用方向」
    第 7 點）：伺服器實際算過；``False`` 時按鈕標灰、不能按，灰字是 ``problem_zh``。"""
    problem_zh: str | None = None
    """不能重閃這一欄的原因（可以時為 ``None``）。"""


class SkillFlashOut(_ApiModel):
    """一招學會的技能的閃現狀態（Phase 3W-5；卡片的「已閃 N／5 次」「可以閃現了」與變化歷程）。"""

    skill_id: str
    base_id: str
    """閃現前的原本技能 ID（種子標籤用）。"""
    flashes: int
    """視為閃過幾次（完整技能為 3）。"""
    complete: bool
    """完整技能（不能再閃，只能重閃調整欄）。"""
    used: bool
    """自上次閃現（或取得）後已在戰鬥中用過。"""
    can_flash: bool
    """點數以外的條件都符合，可以閃現（「可以閃現了」）。"""
    flash_problem_zh: str | None = None
    """不能閃現的原因（可以時為 ``None``）。"""
    flash_available: bool = True
    """這一次閃現有沒有任何合法選項（FL-1c）：其他條件都符合時伺服器實際算過；``False`` 時
    ``can_flash`` 也是 ``False``，``flash_problem_zh`` 是「這招目前沒有可以閃的變化」，面板
    顯示灰色。其他條件不符合時（還沒用過、閃滿等）不算，照 ``True``。"""
    next_major: bool = False
    """下一次閃現是大變化（第 3 次）。"""
    records: tuple[FlashRecordOut, ...] = ()
    """變化歷程（依次序；完整技能的調整欄放最後）。"""
    spent: int = 0
    """花在這招身上的靈感點。"""
    dissolve_refund: int = 0
    """溶掉會退回的點數（花掉的一半，無條件捨去）。"""
    reflash_transform_hint: bool = False
    """升階提示用（交給 3W-6）：第 3 次是大變化但不是轉型，可以重閃第 3 格試試轉型（照常付點）。"""
    reflash_slots: tuple[ReflashSlotOut, ...] = ()
    """可以重閃的欄（點數與地點另外檢查；3W-R2）。"""
    carryable: tuple[int, ...] = ()
    """傳承時可以被帶走的變化（第幾次；3W-R2）。"""
    inherit_problem_zh: str | None = None
    """這招不能傳承給別招的原因（可以時為 ``None``；3W-R2）。"""
    inherit_target: bool = False
    """這招可以接受傳承（還沒閃過、不是完整技能；3W-R2）。"""


class ChangeIconOut(_ApiModel):
    """「前 → 後」一列的欄位小圖（FL-1b，移植需求第 7 節；圖示一律沿用前批）。

    ``part``＝第④批部件圖樣（``cat``：``card`` 卡片小圖、``shape``、``surface``、``skeleton``）；
    ``status``＝第⑤批狀態圖示；``keyword``＝第⑤b 批關鍵字圓章。"""

    kind: Literal["part", "status", "keyword"]
    cat: str | None = None
    id: str


class StatChangeOut(_ApiModel):
    """閃現選項「前 → 後」的一列（FL-1a）：閃現前與選項套用後技能卡上一個數字的差異。"""

    field: str
    """欄位路徑：``range``、``radius``、``size``；代價 ``cost.<種類>``（``cost.ap``、
    ``cost.cooldown``、``cost.mana``…，種類同 ``CostStat.kind``）；效果 ``effects[i].dice``／
    ``.multiplier_permille``／``.amount``（回合、格數、層數）／``.magnitude_permille``（狀態強度）；
    接續段 ``followup[i]...``；整個效果新增或拿掉時是 ``effects[i]``。"""
    label_zh: str
    """欄位的中文名（例「燃燒回合」「傷害骰子」「冷卻」）。"""
    effect_index: int | None = None
    """效果列的 ``index``（同卡片 ``stats.effects`` 或接續段的位置）；技能層級與代價為 ``None``。"""
    before: str | None
    """閃現前的值（顯示用字串：骰子「1d8」、倍率「×1.15」、強度「1025‰」、回合「5」）；新加的為
    ``None``。"""
    after: str | None
    """選項套用後的值；拿掉的為 ``None``。"""
    direction: Literal["better", "worse", "cost", "new"]
    """``better``／``worse``：強度變強／變弱；``cost``：代價變了（升降看前後值）；``new``：新加的。"""
    name_zh: str = ""
    """畫面上的欄位名（FL-1b，移植需求 9.1 #4：射程、冷卻、AP、燃燒、範圍、地面、額外傷害、
    接續、第二元素、效果、種類…；對照表在 :mod:`trpg.api.flash_changes`）。"""
    term: str | None = None
    """欄位名的說明卡（:attr:`PendingFlashOut.terms` 的鍵）；沒有說明卡為 ``None``。"""
    before_zh: str | None = None
    """「前」的顯示字（帶單位：「4 格」「2 回合」「3 成武器傷害」）；``None``＝原本沒有。
    可帶術語標記 ``[[術語|字]]`` 與圖示標記 ``{{kw:<id>}}``。"""
    after_zh: str | None = None
    """「後」的顯示字；``None``＝拿掉了（畫面寫「沒有」）。"""
    icon: ChangeIconOut | None = None


class FlashOptionOut(_ApiModel):
    """待選閃現的一個選項：變化與套用後的技能卡。"""

    index: int
    source: Literal["minor", "major", "transform"]
    category: str
    category_zh: str
    """類別中文名；轉型為「轉型」。"""
    template: str
    summary_zh: str
    transform: bool
    """轉型選項（第 3 次的保底，列在最後時標示「轉型」）。"""
    card: SkillCard
    unequip_candidates: tuple[str, ...] = ()
    """選這個（轉型換到已滿的欄位）要卸下其中一招到備用（送 ``flash_pick`` 的 ``unequip``）。"""
    unequip_slot: str | None = None
    """要卸下時，轉型後佔的欄位（FL-1b 8.3：卸下選單寫「被動欄滿了…」；姿態欄只有 1 格，畫面自動換下
    原姿態、不出選單）；不用卸下為 ``None``。"""
    changes: tuple[StatChangeOut, ...] = ()
    """和閃現前（重閃是被換掉那一筆之前）比，卡片上有變的數字（FL-1a；只列有變的，順序：射程等 →
    代價 → 效果 → 接續段）。"""
    headline_zh: str | None = None
    """白話大標（FL-1b，``flash_templates.yaml`` 的 ``headline_zh`` 與「模板 × 關鍵字」表）；
    還沒填的模板為 ``None``，畫面退回 ``summary_zh``。"""
    say_zh: str = ""
    """選中時下固定區的一句話（FL-1b 9.3）：模板有寫的照模板，沒有的照差異清單組。可帶術語標記。"""
    tag_term: str | None = None
    """類別標籤的說明卡（FL-1b 9.2：蓄力「威力提高」、輕巧「威力降低」只在說明卡）。"""
    note_zh: str | None = None
    """LLM 寫的一句話描述（LF-3；``Variation.note_zh``，引擎 ``clean_note`` 過了才有）；沒有＝畫面
    照舊只畫大標與「前 → 後」，不佔位。純文字，不帶術語標記。"""
    name_source: Literal["llm", "template"] = "template"
    """這個選項的技能名稱（``card.name_zh``）從哪來（LF-3）：``llm``＝這次閃現的大變化或轉型帶了
    LLM 名稱而且用上了；``template``＝其他（組合式「{前綴}・{原名}」，或小變化沿用原名）。"""


class FlashTermOut(_ApiModel):
    """選變體畫面的一張說明卡（FL-1b，移植需求 9.2）：數字已照資料填好。"""

    title_zh: str
    text_zh: str


class FlashBaseStatOut(_ApiModel):
    """原技能列的一個數字（FL-1b 2.1：AP、耐力、冷卻、射程、燃燒回合…，各帶卡片小圖與說明卡）。"""

    name_zh: str
    value_zh: str
    term: str | None = None
    icon: ChangeIconOut | None = None


class PendingFlashOut(_ApiModel):
    """已付點、還沒選的閃現選項（Phase 3W-5）；選之前不能做別的事。"""

    skill_id: str
    nth: int
    slot: int | None
    """重閃的欄位；閃現為 ``None``。"""
    category: str | None
    major: bool
    cost: int
    options: tuple[FlashOptionOut, ...]
    base_stats: tuple[FlashBaseStatOut, ...] = ()
    """原技能列（閃現前）的數字（FL-1b 2.1）；欄位名與小圖和「前 → 後」同一份對照。"""
    terms: dict[str, FlashTermOut] = Field(default_factory=dict)
    """這次選項（大標、前 → 後、說明句、原技能列）用到的說明卡（FL-1b）：術語 ID → 說明卡。
    畫面只查表；查不到的術語不畫底線。"""


class FlashPreviewRequest(_ApiModel):
    """閃現（``slot`` 為空）或重閃第 ``slot`` 次之前的預覽：選類別畫面用。"""

    skill: str
    slot: int | None = Field(default=None, ge=0)


class FlashCategoryOut(_ApiModel):
    """可指定的一個類別：目前有幾個合法變化（「連段（2）」；0 個不能選）。"""

    id: str
    name_zh: str
    count: int


class FlashPreviewOut(_ApiModel):
    """閃現或重閃之前的預覽（Phase 3W-5，含 3W-2c 的每類數量）。"""

    skill_id: str
    slot: int | None
    nth: int
    major: bool
    problem_zh: str | None
    """不能閃現（或重閃）的原因（點數與地點另外看）；可以時為 ``None``。"""
    open_cost: int
    focused_cost: int
    categories: tuple[FlashCategoryOut, ...]
    """可指定的類別（資料順序）；有問題時為空。"""
    history_note_zh: str | None = None
    """已存的變化歷程在目前的內容版本重推不了時的原因（3W-R1；這時改用存檔裡的數值當起點）。"""


class AttributePerkOut(_ApiModel):
    """屬性的常駐數值（Phase 3H-1，``core.yaml`` 的 ``attribute_perks``）：說明由資料產生。"""

    attr: Attribute
    tier: int
    """目前階數（屬性高於 10 每 4 點一階；0 為還沒有）。"""
    per_tier_zh: str
    """每階的效果，例：「你造成的撞擊傷害 +1／階」。"""
    now_zh: str | None
    """目前階數的總效果（0 階為 ``None``）。"""
    next_at: int
    """下一階需要的屬性值。"""


class GearCandidateOut(_ApiModel):
    """一件可以換上的裝備（戰後三選一的候選、背包裡的裝備；Phase 3K-2）：物品卡、換上會放進的欄位，
    以及和該欄位目前裝備的比較（目前的物品卡與兩邊的預算分數、換上的連帶效果）。"""

    item: GearItemInfo
    slot: str
    slot_zh: str
    current: GearItemInfo | None = None
    """該欄位目前的裝備（主手沒有物品時是主角的基礎武器；欄位空著為 ``None``）。"""
    notes_zh: tuple[str, ...] = ()
    """換上的連帶效果（武器換了、副手收進背包）。"""
    weapon_swap_zh: str | None = None
    """換主手武器且縮放屬性和目前武器不同時的提示（3K-2b）：「這把看〔屬性〕，你目前最高的是〔屬性〕」；
    前端換上前要讓玩家確認。屬性相同、或不是換武器為 ``None``。"""


class GearOfferOut(_ApiModel):
    """戰後裝備三選一（節點 ``gear_offer``）。"""

    after_battle: int
    candidates: tuple[GearCandidateOut, ...]


class HeroGearSlotOut(_ApiModel):
    """主角一個裝備欄位目前的裝備（9 個欄位都列；空著 ``item`` 為 ``None``）。"""

    slot: str
    slot_zh: str
    item: GearItemInfo | None = None
    opening_note_zh: str | None = None
    """大世界、開局還沒結束時卡片多寫的一行（OB-6：入門武器是借的／4 級前重選會收回起始武器）；
    一輪與其他時候 ``None``。"""


class HeroOut(_ApiModel):
    build_id: str
    name_zh: str
    level: int
    xp: int
    xp_next: int | None
    """升到下一級需要的累計經驗（已到等級上限為 ``None``）。"""
    attributes: dict[Attribute, int]
    hp: int
    max_hp: int
    hp_per_con_point: int
    """每點體質的最大 HP（``core.yaml``；前端的「＋N HP」預覽用）。"""
    hp_con_base: int
    """體質的基準值（高於它才有 HP 加成）。"""
    effective_attributes: dict[Attribute, int] = Field(default_factory=dict)
    """有效屬性（Phase 3H-3）：基礎屬性＋裝備的屬性詞條（戰鬥之間沒有狀態）；和引擎同一個算法。
    常駐數值的階數依它算，``attributes`` 仍是基礎值（配點用）。"""
    attribute_points: int = 0
    """營火重配後還沒分配的屬性點（Phase 3H-3）。"""
    attribute_spent: dict[Attribute, int] = Field(default_factory=dict)
    """分配出去、營火重配時會退回的屬性點（Phase 3H-3）。"""
    attribute_affects: tuple[AttributeAffectsOut, ...] = ()
    """每個屬性影響你的哪些招（Phase 3H-3；裝備中的技能與武器）。"""
    attribute_perks: tuple[AttributePerkOut, ...] = ()
    """屬性的常駐數值（Phase 3H-1）：面板每個屬性底下顯示（階數依有效屬性）。"""
    mana: int
    max_mana: int
    stamina: int = 0
    """目前耐力（Phase 3H-2：武器技與格擋共用；戰鬥之間不回復，營火回滿）。"""
    max_stamina: int = 0
    """耐力上限（基礎 ＋（力量、敏捷、體質最高者 − 10）× 2，07 7.2）。"""
    source: int
    source_max: int
    weapon: str
    weapon_name_zh: str = ""
    """武器中文名（Phase 3-18b，一輪中英雄面板顯示）。"""
    weapon_class: str = ""
    """武器大類（melee、ranged、focus）；前端不認得 ``weapon`` 時依此退回武器小圖示。"""
    weapon_traits_zh: tuple[str, ...] = ()
    """武器小特性的說明，每個特性一行（Phase 3-24a1）。"""
    offhand_name_zh: str = ""
    """副手（圓盾、塔盾、法書、法器珠；測試模式挑的裝備，Phase 3I-2）的中文名；沒有時為空。"""
    offhand_traits_zh: tuple[str, ...] = ()
    """副手特性的說明，每個特性一行（Phase 3I-2；圓盾附目前的格擋強化）。"""
    skills: tuple[SkillCard, ...]
    start_keywords: tuple[KeywordRef, ...] = ()
    """開局選的關鍵字（Phase 3-24b2；以 build 開局時為空）。"""
    dev_pack: str | None = None
    """開發者起始包 ID（Phase 3-24b2，開發用）。"""
    race_id: str | None = None
    race_name_zh: str = ""
    """主角的種族（Phase 3R-3a；沒有種族時 ``None``／空字串）。"""
    origin_id: str | None = None
    origin_name_zh: str = ""
    """這一輪的出身（Phase 3R-3a；沒有出身時 ``None``／空字串）。"""
    origin_realm: str | None = None
    """出身的區域 ID（QK-2b：主角 Q 版頭像的框色）；沒有出身為 ``None``。"""
    insight: int = 0
    """還沒花的靈感點（Phase 3W-5）。"""
    flash_rules: FlashRulesOut | None = None
    flash: tuple[SkillFlashOut, ...] = ()
    """學會的每招技能（裝備中依技能列順序，再來是備用）的閃現狀態（Phase 3W-5）。"""
    bench: tuple[SkillCard, ...] = ()
    """備用技能（Phase 3-26a；卸下的技能，閃現狀態保留）。"""
    equipment: tuple[HeroGearSlotOut, ...] = ()
    """目前穿戴的裝備（Phase 3K-2；依欄位固定順序，9 個欄位都列）。"""
    backpack: tuple[GearCandidateOut, ...] = ()
    """背包（Phase 3K-2）：換下的裝備與換上後的比較；營火可以換上（``equip``）。"""


class BattlePlanOut(_ApiModel):
    index: int
    map_id: str
    map_name_zh: str
    boss: bool
    enemies: tuple[str, ...]
    """敵人的中文名。"""
    done: bool
    objective: Objective
    """本場的勝利條件（Phase 3-22）：全滅、撤離（出口格＋輪數）或守點（守點格＋輪數）。"""


class OfferTagOut(_ApiModel):
    """候選的標示（Phase 3-24b2）：加深／橋接／新方向與它帶的關鍵字。"""

    kind: Literal["deepen", "bridge", "new"]
    label_zh: str
    """「加深」「橋接」「新方向」。"""
    keywords: tuple[KeywordRef, ...]
    fallback: bool
    """定義做不到而退回（例：只持有 1 個關鍵字時的橋接改成「持有的 ＋ 新的」）。"""
    source: Literal["pool", "composer", "llm"]


class OfferOut(_ApiModel):
    reason: Literal["level_up", "complete"]
    """``level_up`` 升級的白板三選一；``complete`` 完整技能三選一（Phase 3W-5）。"""
    tier: int
    top_attribute: Attribute
    candidates: tuple[SkillCard, ...]
    off_route: tuple[int, ...]
    """「偏離路線」候選的索引。"""
    tags: tuple[OfferTagOut, ...] = ()
    """與 ``candidates`` 一一對應的標示（Phase 3-24b2）。"""


class NodeOut(_ApiModel):
    """目前節點：``battle``（``battle_index``）、``gear_offer``（``gear``，Phase 3K-2）、
    ``level_up``（``level``、``points``、``offer``、``tier_up``）、``complete_offer``（完整技能三選一，
    ``after_battle``、``offer``；Phase 3W-5）、``campfire``（``after_battle``）、
    ``ended``（``victory``）。"""

    kind: Literal["battle", "gear_offer", "level_up", "complete_offer", "campfire", "ended"]
    battle_index: int | None = None
    boss: bool | None = None
    level: int | None = None
    points: int | None = None
    tier_up: bool | None = None
    """這次升級讓角色升階（升階提示「可以重閃第 3 格轉型」；Phase 3W-5 提供旗標，3W-6 顯示）。"""
    after_battle: int | None = None
    offer: OfferOut | None = None
    victory: bool | None = None
    gear: GearOfferOut | None = None
    """戰後裝備三選一（``gear_offer``；Phase 3K-2）。"""


class LlmStatsOut(_ApiModel):
    """一輪的 LLM 生成統計（Phase 4-L6b；與 ``trpg run`` 摘要同源）。"""

    total: int
    """請 LLM 提議的題數。"""
    succeeded: int
    failed: int
    """退回（提議器 3 次重試後仍失敗，改用一般生成）的題數。"""
    fallback_permille: int
    attempts: int
    """呼叫模型的總次數（提議）。"""
    alert_permille: int
    alert: bool
    """退回率超過提醒線。"""
    named: int
    name_generated: int
    name_fallback: int


class RunResponse(_ApiModel):
    run_id: str
    seed: int
    node: NodeOut
    hero: HeroOut
    battles_done: int
    plan: tuple[BattlePlanOut, ...]
    history: tuple[BattleRecord, ...]
    battle_id: str | None
    """進行中的戰鬥（用 ``/api/battles/{battle_id}`` 操作）；沒有時為 ``None``。"""
    test_mode: bool = False
    """測試模式的一輪（Phase 3-39；不計入統計，介面要標記）。"""
    test_equipment: dict[str, str] = Field(default_factory=dict)
    """測試模式挑的裝備（欄位 → 物品 ID）。"""
    resource_rule_zh: str = ""
    """戰鬥之間 HP、法力怎麼回復的說明（Phase 3-41b，由 ``roguelite.yaml`` 的營火設定產生）。"""
    llm: bool = False
    """這一輪有開 LLM 生成（Phase 4-L6b）。"""
    llm_notice: str | None = None
    """只在開新一輪的回應帶出一次（例如「連不到本機模型，這一輪改用一般技能生成」）。"""
    load_notice: str | None = None
    """只在讀檔的回應帶出一次（例如「這場戰鬥的紀錄格式已更新，從這場的開頭重新開始。」，3W-R1）。"""
    llm_stats: LlmStatsOut | None = None
    """LLM 統計；這一輪沒開 LLM 且沒有任何題目時為 ``None``。"""
    pending_flash: PendingFlashOut | None = None
    """已付點、還沒選的閃現選項（Phase 3W-5）。"""


class RunBattleResponse(_ApiModel):
    run: RunResponse
    battle: BattleResponse


class SaveOut(_ApiModel):
    run_id: str
    file: str
    """存檔檔名（在伺服器的存檔資料夾內）。"""
    format: str
    in_battle: bool


class SaveSummary(_ApiModel):
    run_id: str
    build_id: str
    build_name_zh: str
    seed: int
    level: int
    battles_done: int
    battles_total: int
    node: Literal["battle", "gear_offer", "level_up", "complete_offer", "campfire", "ended"]
    in_battle: bool
    victory: bool | None = None
    """已結束的一輪是否勝利；未結束為 ``None``。"""
    test_mode: bool = False
    """測試模式的一輪（Phase 3-39）。"""
