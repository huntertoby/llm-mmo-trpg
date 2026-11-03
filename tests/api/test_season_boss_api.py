"""賽季 Boss 的伺服器端：首殺紀錄、首殺戰鬥紀錄可重播、評分榜、公告板區塊（Phase 5F-3；
``docs/phases/Phase5計畫.md`` 37.7）。"""

from __future__ import annotations

import io
from pathlib import Path

from tests.world.helpers import NOON, PARTY
from trpg.api.season_view import season_board
from trpg.api.sessions import SessionStore
from trpg.api.world import WorldStore
from trpg.cli.battle import cmd_replay
from trpg.content.library import ContentLibrary
from trpg.engine.battle import begin_battle
from trpg.engine.runner import apply_step
from trpg.server.accounts import AccountTitle
from trpg.server.announce import load_templates, render_first_kill
from trpg.server.season_boss_board import BossBoardEntry, SeasonBossBoard
from trpg.shared.types import Team
from trpg.world.actions import FightAction
from trpg.world.battle import auto_steps, grow_enemy, prepare_battle
from trpg.world.season_boss import challenge
from trpg.world.season_events import SeasonBossAction, SeasonBossClearedEvent
from trpg.world.state import CharacterState
from trpg.world.step import world_step

DAY10 = NOON + 9 * 24 * 3600
START = ("阿霧", "fire_staff", ("ignite", "marked"))


def _store(library: ContentLibrary, root: Path) -> WorldStore:
    store = WorldStore(library, SessionStore(library), root, prefetch=False, clock=lambda: DAY10)
    store.season_start = NOON
    store.actor_of = lambda _cid: "acc1"
    return store


def _ready(store: WorldStore) -> CharacterState:
    """10 級的火術士主角（底稿照敵我同一套成長拉到 10 級，同模擬腳本）＋傭兵。"""
    name, weapon, keywords = START
    char = store.create(name, weapon, keywords, seed=0)
    base = next(b.hero for b in store.library.builds.builds if b.id == "build_fire")
    grown, skills = grow_enemy(store.library, base, 10)
    hero = grown.model_copy(update={"max_hp": base.max_hp, "level": 1, "name_zh": name})
    char = char.model_copy(
        update={
            "hero": hero,
            "generated_skills": skills,
            "level": 10,
            "mercenaries": PARTY,
            "seal_key_sources": ("summit_boss",),
        }
    )
    store._save_char(char)
    return char


def _winning(library: ContentLibrary, store: WorldStore, char: CharacterState) -> CharacterState:
    """找一個挑戰種子打得贏的角色（改 ``battle`` 串流的計數；確定性）。"""
    world = store.world()
    for counter in range(12):
        trial = char.model_copy(update={"rng_counters": {"battle": counter}})
        _, challenged, _ = challenge(library, world, trial, DAY10, actor="probe")
        prepared = prepare_battle(library, challenged)
        state = begin_battle(prepared.setup, prepared.seed).state
        for step in auto_steps(library, challenged):
            state = apply_step(state, step).state
        if state.winner is Team.ALLY:
            return trial
    raise AssertionError("找不到打得贏的挑戰種子")


def test_first_kill_records_replayable_log(library: ContentLibrary, tmp_path: Path) -> None:
    root = tmp_path / "world"
    store = _store(library, root)
    granted: list[tuple[str, AccountTitle]] = []
    store.grant_title = lambda account, title: granted.append((account, title))
    char = _winning(library, store, _ready(store))
    store._save_char(char)
    store.act(char.character_id, SeasonBossAction())
    challenged = store.character(char.character_id)
    steps = auto_steps(library, challenged)
    outcome = store._apply(challenged, FightAction(steps=steps), DAY10 + 60)
    cleared = next(e for e in outcome.events if isinstance(e, SeasonBossClearedEvent))
    assert cleared.first
    (kill,) = [k for k in store.first_kills.all() if k.kind == "season_boss"]
    assert kill.account_id == "acc1" and kill.target == "rift_shard_lord"
    assert kill.battle_log is not None
    out = io.StringIO()
    assert cmd_replay(root / kill.battle_log, out) == 0
    assert "重播驗證通過" in out.getvalue()
    (entry,) = store.boss_board.top(store.world().season_id)
    assert entry.score == cleared.score and entry.account_id == "acc1"
    # 5F-3b：帳號層級的紀念稱號「碎晶的終結者」（評分榜照樣顯示）
    ((account, title),) = granted
    assert account == "acc1" and title.name_zh == cleared.title_zh == "碎晶的終結者"
    assert title.id == "season_boss:rift_shard_lord" and title.character_id == char.character_id
    assert title.season_id == store.world().season_id
    text = render_first_kill(load_templates(), kill)
    assert text.startswith("【賽季首殺】") and "碎晶之主" in text
    board = season_board(
        library,
        store.world(),
        store.character(char.character_id),
        DAY10 + 120,
        actor="acc1",
        boss_board=store.boss_board.top(store.world().season_id),
    )
    boss = board.season_boss
    assert boss is not None and boss.status == "open" and boss.attempts_left == 2
    assert boss.first_kill_zh is not None and boss.board[0].mine


def _cleared(score: int, rounds: int) -> SeasonBossClearedEvent:
    return SeasonBossClearedEvent(
        boss="rift_shard_lord",
        name_zh="碎晶之主",
        first=False,
        score=score,
        rounds=rounds,
        survivors=3,
        allies=3,
        no_down=False,
        title_zh="碎晶的終結者",
    )


def test_board_keeps_each_characters_best(library: ContentLibrary, tmp_path: Path) -> None:
    store = _store(library, tmp_path / "world")
    a, b = _ready(store), _ready(store)
    board = SeasonBossBoard(tmp_path / "board")
    (tmp_path / "board").mkdir()

    def put(char: CharacterState, score: int, rounds: int, seq: int) -> bool:
        cleared = _cleared(score, rounds)
        entry = board.record(
            char, char, cleared, season_id="s1", account_id=None, seq=seq, now=NOON
        )
        return entry is not None

    assert put(a, 900, 10, 1) and put(b, 1100, 8, 2)
    assert not put(a, 800, 12, 3)  # 比較差：不換
    assert put(a, 1100, 7, 4)  # 同分輪數少：換
    assert [(e.character_id, e.score, e.rounds) for e in board.top("s1")] == [
        (a.character_id, 1100, 7),
        (b.character_id, 1100, 8),
    ]
    assert board.top("s2") == ()
    assert isinstance(board.all()[0], BossBoardEntry)


def test_failed_attempt_is_not_on_the_board(library: ContentLibrary, tmp_path: Path) -> None:
    store = _store(library, tmp_path / "world")
    char = _ready(store)
    step = world_step(library, store.world(), char, SeasonBossAction(), DAY10, actor="acc1")
    assert step.char.pending_encounter is not None
    assert store.boss_board.all() == ()
