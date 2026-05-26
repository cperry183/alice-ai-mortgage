from fastapi import Depends, FastAPI
from agent import LoanAgent
from rbac import require_agent_role

app = FastAPI()
agent = LoanAgent()

@app.post("/evaluate")
def evaluate(data: dict, role: str = Depends(require_agent_role("orchestrator"))):
    return agent.evaluate(data)
