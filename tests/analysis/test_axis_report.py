import json
import tempfile
import unittest
from pathlib import Path

from story_patterns.analysis.axis_consensus import axis_consensus
from story_patterns.analysis.axis_crosstab import axis_crosstab
from story_patterns.analysis.export import export_axis_csv, export_json
from story_patterns.analysis.markdown import render_axis_report
from tests.support import AppCase, axis_adjudication, axis_coding, batch, story


INH = "inheritance"
STA = "stance"


class AxisConsensusRuleTests(unittest.TestCase):
    def test_quorum_leader_split_and_insufficient_are_distinct(self):
        self.assertEqual(axis_consensus(["wins", "wins", "loses"], INH, 2), ("wins", "agreed"))
        self.assertEqual(axis_consensus(["wins", "loses"], INH, 2), (None, "split"))
        self.assertEqual(axis_consensus(["tension"], STA, 2), (None, "insufficient"))

    def test_each_axis_uses_its_own_abstention_label(self):
        self.assertEqual(axis_consensus(["wins", "unknown"], INH, 2), (None, "insufficient"))
        self.assertEqual(axis_consensus(["tension", "unclear", "tension"], STA, 2),
                         ("tension", "agreed"))

    def test_crosstab_counts_exclusions_per_axis(self):
        rows = [
            {"axes": {INH: {"reader_consensus": "wins"}, STA: {"reader_consensus": "tension"}}},
            {"axes": {INH: {"reader_consensus": "wins"}, STA: {"reader_consensus": None}}},
            {"axes": {INH: {"reader_consensus": None}, STA: {"reader_consensus": "no_tension"}}},
            {"axes": {INH: {"reader_consensus": None}, STA: {"reader_consensus": None}}},
        ]
        result = axis_crosstab(rows)
        self.assertEqual(result["counts"], {"wins": {"tension": 1}})
        self.assertEqual(result["eligible_story_revisions"], 1)
        self.assertEqual(result["excluded_missing_inheritance"], 2)
        self.assertEqual(result["excluded_missing_stance"], 2)
        self.assertEqual(result["excluded_missing_both"], 1)


