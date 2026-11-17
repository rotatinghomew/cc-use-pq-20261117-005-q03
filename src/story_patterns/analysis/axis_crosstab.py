from __future__ import annotations

from collections import Counter

from story_patterns.axes import AXIS_LABELS


def axis_crosstab(story_results: list[dict]) -> dict:
    """两轴读者共识的交叉表；任一轴无共识的故事都被排除并分别计数。"""
    inheritance_axis, stance_axis = AXIS_LABELS
    pairs = Counter()
    missing_inheritance = 0
    missing_stance = 0
    missing_both = 0
    for row in story_results:
        inheritance = row["axes"][inheritance_axis]["reader_consensus"]
        stance = row["axes"][stance_axis]["reader_consensus"]
        if inheritance is None and stance is None:
            missing_both += 1
        elif inheritance is None:
            missing_inheritance += 1
        elif stance is None:
            missing_stance += 1
        else:
            pairs[(inheritance, stance)] += 1
    matrix: dict[str, dict[str, int]] = {}
    for (inheritance, stance), count in sorted(pairs.items()):
        matrix.setdefault(inheritance, {})[stance] = count
    eligible = sum(pairs.values())
    return {
        "basis": "story revisions with independent-reader consensus on both axes",
        "axes": list(AXIS_LABELS),
        "eligible_story_revisions": eligible,
        "eligible_denominator_note": "only stories with reader consensus (not abstentions/split/insufficient) on both axes",
        "excluded_missing_inheritance": missing_inheritance + missing_both,
        "excluded_missing_stance": missing_stance + missing_both,
        "excluded_missing_both": missing_both,
        "counts": matrix,
    }
