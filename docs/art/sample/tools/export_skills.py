"""把 content/ 的技能與名稱表匯出成樣張頁用的 skillsData.js（美術樣張用，不是正式程式）。

用法：uv run python docs/art/sample/tools/export_skills.py
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
CONTENT = ROOT / "content"
OUT = Path(__file__).resolve().parents[1] / "skillsData.js"
COST_KEYS = ("source", "on_miss", "self_status", "uses_per_battle", "stacks")
ELEMENTS = ["physical", "fire", "ice", "lightning", "poison", "wind", "earth", "holy", "shadow"]


def load(name: str) -> dict:
    return yaml.safe_load((CONTENT / name).read_text(encoding="utf-8"))


def names(name: str, key: str) -> dict[str, str]:
    return {row["id"]: row.get("name_zh", row["id"]) for row in load(name)[key]}


def elements_of(effects: list[dict]) -> list[str]:
    found: list[str] = []
    for e in effects:
        el = e.get("element")
        if isinstance(el, str) and el not in found:
            found.append(el)
    return found


def effect_row(e: dict) -> dict:
    row = {"type": e["type"]}
    for k in ("status", "surface", "affects"):
        if k in e:
            row[k] = e[k]
    if e.get("condition"):
        row["condition"] = e["condition"].get("type")
    return row


def segment(d: dict) -> dict:
    shape = d.get("shape") or {}
    return {
        "skeleton": d.get("skeleton"),
        "shape": shape.get("type"),
        "range": shape.get("range"),
        "effects": [effect_row(e) for e in d.get("effects") or []],
    }


def skill(d: dict) -> dict:
    effects = list(d.get("effects") or [])
    fu = d.get("followup")
    all_effects = effects + list((fu or {}).get("effects") or [])
    els = elements_of(all_effects)
    if not els:
        els = [t for t in d.get("tags") or [] if t in ELEMENTS][:1]
    cost = d.get("cost") or {}
    out = {
        "id": d["id"],
        "name": d["name_zh"],
        "kind": d["kind"],
        "rarity": d["rarity"],
        "weapon_req": d.get("weapon_req"),
        "elements": els,
        **segment(d),
        "condition": (d.get("condition") or {}).get("type"),
        "cost": {k: cost[k] for k in COST_KEYS if k in cost},
        "activation": d.get("activation"),
        "trigger": (d.get("trigger") or {}).get("event"),
        "reaction": (d.get("reaction") or {}).get("event"),
        "tags": d.get("tags") or [],
    }
    if any(e["type"] == "gamble" for e in all_effects):
        out["cost"]["gamble"] = True
    if fu:
        out["followup"] = {"when": fu.get("when"), "release": fu.get("release"), **segment(fu)}
        f_els = elements_of(list(fu.get("effects") or []))
        out["followup"]["elements"] = f_els or els
    if d.get("modifiers"):
        out["modifiers"] = [
            {"applies_to": m.get("applies_to"), "change": m.get("change")} for m in d["modifiers"]
        ]
    return out


def main() -> None:
    skills = []
    for path in sorted((CONTENT / "skills").glob("*.yaml")):
        skills.append(skill(yaml.safe_load(path.read_text(encoding="utf-8"))))
    names_zh = {
        "primitive": names("skill_primitives.yaml", "primitives"),
        "condition": names("skill_conditions.yaml", "conditions"),
        "trigger": names("skill_triggers.yaml", "triggers"),
        "status": names("statuses.yaml", "statuses"),
        "surface": names("surfaces.yaml", "surfaces"),
        "shape": names("skill_shapes.yaml", "shapes"),
    }
    OUT.write_text(
        "// 由 tools/export_skills.py 從 content/ 匯出（樣張用）\n"
        f"window.SKILLS = {json.dumps(skills, ensure_ascii=False)};\n"
        f"window.NAMES_ZH = {json.dumps(names_zh, ensure_ascii=False)};\n",
        encoding="utf-8",
    )
    print(f"{len(skills)} skills -> {OUT}")


if __name__ == "__main__":
    main()
