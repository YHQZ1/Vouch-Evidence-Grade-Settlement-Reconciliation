from types import SimpleNamespace

import pytest

from app.application.investigation_model import ModelRequestTooLargeError
from app.infrastructure.investigation_model import OllamaInvestigationModel


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://localhost:11434",
        "https://127.0.0.1:11434",
        "http://127.0.0.1:bad",
        "http://127.0.0.1:11434/path",
        "http://127.0.0.1:11434?proxy=1",
        "http://user:pass@127.0.0.1:11434",
        "http://192.0.2.1:11434",
    ],
)
def test_ollama_endpoint_requires_credential_free_loopback_ip_literal(endpoint):
    with pytest.raises(ValueError):
        OllamaInvestigationModel(
            endpoint=endpoint,
            model="test-model",
            connect_timeout_ms=10,
            read_timeout_ms=10,
            max_response_bytes=1024,
            max_request_bytes=1024,
            max_tokens=8,
        )


def test_ollama_rejects_initial_prompt_before_connection():
    model = OllamaInvestigationModel(
        endpoint="http://127.0.0.1:11434",
        model="test-model",
        connect_timeout_ms=10,
        read_timeout_ms=10,
        max_response_bytes=1024,
        max_request_bytes=1,
        max_tokens=8,
    )
    scope = SimpleNamespace(
        settlement_id="set-1",
        settlement=SimpleNamespace(
            state=SimpleNamespace(value="needs_review"), reason_codes=()
        ),
        aggregate=SimpleNamespace(model_dump=lambda mode: {}),
        candidate_bank_source_record_ids=(),
    )
    with pytest.raises(ModelRequestTooLargeError, match="request exceeded"):
        model.next_action(
            scope=scope,
            tool_trace=(),
            available_tools=(),
            step_number=1,
        )
