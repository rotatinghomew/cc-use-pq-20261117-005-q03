from __future__ import annotations

from collections import Counter, defaultdict

from story_patterns.axes import AXIS_LABELS, abstentions


def axis_vote_distribution(stories: list[dict], codings: dict) -> dict:
    """逐轴的读者投票分布，显式区分有效票、弃权票与未编码故事。"""
    totals = {axis: Counter() for axis in AXIS_LABELS}
    workload: dict[str, set] = defaultdict(set)
    story_rows = []
    for story in stories:
        identity = (story["story_id"], story["revision"])
        per_axis = codings.get(identity, {})
        row = {"story_id": identity[0], "revision": identity[1], "axes": {}}
        for axis in AXIS_LABELS:
            votes = per_axis.get(axis, [])
            counts = Counter(vote["value"] for vote in votes)
            totals[axis].update(counts)
            for vote in votes:
                workload[vote["annotator"]].add(f"{identity[0]}@{identity[1]}")
            skip = abstentions(axis)
            row["axes"][axis] = {
                "reader_count": len(votes),
                "value_votes": {label: counts.get(label, 0) for label in AXIS_LABELS[axis]},
                "usable_votes": sum(count for label, count in counts.items() if label not in skip),
                "abstaining_votes": sum(count for label, count in counts.items() if label in skip),
            }
        story_rows.append(row)
    axes_summary = {}
    for axis in AXIS_LABELS:
        axes_summary[axis] = {
            "active_reader_votes": sum(totals[axis].values()),
            "value_votes": {label: totals[axis].get(label, 0) for label in AXIS_LABELS[axis]},
        }
    return {
        "axes": axes_summary,
        "reader_workload": [
            {"annotator": name, "story_revisions_coded": len(identities)}
            for name, identities in sorted(workload.items())
        ],
        "stories": story_rows,
    }
