"""两条独立研究轴的词汇表与共享规则。

课堂讨论把两个问题视为相关但不同的编码轴：

* ``inheritance`` —— 最小者（最年幼的兄弟姐妹）是否取得继承资格；
* ``stance`` —— 叙事是否呈现草根与精英之间的立场张力。

两轴各自保留证据、弃权、分歧与仲裁状态；一轴缺料、修订或仲裁
不影响另一轴的独立解释。旧的平行型/加害型标签仍按其原含义留在
``decisions`` / ``adjudications`` 表中，不做任何重新解释。
"""

from __future__ import annotations

from story_patterns.errors import ValidationError

#: 轴标识 -> 该轴读者投票允许使用的判断标签
AXIS_LABELS: dict[str, tuple[str, ...]] = {
    "inheritance": ("wins", "loses", "mixed", "unknown"),
    "stance": ("tension", "no_tension", "unclear"),
}

#: 各轴的弃权标签（不进入投票多数，但保留在覆盖表中）
AXIS_ABSTENTIONS: dict[str, frozenset[str]] = {
    "inheritance": frozenset({"unknown"}),
    "stance": frozenset({"unclear"}),
}

#: 仲裁只允许实质判断，不允许把弃权裁定为最终结论
AXIS_ADJUDICATION_LABELS: dict[str, tuple[str, ...]] = {
    "inheritance": ("wins", "loses", "mixed"),
    "stance": ("tension", "no_tension"),
}

#: 覆盖状态固定键序，保证空队列下各状态仍显式出现
COVERAGE_STATUSES = ("agreed", "split", "insufficient")


def validate_axis(axis: object) -> str:
    if not isinstance(axis, str) or axis not in AXIS_LABELS:
        supported = ", ".join(sorted(AXIS_LABELS))
        raise ValidationError(f"axis must be one of: {supported}")
    return axis


def axis_labels(axis: str) -> tuple[str, ...]:
    return AXIS_LABELS[validate_axis(axis)]


def abstentions(axis: str) -> frozenset[str]:
    return AXIS_ABSTENTIONS[validate_axis(axis)]


def adjudication_labels(axis: str) -> tuple[str, ...]:
    return AXIS_ADJUDICATION_LABELS[validate_axis(axis)]
