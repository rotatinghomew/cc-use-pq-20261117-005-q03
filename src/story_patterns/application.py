from story_patterns.analysis.axis_report import AxisReportService
from story_patterns.analysis.report import ReportService
from story_patterns.catalog.service import CatalogService
from story_patterns.review.axis_service import AxisReviewService
from story_patterns.review.service import ReviewService
from story_patterns.storage import StoryStore


class StoryPatternApplication:
    """协调样本导入、证据审阅与可复现的本地汇总。"""

    def __init__(self, database: str):
        self.store = StoryStore(database)
        self.catalog = CatalogService(self.store)
        self.review = ReviewService(self.store)
        self.reports = ReportService(self.store)
        self.axis_review = AxisReviewService(self.store)
        self.axis_reports = AxisReportService(self.store)

    def import_batch(self, batch: dict) -> dict:
        return self.catalog.import_batch(batch)

    def record_decision(self, decision: dict) -> dict:
        return self.review.record_decision(decision)

    def create_report(self, tradition: str | None = None, minimum_reviewers: int = 2) -> dict:
        return self.reports.create(tradition, minimum_reviewers)

    def review_queue(self, minimum_reviewers: int = 2, tradition: str | None = None) -> dict:
        return self.review.queue(minimum_reviewers, tradition)

    def stored_report(self, report_id: str) -> dict | None:
        return self.reports.get(report_id)

    def preview_stories(self, rows: list[dict]) -> dict:
        return self.catalog.preview(rows)

    def revision_lineage(self) -> list[dict]:
        return self.catalog.lineage()

    def catalog_manifest(self) -> dict:
        return self.catalog.manifest()

    def record_adjudication(self, record: dict) -> dict:
        return self.review.record_adjudication(record)

    def compare_traditions(self, minimum_reviewers: int = 2) -> dict:
        return self.reports.compare(minimum_reviewers)

    def search_stories(self, **criteria) -> list[dict]:
        return self.catalog.search(**criteria)

    def review_history(self, story_id: str, revision: int) -> dict:
        return self.review.history(story_id, revision)

    def audit(self) -> dict:
        return self.catalog.audit()

    def record_axis_coding(self, coding: dict) -> dict:
        return self.axis_review.record_coding(coding)

    def record_axis_adjudication(self, record: dict) -> dict:
        return self.axis_review.record_adjudication(record)

    def axis_review_queue(self, minimum_reviewers: int = 2, tradition: str | None = None) -> dict:
        from story_patterns.analysis.cohorts import select_cohort, validate_minimum
        from story_patterns.review.axis_readiness import axis_queue_totals, build_axis_queue

        minimum = validate_minimum(minimum_reviewers)
        stories, codings, _origins, adjudications = self.store.axis_analysis_snapshot(tradition)
        rows = build_axis_queue(select_cohort(stories, tradition), codings, minimum, adjudications)
        return {"minimum_reviewers": minimum, "total": len(rows),
                "by_status": axis_queue_totals(rows), "stories": rows}

    def create_axis_report(self, tradition: str | None = None, minimum_reviewers: int = 2) -> dict:
        return self.axis_reports.create(tradition, minimum_reviewers)

    def stored_axis_report(self, report_id: str) -> dict | None:
        return self.axis_reports.get(report_id)

    def axis_history(self, story_id: str, revision: int) -> dict:
        return self.axis_review.history(story_id, revision)

    def compare_traditions_by_axis(self, minimum_reviewers: int = 2) -> dict:
        from story_patterns.analysis.axis_comparison import compare_traditions_by_axis
        from story_patterns.analysis.cohorts import validate_minimum

        minimum = validate_minimum(minimum_reviewers)
        stories, codings, _origins, adjudications = self.store.axis_analysis_snapshot(None)
        return compare_traditions_by_axis(stories, codings, minimum, adjudications)
