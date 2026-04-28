class LoanAgent:
    def evaluate(self, data: dict) -> dict:
        income = data.get("income", 0)
        debt = data.get("debt", 0)

        dti = debt / income if income else 0

        return {
            **data,
            "dti": dti,
            "eligible": dti < 0.43
        }
