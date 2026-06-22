"""
SAP KNA1 → CRM Migration Agent
Orchestrates the migration pipeline via Claude claude-sonnet-4-6 tool_use when an
ANTHROPIC_API_KEY is available, otherwise falls back to direct Python orchestration.
"""

import os
import json
import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# ── local imports ──────────────────────────────────────────────────────────
from data.synthetic.generate import generate, save
from tools import schema as schema_tool
from tools import validation as validation_tool
from tools import mapping as mapping_tool
from tools import transformation as transformation_tool
from tools import verify as verify_tool

console = Console()

# ── tool registry ──────────────────────────────────────────────────────────

TOOLS = [
    schema_tool.TOOL_DEF,
    validation_tool.TOOL_DEF,
    mapping_tool.TOOL_DEF,
    transformation_tool.TOOL_DEF,
    verify_tool.TOOL_DEF,
]

# ── state shared across tool calls ────────────────────────────────────────

STATE: dict = {
    "raw_rows": [],
    "mapped_rows": [],
    "validation_result": {},
    "transform_result": {},
}


def dispatch_tool(name: str, tool_input: dict) -> str:
    if name == "validate_schema":
        result = schema_tool.run_tool(tool_input, STATE["raw_rows"])
        return result

    if name == "validate_data":
        result_str = validation_tool.run_tool(tool_input, STATE["raw_rows"])
        STATE["validation_result"] = json.loads(result_str)
        return result_str

    if name == "map_fields":
        result = mapping_tool.run_tool(tool_input, STATE["raw_rows"])
        STATE["mapped_rows"] = result.get("mapped_rows", []) if isinstance(result, dict) else []
        # return summary without full row list for token budget
        summary = {k: v for k, v in result.items()
                   if k not in ("mapped_rows", "field_mapping", "sample_output")}
        return json.dumps(summary, indent=2)

    if name == "transform_and_cleanse":
        result = transformation_tool.run_tool(
            tool_input,
            STATE["mapped_rows"],
            STATE["validation_result"],
        )
        STATE["transform_result"] = result
        summary = {k: v for k, v in result.items()
                   if k not in ("passed_rows", "rejected_rows")}
        return json.dumps(summary, indent=2)

    if name == "verify_database":
        return verify_tool.run_tool(tool_input)

    return json.dumps({"error": f"Unknown tool: {name}"})


# ── agent loop ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert SAP data migration agent.
Your job is to migrate SAP KNA1 customer master records to a target CRM system.

You have five tools available (call them in this order):
1. validate_schema       — check structural completeness of the source data
2. validate_data         — run field-level validation (required, lengths, allowed values, dates, duplicates)
3. map_fields            — apply the KNA1→CRM field mapping
4. transform_and_cleanse — cleanse and normalise mapped data; write passed rows to SQLite DB
5. verify_database       — confirm row count, print 5 sample records, verify mandatory fields non-null

After all five tools have run, produce a final migration report in this exact structure:

## SAP KNA1 Migration Report
**Date:** <today>
**Source:** KNA1 synthetic dataset

### 1. Schema Validation
...summary...

### 2. Data Quality Validation
...summary with error breakdown by type...

### 3. Field Mapping
...summary...

### 4. Transformation & Cleansing
...summary...

### 5. Final Migration Outcome
| Metric | Value |
|--------|-------|
| Total records | ... |
| Records passed | ... |
| Records rejected | ... |
| Pass rate | ...% |

### 6. Top Issues Found
List the top 5 error categories with counts.

