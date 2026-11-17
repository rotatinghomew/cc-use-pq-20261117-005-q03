import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from story_patterns.cli import main
from tests.support import AppCase, axis_adjudication, axis_coding, batch, story


class AxisCliWorkflowTests(AppCase, unittest.TestCase):
    def _write(self, directory: str, name: str, payload: dict) -> str:
        path = Path(directory) / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def test_code_axis_report_and_export_round_trip(self):
        self.import_story()
        with tempfile.TemporaryDirectory() as directory:
            coding_file = self._write(directory, "coding.json", axis_coding())
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["code", "--database", self.database, "--file", coding_file])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "recorded")

            report_stdout = io.StringIO()
            with contextlib.redirect_stdout(report_stdout):
                code = main(["axis-report", "--database", self.database])
            report = json.loads(report_stdout.getvalue())
            report_id = report["report_id"]

            for fmt, filename in [("json", "axis.json"), ("csv", "axis.csv"), ("md", "axis.md")]:
                output = str(Path(directory) / filename)
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main(["axis-export", "--database", self.database,
                                 "--report-id", report_id, "--format", fmt, "--output", output])
                self.assertEqual(code, 0)
                self.assertTrue(Path(output).exists())

    def test_axis_queue_and_history_commands(self):
        self.import_story()
        self.app.record_axis_coding(axis_coding(axis="stance", value="tension", coding_id="s1"))
        with tempfile.TemporaryDirectory() as directory:
            adjudication_file = self._write(
                directory, "adj.json", axis_adjudication(axis="stance", value="tension")
            )
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(["adjudicate-axis", "--database", self.database,
                          "--file", adjudication_file]), 0
                )
            queue_buffer, history_buffer = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(queue_buffer):
                main(["axis-queue", "--database", self.database])
            with contextlib.redirect_stdout(history_buffer):
                main(["axis-history", "--database", self.database,
                      "--story-id", "tale-a", "--revision", "1"])
        queue_payload = json.loads(queue_buffer.getvalue())
        self.assertEqual(queue_payload["stories"][0]["status"], "adjudicated")
        history_payload = json.loads(history_buffer.getvalue())
        self.assertEqual(history_payload["active_axis_adjudication_ids"],
                         {"stance": "tale-a-stance-adj-1"})

    def test_axis_compare_command_reports_per_axis_denominators(self):
        self.app.import_batch(batch([story("a", tradition="coast"),
                                     story("b", tradition="hill")], "groups"))
        self.app.record_axis_coding(axis_coding("a", axis="inheritance",
                                                annotator="reader-a", coding_id="a-i-a"))
        self.app.record_axis_coding(axis_coding("a", axis="inheritance",
                                                annotator="reader-b", coding_id="a-i-b"))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["axis-compare", "--database", self.database])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        groups = {row["tradition"]: row for row in payload["groups"]}
        self.assertEqual(groups["coast"]["axes"]["inheritance"]["consensus_denominator"], 1)
        self.assertEqual(groups["hill"]["axes"]["inheritance"]["consensus_denominator"], 0)

    def test_unknown_axis_report_export_is_domain_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = main(["axis-export", "--database", self.database, "--report-id", "nope",
                         "--format", "json", "--output", "/tmp/unused.json"])
        self.assertEqual(code, 2)
        self.assertIn("error", json.loads(stderr.getvalue()))


class AxisAuditTests(AppCase, unittest.TestCase):
    def test_audit_covers_axis_tables_and_reports(self):
        self.import_story()
        self.app.record_axis_coding(axis_coding())
        self.app.record_axis_adjudication(axis_adjudication())
        self.app.create_axis_report()
        result = self.app.audit()
        self.assertTrue(result["ok"])
        self.assertEqual(result["axis_codings_checked"], 1)
        self.assertEqual(result["axis_adjudications_checked"], 1)
        self.assertEqual(result["axis_reports_checked"], 1)

    def test_audit_flags_tampered_axis_report(self):
        self.import_story()
        self.app.record_axis_coding(axis_coding())
        self.app.create_axis_report()
        with self.app.store.transaction() as connection:
            connection.execute("UPDATE axis_reports SET document='{}'")
        result = self.app.audit()
        self.assertFalse(result["ok"])
        self.assertTrue(any(item["scope"] == "axis_report" for item in result["issues"]))

    def test_audit_flags_tampered_axis_coding_digest(self):
        self.import_story()
        self.app.record_axis_coding(axis_coding())
        with self.app.store.transaction() as connection:
            connection.execute("UPDATE axis_codings SET value='loses'")
        result = self.app.audit()
        self.assertFalse(result["ok"])
        self.assertTrue(any(item["scope"] == "axis_coding" for item in result["issues"]))

    def test_reopened_application_preserves_axis_state(self):
        self.import_story()
        self.app.record_axis_coding(axis_coding())
        report = self.app.create_axis_report()
        reopened = type(self.app)(self.database)
        self.assertEqual(reopened.stored_axis_report(report["report_id"])["report_id"],
                         report["report_id"])
        self.assertEqual(reopened.axis_review.codings_for("tale-a", 1)["inheritance"][0]["value"],
                         "wins")


if __name__ == "__main__":
    unittest.main()
