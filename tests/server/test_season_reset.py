"""季末重置（Phase 5F-5；``docs/phases/Phase5計畫.md`` 第 40 節）。

建一個有數值的假賽季（角色、世界、配方、報名、留言、首殺、評分榜、循環賽、編年史、帳號），重置後
照 :mod:`trpg.server.season_policy` 逐一檢查每個分類欄位：數值類清掉、紀念類保留且值不變、
``CARRIED`` 的內容寫進編年史。
"""

from __future__ import annotations

import dataclasses
import importlib.util
import io
import json
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from types import ModuleType

import pytest
from pydantic import BaseModel

from trpg.content.battle import DollLook
from trpg.content.library import ContentLibrary, load_library
from trpg.server.accounts import AccountRecord, AccountStore
from trpg.server.chronicle import (
    ChronicleHero,
    LeagueChronicle,
    LeagueChronicleRank,
    LeagueChronicleSeason,
    LeagueChronicleStore,
    RecipeDiscovery,
    SeasonChronicle,
    SeasonChronicleEntry,
    SeasonChronicleStore,
)
from trpg.server.first_kills import FirstKill
from trpg.server.league import LeagueMatch, LeagueRecord, new_record
from trpg.server.notes import LocationNote
from trpg.server.season_boss_board import BossBoardEntry
from trpg.server.season_policy import (
    CARRIED,
    HERO_LEGACY_FIELDS,
    MEMORIAL,
    NUMERIC,
    SEASON_POLICY,
    fields_of_kind,
)
from trpg.server.season_reset import (
    SeasonResetError,
    SeasonResetReport,
    next_season_id,
    season_name_zh,
    season_reset,
)
from trpg.world.league import league_rules
from trpg.world.league_actions import LeagueEnterAction
from trpg.world.save import dumps_char, dumps_world, loads_world, write_atomic
from trpg.world.state import CharacterState, CraftRecipe, RecipeRecord, WorldState
from trpg.world.step import new_character, world_step

NOON = 1_793_592_000
DAY = 24 * 3600
ENDED = NOON + 15 * DAY  # 第 16 天：14 天的賽季已經結束
NEXT_START = NOON + 20 * DAY
ELITE = "bandit_boss"
SKELETON = "granny_past"
DOLL = DollLook(skin="#a8724c", hair="short")


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    library = load_library()
    season = library.world_season
    assert season is not None and season.league is not None
    league = season.league.model_copy(update={"maps": ("open_plain",), "seeds": 1})
    return dataclasses.replace(library, world_season=season.model_copy(update={"league": league}))


# -- 假賽季 -------------------------------------------------------------------


@dataclasses.dataclass
class Season:
    save_dir: Path
    world_dir: Path
    accounts: AccountStore
    account_ids: tuple[str, str]
    world: WorldState
    chars: tuple[CharacterState, ...]
    league: LeagueRecord
    archived: LeagueRecord
    memorial_files: dict[str, bytes]


def _char(library: ContentLibrary, cid: str, build: str, *, race: str | None) -> CharacterState:
    heroes = {b.id: b.hero for b in library.builds.builds}
    hero = heroes[build].model_copy(update={"name_zh": f"勇者{cid}", "race": race, "doll": DOLL})
    char = new_character(library, cid, hero, region="cloud_ridge")
    return char.model_copy(
        update={
            "level": 7,
            "xp": 123,
            "gold": 456,
            "quest_coins": 9,
            "elite_kills": (ELITE,),
            "finished_skeletons": (SKELETON,),
            "story_flags": ("met_ayue",),
        }
    )


def _recipe(code: str, name: str) -> RecipeRecord:
    return RecipeRecord(
        code=code,
        recipe=CraftRecipe(slot_type="head", rarity="rare", item_level=5, grade="iron_ore"),
        name_zh=name,
        discoverer="c1",
        discoverer_name="勇者c1",
        discovered_at=NOON + 3 * DAY,
        hidden=None,
        steps=(),
        listed=True,
        season_id="s1",
    )


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def _world(library: ContentLibrary, chars: tuple[CharacterState, ...]) -> WorldState:
    world = WorldState(season_id="s1", season_seed=20261102, season_start=NOON)
    for index, char in enumerate(chars):
        step = world_step(
            library, world, char, LeagueEnterAction(), NOON + index, actor=f"acc{index}"
        )
        world = step.world
    return world.model_copy(
        update={
            "flags": ("ashen_waste_open",),
            "seal_keys": 7,
            "recipes": (_recipe("0123456789", "霧鐵盔"), _recipe("abcdef0123", "灰燼盔")),
            "level_bonus": {"ashen_waste": 1},
            "shop_price": {"shop_iron_lady": 200},  # 5F-5b
            "rolled_day": 5,
        }
    )


