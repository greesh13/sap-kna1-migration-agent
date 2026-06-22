"""
Generate 500 rows of synthetic SAP KNA1 customer master data with injected errors.
Run directly:  python -m data.synthetic.generate
"""

import random
import string
import json
import os
from datetime import date, timedelta

try:
    from faker import Faker
except ImportError:
    raise SystemExit("Run: pip install faker")

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.schemas import VALID_COUNTRIES, VALID_ACCOUNT_GROUPS

fake = Faker()
random.seed(42)

# ── helpers ────────────────────────────────────────────────────────────────

def rand_kunnr(i: int) -> str:
    return str(i + 1000000).zfill(10)

def rand_date(start=date(2010, 1, 1), end=date(2024, 12, 31)) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()

REGIONS = {
    "US": ["CA","NY","TX","FL","IL","WA","GA"],
    "DE": ["BY","BE","NW","HE","BW"],
    "GB": ["ENG","SCT","WLS","NIR"],
    "FR": ["IDF","ARA","NAQ","OCC"],
    "CA": ["ON","BC","AB","QC"],
    "AU": ["NSW","VIC","QLD","WA"],
    "IN": ["MH","DL","KA","TN"],
    "JP": ["13","14","27","23"],
    "BR": ["SP","RJ","MG","BA"],
    "MX": ["CMX","JAL","NLE","MEX"],
}

INDUSTRIES = ["BANK","MANU","RETL","TECH","HLTH","AGRI","CONS","TRAN","ENGY","EDUC"]
ACCOUNT_GROUPS = VALID_ACCOUNT_GROUPS
TITLES = ["Mr.","Mrs.","Ms.","Dr.","Prof.","Company",""]
USERS = ["ADMIN","MIGRATE","SYSTEM","JSMITH","AWONG","MLOPEZ","DBROWN"]

# ── clean row ──────────────────────────────────────────────────────────────

def clean_row(i: int) -> dict:
    country = random.choice(VALID_COUNTRIES)
    name1 = fake.company() if random.random() < 0.4 else fake.last_name()
    name2 = fake.first_name() if random.random() < 0.5 else ""
    return {
        "KUNNR": rand_kunnr(i),
        "NAME1": name1[:35],
        "NAME2": name2[:35],
        "STRAS": fake.street_address()[:35],
        "ORT01": fake.city()[:35],
        "ORT02": fake.city()[:35] if random.random() < 0.3 else "",
        "PSTLZ": fake.postcode()[:10],
        "LAND1": country,
        "REGIO": random.choice(REGIONS[country]),
        "TELF1": fake.phone_number()[:16],
        "TELFX": fake.phone_number()[:31] if random.random() < 0.4 else "",
        "STCD1": fake.numerify("##-#######")[:16] if random.random() < 0.6 else "",
        "STCD2": fake.numerify("#########")[:11] if random.random() < 0.4 else "",
        "KTOKD": random.choice(ACCOUNT_GROUPS),
        "ANRED": random.choice(TITLES),
        "BRSCH": random.choice(INDUSTRIES),
        "SPERR": "",
        "LOEVM": "",
        "ERDAT": rand_date(),
        "ERNAM": random.choice(USERS),
    }

# ── error injectors ────────────────────────────────────────────────────────

def err_missing_required(row: dict) -> dict:
    field = random.choice(["NAME1","ORT01","PSTLZ","LAND1","ERDAT"])
    row[field] = ""
    row["_injected_error"] = f"missing_required:{field}"
    return row

def err_invalid_country(row: dict) -> dict:
    row["LAND1"] = random.choice(["XX","ZZ","EU","UK","??"])
    row["_injected_error"] = "invalid_country"
    return row

def err_field_too_long(row: dict) -> dict:
    row["NAME1"] = fake.text(max_nb_chars=80)
    row["_injected_error"] = "name1_too_long"
    return row

def err_invalid_account_group(row: dict) -> dict:
    row["KTOKD"] = random.choice(["XXXX","9999","????","    "])
    row["_injected_error"] = "invalid_account_group"
    return row

def err_bad_date(row: dict) -> dict:
    row["ERDAT"] = random.choice(["31-13-2020","2020/99/01","not-a-date","","20201301"])
    row["_injected_error"] = "bad_date_format"
    return row

def err_duplicate_kunnr(row: dict, existing_id: str) -> dict:
    row["KUNNR"] = existing_id
    row["_injected_error"] = "duplicate_kunnr"
    return row

def err_blocked_and_active(row: dict) -> dict:
    row["SPERR"] = "X"
    row["LOEVM"] = "X"
    row["_injected_error"] = "blocked_and_deletion_flagged"
    return row

def err_invalid_sperr(row: dict) -> dict:
    row["SPERR"] = random.choice(["Y","1","yes"])
    row["_injected_error"] = "invalid_sperr_value"
    return row

ERROR_INJECTORS = [
    err_missing_required,
    err_invalid_country,
    err_field_too_long,
    err_invalid_account_group,
    err_bad_date,
    err_blocked_and_active,
    err_invalid_sperr,
]

# ── main generator ─────────────────────────────────────────────────────────

def generate(n: int = 500) -> list[dict]:
    rows = []
    existing_ids = []
    error_count = 0
    target_errors = int(n * 0.20)   # ~20 % rows have injected errors

    for i in range(n):
        row = clean_row(i)
        existing_ids.append(row["KUNNR"])
        row["_injected_error"] = ""

        # inject errors in ~20 % of rows
        if error_count < target_errors and random.random() < 0.25:
            injector = random.choice(ERROR_INJECTORS)
            if injector == err_duplicate_kunnr and len(existing_ids) > 1:
                row = injector(row, random.choice(existing_ids[:-1]))
            else:
                row = injector(row)
            error_count += 1

        rows.append(row)

    return rows


def save(rows: list[dict], path: str = None) -> str:
    if path is None:
        base = os.path.dirname(__file__)
        path = os.path.join(base, "kna1_raw.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    return path


if __name__ == "__main__":
    rows = generate(500)
    path = save(rows)
    injected = sum(1 for r in rows if r["_injected_error"])
    print(f"Generated {len(rows)} rows → {path}")
    print(f"Injected errors: {injected} rows ({injected/len(rows)*100:.1f}%)")
