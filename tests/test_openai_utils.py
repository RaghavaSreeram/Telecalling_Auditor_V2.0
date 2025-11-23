import pytest
from backend.openai_utils import parse_and_validate_analysis


def test_parse_valid_json():
    raw = '{"agent_id":"AG1","customer_id":"C1","call_start_time":"2025-01-01T00:00:00Z","call_duration_seconds":120,"script_followed":true,"lead_qualified":true,"site_visit_confirmed":false,"sentiment":"positive","overall_score":85}'
    analysis, parsed, errors = parse_and_validate_analysis(raw)
    assert parsed is True
    assert errors == []
    assert analysis["agent_id"] == "AG1"


def test_parse_malformed_json_returns_fallback():
    # missing closing brace
    raw = '{"agent_id":"AG1","customer_id":"C1","call_start_time":"2025-01-01T00:00:00Z","call_duration_seconds":120'
    analysis, parsed, errors = parse_and_validate_analysis(raw, context={"agent_number": "AG1"})
    assert parsed is False
    assert "Failed to parse JSON" in errors[0] or len(errors) > 0
    assert analysis.get("_parsed") is False
    assert analysis.get("agent_id") == "AG1"


def test_parse_wrong_schema_returns_validation_error():
    # JSON present but missing required fields
    raw = '{"agent_id":"AG1","customer_id":"C1","call_start_time":"2025-01-01T00:00:00Z","script_followed":true}'
    analysis, parsed, errors = parse_and_validate_analysis(raw)
    assert parsed is False
    assert any("Schema validation error" in e for e in errors)
    assert analysis.get("_parsed") is False
