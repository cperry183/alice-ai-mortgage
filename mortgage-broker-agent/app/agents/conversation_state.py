"""
Conversation State Management
Tracks the state of a mortgage application conversation with 
strict state-specific (MA/NH/NY/CT) and program/compliance awareness.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime


@dataclass
class ApplicationData:
    """Structured mortgage application data with jurisdictional routing."""
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
    def state_compliance(self) -> dict:
        return self.raw.get("state_compliance", {})

    @property
    def state_jurisdiction(self) -> Optional[str]:
        state = self.property_info.get("subject_property_state") or self.personal.get("state")
        if state:
            state = str(state).upper().strip()
            if state in ["MA", "NH", "NY", "CT"]:
                return state
        return self.raw.get("state_jurisdiction")

    @property
    def loan_type(self) -> str:
        return str(self.loan_preferences.get("loan_type", "Conventional")).upper().strip()

    @property
    def is_self_employed(self) -> bool:
        val = self.employment.get("is_self_employed")
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ["true", "yes", "1"]
        return False

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
    def borrower_email(self) -> Optional[str]:
        return self.personal.get("email")

    @property
    def borrower_phone(self) -> Optional[str]:
        return self.personal.get("phone") or self.personal.get("phone_number")

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
            if self.is_self_employed:
                return float(self.employment.get("net_business_monthly_income", 0) or 0)

            base = float(self.employment.get("base_monthly_income", 0) or 0)
            other = float(self.employment.get("other_monthly_income", 0) or 0)
            return base + other
        except (ValueError, TypeError):
            return 0.0

    @property
    def total_monthly_debt(self) -> float:
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
        if self.monthly_income > 0:
            return (self.total_monthly_debt / self.monthly_income) * 100
        return 0.0

    @property
    def ltv_ratio(self) -> float:
        if self.property_value > 0:
            return (self.loan_amount / self.property_value) * 100
        return 0.0


class ConversationState:
    """
    Manages lifecycle, stage progression, and contextual state
    for a mortgage application conversation.
    """

    STAGES = [
        "personal",
        "jurisdiction",
        "employment",
        "assets",
        "liabilities",
        "property",
        "loan_preferences",
    ]

    def __init__(self, session_id: Optional[str] = None):
        # 🔥 FIX: session-aware initialization (prevents stateless resets)
        self.session_id: str = session_id or str(uuid.uuid4())
        self.created_at: datetime = datetime.now()

        self.messages: List[Dict[str, str]] = []
        self.current_stage: str = "personal"
        self.is_complete: bool = False
        self.application_data: ApplicationData = ApplicationData(raw={})

        self.state_jurisdiction: Optional[str] = None
        self.loan_type: str = "CONVENTIONAL"
        self.is_self_employed: bool = False

        self.intent_to_proceed: bool = False
        self.ma_compensation_disclosed: bool = False
        self.nh_credit_disclosure_provided: bool = False

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
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

    def sync_context_properties(self):
        if not self.application_data:
            return

        if self.application_data.state_jurisdiction:
            self.state_jurisdiction = self.application_data.state_jurisdiction

        self.loan_type = self.application_data.loan_type
        self.is_self_employed = self.application_data.is_self_employed

        sc = self.application_data.state_compliance
        self.intent_to_proceed = sc.get("intent_to_proceed", False)
        self.ma_compensation_disclosed = sc.get("ma_compensation_disclosed", False)
        self.nh_credit_disclosure_provided = sc.get("nh_credit_disclosure_provided", False)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "current_stage": self.current_stage,
            "state_jurisdiction": self.state_jurisdiction,
            "loan_type": self.loan_type,
            "is_self_employed": self.is_self_employed,
            "is_complete": self.is_complete,
            "progress": self.get_progress_percent(),
            "message_count": len(self.messages),
            "borrower_name": self.application_data.borrower_name if self.application_data else "Applicant",
            "metrics": {
                "dti": round(self.application_data.dti_ratio, 2) if self.application_data else 0.0,
                "ltv": round(self.application_data.ltv_ratio, 2) if self.application_data else 0.0,
            },
        }

    def to_snapshot(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "messages": self.messages,
            "current_stage": self.current_stage,
            "is_complete": self.is_complete,
            "application_data": self.application_data.raw if self.application_data else {},
            "state_jurisdiction": self.state_jurisdiction,
            "loan_type": self.loan_type,
            "is_self_employed": self.is_self_employed,
            "intent_to_proceed": self.intent_to_proceed,
            "ma_compensation_disclosed": self.ma_compensation_disclosed,
            "nh_credit_disclosure_provided": self.nh_credit_disclosure_provided,
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict):
        state = cls()
        if not snapshot:
            return state

        state.session_id = snapshot.get("session_id") or state.session_id

        created_at = snapshot.get("created_at")
        if created_at:
            try:
                state.created_at = datetime.fromisoformat(created_at)
            except (TypeError, ValueError):
                pass

        messages = snapshot.get("messages") or []
        if isinstance(messages, list):
            state.messages = [
                {"role": m.get("role", ""), "content": m.get("content", "")}
                for m in messages
                if isinstance(m, dict) and m.get("role") and m.get("content")
            ]

        state.current_stage = snapshot.get("current_stage") or state.current_stage
        state.is_complete = bool(snapshot.get("is_complete", False))
        state.application_data = ApplicationData(snapshot.get("application_data") or {})
        state.state_jurisdiction = snapshot.get("state_jurisdiction")
        state.loan_type = snapshot.get("loan_type") or state.loan_type
        state.is_self_employed = bool(snapshot.get("is_self_employed", False))
        state.intent_to_proceed = bool(snapshot.get("intent_to_proceed", False))
        state.ma_compensation_disclosed = bool(snapshot.get("ma_compensation_disclosed", False))
        state.nh_credit_disclosure_provided = bool(snapshot.get("nh_credit_disclosure_provided", False))

        state.sync_context_properties()
        return state