# SAP KNA1 Migration Agent

Built a SAP KNA1 customer master data migration agent inspired by enterprise engagements in manufacturing and supply chain. Synthetic data modeled after real KNA1 schemas used in large-scale SAP-to-CRM migrations at companies like Honeywell. Demonstrates the architecture used in production migration pipelines.

---

## Overview

An end-to-end agentic migration pipeline that takes SAP KNA1 customer master records and migrates them to a target CRM schema. The agent uses Claude claude-sonnet-4-6 with tool_use to autonomously orchestrate the migration pipeline — deciding which tools to call, in what order, and interpreting results between each step.

---

## Architecture

```
SAP KNA1 Source Data (500 records)
        ↓
┌─────────────────────────────────────┐
│          Migration Agent            │
│                                     │
│  Claude claude-sonnet-4-6 (tool_use loop)  │
│                                     │
│  ├── validate_schema                │
│  ├── validate_data                  │
│  ├── map_fields                     │
│  └── transform_and_cleanse          │
└─────────────────────────────────────┘
        ↓
Migration Report + Clean CRM Records
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
- Routes records to passed or rejected based on validation outcome

---

## Project Structure

```
sap-kna1-migration-agent/
├── config/
│   └── schemas.py          # KNA1 + CRM schema definitions, field mapping
├── data/
│   └── synthetic/
│       └── generate.py     # 500-row KNA1 synthetic data generator
├── tools/
│   ├── schema.py           # Schema validation tool
│   ├── validation.py       # Data quality validation tool
│   ├── mapping.py          # Field mapping tool
│   └── transformation.py   # Cleansing and transformation tool
├── main.py                 # Migration agent orchestrator
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

Standalone mode runs the full pipeline as a direct Python orchestration — same results, no API credits required.

---

## Sample Migration Report

```
Total records        500
Records passed       446
Records rejected      54
Pass rate           89.2%

Top issues:
1. allowed_values    41   (invalid country codes, account groups)
2. max_length        18   (NAME1 exceeds 35-char limit)
3. required          18   (blank mandatory fields)
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
- Faker (synthetic data generation)
- Rich (terminal reporting)
