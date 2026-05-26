"""
Input Validation — Mortgage Broker Agent
Validates borrower responses based on field context.
Returns (is_valid: bool, errors: list[str])
"""
import re
from typing import Tuple, List


# ── individual validators ─────────────────────────────────────

def _ssn(v: str) -> bool:
    return bool(re.match(r"^\d{3}-?\d{2}-?\d{4}$", v.strip()))

def _email(v: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$", v.strip()))

def _phone(v: str) -> bool:
    return len(re.sub(r"\D", "", v)) == 10

def _income(v: str) -> bool:
    try:
        n = float(re.sub(r"[$,\s]", "", v))
        return 0 < n < 10_000_000
    except (ValueError, TypeError):
        return False

def _loan_amount(v: str) -> bool:
    try:
        n = float(re.sub(r"[$,\s]", "", v))
        return 50_000 <= n <= 10_000_000
    except (ValueError, TypeError):
        return False

def _zip_code(v: str) -> bool:
    return bool(re.match(r"^\d{5}(-\d{4})?$", v.strip()))

def _date(v: str) -> bool:
    return bool(
        re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", v.strip()) or
        re.match(r"^\d{4}-\d{2}-\d{2}$", v.strip())
    )

def _credit_score(v: str) -> bool:
    try:
        n = int(re.sub(r"\D", "", v))
        return 300 <= n <= 850
    except (ValueError, TypeError):
        return False

def _percentage(v: str) -> bool:
    try:
        n = float(re.sub(r"[%\s]", "", v))
        return 0 <= n <= 100
    except (ValueError, TypeError):
        return False


# ── keyword → (validator, error message) ─────────────────────
# Context string is searched for these keywords (case-insensitive).
# First match wins.

RULES: List[Tuple[str, any, str]] = [
    ("ssn",           _ssn,          "Please enter a valid SSN (e.g. 123-45-6789)"),
    ("social security",_ssn,         "Please enter a valid SSN (e.g. 123-45-6789)"),
    ("email",         _email,        "Please enter a valid email address"),
    ("phone",         _phone,        "Please enter a valid 10-digit phone number"),
    ("income",        _income,       "Please enter a valid income amount (e.g. 75000)"),
    ("salary",        _income,       "Please enter a valid salary amount"),
    ("annual",        _income,       "Please enter a valid annual amount"),
    ("loan amount",   _loan_amount,  "Loan amount must be between $50,000 and $10,000,000"),
    ("purchase price",_loan_amount,  "Purchase price must be between $50,000 and $10,000,000"),
    ("property value",_loan_amount,  "Please enter a valid property value"),
    ("zip",           _zip_code,     "Please enter a valid ZIP code (e.g. 90210)"),
    ("date of birth", _date,         "Please enter a valid date (e.g. 01/15/1985)"),
    ("dob",           _date,         "Please enter a valid date (e.g. 01/15/1985)"),
    ("credit score",  _credit_score, "Credit score must be between 300 and 850"),
    ("down payment",  _percentage,   "Please enter a valid percentage or dollar amount"),
    ("interest rate", _percentage,   "Please enter a valid interest rate (e.g. 6.5)"),
]

MULTI_FIELD_KEYWORDS = {
    "ssn", "social security", "email", "phone", "income", "salary", "annual",
    "loan amount", "purchase price", "property value", "zip", "date of birth",
    "dob", "credit score", "down payment", "interest rate",
}


def validate_message(
    message: str,
    context: str = "",
) -> Tuple[bool, List[str]]:
    """
    Validate a borrower's message given the conversational context
    (typically the AI's last question / prompt).

    Returns (True, []) if valid or no rule matches.
    Returns (False, [error_string]) on a format violation.
    """
    msg = message.strip()

    if not msg:
        return False, ["Please enter a response before sending."]

    ctx = context.lower()
    matched_keywords = [keyword for keyword in MULTI_FIELD_KEYWORDS if keyword in ctx]
    if len(matched_keywords) > 1:
        return True, []

    for keyword, validator, error_msg in RULES:
        if keyword in ctx:
            if not validator(msg):
                return False, [error_msg]
            return True, []

    # No specific rule matched — allow through
    return True, []


def sanitize_input(text: str) -> str:
    """Strip leading/trailing whitespace and collapse internal spaces."""
    return " ".join(text.split())