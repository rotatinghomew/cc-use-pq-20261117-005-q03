from __future__ import annotations

from story_patterns.axes import AXIS_LABELS


def axis_evidence_coverage(stories: list[dict], codings: dict) -> dict:
    """按轴统计事件证据覆盖率；一轴的证据缺失不影响另一轴的分母。"""
    total_events = 0
    by_axis = {
        axis: {"cited_events": 0, "story_revisions_with_coding": 0,
               "story_revisions_without_coding": 0, "stories": []}
        for axis in AXIS_LABELS
    }
    for story in stories:
        identity = (story["story_id"], story["revision"])
        known = {event["event_id"] for event in story["events"]}
        total_events += len(known)
        per_axis = codings.get(identity, {})
        for axis in AXIS_LABELS:
            votes = per_axis.get(axis, [])
            cited = {event_id for vote in votes for event_id in vote["evidence_event_ids"]}
            covered = known & cited
            if votes:
                by_axis[axis]["story_revisions_with_coding"] += 1
            else:
                by_axis[axis]["story_revisions_without_coding"] += 1
            by_axis[axis]["cited_events"] += len(covered)
            by_axis[axis]["stories"].append({
                "story_id": story["story_id"], "revision": story["revision"],
                "total_events": len(known), "cited_events": len(covered),
                "coding_count": len(votes),
                "coverage_rate": len(covered) / len(known) if known else None,
                "uncited_event_ids": sorted(known - covered),
            })
    result = {"total_events": total_events, "axes": {}}
    for axis in AXIS_LABELS:
        block = by_axis[axis]
        denominator = block["story_revisions_with_coding"] + block["story_revisions_without_coding"]
        result["axes"][axis] = {
            "cited_events": block["cited_events"],
            "total_events": total_events,
            "coverage_rate": block["cited_events"] / total_events if total_events else None,
            "story_revisions_with_coding": block["story_revisions_with_coding"],
            "story_revisions_without_coding": block["story_revisions_without_coding"],
            "coding_denominator": denominator,
            "stories": block["stories"],
        }
    return result
