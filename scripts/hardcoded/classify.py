"""寫死數值歸類（HC-1；``docs/phases/PhaseHC-1計畫.md`` 第 3～5 項）。

把 ``scan_py.py``（後端）和 ``scan_ts.py``（前端）的掃描結果，照 ``classes.yaml`` 的規則歸成五類：

- ``config``：應該進 content 或工坊設定的玩法數值
- ``scale``：量類，應該由 ``quantity_scale`` 推導
- ``const``：真的是常數（格數、AP、d20、‰ 換算、程式邏輯、開發說明……）
- ``text``：說明文字裡的數字，應該從資料帶入
- ``layout``：前端呈現（排版、繪圖、動畫、音效）

規則由上往下比對，**第一條符合的規則勝出**；規則的寫法見 ``classes.yaml`` 開頭。不比對行號，所以別人
改動檔案、行號移動時歸類照舊成立。

用法::

    uv run python scripts/hardcoded/classify.py --check           # 有沒歸類的就列出並結束碼 1
    uv run python scripts/hardcoded/classify.py --stats           # 各類、各區塊筆數
    uv run python scripts/hardcoded/classify.py --unused          # 一筆都沒用到的規則
    uv run python scripts/hardcoded/classify.py --dump config     # 列出某一類（tsv）
    uv run python scripts/hardcoded/classify.py --md docs/phases/寫死數值-清單.md   # 產生清單文件
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Final, Protocol

import yaml

HERE: Final = Path(__file__).resolve().parent
ROOT: Final = HERE.parents[1]
CLASSES_PATH: Final = HERE / "classes.yaml"
CLASSES: Final = ("config", "scale", "const", "text", "layout")
TODO_CLASSES: Final = ("config", "scale", "text")
"""要搬家的三類；``const``、``layout`` 不用搬，``status`` 一律是 ``done``。"""
STATUSES: Final = ("todo", "done")
_LIST_KEYS: Final = ("lang", "files", "scope", "where", "kind", "slot", "owner", "ann", "value")
_REGEX_KEYS: Final = ("text", "context")
_META_KEYS: Final = ("id", "class", "status", "note")
_CONDITION_KEYS: Final = frozenset((*_LIST_KEYS, *_REGEX_KEYS, "bare_digits"))
_ALLOWED_KEYS: Final = _CONDITION_KEYS | frozenset((*_META_KEYS, "not"))
_PLACEHOLDER: Final = re.compile(r"\$?\{[^{}]*\}")
_DIGIT: Final = re.compile(r"[0-9\uff10-\uff19]")
_DESCRIBE_MAX: Final = 60
_BLOCK_DEPTH: Final = 3


class HitLike(Protocol):
    @property
    def lang(self) -> str: ...
    @property
    def file(self) -> str: ...
    @property
    def line(self) -> int: ...
    @property
    def scope(self) -> str: ...
    @property
    def kind(self) -> str: ...
    @property
    def value(self) -> str: ...
    @property
    def slot(self) -> str: ...
    @property
    def context(self) -> str: ...
    @property
    def owner(self) -> str: ...
    @property
    def ann(self) -> str: ...


class ClassesError(ValueError):
    """``classes.yaml`` 寫錯。"""


def _load_module(name: str) -> ModuleType:
    path = HERE / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"hardcoded_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def scan_all() -> list[HitLike]:
    """後端＋前端全部的掃描結果。"""
    hits: list[HitLike] = []
    for name in ("scan_py", "scan_ts"):
        hits.extend(_load_module(name).scan())
    return hits


# ---------------------------------------------------------------------- 規則
_Test = Callable[[HitLike, bool], bool]


@dataclass
class Rule:
    id: str
    cls: str
    status: str
    note: str
    tests: list[_Test] = field(default_factory=list)
    hits: int = 0

    def matches(self, hit: HitLike, bare: bool) -> bool:
        return all(test(hit, bare) for test in self.tests)


def _as_list(value: object, key: str, rule_id: str) -> list[str]:
    if isinstance(value, str | int | float):
        return [str(value)]
    if isinstance(value, list) and all(isinstance(v, str | int | float) for v in value):
        return [str(v) for v in value]
    raise ClassesError(f"規則 {rule_id}：{key} 要是字串或字串清單")


def where_of(hit: HitLike) -> str:
    """``where``：函式或類別裡的就是 ``scope``；模組層的是 ``<module>.常數名``。"""
    return hit.scope if hit.scope != "<module>" else f"<module>.{hit.owner}"


def _attr(hit: HitLike, name: str) -> str:
    return where_of(hit) if name == "where" else str(getattr(hit, name))


def _glob_test(attr: str, patterns: list[str]) -> Callable[[HitLike, bool], bool]:
    regex = re.compile("|".join(f"(?:{fnmatch.translate(p)})" for p in patterns), re.DOTALL)

    def test(hit: HitLike, _bare: bool) -> bool:
        return regex.match(_attr(hit, attr)) is not None

    return test


def _regex_test(attr: str, pattern: str, rule_id: str) -> Callable[[HitLike, bool], bool]:
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        raise ClassesError(f"規則 {rule_id}：{attr} 的正規表示式寫錯（{exc}）") from exc
    return lambda hit, _bare: regex.search(str(getattr(hit, attr))) is not None


def _bare_test(flag: bool) -> Callable[[HitLike, bool], bool]:
    return lambda _hit, bare: bare is flag


def _conditions(raw: dict[str, Any], rule_id: str) -> list[_Test]:
    tests: list[_Test] = []
    for key in _LIST_KEYS:
        if key in raw:
            items = _as_list(raw[key], key, rule_id)
            tests.append(_glob_test("file" if key == "files" else key, items))
    for key in _REGEX_KEYS:
        if key in raw:
            attr = "value" if key == "text" else key
            tests.append(_regex_test(attr, str(raw[key]), rule_id))
    if "bare_digits" in raw:
        flag = raw["bare_digits"]
        if not isinstance(flag, bool):
            raise ClassesError(f"規則 {rule_id}：bare_digits 要是 true 或 false")
        tests.append(_bare_test(flag))
    return tests


def _not_test(raw: object, rule_id: str) -> _Test:
    if not isinstance(raw, dict) or not raw or set(raw) - _CONDITION_KEYS:
        raise ClassesError(f"規則 {rule_id}：not 要是條件的 mapping（欄位同規則的條件）")
    inner = _conditions(raw, rule_id)
    return lambda hit, bare: not all(test(hit, bare) for test in inner)


def _rule(raw: object, index: int) -> Rule:
    if not isinstance(raw, dict):
        raise ClassesError(f"第 {index + 1} 條規則要是 mapping")
    rule_id = str(raw.get("id") or "")
    if not rule_id:
        raise ClassesError(f"第 {index + 1} 條規則缺 id")
    unknown = sorted(set(raw) - _ALLOWED_KEYS)
    if unknown:
        raise ClassesError(f"規則 {rule_id}：不認得的欄位 {unknown}")
    cls = raw.get("class")
    if cls not in CLASSES:
        raise ClassesError(f"規則 {rule_id}：class 要是 {'／'.join(CLASSES)} 之一，收到 {cls!r}")
    status = raw.get("status")
    if status not in STATUSES:
        raise ClassesError(f"規則 {rule_id}：status 要是 todo 或 done，收到 {status!r}")
    if cls not in TODO_CLASSES and status != "done":
        raise ClassesError(f"規則 {rule_id}：{cls} 不用搬，status 要寫 done")
    rule = Rule(rule_id, str(cls), str(status), str(raw.get("note") or ""))
    rule.tests = _conditions(raw, rule_id)
    if "not" in raw:
        rule.tests.append(_not_test(raw["not"], rule_id))
    return rule


@dataclass
class Classes:
    rules: list[Rule]
    references: list[re.Pattern[str]]

    def bare_digits(self, hit: HitLike) -> bool:
        """去掉占位（``{x}``、``${x}``）和引用（``#12``、``5.4.1``……）後還有沒有數字。"""
        if hit.kind == "number":
            return True
        text = _PLACEHOLDER.sub(" ", hit.value)
        for ref in self.references:
            text = ref.sub(" ", text)
        return _DIGIT.search(text) is not None

    def classify(self, hit: HitLike) -> Rule | None:
        bare = self.bare_digits(hit)
        for rule in self.rules:
            if rule.matches(hit, bare):
                return rule
        return None