def _fake_season(library: ContentLibrary, root: Path) -> Season:
    save_dir = root / "saves"
    world_dir = save_dir / "world"
    ids = iter(("a0000001", "a0000002"))
    accounts = AccountStore(save_dir / "accounts", clock=lambda: NOON, new_id=lambda: next(ids))
    alice = accounts.create("alice", "password123")
    bob = accounts.create("bobby", "password123")
    chars = (
        _char(library, "c1", "build_support", race="fox"),
        _char(library, "c2", "build_charger", race=None),
    )
    accounts.attach_character(alice.account_id, "c1")
    accounts.attach_character(bob.account_id, "c2")
    world = _world(library, chars)
    write_atomic(world_dir / "world.json", dumps_world(world))
    for char in chars:
        write_atomic(world_dir / "chars" / f"{char.character_id}.json", dumps_char(char))
    write_atomic(world_dir / "log.jsonl", '{"seq": 1}\n{"seq": 2}\n')
    note = LocationNote(
        note_id="n0000abcd",
        region="cloud_ridge",
        location="mist_ferry",
        character_id="c1",
        name="勇者c1",
        text="小心狼",
        at=NOON,
    )
    _write_json(world_dir / "notes.json", {"format": "trpg-notes/1", "notes": [note.model_dump()]})
    kill = FirstKill(
        kind="elite",
        target=ELITE,
        target_name_zh="盜賊頭目",
        character_id="c1",
        name="勇者c1",
        region="cloud_ridge",
        location="north_slope",
        seq=1,
        at=NOON + DAY,
        account_id=alice.account_id,
    )
    _write_json(
        world_dir / "first_kills.json",
        {"format": "trpg-firstkills/1", "kills": [kill.model_dump(mode="json")]},
    )
    board = BossBoardEntry(
        season_id="s1",
        boss="shard_lord",
        character_id="c2",
        account_id=bob.account_id,
        name="勇者c2",
        score=88,
        rounds=9,
        survivors=3,
        allies=2,
        no_down=True,
        title_zh="不倒",
        region="cloud_ridge",
        location="rift_gate",
        seq=2,
        at=NOON + 9 * DAY,
    )
    _write_json(
        world_dir / "season_boss_board.json",
        {"format": "trpg-bossboard/1", "entries": [board.model_dump(mode="json")]},
    )
    write_atomic(world_dir / "season_boss" / "s1-first-kill.json", '{"log": true}\n')
    rules = league_rules(library)
    assert rules is not None
    record = new_record(rules, world, NOON + 14 * DAY, key="k1")
    done = tuple(
        m.model_copy(update={"status": "done", "winner": m.a, "rounds": 6}) for m in record.matches
    )
    league = record.model_copy(update={"matches": done})
    archived = record.model_copy(update={"stale_zh": "規則已變、不能重播"})
    write_atomic(world_dir / "league" / "league.json", league.model_dump_json(indent=1))
    write_atomic(
        world_dir / "league" / "archive" / "league-s1-1-0.json", archived.model_dump_json(indent=1)
    )
    for match in league.matches:
        write_atomic(world_dir / "league" / "matches" / f"{match.id}.json", '{"m": 1}\n')
    LeagueChronicleStore(world_dir).write(
        LeagueChronicleSeason(
            season_id="s1",
            finished_at=NOON + 14 * DAY,
            matches=len(league.matches),
            ranks=(
                LeagueChronicleRank(
                    rank=1,
                    account=alice.account_id,
                    name="勇者c1",
                    build_zh="法器・狐族",
                    wins=2,
                    losses=0,
                    draws=0,
                    hp_permille_total=900,
                    rounds_total=12,
                ),
            ),
        )
    )
    SeasonChronicleStore(world_dir).add(
        SeasonChronicleEntry(
            season_id="s0", name_zh="第零季", started_at=1, reset_at=2, next_season_id="s1"
        )
    )
    write_atomic(save_dir / "bot" / "announce_state.json", '{"format": "trpg-announce/1"}\n')
    write_atomic(save_dir / "run-abc.json", "{}\n")
    memorial = [
        world_dir / "first_kills.json",
        world_dir / "season_boss_board.json",
        world_dir / "season_boss" / "s1-first-kill.json",
        world_dir / "chronicle" / "league.json",
        save_dir / "bot" / "announce_state.json",
        save_dir / "run-abc.json",
        *sorted((save_dir / "accounts").glob("*.json")),
    ]
    return Season(
        save_dir=save_dir,
        world_dir=world_dir,
        accounts=accounts,
        account_ids=(alice.account_id, bob.account_id),
        world=world,
        chars=chars,
        league=league,
        archived=archived,
        memorial_files={str(p.relative_to(save_dir)): p.read_bytes() for p in memorial},
    )


