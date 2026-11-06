"""灰燼荒原的小模擬（Phase 5F-5a；5F-5b 加候選內容、敵人高 2 級與灰燼瑪菈主角）。

走大世界的真實路徑（``prepare_battle``）：我方＝主角＋2 名系統傭兵（輸出與控制主角帶預設的賽倫、
回春；守護與輔助主角帶灰燼瑪菈、回春／珊瑚），主角是數種 build 的底稿照大世界敵我同一套成長規則拉到
地點的建議等級；雙方都由效用 AI 操作；``max_rounds`` 照世界規則（30，超過算敗）。

- ``general``：荒原一般遭遇。依序輪流挑營地與村落（每個地點照遭遇表抽陣容、照地點的戰鬥地圖；
  村落是守點戰），主角等級＝地點建議等級；``--enemy-plus 0,2`` 另量敵人高 2 級（07 7.8；走世界事件
  失敗的建議等級加成同一條路，主角等級不變）。
- ``boss``：熔心坑灰燼之心（9 級、Boss 地圖 ``molten_heart_pit``），護甲不調整（沒有旗標與線頭）；
  ``--fire`` 另量灰燼瑪菈（``build_fire``）當主角。

候選內容（``--variant``）：複製一份 ``content/`` 到暫存資料夾、套 :data:`VARIANTS` 的字串替換
再載入，所以引擎與世界的程式完全照正式路徑；``+`` 可以串起多個候選（例 ``dice_up+fire50``）。

用法::

    uv run python scripts/archive/ashen_waste_sim.py [--runs 40] [--only general|boss]
    uv run python scripts/archive/ashen_waste_sim.py --only boss --fire --variant now,dice_up,dice_up+fire50
    uv run python scripts/archive/ashen_waste_sim.py --only general --enemy-plus 0,2

只輸出摘要表（勝率、平均輪數、敗場；Boss 另列到第 2／3 階段的比例、敗場剩餘 HP），最後一張 Markdown
總表；數值建議寫進報告由 PM 決定（CLAUDE.md 第 11 條）。
"""

from __future__ import annotations

import argparse
import dataclasses
import shutil
import sys
import tempfile
from collections import Counter
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import BossPhaseChanged
from trpg.engine.runner import run_battle
from trpg.shared.types import Team
from trpg.world.battle import grow_enemy, prepare_battle
from trpg.world.common import max_hp
from trpg.world.party import default_party
from trpg.world.state import CharacterState, EncounterResult
from trpg.world.step import new_character

REGION = "ashen_waste"
BOSS = "ashen_heart"
BOSS_LOCATION = "molten_heart_pit"
NOON = 1_793_592_000
BUILDS = (
    "build_striker",
    "build_fire",
    "build_storm",
    "build_ranged",
    "build_tank",
    "build_guardian",
    "build_healer",
    "build_trapper",
)
"""輸出、守護、輔助、控制各 2 種（同 5F-3 的 season_boss_sim）。"""
PARTIES = {
    "build_tank": ("merc_chiyan", "merc_huichun"),
    "build_guardian": ("merc_chiyan", "merc_huichun"),
    "build_healer": ("merc_chiyan", "merc_chuanyun"),
}
GENERAL_LOCATIONS = (
    "scorched_outskirts",
    "deadwood_forest",
    "red_sand_village",
    "ash_mire",
    "gang_convoy_road",
    "ash_well_village",
    "tar_pits",
    "lava_cave",
    "iron_forge_village",
    "ruined_fortress",
)
"""一般遭遇輪流挑的地點（營地、村落與遺跡；不含精英巢穴、隱藏地點與 Boss）。"""