def load_classes(path: Path = CLASSES_PATH) -> Classes:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise ClassesError("classes.yaml 要有 rules 清單")
    rules = [_rule(raw, i) for i, raw in enumerate(data["rules"])]
    seen: Counter[str] = Counter(rule.id for rule in rules)
    dup = sorted(rule_id for rule_id, n in seen.items() if n > 1)
    if dup:
        raise ClassesError(f"規則 id 重複：{dup}")
    refs_raw = data.get("references") or []
    if not isinstance(refs_raw, list):
        raise ClassesError("references 要是正規表示式清單")
    try:
        refs = [re.compile(str(r)) for r in refs_raw]
    except re.error as exc:
        raise ClassesError(f"references 的正規表示式寫錯（{exc}）") from exc
    return Classes(rules, refs)


# ---------------------------------------------------------------------- 結果
@dataclass
class Result:
    classes: Classes
    assigned: list[tuple[HitLike, Rule]]
    unclassified: list[HitLike]

    def by_class(self, cls: str) -> list[tuple[HitLike, Rule]]:
        return [(hit, rule) for hit, rule in self.assigned if rule.cls == cls]


def classify(hits: Iterable[HitLike] | None = None, classes: Classes | None = None) -> Result:
    classes = classes or load_classes()
    assigned: list[tuple[HitLike, Rule]] = []
    missing: list[HitLike] = []
    for hit in scan_all() if hits is None else hits:
        rule = classes.classify(hit)
        if rule is None:
            missing.append(hit)
        else:
            rule.hits += 1
            assigned.append((hit, rule))
    return Result(classes, assigned, missing)


