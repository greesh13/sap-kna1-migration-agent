"""
Tool: transform_and_cleanse
Applies data cleansing and transformation rules to mapped CRM rows.

Rules applied:
  - Trim whitespace from all string fields
  - Normalise country to uppercase
  - Strip non-numeric chars from phone / fax
  - Truncate fields exceeding CRM max_length (with warning)
  - Set blocked / marked_deletion to "" if not "X"
  - Normalise postal codes (US: 5-digit ZIP)
  - Flag rows with critical issues as rejected; others pass
"""

import json
import re
from config.schemas import CRM_SCHEMA, VALID_COUNTRIES


def _clean_phone(val: str) -> str:
    digits = re.sub(r"[^\d+\-() ]", "", val)
    return digits.strip()[:20]


def _clean_postal(postal: str, country: str) -> str:
    if country == "US":
        digits = re.sub(r"\D", "", postal)
        return digits[:5] if len(digits) >= 5 else postal
    return postal


def transform_and_cleanse(mapped_rows: list[dict], validation_errors: dict) -> dict:
    # Build set of KUNNR with validation errors for quick lookup
    error_kunnrs = {
        r["kunnr"] for r in validation_errors.get("row_errors", [])
        for issue in r["issues"]
        if issue["rule"] in ("required", "unique", "date_format", "allowed_values")
    }

    passed, rejected, warnings_list = [], [], []
    transformations_applied: dict[str, int] = {}

    def bump(key):
        transformations_applied[key] = transformations_applied.get(key, 0) + 1

    for row in mapped_rows:
        row = dict(row)   # copy
        w = []

        # trim all strings
        for k, v in row.items():
            if isinstance(v, str):
                row[k] = v.strip()

        # normalise country
        row["country"] = row.get("country", "").upper()

        # normalise phone/fax
        if row.get("phone"):
            row["phone"] = _clean_phone(row["phone"])
            bump("phone_normalised")

        if row.get("fax"):
            row["fax"] = _clean_phone(row["fax"])
            bump("fax_normalised")

        # normalise postal code
        postal = row.get("postal_code", "")
        country = row.get("country", "")
        cleaned_postal = _clean_postal(postal, country)
        if cleaned_postal != postal:
            row["postal_code"] = cleaned_postal
            bump("postal_normalised")

        # normalise flag fields
        for flag in ("blocked", "marked_deletion"):
            if row.get(flag, "") not in ("X", ""):
                w.append(f"Flag '{flag}' had value '{row[flag]}' — reset to ''")
                row[flag] = ""
                bump("flag_normalised")

        # truncate overlong fields
        for fname, fdef in CRM_SCHEMA.items():
            val = row.get(fname, "")
            if fdef.max_length and isinstance(val, str) and len(val) > fdef.max_length:
                row[fname] = val[:fdef.max_length]
                w.append(f"'{fname}' truncated to {fdef.max_length} chars")
                bump("field_truncated")

        if w:
            warnings_list.append({"customer_id": row.get("customer_id"), "warnings": w})

        # route to passed / rejected
        if row.get("customer_id", "") in error_kunnrs:
            rejected.append(row)
        else:
            passed.append(row)

    return {
        "tool": "transform_and_cleanse",
        "input_rows": len(mapped_rows),
        "passed": len(passed),
        "rejected": len(rejected),
        "transformations_applied": transformations_applied,
        "warnings": warnings_list[:30],
        "passed_rows": passed,
        "rejected_rows": rejected,
    }


TOOL_DEF = {
    "name": "transform_and_cleanse",
    "description": (
        "Cleanse and transform mapped CRM rows: normalise country codes, phones, postal codes, "
        "truncate overlong fields, reset invalid flag values. "
        "Rows with critical validation errors are rejected; clean rows are passed through."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "run": {
                "type": "boolean",
                "description": "Set to true to run transformation.",
            }
        },
        "required": ["run"],
    },
}


def run_tool(tool_input: dict, mapped_rows: list[dict], validation_result: dict) -> dict:
    return transform_and_cleanse(mapped_rows, validation_result)
