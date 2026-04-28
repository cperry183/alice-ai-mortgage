"""
Conversation State Management
Tracks the state of a mortgage application conversation
"""

from dataclasses import dataclass, field
from typing import Optional
import uuid
from datetime import datetime


@dataclass
class ApplicationData:
    """Structured mortgage application data"""
    raw: dict

    def get(self, section: str, key: str, default=None):
        return self.raw.get(section, {}).get(key, default)

    @property
    def personal(self) -> dict:
        return self.raw.get("personal", {})

    @property
    def employment(self) -> dict:
        return self.raw.get("employment", {})

    @property
    def assets(self) -> dict:
        return self.raw.get("assets", {})

    @property
    def liabilities(self) -> dict:
        return self.raw.get("liabilities", {})

    @property
    def property_info(self) -> dict:
        return self.raw.get("property", {})

    @property
    def loan_preferences(self) -> dict:
        return self.raw.get("loan_preferences", {})

    @property
    def borrower_name(self) -> str:
        p = self.personal
        parts = [
            p.get("first_name", ""),
            p.get("middle_name", ""),
            p.get("last_name", "")
        ]
        return " ".join(p for p in parts if p).strip() or "Applicant"

    @property
    def loan_amount(self) -> float:
        try:
            return float(self.property_info.get("loan_amount", 0) or 0)
        except (ValueError, TypeError):
            return 0.0

    @property
    def property_value(self) -> float:
        try:
            return float(self.property_info.get("property_value", 0) or 0)
        except (ValueError, TypeError):
            return 0.0

    @property
    def monthly_income(self) -> float:
        try:
            base = float(self.employment.get("base_monthly_income", 0) or 0)
            other = float(self.employment.get("other_monthly_income", 0) or 0)
            return base + other
        except (ValueError, TypeError):
            return 0.0

    @property
    def total_monthly_debt(self) -> float:
        """Calculate total monthly debt obligations"""
        liabilities = self.liabilities
        try:
            rent = float(liabilities.get("monthly_rent", 0) or 0)
            car = float(liabilities.get("car_payment", 0) or 0)
            student = float(liabilities.get("student_loan_payment", 0) or 0)
            cc = float(liabilities.get("credit_card_minimum", 0) or 0)
            other = float(liabilities.get("other_monthly_debt", 0) or 0)
            return rent + car + student + cc + other
        except (ValueError, TypeError):
            return 0.0

    @property
    def dti_ratio(self) -> float:
        """Debt-to-income ratio"""
        if self.monthly_income > 0:
            return (self.total_monthly_debt / self.monthly_income) * 100
        return 0.0

    @property
    def ltv_ratio(self) -> float:
        """Loan-to-value ratio"""
        if self.property_value > 0:
            return (self.loan_amount / self.property_value) * 100
        return 0.0


class ConversationState:
    """Manages the state of a single mortgage application conversation"""

    STAGES = [
        "personal",
        "employment",
        "assets",
        "liabilities",
        "property",
        "loan_preferences"
    ]

    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.messages: list = []
        self.current_stage: str = "personal"
        self.is_complete: bool = False
        self.application_data: Optional[ApplicationData] = None

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> list:
        return self.messages.copy()

    def get_stage_index(self) -> int:
        try:
            return self.STAGES.index(self.current_stage)
        except ValueError:
            return 0

    def get_progress_percent(self) -> int:
        if self.is_complete:
            return 100
        return int((self.get_stage_index() / len(self.STAGES)) * 100)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "current_stage": self.current_stage,
            "is_complete": self.is_complete,
            "progress": self.get_progress_percent(),
            "message_count": len(self.messages)
        }