Edit = tuple[str, str, str]
"""(content 下的相對路徑、舊字串、新字串)；舊字串在檔案裡必須剛好出現一次。"""
VARIANTS: dict[str, tuple[Edit, ...]] = {
    "now": (),
    # --- 5F-5b 灰燼之心：HP 160 不動、只調傷害 ---
    "int16": (("units/ashen_heart.yaml", "int: 14,", "int: 16,"),),
    "dice_up": (
        ("skills/skill_lava_spout.yaml", "dice: 1d6, element: fire}", "dice: 1d10, element: fire}"),
        ("skills/skill_heart_inhale.yaml", "dice: 1d10,", "dice: 2d8,"),
        ("skills/skill_heart_exhale.yaml", "dice: 1d6,", "dice: 1d10,"),
        ("skills/skill_heart_meltdown.yaml", "dice: 3d8,", "dice: 3d10,"),
    ),
    "dice_up2": (
        ("skills/skill_lava_spout.yaml", "dice: 1d6, element: fire}", "dice: 2d8, element: fire}"),
        ("skills/skill_heart_inhale.yaml", "dice: 1d10,", "dice: 2d10,"),
        ("skills/skill_heart_exhale.yaml", "dice: 1d6,", "dice: 2d6,"),
        ("skills/skill_heart_exhale.yaml", "duration: 1}", "duration: 2}"),
        ("skills/skill_heart_meltdown.yaml", "dice: 3d8,", "dice: 4d10,"),
    ),
    "fire50": (("units/ashen_heart.yaml", "fire: -750,", "fire: -500,"),),
    # --- 5F-5b 荒原一般遭遇：熔核（熔岩獸群的開場狀態，只有荒原的範本有）的攻擊傷害倍率 ---
    # 現值 2250（5F-5b 定案）；burst1000＝5F-5a（沒有倍率）
    **{
        f"burst{p}": tuple(
            (
                "statuses.yaml",
                f"duration: 2}}\n    damage_dealt_permille: 2250\n{tail}",
                f"duration: 2}}\n    damage_dealt_permille: {p}\n{tail}",
            )
            for tail in ("  # 5F-5b：灰燼之心戰", "  # 5F-5a：灰燼之心第 1 階段")
        )
        for p in (1000, 1500, 2000, 2250, 2500)
    },
    # --- 5F-5b 灰燼之心戰的殼縫餘燼蜥（殼縫熔核）的攻擊傷害倍率；現值 1500 ---
    **{
        f"court{p}": (
            (
                "statuses.yaml",
                "    damage_dealt_permille: 1500\n  # 5F-5a：冰變體",
                f"    damage_dealt_permille: {p}\n  # 5F-5a：冰變體",
            ),
        )
        for p in (1000, 1250, 1500, 1750, 2250)
    },
    # --- 5F-5b 灰燼之心自己的攻擊傷害倍率（開場狀態，整場不移除）：技能在 9 級照階級重配骰數，
    # 改技能的骰不會生效（dice_up／dice_up2 與現值完全相同），所以用狀態倍率 ---
    **{
        f"heart{p}": (
            (
                "statuses.yaml",
                "  - id: molten_shell\n",
                "  - id: ashen_heart_heat\n    polarity: neutral\n    name_zh: 熔心之熱\n"
                "    description_zh: 候選\n    expires: never\n    stacking: refresh\n"
                f"    damage_dealt_permille: {p}\n  - id: molten_shell\n",
            ),
            (
                "units/ashen_heart.yaml",
                "  - {status: molten_shell}\n",
                "  - {status: molten_shell}\n  - {status: ashen_heart_heat}\n",
            ),
        )
        for p in (250, 500, 750, 1500)
    },
}
"""候選內容（``--variant``）。"""


@dataclass(frozen=True)
class Outcome:
    label: str
    build: str
    won: bool
    rounds: int
    boss_hp_permille: int = 0
    phases: int = 0


Job = tuple[str, str, str, int, int | None, str | None, int]
"""(標籤、build、地點、種子、Boss HP 候選、內容資料夾、敵人高幾級)。"""


def variant_root(name: str, base: Path) -> Path | None:
    """候選 ``name`` 的內容資料夾（暫存複本）；``now``＝原內容，回傳 ``None``。"""
    edits = [e for part in name.split("+") for e in VARIANTS[part]]
    if not edits:
        return None
    root = Path(tempfile.mkdtemp(prefix="ashen_")) / "content"
    shutil.copytree(base, root)
    for rel, old, new in edits:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise SystemExit(f"候選 {name}：{rel} 找不到唯一的「{old}」")
        path.write_text(text.replace(old, new), encoding="utf-8")
    return root


