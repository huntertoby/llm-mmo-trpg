"""好感度的重量（Phase 5B-4c；Phase5計畫 21.2；18.7.6「認真玩的人約第 5 天能讓 1～2 個常去的
NPC 到信賴」）。

照一份「認真玩的進度表」（代決 5B4c-1）用內容庫的數值算每位 NPC 到信賴的天數：任務步驟的
``npcs``（``quest_step_delta``）、每天第一次聊天（``daily_talk_delta``）、事件好感度表。進度表的
天數照 18.7：新手鏈第 1～2 天、主線第 1 章約第 2～3 天（劇情技能約第 2 天）、區域鏈中段到結尾
第 3～5 天、導師鏈第 5～6 天；聊天從見到該 NPC 那天起每天一次。隱藏任務與 Boss 不算。

``python -m tests.world.test_affinity_pace`` 印出每位 NPC 的表（報告用）。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary, load_library
from trpg.world.affinity import affinity_rules

REGION = "cloud_ridge"
TRUSTED = "trusted"
LAST_DAY = 10

STEP_DAYS: dict[tuple[str, str], int] = {
    ("starter_ferry", "ferry_bandits"): 1,
    ("starter_ferry", "bamboo_wolves"): 1,
    ("starter_ferry", "terrace_clash"): 2,
    ("main_mist_rift", "missing_townsfolk"): 2,
    ("main_mist_rift", "enter_temple"): 2,
    ("main_mist_rift", "temple_split"): 3,
    ("main_mist_rift", "rift_battle"): 3,
    ("chain_temple_split", "deliver_letter"): 3,
    ("chain_temple_split", "find_traitor"): 4,
    ("chain_temple_split", "night_raid"): 5,
    ("mentor_qingya_trial", "observe_flash"): 5,
    ("mentor_qingya_trial", "learn_from_mist"): 6,
    ("mentor_qingya_trial", "choose_path"): 6,
}
"""（任務, 步驟）→ 完成的那天。"""

EVENT_DAYS: dict[str, int] = {
    "lost_acolyte": 2,  # 迷路的道童（梯田）
    "monks_dispute": 3,  # 兩名修士（山門，主線第 ③ 步）
    "ayue_request": 3,  # 阿岳的請託（獵戶小屋）
    "fox_traveler": 5,  # 狐族旅人（北坡、冬湖）
}
"""事件成功的那天（事件好感度表的 ``success`` 列）。"""

MEET_DAYS: dict[str, int] = {
    "granny_du": 1,
    "shopkeeper_liu": 1,
    "acolyte_xiaolian": 2,
    "daoist_qingya": 2,
    "hunter_ayue": 3,
}
"""從這天起每天聊一次（霧渡鎮第 1 天；山門第 2 天；獵戶小屋第 3 天）。"""


def trust_days(library: ContentLibrary) -> dict[str, tuple[int | None, list[int]]]:
    """每位 NPC：（到信賴的天數或 ``None``, 第 1～``LAST_DAY`` 天結束時的好感度）。"""
    rules = affinity_rules(library)
    quests = library.world_quests.quests[REGION].quest_by_id()
    social = library.world_quests.social[REGION]
    gains: dict[str, dict[int, int]] = {}

    def add(npc: str, day: int, delta: int) -> None:
        gains.setdefault(npc, {}).setdefault(day, 0)
        gains[npc][day] += delta

    for (quest_id, step_id), day in STEP_DAYS.items():
        step = next(s for s in quests[quest_id].steps if s.id == step_id)
        for npc in step.npcs:
            add(npc, day, rules.quest_step_delta)
    for row in social.event_affinity:
        if row.outcome == "success" and row.skeleton in EVENT_DAYS:
            add(row.npc, EVENT_DAYS[row.skeleton], row.delta)
    for npc, first in MEET_DAYS.items():
        for day in range(first, LAST_DAY + 1):
            add(npc, day, rules.daily_talk_delta)
    trusted_min = next(r.min for r in rules.ranks if r.id == TRUSTED)
    out: dict[str, tuple[int | None, list[int]]] = {}
    for npc in sorted(gains):
        value = 0
        curve: list[int] = []
        reached: int | None = None
        for day in range(1, LAST_DAY + 1):
            value = rules.clamp(value + gains[npc].get(day, 0))
            curve.append(value)
            if reached is None and value >= trusted_min:
                reached = day
        out[npc] = (reached, curve)
    return out


def test_one_or_two_npcs_trusted_by_day_5(library: ContentLibrary) -> None:
    days = trust_days(library)
    reached = sorted(d for d, _ in days.values() if d is not None)
    assert reached, days
    assert reached[0] in (4, 5), days  # 第 4～5 天第一位到信賴（玩法 PM 2026-11-03）
    assert 1 <= sum(1 for d in reached if d <= 5) <= 2, days
    assert all(d > 3 for d in reached), days


def test_xiaolian_gains_on_main_steps_2_and_3(library: ContentLibrary) -> None:
    """5B-4d（18.7.6 個別來源）：小蓮＝主線第 ②、③ 步各 +10（代決 5B4d-1：照任務步驟好感度）。"""
    steps = library.world_quests.quests[REGION].quest_by_id()["main_mist_rift"].steps
    with_xiaolian = [i + 1 for i, s in enumerate(steps) if "acolyte_xiaolian" in s.npcs]
    assert with_xiaolian == [2, 3]
    assert affinity_rules(library).quest_step_delta == 10
    _, curve = trust_days(library)["acolyte_xiaolian"]
    assert curve[1] - curve[0] == 10 + 20 + 3  # 第 2 天：主線 ②、迷路的道童（5B-4e：+20）、聊天


def test_xiaolian_event_sources_5b4e(library: ContentLibrary) -> None:
    """5B-4e（18.7.6「5B-4d 代決」）：骨架 2 成功 +20、骨架 6 成功 +10；照進度表（兩個事件都成功）
    第 5 天到信賴（目標第 6 天；報告另列依成功率的平均）。"""
    rows = {
        (r.skeleton, r.outcome): r.delta
        for r in library.world_quests.social[REGION].event_affinity
        if r.npc == "acolyte_xiaolian"
    }
    assert rows[("lost_acolyte", "success")] == 20
    assert rows[("monks_dispute", "success")] == 10
    day, _ = trust_days(library)["acolyte_xiaolian"]
    assert day is not None and day <= 6


if __name__ == "__main__":  # pragma: no cover — 報告用
    for npc, (day, curve) in trust_days(load_library()).items():
        print(f"{npc:18} 信賴：第 {day} 天" if day else f"{npc:18} 信賴：—", curve)
