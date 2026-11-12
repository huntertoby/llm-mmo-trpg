"""``Event`` discriminated union 與 TypeAdapter（成員順序影響 JSON schema，勿調整）。"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, TypeAdapter

from trpg.engine.events.combat import (
    AttackIntercepted,
    AttackRolled,
    ChainLimitReached,
    ConductBlocked,
    DamageDealt,
    Healed,
    ManeuverRolled,
    PushResisted,
    ReactionDeclined,
    ReactionModeSet,
    ReactionTriggered,
    ShieldAbsorbed,
    ShieldEnded,
    ShieldGained,
    StatusApplied,
    StatusConverted,
    StatusRemoved,
    StatusResisted,
    StatusSaveRolled,
    UnitDowned,
)
from trpg.engine.events.environment import (
    BossPhaseChanged,
    EnvironmentEnded,
    EnvironmentStarted,
    MapEventTriggered,
    UnitEscaped,
    UnitSpawned,
    WeatherChanged,
)
from trpg.engine.events.flow import (
    BattleEnded,
    BattleStarted,
    GuardsRetreated,
    InitiativeRolled,
    InitiativeTieBroken,
    RoundEnded,
    RoundStarted,
    TurnEnded,
    TurnOrderSet,
    TurnSkipped,
    TurnStarted,
)
from trpg.engine.events.movement import (
    Collided,
    EnteredDeadlyTerrain,
    GuardSet,
    MoveBlocked,
    RaceSkillUsed,
    UnitAimed,
    UnitCharged,
    UnitDashed,
    UnitFell,
    UnitMoved,
    UnitRan,
    UnitSlid,
    UnitStoodUp,
    UnitVaulted,
    WeaponReloaded,
)
from trpg.engine.events.objects import (
    CheckRolled,
    EffectFizzled,
    ElementTouched,
    ObjectAttacked,
    ObjectCreated,
    ObjectDamaged,
    ObjectDestroyed,
    ObjectExpired,
    ObjectExploded,
    ObjectHurled,
    ObjectIgnited,
    ObjectMoved,
    ObjectToppled,
    ShotPierced,
    SurfaceBlown,
    SurfaceChanged,
    SurfaceEntered,
    TerrainChanged,
    TrapExpired,
    TrapPlaced,
    TrapRevealed,
    TrapTriggered,
)
from trpg.engine.events.parts import PartBroken, PartDamaged, PartStatDown, SkillSealed
from trpg.engine.events.rules import (
    ApGranted,
    ApRefunded,
    BombExploded,
    BombTicked,
    DamageRedirected,
    DeathCheated,
    FormEntered,
    FormLeft,
    FormUpkeepPaid,
    OathBroken,
    ReactionsGranted,
    ResourceRestored,
    RuleChangeTriggered,
    SkillCopied,
    SourceChanged,
    StanceUpkeepPaid,
    UnitRevived,
)
from trpg.engine.events.skills import (
    ActivationExpired,
    BacklashTriggered,
    ChargeActivated,
    FollowupCancelled,
    FollowupCharged,
    GambleRolled,
    GearHpLost,
    GearTriggered,
    OverloadTriggered,
    SkillActivated,
    SkillCooldownChanged,
    SkillFollowup,
    SkillGranted,
    SkillGrantExpired,
    SkillTriggered,
    SkillUsed,
    StacksChanged,
    TriggerLimitReached,
)
from trpg.engine.events.summons import (
    InfusedSkillCast,
    InfusionFizzled,
    SkillInfused,
    SnareTriggered,
    SummonCommanded,
    SummonDetonated,
    SummonExpired,
    SummonModeSet,
    SummonPulled,
    TotemPulsed,
    UnitSummoned,
    WallToppled,
)
from trpg.engine.events.zones import (
    RuneInscribed,
    RuneRemoved,
    ZoneCreated,
    ZoneExpanded,
    ZoneExpired,
    ZoneMoved,
    ZoneTriggered,
)

type Event = Annotated[
    BattleStarted
    | InitiativeRolled
    | InitiativeTieBroken
    | TurnOrderSet
    | RoundStarted
    | RoundEnded
    | TurnStarted
    | TurnEnded
    | GuardsRetreated
    | BattleEnded
    | UnitMoved
    | UnitStoodUp
    | UnitRan
    | UnitVaulted
    | RaceSkillUsed
    | GuardSet
    | UnitAimed
    | WeaponReloaded
    | MoveBlocked
    | Collided
    | UnitFell
    | EnteredDeadlyTerrain
    | AttackRolled
    | DamageDealt
    | ConductBlocked
    | Healed
    | ShieldGained
    | ShieldAbsorbed
    | ShieldEnded
    | StatusApplied
    | StatusRemoved
    | StatusSaveRolled
    | StatusResisted
    | StatusConverted
    | TurnSkipped
    | UnitDowned
    | ChainLimitReached
    | ObjectAttacked
    | ObjectDamaged
    | ObjectDestroyed
    | ObjectIgnited
    | ObjectExploded
    | ObjectMoved
    | ObjectHurled
    | ObjectToppled
    | ShotPierced
    | ObjectCreated
    | ObjectExpired
    | SurfaceChanged
    | SurfaceBlown
    | TerrainChanged
    | ElementTouched
    | SurfaceEntered
    | CheckRolled
    | EffectFizzled
    | ManeuverRolled
    | PushResisted
    | ReactionTriggered
    | ReactionDeclined
    | ReactionModeSet
    | AttackIntercepted
    | EnvironmentStarted
    | EnvironmentEnded
    | MapEventTriggered
    | UnitSpawned
    | UnitEscaped
    | UnitSummoned
    | SummonExpired
    | SummonModeSet
    | SummonCommanded
    | SkillInfused
    | InfusedSkillCast
    | InfusionFizzled
    | SnareTriggered
    | SummonPulled
    | TotemPulsed
    | SummonDetonated
    | WallToppled
    | SkillUsed
    | SkillCooldownChanged
    | FormEntered
    | FormLeft
    | FormUpkeepPaid
    | StanceUpkeepPaid
    | SkillTriggered
    | TriggerLimitReached
    | StacksChanged
    | TrapPlaced
    | TrapRevealed
    | TrapTriggered
    | TrapExpired
    | SourceChanged
    | ApGranted
    | ApRefunded
    | UnitRevived
    | BombTicked
    | BombExploded
    | DeathCheated
    | DamageRedirected
    | ReactionsGranted
    | ResourceRestored
    | UnitDashed
    | UnitSlid
    | UnitCharged
    | SkillCopied
    | SkillFollowup
    | FollowupCharged
    | FollowupCancelled
    | ZoneCreated
    | ZoneMoved
    | ZoneExpanded
    | ZoneTriggered
    | ZoneExpired
    | RuneInscribed
    | RuneRemoved
    | SkillActivated
    | ActivationExpired
    | SkillGranted
    | SkillGrantExpired
    | RuleChangeTriggered
    | GambleRolled
    | BacklashTriggered
    | OverloadTriggered
    | GearHpLost
    | GearTriggered
    | ChargeActivated
    | OathBroken
    | BossPhaseChanged
    | WeatherChanged
    | PartDamaged
    | PartBroken
    | SkillSealed
    | PartStatDown,
    Field(discriminator="type"),
]

EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)
EVENT_LIST_ADAPTER: TypeAdapter[list[Event]] = TypeAdapter(list[Event])
