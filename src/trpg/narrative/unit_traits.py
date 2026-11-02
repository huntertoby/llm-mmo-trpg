"""單位卡的「特性」欄（Phase 5A-M1b，玩法決定 #82）：列出單位的招牌被動、反應、開場狀態與精英詞綴。

資料來自單位範本（變體與精英詞綴會先解析、套用），文字用內容檔裡的中文名稱與說明，所以和規則同一個
來源；只讀內容，不看戰鬥狀態（戰鬥中才加上的狀態不算特性）。順序：精英詞綴、被動技能、反應、
開場狀態（陣法、分傷的開場狀態另有標題，Phase 5A-M2）。找不到範本（例如測試用的臨時單位）時為空。
"""

from __future__ import annotations

from trpg.content.battle import StatusDef, UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.world_enemies import apply_affix
from trpg.narrative.status_info import formation_rules

__all__ = ["resolve_template", "trait_lines_for", "unit_trait_lines"]


def resolve_template(library: ContentLibrary, template_id: str) -> tuple[UnitTemplate, str] | None:
    """單位範本 ID → (範本, 精英詞綴名)；變體與 ``<範本>_<詞綴>`` 的精英範本會解析，
    認不得為 ``None``。詞綴名沒有詞綴時為空字串。"""
    template = library.units.get(template_id)
    if template is not None:
        return template, ""
    catalog = library.enemy_catalog()
    enemies = library.world_enemies
    if enemies is not None:
        for affix in enemies.affixes:
            suffix = f"_{affix.id}"
            if not template_id.endswith(suffix):
                continue
            try:
                base = catalog.template(template_id[: -len(suffix)])
            except KeyError:
                continue
            return apply_affix(base, affix, catalog.default_rules), affix.id
    try:
        return catalog.template(template_id), ""
    except KeyError:
        return None


def trait_lines_for(
    library: ContentLibrary, template: UnitTemplate, affix_id: str = ""
) -> list[str]:
    """``template``（已套用詞綴）的特性句。"""
    lines: list[str] = []
    enemies = library.world_enemies
    if affix_id and enemies is not None:
        affix = enemies.affix_by_id()[affix_id]
        lines.append(f"精英詞綴「{affix.name_zh.rstrip('的')}」：{affix.description_zh}")
    for skill_id in template.skills:
        skill = library.skills.get(skill_id)
        if skill is not None and skill.kind == "passive":
            lines.append(f"被動「{skill.name_zh}」：{skill.description_zh}")
    defaults = {r.reaction for r in library.ruleset.reactions.default_rules}
    for rule in template.reactions or ():
        if rule.reaction in defaults or rule.mode == "off":
            continue
        skill = library.skills.get(rule.reaction)
        if skill is not None:
            lines.append(f"反應「{skill.name_zh}」：{skill.description_zh}")
            continue
        reaction = library.ruleset.reactions.by_id().get(rule.reaction)
        if reaction is not None:
            lines.append(f"反應「{reaction.name_zh}」：{reaction.description_zh}")
    for opening in template.opening_statuses:
        status = library.ruleset.status_def(opening.status)
        turns = f"，開場 {opening.duration} 回合" if opening.duration is not None else ""
        rules = "".join(f"（{r}）" for r in formation_rules(status))  # 數字由欄位產生（5A-M2）
        label = _opening_label(status)
        lines.append(f"{label}「{status.name_zh}」{turns}：{status.description_zh}{rules}")
    return lines


def _opening_label(status: StatusDef) -> str:
    """開場狀態的標題：陣法範圍加成「陣法」、分傷「分傷」（Phase 5A-M2），其他「開場狀態」。"""
    if status.formation is not None:
        return "陣法"
    if status.share_damage is not None:
        return "分傷"
    return "開場狀態"


def unit_trait_lines(library: ContentLibrary, template_id: str) -> tuple[str, ...]:
    """單位範本 ID 的特性句（見模組說明）；認不得範本時為空。"""
    found = resolve_template(library, template_id)
    if found is None:
        return ()
    template, affix_id = found
    return tuple(trait_lines_for(library, template, affix_id))
