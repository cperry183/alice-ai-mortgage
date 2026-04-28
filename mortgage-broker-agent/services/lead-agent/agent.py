class LeadAgent:
    def run(self, data: dict) -> dict:
        # Extract user info
        name = data.get("name")
        income = data.get("income")
        intent = data.get("intent")

        return {
            "name": name,
            "income": income,
            "intent": intent,
            "status": "lead_processed"
        }
