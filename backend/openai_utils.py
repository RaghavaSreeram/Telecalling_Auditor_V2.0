import json
import re
from typing import Tuple, Dict, Any, List, Optional
from jsonschema import validate, ValidationError

# JSON schema for expected analysis output (partial, focused on required top-level fields)
ANALYSIS_JSON_SCHEMA = {
    "type": "object",
    "required": [
        "agent_id",
        "customer_id",
        "call_start_time",
        "call_duration_seconds",
        "script_followed",
        "lead_qualified",
        "site_visit_confirmed",
        "sentiment",
        "overall_score"
    ],
    "properties": {
        "agent_id": {"type": "string"},
        "customer_id": {"type": "string"},
        "call_start_time": {"type": "string"},
        "call_duration_seconds": {"type": "number"},
        "script_followed": {"type": "boolean"},
        "lead_qualified": {"type": "boolean"},
        "site_visit_confirmed": {"type": "boolean"},
        "sentiment": {"type": "string"},
        "overall_score": {"type": ["number", "integer"]}
    }
}


def _try_load_json_candidates(raw: str) -> Optional[Dict[str, Any]]:
    """Try to extract JSON object(s) from raw text and parse them."""
    # First try direct load
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Try to find JSON object-like substrings
    candidates = re.findall(r"\{(?:.|\n)*?\}", raw)
    for c in candidates:
        try:
            return json.loads(c)
        except Exception:
            continue

    return None


def parse_and_validate_analysis(raw_text: str, context: Dict[str, Any] = None) -> Tuple[Dict[str, Any], bool, List[str]]:
    """
    Parse raw model output into JSON and validate against schema.
    Returns (analysis_dict, parsed_bool, validation_errors)
    If parsing/validation fails, returns a fallback analysis (filled from context when possible), parsed_bool=False, and a list of errors.
    """
    errors: List[str] = []
    context = context or {}

    parsed = False
    analysis = None

    parsed_json = _try_load_json_candidates(raw_text)
    if parsed_json is None:
        errors.append("Failed to parse JSON from model output")
    else:
        # Validate against schema
        try:
            validate(instance=parsed_json, schema=ANALYSIS_JSON_SCHEMA)
            analysis = parsed_json
            parsed = True
        except ValidationError as ve:
            errors.append(f"Schema validation error: {ve.message}")
            # still keep the parsed JSON as partial
            analysis = parsed_json

    if not analysis:
        # Build a minimal fallback analysis using context where available
        analysis = {
            "agent_id": context.get("agent_number") or context.get("agent_id") or "",
            "customer_id": context.get("customer_number") or context.get("customer_id") or "",
            "call_start_time": context.get("call_date") if context and isinstance(context.get("call_date"), str) else context.get("call_date_iso") if context else None,
            "call_duration_seconds": None,
            "script_followed": False,
            "lead_qualified": False,
            "site_visit_confirmed": False,
            "sentiment": "neutral",
            "remarks": raw_text[:1000],
            "overall_score": 0,
            # keep room for other fields expected by UI
            "script_adherence_score": 0,
            "communication_score": 0,
            "outcome_achieved": False,
            "lead_status": "not_interested",
            "script_adherence_details": {"followed_points": [], "missed_points": [], "deviations": ""},
            "communication_analysis": {"tone": "neutral", "clarity": 0, "listening_skills": 0, "objection_handling": 0},
            "strengths": [],
            "areas_for_improvement": [],
            "summary": raw_text[:2000],
            "performance_metrics": {"script_adherence_rate": 0, "lead_qualification_rate": 0, "site_visit_conversion_rate": 0, "sentiment_positive_rate": 0}
        }

    # Attach raw and validation errors when not fully parsed/valid
    if not parsed:
        analysis["_raw_output"] = raw_text
        analysis["_parsed"] = False
        analysis["_validation_errors"] = errors
    else:
        analysis["_parsed"] = True

    return analysis, parsed, errors
