"""離線檢查（4-L11b）：用樣本 md 與被擋原句，比較舊／新一致性詞表與規則（不連模型）。

技能的實際效果鍵取不到，所以用卡片文字近似：詞組在卡片文字（階級行＋效果行）裡找不到任何對應
關鍵字，就算「被擋」。用法：``uv run python scripts/consistency_offline_check.py <舊詞表.yaml>``
（舊詞表用 ``git show <commit>:content/llm/effect_words.yaml`` 取得）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from trpg.content.effect_words import EffectWords, load_effect_words
from trpg.llm.consistency import mentioned_groups

DOCS = Path("docs/phases/4-L9")
# 詞組 id -> 卡片文字裡算「有這個效果」的關鍵字
CARD: dict[str, tuple[str, ...]] = {
    "slow": ("緩速", "冰凍", "凍結"),
    "root": ("纏住", "定身", "束縛", "淨化"),
    "stun": ("暈眩",),
    "frozen": ("冰凍", "凍結", "冰」表面"),
    "prone": ("倒地", "擊倒", "震波", "推倒"),
    "push": ("推開", "震波"),
    "pull": ("拉近", "牽引", "交換位置"),
    "blind": ("致盲",),
    "silence": ("沉默",),
    "fear": ("恐懼",),
    "taunt": ("嘲諷",),
    "bleed": ("流血",),
    "stealth": ("隱蔽", "煙霧", "黑暗"),
    "fire": ("火焰", "燃燒", "火」表面"),
    "burning": ("「燃燒」", "火」表面"),
    "vulnerable": ("「易傷」",),
    "ice": ("冰霜", "冰凍", "「冰」"),
    "lightning": ("雷電",),
    "poison": ("毒素", "淨化", "毒」表面"),
    "wind": ("風傷害", "吹"),
    "earth": ("大地", "石柱", "擊倒", "投擲", "把 1 格內"),
    "holy": ("神聖",),
    "shadow": ("暗影", "煙霧", "隱蔽", "致盲"),
    "water": ("「水」表面",),
    "summon": ("召喚", "獻祭"),
    "vine": ("藤蔓", "纏住"),
    "totem": ("圖騰",),
    "teleport": ("傳送", "交換位置"),
    "heal": ("治療", "淨化"),
    "shield": ("護盾", "擋攻擊", "護衛"),
}


def parse(path: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for block in re.split(r"\n(?=### )", path.read_text(encoding="utf-8")):
        head = re.match(r"### \d+\. (.+)", block)
        if not head:
            continue
        name = head.group(1).split("→")[-1].strip()
        fields = dict(re.findall(r"^- (階級|概念|施放敘事|效果)[：: ](.*)$", block, re.M))
        if "概念" in fields:
            fields["name"] = name
            items.append(fields)
    return items


def blocked(text: str, card: str, words: EffectWords) -> list[str]:
    return [
        w
        for g, w in mentioned_groups(text, words)
        if not any(k in card for k in CARD.get(g.id, ()))
    ]


def count(path: Path, words: EffectWords) -> tuple[int, int]:
    items = parse(path)
    bad = 0
    for it in items:
        card = it.get("階級", "") + it.get("效果", "")
        if any(blocked(it.get(k, ""), card, words) for k in ("name", "概念", "施放敘事")):
            bad += 1
    return bad, len(items)


def main() -> None:
    old = load_effect_words(Path(sys.argv[1]))
    new = load_effect_words()
    for label, f in (("舊樣本", "AI生成樣本.md"), ("新樣本", "AI生成樣本_4L11.md")):
        print(label, "改前擋/總:", count(DOCS / f, old), "改後擋/總:", count(DOCS / f, new))
    for it in parse(DOCS / "AI生成樣本_4L11.md"):
        card = it.get("階級", "") + it.get("效果", "")
        for k in ("name", "概念", "施放敘事"):
            b_old, b_new = blocked(it[k], card, old), blocked(it[k], card, new)
            if b_old != b_new:
                print(f"差異 {it['name']}.{k}: {b_old} -> {b_new}")


if __name__ == "__main__":
    main()
