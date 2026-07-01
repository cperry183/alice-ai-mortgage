"""
Mortgage Broker AI Agent
Orchestrates the conversation, enforces state isolation, and drives the document generation workflow.
"""

import json
import os
import re
import time
from copy import deepcopy
from typing import List, Optional
from anthropic import Anthropic
from app.documents.document_generator import MortgageDocumentGenerator
from app.agents.conversation_state import ConversationState, ApplicationData


SYSTEM_PROMPT = """You are an expert mortgage broker assistant operating in Massachusetts, New Hampshire, New York, and Connecticut. Your job is to collect all necessary information from a client to complete a mortgage application and compile the state-compliant broker files.

You must collect information in a friendly, professional manner. Guide the borrower through the process step by step.

You need to collect the following information across these stages:

**STAGE 1: Personal Information**
- Full legal name (first, middle, last)
- Date of birth (MM/DD/YYYY)
- Social Security Number (format: XXX-XX-XXXX)
- Marital status (single/married/divorced/widowed/separated)
- Number of dependents
- Current address (street, city, state, ZIP)
- How long at current address (years/months)
- Previous address if less than 2 years
- Phone number
- Email address
- US Citizen or permanent resident? If not, visa type

**STAGE 2: State Jurisdiction (CRITICAL DISCLOSURE FORK)**
- State Jurisdiction selection (MUST explicitly ask and confirm either 'MA', 'NH', 'NY', or 'CT').
- Explain to the client that mortgage broker forms are heavily driven by local state laws (Massachusetts Division of Banks, New Hampshire Banking Department, New York Department of Financial Services, or Connecticut Department of Banking).

**STAGE 3: Employment & Income**
- Employment status (employed/self-employed/retired/unemployed)
- Employer name and address
- Job title / position
- Years at current employer
- Employment start date
- Base monthly income (gross)
- Overtime/bonus/commission income (monthly average)
- Any other income sources (rental, investment, alimony, etc.)
- IF SELF-EMPLOYED: Business entity name, years in business, and 2-year average net income matrix (explain that we will compile a Profit & Loss Statement and Business Bank Statement Analysis instead of W-2 checklists).

**STAGE 4: Assets**
- Checking account balance(s)
- Savings account balance(s)
- Retirement accounts (401k, IRA) balances
- Stocks/bonds/investments
- Other real estate owned
- Down payment source and amount (if gift funds are used, indicate that an Executed Gift Letter Form will be added to the document manifest).

**STAGE 5: Liabilities & Debts**
- Monthly rent payment (if renting)
- Car loan(s): balance, monthly payment, lender
- Student loans: balance, monthly payment
- Credit card balances and minimum payments
- Personal loans / Any other monthly obligations
- Any judgments, bankruptcies, foreclosures in past 7 years?
- Any delinquent federal debt or lawsuits pending?

**STAGE 6: Property Information**
- Property address (if known)
- Property type (single family/condo/townhouse/multi-family/manufactured)
- Purchase price or estimated value
- Loan amount requested
- Down payment amount
- Loan purpose (purchase/refinance/cash-out refinance)
- How will property be used? (primary residence/second home/investment)
- If refinance: current loan balance, current monthly payment, current lender

**STAGE 7: Loan Preferences**
- Loan type preference (conventional/FHA/VA/USDA/Jumbo)
- Term preference (30-year/20-year/15-year/10-year)
- Rate preference (fixed/adjustable)
- Is borrower a veteran or active military? (If VA, flag for VA Comparison and Certificate of Eligibility).

IMPORTANT RULES:
1. Collect information ONE STAGE AT A TIME. Complete each stage before moving to the next.
2. Within each stage, ask 2-3 related questions at a time - don't bombard with all questions at once.
3. Validate answers as you receive them. If something seems incorrect, politely ask for clarification.
4. Enforce jurisdiction rules contextually. For MA properties, mention the "Disclosure of Loan Originator Compensation" track. For NH, mention "NH Consumer Credit Disclosures". For NY, mention the DFS broker fee disclosure, subprime notice, HELOC addendum, prepayment disclosure, and choice of attorney notice where applicable. For CT, mention the broker agreement, NMLS display, and consumer credit disclosure addenda.
5. When you have collected ALL information for ALL stages, output a special JSON block like this:

<COLLECTED_DATA>
{
  "complete": true,
  "state_jurisdiction": "MA", 
  "personal": { ... },
  "employment": { "is_self_employed": true, ... },
  "assets": { ... },
  "liabilities": { ... },
  "property": { ... },
  "loan_preferences": { "loan_type": "FHA", ... },
  "state_compliance": {
    "intent_to_proceed": true,
    "ma_compensation_disclosed": true,
    "nh_credit_disclosure_provided": false
  }
}
</COLLECTED_DATA>

6. Format numbers properly (no need for $ signs in your JSON, just numbers).
7. If the borrower doesn't know something, use null as the value.
8. Always be encouraging and explain why you need each piece of information.
9. Acknowledge each response before asking the next questions.
10. Current stage should be tracked in your responses so the user knows where they are in the process.
11. For "How long have you lived at this address?" accept concise duration answers such as "2", "2 years", "18 months", "since 2020", or "all my life". Do not repeat the address-duration question after the borrower gives a duration; record it as years_at_address or months_at_address and move on.
12. Treat the supplied application memory as authoritative. Do not ask the borrower to repeat facts already present there; acknowledge known facts and ask only for missing information.
13. If the borrower gives information early or out of order, retain it and use it when that later stage arrives.

Start by warmly greeting the client and explaining what you'll need to collect. Then begin with Stage 1."""


