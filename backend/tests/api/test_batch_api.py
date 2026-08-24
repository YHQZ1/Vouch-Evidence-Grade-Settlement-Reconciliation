from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from app.application.batch_workflow import (
    BatchWorkflowService,
    InMemoryBatchRepository,
)
from app.application.reconciliation import ReconciliationService
from app.core.config import Settings
from app.domain.common import SourceKind
from app.main import create_app

ROOT = Path(__file__).parents[3]
DEMO = ROOT / "data/demonstration/inputs"
CLOCK = "2026-08-31T18:30:00Z"


def _client(**settings) -> TestClient:
    return TestClient(create_app(Settings(environment="test", **settings)))


def _batch(client: TestClient) -> str:
    response = client.post("/api/v1/batches", json={"evaluation_clock": CLOCK})
    assert response.status_code == 201
    return response.json()["batch_id"]


def _upload_all(client: TestClient, batch_id: str) -> None:
    sources = (
        ("gateway", "razorpay_recon.csv", "text/csv"),
        ("bank", "bank_statement.csv", "text/csv"),
        ("ledger", "general_ledger.csv", "text/csv"),
        ("policy", "batch_policy.json", "application/json"),
    )
    for kind, filename, content_type in sources:
        response = client.put(
            f"/api/v1/batches/{batch_id}/sources/{kind}",
            content=(DEMO / filename).read_bytes(),
            headers={
                "content-type": content_type,
                "x-source-filename": filename,
            },
        )
        assert response.status_code in {200, 201}


def test_health_contract_is_unchanged() -> None:
    response = _client().get("/healthz")
    assert response.status_code == 200
    assert response.json() == {
        "service": "vouch-backend",
        "status": "ok",
        "api_version": "v1",
    }


def test_demo_lifecycle_matches_direct_reconciliation_result() -> None:
    client = _client()
    batch_id = _batch(client)
    _upload_all(client, batch_id)

    run = client.post(f"/api/v1/batches/{batch_id}/reconciliation-runs")
    assert run.status_code == 200
    assert run.json()["status"] == "completed"
    assert run.json()["result_available"] is True

    direct = ReconciliationService().reconcile(
        gateway_path=DEMO / "razorpay_recon.csv",
        bank_path=DEMO / "bank_statement.csv",
        ledger_path=DEMO / "general_ledger.csv",
        policy_path=DEMO / "batch_policy.json",
        evaluation_clock=CLOCK,
    )
    result = client.get(f"/api/v1/batches/{batch_id}/result")
    assert result.status_code == 200
    assert result.json() == direct.model_dump(mode="json")
    assert result.json()["evaluation_clock"] == CLOCK
    assert result.json()["close_readiness"]["readiness"] == "BLOCKED"

    repeated = client.post(f"/api/v1/batches/{batch_id}/reconciliation-runs")
    assert repeated.status_code == 200
    assert repeated.json()["result_batch_id"] == result.json()["batch_id"]


def test_upload_idempotency_conflict_and_source_immutability() -> None:
    client = _client()
    batch_id = _batch(client)
    payload = (DEMO / "razorpay_recon.csv").read_bytes()
    headers = {
        "content-type": "text/csv",
        "x-source-filename": "razorpay_recon.csv",
    }
    first = client.put(
        f"/api/v1/batches/{batch_id}/sources/gateway",
        content=payload,
        headers=headers,
    )
    retry = client.put(
        f"/api/v1/batches/{batch_id}/sources/gateway",
        content=payload,
        headers=headers,
    )
    conflict = client.put(
        f"/api/v1/batches/{batch_id}/sources/gateway",
        content=payload + b"\n",
        headers=headers,
    )
    assert first.status_code == 201
    assert retry.status_code == 200
    assert retry.json()["idempotent"] is True
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "SOURCE_CONFLICT"

    _upload_all(client, batch_id)
    assert (
        client.post(f"/api/v1/batches/{batch_id}/reconciliation-runs").status_code
        == 200
    )
    after_run = client.put(
        f"/api/v1/batches/{batch_id}/sources/gateway",
        content=payload,
        headers=headers,
    )
    assert after_run.status_code == 409
    assert after_run.json()["error"]["code"] == "SOURCES_IMMUTABLE"