### 7. Recommendations
Provide 3-5 actionable recommendations for fixing the rejected records before reprocessing.
"""

USER_PROMPT = """The SAP KNA1 dataset has been loaded — {n} rows of customer master data.
Please run the full migration pipeline using your tools and produce the final migration report."""


def run_agent_with_api(n_rows: int, rows: list[dict]) -> str:
    """Agent loop using Claude API tool_use."""
    import anthropic
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": USER_PROMPT.format(n=n_rows)}]

    console.print("\n[bold yellow]Starting Claude agent loop (API mode)…[/bold yellow]")
    step = 0
    while True:
        step += 1
        console.print(f"\n[dim]── Step {step} ──────────────────────────────────[/dim]")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        text_blocks = [b.text for b in response.content if b.type == "text"]
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if text_blocks:
            for t in text_blocks:
                console.print(t[:300] + ("…" if len(t) > 300 else ""))
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason == "end_turn" or not tool_use_blocks:
            return "\n".join(b.text for b in response.content if b.type == "text")
        tool_results = []
        for tb in tool_use_blocks:
            console.print(f"[cyan]→ Tool call:[/cyan] [bold]{tb.name}[/bold]")
            result_str = dispatch_tool(tb.name, tb.input)
            try:
                rj = json.loads(result_str) if isinstance(result_str, str) else result_str
                for key in ("schema_ok","valid_rows","invalid_rows","passed","rejected","mapped_rows"):
                    if key in rj:
                        console.print(f"   [green]{key}[/green]: {rj[key]}")
            except Exception:
                pass
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tb.id,
                "content": result_str if isinstance(result_str, str) else json.dumps(result_str),
            })
        messages.append({"role": "user", "content": tool_results})


def run_agent_standalone(n_rows: int) -> str:
    """
    Direct Python orchestration — identical pipeline, no API key required.
    Runs each tool in sequence and assembles the migration report.
    """
    console.print("\n[bold yellow]Running pipeline (standalone mode — no API key needed)…[/bold yellow]")

    # Step 1: schema validation
    console.print("[cyan]→ Tool:[/cyan] [bold]validate_schema[/bold]")
    schema_result = json.loads(schema_tool.run_tool({}, STATE["raw_rows"]))
    console.print(f"   schema_ok: {schema_result['schema_ok']}  issues: {schema_result['schema_issues']}")

    # Step 2: data validation
    console.print("[cyan]→ Tool:[/cyan] [bold]validate_data[/bold]")
    val_result_str = validation_tool.run_tool({"run": True}, STATE["raw_rows"])
    val_result = json.loads(val_result_str)
    STATE["validation_result"] = val_result
    console.print(f"   valid_rows: {val_result['valid_rows']}  invalid_rows: {val_result['invalid_rows']}")

    # Step 3: field mapping
    console.print("[cyan]→ Tool:[/cyan] [bold]map_fields[/bold]")
    map_result = mapping_tool.run_tool({"run": True}, STATE["raw_rows"])
    STATE["mapped_rows"] = map_result.get("mapped_rows", [])
    console.print(f"   mapped_rows: {map_result.get('mapped_count', len(STATE['mapped_rows']))}")

    # Step 4: transform & cleanse → writes to SQLite
    console.print("[cyan]→ Tool:[/cyan] [bold]transform_and_cleanse[/bold]")
    tx_result = transformation_tool.run_tool({"run": True}, STATE["mapped_rows"], STATE["validation_result"])
    STATE["transform_result"] = tx_result
    console.print(f"   passed: {tx_result['passed']}  rejected: {tx_result['rejected']}")
    console.print(f"   db: {tx_result.get('db_path', '')}")

    # Step 5: verify database
    console.print("[cyan]→ Tool:[/cyan] [bold]verify_database[/bold]")
    verify_result = json.loads(verify_tool.run_tool({"run": True}))
    console.print(f"   row_count: {verify_result.get('row_count')}  mandatory_ok: {verify_result.get('all_mandatory_ok')}")

    # ── build report ───────────────────────────────────────────────────────
    v = val_result
    t = tx_result
    s = schema_result
    total = v["total_rows"]
    passed = t["passed"]
    rejected = t["rejected"]
    pass_rate = round(passed / total * 100, 1)
    err_by_type = v.get("errors_by_type", {})
    top_errors = sorted(err_by_type.items(), key=lambda x: x[1], reverse=True)[:5]
    transforms = t.get("transformations_applied", {})

    error_table_rows = "\n".join(
        f"| {rule} | {count} |" for rule, count in top_errors
    )
    transform_rows = "\n".join(
        f"| {rule} | {count} |" for rule, count in transforms.items()
    )

    report = f"""## SAP KNA1 Migration Report
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Source:** KNA1 synthetic dataset ({total} records)
**Pipeline Mode:** Standalone (direct Python orchestration)

---

### 1. Schema Validation
All {total} rows were checked against the KNA1 field schema.

| Metric | Value |
|--------|-------|
| Total rows | {s['total_rows']} |
| Schema-compliant rows | {s['schema_ok']} |
| Schema issues | {s['schema_issues']} |

