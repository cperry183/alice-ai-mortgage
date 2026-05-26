from fastapi import Depends, FastAPI
from agent import LeadAgent
from rbac import require_agent_role

app = FastAPI()
agent = LeadAgent()

@app.post("/process")
def process(data: dict, role: str = Depends(require_agent_role("orchestrator"))):
    return agent.run(data)