class TwoAxisIndependenceTests(AppCase, unittest.TestCase):
    def test_axes_are_counted_with_separate_denominators(self):
        records = [story("a"), story("b"), story("c")]
        self.app.import_batch(batch(records, "three"))
        # a: 两轴都有共识；b: 只有继承轴；c: 完全未编码
        self.add_axis_codings([
            axis_coding("a", annotator="reader-a", axis=INH, value="wins"),
            axis_coding("a", annotator="reader-b", axis=INH, value="wins"),
            axis_coding("a", annotator="reader-a", axis=STA, value="tension", coding_id="a-s-a"),
            axis_coding("a", annotator="reader-b", axis=STA, value="tension", coding_id="a-s-b"),
            axis_coding("b", annotator="reader-a", axis=INH, value="loses", coding_id="b-i-a"),
            axis_coding("b", annotator="reader-b", axis=INH, value="loses", coding_id="b-i-b"),
        ])
        report = self.app.create_axis_report()
        self.assertEqual(report["population"]["story_revisions"], 3)
        self.assertEqual(report["population"]["reader_consensus_by_axis"],
                         {INH: 2, STA: 1})
        self.assertEqual(report["axes"][INH]["coverage"],
                         {"agreed": 2, "split": 0, "insufficient": 1})
        self.assertEqual(report["axes"][STA]["coverage"],
                         {"agreed": 1, "split": 0, "insufficient": 2})
        self.assertEqual(report["axes"][INH]["consensus_denominator"], 2)
        self.assertEqual(report["axes"][STA]["consensus_denominator"], 1)
        # 覆盖分类之和始终等于故事总数
        for axis in (INH, STA):
            self.assertEqual(sum(report["axes"][axis]["coverage"].values()), 3)

    def test_one_axis_split_does_not_block_the_other_axis_consensus(self):
        self.import_story()
        self.add_axis_codings([
            axis_coding(axis=INH, annotator="reader-a", value="wins", coding_id="i-a"),
            axis_coding(axis=INH, annotator="reader-b", value="loses", coding_id="i-b"),
            axis_coding(axis=STA, annotator="reader-a", value="tension", coding_id="s-a"),
            axis_coding(axis=STA, annotator="reader-b", value="tension", coding_id="s-b"),
        ])
        report = self.app.create_axis_report()
        row = report["story_results"][0]["axes"]
        self.assertEqual(row[INH]["status"], "split")
        self.assertIsNone(row[INH]["reader_consensus"])
        self.assertEqual(row[STA]["status"], "agreed")
        self.assertEqual(row[STA]["reader_consensus"], "tension")

    def test_abstentions_remain_in_coverage_but_not_in_vote_denominator(self):
        self.import_story()
        self.add_axis_codings([
            axis_coding(axis=STA, annotator="reader-a", value="tension", coding_id="s-a"),
            axis_coding(axis=STA, annotator="reader-b", value="unclear", coding_id="s-b"),
        ])
        report = self.app.create_axis_report()
        block = report["axes"][STA]
        self.assertEqual(block["coverage"]["insufficient"], 1)
        self.assertEqual(block["consensus_denominator"], 0)
        self.assertEqual(block["consensus_counts"], {})
        self.assertEqual(block["consensus_rates"], {})
        distribution = report["axis_vote_distribution"]["axes"][STA]
        self.assertEqual(distribution["value_votes"], {"tension": 1, "no_tension": 0, "unclear": 1})

    def test_single_axis_revision_leaves_the_other_axis_explainable(self):
        self.import_story()
        self.add_axis_codings([
            axis_coding(axis=INH, annotator="reader-a", value="wins", coding_id="i-a"),
            axis_coding(axis=INH, annotator="reader-b", value="wins", coding_id="i-b"),
            axis_coding(axis=STA, annotator="reader-a", value="tension", coding_id="s-a"),
        ])
        report = self.app.create_axis_report()
        row = report["story_results"][0]["axes"]
        self.assertEqual(row[INH]["status"], "agreed")
        self.assertEqual(row[STA]["status"], "insufficient")
        # 立场轴仍可独立解释：证据、票数和弃权状态都保留
        self.assertEqual(row[STA]["reader_count"], 1)
        self.assertEqual(row[STA]["citing_coding_ids"], ["s-a"])

    def test_axis_adjudication_changes_only_its_own_final_value(self):
        self.import_story()
        self.add_axis_codings([
            axis_coding(axis=INH, annotator="reader-a", value="wins", coding_id="i-a"),
            axis_coding(axis=INH, annotator="reader-b", value="loses", coding_id="i-b"),
            axis_coding(axis=STA, annotator="reader-a", value="tension", coding_id="s-a"),
            axis_coding(axis=STA, annotator="reader-b", value="tension", coding_id="s-b"),
        ])
        self.app.record_axis_adjudication(axis_adjudication(axis=INH, value="mixed"))
        report = self.app.create_axis_report()
        row = report["story_results"][0]["axes"]
        self.assertIsNone(row[INH]["reader_consensus"])
        self.assertEqual(row[INH]["final_value"], "mixed")
        self.assertEqual(row[STA]["final_value"], "tension")
        self.assertIsNone(row[STA]["adjudication_id"])
        self.assertEqual(report["resolution_counts"], {"reader_consensus": 0, "adjudicated": 1})

    def test_report_is_frozen_under_separate_identifier_and_round_trips(self):
        self.import_story()
        self.add_axis_codings([
            axis_coding(axis=INH, annotator="reader-a", value="wins", coding_id="i-a"),
            axis_coding(axis=INH, annotator="reader-b", value="wins", coding_id="i-b"),
        ])
        first = self.app.create_axis_report()
        self.assertEqual(self.app.stored_axis_report(first["report_id"])["report_id"],
                         first["report_id"])
        self.app.record_axis_coding(axis_coding(axis=STA, annotator="reader-a",
                                                value="tension", coding_id="s-a"))
        later = self.app.create_axis_report()
        self.assertNotEqual(first["report_id"], later["report_id"])
        # 旧报告仍按原内容读取
        self.assertEqual(
            self.app.stored_axis_report(first["report_id"])["axes"][STA]["coverage"]
            ["insufficient"], 1
        )
        with tempfile.TemporaryDirectory() as directory:
            path = export_json(later, Path(directory) / "axis.json")
            loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["report_id"], later["report_id"])
        self.assertEqual(loaded["axes"][INH]["consensus_denominator"], 1)

    def test_evidence_coverage_and_pairwise_agreement_are_per_axis(self):
        self.import_story()
        self.add_axis_codings([
            axis_coding(axis=INH, annotator="reader-a", value="wins", evidence=["first"]),
            axis_coding(axis=INH, annotator="reader-b", value="loses", evidence=["first"],
                        coding_id="tale-a-inheritance-reader-b-1"),
            axis_coding(axis=STA, annotator="reader-a", value="tension", evidence=["third"],
                        coding_id="tale-a-stance-reader-a-1"),
            axis_coding(axis=STA, annotator="reader-b", value="tension", evidence=["third"],
                        coding_id="tale-a-stance-reader-b-1"),
        ])
        report = self.app.create_axis_report()
        coverage = report["axis_evidence_coverage"]["axes"]
        self.assertEqual(coverage[INH]["cited_events"], 1)
        self.assertEqual(coverage[STA]["cited_events"], 1)
        pair = report["axis_pairwise_agreement"]["pairs"][0]
        self.assertEqual(pair[INH]["agreement"], 0.0)
        self.assertEqual(pair[STA]["agreement"], 1.0)
        sensitivity = report["axis_reader_sensitivity"]
        # 两人样本剔除任一人都跌破两人门槛：两轴各自独立记录状态变化
        story_check = sensitivity["stories"][0]
        self.assertEqual(story_check["readers_tested"], 2)
        for removal in story_check["removals"]:
            self.assertEqual(removal["axes"][STA]["status"], "insufficient")
            self.assertIsNone(removal["axes"][STA]["value"])
            self.assertTrue(removal["axes"][STA]["changed"])
            self.assertTrue(removal["axes"][INH]["changed"])
        self.assertEqual(sensitivity["results_changed_by_axis"], {INH: 2, STA: 2})

    def test_csv_export_keeps_one_row_per_story_axis_even_without_codings(self):
        records = [story("a"), story("b")]
        self.app.import_batch(batch(records, "two"))
        self.add_axis_codings([
            axis_coding("a", axis=INH, annotator="reader-a", value="wins"),
            axis_coding("a", axis=INH, annotator="reader-b", value="wins",
                        coding_id="a-inh-b"),
        ])
        report = self.app.create_axis_report()
        with tempfile.TemporaryDirectory() as directory:
            path = export_axis_csv(report, Path(directory) / "axes.csv")
            import csv
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 4)  # 2 stories x 2 axes
        missing = [row for row in rows if row["story_id"] == "b" and row["axis"] == STA][0]
        self.assertEqual(missing["status"], "insufficient")
        self.assertEqual(missing["reader_count"], "0")

    def test_markdown_names_each_denominator(self):
        self.import_story()
        self.add_axis_codings([
            axis_coding(axis=INH, annotator="reader-a", value="wins", coding_id="i-a"),
            axis_coding(axis=INH, annotator="reader-b", value="wins", coding_id="i-b"),
        ])
        markdown = render_axis_report(self.app.create_axis_report())
        self.assertIn("Reader-consensus denominator", markdown)
        self.assertIn("Coverage denominator", markdown)
        self.assertIn("Two-axis crosstab", markdown)