{"✅ No structural schema issues found." if s['schema_issues'] == 0 else f"⚠️  {s['schema_issues']} rows had missing or extra fields."}

---

### 2. Data Quality Validation
Field-level validation covering required fields, max lengths, allowed values, date formats, and duplicate keys.

| Metric | Value |
|--------|-------|
| Total rows | {v['total_rows']} |
| Valid rows | {v['valid_rows']} |
| Invalid rows | {v['invalid_rows']} |
| Pass rate | {v['pass_rate_pct']}% |

**Errors by type:**
| Error Type | Count |
|------------|-------|
{error_table_rows if error_table_rows else "| (none) | 0 |"}

---

### 3. Field Mapping
KNA1 source fields were mapped to the target CRM schema.

- **19 source fields** mapped to **19 CRM fields**
- Special rule: `NAME1` + `NAME2` concatenated into `full_name`
- All {total} rows processed through the mapping layer

---

### 4. Transformation & Cleansing
Data cleansing rules applied to all mapped rows.

| Transformation | Count |
|---------------|-------|
{transform_rows if transform_rows else "| (none applied) | 0 |"}

Rows with critical validation errors were **rejected** from the migration load.

---

### 5. Final Migration Outcome
| Metric | Value |
|--------|-------|
| Total records | {total} |
| Records passed (ready to load) | {passed} |
| Records rejected | {rejected} |
| Pass rate | {pass_rate}% |

{"🟢 Migration pass rate is **excellent** (≥ 95%)." if pass_rate >= 95 else "🟡 Migration pass rate is **acceptable** (80–94%)." if pass_rate >= 80 else "🔴 Migration pass rate is **below threshold** (< 80%) — remediation required."}

---

### 6. Top Issues Found
| Rank | Error Category | Occurrences |
|------|---------------|-------------|
""" + "\n".join(
        f"| {i+1} | {rule} | {count} |"
        for i, (rule, count) in enumerate(top_errors)
    ) + f"""

---

### 7. Recommendations
1. **Fix missing required fields** — Run a data enrichment process for blank NAME1, ORT01, PSTLZ, and LAND1 values before re-attempting migration.
2. **Correct invalid country codes** — Map non-standard codes (XX, ZZ, UK) to ISO-3166 two-letter codes; engage source-system owners to enforce the allowed-values list.
3. **Resolve duplicate KUNNR values** — Investigate duplicate customer numbers in the source system; consolidate or reassign as appropriate.
4. **Standardise date formats** — Ensure all ERDAT values conform to YYYY-MM-DD; consider a pre-migration ETL step to convert alternative date formats.
5. **Review blocked+deletion-flagged records** — Customers with both SPERR=X and LOEVM=X should be reviewed by the business before migration to determine whether they should be loaded as inactive or excluded entirely.
"""
    return report


def run_agent(n_rows: int = 500) -> str:
    # ── generate data ──────────────────────────────────────────────────────
    console.print(Panel(f"[bold cyan]SAP Migration Agent[/bold cyan]\nGenerating {n_rows} KNA1 rows…",
                        box=box.DOUBLE_EDGE))
    rows = generate(n_rows)
    path = save(rows)
    STATE["raw_rows"] = rows
    injected = sum(1 for r in rows if r.get("_injected_error"))
    console.print(f"[green]✓[/green] Dataset ready: {len(rows)} rows | {injected} injected errors | saved → {path}")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        return run_agent_with_api(n_rows, rows)
    else:
        console.print("[yellow]ℹ  ANTHROPIC_API_KEY not set — using standalone pipeline mode[/yellow]")
        return run_agent_standalone(n_rows)


# ── report renderer ────────────────────────────────────────────────────────

def render_report(report_md: str):
    console.print("\n")
    console.print(Panel(report_md, title="[bold green]Migration Report[/bold green]",
                        border_style="green", box=box.HEAVY))

    # also save to file
    out_path = os.path.join(os.path.dirname(__file__), "migration_report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# SAP KNA1 Migration Report\n_Generated: {datetime.now().isoformat()}_\n\n")
        f.write(report_md)
    console.print(f"\n[green]Report saved →[/green] {out_path}")


# ── entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    report = run_agent(n)
    render_report(report)