def _tree(root: Path) -> dict[str, bytes]:
    files = (p for p in sorted(root.rglob("*")) if p.is_file())
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in files}


def _reset(
    library: ContentLibrary, season: Season, *, dry_run: bool = False, **kw: object
) -> SeasonResetReport:
    return season_reset(
        library,
        season.save_dir,
        start=NEXT_START,
        now=ENDED,
        accounts=season.accounts,
        backup_root=season.save_dir.parent / "backups",
        dry_run=dry_run,
        **kw,  # type: ignore[arg-type]
    )


# -- 逐一檢查每個分類欄位 ------------------------------------------------------


def _check_character(season: Season) -> None:
    assert not (season.world_dir / "chars").exists()  # 整個數值類：角色檔刪掉
    entry = SeasonChronicleStore(season.world_dir).season("s1")
    assert entry is not None
    heroes = {h.character_id: h for h in entry.heroes}
    for char in season.chars:
        hero = heroes[char.character_id]
        for name in HERO_LEGACY_FIELDS:  # CARRIED：名字與外觀
            got = hero.name if name == "name_zh" else getattr(hero, name)
            assert got == getattr(char.hero, name)
        assert hero.elites and ELITE not in hero.elites  # CARRIED：精英（換成中文名）
        assert all(e in hero.text_zh for e in hero.elites)
        assert len(hero.elites) == len(char.elite_kills)
        assert len(hero.events) == len(char.finished_skeletons)  # CARRIED：完成的事件
        assert hero.text_zh.startswith("第一季：擊倒")
        assert "渡婆婆" in hero.text_zh


def _check_world(season: Season) -> None:
    world = loads_world((season.world_dir / "world.json").read_text(encoding="utf-8"))
    fresh = WorldState(season_id="x", season_seed=0, season_start=0)
    replaced = {"season_id", "season_seed", "season_start"}
    for name in fields_of_kind(WorldState, NUMERIC):
        if name in replaced:
            assert getattr(world, name) != getattr(season.world, name)
        else:
            assert getattr(world, name) == getattr(fresh, name), name
    assert world.season_id == "s2" and world.season_start == NEXT_START


def _check_recipe(season: Season) -> None:
    entry = SeasonChronicleStore(season.world_dir).season("s1")
    assert entry is not None
    found = {r.code: r for r in entry.recipes}
    assert len(found) == len(season.world.recipes)
    for record in season.world.recipes:
        discovery = found[record.code]
        for name in fields_of_kind(RecipeRecord, MEMORIAL):
            assert getattr(discovery, name) == getattr(record, name)
        for name in fields_of_kind(RecipeRecord, NUMERIC):
            assert name not in RecipeDiscovery.model_fields  # 數值類沒有留下來


def _check_unchanged(season: Season) -> None:
    for relative, content in season.memorial_files.items():
        assert (season.save_dir / relative).read_bytes() == content, relative


def _check_note(season: Season) -> None:
    assert not (season.world_dir / "notes.json").exists()


def _league_history(season: Season) -> Path:
    return season.world_dir / "league_history" / "s1"


def _check_league(season: Season) -> None:
    assert not (season.world_dir / "league").exists()
    folder = _league_history(season)
    pairs = (
        (folder / "league.json", season.league),
        (folder / "archive" / "league-s1-1-0.json", season.archived),
    )
    for path, before in pairs:
        after = LeagueRecord.model_validate_json(path.read_text(encoding="utf-8"))
        for name in fields_of_kind(LeagueRecord, MEMORIAL):
            assert getattr(after, name) == getattr(before, name), name
        for name in fields_of_kind(LeagueRecord, NUMERIC):
            assert getattr(after, name) == (), name
    assert before.entries  # 假賽季真的有報名快照


def _check_match(season: Season) -> None:
    after = LeagueRecord.model_validate_json(
        (_league_history(season) / "league.json").read_text(encoding="utf-8")
    )
    assert after.matches == season.league.matches
    for match in season.league.matches:
        assert (_league_history(season) / "matches" / f"{match.id}.json").is_file()