def describe(hit: HitLike) -> str:
    value = hit.value.replace("\n", "\\n")
    if len(value) > _DESCRIBE_MAX:
        value = value[: _DESCRIBE_MAX - 3] + "..."
    extra = f" owner={hit.owner}" if hit.owner else ""
    return (
        f"{hit.file}:{hit.line} [{hit.kind}] scope={hit.scope} slot={hit.slot or '-'}{extra} "
        f"value={value!r}"
    )


def unclassified_message(result: Result, limit: int = 40) -> str:
    lines = [
        f"有 {len(result.unclassified)} 筆寫死的數字或含數字的中文字串沒有歸類。",
        "請在 scripts/hardcoded/classes.yaml 加規則（第一條符合的規則勝出，寫在較寬的規則前面）：",
        "  config＝玩法數值要搬進 content／工坊；scale＝量類（由 quantity_scale 推導）；",
        "  const＝真的常數；text＝說明文字裡的數字（要從資料帶入）；layout＝前端呈現。",
        "  拿不準 config 還是 const 時歸 config。例：",
    ]
    if result.unclassified:
        first = result.unclassified[0]
        lines += [
            "  - id: <新的規則 id>",
            "    class: config",
            "    status: todo",
            f"    files: [{first.file}]",
            f"    scope: [{first.scope!r}]",
            f"    kind: [{first.kind}]",
        ]
        if first.kind == "number":
            lines.append(f"    value: [{first.value!r}]")
    lines.append(f"沒歸類的（前 {limit} 筆）：")
    lines += ["  " + describe(hit) for hit in result.unclassified[:limit]]
    return "\n".join(lines)


def block_of(file: str) -> str:
    """區塊：後端是 ``src/trpg/`` 下的子套件，前端是 ``client/src/`` 下的第一層資料夾。"""
    parts = file.split("/")
    nested = len(parts) > _BLOCK_DEPTH
    if file.startswith("src/trpg/"):
        return "後端 " + (parts[2] if nested else parts[2].removesuffix(".py"))
    if file.startswith("client/src/"):
        return "前端 " + (parts[2] if nested else "(根目錄)")
    return file


def side_of(file: str) -> str:
    return "後端" if file.startswith("src/") else "前端"


# ---------------------------------------------------------------------- 輸出
def stats_lines(result: Result) -> list[str]:
    lines: list[str] = []
    for side in ("後端", "前端"):
        counts = Counter(rule.cls for hit, rule in result.assigned if side_of(hit.file) == side)
        total = sum(counts.values())
        lines.append(f"{side}：共 {total} 筆　" + "　".join(f"{c} {counts[c]}" for c in CLASSES))
    lines.append(f"沒歸類：{len(result.unclassified)}")
    return lines


def _md_escape(text: str, limit: int = 70) -> str:
    text = text.replace("\n", "↵").replace("|", "｜").replace("`", "'")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _count_table(result: Result, side: str) -> list[str]:
    per_block: dict[str, Counter[str]] = defaultdict(Counter)
    for hit, rule in result.assigned:
        if side_of(hit.file) == side:
            per_block[block_of(hit.file)][rule.cls] += 1
    lines = [
        "| 區塊 | " + " | ".join(CLASSES) + " | 合計 |",
        "|---|" + "---:|" * (len(CLASSES) + 1),
    ]
    total: Counter[str] = Counter()
    for block in sorted(per_block):
        counts = per_block[block]
        total.update(counts)
        cells = " | ".join(str(counts[c]) for c in CLASSES)
        lines.append(f"| {block} | {cells} | {sum(counts.values())} |")
    cells = " | ".join(f"**{total[c]}**" for c in CLASSES)
    lines.append(f"| **合計** | {cells} | **{sum(total.values())}** |")
    return lines


