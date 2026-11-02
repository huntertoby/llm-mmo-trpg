# ruff: noqa: E501, PLR2004
"""BAL-15a：資源（法力）批只量＋建議；覆寫只在記憶體內的 library 副本，不改 content。

用法（輸出 Markdown；``--out`` 另存檔）::

    # 1／2／3：build × 情境（一般戰、Boss 戰、連戰 3 場不回營火）× 覆寫組合
    uv run python scripts/bal15a_resources.py measure --variants base,mcap=1800 --builds all \\
        --normal-seeds 6 --boss-seeds 30 --chain-seeds 24 --jobs 4 --out .scratch_15a/m.json
    # 彙整成 Markdown
    uv run python scripts/bal15a_resources.py report --inp .scratch_15a/m.json
    # 靜態表：各 build 法力／耐力上限、技能費用、費用換算
    uv run python scripts/bal15a_resources.py static

覆寫語法（``+`` 串接，依序套用；``base`` ＝ 不改）：

- ``mcap=<‰>``：法力上限倍率（絕對值，content 現況 1400）；``mcost=<‰>``：我方法力費用倍率（絕對值，現況 800）；
- ``mpp=<n>``／``spp=<n>``：法力／耐力上限的每點屬性加成（現況 2）；``sreg=<n>``：英雄耐力回復（現況 5）；
- ``scost=<‰>``：所有技能的耐力費用 ×‰（四捨五入，至少 1）＝ 改法力換耐力的換算比（2:1 → 3:1 ＝ 1500）；
- ``classbase``：所有 build 英雄的法力／耐力基礎改成一輪主角依武器大類的值（``roguelite.yaml`` 的 ``start.heroes``）；
- ``b14=<enemy|companion|summon|all，逗號>``：該類單位改用主角的上限公式（範本 ``scaled_resources`` ＝ 真，
  上限含屬性加成與法力 ×mcap，耐力每回合 +sreg）；
- ``b14cap=<同上>``：只改上限（公式算出的固定值，沒有耐力回復），用來分開「上限」與「回復」兩個效果。

情境：``normal``（每張示範地圖的預設陣容、英雄＋標準隊友）、``boss``（bandit_lair 預設陣容）、
``chain``（3 張地圖連打，英雄 HP 與法力帶入下一場、耐力每場回滿，輸了就中斷）。
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.events import SkillTriggered, SkillUsed, TurnStarted
from trpg.engine.results import ResolveResult
from trpg.engine.runner import run_battle
from trpg.engine.setup import BattleSetup, build_setup
from trpg.engine.skills.targeting import resource_problem
from trpg.engine.state import BattleState, UnitState
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team
from trpg.sim.batch import DEFAULT_MAX_ROUNDS, UtilityPolicyFactory
from trpg.sim.difficulty import enemy_roster
from trpg.sim.matrix import library_with_builds
from trpg.sim.parallel import run_tasks

BOSS_MAP = "bandit_lair"
CASTERS_EXTRA = ("build_summon_swarm", "build_summon_elite")
_MANA = "法力不足"
_STAMINA = "耐力不足"


# --------------------------------------------------------------------------- 覆寫


def _pool(res: Any, kind: str, per_point: int) -> Any:
    pool = res.mana if kind == "mana" else res.stamina
    return pool.model_copy(update={"per_point": per_point})


def _scaled_templates(
    library: ContentLibrary, groups: set[str], *, cap_only: bool
) -> tuple[dict[str, Any], Any]:
    """依 ``groups`` 改單位範本與召喚物範本；回傳（新 units，新 summons 表）。"""
    core = library.ruleset.core
    units = dict(library.units)
    ids: set[str] = set()
    if groups & {"enemy", "all"}:
        ids |= set(enemy_roster(library))
    if groups & {"companion", "all"}:
        ids |= set(library.builds.companions)

    def convert(t: Any) -> Any:
        if cap_only:
            mana = core.resources.max_for("mana", t.max_mana, t.attributes)
            stam = core.resources.max_for("stamina", core.template_stamina(t), t.attributes)
            return t.model_copy(update={"max_mana": mana, "stamina": stam})
        return t.model_copy(update={"scaled_resources": True})

    for tid in sorted(ids):
        units[tid] = convert(units[tid])
    summons = library.ruleset.summons
    if groups & {"summon", "all"}:
        summons = summons.model_copy(
            update={
                "summons": tuple(
                    s.model_copy(update={"template": convert(s.template)}) for s in summons.summons
                )
            }
        )
    return units, summons


def _scale_stamina_costs(skills: dict[str, Any], permille: int) -> None:
    for sid, sk in list(skills.items()):
        if sk.cost.stamina:
            new_v = max(1, (sk.cost.stamina * permille + 500) // 1000)
            skills[sid] = sk.model_copy(
                update={"cost": sk.cost.model_copy(update={"stamina": new_v})}
            )


def _class_bases(library: ContentLibrary, units: dict[str, Any]) -> None:
    for b in library.builds.builds:
        h = library.roguelite.start.heroes[library.weapons[b.hero.weapon].weapon_class]
        units[b.id] = units[b.id].model_copy(update={"max_mana": h.max_mana, "stamina": h.stamina})


def apply_variant(library: ContentLibrary, spec: str) -> ContentLibrary:
    """套用一組覆寫（``+`` 串接）；``base`` ＝ 原物件。"""
    if spec == "base":
        return library
    ruleset = library.ruleset
    core = ruleset.core
    res = core.resources
    skills = dict(library.skills)
    units = dict(library.units)
    core_up: dict[str, Any] = {}
    res_up: dict[str, Any] = {}
    skills_changed = False
    for part in spec.split("+"):
        key, _, val = part.partition("=")
        if key == "mcap":
            res_up["mana_cap_permille"] = int(val)
        elif key == "mcost":
            core_up["ally_mana_cost_permille"] = int(val)
        elif key in ("mpp", "spp"):
            kind = "mana" if key == "mpp" else "stamina"
            res_up[kind] = _pool(res, kind, int(val))
        elif key == "sreg":
            res_up["stamina_regen"] = int(val)
        elif key == "scost":
            _scale_stamina_costs(skills, int(val))
            skills_changed = True
        elif key == "classbase":
            _class_bases(library, units)
        elif key not in ("b14", "b14cap"):  # b14 最後處理（要用到上面改完的公式）
            raise ValueError(f"未知覆寫：{part}")
    new_res = res.model_copy(update=res_up) if res_up else res
    new_core = core.model_copy(update={**core_up, "resources": new_res})
    new_ruleset = ruleset.model_copy(update={"core": new_core})
    if skills_changed:
        table = ruleset.skills.model_copy(
            update={"skills": tuple(skills[s.id] for s in ruleset.skills.skills)}
        )
        new_ruleset = new_ruleset.model_copy(update={"skills": table})
    new_ruleset.model_post_init(None)
    lib = dataclasses.replace(library, skills=skills, ruleset=new_ruleset, units=units)
    for part in spec.split("+"):
        key, _, val = part.partition("=")
        if key in ("b14", "b14cap"):
            groups = set(val.split(","))
            units, summons = _scaled_templates(lib, groups, cap_only=key == "b14cap")
            rs = lib.ruleset.model_copy(update={"summons": summons})
            rs.model_post_init(None)
            lib = dataclasses.replace(lib, units=units, ruleset=rs)
    return lib


# --------------------------------------------------------------------------- 量測


@dataclass(slots=True)
class Sample:
    variant: str
    build: str
    kind: str  # normal／boss／chain1／chain2／chain3／chain（整條）
    map_id: str
    seed: int
    ok: bool = True
    won: bool = False
    rounds: int = 0
    turns: int = 0
    mana_short: int = 0
    mana_dry: int = 0
    stam_short: int = 0
    mana_spent: int = 0
    stam_spent: int = 0
    mana_start: int = 0
    mana_max: int = 0
    mana_left: int = 0
    stam_max: int = 0
    hp_left_pm: int = 0
    enemy_skill_uses: int = 0


def _hero(state: BattleState, build: str) -> UnitState | None:
    return next(
        (u for u in state.units_sorted() if u.team is Team.ALLY and u.template_id == build), None
    )


class Tracker:
    def __init__(self, build: str, sample: Sample) -> None:
        self.build = build
        self.s = sample
        self.seen: set[int] = set()
        self.prev_mana: int | None = None
        self.prev_stam: int | None = None

    def __call__(self, step: object, result: ResolveResult) -> None:
        state = result.state
        hero = _hero(state, self.build)
        if hero is None:
            return
        if self.prev_mana is not None and self.prev_stam is not None:
            self.s.mana_spent += max(0, self.prev_mana - hero.mana)
            self.s.stam_spent += max(0, self.prev_stam - hero.stamina)
        self.prev_mana, self.prev_stam = hero.mana, hero.stamina
        for event in result.events:
            if isinstance(event, SkillUsed | SkillTriggered):
                unit = state.units.get(event.unit_id)
                if unit is not None and unit.team is Team.ENEMY and not unit.is_summon:
                    self.s.enemy_skill_uses += 1
            if isinstance(event, TurnStarted) and event.unit_id == hero.id:
                if state.round in self.seen:
                    continue
                self.seen.add(state.round)
                self._turn(state, hero)

    def _turn(self, state: BattleState, hero: UnitState) -> None:
        mana_any = stam_any = False
        mana_skills = mana_blocked = 0
        for skill_id in hero.skills:
            skill = state.ruleset.skill_def(skill_id)
            if skill.kind != "active":
                continue
            problem = resource_problem(state, hero, skill) or ""
            m = problem.startswith(_MANA)
            mana_any = mana_any or m
            stam_any = stam_any or problem.startswith(_STAMINA)
            if skill.cost.mana > 0:
                mana_skills += 1
                mana_blocked += m
        self.s.turns += 1
        self.s.mana_short += mana_any
        self.s.stam_short += stam_any
        self.s.mana_dry += mana_skills > 0 and mana_blocked == mana_skills


def _fight(
    setup: BattleSetup,
    build: str,
    *,
    variant: str,
    kind: str,
    map_id: str,
    seed: int,
    factory: UtilityPolicyFactory,
) -> tuple[Sample, UnitState | None]:
    s = Sample(variant, build, kind, map_id, seed)
    tracker = Tracker(build, s)
    try:
        run = run_battle(setup, seed, factory(), on_step=tracker)
    except TrpgError:
        s.ok = False
        return s, None
    hero = _hero(run.state, build)
    s.won = run.state.winner is Team.ALLY
    s.rounds = run.state.round
    if hero is not None:
        s.mana_left, s.mana_max, s.stam_max = hero.mana, hero.max_mana, hero.max_stamina
        s.hp_left_pm = hero.hp * 1000 // max(1, hero.max_hp)
    return s, hero


_CACHE: dict[str, Any] = {}


def _lib(variant: str) -> ContentLibrary:
    key = f"lib/{variant}"
    if key not in _CACHE:
        base = _CACHE.get("base")
        if base is None:
            base = _CACHE["base"] = library_with_builds(load_library())
        _CACHE[key] = apply_variant(base, variant)
    lib: ContentLibrary = _CACHE[key]
    return lib


def _setup(variant: str, build: str, map_id: str, enemies: tuple[str, ...] | None) -> BattleSetup:
    key = f"setup/{variant}/{build}/{map_id}"
    if key not in _CACHE:
        lib = _lib(variant)
        if enemies is None:
            enc = lib.map(map_id).encounter
            assert enc is not None
            enemies = tuple(enc.enemies)
        _CACHE[key] = build_setup(
            lib,
            map_id,
            (build, *lib.builds.companions),
            enemies,
            max_rounds=DEFAULT_MAX_ROUNDS,
        )
    setup: BattleSetup = _CACHE[key]
    return setup


def _carry(setup: BattleSetup, hero: UnitState) -> BattleSetup:
    """把英雄的 HP、法力帶入下一場（耐力回滿）。"""
    units = list(setup.units)
    for i, spawn in enumerate(units):
        if spawn.team is Team.ALLY and spawn.template.id == hero.template_id:
            units[i] = spawn.model_copy(update={"hp": max(1, hero.hp), "mana": max(0, hero.mana)})
            break
    return setup.model_copy(update={"units": tuple(units)})


type Task = tuple[str, str, str, int, tuple[str, ...]]
"""（variant, build, kind, seed, chain 用的地圖列表／normal 用的單一地圖）。"""


def work(maps: tuple[str, ...], task: Task) -> list[Sample]:
    variant, build, kind, seed, chain_maps = task
    lib = _lib(variant)
    factory = UtilityPolicyFactory(lib.ai_profiles)
    battle_seed = 1000 + seed
    if kind in ("normal", "boss"):
        map_id = BOSS_MAP if kind == "boss" else chain_maps[0]
        s, _ = _fight(
            _setup(variant, build, map_id, None),
            build,
            variant=variant,
            kind=kind,
            map_id=map_id,
            seed=battle_seed,
            factory=factory,
        )
        return [s]
    out: list[Sample] = []
    carried: UnitState | None = None
    chain = Sample(variant, build, "chain", "+".join(chain_maps), seed)
    for i, map_id in enumerate(chain_maps):
        setup = _setup(variant, build, map_id, None)
        if carried is not None:
            setup = _carry(setup, carried)
        s, hero = _fight(
            setup,
            build,
            variant=variant,
            kind=f"chain{i + 1}",
            map_id=map_id,
            seed=battle_seed + i,
            factory=factory,
        )
        s.mana_start = carried.mana if carried is not None else s.mana_max
        out.append(s)
        if not s.ok or not s.won or hero is None:
            chain.won = False
            chain.ok = s.ok
            chain.rounds = i  # 打贏的場數
            break
        carried = hero
        chain.rounds = i + 1
        chain.won = i == len(chain_maps) - 1
    out.append(chain)
    return out


def all_builds(library: ContentLibrary) -> list[str]:
    return [b.id for b in library.builds.builds if not b.id.startswith("build_form")]


def measure(args: argparse.Namespace) -> int:
    base = library_with_builds(load_library())
    builds = all_builds(base) if args.builds == "all" else args.builds.split(",")
    if args.builds == "named":
        builds = [b for b in all_builds(base) if "blank" not in b and "tester" not in b]
    variants = args.variants.split(",")
    maps = tuple(default_sim_maps(base))
    tasks: list[Task] = []
    for v in variants:
        for b in builds:
            for m in maps:
                tasks += [(v, b, "normal", sd, (m,)) for sd in range(args.normal_seeds)]
            tasks += [(v, b, "boss", sd, ()) for sd in range(args.boss_seeds)]
            for sd in range(args.chain_seeds):
                cm = tuple(maps[(sd * 3 + i * 2 + sd // len(maps)) % len(maps)] for i in range(3))
                if len(set(cm)) < 3:
                    cm = tuple(maps[(sd + i) % len(maps)] for i in range(3))
                tasks.append((v, b, "chain", sd, cm))
    print(
        f"任務 {len(tasks)}；地圖 {len(maps)}；build {len(builds)}；覆寫 {variants}",
        file=sys.stderr,
        flush=True,
    )
    started = time.perf_counter()
    results = run_tasks(work, maps, tasks, jobs=args.jobs)
    flat = [dataclasses.asdict(s) for batch in results for s in batch]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(flat, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"完成 {time.perf_counter() - started:.1f} 秒；樣本 {len(flat)}", file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- 報表


def _pct(n: float, d: float) -> str:
    return "—" if d <= 0 else f"{100 * n / d:.1f}%"


def _agg(rows: list[dict[str, Any]]) -> dict[str, float]:
    ok = [r for r in rows if r["ok"]]
    turns = sum(r["turns"] for r in ok)
    return {
        "n": len(ok),
        "win": sum(r["won"] for r in ok),
        "rounds": sum(r["rounds"] for r in ok),
        "turns": turns,
        "mshort": sum(r["mana_short"] for r in ok),
        "mdry": sum(r["mana_dry"] for r in ok),
        "sshort": sum(r["stam_short"] for r in ok),
        "mspent": sum(r["mana_spent"] for r in ok),
        "sspent": sum(r["stam_spent"] for r in ok),
        "mmax": sum(r["mana_max"] for r in ok),
        "smax": sum(r["stam_max"] for r in ok),
        "mleft": sum(r["mana_left"] for r in ok),
        "eskill": sum(r["enemy_skill_uses"] for r in ok),
    }


def _cell(a: dict[str, float]) -> str:
    if not a["n"]:
        return "—"
    return f"短缺{_pct(a['mshort'], a['turns'])}／勝{_pct(a['win'], a['n'])}／{a['rounds'] / a['n']:.1f}輪"


def _beyond_chain(r: dict[str, Any], limit: int) -> bool:
    kind = r["kind"]
    if kind == "chain":
        return bool(r["seed"] >= limit)
    if kind.startswith("chain"):
        return bool(r["seed"] - 1000 - (int(kind[5:]) - 1) >= limit)
    return False


def report(args: argparse.Namespace) -> int:
    rows = []
    for inp in args.inp.split(","):
        rows += json.loads(Path(inp).read_text(encoding="utf-8"))
    if args.builds:
        keep = set(args.builds.split(","))
        rows = [r for r in rows if r["build"] in keep]
    if args.chain_max:  # 只留前 N 條連戰（種子 < N），讓不同規模的檔案可比
        rows = [r for r in rows if not _beyond_chain(r, args.chain_max)]
    by: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by[(r["variant"], r["build"], r["kind"])].append(r)
    variants = list(dict.fromkeys(r["variant"] for r in rows))
    builds = list(dict.fromkeys(r["build"] for r in rows))
    out: list[str] = []
    for v in variants:
        out += [f"## 覆寫：{v}", ""]
        out += [
            "| build | 一般戰（法力短缺回合／勝率／輪數） | Boss 戰 | 連戰第1場 | 連戰第2場 | 連戰第3場 | 連戰 3 連勝 | 耐力短缺（一般／Boss） | 法力花費÷上限（Boss） |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for b in builds:
            n, bo = _agg(by[(v, b, "normal")]), _agg(by[(v, b, "boss")])
            cs = [_agg(by[(v, b, f"chain{i}")]) for i in (1, 2, 3)]
            ch = by[(v, b, "chain")]
            chok = [r for r in ch if r["ok"]]
            win3 = _pct(sum(r["won"] for r in chok), len(chok))
            ratio = _pct(bo["mspent"], bo["mmax"]) if bo["mmax"] else "—"
            out.append(
                f"| {b} | {_cell(n)} | {_cell(bo)} | {_cell(cs[0])} | {_cell(cs[1])} | {_cell(cs[2])} | {win3} "
                f"| {_pct(n['sshort'], n['turns'])}／{_pct(bo['sshort'], bo['turns'])} | {ratio} |"
            )
        out.append("")
        allk = {
            k: [r for b in builds for r in by[(v, b, k)]]
            for k in ("normal", "boss", "chain1", "chain2", "chain3")
        }
        out += ["全 build 合計：", ""]
        for k, rs in allk.items():
            a = _agg(rs)
            if a["n"]:
                out.append(
                    f"- {k}：n={a['n']:.0f}｜法力短缺 {_pct(a['mshort'], a['turns'])}｜法力全空 {_pct(a['mdry'], a['turns'])}｜耐力短缺 {_pct(a['sshort'], a['turns'])}｜勝率 {_pct(a['win'], a['n'])}｜輪數 {a['rounds'] / a['n']:.2f}｜敵方技能次數/場 {a['eskill'] / a['n']:.2f}"
                )
        out.append("")
    Path(args.out).write_text(
        "\n".join(out), encoding="utf-8", newline="\n"
    ) if args.out else print("\n".join(out))
    return 0


# --------------------------------------------------------------------------- 靜態


def static(args: argparse.Namespace) -> int:
    lib = library_with_builds(load_library())
    core = lib.ruleset.core
    res = core.resources
    lines = [
        "## 各 build 資源上限與技能費用（現況）",
        "",
        f"法力 ×{res.mana_cap_permille / 1000}、我方費用 ×{core.ally_mana_cost_permille / 1000}、耐力回復 {res.stamina_regen}／回合",
        "",
        "| build | 武器 | 法力基礎 | 耐力基礎 | 法力屬性 | 耐力屬性 | 法力上限 | 耐力上限 | 主動技 | 法力技（打折後費用） | 耐力技（費用） | 法力技可連放次數 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for b in lib.builds.builds:
        if b.id.startswith("build_form"):
            continue
        h = b.hero
        mcap = core.template_max_resource("mana", h)
        scap = core.template_max_resource("stamina", h)
        act = [lib.skills[s] for s in h.skills if lib.skills[s].kind == "active"]
        mc = [
            (
                s.id.removeprefix("skill_"),
                (s.cost.mana * core.ally_mana_cost_permille + 500) // 1000,
            )
            for s in act
            if s.cost.mana
        ]
        sc = [(s.id.removeprefix("skill_"), s.cost.stamina) for s in act if s.cost.stamina]
        avg = sum(c for _, c in mc) / len(mc) if mc else 0
        casts = f"{mcap / avg:.1f}（均費 {avg:.1f}）" if mc else "—"
        best = max((h.attributes[a] for a in res.mana.attrs), default=10)
        sbest = max((h.attributes[a] for a in res.stamina.attrs), default=10)
        lines.append(
            f"| {b.id} | {h.weapon} | {h.max_mana} | {core.template_stamina(h)} | {best} | {sbest} | {mcap} | {scap} "
            f"| {len(act)} | {', '.join(f'{n}:{c}' for n, c in mc) or '—'} | {', '.join(f'{n}:{c}' for n, c in sc) or '—'} | {casts} |"
        )
    text = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--variants", default="base")
    m.add_argument("--builds", default="named", help="all／named（不含白板與 tester）／逗號分隔")
    m.add_argument("--normal-seeds", type=int, default=6)
    m.add_argument("--boss-seeds", type=int, default=30)
    m.add_argument("--chain-seeds", type=int, default=24)
    m.add_argument("--jobs", type=int, default=1)
    m.add_argument("--out", required=True)
    m.set_defaults(fn=measure)
    r = sub.add_parser("report")
    r.add_argument("--inp", required=True, help="逗號分隔多個 json，依序合併")
    r.add_argument("--builds", default="", help="只列這些 build（逗號）")
    r.add_argument("--chain-max", type=int, default=0, help="連戰只計前 N 條")
    r.add_argument("--out", default="")
    r.set_defaults(fn=report)
    s = sub.add_parser("static")
    s.add_argument("--out", default="")
    s.set_defaults(fn=static)
    args = p.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
