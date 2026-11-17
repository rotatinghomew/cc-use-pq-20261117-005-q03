"""两轴独立分析：共识、覆盖、仲裁与每个统计的显式分母。"""

from __future__ import annotations

from collections import Counter
from typing import Any

from story_patterns.axes import AXIS_LABELS, abstentions
from story_patterns.catalog.validate import canonical_json, digest_json
from story_patterns.analysis.axis_agreement import axis_pairwise_agreement
from story_patterns.analysis.axis_consensus import axis_consensus
from story_patterns.analysis.axis_evidence import axis_evidence_coverage
from story_patterns.analysis.axis_sensitivity import axis_leave_one_reader_out
from story_patterns.analysis.axis_votes import axis_vote_distribution
from story_patterns.catalog.history import lineage_warnings, revision_lineage
from story_patterns.analysis.revision_drift import compare_revisions
from story_patterns.analysis.sample_profile import build_sample_profile
from story_patterns.analysis.axis_crosstab import axis_crosstab
from story_patterns.errors import ConflictError


def _axis_block(axis: str, votes: list[dict], minimum: int, adjudication: dict | None) -> dict:
    values = [item["value"] for item in votes]
    consensus, status = axis_consensus(values, axis, minimum)
    final_value = adjudication["value"] if adjudication else consensus
    counts = Counter(vote for vote in values if vote not in abstentions(axis))
    abstaining = Counter(vote for vote in values if vote in abstentions(axis))
    return {
        "reader_consensus": consensus,
        "status": status,
        "final_value": final_value,
        "adjudication_id": adjudication["axis_adjudication_id"] if adjudication else None,
        "adjudication_rationale": adjudication["rationale"] if adjudication else None,
        "adjudication_evidence_event_ids": adjudication["evidence_event_ids"] if adjudication else [],
        "reader_count": len(votes),
        "usable_vote_count": len([vote for vote in values if vote not in abstentions(axis)]),
        "abstaining_vote_count": sum(abstaining.values()),
        "vote_counts": {label: counts.get(label, 0) for label in AXIS_LABELS[axis]
                        if label not in abstentions(axis)},
        "abstention_counts": {label: abstaining.get(label, 0) for label in AXIS_LABELS[axis]
                              if label in abstentions(axis)},
        "citing_coding_ids": sorted(item["coding_id"] for item in votes),
        "citing_event_ids": sorted({event_id for item in votes for event_id in item["evidence_event_ids"]}),
    }