def make_char(
    library: ContentLibrary, build_id: str, location: str, seed: int, enemy_plus: int = 0
) -> CharacterState:
    """地點建議等級的主角（照敵我同一套成長）＋預設傭兵，身上有那個地點的遭遇；敵人高
    ``enemy_plus`` 級。"""
    place = library.world_maps[REGION].location_by_id()[location]
    assert place.level_min is not None
    level = place.level_min
    base = next(b.hero for b in library.builds.builds if b.id == build_id)
    grown, skills = grow_enemy(library, base, level)
    hero = grown.model_copy(update={"max_hp": base.max_hp, "level": 1})  # 等級 HP 由開戰時加
    char = new_character(library, "sim", hero, region=REGION)
    table = library.world_encounters[REGION]
    objective = table.location_by_id()[location].objective
    encounter = EncounterResult(
        region=REGION,
        location=location,
        level=level,
        battle_map=place.battle_maps[seed % len(place.battle_maps)] if place.battle_maps else None,
        battle_seed=seed,
        weather="clear",
        day_phase="day",
        at=NOON,
        objective=objective,
        level_bonus=enemy_plus,
    )
    char = char.model_copy(
        update={
            "level": level,
            "location": location,
            "mercenaries": PARTIES.get(build_id, default_party(library)),
            "generated_skills": skills,
            "pending_encounter": encounter,
        }
    )

    return char.model_copy(update={"hp": max_hp(library, char)})


_LIBS: dict[tuple[str | None, int | None], ContentLibrary] = {}


def _library(boss_hp: int | None, root: str | None) -> ContentLibrary:
    """每個工作程序快取一份（候選內容資料夾、Boss HP）的內容庫。"""
    key = (root, boss_hp)
    if key not in _LIBS:
        library = load_library(None if root is None else Path(root))
        if boss_hp is not None:
            units = dict(library.units)
            units[BOSS] = units[BOSS].model_copy(update={"max_hp": boss_hp})
            library = dataclasses.replace(library, units=units)
        _LIBS[key] = library
    return _LIBS[key]


def _run(args: Job) -> Outcome:
    label, build_id, location, seed, boss_hp, root, enemy_plus = args
    library = _library(boss_hp, root)
    prepared = prepare_battle(library, make_char(library, build_id, location, seed, enemy_plus))
    run = run_battle(prepared.setup, prepared.seed, UtilityAI(library.ai_profiles))
    won = run.state.winner is Team.ALLY
    boss = next((u for u in run.state.units.values() if u.template_id == BOSS), None)
    if boss is None:
        return Outcome(label=label, build=build_id, won=won, rounds=run.state.round)
    changes = [e for e in run.events if isinstance(e, BossPhaseChanged) and e.unit_id == boss.id]
    return Outcome(
        label=label,
        build=build_id,
        won=won,
        rounds=run.state.round,
        boss_hp_permille=boss.hp * 1000 // max(1, boss.max_hp),
        phases=len(changes),
    )


def summarize(title: str, outcomes: Sequence[Outcome], *, boss: bool) -> str:
    n = len(outcomes)
    wins = sum(o.won for o in outcomes)
    rounds = sum(o.rounds for o in outcomes) / n
    lines = [
        f"## {title}（{n} 場）",
        f"勝率 {wins * 100 // n}%（{wins}/{n}）、平均 {rounds:.1f} 輪",
    ]
    if boss:
        left = [o.boss_hp_permille for o in outcomes if not o.won]
        left_avg = f"{sum(left) / len(left) / 10:.0f}%" if left else "—"
        p2 = sum(o.phases >= 1 for o in outcomes) * 100 // n
        p3 = sum(o.phases >= 2 for o in outcomes) * 100 // n  # noqa: PLR2004
        lines.append(f"到第 2 階段 {p2}%、到第 3 階段 {p3}%、敗場 Boss 剩餘 HP 平均 {left_avg}")
    by_build: Counter[str] = Counter()
    played: Counter[str] = Counter()
    for o in outcomes:
        played[o.build] += 1
        by_build[o.build] += o.won
    lines.append(
        "build 勝場："
        + "、".join(f"{b.removeprefix('build_')} {by_build[b]}/{played[b]}" for b in sorted(played))
    )
    if not boss:
        by_place: Counter[str] = Counter()
        place_n: Counter[str] = Counter()
        for o in outcomes:
            place_n[o.label] += 1
            by_place[o.label] += o.won
        lines.append(
            "地點勝場：" + "、".join(f"{p} {by_place[p]}/{place_n[p]}" for p in sorted(place_n))
        )
    return "\n".join(lines)


