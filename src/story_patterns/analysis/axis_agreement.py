from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from story_patterns.axes import AXIS_LABELS


def axis_pairwise_agreement(codings: dict) -> dict:
    """每个轴单独计算读者两两一致率；只比较两人在该轴都编码过的故事。"""
    pairs = defaultdict(lambda: defaultdict(lambda: {"compared": 0, "matches": 0}))
    for per_axis in codings.values():
        for axis, votes in per_axis.items():
            by_annotator = {vote["annotator"]: vote for vote in votes}
            for first, second in combinations(sorted(by_annotator), 2):
                summary = pairs[(first, second)][axis]
                summary["compared"] += 1
                summary["matches"] += by_annotator[first]["value"] == by_annotator[second]["value"]
    output = []
    for (first, second), by_axis in sorted(pairs.items()):
        row = {"annotators": [first, second]}
        for axis in AXIS_LABELS:
            summary = by_axis.get(axis)
            compared = summary["compared"] if summary else 0
            row[axis] = {
                "compared_story_revisions": compared,
                "matches": summary["matches"] if summary else 0,
                "agreement": (summary["matches"] / compared) if summary and compared else None,
            }
        output.append(row)
    return {
        "method": "exact pairwise agreement per axis; descriptive only; null when the pair shares no coding",
        "pairs": output,
    }