def _check_chronicle(season: Season) -> None:
    store = SeasonChronicleStore(season.world_dir)
    assert [s.season_id for s in store.load().seasons] == ["s0", "s1"]
    entry = store.season("s1")
    assert entry is not None
    assert (entry.name_zh, entry.next_season_id, entry.reset_at) == ("第一季", "s2", ENDED)
    assert entry.started_at == NOON
    account = {h.character_id: h.account_id for h in entry.heroes}
    assert account == {"c1": season.account_ids[0], "c2": season.account_ids[1]}
    assert LeagueChronicleStore(season.world_dir).season("s1") is not None


def _check_accounts(season: Season) -> None:
    _check_unchanged(season)
    records = {a.account_id: a for a in AccountStore(season.save_dir / "accounts").all()}
    assert records[season.account_ids[0]].characters == ("c1",)


CHECKS: Mapping[type[BaseModel], Callable[[Season], None]] = {
    CharacterState: _check_character,
    WorldState: _check_world,
    RecipeRecord: _check_recipe,
    FirstKill: _check_unchanged,
    BossBoardEntry: _check_unchanged,
    AccountRecord: _check_accounts,
    LocationNote: _check_note,
    LeagueRecord: _check_league,
    LeagueMatch: _check_match,
    LeagueChronicle: _check_unchanged,
    LeagueChronicleSeason: _check_unchanged,
    LeagueChronicleRank: _check_unchanged,
    SeasonChronicle: _check_chronicle,
    SeasonChronicleEntry: _check_chronicle,
    ChronicleHero: _check_character,
    RecipeDiscovery: _check_recipe,
}


def test_every_policy_model_is_checked() -> None:
    assert set(CHECKS) == set(SEASON_POLICY)


def test_reset_clears_numeric_and_keeps_memorial(library: ContentLibrary, tmp_path: Path) -> None:
    season = _fake_season(library, tmp_path)
    report = _reset(library, season)
    assert (report.old_season, report.new_season, report.dry_run) == ("s1", "s2", False)
    for model, check in CHECKS.items():
        check(season)
        assert model in SEASON_POLICY
    assert report.chronicle[0].startswith("勇者c1：第一季：擊倒")
    cleared = {line.label_zh: line.count for line in report.cleared}
    assert cleared["角色"] == 2 and cleared["地點留言"] == 1 and cleared["配方表"] == 2
    assert cleared["世界日誌"] == 2 and cleared["循環賽報名快照"] == 2


def test_carried_fields_are_numeric_and_written(library: ContentLibrary, tmp_path: Path) -> None:
    names = {m.__name__: m for m in SEASON_POLICY}
    for model_name, field in CARRIED:
        assert SEASON_POLICY[names[model_name]][field] == NUMERIC
    season = _fake_season(library, tmp_path)
    _reset(library, season)
    _check_character(season)
    _check_recipe(season)


def test_backup_copies_whole_save_dir(library: ContentLibrary, tmp_path: Path) -> None:
    season = _fake_season(library, tmp_path)
    before = _tree(season.save_dir)
    report = _reset(library, season)
    assert report.backup is not None
    backup = Path(report.backup)
    assert backup.parent == season.save_dir.parent / "backups"
    assert backup.name.startswith("saves-") and backup.name.endswith("-s1")
    copied = _tree(backup)
    expected = {k: v for k, v in before.items() if not k.endswith(".lock")}
    assert copied == expected


def test_backup_root_inside_saves_is_refused(library: ContentLibrary, tmp_path: Path) -> None:
    season = _fake_season(library, tmp_path)
    before = _tree(season.world_dir)
    with pytest.raises(SeasonResetError, match="不能放在存檔資料夾裡"):
        season_reset(
            library,
            season.save_dir,
            start=NEXT_START,
            now=ENDED,
            dry_run=False,
            backup_root=season.save_dir / "backups",
        )
    assert _tree(season.world_dir) == before


def test_dry_run_writes_nothing(library: ContentLibrary, tmp_path: Path) -> None:
    season = _fake_season(library, tmp_path)
    before = _tree(tmp_path)
    report = _reset(library, season, dry_run=True)
    assert report.dry_run and report.backup is None
    assert _tree(tmp_path) == before
    assert report.new_season == "s2"
    kept = {line.label_zh for line in report.kept}
    assert {"帳號", "首殺紀錄", "賽季 Boss 評分榜", "循環賽場次"} <= kept
    assert len(report.chronicle) == 2


def test_deterministic(library: ContentLibrary, tmp_path: Path) -> None:
    """兩份相同的存檔各重置一次：世界資料夾逐位元相同（備份名只看 ``now``，也相同）。"""
    trees = []
    for name in ("a", "b"):
        season = _fake_season(library, tmp_path / name)
        report = _reset(library, season)
        assert report.backup is not None
        trees.append((_tree(season.world_dir), Path(report.backup).name))
    assert trees[0] == trees[1]