def table_row(kind: str, variant: str, who: str, outcomes: Sequence[Outcome]) -> str:
    """總表的一列：勝率、平均輪數、勝場平均輪數。"""
    n = len(outcomes)
    wins = sum(o.won for o in outcomes)
    won_rounds = [o.rounds for o in outcomes if o.won]
    avg_won = f"{sum(won_rounds) / len(won_rounds):.1f}" if won_rounds else "—"
    avg = sum(o.rounds for o in outcomes) / n
    return (
        f"| {kind} | {variant} | {who} | {wins * 100 // n}%（{wins}/{n}） | {avg:.1f} | {avg_won} |"
    )


def build_jobs(
    args: argparse.Namespace, roots: dict[str, Path | None]
) -> dict[tuple[str, str, str], list[Job]]:
    """(場景、候選、隊伍) → 這組要跑的場次。"""
    jobs: dict[tuple[str, str, str], list[Job]] = {}
    for name, root in roots.items():
        where = None if root is None else str(root)
        if args.only in (None, "general"):
            for plus in (int(v) for v in args.enemy_plus.split(",")):
                jobs["一般遭遇", name, f"敵人 +{plus} 級"] = [
                    (loc, BUILDS[i % len(BUILDS)], loc, 1000 + i, None, where, plus)
                    for i in range(args.runs)
                    for loc in (GENERAL_LOCATIONS[i % len(GENERAL_LOCATIONS)],)
                ]
        if args.only in (None, "boss"):
            given: list[int | None] = [int(v) for v in args.boss_hp.split(",") if v]
            for hp in given or [None]:
                label = name if hp is None else f"{name}，HP {hp}"
                jobs["灰燼之心", label, "8 種 build"] = [
                    (BOSS_LOCATION, BUILDS[i % len(BUILDS)], BOSS_LOCATION, 2000 + i, hp, where, 0)
                    for i in range(args.runs)
                ]
                if args.fire:
                    jobs["灰燼之心", label, "灰燼瑪菈主角"] = [
                        (BOSS_LOCATION, "build_fire", BOSS_LOCATION, 3000 + i, hp, where, 0)
                        for i in range(args.runs)
                    ]
    return jobs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--runs", type=int, default=40)
    parser.add_argument("--only", choices=("general", "boss"), default=None)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--boss-hp", default="", help="候選的灰燼之心 HP（逗號分隔；空＝現值）")
    parser.add_argument("--variant", default="now", help="候選內容（逗號分隔；見 VARIANTS）")
    parser.add_argument(
        "--fire", action="store_true", help="灰燼之心另量灰燼瑪菈（build_fire）當主角"
    )
    parser.add_argument("--enemy-plus", default="0", help="一般遭遇敵人高幾級（逗號分隔，例 0,2）")
    args = parser.parse_args(argv)
    base = Path(__file__).resolve().parents[2] / "content"
    roots = {name: variant_root(name, base) for name in args.variant.split(",")}
    table = ["| 場景 | 候選 | 隊伍 | 勝率 | 平均輪數 | 勝場平均輪數 |", "|---|---|---|---|---|---|"]
    try:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for (kind, variant, who), batch in build_jobs(args, roots).items():
                outcomes = list(pool.map(_run, batch))
                print(summarize(f"{kind}（{variant}；{who}）", outcomes, boss=kind == "灰燼之心"))
                print()
                table.append(table_row(kind, variant, who, outcomes))
    finally:
        for root in roots.values():
            if root is not None:
                shutil.rmtree(root.parent, ignore_errors=True)
    print("\n".join(table))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
