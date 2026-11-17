from __future__ import annotations

from story_patterns.catalog.validate import canonical_json, digest_json
from story_patterns.errors import ConflictError, NotFoundError
from story_patterns.review.axis_validate import normalize_axis_adjudication, normalize_axis_coding


class AxisReviewService:
    """按轴记录读者编码与编辑仲裁；两轴的状态、证据与序号完全独立。"""

    def __init__(self, store):
        self.store = store

    def record_coding(self, raw: dict) -> dict:
        story_id = raw.get("story_id") if isinstance(raw, dict) else None
        revision = raw.get("story_revision") if isinstance(raw, dict) else None
        story = self.store.story_document(story_id, revision)
        if story is None:
            raise NotFoundError(f"story revision {story_id!r}/{revision!r} was not found")
        coding = normalize_axis_coding(raw, story)
        digest = digest_json(coding)
        with self.store.transaction() as connection:
            previous = connection.execute(
                "SELECT digest FROM axis_codings WHERE coding_id = ?", (coding["coding_id"],)
            ).fetchone()
            if previous:
                if previous["digest"] != digest:
                    raise ConflictError(f"coding {coding['coding_id']} already identifies different content")
                return {"coding_id": coding["coding_id"], "status": "already_recorded"}
            reused = connection.execute(
                "SELECT coding_id FROM axis_codings WHERE story_id=? AND story_revision=? "
                "AND annotator=? AND axis=? AND sequence=?",
                (story_id, revision, coding["annotator"], coding["axis"], coding["sequence"]),
            ).fetchone()
            if reused:
                raise ConflictError("annotator sequence is already occupied for this story revision and axis")
            connection.execute(
                "INSERT INTO axis_codings(coding_id, story_id, story_revision, annotator, axis, sequence, "
                "value, evidence_event_ids, note, digest) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (coding["coding_id"], story_id, revision, coding["annotator"], coding["axis"],
                 coding["sequence"], coding["value"],
                 canonical_json(coding["evidence_event_ids"]), coding["note"], digest),
            )
        return {"coding_id": coding["coding_id"], "axis": coding["axis"], "status": "recorded"}

    def record_adjudication(self, raw: dict) -> dict:
        story_id = raw.get("story_id") if isinstance(raw, dict) else None
        revision = raw.get("story_revision") if isinstance(raw, dict) else None
        story = self.store.story_document(story_id, revision)
        if story is None:
            raise NotFoundError(f"story revision {story_id!r}/{revision!r} was not found")
        record = normalize_axis_adjudication(raw, story)
        digest = digest_json(record)
        with self.store.transaction() as connection:
            previous = connection.execute(
                "SELECT digest FROM axis_adjudications WHERE axis_adjudication_id=?",
                (record["axis_adjudication_id"],),
            ).fetchone()
            if previous:
                if previous["digest"] != digest:
                    raise ConflictError("axis adjudication identifier already refers to different content")
                return {"axis_adjudication_id": record["axis_adjudication_id"], "status": "already_recorded"}
            occupied = connection.execute(
                "SELECT axis_adjudication_id FROM axis_adjudications "
                "WHERE story_id=? AND story_revision=? AND axis=? AND sequence=?",
                (story_id, revision, record["axis"], record["sequence"]),
            ).fetchone()
            if occupied:
                raise ConflictError("adjudication sequence is already occupied for this story revision and axis")
            connection.execute(
                "INSERT INTO axis_adjudications(axis_adjudication_id, story_id, story_revision, moderator, "
                "axis, sequence, value, evidence_event_ids, rationale, digest) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (record["axis_adjudication_id"], story_id, revision, record["moderator"], record["axis"],
                 record["sequence"], record["value"],
                 canonical_json(record["evidence_event_ids"]), record["rationale"], digest),
            )
        return {"axis_adjudication_id": record["axis_adjudication_id"], "axis": record["axis"],
                "status": "recorded"}

    def codings_for(self, story_id: str, revision: int) -> dict[str, list[dict]]:
        return self.store.latest_axis_codings(story_id, revision)

    def history(self, story_id: str, revision: int) -> dict:
        if self.store.story_document(story_id, revision) is None:
            raise NotFoundError(f"story revision {story_id!r}/{revision!r} was not found")
        codings, adjudications = self.store.axis_history(story_id, revision)
        latest_by_reader_axis = {
            (item["annotator"], item["axis"]): item["sequence"] for item in codings
        }
        latest_by_axis = {}
        for item in adjudications:
            previous = latest_by_axis.get(item["axis"])
            if previous is None or item["sequence"] > previous:
                latest_by_axis[item["axis"]] = item["sequence"]
        for item in codings:
            item["current"] = latest_by_reader_axis[(item["annotator"], item["axis"])] == item["sequence"]
        for item in adjudications:
            item["current"] = latest_by_axis[item["axis"]] == item["sequence"]
        return {
            "story_id": story_id,
            "revision": revision,
            "axis_codings": codings,
            "axis_adjudications": adjudications,
            "active_axis_adjudication_ids": {
                axis: next(item["axis_adjudication_id"] for item in adjudications
                           if item["axis"] == axis and item["current"])
                for axis in latest_by_axis
            },
        }