class MortgageAgent:
    def __init__(self):
        self.client = Anthropic()
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.doc_generator = MortgageDocumentGenerator()

    def process_message(self, user_message: str, state: ConversationState) -> dict:
        """
        Primary entry point processing broker conversation loops.
        Resolves the AttributeError by mapping directly to server execution calls.
        """
        # Ensure session properties are mapped from database context layers
        self._refresh_application_memory(state)
        state.sync_context_properties()

        # Append user text to conversational chain
        state.add_message("user", user_message)
        self._remember_turn(state, user_message)

        # Call Anthropic API Engine
        started_at = time.perf_counter()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self._system_prompt_with_memory(state),
            messages=state.get_messages()
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)

        assistant_message = response.content[0].text

        # Append assistant text to conversational chain
        state.add_message("assistant", assistant_message)

        # Inspect if rules engine block has reached completion criteria
        collected_data = self._extract_collected_data(assistant_message)

        result = {
            "message": self._clean_message(assistant_message),
            "stage": state.current_stage,
            "complete": False,
            "progress": state.get_progress_percent(),
            "documents": [],
            "suggestions": self._suggestions_for_stage(state.current_stage),
            "agent_metrics": {
                "model": self.model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
            },
        }

        if collected_data and collected_data.get("complete"):
            # Construct application data mapping structure
            app_data = ApplicationData(collected_data)
            
            # Delegate compilation out to document assembly engine
            documents = self.doc_generator.generate_all_documents(app_data)
            
            state.application_data = app_data
            state.is_complete = True
            
            result["complete"] = True
            result["documents"] = documents
            result["message"] = self._clean_message(assistant_message)

        # Advance or realign operational stages
        result["stage"] = self._detect_stage(assistant_message)
        state.current_stage = result["stage"]
        result["progress"] = state.get_progress_percent()
        result["suggestions"] = [] if result["complete"] else self._suggestions_for_stage(result["stage"])

        return result

    def _system_prompt_with_memory(self, state: ConversationState) -> str:
        memory = state.application_data.raw if state.application_data else {}
        if not memory:
            return SYSTEM_PROMPT
        return (
            f"{SYSTEM_PROMPT}\n\n"
            "CURRENT APPLICATION MEMORY (authoritative; do not re-ask for these known values):\n"
            f"{json.dumps(memory, indent=2, sort_keys=True)}"
        )

    def _refresh_application_memory(self, state: ConversationState):
        """Rebuild structured memory from the persisted transcript plus saved facts."""
        raw = deepcopy(state.application_data.raw if state.application_data else {})
        previous_assistant = ""

        for message in state.get_messages():
            role = message.get("role")
            content = message.get("content", "")
            if role == "assistant":
                previous_assistant = content
            elif role == "user":
                self._merge_dict(raw, self._extract_facts(content, previous_assistant, state.current_stage))

        if state.state_jurisdiction:
            raw["state_jurisdiction"] = state.state_jurisdiction
            raw.setdefault("property", {})["subject_property_state"] = state.state_jurisdiction

        state.application_data = ApplicationData(raw)
        state.sync_context_properties()

    def _remember_turn(self, state: ConversationState, user_message: str):
        messages = state.get_messages()
        previous_assistant = ""
        for message in reversed(messages[:-1]):
            if message.get("role") == "assistant":
                previous_assistant = message.get("content", "")
                break

        raw = deepcopy(state.application_data.raw if state.application_data else {})
        self._merge_dict(raw, self._extract_facts(user_message, previous_assistant, state.current_stage))
        state.application_data = ApplicationData(raw)
        state.sync_context_properties()

    def _extract_facts(self, user_message: str, assistant_context: str, current_stage: str) -> dict:
        text = user_message.strip()
        lower_text = text.lower()
        lower_context = assistant_context.lower()
        facts = {}

        email = re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', text)
        if email:
            facts.setdefault("personal", {})["email"] = email.group(0)

        phone = re.search(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phone:
            facts.setdefault("personal", {})["phone"] = phone.group(0)

        if re.search(r'\b(MA|Massachusetts)\b', text, re.I):
            facts["state_jurisdiction"] = "MA"
            facts.setdefault("property", {})["subject_property_state"] = "MA"
        elif re.search(r'\b(NH|New Hampshire)\b', text, re.I):
            facts["state_jurisdiction"] = "NH"
            facts.setdefault("property", {})["subject_property_state"] = "NH"
        elif re.search(r'\b(NY|New York)\b', text, re.I):
            facts["state_jurisdiction"] = "NY"
            facts.setdefault("property", {})["subject_property_state"] = "NY"
        elif re.search(r'\b(CT|Connecticut)\b', text, re.I):
            facts["state_jurisdiction"] = "CT"
            facts.setdefault("property", {})["subject_property_state"] = "CT"

        if "how long have you lived" in lower_context or "how long at current address" in lower_context:
            facts.setdefault("personal", {}).update(self._duration_fields(text, "address"))

        if "current address" in lower_context and re.search(r'\d+ .+', text):
            facts.setdefault("personal", {})["current_address"] = text

        if "employment status" in lower_context or current_stage == "employment" or "employed" in lower_text:
            status = self._employment_status(lower_text)
            if status:
                employment = facts.setdefault("employment", {})
                employment["employment_status"] = status
                employment["is_self_employed"] = status == "self-employed"

        employer_match = re.search(r'\b(?:work|employed)\s+(?:at|for|by)\s+(.+)', text, re.I)
        if "current employer" in lower_context or "employer name" in lower_context or employer_match:
            employer = facts.setdefault("employment", {})
            employer_text = employer_match.group(1).strip() if employer_match else text
            employer["employer_name"] = employer_text
            if "," in employer_text:
                name, address = employer_text.split(",", 1)
                employer["employer_name"] = name.strip()
                employer["employer_address"] = address.strip()

        if "job title" in lower_context or "position" in lower_context:
            facts.setdefault("employment", {})["job_title"] = text

        if "years at current employer" in lower_context or "how long" in lower_context and "employer" in lower_context:
            facts.setdefault("employment", {}).update(self._duration_fields(text, "employer"))

        if "employment start" in lower_context or "start date" in lower_context:
            facts.setdefault("employment", {})["employment_start"] = text

        income_terms = ["base monthly income", "monthly income", "income", "salary", "earn", "make", "annual"]
        if any(word in lower_context for word in income_terms) or any(word in lower_text for word in income_terms):
            amount = self._money_amount(text)
            if amount is not None:
                employment = facts.setdefault("employment", {})
                if "annual" in lower_context or "annual" in lower_text or "year" in lower_text:
                    employment["annual_income"] = amount
                    employment["base_monthly_income"] = round(amount / 12, 2)
                else:
                    employment["base_monthly_income"] = amount

        return facts

    def _merge_dict(self, target: dict, source: dict):
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                self._merge_dict(target[key], value)
            elif value not in (None, "", [], {}):
                target[key] = value

    def _duration_fields(self, text: str, target: str) -> dict:
        lower = text.lower().strip()
        years = re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?|y)\b', lower)
        months = re.search(r'(\d+(?:\.\d+)?)\s*(?:months?|mos?|m)\b', lower)
        since = re.search(r'\bsince\s+(\d{4})\b', lower)
        bare_number = re.fullmatch(r'\d+(?:\.\d+)?', lower)

        prefix = "years_at_address" if target == "address" else "years_at_employer"
        month_key = "months_at_address" if target == "address" else "months_at_employer"

        if years:
            return {prefix: float(years.group(1))}
        if months:
            return {month_key: float(months.group(1))}
        if since:
            return {prefix: f"since {since.group(1)}"}
        if bare_number:
            return {prefix: float(lower)}
        if lower:
            return {prefix: text}
        return {}

    def _employment_status(self, lower_text: str) -> Optional[str]:
        if "self" in lower_text and "employ" in lower_text:
            return "self-employed"
        for status in ["employed", "retired", "unemployed"]:
            if re.search(rf'\b{status}\b', lower_text):
                return status
        return None

    def _money_amount(self, text: str) -> Optional[float]:
        match = re.search(r'\$?\s*([0-9][0-9,]*(?:\.\d+)?)', text)
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None

    def _extract_collected_data(self, message: str) -> Optional[dict]:
        """Extract structured JSON data block out of response stream."""
        pattern = r'<COLLECTED_DATA>(.*?)</COLLECTED_DATA>'
        match = re.search(pattern, message, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                return None
        return None

    def _clean_message(self, message: str) -> str:
        """Removes the structural raw JSON blocks from screen rendering outputs."""
        cleaned = re.sub(r'<COLLECTED_DATA>.*?</COLLECTED_DATA>', '', message, flags=re.DOTALL)
        return cleaned.strip()

    def _detect_stage(self, message: str) -> str:
        """Determines current tracking index markers based on context indicators."""
        msg_lower = message.lower()
        if "stage 7" in msg_lower or "loan preference" in msg_lower:
            return "loan_preferences"
        elif "stage 6" in msg_lower or "property" in msg_lower:
            return "property"
        elif "stage 5" in msg_lower or "liabilities" in msg_lower or "debt" in msg_lower:
            return "liabilities"
        elif "stage 4" in msg_lower or "asset" in msg_lower:
            return "assets"
        elif "stage 3" in msg_lower or "employment" in msg_lower or "income" in msg_lower:
            return "employment"
        elif "stage 2" in msg_lower or "jurisdiction" in msg_lower or "massachusetts" in msg_lower or "new hampshire" in msg_lower or "new york" in msg_lower or "connecticut" in msg_lower:
            return "jurisdiction"
        else:
            return "personal"

    def _suggestions_for_stage(self, stage: str) -> List[str]:
        """Return lightweight UI prompts that help borrowers answer the next turn."""
        suggestions = {
            "personal": [
                "I can provide my contact details",
                "I need help with this question",
                "I don't know yet",
            ],
            "jurisdiction": ["MA", "NH", "NY", "CT"],
            "employment": [
                "I'm employed full-time",
                "I'm self-employed",
                "I have additional income",
            ],
            "assets": [
                "Checking and savings balances",
                "Retirement or investment accounts",
                "Gift funds will be used",
            ],
            "liabilities": [
                "No other debts",
                "I have monthly loan payments",
                "I have credit card balances",
            ],
            "property": [
                "Purchase",
                "Refinance",
                "Property address unknown",
            ],
            "loan_preferences": [
                "Conventional fixed-rate",
                "FHA",
                "I'm a veteran or active military",
            ],
        }
        return suggestions.get(stage, suggestions["personal"])
