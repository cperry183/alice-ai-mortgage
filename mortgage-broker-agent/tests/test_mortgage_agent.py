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

    def test_loan_amount(self):
        assert self.app_data.loan_amount == 304000.0

    def test_property_value(self):
        assert self.app_data.property_value == 0.0  # property_value not set, purchase_price used

    def test_monthly_income(self):
        # base (8500) + other (0) = 8500
        assert self.app_data.monthly_income == 8500.0

    def test_total_monthly_debt(self):
        # rent(1800) + car(450) + student(300) + cc(150) + other(0) = 2700
        assert self.app_data.total_monthly_debt == 2700.0

    def test_ltv_ratio_zero_without_property_value(self):
        assert self.app_data.ltv_ratio == 0.0


# ─────────────────────────────────────────────────────────────
#  Unit Tests: ConversationState
# ─────────────────────────────────────────────────────────────

class TestConversationState:
    def setup_method(self):
        self.state = ConversationState()

    def test_initial_stage(self):
        assert self.state.current_stage == "personal"

    def test_add_message(self):
        self.state.add_message("user", "Hello")
        assert len(self.state.messages) == 1
        assert self.state.messages[0]["role"] == "user"

    def test_progress_zero_at_start(self):
        assert self.state.get_progress_percent() == 0

    def test_progress_100_when_complete(self):
        self.state.is_complete = True
        assert self.state.get_progress_percent() == 100

    def test_stage_index(self):
        self.state.current_stage = "employment"
        assert self.state.get_stage_index() == 1

    def test_to_dict(self):
        d = self.state.to_dict()
        assert "session_id" in d
        assert "current_stage" in d
        assert d["is_complete"] is False


# ─────────────────────────────────────────────────────────────
#  Unit Tests: Document Generator
# ─────────────────────────────────────────────────────────────

class TestDocumentGenerator:
    def setup_method(self):
        self.output_dir = "/tmp/test_mortgage_docs"
        self.generator = MortgageDocumentGenerator(output_dir=self.output_dir)
        self.app_data = ApplicationData(SAMPLE_APP_DATA)

    def test_output_dir_created(self):
        assert os.path.exists(self.output_dir)

    def test_generate_urla_1003(self):
        filepath = os.path.join(self.output_dir, "test_1003.pdf")
        self.generator._generate_urla_1003(self.app_data, filepath)
        assert os.path.exists(filepath)
        assert os.path.getsize(filepath) > 1000  # Non-empty PDF

    def test_generate_good_faith_estimate(self):
        filepath = os.path.join(self.output_dir, "test_gfe.pdf")
        self.generator._generate_good_faith_estimate(self.app_data, filepath)
        assert os.path.exists(filepath)
        assert os.path.getsize(filepath) > 1000

    def test_generate_borrower_authorization(self):
        filepath = os.path.join(self.output_dir, "test_auth.pdf")
        self.generator._generate_borrower_authorization(self.app_data, filepath)
        assert os.path.exists(filepath)

    def test_generate_privacy_notice(self):
        filepath = os.path.join(self.output_dir, "test_privacy.pdf")
        self.generator._generate_privacy_notice(self.app_data, filepath)
        assert os.path.exists(filepath)

    def test_generate_credit_authorization(self):
        filepath = os.path.join(self.output_dir, "test_credit.pdf")
        self.generator._generate_credit_authorization(self.app_data, filepath)
        assert os.path.exists(filepath)

    def test_generate_income_verification(self):
        filepath = os.path.join(self.output_dir, "test_income.pdf")
        self.generator._generate_income_verification(self.app_data, filepath)
        assert os.path.exists(filepath)

    def test_generate_all_documents(self):
        documents = self.generator.generate_all_documents(self.app_data)
        assert len(documents) == 6
        for doc in documents:
            assert "id" in doc
            assert "name" in doc
            assert "filename" in doc
            if doc.get("generated"):
                assert os.path.exists(doc["filepath"])


# ─────────────────────────────────────────────────────────────
#  Unit Tests: Utility Functions
# ─────────────────────────────────────────────────────────────

class TestUtilityFunctions:
    def test_try_float_with_valid_number(self):
        assert _try_float(100) == 100.0
        assert _try_float("250.50") == 250.50

    def test_try_float_with_none(self):
        assert _try_float(None) == 0.0

    def test_try_float_with_invalid_string(self):
        assert _try_float("not-a-number") == 0.0

    def test_try_float_with_zero(self):
        assert _try_float(0) == 0.0

    def test_try_float_with_custom_default(self):
        assert _try_float(None, default=99.9) == 99.9


# ─────────────────────────────────────────────────────────────
#  API Integration Tests
# ─────────────────────────────────────────────────────────────

class TestAPI:
    def setup_method(self):
        os.environ["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "test-key")
        from app.api.server import app
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_health_endpoint(self):
        res = self.client.get("/api/health")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["status"] == "ok"

    def test_new_session(self):
        res = self.client.post("/api/session/new")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "session_id" in data
        assert data["status"] == "created"

    def test_session_status_not_found(self):
        res = self.client.get("/api/session/nonexistent-session-id/status")
        assert res.status_code == 404

    def test_chat_missing_fields(self):
        res = self.client.post("/api/chat",
            data=json.dumps({}),
            content_type="application/json")
        assert res.status_code == 400

    def test_document_download_invalid_filename(self):
        res = self.client.get("/api/documents/../etc/passwd")
        assert res.status_code == 400

    def test_document_download_not_found(self):
        res = self.client.get("/api/documents/nonexistent_doc.pdf")
        assert res.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
