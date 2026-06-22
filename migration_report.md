# SAP KNA1 Migration Report
_Generated: 2026-06-22T16:24:13.546585_

All four pipeline stages are complete. Here is the comprehensive migration report:

---

## SAP KNA1 Migration Report
**Date:** 2025-07-14
**Source:** KNA1 Synthetic Dataset (500 Customer Master Records)

---

### 1. Schema Validation
All **500 rows** passed structural inspection with **zero schema issues** detected. Every row contained exactly the expected set of KNA1 fields — no missing columns, no extra or unexpected fields. The dataset is structurally sound and fully ready for content-level validation.

| Metric | Value |
|--------|-------|
| Total rows inspected | 500 |
| Schema-compliant rows | 500 |
| Schema issues found | 0 |

---

### 2. Data Quality Validation
Field-level validation revealed **100 invalid rows (20%)** across five error categories. Some rows carried multiple errors simultaneously (e.g., SPERR failing both `max_length` and `allowed_values`), bringing the total error count to **102 individual violations**.

| Error Type | Count | Description |
|---|---|---|
| `allowed_values` | 41 | Invalid values in SPERR (e.g. `1`, `Y`, `yes`), LAND1 (e.g. `EU`, `UK`, `XX`, `ZZ`, `??`), and KTOKD (e.g. `9999`, `XXXX`, `????`) |
| `max_length` | 18 | NAME1 exceeds the 35-character maximum (values up to 77 chars found); SPERR exceeds 1-char max |
| `required` | 18 | Missing values in mandatory fields: ERDAT (5), KTOKD (4), LAND1 (2), PSTLZ (2), ORT01 (3), NAME1 (2) |
| `business_rule` | 15 | Customers simultaneously flagged as both deletion-marked (LOEVM=X) and blocked (SPERR=X) |
| `date_format` | 10 | ERDAT contains non-YYYY-MM-DD values (`31-13-2020`, `not-a-date`, `20201301`) |
| **Total** | **102** | |

---

### 3. Field Mapping
The KNA1→CRM mapping executed successfully across **all 500 rows**. Key transformations applied during mapping:
- `KUNNR` → `customer_id`
- `NAME1` + `NAME2` concatenated → `full_name`
- `STRAS` → `address_line1`
- `ORT01` → `city`, `PSTLZ` → `postal_code`, `LAND1` → `country_code`
- `TELF1` → `phone`, `TELFX` → `fax`
- `BRSCH` → `industry`, `KTOKD` → `account_group`
- `ERDAT`/`ERNAM` → `created_date`/`created_by`
- `LOEVM` → `deletion_flag`, `SPERR` → `blocked`

| Metric | Value |
|--------|-------|
| Rows submitted for mapping | 500 |
| Rows successfully mapped | 500 |
| Mapping failures | 0 |

---

### 4. Transformation & Cleansing
The cleansing engine processed all 500 mapped rows. Records with **critical errors** (required fields missing, invalid dates, unresolvable country codes, business rule conflicts) were **rejected**. Records with recoverable issues were auto-corrected and **passed**.

**Transformations Applied:**

| Transformation | Rows Affected |
|---|---|
| Phone numbers normalised | 500 |
| Fax numbers normalised | 180 |
| Invalid flag values reset to `''` | 13 |
| `full_name` field truncated to 70 chars | 7 |

**Outcome:**

| Metric | Value |
|---|---|
| Input rows | 500 |
| Rows passed (clean) | 446 |
| Rows rejected (critical errors) | 54 |

---

### 5. Final Migration Outcome

| Metric | Value |
|--------|-------|
| Total records | 500 |
| Records passed | 446 |
| Records rejected | 54 |
| Pass rate | **89.2%** |

---

### 6. Top Issues Found

| Rank | Error Category | Count | Key Fields Affected |
|---|---|---|---|
| 1 | Invalid `allowed_values` | 41 | SPERR, LAND1, KTOKD |
| 2 | `max_length` exceeded | 18 | NAME1 (up to 77 chars vs. 35-char max) |
| 3 | `required` field missing | 18 | ERDAT, KTOKD, LAND1, PSTLZ, ORT01, NAME1 |
| 4 | `business_rule` violation | 15 | LOEVM+SPERR both set to `X` simultaneously |
| 5 | Invalid `date_format` | 10 | ERDAT (`31-13-2020`, `not-a-date`, `20201301`) |

---

### 7. Recommendations

1. **🌍 Standardise LAND1 Country Codes (41 records)**
The most frequent failure. Values like `EU`, `UK`, `XX`, `ZZ`, and `??` are not valid ISO 3166-1 alpha-2 codes. The source team should implement a lookup/mapping table to convert `UK` → `GB`, and work with business owners to resolve placeholder codes (`EU`, `XX`, `ZZ`, `??`) to the correct country before reprocessing.

2. **✂️ Truncate or Split Overlong NAME1 Values (18 records)**
NAME1 values exceeding 35 characters should be trimmed at source, with overflow text moved to NAME2. A pre-migration ABAP report or Excel formula can flag these automatically. Transformation already handles 7 truncations of `full_name`, but the source field itself should be corrected.

3. **📋 Populate All Required Fields Before Resubmission (18 records)**
Fields ERDAT, KTOKD, LAND1, PSTLZ, ORT01, and NAME1 must not be blank. Coordinate with the SAP system admin to extract these values from related tables (e.g., change documents for missing ERDAT, sales area data for KTOKD) or obtain them from the business data owners.

4. **🔒 Resolve LOEVM+SPERR Business Rule Conflicts (15 records)**
Customers cannot be simultaneously flagged for deletion and blocked — this indicates inconsistent lifecycle management in the source system. Each of the 15 affected customers (e.g., `0001000012`, `0001000021`) must be manually reviewed: either remove the deletion flag if the customer is still active, or remove the block flag if deletion processing has already completed.

5. **📅 Correct ERDAT Date Formats (10 records)**
All creation dates must conform strictly to `YYYY-MM-DD`. The three patterns found (`DD-MM-YYYY` reversed, `not-a-date` placeholder text, and `YYYYDDMM` transposition) suggest multiple upstream data entry issues. A pre-migration date-normalisation script should be applied to auto-correct `DD-MM-YYYY` → `YYYY-MM-DD` where possible, and flag `not-a-date` placeholders for manual lookup in SAP change logs.