class AxisQueueTests(AppCase, unittest.TestCase):
    def test_queue_exposes_axis_level_statuses_separately(self):
        records = [story("a"), story("b")]
        self.app.import_batch(batch(records, "two"))
        self.add_axis_codings([
            axis_coding("a", axis=INH, annotator="reader-a", value="wins", coding_id="a-i-a"),
            axis_coding("a", axis=INH, annotator="reader-b", value="wins", coding_id="a-i-b"),
            axis_coding("a", axis=STA, annotator="reader-a", value="tension", coding_id="a-s-a"),
        ])
        queue = self.app.axis_review_queue()
        rows = {row["story_id"]: row for row in queue["stories"]}
        self.assertEqual(rows["a"]["axis_status"], {INH: "agreed", STA: "insufficient"})
        self.assertEqual(rows["a"]["status"], "needs_more_reviews")
        self.assertEqual(rows["b"]["status"], "unreviewed")
        self.assertEqual(queue["by_status"]["needs_more_reviews"], 1)
        self.assertEqual(queue["by_status"]["unreviewed"], 1)

    def test_split_on_one_axis_marks_story_disputed(self):
        self.import_story()
        self.add_axis_codings([
            axis_coding(axis=STA, annotator="reader-a", value="tension", coding_id="s-a"),
            axis_coding(axis=STA, annotator="reader-b", value="no_tension", coding_id="s-b"),
        ])
        row = self.app.axis_review_queue()["stories"][0]
        self.assertEqual(row["status"], "disputed")
        self.assertEqual(row["axis_status"][STA], "split")
        self.assertEqual(row["axis_status"][INH], "insufficient")

    def test_adjudicated_story_is_flagged_while_axis_states_remain_visible(self):
        self.import_story()
        self.add_axis_codings([
            axis_coding(axis=INH, annotator="reader-a", value="wins", coding_id="i-a"),
            axis_coding(axis=INH, annotator="reader-b", value="loses", coding_id="i-b"),
        ])
        self.app.record_axis_adjudication(axis_adjudication(axis=INH, value="wins"))
        row = self.app.axis_review_queue()["stories"][0]
        self.assertEqual(row["status"], "adjudicated")
        self.assertEqual(row["axes"][INH]["final_value"], "wins")
        self.assertIsNone(row["axes"][STA]["adjudication_id"])


class AxisComparisonTests(AppCase, unittest.TestCase):
    def test_each_group_and_axis_carries_its_own_denominator(self):
        coast, hill = story("coast", tradition="coast"), story("hill", tradition="hill")
        self.app.import_batch(batch([coast, hill], "groups"))
        self.add_axis_codings([
            axis_coding("coast", axis=INH, annotator="reader-a", value="wins", coding_id="c-i-a"),
            axis_coding("coast", axis=INH, annotator="reader-b", value="wins", coding_id="c-i-b"),
            axis_coding("hill", axis=STA, annotator="reader-a", value="tension", coding_id="h-s-a"),
            axis_coding("hill", axis=STA, annotator="reader-b", value="tension", coding_id="h-s-b"),
        ])
        result = self.app.compare_traditions_by_axis()
        groups = {row["tradition"]: row for row in result["groups"]}
        self.assertEqual(groups["coast"]["axes"][INH]["consensus_denominator"], 1)
        self.assertEqual(groups["coast"]["axes"][STA]["consensus_denominator"], 0)
        self.assertEqual(groups["hill"]["axes"][STA]["consensus_rates"], {"tension": 1.0})
        self.assertIn("denominator", result["interpretation_limit"])


if __name__ == "__main__":
    unittest.main()
