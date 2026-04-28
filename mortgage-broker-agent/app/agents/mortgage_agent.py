"""
Mortgage Broker AI Agent
Orchestrates the conversation and document generation workflow
"""

import json
import re
from typing import Optional
from anthropic import Anthropic
from app.documents.document_generator import MortgageDocumentGenerator
from app.agents.conversation_state import ConversationState, ApplicationData


SYSTEM_PROMPT = """You are an expert mortgage broker assistant. Your job is to collect all necessary information from a client to complete a mortgage application and generate the required documents.

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

**STAGE 2: Employment & Income**
- Employment status (employed/self-employed/retired/unemployed)
- Employer name and address
- Job title / position
- Years at current employer
- Employment start date
- Base monthly income (gross)
- Overtime/bonus/commission income (monthly average)
- Any other income sources (rental, investment, alimony, etc.)
- If self-employed: business name, years in business, 2-year average net income

**STAGE 3: Assets**
- Checking account balance(s)
- Savings account balance(s)
- Retirement accounts (401k, IRA) balances
- Stocks/bonds/investments
- Other real estate owned
- Vehicles
- Other assets
- Down payment source and amount

**STAGE 4: Liabilities & Debts**
- Monthly rent payment (if renting)
- Car loan(s): balance, monthly payment, lender
- Student loans: balance, monthly payment
- Credit card balances and minimum payments
- Personal loans
- Any other monthly obligations
- Any judgments, bankruptcies, foreclosures in past 7 years?
- Any delinquent federal debt?
- Any lawsuits pending?

**STAGE 5: Property Information**
- Property address (if known)
- Property type (single family/condo/townhouse/multi-family/manufactured)
- Purchase price or estimated value
- Loan amount requested
- Down payment amount
- Loan purpose (purchase/refinance/cash-out refinance)
- How will property be used? (primary residence/second home/investment)
- If refinance: current loan balance, current monthly payment, current lender

**STAGE 6: Loan Preferences**
- Loan type preference (conventional/FHA/VA/USDA)
- Term preference (30-year/20-year/15-year/10-year)
- Rate preference (fixed/adjustable)
- Is borrower a veteran or active military?

IMPORTANT RULES:
1. Collect information ONE STAGE AT A TIME. Complete each stage before moving to the next.
2. Within each stage, ask 2-3 related questions at a time - don't bombard with all questions at once.
3. Validate answers as you receive them. If something seems incorrect, politely ask for clarification.
4. Be conversational and empathetic - this is a significant financial decision.
5. When you have collected ALL information for ALL stages, output a special JSON block like this:

<COLLECTED_DATA>
{
  "complete": true,
  "personal": { ... },
  "employment": { ... },
  "assets": { ... },
  "liabilities": { ... },
  "property": { ... },
  "loan_preferences": { ... }
}
</COLLECTED_DATA>

6. Format numbers properly (no need for $ signs in your JSON, just numbers).
7. If the borrower doesn't know something, use null as the value.
8. Always be encouraging and explain why you need each piece of information.
9. Acknowledge each response before asking the next questions.
10. Current stage should be tracked in your responses so the user knows where they are in the process.

Start by warmly greeting the client and explaining what you'll need to collect. Then begin with Stage 1."""


class MortgageAgent:
    def __init__(self):
        self.client = Anthropic()
        self.doc_generator = MortgageDocumentGenerator()

    def chat(self, state: ConversationState, user_message: str) -> dict:
        """Process a user message and return agent response"""

        # Add user message to history
        state.add_message("user", user_message)

        # Call Claude API
        response = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=state.get_messages()
        )

        assistant_message = response.content[0].text

        # Add assistant response to history
        state.add_message("assistant", assistant_message)

        # Check if data collection is complete
        collected_data = self._extract_collected_data(assistant_message)

        result = {
            "message": self._clean_message(assistant_message),
            "stage": state.current_stage,
            "complete": False,
            "documents": []
        }

        if collected_data and collected_data.get("complete"):
            # Generate all documents
            app_data = ApplicationData(collected_data)
            documents = self.doc_generator.generate_all_documents(app_data)
            state.application_data = app_data
            state.is_complete = True
            result["complete"] = True
            result["documents"] = documents
            result["message"] = self._clean_message(assistant_message)

        # Update stage based on conversation progress
        result["stage"] = self._detect_stage(assistant_message)
        state.current_stage = result["stage"]

        return result

    def _extract_collected_data(self, message: str) -> Optional[dict]:
        """Extract JSON data block from agent response"""
        pattern = r'<COLLECTED_DATA>(.*?)</COLLECTED_DATA>'
        match = re.search(pattern, message, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                return None
        return None

    def _clean_message(self, message: str) -> str:
        """Remove the JSON data block from the display message"""
        cleaned = re.sub(r'<COLLECTED_DATA>.*?</COLLECTED_DATA>', '', message, flags=re.DOTALL)
        return cleaned.strip()

    def _detect_stage(self, message: str) -> str:
        """Detect current stage from message content"""
        msg_lower = message.lower()
        if "stage 6" in msg_lower or "loan preference" in msg_lower:
            return "loan_preferences"
        elif "stage 5" in msg_lower or "property information" in msg_lower:
            return "property"
        elif "stage 4" in msg_lower or "liabilities" in msg_lower or "debts" in msg_lower:
            return "liabilities"
        elif "stage 3" in msg_lower or "assets" in msg_lower:
            return "assets"
        elif "stage 2" in msg_lower or "employment" in msg_lower or "income" in msg_lower:
            return "employment"
        else:
            return "personal"