def build_axis_report(stories: list[dict], codings: dict, tradition: str | None, minimum: int,
                      origins: dict | None = None, adjudications: dict | None = None) -> dict[str, Any]:
    adjudications = adjudications or {}
    coverage = {axis: Counter() for axis in AXIS_LABELS}
    consensus_counts = {axis: Counter() for axis in AXIS_LABELS}
    final_counts = {axis: Counter() for axis in AXIS_LABELS}
    resolution_counts = Counter()
    used_codings: list[str] = []
    used_adjudications: list[str] = []
    story_results = []
    for story in stories:
        identity = (story["story_id"], story["revision"])
        per_axis_votes = codings.get(identity, {})
        per_axis_adjudication = adjudications.get(identity, {})
        axes_block = {}
        for axis in AXIS_LABELS:
            votes = per_axis_votes.get(axis, [])
            adjudication = per_axis_adjudication.get(axis)
            block = _axis_block(axis, votes, minimum, adjudication)
            coverage[axis][block["status"]] += 1
            if block["reader_consensus"] is not None:
                consensus_counts[axis][block["reader_consensus"]] += 1
            if block["final_value"] is not None:
                final_counts[axis][block["final_value"]] += 1
            used_codings.extend(item["coding_id"] for item in votes)
            if adjudication:
                used_adjudications.append(adjudication["axis_adjudication_id"])
            axes_block[axis] = block
        if per_axis_adjudication:
            resolution_counts["adjudicated"] += 1
        else:
            resolution_counts["reader_consensus"] += 1
        story_results.append({
            "story_id": story["story_id"], "revision": story["revision"],
            "title": story["title"], "tradition": story["tradition"],
            "axes": axes_block,
            "axes_with_reader_coding": sorted(per_axis_votes.keys()),
            "axes_with_adjudication": sorted(per_axis_adjudication.keys()),
        })
    axes_summary = {}
    for axis in AXIS_LABELS:
        consensus_denominator = sum(consensus_counts[axis].values())
        final_denominator = sum(final_counts[axis].values())
        coverage_block = {status: coverage[axis].get(status, 0) for status in ("agreed", "split", "insufficient")}
        axes_summary[axis] = {
            "label": axis,
            "abstention_values": sorted(abstentions(axis)),
            "coverage": coverage_block,
            "coverage_denominator": sum(coverage_block.values()),
            "consensus_counts": dict(sorted(consensus_counts[axis].items())),
            "consensus_denominator": consensus_denominator,
            "consensus_rates": {
                label: count / consensus_denominator
                for label, count in sorted(consensus_counts[axis].items())
            } if consensus_denominator else {},
            "final_counts": dict(sorted(final_counts[axis].items())),
            "final_denominator": final_denominator,
            "final_rates": {
                label: count / final_denominator
                for label, count in sorted(final_counts[axis].items())
            } if final_denominator else {},
        }
    return {
        "schema": "two-axis independent coding report; axes are coded, adjudicated and counted separately",
        "criteria": {"tradition": tradition, "minimum_reviewers": minimum,
                     "abstentions_excluded_from_votes": {
                         axis: sorted(abstentions(axis)) for axis in AXIS_LABELS}},
        "population": {
            "story_revisions": len(stories),
            "story_revisions_with_any_axis_coding": sum(1 for identity in codings if codings.get(identity)),
            "reader_consensus_by_axis": {axis: axes_summary[axis]["consensus_denominator"] for axis in AXIS_LABELS},
        },
        "axes": axes_summary,
        "resolution_counts": {key: resolution_counts.get(key, 0)
                              for key in ("reader_consensus", "adjudicated")},
        "adjudicated_story_revisions": sum(1 for value in adjudications.values() if value),
        "story_results": story_results,
        "axis_pairwise_agreement": axis_pairwise_agreement(codings),
        "axis_evidence_coverage": axis_evidence_coverage(stories, codings),
        "axis_reader_sensitivity": axis_leave_one_reader_out(stories, codings, minimum),
        "axis_vote_distribution": axis_vote_distribution(stories, codings),
        "axis_crosstab": axis_crosstab(story_results),
        "sample_profile": build_sample_profile(stories),
        "revision_lineage": {"scope": "selected story revisions", "stories": revision_lineage(stories),
                             "warnings": lineage_warnings(revision_lineage(stories))},
        "revision_changes": compare_revisions(stories),
        "provenance": {
            "story_revisions": [f"{item['story_id']}@{item['revision']}" for item in stories],
            "axis_coding_ids": sorted(set(used_codings)),
            "axis_adjudication_ids": sorted(set(used_adjudications)),
            "batch_ids_by_story": {
                f"{story_id}@{revision}": sorted(batch_ids)
                for (story_id, revision), batch_ids in sorted((origins or {}).items())
            },
        },
    }


class AxisReportService:
    def __init__(self, store):
        self.store = store

    def create(self, tradition: str | None, minimum: int) -> dict:
        from story_patterns.analysis.cohorts import select_cohort, validate_minimum

        minimum = validate_minimum(minimum)
        stories, codings, origins, adjudications = self.store.axis_analysis_snapshot(tradition)
        stories = select_cohort(stories, tradition)
        result = build_axis_report(stories, codings, tradition, minimum, origins, adjudications)
        report_id = digest_json(result)[:24]
        request_digest = digest_json({"criteria": result["criteria"], "provenance": result["provenance"]})
        document = canonical_json({"report_id": report_id, **result})
        with self.store.transaction() as connection:
            previous = connection.execute(
                "SELECT document FROM axis_reports WHERE report_id=?", (report_id,)
            ).fetchone()
            if previous and previous["document"] != document:
                raise ConflictError("axis report identifier collision with different contents")
            connection.execute(
                "INSERT OR IGNORE INTO axis_reports(report_id, request_digest, document) VALUES(?,?,?)",
                (report_id, request_digest, document),
            )
        return {"report_id": report_id, **result}

    def get(self, report_id: str) -> dict | None:
        return self.store.axis_report_document(report_id)
