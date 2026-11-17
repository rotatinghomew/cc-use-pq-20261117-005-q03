from __future__ import annotations

import json


def _table(rows: list[dict], columns: list[tuple[str, str]]) -> list[str]:
    headings = [label for _, label in columns]
    lines = ["| " + " | ".join(headings) + " |", "| " + " | ".join("---" for _ in headings) + " |"]
    for row in rows:
        cells = [str(row.get(key, "" )).replace("|", "\\|").replace("\n", " ") for key, _ in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def render_report(report: dict) -> str:
    population = report["population"]
    criteria = report["criteria"]
    lines = [
        f"# Narrative analysis report {report['report_id']}", "",
        "This report summarizes annotated local records. It does not make literary claims on its own.", "",
        "## Scope", "",
        f"- Tradition filter: {criteria['tradition'] or 'all'}",
        f"- Minimum independent readers: {criteria['minimum_reviewers']}",
        f"- Story revisions: {population['story_revisions']}",
        f"- Pattern consensus: {population['pattern_consensus']}",
        f"- Outcome consensus: {population['outcome_consensus']}", "",
        "## Independent-reader consensus counts", "",
    ]
    lines.extend(_table([{"pattern": key, "count": value} for key, value in report["pattern_counts"].items()],
                        [("pattern", "Pattern"), ("count", "Stories")]))
    lines.extend(["", "## Final pattern counts", ""])
    lines.extend(_table([{"pattern": key, "count": value}
                         for key, value in report["final_pattern_counts"].items()],
                        [("pattern", "Pattern"), ("count", "Stories")]))
    lines.extend(["", "## Coverage", "", "Status counts retain unresolved records in the denominator.", ""])
    coverage = report["coverage"]["pattern"]
    lines.extend(_table([{"status": key, "count": value} for key, value in coverage.items()],
                        [("status", "Pattern review status"), ("count", "Stories")]))
    lines.extend(["", "## Provenance", "", "Story revisions and decision IDs used:", "",
                  "```json", json.dumps(report["provenance"], ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(lines)


def render_axis_report(report: dict) -> str:
    criteria = report["criteria"]
    population = report["population"]
    axis_names = {
        "inheritance": "Inheritance qualification of the youngest (最小者继承资格)",
        "stance": "Grassroots versus elite narrative stance (草根与精英立场张力)",
    }
    lines = [
        f"# Two-axis narrative report {report['report_id']}", "",
        "The two axes are coded and adjudicated independently. This report makes no literary claims on its own.",
        "",
        "## Scope", "",
        f"- Tradition filter: {criteria['tradition'] or 'all'}",
        f"- Minimum independent readers: {criteria['minimum_reviewers']}",
        f"- Story revisions in scope (coverage denominator): {population['story_revisions']}",
        f"- Story revisions with at least one axis coding: {population['story_revisions_with_any_axis_coding']}",
        "",
        "## Per-axis results (each statistic names its own denominator)", "",
    ]
    for axis, block in report["axes"].items():
        lines.extend([
            f"### {axis_names.get(axis, axis)}", "",
            f"- Abstention values (excluded from votes, kept in coverage): {', '.join(block['abstention_values']) or 'none'}",
            f"- Coverage denominator: {block['coverage_denominator']} story revisions",
            f"- Reader-consensus denominator: {block['consensus_denominator']} story revisions",
            f"- Final-value denominator: {block['final_denominator']} story revisions",
            "",
            "Coverage:",
            "",
        ])
        lines.extend(_table(
            [{"status": status, "count": count} for status, count in block["coverage"].items()],
            [("status", "Status"), ("count", "Stories")],
        ))
        lines.extend(["", "Reader consensus counts and rates:", ""])
        lines.extend(_table(
            [{"value": value, "count": count,
              "rate": f"{count / block['consensus_denominator']:.3f}" if block["consensus_denominator"] else "n/a"}
             for value, count in block["consensus_counts"].items()],
            [("value", "Value"), ("count", "Stories"), ("rate", "Rate over consensus denominator")],
        ))
        lines.extend(["", "Final counts (reader consensus unless adjudicated) and rates:", ""])
        lines.extend(_table(
            [{"value": value, "count": count,
              "rate": f"{count / block['final_denominator']:.3f}" if block["final_denominator"] else "n/a"}
             for value, count in block["final_counts"].items()],
            [("value", "Value"), ("count", "Stories"), ("rate", "Rate over final denominator")],
        ))
        lines.append("")
    crosstab = report["axis_crosstab"]
    lines.extend([
        "## Two-axis crosstab", "",
        f"- Basis: {crosstab['basis']}",
        f"- Eligible story revisions (both axes have reader consensus): {crosstab['eligible_story_revisions']}",
        f"- Excluded missing inheritance axis: {crosstab['excluded_missing_inheritance']}",
        f"- Excluded missing stance axis: {crosstab['excluded_missing_stance']}",
        f"- Excluded missing both axes: {crosstab['excluded_missing_both']}",
        "",
        "```json", json.dumps(crosstab["counts"], ensure_ascii=False, indent=2), "```", "",
        "## Provenance", "",
        "```json", json.dumps(report["provenance"], ensure_ascii=False, indent=2), "```", "",
    ])
    return "\n".join(lines)