def test_upload_and_lifecycle_validation_errors_are_stable() -> None:
    client = _client(max_upload_bytes=32)
    batch_id = _batch(client)
    cases = (
        ("text/plain", b"x", 415, "UNSUPPORTED_CONTENT_TYPE"),
        ("text/csv", b"\xff\xfe", 422, "INVALID_SOURCE"),
        ("text/csv", b"not,a,supported,header\n", 422, "INVALID_SOURCE"),
        ("text/csv", b"x" * 33, 413, "UPLOAD_TOO_LARGE"),
    )
    for content_type, payload, status, code in cases:
        response = client.put(
            f"/api/v1/batches/{batch_id}/sources/bank",
            content=payload,
            headers={"content-type": content_type},
        )
        assert response.status_code == status
        assert response.json()["error"]["code"] == code
        assert set(response.json()) == {"error"}
        assert set(response.json()["error"]) == {"code", "message", "details"}

    malformed_policy = client.put(
        f"/api/v1/batches/{batch_id}/sources/policy",
        content=b"{",
        headers={"content-type": "application/json"},
    )
    assert malformed_policy.status_code == 422
    assert malformed_policy.json()["error"]["code"] == "INVALID_SOURCE"
    unsupported_kind = client.put(
        f"/api/v1/batches/{batch_id}/sources/other",
        content=b"x",
        headers={"content-type": "text/csv"},
    )
    assert unsupported_kind.status_code == 422
    assert unsupported_kind.json()["error"]["code"] == "UNSUPPORTED_SOURCE_KIND"

    missing = client.post(f"/api/v1/batches/{batch_id}/reconciliation-runs")
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "BATCH_INCOMPLETE"
    invalid_request = client.post("/api/v1/batches", json={"evaluation_clock": "naive"})
    assert invalid_request.status_code == 422
    assert invalid_request.json()["error"]["code"] == "INVALID_REQUEST"


def test_unknown_ids_and_pagination_exports_are_deterministic() -> None:
    client = _client()
    batch_id = _batch(client)
    assert client.get("/api/v1/batches/does-not-exist").status_code == 404
    _upload_all(client, batch_id)
    client.post(f"/api/v1/batches/{batch_id}/reconciliation-runs")
    unknown = client.get(f"/api/v1/batches/{batch_id}/settlements/nope")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "SETTLEMENT_NOT_FOUND"

    first_page = client.get(f"/api/v1/batches/{batch_id}/settlements?limit=3")
    second_page = client.get(f"/api/v1/batches/{batch_id}/settlements?offset=3&limit=3")
    assert first_page.status_code == second_page.status_code == 200
    assert first_page.json()["total"] == 12
    assert first_page.json()["next_offset"] == 3
    assert second_page.json()["next_offset"] == 6
    assert [
        item["aggregate"]["settlement_id"] for item in first_page.json()["items"]
    ] == sorted(
        item["aggregate"]["settlement_id"] for item in first_page.json()["items"]
    )
    boundary = client.get(f"/api/v1/batches/{batch_id}/settlements?offset=12&limit=3")
    assert boundary.status_code == 200
    assert boundary.json()["items"] == []
    assert (
        client.get(f"/api/v1/batches/{batch_id}/settlements?limit=101").status_code
        == 422
    )

    small_client = _client(max_page_size=2)
    small_batch_id = _batch(small_client)
    _upload_all(small_client, small_batch_id)
    small_client.post(f"/api/v1/batches/{small_batch_id}/reconciliation-runs")
    default_page = small_client.get(f"/api/v1/batches/{small_batch_id}/settlements")
    assert default_page.status_code == 200
    assert default_page.json()["limit"] == 2
    assert (
        small_client.get(
            f"/api/v1/batches/{small_batch_id}/settlements?limit=3"
        ).status_code
        == 422
    )

    for artifact in ("reconciliation-result", "exceptions", "audit-events"):
        first = client.get(f"/api/v1/batches/{batch_id}/exports/{artifact}")
        second = client.get(f"/api/v1/batches/{batch_id}/exports/{artifact}")
        assert first.status_code == second.status_code == 200
        assert first.content == second.content
        assert first.headers["content-type"] == "application/json"
        assert 'attachment; filename="vouch-' in first.headers["content-disposition"]
        assert (
            "/"
            not in first.headers["content-disposition"]
            .split('filename="', 1)[1]
            .split('"', 1)[0]
        )
        json.loads(first.content)


