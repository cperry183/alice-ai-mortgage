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
    return bool(re.search(r"\b\d{5}(?:-\d{4})?\b", v.strip()))

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

def _residence_duration(v: str) -> bool:
    value = v.strip().lower()
    return bool(
        re.search(r"\b\d+(\.\d+)?\s*(year|years|yr|yrs|month|months|mo|mos)?\b", value) or
        re.search(r"\bsince\s+\d{4}\b", value) or
        re.search(r"\b(all my life|lifetime|always)\b", value)
    )


def _context_asks_for_income_amount(ctx: str) -> bool:
    income_amount_patterns = [
        r"\b(base|gross|monthly|annual|yearly)\s+income\b",
        r"\bincome\s+(amount|total|average)\b",
        r"\b(amount|how much|monthly average|per month|per year|annually)\b",
        r"\b(salary|earn|make|wages|pay)\b",
    ]
    return any(re.search(pattern, ctx) for pattern in income_amount_patterns)


def _context_asks_income_existence(ctx: str) -> bool:
    income_existence_patterns = [
        r"\b(any|other|additional)\s+income\s+(source|sources)\b",
        r"\b(do you|are you)\s+.*\b(receiv(?:e|ing)|have)\s+.*\bincome\b",
        r"\brental income\b",
    ]
    return any(re.search(pattern, ctx) for pattern in income_existence_patterns)


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
    ("how long have you lived", _residence_duration, "Please enter how long you have lived there (e.g. 2 years or 18 months)"),
    ("how long at current address", _residence_duration, "Please enter how long you have lived there (e.g. 2 years or 18 months)"),
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
    if "income" in ctx and _context_asks_income_existence(ctx) and not _context_asks_for_income_amount(ctx):
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
