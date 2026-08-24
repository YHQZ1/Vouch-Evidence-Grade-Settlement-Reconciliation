"""Provider-independent model boundary for the bounded investigator."""

from __future__ import annotations

import threading
from typing import Protocol

from app.domain.investigation import InvestigationScope, ModelAction, ProviderProvenance


class ModelUnavailableError(RuntimeError):
    """The configured provider could not produce a response safely."""


class ModelTimeoutError(ModelUnavailableError):
    """The provider exceeded its fixed request or total budget."""


class ModelResponseError(ModelUnavailableError):
    """The provider response was too large, malformed, or schema-invalid."""


class ModelRequestTooLargeError(ModelUnavailableError):
    """The initial provider request exceeded the configured byte budget."""


class InvestigationModel(Protocol):
    """Minimal provider-independent action interface."""

    mode: str
    provider_provenance: ProviderProvenance
    configured_model_identifier: str | None

    def next_action(
        self,
        *,
        scope: InvestigationScope,
        tool_trace: tuple[dict[str, object], ...],
        available_tools: tuple[dict[str, object], ...],
        step_number: int,
        deadline_monotonic: float | None = None,
        cancel_event: threading.Event | None = None,
    ) -> ModelAction: ...


__all__ = [
    "InvestigationModel",
    "ModelResponseError",
    "ModelRequestTooLargeError",
    "ModelTimeoutError",
    "ModelUnavailableError",
]
