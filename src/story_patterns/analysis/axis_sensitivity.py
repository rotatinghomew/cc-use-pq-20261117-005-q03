from __future__ import annotations

from story_patterns.axes import AXIS_LABELS
from story_patterns.analysis.axis_consensus import axis_consensus


def axis_leave_one_reader_out(stories: list[dict], codings: dict, minimum: int) -> dict:
    """逐轴的剔除读者敏感性：一轴结论是否依赖某位读者，与另一轴无关。"""
    examined = []
    changed_counts = {axis: 0 for axis in AXIS_LABELS}
    for story in stories:
        identity = (story["story_id"], story["revision"])
        per_axis = codings.get(identity, {})
        removals_by_annotator: dict[str, dict] = {}
        baseline = {}
        for axis in AXIS_LABELS:
            votes = per_axis.get(axis, [])
            baseline_value, baseline_status = axis_consensus(
                [vote["value"] for vote in votes], axis, minimum
            )
            baseline[axis] = {"value": baseline_value, "status": baseline_status}
            for omitted in votes:
                remaining = [vote for vote in votes if vote["coding_id"] != omitted["coding_id"]]
                value, status = axis_consensus(
                    [vote["value"] for vote in remaining], axis, minimum
                )
                changed = (value, status) != (baseline_value, baseline_status)
                changed_counts[axis] += int(changed)
                removals_by_annotator.setdefault(
                    omitted["annotator"], {}
                )[axis] = {"value": value, "status": status, "changed": changed}
        examined.append({
            "story_id": story["story_id"], "revision": story["revision"],
            "baseline": baseline,
            "removals": [
                {"omitted_annotator": annotator, "axes": axes}
                for annotator, axes in sorted(removals_by_annotator.items())
            ],
            "readers_tested": len(removals_by_annotator),
        })
    return {
        "method": "leave-one-reader-out stability check per axis; diagnostic, not a confidence interval",
        "results_changed_by_axis": changed_counts,
        "stories_examined": len(examined),
        "stories": examined,
    }
