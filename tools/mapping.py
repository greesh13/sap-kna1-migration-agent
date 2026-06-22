"""
Tool: map_fields
Applies the KNA1 → CRM field mapping to each row.
NAME1 + NAME2 are concatenated into full_name.
Returns mapped rows and a mapping summary.
"""

import json
from config.schemas import FIELD_MAPPING


def map_fields(rows: list[dict]) -> dict:
    mapped = []
    for row in rows:
        crm = {}
        for src, tgt in FIELD_MAPPING.items():
            crm[tgt] = str(row.get(src, "") or "").strip()

        # Special: concatenate NAME1 + NAME2 into full_name
        name2 = str(row.get("NAME2", "") or "").strip()
        if name2:
            crm["full_name"] = (crm["full_name"] + " " + name2).strip()

        mapped.append(crm)

    return {
        "tool": "map_fields",
        "total_rows": len(rows),
        "mapped_count": len(mapped),
        "mapped_rows": mapped,
        "field_mapping": FIELD_MAPPING,
        "sample_output": mapped[:3],
    }


TOOL_DEF = {
    "name": "map_fields",
    "description": (
        "Map SAP KNA1 source fields to target CRM fields using the defined mapping table. "
        "Concatenates NAME1 and NAME2 into full_name. Returns mapped rows and a summary."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "run": {
                "type": "boolean",
                "description": "Set to true to execute field mapping.",
            }
        },
        "required": ["run"],
    },
}


def run_tool(tool_input: dict, all_rows: list[dict]) -> dict:
    return map_fields(all_rows)
