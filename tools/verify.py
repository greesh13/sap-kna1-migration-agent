"""
Tool: verify_database
Connects to customer_master.db and confirms:
  - Row count via SELECT COUNT(*)
  - 5 sample records printed as a table
  - All mandatory CRM fields are non-null in the DB
"""

import json
import os

import pandas as pd
from sqlalchemy import create_engine, text
from rich.console import Console
from rich.table import Table
from rich import box

from config.schemas import CRM_SCHEMA
from tools.transformation import DB_PATH, TABLE_NAME

console = Console()

MANDATORY_FIELDS = [f for f, d in CRM_SCHEMA.items() if d.required]


def verify_database() -> dict:
    db_abs = os.path.abspath(DB_PATH)

    if not os.path.exists(db_abs):
        return {"tool": "verify_database", "error": f"Database not found at {db_abs}"}

    engine = create_engine(f"sqlite:///{db_abs}")

    with engine.connect() as conn:
        # 1. row count
        row_count = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}")).scalar()

        # 2. sample records
        sample_df = pd.read_sql(
            f"SELECT * FROM {TABLE_NAME} LIMIT 5", conn
        )

        # 3. mandatory field null checks
        null_counts = {}
        for field in MANDATORY_FIELDS:
            if field in sample_df.columns or True:
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE \"{field}\" IS NULL OR \"{field}\" = ''")
                ).scalar()
                null_counts[field] = result

    engine.dispose()

    all_mandatory_ok = all(v == 0 for v in null_counts.values())

    # ── rich table for sample records ──────────────────────────────────────
    console.print()
    t = Table(title="[bold]5 Sample Records from CUSTOMER_MASTER[/bold]",
              box=box.SIMPLE_HEAVY, show_lines=True)

    display_cols = ["customer_id", "full_name", "city", "country", "postal_code",
                    "phone", "account_group", "created_date"]
    cols = [c for c in display_cols if c in sample_df.columns]

    for col in cols:
        t.add_column(col, style="cyan", no_wrap=True)

    for _, row in sample_df[cols].iterrows():
        t.add_row(*[str(row[c]) for c in cols])

    console.print(t)

    # ── mandatory field null check table ──────────────────────────────────
    nt = Table(title="[bold]Mandatory Field Null Check[/bold]",
               box=box.SIMPLE_HEAVY)
    nt.add_column("Field", style="white")
    nt.add_column("Null/Empty Rows", style="white")
    nt.add_column("Status", style="white")

    for field, count in null_counts.items():
        status = "[green]✓ OK[/green]" if count == 0 else f"[red]✗ {count} nulls[/red]"
        nt.add_row(field, str(count), status)

    console.print(nt)

    return {
        "tool": "verify_database",
        "db_path": db_abs,
        "table": TABLE_NAME,
        "row_count": row_count,
        "mandatory_fields_checked": MANDATORY_FIELDS,
        "null_counts": null_counts,
        "all_mandatory_ok": all_mandatory_ok,
        "sample_records": sample_df.to_dict(orient="records"),
    }


TOOL_DEF = {
    "name": "verify_database",
    "description": (
        "Connect to the migrated SQLite database, confirm the row count, "
        "print 5 sample records, and verify all mandatory CRM fields are non-null."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "run": {
                "type": "boolean",
                "description": "Set to true to run database verification.",
            }
        },
        "required": ["run"],
    },
}


def run_tool(tool_input: dict) -> str:
    result = verify_database()
    # return summary without sample_records list (token budget)
    summary = {k: v for k, v in result.items() if k != "sample_records"}
    return json.dumps(summary, indent=2)
