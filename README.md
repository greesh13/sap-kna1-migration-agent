# SAP KNA1 Migration Agent

Built a SAP KNA1 customer master data migration agent inspired by enterprise engagements in manufacturing and supply chain. Synthetic data modeled after real KNA1 schemas used in large-scale SAP-to-CRM migrations at companies like Honeywell. Demonstrates the architecture used in production migration pipelines — including autonomous agent orchestration, data validation, field mapping, cleansing, SQLite persistence, and post-load database verification.

---

## Overview

An end-to-end agentic migration pipeline that takes SAP KNA1 customer master records and migrates them to a target CRM schema. The agent uses Claude claude-sonnet-4-6 with tool_use to autonomously orchestrate the pipeline — deciding which tools to call, in what order, and interpreting results between each step. Clean records are written to a SQLite database and verified post-load.

---

## Architecture

```
SAP KNA1 Source Data (500 records)
        ↓
┌──────────────────────────────────────────┐
│            Migration Agent               │
│                                          │
│  Claude claude-sonnet-4-6 (tool_use loop)│
│                                          │
│  ├── validate_schema                     │
│  ├── validate_data                       │
│  ├── map_fields                          │
│  ├── transform_and_cleanse               │
│  └── verify_database                     │
└──────────────────────────────────────────┘
        ↓
SQLite Database (data/migrated/customer_master.db)
        ↓
Migration Report + Verification Output
```

---

## Pipeline Stages

### 1. Schema Validation
Checks every row for structural completeness — no missing fields, no unexpected columns.

### 2. Data Quality Validation
Field-level validation covering:
- Required field checks
- Max length enforcement
- Allowed value lists (country codes, account groups)
- Date format validation (YYYY-MM-DD)
- Duplicate KUNNR detection
- Business rule checks (SPERR + LOEVM conflict)

### 3. Field Mapping
Maps 19 KNA1 source fields to target CRM schema:
- `KUNNR` → `customer_id`
- `NAME1` + `NAME2` → `full_name`
- `STRAS` → `street_address`
- `LAND1` → `country`
- `TELF1` → `phone`
- `ERDAT` → `created_date`
- and more...

### 4. Transformation & Cleansing
- Normalises phone and fax numbers
- Standardises country codes to uppercase
- Cleans US postal codes to 5-digit ZIP
- Resets invalid flag values
- Truncates fields exceeding CRM max length
- Rejects records where any mandatory field is blank after cleansing
- Writes all passed records to SQLite via pandas `to_sql` + SQLAlchemy

### 5. Database Verification
After load, connects to `customer_master.db` and confirms:
- Row count via `SELECT COUNT(*)`
- 5 sample records printed as a rich terminal table
- All 8 mandatory CRM fields verified non-null across every loaded record

---

## Project Structure

```
sap-kna1-migration-agent/
├── config/
│   └── schemas.py              # KNA1 + CRM schema definitions, field mapping
├── data/
│   ├── synthetic/
│   │   ├── generate.py         # 500-row KNA1 synthetic data generator with injected errors
│   │   └── kna1_raw.json       # Generated source dataset
│   └── migrated/
│       └── customer_master.db  # SQLite database of migrated CRM records
├── tools/
│   ├── schema.py               # Schema validation tool
│   ├── validation.py           # Data quality validation tool
│   ├── mapping.py              # Field mapping tool
│   ├── transformation.py       # Cleansing, transformation, and SQLite write
│   └── verify.py               # Post-load database verification tool
├── main.py                     # Migration agent orchestrator
├── migration_report.md         # Last run migration report
├── requirements.txt
└── README.md
```

---

## Setup

```bash
git clone https://github.com/greesh13/sap-kna1-migration-agent.git
cd sap-kna1-migration-agent
pip install -r requirements.txt
```

---

## Run

**With Claude agent loop (requires Anthropic API key):**
```bash
export ANTHROPIC_API_KEY="your-key-here"
python main.py
```

**Standalone mode (no API key needed):**
```bash
python main.py
```

Standalone mode runs the full pipeline as direct Python orchestration — same results, no API credits required.

---

## Sample Verification Output

```
5 Sample Records from CUSTOMER_MASTER
──────────────────────────────────────────────────────────────────────
customer_id   full_name                city          postal_code   account_group
0001000001    Boyd, Monroe and Wilson  Port Stevens  73421         0001
0001000002    Johns Robert             New Antonia   98034         0001
0001000003    Allen, Odom and Doyle    South Adams   90210         0002
0001000004    Mcdonald                 Port Victor   66012         0001
0001000005    Green                    Shannonville  49301         KRED

Mandatory Field Null Check
──────────────────────────────────────────
Field            Null/Empty Rows   Status
customer_id      0                 ✓ OK
full_name        0                 ✓ OK
city             0                 ✓ OK
postal_code      0                 ✓ OK
country          0                 ✓ OK
account_group    0                 ✓ OK
created_date     0                 ✓ OK
created_by       0                 ✓ OK

row_count: 444   mandatory_ok: True
```

---

## Sample Migration Report

```
Total records        500
Records passed       444
Records rejected      56
Pass rate           88.8%

Top issues:
1. allowed_values    41   (invalid country codes, account groups)
2. required          18   (blank mandatory fields)
3. max_length        17   (NAME1 exceeds 35-char limit)
4. business_rule     15   (SPERR + LOEVM both flagged)
5. date_format       10   (non-ISO ERDAT values)
```

---

## KNA1 Fields Covered

| SAP Field | Description | CRM Field |
|-----------|-------------|-----------|
| KUNNR | Customer number | customer_id |
| NAME1 | Name 1 | full_name |
| NAME2 | Name 2 | full_name (appended) |
| STRAS | Street address | street_address |
| ORT01 | City | city |
| PSTLZ | Postal code | postal_code |
| LAND1 | Country key | country |
| REGIO | Region / state | state_region |
| TELF1 | Telephone | phone |
| KTOKD | Account group | account_group |
| ERDAT | Creation date | created_date |

---

## Tech Stack

- Python 3.11+
- Anthropic Claude API (claude-sonnet-4-6)
- pandas + SQLAlchemy (SQLite persistence)
- Faker (synthetic data generation)
- Rich (terminal reporting)
