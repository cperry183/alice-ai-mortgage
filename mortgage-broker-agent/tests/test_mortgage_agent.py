"""
Test suite for Mortgage Broker Agent
"""

import pytest
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.conversation_state import ConversationState, ApplicationData
from app.documents.document_generator import MortgageDocumentGenerator, _try_float
from app.utils.validation import validate_message


# ─────────────────────────────────────────────────────────────
#  Sample application data for testing
# ─────────────────────────────────────────────────────────────

SAMPLE_APP_DATA = {
    "complete": True,
    "personal": {
        "first_name": "John",
        "middle_name": "Robert",
        "last_name": "Smith",
        "dob": "01/15/1985",
        "ssn": "123-45-6789",
        "marital_status": "married",
        "dependents": 2,
        "current_address": "123 Main St, Springfield, IL 62701",
        "years_at_address": 5,
        "phone": "555-867-5309",
        "email": "john.smith@email.com",
        "us_citizen": True,
        "own_or_rent": "Rent"
    },
    "employment": {
        "employment_status": "employed",
        "employer_name": "Acme Corporation",
        "employer_address": "456 Business Ave, Springfield, IL 62702",
        "job_title": "Senior Engineer",
        "years_at_employer": 8,
        "employment_start": "2016-03",
        "base_monthly_income": 8500,
        "overtime_monthly": 500,
        "bonus_monthly": 250,
        "self_employed": False
    },
    "assets": {
        "checking_balance": 15000,
        "savings_balance": 45000,
        "retirement_balance": 120000,
        "investments": 30000,
        "real_estate_value": 0,
        "other_assets": 5000
    },
    "liabilities": {
        "monthly_rent": 1800,
        "car_payment": 450,
        "car_balance": 18000,
        "student_loan_payment": 300,
        "student_loan_balance": 25000,
        "credit_card_minimum": 150,
        "credit_card_balance": 8000,
        "other_monthly_debt": 0,
        "judgments": False,
        "bankruptcy": False,
        "foreclosure": False,
        "lawsuit": False
    },
    "property": {
        "property_address": "789 Oak Lane, Springfield, IL 62703",
        "property_type": "Single Family",
        "purchase_price": 380000,
        "loan_amount": 304000,
        "down_payment": 76000,
        "loan_purpose": "Purchase",
        "property_use": "Primary Residence"
    },
    "loan_preferences": {
        "loan_type": "Conventional",
        "loan_term": 30,
        "rate_type": "Fixed",
        "veteran": False
    }
}


# ─────────────────────────────────────────────────────────────
#  Unit Tests: ApplicationData
# ─────────────────────────────────────────────────────────────

class TestApplicationData:
    def setup_method(self):
        self.app_data = ApplicationData(SAMPLE_APP_DATA)

    def test_borrower_name(self):
        assert self.app_data.borrower_name == "John Robert Smith"
