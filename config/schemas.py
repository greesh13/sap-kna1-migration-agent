"""
SAP KNA1 (Customer Master - General Data) schema definition.
Defines source schema, target schema, and field-level rules.
"""

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Field descriptor
# ---------------------------------------------------------------------------

@dataclass
class FieldDef:
    name: str
    dtype: str          # 'str' | 'int' | 'float' | 'date'
    max_length: Optional[int] = None
    required: bool = False
    allowed_values: Optional[list] = None
    description: str = ""


# ---------------------------------------------------------------------------
# SAP KNA1 source schema
# ---------------------------------------------------------------------------

KNA1_FIELDS: list[FieldDef] = [
    FieldDef("KUNNR", "str", 10, True,  description="Customer number"),
    FieldDef("NAME1", "str", 35, True,  description="Name 1"),
    FieldDef("NAME2", "str", 35, False, description="Name 2"),
    FieldDef("STRAS", "str", 35, False, description="Street address"),
    FieldDef("ORT01", "str", 35, True,  description="City"),
    FieldDef("ORT02", "str", 35, False, description="District"),
    FieldDef("PSTLZ", "str", 10, True,  description="Postal code"),
    FieldDef("LAND1", "str",  3, True,
             allowed_values=["US","DE","GB","FR","CA","AU","IN","JP","BR","MX"],
             description="Country key"),
    FieldDef("REGIO", "str",  3, False, description="Region / state"),
    FieldDef("TELF1", "str", 16, False, description="Telephone 1"),
    FieldDef("TELFX", "str", 31, False, description="Fax number"),
    FieldDef("STCD1", "str", 16, False, description="Tax number 1"),
    FieldDef("STCD2", "str", 11, False, description="Tax number 2"),
    FieldDef("KTOKD", "str",  4, True,
             allowed_values=["0001","0002","CPD","KRED"],
             description="Customer account group"),
    FieldDef("ANRED", "str", 15, False,
             allowed_values=["Mr.","Mrs.","Ms.","Dr.","Prof.","Company",""],
             description="Title / salutation"),
    FieldDef("BRSCH", "str",  4, False, description="Industry key"),
    FieldDef("SPERR", "str",  1, False,
             allowed_values=["", "X"],
             description="Central posting block"),
    FieldDef("LOEVM", "str",  1, False,
             allowed_values=["", "X"],
             description="Central deletion flag"),
    FieldDef("ERDAT", "str", 10, True,  description="Record creation date (YYYY-MM-DD)"),
    FieldDef("ERNAM", "str", 12, True,  description="Created by (user)"),
]

KNA1_SCHEMA: dict[str, FieldDef] = {f.name: f for f in KNA1_FIELDS}

# ---------------------------------------------------------------------------
# Target CRM schema (flat, snake_case)
# ---------------------------------------------------------------------------

CRM_FIELDS: list[FieldDef] = [
    FieldDef("customer_id",     "str", 20, True,  description="Unique customer identifier"),
    FieldDef("full_name",       "str", 70, True,  description="Full name (NAME1 + NAME2)"),
    FieldDef("street_address",  "str", 35, False, description="Street address"),
    FieldDef("city",            "str", 35, True,  description="City"),
    FieldDef("district",        "str", 35, False, description="District"),
    FieldDef("postal_code",     "str", 10, True,  description="Postal code"),
    FieldDef("country",         "str",  3, True,  description="ISO country code"),
    FieldDef("state_region",    "str",  3, False, description="State or region"),
    FieldDef("phone",           "str", 20, False, description="Primary phone"),
    FieldDef("fax",             "str", 31, False, description="Fax number"),
    FieldDef("tax_id_1",        "str", 16, False, description="Tax ID 1"),
    FieldDef("tax_id_2",        "str", 11, False, description="Tax ID 2"),
    FieldDef("account_group",   "str",  4, True,  description="Account group"),
    FieldDef("salutation",      "str", 15, False, description="Salutation"),
    FieldDef("industry",        "str",  4, False, description="Industry code"),
    FieldDef("blocked",         "str",  1, False, description="Posting blocked flag"),
    FieldDef("marked_deletion", "str",  1, False, description="Deletion flag"),
    FieldDef("created_date",    "str", 10, True,  description="Creation date ISO"),
    FieldDef("created_by",      "str", 12, True,  description="Created by user"),
]

CRM_SCHEMA: dict[str, FieldDef] = {f.name: f for f in CRM_FIELDS}

# ---------------------------------------------------------------------------
# KNA1 → CRM field mapping
# ---------------------------------------------------------------------------

FIELD_MAPPING: dict[str, str] = {
    "KUNNR": "customer_id",
    "NAME1": "full_name",       # NAME2 appended during transformation
    "STRAS": "street_address",
    "ORT01": "city",
    "ORT02": "district",
    "PSTLZ": "postal_code",
    "LAND1": "country",
    "REGIO": "state_region",
    "TELF1": "phone",
    "TELFX": "fax",
    "STCD1": "tax_id_1",
    "STCD2": "tax_id_2",
    "KTOKD": "account_group",
    "ANRED": "salutation",
    "BRSCH": "industry",
    "SPERR": "blocked",
    "LOEVM": "marked_deletion",
    "ERDAT": "created_date",
    "ERNAM": "created_by",
}

VALID_COUNTRIES = ["US","DE","GB","FR","CA","AU","IN","JP","BR","MX"]
VALID_ACCOUNT_GROUPS = ["0001","0002","CPD","KRED"]