def test_unfinished_season_needs_force(library: ContentLibrary, tmp_path: Path) -> None:
    season = _fake_season(library, tmp_path)
    early = NOON + 5 * DAY
    with pytest.raises(SeasonResetError, match="還沒結束"):
        season_reset(library, season.save_dir, start=NEXT_START, now=early)
    report = season_reset(library, season.save_dir, start=NEXT_START, now=early, force=True)
    assert report.warnings == ("這一季還沒結束",)


def test_pending_league_needs_force(library: ContentLibrary, tmp_path: Path) -> None:
    season = _fake_season(library, tmp_path)
    matches = tuple(m.model_copy(update={"status": "pending"}) for m in season.league.matches)
    pending = season.league.model_copy(update={"matches": matches})
    write_atomic(season.world_dir / "league" / "league.json", pending.model_dump_json())
    with pytest.raises(SeasonResetError, match="循環賽還有"):
        _reset(library, season, dry_run=True)


def test_season_ids(library: ContentLibrary, tmp_path: Path) -> None:
    assert next_season_id("s1") == "s2"
    assert next_season_id("s9") == "s10"
    assert season_name_zh("s1") == "第一季"
    assert season_name_zh("s10") == "第十季"
    assert season_name_zh("s23") == "第二十三季"
    with pytest.raises(SeasonResetError):
        next_season_id("beta")
    season = _fake_season(library, tmp_path)
    with pytest.raises(SeasonResetError, match="一樣"):
        _reset(library, season, dry_run=True, season_id="s1")
    with pytest.raises(SeasonResetError, match="已經用過"):
        _reset(library, season, dry_run=True, season_id="s0")
    with pytest.raises(SeasonResetError, match="不合法"):
        _reset(library, season, dry_run=True, season_id="S-2")
    report = _reset(library, season, season_id="s1b", seed=42)
    world = loads_world((season.world_dir / "world.json").read_text(encoding="utf-8"))
    assert (report.new_season, world.season_id, world.season_seed) == ("s1b", "s1b", 42)


def test_rerun_after_interrupt_keeps_full_chronicle(
    library: ContentLibrary, tmp_path: Path
) -> None:
    """編年史寫好、角色刪了一半時中斷（world.json 還是舊季）：重跑不會用半套資料蓋掉編年史。"""
    season = _fake_season(library, tmp_path)
    full = _reset(library, season, dry_run=True)
    store = SeasonChronicleStore(season.world_dir)
    from trpg.server import season_reset as module  # noqa: PLC0415

    entry = module._plan(
        library,
        module._read_current(season.world_dir),
        season.accounts.all(),
        now=ENDED,
        season_id=None,
        seed=None,
        force=False,
    ).entry
    store.add(entry)
    (season.world_dir / "chars" / "c2.json").unlink()
    _reset(library, season)
    saved = store.season("s1")
    assert saved is not None and len(saved.heroes) == 2 == len(full.chronicle)


def test_no_world_is_refused(library: ContentLibrary, tmp_path: Path) -> None:
    with pytest.raises(SeasonResetError, match="還沒有世界存檔"):
        season_reset(library, tmp_path, start=NEXT_START, now=ENDED)


def _script() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "season_reset.py"
    spec = importlib.util.spec_from_file_location("season_reset_script", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["season_reset_script"] = module
    spec.loader.exec_module(module)
    return module


def test_script_dry_run_then_execute(library: ContentLibrary, tmp_path: Path) -> None:
    season = _fake_season(library, tmp_path)
    script = _script()
    base = [
        "--start-date",
        "2027-01-01",
        "--save-dir",
        str(season.save_dir),
        "--accounts-dir",
        str(season.save_dir / "accounts"),
        "--backup-root",
        str(tmp_path / "backups"),
    ]
    before = _tree(season.save_dir)
    out, err = io.StringIO(), io.StringIO()
    if script.main(base, out, err) != 0:  # 真實時間：假賽季可能還沒結束
        assert "還沒結束" in err.getvalue()
        base.append("--force")
        out = io.StringIO()
        assert script.main(base, out, err) == 0
    assert "dry-run" in out.getvalue() and "角色 2" in out.getvalue()
    assert _tree(season.save_dir) == before
    out = io.StringIO()
    assert script.main([*base, "--execute"], out, err) == 0
    assert "已重置：s1 → s2" in out.getvalue() and "備份：" in out.getvalue()
    assert not (season.world_dir / "chars").exists()
