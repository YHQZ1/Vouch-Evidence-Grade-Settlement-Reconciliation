"""Deterministic materiality and batch close-readiness policy."""

from __future__ import annotations

from app.domain import ClosePolicy


def is_material(value_subunits: int, policy: ClosePolicy, batch_total_abs: int) -> bool:
    absolute = abs(value_subunits) >= policy.materiality_absolute_subunits
    relative = (
        policy.materiality_relative_bps is not None
        and abs(value_subunits) * 10_000
        >= batch_total_abs * policy.materiality_relative_bps
    )
    return absolute or relative


__all__ = ["is_material"]