def test_openapi_declares_upload_successes_and_common_error_envelopes() -> None:
    schema = _client().app.openapi()
    upload = schema["paths"]["/api/v1/batches/{batch_id}/sources/{source_kind}"]["put"]
    assert {"200", "201"} <= set(upload["responses"])
    assert upload["responses"]["201"]["content"]
    assert upload["responses"]["409"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/ErrorEnvelope")


def test_openapi_declares_export_media_types_and_actual_payload_shapes() -> None:
    schema = _client().app.openapi()
    expected = {
        "/api/v1/batches/{batch_id}/exports/reconciliation-result": "BatchResult",
        "/api/v1/batches/{batch_id}/exports/exceptions": "ExceptionExportResponse",
        "/api/v1/batches/{batch_id}/exports/audit-events": "AuditEventExportResponse",
    }
    for path, model_name in expected.items():
        response = schema["paths"][path]["get"]["responses"]["200"]
        content = response["content"]["application/json"]
        assert content["schema"]["$ref"].endswith(f"/{model_name}")
    result = schema["paths"]["/api/v1/batches/{batch_id}/result"]["get"]
    assert result["responses"]["404"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/ErrorEnvelope")


def test_openapi_declares_phase8_operations_and_error_envelopes() -> None:
    schema = _client().app.openapi()
    operations = {
        (
            "post",
            "/api/v1/batches/{batch_id}/settlements/{settlement_id}/investigations",
        ): "runInvestigation",
        (
            "get",
            "/api/v1/batches/{batch_id}/settlements/{settlement_id}/investigations",
        ): "listSettlementInvestigations",
        ("get", "/api/v1/batches/{batch_id}/investigations"): "listBatchInvestigations",
        (
            "get",
            "/api/v1/batches/{batch_id}/settlements/{settlement_id}/investigations/eligibility",
        ): "getInvestigationEligibility",
        (
            "get",
            "/api/v1/batches/{batch_id}/settlements/{settlement_id}/effective-review",
        ): "getEffectiveReview",
        ("get", "/api/v1/batches/{batch_id}/effective-review"): "listEffectiveReviews",
        (
            "get",
            "/api/v1/batches/{batch_id}/exports/investigations",
        ): "exportInvestigations",
    }
    for (method, path), operation_id in operations.items():
        operation = schema["paths"][path][method]
        assert operation["operationId"] == operation_id
        assert "200" in operation["responses"]
        assert any(
            response.get("content", {})
            .get("application/json", {})
            .get("schema", {})
            .get("$ref", "")
            .endswith("/ErrorEnvelope")
            for response in operation["responses"].values()
        )


def test_concurrent_source_uploads_receive_unique_lifecycle_sequences() -> None:
    workflow = BatchWorkflowService(InMemoryBatchRepository())
    batch = workflow.create_batch(CLOCK)
    sources = (
        (SourceKind.GATEWAY, "razorpay_recon.csv", "text/csv"),
        (SourceKind.BANK, "bank_statement.csv", "text/csv"),
        (SourceKind.LEDGER, "general_ledger.csv", "text/csv"),
        (SourceKind.POLICY, "batch_policy.json", "application/json"),
    )

    def upload(item):
        kind, filename, content_type = item
        return workflow.upload_source(
            batch.batch_id,
            kind,
            filename=filename,
            content_type=content_type,
            payload=(DEMO / filename).read_bytes(),
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(upload, sources))

    snapshot = workflow.repository.get(batch.batch_id)
    assert snapshot.status == "ready"
    assert sorted(source.sequence for source in snapshot.sources) == [2, 3, 4, 5]


def test_failed_run_has_no_partial_result_and_instances_are_isolated() -> None:
    class BrokenService:
        def reconcile(self, **_kwargs):
            raise RuntimeError("internal path and labels must not escape")

    workflow = BatchWorkflowService(InMemoryBatchRepository(), BrokenService())
    first = TestClient(create_app(Settings(environment="test"), workflow=workflow))
    batch_id = _batch(first)
    _upload_all(first, batch_id)
    run = first.post(f"/api/v1/batches/{batch_id}/reconciliation-runs")
    assert run.status_code == 200
    assert run.json()["status"] == "failed"
    assert run.json()["failure"] == {
        "code": "RECONCILIATION_FAILED",
        "message": "reconciliation failed; no result is available",
        "sequence": 7,
    }
    result = first.get(f"/api/v1/batches/{batch_id}/result")
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "RESULT_UNAVAILABLE"
    assert "internal path" not in result.text

    second = _client()
    assert second.get(f"/api/v1/batches/{batch_id}").status_code == 404
