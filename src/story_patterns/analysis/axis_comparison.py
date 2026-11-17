from __future__ import annotations

from collections import defaultdict

from story_patterns.axes import AXIS_LABELS
from story_patterns.analysis.axis_report import build_axis_report


def compare_traditions_by_axis(stories: list[dict], codings: dict, minimum: int,
                               adjudications: dict | None = None) -> dict:
    grouped = defaultdict(list)
    for story in stories:
        grouped[story["tradition"]].append(story)
    rows = []
    for tradition in sorted(grouped):
        cohort = grouped[tradition]
        identities = {(item["story_id"], item["revision"]) for item in cohort}
        cohort_codings = {identity: codings.get(identity, {}) for identity in identities}
        cohort_adjudications = (
            {identity: (adjudications or {}).get(identity, {}) for identity in identities}
            if adjudications else {}
        )
        summary = build_axis_report(cohort, cohort_codings, tradition, minimum,
                                    adjudications=cohort_adjudications)
        rows.append({
            "tradition": tradition,
            "story_revisions": summary["population"]["story_revisions"],
            "axes": {
                axis: {
                    "coverage": summary["axes"][axis]["coverage"],
                    "coverage_denominator": summary["axes"][axis]["coverage_denominator"],
                    "consensus_counts": summary["axes"][axis]["consensus_counts"],
                    "consensus_denominator": summary["axes"][axis]["consensus_denominator"],
                    "consensus_rates": summary["axes"][axis]["consensus_rates"],
                    "final_counts": summary["axes"][axis]["final_counts"],
                    "final_denominator": summary["axes"][axis]["final_denominator"],
                    "final_rates": summary["axes"][axis]["final_rates"],
                }
                for axis in AXIS_LABELS
            },
        })
    return {
        "method": "descriptive per-axis comparison of independently filtered cohorts",
        "minimum_reviewers": minimum,
        "groups": rows,
        "interpretation_limit": "Each axis and group has its own denominator; coverage must be reviewed before comparison.",
    }
