"""两轴共识规则：独立于报告组装逻辑，避免循环导入。"""

from __future__ import annotations

from collections import Counter

from story_patterns.axes import abstentions, validate_axis


def axis_consensus(votes: list[str], axis: str, minimum: int) -> tuple[str | None, str]:
    """与旧 ``_consensus`` 同规则，但弃权标签由具体轴决定。

    返回 (共识值或 None, 状态)；状态为 agreed / split / insufficient。
    """
    validate_axis(axis)
    skip = abstentions(axis)
    usable = [vote for vote in votes if vote not in skip]
    if len(usable) < minimum:
        return None, "insufficient"
    counts = Counter(usable)
    ordered = counts.most_common()
    if len(ordered) > 1 and ordered[0][1] == ordered[1][1]:
        return None, "split"
    return ordered[0][0], "agreed"
