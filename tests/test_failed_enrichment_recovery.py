"""When any individual enrichment worker crashes, every input still gets a terminal envelope."""
from scripts.run_competition_batch import recover_failed_profile
from norway_company_agent.batch import terminal_envelope, validate_envelopes


def test_worker_crash_preserves_identity_and_reports_missing_sources():
    profile = {
        "organisation_number": "985589003",
        "name": "SIMULATED AS",
        "evidence": {
            "registry": {"status": "available", "retrieved_at": "2026-10-10T00:00:00Z"},
            "accounting_obligation": {"status": "available", "retrieved_at": "2026-10-10T00:00:00Z"},
        },
    }
    requested = ["registry", "accounting_obligation", "financials", "roles", "website"]
    result, metric = recover_failed_profile(profile, requested, TimeoutError("private url should not leak"))
    assert result["organisation_number"] == "985589003"
    assert result["evidence"]["registry"]["status"] == "available"
    assert result["evidence"]["financials"]["status"] == "source_error"
    assert result["evidence"]["website"]["status"] == "source_error"
    assert "private url" not in result["evidence"]["website"]["note"]
    assert metric["partial_accounting"]
    env = terminal_envelope(result, run_id="unit", modules=requested,
                            started_at="2026-10-10T00:00:00Z", completed_at="2026-10-10T00:00:01Z")
    assert env["modules"]["financials"]["state"] == "source_error"
    check = validate_envelopes([env], 1)
    assert check["passed"]
    assert check["checks"]["zero_silent_drops"]


def test_worker_crash_does_not_overwrite_successful_module():
    profile = {
        "organisation_number": "985589003",
        "evidence": {"registry": {"status": "available"},
                     "financials": {"status": "available", "value": {"revenue": 100}}},
    }
    out, _ = recover_failed_profile(profile, ["registry", "financials", "website"], RuntimeError("timeout"))
    assert out["evidence"]["financials"]["value"]["revenue"] == 100
    assert out["evidence"]["website"]["status"] == "source_error"
