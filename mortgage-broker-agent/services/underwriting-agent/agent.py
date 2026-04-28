class UnderwritingAgent:
    def run(self, data: dict) -> dict:
        if not data.get("eligible"):
            decision = "denied"
        elif not data.get("documents_verified"):
            decision = "pending"
        else:
            decision = "approved"

        return {
            **data,
            "decision": decision
        }
