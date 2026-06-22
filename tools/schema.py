"""
Tool: validate_schema
Checks that each row contains all KNA1 fields (no extra, no missing keys).
Returns a structured report dict.
"""

import json
from config.schemas import KNA1_SCHEMA


def validate_schema(rows: list[dict]) -> dict:
    """
    Verify structural completeness: every row must have exactly the KNA1 fields.
    Returns counts and a list of per-row issues.
    """
    expected = set(KNA1_SCHEMA.keys()) | {"_injected_error"}
    issues = []

    for idx, row in enumerate(rows):
        row_keys = set(row.keys())
        missing = expected - row_keys - {"_injected_error"}
        extra   = row_keys - expected
        if missing or extra:
            issues.append({
                "row_index": idx,
                "kunnr": row.get("KUNNR", "?"),
                "missing_fields": sorted(missing),
                "extra_fields": sorted(extra),
            })

    return {
        "tool": "validate_schema",
        "total_rows": len(rows),
        "schema_ok": len(rows) - len(issues),
        "schema_issues": len(issues),
        "details": issues[:50],   # cap for readability
    }


# Tool definition for Claude tool_use
TOOL_DEF = {
    "name": "validate_schema",
    "description": (
        "Check that every row in the dataset has exactly the expected KNA1 fields. "
        "Returns counts of rows with missing or extra fields."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sample_rows": {
                "type": "array",
                "description": "A sample of rows (as JSON objects) to inspect for schema completeness.",
                "items": {"type": "object"},
            }
        },
        "required": ["sample_rows"],
    },
}


def run_tool(tool_input: dict, all_rows: list[dict]) -> str:
    result = validate_schema(all_rows)
    return json.dumps(result, indent=2)
