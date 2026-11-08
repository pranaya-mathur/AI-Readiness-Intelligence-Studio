"""Validate and normalize finding-to-evidence relationships."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any


def index_assessment_evidence(
    evidence_items: Sequence[dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in evidence_items or []:
        eid = item.get("evidence_id")
        if eid:
            index[str(eid)] = item
    return index


def validate_evidence_refs(
    *,
    evidence_refs: Iterable[Any] | None,
    evidence_index: dict[str, dict[str, Any]],
    claimed_source_file: str | None = None,
) -> list[str]:
    """
    Keep only evidence IDs that exist in this assessment's evidence package.
    When a source file is claimed, require the cited evidence to match that file.
    """
    valid: list[str] = []
    seen: set[str] = set()
    for raw in evidence_refs or []:
        eid = str(raw).strip()
        if not eid or eid in seen:
            continue
        item = evidence_index.get(eid)
        if not item:
            continue
        if claimed_source_file:
            source = (item.get("source_file") or "").strip()
            if source and source != claimed_source_file.strip():
                continue
        seen.add(eid)
        valid.append(eid)
    return valid


def enrich_finding_with_validated_refs(
    finding: dict[str, Any],
    evidence_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return a shallow copy with validated evidence_refs only."""
    out = dict(finding)
    claimed_file = out.get("source_file")
    out["evidence_refs"] = validate_evidence_refs(
        evidence_refs=out.get("evidence_refs") or [],
        evidence_index=evidence_index,
        claimed_source_file=claimed_file if isinstance(claimed_file, str) else None,
    )
    return out
