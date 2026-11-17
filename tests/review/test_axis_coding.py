import unittest

from story_patterns.errors import ConflictError, NotFoundError, ValidationError
from tests.support import AppCase, axis_adjudication, axis_coding, batch, story


class AxisCodingValidationTests(AppCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.import_story()

    def test_each_axis_accepts_its_own_vocabulary(self):
        self.app.record_axis_coding(axis_coding(axis="inheritance", value="wins"))
        self.app.record_axis_coding(axis_coding(axis="stance", value="tension",
                                                coding_id="stance-1", annotator="reader-b"))
        stored = self.app.axis_review.codings_for("tale-a", 1)
        self.assertEqual(set(stored), {"inheritance", "stance"})

    def test_unknown_axis_and_cross_axis_values_are_rejected(self):
        for record in [
            axis_coding(axis="pattern"),
            axis_coding(axis="stance", value="wins"),
            axis_coding(axis="inheritance", value="tension"),
        ]:
            with self.subTest(record=record):
                with self.assertRaises(ValidationError):
                    self.app.record_axis_coding(record)

    def test_abstentions_are_stored_per_axis(self):
        self.app.record_axis_coding(axis_coding(axis="inheritance", value="unknown",
                                                coding_id="inh-abs"))
        self.app.record_axis_coding(axis_coding(axis="stance", value="unclear",
                                                coding_id="sta-abs", annotator="reader-b"))
        stored = self.app.axis_review.codings_for("tale-a", 1)
        self.assertEqual(stored["inheritance"][0]["value"], "unknown")
        self.assertEqual(stored["stance"][0]["value"], "unclear")

    def test_evidence_is_required_and_must_reference_this_revision(self):
        for evidence in [[], ["missing"], ["first", "first"], ["first", 4]]:
            with self.subTest(evidence=evidence):
                with self.assertRaises(ValidationError):
                    self.app.record_axis_coding(axis_coding(evidence=evidence))

    def test_coding_idempotency_and_content_conflict(self):
        record = axis_coding(coding_id="stable-coding")
        self.assertEqual(self.app.record_axis_coding(record)["status"], "recorded")
        self.assertEqual(self.app.record_axis_coding(record)["status"], "already_recorded")
        altered = axis_coding(coding_id="stable-coding", value="loses")
        with self.assertRaises(ConflictError):
            self.app.record_axis_coding(altered)

    def test_sequence_occupancy_is_scoped_per_axis(self):
        self.app.record_axis_coding(axis_coding(axis="inheritance", sequence=1, coding_id="inh-1"))
        # 同一读者同序号但不同轴不冲突
        self.app.record_axis_coding(axis_coding(axis="stance", sequence=1, value="tension",
                                                coding_id="sta-1"))
        with self.assertRaises(ConflictError):
            self.app.record_axis_coding(axis_coding(axis="inheritance", sequence=1, coding_id="inh-other"))
        # 更大序号在同一轴上取代旧编码
        self.app.record_axis_coding(axis_coding(axis="inheritance", sequence=2, value="loses",
                                                coding_id="inh-2"))
        latest = self.app.axis_review.codings_for("tale-a", 1)["inheritance"]
        self.assertEqual(len(latest), 1)
        self.assertEqual(latest[0]["value"], "loses")

    def test_coding_requires_existing_story_revision(self):
        with self.assertRaises(NotFoundError):
            self.app.record_axis_coding(axis_coding(story_id="missing"))

    def test_revision_isolation_keeps_axes_separate(self):
        revised = story(revision=2)
        self.app.import_batch(batch([revised], "revision-two"))
        self.app.record_axis_coding(axis_coding(revision=1, coding_id="r1"))
        self.app.record_axis_coding(axis_coding(revision=2, coding_id="r2"))
        self.assertEqual(len(self.app.axis_review.codings_for("tale-a", 1)["inheritance"]), 1)
        self.assertEqual(len(self.app.axis_review.codings_for("tale-a", 2)["inheritance"]), 1)

    def test_reader_can_finish_one_axis_without_the_other(self):
        self.app.record_axis_coding(axis_coding(axis="inheritance", annotator="reader-a"))
        view = self.app.axis_review.codings_for("tale-a", 1)
        self.assertIn("inheritance", view)
        self.assertNotIn("stance", view)


class AxisAdjudicationTests(AppCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.import_story()

    def test_adjudication_is_recorded_per_axis_and_keeps_independent_evidence(self):
        result = self.app.record_axis_adjudication(axis_adjudication(axis="stance", value="tension"))
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["axis"], "stance")
        history = self.app.axis_history("tale-a", 1)
        self.assertEqual(history["active_axis_adjudication_ids"], {"stance": "tale-a-stance-adj-1"})
        self.assertEqual(history["axis_codings"], [])

    def test_adjudication_rejects_abstentions(self):
        for axis, value in [("inheritance", "unknown"), ("stance", "unclear")]:
            with self.subTest(axis=axis):
                with self.assertRaises(ValidationError):
                    self.app.record_axis_adjudication(axis_adjudication(axis=axis, value=value))

    def test_one_axis_adjudication_does_not_create_state_for_the_other(self):
        self.app.record_axis_adjudication(axis_adjudication(axis="inheritance", value="wins"))
        report = self.app.create_axis_report()
        row = report["story_results"][0]
        self.assertEqual(row["axes"]["inheritance"]["adjudication_id"], "tale-a-inheritance-adj-1")
        self.assertIsNone(row["axes"]["stance"]["adjudication_id"])
        self.assertEqual(row["axes_with_adjudication"], ["inheritance"])

    def test_later_axis_adjudication_supersedes_without_deleting(self):
        self.app.record_axis_adjudication(axis_adjudication(sequence=1, value="wins",
                                                            record_id="adj-1"))
        self.app.record_axis_adjudication(axis_adjudication(sequence=2, value="mixed",
                                                            record_id="adj-2"))
        history = self.app.axis_history("tale-a", 1)
        self.assertEqual([item["axis_adjudication_id"] for item in history["axis_adjudications"]],
                         ["adj-1", "adj-2"])
        self.assertEqual(history["active_axis_adjudication_ids"], {"inheritance": "adj-2"})

    def test_axis_adjudication_requires_rationale_and_real_events(self):
        for record in [
            axis_adjudication(evidence=[]),
            axis_adjudication(evidence=["ghost"]),
            axis_adjudication(rationale=" "),
        ]:
            with self.subTest():
                with self.assertRaises(ValidationError):
                    self.app.record_axis_adjudication(record)

    def test_axis_history_unknown_story_raises(self):
        with self.assertRaises(NotFoundError):
            self.app.axis_history("absent", 1)


if __name__ == "__main__":
    unittest.main()
