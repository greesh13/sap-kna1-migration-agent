"""
Tool: validate_data
Field-level validation against KNA1 schema rules.
Checks: required fields, max lengths, allowed values, date formats, duplicates.
"""

import json
import re
from datetime import datetime
from config.schemas import KNA1_SCHEMA, VALID_COUNTRIES, VALID_ACCOUNT_GROUPS

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_valid_date(val: str) -> bool:
    if not DATE_PATTERN.match(val):
        return False
    try:
        datetime.strptime(val, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_data(rows: list[dict]) -> dict:
    errors_by_type: dict[str, int] = {}
    row_errors: list[dict] = []
    seen_kunnr: dict[str, int] = {}
    error_rows = set()

    for idx, row in enumerate(rows):
        row_issues = []

        # duplicate KUNNR check
        kunnr = row.get("KUNNR", "").strip()
        if kunnr in seen_kunnr:
            row_issues.append({
                "field": "KUNNR",
                "rule": "unique",
                "value": kunnr,
                "message": f"Duplicate KUNNR (first seen at row {seen_kunnr[kunnr]})",
            })
        else:
            seen_kunnr[kunnr] = idx

        for fname, fdef in KNA1_SCHEMA.items():
            val = str(row.get(fname, "") or "").strip()

            # required
            if fdef.required and not val:
                row_issues.append({
                    "field": fname,
                    "rule": "required",
                    "value": val,
                    "message": f"{fname} is required but empty",
                })

            # max_length
            if fdef.max_length and len(val) > fdef.max_length:
                row_issues.append({
                    "field": fname,
                    "rule": "max_length",
                    "value": val[:40] + "…",
                    "message": f"{fname} length {len(val)} exceeds max {fdef.max_length}",
                })

            # allowed_values (only check non-empty)
            if fdef.allowed_values is not None and val:
                if val not in fdef.allowed_values:
                    row_issues.append({
                        "field": fname,
                        "rule": "allowed_values",
                        "value": val,
                        "message": f"{fname} value '{val}' not in allowed list",
                    })

        # date format for ERDAT
        erdat = str(row.get("ERDAT", "") or "").strip()
        if erdat and not _is_valid_date(erdat):
            row_issues.append({
                "field": "ERDAT",
                "rule": "date_format",
                "value": erdat,
                "message": f"ERDAT '{erdat}' is not YYYY-MM-DD",
            })

        # business rule: LOEVM=X and SPERR=X simultaneously is a warning
        if row.get("LOEVM") == "X" and row.get("SPERR") == "X":
            row_issues.append({
                "field": "LOEVM+SPERR",
                "rule": "business_rule",
                "value": "X+X",
                "message": "Customer marked for deletion AND blocked — review required",
            })

        if row_issues:
            error_rows.add(idx)
            row_errors.append({
                "row_index": idx,
                "kunnr": row.get("KUNNR", "?"),
                "issues": row_issues,
            })
            for issue in row_issues:
                key = issue["rule"]
                errors_by_type[key] = errors_by_type.get(key, 0) + 1

    valid_rows = len(rows) - len(error_rows)
    return {
        "tool": "validate_data",
        "total_rows": len(rows),
        "valid_rows": valid_rows,
        "invalid_rows": len(error_rows),
        "pass_rate_pct": round(valid_rows / len(rows) * 100, 1),
        "errors_by_type": errors_by_type,
        "row_errors": row_errors[:80],   # cap for token budget
    }


TOOL_DEF = {
    "name": "validate_data",
    "description": (
        "Run field-level validation on KNA1 rows: required fields, max lengths, "
        "allowed values, date formats, duplicates, and business rules. "
        "Returns a detailed report with per-row error details."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "run": {
                "type": "boolean",
                "description": "Set to true to trigger full validation.",
            }
        },
        "required": ["run"],
    },
}


def run_tool(tool_input: dict, all_rows: list[dict]) -> str:
    result = validate_data(all_rows)
    return json.dumps(result, indent=2)
