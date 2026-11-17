from __future__ import annotations

from story_patterns.axes import adjudication_labels, axis_labels, validate_axis
from story_patterns.catalog.validate import _text
from story_patterns.errors import ValidationError


def _validate_evidence(raw: dict, story: dict, field: str) -> list[str]:
    evidence_ids = raw.get("evidence_event_ids")
    known = {event["event_id"] for event in story["events"]}
    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise ValidationError("at least one evidence event is required")
    if any(not isinstance(item, str) or item not in known for item in evidence_ids):
        raise ValidationError(f"{field} evidence_event_ids must refer to events in this revision")
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValidationError("evidence_event_ids cannot repeat")
    return sorted(evidence_ids)


def normalize_axis_coding(raw: dict, story: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValidationError("axis coding must be an object")
    coding_id = _text(raw.get("coding_id"), "coding_id", 120)
    annotator = _text(raw.get("annotator"), "annotator", 120)
    axis = validate_axis(raw.get("axis"))
    sequence = raw.get("sequence")
    if type(sequence) is not int or sequence < 1:
        raise ValidationError("sequence must be a positive integer")
    value = raw.get("value")
    if value not in axis_labels(axis):
        raise ValidationError(f"value must be one of: {', '.join(axis_labels(axis))}")
    evidence = _validate_evidence(raw, story, "coding")
    note = raw.get("note", "")
    if not isinstance(note, str) or len(note) > 1000:
        raise ValidationError("note must be text of at most 1000 characters")
    return {
        "coding_id": coding_id,
        "story_id": story["story_id"],
        "story_revision": story["revision"],
        "annotator": annotator,
        "axis": axis,
        "sequence": sequence,
        "value": value,
        "evidence_event_ids": evidence,
        "note": note.strip(),
    }


def normalize_axis_adjudication(raw: dict, story: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValidationError("axis adjudication must be an object")
    record_id = _text(raw.get("axis_adjudication_id"), "axis_adjudication_id", 120)
    moderator = _text(raw.get("moderator"), "moderator", 120)
    axis = validate_axis(raw.get("axis"))
    sequence = raw.get("sequence")
    if type(sequence) is not int or sequence < 1:
        raise ValidationError("sequence must be a positive integer")
    value = raw.get("value")
    if value not in adjudication_labels(axis):
        raise ValidationError(
            f"an adjudicated value must be one of: {', '.join(adjudication_labels(axis))} "
            "(abstentions cannot be adjudicated)"
        )
    evidence = _validate_evidence(raw, story, "adjudication")
    rationale = _text(raw.get("rationale"), "rationale", 1500)
    return {
        "axis_adjudication_id": record_id,
        "story_id": story["story_id"],
        "story_revision": story["revision"],
        "moderator": moderator,
        "axis": axis,
        "sequence": sequence,
        "value": value,
        "evidence_event_ids": evidence,
        "rationale": rationale,
    }
