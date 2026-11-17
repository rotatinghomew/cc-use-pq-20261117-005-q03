from __future__ import annotations

from collections import defaultdict

from story_patterns.axes import AXIS_LABELS
from story_patterns.analysis.axis_consensus import axis_consensus


#: 队列整体状态键序；两轴状态在 axis_status 中单独保留
QUEUE_STATUSES = ("unreviewed", "needs_more_reviews", "disputed", "ready", "adjudicated")


def build_axis_queue(stories: list[dict], codings: dict, minimum: int,
                     adjudications: dict | None = None) -> list[dict]:
    adjudications = adjudications or {}
    queue = []
    for story in sorted(stories, key=lambda item: (item["tradition"], item["story_id"], item["revision"])):
        identity = (story["story_id"], story["revision"])
        per_axis_votes = codings.get(identity, {})
        per_axis_adjudication = adjudications.get(identity, {})
        cited = {
            event_id
            for votes in per_axis_votes.values()
            for vote in votes
            for event_id in vote["evidence_event_ids"]
        }
        missing_evidence = [event["event_id"] for event in story["events"]
                            if event["event_id"] not in cited]
        axis_status = {}
        axis_rows = {}
        for axis in AXIS_LABELS:
            votes = per_axis_votes.get(axis, [])
            value, status = axis_consensus([vote["value"] for vote in votes], axis, minimum)
            adjudication = per_axis_adjudication.get(axis)
            axis_status[axis] = status
            axis_rows[axis] = {
                "reader_consensus": value,
                "status": status,
                "final_value": adjudication["value"] if adjudication else value,
                "adjudication_id": adjudication["axis_adjudication_id"] if adjudication else None,
                "reader_count": len(votes),
                "reviewer_names": sorted(vote["annotator"] for vote in votes),
            }
        any_coding = any(per_axis_votes.get(axis) for axis in AXIS_LABELS)
        if per_axis_adjudication:
            status = "adjudicated"
        elif not any_coding:
            status = "unreviewed"
        elif "split" in axis_status.values():
            status = "disputed"
        elif any(axis_status[axis] != "agreed" for axis in AXIS_LABELS):
            status = "needs_more_reviews"
        else:
            status = "ready"
        queue.append({
            "story_id": story["story_id"], "revision": story["revision"], "title": story["title"],
            "tradition": story["tradition"], "status": status,
            "axis_status": dict(axis_status),
            "axes": axis_rows,
            "axes_with_reader_coding": sorted(per_axis_votes.keys()),
            "missing_evidence_event_ids": missing_evidence,
            "reviewer_count": sum(len(votes) for votes in per_axis_votes.values()),
            "reviewer_names": sorted({
                vote["annotator"] for votes in per_axis_votes.values() for vote in votes
            }),
        })
    return queue


def axis_queue_totals(rows: list[dict]) -> dict:
    totals = defaultdict(int)
    for row in rows:
        totals[row["status"]] += 1
    return {key: totals.get(key, 0) for key in QUEUE_STATUSES}