def _rule_table(result: Result, classes: Sequence[str]) -> list[str]:
    lines = ["| 規則 | 類 | 筆數 | 說明 |", "|---|---|---:|---|"]
    for rule in result.classes.rules:
        if rule.cls in classes and rule.hits:
            note = _md_escape(rule.note, 120)
            lines.append(f"| `{rule.id}` | {rule.cls} | {rule.hits} | {note} |")
    return lines


def _item_list(result: Result, cls: str) -> list[str]:
    grouped: dict[str, dict[str, list[tuple[HitLike, Rule]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for hit, rule in result.by_class(cls):
        grouped[block_of(hit.file)][hit.file].append((hit, rule))
    lines: list[str] = []
    for block in sorted(grouped):
        count = sum(len(v) for v in grouped[block].values())
        lines += [f"#### {cls}｜{block}（{count}）", ""]
        for file in sorted(grouped[block]):
            lines.append(f"- `{file}`")
            for hit, rule in sorted(grouped[block][file], key=lambda pair: pair[0].line):
                owner = f" `{hit.owner}`" if hit.owner and hit.owner != hit.scope else ""
                lines.append(
                    f"  - {hit.line}｜`{hit.scope}`{owner}｜`{_md_escape(hit.value, 50)}`"
                    f"｜`{_md_escape(hit.context, 80)}`｜{rule.id}｜{rule.status}"
                )
        lines.append("")
    return lines


def markdown(result: Result, plan: list[str]) -> str:
    lines = [
        "# 寫死數值清單（HC-1 產出）",
        "",
        "> 由 `uv run python scripts/hardcoded/classify.py --md docs/phases/寫死數值-清單.md` "
        "產生，**不要手改**；改 `scripts/hardcoded/classes.yaml` 後重產。",
        "> 行號是產生當時的位置，只供查找；歸類本身不靠行號。",
        "",
        "## 1. 筆數",
        "",
        *[f"- {line}" for line in stats_lines(result)],
        "",
        "### 後端（`src/trpg/`）",
        "",
        *_count_table(result, "後端"),
        "",
        "### 前端（`client/src/`）",
        "",
        *_count_table(result, "前端"),
        "",
        "## 2. 建議的搬家分段",
        "",
        *plan,
        "",
        "## 3. 要搬的規則（config／scale／text）",
        "",
        *_rule_table(result, TODO_CLASSES),
        "",
        "## 4. 不搬的規則（const／layout）",
        "",
        *_rule_table(result, ("const", "layout")),
        "",
        "## 5. 完整清單（config／scale／text，依區塊、檔案分組）",
        "",
        "每列：行｜所在函式或類別 `欄位或常數`｜值｜那一行原文｜規則｜狀態。",
        "",
    ]
    for cls in TODO_CLASSES:
        lines += [f"### {cls}（{len(result.by_class(cls))}）", "", *_item_list(result, cls)]
    return "\n".join(lines).rstrip() + "\n"


def _plan(path: Path = CLASSES_PATH) -> list[str]:
    data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    plan = data.get("plan") or []
    return [str(line) for line in plan]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="寫死數值歸類（HC-1）")
    parser.add_argument("--check", action="store_true", help="有沒歸類的就列出並結束碼 1")
    parser.add_argument("--stats", action="store_true", help="各類筆數")
    parser.add_argument("--unused", action="store_true", help="一筆都沒用到的規則")
    parser.add_argument("--dump", choices=CLASSES, help="列出某一類（tsv）")
    parser.add_argument("--unclassified", action="store_true", help="列出全部沒歸類的（tsv）")
    parser.add_argument("--md", type=Path, help="產生清單文件到這個路徑")
    args = parser.parse_args(argv)
    result = classify()
    if args.dump or args.unclassified:
        rows = (
            [(hit, "-") for hit in result.unclassified]
            if args.unclassified
            else [(hit, rule.id) for hit, rule in result.by_class(args.dump)]
        )
        for hit, rule_id in rows:
            value = hit.value.replace("\n", "\\n").replace("\t", " ")[:80]
            print(
                f"{hit.file}:{hit.line}\t{hit.scope}\t{hit.kind}\t{hit.slot}\t{hit.owner}\t"
                f"{hit.ann}	{value}	{rule_id}	{hit.context[:100]}"
            )
    if args.unused:
        for rule in result.classes.rules:
            if not rule.hits:
                print(f"沒用到：{rule.id}")
    if args.md:
        target = args.md if args.md.is_absolute() else ROOT / args.md
        target.write_text(markdown(result, _plan()), encoding="utf-8", newline="\n")
        print(f"寫入 {target.relative_to(ROOT).as_posix()}")
    if args.stats or args.check or not (args.dump or args.unused or args.md or args.unclassified):
        for line in stats_lines(result):
            print(line)
    if args.check and result.unclassified:
        print(unclassified_message(result))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
